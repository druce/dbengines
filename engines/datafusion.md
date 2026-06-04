---
name: Apache DataFusion
slug: datafusion
adjacent: true
rank: n/a
category: query-engine
data_model: Embeddable columnar SQL/DataFrame query engine (library)
license: Apache 2.0 (permissive)
summary: A fast, embeddable Rust/Arrow query engine you build databases out of, not a database itself.
last_researched: 2026-06-04
confidence: high
---

# Apache DataFusion

> An extensible, vectorized SQL and DataFrame query engine written in Rust on Apache Arrow, designed to be embedded as a *library* inside other data systems — it is the engine, not the database.

## When to use

**Use Apache DataFusion if:**
- ✅ You are building a data system in Rust (a database, dataframe library, streaming/ML engine) and want a production-grade Arrow-native SQL planner + vectorized executor without writing one
- ✅ You need an extensible engine — custom `TableProvider` data sources, scalar/aggregate/window UDFs, optimizer passes, and physical operators are all replaceable traits
- ✅ You want a fast local file-querying tool via `datafusion-cli`, or zero-copy Arrow interop into pandas/Polars/Arrow Flight pipelines

**Avoid Apache DataFusion if:**
- ❌ You expect a finished database — there is no storage, no transactions, no server, and no client/JDBC protocol; those are your job
- ❌ You want a turnkey managed service or a stable frozen API — there is no managed "DataFusion" and the fast release cadence brings breaking API changes
- ❌ You run big joins/aggregations without wiring up the `MemoryPool` and disk-spill config — the default is unbounded memory use and OOM rather than graceful degradation

