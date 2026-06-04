---
name: LevelDB
slug: leveldb
rank: 132
data_model: Key-value (embedded LSM)
license: BSD-3-Clause (permissive)
summary: Google's lightweight embedded ordered key-value library; the canonical open-source LSM-tree, but single-process, library-only, and barely maintained.
last_researched: 2026-06-04
confidence: high
---

# LevelDB

> An embedded, single-process C++ library giving an ordered key→value byte-string map backed by an LSM tree — the original open-source LSM that seeded [rocksdb](rocksdb.md), now in maintenance mode.

## When to use

**Use LevelDB if:**
- ✅ You need a small, fast, dependency-light embedded ordered key-value store inside a single-process application
- ✅ You want LSM write throughput with zero operational footprint (no daemon, no wire protocol)
- ✅ You value a clean permissive BSD-3-Clause license and a tiny API
- ✅ You need ordered range scans over sorted keys (browser storage, local caches/indexes, blockchain node state)

**Avoid LevelDB if:**
- ❌ Default writes are not fsynced — a power loss can silently drop your last writes unless you set `sync=true` (and pay ~1000x latency)
- ❌ You need a server, multiple concurrent processes (one process per DB dir), replication, or cross-key transactions
- ❌ You need SQL/ad-hoc queries or sustained high-concurrency writes — and for most new embedded-LSM projects [rocksdb](rocksdb.md) is the better-maintained descendant

## Identity
- **Taxonomy / data model:** Embedded ordered key-value store. Keys and values are arbitrary byte arrays; keys are kept sorted by a user-supplied comparator (lexicographic by default). It is a *library*, not a server — there is no daemon, no wire protocol, no client-server support ([readme](https://github.com/google/leveldb)). See [embedded-databases](../concepts/embedded-databases.md).
- **Storage model:** Log-structured merge tree ([lsm-vs-btree](../concepts/lsm-vs-btree.md)). Writes land in an in-memory sorted skiplist (memtable) plus a write-ahead log; the memtable is flushed to immutable on-disk SSTable files organized into levels (L0..L6), merged by background compaction. On-disk format is SSTables (sorted blocks + index + optional Bloom filter); block compression via Snappy by default. Zstd support exists only on the unreleased `main` branch (added March 2023) and is **not** in the latest tagged release 1.23 (Feb 2021) ([readme](https://github.com/google/leveldb)).
- **Workload:** OLTP-ish embedded point/range access. Write-optimized (large sequential writes preferred over small random writes). Not OLAP, no query engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Designed at Google by Jeff Dean and Sanjay Ghemawat as an open-sourceable echo of the Bigtable tablet stack, and to back Chrome's IndexedDB ([dbdb.io](https://dbdb.io/db/leveldb)).

## Distribution & consistency
- **CAP under partition:** N/A — single-node, single-process embedded library. No replication, no cluster, no network. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — single-node.
- **Default isolation & what's achievable:** No multi-key transactions in the SQL sense. Atomicity is provided per `WriteBatch`: a batch is applied atomically and in order, so a crash never leaves a batch half-applied ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)). Consistent point-in-time reads come from **snapshots** (`DB::GetSnapshot()`): a reader holding a snapshot sees a frozen view regardless of concurrent writes; a NULL snapshot reads an implicit snapshot of current state ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)). This is effectively snapshot-style read consistency, not configurable SQL isolation levels — see [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md) (LevelDB uses internal sequence numbers per key, MVCC-like).
- **Replication:** None built in. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No. The only knob is the per-write `sync` flag (durability, not consistency).
- **Clock dependency:** None — ordering is by internal monotonic sequence number, not wall-clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schemaless. Keys and values are opaque byte arrays; any structure lives in application code.
- **Migration/evolution:** N/A — no schema, no DDL. The one cross-version constraint: the comparator name is persisted with the DB, and changing comparator semantics breaks key ordering / risks data loss ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)).
- **Type system:** None — bytes only. No native JSON, arrays, geospatial, or vector types. Range scans over sorted keys are the only "structure."

## Query interface
- **Language:** API-only (C++). Core ops: `Put(key,value)`, `Get(key)`, `Delete(key)`, `Write(WriteBatch)`, plus forward/backward iterators for range scans. No SQL, no query language ([readme](https://github.com/google/leveldb)).
- **Transactions:** Single atomic unit = `WriteBatch` (multi-key atomic write). No interactive/multi-statement transactions, no rollback after commit, no cross-key read-modify-write isolation beyond snapshots.
- **Native vs app-side:** No secondary indexes, no joins, no aggregations — all app-side. Only the primary sorted-key index exists.
- **Stored procedures / UDFs:** None. Extension points are C++ virtual interfaces: custom `Comparator`, `FilterPolicy` (Bloom), and `Env` (OS abstraction).

## Scaling & topology
- **Vertical vs horizontal:** Vertical only — bounded by one machine's disk and RAM. No sharding, no partitioning, no resharding (because no cluster). Horizontal scaling is entirely the embedding application's job.
- **Read replicas:** None. A given DB directory can be opened by **only one process at a time** (enforced by a filesystem lock); within that process multiple threads may share the `DB` object safely ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)).
- **Storage/compute separation:** N/A — local files only. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Append to WAL + insert into memtable. The `WriteOptions::sync` flag controls fsync: default `sync=false` hands data to the OS page cache and returns (so a *process* crash loses nothing, but a *machine* crash/power loss can lose the last few writes); `sync=true` forces `fsync`/`fdatasync`/`msync` before returning ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)). Synchronous writes are ~1000x slower than async ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)). **Data-loss window on crash:** with default async writes, all not-yet-fsynced updates since the last sync. See [wal-and-durability](../concepts/wal-and-durability.md). WAL/SSTable blocks carry CRC checksums; historically, mishandled fsync errors could silently undermine durability (a known LSM/filesystem gotcha).
- **Throughput/latency:** Per the project's own benchmark (~1.1M small entries): ~62.7 MB/s sequential writes, ~45 MB/s random writes; ~60K random reads/sec cold, rising to ~85K–190K/sec after compaction warms caches ([readme](https://github.com/google/leveldb)). Numbers are from 2011-era hardware — treat as relative, not absolute.
- **Compaction / GC:** Leveled compaction runs in a single background thread. p99 hazards: L0→L1 compaction can stall writes ("write stall" / "stop") when L0 accumulates too many files, and the single-threaded compactor can fall behind under sustained write bursts — a classic LSM tail-latency problem. Deletes are tombstones reclaimed only at compaction; space is not freed immediately. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).

