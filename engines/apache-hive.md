---
name: Apache Hive
slug: apache-hive
rank: 15
data_model: Relational (SQL-on-Hadoop)
license: Apache License 2.0 (permissive)
summary: The original SQL-on-Hadoop batch warehouse; a query layer + metastore over files in HDFS/S3, not a database with its own storage.
last_researched: 2026-06-04
confidence: high
---

# Apache Hive

> A SQL compiler and metadata catalog that turns HiveQL into distributed batch jobs over files in HDFS/object storage — high-latency, high-throughput analytics, never an OLTP store.

## When to use

**Use Apache Hive if:**
- ✅ You already run Hadoop/HDFS (or a data lake) and need throughput-oriented batch SQL ETL/ELT over huge (TB–PB) datasets at a permissive Apache 2.0 license
- ✅ You need its ubiquitous Hive Metastore as a shared catalog that [trino](trino.md)/[presto](presto.md), [apache-spark-sql](apache-spark-sql.md), Impala, and Flink can all read from
- ✅ You want SQL over open columnar formats (ORC/Parquet/[apache-iceberg](apache-iceberg.md)) with storage/compute already decoupled

**Avoid Apache Hive if:**
- ❌ You need anything interactive, transactional, low-latency, or high-concurrency — for interactive lake SQL use [trino](trino.md)/[presto](presto.md) or [apache-spark-sql](apache-spark-sql.md)
- ❌ You need OLTP, serializable transactions, sub-second point lookups, or frequent single-row updates
- ❌ You can't maintain the day-2 chores — "ACID" means snapshot-isolated managed ORC tables that require ongoing compaction, and the single-RDBMS Metastore is a SPOF that over-partitioning will bring to its knees

## Identity
- **Taxonomy / data model:** relational SQL engine over the Hadoop ecosystem. Hive itself stores no data; tables are metadata (in the **Hive Metastore**) mapping schemas onto files in HDFS, S3, ADLS, GCS, etc. Increasingly used as a query engine over open table formats (ORC, Parquet, Avro, and native [apache-iceberg](apache-iceberg.md) tables since Hive 4.0).
- **Storage model:** pluggable file formats; columnar **ORC** is the canonical format (and the only one supporting full ACID). Not an [lsm-vs-btree](../concepts/lsm-vs-btree.md) engine — there is no Hive-managed on-disk index structure; it relies on columnar file layouts, partition pruning, and ORC/Parquet stripe/footer statistics.
- **Workload:** OLAP / batch analytics ([oltp-olap-htap](../concepts/oltp-olap-htap.md)). Classic Hive is high-latency MapReduce batch; with Tez + **LLAP** (Live Long and Process) persistent executors and caching, it reaches interactive-ish latencies, but it is **not** HTAP and never an OLTP system.

## Distribution & consistency
- **CAP under partition:** N/A in the usual sense — Hive is a stateless compute layer; durability/availability are properties of the underlying store (HDFS/S3) and the Metastore RDBMS, not Hive. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — no Hive-managed replication or quorum.
- **Default isolation & what's achievable:** **snapshot isolation only** for ACID tables; the reader pins a high-watermark transaction list at query start and skips deltas from aborted/in-flight transactions ([Hive ACID docs](https://hive.apache.org/docs/latest/user/hive-transactions-acid/)). There is no serializable isolation. ACID applies **only to managed ORC tables**; external tables and non-ORC formats are not transactional. Treat "ACID" here as "snapshot-isolated, single-table, coarse-grained" — fine for slowly-changing dimensions and GDPR deletes, not for concurrent row-level OLTP ([Hive Transactions](https://hive.apache.org/docs/latest/user/hive-transactions/)). See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** N/A at the Hive layer — data replication is HDFS's job (3x replication) or the object store's. The Metastore is a single RDBMS (typically MySQL/PostgreSQL) whose HA is your responsibility. Hive does have a **replication/DR feature (HiveRepl)** for copying tables/metadata between clusters. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels.
- **Clock dependency:** No correctness dependence on synchronized clocks; transaction ordering is via a Metastore-issued monotonic transaction ID. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** by design: data files exist independently; a table definition projects a schema over them at query time. Bad/mismatched data surfaces as NULLs or errors at read, not write.
- **Migration/evolution:** `ALTER TABLE` is largely a Metastore metadata operation and is cheap (add/rename columns, add partitions) — it does not rewrite data files. Schema evolution semantics depend on the file format (ORC/Parquet handle added columns gracefully). Iceberg tables add true schema/partition evolution.
- **Type system:** primitives plus complex types — `ARRAY`, `MAP`, `STRUCT`, `UNIONTYPE`, `DECIMAL`, `DATE`/`TIMESTAMP`. No native vector or first-class geospatial types (geospatial via UDFs/external libs). JSON handled via SerDes/UDFs, not a native type.

