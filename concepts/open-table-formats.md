---
name: Open Table Formats
slug: open-table-formats
summary: The metadata layer that turns a pile of Parquet files in object storage into a transactional table — Iceberg, Delta, Hudi, Paimon. They give the lake ACID, time travel, and schema evolution; they are not engines.
last_researched: 2026-06-04
---

# Open Table Formats

> An **open table format** is a specification + metadata layer over columnar files (usually Parquet)
> in object storage. It records which files make up a table *right now* (snapshots), enabling **ACID
> commits, time travel, schema/partition evolution, and row-level updates/deletes** — the management
> guarantees that make the [lakehouse](lakehouse.md) work. A format is **not** a query engine and not a database;
> engines ([apache-spark-sql](../engines/apache-spark-sql.md), [trino](../engines/trino.md), [snowflake](../engines/snowflake.md), [apache-flink](../engines/apache-flink.md), [duckdb](../engines/duckdb.md)) read/write it.

## How they work
A write creates new data files plus a new **metadata snapshot**; a commit **atomically swaps** the
table's current pointer (via a [catalog](data-catalog.md) or atomic file rename). Readers see a
consistent snapshot; concurrent writers use **optimistic concurrency** (detect conflict at commit,
retry). Deletes/updates use either **copy-on-write** (rewrite affected files) or **merge-on-read**
(write delete/change files, merge at query time) — the central performance trade-off.

## The four
- **[apache-iceberg](../engines/apache-iceberg.md)** — the vendor-neutral standard (Netflix-born, ASF). Hidden partitioning,
  full schema/partition evolution, snapshot isolation, a well-defined **REST catalog** spec; broadest
  multi-engine support. The de facto default for new lakehouses.
- **[delta-lake](../engines/delta-lake.md)** — Databricks-born (Linux Foundation). A JSON+checkpoint transaction log over
  Parquet; deeply integrated with [databricks](../engines/databricks.md)/[apache-spark-sql](../engines/apache-spark-sql.md); "Delta UniForm" exposes
  Iceberg-compatible metadata. Best inside the Databricks ecosystem.
- **[apache-hudi](../engines/apache-hudi.md)** — Uber-born; pioneered **upserts/incremental** processing and CDC ingestion on
  the lake; copy-on-write and merge-on-read tables; strong for mutable, streaming-fed data.
- **[apache-paimon](../engines/apache-paimon.md)** — Flink-born ([apache-flink](../engines/apache-flink.md)); an **[LSM](lsm-vs-btree.md)-based** streaming
  lakehouse format built for high-frequency updates and streaming reads/writes.

## What they share vs differ
- **Shared:** ACID snapshots, time travel, schema evolution, Parquet underneath, optimistic commits.
- **Differ:** catalog story (Iceberg's REST catalog vs Delta's log), update strategy defaults
  (CoW vs MoR), streaming-first (Hudi/Paimon) vs batch-first (Iceberg/Delta), and how vendor-neutral
  the governance is (Iceberg most, Delta historically Databricks-leaning).

## Caveats to flag
Table-format ACID is **table-level optimistic**, not row-level [mvcc](mvcc.md) — high-concurrency small
writes cause commit conflicts and metadata/small-file bloat needing **compaction**. Interop claims
("any engine can read it") depend on engine + catalog support and write vs read-only capability —
verify, don't assume.

## How to use it on engine pages
For any warehouse/lake engine, state which formats it can **read** vs **write**, the update strategy,
and the catalog it uses. Tie back to [lakehouse](lakehouse.md) and [data-catalog](data-catalog.md).
