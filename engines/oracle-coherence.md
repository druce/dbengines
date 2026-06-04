---
name: Oracle Coherence
slug: oracle-coherence
rank: 145
data_model: Key-value (in-memory data grid)
license: Community Edition under Universal Permissive License 1.0 (permissive); Enterprise/Grid editions proprietary
summary: Java in-memory data grid that partitions a key-value namespace across a peer-to-peer cluster with synchronous backups; a cache/compute layer, not a system of record.
last_researched: 2026-06-04
confidence: medium
---

# Oracle Coherence

> A Java distributed in-memory data grid that auto-partitions a key-value space across a cluster with one synchronous backup per partition for HA — fast and consistent for single-key ops, but it is a caching/compute tier, not a durable database of record.

## When to use

**Use Oracle Coherence if:**
- ✅ You need a low-latency, horizontally scalable Java caching/compute grid in front of a system of record (read-through/write-behind)
- ✅ You want data-local compute via entry processors (atomic single-key read-modify-write on the data member), HTTP session replication, or reference-data grids
- ✅ You want automatic hash partitioning with auto-rebalancing on membership change, ideally on Kubernetes via the Coherence Operator

**Avoid Oracle Coherence if:**
- ❌ You treat it as your durable database — it is a **cache first**: without persistence enabled, a full-cluster restart loses everything
- ❌ You need database-wide multi-key ACID by default (only opt-in via the Transaction Framework; otherwise per-entry atomicity only)
- ❌ You run analytics/OLAP or relational/joins-heavy workloads, or datasets too large to keep in JVM heap
- ❌ Your team can't operate large JVM clusters — GC pauses are the primary p99 tail risk

## Identity
- **Taxonomy / data model:** Key-value store exposed as a Java `Map`/`NamedCache`, distributed as an in-memory data grid (IMDG). Values are typically serialized Java objects (POF — Portable Object Format — or Java serialization). Not relational. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Primarily in-memory (on-heap or off-heap/journal). Data is hash-partitioned across cluster members; each partition has a configurable number of synchronous backup copies (default 1) on other members. Optional disk persistence ([wal-and-durability](../concepts/wal-and-durability.md)) and elastic-data "flash/RAM journal" tiers extend capacity beyond heap. Not LSM/B-tree; it is a partition map of serialized entries, so the [lsm-vs-btree](../concepts/lsm-vs-btree.md) distinction does not apply at the storage core.
- **Workload:** OLTP-style low-latency key-value access and server-side compute (entry processors, aggregators). Not an analytics engine; parallel aggregations exist but it is not a columnar OLAP system. Best described as a caching/compute grid in front of a system of record.

