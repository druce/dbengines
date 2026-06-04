---
name: Debezium
slug: debezium
adjacent: true
rank: n/a
category: cdc
data_model: Log-based change-data-capture platform
license: Apache License 2.0 (permissive)
summary: Open-source log-based CDC that turns a database's transaction log into an ordered stream of row-level change events.
last_researched: 2026-06-04
confidence: high
---

# Debezium

> Debezium tails a database's write-ahead/replication log and emits each committed row change as a structured event — it is a CDC pipeline, not a database or a query engine.

## Identity / role
- **What it is:** a log-based [change-data-capture](../concepts/change-data-capture.md) platform. Source-database connectors read the transaction log (Postgres logical WAL/`pgoutput`, MySQL/MariaDB binlog, Oracle LogMiner/OpenLogReplicator, SQL Server CDC tables, MongoDB oplog/change streams) and produce one row-level `INSERT`/`UPDATE`/`DELETE` event per change, with `before`/`after` images plus source metadata (LSN, transaction id, timestamp).
- **What it is NOT:** not a database, not a message broker, not a stream processor, not a query engine. It is the *capture* stage. It does not store data long-term, does not transform/join streams beyond lightweight single-message transforms (SMTs), and does not serve queries. Pair it with a transport ([apache-kafka](apache-kafka.md), Pulsar, Kinesis) and a sink/processor ([apache-flink](apache-flink.md), [apache-spark-sql](apache-spark-sql.md), a warehouse, [clickhouse](clickhouse.md)).
- It is a building block for replication, cache invalidation, search-index sync, event sourcing, and feeding [lakehouse](../concepts/lakehouse.md)/[real-time-olap](../concepts/real-time-olap.md) systems from operational [OLTP](../concepts/oltp-olap-htap.md) stores without dual-writes.

## How it fits
- **Three runtimes, one connector core:**
  - **Kafka Connect (classic):** Debezium connectors run as Kafka Connect source connectors; change events land in [apache-kafka](apache-kafka.md) topics (one topic per captured table by default). Connect provides distributed workers, offset/config/status storage, and rebalancing. This is the most battle-tested mode.
  - **Debezium Server:** a standalone app that runs a single connector and writes to a non-Kafka sink — Kinesis, Google Pub/Sub, Pulsar, Azure Event Hubs, RabbitMQ, Redis Streams, NATS, an HTTP endpoint, and a native Apache Iceberg sink (and vector sinks such as Milvus/Qdrant in recent releases). No Kafka required.
  - **Debezium Engine (embedded):** the `io.debezium.engine.DebeziumEngine` Java API embeds capture directly inside your application — no external service. You own offset management and delivery; fewer guarantees come for free.
- **Snapshot then stream:** on first start a connector takes a consistent **snapshot** of existing rows, then switches to tailing the log. **Incremental snapshots** (signal-table or read-only/Kafka-signal driven) let you (re)snapshot tables in configurable chunks while streaming continues, avoiding a long blocking lock.
- **Schema history:** relational connectors persist captured DDL to a **schema history topic** so events are decoded against the schema in force at the time of each change; losing/corrupting this topic breaks the connector.

