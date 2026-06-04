---
name: Amazon Aurora
slug: amazon-aurora
rank: 44
data_model: Relational
license: Proprietary (managed cloud service; MySQL/PostgreSQL wire- and feature-compatible)
summary: AWS's cloud-native MySQL/PostgreSQL-compatible engine that disaggregates compute from a quorum-replicated, log-structured storage fleet — the safe managed OLTP default on AWS.
last_researched: 2026-06-04
confidence: high
---

# Amazon Aurora

> A managed relational engine that keeps MySQL/PostgreSQL semantics on the front end but replaces the storage layer with a multi-AZ, 6-way quorum-replicated distributed log — buying durability and fast failover at the cost of being locked to AWS.

## When to use

**Use Amazon Aurora if:**
- ✅ You're committed to AWS and want managed MySQL/PostgreSQL with better durability (6-way, 3-AZ quorum), sub-minute failover, and near-real-time read replicas
- ✅ You want cheap copy-on-write clones, continuous PITR, and storage that auto-grows to 256 TiB without provisioning
- ✅ It's a cloud-native OLTP / web / SaaS backend, or a lift-and-shift target for an existing MySQL/PostgreSQL app

**Avoid Amazon Aurora if:**
- ❌ You need write throughput beyond one node — the base engine is single-writer; use Aurora Limitless or [Aurora DSQL](amazon-aurora.md)
- ❌ Your workload is heavy analytics/OLAP (offload to [amazon-redshift](amazon-redshift.md)), or you need multi-cloud / on-prem portability (Aurora is AWS-only)
- ❌ You can't model your I/O — on the Standard tier per-I/O billing can dwarf compute and surprise you at scale (the single biggest gotcha); reads off replicas are also bounded-stale, not strongly consistent

