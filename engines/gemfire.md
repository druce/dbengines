---
name: GemFire
slug: gemfire
rank: 102
data_model: Key-value (in-memory data grid)
license: Proprietary commercial (Broadcom/VMware GemFire, forked from Geode); open-source sibling is Apache Geode (Apache 2.0)
summary: Java in-memory data grid (the OSS Apache Geode core, commercialized by Broadcom) for low-latency caching, partitioned regions, and WAN replication — strong on speed and HA, weak on cross-partition transactions and SQL.
last_researched: 2026-06-04
confidence: high
---

# GemFire

> A Java distributed in-memory data grid — regions of key-value objects spread across a shared-nothing cluster for sub-millisecond reads/writes, with disk persistence and WAN replication; choose it as a scale-out cache/operational store, not as a SQL database.

## When to use

**Use GemFire if:**
- ✅ You need a battle-tested, low-latency (sub-millisecond) Java in-memory data grid for caching or operational hot data, especially in a Spring/JVM shop.
- ✅ You want HA via configurable in-memory redundant copies plus optional oplog disk persistence and asynchronous WAN (geo) replication.
- ✅ You run real-time event processing with continuous queries (CQ) and data-aware server-side function execution.

**Avoid GemFire if:**
- ❌ You need distributed cross-shard ACID transactions — multi-key ACID effectively requires data colocated on a single member, and isolation is repeatable-read (not serializable), with no Jepsen validation.
- ❌ You need SQL/analytics/ad-hoc aggregation — OQL lacks aggregation functions and joins are limited to colocated/replicated data.
- ❌ Your dataset won't economically fit in RAM, or your team lacks JVM-tuning expertise — it is memory-first and GC pauses dominate tail latency.
- **Taxonomy / data model:** Key-value [oltp-olap-htap](../concepts/oltp-olap-htap.md) in-memory data grid (IMDG). Data lives in named **regions** (analogous to tables/maps) inside a distributed **cache**; values are arbitrary Java objects, queried via OQL on object graphs. GemFire is the commercial product (originally GemStone Systems → Pivotal/VMware → Broadcom); its open-source core was donated to the Apache Software Foundation in 2015 as **Apache Geode** ([VMware Open Source Blog](https://blogs.vmware.com/opensource/2020/04/14/apache-geode-a-quick-history/)). They originated from a shared codebase, but **VMware GemFire has since forked and diverged** — it is not open source, selectively pulls in (and adds proprietary features beyond) Geode improvements, and newer GemFire/Geode clients are not cross-compatible with older servers. Apache Geode itself was voted into the **Apache Attic in November 2022** (no active PMC), the PMC moved to terminate it in 2024, and it was then **revived** — Geode 1.15.2 (Sep 2025) and **Geode 2.0 (Dec 2025)** ([ASF blog: Geode 2.0 revival](https://news.apache.org/foundation/entry/apache-geode-2-0-revival-reinvention-and-the-road-ahead)).
- **Storage model:** Primary store is JVM heap (and off-heap) memory across cluster members; no [lsm-vs-btree](../concepts/lsm-vs-btree.md) page store. Optional disk persistence uses append-only **operation logs (oplogs)** — a write-ahead-log design with parallel recovery ([Geode](https://geode.apache.org/)). Indexes are hash-based (entry keys hash to buckets); range/OQL indexes are also supported.
- **Workload:** OLTP-style low-latency reads/writes and caching. Not an OLAP/analytics engine — OQL lacks aggregation functions ([dbdb.io](https://dbdb.io/db/geode)). No HTAP claim.

## Distribution & consistency
- **CAP under partition:** Effectively **CP-leaning for partitioned regions** — Geode/GemFire prioritizes consistency and uses membership/quorum mechanisms (network-partition detection, "weighted membership") to shut down minority sides and avoid split-brain, at the cost of availability for those members. See [cap-pacelc](../concepts/cap-pacelc.md). ⚠️ unverified — no published Jepsen report exists for GemFire/Geode, so its partition behavior under adversarial testing is not independently confirmed.
- **PACELC:** ⚠️ unverified — not formally stated by the vendor. In practice: under partition it favors consistency (fences off minority members); else (normal operation) it favors latency, with consistency tunable per-region (synchronous replication vs async, redundancy level).
- **Default isolation & what's achievable:** Geode/GemFire documents its cache transactions as having **repeatable read isolation** — once a committed value is read for a key inside a transaction, that transaction keeps seeing the same value ([Geode transaction semantics](https://geode.apache.org/docs/guide/114/developing/transactions/transaction_semantics.html), [Adherence to ACID Promises](https://geode.apache.org/docs/guide/114/developing/transactions/transactions_intro.html)). Isolation is at the **process-thread level**: a transaction's uncommitted changes are visible only inside its own thread until commit begins. **Caveat — dirty reads:** by default, once commit *begins*, other (non-transactional) threads can observe partial results; to get the conventional model that forbids dirty reads of transitional state, reads must run inside transactions with `-Dgemfire.detectReadConflicts=true` ([Geode transaction semantics](https://geode.apache.org/docs/guide/114/developing/transactions/transaction_semantics.html)). Conflict handling is **optimistic** — no locks during the transaction; a reservation/conflict check happens at commit (last-committer-wins is rejected via `CommitConflictException`). This is **not serializable** — see [isolation-levels](../concepts/isolation-levels.md). The "ACID" label applies only to a transaction whose data is **colocated on one member**; cross-node transactions are restricted.
- **Replication:** Per-region. **Replicated regions** copy full data to every member; **partitioned regions** shard data with configurable in-memory **redundant copies** (e.g. 1 backup). Updates are propagated to redundant copies; consistency between copies is maintained by **version stamps** (per-entry version + member ID; higher version wins, member ID breaks ties) ([Geode region versioning](https://geode.apache.org/docs/guide/114/developing/distributed_regions/how_region_versioning_works.html)). See [replication-models](../concepts/replication-models.md). **WAN replication** (gateway senders/receivers) is asynchronous and eventually consistent across geo sites.
- **Tunable consistency?** Yes, per-region: replicated vs partitioned, redundancy level, synchronous vs async distribution, consistency-checking on/off.
- **Clock dependency:** No reliance on synchronized physical clocks for correctness — ordering uses logical version vectors, not timestamps. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Regions hold arbitrary serialized objects; structure lives in application code. GemFire's **PDX serialization** allows storing objects without the class on the server and supports field-level access and limited schema evolution (adding/removing fields across versions).
- **Migration/evolution:** No DDL/ALTER. Region structure changes are application/serialization concerns; PDX handles versioned object fields.
- **Type system:** Whatever the JVM serializes — POJOs via PDX or Java serialization, plus JSON (stored as PDX). No native geospatial/vector types; full-text via an optional Apache Lucene integration.

## Query interface
- **Language:** **OQL (Object Query Language)**, an object-oriented SQL-like dialect that queries region values and object graphs by default (not keys), and **lacks aggregation functions** ([dbdb.io](https://dbdb.io/db/geode)). Also a direct key-based Map API (get/put/getAll/putAll), continuous queries (CQ) for change notification, and function execution (server-side compute colocated with data).
- **Transactions:** Multi-key ACID **only when all keys are colocated on a single member**; partitioned-region transactions require colocation ([Geode](https://geode.apache.org/)). No distributed cross-node transaction coordinator in the general case (JTA integration exists for app-server coordination).
- **Native vs app-side:** OQL joins are limited (within colocated/replicated data); secondary indexes on region fields are native; aggregations must be done app-side or via function execution. No window functions.
- **Stored procedures / UDFs:** **Function service** — deploy Java functions that execute on members where the data lives (data-aware routing), the primary server-side compute mechanism.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — add members to grow capacity/throughput. Partitioned regions auto-distribute data across buckets; adding members triggers **rebalancing** of buckets.
- **Sharding:** Automatic bucket-based partitioning with a configurable partition resolver and **colocation** (related data on the same member). Resharding/rebalance is online but moves data over the network and consumes heap/CPU.
- **Read replicas & consistency:** Redundant copies serve as HA backups; reads can be served from a primary or, with configuration, from redundant copies. Within a region, version stamps keep copies consistent.
- **Storage/compute separation:** No — compute and in-memory data are colocated on members (shared-nothing). Disk persistence is local per member. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) architecture.

## Performance & durability
- **Write path:** In-memory writes propagated to redundant copies; optional disk persistence appends to **oplogs** (WAL-style) with configurable sync — `disk-synchronous=true` flushes per op (durable, slower) vs async buffered (faster, with a crash data-loss window). See [wal-and-durability](../concepts/wal-and-durability.md). If a region is memory-only (no persistence) and all redundant copies are lost, that data is gone — durability depends entirely on configured redundancy + persistence.
- **Throughput/latency:** Designed for sub-millisecond reads and very high concurrency; historically used in Wall Street trading and low-latency systems ([O'Reilly](https://www.oreilly.com/library/view/scaling-data-services/9781492027584/ch01.html)). ⚠️ unverified — no vendor-independent p99 benchmarks reviewed here.
- **GC/compaction:** Being JVM-heap-resident, **GC pauses are the dominant p99 risk**; off-heap storage and tuning mitigate this. Disk oplogs require periodic compaction to reclaim space from overwritten/deleted entries.

## Operations & maturity
- **Backup/restore:** Online backups of persistent regions (incremental supported); disk-store snapshots and region snapshot import/export.
- **Observability:** JMX metrics, statistics archives, `gfsh` (command-line shell) for cluster admin and queries, Pulse web dashboard, OQL `EXPLAIN`-style query inspection is limited.
- **Upgrade story:** Rolling upgrades supported across compatible versions; day-2 burden is real — heap/GC tuning, rebalancing, disk-store management, and membership/locator configuration require expertise.
- **Maturity:** Long production track record (GemStone lineage from the late 1990s; financial-sector deployments). Known failure modes: GC-induced pauses and "slow member" cascades, heap exhaustion, network-partition member shutdowns, and operational complexity. **Jepsen:** ⚠️ unverified — no public Jepsen analysis of GemFire/Geode is known.

## Ecosystem & people
- **Canonical use cases:** Distributed cache / system-of-record acceleration in front of an RDBMS, low-latency session and reference-data stores, real-time event processing with continuous queries, and "database offload" where hot operational data lives in the grid. Strong fit with Spring ([Spring Data for VMware GemFire](https://spring.io/projects/spring-data-gemfire/)).
- **Anti-patterns:** Analytics/ad-hoc aggregation (OQL can't aggregate well), workloads needing distributed cross-shard ACID transactions, datasets that vastly exceed affordable RAM (it is memory-first), and teams without JVM-tuning expertise. Not a general-purpose SQL database.
- **Drivers/connectors:** Java is first-class; Spring Data for GemFire/Geode, Spring Session, Spring Integration; native clients for C++/.NET; REST API; Lucene integration for text search; WAN gateways for geo-replication. CDC/Kafka integration is via cache listeners/async event queues rather than a turnkey log.
- **Community/support:** Apache Geode provides an OSS community; GemFire commercial support and docs come from Broadcom (formerly VMware/Pivotal). Smaller ecosystem than Redis/Hazelcast; learning curve is steep (regions, redundancy, colocation, GC).

## Licensing & cost
- **License & flavor:** Open-source sibling is **Apache Geode (Apache 2.0, permissive)** — note Geode was in the Apache Attic from late 2022 and was only revived in late 2025 (Geode 2.0). **GemFire** itself **forked from Geode and is not open source** ([dbdb.io / Dremio](https://www.dremio.com/wiki/apache-geode/)); it is a **commercial, proprietary** product now owned by **Broadcom** (acquired VMware in 2023), distributed via Broadcom/Tanzu with Maven artifacts requiring a Broadcom account/entitlement. See [license-taxonomy](../concepts/license-taxonomy.md). ⚠️ unverified — exact current GemFire commercial license text was not read from a primary license document in this research.
- **Self-managed vs managed:** Primarily self-managed software; also offered as a managed service on VMware Tanzu / cloud foundries. Lock-in risk comes from proprietary GemFire-only features and PDX/OQL specifics; Apache Geode is a partial open-source escape hatch, but the codebases have diverged (clients/servers are not cross-version compatible) and Geode's long Attic dormancy weakened that path.
- **Cost model:** Commercial GemFire is subscription/support-based (per-node or capacity); ⚠️ unverified — no public list pricing. Cost scales with the amount of data you must hold in RAM, which inverts the "cheap" story at large data sizes.

## Hardware / deployment
- **Resource profile:** **Memory-bound** — the working set (often all of it) must fit in cluster RAM across members and their redundant copies; CPU and network matter for rebalancing and replication. JVM heap sizing and GC are the core tuning levers.
- **Storage assumptions:** Local disk for oplogs/persistence (NVMe/SSD preferred for sync persistence latency); does not assume network-attached storage.
- **Footprint:** Clustered JVM processes (data members + locators); not embedded, not serverless. Single-node is possible for dev only.
- **Deployment:** On-prem or cloud VMs; runs on Kubernetes (StatefulSets) but stateful in-memory clustering, locators, and rebalancing add operational nuance.

## Bottom line
Reach for GemFire (or its OSS sibling Apache Geode — now diverged and recently revived as Geode 2.0) when you need a battle-tested, low-latency Java in-memory data grid for caching and operational hot data with HA redundancy and WAN replication — especially in a Spring/JVM shop. Do not reach for it as a SQL/analytics database, for datasets that won't economically fit in RAM, or when you need distributed cross-shard serializable transactions. The single biggest gotcha: transactional ACID guarantees and joins effectively require **colocated data on one member**, and consistency claims are Read Committed (not serializable) with no independent Jepsen validation — plus JVM GC pauses dominate tail latency.

## Sources
- [Apache Geode project site](https://geode.apache.org/)
- [Apache Geode: A Quick History — VMware Open Source Blog](https://blogs.vmware.com/opensource/2020/04/14/apache-geode-a-quick-history/)
- [Apache Geode 2.0: Revival, Reinvention, and the Road Ahead — ASF Blog](https://news.apache.org/foundation/entry/apache-geode-2-0-revival-reinvention-and-the-road-ahead)
- [What is Apache Geode? — Dremio (on GemFire fork / not open source)](https://www.dremio.com/wiki/apache-geode/)
- [Adherence to ACID Promises — Geode Docs](https://geode.apache.org/docs/guide/114/developing/transactions/transactions_intro.html)
- [Database of Databases — Geode](https://dbdb.io/db/geode)
- [Geode Cache Transaction Semantics](https://geode.apache.org/docs/guide/12/developing/transactions/transaction_semantics.html)
- [Consistency Checking by Region Type / region versioning](https://geode.apache.org/docs/guide/114/developing/distributed_regions/how_region_versioning_works.html)
- [Scaling Data Services with Pivotal GemFire (O'Reilly)](https://www.oreilly.com/library/view/scaling-data-services/9781492027584/ch01.html)
- [Spring Data for VMware GemFire](https://spring.io/projects/spring-data-gemfire/)
