---
name: Redis
slug: redis
rank: 8
data_model: Key-value (multi-model)
license: Tri-license since Redis 8 (May 2025) — AGPLv3 (OSI) plus RSALv2/SSPLv1 (source-available); see [license-taxonomy](../concepts/license-taxonomy.md)
summary: In-memory data-structure server; the default cache and ephemeral KV store, but not a strongly-consistent database.
last_researched: 2026-06-04
confidence: high
---

# Redis

> The de facto in-memory key-value/data-structure server — blisteringly fast for caching, queues, and ephemeral state, but its async replication and best-effort durability mean you should not treat it as a system of record.

## Identity
- **Taxonomy / data model:** Primarily key-value, but really a *data-structure server* — values are typed (strings, hashes, lists, sets, sorted sets, streams, bitmaps, HyperLogLog, geospatial, and vector sets). With modules now folded into core Redis 8 (JSON, Time Series, probabilistic types, and the Redis Query Engine for full-text + vector search), it is genuinely [multi-model](../concepts/multi-model.md). See also [vector-search-ann](../concepts/vector-search-ann.md), [full-text-search](../concepts/full-text-search.md), [time-series-storage](../concepts/time-series-storage.md).
- **Storage model:** In-memory primary store (the entire dataset must fit in RAM), with optional on-disk persistence via RDB point-in-time snapshots and/or AOF (append-only file) command logging. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — it is a hash-table/skiplist memory engine, with disk used only for durability/restart.
- **Workload:** OLTP-adjacent, but specifically low-latency point operations and simple range/set ops. Not OLAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Single-threaded command execution for the data path (I/O is multi-threaded since 6.0), so per-key operations are atomic without locking.

