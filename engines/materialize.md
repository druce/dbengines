---
name: Materialize
slug: materialize
adjacent: true
rank: n/a
category: streaming-database
data_model: Streaming SQL database (incremental view maintenance)
license: Business Source License 1.1 (source-available; → Apache 2.0 after ~4 years); free Community self-managed tier
summary: Postgres-wire streaming database that keeps SQL materialized views incrementally up to date with strict-serializable consistency, built on Differential Dataflow.
last_researched: 2026-06-04
confidence: high
---

# Materialize

> A streaming SQL database that turns standard SQL `MATERIALIZED VIEW`s into always-fresh, incrementally maintained results over changing data — speaking the Postgres wire protocol and defaulting to strict serializability.

## When to use

**Use Materialize if:**
- ✅ You need always-fresh SQL results over fast-changing data with real database correctness — real-time dashboards, alerting, segmentation, feature serving
- ✅ Stale or torn intermediate results are unacceptable (default strict serializable, vs eventually-consistent streaming stacks)
- ✅ You want plain Postgres-flavored SQL and pgwire compatibility instead of a stream-processing API
- ✅ You ingest CDC from Postgres/MySQL or Kafka/Redpanda and want incrementally-maintained joins/aggregations/recursion

**Avoid Materialize if:**
- ❌ Every materialized view is a standing, RAM-resident, always-running dataflow — broad or unbounded-state views get expensive and can OOM
- ❌ You need a primary OLTP system of record (it ingests change streams, it is not your source of truth)
- ❌ You want a batch warehouse for ad-hoc scans over huge cold data ([snowflake](snowflake.md)/[trino](trino.md)/[duckdb](duckdb.md) fit better), or the always-on continuous-compute cost outweighs the freshness benefit

## Identity / role
- **What it is:** an operational [streaming database](../concepts/streaming-databases.md) for **incremental view maintenance (IVM)**. You write SQL views; Materialize recomputes only the deltas as inputs change, keeping results fresh at sub-second latency rather than re-scanning on each query.
- **What it is NOT:** not a general-purpose OLTP database (it ingests change streams, it is not your system of record), not a batch warehouse like [snowflake](snowflake.md) (no large ad-hoc scan workloads), and not merely a stream processor like [apache-flink](apache-flink.md) — it exposes durable, queryable SQL state with database semantics, not just a dataflow job. It sits on the [oltp-olap-htap](../concepts/oltp-olap-htap.md) spectrum as a serving layer for derived/real-time data.
- Closest peers: [risingwave](risingwave.md) (also streaming SQL), Flink SQL, and Feldera. Materialize's differentiator is its consistency model and Postgres compatibility.

