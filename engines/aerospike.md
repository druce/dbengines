---
name: Aerospike
slug: aerospike
rank: 77
data_model: Key-value (also: Document, multi-model)
license: AGPLv3 (Community Edition) / proprietary (Enterprise & Standard) — source-available core
summary: Hybrid-RAM-index/SSD key-value store built for sub-millisecond reads at huge scale, with opt-in linearizable strong consistency and (since 8.0) multi-record ACID.
last_researched: 2026-06-04
confidence: high
---

# Aerospike

> A flash-optimized distributed key-value store that keeps the index in RAM and data on NVMe, delivering predictable sub-millisecond latency at terabyte-to-petabyte scale — fast and operationally lean, but a poor fit for ad-hoc analytics or rich relational queries.

## When to use

**Use Aerospike if:**
- ✅ You have a large operational dataset (TB–PB) needing predictable sub-millisecond point reads/writes — user profiles, real-time bidding, fraud detection, feature/session stores
- ✅ You want SSD economics: only the index must fit in RAM while data lives on NVMe, far cheaper than all-RAM Redis
- ✅ You can opt into Strong Consistency mode for linearizable single-record (and, since 8.0, strict-serializable multi-record) transactions

**Avoid Aerospike if:**
- ❌ You need ad-hoc analytics, complex multi-table joins, heavy aggregation, full-text search, or rich SQL — there's no relational planner and no JOINs
- ❌ Your durability/consistency is left at defaults: without `commit-to-device` and SC mode you can lose recently-acked writes on crashes (the single biggest gotcha)
- ❌ You run SC deployments without controlling GC pauses and clock skew — Jepsen flagged residual data-loss risk under long process pauses / clock skew

