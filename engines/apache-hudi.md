---
name: Apache Hudi
slug: apache-hudi
adjacent: true
rank: n/a
category: table-format
data_model: Open lakehouse table format (mutable, upsert/CDC-oriented)
license: Apache License 2.0 (permissive)
summary: Open table format built around record-level upserts, deletes, and incremental change streams on object storage — the table format that treats the lake like a mutable CDC sink.
last_researched: 2026-06-04
confidence: high
---

# Apache Hudi

> An open lakehouse table format whose differentiator is first-class record-level **upserts/deletes and incremental "change stream" reads** — built for high-frequency CDC ingestion, not just appending columnar files.

## Identity / role
- **What it is:** an open [table format](../concepts/open-table-formats.md) plus an ingestion/table-management layer that sits on top of columnar files (Parquet base files, Avro log files) in object storage (S3/GCS/ADLS/HDFS). It adds a transaction **timeline**, indexing, and table services (compaction, cleaning, clustering) so a folder of files behaves like a mutable, versioned table. Pairs with the [lakehouse](../concepts/lakehouse.md) pattern and [storage-compute-separation](../concepts/storage-compute-separation.md).
- **What it is NOT:** not a query engine — it has no compute of its own; engines like [apache-spark-sql](apache-spark-sql.md), [apache-flink](apache-flink.md), [trino](trino.md), Presto, and [starrocks](starrocks.md) do the reading/writing. Not a database server (no always-on process owning the data; correctness comes from the on-storage timeline + writers). Workload is [OLAP/streaming-ingest](../concepts/oltp-olap-htap.md), not OLTP.
- **Distinctive stance:** where [apache-iceberg](apache-iceberg.md) and Delta were originally append-and-snapshot oriented, Hudi was designed from the start (at Uber, ~2016) for **mutable upsert workloads** — keyed records, dedup, and incremental pull of *changes* (including updates and deletes), not just new appends.

