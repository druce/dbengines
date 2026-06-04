---
name: InfluxDB
slug: influxdb
rank: 30
data_model: Time-series
license: MIT / Apache-2.0 (v3 Core OSS); proprietary commercial editions (Enterprise, Clustered, Cloud)
summary: The default open-source time-series DB; v3 is a full Rust/Arrow/Parquet rewrite that trades the old TSM engine and Flux for columnar object-storage and SQL.
last_researched: 2026-06-04
confidence: high
---

# InfluxDB

> The most popular open-source time-series database, now in its third, ground-up rewrite (v3 / "IOx") on Apache Arrow + DataFusion + Parquet — solving v1/v2's cardinality wall but fragmenting users across three incompatible generations.

## When to use

**Use InfluxDB if:**
- ✅ You need a popular, well-integrated time-series store for metrics/IoT/observability with first-class Telegraf and Grafana integration.
- ✅ v1/v2's high-cardinality cardinality wall hurt you — v3's Arrow/Parquet/object-storage columnar engine is designed precisely to fix that and claims unbounded series cardinality.
- ✅ You want object-storage-backed, storage-compute-separated time-series with SQL (via DataFusion) and cheap storage at scale.

**Avoid InfluxDB if:**
- ❌ You depend on Flux or are unsure which generation to run — it is really three incompatible databases (v1 TSM/InfluxQL, v2 TSM/Flux, v3 IOx/SQL); migrating is a re-platforming decision, not an upgrade (the biggest gotcha).
- ❌ You need a general-purpose or transactional store — there are no multi-statement transactions or isolation levels; it is append-oriented.
- ❌ You need long-range full-history analytical scans on the free Core edition — the full compactor that enables them is Enterprise-only (Core caps queries at ~72 h).

