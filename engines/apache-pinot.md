---
name: Apache Pinot
slug: apache-pinot
adjacent: true
rank: n/a
category: real-time-olap
data_model: Distributed columnar real-time OLAP datastore
license: Apache License 2.0 (permissive)
summary: Distributed columnar OLAP store built for sub-second, high-QPS queries on streaming-fresh data powering user- and agent-facing analytics.
last_researched: 2026-06-04
confidence: high
---

# Apache Pinot

> A distributed, columnar real-time OLAP datastore engineered for sub-second analytical queries at very high concurrency on data that is seconds-fresh from a Kafka-style stream — the engine behind "user-facing analytics" dashboards (LinkedIn, Uber).

## Identity / role
- **What it is:** a purpose-built [real-time-olap](../concepts/real-time-olap.md) datastore (originally LinkedIn, now ASF). It owns its own [columnar](../concepts/columnar-storage.md) storage format ("segments") *and* a distributed query engine. Unlike a [table format](../concepts/open-table-formats.md), it is not a metadata layer over someone else's files — it ingests, stores, indexes, and serves.
- **Its niche vs. peers:** optimized for **high-QPS (thousands of concurrent queries), low-latency (p99 < 1s), point-lookup-style analytical** queries on a known set of dashboards — the "user-facing analytics" workload. Contrast with [clickhouse](clickhouse.md) (great single-query throughput, fewer concurrent users) and [apache-druid](apache-druid.md) (closest architectural sibling). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **What it is NOT:** not an OLTP database (no general multi-row transactions), not a data warehouse for ad-hoc heavy joins over cold data (use [trino](trino.md)/[snowflake](snowflake.md)/[databricks](databricks.md)), and not a stream *processor* — it stores and serves; transformation/enrichment is done upstream in [apache-flink](apache-flink.md) or Kafka. JOINs exist (v2 engine) but are not its strength.

