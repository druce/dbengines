---
name: Apache Flink
slug: apache-flink
rank: 41
data_model: Relational (stream processing)
license: Apache License 2.0 (permissive)
summary: Stateful stream-processing engine with exactly-once semantics and SQL; a compute engine, not a database — it processes streams and externalizes state.
last_researched: 2026-06-04
confidence: high
---

# Apache Flink

> A distributed stateful stream-processing engine that provides exactly-once-effect guarantees over unbounded data via checkpointed snapshots — not a database you query, but a compute layer that consumes, transforms, and emits streams.

## When to use

**Use Apache Flink if:**
- ✅ You need stateful, exactly-once stream processing at scale (continuous ETL, event-driven apps, CEP, CDC, streaming lakehouse)
- ✅ You need event-time semantics with watermarks to handle out-of-order/late data correctly
- ✅ You need native stateful joins, windowed/continuous aggregations, dedup, top-N, or pattern matching over unbounded data
- ✅ Your team can absorb the operational complexity (checkpoint tuning, state management, savepoint-based upgrades)

**Avoid Apache Flink if:**
- ❌ You expect "exactly-once" to be automatic — it's effectively-once and only end-to-end if sources are replayable and sinks are transactional/idempotent (biggest gotcha)
- ❌ You want a database to query or serve reads — it owns no data of record; point a sink store at it instead
- ❌ You need ad-hoc interactive OLAP — use ClickHouse/Pinot/Druid downstream
- ❌ You only need simple at-least-once Kafka transforms — Kafka Streams or a lighter tool suffices and Flink is operationally heavy for small teams

