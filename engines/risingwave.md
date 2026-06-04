---
name: RisingWave
slug: risingwave
adjacent: true
rank: n/a
category: streaming-database
data_model: Streaming SQL database (incremental materialized views)
license: Apache 2.0 (core); premium features gated behind a paid license key
summary: Postgres-wire streaming SQL database that maintains incremental materialized views over event streams, with all state on S3-compatible object storage.
last_researched: 2026-06-04
confidence: high
---

# RisingWave

> A PostgreSQL-compatible streaming database: you write SQL `CREATE MATERIALIZED VIEW` over Kafka/CDC streams and it keeps them incrementally up to date with sub-second latency, storing all streaming state in object storage instead of local disk.

## When to use

**Use RisingWave if:**
- ✅ You want streaming transformations expressed as SQL materialized views that are also directly queryable over the Postgres wire protocol.
- ✅ You'd otherwise stitch together Debezium + Kafka + Flink + a serving DB and prefer SQL over Flink's Java/DataStream API.
- ✅ You want cheap object-storage state (no provisioned SSD/JVM) and Iceberg as the durable lakehouse output.

**Avoid RisingWave if:**
- ❌ You need a general-purpose OLTP database or a heavy ad-hoc OLAP warehouse — it is built for continuous incremental computation, not point writes or large scans.
- ❌ You need custom imperative operators or complex-event-processing (`MATCH_RECOGNIZE`) that Flink's DataStream API provides.
- ❌ You assume end-to-end exactly-once for free — it is only as strong as the sink connector, and large stateful pipelines are memory-sensitive despite S3-backed state.
- ❌ You need every production feature in the Apache 2.0 core — some sit behind the paid premium license.

