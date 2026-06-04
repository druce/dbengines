---
name: GBase
slug: gbase
rank: 120
data_model: Relational
license: Proprietary (commercial; source-available editions exist for some products)
summary: Chinese MPP columnar analytical data warehouse (GBase 8a), built for SQL OLAP at telecom/government/bank scale; an OLTP product (8s) and a distributed/cloud product (8c) share the brand but not the engine.
last_researched: 2026-06-04
confidence: medium
---

# GBase

> A family of Chinese-domestic ("信创") databases from General Data Technology; the flagship and db-engines-ranked product is **GBase 8a**, a shared-nothing MPP **columnar analytical** warehouse — think a Greenplum/Vertica-class OLAP engine localized for Chinese government, telecom, and banking deployments.

## When to use

**Use GBase if:**
- ✅ You need a mature, high-compression MPP analytical (OLAP) warehouse and operate in the Chinese market where domestic-vendor (信创) procurement mandates rule out [oracle](oracle.md)/Teradata/US-cloud warehouses.
- ✅ You want a localized Teradata/Greenplum/Vertica alternative with Chinese-language support and large existing government/telecom/finance reference deployments.
- ✅ Your workload is bulk-load-then-scan BI/decision-support over large structured datasets (GBase 8a, columnar).

**Avoid GBase if:**
- ❌ You run OLTP / high-rate transactional workloads or need enforced PK/FK/unique constraints — 8a is a load-and-scan warehouse (use the separate, unrelated 8s engine instead).
- ❌ You need English documentation, a global community, or independently-verified distributed-correctness — claims are vendor-stated with no Jepsen/third-party verification available to outside readers.
- ❌ You expect one engine — "GBase" is three unrelated engines (8a/8s/8c) under one brand that don't share a storage engine; benchmark before betting on it.

Note on scope: "GBase" is a brand covering several distinct engines — **8a** (MPP analytics, columnar), **8s** (OLTP; an Informix-lineage transactional DB), and **8c** (distributed/cloud-native, [postgresql](postgresql.md)/openGauss-lineage), plus the GCDW cloud warehouse. They do not share a storage engine. This page describes **GBase 8a** unless noted, since it is the product that defines GBase's db-engines presence and analytical reputation. Treat cross-product claims with care.

## Identity
- **Taxonomy / data model:** relational, SQL. GBase 8a is an analytical relational engine; the broader brand is effectively multi-model only across separate products, not one engine.
- **Storage model:** **column-store** primarily, with a row-column hybrid (mixed) storage option per table. Heavy columnar compression (vendor claims 1:20 typical, up to 1:30) plus automatic "coarse-grained intelligent indexes" — block-level min/max-style zone maps rather than B-trees, kept small (<1% expansion, vendor claim). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md)-style; it is a columnar warehouse layout closer to [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** **OLAP** — data warehousing, BI, decision support. GBase 8a does **not** enforce primary keys, unique keys, foreign keys, or index constraints (⚠️ unverified — widely reported as a design choice and consistent with the load-and-scan warehouse model, but not confirmed here from an official 8a constraint-support spec), which is normal for a warehouse but disqualifies it for OLTP. For transactional workloads the brand points you at **GBase 8s** instead. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). No genuine single-engine HTAP claim here.

## Distribution & consistency
- **CAP under partition:** ⚠️ unverified — vendor docs do not state a clean [cap-pacelc](../concepts/cap-pacelc.md) classification. Architecturally it is a coordinator + data-node MPP warehouse with synchronous replica maintenance, so it behaves **CP-leaning** (a shard with no surviving replica stalls rather than serving stale data). No independent (e.g. Jepsen) verification exists.
- **PACELC:** ⚠️ unverified — not characterized by the vendor; treat any latency-vs-consistency tradeoff claims as unconfirmed.
- **Default isolation & what's achievable:** vendor documents **Repeatable Read and Snapshot isolation via [mvcc](../concepts/mvcc.md)** for transactional tables. As a warehouse the common pattern is bulk-load-then-query rather than concurrent read/write transactions; serializability is not advertised. See [isolation-levels](../concepts/isolation-levels.md). ⚠️ unverified — exact concurrency guarantees under heavy mixed load are not independently tested.
- **Replication:** data is replicated across **GNode** data nodes — 0, 1, or 2 replicas configurable (i.e. up to 3 copies). The primary shard assembles loaded data and forwards to replica nodes; vendor describes this as synchronous standby-shard sync. With 3 copies the cluster tolerates 2 simultaneous node failures for that shard. See [replication-models](../concepts/replication-models.md).
- **Cluster control plane:** three roles — **GCluster** (scheduling/coordinator nodes: access, auth, SQL parse/plan), **GNode** (data + replicas), and **GCware** (metadata/cluster consistency, which uses the **Raft** protocol — see [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)). Up to 64 coordinator nodes and 4,096+ data nodes claimed.
- **Tunable consistency?** No Dynamo-style per-query consistency levels; replica count is a table/cluster setting, not a read-time knob.
- **Clock dependency:** ⚠️ unverified — no documented dependence on synchronized clocks (no TrueTime/HLC claims). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema. Tables are typed and defined up front.
- **Migration/evolution:** ⚠️ unverified — online-DDL vs locking-`ALTER` behavior is not clearly documented in English sources; columnar add/drop column is typically cheap but assume some operations rewrite/lock.
- **Type system:** standard SQL scalar types, dates/times, OLAP-oriented numerics. ⚠️ unverified — native JSON/array/geospatial/vector support is not clearly documented for 8a; do not assume rich semi-structured types.

