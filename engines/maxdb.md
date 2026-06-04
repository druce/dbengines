---
name: MaxDB
slug: maxdb
rank: 134
data_model: Relational
license: Proprietary (SAP), source-available history; previously GPL as SAP DB
summary: SAP's legacy ANSI-SQL-92 RDBMS descended from Adabas D, kept alive mainly to host older SAP application stacks, now sunset in favor of HANA.
last_researched: 2026-06-04
confidence: medium
---

# MaxDB

> A mature single-leader relational engine that SAP shipped as the cheap DB option under its own apps; it works, but it is end-of-the-road software you only choose if SAP already chose it for you.

## Identity
- **Taxonomy / data model:** classic relational RDBMS, ANSI SQL-92 entry-level compliant ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)). Written in C++.
- **Storage model:** row-store (N-ary storage model / record-oriented per [dbdb.io](https://dbdb.io/db/maxdb)); on-disk data and indexes organized as B*-trees (see [lsm-vs-btree](../concepts/lsm-vs-btree.md) — it is firmly B-tree, not LSM). Pages live in "volumes"; a separate log volume holds the WAL.
- **Workload:** OLTP. Designed as the operational store under SAP business applications (ERP, BW, content server, liveCache base). Not an analytics/HTAP engine — no columnar store, no separate OLAP replica. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** N/A in the Dynamo sense — MaxDB is a single-node engine with optional hot-standby; it is effectively CP, refusing to lose committed data rather than staying available across a partition. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** essentially a single-node store; the distribution dimension is just standby failover, so PACELC framing barely applies (no quorum, no tunable A/C).
- **Default isolation & what's achievable:** MVCC was added in version 7.7 ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)); before that it was lock-based only. SQL isolation levels: 0 = read uncommitted (no shared locks), 1/10 = committed read, 15 = shared locks on all addressed tables, 2/20 = repeatable read, 3/30 = serializable ([SAP docs, Isolation Level](https://maxdb.sap.com/doc/7_7/44/c3758d865960efe10000000a155369/content.htm)). SAP also documents internal level numbers 50 (committed read, per-statement snapshot) and 60 (serializable, transaction-start snapshot) for the MVCC path ([SAP isolation training](https://maxdb.sap.com/training/internals_7.6/locking_EN_76.pdf)). ⚠️ unverified — the exact factory-default isolation level is not stated in the docs reviewed; in SAP NetWeaver deployments it is driver/app-configured (typically committed read). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** single-leader hot-standby ("standby database") fed via log shipping; failover is manual/scripted, not automatic consensus. No multi-leader and no leaderless quorum. See [replication-models](../concepts/replication-models.md). ⚠️ unverified — split-brain protection relies on operator procedure, not a built-in fencing/consensus layer.
- **Tunable consistency?** Only via standard SQL isolation levels per session; no Dynamo-style per-query consistency knobs.
- **Clock dependency:** none for correctness — no TrueTime/HLC scheme. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; tables, columns, constraints defined up front.
- **Migration/evolution:** DDL via SQL (`ALTER TABLE`). ⚠️ unverified — online/non-locking DDL guarantees not confirmed; treat schema changes as potentially blocking.
- **Type system:** standard SQL-92 types — numeric, char/varchar, date/time, plus LONG/BLOB-style large objects. No native JSON, vector, or rich geospatial types (it predates those expectations).

## Query interface
- **Language:** SQL (ANSI SQL-92 entry level) ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)). Also exposes loader/admin tooling (`dbmcli`, Loader, SQL Studio / Database Studio).
- **Transactions:** full multi-statement ACID with COMMIT/ROLLBACK.
- **Native vs app-side:** native secondary indexes, joins, aggregations, views. Server-side stored procedures and triggers supported via MaxDB's SQL procedural dialect (DB Procedures); ⚠️ unverified — window-function / advanced-analytic SQL coverage is limited compared to modern engines.
- **Drivers:** JDBC, ODBC, and bindings for PHP, Python, Perl, .NET ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)); SQLDBC native interface.

