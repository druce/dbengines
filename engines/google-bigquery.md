---
name: Google BigQuery
slug: google-bigquery
rank: 19
data_model: Relational (cloud data warehouse)
license: Proprietary, managed-only (Google Cloud)
summary: Serverless, columnar, separated-storage-and-compute cloud data warehouse; the OLAP default on GCP, billed by bytes scanned or by slots.
last_researched: 2026-06-04
confidence: high
---

# Google BigQuery

> Fully managed, serverless OLAP data warehouse that scans columnar data on Colossus with on-demand Dremel compute — no clusters to size, but cost is driven by bytes scanned, and it is the wrong tool for OLTP or low-latency point lookups.

## Identity
- **Taxonomy / data model:** Relational data warehouse with ANSI SQL ("GoogleSQL"); supports nested/repeated fields (STRUCT/ARRAY) for semi-structured data, native JSON, and geospatial. Multi-model adjuncts: BigQuery ML (in-database models), vector search ([vector-search-ann](../concepts/vector-search-ann.md)), and BigLake/external tables over object storage.
- **Storage model:** Column-store. Proprietary [columnar-storage](../concepts/columnar-storage.md) format **Capacitor** (replaced ColumnIO in 2016), stored on Google's **Colossus** distributed filesystem; not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — analytic columnar files, not a mutable index tree. Compute (Dremel) and storage (Colossus) are fully separated. See [storage-compute-separation](../concepts/storage-compute-separation.md).
- **Workload:** OLAP / analytics. Not HTAP in the transactional sense. The "real-time analytics" story comes from the **Storage Write API / streaming inserts** plus BigQuery's ability to query recently-streamed rows; it is *not* a transactional system and should not back an application's writes. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Managed service abstracts this away; effectively CP-leaning for committed data (a query returns a consistent snapshot or fails). Single-region or multi-region storage with Google-managed replication. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Not a tunable distributed DB in the Dynamo sense; the user does not choose consistency-vs-latency per query. Reads see a consistent snapshot as of query/transaction start.
- **Default isolation & what's achievable:** **Snapshot isolation** for multi-statement transactions; statements see a consistent snapshot as of the transaction start, support read-your-own-writes, and do not observe other concurrent transactions' changes ([docs](https://cloud.google.com/bigquery/docs/transactions)). ACID is honored for transactions, but the engine is built around bulk DML and snapshot reads, not high-concurrency row contention — if a transaction mutates rows in a table, other transactions/DML that mutate the same table cannot run concurrently and **conflicting transactions are cancelled** (not auto-retried), per the [docs](https://cloud.google.com/bigquery/docs/transactions). Serializable is **not** the model. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md) (BigQuery keeps a mutation history / time-travel window enabling snapshots).
- **Replication:** Google-managed, opaque to the user; durability and replication handled by Colossus. No user-facing leader/follower or quorum knobs. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels. Caveat: reads from **external/federated sources** (e.g. external tables, BigLake) are **not** guaranteed consistent within a transaction if the underlying source changes ([docs](https://cloud.google.com/bigquery/docs/transactions)).
- **Clock dependency:** No user-visible clock-correctness dependency (no TrueTime exposure as in [google-cloud-spanner](google-cloud-spanner.md)). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, with flexibility.** Tables are typed; schema-on-read is available via external tables and the JSON type / `JSON_*` functions for semi-structured data.
- **Migration/evolution:** Online, non-locking schema changes for common cases — add columns, relax modes (REQUIRED→NULLABLE) without rewriting; column drop/rename and type changes supported via DDL. No table-level lock to add a column (it is a metadata operation, not a full rewrite).
- **Type system:** Scalars plus ARRAY, STRUCT, native JSON, NUMERIC/BIGNUMERIC (fixed precision), GEOGRAPHY (geospatial), INTERVAL, RANGE, and vector embeddings (ARRAY<FLOAT64>) with `VECTOR_SEARCH` / vector indexes.

## Query interface
- **Language:** ANSI-compliant SQL ("GoogleSQL"); legacy SQL deprecated. Rich analytics: window functions, approximate aggregates (HLL++), geospatial, `CREATE MODEL` (BigQuery ML), `ML.PREDICT`, `VECTOR_SEARCH`.
- **Transactions:** Multi-statement ACID transactions within a single query or across queries in a **session**, with `BEGIN/COMMIT/ROLLBACK`, snapshot isolation ([docs](https://cloud.google.com/bigquery/docs/transactions)). Designed for bulk DML, not OLTP.
- **Native vs app-side:** Joins, aggregations, window functions all native and distributed. Secondary indexes are limited — **search indexes** (for text/`SEARCH`) and **vector indexes** exist, but there is no general-purpose B-tree secondary index; performance comes from partitioning and clustering, not point indexes.
- **Stored procedures / UDFs:** SQL stored procedures and scripting; UDFs in SQL and **JavaScript**; remote functions backed by Cloud Functions/Cloud Run; Apache Spark stored procedures.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal and serverless — the user does not provision nodes. Concurrency/compute is governed by **slots** (units of CPU/RAM); on-demand allocates them dynamically, editions reserve/autoscale them.
- **Sharding/partitioning:** [sharding-partitioning](../concepts/sharding-partitioning.md) — tables can be **partitioned** (by ingestion time, a DATE/TIMESTAMP column, or integer range) and **clustered** (up to 4 columns) to prune bytes scanned. No manual resharding; partitioning is declarative and pruning is automatic. Choosing partition/cluster keys well is the primary performance/cost lever.
- **Read replicas / read consistency:** N/A in the traditional sense — there is one logical copy; reads are consistent snapshots. Cross-region replication of datasets is a managed feature.
- **Storage/compute separation:** Yes, foundational — Colossus storage scales independently of Dremel compute over Google's Jupiter network. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path / durability:** Loads and the Storage Write API commit to Colossus, which provides Google's durability/replication; there is no user-managed WAL or fsync knob and effectively no user-visible data-loss window for committed writes. See [wal-and-durability](../concepts/wal-and-durability.md). Streaming has historically had a buffer where very recent rows are queryable before being fully optimized into columnar storage.
- **Throughput/latency profile:** Built for large scans and high aggregate throughput, not low latency. Per-query overhead means **even trivial queries take on the order of a second or more** — point lookups are slow and expensive relative to an OLTP DB. p99 query latency is dominated by available slots and queueing: under on-demand or a too-small reservation, queries queue and tail latency spikes. BI Engine (in-memory cache) and materialized views accelerate repeated/dashboards.
- **Compaction / GC:** No user-managed vacuum. BigQuery transparently optimizes Capacitor storage in the background; time-travel (default 7 days, configurable 2–7) retains prior versions for snapshot/restore.

## Operations & maturity
- **Backup/restore, PITR:** **Time travel** (point-in-time within the 2–7 day window) and **table snapshots** / clones; dataset-level cross-region copy for DR. No traditional backup files to manage.
- **Observability:** `INFORMATION_SCHEMA` views (jobs, reservations, storage), per-query execution plan/timeline in console, bytes-scanned and slot-time metrics, Cloud Monitoring/Audit Logs integration.
- **Upgrade story:** Fully managed; no version upgrades or downtime for the user — Google rolls out continuously.
- **Maturity:** Very mature (public since 2011, built on Google's internal **Dremel**; Dremel/Capacitor are published research). No Jepsen report exists — ⚠️ unverified — Jepsen has not, to my knowledge, tested BigQuery (it is a closed managed service, not the kind of self-hostable distributed DB Jepsen targets). Known failure modes are operational/cost rather than correctness: runaway bytes-scanned bills, slot queueing under-provisioning, and quota limits on streaming and concurrent queries.

## Ecosystem & people
- **Canonical use cases:** Large-scale ad-hoc analytics, BI/dashboarding over big datasets, ELT data warehousing, log/event analytics, ML feature pipelines and in-warehouse ML, geospatial analytics. **Anti-patterns:** OLTP / application backing store; high-frequency single-row reads/writes; sub-100ms latency needs; small-data workloads where a single Postgres node would be cheaper and faster; workloads with unbounded ad-hoc `SELECT *` scans (cost explosion).
- **Drivers/connectors:** JDBC/ODBC, client libraries (Python, Java, Go, etc.), Storage Read/Write APIs, Datastream and Pub/Sub for ingestion, Dataflow/Spark connectors, **dbt** (first-class adapter), Looker/Looker Studio/Tableau/Power BI, Kafka via connectors. Federation to Cloud Storage, Bigtable, Spanner, Cloud SQL.
- **Community/support:** Large user base, strong Google docs, GCP commercial support. Learning curve is low for SQL users; the real skill is cost control (partition/cluster design, avoiding full scans).

## Licensing & cost
- **License/flavor:** Proprietary, managed-only — no self-hosted or open-source edition. Not relevant to the [license-taxonomy](../concepts/license-taxonomy.md) OSS axis; the lock-in is the managed service and proprietary SQL/ML extensions.
- **Self-managed vs managed-only:** Managed-only on Google Cloud.
- **Cost model — two axes:**
  - **Compute:** **On-demand** at ~$6.25 per TiB scanned ([pricing](https://cloud.google.com/bigquery/pricing)) — you pay for bytes a query reads, so column/partition pruning directly cuts cost; or **capacity (slots)** via editions: **Standard** (~$0.04/slot-hour, no commitments), **Enterprise**, **Enterprise Plus**, with 1- and 3-year commitments giving ~20%/40% discounts and slot **autoscaling** ([Google Cloud blog](https://cloud.google.com/blog/products/data-analytics/introducing-new-bigquery-pricing-editions)).
  - **Storage:** Active vs long-term (auto-discounted after 90 days untouched), with compressed (physical-byte) storage billing optional.
  - **At scale:** On-demand is cheap-at-small but a single bad `SELECT *` can scan terabytes; large/steady workloads usually move to slot reservations for predictable cost. The classic gotcha is surprise bills from full-table scans.

## Hardware / deployment
- **Resource profile:** Irrelevant to the user — serverless; Google manages CPU/RAM/disk. The user's only "sizing" knob is slots (compute) and partition/cluster design (bytes scanned). Working set need not fit in RAM (it scans Colossus), though BI Engine caches hot data in memory for speed.
- **Storage assumptions:** Colossus (Google's distributed filesystem) — network-attached, separated from compute by the Jupiter fabric. No user disk choices.
- **Footprint:** Cloud SaaS only; no embedded/single-node mode.
- **Deployment:** GCP regions/multi-regions; no on-prem, no k8s/StatefulSet — it is a Google-hosted API. BigQuery Omni offers querying data in AWS/Azure via Anthos, but the control plane remains Google.

## Bottom line
Reach for BigQuery when you want a zero-ops analytics warehouse on GCP that scales to petabytes with plain SQL and pay-per-scan economics, and when your access pattern is large scans, BI, and ELT. Do **not** use it as an application database or for low-latency point lookups — per-query latency is seconds and there are no general secondary indexes. The single biggest gotcha is cost: bytes-scanned billing punishes `SELECT *` and unpartitioned tables, so partition/cluster design and reservation choice are the real engineering work.

## Sources
- [BigQuery multi-statement transactions (official docs)](https://cloud.google.com/bigquery/docs/transactions)
- [BigQuery pricing (official)](https://cloud.google.com/bigquery/pricing)
- [Introducing new BigQuery pricing editions (Google Cloud Blog)](https://cloud.google.com/blog/products/data-analytics/introducing-new-bigquery-pricing-editions)
- [Understand BigQuery editions (official docs)](https://docs.cloud.google.com/bigquery/docs/editions-intro)
- [BigQuery architecture overview (storage/compute separation, Dremel/Capacitor/Colossus/Jupiter)](https://panoply.io/data-warehouse-guide/bigquery-architecture/)
