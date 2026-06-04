---
name: Apache Drill
slug: apache-drill
rank: 140
data_model: Multi-model (schema-free SQL query engine / federated)
license: Apache License 2.0 (permissive)
summary: Schema-free distributed SQL query engine that reads files and NoSQL stores in place; a query layer, not a database that stores or mutates data.
last_researched: 2026-06-04
confidence: high
---

# Apache Drill

> A distributed, schema-on-read SQL engine for querying JSON/Parquet/CSV files and NoSQL stores in place across S3/HDFS/Mongo/HBase — it executes queries, it does not durably own, mutate, or transact your data.

## Identity
- **Taxonomy / data model:** Federated SQL query engine, not a storage engine. Schema-free / schema-on-read over external data sources (files, HDFS, S3/GCS/Azure Blob, MongoDB, HBase, Hive, RDBMS via JDBC). Internally uses a hierarchical JSON-like document model so it can represent nested/dynamic data ([architecture](https://drill.apache.org/docs/architecture-introduction/)). Modeled after Google Dremel, like [apache-impala](apache-impala.md) and a sibling concept to [presto](presto.md)/[trino](trino.md).
- **Storage model:** No native on-disk format — Drill reads whatever the source provides (Parquet columnar, JSON, CSV, Avro, etc.). Execution uses a **shredded in-memory columnar representation** (vectorized value vectors) for columnar-speed processing of complex data ([drill.apache.org](https://drill.apache.org/)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — Drill owns no persistent index or write path.
- **Workload:** Interactive [OLAP](../concepts/oltp-olap-htap.md) / ad-hoc data exploration and BI over data lakes. Positioned for low-latency exploration rather than long-running batch ETL (it contrasts itself with Hive's batch model in its [FAQ](https://drill.apache.org/faq/)). Not OLTP, not HTAP.

## Distribution & consistency
- **CAP under partition:** N/A in the traditional sense — Drill stores no data of its own, so it provides **no consistency or durability guarantees**; correctness and consistency are entirely those of the underlying source (S3, HDFS, Mongo, etc.). Drillbits coordinate cluster membership through [ZooKeeper](../concepts/consensus-raft-paxos.md), but a query simply fails / partially fails if a Drillbit is lost — there is no replication of state to reason about with [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — no replicated state machine; latency-vs-consistency is a property of the data sources Drill reads.
- **Default isolation & what's achievable:** No transactions, **no isolation level** ([isolation-levels](../concepts/isolation-levels.md) does not apply). Each query is a read (plus optional bulk create); there is no MVCC, no [mvcc](../concepts/mvcc.md) snapshot, no multi-statement transaction. A query sees whatever the source files currently contain; concurrent writes to the underlying source are not coordinated.
- **Replication:** N/A — Drill has no [replication](../concepts/replication-models.md) of its own. Drillbits are symmetric workers (no master/slave); any Drillbit can act as the **Foreman** (query coordinator) for a given query ([architecture](https://drill.apache.org/docs/architecture-introduction/)).
- **Tunable consistency?** N/A.
- **Clock dependency:** None for correctness ([clocks-and-time](../concepts/clocks-and-time.md) not relevant).

## Schema
- **Schema-on-read** ("on-the-fly schema discovery"): execution begins without knowing data structure; the plan is compiled and **re-compiled during execution** as actual data flows ([FAQ](https://drill.apache.org/faq/)). It can leverage Hive metastore schemas when querying Hive. This flexibility is also the main source of brittleness — schema changes mid-scan (a column that is sometimes int, sometimes string) cause runtime errors rather than clean failures.
- **Migration / DDL:** Mostly N/A — no managed schema to migrate. `CREATE VIEW` exists; tables are external. No `ALTER TABLE` data mutation.
- **Type system:** Rich support for nested/complex types (maps, arrays), JSON, and the standard SQL scalar types; geospatial and vector types are not first-class. ⚠️ unverified — no native vector/ANN support.

## Query interface
- **Language:** ANSI-leaning SQL with extensions for nested data and file-path addressing (e.g. `SELECT * FROM dfs.\`/data/*.parquet\``). JDBC/ODBC drivers and a REST API.
- **Transactions:** **None.** No INSERT/UPDATE/DELETE on existing data. Writes are limited to bulk [`CREATE TABLE AS` (CTAS)](https://drill.apache.org/docs/create-table-as-ctas/) and `CREATE TEMPORARY TABLE AS` into a writable (mutable) workspace — data is written only at table-creation time and cannot be appended or modified afterward ([CTAS docs](https://drill.apache.org/docs/create-table-as-ctas/)). Treat Drill as effectively read-only with an export-to-file escape hatch.
- **Native joins/indexes/aggregations:** Full SQL joins (including **cross-source joins** in a single query — e.g. Mongo joined to a Parquet file on S3), aggregations, and window functions are native to the engine. No secondary indexes (it relies on source-side pushdown — filter/limit pushdown to Hive, HBase, etc.).
- **Stored procedures / UDFs:** No stored procedures. Custom **UDFs in Java**, plus custom **storage and format plugins** in Java.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — add Drillbits to a cluster; a query is parallelized into fragments distributed across Drillbits. Scales from a single embedded node to large clusters ([drill.apache.org](https://drill.apache.org/)).
- **Sharding / partitioning:** Drill does not shard data (it owns none). Parallelism comes from partitioning the *scan* of source data (file splits, Parquet row groups, HBase regions). "Partition pruning" applies for directory-partitioned file layouts.
- **Read replicas / read consistency:** N/A — reads go straight to sources.
- **Storage/compute separation:** Inherent — Drill **is** compute-only; all data lives in external stores. This is [storage-compute-separation](../concepts/storage-compute-separation.md) taken to its logical end (no proprietary storage tier at all).

## Performance & durability
- **Write path:** N/A — no WAL, no fsync, no durability of its own ([wal-and-durability](../concepts/wal-and-durability.md) does not apply). "Data-loss window on crash" is meaningless for Drill itself; a crash just fails in-flight queries. CTAS output durability is that of the target filesystem.
- **Throughput/latency:** Columnar vectorized execution gives good scan throughput, especially over Parquet. p99 tail is dominated by source latency (object-store GETs, Mongo scans) and by memory pressure — large hash joins/sorts can spill or **fail with out-of-memory** rather than degrade gracefully, a recurring operational complaint. ⚠️ unverified — no authoritative current p99 benchmark located.
- **Compaction / vacuum / GC:** No compaction or vacuum (no owned storage). JVM **garbage collection** and off-heap (direct) memory tuning are the real performance levers; mis-sized direct memory is the classic Drill failure mode.

## Operations & maturity
- **Backup/restore, PITR:** N/A — nothing to back up except config and any CTAS output files (which live in the source store). No snapshots, no PITR.
- **Observability:** Web UI per Drillbit with query profiles (physical plan, per-fragment timing), `EXPLAIN` plans, REST API metrics. Profiles are the primary debugging tool.
- **Upgrade story:** Cluster of stateless Drillbits behind ZooKeeper; upgrades are essentially redeploys. Day-2 burden centers on JVM/memory tuning and storage-plugin configuration, not data management.
- **Maturity:** Apache top-level project since 2014; still maintained but **low-velocity** — recent releases are 1.21.2 (June 2024) and 1.22 (June 2025), largely bug-fix/maintenance ([ASF board notes](https://whimsy.apache.org/board/minutes/Drill.html), [GitHub releases](https://github.com/apache/drill/releases)). Community is modest (≈62 committers, ≈28 PMC). Mindshare has largely shifted to [trino](trino.md)/[presto](presto.md) and [duckdb](duckdb.md) for the "query files in place" niche; rank 140 reflects this decline. **No Jepsen report** — and none would be meaningful, since Drill provides no consistency guarantees to test.

## Ecosystem & people
- **Canonical use cases:** Ad-hoc SQL exploration over a messy data lake of JSON/Parquet/CSV; quick BI on files without an ETL/load step; one-off cross-source joins (e.g. Mongo + S3). Good when you want SQL over self-describing files *right now*.
- **Anti-patterns:** Any system of record, OLTP, frequent updates, low-latency point lookups, or anything needing transactions/durability. For a managed lakehouse query layer most teams now reach for [trino](trino.md); for single-node file analytics, [duckdb](duckdb.md) is faster and simpler. Drill's schema-on-read also bites on dirty/heterogeneous data, producing runtime type errors.
- **Drivers / connectors:** JDBC/ODBC, REST; BI tool integration (Tableau, Qlik, Superset, Excel). Python via JDBC/REST; Airflow has an `apache-drill` provider. CDC/Kafka are not native (Drill reads at rest).
- **Docs quality:** Reasonable official docs, though some pages are dated relative to the slowing release cadence.

## Licensing & cost
- **License:** Apache License 2.0 — fully permissive, no post-2018 relicensing concerns ([license-taxonomy](../concepts/license-taxonomy.md)). No source-available/SSPL/BSL restrictions.
- **Self-managed vs managed:** Self-managed only. No major vendor sells a hosted Drill service today; ⚠️ unverified — MapR (acquired by HPE) historically packaged it, but that distribution is effectively defunct.
- **Lock-in:** Minimal — Drill owns no data and uses open formats; you can drop it without migrating storage. The lock-in risk is the opposite one: relying on an engine whose community is shrinking.
- **Cost model:** Free software; cost is the compute (JVM nodes) and engineering time to operate it.

## Hardware / deployment
- **Resource profile:** Memory-bound and CPU-bound. Heavy use of **off-heap direct memory** for the columnar value vectors; large sorts/joins need generous direct-memory configuration or they OOM. Working set need not fully fit in RAM, but per-operator memory must.
- **Storage assumptions:** No local storage requirement for data; performance depends on the latency/throughput of the backing store (NVMe-backed HDFS vs higher-latency object stores like S3).
- **Footprint:** Distributed cluster of Drillbits, or a single **embedded** Drillbit for laptop/dev use. JVM-based.
- **Deployment:** On-prem or self-hosted in cloud; runs on YARN, bare metal, or containers/k8s. StatefulSet not really needed since Drillbits are stateless (state lives in ZooKeeper and the data sources).

## Bottom line
Reach for Apache Drill when you need ad-hoc ANSI SQL over heterogeneous files and NoSQL stores **in place**, with no load step and no schema definition — especially for cross-source joins. Do not reach for it as a database: it has no transactions, no durability, no consistency model, and no managed storage of its own. The single biggest gotcha is treating it like a data store — it is purely a query layer, and in 2026 the engines that won this niche ([trino](trino.md), [duckdb](duckdb.md)) are better supported; choose Drill only if its specific source plugins or schema-free JSON handling fit you uniquely well.

## Sources
- [Apache Drill — official site](https://drill.apache.org/)
- [Architecture Introduction](https://drill.apache.org/docs/architecture-introduction/)
- [Apache Drill FAQ](https://drill.apache.org/faq/)
- [CREATE TABLE AS (CTAS)](https://drill.apache.org/docs/create-table-as-ctas/)
- [Supported SQL Commands](https://drill.apache.org/docs/supported-sql-commands/)
- [GitHub releases (apache/drill)](https://github.com/apache/drill/releases)
- [ASF Board minutes — Drill](https://whimsy.apache.org/board/minutes/Drill.html)
