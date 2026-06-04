---
name: Kdb
slug: kdb
rank: 51
data_model: Time-series / columnar (multi-model)
license: Proprietary commercial (KX); free Personal Edition + KDB-X Community Edition
summary: Column-oriented time-series database fused with the q array language; the dominant engine for high-frequency financial tick data, blazing on ordered columnar scans but proprietary, idiosyncratic, and weak on classic transactional guarantees.
last_researched: 2026-06-04
confidence: medium
---

# Kdb

> The de facto standard for capital-markets tick data: a columnar, in-memory-first time-series store welded to the terse q/APL-family language, optimized for ordered, time-ordered analytics rather than concurrent OLTP.

## When to use

**Use Kdb if:**
- ✅ You must capture and analyze massive volumes of time-ordered data (especially market tick data) at microsecond query latencies
- ✅ You need fast `asof`/window joins and aggregations over ordered columnar time-series data
- ✅ You can afford both the commercial license and specialized q talent
- ✅ Your domain is HFT/quant/TCA/surveillance, or other high-frequency time-series (telco, IoT, energy, telemetry)

**Avoid Kdb if:**
- ❌ Its "high availability" and "durability" are things you assemble from tickerplant logs and redundant consumers — there is no built-in replication/consensus
- ❌ You need general-purpose OLTP, multi-statement ACID/rollback, or MVCC (none exist — single-threaded, single-writer, append-no-undo)
- ❌ You need JSON/document workloads, standard ANSI SQL, an open-source stack, or commodity hiring (q is steep and scarce)

