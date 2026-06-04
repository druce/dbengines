---
name: Pinecone
slug: pinecone
rank: 48
data_model: Vector
license: Proprietary / closed-source (managed SaaS only)
summary: Fully-managed, serverless vector database for AI/RAG retrieval; object-storage-backed with separated read/write paths and no self-hosted option.
last_researched: 2026-06-04
confidence: high
---

# Pinecone

> A closed-source, fully-managed serverless vector database purpose-built for similarity search and RAG retrieval — you trade self-hosting and SQL for zero ops, billions of vectors on object storage, and per-operation billing.

## When to use

**Use Pinecone if:**
- ✅ You want production vector search (RAG, semantic search, recommendations, agent memory) with zero operational burden
- ✅ You need to scale to billions of vectors on object storage without provisioning or managing nodes
- ✅ You want hosted embedding/reranking (Pinecone Inference) and a small API surface so the learning curve stays low
- ✅ You can live entirely on a managed, closed-source SaaS and prefer per-operation billing

**Avoid Pinecone if:**
- ❌ You need a system of record with real transactions, SQL, or joins — it has no multi-record transactions and is eventually consistent (LSN/read-your-writes is per-namespace and vendor-asserted, with no Jepsen validation)
- ❌ You require self-hosting, air-gapped, or on-prem deployment (managed-only; BYOC runs in your VPC but is still proprietary)
- ❌ You run sustained high QPS on shared serverless — per-request read pricing and the 100 RPS/namespace limit bite (Dedicated Read Nodes mitigate but cost more)
- ❌ You need exact (non-approximate) search, or a small/low-budget project where pgvector or an OSS engine avoids a separate vendor and bill

