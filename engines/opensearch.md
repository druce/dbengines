---
name: OpenSearch
slug: opensearch
rank: 32
data_model: Search engine (multi-model — also document, vector)
license: Apache 2.0 (permissive); governed by the OpenSearch Software Foundation (Linux Foundation)
summary: Apache-2.0 fork of Elasticsearch 7.10; a Lucene-backed distributed search/analytics engine for logs, search, and vectors — not a system of record.
last_researched: 2026-06-04
confidence: high
---

# OpenSearch

> Community-governed, Apache-2.0 fork of Elasticsearch 7.10 — a distributed Lucene search/analytics engine for logs, observability, full-text and vector search, with the same near-real-time, eventually-consistent, non-transactional behavior as its parent (so do not use it as your primary store).

## When to use

**Use OpenSearch if:**
- ✅ You need vendor-neutral, Apache-2.0 full-text search, log/observability analytics, or SIEM at scale (the ELK niche, no SSPL)
- ✅ You want native k-NN/vector + hybrid (keyword+vector) search and RAG retrieval with built-in ML pipelines
- ✅ You can tier hot/warm/cold via remote-backed storage and searchable snapshots to control cost at log-scale retention

**Avoid OpenSearch if:**
- ❌ You want a system of record — it is near-real-time and **non-transactional**: reads lag writes, multi-document ops are not atomic, durability depends on translog settings
- ❌ You need relational joins or strict OLTP (no cross-document joins; denormalize instead)
- ❌ You need strong consistency / read-your-writes by default (the parent's Jepsen history shows write loss under partition)
- ❌ You can't manage shard/heap sizing, segment merges, and JVM GC — the usual p99 and operational footguns

## Identity
- **Taxonomy / data model:** Search engine; multi-model in practice — JSON document store with [full-text-search](../concepts/full-text-search.md), plus a native k-NN/[vector-search-ann](../concepts/vector-search-ann.md) engine (HNSW/IVF via Lucene, FAISS, nmslib). Forked from Elasticsearch 7.10.2 + Kibana 7.10.2 after Elastic's 2021 relicense ([InfoWorld](https://www.infoworld.com/article/3971473/opensearch-in-2025-much-more-than-an-elasticsearch-fork.html)).
- **Storage model:** Inverted indexes + columnar doc-values + row-ish `_source` JSON, all in immutable Apache Lucene segments. Segments are write-once and merged; the engine is append-merge, closer to [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM than B-tree. Per-shard write-ahead translog for durability.
- **Workload:** OLAP/search-analytics, not OLTP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Strong at search, aggregations, and log/observability analytics; weak at point-consistent transactional writes. No HTAP claim.

## Distribution & consistency
- **CAP under partition:** Effectively **AP/eventually-consistent for search**; the indexing path is CP-ish at the document level (writes need an in-sync primary + quorum of replicas to ack) but search reads are near-real-time and can serve stale data. Inherits Elasticsearch's distributed design; the classic [Jepsen: Elasticsearch](https://aphyr.com/posts/317-jepsen-elasticsearch) report documented lost/dirty writes under partition in the pre-fork engine — ⚠️ unverified — no public Jepsen analysis exists for OpenSearch specifically, so treat the parent's findings as the closest evidence. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition (P) it favors availability of reads while pausing writes that cannot reach a quorum; else (E) it favors **latency** — search reads default to ~1s-stale (refresh interval) over strict consistency.
- **Default isolation & what's achievable:** **No multi-document transactions and no isolation levels.** Single-document index/update/delete is atomic; multi-doc `_bulk` is *not* transactional (partial failures possible). Concurrency is **[mvcc](../concepts/mvcc.md)-style optimistic concurrency control** via `_seq_no` + `_primary_term`; conflicts raise `VersionConflictEngineException` ([OpenSearch docs](https://docs.opensearch.org/latest/api-reference/document-apis/index/)). Calling this engine "ACID" is wrong — there are no transactions. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-leader per shard (primary → replicas). Two intra-cluster modes: **document replication** (default; replicas re-index each op) and **segment replication** (primaries ship Lucene segments to replicas, ~25% higher ingest throughput but replicas lag → more visibly eventually consistent) ([SegRep consistency issue #8700](https://github.com/opensearch-project/OpenSearch/issues/8700)). Cross-cluster replication is active-passive (follower pulls from leader). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Per-request `wait_for_active_shards`, refresh control (`refresh=wait_for`/`true`), and read preference, but no Dynamo-style per-query consistency levels.
- **Clock dependency:** Cluster coordination uses a custom Raft-inspired quorum/two-phase-commit subsystem (inherited from Elasticsearch's Zen2, not literally Raft) requiring a majority of cluster-manager-eligible nodes — not wall-clock; correctness does not rest on synchronized clocks ([OpenSearch voting & quorum docs](https://docs.opensearch.org/latest/tuning-your-cluster/discovery-cluster-formation/voting-quorums/)). See [clocks-and-time](../concepts/clocks-and-time.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).

## Schema
- **Schema-on-write with dynamic mapping:** indexes have mappings; by default new fields are auto-typed on first write ("dynamic mapping"), which feels schemaless but is schema-on-write under the hood.
- **Migration/evolution:** Field mappings are largely **immutable** — you can add fields but cannot change an existing field's type; doing so requires reindexing into a new index (aliases + `_reindex` are the standard online-ish migration path). No `ALTER`-style in-place type change.
- **Type system:** rich — text/keyword, numeric, date, boolean, `object`/`nested`, `geo_point`/`geo_shape`, IP, `dense_vector`-equivalent `knn_vector`, `flat_object`, percolator. Native JSON throughout.

## Query interface
- **Language:** primary is **Query DSL** (JSON over the `_search` REST API). Also a **SQL** plugin (read-only `SELECT`/`WHERE`/`GROUP BY`, not a full RDBMS dialect) and **PPL** (Piped Processing Language, pipe-operator query language aimed at observability) ([SQL/PPL docs](https://docs.opensearch.org/latest/sql-and-ppl/)).
- **Transactions:** none (see above) — single-document atomicity only.
- **Native vs app-side:** powerful native full-text + aggregations + k-NN + `nested`/`join` field types and parent-child; **no relational joins** across documents (denormalize instead). Secondary "indexes" are inherent (everything is indexed per mapping).
- **Stored procedures / UDFs:** no SQL stored procedures; extensibility is via Painless scripting (sandboxed scripting language), ingest pipelines/processors, and Java plugins. ML/search pipelines and a built-in ML Commons + agent framework for neural/hybrid search.

## Scaling & topology
- **Vertical vs horizontal:** horizontal — indexes split into **shards** (fixed primary count at creation) spread across data nodes. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding pain:** primary shard count is **fixed at index creation**; changing it requires `_split`/`_shrink`/reindex. Over-sharding and oversized shards are the classic operational footguns. Replicas are adjustable online.
- **Read replicas & consistency:** replica shards serve reads; reads can be stale relative to primary (eventual, bounded by refresh). No read-your-writes guarantee unless you force a refresh or read by primary.
- **Storage/compute separation:** yes, increasingly — **remote-backed storage** uploads segments/translog to object stores (e.g. S3), **searchable snapshots** + warm/cold node tiers query data directly from object storage, decoupling storage from compute. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** per-shard **translog** (WAL). Default `index.translog.durability=request` → `fsync` after every request, so acknowledged writes survive crash; setting `async` (`sync_interval` 5s default) trades durability for throughput — **all acked writes since the last fsync can be lost on crash** ([OpenSearch concepts/translog docs](https://docs.opensearch.org/latest/getting-started/concepts/)). Remote-backed storage offers refresh-level or request-level durability to object storage. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** high ingest and sub-second search at scale; near-real-time visibility (default 1s refresh). Segment replication raises ingest ~25%; OpenSearch 3.0 (Lucene 10, JDK 21) is reported ~8.4x faster than 1.3 on aggregate ([OpenSearch 3.0 blog](https://opensearch.org/blog/opensearch-3-0-what-to-expect/)).
- **p99 tail:** dominated by JVM **GC pauses**, segment **merges**, large/expensive aggregations, and heavy k-NN queries; oversized shards and heap pressure are the usual tail-latency culprits.
- **Compaction/GC:** background segment merging reclaims deletes and consolidates segments (I/O-heavy, can spike p99); force-merge available for read-only indexes. JVM heap GC is a separate, ever-present tuning concern.

## Operations & maturity
- **Backup/restore, PITR:** snapshot/restore to object storage (incremental); searchable snapshots; no continuous PITR-to-a-timestamp like an RDBMS — recovery granularity is the last snapshot.
- **Observability:** OpenSearch Dashboards (Kibana fork), `_cat`/`_cluster`/`_nodes/stats` APIs, the Profile API and `_search?explain` for query plans, slow logs for slow queries/indexing, plus a Prometheus exporter.
- **Upgrade story:** rolling upgrades supported within compatible versions; major upgrades (e.g. 2.x→3.0 on Lucene 10) carry **breaking changes** and reindex requirements for old-format indexes. Day-2 burden is real: shard/heap sizing, ILM/ISM lifecycle policies, merge and GC tuning.
- **Maturity:** very mature lineage (Elasticsearch/Lucene); large production footprint via AWS OpenSearch Service, OCI, Aiven, Instaclustr, self-managed. **Known failure modes:** split-brain historically (mitigated by quorum coordination), data loss with `async` translog or aggressive settings, and write loss under partition per the parent's Jepsen history. No OpenSearch-specific Jepsen report published.

## Ecosystem & people
- **Canonical use cases:** log/observability analytics (the OpenSearch/ELK niche), site and product full-text search, security analytics/SIEM, and vector/semantic + hybrid (keyword+vector) search and RAG retrieval.
- **Anti-patterns:** as a **primary/system-of-record database** (no transactions, eventual reads, mapping rigidity), for relational/joined workloads, for strict OLTP, or for use cases needing serializability or strong read-your-writes by default.
- **Connectors:** Data Prepper, Logstash, Fluentd/Fluent Bit, OpenSearch ingestion pipelines, Kafka connectors, CDC into it (e.g. Debezium → OpenSearch), language clients (Java, Python, Go, JS, etc.). Good docs; learning curve is moderate (Query DSL + shard/cluster ops). Active community under the Linux Foundation.

## Licensing & cost
- **OSS license & flavor:** **Apache 2.0** — fully permissive, no CLA — explicitly created to escape Elastic's source-available SSPL/Elastic License relicensing of 2021 ([Wikipedia](https://en.wikipedia.org/wiki/OpenSearch_(software))). See [license-taxonomy](../concepts/license-taxonomy.md). Since **September 2024** governed by the **OpenSearch Software Foundation** under the Linux Foundation (AWS donated it; TSC retains technical control) ([Linux Foundation](https://www.linuxfoundation.org/blog/how-the-opensearch-software-foundation-will-ensure-long-term-sustainability-of-the-opensearch-project)).
- **Self-managed vs managed:** both — fully self-hostable, plus Amazon OpenSearch Service, OCI Search, Aiven, Instaclustr. Low lock-in (open APIs, open license); managed services add proprietary ops conveniences.
- **Cost model:** self-managed = your hardware. Managed = per-node/instance-hour + storage (+ often separate data-ingestion or serverless OCU pricing on AWS). Cost scales with data volume and replica count; cheap to start, can get expensive at log-scale retention — searchable snapshots/warm-cold tiers exist to cut it.

## Hardware / deployment
- **Resource profile:** **memory- and CPU-bound**, JVM-based. Working set need not fit fully in RAM, but filesystem cache and JVM heap (rule of thumb ≤ ~50% RAM, under ~32 GB heap for compressed oops) dominate performance; k-NN/HNSW indexes are RAM-hungry.
- **Storage assumptions:** local **NVMe/SSD** strongly preferred for hot data; network-attached/object storage acceptable for warm/cold/searchable-snapshot tiers.
- **Footprint:** clustered (multi-node) by default; runs single-node for dev. Not embedded. Remote-store + serverless-style options emerging.
- **Deployment:** SaaS (AWS/OCI/Aiven) or on-prem; container/Kubernetes-friendly with the OpenSearch Operator and Helm charts (StatefulSets + persistent volumes; standard stateful-cluster operational care applies).

## Bottom line
Reach for OpenSearch when you need open-source (Apache-2.0, vendor-neutral) full-text search, log/observability analytics, or vector/hybrid search at scale and want to avoid Elastic's source-available licensing. Do not reach for it as a system of record, for transactional/relational workloads, or when you need strong consistency by default. The single biggest gotcha: it is **near-real-time and non-transactional** — search reads lag writes, multi-document operations are not atomic, and durability/consistency depend on settings (translog mode, replication mode) you must understand before trusting it with data you cannot reconstruct.

## Sources
- [OpenSearch documentation — concepts, document APIs, SQL/PPL](https://docs.opensearch.org/latest/)
- [OpenSearch 3.0: Lucene 10, breaking changes, performance](https://opensearch.org/blog/opensearch-3-0-what-to-expect/)
- [Segment replication consistency limitations (issue #8700)](https://github.com/opensearch-project/OpenSearch/issues/8700)
- [Linux Foundation — OpenSearch Software Foundation](https://www.linuxfoundation.org/blog/how-the-opensearch-software-foundation-will-ensure-long-term-sustainability-of-the-opensearch-project)
- [Wikipedia — OpenSearch (software), origin & license](https://en.wikipedia.org/wiki/OpenSearch_(software))
- [Jepsen: Elasticsearch (pre-fork parent engine)](https://aphyr.com/posts/317-jepsen-elasticsearch)
- [InfoWorld — OpenSearch in 2025: more than an Elasticsearch fork](https://www.infoworld.com/article/3971473/opensearch-in-2025-much-more-than-an-elasticsearch-fork.html)
