---
name: Google Cloud Spanner
slug: google-cloud-spanner
rank: 94
data_model: Relational
license: Proprietary (managed cloud service; downloadable Spanner Omni for self-hosting, also proprietary)
summary: Google's globally-distributed relational DB that delivers strict serializability across regions using TrueTime synchronized clocks; CP, expensive, and lock-in heavy.
last_researched: 2026-06-04
confidence: high
---

# Google Cloud Spanner

> A horizontally-scalable relational database that gives you external consistency (strict serializability) across continents by betting correctness on GPS/atomic-clock-synchronized time — at the price of cloud lock-in and a high floor cost.

## Identity
- **Taxonomy / data model:** Distributed relational (SQL). Also exposes a [postgresql](postgresql.md)-dialect interface (PostgreSQL interface) and a GoogleSQL dialect. Supports interleaved tables for parent-child locality. Has bolt-on graph (Spanner Graph / GQL) and vector-search capabilities, making it loosely multi-model, but the core is relational.
- **Storage model:** Row-oriented, [LSM-tree](../concepts/lsm-vs-btree.md)-based storage on Google's Colossus distributed filesystem (the same lineage as Bigtable). Data is range-partitioned into "splits" by primary key. See [storage-compute-separation](../concepts/storage-compute-separation.md) — compute (Spanner servers) is decoupled from storage (Colossus).
- **Workload:** OLTP-first, globally distributed. Increasingly positioned for [HTAP](../concepts/oltp-olap-htap.md) via a built-in columnar engine ("Spanner Data Boost" / columnar accelerator) and federation with BigQuery; the physical separation is a separate columnar representation/accelerator, not just a marketing label, though analytical maturity lags dedicated OLAP engines. Treat heavy analytics as a federation-to-BigQuery story, not native.