## Distribution & consistency
- **CAP under partition:** Effectively **CP for the primary partitioned cache** within a single cluster — Coherence is a single-cluster, partition-aware grid that keeps a primary and synchronous backups consistent and relies on cluster membership (a TCMP "death detection"/quorum mechanism) to evict unreachable members rather than serve divergent copies ([Oracle: clustering/TCMP](https://docs.oracle.com/en/middleware/standalone/coherence/14.1.1.0/develop-applications/introduction-coherence-caches.html)). ⚠️ unverified — there is no Jepsen report or formal CAP classification from Oracle; this is inferred from the synchronous-backup + membership design.
- **PACELC:** ⚠️ unverified — not formally published. In practice, within a cluster it favors consistency (synchronous backup on write); **cross-cluster federation is explicitly asynchronous and eventually consistent** ([Oracle: Federating Caches Across Clusters](https://docs.oracle.com/middleware/1221/coherence/administer/replication.htm)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** Single-entry operations are atomic. There is **no general multi-key ACID transaction by default.** Cross-partition/cross-cache ACID is only available via the separate **Transaction Framework API** (read consistency + atomic commit across partitions, with its own concurrency and recovery manager) ([Oracle: Performing Transactions](https://docs.oracle.com/middleware/1221/coherence/develop-applications/api_transactionslocks.htm)). Most application code instead uses **entry processors**, which give atomic, lock-free read-modify-write on a single key executed on the primary member. So an "ACID/transactional integrity" claim really means: per-entry atomicity plus an opt-in transaction API, not database-wide serializable transactions. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Within a cluster, **synchronous backup** — a write to the primary is replicated to N backup members before acknowledging (no async lag on the hot path). Across clusters, **federated caching** is asynchronous multi-directional replication (active-active, active-passive, or custom topologies), i.e. eventually consistent. Conflicts between concurrent updates of the same entry are resolved by application-supplied **interceptors on federation change events** (`COMMITTING_LOCAL`/`COMMITTING_REMOTE`), not a fixed built-in policy — there is no default automatic last-writer-wins; you write the resolution logic ([Oracle: Federating Caches Across Clusters](https://docs.oracle.com/middleware/1221/coherence/administer/replication.htm)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited. Backup count and read-from-backup are configurable; there is no Dynamo-style per-query R/W quorum knob.
- **Clock dependency:** No TrueTime/HLC requirement for single-cluster correctness. Federation conflict resolution is whatever the application's interceptors implement (which may consult timestamps), not a clock-dependent built-in. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Values are opaque serialized objects; the "schema" lives in application classes. Coherence does not enforce or know field types except via extractors.
- **Migration/evolution:** Handled at the serialization layer. **POF supports versioned/evolvable types** (add fields without breaking old readers), which is the supported path for rolling object-schema changes. No DDL, no `ALTER`.
- **Type system:** No native column types. Indexing and querying work by applying **value extractors** (incl. `PofExtractor`) to fields of stored objects; supports building indexes on extracted attributes. No native geospatial/vector/JSON types as first-class storage primitives.

## Query interface
- **Language:** Java API is primary (`NamedCache` get/put/invoke, `Filter`-based queries, aggregators). **CohQL** is a lightweight SQL-like DSL for cache CRUD/queries from code or a CLI ([Oracle: CohQL](https://docs.oracle.com/en/middleware/standalone/coherence/14.1.1.0/develop-applications/using-coherence-query-language.html)). REST and gRPC/Extend client gateways exist for non-Java clients.
- **Transactions:** Single-entry atomic (esp. via entry processors); multi-key/multi-cache ACID only via the explicit Transaction Framework API. No general SQL transactions.
- **Native vs app-side:** Queries (filters) run **in parallel across partitions, using indexes when defined**; on partitioned caches this is server-side and parallel ([Oracle: querying](https://docs.oracle.com/en/middleware/standalone/coherence/14.1.1.0/develop-applications/using-coherence-query-language.html)). No SQL joins; joins/relationships are an app concern. Aggregations supported via parallel aggregators.
- **Stored procedures / UDFs:** **Entry processors and aggregators** are the equivalent — arbitrary Java executed on the data members where entries live (data-local compute), avoiding moving data to the client. Java only (plus JVM languages).

## Scaling & topology
- **Vertical vs horizontal:** Horizontal scale-out by adding JVM members ("storage-enabled" nodes); data and load rebalance automatically.
- **Sharding:** Automatic hash partitioning (fixed partition count, default 257). **Resharding/rebalancing is automatic** on membership change — adding/removing nodes triggers partition redistribution without manual resharding. This is a core strength versus manually sharded stores.
- **Read replicas / read consistency:** Backups are normally not read (reads go to the primary, giving read-your-writes within a cluster); `read-from-backup` can be enabled for locality at the cost of possibly stale reads. **Near caches** keep a client-local copy of hot entries with invalidation; **replicated caches** put a full copy on every member (read-fast, write-expensive, small datasets only).
- **Storage/compute separation:** No — classic shared-nothing grid; storage-enabled members hold data in their own heap/journal. Extend/gRPC clients are compute-only proxies but the grid itself co-locates storage and compute. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** In-memory write to primary + synchronous backup before ack → small in-cluster data-loss window for a single-node crash (backup promotes). **Without persistence enabled, a full-cluster outage loses all data** — it is a cache. Optional **persistence**: *active mode* writes all mutations to disk and auto-recovers on restart; *on-demand* mode does manual snapshots via the persistence coordinator MBean ([Oracle: Persisting Caches](https://docs.oracle.com/middleware/1221/coherence/administer/persistence.htm)). See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact fsync/group-commit semantics of active persistence not confirmed here.
- **Throughput/latency:** In-memory key access is sub-millisecond to low-millisecond; entry processors avoid round-trips by computing on the data member. Designed for high concurrent throughput.
- **Compaction / vacuum / GC:** Runs on the JVM → **GC pauses are the primary p99 tail risk.** Off-heap/elastic-data journals and tuning exist specifically to reduce heap pressure and GC stalls. No LSM compaction.

## Operations & maturity
- **Backup/restore, PITR:** Persistence snapshots (create/archive/recover via MBean); active persistence for auto-recovery. No fine-grained PITR/WAL replay story comparable to an RDBMS. ⚠️ unverified — PITR granularity.
- **Observability:** JMX MBeans for cluster/service/cache metrics; reporter framework; Coherence VisualVM plugin; Grafana/Prometheus dashboards via metrics endpoint; query explain plans available for CohQL/filters.
- **Upgrade story:** Rolling upgrades supported (members restart while the grid maintains availability via backups); requires version-compatibility care. Day-2 burden is mostly JVM/heap/GC tuning and capacity planning.
- **Maturity:** Very mature — Tangosol Coherence shipped Dec 2001, Oracle acquired Tangosol in 2007; long production track record in finance/telco. Known failure modes: GC-induced pauses, split-brain risk if cluster membership/quorum is misconfigured, and total data loss on full-cluster restart without persistence. **No Jepsen report exists** for Coherence (as of this writing).

## Ecosystem & people
- **Canonical use cases:** Caching tier in front of an RDBMS (read-through/write-through/write-behind to a system of record), HTTP session replication (Coherence*Web), low-latency reference-data grids, and data-local compute (entry processors) for trading/risk/telco workloads.
- **Anti-patterns:** Using it as the durable system of record; analytical/OLAP queries; relational/joins-heavy workloads; large datasets where keeping the working set in JVM heap is uneconomical; teams not comfortable operating large JVM clusters.
- **Drivers/connectors:** Native Java; Extend clients for C++/.NET; REST and gRPC gateways; integrates with WebLogic, JCache (JSR-107), Spring, Micronaut, Helidon, and Kubernetes via the **Coherence Operator**. Read/write-through integrations to JPA/JDBC/external stores.
- **Community, support, docs:** Oracle docs are extensive but version-fragmented. Community Edition has an active GitHub project and [coherence.community](https://coherence.community/) site. Commercial support tied to Oracle. Learning curve is moderate-to-steep (grid concepts, serialization/POF, JVM tuning); team is typically Java engineers.

## Licensing & cost
- **OSS license & flavor:** **Coherence Community Edition (CE)** released open-source in summer 2020 under the **Universal Permissive License 1.0 (permissive)** on GitHub, usable in production with no license fee but without Oracle support or some Grid features ([Oracle: announcing CE](https://blogs.oracle.com/oraclecoherence/post/announcing-coherence-community-edition)). This is a 2020 *opening up*, the opposite of the post-2018 source-available relicensing trend. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Commercial editions:** Enterprise Edition and Grid Edition are proprietary, per-processor licensed. ⚠️ unverified pricing (third-party figures): roughly ~$11,500/processor (Enterprise) and ~$25,000/processor (Grid), +22%/yr support ([Redress Compliance](https://redresscompliance.com/oracle-coherence-licensing-costs-guide/)). Treat as indicative, not authoritative.
- **Self-managed vs managed:** Primarily self-managed (or embedded in WebLogic/Fusion Middleware). No mainstream first-party serverless SaaS.
- **Lock-in:** POF/Java object serialization and Coherence-specific APIs (entry processors, filters) create application-level lock-in even with CE.
- **Cost at scale:** Cost scales with cluster node/heap footprint (RAM is the dominant cost) plus per-processor license for commercial editions; can get expensive because all hot data lives in JVM memory.

## Hardware / deployment
- **Resource profile:** **Memory-bound** — the working set (or all data, since it's a cache) must fit in cluster RAM (heap + off-heap journal). CPU matters for serialization and entry-processor compute; GC tuning is central.
- **Storage assumptions:** Disk only needed for optional persistence/snapshots; NVMe/SSD recommended for active persistence throughput. Network: low-latency cluster interconnect matters (TCMP).
- **Footprint:** Clustered, embeddable as a library inside any JVM application; not a standalone server-only product and not embedded single-file. Members are JVMs.
- **Deployment:** On-prem, VM, or container; **first-class Kubernetes support via the Coherence Operator** (StatefulSet-style management, scaling, persistence volumes). Common inside WebLogic.

## Bottom line
Reach for Coherence when you need a low-latency, horizontally scalable Java caching/compute grid in front of a system of record — especially for read-through/write-behind caching, session replication, or data-local compute via entry processors, ideally on Kubernetes with the Coherence Operator. Do not use it as your durable database, for analytics, or for relational/joins-heavy workloads. The single biggest gotcha: **it is a cache first** — without persistence enabled a full-cluster restart loses everything, multi-key ACID is opt-in (Transaction Framework) rather than default, and JVM GC is your p99 tail.

## Sources
- [Oracle: Introduction to Coherence Caches (14.1.1)](https://docs.oracle.com/en/middleware/standalone/coherence/14.1.1.0/develop-applications/introduction-coherence-caches.html)
- [Oracle: Using Coherence Query Language (CohQL)](https://docs.oracle.com/en/middleware/standalone/coherence/14.1.1.0/develop-applications/using-coherence-query-language.html)
- [Oracle: Performing Transactions (Transaction Framework)](https://docs.oracle.com/middleware/1221/coherence/develop-applications/api_transactionslocks.htm)
- [Oracle: Persisting Caches](https://docs.oracle.com/middleware/1221/coherence/administer/persistence.htm)
- [Oracle: Federating Caches Across Clusters](https://docs.oracle.com/middleware/1221/coherence/administer/replication.htm)
- [Oracle blog: Announcing Coherence Community Edition (2020)](https://blogs.oracle.com/oraclecoherence/post/announcing-coherence-community-edition)
- [Coherence Community site](https://coherence.community/)
- [Wikipedia: Oracle Coherence (history)](https://en.wikipedia.org/wiki/Oracle_Coherence)
- [Redress Compliance: Coherence licensing & cost (third-party, unverified pricing)](https://redresscompliance.com/oracle-coherence-licensing-costs-guide/)
