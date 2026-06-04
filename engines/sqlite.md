---
name: SQLite
slug: sqlite
rank: 11
data_model: Relational (embedded)
license: Public Domain
summary: The world's most-deployed database — a zero-config, in-process relational engine that is one file on disk, single-writer, and ruthlessly tested.
last_researched: 2026-06-04
confidence: high
---

# SQLite

> An embedded, serverless, single-file relational database that runs inside your process — choose it when the database lives next to the app and one writer at a time is fine; avoid it when you need concurrent writers across a network.

## Identity
- **Taxonomy / data model:** Relational (SQL). Embedded/in-process library, not a client-server DBMS — there is no daemon; the database is a single file and the engine is linked into the host application.
- **Storage model:** Row-store on a B-tree on-disk format ([lsm-vs-btree](../concepts/lsm-vs-btree.md)). The entire database — tables, indexes, schema — is one cross-platform file ([file format is a documented, stable, backwards-compatible standard](https://sqlite.org/fileformat2.html)). Page-based; default page size 4 KB.
- **Workload:** OLTP-leaning, but realistically a general-purpose embedded store. Not OLAP — for in-process analytics the columnar cousin is [duckdb](duckdb.md). See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP (single-node, single-writer).
- See [embedded-databases](../concepts/embedded-databases.md).

## Distribution & consistency
- **CAP / PACELC:** N/A — single-node, non-distributed. No replication, no partitions, so [cap-pacelc](../concepts/cap-pacelc.md) does not apply to core SQLite.
- **Isolation:** Default isolation is **serializable** — transactions behave as some serial execution ([SQLite isolation docs](https://sqlite.org/isolation.html)). Readers get **snapshot isolation** of the database as it was when their read transaction began ([same source](https://sqlite.org/isolation.html)). This is a genuine serializable claim, not "ACID = snapshot" hand-waving; it is achievable precisely *because* writes are serialized to one at a time. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md) (SQLite is not full MVCC — it uses file/WAL-based snapshots, not per-row versions).
- **Concurrency:** **Exactly one writer at a time** for the whole database. In rollback-journal mode a writer blocks all readers; in **WAL mode** readers and the single writer proceed concurrently (readers don't block the writer, writer doesn't block readers), but **WAL does not give concurrent writers** — a second writer gets `SQLITE_BUSY` ([WAL docs](https://sqlite.org/wal.html)).
- **Replication / failover:** None built in. HA is bolted on externally — e.g. litestream-style streaming of the WAL to object storage, or rqlite / dqlite which wrap SQLite in [consensus-raft-paxos](../concepts/consensus-raft-paxos.md). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** N/A (single node).
- **Clock dependency:** None. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, but unusually flexible: by default columns use **type affinity / dynamic typing** — a column's declared type is a hint, and you can store any type in any column (the classic SQLite gotcha). [`STRICT` tables](https://sqlite.org/stricttables.html) (3.37+, 2021) enforce rigid types per row.
- **Migration:** `ALTER TABLE` supports `ADD COLUMN`, `RENAME`, `DROP COLUMN` (3.35+), but is limited compared to Postgres; complex changes use the documented 12-step table-rebuild dance. DDL is transactional. There is no online-DDL/locking concern in the multi-user sense because there is at most one writer anyway.
- **Type system:** storage classes NULL, INTEGER, REAL, TEXT, BLOB. JSON via built-in [JSON functions](https://sqlite.org/json1.html) (and `JSONB` binary form, 3.45+); generated columns; full-text search via FTS5; R-Tree module for geospatial/bounding-box; no native vector type (extensions like sqlite-vec add ANN — see [vector-search-ann](../concepts/vector-search-ann.md)).

## Query interface
- **Language:** SQL — a large, mostly standard subset (window functions, CTEs incl. recursive, `UPSERT`, `RETURNING` (3.35+), full outer join (3.39+)). Some intentional omissions (limited `ALTER`, no native stored-procedure language). API-only access is also common via the C API.
- **Transactions:** Full multi-statement ACID. `BEGIN`/`COMMIT`/`ROLLBACK`, savepoints, deferred/immediate/exclusive transaction modes.
- **Native vs app-side:** Native joins, aggregations, subqueries, secondary indexes, partial & expression indexes, window functions.
- **Stored procedures / UDFs:** No SQL stored-procedure language. UDFs, aggregates, virtual tables, and collations are registered **from the host program** in C (and via bindings: Python, Rust, etc.). Virtual tables are the main extensibility hook (FTS5, R-Tree, CSV, etc.).

## Scaling & topology
- **Vertical only.** No sharding, no partitioning, no clustering in core SQLite. "Scaling" means a bigger box and read concurrency via WAL. Theoretical max DB size ~281 TB; practical limits are filesystem and single-writer throughput.
- **Read replicas:** none natively; achievable via external WAL shipping (litestream) or Raft wrappers (rqlite, dqlite). Reads from such replicas are typically eventually consistent.
- **Storage/compute separation:** N/A for core SQLite (storage *is* the local file). Cloud variants change this: [Turso/libSQL](https://turso.tech/libsql) and [Cloudflare D1](https://developers.cloudflare.com/d1/) offer SQLite-compatible managed/edge databases; see [storage-compute-separation](../concepts/storage-compute-separation.md). litefs presents SQLite over a FUSE filesystem for replication.

## Performance & durability
- **Write path:** Either a rollback journal (default historically) or **WAL** (preferred for concurrency). Durability is governed by `PRAGMA synchronous`: `FULL` fsyncs the WAL/journal at commit; `NORMAL` (the common WAL default) fsyncs less often. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Data-loss window — the big gotcha:** In WAL mode with `synchronous=NORMAL`, transactions are durable across *application* crashes but **a recent commit can be rolled back after an OS crash or power loss** ([SQLite WAL docs](https://sqlite.org/wal.html)). Worse, defaults differ by platform/build: macOS's system SQLite ships `synchronous=NORMAL` while Homebrew builds default to `FULL`, and even `synchronous=FULL` in *journal* mode may not be fully durable on power loss per recent analysis ([avi.im, 2025](https://avi.im/blag/2025/sqlite-fsync/); [HN discussion](https://news.ycombinator.com/item?id=45066999)). Treat "durable by default" as **build-dependent — verify your `synchronous` and journal mode.**
- **Throughput/latency:** In-process, no network/IPC round-trip, so point reads/writes are extremely low-latency. With WAL + batched transactions, single-node write throughput is high; but throughput collapses if each statement is its own transaction (each commit fsyncs). Single-writer serialization is the ceiling under write contention — `SQLITE_BUSY` is the symptom.
- **Compaction/GC:** No background compaction. Deleting rows leaves free pages; reclaim with `VACUUM` (rewrites the whole file, takes a lock) or `auto_vacuum`. WAL grows until a checkpoint folds it back into the main file; checkpoints are mostly automatic but can cause occasional latency spikes.

## Operations & maturity
- **Backup/restore:** Online Backup API; `VACUUM INTO` for a clean copy; or copy the file when quiesced. PITR is not native but is provided by litestream (continuous WAL replication to S3) or the `.dump` SQL text export.
- **Observability:** `EXPLAIN QUERY PLAN`, the query planner stability guarantee, `PRAGMA` introspection, `sqlite3_analyzer`. No server-side metrics/slow-query log — observability lives in the host app.
- **Upgrade:** Library upgrade = recompile/relink (or update the system lib); file format is forward/backward compatible across versions, so no data migration. No rolling-upgrade concept (no cluster).
- **Maturity:** Among the most thoroughly tested software in existence — [100% branch (MC/DC) test coverage](https://sqlite.org/testing.html), billions of deployments (every Android/iOS device, browsers, many apps). Known failure modes are about misuse, not engine bugs: `SQLITE_BUSY` under write contention, durability surprises from `synchronous` defaults, type-affinity foot-guns, and corruption when a database file is placed on a network filesystem (NFS/SMB) where locking is unreliable ([SQLite explicitly warns against this](https://sqlite.org/faq.html#q5)). No Jepsen report exists — Jepsen targets distributed systems, and SQLite is single-node.

## Ecosystem & people
- **Canonical use cases:** application file format / local app storage (desktop, mobile), embedded/IoT, browser storage, edge and on-device, test fixtures, small-to-medium websites with read-heavy traffic, caches, and as the local query engine for analytics tooling.
- **Anti-patterns:** high-concurrency multi-writer workloads; client-server access over a network (use [postgresql](postgresql.md) / [mysql](mysql.md)); databases on NFS/SMB; very large write-throughput needs; analytics over big columnar data (use [duckdb](duckdb.md)).
- **Drivers/connectors:** First-class everywhere — stdlib in Python (`sqlite3`); native bindings in essentially every language; ORMs (SQLAlchemy, Django, Rails ActiveRecord, GORM, Prisma); dbt has a community SQLite adapter; CDC/Kafka are not native (no log to tail beyond the WAL).
- **Community / support:** Developed and controlled by a small core team (D. Richard Hipp et al.) under the **SQLite Consortium** funding model; not an open-contribution project (it accepts code only under specific terms). Docs are excellent and primary-source-quality. Learning curve is minimal.

## Licensing & cost
- **License:** **Public domain** — the source code is dedicated to the public domain, arguably the most permissive arrangement possible (the team also sells a [warranty-of-title license](https://sqlite.org/copyright.html) for orgs that need a contract). No copyleft, no SSPL/BSL drama, no post-2018 relicensing. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed:** Always self-embedded; there is no managed SQLite service in the core project. Managed/edge offerings are *compatible reimplementations or wrappers* (Turso/libSQL, Cloudflare D1, rqlite) — those carry their own licenses and lock-in.
- **Cost model:** The engine is free. Cost is just the storage and compute of wherever it's embedded; effectively zero marginal cost. Paid commercial add-ons exist (SEE encryption extension, the Consortium membership).

## Hardware / deployment
- **Resource profile:** Tiny. Library footprint is on the order of ~1 MB; can run with very little RAM. Working set need not fit in RAM — it's a disk-backed B-tree with a page cache; performance is best when hot pages fit the cache. Largely disk/IO-bound for writes (fsync), CPU-cheap for reads.
- **Storage assumptions:** Local disk strongly preferred. NVMe/SSD helps commit latency. **Network filesystems are unsafe** due to broken/locking semantics — explicitly discouraged.
- **Footprint:** Embedded/in-process. No server, no ports, no config files. Optionally fully in-memory (`:memory:`).
- **Deployment:** Ships *inside* the application binary or as a single file alongside it. For k8s, a SQLite file on a PVC works for single-pod stateful apps but does not scale across replicas without an external replication layer (litefs/litestream/rqlite).

## Bottom line
Reach for SQLite whenever the database can live in the same process/host as the application and writes are not heavily concurrent: local apps, mobile, edge, embedded, tests, and surprisingly capable read-heavy websites. Do not reach for it when multiple machines must write over a network, when you need horizontal scale or built-in HA, or for OLAP (use [duckdb](duckdb.md)) — and never put the file on NFS. The single biggest gotcha is durability: defaults vary by platform/build, and in WAL + `synchronous=NORMAL` a just-committed transaction can be lost on power failure — set `synchronous` deliberately if your data must survive a crash.

## Sources
- [SQLite — Isolation](https://sqlite.org/isolation.html)
- [SQLite — Write-Ahead Logging (WAL)](https://sqlite.org/wal.html)
- [SQLite — Atomic Commit](https://sqlite.org/atomiccommit.html)
- [SQLite — How SQLite Is Tested](https://sqlite.org/testing.html)
- [SQLite — File Format](https://sqlite.org/fileformat2.html)
- [SQLite — STRICT Tables](https://sqlite.org/stricttables.html)
- [SQLite — JSON1 / JSONB](https://sqlite.org/json1.html)
- [SQLite — Copyright / Public Domain](https://sqlite.org/copyright.html)
- [SQLite — FAQ (network filesystem warning)](https://sqlite.org/faq.html#q5)
- ["SQLite commits are not durable under default settings" — avi.im, 2025](https://avi.im/blag/2025/sqlite-fsync/)
- [HN discussion: SQLite durability documentation is unclear](https://news.ycombinator.com/item?id=45066999)
