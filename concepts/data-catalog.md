---
name: Data Catalog
slug: data-catalog
summary: The metadata service that tracks what tables exist, their schema and current snapshot, and who may touch them — the linchpin that makes multi-engine lakehouse ACID and governance possible.
last_researched: 2026-06-04
---

# Data Catalog

> In a [lakehouse](lakehouse.md), the **catalog** is the source of truth for **table identity**: it maps a table
> name to its schema and its *current* [snapshot](open-table-formats.md), and arbitrates commits so
> that many engines can read and write the same tables safely. Without a shared catalog, multi-engine
> ACID and consistent governance fall apart.

## Two jobs
1. **Technical metastore** — table → location, schema, partitioning, current snapshot pointer; the
   thing engines query to plan and the thing that **atomically swaps** the snapshot on commit.
2. **Governance / discovery** — access control, lineage, auditing, search, tags. Modern "catalogs"
   increasingly bundle both.

## The landscape
- **[hive-metastore](../engines/hive-metastore.md)** — the original (Hadoop-era) table metastore; ubiquitous, Thrift API, still
  widely used, but heavyweight and not designed for modern table-format commit semantics.
- **[unity-catalog](../engines/unity-catalog.md)** — Databricks' governance + metastore for the [lakehouse](lakehouse.md) (now open-sourced);
  unified ACL/lineage across tables, files, ML, and AI assets.
- **[apache-polaris](../engines/apache-polaris.md)** — open **Iceberg REST catalog** (donated by Snowflake to the ASF); a
  vendor-neutral implementation of the Iceberg catalog spec, so any Iceberg engine can share tables.
- **Project Nessie** — git-like catalog with **branches/tags** and cross-table transactions over
  Iceberg ("data version control").
- **AWS Glue Data Catalog** — managed metastore for the AWS analytics stack (Athena/EMR/Redshift).

## Why the REST catalog spec matters
[apache-iceberg](../engines/apache-iceberg.md)'s **REST catalog** standardized the commit protocol so the catalog (not the
client) owns atomic snapshot swaps and credential vending. This is what lets [snowflake](../engines/snowflake.md),
[apache-spark-sql](../engines/apache-spark-sql.md), [trino](../engines/trino.md), [dremio](../engines/dremio.md), and [apache-flink](../engines/apache-flink.md) write the *same* Iceberg tables
without corrupting each other — the catalog is the concurrency arbiter.

## Caveats to flag
- **The catalog is a single point of correctness.** Two engines writing the same table through
  *different* catalogs can break atomicity — interop requires a *shared* catalog.
- **Governance lock-in** — Unity Catalog/Glue tie governance to a vendor; open Iceberg REST catalogs
  (Polaris/Nessie) are the neutral path.

## How to use it on engine/adjacent pages
For lakehouse engines, name which catalog(s) they support and whether they can write through a shared
catalog. Tie back to [lakehouse](lakehouse.md) and [open-table-formats](open-table-formats.md).
