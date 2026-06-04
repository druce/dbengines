---
name: Informix
slug: informix
rank: 38
data_model: Relational (object-relational, multi-model)
license: Proprietary (commercial; free Developer/Innovator-C editions). IBM-owned, HCL-developed.
summary: Mature object-relational OLTP engine with native time-series and spatial; quiet, low-admin, embeddable, but proprietary and a shrinking talent pool.
last_researched: 2026-06-04
confidence: medium
---

# Informix

> A decades-proven, low-administration object-relational SQL engine whose real edge is native time-series + spatial in one OLTP engine — useful for IoT/embedded, but locked into a proprietary stack with a thinning ecosystem.

## When to use

**Use Informix if:**
- ✅ You already run it, or need rock-solid low-admin ("set it and forget it") OLTP on modest hardware.
- ✅ You want native time-series and spatial (R-tree) in one engine for IoT/edge/embedded, smart-meter, retail POS, or manufacturing workloads.
- ✅ You need a small-footprint, embeddable object-relational engine with full multi-statement ACID and a MongoDB-compatible document API.

**Avoid Informix if:**
- ❌ It is a greenfield project — it is proprietary with a shrinking talent pool and an unusual IBM-owns/HCL-develops arrangement (the biggest gotcha); [postgresql](postgresql.md) with TimescaleDB/PostGIS covers most of the same ground openly.
- ❌ You need cloud-native elasticity, serverless, or web-scale horizontal scale-out — there is no first-party managed DBaaS and resharding is manual.
- ❌ You need large-scale analytics (use a dedicated columnar warehouse) or an active open-source community and deep third-party tooling.

