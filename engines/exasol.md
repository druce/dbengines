---
name: EXASOL
slug: exasol
rank: 136
data_model: Relational (in-memory columnar MPP analytics)
license: Proprietary / source-available (free Community & Personal editions; commercial Enterprise/SaaS)
summary: In-memory, shared-nothing MPP columnar SQL warehouse tuned for very fast analytics with near-zero index/tuning effort — but proprietary and analytics-only.
last_researched: 2026-06-04
confidence: high
---

# EXASOL

> A proprietary in-memory, shared-nothing MPP columnar relational database built purely for fast analytics (OLAP), where the engine auto-creates indexes and self-tunes, so DBAs do almost no physical design — at the cost of being closed-source and a poor fit for OLTP.

## Identity
- **Taxonomy / data model:** Relational SQL database, marketed as an "analytics database / data warehouse." Single data model (relational); not multi-model.
- **Storage model:** Columnar storage with heavy compression (vendor claims ~2.5x typical; ratio is data-dependent). In-memory **processing** engine: hot data is held and processed in RAM, with column data persisted to disk and loaded into memory on demand. Note it is *not* a pure in-memory database — the working set does not have to fit entirely in RAM; more RAM improves performance but data is persisted on disk ([Exasol — In-Memory Database overview](https://docs.exasol.com/db/7.1/get_started/exasol_overview.htm)). On-disk format is a proprietary compressed columnar format. See [columnar-storage](../concepts/columnar-storage.md), [lsm-vs-btree](../concepts/lsm-vs-btree.md) (Exasol is neither classic LSM nor B-tree; it is a compressed columnar store with in-memory processing).
- **Workload:** OLAP / analytical query serving, BI, and dashboards. Not an OLTP or HTAP system — it does bulk-load + read-heavy analytics, not high-rate small transactional writes. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** ⚠️ unverified — Exasol does not publish a formal CAP/PACELC characterization. Architecturally it is a single-cluster, shared-nothing MPP system where data is synchronized across nodes; it favors consistency/correctness within the cluster and uses hot-standby/failover rather than partition-tolerant multi-region quorum, so it behaves CP-like (a partitioned/failed cluster fails over or stops rather than serving divergent replicas). Treat as ⚠️ unverified absent a vendor or Jepsen statement. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — not characterized by the vendor; as a single-cluster CP-style analytics system the latency-vs-consistency tradeoff is not a primary design axis.
- **Default isolation & what's achievable:** SERIALIZABLE is the (only) isolation level. Exasol's Transaction Management System (TMS) runs transactions "as if part of a sequence even though [they] run in parallel," with **object-level locking** (granularity is an entire schema or table, not a row), backed by a "MultiCopy" multi-versioning format that temporarily keeps multiple versions of objects to reduce collisions ([Exasol docs — Transaction Management](https://docs.exasol.com/db/latest/database_concepts/transaction_management.htm)). Because locks are at object granularity, two concurrent transactions cannot modify different rows of the same table at once — this is acceptable for a load-then-query warehouse but would be crippling for OLTP. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Intra-cluster data redundancy (e.g. redundancy level 2 replicates each node's data to a neighbor); on physical hardware a hot-standby reserve node takes over a failed node automatically ([Exasol docs — Fail Safety on-premise](https://docs.exasol.com/db/latest/planning/fail_safety/fail_safety_on_premise.htm)). This is cluster-internal redundancy, not cross-region async replication. A synchronous dual-data-center option exists for business continuity ([Exasol docs — Synchronous Dual Data Center](https://docs.exasol.com/db/7.1/planning/business_continuity/sddc_details.htm)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No. One isolation level (serializable); no per-query consistency knobs.
- **Clock dependency:** ⚠️ unverified — no documented dependency on synchronized clocks (TrueTime/HLC) for correctness; consistency is lock/version based within a single cluster. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** Rigid relational schema; tables, columns, and types declared up front. Not schemaless.
- **Migration / DDL:** Standard SQL DDL (`CREATE/ALTER/DROP`). ⚠️ unverified — Exasol does not prominently document "online DDL"; given object-level locking, `ALTER`/large changes can take a lock on the object. Verify against the SQL reference for a specific operation.
- **Type system:** Standard SQL scalar types (numeric, decimal, varchar, date/time, boolean, intervals, geospatial GEOMETRY). No native JSON document type or vector type as first-class storage — JSON is handled via functions/UDFs rather than a JSONB-style column. Not a document or vector store.

## Query interface
- **Language:** SQL, compliant with SQL Standard 2003 core, accessed via ODBC, JDBC, ADO.NET (and a native CLI/`websocket` API). Standard SQL dialect with analytic extensions.
- **Transactions:** Full multi-statement ACID transactions, serializable. Optimized for bulk load + analytic read, not high-frequency row writes.
- **Native vs app-side:** Native joins, aggregations, window functions, and analytic SQL — this is its core strength. Indexes are **engine-managed**: Exasol auto-creates join indexes as needed, reuses existing ones, and drops indexes unused for >5 weeks, so users generally do not create/manage indexes manually.
- **Stored procedures / UDFs:** UDF scripts in Lua (natively embedded, lowest overhead), Python, R, and Java; plus a Lua-based scripting language for control logic ([Exasol docs — UDF programming languages](https://docs.exasol.com/db/latest/database_concepts/udf_scripts/programming_languages_detail.htm)). Strong in-database analytics / ML-via-UDF story.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal scale-out via shared-nothing MPP — add nodes to a cluster, queries run in parallel across all nodes with no master node. Also scales vertically (more RAM = more in-memory working set).
- **Sharding / partitioning:** Data is distributed across nodes; users can set **distribution keys** to colocate joinable data and enable local joins and reduce inter-node traffic. Choosing the wrong distribution key causes data reshuffling and skew — the main physical-design lever the user still owns.
- **Read replicas / read consistency:** No conventional async read-replica model; reads come from the cluster and are consistent (serializable). The SaaS product separates compute from a shared S3-backed storage layer so multiple compute clusters can read the same data (see below).
- **Storage/compute separation:** Classic on-prem/cluster deployments are shared-nothing (storage local to nodes). **Exasol SaaS** uses Amazon S3 as the storage backend and lets one database back multiple compute clusters — a storage/compute-separated model. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** ACID with COMMIT durability ("all changes confirmed with COMMIT remain intact" — [Exasol docs](https://docs.exasol.com/db/latest/database_concepts/transaction_management.htm)). Data is persisted to disk (and redundantly to a neighbor node at redundancy 2); the in-memory layer is a cache/working set, not the system of record. ⚠️ unverified — Exasol does not prominently publish a per-commit fsync/group-commit policy or a precise crash data-loss window; the documented recovery mechanism is node failover plus persisted redundant volumes. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput / latency:** Designed for very fast analytic scans/joins from RAM; vendor markets large speedups vs disk-based warehouses (treat "10x–1000x" as marketing — real gains depend on working set fitting in RAM and query shape). Best p99 when the hot working set is memory-resident; spilling to disk degrades latency.
- **Compaction / GC:** Columnar compressed storage; the MultiCopy multi-versioning means old object versions are kept temporarily and reclaimed. ⚠️ unverified — no detailed public account of background compaction/GC cadence and its p99 impact.

## Operations & maturity
- **Backup/restore, PITR:** Backups to local/remote (e.g. archive) volumes are supported; ⚠️ unverified — confirm full point-in-time-recovery granularity in the current admin docs (backup/restore is documented; continuous PITR specifics should be verified per version).
- **Observability:** Management via **EXAoperation** (cluster admin UI) on on-prem deployments; system tables (`EXA_*` / statistics schema) expose monitoring and query/audit information; SQL `EXPLAIN`/profiling and auditing are available.
- **Upgrade story:** Cluster/managed upgrades; ⚠️ unverified — rolling vs downtime specifics vary by deployment (on-prem cluster vs SaaS) and should be confirmed per version. Day-2 burden is comparatively low: self-tuning indexes and minimal physical design are the headline operational selling point.
- **Maturity:** Mature commercial product (company founded ~2000, German origin), with a long record of strong TPC-H benchmark results and use in enterprise BI. Narrow but deep: it does analytic SQL well. **No public Jepsen report exists** for Exasol (⚠️ unverified by independent distributed-systems testing). Known limitation/failure mode: object-level locking makes concurrent writers to the same table serialize, which surprises teams expecting OLTP concurrency.

## Ecosystem & people
- **Canonical use cases:** High-performance BI/dashboard back-end, data-mart and data-warehouse acceleration, ad-hoc analytic SQL over large datasets that fit (mostly) in cluster RAM, in-database analytics via UDFs.
- **Anti-patterns:** OLTP / high-rate transactional workloads (object-level locks); document, KV, graph, full-text, or vector workloads (single relational model); workloads far larger than affordable RAM where a cheaper disk/object-store columnar engine ([clickhouse](clickhouse.md), [snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [duckdb](duckdb.md)) is more cost-effective; teams needing open source / no vendor lock-in.
- **Connectors / tooling:** ODBC/JDBC/ADO.NET; integrates with BI tools (Tableau, MicroStrategy, Power BI, Looker) and ETL/integration tools (Informatica, Talend); virtual-schema connectors for federation; works with dbt via community/vendor adapters. ⚠️ unverified — confirm current CDC/Kafka and dbt adapter support status.
- **Community / support:** Commercial vendor with paid support; smaller community than mainstream warehouses; docs are reasonable but the product is niche. Learning curve is low for SQL/BI users precisely because tuning is automated.

## Licensing & cost
- **License:** Proprietary, not open source. Free tiers exist: **Community Edition** (free, on-prem, up to ~200 GB raw data) and **Personal Edition** (free, single-user, full enterprise features, BYOC into AWS/Azure/Exoscale); **Enterprise Edition** and **Exasol SaaS** are commercial ([Exasol docs — Editions](https://docs.exasol.com/db/latest/get_started/exasol_editions.htm)). See [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 OSS relicensing event — it was never open source.
- **Self-managed vs managed:** Both. Self-managed on-prem/cloud (Enterprise), or fully managed **Exasol SaaS** (S3-backed, multi-cluster). Lock-in via the proprietary engine and EXAoperation tooling.
- **Cost model:** Licensing is **raw-data-size based** (a "Raw Data" license caps total raw data across the cluster), with a BYOL option that decouples static software license from dynamic cloud-resource billing ([Exasol docs — Licensing](https://docs.exasol.com/db/latest/planning/licensing.htm)). SaaS uses consumption credits (compute config + storage + data transfer). Because it is in-memory, cost scales with the RAM needed to hold the hot working set — cheap at small scale can invert at large data volumes versus disk/object-store warehouses.

## Hardware / deployment
- **Resource profile:** Memory-bound. Performance depends on the hot working set fitting in cluster RAM; the more of the active data that lives in memory, the better. CPU matters for parallel scan/join; disk holds the persisted compressed columns.
- **Storage assumptions:** Local fast storage on cluster nodes (NVMe/SSD favored) for the persisted column store; SaaS uses S3 object storage behind a compute layer.
- **Footprint:** Single node up to large clusters (hundreds of nodes), shared-nothing. Not embedded. Available as appliance/self-managed cluster and as serverless-ish managed SaaS.
- **Deployment:** On-prem, cloud (AWS/Azure/GCP marketplaces), hybrid, and SaaS. ⚠️ unverified — Kubernetes/StatefulSet support specifics should be confirmed; historically Exasol shipped as a clustered OS/appliance rather than a k8s-native database.

## Bottom line
Reach for Exasol when you need a fast analytic SQL warehouse and want minimal physical tuning — its auto-indexing and in-memory MPP make BI queries fast with little DBA effort, and TPC-H pedigree backs the speed claims. Avoid it for OLTP (object-level locking serializes table writers), for non-relational workloads, and where open source / no lock-in is a hard requirement; at large data volumes the in-memory, RAM-cost model can lose to disk/object-store columnar engines like [clickhouse](clickhouse.md), [snowflake](snowflake.md), or [google-bigquery](google-bigquery.md). Biggest gotcha: lock granularity is the **whole table/schema**, so "serializable" here means coarse object locks, not row-level MVCC — fine for load-then-query, painful for concurrent writers.

## Sources
- [Exasol docs — Transaction Management](https://docs.exasol.com/db/latest/database_concepts/transaction_management.htm)
- [Exasol docs — Editions overview](https://docs.exasol.com/db/latest/get_started/exasol_editions.htm)
- [Exasol docs — Licensing](https://docs.exasol.com/db/latest/planning/licensing.htm)
- [Exasol docs — Fail Safety (on-premise)](https://docs.exasol.com/db/latest/planning/fail_safety/fail_safety_on_premise.htm)
- [Exasol docs — Redundancy](https://docs.exasol.com/db/latest/administration/on-premise/architecture/redundancy.htm)
- [Exasol docs — Cluster Architecture](https://docs.exasol.com/db/latest/administration/on-premise/architecture/cluster_architecture.htm)
- [Exasol docs — UDF programming languages](https://docs.exasol.com/db/latest/database_concepts/udf_scripts/programming_languages_detail.htm)
- [Exasol docs — Synchronous Dual Data Center](https://docs.exasol.com/db/7.1/planning/business_continuity/sddc_details.htm)
- [Exasol product — Architecture overview](https://www.exasol.com/product-overview/architecture)
- [Exasol SaaS](https://www.exasol.com/exasol-saas/)
- [Wikipedia — Exasol](https://en.wikipedia.org/wiki/Exasol)