## Identity
- **Taxonomy / data model:** primarily a distributed [key-value store](https://en.wikipedia.org/wiki/Aerospike_(database)); also document-oriented via Collection Data Types (maps/lists holding JSON-like structures). Records live in *sets* within *namespaces* (a namespace ≈ a database/tablespace). Multi-model in practice (KV + document), not relational/graph.
- **Storage model:** row-style records, not columnar. Signature design is **Hybrid Memory Architecture (HMA)**: the primary index is kept entirely in RAM (~64 bytes/record) and is *not* persisted, while record data sits on SSD/NVMe and is read directly from disk ([Aerospike docs: hybrid storage](https://docs.aerospike.com/server/architecture/storage.html)). On-disk format is log-structured — no in-place updates; **copy-on-write large-block writes** with background defragmentation to spread SSD wear (functionally [lsm-vs-btree](../concepts/lsm-vs-btree.md)-like log-structured, not a B-tree). Can also run all-in-memory or (newer) all-flash with index on SSD.
- **Workload:** OLTP / operational. Optimized for high-throughput point reads/writes and small batch queries. Not an analytics engine — no MPP scan engine, limited aggregation. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Does not meaningfully claim HTAP.

## Distribution & consistency
- **CAP under partition:** *configurable per namespace*. **AP mode** (default historically) stays available and reconciles; **SC (Strong Consistency) mode** chooses consistency and refuses writes that can't be safely committed ([Aerospike: consistency](https://docs.aerospike.com/server/architecture/consistency)). So it is CP or AP by configuration — see [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** SC mode = PC/EC (gives up availability under partition; favors consistency in normal operation, paying replication latency). AP mode = PA/EL (stays up, favors latency, reconciles later). See [cap-pacelc](../concepts/cap-pacelc.md).
- **Isolation / consistency level:** single-record operations in SC mode are **linearizable** (or session-consistent if configured) ([Aerospike SC](https://aerospike.com/products/features/strong-consistency/)). Since **8.0 (Feb 2025)** multi-record distributed transactions provide **strict serializability** per Aerospike ([Aerospike 8.0 transactions](https://aerospike.com/blog/aerospike8-transactions/)) — verify against your workload, as it carries notable overhead (below). Before 8.0 there was *no* multi-record ACID; "ACID" claims applied only to single records.
- **Replication:** synchronous master + replicas within a cluster (each record has an elected master at a point in time; writes are sequenced per record). Replication factor configurable (commonly 2). Cross-region is async via **XDR (Cross Datacenter Replication)**, supporting active-active topologies ([XDR docs](https://aerospike.com/docs/database/learn/architecture/xdr/)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes — per-namespace AP vs SC; read modes (e.g. linearize vs session) and write commit levels are tunable.
- **Clock dependency:** Aerospike uses internal regime/sequence numbers and a Lamport-style scheme rather than synchronized wall clocks for ordering, but Jepsen found wall clocks were used as tiebreakers on regime overflow, creating a clock-skew data-loss window (see Operations). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Namespaces and sets are largely schemaless; records are bags of typed *bins* (columns) defined by the application — no enforced table schema. Secondary indexes impose typing on indexed bins.
- **Migration/evolution:** adding/removing bins is a client-side concern, no table-rewrite DDL. Namespace-level config (replication, storage) is set at startup; some changes need rolling restarts. No locking `ALTER` because there's no rigid schema.
- **Type system:** integers, doubles, strings, blobs, booleans, **GeoJSON** geospatial, lists and maps (CDTs) for nested/document data, and HyperLogLog. Vector search is offered separately via **Aerospike Vector Search (AVS)**, a distinct product, not core bins.

## Query interface
- **Language:** primarily **API-only** key-value (get/put/operate) through native clients. **AQL** offers a SQL-like CLI for CRUD and secondary-index queries but is a tool/convenience layer, not a full SQL engine. There is also a Spark connector and a Presto/Trino connector for analytics offload.
- **Transactions:** single-record atomic operations always (multi-op on one record is atomic). **Multi-record ACID** added in 8.0; before that, none. Use sparingly — Aerospike advises judicious use alongside single-record workloads.
- **Native vs app-side:** secondary indexes are native (including on nested CDT/map elements since 6.x); queries can run with predicate filters and aggregations via **UDFs (Lua)**. **No joins** — relational joins are app-side. Aggregations are limited (stream UDFs, not a query planner).
- **Stored procedures / UDFs:** Lua UDFs (record-level and stream/aggregation).

## Scaling & topology
- **Horizontal, shared-nothing.** Data is auto-sharded into 4096 partitions per namespace, distributed across nodes by a deterministic hash (RIPEMD-160) — **no manual sharding, no hot-spot resharding pain**; adding/removing nodes triggers automatic, balanced data migration.
- **Read replicas / read consistency:** replicas are within-cluster; in SC mode reads from master are linearizable, replica reads are session-consistent depending on config. Cross-DC reads via XDR are eventually consistent.
- **Rack awareness:** records can be read from a local rack/AZ; 7.2 added `active-rack` to route synchronous writes and cut cross-AZ latency/egress.
- **Storage/compute separation:** No — compute and SSD storage are co-located per node (shared-nothing). Not a Snowflake/Aurora-style design. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** writes go to an in-memory write buffer then flushed to SSD in large blocks. By default a write is acked after replication in memory; **durability before ack requires `commit-to-device`** ([Jepsen](https://jepsen.io/analyses/aerospike-3-99-0-3)) — otherwise there is a **data-loss window** if all replicas crash before the buffer flushes. Enterprise adds the *durable write* / shadow-device options. See [wal-and-durability](../concepts/wal-and-durability.md). There is no traditional separate WAL; the log-structured device write *is* the durability mechanism.
- **Throughput/latency:** designed for sub-millisecond reads/writes and very high throughput (millions of ops/sec on modest clusters); predictable because index lookups never hit disk. p99 is generally tight, which is the core selling point.
- **Compaction/GC:** background **defragmentation** reclaims space from the log-structured store; configured via high/low water marks. Defrag and migrations can add I/O pressure and affect tail latency under heavy churn or near-full devices — keep headroom.

## Operations & maturity
- **Backup/restore:** `asbackup`/`asrestore` for full/incremental; Enterprise adds fast restore and other tooling. No built-in continuous PITR in the Postgres sense; XDR is often used for DR rather than point-in-time recovery.
- **Observability:** rich metrics (Prometheus exporter, `asadm`), latency histograms, log-based slow-op visibility. No cost-based EXPLAIN planner (limited query surface).
- **Upgrade story:** rolling upgrades supported; node-by-node restarts trigger migrations. Day-2 burden is moderate — capacity planning around RAM-for-index (a hard limit), SSD endurance, and defrag/migration tuning are the main concerns.
- **Maturity:** production-proven at scale in adtech, telco, fraud, and financial services. **Jepsen** (Dec 2017) tested the new SC mode on pre-release builds for 4.0 (versions 3.99.x): initial versions showed dirty reads after partitions, data loss on rapid node crashes (async-to-disk window), and **update loss under process pauses >27s / clock skew via regime tiebreaker overflow** ([Jepsen: Aerospike 3.99.0.3](https://jepsen.io/analyses/aerospike-3-99-0-3)). Aerospike fixed the proxy-retry dirty reads (3.99.1.5) and added `commit-to-device` (3.99.2.1); Jepsen concluded SC "does appear to provide linearizability through network partitions and process crashes, but data loss due to process pauses and clock skew remains." ⚠️ unverified — whether the process-pause/clock-skew loss has been fully closed in current 7.x/8.x releases; treat clock skew and long GC pauses as live risks in SC deployments.

## Ecosystem & people
- **Canonical use cases:** user profile stores, real-time bidding / adtech, recommendation and personalization, fraud detection, feature stores, session stores, and any "huge dataset, sub-ms point lookups, predictable cost" workload — especially where keeping everything in RAM (Redis-style) would be too expensive and SSD economics win.
- **Anti-patterns:** ad-hoc analytics / reporting, complex multi-table joins, heavy aggregation, strong relational integrity, or full-text search — wrong tool. Also a poor fit if you need rich SQL or if your team expects a relational planner. Heavy multi-record transactional workloads will pay real overhead.
- **Drivers / connectors:** official clients (Java, Go, Python, C#, C, Node.js, Rust, etc.), Spark connector, Trino/Presto connector, Kafka connect (inbound/outbound), Pulsar, and XDR for inter-cluster. dbt/BI integration is weak (not its niche).
- **Community / support:** commercial vendor (Aerospike, Inc.) with enterprise support; smaller community than Redis/Cassandra. Docs are solid. Learning curve: easy KV API, but storage/RAM/defrag capacity planning takes expertise.

## Licensing & cost
- **License:** Community Edition is **AGPLv3** (source-available copyleft — note network-use copyleft implications); Enterprise and Standard editions are **proprietary/closed-source**, requiring a feature-key file. Multi-record transactions, durable deletes, and admin commands are Enterprise-only ([editions](https://aerospike.com/products/features-and-editions/)). See [license-taxonomy](../concepts/license-taxonomy.md). ⚠️ unverified — exact AGPL-vs-proprietary boundary by feature can shift across releases; confirm against current edition matrix.
- **Self-managed vs managed:** self-managed on-prem/cloud, plus Aerospike Cloud (managed). AWS/GCP/Azure marketplace images exist.
- **Lock-in:** moderate — proprietary client protocol and Enterprise-only features (XDR, transactions, durable deletes); data is portable via backup tools.
- **Cost model:** Enterprise priced primarily by **unique data volume managed** (plus features) — explicitly **not** per-node or per-core. This inverts the usual scaling math: more servers/cores don't raise license cost, but large datasets do. Hardware cost is dominated by RAM (for the index) and NVMe.

## Hardware / deployment
- **Resource profile:** RAM-bound for the index (a fixed ~64 bytes/record/replica is a hard sizing constraint regardless of value size) and disk-bound for data; CPU is rarely the bottleneck. The *data* working set need not fit in RAM (its key differentiator vs. Redis), but the *index* must (unless all-flash mode).
- **Storage assumptions:** built for **local NVMe/SSD**; random and sequential SSD read latency parity is foundational to the design. Network-attached storage (EBS) undercuts the performance model and is discouraged for hot namespaces.
- **Footprint:** clustered, distributed (shared-nothing). Not embedded; not serverless in the core product (managed cloud aside). Minimum sensible deployment is a multi-node cluster (RF≥2).
- **Deployment:** on-prem and all major clouds; Kubernetes operator available (StatefulSets with local NVMe). Multi-site clustering and XDR for geo distribution.

## Bottom line
Reach for Aerospike when you have a large operational dataset and need predictable sub-millisecond point access at scale, want SSD economics rather than all-RAM cost, and your access pattern is key-value/document rather than relational or analytic. Don't reach for it for analytics, complex joins, full-text search, or as a general SQL database. The single biggest gotcha: durability and strong-consistency are **opt-in and config-sensitive** — without `commit-to-device` and SC mode you can lose recently-acked writes on crashes, and Jepsen flagged residual data-loss risk under long process pauses / clock skew, so SC deployments must control GC pauses and clock discipline.

## Sources
- [Aerospike docs — Hybrid storage / architecture](https://docs.aerospike.com/server/architecture/storage.html)
- [Aerospike docs — Consistency](https://docs.aerospike.com/server/architecture/consistency)
- [Aerospike — Strong Consistency feature](https://aerospike.com/products/features/strong-consistency/)
- [Jepsen: Aerospike 3.99.0.3](https://jepsen.io/analyses/aerospike-3-99-0-3)
- [Aerospike blog — Introducing ACID Transactions in Aerospike 8.0](https://aerospike.com/blog/aerospike8-transactions/)
- [Aerospike — XDR documentation](https://aerospike.com/docs/database/learn/architecture/xdr/)
- [Aerospike — Features and editions / pricing](https://aerospike.com/products/features-and-editions/)
- [Aerospike (database) — Wikipedia](https://en.wikipedia.org/wiki/Aerospike_(database))
