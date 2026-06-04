---
name: Apache Druid
slug: apache-druid
rank: 82
data_model: Time-series / real-time analytics (multi-model OLAP)
license: Apache License 2.0 (permissive)
summary: Distributed columnar OLAP datastore for sub-second slice-and-dice over event/time-series data; fast reads, weak on joins and record-level mutation.
last_researched: 2026-06-04
confidence: high
---

# Apache Druid

> A distributed, columnar, time-partitioned analytics datastore built for sub-second aggregation queries over high-volume event streams — not a system of record, and deliberately bad at joins and per-row updates.

## Identity
- **Taxonomy / data model:** real-time analytics / time-series OLAP datastore. Data lives in **datasources** (table analogs) with a mandatory **primary timestamp**, plus **dimensions** (filter/group columns) and **metrics** (aggregatable measures) per the classic OLAP model ([schema model docs](https://druid.apache.org/docs/latest/ingestion/schema-model/)). Often described as multi-model because it ingests JSON/nested data and supports approximate sketches, but it is fundamentally an aggregation engine, not relational.
- **Storage model:** **columnar**, immutable, compressed **segment** files. Each datasource is partitioned by time into chunks, and each chunk into one or more segments (~few million rows each), with per-column indexes/bitmaps ([segments docs](https://druid.apache.org/docs/latest/design/segments/)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md); segments are write-once immutable files, replaced atomically rather than mutated in place.
- **Workload:** OLAP, not OLTP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Optimized for high-concurrency filter/group-by/top-N/count-distinct over time. Real-time streaming ingest plus historical query gives it a "real-time analytics" feel, but it is not HTAP — there is no transactional point-write path; it co-locates fresh streaming segments and old historical segments in the same query, which is concurrency, not OLTP+OLAP unification.

## Distribution & consistency
- **CAP under partition:** AP-leaning for **reads** — queries continue against whatever segments are currently available; the Broker picks a consistent set of segment versions at query start, so you may read a stale-but-consistent view during failures ([storage/consistency docs](https://druid.apache.org/docs/latest/design/storage/)). See [cap-pacelc](../concepts/cap-pacelc.md). There is no cross-row transactional consistency model in the relational sense.
- **PACELC:** roughly **A/EL** — favors availability under partition and low latency otherwise. Reads are eventually consistent with respect to in-flight ingestion; freshly ingested rows become visible when segments are published and handed off.
- **Default isolation & what's achievable:** **No ACID transactions across records** — Druid is explicitly not a system of record and does not offer multi-statement transactions ([Imply: ACID and Druid](https://imply.io/blog/acid-and-apache-druid/)). The only meaningful atomicity is: (1) **atomic segment replacement** (queries flip from old to new segment versions instantaneously, no torn reads) and (2) **all-or-nothing ingestion publish** for pull-based ingest. So "transactional" in Druid docs means *segment publish atomicity*, not [isolation-levels](../concepts/isolation-levels.md) guarantees. ⚠️ unverified — there is no published serializable/snapshot isolation claim to map onto, because record-level concurrent mutation is not a supported operation.
- **Replication:** segment-level. The Coordinator assigns N replicas of each segment across Historical nodes for read availability and load balancing; the durable copy of every segment lives in **deep storage** (S3/HDFS/NFS). This is replication-for-availability, not a single/multi-leader write log — see [replication-models](../concepts/replication-models.md). Streaming ingest (Kafka/Kinesis) commits stream offsets to the metadata store in the same transaction as segment metadata, giving exactly-once-style guarantees on the publish.
- **Tunable consistency?** Not in the Dynamo/Cassandra per-query sense. You tune replication factor and ingestion handoff timing, not read/write quorums.
- **Clock dependency:** depends on the event **timestamp column** for partitioning and time-range operations, but correctness does not rest on synchronized wall clocks across nodes the way TrueTime/HLC systems do. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write (mostly), with flexibility:** you define dimensions/metrics at ingestion; segments are written in that shape. Schema **auto-discovery** and nested/JSON columns are supported, so it tolerates evolving inputs better than older versions.
- **Migration/evolution:** there is **no `ALTER TABLE`**. Changing the data model means **re-ingesting / reprocessing** affected time chunks — potentially reloading large historical ranges, which is costly ([data updates docs](https://druid.apache.org/docs/latest/data-management/update/)). Schema changes across segments are handled at query time by treating missing columns as null, but type/layout changes require reindex.
- **Type system:** long, float, double, string, **arrays** (true arrays via SQL-based ingestion since Druid 28), nested/JSON columns, and **approximate sketch** columns (HLL, Theta, quantiles/T-Digest, DataSketches). No native geospatial index beyond limited spatial dimensions; vectors are not a first-class type.

## Query interface
- **Language:** **Druid SQL** (planned via Apache **Calcite**) plus a native JSON query API. Druid 28 moved toward ANSI-SQL semantics — NULL handling, strict boolean and three-valued logic on by default ([Imply: Druid 28](https://imply.io/blog/introducing-apache-druid-28-0-0/)). Not full ANSI SQL: limited join semantics, OLAP-shaped.
- **Transactions:** none at the statement level; single multi-row INSERT/REPLACE via the multi-stage query (MSQ) engine is the unit of atomic publish.
- **Native vs app-side:** group-by, top-N, timeseries, count-distinct, window functions, and **UNNEST** are native (window + UNNEST GA as of recent releases). **Joins are the weak spot:** no query-time join of two large distributed datasources — all but the base table must **fit in memory**, join condition must be equality (broadcast hash join semantics) ([joins docs](https://druid.apache.org/docs/latest/querying/joins/)). The intended pattern is to **denormalize before ingest** into flat datasources.
- **Approximation as a feature:** `APPROX_COUNT_DISTINCT`, approximate quantiles, etc. — exact computation is available but approximation is the fast path.
- **Stored procedures / UDFs:** no general stored-procedure language; extension functions and DataSketches aggregators rather than user PL/SQL.

## Scaling & topology
- **Horizontal, role-separated:** services split into Master (**Coordinator**, **Overlord**), Query (**Broker**, **Router**), and Data (**Historical**, **MiddleManager/Indexer + Peons**) servers. External deps: **deep storage**, a **metadata RDBMS** (Postgres/MySQL), and historically **ZooKeeper** for service discovery/leader election. ZooKeeper's role has shrunk: as of **Druid 31** ZooKeeper-based segment loading was removed in favor of HTTP-based loading ([Druid 31 release notes / upgrade notes](https://druid.apache.org/docs/latest/release-info/upgrade-notes/)), and a **Kubernetes discovery extension** lets clusters run with `druid.zk.service.enabled=false` (k8s API for discovery/leader election) so ZooKeeper is no longer strictly mandatory ([Kubernetes extension docs](https://druid.apache.org/docs/latest/development/extensions-core/kubernetes/)). Default/non-k8s deployments still use ZooKeeper.
- **Sharding:** automatic time-partitioning into segments, with optional secondary partitioning (hash/range/single-dim). Resharding = recompaction/reindex of segments, handled by the Coordinator's compaction; not a manual hot-resharding ordeal but reprocessing-bound.
- **Read replicas / read consistency:** Historicals serve replicated read-only segments; reads are consistent within the segment-version set the Broker selects per query.
- **Storage/compute separation:** yes — durable data lives in deep storage; Historicals cache segments on local disk for query speed and can be rebuilt entirely from deep storage after total loss. **Query-from-deep-storage** (MSQ async) lets you query cold data not loaded on Historicals. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** real-time ingest buffers in MiddleManager/Indexer; periodically persists segments and **publishes to deep storage** ([wal-and-durability](../concepts/wal-and-durability.md)). Durable copy = deep storage; before handoff, in-memory real-time data is the exposure window. Streaming ingest's offset-in-metadata-store commit bounds the **data-loss window** to un-published in-flight rows; on crash, supervisors resume from committed offsets. ⚠️ unverified — exact fsync/group-commit semantics depend on ingestion task config and the indexing engine variant.
- **Throughput/latency:** designed for sub-second aggregation at high concurrency; bitmap-indexed columnar scans + per-segment parallelism. Strong p99 for filter/group-by dashboards; **p99 degrades on heavy joins, high-cardinality exact count-distinct, or large un-rolled scans.**
- **Compaction / GC:** background **compaction** merges small/real-time segments into larger optimized ones and can re-partition or re-roll-up; runs via Coordinator. Poorly-tuned segment sizes and many tiny real-time segments are a classic source of bad tail latency.

## Operations & maturity
- **Backup/restore:** durability is the deep-storage copy plus the metadata DB; back up the **metadata store** (segment/task metadata) and rely on deep storage for segment data. No conventional PITR — recovery is reconstructing from deep storage + metadata.
- **Observability:** rich metrics emitter (StatsD/Prometheus/Kafka), query/segment metrics, native query EXPLAIN/plan via Calcite, and the Router web console for cluster state.
- **Upgrade story:** supports **rolling updates** of services ([rolling updates docs](https://druid.apache.org/docs/latest/operations/rolling-updates.html)). Day-2 burden is real: many service types, a metadata DB + deep storage (and ZooKeeper unless you run the k8s discovery extension) to operate, and constant attention to segment sizing/compaction. This operational complexity is the standard reason teams pick managed imply-polaris instead.
- **Maturity:** mature, originated at Metamarkets (2011), Apache top-level since 2018/2019, widely deployed for analytics dashboards (Netflix, Confluent, etc.). ⚠️ unverified — no public **Jepsen** report exists for Druid; given it makes no serializable cross-record claims, the usual Jepsen lens (isolation violations) largely doesn't apply.

## Ecosystem & people
- **Canonical use cases:** user-facing analytics dashboards, clickstream/ad-tech/observability/network-flow analytics, real-time operational monitoring over Kafka/Kinesis streams — high-concurrency time-sliced aggregation.
- **Anti-patterns:** system of record / OLTP; workloads needing per-row updates or deletes by key; arbitrary large-table joins; full-row retrieval / point lookups; anything requiring foreign keys, constraints, or multi-statement transactions. If your queries are join-heavy or your data is highly normalized, Druid is the wrong tool unless you denormalize upstream.
- **Connectors:** native **Kafka** and **Kinesis** streaming supervisors; batch from S3/HDFS/local; integrations with dbt (limited), BI tools (Superset, Tableau via SQL/Avatica JDBC), and Kafka-based CDC pipelines feeding ingestion.
- **Community / support:** active Apache project; commercial support and tooling from **Imply** (founded by Druid creators). Docs are good. Learning curve is steep — segment/compaction/ingestion-spec mental model is non-trivial.

## Licensing & cost
- **License:** **Apache License 2.0**, permissive ([Druid licensing](https://druid.apache.org/licensing/)) — no post-2018 relicensing rug-pull. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable OSS; managed via **imply-polaris** (Imply's cloud DBaaS built on Druid) or self-run on k8s/VMs. Lock-in risk is low at the OSS layer; Polaris adds proprietary management conveniences.
- **Cost model:** self-managed = your infrastructure (notably needs fast local disk on Historicals plus deep-storage object-store costs). At scale, cost is driven by Historical node count/local SSD to keep the hot working set queryable; Polaris is a managed/usage-based service. Cheap-at-small can invert because the always-on Historical tier and multi-service footprint have meaningful baseline cost.

## Hardware / deployment
- **Resource profile:** **memory- and disk-bound** on the query (Historical) tier — best p99 when the hot working set fits in page cache / local SSD; CPU matters for scan/aggregation. The full dataset need not fit in RAM (it lives in deep storage), but the *queried* portion should be on fast local storage.
- **Storage assumptions:** Historicals want **local NVMe/SSD**; deep storage is object store / HDFS (latency-tolerant, used for durability and cold queries, not the hot path).
- **Footprint:** **distributed/clustered only** in practice — multiple service types plus a metadata DB (and ZooKeeper, unless using the k8s discovery extension). Not embedded, not truly single-node for production (a single-box quickstart exists for dev).
- **Deployment:** on-prem or cloud VMs/k8s (StatefulSets for data tiers); SaaS via Imply Polaris. Operationally heavier on k8s than a single-binary engine.

## Bottom line
Reach for Druid when you need **sub-second, high-concurrency aggregation over large time-stamped event data** — dashboards, real-time monitoring, clickstream/ad-tech analytics fed from Kafka. Do **not** use it as a primary database, for transactional or per-row-update workloads, or for join-heavy normalized schemas: the model assumes you **denormalize before ingest** and treat data as immutable, time-partitioned segments. The single biggest gotcha is the **operational/data-model rigidity** — no real joins, no `ALTER`/record updates (changes mean re-ingesting time chunks), and a many-service cluster (metadata DB + deep storage, plus ZooKeeper unless you run the k8s discovery extension) that is heavy to run well.

## Sources
- [Druid architecture](https://druid.apache.org/docs/latest/design/architecture/)
- [Storage & consistency overview](https://druid.apache.org/docs/latest/design/storage/)
- [Segments](https://druid.apache.org/docs/latest/design/segments/)
- [Schema model](https://druid.apache.org/docs/latest/ingestion/schema-model/)
- [Joins](https://druid.apache.org/docs/latest/querying/joins/)
- [Data updates](https://druid.apache.org/docs/latest/data-management/update/)
- [Rolling updates](https://druid.apache.org/docs/latest/operations/rolling-updates.html)
- [Kubernetes discovery extension (ZooKeeper-less)](https://druid.apache.org/docs/latest/development/extensions-core/kubernetes/)
- [Upgrade notes (ZooKeeper segment loading removed in 31)](https://druid.apache.org/docs/latest/release-info/upgrade-notes/)
- [Licensing (Apache 2.0)](https://druid.apache.org/licensing/)
- [Imply: ACID and Apache Druid](https://imply.io/blog/acid-and-apache-druid/)
- [Imply: Introducing Druid 28 (ANSI SQL, arrays)](https://imply.io/blog/introducing-apache-druid-28-0-0/)
