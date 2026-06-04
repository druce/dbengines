---
name: RocksDB
slug: rocksdb
rank: 76
data_model: Key-value (embedded)
license: Dual GPLv2 / Apache 2.0 (permissive option)
summary: Embeddable LSM-tree key-value storage engine; the default substrate other databases are built on, not a database you run by itself.
last_researched: 2026-06-04
confidence: high
---

# RocksDB

> An embedded, single-node, ordered key-value storage engine optimized for fast SSD/NVMe — it is the storage layer inside many distributed databases (tikv, [cockroachdb](cockroachdb.md) historically, MyRocks, Kafka Streams), not an end-user database.

## When to use

**Use RocksDB if:**
- ✅ You are *building* a database, queue, or stateful service and need a fast, proven, embeddable LSM key-value engine on SSD/NVMe.
- ✅ You need ordered byte-key point lookups and range scans, with optional snapshot-isolation transactions, embedded in-process.
- ✅ You want a permissively-licensed (Apache 2.0 option) storage substrate and will layer schemas, indexes, replication, and HA yourself.

**Avoid RocksDB if:**
- ❌ You want an application database — it has no SQL, no schema, no server, no replication, and no HA; reach for [postgresql](postgresql.md) or [redis](redis.md) instead.
- ❌ You can't invest in LSM tuning — get compaction wrong and you get write stalls, p99 spikes, and space amplification.
- ❌ You need durable-by-default writes — durability defaults to non-fsync'd (`sync=false`), so a power loss can lose recent commits unless you set `WriteOptions` deliberately.

## Identity
- **Taxonomy / data model:** embedded key-value store. Keys and values are arbitrary byte streams; keys are kept sorted, so it supports point lookups and ordered range scans ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)). Forked from LevelDB. No relational, document, or graph model — those are built *on top of* RocksDB by other systems. See [embedded-databases](../concepts/embedded-databases.md).
- **Storage model:** [LSM-tree](../concepts/lsm-vs-btree.md). Write path = MemTable (in-memory skiplist) → Write-Ahead Log → flush to immutable Level-0 SST (Sorted String Table) files → background compaction merges SSTs across levels ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)). Block-based on-disk SST format with configurable compression (Snappy/LZ4/Zstd) and Bloom filters. Optimized for write-heavy workloads and SSDs. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP-style point/range access embedded into a host application; not an analytics engine. Not HTAP — it is a single-node storage primitive. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Column families:** a DB can be partitioned into named column families, each its own LSM-tree (separate MemTable, compaction config) but sharing one WAL so cross-family writes stay atomic ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)).

## Distribution & consistency
- **CAP / PACELC:** N/A — single-node, in-process library. RocksDB is **not replicated and not distributed**; it provides "helper functions to enable users to implement their replication system" but ships none ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)). Distribution, consensus, and CAP behavior live in the *host* system (e.g. tikv wraps it with [Raft](../concepts/consensus-raft-paxos.md)). See [cap-pacelc](../concepts/cap-pacelc.md), [replication-models](../concepts/replication-models.md).
- **Default isolation & what's achievable:** with the optional Transaction API, RocksDB supports **snapshot isolation** via monotonically increasing per-write sequence numbers; a snapshot read sees only keys with sequence ≤ snapshot ([RocksDB Transactions wiki](https://github.com/facebook/rocksdb/wiki/Transactions)). Both **pessimistic** (lock-based, point and range locks via a pluggable LockManager) and **optimistic** (commit-time conflict detection against the MemTable) transaction modes exist. The default write policy for pessimistic transactions is *WriteCommitted* — data enters the MemTable/WAL only at commit ([RocksDB Transactions wiki](https://github.com/facebook/rocksdb/wiki/Transactions), [WritePrepared Transactions](https://rocksdb.org/blog/2017/12/19/write-prepared-txn.html)). ⚠️ unverified — exact serializable guarantees depend on which lock mode and write policy the embedder configures; without transactions, a bare `Put`/`Write` gives only batch atomicity, not multi-statement isolation. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Tunable consistency:** N/A at the engine level (single node).
- **Clock dependency:** none — ordering is by internal sequence numbers, not wall-clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** RocksDB has no schema, no types — values are opaque bytes. Any structure (rows, secondary indexes, encoding) lives in the application/host database. Key ordering is the only built-in structure (lexicographic by default, or a custom comparator).
- **Migration/DDL:** N/A — no schema to alter. Column families can be created/dropped online.
- **Type system:** none beyond `byte[]` keys and values. The `Merge` operator allows custom read-modify-write semantics (e.g. counters) defined in host code.

