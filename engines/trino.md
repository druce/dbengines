---
name: Trino
slug: trino
rank: 53
data_model: Relational (distributed SQL query engine)
license: Apache License 2.0 (permissive)
summary: Storage-less distributed SQL engine that federates queries across many data sources; an analytics query layer, not a database.
last_researched: 2026-06-04
confidence: high
---

# Trino

> A massively-parallel, storage-less SQL **query engine** (forked from Presto) that runs interactive analytics across heterogeneous data sources you already have — it stores nothing itself, so its consistency and durability are entirely those of the connected systems.

## When to use

**Use Trino if:**
- ✅ You need fast, standard ANSI SQL over data scattered across a lake plus several databases, without first centralizing it via ETL
- ✅ You want interactive BI/ad-hoc analytics over a lakehouse (Iceberg/Delta/Hive on object storage)
- ✅ You need to federate-join a warehouse, an RDBMS, and a search index in one query, or run SQL ETL into Iceberg/Delta with fault-tolerant execution
- ✅ You want fully decoupled compute over storage queried in place, scaling workers independently

**Avoid Trino if:**
- ❌ You need a system of record — it stores nothing; durability, isolation, and consistency are entirely inherited from each connected source (the biggest gotcha)
- ❌ Your workload is OLTP, high-concurrency low-latency point lookups, or chatty per-row updates/deletes
- ❌ You expect cross-source ACID or cross-catalog transactions — there is no distributed 2PC across connectors
- ❌ A federated join touches a slow/weak source — it is only as fast and safe as the slowest source it touches

