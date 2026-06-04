---
name: Apache Accumulo
slug: apache-accumulo
rank: 108
data_model: Wide-column
license: Apache License 2.0 (permissive)
summary: BigTable-style wide-column store on HDFS, distinguished by per-cell visibility labels for fine-grained security; NSA-born, government/intel niche.
last_researched: 2026-06-04
confidence: medium
---

# Apache Accumulo

> A Google BigTable clone built on Hadoop/HDFS whose one differentiating feature is cell-level (column-visibility) access control — pick it for classified/multi-tenant data on a Hadoop stack, not for general use.

## When to use

**Use Apache Accumulo if:**
- ✅ You must enforce per-cell access control via security labels (column visibility) — its genuine, near-unique strength.
- ✅ You store large, sparse data on an existing Hadoop/HDFS stack and have ZooKeeper/HDFS operational expertise.
- ✅ You need massive-scale indexing/search over sparse data (e.g. GeoMesa, Apache Fluo) with strong per-row (CP) consistency.

**Avoid Apache Accumulo if:**
- ❌ You don't specifically need cell-level security — HBase, Cassandra, or ScyllaDB are better-supported choices.
- ❌ You need SQL, joins, or multi-row transactions — "atomic" means single-row only, with no independent Jepsen verification.
- ❌ You have a small dataset or no Hadoop/HDFS/ZooKeeper team — there is no managed offering and cluster overhead is unjustified.

