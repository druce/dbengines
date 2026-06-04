---
name: PostgreSQL
slug: postgresql
rank: 4
data_model: Relational
license: PostgreSQL License (permissive)
summary: Battle-tested open-source relational DB with a deep extension ecosystem; the safe default for OLTP.
last_researched: 2026-06-04
confidence: high
---

# PostgreSQL

> The boringly-reliable open-source relational default: real serializable isolation, MVCC, and an extension ecosystem (PostGIS, pgvector, Citus) that lets it impersonate half the other engines in this wiki — at the cost of vacuum/bloat management and no built-in sharding.

## Identity
- **Taxonomy / data model:** Relational (SQL) core, but effectively multi-model via extensions and built-in types: document (JSONB), key-value (hstore), geospatial ([postgis](postgis.md)), vector (pgvector), full-text search, time-series ([timescaledb](timescaledb.md)), and graph (Apache AGE). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Row-store, heap tables + B-tree (default) and GiST/GIN/BRIN/SP-GiST/Hash indexes. Not [LSM](../concepts/lsm-vs-btree.md). On-disk: 8 KB pages, fixed-size heap with a visibility map and free space map. Column-store only via extensions/foreign data wrappers (e.g. Citus columnar, Hydra).
- **Workload:** Primarily OLTP. Capable of moderate analytical/HTAP work (parallel query, partitioning, JIT), but the row-store heap is not competitive with column stores like [duckdb](duckdb.md) / [clickhouse](clickhouse.md) on large scans. No native HTAP separation — analytics either runs on the same heap (contending with OLTP) or on a read replica.

