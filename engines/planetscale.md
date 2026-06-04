---
name: PlanetScale
slug: planetscale
rank: 142
data_model: Relational (MySQL via Vitess; Postgres)
license: Proprietary managed service (built on Apache-2.0 Vitess for MySQL; "Neki" sharding for Postgres is proprietary, planned open-source)
summary: Managed, horizontally sharded MySQL on Vitess (now also Postgres) with Git-style schema branching and non-blocking online DDL — scale and DX at the cost of an opinionated, foreign-key-hostile, paid-only platform.
last_researched: 2026-06-04
confidence: high
---

# PlanetScale

> Fully managed MySQL-on-[Vitess] (and now Postgres) that turns schema changes into reviewable, non-blocking "deploy requests" and gives you Git-like database branching — best for teams that have outgrown a single MySQL node and value workflow over raw flexibility.

## When to use

**Use PlanetScale if:**
- ✅ You run MySQL (or now Postgres) at a scale where a single node hurts and want managed Vitess sharding
- ✅ You value a reviewable, non-blocking, branch-based schema-change workflow (deploy requests with safe revert)
- ✅ You want Git-like database branching and CI for the database
- ✅ You have high-connection serverless/edge apps (HTTP driver, Vercel/Cloudflare Workers integrations)

**Avoid PlanetScale if:**
- ❌ Your app depends on cross-shard transactions, cross-shard foreign keys, or heavy ad-hoc cross-shard joins — once sharded, the "it's just MySQL/ACID" model breaks (cross-shard atomicity is best-effort or 2PC-without-isolation)
- ❌ It's a hobby/tiny project — it is paid-only (the free Hobby tier was removed in April 2024)
- ❌ You need analytics/OLAP — no columnar store, no HTAP
- ❌ You need superuser/extension freedom or scan-heavy query patterns — row-read billing can surprise unindexed workloads

