---
name: Qdrant
slug: qdrant
rank: 64
data_model: Vector
license: Apache 2.0 (permissive; OSS) + managed Qdrant Cloud
summary: Rust-built vector search engine with rich payload filtering and tunable read/write consistency; metadata is Raft-consistent but vector replication is not strongly serializable.
last_researched: 2026-06-04
confidence: high
---

# Qdrant

> A Rust-native vector database whose differentiator is fast filtered ANN search over rich JSON payloads, with metadata coordinated by Raft but vector data using best-effort replication and explicitly tunable consistency.

## When to use

**Use Qdrant if:**
- ✅ You need a dedicated, high-performance vector search engine with rich payload filtering (filterable HNSW applies filters during graph traversal)
- ✅ You want hybrid dense+sparse search, multi-vectors, server-side fusion/reranking, and multi-stage query
- ✅ You need multi-tenant vector search with per-tenant payload filtering and custom shard keys
- ✅ You want Apache-2.0 OSS you can self-host at any scale (or managed Qdrant Cloud with no per-query charge)

**Avoid Qdrant if:**
- ❌ You need durable, strongly-consistent vector replication out of the box — defaults optimize for speed/availability (`write_ordering=weak`, consistency factor 1, single-replica reads), Raft only protects *metadata*, and there's no Jepsen report
- ❌ You need a system of record with ACID transactions or strict serializable cross-record consistency
- ❌ You want an analytics warehouse, relational joins, or rich aggregations — only facets/counts
- ❌ You already run Postgres with modest vector volume — pgvector may avoid a separate engine

