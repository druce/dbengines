---
name: Memcached
slug: memcached
rank: 39
data_model: Key-value (in-memory cache)
license: Revised BSD (BSD 3-Clause, permissive)
summary: Minimalist multi-threaded in-memory key-value cache; volatile by design, sharded entirely client-side, and deliberately featureless.
last_researched: 2026-06-04
confidence: high
---

# Memcached

> A bare-bones, multi-threaded, in-RAM string-blob cache that does one thing — fast get/set with LRU eviction — and intentionally nothing else; it is not a database and loses all data on crash.

## When to use

**Use Memcached if:**
- ✅ You need a dead-simple, multi-threaded look-aside cache (DB results, rendered fragments, API responses, sessions) in front of a slower system of record
- ✅ You can tolerate losing the entire cache at any moment — all data is disposable by design
- ✅ You want to scale horizontally across cores and across independent nodes via client-side consistent hashing
- ✅ You want minimal operational surface and a permissive BSD license with no lock-in

**Avoid Memcached if:**
- ❌ You need durability, replication, or HA — there is no persistence (everything is lost on crash) and no server-to-server replication
- ❌ You need data structures, secondary indexes, range/scan queries, or values larger than 1 MB (default) — reach for [redis](redis.md) or a real database
- ❌ You would treat it as a system of record — that is the single biggest mistake
- ❌ You might expose it to the internet — unauthenticated instances are a documented UDP DDoS-amplification and data-leak hazard