## Identity / role
- **What it IS:** a distributed [streaming database](../concepts/streaming-databases.md) written in Rust. Unlike a pure stream processor, it both *processes* streams (incremental materialized views) and *stores + serves* the results as a queryable database over the Postgres wire protocol. Sits in the compute+state layer of a real-time stack.
- **What it is NOT:** not a message broker / event log (it consumes from [apache-kafka](apache-kafka.md), it is not Kafka); not a general-purpose [OLTP](../concepts/oltp-olap-htap.md) database (it is built for continuous incremental computation, not high-rate point writes/updates of arbitrary rows); not a batch OLAP warehouse like [snowflake](snowflake.md) or [clickhouse](clickhouse.md) (ad-hoc large scans are not its strength).
- Closest comparison is [apache-flink](apache-flink.md) SQL — but Flink is a stateful compute engine that does not persist/serve user data, whereas RisingWave is a database that can be queried directly. ([RisingWave vs Flink](https://risingwave.com/blog/risingwave-and-apache-flink-sql-a-comparison-2/))

## How it fits
- **Architecture:** disaggregated compute-storage ([storage-compute-separation](../concepts/storage-compute-separation.md)). Four node types: stateless **Frontend** (Postgres protocol proxy + SQL optimizer), **ComputeNode** (runs the streaming dataflow), stateless **Compactor** (compaction of the state store), and **MetaServer** (metadata/coordination). All streaming state — operator state, internal tables, materialized views — lives in S3-compatible object storage via an LSM-style state store ("Hummock"), not on local SSD. ([docs](https://docs.risingwave.com/get-started/intro), [dbdb.io](https://dbdb.io/db/risingwave))
- **Problem it solves:** replaces the assemble-it-yourself stack of Debezium + Kafka + Flink + a serving DB with one SQL system. You ingest, transform, and serve in the same engine.
- **Pairs with:** [apache-kafka](apache-kafka.md)/Pulsar/Kinesis as sources; Postgres/MySQL [CDC](../concepts/change-data-capture.md) as sources; [apache-iceberg](apache-iceberg.md) as the long-term/lakehouse sink (and as a source) — Iceberg tables are then readable by [trino](trino.md), [apache-spark-sql](apache-spark-sql.md), [snowflake](snowflake.md), [duckdb](duckdb.md), etc. Query layer uses Apache DataFusion for batch/Iceberg reads.

## Guarantees & consistency
- **Delivery semantics:** exactly-once internal processing via consistent snapshots and **barrier-based checkpointing** using the Chandy–Lamport algorithm; materialized views are claimed to stay consistent even across multi-way joins and complex pipelines. ([docs/intro](https://docs.risingwave.com/get-started/intro), vendor blog). End-to-end exactly-once depends on the sink: it requires a sink that supports transactional/idempotent writes (e.g. Kafka transactions, Iceberg commits) — otherwise the practical guarantee at the sink degrades to at-least-once. ⚠️ unverified — per-sink exactly-once support varies by connector; check the specific sink's docs.
- **Event-time vs processing-time:** supports event-time processing with watermarks and time windows (tumbling/hopping/session), so out-of-order/late data is handled on event time, not just arrival time.
- **Read consistency:** reads are served from the most recent committed checkpoint, so a query sees a globally consistent snapshot of all materialized views rather than partial mid-update state.
- **Durability / data-loss window:** state and checkpoints are persisted to object storage; the data-loss exposure on crash is bounded by the checkpoint/barrier interval (work since the last checkpoint is replayed from source offsets on recovery, requiring replayable sources like Kafka). See [wal-and-durability](../concepts/wal-and-durability.md).
- **CAP/isolation:** N/A in the classic transactional sense — this is a streaming dataflow system, not a multi-statement OLTP store; the meaningful guarantee is snapshot-consistent materialized views, not [serializable transactions](../concepts/isolation-levels.md).

## Interfaces & integration
- **Language:** SQL, wire-compatible with the **PostgreSQL protocol v3.0** — connect with psql, JDBC, psycopg2, and most Postgres tooling/BI clients. Dialect is Postgres-flavored but is *not* full Postgres (no general OLTP feature parity); the headline objects are `CREATE SOURCE`, `CREATE MATERIALIZED VIEW`, and `CREATE SINK`. ([PG compatibility](https://risingwave.com/glossary/postgresql-compatibility/))
- **Sources:** Kafka, Pulsar, Kinesis, webhooks, Postgres/MySQL CDC, S3 batch files, Iceberg.
- **Sinks:** Kafka, Postgres/MySQL, ClickHouse, Iceberg, Delta Lake, data warehouses, etc. Native **Iceberg table engine / "Open Lake"** for managed Iceberg ingestion with automatic compaction and schema evolution.
- **Programmatic:** UDFs in Python/Java/Rust/JavaScript; an MCP server is offered for agent/LLM access.
- **Interop note:** because results land in [Iceberg](apache-iceberg.md) (open table format), downstream engines read RisingWave output without a proprietary client.

## Operations & maturity
- **Deployment:** single-binary/Docker for dev; distributed cluster (k8s operator) for production; or **RisingWave Cloud** fully managed (SOC 2 / GDPR / HIPAA per vendor). Requires an object store (S3/GCS/MinIO) and a meta-store backend.
- **Ops burden:** lighter than self-managing Flink+Kafka+Zookeeper+a serving DB — fewer moving parts, no JVM tuning, elastic compute scaling against shared object storage. Tradeoff: object-storage state means latency/throughput depend on caching working state in compute-node memory, and large stateful joins/aggregations are memory-sensitive.
- **Maturity:** younger than [apache-flink](apache-flink.md) (RisingWave Labs founded ~2021; v1.0 in 2023). Production users exist but the track record is shorter; no public Jepsen report. ⚠️ unverified — no independent formal verification of the exactly-once/consistency claims is publicly available; claims are vendor-stated.
- **Known limits vs Flink:** Flink is still preferred for custom Java operators, the low-level DataStream API, and `MATCH_RECOGNIZE`-style complex event processing (per vendor's own comparison). RisingWave is SQL-first and does not expose an equivalent imperative dataflow API.
- **Governance:** single-vendor open source (RisingWave Labs), not an Apache Software Foundation project — direction and premium gating are vendor-controlled.

## Licensing & cost
- **Core engine:** Apache 2.0 (permissive) — deploy, modify, distribute in production freely. See [license-taxonomy](../concepts/license-taxonomy.md). ([GitHub](https://github.com/risingwavelabs/risingwave))
- **Premium features:** a set of enterprise features are built on top of the Apache-licensed Community Edition and require a **paid license key** on self-managed clusters (free trial limited to clusters ≤ 4 RWUs). ([Premium features](https://docs.risingwave.com/get-started/premium-features)) This is the lock-in vector: the OSS core is permissive, but some advanced/connector/operational features are gated.
- **Cost model:** self-host cost is dominated by compute nodes + cheap object storage (vendor markets ~10x cost efficiency vs Flink by avoiding provisioned SSD and JVM overhead — a vendor benchmark claim, treat as directional). Managed RisingWave Cloud is usage/RWU-based.

## Bottom line
- Reach for RisingWave when you want **streaming transformations expressed as SQL materialized views that are also directly queryable**, with low operational overhead and cheap object-storage state — i.e. you'd otherwise stitch together Kafka + Flink + a serving database. It is especially attractive for teams that prefer SQL over Flink's Java/DataStream API and want Iceberg as the durable output. Do **not** reach for it as a general-purpose OLTP database, as a heavy ad-hoc OLAP warehouse, or when you need custom imperative operators / complex-event-processing patterns that Flink's DataStream API provides. **Biggest gotcha:** end-to-end exactly-once is only as strong as the sink connector, and large stateful pipelines are memory-sensitive despite state living on S3 — and some "production-grade" features sit behind the paid premium license, so audit the feature list before assuming the Apache 2.0 core covers your needs.

## Sources
- [What is RisingWave? (official docs)](https://docs.risingwave.com/get-started/intro)
- [RisingWave GitHub README](https://github.com/risingwavelabs/risingwave)
- [PostgreSQL compatibility](https://risingwave.com/glossary/postgresql-compatibility/)
- [Premium features (license gating)](https://docs.risingwave.com/get-started/premium-features)
- [RisingWave and Apache Flink SQL: A Comparison](https://risingwave.com/blog/risingwave-and-apache-flink-sql-a-comparison-2/)
- [Iceberg Table Engine in RisingWave](https://www.risingwave.com/blog/risingwave-iceberg-table-engine/)
- [Database of Databases — RisingWave](https://dbdb.io/db/risingwave)
