---
name: TimescaleDB
slug: timescaledb
rank: 62
data_model: Time-series (PostgreSQL extension)
license: Apache 2.0 (core) + Timescale License (TSL, source-available) for advanced features
summary: PostgreSQL extension that turns Postgres into a time-series database via auto-partitioned hypertables and columnar compression — full SQL, but single-node only since multi-node was removed in 2.14.
last_researched: 2026-06-04
confidence: high
---

# TimescaleDB

> A PostgreSQL extension that adds time-series superpowers (auto-partitioning, columnar compression, continuous aggregates) without leaving SQL or the Postgres ecosystem — at the cost of inheriting Postgres's single-writer scaling ceiling now that distributed multi-node is gone.

## Identity
- **Taxonomy / data model:** Time-series database implemented as a [postgresql](postgresql.md) extension; relational underneath, so you also get full relational/JSON/geospatial modeling. Vendor (Timescale, rebranded **Tiger Data** in June 2025; the OSS extension keeps the name TimescaleDB) now positions it as general-purpose "modern Postgres" beyond time-series ([rebrand announcement](https://www.tigerdata.com/blog/announcing-the-new-timescale)).
- **Storage model:** Hybrid row+columnar, branded **Hypercore** since v2.18 (Jan 2025) — the same engine previously surfaced only as "compression" ([Hypercore docs](https://docs.timescale.com/use-timescale/latest/hypercore/)). Recent data lives in Postgres row-store heap (B-tree, [lsm-vs-btree](../concepts/lsm-vs-btree.md)); older chunks are transactionally rewritten into a **columnar compressed** format (values grouped ~1,000 rows/column into arrays, then compressed with type-specific codecs: delta-of-delta, Gorilla for floats, dictionary for low-cardinality, run-length/simple-8b) ([compression methods](https://www.tigerdata.com/docs/learn/columnar-storage/compression-methods)). Core abstraction is the **hypertable**: a virtual table auto-partitioned by time (and optionally a space dimension) into **chunks**, each a real child Postgres table. See [columnar-storage](../concepts/columnar-storage.md), [time-series-storage](../concepts/time-series-storage.md).
- **Workload:** Time-series ingest + analytics (a form of HTAP). Physical OLTP/OLAP separation is real, not vague: recent chunks stay row-oriented for fast writes/point lookups; aged chunks become columnar for scan-heavy analytics, and a `ColumnarScan` operator reads only referenced columns. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP, inherited from single-node [postgresql](postgresql.md): one primary accepts writes; on partition the primary stays consistent and replicas may serve stale reads. Not a quorum/multi-leader system. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EC** in practice — favors consistency on the primary; else (no partition) low latency on the primary, with the usual replica-lag tradeoff if you read from async replicas.
- **Default isolation & what's achievable:** Exactly PostgreSQL's: **Read Committed** by default, with snapshot isolation (Repeatable Read) and **Serializable via SSI** available. Genuinely ACID and genuinely serializable — not the "ACID-means-snapshot" hedge common elsewhere. Uses Postgres [mvcc](../concepts/mvcc.md). See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Postgres physical **streaming replication** (single-leader, WAL shipping; sync or async) ([Timescale replication docs](https://github.com/timescale/docs.timescale.com-content/blob/master/tutorials/replication.md)). Logical replication is **not recommended** for hypertables (partition-root and schema-sync limitations) ([same docs](https://github.com/timescale/docs.timescale.com-content/blob/master/tutorials/replication.md)). Postgres has no built-in automatic failover; HA needs external tooling, typically **Patroni** (etcd + Raft, [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)) ([Timescale + Patroni evaluation](https://www.tigerdata.com/blog/high-availability-timescaledb-postgresql-patroni-a4572264a831)). Split-brain protection is the failover tool's job, not the DB's.
- **Tunable consistency?** No per-query consistency levels. Choice is binary: read primary (fresh) vs async replica (possibly stale); synchronous replication exists but "isn't recommended" due to severe write-latency cost under load ([Severalnines](https://severalnines.com/blog/overview-streaming-replication-timescaledb/)).
- **Clock dependency:** None for correctness; ordering comes from MVCC/WAL, not wall clocks. See [clocks-and-time](../concepts/clocks-and-time.md). Time partitioning uses the row's own timestamp column, not server time.

## Schema
- **Schema-on-write:** rigid relational schema like Postgres; a hypertable is created from a normal table via `create_hypertable()`.
- **Migration/evolution:** `ALTER TABLE` on a hypertable cascades to chunks; Postgres online-DDL rules apply (adding a nullable/defaulted column is cheap on modern Postgres; some operations still lock). Changing schema on already-compressed chunks historically required care — newer versions relax this but verify per release.
- **Type system:** Full Postgres types — JSON/JSONB, arrays, geospatial via PostGIS, ranges, intervals; **vectors via pgvector / pgvectorscale** (Tiger Data ships pgvectorscale for ANN, [vector-search-ann](../concepts/vector-search-ann.md)). Toolkit adds time-series-specific types/functions (gauges, counters, percentile approximations) under TSL.

## Query interface
- **Language:** Standard **SQL** (full PostgreSQL dialect) — its biggest differentiator vs DSL-based TSDBs like [influxdb](influxdb.md). Adds functions: `time_bucket`, continuous aggregates, hyperfunctions.
- **Transactions:** Full multi-statement **ACID** (Postgres engine).
- **Native joins/indexes/aggregations:** All native — joins, window functions, CTEs, secondary B-tree/GIN/BRIN indexes, plus chunk-exclusion pruning so queries skip irrelevant time chunks.
- **Continuous aggregates:** materialized, incrementally-refreshed rollups (real-time aggregation combines materialized + fresh raw data) ([continuous aggregates docs](https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/about-continuous-aggregates)).
- **Stored procedures / UDFs:** Full Postgres support — PL/pgSQL, PL/Python, PL/v8, C, etc.

## Scaling & topology
- **Vertical first.** Single-node scale-up is the supported path. **Multi-node distributed hypertables were deprecated in 2.13 and removed in 2.14** (only ~1% of deployments used it; maintenance cost too high) ([multi-node deprecation notice](https://github.com/timescale/timescaledb/blob/main/docs/MultiNodeDeprecation.md)). Horizontal write sharding is now an **application-level concern**.
- **Sharding/partitioning:** automatic time-based chunking within a node (and optional space/hash dimension); resharding is not a typical operation since chunks are bounded by time. No cross-node sharding.
- **Read replicas:** Postgres physical replicas; reads can be **stale under load** unless synchronous replication is used ([Severalnines](https://severalnines.com/blog/overview-streaming-replication-timescaledb/)).
- **Storage/compute separation:** Not in the engine. **Timescale Cloud** adds **tiered storage** that moves aged chunks to bottomless **S3 object storage**, transparently queryable — a managed-only approximation of [storage-compute-separation](../concepts/storage-compute-separation.md) ([data tiering docs](https://docs.timescale.com/use-timescale/latest/data-tiering/enabling-data-tiering/)).

## Performance & durability
- **Write path:** PostgreSQL **WAL** + fsync; group commit applies. Data-loss window on crash is the standard Postgres story — none with `synchronous_commit=on`, a small async-flush window if relaxed, and with async replicas a failover can lose un-shipped WAL. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** High sustained ingest from time-ordered inserts hitting recent chunks; chunk pruning + columnar scans give strong analytical latency. p99 on writes depends on autovacuum and on compression jobs running on background workers.
- **Compaction/vacuum/GC:** Inherits Postgres **autovacuum/VACUUM** (bloat and p99 risk under high churn/updates — time-series append-heavy workloads mitigate this). Background **compression policies** rewrite old chunks (row→columnar) and **retention policies** drop old chunks; both run as scheduled jobs that compete for I/O and can affect tail latency.

## Operations & maturity
- **Backup/restore, PITR:** Full Postgres toolchain — `pg_dump`/`pg_restore`, physical base backups, **PITR via WAL archiving**, pgBackRest, etc.
- **Observability:** Postgres `EXPLAIN`/`EXPLAIN ANALYZE` query plans, `pg_stat_statements`, slow-query log, standard Postgres metrics exporters; hypertable/chunk/compression stats via Timescale views.
- **Upgrade story:** Extension upgrade via `ALTER EXTENSION timescaledb UPDATE`; major Postgres upgrades follow Postgres rules. Rolling upgrades need replica-promotion tooling (Patroni). Day-2 burden ≈ running production Postgres plus tuning compression/retention/continuous-aggregate policies.
- **Maturity:** Mature, widely deployed (vendor cites 3M+ active databases). Production users include Cloudflare for analytics ([Cloudflare blog](https://blog.cloudflare.com/timescaledb-art/)). **No public Jepsen report specific to TimescaleDB**; consistency/safety rests on the well-studied PostgreSQL engine. ⚠️ unverified — no independent formal-verification report for the columnar-compression/chunk machinery itself.
- **Known failure modes:** replica staleness under write bursts; autovacuum bloat on update-heavy use; background compression/retention jobs contending for I/O; loss of multi-node means a single hot shard can't be split across nodes.

## Ecosystem & people
- **Canonical use cases:** metrics/monitoring, IoT sensor data, financial tick/market data, event/observability analytics, real-time dashboards — anywhere you want SQL + Postgres ecosystem on time-series. Increasingly also general app DB + vector/RAG.
- **Anti-patterns:** workloads needing **horizontal write scale beyond one node** (multi-node is gone — consider [clickhouse](clickhouse.md), [apache-cassandra](apache-cassandra.md), or app-level sharding); extreme-cardinality pure metrics where a purpose-built TSDB compresses/scales cheaper; pure OLAP at petabyte scale ([clickhouse]] / [apache-druid](apache-druid.md) territory); key-value or graph workloads.
- **Drivers/connectors:** any **PostgreSQL driver/ORM** works unchanged (psql, JDBC, psycopg, SQLAlchemy, etc.); CDC via Postgres logical decoding / Debezium → Kafka; **dbt** support (dbt-timescaledb adapter); all Postgres BI tools (Grafana, Tableau, Metabase, Superset).
- **Community/support:** large by virtue of Postgres compatibility; strong docs; commercial support and managed cloud from Tiger Data. Low learning curve **if** you already know SQL/Postgres.

## Licensing & cost
- **Two-license model.** Core (hypertables, basic features) is **Apache 2.0** (permissive). Advanced features — **compression, continuous aggregates, tiered storage, some toolkit features** — are under the **Timescale License (TSL)**, a **source-available** license introduced in 2018 ([TSL text](https://github.com/timescale/timescaledb/blob/main/tsl/LICENSE-TIMESCALE), [rationale](https://www.tigerdata.com/blog/how-we-are-building-a-self-sustaining-open-source-business-in-the-cloud-era)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **What TSL restricts:** you may self-host and use Community (TSL) features free for internal/commercial use; you **may not offer TimescaleDB as a hosted Database-as-a-Service** ([TSL summary](https://www.tigerdata.com/blog/how-we-are-building-a-self-sustaining-open-source-business-in-the-cloud-era)). Practically: fine for almost everyone except would-be DBaaS competitors (this is why AWS RDS ships only the Apache-2 subset of features). A few "Enterprise" features need a commercial relationship.
- **Self-managed vs managed:** both. Self-host the extension on your own Postgres, or use **Timescale Cloud** (managed, adds tiered S3 storage and other cloud-only features). Lock-in is low at the SQL/Postgres level; higher if you depend on TSL/cloud-only features.
- **Cost model:** OSS = free (your hardware). Cloud = usage-based (compute + storage, with cheap tiered object storage for cold chunks). Costs scale with retained data; tiering is the lever to keep cold data cheap.

## Hardware / deployment
- **Resource profile:** like Postgres — memory helps (shared_buffers, working set / recent chunks ideally in RAM) but does **not** require all data in RAM; disk-bound for large historical scans, CPU spent on compression/decompression and analytical scans.
- **Storage assumptions:** local NVMe/SSD strongly preferred for the hot tier; tolerates network-attached (EBS-style) at a latency cost; cold tier offloads to S3 on Cloud.
- **Footprint:** single-node clustered-via-replication (no embedded mode). Runs anywhere Postgres runs.
- **Deployment:** self-hosted on-prem/VM, Docker, **Kubernetes** (official Helm chart / operator; StatefulSet + Patroni patterns), or **Timescale Cloud** SaaS.

## Bottom line
Reach for TimescaleDB when you have time-series or analytical workloads and want to **stay in PostgreSQL** — full SQL, ACID, joins, Postgres tooling, plus auto-partitioning, columnar compression, and continuous aggregates that vanilla Postgres lacks. Do **not** reach for it if you need horizontal write scale across nodes (multi-node was removed in 2.14, making single-node the ceiling) or if a purpose-built columnar engine like [clickhouse](clickhouse.md) would serve a pure-OLAP / extreme-cardinality workload far cheaper. The single biggest gotcha: **its scaling story is now Postgres's scaling story** — vertical scale-up plus read replicas — so capacity-plan the primary as if there is no sharding escape hatch, because there isn't one anymore.

## Sources
- [TimescaleDB GitHub (overview)](https://github.com/timescale/timescaledb)
- [Compression docs](https://github.com/timescale/docs.timescale.com-content/blob/master/using-timescaledb/compression.md)
- [Multi-node deprecation notice](https://github.com/timescale/timescaledb/blob/main/docs/MultiNodeDeprecation.md)
- [Replication tutorial](https://github.com/timescale/docs.timescale.com-content/blob/master/tutorials/replication.md)
- [HA with Patroni evaluation](https://www.tigerdata.com/blog/high-availability-timescaledb-postgresql-patroni-a4572264a831)
- [Streaming replication overview (Severalnines)](https://severalnines.com/blog/overview-streaming-replication-timescaledb/)
- [Continuous aggregates docs](https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/about-continuous-aggregates)
- [Data tiering to S3 docs](https://docs.timescale.com/use-timescale/latest/data-tiering/enabling-data-tiering/)
- [Timescale License (TSL) text](https://github.com/timescale/timescaledb/blob/main/tsl/LICENSE-TIMESCALE)
- [Building a self-sustaining OSS business (TSL rationale)](https://www.tigerdata.com/blog/how-we-are-building-a-self-sustaining-open-source-business-in-the-cloud-era)
- [Tiger Data rebrand announcement](https://www.tigerdata.com/blog/announcing-the-new-timescale)
- [Cloudflare: scaling analytics with TimescaleDB](https://blog.cloudflare.com/timescaledb-art/)
