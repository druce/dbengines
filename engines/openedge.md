---
name: OpenEdge
slug: openedge
rank: 79
data_model: Relational
license: Proprietary (commercial, per-core / per-user; no OSS edition)
summary: Progress's 4GL-plus-RDBMS application platform; a tightly-coupled ABL language and database that ERP/ISV apps (notably QAD) are built on, not a database you adopt standalone.
last_researched: 2026-06-04
confidence: medium
---

# OpenEdge

> A proprietary, single-leader relational engine fused to the ABL (Progress 4GL) language — chosen because your application is *already written in ABL*, not on database merits.

## When to use

**Use OpenEdge if:**
- ✅ You run or build on an ABL/Progress application — above all QAD ERP or a vendor ISV business app
- ✅ You want an integrated, battle-tested 4GL-plus-RDBMS for OLTP where language and database were developed together
- ✅ You need AppServer (PASOE) app-tier fan-out and async-replica read offload within a single-primary topology

**Avoid OpenEdge if:**
- ❌ It's a greenfield project with no ABL commitment — picking it standalone over [postgresql](postgresql.md) is rarely justified on DB merits
- ❌ You want open-source, cloud-native, horizontally-sharded, or polyglot-driver ecosystems — it is proprietary, single-primary, vertically scaled, high lock-in
- ❌ You can't enforce disciplined lock scoping — ABL defaults to SHARE-LOCK and is routinely written NO-LOCK (effectively read-uncommitted), so consistency is by convention
- ❌ You need analytics/HTAP or a large pool of available developers (shrinking ABL talent)