## Identity
- **Taxonomy / data model:** Relational. Two engines: (1) the original MySQL service built on **Vitess** (the YouTube-born MySQL sharding/clustering layer), and (2) **PlanetScale for Postgres** (GA in 2025), with a next-gen Postgres sharding layer called **Neki** ([InfoQ, Oct 2025](https://www.infoq.com/news/2025/10/planetscale-metal-postgres/), [PlanetScale Postgres GA](https://planetscale.com/blog/planetscale-for-postgres-is-generally-available)).
- **Storage model:** Row-store. MySQL engine uses InnoDB (B-tree, see [lsm-vs-btree](../concepts/lsm-vs-btree.md)); Postgres engine uses PostgreSQL's heap + B-tree. **PlanetScale Metal** runs the database on local NVMe drives ("unlimited IOPS") rather than network-attached block storage, trading EBS-style durability semantics for latency ([PlanetScale Metal](https://planetscale.com/benchmarks/vitess)).
- **Workload:** OLTP. Not an analytics engine — no columnar store, no HTAP claim. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP per shard. Each shard is a single-primary MySQL replication group; on partition the shard's primary side stays writable and the cut-off replicas serve stale reads or are fenced. Vitess relies on a leader per shard, so writes to an isolated minority stop. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PC/EC in the common single-shard path (primary serves consistent reads); EL if you opt into replica reads, which are asynchronous and can lag. Cross-shard reads/writes weaken this further (below).
- **Default isolation & what's achievable:** Within a single shard you get MySQL's default **REPEATABLE READ** (snapshot-style, see [isolation-levels](../concepts/isolation-levels.md) and [mvcc](../concepts/mvcc.md)). **Across shards there is no global isolation.** Vitess offers best-effort multi-shard commit (partial commits possible on failure) and an optional **two-phase-commit** mode that gives cross-shard *atomicity* but still **not isolation** — other clients can observe partial commits across shards ([Vitess two-phase commit](https://vitess.io/docs/reference/features/two-phase-commit/), [Vitess distributed transactions](https://vitess.io/docs/22.0/reference/features/distributed-transaction/)). Treating PlanetScale as "ACID like one MySQL" is only true while you stay on one shard.
- **Replication:** Single-leader async MySQL replication per shard (semi-sync available); failover is automated via Vitess orchestration with primary election. See [replication-models](../concepts/replication-models.md). Split-brain is bounded by single-primary-per-shard fencing.
- **Tunable consistency?** Coarse: you choose primary vs. replica routing per connection/query; replica reads are eventually consistent. No Dynamo-style per-query quorum.
- **Clock dependency:** No TrueTime/HLC-style clock-bound correctness; ordering is per-shard via MySQL replication. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid relational schema (both MySQL and Postgres engines).
- **Migration / online DDL:** This is the headline feature. Schema changes go through **branches + deploy requests**: you branch the schema, alter it, request review, and merge with non-blocking online DDL (Vitess uses VReplication / gh-ost-style ghost-table migrations, so `ALTER` does not lock the table) ([how online schema change works](https://planetscale.com/docs/vitess/schema-changes/how-online-schema-change-tools-work)). Includes safe revert.
- **Type system:** Standard MySQL types (JSON, generated columns, spatial) or PostgreSQL types depending on engine. Native JSON on MySQL; richer types (arrays, ranges, native vectors via pgvector) on the Postgres side.
- **Caveat — foreign keys:** Historically PlanetScale **did not support foreign keys** because they break ghost-table online migrations ([challenges of FK constraints](https://planetscale.com/blog/challenges-of-supporting-foreign-key-constraints)). FKs are now supported but **only on unsharded/single-shard databases**; sharded FK support is not available ([FK GA](https://planetscale.com/blog/foreign-key-constraints-are-now-generally-available)). Apps designed for sharding must enforce referential integrity in application code.

## Query interface
- **Language:** Standard MySQL dialect (Vitess engine) or PostgreSQL dialect — wire-compatible, so existing drivers/ORMs work. PlanetScale also ships an HTTP/serverless driver (`@planetscale/database`) for edge/Workers environments.
- **Transactions:** Full multi-statement ACID **within a shard**; cross-shard transactions are best-effort or 2PC-atomic-but-not-isolated (see Distribution).
- **Native vs app-side:** Single-shard joins/aggregations/window functions run natively in MySQL/Postgres. **Cross-shard joins** are supported by Vitess's query planner but with real limits — complex cross-shard joins and aggregations can scatter-gather, be slow, or be unsupported; design for shard-local queries.
- **Stored procedures / UDFs:** MySQL stored routines and Postgres functions are constrained on the managed platform; Vitess does not fully support all stored-procedure semantics. Verify per feature.

## Scaling & topology
- **Vertical and horizontal.** Horizontal scaling is via Vitess **sharding** by a vindex (sharding key). Sharding is a deliberate operation, not automatic; **resharding** is an online VReplication-based workflow (PlanetScale automates it) but choosing a bad shard key is the classic pain point. Postgres sharding is to be handled by **Neki**, which is still in active development with design partners (not yet GA) and which PlanetScale has stated it will open-source when production-ready ([Announcing Neki](https://planetscale.com/blog/announcing-neki), [Neki](https://planetscale.com/neki)).
- **Read replicas:** Yes; reads from replicas are asynchronous/eventually consistent. Routing is explicit.
- **Storage/compute separation:** Not the Aurora/Neon model. PlanetScale Metal explicitly uses **local NVMe** attached to compute rather than separated network storage — the opposite design choice, optimizing IOPS/latency over independent scaling. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** InnoDB redo log + binlog (MySQL) or WAL (Postgres); see [wal-and-durability](../concepts/wal-and-durability.md). Durability depends on `sync_binlog`/`innodb_flush_log_at_trx_commit` and on replication acknowledgment. With async replication, a primary crash before replica catch-up has a small **data-loss window**; semi-sync narrows it. ⚠️ unverified — exact default fsync/semi-sync settings on the managed platform are not publicly documented in detail.
- **Throughput / latency:** Strong single-node and per-shard throughput; Metal's local NVMe targets low p99 by removing network-storage I/O variance ([Metal benchmarks](https://planetscale.com/benchmarks/vitess)). The Vitess proxy (vtgate) adds connection pooling that helps serverless/connection-storm workloads but adds a hop.
- **Compaction / vacuum / GC:** InnoDB purge / Postgres autovacuum apply as usual; online DDL via ghost tables adds background copy load and temporary 2x storage during a migration. p99 can spike during large table migrations or resharding.

## Operations & maturity
- **Backup/restore, PITR:** Automated backups and point-in-time recovery on paid plans; branches can be created from production data.
- **Observability:** Built-in query insights / "Query Insights" (per-query latency, row reads/writes), slow-query surfacing, `EXPLAIN`, and Vitess metrics. Boxed billing metric is **rows read** — query patterns that scan rows are expensive and observable.
- **Upgrade story:** Fully managed; PlanetScale handles version upgrades and failover with minimal/zero downtime. Day-2 burden is low *if* you accept the platform's constraints (no arbitrary superuser, opinionated migration flow).
- **Maturity:** Vitess is battle-tested at hyperscale (YouTube, Slack, GitHub, Square). No public **Jepsen** report exists for PlanetScale/Vitess; do not infer formal cross-shard consistency guarantees beyond what Vitess docs state. ⚠️ unverified — no independent formal-verification report found. Known failure modes: bad shard-key choice, cross-shard transaction surprises, FK limitations.

## Ecosystem & people
- **Canonical use cases:** MySQL/Postgres apps that need horizontal scale and a safe, reviewable schema-change workflow; teams wanting branching/CI for the database; high-connection serverless apps (HTTP driver). 
- **Anti-patterns:** Hobby/tiny projects (paid-only, see cost); apps that lean on cross-shard transactions, cross-shard FKs, or heavy ad-hoc cross-shard joins; analytics/OLAP; workloads needing superuser/extension freedom or unusual MySQL features.
- **Connectors:** Standard MySQL/Postgres drivers and ORMs (Prisma, Drizzle, Rails, etc.); CDC via binlog (Debezium/Kafka); dbt and BI tools via standard SQL; first-class Vercel/Cloudflare Workers integrations.
- **Community / support:** Strong docs, active engineering blog; commercial support on paid plans; Vitess has a large CNCF community. Learning curve: low for single-node MySQL users, real for sharding.

## Licensing & cost
- **License:** The **service is proprietary/managed**. The MySQL engine is built on **Vitess (Apache 2.0, CNCF)**; the Postgres sharding layer **Neki is currently proprietary/closed and still in development**, with PlanetScale's stated intent to open-source it once it is production-tested ([Announcing Neki](https://planetscale.com/blog/announcing-neki), [InfoQ](https://www.infoq.com/news/2025/10/planetscale-metal-postgres/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Managed-only:** No self-hosted PlanetScale (you can self-host open-source Vitess separately, which is a different product/effort). Lock-in is moderate: standard wire protocols ease exit, but the branching/deploy-request workflow and metering are platform-specific.
- **Cost model:** Usage + plan based, metered notably on **rows read/written** and storage, plus per-cluster compute. PlanetScale **removed its free "Hobby" tier in April 2024** amid layoffs ([The Register, Mar 2024](https://www.theregister.com/2024/03/11/planetscale_lays_off_staff_and/), [Hobby deprecation FAQ](https://planetscale.com/docs/plans/hobby-plan-deprecation-faq)), drawing heavy criticism. Pricing has since shifted: the cheapest MySQL/Scaler plan is around **$29–39/mo** (in flux), **PlanetScale Postgres single-node starts at ~$5/mo**, and **Metal starts at ~$50/mo** (M-10) ([Postgres GA](https://planetscale.com/blog/planetscale-for-postgres-is-generally-available), [$50 Metal is GA for Postgres](https://planetscale.com/blog/50-dollar-planetscale-metal-is-ga-for-postgres)). As of the live pricing page (mid-2026) there is **no free tier** — PlanetScale's own support docs and pricing page list only paid plans plus Enterprise ([pricing](https://planetscale.com/pricing)). ⚠️ unverified — some third-party sites reference a reinstated "PlanetScale forever" free plan; this is not reflected on the official pricing page, so treat as unconfirmed. At scale, row-read billing can surprise unindexed/scan-heavy workloads.

## Hardware / deployment
- **Resource profile:** Disk-I/O- and CPU-bound; Metal is designed so workloads hit CPU before exhausting local-NVMe I/O. Working set should fit in buffer pool for good p99 but full dataset need not fit in RAM.
- **Storage assumptions:** Metal = **local NVMe** (high IOPS, latency-optimized); non-Metal tiers use cloud block storage. Runs on AWS and GCP regions.
- **Footprint:** Clustered managed cloud service (vtgate proxy + per-shard MySQL/Postgres). Not embedded, not self-serverless-scale-to-zero in the Neon sense.
- **Deployment:** SaaS only. Edge/serverless access via HTTP driver; integrations with Vercel and Cloudflare Workers. No customer-run k8s/StatefulSet (that would be self-hosted Vitess instead).

## Bottom line
Reach for PlanetScale if you run MySQL (or now Postgres) at a scale where a single node hurts, and you value a reviewable, non-blocking, branch-based schema-change workflow and managed Vitess sharding more than raw database flexibility. Do **not** pick it for hobby projects (paid-only), for apps that depend on cross-shard transactions / foreign keys / ad-hoc cross-shard joins, or for analytics. The single biggest gotcha: the moment your data is sharded, the comfortable "it's just MySQL/ACID" mental model breaks — cross-shard atomicity is best-effort or 2PC-without-isolation, and foreign keys don't span shards.

## Sources
- [PlanetScale for Postgres is now GA](https://planetscale.com/blog/planetscale-for-postgres-is-generally-available)
- [InfoQ: PlanetScale extends to PostgreSQL (Metal, Neki), Oct 2025](https://www.infoq.com/news/2025/10/planetscale-metal-postgres/)
- [PlanetScale Metal benchmarks](https://planetscale.com/benchmarks/vitess)
- [Vitess: Two-Phase Commit](https://vitess.io/docs/reference/features/two-phase-commit/)
- [Vitess: Distributed Transactions](https://vitess.io/docs/22.0/reference/features/distributed-transaction/)
- [Vitess: MySQL compatibility](https://vitess.io/docs/22.0/reference/compatibility/mysql-compatibility/)
- [PlanetScale: challenges of supporting foreign key constraints](https://planetscale.com/blog/challenges-of-supporting-foreign-key-constraints)
- [PlanetScale: foreign key constraints GA](https://planetscale.com/blog/foreign-key-constraints-are-now-generally-available)
- [PlanetScale: how online schema change tools work](https://planetscale.com/docs/vitess/schema-changes/how-online-schema-change-tools-work)
- [PlanetScale: Hobby plan deprecation FAQ](https://planetscale.com/docs/plans/hobby-plan-deprecation-faq)
- [The Register: PlanetScale ends free tier and cuts staff, Mar 2024](https://www.theregister.com/2024/03/11/planetscale_lays_off_staff_and/)
- [Vitess: Shard Isolation and Atomicity Model](https://vitess.io/docs/20.0/user-guides/configuration-advanced/shard-isolation-atomicity/)
- [PlanetScale: Announcing Neki (Postgres sharding)](https://planetscale.com/blog/announcing-neki)
- [PlanetScale pricing](https://planetscale.com/pricing)