## Query interface
- **Language:** **SQL**, advertised as ANSI/ISO **SQL-92/99/2003** compliant including SQL:2003 OLAP/window functions. Access via **ODBC, JDBC, ADO.NET, OLEDB**, plus C/Python/TCL APIs. MySQL-protocol-compatible client experience is commonly cited. ⚠️ unverified — exact dialect/standard-compliance breadth is a vendor claim, not independently audited.
- **Transactions:** MVCC-backed transactions exist on transactional tables (RR/snapshot), but the engine is optimized for bulk-load + analytic query, not high-rate multi-statement OLTP. Distributed-transaction "high availability for primary-replica sharding" is claimed.
- **Native vs app-side:** native distributed joins, aggregations, and window functions across the MPP cluster; the planner produces distributed execution plans. **No** PK/FK/unique/index constraints (warehouse design choice).
- **Stored procedures / UDFs:** ⚠️ unverified — procedural/UDF support exists in the broader GBase line; specifics for 8a not confirmed here.

## Scaling & topology
- **Horizontal**, shared-nothing MPP. Tables distributed by **HASH** (on a chosen key) or **RANDOM** distribution.
- **Sharding:** distribution is chosen at table-create time; **online horizontal scale-out** (adding nodes / redistributing) is supported with claimed ~20 TB/hour redistribution and "minimal business impact." Resharding/redistribution is still a heavyweight data-movement operation — plan capacity ahead.
- **Read replicas / read consistency:** replicas are for HA and parallel read, not a separate eventually-consistent tier; reads hit consistent shard data.
- **Storage/compute separation:** classic 8a is shared-nothing with local storage (compute and data colocated) — **not** separated. The separate **GCDW** cloud product is the storage/compute-separated offering. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** ingest is bulk/parallel load oriented (claimed 30 TB/hour+ load). ⚠️ unverified — explicit WAL/fsync policy and the crash data-loss window are not documented in available English sources; durability rests on replica copies plus load-staging more than a documented per-row WAL. See [wal-and-durability](../concepts/wal-and-durability.md). Do not assume zero-data-loss-on-crash without testing.
- **Throughput/latency:** strong large-scan/aggregation throughput from columnar + compression + zone-map skipping; designed for high-concurrency BI. ⚠️ unverified — no independent p99/tail benchmarks available; all throughput figures (load rate, compression ratio) are vendor numbers under ideal conditions.
- **Compaction / GC:** columnar storage with periodic space-reclamation operations (DBA-driven space reclaim is part of standard ops). ⚠️ unverified — its impact on query p99 is not documented.

