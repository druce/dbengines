---
name: Real-Time OLAP
slug: real-time-olap
summary: Analytical stores that ingest fresh (often streaming) data and serve sub-second ad-hoc aggregations at high concurrency — Pinot, Druid, ClickHouse, StarRocks, Doris. The query-serving end of the streaming stack.
last_researched: 2026-06-04
---

# Real-Time OLAP

> **Real-time OLAP** stores combine two things classic warehouses don't do well together: **fresh
> ingestion** (events queryable seconds after they happen) and **sub-second, high-concurrency ad-hoc
> aggregations** over large data. They are the **serving layer** for user-facing analytics,
> dashboards, and observability — distinct from [streaming-databases](streaming-databases.md) (pre-defined incrementally
> maintained views) because here *you write the queries at read time*.

## What makes them fast
- **[Columnar](columnar-storage.md)** layout + heavy compression + vectorized execution.
- **Pre-aggregation / indexing** — inverted, star-tree, bitmap, and sorted indexes (Pinot/Druid) to
  prune and pre-roll; sorted/merge-tree parts (ClickHouse).
- **Streaming + batch ingestion** — consume directly from [Kafka](streaming-platforms.md) for
  real-time rows, plus batch backfill; a hot/realtime tier merged with a historical tier.
- **High read concurrency** — designed for thousands of concurrent dashboard/API queries, not just a
  few analyst sessions.

## The stores
- **[apache-pinot](../engines/apache-pinot.md)** — LinkedIn/Uber-born; rich indexing (star-tree), built for user-facing
  analytics at very high QPS and low latency.
- **[apache-druid](../engines/apache-druid.md)** — time-partitioned segments; great for time-series slice-and-dice and
  exploratory analytics; weak joins.
- **[clickhouse](../engines/clickhouse.md)** — general columnar OLAP; blazing scans, increasingly used as a real-time store;
  eventually consistent, async merges.
- **[apache-doris](../engines/apache-doris.md)** / **[starrocks](../engines/starrocks.md)** — MPP columnar with better **JOIN** support and MySQL
  protocol; lean toward real-time data-warehouse use.

## The trade-offs / anti-patterns
- **Not OLTP and not a system of record** — append/ingest-oriented, limited or no row-level
  updates/transactions; pair with a durable source ([oltp-olap-htap](oltp-olap-htap.md)).
- **Joins vary widely** — Druid/Pinot historically weak on large joins; Doris/StarRocks stronger.
  Pick by whether your workload is single-table slice-and-dice or join-heavy.
- **Denormalize for speed** — like [wide-column](wide-column.md) stores, you often model for the query.

## How to use it on engine/adjacent pages
Note ingestion sources (Kafka/batch), indexing strategy, join capability, concurrency target,
update/transaction support, and freshness. Distinguish from a batch warehouse ([snowflake](../engines/snowflake.md),
[google-bigquery](../engines/google-bigquery.md)) and from [IVM streaming DBs](streaming-databases.md).
