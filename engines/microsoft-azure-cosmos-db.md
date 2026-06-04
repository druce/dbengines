---
name: Microsoft Azure Cosmos DB
slug: microsoft-azure-cosmos-db
rank: 29
data_model: Multi-model
license: Proprietary (managed-only, Azure-exclusive)
summary: Azure's globally distributed PaaS database with five tunable consistency levels and wire-compatible NoSQL/Mongo/Cassandra/Gremlin/Table APIs; powerful but RU-billed and lock-in heavy.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Azure Cosmos DB

> A fully managed, globally distributed Azure database whose defining feature is five well-defined consistency levels (not just strong/eventual) with single-digit-millisecond SLAs — at the cost of an opaque Request-Unit billing model and deep Azure lock-in.

## When to use

**Use Microsoft Azure Cosmos DB if:**
- ✅ You are committed to Azure and need a turnkey, globally distributed, low-latency document/KV store with SLA-backed single-digit-ms reads/writes
- ✅ You want genuinely fine-grained consistency control — five well-defined levels (Strong → Eventual), tunable per account/request
- ✅ Your access patterns are point reads/writes for web/mobile/IoT, session/profile/catalog stores, or multi-tenant SaaS
- ✅ You want integrated vector search (DiskANN) for RAG/agent memory alongside your operational data

**Avoid Microsoft Azure Cosmos DB if:**
- ❌ You need cross-partition or serializable transactions, or cross-entity relational joins (ACID is snapshot isolation scoped to a single logical partition)
- ❌ You have spiky/unpredictable traffic that blows past provisioned RU — exceeding RU/s returns HTTP 429 throttling
- ❌ You need heavy ad-hoc analytics or multi-cloud portability (it is managed-only, Azure-exclusive)
- ❌ You might pick a low-cardinality/hot partition key — the **immutable partition key** is the biggest gotcha, fixable only by full data migration

## Identity
- **Taxonomy / data model:** [multi-model](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction). One engine exposed through several wire-compatible APIs: NoSQL (native document/JSON), MongoDB (RU and vCore), Cassandra (CQL), Gremlin ([graph](../concepts/graph-data-model.md)), and Table (KV). Native [vector search](../concepts/vector-search-ann.md) (DiskANN) in the NoSQL API stores embeddings alongside documents ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/vector-search)). Cosmos DB for PostgreSQL is a separate Citus-based product, not this engine.
- **Storage model:** schema-agnostic JSON document store with an automatic, write-optimized indexing engine that indexes every property by default; ⚠️ unverified — Microsoft does not publicly commit to a [B-tree vs LSM](../concepts/lsm-vs-btree.md) on-disk layout, treating the storage format as an internal implementation detail.
- **Workload:** primarily [OLTP](../concepts/oltp-olap-htap.md) (point reads/writes, key-value and document patterns). For analytics it offers a column-store "analytical store" (Synapse Link / Fabric mirroring) physically separate from the transactional store — genuine HTAP separation rather than a vague claim, but analytics run in Synapse/Fabric, not in Cosmos itself.

