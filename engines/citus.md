---
name: Citus
slug: citus
rank: 116
data_model: Relational (distributed PostgreSQL extension)
license: AGPL-3.0 (copyleft, open source); managed flavor is Azure Cosmos DB for PostgreSQL
summary: A PostgreSQL extension that shards tables across worker nodes for scale-out OLTP and real-time analytics — full Postgres, but atomic-not-isolated across shards.
last_researched: 2026-06-04
confidence: high
---

# Citus

> A PostgreSQL extension (not a fork) that turns Postgres into a shared-nothing sharded cluster — great for multi-tenant SaaS and real-time analytics, but cross-shard transactions are atomic without distributed snapshot isolation.

## Identity
- **Taxonomy / data model:** Relational. Citus is a Postgres *extension*, so it inherits the full Postgres type system and is fully compatible with [postgresql](postgresql.md). Three table kinds: **distributed** (hash-sharded across workers by a distribution column), **reference** (full copy replicated to every node, for small dimension tables / joins), and **local** (ordinary Postgres tables on the coordinator). ([Concepts](https://docs.citusdata.com/en/stable/get_started/concepts.html))
- **Storage model:** Row-store by default (Postgres heap, B-tree indexes; see [lsm-vs-btree](../concepts/lsm-vs-btree.md)). Since Citus 10 it also offers **columnar** table storage with zstd compression (3x–10x ratios, column projection skipping), but columnar tables are append-mostly: no UPDATE/DELETE, no foreign keys, batch load via COPY/INSERT..SELECT only. ([Citus 10 columnar](https://www.citusdata.com/blog/2021/03/06/citus-10-columnar-compression-for-postgres/))
- **Workload:** Pitched at three workloads — multi-tenant SaaS (shard by tenant id), real-time analytics dashboards, and time-series. This is genuine [oltp-olap-htap](../concepts/oltp-olap-htap.md) HTAP via *physical sharding plus optional columnar*: OLTP queries route to a single shard (single-tenant), analytics fan out and parallelize across shards/cores, and columnar storage gives the analytical side compression. The separation mechanism is real (sharding + columnar tables), not a vague claim.

## Distribution & consistency
- **CAP under partition:** CP-leaning in practice. The coordinator holds the cluster metadata (shard placement, node health); writes to a shard whose owning worker is partitioned away fail rather than diverge. Citus is a single-cluster scale-out system, not a multi-region AP store. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PA/EC is not the right frame — Citus does not offer geo-distributed multi-leader tunable consistency. Else-case: cross-shard queries pay coordinator round-trips and 2PC latency for consistency. ⚠️ unverified — no formal PACELC classification published.
- **Default isolation & what's achievable — THE key gotcha:** A single-shard transaction gets full Postgres MVCC ([mvcc](../concepts/mvcc.md)) at the worker's isolation level. But **multi-node transactions are atomic and durable, yet do NOT get distributed snapshot isolation**: remote transactions run at READ COMMITTED, and a multi-shard query can observe a concurrent commit as applied on one node but not yet on another. So "ACID" here means atomic + durable across shards, **not** a globally consistent snapshot. ([Concepts](https://docs.citusdata.com/en/stable/get_started/concepts.html), [How Citus Executes Distributed Transactions](https://www.citusdata.com/blog/2017/11/22/how-citus-executes-distributed-transactions/)) See [isolation-levels](../concepts/isolation-levels.md). A widely cited critique frames this as "not fully ACID / eventually consistent at multi-shard read time" ([dev.to critique](https://dev.to/yugabyte/citus-is-not-acid-but-eventually-consistent-3711)) — accurate for cross-shard *reads*; cross-shard *writes* are still atomic via 2PC.
- **Replication:** Per-node Postgres **streaming replication** for HA (coordinator and each worker get hot standbys; managed tier auto-promotes on failure). Citus's own older shard-level replication (multiple shard copies) exists but is deprecated for HA in favor of streaming replicas. Single-leader per node. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo-style per-query consistency levels.
- **Clock dependency:** No TrueTime/HLC requirement; correctness rests on 2PC + a distributed deadlock detector, not synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema (it is Postgres). DDL on distributed tables is propagated to all shards by the coordinator.
- **Migration/evolution:** Inherits Postgres DDL semantics; `ALTER TABLE` on a distributed table runs across all shards (locking behavior follows Postgres per shard). Choosing/changing a **distribution column** is the painful part — reshaping which column shards a table is not a casual online operation.
- **Type system:** Full Postgres — JSONB, arrays, ranges, PostGIS geospatial, `pgvector`, etc., all work since extensions load alongside Citus.

## Query interface
- **Language:** Standard PostgreSQL SQL — same dialect, drivers, and wire protocol. Most apps need no SQL rewrite beyond choosing distribution columns.
- **Transactions:** Single-shard = full multi-statement ACID. Cross-shard = atomic via **2PC** (`PREPARE TRANSACTION` → `COMMIT PREPARED`) with crash recovery from coordinator metadata, but without a distributed snapshot (see above). ([2PC blog](https://www.citusdata.com/blog/2017/11/22/how-citus-executes-distributed-transactions/))
- **Native vs app-side:** Native distributed joins, aggregations, and window functions — best when joins are co-located on the distribution column or one side is a reference table; cross-shard non-co-located joins may require repartitioning and are slower. Distributed deadlock detector runs as a background worker.
- **Stored procedures / UDFs:** Full Postgres PL/pgSQL and other PLs; functions can be *distributed* and delegated to the worker owning a shard.

## Scaling & topology
- **Horizontal** scale-out: add worker nodes, then rebalance shards (open-source online shard rebalancer since Citus 10). Sharding is **hash-based on a distribution column**, chosen explicitly per table — not automatic; bad distribution-key choice is the classic footgun.
- **Resharding:** Shard count is set at table creation; the rebalancer moves shards between nodes but changing shard count or distribution column is heavyweight.
- **Read replicas:** Per-node Postgres streaming replicas; reads from a hot standby are async and can be stale.
- **Storage/compute separation:** No — shared-nothing local storage per node (each worker stores its shards on its own disks). Not a Snowflake/Aurora-style architecture. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Standard Postgres WAL + fsync per node ([wal-and-durability](../concepts/wal-and-durability.md)); durability and crash-recovery window are per-node Postgres semantics. Distributed commits add 2PC overhead; prepared-transaction state is logged so the coordinator can recover in-flight 2PCs after a crash.
- **Throughput/latency:** Single-shard OLTP ≈ native Postgres; multi-tenant workloads scale near-linearly with workers when queries route to one shard. Analytical queries parallelize across shards and cores. Cross-shard transactions and non-co-located joins add coordinator/2PC tail latency; the coordinator can be a bottleneck for fan-out-heavy workloads.
- **Compaction / vacuum / GC:** Per-node Postgres autovacuum — runs independently on each worker; vacuum/bloat tuning is multiplied across the cluster. Columnar tables avoid row-update bloat but cannot be updated in place.

## Operations & maturity
- **Backup/restore, PITR:** Per-node Postgres `pg_basebackup` / WAL archiving; the managed Azure tier provides automated backups, PITR, and failover.
- **Observability:** Postgres `EXPLAIN` extended for distributed plans, `citus_stat_*` views, plus standard Postgres metrics and slow-query logging.
- **Upgrade story:** Postgres major-version and Citus extension upgrades; day-2 burden is managing N+1 Postgres nodes (vacuum, replicas, failover) rather than one — non-trivial self-managed.
- **Maturity:** Mature, acquired by Microsoft in 2019, ~10+ years of production use, SIGMOD '21 design paper ([Citus: Distributed PostgreSQL for Data-Intensive Applications](https://dl.acm.org/doi/10.1145/3448016.3457551)). Current line is Citus 14.x (14.0.0 released Feb 2026, tracking PostgreSQL 17); 13.0 was the PG17-first release in Feb 2025. **No public Jepsen report exists** — and given the documented lack of distributed snapshot isolation, do not assume serializable cross-shard behavior. ⚠️ unverified — no Jepsen analysis of Citus has been published.

## Ecosystem & people
- **Canonical use cases:** Multi-tenant SaaS sharded by tenant id (the sweet spot — most queries stay single-shard); customer-facing real-time analytics; high-ingest time-series.
- **Anti-patterns:** Workloads needing strong cross-shard serializability or a globally consistent multi-shard snapshot; analytics requiring heavy non-co-located joins across many shards; small databases that fit one Postgres node (sharding is pure overhead); geo-distributed multi-region writes.
- **Drivers / connectors:** Anything that speaks Postgres — psql, all Postgres drivers/ORMs, dbt, Debezium CDC (per node), Kafka, BI tools. No special client needed.
- **Community / support:** Strong Postgres-ecosystem familiarity, good docs, Microsoft commercial support via the managed service. Learning curve is mainly distributed-data-modeling (picking distribution columns, co-location), not new SQL.

## Licensing & cost
- **License:** **AGPL-3.0** — copyleft, fully open source (the entire engine, including the former "enterprise" features, was open-sourced; the rebalancer became OSS in Citus 10). AGPL is more restrictive than permissive Apache/BSD — relevant if you build a hosted service on it. See [license-taxonomy](../concepts/license-taxonomy.md). ([GitHub](https://github.com/citusdata/citus))
- **Self-managed vs managed:** Self-host the AGPL extension on your own Postgres, or use **Azure Cosmos DB for PostgreSQL** (the rebranded Hyperscale/Citus managed service). Lock-in is low for self-managed (it's Postgres); the managed tier ties you to Azure.
- **Cost model:** Self-managed = your infrastructure. Managed = per-node (coordinator + worker vCores/storage); cost scales with node count and grows as you add workers.

## Hardware / deployment
- **Resource profile:** Per-node Postgres — memory + disk bound; working set per shard should ideally fit each worker's RAM for good cache behavior. CPU matters for parallel analytical fan-out.
- **Storage assumptions:** Local disk per node (NVMe/SSD ideal); shared-nothing, so no reliance on network-attached storage semantics.
- **Footprint:** Clustered (coordinator + ≥1 workers); also runs as a **single node** for dev or small deploys (since Citus 10) — useful to start single-node and scale out later.
- **Deployment:** Self-managed on-prem/cloud or k8s, or fully managed on Azure. StatefulSet-style per-node Postgres operational realities apply.

## Bottom line
Reach for Citus when you have a Postgres app that has outgrown one node and your access pattern is naturally shardable — classically multi-tenant SaaS (shard by tenant), real-time analytics, or time-series — and you want to keep full Postgres SQL, types, and tooling. Do **not** reach for it if you need globally serializable cross-shard transactions or a consistent multi-shard snapshot, if your joins span shards unpredictably, or if your data fits comfortably on one Postgres node. The single biggest gotcha: cross-shard transactions are *atomic but not snapshot-isolated* — a multi-shard read can see a transaction half-applied across nodes, so "distributed ACID" here is narrower than it sounds.

## Sources
- [Citus Concepts — official docs](https://docs.citusdata.com/en/stable/get_started/concepts.html)
- [How Citus Executes Distributed Transactions on Postgres (2PC)](https://www.citusdata.com/blog/2017/11/22/how-citus-executes-distributed-transactions/)
- [Citus 10: Columnar, rebalancer, single-node (open source)](https://www.citusdata.com/blog/2021/03/05/citus-10-release-open-source-rebalancer-and-columnar-for-postgres/)
- [Citus 10 brings columnar compression to Postgres](https://www.citusdata.com/blog/2021/03/06/citus-10-columnar-compression-for-postgres/)
- [citusdata/citus on GitHub (license, versions, table types)](https://github.com/citusdata/citus)
- [Critique: "Citus is not ACID but Eventually Consistent"](https://dev.to/yugabyte/citus-is-not-acid-but-eventually-consistent-3711)