## Distribution & consistency
- **CAP under partition:** Effectively **AP/CP-ish-but-neither-strictly** — Redis is *not* a CP system. With default async replication, a primary keeps serving and acknowledges writes before replicas confirm, so a failover can silently drop acknowledged writes. ([Redis WAIT docs](https://redis.io/commands/wait): WAIT "does not turn a set of Redis instances into a CP system... acknowledged writes can still be lost during a failover"). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition (P) it favors **availability** (A) — the old primary may keep accepting writes until a replica is promoted, risking divergence/split-brain. Else (E) it favors **latency** (L) over consistency — writes return before replication.
- **Default isolation & what's achievable:** No transaction isolation levels in the SQL sense. `MULTI`/`EXEC` provides **atomic, serially-executed batches** (no rollback on logical errors; not real ACID transactions). Lua scripts and functions run atomically. Calling this "ACID" overstates it — there is no isolation/durability guarantee equivalent to a relational DB. See [isolation-levels](../concepts/isolation-levels.md). No [mvcc](../concepts/mvcc.md).
- **Replication:** Single-leader, **asynchronous by default**. `WAIT n timeout` blocks until *n* replicas ack, improving (but not guaranteeing) durability — a synchronously-acked write can still be lost on failover ([Redis docs](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)). High availability via **Sentinel** (monitors + promotes) or **Redis Cluster** (sharded, gossip-based). Split-brain is a real failure mode during partitions. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Coarsely: `WAIT`, `min-replicas-to-write`, and AOF `appendfsync` policy. No per-query quorum levels like Dynamo/Cassandra.
- **Clock dependency:** No correctness dependence on synchronized clocks; failover is timeout/quorum-based via Sentinel/Cluster, not [clocks-and-time](../concepts/clocks-and-time.md)-based.

## Schema
- **Schema model:** Schemaless — keys are opaque, value structure lives in application code. The Redis Query Engine adds explicit secondary indexes (`FT.CREATE`) over hash/JSON fields, which is the closest thing to a schema.
- **Migration/evolution:** No DDL, no `ALTER`. Data shape changes are an application concern. Cluster reshard moves hash slots online (with some operational care).
- **Type system:** Rich native value types (see Identity). Native JSON (RedisJSON), vectors (vector sets / HNSW via Query Engine), geospatial, time series, and probabilistic structures (Bloom/Cuckoo/Count-Min/Top-K).

## Query interface
- **Language:** Redis command protocol (RESP) via `GET`/`SET`/etc. — **API-only**, no SQL. DSLs exist for sub-features: `FT.SEARCH` (query engine), `TS.*` (time series), `JSON.*`.
- **Transactions:** `MULTI`/`EXEC` (atomic batch, optimistic locking via `WATCH`), Lua scripting, and Functions — all single-row/single-shard atomic. **No** multi-statement ACID with rollback; no cross-shard transactions in Cluster mode.
- **Native vs app-side:** No joins. Secondary indexes, full-text search, aggregations, and vector KNN exist only via the Query Engine; otherwise lookups are by key and you design access patterns up front.
- **Stored procedures / UDFs:** Lua scripts (`EVAL`) and Redis Functions (Lua). Modules can be written in C.

## Scaling & topology
- **Vertical vs horizontal:** Vertical first (RAM-bound). Horizontal via **Redis Cluster**, which shards keys across **16384 hash slots** (`slot = CRC16(key) mod 16384`). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding:** Auto-distributed across slots; resharding moves slots between nodes and can be done live but requires operational attention. Multi-key ops must share a slot (use hash tags `{...}`) or they error.
- **Read replicas:** Yes; reads from replicas are **asynchronous → possibly stale** (eventual). `WAIT` does not make replica reads linearizable.
- **Storage/compute separation:** No — compute and (in-memory) storage are co-located per node. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) architecture (contrast Aurora/Neon).

## Performance & durability
- **Write path:** RAM-first. Durability is **optional and best-effort**. AOF with `appendfsync everysec` (default-ish when AOF on) means a crash can lose ~1 second of writes; `appendfsync always` is durable per-op but much slower; RDB snapshots lose everything since the last snapshot. See [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window on crash: up to ~1s (AOF everysec), or a full snapshot interval (RDB), or unbounded if persistence is off** (common for pure-cache deployments).
- **Throughput/latency:** Sub-millisecond p50 for point ops; very high ops/sec single-node. Tail (p99) is hurt by: single-threaded blocking commands (`KEYS`, large `SMEMBERS`, big Lua), fork-based RDB/AOF-rewrite (copy-on-write memory spikes + latency blips), and synchronous `DEL` of huge keys (mitigate with `UNLINK`/lazy-free).
- **Compaction/GC:** No LSM compaction. AOF rewrite compacts the log (forks a child). Eviction under `maxmemory` uses configurable policies (LRU/LFU/random/TTL); active expiration is sampled + lazy, so expired keys can transiently linger.

## Operations & maturity
- **Backup/restore, PITR:** RDB snapshots for backups; AOF for finer recovery. No built-in continuous PITR in OSS (managed offerings layer it on).
- **Observability:** `INFO`, `MONITOR`, `SLOWLOG`, `LATENCY` tooling, keyspace notifications, `MEMORY DOCTOR`. No query planner (no SQL); `FT.EXPLAIN` exists for query-engine queries.
- **Upgrade story:** Rolling upgrades possible in Sentinel/Cluster setups; single-node implies a restart (reload from RDB/AOF). Day-2 burden centers on memory management, eviction tuning, fork latency, and failover testing.
- **Maturity:** Extremely mature, ubiquitous since 2009. **Jepsen tested Redis-Raft** (an experimental strong-consistency module, never released): the early build was "essentially unusable" with stale reads, split-brain, and total data loss on failover; most issues were fixed in later dev builds but the module shipped at most experimentally ([Jepsen: Redis-Raft 1b3fbf6](https://jepsen.io/analyses/redis-raft-1b3fbf6)). Core Redis was never claimed to be linearizable; the well-known failure mode is **lost acknowledged writes during failover** under async replication.

## Ecosystem & people
- **Canonical use cases:** Caching (cache-aside, read-through), session stores, rate limiting, leaderboards (sorted sets), pub/sub, job queues (Streams, lists), real-time counters, ephemeral feature stores, and increasingly vector/semantic caching for LLM apps.
- **Anti-patterns:** System of record / source of truth for data you cannot afford to lose; datasets larger than RAM (cost explodes); analytical queries, complex joins, or strong-consistency transactional workloads — reach for [postgresql](postgresql.md) or a CP store instead.
- **Drivers/connectors:** First-class clients in every language (redis-py, Jedis/Lettuce, node-redis, go-redis, etc.). CDC and Kafka connectors exist; debezium-style change capture is limited (keyspace notifications are best-effort).
- **Community:** Huge. Excellent docs, large commercial backing (Redis Ltd. + the BSD-licensed [valkey](valkey.md) fork backed by AWS/Google/Oracle under the Linux Foundation). Low learning curve for basics; correct distributed operation (Cluster, failover, durability tuning) is the hard part.

## Licensing & cost
- **License history (contentious — note carefully):** BSD-3-Clause until **March 2024**, when Redis Ltd. relicensed to dual **RSALv2 / SSPLv1** (source-available, not OSI open source) — triggering the **[valkey](valkey.md)** fork (BSD, CNCF/Linux Foundation, AWS+Google+Oracle backing). In **May 2025**, Redis 8 added **AGPLv3** as an option, returning to an OSI-approved license; the source-available licenses remain offered alongside ([Redis blog](https://redis.io/blog/agplv3/), [InfoQ](https://www.infoq.com/news/2025/05/redis-agpl-license/)). See [license-taxonomy](../concepts/license-taxonomy.md). AGPLv3 still imposes network-copyleft obligations on modified hosted versions — not as permissive as the original BSD.
- **Self-managed vs managed:** Both. Managed: Redis Cloud, plus cloud providers' offerings (many of which now run Valkey rather than Redis to avoid the license).
- **Lock-in:** Low at the protocol level (RESP is widely reimplemented; Valkey is drop-in). Higher if you depend on Redis-Ltd-specific modules/Query-Engine features.
- **Cost model:** OSS free (per AGPL terms); managed is typically per-GB-RAM + throughput tier. Cost scales with the RAM-bound dataset, which inverts the "cheap" story at large data sizes.

## Hardware / deployment
- **Resource profile:** **Memory-bound** — the working set (in fact the entire dataset) must fit in RAM. CPU matters for the single-threaded command loop; network I/O is multi-threaded since 6.0.
- **Storage assumptions:** Disk used only for persistence (RDB/AOF). NVMe helps AOF fsync latency; not latency-sensitive to network-attached storage the way a disk-resident DB is.
- **Footprint:** Single-node, replicated (Sentinel), or sharded cluster. Lightweight binary; commonly run as a sidecar/cache tier.
- **Deployment:** SaaS and on-prem. k8s-friendly (operators exist; StatefulSets for Cluster/persistence), though stateful failover and persistent-volume management need care.

## Bottom line
Reach for Redis when you need sub-millisecond access to ephemeral or cacheable state — caching, sessions, queues, rate limiting, leaderboards, and increasingly vector/semantic caches. Do **not** use it as your primary system of record for data you cannot lose, for datasets that exceed RAM economically, or where you need strong consistency or real ACID transactions. The single biggest gotcha: **async replication means acknowledged writes can vanish on failover** — `WAIT` reduces but does not eliminate this, so treat Redis durability as best-effort, not guaranteed.

## Sources
- [Redis WAIT command docs](https://redis.io/commands/wait)
- [Redis replication docs](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)
- [Jepsen: Redis-Raft 1b3fbf6](https://jepsen.io/analyses/redis-raft-1b3fbf6)
- [Redis is now available under AGPLv3 (Redis blog)](https://redis.io/blog/agplv3/)
- [Redis Returns to Open Source under AGPL (InfoQ)](https://www.infoq.com/news/2025/05/redis-agpl-license/)
- [The Redis License Has Changed (Percona)](https://www.percona.com/blog/the-redis-license-has-changed-what-you-need-to-know/)
- [The Evolution of Redis: From Cache to AI-Database (Percona)](https://www.percona.com/blog/the-evolution-of-redis-from-cache-to-ai-database-v1-0-to-8-4/)
- [Redis Cluster scalability / hash slots](https://redis.io/tutorials/operate/redis-at-scale/scalability/)
