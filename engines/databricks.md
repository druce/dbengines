---
name: Databricks
slug: databricks
rank: 7
data_model: Multi-model (lakehouse — relational/columnar over object storage)
license: Proprietary platform over OSS core (Delta Lake/Spark Apache-2.0; Photon proprietary)
summary: Spark-based lakehouse that runs SQL/ML over Delta Lake (Parquet + transaction log) on cloud object storage; analytics-first, not an OLTP database.
last_researched: 2026-06-04
confidence: high
---

# Databricks

> A managed lakehouse platform that puts ACID tables and a fast vectorized SQL engine on top of cheap cloud object storage — excellent for OLAP/ML at scale, the wrong tool for transactional, low-latency point workloads.

## When to use

**Use Databricks if:**
- ✅ You have large-scale analytics, ETL/ELT, streaming, and ML over a shared open table format and want one governed platform instead of separate lake/warehouse/ML stacks.
- ✅ You want vectorized SQL (Photon) and ACID Delta tables on cheap cloud object storage with storage/compute separation.
- ✅ Your sweet spot is large sequential scans/aggregations, not small random reads.

**Avoid Databricks if:**
- ❌ You need OLTP, low-latency single-row point lookups, or a high-concurrency app backend — it is analytics-first, not transactional.
- ❌ Your datasets are small enough that [duckdb](duckdb.md) or [postgresql](postgresql.md) are dramatically cheaper and faster.
- ❌ You can't manage cost/operational hygiene — DBU spend balloons with idle/oversized clusters and small-file neglect, and "ACID" means per-table WriteSerializable.

