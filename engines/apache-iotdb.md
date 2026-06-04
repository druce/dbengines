---
name: Apache IoTDB
slug: apache-iotdb
rank: 138
data_model: Time-series (IoT)
license: Apache License 2.0 (permissive); commercial TimechoDB distribution
summary: Apache time-series DB purpose-built for industrial IoT, with a tree/table data model, columnar TsFile storage, and a pluggable consensus framework that trades consistency for write throughput.
last_researched: 2026-06-04
confidence: medium
---

# Apache IoTDB

> An Apache-licensed, write-optimized time-series database for industrial IoT that stores device telemetry in columnar TsFiles and lets you pick the consensus protocol per data type — strong (Raft) for metadata, weak/eventual (IoTConsensus) for time-series — making it fast and cheap but not a transactional store.

## When to use

**Use Apache IoTDB if:**
- ✅ You have industrial/IoT time-series at scale — high-frequency sensor telemetry, manufacturing, energy/grid, vehicles, high cardinality and out-of-order arrivals
- ✅ You want an Apache-licensed columnar, write-optimized store with an open file format (TsFile) and per-column encoding/compression
- ✅ You want to dial consistency per data type (strong Raft for metadata, fast eventual IoTConsensus for time-series)
- ✅ You need edge-to-cloud deployment, including lightweight edge nodes on constrained hardware

**Avoid Apache IoTDB if:**
- ❌ You need a transactional system of record — there are no multi-row/multi-statement transactions, only single-insert atomicity (biggest gotcha)
- ❌ You assume linearizable, durable-on-ack data writes — the high-throughput default (IoTConsensus) gives only eventual/session consistency, with no independent Jepsen verification
- ❌ You need relational joins, normalized models, or ad-hoc BI on non-time-series data
- ❌ You need strong cross-replica read-after-write on the time-series path

