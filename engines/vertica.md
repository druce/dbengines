---
name: Vertica
slug: vertica
rank: 47
data_model: Relational (columnar MPP)
license: Proprietary (OpenText; being divested to Rocket Software, deal announced Feb 2026, expected to close mid-2026); free Community Edition (≤3 nodes, ≤1 TB)
summary: Shared-nothing columnar MPP analytics warehouse descended from C-Store; projections instead of indexes, with an Eon mode that separates compute from S3-style communal storage.
last_researched: 2026-06-04
confidence: high
---

# Vertica

> A mature columnar MPP analytics database (the commercialized C-Store) whose performance comes from physically pre-sorted, pre-segmented, compressed "projections" rather than indexes — now offered in an Eon mode that decouples compute from object storage.

## When to use

**Use Vertica if:**
- ✅ You need a battle-tested, high-performance columnar MPP warehouse for large SQL analytics, BI, clickstream/ad-tech, or telco CDR workloads
- ✅ You want to run it yourself (on-prem or your own cloud), especially Eon mode for elastic compute over S3-style communal storage
- ✅ You bulk-load via COPY and run large scans, joins, and aggregations — plus in-database ML over big columnar datasets
- ✅ You can invest in projection/segmentation design to get columnar I/O performance

**Avoid Vertica if:**
- ❌ You get projection design or Tuple Mover health wrong — bad sort order/segmentation, too many small ROS containers, or unpurged deletes slow it dramatically, and there are no indexes to bail you out (the biggest gotcha)
- ❌ Your workload is OLTP, single-row lookups/updates, or high-concurrency small transactions
- ❌ You have heavy trickle/row-at-a-time inserts that fight the Tuple Mover, or tiny datasets where DuckDB/Postgres is simpler
- ❌ You want a zero-ops serverless warehouse — Snowflake or BigQuery fit better

