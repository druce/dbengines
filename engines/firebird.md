---
name: Firebird
slug: firebird
rank: 34
data_model: Relational
license: IDPL + IPL (both MPL 1.1 variants) — file-level copyleft on the engine; proprietary apps can build/ship against it
summary: Lightweight open-source SQL RDBMS forked from Borland InterBase; multi-generational MVCC, tiny footprint, embeddable — but single-node and a niche ecosystem.
last_researched: 2026-06-04
confidence: high
---

# Firebird

> A small, mature, low-admin relational engine descended from InterBase, built around multi-generational MVCC; great as an embedded or single-server SQL store, but not a distributed system.

## When to use

**Use Firebird if:**
- ✅ You need a real multi-user SQL engine with transactions, stored procedures (PSQL), and near-zero administration that you can embed and ship inside an application
- ✅ You want a frugal single-server OLTP store that runs well on small hardware without the working set fitting in RAM
- ✅ You want full multi-user SQL with an embedded mode that overlaps [sqlite](sqlite.md)'s niche but adds concurrency and snapshot-isolation MVCC

**Avoid Firebird if:**
- ❌ You need horizontal scale, OLAP/columnar analytics, or multi-region HA with automatic consistent failover — core replication is uni-directional master→replica only
- ❌ You want a deep cloud/managed ecosystem and a large hiring pool — there is no first-party managed Firebird and the talent pool is small ([postgresql](postgresql.md) dominates there)
- ❌ You can't enforce transaction hygiene — long-running or abandoned transactions widen the OIT/OAT gap, bloat MGA version chains, and degrade performance; never disable forced writes on Windows