## Identity
- **Taxonomy / data model:** Purpose-built vector database (see [vector-search-ann](../concepts/vector-search-ann.md)). Each record ("point") is a vector (or several named vectors) plus an arbitrary JSON "payload" used for filtering. Not a general-purpose store. Related: [oltp-olap-htap](../concepts/oltp-olap-htap.md) — neither; it is an ANN serving engine.
- **Storage model:** Segment-based. Each segment is self-contained: vector storage, payload storage, an [HNSW](../concepts/full-text-search.md) index, and an ID mapper. Vectors live in RAM or memory-mapped on disk (`on_disk: true` / `memmap_threshold`); payload can be InMemory or OnDisk (Gridstore). Not a B-tree or [LSM](../concepts/lsm-vs-btree.md) engine — the primary index is the [HNSW graph](https://qdrant.tech/documentation/concepts/indexing/), with optional scalar/product/binary quantization for RAM reduction.
- **Workload:** Online similarity search (RAG, recommendation, dedup, semantic search), not OLTP or OLAP. HTAP: N/A — does not claim it.

## Distribution & consistency
- **CAP under partition:** Tunable per-operation rather than a single fixed point; defaults lean **AP** for writes. With defaults (`write_consistency_factor=1`, `write_ordering=weak`), a write is acked once a single replica applies it and may be reordered — favoring availability over consistency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Effectively **A-and-L by default, tunable toward C**. Under partition you can choose availability (low consistency factor) or consistency (high factor, refusing writes when replicas are missing); in the normal case `write_ordering=weak` and read consistency `1` favor latency. ⚠️ unverified — no formal PACELC classification is published; this is inferred from the [distributed deployment docs](https://qdrant.tech/documentation/guides/distributed_deployment/).
- **Default isolation & what's achievable:** No SQL-style transactions or isolation levels (see [isolation-levels](../concepts/isolation-levels.md)). Updates are atomic at the point/operation granularity, not multi-statement. Each operation gets a monotonic WAL sequence number; clock tags / point versions reject stale updates and resolve conflicts. There is **no serializability claim** — do not treat "consistent" here as serializable. ([docs](https://qdrant.tech/documentation/concepts/storage/))
- **Replication:** Leaderless-style per-shard replication. **Raft** governs only cluster topology and collection metadata (not per-point vector data) — [docs](https://qdrant.tech/documentation/guides/distributed_deployment/). Vector mutations propagate to shard replicas per the chosen consistency factor; `write_consistency_factor` (default 1) sets how many replicas must ack. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md), [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Tunable consistency?** Yes — the core selling point. **Read consistency:** integer N / `majority` / `quorum` / `all`. **Write ordering:** `weak` (default, may reorder, fastest) / `medium` (dynamically selected leader) / `strong` (permanent leader, consistent but unavailable if leader down). **Write consistency factor:** how many replicas must ack. ([docs](https://qdrant.tech/documentation/guides/distributed_deployment/))
- **Clock dependency:** Uses logical clock tags / per-point versions for conflict detection, **not** wall-clock or TrueTime — no synchronized-clock requirement for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Payload is schema-less JSON; collection-level config fixes vector dimensionality and distance metric (Cosine/Dot/Euclid/Manhattan) at creation. Vector size is effectively immutable per named vector.
- **Migration/evolution:** No locking `ALTER`-style DDL. You add payload fields freely; you create payload field indexes on demand (online). Changing vector dimensionality means a new collection + re-ingest.
- **Type system:** Dense vectors, sparse vectors (for hybrid/keyword search), multi-vectors (e.g. ColBERT-style late interaction), named vectors per point. Payload supports keyword, integer, float, bool, geo, datetime, and full-text fields, each independently indexable.

## Query interface
- **Language:** API-only — REST and gRPC; no SQL or query DSL. Query = vector(s) + optional filter (must/should/must_not boolean tree over payload). Official clients: Python, Rust, Go, JS/TS, Java, .NET.
- **Transactions:** None in the ACID sense. Single update operations are atomic; batch upserts apply atomically per operation but there is no multi-operation transaction.
- **Native vs app-side:** Native filtered ANN — Qdrant extends the HNSW graph with payload-aware edges so filters are applied *during* graph traversal (filterable HNSW), avoiding both naive pre-filter (which breaks graph connectivity) and post-filter; a per-segment query planner switches strategy based on filter cardinality and `full_scan_threshold` ([filtering article](https://qdrant.tech/articles/vector-search-filtering/)). Hybrid dense+sparse search with server-side fusion (RRF/DBSF), recommendations, grouping, and multi-stage query (prefetch + rerank). No joins. Aggregations are limited (facets/counts), not analytical.
- **Stored procedures / UDFs:** None.

## Scaling & topology
- **Vertical vs horizontal:** Both. Single-node scales vertically; cluster mode shards horizontally. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding:** Number of shards chosen at collection creation (manual). Auto-sharding by hash of point ID, or user-defined custom sharding keys (e.g. per-tenant, available since v1.7.0). Resharding of existing collections is now supported as a transparent, no-downtime process that can grow/shrink shard count and rebalance across nodes ([tracking issue #4213](https://github.com/qdrant/qdrant/issues/4213), [Cloud cluster scaling docs](https://qdrant.tech/documentation/cloud/cluster-scaling/)) — but it is exposed primarily on multi-node Cloud/Hybrid/Private Cloud tiers and remains a heavier operation than a fully elastic engine; early versions required recreate/migrate.
- **Read replicas:** Replicas serve reads; read consistency level (N/majority/quorum/all) controls staleness vs latency. Default reads from one replica can be stale.
- **Storage/compute separation:** No — local-storage shared-nothing nodes, not a Snowflake/Aurora split. See [storage-compute-separation](../concepts/storage-compute-separation.md). (Qdrant Cloud adds tiered/object-backed storage options but the OSS engine is shared-nothing.)

## Performance & durability
- **Write path:** Two-stage — operation first appended to the **WAL** (ordered, sequenced; survives power loss once written), then applied to segments. flush cadence is governed by `flush_interval_sec` (default 5s); **larger intervals batch writes for speed but widen the crash data-loss window** to that interval. See [wal-and-durability](../concepts/wal-and-durability.md). Default `wal_capacity_mb` is 32 (single WAL segment size). ([storage docs](https://qdrant.tech/documentation/concepts/storage/), [configuration](https://qdrant.tech/documentation/operations/configuration/))
- **Throughput/latency:** Strong ANN latency when the working set (or quantized vectors) fits in RAM; HNSW gives low-latency recall-tunable search (`ef`/`m` params). On-disk/mmap mode trades latency for capacity. p99 is sensitive to whether vectors are resident vs paged from disk.
- **Compaction / GC:** Background **optimizers** merge segments, build HNSW on sealed segments, apply quantization, and vacuum deleted points. Optimization is I/O- and CPU-heavy; running it during ingest can spike p99 and RAM. Deleted points are tombstoned until optimized away.

## Operations & maturity
- **Backup/restore:** Snapshots per-collection and full-storage; snapshots can be stored locally or to S3-compatible object storage. No continuous PITR/log-shipping in OSS — recovery point is the last snapshot plus WAL replay. Distributed snapshots of large collections have known operational sharp edges ([issue #2893](https://github.com/qdrant/qdrant/issues/2893)).
- **Observability:** Prometheus `/metrics`, REST telemetry/health endpoints, a built-in web UI. No SQL EXPLAIN; query introspection is limited.
- **Upgrade story:** Rolling upgrades supported in cluster mode; recovering nodes catch up via consensus-triggered replication of missed updates.
- **Maturity:** Widely deployed for RAG/vector search since ~2021; active development. **No published [Jepsen](../concepts/jepsen.md) report exists** — distributed-safety claims are not third-party-verified. Qdrant maintains an internal "crasher" fault-injection tool. Reported edge cases include replica inconsistency after migration ([#5101](https://github.com/qdrant/qdrant/issues/5101)) and downtime handling in 3-node replicated clusters ([#5215](https://github.com/qdrant/qdrant/issues/5215)). Treat strong cross-replica consistency as your responsibility to configure (higher consistency factor + `strong` ordering), not a default.

## Ecosystem & people
- **Canonical use cases:** RAG retrieval, semantic search, recommendation, image/audio similarity, dedup, multi-tenant vector search with per-tenant payload filtering and custom shard keys.
- **Anti-patterns:** Primary system of record / transactional store (no ACID transactions, no joins); analytics warehouse; small metadata-only workloads better served by Postgres+pgvector; cases needing strict serializable cross-record consistency. If you already run Postgres and have modest vector volume, a dedicated engine may be unnecessary.
- **Drivers / connectors:** Native clients (Python/Rust/Go/JS/Java/.NET); first-class integrations with LangChain, LlamaIndex, Haystack, and embedding providers. Less mature CDC/Kafka/dbt/BI tooling than relational engines — it is not part of the analytics stack.
- **Community size, support, docs:** Strong OSS traction and good documentation; commercial support via Qdrant Cloud. Low learning curve for basic search; tuning HNSW/quantization/consistency for production is where the depth is.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive) — [LICENSE](https://github.com/qdrant/qdrant/blob/master/LICENSE). No post-2018 relicensing to SSPL/BSL; the engine remains fully open and free to self-host at any scale. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-host the OSS engine, or use managed **Qdrant Cloud** (also Hybrid Cloud / Private Cloud). Some advanced cloud features are proprietary; the core engine is not.
- **Lock-in:** Low at the engine level (open format, open clients); moderate if you adopt Cloud-only features.
- **Cost model:** OSS = your infrastructure only. Cloud bills hourly on **compute (vCPU) + memory (GB) + storage (GB)** plus backup storage and inference tokens; notably **no per-query charge** ([pricing](https://qdrant.tech/pricing/)). At scale, cost is dominated by RAM — quantization (scalar/product/binary) is the main lever to keep large collections affordable.

## Hardware / deployment
- **Resource profile:** **Memory-bound.** HNSW search is fast when vectors (or their quantized form) fit in RAM. Binary quantization can cut RAM ~32x at a recall cost mitigated by rescoring. mmap/on-disk mode allows working sets larger than RAM but raises p99.
- **Storage assumptions:** Local disk (NVMe strongly preferred for mmap/on-disk and optimizer I/O). Shared-nothing; not designed for high-latency network-attached storage on the hot path.
- **Footprint:** Single binary (Rust). Runs single-node, embedded-ish via local mode, or as a multi-node cluster. No separate coordinator process — Raft runs in-process.
- **Deployment:** Self-hosted (Docker/Kubernetes; official Helm chart and StatefulSet patterns), or SaaS via Qdrant Cloud.

## Bottom line
Reach for Qdrant when you need a dedicated, high-performance vector search engine with rich payload filtering, hybrid (dense+sparse) search, and per-tenant sharding — especially for RAG and recommendation at scale. Do not use it as a system of record or where you need ACID transactions or strict serializable cross-replica consistency. The biggest gotcha: defaults optimize for speed/availability (`write_ordering=weak`, consistency factor 1, single-replica reads) and Raft only protects *metadata* — if you need durable, consistent vector replication you must explicitly raise the consistency factor and write ordering, and there is **no Jepsen report** to lean on.

## Sources
- [Qdrant — Distributed Deployment](https://qdrant.tech/documentation/guides/distributed_deployment/)
- [Qdrant — Storage (WAL, segments, mmap)](https://qdrant.tech/documentation/concepts/storage/)
- [Qdrant — Indexing (HNSW, payload, quantization)](https://qdrant.tech/documentation/concepts/indexing/)
- [DeepWiki — Write Consistency and Replication](https://deepwiki.com/qdrant/qdrant/6.3-write-consistency-and-replication)
- [DeepWiki — System Architecture](https://deepwiki.com/qdrant/qdrant/2-system-architecture)
- [Qdrant LICENSE (Apache 2.0)](https://github.com/qdrant/qdrant/blob/master/LICENSE)
- [Qdrant Cloud Pricing](https://qdrant.tech/pricing/)
- [GitHub issue #5101 — data inconsistency after migration](https://github.com/qdrant/qdrant/issues/5101)
- [GitHub issue #5215 — 3-node replication downtime](https://github.com/qdrant/qdrant/issues/5215)
