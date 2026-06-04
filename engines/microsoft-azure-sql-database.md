---
name: Microsoft Azure SQL Database
slug: microsoft-azure-sql-database
rank: 14
data_model: Relational (multi-model: JSON, graph, spatial, vector, XML)
license: Proprietary, managed-only (PaaS); built on the SQL Server engine
summary: Fully-managed PaaS SQL Server engine with decoupled compute/storage (Hyperscale) and RCSI-by-default; the safe managed relational choice on Azure, but you never touch the box.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Azure SQL Database

> Microsoft's fully-managed cloud relational PaaS built on the SQL Server engine — RCSI on by default, Accelerated Database Recovery always on, and a Hyperscale tier that decouples compute from storage up to 128 TB — at the cost of no OS/instance access and Azure lock-in.

## When to use

**Use Microsoft Azure SQL Database if:**
- ✅ You want a fully-managed SQL Server-grade relational engine on Azure with HA, PITR, and zero patching effort
- ✅ Your workload is OLTP / line-of-business, especially .NET/Microsoft-stack apps and multi-tenant SaaS (elastic pools)
- ✅ You need very large databases with fast scale and near-instant restores (Hyperscale decouples compute/storage up to 128 TB)
- ✅ You value RCSI-by-default (READ COMMITTED snapshot) and Accelerated Database Recovery always on

**Avoid Microsoft Azure SQL Database if:**
- ❌ You need OS/instance access, SQLCLR, cross-database/linked-server features, or SQL Agent (use Managed Instance or SQL Server on a VM)
- ❌ You need transparent horizontal sharding or active-active multi-region writes
- ❌ You run large-scale MPP analytics/data-warehouse scans (use Fabric / Synapse / a columnar warehouse)
- ❌ You want to avoid the biggest gotcha: it is **managed-only and Azure-locked**, with per-replica/per-vCore billing that quietly inverts from cheap to expensive at scale

