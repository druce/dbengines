---
name: SAP SQL Anywhere
slug: sap-sql-anywhere
rank: 85
data_model: Relational (embedded)
license: Proprietary / commercial (closed-source); free developer/dev-use licensing
summary: Self-managing embeddable relational engine built for occasionally-connected and edge/mobile deployments, with mature store-and-forward and MobiLink sync.
last_researched: 2026-06-04
confidence: high
---

# SAP SQL Anywhere

> A low-administration, embeddable SQL engine whose real differentiator is data synchronization (MobiLink, SQL Remote, UltraLite) for thousands of edge/mobile databases feeding a central consolidated store — not raw single-node performance.

## Identity
- **Taxonomy / data model:** relational (SQL), single-file embedded/server RDBMS. Lineage: Watcom SQL (1992) → SQL Anywhere → Adaptive Server Anywhere → SQL Anywhere again (v10, 2006); acquired by Sybase, then SAP ([SQL Anywhere history](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-history.html), [Wikipedia](https://en.wikipedia.org/wiki/SQL_Anywhere)). Versions 13–15 skipped; current major release is **v17** (GA July 2015), still actively patched via Support Packages (17.0 SP1 builds through 2025) and supported until 2028 ([SQL Anywhere release/update history](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-release-history.html)).
- **Storage model:** row-store B-tree pages in a single database file plus a separate transaction log; classic page-based engine (not [LSM](../concepts/lsm-vs-btree.md)). It is **OLTP-oriented**; it does *not* market itself as a columnar/HTAP analytics engine, so treat any analytics use as secondary. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Workload:** OLTP for embedded apps, point-of-sale, field/mobile devices, and small-to-mid server deployments. Designed to run "zero-admin" inside an application. ⚠️ unverified — claims of an in-memory/columnar accelerator do not appear in current docs; older "in-memory mode" refers to a no-disk-write runtime option, not a column store.

## Distribution & consistency
- **CAP under partition:** Not a distributed quorum system. Core is a **single primary** node; HA is via **database mirroring** (primary + mirror + arbiter), which is CP-leaning — failover promotes the mirror, the primary processes all writes ([database mirroring docs](http://dcx.sap.com/sa160/en/dbadmin/ha-mobilink.html)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Effectively single-node semantics; under mirroring the latency-vs-consistency tradeoff is explicitly tunable via the mirror **synchronization mode** — `synchronous` (committed transactions guaranteed on the mirror, no data loss on automatic failover, at the cost of commit latency), `asynchronous`, or `asyncfullpage` (lower latency but committed transactions may be lost and, by default, the mirror will *not* auto-take ownership on failure) ([database mirroring modes](http://dcx.sap.com/sa160/en/dbadmin/mirroring-roleswitch.html)). So: PC/EL under async modes, PC/EC under synchronous mode.
- **Default isolation & what's achievable:** Default isolation level is **0 = READ UNCOMMITTED** for native/ODBC connections, but **1 = READ COMMITTED** for jConnect/JDBC/Open Client/TDS connections ([isolation levels docs](https://dcx.sap.com/1200/en/dbusage/udtchan.html)). Lock-based levels 0–3 (0 read-uncommitted, 1 read-committed, 2 repeatable-read, 3 serializable) plus **snapshot isolation** (statement-snapshot and transaction-snapshot) once explicitly enabled per database ([isolation and consistency](https://dcx.sap.com/1201/en/dbusage/udtisol.html), [snapshot isolation blog](https://blogs.sap.com/2014/03/19/why-snapshot-isolation-is-so-useful/)). The level-0 default means out-of-the-box reads can see uncommitted data — a notable gotcha. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Two distinct stories. (1) **HA mirroring** for failover (single-leader). (2) **Data sync**: MobiLink (session-based, scalable hub-and-spoke to a consolidated DB) and SQL Remote (store-and-forward via files/messages) — both are **asynchronous, eventually-consistent** replication for occasionally-connected clients, not synchronous clustering. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Per-connection/per-transaction isolation level can be changed mid-transaction ([changing isolation](https://dcx.sap.com/1201/en/dbusage/changing-understanding-transact.html)); no Dynamo-style per-query quorum levels.
- **Clock dependency:** No TrueTime/HLC dependency for correctness; conflict resolution in sync is logical/user-defined. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; standard DDL.
- **Migration/evolution:** standard `ALTER TABLE`; ⚠️ unverified — extent of online/non-locking DDL not confirmed.
- **Type system:** standard SQL types plus **spatial/geospatial** data, **full-text search** indexes, and UUIDs; JSON support is limited compared to document stores. No native vector type confirmed.

## Query interface
- **Language:** SQL. Supports both its **Watcom-SQL** procedural dialect and **Transact-SQL (T-SQL)** compatibility (Sybase ASE heritage) ([Wikipedia](https://en.wikipedia.org/wiki/SQL_Anywhere)). Interfaces: ODBC, JDBC, ADO.NET, OLE DB, embedded SQL, plus an HTTP/OData server option.
- **Transactions:** full multi-statement ACID with commit/rollback and savepoints.
- **Native vs app-side:** native secondary indexes, joins, aggregations, window functions, views, triggers, referential integrity, row-level locking.
- **Stored procedures / UDFs:** in Watcom-SQL, T-SQL, **Java**, and **C/C++** external procedures.

## Scaling & topology
- **Vertical vs horizontal:** primarily **vertical** (scale-up single node). Horizontal "scale" is achieved by **distributing many embedded databases** and synchronizing them to a consolidated server via MobiLink — a fan-in topology, not transparent sharding.
- **Sharding:** no automatic sharding/resharding; partitioning is application/sync-design driven.
- **Read replicas:** yes — the mirror server can be accessed via read-only connections, and the **read-only scale-out** feature adds a tree of read-only **copy nodes** (which receive transaction-log pages from the root and can never become primary) to offload reporting ([read-only scale-out](https://dcx.sap.com/sa160/en/dbadmin/da-copy-nodes.html)). Reads on copy nodes track applied log pages, so they can lag (eventually consistent), not guaranteed current. MobiLink/SQL Remote sync remotes are stale by design.
- **Storage/compute separation:** No — local-file engine. See [storage-compute-separation](../concepts/storage-compute-separation.md) (not applicable).

## Performance & durability
- **Write path:** WAL-style **transaction log** separate from the database file; checkpointing flushes pages. Data-loss window on crash depends on log/fsync configuration and recovery from the log. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact default fsync/group-commit behavior and crash data-loss window not confirmed from primary docs.
- **Throughput/latency:** tuned for low footprint and self-tuning query optimization; strong on small-to-mid OLTP. ⚠️ unverified — no public p99 benchmarks reviewed; treat performance claims as vendor-stated.
- **Compaction / GC:** page-based engine; snapshot isolation retains old row versions, which consumes space/temp until older transactions complete (standard [mvcc](../concepts/mvcc.md) cost). No LSM compaction.

## Operations & maturity
- **Backup/restore, PITR:** online backups and log-based recovery; PITR via transaction log replay. ⚠️ unverified — exact PITR tooling specifics.
- **Observability:** query plans/optimizer diagnostics, procedure profiling, MobiLink server logs and sync log viewer.
- **Upgrade story:** in-place database file/format upgrades between major versions; embedded deployments upgrade with the host app. Day-2 burden is deliberately low ("self-managing," minimal DBA).
- **Maturity:** 30+ year lineage (Watcom → Sybase → SAP), production-proven in retail/POS, field service, and embedded OEM. **No public Jepsen report exists** for SQL Anywhere (as of research date); distributed-correctness claims are therefore not independently verified.

## Ecosystem & people
- **Canonical use cases:** embedded/OEM database shipped inside applications; point-of-sale and retail; field/mobile data capture that must work offline and sync later; thousands of remote databases consolidating to a central store.
- **Anti-patterns:** large-scale analytics/data-warehousing (use a columnar engine); cloud-native horizontally-sharded OLTP at internet scale; teams wanting open-source or a large hiring pool — the skill base and community have **shrunk** under SAP, and mindshare is low (rank ~85). Default READ UNCOMMITTED isolation is a footgun for the unaware.
- **Drivers/connectors:** ODBC/JDBC/ADO.NET/OLE DB, OData/HTTP, MobiLink to consolidated DBs (Oracle, SQL Server, ASE, etc.), UltraLite client for phones/devices. CDC/Kafka/dbt/BI integration is weak relative to mainstream engines.
- **Docs quality:** thorough official docs (dcx.sap.com / SAP Help), though some live on legacy Sybase infocenter hosts. Learning curve moderate; small team sizes typical for embedded deployments.

## Licensing & cost
- **License:** **proprietary / closed-source commercial** (not OSS — none of permissive/copyleft/source-available applies). Free developer-use editions exist. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Editions:** **Edge** (entry; per-named-user or per-core at 4/8 cores) and **Advanced** (adds HA mirroring, more OSes, production tools) ([editions & licensing](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-licensing.html), [SAP community](https://community.sap.com/t5/technology-q-a/sap-sql-anywhere-17-editions-and-licensing/qaq-p/13620114)).
- **Cost model:** per-core (sold in multiples of 4; SAP moved from per-CPU to per-core licensing in 2016) or per-named-user/per-device. Self-managed (no first-party SaaS). Lock-in via T-SQL/Watcom-SQL procedures and MobiLink/UltraLite sync stack. ⚠️ unverified — current list pricing not published openly.

## Hardware / deployment
- **Resource profile:** lightweight; **does not require the working set to fit in RAM** — designed to run on modest hardware, including embedded/edge devices. Disk-and-memory balanced.
- **Storage assumptions:** ordinary local disk; no NVMe/network-storage assumptions; single database file is portable across platforms without conversion.
- **Footprint:** **embedded** (in-process) or client/server; UltraLite variant for phones/IoT. Small install size. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) for workload fit.
- **Deployment:** on-prem / on-device / OEM-embedded. Runs on Windows, Linux, macOS, and several Unix variants. Not a cloud-managed service; k8s/StatefulSet use is uncommon for this engine.

## Bottom line
Reach for SAP SQL Anywhere when you need a zero-admin, embeddable SQL database that ships inside an application or onto offline/edge devices and must **synchronize** reliably with a central database — that sync stack (MobiLink/SQL Remote/UltraLite) is its genuine edge. Do not reach for it for analytics, internet-scale sharded OLTP, or anything where you want open-source, cloud-native operation, or a large talent pool; mindshare is declining. The single biggest gotcha: the **default isolation level is READ UNCOMMITTED (0)** for native connections, so enable snapshot isolation or raise the level before assuming clean reads.

## Sources
- [Isolation levels and consistency (SAP DCX docs)](https://dcx.sap.com/1201/en/dbusage/udtisol.html)
- [Setting the isolation level (defaults: 0 native, 1 JDBC/TDS)](https://dcx.sap.com/1200/en/dbusage/udtchan.html)
- [Changing isolation levels within a transaction](https://dcx.sap.com/1201/en/dbusage/changing-understanding-transact.html)
- [Why snapshot isolation is so useful (SAP blog)](https://blogs.sap.com/2014/03/19/why-snapshot-isolation-is-so-useful/)
- [Database mirroring and MobiLink (HA docs)](http://dcx.sap.com/sa160/en/dbadmin/ha-mobilink.html)
- [Database mirroring modes / role switches (sync vs async data-loss behavior)](http://dcx.sap.com/sa160/en/dbadmin/mirroring-roleswitch.html)
- [Read-only scale-out and copy nodes](https://dcx.sap.com/sa160/en/dbadmin/da-copy-nodes.html)
- [SQL Anywhere release/update history](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-release-history.html)
- [SQL Anywhere editions and licensing](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-licensing.html)
- [SAP SQL Anywhere 17 editions and licensing (SAP Community)](https://community.sap.com/t5/technology-q-a/sap-sql-anywhere-17-editions-and-licensing/qaq-p/13620114)
- [SQL Anywhere history](https://www.sqlanywhere.info/EN/sql-anywhere/sql-anywhere-history.html)
- [SQL Anywhere (Wikipedia)](https://en.wikipedia.org/wiki/SQL_Anywhere)