## Identity / role
- **What it is:** a query engine library — a full pipeline of SQL/DataFrame frontends → logical plan → optimizer → physical plan → a columnar, multi-threaded, vectorized, streaming execution engine, all operating on the [Apache Arrow](../concepts/columnar-storage.md) in-memory format. Distributed across 40+ Rust crates, every layer of which is replaceable.
- **What it is NOT:** not a standalone database, not a storage layer, not a service. It has no persistent storage, no transactions, no client/server protocol of its own ([the docs are explicit it "is not a database"](https://datafusion.apache.org/user-guide/introduction.html)). You bring storage, a catalog, and a deployment wrapper. It sits on the OLAP side of [oltp-olap-htap](../concepts/oltp-olap-htap.md) — built for analytic scans, not point-update OLTP.
- Closest analogues: it competes conceptually with embeddable engines like [duckdb](duckdb.md) (C++) and with the planner/execution layers inside engines like [trino](trino.md) and [apache-spark-sql](apache-spark-sql.md) — but is shipped as a customizable Rust crate rather than a finished product.

## How it fits
- **Problem it solves:** lets builders of "data-centric systems" (databases, dataframe libraries, streaming engines, ML feature stores) avoid reimplementing a SQL parser, optimizer, and vectorized executor. You extend it via traits: `TableProvider` (custom data sources / file formats), scalar/aggregate/window UDFs, custom optimizer passes, custom physical operators, and even alternative query languages.
- **Execution model:** physical plans `execute()` into one or more partitions exposed as a `SendableRecordBatchStream` — a pull-based stream of Arrow `RecordBatch`es. Parallelism is Volcano/Exchange-style via a `RepartitionExec` operator. Resource management is pluggable: `MemoryPool` for memory budgeting, `DiskManager` for spill-to-disk, `CacheManager` for metadata caching.
- **What it pairs with:** native readers/writers for Parquet, CSV, JSON, and Avro on local or object storage; it is the query brain inside [influxdb](influxdb.md) 3.x (IOx, also exposing InfluxQL/SQL), GreptimeDB, Delta Lake's Rust implementation (delta-rs), Apache Iceberg's Rust binding, [Spark](apache-spark-sql.md) via the **Comet** accelerator, and many others (40+ projects). **Ballista** is the DataFusion subproject that distributes plans across nodes. Python bindings (`datafusion`) and DataFrame use are first-class.

## Guarantees & consistency
- **Transactions/ACID:** N/A — DataFusion has no storage and no transaction manager. ACID/[isolation](../concepts/isolation-levels.md) are the responsibility of whatever system embeds it (e.g. Delta Lake or Iceberg table semantics layered on top via [open-table-formats](../concepts/open-table-formats.md)).
- **Query consistency:** a query executes against the table snapshot resolved at planning time through the supplied `TableProvider` / catalog; consistency of that snapshot is delegated to the embedder. [Durability](../concepts/wal-and-durability.md): N/A — nothing is persisted by the engine.
- **CAP/[cap-pacelc](../concepts/cap-pacelc.md):** N/A — single-process library; distribution (and any partition-tolerance behavior) lives in Ballista or the host system, not the core engine.
- **Correctness maturity:** SQL semantics are extensively tested, and a [SIGMOD 2024 paper](https://dl.acm.org/doi/10.1145/3626246.3653368) describes the design. No Jepsen report exists or would be meaningful — there are no distributed consistency guarantees to test in the core.

## Interfaces & integration
- **Languages/APIs:** SQL (a broad, evolving dialect with window functions, CTEs, subqueries, many built-in functions), a fluent **DataFrame API**, and a **CLI** (`datafusion-cli`) for ad-hoc querying of files/object stores. Substrait import/export is supported for cross-engine plan interchange. Python bindings expose SQL + DataFrame.
- **Data sources:** built-in Parquet/CSV/JSON/Avro; object store support (S3, GCS, Azure) via the `object_store` crate; anything else via custom `TableProvider`. Strong [ClickBench](https://datafusion.apache.org/) Parquet performance is a frequently cited result.
- **Ecosystem interop:** because it is Arrow-native, results move zero-copy into pandas/Polars/Arrow Flight pipelines. It is consumed *as a dependency* rather than connected to via drivers — the integration surface is the Rust (or Python) API, not JDBC/ODBC.

## Operations & maturity
- **Deployment & ops:** there is nothing to deploy on its own — operability is whatever the embedding system provides. `datafusion-cli` is the only "runnable" artifact and is for local use. Ballista adds a scheduler/executor topology for distributed runs (less mature than the core).
- **Maturity:** strong and rising. Developed at the ASF since 2019 (originally inside Apache Arrow), it [graduated to a standalone ASF Top-Level Project in June 2024](https://news.apache.org/foundation/entry/apache-software-foundation-announces-new-top-level-project-apache-datafusion). Heavily exercised in production by InfluxDB 3.x, GreptimeDB, delta-rs, and others. Releases are frequent; the API surface still changes between versions, so embedders should expect to track upgrades.
- **Known failure modes:** memory pressure on large aggregations/joins if `MemoryPool`/spill are not configured (OOM rather than graceful degradation by default); SQL-dialect gaps versus Postgres/Spark on edge cases; the fast release cadence means breaking API changes for downstream crates.
- **Governance:** vendor-neutral Apache Software Foundation community; no single controlling company (contributors span InfluxData, Synnada, and many others).

## Licensing & cost
- **License:** [Apache 2.0](https://github.com/apache/datafusion) — permissive, no open-core or source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Open vs vendor-controlled:** fully open, ASF-governed; no managed service of "DataFusion" itself — you embed it. Cost is engineering/operational only (it is a free library); your runtime cost is whatever host system and hardware you run it on.

## Bottom line
- Reach for DataFusion if you are **building** a data system in Rust (a database, dataframe library, streaming/ML engine, or a fast file-querying tool) and want a production-grade Arrow-native SQL planner + vectorized executor without writing one. It is also a fine fast local query tool via `datafusion-cli`. Do **not** reach for it expecting a database: there is no storage, no transactions, no server, no client protocol — those are your job. The biggest gotcha is treating it as a finished product; the second is unbounded memory use on big joins/aggregations unless you wire up the `MemoryPool` and disk-spill configuration.

## Sources
- [Apache DataFusion documentation — Introduction](https://datafusion.apache.org/user-guide/introduction.html)
- [Apache DataFusion home / overview](https://datafusion.apache.org/)
- [ASF announcement: DataFusion becomes a Top-Level Project (June 2024)](https://news.apache.org/foundation/entry/apache-software-foundation-announces-new-top-level-project-apache-datafusion)
- [apache/datafusion on GitHub (license, source)](https://github.com/apache/datafusion)
- [SIGMOD 2024 paper: "Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic Query Engine"](https://dl.acm.org/doi/10.1145/3626246.3653368)
- [Apache DataFusion Comet (Spark accelerator)](https://datafusion.apache.org/comet/)
- [InfluxData: 7 Projects Building on DataFusion](https://www.influxdata.com/blog/7-datafusion-projects-influxdb/)