## Identity
- **Taxonomy / data model:** relational SQL data warehouse; commercial descendant of the academic [C-Store](https://dbdb.io/db/vertica) column-store prototype. Sold today as "OpenText Analytics Database (Vertica)."
- **Storage model:** true column-store. Data lives in **projections** — materialized, sorted, segmented, aggressively compressed/encoded copies of (subsets of) table columns; there are no traditional secondary indexes ([columnar-storage](../concepts/columnar-storage.md), [lsm-vs-btree](../concepts/lsm-vs-btree.md) — Vertica is neither LSM nor B-tree; it is sorted/encoded column files). On-disk format is the **ROS (Read Optimized Store)**: sorted, compressed column files on disk. Historically a small in-memory **WOS (Write Optimized Store)** absorbed trickle inserts before the Tuple Mover flushed them to ROS; WOS was deprecated and removed in recent versions, so loads now go directly to ROS containers.
- **Workload:** OLAP — large scans, joins, and aggregations over bulk-loaded data. Not an OLTP engine: no efficient single-row point lookups/updates, and row-at-a-time DML is slow. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** CP-leaning. Vertica is a shared-nothing cluster requiring a quorum of nodes plus K-safety to stay up; on enough node loss the database goes down rather than serving divergent data. See [cap-pacelc](../concepts/cap-pacelc.md). ⚠️ unverified — no formal CAP/PACELC classification is published by the vendor; this is inferred from its quorum + K-safety design.
- **PACELC:** ⚠️ unverified — not formally characterized. In practice it favors consistency/correctness over availability under partition (quorum requirement), and is a latency-vs-throughput analytics engine in the normal case rather than a low-latency-vs-consistency tradeoff.
- **Default isolation & what's achievable:** **READ COMMITTED by default**; **SERIALIZABLE** is available and is what internal Tuple Mover, refresh, and all DDL run at ([source](https://docs.vertica.com/24.1.x/en/admin/transactions/read-committed-isolation/), [SERIALIZABLE](https://docs.vertica.com/24.1.x/en/admin/transactions/serializable-isolation/)). Vertica only implements these two of the four SQL levels — REPEATABLE READ is treated as SERIALIZABLE. READ COMMITTED uses MVCC-style epoch snapshots (a SELECT sees a snapshot of committed data as of transaction start) and thus permits non-repeatable and phantom reads; SERIALIZABLE is implemented via **table-level read/write locks**, not predicate locks or SSI ([source](https://docs.vertica.com/24.1.x/en/admin/transactions/serializable-isolation/)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** not single/multi-leader in the OLTP sense. Durability and availability come from **K-safety**: each segment is stored on K+1 nodes (buddy projections). In **Enterprise mode** data is co-located on node disks; in **Eon mode** durability lives in communal object storage and nodes subscribe to shards. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels (not a Dynamo-style system). Consistency is governed by isolation level + epochs.
- **Clock dependency:** correctness does not rest on synchronized physical clocks; visibility is governed by an internal **epoch** counter, not wall-clock time. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational schema; strongly typed columns. Can also query external/Parquet/ORC data on object storage (external tables, schema applied on read for those).
- **Migration/evolution:** supports `ALTER TABLE ADD/DROP COLUMN`; many such operations are metadata-only and fast, but changes that affect a projection's sort order or segmentation require creating/refreshing new projections (which copy data). DDL runs at SERIALIZABLE and takes table locks.
- **Type system:** standard SQL types plus arrays, structs (`ROW`)/nested types, geospatial (`GEOMETRY`/`GEOGRAPHY` via the Place package), `UUID`, intervals, and a flexible/semi-structured **Flex Tables** facility for JSON. No first-class native vector/ANN index type comparable to dedicated vector DBs.

## Query interface
- **Language:** SQL — broadly standard, PostgreSQL-flavored syntax and wire-protocol-adjacent drivers; rich analytic SQL (window functions, `GROUPING SETS`, time-series gap-filling/interpolation, pattern matching `MATCH`, event-series joins). Plus built-in in-database **machine learning** functions.
- **Transactions:** full multi-statement ACID transactions, but tuned for bulk/analytic DML, not high-concurrency row updates.
- **Native vs app-side:** joins, aggregations, and window functions are native and the core competency; there are **no user-managed secondary indexes** — query speed comes from designing projections (Database Designer can auto-generate them).
- **Stored procedures / UDFs:** stored procedures (PL/vSQL), plus UDxs (user-defined transforms/aggregates/scalars/load parsers) in C++, Java, Python, and R.

## Scaling & topology
- **Vertical vs horizontal:** horizontal MPP scale-out across a shared-nothing cluster; also benefits from large per-node RAM/CPU.
- **Sharding/partitioning:** tables are **segmented** (hash-distributed) across nodes and additionally **partitioned** by a column (commonly date) for partition pruning and fast drop. In **Enterprise mode**, adding/removing nodes triggers an expensive rebalance/re-segmentation ([can mean hours of degraded performance/downtime](https://docs.vertica.com/25.1.x/en/architecture/eon-vs-enterprise/)).
- **Read replicas / read consistency:** no separate "read replica" concept; all nodes serve queries. K-safe buddy projections provide redundancy, not a stale read tier.
- **Storage/compute separation:** **Eon mode** stores all data in **communal storage** (S3, GCS, Azure Blob, or on-prem S3-compatible like Pure/MinIO) and caches hot data in a local **depot**; compute nodes/**subclusters** can scale elastically and independently of storage, and new nodes join in minutes by subscribing to shards rather than rebalancing data ([Eon vs Enterprise](https://docs.vertica.com/25.1.x/en/architecture/eon-vs-enterprise/), [Eon paper](https://pages.cs.wisc.edu/~yxy/cs839-s20/papers/eon-Vertica.pdf)). See [storage-compute-separation](../concepts/storage-compute-separation.md). **Enterprise mode** keeps the classic local-disk shared-nothing design.

## Performance & durability
- **Write path:** loads go to ROS containers; the background **Tuple Mover** merges/compacts small containers (mergeout) — analogous in spirit to compaction. Bulk `COPY` is the intended ingest path and is very fast; trickle/row-by-row inserts create many small containers and pressure the Tuple Mover. Durability is from K-safe replication (Enterprise) or commit to communal storage (Eon); see [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact crash-recovery data-loss window for in-flight, not-yet-flushed loads is not precisely documented here; committed transactions are recovered from buddy projections (Enterprise) or communal storage (Eon).
- **Throughput/latency:** excellent scan/aggregation throughput on well-designed projections due to columnar I/O, encoding, and pushed-down operators; poor at point queries and high small-transaction concurrency. p99 is sensitive to projection quality, depot warmth (Eon), and Tuple Mover backlog.
- **Compaction / GC:** Tuple Mover mergeout consolidates ROS containers; deletes are logical (delete vectors) and reclaimed by **purge**/mergeout at/after the **Ancient History Mark (AHM)** epoch. Too-many-small-ROS ("ROS pushback") and unpurged deletes are the classic p99 killers.

## Operations & maturity
- **Backup/restore, PITR:** `vbr` backup/restore and object-level restore (Enterprise); in Eon, durability and point-in-time-ish recovery leverage communal storage plus restore points/revive. Snapshotting supported.
- **Observability:** `EXPLAIN` plans and profiling, extensive system tables (`V_MONITOR`/`V_CATALOG`), query/resource-pool monitoring, Management Console GUI.
- **Upgrade story:** version upgrades generally require a cluster restart (downtime); not a zero-downtime rolling upgrade for the core engine. Eon subclusters ease some operational changes. Day-2 burden centers on **projection design / Database Designer**, resource pool tuning, and Tuple Mover/partition management.
- **Maturity:** very mature (GA ~2005, C-Store lineage), large production deployments at telco/ad-tech/finance scale. **No published Jepsen report exists** for Vertica. Known failure modes: ROS pushback, runaway Tuple Mover, projection skew, and rebalance pain when resizing Enterprise clusters.

## Ecosystem & people
- **Canonical use cases:** large-scale SQL data warehousing / BI, clickstream and ad-tech analytics, telco CDR analytics, in-database ML over big columnar datasets. **Anti-patterns:** OLTP, single-row lookups/updates, high-concurrency small transactions, low-latency operational serving, tiny datasets where a single-node engine (e.g. [duckdb](duckdb.md), [postgresql](postgresql.md)) is simpler. Heavy trickle-insert workloads fight the Tuple Mover.
- **Drivers / connectors:** JDBC, ODBC, ADO.NET, Python (`vertica-python`), Go, vsql CLI; integrates with Kafka (native streaming load), Spark, dbt, and mainstream BI tools (Tableau, Power BI, Looker). Reads/writes Parquet/ORC on object stores.
- **Community / support:** commercial vendor support (OpenText today; moving to Rocket Software per the Feb 2026 divestiture); reasonable docs; smaller mindshare today versus cloud-native warehouses ([snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [amazon-redshift](amazon-redshift.md)) and [clickhouse](clickhouse.md). Learning curve concentrated in projection/segmentation design.

## Licensing & cost
- **License:** **proprietary**, closed-source. Ownership chain: Vertica Systems (standalone, founded by Michael Stonebraker et al.) → **HP** (2011) → **HPE** (2015) → **Micro Focus** (2017) → **OpenText** (Jan 2023, via its Micro Focus acquisition). On **2 Feb 2026, OpenText announced it will divest Vertica to [Rocket Software for US$150M](https://www.rocketsoftware.com/en-us/news/rocket-software-acquire-vertica-analytics-database-platform-opentext)**, a deal expected to close mid-2026 subject to regulatory approval — so the vendor of record is changing. See [license-taxonomy](../concepts/license-taxonomy.md). A free **Community Edition** allows up to **3 nodes and 1 TB** of (uncompressed) data; this CE offering remains documented through current releases (CE container images expire after one year) ([CE docs](https://docs.vertica.com/24.4.x/en/getting-started/community-edition-ce/)).
- **Self-managed vs managed:** primarily self-managed software (on-prem or in your own cloud/VMs); deployable on AWS/GCP/Azure and Kubernetes. There is no first-party fully-serverless SaaS comparable to Snowflake's model, though Eon makes cloud elasticity feasible.
- **Cost model:** commercial licensing is **per-TB of raw data** (unlimited nodes/users) **or per-node measured in cores** (unlimited data) ([OpenText ALA](https://www.opentext.com/media/documentation/additional-license-authorizations-for-analytics-database-software-products-documentation-en.pdf)). Per-TB pricing can invert badly as raw data grows; per-core suits large data with bounded compute. **Lock-in** risk via proprietary projection/storage format and SQL extensions.

## Hardware / deployment
- **Resource profile:** CPU- and memory-hungry for joins/aggregations; benefits from large RAM (resource pools, hash joins, depot in Eon) but does **not** require the full dataset to fit in RAM — it is a disk/object-store-backed columnar engine.
- **Storage assumptions:** Enterprise mode wants fast local disks (NVMe/SSD) per node; Eon mode tolerates object-storage latency by caching hot data in the local **depot** (so local SSD still matters for performance).
- **Footprint:** clustered, multi-node (minimum viable is a few nodes; K-safety needs ≥3 for K=1). Not embedded, not single-binary. Eon enables elastic subclusters.
- **Deployment:** on-prem or self-hosted cloud; container/Kubernetes operator available; Eon mode is the natural cloud/object-storage deployment.

## Bottom line
Reach for Vertica when you need a battle-tested, high-performance columnar MPP warehouse for large SQL analytics and want to run it yourself (on-prem or your own cloud), especially with Eon mode for elastic compute over S3-style storage. Skip it for OLTP, point lookups, high-concurrency small writes, or small datasets — and avoid it if you want a zero-ops serverless warehouse, where [snowflake](snowflake.md) or [google-bigquery](google-bigquery.md) fit better. The single biggest gotcha is that performance lives and dies by **projection design and Tuple Mover health**: get segmentation/sort order wrong (or let small ROS containers and unpurged deletes pile up) and the engine slows dramatically — there are no indexes to bail you out.

## Sources
- [Database of Databases — Vertica (C-Store lineage, architecture)](https://dbdb.io/db/vertica)
- [READ COMMITTED isolation — Vertica docs](https://docs.vertica.com/24.1.x/en/admin/transactions/read-committed-isolation/)
- [SERIALIZABLE isolation — Vertica docs](https://docs.vertica.com/24.1.x/en/admin/transactions/serializable-isolation/)
- [Eon vs. Enterprise Mode — Vertica docs](https://docs.vertica.com/25.1.x/en/architecture/eon-vs-enterprise/)
- [Eon Mode: Bringing the Vertica Columnar Database to the Cloud (paper)](https://pages.cs.wisc.edu/~yxy/cs839-s20/papers/eon-Vertica.pdf)
- [Community Edition — Vertica docs](https://docs.vertica.com/24.4.x/en/getting-started/community-edition-ce/)
- [OpenText Analytics Database — Additional License Authorizations (pricing metrics)](https://www.opentext.com/media/documentation/additional-license-authorizations-for-analytics-database-software-products-documentation-en.pdf)
- [Rocket Software to Acquire Vertica from OpenText (Feb 2026 divestiture)](https://www.rocketsoftware.com/en-us/news/rocket-software-acquire-vertica-analytics-database-platform-opentext)
