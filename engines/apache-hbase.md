---
name: Apache HBase
slug: apache-hbase
rank: 31
data_model: Wide-column
license: Apache License 2.0 (permissive)
summary: Bigtable-style wide-column store on HDFS; strongly consistent per row, CP, operationally heavy.
last_researched: 2026-06-04
confidence: high
---

# Apache HBase

> Open-source clone of Google Bigtable: a horizontally-scalable sparse wide-column store layered on HDFS, strongly consistent per region (CP) but with a heavy, ZooKeeper/HDFS-dependent operational footprint and no SQL or multi-row transactions out of the box.

## When to use

**Use Apache HBase if:**
- ✅ You have truly large (TB–PB), key-accessed, sparse data already living in a Hadoop/HDFS world.
- ✅ You need strong per-row consistency (CP) with high write throughput and range scans by row key.
- ✅ You have a platform team to run HDFS + ZooKeeper + JVM GC tuning (and Phoenix for SQL on top).

**Avoid Apache HBase if:**
- ❌ Your row keys are monotonic/sequential without salting — hotspotting one RegionServer is the classic failure mode.
- ❌ You need ad-hoc SQL, joins, native secondary indexes, or multi-row ACID transactions.
- ❌ You have small/medium data or a low-ops/serverless team — the operational tax is enormous.

