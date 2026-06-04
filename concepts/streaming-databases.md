---
name: Streaming Databases
slug: streaming-databases
summary: Databases that compute over unbounded streams and keep results continuously fresh via incremental view maintenance — Materialize, RisingWave, ksqlDB. The spectrum runs from stream processor to streaming DB to real-time OLAP.
last_researched: 2026-06-04
---

# Streaming Databases

> A **streaming database** runs SQL over never-ending input streams and keeps the answer
> **continuously up to date** as new events arrive, instead of re-scanning on each query. The key
> technique is **incremental view maintenance (IVM)**: when a row changes, only the affected part of
> the result is recomputed. You write a `CREATE MATERIALIZED VIEW`; it stays fresh.

## The spectrum (don't conflate these)
1. **Stream processors** — code/operators over streams; you manage state and outputs.
   [apache-flink](../engines/apache-flink.md) (stateful, event-time, exactly-once), Kafka Streams, Spark Structured Streaming.
   Powerful, lower-level; not a queryable DB by themselves.
2. **Streaming databases** — SQL + persisted, queryable, incrementally-maintained views:
   - **[materialize](../engines/materialize.md)** — Postgres-wire; strongly-consistent IVM (Timely/Differential Dataflow);
     correct, low-latency materialized views.
   - **[risingwave](../engines/risingwave.md)** — Postgres-wire, cloud-native (storage/compute separated); IVM with
     [S3-backed](storage-compute-separation.md) state.
   - **[ksqldb](../engines/ksqldb.md)** — Kafka-native streaming SQL over Kafka Streams; tied to the [apache-kafka](../engines/apache-kafka.md) log.
3. **Real-time OLAP** — ingest streams and serve **ad-hoc** low-latency aggregations (you write the
   queries, not pre-defined views): [apache-pinot](../engines/apache-pinot.md), [apache-druid](../engines/apache-druid.md), [clickhouse](../engines/clickhouse.md),
   [apache-doris](../engines/apache-doris.md). See [real-time-olap](real-time-olap.md).

## Event-time vs processing-time
Real streams arrive late and out of order. Mature engines reason about **event time** with
**watermarks** (how long to wait for stragglers) and **windowing** (tumbling/sliding/session) — not
just wall-clock arrival ([clocks-and-time](clocks-and-time.md)). Correct handling of late data is the hard part and a
key differentiator.

## Guarantees
**Exactly-once** end-to-end requires the whole chain — idempotent/transactional source
([streaming-platforms](streaming-platforms.md)), checkpointed processor state, and idempotent sink — not just one box.
Consistency of the *served view* varies: Materialize targets strong consistency (the view reflects a
consistent prefix of inputs); many systems are eventually consistent. Verify the specific claim.

## How to use it on adjacent pages
Place the engine on the spectrum (processor / streaming DB / real-time OLAP), note IVM vs ad-hoc,
event-time/watermark support, exactly-once scope, and the serving consistency. Anti-pattern: using a
stream processor where you actually need a queryable store, or a streaming DB for heavy ad-hoc OLAP.
