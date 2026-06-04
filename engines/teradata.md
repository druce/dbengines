---
name: Teradata
slug: teradata
rank: 23
data_model: Relational (MPP data warehouse)
license: Proprietary / commercial (closed-source; cloud-consumption and on-prem appliance)
summary: The original shared-nothing MPP data warehouse — lock-based serializable SQL at petabyte scale, now repackaged for cloud consumption.
last_researched: 2026-06-04
confidence: high
---

# Teradata

> The veteran shared-nothing MPP relational warehouse: hash-distributed across AMPs, lock-based (no MVCC) serializable SQL, built for big batch analytics and now retrofitted with storage/compute separation in VantageCloud Lake.

## When to use

**Use Teradata if:**
- ✅ You already run it at enterprise scale and need rock-solid SERIALIZABLE concurrency on a big integrated warehouse
- ✅ You need mature workload management (TASM/TIWM priority, throttles) for high-concurrency mixed BI/reporting workloads
- ✅ You have the specialized DBAs to tune physical design (Primary Index, stats, partitioning) and value its deep ops/observability tooling (DBQL, Viewpoint)
- ✅ You need petabyte-scale batch analytics with a sophisticated cost-based optimizer

**Avoid Teradata if:**
- ❌ You want it for OLTP or high-rate single-row writes — it's lock-based (no MVCC), optimized for set operations
- ❌ You're greenfield and want cheap/elastic cloud analytics ([snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [databricks](databricks.md) win on cost and zero-tuning elasticity) or open source
- ❌ You can't manage Primary Index design — a poorly chosen PI silently causes AMP skew that destroys parallelism (the single biggest gotcha)
- ❌ Your workload is small/cheap — cost and operational weight are high

