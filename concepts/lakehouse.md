---
name: Lakehouse
slug: lakehouse
summary: Put a transactional table layer (an open format + catalog) directly on cheap object storage, then point many decoupled engines at it — warehouse-style SQL on data-lake economics, with no copy into a proprietary store.
last_researched: 2026-06-04
---

# Lakehouse

> A **lakehouse** is an architecture, not a product: keep data as open columnar files (Parquet/ORC)
> in object storage, add an **open table format** ([Iceberg/Delta/Hudi/Paimon](open-table-formats.md))
> that gives those files ACID transactions, schema evolution, and time travel, register them in a
> **[catalog](data-catalog.md)**, and let multiple **decoupled engines** read and write the *same*
> tables. It merges the cheap, open storage of a data lake with the management guarantees of a
> warehouse.

## The four layers
1. **Object storage** — S3 / GCS / Azure Blob: cheap, durable (11 nines), the shared substrate (see
   [storage-compute-separation](storage-compute-separation.md)).
2. **File format** — [columnar](columnar-storage.md) Parquet/ORC for scan-efficient, compressed data.
3. **Table format** — metadata that turns a directory of files into a transactional table:
   snapshots, ACID commits, hidden partitioning, schema/partition evolution, time travel. This is
   the layer that makes a "lake" behave like a "house" — see [open-table-formats](open-table-formats.md).
4. **Catalog** — tracks table identity, schema, and current snapshot; arbitrates commits and governs
   access ([data-catalog](data-catalog.md)).

## Why it matters
- **One copy, many engines.** [databricks](../engines/databricks.md), [apache-spark-sql](../engines/apache-spark-sql.md), [trino](../engines/trino.md)/[presto](../engines/presto.md),
  [snowflake](../engines/snowflake.md), [clickhouse](../engines/clickhouse.md), [starrocks](../engines/starrocks.md), [apache-flink](../engines/apache-flink.md), [duckdb](../engines/duckdb.md), [dremio](../engines/dremio.md) can all
  query the same Iceberg/Delta tables — no ETL into a vendor silo, less lock-in.
- **Warehouse features on lake economics** — ACID, updates/deletes/merges, time travel, and schema
  evolution over commodity storage.
- **Storage/compute fully separated** — scale or swap compute without moving data; the defining
  property carried over from [snowflake](../engines/snowflake.md)-style designs.

## The honest caveats
- **It's an assembly, not a database.** Concurrency control is *optimistic at the table level*
  (commit conflicts → retries), not row-level [mvcc](mvcc.md); small frequent writes create many metadata
  files and need compaction. Latency is object-storage latency — **not for OLTP** (see
  [oltp-olap-htap](oltp-olap-htap.md)).
- **Catalog is the linchpin.** Multi-engine ACID only holds if every writer goes through a catalog
  that enforces atomic snapshot swaps; mixing writers across incompatible catalogs corrupts the
  guarantee.
- **"Open" varies.** Delta's richest features historically favored [databricks](../engines/databricks.md); Iceberg's
  governance is the most vendor-neutral. Read [open-table-formats](open-table-formats.md).

## How to use it on engine/adjacent pages
For warehouses/engines, note whether they read/write open table formats (and which), and whether
they can be the *writer* or only a reader. For the table-format and catalog pages, tie back here.
Contrast with a monolithic warehouse ([snowflake](../engines/snowflake.md) native tables) where storage is managed/closed.