## Query interface
- **Language:** **HiveQL**, a SQL dialect (close to SQL but with Hive-specific DDL/extensions). Mature analytic SQL: joins, `GROUP BY`/`GROUPING SETS`, window functions, CTEs, subqueries.
- **Transactions:** multi-statement transactions exist but are limited — `INSERT`/`UPDATE`/`DELETE`/`MERGE` on managed ACID (ORC) tables under snapshot isolation. No interactive low-latency transactional workloads; commits are coarse and writes generate delta files compacted later.
- **Native vs app-side:** joins, aggregations, window functions all native and pushed into the execution engine (Tez/MapReduce/Spark). Indexes were removed (the old Hive index feature was dropped in Hive 3); performance comes from partitioning, bucketing, and ORC/Parquet column statistics + predicate pushdown instead.
- **Stored procedures / UDFs:** **HPL/SQL** (procedural SQL) ships with Hive 2+. Rich UDF/UDAF/UDTF extensibility in **Java**; SerDes for custom formats.

## Scaling & topology
- **Vertical vs horizontal:** horizontally scalable compute — queries fan out across a YARN/Tez/Spark cluster; throughput scales with cluster size. Data scaling is the storage layer's concern (HDFS/object store), effectively unbounded.
- **Sharding/partitioning:** tables are **partitioned** (directory-per-partition-value) and optionally **bucketed** (hash into fixed file count). Partition pruning is the main performance lever; over-partitioning (many small partitions/files) is a classic foot-gun that hammers the Metastore and NameNode.
- **Read replicas / read consistency:** N/A — readers see a consistent snapshot of the committed file set.
- **Storage/compute separation:** **yes, inherently** — compute (Hive on Tez/LLAP) is fully decoupled from storage (HDFS/S3). This is the Hadoop-era precursor to the modern pattern. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** no Hive WAL ([wal-and-durability](../concepts/wal-and-durability.md)); durability is delegated to HDFS (replication + its own write pipeline) or the object store. ACID writes append **delta files**; a separate **compaction** process (minor → merge deltas, major → rewrite base) consolidates them. Data-loss window = whatever the underlying store guarantees.
- **Throughput/latency:** built for **throughput over latency** — large scans, ETL, batch aggregation over TB–PB. MapReduce execution has seconds-to-minutes startup overhead; Tez and LLAP cut this dramatically (LLAP keeps JVMs warm and caches columnar data in memory). p99 is dominated by stragglers, skew, and small-file/partition-metadata overhead, not by a storage engine's GC.
- **Compaction/GC:** ACID tables **require** periodic compaction or read performance degrades as delta files accumulate; uncompacted ACID tables and the "too many small files" problem are the dominant operational pain points.

