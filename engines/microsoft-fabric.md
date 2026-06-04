---
name: Microsoft Fabric
slug: microsoft-fabric
rank: 33
data_model: Relational (SaaS analytics platform; multi-engine over a Delta-Parquet lake)
license: Proprietary (SaaS, managed-only)
summary: SaaS analytics suite stitching a SQL warehouse, Spark lakehouse, KQL real-time store and Power BI over one Delta-Parquet lake (OneLake), billed by shared capacity units.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Fabric

> Microsoft's all-in-one SaaS analytics platform: multiple compute engines (T-SQL Warehouse, Spark Lakehouse, KQL Real-Time, Power BI) sharing one Delta-Parquet lake (OneLake), billed against a single pool of "capacity units" — not a database engine so much as a bundled analytics estate.

## When to use

**Use Microsoft Fabric if:**
- ✅ You are a Microsoft/Power BI shop wanting one governed SaaS analytics estate — lake, T-SQL warehouse, Spark, real-time, and BI sharing one Delta store
- ✅ You want "one copy of data, many engines" — warehouse, Spark, and BI read the same OneLake Delta files with no copy
- ✅ You want Power BI-centric BI at scale via Direct Lake (Import-mode speed without an Import refresh)
- ✅ You prefer a SaaS platform with no infrastructure to manage and open Delta/Parquet storage you can read externally

**Avoid Microsoft Fabric if:**
- ❌ You need OLTP / transactional apps — the Warehouse is not for high-concurrency row writes (use [microsoft-sql-server](microsoft-sql-server.md) or [postgresql](postgresql.md))
- ❌ You have cost- or latency-sensitive small/spiky workloads where a shared capacity gets throttled
- ❌ You want node-level control or a non-Microsoft BI stack (heavy Azure/Entra/Power BI lock-in)
- ❌ You can't handle the biggest gotcha: the Warehouse enforces **snapshot isolation with table-level write-conflict detection** — concurrent UPDATE/DELETE/MERGE on the same table abort and must be retried in app code

