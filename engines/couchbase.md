---
name: Couchbase
slug: couchbase
rank: 43
data_model: Document (multi-model — also KV, full-text search, vector, analytics)
license: Business Source License 1.1 (source-available; converts to Apache 2.0 after 4 years)
summary: Memcached-rooted distributed JSON document store with a SQL++ query layer, integrated KV/search/analytics/vector services, and a memory-first write path; strong single-node consistency, weaker cross-datacenter (LWW) guarantees.
last_researched: 2026-06-04
confidence: high
---

# Couchbase

> A memory-first distributed document database that grew out of memcached + CouchDB: fast KV with a SQL++ (N1QL) query layer and multiple co-located services, durable and strongly consistent on a single cluster but LWW/clock-dependent across datacenters.

## Identity
- **Taxonomy / data model:** Multi-model. Primary model is JSON **document**; also a native **key-value** store (memcached lineage), **full-text search** ([full-text-search](../concepts/full-text-search.md)), **vector search** ([vector-search-ann](../concepts/vector-search-ann.md)), and a columnar **Analytics** service. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Per-bucket pluggable storage. Default **Couchstore** is a **copy-on-write (append-only) B-tree** ([Storage engines docs](https://docs.couchbase.com/server/current/learn/buckets-memory-and-storage/storage-engines.html); [lsm-vs-btree](../concepts/lsm-vs-btree.md)); **Magma** (introduced 7.1) is an LSM-tree + log-structured value-separation engine for datasets larger than RAM ([Magma paper, VLDB 2022](https://www.vldb.org/pvldb/vol15/p3496-lakshman.pdf)). KV operations are served from an in-memory managed cache; documents are written to memory first, then persisted asynchronously by default. On-disk format is append-only with background compaction.
- **Workload:** OLTP/KV-centric. The separate **Analytics** service provides columnar OLAP over the same data (shadow copies kept in sync via the internal DCP stream), giving an HTAP-ish split where the **physical separation is real**: analytics runs on its own nodes/columnar store fed by a change-data stream, not on the OLTP indexes. ([Multi-Dimensional Scaling](https://www.couchbase.com/multi-dimensional-scalability-overview/))

## Distribution & consistency
- **CAP under partition:** Within a single cluster, **CP-leaning** — the active node (single owner per vBucket) serves reads/writes; durable writes wait for replica acknowledgment. Across datacenters via XDCR it is **AP** with last-write-wins reconciliation. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Single cluster ≈ **PC/EC**-ish for durable writes (waits for majority before acknowledging). Default async-persisted writes trade durability for latency (**EL** flavor). XDCR is **PA/EL** — availability and latency over cross-cluster consistency.
- **Default isolation & what's achievable:** KV ops give per-document atomicity with **MVCC via CAS** (compare-and-swap) for optimistic concurrency. Multi-document **ACID transactions** exist (SDK transactions since 6.5; N1QL/SQL++ transactions since 7.0) at **READ COMMITTED** isolation — and READ COMMITTED is the *only* isolation level offered (it is also the default); transactional reads are actually stricter than plain RC, providing Monotonic Atomic View (MAV) ([SQL++ transactions docs](https://docs.couchbase.com/cloud/n1ql/n1ql-language-reference/transactions.html), [SET TRANSACTION docs](https://docs.couchbase.com/cloud/n1ql/n1ql-language-reference/set-transaction.html)). No snapshot or serializable isolation is offered; "ACID" here means READ COMMITTED multi-document transactions, not snapshot/serializable. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Intra-cluster is **single-leader per vBucket** (one active, configurable replicas), in-memory via DCP. **Durable Writes** (≥6.5) let a write block until `durabilityLevel` is met: `majority`, `majorityAndPersistActive`, or `persistToMajority` ([Durability docs](https://docs.couchbase.com/cxx-sdk/current/concept-docs/data-durability-acid-transactions.html)). Failover (auto or manual) promotes a replica vBucket to active. Split-brain is mitigated by quorum-based auto-failover. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes on two axes: per-write `durabilityLevel`, and per-query **scan consistency** for the Query/Index services (`not_bounded` = stale-OK fast reads; `request_plus` = read-your-writes, waits for the index to catch up to the mutation).
- **Clock dependency:** Single-cluster correctness does **not** require synchronized clocks. **XDCR timestamp-based (LWW) conflict resolution does** — it compares CAS timestamps and silently discards the "older" write, so NTP skew can cause data loss/incorrect winners ([XDCR conflict resolution docs](https://docs.couchbase.com/server/current/learn/clusters-and-availability/xdcr-conflict-resolution.html)). Newer versions add Hybrid Logical Vector (HLV) metadata for cross-cluster versioning. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Buckets hold schemaless JSON documents; structure lives in application code. Logical grouping via **scopes** and **collections** (since 7.0) gives a namespace hierarchy roughly analogous to schema/table.
- **Migration/evolution:** No table-level DDL locking — documents evolve freely. Index changes (GSI) are online; building a new index does not block writes.
- **Type system:** JSON types (objects, arrays, numbers, strings, booleans, null). Native **geospatial** and **vector** indexing via the Search service; full-text indexes; sub-document API for partial reads/writes without fetching the whole doc.

## Query interface
- **Language:** **SQL++** (formerly N1QL) — a JSON-aware superset of SQL with nesting/unnesting, plus a KV get/put/CAS API, FTS query DSL, and Analytics SQL++. Multiple access paths to the same data.
- **Transactions:** Multi-document, multi-collection, multi-statement **ACID** at READ COMMITTED (SDK 6.5+, SQL++ 7.0+). Single-document ops are atomic with CAS.
- **Native vs app-side:** Native secondary indexes (**GSI** — Global Secondary Indexes), ANSI **joins** across documents, aggregations, and window functions in SQL++. Joins/indexes are first-class, not app-side.
- **Stored procedures / UDFs:** User-defined functions in **JavaScript** and inline SQL++. **Eventing** service runs JavaScript functions on data-change triggers.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal scale-out is the design center. **Multi-Dimensional Scaling (MDS)** lets each service (Data/KV, Index, Query, Search, Analytics, Eventing) scale on independent node pools, isolating workloads ([MDS overview](https://www.couchbase.com/multi-dimensional-scalability-overview/)).
- **Sharding:** Automatic via **1024 vBuckets** per bucket, hash-partitioned across data nodes. Rebalance redistributes vBuckets when nodes are added/removed — online but I/O-heavy. The vBucket count is fixed at 1024, so very small or very large clusters can have uneven distribution.
- **Read replicas:** Replica vBuckets are normally passive (failover targets). Apps can opt into reading from replicas (`getAnyReplica`), which returns **possibly stale** data.
- **Storage/compute separation:** Largely shared-nothing (compute co-located with local storage). The Analytics/columnar tier separates analytical compute from operational data. **Capella Columnar** and Capella push further toward managed separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Mutation lands in the in-memory cache on the active node, then flows to (a) replicas via DCP and (b) disk via the persistence queue. **Default acknowledgment is in-memory only** — a crash before persistence/replication loses the write; the **data-loss window** is whatever is still queued. `durabilityLevel` closes this by waiting for majority-memory and/or disk persistence before ack. See [wal-and-durability](../concepts/wal-and-durability.md). Note Couchbase has no classic separate WAL: durability comes from the append-only storage engine's own commit plus the in-memory replication (DCP) and persistence queues.
- **Throughput/latency:** Sub-millisecond KV reads/writes from cache are the headline strength. p99 degrades when the working set exceeds RAM (cache misses → disk fetches) and during rebalance/compaction. Magma improves large-dataset (RAM-overcommitted) behavior.
- **Compaction / GC:** Append-only Couchstore files require **background compaction** to reclaim space; this competes for disk I/O and can spike p99. Magma uses LSM-style compaction with different tradeoffs.

## Operations & maturity
- **Backup/restore:** `cbbackupmgr` for full/incremental backup; PITR-style incrementals; cluster-consistent snapshots. XDCR can also serve DR.
- **Observability:** Built-in admin UI, Prometheus-compatible metrics, per-query plans (`EXPLAIN`), slow-query logging, and cluster/vBucket health views.
- **Upgrade story:** Rolling upgrades via swap-rebalance / node-by-node; generally no full-cluster downtime, but rebalances are heavy and require spare capacity.
- **Maturity:** Mature (Couchbase Server lineage since ~2011; memcached/CouchDB roots older). Known failure modes: cache-miss latency cliffs when working set > RAM, rebalance-induced latency, and **XDCR LWW silently dropping writes** under clock skew. **Jepsen:** Couchbase runs Jepsen **in-house** ([couchbaselabs/jepsen.couchbase](https://github.com/couchbaselabs/jepsen.couchbase), [intro blog](https://www.couchbase.com/blog/introduction-to-jepsen-testing-at-couchbase/)) testing that durable writes are not lost and at least sequential consistency holds under failures. ⚠️ unverified — there is **no independent Aphyr/jepsen.io published analysis** of Couchbase; the testing is vendor-run, so treat the consistency claims accordingly.

## Ecosystem & people
- **Canonical use cases:** Low-latency caching+system-of-record (caching layer and durable store in one), user profiles/sessions, product catalogs, real-time personalization, mobile/edge sync via **Couchbase Lite + Sync Gateway / Capella App Services**.
- **Anti-patterns:** Heavy relational/normalized workloads needing serializable isolation; complex multi-table OLAP as the primary use (use a real warehouse); workloads where the working set vastly exceeds RAM budget without Magma planning; strong cross-region consistency (XDCR is LWW, not consensus).
- **Drivers/connectors:** First-party SDKs (Java, .NET, Go, Node, Python, C, etc.), Spring Data, Kafka connector (source/sink via DCP), Spark connector, Elasticsearch connector, CDC via DCP. ⚠️ unverified — official dbt support is limited.
- **Community/support:** Commercial vendor (Couchbase, Inc., NASDAQ: BASE) with enterprise support; solid docs; moderate community. Learning curve: KV is easy, but tuning MDS, indexing, durability levels, and rebalance is a real day-2 skill.

## Licensing & cost
- **OSS license & flavor:** **Source-available, not OSS.** Couchbase relicensed from Apache 2.0 to **Business Source License 1.1 (BSL)** ([BSL adoption blog](https://www.couchbase.com/blog/couchbase-adopts-bsl-license/)); source converts to Apache 2.0 after a **4-year** change date. The **Community Edition** binary is free but license-restricted to **departmental-scale** deployments (no unlimited-size clusters, lagging features) ([CE license change](https://www.couchbase.com/blog/couchbase-modifies-license-free-community-edition-package/)). Enterprise Edition is subscription-licensed. See [license-taxonomy](../concepts/license-taxonomy.md). This is a post-2018 relicensing pattern (BSL, like CockroachDB/MariaDB MaxScale).
- **Self-managed vs managed:** Both. Self-managed Server (EE/CE), or **Capella** DBaaS (managed, on AWS/GCP/Azure).
- **Lock-in:** SQL++ and the multi-service architecture are Couchbase-specific; XDCR/Eventing/App Services deepen lock-in. Capella adds managed-service lock-in.
- **Cost model:** EE is subscription (typically per-node/core); Capella is consumption/credit-based by instance size and storage. Cheap-at-small can invert at scale because RAM is the binding resource and EE node counts drive cost.

## Hardware / deployment
- **Resource profile:** **Memory-bound** by design — KV performance depends on the working set (or at least the metadata/hot set) fitting in the managed cache. Magma relaxes the "all data in RAM" assumption but raises disk I/O importance.
- **Storage assumptions:** Favors **local SSD/NVMe**; append-only writes + compaction make fast local disk preferable to high-latency network storage.
- **Footprint:** **Clustered** (multi-node) for Server; **embedded** for Couchbase Lite (mobile/edge); **serverless/managed** via Capella.
- **Deployment:** SaaS (Capella) or on-prem/self-managed. Official **Kubernetes Autonomous Operator** handles StatefulSet realities (rebalance, failover, upgrades) on k8s.

## Bottom line
Reach for Couchbase when you want **memcached-class KV latency plus a SQL++ query/search/analytics layer in one clustered system**, especially for caching-as-system-of-record, user/session data, catalogs, and mobile-sync apps. Avoid it for serializable relational workloads, primary heavy-OLAP, or when you need consensus-grade cross-region consistency. The single biggest gotcha: writes are **acknowledged from memory by default** (set `durabilityLevel` or risk a data-loss window), and **XDCR conflict resolution is last-write-wins on clock timestamps** — clock skew can silently drop writes across datacenters.

## Sources
- [Couchbase Multi-Dimensional Scaling overview](https://www.couchbase.com/multi-dimensional-scalability-overview/)
- [Couchbase Durability & ACID transactions docs](https://docs.couchbase.com/cxx-sdk/current/concept-docs/data-durability-acid-transactions.html)
- [Durability & failure considerations (C SDK)](https://docs.couchbase.com/c-sdk/current/concept-docs/durability-replication-failure-considerations.html)
- [N1QL/SQL++ transactions (READ COMMITTED)](https://www.couchbase.com/blog/couchbase-transactions-with-n1ql/)
- [XDCR conflict resolution (LWW / timestamp / HLV)](https://docs.couchbase.com/server/current/learn/clusters-and-availability/xdcr-conflict-resolution.html)
- [Introduction to Jepsen testing at Couchbase (vendor-run)](https://www.couchbase.com/blog/introduction-to-jepsen-testing-at-couchbase/)
- [couchbaselabs/jepsen.couchbase](https://github.com/couchbaselabs/jepsen.couchbase)
- [Couchbase adopts BSL 1.1](https://www.couchbase.com/blog/couchbase-adopts-bsl-license/)
- [Couchbase modifies Community Edition license](https://www.couchbase.com/blog/couchbase-modifies-license-free-community-edition-package/)
- [QuABaseBD: Couchbase consistency features](https://quabase.sei.cmu.edu/mediawiki/index.php/Couchbase_Consistency_Features)