## Operations & maturity
- **Backup/restore, PITR:** no built-in PITR. Backup = back up the Metastore RDBMS + the underlying files; HiveRepl provides cross-cluster table/metadata replication for DR.
- **Observability:** `EXPLAIN` / `EXPLAIN EXTENDED` query plans; HiveServer2 web UI; Tez UI; metrics via Hadoop/YARN. Query history and slow-query analysis typically come from the surrounding platform (Cloudera, Ambari, EMR).
- **Upgrade story:** Metastore schema upgrades via `schematool`; the **Hive 2→3 jump was disruptive** (managed tables became ACID/ORC by default, external tables changed semantics, location changes). Day-2 burden centers on the Metastore (a single RDBMS bottleneck and SPOF), compaction tuning, and small-file management.
- **Maturity:** very mature (first released 2010, out of Facebook). **Hive 4.0.0 went GA on 2024-04-30** ([ASF announcement](https://news.apache.org/foundation/entry/apache-software-foundation-announces-apache-hive-4-0)), adding native Apache Iceberg integration and improved compaction. No Jepsen report exists (not a distributed consensus database, so the usual Jepsen lens does not apply). Known failure modes: Metastore overload from too many partitions, small-file proliferation, and unbounded delta growth without compaction.

## Ecosystem & people
- **Canonical use cases:** large-scale batch ETL/ELT, data-lake SQL over HDFS/S3, periodic reporting and aggregation, the **central metastore catalog** that many other engines ([presto](presto.md)/[trino](trino.md), [apache-spark-sql](apache-spark-sql.md) SQL, Apache Impala, [apache-flink](apache-flink.md)) read from. The Hive Metastore is arguably more widely used than the Hive query engine itself.
- **Anti-patterns:** OLTP, low-latency point lookups, high-concurrency interactive dashboards, sub-second queries, anything needing serializable transactions or frequent single-row updates. For interactive lakehouse SQL most teams now reach for [trino](trino.md)/[presto](presto.md) or [apache-spark-sql](apache-spark-sql.md); for the same warehouse pattern in the cloud, [snowflake](snowflake.md)/[google-bigquery](google-bigquery.md)/[databricks](databricks.md).
- **Drivers/connectors:** JDBC/ODBC via HiveServer2; Thrift Metastore API consumed across the ecosystem; integrates with Kafka, Sqoop, dbt (via adapters), and BI tools (Tableau, Superset, etc.).
- **Community/support:** large, mature Apache community; commercial support historically via Cloudera (CDP) and cloud-managed Hive on AWS EMR, etc. Docs are adequate but spread across the cwiki and the newer docs site. Learning curve is low for SQL users but operating Hadoop/YARN/Metastore underneath is the real cost.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-managed on a Hadoop cluster, or managed (AWS EMR, Cloudera CDP, Dataproc). No single proprietary "Hive Inc."
- **Lock-in:** low — open formats (ORC/Parquet/Iceberg) and an open Metastore mean data is portable; many engines can read the same tables.
- **Cost model:** no license fee; cost is infrastructure (cluster compute + storage) plus operational staffing. On-prem Hadoop is cheap-at-scale on storage but operationally heavy; cloud-managed shifts that to per-instance/per-cluster spend.

## Hardware / deployment
- **Resource profile:** disk-/IO-bound for classic batch scans; LLAP is memory-bound (caches columnar data and keeps executors warm). CPU matters for ORC/Parquet decode and vectorized execution. Working set need not fit in RAM — it is a spill-to-disk batch engine.
- **Storage assumptions:** designed for HDFS on commodity disks; runs well over network-attached object stores (S3/ADLS/GCS), tolerating their higher latency by virtue of large sequential scans.
- **Footprint:** clustered, **not** embedded and not single-node-meaningful in production (requires a Metastore RDBMS + an execution cluster). A local single-node mode exists for dev only.
- **Deployment:** on-prem Hadoop, or cloud managed services; official Docker images shipped with Hive 4.0. Kubernetes deployment is possible but Hive is YARN-centric and not natively k8s-friendly.

## Bottom line
Reach for Hive when you already run Hadoop/HDFS (or a data lake) and need throughput-oriented batch SQL ETL over huge datasets at a permissive license, or when you need its ubiquitous Metastore as a shared catalog. Do **not** use it for anything interactive, transactional, or latency-sensitive — for interactive lake SQL use [trino](trino.md)/[presto](presto.md) or [apache-spark-sql](apache-spark-sql.md), and for a managed cloud warehouse use [snowflake](snowflake.md)/[google-bigquery](google-bigquery.md)/[databricks](databricks.md). The single biggest gotcha: "ACID" means snapshot-isolated managed ORC tables that **require ongoing compaction**, and the Metastore is a single-RDBMS bottleneck and SPOF that over-partitioning will bring to its knees.

## Sources
- [Apache Hive official site](https://hive.apache.org/)
- [Hive Transactions (ACID) docs](https://hive.apache.org/docs/latest/user/hive-transactions-acid/) — snapshot isolation, ORC-only, delta/compaction model
- [Hive Transactions overview](https://hive.apache.org/docs/latest/user/hive-transactions/)
- [ASF announces Apache Hive 4.0 (2024-04-30)](https://news.apache.org/foundation/entry/apache-software-foundation-announces-apache-hive-4-0) — GA date, Iceberg integration, compaction
- [Apache ORC ACID support](https://orc.apache.org/docs/acid.html)
- [Apache Hive — Wikipedia](https://en.wikipedia.org/wiki/Apache_Hive)
- [apache/hive on GitHub](https://github.com/apache/hive)
