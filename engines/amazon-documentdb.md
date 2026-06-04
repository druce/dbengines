---
name: Amazon DocumentDB
slug: amazon-documentdb
rank: 124
data_model: Document (MongoDB-compatible)
license: Proprietary / managed-only (AWS); emulates the Apache-2.0 MongoDB wire protocol
summary: AWS's proprietary, Aurora-style document database that speaks the MongoDB API but is a from-scratch engine — managed-only, with notable feature gaps versus real MongoDB.
last_researched: 2026-06-04
confidence: high
---

# Amazon DocumentDB

> A fully-managed AWS document store that emulates the MongoDB wire protocol on top of an Aurora-like distributed storage layer — pick it for MongoDB-API workloads you want AWS to operate, but only after checking the long list of unsupported MongoDB features.

## Identity
- **Taxonomy / data model:** [document-data-model](../concepts/document-data-model.md) (BSON/JSON documents in collections). Speaks the MongoDB 3.6 / 4.0 / 5.0 / 8.0 APIs and wire protocol ([AWS compatibility docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/compatibility.html)). It is **not** MongoDB code — AWS built a new engine that emulates the Apache-2.0 MongoDB API ([AWS DocumentDB FAQs](https://aws.amazon.com/documentdb/faqs/)).
- **Storage model:** compute is decoupled from a purpose-built distributed storage layer (the Aurora pattern — see [storage-compute-separation](../concepts/storage-compute-separation.md)). Storage is log-structured / redo-log-shipping: the primary writes a durable log to the cluster volume and ships *log records, not pages*, to replicas ([How it works](https://docs.aws.amazon.com/documentdb/latest/devguide/how-it-works.html)). Data is replicated 6 ways across 3 AZs. Underlying indexing is B-tree-style, not [LSM](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP document store. Not an analytics engine — no map-reduce, no `$out`-style materialized analytics pipelines in the MongoDB sense. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** CP within a region — a single-leader cluster that fails over rather than serving stale/conflicting writes (one writable primary at a time). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition, favors consistency (CP); else (normal operation) it offers a latency-vs-consistency knob via read preference — primary reads are read-after-write, replica reads trade latency for staleness ([replication docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/replication.html)).
- **Default isolation & what's achievable:** transactions (4.0+) run at **snapshot isolation** — DocumentDB always upgrades `readConcern` of local/available/majority up to `snapshot`, and rejects `linearizable` ([transactions docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html)). This is genuine snapshot isolation (MVCC, see [mvcc](../concepts/mvcc.md) and [isolation-levels](../concepts/isolation-levels.md)), not full serializable. Single-statement CRUD is atomic even across multiple documents. ⚠️ unverified — no published Jepsen analysis exists for DocumentDB, so snapshot-isolation correctness rests on AWS's own claims rather than independent verification.
- **Replication:** single-leader (one primary, up to 15 read replicas) with synchronous quorum at the storage layer; `writeConcern` is always forced to `majority` (4 of 6 copies across 3 AZs) and journaling cannot be disabled ([transactions docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html)). See [replication-models](../concepts/replication-models.md). Replicas are eventually consistent, typically <100 ms lag ([How it works](https://docs.aws.amazon.com/documentdb/latest/devguide/how-it-works.html)). Failover promotes a replica (you can set priority tiers); a write-then-read straddling a failover can briefly return non-strongly-consistent data ([best practices](https://docs.aws.amazon.com/documentdb/latest/developerguide/best_practices.html)).
- **Tunable consistency?** Via MongoDB read preference (primary vs secondary) and read/write concern, but concern levels are clamped (write→majority, read→snapshot). Effectively coarse-grained, not Dynamo-style per-query quorums.
- **Clock dependency:** no documented dependence on synchronized physical clocks for correctness (single-leader ordering). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** — flexible BSON documents, schema lives in app code. No schema-on-write enforcement.
- **Migration/evolution:** no rigid DDL to alter; collections and fields are dynamic. Index builds run online (background).
- **Type system:** BSON types (strings, numbers, dates, arrays, embedded docs, ObjectId, binary). Geospatial support is limited; **no native vector-search indexes, no text indexes, no time-series collections, no GridFS, no capped collections, no partial/case-insensitive indexes** ([functional differences](https://docs.aws.amazon.com/documentdb/latest/devguide/functional-differences.html)).

## Query interface
- **Language:** MongoDB Query Language (MQL) / aggregation pipeline over the MongoDB wire protocol. Use any MongoDB 4.0+ driver. No SQL.
- **Transactions:** multi-statement, multi-collection, multi-database ACID transactions in 4.0+ ([transactions docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html)). Hard limits: a transaction must complete within ~1 minute (session timeout 30 min), per-transaction log size <32 MB, **no cursors inside a transaction**, cannot create collections inside a transaction, document-level write lock has a non-configurable 1-minute timeout, retryable writes unsupported ([transactions docs](https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html)).
- **Native vs app-side:** native secondary indexes, aggregation pipeline (joins via `$lookup`), and server-side aggregation. No map-reduce. No stored procedures / server-side JavaScript (`$where`, `$function`, `mapReduce` unsupported).
- **Stored procedures / UDFs:** none — server-side JS execution is not supported.

## Scaling & topology
- **Vertical:** scale the primary/replica instance class up or down. Instance-based clusters scale reads by adding up to 15 replicas that all mount the same shared storage volume (no data copy on add). Serverless variant auto-scales compute (DCUs).
- **Horizontal sharding:** only via **elastic clusters**, which add hash-based sharding for millions of ops/sec and petabyte storage ([elastic clusters](https://docs.aws.amazon.com/documentdb/latest/developerguide/elastic-how-it-works.html)). Standard instance-based clusters do **not** shard — single-primary write ceiling. Resharding is a known pain point; choose the shard key carefully.
- **Read replicas:** yes, eventually consistent unless you pin read preference to primary.
- **Storage/compute separation:** yes — the defining architectural feature; storage auto-grows (up to 128 TiB on instance clusters) and a single-instance cluster is still durable because durability lives in the storage layer. See [storage-compute-separation](../concepts/storage-compute-separation.md).
- **Global Clusters:** cross-region async replication (sub-second target) for instance-based clusters; not available on elastic clusters.

## Performance & durability
- **Write path:** redo-log-based; the primary persists log records to the distributed storage volume and reaches a 4-of-6 write quorum before acknowledging. Journaling is mandatory. See [wal-and-durability](../concepts/wal-and-durability.md). **Data-loss window on crash:** effectively none for committed writes — durability is at the quorum storage layer; a single failed instance loses no acknowledged data.
- **Throughput/latency:** read scaling via replicas; replica lag usually <100 ms. Writes bottleneck on the single primary unless you use elastic clusters' sharding. ⚠️ unverified — AWS does not publish independent p99 benchmarks; tail latency depends heavily on IO-Optimized vs standard storage config and instance class.
- **Compaction / vacuum / GC:** storage GC is managed by AWS at the storage layer; no user-visible compaction tuning (unlike self-hosted MongoDB WiredTiger). This removes a class of operational toil but also removes a tuning lever.

## Operations & maturity
- **Backup/restore:** continuous backup to S3 with point-in-time restore (PITR) and on-demand snapshots; restore creates a new cluster.
- **Observability:** CloudWatch metrics, Performance Insights, slow-query logging, the `explain` command for query plans, and Profiler for slow ops.
- **Upgrade story:** managed major-version upgrades (e.g., 3.6→4.0→5.0); generally requires a maintenance action and can involve downtime/failover. Minor patches apply in maintenance windows. AWS announced *Extended Support* for the EOL 3.6 line ([AWS blog](https://aws.amazon.com/blogs/database/announcing-extended-support-for-amazon-documentdb-with-mongodb-compatibility-version-3-6/)).
- **Maturity:** GA since January 2019; mature managed service, but the engine is a re-implementation, so MongoDB feature parity lags (especially server-side JS, change-stream/aggregation edge cases, and newer Atlas-only features like vector/Atlas Search). **No public Jepsen report exists.** Biggest known failure mode: applications written against full MongoDB that hit an unsupported operator or index type.

## Ecosystem & people
- **Canonical use cases:** teams that want a MongoDB-API document store fully operated by AWS, tight IAM/VPC/KMS integration, and Aurora-style durability without running MongoDB themselves; content management, catalogs, user profiles, JSON-heavy OLTP.
- **Anti-patterns:** apps that rely on unsupported MongoDB features (text/vector search, GridFS, map-reduce, server-side JS, time-series, change-stream specifics); very high single-collection write throughput on non-elastic clusters; analytics/OLAP; teams wanting multi-cloud portability — DocumentDB is a lock-in to AWS. If you need true MongoDB feature breadth, prefer [mongodb](mongodb.md) / MongoDB Atlas.
- **Drivers/connectors:** standard MongoDB drivers (4.0+ for transactions); integrates with AWS DMS (migration/CDC), change streams (with limits), Glue, and BI tools via the Mongo connector. Connections require TLS and a VPC.
- **Community/support:** AWS commercial support; docs are solid for the AWS surface. Learning curve is low for MongoDB users — until they hit a compatibility gap.

## Licensing & cost
- **License/flavor:** **proprietary, managed-only AWS service.** It contains no MongoDB SSPL code; it emulates the Apache-2.0-licensed MongoDB API of older versions, which is precisely how AWS sidestepped MongoDB's 2018 SSPL relicensing ([The Register](https://www.theregister.com/2019/01/10/amazon_documentdb/), [Stratechery](https://stratechery.com/2019/aws-mongodb-and-the-economic-realities-of-open-source/)). See [license-taxonomy](../concepts/license-taxonomy.md). There is no self-hosted/OSS edition.
- **Self-managed vs managed-only:** managed-only. Lock-in is high (AWS-only, proprietary control plane).
- **Cost model:** instance-based = per-instance-hour + storage GB/month + per-million IOs (or IO-Optimized flat-rate storage tier); elastic clusters ≈ $0.132/vCPU-hour + $0.30/GB-month; serverless bills compute capacity units; Global Clusters add ~$0.20 per million replicated write IOs ([pricing](https://aws.amazon.com/documentdb/pricing/)). IO charges on standard config can dominate the bill at scale — the IO-Optimized config exists precisely because IO-heavy workloads invert the cheap-at-small economics.

## Hardware / deployment
- **Resource profile:** memory-bound for the working set (index + hot docs should fit the instance's RAM for good performance), IO-bound on writes; CPU scales with instance class.
- **Storage assumptions:** network-attached distributed storage (the cluster volume), not local NVMe — latency tolerance is engineered into the quorum design. Storage auto-grows.
- **Footprint:** clustered managed service only; no embedded/self-hosted option. Instance-based, elastic (sharded), or serverless deployment shapes.
- **Deployment:** SaaS-style AWS service inside your VPC; no on-prem, no k8s self-hosting. Multi-AZ by default at the storage layer.

## Bottom line
Reach for Amazon DocumentDB when you're committed to AWS, want a MongoDB-API document database that AWS fully operates with Aurora-grade durability (6-way/3-AZ storage, snapshot-isolation transactions), and your app stays within the supported MongoDB subset. Avoid it if you need full MongoDB feature parity (vector/text search, server-side JS, time-series, map-reduce), multi-cloud portability, or very high single-cluster write throughput without sharding. The single biggest gotcha: it is a *re-implementation*, not MongoDB — validate every operator, index type, and driver feature your app uses against the compatibility matrix before you migrate, and watch IO-based billing at scale.

## Sources
- [What is Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/what-is.html)
- [Amazon DocumentDB: how it works](https://docs.aws.amazon.com/documentdb/latest/devguide/how-it-works.html)
- [Transactions in Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html) (isolation/concern behavior)
- [MongoDB compatibility](https://docs.aws.amazon.com/documentdb/latest/developerguide/compatibility.html) and [functional differences](https://docs.aws.amazon.com/documentdb/latest/devguide/functional-differences.html)
- [High availability and replication](https://docs.aws.amazon.com/documentdb/latest/developerguide/replication.html)
- [Elastic clusters: how it works](https://docs.aws.amazon.com/documentdb/latest/developerguide/elastic-how-it-works.html)
- [Amazon DocumentDB FAQs](https://aws.amazon.com/documentdb/faqs/)
- [Pricing](https://aws.amazon.com/documentdb/pricing/)
- [The Register: Amazon launches DocumentDB](https://www.theregister.com/2019/01/10/amazon_documentdb/), [Stratechery: AWS, MongoDB and open source](https://stratechery.com/2019/aws-mongodb-and-the-economic-realities-of-open-source/) (licensing context)