## Identity
- **Taxonomy / data model:** Relational. Two editions: **Aurora MySQL-Compatible** and **Aurora PostgreSQL-Compatible**. The query/transaction engine is the upstream MySQL/PostgreSQL code; only the storage subsystem is replaced. (Distinct from the newer, separate products [Aurora DSQL](amazon-aurora.md) and Aurora PostgreSQL Limitless — see below.)
- **Storage model:** Row-store (InnoDB-derived for MySQL; heap for PostgreSQL) on top of a **log-structured, distributed storage fleet**. The compute node ships only redo-log records to storage; storage nodes materialize pages from the log. Volume is sliced into 10 GB "protection groups," each replicated **6 ways (2 copies × 3 AZs)** ([Aurora SIGMOD 2017 / design overview](https://www.allthingsdistributed.com/2019/03/amazon-aurora-design-cloud-native-relational-database.html)). See [lsm-vs-btree](../concepts/lsm-vs-btree.md) for the log-vs-page contrast; Aurora is closer to "the log is the database."
- **Workload:** OLTP. Not an analytics/HTAP engine on its own — for OLAP you offload via [amazon-redshift](amazon-redshift.md) Zero-ETL or query through external tools. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** for writes. A single writer plus a 4-of-6 write quorum across 3 AZs means writes survive losing an entire AZ (2 copies) plus one more node; reads use a 3-of-6 read quorum ([Aurora under the hood: quorum & correlated failure](https://aws.amazon.com/blogs/database/amazon-aurora-under-the-hood-quorum-and-correlated-failure/)). During writer failover, writes are briefly unavailable (CP behavior). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, prioritizes consistency/durability (refuses or pauses writes). Else (normal operation), the single-writer design gives strong consistency on the writer; reads served from replicas trade latency for staleness (see below). Roughly **PC/EL** for replica reads.
- **Default isolation & what's achievable:** Inherits engine semantics. **Aurora MySQL:** writer defaults to `REPEATABLE READ` (MySQL snapshot semantics); `READ COMMITTED`, `READ UNCOMMITTED`, `SERIALIZABLE` also available ([Aurora MySQL isolation levels](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Reference.IsolationLevels.html)). **Aurora replicas default to `REPEATABLE READ` and cannot take user-level locks**; `READ COMMITTED` on a replica is available via `aurora_read_replica_read_committed` but is **less strict than on the primary** and can return inconsistent results for long queries ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Reference.IsolationLevels.html)). **Aurora PostgreSQL** offers `READ COMMITTED` (default), `REPEATABLE READ` (snapshot), and `SERIALIZABLE` (SSI). See [isolation-levels](../concepts/isolation-levels.md) and [mvcc](../concepts/mvcc.md).
- **Replication:** **Single-leader (one writer)** with up to 15 reader replicas sharing the same storage volume. Replicas do not pull data over a logical replication stream the way classic MySQL/Postgres replicas do — the writer streams redo-log records to readers so they can update in-memory pages; all instances read the *same* underlying quorum volume. Replica lag is therefore typically **<100 ms, often single-digit ms** ([Aurora replication docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Replication.html)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited. No per-query quorum knobs (the quorum is internal). You choose *where* to read (writer = strongly consistent; reader = bounded-stale). **Local write forwarding** lets reader endpoints forward writes to the writer with selectable session consistency levels.
- **Clock dependency:** No TrueTime-style requirement for the single-region engine; ordering comes from the writer's LSN sequence. (The separate Aurora DSQL product does use synchronized time.) See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema (MySQL/PostgreSQL DDL).
- **Migration/evolution:** Same DDL behavior as the underlying engine. Some `ALTER TABLE` operations are online (esp. modern MySQL 8 / Postgres), but many still take metadata or table locks — Aurora does **not** remove the engine's locking-DDL gotchas. Aurora MySQL adds fast DDL for some operations.
- **Type system:** Full MySQL or PostgreSQL type system, including JSON/JSONB, arrays (Postgres), geospatial (PostGIS on Aurora PostgreSQL), and **`pgvector` for vector/embedding search** on Aurora PostgreSQL. See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** SQL — MySQL dialect or PostgreSQL dialect depending on edition. Babelfish for Aurora PostgreSQL adds T-SQL / TDS (SQL Server) wire compatibility.
- **Transactions:** Full multi-statement ACID, same as the host engine.
- **Native vs app-side:** Native joins, secondary indexes, aggregations, window functions, CTEs — everything the underlying MySQL/PostgreSQL provides.
- **Stored procedures / UDFs:** Yes — SQL/PSM (MySQL) or PL/pgSQL and other PLs (PostgreSQL). Aurora also exposes integrations to invoke AWS Lambda and load from/save to S3.

## Scaling & topology
- **Vertical:** resize instance class (or use **Aurora Serverless v2**, which auto-scales compute in fine-grained ACU increments). **Horizontal reads:** up to 15 read replicas sharing storage, all near-real-time.
- **Horizontal writes:** the base engine is **single-writer** — you cannot scale writes by adding nodes. To scale writes you must move to **Aurora PostgreSQL Limitless** (automated sharding across a router/shard topology, PostgreSQL 16-compatible) or the separate **Aurora DSQL** distributed product. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Storage:** auto-grows to **256 TiB per volume** without manual provisioning (raised from 128 TiB for both Aurora MySQL and PostgreSQL in July 2025; [AWS announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-aurora-postgresql-database-clusters-256-tib-storage-volume/)); no manual resharding for the base engine.
- **Read replicas & read consistency:** reads from replicas are bounded-stale (lag metric `AuroraReplicaLag`), not strongly consistent; read-after-write requires the writer endpoint or write forwarding.
- **Storage/compute separation:** This is Aurora's defining feature — compute is stateless over a shared, independently scaled, quorum-replicated storage tier (the Aurora/Neon/Snowflake pattern). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Compute ships **redo-log records only** (no full dirty pages) to 6 storage nodes; a write commits on a **4-of-6 quorum**, so a commit is durable in ≥2 AZs ([quorum design](https://aws.amazon.com/blogs/database/amazon-aurora-under-the-hood-quorum-and-correlated-failure/)). Storage nodes asynchronously coalesce log into pages. This log-only write path is why Aurora claims much higher write throughput than vanilla MySQL on the same instance. **Data-loss window on crash:** effectively zero for committed transactions within the region (committed = quorum-durable). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** AWS markets up to ~5x MySQL / ~3x PostgreSQL throughput; real gains are workload-dependent and largest on write-heavy, fan-out workloads. Crash recovery is fast because there is no redo replay on the compute node — storage rebuilds pages on demand.
- **Compaction/vacuum/GC:** Aurora PostgreSQL still requires **autovacuum** (PostgreSQL MVCC bloat is not eliminated — a real p99/operational concern on high-churn tables). Aurora MySQL inherits InnoDB purge. The distributed storage layer handles its own log GC and segment repair transparently.

## Operations & maturity
- **Backup/restore, PITR:** Continuous, incremental backups to S3; **PITR to any second within the retention window** (typically to within ~5 min of now) at no extra storage charge beyond the backup itself. Fast clone (copy-on-write) for cheap test copies. Snapshots are volume-level.
- **Observability:** CloudWatch metrics, **Performance Insights**, Enhanced Monitoring, slow-query logs, `EXPLAIN`/query plans from the underlying engine, `aurora_replica_status`.
- **Upgrade story:** Managed minor/major version upgrades; **Blue/Green Deployments** for near-zero-downtime major upgrades. Day-2 burden is low relative to self-managed — AWS handles storage repair, patching, failover. Failover to a replica is typically **~30 s or less**; writes are interrupted during promotion.
- **Maturity:** GA since 2015, very large production footprint, one of AWS's flagship databases. **No public Jepsen report exists for Aurora itself** — Aurora's durability/isolation claims rest on AWS docs and the SIGMOD papers, not an independent formal-verification audit. However, the closely related (but *architecturally distinct*) **Amazon RDS for PostgreSQL Multi-AZ cluster** product *was* analyzed by Jepsen (Apr 2025, versions 13.15–17.4): it found Multi-AZ clusters **do not provide Snapshot Isolation**, exhibiting Long Fork and other G-nonadjacent anomalies on read replicas every few minutes under healthy load ([Jepsen: Amazon RDS for PostgreSQL 17.4](https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4)). That report does *not* test Aurora, whose replica architecture differs (shared storage volume rather than streaming logical replicas), but it is a cautionary data point reinforcing that **reads off Aurora replicas are not strongly consistent** — do not assume cross-replica snapshot guarantees. Known sharp edges: replica-read staleness surprises, autovacuum bloat (Postgres), and locking DDL inherited from the engines.

## Ecosystem & people
- **Canonical use cases:** Cloud-native OLTP and web/SaaS backends on AWS that want managed Postgres/MySQL with better durability, fast failover, cheap clones, and read fan-out. Good lift-and-shift target for existing MySQL/PostgreSQL apps.
- **Anti-patterns:** heavy analytics/OLAP (use [amazon-redshift](amazon-redshift.md) / a columnar engine); write-throughput beyond one node (needs Limitless/DSQL or app sharding); multi-cloud or on-prem requirements (Aurora is AWS-only); ultra-low-cost small workloads where plain amazon-rds / self-managed Postgres is cheaper; latency-sensitive read-after-write off replicas.
- **Drivers/connectors:** Standard MySQL/PostgreSQL drivers and ORMs work unchanged; RDS Data API; **Zero-ETL to Redshift and OpenSearch**; CDC via AWS DMS and Postgres logical replication / MySQL binlog; works with dbt, Kafka connectors, and all standard BI tools.
- **Community/support:** Backed by AWS commercial support; excellent AWS docs; learning curve is mostly AWS operational (IAM, VPC, parameter groups) rather than SQL.

## Licensing & cost
- **License:** **Proprietary managed service.** There is no self-hostable Aurora binary — you cannot run it outside AWS. The compatibility layers reuse open-source MySQL/PostgreSQL, but Aurora itself is closed and **managed-only**. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Lock-in:** High at the operational layer (storage, failover, clone, Serverless, Zero-ETL are AWS-specific); **moderate at the data/SQL layer** because wire/SQL compatibility means an app can usually move to self-managed MySQL/PostgreSQL with effort (losing Aurora-specific features).
- **Cost model:** Per-instance-hour (or **per-ACU-hour** for Serverless v2, ~$0.12–0.16/ACU-hr) + storage per-GB-month + backup storage + data transfer. Two storage tiers: **Aurora Standard** (lower storage, but **billed per-I/O at ~$0.20/million requests**) vs **Aurora I/O-Optimized** (no I/O charges, ~2.25x storage and ~25% higher compute) — I/O-Optimized wins when I/O exceeds ~25% of the bill ([I/O-Optimized announcement](https://aws.amazon.com/blogs/aws/new-amazon-aurora-i-o-optimized-cluster-configuration-with-up-to-40-cost-savings-for-i-o-intensive-applications/)). **Gotcha:** on Aurora Standard, per-I/O charges can dominate and surprise at scale. Cross-region Global Database adds replication and per-region instance/storage cost.

## Hardware / deployment
- **Resource profile:** Memory-bound for read performance (buffer pool / page cache hit rate drives latency); the storage tier absorbs I/O. Working set ideally fits in RAM; full dataset need not.
- **Storage assumptions:** Fully managed, network-attached distributed storage across 3 AZs — you do not provision IOPS or disks. NVMe-backed local cache on instances.
- **Footprint:** Clustered managed service only (writer + readers + storage fleet). **Aurora Serverless v2** is the auto-scaling/scale-to-low option. Not embedded, not single-binary.
- **Deployment:** SaaS on AWS only (no on-prem, no k8s self-host). Multi-AZ by default; **Aurora Global Database** adds cross-region replicas with typical **RPO ~1 s and RTO ~1 min** for DR ([Aurora HA/DR whitepaper](https://d1.awsstatic.com/Amazon%20Aurora%20High%20Availability%20and%20Disaster%20Recovery%20Features%20for%20Global%20Resilience%20Whitepaper.pdf)).

## Bottom line
Reach for Aurora when you're committed to AWS and want managed MySQL/PostgreSQL with materially better durability, sub-minute failover, near-real-time read replicas, and cheap copy-on-write clones — it's the safe managed OLTP default on AWS. Do **not** reach for it if you need write scale-out beyond one node (look at Aurora Limitless or [Aurora DSQL](amazon-aurora.md)), heavy analytics, or any non-AWS portability. The single biggest gotcha is cost: on the Standard tier, per-I/O billing can dwarf compute on busy workloads — model your I/O and consider I/O-Optimized before you're surprised by the bill.

## Sources
- [Amazon Aurora ascendant: how we designed a cloud-native relational database (All Things Distributed)](https://www.allthingsdistributed.com/2019/03/amazon-aurora-design-cloud-native-relational-database.html)
- [Aurora under the hood: quorum and correlated failure (AWS)](https://aws.amazon.com/blogs/database/amazon-aurora-under-the-hood-quorum-and-correlated-failure/)
- [Aurora MySQL isolation levels (AWS docs)](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Reference.IsolationLevels.html)
- [Replication with Amazon Aurora (AWS docs)](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Replication.html)
- [Aurora I/O-Optimized cluster configuration (AWS)](https://aws.amazon.com/blogs/aws/new-amazon-aurora-i-o-optimized-cluster-configuration-with-up-to-40-cost-savings-for-i-o-intensive-applications/)
- [Amazon Aurora pricing](https://aws.amazon.com/rds/aurora/pricing/)
- [Aurora HA and DR for Global Resilience (AWS whitepaper)](https://d1.awsstatic.com/Amazon%20Aurora%20High%20Availability%20and%20Disaster%20Recovery%20Features%20for%20Global%20Resilience%20Whitepaper.pdf)
- [Jepsen: Amazon RDS for PostgreSQL 17.4](https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4) (RDS Multi-AZ, *not* Aurora — adjacent cautionary result)
- [Aurora 256 TiB storage volume announcement (AWS)](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-aurora-postgresql-database-clusters-256-tib-storage-volume/)
- [Aurora PostgreSQL Limitless Database architecture (AWS docs)](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/limitless-architecture.html)