## Identity
- **Taxonomy / data model:** specialized [vector-search-ann](../concepts/vector-search-ann.md) database. Records are `(id, dense vector, optional sparse vector, metadata JSON)`; query by approximate nearest-neighbor (ANN) over similarity metrics (cosine, dot product, euclidean). Not a general-purpose store — no relational/document/graph model. Adds native full-text/keyword search (public preview, 2025) and hosted embedding/reranking via Pinecone Inference. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) (this is neither OLTP nor OLAP — it is online retrieval/serving).
- **Storage model:** object-storage-backed. Vectors persist as immutable files called **slabs** in distributed object storage (S3/GCS/Azure Blob). The write path is described by Pinecone as an [LSM](../concepts/lsm-vs-btree.md)-style design: writes land in an in-memory memtable, then flush to slabs. ([Pinecone serverless architecture](https://docs.pinecone.io/reference/architecture/serverless-architecture), [slab architecture](https://www.pinecone.io/learn/slab-architecture/))
- **Index algorithms:** notably **not HNSW**. Small slabs use Pinecone's proprietary "Ananas" (Fast Johnson-Lindenstrauss Transform / random projections), medium slabs use Product Quantization Fast Scan (PQFS), large slabs use IVF (inverted file / cluster-based). The system adaptively merges small slabs into larger ones with heavier indexing. ([Pinecone how-it-works](https://www.pinecone.io/how-pinecone-works/))
- **Workload:** online vector retrieval for AI applications (semantic search, RAG, recommendations, agent memory). Not HTAP, not analytical SQL.

## Distribution & consistency
- **CAP under partition:** managed multi-tenant service over object storage; not framed in classic CAP terms. Reads favor availability and low latency; durability rests on the underlying object store. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — Pinecone publishes no formal PACELC characterization. In practice: **eventually consistent** persistent layer with a **read-your-writes** freshness layer (see below); else-case design clearly favors latency/availability over global consistency.
- **Default isolation & what's achievable:** **no multi-record transactions and no traditional isolation levels** ([isolation-levels](../concepts/isolation-levels.md) does not apply — there is no SQL transaction model). Upserts are per-record: an upsert replaces a vector ID atomically at the single-record level. There is no documented atomic multi-record commit or rollback. Do not treat "consistency" claims here as ACID. ([upsert/update data](https://docs.pinecone.io/guides/data/update-data))
- **Consistency model:** **eventual consistency**, but with a strong freshness guarantee via LSN tracking. Each write gets a monotonically increasing log sequence number (LSN); a query carrying an LSN ≥ a write's LSN reflects that write. Reads check the memtable first, so just-written records are immediately queryable before they flush to object storage. Staleness is "seconds, not minutes/hours" per Pinecone. ([data freshness](https://docs.pinecone.io/guides/data/data-freshness/understanding-data-freshness))
- **Replication / failover:** managed internally; durability/HA inherited from the cloud object store (multi-AZ). No user-visible [replication](../concepts/replication-models.md) topology or split-brain tuning — it is a black box. Read scaling via stateless query executors and optional Dedicated Read Nodes.
- **Tunable consistency?** No per-query consistency levels (unlike Dynamo/Cassandra). You can poll/compare LSNs to confirm a write is visible.
- **Clock dependency:** correctness rests on per-namespace LSN ordering, not synchronized wall clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** essentially schemaless for vectors + flexible metadata. An index fixes vector **dimension** and **similarity metric** at creation; these cannot be changed later (you create a new index to change them). Metadata is arbitrary JSON with typed fields.
- **Migration / evolution:** no online DDL concept; reshaping (e.g., changing dimension/metric) means a new index and re-ingest. Full-text search requires defining searchable fields (schema, up to 100 fields).
- **Type system:** dense float vectors (up to 20,000 dims), sparse vectors (up to 2,048 non-zero values, ~4.2B dimensionality), and metadata of strings, numbers, booleans, and string lists. Filterable metadata capped at 40 KB per record. ([limits](https://docs.pinecone.io/docs/limits))

## Query interface
- **Language:** **API-only** — REST/gRPC plus official SDKs (Python, Node.js, Java, Go, .NET). No SQL, no query DSL. Core ops: `upsert`, `query` (top-k ANN + metadata filter), `fetch`, `update`, `delete`, `list`, plus hosted `embed`/`rerank`/`search` (Inference).
- **Transactions:** none in the SQL sense — single-record atomic upsert only; no multi-statement ACID, no rollback.
- **Native vs app-side:** ANN search, metadata filtering, hybrid dense+sparse search, and reranking are native. No joins, no aggregations, no window functions — those are application concerns. `top_k` capped at 10,000; result payload capped at 4 MB.
- **Stored procedures / UDFs:** none.

## Scaling & topology
- **Vertical vs horizontal:** horizontal and automatic. Serverless indexes scale to billions of vectors on object storage with no node provisioning. Reads and writes scale on **separate paths** so queries never throttle writes and vice versa. ([why serverless](https://www.pinecone.io/blog/why-serverless/))
- **Sharding / partitioning:** indexes are partitioned into **namespaces**; every read/write is scoped to one namespace and each namespace is stored separately (physical isolation — the recommended multitenancy pattern, with thousands of namespaces per index). No manual shard management or painful resharding.
- **Read replicas / read consistency:** stateless query executors cache slabs on local SSD; **Dedicated Read Nodes (DRN)** (GA-track, launched Dec 2025) give provisioned, predictable read capacity that bypasses the 100 RPS/namespace rate limit. Reads are eventually consistent with the LSN freshness guarantee above. ([Pinecone DRN](https://www.infoq.com/news/2025/12/pinecone-drn-vector-workloads/))
- **Storage/compute separation:** yes — a defining trait. Vectors live in object storage; compute auto-scales independently. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** writes are logged with an LSN, buffered in an in-memory memtable, then flushed to immutable slabs in object storage. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — Pinecone does not publish the exact crash/data-loss window of unflushed memtable writes; durability is asserted to come from the logged write + object-store persistence, but the precise fsync/ack semantics are not documented.
- **Throughput / latency:** typical serverless query latency ~50–100 ms; throughput rate-limited to **100 RPS per namespace** on shared serverless (DRN removes this). Tail latency can rise on cold slabs (object-store fetch when not cached on SSD); DRN exists specifically to make p99 predictable for spiky/high-QPS workloads. ([limits](https://docs.pinecone.io/docs/limits), [Pinecone DRN](https://blocksandfiles.com/2025/12/01/pinecone-dedicated-read-nodes/))
- **Compaction / GC:** background slab merging (small → large slabs) is the analog of LSM compaction; managed automatically, invisible to the user. Cold-slab fetches and compaction are the main p99 risk factors, and the user has no knobs over them.

## Operations & maturity
- **Backup/restore:** serverless supports **backups** of indexes (and restore to a new index); legacy pod-based indexes used "collections" for the same purpose. No user-managed PITR to an arbitrary timestamp.
- **Observability:** console metrics, usage dashboards, and per-namespace stats; you can read the current LSN to verify write visibility. No EXPLAIN/query-plan concept (there is no query planner exposed).
- **Upgrade story:** fully managed — no version upgrades for the user. Note the major **pod-based → serverless** generational shift: pod indexes are legacy; all new indexes are serverless. Migrating off pods is a re-ingest/restore exercise, not transparent.
- **Maturity:** mature, widely deployed managed service (founded 2019; serverless GA 2024; DRN Dec 2025). SOC 2 Type II and HIPAA compliance offered; CMEK and private networking on Enterprise. **No Jepsen report exists** for Pinecone — consistency claims rest on vendor docs only, which is a gap to weigh for correctness-critical use. ⚠️ unverified — no independent formal verification of the eventual-consistency/LSN model.

## Ecosystem & people
- **Canonical use cases:** RAG retrieval, semantic search, recommendation, agent/long-term memory, dedup/anomaly via embeddings. Strong fit when you want managed vector search and don't want to run infrastructure.
- **Anti-patterns:** as a system of record or primary database (no transactions, no SQL, no joins); when you need self-hosting / air-gapped / on-prem (managed-only, though BYOC exists for VPC deployment); when you need strict relational consistency; small/low-budget projects where pgvector in an existing [postgresql](postgresql.md) or an OSS engine ([qdrant](qdrant.md), [weaviate](weaviate.md), [milvus](milvus.md), [chroma](chroma.md)) avoids a separate vendor and bill; workloads needing exact (non-approximate) search.
- **Integrations:** LangChain, LlamaIndex, Haystack; connectors/SDKs across major languages; hosted embedding + reranking models (Pinecone Inference) reduce the need for a separate embedding service.
- **Community / docs / support:** large community, strong docs, commercial support tiers. Learning curve is low — the API surface is small.

## Licensing & cost
- **License:** **proprietary, closed-source, managed SaaS** (with a BYOC/Dedicated option that runs in your cloud account). No OSS edition; not in scope for [license-taxonomy](../concepts/license-taxonomy.md) copyleft/permissive/source-available distinctions — it is simply closed. Lock-in is real: proprietary index format, API, and hosted models; portability means re-embedding/re-ingesting elsewhere.
- **Plans:** Starter (free; AWS us-east-1, 2 GB, capped units), Standard ($50/mo minimum), Enterprise ($500/mo minimum, private networking, CMEK, HIPAA), and Dedicated/BYOC (custom). ([pricing](https://www.pinecone.io/pricing/))
- **Cost model:** serverless bills three usage axes — **read units, write units, and storage** (e.g., Standard ~$0.33/GB-mo storage, ~$4/M write units, ~$16/M read units; Enterprise higher per unit). Pay-per-use is cheap at small scale but **per-request read pricing can become unpredictable and expensive at sustained high QPS** — which is exactly the gap Dedicated Read Nodes (per-node hourly) address. ([understanding cost](https://docs.pinecone.io/guides/manage-cost/understanding-cost), [Pinecone DRN](https://www.infoq.com/news/2025/12/pinecone-drn-vector-workloads/))

## Hardware / deployment
- **Resource profile:** abstracted away — you don't size memory/CPU. Internally it is object-storage-bound with SSD slab caching; recently-queried slabs cache on executor local SSD, cold queries pay an object-store fetch.
- **Storage assumptions:** built on cloud object storage (S3/GCS/Azure Blob) with local-SSD caching tiers — designed around network-attached, cheap, near-infinite capacity rather than local NVMe.
- **Footprint:** serverless multi-tenant; **no embedded or self-managed open-source mode**. Dedicated Read Nodes and BYOC provide more isolated/provisioned variants.
- **Deployment:** SaaS on AWS, GCP, and Azure regions; BYOC runs Pinecone's data plane inside your own cloud VPC. No Kubernetes/StatefulSet for you to operate.

## Bottom line
Reach for Pinecone when you want production vector search at scale with **zero operational burden** and are happy to pay per operation and live entirely on a managed, closed-source service — RAG and agent retrieval are the sweet spot. Avoid it if you need self-hosting/on-prem, a system of record with real transactions, exact search, or tight cost control at very high sustained QPS (where per-request read pricing bites — mitigate with Dedicated Read Nodes). The single biggest gotcha: it is **eventually consistent with no Jepsen validation and no multi-record transactions** — the LSN/read-your-writes guarantee is per-namespace and vendor-asserted, so do not treat it as a strongly-consistent system of record.

## Sources
- [Pinecone serverless architecture (docs)](https://docs.pinecone.io/reference/architecture/serverless-architecture)
- [How Pinecone works — engineering deep dive](https://www.pinecone.io/how-pinecone-works/)
- [Inside Pinecone: slab architecture](https://www.pinecone.io/learn/slab-architecture/)
- [Understanding data freshness (LSN model)](https://docs.pinecone.io/guides/data/data-freshness/understanding-data-freshness)
- [Pinecone limits](https://docs.pinecone.io/docs/limits)
- [Pinecone pricing](https://www.pinecone.io/pricing/) and [understanding cost](https://docs.pinecone.io/guides/manage-cost/understanding-cost)
- [Pinecone Dedicated Read Nodes (InfoQ, Dec 2025)](https://www.infoq.com/news/2025/12/pinecone-drn-vector-workloads/)
- [Introducing Pinecone Serverless (blog)](https://www.pinecone.io/blog/serverless/)
- [Pods vs serverless migration](https://www.pinecone.io/lp/pods-vs-serverless/)
