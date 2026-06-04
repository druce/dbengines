---
name: Oracle Berkeley DB
slug: oracle-berkeley-db
rank: 149
data_model: Key-value (embedded)
license: AGPLv3 (copyleft) / commercial dual license — relicensed from Sleepycat in 2013
summary: Venerable embedded transactional key-value library that links into your process; powerful but a 2013 AGPL relicensing made it radioactive for most new use.
last_researched: 2026-06-04
confidence: high
---

# Oracle Berkeley DB

> A 30-year-old embedded ACID key-value storage library (B-tree/hash/queue/recno) that runs inside your application process — technically solid, but the 2013 switch from the permissive Sleepycat license to AGPLv3 effectively killed it for new open-source adoption.

## When to use

**Use Oracle Berkeley DB if:**
- ✅ You already depend on it and need an in-process ACID key-value engine with no separate DB server
- ✅ You need mature B-tree/hash/queue/recno access methods with serializable 2PL isolation (or opt-in MVCC snapshots)
- ✅ You can accept AGPLv3 obligations or will buy a commercial Oracle license

**Avoid Oracle Berkeley DB if:**
- ❌ You're starting fresh and want permissive licensing — the 2013 Sleepycat→AGPLv3 switch can force your whole linking application open or into a paid Oracle contract
- ❌ You need SQL/ad-hoc queries, horizontal write scaling, or a multi-tenant network database ([postgresql](postgresql.md), [redis](redis.md), [etcd](etcd.md))
- ❌ You want a modern permissive embedded KV — pick [sqlite](sqlite.md), [rocksdb](rocksdb.md), or [leveldb](leveldb.md) instead
- ❌ Your team won't operate log/checkpoint internals — unmanaged transaction logs silently fill the disk

