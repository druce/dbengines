---
name: Neon
slug: neon
adjacent: true
rank: n/a
category: relational
data_model: Relational (serverless Postgres)
license: Apache 2.0 (permissive; OSS) + Neon managed cloud (Databricks, proprietary)
summary: Serverless Postgres that disaggregates storage from compute — real Postgres on a multi-tenant log-structured storage engine (Paxos-quorum safekeepers + pageserver on S3), giving scale-to-zero, autoscaling, and instant copy-on-write branching; Apache-2.0, Databricks-owned since 2025.
last_researched: 2026-06-04
confidence: medium
---

# Neon

> **Serverless Postgres with storage and compute pulled apart.** The compute is unmodified, stateless Postgres; durability and history live in a separate multi-tenant storage layer (a Paxos-quorum WAL service plus a pageserver that materializes pages on demand and tiers to object storage). That split buys **scale-to-zero**, independent autoscaling, and **instant copy-on-write database branching** — at the cost of network page-fetch latency and a cold-start. It is real Postgres, so it inherits [postgresql](postgresql.md)'s SQL, semantics, and extensions.

## When to use

**Use Neon if:**
- ✅ You want **serverless Postgres that scales to zero** (pay ~nothing when idle) and autoscales on load — ideal for dev/preview environments, spiky or bursty apps, per-tenant databases, and **AI-agent-provisioned** databases (a headline Neon use case — most of its databases are created by agents).
- ✅ You want **instant, copy-on-write [branching](https://neon.com/docs/introduction/architecture-overview)** of a production-sized database for CI, previews, and testing **without copying data** (a branch is a metadata pointer into the parent's WAL history).
- ✅ You want **real Postgres compatibility** (wire protocol, extensions, `pgvector`) without operating storage, HA, backups, or PITR yourself.

**Avoid Neon if:**
- ❌ Your workload is **steady, high-throughput, and never idles** — scale-to-zero gives no benefit, and disaggregated storage adds page-fetch latency versus local NVMe; a provisioned [amazon-aurora](amazon-aurora.md)/RDS or self-hosted [postgresql](postgresql.md) can be cheaper and faster.
- ❌ You need **cold-start-free tail latency** — a scaled-to-zero endpoint pays a (sub-second but nonzero) cold start on the next connection, and a cold pageserver cache adds first-touch page-fetch latency. This is the biggest gotcha.
- ❌ You need **on-prem simplicity or write scale-out** — the OSS is operationally heavy (pageserver + safekeepers + object store), so in practice you take the managed service (cloud lock-in / Databricks), and writes are still **single-primary** (no built-in horizontal write sharding — use [citus](citus.md) or a distributed-SQL engine for that).

## Identity
- **Taxonomy / data model:** **Relational — it *is* Postgres.** The compute node runs standard Postgres, so the data model, SQL dialect, type system, and extension ecosystem are [postgresql](postgresql.md)'s. The novelty is entirely in the storage layer.
- **Storage model:** **disaggregated / log-structured.** Three layers ([architecture](https://neon.com/docs/introduction/architecture-overview)): **compute** (stateless Postgres, no local durable state); **safekeepers** (a redundant WAL service that durably holds WAL via a **Paxos-based consensus** quorum); and the **pageserver** (consumes WAL, slices it per-relation/per-page, materializes page versions on demand, and tiers cold data to **object storage** — "bottomless" storage). See [storage-compute-separation](../concepts/storage-compute-separation.md), [wal-and-durability](../concepts/wal-and-durability.md).
- **Workload:** OLTP (Postgres). Not an analytics warehouse on its own, though Databricks positions it as **"Lakebase"** — an operational Postgres paired with the lakehouse. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** the **storage** layer is **CP-leaning for commit** — a transaction is committed only once a **quorum of safekeepers acknowledges the WAL** via Paxos ([architecture](https://neon.com/docs/introduction/architecture-overview)); the compute is a single-primary Postgres. See [cap-pacelc](../concepts/cap-pacelc.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **PACELC:** ⚠️ unverified — no published PACELC; in practice Else-favors-latency for reads (page fetches), with commit gated on the safekeeper quorum.
- **Default isolation & what's achievable:** **identical to [postgresql](postgresql.md)** — default **read committed**, real **serializable** via SSI — because it runs actual Postgres. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** WAL is streamed to the **safekeeper Paxos quorum** for durability; read replicas spin up from the pageserver (shared storage), so a replica reads materialized pages rather than replaying a local copy. **Single primary writer.** See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo-style per-query knobs (it's Postgres).
- **Clock dependency:** No — ordering is by WAL **LSN**, not wall-clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, rigid relational** — Postgres semantics. Online DDL behaves as in Postgres.
- **Migration / evolution:** standard Postgres `ALTER`; **branching** makes schema-migration testing cheap (branch, migrate, validate, discard).
- **Type system:** full Postgres types plus extensions — JSON/JSONB, arrays, geospatial (PostGIS), `pgvector`, etc.

## Query interface
- **Language:** **SQL (PostgreSQL dialect)** over the Postgres wire protocol; also an HTTP/serverless driver for edge/serverless clients.
- **Transactions:** full multi-statement **ACID**, as Postgres.
- **Native vs app-side:** everything Postgres offers — joins, window functions, secondary indexes, CTEs, stored procedures/UDFs (PL/pgSQL and others), extensions.
- **Stored procedures / UDFs:** Postgres procedural languages; extension availability is curated by the managed service.

## Scaling & topology
- **Vertical autoscaling** of compute (CPU/RAM scale up/down with load, **down to zero**); **storage scales independently** and "bottomlessly" on object storage.
- **Sharding / partitioning:** no built-in horizontal **write** sharding — single primary. Read scale via replicas off shared storage.
- **Read replicas / read consistency:** replicas read materialized pages from the pageserver; ⚠️ unverified — exact replica staleness/read-your-writes guarantees not captured here.
- **Storage/compute separation:** **the entire design point** — stateless compute over a shared, versioned, object-storage-backed storage engine. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Postgres emits WAL → **safekeepers** durably hold it once a **Paxos quorum** acks (commit point) → the **pageserver** asynchronously ingests WAL and uploads to object storage. No local-disk fsync on the compute is the durability anchor; the safekeeper quorum is. Data-loss window is whatever the quorum guarantees on an acked commit. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** excellent for bursty/serverless; **cold start** on a scaled-to-zero endpoint and **page-fetch latency** on a cold pageserver cache are the tail-latency sources (vs a warm, locally-attached Postgres). Steady heavy OLTP may prefer provisioned/local-NVMe options.
- **Compaction / GC:** the pageserver compacts/garbage-collects page-version history and enforces retention (which bounds how far back branches/PITR can reach); managed automatically. ⚠️ unverified — exact retention defaults vary by plan.

## Operations & maturity
- **Backup/restore, PITR:** **point-in-time restore and branching** fall out of the WAL-history storage model — restore to any LSN/timestamp within the retention window by creating a branch. Physical durability rests on the object store.
- **Observability:** managed-console metrics, Postgres `EXPLAIN`/`pg_stat_*`. ⚠️ unverified — depth of self-host observability not captured.
- **Upgrade story:** managed/rolling for the cloud service; OSS tracks Postgres major versions plus Neon's storage components.
- **Maturity:** young but fast-growing and now **Databricks-backed** (acquired May 2025, ~$1B; Databricks committed to keep it open source and run it independently). Heavily used for agent-provisioned and preview/branching workflows. **No Jepsen report** — the safety story rests on the documented Paxos-quorum WAL design plus Postgres's own semantics, not third-party formal verification (⚠️).

## Ecosystem & people
- **Canonical use cases:** serverless app backends, **dev/preview/CI environments with branching**, per-tenant SaaS databases, **AI-agent-provisioned** databases, and operational Postgres alongside a lakehouse ("Lakebase"). **Anti-patterns:** steady always-on heavy OLTP where scale-to-zero/branching add no value; latency-critical workloads intolerant of cold starts; write-scale-out beyond a single primary.
- **Drivers / connectors:** anything that speaks Postgres — standard drivers/ORMs (`psql`, SQLAlchemy, Prisma, Drizzle, etc.), plus a **serverless HTTP driver** for edge runtimes. Integrates with the broader Postgres extension and tooling ecosystem.
- **Community size, support, docs:** strong docs and a large developer following; commercial support via the Neon/Databricks managed service.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive) for the Neon storage system and tooling ([GitHub](https://github.com/neondatabase/neon)). The compute is open-source Postgres. Low lock-in at the **SQL** level (it's Postgres); higher if you depend on serverless/branching/Lakebase features or run on the managed service.
- **Self-managed vs managed:** the OSS can be self-hosted but is operationally heavy (pageserver/safekeepers/object store); the vast majority of users take **Neon managed cloud** (now under Databricks).
- **Cost model:** consumption-based — compute by active time (scale-to-zero means you pay ~nothing idle) plus storage; cheap for spiky/dev workloads, can invert for steady high-utilization compute. ⚠️ unverified — exact per-unit pricing not captured here.

## Hardware / deployment
- **Resource profile:** compute is elastic (autoscaling, scale-to-zero); performance is dominated by **pageserver cache locality** and network rather than a fixed local disk.
- **Storage assumptions:** **object-storage-native** backend (durable, bottomless) with safekeeper-quorum WAL in front; explicitly designed to tolerate disaggregated, networked storage.
- **Footprint:** managed multi-tenant cloud service (primary); self-hostable OSS cluster (compute + safekeepers + pageserver + object store) for the determined.
- **Deployment:** SaaS / BYOC under Databricks; serverless- and edge-friendly via the HTTP driver. Not an embedded or single-binary database.

## Bottom line
Reach for Neon when you want **serverless Postgres**: real Postgres compatibility with **scale-to-zero**, autoscaling, and **instant copy-on-write branching**, without operating storage/HA/PITR — superb for dev/preview/CI, spiky or per-tenant apps, and agent-provisioned databases. Don't reach for it for steady always-on heavy OLTP (where provisioned/local-NVMe Postgres is cheaper and lower-latency), for cold-start-sensitive paths, or for single-primary write scale-out. The single biggest gotcha is **latency from disaggregation**: a scaled-to-zero endpoint cold-starts and a cold pageserver cache adds page-fetch latency — and there is **no Jepsen report**, so the safety story is "Postgres semantics on top of a documented Paxos-quorum WAL," not independently verified. See the hosted-Postgres landscape in the [decision guide](../decision-guide.md) (§1) alongside [amazon-aurora](amazon-aurora.md) and [edb-postgres](edb-postgres.md).

## Sources
- [Neon GitHub (Apache 2.0, "we separated storage and compute…")](https://github.com/neondatabase/neon)
- [Neon architecture overview — compute / safekeepers (Paxos WAL) / pageserver / object storage, branching](https://neon.com/docs/introduction/architecture-overview)
- [Why Neon — scale-to-zero, autoscaling, branching](https://neon.com/docs/get-started/why-neon)
- [Jack Vanlightly — Neon serverless PostgreSQL architecture analysis](https://jack-vanlightly.com/analyses/2023/11/15/neon-serverless-postgresql-asds-chapter-3)
- [Databricks Lakebase / decoupling compute & storage in Postgres](https://alexeyevlampiev.github.io/posts/decoupling-compute-storage-postgres-lakebase/)