## Identity
- **Taxonomy / data model:** Object-relational RDBMS, marketed as multi-model: SQL relational + user-defined types, native time-series, spatial (R-tree), and JSON/BSON document (MongoDB-compatible wire API). Native vector search is **not yet GA** — a "vector blade" with a native vector type is announced for HCL Informix 15, slated for **Summer 2026** ([Actian: Informix vector blade](https://www.actian.com/blog/databases/from-spatial-to-vectors-how-hcl-informix-brings-ai-to-your-existing-data/)), i.e. not shipped as of 2026-06-04. Multi-model claims are real but uneven in maturity — the time-series and spatial DataBlades are the well-trodden paths; document is a newer overlay and vector is forthcoming. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Primarily a **row-store** on a B-tree on-disk layout (see [lsm-vs-btree](../concepts/lsm-vs-btree.md)); data lives in dbspaces/chunks managed by the engine, not the filesystem. The **Informix Warehouse Accelerator (IWA)** is a separate in-memory **columnar** store (Huffman/dictionary-encoded) used to accelerate analytic queries ([IWA overview](https://docs.deistercloud.com/content/Databases.30/IBM%20Informix%20IWA.4/index.xml?embedded=true)).
- **Workload:** Primarily **OLTP**, low-admin, high-transaction. HTAP-ish only via IWA: OLAP is physically offloaded into a separate columnar in-memory accelerator process and the optimizer routes eligible queries there — so the analytic/transactional separation is a **distinct columnar engine attachment**, not a vague "HTAP" claim. ⚠️ unverified — current IWA availability/parity in the latest HCL editions; historically IWA shipped with Advanced editions.

## Distribution & consistency
- **CAP under partition:** Effectively **CP** for the primary in its HA cluster model — a single primary owns writes; secondaries serve reads. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, consistency is preserved at the cost of write availability on the failed primary (failover required); else, latency-vs-consistency is **tunable** via sync vs async HDR replication. ⚠️ unverified — no formal PACELC classification published; this is inferred from the replication model.
- **Default isolation & what's achievable:** In a logged, non-ANSI database the default is **Committed Read**; in an ANSI-compliant database the default is **Repeatable Read** ([HCL docs: default isolation](https://informix.hcldoc.com/12.10/help/topic/com.ibm.sqls.doc/ids_sqs_1206.htm)). Levels: Dirty Read (= ANSI Read Uncommitted), Committed Read, Cursor Stability, Repeatable Read (= ANSI Serializable via row/range locking) ([SET ISOLATION docs](https://www.ibm.com/docs/en/informix-servers/12.10.0?topic=levels-using-dirty-read-isolation-level)). Concurrency is **lock-based**, not snapshot MVCC; the **LAST COMMITTED** option on Committed Read returns the most recently committed row version instead of blocking on exclusive locks ([USELASTCOMMITTED](https://www.ibm.com/docs/en/informix-servers/14.10?topic=parameters-uselastcommitted-configuration-parameter)). Note: "Repeatable Read" here is the engine's serializable equivalent (it prevents phantoms by locking **all rows examined, not just those fetched**, for the duration of the transaction) — not [mvcc](../concepts/mvcc.md)-style snapshots ([Repeatable Read isolation](https://www.ibm.com/docs/en/informix-servers/14.10.0?topic=level-repeatable-read-isolation)). See [isolation-levels](../concepts/isolation-levels.md).
- **Replication / HA:** Single-leader log shipping. **HDR** (one synchronous-or-async secondary), **RSS** (remote standalone async secondaries, can be many), **SDS** (shared-disk secondaries on the same storage, always in sync), and **Enterprise Replication (ER)** for async, log-based, multi-master / partial replication between independent servers ([HA solutions](https://advantek.com.co/en/index.php/high-availability-solutions-for-informix/)). Failover is arbitrated by the **Connection Manager** (recommended `DRAUTO=3`); split-brain is the operator's risk if arbitration is misconfigured. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes operationally: choose sync vs async HDR, and which secondary type. Note a sharp gotcha: HDR secondaries **effectively read at Dirty Read isolation regardless of the requested isolation level**, unless `UPDATABLE_SECONDARY` is enabled ([dirty-read-on-secondary behavior](https://www.ibm.com/docs/en/informix-servers/12.10.0?topic=levels-using-dirty-read-isolation-level)).
- **Clock dependency:** No TrueTime/HLC-style clock-dependent correctness; ordering comes from the logical log. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write** for relational tables (rigid, typed). JSON/BSON collections allow schema-on-read document storage. Object-relational extensibility: user-defined types, opaque types, and **DataBlades** add domain types (time-series, spatial) into the type system.
- **Migration/evolution:** Standard SQL DDL. ⚠️ unverified — exact online/non-locking DDL coverage; historically many `ALTER TABLE` operations are in-place ("fast alter") but some force a slow table rebuild with locking.
- **Type system:** Rich — native time-series (`TimeSeries` type with loader + SQL routines), spatial/geodetic (R-tree), JSON/BSON, arrays/collections (SET/LIST/MULTISET), row types, LOBs, interval/datetime. A native vector type is announced for v15 (Summer 2026) but not yet GA as of 2026-06-04.

## Query interface
- **Language:** SQL (Informix dialect, broadly SQL-92 with object-relational extensions). Document access via a **MongoDB-compatible wire protocol** and REST listener. Time-series exposed through SQL routines.
- **Transactions:** Full **multi-statement ACID** with WAL logging (logged databases). Unlogged databases exist for bulk/legacy use.
- **Native vs app-side:** Native secondary indexes (B-tree, R-tree, functional), joins, aggregations, window functions; the cost-based optimizer can route analytic portions to IWA.
- **Stored procedures / UDFs:** SPL (Stored Procedure Language), plus C and Java UDRs (user-defined routines); DataBlades are packaged extensions.

## Scaling & topology
- **Vertical first:** The **Dynamic Scalable Architecture (DSA)** uses multithreaded **virtual processors** over a shared-memory pool to scale on a single node across CPUs/disks — its historic strength. Vendor cites very high single-node TPS ([HCL/Actian](https://www.actian.com/databases/hcl-informix/)) — treat the "2M+ TPS" number as a marketing benchmark, not a guarantee for your workload.
- **Horizontal:** Sharding across cluster members via Enterprise Replication and the **Grid**; partitioning (fragmentation) by range/list/expression/round-robin within a server. Auto-rebalancing/resharding is not a one-click strength — manual planning is the norm.
- **Read replicas:** HDR/RSS/SDS secondaries serve reads; consistency varies (async secondaries lag; reads there are effectively dirty-read unless made updatable, see above).
- **Storage/compute separation:** Not in the cloud-native Aurora/Neon sense; SDS (multiple compute nodes over shared disk) is the closest analog. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WAL via the **logical log** plus a **physical log** for fast-recovery checkpointing; configurable buffered vs unbuffered logging. Unbuffered/sync logging minimizes the data-loss window; buffered logging trades a small loss window for throughput. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — precise default fsync/group-commit behavior across editions.
- **Throughput/latency:** Long reputation for steady OLTP throughput and low latency on modest hardware; small memory footprint suits embedded/edge. ⚠️ unverified — independent published p99/tail-latency benchmarks are scarce; most numbers are vendor-sourced.
- **Compaction/vacuum/GC:** B-tree, so no LSM-style compaction; instead routine maintenance is index rebuilds, `update statistics`, and dbspace/extent management. p99 impact comes from checkpoints and lock contention rather than background compaction.

## Operations & maturity
- **Backup/restore:** `ontape` and `onbar` (with a storage manager / IBM Spectrum Protect) provide full + incremental backups, and **point-in-time restore** via logical-log replay.
- **Observability:** `onstat`/`oncheck` utilities, SMI/sysmaster pseudo-tables for metrics, SQL `EXPLAIN`/SET EXPLAIN query plans, and the OpenAdmin Tool (OAT) / HCL admin console.
- **Upgrade story:** In-place server upgrades; rolling upgrades possible across a cluster but require care. Day-2 burden is famously **low** — "set it and forget it" is the long-standing selling point.
- **Maturity:** Very mature (lineage to the late 1980s; IBM acquired Informix Software in 2001, HCL took over development in 2017). Battle-tested in retail, finance, telco, manufacturing, and IoT. **No public Jepsen report exists** for Informix (⚠️ none found as of 2026-06-04). Known concerns are ecosystem decline and proprietary lock-in rather than reliability bugs.

## Ecosystem & people
- **Canonical use cases:** Embedded/edge OLTP, retail point-of-sale, smart-meter / IoT time-series, manufacturing, and shops with an existing Informix estate wanting native time-series + spatial without bolting on a second system.
- **Anti-patterns:** Greenfield projects wanting a large hiring pool and open ecosystem (prefer [postgresql](postgresql.md)); cloud-native serverless/elastic needs; pure large-scale analytics (use a columnar warehouse); teams that need an active open-source community and third-party tooling.
- **Connectors:** ODBC/JDBC/.NET, ESQL/C, the MongoDB driver via the document API, CDC capture API, and ER for replication. Third-party tooling (BI, ORMs, dbt adapters) exists but is thin versus Postgres/MySQL/Oracle.
- **Community/support:** Commercial support from IBM and HCL/Actian; the **IIUG** user group is active but the overall community and new-engineer availability are shrinking — a real staffing risk.

## Licensing & cost
- **Proprietary, closed-source.** Free, restricted **Developer** and **Innovator-C** editions (Innovator-C capped at 2 cores / 8 GB RAM / 50 GB and usable for small production without a license fee — [edition limits](https://www.cursor-distribution.de/en/sales-informix/informix-produktlinien/informix-innovator-c-en)). Commercial editions (Express, Workgroup, Advanced Workgroup, Enterprise, Advanced Enterprise; HCL ships a single edition with Advanced-Enterprise parity) are paid. Not source-available; not affected by the post-2018 SSPL/BSL relicensing wave because it was never open source. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Ownership oddity:** IBM owns Informix but **delegated development and support to HCL in 2017** for 15 years; it is sold as both "IBM Informix" and "HCL Informix" (and surfaced via Actian) ([Wikipedia](https://en.wikipedia.org/wiki/IBM_Informix)).
- **Self-managed vs managed:** Primarily self-managed (on-prem, cloud VM, AWS Marketplace AMIs). Lock-in via proprietary SQL extensions, DataBlades, and the storage engine.
- **Cost model:** Per-core / PVU-style licensing; historically ranged roughly tens to ~540 USD/PVU depending on edition ([licensing metrics](https://omtco.eu/references/ibm/ibm-informix-product-editions-metrics-and-licensing-restrictions/)). ⚠️ unverified — current HCL/Actian list pricing.

## Hardware / deployment
- **Resource profile:** Efficient and modest — small footprint, runs well on limited RAM/CPU, which is why it persists in embedded/edge and IoT. Working set need not fit in RAM (disk-resident B-tree with a buffer pool); IWA analytics is memory-bound.
- **Storage assumptions:** Works on local disk or SAN; SDS specifically assumes **shared storage** across nodes. No hard NVMe requirement.
- **Footprint:** Single-node, clustered (HDR/RSS/SDS/ER), or **embeddable** within applications/appliances.
- **Deployment:** On-prem, VM/cloud images, containers; no first-party fully-managed serverless DBaaS in the Aurora sense. ⚠️ unverified — current k8s operator maturity.

## Bottom line
Reach for Informix if you already run it, or need rock-solid low-admin OLTP with **native time-series and spatial in one engine** for IoT/edge/embedded deployments on modest hardware. Do **not** pick it for greenfield projects, cloud-native elasticity, big analytics, or where you need to hire easily and lean on an open ecosystem — [postgresql](postgresql.md) (with TimescaleDB/PostGIS) covers most of the same ground openly. The single biggest gotcha: it is **proprietary with a shrinking talent pool and an unusual IBM-owns/HCL-develops arrangement**, so factor long-term staffing and vendor risk into any new bet.

## Sources
- [Informix — Wikipedia](https://en.wikipedia.org/wiki/IBM_Informix)
- [HCL/IBM docs: Using the Dirty Read isolation level (and HDR-secondary behavior)](https://www.ibm.com/docs/en/informix-servers/12.10.0?topic=levels-using-dirty-read-isolation-level)
- [HCL docs: Default isolation levels](https://informix.hcldoc.com/12.10/help/topic/com.ibm.sqls.doc/ids_sqs_1206.htm)
- [IBM docs: Repeatable Read isolation (= ANSI Serializable; locks all examined rows)](https://www.ibm.com/docs/en/informix-servers/14.10.0?topic=level-repeatable-read-isolation)
- [Actian/HCL: Informix vector blade (announced for v15, Summer 2026)](https://www.actian.com/blog/databases/from-spatial-to-vectors-how-hcl-informix-brings-ai-to-your-existing-data/)
- [USELASTCOMMITTED configuration parameter](https://www.ibm.com/docs/en/informix-servers/14.10?topic=parameters-uselastcommitted-configuration-parameter)
- [High-availability solutions for Informix (HDR/RSS/SDS/ER)](https://advantek.com.co/en/index.php/high-availability-solutions-for-informix/)
- [Informix Warehouse Accelerator (IWA) overview](https://docs.deistercloud.com/content/Databases.30/IBM%20Informix%20IWA.4/index.xml?embedded=true)
- [HCL Informix (Actian) product page](https://www.actian.com/databases/hcl-informix/)
- [Informix Innovator-C edition limits](https://www.cursor-distribution.de/en/sales-informix/informix-produktlinien/informix-innovator-c-en)
- [IBM Informix licensing metrics/restrictions](https://omtco.eu/references/ibm/ibm-informix-product-editions-metrics-and-licensing-restrictions/)
- [Compare Informix v15 editions — IIUG](https://www.iiug.org/en/2019/10/08/compare-informix/)
