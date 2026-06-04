---
name: Milvus
slug: milvus
rank: 56
data_model: Vector
license: Apache 2.0 (permissive); managed Zilliz Cloud is proprietary
summary: Cloud-native, horizontally scalable vector database with disaggregated storage/compute, tunable consistency, and every mainstream ANN index — built for billion-scale similarity search, not for transactions.
last_researched: 2026-06-04
confidence: high
---

# Milvus

> Open-source (Apache 2.0) distributed vector database that scales ANN search to billions of vectors via stateless compute over object storage and a log-broker WAL — pick it for large-scale similarity search, not as a system of record.

## Identity
- **Taxonomy / data model:** Vector database. Stores collections of entities = primary key + one or more vector fields + scalar fields; supports vector similarity search with scalar metadata filtering. See [vector-search-ann](../concepts/vector-search-ann.md). Multi-model-lite: scalar fields, JSON (with JSON shredding/indexing in 2.6), arrays, and full-text/BM25 sparse-vector search in recent versions, but it is not a general-purpose document or relational store.
- **Storage model:** Hybrid log-structured. Incoming writes land in **growing segments** in memory fed from a write-ahead log broker; these are sealed into immutable **sealed segments** persisted as columnar files in object storage, then indexed ([Milvus segments are immutable, "write once, read many"](https://milvus.io/docs/architecture_overview.md)). Conceptually closer to [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM (append + compaction) than B-tree. ANN indexes (HNSW graph, IVF lists, DiskANN, etc.) are built per sealed segment.
- **Workload:** OLAP-leaning analytical/search workload over vectors, not OLTP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — no transactional path to speak of.

## Distribution & consistency
- **CAP under partition:** CP-leaning. Coordinators and metadata rely on **etcd** (Raft, strongly consistent) for cluster topology and schema ([Milvus uses etcd for "extremely high availability, strong consistency, and transaction support"](https://milvus.io/docs/architecture_overview.md)). Data durability depends on the log broker (Pulsar/Kafka/Woodpecker) and object storage. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** The docs explicitly frame consistency via [PACELC](https://milvus.io/docs/consistency.md): in the else (no-partition) case Milvus trades latency for consistency — higher consistency = higher search latency, lower consistency = faster but stale reads.
- **Default isolation & what's achievable:** No transactional isolation in the SQL sense. Instead Milvus exposes four **tunable read-consistency levels**: Strong, Bounded staleness (**default**), Session, and Eventually ([the default consistency level in Milvus is bounded staleness](https://milvus.io/docs/consistency.md)). Implemented via a **GuaranteeTs** timestamp: a query waits until all data up to GuaranteeTs is visible to query nodes. Strong sets GuaranteeTs to the latest system timestamp; Session uses the client's last write ts (read-your-writes); Eventually skips the check entirely ([consistency.md](https://milvus.io/docs/consistency.md)). See [isolation-levels](../concepts/isolation-levels.md). Note: "ACID-configurable" claims really mean *durability by default + optional strong read consistency*, not multi-statement atomic transactions — there is no transaction primitive and a batch insert can partially succeed.
- **Replication:** Durability/replication is delegated to the WAL layer. Streaming/query nodes are stateless replicas reading from shared object storage; per-shard ordering comes from the log broker. Failover = reschedule stateless nodes on Kubernetes; no split-brain on the data plane because storage is shared and metadata is in etcd. See [replication-models](../concepts/replication-models.md). Newer **Woodpecker** WAL (Milvus 2.6) in its QuorumBuffer mode acks a write after replicating to ≥2 of 3 quorum nodes, then async-flushes to object storage; a zero-disk MemoryBuffer mode also exists ([Woodpecker blog](https://milvus.io/blog/we-replaced-kafka-pulsar-with-a-woodpecker-for-milvus.md), [Woodpecker architecture](https://milvus.io/docs/woodpecker_architecture.md)).
- **Tunable consistency?** Yes — per-search/query consistency level (the four levels above), one of Milvus's distinguishing features.
- **Clock dependency:** Uses logical/hybrid timestamps (Timestamp Oracle assigning monotonic ts) for ordering and GuaranteeTs, not wall-clock TrueTime. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, with flexibility:** Collections have a defined schema (fields + types), but a **dynamic field** option allows schemaless JSON-style extra attributes. Mostly schema-on-write for typed/indexed fields, schema-on-read for dynamic ones.
- **Migration/evolution:** Limited online DDL. Adding fields/partitions is supported in recent versions; deep schema changes historically meant recreating the collection. ⚠️ unverified — exact set of non-locking `ALTER`-equivalent operations varies sharply by version; check release notes for your build.
- **Type system:** Float/binary/float16/bfloat16 dense vectors, **sparse vectors** (for BM25/full-text and learned sparse retrieval), scalar types (int, float, bool, varchar), JSON (with JSON shredding indexing in 2.6), and arrays. Geospatial: not a focus.

## Query interface
- **Language:** API-only via SDKs (Python/`pymilvus`, Go, Java, Node.js, C++/REST). No SQL. Operations: `search` (ANN), `query` (scalar filter / get), `insert`, `upsert`, `delete`, hybrid/multi-vector search with rerankers. Boolean filter expressions (e.g. `price < 10 && category == "x"`) attach scalar predicates to vector search.
- **Transactions:** None in the classic sense. Single insert/upsert/delete are the unit of work; a batch insert may **partially succeed** ([insert/upsert/delete behavior](https://milvus.io/docs/insert-update-delete.md)). Upsert = delete + insert under the hood, so it can compromise performance. Durability is provided, multi-statement atomicity is not.
- **Native vs app-side:** Native ANN search, scalar filtering, range search, hybrid search, and reranking. **No joins.** Aggregations are minimal (count, grouping search) — not an analytics SQL engine.
- **Stored procedures / UDFs:** None. Logic lives in the application; custom rerankers/functions are configured, not user-coded server-side.

## Scaling & topology
- **Vertical vs horizontal:** Built for **horizontal** scale. Three modes: **Milvus Lite** (embedded Python lib for prototyping/edge — see [embedded-databases](../concepts/embedded-databases.md)), **Standalone** (single-node server), and **Distributed cluster** (the design point).
- **Sharding/partitioning:** Collections split into shards (mapped to log-broker channels) and **partitions** (user-defined, e.g. per-tenant/date — supports partition-key for multi-tenancy). Segments are the physical query/index unit. Resharding existing collections is not trivial; choose shard count up front. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas:** Query nodes load sealed segments from object storage and can be replicated for read scale-out; read consistency across them is governed by the chosen consistency level + GuaranteeTs.
- **Storage/compute separation:** Yes — a core selling point. "Fully disaggregated storage and compute," stateless worker nodes over shared object storage ([architecture_overview.md](https://milvus.io/docs/architecture_overview.md)). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Writes go to the **log broker WAL** (Pulsar, Kafka, or the newer object-storage-native Woodpecker) before being acked; data is buffered in growing segments, periodically flushed/sealed to object storage, then indexed. See [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window on crash:** bounded by what is acked in the WAL — with Woodpecker (QuorumBuffer mode) an ack means ≥2-of-3 quorum replication before async flush ([Woodpecker blog](https://milvus.io/blog/we-replaced-kafka-pulsar-with-a-woodpecker-for-milvus.md)); with Kafka/Pulsar durability is whatever that broker is configured for. ⚠️ unverified — precise fsync/flush-interval semantics depend on broker config and Milvus version.
- **Throughput/latency:** Optimized for high-recall ANN at low latency; supports mmap, quantization (PQ/SQ), and GPU indexes (CAGRA) for throughput. p99 is sensitive to: querying **growing (unindexed) segments** with brute force, compaction/flush pressure, and high-cardinality scalar filters. Cold query nodes must load segments from object storage, adding warm-up latency.
- **Compaction / GC:** Background **compaction** merges small/deleted-heavy segments; deletes are tombstones (soft delete) reclaimed by compaction — heavy delete/upsert workloads degrade query performance until compaction catches up, a real p99 driver.

## Operations & maturity
- **Backup/restore:** `milvus-backup` tool for collection-level backup/restore to object storage; snapshots via object-storage + etcd metadata. Point-in-time recovery is not a first-class relational-style PITR.
- **Observability:** Prometheus metrics + Grafana dashboards, Attu GUI for inspection. No SQL `EXPLAIN`; search has search-params/profiling but not a relational query planner. Slow-query visibility is limited compared to RDBMSs.
- **Upgrade story:** Rolling upgrades supported on Kubernetes via the operator/Helm; major-version jumps (e.g. 2.x line) have had migration steps. Day-2 burden of the **distributed** mode is significant: you operate etcd, an object store, a log broker, and several coordinator/worker node types — many teams run Standalone or Zilliz Cloud to avoid this.
- **Maturity:** Widely deployed, LF AI & Data project, large community. **No public Jepsen report exists** for Milvus as of June 2026 — its distributed-consistency guarantees are documented by the vendor but not independently formally verified. ⚠️ unverified — treat strong-consistency-under-failure claims as vendor-stated, not Jepsen-confirmed. Known sharp edges: partial-success batch inserts, no dedup on plain insert (duplicate PKs unless you use upsert), compaction-driven p99.

## Ecosystem & people
- **Canonical use cases:** RAG / LLM retrieval, semantic & image/audio search, recommendation, dedup/anomaly detection — anywhere you need billion-scale ANN with metadata filtering.
- **Anti-patterns:** System of record / transactional OLTP (no transactions, partial-success writes); small datasets where pgvector/SQLite-VSS/a library like FAISS suffices (Milvus's distributed machinery is overkill — use Milvus Lite or another tool); workloads needing joins, SQL analytics, or strict relational integrity. See pgvector / [qdrant](qdrant.md) / [weaviate](weaviate.md) / [chroma](chroma.md) for lighter or differently-shaped alternatives.
- **Drivers/connectors:** pymilvus (primary), Go/Java/Node SDKs, REST; integrations with LangChain, LlamaIndex, Spark, and CDC tooling. BI/dbt: not applicable (no SQL).
- **Community/support:** Large OSS community, good docs, active releases; commercial support and managed service from Zilliz. Learning curve: easy in Lite/Standalone, steep to operate the distributed cluster well.

## Licensing & cost
- **OSS license:** **Apache 2.0**, permissive — under the LF AI & Data Foundation, with Zilliz as primary contributor ([GitHub repo / FAQ](https://milvus.io/docs/product_faq.md)). No post-2018 relicensing rug-pull; the core stays Apache 2.0. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-host (Lite/Standalone/distributed) for free, or **Zilliz Cloud** (proprietary managed: Serverless, Dedicated, BYOC). Lock-in is modest at the API level (open-source server you can run yourself), higher if you adopt Zilliz Cloud-only features.
- **Cost model:** Self-managed = your infra (compute nodes + object storage + etcd + broker). Zilliz Cloud = consumption/serverless or provisioned. At scale, object-storage-backed design keeps cold-data cheap; the cost driver is RAM for in-memory indexes (HNSW/IVF) — DiskANN/mmap/quantization exist precisely to push that down.

## Hardware / deployment
- **Resource profile:** **Memory-bound** for in-memory indexes (HNSW/IVF want the working set, and often the index, in RAM); **DiskANN** lets datasets exceed RAM at a recall/latency cost; GPU indexes (CAGRA) are CPU/GPU-bound. Scalar-filter-heavy queries add CPU.
- **Storage assumptions:** Shared **object storage** (S3 / Azure Blob / MinIO) for durable segment + index files; local NVMe helps for DiskANN and caches. Tolerant of network-attached storage by design.
- **Footprint:** Embedded (Milvus Lite), single-node (Standalone), or clustered/distributed. The distributed cluster is **Kubernetes-native** (operator/Helm, StatefulSets for stateful deps like etcd/broker, stateless Deployments for workers).
- **Deployment:** Self-managed on-prem/cloud, or SaaS via Zilliz Cloud. K8s-friendly is a core design goal.

## Bottom line
Reach for Milvus when you need to do similarity search over tens of millions to billions of vectors with metadata filtering and want a cloud-native system that scales compute independently of storage; its tunable consistency and full menu of ANN indexes are genuine strengths. Do not reach for it as a transactional system of record — there are no real transactions, plain inserts don't dedup, and batch writes can partially succeed. The single biggest gotcha: operating the **distributed** mode means running etcd + object store + a log broker + multiple node types, so unless you truly need that scale, use Milvus Lite/Standalone or Zilliz Cloud — and remember its strong-consistency claims are vendor-documented, not Jepsen-verified.

## Sources
- [Milvus Architecture Overview](https://milvus.io/docs/architecture_overview.md)
- [Milvus Consistency Level docs](https://milvus.io/docs/consistency.md)
- [Storage/Computing Disaggregation (four layers)](https://milvus.io/docs/four_layers.md)
- [In-memory / index types](https://milvus.io/docs/index.md)
- [Insert, Upsert & Delete behavior](https://milvus.io/docs/insert-update-delete.md)
- [Product FAQ (license / LF AI & Data)](https://milvus.io/docs/product_faq.md)
- [Milvus 2.6 release notes](https://milvus.io/docs/v2.6.x/release_notes.md)
- [Woodpecker WAL architecture](https://milvus.io/docs/woodpecker_architecture.md) / [Woodpecker blog post](https://milvus.io/blog/we-replaced-kafka-pulsar-with-a-woodpecker-for-milvus.md)
- [milvus-io/milvus on GitHub](https://github.com/milvus-io/milvus)
- [Milvus (vector database) — Wikipedia](https://en.wikipedia.org/wiki/Milvus_(vector_database))