## Identity
- **Taxonomy / data model:** Relational (T-SQL / SQL Server engine), increasingly multi-model — native JSON, XML, spatial (geometry/geography), graph (node/edge tables), key-value, and a native `vector` type ([GA June 19, 2025](https://learn.microsoft.com/en-us/azure/azure-sql/database/ai-artificial-intelligence-intelligent-applications)). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Row-store B-tree by default; columnstore indexes (clustered/nonclustered) for analytics; In-Memory OLTP (Hekaton) memory-optimized tables on a subset of tiers. On-disk format is SQL Server page/extent (8 KB pages) plus the SQL Server transaction log. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** Primarily OLTP. **HTAP** is claimed for Hyperscale ([docs say "optimized for OLTP and HTAP"](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale?view=azuresql)). The *physical separation* mechanism: columnstore indexes (a columnar secondary representation) plus read-scale-out replicas to offload analytics off the primary — not a separate analytics engine. For real columnar/lakehouse analytics Microsoft now mirrors Azure SQL into [Microsoft Fabric](https://thenewstack.io/ignite-2024-microsoft-debuts-sql-server-2025-integrates-azure-sql-into-fabric/). Treat broad HTAP claims as "columnstore + read replicas," not MPP.

## Distribution & consistency
- **CAP under partition:** CP for the primary. A single logical database has one read-write primary; it does not stay writable across a partition that isolates it. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **Else** the tradeoff depends on tier. Business Critical (Always On AG with synchronous local/zone replicas) favors consistency on the local quorum; geo-replication is **asynchronous** (PA/EL — favors availability/latency over cross-region consistency). See [replication-models](../concepts/replication-models.md).
- **Default isolation & what's achievable:** **READ COMMITTED via RCSI (Read Committed Snapshot Isolation) is the default** — unlike on-prem SQL Server, which defaults to locking read-committed ([Microsoft docs](https://learn.microsoft.com/en-us/sql/relational-databases/performance/optimized-locking?view=sql-server-ver17)). SNAPSHOT and SERIALIZABLE are available; the engine implements true serializable via locking/range locks (not optimistic SSI like Postgres). RCSI uses MVCC row versioning. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). Row versions live in the **Persistent Version Store (PVS)** in the user database because **Accelerated Database Recovery (ADR) is always on** ([docs](https://learn.microsoft.com/en-us/sql/relational-databases/accelerated-database-recovery-troubleshoot?view=sql-server-ver17)), not in tempdb.
- **Replication:** Single-leader. HA built on Always On Availability Groups — Business Critical keeps 3–4 synchronous replicas (one readable); General Purpose uses remote Azure premium storage with a single compute replica (storage-level durability). Cross-region = **active geo-replication** (async, up to 4 geo-secondaries) and **auto-failover groups** (declarative wrapper with listener endpoints). Failover groups: **RPO 5 s, RTO 1 hour**; planned failover does a full sync first for zero data loss ([failover groups docs](https://learn.microsoft.com/en-us/azure/azure-sql/database/failover-group-sql-db?view=azuresql), [active geo-replication](https://learn.microsoft.com/en-us/azure/azure-sql/database/active-geo-replication-overview?view=azuresql)). Business Critical with active geo-replication: **RPO 5 s, RTO 30 s** ([docs](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore?view=azuresql)). Split-brain is avoided via Azure-managed failover orchestration (single writer at a time).
- **Tunable consistency?** No per-query consistency-level knobs (not a Dynamo-style system). You choose isolation levels and where you read (primary vs read replica). Reads from geo-secondaries are eventually consistent.
- **Clock dependency:** No correctness dependence on synchronized physical clocks (no TrueTime-style scheme). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid relational schema, enforced at write. JSON/XML columns allow schema-flexible blobs within a typed column (schema-on-read inside the document).
- **Migration/evolution:** Online DDL available for many operations (online index rebuild, `ADD COLUMN` with defaults is metadata-only in many cases), but some `ALTER` operations still take schema-modification locks and can block. No native automatic version migrations.
- **Type system:** Full SQL Server types — `datetime2`, `decimal`, `uniqueidentifier`, native JSON functions (and a `json` type in newer engine versions), XML, spatial `geometry`/`geography`, hierarchyid, sql_variant, and a native `vector` type with `VECTOR_DISTANCE` / approximate vector search ([native vector preview/GA](https://devblogs.microsoft.com/azure-sql/exciting-announcement-public-preview-of-native-vector-support-in-azure-sql-database/)).

## Query interface
- **Language:** T-SQL (SQL Server dialect). Not full ANSI but broad. Graph queries via `MATCH`, spatial methods, JSON via `OPENJSON`/`JSON_VALUE`/`FOR JSON`.
- **Transactions:** Full multi-statement ACID with savepoints. Cross-database transactions on the *same logical server* are limited; elastic transactions span databases via distributed coordination but with constraints.
- **Native vs app-side:** Native secondary indexes (incl. filtered, included-column, columnstore), joins, aggregations, window functions, CTEs, MERGE — full relational engine.
- **Stored procedures / UDFs:** T-SQL stored procs, functions, triggers; natively-compiled procs for In-Memory OLTP. **No SQLCLR (.NET in-engine) on Azure SQL Database** (a key gap vs on-prem SQL Server / Managed Instance).

## Scaling & topology
- **Vertical:** Primary scaling axis — change service tier / vCore count online. Serverless tier autoscales vCores and auto-pauses.
- **Horizontal:** No transparent built-in sharding of a single database. App-level sharding via **Elastic Database tools / shard map manager** (manual, app-aware; resharding is painful and app-driven). Elastic pools share compute across many databases for cost, not for sharding one DB.
- **Read replicas:** Business Critical exposes one readable secondary (`ApplicationIntent=ReadOnly`); Hyperscale supports up to 4 HA secondaries plus **up to 30 named replicas** with independent compute for read scale-out, plus geo-replicas. Reads from secondaries are slightly stale (async apply) — not guaranteed read-your-writes.
- **Storage/compute separation:** Yes, strongest in **Hyperscale** — a multi-tier architecture: stateless compute nodes, a **log service**, **page servers** holding data, and a local-SSD **RBPEX** (Resilient Buffer Pool Extension) cache on each compute node. Compute scales without data movement; storage grows to 128 TB. General Purpose also separates compute from remote premium storage. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Standard SQL Server WAL semantics; commit is durable when the log is hardened. In Hyperscale, the **log service** persists the log to durable storage and is the source of truth — page servers and replicas apply from the log. Group commit applies. **Data-loss window on crash: zero for committed transactions on a healthy primary** (durable log); the exposure is the async geo-replication RPO (~5 s) on regional failover. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Business Critical targets 1–2 ms local-SSD latency; Hyperscale gives high log throughput and fast commit independent of data size. Hyperscale max ~5,500 IOPS/vCore (effective IOPS workload-dependent due to multi-tier caching) ([Hyperscale tier docs](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale?view=azuresql)). p99 tail is sensitive to noisy-neighbor effects in shared/serverless tiers and to cold caches after a failover (mitigated by **continuous priming** of BP/RBPEX on Hyperscale HA replicas).
- **Compaction / vacuum / GC:** No LSM compaction. Version cleanup is the PVS cleaner (ADR); long-running transactions bloat PVS and hurt cleanup, a known p99/space risk. Ghost-record cleanup and index maintenance behave as in SQL Server.

## Operations & maturity
- **Backup/restore, PITR:** Automated backups always on; **PITR 1–35 days** (7 default), long-term retention up to 10 years. Choice of LRS/ZRS/GRS backup storage. **Geo-restore** requires geo-redundant (RA-GRS) storage. Hyperscale backups/restores are **file-snapshot based — near-instant regardless of size** ([docs](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale?view=azuresql)).
- **Observability:** Query Store, EXPLAIN/actual execution plans, DMVs, Intelligent Insights, Azure Monitor metrics, automatic tuning (auto plan correction, auto index create/drop). Strong query-plan tooling.
- **Upgrade story:** Engine version is **managed by Microsoft** — you do not control patching; updates roll out transparently with brief failovers (use a maintenance window to schedule them). Day-2 burden is low for patching/HA/backups; the burden shifts to cost governance and tier sizing.
- **Maturity:** Very mature — same battle-tested SQL Server engine, GA since 2010, huge production footprint. **No public Jepsen report exists** for Azure SQL Database. ⚠️ unverified — no independent formal-verification/Jepsen analysis of its distributed/geo-replication consistency is publicly available; consistency claims rest on Microsoft's documentation. Known gotchas: DBCC CHECKDB unsupported on Hyperscale (use CHECKTABLE/CHECKFILEGROUP); no SQLCLR; In-Memory OLTP only partially supported on Hyperscale.

## Ecosystem & people
- **Canonical use cases:** Cloud OLTP/line-of-business apps on Azure, .NET/Microsoft-stack apps, multi-tenant SaaS (elastic pools), apps wanting managed SQL Server without VM ops, large databases needing fast scale/restore (Hyperscale). **Anti-patterns:** heavy MPP analytics/data-warehouse scans at scale (use Fabric / Synapse / a columnar warehouse); workloads needing OS access, SQLCLR, cross-database/linked-server features, SQL Agent, or full instance control (use **Azure SQL Managed Instance** or SQL Server on a VM); multi-region active-active writes; cost-sensitive workloads at very large scale (per-vCore-per-replica billing adds up).
- **Drivers / connectors:** First-class — ODBC/JDBC/ADO.NET, EF Core and most ORMs, dbt (sqlserver adapter), Power BI and all major BI tools, CDC via SQL Server change tracking / change data capture, Debezium SQL Server connector, Azure Data Factory.
- **Community / support:** Enormous SQL Server community and docs; commercial support via Azure; gentle learning curve for anyone with SQL Server background. Excellent docs (Microsoft Learn).

## Licensing & cost
- **License:** Proprietary, **managed-only** — there is no self-hosted "Azure SQL Database." The engine is SQL Server but the service is PaaS-only. See [license-taxonomy](../concepts/license-taxonomy.md). Lock-in via Azure-specific features (Hyperscale, serverless, elastic pools, failover groups) and the inability to lift the instance out.
- **Self-managed vs managed:** Managed-only. (Self-managed paths are SQL Server on VM or, for closer parity, Azure SQL Managed Instance.)
- **Cost model:** Two purchasing models — **DTU** (bundled compute+storage, Basic/Standard/Premium) and **vCore** (separate CPU/memory/storage; provisioned or **serverless** per-second billing with auto-pause). Hyperscale bills **per vCore per replica** plus allocated storage plus backup storage; IOPS not billed ([vCore docs](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore?view=azuresql)). **Azure Hybrid Benefit** (reuse SQL Server licenses w/ Software Assurance) reduces compute cost — but **not in serverless**, and **not for new Hyperscale** databases as of Dec 2023. Cheap at small scale (serverless/Basic), inverts at large scale (Business Critical replicas, backup egress, per-replica Hyperscale). Watch hidden backup-storage costs.

## Hardware / deployment
- **Resource profile:** Memory- and I/O-bound like SQL Server; working set does not need to fully fit in RAM (RBPEX/page-server tiers in Hyperscale, remote storage in GP), though hot pages should. Business Critical is local-SSD latency-bound.
- **Storage assumptions:** Business Critical = local NVMe SSD; General Purpose = network-attached Azure premium storage (higher latency, tolerated by design); Hyperscale = decoupled page servers + local SSD cache.
- **Footprint:** Cloud PaaS only — single logical database, elastic pool, or Hyperscale cluster. Not embeddable, not on-prem. Serverless option for bursty/intermittent workloads.
- **Deployment:** Azure SaaS/PaaS exclusively; no containers/k8s self-hosting (Azure manages the fleet). Provisioned via portal, T-SQL, ARM/Bicep, PowerShell, CLI, Terraform.

## Bottom line
Reach for Azure SQL Database when you want a fully-managed SQL Server-grade relational engine on Azure with HA, PITR, and zero patching effort — especially for OLTP and Microsoft-stack apps, with Hyperscale handling very large databases and fast restores. Do not reach for it if you need OS/instance control, SQLCLR, cross-database/linked-server features, transparent sharding, active-active multi-region writes, or large-scale MPP analytics (use Managed Instance, SQL Server on VM, or Fabric/Synapse instead). The single biggest gotcha: it is **managed-only and Azure-locked** — combined with per-replica/per-vCore billing that quietly inverts from cheap to expensive at scale, and feature gaps (no SQLCLR, Hyperscale's missing DBCC CHECKDB) that differentiate it from "real" SQL Server.

## Sources
- [What is the Hyperscale service tier? — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale?view=azuresql)
- [vCore purchasing model — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore?view=azuresql)
- [Purchasing models (DTU vs vCore) — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/purchasing-models?view=azuresql)
- [Failover groups overview & best practices — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/failover-group-sql-db?view=azuresql)
- [Active geo-replication — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/active-geo-replication-overview?view=azuresql)
- [Optimized locking & RCSI default — Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/performance/optimized-locking?view=sql-server-ver17)
- [Accelerated Database Recovery (PVS) — Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/accelerated-database-recovery-troubleshoot?view=sql-server-ver17)
- [Native vector support in Azure SQL Database — Azure SQL Dev Corner](https://devblogs.microsoft.com/azure-sql/exciting-announcement-public-preview-of-native-vector-support-in-azure-sql-database/)
- [Ignite 2024: Azure SQL into Fabric — The New Stack](https://thenewstack.io/ignite-2024-microsoft-debuts-sql-server-2025-integrates-azure-sql-into-fabric/)
