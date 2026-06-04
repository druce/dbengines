---
name: ClickHouse
slug: clickhouse
rank: 26
data_model: Relational (columnar OLAP)
license: Apache 2.0 (permissive)
summary: Open-source columnar OLAP engine built for blazing analytical scans; trades transactional safety for raw read throughput.
last_researched: 2026-06-04
confidence: high
---

# ClickHouse

> A column-store SQL analytics engine that is one of the fastest things in the world for large aggregate scans — provided you accept eventual consistency, asynchronous updates, and snapshot (not serializable) isolation.

## When to use

**Use ClickHouse if:**
- ✅ You need extremely fast SQL analytics over huge append-mostly datasets (logs, events, metrics, clickstream, BI)
- ✅ You can batch your inserts (many tiny inserts cause part explosion)
- ✅ You want world-class aggregations / `GROUP BY` and wide scans over billions of rows in sub-second time
- ✅ You want permissive Apache-2.0 licensing with a self-host or managed-cloud path

**Avoid ClickHouse if:**
- ❌ You'd use it as a transactional system of record, for frequent row-level updates/deletes, or point-lookup key-value access
- ❌ You need serializable isolation or strong cross-row consistency (it gives snapshot isolation, eventual consistency, and durability isn't on by default — the biggest gotcha)
- ❌ You'd issue many concurrent tiny inserts
- ❌ You need automatic resharding (open source requires manual data redistribution)

## Identity
- **Taxonomy / data model:** relational, SQL-based, but columnar and OLAP-first — not a transactional system. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** column-store. The flagship `MergeTree` engine family writes immutable, sorted, compressed **data parts** that background processes merge over time — an LSM-like write/merge pattern (see [lsm-vs-btree](../concepts/lsm-vs-btree.md), [columnar-storage](../concepts/columnar-storage.md)). Sparse primary-key index (one mark per granule, default 8192 rows) rather than a per-row B-tree.
- **Workload:** OLAP. Optimized for high-throughput inserts and wide aggregate scans, *not* point lookups or frequent single-row updates. Not HTAP — updates/deletes are asynchronous background "mutations," so it should not be the system of record for OLTP.

## Distribution & consistency
- **CAP under partition:** **AP-leaning / eventually consistent** by default. `ReplicatedMergeTree` replicas converge by fetching parts via coordination metadata; a replica can keep serving stale reads during a partition ([replication docs](https://clickhouse.com/docs/architecture/replication)). You can opt into CP-like write behavior with `insert_quorum`. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition, default favors Availability; in normal operation it favors Latency/throughput over strong consistency unless you raise `insert_quorum` / `select_sequential_consistency`. Coordination (DDL, replication queue, quorum) runs through **ClickHouse Keeper**, a C++ reimplementation of ZooKeeper using **Raft** (production-ready since 22.3) ([Keeper](https://clickhouse.com/docs/architecture/replication)). See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Default isolation & what's achievable:** clients **outside a transaction get read-uncommitted**; queries run against a consistent snapshot of immutable parts giving **snapshot isolation** in practice (MVCC over parts) ([transactional docs](https://clickhouse.com/docs/guides/developer/transactional)). Serializable is **not** available. Multi-statement BEGIN/COMMIT/ROLLBACK exists but is **experimental and unstable** (`allow_experimental_transactions`, requires Keeper + Atomic database). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). Treat any "ACID" claim narrowly: it means a single single-partition INSERT packed into one block is atomic and durable — not general multi-statement ACID.
- **Replication:** multi-master / leaderless within a shard — every `ReplicatedMergeTree` replica accepts inserts and coordinates via Keeper; asynchronous by default. No single elected leader for writes; conflict-free because inserts only append new parts (cannot collide). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** yes — `insert_quorum` (`N` or `'auto'`=majority) blocks the insert until N replicas confirm; `select_sequential_consistency` forces reads to wait for quorum-acknowledged data.
- **Clock dependency:** does not depend on synchronized clocks for correctness (no TrueTime-style scheme). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid typed columns; no schemaless documents (though `JSON`/`Dynamic`/`Variant` types now exist for semi-structured data).
- **Migration:** `ALTER ... ADD/DROP/MODIFY COLUMN` is metadata-only and cheap for most cases; data rewrites for type changes run as **async mutations** in the background. `UPDATE`/`DELETE` are mutations (rewrite affected parts) — expensive, not for high-frequency row edits. Lightweight `DELETE` and (newer) lightweight `UPDATE` mark rows without full rewrite.
- **Type system:** rich — `LowCardinality`, `Enum`, `Array`, `Tuple`, `Map`, `Nested`, `Decimal`, `UUID`, IPv4/v6, geospatial, `DateTime64`, native `JSON`, and aggregate-function state types for materialized rollups. Vector columns (`Array(Float32)`) with approximate vector indexes are supported. See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** SQL, ClickHouse dialect (broad ANSI coverage plus many extensions: `ARRAY JOIN`, combinators like `-If`/`-Array`, window functions, rich aggregate functions).
- **Transactions:** effectively **single-INSERT atomicity** — atomic + durable only when the insert is a single partition packed into one block (≤ `max_insert_block_size`, default ~1M rows) ([transactional docs](https://clickhouse.com/docs/guides/developer/transactional)). Multi-partition / distributed inserts have **no whole-operation atomicity or durability**. General multi-statement transactions are experimental.
- **Native vs app-side:** joins are supported but historically weaker than dedicated OLTP/MPP engines (hash/partial-merge; large joins memory-hungry); aggregations and `GROUP BY` are world-class. Secondary indexes exist as **skip indexes** (data-skipping, not classic B-tree lookups). Dictionaries provide fast key-value lookups for joins.
- **Stored procedures / UDFs:** SQL UDFs and executable/external UDFs (run a script in any language); no rich PL/pgSQL-style procedural language.

## Scaling & topology
- **Horizontal:** scales via **manual sharding** (Distributed table over shards) + replication per shard. Resharding is **painful** — no automatic rebalancing in open source; you redistribute data yourself. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Partitioning:** user-defined `PARTITION BY` (commonly by month/day) plus the sort-key ordering within parts.
- **Read replicas:** all replicas are readable; reads are eventually consistent unless `select_sequential_consistency` is set.
- **Storage/compute separation:** the open-source server is shared-nothing local-disk, but supports object-storage (S3) disks. **ClickHouse Cloud** is a full storage/compute-separated architecture on object storage with independent autoscaling compute and shared data across services. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** inserts land as new parts written to the filesystem before the client is acked; **fsync is off by default** (`fsync_after_insert=0`), so a crash before the OS flushes can lose recently inserted parts — a real **data-loss window** unless you enable fsync and/or quorum. See [wal-and-durability](../concepts/wal-and-durability.md). (MergeTree has no traditional redo WAL; durability comes from flushed immutable parts + replication.)
- **Throughput/latency:** exceptional scan/aggregation throughput (vectorized, SIMD, late-materialization); sub-second analytics over billions of rows is routine. Best with **large batched inserts**; many tiny inserts create part explosion ("too many parts" errors) and hurt p99.
- **Compaction/GC:** background **merges** continuously combine parts; mutations and merges compete for I/O and CPU and are the main source of p99 spikes and disk-space churn. Special engines (`ReplacingMergeTree`, `AggregatingMergeTree`, `CollapsingMergeTree`) defer dedup/aggregation to merge time, so reads may see not-yet-merged duplicates unless you use `FINAL`.

## Operations & maturity
- **Backup/restore:** `BACKUP`/`RESTORE` commands (to local/S3); part-level `FREEZE` snapshots via hard links; PITR is not a first-class turnkey feature in OSS (rebuild from backups + replication).
- **Observability:** extensive `system.*` tables (query_log, part_log, metrics, asynchronous_metrics), `EXPLAIN` plans, slow-query logging, Prometheus endpoint.
- **Upgrade:** rolling upgrades across replicas are supported; generally backward-compatible storage. Day-2 burden centers on tuning merges, partition design, Keeper health, and avoiding small-insert pathologies.
- **Maturity:** very mature and widely deployed at large scale (Cloudflare, observability vendors, ad-tech). **No independent jepsen.io report exists for the full database**, so its replication/consistency guarantees are documented but not independently formally verified. However, the **ClickHouse Keeper** Raft coordination layer (which underpins replicated writes, DDL, and quorum) is tested with the **Jepsen framework in CI** — automated workflows/fault-injection scenarios run on a schedule to validate the consensus mechanism; Keeper targets linearizable writes and, optionally, linearizable reads (`quorum_reads`), matching ZooKeeper's model ([Keeper blog](https://clickhouse.com/blog/clickhouse-keeper-a-zookeeper-alternative-written-in-cpp)). Known failure modes: too-many-parts, runaway mutations, Keeper quorum loss blocking all replicated writes, memory blowups on big joins/`GROUP BY`.

## Ecosystem & people
- **Canonical use cases:** real-time analytics, observability/logs/metrics/traces, clickstream and event analytics, time-series, BI over huge append-mostly datasets. See [time-series-storage](../concepts/time-series-storage.md).
- **Anti-patterns:** OLTP / system-of-record, frequent single-row updates or deletes, point-lookup key-value access, workloads needing serializable transactions or strong cross-row consistency, or many concurrent tiny inserts.
- **Connectors:** Kafka table engine + ClickPipes, official drivers (Go, Python, JDBC/ODBC, JS), dbt adapter, Grafana/Superset/Metabase, CDC tools (Debezium, PeerDB), MaterializedPostgreSQL/MySQL engines.
- **Community:** large, active OSS community; commercial support from ClickHouse Inc. and Altinity; docs are thorough.

## Licensing & cost
- **OSS license:** **Apache 2.0** — fully permissive, no post-2018 relicensing (notably has *not* moved to source-available, unlike some peers) ([Altinity](https://altinity.com/blog/clickhouse-is-apache-2-0)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-host freely; managed options include **ClickHouse Cloud** (vendor SaaS), Altinity, Aiven, Tinybird.
- **Lock-in:** core is OSS and portable; ClickHouse Cloud's storage/compute architecture and some Cloud-only features are proprietary.
- **Cost model:** OSS = your hardware. ClickHouse Cloud meters **compute per-minute (in RAM increments)** + **compressed object-storage GB**, with compute autoscaling and shared data across services ([pricing](https://clickhouse.com/pricing)). At scale, compute (not storage) tends to dominate; idle-scaling helps bursty workloads.

## Hardware / deployment
- **Resource profile:** CPU- and memory-hungry for query execution (vectorized scans, hash aggregation/joins); disk-bound for cold scans. Working set need not fit in RAM, but big joins/`GROUP BY` can OOM if memory limits are too low.
- **Storage assumptions:** loves fast local **NVMe**; works on network/object storage (S3 disks, Cloud) with caching to hide latency.
- **Footprint:** single-node to large multi-shard clusters; also runnable as a single binary (`clickhouse-local`) for embedded/CLI analytics over files — comparable in spirit to [duckdb](duckdb.md) for ad-hoc local use. See [embedded-databases](../concepts/embedded-databases.md).
- **Deployment:** SaaS (ClickHouse Cloud) or on-prem/self-managed; mature Kubernetes operators (Altinity, ClickHouse) handle StatefulSet realities and Keeper coordination.

## Bottom line
Reach for ClickHouse when you need extremely fast SQL analytics over huge append-mostly datasets — logs, events, metrics, BI — and can batch your inserts. Do **not** use it as a transactional system of record, for frequent row-level updates, point lookups, or anything needing serializable isolation. The single biggest gotcha: updates/deletes are asynchronous **mutations** and durability is **not on by default** (no fsync) — so it is fast precisely because it relaxes the guarantees an OLTP database makes.

## Sources
- [Transactional (ACID) support — ClickHouse Docs](https://clickhouse.com/docs/guides/developer/transactional)
- [Replicating data — ClickHouse Docs](https://clickhouse.com/docs/architecture/replication)
- [ClickHouse Cloud pricing](https://clickhouse.com/pricing)
- [ClickHouse is Apache 2.0 — Altinity](https://altinity.com/blog/clickhouse-is-apache-2-0)
- [ClickHouse: Lightning Fast Analytics for Everyone (VLDB paper, summary)](https://www.hemantkgupta.com/p/insights-from-paper-clickhouse-lightning)