## Identity
- **Taxonomy / data model:** Wide-column store, a near-direct clone of [Google BigTable](https://accumulo.apache.org/docs/2.x/getting-started/design). Keys are 5-tuples: Row ID, Column Family, Column Qualifier, **Column Visibility**, and Timestamp; values are opaque bytes. A sparse, sorted, multi-dimensional map. The Visibility element (a boolean expression of security labels) is the headline differentiator over [apache-hbase](apache-hbase.md) and BigTable. See [wide-column](../concepts/wide-column.md).
- **Storage model:** [LSM-tree](../concepts/lsm-vs-btree.md). Writes hit a [WAL](../concepts/wal-and-durability.md) then an in-memory MemTable; minor compaction flushes sorted runs to **RFiles** (an ISAM-style indexed format with data/index/metadata blocks) stored in HDFS. Reads merge the MemTable with on-disk RFiles. Major compaction merges RFiles. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP-ish at the API level (low-latency point gets/puts, range scans), but the canonical use is large-scale indexing/search over sparse data. Not an analytics engine (no SQL, no columnar OLAP). Not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP**. Each tablet is served by exactly one TabletServer at a time, with assignment arbitrated through ZooKeeper locks; a partitioned-off TabletServer loses its lock and its tablets are reassigned, so the system favors consistency/single-writer over availability. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no formal PACELC statement exists. In practice: under partition it sacrifices availability (PC); else, because each tablet has a single server and a write returns only after WAL sync, it favors consistency over latency (EC). Treat as inference, not a vendor claim.
- **Default isolation & what's achievable:** No multi-row transactions. A single **Mutation** is an atomic, isolated set of changes **to one row** ([Mutation API](https://accumulo.apache.org/docs/2.x/apidocs/org/apache/accumulo/core/data/Mutation.html)). **Conditional Mutations** (since 1.6) give atomic read-modify-write on a single row by holding a server-side row lock while checking value/absence conditions ([API docs](https://accumulo.apache.org/docs/2.x/apidocs/index-all.html)). There is no cross-row ACID, no snapshot isolation, no serializable multi-key transactions — do not read "atomic" as transactional. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Durability and replication are delegated to **HDFS** (typically 3x block replication); Accumulo itself runs one TabletServer per tablet (single-leader-per-shard, no Accumulo-level replica serving). Cross-instance replication for DR exists but is a separate, coarser mechanism. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Not Dynamo-style per-query consistency. Tunable **durability** instead (see Performance). Visibility-based reads always reflect the single authoritative tablet copy.
- **Clock dependency:** Timestamps order versions of a key and drive version-based deletes/conflict resolution. ⚠️ unverified — correctness does not appear to depend on synchronized wall clocks the way Spanner/TrueTime does, but skewed timestamps can mis-order versions. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Tables are defined, but columns/qualifiers are arbitrary per row — no fixed column schema; the application interprets bytes. Column families can be grouped into **locality groups** for column-oriented read efficiency.
- **Migration/evolution:** Adding columns/qualifiers needs no DDL. Per-table config (iterators, locality groups, visibility constraints, splits) is set online without downtime; no rigid `ALTER`-and-lock model because there is no rigid schema.
- **Type system:** None — keys and values are byte arrays. No native JSON, geospatial, or vector types. Structure and typing live entirely in application code (and in iterator logic).

## Query interface
- **Language:** **API-only** (Java client primarily; Thrift proxy for other languages). No SQL, no declarative query language. Access is via Scanner/BatchScanner (range scans) and BatchWriter (bulk writes). SQL access requires external layers (e.g. Presto/Trino connectors, or projects like [Apache Fluo] / Geomesa on top).
- **Transactions:** Single-row atomicity only; conditional mutations for single-row CAS. No multi-statement ACID.
- **Native vs app-side:** No native secondary indexes (you build index tables yourself), no joins, no aggregations in the query layer. Server-side **Iterators** push computation to TabletServers — combiners (sums/aggregates over versions), filters, and visibility enforcement run during scans and compactions, roughly equivalent to a MapReduce combiner.
- **Stored procedures / UDFs:** Iterators are the UDF mechanism, written in **Java** and deployed to every TabletServer's classpath.

## Scaling & topology
- **Horizontal.** Tables split into **tablets** on row boundaries; tablets auto-split as they grow and are auto-distributed/rebalanced across TabletServers by the Manager. Sharding is automatic and online — resharding is far less painful than manual-shard systems because splitting is a built-in continuous operation.
- **Partitioning:** Range-partitioned by row key (sorted). All columns/values for a given row stay in one tablet, so single-row operations are local. Designing row keys to avoid hotspots is the main scaling discipline.
- **Read replicas:** None at the Accumulo layer — one TabletServer owns each tablet. Read scaling comes from spreading tablets, not from replicas. (Durability replication is HDFS's job.)
- **Storage/compute separation:** Partial — TabletServers (compute) are decoupled from HDFS DataNodes (storage), though they are typically colocated for data locality. Not a Snowflake/Aurora-style elastic separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Write → WAL in HDFS → MemTable. Group commit batches WAL syncs. **Tunable durability** per table/write via `table.durability` and the `Durability` enum ([durability blog](https://accumulo.apache.org/blog/2016/11/02/durability-performance.html)): `sync` (fsync to persistent storage — default, max durability), `flush` (push to remote HDFS servers' memory but maybe not disk), `log` (WAL without forced flush), `none` (skip WAL entirely — data-loss window = everything in MemTable on crash). Default `sync` ≈ no data-loss window on single-node crash since WAL is in replicated HDFS. **Gotcha:** group commit picks the *most durable* setting among concurrently committing writes, so a `sync` write can slow down `none`/`flush` writes sharing the commit ([durability blog](https://accumulo.apache.org/blog/2016/11/02/durability-performance.html)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Designed for very high ingest; published benchmarks demonstrate massive aggregate insert rates on large clusters ([D4M 100M inserts/sec paper](https://arxiv.org/pdf/1406.4923); [Accumulo benchmarking 2.1](https://accumulo.apache.org/papers/accumulo-benchmarking-2.1.pdf)). p99 read/write tails are dominated by HDFS, JVM GC, and compaction activity. ⚠️ unverified — no canonical p99 figures; tail behavior is cluster- and tuning-dependent.
- **Compaction / GC:** LSM minor (MemTable→RFile) and major (RFile merge) compactions consume disk/CPU IO and create p99 latency spikes typical of LSM stores. Runs on the JVM, so GC pauses add tail latency. A separate GC process reclaims unreferenced files in HDFS.

## Operations & maturity
- **Backup/restore:** No turnkey PITR. Mechanisms include table exports, bulk-import of RFiles, HDFS snapshots, and cross-instance replication. Operationally hands-on. ⚠️ unverified — no managed PITR feature comparable to RDBMS.
- **Observability:** Built-in Monitor web UI, metrics (Hadoop metrics2 / Micrometer in 2.x), and per-tablet/ingest stats. No SQL EXPLAIN (no query planner); performance debugging is at the iterator/scan/compaction level.
- **Upgrade story:** Tied to the Hadoop/ZooKeeper ecosystem version matrix; major upgrades (e.g. 1.x→2.x) involve schema/metadata migration steps and are not trivially rolling. Day-2 burden is high: you operate HDFS, ZooKeeper, and Accumulo together.
- **Maturity:** Originated at the **NSA (2008) as an independent clone of Google BigTable** (not a fork of HBase — HBase was new/unproven when NSA started; Accumulo's differentiator was cell-level security), open-sourced to Apache as an incubator project in 2011, top-level project since 2012 ([Wikipedia](https://en.wikipedia.org/wiki/Apache_Accumulo)). Mature and battle-tested in U.S. government/intelligence and large enterprises, but a comparatively small community. **No published [Jepsen](https://jepsen.io) report exists** as of this writing; correctness evidence comes from its own Continuous Ingest / RandomWalk test suites ([accumulo-testing](https://github.com/apache/accumulo-testing)), not independent formal verification — treat distributed-consistency claims accordingly.

## Ecosystem & people
- **Canonical use cases:** Massive sparse indexes; data lakes/search over Hadoop where **cell-level security / multi-level classification** is a hard requirement (the reason it exists). Backs projects like GeoMesa (spatio-temporal) and Apache Fluo (incremental processing).
- **Anti-patterns:** General-purpose app database; anything needing SQL, joins, or multi-row transactions; analytics/BI (use a columnar OLAP store); teams without existing Hadoop/HDFS/ZooKeeper operational expertise; small datasets (the cluster overhead is unjustified). If you don't specifically need column-visibility security, [apache-hbase](apache-hbase.md), [apache-cassandra](apache-cassandra.md), or [scylladb](scylladb.md) are usually better-supported choices.
- **Connectors:** Java/Thrift clients; Trino/Presto connector for SQL access; integrates with Spark/MapReduce via input/output formats. Weaker CDC/Kafka/dbt/BI tooling than mainstream databases.
- **Community:** Small but active Apache community; commercial support is limited (historically via vendors in the gov/defense space). Docs are solid but assume Hadoop fluency. Steep learning curve.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing drama (contrast with source-available shifts elsewhere). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Effectively **self-managed** — there is no mainstream first-party managed Accumulo SaaS; you run it on your own Hadoop cluster (on-prem or cloud IaaS). No proprietary-extension lock-in (it's all ASF), but operational lock-in to the Hadoop stack is real.
- **Cost model:** Cost is your cluster: nodes for TabletServers + HDFS DataNodes + ZooKeeper ensemble. Cheap on small clusters is not the point — it's built for big clusters where the fixed Hadoop overhead amortizes. At scale, cost tracks node count and HDFS storage (3x replication).

## Hardware / deployment
- **Resource profile:** Memory- and IO-bound. TabletServers want large heaps for MemTables/caches (mind JVM GC); reads benefit when hot data fits in cache, but full dataset need not fit in RAM (it's an on-disk LSM over HDFS). Compaction is CPU/IO heavy.
- **Storage assumptions:** Built for commodity disks via HDFS; NVMe/SSD helps WAL sync and compaction throughput. Assumes a healthy, low-latency HDFS — network-attached/cloud-object storage works only via HDFS-compatible layers and may hurt latency.
- **Footprint:** **Clustered only** — minimum viable deployment is HDFS + ZooKeeper + Manager + TabletServer(s). Not embeddable, not serverless, not single-node-friendly for production.
- **Deployment:** Traditionally on-prem Hadoop; runnable on k8s but with full StatefulSet realities for HDFS/ZooKeeper/TabletServers. Heavyweight to stand up.

## Bottom line
Reach for Accumulo if you must store large, sparse data on a Hadoop stack **and** require per-cell access control with security labels (its genuine, somewhat unique strength, born of NSA requirements). Everyone else should not: it has no SQL, no multi-row transactions, a heavy Hadoop/ZooKeeper operational footprint, no managed offering, and a small community. The single biggest gotcha is that "atomic" means **single-row only** — there are no cross-row transactions and no independent Jepsen verification of its distributed consistency.

## Sources
- [Accumulo Design (official docs, 2.x)](https://accumulo.apache.org/docs/2.x/getting-started/design)
- [Accumulo Features (official docs, 2.x)](https://accumulo.apache.org/docs/2.x/getting-started/features)
- [Mutation API (2.1.4)](https://accumulo.apache.org/docs/2.x/apidocs/org/apache/accumulo/core/data/Mutation.html) and [API index (conditional mutations, durability)](https://accumulo.apache.org/docs/2.x/apidocs/index-all.html)
- [Durability Performance Implications (Accumulo blog)](https://accumulo.apache.org/blog/2016/11/02/durability-performance.html)
- [Security / Column Visibility (user manual)](https://accumulo.apache.org/1.4/user_manual/Security.html)
- [Benchmarking the Apache Accumulo Distributed Key–Value Store (2.1)](https://accumulo.apache.org/papers/accumulo-benchmarking-2.1.pdf)
- [Achieving 100,000,000 inserts/sec with Accumulo and D4M (arXiv)](https://arxiv.org/pdf/1406.4923)
- [apache/accumulo-testing (Continuous Ingest / RandomWalk)](https://github.com/apache/accumulo-testing)
- [Apache Accumulo (Wikipedia — history/origin)](https://en.wikipedia.org/wiki/Apache_Accumulo)
