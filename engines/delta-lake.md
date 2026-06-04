---
name: Delta Lake
slug: delta-lake
adjacent: true
rank: n/a
category: table-format
data_model: Open table format (ACID metadata layer over Parquet on object storage)
license: Apache 2.0 (Linux Foundation); spec governed by Delta Lake project, originated and steered by Databricks
summary: Open ACID table format that turns a directory of Parquet files plus a JSON/checkpoint transaction log into a versioned, transactional table; native to Spark/Databricks.
last_researched: 2026-06-04
confidence: high
---

# Delta Lake

> A transaction-log layer over Parquet on object storage that gives a Parquet directory ACID writes, snapshot-isolation reads, and time travel — a table *format*, not an engine, and historically Databricks/[apache-spark-sql](apache-spark-sql.md)-centric.

## When to use

**Use Delta Lake if:**
- ✅ Your lakehouse is centered on [apache-spark-sql](apache-spark-sql.md)/[databricks](databricks.md) and you want battle-tested ACID, `MERGE`, time travel, and CDC over Parquet with minimal fuss.
- ✅ You need atomic multi-file writes and snapshot-isolation reads during concurrent writes that raw Parquet directories can't give.
- ✅ You're fine pairing it with object storage and a compute engine (it has no compute of its own).

**Avoid Delta Lake if:**
- ❌ You need a truly engine-neutral, multi-writer-across-many-engines format — Iceberg's catalog/engine neutrality is the cleaner fit.
- ❌ You're running naïve multi-writer Delta on plain S3 without the DynamoDB LogStore — correctness depends on atomic put-if-absent and you can silently lose commits.
- ❌ You want an OLTP store or high-frequency tiny writes — you'll drown in small files and constant OCC retries.

## Identity / role
- **What it IS:** an open [table format](../concepts/open-table-formats.md) — a metadata/protocol layer that makes a collection of Parquet data files behave as a single transactional table. The unit of truth is the `_delta_log/` transaction log (ordered JSON commits, periodically compacted into Parquet checkpoints) sitting alongside the data files.
- **What it is NOT:** not a query engine, not a database server, not storage. It has no compute of its own and no running process; an engine ([apache-spark-sql](apache-spark-sql.md), [trino](trino.md), [duckdb](duckdb.md), [clickhouse](clickhouse.md), [apache-flink](apache-flink.md)) reads the log and the Parquet files. It is the metadata + protocol, paired with object storage (S3/ADLS/GCS) and a compute engine. See [lakehouse](../concepts/lakehouse.md).
- **Role in the stack:** the table/format layer of a [lakehouse](../concepts/lakehouse.md) — the same niche as Apache Iceberg and Apache Hudi. Workload is analytical / [OLAP](../concepts/oltp-olap-htap.md) over [columnar](../concepts/columnar-storage.md) Parquet; it is not an OLTP store.

## How it fits
- **Architecture:** data lives as immutable Parquet files in a directory; every change (add/remove file, schema change, metadata) is an *atomic commit* appended to `_delta_log/` as a numbered JSON file (`00000000000000000001.json`, ...). A reader reconstructs table state by replaying the log up to a version; checkpoints (Parquet snapshots of state every ~10 commits) bound replay cost. This is the same metadata-over-object-store pattern as Iceberg, but log-based (linear commit history) rather than Iceberg's tree-of-manifests snapshot pointer.
- **Solves:** atomic multi-file writes, consistent reads during concurrent writes, schema enforcement/evolution, `UPDATE`/`DELETE`/`MERGE` and time travel — none of which raw Parquet directories offer.
- **Pairs with:** [apache-spark-sql](apache-spark-sql.md)/[databricks](databricks.md) (first-class read+write), and read/write from [trino](trino.md), [apache-flink](apache-flink.md), [duckdb](duckdb.md) (`delta` extension), [clickhouse](clickhouse.md), plus Delta Kernel-based connectors. **UniForm** (Universal Format, GA since Delta 3.0) writes Iceberg/Hudi-compatible metadata alongside the Delta log so Iceberg/Hudi readers can query the same files — but ⚠️ UniForm-Iceberg historically requires **deletion vectors disabled** ([per the project: Iceberg compatibility precludes DVs](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)).
- **Key features:** deletion vectors (merge-on-read soft deletes — mark rows dead in a bitmap instead of rewriting files), liquid clustering (adaptive multi-dimensional data layout replacing Hive partitioning + Z-order), Change Data Feed ([CDC](../concepts/change-data-capture.md) output), row tracking, column mapping, and (Delta 4.0) catalog-managed/coordinated commits.