## Identity
- **Taxonomy / data model:** Wide-column store ([wide-column](../concepts/wide-column.md)), a near-direct implementation of the [Google Bigtable](https://research.google/pubs/pub27898/) model. Data is a sparse, distributed, multidimensional sorted map keyed by `(row key, column family, column qualifier, timestamp/version)`. No relational model, no native joins.
- **Storage model:** [LSM-tree](https://lsm-vs-btree) — writes hit an in-memory MemStore + WAL, flush to immutable **HFiles** on HDFS, merged by background compaction. See [lsm-vs-btree](../concepts/lsm-vs-btree.md), [columnar-storage](../concepts/columnar-storage.md). Column-family-oriented on disk (each family is a separate set of HFiles), so it is *column-family* partitioned rather than true columnar.
- **Workload:** OLTP-ish random read/write on huge tables and high-volume sequential scans; **not** an analytical/SQL engine on its own. Best at billions of rows with point lookups and range scans by row key. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). HTAP: N/A — pair with Phoenix or Spark for query, or replicate to a column store for analytics.

## Distribution & consistency
- **CAP under partition:** **CP**. Each region is served by exactly one RegionServer (single-homing), so reads/writes for a row go through one serializing node. If that RegionServer or its ZooKeeper session dies, its regions are **unavailable** until reassigned and WAL replayed (MTTR commonly ~minutes; tunable toward <2 min) ([HBase reference guide / fault tolerance](https://hbase.apache.org/book.html)). It sacrifices availability to keep consistency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PC/EC — consistent under partition; in normal operation it also favors consistency (single-homed reads from the authoritative RegionServer) over latency, unless you opt into timeline-consistent reads (below).
- **Default isolation & what's achievable:** **Read committed**, explicitly ([HBase ACID semantics](https://hbase.apache.org/acid-semantics.html)). Atomicity is **single-row only** — a `put`/`delete` over multiple column families in one row is atomic; multi-row mutations are **not** atomic ("a multiput on rows a,b,c may mutate some but not all"). Scans are **not** snapshot-isolated ("Scans do not exhibit snapshot isolation") ([ACID semantics](https://hbase.apache.org/acid-semantics.html)). `checkAndPut`/`checkAndDelete` give per-row CAS. Calling this "ACID" is misleading: it is durable + per-row atomic + read-committed, with no multi-row transactions.
- **Replication:** Durability/HA come from **HDFS block replication** (default 3x), not a DB-level quorum — there is no leaderless or multi-leader write path. Cross-cluster async replication exists for DR/geo. ZooKeeper provides coordination and HMaster election. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes, limited: **timeline-consistent high-availability reads** (region replicas, `Consistency.TIMELINE`) let stale reads serve from secondary replicas during primary outage; default is `STRONG` ([timeline-consistent reads](https://devdoc.net/bigdata/hbase-0.98.7-hadoop1/book/arch.timelineconsistent.reads.html)).
- **Clock dependency:** Versions are timestamp-keyed; correctness of MVCC ordering is internal (sequence IDs), but cell version semantics and TTL rely on wall-clock timestamps you can also supply manually. Not TrueTime-style. See [clocks-and-time](../concepts/clocks-and-time.md), [mvcc](../concepts/mvcc.md).

## Schema
- **Schema-on-write vs read:** Hybrid. **Column families are schema-on-write** (declared up front, expensive to add/change, ideally few — 1-3); **columns/qualifiers within a family are schema-on-read** (created dynamically per row, sparse). Effective schema (qualifier names, value encoding) lives in app code.
- **Migration/evolution:** Adding/altering a column family requires an `alter` that historically took the table offline/disabled it; online operations have improved but family changes remain a heavy operation. Adding qualifiers is free.
- **Type system:** Everything is **uninterpreted byte arrays** (`byte[]`) for keys, qualifiers, and values. No native typing, JSON, arrays, geospatial, or vectors at the HBase layer — typing is imposed by clients (or by Phoenix on top).

## Query interface
- **Language:** **API-only** at the core — Java client (`Get`, `Put`, `Scan`, `Delete`), plus Thrift/REST gateways and a shell. No native SQL. **[Apache Phoenix](https://phoenix.apache.org/)** layers a SQL skin (compiles to scans + coprocessors) and adds strongly-consistent secondary indexes; **Apache Spark / Hive** integrations exist for batch.
- **Transactions:** Single-row atomic mutations + per-row CAS only; **no multi-statement / multi-row ACID transactions** natively. (Phoenix and the older Tephra/Trafodion projects add cross-row transactions on top, with caveats.)
- **Native vs app-side:** Joins and aggregations are **app-side** (or via Phoenix/Spark). **No native secondary indexes** — you build them via Phoenix or by maintaining a second table yourself. Server-side filters and **coprocessors** (observers/endpoints, akin to triggers + stored procedures) push computation to RegionServers.
- **Stored procedures / UDFs:** Coprocessors written in **Java** run in-process on RegionServers — powerful but can destabilize the server if buggy (they share the JVM).

## Scaling & topology
- **Vertical vs horizontal:** Designed for **horizontal** scale to thousands of nodes / petabytes — the canonical reason to choose it.
- **Sharding:** **Auto-sharding by row-key range into regions**; regions auto-split when they grow and are balanced across RegionServers. Resharding is automatic but **hotspotting on sequential/monotonic row keys** is the classic failure mode — you must design keys (salting, hashing) to spread load. Manual pre-splitting is common.
- **Read replicas:** Region replicas enable timeline-consistent (possibly stale) reads; default reads are single-homed and strongly consistent.
- **Storage/compute separation:** Partially — compute (RegionServers) is separate from storage (**HDFS**), and HBase-on-S3 (e.g. EMR) decouples further, but it is not a Snowflake/Aurora-style elastic design. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Write → **WAL** (on HDFS) + MemStore; ack after WAL append. fsync/durability is governed by the HDFS hflush/hsync path and the per-table/mutation `Durability` setting (SKIP_WAL/ASYNC_WAL/SYNC_WAL/FSYNC_WAL). **Data-loss window:** with deferred/async WAL or skip-WAL you can lose un-synced edits on crash; with SYNC/FSYNC the window narrows to HDFS durability semantics. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** High write throughput (LSM, sequential WAL); point reads can be fast from BlockCache/MemStore but cold reads touch multiple HFiles + HDFS. **p99 is the pain point** — GC pauses (large JVM heaps), compaction I/O, and region splits cause tail spikes. Off-heap BucketCache and hedged reads ([HBase performance docs](https://hbase.apache.org/docs/performance/)) are the documented levers for tail latency. ⚠️ unverified — AdaptiveLRU BlockCache (HBASE-23887) exists, but the previously cited "~3x p99 reduction" figure could not be confirmed against the official performance docs.
- **Compaction / GC:** Background **minor and major compactions** merge HFiles and reclaim tombstones/old versions; major compaction is I/O-heavy and a notorious p99 source — often scheduled off-peak. **In-memory compaction (Accordion)** reduces flush frequency and write amplification ([in-memory compaction](https://hbase.apache.org/docs/inmemory-compaction/)). JVM GC tuning is a permanent operational concern.

## Operations & maturity
- **Backup/restore, PITR:** Table **snapshots** (cheap, HDFS-level), `ExportSnapshot`, full/incremental backup tooling, and cross-cluster replication for DR. No true continuous PITR; you reconstruct from snapshots + WAL/replication.
- **Observability:** JMX metrics, per-RegionServer web UIs, the HBase Master UI, and integration with Hadoop monitoring. EXPLAIN-style plans only via Phoenix; slow ops surface in logs/metrics, not a polished slow-query log.
- **Upgrade story:** **Rolling upgrades** supported within compatible lines; major-version (e.g. 1.x→2.x) and HDFS/ZooKeeper coordination is a substantial project ([Salesforce HBase2/Phoenix5 upgrade paper](https://engineering.salesforce.com/wp-content/uploads/2023/12/SFDC-HBase2-Phoenix5-Paper-2023.pdf)). **Day-2 burden is high:** you operate HDFS + ZooKeeper + HBase + (often) Phoenix together.
- **Maturity:** Very mature (since ~2008), proven at extreme scale (Facebook Messages historically, many large enterprises). Known failure modes: **row-key hotspotting**, **GC-induced ZooKeeper session timeouts** causing region churn, slow MTTR on RegionServer loss, and major-compaction storms. **Jepsen:** ⚠️ unverified — no canonical Aphyr/Jepsen analysis of HBase is publicly known; its single-homed-region design makes strong per-row consistency architecturally straightforward rather than quorum-based.

## Ecosystem & people
- **Canonical use cases:** Massive sparse tables with key-based access — time-series/event logs, messaging/inbox stores, large-scale OLTP-ish lookups, serving layer for Hadoop pipelines, feature stores. **Anti-patterns:** small datasets (overkill — use a relational DB), workloads needing ad-hoc SQL/joins/secondary indexes (use a relational or [apache-cassandra](apache-cassandra.md) + materialized views, or add Phoenix), strict multi-row transactions, low-ops/serverless teams, and anything with monotonically increasing keys without salting.
- **Drivers/connectors:** Java/Thrift/REST clients; **Phoenix** (JDBC/SQL), **Spark**, **Hive**, **MapReduce**; CDC via WAL-based replication and tools; integrates with the broader Hadoop ecosystem.
- **Community & support:** Active Apache project; commercial support historically via Cloudera (CDP). Docs are thorough but dense; **learning curve and operational complexity are high** — expect a dedicated platform/ops team.

## Licensing & cost
- **License:** **Apache License 2.0**, fully permissive — no SSPL/BSL relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Mostly **self-managed** on Hadoop; managed offerings exist (AWS EMR HBase, Cloudera CDP, Azure HDInsight, Google Bigtable as a hosted Bigtable alternative — API-similar but not HBase). Low lock-in at the format/API layer; lock-in is really to the Hadoop operational stack.
- **Cost model:** No license fee; cost is **infrastructure + operations** — per-node (RegionServers, HDFS DataNodes, ZooKeeper) plus the human cost of running the stack. Economical at very large scale where per-GB storage on commodity disks dominates; expensive in operational overhead at small scale.

## Hardware / deployment
- **Resource profile:** **Memory- and disk-bound.** Large JVM heaps (BlockCache + MemStore) make it GC-sensitive; off-heap caching mitigates. Working set need not fit in RAM (LSM on HDFS), but cache hit rate drives p99.
- **Storage assumptions:** Sits on **HDFS**, traditionally local disks (HDD or NVMe) on DataNodes for data locality; can run on S3/object storage (EMR) at some latency/locality cost. Loss of data locality hurts read latency.
- **Footprint:** **Clustered** — minimum viable production cluster is multiple RegionServers + HDFS (NameNode + DataNodes) + a ZooKeeper quorum + HMaster(s) with backups. Not embedded, not serverless.
- **Deployment:** On-prem or cloud VMs; k8s deployment is possible but the HDFS/ZooKeeper StatefulSet realities (stable network identity, persistent volumes, data locality) make it operationally fiddly.

## Bottom line
Reach for HBase when you have **truly large** (TB–PB), key-accessed, sparse data already living in a Hadoop/HDFS world and you need strong per-row consistency with high write throughput. Do **not** reach for it for small/medium data, ad-hoc SQL/analytics, multi-row transactions, or if you lack a team to run HDFS + ZooKeeper + JVM GC tuning. The single biggest gotcha is **row-key design**: get it wrong and you hotspot one RegionServer; combined with GC-induced session timeouts and major-compaction storms, p99 and availability suffer despite the "strongly consistent" headline. For a more available, easier-to-operate alternative consider [apache-cassandra](apache-cassandra.md) (AP) or [scylladb](scylladb.md); for the managed Bigtable model, [google-cloud-bigtable](google-cloud-bigtable.md).

## Sources
- [HBase ACID semantics (official)](https://hbase.apache.org/acid-semantics.html)
- [HBase Reference Guide (official)](https://hbase.apache.org/book.html)
- [HBase Architecture docs](https://hbase.apache.org/docs/architecture/)
- [HBase Performance Tuning](https://hbase.apache.org/docs/performance/)
- [In-memory Compaction (Accordion)](https://hbase.apache.org/docs/inmemory-compaction/)
- [Timeline-consistent HA reads](https://devdoc.net/bigdata/hbase-0.98.7-hadoop1/book/arch.timelineconsistent.reads.html)
- [Apache Phoenix (SQL + secondary indexes)](https://phoenix.apache.org/)
- [Salesforce HBase2/Phoenix5 rolling upgrade paper (2023)](https://engineering.salesforce.com/wp-content/uploads/2023/12/SFDC-HBase2-Phoenix5-Paper-2023.pdf)
- [Google Bigtable paper (model HBase implements)](https://research.google/pubs/pub27898/)
