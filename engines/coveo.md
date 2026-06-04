---
name: Coveo
slug: coveo
rank: 110
data_model: Search engine (hosted SaaS)
license: Proprietary / commercial SaaS (closed-source)
summary: Cloud-only enterprise/commerce AI-search service — a managed index plus ML relevance and RAG layer, not a database you self-host.
last_researched: 2026-06-04
confidence: medium
---

# Coveo

> A proprietary, fully-managed enterprise and commerce search-as-a-service: you push or crawl content into Coveo's cloud index and consume search, recommendations, and generative answers via API — there is no self-hostable engine and no general-purpose query/storage interface.

## Identity
- **Taxonomy / data model:** [full-text-search](../concepts/full-text-search.md) engine delivered as SaaS, layered with [vector-search-ann](../concepts/vector-search-ann.md) semantic retrieval, ML ranking, recommendations, and RAG ("Relevance Generative Answering"). It is a search/relevance platform, not a system-of-record database — content lives in source systems (Salesforce, ServiceNow, Sitecore, websites, file shares) and Coveo indexes a copy.
- **Storage model:** proprietary binary inverted index stored on encrypted volumes ([Coveo content security docs](https://docs.coveo.com/en/1779/)); not row/column/document-store in the DB sense, and the on-disk format is closed. Underlying index technology is proprietary and undocumented publicly (⚠️ unverified — Coveo does not state whether the modern Cloud index derives from its older on-prem CES engine or a rewrite). Document chunks are also embedded into a vector space for semantic/RGA retrieval ([Semantic Encoder docs](https://docs.coveo.com/en/nb6a0483/leverage-machine-learning/about-semantic-encoder-se)).
- **Workload:** read-heavy search/discovery serving (the search analogue of OLTP query serving). Not OLTP and not OLAP — see [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not an analytics warehouse; it serves low-latency user-facing search, recommendation, and answer requests.

## Distribution & consistency
- **CAP under partition:** N/A in the classic sense — Coveo is a managed multi-tenant cloud service, not a database whose partition behavior you reason about. It is a secondary search index over external sources, so it is **eventually consistent with the source of truth**: indexed content lags the origin system until the next crawl/refresh or push. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — no exposed tunable consistency/latency model; consistency-with-source is governed by refresh cadence and Push/Stream API ingestion, not by a quorum protocol.
- **Default isolation & what's achievable:** N/A — there are no multi-document ACID transactions. Indexing is append/update of documents into the index; reads are search queries. Do not treat Coveo as transactional. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication / failover:** managed internally by Coveo on cloud infrastructure (AWS); not user-configurable. Single-leader/quorum mechanics are not exposed. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels; "freshness" is a function of source refresh schedules and real-time push.
- **Clock dependency:** none exposed to users. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read, effectively.** Sources are connected, content is mapped to **fields** in the indexing pipeline ("mappings"), and you define which fields are searchable/facetable/sortable. Flexible per-source field mapping rather than a rigid global schema.
- **Migration/evolution:** changing field configuration or mappings typically requires a source **rebuild/rescan** to reflect across already-indexed items; no online `ALTER`-style operation since there is no SQL schema.
- **Type system:** field types for text, numeric, date, and facet fields; document-level [full-text-search](../concepts/full-text-search.md) over body text; geospatial and rich types are not a first-class strength. Vector embeddings are generated internally from body text for semantic/RGA — you do not BYO arbitrary vectors as a primary interface (⚠️ unverified — limited public detail on user-supplied vector ingestion).

## Query interface
- **Language:** **API-only** — the Coveo Search API (REST) with a query syntax and the query-pipeline layer; no SQL, no general DSL you would use as a database. Indexing via crawlers/connectors, **Push API**, and **Stream API** ([indexing pipeline docs](https://docs.coveo.com/en/1893/)). A **query pipeline** of rules rewrites/optimizes queries before they hit the index ([query pipeline docs](https://docs.coveo.com/en/1450/)).
- **Transactions:** none — no multi-statement ACID; ingestion is document upsert/delete.
- **Native vs app-side:** native full-text matching, faceting, sorting, ML re-ranking, query suggestions, and recommendations; **no joins** in the relational sense. Aggregations are limited to search facets/counts, not analytical GROUP BY.
- **Stored procedures / UDFs:** **Indexing Pipeline Extensions (IPEs)** let you run custom **Python** scripts server-side during indexing to transform/enrich documents ([IPE API docs](https://docs.coveo.com/en/146/)). This is the closest analogue to a UDF.

## Scaling & topology
- **Vertical vs horizontal:** fully abstracted — Coveo runs and scales the index for you on its cloud. You do not provision nodes, shards, or replicas.
- **Sharding/partitioning:** managed internally; not exposed or your concern. No resharding pain because there is nothing to reshard by hand.
- **Read replicas / read consistency:** abstracted; the relevant consistency question is content freshness vs. the source system, not replica lag.
- **Storage/compute separation:** as a SaaS the user never sees the split; capacity is sold by **queries-per-month (QPM)** and index size, not by separable storage/compute knobs. See [storage-compute-separation](../concepts/storage-compute-separation.md) for the general pattern.

## Performance & durability
- **Write path:** "writes" are ingestion via crawl/Push/Stream into the indexing pipeline (crawl → extension stages → OCR → mapping → index). Durability of the index is Coveo's responsibility; the authoritative copy of your data remains in the source systems, so a data-loss window in Coveo is recoverable by re-indexing rather than catastrophic. See [wal-and-durability](../concepts/wal-and-durability.md) for the general durability concept (⚠️ unverified — Coveo does not publish index WAL/fsync internals).
- **Throughput/latency:** designed for low-latency user-facing search and commerce; specific p99 numbers are not publicly published and depend on plan/QPM tier (⚠️ unverified — no public, falsifiable latency SLOs found).
- **Compaction / GC:** index maintenance, merges, and re-ranking model retraining are handled by Coveo; not user-visible. ML models retrain on accumulated usage analytics.

## Operations & maturity
- **Backup/restore / PITR:** N/A in the DB sense — recovery is re-indexing from the always-authoritative source systems; there is no user-facing snapshot/PITR of the index.
- **Observability:** rich **Usage Analytics** (search/click events feeding ML), query-pipeline inspection and rule debugging ([inspect query pipeline docs](https://docs.coveo.com/en/mc2g0358/)), and admin console dashboards. No EXPLAIN-style plan, but query-pipeline tracing serves a similar diagnostic role.
- **Upgrade story:** zero — it is SaaS; Coveo upgrades the platform continuously with no customer downtime burden. Day-2 burden is content/connector configuration, relevance tuning, and security-identity maintenance, not infra ops.
- **Maturity:** mature commercial product (Coveo Solutions, publicly traded TSX:CVO), descended from the older on-prem **Coveo Enterprise Search (CES)** lineage and re-platformed as cloud SaaS; widely deployed in Salesforce/ServiceNow/Sitecore ecosystems. **No Jepsen report exists** (not applicable — it is not a distributed database with a consistency contract to verify).

## Ecosystem & people
- **Canonical use cases:** enterprise/workplace search over fragmented repositories, customer self-service and case-deflection in support portals, e-commerce product discovery and merchandising, and grounded GenAI answering (RGA) / RAG retrieval (**Passage Retrieval / CPR**, including an Amazon Bedrock integration — [AWS ML blog](https://aws.amazon.com/blogs/machine-learning/enhancing-llm-accuracy-with-coveo-passage-retrieval-on-amazon-bedrock/)).
- **Anti-patterns:** **wrong tool as a primary datastore, OLTP system, or analytics warehouse.** Do not pick Coveo if you want to self-host or avoid vendor lock-in, if you need transactional writes or SQL, if your scale is small (enterprise pricing/complexity), or if a self-managed search engine ([elasticsearch](elasticsearch.md), [opensearch](opensearch.md), [apache-solr](apache-solr.md)) or vector DB ([weaviate](weaviate.md), [qdrant](qdrant.md)) plus your own RAG stack would do — Coveo's value is the managed connectors + ML relevance + security trimming, not raw search you couldn't build.
- **Connectors/integrations:** 55+ prebuilt source connectors (Salesforce, ServiceNow, Sitecore, SharePoint, file/web crawlers), Push/Stream APIs, REST/GraphQL API sources, and front-end libraries (Atomic/Headless JS components). Deep Salesforce and Sitecore partnerships.
- **Community & docs:** docs.coveo.com is thorough; community is enterprise/partner-oriented (system integrators) rather than a large grassroots OSS community. Commercial support and professional services are central to the model.

## Licensing & cost
- **License:** **proprietary, closed-source, commercial SaaS** — no OSS edition, no source-available tier. See [license-taxonomy](../concepts/license-taxonomy.md). (The on-prem CES product is legacy; the platform today is cloud-only.)
- **Self-managed vs managed-only:** **managed-only.** You cannot run the engine yourself; strong vendor lock-in (proprietary index, ML models, connectors, and front-end framework).
- **Cost model:** **queries-per-month (QPM)** is the core metric — a query = a search-API request (search, facet interaction, next page, sort) ([Coveo pricing](https://www.coveo.com/en/pricing)). Plans (Service/Websites, Workplace, Commerce, Platform) are quote-based; entry around the low-hundreds/month with enterprise deals far higher, scaling by QPM tiers (e.g., 100k QPM base, add-on 100k blocks) plus content volume and ML features. At scale, costs are driven by query volume and feature mix; budgeting is hard because list pricing is not public (⚠️ unverified — exact tier prices are quote-gated).

## Hardware / deployment
- **Resource profile:** N/A to the user — Coveo owns the hardware. You do not size RAM/CPU/disk; the working-set/RAM question is internal to Coveo.
- **Storage assumptions:** internal; indexes are on encrypted cloud volumes ([content security docs](https://docs.coveo.com/en/1779/)).
- **Footprint:** **cloud SaaS only** (hosted on AWS; also offered via AWS Marketplace). No embedded, no on-prem cluster, no container you operate. **Security note:** Coveo crawlers use **early-binding** permission capture — item ACLs are pulled at crawl time and stored with the document so results are security-trimmed per user before queries run ([security identities docs](https://docs.coveo.com/en/1719/), [permission model](https://docs.coveo.com/en/25/)), with a security-identity cache to reflect current group memberships.
- **Deployment:** SaaS; integrate via APIs and JS front-end libraries. No StatefulSet/k8s concerns for you.

## Bottom line
Reach for Coveo if you are an enterprise (commonly already on Salesforce, ServiceNow, or Sitecore) that wants turnkey, security-trimmed search, recommendations, and grounded GenAI answers across many content silos **without operating any search infrastructure**, and you can absorb quote-based enterprise pricing and lock-in. Do not reach for it as a database, as a system-of-record, for OLTP/analytics, or if you need self-hosting, source availability, or fine cost predictability — a self-managed [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md)/[apache-solr](apache-solr.md) plus your own RAG would serve those better. The single biggest gotcha: it is a **proprietary, cloud-only, managed secondary index** — your data freshness is bounded by crawl/refresh cadence, there is no transactional or SQL surface, and you cannot run or export the engine.

## Sources
- [Coveo Platform overview](https://docs.coveo.com/en/3361/)
- [Indexing pipeline](https://docs.coveo.com/en/1893/) · [Query pipelines in the Search API](https://docs.coveo.com/en/1450/) · [Inspect your query pipeline](https://docs.coveo.com/en/mc2g0358/)
- [Indexing Pipeline Extension API](https://docs.coveo.com/en/146/)
- [Content security](https://docs.coveo.com/en/1779/) · [Security identities & permissions](https://docs.coveo.com/en/1719/) · [Complete permission model](https://docs.coveo.com/en/25/)
- [About Semantic Encoder](https://docs.coveo.com/en/nb6a0483/leverage-machine-learning/about-semantic-encoder-se) · [RGA model overview](https://docs.coveo.com/en/nb6a0390/)
- [Coveo Passage Retrieval on Amazon Bedrock (AWS ML blog)](https://aws.amazon.com/blogs/machine-learning/enhancing-llm-accuracy-with-coveo-passage-retrieval-on-amazon-bedrock/)
- [Coveo pricing](https://www.coveo.com/en/pricing) · [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-fvsorznffpqc2)
