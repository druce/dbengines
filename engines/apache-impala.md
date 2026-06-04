---
name: Apache Impala
slug: apache-impala
rank: 40
data_model: Relational (SQL-on-Hadoop / lakehouse MPP query engine)
license: Apache License 2.0 (permissive)
summary: Open-source MPP SQL query engine for the Hadoop/lakehouse stack — fast interactive analytics over HDFS/S3/Kudu/Iceberg, but it owns no storage and does no real transactions.
last_researched: 2026-06-04
confidence: high
---

# Apache Impala

> A daemon-based, massively-parallel SQL **query engine** (not a database) that runs low-latency analytic queries directly over data sitting in HDFS, S3/ADLS/Ozone, Kudu, HBase, and Iceberg — bring your own storage, durability, and consistency.

## Identity
- **Taxonomy / data model:** Relational, SQL-on-Hadoop / lakehouse MPP query engine. It is a compute layer, not a storage engine — it queries data in external stores ([HDFS, S3, ADLS, Ozone, Kudu, HBase, Iceberg](https://impala.apache.org/)).
- **Storage model:** No native storage. Reads columnar [Parquet]/[ORC], plus Avro, RCFile, text; columnar Parquet is the performance default ([db-engines / docs](https://impala.apache.org/)). For mutable data it leans on [apache-kudu](apache-kudu.md) (its sister project) or [apache-iceberg](apache-iceberg.md) table format. See [columnar-storage](../concepts/columnar-storage.md), [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLAP — interactive BI / ad-hoc analytics. Explicitly *not* OLTP: "Impala is primarily designed for analytical workloads"; no efficient single-row point operations. Built to give low latency + high concurrency for read-mostly queries where Hive/MapReduce was too slow ([Impala CIDR'15 paper](http://pandis.net/resources/cidr15impala.pdf)). See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Any "HTAP" framing only exists via Kudu (which supports row mutations) + Impala on top — Impala itself does not separate hot/cold paths.

## Distribution & consistency
- **Architecture:** shared-nothing MPP. Symmetric `impalad` daemons (each acts as query coordinator and/or executor) co-located on data nodes; `statestored` gossips cluster membership/health; `catalogd` propagates metadata ([docs/overview](https://impala.apache.org/)). No single master in the query path.
- **CAP under partition:** Largely **N/A** as a query engine — Impala holds no durable state of its own, so CAP applies to the *underlying* store ([apache-kudu](apache-kudu.md) is CP via Raft; HDFS is CP for its namenode). For query availability: if an `impalad` involved in a query dies, that query fails (no mid-query fault tolerance); the cluster stays up for new queries. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A for Impala itself — inherited from the backing store.
- **Default isolation & what's achievable:** Impala provides **atomicity and isolation of INSERT on transactional (insert-only) tables** — an insert commits in full or not at all, invisible to others until committed ([Impala transactions docs](https://impala.apache.org/docs/build/html/topics/impala_transactions.html)). This is **not** full ACID: only `CREATE/DROP/TRUNCATE/INSERT/SELECT` participate; there are **no multi-statement transactions** (every statement auto-commits) and **no UPDATE/DELETE** on these insert-only tables. Calling this "ACID" overstates it — it is insert-only atomicity, see [isolation-levels](../concepts/isolation-levels.md). On [apache-kudu](apache-kudu.md) tables, reads default to `READ_LATEST` = **read-committed**; `READ_AT_SNAPSHOT` gives repeatable snapshot reads ([KUDU_READ_MODE docs](https://impala.apache.org/docs/build/html/topics/impala_kudu_read_mode.html)). On Iceberg tables, snapshot isolation comes from Iceberg's table format, not Impala.
- **Replication:** N/A — delegated to the storage layer (HDFS block replication, Kudu Raft, S3 durability). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Only via Kudu read modes (above). See [clocks-and-time](../concepts/clocks-and-time.md) — Kudu's snapshot/external-consistency semantics depend on timestamps/clocks, not Impala.

## Schema
- **Schema-on-write vs schema-on-read:** Hybrid. Tables are declared in the [apache-hive](apache-hive.md) Metastore (HMS), but data files already exist on disk — so it is effectively **schema-on-read** with a catalog overlay. Schema and storage are decoupled.
- **Migration / DDL:** DDL (`ALTER TABLE`, add column, partitions) is metadata-only in HMS and cheap; no table rewrite for most changes. Iceberg tables get richer schema evolution / partition evolution via the table format. Historically, metadata changes made elsewhere require `INVALIDATE METADATA` / `REFRESH` to be seen — a classic day-2 gotcha (improved by automatic metadata invalidation via [apache-kafka](apache-kafka.md)/event-based notifications in recent versions).
- **Type system:** SQL scalar types, `DECIMAL`, `TIMESTAMP`, `DATE`, `STRING`, complex types (`STRUCT`, `ARRAY`, `MAP`) on Parquet/ORC/Iceberg. No native geospatial/vector types. No first-class JSON column type comparable to PostgreSQL's `jsonb` — JSON is stored as `STRING` and parsed with `GET_JSON_OBJECT` ([Impala data types docs](https://impala.apache.org/docs/build/html/topics/impala_datatypes.html)).

## Query interface
- **Language:** SQL. Impala SQL is **HiveQL-compatible** (shares the HMS catalog and dialect with [apache-hive](apache-hive.md)) — ANSI-style SELECT/JOIN/window functions/CTEs. Not full ANSI SQL standard compliance.
- **Transactions:** Insert-only atomicity per statement (above); **no BEGIN/COMMIT multi-statement transactions**; UPDATE/DELETE only against [apache-kudu](apache-kudu.md) or Iceberg V2 tables, executed as separate auto-committing statements.
- **Native vs app-side:** Native distributed joins (broadcast & partitioned/shuffle hash joins), aggregations, analytic/window functions, runtime filters. Cost-based optimizer using table/column stats (`COMPUTE STATS` — stale stats are a common cause of bad plans). No persistent secondary indexes (relies on partition pruning, Parquet/ORC predicate pushdown, runtime filters, Kudu's own indexing).
- **Stored procedures / UDFs:** UDFs/UDAFs in **C++** (native, fast) or **Java** (Hive-compatible). No stored-procedure language.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — add `impalad` daemons to add query parallelism/concurrency. Scaling is **compute-only**; storage scales independently in the underlying system.
- **Sharding/partitioning:** Inherited from storage — HDFS/Iceberg directory partitioning, Kudu hash/range partitioning. Partition pruning is the main scaling lever; over-partitioning ("small files problem") hurts.
- **Read replicas / consistency:** N/A at the engine level.
- **Storage/compute separation:** **Yes, by design** — this is the whole point. Compute (`impalad` fleet) is fully decoupled from storage (HDFS/S3/Kudu). Modern deployments run Impala over object storage, true [storage-compute-separation](../concepts/storage-compute-separation.md). Classic deployments co-locate daemons on data nodes for locality.

## Performance & durability
- **Write path / durability:** Impala does not own a [WAL](../concepts/wal-and-durability.md); durability belongs to the storage layer (HDFS fsync/replication, Kudu's per-tablet WAL, S3 durability). Insert-only-table inserts are atomic via the HMS transaction + write-then-publish; a failed INSERT/UPDATE/DELETE on non-transactional or Kudu tables **does not roll back partial effects** ([transactions docs](https://impala.apache.org/docs/build/html/topics/impala_transactions.html)). **Data-loss window** = whatever the backing store provides.
- **Throughput/latency:** Built for low-latency interactive analytics; native C++ runtime with LLVM **code generation (codegen)** per query, MPP execution, no MapReduce startup tax — historically much faster than Hive for interactive BI ([CIDR'15 paper](http://pandis.net/resources/cidr15impala.pdf)).
- **p99 / tail behavior:** Default execution is **in-memory / pipelined**; a query that exceeds its memory limit historically **failed** rather than spilling. Spill-to-disk for joins/aggregations/sorts has been added, but memory-bound failures and admission-control queueing under high concurrency are the classic tail-latency / reliability gotchas. No mid-query fault tolerance: a node failure kills the running query (it must be re-run).
- **Compaction/GC:** None of its own. Small-file compaction and Iceberg/Kudu maintenance are the storage layer's job.

## Operations & maturity
- **Backup/restore, PITR:** N/A in-engine — back up the underlying store (HDFS snapshots, Kudu backups, S3 versioning, Iceberg snapshots/time-travel).
- **Observability:** Per-daemon web UI, detailed **query profiles** (per-operator timing/memory), `EXPLAIN`/`SUMMARY` plans, query history; admission control queues; metrics endpoints.
- **Upgrade story:** Rolling restarts of `impalad` daemons possible; coordinated with HMS/catalog. Day-2 burden centers on **metadata refresh** correctness, **admission control / memory tuning**, **stats freshness**, and the small-files problem — operationally heavier than a self-contained DB because you operate the whole Hadoop/lakehouse stack alongside it.
- **Maturity:** Mature — originated at Cloudera (2012), Apache top-level project since 2017, widely deployed for Hadoop-era BI. No public **Jepsen** report exists for Impala (confirmed absent from [jepsen.io/analyses](https://jepsen.io/analyses) — expected, since it delegates consistency to storage; Jepsen-style scrutiny would target [apache-kudu](apache-kudu.md)). Known failure modes: query OOM, coordinator bottleneck under high concurrency, stale metadata, slow planning on huge partition counts.

## Ecosystem & people
- **Canonical use cases:** Interactive SQL/BI on a data lake; ad-hoc exploration over Parquet/Iceberg on HDFS or object storage; dashboarding via JDBC/ODBC BI tools; low-latency queries over Kudu for near-real-time analytics.
- **Anti-patterns:** OLTP / high-rate single-row writes; multi-statement transactional workloads; tiny lookups (use Kudu/HBase directly or a real OLTP DB); huge ETL/transform jobs needing fault tolerance mid-query (use [apache-spark-sql](apache-spark-sql.md)/Hive); workloads needing it to be the system of record (it isn't — it owns no data).
- **Connectors:** JDBC/ODBC, Hue, Impala shell; integrates with [apache-hive](apache-hive.md) Metastore, [apache-kudu](apache-kudu.md), [apache-iceberg](apache-iceberg.md), [apache-spark-sql](apache-spark-sql.md) (shared tables), BI tools (Tableau/Power BI/Superset), and Cloudera's CDP platform. dbt support via community adapter.
- **Community/support:** Apache project; primary commercial backer **Cloudera** (CDP). Smaller mindshare today as the lakehouse market shifted toward [trino](trino.md)/[apache-spark-sql](apache-spark-sql.md)/serverless engines; still strong in existing Cloudera/Hadoop estates. Docs are solid; SQL learning curve low if you know Hive.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-managed OSS, or via **Cloudera Data Platform** (on-prem and cloud) as the main managed offering. Not a standalone cloud SaaS.
- **Lock-in:** Low at the format level (open Parquet/Iceberg/HMS); practical lock-in is to the Hadoop/Cloudera operational stack rather than to Impala itself.
- **Cost model:** No per-query licensing in OSS — you pay for the **compute cluster** (nodes/cores) plus the underlying storage and (optionally) Cloudera subscription. Cost scales with the always-on daemon fleet; no native pay-per-query serverless model.

## Hardware / deployment
- **Resource profile:** **Memory-bound** — joins/aggregations execute largely in RAM; insufficient memory causes spill or query failure, so RAM sizing and admission control dominate tuning. CPU-intensive too (codegen, vectorized-ish execution). The full *dataset* need not fit in RAM, but a query's working set effectively must (or it spills/fails).
- **Storage assumptions:** Performs best on columnar Parquet/ORC; works over local HDFS (data locality), NVMe, or network-attached object storage (S3/ADLS) — object-storage latency tolerated but locality lost.
- **Footprint:** **Clustered**, always-on daemon fleet. Not embedded, not single-binary, not serverless.
- **Deployment:** On-prem Hadoop, or cloud over object storage; runs in containers/k8s (Cloudera supports k8s deployments), but it expects an external HMS + storage layer to exist.

## Bottom line
Reach for Impala when you already run a Hadoop or Cloudera lakehouse and need **fast, concurrent, interactive SQL** over Parquet/Iceberg/Kudu without standing up a separate warehouse. Do **not** treat it as a database: it owns no storage, has no real multi-statement transactions, and depends entirely on the underlying store for durability and consistency. The single biggest gotcha is the **memory model** — queries that outgrow their memory budget historically fail rather than degrade gracefully, and admission control + `COMPUTE STATS` discipline are mandatory operational chores; for greenfield projects today, evaluate [trino](trino.md) and serverless lakehouse engines as alternatives.

## Sources
- [Apache Impala — official site / overview](https://impala.apache.org/)
- [Impala: A Modern, Open-Source SQL Engine for Hadoop (CIDR 2015 paper)](http://pandis.net/resources/cidr15impala.pdf)
- [Impala Transactions (insert-only ACID semantics)](https://impala.apache.org/docs/build/html/topics/impala_transactions.html)
- [KUDU_READ_MODE query option — read-committed vs snapshot](https://impala.apache.org/docs/build/html/topics/impala_kudu_read_mode.html)
- [Using Impala with Iceberg tables](https://impala.apache.org/docs/build/html/topics/impala_iceberg.html)
- [Apache Kudu transaction semantics](https://kudu.apache.org/docs/transaction_semantics.html)
- [Apache Impala — Wikipedia](https://en.wikipedia.org/wiki/Apache_Impala)