## How it fits
- **Engine:** built on **Timely Dataflow** and **Differential Dataflow** (Frank McSherry et al.) — a delta-based dataflow runtime where every update carries an explicit logical timestamp ("virtual time"), enabling correct incremental maintenance of joins, aggregations, and recursion. ([architecture](https://materialize.com/blog/materialize-architecture/))
- **Architecture:** cloud-native with **storage/compute separation** ([storage-compute-separation](../concepts/storage-compute-separation.md)). A distributed key-value persistence layer ("persist", on object storage) holds source data and materialized-view results; **clusters** (each with one or more **replicas** = the actual machines) run the dataflows. You scale or isolate workloads by sizing/adding clusters. ([dbdb.io](https://dbdb.io/db/materialize))
- **Inputs:** ingests **change data** ([change-data-capture](../concepts/change-data-capture.md)) directly from **PostgreSQL** and **MySQL** replication ([WAL/binlog](../concepts/wal-and-durability.md)) and from **Kafka / Redpanda** topics (incl. Debezium-style CDC). It pairs with a [streaming-platforms](../concepts/streaming-platforms.md) (Kafka) or an OLTP DB as the upstream source of truth.
- **Outputs:** query interactively via SQL, push live result deltas to clients with `SUBSCRIBE`, or write results back out via **Kafka sinks**.

## Guarantees & consistency
- **Isolation:** default **strict serializable** (serializable + linearizable: if T1 finishes before T2 starts in real time, the serial order respects that). **Serializable** is also selectable for lower latency (may return internally-consistent but slightly stale snapshots). Read Uncommitted/Committed/Repeatable Read are accepted but treated as Serializable. ([docs](https://materialize.com/docs/get-started/isolation-level/))
- **Why this matters:** Materialize argues eventual consistency is wrong for streaming because partial/incoherent intermediate results leak; it timestamps every input update so all updates of a transaction share one timestamp and views never expose torn states. ([consistency blog](https://materialize.com/blog/strong-consistency-in-materialize/), [eventual consistency isn't for streaming](https://materialize.com/blog/eventual-consistency-isnt-for-streaming/))
- **Recency tradeoff:** even under strict serializable, a `SELECT` reflects data Materialize has *already ingested*; the optional **Real-Time Recency** (preview, strict-serializable only) makes a query wait until it has consumed all data visible upstream at query time — correctness at the cost of latency. ([docs](https://materialize.com/docs/get-started/isolation-level/))
- **Delivery semantics:** results are deterministic with respect to input timestamps. Kafka sinks provide **exactly-once** output semantics (each consistent batch emitted under a Materialize timestamp). ⚠️ unverified — exact end-to-end exactly-once behavior depends on source replay guarantees and sink transactional config; validate for your topology.
- No published Jepsen report; consistency claims are vendor-stated and grounded in the Differential Dataflow research, not independently formally verified here.

## Interfaces & integration
- **Wire protocol:** **PostgreSQL pgwire** — works with `psql`, Postgres drivers, and many BI/SQL tools out of the box.
- **Language:** SQL (Postgres-dialect-compatible subset) with `CREATE SOURCE`, `CREATE MATERIALIZED VIEW`, `CREATE INDEX` (in-memory served results), and `SUBSCRIBE` for change feeds. Supports joins, aggregations, and recursive (WITH RECURSIVE / `WMR`) queries maintained incrementally.
- **Connectors:** Postgres CDC, MySQL CDC, Kafka/Redpanda (Avro/JSON/Protobuf via schema registry), webhook sources; Kafka sinks. Integrates with **dbt** (dbt-materialize adapter) and downstream apps/dashboards.
- Distinct from open table formats: it does not read/write [Iceberg/Delta](../concepts/open-table-formats.md) tables as a primary store; it is a serving/compute layer, though it can sink to systems that do.

## Operations & maturity
- **Deployment:** primarily a **managed cloud** service (credit-based pricing). Also **Self-Managed** (Kubernetes-based; v26 added schema-change support) and a free **Community** self-managed license capped at 24 GiB memory / 48 GiB disk. An emulator/Docker image exists for local dev.
- **Ops burden:** memory-bound — maintained views and indexes keep working state in RAM on cluster replicas, so cost/scaling is driven by view complexity and arrangement size, not just data volume. Sizing clusters and watching memory is the main day-2 concern.
- **Failure modes:** OOM on overly broad/stateful views; ingestion lag if upstream CDC bursts; replica restarts rehydrate from persisted state. Replicas can be added for availability and for [active-active](../concepts/consensus-raft-paxos.md)-style redundancy within a cluster.
- **Maturity:** GA commercial product (company founded 2019, rewritten to the cloud platform ~2022). Production use in real-time analytics, fraud/alerting, feature serving; smaller install base and ecosystem than mature OLTP/OLAP engines.

## Licensing & cost
- **License:** **Business Source License 1.1** (source-available), converting to **Apache 2.0** after ~4 years — see [license-taxonomy](../concepts/license-taxonomy.md). This is not OSI open-source while under BSL; production use of the source outside the Community/commercial terms is restricted.
- **Open vs vendor-controlled:** vendor-controlled (Materialize Inc.), single-vendor governance — not an ASF project.
- **Cost model:** managed cloud bills on compute credits tied to cluster size/replicas (continuous compute, since views are always maintained) — costs accrue even when query volume is low. Self-managed Community tier is free within the memory/disk caps.

## Bottom line
- Reach for Materialize when you need **always-fresh SQL results over fast-changing data with real database correctness** — real-time dashboards, alerting, segmentation, and feature serving where stale or torn intermediate results are unacceptable, and you want plain Postgres-flavored SQL instead of a stream-processing API. Its strict-serializable default is a genuine differentiator versus eventually-consistent streaming stacks.
- **Do not** use it as your primary OLTP store, as a batch warehouse for ad-hoc scans over huge cold data ([snowflake](snowflake.md)/[trino](trino.md)/[duckdb](duckdb.md) fit better), or for workloads where the always-on, **memory-bound** continuous-compute cost outweighs the freshness benefit. The biggest gotcha: every materialized view is a standing, RAM-resident, always-running dataflow — broad or unbounded-state views get expensive and can OOM, so model view state deliberately.

## Sources
- [What is Materialize? (docs)](https://materialize.com/docs/get-started/)
- [Consistency guarantees / isolation levels (docs)](https://materialize.com/docs/get-started/isolation-level/)
- [The Software Architecture of Materialize](https://materialize.com/blog/materialize-architecture/)
- [Strong Consistency in Materialize](https://materialize.com/blog/strong-consistency-in-materialize/)
- [Eventual Consistency isn't for Streaming](https://materialize.com/blog/eventual-consistency-isnt-for-streaming/)
- [Incremental Computation guide](https://materialize.com/guides/incremental-computation/)
- [Database of Databases — Materialize](https://dbdb.io/db/materialize)
- [Self-Managed v26.0.0 release](https://materialize.com/blog/materialize-self-managed-v26-0-0-release/)
- [GitHub — MaterializeInc/materialize (license)](https://github.com/MaterializeInc/materialize/)
