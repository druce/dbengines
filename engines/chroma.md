---
name: Chroma
slug: chroma
rank: 92
data_model: Vector
license: Apache 2.0 (permissive)
summary: Developer-first embedding/search database that runs embedded for prototyping and scales to a serverless object-storage-backed cloud, with a Rust core since 1.0.
last_researched: 2026-06-04
confidence: medium
---

# Chroma

> An Apache-2.0 vector/search database built for AI app developers — trivially embeddable for local RAG prototyping, with an object-storage-backed serverless cloud for scale; not a general-purpose database and weak on hard distributed-consistency guarantees.

## When to use

**Use Chroma if:**
- ✅ You're building AI retrieval (RAG, semantic/hybrid search, agent or chatbot memory)
- ✅ You want the shortest path from a laptop prototype to production — `pip install chromadb`, then the same API scales onto an object-storage-backed serverless cloud
- ✅ You want Apache-2.0 licensing with low core-API lock-in
- ✅ You want combinable native dense-vector ANN, sparse/full-text, regex, and metadata filtering in one query

**Avoid Chroma if:**
- ❌ You need a primary system of record, or OLTP/relational/analytics workloads (no joins, aggregations, or window functions)
- ❌ You need audited serializable isolation or a Jepsen-validated consistency guarantee — its "strongly consistent reads" claim is unverified design intent (the biggest gotcha)
- ❌ Your self-hosted single-node deployment would exceed ~10M records (the documented ceiling)
- ❌ You need fine-grained, self-managed horizontal sharding control on-prem

