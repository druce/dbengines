---
name: DuckDB
slug: duckdb
rank: 42
data_model: Relational (embedded OLAP)
license: MIT (permissive)
summary: Embedded columnar OLAP engine — "SQLite for analytics" that runs in-process and vectorizes over Parquet/Arrow with zero server.
last_researched: 2026-06-04
confidence: high
---

# DuckDB

> An in-process, single-file columnar SQL engine for analytics — think SQLite's deployment model with a vectorized OLAP engine bolted on; superb on one machine, not a distributed warehouse or a write-concurrent OLTP store.

## Identity
- **Taxonomy / data model:** relational, embedded (in-process library, not a server). Primary use is analytical SQL. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) and [embedded-databases](../concepts/embedded-databases.md).
- **Storage model:** columnar / column-store on disk; data lives in a single `.duckdb` file (or purely in-memory). Hierarchy is RowGroupCollection → RowGroup (~120K rows) → ColumnData → ColumnSegment (the compressed physical unit with per-segment statistics) ([DuckDB internals](https://duckdb.org/why_duckdb), [dbdb.io](https://dbdb.io/db/duckdb)). Compressed columnar format, not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — no LSM, no row B-tree heap. See [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** OLAP-first. Execution combines columnar storage, a **vectorized** engine (operates on ~2048-value chunks for cache efficiency) and **morsel-driven parallelism** across cores ([Why DuckDB](https://duckdb.org/why_duckdb)). It can do OLTP-style row mutations via MVCC but is not designed as a high-write-concurrency OLTP system (see Distribution). Not HTAP in the dual-store sense.

## Distribution & consistency
- **CAP under partition:** N/A — single-node, in-process. No distribution layer, no partitions to tolerate. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — single-node.
- **Default isolation:** **Snapshot isolation**, always; the isolation level is not configurable ([DuckDB transactions docs](https://duckdb.org/docs/stable/sql/statements/transactions), [Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions)). DuckDB markets this as "similar to serializable," but it is snapshot isolation (write-write conflicts abort the later transaction) — not formally serializable in the SSI sense. See [isolation-levels](../concepts/isolation-levels.md) and [mvcc](../concepts/mvcc.md). ACID is provided via a bulk-optimized MVCC scheme derived from HyPer's serializable MVCC variant, which updates in place and keeps prior versions in an undo buffer ([ACID blog](https://duckdb.org/2024/09/25/changing-data-with-confidence-and-acid)).
- **Replication:** N/A — single-node. See [replication-models](../concepts/replication-models.md). (Cloud variant MotherDuck handles managed storage/sharing separately.)
- **Concurrency model — the key gotcha:**
  - *Within one process:* multiple writer threads are supported via MVCC + optimistic concurrency control; readers see a consistent snapshot and never block writers ([Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions)).
  - *Across processes:* the native file allows **one read-write process, OR multiple read-only processes** — not both, and not multiple writers ([concurrency docs](https://duckdb.org/docs/current/connect/concurrency.html)). Cross-process multi-writer requires the Quack remote protocol (beta as of 1.5.2) or the DuckLake format with an external catalog DB.
- **Tunable consistency?** No.
- **Clock dependency:** None. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write** for native tables (typed columns, rigid). Also reads external Parquet/CSV/JSON with **schema-on-read** inference. Can register and query Arrow/Pandas/Polars dataframes directly in-process (zero-copy in many cases).
- **Migration/DDL:** `ALTER TABLE` (add/drop/rename column, change type) supported; runs in-process, transactional. No online-DDL-vs-locking concern in the distributed sense — it is a single file.
- **Type system:** rich — `STRUCT`, `LIST`, `MAP`, `UNION`, nested/composite types, `DECIMAL`, `INTERVAL`, native JSON (extension), `ENUM`, `UUID`, fixed-size `ARRAY` with array distance functions for vector similarity. Geospatial via the `spatial` extension. Full-text search via the `fts` extension.

## Query interface
- **Language:** SQL — its own dialect aiming at PostgreSQL compatibility, with ergonomic extensions (`SELECT * EXCLUDE`, `GROUP BY ALL`, `QUALIFY`, list comprehensions, friendly `FROM`-first syntax, `SUMMARIZE`). Native API in C/C++, Python, R, Java, Node.js, WASM, Go, Rust.
- **Transactions:** full multi-statement ACID (`BEGIN`/`COMMIT`/`ROLLBACK`) under snapshot isolation.
- **Native vs app-side:** full relational engine — joins (hash/merge), aggregations, window functions, CTEs (incl. recursive), set ops — all native and vectorized. ART indexes for PK/unique/point lookups; otherwise scans rely on columnar zone-map pruning rather than secondary indexes.
- **Stored procedures / UDFs:** no SQL stored-procedure language. UDFs are registered from the host language (e.g. Python/scalar + Arrow-vectorized UDFs); macros (`CREATE MACRO`) provide SQL-level parameterized expressions/tables.

## Scaling & topology
- **Vertical only.** Scales with cores, RAM, and local NVMe on one machine. No built-in sharding, no cluster. "Bigger box" is the scaling story.
- **Out-of-core:** can spill to disk and process datasets larger than RAM for many operators, but it is fundamentally single-node — there is no horizontal partitioning to manage.
- **Read replicas:** N/A. Multiple read-only processes can open the same file concurrently, which approximates fan-out for read workloads.
- **Storage/compute separation:** not in the core single-file model. The MotherDuck cloud service and the DuckLake table format (Parquet + external catalog) provide separation-style architectures layered on top. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** uses a write-ahead log; on commit DuckDB explicitly calls `fsync()` to force WAL entries to persistent storage (so a committed transaction survives a crash/power loss), and checkpointing folds the WAL into the main file — automatically once the WAL reaches `checkpoint_threshold` (default 16 MB) or on database close ([Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions)). DuckDB 1.x supports multiple WAL files so one can be checkpointed into the main file while another accepts writes in parallel ([MotherDuck 1.5 notes](https://motherduck.com/blog/DuckDB-1.5-features-I-am-excited-about)). See [wal-and-durability](../concepts/wal-and-durability.md). For in-memory databases there is by definition no durability.
- **Throughput/latency:** excellent on large analytical scans and aggregations on a single box — vectorized execution + columnar compression + multicore parallelism. Latency is dominated by scan/aggregate cost, not network. Not optimized for many small concurrent transactional writes (single-writer-process limit, plus checkpoint cost).
- **Compaction / vacuum / GC:** no LSM compaction. MVCC undo versions are reclaimed after transactions complete; checkpoint compacts the WAL. p99 impact comes mainly from checkpointing large write batches, not background compaction.

## Operations & maturity
- **Backup/restore:** the database is a single file — copy it (when not being written) for backup, or `EXPORT DATABASE` / `IMPORT DATABASE` to a directory of Parquet + SQL. No built-in PITR/snapshotting service; rely on filesystem/object-store snapshots.
- **Observability:** `EXPLAIN` and `EXPLAIN ANALYZE` query plans, profiling output (`PRAGMA enable_profiling`), per-operator timings. No server-side slow-query log/metrics daemon — it is a library, so observability is whatever the host app instruments.
- **Upgrade story:** reached **1.0 in mid-2024**; the storage format is now stable and forward/backward-compatible across recent versions. Pre-1.0, storage format changes sometimes required re-export. "Upgrade" = swap the library version in your app; no rolling cluster upgrade.
- **Maturity:** widely adopted in data science, analytics, and embedded analytics; backed by DuckDB Labs and the non-profit DuckDB Foundation. **No Jepsen report exists** (Jepsen targets distributed systems; DuckDB is single-node, so it is largely out of scope). Known failure modes: corruption risk if a single file is written from multiple processes or over flaky network/shared filesystems ([concurrency docs](https://duckdb.org/docs/current/connect/concurrency.html)); not for high-concurrency write serving.

## Ecosystem & people
- **Canonical use cases:** local/embedded analytics, ad-hoc querying of Parquet/CSV/JSON (including remote files on S3/HTTP via `httpfs`), the compute engine inside data apps and notebooks, dbt transformations, ETL/ELT staging, replacing pandas for larger-than-memory crunching, and edge/in-browser analytics via WASM.
- **Anti-patterns:** multi-user concurrent-write OLTP backends; a shared central database server for many writers; anything needing horizontal scale-out, HA/replication/failover, or durability of an in-memory instance. Reach for [postgresql](postgresql.md)/[mysql](mysql.md) for OLTP, or [clickhouse](clickhouse.md)/[snowflake](snowflake.md)/[google-bigquery](google-bigquery.md) for a distributed warehouse.
- **Drivers/connectors:** first-class Python/R/Java/Node/WASM/Go/Rust; reads/writes Parquet, CSV, JSON, Arrow, Iceberg, Delta; integrates with dbt (`dbt-duckdb`), Polars/Pandas, and BI tools. Rich extension ecosystem (`httpfs`, `parquet`, `json`, `spatial`, `fts`, `vss` vector search, `iceberg`, `delta`, `motherduck`), many autoloaded on demand.
- **Community/support:** large and fast-growing; excellent docs; gentle learning curve for anyone who knows SQL. Commercial support and a managed cloud (MotherDuck) available.

## Licensing & cost
- **License:** **MIT** — permissive, no open-core/enterprise tier; IP is held by the non-profit DuckDB Foundation to keep it MIT in perpetuity ([DuckDB FAQ](https://duckdb.org/faq)). No post-2018 relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** the engine is a free library you embed; MotherDuck is the optional managed cloud (separate commercial pricing).
- **Lock-in:** minimal — standard SQL, open file format, and trivial export to Parquet. MotherDuck-specific features are the only lock-in vector if you adopt the cloud.
- **Cost model:** the library is free; "cost" is the hardware you run it on. Scales cheaply on a single machine; cost rises only when you outgrow one box and must move to a distributed system.

## Hardware / deployment
- **Resource profile:** CPU- and memory-hungry for big scans; benefits hugely from many cores and RAM, but supports out-of-core processing so the working set need not fully fit in RAM. Memory limit is configurable (`memory_limit`).
- **Storage assumptions:** local NVMe/SSD ideal for the database file and spill. ⚠️ unverified as best practice — running the native file over network-attached/shared filesystems is explicitly cautioned against due to file-locking risks ([concurrency docs](https://duckdb.org/docs/current/connect/concurrency.html)); object storage is fine as a *data source* via `httpfs`, not as the live database file.
- **Footprint:** **embedded** — a single library linked into the host process; no daemon, no network port, no separate install. Also runs in the browser via WebAssembly.
- **Deployment:** on-prem/in-app/serverless-function/edge; container-friendly because it is just a dependency. No StatefulSet/cluster concerns — there is no cluster.

## Bottom line
Reach for DuckDB when you want fast analytical SQL on one machine with zero operational overhead — querying Parquet/CSV/Arrow, powering notebooks and data apps, dbt transforms, or embedding analytics in an application or browser. Do not reach for it as a multi-writer shared database server, an OLTP backend, or a horizontally scalable warehouse. The single biggest gotcha: the native file tolerates only **one read-write process at a time** (or many read-only) — point multiple writer processes at the same file and you risk blocking, errors, or corruption.

## Sources
- [Why DuckDB (official)](https://duckdb.org/why_duckdb)
- [DuckDB FAQ — license & foundation](https://duckdb.org/faq)
- [Transaction Management (official docs)](https://duckdb.org/docs/stable/sql/statements/transactions)
- [Analytics-Optimized Concurrent Transactions (official blog)](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions)
- [Changing Data with Confidence and ACID (official blog)](https://duckdb.org/2024/09/25/changing-data-with-confidence-and-acid)
- [Concurrency for multiple processes (official docs)](https://duckdb.org/docs/current/connect/concurrency.html)
- [Database of Databases — DuckDB](https://dbdb.io/db/duckdb)
- [MotherDuck — DuckDB 1.5 features](https://motherduck.com/blog/DuckDB-1.5-features-I-am-excited-about)
