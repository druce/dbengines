---
name: Valkey
slug: valkey
rank: 106
data_model: Key-value
license: BSD 3-Clause (permissive)
summary: Linux Foundation fork of Redis 7.2.4, BSD-licensed and moving faster than Redis; same in-memory KV engine, same best-effort-cache consistency.
last_researched: 2026-06-04
confidence: high
---

# Valkey

> A community-governed, BSD-licensed continuation of Redis 7.2.4 with added multithreaded I/O and faster sync — but it inherits Redis's async-replication, best-effort-cache consistency model, so don't treat it as a system of record.

## Identity
- **Taxonomy / data model:** in-memory key-value store with rich value types (strings, hashes, lists, sets, sorted sets, streams, bitmaps, HyperLogLog, geospatial). Forked from Redis 7.2.4 in March 2024 after Redis relicensed away from BSD; governed under the Linux Foundation with AWS, Google, Oracle, and Ericsson backing ([valkey.io](https://valkey.io/), [redis.io comparison](https://redis.io/blog/what-is-valkey/)).
- **Storage model:** RAM-resident dataset; not [lsm-vs-btree](../concepts/lsm-vs-btree.md) (no on-disk index structure). On-disk persistence is only for restart/durability via point-in-time RDB snapshots and/or an append-only command log (AOF) ([persistence docs](https://valkey.io/topics/persistence/)). Working set must fit in memory.
- **Workload:** OLTP-adjacent — caching, session store, rate limiting, leaderboards, pub/sub, queues/streams. Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **AP / best-effort.** Replication is asynchronous and failover (Sentinel or Cluster) is "last failover wins," so acknowledged writes can be lost during partitions. Valkey inherits Redis's design here; the canonical Jepsen finding (Redis + Sentinel lost ~56% of acknowledged writes under partition) reflects this shared lineage ([Jepsen: Redis](https://aphyr.com/tags/redis)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition, favors Availability (serves stale/loses writes); Else favors Latency over Consistency (async replicas, in-memory reads). It is an **PA/EL** system.
- **Default isolation & what's achievable:** single-threaded command execution gives serial execution of individual commands. `MULTI`/`EXEC` transactions are **not** rollback-able ACID transactions — they batch commands and execute them without interleaving, but a command failing mid-transaction does not roll back prior ones. Lua scripts / Functions run atomically (the whole script executes as one unit, blocking other clients) ([scripting docs](https://valkey.io/topics/eval-intro/), [functions docs](https://valkey.io/topics/functions-intro/)). There is no snapshot isolation or MVCC; see [isolation-levels](../concepts/isolation-levels.md) and [mvcc](../concepts/mvcc.md) for contrast.
- **Replication:** single-leader (primary→replica), **asynchronous** by default. `WAIT n timeout` blocks until N replicas ack, narrowing but not closing the loss window — it does not make failover safe ([Jepsen: Redis](https://aphyr.com/tags/redis)). See [replication-models](../concepts/replication-models.md). Failover via Sentinel (HA for non-clustered) or Cluster's built-in gossip + automatic failover (up to ~1000 nodes pre-9.0, 2,000 in 9.0).
- **Tunable consistency?** Only coarsely: `WAIT` for write durability acks; no per-query quorum read/write levels like Dynamo/Cassandra.
- **Clock dependency:** no correctness dependence on synchronized clocks. Failover uses configurable timeouts, not wall-clock ordering. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** schemaless; structure lives in application code and key-naming conventions. No DDL.
- **Migration/evolution:** N/A — no schema to migrate; key reshaping is an application concern.
- **Type system:** the value-type set above. No native JSON/vector/geospatial *index* types in core (those were Redis Modules; Valkey ships equivalents as separate modules — e.g. valkey-json, valkey-search/vector, valkey-bloom — under BSD, not in the core binary).

## Query interface
- **Language:** RESP-protocol command API (get/put-style verbs per type), not SQL. Drivers across all major languages.
- **Transactions:** `MULTI`/`EXEC`/`WATCH` (optimistic locking via WATCH for compare-and-set); single-command atomicity; Lua/Functions for atomic multi-step logic. No multi-statement rollback. See [isolation-levels](../concepts/isolation-levels.md).
- **Native vs app-side:** no joins, no secondary indexes in core (sorted sets are the manual indexing primitive); aggregation only via Lua or type-specific ops. Cross-key operations are app-side.
- **Stored procedures / UDFs:** Lua scripts (`EVAL`) and **Valkey Functions** (named, versioned, persisted to AOF and replicated) ([functions docs](https://valkey.io/topics/functions-intro/)).

## Scaling & topology
- **Vertical vs horizontal:** vertical first (single-thread command path historically the bottleneck; Valkey 8 added multithreaded **I/O** but command execution remains effectively single-threaded). Horizontal via Cluster: hash-slot sharding (16384 slots); slot assignment/resharding historically manual, now eased by atomic slot migration in 9.0. Cluster supports up to ~1000 nodes pre-9.0, raised to **2,000 nodes in Valkey 9.0** ([Valkey 9.0](https://valkey.io/blog/introducing-valkey-9/)).
- **Sharding / resharding:** slot migration is online; Valkey 8 made `CLUSTER SETSLOT` replicate synchronously to replicas before execution and gave empty new shards automatic failover, and **Valkey 9.0 (Oct 2025) added atomic slot migration** — entire slots move atomically (transferred via AOF format) instead of the older key-by-key/manual `CLUSTER SETSLOT` dance, reducing scaling-window unavailability ([Valkey 8.0 GA](https://valkey.io/blog/valkey-8-ga/), [Valkey 9.0](https://valkey.io/blog/introducing-valkey-9/)).
- **Read replicas:** yes; replica reads are **eventually consistent** (async lag) unless you constrain to primary.
- **Storage/compute separation:** no — compute and (in-memory) storage are co-located per node. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** writes hit RAM first. Durability via AOF with fsync policy `always` (every write — slowest, smallest loss), `everysec` (default; **up to ~1s loss window**), or `no` (OS-flushed) ([persistence docs](https://valkey.io/topics/persistence/)). RDB snapshots lose everything since the last snapshot on crash. fsync runs on a background thread. See [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window:** ~1s with `everysec`; larger with RDB-only; replication adds its own async loss window on failover.
- **Throughput/latency:** sub-millisecond p50; very high throughput. Valkey 8 multithreaded I/O reports ~1.19M RPS on suitable hardware vs the ~hundreds-of-K single-threaded ceiling ([Valkey 8.0](https://valkey.io/blog/valkey-8-0-0-rc1/), [1M RPS post](https://valkey.io/blog/unlock-one-million-rps/)).
- **p99 tail risks:** fork()-based RDB/AOF-rewrite copies page tables and can cause latency spikes and memory spikes (copy-on-write) on large datasets; `fsync always` hurts tail badly. No background compaction/vacuum (LSM-style), so that class of p99 problem doesn't apply.

## Operations & maturity
- **Backup/restore:** RDB snapshot files (copyable point-in-time backups); AOF replay on restart. No built-in continuous PITR beyond replaying AOF.
- **Observability:** `INFO`, `SLOWLOG`, `LATENCY` monitoring, `MEMORY` introspection, `MONITOR`, keyspace notifications. No query planner (commands are direct).
- **Upgrade story:** rolling upgrades via replica promotion; protocol/format compatible with Redis 7.2.x, easing migration from Redis or ElastiCache. Day-2 burden: memory management (eviction policy, fragmentation), persistence tuning, and failover testing.
- **Maturity:** young project name (2024) but mature codebase (Redis lineage since 2009). Heavily backed; AWS ElastiCache and MemoryDB, Google Memorystore offer managed Valkey. **Jepsen:** no Valkey-specific report; the relevant analyses are on Redis ([Jepsen: Redis](https://aphyr.com/tags/redis), [Jepsen: Redis-Raft](https://jepsen.io/analyses/redis-raft-1b3fbf6)) — both conclude Redis-family failover is best-effort and not safe for a system of record. Valkey 9.0 (Oct 2025) added multidatabase clustering, atomic slot migration, and hash-field expiration but **did not change the async-replication consistency model** ([Valkey 9.0](https://valkey.io/blog/introducing-valkey-9/)) — the best-effort-cache behavior above still holds. ⚠️ unverified — Valkey's planned Raft-based clustering (discussed as a future direction) had not shipped or been independently verified as of research date.

## Ecosystem & people
- **Canonical use cases:** cache-aside / read-through caching, session/token store, rate limiters, leaderboards (sorted sets), pub/sub fan-out, lightweight job queues and streams.
- **Anti-patterns:** primary system of record / source of truth (async loss); data larger than RAM; relational/analytical queries; anything needing serializable cross-key transactions or guaranteed durability of every ack.
- **Drivers / connectors:** valkey-glide (official multi-language client), plus existing Redis clients (redis-py, Jedis/Lettuce, node-redis, go-redis) work over RESP. Drop-in for most Redis tooling, Kafka Redis connectors, etc.
- **Community / support:** Linux Foundation governance; broad vendor support (AWS, Google, Oracle); docs are solid and largely descended from Redis docs; gentle learning curve for anyone who knows Redis.

## Licensing & cost
- **License:** **BSD 3-Clause, permissive** — explicitly the *reason* the fork exists. Redis 7.4 moved to the dual RSALv2/SSPLv1 source-available model in 2024; Valkey continued the pre-change BSD code. (Redis later re-added an AGPL option in Redis 8, 2025, but Valkey remains the permissive lineage.) See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** both. Self-host the open binary, or use managed Valkey on AWS ElastiCache/MemoryDB and Google Memorystore.
- **Lock-in:** minimal — open protocol, open license, multiple compatible clients and managed providers.
- **Cost model:** self-managed = your hardware (RAM-dominated). Managed = per-node-hour by instance memory/CPU. Cost scales with RAM, which gets expensive for large datasets since everything lives in memory.

## Hardware / deployment
- **Resource profile:** **memory-bound** — entire dataset (plus COW headroom for forks) must fit in RAM. CPU matters more now with multithreaded I/O; modest disk for persistence.
- **Storage assumptions:** persistence I/O benefits from fast local disk (NVMe) for AOF fsync; network-attached storage adds fsync latency. Reads/writes are RAM, not disk-bound.
- **Footprint:** single-node, primary/replica HA, or clustered (up to ~1000 nodes pre-9.0, 2,000 in 9.0). Not embedded; runs as a server process.
- **Deployment:** on-prem or SaaS; container/k8s-friendly with StatefulSets and operators (Bitnami chart, community operators), though stateful failover semantics still require care.

## Bottom line
Reach for Valkey when you want Redis's speed and data structures with a permissive BSD license and an actively-developed, vendor-neutral codebase — it's a near drop-in replacement for Redis 7.2.x and the natural choice post-relicensing. Don't reach for it as your durable system of record, for datasets larger than RAM, or where you need serializable transactions. **Biggest gotcha:** despite "persistence," it remains a best-effort store — async replication plus last-failover-wins means acknowledged writes can vanish during partitions/failover, exactly as Jepsen documented for Redis.

## Sources
- [Valkey official site](https://valkey.io/)
- [Valkey persistence docs](https://valkey.io/topics/persistence/)
- [Valkey scripting (Lua) docs](https://valkey.io/topics/eval-intro/)
- [Valkey Functions docs](https://valkey.io/topics/functions-intro/)
- [Valkey 8.0 GA blog](https://valkey.io/blog/valkey-8-ga/)
- [Valkey 8.0 RC performance/reliability blog](https://valkey.io/blog/valkey-8-0-0-rc1/)
- [Valkey: 1 Million RPS](https://valkey.io/blog/unlock-one-million-rps/)
- [Redis: What is Valkey? (comparison)](https://redis.io/blog/what-is-valkey/)
- [Jepsen: Redis (tag)](https://aphyr.com/tags/redis)
- [Jepsen: Redis-Raft 1b3fbf6](https://jepsen.io/analyses/redis-raft-1b3fbf6)
- [The Register: Valkey 9](https://www.theregister.com/2025/09/29/valkey_9/)