## Identity
- **Taxonomy / data model:** purpose-built time-series database. Data is organized as *measurements* (≈ tables) with *tags* (indexed string dimensions), *fields* (values), and a *time* column. See [time-series-storage](../concepts/time-series-storage.md), [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** **Generation-dependent — this is the central fact about InfluxDB.**
  - **v1/v2:** the **TSM (Time-Structured Merge Tree)**, an LSM-tree variant ([lsm-vs-btree](../concepts/lsm-vs-btree.md)), paired with the **TSI** inverted index mapping series metadata to data. Performance degraded badly as series cardinality grew (the notorious "cardinality wall"). ([InfluxDB 3 storage engine](https://docs.influxdata.com/influxdb3/core/reference/internals/storage-engine/))
  - **v3 (IOx):** completely different — **columnar**, in-memory [columnar-storage](../concepts/columnar-storage.md) via **Apache Arrow**, on-disk **Parquet** files in object storage, queried by **Apache DataFusion**. No TSM, no TSI; claims unbounded series cardinality. ([FDAP architecture](https://www.influxdata.com/blog/flight-datafusion-arrow-parquet-fdap-architecture-influxdb/))
- **Workload:** OLTP-style high-rate ingest + analytical range/aggregation queries over time windows. v3's columnar/Parquet engine makes it effectively an OLAP engine specialized for time-series; not a general transactional store.

## Distribution & consistency
- **CAP under partition:** ⚠️ unverified — no Jepsen report exists for any InfluxDB version. v3 Core/Enterprise is effectively **CP-flavored** in that durability is anchored to a single object-store backend (S3/GCS/Azure) which is itself the consistency boundary; InfluxDB nodes are largely stateless compute. There is no multi-node quorum replication protocol in the open-source line. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — not formally characterized. Practically: durability and "single source of truth" come from object storage, not from inter-node consensus, so the classic partition/quorum tradeoffs do not map cleanly.
- **Default isolation:** **No multi-statement transactions and no isolation levels in the SQL sense** — writes are point/line appends, not transactions. There is no [mvcc](../concepts/mvcc.md) read-snapshot model exposed to users. Do not treat any "ACID" framing as applicable; InfluxDB is an append-oriented metrics store, not a transactional DBMS. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** v1 OSS = single-node only (clustering was Enterprise-only). v3 **Core** = single-node. v3 **Enterprise / Clustered** achieve HA by running multiple stateless ingester/querier nodes against shared object storage; durability/replication is delegated to the object store rather than a [consensus-raft-paxos](../concepts/consensus-raft-paxos.md) log. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels in the Dynamo/Cassandra sense.
- **Clock dependency:** timestamps are client- or server-supplied; correctness of ordering relies on caller timestamps, not on synchronized cluster clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, but auto-created:** schema is inferred from the first write of a measurement (tag/field names and field types). Effectively schema-on-write with implicit DDL — field **types are fixed** after first write; writing a conflicting type for a field is rejected.
- **Migration/evolution:** adding new tags/fields/measurements is free (just write them). Changing an existing field's type is not supported in place. No locking `ALTER` because there is no rigid up-front DDL.
- **Type system:** float, integer, unsigned integer, string, boolean, plus the time column. Tags are always strings. ⚠️ unverified — no native geospatial or vector types; not a vector/geo database.

## Query interface
- **Language — also generation-dependent:**
  - **v1:** InfluxQL (SQL-like DSL).
  - **v2:** **Flux**, a bespoke functional data-scripting language (now de-emphasized/maintenance).
  - **v3:** **SQL** (via DataFusion) as the primary language, plus an InfluxQL compatibility frontend. Flux is **not** supported in v3. ([InfluxDB 3 docs](https://docs.influxdata.com/influxdb3/which-influxdb-3/))
- **Wire protocols:** line-protocol for writes; **Arrow Flight SQL** for v3 queries; HTTP API across versions.
- **Transactions:** none (single-point writes; no multi-statement ACID).
- **Native vs app-side:** v3 inherits DataFusion's SQL — joins, aggregations, window functions are available; in v1/v2 joins were limited/awkward. No secondary B-tree indexes in the relational sense; tags act as the indexed dimensions.
- **Stored procedures / UDFs:** v3 Enterprise/Core ship a **Processing Engine** for embedded Python plugins (triggers on write/query/schedule). ⚠️ unverified — exact capabilities vary by release.

## Scaling & topology
- **Vertical vs horizontal:** v1/v2 OSS scale **vertically only** (single node); horizontal scale was paywalled into Enterprise/Cloud. v3 separates compute from storage so ingest and query tiers scale horizontally against shared object storage (Enterprise/Clustered).
- **Sharding/partitioning:** time-based partitioning (e.g. 10-minute Parquet blocks in v3, configurable). Cardinality scaling was v1/v2's Achilles heel; v3 claims "infinite cardinality."
- **Read replicas / read consistency:** v3 queriers read the same Parquet in object storage, so reads are consistent to whatever has been persisted; recent unpersisted data is served from the in-memory queryable buffer.
- **Storage/compute separation:** **yes, central to v3** — object storage is the only durable layer; nodes are stateless. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path (v3 Core):** writes are validated into an in-memory buffer; **every ~1 s the buffer is flushed to a WAL in object storage** ([wal-and-durability](../concepts/wal-and-durability.md)); every ~10 min data is compacted into Parquet. Default `no_sync=false` acks only after WAL persistence; `no_sync=true` acks immediately (faster, larger loss window). ([Core durability docs](https://docs.influxdata.com/influxdb3/core/reference/internals/durability/))
- **Data-loss window on crash:** up to ~1 s of acked-but-unflushed writes with defaults; effectively all in-flight buffer with `no_sync=true`. ([Core durability docs](https://docs.influxdata.com/influxdb3/core/reference/internals/durability/))
- **Throughput/latency:** InfluxData markets v3 as **~10x ingest, ~100x faster high-cardinality queries, ~10x better compression** vs prior versions — these are **vendor benchmarks; treat as directional, not independently verified.** ([InfluxData](https://www.influxdata.com/blog/flight-datafusion-arrow-parquet-fdap-architecture-influxdb/)) Independent benchmarks (QuestDB) flagged the Core alpha as immature on some workloads. ([QuestDB benchmark](https://questdb.com/blog/influxdb3-core-alpha-benchmarks-and-caveats/))
- **Compaction/GC:** v3 background **compactor** merges 10-minute (gen1) Parquet files into larger sorted blocks. **Core lacks the full compactor**: it enforces a query time-range limit (default `query_file_limit` 432 files × 10-min gen1 = ~72 h, configurable) so queries cannot scan unbounded history; the **full compactor that rewrites/indexes files for long-range queries is an Enterprise feature.** ([72-hour limitation update](https://www.influxdata.com/blog/influxdb3-open-source-public-alpha-jan-27/))

## Operations & maturity
- **Backup/restore, PITR:** in v3 the durable state is Parquet + WAL in object storage, so backup is largely an object-store concern; v1/v2 had their own backup/restore tooling. ⚠️ unverified — first-class PITR semantics vary by edition.
- **Observability:** EXPLAIN query plans (DataFusion) in v3; Prometheus-style metrics; slow-query visibility varies by edition.
- **Upgrade story:** **the big day-2 gotcha — upgrades between major versions are migrations, not rolling upgrades.** v1→v2→v3 change the query language and storage engine; Flux workloads do not run on v3, and v1/v2 are now in **maintenance** with new workloads steered to v3. ([Which InfluxDB 3](https://docs.influxdata.com/influxdb3/which-influxdb-3/))
- **Maturity:** v1/v2 are very mature and widely deployed; **v3 Core/Enterprise went GA in April 2025** (after a Jan 2025 public alpha) and is comparatively young. No Jepsen report exists for any InfluxDB version. AWS added managed **InfluxDB 3 (Core and Enterprise)** to **Amazon Timestream for InfluxDB in October 2025**. ([AWS: Timestream now supports InfluxDB 3](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-timestream-influxdb-3/))

## Ecosystem & people
- **Canonical use cases:** infrastructure/app metrics & monitoring, IoT/sensor telemetry, DevOps observability, real-time dashboards. Tight integration with **Telegraf** (collector) and Grafana.
- **Anti-patterns:** not for relational/OLTP apps, not for ad-hoc full-history analytical scans in Core (compactor limits), not a general document/event store, not for use cases needing strong multi-row transactions. The old **high-cardinality (many unique tag combinations)** anti-pattern is the reason v3 exists — avoid v1/v2 there.
- **Drivers/connectors:** line protocol clients in all major languages, Arrow Flight SQL clients (v3), Telegraf, Grafana, Kafka via Telegraf. dbt support is limited vs relational engines.
- **Community/support:** large community, the most popular TS DB by [db-engines](https://db-engines.com/en/ranking) mindshare; docs are good but **fragmented across three versions**, which is itself a learning-curve hazard.

## Licensing & cost
- **OSS license:** v3 **Core is MIT / Apache-2.0** (permissive) — a notable shift; v1/v2 OSS were MIT. ([MIT/Apache announcement](https://community.influxdata.com/t/influxdb-3-open-source-now-in-public-alpha-under-mit-apache-2-license/55208)) See [license-taxonomy](../concepts/license-taxonomy.md).
- **Source-available/proprietary tiers:** **Enterprise, Clustered, and Cloud are commercial/proprietary.** Key OSS-vs-paid divides: clustering, HA, advanced security, and the **full compactor** (long-range queries) are Enterprise-only. InfluxData offers a **free Enterprise tier for non-commercial at-home use** (rate-limited). ([Enterprise free at-home](https://www.influxdata.com/blog/influxdb3-open-source-public-alpha-jan-27/)) Critics note OSS users are pushed toward paid tiers for production-scale querying. ([TDengine commentary](https://tdengine.com/influxdb-leaves-oss-users-behind/))
- **Lock-in:** line protocol and SQL are portable; Flux scripts are not, and the cross-version rewrites have repeatedly forced re-platforming.
- **Cost model:** Cloud is usage-based (data in, storage, query); Enterprise is licensed per deployment. v3's object-storage backing makes storage cheap at scale.

## Hardware / deployment
- **Resource profile:** v3 is **memory-bound on the hot ingest/buffer path and CPU-bound on Arrow/DataFusion query execution**; the full dataset does *not* need to fit in RAM since cold data lives in object storage. v1/v2 TSI index could be memory-hungry at high cardinality.
- **Storage assumptions:** v3 is built for **object storage (S3/GCS/Azure Blob)** as the durable layer ("diskless"); local NVMe is used as cache. v1/v2 assume local disk.
- **Footprint:** v3 Core = single binary/single node (also runnable as an edge/embedded-ish collector); Enterprise/Clustered = multi-node, **Kubernetes-native** (Clustered is K8s-managed on your own infra).
- **Deployment:** self-managed (Core/Enterprise/Clustered), fully managed (InfluxDB Cloud), or third-party managed (Amazon Timestream for InfluxDB).

## Bottom line
Reach for InfluxDB when you need a popular, well-integrated time-series store for metrics/IoT/observability with Telegraf + Grafana, and especially if v1/v2's high-cardinality cardinality wall hurt you — v3's Arrow/Parquet/object-storage engine is designed precisely to fix that. Do not reach for it as a general-purpose or transactional database, and think twice if you depend on Flux (gone in v3) or need long-range full-history queries on the free Core edition (the compactor that enables them is Enterprise-only). The single biggest gotcha: **InfluxDB is really three different databases (v1 TSM/InfluxQL, v2 TSM/Flux, v3 IOx/SQL) with incompatible engines and query languages — choosing or migrating between them is a re-platforming decision, not an upgrade.**

## Sources
- [InfluxDB 3 storage engine architecture (official docs)](https://docs.influxdata.com/influxdb3/core/reference/internals/storage-engine/)
- [InfluxDB 3 Core durability internals (official docs)](https://docs.influxdata.com/influxdb3/core/reference/internals/durability/)
- [Which InfluxDB 3 should I use? (official docs)](https://docs.influxdata.com/influxdb3/which-influxdb-3/)
- [FDAP architecture: Flight, DataFusion, Arrow, Parquet (InfluxData blog)](https://www.influxdata.com/blog/flight-datafusion-arrow-parquet-fdap-architecture-influxdb/)
- [InfluxDB 3 OSS public alpha under MIT/Apache 2 (community)](https://community.influxdata.com/t/influxdb-3-open-source-now-in-public-alpha-under-mit-apache-2-license/55208)
- [Enterprise free at-home + 72-hour limitation update (InfluxData blog)](https://www.influxdata.com/blog/influxdb3-open-source-public-alpha-jan-27/)
- [QuestDB independent benchmark of Core alpha](https://questdb.com/blog/influxdb3-core-alpha-benchmarks-and-caveats/)
- [Amazon Timestream for InfluxDB 3 (AWS)](https://aws.amazon.com/blogs/database/features-and-workflows-with-amazon-timestream-for-influxdb-3/)
- [TDengine commentary on OSS limitations](https://tdengine.com/influxdb-leaves-oss-users-behind/)
- [db-engines ranking](https://db-engines.com/en/ranking)
