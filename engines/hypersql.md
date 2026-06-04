---
name: HyperSQL
slug: hypersql
rank: 99
data_model: Relational (embedded Java)
license: BSD 3-clause (permissive)
summary: Pure-Java embeddable SQL database with unusually deep standards compliance; the go-to in-process test/desktop DB for the JVM, not a production server.
last_researched: 2026-06-04
confidence: high
---

# HyperSQL

> A small, fast, pure-Java relational engine (HSQLDB) that embeds in-process or runs as a single-node server, with the widest SQL-standard coverage of any open-source DB — best known as the JVM's default in-memory test database, not as a scalable production server.

## When to use

**Use HyperSQL if:**
- ✅ You need a real SQL database inside a JVM process for fast in-memory tests, desktop apps, or small embedded systems (ships as one ~1.5 MB JAR).
- ✅ You value unusually deep SQL-standard coverage (SQL:2023 core, window functions, recursive CTEs, MERGE, SQL/PSM and Java stored procedures).
- ✅ You want a fully permissive (BSD 3-clause) embedded engine with low lock-in and low day-2 burden (there is no cluster to operate).

**Avoid HyperSQL if:**
- ❌ You need high write concurrency, horizontal scale, or HA/replication — these are explicit non-goals (it is single-node with no clustering).
- ❌ You rely on durability of the last sub-second of commits — the default `WRITE DELAY` of 0.5 s means a crash can lose committed transactions unless you set it to 0 (the biggest gotcha).
- ❌ You assume true serializability — under MVCC, REPEATABLE READ and SERIALIZABLE are snapshot isolation, so plan for serialization-failure retries.

