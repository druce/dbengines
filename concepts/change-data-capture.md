---
name: Change Data Capture (CDC)
slug: change-data-capture
summary: Stream a database's row-level changes (insert/update/delete) out of its transaction log in commit order — the low-overhead way to replicate OLTP data into lakes, warehouses, search, and caches.
last_researched: 2026-06-04
---

# Change Data Capture (CDC)

> **CDC** captures every row-level change in a source database and emits it as an ordered stream of
> events, so downstream systems stay in sync without re-querying. The good implementations read the
> **transaction/replication log** ([WAL](wal-and-durability.md)/binlog/redo) rather than polling — low
> overhead, complete (no missed changes), and in **commit order**.

## Log-based vs query-based
- **Log-based (preferred)** — tail the source's replication log (Postgres logical decoding, MySQL
  binlog, Oracle redo, Mongo oplog). Captures deletes, preserves order, minimal load on the source.
- **Query-based (polling)** — repeatedly `SELECT ... WHERE updated_at > x`. Simple but misses
  deletes, adds load, and can skip intermediate states. A fallback, not the goal.

## What it's used for
- **Lake/warehouse ingestion** — land OLTP changes into a [lakehouse](lakehouse.md) / [table
  format](open-table-formats.md) (Hudi/Iceberg/Delta) or a [real-time OLAP](real-time-olap.md) store, kept current.
- **Replication & migration** — keep a replica, cache, or [search index](full-text-search.md)
  ([elasticsearch](../engines/elasticsearch.md)) in sync with the system of record.
- **Event-driven architecture** — turn DB changes into events on a [log](streaming-platforms.md)
  ([apache-kafka](../engines/apache-kafka.md)), often via the **outbox pattern** to get exactly-once-ish, ordered domain events.

## Tools
- **[debezium](../engines/debezium.md)** — the dominant open-source log-based CDC platform; source connectors for
  Postgres/MySQL/Mongo/SQL Server/Oracle, emitting to [apache-kafka](../engines/apache-kafka.md) (via Kafka Connect) or
  embedded. **Flink CDC** brings Debezium connectors into [apache-flink](../engines/apache-flink.md) pipelines; many warehouses
  and [streaming-databases](streaming-databases.md) ingest CDC natively.

## Caveats to flag
- **Ordering & exactly-once** hold only end-to-end: ordered log + idempotent/transactional delivery +
  idempotent sink. At-least-once with duplicates is the common reality — sinks must dedupe/upsert.
- **Schema changes (DDL)** in the source can break or stall a CDC pipeline; schema evolution handling
  varies.
- **Snapshot + stream** — initial load (snapshot) then switch to streaming; the handover is a classic
  source of gaps/dupes if done naively.

## How to use it on engine/adjacent pages
For source DBs, note whether log-based CDC is available (logical replication/binlog/oplog) and its
maturity. For sinks, note native CDC ingest. Tie to [streaming-platforms](streaming-platforms.md) and [debezium](../engines/debezium.md).