## Distribution & consistency
- **CAP under partition:** tunable. Strong is [CP](../concepts/cap-pacelc.md) (refuses to serve stale reads, sacrifices availability during partition); Eventual/Session/Consistent-Prefix lean AP. Cosmos's own docs frame the tradeoff via [PACELC](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels).
- **PACELC:** the five levels span the spectrum — under Partition, Strong chooses Consistency, weaker levels choose Availability; Else (no partition), it lets you trade Latency for Consistency per request. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Five consistency levels** (strongest→weakest): **Strong** (linearizable, returns latest committed write), **Bounded Staleness** (lag bounded by K versions or T time, whichever first), **Session** (read-your-writes within a session via a partition-bound session token — the default and most-used level), **Consistent Prefix** (writes seen in order, no gaps), **Eventual** ([source](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)). Set account-wide; **Session is the default for new accounts** ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-manage-consistency)). The classic per-request override only relaxes consistency (see Tunable consistency below).
- **"ACID" caveat:** transactions are ACID with **snapshot isolation**, scoped to a single logical partition ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/database-transactions-optimistic-concurrency)). This is snapshot isolation, not serializable, and not cross-partition. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** within a region, every write goes to a local majority (3 of a 4-replica set). Strong commits to a **global majority** across all regions before acknowledging; all weaker levels commit locally and replicate asynchronously ([source](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)). Multi-region writes (multi-leader) use last-writer-wins or a custom merge stored procedure for conflict resolution. See [replication-models](../concepts/replication-models.md).
- **Key constraint:** multi-region write accounts **cannot** use Strong consistency (no RPO=0 + RTO=0 distributed system) ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)). Strong across regions >5,000 mi is blocked by default due to write latency.
- **Tunable consistency:** yes — this is the headline feature. **Session is the account-level default** ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-manage-consistency)); the classic per-request `ConsistencyLevel` override can only *relax* below the account default, but the newer `ReadConsistencyStrategy` (preview; .NET v3.46+/Java v4.69+, direct mode only) can also *strengthen* a read above the account default ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-manage-consistency)). The *Probabilistically Bounded Staleness (PBS)* metric tells you how often you actually get stronger-than-configured reads.
- **Clock dependency:** ⚠️ unverified — Cosmos does not advertise a TrueTime/HLC-style clock dependency for correctness; consistency is enforced via quorum and per-partition logical sequence numbers. See [clocks-and-time](../concepts/clocks-and-time.md).
- **Formal verification:** the five levels are formally specified in [TLA+](https://github.com/azure/azure-cosmos-tla). An independent TLA+ study ([arXiv 2210.13661](https://arxiv.org/pdf/2210.13661)) surfaced two documentation errors (since fixed) and behaviors poorly understood even internally. No public **Jepsen** report exists.

## Schema
- **Schema-on-read** — schemaless JSON; schema lives in app code. No table-level DDL locks because there is no rigid schema.
- **Migration/evolution:** add/remove fields freely; the automatic index adapts. Indexing-policy changes apply online in the background (no table lock).
- **Type system:** JSON primitives, arrays, nested objects; geospatial (GeoJSON points/polygons), and vectors (float arrays with vector index). No native intervals/decimals beyond JSON number semantics.

## Query interface
- **Language:** depends on API. NoSQL API uses a SQL-like dialect over JSON (SELECT/WHERE/JOIN within a document, no cross-document joins). Other APIs speak their native protocol: MongoDB query language, CQL, Gremlin, OData (Table).
- **Transactions:** ACID **within a single logical partition** only — via stored procedures/triggers (JavaScript hosted in-engine) or `TransactionalBatch` (max 100 ops, 2 MB, 5 s) ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/transactional-batch)). No cross-partition or cross-container transactions. Optimistic concurrency via ETags.
- **Native vs app-side:** automatic indexing of all properties; aggregations and intra-document joins supported in NoSQL API; cross-document/cross-partition joins must be done app-side. Cross-partition queries fan out and cost more RU.
- **Stored procedures / UDFs / triggers:** JavaScript, executed inside the engine in the same transactional scope as the partition ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/stored-procedures-triggers-udfs)). Pre/post triggers and UDFs supported.

## Scaling & topology
- **Horizontal by design.** You pick a **partition key**; data is split into logical partitions, mapped onto physical partitions ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/partitioning)). Each physical partition caps at ~50 GB and 10,000 RU/s; a single logical partition is bounded to one physical partition (so a hot/oversized logical partition is a hard ceiling).
- **Resharding pain:** partition key is **immutable** after container creation — choosing a low-cardinality or hot key is the classic Cosmos failure mode requiring a full data migration to fix. Physical splits are automatic and invisible.
- **Read replicas:** add/remove regions with a few clicks; reads served from the local region. Read consistency from secondaries depends on the configured level (Session/Eventual may lag; Bounded Staleness bounds the lag).
- **Storage/compute separation:** RU throughput (compute) and storage are billed and scaled independently; analytical store further separates OLAP storage. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** local quorum to 3 of 4 replicas before ack for weaker levels; Strong adds synchronous cross-region commit. See [wal-and-durability](../concepts/wal-and-durability.md).
- **SLAs:** read and write latency guaranteed <10 ms at p99 (typical p50 ~4–5 ms); throughput SLA tied to provisioned RU/s ([source](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)). **Exception:** multi-region Strong write latency = ~2× the inter-region RTT + 10 ms, which can be tens to hundreds of ms.
- **Data-loss window (RPO):** single-region accounts <240 min; multi-region single-write Strong = 0; Session/Eventual <15 min; Bounded Staleness = K & T ([docs](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)).
- **Throughput cost asymmetry:** Strong and Bounded Staleness reads hit two replicas, so read RU cost is **2×** that of Session/Consistent-Prefix/Eventual (single-replica reads). Write RU is identical across levels.
- **p99 / throttling:** exceeding provisioned RU/s returns HTTP 429 (rate-limited) — the dominant operational gotcha. Autoscale (0.1×Tmax ≤ T ≤ Tmax) and per-partition dynamic scaling mitigate hot partitions but do not remove the per-partition 10k RU/s ceiling. No user-visible compaction/vacuum.

