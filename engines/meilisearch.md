---
name: Meilisearch
slug: meilisearch
rank: 148
data_model: Search engine
license: Community Edition MIT (permissive); Enterprise Edition BUSL 1.1 (source-available, sharding/replication) since v1.19 (Aug 2025)
summary: Developer-friendly, Rust + LMDB full-text/hybrid search engine; instant typo-tolerant search; horizontal sharding + replication exist but are gated behind the paid BUSL Enterprise Edition.
last_researched: 2026-06-04
confidence: high
---

# Meilisearch

> A Rust + LMDB search engine optimized for instant typo-tolerant "search-as-you-type" with built-in hybrid (keyword + vector) search — Algolia ergonomics, self-hosted. The free Community Edition is single-node MIT; horizontal sharding and replication exist as of v1.37 (2026) but require the paid BUSL Enterprise Edition, and even then use a simple leader-follower model with no consensus.

## When to use

**Use Meilisearch if:**
- ✅ You want Algolia-style instant, typo-tolerant, search-as-you-type that you can self-host under a permissive MIT license
- ✅ You need built-in hybrid (BM25 keyword + vector) search via a tunable `semanticRatio` for on-site/e-commerce/docs search or RAG
- ✅ Your data fits comfortably on one beefy NVMe node and a real database remains your source of truth
- ✅ You value strong DX and a simple HTTP/JSON REST API with official SDKs

**Avoid Meilisearch if:**
- ❌ Indexing is asynchronous — documents are not searchable the instant you write them (no immediate read-your-writes)
- ❌ You need built-in HA/auto-failover — the free MIT CE has none, and even sharding/replication require the BUSL Enterprise Edition with a leader-follower model, no consensus, and no documented auto-failover
- ❌ You want a primary store/system of record, analytics/aggregation workloads, joins, or SQL — index data that lives authoritatively in e.g. [postgresql](postgresql.md)