## Query interface
- **Language:** API-only — no SQL, no query language. C++ core with bindings for Java (RocksJava), and third-party C, Rust, Go, Python bindings. Operations: `Get`/`MultiGet`, `Put`, `Delete`, `Merge`, atomic `Write` (WriteBatch), `Iterator` (range scans), and `Snapshot` ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)).
- **Transactions:** optional multi-key ACID transactions (pessimistic/optimistic, see above). A bare `WriteBatch` is atomic-all-or-nothing but not isolated. No transactions across multiple RocksDB instances.
- **Native vs app-side:** no joins, no secondary indexes, no aggregations, no server-side query execution — all of that is the embedder's responsibility. This is the whole point: RocksDB does storage; the host does the database.
- **Stored procedures / UDFs:** none, except the user-supplied comparator, merge operator, and compaction filter (C++/Java callbacks).

## Scaling & topology
- **Vertical only** within a single process/host. There is no built-in sharding, no horizontal scaling, no read replicas — RocksDB scales by the host system layering partitioning and replication above it.
- **Sharding/partitioning:** N/A in-engine.
- **Read replicas:** N/A.
- **Storage/compute separation:** the upstream engine is local-disk only. Variants like rocksdb-cloud (Rockset) and remote-storage forks add object-storage backing, but that is not core RocksDB. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** every write optionally goes to the WAL before the MemTable; the WAL flag and fsync are controlled **per write** via `WriteOptions` ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)). By default `sync=false`: writes are durable to the OS page cache but **not fsync'd**, so a power loss can lose recently committed data up to the WAL flush window. Setting `WriteOptions.sync=true` fsyncs each commit (much slower); group/batch commit amortizes fsync cost across concurrent writers. Disabling the WAL entirely (`disableWAL`) trades all crash durability for throughput. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** excellent write throughput and low write amplification-tuned-vs-read-amplification tradeoffs typical of [LSM trees](../concepts/lsm-vs-btree.md); fast point reads via Bloom filters and block cache.
- **Compaction / GC and p99:** the classic LSM gotcha — background compaction competes for disk I/O and CPU and causes **read/write/space amplification and p99 latency spikes and write stalls** when L0 files accumulate or compaction falls behind. Tuning (compaction style: leveled vs universal vs FIFO, rate limiter, level sizes) is the dominant operational task. Tombstones from deletes persist until compacted, slowing range scans over deleted keys.

## Operations & maturity
- **Backup/restore:** built-in `BackupEngine` API plus checkpoints (hard-link snapshots of a DB); PITR is up to the host via WAL archiving ([RocksDB Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)).
- **Observability:** rich Statistics, per-operation counters, `GetProperty` introspection (compaction state, MemTable usage, level sizes), and perf/IO context. No query planner (no queries). LOG file for compaction/flush events.
- **Upgrade story:** it is a linked library — you upgrade by relinking the host binary; SST/WAL formats are forward/backward compatible within documented bounds. No rolling-upgrade concept at the engine level; that is the host's concern.
- **Maturity:** very high. Battle-tested at Meta scale and embedded in tikv, MyRocks (MySQL/MariaDB storage engine), Kafka Streams/ksqlDB state stores, Apache Flink (FRocksDB fork), [cockroachdb](cockroachdb.md) (used Pebble — a Go reimplementation — to replace it), Ceph BlueStore, and many others. **No Jepsen report applies directly** — RocksDB is a single-node engine, so Jepsen testing targets the distributed systems built on it, not RocksDB itself. Known failure modes: write stalls, compaction backlog, large WAL replay on crash recovery, and mis-tuning leading to space blowup.

