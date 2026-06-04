---
name: Riak KV
slug: riak-kv
rank: 90
data_model: Key-value (Dynamo-style)
license: Apache 2.0 (permissive)
summary: Dynamo-faithful AP key-value store with tunable quorums and CRDTs; safe only if you embrace siblings — its last-write-wins default silently drops writes.
last_researched: 2026-06-04
confidence: high
---

# Riak KV

> A high-availability, eventually-consistent key-value store that is a near-literal implementation of Amazon's Dynamo paper — operationally simple to scale, but its convenient last-write-wins default loses acknowledged writes by design.

## When to use

**Use Riak KV if:**
- ✅ You need a leaderless, always-writable, horizontally-scalable KV store across datacenters where availability beats consistency.
- ✅ Your team will genuinely model conflicts with CRDTs or client-side sibling merges (`allow_mult=true`).
- ✅ You want predictable, low-variance latency at scale and no-drama rolling upgrades / node add-remove.

**Avoid Riak KV if:**
- ❌ Anyone might enable last-write-wins (`allow_mult=false`) — Jepsen measured 71% of acknowledged writes lost with no partition and up to 91% across one.
- ❌ You need transactions, joins, ad-hoc queries, or strong consistency.
- ❌ It is a greenfield choice — commercial backer Basho went bankrupt in 2017 and maintenance velocity is low; prefer DynamoDB or Cassandra.

