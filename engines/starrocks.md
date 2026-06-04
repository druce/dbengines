---
name: StarRocks
slug: starrocks
rank: 139
data_model: Relational (columnar MPP OLAP / lakehouse query engine)
license: Apache License 2.0 (permissive; relicensed from Elastic License in Dec 2022)
summary: Vectorized MPP columnar warehouse for sub-second real-time analytics, with a primary-key table for upserts and federated querying of Iceberg/Hudi/Hive/Delta.
last_researched: 2026-06-04
confidence: high
---

# StarRocks

> A fully-vectorized, MPP columnar analytics database for sub-second real-time and customer-facing OLAP — fast on its own storage and as a query engine over open-table lakehouses, but with a deliberately thin transaction model (READ COMMITTED, no write-conflict checks).

## When to use

**Use StarRocks if:**
- ✅ You need sub-second, high-concurrency analytics — real-time dashboards or customer-facing/embedded analytics
- ✅ You want fast SQL directly over Iceberg/Hudi/Hive/Delta lakehouses via one vectorized MPP engine instead of stitching several together
- ✅ You want MySQL-protocol compatibility (BI tools, MySQL drivers) and a cost-based optimizer that runs full TPC-DS
- ✅ Storage/compute separation (shared-data mode over S3/GCS/Azure Blob) fits your cloud cost model

**Avoid StarRocks if:**
- ❌ You need a transactional system of record or high-rate single-row OLTP writes
- ❌ You require serializable isolation or write-conflict detection — it is READ COMMITTED with NO write-conflict checks, so concurrent writers to the same table can both commit
- ❌ You want a tiny single-node deployment (FE+BE/CN cluster overhead; multi-node for HA)
- ❌ You can't invest in tuning (bucket/partition counts, primary-key index memory, compaction under heavy upserts) — get these wrong and p99 suffers

