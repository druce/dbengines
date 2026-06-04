---
name: Weaviate
slug: weaviate
rank: 70
data_model: Vector
license: BSD-3-Clause (permissive) for OSS core; managed Weaviate Cloud is proprietary
summary: Open-source, AI-native vector database with built-in embedding/RAG modules and hybrid (BM25 + vector) search; leaderless tunable-consistency data plane with a Raft-backed schema.
last_researched: 2026-06-04
confidence: high
---

# Weaviate

> Open-source vector database that bundles embeddings, hybrid search, and RAG plumbing behind one API — availability-favoring leaderless data replication with a strongly-consistent Raft schema, but no ACID transactions.

## Identity
- **Taxonomy / data model:** Vector database storing objects + their vectors together in "collections" (formerly "classes"); supports structured filtering alongside [vector-search-ann](../concepts/vector-search-ann.md). Also a [full-text-search](../concepts/full-text-search.md) engine via BM25, making it effectively a multi-model search/vector store.
- **Storage model:** Object store backed by an LSM-tree key-value store ([lsm-vs-btree](../concepts/lsm-vs-btree.md)); vectors held in a separate vector index. Index choices: HNSW (default, graph-based ANN), flat (brute-force, small datasets), dynamic (flat→HNSW as data grows), plus newer variants ([HFresh in 1.31](https://weaviate.io/blog/weaviate-1-31-release)). Vector compression via product quantization (PQ), binary quantization (BQ), scalar quantization (SQ) to cut RAM ([Weaviate quantization docs](https://docs.weaviate.io/weaviate/concepts/vector-quantization)).
- **Workload:** Online similarity search / retrieval (RAG, semantic search, recommendation) — not OLTP, not OLAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). No HTAP claim.

## Distribution & consistency
- **CAP under partition:** Split by concern. **Data objects: AP** — "favors availability over consistency," BASE/eventually-consistent. **Schema/cluster metadata: CP** — strongly consistent via [consensus-raft-paxos](../concepts/consensus-raft-paxos.md) (Raft, since v1.25) ([Weaviate consistency docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition (data plane), favors availability (PA); else, the latency/consistency tradeoff is **tunable per request** (EL/EC depending on chosen level).
- **Default isolation & what's achievable:** **No ACID transactions and no isolation levels.** Per the Weaviate FAQ: "Weaviate has no notion of transactions, operations always affect exactly a single key, therefore Serializability is not applicable" ([Weaviate FAQ](https://docs.weaviate.io/weaviate/more-resources/faq)). Treat it as eventually consistent per-object (single-key) storage, not a transactional DB. See [isolation-levels](../concepts/isolation-levels.md). ⚠️ unverified — exact concurrent-write conflict semantics for a single object beyond last-write/timestamp resolution.
- **Replication:** Data plane is **leaderless** (Dynamo-style, no primary), with **tunable consistency** levels ONE / QUORUM (n/2+1) / ALL for both reads and writes; **QUORUM is the default for both reads and writes** (write consistency became tunable and defaulted to QUORUM in v1.18, prior to which writes were always ALL). r+w>n yields strong consistency ([consistency docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)). See [replication-models](../concepts/replication-models.md). Anti-entropy via **repair-on-read** (QUORUM/ALL reads fix divergent replicas) and **async replication** using Merkle trees for bulk reconciliation. Deletes resolved via TimeBasedResolution (default since v1.36), DeleteOnConflict, or NoAutomatedResolution ([consistency docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)).
- **Tunable consistency?** Yes — per-query ONE/QUORUM/ALL ([consistency docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)).
- **Clock dependency:** Default deletion-conflict resolution is timestamp-based, so cross-node clock skew can affect which delete wins. See [clocks-and-time](../concepts/clocks-and-time.md). ⚠️ unverified — whether HLCs or only wall clocks are used.

## Schema
- **Schema-on-write.** Collections have defined properties and per-collection vectorizer/index config; auto-schema can infer properties on ingest but a defined schema is standard. Schema changes are Raft-replicated and strongly consistent.
- **Migration/evolution:** Add properties and tenants online; **cannot change a property's data type in place** (requires recreating). ⚠️ unverified — current exact set of allowed in-place schema mutations across versions.
- **Type system:** text, int, number, boolean, date, geoCoordinates, phoneNumber, UUID, object/nested objects, arrays, and cross-references between objects; vectors per object (single or named/multiple vectors). [full-text-search](../concepts/full-text-search.md) inverted index for filterable/searchable text.

## Query interface
- **Language:** **GraphQL** (primary query language), plus **REST** and **gRPC** APIs ([GitHub](https://github.com/weaviate/weaviate)). No SQL. Searches: nearVector/nearText/nearObject, BM25 keyword, and **hybrid** (BM25 + vector fused via RRF or relative scoring).
- **Transactions:** **None** — no multi-statement ACID; per-object writes only, batched for throughput.
- **Native vs app-side:** Native vector ANN, BM25 keyword, hybrid fusion, structured filtering, GroupBy, basic aggregations. Cross-references support graph-like traversal but it is not a full graph query engine. No joins in the relational sense.
- **Stored procedures / UDFs:** No general UDF/stored-proc system. Extensibility is via **modules** — vectorizers (text2vec-openai/cohere/huggingface/transformers/ollama), generative (RAG) modules, rerankers, multimodal — that call external or local models at ingest/query time.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — **sharding** distributes a collection's objects across nodes; **replication factor** copies shards for HA. Resharding of an existing collection is limited; choose shard count up front. ⚠️ unverified — current online-resharding support.
- **Partitioning:** Hash-based sharding; also **multi-tenancy** mode (one shard per tenant) for isolating many small tenants efficiently.
- **Read replicas / consistency:** All replicas are read/write (leaderless); read consistency is the chosen level (ONE may read stale, QUORUM/ALL stronger + repair-on-read).
- **Storage/compute separation:** Largely shared-nothing; data + vector index colocated per node. ⚠️ unverified — degree of compute/storage separation in Weaviate Cloud / BYOC offerings. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** LSM store with a write-ahead log / commit log per shard; group/batch ingestion is the norm. Crash data-loss window depends on flush/WAL settings — see [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact default fsync policy and the resulting data-loss window on power loss.
- **Throughput/latency:** HNSW gives low-latency ANN; recall/latency/RAM traded via efConstruction/ef/maxConnections and quantization. Building/maintaining HNSW is CPU- and RAM-intensive; large indexes typically must fit in RAM unless quantized.
- **Compaction / GC:** LSM compaction runs in the background ([lsm-vs-btree](../concepts/lsm-vs-btree.md)); HNSW index maintenance and tombstone cleanup for deletes add background work that can affect p99 under heavy churn. ⚠️ unverified — published p99 tail figures under sustained delete/update load.

## Operations & maturity
- **Backup/restore:** Native backup module to S3/GCS/Azure/filesystem; supports full and class-scoped backups. No documented continuous PITR. ⚠️ unverified — point-in-time recovery support.
- **Observability:** Prometheus metrics, structured logs; GraphQL `explain`-style query introspection is limited compared to SQL EXPLAIN plans. ⚠️ unverified — depth of query-plan visibility.
- **Upgrade story:** Rolling upgrades on multi-node clusters; Helm chart for Kubernetes. Day-2 burden centers on HNSW RAM sizing, shard/replica planning, and module/model dependency management.
- **Maturity:** Widely adopted in the RAG/LLM wave; active OSS project (weaviate/weaviate). **No Jepsen report exists** as of 2026 — distributed-correctness claims (leaderless tunable consistency, Raft schema) are **not independently formally verified**; treat them as vendor-stated. ⚠️ unverified — absence of any third-party formal/consistency audit.

## Ecosystem & people
- **Canonical use cases:** RAG / LLM retrieval, semantic + hybrid search, recommendations, multimodal search, anomaly/dedup by similarity.
- **Anti-patterns:** Not a system of record or transactional OLTP store (no ACID); not an analytics/OLAP warehouse; overkill for tiny datasets where a flat index or pgvector/[postgresql](postgresql.md) suffices; avoid if you need strong cross-object transactional consistency.
- **Drivers/connectors:** Official clients (Python, JS/TS, Go, Java); integrations with LangChain, LlamaIndex, Haystack; Spark/Kafka and CDC pipelines exist but it is primarily fed by application ingest. Embedding integrations with OpenAI, Cohere, HuggingFace, Ollama, etc.
- **Community/support:** Large community, good docs, commercial support via Weaviate Cloud and enterprise. Learning curve moderate; GraphQL + module config is the main ramp.

## Licensing & cost
- **OSS license:** **BSD-3-Clause** (permissive) for the core engine ([GitHub](https://github.com/weaviate/weaviate)). No post-2018 source-available relicensing of the core. See [license-taxonomy](../concepts/license-taxonomy.md). (Some module/secondary code may carry other permissive licenses — ⚠️ unverified per-module.)
- **Self-managed vs managed:** Self-host OSS free (pay only infra) or use **Weaviate Cloud** (proprietary managed, plus dedicated/BYOC tiers).
- **Lock-in:** Low at the engine level (open core, portable). Managed-tier and module choices (e.g. proprietary vectorizers) create softer lock-in.
- **Cost model:** Cloud pricing reworked Oct 2025 to a **three-dimension model** — vector dimensions stored (per million/month), object storage (per GiB), backup storage (per GiB) — across Flex (~$45/mo), Plus (~$280/mo), Premium (custom/BYOC, HIPAA) tiers ([Weaviate pricing](https://weaviate.io/pricing)). Dimension-based billing means high-dimensional embeddings at scale get expensive fast — quantization is a real cost lever.

## Hardware / deployment
- **Resource profile:** **RAM-bound** when using HNSW — the graph index (and often full-fidelity vectors) want to live in memory; quantization (PQ/BQ/SQ) trades recall for RAM. CPU-bound during index build and query distance computation.
- **Storage assumptions:** Local SSD/NVMe preferred for the LSM store; network-attached storage tolerable but adds latency. Working set ideally in RAM.
- **Footprint:** Single-node, clustered (sharded + replicated), or managed/serverless via Cloud. Not embedded.
- **Deployment:** Docker and **Kubernetes-native** (official Helm chart, StatefulSets); SaaS via Weaviate Cloud; BYOC for enterprise.

## Bottom line
Reach for Weaviate when you need a production vector/hybrid-search store with batteries-included embeddings and RAG modules, an open (BSD) core, and horizontal HA scaling. Do **not** use it as a system of record: there are no ACID transactions, the data plane is eventually consistent (AP) by default, and only the schema is strongly consistent via Raft. The biggest gotchas are (1) RAM cost of HNSW and dimension-based cloud billing at scale, and (2) distributed-correctness claims have no Jepsen/third-party audit — validate consistency behavior for your own r+w>n configuration before trusting it with critical data.

## Sources
- [Weaviate GitHub (license, overview)](https://github.com/weaviate/weaviate)
- [Consistency — Weaviate docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)
- [Weaviate FAQ (transactions / ACID)](https://docs.weaviate.io/weaviate/more-resources/faq)
- [Replication architecture — Weaviate docs](https://docs.weaviate.io/weaviate/concepts/replication-architecture)
- [Vector quantization (PQ/BQ/SQ) — Weaviate docs](https://docs.weaviate.io/weaviate/concepts/vector-quantization)
- [Vector index types — Weaviate docs](https://docs.weaviate.io/weaviate/config-refs/indexing/vector-index)
- [Hybrid search — Weaviate docs](https://docs.weaviate.io/weaviate/concepts/search/hybrid-search)
- [Weaviate Cloud pricing](https://weaviate.io/pricing)
- [Weaviate 1.31 release notes](https://weaviate.io/blog/weaviate-1-31-release)