## Identity
- **Taxonomy / data model:** [vector](../concepts/vector-search-ann.md) database (the dominant model) that Chroma now positions as "search infrastructure for AI," unifying dense-vector ANN, sparse-vector/[full-text](../concepts/full-text-search.md), regex, and metadata filtering in one query API ([Chroma docs](https://docs.trychroma.com/), [GitHub](https://github.com/chroma-core/chroma)). Records are items with an ID, embedding, optional document text, and metadata, grouped into **collections** → **databases** → **tenants**.
- **Storage model:** local/single-node mode stores metadata in **SQLite** and vectors in a custom binary format on disk; the whole DB is a single portable directory ([architecture](https://docs.trychroma.com/docs/overview/architecture)). Vector index is **HNSW** ([graph-based ANN](../concepts/lsm-vs-btree.md), not B-tree/LSM); the distributed system adds **SPANN** (head ANN + posting lists) and immutable **Arrow-backed blockfile segments** with copy-on-write ([Chroma Cookbook concepts](https://cookbook.chromadb.dev/core/concepts/)).
- **Workload:** retrieval/search serving for AI applications (RAG, semantic search, agent memory), not OLTP or OLAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Read-heavy nearest-neighbor + filter queries; not a system of record.

## Distribution & consistency
- **Single-node / embedded:** N/A — single-node. Embedded and single-server modes are not partition-tolerant; durability rests on local disk + SQLite/WAL.
- **Distributed (Chroma Cloud / OSS distributed):** writes go to a durable append-only **write-ahead log** (`wal3`) before ack; a separate **compaction** service asynchronously materializes WAL history into read-optimized segments on object storage — "durable first, indexed asynchronously" ([Cookbook concepts](https://cookbook.chromadb.dev/core/concepts/)). See [wal-and-durability](../concepts/wal-and-durability.md), [storage-compute-separation](../concepts/storage-compute-separation.md).
- **CAP under partition:** ⚠️ unverified — Chroma publishes no formal CAP/PACELC classification. The architecture (durable WAL + async indexing on shared object storage) is consistent with a CP-leaning, storage-compute-separated design rather than a Dynamo-style AP quorum. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Consistency:** by default reads are "strongly consistent" — the default `ReadLevel: IndexAndWal` combines indexed segment state with recent un-compacted WAL data, so reads see prior writes ([Cookbook concepts](https://cookbook.chromadb.dev/core/concepts/), [ReadLevel changelog](https://www.trychroma.com/changelog/readlevel)). ⚠️ unverified — there is no Jepsen report or formal verification; treat the strong-consistency claim as a design intent under normal operation, not an independently validated guarantee under faults.
- **Isolation:** ⚠️ unverified — Chroma does not document SQL-style [isolation levels](../concepts/isolation-levels.md); it is not a transactional database and there is no multi-statement ACID. Operations are per-collection writes, not serializable transactions.
- **Replication:** in the cloud/distributed design, durability and availability come from replicated **object storage** + the WAL rather than classic single-/multi-leader replicas. See [replication-models](../concepts/replication-models.md). ⚠️ unverified — failover/split-brain behavior is not publicly documented in detail.
- **Tunable consistency?** Yes — a per-query **`ReadLevel`** parameter: `IndexAndWal` (default; reads index + recent un-compacted WAL for strongly consistent, slightly slower reads) or `IndexOnly` (reads only indexed segments for faster, lower-latency but staler reads) ([ReadLevel changelog](https://www.trychroma.com/changelog/readlevel)).
- **Clock dependency:** ⚠️ unverified — no documented dependency on synchronized clocks (no TrueTime/HLC claims). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** schema-on-read / flexible. Collections do not enforce a rigid schema; each item carries arbitrary JSON-like metadata. Embedding dimensionality is fixed per collection by the embedding function used.
- **Migration / evolution:** no `ALTER TABLE` concept; you add/update/upsert items. Changing embedding model or dimensionality generally means a new collection and re-indexing rather than an in-place migration.
- **Type system:** documents (text), float embedding vectors, and metadata scalars (string/int/float/bool) used for filtering. Native full-text and regex matching over documents; no rich geospatial/interval types.

## Query interface
- **Language:** **API-only** (no SQL). Python and JS/TS are first-class; Rust core since 1.0 added native bindings for JS, Ruby, Swift and WASM browser builds ([Chroma 1.0 announcement](https://www.trychroma.com/project/1.0.0)). Core ops: `add`/`upsert`/`get`/`query`/`delete` with `where` (metadata) and `where_document` (full-text/regex) filters.
- **Transactions:** none in the ACID sense — no multi-statement transactions; writes are per-collection upserts. Atomicity is at the operation level.
- **Native vs app-side:** nearest-neighbor search, metadata filtering, full-text, and regex are native and combinable in one query (hybrid retrieval). No joins, no aggregations, no window functions — relational analytics belong elsewhere.
- **Stored procedures / UDFs:** none. Embedding functions run client-side or via configured embedding providers, not as in-DB procedures.

## Scaling & topology
- **Single-node ceiling:** official docs put single-node deployment at **"typically fewer than 10 million records across a handful of collections,"** beyond which you should move to distributed/cloud ([architecture](https://docs.trychroma.com/docs/overview/architecture)). That figure is a docs guideline and is workload-dependent.
- **Horizontal scale:** achieved via Chroma Cloud's distributed system on object storage, not via manual sharding of the OSS single-node server. The serverless design tiers data across hot memory cache → warm SSD → cold object storage ([serverless engineering post](https://www.trychroma.com/engineering/serverless)).
- **Sharding / partitioning:** handled by the cloud service; not a user-managed resharding exercise in the managed product. ⚠️ unverified — OSS self-hosted distributed mode operability is less documented.
- **Read replicas / read consistency:** compute reads from shared object storage rather than from per-node replicas; by default reads include recent WAL data (`ReadLevel: IndexAndWal`), tunable per query to `IndexOnly` (see Tunable consistency).
- **Storage/compute separation:** yes — a core design point of the cloud product ([serverless post](https://www.trychroma.com/engineering/serverless)). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** distributed mode appends to a durable WAL before ack, then compacts asynchronously into segments ([Cookbook concepts](https://cookbook.chromadb.dev/core/concepts/)). See [wal-and-durability](../concepts/wal-and-durability.md). Local/embedded durability relies on disk + SQLite; the crash data-loss window depends on fsync timing. ⚠️ unverified — exact fsync/group-commit policy for embedded mode is not clearly documented.
- **Throughput / latency:** Chroma 1.0's Rust rewrite reports **~3–5x faster writes and queries (≈4x overall)** for local workflows vs the prior Python implementation, and removes the Python GIL bottleneck for true multithreading ([Chroma 1.0](https://www.trychroma.com/project/1.0.0)). These are first-party benchmarks — treat as vendor numbers, not independent. p99 tail behavior is not published.
- **Compaction / GC:** background compaction turns WAL into immutable Arrow blockfile segments; a dedicated **garbage collector** prunes obsolete index artifacts and WAL entries using version graphs/retention so it doesn't break active readers ([Cookbook concepts](https://cookbook.chromadb.dev/core/concepts/)). HNSW index rebuild/compaction cost is the main p99 risk on heavy ingest. ⚠️ unverified — no published p99-under-compaction data.

## Operations & maturity
- **Backup/restore:** local mode — copy the persistence directory (single-folder portability is a selling point). Cloud — managed by the provider. ⚠️ unverified — no documented PITR for self-hosted.
- **Observability:** basic; collection counts, server logs. No EXPLAIN/query-plan tooling comparable to a SQL engine. ⚠️ unverified — depth of metrics/slow-query logging.
- **Upgrade story:** local library upgrades are pip/npm version bumps; the 1.0 release is advertised as **fully API-compatible** with prior versions ([Chroma 1.0](https://www.trychroma.com/project/1.0.0)). Cloud upgrades are managed.
- **Maturity:** young but very popular OSS project (one of the most-starred vector DBs); the distributed/serverless cloud reached general availability relatively recently (2025). **No Jepsen report exists.** Known sharp edges: single-node scaling ceiling, limited transactional/consistency guarantees, evolving distributed mode.

## Ecosystem & people
- **Canonical use cases:** RAG over a document corpus, semantic/hybrid search, agent and chatbot memory, quick local prototyping that graduates to a managed cloud with the same API.
- **Anti-patterns:** as a primary system of record, for OLTP/relational workloads, for analytics/joins/aggregations, or where you need audited serializable transactions or a formally verified consistency model. Also a poor fit if you need fine-grained, self-managed horizontal sharding control on-prem.
- **Drivers / connectors:** Python and JS/TS SDKs (plus Rust/Ruby/Swift bindings); deep integration with **LangChain** and **LlamaIndex**; Docker/Kubernetes deployment for self-hosting. ⚠️ unverified — first-class CDC/Kafka/dbt connectors are not a focus.
- **Community & docs:** large, active developer community; docs are approachable and example-driven; very low learning curve — `pip install chromadb` and a few lines to a working store. Commercial support via Chroma Cloud / the company behind it.

## Licensing & cost
- **OSS license:** **Apache 2.0**, permissive — no post-2018 SSPL/BSL relicensing ([LICENSE](https://github.com/chroma-core/chroma/blob/main/LICENSE)). See [license-taxonomy](../concepts/license-taxonomy.md). The core engine, including the Rust rewrite, is open source.
- **Self-managed vs managed:** both. Self-host the OSS server/embedded library, or use **Chroma Cloud** (serverless managed). Lock-in is low for the core API, but the distributed/serverless scaling story is most turnkey on Chroma Cloud.
- **Cost model:** OSS is free (you pay infra). Chroma Cloud is **usage-based serverless** with a free tier: roughly **$0.02/GB-month storage** on object storage, plus per-GB write and per-query fees — e.g., a ~1M-vector (~6GB) dataset cited at ~$2/month storage plus a one-time ~$15 write fee ([Chroma pricing](https://www.trychroma.com/pricing); third-party analysis: [maxrohde.com](https://maxrohde.com/2025/08/09/pinecone-price-increase-is-chroma-cloud-the-best-alternative/)). Object-storage backing makes cost-at-scale far cheaper than RAM-resident vector services. ⚠️ unverified — exact current per-GB-written and per-query rates change; confirm on the pricing page.

## Hardware / deployment
- **Resource profile:** HNSW indexes are memory-hungry — local/single-node performance is memory-bound and the working set effectively wants to fit in RAM. The cloud design relaxes this by tiering hot/warm/cold across memory → SSD → object storage.
- **Storage assumptions:** local mode uses local disk; distributed mode is built on **cloud object storage** (S3-style), tolerating its higher latency via caching/tiering rather than assuming low-latency NVMe.
- **Footprint:** spans **embedded library → single-node server → distributed/serverless cloud** from one codebase (shared Rust core). See [embedded-databases](../concepts/embedded-databases.md).
- **Deployment:** SaaS (Chroma Cloud) or self-hosted on-prem via Docker/Kubernetes; the embedded mode needs no server at all.

## Bottom line
Reach for Chroma when you're building AI retrieval (RAG, semantic/hybrid search, agent memory) and want the shortest path from a laptop prototype to production: `pip install chromadb`, Apache-2.0, and the same API scales onto an object-storage-backed serverless cloud. Don't reach for it as a primary database, for transactional/relational workloads, or where you need audited serializable isolation or a Jepsen-validated consistency guarantee — none of those exist here. The single biggest gotcha: the self-hosted single-node server tops out around ~10M records and Chroma's "strongly consistent reads" claim is a design assertion with no independent verification, so validate consistency and scale against your own workload before betting on them.

## Sources
- [Chroma documentation](https://docs.trychroma.com/) and [architecture overview](https://docs.trychroma.com/docs/overview/architecture)
- [Chroma Cookbook — core concepts (distributed architecture, WAL, compaction, consistency)](https://cookbook.chromadb.dev/core/concepts/)
- [Chroma 1.0 / Rust rewrite announcement](https://www.trychroma.com/project/1.0.0)
- [Chroma serverless engineering post (object-storage retrieval)](https://www.trychroma.com/engineering/serverless)
- [Chroma pricing](https://www.trychroma.com/pricing)
- [chroma-core/chroma GitHub + LICENSE (Apache 2.0)](https://github.com/chroma-core/chroma/blob/main/LICENSE)
- Third-party cost analysis: [maxrohde.com — Chroma Cloud vs Pinecone](https://maxrohde.com/2025/08/09/pinecone-price-increase-is-chroma-cloud-the-best-alternative/)
