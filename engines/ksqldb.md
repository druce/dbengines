---
name: ksqlDB
slug: ksqldb
adjacent: true
rank: n/a
category: streaming-database
data_model: Streaming SQL DB (over Kafka topics)
license: Confluent Community License (source-available, not OSI)
summary: Kafka-native streaming SQL layer over Kafka Streams; great for simple Kafka-in/Kafka-out transforms, now superseded by Flink as Confluent's strategic engine.
last_researched: 2026-06-04
confidence: high
---

# ksqlDB

> A SQL veneer over [Kafka Streams](../concepts/streaming-databases.md) that turns continuous Kafka topic processing into `CREATE STREAM ... AS SELECT` statements — convenient for Kafka-centric ETL, but Kafka-bound and now in strategic maintenance behind [Flink](apache-flink.md).

## When to use

**Use ksqlDB if:**
- ✅ You are already all-in on Kafka and want lightweight, SQL-expressed stream transforms and enrichments without writing Kafka Streams Java
- ✅ You need simple Kafka-in/Kafka-out ETL with joins, windowed aggregations, and materialized key/range lookups (pull queries)
- ✅ You want exactly-once processing within the Kafka boundary (`exactly_once_v2`)

**Avoid ksqlDB if:**
- ❌ It only knows Kafka and is on a maintenance track behind [Flink](apache-flink.md) — new complex pipelines risk a future migration
- ❌ You need a general database for ad-hoc analytical queries (pull queries are key-lookups on materialized tables, not OLAP)
- ❌ You need rich ANSI SQL, sources beyond Kafka, parallelism past your partition count, or a permissive OSI license (it is source-available Confluent Community)

## Identity / role
- ksqlDB is a **stream processing database**: you write SQL against [Kafka](apache-kafka.md) topics and it continuously computes derived streams and materialized tables. It sits in the **compute** layer of a [streaming platform](../concepts/streaming-platforms.md), not storage — all durable state lives in Kafka topics.
- What it is NOT: it is **not a general-purpose database** (no arbitrary OLTP/OLAP queries over external data), **not a standalone storage engine** (Kafka is the source of truth), and **not a transport/broker** (Kafka is). It is a thin, SQL-shaped front end to [Kafka Streams](../concepts/streaming-databases.md).
- Compared to a [streaming database](../concepts/streaming-databases.md) like [materialize](materialize.md) or [risingwave](risingwave.md), ksqlDB is tightly coupled to one system (Kafka) and far narrower in SQL scope. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) for where streaming compute fits.

## How it fits
- Architecture: the ksqlDB engine parses each SQL statement into a **Kafka Streams topology** and runs it inside a JVM ("ksqlDB Server"). Source data is Kafka topics; outputs are Kafka topics. Materialized **TABLE** state is held in embedded RocksDB ([LSM-tree](../concepts/lsm-vs-btree.md)) state stores, with the durable copy written to compacted Kafka **changelog topics** for fault-tolerant recovery.
- Two query types: **push queries** (`EMIT CHANGES`) — long-lived subscriptions that stream incremental results as the topic changes; and **pull queries** — point lookups against a materialized table "as of now," returning a finite result like a key/value DB query. Pull queries are deliberately limited (key/range lookups on materialized tables, not full ad-hoc SQL).
- Pairs with: [apache-kafka](apache-kafka.md) (mandatory), Kafka [Connect/CDC](../concepts/change-data-capture.md) (e.g. Debezium) for ingest, [Schema Registry](../concepts/streaming-platforms.md) for Avro/Protobuf/JSON-Schema. Typical pattern: Debezium CDC into Kafka → ksqlDB joins/aggregates → enriched topics consumed by sinks or by [apache-druid](apache-druid.md)/[clickhouse](clickhouse.md)/[elasticsearch](elasticsearch.md) for serving.
- Scaling: stateless and stateful work is partitioned by Kafka partition; adding ksqlDB Server instances in the same `ksql.service.id` cluster rebalances processing — so **max parallelism is capped by the source topic's partition count**.

