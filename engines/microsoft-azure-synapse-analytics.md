---
name: Microsoft Azure Synapse Analytics
slug: microsoft-azure-synapse-analytics
rank: 35
data_model: Relational (cloud data warehouse)
license: Proprietary, managed-only (Azure PaaS)
summary: Azure's MPP cloud data warehouse + lake/Spark workspace; in maintenance mode as Microsoft pushes new investment to Microsoft Fabric.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Azure Synapse Analytics

> Azure's columnar MPP data-warehouse engine (the former SQL DW) plus a serverless-SQL-over-data-lake and Spark workspace — now effectively frozen, with Microsoft steering all new work to [microsoft-fabric](microsoft-fabric.md).

## Identity
- **Taxonomy / data model:** Relational analytical warehouse, exposed via T-SQL. It is a *workspace* bundling three compute engines: **dedicated SQL pool** (provisioned MPP warehouse, formerly Azure SQL Data Warehouse), **serverless SQL pool** (query-on-demand over data-lake files), and **Apache Spark pools** ([apache-spark-sql](apache-spark-sql.md)). It is not a single database engine — the dimensions below mostly describe the dedicated SQL pool, the warehouse core.
- **Storage model:** Column-store. Dedicated pool tables default to **clustered columnstore indexes** (compressed column segments) on Azure Storage; row-store heap/clustered-index and replicated tables are also available. Serverless pool reads external **Parquet/CSV/Delta** files directly from ADLS Gen2 — no ingestion. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md); this is classic warehouse columnar storage ([columnar-storage](../concepts/columnar-storage.md)).
- **Workload:** OLAP / batch analytics. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not OLTP — high per-statement latency, no point-write efficiency, 60-distribution fan-out optimized for scans. HTAP is *not* a native property; the (deprecated) Synapse Link for SQL/Cosmos DB replicated operational data in for analytics rather than co-locating workloads. ([Synapse SQL architecture](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-architecture))

## Distribution & consistency
- **Architecture:** Shared-nothing MPP. A **Control node** runs the distributed query optimizer; **Compute nodes** (1–60, set by service level) own the **60 fixed distributions**; the **Data Movement Service (DMS)** shuffles rows between nodes for joins/aggregations that aren't co-located. ([Synapse SQL architecture](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-architecture)) See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Distribution methods:** hash (deterministic on a chosen column — best for big joins/aggregations), round-robin (even, simple, used for staging — joins force a reshuffle), replicated (full copy cached per compute node — for small dimensions). ([Synapse SQL architecture](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-architecture))
- **CAP under partition:** N/A in the classic sense — this is a single-region managed service over Azure Storage, not a multi-master distributed database. Durability/replication ride on Azure Storage; it is consistent (CP-like) but not designed to survive region partition while serving writes. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** dedicated SQL pool defaults to **READ UNCOMMITTED**, an unusual and surprising default for a SQL engine — dirty reads are possible unless you opt in. You can enable **READ COMMITTED SNAPSHOT** at the database level, after which all transactions run under snapshot isolation and session-level READ UNCOMMITTED is ignored. Serializable/repeatable-read are **not** supported. ([Transactions in dedicated SQL pool](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-transactions)) See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Storage-layer redundancy via Azure Storage (LRS/ZRS/GRS); no user-facing leader/follower replica topology like Postgres. Serverless pool has no persistent state of its own. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels.
- **Clock dependency:** None notable. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schema-on-write for dedicated pool tables; **schema-on-read** for serverless pool over lake files (Parquet/CSV/Delta inferred or declared via external tables / OPENROWSET).
- **Migration / DDL:** Standard T-SQL `ALTER`. Dedicated pool lacks some SQL Server DDL niceties; CTAS (`CREATE TABLE AS SELECT`) is the idiomatic way to rebuild/repartition tables. No online-DDL guarantees comparable to PostgreSQL.
- **Type system:** T-SQL types. Clustered columnstore does not support `VARCHAR(MAX)`/`NVARCHAR(MAX)`/`VARBINARY(MAX)` (LOB max-length) columns — since columnstore is the table default, a MAX column forces you onto a heap or clustered (row-store) index instead. ([Columnstore index and varchar(max) — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/965610/azure-synapse-columnstore-index-and-varchar(max))) Limited vs SQL Server: no native JSON column type parity, constraints (FK/unique) are not enforced in dedicated pool. Geospatial/vector support is weak compared to general-purpose engines.

