---
name: Rockset
slug: rockset
rank: 135
data_model: Document / multi-model (search + analytics)
license: Proprietary (managed-only SaaS) — service discontinued
summary: Real-time analytics SaaS that auto-indexed JSON every which way (row + column + inverted) on RocksDB-Cloud; acquired by OpenAI and shut down to outside customers in 2024.
last_researched: 2026-06-04
confidence: high
---

# Rockset

> A managed real-time indexing database that auto-built a row + columnar + inverted "Converged Index" over schemaless JSON so you could run low-latency SQL on fast-changing data — **now defunct: OpenAI acquired the team in June 2024 and shut the public service down (~30 Sep 2024).** ([OpenAI](https://openai.com/index/openai-acquires-rockset/), [The New Stack](https://thenewstack.io/rockset-users-stranded-by-openai-acquisition-now-what/))

## When to use

**Use Rockset if:**
- ✅ (Historically) you needed sub-second SQL — including joins and aggregations — on fast-changing schemaless JSON without managing indexes.
- ✅ (Historically) you wanted real-time operational dashboards, embedded analytics, or hybrid vector + text + metadata search via CDC ingest.

**Avoid Rockset if:**
- ❌ You are building anything new — the service is **defunct**: OpenAI acquired the team in June 2024 and shut the public service down (~30 Sep 2024), and it was never open source, so there is no self-hosted fallback.
- ❌ You need transactional/OLTP workloads, large full-table scans, or global sorts — it indexed for selective access, not full-table scans.
- ❌ You are cost-sensitive at large scale — indexing every field made storage cost grow faster than raw data size.

## Identity
- **Taxonomy / data model:** document store with a "relational document model" — semi-structured JSON documents grouped into collections (≈ tables) inside workspaces, queried with SQL. Effectively multi-model: it served document, search, and analytical access from one index. ([InfoWorld review](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))
- **Storage model:** hybrid. Its signature **Converged Index** indexes every field of every document three ways at once — an inverted (search) index, a columnar index, and a row/document index — all stored as key-value pairs in [RocksDB-Cloud](https://rockset.com/blog/how-we-use-rocksdb-at-rockset/), an [LSM](../concepts/lsm-vs-btree.md)-tree engine. LSM (not B-tree) was chosen so that indexing many fields stays write-cheap; storage uses delta-encoding between keys, Zstandard dictionary compression, and bloom filters. ([Converged Index](https://medium.com/rocksetcloud/how-rocksets-converged-index-powers-real-time-analytics-c6c2e6066d9e))
- **Workload:** real-time analytics / serving ([OLAP-leaning, serving-tier](../concepts/oltp-olap-htap.md)). Explicitly **not OLTP** — "by eliminating transactions and making most writes asynchronous and non-blocking" it could index any field cheaply, and the company stated it had no plans to do transaction processing. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))

## Distribution & consistency
- **CAP under partition:** N/A as a user-facing knob — it was a managed cloud service on object storage, not a quorum DB you operated. Internally durability rested on cloud object storage (S3/GCS) with a hot SSD tier; see [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** not a tunable. The design optimized for read freshness on a single authoritative copy backed by object storage rather than offering consistency-vs-latency knobs.
- **Default isolation & what's achievable:** no transactions. There is **no multi-statement ACID and no isolation level to speak of** — writes are asynchronous, idempotent upserts keyed by `_id`. ⚠️ unverified — the precise read-consistency contract (e.g. monotonic reads across virtual instances) was not pinned down in available primary docs beyond "data freshness guaranteed across virtual instances." See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** managed internally; durability via cloud object storage rather than user-configured leader/quorum [replication](../concepts/replication-models.md). Compute-compute separation let multiple virtual instances read the same datasets. ([Compute-compute separation](https://rockset.com/blog/tech-overview-compute-compute-separation/))
- **Tunable consistency:** ingest was asynchronous with a **sub-second target**; new data was queryable at a p95 of ~2 seconds. Optional **commit markers** could block a query until a specific write had been indexed, giving read-your-writes for special cases. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))
- **Clock dependency:** none material; see [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Ingest was fully schemaless — raw JSON went in untouched. "Smart Schema" then inferred field types **per value, not per column** ("strong dynamic typing"): a ZIP field could be string in one doc, int in another, missing in a third. SQL queries saw the inferred schema at read time. ([Smart Schema](https://medium.com/rocksetcloud/from-schemaless-ingest-to-smart-schema-enabling-sql-on-raw-data-2fbecb9bbd3e))
- **Migration/evolution:** trivially flexible — adding/removing fields needed no DDL or table lock; new fields were auto-indexed on ingest. The cost was paying for indexing every field.
- **Type system:** JSON/semi-structured natives (nested objects, arrays), plus geospatial; ingest accepted JSON, Parquet, XML, CSV/TSV. Vector search was added later: native vector embeddings/ANN search launched April 2023, and a dedicated **hybrid search** feature (combining vector + text + metadata filtering in one SQL query) landed May 2024 — just weeks before the acquisition, and a primary reason OpenAI bought the team for its retrieval infrastructure. ([Vector search](https://rockset.com/press/rockset-adds-vector-search-for-real-time-machine-learning-at-scale/), [Hybrid search](https://rockset.com/press/rockset-hybrid-search/))

## Query interface
- **Language:** full **SQL** with extensions for `UNNEST` over arrays and JSON-path access into nested fields. Reusable parameterized queries could be published as named REST endpoints called **Query Lambdas**.
- **Transactions:** none — single-document upserts only; no multi-statement atomicity.
- **Native vs app-side:** native secondary indexes (everything is indexed), native joins, aggregations, and window functions executed server-side across collections. Joins and aggregations were a differentiator vs. typical search/serving stores.
- **Stored procedures / UDFs:** ⚠️ unverified — no general stored-procedure/UDF language found; Query Lambdas served the "saved logic" role.

## Scaling & topology
- **Vertical vs horizontal:** horizontal, but fully managed — you chose a **Virtual Instance** size (compute+memory allocation), not nodes. Sharding/partitioning of the index was automatic and invisible.
- **Read replicas / read consistency:** **compute-compute separation** let you spin up independent virtual instances over the same shared data so ingest compute and query compute (and multiple query workloads) scaled independently, "guaranteeing data freshness across all virtual instances." ([Compute-compute separation](https://rockset.com/blog/tech-overview-compute-compute-separation/))
- **Storage/compute separation:** yes, a core design point — a shared **hot storage layer** of SSD-backed storage nodes plus durable cloud object storage, decoupled from compute via RocksDB-Cloud, so VIs could be resized instantly with no data movement. See [storage-compute-separation](../concepts/storage-compute-separation.md). Architecturally this follows the **Aggregator-Leaf-Tailer (ALT)** pattern: Tailers ingest, Leaves index, Aggregators run queries — separating write compute, read compute, and storage. ([Separate compute & storage](https://rockset.com/blog/separate-compute-storage-rocksdb/), [ALT](https://medium.com/rocksetcloud/aggregator-leaf-tailer-an-alternative-to-lambda-architecture-for-real-time-analytics-8b1827a6c9fd))

## Performance & durability
- **Write path:** asynchronous, non-blocking, idempotent upserts into an LSM index; durability backed by cloud object storage. Because writes are async, the "data-loss window" question is about the managed pipeline rather than a user fsync policy; see [wal-and-durability](../concepts/wal-and-durability.md). Ingest-to-queryable latency target sub-second, p95 ~2s. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))
- **Throughput/latency:** designed for low-latency, high-concurrency point and selective analytical queries (filters, lookups, aggregations) over fresh data — the indexing makes selective queries fast without scans.
- **Compaction/GC:** RocksDB LSM compaction underneath. **Anti-pattern that hurts tail latency:** queries requiring a global sort or full scan of a large dataset force full table scans and heavy RAM use — Rockset is built for selective indexed access, not full-table OLAP scans. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))

## Operations & maturity
- **Backup/restore / PITR:** managed by the service; not a user-operated concern. No self-hosted snapshot story (managed-only).
- **Observability:** SQL query profiles/plans, console metrics, query performance views (managed dashboards).
- **Upgrade story:** zero — fully managed SaaS, no version to roll.
- **Maturity:** ~7 years in production with customers including Walmart, Cisco, Klarna, and AthenaHealth ([Stacksync](https://www.stacksync.com/blog/acquired-by-openai-the-origin-story-of-rockset)). **No public Jepsen report exists.** Its defining "failure mode" is existential: **OpenAI acquired Rockset in June 2024 and discontinued the standalone service (target shutdown ~30 Sep 2024), stranding customers with a months-long migration window.** ([OpenAI](https://openai.com/index/openai-acquires-rockset/), [The New Stack](https://thenewstack.io/rockset-users-stranded-by-openai-acquisition-now-what/))

## Ecosystem & people
- **Canonical use cases:** real-time operational dashboards, embedded/customer-facing analytics, personalization, search+analytics over fast-changing JSON, IoT, 360° customer views — anywhere you needed sub-second SQL on streaming data without managing indexes. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html))
- **Anti-patterns:** transactional/OLTP workloads; large full-table scans or global sorts (no index helps); cost-sensitive workloads with huge datasets (index-everything blows up storage); and — decisively today — any new build, since the service is gone.
- **Connectors:** strong real-time CDC ingest from Amazon DynamoDB, MongoDB, Apache Kafka/Kinesis, plus batch from S3, GCS, and Redshift, and a Write API. BI/app integration via SQL and Query Lambda REST endpoints.
- **Community / support / docs:** docs were well regarded; community modest; commercial support was the vendor only (now defunct).

## Licensing & cost
- **License:** **proprietary, managed-only SaaS** — never open source, no self-hosted option, so inherent vendor lock-in. See [license-taxonomy](../concepts/license-taxonomy.md). (No post-2018 OSS relicensing applies — it was never OSS.)
- **Self-managed vs managed-only:** managed-only; you could not run it yourself, which made the shutdown unrecoverable for users.
- **Cost model:** **per-GB of active data plus compute (virtual instance) hours** — roughly $6/GB/mo (Basic) to $9/GB/mo (Pro) for storage tiers, free up to ~2 GB. ⚠️ unverified — exact pricing varied over time and is moot post-shutdown. ([InfoWorld](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html)) Index-everything meant storage cost grew faster than raw data size — cheap at small scale, expensive at large.

## Hardware / deployment
- **Resource profile:** memory- and SSD-bound for low-latency serving; the hot tier is SSD-backed, with cold data on object storage.
- **Storage assumptions:** cloud-native — SSD hot tier over network-attached cloud object storage (S3/GCS) via RocksDB-Cloud.
- **Footprint:** **serverless/SaaS only** (multi-tenant or dedicated virtual instances). No embedded, on-prem, or single-node deployment.
- **Deployment:** vendor-hosted cloud (AWS/GCP). No k8s/StatefulSet story for users — it was a black-box service.

## Bottom line
Rockset was a genuinely clever piece of engineering — schemaless ingest plus a Converged Index (row + column + inverted) on RocksDB-Cloud with true storage/compute and compute-compute separation, giving sub-second SQL on fast-moving JSON without index tuning. **Nobody should reach for it now: OpenAI acquired the team in June 2024 and shut the public service down, and it was never open source, so there is no self-hosted fallback.** If you liked its profile, look at [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md), [clickhouse](clickhouse.md), [apache-pinot](apache-pinot.md), [apache-druid](apache-druid.md), [singlestore](singlestore.md), or tinybird. The single biggest gotcha is the obvious one — building on a proprietary managed-only database that can vanish in an acquisition.

## Sources
- [OpenAI — OpenAI acquires Rockset](https://openai.com/index/openai-acquires-rockset/)
- [The New Stack — Rockset Users Stranded by OpenAI Acquisition: Now What?](https://thenewstack.io/rockset-users-stranded-by-openai-acquisition-now-what/)
- [InfoWorld — Rockset review: Real-time SQL for operational data](https://www.infoworld.com/article/2263499/rockset-review-real-time-sql-for-operational-data.html)
- [Rockset — How the Converged Index Powers Real-Time Analytics](https://medium.com/rocksetcloud/how-rocksets-converged-index-powers-real-time-analytics-c6c2e6066d9e)
- [Rockset — How We Use RocksDB at Rockset](https://rockset.com/blog/how-we-use-rocksdb-at-rockset/)
- [Rockset — Tech Overview of Compute-Compute Separation](https://rockset.com/blog/tech-overview-compute-compute-separation/)
- [Rockset — How Rockset Separates Compute and Storage Using RocksDB](https://rockset.com/blog/separate-compute-storage-rocksdb/)
- [Dhruba Borthakur — Aggregator Leaf Tailer architecture](https://medium.com/rocksetcloud/aggregator-leaf-tailer-an-alternative-to-lambda-architecture-for-real-time-analytics-8b1827a6c9fd)
- [Rockset — From Schemaless Ingest to Smart Schema](https://medium.com/rocksetcloud/from-schemaless-ingest-to-smart-schema-enabling-sql-on-raw-data-2fbecb9bbd3e)
- [Stacksync — Acquired by OpenAI: The Origin Story of Rockset](https://www.stacksync.com/blog/acquired-by-openai-the-origin-story-of-rockset)