## Identity
- **Taxonomy / data model:** relational, SQL, analytical (OLAP). Originated in 2020 as a commercialized fork of [apache-doris](apache-doris.md) and since heavily rewritten ([CelerData / Linux Foundation announcement](https://celerdata.com/blog/celerdata-contributes-starrocks-project-to-the-linux-foundation)). Also serves as a lakehouse query engine over external tables.
- **Storage model:** column-store. On-disk data is organized into segments with per-column encoding/compression, sorted by key, plus prefix indexes, zone maps, bitmap and bloom-filter indexes. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md)-style in the classic sense; the **primary-key table** uses a delete-and-insert (DelVector + primary-key index) upsert pattern ([primary-key table docs](https://docs.starrocks.io/docs/table_design/table_types/primary_key_table/)) rather than the merge-on-read of aggregate/unique tables.
- **Workload:** OLAP, with strong real-time ingestion. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). It is **not HTAP** — it is an analytics engine, not an OLTP system; treat any "real-time" claim as fast ingest + fast scan, not transactional point-write workloads.

## Distribution & consistency
- **CAP under partition:** CP-leaning for metadata. Frontend (FE) nodes keep a full in-memory metadata copy in BDB JE and elect a leader; a metadata write commits only after replication to a majority of follower FEs ([architecture docs](https://docs.starrocks.io/docs/introduction/Architecture/)) — i.e. a Raft-like majority-quorum metadata layer. See [cap-pacelc](../concepts/cap-pacelc.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **PACELC:** ⚠️ unverified — no formal PACELC statement published. In practice: under partition the metadata layer favors consistency (loses minority FEs); else, query reads favor latency (this is an analytics engine, not a strongly-consistent transactional store).
- **Default isolation & what's achievable:** StarRocks supports **only limited READ COMMITTED** for SQL transactions, and **does not perform write-conflict checks** — two concurrent transactions writing the same table can both commit, with visibility decided by COMMIT order ([SQL transaction docs](https://docs.starrocks.io/docs/loading/SQL_transaction/)). Each load/ingest job is itself an atomic ACID transaction (all-or-nothing) ([primary-key table docs](https://docs.starrocks.io/docs/table_design/table_types/primary_key_table/)), but this is per-load atomicity, not serializable multi-statement isolation. Treat the "ACID" claim as **per-load atomicity + RC**, not snapshot/serializable. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** shared-nothing mode stores multiple data replicas (default 3) across BEs for reliability; shared-data mode pushes durability to object storage and keeps CNs stateless. FE metadata uses leader + follower replication (majority quorum). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels in the Dynamo/Cassandra sense.
- **Clock dependency:** ⚠️ unverified — no documented dependence on synchronized clocks for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write** for native tables (typed columns, defined keys/partitions/buckets). Schema-on-read for external lakehouse tables (Iceberg/Hudi/Hive/Delta).
- **Migration/evolution:** supports ALTER for add/drop column and lightweight schema changes; column changes can trigger background data transformation. ⚠️ unverified — exact locking/online-DDL behavior per operation; some schema changes run as async background jobs.
- **Type system:** standard SQL scalar types plus ARRAY, MAP, STRUCT, JSON, BITMAP (for distinct counts / hyperloglog-style), HLL, and DATE/DATETIME. Vector/ANN support has been added in recent releases (vector index). ⚠️ unverified — vector-index maturity. See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** SQL, **MySQL wire-protocol compatible** — connect with MySQL clients/drivers and BI tools. CBO is a Cascades-style cost-based optimizer that runs all 99 TPC-DS queries ([features docs](https://docs.starrocks.io/docs/introduction/Features/)).
- **Transactions:** explicit SQL transactions exist but are limited (RC, no conflict checks, see above). UPDATE/DELETE inside transactions are supported only in shared-data clusters from v4.0 onward; primary-key values cannot be updated ([SQL transaction docs](https://docs.starrocks.io/docs/loading/SQL_transaction/)). Most workloads rely on load-job atomicity, not interactive multi-statement transactions.
- **Native vs app-side:** native distributed joins (including broadcast/shuffle/colocate joins), aggregations, window functions, CTEs, lateral joins. Materialized views can transparently rewrite queries ([features docs](https://docs.starrocks.io/docs/introduction/Features/)).
- **Stored procedures / UDFs:** Java UDFs supported; ⚠️ unverified — breadth of stored-procedure support (limited compared to OLTP RDBMS).

## Scaling & topology
- **Vertical and horizontal.** Horizontal scaling by adding BEs (shared-nothing) or CNs (shared-data).
- **Sharding/partitioning:** tables are range/expression **partitioned** and then **bucketed** (hash distribution) into tablets; tablets are the unit of replication and parallelism. Expression/auto-partitioning available in newer versions. Resharding/bucket changes can require data redistribution; choosing bucket count is a known tuning chore.
- **Read replicas:** data replicas (shared-nothing) serve reads and provide HA; reads see committed versions. No async-stale read-replica tier in the OLTP sense.
- **Storage/compute separation:** yes — **shared-data** mode (v3.0+, FE + stateless CN) stores data in S3/GCS/Azure Blob/HDFS/MinIO and uses a memory→local-disk→object-store cache hierarchy; CNs scale in/out in seconds without data rebalancing ([storage-compute blog](https://www.starrocks.io/blog/separation-of-storage-and-compute-an-architecture-that-cuts-costs-and-enhances-efficiency)). Cold queries pay the object-store fetch; warm-cache performance is claimed comparable to shared-nothing. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** ingest is batched into load transactions; each load is atomic. Shared-nothing durability comes from multi-replica writes across BEs; shared-data durability comes from object storage. ⚠️ unverified — exact fsync/group-commit and crash data-loss window; data-loss exposure is mainly the in-flight uncommitted load. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** designed for sub-second, high-concurrency analytical queries; fully vectorized execution claims 3–10x operator speedups ([features docs](https://docs.starrocks.io/docs/introduction/Features/)). p99 tail behavior depends heavily on bucket/partition design, cache warmth (shared-data), and compaction load. ⚠️ unverified — independent p99 benchmarks.
- **Compaction / GC:** background compaction merges segments and applies deletes; the primary-key table's persistent index and DelVector cleanup add background work. Compaction pressure under heavy upsert/real-time ingest is the main p99 risk.

## Operations & maturity
- **Backup/restore:** BACKUP/RESTORE to remote storage (e.g. S3/HDFS) and snapshots; shared-data effectively delegates durability to object storage. ⚠️ unverified — PITR granularity.
- **Observability:** EXPLAIN / EXPLAIN ANALYZE query plans, profiles, audit/slow-query log plugin, metrics endpoints (Prometheus-compatible).
- **Upgrade story:** rolling upgrades of FE/BE/CN are supported; FE metadata compatibility constrains skip-version upgrades. Day-2 burden centers on bucket/partition tuning, compaction, and memory sizing for primary-key indexes.
- **Maturity:** production use at scale (e.g. Airbnb, Lenovo, Trip.com per vendor); fast-moving releases (3.x/4.x). **No public Jepsen report exists** for StarRocks as of this writing — given RC-only isolation and no write-conflict checks, do not assume strong transactional guarantees. Known sharp edges: memory pressure from in-memory/persistent primary-key indexes, compaction lag under high-frequency upserts.

## Ecosystem & people
- **Canonical use cases:** real-time dashboards, customer-facing/embedded analytics with high concurrency, ad-hoc OLAP directly on Iceberg/Hudi/Hive/Delta lakehouses, and consolidating multiple query engines onto one. Strong fit replacing [apache-doris](apache-doris.md), [clickhouse](clickhouse.md), or Druid-style real-time OLAP stacks.
- **Anti-patterns:** OLTP / high-rate single-row transactional writes; workloads needing serializable isolation or write-conflict detection; tiny single-node deployments (operational overhead of FE+BE clusters); as a system-of-record primary database.
- **Connectors:** MySQL protocol (BI tools, MySQL drivers), Flink/Spark connectors, Kafka routine load, [apache-flink](apache-flink.md)/[apache-spark-sql](apache-spark-sql.md) CDC ingestion, dbt adapter, plus external catalogs for Iceberg/Hudi/Hive/Delta and JDBC.
- **Community/support:** Linux Foundation project with active OSS community; commercial support and managed cloud via CelerData. Docs are reasonably thorough but version-fragmented.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive). Notably **relicensed from the Elastic License 2.0 to Apache 2.0 in December 2022** ([StarRocks is now under Apache License 2.0](https://www.starrocks.io/blog/starrocks-is-now-under-apache-license-2.0), Dec 6 2022), then contributed to the Linux Foundation in 2023 ([CelerData / Linux Foundation announcement](https://celerdata.com/blog/celerdata-contributes-starrocks-project-to-the-linux-foundation)) — a rare *toward*-permissive move against the post-2018 source-available trend. (StarRocks began in 2020 as DorisDB, a commercial fork of [apache-doris](apache-doris.md); the company renamed to CelerData in Aug 2022.) See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable (Apache 2.0); CelerData offers managed/BYOC cloud. Lock-in risk is low for the engine; managed-service features and MySQL-dialect specifics are the soft lock-in.
- **Cost model:** self-managed = your infrastructure (compute + object storage in shared-data). Shared-data decouples cheap object storage from elastic compute, which improves cost at scale vs always-on shared-nothing BE clusters. Managed pricing is vendor-defined.

## Hardware / deployment
- **Resource profile:** CPU-bound (vectorized scan/aggregation) and memory-sensitive; primary-key tables in particular want enough RAM for the PK index (persistent-index mode mitigates by keeping most of it on disk). Working set need not all fit in RAM, but hot data should.
- **Storage assumptions:** local NVMe/SSD strongly preferred for BE (shared-nothing) and for the CN cache (shared-data); shared-data tolerates network/object storage for cold data via the cache hierarchy.
- **Footprint:** clustered (FE + BE, or FE + CN). Not embedded, not single-process. Minimum sensible deployment is multi-node for HA.
- **Deployment:** on-prem or cloud; container/Kubernetes operator available; shared-data + object storage is the natural cloud-native deployment.

## Bottom line
Reach for StarRocks when you need sub-second, high-concurrency analytics — real-time dashboards, customer-facing analytics, or fast SQL directly over an Iceberg/Hudi lakehouse — and want one vectorized MPP engine instead of stitching together several. Do not use it as a transactional system of record: its transaction model is deliberately thin (READ COMMITTED, **no write-conflict checks — concurrent writers to the same table can both commit**), so correctness for concurrent mutations is your responsibility, and there is no Jepsen report to lean on. The biggest operational gotcha is tuning (bucket/partition counts, primary-key index memory, compaction under heavy upserts) — get those wrong and your p99 suffers.

## Sources
- [StarRocks architecture docs](https://docs.starrocks.io/docs/introduction/Architecture/)
- [StarRocks features docs](https://docs.starrocks.io/docs/introduction/Features/)
- [Primary Key table docs](https://docs.starrocks.io/docs/table_design/table_types/primary_key_table/)
- [SQL Transaction docs (isolation = limited READ COMMITTED, no write-conflict checks)](https://docs.starrocks.io/docs/loading/SQL_transaction/)
- [Separation of storage and compute (shared-data) blog](https://www.starrocks.io/blog/separation-of-storage-and-compute-an-architecture-that-cuts-costs-and-enhances-efficiency)
- [StarRocks is now under Apache License 2.0 (Dec 6 2022; relicensed from Elastic License 2.0)](https://www.starrocks.io/blog/starrocks-is-now-under-apache-license-2.0)
- [CelerData contributes StarRocks to the Linux Foundation (license history)](https://celerdata.com/blog/celerdata-contributes-starrocks-project-to-the-linux-foundation)
- [GitHub: StarRocks/starrocks](https://github.com/StarRocks/starrocks)
