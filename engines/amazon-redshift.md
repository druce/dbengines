---
name: Amazon Redshift
slug: amazon-redshift
rank: 37
data_model: Relational (cloud data warehouse)
license: Proprietary / managed-only (AWS)
summary: AWS's columnar MPP cloud data warehouse; PostgreSQL-flavored SQL for OLAP, with RA3 storage/compute separation and a serverless mode. Default isolation is now SNAPSHOT (provisioned and serverless).
last_researched: 2026-06-04
confidence: high
---

# Amazon Redshift

> AWS's managed, columnar, massively-parallel (MPP) relational data warehouse for OLAP — Postgres-dialect SQL with decoupled storage/compute (RA3) and a pay-per-RPU serverless option; great for analytics over large fact tables, wrong for high-concurrency OLTP.

## Identity
- **Taxonomy / data model:** Relational, SQL data warehouse. Forked long ago from PostgreSQL 8.0.2 wire protocol/syntax (ParAccel lineage); not a row of modern Postgres internally.
- **Storage model:** Columnar (column-store), compressed in 1 MB blocks with per-column encodings; not B-tree or [lsm-vs-btree](../concepts/lsm-vs-btree.md). Uses **zone maps** (in-memory per-block min/max metadata) to skip blocks during scans ([RA3/managed-storage docs](https://docs.aws.amazon.com/whitepapers/latest/data-warehousing-on-aws/amazon-redshift-deep-dive.html)). RA3 nodes use **Redshift Managed Storage (RMS)**: hot blocks cached on local SSD, cold blocks tiered to S3 ([RA3 features](https://aws.amazon.com/redshift/features/ra3/)).
- **Workload:** OLAP / analytics. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP itself; AWS positions zero-ETL (Aurora/RDS → Redshift) as the way to get near-real-time operational data in for analytics, which is replication, not in-place HTAP.

## Distribution & consistency
- **CAP under partition:** Within a single cluster it is effectively CP/single-system — a leader node coordinates; it is not a partition-tolerant quorum system. See [cap-pacelc](../concepts/cap-pacelc.md). (Cross-region/cross-cluster data sharing and snapshots are separate replication mechanisms.)
- **PACELC:** Not a multi-master distributed DB in the Dynamo sense; the relevant tradeoff is scan throughput vs. concurrency, not latency-vs-consistency under partition.
- **Default isolation:** **SNAPSHOT ISOLATION** is now the default for *both* Redshift Serverless and newly created/restored provisioned clusters. AWS made SNAPSHOT the default for new provisioned clusters and restores on **2024-05-22** (existing clusters keep their prior level unless changed; older clusters historically defaulted to SERIALIZABLE) ([isolation-levels docs](https://docs.aws.amazon.com/redshift/latest/dg/c_serial_isolation.html), [snapshot-default announcement (May 2024)](https://aws.amazon.com/about-aws/whats-new/2024/05/amazon-redshift-snapshot-isolation-provisioned-clusters/)). Both SNAPSHOT and SERIALIZABLE are "serializable isolation levels" in AWS's wording, but SNAPSHOT permits write-skew anomalies and allows higher write concurrency on different rows; SERIALIZABLE aborts transactions whose result can't map to a serial order — the infamous "1023 serializable isolation violation" error under concurrent writes to the same tables. Snapshot isolation was added in 2022 ([snapshot isolation launch](https://aws.amazon.com/about-aws/whats-new/2022/05/amazon-redshift-snapshot-isolation-level-support-concurrent-transactions/)). Isolation level is set per database via `CREATE`/`ALTER DATABASE`. Uses [mvcc](../concepts/mvcc.md) (snapshots taken at first qualifying statement). See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-cluster with one leader + N compute nodes; data is mirrored across compute nodes within the cluster. Cross-region snapshots and **data sharing** (read access to another cluster's RMS data) provide replication/fan-out. **Multi-AZ** (active/active across two AZs, single endpoint, 99.99% SLA, RTO in tens of seconds) is supported on **provisioned RA3 (and RG) clusters only** — not a configurable feature on Serverless, which handles AZ failover automatically ([Multi-AZ docs](https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-multi-az.html)); historically Redshift was single-AZ. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels. You choose the isolation level at the session/cluster level.
- **Clock dependency:** No TrueTime/HLC correctness dependency. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid relational schema for native tables. **Schema-on-read** for external tables via Spectrum (data in S3) and federated queries.
- **Migration/evolution:** `ALTER TABLE` supports many online operations (add/drop column, rename); some changes (e.g. altering certain column types, sort/dist key changes) historically required recreate-and-reload, though more in-place ALTERs have been added over time. ⚠️ unverified — exact set of fully-online ALTERs varies by release.
- **Type system:** Standard SQL types plus `SUPER` (semi-structured JSON/Ion, queried with PartiQL), `VARBYTE`, `GEOMETRY`/`GEOGRAPHY` (spatial), `HLLSKETCH`. Vector/embedding storage is not a first-class native type (no native ANN index — see anti-patterns). See [full-text-search](../concepts/full-text-search.md) / [vector-search-ann](../concepts/vector-search-ann.md) as concepts Redshift does *not* natively serve.

## Query interface
- **Language:** SQL, PostgreSQL-derived dialect (Postgres 8.0.2 era) plus Redshift extensions; PartiQL for `SUPER`. Standard JDBC/ODBC and a Data API (HTTP).
- **Transactions:** Full multi-statement ACID within a cluster, but tuned for bulk DML (COPY/UPDATE/DELETE), not many small concurrent transactions.
- **Native vs app-side:** Native joins, aggregations, window functions, CTEs, materialized views (with auto-refresh and auto-query-rewrite). Has no traditional secondary indexes — performance comes from **sort keys** (zone-map pruning) and **distribution styles** (KEY/EVEN/ALL/AUTO) that control data colocation for joins.
- **Stored procedures / UDFs:** Stored procedures in **PL/pgSQL**; UDFs in SQL, **Python**, or **Lambda**; ML inference via Redshift ML (SageMaker-backed).

## Scaling & topology
- **Vertical vs horizontal:** Horizontal MPP — add compute nodes; RA3 lets you scale compute and storage independently. Data partitioned across node **slices**; choosing a bad distribution key causes **data skew** and broadcast/redistribution during joins, the classic tuning pain.
- **Sharding/resharding:** Resize is elastic (fast, limited node-count changes) or classic (full reload, slower). Distribution-key changes can force data movement.
- **Read replicas / read consistency:** No conventional read replicas; **Concurrency Scaling** transparently spins up transient read clusters (and write queries) during spikes, billed per-second beyond accrued free credits ([concurrency scaling docs](https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html)). **Data sharing** exposes a producer cluster's data to consumer clusters read-only with transactional consistency.
- **Storage/compute separation:** Yes on RA3 via RMS (S3-backed managed storage); serverless takes this further. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Durability via Redshift Managed Storage continuously backing data to S3; clusters take automated **incremental snapshots** roughly every 8 hours or per ~5 GB/node of change ([snapshots docs](https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html)). Bulk load via `COPY` from S3 is the standard path; row-by-row `INSERT` is slow and discouraged. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Optimized for scan-heavy analytical queries over large tables; excellent aggregate throughput, poor for point lookups and high small-query concurrency. p99 tail is dominated by queue waits under concurrency (mitigated by WLM/auto-WLM and Concurrency Scaling) and by skew/redistribution on badly distributed joins.
- **Compaction / vacuum / GC:** Deletes/updates are logical (tombstones) until **VACUUM** reclaims space and re-sorts; Redshift now runs **auto-vacuum, auto-analyze, and auto-sort** in the background. Unsorted/unvacuumed tables degrade zone-map pruning and inflate storage. [columnar-storage](../concepts/columnar-storage.md)

## Operations & maturity
- **Backup/restore, PITR:** Automated + manual snapshots to S3; cross-region snapshot copy for DR; restore to a new cluster (and table-level restore). Serverless uses recovery points + snapshots.
- **Observability:** `EXPLAIN` plans, system tables/views (STL/STV/SVL, `SYS_*` monitoring views), Performance/Query monitoring in console + CloudWatch, slow-query and WLM queue insight.
- **Upgrade story:** Fully managed — AWS applies maintenance during a configurable window; serverless removes version/patch management entirely. Day-2 burden historically centered on distribution/sort-key tuning, VACUUM, and WLM, much of which auto-tuning ("Auto" everything) has reduced.
- **Maturity:** GA since 2013, very widely deployed, large track record. No public Jepsen report (single-system architecture makes the classic distributed-Jepsen scope less applicable). Known failure modes: serializable-isolation aborts under concurrent writers, data skew, runaway VACUUM, and queue saturation. Architecture documented in the [Redshift Re-invented (SIGMOD 2022) paper](https://assets.amazon.science/4b/37/223ac61e450898244a31bed53734/amazon-redshift-re-invented.pdf).

## Ecosystem & people
- **Canonical use cases:** Enterprise BI/reporting, large-scale aggregations, data-warehouse consolidation, dashboards over big fact tables, S3 data-lake querying via Spectrum, zero-ETL analytics on Aurora/RDS data.
- **Anti-patterns:** OLTP, high-concurrency small transactions, frequent single-row writes/updates, sub-millisecond point lookups, primary key uniqueness enforcement (constraints are informational/not enforced — a real gotcha), and as a vector database for ANN search.
- **Connectors:** JDBC/ODBC/Python (redshift_connector), Data API, deep AWS integration (Glue, Kinesis/Firehose streaming ingestion, Lambda, SageMaker, QuickSight); dbt, Airbyte, Fivetran, Kafka, and most BI tools (Tableau, Looker, Power BI) support it.
- **Community/support:** Backed by AWS support; large user base and documentation; competes with [snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [databricks](databricks.md), and [clickhouse](clickhouse.md).

## Licensing & cost
- **License:** Proprietary, **managed-only** AWS service — no self-hosting. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Lock-in:** Moderate-to-high — Postgres-ish SQL eases portability, but Spectrum, RMS, data sharing, zero-ETL, and AWS-native integrations are sticky.
- **Cost model:** Provisioned = per-node-hour (on-demand or reserved) + RMS per-GB-month for RA3; Serverless = per **RPU-hour** (8 RPU minimum, scales with workload), with Concurrency Scaling and Spectrum included. Spectrum on provisioned is billed per-TB scanned. Cheap-at-idle is the serverless story; provisioned reserved instances win at steady high utilization. ⚠️ unverified — specific list prices change; check [Redshift pricing](https://aws.amazon.com/redshift/pricing/).

## Hardware / deployment
- **Resource profile:** Disk/IO- and memory-bound for scans; CPU-bound for compression/decompression and heavy aggregation. Working set does not need to fit in RAM (RMS tiers to S3), but hot data on local SSD drives performance.
- **Storage assumptions:** Local NVMe SSD cache (RA3, Nitro-based instances) over S3-backed managed storage.
- **Footprint:** Clustered managed service (leader + compute nodes) or serverless. Not embedded, not self-hostable.
- **Deployment:** SaaS only (AWS); no on-prem, no k8s. Multi-AZ available on provisioned RA3 (and RG) clusters for HA.

## Bottom line
Reach for Redshift when your analytics live in AWS and you want a mature, columnar MPP warehouse with deep AWS-native integration (S3/Spectrum, Aurora zero-ETL, SageMaker); serverless makes it approachable without cluster tuning. Avoid it for OLTP, high-concurrency small writes, point lookups, or vector search — it is a scan engine, not a transactional store. The single biggest gotcha: primary-key/unique constraints are *not enforced* (informational only) — your app must guarantee uniqueness. Also note that the default isolation is now SNAPSHOT (as of May 2024 for new provisioned clusters; serverless already), which permits write-skew anomalies; opting into SERIALIZABLE for stricter correctness means concurrent writers touching overlapping tables get aborted with "1023" serializable-isolation violations.

## Sources
- [Amazon Redshift deep dive whitepaper (zone maps, columnar)](https://docs.aws.amazon.com/whitepapers/latest/data-warehousing-on-aws/amazon-redshift-deep-dive.html)
- [RA3 with managed storage](https://aws.amazon.com/redshift/features/ra3/)
- [Isolation levels in Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_serial_isolation.html)
- [Snapshot isolation launch (2022)](https://aws.amazon.com/about-aws/whats-new/2022/05/amazon-redshift-snapshot-isolation-level-support-concurrent-transactions/)
- [Snapshot isolation as default for provisioned clusters (May 2024)](https://aws.amazon.com/about-aws/whats-new/2024/05/amazon-redshift-snapshot-isolation-provisioned-clusters/)
- [Multi-AZ deployment docs](https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-multi-az.html)
- [Concurrency scaling docs](https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html)
- [Snapshots and backups](https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html)
- [Federated query overview](https://docs.aws.amazon.com/redshift/latest/dg/federated-overview.html)
- [Amazon Redshift Re-invented (SIGMOD 2022)](https://assets.amazon.science/4b/37/223ac61e450898244a31bed53734/amazon-redshift-re-invented.pdf)
- [Redshift pricing](https://aws.amazon.com/redshift/pricing/)
