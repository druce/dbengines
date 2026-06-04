---
name: FileMaker
slug: filemaker
rank: 24
data_model: Relational
license: Proprietary commercial (closed-source)
summary: Apple/Claris low-code RAD platform with a bundled relational engine; you buy the app-builder, not a standalone DBMS.
last_researched: 2026-06-04
confidence: medium
---

# FileMaker

> A proprietary low-code application platform (UI + scripting + bundled relational engine) for small workgroup apps — not a standalone database you'd put behind a high-throughput service.

## Identity
- **Taxonomy / data model:** Relational. The product is really a RAD/low-code platform (forms-and-scripts "layouts") with an integrated database engine, GUI, and security model — not a SQL server you connect to with arbitrary clients ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)). Now branded "Claris FileMaker" / "FileMaker 2025"; developed by Claris International, an Apple subsidiary ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)).
- **Storage model:** Single-file proprietary format `.fmp12` (current since FileMaker Pro 12, 2012); each file holds multiple tables, layouts, scripts, and value lists ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)). On-disk format is closed and undocumented; ⚠️ unverified — internal page structure (B-tree vs other) is not publicly documented. Containers can hold up to 4 GB binary / 2 GB text per field ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)).
- **Workload:** OLTP-style interactive business apps (CRM, inventory, project tracking) for small workgroups. Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). A defining quirk: much transaction/query processing happens **on the client**, not the server — records are fetched to the client, edited, then committed back ([ScaleFM](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)).

## Distribution & consistency
- **Topology:** Effectively single-server. FileMaker Server hosts files; clients (FileMaker Pro, Go, WebDirect) connect to one server. There is no built-in multi-node clustering, sharding, or quorum replication. So [cap-pacelc](../concepts/cap-pacelc.md) is largely **N/A — single-server**; availability is bounded by that one host.
- **Default isolation & what's achievable:** Isolation via **pessimistic record-level locking** — once a user opens a record for edit, it is locked and other users/scripts get an error they must handle ([Tim Dietrich](https://timdietrich.me/blog/filemaker-multi-user-record-locking/), [ScaleFM](https://scalefm.com/2016/06/acid-does-filemaker-support-isolation-part4/)). This is closer to lock-based serialization on touched records than MVCC snapshot isolation (contrast [mvcc](../concepts/mvcc.md) / [isolation-levels](../concepts/isolation-levels.md)). FileMaker does **not** advertise standard SQL isolation levels.
- **Transactions / ACID — the divergence:** FileMaker is often described as "ACID-capable," but that is conditional. Atomicity and consistency are achievable only through a deliberate **scripted "transaction" pattern** (edit related records via the relationship graph, then `Commit Records` or `Revert Record`) — there is no `BEGIN/COMMIT` SQL transaction primitive ([ScaleFM atomicity](https://scalefm.com/2016/06/acid-is-filemaker-atomic-part2/), [ScaleFM summary](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)). Durability is the weak link: the server caches writes in RAM, and an abrupt crash can lose unsaved data — recovery exists but does **not** guarantee atomicity/consistency of the recovered file ([ScaleFM summary](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Replication / tunable consistency / clocks:** No native replication, no tunable consistency, no clock-dependency story (single server). See [replication-models](../concepts/replication-models.md), [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Rigid relational schema defined in a GUI (tables, fields, relationship graph). Field-level validation and stored/unstored calculated fields enforce consistency ([ScaleFM](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)).
- **Migration/evolution:** Schema changes are made interactively; ⚠️ unverified — locking behavior of schema changes under heavy concurrent load is not well documented. Deploying schema changes to production typically uses the Data Migration Tool to move data from old file to new.
- **Type system:** text, number, date, time, timestamp, container (BLOB: images/files), and calculation/summary fields. Container fields up to 4 GB binary / 2 GB text ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)). No native JSON column type, but JSON parsing/building functions exist; no native vector or rich geospatial type.