## Identity
- **Taxonomy / data model:** dedicated [full-text-search](../concepts/full-text-search.md) engine with documents (JSON objects) grouped into *indexes*; not a general-purpose database. Adds [vector-search-ann](../concepts/vector-search-ann.md) (hybrid keyword + semantic), faceted filtering, geosearch.
- **Storage model:** built on **LMDB** (Lightning Memory-Mapped Database), a memory-mapped, copy-on-write **B+tree** transactional key-value store — *not* an [LSM](../concepts/lsm-vs-btree.md) design. The search-specific structures (inverted indexes, the `milli` crate) sit on top of LMDB. Data is served straight from the memory map with no copy on read ([docs](https://www.meilisearch.com/docs/resources/internals/storage)). The LMDB wrapper is the in-house `heed` Rust crate; recent releases patched LMDB (with LMDB author Howard Chu) for nested read transactions on uncommitted writes, speeding the vector store ~3x ([blog](https://www.meilisearch.com/blog/3xfaster-vector-store)).
- **Workload:** read-optimized search ([OLTP](../concepts/oltp-olap-htap.md)-ish low-latency point queries, sub-50ms target). Not OLAP, not HTAP, not a system of record — it indexes data that lives authoritatively elsewhere.

## Distribution & consistency
- **CAP under partition:** the **Community Edition is single-node** (one process, one LMDB file; no consensus or quorum), so CAP is N/A there. The **Enterprise Edition (v1.37+, BUSL)** adds a multi-node cluster with **sharding + replication**; it uses a designated **leader** for writes (non-leaders reject writes with a `not_leader` error) and so leans CP-ish on the write path, but there is **no consensus protocol (no Raft/Paxos), no automatic leader election, and no documented split-brain handling** — operators manage topology manually ([replication & sharding docs](https://www.meilisearch.com/docs/resources/self_hosting/sharding/overview)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** CE is single-node (N/A). EE clustering uses leader-routed writes and queries each shard exactly once (favoring the local replica); it is not a tunable-consistency quorum system, so the PACELC tradeoff is coarse and largely operator-managed. ⚠️ unverified — Meilisearch does not publish a formal CAP/PACELC classification; the above is inferred from the leader-follower replication docs.
- **High availability / replication:** **no HA in the free CE** — multi-node there means running independent instances and fanning out the same writes yourself. **HA is an Enterprise-Edition (BUSL) feature** (v1.37+): replication assigns each shard to more than one node for redundancy, and sharding distributes a single index across nodes via Rendezvous (consistent) hashing on the document primary key ([blog](https://www.meilisearch.com/blog/horizontal-scaling-with-sharding), [docs](https://www.meilisearch.com/docs/resources/self_hosting/sharding/overview)). A write sent to any node is forwarded to all nodes, each of which indexes only its assigned subset. There is still **no automatic failover or leader election** documented, and a production self-hosted commercial license is required. The older community sharding/replication tracking issue ([GitHub #3494](https://github.com/meilisearch/meilisearch/issues/3494)) has effectively been superseded by this paid EE feature. See [replication-models](../concepts/replication-models.md).
- **Default isolation & what's achievable:** local ACID transactions come from LMDB (single-writer, MVCC-style readers; writers serialized). Indexing is **asynchronous** via a task queue, so a successful write returns a `taskUid` and the document is *not* yet searchable until the task is processed — read-your-writes is **not** immediate ([Tasks](https://www.meilisearch.com/docs/learn/async/asynchronous_operations)). This is the key consistency gotcha, not classic SQL isolation levels. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Tunable consistency:** no.
- **Clock dependency:** none of note. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read / flexible:** documents are schemaless JSON; you POST documents and Meilisearch infers fields. Per-index *settings* (searchable attributes, filterable/sortable attributes, ranking rules, synonyms, stop-words) act as a soft schema.
- **Migration/evolution:** changing index settings (e.g. adding a filterable attribute) triggers a **full re-index of that index** as an async task — can be expensive on large indexes; there is no online ALTER analog.
- **Type system:** JSON scalars, arrays, nested objects, geo points (`_geo`), and dense vectors (`_vectors`) for semantic search.

## Query interface
- **Language:** **HTTP/JSON REST API** (`/search`, `/documents`, `/settings`). No SQL, no query DSL beyond filter expressions (`filter` with `AND`/`OR`/`IN`, ranges). Official client SDKs for JS, Python, Go, Rust, PHP, Ruby, etc.
- **Search features:** typo tolerance, prefix search (search-as-you-type), faceting, sorting, geosearch, synonyms, stop-words, custom ranking rules; **hybrid search** mixing BM25-style keyword scoring with vector similarity via a tunable `semanticRatio` ([hybrid search](https://www.meilisearch.com/blog/hybrid-search)). Embeddings are generated by external models (OpenAI, HuggingFace, Ollama, user-provided).
- **Transactions:** **no multi-statement transactions** exposed to clients; writes are single-document/batch operations enqueued as tasks. Not a transactional store.
- **Joins / aggregations:** no joins; faceting gives count-style aggregation only. Denormalize at index time.
- **Stored procedures / UDFs:** none.

## Scaling & topology
- **Vertical-first in the free CE.** In the Community Edition you scale by giving one instance more RAM/CPU/NVMe; there is no native sharding, so single-index size is bounded by one machine. **Native sharding to distribute one index across nodes does exist, but only in the BUSL Enterprise Edition (v1.37+)** via Rendezvous hashing ([blog](https://www.meilisearch.com/blog/horizontal-scaling-with-sharding)).
- **Read scaling:** EE replication adds redundant shard copies for read availability; in the free CE you front multiple instances (independently fed the same writes) behind a load balancer with no managed read-replica or defined read consistency. ⚠️ unverified — CE replica freshness depends entirely on your fan-out write pipeline.
- **Resharding pain:** topology changes (adding/removing shards) run as `NetworkTopologyChange` tasks; searches referencing shards mid-change can fail until those tasks complete ([docs](https://www.meilisearch.com/docs/resources/self_hosting/sharding/overview)). N/A in the free CE (no sharding).
- **Storage/compute separation:** none; storage and query are co-located in one process over a local LMDB file. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** LMDB is memory-mapped with copy-on-write B+trees; it does **not** use a separate write-ahead log (durability comes from LMDB's transaction commit / msync, not a WAL replay step) — Meilisearch starts instantly with no log replay. Crash-consistency relies on LMDB's commit semantics; with default sync settings the data-loss window is small but indexing throughput vs. fsync is an LMDB tuning concern. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact default fsync/durability mode and its data-loss window are not clearly documented; verify before relying on it as a source of truth.
- **Throughput/latency:** designed for sub-50ms search ([source](https://www.meilisearch.com/blog/hybrid-search)). Writes are async and **single-threaded through the task queue** — bulk indexing and setting changes can lag, and the queue has a hard cap (~10GiB) that returns `no_space_left_on_device` when full, requiring task deletion ([GitHub #5161](https://github.com/meilisearch/meilisearch/issues/5161)).
- **Compaction / vacuum / GC:** LMDB does **not** return freed pages to the OS — deleting documents marks space free internally for reuse but on-disk file size does not shrink, so there is no compaction step (and disk can stay high after deletions) ([docs](https://www.meilisearch.com/docs/resources/internals/storage)).

## Operations & maturity
- **Backup/restore:** two mechanisms — **snapshots** (fast binary restore of the current DB state, version-locked) and **dumps** (raw, version-portable export used to upgrade across Meilisearch versions) ([snapshots spec](https://specs.meilisearch.dev/specifications/text/0258-snapshots-api.html)). No continuous PITR.
- **Observability:** task queue status API (every write is a trackable task), `/stats`, experimental metrics/Prometheus endpoint, logs. No EXPLAIN-style query planner output.
- **Upgrade story:** historically required a **dump-and-restore** across minor versions (breaking DB format). Since v1.12→v1.13, an **experimental "dumpless" in-place upgrade** is available via the `--experimental-dumpless-upgrade` flag, which auto-migrates indexes on launch; docs warn it can rarely corrupt the DB, so a snapshot first is mandatory ([updating docs](https://www.meilisearch.com/docs/learn/update_and_migration/updating)).
- **Maturity:** widely adopted OSS project, very good docs and DX. **No Jepsen report exists** for Meilisearch (verified — not listed on jepsen.io); a distributed-consistency Jepsen test would only be meaningful against the newer EE clustering, which has not been independently tested. Known failure modes: async write lag/queue saturation, full re-index on settings change, disk not reclaimed after deletes, and (in the free CE) no built-in HA.

## Ecosystem & people
- **Canonical use cases:** in-app / on-site instant search, e-commerce product search, documentation search, search-as-you-type autocomplete, hybrid semantic+keyword search for RAG/AI apps — a self-hosted, cheaper alternative to [algolia](algolia.md) and lighter than [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md).
- **Anti-patterns:** primary data store / system of record; analytics or aggregation workloads; datasets too large for one node's RAM/disk *unless you buy the EE for sharding*; applications requiring automatic failover or read-your-writes immediately after write (the free CE has no HA at all, and even EE clustering has no documented auto-failover/leader election). Use a real database (e.g. [postgresql](postgresql.md)) as the source of truth and index into Meilisearch.
- **Connectors:** REST + official SDKs; community integrations for Laravel Scout, Strapi, LangChain, and data sync via tools/CDC pipelines you wire up yourself (no first-class Kafka/Debezium/dbt integration).
- **Community:** active GitHub project, strong documentation, low learning curve; commercial support via Meilisearch Cloud.

## Licensing & cost
- **License: dual model since v1.19 (Aug 2025).** The **Community Edition is MIT — permissive** ([GitHub](https://github.com/meilisearch/meilisearch)) and covers all core full-text and AI/hybrid search. A separate **Enterprise Edition is under the Business Source License (BUSL 1.1)** — a source-available license that "cannot be freely used in production" without a commercial agreement ([EE license announcement](https://www.meilisearch.com/blog/enterprise-license), [EE docs](https://www.meilisearch.com/docs/resources/self_hosting/enterprise_edition)). EE-exclusive capabilities are **sharding/replication, analytics, and fine-grained access controls + advanced observability**; sharding is the headline EE-only feature. So the earlier framing that Meilisearch is purely MIT and avoided the source-available path is **outdated**: it stayed MIT for the core but moved scale/enterprise features to BUSL. Free EE licenses are offered to indie/non-profit projects on request. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable for free; **Meilisearch Cloud** is the managed offering (plans publicly start around $30/mo, scaling up by usage/searches) ([pricing](https://www.meilisearch.com/pricing)).
- **Lock-in:** low — permissive license, open format, dump/restore portability.
- **Cost model:** self-hosted = your hardware; Cloud = tiered by index size / number of searches, which can climb at high search volume.

## Hardware / deployment
- **Resource profile:** **memory-favoring.** Best performance when the dataset fits in RAM, but docs note a ~1/3 RAM-to-disk ratio is acceptable and some workloads tolerate ~1/10 ([docs](https://www.meilisearch.com/docs/resources/internals/storage)). Indexing is CPU-intensive; disk type matters a lot.
- **Storage assumptions:** **NVMe SSD strongly preferred**; HDD or network-attached storage degrades performance materially.
- **Footprint:** single binary, single node; trivial to run locally or in a container. Not embedded (it's a server), not natively clustered.
- **Deployment:** SaaS (Meilisearch Cloud) or on-prem/self-host; container/k8s-friendly as a single Deployment, but as a stateful single-writer it does not naturally fan out across a StatefulSet for HA.

## Bottom line
Reach for Meilisearch when you want Algolia-style instant, typo-tolerant, hybrid search that you can self-host under a permissive MIT license, your data fits comfortably on one beefy NVMe node, and a real database remains your source of truth. Do **not** use it as a primary store, for analytics, or where you need automatic failover — those remain structural gaps even with the paid tier. Horizontal sharding and replication now exist, but only in the **BUSL-licensed, commercially-licensed Enterprise Edition (v1.37+)**, and that clustering is a leader-follower model with no consensus and no documented auto-failover. The single biggest gotcha: **indexing is asynchronous**, so documents are not searchable the instant you write them; and in the free MIT Community Edition there is no built-in HA at all — you own availability and write fan-out yourself.

## Sources
- [Meilisearch — Storage engine (LMDB)](https://www.meilisearch.com/docs/resources/internals/storage)
- [Meilisearch — Enterprise Edition license announcement (BUSL, v1.19)](https://www.meilisearch.com/blog/enterprise-license)
- [Meilisearch — Enterprise vs Community editions](https://www.meilisearch.com/docs/resources/self_hosting/enterprise_edition)
- [Meilisearch — Replication and sharding overview](https://www.meilisearch.com/docs/resources/self_hosting/sharding/overview)
- [Meilisearch — Horizontal scaling with sharding (blog)](https://www.meilisearch.com/blog/horizontal-scaling-with-sharding)
- [Meilisearch — Updating / dumpless upgrade](https://www.meilisearch.com/docs/learn/update_and_migration/updating)
- [Meilisearch — Tasks and asynchronous operations](https://www.meilisearch.com/docs/learn/async/asynchronous_operations)
- [Meilisearch — Hybrid search](https://www.meilisearch.com/blog/hybrid-search)
- [Meilisearch — Pricing](https://www.meilisearch.com/pricing)
- [GitHub — meilisearch/meilisearch (MIT license)](https://github.com/meilisearch/meilisearch)
- [GitHub Issue #3494 — About replicating Meilisearch](https://github.com/meilisearch/meilisearch/issues/3494)
- [GitHub Issue #5161 — task queue processing limits](https://github.com/meilisearch/meilisearch/issues/5161)
- [Snapshots API specification](https://specs.meilisearch.dev/specifications/text/0258-snapshots-api.html)