## Identity
- **Taxonomy / data model:** Relational (SQL), single-node. Pure Java; ships as one ~1.5 MB JAR with a JDBC driver. Also commonly called HSQLDB.
- **Storage model:** Per-table choice. `MEMORY` tables live entirely in RAM (the default; persisted by replaying a SQL `.script`/`.log` on startup). `CACHED` tables are disk-based, partially loaded, B-tree-indexed row store written to a `.data` file. `TEXT` tables map to external CSV/delimited files with in-memory indexes. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM — it is a row store with B-tree indexes and a SQL/operation log for durability ([HyperSQL Features](https://hsqldb.org/web/hsqlFeatures.html)).
- **Workload:** [oltp-olap-htap](../concepts/oltp-olap-htap.md) OLTP-oriented, small to mid-size. No columnar engine, no MPP — not an analytics or HTAP system. Excellent for embedded/transactional workloads up to a few GB; a single CACHED table supports up to 8 TB (TEXT tables up to 256 GB each) and the LOB store up to 64 TB total by config, but practical use is far smaller ([HyperSQL Features](https://hsqldb.org/web/hsqlFeatures.html)).

## Distribution & consistency
- **CAP under partition:** N/A — single-node. There is no built-in replication, sharding, or clustering, so [cap-pacelc](../concepts/cap-pacelc.md) does not apply. Crash/HA is handled externally (e.g. shared storage failover or app-level replication).
- **PACELC:** N/A — single-node.
- **Default isolation & what's achievable:** Two concurrency models. Default is **two-phase locking (2PL)**, which supports `READ COMMITTED` (default), `REPEATABLE READ`, and `SERIALIZABLE`; there is also an **MVCC** model and a hybrid `MVLOCKS` (2PL + multiversion rows). Under MVCC, both `REPEATABLE READ` and `SERIALIZABLE` are implemented as **snapshot isolation**, so conflicting transactions fail with a serialization error at commit rather than blocking — note this is snapshot isolation, not true serializability (it avoids the three standard anomalies but is not SSI) ([Sessions and Transactions](https://hsqldb.org/doc/2.0/guide/sessions-chapt.html)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** None built in. See [replication-models](../concepts/replication-models.md) — not applicable.
- **Tunable consistency?** No (no distribution). You tune the *concurrency model* (2PL / MVCC / MVLOCKS) and isolation level per session.
- **Clock dependency:** None — correctness does not rest on synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** Rigid, full SQL DDL with constraints, foreign keys, CHECK, and schemas/catalogs.
- **Migration/evolution:** Standard `ALTER TABLE`. On a single embedded node, DDL is effectively exclusive — no online-DDL machinery like a distributed system needs; for small tables this is a non-issue.
- **Type system:** Broad standard SQL types: `INTERVAL`, `ARRAY`, multidimensional-style arrays, BLOB/CLOB (dedicated multi-GB LOB store), `BOOLEAN`, `UUID`, `BIT`, time-with-timezone, and user-defined types. No native JSON type or vector/geospatial types (⚠️ unverified — JSON/GIS support may exist via functions in 2.7; core type system is not JSON-native).

## Query interface
- **Language:** SQL. Unusually deep standards coverage — claims SQL:2023 core plus an extensive list of optional features, the widest of any open-source engine ([HyperSQL Features](https://hsqldb.org/web/hsqlFeatures.html)). Window functions, CTEs (recursive), LATERAL and FULL joins, MERGE, set operations, updatable views.
- **Transactions:** Full multi-statement ACID with savepoints; durability gated by the `WRITE DELAY` setting (see below).
- **Native vs app-side:** Native secondary indexes, joins, aggregations, window functions — all in-engine.
- **Stored procedures / UDFs:** Both **SQL/PSM** (SQL Procedural Language) and **Java** stored procedures/functions, plus user-defined aggregate functions ([HyperSQL Features](https://hsqldb.org/web/hsqlFeatures.html)).

## Scaling & topology
- **Vertical vs horizontal:** Vertical only. No sharding, no partitioning across nodes, no resharding story because there is nothing to reshard.
- **Read replicas:** None native.
- **Storage/compute separation:** No — see [storage-compute-separation](../concepts/storage-compute-separation.md), not applicable. Storage and compute are the same JVM process (embedded) or one server process.
- **Footprint axis:** Scales by RAM (MEMORY tables) or local disk (CACHED tables); concurrency is multithreaded within the single process.

## Performance & durability
- **Write path:** MEMORY tables append SQL/operation entries to a `.log`; CACHED-table changes go to the `.data` file with the log. Durability is controlled by **`SET FILES WRITE DELAY`**: a value of `0` forces a `FileDescriptor.sync()` on every commit (fully durable, slower); a timed delay (default **0.5 s**) fsyncs only periodically, so a crash can lose up to the last interval's committed transactions — i.e. a sub-second **data-loss window by default** ([System Management](https://hsqldb.org/doc/2.0/guide/management-chapt.html)). See [wal-and-durability](../concepts/wal-and-durability.md). The on-disk persistence is a SQL/op log rather than a classic binary WAL.
- **Throughput/latency:** Very low latency for in-process MEMORY tables (no network, no serialization). CACHED-table performance is bounded by the file cache size and disk. No published p99/tail benchmarks at scale; ⚠️ unverified — tail behavior under heavy concurrent write contention is not well documented.
- **Compaction / vacuum / GC:** No LSM compaction. Disk databases accumulate the `.log`; a `CHECKPOINT` (or `SHUTDOWN COMPACT`) consolidates the log into the `.script`/`.data` and reclaims space. Being JVM-based, it is subject to **Java GC pauses** for in-memory workloads.

## Operations & maturity
- **Backup/restore, PITR:** Online `BACKUP DATABASE` to a compressed archive; recovery replays the `.script` + `.log`. No true continuous PITR / log-shipping like a server-grade RDBMS.
- **Observability:** JDBC metadata, SQL `EXPLAIN PLAN`, and a SQL log. No rich metrics/slow-query subsystem — observability is whatever the embedding application provides.
- **Upgrade story:** Library version bump (swap the JAR); cross-major-version on-disk format upgrades may require a controlled checkpoint. Day-2 burden is minimal *because* it is embedded — there is no cluster to operate.
- **Maturity:** Very mature (descends from Thomas Mueller's original Hypersonic SQL, ~2001; HSQLDB has shipped for two decades). Widely embedded — historically the default test DB in many Java/Spring projects and bundled in OpenOffice/LibreOffice Base. **No Jepsen report exists** (none is expected — Jepsen targets distributed systems; HyperSQL is single-node). Known limitation: it is not designed as a high-concurrency multi-user production server.

## Ecosystem & people
- **Canonical use cases:** In-memory database for unit/integration tests on the JVM; embedded DB for desktop/Java apps; small single-user or low-concurrency applications; the embedded engine behind LibreOffice/OpenOffice Base. **Anti-patterns:** multi-node HA, high write concurrency, large analytics, anything needing horizontal scale or replication — reach for [postgresql](postgresql.md), [mariadb](mariadb.md), or a distributed store instead. Note [h2](h2.md) and [apache-derby](apache-derby.md) are the direct embedded-Java competitors, and [sqlite](sqlite.md) is the cross-language embedded analog.
- **Drivers / ORMs / connectors:** Native JDBC (4.2); works with Hibernate/JPA, Spring, and any JVM ORM. ODBC available via a PostgreSQL-protocol-compatible path. CDC/Kafka/dbt integration is minimal — it is not a typical analytics-pipeline source.
- **Community & support:** Small, stable open-source project (hsqldb.org, SourceForge). Docs are thorough and standards-focused. No major commercial vendor; support is community-based. Learning curve is low for anyone who knows SQL/JDBC.

## Licensing & cost
- **License:** **BSD 3-clause** — fully permissive, no copyleft, no post-2018 relicensing drama ([HSQLDB FAQ](https://hsqldb.org/web/hsqlFAQ.html)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Self-managed library; no managed cloud offering (and none needed — it embeds).
- **Lock-in:** Low. Standard SQL and JDBC; migrating off to another RDBMS is straightforward.
- **Cost model:** Free. Cost is the RAM/CPU of the host JVM. No per-node/per-core/per-GB pricing.

## Hardware / deployment
- **Resource profile:** Memory-bound for MEMORY tables (the whole dataset must fit in JVM heap); disk-bound for CACHED tables (only a configurable cache fits in RAM). CPU is shared with the host application in embedded mode.
- **Storage assumptions:** Local filesystem; no network-attached-storage design assumptions. fsync behavior governed by `WRITE DELAY`.
- **Footprint:** Embedded in-process (primary mode) or a single standalone server (HSQL/HTTP/HSQL-BER protocols, optional SSL). No clustered mode.
- **Deployment:** Ships inside the application artifact; container/k8s deployment means deploying the *app* — there is no StatefulSet/operator story because there is no standalone cluster to run.

## Bottom line
Reach for HyperSQL when you need a real SQL database *inside* a JVM process — fast in-memory tests, desktop apps, or small embedded systems — and you value its remarkably complete SQL-standard implementation. Do not reach for it for high write concurrency, horizontal scale, HA/replication, or analytics; those are explicit non-goals. The single biggest gotcha: the default `WRITE DELAY` of 0.5 s means committed transactions can be lost in a crash unless you set it to `0` (at a throughput cost) — and "REPEATABLE READ/SERIALIZABLE" under MVCC is really snapshot isolation, so plan for serialization-failure retries.

## Sources
- [HyperSQL Features](https://hsqldb.org/web/hsqlFeatures.html)
- [HyperSQL Guide — Sessions and Transactions (isolation, MVCC, 2PL)](https://hsqldb.org/doc/2.0/guide/sessions-chapt.html)
- [HyperSQL Guide — System Management (WRITE DELAY, durability, backup)](https://hsqldb.org/doc/2.0/guide/management-chapt.html)
- [HyperSQL FAQ (license)](https://hsqldb.org/web/hsqlFAQ.html)
- [HSQLDB — Wikipedia](https://en.wikipedia.org/wiki/HSQLDB)