## Query interface
- **Primary interface is the GUI/script layer**, not SQL. Apps are built from layouts, the relationship graph, and a proprietary scripting language with a large function library and a step debugger (in advanced/Pro) ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)).
- **SQL:** Read-only via the `ExecuteSQL()` function (SELECT only — no INSERT/UPDATE/DELETE, no DDL) ([Claris SQL Reference](https://help.claris.com/en/sql-reference/content/index.html)). External ODBC/JDBC clients can also query/modify hosted files via FileMaker's SQL interface, but FileMaker SQL is a limited dialect.
- **Transactions:** No multi-statement SQL transactions; atomicity is the scripted commit/revert pattern described above (single-record atomicity is automatic; multi-record atomicity must be engineered).
- **Native vs app-side:** Joins/relationships are native via the relationship graph; aggregations via summary fields and `ExecuteSQL`. "Stored procedures" are FileMaker scripts (proprietary language); also supports plug-ins (C/C++) and server-side scripting.
- **ESS (External SQL Sources):** Since v9, FileMaker can mount MySQL, SQL Server, Oracle, PostgreSQL, DB2 tables into its relationship graph via ODBC and CRUD them through layouts — using the external DB as the real store ([DB Services](https://dbservices.com/blog/integrating-claris-filemaker-with-sql-database-via-ess), [Claris ESS overview](https://support.claris.com/s/article/Accessing-External-SQL-Data-Sources-ESS-Overview-and-Troubleshooting-1503693056607?language=en_US)).

## Scaling & topology
- **Vertical only.** Scale by giving the single FileMaker Server more CPU/RAM/fast storage. No sharding, no horizontal scale-out, no read replicas.
- **Concurrency limits:** WebDirect (browser client) is documented to scale up to 500 concurrent connections — but only across a multi-machine deployment (roughly 100 per machine, so ~5 well-provisioned worker machines for the 500 ceiling); a single server machine supports ~100 ([Claris: Maximum number of connections](https://help.claris.com/en/webdirect-guide/content/maximum-number-of-connections.html)); ⚠️ unverified — practical concurrent-user ceilings for FileMaker Pro/Go clients depend heavily on schema design and are not a single published number. Heavy concurrent editing surfaces record-locking conflicts that developers must handle ([Tim Dietrich](https://timdietrich.me/blog/filemaker-multi-user-record-locking/)).
- **Storage/compute separation:** None — monolithic single-server. See [storage-compute-separation](../concepts/storage-compute-separation.md) (not applicable here).

## Performance & durability
- **Write path:** Writes are cached in server RAM and flushed to the `.fmp12` file; the RAM cache setting and storage speed (SSD vs HDD) directly govern the **data-loss window** on an abrupt crash ([ScaleFM summary](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)). ⚠️ unverified — FileMaker does not document a classic write-ahead log; durability relies on cache flush + scheduled backups rather than WAL replay. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Tuned for interactive single-user-per-record latency, not high write throughput. The client-side processing model means slow networks and unstored calculations dominate perceived performance. No published p99 benchmarks; ⚠️ unverified — tail-latency profile under concurrency is undocumented and design-dependent.
- **Compaction/GC:** Files accumulate bloat over time; the remedy is periodic "Save a Copy as Compacted" / file recovery, an offline-ish operation — there is no online vacuum like Postgres.

## Operations & maturity
- **Backup/restore:** FileMaker Server provides scheduled live backups and progressive backups; recovery tool repairs damaged files but does **not** guarantee a consistent/atomic result ([ScaleFM summary](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)). No true point-in-time replay (PITR) like log-shipping RDBMSs; ⚠️ unverified — PITR granularity is limited to backup snapshots.
- **Observability:** Admin Console with stats, server logs, and the Script Debugger / Data Viewer in FileMaker Pro Advanced. No SQL `EXPLAIN`-style query planner exposure.
- **Upgrade story:** Server upgrades generally require downtime; client and server versions are coupled. Day-2 burden centers on backup management, file maintenance/compaction, and handling lock conflicts in scripts.
- **Maturity:** Very mature product (shipping since 1985; current "FileMaker 2025" / v22, released July 2025, with point releases through 22.0.x in late 2025) ([Claris FileMaker Pro Release Notes](https://help.claris.com/en/pro-release-notes/content/index.html), [Wikipedia](https://en.wikipedia.org/wiki/FileMaker)). No public **Jepsen** report exists — and it would be largely inapplicable given the single-server, non-distributed design. Known failure modes: crash-time data loss from RAM cache, file corruption requiring recovery, and lock-conflict bugs from naive scripting.

## Ecosystem & people
- **Canonical use cases:** Departmental/SMB line-of-business apps built fast by non-specialist "citizen developers" — CRM, inventory, scheduling, custom workflow apps, especially in Apple/iOS shops (FileMaker Go on iPad/iPhone is a strong differentiator).
- **Anti-patterns:** Public-facing high-traffic web apps; analytics/data-warehouse workloads; systems needing horizontal scale, geo-replication, strong distributed consistency, or thousands of concurrent writers. If you need a real SQL backend, use [postgresql](postgresql.md) or [mysql](mysql.md) (and FileMaker can front them via ESS).
- **Connectors:** ODBC/JDBC, the Data API (REST) and OData (newer versions), the relationship-graph ESS to external SQL DBs, and a C/C++ plug-in API. Integrations with BI/CDC/Kafka/dbt are uncommon and typically go through ODBC or the Data API rather than native connectors.
- **Community & docs:** Active developer/partner community (Claris Marketplace, consultants) and decent official docs, but a smaller, more specialized talent pool than mainstream SQL ecosystems. Learning curve is low for building simple apps, higher for robust transactional/scripted patterns.

## Licensing & cost
- **License:** Proprietary, closed-source commercial software ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)). No OSS edition; see [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 relicensing relevant (it was never open source).
- **Managed vs self-managed:** Both — self-host FileMaker Server (macOS/Windows/Ubuntu) or use **FileMaker Cloud** (SaaS on AWS) ([Wikipedia](https://en.wikipedia.org/wiki/FileMaker)).
- **Lock-in:** High. Apps are deeply tied to the proprietary `.fmp12` format, scripting language, and layout engine; migrating off FileMaker is a rewrite, not a data export.
- **Cost model:** Per-user subscription licensing (Claris user-connection / annual subscription), not per-core or per-GB. Costs scale with named/concurrent users; ⚠️ unverified — exact current per-user pricing tiers; verify on the Claris site.

## Hardware / deployment
- **Resource profile:** Memory- and storage-latency-sensitive on the server (RAM cache governs durability window and throughput); CPU matters for WebDirect and server-side scripting. Working set need not fully fit in RAM, but more cache improves performance.
- **Storage assumptions:** Local/fast storage strongly preferred (SSD reduces the crash data-loss window) ([ScaleFM summary](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)); network-attached storage for live files is discouraged.
- **Footprint:** Single-server (FileMaker Server) plus thick clients (Pro, Go) or browser (WebDirect). Not embedded, not clustered, not serverless.
- **Deployment:** Self-managed FileMaker Server on macOS, Windows Server, or Linux (Ubuntu LTS) — ⚠️ unverified — exact supported Ubuntu LTS versions for FileMaker 2025; verify on the Claris OS-requirements page — or Claris-managed Cloud on AWS. Not designed for k8s/StatefulSet-style orchestration ([Claris: FileMaker Server OS requirements](https://support.claris.com/s/article/FileMaker-Server-operating-system-requirements-all-versions-1503692927810?language=en_US)).

## Bottom line
Reach for FileMaker when a small team — especially an Apple/iOS shop — needs a custom business app built and shipped fast by people who aren't database engineers; its bundled UI + scripting + engine is the whole point. Do **not** reach for it as a general-purpose, high-concurrency, or distributed database, or to back a public web service at scale. The single biggest gotcha: "ACID" is conditional — durability hinges on a RAM cache and backups (an abrupt crash can lose recent writes), and multi-record atomicity only exists if you deliberately script the commit/revert transaction pattern.

## Sources
- [FileMaker — Wikipedia](https://en.wikipedia.org/wiki/FileMaker)
- [ScaleFM: ACID Summary and Best Practices (Part 6)](https://scalefm.com/2016/07/acid-summary-and-best-practices-part6/)
- [ScaleFM: Is FileMaker Atomic? (Part 2)](https://scalefm.com/2016/06/acid-is-filemaker-atomic-part2/)
- [ScaleFM: Does FileMaker Support Isolation? (Part 4)](https://scalefm.com/2016/06/acid-does-filemaker-support-isolation-part4/)
- [Tim Dietrich: Multi-User Record Locking in FileMaker](https://timdietrich.me/blog/filemaker-multi-user-record-locking/)
- [Claris: ExecuteSQL / SQL Reference](https://help.claris.com/en/sql-reference/content/index.html) (ExecuteSQL supports SELECT only; ODBC/JDBC drivers support full DML/DDL)
- [Claris: FileMaker Pro Release Notes](https://help.claris.com/en/pro-release-notes/content/index.html)
- [Claris: WebDirect maximum number of connections](https://help.claris.com/en/webdirect-guide/content/maximum-number-of-connections.html)
- [Claris: FileMaker Server operating-system requirements (all versions)](https://support.claris.com/s/article/FileMaker-Server-operating-system-requirements-all-versions-1503692927810?language=en_US)
- [Claris: External SQL Data Sources (ESS) Overview & Troubleshooting](https://support.claris.com/s/article/Accessing-External-SQL-Data-Sources-ESS-Overview-and-Troubleshooting-1503693056607?language=en_US)
- [DB Services: Integrating Claris FileMaker with a SQL Database via ESS](https://dbservices.com/blog/integrating-claris-filemaker-with-sql-database-via-ess)
