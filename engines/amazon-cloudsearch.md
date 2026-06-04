---
name: Amazon CloudSearch
slug: amazon-cloudsearch
rank: 126
data_model: Search engine
license: Proprietary (AWS managed service; built on Apache Solr internals)
summary: Fully-managed AWS search service built on Apache Solr — now closed to new customers, AWS steers everyone to OpenSearch.
last_researched: 2026-06-04
confidence: high
---

# Amazon CloudSearch

> A fully-managed, Solr-backed AWS search service that hides cluster ops behind a REST API — but it is in maintenance mode (closed to new sign-ups since July 2024) and AWS now pushes [opensearch](opensearch.md) instead.

## Identity
- **Taxonomy / data model:** Search engine (full-text/faceted document search), offered as a managed SaaS "search domain." Not a general-purpose database — it indexes documents you push to it; it is not the system of record. See [full-text-search](../concepts/full-text-search.md).
- **Storage model:** Inverted-index search engine. The 2013-01-01 API generation is built on **Apache Solr** (Lucene) internals ([AWS CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)); earlier 2011 API generations used AWS's own engine (A9). On-disk format is the managed Lucene index — not user-accessible. See [lsm-vs-btree](../concepts/lsm-vs-btree.md) for the inverted-index contrast (Lucene segments are immutable, merged like LSM SSTables).
- **Workload:** Read-heavy search/query serving, fed by batch document uploads. Not OLTP and not OLAP — a search index layered beside a primary store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** AP-leaning for the read path — search instances stay available and serve possibly-stale results. Not a transactional store, so CAP is a loose fit. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Else-case favors latency/availability over consistency — updates propagate to instances **eventually**, and AWS explicitly warns this can affect score-sorted results across instances ([CloudSearch troubleshooting docs](https://docs.aws.amazon.com/cloudsearch/latest/developerguide/troubleshooting.html)).
- **Default isolation & what's achievable:** N/A — no multi-document transactions, no isolation levels. Each document upload is independent; there is no notion of ACID here. Don't treat it as a database. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Managed internally. Auto-scaling replicates partitions (up to 5 replicas per partition) for traffic; optional **Multi-AZ** keeps standby instances in a second Availability Zone with automatic failover ([CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)). User has no control over the replication protocol. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No. Updates are eventually consistent; there is no per-query consistency level.
- **Clock dependency:** None exposed to the user. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** You define an index with typed fields before (or while) uploading; CloudSearch can also auto-detect fields from sample data.
- **Migration/evolution:** Adding/changing index fields triggers re-indexing of the domain; field changes are an online operation but require an explicit `IndexDocuments` run to take effect, and large domains re-index slowly.
- **Type system:** `text`, `literal`, `date`, `double`, `int` (64-bit signed), `latlon` (geospatial), plus array/multi-value variants ([CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)). No native JSON object/vector types — there is no vector/embedding field type; AWS explicitly cites semantic/vector search as a reason to move to OpenSearch ([Transition from CloudSearch to OpenSearch](https://aws.amazon.com/blogs/big-data/transition-from-amazon-cloudsearch-to-amazon-opensearch-service/)).

## Query interface
- **Language:** No SQL. REST search API with several query parsers — `simple`, `structured` (CloudSearch's Boolean DSL), Lucene, and `dismax` ([CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)). Supports faceting, highlighting, suggesters, field weighting, custom relevance/rank expressions, stemming, stopwords, synonyms across ~34 languages.
- **Transactions:** None. Document uploads are batched (`documents/batch`), not transactional.
- **Native vs app-side:** Search, facet, sort, geo-distance, and aggregation-style faceting are native. No joins — denormalize into documents before indexing.
- **Stored procedures / UDFs:** None. Relevance tuning is via expressions/rank config, not user code.

## Scaling & topology
- **Vertical + horizontal, both auto-managed.** Vertical: instance types `search.small` → `search.2xlarge`. Horizontal: automatic partitioning (documented limit ~10 partitions) and replica scaling based on data size and CPU; scales **down** below ~30% CPU to cut cost ([CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)).
- **Sharding:** Fully automatic — no manual shard keys, no resharding pain, but also no control. The flip side: you cannot tune placement, and re-indexing a large domain is opaque.
- **Read replicas:** Replicas serve search traffic; reads can be stale (eventual consistency).
- **Storage/compute separation:** No — classic instance-coupled storage. Contrast modern serverless search. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Documents are uploaded in batches (max 5 MB/batch, ~one batch per 10 s per recommendation; parallel batches allowed) and indexed near-real-time — searchable within "seconds to a few minutes" ([CloudSearch FAQ](https://aws.amazon.com/cloudsearch/faqs/)). AWS states uploaded updates are stored durably; the write path/WAL details are not user-exposed. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** ⚠️ unverified — no official p99 SLAs published; latency is a function of instance type and partition count, both auto-scaled. Tail behavior during a scale-up/re-partition event is the practical risk.
- **Compaction/vacuum/GC:** Lucene segment merges handled internally; not user-tunable and not exposed in metrics beyond coarse CloudWatch counters.

## Operations & maturity
- **Backup/restore, PITR:** No native snapshot/restore of the index — the documented recovery model is **re-upload from your source of truth**. There is no PITR. This is the biggest operational gotcha: CloudSearch is a derived index, not durable primary storage.
- **Observability:** CloudWatch metrics (search/index instance counts, partitions, CPU), AWS Console domain dashboard, CloudTrail for control-plane calls. No deep query-plan/EXPLAIN tooling.
- **Upgrade story:** Fully managed; AWS patches the fleet. The major "upgrade" is migrating off it.
- **Maturity:** Launched 2012, Solr-based generation since 2013. Mature but **frozen** — AWS "does not plan to introduce new features" and **closed CloudSearch to new customers effective July 25, 2024** ([AWS: Transition from CloudSearch to OpenSearch](https://aws.amazon.com/blogs/big-data/transition-from-amazon-cloudsearch-to-amazon-opensearch-service/)). No Jepsen analysis exists or is relevant (not a consistency-critical store).

## Ecosystem & people
- **Canonical use cases:** Add site/app/catalog search to an existing application with minimal ops — faceted e-commerce search, document/content search where you want a managed box and don't need vector/semantic search.
- **Anti-patterns:** As a system of record or database (no transactions, no PITR); for log/observability analytics (use OpenSearch/Elasticsearch); for semantic/vector search (no embedding support); and for **any new project** — it's closed to new customers, so picking it is picking a dead end.
- **Drivers/connectors:** AWS SDKs (Java, Python, Ruby, .NET, PHP, Node.js), AWS CLI. No first-class CDC/Kafka/dbt integration — you write your own upload pipeline. AWS recommends OpenSearch Ingestion for migration.
- **Community/support:** Backed by AWS Support; community momentum has fully shifted to OpenSearch/Elasticsearch. Docs are adequate but no longer evolving.

## Licensing & cost
- **License:** Proprietary AWS managed service. Internally built on Apache Solr/Lucene (Apache 2.0), but you consume it as a closed SaaS — no self-hosting. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Managed-only:** Cannot be self-hosted. Lock-in is real: the query DSL, field-config format, and API are AWS-specific, so migrating means re-modeling (AWS provides a CloudSearch→OpenSearch transition path but it is a rewrite, not a lift-and-shift).
- **Cost model:** Per **search-instance-hour** (billed as full hours, by instance type) dominates cost; plus **$0.10 per 1,000 batch upload requests**, index-document data charges, and data transfer ([CloudSearch pricing](https://aws.amazon.com/cloudsearch/pricing/)). Cheap at small scale; cost grows with partitions/replicas as data and traffic rise.

## Hardware / deployment
- **Resource profile:** Managed; effectively memory/CPU-bound like any Lucene index (hot index benefits from RAM), but the user only picks instance size, not memory tuning.
- **Storage assumptions:** Abstracted away — AWS-managed instance storage; no NVMe-vs-EBS choice exposed.
- **Footprint:** Managed cloud service ("search domain"); not embeddable, not self-hostable, not serverless (instances are provisioned, though auto-scaled).
- **Deployment:** SaaS only, AWS regions. No on-prem, no container/k8s deployment — you call an HTTPS endpoint.

## Bottom line
CloudSearch was a reasonable "managed Solr without the ops" choice a decade ago, and existing domains still run fine. But AWS closed it to new customers in July 2024 and froze feature work, steering everyone to [opensearch](opensearch.md), which adds vector/semantic search. **Do not start anything new on it.** The single biggest gotcha: it is a derived index with no snapshot/PITR — your documents must be durably stored elsewhere, because the only recovery path is re-uploading them.

## Sources
- [Amazon CloudSearch FAQs](https://aws.amazon.com/cloudsearch/faqs/)
- [Amazon CloudSearch Pricing](https://aws.amazon.com/cloudsearch/pricing/)
- [AWS Big Data Blog: Transition from Amazon CloudSearch to Amazon OpenSearch Service](https://aws.amazon.com/blogs/big-data/transition-from-amazon-cloudsearch-to-amazon-opensearch-service/) (closed to new customers July 25, 2024; maintenance mode)
- [Amazon CloudSearch Developer Guide — Troubleshooting](https://docs.aws.amazon.com/cloudsearch/latest/developerguide/troubleshooting.html) (eventual consistency of updates across instances)
- [Amazon CloudSearch Developer Guide — Uploading Data](https://docs.aws.amazon.com/cloudsearch/latest/developerguide/uploading-data.html)