## Identity
- **Taxonomy / data model:** relational (SQL) analytical [OLAP](../concepts/oltp-olap-htap.md) warehouse. The current product line is "Vantage" — VantageCore (on-prem/appliance and IntelliFlex/VMware), VantageCloud Enterprise (lift-and-shift to AWS/Azure/GCP), and VantageCloud Lake (cloud-native). Bundles in-database analytics/ML functions and limited time-series/geospatial types beyond core relational.
- **Storage model:** row-oriented by default, hash-distributed across AMPs; supports a **columnar** table format and multi-level **Partitioned Primary Index (PPI)** for partition elimination ([dwhpro PPI](https://www.dwhpro.com/teradata-partitioned-primary-index-ppi/)). Block-based on-disk format; not [LSM/B-tree](../concepts/lsm-vs-btree.md) — it is a custom MPP block store with hash buckets, not a single-node index engine.
- **Workload:** OLAP / batch + ad-hoc analytics. Strong at large scans, joins, and concurrent mixed workloads with mature workload management; **not an OLTP engine** (lock-based, no row-versioning, optimized for set operations, not high-rate single-row writes).

## Distribution & consistency
- **CAP under partition:** CP-leaning. A single Teradata system is a tightly-coupled cluster over the BYNET interconnect ([Teradata architecture](https://developers.teradata.com/quickstarts/introduction/teradata-vantage-engine-architecture-and-concepts/)); it is not designed to keep serving a partitioned cluster as an AP store. CAP framing is a weak fit — see [cap-pacelc](../concepts/cap-pacelc.md); this is a warehouse, not a geo-distributed multi-leader DB.
- **PACELC:** ⚠️ unverified — Teradata does not publish a PACELC characterization. Practically, within one cluster it favors consistency (locking) over latency; cross-cluster data sharing in Lake is eventual at the catalog level.
- **Default isolation & what's achievable:** **SERIALIZABLE by default**, achieved with **two-phase locking, not [MVCC](../concepts/mvcc.md)** — readers and writers block each other ([Teradata: Database Locks, 2PL, and Serializability](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Request-and-Transaction-Processing/Transaction-Processing/Database-Locks-Two-Phase-Locking-and-Serializability)). Vantage supports only **SERIALIZABLE and READ UNCOMMITTED** as session isolation levels — it does **not** implement READ COMMITTED or REPEATABLE READ ([same docs](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Request-and-Transaction-Processing/Transaction-Processing/Database-Locks-Two-Phase-Locking-and-Serializability)). `SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` (equivalently `LOCKING FOR ACCESS`, "dirty read") trades consistency for concurrency on reports ([SET SESSION isolation docs](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Data-Definition-Language-Syntax-and-Examples/Session-Statements/SET-SESSION-TRANSACTION-ISOLATION-LEVEL)). **Load Isolation** (since 15.10) keeps committed row versions so readers see consistent committed data while a load runs — a limited, opt-in form of versioning, not general MVCC ([dwhpro Load Isolation](https://www.dwhpro.com/teradata-load-isolation/)). See [isolation-levels](../concepts/isolation-levels.md). Note: "ACID" here genuinely means serializable, which is stronger than the snapshot isolation many "ACID" systems ship.
- **Replication:** **FALLBACK** stores a second copy of each row on a different AMP in the cluster for fault tolerance ([dwhpro PI](https://www.dwhpro.com/teradata-primary-index-pi/)). Cross-system replication/DR is via Data Mover / Unity (async). Single tightly-coupled cluster model rather than [single-/multi-leader quorum](../concepts/replication-models.md); no split-brain failover semantics in the Dynamo sense.
- **Tunable consistency?** Per-statement lock level (ACCESS vs READ vs WRITE/EXCLUSIVE) and session isolation level — a coarse consistency knob, not Cassandra-style per-query quorum.
- **Clock dependency:** No dependency on synchronized clocks for correctness (lock-based, single-cluster). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema. (Lake/NOS can query external object-store files schema-on-read via foreign tables.)
- **Migration/evolution:** standard `ALTER TABLE` DDL; ⚠️ unverified — heavy schema changes on large tables can require locks/rewrites; no broadly-advertised lock-free online DDL.
- **Type system:** full SQL types plus DATE/TIME/INTERVAL, PERIOD (temporal), JSON, XML, geospatial (ST_Geometry), and array/dataset types; in-database ML/analytics functions. Native **vector embeddings** are now supported via the Enterprise Vector Store (GA'd March 2025, later extended to a multi-modal "Agentic" version) — vector ingest, embedding generation, indexing and similarity search inside Vantage ([Teradata Enterprise Vector Store](https://www.teradata.com/platform/clearscape-analytics/enterprise-vector-store)).

## Query interface
- **Language:** ANSI SQL with a rich Teradata dialect (BTEQ utility, extensive analytic/OLAP window functions, QUALIFY clause, recursive queries). Highly standards-aware and mature optimizer.
- **Transactions:** full multi-statement **ACID**; supports both ANSI mode and Teradata (BTET — BEGIN/END TRANSACTION) mode.
- **Native vs app-side:** joins, aggregations, window functions, secondary indexes (USI/NUSI), join indexes, hash indexes — all native and cost-based-optimized. Strong query optimizer is a historical differentiator.
- **Stored procedures / UDFs:** SQL stored procedures; UDFs/UDTs/table functions in C/C++ and Java; in-database scripting via SCRIPT/ExecR and bundled analytic function libraries (Vantage Analytics).

## Scaling & topology
- **Vertical vs horizontal:** horizontal MPP — scale by adding nodes/AMPs. Classic appliance scaling means adding nodes and **redistributing data** (resharding pain on-prem).
- **Sharding/partitioning:** automatic hash distribution by **Primary Index** across AMPs ([architecture docs](https://developers.teradata.com/quickstarts/introduction/teradata-vantage-engine-architecture-and-concepts/)). **PI choice is load-bearing**: a low-cardinality PI causes AMP **skew** that wrecks parallelism — the single biggest design gotcha ([dwhpro skew](https://www.dwhpro.com/teradata-primary-index-pi/)). NoPI tables and PPI (partition elimination) available.
- **Read replicas:** no read-replica concept like OLTP DBs; FALLBACK copies are for fault tolerance, not read scale-out.
- **Storage/compute separation:** **only in VantageCloud Lake**, which decouples elastic compute clusters from S3-class object storage, allowing independent compute scaling and workload-isolated clusters over shared data ([VantageCloud Lake press](https://www.teradata.com/press-releases/2022/teradata-announces-vantagecloud-lake)). Classic Teradata and VantageCloud Enterprise remain tightly-coupled shared-nothing (compute+storage together). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** ACID-durable; FALLBACK provides in-cluster redundancy; Transient Journal supports transaction rollback. ⚠️ unverified — exact fsync/group-commit/data-loss-window semantics are not publicly documented in detail. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** built for high-throughput parallel scans and large joins with predictable concurrency under sophisticated workload management (TASM/TIWM priority, throttles). Latency is batch/analytic, not single-row OLTP; p99 is dominated by skew and the slowest AMP — one skewed AMP stalls the whole step.
- **Compaction/GC:** no LSM-style compaction. Space is managed via spool, transient journal cleanup, and periodic stats collection; **COLLECT STATISTICS** quality is critical to optimizer plans and tail latency.

## Operations & maturity
- **Backup/restore, PITR:** mature tooling — DSA (Data Stream Architecture)/ARC for backup/restore; Data Mover for table movement; Unity for routing/DR. PITR ⚠️ unverified as a turnkey feature vs snapshot+journal.
- **Observability:** extensive DBQL (Database Query Logging), Viewpoint monitoring portal, EXPLAIN plans, and detailed step-level diagnostics — among the most mature ops/observability stacks in the warehouse space.
- **Upgrade story:** managed/rolling for cloud; on-prem appliance upgrades are a planned, heavyweight DBA exercise. Day-2 burden is non-trivial (PI design, stats, workload management tuning) and demands specialized DBAs.
- **Maturity:** ~40+ years in production at the largest enterprises (banks, telco, retail); extremely battle-tested for big-warehouse correctness and concurrency. **No Jepsen report exists** (⚠️ — not a target for Jepsen-style partition testing, being a single-cluster proprietary warehouse).

## Ecosystem & people
- **Canonical use cases:** large enterprise data warehouse / integrated data warehouse, complex mixed-workload analytics, regulatory/financial reporting, high-concurrency BI. **Anti-patterns:** OLTP / high-rate single-row writes; small/cheap workloads (cost and ops weight); greenfield teams wanting open-source or pay-as-you-go-cheap — [snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [amazon-redshift](amazon-redshift.md), [databricks](databricks.md), [clickhouse](clickhouse.md) are the modern competitors.
- **Drivers/connectors:** JDBC/ODBC/.NET, Python (teradatasql, teradataml), R; dbt adapter; Teradata Parallel Transporter (TPT) for bulk load; QueryGrid for cross-system federation; integrates with major BI tools (Tableau, Power BI). NOS reads external S3/object data.
- **Community & support:** commercial enterprise support; smaller, older, more specialized talent pool than the cloud-native DWs; deep but proprietary docs (docs.teradata.com); steep learning curve centered on physical design (PI, stats, workload management).

## Licensing & cost
- **License:** **proprietary / closed-source** commercial software — there is no OSS edition. See [license-taxonomy](../concepts/license-taxonomy.md). (Express/developer sandbox editions have existed historically.)
- **Self-managed vs managed:** on-prem appliance / IntelliFlex / VMware (VantageCore), customer-cloud lift-and-shift (VantageCloud Enterprise), and fully cloud-native (VantageCloud Lake). Significant lock-in via PI physical design, proprietary utilities (TPT/BTEQ), and SQL dialect extensions.
- **Cost model:** moving from per-node/per-core appliance capex to **consumption-based units** in the cloud; VantageCloud Enterprise plans start around $9,000–$10,500/month with multi-year commitments ([Teradata pricing](https://www.teradata.com/getting-started/pricing)). Historically one of the most expensive warehouses per TB; cost has been the main reason customers migrate off.

## Hardware / deployment
- **Resource profile:** CPU- and I/O-bound parallel scan engine; memory matters but the design predates "all in RAM" — working set need not fit in RAM. Performance scales with AMPs × spindles/NVMe and interconnect.
- **Storage assumptions:** classic appliances use locally-attached disk/NVMe per node (shared-nothing); Lake uses network-attached object storage (S3-class) with local cache.
- **Footprint:** clustered MPP only — no embedded/single-node-library mode. Sizes from a node to large multi-rack systems.
- **Deployment:** on-prem appliance, customer VPC on AWS/Azure/GCP, or Teradata-managed cloud (SaaS-like). Cloud-native Lake is the strategic direction; classic on-prem remains in large installed base. Not a lightweight containerized/k8s-native product.

## Bottom line
Reach for Teradata when you already run it at enterprise scale, need rock-solid **serializable** concurrency on a big integrated warehouse with mature workload management and ops tooling, and have the DBAs to tune it. Do not pick it greenfield for OLTP, for cheap/elastic cloud analytics (Snowflake/BigQuery/Databricks win on cost and zero-tuning elasticity), or if you want open source. The single biggest gotcha is **Primary Index / skew**: a poorly chosen PI silently destroys parallelism, and the lock-based (non-MVCC) concurrency model means heavy readers and writers contend unless you deliberately use ACCESS locks or Load Isolation.

## Sources
- [Teradata Vantage Engine Architecture and Concepts (official)](https://developers.teradata.com/quickstarts/introduction/teradata-vantage-engine-architecture-and-concepts/)
- [Understanding ACID Compliance (Teradata)](https://www.teradata.com/insights/data-platform/understanding-acid-compliance)
- [SET SESSION TRANSACTION ISOLATION LEVEL (Teradata docs)](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Data-Definition-Language-Syntax-and-Examples/Session-Statements/SET-SESSION-TRANSACTION-ISOLATION-LEVEL)
- [Database Locks, Two-Phase Locking, and Serializability (Teradata docs)](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/SQL-Request-and-Transaction-Processing/Transaction-Processing/Database-Locks-Two-Phase-Locking-and-Serializability)
- [Teradata Enterprise Vector Store (official)](https://www.teradata.com/platform/clearscape-analytics/enterprise-vector-store)
- [Teradata Load Isolation (dwhpro)](https://www.dwhpro.com/teradata-load-isolation/)
- [Primary Index, distribution, skew (dwhpro)](https://www.dwhpro.com/teradata-primary-index-pi/)
- [Partitioned Primary Index (dwhpro)](https://www.dwhpro.com/teradata-partitioned-primary-index-ppi/)
- [Teradata Announces VantageCloud Lake (press release)](https://www.teradata.com/press-releases/2022/teradata-announces-vantagecloud-lake)
- [VantageCloud pricing (Teradata)](https://www.teradata.com/getting-started/pricing)