## How it fits
- **Storage layout:** data lives in **file groups**, each a sequence of **file slices**. A slice = one columnar **base file** (Parquet) at a commit instant + a set of row-oriented **log files** (Avro) holding inserts/updates/deletes written since that base file ([Hudi table types](https://hudi.apache.org/docs/table_types/)).
- **Two table types** ([docs](https://hudi.apache.org/docs/table_types/)):
  - **Copy-on-Write (CoW):** every update rewrites the affected base Parquet file → fast reads, slow/write-amplified writes; good for read-heavy tables.
  - **Merge-on-Read (MoR):** updates append to delta **log files** and are merged at read time, then folded into base files by background **compaction** → low write latency / near-real-time ingest, with read-time merge cost (or stale-but-fast "read-optimized" queries).
- **Timeline:** an ordered log of actions (commits, delta-commits, compaction, cleans, clustering, rollback) keyed by monotonically increasing instant timestamps. It is the source of truth for atomicity, snapshot isolation, and time travel. Hudi 1.0 reorganized this into an **LSM-tree timeline** so metadata scales to millions of commits ([LSM timeline blog](https://hudi.apache.org/blog/2025/05/29/lsm-timeline/)).
- **Indexing — the part that makes upserts cheap:** Hudi maintains indexes (in a metadata table) to map record keys → file groups so a write knows where to update without scanning: **Bloom filter index**, **Record-Level Index (RLI)** (global key→location map, sharded for scale), **column-stats / partition-stats** for file pruning, and a **secondary index** (Spark, as of 1.x) ([secondary index blog](https://hudi.apache.org/blog/2025/04/02/secondary-index/)). Flink keeps key→location mappings in operator state instead.
- **What it pairs with:** Kafka → Flink/Spark CDC ingestion → Hudi MoR table → queried by Trino/Presto/Spark/StarRocks; integrates with [change-data-capture](../concepts/change-data-capture.md) sources (Debezium) via its ingestion utilities (Hudi Streamer / DeltaStreamer). Apache **XTable** (ex-OneTable) translates Hudi metadata to/from Iceberg/Delta for cross-format interop.

## Guarantees & consistency
- **Transactions / ACID:** atomic commits via the timeline; a commit is visible only after its completed-instant is written. Provides **snapshot isolation** between readers and writers; readers see a consistent file-slice view as of a timeline instant ([Hudi concepts](https://hudi.apache.org/docs/concepts.html); [LSM timeline](https://hudi.apache.org/blog/2025/05/29/lsm-timeline/)). See [isolation-levels](../concepts/isolation-levels.md).
- **Concurrency control:**
  - Default historically a **single-writer** model (table services run inline/async but writes serialize).
  - **Optimistic Concurrency Control (OCC)** for multi-writer: conflicting writers to the same file group abort at commit; requires an external lock provider (Zookeeper/DynamoDB/Hive metastore) to guard the commit ([RFC-22 / concurrency control](https://hudi.apache.org/blog/2025/01/28/concurrency-control/)).
  - **Non-Blocking Concurrency Control (NBCC)** added in Hudi 1.0: multiple writers append log files to the *same* file group concurrently without serializing; conflicts are deferred and resolved at compaction/read time. Only the commit-metadata write needs a lock ([concurrency control blog](https://hudi.apache.org/blog/2025/01/28/concurrency-control/)). Note in practice: NBCC suits concurrent ingest + table services; it does not make arbitrary cross-row transactional invariants safe — it resolves per-record ordering, not application-level constraints.
- **Delivery / CDC semantics:** Hudi Streamer + Spark/Flink writers target **exactly-once** ingestion (checkpoint offsets committed atomically with the Hudi commit). Hudi exposes **incremental queries** that return inserts *and* updates *and* deletes since an instant — a true change stream, which append-only incremental reads in some formats cannot do.
- **Durability / data-loss window:** durability rests on the underlying object store's durability and on writers fsyncing/committing; an uncommitted in-flight write is rolled back and leaves no visible data. See [wal-and-durability](../concepts/wal-and-durability.md). CAP/[cap-pacelc](../concepts/cap-pacelc.md): **N/A** — Hudi is not a replicated distributed database; availability/partition behavior is that of the object store and the engine.

## Interfaces & integration
- **Write/manage:** Spark (DataSource + SQL), Flink (SQL/DataStream), Hudi **Streamer/DeltaStreamer** (Kafka/Debezium/file sources), Java client. Spark SQL supports `MERGE INTO`, `UPDATE`, `DELETE`, time-travel, and `CALL` procedures for table services.
- **Read:** snapshot, **read-optimized** (base files only, fast but possibly stale on MoR), and **incremental** queries. Engines that read Hudi: [Spark](apache-spark-sql.md), [Flink](apache-flink.md), Presto, [Trino](trino.md), [StarRocks](starrocks.md), Hive, Impala, Amazon Athena/EMR, and Hudi-aware connectors. Secondary-index pushdown is currently Spark-first, with Flink/Trino/Presto support trailing per release.
- **Catalogs:** integrates with Hive Metastore, AWS Glue, and [catalog](../concepts/data-catalog.md) sync; ⚠️ unverified — the depth of native REST-catalog parity with Iceberg's catalog ecosystem.
- **Interop:** Apache **XTable** exposes a Hudi table's metadata as Iceberg/Delta (and vice versa) without copying data, easing multi-engine estates.

## Operations & maturity
- **Maturity:** Apache top-level project; production at very large scale (origin at Uber; used by Amazon, Robinhood, Walmart, ByteDance, etc.). Hudi **1.0 GA** (late 2024 / 2025 line) brought the LSM timeline, NBCC, expanded indexing, and a "database-like" experience push ([1.0 preview](https://www.onehouse.ai/blog/apache-hudi-1-0-preview-a-database-experience-on-the-data-lake)).
- **Ops burden:** the highest of the three major table formats. You must reason about table type (CoW vs MoR), index choice, and a set of **table services** — compaction, cleaning (old-version GC), clustering, and (for multi-writer) an external lock provider. Misconfigured compaction/cleaning is the classic failure mode: log files pile up, read-time merge gets slow, or cleaning lags and storage/metadata bloats. Small-file management and metadata-table upkeep need attention.
- **Known sharp edges:** read-optimized queries on MoR can serve stale data if compaction falls behind; engine support for newer features (secondary index, NBCC) lags Spark; historically considered harder to tune than Iceberg/Delta for casual users.
- **Governance:** ASF community project. Commercial steward/major contributor is **Onehouse** (founded by Hudi's creators), which also drives XTable — worth noting when reading "Hudi vs X" comparisons authored by vendors.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Open vs vendor-controlled:** genuinely open (ASF); not gated behind a single vendor's runtime. Onehouse offers a managed service but the format and engine are usable standalone.
- **Self-host vs managed:** fully self-hostable on any object store + Spark/Flink. Managed paths: Onehouse, AWS EMR/Glue (native Hudi support), Athena, plus DIY on Kubernetes/EMR/Dataproc.
- **Cost model:** no license cost; you pay for object storage + the compute that ingests, compacts, and queries. Cost is dominated by **table-service compute** (compaction/clustering) and read-time merge on MoR — under-provision these and either cost or latency spikes.

## Bottom line
- Reach for Hudi when your central problem is **mutable, high-frequency ingestion** — CDC replication of operational databases, streaming upserts, dedup on a primary key, and consumers that need the *change stream* (updates and deletes), not just appends. Its record-level index + MoR + incremental queries are best-in-class for that pattern.
- Do **not** reach for it if you mainly have append-only analytics tables, multi-engine read estates, or a team that wants minimal table-tuning — [apache-iceberg](apache-iceberg.md) (broad engine/catalog ecosystem) or Delta ([databricks](databricks.md)-native) are simpler defaults there. Also wrong for low-latency point lookups / OLTP — it's a lake table format, not a serving store like [apache-druid](apache-druid.md)/[clickhouse](clickhouse.md).
- **Biggest gotcha:** operational complexity. The upsert/CDC power comes bundled with compaction, cleaning, indexing, and (for multi-writer) lock-provider decisions; if those table services aren't run and tuned, MoR reads go stale/slow or storage and metadata bloat. The advanced 1.0 features (NBCC, secondary index) are also still Spark-leading, so verify your query engine actually supports the feature you're banking on.

## Sources
- [Apache Hudi — Table & Query Types](https://hudi.apache.org/docs/table_types/)
- [Apache Hudi — Concepts](https://hudi.apache.org/docs/concepts.html)
- [Apache Hudi — Concurrency Control (OCC & NBCC)](https://hudi.apache.org/blog/2025/01/28/concurrency-control/)
- [Apache Hudi — LSM Timeline](https://hudi.apache.org/blog/2025/05/29/lsm-timeline/)
- [Apache Hudi — Secondary Index](https://hudi.apache.org/blog/2025/04/02/secondary-index/)
- [Apache Hudi — Querying Data](https://hudi.apache.org/docs/querying_data.html)
- [Onehouse — Hudi 1.0 Preview: A Database Experience on the Data Lake](https://www.onehouse.ai/blog/apache-hudi-1-0-preview-a-database-experience-on-the-data-lake)
- [Onehouse — Hudi vs Delta Lake vs Iceberg feature comparison](https://www.onehouse.ai/blog/apache-hudi-vs-delta-lake-vs-apache-iceberg-lakehouse-feature-comparison) (vendor-authored; cross-checked against primary docs)
- [Dremio — Comparison of Data Lake Table Formats](https://www.dremio.com/blog/comparison-of-data-lake-table-formats-apache-iceberg-apache-hudi-and-delta-lake/)
