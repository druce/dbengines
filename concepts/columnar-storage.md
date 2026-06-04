---
name: Columnar Storage
slug: columnar-storage
summary: Store each column contiguously instead of each row — the foundation of analytical (OLAP) engines, trading cheap full-table scans and compression for expensive row-level writes.
last_researched: 2026-06-04
---

# Columnar Storage

> A **column-store** lays out a table column-by-column on disk rather than row-by-row. Analytical
> queries touch a few columns over millions of rows, so reading only those columns — already
> compressed — is the single biggest win for [OLAP](oltp-olap-htap.md).

## Why it's fast for analytics
- **Less I/O** — a query reading 3 of 80 columns reads ~3/80 of the data; a row-store reads whole rows.
- **Better compression** — a column holds one data type with low cardinality / sorted runs, so
  run-length, dictionary, delta, and bit-packing encodings shrink it 5–20×. Less bytes = less I/O.
- **Vectorized execution** — process column values in tight, SIMD-friendly batches; encodings let
  engines compute on compressed data (late materialization). Pioneered by C-Store/[vertica](../engines/vertica.md),
  MonetDB.
- **Pruning** — per-block min/max (zone maps) and partition metadata skip blocks that can't match,
  avoiding the scan entirely (see [storage-compute-separation](storage-compute-separation.md) warehouses).

## Why it's bad for OLTP
A single-row insert/update/delete must touch every column file and disturb compression, so
point-write latency is poor. Column-stores therefore favor **bulk load + append**, often with a
small uncompressed **delta/row store** for recent writes that is merged into the columnar main in
the background (the [HTAP](oltp-olap-htap.md) pattern). Updates are frequently implemented as
insert+tombstone, reclaimed by compaction.

## Where it shows up
Analytics engines and warehouses: [clickhouse](../engines/clickhouse.md), [snowflake](../engines/snowflake.md), [google-bigquery](../engines/google-bigquery.md),
[amazon-redshift](../engines/amazon-redshift.md), [vertica](../engines/vertica.md), [duckdb](../engines/duckdb.md), [apache-druid](../engines/apache-druid.md), [starrocks](../engines/starrocks.md), [exasol](../engines/exasol.md),
[sap-iq](../engines/sap-iq.md), [apache-spark-sql](../engines/apache-spark-sql.md) (Parquet/ORC), [databricks](../engines/databricks.md) (Delta). Hybrids add a columnar
**secondary** to a row-store: [microsoft-sql-server](../engines/microsoft-sql-server.md) columnstore indexes, [oracle](../engines/oracle.md) In-Memory,
[singlestore](../engines/singlestore.md), [tidb](../engines/tidb.md) TiFlash, [sap-hana](../engines/sap-hana.md).

## How to use it on engine pages
State row vs column vs hybrid and tie it to the workload. For an HTAP claim, say how the two layouts
coexist (delta+main, secondary index, separate replica) — see [oltp-olap-htap](oltp-olap-htap.md). Relates to
[lsm-vs-btree](lsm-vs-btree.md) (orthogonal: an engine can be columnar *and* LSM-organized).
