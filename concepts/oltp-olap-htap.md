---
name: OLTP / OLAP / HTAP
slug: oltp-olap-htap
summary: The workload axis — many small transactional writes (OLTP) vs few huge analytical scans (OLAP) vs the contested promise of doing both on one system (HTAP).
last_researched: 2026-06-04
---

# OLTP / OLAP / HTAP

> The single most useful question to classify a database: **what shape is the workload?** It drives
> storage layout (row vs column), indexing, and concurrency design more than anything else.

## OLTP — Online Transaction Processing
Many concurrent, short transactions touching **few rows** each (point lookups, single-row
inserts/updates); latency-sensitive; correctness-critical. Favors **row-stores**, B-tree indexes
(see [lsm-vs-btree](lsm-vs-btree.md)), and strong [isolation](isolation-levels.md)/[mvcc](mvcc.md). Examples:
[postgresql](../engines/postgresql.md), [mysql](../engines/mysql.md), [oracle](../engines/oracle.md), [microsoft-sql-server](../engines/microsoft-sql-server.md).

## OLAP — Online Analytical Processing
Few, long-running queries that **scan/aggregate huge row counts** over few columns; throughput- and
scan-efficiency-oriented; tolerant of staleness. Favors **column-stores** (read only needed columns,
great compression), vectorized/MPP execution, and [storage-compute-separation](storage-compute-separation.md). Examples:
[snowflake](../engines/snowflake.md), [google-bigquery](../engines/google-bigquery.md), [amazon-redshift](../engines/amazon-redshift.md), [clickhouse](../engines/clickhouse.md), [databricks](../engines/databricks.md).

## Row-store vs column-store — the physical root cause
- **Row-store** — all columns of a row stored together → cheap to read/write a whole row (OLTP).
- **Column-store** — each column stored contiguously → cheap to scan one column over millions of
  rows, compresses well (OLAP), but row-at-a-time writes/updates are expensive.

This is why one layout is bad at the other workload, and why **HTAP is hard**.

## HTAP — Hybrid Transactional/Analytical Processing
The claim: serve OLTP and OLAP on **one system** without ETL to a separate warehouse. The honest
question is **how it physically separates the two**, because a single layout can't be optimal for
both. Legitimate mechanisms:
- A **columnar secondary copy/index** alongside the row-store ([microsoft-sql-server](../engines/microsoft-sql-server.md)
  columnstore, [oracle](../engines/oracle.md) In-Memory column store, [singlestore](../engines/singlestore.md) rowstore+columnstore).
- A **delta row-store + columnar main**, merged in background ([singlestore](../engines/singlestore.md), [apache-druid](../engines/apache-druid.md)).
- **Separate replicas** with different layouts fed by the same log ([tidb](../engines/tidb.md) TiFlash columnar Raft
  learners).

⚠️ A vague "HTAP" with no stated separation mechanism is a marketing flag — note it as such. The
real cost is usually some staleness between the transactional and analytical sides, and/or resource
contention.

## How to use it on engine pages
Pin the engine to OLTP / OLAP / HTAP, name the storage layout (row/column/hybrid), and for any HTAP
claim describe the physical separation. This is the top-level split in [decision-guide](../decision-guide.md).
