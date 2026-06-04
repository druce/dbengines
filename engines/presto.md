---
name: Presto
slug: presto
rank: 59
data_model: Relational (distributed SQL query engine)
license: Apache License 2.0 (permissive)
summary: Facebook-born distributed SQL engine that queries data in place across many sources; storage-less MPP for interactive analytics, now diverged from the faster-moving Trino fork.
last_researched: 2026-06-04
confidence: high
---

# Presto

> A storage-less, in-memory MPP SQL engine ("PrestoDB") that federates queries across data lakes and external databases without owning the data — pick it for interactive OLAP over Hive/Iceberg/S3, but know that most of its mindshare and velocity moved to the [trino](trino.md) fork.

## When to use

**Use Presto if:**
- ✅ You need fast interactive SQL over a data lake/lakehouse (Hive/Iceberg/Delta on S3/HDFS) to replace slow Hive batch jobs
- ✅ You want to federate a single query across many sources (object storage + operational DBs) without copying data
- ✅ You value its Meta-scale pedigree and the C++/Velox ("Prestissimo") performance path with lower GC variance
- ✅ You want a stateless, storage-compute-separated engine that's cheap to idle-down since it holds no data

**Avoid Presto if:**
- ❌ You run long interactive queries on unreliable/spot nodes — the default path has no mid-query fault tolerance, so a single worker failure restarts the whole query (batch modes exist but aren't the default)
- ❌ You need OLTP, point lookups, or a system of record — it stores nothing and offers no engine-level durability
- ❌ You need long batch ETL with mid-query fault tolerance — prefer Trino's fault-tolerant execution or Spark SQL
- ❌ You want the largest connector set and community momentum — the faster-evolving Trino fork now leads; evaluate it first

## Identity
- **Taxonomy / data model:** Relational, SQL-on-everything **query engine** — not a database. Presto stores no data; it reads through pluggable **connectors** (Hive/S3, Iceberg, Delta, MySQL, PostgreSQL, Cassandra, Kafka, MongoDB, Redshift, etc.) and can join across them in a single query ([Presto: SQL on Everything](https://trino.io/Presto_SQL_on_Everything.pdf)). It is a federated compute layer; durability, schema, and storage live in the underlying source.
- **Storage model:** None of its own. On-disk format is whatever the connector targets (ORC/Parquet on object storage for the dominant Hive/Iceberg case). Execution is **pipelined and largely in-memory** between stages — unlike Hive MapReduce, it does not materialize each stage to disk. It does, however, support **opt-in spill-to-disk** for aggregations and joins (and, in newer versions, ordering/window ops) when a query exceeds memory limits ([Spill to Disk — Presto docs](https://prestodb.io/docs/current/admin/spill.html)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) relevant — Presto owns no persistence layer.
- **Workload:** OLAP / interactive ad-hoc analytics; see [oltp-olap-htap](../concepts/oltp-olap-htap.md). Built to replace slow Hive batch jobs with seconds-to-minutes interactive SQL. **Not HTAP and not OLTP** — no point writes, no transactional updates of its own.

## Distribution & consistency
- **Architecture:** one **coordinator** (parse, plan, optimize, schedule) plus N **workers** (execute query fragments). Communication is HTTP on a single port; workers register via a discovery service on the coordinator. A later **disaggregated coordinator** design splits coordinator duties to scale very large clusters ([Disaggregated Coordinator, 2022](https://prestodb.io/blog/2022/04/15/disggregated-coordinator/)).
- **CAP under partition:** N/A in the classic database sense — Presto has no replicated state store of its own; consistency semantics are inherited from each connector's source system. See [cap-pacelc](../concepts/cap-pacelc.md). As a cluster it is **not partition-tolerant**: historically a coordinator or worker failure fails the whole query (see below).
- **PACELC:** N/A — no Presto-owned replicated data.
- **Default isolation & what's achievable:** Presto exposes a transaction API and **the SQL standard's four isolation levels are defined in the connector SPI, but actual transactional support is per-connector** ([PrestoDB on dbdb.io](https://dbdb.io/db/prestodb)). Most analytic reads run as read-only snapshots against immutable files; cross-connector multi-statement ACID is **not** provided. ⚠️ unverified — exact default isolation level varies by connector; treat any blanket "ACID" claim as connector-specific, not engine-wide. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication / failover:** N/A at the engine layer — Presto replicates no data. Worker pool is scaled horizontally for throughput, not redundancy. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** N/A — defers to source.
- **Clock dependency:** None for correctness; no [clocks-and-time](../concepts/clocks-and-time.md) / TrueTime reliance.

## Schema
- **Schema-on-read.** Presto imposes a relational view over external data; the catalog/schema/table namespace is supplied by each connector (e.g., Hive Metastore or Glue). It does not own a write-side schema.
- **Migration / DDL:** DDL (CREATE/ALTER/DROP TABLE, etc.) is delegated to the connector; behavior and locking are the source's concern (e.g., Iceberg gives cheap metadata-only schema evolution; Hive does not).
- **Type system:** Rich ANSI-style types — VARCHAR, DECIMAL, DATE/TIMESTAMP (with time zone), ARRAY, MAP, ROW (structs), JSON, and geospatial functions. No native vector/ANN type. ⚠️ unverified — vector search is not a first-class Presto feature.

## Query interface
- **Language:** ANSI-leaning **SQL** with window functions, CTEs, complex types, and a large built-in function library; client speaks the Presto REST/HTTP protocol (JDBC/ODBC drivers wrap it).
- **Transactions:** Connector-dependent; effectively **read-oriented** for analytics. No general multi-statement ACID across federated sources.
- **Native vs app-side:** Joins, aggregations, window functions, and cross-source joins are all native and distributed. **Secondary indexes are not a Presto concept** — it relies on partition pruning, predicate/column pushdown to connectors, and columnar file skipping for performance.
- **Stored procedures / UDFs:** User-defined functions in Java (plugin SPI); some connectors expose procedures (e.g., system procedures). No PL/SQL-style stored procedure language.

## Scaling & topology
- **Horizontal**, MPP: add workers for more parallelism. Coordinator is a scaling bottleneck on huge clusters, addressed by the disaggregated-coordinator work.
- **Sharding/partitioning:** N/A as owned state — Presto exploits the **source's** partitioning (e.g., Hive partitions) for pruning; no resharding pain because it stores nothing.
- **Read replicas / read consistency:** N/A — reads hit the source directly; consistency is the source's.
- **Storage/compute separation:** This *is* the model — compute is fully decoupled from storage (typically S3/HDFS object storage). See [storage-compute-separation](../concepts/storage-compute-separation.md). **RaptorX** added a multi-tier caching layer (local disk/in-memory) to cut object-store latency.

## Performance & durability
- **Write path:** N/A for engine durability — Presto has no WAL of its own; durability is the connector/source's (see [wal-and-durability](../concepts/wal-and-durability.md)). Writes via connectors (e.g., INSERT into a Hive/Iceberg table) inherit that source's commit semantics.
- **Throughput/latency:** Strong for interactive scan-heavy and aggregation queries; pipelined in-memory execution avoids MapReduce-style materialization. **Tail/p99 risk:** a single worker crash historically kills the whole query, so p99 on long queries can spike to "rerun from scratch." Spill-to-disk is supported but opt-in and limited (aggregations/joins, plus ordering and window functions in newer releases) and slows queries by orders of magnitude; with spill disabled, memory-bound queries that exceed limits fail rather than spilling ([Spill to Disk — Presto docs](https://prestodb.io/docs/current/admin/spill.html)).
- **Fault tolerance:** The default interactive execution path has **no mid-query checkpointing** — a coordinator or worker failure fails the query and the client must retry it whole ([Presto: SQL on Everything](https://trino.io/Presto_SQL_on_Everything.pdf), [prestodb#11241](https://github.com/prestodb/presto/issues/11241)). This is the single biggest operational gotcha for long-running batch on spot instances. For batch, Presto offers partial-recovery paths — **recoverable grouped execution** (per-partition "lifespan" retries when stages write to persistent storage) and **Presto on Spark** (materialized shuffle with partition-level retries) ([Presto on Spark](https://prestodb.io/blog/2021/11/15/what-is-presto-on-spark/)) — but these are batch-oriented and not the default interactive mode. The [trino](trino.md) fork added general task-level fault-tolerant execution (since v376).
- **Compaction / vacuum / GC:** N/A at the engine — file compaction is a source-side (Iceberg/Hive) concern. JVM GC pauses on Java workers can affect p99; the C++ worker rewrite (below) targets exactly this.

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** N/A — stateless engine; back up the underlying stores. Time-travel/snapshots come from the connector (e.g., Iceberg snapshots), not Presto.
- **Observability:** EXPLAIN / EXPLAIN ANALYZE query plans, a web UI for live query/stage/task inspection, JMX metrics; Prometheus reporter available for the C++ workers ([prestodb blog, 2024](https://prestodb.io/blog/2024/09/03/capturing-worker-runtime-metrics-with-prometheus-reporter-in-presto-c/)).
- **Upgrade story:** Cluster software upgrade; because it is stateless, rolling/replace upgrades are comparatively low-risk versus a stateful DB, though in-flight queries are lost on coordinator restart. Day-2 burden is mostly cluster sizing, memory tuning, and connector/metastore management.
- **Maturity:** Battle-tested at **Meta scale** for over a decade and used in production at IBM. **Presto C++ ("Prestissimo", a.k.a. Presto 2.0)** replaces the Java worker with a C++ engine built on the **Velox** library for major speedups and lower GC variance, in production at Meta and IBM ([Diving into Presto C++, 2024](https://prestodb.io/blog/2024/06/24/diving-into-the-presto-native-c-query-engine-presto-2-0/)). No formal Jepsen report — and Jepsen is largely N/A given Presto owns no distributed state.

## Ecosystem & people
- **Canonical use cases:** Interactive SQL over data-lake/lakehouse files (Hive/Iceberg/Delta on S3/HDFS); ad-hoc analytics; federated queries joining a lake with operational databases; BI dashboards over object storage.
- **Anti-patterns:** OLTP / high-concurrency point lookups; low-latency single-row reads; long batch ETL needing mid-query fault tolerance (use [trino](trino.md)'s fault-tolerant execution or [apache-spark-sql](apache-spark-sql.md)); anything needing the engine itself to durably store or transactionally update data.
- **Connectors / integrations:** Hive, Iceberg, Delta Lake, MySQL, PostgreSQL, SQL Server, Cassandra, Kafka, MongoDB, Redshift, Elasticsearch, and more; JDBC/ODBC; dbt and BI tools (Tableau, Superset, etc.) connect via the SQL/JDBC layer.
- **Community / support:** Governed by the **Presto Foundation under the Linux Foundation** (since Sept 2019); members include Meta and IBM. Commercial backing narrowed after the original creators forked to Trino and **Ahana** (the PrestoDB cloud vendor) was acquired by IBM in 2023. Docs are decent; community momentum is notably smaller than Trino's.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing; see [license-taxonomy](../concepts/license-taxonomy.md). No source-available/SSPL restrictions.
- **Self-managed vs managed:** Self-managed open source; managed offerings include AWS (Athena and EMR are Presto/Trino-derived), IBM (post-Ahana watsonx.data), and others. ⚠️ unverified — note AWS Athena's lineage straddles both Presto and Trino over time; verify the exact engine version per service.
- **Lock-in:** Low — it is a stateless engine over open formats; switching to [trino](trino.md) is plausible (shared ancestry) though dialects/SPIs have diverged.
- **Cost model:** No license cost (OSS); you pay for the **compute cluster** (per-node/per-core) plus the underlying storage and metastore. Cost scales with worker count and query concurrency; cheap to idle-down since it holds no data.

## Hardware / deployment
- **Resource profile:** **Memory- and CPU-bound.** Working set of a query (hash tables, sorts, joins) should fit in cluster RAM; with spill disabled, Presto fails queries that exceed per-query/per-node memory limits, so right-sizing worker memory (or enabling spill-to-disk) is critical.
- **Storage assumptions:** Reads from network-attached object storage (S3/HDFS) is the norm; RaptorX caching mitigates that latency. Local NVMe helps caching/spill.
- **Footprint:** **Clustered** (coordinator + workers); not embedded, not single-node-serious for scale. Runs on VMs or Kubernetes.
- **Deployment:** On-prem or cloud; container/k8s-friendly (workers are stateless, easy to scale as Deployments rather than StatefulSets).

## Bottom line
Reach for Presto when you need fast interactive SQL across a data lake or to federate queries over many sources without copying data, and you value its Meta-scale pedigree and the C++/Velox performance path. Do **not** use it for OLTP, point lookups, or as a system of record — it stores nothing and offers no engine-level durability. The biggest gotcha: the default interactive path has **no mid-query fault tolerance** (a node failure restarts the whole query — batch modes like recoverable grouped execution and Presto on Spark exist but are not the default), and for most users the faster-evolving [trino](trino.md) fork now has more connectors, features, and community — evaluate Trino before defaulting to PrestoDB.

## Sources
- [Presto: SQL on Everything (ICDE 2019 paper, PDF)](https://trino.io/Presto_SQL_on_Everything.pdf)
- [PrestoDB official docs — Concepts](https://prestodb.github.io/docs/current/overview/concepts.html)
- [PrestoDB on Database of Databases (dbdb.io)](https://dbdb.io/db/prestodb)
- [Presto joins the Linux Foundation (2019)](https://prestodb.github.io/blog/2019/09/23/linux-foundation)
- [Diving into the Presto Native C++ Query Engine (Presto 2.0), 2024](https://prestodb.io/blog/2024/06/24/diving-into-the-presto-native-c-query-engine-presto-2-0/)
- [Disaggregated Coordinator (2022)](https://prestodb.io/blog/2022/04/15/disggregated-coordinator/)
- [prestodb#11241 — Fault tolerance for long running queries](https://github.com/prestodb/presto/issues/11241)
- [Spill to Disk — PrestoDB docs](https://prestodb.io/docs/current/admin/spill.html)
- [What is Presto on Spark? (2021)](https://prestodb.io/blog/2021/11/15/what-is-presto-on-spark/)
- [Presto (SQL query engine) — Wikipedia](https://en.wikipedia.org/wiki/Presto_(SQL_query_engine))
- [Starburst — PrestoDB vs PrestoSQL vs Trino](https://www.starburst.io/blog/prestodb-vs-prestosql/)