## Identity
- **Taxonomy / data model:** Distributed key-value store organized as buckets → keys → opaque values; supports [crdts](../concepts/crdts.md)-based data types (counters, sets, maps, registers, flags) on top of the KV core. One of the original Dynamo clones, alongside [apache-cassandra](apache-cassandra.md) and [amazon-dynamodb](amazon-dynamodb.md).
- **Storage model:** Pluggable per-bucket backends. Default **Bitcask** is a log-structured hash index ([lsm-vs-btree](../concepts/lsm-vs-btree.md)-adjacent; append-only log + in-RAM keydir, so **all keys must fit in memory**). **LevelDB / leveled** are LSM-tree backends supporting secondary indexes and unbounded keyspaces. Memory backend for caches.
- **Workload:** OLTP, high-write-availability KV access (get/put by key). Not OLAP — no analytical query engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **AP by default** — stays available on both sides of a partition and reconciles later via vector clocks / read repair / handoff. An optional **strongly consistent (CP)** mode exists per bucket-type but is documented as experimental and *not production-supported* ([Strong Consistency Reference](https://docs.riak.com/riak/kv/2.2.3/using/reference/strong-consistency/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PA/EL** — under Partition favors Availability; Else favors Latency (tunable down per-request via R/W/PR/PW quorum knobs at some consistency cost).
- **Default isolation & what's achievable:** No multi-key transactions and no isolation in the SQL sense. Single-key writes are not serialized — **concurrent writes produce siblings** (conflicting versions). The dangerous part: the convenience setting `allow_mult=false` (last-write-wins) resolves siblings by **wall-clock timestamp**, silently discarding the losing write. Jepsen measured **71% of acknowledged writes lost on a healthy, partition-free cluster** under LWW, and **91% lost across a partition** ([Jepsen: Riak](https://aphyr.com/posts/285-jepsen-riak)). With `allow_mult=true` and client-side merge (or CRDTs), no acknowledged writes are lost — this is the only safe way to run it. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Leaderless **N/R/W quorum** (Dynamo-style, R+W>N for read-your-writes likelihood; default N=3). Sympathetic features: hinted handoff, read repair, active anti-entropy (Merkle trees). Writes are async to replicas; **PW/DW** tune durable-write guarantees. No leader → no split-brain election, but partitions yield divergent siblings. Cross-cluster **Multi-Datacenter Replication (MDC)**, uni- and bi-directional, was a Basho Enterprise feature now open-sourced. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** Yes — per-request R, W, PR, PW, DW, plus `notfound_ok`, `basic_quorum`. Quintessential tunable-consistency system.
- **Clock dependency:** **Logical clocks** ([clocks-and-time](../concepts/clocks-and-time.md)) — vector clocks, and since 2.0 **dotted version vectors (DVVs)**, which bound sibling explosion under many concurrent writers ([DVV docs](https://docs.riak.com/riak/kv/2.2.3/learn/concepts/causal-context/)). Note: DVVs are on by default (`dvv_enabled=true`) only for *custom bucket types* created in 2.0+; the legacy default bucket type keeps classic vector clocks (`dvv_enabled=false`). Correctness of causality does *not* depend on synchronized wall clocks — but **last-write-wins conflict resolution does**, which is exactly why LWW is unsafe.

## Schema
- **Schema model:** Schemaless / schema-on-read. Values are opaque blobs (JSON, protobuf, anything); structure lives in the application. CRDT data types impose minimal structure.
- **Migration/evolution:** No DDL, no `ALTER`, no online schema migration concept — versioning is an application concern.
- **Type system:** Opaque values + content-type metadata; native CRDT types (counter, set, map, register, flag); secondary indexes (2i) on LevelDB/leveled backends; Riak Search (Solr-backed, [full-text-search](../concepts/full-text-search.md)).

## Query interface
- **Language:** **API-only** — HTTP/REST and Protocol Buffers get/put/delete by key. No SQL. Secondary-index range queries, Solr-backed search (Yokozuna), and MapReduce (Erlang/JavaScript) for richer access.
- **Transactions:** **None across keys.** Single-key updates are atomic at the object level but produce siblings rather than serializing. No multi-statement ACID.
- **Native vs app-side:** No joins. Secondary indexes and search are native (on supported backends). Aggregations via MapReduce or CRDTs. Conflict *resolution* is app-side unless using CRDTs.
- **Stored procedures / UDFs:** MapReduce functions in Erlang or JavaScript; pre/post-commit hooks in Erlang/JS.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal-first. **Consistent hashing** over a fixed ring of partitions (vnodes, default 64); data and ownership gossip around the ring like Dynamo.
- **Sharding/resharding:** Automatic via consistent hashing; adding/removing nodes triggers vnode handoff (rebalancing) — operationally one of Riak's strong points, generally low-drama compared to manual-shard systems. The fixed `ring_size` is chosen at cluster creation and is painful to change later.
- **Read replicas / consistency:** No primary/replica split; every node serves reads. Read consistency is tunable via R/PR; stale reads possible under AP defaults; read repair heals divergence opportunistically.
- **Storage/compute separation:** No — shared-nothing, data co-located with compute on each node. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Bitcask appends to a log and updates an in-memory keydir; **fsync is not per-write by default**, so a crash can lose recently-acked writes within the OS buffer window unless `DW`/durable settings are tightened. LevelDB uses an LSM WAL + memtable. See [wal-and-durability](../concepts/wal-and-durability.md). Predictable low-latency writes are a core selling point.
- **Throughput/latency / p99:** Designed for **predictable, low-variance latency** at scale — leaderless writes avoid leader bottlenecks; p99 stays tight precisely because the system never blocks for consensus (the flip side being weak consistency). Bitcask gives near-constant get/put latency.
- **Compaction / GC:** Bitcask **merges** append-only log files to reclaim space (compaction can cause I/O spikes affecting p99); LevelDB does LSM compaction. Active anti-entropy runs background Merkle-tree exchanges.

## Operations & maturity
- **Backup/restore:** File-system-level backup of per-node data dirs; no built-in PITR. MDC used for DR. Snapshotting is backend-dependent.
- **Observability:** `riak admin` / `riak-admin` stats, ring status, console; per-vnode and cluster metrics; no query planner (no queries). Logs via lager.
- **Upgrade story:** **Rolling upgrades** node-by-node with no downtime — a genuine strength of the leaderless design.
- **Maturity:** Mature, battle-tested in 2010s (Comcast, Riot Games, bet365). **Jepsen ([aphyr](https://aphyr.com/posts/285-jepsen-riak)):** vector clocks + sibling merging behave correctly and lose no acknowledged writes; **last-write-wins loses 71% of writes with no partition and up to 91% across one** — the headline cautionary result. The optional strong-consistency mode was never declared production-ready ([docs](https://docs.riak.com/riak/kv/2.2.3/using/reference/strong-consistency/)). **Biggest maturity caveat: commercial vendor Basho went bankrupt in 2017**; community/bet365 maintenance continues but at far lower velocity (latest 3.2.0, Jan 2023).

## Ecosystem & people
- **Canonical use cases:** High-write-availability KV — session/profile stores, IoT/sensor ingestion, shopping carts, mutable replicated state where availability beats consistency and the app can merge siblings (or use CRDTs). Multi-datacenter active/active.
- **Anti-patterns:** Anything needing transactions, joins, ad-hoc queries, or strong consistency; teams unwilling to handle siblings (they will reach for LWW and lose data); analytics; small single-node deployments (overkill vs [redis](redis.md)/[postgresql](postgresql.md)). Also risky as a *new* greenfield choice given the post-Basho maintenance situation.
- **Drivers/connectors:** Official clients for Erlang, Java, Python, Ruby, Go, .NET, Node.js; HTTP and PB protocols. Solr integration for search. Limited modern CDC/Kafka/dbt/BI ecosystem compared to its heyday.
- **Community / support:** Once-large community has shrunk markedly post-Basho; commercial support now via third parties (e.g., TI Tokyo) rather than a primary vendor. Docs are thorough (legacy Basho docs) but aging. Steep conceptual learning curve (siblings, vector clocks, quorums).

## Licensing & cost
- **License:** **Apache 2.0**, permissive ([license-taxonomy](../concepts/license-taxonomy.md)). After Basho's 2017 receivership, **bet365 acquired the IP and open-sourced all formerly-Enterprise features** (notably MDC replication) — a rare *de*-commercialization, the opposite of the post-2018 source-available trend.
- **Self-managed vs managed:** Self-managed/on-prem only; no first-party managed cloud service today. No meaningful proprietary lock-in (fully OSS).
- **Cost model:** Free software; cost is purely infrastructure + operational expertise (3+ nodes minimum to be meaningful). Scales linearly in node count; cheap-at-small is *not* its niche.

## Hardware / deployment
- **Resource profile:** With **Bitcask, RAM-bound** — the entire keydir (all keys) must fit in memory per node; LevelDB/leveled relax this (disk-bound, working set in RAM). Generally disk-I/O- and memory-sensitive.
- **Storage assumptions:** Local disk, shared-nothing; benefits from SSD/NVMe for compaction and LSM backends; not designed around network-attached storage.
- **Footprint:** Clustered (minimum 3, recommended 5+ nodes for N=3 quorums); not embedded, not serverless.
- **Deployment:** On-prem / self-hosted; runs on Linux/FreeBSD; Erlang/OTP 22/24/25 (3.2.0). Containerizable but predates cloud-native tooling; StatefulSet-on-k8s is possible but not a first-class story.

## Bottom line
Reach for Riak KV when you need a leaderless, always-writable, horizontally-scalable KV store across datacenters and your team will genuinely model conflicts with CRDTs or client-side sibling merges. Do not reach for it if you need transactions, queries, strong consistency, or — critically — if anyone might flip on last-write-wins, which **silently discards the majority of concurrent writes** (Jepsen: up to 91% loss). The single biggest gotcha is dual: the LWW data-loss trap, and the fact that its commercial backer is gone, making it a hard sell for new projects versus a maintained Dynamo-style alternative like [amazon-dynamodb](amazon-dynamodb.md) or [apache-cassandra](apache-cassandra.md).

## Sources
- [Jepsen: Riak (aphyr)](https://aphyr.com/posts/285-jepsen-riak)
- [Riak docs — Dynamo](https://docs.riak.com/riak/kv/2.2.3/learn/dynamo/index.html)
- [Riak docs — Causal Context / Dotted Version Vectors](https://docs.riak.com/riak/kv/2.2.3/learn/concepts/causal-context/index.html)
- [Riak docs — Conflict Resolution](https://docs.riak.com/riak/kv/latest/developing/usage/conflict-resolution/index.html)
- [Riak docs — Strong Consistency Reference (experimental, not production)](https://docs.riak.com/riak/kv/2.2.3/using/reference/strong-consistency/)
- [Riak docs — CRDT Data Types](https://docs.riak.com/riak/kv/2.2.3/learn/concepts/crdts/)
- [Riak docs — LevelDB backend](https://docs.riak.com/riak/kv/latest/setup/planning/backend/leveldb/index.html)
- [Wikipedia — Riak](https://en.wikipedia.org/wiki/Riak)