## Guarantees & consistency
- **Delivery — default is at-least-once.** Debezium guarantees no change is skipped, but on crash/restart it may **re-emit** events already produced; consumers must be idempotent or key-dedup. ([Debezium blog: "Towards exactly-once delivery"](https://debezium.io/blog/2023/06/22/towards-exactly-once-delivery/) explicitly states the historical target was at-least-once.)
- **Exactly-once is available but conditional.** Debezium 3.x added exactly-once semantics for core connectors (MariaDB, MongoDB, MySQL, Oracle, PostgreSQL, SQL Server) **when run on Kafka Connect with EOS enabled** (Kafka transactions / `exactly.once.source.support`). It is *not* automatic and does not apply to Debezium Server / Engine sinks the same way. Treat "exactly-once" as a Kafka-Connect-with-correct-config property, not a default. ([Debezium 3.3 release notes](https://debezium.io/blog/2025/10/01/debezium-3-3-final-released/))
- **Ordering:** events for a given table/source are delivered in **commit order** (per source partition). Cross-table/global ordering is not guaranteed once events are spread across topics/partitions; use the source LSN/txid metadata or the transaction-metadata topic to reconstruct it.
- **Durability / data-loss window:** capture position is tracked by committed offsets. Risk is on the *source* side: if a database recycles its log (binlog expiry, replication-slot drop) before Debezium reads it, those changes are lost permanently. See [wal-and-durability](../concepts/wal-and-durability.md).
- **CAP/[isolation-levels](../concepts/isolation-levels.md):** N/A — Debezium is a stream of already-committed changes, not a transactional store. It reflects the source DB's isolation; it adds no transactions of its own (it can group events by source transaction but does not provide cross-record atomicity to consumers).

## Interfaces & integration
- **Event format:** JSON or Avro/Protobuf via a schema registry; pluggable converters. Optional **CloudEvents** envelope. SMTs (e.g. `ExtractNewRecordState`/unwrap, routing, filtering, content-based routing) shape events in flight.
- **Sources:** PostgreSQL, MySQL, MariaDB, MongoDB, Oracle, SQL Server, Db2, Cassandra, Vitess, Spanner, Informix, JDBC-based and others (maturity varies by connector — Postgres/MySQL/MongoDB/SQL Server are the most mature; Oracle and the newer ones are less so).
- **Consumed by:** anything reading Kafka/Pulsar/Kinesis — [apache-flink](apache-flink.md), Kafka Streams, [apache-spark-sql](apache-spark-sql.md) Structured Streaming, ksqlDB, and sink connectors into [snowflake](snowflake.md), [clickhouse](clickhouse.md), Elasticsearch, JDBC targets, and Iceberg tables ([open-table-formats](../concepts/open-table-formats.md)). Common as the CDC source feeding a [lakehouse](../concepts/lakehouse.md) or a [streaming database](../concepts/streaming-databases.md).

## Operations & maturity
- **Maturity:** the de facto open-source CDC standard; widely deployed in production, founded by Red Hat, now a CNCF Sandbox project. Strong community and docs.
- **Ops burden:** non-trivial. Kafka Connect mode means operating Connect (and Kafka) — connector restarts, rebalancing, offset/schema-history topic care. Key failure modes: PostgreSQL **replication-slot WAL retention** (an inactive/lagging slot pins WAL and can fill the source disk), MySQL **binlog expiry** racing the connector, large initial snapshots, and schema-history loss requiring a re-snapshot. Heavy DDL and very wide tables stress the connector.
- **Governance:** Apache-licensed community project (vendor-neutral CNCF) with a commercially supported Red Hat build; many managed offerings (Confluent, AWS MSK Connect, Decodable, Estuary, etc.) wrap or reimplement it.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Cost:** the software is free. Real cost is the surrounding infrastructure (Kafka/Connect clusters, or a managed CDC service) and operational expertise. Self-host is fully open; managed-CDC vendors charge per connector/throughput/data volume.

## Bottom line
- Reach for Debezium when you need reliable, low-impact, log-based CDC out of a mainstream OLTP database and want an open, non-proprietary capture layer feeding Kafka, a lakehouse, or a stream processor. It is the safe default for "stream my Postgres/MySQL changes." **Anti-patterns:** treating it as turnkey exactly-once (default is at-least-once — build idempotent consumers), or running it without operating Kafka/Connect and watching source-side log retention. The single biggest gotcha is the source database's log: a stalled Postgres replication slot or expired MySQL binlog can fill disks or lose changes — monitor slot lag and binlog retention from day one.

## Sources
- [Debezium Architecture (official docs)](https://debezium.io/documentation/reference/stable/architecture.html)
- [Debezium blog: Towards exactly-once delivery (2023)](https://debezium.io/blog/2023/06/22/towards-exactly-once-delivery/)
- [Debezium 3.3.0.Final release notes (exactly-once for core connectors)](https://debezium.io/blog/2025/10/01/debezium-3-3-final-released/)
- [Debezium 3.4.0.Final release notes](https://debezium.io/blog/2025/12/16/debezium-3-4-final-released/)
- [Incremental Snapshots in Debezium](https://debezium.io/blog/2021/10/07/incremental-snapshots/)
- [Debezium Server (sinks) docs](https://debezium.io/documentation/reference/stable/operations/debezium-server.html)
- [The Debezium Trio: Kafka Connect vs Server vs Engine (Sequin)](https://blog.sequinstream.com/the-debezium-trio-comparing-kafka-connect-server-and-engine-run-times/)
- [Debezium GitHub](https://github.com/debezium/debezium)