## Operations & maturity
- **Backup/restore:** full + incremental backup and active-standby cluster sync with same-city disaster recovery are documented. PITR specifics ⚠️ unverified.
- **Observability:** cluster-management tooling (GCware/cluster manage tool), system metadata views, distributed EXPLAIN/execution plans. Slow-query logging ⚠️ unverified.
- **Upgrade story:** ⚠️ unverified — rolling vs downtime upgrade behavior not documented in English sources; day-2 burden is real (MPP cluster ops: redistribution, replica management, space reclaim, GCware quorum health).
- **Maturity:** production-proven **within China** — deployed since the 2000s across government, telecom, finance (e.g. cited as the core data warehouse of a major state bank's big-data platform), power, and regulators. **No Jepsen report exists.** Documentation and community are predominantly Chinese; independent verification of distributed-correctness claims is essentially unavailable to outside readers — the biggest evidence gap on this page.

## Ecosystem & people
- **Canonical use cases:** large structured-data warehouses and BI/decision-support in Chinese enterprises and government, especially where **domestic-vendor / 信创 procurement mandates** rule out [oracle](oracle.md), [teradata](teradata.md), or US-cloud warehouses. Frequently positioned as a replacement for Teradata/Greenplum/Oracle DW.
- **Anti-patterns:** OLTP / high-rate transactional workloads (use GBase 8s or a real OLTP engine), key-value or document workloads, anything needing PK/FK constraints enforced by the DB, low-latency single-row lookups, or deployments outside the Chinese ecosystem where docs/support/community are thin.
- **Connectors:** standard ODBC/JDBC means it plugs into common BI tools (FineBI, HENGSHI, etc. document GBase connectors); Kafka/CDC/dbt integration is not first-class in the global ecosystem. ⚠️ unverified — robust CDC support.
- **Community / support:** commercial vendor (General Data Technology, Tianjin, founded 2004); strong commercial support and large reference base in China, weak global community and English documentation. Learning curve is moderate for anyone who knows MPP warehouses.

## Licensing & cost
- **License:** **proprietary / commercial.** Not open source for 8a. (Some GBase line members are source-available/openGauss- or PostgreSQL-derived, but 8a is a closed commercial product — verify per product.) See [license-taxonomy](../concepts/license-taxonomy.md). ⚠️ unverified — precise current licensing terms per edition.
- **Self-managed vs managed:** self-managed on-prem clusters are the norm (the deployment model the Chinese market expects); GCDW provides a cloud/managed warehouse. Available on AWS Marketplace as well.
- **Lock-in:** proprietary engine, Chinese-language ecosystem, and 信创 procurement context make this a strategic platform commitment, not a casually-swappable component.
- **Cost model:** ⚠️ unverified — typical per-node / per-core enterprise licensing; published pricing is not transparent outside sales channels.

## Hardware / deployment
- **Resource profile:** disk-and-CPU-bound analytical scanner; benefits from many cores and fast local storage. Working set need not fit in RAM (it scans compressed columns from disk), but RAM helps caching/joins.
- **Storage assumptions:** designed for **local storage** (SATA/SAS/SSD) in shared-nothing nodes; SAN/NAS and SSD/flash L2 cache configurations are supported. Intel published a "Select Solution" reference config for it.
- **Footprint:** **clustered** MPP (also deployable small/single-node for dev). Runs on x86-64 and **ARM** (important for Chinese domestic-chip mandates), CentOS/RHEL/SUSE Linux.
- **Deployment:** primarily on-prem; cloud via GCDW or marketplace images. k8s-native operation is not its heritage (stateful MPP with local disks).

## Bottom line
Reach for **GBase 8a** if you need a mature, high-compression MPP **analytical** warehouse and you are operating in the Chinese market where domestic-vendor (信创) requirements, Chinese-language support, and large existing reference deployments matter — it is a credible localized alternative to Teradata/Greenplum/Vertica. Do **not** reach for it for OLTP (that's a different product, 8s), for anything needing enforced PK/FK constraints, or if you need English documentation, a global community, or independently-verified distributed-correctness guarantees. The single biggest gotcha: "GBase" is **three unrelated engines under one brand**, and nearly all reliability/consistency claims are vendor-stated with **no Jepsen or third-party verification** available to non-Chinese readers — benchmark and test before betting on it.

## Sources
- [GBase 8a product page (official, EN)](https://www.gbase.cn/en/product/gbase-8a)
- [Introduction to High Availability in GBase 8a (GCluster/GNode/GCware, Raft) — vendor dev.to](https://dev.to/generaldata/introduction-to-high-availability-in-gbase-8a-7jf)
- [GBase Database High Availability Solutions (replica factor, primary/replica shards) — vendor](https://dev.to/generaldata/gbase-database-high-availability-solutions-ensure-data-integrity-relentless-pursuit-of-business-l1h)
- [GBase 8a MPP Cluster Performance Optimization: Storage — vendor Medium](https://medium.com/@gbasemarket/gbase-8a-mpp-cluster-performance-optimization-storage-optimization-81fc1295c49c)
- [GBase 8a Operations Cheat Sheet (DBA commands) — dev.to](https://dev.to/michaelfv/gbase-8a-operations-cheat-sheet-essential-commands-for-dbas-6bj)
- [Annual Review of GBase Database Technology 2024 (product family: 8a/8s/8c/GCDW) — Oreate AI](https://www.oreateai.com/blog/annual-review-of-gbase-database-technology-2024-core-technologies-and-application-practices-overview/3b5d181101e5785b478edad004c3a27b)
- [In-Depth Analysis of Domestic Database Vendors: GBASE and GoldenDB — Oreate AI](https://www.oreateai.com/blog/indepth-analysis-of-domestic-database-representative-vendors-gbase-and-goldendb/d598d341abc8d6f702543090d84fe614)
- [Database of Databases — GBase (dbdb.io)](https://dbdb.io/db/gbase)
- [GBase 8a MPP Cluster on AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-q26qp3u3qdu5e)
- [Intel Select Solutions for GBase 8a MPP Cluster](https://www.intel.in/content/www/in/en/products/solutions/select-solutions/analytics/gbase-8a-mpp-cluster-brief.html)