## Query interface
- **Language:** T-SQL (a subset — not full SQL Server surface; missing features like cross-database queries, certain constraints, some functions). Serverless adds `OPENROWSET` over files.
- **Transactions:** ACID multi-statement transactions are supported but constrained — transaction size limits apply, and the default READ UNCOMMITTED isolation means you must explicitly enable snapshot for clean reads. ([Transactions](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-transactions))
- **Joins/aggregations:** Native, parallelized across 60 distributions; cross-distribution joins trigger DMS data movement (the main performance lever — co-locate via matching hash keys).
- **Indexes:** clustered columnstore (default), heap, clustered/nonclustered B-tree, no enforced unique/PK. No secondary indexes in the OLTP sense.
- **Stored procedures / UDFs:** T-SQL stored procedures supported; scalar UDF support is limited compared to SQL Server. Spark pools add Python/Scala/.NET/SQL.

## Scaling & topology
- **Scale model:** Vertical-ish via **DWU** (Data Warehouse Units) for dedicated pool — pick a service level (DW100c … DW30000c) that remaps the 60 distributions across 1–60 compute nodes. You can grow/shrink without moving data, and **pause** compute (pay storage only). ([Architecture](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-architecture))
- **Sharding:** Fixed at 60 distributions — you choose the distribution key per table, not the shard count. Bad key choice → skew or constant DMS shuffles.
- **Serverless:** auto-scales compute per query; no provisioning.
- **Storage/compute separation:** Yes — compute is decoupled from Azure Storage; this is the headline design property. See [storage-compute-separation](../concepts/storage-compute-separation.md).
- **Read replicas:** No conventional read-replica fan-out.

## Performance & durability
- **Write path:** Data lands in Azure Storage; columnstore writes go through a delta/rowgroup mechanism then compress into segments. Durability is Azure Storage's (replicated, fsync handled below the service). See [wal-and-durability](../concepts/wal-and-durability.md). Bulk load via PolyBase / `COPY INTO` is the high-throughput path.
- **Throughput/latency:** Built for high-throughput scans over TB–PB; **not** for low-latency point queries or high concurrency. Concurrency is gated by DWU-tied **concurrency slots** and resource classes — a real limit teams hit. p99 is dominated by DMS data-movement on poorly distributed schemas.
- **Compaction/GC:** Columnstore rowgroups can fragment (small/open rowgroups from trickle loads); periodic index rebuild / CTAS is needed to maintain scan performance. This is the classic warehouse maintenance burden, not a background-compaction-vs-p99 story like LSM engines.

## Operations & maturity
- **Backup/restore, PITR:** Dedicated pool has automatic restore points (snapshots) and geo-restore; PITR within retention windows. Serverless is stateless (nothing to back up).
- **Observability:** EXPLAIN-equivalent query plans, `sys.dm_pdw_*` DMVs, Azure Monitor metrics, query store-style insights. Distribution-level DMVs help diagnose skew/data movement.
- **Upgrade story:** Fully managed PaaS — Microsoft handles patching; no rolling-upgrade work for the customer.
- **Maturity:** Mature lineage (Azure SQL DW since ~2016, MPP roots in PDW/Analytics Platform System). **No public Jepsen report exists** for Synapse. The dominant maturity fact is strategic: **dedicated SQL pools are in maintenance mode — security updates only, no new feature development**, with investment redirected to [microsoft-fabric](microsoft-fabric.md). Microsoft has not announced a hard end-of-life date for the Synapse service as a whole, but the trajectory is unambiguous; some sub-features are already retired (Synapse Data Explorer (Preview) pool retired Oct 7, 2025, succeeded by Eventhouse in Fabric Real-Time Intelligence; Synapse Link for Cosmos DB closed to new projects in favor of Fabric mirroring). Microsoft's own docs now banner every Synapse SQL article steering new users to Fabric Data Warehouse. ([Fabric migration guidance](https://learn.microsoft.com/en-us/fabric/data-warehouse/migration-synapse-dedicated-sql-pool-warehouse); [Synapse Data Explorer retirement](https://learn.microsoft.com/en-us/azure/synapse-analytics/data-explorer/data-explorer-overview))