## Scaling & topology
- **Vertical, not horizontal:** scales by bigger boxes and more volumes; no built-in sharding or distributed query. Resharding pain is N/A because there is no native sharding to begin with.
- **Read replicas:** the standby is for failover, not a fan-out read pool; MaxDB is not designed as a read-replica scale-out database.
- **Storage/compute separation:** none — local volumes, shared-everything single node ([dbdb.io](https://dbdb.io/db/maxdb)). See [storage-compute-separation](../concepts/storage-compute-separation.md) (it does not do this).

## Performance & durability
- **Write path:** write-ahead log to a dedicated log volume; commit forces the redo log, giving standard crash recovery with a small data-loss window bounded by log-flush policy. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact group-commit / async-log defaults not confirmed from primary docs.
- **Throughput/latency:** adequate for mid-size SAP OLTP workloads; no published modern benchmarks of note. ⚠️ unverified — p99 / tail-latency characterizations are not documented in sources reviewed.
- **GC/compaction:** B*-tree engine, so no LSM-style background compaction; space reclamation is via normal page/garbage handling and the MVCC version cleanup introduced with 7.7. There is no Postgres-style vacuum-bloat problem of the same shape.

## Operations & maturity
- **Backup/restore:** built-in backup including online/hot backup and incremental/log backups; point-in-time recovery via log replay is supported (a long-standing MaxDB strength) ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)).
- **Observability:** admin tooling (Database Manager / `dbmcli`, Database Studio), SQL EXPLAIN for plans, and SAP DBA Cockpit integration when used under NetWeaver.
- **Upgrade story:** version upgrades are operator-driven with downtime; rolling upgrade is not a feature. Day-2 burden is "old but stable" — well-trodden but a shrinking knowledge pool.
- **Maturity:** decades in production under SAP installs; very stable for what it is. **No Jepsen report exists.** ⚠️ unverified — no formal/independent distributed-consistency verification is published. The dominant risk is product status: SAP has stated there will be no major/minor releases after 7.9, steering customers to HANA ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)); 7.9 maintenance currently runs through end of 2027 per SAP's lifecycle notes ([SAP MaxDB Version Information](https://help.sap.com/docs/SUPPORT_CONTENT/maxdb/3362173683.html)).

## Ecosystem & people
- **Canonical use cases:** the database tier under classic SAP NetWeaver / ABAP application stacks, SAP Content Server, and as the base store for SAP liveCache. Picked historically because it was bundled/low-cost with SAP.
- **Anti-patterns:** any greenfield project; analytics/OLAP; horizontal scale-out; anything needing JSON/vector/geospatial/modern SQL; any workload where you want a vibrant community and long-term roadmap. Do not start here in 2026.
- **Community & support:** small, SAP-centric, aging. Commercial support is via SAP (and only meaningful when run under SAP applications). Docs exist but are dated; learning curve is manageable for a DBA but talent is scarce.
- **Connectors:** standard JDBC/ODBC reach for BI and dbt-style tooling; ⚠️ unverified — no notable native CDC/Kafka connector ecosystem.

## Licensing & cost
- **License history:** released as **SAP DB under the GPL** in October 2000; versions 7.2–7.6 were GPL, 7.5 added dual licensing, and from October 2007 MaxDB 7.6 went **closed source / proprietary**, free-of-charge but with usage restrictions for non-SAP use ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)). This is a copyleft → source-available/proprietary trajectory, the reverse of the usual modern relicensing story. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed:** runs on-prem / self-managed; no first-class managed cloud service.
- **Lock-in / cost:** licensing and real-world support are tied to SAP — the lock-in is the SAP application above it more than the DB itself. No per-core/per-GB cloud meter; cost is bundled into the SAP relationship.

## Hardware / deployment
- **Resource profile:** conventional disk-backed RDBMS with a data cache; working set does not need to fit entirely in RAM (unlike HANA). Memory helps cache hit rates; it is disk- and cache-bound, not in-memory-mandatory.
- **Storage assumptions:** local block volumes (data + log); fine on NVMe/SSD, originally built for spinning disk. Not designed around network-attached storage-compute separation.
- **Footprint:** single-node server with optional standby. Not embedded, not serverless, not natively clustered.
- **Deployment:** on-prem / VM; cross-platform — AIX, HP-UX, Linux, Solaris, Windows ([Wikipedia](https://en.wikipedia.org/wiki/MaxDB)). No official k8s/StatefulSet story.

## Bottom line
Reach for MaxDB only if you are operating an existing SAP system that already runs on it; it is a stable, ACID, hot-backup-capable OLTP database that does its narrow job well. Everyone else should pick a living engine ([postgresql](postgresql.md) for general OLTP, or [sap-hana](sap-hana.md) if you are staying in the SAP world). The single biggest gotcha: it is **end-of-life by SAP's own statement** (no releases past 7.9, HANA is the successor), so any new bet on it is a bet on managed decline.

## Sources
- [MaxDB — Wikipedia](https://en.wikipedia.org/wiki/MaxDB)
- [Database of Databases — MaxDB (dbdb.io)](https://dbdb.io/db/maxdb)
- [SAP MaxDB docs — Isolation Level (7.7)](https://maxdb.sap.com/doc/7_7/44/c3758d865960efe10000000a155369/content.htm)
- [SAP MaxDB internals — Locking / isolation training (7.6)](https://maxdb.sap.com/training/internals_7.6/locking_EN_76.pdf)
- [SAP MaxDB project home](https://maxdb.sap.com/)
