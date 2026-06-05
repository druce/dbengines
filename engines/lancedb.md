---
name: LanceDB
slug: lancedb
adjacent: true
rank: n/a
category: vector
data_model: Vector
license: Apache 2.0 (permissive; OSS Lance + LanceDB) + LanceDB Cloud/Enterprise (managed, proprietary)
summary: Embedded "SQLite/DuckDB for vectors and multimodal AI" — an Apache-2.0 in-process retrieval library on the columnar Lance format that runs zero-daemon over local disk or object storage, with a managed Enterprise tier for low-latency scale.
last_researched: 2026-06-04
confidence: medium
---

# LanceDB

> An Apache-2.0 embedded vector/multimodal database — the "**SQLite for vector + AI data**" — that runs in-process (Python/Rust/JS, no server daemon in OSS) and keeps **vectors, metadata, and raw multimodal blobs together** in one versioned columnar **Lance** table. It is **local-disk-first and fast there** (sub-10ms p95 on NVMe); it can *also* point the same table at S3/GCS/Azure object storage, where cold reads are the latency caveat — and a managed Enterprise tier adds NVMe-cached distributed serving for high-QPS.

## When to use

**Use LanceDB if:**
- ✅ You want an **embedded, zero-ops** vector store that ships inside your app/Lambda/notebook (the [embedded](../concepts/embedded-databases.md) "SQLite/DuckDB for AI data" niche) rather than running a server like [milvus](milvus.md)/[qdrant](qdrant.md)/[weaviate](weaviate.md) or paying for managed-only [pinecone](pinecone.md).
- ✅ Your data is **multimodal** (images, video, audio, text, embeddings side-by-side) and you want columnar storage with **built-in versioning / time-travel** and zero-copy column addition — the Lance format's core differentiator versus a metadata-DB-plus-blob-store split.
- ✅ You want a **single object-storage-native artifact** (a Lance table on S3/GCS/Azure) queryable by many readers, with no separate index service, and interop with Arrow/DuckDB/Polars/pandas/PyTorch.

