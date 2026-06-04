---
name: Apache Doris
slug: apache-doris
adjacent: true
rank: n/a
category: real-time-olap
data_model: Real-time MPP columnar OLAP data warehouse
license: Apache License 2.0 (permissive)
summary: MySQL-protocol MPP columnar warehouse for sub-second real-time analytics with built-in upserts and lakehouse federation.
last_researched: 2026-06-04
confidence: high
---

# Apache Doris

> A self-contained, MySQL-wire-compatible MPP columnar OLAP warehouse that does sub-second analytics, real-time upserts, and external-catalog lakehouse queries without bolting on ZooKeeper or external coordinators.

## When to use

**Use Apache Doris if:**
- ✅ You want a single MySQL-compatible MPP warehouse doing both high-throughput aggregation and real-time row-level upserts/CDC serving
- ✅ You want fewer moving parts than ClickHouse (no ZooKeeper in integrated mode) and easier SQL/joins than Druid
- ✅ You need sub-second analytics with window functions, CTEs, complex joins, and a cost-based optimizer over the MySQL protocol
- ✅ You want lakehouse federation over external Hive/Iceberg/Hudi/JDBC catalogs alongside its own columnar store

**Avoid Apache Doris if:**
- ❌ You need an OLTP system of record — it is READ COMMITTED only with no serializable/snapshot multi-statement guarantees (and no Jepsen-grade verification)
- ❌ Your write pattern is high-frequency tiny imports — merge-on-write upserts plus many small loads create compaction pressure that punishes naive patterns (biggest gotcha; batch your loads)
- ❌ You need a stream transport/bus — it is a serving/analytics sink, not Kafka
- ❌ You need rich multi-statement transactional app workloads

## Identity / role
- Apache Doris IS an analytical (OLAP) database — a clustered columnar query engine *and* its own storage. It is not just a query engine over someone else's tables (unlike [trino](trino.md)) and not a transactional store; it sits in the [real-time-olap](../concepts/real-time-olap.md) / [OLAP](../concepts/oltp-olap-htap.md) slot alongside [clickhouse](clickhouse.md), [apache-druid](apache-druid.md), and [starrocks](starrocks.md) (which forked from Doris and shares the FE/BE split).
- It also functions as a federated query engine over external catalogs (Hive/[Iceberg](apache-iceberg.md)/Hudi/[open-table-formats](../concepts/open-table-formats.md), JDBC, [postgresql](postgresql.md), object storage), but its sweet spot is data physically ingested into its own merge-on-write columnar store.
- What it is NOT: a row-store OLTP database (READ COMMITTED only, no rich multi-statement transactional app workloads), and not a [stream transport](../concepts/streaming-platforms.md) — it is a sink/serving layer, not Kafka.

