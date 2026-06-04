---
name: dBASE
slug: dbase
rank: 49
data_model: Relational (legacy / flat-file xBase)
license: Proprietary commercial (dBASE Plus, source-closed); historical versions Ashton-Tate/Borland
summary: 1980s microcomputer DBMS whose .dbf flat-file format outlived the product; a single-file, file-locking xBase environment now niche-only.
last_researched: 2026-06-04
confidence: high
---

# dBASE

> The original PC database (1980): a single-file, file-share xBase environment whose lasting legacy is the .dbf format, not its largely-stagnant present-day product.

## When to use

**Use dBASE if:**
- ✅ You must maintain or extend an existing legacy xBase/dBL line-of-business desktop app.
- ✅ You need to read/write the still-ubiquitous `.dbf` interchange format (GIS shapefiles, government datasets, older tooling).
- ✅ Your dataset is small, single-user, and lives on local disk.

**Avoid dBASE if:**
- ❌ You're starting anything new — almost any modern engine ([sqlite](sqlite.md), [postgresql](postgresql.md), [mysql](mysql.md)) is the right tool instead.
- ❌ You need real transactions, enforced isolation, replication, or horizontal scale — none exist; concurrency safety rests entirely on the app calling locks correctly.
- ❌ You run multi-writer over an SMB/network file share — there is no WAL, and an ill-timed crash can corrupt the `.dbf`/index set.