## Guarantees & consistency
- **ACID:** yes, at the single-table level, via **optimistic concurrency control** — writers read a snapshot, stage new Parquet, then attempt to commit the next log version; on conflict the loser retries or fails ([Delta concurrency-control docs](https://docs.delta.io/concurrency-control/)). Reads get **snapshot isolation** (consistent view of one log version, even during concurrent writes). No multi-table transactions.
- **The commit depends on the storage layer providing mutual exclusion (atomic put-if-absent).** This is the single biggest gotcha. HDFS and Azure/GCS provide it natively. **Plain S3 historically did NOT** offer put-if-absent, so multi-writer correctness on S3 required the `S3DynamoDBLogStore` (DynamoDB conditional `PutItem` as an external lock) to avoid two writers clobbering the same log version ([Delta on S3](https://delta.io/blog/2022-05-18-multi-cluster-writes-to-delta-lake-storage-in-s3/)). S3 added conditional writes (Aug 2024), easing this, but cross-engine multi-writer setups still need a coordination story (Delta 4.0 "coordinated commits" / catalog-managed tables address this). See [isolation-levels](../concepts/isolation-levels.md).
- **Durability / data-loss window:** commit is durable once the log JSON is durably written to object storage; partial Parquet writes that never get a log entry are simply ignored (invisible). See [wal-and-durability](../concepts/wal-and-durability.md). CAP/[cap-pacelc](../concepts/cap-pacelc.md): N/A as a format — properties come from the underlying object store (typically strongly consistent today) plus the mutual-exclusion mechanism.
- No serializable cross-engine guarantees beyond what OCC + the LogStore provide; conflicting concurrent MERGE/UPDATE on overlapping files will fail one writer rather than silently corrupt.

## Interfaces & integration
- **No query language of its own.** You use the host engine's SQL/DataFrame API; Delta adds `MERGE INTO`, `UPDATE`, `DELETE`, `OPTIMIZE`, `VACUUM`, time travel (`VERSION AS OF` / `TIMESTAMP AS OF`), `CREATE TABLE ... USING DELTA`.
- **Write path is strongest in Spark/[databricks](databricks.md);** broad reader support elsewhere. **Delta Kernel** (Java and Rust libraries) gives connector authors stable APIs that hide protocol details, widening engine support; `delta-rs` (Rust + Python `deltalake`) enables non-JVM read/write.
- **Reads/writes from:** [apache-spark-sql](apache-spark-sql.md), [trino](trino.md), Presto, [apache-flink](apache-flink.md), [duckdb](duckdb.md), [clickhouse](clickhouse.md), Athena, Snowflake (via Iceberg/UniForm), BigQuery (external). **Interop:** UniForm + Unity Catalog's Iceberg REST API let Iceberg-only engines read Delta tables, narrowing the historical interop gap vs Iceberg.
- **Catalog:** integrates with Hive Metastore, AWS Glue, and Unity Catalog ([data-catalog](../concepts/data-catalog.md)); Delta 4.0 adds catalog-managed tables where the catalog (not the filesystem) coordinates commits.

## Operations & maturity
- **Mature and heavily deployed** — the default format on Databricks for years; very large production footprint. Reliable for Spark-centric batch + streaming lakehouses.
- **Day-2 ops:** must run `OPTIMIZE` (file compaction / liquid clustering) and `VACUUM` (delete tombstoned files past the retention window) to control small-file proliferation and storage cost; `VACUUM` too aggressively can break in-flight readers/time travel. Log checkpoints are managed automatically.
- **Known failure modes:** S3 multi-writer without DynamoDB LogStore → silent lost updates (the classic footgun); small-file explosion from frequent streaming commits; deletion-vector vs UniForm-Iceberg incompatibility; protocol reader/writer version mismatches when a new feature bumps the table's required protocol version and older engines can no longer read/write.
- **Governance:** open-sourced under the **Linux Foundation** (Delta Lake project), Apache 2.0. In practice Databricks is the dominant contributor and the protocol's most advanced features land in Databricks Runtime first, so it is *open but vendor-influenced* — less neutral than Iceberg's ASF community, a perception the 2024 Databricks–Tabular acquisition and the Delta/Iceberg convergence push are meant to soften.

## Licensing & cost
- **License:** Apache 2.0, permissive — see [license-taxonomy](../concepts/license-taxonomy.md). The spec (`PROTOCOL.md`) and reference libraries are open.
- **Self-host vs managed:** the format is free to self-host on any object store with any supported engine. Cost is the underlying object storage + whatever compute engine you run; the format itself adds no license fee. Managed convenience (and the newest features earliest) comes via [databricks](databricks.md).
- **Lock-in:** format is open, but the richest tooling/perf and earliest features are Databricks-first; teams sometimes feel pulled toward Databricks even though the spec is open.

## Bottom line
- Reach for Delta Lake if your lakehouse is centered on [apache-spark-sql](apache-spark-sql.md)/[databricks](databricks.md) and you want battle-tested ACID, `MERGE`, time travel, and CDC over Parquet with minimal fuss. It is a table *format* — you still need an engine and object storage. Avoid making it your primary choice if you need a truly engine-neutral, multi-writer-across-many-engines format (Iceberg's broader catalog/engine neutrality is the cleaner fit, though UniForm narrows the gap). **Biggest gotcha:** correctness of concurrent writes depends on the storage layer's atomic put-if-absent — naïve multi-writer Delta on plain S3 without the DynamoDB LogStore can silently lose commits. Anti-pattern: using it as an OLTP store or for high-frequency tiny writes — you will drown in small files and constant OCC retries.

## Sources
- [Delta Lake PROTOCOL.md (spec)](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)
- [Concurrency control | Delta Lake docs](https://docs.delta.io/concurrency-control/)
- [Multi-cluster writes to Delta Lake on S3](https://delta.io/blog/2022-05-18-multi-cluster-writes-to-delta-lake-storage-in-s3/)
- [Storage configuration | Delta Lake docs](https://docs.delta.io/delta-storage/)
- [Delta Lake 4.0 announcement](https://delta.io/blog/2025-09-25-delta-lake-40/)
- [Announcing Delta Lake 3.0 (UniForm + Liquid Clustering)](https://www.databricks.com/blog/announcing-delta-lake-30-new-universal-format-and-liquid-clustering)
- [Liquid clustering | Delta Lake docs](https://docs.delta.io/latest/delta-clustering.html)
- [Deletion Vectors — Internals of Delta Lake](https://books.japila.pl/delta-lake-internals/deletion-vectors/)
- [Apache Iceberg vs Delta Lake (Dremio)](https://www.dremio.com/blog/apache-iceberg-vs-delta-lake/)
