---
name: Amazon DynamoDB
slug: amazon-dynamodb
rank: 18
data_model: Key-value / document (multi-model)
license: Proprietary (managed-only AWS service)
summary: Fully managed serverless key-value/document store with predictable single-digit-ms latency at any scale — but you design for its access patterns, not the other way around.
last_researched: 2026-06-04
confidence: high
---

# Amazon DynamoDB

> AWS's serverless NoSQL workhorse: it trades SQL flexibility and joins for guaranteed single-digit-millisecond latency at effectively unbounded scale, as long as you design your keys around your queries up front.

## When to use

**Use Amazon DynamoDB if:**
- ✅ You have a high-scale OLTP workload with known, stable access patterns — shopping carts, session/user state, IoT/event ingestion, gaming leaderboards, serverless backends
- ✅ You want zero operational burden and predictable single-digit-ms latency at any scale; on-demand mode suits spiky, unpredictable traffic
- ✅ You need per-request tunable read consistency and constrained serializable transactions (up to 100 items) within a region

**Avoid Amazon DynamoDB if:**
- ❌ You need ad-hoc queries, JOINs, analytics, or relational flexibility — large `Scan`s and cross-partition access are punished in cost and latency
- ❌ You don't know your queries in advance — success is decided at data-modeling time, and a bad partition key produces hot partitions, throttling, and cost surprises no capacity can fix (the single biggest gotcha)
- ❌ You cannot tolerate hard AWS lock-in (managed-only, proprietary single-table model) or accept silent last-writer-wins conflict loss in eventually-consistent global tables