## Identity
- **Taxonomy / data model:** Multi-model "lakehouse" platform, not a single database engine. The data layer is [delta-lake](delta-lake.md) tables (open Parquet files + a JSON/checkpoint transaction log) on S3/ADLS/GCS; queried as relational SQL, DataFrames (Spark/PySpark), and increasingly via [apache-iceberg](apache-iceberg.md) interop. Governance/metadata lives in Unity Catalog.
- **Storage model:** Columnar (Parquet) data files with a separate append-only transaction log (the DeltaLog) — a metadata-driven table format, distinct from a [B-tree or LSM](../concepts/lsm-vs-btree.md) storage engine. On-disk format is open Parquet; the log gives ACID, time travel, and schema enforcement. Photon is the proprietary vectorized C++ execution engine (replaces the JVM Spark code path for filters/joins/aggregates/scans).
- **Workload:** OLAP / data engineering / ML, with HTAP-style ambitions. **It is not OLTP.** Databricks SQL (Photon + Delta) handles BI/warehouse queries; Spark handles ETL and ML. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Any "real-time" claim refers to streaming ingest and serving (Delta Live Tables, online tables/feature serving), not transactional row mutation latency. **Lakebase** (introduced at the 2025 Data + AI Summit, GA on AWS, built on the Neon Postgres technology Databricks acquired) is a separate managed serverless Postgres OLTP database — a distinct engine alongside the lakehouse, not the Delta/Photon analytical engine itself ([Lakebase docs](https://docs.databricks.com/aws/en/oltp/)).

## Distribution & consistency
- **CAP under partition:** Not a self-clustering DB — durability and consistency are delegated to the underlying cloud object store (S3/ADLS/GCS), which is the source of truth. Effectively **CP at the table level**: a write either atomically commits to the transaction log or fails. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Largely N/A as a distributed-database tradeoff — the object store provides the consistency/availability guarantees; Databricks compute is stateless against it.
- **Default isolation & what's achievable:** **WriteSerializable by default** for writes (concurrent writes allowed; final state equals *some* serial order); **Serializable** is selectable but more restrictive; reads get **snapshot isolation** ([Databricks ACID docs](https://docs.databricks.com/aws/en/lakehouse/acid)). Concurrency is **optimistic** — read state, write files, then validate-and-commit; on conflict the write throws (`ConcurrentAppendException`/`ConcurrentModificationException`) rather than corrupting data. Note the "ACID" claim is **per-table** by default; multi-table/multi-statement transactions (`BEGIN ATOMIC ... END`) exist but require catalog commits enabled on participating tables ([Databricks ACID docs](https://docs.databricks.com/aws/en/lakehouse/acid)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** N/A at the engine level — replication, durability, and cross-AZ availability come from the object store. Cross-region is a data-copy/replication-job concern, not built-in quorum replication. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Isolation level (Serializable vs WriteSerializable) is tunable per table; no Dynamo-style per-query read consistency knobs.
- **Clock dependency:** None for correctness — commit ordering is enforced via mutual exclusion on the log (put-if-absent), not clocks. See [clocks-and-time](../concepts/clocks-and-time.md). Multi-cluster writes on S3 historically required a DynamoDB log store because S3 lacked atomic put-if-absent ([Delta Lake S3 multi-cluster writes](https://delta.io/blog/2022-05-18-multi-cluster-writes-to-delta-lake-storage-in-s3/)); S3 added conditional-write (put-if-absent via `If-None-Match`) support in late 2024, reducing this need ([AWS S3 conditional writes](https://aws.amazon.com/about-aws/whats-new/2024/08/amazon-s3-conditional-writes/)).

## Schema
- **Schema-on-write vs schema-on-read:** Schema-on-write with **schema enforcement** on Delta tables (malformed records rejected); flexible via opt-in **schema evolution** (`mergeSchema`, auto-evolution on MERGE). Raw lake files can still be queried schema-on-read.
- **Migration/evolution:** Online column add/rename/type-widen supported via schema evolution and column mapping; no table-level lock held for the duration the way a row-store `ALTER` would — changes are metadata commits on the log. Large rewrites (e.g., partition changes) still cost a data rewrite.
- **Type system:** SQL types plus arrays, maps, structs, JSON handling, geospatial (via libraries/H3), timestamps/intervals; vector/embedding support via Mosaic AI / Vector Search rather than a native column type in the table engine.

## Query interface
- **Language:** ANSI-leaning **Spark SQL** (Databricks SQL dialect) and DataFrame APIs in Python/Scala/R/Java; SQL is the primary warehouse interface. Not a Postgres-wire-compatible engine.
- **Transactions:** ACID at the **table** level (atomic MERGE/UPDATE/DELETE/INSERT); multi-statement atomic blocks available with catalog commits. Not designed for high-rate single-row OLTP transactions.
- **Native vs app-side:** Native joins, aggregations, window functions, CTEs, MERGE; secondary indexing is replaced by **data skipping** (file-level min/max stats), **Z-ordering**, and **liquid clustering** rather than traditional B-tree secondary indexes.
- **Stored procedures / UDFs:** Python/Scala/SQL UDFs, pandas UDFs, and SQL functions; notebooks and jobs are the orchestration unit.

## Scaling & topology
- **Vertical vs horizontal:** Horizontally scaled compute — a driver + N workers (Spark executors), with **optimized autoscaling** that can scale down even mid-job by tracking shuffle-file state ([Databricks autoscaling](https://www.databricks.com/blog/2018/05/02/introducing-databricks-optimized-auto-scaling.html)). SQL Warehouses scale clusters for concurrency.
- **Sharding:** No manual sharding — data is partitioned/clustered as files in object storage; "resharding" is a re-layout (repartition / liquid clustering) job, not a painful online reshard.
- **Read replicas:** N/A — all compute reads the same object-store source of truth; read scaling is "spin up more compute," reads are snapshot-consistent.
- **Storage/compute separation:** Yes, foundational — compute (Databricks runtime/Photon) is fully decoupled from storage (your object store). Classic compute runs in the customer's cloud account; serverless runs in Databricks' account. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Data written as Parquet files to object storage, then an **atomic commit** to the transaction log makes them visible; durability is the object store's (typically 11-nines). The "data-loss window on crash" is effectively the durability of object PUTs — an uncommitted write simply never becomes visible. See [wal-and-durability](../concepts/wal-and-durability.md). No traditional WAL/fsync semantics; the DeltaLog *is* the WAL.
- **Throughput/latency:** Strong scan/aggregate throughput; Photon gives ~2–4x speedups on BI-style queries vs JVM Spark (vendor benchmark — treat as directional). **High per-query/job startup latency** and object-store round-trips make it poor for single-row, sub-100ms point lookups; tail latency dominated by file listing, small-file overhead, and cluster/warehouse cold starts.
- **Compaction / vacuum / GC:** `OPTIMIZE` (compaction + Z-order/liquid clustering) and `VACUUM` (remove tombstoned files past a retention window) are explicit maintenance ops. Skipping them causes the classic **small-files problem** and degraded p99; `VACUUM` with too-short retention can break time travel and concurrent readers.

## Operations & maturity
- **Backup/restore, PITR:** **Time travel** (`VERSION AS OF` / `TIMESTAMP AS OF`) and `RESTORE` give versioned point-in-time recovery, bounded by retention and `VACUUM`. Object-store versioning/cross-region copy provides DR.
- **Observability:** Query history/profiles, Spark UI, EXPLAIN plans, the Photon query profile, cluster/SQL-warehouse metrics, Unity Catalog audit logs and **data lineage**.
- **Upgrade story:** Managed runtime — Databricks Runtime versions (LTS lines) are selected per cluster; serverless is auto-managed. Rolling/no-downtime at the platform level; day-2 burden is real around **cost control** (DBU sprawl), small-file/compaction hygiene, and cluster right-sizing.
- **Maturity:** Very mature, large production base; Delta Lake is a Linux Foundation project. **No public Jepsen report** exists for Databricks/Delta Lake; correctness reasoning relies on the optimistic-concurrency protocol and the object store's atomicity guarantees rather than independent formal verification. No Jepsen analysis of Databricks/Delta Lake appears in the [Jepsen analyses list](https://jepsen.io/analyses) as of 2026-06. Known failure modes: concurrent-write conflicts on hot tables, `VACUUM`/retention foot-guns, and S3-eventual-consistency-era multi-writer pitfalls (now largely mitigated).

## Ecosystem & people
- **Canonical use cases:** Large-scale ETL/ELT, data warehousing/BI (Databricks SQL), streaming pipelines (Structured Streaming / Delta Live Tables), and ML/AI (MLflow, Mosaic AI, feature/vector serving) — a unified lake + warehouse + ML stack.
- **Anti-patterns:** OLTP / high-concurrency single-row reads and writes; low-latency app backends; small datasets where a single-node engine like [duckdb](duckdb.md) or [postgresql](postgresql.md) is cheaper and faster; workloads needing strict per-row transactional throughput.
- **Drivers / connectors:** JDBC/ODBC, Spark connectors, dbt adapter, Kafka/Kinesis ingest, CDC tooling, Fivetran/Airbyte, Power BI/Tableau/Looker; Delta Sharing for cross-org data sharing; broad cloud-marketplace presence (AWS/Azure/GCP).
- **Community & support:** Large community, strong docs, commercial support from Databricks. Learning curve is moderate-to-steep (Spark internals, cost/perf tuning, Unity Catalog governance).

## Licensing & cost
- **OSS vs proprietary:** Hybrid. **Delta Lake**, **Apache Spark**, and **MLflow** are open source (Apache-2.0, Linux Foundation governed); **Photon**, Unity Catalog (managed), the optimized runtime, and the platform are **proprietary** and only available on the Databricks service. The open core means table data is portable (open Parquet/Delta), but the *engine that makes it fast* is not. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Managed-only platform (multi-cloud SaaS on AWS/Azure/GCP). You can read your Delta tables with other engines, but the Databricks runtime/Photon is not self-hostable.
- **Lock-in:** Moderate — data is open (low data lock-in) but Photon, Unity Catalog, DLT pipelines, notebooks, and workflows are platform-specific (real workflow lock-in).
- **Cost model:** **DBU** (Databricks Unit) consumption-based, on top of (classic) or bundled with (serverless) cloud compute. Serverless SQL ~\$0.70/DBU US (regional variation); per-DBU rates ~\$0.35–\$0.95 depending on product/tier ([Flexera pricing guide](https://www.flexera.com/blog/finops/databricks-pricing-guide/)). Cheap-at-small can invert badly — idle/oversized clusters and small-query overhead drive surprise bills.

## Hardware / deployment
- **Resource profile:** Memory- and CPU-bound for compute (Spark/Photon), I/O-bound on object-store reads; working set need not fit in RAM (spills to disk/shuffle), but RAM pressure and shuffle dominate large-join performance.
- **Storage assumptions:** Cloud **object storage** (network-attached, high-latency, high-throughput) — designed around S3/ADLS/GCS economics, not local NVMe. Small random reads are expensive; large sequential scans are the sweet spot.
- **Footprint:** Clustered/distributed and **serverless** options; not embedded, not single-node-first. Compute is ephemeral against durable object storage.
- **Deployment:** SaaS on the three major clouds; classic compute runs in the customer's VPC/account (control plane in Databricks'), serverless runs in Databricks' account. Kubernetes is not the user-facing deployment model — cluster management is abstracted by the platform.

## Bottom line
Reach for Databricks when you have large-scale analytics, ETL, streaming, and ML over a shared open table format and want one governed platform instead of separate lake/warehouse/ML stacks. Do not reach for it as an OLTP database, a low-latency application backend, or for small datasets where [duckdb](duckdb.md)/[postgresql](postgresql.md) are dramatically cheaper. The single biggest gotcha is **cost and operational hygiene**: DBU spend balloons with idle/oversized clusters and small-file neglect, and "ACID" means **per-table WriteSerializable**, not a free OLTP transactional engine.

## Sources
- [What are ACID guarantees on Databricks? (official docs)](https://docs.databricks.com/aws/en/lakehouse/acid)
- [What is Photon? (official docs)](https://docs.databricks.com/aws/en/compute/photon)
- [Compute configuration reference (official docs)](https://docs.databricks.com/aws/en/compute/configure)
- [Multi-cluster writes to Delta Lake Storage in S3 (delta.io)](https://delta.io/blog/2022-05-18-multi-cluster-writes-to-delta-lake-storage-in-s3/)
- [Understanding the Delta Lake Transaction Log (Databricks blog)](https://www.databricks.com/blog/2019/08/21/diving-into-delta-lake-unpacking-the-transaction-log.html)
- [Introducing Databricks Optimized Autoscaling (Databricks blog)](https://www.databricks.com/blog/2018/05/02/introducing-databricks-optimized-auto-scaling.html)
- [Databricks pricing guide 2026 (Flexera)](https://www.flexera.com/blog/finops/databricks-pricing-guide/)
- [Understanding Delta Lake's consistency model (Jack Vanlightly)](https://jack-vanlightly.com/analyses/2024/4/29/understanding-delta-lakes-consistency-model)