## Identity
- **Taxonomy / data model:** Not a single engine. It is a SaaS platform that packages several engines over a common store. Primary face is the **Warehouse** (T-SQL, relational, OLAP) and **Lakehouse** (Spark + SQL endpoint). Also includes a KQL real-time store (Eventhouse / [microsoft-azure-data-explorer](microsoft-azure-data-explorer.md) lineage), an [microsoft-sql-server](microsoft-sql-server.md)-derived OLTP "SQL database in Fabric," and Power BI semantic models. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) — the platform is overwhelmingly **OLAP/analytics**; OLTP is a bolted-on mirror, not the core.
- **Storage model:** Everything lands in **OneLake** as **Delta Lake tables (Parquet files + a `_delta_log` transaction log)** ([Lakehouse and Delta tables](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-and-delta-tables)). Columnar Parquet; Microsoft adds "V-Order" write-time optimization for VertiPaq read speed. OneLake is built on Azure Data Lake Storage (ADLS) Gen2 ([Fabric overview](https://learn.microsoft.com/en-us/fabric/fundamentals/microsoft-fabric-overview)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — it is immutable-file log-structured columnar storage.
- **Workload:** OLAP / analytics first. The marketing "one copy of data, many engines" is the genuinely novel bit: warehouse and Spark and BI read the *same* Delta files with no copy. HTAP-style "real-time" claims rest on **Mirroring** — CDC replication of operational DBs (Azure SQL, Cosmos DB, Snowflake, Databricks) into OneLake Delta — which is async replication into a separate analytics copy, **not** a single HTAP engine. ⚠️ unverified — exact mirror replication lag is workload-dependent and not a fixed SLA.

## Distribution & consistency
- **CAP under partition:** The Warehouse engine is **Polaris** ([Extending Polaris to Support Transactions, SIGMOD 2024](https://dl.acm.org/doi/10.1145/3626246.3653392)), a CP-style distributed query/transaction engine over cloud storage; it favors consistency and will fail/retry rather than serve stale or divergent state. See [cap-pacelc](../concepts/cap-pacelc.md). This is a managed cloud service, so classic CAP framing is partly moot — the durability and consistency boundary is ADLS, not a quorum of your nodes.
- **PACELC:** ⚠️ unverified — no published PACELC characterization. In practice (else-case) it trades latency for consistency: transactions read a consistent snapshot from immutable files, and commit conflicts are resolved at commit time (see below).
- **Default isolation & what's achievable:** Warehouse **enforces snapshot isolation on all transactions; any client `SET TRANSACTION ISOLATION LEVEL` is ignored** ([Transactions in Fabric Data Warehouse](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions)). So "ACID-compliant" here means **snapshot isolation, not serializable** — readers never block writers and vice versa, but write-write conflicts on a table abort the later committer (errors 24556 / 24706, retry required). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). Conflicts are evaluated at **table granularity** (table-level locking), so two transactions touching different rows of the same table can still collide. The KQL/Eventhouse and Spark engines have their own (weaker, file-version-based) semantics.
- **Replication:** Storage durability/replication is handled by ADLS Gen2 underneath (Microsoft-managed). Cross-engine "replication" is really the same Delta files being read by multiple engines, plus async **Mirroring** CDC for external sources. No user-facing leader/follower or quorum config. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency knobs (and isolation level is locked to snapshot for the Warehouse).
- **Clock dependency:** ⚠️ unverified — no documented correctness dependence on synchronized clocks; commit ordering is managed by centralized transaction-log services, not TrueTime-style clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Warehouse is **schema-on-write** (relational tables, T-SQL DDL). Lakehouse supports both — schema-on-read over files plus managed Delta tables. The SQL analytics endpoint over a Lakehouse is **read-only** T-SQL.
- **Migration / online DDL:** DDL (`CREATE`/`ALTER`/`DROP`/`TRUNCATE`/CTAS) is transactional and can run inside `BEGIN TRAN`, but DDL takes a **schema-modification (`Sch-M`) lock that blocks all concurrent access to the table** for the duration ([transactions doc](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions)) — so `ALTER` is *not* freely online; schedule it in maintenance windows. `ALTER TABLE` supports add nullable column / drop column / NOT ENFORCED constraints.
- **Type system:** T-SQL types in the Warehouse but with a **reduced surface area** vs SQL Server (no full T-SQL; see surface-area limits). Native Delta/Parquet types in the Lakehouse. Constraints (PK/UNIQUE/FK) are supported only as **`NOT ENFORCED`**. JSON support is limited relative to full SQL Server. No native vector type in the Warehouse as of this writing.

## Query interface
- **Language:** Per engine — **T-SQL** (Warehouse and Lakehouse SQL endpoint), **Spark SQL / PySpark / Scala / R** (Lakehouse Data Engineering), **KQL** (Real-Time Intelligence / Eventhouse), **DAX/MDX** (Power BI semantic models), and **Power Query (M)** in Dataflows. There is no single unified query language.
- **Transactions:** Warehouse supports **multi-statement, multi-table ACID transactions** under snapshot isolation, including **cross-warehouse transactions within the same workspace** and reads from a Lakehouse SQL endpoint. **No** distributed transactions, savepoints, named or marked transactions ([transactions doc](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions)). Spark/Lakehouse writes get Delta's per-table atomicity, not cross-table multi-statement transactions.
- **Native vs app-side:** Native SQL joins, aggregations, window functions in the Warehouse (it is genuinely a SQL MPP engine). Secondary indexes in the classic B-tree sense are absent — it relies on columnar scan + statistics, not user indexes.
- **Stored procedures / UDFs:** T-SQL stored procedures supported; Fabric also adds Python "User Data Functions." Spark notebooks cover programmatic transforms.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal MPP. **Polaris separates compute from storage** and can spin compute pools that transactionally access the same logical database via centralized metadata/transaction-log services ([SIGMOD 2024 paper](https://dl.acm.org/doi/10.1145/3626246.3653392)). See [storage-compute-separation](../concepts/storage-compute-separation.md). You do **not** size nodes directly — you buy a **capacity SKU (F2…F2048)** and the platform allocates/auto-scales compute, with **bursting** above the SKU and **smoothing** of the bill over time ([smoothing & throttling](https://learn.microsoft.com/en-us/fabric/data-warehouse/compute-capacity-smoothing-throttling)).
- **Sharding:** Hidden from the user; data is distributed across Parquet files automatically. No manual shard-key management, no resharding pain — and also no control if a layout is bad (you tune via table maintenance / V-Order / OPTIMIZE).
- **Read replicas & read consistency:** Multiple compute pools read the same OneLake Delta files; a query sees a consistent snapshot of committed data. The Lakehouse **SQL analytics endpoint can lag** behind Spark writes due to metadata sync — a known consistency wrinkle. ⚠️ unverified — exact endpoint sync latency varies.
- **Storage/compute separation:** Yes, foundational. Storage is OneLake/ADLS; compute is ephemeral and capacity-billed. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Writes produce new immutable Parquet files plus a Delta `_delta_log` commit; durability rests on **ADLS Gen2** (Microsoft-managed, replicated). Because files are immutable and commits are atomic log appends, the crash data-loss window is effectively the committed-vs-uncommitted boundary — uncommitted transactions roll back. See [wal-and-durability](../concepts/wal-and-durability.md). INSERTs always create new files (fewer conflicts); UPDATE/DELETE/MERGE rewrite files and conflict at table level.
- **Throughput / latency:** Strong on large analytical scans (columnar MPP + VertiPaq for BI). **Direct Lake** lets Power BI page Delta columns straight into the VertiPaq engine, giving Import-mode speed without an Import refresh ([Direct Lake overview](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview)). Weak at high-concurrency small writes / point lookups — table-level locking and file-rewrite cost make it a poor OLTP store. ⚠️ unverified — no neutral published TPC-style benchmark; vendor benchmarks should be treated as marketing.
- **Compaction / vacuum / GC:** Background **data compaction** rewrites small/poor files; this can race user writes but "compaction preemption" is designed to avoid write-write conflicts ([transactions doc](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions)). Delta `OPTIMIZE`/`VACUUM` and table maintenance reclaim space and tune row groups; neglecting them degrades Direct Lake and scan p99.

## Operations & maturity
- **Backup/restore, PITR:** Warehouse has automatic **restore points** and restore-in-place; zero-copy **CLONE** (`CREATE TABLE AS CLONE OF`) for point-in-time table copies. Delta time-travel gives version history on Lakehouse tables. ⚠️ unverified — cross-engine, tenant-wide coordinated PITR is not a single guaranteed operation.
- **Observability:** T-SQL DMVs (`sys.dm_tran_locks`, query insights views), Power BI Capacity Metrics app for CU consumption/throttling, Spark monitoring, query plans/EXPLAIN in the SQL engines.
- **Upgrade story:** SaaS — Microsoft ships continuous updates; **no customer-managed upgrades**, but also little version control and frequent behavior changes (the docs themselves warn features are "evolving rapidly").
- **Maturity:** **Young.** Fabric GA'd in late 2023; the Warehouse/Polaris lineage traces to Azure Synapse, but the integrated SaaS product is new and changing fast. **No public [jepsen](../concepts/jepsen.md) report exists** for Fabric. Known sharp edges: table-level (not row-level) write conflicts forcing retry logic, DDL blocking, Lakehouse SQL-endpoint sync lag, and capacity **throttling** when a shared capacity is overloaded ([throttling](https://learn.microsoft.com/en-us/fabric/enterprise/throttling)).

## Ecosystem & people
- **Canonical use cases:** Microsoft-shop enterprises wanting one governed analytics estate — lake + warehouse + BI + real-time — without wiring separate Azure services; Power BI-centric BI at scale via Direct Lake; medallion-architecture lakehouses on Delta.
- **Anti-patterns:** OLTP / transactional apps (use [microsoft-sql-server](microsoft-sql-server.md), [postgresql](postgresql.md), or the embedded "SQL database in Fabric" instead — the Warehouse is not for high-concurrency row writes); cost-sensitive small/spiky workloads where a shared capacity gets throttled; teams wanting fine node-level control or a non-Microsoft BI stack; multi-cloud-neutral shops (heavy Azure/Entra/Power BI lock-in).
- **Drivers / connectors:** Standard SQL Server TDS drivers (ODBC/JDBC/.NET) to the SQL endpoints; Spark connectors; 200+ Data Factory connectors; Mirroring CDC from Azure SQL, Cosmos DB, Snowflake, Databricks, PostgreSQL; **dbt** has a Fabric adapter; deep Microsoft 365 / Excel / Teams / Purview integration.
- **Community / support:** Backed by Microsoft with enterprise support and large Power BI community; docs are extensive but churn quickly. Learning curve: easy to start (SaaS), hard to master (capacity sizing, cross-engine consistency, cost control).

## Licensing & cost
- **License:** **Proprietary, managed-only SaaS.** No self-hosting, no open-source core. The underlying *storage format* (Delta Lake / Parquet) is open, which mitigates some lock-in (you can read OneLake Delta files from outside), but the engines and platform are closed. See [license-taxonomy](../concepts/license-taxonomy.md). (Note: legacy Power BI Premium **P SKUs** are being retired in favor of Fabric **F SKUs**.)
- **Self-managed vs managed-only:** Managed-only.
- **Lock-in:** High at the platform layer (Entra identity, Power BI semantic models, capacity model, Purview governance); **moderated** by open Delta storage you can shortcut/export.
- **Cost model:** **Capacity Units (CUs)** via F-SKUs (F2 ≈ 2 CUs … up to F2048), pay-as-you-go ≈ $0.18/CU-hour, billed per-second with a one-minute minimum; **pausable** to stop charges when idle ([Fabric pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)). All engines draw from the **same shared capacity**, so a heavy Spark job can starve interactive BI — and overload triggers **throttling**, not just a bigger bill. Cheap-at-small (pause an F2) but cost and contention can invert fast at scale; **F64+** is the threshold for several features (e.g. free Power BI report consumption, larger Direct Lake guardrails).

## Hardware / deployment
- **Resource profile:** Abstracted away — you buy CUs, not RAM/CPU. Direct Lake performance is **memory-bound** at the semantic-model layer: each SKU caps max model memory (e.g. F2 ≈ 3 GB, F64 ≈ 25 GB, F512 ≈ 200 GB), and exceeding it causes paging and slow queries ([Direct Lake overview](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview)).
- **Storage assumptions:** Cloud object storage (ADLS Gen2) only; no on-prem storage, no local-NVMe option. Network-attached latency is inherent.
- **Footprint:** Cloud SaaS only — **no single-node, no embedded, no on-prem** deployment. OneLake **Shortcuts** give zero-copy access to external ADLS / S3 / GCS without ETL.
- **Deployment:** Microsoft-hosted SaaS; no containers/k8s/StatefulSets to run. You manage workspaces and capacities, not infrastructure. Region pinning matters (semantic model must be co-region with its source).

## Bottom line
Reach for Fabric if you are a Microsoft/Power BI shop that wants a single governed, SaaS analytics estate — lake, T-SQL warehouse, Spark, real-time, and BI sharing one open Delta store — without operating separate Azure services. Avoid it for OLTP, for cost- or latency-sensitive small workloads (shared-capacity throttling bites), and where you need node-level control or a non-Microsoft stack. The single biggest gotcha: the Warehouse enforces **snapshot isolation with table-level write-conflict detection** — concurrent UPDATE/DELETE/MERGE on the same table abort and *must* be retried in app code — and all engines compete for one shared, throttleable capacity, so capacity sizing is the real operational discipline.

## Sources
- [What is Microsoft Fabric (overview)](https://learn.microsoft.com/en-us/fabric/fundamentals/microsoft-fabric-overview)
- [Transactions in Fabric Data Warehouse](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions)
- [Direct Lake overview](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview)
- [Lakehouse and Delta Lake tables](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-and-delta-tables)
- [OneLake overview](https://learn.microsoft.com/en-us/fabric/onelake/onelake-overview)
- [Compute capacity smoothing and throttling](https://learn.microsoft.com/en-us/fabric/data-warehouse/compute-capacity-smoothing-throttling)
- [Understand Fabric capacity throttling](https://learn.microsoft.com/en-us/fabric/enterprise/throttling)
- [Microsoft Fabric pricing (Azure)](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/)
- [Extending Polaris to Support Transactions (SIGMOD 2024)](https://dl.acm.org/doi/10.1145/3626246.3653392) / [arXiv 2401.11162](https://arxiv.org/abs/2401.11162)