## How it fits
- **Cluster components** (coordinated by Apache Helix on ZooKeeper): **Controller** (cluster/segment metadata, assignment, validation), **Broker** (scatter-gather: routes a query to the servers holding relevant segments, merges results), **Server** (stores segments + executes query fragments), and optional **Minion** (background tasks: segment merge/rollup, purge, real-time-to-offline jobs). ([docs](https://docs.pinot.apache.org/basics/concepts/architecture))
- **Storage model:** data is sharded into immutable **segments** (columnar chunks with dictionaries + indexes). Tables come in two flavors: **offline** (batch-loaded segments) and **real-time** (consumed directly from a stream). A **hybrid** table unions both, with real-time serving fresh data and offline serving backfilled history.
- **Real-time ingestion:** servers consume directly from [Kafka](apache-kafka.md)/Kinesis/Pulsar into a mutable in-memory "consuming" segment; on reaching a row/time threshold the segment is **committed** — sealed, heavy indexes built, and pushed to the **deep store** (S3/HDFS/GCS), the durable system-of-record from which servers re-download on recovery. ([docs](https://startree.ai/resources/inside-the-flight-path-of-real-time-ingestion-in-apache-pinot/))
- **Pairs with:** Kafka/Pulsar/Kinesis upstream, [apache-flink](apache-flink.md)/Kafka Streams for pre-processing, S3/HDFS as deep store, Superset/Grafana/custom apps downstream.
- **Indexing is the differentiator:** forward, inverted, sorted, range, bloom, JSON, text, geospatial, and the **star-tree index** — a configurable pre-aggregated multi-column tree that bounds query latency by trading space for time, the key to sub-second aggregations on large data. ([docs](https://docs.pinot.apache.org/basics/indexing/star-tree-index))

## Guarantees & consistency
- **Delivery semantics:** real-time consumption is effectively **at-least-once**. Pinot tracks committed stream offsets and replays on recovery; per StarTree it "intentionally runs at-least-once to keep freshness and availability high" rather than paying the coordination cost of end-to-end exactly-once with the source. ([StarTree](https://startree.ai/resources/data-freshness-apache-pinot-vs-clickhouse/)) End-to-end exactly-once is achievable only by combining an exactly-once upstream (e.g. Flink) with Pinot **upserts** that dedup on primary key.
- **Upserts:** supported on real-time tables, but with a hard constraint — the **input stream must be partitioned by the primary key**, and **all segments of a partition must be served from the same server**, so the dedup state lives in one place. This couples upsert correctness to your Kafka partitioning and limits rebalancing flexibility. ([docs](https://docs.pinot.apache.org/manage-data/data-import/upsert-and-dedup/upsert))
- **Query/upsert consistency modes:** `SYNC` blocks upserts while a query reads validDocIds (consistent but contends); `SNAPSHOT` gives queries a consistent bitmap snapshot without blocking writes (better under high write+read). Default behavior can otherwise expose in-flight upsert updates.
- **ACID:** N/A — no multi-statement transactions; mutability is limited to upsert/dedup on real-time tables. Segments are otherwise immutable. There is no [serializable isolation](../concepts/isolation-levels.md) notion; queries are best-effort consistent over the segments currently served.
- **CAP:** leans **AP/availability-first** for ingestion — favors staying up and fresh; recovery from deep store + offsets restores correctness. Not a strongly-consistent transactional store; do not treat it as a source of truth (the upstream log is the source of truth). See [cap-pacelc](../concepts/cap-pacelc.md), [wal-and-durability](../concepts/wal-and-durability.md).

## Interfaces & integration
- **Query language:** SQL. The **multi-stage query engine (v2)** (GA from Pinot 1.0) adds ANSI-SQL features including **all JOIN types**, window functions, and distributed shuffles; the older single-stage engine handles fast scatter-gather aggregations/filters. ([docs](https://docs.pinot.apache.org/reference/multi-stage-engine)) JOINs and complex correlations work but are not where Pinot wins versus [trino](trino.md)/[starrocks](starrocks.md).
- **Ingestion connectors:** Kafka, Kinesis, Pulsar (real-time); batch ingestion from S3/HDFS/GCS via Spark/Hadoop/standalone jobs. CDC via [Debezium](../concepts/change-data-capture.md)→Kafka→Pinot upsert tables is a common pattern.
- **Client/BI:** JDBC, REST query endpoint, Java/Python/Go clients; integrates with Superset, Grafana, Trino (Pinot connector), Presto.
- **Format interop:** Pinot's segment format is **proprietary to Pinot** — it is not an open lakehouse table format. ⚠️ unverified — direct external reads of Pinot segments by Spark/Trino go *through Pinot* (connectors query the cluster), not by reading segment files as an open format the way [Iceberg](apache-iceberg.md) is read.

## Operations & maturity
- **Maturity:** battle-tested at very large scale (LinkedIn — origin, Uber, Stripe, Walmart, Slack, Target). Top-level ASF project (graduated 2021). Real-time analytics at hundreds of thousands of QPS in production.
- **Ops burden:** **high.** A production cluster requires ZooKeeper, controllers, brokers, servers, a deep store, and an upstream stream — many moving parts to size, monitor, and rebalance. Segment assignment, tiered storage, retention, and upsert co-location all need deliberate configuration. Minion tasks (merge/rollup, purge) add another subsystem.
- **Known sharp edges:** upsert tables constrain partitioning/rebalancing (see above); memory pressure from consuming segments and many indexes; rebalancing large clusters is operationally delicate; the v2 multi-stage engine, while capable, is newer and less mature than the core scatter-gather path.
- **Governance:** vendor-neutral Apache project; **StarTree** is the primary commercial driver (founded by Pinot creators) offering StarTree Cloud (managed Pinot) and contributing most development — a single-vendor-heavy community in practice.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md). ([LICENSE](https://github.com/apache/pinot/blob/master/LICENSE))
- **Open vs vendor-controlled:** fully open core; no proprietary core features gating production use. StarTree adds proprietary tiered-storage/managed features on top.
- **Self-host vs managed:** self-hostable (your own cluster + deep store + ZooKeeper), or fully managed via StarTree Cloud (and similar). Self-hosting is real engineering work.
- **Cost model:** self-hosted = infra cost (servers are memory- and CPU-heavy; deep store is cheap object storage). Managed = vendor pricing, typically compute/storage-tiered.

## Bottom line
Reach for Pinot when you need **sub-second analytics at high concurrency on freshly-streamed data** — user-facing dashboards, real-time metrics for many simultaneous users, or agent-facing lookups — and you can invest in operating a multi-component cluster fed by Kafka. Do **not** reach for it as a general data warehouse, for ad-hoc heavy multi-table joins over historical data ([trino](trino.md)/[snowflake](snowflake.md)/[databricks](databricks.md) win there), for low-concurrency batch analytics ([clickhouse](clickhouse.md)/[duckdb](duckdb.md) are simpler), or as a transactional system of record. The single biggest gotcha: **upserts force primary-key partitioning of the input stream and co-location of a partition's segments on one server**, tightly coupling correctness to your Kafka layout and constraining rebalancing — design this before you ingest, not after.

## Sources
- [Apache Pinot — Architecture (official docs)](https://docs.pinot.apache.org/basics/concepts/architecture)
- [Star-tree index (official docs)](https://docs.pinot.apache.org/basics/indexing/star-tree-index)
- [Stream ingestion with Upsert (official docs)](https://docs.pinot.apache.org/manage-data/data-import/upsert-and-dedup/upsert)
- [Multi-stage query engine v2 (official docs)](https://docs.pinot.apache.org/reference/multi-stage-engine)
- [Inside the flight path of real-time ingestion in Apache Pinot (StarTree)](https://startree.ai/resources/inside-the-flight-path-of-real-time-ingestion-in-apache-pinot/)
- [Measuring data freshness: Pinot vs ClickHouse (StarTree)](https://startree.ai/resources/data-freshness-apache-pinot-vs-clickhouse/)
- [Apache Pinot LICENSE (Apache 2.0)](https://github.com/apache/pinot/blob/master/LICENSE)
- [Apache Pinot — Wikipedia](https://en.wikipedia.org/wiki/Apache_Pinot)
