---
name: Apache Spark (SQL)
slug: apache-spark-sql
rank: 27
data_model: Relational (engine)
license: Apache License 2.0 (permissive)
summary: Distributed SQL/dataframe query engine over external storage — not a database; bring your own catalog, table format, and ACID.
last_researched: 2026-06-04
confidence: high
---

# Apache Spark (SQL)

> Spark SQL is a distributed query *engine*, not a database: it executes SQL/dataframe jobs over data living in someone else's storage (files, object stores, JDBC, [delta-lake](delta-lake.md)/[apache-iceberg](apache-iceberg.md) tables), so most "database" properties — durability, ACID, isolation — come from the table format underneath, not from Spark.

## Identity
- **Taxonomy / data model:** Relational query engine on top of Spark Core. Exposes a SQL interface and the typed DataFrame/Dataset API over distributed collections (RDDs). It owns *computation*, not *storage* — db-engines lists it among DBMS but it is more accurately a compute/query layer.
- **Storage model:** No native storage. Reads/writes columnar [Parquet](https://parquet.apache.org/) and ORC, plus CSV/JSON/Avro/text, JDBC sources, and lakehouse table formats ([delta-lake](delta-lake.md), [apache-iceberg](apache-iceberg.md), Apache Hudi) over HDFS/S3/GCS/ADLS. In-memory and shuffle representation is columnar/vectorized via Project Tungsten; on-disk format is whatever the source dictates. See [columnar-storage](../concepts/columnar-storage.md), [lsm-vs-btree](../concepts/lsm-vs-btree.md) (mostly N/A — Spark does not manage an LSM/B-tree itself).
- **Workload:** OLAP / batch ETL and ad-hoc analytics; also streaming via Structured Streaming (micro-batch, or continuous/low-latency modes). Not OLTP — no point lookups, no per-row updates without a table format that provides them. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Not a replicated stateful store, so classic [cap-pacelc](../concepts/cap-pacelc.md) does not apply to Spark itself; consistency/availability are properties of the *storage layer* (e.g. Delta/Iceberg transaction logs) and the metastore. A Spark job is a transient compute DAG; on partition/failure it retries tasks or fails the job.
- **PACELC:** N/A for the engine — defer to the underlying table format and object store.
- **Default isolation & what's achievable:** Spark SQL has no transaction manager of its own. With plain files, writes are *not* isolated and a failed job can leave partial output (`.crc`/temp files, partial partitions). Atomicity/isolation come from the table format: [Delta Lake](https://docs.databricks.com/aws/en/delta/) provides ACID via a file-based transaction log with optimistic concurrency control; [Apache Iceberg] and Hudi provide similar snapshot isolation. So an "ACID Spark" claim really means "ACID Delta/Iceberg table read/written by Spark." See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** N/A — no data replication in Spark. Durability/replication belong to HDFS/S3 or the table format. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** N/A.
- **Clock dependency:** No correctness dependence on synchronized clocks for the engine. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** by default — Spark infers or accepts a schema when reading files; no schema is enforced by the store unless a table format enforces it. Lakehouse formats add **schema enforcement and evolution** (add/rename/reorder columns) on write.
- **Migration/evolution:** `ALTER TABLE` semantics depend on the catalog/format; with Delta/Iceberg, schema evolution is metadata-only and cheap. With raw Parquet directories, "migration" is really a rewrite.
- **Type system:** rich SQL types incl. `STRUCT`, `ARRAY`, `MAP`, `DECIMAL`, timestamps (with/without timezone in Spark 3.4+), and `VARIANT` (semi-structured JSON) added in [Spark 4.0](https://www.databricks.com/blog/introducing-apache-spark-40). No native geospatial or vector types in core Spark (provided by libraries like Apache Sedona).

## Query interface
- **Language:** SQL (its own dialect, broadly ANSI-aligned) plus the DataFrame/Dataset API in Scala, Java, Python (PySpark), and R. **ANSI SQL mode is enabled by default since [Spark 4.0](https://www.databricks.com/blog/introducing-apache-spark-40)** (May 2025) — stricter errors instead of silent NULL/overflow, a notable behavior change from 3.x.
- **Transactions:** No multi-statement transactions, no `BEGIN`/`COMMIT` in the engine. Single-write atomicity exists only via the table format's commit (one Delta/Iceberg commit per write). There is no cross-table transaction.
- **Native vs app-side:** joins, aggregations, window functions, CTEs, and subqueries are all native and distributed. **No indexes** in the OLTP sense; performance comes from partition pruning, predicate/column pushdown, file skipping (Delta/Iceberg stats, Z-ordering/clustering), and bucketing — not B-tree indexes. Optimized by the **Catalyst** rule/cost optimizer plus **Adaptive Query Execution (AQE)**, default-on since 3.2, which re-plans at runtime (coalesces shuffle partitions, switches sort-merge→broadcast joins, splits skewed joins) using actual shuffle statistics ([AQE docs](https://spark.apache.org/docs/latest/sql-performance-tuning.html)).
- **Stored procedures / UDFs:** UDFs in Scala/Java/Python; Python UDTFs and improved Arrow-based Python UDFs in Spark 4.0. SQL user-defined functions and a SQL scripting language were added in 4.x. No traditional stored-procedure engine.

## Scaling & topology
- **Horizontal**, share-nothing: a driver coordinates executors across a cluster (YARN, Kubernetes, Spark Standalone, or managed services). Scales by adding executors; dynamic allocation can add/remove them per workload.
- **Sharding/partitioning:** data is partitioned by the storage layout (directory partitioning, bucketing) and re-partitioned by shuffles at runtime; there is no fixed shard map to reshard — repartitioning is a job, not an ops migration. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** N/A — Spark reads from shared storage; consistency of reads depends on the object store and table-format snapshot you pin.
- **Storage/compute separation:** Yes, fundamentally — compute (Spark cluster) is fully decoupled from storage (object store + table format). This is the canonical [storage-compute-separation](../concepts/storage-compute-separation.md) architecture and what makes ephemeral/elastic clusters and serverless Spark possible.

## Performance & durability
- **Write path:** No WAL of its own. Output durability = the storage system's (S3 PUT, HDFS replication) plus the table format's atomic commit. **Data-loss / partial-write window:** with plain file output, a crashed job can leave committed-looking partial directories; the FileOutputCommitter v1/v2 choice and object-store consistency affect this. Delta/Iceberg eliminate partial visibility via a single atomic log commit. Structured Streaming uses checkpointing + write-ahead logs for exactly-once *to supported sinks*. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** high throughput for large scans/joins; **high per-query latency floor** (JVM/executor scheduling, shuffle, task launch) — seconds to minutes, not milliseconds. Wrong tool for interactive sub-second point queries.
- **p99 tail:** dominated by **shuffle and data skew** — a single skewed key can stall a stage; AQE skew handling and skew hints mitigate but do not eliminate it. Straggler tasks, GC pauses, and shuffle spill to disk drive tail latency.
- **Compaction/vacuum/GC:** the *engine* has JVM GC (a real tuning concern for large executors). *Table maintenance* (small-file compaction, `VACUUM`/expire-snapshots) is a property of Delta/Iceberg, run as separate Spark jobs.

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** N/A for the engine. Time-travel / snapshot reads and rollback come from Delta/Iceberg (query a table as-of a version or timestamp).
- **Observability:** Spark UI (DAG, stages, tasks, SQL plans), event logs / history server, `EXPLAIN` (incl. `EXPLAIN FORMATTED` and AQE-adjusted plans), and metrics via Dropwizard/Prometheus. Debugging skew and shuffle is the day-2 reality.
- **Upgrade story:** version upgrades are non-trivial — 3.x→4.0 changed defaults (ANSI mode on, Scala 2.13, Java 17+) and can break jobs; treat as a migration with testing. Clusters are typically immutable/redeployed rather than rolling-upgraded in place.
- **Maturity:** very mature, huge production footprint (since 2014; Spark 4.0 May 2025, [4.1.0 Dec 2025](https://spark.apache.org/releases/spark-release-4.1.0.html)). **No Jepsen report applies** — Spark is not a consistency-critical replicated store, so there is nothing for Jepsen to test; correctness questions point at the table format instead. Known failure modes: OOM/GC on the driver and executors, shuffle-fetch failures, small-files problem, and data skew.

## Ecosystem & people
- **Canonical use cases:** large-scale batch ETL/ELT, building and querying lakehouse tables, ML feature pipelines (MLlib / Spark ML), and streaming ingestion (Structured Streaming). The de facto compute engine for [delta-lake](delta-lake.md) and a first-class engine for [apache-iceberg](apache-iceberg.md).
- **Anti-patterns:** OLTP, low-latency point lookups, high-concurrency serving, small datasets (a single-node tool like [duckdb](duckdb.md) or [postgresql](postgresql.md) is faster and far simpler), and anything needing real per-row transactions without a lakehouse format.
- **Drivers/connectors:** JDBC/ODBC via the Thrift server; deep integration with Hive Metastore / Unity Catalog / AWS Glue; connectors for Kafka, Cassandra, JDBC databases, and most object stores; dbt has a Spark adapter; BI tools connect over JDBC/ODBC (latency-permitting). CDC is typically handled by the table format + a streaming source.
- **Community/support:** one of the largest data-engineering communities; commercial backing primarily from Databricks (and managed Spark on EMR, Dataproc, Synapse/Fabric, etc.). Docs are extensive. Learning curve: moderate for SQL users, steeper to tune (partitioning, shuffle, memory) at scale.

## Licensing & cost
- **OSS license:** Apache 2.0 — permissive, no post-2018 relicensing of Spark itself. See [license-taxonomy](../concepts/license-taxonomy.md). (Note: Databricks' managed runtime and some surrounding tooling are proprietary, and Delta Lake's fully open feature set vs Databricks extras is a known gray area.)
- **Self-managed vs managed:** both — self-host on YARN/Kubernetes/standalone, or managed (Databricks, EMR, Dataproc, Microsoft Fabric, Spark-on-K8s). Spark Connect (GA-level parity in 4.0) decouples client from cluster.
- **Lock-in:** the engine is portable; lock-in risk lives in the *catalog* (Unity Catalog), proprietary runtime optimizations, and managed-service glue — not in Spark SQL syntax itself.
- **Cost model:** you pay for compute (cluster nodes / DBUs / vCPU-hours) plus the object storage and egress. Cheap to start, but **idle clusters and over-provisioned executors are the classic cost trap**; serverless and autoscaling help. Cost is decoupled from data volume since storage is separate.

## Hardware / deployment
- **Resource profile:** memory- and CPU-bound; shuffle-heavy jobs become disk- and network-bound. The working set does *not* need to fit in RAM (it spills to disk), but enough memory dramatically reduces spill and GC.
- **Storage assumptions:** designed for network-attached/object storage (S3/GCS/ADLS) and HDFS; tolerant of high storage latency by reading in large columnar blocks. Local NVMe matters most for shuffle/spill scratch space.
- **Footprint:** clustered/distributed (driver + executors). Can run single-node for dev, but that defeats the purpose — use a single-node engine instead for small data.
- **Deployment:** Kubernetes-native operator support, YARN, standalone, and SaaS. Generally container/k8s-friendly; the driver is a single point of coordination per application.

## Bottom line
Reach for Spark SQL when you have genuinely large data, need distributed batch/streaming compute over a lakehouse, and want one engine across SQL, Python, Scala, and ML. Do *not* reach for it for OLTP, interactive sub-second queries, high-concurrency serving, or small data — a single-node engine like [duckdb](duckdb.md) or a real OLTP database will be simpler and faster. The single biggest gotcha: **Spark SQL is not a database** — durability, ACID, time-travel, and schema enforcement come from the table format ([delta-lake](delta-lake.md)/[apache-iceberg](apache-iceberg.md)) and storage beneath it, so reason about correctness there, and budget for shuffle/skew tuning as the dominant operational cost.

## Sources
- [Introducing Apache Spark 4.0 — Databricks blog](https://www.databricks.com/blog/introducing-apache-spark-40)
- [Spark Release 4.1.0 — apache.org](https://spark.apache.org/releases/spark-release-4.1.0.html)
- [Spark SQL Performance Tuning (AQE) — official docs](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- [What is Delta Lake (ACID via transaction log) — Databricks docs](https://docs.databricks.com/aws/en/delta/)
- [Apache Spark — Wikipedia (history/versions)](https://en.wikipedia.org/wiki/Apache_Spark)
