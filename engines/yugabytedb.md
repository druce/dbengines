---
name: YugabyteDB
slug: yugabytedb
rank: 117
data_model: Relational (distributed SQL / NewSQL)
license: Apache 2.0 (permissive; relicensed from source-available in 2019)
summary: Spanner-inspired distributed SQL with a PostgreSQL-wire-compatible query layer over a Raft-replicated, RocksDB-based shard store.
last_researched: 2026-06-04
confidence: high
---

# YugabyteDB

> A horizontally scalable, strongly consistent distributed SQL database that reuses real PostgreSQL query-layer code on top of a Spanner-style sharded, Raft-replicated storage engine — choose it when you need Postgres semantics that survive node loss and outgrow one machine, not for analytics or single-node simplicity.

## When to use

**Use YugabyteDB if:**
- ✅ You have a PostgreSQL workload that must scale writes horizontally and survive node/zone/region failures with strong consistency (CP, synchronous Raft)
- ✅ You need genuine Postgres query-layer compatibility (YSQL reuses upstream Postgres code) plus full multi-statement distributed ACID across shards
- ✅ You're building geo-distributed/multi-region OLTP with data-residency needs (geo-partitioning) or Postgres apps hitting single-node ceilings
- ✅ You want automatic sharding/rebalancing, global secondary indexes, and a permissive Apache 2.0 license

**Avoid YugabyteDB if:**
- ❌ You ignore clock-skew monitoring — correctness rests on bounded skew (HLC, not TrueTime), and distributed commit adds real WAN latency on geo-writes (the biggest gotcha)
- ❌ Your workload is heavy analytics/OLAP — there is no columnar engine; CDC out to a warehouse instead
- ❌ You have a simple single-node app — a plain Postgres node is far less operationally complex
- ❌ You need transactional DDL or ultra-low-latency single-region writes where distributed-commit overhead isn't worth it