## How it fits
- Two process types only: **Frontend (FE)** handles SQL parsing, planning, metadata, and node management; **Backend (BE)** stores data (sharded tablets, multi-replica) and executes the vectorized pipeline plan. FE runs Master/Follower/Observer roles; each FE holds a full metadata copy, replicated via a BDB-JE/quorum protocol (a Paxos-style edit-log replication; see [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)). No external ZooKeeper — a deliberate contrast to ClickHouse/[Kafka](apache-kafka.md)-coupled stacks.
- **Storage-compute integrated** (classic) keeps data on BE local disks with N replicas. **Storage-compute decoupled** (v3.0+, see [storage-compute-separation](../concepts/storage-compute-separation.md)) makes BEs stateless caches over shared object storage (S3/OSS/COS/GCS/Azure Blob/HDFS), with a stateless **Meta Service** layer persisting tablet/rowset metadata and import transactions into **FoundationDB**. Decoupled mode enables elastic compute clusters sharing one data copy. ([overview](https://doris.apache.org/docs/3.0/compute-storage-decoupled/overview/))
- Pairs with [Flink](apache-flink.md)/[Spark](apache-spark-sql.md) connectors, Kafka via Routine Load, and CDC pipelines (Flink CDC) for second-level ingestion from upstream OLTP. Read by BI tools (Superset, Tableau, Power BI) over the MySQL protocol; integrates with dbt via an adapter.

## Guarantees & consistency
- **Three table models** shape semantics: **Duplicate** (append-only fact rows), **Unique/Primary Key** (row-level upsert), and **Aggregate** (pre-aggregate on key, e.g. SUM/REPLACE). Unique Key defaults to **merge-on-write** since v1.2 — duplicates are merged at write time so reads hit a single final version (better query perf, predicate pushdown) at higher write cost. ([unique key](https://doris.apache.org/docs/dev/table-design/data-model/unique/))
- **Loads are atomic**: an import job commits fully or not at all, including multi-table imports in one job. ([load atomicity](https://doris.apache.org/docs/2.0/data-operate/import/load-atomicity/))
- **Exactly-once ingestion** is achievable via **labels**: each load carries a unique label that commits at most once, so retries are idempotent; combined with an at-least-once source (Kafka), this yields effective exactly-once delivery into Doris. ([load atomicity](https://doris.apache.org/docs/2.0/data-operate/import/load-atomicity/))
- **Isolation**: the only level is **READ COMMITTED** — a statement sees only data committed before it began. Concurrency is [MVCC](../concepts/mvcc.md)-based; each write gets a transaction. No serializable/snapshot multi-statement guarantees. ([transaction docs](https://doris.apache.org/docs/3.x/data-operate/transaction/))
- In decoupled mode, merge-on-write write-write conflicts (load vs compaction vs schema change) are arbitrated by a distributed table lock in Meta Service backed by FoundationDB's transactional KV. ([concurrency control](https://doris.apache.org/docs/data-operate/update/unique-update-concurrent-control/))
- CAP: the FE metadata layer is effectively **CP** (quorum edit-log; loses write availability without a Master quorum). Durability ([wal-and-durability](../concepts/wal-and-durability.md)): integrated mode relies on multi-replica BE writes; decoupled mode on durable object storage + FDB. No published Jepsen report. ⚠️ unverified — no formal external consistency verification of Doris exists as of 2026.

## Interfaces & integration
- **SQL** with strong **MySQL protocol** compatibility — any MySQL client/driver/BI tool connects; standard ANSI-ish SQL with window functions, CTEs, complex joins (cost-based optimizer), materialized views (sync and async), and a vectorized + pipeline execution engine.
- Ingestion: **Stream Load** (HTTP), **Routine Load** (consumes Kafka), **Broker/Insert Load**, **INSERT INTO ... SELECT**, Flink/Spark connectors, and Flink CDC for [change-data-capture](../concepts/change-data-capture.md) from OLTP sources.
- Indexes: sorted prefix keys, Min/Max (zone maps), BloomFilter, and **inverted indexes** for full-text search (positioned as an [elasticsearch](elasticsearch.md) alternative for log/text analytics).
- Lakehouse: external catalogs read Hive, [Iceberg](apache-iceberg.md), Hudi, Paimon, JDBC sources, and object-storage files; supports the [data-catalog](../concepts/data-catalog.md) federation pattern. Iceberg write support is more limited than read.

## Operations & maturity
- Low external-dependency footprint (no ZooKeeper in integrated mode) lowers day-2 burden vs ClickHouse clusters; decoupled mode adds FoundationDB + Meta Service to operate. Both FE and BE scale horizontally.
- Mature, widely deployed (originated at Baidu as "Palo," donated to ASF, graduated 2022). Governed by the **Apache Software Foundation**; primary commercial driver is **VeloDB** (founded by core committers), which offers a managed cloud and enterprise build.
- Known rough edges: merge-on-write amplifies write cost under heavy high-frequency upserts; compaction tuning matters for p99; many tiny imports cause version/compaction pressure (batch them); decoupled mode is newer (3.0, 2024) and operationally heavier than integrated.

## Licensing & cost
- **Apache License 2.0** — permissive, genuinely open ([license-taxonomy](../concepts/license-taxonomy.md)), no source-available relicensing. Self-host free.
- Managed/enterprise via VeloDB (cloud, usage/compute-based) or other vendors; possible lock-in only through proprietary VeloDB-specific features, not the OSS core.
- Cost model when self-hosted: standard node-based infra. Decoupled mode lets you cut storage cost (shared object storage, single data copy) and scale compute independently, Snowflake/[snowflake](snowflake.md)-style.

## Bottom line
- Reach for Doris when you want a single MySQL-compatible MPP warehouse that does both high-throughput aggregation *and* real-time row-level upserts/CDC serving, with fewer moving parts than ClickHouse and an easier SQL/join story than [Druid](apache-druid.md). The biggest gotcha: it is READ COMMITTED only with no Jepsen-grade verification, and merge-on-write upserts plus frequent small imports create compaction pressure that punishes naive high-frequency-tiny-write patterns — batch your loads and size compaction. Do not reach for it as an OLTP system or as a stream bus; it is a serving/analytics layer.

## Sources
- [What is Apache Doris (3.x docs)](https://doris.apache.org/docs/3.x/gettingStarted/what-is-apache-doris/)
- [Compute-storage decoupled overview](https://doris.apache.org/docs/3.0/compute-storage-decoupled/overview/)
- [Transaction & isolation docs](https://doris.apache.org/docs/3.x/data-operate/transaction/)
- [Load atomicity & exactly-once labels](https://doris.apache.org/docs/2.0/data-operate/import/load-atomicity/)
- [Unique Key table / merge-on-write](https://doris.apache.org/docs/dev/table-design/data-model/unique/)
- [Concurrency control for primary-key updates](https://doris.apache.org/docs/data-operate/update/unique-update-concurrent-control/)
- [Install FoundationDB (decoupled metadata store)](https://doris.apache.org/docs/3.0/install/deploy-on-kubernetes/separating-storage-compute/install-fdb/)
- [Release 3.0.0 notes](https://doris.apache.org/docs/3.x/releasenotes/v3.0/release-3.0.0/)
