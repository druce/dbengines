---
name: Microsoft Access
slug: microsoft-access
rank: 17
data_model: Relational (desktop)
license: Proprietary (commercial; bundled with Microsoft 365 / Office)
summary: File-based desktop relational DB with a forms/reports RAD environment; great for single-user and small-workgroup apps, dangerous past a handful of concurrent writers.
last_researched: 2026-06-04
confidence: medium
---

# Microsoft Access

> A single-file desktop relational database plus a rapid forms/reports/macro app builder; the right tool for one user or a tiny LAN workgroup, and the wrong tool the moment you need real concurrency, durability, or scale.

## Identity
- **Taxonomy / data model:** relational. A complete Office application combining the **ACE database engine** (Access Connectivity Engine, successor to the older **Jet** engine since Access 2007) with a RAD layer of forms, reports, queries, macros, and VBA. The engine and the dev environment ship together; "Access" colloquially means both.
- **Storage model:** single-file, page-based **B-tree** ([lsm-vs-btree](../concepts/lsm-vs-btree.md)) row-store. The whole database — tables, indexes, queries, forms, reports, VBA — lives in **one `.accdb` file** (legacy `.mdb` for Jet). Page size is 4 KB for `.accdb` (2 KB for old `.mdb`).
- **Workload:** OLTP-flavored but at desktop scale; really a personal/departmental productivity DB, not a server. Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** N/A — not a distributed system. It is a file on a disk or network share, accessed in-process by each client. There is no server process, no cluster, no replication tier. (Jet "replication" existed historically as file-merge sync but was deprecated and removed in `.accdb`.)
- **PACELC:** N/A — single shared file, not a distributed engine. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** transactions exist via DAO `Workspace.BeginTrans` / `CommitTrans` / `Rollback`, providing atomic grouping ([Access Database Engine — Wikipedia](https://en.wikipedia.org/wiki/Access_Database_Engine)). Concurrency control is **pessimistic locking**, not [mvcc](../concepts/mvcc.md). Modern `.accdb` (Jet 4 / ACE) supports **record-level locking**; the older **page-level** model (pre-Jet-4 `.mdb`) is where one user's edit collaterally locks adjacent records sharing the same data page ([Access Database Engine — Wikipedia](https://en.wikipedia.org/wiki/Access_Database_Engine); [Jet locking — FMS](https://www.fmsinc.com/MicrosoftAccess/JetEngine/jet_locking.html)). Default form record-locking mode is "No Locks" (optimistic, last-write-wins with a write-conflict dialog); "Edited Record" (pessimistic) and "All Records" are options. There is **no serializable isolation guarantee** in the SQL-engine sense — see [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** none in modern `.accdb`. The supported multi-user pattern is a **split front-end/back-end**: each user runs a private copy of the FE (forms/queries/VBA) linked to one shared BE `.accdb` on a file share. See [replication-models](../concepts/replication-models.md) for what real replication looks like — Access has none of it.
- **Tunable consistency?** No.
- **Clock dependency:** none. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid. Tables have fixed typed columns defined up front.
- **Migration/evolution:** `ALTER TABLE` and the table designer work, but structural changes generally require **exclusive access** to the file; you cannot do online DDL while others are connected. Changes propagate to linked front-ends only on relink.
- **Type system:** Text/Long Text (Memo), Number, Currency, Date/Time, Yes/No, AutoNumber, OLE Object, Hyperlink, Attachment, and **multi-valued fields** (`.accdb` only) — the latter two are non-relational conveniences that break portability to real RDBMSs. No native JSON, no arrays-as-first-class, no vectors, limited geospatial. Max **255 fields per table** ([source](https://support.microsoft.com/en-us/access/access-specifications)).

## Query interface
- **Language:** a non-standard **Access SQL** dialect (executed by ACE/Jet), plus a visual Query-By-Example designer. Dialect quirks: `*`/`?` wildcards in some modes, `IIF`, `Nz`, `TRANSFORM ... PIVOT` crosstabs, no window functions, no CTEs, limited subquery support versus ANSI SQL.
- **Transactions:** multi-statement transactions via DAO/ADO at the engine level; UI-driven edits are generally autocommit per record. Atomic but not serializable.
- **Native vs app-side:** native joins, aggregations, secondary indexes, and crosstab queries. No stored procedures in the server sense; **VBA** and **macros** provide procedural logic, and saved queries act as parameterized views. UDFs = VBA functions callable from queries.
- **Pass-through:** can act as a front-end to [microsoft-sql-server](microsoft-sql-server.md), [postgresql](postgresql.md), etc. via ODBC linked tables / pass-through queries — the common "outgrow Access" upgrade path.

## Scaling & topology
- **Vertical only,** and barely. Hard limits: **2 GB max file size** (minus system-object overhead), **255 concurrent users** as the absolute ceiling, 32,768 objects per database ([source](https://support.microsoft.com/en-us/access/access-specifications)).
- **Practical concurrency is far below 255.** Vendor and field guidance: a well-designed split app can serve dozens of read-mostly users, but concurrent **writers** become unreliable past roughly 10–20, and many shops keep it under ~5–10 for write-heavy apps ([FMS](https://blog.fmsinc.com/microsoft-access-database-scalability-how-many-users-can-it-support/)). The 255 figure is a spec ceiling, not a real-world capacity — treat the marketing-adjacent "hundreds of users" claim as best-case read-only.
- **Sharding/partitioning:** none. **Read replicas:** none. **Storage/compute separation:** none — see [storage-compute-separation](../concepts/storage-compute-separation.md) for the opposite design.

## Performance & durability
- **Write path:** there is **no server-side WAL / redo log** ([wal-and-durability](../concepts/wal-and-durability.md)). The engine writes pages into the shared file and relies on a `.laccdb`/`.ldb` lock file for coordination. **Data-loss / corruption window:** if a client crashes, loses Wi-Fi/VPN, or the SMB connection drops **mid-write**, the file can be left in a partial state — this is the single most notorious Access failure mode ([Access Database Engine — Wikipedia](https://en.wikipedia.org/wiki/Access_Database_Engine)). Corruption risk rises sharply with multiple concurrent writers over a flaky network share.
- **Throughput/latency:** fine for one user on local NVMe. Over a network share, all index traversal and locking happen **client-side over the file protocol**, so latency and p99 degrade fast with contention and with WAN/VPN file access (a frequent corruption trigger). No server means no shared buffer pool across clients.
- **Compaction / GC:** deleted-row and churn space is **not auto-reclaimed**; the file bloats and must be periodically **Compact & Repair** (offline, exclusive). Bloat also degrades query-plan stats. This manual maintenance is a defining day-2 chore.

## Operations & maturity
- **Backup/restore:** copy the file while no one is in it. **No PITR, no incremental backup, no snapshots** in the DBMS sense. "Compact & Repair" is also the primary corruption-recovery tool; severe corruption often needs third-party recovery utilities.
- **Observability:** essentially none — no metrics, no slow-query log, no real query-plan tooling beyond the obscure **JET SHOWPLAN** registry trace. Debugging is via the VBA IDE.
- **Upgrade story:** new Access version = new client install; file formats are mostly forward-compatible, but VBA reference and ACE-version mismatches cause breakage. No rolling upgrades (no server).
- **Maturity:** extremely mature (since 1992) and battle-tested for what it is. **No Jepsen report exists or would be meaningful** — it is not a distributed/networked database. Known failure modes: file corruption under concurrent network writes, 2 GB ceiling hit, bloat, and "split-brain" of front-ends with stale linked schemas.

## Ecosystem & people
- **Canonical use cases:** single-user or small-team departmental apps, Excel-graduation databases, quick CRUD apps with forms/reports, and **front-ends to SQL Server/other RDBMSs** via ODBC. Excellent prototyping/RAD tool.
- **Anti-patterns:** web apps, public-facing apps, anything needing real concurrency, high write throughput, >2 GB data, strong durability, or 24/7 uptime. Do not put the `.accdb` on a WAN/VPN/Wi-Fi-only share with multiple writers. When you outgrow it, migrate the back-end to [microsoft-sql-server](microsoft-sql-server.md) (the official upsizing path), [postgresql](postgresql.md), or [sqlite](sqlite.md) for embedded single-file needs.
- **Drivers/connectors:** ODBC/OLEDB (the redistributable "Microsoft Access Database Engine" / ACE driver lets non-Access apps read `.accdb`/`.mdb`), DAO, ADO. BI/dbt/Kafka/CDC integration is effectively absent — there is no log to tail.
- **Community/support:** huge legacy user base, vast forum/Stack Overflow knowledge, commercial Access dev shops (e.g., FMS). Docs quality good. Learning curve: very low to start, deceptively high to do multi-user correctly.

## Licensing & cost
- **License:** **proprietary, commercial.** Bundled with Microsoft 365 (certain tiers) and Office Professional; not OSS. No copyleft/source-available question applies — see [license-taxonomy](../concepts/license-taxonomy.md) for the categories Access does *not* fit. The **Access Database Engine Redistributable** (ACE driver) is free to distribute for reading files, but the Access app itself is licensed.
- **Self-managed vs managed:** self-managed file only; no managed/cloud service (Access Web Apps / SharePoint-hosted Access were **retired**). Microsoft positions **Power Apps + Dataverse** as the cloud successor, which is a different product and pricing model.
- **Lock-in:** moderate — `.accdb` is a proprietary format, and forms/reports/macros/VBA do not port to other databases (only the table data migrates cleanly). Multi-value and attachment fields actively complicate migration.
- **Cost model:** per-user Office/365 licensing. No per-GB or per-query cost; the "cost" at scale is operational pain and corruption, not license fees.

## Hardware / deployment
- **Resource profile:** lightweight, disk-bound for large files; working set need not fit in RAM but large files over a network are I/O- and latency-bound. CPU is rarely the limit.
- **Storage assumptions:** local NVMe/SSD ideal. **Network-attached file shares are a known reliability hazard** — SMB over Wi-Fi/VPN is the most reliable way to corrupt the file. Never on object storage or anything with non-POSIX locking semantics.
- **Footprint:** **embedded/desktop single-file** (conceptually like [sqlite](sqlite.md) but Windows-only and with a full app/RAD layer). No clustered or serverless mode.
- **Deployment:** Windows desktop only (no native macOS/Linux Access; the ACE driver runs on Windows). On-prem/LAN; not container/k8s-oriented. Best practice is **split FE/BE**, one shared back-end file, individual front-ends per user.

## Bottom line
Reach for Access when one person, or a small trusted LAN workgroup, needs a quick database app with forms and reports and you value build speed over robustness — it is one of the fastest RAD tools ever made. Do **not** use it for web/public apps, real concurrency, mission-critical durability, or data approaching 2 GB. The single biggest gotcha: it is a **shared file, not a server** — multiple concurrent writers over a network share (especially Wi-Fi/VPN) will eventually corrupt it, because there is no server-side transaction log to recover from.

## Sources
- [Access specifications — Microsoft Support](https://support.microsoft.com/en-us/access/access-specifications) (2 GB limit, 255 concurrent users, 255 fields/table, 32,768 objects)
- [Access Database Engine — Wikipedia](https://en.wikipedia.org/wiki/Access_Database_Engine) (ACE vs Jet, record vs page locking, transactions, replication discontinued)
- [Understanding Microsoft Jet Locking — FMS](https://www.fmsinc.com/MicrosoftAccess/JetEngine/jet_locking.html) (page- vs record-level locking detail)
- [Microsoft Access Database Scalability: How many users? — FMS](https://blog.fmsinc.com/microsoft-access-database-scalability-how-many-users-can-it-support/) (real-world concurrency limits)
- [When and How to Upsize Microsoft Access Databases to SQL Server — FMS](https://www.fmsinc.com/microsoftaccess/SQLServerUpsizing/how/index.htm)