## Identity
- **Taxonomy / data model:** Time-series database for IoT. Two query models coexist: the original **tree model** (hierarchical paths `root.<group>.<device>.<measurement>`, schema partitioned by series family) and a newer **table model** (relational-style `SELECT ... FROM table` with tag/field columns) introduced in the 1.x line ([table-model query docs](https://iotdb.apache.org/UserGuide/latest-Table/Basic-Concept/Query-Data_apache.html)). See [time-series-storage](../concepts/time-series-storage.md).
- **Storage model:** Columnar on disk via **TsFile**, IoTDB's open column-oriented time-series file format with per-column encoding and compression ([Apache TsFile](https://github.com/apache/tsfile)). Write path is **LSM-like** ([lsm-vs-btree](../concepts/lsm-vs-btree.md)): inserts land in an in-memory MemTable (multiple series sorted separately), flushed to immutable TsFiles, merged by background compaction ([SIGMOD 2023 paper](https://sxsong.github.io/doc/23sigmod-iotdb.pdf)).
- **Workload:** OLTP-ingest + time-series analytics — heavy append ingestion plus range/aggregation scans. Not HTAP in the relational sense; it is a specialized time-series store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **Architecture:** Separates **ConfigNode** (metadata, partition table, scheduling) from **DataNode** (storage + query). Standard cluster is 3C3D — 3 ConfigNodes and ≥3 DataNodes ([cluster deployment](https://iotdb.apache.org/UserGuide/latest/Deployment-and-Maintenance/Cluster-Deployment_apache.html)). Data is partitioned by series family (vertical), then by time range (horizontal); partitions are placed on N nodes by consistent hashing where N = replication factor ([SIGMOD 2023 paper](https://sxsong.github.io/doc/23sigmod-iotdb.pdf)).
- **Pluggable consensus framework** — IoTDB's distinguishing feature; consistency depends entirely on which protocol you configure for each replica group ([Timecho: replication & consensus](https://www.timecho-global.com/archives/apache-iotdb-distributed-architecture-3-replication-and-consensus-algorithms)). See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md), [replication-models](../concepts/replication-models.md):
  - **RatisConsensus** — Raft, strong consistency, majority quorum; default for ConfigNode/metadata. CP under partition. See [cap-pacelc](../concepts/cap-pacelc.md).
  - **IoTConsensus** — multi-leader async replication for time-series data; documented as providing **eventual / session consistency**, high availability with as few as 2 replicas. AP-leaning: replicas accept writes independently and reconcile, so cross-replica reads can be stale.
  - **SimpleConsensus** — single replica, no replication, no failover.
- **CAP under partition:** Mixed by design — **CP for metadata (Ratis), AP/eventual for time-series data (IoTConsensus)**. The common production config sacrifices strict consistency on the data path for throughput.
- **PACELC:** With IoTConsensus, effectively **PA/EL** — favors availability under partition and low latency over consistency otherwise. With RatisConsensus on data, **PC/EC**. ⚠️ unverified — IoTDB has no published formal PACELC classification; this is inferred from the documented protocol semantics.
- **Default isolation:** No multi-statement transactions. The engine assumes single-record inserts, rare updates, and no multi-query transactions; concurrency control is bare-bones read/write locks (ReentrantReadWriteLock + a 100-slot HashLock) ([SIGMOD 2023 paper](https://sxsong.github.io/doc/23sigmod-iotdb.pdf); [dbdb.io](https://dbdb.io/db/iotdb)). dbdb.io labels its isolation "serializable" via those locks, but with **no transaction abstraction** that label means little for application correctness — treat writes as single-row atomic, not ACID-transactional. See [isolation-levels](../concepts/isolation-levels.md).
- **Tunable consistency:** Yes, but coarse — chosen per consensus group/data type, not per query.
- **Clock dependency:** Data is keyed by application-supplied timestamps; the DB does not rely on synchronized server clocks like TrueTime. Out-of-order ("delayed") arrivals are handled by the LSM/compaction path. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write** for the tree model: time-series paths and data types are registered (auto-registration is available). Table model adds explicit table/column definitions.
- **Migration/evolution:** New devices/measurements appear by inserting new paths — schema grows organically without a locking `ALTER`. ⚠️ unverified — no documented online-DDL story for retroactive type changes on existing series.
- **Type system:** Time-series of `BOOLEAN`, `INT32/64`, `FLOAT/DOUBLE`, `TEXT`, plus `STRING`, `BLOB`, `DATE`, `TIMESTAMP` in newer releases. Per-column **encodings** (RLE, TS_2DIFF, GORILLA, dictionary, etc.) and compressors (SNAPPY, LZ4, ZSTD, GZIP) — a core efficiency lever ([compression paper, VLDB 2025](https://www.vldb.org/pvldb/vol18/p3406-tang.pdf)). No native relational JSON/geospatial; this is a metric store.

## Query interface
- **Language:** SQL-like dialect parsed with ANTLR4. Supports `SELECT/FROM/WHERE/GROUP BY/HAVING/FILL`, time-range/down-sampling (`GROUP BY time`), and aggregation; statements split into schema, data-management, database-management, and functions ([SQL reference](https://iotdb.apache.org/UserGuide/V0.13.x/Reference/SQL-Reference.html)). Not standard ANSI SQL.
- **Transactions:** None (no multi-statement ACID). Single insert atomicity only.
- **Native vs app-side:** Native time-series aggregation, down-sampling, FILL/interpolation, and built-in UDF framework; joins are limited (time-aligned across series) versus a general relational engine.
- **Stored procedures / UDFs:** User-Defined Functions (and triggers) in **Java**; built-in analytics/ML functions in newer versions.

## Scaling & topology
- **Horizontal** scale-out across DataNodes; partitioning by series family + time range with consistent-hashing placement ([SIGMOD 2023 paper](https://sxsong.github.io/doc/23sigmod-iotdb.pdf)). Resharding/rebalancing is managed by ConfigNode. ⚠️ unverified — operational pain of live resharding not well documented in primary sources.
- **Read replicas / read consistency:** Replicas come from the consensus group. Under **IoTConsensus**, replica reads can be stale (eventual/session consistency); under Ratis, reads are strongly consistent ([Timecho consensus](https://www.timecho-global.com/archives/apache-iotdb-distributed-architecture-3-replication-and-consensus-algorithms)).
- **Storage/compute separation:** No — DataNodes are storage + compute (shared-nothing). Not an Aurora/Snowflake-style design. See [storage-compute-separation](../concepts/storage-compute-separation.md).
- **ConfigNode count must be 1 or 3** (two has no quorum HA; more than three loses performance) ([cluster deployment](https://iotdb.apache.org/UserGuide/latest/Deployment-and-Maintenance/Cluster-Deployment_apache.html)).

## Performance & durability
- **Write path:** Each insert is appended to a **REDO-only WAL** before the MemTable; MemTables flush to TsFiles when appropriate, after which the corresponding WAL is reclaimed (continuous WAL recycle, no explicit checkpoint) ([dbdb.io](https://dbdb.io/db/iotdb)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Data-loss window on crash:** Depends on **WAL fsync mode** (sync vs periodic-flush). With async/periodic WAL flushing, recently buffered writes can be lost on crash; with IoTConsensus async replication, an un-replicated write on a failed leader can also be lost. ⚠️ unverified — exact default fsync policy varies by version; confirm `wal_mode`/sync settings for your release.
- **Throughput/latency:** Designed for very high ingest of narrow time-series rows; columnar encoding keeps storage small and scans fast. Vendor/benchmark sources (BenchANT, vendor blogs) report strong ingest numbers — treat as ⚠️ marketing-adjacent; p99/tail behavior under compaction is not well characterized in independent sources.
- **Compaction:** Background compaction merges TsFiles (normal, delayed/out-of-order, and tombstone files) to accelerate queries; like any LSM it competes for I/O and can affect p99 during heavy merges. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).

## Operations & maturity
- **Backup/restore:** Snapshot/export tooling and maintenance commands exist ([maintenance command docs](https://iotdb.apache.org/UserGuide/V0.13.x/Maintenance-Tools/Maintenance-Command.html)). ⚠️ unverified — robust PITR semantics on the data path are not clearly documented.
- **Observability:** Metrics framework (Prometheus-compatible), `EXPLAIN`/query plans, and cluster management tooling.
- **Upgrade story:** Rolling cluster ops are supported in the 1.x ConfigNode/DataNode architecture; the 0.x → 1.x migration was a major architectural break. ⚠️ unverified — confirm version-to-version rolling-upgrade support before relying on zero downtime.
- **Maturity:** Top-Level Apache project (graduated 2020), originated at Tsinghua University (2017), backed commercially by Timecho. Published peer-reviewed papers ([VLDB 2020](https://www.vldb.org/pvldb/vol13/p2901-wang.pdf), [SIGMOD 2023](https://sxsong.github.io/doc/23sigmod-iotdb.pdf), [TODS 2025](https://dl.acm.org/doi/full/10.1145/3726523)). **No public Jepsen report exists** — given the weak-consistency IoTConsensus data path, the lack of independent consistency testing is a real gap; do not assume linearizable data writes.

## Ecosystem & people
- **Canonical use cases:** Industrial IoT / IIoT telemetry, manufacturing, energy/grid, vehicles and intelligent transportation, edge-to-cloud sensor data with high cardinality and out-of-order arrivals; edge deployment on constrained hardware.
- **Anti-patterns:** General-purpose OLTP, anything needing multi-row ACID transactions, relational joins/normalized models, ad-hoc BI on non-time-series data, or strong cross-replica read-after-write on the time-series path. Wrong tool if you need a transactional system of record.
- **Drivers/connectors:** JDBC, native session API (Java/Python/C++/Go/etc.), Thrift; integrations with Kafka, Flink/Spark, Grafana, and MQTT ingestion. Edge-cloud sync supported.
- **Community/support:** Active ASF community; commercial support, managed/enterprise features, and the TimechoDB distribution from Timecho. Docs are reasonable but split across Apache and Timecho sites and across rapidly changing versions, which raises the learning curve.

## Licensing & cost
- **OSS license:** **Apache License 2.0** — permissive, no post-2018 relicensing. See [license-taxonomy](../concepts/license-taxonomy.md). The TsFile format is also Apache-licensed and a separate project.
- **Commercial:** **TimechoDB** is the vendor distribution with licensing/activation and enterprise features (security, ops tooling, additional consensus/cluster capabilities). Open-source IoTDB is fully self-managed.
- **Lock-in:** Low at the license level; some advanced features and managed convenience live in TimechoDB. TsFile being open mitigates data lock-in.
- **Cost model:** Self-hosted (your hardware) for OSS; TimechoDB is commercially licensed (per-vendor terms). No first-party serverless offering. ⚠️ unverified — current commercial pricing not published openly.

## Hardware / deployment
- **Resource profile:** Disk/IO-bound for ingest+compaction; memory for MemTables and query buffers. Working set need not fit in RAM (LSM + columnar on disk), but more RAM improves flush/query behavior.
- **Storage assumptions:** Local disk per DataNode; NVMe/SSD recommended for compaction-heavy workloads. Shared-nothing, not network-attached-storage-centric.
- **Footprint:** Runs standalone (single node), as a cluster (3C3D+), and on the **edge** (lightweight JVM deployment); TsFile can be used as a standalone embeddable file format. JVM-based (Java).
- **Deployment:** On-prem and container/Kubernetes deployments documented ([k8s docs](https://www.timecho.com/docs/UserGuide/latest/Deployment-and-Maintenance/Kubernetes_timecho.html)); no first-party public SaaS. StatefulSet-style per-node persistence.

## Bottom line
Reach for Apache IoTDB when you have industrial/IoT time-series at scale — high-frequency sensor telemetry, edge-to-cloud, out-of-order arrivals — and want an Apache-licensed, columnar, write-optimized store with open file format (TsFile) and the flexibility to dial consistency per data type. Do not reach for it as a general database: there are **no multi-row transactions**, joins are limited, and the high-throughput default (IoTConsensus) gives only **eventual/session consistency** on the data path. The single biggest gotcha: the "serializable"/strong-consistency language applies to metadata (Ratis), not necessarily to your time-series writes — and there is no independent Jepsen verification, so do not assume linearizable, durable-on-ack data writes without testing your own WAL/consensus configuration.

## Sources
- [Apache IoTDB website / docs](https://iotdb.apache.org/)
- [SIGMOD 2023: Apache IoTDB — A Time Series Database for IoT Applications (PDF)](https://sxsong.github.io/doc/23sigmod-iotdb.pdf)
- [VLDB 2020: Apache IoTDB — Time-series Database for IoT (PDF)](https://www.vldb.org/pvldb/vol13/p2901-wang.pdf)
- [TODS 2025: Apache IoTDB for Large Scale IoT Applications](https://dl.acm.org/doi/full/10.1145/3726523)
- [VLDB 2025: Improving Time Series Data Compression in Apache IoTDB (PDF)](https://www.vldb.org/pvldb/vol18/p3406-tang.pdf)
- [Timecho: Distributed Architecture — Replication & Consensus](https://www.timecho-global.com/archives/apache-iotdb-distributed-architecture-3-replication-and-consensus-algorithms)
- [Cluster Deployment docs](https://iotdb.apache.org/UserGuide/latest/Deployment-and-Maintenance/Cluster-Deployment_apache.html)
- [Table-model Query docs](https://iotdb.apache.org/UserGuide/latest-Table/Basic-Concept/Query-Data_apache.html)
- [SQL Reference](https://iotdb.apache.org/UserGuide/V0.13.x/Reference/SQL-Reference.html)
- [Apache TsFile (GitHub)](https://github.com/apache/tsfile)
- [Database of Databases — IoTDB](https://dbdb.io/db/iotdb)
