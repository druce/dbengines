---
name: Apache Iceberg
slug: apache-iceberg
adjacent: true
rank: n/a
category: table-format
data_model: Open lakehouse table format
license: Apache License 2.0 (permissive)
summary: Open table format that turns object-store file collections into ACID, evolvable, engine-neutral tables — the de facto lakehouse standard.
last_researched: 2026-06-04
confidence: high
---

# Apache Iceberg

> A metadata layer over Parquet/ORC/Avro files in object storage that gives you ACID commits, schema/partition evolution, time travel, and snapshot isolation — readable and writable by many engines, owned by none.

## Identity / role
- Iceberg is a **table format**, not a query engine, not a storage system, and not a database. It is a specification (plus reference Java/Python/Rust libraries) for laying out and tracking data files so that independent compute engines agree on what rows constitute "the table." The actual data lives as Parquet/ORC/Avro files; Iceberg adds the metadata tree that makes them a transactional table.
- It sits in the **storage/table-format layer** of a [lakehouse](../concepts/lakehouse.md) (see [open-table-formats](../concepts/open-table-formats.md)): below query engines ([trino](trino.md), [apache-spark-sql](apache-spark-sql.md), [snowflake](snowflake.md), [clickhouse](clickhouse.md), [starrocks](starrocks.md), [duckdb](duckdb.md)), above object storage (S3/GCS/ADLS/HDFS). It is the principal alternative to [delta-lake](delta-lake.md) and [apache-hudi](apache-hudi.md).
- What it is **not**: it does not execute queries, does not provide a SQL planner, and does not manage compute. It also is not itself a [catalog](../concepts/data-catalog.md) — it defines a catalog *interface* but relies on an external catalog implementation (REST, AWS Glue, Hive Metastore, Nessie, Polaris, Unity) to track the current metadata pointer. Workload is firmly analytical/[OLAP](../concepts/oltp-olap-htap.md); it is not for OLTP point-write workloads.

