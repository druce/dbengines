---
name: Tantivy
slug: tantivy
adjacent: true
rank: n/a
category: full-text
data_model: Search engine (embedded library)
license: MIT
summary: Embedded full-text search engine library in Rust — "Lucene for Rust": segment-based inverted index with BM25, no server, compiled into your app; the engine under Quickwit and ParadeDB.
last_researched: 2026-06-04
confidence: medium
---

# Tantivy

> A **full-text search engine library** (not a server) written in Rust and inspired by Apache Lucene — the same proven design (immutable **segments**, **inverted index**, **BM25** scoring, columnar fast-fields) compiled directly into your application. It is to [elasticsearch](elasticsearch.md)/Lucene what [sqlite](sqlite.md) is to a database server: you embed it instead of operating a search cluster. It is the engine **Quickwit** and **ParadeDB** are built on.

## When to use

**Use Tantivy if:**
- ✅ You want **Lucene-class full-text search embedded in-process** (Rust natively; Python/Go/Java via bindings) with **no separate search server** — fast startup (<10 ms) and ~2× Lucene throughput in the project's benchmarks.
- ✅ You are **building a search product or feature on top of a library** (as Quickwit does for distributed log search, and ParadeDB's `pg_search` does inside Postgres) rather than operating [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md).
- ✅ You want **predictable, dependency-free, in-process** BM25 search/faceting over local disk (or object storage with your own caching), with full control of the index lifecycle.

**Avoid Tantivy if:**
- ❌ You want a **turnkey distributed search *server*** with clustering, replication, REST, and a UI out of the box — that is [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md), [apache-solr](apache-solr.md), or **Quickwit** (which wraps Tantivy); Tantivy itself is a building block, and **you build the service** around it. This is the biggest gotcha.
- ❌ You need a **system of record** — it is a derived **secondary index** over a durable primary store, like all search engines (see [full-text-search](../concepts/full-text-search.md)).
- ❌ You need the **vast analyzer/plugin/integration/managed-hosting ecosystem** of Lucene/Elasticsearch — Tantivy is leaner and younger, and much of the surrounding tooling you assemble yourself.

## Identity
- **Taxonomy / data model:** [full-text-search](../concepts/full-text-search.md) engine **library**; an **inverted index** (term → postings) over documents with a declared field schema. Embedded, not a document/relational store.
- **Storage model:** **Lucene-style immutable segments** — documents are indexed into segments, each an inverted index; background **merges** consolidate segments. Columnar **fast fields** back sorting/faceting/aggregations; memory-mapped on-disk access with SIMD. Append + merge over immutable segments is [LSM](../concepts/lsm-vs-btree.md)-adjacent. See [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** search/retrieval (BM25 ranking, phrase/boolean/range/fuzzy queries) plus faceting and aggregations; not OLTP, not a transactional store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** N/A — single-process embedded library. Any distribution/replication is the **host application's** responsibility (e.g. Quickwit adds the distributed, object-storage-native layer). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — single-node library.
- **Default isolation & what's achievable:** no SQL transactions. The atomic unit is an **index commit**: a writer stages documents and `commit()`s a new segment generation atomically; readers open a point-in-time snapshot (reload to see new commits). **Single `IndexWriter` (one writer) with many concurrent readers**, à la Lucene. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** N/A in the library — delegated to the host/Quickwit. See [replication-models](../concepts/replication-models.md).
- **Clock dependency:** none. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** You declare a **schema** up front: fields typed as text, `u64`/`i64`/`f64`, `date`, `bytes`, `facet`, IP, or **JSON**, each marked **stored / indexed / fast** as needed. Tokenizers/analyzers configure full-text behavior.
- **Migration / evolution:** changing field types/options generally means **reindexing** into a new index (Lucene-like rigidity); adding documents is online.
- **Type system:** text (analyzed), numerics, dates, booleans, bytes, IP, hierarchical **facets**, and dynamic **JSON** fields; positions/offsets for phrase and highlight support.

## Query interface
- **Language:** **Rust API** — programmatic query construction (`TermQuery`, `BooleanQuery`, `PhraseQuery`, `RangeQuery`, `FuzzyTermQuery`, etc.) plus a **query-parser** grammar for user query strings. **BM25** scoring by default. No SQL. Bindings exist for **Python** (`tantivy-py`), **Go**, **Java**, and others.
- **Transactions:** none beyond atomic index commit (single append/delete/update batch made durable on `commit()`).
- **Native vs app-side:** native **full-text ranking, boolean/phrase/range/fuzzy queries, faceting, aggregations, highlighting, and collectors**; **no joins** and no SQL query layer — you compose queries in code.
- **Stored procedures / UDFs:** none server-side; custom tokenizers/collectors are Rust code in the host process.

## Scaling & topology
- **Vertical, single-node library.** Multi-threaded indexing and search within one process; bounded by host CPU/memory/disk.
- **Sharding / partitioning:** none in the library; you partition by creating multiple indices, or adopt **Quickwit** for distributed, object-storage-native scale-out.
- **Read replicas / read consistency:** "replicas" are just additional processes opening the same index files; each reads the commit generation it loaded.
- **Storage/compute separation:** not in the core (local mmap), but the immutable-segment design enables object-storage-native serving — the basis for **Quickwit** searching indexes on S3 with NVMe warm caching. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** documents buffer in an `IndexWriter`; `commit()` flushes segments and atomically advances the index generation. Durability is the filesystem's once the commit lands; there is no separate WAL daemon. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** a headline strength — **sub-10 ms startup** and roughly **2× Lucene** in the project's benchmarks; memory-mapped, SIMD-accelerated, low-overhead. Tail latency is dominated by segment-merge activity and (for object-storage deployments) cache-miss fetches.
- **Compaction / GC:** background **segment merging** bounds segment count and materializes deletes; merge cadence trades write amplification against query latency.

## Operations & maturity
- **Backup/restore:** copy the index directory (self-contained); no native PITR — the host/Quickwit provides any higher-level snapshotting.
- **Observability:** library-level (logging, query/explain in code). No server-grade metrics suite — that's the host's job.
- **Upgrade story:** crate/bindings version bumps; index-format compatibility is managed across Tantivy versions (reindex on incompatible format changes).
- **Maturity:** **mature and widely embedded.** Created by Paul Masurel; it powers **Quickwit** (distributed log/observability search — Quickwit was acquired by Datadog, 2024–25) and **ParadeDB** (`pg_search`, Tantivy embedded in Postgres), among others (e.g. MyScaleDB). No Jepsen report applies (it is a single-node library; safety questions belong to whatever distributes it).

## Ecosystem & people
- **Canonical use cases:** embedding search in a Rust/Python/Go app; **building a search engine/product on a library** (Quickwit for logs at scale, ParadeDB for Postgres-native BM25); local/edge search; in-process retrieval for RAG pipelines. **Anti-patterns:** wanting a managed/clustered search *server* without building it; using it as a system of record; expecting the full Elasticsearch plugin ecosystem.
- **Drivers / connectors:** Rust crate (`tantivy`) plus **`tantivy-py`** (Python), Go and Java bindings; used as the core of Quickwit and ParadeDB. Maintained under the **quickwit-oss** org.
- **Community size, support, docs:** active OSS community, good docs and examples, no vendor SaaS for the library itself (commercial offerings are the products built on it).

## Licensing & cost
- **OSS license:** **MIT** ([LICENSE](https://github.com/quickwit-oss/tantivy/blob/main/LICENSE)) — permissive, no copyleft, no source-available relicensing. See [license-taxonomy](../concepts/license-taxonomy.md). Minimal lock-in: it's a library with an open on-disk index format.
- **Self-managed vs managed:** library only — you embed it; there is no managed Tantivy service (managed offerings are Quickwit/ParadeDB-derived).
- **Cost model:** free library; cost is the host hardware you run it on.

## Hardware / deployment
- **Resource profile:** **disk-first**, memory-mapped with SIMD; benefits from RAM for OS page cache but does not require the index to fit in RAM. CPU-bound on analysis/scoring, I/O-bound on merges.
- **Storage assumptions:** local NVMe/SSD ideal; object storage workable with a caching layer (the Quickwit pattern).
- **Footprint:** **embedded library** (in-process, no daemon) — see [embedded-databases](../concepts/embedded-databases.md); compiles into any Rust binary, or is loaded via bindings.
- **Deployment:** wherever your app runs — server, CLI, container, edge; distribution/HA only via the system you build around it (or Quickwit).

## Bottom line
Reach for Tantivy when you want **Lucene-class full-text search embedded in your application** with no search server to operate — fast, lean, MIT-licensed, and the proven foundation under Quickwit and ParadeDB. It is the **"SQLite/Lucene-for-Rust"** of search: a library you build on, the in-process counterpoint to a [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md) cluster. Don't reach for it expecting a turnkey distributed search server, a system of record, or the full Elasticsearch ecosystem. The single biggest gotcha: **it is a library, not a service** — clustering, replication, REST, and ops are yours to build (or adopt Quickwit, which already did).

## Sources
- [Tantivy GitHub (quickwit-oss; "full-text search engine library inspired by Apache Lucene, written in Rust")](https://github.com/quickwit-oss/tantivy) · [LICENSE (MIT)](https://github.com/quickwit-oss/tantivy/blob/main/LICENSE)
- [ParadeDB — Introduction to Tantivy (segments, inverted index, BM25; embedded in Postgres via pg_search)](https://www.paradedb.com/learn/tantivy/introduction)
- [Spice.ai — What is Tantivy? (Lucene-class, library not server, <10ms startup, ~2× Lucene)](https://spice.ai/learn/tantivy)
- [dbdb.io — Tantivy](https://dbdb.io/db/tantivy)
- [Quickwit (distributed search built on Tantivy)](https://quickwit.io/)