## Identity
- **Taxonomy / data model:** Distributed relational ("distributed SQL" / NewSQL). Two query APIs share one storage engine: **YSQL** (PostgreSQL-wire-compatible, reuses upstream Postgres source) and **YCQL** (a Cassandra-CQL-like semi-relational API). ([key concepts](https://docs.yugabyte.com/stable/architecture/key-concepts/))
- **Storage model:** Row-oriented document persistence in **DocDB**, a heavily customized fork of **RocksDB** — an [LSM-tree](../concepts/lsm-vs-btree.md) store. Rows are encoded as documents; on-disk format is RocksDB SSTables.
- **Workload:** OLTP-first. Markets itself for some HTAP/analytical reach, but there is **no separate columnar engine or delta store** — analytical queries run over the same LSM row store, so treat HTAP claims as "OLTP that can also run moderate analytical SQL," not true physical workload separation. No columnar secondary format exists; for heavy analytics the recommended pattern is CDC out to a warehouse (ClickHouse/Snowflake/BigQuery). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** — a tablet's writes require a Raft majority; the minority partition refuses writes to preserve consistency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EC** — under Partition it chooses Consistency; Else it favors Consistency over Latency (synchronous Raft commit on the write path), Spanner-style.
- **Default isolation & what's achievable:** YSQL supports **Read Committed, Snapshot (= PostgreSQL Repeatable Read), and Serializable**. Default is **Read Committed in v2025.2+** when deployed via yugabyted/Anywhere/Aeon; on earlier/manual deployments `yb_enable_read_committed_isolation` defaults false and Read Committed silently **falls back to Snapshot**. Read Uncommitted behaves as Read Committed. YCQL supports only Snapshot isolation. ([isolation levels](https://docs.yugabyte.com/stable/architecture/transactions/isolation-levels/)) See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Per-tablet **single-leader Raft**; synchronous replication to a majority of replicas (typically RF=3). Automatic leader election on failover; no split-brain since a minority cannot commit. Async **xCluster** replication available for cross-region/DR. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** Limited vs Dynamo-style — strongly consistent by default; **follower reads** (bounded-staleness) can be opted into for lower-latency reads.
- **Clock dependency:** Uses **Hybrid Logical Clocks (HLC)**, not Google TrueTime hardware. Correctness depends on bounded clock skew within `--max_clock_skew_usec` (conservative default 500000µs = 500ms; tighter values reduce read-restart latency but risk consistency violations if exceeded). Exceeding the bound can break linearizability. ([deploy checklist](https://docs.yugabyte.com/stable/deploy/checklist/), [Jepsen 1.3.1](https://jepsen.io/analyses/yugabyte-db-1.3.1)) See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema (YSQL). YCQL is semi-relational with a defined schema.
- **Migration/evolution:** Online schema changes are supported but historically a weak spot — Jepsen found **non-transactional DDL** (`DEFAULT` columns could initialize to NULL because schema change wasn't atomic). YSQL does not support fully transactional DDL, a known limitation shared by most distributed SQL engines. ([Jepsen 1.3.1](https://jepsen.io/analyses/yugabyte-db-1.3.1))
- **Type system:** Inherits PostgreSQL types via YSQL — JSON/JSONB, arrays, UUID, intervals, and (via the pgvector extension) **vector** types for ANN. PostGIS-style geospatial support is partial/evolving.

## Query interface
- **Language:** **YSQL** = PostgreSQL dialect, reusing upstream Postgres query-layer code for high compatibility (functions, joins, window functions, CTEs, many extensions). **YCQL** = CQL-like DSL.
- **Transactions:** Full **multi-statement distributed ACID** across shards and nodes (2-phase commit coordinated over Raft + HLC). YCQL supports distributed transactions and strongly consistent secondary indexes.
- **Native vs app-side:** Native distributed joins, aggregations, window functions, and **global secondary indexes** (consistent, unlike eventually-consistent secondary indexes in some NoSQL).
- **Stored procedures / UDFs:** PL/pgSQL and other PostgreSQL procedural languages via YSQL.

## Scaling & topology
- **Horizontal**, scale-out by adding nodes. Tables are auto-sharded into **tablets**; sharding is **automatic** (hash or range). **Auto-rebalancing** and automatic tablet splitting reduce manual resharding pain, though large rebalances generate background load.
- **Read replicas / follower reads:** Read replicas (async, read-only) and follower reads give scalable reads; follower reads are bounded-stale, leader reads are strongly consistent.
- **Storage/compute separation:** No — it is shared-nothing; each node owns local storage. Not an Aurora/Neon disaggregated design. The managed **Aeon** service runs the same shared-nothing engine. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Raft log is the durability mechanism; a write is acked after replication to a Raft majority and fsync of the Raft log. **Data-loss window on crash is effectively zero for committed writes** (durable on a majority before ack), modulo fsync config. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Cross-node Raft commit adds latency vs single-node Postgres; multi-region deployments pay WAN round-trips on writes unless using follower reads or geo-partitioning. p99 is sensitive to leader placement and clock skew.
- **Compaction/GC:** RocksDB-style LSM **background compaction**; like any [LSM](../concepts/lsm-vs-btree.md) engine, compaction competes for I/O and can spike p99. MVCC garbage from old versions is reclaimed during compaction.

## Operations & maturity
- **Backup/restore:** Distributed backups, snapshots, and **PITR** are open-source (since the 2019 relicensing). xCluster for DR.
- **Observability:** Prometheus metrics, per-tablet stats, EXPLAIN/EXPLAIN ANALYZE via YSQL, slow-query logging (pg_stat_statements).
- **Upgrade story:** Rolling upgrades, node-by-node, without downtime in an RF=3 cluster.
- **Maturity & Jepsen:** Production-grade since v2.0 (2019). **Jepsen tested by Kyle Kingsbury**: YCQL (1.2) and YSQL (1.3.1) both analyzed. 1.3.1 found two safety bugs — `DEFAULT` columns initializing to NULL (non-transactional DDL) and **G2-item anti-dependency cycles** (serializability violations during master crashes/pauses); the G2 issue was fixed in 1.3.1.2-b1, and Jepsen judged YSQL not production-ready until 2.0. ([Jepsen 1.3.1](https://jepsen.io/analyses/yugabyte-db-1.3.1), [Yugabyte Jepsen blog](https://www.yugabyte.com/blog/yugabyte-db-distributed-sql-api-passes-jepsen-tests/))

## Ecosystem & people
- **Canonical use cases:** Geo-distributed OLTP needing Postgres compatibility plus horizontal write scaling and zero-downtime resilience; multi-region apps with data-residency (geo-partitioning); Postgres apps that hit single-node ceilings.
- **Anti-patterns:** Heavy analytics/OLAP (no columnar engine — use a warehouse); small single-node workloads (a single Postgres or [cockroachdb](cockroachdb.md) node is simpler); ultra-low-latency single-region writes where distributed-commit overhead isn't worth it; workloads needing transactional DDL.
- **Drivers/connectors:** PostgreSQL drivers/ORMs work via YSQL (smart drivers add cluster awareness); CDC, Kafka connectors, dbt, and standard BI tools via the Postgres protocol. Closest peer is [cockroachdb](cockroachdb.md) (also Spanner-inspired distributed SQL); contrast with [tidb](tidb.md) (MySQL-compatible, columnar TiFlash for real HTAP).
- **Community & support:** Active OSS project (yugabyte/yugabyte-db on GitHub); commercial support and managed **Aeon** + self-managed **Anywhere** from Yugabyte, Inc. Docs are strong. Learning curve: easy for Postgres users on the SQL surface, harder on distributed-systems operations.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive) for the core database since the **July 2019 relicensing** that moved previously source-available enterprise features (backups, encryption, read replicas) into the open-source core. Note this is a 2018-era relicensing trend going the *opposite* direction from MongoDB/Elastic — toward more-open, not less. See [license-taxonomy](../concepts/license-taxonomy.md). ([Yugabyte relicensing blog](https://www.yugabyte.com/blog/why-we-changed-yugabyte-db-licensing-to-100-open-source/))
- **Self-managed vs managed:** Fully self-hostable (Apache 2.0); commercial **Aeon** (managed cloud) and **Anywhere** (self-managed control plane) are paid. Low lock-in given Postgres wire compatibility.
- **Cost model:** Self-managed = your hardware. Aeon is consumption/instance-based (vCPU + storage). Distributed RF=3 means ~3x storage for replication, which dominates cost at scale.

## Hardware / deployment
- **Resource profile:** CPU- and I/O-bound under write load; benefits from large RAM for RocksDB block cache but **does not require the whole dataset in RAM** — it spills to disk like any LSM store.
- **Storage assumptions:** Designed for **local NVMe/SSD**; tolerant of commodity cloud disks but latency-sensitive. Network-attached storage works but adds latency.
- **Footprint:** Clustered/distributed (min 3 nodes for RF=3 fault tolerance); not embedded. Single-node mode exists for dev only.
- **Deployment:** Self-managed on-prem or any cloud, managed Aeon SaaS; first-class Kubernetes/StatefulSet support and a Helm chart/operator.

## Bottom line
Reach for YugabyteDB when you have a PostgreSQL workload that must scale writes horizontally and survive node/zone/region failures with strong consistency — it gives you genuine Postgres query-layer compatibility on a Spanner-style core. Do not reach for it for analytics (no columnar engine), for simple single-node apps (a plain Postgres node is far less operationally complex), or where you need transactional DDL. The biggest gotcha: correctness rests on bounded clock skew (HLC, not TrueTime) and distributed commit adds real latency — geo-distributed writes are not free, and clock-skew monitoring is mandatory.

## Sources
- [YugabyteDB Docs — Key concepts](https://docs.yugabyte.com/stable/architecture/key-concepts/)
- [YugabyteDB Docs — Transaction isolation levels](https://docs.yugabyte.com/stable/architecture/transactions/isolation-levels/)
- [Jepsen: YugaByte DB 1.3.1](https://jepsen.io/analyses/yugabyte-db-1.3.1)
- [Yugabyte blog — Distributed SQL API passes Jepsen](https://www.yugabyte.com/blog/yugabyte-db-distributed-sql-api-passes-jepsen-tests/)
- [Yugabyte blog — Why we changed licensing to 100% open source (Apache 2.0)](https://www.yugabyte.com/blog/why-we-changed-yugabyte-db-licensing-to-100-open-source/)
- [Wikipedia — YugabyteDB](https://en.wikipedia.org/wiki/YugabyteDB)