## How it fits
- **Metadata tree (the core idea):** a catalog holds a pointer to the current **metadata file** (table schema, partition specs, snapshot list, properties). Each **snapshot** points to a **manifest list**, which points to **manifest files**, which list the actual **data files** plus per-file statistics (row counts, column min/max, null counts). A commit = atomically swapping the catalog's metadata pointer to a new metadata file (optimistic concurrency, compare-and-swap on the pointer).
- **Why it exists:** it replaces the Hive table model, where a table was "all files under a directory prefix." That model required slow, inconsistent directory listings, made atomic multi-partition changes impossible, and tied you to physical partition paths. Iceberg tracks files explicitly in metadata, enabling fast planning (no `LIST`), partition pruning via stats, and **hidden partitioning** (partition transforms like `days(ts)` are recorded in metadata, so queries need not reference partition columns and partitioning can change without rewriting data).
- **Key capabilities:** schema evolution by column ID (add/drop/rename/reorder without rewriting files), partition evolution, snapshot **time travel** and rollback, and metadata-only operations. Spec **v2** added row-level deletes (merge-on-read via position/equality delete files). Spec **v3** (preview early 2026, GA mid-2026 in major engines like Snowflake) adds **deletion vectors** (Puffin-encoded, replacing v2 positional delete files to cut write amplification), the **variant** semi-structured type, **default column values**, and **row lineage** (`_row_id`, `_last_updated_sequence_number`). ([Iceberg spec](https://iceberg.apache.org/spec/), [Google OSS blog on v3](https://opensource.googleblog.com/2025/08/whats-new-in-iceberg-v3.html))
- **Pairs with:** an external catalog (the Iceberg **REST catalog** OpenAPI spec is the converging standard — [apache-polaris](apache-polaris.md), Unity Catalog, nessie, AWS Glue/S3 Tables all speak it), plus a compute engine for reads/writes and an orchestrator (Airflow/dbt) for maintenance jobs.

## Guarantees & consistency
- **ACID via optimistic concurrency / snapshot isolation.** Readers always see a consistent snapshot; writers commit by atomically swapping the metadata pointer. On conflict, a writer retries against the new snapshot. This gives **serializable** behavior for the commit itself but the *practical* isolation level seen by concurrent writers is **snapshot isolation with optimistic retry** — concurrent appends to disjoint files generally succeed; conflicting overwrites can force retries or fail. See [isolation-levels](../concepts/isolation-levels.md).
- **The atomicity guarantee is only as strong as the catalog's compare-and-swap.** Iceberg's correctness rests on the catalog providing an atomic pointer swap. A plain S3/filesystem "catalog" without a real CAS primitive can lose the atomicity guarantee and risk lost updates under concurrent writers — this is a real and frequently-cited gotcha. Use a transactional catalog (REST/Glue/Nessie/JDBC with proper locking), not bare object-store metadata pointers, for concurrent writes. ⚠️ unverified — exact failure modes vary by catalog implementation and version; validate your specific catalog's CAS semantics.
- **Durability:** Iceberg inherits the durability of the underlying object store (e.g., S3 11-nines). There is no separate write-ahead log; durability is "commit succeeds = files + metadata are persisted in the store." No [WAL](../concepts/wal-and-durability.md) data-loss window in the database sense, but in-flight uncommitted files are simply not visible.
- **CAP:** N/A as stated — Iceberg has no cluster of its own. Consistency/availability characteristics are inherited from the object store and the catalog service.

## Interfaces & integration
- **No query language of its own.** You interact via an engine's SQL (Spark SQL, Trino SQL, Flink SQL, Snowflake SQL, Dremio, StarRocks, ClickHouse, DuckDB) or via the Java / **PyIceberg** / **iceberg-rust** libraries. Maintenance procedures (compaction, expire snapshots, rewrite manifests, remove orphan files) are exposed as engine stored procedures (e.g. Spark `CALL`).
- **Broad multi-engine interop is the headline feature.** Read/write support spans [apache-spark-sql](apache-spark-sql.md) (most complete), [apache-flink](apache-flink.md) (streaming sink/source), [trino](trino.md), [snowflake](snowflake.md) (managed + external/REST catalog), [databricks](databricks.md), Dremio, [starrocks](starrocks.md), [clickhouse](clickhouse.md), [duckdb](duckdb.md), BigQuery, Athena/EMR, and Redshift. Maturity varies: Spark/Flink/Trino are most feature-complete; some engines are read-only or lag on v2/v3 deletes.
- **Catalogs:** REST catalog spec is the interop convergence point; also Hive Metastore, AWS Glue, JDBC, Nessie (git-like branching), Polaris, Unity Catalog. [CDC](../concepts/change-data-capture.md) inflow typically lands via Flink/Spark/Kafka Connect sink jobs; downstream BI and dbt read it like any warehouse table.
- **Format interop / XTable / UniForm:** Apache XTable and Delta UniForm can expose the same Parquet files as Iceberg metadata, easing Delta↔Iceberg coexistence.

## Operations & maturity
- **Day-2 burden is real and often underestimated.** Streaming/frequent writes create many small files and (for merge-on-read) accumulating delete files; you must run periodic **compaction**, **snapshot expiration**, **manifest rewrite**, and **orphan-file cleanup** or read performance and storage cost degrade. These are explicit jobs you schedule — there is no built-in autovacuum unless your managed service provides one.
- **Maturity:** high. Originated at Netflix (Ryan Blue, Dan Weeks), donated to the ASF, top-level project since 2020; production-proven at very large scale (Netflix, Apple, LinkedIn, etc.). Widely regarded post-2024 as the winning open lakehouse format.
- **Governance / the 2024 inflection:** [databricks](databricks.md) acquired **Tabular** (the company founded by Iceberg's creators) in mid-2024 for a reported ~$1–2B, the same week [snowflake](snowflake.md) announced **Polaris** (open-source Iceberg REST catalog). This signaled industry consolidation around Iceberg as the neutral standard and pushed both Delta and Iceberg toward interop. ([Starburst summary](https://www.starburst.io/blog/snowflake-databricks-tabular-iceberg/)) The format itself remains ASF-governed and vendor-neutral; that neutrality is its main strategic asset.
- **Known failure modes:** lost updates with a non-CAS catalog (above); read-amplification from delete files under heavy MoR before compaction; small-file explosion from streaming; cross-engine version skew (an engine that only understands v2 cannot read v3 deletion vectors).

## Licensing & cost
- **Apache License 2.0** — permissive, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md). The spec and reference libraries are fully open; no vendor controls the format.
- **Self-host vs managed:** fully self-hostable (your object store + open-source engine + open-source catalog). Managed variants exist (Snowflake-managed Iceberg, Databricks, AWS S3 Tables / Glue, Dremio, Tabular-derived offerings).
- **Cost model:** Iceberg itself is free. Real cost = object storage + compute (per engine) + the operational/compute cost of maintenance jobs (compaction et al.). Lock-in risk is low at the format layer, but a **managed catalog** can become the lock-in point — choose REST-compatible catalogs to preserve engine independence.

## Bottom line
- Reach for Iceberg when you want a **single open copy of analytical data in object storage that many engines can safely read and write**, with ACID, schema/partition evolution, and time travel, and you want to avoid warehouse lock-in. It is the safest default open table format in 2026. Do **not** reach for it for OLTP, low-latency single-row lookups, or high-frequency tiny writes — that workload belongs in an [OLTP](../concepts/oltp-olap-htap.md) store or a [real-time-olap](../concepts/real-time-olap.md) engine, not a lakehouse table. The single biggest gotcha: Iceberg's ACID guarantee is **only as strong as your catalog's atomic compare-and-swap** — a "filesystem catalog" with concurrent writers can silently lose commits, and neglected compaction/expiration will quietly erode performance and cost.

## Sources
- [Apache Iceberg table spec](https://iceberg.apache.org/spec/)
- [Apache Iceberg documentation](https://iceberg.apache.org/docs/latest/)
- [What's new in Apache Iceberg v3 — Google Open Source blog](https://opensource.googleblog.com/2025/08/whats-new-in-iceberg-v3.html)
- [Snowflake: Iceberg v3 support (GA, 2026-05-07)](https://docs.snowflake.com/en/release-notes/2026/other/2026-05-07-iceberg-v3-ga)
- [AWS Prescriptive Guidance: Iceberg spec v3](https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/table-spec-v3.html)
- [Starburst: Snowflake, Databricks, Tabular, Iceberg — what it means](https://www.starburst.io/blog/snowflake-databricks-tabular-iceberg/)
- [Snowflake: configure an Iceberg REST catalog integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest)