## Identity
- **Taxonomy / data model:** relational query engine over external sources via pluggable **connectors**; presents everything as catalogs/schemas/tables with ANSI SQL. It is explicitly **not a database** — no native storage layer ([Trino overview](https://trino.io/docs/current/overview.html)).
- **Storage model:** none of its own. Storage characteristics ([lsm-vs-btree](../concepts/lsm-vs-btree.md), file/columnar format) belong to the backing source — most commonly columnar lake formats (Parquet/ORC) via [apache-iceberg](apache-iceberg.md), Delta Lake, Hive; also RDBMSs ([postgresql](postgresql.md), [mysql](mysql.md)), [apache-cassandra](apache-cassandra.md), [mongodb](mongodb.md), [elasticsearch](elasticsearch.md), [clickhouse](clickhouse.md), object stores, Kafka, etc. See [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** OLAP / interactive analytics and federation; increasingly ETL/batch via fault-tolerant execution. Not OLTP (no point-write workload, no indexes it owns). See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — it is the analytic side that queries other systems' operational data.

## Distribution & consistency
- **Architecture:** one coordinator (parse, plan, schedule) + N stateless workers executing pipelined stages in memory ([Trino concepts](https://trino.io/docs/current/overview/concepts.html)).
- **CAP under partition:** N/A as a stateful system — Trino holds no replicated data. A query either completes or fails; consistency/availability of the *data* is the source's property. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — no replication of persistent state to trade off.
- **Isolation & transactions:** SQL transactions (`START TRANSACTION`/`COMMIT`) exist and the grammar accepts all four ANSI isolation levels ([READ UNCOMMITTED → SERIALIZABLE](https://trino.io/docs/current/sql/start-transaction.html)), but the **effective** isolation is whatever the connector provides. Multi-source distributed transactions are not coordinated across catalogs. For lake tables, ACID and isolation come from the table format: the [Iceberg connector](https://trino.io/docs/current/connector/iceberg.html) uses Iceberg's transaction API and supports serializable (default) and snapshot isolation. ⚠️ unverified — treating Trino's `SET TRANSACTION ISOLATION` as a global, source-independent guarantee is a mistake; do not assume serializable across federated joins. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication / clock dependency:** N/A — coordinator is a single point of scheduling (not data); correctness does not rest on synchronized clocks ([clocks-and-time](../concepts/clocks-and-time.md)). See [replication-models](../concepts/replication-models.md).

## Schema
- **Schema model:** schema-on-read in spirit — Trino imposes a relational view over the source. Schema rigidity is the source's (Iceberg/Hive metastore, RDBMS catalog, JSON-on-read for document/search sources).
- **Migration / DDL:** DDL support varies by connector; on Iceberg/Delta, online schema evolution (add/drop/rename column) is supported because the table format handles it — no table rewrite. Many connectors are read-only or limited-DDL.
- **Type system:** rich SQL types incl. `ARRAY`, `MAP`, `ROW` (nested), `JSON`, `DECIMAL`, date/time with time zone, `UUID`, IP address, and geospatial functions. No first-class native vector/ANN index (delegated to sources).

## Query interface
- **Language:** ANSI SQL (its own dialect, broadly standards-aligned) with window functions, CTEs, grouping sets, `LATERAL`, correlated subqueries, and a large built-in function library.
- **Transactions:** multi-statement transactions per the SQL grammar, but real guarantees are connector-bound (see above); no cross-catalog 2PC.
- **Native vs app-side:** joins, aggregations, and cross-source (federated) joins are executed **inside** Trino — it pulls data from each source and joins in its own engine, which is the headline feature and also the main performance trap (large cross-source joins shuffle a lot). Predicate/projection pushdown into sources is connector-dependent.
- **Stored procedures / UDFs:** Java/plugin SDK for connectors and functions; SQL-language routines (`FUNCTION`) supported in recent versions. No PL/pgSQL-style server-side procedural language beyond that.

## Scaling & topology
- **Horizontal:** add workers to scale query parallelism; near-linear for scan/aggregate-heavy work. Coordinator scales vertically (planning is centralized; HA coordinator setups are an enterprise/distribution concern).
- **Sharding/partitioning:** none of its own — relies on source partitioning and the connector's split generation to parallelize scans.
- **Read replicas / read consistency:** N/A — Trino reads whatever the source serves; snapshot consistency for a query depends on the source (e.g., Iceberg snapshot isolation gives a stable read).
- **Storage/compute separation:** this **is** the model — compute is fully decoupled from storage, which it queries in place (lakehouse pattern). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** Trino has no durability of its own; on write to a lake/RDBMS, the [wal-and-durability](../concepts/wal-and-durability.md) and crash-recovery story is the target system's. Trino's job is to push committed files/rows.
- **Execution & latency:** classic mode is fully **in-memory, pipelined MPP** — fast for interactive queries but historically a single worker loss kills the query. **Fault-tolerant execution (Project Tardigrade, `retry-policy=TASK|QUERY`, GA-tracked since ~v376)** adds exchange spooling so individual tasks retry on worker failure, enabling long ETL on spot/preemptible nodes at the cost of latency ([Tardigrade launch](https://trino.io/blog/2022/05/05/tardigrade-launch.html), [fault-tolerant execution docs](https://trino.io/docs/current/admin/fault-tolerant-execution.html)). This is a key difference from upstream PrestoDB, whose retries are query-level ([Starburst on Presto vs Trino](https://www.starburst.io/blog/prestodb-vs-prestosql/)).
- **Tail behavior:** p99 is dominated by source latency, skewed splits, and (in classic mode) memory pressure — large queries can fail with "exceeded memory limit" rather than spilling unless spill-to-disk/FTE is enabled.
- **Compaction/GC:** N/A for Trino itself; JVM GC pauses on workers are the operational analog. Table compaction (e.g., Iceberg `OPTIMIZE`) is invoked through Trino but performed on the source.

## Operations & maturity
- **Backup/restore/PITR:** N/A — there is nothing to back up except config; data backup/PITR is the source's responsibility (e.g., Iceberg time-travel/snapshots).
- **Observability:** rich `EXPLAIN`/`EXPLAIN ANALYZE` plans, a live query/stage Web UI, JMX metrics, event listeners, and per-query stats; strong query-plan introspection.
- **Upgrade story:** frequent releases (monthly-ish; v481+ as of 2025–26). No rolling cross-version cluster — coordinator and workers must run the **same version**, so upgrades are a full-cluster restart; plan for a brief query outage. Day-2 burden is mostly memory tuning, connector config, and metastore/catalog management.
- **Maturity:** very mature, widely deployed (Netflix/Meta-lineage via Presto; Amazon Athena is managed Presto/Trino-family). No formal **Jepsen** report applies, and one largely wouldn't — Trino holds no replicated state to test for linearizability; correctness questions reduce to the connectors'.

## Ecosystem & people
- **Canonical use cases:** interactive BI/ad-hoc SQL over a data lake/lakehouse; federated queries joining a warehouse, an RDBMS, and a search index without ETL; SQL-based ETL into Iceberg/Delta with fault-tolerant execution.
- **Anti-patterns:** OLTP or high-concurrency low-latency point lookups; a system of record (it stores nothing); chatty per-row updates/deletes; treating a federated join across two slow sources as cheap; relying on it for cross-source ACID.
- **Connectors/integrations:** dozens of official connectors; works with dbt (trino adapter), BI tools (Tableau, Superset, Power BI) via JDBC/ODBC, and the Python client. CDC is upstream-source territory, not Trino's.
- **Community / support:** large active OSS community under the Trino Software Foundation; commercial support and a managed/enterprise product from **Starburst** (Galaxy/Enterprise), plus AWS Athena and other managed offerings. Docs are thorough.

## Licensing & cost
- **License:** [Apache License 2.0](https://trino.io/foundation.html) (permissive — see [license-taxonomy](../concepts/license-taxonomy.md)); governed by the independent **Trino Software Foundation**. **No relicensing** — the foundation explicitly commits to staying Apache 2.0, a deliberate contrast to source-available shifts elsewhere. (Trino is the 2020-renamed fork of PrestoSQL.)
- **Self-managed vs managed:** fully self-hostable for free; managed via Starburst Galaxy, AWS Athena/EMR, etc. Lock-in risk is low for core SQL; Starburst-only features (Warp Speed, governance) are the lock-in surface.
- **Cost model:** OSS = your compute. Managed offerings price per-cluster/compute-hour or per-query (Athena = per-TB scanned). At scale, cost tracks worker count and data scanned; columnar formats + partition pruning are the main levers.

## Hardware / deployment
- **Resource profile:** memory- and CPU-bound — classic execution keeps intermediate results in RAM, so workers want lots of memory; the working set of a query (not all data) must fit, or you need spill/FTE. Fast network matters for shuffles.
- **Storage assumptions:** none locally beyond spill scratch; reads from object storage (S3/GCS/ADLS) or remote DBs, so it tolerates network-attached latency by design.
- **Footprint:** clustered (coordinator + workers); not embedded, not single-node-oriented (though a single node can run both roles for dev).
- **Deployment:** runs on VMs, bare metal, and Kubernetes; container/k8s-friendly with stateless workers, which suits autoscaling. SaaS via Starburst Galaxy / Athena.

## Bottom line
Reach for Trino when you have data scattered across a lake plus several databases and want fast, standard SQL over all of it without first centralizing it — the storage-less, connector-based design is its superpower and its limit. Do **not** use it as a system of record, for OLTP, or for high-concurrency point lookups, and never assume it provides cross-source transactions or end-to-end ACID — those guarantees live in the connected systems, not in Trino. Biggest gotcha: it stores nothing, so durability, isolation, and "is my data consistent" are entirely inherited from each source, and a federated join is only as fast and safe as the slowest, weakest source it touches.

## Sources
- [Trino overview](https://trino.io/docs/current/overview.html)
- [Trino concepts (coordinator/worker architecture)](https://trino.io/docs/current/overview/concepts.html)
- [Connectors (SPI / federation)](https://trino.io/docs/current/develop/connectors.html)
- [START TRANSACTION (isolation levels)](https://trino.io/docs/current/sql/start-transaction.html)
- [Iceberg connector (ACID, serializable/snapshot isolation)](https://trino.io/docs/current/connector/iceberg.html)
- [Fault-tolerant execution docs](https://trino.io/docs/current/admin/fault-tolerant-execution.html)
- [Project Tardigrade launch](https://trino.io/blog/2022/05/05/tardigrade-launch.html)
- [Trino Software Foundation / Apache 2.0 license](https://trino.io/foundation.html)
- [Starburst: PrestoDB vs PrestoSQL/Trino](https://www.starburst.io/blog/prestodb-vs-prestosql/)