## Identity
- **Taxonomy / data model:** [key-value](../concepts/key-value-store.md) cache. Opaque keys (≤250 bytes) → opaque byte-string values (default ≤1 MB). No data types, no structure inside values (contrast [redis](redis.md), which has lists/sets/hashes). It is a cache, not a store of record.
- **Storage model:** pure in-memory hash table + [slab allocator](../concepts/lsm-vs-btree.md)-managed memory (not LSM, not B-tree). Memory is carved into 1 MB pages split into fixed-size chunks grouped by "slab class"; an item lands in the smallest chunk that fits, which causes internal fragmentation and per-slab-class eviction ([slab/LRU docs](https://docs.memcached.org/features/slabs/)). **extstore** (1.6.0+) optionally spills *values* to flash while keeping keys/metadata in RAM ([extstore wiki](https://github.com/memcached/memcached/wiki/Extstore)) — this is overflow capacity, not durability.
- **Workload:** read-heavy caching in front of a slower system of record (DB, API). Not OLTP, not OLAP — see [oltp-olap-htap](../concepts/oltp-olap-htap.md). The canonical pattern is cache-aside/look-aside: app checks cache, falls back to DB on miss, repopulates.

## Distribution & consistency
- **CAP under partition:** N/A in the usual sense — Memcached has **no server-to-server replication or coordination**. Each node is independent; "distribution" is purely client-side sharding. There is no single consistency model to violate because there is no cross-node agreement. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — no replication, so no partition/latency-vs-consistency tradeoff at the engine level. The client library owns all topology decisions.
- **Default isolation & what's achievable:** no transactions and no [isolation levels](../concepts/isolation-levels.md). Single-key operations are atomic; multi-key atomicity does not exist. Optimistic concurrency is available per-key via **CAS** (compare-and-swap using a version token); `incr`/`decr`/`add`/`append`/`prepend` give limited atomic primitives. Any "ACID" framing is inapplicable.
- **Replication:** none built-in. High availability is achieved by the client hashing keys across many independent nodes (typically via consistent hashing / ketama) so that losing one node only drops that node's share of cache — see [replication-models](../concepts/replication-models.md) and [sharding-partitioning](../concepts/sharding-partitioning.md). Managed offerings (e.g. AWS ElastiCache for Memcached) add node management but still no native replication of data between Memcached nodes.
- **Tunable consistency?** No. Consistency is whatever the client's sharding scheme yields; a key lives on exactly one node.
- **Clock dependency:** none for correctness. TTLs use the server's wall clock for expiry; expiry is approximate (lazy + LRU-crawler reaping), not a real-time guarantee. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** in the loosest sense: the value is an opaque blob; any structure (serialization format, key naming convention) lives entirely in application code. Schemaless.
- **Migration/evolution:** N/A — no schema, no DDL. Changing slab/growth settings historically required restart; warm-restart preserves cache across most setting changes (1.5.18+).
- **Type system:** none. Values are bytes plus a small flags field (typically used by clients to record serialization type). No native JSON, arrays, geospatial, or vectors.

## Query interface
- **Language:** simple text/binary protocol over TCP/UDP/Unix socket; commands `get/gets/set/add/replace/append/prepend/cas/delete/incr/decr/flush_all`. The newer **meta protocol** adds richer flags (TTL fetch, recache hints, probabilistic logic) for stampede control. No SQL, no query language, no scans/range queries.
- **Transactions:** none. Per-key atomic ops and CAS only.
- **Native vs app-side:** no joins, no secondary indexes, no aggregations, no server-side filtering. Everything beyond get/set is done in the application.
- **Stored procedures / UDFs:** none. (Memcached is deliberately not extensible at the data layer; contrast [redis](redis.md) Lua scripting/modules.)

## Scaling & topology
- **Vertical vs horizontal:** scales vertically by giving a node more RAM/cores (it is genuinely multi-threaded and scales well across cores, unlike single-threaded [redis](redis.md) core). Scales horizontally by adding independent nodes — but the **client** must reshard.
- **Sharding:** client-side, manual in the sense that the engine provides nothing; libraries implement consistent hashing (ketama) so adding/removing a node remaps only ~1/N of keys (a cold-cache event for that fraction, not data loss of a store of record). See [sharding-partitioning](../concepts/sharding-partitioning.md). No auto-rebalancing, no resharding coordination — the engine is unaware it is part of a cluster.
- **Read replicas / read consistency:** none — a key exists on exactly one node; no replica reads.
- **Storage/compute separation:** N/A. extstore attaches local flash to a node; it is not the Aurora/Neon disaggregation pattern. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** writes go to RAM only. **No WAL, no fsync, no persistence by default** — see [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window on crash = everything**; a crash or unclean restart drops the entire cache ([data-loss note](https://docs.memcached.org/features/restart/)). The **warm restart** feature (1.5.18+) can recover the cache across a *clean* restart by mmap-ing item memory to a file and rebuilding pointers/hash table on startup — but it is explicitly **not crash-safe** ([warm restart docs](https://docs.memcached.org/features/restart/)). Treat all data as ephemeral.
- **Throughput/latency:** very high throughput, sub-millisecond latencies; multi-threaded design uses all cores. Predictable, low p99 under normal load — there is little background work to cause stalls. Tail latency is dominated by network and, with extstore enabled, by flash read latency on values fetched from disk.
- **Compaction / vacuum / GC:** none in the LSM sense. Expiry is lazy plus a background LRU crawler; the slab allocator can do limited automatic slab rebalancing/page moving (`slab_automove`). Per-slab-class LRU means a full slab class evicts its own oldest items even if other classes have free chunks — a classic operational gotcha (calcified slabs after a workload shift).

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** none, by design — it is a cache. Warm restart is the closest thing and only survives clean restarts. No PITR.
- **Observability:** `stats` command family (stats, stats slabs, stats items, stats sizes) exposes hit/miss ratios, evictions, memory per slab class; widely integrated with Prometheus exporters, Datadog, etc. No query plans (no queries). Hit ratio and eviction count are the load-bearing metrics.
- **Upgrade story:** trivial — replace the binary and restart; warm restart can preserve cache across binary upgrades in many cases. Nodes are independent, so rolling upgrades are simple. Day-2 burden is low: the main concerns are right-sizing memory, tuning slab classes/item size, watching eviction rate, and securing access.
- **Maturity:** extremely mature (since 2003), ubiquitous, battle-tested at hyperscale (Facebook's "Scaling Memcache at Facebook" paper is the reference text). Known failure modes: thundering-herd/cache-stampede on hot-key expiry (mitigated by the meta protocol and client lease/recache logic), slab calcification, and the security footgun below. **No Jepsen report exists** — and it would not be meaningful, since the engine offers no distributed consistency guarantees to test.

## Ecosystem & people
- **Canonical use cases:** look-aside caching of DB query results, rendered fragments, API responses, and session storage (where session loss is tolerable); rate-limiting counters via atomic incr. **Anti-patterns:** anything needing durability, replication, secondary access patterns, range/scan queries, values >1 MB (default), or rich data structures — for those reach for [redis](redis.md) (data structures, persistence, replication, pub/sub) or a real database. Using it as a system of record is a mistake.
- **Drivers / connectors:** mature clients in every major language (libmemcached, pymemcache, spymemcached/xmemcached, Dalli, php-memcached). First-class in Django/Rails/Symfony cache backends. Not a CDC/Kafka/dbt/BI participant — it is a cache, not a data source.
- **Community / support / docs:** active OSS project (latest stable 1.6.42, May 2026 — [release notes](https://github.com/memcached/memcached/wiki/ReleaseNotes)), good official docs at docs.memcached.org. Commercial support primarily via managed clouds (AWS ElastiCache, Google Memorystore for Memcached). Very low learning curve — the entire feature surface fits on one page; the hard part is cache-invalidation strategy, which lives in your app.

## Licensing & cost
- **OSS license:** Revised BSD (BSD 3-Clause), fully permissive — no copyleft, no post-2018 source-available relicensing (contrast [redis](redis.md)'s 2024 move from BSD-3 to dual source-available [RSALv2/SSPLv1](https://redis.io/blog/redis-adopts-dual-source-available-licensing/); Redis 8 in 2025 re-added an OSI-approved AGPLv3 option). See [license-taxonomy](../concepts/license-taxonomy.md). Genuinely free to self-host and embed.
- **Self-managed vs managed:** both common. Self-managed is simple; managed (ElastiCache, Memorystore) adds provisioning/monitoring/auto-discovery but no extra data guarantees.
- **Lock-in:** essentially none — trivial protocol, many interchangeable clients, no proprietary features to depend on.
- **Cost model:** self-hosted cost = RAM (the dominant input). Managed = per-node/per-hour by instance memory/CPU. Cheap and predictable; cost scales with the RAM you want cached. extstore lets you trade cheaper flash for some hit-latency to cache more per node.

## Hardware / deployment
- **Resource profile:** **memory-bound** — the working set you want cached must fit in RAM (or in RAM+flash with extstore). Modest CPU; multi-threaded so it uses available cores. Not disk-bound unless extstore is enabled.
- **Storage assumptions:** none by default (RAM only). With extstore, prefers fast local NVMe for value spillover; network-attached storage is a poor fit given the latency-sensitive use case.
- **Footprint:** single lightweight daemon per node; "clusters" are just N independent daemons coordinated by clients. Not embedded, not serverless (though managed serverless-ish offerings exist).
- **Deployment:** trivially container/k8s-friendly; usually run as a Deployment (stateless, since data is disposable) rather than a StatefulSet — losing a pod just cold-caches its key range. SaaS and on-prem both standard. **Security gotcha:** default config historically binds broadly and has no auth on the plain protocol; exposing Memcached to the internet enabled massive UDP reflection DDoS amplification (2018). Bind to localhost/private network, disable UDP if unused, and use SASL/TLS (TLS supported in recent versions) where needed.

## Bottom line
Reach for Memcached when you want a dead-simple, multi-threaded, horizontally-shardable RAM cache in front of a system of record and you can tolerate losing the entire cache at any moment. Do not reach for it if you need persistence, replication, data structures, secondary queries, or values larger than a megabyte — that is [redis](redis.md)'s or a real database's job. The single biggest gotcha is treating it as anything other than disposable: it has no durability, no built-in HA, and an internet-exposed instance is a documented DDoS-amplification and data-leak hazard.

## Sources
- [Memcached official documentation](https://docs.memcached.org/)
- [Slab allocator / LRU](https://docs.memcached.org/features/slabs/)
- [Extstore (flash storage) wiki](https://github.com/memcached/memcached/wiki/Extstore) and [Flash storage docs](https://docs.memcached.org/features/flashstorage/)
- [Warm restart docs (not crash-safe)](https://docs.memcached.org/features/restart/)
- [Features overview](https://docs.memcached.org/features/)
- [AWS ElastiCache for Memcached](https://aws.amazon.com/elasticache/memcached/)
- Nishtala et al., "Scaling Memcache at Facebook" (NSDI 2013) — reference for large-scale operational patterns.