## Distribution & consistency
- **CAP under partition:** A single primary is CP within itself; the cluster's behavior depends on the replication/failover tooling you bolt on (Patroni, repmgr). Core PostgreSQL ships no automatic consensus-based failover. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Single-node has no partition tradeoff. With async streaming replication: under partition the primary stays available (replicas may stale or be promoted, risking lost writes / split-brain); else, favors latency over consistency (replica reads are eventually consistent). Synchronous replication shifts toward consistency at the cost of write latency.
- **Default isolation & what's achievable:** Default is **READ COMMITTED**. `REPEATABLE READ` is implemented as **snapshot isolation** (blocks dirty/non-repeatable reads and phantoms, but not write skew). True **SERIALIZABLE** is available via **SSI (Serializable Snapshot Isolation)**, which detects dangerous read-write dependency cycles and aborts a transaction with a serialization failure. See [isolation-levels](../concepts/isolation-levels.md) and [mvcc](../concepts/mvcc.md).
  - ⚠️ Caveat: Jepsen found PostgreSQL 12.3 `SERIALIZABLE` exhibited G2-item (a true serializability violation present since SSI's introduction in 9.1); it was patched in the following minor release. [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3)
- **Replication:** Single-leader (primary/standby). Physical streaming replication (WAL shipping) and logical replication (row-level, publish/subscribe, since 10). Sync or async, configurable per-standby; `synchronous_commit` is tunable (`off`, `local`, `remote_write`, `on`, `remote_apply`). No native multi-leader (BDR/pgEdge are external). Failover is not automatic in core — split-brain prevention is the operator's (Patroni/etcd) responsibility. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Not per-query Dynamo-style levels. You get per-transaction isolation levels and per-commit synchronous durability settings, plus the choice to read from a replica (stale) vs primary.
- **Clock dependency:** No — correctness does not rest on synchronized clocks. MVCC visibility uses internal transaction IDs (XIDs) and snapshots, not wall-clock or [TrueTime/HLC](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid relational schema by default; schema-on-read achievable by storing JSONB and querying it. "Schemaless" is not a native mode.
- **Migration/evolution:** Many `ALTER TABLE` forms are fast (metadata-only `ADD COLUMN` with no rewrite since 11; nullable or volatile-default adds may rewrite). DDL is transactional (can run inside a transaction and roll back). `ALTER` can take an `ACCESS EXCLUSIVE` lock; index builds support `CREATE INDEX CONCURRENTLY` to avoid blocking writes. No fully online table rewrite in core (use pg_repack / logical replication tricks).
- **Type system:** Very rich — native JSON/JSONB, arrays, ranges, composite types, enums, UUID, network/CIDR, full-text `tsvector`, intervals, and user-defined types. Geospatial via [postgis](postgis.md); vectors via pgvector. Extensible type system is a core design point.

## Query interface
- **Language:** SQL, broadly standards-compliant (large subset of SQL:2016+), with rich extensions: CTEs (incl. recursive), window functions, `LATERAL`, `GROUPING SETS`/`ROLLUP`/`CUBE`, `MERGE` (since 15), SQL/JSON `JSON_TABLE` and constructors (since 17). [PostgreSQL 17 release notes](https://www.postgresql.org/about/news/postgresql-17-released-2936/)
- **Transactions:** Full multi-statement ACID, savepoints, transactional DDL.
- **Native vs app-side:** Native secondary indexes (multiple types, partial, expression, covering/`INCLUDE`), joins (hash/merge/nested-loop), aggregations, window functions, parallel query, JIT compilation (LLVM) for large queries.
- **Stored procedures / UDFs:** PL/pgSQL built-in; also PL/Python, PL/Perl, PL/Tcl, and external languages (PL/v8 for JS, PL/Rust). Procedures (with transaction control) since 11.

## Scaling & topology
- **Vertical vs horizontal:** Primarily scale-up. **No built-in automatic sharding.** Horizontal scale comes from extensions: [citus](citus.md) (distributed tables, columnar) or foreign-data-wrapper sharding; declarative partitioning (range/list/hash, since 10+) handles single-node large tables but is not distribution across nodes.
- **Read replicas:** Hot standbys serve read-only queries; reads are eventually consistent (replica lag), not guaranteed to see the latest commit unless using sync `remote_apply`.
- **Storage/compute separation:** Not in core. Achieved by ecosystem: Amazon Aurora (Postgres-compatible), Neon, and AlloyDB re-architect storage/compute. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WAL with group commit; `fsync` on by default, `synchronous_commit` controls the durability window. With `synchronous_commit=on` (default) and `fsync=on`, a committed transaction survives crash. **Data-loss window:** turning off `synchronous_commit` (async commit) risks losing the last `wal_writer_delay`-worth of committed transactions on crash; turning off `fsync` risks total corruption. With async replication, a primary failure can lose un-shipped WAL. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency profile:** Strong OLTP point-query and short-transaction performance. p99 tails are dominated by checkpoint spikes (I/O bursts), autovacuum activity, and lock contention.
- **Compaction / vacuum / GC:** MVCC keeps old row versions in the heap; **VACUUM** reclaims dead tuples and prevents transaction-ID wraparound; autovacuum runs in background. The classic gotcha: under high churn, bloat grows and autovacuum can fall behind, inflating p99 and disk usage; long-running transactions pin old versions and block cleanup. Wraparound emergencies can force aggressive vacuums. PostgreSQL 17 reworked vacuum memory management to reduce this pressure. [PostgreSQL 17 release notes](https://www.postgresql.org/about/news/postgresql-17-released-2936/) See [mvcc](../concepts/mvcc.md).

## Operations & maturity
- **Backup/restore, PITR:** Logical (`pg_dump`/`pg_restore`) and physical (`pg_basebackup`, WAL archiving for point-in-time recovery). Incremental physical backups added in 17. [PostgreSQL 17 release notes](https://www.postgresql.org/about/news/postgresql-17-released-2936/)
- **Observability:** `EXPLAIN`/`EXPLAIN ANALYZE` query plans, `pg_stat_*` views, `pg_stat_statements`, `auto_explain`, slow-query logging, rich extension/exporter ecosystem (Prometheus postgres_exporter).
- **Upgrade story:** Minor upgrades are in-place (restart). Major upgrades require `pg_upgrade` (brief downtime) or logical replication for near-zero-downtime cut-over. Day-2 burden centers on vacuum/bloat tuning, connection management (no built-in pooler — PgBouncer/pgcat external), and replication/failover orchestration.
- **Maturity:** 35+ years, extremely mature, huge production track record. Known failure modes: TXID wraparound if vacuum is neglected, connection exhaustion (process-per-connection model), replication lag, lock pile-ups on DDL. **Jepsen:** found and fixed a `SERIALIZABLE` G2-item bug in 12.3 ([Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3)). A 2025 report on **Amazon RDS multi-AZ clusters** (13.15–17.4) found Long-Fork anomalies — they do **not** provide the advertised snapshot isolation, behaving closer to Parallel Snapshot Isolation; root cause was primary/secondary disagreement on transaction order (in-memory lock order vs WAL order). This was specific to RDS clusters, **not** single-node PostgreSQL. [Jepsen: Amazon RDS for PostgreSQL 17.4](https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4)

## Ecosystem & people
- **Canonical use cases:** General-purpose OLTP, system-of-record, multi-tenant SaaS, geospatial ([postgis](postgis.md)), JSON document workloads, and increasingly vector/RAG search (pgvector). The reflexive "just use Postgres" default.
- **Anti-patterns:** Massive analytical scans over wide tables (use [duckdb](duckdb.md)/[clickhouse](clickhouse.md)); write-heavy workloads needing horizontal scale without operational appetite for Citus/sharding; very high connection counts without a pooler; globally-distributed multi-region writes (use [cockroachdb](cockroachdb.md)/[yugabytedb](yugabytedb.md)).
- **Drivers / connectors:** First-class drivers in every language (libpq, JDBC, psycopg, pgx, node-postgres); ORMs (Hibernate, SQLAlchemy, Prisma, ActiveRecord); CDC via logical replication / Debezium; dbt, Kafka Connect, every BI tool.
- **Community:** Large, independent, vendor-neutral global community; no single corporate owner. Excellent documentation. Abundant engineer availability; gentle learning curve to start, deeper for vacuum/replication/performance tuning.

## Licensing & cost
- **OSS license:** [PostgreSQL License](https://www.postgresql.org/about/licence/) — permissive, MIT/BSD-style. No post-2018 relicensing; no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Fully self-hostable; also offered by every major cloud (RDS/Aurora, Cloud SQL/AlloyDB, Azure Database, Neon, Crunchy, Supabase). Core has no lock-in; managed services may add proprietary extensions or fork behavior (e.g. Aurora storage).
- **Cost model:** Free software. Managed cost is per-instance (vCPU/RAM) + storage + IOPS, or serverless (Aurora/Neon) per-capacity-unit. Cheap at small scale; vertical-scaling ceiling and replica fan-out drive cost up before sharding becomes necessary.

## Hardware / deployment
- **Resource profile:** Benefits heavily from RAM (shared_buffers + OS page cache); working set ideally fits in RAM for low-latency OLTP, but does not require all data in memory. Can be CPU-bound on complex queries, I/O-bound on checkpoints/vacuum.
- **Storage assumptions:** Happy on NVMe/SSD; tolerant of network-attached storage (EBS) though fsync latency matters. Local SSD best for write-heavy.
- **Footprint:** Single-node by default; clustered via external HA tooling. Not embedded (contrast [sqlite](sqlite.md)/[duckdb](duckdb.md)). Serverless variants exist (Neon, Aurora Serverless).
- **Deployment:** SaaS or on-prem; container/k8s-friendly with operators (CloudNativePG, Zalando, Crunchy) handling StatefulSet/PVC and failover realities.

## Bottom line
Reach for PostgreSQL by default for any OLTP or general-purpose relational workload, especially when you value correctness (real serializable via SSI), a rich type system, and an extension ecosystem that pushes off the need for a second database. Don't reach for it for large-scale analytics (column stores win), or when you need built-in horizontal scaling or multi-region active-active without taking on Citus/Cockroach-class operational complexity. The single biggest gotcha is **MVCC bloat and vacuum**: neglect autovacuum (or run long transactions) and you get table bloat, p99 spikes, and — at the extreme — transaction-ID-wraparound emergencies.

## Sources
- [PostgreSQL official documentation](https://www.postgresql.org/docs/current/)
- [PostgreSQL 17 Released (release announcement)](https://www.postgresql.org/about/news/postgresql-17-released-2936/)
- [PostgreSQL License](https://www.postgresql.org/about/licence/)
- [PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/)
- [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3)
- [Jepsen: Amazon RDS for PostgreSQL 17.4](https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4)
