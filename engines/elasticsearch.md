---
name: Elasticsearch
slug: elasticsearch
rank: 12
data_model: Search engine (multi-model: document store, vector, time-series/logs)
license: Triple-licensed — AGPLv3 / SSPL 1.0 / Elastic License v2 (source-available); see [license-taxonomy](../concepts/license-taxonomy.md)
summary: Distributed Lucene-based search engine that doubles as a JSON document store; great for search/log analytics, not a system of record.
last_researched: 2026-06-04
confidence: high
---

# Elasticsearch

> A distributed, near-real-time full-text search and analytics engine built on Lucene — the heart of the **ELK / Elastic Stack** and the default for search, observability, and log analytics, but historically weak as a primary store of record (acknowledged writes were lost under partition in Jepsen testing).

## When to use

**Use Elasticsearch if:**
- ✅ You need fast full-text/site search or log/observability/SIEM analytics at scale with rich aggregations and best-in-class introspection (the ELK/Elastic Stack).
- ✅ You want semantic/hybrid search combining BM25 with `dense_vector` kNN/ANN in one engine.
- ✅ You can treat it as a derived index over a real source of truth, keeping durability guarantees elsewhere.

**Avoid Elasticsearch if:**
- ❌ You need a system of record for transactional/financial data — there are no cross-document transactions and it has a history of losing acknowledged writes under partition (Jepsen).
- ❌ You need relational joins or serializable transactions — joins are an anti-pattern (denormalize at index time) and there are no isolation levels.
- ❌ Your design can't commit to fixed primary shard count and field types at index creation — changing them means a full reindex (shard/mapping rigidity is the biggest gotcha).
- **Taxonomy / data model:** primarily a [full-text-search](../concepts/full-text-search.md) engine; secondarily a schemaless JSON document store, a [vector-search-ann](../concepts/vector-search-ann.md) engine (dense_vector + HNSW kNN), and the storage layer for logs/metrics/traces (the "ELK"/observability stack). Effectively multi-model around an inverted index.
- **Storage model:** built on Apache Lucene. Each shard is a Lucene index composed of immutable **segments**; each segment is an inverted index (term → posting list). Append-only segment writes plus background merges — closer in spirit to [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM than B-tree. Columnar `doc_values` (on disk) back sorting/aggregations; `dense_vector` fields back ANN.
- **Workload:** search and OLAP-style analytics over documents/logs, not OLTP. Aggregations are strong; it is not a transactional store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — no transactional row engine.

## Distribution & consistency
- **CAP under partition:** **AP-leaning in practice for safety.** Historically Elasticsearch acknowledged writes that were then lost: the 2014 [Jepsen 1.1.0](https://aphyr.com/posts/317-jepsen-elasticsearch) run found 645 of 1961 acknowledged writes lost under nontransitive partitions; the 2015 [Jepsen 1.5.0](https://aphyr.com/posts/323-jepsen-elasticsearch-1-5-0) follow-up reduced but did not eliminate the loss (e.g. 22 of 897 under intersecting partitions, 209 of 947 when isolating primaries, ~10% on node-crash patterns), with concurrent primaries accepting and later discarding writes. The post-7.0 rewrite (below) closed the worst of these, but Elasticsearch has **not** re-run a public Jepsen audit, so treat strong-consistency claims as unverified for the cluster as a whole.
- **PACELC:** under Partition it historically favored Availability over Consistency (acked-then-lost writes); Else it favors low Latency — search is near-real-time (default 1s refresh), reads can be stale. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** **no multi-document transactions and no isolation levels.** Single-document operations are atomic; concurrency safety is via [mvcc](../concepts/mvcc.md)-style optimistic concurrency control using `_seq_no` + `_primary_term` (compare-and-set on write) ([optimistic concurrency control](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/optimistic-concurrency-control)). There is no notion of "ACID across documents." See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **single-leader per shard** (primary → replicas), synchronous to in-sync replicas before ack. Sequence-number-based replication (since 6.0) plus primary terms (a Raft-like generation counter) prevent stale primaries from overwriting newer data ([sequence IDs](https://www.elastic.co/blog/elasticsearch-sequence-ids-6-0)). **Cluster-state/metadata** consensus uses the 7.0 "Zen2" coordination layer, a formally-modeled (TLA+) Raft-/VR-style protocol replacing the older ad-hoc Zen discovery ([a new era for cluster coordination](https://www.elastic.co/blog/a-new-era-for-cluster-coordination-in-elasticsearch); [formal models](https://github.com/elastic/elasticsearch-formal-models)). See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** `wait_for_active_shards` controls how many shard copies must be available before a write proceeds; refresh policy (`wait_for`/`true`) controls read-your-write visibility. No Dynamo-style per-query R/W quorum knobs.
- **Clock dependency:** correctness does not depend on synchronized clocks (uses seq numbers + primary terms, not timestamps). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write with dynamic mapping.** You can index JSON without a schema (fields are auto-typed), but the resulting **mapping is the schema** and is largely immutable: you can add fields but generally **cannot change a field's type** without reindexing into a new index.
- **Migration/evolution:** field additions are online; type changes require a full reindex (then alias swap). No `ALTER`-style in-place column retype.
- **Type system:** text/keyword, numeric, date, boolean, `object`/`nested`, geo_point/geo_shape (geospatial), `dense_vector` (kNN/ANN), `ip`, ranges, `flattened`, runtime fields. Analyzers/tokenizers configure full-text behavior.

## Query interface
- **Language:** primarily the **Query DSL** (JSON over a REST API). Also: **ES|QL** (a piped query language, GA in 8.x), SQL (read-only subset via the `_sql` API), EQL (event sequences), KQL (Kibana), and Painless scripting. API-first, not SQL-first.
- **Transactions:** **none across documents.** Single-doc atomicity only; bulk requests are not atomic.
- **Native vs app-side:** rich full-text scoring (BM25), aggregations (metric/bucket/pipeline), and ANN kNN are native. **No native joins** — only limited workarounds: `nested` docs, `parent/join` (single-shard), `terms` lookup, or denormalization. Cross-index joins are an anti-pattern; you denormalize at index time.
- **Stored procedures / UDFs:** Painless scripts (sandboxed) for scoring, runtime fields, ingest pipelines; ingest processors for ETL-on-write. No SQL stored procedures.

## Scaling & topology
- **Horizontal by design.** Indices split into **shards**; shards spread across nodes; each shard has 0..N replicas for HA and read throughput.
- **Sharding (resharding pain):** primary shard count is **fixed at index creation** — to change it you `_split`/`_shrink` (constrained) or **reindex** into a new index. This rigidity is a classic operational gotcha; over-sharding ("shard explosion") also degrades the cluster. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / consistency:** replica reads are near-real-time but may be stale up to the refresh interval (default 1s) and lag replication; not guaranteed read-your-writes unless you set the refresh policy.
- **Storage/compute separation:** classic deployment couples compute+local disk. Newer **searchable snapshots** + frozen tier read directly from object storage, and **Stateless Elasticsearch** / Elastic Cloud Serverless decouple storage (object store) from compute — a move toward [storage-compute-separation](../concepts/storage-compute-separation.md). ⚠️ unverified — exact GA scope of Stateless/Serverless varies by deployment.

## Performance & durability
- **Write path:** doc → in-memory buffer + **translog** (write-ahead log). **Refresh** (default 1s) makes docs searchable by creating a new segment in filesystem cache (not yet fsynced). **Flush** commits Lucene segments and fsyncs/truncates the translog. Default `index.translog.durability: request` fsyncs+commits the translog on primary and all allocated replicas **before acking** each write; `async` fsyncs only every `sync_interval` (default 5s), trading a crash data-loss window for throughput ([translog settings](https://www.elastic.co/docs/reference/elasticsearch/index-settings/translog)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** excellent read/search latency and high ingest throughput; p99 search tail is hurt by large/expensive aggregations, deep pagination, GC pauses (JVM, heap-bound), and cold/frozen-tier object-store fetches.
- **Compaction/GC:** background **segment merging** (LSM-style) reclaims deleted docs and bounds segment count; merges are I/O-heavy and can spike p99. JVM garbage collection pauses are a real tail-latency source; heap should generally stay ≤~31 GB (compressed oops).

## Operations & maturity
- **Backup/restore:** native **snapshot/restore** to S3/GCS/Azure/shared FS; searchable snapshots; no traditional PITR/WAL-replay — recovery granularity is the snapshot.
- **Observability:** rich `_cat`, `_cluster/health`, `_nodes/stats`, `_profile` (query plans), slowlogs, and tight Kibana integration; arguably best-in-class introspection.
- **Upgrade story:** rolling upgrades supported within constraints; one-major-version reindex/compat rules apply. Day-2 burden is real: shard sizing, mapping discipline, heap/GC tuning, ILM (index lifecycle) for hot-warm-cold-frozen tiers.
- **Maturity:** very mature, huge production footprint. Known failure modes: historical **acked-write loss under partition** ([Jepsen 1.5.0](https://aphyr.com/posts/323-jepsen-elasticsearch-1-5-0), [Jepsen 1.1.0](https://aphyr.com/posts/317-jepsen-elasticsearch)); shard explosion; mapping explosion; split-brain (largely fixed by Zen2). No current public Jepsen re-audit of the modern coordination layer.

## Ecosystem & people
- **The ELK / Elastic Stack:** Elasticsearch is the **datastore + search/aggregation engine at the center of a stack**, not a standalone product in most deployments. The classic **ELK** trio is **E**lasticsearch (store + query) + **L**ogstash (server-side ingest/transform pipeline) + **K**ibana (the visualization/exploration/dashboard UI). Elastic later added **Beats** (lightweight per-host shippers — Filebeat for logs, Metricbeat, Packetbeat, etc.) and the unified **Elastic Agent**/Fleet, and rebranded the whole thing the **Elastic Stack**. Typical data flow: *Beats/Logstash → Elasticsearch → Kibana*. It is the dominant **open(-ish) logs/observability/SIEM platform** — the dual to [splunk](splunk.md) — spanning centralized logging, full observability (logs/metrics/traces via Elastic APM), and security analytics. Note Logstash is heavy (JVM, rich filter plugins); many modern pipelines push transforms into **Elasticsearch ingest pipelines** or ship via Beats/**OpenTelemetry** directly, reserving Logstash for complex enrichment. The Apache-2.0 [opensearch](opensearch.md) fork ships a parallel stack: OpenSearch + **OpenSearch Dashboards** (Kibana fork) + **Data Prepper**/Logstash. Logstash and Kibana are companion tools, not databases, so they have no separate page here.
- **Canonical use cases:** full-text/site search, log & observability analytics (ELK/Elastic Stack), security analytics (SIEM), geo search, and increasingly semantic/hybrid (BM25 + vector) search.
- **Anti-patterns:** system-of-record for financial/transactional data (no cross-doc ACID, history of write loss); workloads needing relational joins or strong serializable transactions; high-cardinality frequently-updated documents (every update rewrites/marks-deletes a doc). When you need durability guarantees, keep the source of truth elsewhere and treat ES as a derived index.
- **Ecosystem:** enormous. Official clients (Java/Python/JS/Go/.NET/etc.), Logstash/Beats/Elastic Agent ingestion, Kibana for viz, Kafka connectors, Debezium/CDC, dbt and BI via ES|QL/SQL bridges. Docs are extensive; learning curve moderate (Query DSL + sharding/mapping mental model).

## Licensing & cost
- **License:** **triple-licensed.** Originally Apache 2.0; **relicensed in 2021 (7.11)** to dual SSPL 1.0 / Elastic License v2 amid the AWS/OpenSearch fork dispute; in **2024 Elastic added AGPLv3** (OSI-approved) as a third option ([Elastic AGPL announcement coverage](https://www.infoq.com/news/2024/09/elastic-open-source-agpl/); [Elastic licensing FAQ](https://www.elastic.co/pricing/faq/licensing)). SSPL/ELv2 are **source-available, not OSI-open**; AGPLv3 is copyleft. The 2021 change spawned the **[opensearch](opensearch.md)** (Apache 2.0) fork by AWS. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-host (free tier under any of the three licenses) or Elastic Cloud (and AWS/GCP/Azure marketplace). Advanced features (some security, ML, etc.) gated behind paid subscription tiers under ELv2.
- **Lock-in:** moderate — Query DSL, ES|QL, mappings, and ingest pipelines are Elastic-specific; OpenSearch is largely wire-compatible for older versions but has diverged.
- **Cost model:** self-managed = per-node infra; Elastic Cloud = per resource (RAM/storage/compute) per tier; Serverless = consumption-based. Cost scales with data volume and replica/retention choices; hot-tier RAM is the expensive part.

## Hardware / deployment
- **Resource profile:** **memory-bound** (JVM heap + OS filesystem cache for Lucene; hot working set ideally cached) and I/O-bound on ingest/merge; CPU-bound on analysis and aggregations. Heap typically capped ~31 GB; rely on OS cache for the rest.
- **Storage assumptions:** **local NVMe/SSD strongly preferred** for hot data; network-attached/object storage acceptable for warm/cold/frozen (searchable snapshots) with higher latency.
- **Footprint:** clustered/distributed (not embedded, not single-binary-trivial at scale). Runs on the JVM.
- **Deployment:** SaaS (Elastic Cloud/Serverless) or on-prem; Kubernetes via **ECK operator** (StatefulSets, persistent volumes); container-friendly but stateful-set realities (volume affinity, rolling restarts, shard recovery) apply.

## Bottom line
Reach for Elasticsearch when you need fast full-text/log/observability/vector search at scale with rich aggregations and a best-in-class ops/visualization ecosystem. Do **not** make it your system of record: there are no cross-document transactions, and its history of losing acknowledged writes under partition ([Jepsen](https://aphyr.com/posts/323-jepsen-elasticsearch-1-5-0)) means the source of truth belongs in a real database with ES as a derived index. The single biggest gotcha is shard/mapping rigidity — primary shard count and field types are fixed at index creation, so a bad initial design means a full reindex later.

## Sources
- [Optimistic concurrency control — Elasticsearch docs](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/optimistic-concurrency-control)
- [Translog settings — Elasticsearch docs](https://www.elastic.co/docs/reference/elasticsearch/index-settings/translog)
- [A new era for cluster coordination in Elasticsearch (Zen2) — Elastic blog](https://www.elastic.co/blog/a-new-era-for-cluster-coordination-in-elasticsearch)
- [Sequence IDs: Coming Soon to an Elasticsearch Cluster Near You — Elastic blog](https://www.elastic.co/blog/elasticsearch-sequence-ids-6-0)
- [Elasticsearch formal models (TLA+) — GitHub](https://github.com/elastic/elasticsearch-formal-models)
- [Jepsen: Elasticsearch 1.5.0](https://aphyr.com/posts/323-jepsen-elasticsearch-1-5-0)
- [Jepsen: Elasticsearch (1.1.0)](https://aphyr.com/posts/317-jepsen-elasticsearch)
- [Elastic licensing FAQ](https://www.elastic.co/pricing/faq/licensing)
- [Elastic returns to open source with AGPLv3 — InfoQ](https://www.infoq.com/news/2024/09/elastic-open-source-agpl/)
