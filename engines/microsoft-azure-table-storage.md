---
name: Microsoft Azure Table Storage
slug: microsoft-azure-table-storage
rank: 96
data_model: Wide-column / key-value
license: Proprietary (managed cloud service, Azure)
summary: Azure's cheap schemaless key-value/wide-column store keyed on (PartitionKey, RowKey); single-partition transactions only, no secondary indexes.
last_researched: 2026-06-04
confidence: high
---

# Microsoft Azure Table Storage

> A bargain-priced, schemaless NoSQL store inside an Azure Storage account, addressed by a two-part `(PartitionKey, RowKey)` key — fast and cheap when you query by key, painful the moment you need a secondary index, a cross-partition transaction, or rich querying.

## Identity
- **Taxonomy / data model:** Wide-column / key-value. Entities (rows) live in tables; each entity is a flat bag of up to 252 typed properties plus the mandatory `PartitionKey`, `RowKey`, and `Timestamp`. Different entities in the same table can have different property sets — schema lives in app code. Often described as wide-column because columns are per-row and sparse; in practice it behaves as a partitioned key-value store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Row-oriented entities; `PartitionKey` + `RowKey` form a clustered index, the only index that exists ([Table service data model](https://learn.microsoft.com/en-us/rest/api/storageservices/understanding-the-table-service-data-model)). On-disk format is the opaque internal Azure Storage stamp engine (not documented publicly; the WAS design paper covers the underlying architecture).
- **Workload:** OLTP-style point reads/writes and key-range scans within a partition. Not OLAP, not HTAP — no analytical engine, no joins, no aggregations server-side.

## Distribution & consistency
- **CAP under partition:** CP within the primary region — writes commit to the primary stamp and reads are strongly consistent there ([data redundancy](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy)). Geo-replication (GRS/GZRS) adds an **eventually consistent, asynchronous** secondary; the secondary is not writable without an explicit account failover. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EL** in effect. Single-region access is strongly consistent (the system favors consistency); the geo-secondary trades consistency for latency/availability, lagging the primary by an asynchronous **RPO measured in minutes** (Microsoft's Geo priority replication targets RPO ≤ 15 min for block blobs; table RPO is similarly best-effort, not SLA-bounded) ([data redundancy](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy)).
- **Default isolation & what's achievable:** Reads from the primary are strongly consistent. Atomic multi-entity writes exist only via **Entity Group Transactions (EGTs)**, which are restricted to a single partition (same `PartitionKey`), at most 100 entities and ≤ 4 MiB per batch ([table design](https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-design)). There is **no cross-partition transaction and no serializable isolation across partitions** — concurrency between single operations is handled by optimistic concurrency via ETags. Calling this an "ACID database" overstates it: atomicity/isolation hold only inside one partition. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Synchronous within the primary region (LRS = 3 copies in one datacenter; ZRS = across 3 availability zones); asynchronous single-leader copy to a paired secondary region for GRS/GZRS. RA-GRS/RA-GZRS expose a read-only secondary endpoint (`-secondary` suffix) that is eventually consistent. Failover is account-level and operator-initiated, not automatic per-partition. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency knobs (unlike [amazon-dynamodb](amazon-dynamodb.md) or [apache-cassandra](apache-cassandra.md)). You choose strong-primary reads or eventually-consistent secondary reads only by which endpoint you target.
- **Clock dependency:** None for correctness; ordering within a partition is internal. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** No table-level schema; properties are defined per entity at write time. "Schemaless" here genuinely means the contract lives in your application.
- **Migration/evolution:** No `ALTER TABLE` — adding/removing properties is just writing entities with different shapes; no migration step, no locking. The flip side: no enforcement, so consumers must defensively handle missing/typed properties.
- **Type system:** Small fixed set — String, Int32, Int64, Double, Boolean, DateTime, GUID, Binary. **No JSON type, no arrays, no nested objects, no geospatial, no vectors.** Max entity size 1 MiB; max property value 64 KiB (String/Binary).

## Query interface
- **Language:** REST/OData query API (`$filter`); no SQL, no DSL. Filters are OData expressions; SDKs (.NET, Java, Python, JS, Go) wrap the same REST surface. Queries not anchored on `PartitionKey`+`RowKey` degrade to **full-table or full-partition scans** because there are no secondary indexes.
- **Transactions:** Single-partition EGTs (≤100 entities, ≤4 MiB) only; otherwise per-operation atomicity with optimistic concurrency (ETag/`If-Match`).
- **Native vs app-side:** **No server-side joins, no aggregations, no GROUP BY, no ORDER BY beyond the natural `(PartitionKey, RowKey)` sort.** All of that is app-side. Secondary access paths are typically built by hand using duplicated entities / the [Inter-Partition / index-table pattern](https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-design-patterns).
- **Stored procedures / UDFs:** None.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal and automatic — partitions are spread across storage nodes by `PartitionKey`; the platform load-balances and splits hot ranges. You never provision nodes.
- **Sharding:** Partitioning *is* the `PartitionKey` you choose; the platform handles physical placement, but **resharding is a design problem you own** — a poorly chosen `PartitionKey` (too coarse → hot partition; too fine → no batch atomicity) is expensive to fix after the fact ([scalable partitioning](https://learn.microsoft.com/en-us/rest/api/storageservices/designing-a-scalable-partitioning-strategy-for-azure-table-storage)).
- **Throughput targets:** A single partition is throttled at ~**2,000 entities/sec**; a whole storage account targets up to **20,000 entities/sec** (1 KiB entities) ([scalability targets](https://learn.microsoft.com/en-us/azure/storage/tables/scalability-targets)). Hot partitions hit the per-partition ceiling regardless of account headroom.
- **Read replicas / read consistency:** Only the RA-GRS/RA-GZRS geo-secondary, which is read-only and eventually consistent.
- **Storage/compute separation:** Inherently storage-only — there is no compute tier you scale. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Writes are committed synchronously to all in-region replicas (LRS within one DC, ZRS across zones) before ack — the Azure Storage stamp uses an internal commit log; the **in-region data-loss window on a single committed write is effectively zero**. The data-loss exposure is the **async geo-replication lag** (RPO minutes) if you lose the whole primary region before it replicates. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Low-single-digit-millisecond point reads/writes by key within targets; **no published p99 latency SLA** (unlike Cosmos DB's single-digit-ms p99 guarantee). Throttling (HTTP 503/server-busy) is the dominant tail-latency cause once a partition saturates — handle with exponential-backoff retries.
- **Compaction / vacuum / GC:** Opaque, platform-managed. No user-visible compaction, vacuum, or GC knobs; no operational p99 impact you can tune.

## Operations & maturity
- **Backup/restore, PITR:** No native point-in-time restore for tables. Durability comes from replication, not snapshots; backup is DIY (e.g., AzCopy export, Data Factory copy) or relies on object-replication/geo-redundancy. ⚠️ unverified — there is no first-class table-level PITR feature as of mid-2026.
- **Observability:** Azure Monitor metrics (transactions, throttling, latency, capacity), Storage Analytics logs, and per-request `x-ms-request-id`. No `EXPLAIN`/query planner — there is no planner to expose; query cost is determined entirely by whether you hit the key or scan.
- **Upgrade story:** Fully managed PaaS — no version upgrades, no patching, no downtime windows owned by you. Day-2 burden is near-zero operationally; the real burden is **data-model design** up front.
- **Maturity:** Very mature — one of the original Azure Storage services (GA ~2010), built on the Windows Azure Storage (WAS) engine described in the [SOSP 2011 WAS paper](https://sigops.org/s/conferences/sosp/2011/current/2011-Cascais/printable/11-calder.pdf). No public **Jepsen** report exists. ⚠️ unverified — no independent formal-consistency analysis of Table Storage is publicly available; consistency claims rest on Microsoft documentation and the WAS paper.

## Ecosystem & people
- **Canonical use cases:** Cheap, durable storage of large volumes of simple, denormalized, key-addressable data — device/telemetry records, audit/event logs, user metadata, session state, Dapr state stores. Strong when access is overwhelmingly by `(PartitionKey, RowKey)`.
- **Anti-patterns:** Anything needing ad-hoc queries, secondary-index lookups, joins, aggregations, server-side sorting, cross-partition transactions, low-latency SLAs, or global low-latency reads. For those, reach for [microsoft-azure-cosmos-db](microsoft-azure-cosmos-db.md) (Table API is drop-in via connection-string swap, auto-indexes all properties, gives a p99 SLA — at roughly an order of magnitude higher cost), [postgresql](postgresql.md), or [amazon-dynamodb](amazon-dynamodb.md).
- **Drivers / connectors:** Official SDKs (.NET, Java, Python, JS/TS, Go, C++), REST, AzCopy, Azure Data Factory, and Dapr state-store component. The API is **wire-compatible with the Cosmos DB Table API**, easing migration in either direction.
- **Community / docs:** Large Azure ecosystem, thorough Microsoft Learn docs (including detailed design-pattern guidance because the model forces hand-rolled indexing). Learning curve is low to start, but designing `PartitionKey` strategy well takes real expertise.

## Licensing & cost
- **License:** Proprietary, managed-only cloud service — no self-hosted/open-source edition. The Azurite emulator exists for local dev only. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Managed-only (part of an Azure Storage account). Lock-in is moderate: the data model and OData API are Azure-specific, though the Cosmos DB Table API offers an in-cloud escape hatch.
- **Cost model:** Per-GB stored + per-transaction + egress; **extremely cheap** — illustrative third-party comparison: ~$1.67/month vs ~$26.50/month for Cosmos DB serverless on ~1M reads + 500K writes/day ([Table Storage vs Cosmos DB Table API](https://oneuptime.com/blog/post/2026-02-16-how-to-use-azure-cosmos-db-table-api-as-a-replacement-for-azure-table-storage/view)). Cost stays low and predictable at scale because there is no provisioned-throughput tier; you pay for what you store and call. The trade-off you pay for that price is feature poverty, not money.

## Hardware / deployment
- **Resource profile:** Irrelevant to the user — fully serverless storage; no RAM/CPU sizing, no working-set-in-memory requirement.
- **Storage assumptions:** Network-attached, platform-managed durable storage; latency is network-round-trip-bound, not local-NVMe-bound.
- **Footprint:** Cloud service only (an Azure region/storage account). No embedded or on-prem deployment; Azurite emulates it locally for testing.
- **Deployment:** SaaS/PaaS exclusively — no containers, no k8s, no StatefulSets to operate.

## Bottom line
Reach for Azure Table Storage when you need dirt-cheap, durable, massively scalable storage of simple records addressed by a known key, and you can live without rich queries — think logs, telemetry, session/metadata stores, and Dapr state. Do **not** reach for it if you need secondary indexes, joins/aggregations, cross-partition transactions, or a latency SLA; you'll either build a fragile hand-rolled index layer or pay much more for [microsoft-azure-cosmos-db](microsoft-azure-cosmos-db.md). The single biggest gotcha: `PartitionKey` choice is a one-way door — it dictates both your transaction boundary and your hot-partition ceiling (2,000 entities/sec), and there is no secondary index to bail you out later.

## Sources
- [Understanding the Table service data model (REST API)](https://learn.microsoft.com/en-us/rest/api/storageservices/understanding-the-table-service-data-model)
- [Design scalable and performant tables in Azure Table storage](https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-design)
- [Scalability and performance targets for Table storage](https://learn.microsoft.com/en-us/azure/storage/tables/scalability-targets)
- [Designing a scalable partitioning strategy for Azure Table storage](https://learn.microsoft.com/en-us/rest/api/storageservices/designing-a-scalable-partitioning-strategy-for-azure-table-storage)
- [Azure storage table design patterns](https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-design-patterns)
- [Data redundancy - Azure Storage](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy)
- [Azure Table Storage support - Azure Cosmos DB for Table](https://learn.microsoft.com/en-us/azure/cosmos-db/table/support)
- [Windows Azure Storage (WAS) — SOSP 2011 paper](https://sigops.org/s/conferences/sosp/2011/current/2011-Cascais/printable/11-calder.pdf)
- [How to Use Azure Cosmos DB Table API as a Replacement for Azure Table Storage](https://oneuptime.com/blog/post/2026-02-16-how-to-use-azure-cosmos-db-table-api-as-a-replacement-for-azure-table-storage/view)