## Operations & maturity
- **Backup/restore, PITR:** No built-in backup, snapshot-to-file, or PITR tooling. Operationally you copy the DB directory (ideally while quiesced) or use a snapshot + iterate. This is the embedding app's responsibility.
- **Observability:** Minimal. `GetProperty()` exposes a few stats (e.g., `leveldb.stats`, SSTable level counts, approximate sizes); no query plans, no slow-query log, no metrics endpoint.
- **Upgrade story:** It's a linked library — "upgrade" means relinking your app. On-disk format has been stable across versions; current release is **1.23** (Feb 2021). The repo states it is "receiving very limited maintenance" — only critical bug fixes and internal-client needs ([readme](https://github.com/google/leveldb)).
- **Maturity & known failure modes:** Mature and battle-tested (Chrome IndexedDB, Bitcoin Core historically, countless embedded uses), but effectively frozen. Known issues: write stalls under heavy load, single-threaded compaction, manifest/log corruption recovery quirks, and historical fsync-error handling. No Jepsen report exists (Jepsen targets distributed systems; LevelDB is single-node, so it is out of scope). ⚠️ unverified — no formal verification of crash-consistency exists for LevelDB itself.

## Ecosystem & people
- **Canonical use cases:** Embedded ordered KV storage inside an application — browser storage (IndexedDB), a building block beneath larger systems, local caches/indexes, blockchain node state. Good when you want LSM write throughput with zero operational footprint.
- **Anti-patterns:** Anything needing a server, multiple concurrent processes, replication/HA, transactions across keys, SQL/ad-hoc queries, large values, or heavy concurrent write load. For most of these, reach for [rocksdb](rocksdb.md) (Facebook's LevelDB fork: multi-threaded compaction, column families, transactions, tuning knobs) or a real database.
- **Drivers / connectors:** C++ core with community bindings (Python `plyvel`, Node `leveldown`/`level`, Go `goleveldb`, Java via JNI). No CDC, no Kafka/dbt/BI integration — it is a library, not a data platform.
- **Community & docs:** Large historical user base but the project itself is quiescent; most active investment moved to RocksDB. Docs are a concise README + `doc/index.md`; clear but minimal. Learning curve is low (a handful of API calls), one-developer footprint.

## Licensing & cost
- **OSS license:** BSD-3-Clause — permissive, no copyleft, no source-available restrictions, no post-2018 relicensing. See [license-taxonomy](../concepts/license-taxonomy.md). (Contrast with [rocksdb](rocksdb.md), which is GPLv2/Apache-2.0 dual-licensed.)
- **Self-managed vs managed:** Self-managed/embedded only; there is no managed offering and no vendor lock-in (it's a small BSD library you compile in).
- **Cost model:** Free; cost is purely the hardware it runs on plus engineering time. No per-node/core/GB licensing.

## Hardware / deployment
- **Resource profile:** Disk-bound for the dataset; memory used for the memtable, block cache, and Bloom filters. Working set need not fit in RAM (it's disk-backed LSM), but a larger block cache and Bloom filters sharply cut read amplification ([docs](https://github.com/google/leveldb/blob/main/doc/index.md)).
- **Storage assumptions:** Local filesystem. Benefits from fast local SSD/NVMe (compaction is IO-heavy); the `Env` abstraction lets you swap the OS/storage layer, but it assumes a POSIX-like local FS, not object storage.
- **Footprint:** Embedded library, single process. No daemon, no container/k8s story of its own — it ships inside whatever binary links it.
- **Deployment:** On-prem/in-process only. k8s relevance is only via the host application; a StatefulSet would manage that app's pod, not LevelDB directly.

## Bottom line
Reach for LevelDB when you need a small, fast, dependency-light embedded ordered key-value store inside a single-process application and you value a clean permissive BSD license and a tiny API. Do not reach for it if you need a server, multiple processes, replication, cross-key transactions, queries, or sustained high-concurrency writes — and for almost any *new* project wanting an embedded LSM, [rocksdb](rocksdb.md) is the better-maintained, more capable descendant. The single biggest gotcha: default writes are **not** fsynced, so a power loss can silently drop your last writes unless you set `sync=true` (and pay the ~1000x latency cost) or batch carefully.

## Sources
- [LevelDB GitHub repository (README)](https://github.com/google/leveldb)
- [LevelDB documentation (doc/index.md)](https://github.com/google/leveldb/blob/main/doc/index.md)
- [LevelDB options.h (sync/compression/comparator options)](https://github.com/google/leveldb/blob/main/include/leveldb/options.h)
- [Database of Databases — LevelDB](https://dbdb.io/db/leveldb)
- [Wikipedia — LevelDB](https://en.wikipedia.org/wiki/LevelDB)
