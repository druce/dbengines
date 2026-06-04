---
name: Dremio
slug: dremio
adjacent: true
rank: n/a
category: query-engine
data_model: Lakehouse SQL query engine + semantic layer
license: Apache 2.0 core (dremio-oss); proprietary Enterprise/Cloud editions
summary: Apache Arrow-based SQL query engine over object-storage lakehouses, with a built-in semantic layer and Iceberg-materialized "Reflections" for BI acceleration.
last_researched: 2026-06-04
confidence: medium
---

# Dremio

> A distributed SQL engine that queries Iceberg/Parquet on object storage directly, fronting it with a virtual-dataset semantic layer and auto-substituted "Reflections" so BI tools get warehouse-like speed without ETL into a warehouse.

## Identity / role
- **What it is:** an MPP **SQL query engine** for the [lakehouse](../concepts/lakehouse.md) — coordinator + executor nodes (Java) that read/write [Iceberg](../concepts/open-table-formats.md), Parquet, and federated sources, plus a built-in **semantic layer** (virtual datasets/views) and an Iceberg-based **catalog**. It competes most directly with [trino](trino.md), [Spark SQL](apache-spark-sql.md), [starrocks](starrocks.md) (lakehouse mode), and as a query layer against [databricks](databricks.md)/[snowflake](snowflake.md).
- **What it is NOT:** not a storage engine and not a database in the [OLTP](../concepts/oltp-olap-htap.md) sense — it owns no primary data format; data lives in your object store as Iceberg/Parquet. It is also not just a connector: it adds query acceleration (Reflections), caching, and a governed semantic layer on top of the lake.
- Workload: interactive/BI analytics ([OLAP](../concepts/oltp-olap-htap.md)) and ad-hoc SQL over the lake.

## How it fits
- **Compute–storage separation** ([storage-compute-separation](../concepts/storage-compute-separation.md)): executors are stateless and elastic; all data sits in S3/ADLS/GCS/HDFS or federated DBs. Internal in-memory format is **Apache Arrow** (Dremio co-created Arrow), with vectorized execution and Arrow Flight for high-throughput client transfer.
- **Reflections:** physically optimized materializations (raw or aggregation) stored as Iceberg tables on your lake. A cost-based optimizer transparently rewrites a user's SQL-against-a-view to read the cheapest Reflection — the user never references it directly. This is the headline differentiator vs. plain Trino. Functionally a managed materialized-view/cube layer; you must still choose which views to reflect, partitioning/sort, and refresh cadence, and stale/over-broad Reflections are the main tuning burden.
- **Columnar Cloud Cache (C3):** executor-local NVMe cache of Parquet/columnar reads from object storage, narrowing the latency gap to cloud storage and cutting egress.
- **Federation:** queries and joins across object storage + RDBMS (Postgres, MySQL, SQL Server, Oracle), Mongo, Elasticsearch, and other lakehouse catalogs, presented through one semantic layer.
- **Catalog:** historically **Dremio Arctic**, built on **Project Nessie** ("Git for data" — branch/tag/commit, multi-table transactions on Iceberg). Current "Open Catalog" is built on **Apache Polaris (incubating)**, the Iceberg REST catalog donated by Snowflake; Dremio can also consume external Polaris/Nessie/Glue/Hive catalogs. Nessie and Polaris are separately governed open-source projects.

## Guarantees & consistency
- **Transactions:** ACID semantics come from the underlying [Iceberg](../concepts/open-table-formats.md) table format (snapshot isolation via optimistic concurrency on the catalog), not from a Dremio transaction manager. Multi-statement/multi-table transactions exist only via the Nessie/Arctic catalog's commit/branch model, not classic interactive BEGIN/COMMIT across arbitrary sources.
- **Query consistency:** reads see a committed Iceberg snapshot; results reflect the latest committed snapshot at planning time. With Nessie branching, you can pin reads to a branch/tag for reproducibility.
- **Federated sources:** correctness/consistency are inherited from the source system; cross-source joins give no global isolation guarantee. ⚠️ unverified — Dremio has no published Jepsen-style formal analysis; treat strong-consistency claims as scoped to Iceberg snapshot semantics.
- **Durability:** ⚠️ unverified [wal-and-durability](../concepts/wal-and-durability.md) — durability is the object store's + Iceberg metadata's; executors are stateless, so a node crash loses in-flight queries, not committed data. [cap-pacelc](../concepts/cap-pacelc.md)/[isolation-levels](../concepts/isolation-levels.md): N/A as engine properties — Dremio is a query layer, isolation is the table format's.

