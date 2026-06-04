---
name: Microsoft Azure AI Search
slug: microsoft-azure-ai-search
rank: 57
data_model: Search engine
license: Proprietary (managed-only SaaS)
summary: Fully managed Lucene-based full-text + vector search service on Azure; a RAG retrieval layer, not a system of record.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Azure AI Search

> Azure's managed full-text + vector + hybrid search service (formerly Azure Cognitive Search / Azure Search) — a secondary retrieval index for search UX and RAG grounding, explicitly not designed as a primary data store.

## Identity
- **Taxonomy / data model:** [full-text-search](../concepts/full-text-search.md) engine over JSON documents, with first-class [vector-search-ann](../concepts/vector-search-ann.md) (HNSW) and hybrid (BM25 + vector via RRF). Search-engine category (also vector). Documents are schema-bound fields; the corpus unit is an *index* inside a *search service*.
- **Storage model:** inverted indexes for tokenized text; separate vector indexes for embeddings. Built on Apache Lucene for the text engine, with BM25 scoring ([Full-text search / Lucene query architecture](https://learn.microsoft.com/en-us/azure/search/search-lucene-query-architecture)). On-disk inverted index + HNSW graph for vectors. ⚠️ unverified — Microsoft's vector-index doc does not explicitly state HNSW fields must be fully RAM-resident at query time; it documents per-tier vector-storage limits ([vector index overview](https://learn.microsoft.com/en-us/azure/search/vector-store)) and the practical RAM-bound behavior of HNSW ANN is an inference from how HNSW works generally, not an explicit Microsoft guarantee.
- **Workload:** retrieval/search (OLTP-ish read-heavy point/ranked lookups), not analytics. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — it is a derived/secondary index fed from external sources, not a transactional or analytical database.

## Distribution & consistency
- **CAP under partition:** N/A in the classic single-leader sense — it is a single-region managed service backed by replicas; within a service it favors availability for reads. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** not formally characterized by Microsoft. Practically: writes go to one primary replica and replicate **asynchronously** to other replicas; reads are load-balanced across all replicas, so reads are eventually consistent (else-case favors latency/availability over consistency).
- **Consistency:** **eventual consistency, no monotonic reads.** A 200 on an indexing request means durability, not immediate searchability; documents become queryable after a delay (seconds, load-dependent) and not necessarily in ingestion order. Concurrent updates can make a query return temporarily incomplete results ([Update or rebuild an index](https://learn.microsoft.com/en-us/azure/search/search-howto-reindex)). A best-effort `sessionId` (sticky session) targets the same replica set for more consistent results — best effort only.
- **Isolation/transactions:** **no multi-document transactions.** Writes are per-document upsert/merge/delete (`mergeOrUpload` etc.); each document operation is atomic, but there is no cross-document atomicity or isolation in the [isolation-levels](../concepts/isolation-levels.md) sense. Optimistic concurrency on a single document via ETag. Treat "ACID" as inapplicable.
- **Replication:** single primary replica for writes, read replicas for queries; async replication; automatic primary promotion on zone failure (~seconds of write unavailability) ([Reliability in Azure AI Search](https://learn.microsoft.com/en-us/azure/reliability/reliability-ai-search)). See [replication-models](../concepts/replication-models.md). Zone-redundant: with ≥2 replicas, Azure attempts to spread replicas across availability zones (Basic tier and up).
- **Tunable consistency?** No per-query consistency levels; only the `sessionId` sticky-session hint.
- **Clock dependency:** none for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Each index has an explicit field schema (types, and per-field flags: searchable, filterable, sortable, facetable, retrievable). Vector fields declare dimensions and an HNSW/algorithm profile.
- **Migration/evolution:** mostly **rigid** — you can add new fields to an existing index, but changing a field's type or most attributes requires dropping and rebuilding the index (no in-place ALTER of existing fields) ([Update or rebuild an index](https://learn.microsoft.com/en-us/azure/search/search-howto-reindex)). Rebuild = recreate + reload from the source of truth.
- **Type system:** strings, numbers, booleans, `DateTimeOffset`, `GeographyPoint` (geo-spatial filtering/sorting), complex/nested objects, collections (arrays), and `Collection(Edm.Single)` vector fields. JSON-document oriented; no native joins.

## Query interface
- **Language:** REST API and SDKs (.NET, Java, JavaScript, Python) — **API-only**, no SQL. Full-text uses a simple query syntax or the **Lucene query syntax**; filtering/sorting use **OData** expression syntax ([OData filter reference](https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter)). Vector queries via the search API; hybrid combines BM25 + vector with Reciprocal Rank Fusion.
- **Transactions:** none beyond single-document atomicity (see above).
- **Native vs app-side:** native full-text, fuzzy, autocomplete/suggestions, facets, filters, geo-search, scoring profiles (up to 100/index), synonym maps. **Semantic ranker** adds a Bing-derived deep-learning reranker over the top BM25/RRF results ([Semantic ranking overview](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview)). **No joins** — denormalize at index time. Aggregations limited to facet counts, not general GROUP BY.
- **Stored procedures / UDFs:** none. Server-side enrichment happens in **skillsets** (the AI-enrichment pipeline: chunking, embedding via integrated vectorization, OCR, entity extraction, custom Web API skills) during indexing, not at query time.

## Scaling & topology
- **Vertical + horizontal within a service:** scale **partitions** (1–N, storage + indexing parallelism) and **replicas** (1–12, query throughput + availability). Capacity billed as Search Units = partitions × replicas.
- **Sharding:** automatic — an index is distributed across the service's partitions; you do not manage shard keys. Resharding = change partition count (a re-provisioning operation, can be slow for large indexes); tier sets max partitions/storage.
- **Read replicas:** all non-primary replicas serve reads; reads are eventually consistent (no read-your-writes guarantee without `sessionId` best-effort).
- **Storage/compute separation:** No true [storage-compute-separation](../concepts/storage-compute-separation.md) in the dedicated model — replicas hold full copies and HNSW vectors live in replica RAM. The **Serverless (preview)** tier adds consumption-based auto-scaling (Compute Units/hr + per-GB storage), moving toward elastic capacity, but is preview, no SLA, and not for production.

## Performance & durability
- **Write path:** indexing request returns 200 on durable acceptance; document is searchable after async processing and replication — a few seconds typically. There is no user-visible WAL/fsync knob (managed). See [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window:** if the primary replica's zone fails before async replication completes, un-replicated writes can be lost ([Reliability](https://learn.microsoft.com/en-us/azure/reliability/reliability-ai-search)).
- **Throughput/latency:** add replicas for query QPS and lower tail latency; add partitions for indexing throughput and larger corpora. Vector (HNSW) queries are RAM-bound; p99 degrades when the vector index exceeds memory budget for the tier. Indexer-based (pull) ingestion can occasionally double-process a document (buffer overlap) — harmless to stored data but lengthens time-to-consistency.
- **Compaction/GC:** managed and not user-visible; no vacuum knobs. Rebuilds are the main heavy operation.

## Operations & maturity
- **Backup/restore:** **no self-service backup/restore / PITR** — Microsoft positions it as a non-primary store. Use the `index-backup-restore` sample (.NET/Python) to export index definition + docs to JSON, or rebuild from the source of truth ([Reliability](https://learn.microsoft.com/en-us/azure/reliability/reliability-ai-search)).
- **Observability:** Azure Monitor metrics, diagnostic logs, alerts; per-query diagnostics and indexer execution history/error logs; no EXPLAIN-style query planner output.
- **Upgrade story:** fully managed — no version upgrades to run. **Caveat:** Microsoft performs unscheduled maintenance with no advance notice and no scheduling window; single-replica services can see brief interruptions — hence ≥2 replicas (read SLA) / ≥3 (read-write SLA) for production.
- **Maturity:** GA since 2015 (as Azure Search), widely used; renamed Azure Cognitive Search (2021) then **Azure AI Search** (2023). No public Jepsen report — ⚠️ unverified — no formal external consistency verification exists; consistency claims here are from Microsoft docs. Known failure mode: treating it as a source of truth and losing data on accidental index deletion with no backup.
- **SLA:** 99.9%, and only when on a billable tier with ≥2 replicas (reads) / ≥3 (read-write); Free tier has no SLA ([Reliability](https://learn.microsoft.com/en-us/azure/reliability/reliability-ai-search)).

## Ecosystem & people
- **Canonical use cases:** site/app search; enterprise document search; **RAG grounding for LLMs/agents** (hybrid + semantic ranking + integrated vectorization), now including "agentic retrieval" (multi-query LLM-planned retrieval over knowledge sources). Tight integration with Azure OpenAI / Microsoft Foundry.
- **Anti-patterns:** primary/system-of-record database; anything needing multi-document transactions, strong read-your-writes, or relational joins; cost-sensitive workloads where a self-hosted [opensearch](opensearch.md)/[elasticsearch](elasticsearch.md) or pgvector ([postgresql](postgresql.md)) would do; multi-cloud or on-prem (Azure-only).
- **Ingestion/connectors:** push API (any source, real-time) or pull **indexers** for Azure Blob Storage, ADLS Gen2, Cosmos DB, Azure SQL, SharePoint, OneLake, etc., with change tracking. Skillsets for chunking/embedding/OCR/custom enrichment.
- **Community & docs:** large; Microsoft Learn docs are extensive and current; commercial support via Azure. Learning curve moderate — index/indexer/skillset model and the eventual-consistency + non-primary-store mindset trip up newcomers.

## Licensing & cost
- **License:** **proprietary, managed-only SaaS.** No self-hosted or open-source edition; the text engine uses Apache Lucene internally but the service is closed. See [license-taxonomy](../concepts/license-taxonomy.md). No relicensing event applies (it was never OSS).
- **Self-managed vs managed:** managed-only. **Lock-in:** API surface, skillsets, integrated vectorization, and Azure-native connectors are Azure-specific; migrating off means re-implementing on another engine.
- **Cost model:** **Dedicated** = per-Search-Unit/hour (partitions × replicas) by tier (Free, Basic, S1–S3/S3 HD, L1–L2 storage-optimized); fixed regardless of utilization, so it can be expensive at low usage and capacity-capped at high usage. **Serverless (preview)** = Compute Units/hr + per-GB storage (no SLA). Note S3 HD has no indexers (push-only).

## Hardware / deployment
- **Resource profile:** **memory-bound for vectors** in practice (HNSW ANN is RAM-intensive); otherwise disk + CPU for text. ⚠️ unverified — "vector working set must fit entirely in RAM" is the general behavior of HNSW, not an explicit Microsoft guarantee; Microsoft documents per-tier vector-storage limits rather than a hard RAM-residency requirement.
- **Storage assumptions:** abstracted (managed Azure storage); no user choice of NVMe vs network-attached.
- **Footprint:** clustered managed service (replicas × partitions); single-region only — multi-region resilience is a DIY pattern (deploy N services, sync indexes, front with load balancer).
- **Deployment:** SaaS on Azure only; no containers/k8s/on-prem; provision via portal, ARM/Bicep, CLI, or SDK.

## Bottom line
Reach for Azure AI Search if you are on Azure and need a managed full-text + vector + hybrid retrieval layer for search UX or LLM/RAG grounding without operating Elasticsearch/OpenSearch yourself — the integrated vectorization, semantic ranker, and agentic retrieval are genuinely convenient. Do not reach for it as a system of record: there are no transactions, no read-your-writes by default, eventual consistency with no monotonic-read guarantee, and **no self-service backup/restore**. The single biggest gotcha is exactly that — it is a *secondary* index; if you delete an index without your own backup, the only recovery is rebuilding from the original source.

## Sources
- [Introduction to Azure AI Search — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search)
- [Full-text search (Lucene query architecture, BM25) — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-lucene-query-architecture)
- [Reliability in Azure AI Search — Microsoft Learn](https://learn.microsoft.com/en-us/azure/reliability/reliability-ai-search)
- [Update or rebuild an index (eventual consistency, sessionId) — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-howto-reindex)
- [Vector index overview (HNSW, in-memory) — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/vector-store)
- [Vector search overview — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/vector-search-overview)
- [Semantic ranking overview — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview)
- [OData filter reference — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter)
- [Choose a pricing model and service tier — Microsoft Learn](https://learn.microsoft.com/en-us/azure/search/search-sku-tier)