## Ecosystem & people
- **Canonical use cases:** Enterprise data warehousing in the Azure/Microsoft stack; Power BI dashboards over a star schema; lake querying via serverless SQL; batch ETL with Spark + Synapse Pipelines (a hosted Azure Data Factory). Strong fit when the org is already all-in on Azure + Power BI.
- **Anti-patterns:** OLTP / high-concurrency transactional apps; low-latency point lookups; anything needing serializable isolation or enforced constraints; **and — most importantly today — new greenfield projects**, which Microsoft itself steers to Fabric Data Warehouse or to non-Azure lakehouses ([databricks](databricks.md), [snowflake](snowflake.md)).
- **Connectors:** Deep Microsoft integration — Power BI, Azure Data Factory/Synapse Pipelines, Azure ML, PolyBase, `COPY INTO`, dbt (via SQL Server/Synapse adapter), JDBC/ODBC. CDC into Synapse historically via Synapse Link (now deprecated path).
- **Community / docs / learning curve:** Large Microsoft ecosystem and good docs, but the docs now actively banner-push Fabric. Learning curve: moderate for T-SQL users; the distribution-key/data-movement mental model is the real skill.

## Licensing & cost
- **License:** Proprietary, **managed-only** Azure PaaS — no self-hosted option. See [license-taxonomy](../concepts/license-taxonomy.md). Lock-in is significant (T-SQL dialect quirks, distribution model, Azure-native tooling).
- **Cost model:** Dedicated pool billed per **DWU-hour** (~$1.2–1.4/hr at DW100c, ~$1k/mo always-on; scales linearly up the DWU ladder — DW1000c ≈ $11k/mo) plus Azure Storage; **pausing compute** is the main savings lever. Serverless SQL billed **per TB scanned** (~$5/TB, 10 MB minimum per query, rounded up). Spark pools billed per vCore-hour. (pricing approximate, list/USD; verify on [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/synapse-analytics/)) ⚠️ unverified — exact current per-DWU and per-TB rates vary by region and change over time.
- **At scale:** Always-on dedicated pools get expensive fast; serverless can surprise with cost on poorly-pruned (non-Parquet, no partition pruning) lake scans.

## Hardware / deployment
- **Resource profile:** Cloud-managed; you size DWUs, not RAM/CPU directly. Working set need not fit in RAM (it is a scan-heavy disk/columnar engine), but concurrency and cache (Adaptive/Result-set cache) materially affect latency.
- **Storage assumptions:** Azure Storage / ADLS Gen2 (network-attached object storage) — designed for that latency profile, not local NVMe.
- **Footprint:** Cloud-only managed service (clustered MPP under the hood); no embedded or on-prem deployment.
- **Deployment:** Azure SaaS/PaaS only; no Kubernetes/StatefulSet self-management.

## Bottom line
Reach for Synapse dedicated SQL pool only if you already run it in production on Azure and need to keep it operating; it is a competent, mature columnar MPP warehouse with strong Power BI integration. Do **not** start new projects on it — Microsoft has frozen feature work and is funneling everyone to [microsoft-fabric](microsoft-fabric.md) (and competitively, [databricks](databricks.md)/[snowflake](snowflake.md)). The single biggest gotcha is the **READ UNCOMMITTED default isolation** (dirty reads unless you enable snapshot) — closely followed by the **distribution-key choice**, which silently determines whether queries fly or drown in DMS data movement.

## Sources
- [Synapse SQL architecture — Microsoft Learn](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-architecture)
- [Use transactions with dedicated SQL pool — Microsoft Learn](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-transactions)
- [Dedicated SQL pool (formerly SQL DW) MPP architecture — Microsoft Learn](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/massively-parallel-processing-mpp-architecture)
- [Migrating Synapse dedicated SQL pools to Microsoft Fabric — Microsoft Learn](https://learn.microsoft.com/en-us/fabric/data-warehouse/migration-synapse-dedicated-sql-pool-warehouse)
- [Plan and manage costs for Azure Synapse Analytics — Microsoft Learn](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/synapse-analytics/plan-manage-costs.md)
- [Azure Synapse Analytics pricing](https://azure.microsoft.com/en-us/pricing/details/synapse-analytics/)