## Identity
- **Taxonomy / data model:** Relational-ish flat-file "xBase" engine. Each table is one `.dbf` file with a fixed-width record layout; "relational" here means you can open multiple tables and relate them in app code, not a true relational engine with a query planner and referential integrity. The product bundles a DBMS, a forms/report engine, and the dBL programming language ([db-engines / Wikipedia](https://en.wikipedia.org/wiki/DBase)).
- **Storage model:** Row-store, fixed-width records in a `.dbf` file with a self-documenting header (field names, types, widths, record count); variable-length text spills to a `.dbt`/`.fpt` memo file; indexes live in separate `.ndx` (single) or `.mdx` (multi-index, up to ~47/48 indexes per file) B-tree files ([.dbf format, Wikipedia](https://en.wikipedia.org/wiki/.dbf); [LoC DBF format description](https://www.loc.gov/preservation/digital/formats/fdd/fdd000325.shtml)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM — classic in-place B-tree indexing over flat data files.
- **Workload:** OLTP-style interactive record CRUD on small desktop/LAN datasets. Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). It is fundamentally a single-machine / shared-file-on-a-network-drive tool, not a server engine.

## Distribution & consistency
- **CAP under partition:** N/A — not a distributed system. It is a file-based engine; "concurrency" means multiple desktop clients opening the same `.dbf` over an SMB/file share. See [cap-pacelc](../concepts/cap-pacelc.md) for why this axis does not apply.
- **PACELC:** N/A — single shared file, no replication.
- **Default isolation & what's achievable:** No MVCC, no transaction isolation levels in the SQL sense. Concurrency is managed by **file and record locks** (`RLOCK()`, `FLOCK()`, exclusive `USE` vs shared) that the application must explicitly request; correctness depends on disciplined app-level locking. ⚠️ unverified — the legacy file engine has no enforced serializable isolation; lost-update and dirty-read avoidance is the programmer's responsibility, not the engine's. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** None native. See [replication-models](../concepts/replication-models.md) — N/A.
- **Tunable consistency?** N/A.
- **Clock dependency:** None for correctness. See [clocks-and-time](../concepts/clocks-and-time.md) — N/A.

## Schema
- **Schema-on-write.** Rigid fixed-width record layout defined at table creation; field types are limited (Character, Numeric, Float, Date, Logical, Memo, and newer types in modern dBASE).
- **Migration/evolution:** Changing a `.dbf` structure rewrites the file (historically via `COPY STRUCTURE` / `MODIFY STRUCTURE` rebuilds). No online DDL; restructuring is an offline file operation.
- **Type system:** Classic types are narrow (e.g. Character fields capped at 254 bytes; longer text goes to memo). Modern dBASE Plus adds wider/auto-increment/timestamp types. No native JSON, arrays, geospatial, or vector types.

## Query interface
- **Language:** Two layers. (1) The historic interactive **xBase dot-prompt command language** (`USE`, `SKIP`, `GO TOP`, `LOCATE`, `REPLACE`, `INDEX ON`), and (2) **dBL**, the modern object-oriented dBASE language in dBASE Plus (OODML for data access) ([dBASE Plus overview](https://www.dbase.com/dbase-plus-10-overview/overview/)). SQL is supported as a secondary interface, largely via the Borland Database Engine's "Local SQL" subset and ODBC/ADO pass-through, not as the primary or fully-featured query layer ([dBASE BDE article](https://www.dbase.com/Gold/Articles/BDEAliases/BDEAliases.print.htm)).
- **Transactions:** ⚠️ unverified — BDE provides limited transaction support for local tables, but the core model is record-navigation + explicit locking rather than full multi-statement ACID. Treat "ACID" claims skeptically: durability/atomicity guarantees for `.dbf` writes are weak and crash-sensitive.
- **Native vs app-side:** Indexes are native (`.ndx`/`.mdx`); joins, aggregations, and relations are largely expressed in dBL app code (set-relation between work areas) rather than a SQL optimizer. Local SQL via BDE offers basic SELECT/JOIN over `.dbf` tables.
- **Stored procedures / UDFs:** Logic lives in dBL program files (`.prg`) and classes, not server-side stored procedures (there is no server).

## Scaling & topology
- **Vertical vs horizontal:** Vertical only, and modestly so — it is a desktop/small-LAN tool. No sharding, no clustering. See [storage-compute-separation](../concepts/storage-compute-separation.md) — N/A.
- **Sharding / partitioning:** None. Scale ceiling is the practical size of a single `.dbf` over a file share before lock contention and corruption risk dominate.
- **Read replicas / read consistency:** N/A — no replication.
- **Concurrency limit:** Multi-user means N clients on a shared file directory; this is fragile over network shares (lock semantics depend on the filesystem/OS, and `.dbf`/index corruption from interrupted writes or bad SMB locking is a well-known historical failure mode).

## Performance & durability
- **Write path:** Direct in-place writes to the `.dbf` file plus separate index file updates; durability depends on OS file buffering and `fsync`/flush behavior, not a managed WAL. There is no write-ahead log in the [wal-and-durability](../concepts/wal-and-durability.md) sense — **a crash mid-write can leave the `.dbf` header record-count and the data/index out of sync, corrupting the table** (the canonical xBase failure, often "fixed" by reindexing and header repair).
- **Throughput/latency:** Fast for small single-user datasets on local disk (it was designed for 1980s PCs). p99 degrades sharply under multi-user file-share contention; no engine-side tail-latency management.
- **Compaction / GC:** Deletes are *logical* (records flagged deleted, space not reclaimed) until a `PACK` operation physically removes them and rebuilds; indexes must be `REINDEX`ed to stay consistent. No background vacuum.

## Operations & maturity
- **Backup/restore:** File-copy backup of the `.dbf`/`.dbt`/`.mdx` set (best done with the table closed/exclusive). No PITR, no snapshots, no incremental log shipping.
- **Observability:** Minimal — no metrics endpoints, no EXPLAIN/query planner, no slow-query log. Debugging is via the dBL IDE/debugger in dBASE Plus.
- **Upgrade story:** Desktop application install/upgrade; the 64-bit-Windows path for legacy DOS apps runs through the **dbDOS** emulator. Day-2 burden is mostly file hygiene: regular `PACK`/`REINDEX` and corruption recovery.
- **Maturity:** Extremely mature *as a format* and historically — dBASE was the dominant PC DBMS in the 1980s ([Wikipedia](https://en.wikipedia.org/wiki/DBase)). The product itself peaked at dBASE III, faltered badly with dBASE IV (1988), and the xBase market faded by ~2000. The current owner, dBase LLC, ships dBASE PLUS — the current major version is dBASE PLUS 12 (announced May 2018; point releases ~12.x), targeting Windows ([dBASE PLUS 12 product page](https://www.dbase.com/dbase-plus-12/)). **No Jepsen report exists or is applicable** (not a distributed system).

## Ecosystem & people
- **Canonical use cases:** Maintaining/extending legacy line-of-business desktop apps; reading/writing the ubiquitous `.dbf` interchange format (still emitted by GIS shapefiles, some government datasets, Excel/older tooling). The format's self-documenting header is why so many tools read `.dbf`.
- **Anti-patterns:** Any web-scale, high-concurrency, multi-writer, or server-side workload; anything needing real transactions, strong isolation, replication, or horizontal scale. For new projects almost any modern engine ([sqlite](sqlite.md), [postgresql](postgresql.md), [mysql](mysql.md)) is the right tool instead.
- **Drivers / connectors:** Read access to `.dbf` is broadly available (BDE, ODBC, plus open-source readers in Python, Perl `DBD-XBase`, etc.). Open-source xBase-language descendants — **Harbour** and **XSharp** — keep the language alive independently of the dBase LLC product.
- **Community / support:** Small, aging, niche community; commercial support from dBase LLC. Docs are dated. Learning curve is low for the classic command language but the ecosystem knowledge is shrinking.

## Licensing & cost
- **License:** Proprietary, closed-source commercial product. Historically owned by Ashton-Tate → Borland → dBase LLC. No OSS license; this is not a [license-taxonomy](../concepts/license-taxonomy.md) permissive/copyleft/source-available situation — it is classic paid proprietary software. (The `.dbf` *format* is unencumbered and de-facto open, which is separate from the product license.)
- **Self-managed vs managed-only:** Self-managed desktop install only; no managed/cloud offering.
- **Lock-in:** Low at the data layer (`.dbf` is portable), higher at the application layer (dBL/forms code is dBASE-specific).
- **Cost model:** Per-seat / per-developer license plus a redistributable runtime (and BDE) for deployed apps. ⚠️ unverified — exact current pricing not confirmed from a primary source.

## Hardware / deployment
- **Resource profile:** Lightweight, disk-bound on small files; trivially fits modern RAM. Working set does not need to fit in RAM, but small datasets effectively cache anyway.
- **Storage assumptions:** Designed for local disk; **network-attached/SMB file shares are the historical multi-user deployment and also the historical source of locking/corruption pain.**
- **Footprint:** Effectively an embedded/desktop file engine (no server daemon), conceptually closer to [sqlite](sqlite.md) than to a client/server DBMS — but without SQLite's single-file atomic-commit/WAL durability guarantees.
- **Deployment:** On-prem Windows desktop / small LAN; legacy DOS via dbDOS emulation. Not container/k8s oriented; no StatefulSet story.

## Bottom line
Reach for dBASE only to maintain an existing legacy app or to read/write the still-everywhere `.dbf` interchange format. Do not choose it for anything new: no real transactions, no enforced isolation, no replication, no horizontal scale, and a genuine corruption risk under multi-user file sharing. The biggest gotcha is durability — there is no WAL, so an ill-timed crash can corrupt a `.dbf`/index set, and concurrency safety rests entirely on the application calling locks correctly.

## Sources
- [dBase — Wikipedia](https://en.wikipedia.org/wiki/DBase)
- [.dbf file format — Wikipedia](https://en.wikipedia.org/wiki/.dbf)
- [Library of Congress: dBASE Table File Format (DBF)](https://www.loc.gov/preservation/digital/formats/fdd/fdd000325.shtml)
- [dBASE .DBF / index file structure (official)](https://www.dbase.com/Knowledgebase/INT/db7_file_fmt.htm)
- [dBASE Plus product overview (dBase LLC)](https://www.dbase.com/dbase-plus-10-overview/overview/)
- [dBASE PLUS 12 product page (dBase LLC, current version)](https://www.dbase.com/dbase-plus-12/)
- [Working with BDE Aliases in dBASE Plus (Local SQL / ODBC pass-through)](https://www.dbase.com/Gold/Articles/BDEAliases/BDEAliases.print.htm)
