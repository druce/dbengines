---
name: CockroachDB
slug: cockroachdb
rank: 71
data_model: Relational (distributed NewSQL)
license: CockroachDB Software License (source-available, proprietary; was Apache 2.0 → BSL → CSL)
summary: Geo-distributed PostgreSQL-wire-compatible SQL with serializable-by-default isolation and Raft-replicated auto-sharded ranges; survives node/zone loss but pays a latency tax and emits retryable serialization errors.
last_researched: 2026-06-04
confidence: high
---

# CockroachDB

> A horizontally-scalable, Postgres-compatible distributed SQL DB that defaults to true serializable isolation across Raft-replicated ranges — pick it for geo-distributed survivability, not for single-region low-latency OLTP.

## When to use

**Use CockroachDB if:**
- ✅ You need a relational database that survives node, zone, or region failure with zero data loss (RPO≈0)
- ✅ You want true SERIALIZABLE isolation by default, not snapshot dressed up as ACID
- ✅ You can pin data geographically — multi-region SaaS, systems of record, and financial ledgers are the sweet spot
- ✅ You want Postgres wire compatibility plus automatic sharding/rebalancing (no manual resharding)

**Avoid CockroachDB if:**
- ❌ You're a single-region low-latency app where plain [postgresql](postgresql.md)/MySQL suffice (you'd pay consensus latency for nothing)
- ❌ You need an analytics/OLAP warehouse (no columnar storage — CDC out to one instead)
- ❌ Your app can't handle retryable `40001` serialization errors, or you'd use naive monotonic primary keys that create write hotspots (the biggest gotcha)
- ❌ You require an OSI open-source license — it shifted to the source-available, license-key-gated CSL in 2024