## Identity
- **Taxonomy / data model:** Column-oriented relational [oltp-olap-htap](../concepts/oltp-olap-htap.md) time-series database; multi-model in the sense that it natively carries tables, dictionaries, lists, and nanosecond timestamps as first-class types ([KX kdb+](https://kx.com/products/kdb/), [Wikipedia](https://en.wikipedia.org/wiki/Kdb+)). It is inseparable from **q**, a vector/array language in the APL/K lineage created by Arthur Whitney; the database and the language are the same product.
- **Storage model:** Columnar throughout. In-memory tables hold ordered columns; on-disk data uses **splayed** tables (one file per column) usually **partitioned by date**, memory-mapped at query time ([Partitioning data in kdb+](https://kx.com/blog/partitioning-data-in-kdb/), [HDB docs](https://code.kx.com/q/learn/startingkdb/hdb/)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — there is no LSM tree and no B-tree; the on-disk format is flat per-column files, and primary "indexing" is the physical sort order plus partition pruning. See [columnar-storage](../concepts/columnar-storage.md), [time-series-storage](../concepts/time-series-storage.md).
- **Workload:** Primarily OLAP/analytical on time-ordered data, with a real-time ingest tier that makes it feel HTAP. The HTAP behavior is achieved by **physical tiering, not a single engine doing both**: a Real-Time Database (RDB) holds today's data in RAM while a Historical Database (HDB) memory-maps prior days from disk ([Tick architecture](https://kx.com/blog/tick-architecture-simplicity-and-speed-the-kdb-way/)). It is not a general-purpose OLTP system.

## Distribution & consistency
- **CAP under partition:** Largely **N/A as a distributed consensus system** — core kdb+ is a single-node engine; multi-node "tick" deployments are an assembly of processes (tickerplant, RDB, HDB, gateways) connected by IPC, not a quorum-replicated cluster. There is no built-in [consensus-raft-paxos](../concepts/consensus-raft-paxos.md); HA is achieved by running redundant independent copies fed by the same publisher ([disaster recovery](https://code.kx.com/q/wp/disaster-recovery/)). Closest characterization: a CP-ish single-writer pipeline where availability depends on operator-built redundancy. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Not meaningfully applicable to a single-process store. In the standard pub/sub tick topology, the tickerplant is the single ordering point; subscribers (RDB, HDB-feeders) receive the same ordered stream, so there is no multi-master reconciliation. ⚠️ unverified — formal PACELC classification; KX does not frame the product in CAP/PACELC terms.
- **Default isolation & what's achievable:** kdb+ runs **single-threaded by default**, executing messages in arrival order, which gives serial, race-free updates without a traditional transaction manager ([multi-threading WP](https://code.kx.com/q/wp/multi-thread/)). It does **not** provide multi-statement ACID transactions, rollback, or [mvcc](../concepts/mvcc.md)/snapshot isolation in the RDBMS sense. "Consistency" here means deterministic serial execution, not [isolation-levels](../concepts/isolation-levels.md) guarantees — do not read kdb+ as an ACID OLTP database. ⚠️ unverified — there is no documented BEGIN/COMMIT/ROLLBACK or savepoint mechanism; treat writes as append-with-no-undo.
- **Replication:** No native leader/follower replication protocol. Durability and recovery rest on the **tickerplant log** (a sequential journal of every published message) which can be **replayed** to rebuild an RDB or roll into the HDB ([logging/recovery/replication KB](https://code.kx.com/q/kb/logging/)). "Replication" in practice = run a second consumer reading the same tickerplant feed/log. See [replication-models](../concepts/replication-models.md), [wal-and-durability](../concepts/wal-and-durability.md).
- **Tunable consistency?** No per-query consistency levels; the model is single-writer-ordered.
- **Clock dependency:** Correctness does not depend on synchronized distributed clocks (no TrueTime/HLC). Timestamps are application/feed-supplied or stamped by the tickerplant; ordering is by message arrival at the single ordering point. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Tables have fixed, typed columns; you define column types up front. Schemaless ingestion is not the model.
- **Migration/evolution:** Adding or changing columns on splayed/partitioned on-disk tables is a manual, often scripted operation (rewriting per-column files across partitions); there is no online-DDL transaction. ⚠️ unverified — exact locking behavior of in-place schema changes; in practice schema changes on large HDBs are batch maintenance jobs.
- **Type system:** Rich temporal types (date, time, timestamp/nanosecond, timespan, month, minute, second), plus symbols (interned strings), floats/ints/bytes, nested lists, dictionaries, and keyed tables. No native JSON document type or built-in geospatial/vector index in the core engine (KX positions newer products for vector search, but classic kdb+ is not a [vector-search-ann](../concepts/vector-search-ann.md) engine). ⚠️ unverified — current vector-search support in KDB-X variants.

## Query interface
- **Language:** **q** (terse APL-family vector language) is primary; it also exposes **qSQL**, an SQL-like dialect over tables, and **kdb+tick** patterns. q is famously concise and famously unfamiliar — a real learning curve. Not standard ANSI SQL.
- **Transactions:** Effectively **single-message atomicity** via serial execution; **no** multi-statement ACID transactions, no rollback. An update is applied as it executes.
- **Native vs app-side:** Joins (including time-series-specific `aj`/`asof` and window joins), aggregations, and grouping are native and extremely fast on ordered columnar data; window functions and complex analytics are core strengths. Secondary indexes are minimal — performance comes from sort order, partitioning, and the attribute system (e.g. `` `p#``/``g#``/``s#`` grouped/sorted/parted attributes) rather than B-tree indexes.
- **Stored procedures / UDFs:** Everything is q — functions, including server-side logic, are written in q and run in-process; no separate procedural language layer.

## Scaling & topology
- **Vertical first.** kdb+ scales primarily by adding RAM/cores/fast disk to powerful nodes; a single process is extremely efficient per core. Horizontal scaling is **operator-assembled**: split data across HDB processes by date/partition, fan queries through gateway processes, and parallelize with `peach` (parallel-each across secondary threads/processes).
- **Sharding:** Effectively manual — partitioning is by date (and optionally further segmented across storage). There is no automatic resharding/rebalancing service; capacity planning and partition layout are an operational discipline. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** "Replicas" are independent consumers of the same tickerplant feed/log; reads from an RDB reflect intraday data, reads from an HDB reflect finalized prior-day partitions. No cross-replica consensus.
- **Storage/compute separation:** Classic kdb+ is local-disk/memory-mapped. Cloud reference architectures (and newer KDB-X / kdb Insights tiers) layer object storage and separated tiers on top, approximating [storage-compute-separation](../concepts/storage-compute-separation.md), but the core engine assumes fast (ideally local NVMe) attached storage. ⚠️ unverified — degree of native compute/storage separation in current managed offerings.

## Performance & durability
- **Write path:** Ingest is append-oriented through the **tickerplant**, which writes each message to a sequential **log file** before/while publishing to subscribers ([tick architecture](https://kx.com/blog/tick-architecture-simplicity-and-speed-the-kdb-way/), [logging KB](https://code.kx.com/q/kb/logging/)). This log is the durability mechanism — analogous to a [wal-and-durability](../concepts/wal-and-durability.md) journal. **Data-loss window:** anything in memory not yet flushed to the tickerplant log is at risk on crash; the log fsync/flush cadence and whether intraday write-down is used determine the exposure. ⚠️ unverified — default fsync policy of the tickerplant log (commonly tuned; can be per-message or batched, trading latency for durability).
- **Throughput/latency:** Microsecond-to-millisecond query latencies on in-memory ordered columns are the headline strength; ingest handles very high message rates (designed for full market data feeds). p99 is generally excellent for read-heavy analytical workloads because there is no compaction/vacuum/GC churn competing with queries.
- **Compaction / vacuum / GC:** No LSM compaction and no MVCC vacuum. The main periodic operation is the **end-of-day roll**: flush RDB to HDB partitions and clear the in-memory day. q's memory management is reference-counted with manual `.Q.gc[]`; large transient allocations can fragment memory and require explicit GC. ⚠️ unverified — current GC behavior specifics across versions.

## Operations & maturity
- **Backup/restore, PITR:** Backups are filesystem/snapshot-based on the HDB partitions plus the tickerplant logs; PITR is achieved by replaying tickerplant logs up to a chosen point ([disaster recovery WP](https://code.kx.com/q/wp/disaster-recovery/)). Intraday write-down is used to bound log size and shorten replay/recovery time ([intraday write-down WP](https://code.kx.com/q/wp/intraday-writedown/)).
- **Observability:** No turnkey metrics stack; introspection is done in q itself (query timing, memory stats). Slow-query analysis and EXPLAIN-style tooling are limited compared to mainstream RDBMSs — operators instrument in q.
- **Upgrade story:** Version upgrades of the engine binary plus q code; HA topologies allow rolling upgrade of redundant consumer processes. Day-2 burden is real: kdb+ shops typically employ specialized "kdb developers" to maintain feed handlers, tickerplants, gateways, and partition maintenance.
- **Maturity:** Very mature (kdb 1998, 64-bit kdb+ 2003, v4.0 in 2020 added multithreaded primitives and encryption) and battle-tested in production at most major banks and exchanges ([Wikipedia](https://en.wikipedia.org/wiki/Kdb+)). No public **Jepsen** report exists — unsurprising, as it is not marketed as a distributed consensus database. ⚠️ unverified — no Jepsen analysis found.

## Ecosystem & people
- **Canonical use cases:** Capital-markets tick capture and analytics (HFT, quant research, TCA, market surveillance), plus other high-frequency time-series domains — telco, IoT/sensor, energy trading, Formula One telemetry. Anything requiring fast `asof`/window joins over ordered timestamped data.
- **Anti-patterns:** General-purpose OLTP, multi-row ACID transactions, highly concurrent random updates/deletes, document/JSON-centric apps, teams without q expertise, or budget-constrained projects that need an open-source stack. It is the wrong tool when you need standard SQL, mutable transactional records, or commodity hiring.
- **Drivers/connectors:** IPC interfaces and bindings for C, C++, Java, C#, Python (PyKX is the prominent Python bridge); connectors exist for common feeds and BI, but the ecosystem is smaller and more specialized than mainstream databases. dbt/Kafka integrations exist but are niche.
- **Community/support:** Smaller, specialized, finance-heavy community; strong official docs (code.kx.com); commercial support from KX. Learning curve for q is steep; experienced kdb engineers are scarce and well-paid.

## Licensing & cost
- **License:** **Proprietary, source-available-not / closed commercial** — there is no open-source kdb+ ([Wikipedia](https://en.wikipedia.org/wiki/Kdb+)). Free tiers exist: the long-standing **kdb+ Free Personal Edition** (non-commercial, on-demand license check, capped cores, no cloud) and the newer **KDB-X Community Edition** (announced Nov 2025), which is free for personal *and commercial* use but capped (up to 16GB RAM, 4 secondary threads, and 16 connections per q process, limited to a single physical/virtual instance) ([KX KDB-X](https://kx.com/products/kdb-x/), [BusinessWire 2025](https://www.businesswire.com/news/home/20251119593382/en/), [licensing docs](https://code.kx.com/q/learn/licensing/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-managed core engine, plus KX cloud/managed offerings (kdb Insights / KDB-X tiers). Lock-in is significant: q is a unique language and the data layout/tooling are KX-specific.
- **Cost model:** Commercial licensing is negotiated with KX (historically per-core, expensive at scale, pricing not public) — well known as costly for smaller organizations. The free editions lower the entry barrier but are capacity-limited. ⚠️ unverified — current commercial pricing structure (KX does not publish it).

## Hardware / deployment
- **Resource profile:** Memory- and I/O-bound. The RDB tier wants enough RAM to hold a full day of data; HDB query speed depends heavily on fast storage for memory-mapped column files. CPU matters for analytics but a single core is already very efficient. The hot working set does not all need to fit in RAM (HDB is mmap'd), but intraday RDB data effectively does.
- **Storage assumptions:** Strongly favors **fast local NVMe**; network-attached/object storage works in cloud architectures but adds latency that the engine is sensitive to.
- **Footprint:** Tiny single binary; can run embedded/single-node or as a multi-process tick cluster. No heavyweight runtime.
- **Deployment:** On-prem (traditional in finance) and cloud (AWS/GCP/Azure reference architectures); container/k8s deployment is possible but stateful tick topologies require careful StatefulSet/storage design. ⚠️ unverified — maturity of official k8s operators.

## Bottom line
Reach for kdb+ when you must capture and analyze massive volumes of time-ordered data (especially market tick data) at microsecond query latencies and you can afford both the license and the specialized q talent — nothing in the mainstream beats it at ordered columnar time-series analytics with `asof`/window joins. Do **not** reach for it as a general OLTP database, for transactional integrity (no multi-statement ACID/rollback, no MVCC), for JSON/document workloads, or where an open-source, easy-to-hire-for stack matters. The single biggest gotcha: kdb+ is a single-threaded-by-default, single-writer engine whose "high availability" and "durability" are things *you assemble* from tickerplant logs and redundant consumers — there is no built-in replication/consensus, so resilience is an operator responsibility, not a database feature.

## Sources
- [kdb+ — KX product page](https://kx.com/products/kdb/)
- [kdb+ — Wikipedia](https://en.wikipedia.org/wiki/Kdb+)
- [Tick architecture: simplicity and speed, the kdb+ way (KX)](https://kx.com/blog/tick-architecture-simplicity-and-speed-the-kdb-way/)
- [Partitioning data in kdb+ (KX)](https://kx.com/blog/partitioning-data-in-kdb/)
- [Historical database — Starting kdb+ (KX docs)](https://code.kx.com/q/learn/startingkdb/hdb/)
- [Logging, recovery and replication (KX KB)](https://code.kx.com/q/kb/logging/)
- [Multi-threading in kdb+ (KX WP)](https://code.kx.com/q/wp/multi-thread/)
- [Disaster-recovery planning for kdb+ tick systems (KX WP)](https://code.kx.com/q/wp/disaster-recovery/)
- [RDB intraday write-down solutions (KX WP)](https://code.kx.com/q/wp/intraday-writedown/)
- [Licensing kdb+ (KX docs)](https://code.kx.com/q/learn/licensing/)
- [KDB-X product page (KX)](https://kx.com/products/kdb-x/)
- [KX debuts KDB-X Community Edition (BusinessWire, Nov 2025)](https://www.businesswire.com/news/home/20251119593382/en/)