## Operations & maturity
- **Backup/restore:** periodic backups by default; **continuous backup with point-in-time restore** (7- or 30-day window) for NoSQL, MongoDB, Gremlin, Table — **Cassandra API is not supported** for continuous backup ([Azure docs](https://learn.microsoft.com/en-us/azure/cosmos-db/continuous-backup-restore-introduction)).
- **Observability:** Azure Monitor metrics, per-request RU charge headers, query execution metrics, PBS metric, diagnostic logs. No `EXPLAIN` in the SQL sense but indexed-vs-scan metrics are exposed.
- **Upgrade story:** fully managed PaaS — no version upgrades, patching, or downtime windows the user manages. Day-2 burden shifts from ops to **RU capacity planning and partition-key design**.
- **Maturity:** GA since 2017 (evolved from Microsoft's "Project Florence"/DocumentDB, 2014); backs large first-party Microsoft services. No public Jepsen report; consistency model is TLA+-specified and independently audited (see Distribution section). Known failure modes: hot partitions, 429 throttling, partition-key lock-in.

## Ecosystem & people
- **Canonical use cases:** globally distributed OLTP web/mobile/IoT apps, session/user-profile/catalog stores, multi-tenant SaaS, low-latency key-value/document workloads, and increasingly RAG/agent memory via integrated vector search.
- **Anti-patterns:** relational workloads needing cross-entity joins or cross-partition serializable transactions; heavy ad-hoc analytics (use analytical store/Fabric instead); cost-sensitive workloads with spiky or unpredictable traffic that blow past provisioned RU; anyone needing multi-cloud portability.
- **Drivers/connectors:** SDKs for .NET, Java, Python, JS, Go; the Mongo/Cassandra/Gremlin/Table wire APIs let existing drivers connect (with compatibility caveats). Change feed for CDC, native Kafka connectors, Spark connector, Synapse Link / Microsoft Fabric mirroring for analytics.
- **Community/support:** large within the Microsoft/Azure ecosystem; first-party docs are thorough; commercial support via Azure. Learning curve is real around RU economics and partition design.

## Licensing & cost
- **License:** proprietary, **managed-only** — there is no self-hosted or open-source edition. You can only run it on Azure. The wire-compatible APIs (Mongo, Cassandra) mimic OSS protocols but the engine is closed. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Lock-in:** high — proprietary RU model, partition semantics, change feed, and Azure-only hosting. Wire compatibility eases driver migration *in* but not data/operational migration *out*.
- **Cost model:** **Request Units per second (RU/s)** — a normalized abstraction over CPU/IO/memory — plus per-GB storage. Modes: provisioned (manual), autoscale (pay for peak within 0.1×–1× band), and serverless (pay per RU consumed). At scale, costs invert: cheap for small/bursty serverless workloads but provisioned RU for sustained high throughput across many partitions/regions can be expensive and hard to forecast. ⚠️ unverified — exact $/RU pricing varies by region and changes over time; check the Azure pricing calculator.

## Hardware / deployment
- **Resource profile:** abstracted away — you provision RU/s, not CPU/RAM/disk. Effectively IO/throughput-bound from the user's perspective; working set need not fit in RAM.
- **Storage assumptions:** managed Azure storage; users do not choose NVMe vs network-attached.
- **Footprint:** cloud-only, clustered/serverless PaaS. No embedded or on-prem option (Azure Stack notwithstanding).
- **Deployment:** SaaS/PaaS exclusively; no containers or StatefulSets to manage. Multi-region turn-up is a configuration toggle.

## Bottom line
Reach for Cosmos DB when you are committed to Azure and need a turnkey, globally distributed, low-latency document/KV store with genuinely fine-grained consistency control and SLA-backed latency. Avoid it for relational/join-heavy workloads, cross-partition transactions, heavy analytics, or multi-cloud strategies. The single biggest gotcha is the combination of an **immutable partition key** and **RU-based throttling**: a poorly chosen partition key creates hot partitions that throttle (429) and can only be fixed by a full migration — design it carefully up front.

## Sources
- [Consistency levels in Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels) (official)
- [Partitioning and horizontal scaling](https://learn.microsoft.com/en-us/azure/cosmos-db/partitioning) (official)
- [Database transactions and optimistic concurrency control](https://learn.microsoft.com/en-us/azure/cosmos-db/database-transactions-optimistic-concurrency) (official)
- [Transactional batch operations](https://learn.microsoft.com/en-us/azure/cosmos-db/transactional-batch) (official)
- [Stored procedures, triggers, and UDFs](https://learn.microsoft.com/en-us/azure/cosmos-db/stored-procedures-triggers-udfs) (official)
- [Vector search in Azure Cosmos DB for NoSQL](https://learn.microsoft.com/en-us/azure/cosmos-db/vector-search) (official)
- [Unified AI Database — introduction](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction) (official)
- [azure/azure-cosmos-tla — TLA+ specs of the five consistency levels](https://github.com/azure/azure-cosmos-tla)
- [Understanding Inconsistency in Azure Cosmos DB with TLA+ (arXiv 2210.13661)](https://arxiv.org/pdf/2210.13661)