## Identity
- **Taxonomy / data model:** Relational (NewSQL), PostgreSQL wire-protocol compatible. Single monolithic ordered key space mapped to SQL tables/indexes.
- **Storage model:** Row-oriented KV underneath. Storage engine is **Pebble**, an LSM-tree engine ([lsm-vs-btree](../concepts/lsm-vs-btree.md)) written in Go and inspired by/replacing RocksDB ([CRDB design](https://github.com/cockroachdb/cockroach/blob/master/docs/design.md)). [mvcc](../concepts/mvcc.md) versioning is timestamped via [hybrid logical clocks](../concepts/clocks-and-time.md).
- **Workload:** Primarily **OLTP** with strong consistency. Has a vectorized SQL execution engine and columnar batch processing for analytical-ish queries, but it is **not an OLAP/HTAP warehouse** — no columnar storage. Treat HTAP claims as overstated; for analytics most users CDC out to a warehouse. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** — a range becomes unavailable for writes if its Raft group cannot reach quorum, choosing consistency over availability ([cap-pacelc](../concepts/cap-pacelc.md)). The whole cluster stays up; only under-replicated ranges block.
- **PACELC:** **PC/EC** — consistent under partition, and in normal operation it still favors consistency, paying cross-node/cross-region consensus latency on writes ([cap-pacelc](../concepts/cap-pacelc.md)).
- **Default isolation & what's achievable:** **SERIALIZABLE by default** — real serializability, not snapshot dressed up as ACID ([Transactions](https://www.cockroachlabs.com/docs/stable/transactions)). Since v23.2 it also offers **READ COMMITTED** as an opt-in for fewer retry errors and Postgres-app compatibility ([Read Committed](https://www.cockroachlabs.com/docs/stable/read-committed)). The trade-off: serializable produces **retryable serialization errors** (`40001`) the app must handle. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **Raft consensus per range** ([consensus-raft-paxos](../concepts/consensus-raft-paxos.md), [replication-models](../concepts/replication-models.md)); a quorum (typically 3 or 5 replicas) must ack each write. Synchronous within the Raft group. A **leaseholder** per range coordinates reads/writes. Failover is automatic on quorum loss of the leaseholder; no split-brain because writes require majority.
- **Tunable consistency?** Limited. Strong by default; **follower reads** allow bounded-staleness or exact-staleness reads from non-leaseholders to cut geo-latency ([reads-and-writes](https://www.cockroachlabs.com/docs/stable/architecture/reads-and-writes-overview)). Not Dynamo-style per-query R/W quorum tuning.
- **Clock dependency:** Yes, but bounded. Uses **HLCs**, and correctness depends on clock skew staying under `--max-offset` (default 500ms); a node whose clock drifts beyond this **self-terminates** to preserve safety. No TrueTime/GPS hardware required, unlike Spanner. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema with Postgres-style typing.
- **Migration / online DDL:** Supports **online schema changes** — most `ALTER`s run as background jobs without long table locks, using a multi-version schema-element protocol. This is a genuine differentiator vs. lock-heavy `ALTER` in classic RDBMSs.
- **Type system:** Postgres-compatible: JSONB, arrays, `INTERVAL`, UUID, spatial/geospatial (PostGIS-subset), and a `VECTOR` type with vector indexing in recent versions. Computed columns, hash-sharded indexes for hot sequential keys.

## Query interface
- **Language:** SQL, **PostgreSQL dialect** over the pgwire protocol — most Postgres drivers/ORMs connect unmodified (dialect is a subset; not 100% Postgres feature parity).
- **Transactions:** Full **multi-statement ACID** distributed transactions across ranges/nodes (two-phase, write-pipelined, parallel commits).
- **Native vs app-side:** Native distributed joins, aggregations, window functions, secondary indexes (global, not partition-local), CTEs. Distributed SQL execution engine (DistSQL) pushes computation to data.
- **Stored procedures / UDFs:** SQL and PL/pgSQL UDFs and stored procedures supported in recent versions.

## Scaling & topology
- **Vertical & horizontal.** Horizontal scale is the headline: add nodes and the cluster auto-rebalances.
- **Sharding:** **Automatic.** Keyspace split into ~64–512MB **ranges** that split when large/hot and merge when small; ranges rebalance across nodes automatically. No manual resharding — a major operational win vs. manually-sharded systems.
- **Partitioning:** Row-level **geo-partitioning** / multi-region — pin data to regions for locality and compliance (table localities: regional-by-row, global, etc.). Multi-region is an enterprise feature.
- **Read replicas / read consistency:** No separate read-replica tier; reads served by leaseholders (strongly consistent) or via **follower reads** (bounded/exact staleness). Default reads are linearizable per key.
- **Storage/compute separation:** Classic CRDB is **shared-nothing**, compute+storage co-located. The managed **CockroachDB Cloud (serverless/standard)** offering layers elastic, usage-metered serverless on top. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Raft log per range provides the WAL; a write is durable once a **majority** of replicas persist it ([wal-and-durability](../concepts/wal-and-durability.md)). **Data-loss window on crash is effectively zero (RPO≈0)** for committed writes given a surviving quorum — the key durability advantage over single-node async-replication setups.
- **Throughput/latency:** Scales throughput near-linearly with nodes. **Write latency carries a consensus tax** (≥1 network round-trip to quorum; cross-region writes are slow unless data is geo-partitioned). Single-row reads from the leaseholder are fast; **p99 tails are sensitive to range leaseholder location, retries, and contention** — hotspots on monotonically increasing keys (e.g. sequential PKs) are a known footgun (mitigate with hash-sharded indexes/UUIDs).
- **Compaction / GC:** Pebble LSM compaction plus **MVCC garbage collection** of old versions (default GC TTL ~25h, tunable). Long GC TTLs bloat storage and can hurt scan p99; compaction competes for I/O like any LSM.

## Operations & maturity
- **Backup/restore, PITR:** Full/incremental **BACKUP/RESTORE** and **point-in-time recovery** (PITR) within the GC window; scheduled backups. RPO≈0 / near-zero RTO on node loss via Raft.
- **Observability:** Built-in DB Console UI, Prometheus metrics endpoint, `EXPLAIN`/`EXPLAIN ANALYZE` with plan diagrams, statement/transaction statistics, slow-query and contention insights.
- **Upgrade story:** **Rolling, online upgrades** node-by-node with a finalize step; designed for zero-downtime. Day-2 burden is moderate — capacity/rebalancing, GC TTL tuning, hotspot diagnosis, and handling retryable errors in app code are the recurring concerns.
- **Maturity & Jepsen:** Mature (GA since 1.0, 2017). **Jepsen-audited** — the [beta-20160829 analysis](https://jepsen.io/analyses/cockroachdb-beta-20160829) found several serializability violations in beta (timestamp-cache bug, fixed pre-1.0); later betas passed register/bank/g2/sequential under partitions, crashes, pauses, and clock offsets up to 250ms. CockroachDB does **not** claim strict serializability (the `comments` test failed as expected — it provides single-key linearizability, not global strict-serializable real-time ordering) ([beta-20160829](https://jepsen.io/analyses/cockroachdb-beta-20160829)). A later [nightly run](https://www.cockroachlabs.com/blog/jepsen-tests-lessons/) caught a real bug in 2.1 pipelined writes, since fixed. CockroachDB runs Jepsen nightly in CI.

## Ecosystem & people
- **Canonical use cases:** Geo-distributed OLTP requiring survivability (zone/region failure), strong consistency, and data-residency/compliance pinning; "Postgres that scales out." Multi-region SaaS, financial ledgers, systems of record.
- **Anti-patterns:** Single-region low-latency apps where Postgres/MySQL suffice (you pay consensus latency for nothing); analytics/warehousing (use a columnar OLAP store); heavy write contention on hot keys; workloads that can't tolerate retryable serialization errors; bulk single-row latency-critical paths across regions.
- **Connectors:** pgwire → most Postgres drivers/ORMs (psycopg, JDBC, GORM, Prisma, SQLAlchemy, Hibernate). Native **changefeeds (CDC)** to Kafka, cloud sinks, webhooks; dbt and BI tools via the Postgres adapter.
- **Community / support:** Well-funded vendor (Cockroach Labs), strong docs, sizable community. Commercial support + managed Cloud. Learning curve: SQL is familiar, but the distributed mental model (ranges, leaseholders, retries, clock bounds) is real.

## Licensing & cost
- **License:** **Source-available, proprietary.** Path: **Apache 2.0 → BSL (2019) → CockroachDB Software License (2024)**. In Aug 2024 Cockroach Labs announced retiring the free open-source "Core"; from **v24.3 (Nov 2024)** all releases (and back-patches to 23.1–24.2) ship under the **CSL**, which adds mandatory license keys, enforced telemetry, and benchmarking/use restrictions ([license change](https://www.theregister.com/2024/08/19/cockroachdb_abandons_open_core/), [InfoQ](https://www.infoq.com/news/2024/09/cockroachdb-license-concerns/)). A **free, annually-renewable Enterprise license** is offered to individuals, students, academics, and businesses under \$10M annual revenue; otherwise paid. This is **not OSI open source** — see [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Both — self-hosted (license key required), or **CockroachDB Cloud** (Basic/serverless, Standard, Advanced).
- **Lock-in:** pgwire eases migration *in*, but CRDB-specific features (multi-region SQL, changefeeds, geo-partitioning) and the proprietary license create stickiness.
- **Cost model:** Self-hosted is license-key + your infra; Cloud is **usage-metered** (request units / storage / vCPU). At scale the 3–5× replication factor multiplies storage/compute cost vs. a single-node DB — budget for the consistency you're buying.

## Hardware / deployment
- **Resource profile:** CPU- and I/O-bound under load; benefits from large RAM (block cache) and **fast local NVMe** for the Pebble LSM. Working set need not fit in RAM, but hot data should.
- **Storage assumptions:** Prefers **local NVMe**; network-attached (EBS-style) works but the LSM + Raft fsync path is latency-sensitive.
- **Footprint:** **Clustered / distributed** (3+ nodes for meaningful HA); single-node mode exists for dev only. Also a managed serverless offering. Not embedded.
- **Deployment:** SaaS (CockroachDB Cloud) or on-prem/any-cloud. **k8s-friendly** — official operator and Helm charts; runs as a StatefulSet with persistent volumes (mind disk-class latency and pod-eviction/rebalance interactions).

## Bottom line
Reach for CockroachDB when you need a relational database that **survives node, zone, or region failure with zero data loss and true serializable isolation**, and you can pin data geographically — multi-region SaaS and systems of record are the sweet spot. Do **not** use it as a single-region speed-of-light OLTP engine (plain Postgres is faster and simpler) or as an analytics warehouse. The single biggest gotcha: serializable isolation surfaces **retryable `40001` errors** that your application *must* handle, and naive monotonic primary keys create write hotspots that cap your throughput — design for both up front. Also weigh the 2024 shift to a proprietary, license-key-gated model.

## Sources
- [CockroachDB design doc (GitHub)](https://github.com/cockroachdb/cockroach/blob/master/docs/design.md)
- [Transactions / isolation levels (docs)](https://www.cockroachlabs.com/docs/stable/transactions)
- [Read Committed isolation (docs)](https://www.cockroachlabs.com/docs/stable/read-committed)
- [Reads and writes overview (docs)](https://www.cockroachlabs.com/docs/stable/architecture/reads-and-writes-overview)
- [Jepsen: CockroachDB beta-20160829](https://jepsen.io/analyses/cockroachdb-beta-20160829)
- [Lessons from 2+ years of nightly Jepsen tests (Cockroach Labs)](https://www.cockroachlabs.com/blog/jepsen-tests-lessons/)
- [CockroachDB: The Resilient Geo-Distributed SQL Database (SIGMOD paper)](https://rcs.uwaterloo.ca/~ali/cs854-f23/papers/cockroachdb.pdf)
- [License change coverage — The Register](https://www.theregister.com/2024/08/19/cockroachdb_abandons_open_core/) · [InfoQ](https://www.infoq.com/news/2024/09/cockroachdb-license-concerns/) · [Licensing FAQs (docs)](https://www.cockroachlabs.com/docs/stable/licensing-faqs)