## Distribution & consistency
- **CAP under partition:** **CP.** Spanner chooses consistency over availability; a minority partition that loses Paxos quorum cannot accept writes. Google argues that because it runs on a private, highly-redundant network, partitions are rare enough that it "effectively" delivers high availability, but this is an operational argument, not a CAP exemption ([Google: "Spanner, TrueTime and the CAP Theorem"](https://research.google/pubs/spanner-truetime-and-the-cap-theorem/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EC** — under partition it sacrifices availability for consistency; in normal operation it also favors consistency (and pays cross-region latency) over latency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** Default is **serializable**, and specifically **external consistency = strict serializability** (the strongest practical guarantee — serializable plus real-time ordering) ([Spanner isolation levels](https://docs.cloud.google.com/spanner/docs/isolation-levels), [TrueTime & external consistency](https://docs.cloud.google.com/spanner/docs/true-time-external-consistency)). A weaker **Repeatable Read** level (implemented via snapshot isolation, susceptible to write skew) was added to reduce abort rates under contention ([isolation levels](https://docs.cloud.google.com/spanner/docs/isolation-levels)). Read-only transactions and bounded/exact stale reads execute lock-free against an [MVCC](../concepts/mvcc.md) snapshot. This is a rare case where the "ACID, strongly consistent" marketing is literally accurate. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Synchronous, **Paxos-based** per split. Each split's replica set elects a leader; writes go to the leader, which logs and forwards in parallel to voting replicas and commits when a quorum votes ([Spanner replication](https://docs.cloud.google.com/spanner/docs/replication)). See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md), [replication-models](../concepts/replication-models.md). Failover is automatic via Paxos leader re-election; split-brain is prevented by quorum.
- **Tunable consistency?** Limited: you choose strong reads vs. bounded-staleness/exact-staleness reads, and the isolation level (serializable vs repeatable read). There is no Dynamo-style per-query R/W quorum knob — quorum is internal.
- **Clock dependency:** **Yes — central to correctness.** TrueTime exposes time as an interval `[earliest, latest]` bounded by GPS and atomic clocks; commit timestamps wait out the uncertainty ("commit wait") so external consistency holds. If clock uncertainty exceeds bounds, Spanner blocks rather than risk incorrectness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** Rigid, typed relational schema with primary keys; "schemaless" is not on offer.
- **Migration/evolution:** Online, non-blocking schema changes for most DDL (add column, add index) — index backfills run in the background; some changes have validation phases. Generally no table-locking `ALTER` for common operations.
- **Type system:** Standard SQL scalar types, `ARRAY`, `STRUCT`, `JSON`, `NUMERIC`, timestamps, and native `vector`/embedding support with ANN indexing; geospatial support is limited compared to [postgresql](postgresql.md)/PostGIS. ⚠️ unverified — exact extent of native geospatial functions.

## Query interface
- **Language:** SQL in two dialects — **GoogleSQL** and a **PostgreSQL-dialect** interface (a subset of Postgres, not full wire-compatibility with all extensions). Also DML and a Read/Mutation API. **Spanner Graph** adds GQL/openCypher-style graph queries over relational tables.
- **Transactions:** Full multi-statement, distributed **ACID** transactions across rows, tables, and splits (cross-region). This is Spanner's headline feature.
- **Native vs app-side:** Native secondary indexes (global and interleaved/local), joins, aggregations, and window functions execute server-side with a distributed query planner.
- **Stored procedures / UDFs:** Historically weak — limited stored-procedure support. ⚠️ unverified — current state of UDF/stored-proc support; check docs for the latest.

## Scaling & topology
- **Vertical vs horizontal:** **Horizontal, automatic.** Capacity is provisioned in nodes or sub-node "processing units" (1000 PU = 1 node); Spanner auto-shards data into splits and rebalances them based on load/size with no manual resharding ([pricing/compute](https://cloud.google.com/spanner/pricing)). This automatic, painless resharding is the key differentiator vs. manually-sharded relational setups.
- **Sharding/partitioning:** Range partitioning by primary key. **Gotcha:** monotonically increasing keys (timestamps, sequential IDs) create write hotspots on a single split — you must hash/reverse keys, a real day-1 design constraint.
- **Read replicas & consistency:** Read-write, read-only, and witness replica types. Read-only replicas serve strong reads (globally consistent) or stale reads; all read paths can return up-to-date data because replication is synchronous.
- **Storage/compute separation:** Yes — Spanner servers compute over data in Colossus. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Writes are Paxos-replicated to a quorum and persisted to Colossus (WAL-style logging); commit returns only after quorum durability, so the **data-loss window on commit is effectively zero** for acknowledged writes. Commit-wait adds a few ms of latency to bound timestamp uncertainty. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Scales linearly with nodes for well-distributed keys. Cross-region writes pay inter-region RTT (commit must reach a quorum that may span regions) — multi-region write latency is materially higher than single-region. p99 is sensitive to hotspots and lock contention; the repeatable-read level exists partly to tame tail latency under contention. Per-node guidance historically ~10k QPS reads / ~2k QPS writes as a rough planning figure. ⚠️ unverified — current per-node throughput figures; treat as approximate.
- **Compaction / GC:** LSM compaction and MVCC garbage collection run in the background on Colossus; version GC reclaims old MVCC versions after a retention window (default ~1 hour, configurable up to days). Long stale-read windows increase storage. Compaction is managed by Google — not a customer-tuned knob.

## Operations & maturity
- **Backup/restore, PITR:** Managed backups, backup scheduling, and **point-in-time recovery** via version retention (configurable up to ~7 days). Restore can be fast via backup pointers.
- **Observability:** Cloud Monitoring metrics, query plans (`EXPLAIN`/`EXPLAIN ANALYZE`), query insights, lock/transaction stats tables, and CPU/latency dashboards. Strong, fully-managed observability.
- **Upgrade story:** Fully managed; Google handles patching/upgrades with **no customer downtime** and no maintenance windows for the engine itself. Day-2 burden is mostly schema/hotspot design and cost management, not ops.
- **Maturity:** Production at Google since ~2012 (powers AdWords, Play, etc.), GA as Cloud Spanner since 2017. Battle-tested. **Jepsen:** Google has not published an official Jepsen report; an internal/intern project ([googleinterns/jepsen-on-spanner](https://github.com/googleinterns/jepsen-on-spanner)) built Jepsen-style tests checking linearizability/external consistency, but there is no independent Jepsen analysis with the rigor of those for [cockroachdb](cockroachdb.md)/[mongodb](mongodb.md). ⚠️ unverified — no public third-party Jepsen verdict; correctness claims rest on Google's own papers and design.

## Ecosystem & people
- **Canonical use cases:** Global OLTP needing strong consistency at scale — financial ledgers, inventory, gaming, regulated systems spanning regions; workloads that have outgrown a single [postgresql](postgresql.md)/[mysql](mysql.md) instance but cannot tolerate eventual consistency.
- **Anti-patterns:** Small/single-region apps (huge cost floor vs. managed Postgres), analytics-heavy/scan-heavy workloads (use BigQuery), write-hot sequential-key workloads, latency-critical apps that can't absorb cross-region commit waits, and anyone needing portability/no lock-in.
- **Drivers/connectors:** Official client libraries (Java, Go, Python, Node, C#, etc.), JDBC, the PostgreSQL-dialect interface enabling some Postgres tooling, dbt adapter, Dataflow/Kafka connectors, and CDC via change streams. Spanner change streams feed Kafka/BigQuery/PubSub.
- **Community/support:** Closed-source, so no community contribution; backed by Google Cloud support and solid docs. Smaller practitioner community than [postgresql](postgresql.md); learning curve centers on key design and cost modeling.

## Licensing & cost
- **License:** **Proprietary.** No open-source core. The flagship product is a Google Cloud managed service, but **Spanner Omni** is a downloadable, customer-deployable build of Spanner that runs on-premises, on AWS (EKS/EC2), on GKE, and even on a laptop — self-managed by the customer, though still proprietary/licensed, not open source ([Spanner Omni overview](https://docs.cloud.google.com/spanner-omni/overview)). See [license-taxonomy](../concepts/license-taxonomy.md) (proprietary end of the spectrum; Omni is downloadable-proprietary, not source-available).
- **Self-managed vs managed:** Primarily managed; Omni now offers a self-managed/on-prem/multi-cloud option (e.g. for hot/cold failover off Google Cloud). Lock-in is still high — TrueTime, APIs, and operational semantics are Google-specific, and SQL portability is only partial via the Postgres interface — but Omni reduces the hard "managed-only" off-ramp problem.
- **Cost model:** Per **compute** (nodes / processing units, billed by node-hour, sub-node granularity available), plus storage per GB-month, plus network/replication egress for multi-region. Intra-region replication is free; cross-region replication is billed on data volume ([pricing](https://cloud.google.com/spanner/pricing)). **Behavior at scale:** historically expensive at the low end (a full node was a high monthly floor), softened by granular processing units; still pricey relative to managed Postgres, but scales predictably. SLA: **99.999%** multi-region, **99.99%** single-region ([replication docs](https://docs.cloud.google.com/spanner/docs/replication)).

## Hardware / deployment
- **Resource profile:** Abstracted — you buy nodes/processing units, not RAM/CPU/disk. Working set need not fit in RAM (data lives in Colossus); performance still benefits from cache locality.
- **Storage assumptions:** Runs on Google's Colossus (network-attached distributed storage) over Google's private global network — the low-latency, high-redundancy network is what makes its CP/availability story viable.
- **Footprint:** Clustered, fully managed in the GCP service; granular instances allow small starting footprints. **Spanner Omni** adds a self-deployable footprint (on-prem Linux, AWS EC2/EKS, GKE, even a laptop). No open-source embedded mode like SQLite/DuckDB.
- **Deployment:** Google Cloud SaaS for the managed product; **Spanner Omni** enables customer-operated deployment on-prem and on AWS/GKE (proprietary download) ([Spanner Omni overview](https://docs.cloud.google.com/spanner-omni/overview)). Apps connect from anywhere including GKE.

## Bottom line
Reach for Spanner when you genuinely need **horizontally-scalable relational OLTP with strict serializability across regions** and are willing to commit to Google's stack (largely inside Google Cloud, with Spanner Omni now offering a self-managed/on-prem/AWS escape hatch) — it is one of very few systems that deliver externally-consistent distributed transactions, and it does so with near-zero ops. Do not reach for it for small apps (cost floor), analytics (use BigQuery), or if portability/no-lock-in matters. The single biggest gotcha: **primary-key design** — monotonic keys create write hotspots that silently cap throughput, and correctness rests on TrueTime, a Google-internal capability you cannot reproduce elsewhere.

## Sources
- [Spanner: TrueTime and external consistency (official docs)](https://docs.cloud.google.com/spanner/docs/true-time-external-consistency)
- [Spanner isolation levels (official docs)](https://docs.cloud.google.com/spanner/docs/isolation-levels)
- [Spanner replication (official docs)](https://docs.cloud.google.com/spanner/docs/replication)
- [Spanner, TrueTime and the CAP Theorem (Google Research)](https://research.google/pubs/spanner-truetime-and-the-cap-theorem/)
- [Cloud Spanner pricing](https://cloud.google.com/spanner/pricing)
- [Strict Serializability and External Consistency in Spanner (Google Cloud Blog)](https://cloud.google.com/blog/products/databases/strict-serializability-and-external-consistency-in-spanner)
- [jepsen-on-spanner (Google interns project)](https://github.com/googleinterns/jepsen-on-spanner)