## Identity
- **Taxonomy / data model:** Key-value and document store; multi-model in the sense that items are schemaless JSON-like documents addressed by a primary key. Descended from the 2007 Dynamo paper but a distinct managed service since 2012.
- **Storage model:** Distributed [LSM-tree](../concepts/lsm-vs-btree.md)-style partitioned storage; data is range-partitioned by partition-key hash across many storage nodes, each a B-tree/LSM hybrid internally (AWS does not fully expose the on-disk format). Replicated 3-way within a region across AZs ([USENIX ATC 2022 paper](https://www.usenix.org/conference/atc22/presentation/elhemali)).
- **Workload:** OLTP / high-throughput key-value. Not OLAP — no ad-hoc analytical queries; for analytics you export to S3 or stream to Redshift/Athena. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** Within a region, **CP-leaning** for strongly consistent reads (a partition's leader replica must be reachable) and AP for eventually consistent reads. Cross-region behavior depends on the mode (below). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under Partition, single-region strong reads sacrifice Availability (PC); eventual reads favor Availability (PA). Else, you pick per-request: strong reads pay Latency, eventually-consistent reads (the default for GetItem) favor latency over consistency (EL). See [replication-models](../concepts/replication-models.md).
- **Default isolation & what's achievable:** Single-item operations are atomic. `TransactWriteItems`/`TransactGetItems` provide **serializable isolation**, but only within a single region and capped at 100 items per transaction ([AWS docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)). These are single-request transactions — no interactive multi-statement BEGIN/COMMIT sessions. See [isolation-levels](../concepts/isolation-levels.md). Note: "ACID" here means a constrained, single-shot serializable transaction, not a long-running session like a relational DB.
- **Replication:** Within a region, single-leader per partition with synchronous quorum to 3 AZ replicas; failover is automatic and fast. Cross-region via **global tables**: default is **multi-Region eventual consistency (MREC)** — multi-leader, async, last-writer-wins by timestamp ([AWS docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html)). Since June 2025, **multi-Region strong consistency (MRSC)** is GA: requires three regions (or two replicas + a witness), quorum writes across a multi-region journal, serializable cross-region reads with `ConsistentRead=True`, and zero RPO ([AWS announcement, June 2025](https://aws.amazon.com/blogs/aws/build-the-highest-resilience-apps-with-multi-region-strong-consistency-in-amazon-dynamodb-global-tables/)). MRSC tables must be created empty and are limited to specific region sets.
- **Tunable consistency:** Per-read choice of eventual (default) or strong (`ConsistentRead`) within a region; per-table choice of MREC vs MRSC across regions.
- **Clock dependency:** MREC last-writer-wins relies on item-level timestamps; AWS documents that regions share atomic-clock-backed time so the later-timestamped write wins ([AWS docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html)), but LWW can still silently drop a concurrent write to the same item. See [clocks-and-time](../concepts/clocks-and-time.md). No Jepsen report exists for DynamoDB; ⚠️ unverified — cross-region MREC conflict-loss behavior under concurrent writes is documented by AWS but has not been independently formally verified.

## Schema
- **Schema-on-read.** Only the primary key (partition key, optional sort key) and any indexed attributes are declared; all other attributes are arbitrary per item. The real schema lives in application code and access patterns.
- **Migration/evolution:** No `ALTER TABLE`. Adding attributes is free (schemaless). Changing key structure requires creating a new table and migrating. Global Secondary Indexes can be added/removed online (backfill runs in background).
- **Type system:** Scalars (string, number, binary, bool, null), sets, lists, and nested maps (document type). No native geospatial, vector, or interval types. No native JOIN-able foreign keys.

## Query interface
- **Language:** API-only (`GetItem`, `PutItem`, `Query`, `Scan`, `BatchGet/Write`, `TransactWrite/Get`). PartiQL (a SQL-ish dialect) is offered as a thin wrapper but does not add joins or change the underlying access-pattern constraints. No relational SQL.
- **Transactions:** Single-region serializable transactions up to 100 items / 4 MB ([AWS docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)); otherwise single-item atomicity. No interactive transactions.
- **Native vs app-side:** `Query` is efficient only on a partition key (+ sort-key range). Cross-partition or cross-table access = full `Scan` (expensive) or app-side joins. Secondary indexes: Local (LSI, same partition key) and Global (GSI, different key, eventually consistent, separately provisioned). Aggregations and window functions: none natively — done app-side or via export.
- **Stored procedures / UDFs:** None. Logic lives in application code or in DynamoDB Streams → Lambda triggers.

## Scaling & topology
- **Vertical vs horizontal:** Purely horizontal and automatic. Partitions split as data/throughput grows; no node sizing exposed.
- **Sharding:** Automatic by partition-key hash — no manual resharding, but **hot partitions** are the classic failure: a poorly distributed partition key throttles even if total table capacity is high. Adaptive capacity mitigates but does not eliminate this.
- **Read replicas / read consistency:** Within-region replicas serve eventually consistent reads by default; strong reads hit the leader. Cross-region replicas (global tables) are eventually consistent unless MRSC.
- **Storage/compute separation:** Yes — storage, request routing, and the partition metadata system are independent fleets; on-demand mode is true [serverless](../concepts/storage-compute-separation.md) with no provisioned nodes.

## Performance & durability
- **Write path:** Writes are committed to a quorum of in-region replicas with a write-ahead log before acknowledgment; durable across AZ failure. See [wal-and-durability](../concepts/wal-and-durability.md). Data-loss window within a region is effectively zero for acknowledged writes; cross-region MREC has a replication lag window (typically sub-second but unbounded under stress).
- **Throughput/latency:** Design target is single-digit-ms point reads/writes at any scale, with consistent **p99** behavior being the explicit selling point per the [USENIX ATC 2022 paper](https://www.usenix.org/conference/atc22/presentation/elhemali). Tail latency degrades on hot partitions and on throttling (provisioned mode) — `ProvisionedThroughputExceededException` / on-demand request rejection are the real-world tail events.
- **Compaction / GC:** LSM compaction is managed by AWS and not user-visible; no `VACUUM` to tune. TTL-based item expiry is a background sweep (can lag hours behind the TTL timestamp).

## Operations & maturity
- **Backup/restore:** On-demand backups and continuous backups with **Point-in-Time Recovery (PITR)** to any second in the last 35 days. Full-table export to S3 without consuming capacity.
- **Observability:** CloudWatch metrics (consumed capacity, throttles, latency), CloudWatch Contributor Insights for hot keys. No `EXPLAIN` / query plans (access path is implied by key design); no slow-query log in the relational sense.
- **Upgrade story:** Fully managed — no version upgrades, patching, or downtime for the customer. This is the core value proposition.
- **Maturity:** Extremely mature; powers Amazon.com's largest workloads, used at internet scale since 2012. Known failure modes: hot partitions, throttling under skew, surprise costs, and silent LWW conflict loss in MREC global tables. **No public Jepsen report exists.** Reliability claims rest on AWS's own [USENIX ATC 2022 paper](https://www.usenix.org/conference/atc22/presentation/elhemali) and operational track record, not third-party formal verification.

## Ecosystem & people
- **Canonical use cases:** High-scale OLTP with well-known access patterns — shopping carts, session/user state, IoT/event ingestion, gaming leaderboards, serverless app backends. **Anti-patterns:** ad-hoc/analytical queries, anything needing JOINs or flexible querying, relational reporting, workloads with unpredictable access patterns, or large scans — DynamoDB punishes all of these in cost and latency. If you do not know your queries in advance, it is the wrong tool.
- **Drivers / connectors:** First-class AWS SDKs in every language; DynamoDB Streams → Lambda/Kinesis for CDC; Glue/Athena/Redshift and S3 export for analytics; integrations with most BI and dbt-adjacent tooling are export-based, not live. Single-table-design ORMs (e.g. ElectroDB, DynamoDB Toolbox).
- **Community / support:** Large; commercial support via AWS. Docs are thorough. Learning curve is real and inverted from SQL — the hard part is data modeling (single-table design), not operations.

## Licensing & cost
- **License:** Proprietary, **managed-only** — no self-hosted or open-source edition. (DynamoDB Local exists for dev/testing only.) See [license-taxonomy](../concepts/license-taxonomy.md). Heavy **lock-in**: the API, single-table data model, and access patterns do not port to other databases without redesign.
- **Cost model:** Two modes. **On-demand** bills per request (RRU/WRU) — AWS cut on-demand throughput pricing ~50% in Nov 2024 and now recommends it as the default ([pricing](https://aws.amazon.com/dynamodb/pricing/provisioned/)). **Provisioned** bills per RCU/WCU-hour (with auto-scaling and 1/3-year reserved discounts of ~54–77%). Plus storage per GB, streams, backups, and global-table cross-region replication. Cheap at small/spiky scale; can become expensive and hard to predict at sustained high throughput — a frequently cited gotcha. One RCU = 1 strong read/s (or 2 eventual) up to 4 KB; one WCU = 1 write/s up to 1 KB.

## Hardware / deployment
- **Resource profile:** N/A to the user — no servers, RAM, or disk to size. AWS manages all hardware. Performance is a function of key design and provisioned/on-demand capacity, not your hardware.
- **Storage assumptions:** Abstracted; AWS uses SSD-backed storage internally.
- **Footprint:** Serverless, regional service; global tables span regions. No embedded or single-node production deployment (DynamoDB Local is dev-only).
- **Deployment:** SaaS-only, AWS regions. No on-prem, no k8s/StatefulSet — you consume an API endpoint.

## Bottom line
Reach for DynamoDB when you have a high-scale OLTP workload with **known, stable access patterns** and want zero operational burden with predictable single-digit-ms latency — serverless on-demand mode makes it especially attractive for spiky, unpredictable traffic. Do not reach for it if you need ad-hoc queries, JOINs, analytics, or relational flexibility, or if you cannot tolerate hard AWS lock-in. The single biggest gotcha: success or failure is decided at data-modeling time — a bad partition key produces hot partitions, throttling, and cost surprises that no amount of capacity can fully fix.

## Sources
- [Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service — USENIX ATC 2022](https://www.usenix.org/conference/atc22/presentation/elhemali) (the authoritative design paper)
- [DynamoDB Transactions: how it works (AWS docs)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- [How DynamoDB global tables work (AWS docs)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html)
- [Multi-Region strong consistency GA announcement, June 2025 (AWS blog)](https://aws.amazon.com/blogs/aws/build-the-highest-resilience-apps-with-multi-region-strong-consistency-in-amazon-dynamodb-global-tables/)
- [DynamoDB pricing (AWS)](https://aws.amazon.com/dynamodb/pricing/provisioned/)
- [Understanding eventual consistency in DynamoDB — Alex DeBrie](https://www.alexdebrie.com/posts/dynamodb-eventual-consistency/)