## Guarantees & consistency
- **Delivery semantics:** inherits Kafka Streams. Default is at-least-once; **exactly-once** is available via `processing.guarantee=exactly_once_v2`, which uses Kafka transactions across consume→process→produce ([Confluent: exactly-once processing](https://docs.confluent.io/platform/current/ksqldb/faq.html)). This is exactly-once **within the Kafka boundary**; end-to-end exactly-once to external sinks depends on the sink connector's idempotency.
- **Time semantics:** supports **event-time** (timestamp extracted from the record/payload) and processing-time; windowed aggregations (tumbling/hopping/session) with **grace periods** to bound late data. Late records past the grace period are dropped.
- **Consistency model:** materialized tables are eventually consistent with the input streams; pull queries read the local materialized state, which can lag the input. There is no multi-statement ACID and no cross-key transaction — [isolation levels](../concepts/isolation-levels.md) are N/A. CAP framing is N/A: durability and ordering are delegated to Kafka (per-partition total order). No independent [cap-pacelc](../concepts/cap-pacelc.md) story.
- **Durability / data-loss window:** state is recoverable because the source of truth is Kafka changelog topics; see [wal-and-durability](../concepts/wal-and-durability.md). A loss window exists only insofar as the upstream Kafka producers' acks/durability allow. ⚠️ unverified — no public Jepsen report exists for ksqlDB specifically; correctness claims rest on the Kafka Streams transactional model.

## Interfaces & integration
- **Language:** ksqlDB SQL — a SQL-like dialect with `CREATE STREAM`/`CREATE TABLE`, `CREATE ... AS SELECT` (persistent queries), joins (stream-stream, stream-table, table-table), windowed aggregations, and `EMIT CHANGES`. It is **not** ANSI SQL and is notably narrower than Flink SQL (limited join types, limited subquery/CTE support, no general OLAP).
- **APIs:** REST API, a Java client, the `ksql` CLI, and a Confluent Cloud UI. **UDF/UDAF/UDTF** extensibility in **Java** (custom functions packaged as JARs).
- **Interop:** because everything is just Kafka topics, outputs are consumable by any Kafka client, Kafka Connect sink, or downstream engine. Schema integration via Confluent Schema Registry. Unlike [open table formats](../concepts/open-table-formats.md), there is no neutral storage artifact — interop is "via Kafka," and ksqlDB SQL itself is Confluent-specific.

## Operations & maturity
- **Deployment:** self-managed ksqlDB Server (JVM, often containerized) as part of Confluent Platform, or fully managed in **Confluent Cloud**. Clustering is via shared `ksql.service.id`.
- **Maturity:** production-proven since ~2019 (evolved from KSQL, 2017). Mature and stable for what it does.
- **Strategic status (the big caveat):** after Confluent's 2023 acquisition of Immerok (creators of [Flink](apache-flink.md)), **Flink SQL is Confluent's strategic stream-processing engine**, and ksqlDB is effectively in maintenance mode. Confluent states ksqlDB remains supported and continues on the Kafka Streams engine, but new investment and the recommended path for new projects is Flink ([Confluent / community guidance, 2024–2025](https://developer.confluent.io/learn-more/podcasts/flink-vs-kafka-streams-ksqldb-comparing-stream-processing-tools/)). ⚠️ unverified — no public hard end-of-life date for ksqlDB has been announced as of 2026-06.
- **Known failure modes:** parallelism ceiling at source partition count; expensive/large stateful joins and aggregations stress RocksDB and changelog topics; query/topology changes can require reprocessing; repartition ("internal") topics multiply cluster topic count; schema evolution limits on existing persistent queries.
- **Governance:** vendor-controlled by **Confluent** (single-vendor open-core), not an Apache Software Foundation project — contrast with [apache-flink](apache-flink.md) and Kafka itself.

## Licensing & cost
- **License:** [Confluent Community License](https://www.confluent.io/confluent-community-license-faq/) — **source-available, not OSI-approved**: free to use and self-host, but you may not offer ksqlDB "as a SaaS" competing with Confluent. See [license-taxonomy](../concepts/license-taxonomy.md). This is materially less open than Apache-2.0 Kafka/Flink.
- **Open vs vendor-controlled:** single-vendor; the SQL dialect and engine are Confluent's, creating lock-in to the Confluent/Kafka ecosystem.
- **Cost model:** self-managed = your own compute (JVM nodes + Kafka). Confluent Cloud ksqlDB is billed on provisioned **CSU** (Confluent Streaming Units) capacity plus underlying Kafka/storage — capacity-priced, runs continuously whether or not queries are active.

## Bottom line
- Reach for ksqlDB if you are **already all-in on Kafka** and want lightweight, SQL-expressed stream transforms, enrichments, and simple materialized lookups without writing Kafka Streams Java. It is the lowest-friction way to do Kafka-in/Kafka-out ETL.
- Do **not** choose it for greenfield streaming in 2026: Confluent has anointed [Flink SQL](apache-flink.md) as the strategic engine, so new investment should track Flink (or [materialize](materialize.md)/[risingwave](risingwave.md) if you want a true streaming database with richer SQL and serving). Also avoid it when you need rich ANSI SQL, sources beyond Kafka, parallelism past your partition count, or a permissive OSI license.
- Single biggest gotcha: **it only knows Kafka, and it is on a maintenance track behind Flink** — building new, complex pipelines on ksqlDB risks a future migration. The anti-pattern is treating ksqlDB as a general database for ad-hoc analytical queries; pull queries are key-lookups on materialized tables, not an OLAP engine.

## Sources
- [ksqlDB Overview — Confluent Documentation](https://docs.confluent.io/platform/current/ksqldb/overview.html)
- [Architecture of ksqlDB / How it works — Confluent Documentation](https://docs.confluent.io/platform/current/ksqldb/operate-and-deploy/how-it-works.html)
- [ksqlDB FAQ (exactly-once, semantics) — Confluent Documentation](https://docs.confluent.io/platform/current/ksqldb/faq.html)
- [Queries in ksqlDB (push vs pull) — Confluent Documentation](https://docs.confluent.io/platform/current/ksqldb/concepts/queries.html)
- [Confluent Community License FAQ](https://www.confluent.io/confluent-community-license-faq/)
- [confluentinc/ksql — GitHub](https://github.com/confluentinc/ksql)
- [Flink vs Kafka Streams/ksqlDB — Confluent Developer](https://developer.confluent.io/learn-more/podcasts/flink-vs-kafka-streams-ksqldb-comparing-stream-processing-tools/)
- [Flink SQL vs ksqlDB — Streamkap](https://streamkap.com/resources-and-guides/flink-sql-vs-ksqldb)