## Identity
- **Taxonomy / data model:** [Embedded](../concepts/embedded-databases.md) ordered/unordered **key-value** store. Keys and values are opaque byte strings; no native schema or query language. A SQL layer (a fork of SQLite's API/parser on top of the BDB storage engine) and an XML layer (Berkeley DB XML, XQuery) exist as separate products.
- **Storage model:** Disk-backed pages with an in-memory buffer pool (Mpool, LRU). Multiple **access methods**: **B-tree** (sorted, range scans — see [lsm-vs-btree](../concepts/lsm-vs-btree.md)), **Hash** (linear hashing for exact-match), **Queue** (fixed-length records, FIFO), and **Recno** (record-number/variable-length sequential). Not an LSM engine — it is a classic page/B-tree store.
- **Workload:** OLTP-style embedded point and range access at library speed. Not analytical, not [HTAP](../concepts/oltp-olap-htap.md). There is no server, planner, or network protocol unless the application builds one.

## Distribution & consistency
- **CAP under partition:** When run with the optional High Availability (replication) feature, BDB is a **single-master** group and behaves **CP-leaning** — only the master accepts writes, and on master failure a **majority-quorum election** (a custom protocol based on log recency, then site priority — *not* Paxos) picks a new master ([BDB Reference Guide: Elections](https://docs.oracle.com/cd/E17276_01/html/programmer_reference/rep_elect.html)). Default standalone use is single-node, so CAP is N/A. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under HA, **else-case** consistency is **application-tunable**: synchronous ack of all/quorum replicas gives strong consistency at latency cost; relaxed acks let clients lag by an app-controlled amount (PA/EL when relaxed, PC/EC when fully synchronous) ([Oracle BDB HA](https://www.oracle.com/technical-resources/articles/database/berkeleydb-high-availability.html)).
- **Default isolation & what's achievable:** Locking is **two-phase locking** with a conflict matrix, yielding **serializable** isolation by default ([dbdb.io](https://dbdb.io/db/berkeley-db)). Lower degrees (read-committed / degree 2, read-uncommitted / degree 1) are selectable per cursor/transaction. **Snapshot isolation** is available via **[MVCC](../concepts/mvcc.md)** (DB_MULTIVERSION), which needs a larger cache. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-leader log-shipping. Master ships transaction-log records to clients; clients are read-only. Configurable sync/async acknowledgement; majority-quorum election on failover (custom log-recency/priority protocol, not Paxos) ([BDB Reference Guide: Elections](https://docs.oracle.com/cd/E17276_01/html/programmer_reference/rep_elect.html)). See [replication-models](../concepts/replication-models.md). Split-brain is mitigated by the election quorum (recommend ((N/2)+1) participants), but durability of un-acked writes depends on the chosen ack policy.
- **Tunable consistency?** Yes — degree of consistency and durability are set per deployment (number of acking replicas, sync vs async).
- **Clock dependency:** No reliance on synchronized physical clocks for correctness; ordering comes from the log sequence (LSNs) and the majority-quorum election protocol. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** The core store is schemaless — keys/values are byte arrays and any structure lives in application code. The SQL/XML add-on layers impose their own schema models.
- **Migration/evolution:** No DDL in the core; "migration" means re-serializing application data. The SQL layer follows SQLite-style schema semantics.
- **Type system:** None natively (bytes only). Secondary indexes are supported by registering an app-provided key-extractor callback; the library maintains the secondary B-tree. No native JSON/geospatial/vector types.

## Query interface
- **Language:** **API-only** (C, with C++, Java, and many language bindings). Native operations are get/put/del/cursor over a chosen access method. Optional **SQL** via the BDB SQL product (SQLite-compatible API) and **XQuery** via Berkeley DB XML.
- **Transactions:** Full **multi-statement ACID** transactions across the five subsystems (cache, datastore, locking, logging, recovery) with write-ahead logging and undo/redo recovery ([dbdb.io](https://dbdb.io/db/berkeley-db)). Also usable in non-transactional "Data Store" and "Concurrent Data Store" modes for lighter weight.
- **Native vs app-side:** Secondary indexes are native (callback-driven). **Joins, aggregations, window functions are app-side** in core BDB; only the SQL layer adds relational query processing.
- **Stored procedures / UDFs:** None in core. (SQL layer inherits SQLite's function model.)

## Scaling & topology
- **Vertical vs horizontal:** Primarily **vertical** — it scales with the host's CPU/RAM/disk. HA replication adds read fan-out and failover, not write sharding.
- **Sharding:** **No automatic sharding or partitioning.** Any horizontal partitioning is built by the application across multiple environments. Resharding is entirely an app concern.
- **Read replicas:** Replicas serve reads; their freshness depends on the configured consistency degree (may be stale under async). Reads can be served by any node, master or client ([Oracle BDB HA](https://www.oracle.com/technical-resources/articles/database/berkeleydb-high-availability.html)).
- **Storage/compute separation:** No — storage and compute are co-located in the embedding process. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Write-ahead log with configurable fsync/durability. `DB_TXN_NOSYNC` / `DB_TXN_WRITE_NOSYNC` trade durability for throughput (committed transactions may be lost on crash within the un-synced window); fully synchronous commit closes the data-loss window at latency cost. Group commit is supported. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** In-process library calls avoid network/IPC overhead, giving very low latency for point ops; throughput is bounded by lock contention, cache hit rate, and fsync policy. p99 is sensitive to checkpoint/log-flush activity and to deadlock-retry under heavy 2PL contention.
- **Compaction / vacuum / GC:** B-tree pages can fragment; an explicit **compact** operation reclaims space. **Log files accumulate** and must be removed via checkpointing + log archival (`db_archive`); forgetting this is a classic operational footgun that fills the disk.

## Operations & maturity
- **Backup/restore, PITR:** Hot backup via checkpoint + copying data files and required logs; **point-in-time recovery** by replaying archived logs. Catastrophic recovery (`db_recover -c`) replays from full log history.
- **Observability:** `db_stat` exposes cache, lock, log, and txn statistics; verbose logging and deadlock detector reporting are available. No EXPLAIN in core (it's not a query engine); the SQL layer offers SQLite-style plan inspection.
- **Upgrade story:** Library upgrade plus possible on-disk log/format upgrade; major versions can require a dump/reload or environment recovery. Day-2 burden centers on log management, cache sizing, deadlock tuning, and recovery drills — it's a library you must operate correctly, not a managed service.
- **Maturity:** Extremely mature (originated late 1980s/early 1990s at UC Berkeley; Sleepycat; Oracle since 2006). Embedded in countless systems historically (OpenLDAP, Subversion, Postfix, early Bitcoin Core wallet, MySQL's old BDB engine). **No public Jepsen report.** ⚠️ unverified — no formal verification or Jepsen analysis of the HA/replication safety properties is known to exist.

## Ecosystem & people
- **Canonical use cases:** Embedded persistence for applications/appliances needing local ACID KV storage without a separate DB server; metadata stores, caches with durability, message queues (Queue access method), LDAP/mail backends.
- **Anti-patterns:** New projects wanting permissive licensing (AGPL contagion — see Licensing); anything needing SQL/ad-hoc queries, horizontal write scaling, or a multi-tenant network database (use [postgresql](postgresql.md), [mysql](mysql.md), or a distributed KV like [redis](redis.md)/[etcd](etcd.md)/foundationdb); teams unwilling to operate log/recovery internals. For a modern embedded KV many now choose [rocksdb](rocksdb.md) or [sqlite](sqlite.md).
- **Drivers/connectors:** Language bindings (C/C++/Java/Python/etc.). No first-class CDC/Kafka/dbt/BI ecosystem — it sits below those tools. The SQLite-compatible SQL layer can reuse some SQLite tooling.
- **Community:** Declining. Active OSS uptake fell sharply after the 2013 relicensing; Debian and others moved away. Commercial support available from Oracle. Docs are thorough but dated; learning curve is steep because correctness (locking, recovery, log mgmt) is the developer's responsibility.

## Licensing & cost
- **OSS license & flavor:** **AGPLv3** (strong copyleft) since BDB 6.0 in **2013**, relicensed by Oracle **from the permissive Sleepycat license** ([Wikipedia](https://en.wikipedia.org/wiki/Berkeley_DB); [Slashdot](https://developers.slashdot.org/story/13/07/05/1647215/oracle-quietly-switches-berkeleydb-to-agpl)). Because BDB links into your application, AGPL's network-use copyleft can attach to the whole linking application — the central reason adoption cratered. Versions before 6.0 remain under Sleepycat. See [license-taxonomy](../concepts/license-taxonomy.md). ⚠️ unverified — exact current default license tags on Oracle's distribution (AGPLv3 vs Apache 2.0 for some components) vary by source; treat the binding terms as AGPLv3 unless a commercial license is purchased.
- **Self-managed vs managed-only:** Self-managed library; **no Oracle-managed cloud service.**
- **Lock-in:** Low API lock-in for core KV, but the AGPL/commercial dual-license is itself the lock-in lever — proprietary use requires a paid Oracle license (historically ~$900–$13,800+ per processor) ([Meshed Insights](https://meshedinsights.com/2013/07/05/a-change-in-license-for-berkeley-db/)).
- **Cost model:** Free under AGPL (with copyleft obligations) or per-processor commercial license for closed-source use.

## Hardware / deployment
- **Resource profile:** Performance is dominated by **cache (RAM) hit rate**; the working set should ideally fit in the buffer pool. CPU cost rises with lock contention; disk I/O with log fsync and checkpoints.
- **Storage assumptions:** Local disk; benefits strongly from fast/NVMe storage for the log. Not designed around network-attached storage latency.
- **Footprint:** **Embedded library** linked into a single process (single-node), optionally a replicated HA group. No daemon, no embedded analytics — small, but you own the operational complexity.
- **Deployment:** On-prem / embedded in your binary. No SaaS; k8s use is just "ship it inside your container," with the usual StatefulSet caveats for the data/log volumes.

## Bottom line
Reach for Oracle Berkeley DB only if you already depend on it, need an in-process ACID KV engine with mature B-tree/hash/queue access methods, and either accept AGPLv3 or will buy a commercial license. Everyone else starting fresh should pick a permissively licensed embedded engine ([sqlite](sqlite.md), [rocksdb](rocksdb.md), [leveldb](leveldb.md)) instead. The single biggest gotcha is licensing: AGPLv3 linking contagion (from the 2013 Sleepycat→AGPL switch) can force your entire application open or into a paid Oracle contract — closely followed by the operational footgun of unmanaged transaction logs filling the disk.

## Sources
- [Berkeley DB — Database of Databases (dbdb.io)](https://dbdb.io/db/berkeley-db)
- [Oracle Berkeley DB Storage Layer](https://www.oracle.com/technical-resources/articles/database/oracle-berkeley-db-storage-layer.html)
- [Oracle Berkeley DB Replication for Highly Available Data](https://www.oracle.com/technical-resources/articles/database/berkeleydb-high-availability.html)
- [Berkeley DB Replication — Programmer's Reference (docs.oracle.com)](https://docs.oracle.com/cd/E17276_01/html/programmer_reference/rep.html)
- [Berkeley DB — Wikipedia](https://en.wikipedia.org/wiki/Berkeley_DB)
- [Oracle Quietly Switches BerkeleyDB To AGPL — Slashdot](https://developers.slashdot.org/story/13/07/05/1647215/oracle-quietly-switches-berkeleydb-to-agpl)
- [A Change in License for Berkeley DB — Meshed Insights](https://meshedinsights.com/2013/07/05/a-change-in-license-for-berkeley-db/)