## Ecosystem & people
- **Canonical use cases:** the embedded storage layer for a distributed database, message queue, or stream processor; local persistent state/caches; metadata stores; anything needing a fast, embeddable, ordered KV store on SSD. The single most common pattern is "I'm building a database and need a proven storage engine."
- **Anti-patterns:** using RocksDB *directly* as your application database — you will reinvent schemas, indexes, queries, replication, and HA. If you want a usable KV server, reach for [redis](redis.md) or a RocksDB-backed product. If you want SQL, use [postgresql](postgresql.md)/MyRocks. Heavy delete-then-scan workloads and very large values stress LSM compaction; analytics belongs in a columnar engine.
- **Drivers / connectors:** RocksJava, C/C++ API, plus community Rust (`rust-rocksdb`), Go (`gorocksdb`), Python (`python-rocksdb`) bindings. No native CDC/Kafka/dbt/BI integration — those live at the host layer.
- **Community / support:** large open-source community led by Meta; extensive wiki docs (the best primary source) though tuning knowledge has a steep learning curve. No single vendor SLA; commercial forks/products (Speedb, Rockset cloud) offer support.

## Licensing & cost
- **License:** **dual-licensed GPLv2 + Apache 2.0** since July 2017, when Meta migrated off the controversial BSD+Patents license to enable Apache Software Foundation adoption ([RocksDB README](https://github.com/facebook/rocksdb/blob/main/README.md)). The Apache 2.0 option makes it permissively usable — no source-available/SSPL/BSL restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed:** it is a library — you embed and self-manage it; there is no managed RocksDB service (you'd consume a product that embeds it).
- **Lock-in:** low at the license level; moderate at the operational level (tuning expertise, SST format). Note the existence of API-compatible reimplementations like Pebble (Go) and Speedb that ease migration.
- **Cost model:** free; cost is the engineering time to embed, tune, and operate it.

## Hardware / deployment
- **Resource profile:** disk-bound and memory-sensitive — block cache + MemTables + Bloom filters want RAM; compaction is CPU- and I/O-heavy. Working set need not fit in RAM (data lives on disk), but a too-small block cache hurts read p99.
- **Storage assumptions:** designed for **fast local SSD/NVMe**; LSM write patterns and compaction are far less friendly on spinning disks or high-latency network storage.
- **Footprint:** **embedded, in-process, single-node** — no daemon, no network port. Runs wherever the host process runs.
- **Deployment:** ships as part of the host application; container/k8s realities are entirely those of the embedding system. Persistent local volume required.

## Bottom line
Reach for RocksDB when you are **building** a database, queue, or stateful service and need a fast, proven, embeddable LSM key-value engine on SSD — it is the de facto storage substrate of the industry. Do **not** reach for it as your application's database: it has no SQL, no schema, no server, no replication, and no HA — you must build all of that yourself. The biggest gotcha is compaction: get the [LSM](../concepts/lsm-vs-btree.md) tuning wrong and you get write stalls, p99 spikes, and space amplification, and durability defaults to non-fsync'd (`sync=false`), so set [WriteOptions](../concepts/wal-and-durability.md) deliberately.

## Sources
- [RocksDB Overview (official wiki)](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)
- [RocksDB Transactions (official wiki)](https://github.com/facebook/rocksdb/wiki/Transactions)
- [WritePrepared Transactions (official wiki)](https://github.com/facebook/rocksdb/wiki/WritePrepared-Transactions)
- [WritePrepared Transactions blog](https://rocksdb.org/blog/2017/12/19/write-prepared-txn.html)
- [RocksDB README / license](https://github.com/facebook/rocksdb/blob/main/README.md)
- [RocksDB - Wikipedia](https://en.wikipedia.org/wiki/RocksDB)
- [Database of Databases — RocksDB](https://dbdb.io/db/rocksdb)
