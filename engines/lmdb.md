---
name: LMDB
slug: lmdb
rank: 125
data_model: Key-value
license: OpenLDAP Public License (permissive)
summary: Embedded copy-on-write B+tree KV store; lock-free readers, single writer, crash-proof by design — the fast, simple choice when one process owns the data.
last_researched: 2026-06-04
confidence: high
---

# LMDB

> A tiny embedded key-value library (a memory-mapped, copy-on-write B+tree) that gives full ACID, lock-free MVCC reads, and corruption-proof crash recovery in exchange for one hard limit: a single writer at a time.

## Identity
- **Taxonomy / data model:** embedded ordered key-value store. Keys and values are opaque byte strings; keys are kept sorted (memcmp order by default, custom comparators allowed). Supports "sub-databases" (named B+trees in one env) and duplicate values per key (`MDB_DUPSORT`). See [embedded-databases](../concepts/embedded-databases.md).
- **Storage model:** single memory-mapped file holding a B+tree, on-disk format. **Copy-on-write, append-style** updates — modified pages are written to *new* locations, never overwriting live data, so the on-disk image is always a valid tree ([Symas/Howard Chu interview](https://www.symas.com/post/getting-down-and-dirty-with-lmdb)). Not an LSM and not a conventional in-place B-tree; see [lsm-vs-btree](../concepts/lsm-vs-btree.md). Reads return pointers directly into the mmap — zero-copy, no malloc/memcpy on the read path ([LMDB docs](http://www.lmdb.tech/doc/)). A second internal B+tree (the "free list") tracks pages freed by old transactions for reuse, which is why LMDB needs **no compaction, no checkpointing, no WAL** replay.
- **Workload:** OLTP-style point and range reads, read-heavy embedded workloads. Not OLAP, not HTAP — it is a storage library inside one process, not a query engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** N/A — single-node, single-process embedded library. No replication, no network, no clustering. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — non-distributed.
- **Default isolation & what's achievable:** **serializable**, and genuinely so, not "ACID = snapshot in disguise." Writes are fully serialized (one writer), so write transactions cannot interleave; readers get a stable MVCC snapshot taken at transaction start ([Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database); [LMDB docs](http://www.lmdb.tech/doc/)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** none built in. Applications replicate at a higher layer (e.g. OpenLDAP syncrepl ships on top of back-mdb). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** no — there is one consistency model.
- **Clock dependency:** none; correctness does not rest on clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema:** schemaless — values are opaque bytes; any structure lives in application code. Sub-databases give crude namespacing.
- **Migration / DDL:** none — there is no schema to alter. The mmap *map size* (max DB size) is set at open time; growing it requires reopening the environment (or all readers closing), which is the closest thing to a "migration" pain point.
- **Type system:** none. Bytes in, bytes out. With `MDB_INTEGERKEY`/`MDB_DUPSORT` you get native integer-key ordering and multi-values, but no JSON, arrays, geospatial, or vector types.

## Query interface
- **Language:** **API-only** (C library; `mdb_get`/`mdb_put`/`mdb_del` plus cursors for range scans). No SQL, no DSL. Bindings exist for Python (`lmdb`, `py-lmdb`), Go, Rust, Java, Node, etc.
- **Transactions:** full multi-statement **ACID** transactions. One read-write txn at a time; unlimited concurrent read-only txns. Nested write sub-transactions are supported.
- **Native vs app-side:** no joins, no secondary indexes, no aggregations — all app-side. Range and prefix scans via cursors are native and cheap (ordered B+tree).
- **Stored procedures / UDFs:** none.

## Scaling & topology
- **Vertical vs horizontal:** vertical only. Scale = bigger box, faster NVMe, more RAM for page cache. No sharding mechanism (app must shard across multiple env files itself).
- **Sharding / partitioning:** none native.
- **Read replicas / read consistency:** N/A (no replication). Within a process, readers always see a consistent committed snapshot.
- **Storage/compute separation:** N/A — embedded, storage and compute are the same process. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** copy-on-write into free/new pages, then commit flushes data pages and updates one of **two alternating meta pages** (double-buffered) so a torn meta write can never destroy the previous valid root. Default commit does `fsync()` and is **bottlenecked by fsync** ([LMDB docs](http://www.lmdb.tech/doc/)). Durability is tunable via flags, trading the **data-loss window** for speed (see [wal-and-durability](../concepts/wal-and-durability.md)):
  - `MDB_NOMETASYNC` — skip the metadata fsync each commit; a crash may lose the *last* committed txn but integrity is preserved.
  - `MDB_NOSYNC` — skip fsync at commit; with write-ordering preserved you keep **A, C, I but lose D** — a crash may roll back recent committed transactions while leaving the database structurally intact ([LMDB docs](http://www.lmdb.tech/doc/); [OpenLDAP list](https://openldap-technical.openldap.narkive.com/scaaOuEH/lmdb-concurrent-operation-and-mdb-nosync)).
  - `MDB_WRITEMAP` + `MDB_MAPASYNC` — writable mmap with async msync; fastest, weakest durability, and a stray pointer can in principle corrupt the map.
- **Throughput / latency:** read latency is excellent and extremely predictable — pointer dereferences into the page cache, **no per-read locks** for readers ([Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)). Tail (p99) reads are tight because there is no compaction or background GC to cause stalls. Writes are serialized, so write *throughput* is the single-writer ceiling, but with sorted batch puts in one txn it is competitive.
- **Compaction / vacuum / GC:** none — freed pages are recycled via the internal free-list B+tree, so no p99-killing compaction. **The main gotcha:** a long-running *read* transaction pins the snapshot and prevents the writer from reclaiming pages freed after that snapshot, so the file can **grow rapidly** until that reader finishes ([Symas interview](https://www.symas.com/post/getting-down-and-dirty-with-lmdb)). Keep read txns short.

## Operations & maturity
- **Backup / restore / PITR:** hot backup via `mdb_copy` (consistent snapshot of a live env), or just copy the file when idle. No native PITR. The file is sparse-ish but does not shrink on its own; `mdb_copy -c` compacts.
- **Observability:** `mdb_stat` / `mdb_dump` CLI tools; `mdb_env_info`/`mdb_stat` API expose page counts, depth, reader table. No query planner (no queries), no slow-query log.
- **Upgrade story:** it is a linked library — "upgrade" = relink a new version; file format has been stable for years. No server to roll. Day-2 burden is low: no daemon, no GC tuning, no compaction scheduling.
- **Maturity:** very mature and battle-tested. Created by Howard Chu (Symas) as OpenLDAP's `back-mdb` backend; Debian adopted it as a Berkeley DB replacement after Oracle's 2013 AGPL change. Used by Monero, PowerDNS, Meilisearch, and many others ([Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)). No public Jepsen report — and Jepsen targets distributed systems, so it is not applicable to a single-node embedded library. Known failure modes: file-size blowup from long readers; map-size exhaustion (`MDB_MAP_FULL`) if you under-size; corruption only realistically via `MDB_WRITEMAP` + bad app pointers. ⚠️ unverified — exact disk-size growth multiplier under sustained long-reader load is workload-dependent.

## Ecosystem & people
- **Canonical use cases:** embedded metadata/index stores, caches that must survive restart, directory servers (OpenLDAP), blockchain state (Monero), search-engine storage (Meilisearch), high-read-ratio local KV needs, "I need SQLite-style embedding but pure KV and faster reads." See [embedded-databases](../concepts/embedded-databases.md).
- **Anti-patterns:** write-heavy/high-write-concurrency workloads (single writer is a hard ceiling); multi-process write fan-in; data sets needing built-in compression, secondary indexes, queries, or replication; anything needing horizontal scale; values much larger than RAM working set when you also need random write throughput. Reach for [rocksdb](rocksdb.md)/[leveldb](leveldb.md) (LSM, write-heavy) or [sqlite](sqlite.md) (SQL + embedded) instead.
- **Drivers / connectors:** mature bindings in nearly every language. No CDC/Kafka/dbt/BI integration — it lives below that layer; you wire those yourself.
- **Community / support / docs:** smaller, focused community; commercial support from Symas. Docs are terse C-API reference plus Howard Chu's talks/papers. Learning curve is low for KV usage, but the mmap/map-size/long-reader semantics bite newcomers.

## Licensing & cost
- **OSS license:** **OpenLDAP Public License** — a permissive, BSD-style license ([Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)). No post-2018 relicensing; no SSPL/BSL drama. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-managed only — it is a library you compile in. No vendor, no managed service, no lock-in beyond the (stable, documented) file format. (Note: the on-disk format is endianness/architecture-sensitive, complicating raw file transfer between platforms; use `mdb_dump`/`mdb_load` to move data.)
- **Cost model:** free; cost = your own hardware. Scales cheaply because there is no per-node/per-core licensing and no separate process to run.

## Hardware / deployment
- **Resource profile:** memory-bound for performance — best when the hot working set fits in OS page cache; the full DB need *not* fit in RAM (it is paged in on demand), but random access to a DB larger than RAM degrades to disk-seek speed. CPU cost per op is minimal.
- **Storage assumptions:** benefits from fast random-read storage (NVMe/SSD); fine on network-attached storage but durability flags rely on the underlying storage honoring fsync/write ordering. Map size (max file size) must be chosen up front (can be set large; file is sparse until used).
- **Footprint:** **embedded** — a small C library (~tens of KB), no server, no background threads of its own. Single file plus a lock file.
- **Deployment:** runs wherever your app runs (Linux, BSD, macOS, Windows, mobile). In k8s it is just part of the app pod; persistence is whatever volume backs the env file (a StatefulSet-style durable volume if you need the data to survive pod restarts).

## Bottom line
Reach for LMDB when one process needs a fast, dead-simple, crash-proof embedded key-value store with rock-steady read latency and zero operational ceremony — no daemon, no compaction, no GC tuning. Do **not** reach for it for write-heavy or write-concurrent workloads (the single writer is a hard wall), for anything needing queries/indexes/replication/sharding, or if you want compression. The single biggest gotcha: a forgotten long-running **read** transaction stops page reclamation and lets the file balloon — keep read transactions short, and size the map generously.

## Sources
- [LMDB official docs (Symas / lmdb.tech)](http://www.lmdb.tech/doc/)
- [The Lightning Memory-Mapped Database — Howard Chu, SNIA SDC15 (PDF)](https://www.snia.org/sites/default/files/SDC15_presentations/database/HowardChu_The_Lighting_Memory_Database.pdf)
- [Getting Down and Dirty with LMDB — Symas interview with Howard Chu](https://www.symas.com/post/getting-down-and-dirty-with-lmdb)
- [LMDB — Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)
- [LMDB concurrent operation and MDB_NOSYNC — OpenLDAP technical list](https://openldap-technical.openldap.narkive.com/scaaOuEH/lmdb-concurrent-operation-and-mdb-nosync)
- [Database of Databases — LMDB](https://dbdb.io/db/lmdb)
- [libmdbx (extended fork)](https://github.com/erthink/libmdbx)