**Avoid LanceDB if:**
- ❌ You're serving **high QPS at low single-digit-ms latency, especially from cold object storage**: a single OSS process tops out around 10–50 QPS, and cold S3/GCS/Azure reads pay hundreds of ms per query (local NVMe is sub-10ms, but one process still won't do high concurrency). That *serving* profile requires the **paid Enterprise** NVMe-cached distributed tier ([Enterprise vs OSS](https://docs.lancedb.com/enterprise)). This is the biggest gotcha — and it's a cloud-serving / concurrency limit, not a knock on the local embedded path.
- ❌ You need a **system of record with multi-statement ACID transactions, joins, or SQL OLTP** — LanceDB is a retrieval/search store, not a transactional or relational database.
- ❌ You need a **always-on multi-writer server** with managed failover out of the box in OSS — OSS is a library with no daemon; concurrency rests on object-store atomic commits, and high-concurrency write/delete on S3 has known sharp edges ([issue #3086](https://github.com/lancedb/lancedb/issues/3086)).

## Identity
- **Taxonomy / data model:** [Vector](../concepts/vector-search-ann.md) + multimodal retrieval store. A table is a set of rows with one or more vector columns plus arbitrary scalar/blob columns (text, images, video, audio); it also does [full-text search](../concepts/full-text-search.md) and SQL-style filtering ([GitHub](https://github.com/lancedb/lancedb)). Not a general-purpose relational/document store.
- **Storage model:** **Columnar**, built on the open-source **Lance** format ([columnar-storage](../concepts/columnar-storage.md)), itself Arrow-native. Lance writes **immutable fragments** + a versioned **manifest**; it is positioned as a "lakehouse format for multimodal AI" rather than a Parquet replacement, optimized for **fast random/point access** (vendor benchmarks claim ~2000x faster point access than Parquet via adaptive structural encodings — vendor/first-party numbers, [Lance arxiv paper](https://arxiv.org/html/2504.15247v1), [blog](https://blog.lancedb.com/benchmarking-random-access-in-lance/)). Not a B-tree or [LSM](../concepts/lsm-vs-btree.md) engine; append + compaction over immutable fragments is LSM-adjacent. Disk-first with memory-mapped/SIMD access rather than a RAM-resident index.
- **Workload:** Retrieval serving (ANN + filter + full-text) and ML feature/data access, not OLTP. Leans analytical/[OLAP-ish](../concepts/oltp-olap-htap.md) for scan/feature workloads; **not HTAP** — no transactional path. The Lance format also doubles as a training-data/feature-store format (random access for shuffling/feature hydration).

## Distribution & consistency
- **CAP under partition:** N/A — single-process / embedded; OSS has no distributed cluster. The relevant durability/consistency story is the **object store's**, not a quorum protocol. See [cap-pacelc](../concepts/cap-pacelc.md). (Enterprise is a distributed serving layer over the same shared storage; its CAP classification is ⚠️ unverified — not published.)
- **PACELC:** N/A — single-node OSS. ⚠️ unverified — no published PACELC for Enterprise.
- **Default isolation & what's achievable:** The Lance **table format** provides **MVCC with optimistic concurrency control**; each commit is an atomic, immutable new table version forming a **serializable history**, with automatic conflict detection and **rebase** of compatible concurrent transactions (e.g. deletes on disjoint rows), retry for others, and hard failure for incompatible ones ([Lance transactions](https://lance.org/format/table/transaction/)). This is table-level snapshot/serializable versioning à la [Iceberg](apache-iceberg.md)/[Delta Lake](delta-lake.md) — **not** SQL row-level isolation or multi-statement application transactions. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** N/A in OSS — durability and replication are delegated to the underlying **object store / filesystem** (S3, GCS, Azure Blob, EFS, NVMe). No engine-level leader/quorum replication. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency knob like [milvus](milvus.md)/[qdrant](qdrant.md). Readers open a specific table **version** (latest or pinned for time-travel); writers commit new versions optimistically.
- **Clock dependency:** No documented dependency on synchronized clocks (no TrueTime/HLC). Commit ordering comes from monotonic manifest versions + object-store atomic primitives, not wall-clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, flexible.** Tables have an Arrow schema (typed columns), but Lance's **zero-copy data evolution** lets you add derived columns (new embeddings/features) later **without rewriting existing data** — only new column files are written ([Lance format](https://docs.lancedb.com/lance)).
- **Migration / evolution:** Online add-column and merge/update are first-class via Lance transaction types (Append, Update, Merge, Project, CreateIndex, Rewrite/compaction, etc.) ([transactions](https://lance.org/format/table/transaction/)). No locking `ALTER`; changes commit as new versions. Changing a vector column's dimensionality still means re-embedding into a new column/table.
- **Type system:** Arrow types — dense **vectors**, scalars (int/float/bool/string), nested/struct, and **binary blobs** for images/video/audio (multimodal is a headline use case). Geospatial/interval types are not a focus.

## Query interface
- **Language:** **API/SDK-first** — Python (primary), **Rust**, TypeScript/JavaScript, plus a REST path; the underlying **Lance** format is also readable from DuckDB, Polars, pandas, PyArrow, PyTorch ([GitHub](https://github.com/lancedb/lancedb)). Supports SQL-style filter expressions and full-text search alongside vector search, but it is not a full SQL database engine.
- **Transactions:** No multi-statement application ACID. The atomic unit is a **single committed table version** (one append/update/delete/merge), made durable and conflict-checked by the Lance commit protocol.
- **Native vs app-side:** Native **vector ANN**, **full-text/BM25 search**, **hybrid search**, and **metadata filtering** combinable in one query; reranking supported. **No joins, no aggregations/window functions** as a query engine — push analytics to DuckDB/Spark/Polars reading the Lance files directly.
- **Stored procedures / UDFs:** None server-side. Embedding functions / logic run in the host app process.

## Scaling & topology
- **Vertical vs horizontal:** OSS scales **vertically** — bounded by the single host's CPU/memory/disk; a single process serves ~10–50 QPS ([Enterprise vs OSS](https://docs.lancedb.com/enterprise)). Horizontal read scale-out is an **Enterprise** feature (a distributed serving layer over shared object storage). Multiple OSS readers can independently open the same table on object storage (shared-storage read fan-out), but there is no OSS query router/load balancer.
- **Sharding / partitioning:** No automatic resharding system in OSS; data layout is fragments within a table. ⚠️ unverified — manual partitioning patterns (e.g. table-per-tenant) are user-driven.
- **Read replicas / read consistency:** "Replicas" are just multiple processes reading the same shared storage; each reads a chosen table version, so reads are as consistent as the version they open. No staleness knob.
- **Storage/compute separation:** **Yes, foundational** — compute is stateless and operates over immutable fragments on object storage; this is the design point that lets Enterprise add a cache/serving fleet without moving the data ([storage-compute-separation](../concepts/storage-compute-separation.md), [storage architecture](https://docs.lancedb.com/storage)).

## Performance & durability
- **Write path:** A write stages new immutable data files, then **atomically commits a new manifest** via object-store conditional primitives (**put-if-absent / rename-if-absent**); exactly one writer wins a version, others rebase/retry ([transactions](https://lance.org/format/table/transaction/)). There is **no separate WAL daemon** — durability is the object store's once the commit lands; the data-loss window is whatever the underlying store guarantees on its acked PUT. See [wal-and-durability](../concepts/wal-and-durability.md). On stores lacking native atomic put-if-absent, Lance can use an **external manifest store** (KV with put-if-not-exists) as a commit coordinator; modern **S3/S3 Express** support atomic conditional writes natively, so concurrent single-table writers work out of the box ([issue #2002](https://github.com/lancedb/lancedb/issues/2002)).
- **Throughput/latency:** Strongly storage-tier-dependent. Per LanceDB's own docs: **local NVMe < 10ms p95**, block storage < 30ms, file storage ~100ms, **object storage hundreds of ms** especially cold ([storage architecture](https://docs.lancedb.com/storage)). OSS latency from cold S3 is the headline weakness; Enterprise targets 50–200ms with NVMe caching ([Enterprise](https://docs.lancedb.com/enterprise)). Tail (p99) is dominated by cache-miss object-store round trips.
- **Vector indexes:** **IVF_PQ** (IVF partitioning + product quantization, the common default), **IVF_SQ** (scalar quantization, ~4x compression), and **HNSW-backed hybrid** indexes **IVF_HNSW_PQ / IVF_HNSW_SQ / IVF_HNSW_FLAT**; docs suggest IVF_PQ/IVF_RQ for filtered workloads where HNSW variants show higher latency variance ([vector index docs](https://docs.lancedb.com/indexing/vector-index)). Indexes are built per data and committed as versions.
- **Compaction / GC:** Immutable fragments + soft-deletes (deletion vectors) accumulate; periodic **compaction (Rewrite)** merges fragments and materializes deletes, and old versions must be pruned to reclaim space. In OSS this is **manual/scheduled** (a day-2 chore); Enterprise manages it ([Enterprise](https://docs.lancedb.com/enterprise)).

## Operations & maturity
- **Backup/restore, PITR:** Backup = copy the Lance table directory (self-contained, portable — copying the dataset preserves all versions). **Built-in versioning gives table-level time-travel** to any retained version, which doubles as logical PITR; physical recovery relies on the object store's own durability/replication.
- **Observability:** Library-level (logs, query/explain on the scan plan via the Lance/DataFusion path). ⚠️ unverified — no SQL-grade slow-query log or metrics suite in OSS; Enterprise adds 24×7 monitoring.
- **Upgrade story:** OSS upgrades are pip/cargo/npm version bumps; Lance keeps **stable vs legacy data-format versions** for forward/backward compatibility ([storage architecture](https://docs.lancedb.com/storage)). Enterprise/Cloud upgrades are vendor-managed.
- **Maturity:** Young but fast-growing; the **Lance** format and **LanceDB** library are widely adopted in the AI/ML stack and the format is increasingly used as a standalone multimodal/training-data format. **No Jepsen report exists** — distributed-safety claims rest on object-store guarantees + the documented OCC protocol, not third-party formal verification. Known sharp edges: cold object-store latency, manual compaction in OSS, and **high-concurrency multi-writer delete/write on S3** ([issue #3086](https://github.com/lancedb/lancedb/issues/3086), [issue #1077](https://github.com/lancedb/lancedb/issues/1077)).

## Ecosystem & people
- **Canonical use cases:** Embedded RAG / semantic search inside an app or serverless function; **multimodal AI data lake** (store images/video/audio + embeddings + metadata in one versioned table on S3); ML **feature store / training-data format** needing fast random access; agent memory. **Anti-patterns:** system of record / OLTP; relational analytics needing joins; ultra-low-latency high-QPS serving directly off cold object storage in OSS (use Enterprise or a RAM-resident engine); workloads needing a managed always-on multi-writer server without operating it yourself.
- **Drivers / connectors:** Python/Rust/TS SDKs; Lance files read natively by **DuckDB, Polars, pandas, PyArrow, PyTorch, Spark**; integrations with **LangChain / LlamaIndex** and embedding providers. Less mature CDC/Kafka/dbt/BI tooling than relational engines — it is an AI-retrieval/format play, not part of the BI stack.
- **Community size, support, docs:** Active OSS community and good, example-driven docs; commercial support via **LanceDB Cloud / Enterprise**. Low learning curve to first vector search; production tuning (index choice, storage tier, compaction cadence, concurrency) is where the depth is.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive) for both the **Lance** format and the **LanceDB** library ([GitHub](https://github.com/lancedb/lancedb)) — no copyleft, no post-2018 SSPL/BSL relicensing. See [license-taxonomy](../concepts/license-taxonomy.md). The open columnar format limits lock-in: tables remain readable by other Arrow tools even off LanceDB.
- **Self-managed vs managed:** Self-host the OSS embedded library (free; you pay only storage/infra), or use **LanceDB Cloud** (managed SaaS, "no servers to manage") / **LanceDB Enterprise** (distributed, **BYOC** in your VPC or vendor-managed SaaS; SOC 2 Type II / HIPAA coverage) ([Enterprise](https://docs.lancedb.com/enterprise)). Lock-in is low at the format level, higher if you depend on Enterprise's cache/serving features.
- **Cost model:** OSS = object-storage + compute you already run (cheap at rest on S3; you pay egress/latency on reads). Cloud/Enterprise = managed pricing for the serving fleet + NVMe cache. ⚠️ unverified — exact Cloud/Enterprise per-unit pricing not captured here; confirm on the [LanceDB Enterprise page](https://www.lancedb.com/lp/lancedb-enterprise).

## Hardware / deployment
- **Resource profile:** **Disk-first, not RAM-resident** — vectors/data live on disk/object storage and are memory-mapped with SIMD access, so it does **not** require the working set to fit in RAM (a deliberate contrast with HNSW-in-RAM engines like [qdrant](qdrant.md)/[weaviate](weaviate.md)). Performance is dominated by **storage-tier latency** (NVMe vs S3) more than by RAM size.
- **Storage assumptions:** Pluggable across **local NVMe/SSD, block (EBS), file (EFS), third-party (MinIO/WekaFS), and object storage (S3/GCS/Azure, incl. S3 Express One Zone)** — explicitly object-storage-native, tolerating high latency by design ([storage architecture](https://docs.lancedb.com/storage)).
- **Footprint:** **Embedded library** (in-process, no daemon) in OSS — see [embedded-databases](../concepts/embedded-databases.md); scales out to a **distributed serving cluster** only in Enterprise. Ships inside binaries, containers, notebooks, or serverless functions.
- **Deployment:** Self-hosted embedded anywhere; serverless-friendly (e.g. Lambda querying Lance tables on S3); managed SaaS or BYOC-in-VPC via Cloud/Enterprise. Container/k8s-friendly but does not need a StatefulSet in OSS since state lives in shared storage.

## Bottom line
Reach for LanceDB when you want an **embedded, Apache-2.0 vector + multimodal store** that needs no server, keeps embeddings and raw media together in one **versioned columnar (Lance) table** on local disk or S3, and slots into the Arrow/DuckDB/PyTorch ecosystem — it is the "SQLite/DuckDB for AI data," the local/object-storage-native counterpoint to server engines ([milvus](milvus.md)/[qdrant](qdrant.md)/[weaviate](weaviate.md)) and to managed-only [pinecone](pinecone.md), and it leans harder than [chroma](chroma.md) on its open columnar format and disk-first design. Don't use it as a system of record, for SQL/relational analytics, or where you need multi-statement ACID transactions. The single biggest gotcha applies only to the **object-storage / high-QPS serving** path: a single OSS process serves only tens of QPS and cold S3/GCS/Azure reads cost hundreds of ms (**local NVMe is sub-10ms** — the embedded local path is fast), so low-latency high-throughput *serving* requires the **paid Enterprise** NVMe-cached distributed tier. There is also **no Jepsen report**, so the consistency story is "trust the object store plus a documented optimistic-concurrency commit protocol," not independently verified.

## Sources
- [LanceDB GitHub (OSS, Apache 2.0, SDKs)](https://github.com/lancedb/lancedb)
- [Lance format overview (zero-copy evolution, versioning, multimodal)](https://docs.lancedb.com/lance)
- [Lance table transactions / MVCC + optimistic concurrency](https://lance.org/format/table/transaction/)
- [LanceDB storage architecture (storage tiers, latency, immutable fragments)](https://docs.lancedb.com/storage)
- [LanceDB Enterprise vs OSS (QPS/latency limits, NVMe cache, BYOC/SaaS)](https://docs.lancedb.com/enterprise)
- [LanceDB Enterprise landing page](https://www.lancedb.com/lp/lancedb-enterprise)
- [Vector index types (IVF_PQ, IVF_SQ, IVF_HNSW_*)](https://docs.lancedb.com/indexing/vector-index)
- [Concurrent writes on S3 (issue #2002)](https://github.com/lancedb/lancedb/issues/2002) · [multi-writer delete/storage sharp edges (issue #3086)](https://github.com/lancedb/lancedb/issues/3086)
- [Lance: random access via adaptive structural encodings (arxiv)](https://arxiv.org/html/2504.15247v1) · [random-access benchmark blog](https://blog.lancedb.com/benchmarking-random-access-in-lance/)
- AWS Architecture Blog: [1B+ vector search on LanceDB + S3](https://aws.amazon.com/blogs/architecture/a-scalable-elastic-database-and-search-solution-for-1b-vectors-built-on-lancedb-and-amazon-s3/)
