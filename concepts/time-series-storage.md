---
name: Time-Series Storage
slug: time-series-storage
summary: Append-heavy, timestamp-ordered data with high ingest and time-windowed queries — handled with columnar compression, time partitioning, downsampling, and retention/TTL.
last_researched: 2026-06-04
---

# Time-Series Storage

> Time-series data is a relentless stream of timestamped points (metrics, sensors, events, trades):
> **write-once, append-mostly, rarely updated**, queried over time windows and aggregated. That
> shape lets specialized engines beat general databases on ingest rate and storage efficiency.

## What makes the workload special
- **Append-only, time-ordered** — inserts at "now"; almost no random updates/deletes.
- **High cardinality** — many series (metric × tag combinations); cardinality explosion is the
  classic failure mode.
- **Time-windowed queries** — "last 24h", rollups per minute/hour; recent data hot, old data cold.
- **Aging out** — data has a retention horizon; old data is downsampled or dropped.

## The storage techniques
- **Time partitioning / chunking** — split by time window so writes hit the newest chunk and old
  chunks are dropped cheaply (TTL/retention) and compressed independently. [timescaledb](../engines/timescaledb.md) hypertables,
  InfluxDB shards.
- **[Columnar](columnar-storage.md) + specialized compression** — delta-of-delta on timestamps,
  XOR/Gorilla on floats, run-length on tags → often 10×+ compression. (Facebook's Gorilla paper is
  the canonical reference.)
- **[LSM](lsm-vs-btree.md) ingest path** — buffer in memory, flush sorted, compact — matches the
  append-heavy pattern.
- **Downsampling / continuous aggregates / rollups** — precompute lower-resolution series for fast
  long-range queries; keep raw data short, rollups long.

## Engines
Dedicated: [influxdb](../engines/influxdb.md), [timescaledb](../engines/timescaledb.md) (on [postgresql](../engines/postgresql.md)), [prometheus](../engines/prometheus.md) (monitoring, pull-based),
[victoriametrics](../engines/victoriametrics.md), [questdb](../engines/questdb.md), [tdengine](../engines/tdengine.md), [apache-iotdb](../engines/apache-iotdb.md), [graphite](../engines/graphite.md), [dolphindb](../engines/dolphindb.md),
[kdb](../engines/kdb.md) (finance). Analytics engines often double as TSDBs: [apache-druid](../engines/apache-druid.md),
[microsoft-azure-data-explorer](../engines/microsoft-azure-data-explorer.md), [clickhouse](../engines/clickhouse.md).

## How to use it on engine pages
Note time-partitioning/retention, compression scheme, ingest rate vs cardinality limits,
downsampling/continuous-aggregate support, and the query language (PromQL, InfluxQL/Flux, SQL).
Flag whether it's a true TSDB or a general engine with a time-series extension.