## Interfaces & integration
- **SQL:** ANSI-style SQL (Apache Calcite-based planner/dialect); DML (INSERT/UPDATE/DELETE/MERGE) and DDL on Iceberg tables; views = "virtual datasets" that form the semantic layer.
- **Clients:** JDBC, ODBC, **Arrow Flight (ADBC)** for fast columnar transfer, and REST API. Native BI integration (Tableau, Power BI, Looker, etc.) plus a web UI for the semantic layer.
- **Interop:** Iceberg tables written by Dremio are readable by [trino](trino.md), [Spark](apache-spark-sql.md), [snowflake](snowflake.md), [clickhouse](clickhouse.md), [duckdb](duckdb.md), etc., via Iceberg REST/Polaris/Nessie — the lake stays open. dbt adapter available.

## Operations & maturity
- **Deployment:** **Dremio Cloud** (fully managed, serverless engines) and **self-managed software** (Kubernetes/StatefulSets, also bare VMs). Editions: **Community** (free), **Enterprise**, **Cloud**.
- **Ops burden:** moderate — sizing executor engines, managing Reflection refresh/storage, metadata refresh on sources, and Nessie/Polaris catalog ops. Reflection sprawl and stale acceleration are the common day-2 pain; metadata refresh on large/federated sources can be heavy.
- **Maturity:** founded 2015, established commercial product with sizable enterprise deployments; Arrow/Nessie/Polaris lineage gives strong open-source credibility. Known failure modes: memory pressure / spill on large joins-aggregations, and planning complexity when many Reflections compete.
- **Governance:** company-controlled product; key adjacent pieces (Arrow, Nessie, Polaris) live in the ASF or independent OSS.

## Licensing & cost
- **Core:** `dremio-oss` is **Apache 2.0** ([license-taxonomy](../concepts/license-taxonomy.md) permissive), but some bundled connectors (Oracle/SQL Server/MySQL drivers) ship under non-OSS licenses; pure-OSS builds lose those features. Enterprise and Cloud are **proprietary/source-available-style commercial** with features (fine-grained access control, advanced security, support) gated behind them.
- **Open vs vendor-controlled:** the data and table format stay open (Iceberg on your storage) — low lock-in at the data layer; the acceleration/semantic-layer value and Enterprise features are vendor-controlled.
- **Cost model:** Cloud is consumption-based (compute on elastic engines + storage you own); self-managed is license/subscription + your infra. Reflections add storage and refresh-compute cost.

## Bottom line
- Reach for Dremio when you want **BI-grade interactive SQL directly on an open Iceberg lakehouse** without copying data into a warehouse, and the auto-substituting Reflections + semantic layer justify running it over plain [trino](trino.md). Good fit for "warehouse experience, lake economics, open formats." Not the right tool for OLTP, low-latency point lookups, or high-concurrency real-time serving (use [clickhouse](clickhouse.md)/[apache-druid](apache-druid.md)/[starrocks](starrocks.md)), nor for teams already standardized on [databricks](databricks.md)/[snowflake](snowflake.md) who don't want a second engine. **Biggest gotcha:** Reflections are the performance story and the operational tax — over- or under-building them, plus stale refreshes, is where Dremio deployments most often go sideways; without them, raw federated/lake query latency is closer to ordinary Trino.

## Sources
- [Dremio architecture docs](https://docs.dremio.com/current/what-is-dremio/architecture/)
- [How Dremio delivers fast queries: Arrow, Reflections, C3 (Dremio blog)](https://www.dremio.com/blog/how-dremio-delivers-fast-queries-on-object-storage-apache-arrow-reflections-and-the-columnar-cloud-cache/)
- [Dremio Editions docs](https://docs.dremio.com/editions/)
- [dremio-oss LICENSE (Apache 2.0)](https://github.com/dremio/dremio-oss/blob/master/LICENSE)
- [Is Dremio CE fully Apache 2.0? (community thread on bundled non-OSS drivers)](https://community.dremio.com/t/is-dremio-ce-fully-apache-2-0/3858)
- [What is Nessie? Catalog versioning / Git for data (Dremio blog)](https://www.dremio.com/blog/what-is-nessie-catalog-versioning-and-git-for-data/)
- [Apache Polaris 1.0 release (Dremio blog)](https://www.dremio.com/blog/apache-polaris-1-0-release/)
- [Open Catalog docs](https://docs.dremio.com/current/data-sources/open-catalog/)