## Identity
- **Taxonomy / data model:** relational RDBMS, paired with the OpenEdge Advanced Business Language (ABL), formerly "Progress 4GL" through v9, renamed in 2006 ([Wikipedia: OpenEdge ABL](https://en.wikipedia.org/wiki/OpenEdge_Advanced_Business_Language)). It is sold as an application *platform* (language + database + tooling), not a standalone DB. ABL is procedural with OO support added in 10.1.
- **Storage model:** row-store, B-tree indexes, fixed-size block/area on-disk layout. Modern "Type II" storage area architecture (vs. legacy "Type I") clusters records by object for better locality ([Progress: recovery mechanisms](https://docs.progress.com/bundle/openedge-database-management/page/Introduction-to-recovery-mechanisms.html)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM — it is a traditional update-in-place B-tree engine.
- **Workload:** OLTP. Designed for business/ERP transaction processing. No HTAP claim; analytics is done by reporting against replicas or exporting. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP / [replication-models](../concepts/replication-models.md) single-leader. The native database is a single-primary server; [cap-pacelc](../concepts/cap-pacelc.md) applies in the trivial sense that a partitioned async replica simply lags rather than serving conflicting writes.
- **PACELC:** under partition the primary continues (replica falls behind / failover is operator-driven); else (normal operation) async replication favors latency over consistency — the target lags the source.
- **Default isolation & what's achievable:** *Two distinct concurrency surfaces.*
  - **ABL native access** uses explicit record locks, not SQL isolation levels: `NO-LOCK` (read-only, may read uncommitted/in-flight data — effectively read-uncommitted), `SHARE-LOCK` (the default for FIND/FOR EACH/GET), and `EXCLUSIVE-LOCK` for writes ([Progress: Record locking in ABL](https://documentation.progress.com/output/ua/OpenEdge_latest/gsabl/record-locking-in-abl.html)). In practice most read-heavy ABL code is written with `NO-LOCK`, so applications routinely run at effectively read-uncommitted semantics by convention. See [isolation-levels](../concepts/isolation-levels.md).
  - **OpenEdge SQL** (ODBC/JDBC) supports all four ANSI levels — READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE — set via `SET TRANSACTION ISOLATION LEVEL`, enforced with table/record locks rather than [mvcc](../concepts/mvcc.md) snapshots ([Progress: Setting isolation levels](https://docs.progress.com/bundle/openedge-sql-development/page/Setting-isolation-levels.html); [Working with locking behavior and isolation levels](https://documentation.progress.com/output/ua/OpenEdge_latest/dmsdv/working-with-locking-behavior-and-isolation-leve.html)). ⚠️ unverified — the official OpenEdge SQL docs do not state a *default* isolation level (they require `SET TRANSACTION ISOLATION LEVEL` to choose one); READ COMMITTED is a common RDBMS default but is unconfirmed for OpenEdge. Isolation is enforced via locking, not MVCC snapshots (the docs pair isolation with "transactions and locking"; no snapshot/version-store mechanism is documented).
- **Replication:** OpenEdge Replication is single-leader source→target log shipping (after-image based). Synchronous and asynchronous modes existed pre-12.0, with async recommended for performance ([Progress: replication options](https://docs.progress.com/bundle/openedge-database-replication-quickstart/page/OpenEdge-replication-options.html)). A "replication set" adds a second target so a primary target can be promoted on source loss; the role switch is a multi-step, coordinated shutdown/transition operation, not automatic split-brain-safe failover ([Progress: how replication works with a replication set](https://documentation.progress.com/output/ua/OpenEdge_latest/ffr/how-openedge-replication-works-with-a-replicatio.html)).
- **Tunable consistency?** Only via the lock keywords (ABL) or SQL isolation level per session — not Dynamo-style per-query quorum.
- **Clock dependency:** No documented dependence on synchronized clocks for correctness (single-primary log shipping). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; tables, fields, indexes defined in the data dictionary.
- **Migration/evolution:** schema changes via incremental delta `.df` files and the schema-change tooling; many DDL operations can be applied online but large structural changes (area moves, index rebuilds) are maintenance events. ⚠️ unverified — exact online-DDL locking granularity not confirmed here.
- **Type system:** standard scalar types plus ABL-specific types; supports CLOB/BLOB, table partitioning (horizontal), multi-tenancy, and transparent data encryption as enterprise features ([Progress OpenEdge ABL feature page](https://www.progress.com/openedge/features/abl)). Native vector/geospatial types are not a focus.

## Query interface
- **Language:** dual. (1) **ABL** — the 4GL with integrated data access (FOR EACH, FIND, etc.), the primary interface for OpenEdge applications. (2) **OpenEdge SQL** — ANSI SQL via ODBC/JDBC for external/BI tools. The two engines coexist over the same database.
- **Transactions:** full multi-statement ACID; two-phase commit available for distributed/cross-database transactions.
- **Native vs app-side:** native secondary indexes, joins, and aggregations in both ABL and SQL.
- **Stored procedures / UDFs:** business logic lives in ABL procedures/classes (AppServer); OpenEdge SQL also supports SQL stored procedures (Java-based).

## Scaling & topology
- **Vertical vs horizontal:** primarily vertical (scale the primary server). No built-in automatic sharding/distributed-write cluster; horizontal scale is via app-tier (AppServer) fan-out and read offload to replicas, plus table partitioning within a single database.
- **Sharding:** manual at best; resharding is an application-design exercise, not a managed feature.
- **Read replicas:** OpenEdge Replication targets can serve read-only reporting; reads are eventually-consistent (target lags source under async). Reporters are advised to use READ UNCOMMITTED to avoid lock escalation on the target.
- **Storage/compute separation:** No — local/SAN-attached storage, monolithic server. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) architecture.

## Performance & durability
- **Write path:** Write-Ahead Logging via the Before-Image (BI) file written before data changes; After-Image (AI) files enable roll-forward recovery; two-phase commit for distributed txns ([Progress: recovery mechanisms](https://docs.progress.com/bundle/openedge-database-management/page/Introduction-to-recovery-mechanisms.html)). See [wal-and-durability](../concepts/wal-and-durability.md). Data-loss window depends on BI/AI flush settings and whether AI archiving + replication are enabled; with async replication, committed-but-unshipped transactions can be lost on a hard primary loss.
- **Throughput/latency:** mature, predictable OLTP performance for its target workloads; p99 driven by record-lock contention (long-held SHARE/EXCLUSIVE locks in poorly-scoped ABL transactions are the classic hotspot). No public, current standardized benchmarks reviewed.
- **Compaction / vacuum / GC:** no MVCC version GC. Space management is via storage-area maintenance (dbanalys, index rebuild/compact, table moves); fragmentation in Type I areas historically required periodic maintenance, much improved by Type II areas.

## Operations & maturity
- **Backup/restore, PITR:** online/offline backups, plus roll-forward recovery from backup + After-Image files for point-in-time recovery; two-phase commit transaction log area for distributed recovery.
- **Observability:** PROMON monitoring utility, OpenEdge Management/Explorer, SQL EXPLAIN for the SQL engine, ABL compile-time/XREF and client logging.
- **Upgrade story:** version upgrades are planned maintenance (dump/load or in-place conversion across major versions); day-2 burden centers on BI/AI tuning, lock-table sizing, and replication monitoring — specialist DBA knowledge ("Progress DBA") is its own skill.
- **Maturity:** very mature (1980s lineage), long production track record in ERP/manufacturing. Known failure modes: lock-table exhaustion, BI growth runaway, long-running ABL transactions blocking others. **No Jepsen report exists** for OpenEdge ⚠️ unverified-by-absence — no formal distributed-consistency analysis is publicly known.

## Ecosystem & people
- **Canonical use cases:** existing ABL/Progress applications — most prominently **QAD** ERP — and ISV-built vertical business apps where the database and the application were developed together. Strong fit when you already own such an app.
- **Anti-patterns:** greenfield projects with no ABL commitment; teams wanting open-source, cloud-native, horizontally-sharded, or polyglot-driver ecosystems; analytics/HTAP workloads. Choosing OpenEdge as a fresh standalone database (over [postgresql](postgresql.md) or a managed cloud DB) is rarely justified on database merits alone.
- **Drivers / connectors:** ODBC/JDBC (DataDirect), .NET, REST/Web (PASOE — Progress Application Server for OpenEdge), Pro2 for replication to other targets, CDC features in recent versions. Smaller third-party connector ecosystem (dbt/Kafka/BI) than mainstream OSS engines.
- **Community & support:** commercial support from Progress Software; active but niche community (PUG Challenge, ProgressTalk). Docs are thorough but vendor-siloed. Steep, specialized learning curve; shrinking pool of new ABL developers.

## Licensing & cost
- **License:** proprietary commercial; **no open-source edition**. Perpetual and subscription/SaaS options; EULA-governed ([Progress OpenEdge EULA](https://www.progress.com/legal/license-agreements/openedge)). Not on the OSS spectrum at all — see [license-taxonomy](../concepts/license-taxonomy.md). A free *no-cost* "Classroom" edition of the OpenEdge Developers Kit exists for students/hobbyists, but it is still proprietary (not open source) and not for production use ([Progress OEDK](https://www.progress.com/oedk)).
- **Self-managed vs managed:** primarily self-managed (on-prem or customer cloud / AWS templates); Progress also offers cloud/SaaS arrangements, often via ISVs.
- **Lock-in:** high. ABL applications are deeply coupled to the platform; migrating off means rewriting application logic, not just moving data.
- **Cost model:** per-core / per-user / per-database licensing, largely negotiated rather than list-priced; ISVs commonly resell under percent-of-sale or bundled agreements ([pricing discussion, ProgressTalk](https://www.progresstalk.com/threads/license-costs.78986/)). ⚠️ unverified — no reliable current public price list; costs are quote-driven.

## Hardware / deployment
- **Resource profile:** disk- and memory-sensitive OLTP server; performance is dominated by the database buffer pool (-B) sizing relative to working set — the working set need not fully fit in RAM but should be well-cached. Lock table (-L) and BI/AI buffers are key tunables.
- **Storage assumptions:** local or SAN/block storage; benefits from fast (NVMe/SSD) storage for BI/AI write paths. Network-attached latency on the recovery log path hurts.
- **Footprint:** single-node server (with optional replication targets); not embedded, not serverless.
- **Deployment:** on-prem traditionally; AWS/cloud deployment via Progress-provided templates; container/k8s support exists but it is a stateful monolithic DB, not a cloud-native distributed system.

## Bottom line
Reach for OpenEdge only if you run or build on an ABL/Progress application (above all QAD or a vendor ERP) — there the integrated 4GL-plus-RDBMS is genuinely productive and battle-tested for OLTP. Do not pick it greenfield as a standalone database: it is proprietary, single-primary, vertically scaled, with a niche talent pool and high lock-in. The single biggest gotcha is concurrency by convention — ABL code defaults to SHARE-LOCK and is routinely written with NO-LOCK (effectively read-uncommitted), so consistency depends on disciplined lock scoping rather than an engine-enforced isolation guarantee.

## Sources
- [Progress: OpenEdge ABL feature page](https://www.progress.com/openedge/features/abl)
- [Wikipedia: OpenEdge Advanced Business Language](https://en.wikipedia.org/wiki/OpenEdge_Advanced_Business_Language)
- [Progress: Record locking in ABL](https://documentation.progress.com/output/ua/OpenEdge_latest/gsabl/record-locking-in-abl.html)
- [Progress: Setting isolation levels (OpenEdge SQL)](https://docs.progress.com/bundle/openedge-sql-development/page/Setting-isolation-levels.html)
- [Progress: Working with locking behavior and isolation levels](https://documentation.progress.com/output/ua/OpenEdge_latest/dmsdv/working-with-locking-behavior-and-isolation-leve.html)
- [Progress: Introduction to recovery mechanisms (BI/AI, WAL, 2PC)](https://docs.progress.com/bundle/openedge-database-management/page/Introduction-to-recovery-mechanisms.html)
- [Progress: OpenEdge replication options](https://docs.progress.com/bundle/openedge-database-replication-quickstart/page/OpenEdge-replication-options.html)
- [Progress: How OpenEdge Replication works with a replication set](https://documentation.progress.com/output/ua/OpenEdge_latest/ffr/how-openedge-replication-works-with-a-replicatio.html)
- [Progress OpenEdge End User License Agreement](https://www.progress.com/legal/license-agreements/openedge)