## Identity
- **Taxonomy / data model:** Stream-processing engine, not a storage engine. It is listed by db-engines under "relational" because of its SQL/Table API surface, but it has **no primary persistent store of record** — it reads from and writes to external systems (Kafka, Pulsar, JDBC, object stores, [apache-paimon](apache-paimon.md)/Iceberg). Treat it as a compute engine adjacent to the database space.
- **Storage model:** State is the only thing Flink durably owns. State backends: heap (HashMapStateBackend) or embedded RocksDB ([lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM-tree) on local disk for state larger than RAM. Flink 2.0 (March 2025) added **disaggregated state** via the **ForSt** store, keeping primary state in remote DFS/object storage with local disk as cache ([Flink 2.0 release](https://flink.apache.org/2025/03/24/apache-flink-2.0.0-a-new-era-of-real-time-data-processing/); [VLDB 2025 paper](https://www.vldb.org/pvldb/vol18/p4846-mei.pdf)). See [storage-compute-separation](../concepts/storage-compute-separation.md).
- **Workload:** Streaming (continuous, unbounded) plus bounded batch over the same runtime (unified batch/stream API). It is not OLTP and not an interactive OLAP query engine — it is a long-running dataflow processor. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Largely N/A in the classic DB sense — Flink is not a replicated store serving reads. Its correctness model is about **end-to-end processing guarantees**, not serving consistency. The JobManager coordinates checkpoints; on partition/failure the job halts and recovers from the last checkpoint rather than serving stale or divergent data. See [cap-pacelc](../concepts/cap-pacelc.md) for why CAP is the wrong frame here.
- **Processing guarantee:** **exactly-once *state* semantics** by default via Chandy-Lamport-style asynchronous barrier snapshots ([Lightweight Asynchronous Snapshots paper](https://arxiv.org/abs/1506.08603)); end-to-end exactly-once *output* requires transactional/idempotent sinks (e.g. Kafka transactions, two-phase-commit sink). Without such a sink you get at-least-once output even if state is exactly-once ([checkpointing docs](https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state_backends/)). "Exactly-once" here means **effectively-once**, not that each record is physically processed once.
- **Isolation:** N/A — no multi-statement transactions over a stored dataset; the [isolation-levels](../concepts/isolation-levels.md) concept does not apply. Flink CDC pipelines preserve source ordering and exactly-once via checkpoints ([Flink CDC FAQ](https://nightlies.apache.org/flink/flink-cdc-docs-master/docs/faq/faq/)).
- **Replication:** N/A for data-of-record. For availability: JobManager HA via ZooKeeper or Kubernetes leader election; TaskManager failure triggers full or regional restart from checkpoint. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** Checkpoint mode is configurable EXACTLY_ONCE vs AT_LEAST_ONCE (lower latency, no barrier alignment).
- **Clock dependency:** Correctness does not depend on synchronized wall clocks; it uses **event-time** semantics with **watermarks** to handle out-of-order/late data, and the watermark contract (not physical clocks) drives windowing. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schema-on-read at the source. The Table/SQL API is schema-on-write at the logical level (you declare table schemas in the catalog), but Flink does not own the physical data. DataStream API is typed via Java/Scala/Python generics.
- **Migration/evolution:** **State schema evolution** is supported for POJO/Avro state types (add/remove/rename fields with rules); arbitrary type changes require savepoint migration tooling and are a known operational pain. Job/topology changes require a savepoint, code change, and restart from savepoint.
- **Type system:** Rich SQL types incl. nested rows, maps, arrays, multisets, timestamps with event-time attributes, intervals, and DECIMAL. No native geospatial or vector types in core.

## Query interface
- **Language:** Multiple layered APIs — Flink **SQL** (ANSI-leaning streaming SQL with windowing/MATCH_RECOGNIZE/temporal joins), the **Table API**, the **DataStream API** (Java/Scala/Python via PyFlink), and the low-level ProcessFunction. Streaming SQL semantics differ from batch SQL (continuous queries emit retractions/updates).
- **Transactions:** No interactive multi-statement ACID. Atomicity is at the **checkpoint** boundary; sink transactions (2PC) give end-to-end atomic output.
- **Native vs app-side:** Native stateful joins (interval, temporal/versioned-table, regular streaming joins), windowed and continuous aggregations, deduplication, top-N, pattern matching (CEP). Joins over large keyspaces are stateful and memory/disk-heavy.
- **Stored procedures / UDFs:** Scalar/table/aggregate UDFs in Java, Scala, Python; user-defined sources/sinks/catalogs.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal. Jobs are dataflow graphs split into operator subtasks across TaskManager slots; **parallelism** is set per operator/job.
- **Sharding/partitioning:** Keyed streams partition state by key (hash). **Rescaling** redistributes key-groups; changing parallelism requires a savepoint/restore (not online), which is a real operational cost for large state.
- **Read replicas / read consistency:** N/A — Flink does not serve reads; outputs are pushed to sinks.
- **Storage/compute separation:** Pre-2.0, state was coupled to local disk, making rescaling and checkpointing expensive at TB scale. Flink **2.0 disaggregated state (ForSt)** decouples state to remote DFS with local cache, targeting cloud-native elasticity ([Flink 2.0](https://flink.apache.org/2025/03/24/apache-flink-2.0.0-a-new-era-of-real-time-data-processing/)). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** Durability = periodic **checkpoints** (asynchronous barrier snapshots) to durable storage (HDFS/S3/GCS). **Data-loss window on crash = work since the last successful checkpoint** is reprocessed from replayable sources (e.g. Kafka offsets); no data is lost if sources are replayable and sinks are transactional. RocksDB backend supports **incremental checkpoints** (only changed SST files), dramatically cutting checkpoint time for large state. There is no per-record WAL in the database sense — see [wal-and-durability](../concepts/wal-and-durability.md) for contrast.
- **Throughput/latency:** Designed for millions of events/sec with low latency; **sub-second to low-ms** latency in AT_LEAST_ONCE / unaligned-checkpoint configs, higher under EXACTLY_ONCE barrier alignment. Backpressure propagates upstream automatically.
- **p99 / GC:** Tail latency is dominated by **checkpoint stalls** (barrier alignment, large-state snapshotting) and JVM GC on the heap backend. RocksDB compaction and incremental checkpoints mitigate large-state spikes; long checkpoints under backpressure are a classic production failure mode. ForSt/disaggregated state aims to reduce checkpoint-induced p99 spikes.

## Operations & maturity
- **Backup/restore:** **Savepoints** (manual, portable, self-contained) for upgrades/migrations; **checkpoints** (automatic, for recovery). Restart-from-savepoint is the upgrade and rescale mechanism. No PITR in the relational-DB sense — recovery is to checkpoint/savepoint boundaries.
- **Observability:** Web UI with job graph, backpressure, checkpoint stats; metrics via Prometheus/JMX/etc.; SQL EXPLAIN for plans. Slow/large checkpoints are the key thing to watch.
- **Upgrade story:** Stop-with-savepoint, deploy new version, restore — i.e. a controlled restart, not zero-downtime in general. State compatibility across major versions can require migration. Flink 2.0 removed long-deprecated APIs (DataSet API, legacy state backends), a breaking change for old jobs.
- **Maturity:** Very mature (since 2014, top-level ASF; 1.0 in 2016, 2.0 in 2025), heavily used at Alibaba, Netflix, Uber, etc. **No published external Jepsen report** (jepsen.io) exists, and one would be of limited relevance since Flink is not a replicated store — its guarantees are about deterministic replay from checkpoints, not distributed register linearizability. (Flink does ship an in-tree [`flink-jepsen`](https://github.com/apache/flink/blob/master/flink-jepsen/README.md) test suite built on the Jepsen framework that fault-injects job-availability tests in CI — distinct from a formal published analysis.) ⚠️ unverified — no formal-verification result of the snapshot algorithm's implementation is publicly published, though the underlying ABS algorithm is well-studied academically.
- **Known failure modes:** checkpoint timeouts under backpressure, state too large for local disk, savepoint incompatibility after code changes, skewed keys causing hot subtasks, RocksDB memory misconfiguration.

## Ecosystem & people
- **Canonical use cases:** real-time ETL/streaming pipelines, event-driven applications, streaming analytics/aggregations, fraud/anomaly detection (CEP), CDC ingestion ([Flink CDC](../concepts/change-data-capture.md)), and the **streaming lakehouse** with [apache-paimon](apache-paimon.md) and Iceberg.
- **Anti-patterns:** **not** a serving database — do not point a dashboard or app at Flink for point lookups (use a sink store like a KV/OLAP DB). Not for ad-hoc interactive OLAP (use [clickhouse](clickhouse.md)/[apache-pinot](apache-pinot.md)/[apache-druid](apache-druid.md) downstream). Overkill for simple at-least-once Kafka transforms where [Kafka Streams](../concepts/streaming-databases.md) or a lighter tool suffices; operationally heavy for small teams.
- **Connectors:** Kafka, Pulsar, Kinesis, JDBC, filesystems/object stores, Elasticsearch, Cassandra, HBase, Iceberg, Paimon, Hudi; Flink CDC for MySQL/Postgres/SQL Server/Oracle/MongoDB.
- **Community/support:** Large ASF community; commercial support and managed offerings from **Ververica** (original creators), **Confluent** (managed Flink), **Amazon Managed Service for Apache Flink** (ex-Kinesis Data Analytics), Alibaba Cloud Realtime Compute. Docs are thorough but the learning curve (event time, watermarks, state, checkpoint tuning) is steep.

## Licensing & cost
- **License:** **Apache License 2.0**, permissive — no post-2018 relicensing, no SSPL/BSL concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Fully self-hostable; numerous managed options (Confluent, AWS, Alibaba, Ververica). Lock-in risk is low at the engine level (open API), higher if you adopt a vendor's managed control plane or proprietary connectors.
- **Cost model:** Self-managed cost = compute (TaskManager/JobManager) + durable checkpoint storage. Managed services bill per-compute-unit / per-CFU / per-hour. Cost scales with parallelism and state size; large stateful jobs with frequent checkpoints to object storage incur real storage/IO cost.

## Hardware / deployment
- **Resource profile:** CPU- and memory-bound for compute; **disk-bound for large RocksDB state**. Heap backend needs working set in RAM; RocksDB backend spills to local disk; disaggregated/ForSt shifts primary state to remote storage with local cache. Network throughput matters for shuffles and checkpoints.
- **Storage assumptions:** Local NVMe/SSD strongly recommended for RocksDB state; durable checkpoints to HDFS/S3/GCS. Disaggregated state tolerates network-attached/object storage as primary.
- **Footprint:** Clustered/distributed (Standalone, YARN, **Kubernetes** native + Flink Kubernetes Operator). Not embedded, not serverless in the core (managed vendors layer serverless on top).
- **Deployment:** On-prem or any cloud; strong Kubernetes story (Operator manages JobManager/TaskManager, HA, savepoints). StatefulSet-style local disk for RocksDB is the typical pattern; checkpoint storage must be durable and shared.

## Bottom line
Reach for Flink when you need **stateful, exactly-once stream processing at scale** — continuous ETL, event-driven apps, CEP, CDC, or a streaming lakehouse — and you can absorb its operational complexity (checkpoint tuning, state management, savepoint-based upgrades). Do **not** reach for it as a database to query or serve reads; it owns no data of record and is a compute engine that pushes results to sinks. The single biggest gotcha: "exactly-once" is **effectively-once and only end-to-end if your sources are replayable and your sinks are transactional/idempotent** — otherwise you get at-least-once output, and large-state checkpointing under backpressure is the operational cliff most teams hit.

## Sources
- [Apache Flink 2.0.0 release announcement (Mar 2025)](https://flink.apache.org/2025/03/24/apache-flink-2.0.0-a-new-era-of-real-time-data-processing/)
- [State Backends — Apache Flink docs](https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state_backends/)
- [Disaggregated State Management — Apache Flink docs](https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/disaggregated_state/)
- [Disaggregated State Management in Apache Flink 2.0 — VLDB 2025 paper](https://www.vldb.org/pvldb/vol18/p4846-mei.pdf)
- [Using RocksDB State Backend in Apache Flink — Flink blog](https://flink.apache.org/2021/01/18/using-rocksdb-state-backend-in-apache-flink-when-and-how/)
- [Flink CDC FAQ (consistency/exactly-once)](https://nightlies.apache.org/flink/flink-cdc-docs-master/docs/faq/faq/)