## Identity
- **Taxonomy / data model:** Relational (SQL). Single-model. ([db-engines](https://db-engines.com/en/system/Firebird), [Wikipedia](https://en.wikipedia.org/wiki/Firebird_(database_server)))
- **Storage model:** Row-store, B-tree indexes, page-based on-disk format (not [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM). Uses **Multi-Generational Architecture (MGA)** — older row versions are kept inline in the data pages rather than in a separate undo/rollback segment, which is its distinguishing design. See [mvcc](../concepts/mvcc.md).
- **Workload:** OLTP. Not an analytics engine; no columnar storage. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** N/A in the classic sense — Firebird is fundamentally a **single-node** engine. Built-in replication (since v4) is uni-directional master→replica logical replication, not a quorum/consensus cluster, so there is no automatic consistent failover in core Firebird. ([README.replication.md](https://github.com/FirebirdSQL/firebird/blob/master/doc/README.replication.md)) See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Effectively a single-node store; the latency-vs-consistency tradeoff appears only via async replication lag to replicas (replicas can serve stale reads).
- **Default isolation & what's achievable:** Default is **SNAPSHOT** (snapshot isolation — a transaction sees only data committed before it began). Also supports **READ COMMITTED** and **SNAPSHOT TABLE STABILITY** (most restrictive: blocks other transactions from modifying tables the transaction touches). ([dbdb.io](https://dbdb.io/db/firebird), [Firebird ACID paper](https://firebirdsql.org/file/documentation/papers_presentations/html/paper-fbent-acid.html)) Note: like most snapshot-isolation systems, the default is **snapshot isolation, not serializable** — write-skew anomalies are possible. There is no SSI-style serializable mode; SNAPSHOT TABLE STABILITY achieves serializability only by coarse table-level locking. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-leader logical (record-level) replication; **synchronous** (primary stays connected to replica, applied immediately) or **asynchronous** (journal files shipped, with replication lag). Physical/page-level replication is not built in. ([README.replication.md](https://github.com/FirebirdSQL/firebird/blob/master/doc/README.replication.md)) See [replication-models](../concepts/replication-models.md). HA/failover (synchronous 2-node, automatic failover) is provided by third parties (e.g. HQbird, Evidian), not core. ([Evidian](https://www.evidian.com/products/high-availability-software-for-application-clustering/firebird-high-availability-synchronous-replication-failover/))
- **Tunable consistency?** No Dynamo-style per-query consistency levels — it is not a quorum system.
- **Clock dependency:** No dependence on synchronized clocks for correctness (single-node MVCC keyed on internal transaction IDs). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schema-on-write, rigid relational schema with declared types, constraints, and referential integrity.
- **Migration/evolution:** DDL is transactional and runs inside transactions. ⚠️ unverified — historically some metadata changes to objects in active use can fail or require all dependent transactions to clear; Firebird is known for being touchy about online DDL on busy objects. Treat ALTER on live tables with caution.
- **Type system:** Standard SQL types, `NUMERIC`/`DECIMAL`, `DECFLOAT` (IEEE decimal floating point, added in v4), `BOOLEAN`, `BLOB` (text/binary subtypes), arrays, `TIMESTAMP WITH TIME ZONE` (v4), `INT128` (v4). No native JSON type (handled as text/BLOB), no native vector type, limited geospatial.

## Query interface
- **Language:** SQL, reasonably standards-oriented dialect; common-table expressions, recursive CTEs, window functions, `MERGE`, and (v5) `SKIP LOCKED` for queue-style workloads. ([Firebird 5.0 release notes](https://www.firebirdsql.org/file/documentation/release_notes/html/en/5_0/rlsnotes50.html))
- **Transactions:** Full multi-statement ACID. Durability via "forced writes" by default (see Performance).
- **Native vs app-side:** Native joins, aggregations, secondary indexes, window functions — full relational engine.
- **Stored procedures / UDFs:** **PSQL** (Firebird's procedural SQL) for stored procedures, triggers, and stored functions; packages (v3+); selectable (table-returning) procedures. Also has a built-in **event** mechanism (POST_EVENT) for server-to-client async notifications. External UDFs via UDR (user-defined routines) engine.

## Scaling & topology
- **Vertical vs horizontal:** Primarily **vertical** (scale up one node). No native auto-sharding or distributed query; horizontal scale must be done in the application layer.
- **Sharding:** None built in.
- **Read replicas:** Supported via logical replication; reads from async replicas can be stale (replication lag).
- **Storage/compute separation:** No. Classic monolithic engine; data and compute co-located. See [storage-compute-separation](../concepts/storage-compute-separation.md) (not applicable).

## Performance & durability
- **Write path:** **No write-ahead log.** Firebird uses a "careful write" / multi-generational scheme: it orders page writes so the on-disk database is always self-consistent, avoiding a separate WAL/redo log. See [wal-and-durability](../concepts/wal-and-durability.md) for the contrast. **Forced writes (synchronous fsync) is ON by default** — committed data is flushed before acknowledgment. ([Firebird Quick Start: Protecting your data](https://www.firebirdsql.org/manual/qsg2-safety.html))
- **Data-loss window:** With forced writes on, the window is minimal. ⚠️ Disabling forced writes ("async writes") dramatically widens the data-loss/corruption window on power loss — and on Windows the OS may not flush the cache until the service stops, so the docs explicitly warn against disabling it there. ([Firebird Quick Start: Protecting your data](https://www.firebirdsql.org/manual/qsg2-safety.html))
- **Throughput/latency:** Solid for small-to-mid OLTP on a single box; very low memory/footprint. ⚠️ unverified — no authoritative published p99 benchmarks found; tail behavior is dominated by garbage collection (below) and forced-write fsync cost.
- **Compaction / GC:** MGA means obsolete record versions accumulate inline and must be garbage-collected. GC happens cooperatively (during scans/queries) or via background threads, plus a periodic/triggered **sweep** to clear versions below the oldest interesting transaction (OIT/OAT). A growing **gap between oldest and newest transaction** (e.g. long-running transactions, or aborted transactions left uncommitted) bloats version chains and degrades performance — a classic Firebird operational gotcha analogous to Postgres vacuum/[mvcc](../concepts/mvcc.md) bloat.

## Operations & maturity
- **Backup/restore:** `gbak` logical backup/restore (also compacts the database and resets the MGA generation gap); `nbackup` for incremental physical backups and read-only standby. PITR is not a native turnkey feature (relies on nbackup + replication journals). ⚠️ unverified — no built-in continuous PITR like Postgres archive-WAL.
- **Observability:** Monitoring tables (`MON$*`), trace/audit API, `gstat` for database statistics (incl. the OIT/OAT gap), query plans via `SET PLAN`/optimizer output.
- **Upgrade story:** Major-version upgrades typically require backup/restore (gbak) of the on-disk format (ODS); no rolling upgrade for a single engine. Day-2 burden is low for small deployments but requires attention to the transaction gap and periodic sweeps.
- **Maturity:** Very mature — InterBase lineage dates to the 1980s; Firebird forked from InterBase 6.0 in 2000 and has been largely rewritten since v1.5. ([Wikipedia](https://en.wikipedia.org/wiki/Firebird_(database_server))) **No Jepsen report exists** (it is not a distributed consensus system, so it has not been a Jepsen target). Known failure modes: database corruption from disabling forced writes / abrupt OS crashes; performance collapse from a runaway OIT/OAT gap.

## Ecosystem & people
- **Canonical use cases:** Embedded/desktop applications, ISV-shipped software (the engine embeds with the app, zero-admin), small-to-medium business OLTP, point-of-sale, on-premise line-of-business apps. Strong in regions/verticals with legacy InterBase apps.
- **Anti-patterns:** Web-scale or horizontally distributed workloads; analytics/OLAP; multi-region HA needing automatic consistent failover; teams wanting a large hiring pool and rich cloud-managed offerings — there is no first-party managed cloud Firebird, and the talent pool is small. Reach for [postgresql](postgresql.md) for a similar feature set with a vastly larger ecosystem.
- **Drivers / connectors:** Native client + JDBC (Jaybird), .NET provider, ODBC, Python (fdb/firebird-driver), PHP, Delphi (its traditional stronghold). CDC/Kafka/dbt/BI integrations are thin compared to mainstream engines.
- **Community/support:** Active but niche community (Firebird Foundation); commercial support and tooling from third parties (IBPhoenix, IBSurgeon/HQbird, IBExpert). Docs are decent but scattered. Learning curve moderate; transaction-management discipline (commit promptly, watch the gap) is the main thing newcomers get wrong.

## Licensing & cost
- **OSS license:** Dual-licensed — the **Initial Developer's Public License (IDPL)** covers code written by the Firebird Project, and the **InterBase Public License (IPL)** covers code inherited from InterBase; both are variants of Mozilla Public License 1.1, differing from MPL only to reflect that Netscape did not author the original code. ([Firebird — Licensing](https://www.firebirdsql.org/en/licensing/), [The Firebird licenses](https://www.firebirdsql.org/pdfmanual/html/qsg25-firebird-licenses.html)) File-level copyleft on the engine source, but you can build and ship proprietary applications against it without open-sourcing your app. See [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 relicensing rug-pull — it has stayed open. Fully free, including embedded distribution.
- **Self-managed vs managed:** Self-managed only; no first-party SaaS. Third-party hosting exists but is rare.
- **Lock-in:** Low — open format, open client. Some PSQL/feature specifics are non-portable.
- **Cost model:** Free (the engine). Cost is operational/support; commercial value-add (HQbird etc.) is licensed per-server.

## Hardware / deployment
- **Resource profile:** Light; modest memory and CPU. Working set need not fit in RAM (page cache helps but it is disk-backed). One of its selling points is running well on small hardware.
- **Storage assumptions:** Local disk; benefits from fast storage for fsync (forced writes) but tolerates ordinary disks. No special NVMe requirement.
- **Footprint:** Available as **SuperServer** (multithreaded, shared cache), **SuperClassic** (multithreaded, per-connection cache), **Classic** (one process per connection), and **Embedded** (in-process library, zero-admin, single app) — the embedded mode is a key differentiator vs [postgresql](postgresql.md)/[mysql](mysql.md) and overlaps the niche of [sqlite](sqlite.md) but with full multi-user SQL. ([Wikipedia](https://en.wikipedia.org/wiki/Firebird_(database_server)))
- **Deployment:** On-prem / on-device. Container/k8s usable but not a focus; no managed StatefulSet ecosystem of note.

## Bottom line
Reach for Firebird when you need a real multi-user SQL engine with transactions, stored procedures, and a near-zero administration footprint that you can **embed and ship inside an application** or run on a single modest server — its InterBase heritage makes it stable and frugal. Do **not** reach for it for horizontal scale, OLAP, multi-region HA with automatic failover, or when you want a deep cloud/managed ecosystem and large hiring pool ([postgresql](postgresql.md) dominates there). The single biggest gotcha is transaction hygiene: long-running or abandoned transactions widen the oldest-active-transaction gap, bloat MGA version chains, and silently degrade performance until a sweep or gbak restore — and never disable forced writes on Windows.

## Sources
- [Wikipedia — Firebird (database server)](https://en.wikipedia.org/wiki/Firebird_(database_server))
- [Database of Databases — Firebird](https://dbdb.io/db/firebird)
- [Firebird — ACID Compliance and Firebird (official paper)](https://firebirdsql.org/file/documentation/papers_presentations/html/paper-fbent-acid.html)
- [Firebird Quick Start Guide — Protecting your data (forced writes)](https://www.firebirdsql.org/manual/qsg2-safety.html)
- [FirebirdSQL/firebird — README.replication.md](https://github.com/FirebirdSQL/firebird/blob/master/doc/README.replication.md)
- [Firebird 5.0.4 Release Notes](https://www.firebirdsql.org/file/documentation/release_notes/html/en/5_0/rlsnotes50.html)
- [Evidian — Firebird HA synchronous replication & failover](https://www.evidian.com/products/high-availability-software-for-application-clustering/firebird-high-availability-synchronous-replication-failover/)
- [db-engines — Firebird](https://db-engines.com/en/system/Firebird)
