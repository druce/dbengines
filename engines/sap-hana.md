---
name: SAP HANA
slug: sap-hana
rank: 22
data_model: Relational (in-memory, multi-model)
license: Proprietary / commercial (SAP)
summary: In-memory columnar relational engine built to run OLTP and OLAP on one copy of the data; the database under SAP's own S/4HANA stack.
last_researched: 2026-06-04
confidence: high
---

# SAP HANA

> In-memory, columnar, ACID relational engine designed so analytics run directly on the transactional row set — high-performance and feature-dense, but proprietary, RAM-hungry, expensive, and most compelling when you already live in the SAP application stack.

## Identity
- **Taxonomy / data model:** Primarily relational, but multi-model — bundles graph, spatial/geospatial, document/JSON (DocStore), text/full-text search, and predictive/ML engines inside one server. The marketing position is "one database for everything."
- **Storage model:** Hybrid. Default and signature mode is an **in-memory column store** (dictionary-encoded, compressed, columnar); a **row store** is also available and is preferred for small, write-heavy, frequently-joined config tables. Data is held in RAM for query; persisted to disk for durability (see Performance). Column tables use a write-optimized **delta store** merged into the read-optimized **main store** by a background **delta merge**. See [lsm-vs-btree](../concepts/lsm-vs-btree.md) (HANA is neither classic LSM nor B-tree — delta/main is its own variant), [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** The original HTAP pitch — Hasso Plattner's 2009 "common database approach for OLTP and OLAP using an in-memory column database." The **physical separation mechanism is the delta/main split**: writes land row-wise in delta, analytics scan the compressed columnar main, and the query engine reads a merged view. This is a genuine HTAP design, not a vague claim, though heavy concurrent OLTP + large scans still contend for the same RAM and CPU. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP-leaning. Scale-out uses a single transaction coordinator and 2PC across index servers; partitions stall affected transactions rather than diverging. Primarily a scale-*up* single-node system; distribution is secondary. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no formal PACELC characterization published. In practice: under partition it favors consistency (CP); else it is latency-optimized for a tightly-coupled, low-latency cluster, not a WAN-distributed quorum store.
- **Default isolation & what's achievable:** [mvcc](../concepts/mvcc.md)-based snapshot isolation. Default is **READ COMMITTED** (statement-level snapshot — each statement sees the latest committed state). **REPEATABLE READ** and **SERIALIZABLE** give transaction-level snapshot isolation, and SAP documents that HANA **does not distinguish between the two — SERIALIZABLE is implemented as snapshot isolation, not true serializability** ([SAP SET TRANSACTION docs](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-sql-reference-guide/set-transaction-statement-transaction-management)). So an "ACID + SERIALIZABLE" claim here means SI, with write-write conflicts blocked by locking but no protection against SI anomalies (write skew). See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **System Replication** is the HA/DR primitive — continuous redo-log shipping from primary to one or more secondaries that can pre-load data into memory for fast failover; supports SYNC, SYNCMEM, and ASYNC modes (sync = no data-loss window but latency-coupled; async = possible loss) ([SAP HANA System Replication Guide](https://help.sap.com/docs/SAP_HANA_PLATFORM/6b94445c94ae495c83a19646e7c3fd56/676844172c2442f0bf6c8b080db05ae7.html)). Single-leader model; failover is typically orchestrated by a cluster manager (e.g., Linux Pacemaker). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo-style per-query consistency levels. Choice is at the isolation level and replication-mode granularity.
- **Clock dependency:** No TrueTime/HLC dependency for correctness; distributed snapshot isolation uses internal transaction/commit IDs, not wall clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Schema-on-write, rigid relational SQL schema. The DocStore (JSON collections) adds schema-flexible document storage alongside.
- **Migration / online DDL:** Supports adding columns and a range of online operations; ⚠️ unverified — exact set of fully non-blocking DDL operations varies by version and table type (column vs row).
- **Type system:** Standard SQL types plus native JSON (DocStore), spatial/geometry, graph (vertex/edge via graph workspaces), full-text/text search, and series data. No first-class general-purpose vector type historically; SAP HANA Cloud added a native `REAL_VECTOR` type with cosine-similarity / L2-distance functions in the **Q1 2024** release (vector engine for embeddings/similarity search) ([SAP HANA Cloud Vector Engine](https://community.sap.com/t5/technology-blog-posts-by-sap/vectorize-your-data-sap-hana-cloud-s-vector-engine-for-unified-data/ba-p/13579558)). On-prem HANA 2.0 does not have it.

## Query interface
- **Language:** SQL (HANA SQL dialect) plus **SQLScript** (procedural extension for stored procedures and calculation logic). Domain languages layered on top: graph queries (GraphScript/Cypher-like via openCypher in HANA Cloud), spatial SQL/MM, full-text predicates. Calculation views are a HANA-specific modeling layer.
- **Transactions:** Full multi-statement ACID, including distributed 2PC transactions across scale-out nodes.
- **Native vs app-side:** Native joins, aggregations, window functions, and secondary indexes; pushdown of computation into the engine ("code-to-data") is a core design goal.
- **Stored procedures / UDFs:** SQLScript procedures and functions; also **AFL** (Application Function Library, incl. PAL predictive and BFL business functions) and R/Python integration for analytics.

## Scaling & topology
- **Vertical vs horizontal:** Strongly **scale-up first** — HANA is built to exploit very large single-node memory (multi-TB). **Scale-out** distributes partitions across hosts with a coordinating index server.
- **Sharding / partitioning:** Manual, declarative table partitioning (range, hash, round-robin, and combinations); partitions can be placed on different index servers. Resharding/repartitioning large tables is an operational event, not transparent. Guidance is often to keep a table's partitions co-located on one host to avoid cross-node transaction cost.
- **Read replicas:** System Replication secondaries can serve read-only queries (Active/Active read-enabled), with the secondary slightly behind the primary; reads there are snapshot-consistent but may be stale.
- **Storage/compute separation:** Classic on-prem HANA couples storage and compute. **HANA Cloud** introduces tiered storage (in-memory hot + disk-based "Native Storage Extension" warm + data lake cold) moving toward elasticity, but it is not a fully disaggregated Snowflake-style architecture. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WAL-style **redo log written before commit returns** (group-committable), plus periodic **savepoints** (default ~5 min) that flush changed pages to the data volume; combined with shadow paging ([SAP HANA Savepoints and Redo Logs](https://help.sap.com/docs/SAP_HANA_PLATFORM/6b94445c94ae495c83a19646e7c3fd56/bee45f05696d4b9596797a7980d403c2.html)). **Data-loss window on crash:** with synchronous log flush, none for committed transactions; the log is replayed from the last savepoint on restart. Async replication adds a loss window only on the DR copy. Log volume on fast storage (SSD/NVMe) is important for commit latency. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput / latency:** Very high analytical scan throughput from compressed in-memory columns and SIMD/parallel execution; low-latency point OLTP from row store and delta. **Restart/warm-up** is a real cost — after a crash or restart, column tables must be loaded back into RAM, so first-access latency spikes until data is resident.
- **Compaction / vacuum / GC:** The **delta merge** is HANA's analog — background merge of delta into main store; it is CPU- and memory-intensive and can transiently affect p99 and need extra memory headroom during the merge. MVCC version garbage collection reclaims old row versions; long-running transactions hold versions and bloat memory.

## Operations & maturity
- **Backup/restore, PITR:** Full and incremental/differential data backups, log backups, and **point-in-time recovery** via log replay; snapshot-based backups supported. Mature backup tooling and Backint integration with enterprise backup vendors.
- **Observability:** Rich — monitoring views (M_* system views), the EXPLAIN PLAN / PlanViz visual plan analyzer, SQL trace, expensive-statement (slow-query) trace, and SAP HANA Cockpit / DB Explorer for administration.
- **Upgrade story:** Revision upgrades; near-zero-downtime upgrades achievable via System Replication takeover (upgrade secondary, fail over, upgrade old primary). Day-2 burden is significant: memory sizing, delta-merge tuning, savepoint/log volume management, license/memory monitoring — typically a dedicated HANA Basis/DBA skill set.
- **Maturity:** Mature, GA since 2010-2011, in heavy enterprise production as the foundation of S/4HANA and BW/4HANA. **No public [jepsen](../concepts/jepsen.md)-style independent consistency analysis exists** — ⚠️ unverified externally; the SI/serializable caveat above is the most important known semantic gotcha. Known failure modes: out-of-memory (OOM) under-provisioned, delta-merge pressure, long-running-transaction version bloat.

## Ecosystem & people
- **Canonical use cases:** Backend for SAP S/4HANA ERP and BW/4HANA analytics; real-time operational reporting on transactional data; consolidating OLTP+OLAP to retire separate data-warehouse ETL; SAP-centric analytics.
- **Anti-patterns:** Greenfield, non-SAP, cost-sensitive workloads where a cheaper disk-based engine ([postgresql](postgresql.md), [mysql](mysql.md)) or a purpose-built analytics warehouse ([snowflake](snowflake.md), [clickhouse](clickhouse.md), [google-bigquery](google-bigquery.md)) fits better; multi-TB cold data where paying RAM prices is wasteful; teams without SAP/HANA operational expertise. It is rarely the right choice purely on technical merits outside the SAP ecosystem.
- **Drivers / connectors:** JDBC/ODBC, ODBC, Python (hdbcli), Node.js, Go, .NET; Smart Data Integration/Access (SDI/SDA) for federation and CDC; integrations with SAP Datasphere, SAP Analytics Cloud, and third-party BI/ETL. dbt and Kafka connectivity exist via community/third-party adapters.
- **Community, support, docs:** Large enterprise SAP community and partner ecosystem; commercial support from SAP. Docs are extensive but sprawling. Steep learning curve; specialized, well-paid talent market — not a commodity skill.

## Licensing & cost
- **OSS license & flavor:** None — fully **proprietary, commercial**. Not open source, not source-available. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Available as self-managed (on-prem / on certified hardware or cloud IaaS) and as **SAP HANA Cloud** (SAP-managed DBaaS). Strong lock-in via SAP-specific features (calculation views, SQLScript, AFL) and the S/4HANA dependency.
- **Cost model:** On-prem licensing is largely **per-GB of in-memory data** (full-use vs cheaper runtime licenses tied to a specific SAP application) — ⚠️ unverified pricing, commonly cited on the order of tens of thousands of USD per 64 GB block for full-use ([Redress Compliance overview](https://redresscompliance.com/sap-hana-database-licensing-explained-runtime-vs-full-use-and-costs/)). HANA Cloud is consumption-based via **capacity units** (memory + storage + compute) ([SAP HANA Cloud pricing](https://www.sap.com/products/data-cloud/hana/pricing.html)). Because RAM is the priced/limiting resource, cost scales aggressively with data size — cheap-at-small inverts hard at large data volumes.

## Hardware / deployment
- **Resource profile:** **Memory-bound** by design — the working set (often effectively the full active dataset) must fit in RAM, plus headroom for delta merge, intermediate results, and version store. Also CPU-bound for large parallel scans. On-prem deployments traditionally require SAP-**certified appliance/TDI hardware**.
- **Storage assumptions:** Fast local storage (SSD/NVMe) for the log volume is important for commit latency; data and log volumes persist memory state.
- **Footprint:** Single-node (scale-up, the common case) or clustered scale-out across hosts. Not embedded, not serverless in the classic sense (HANA Cloud is managed/elastic but not function-style serverless).
- **Deployment:** On-prem, cloud IaaS (certified instances on AWS/Azure/GCP), or SAP-managed HANA Cloud. Runs on SLES/RHEL Linux; container/k8s deployment exists but is not the mainstream pattern for production HANA.

## Bottom line
Reach for SAP HANA if you run SAP S/4HANA or BW/4HANA, or need genuine HTAP — real-time analytics directly on transactional data — and can afford to keep the working set in RAM. Avoid it for greenfield non-SAP projects, cost-sensitive workloads, or large cold-data archives, where disk-based OLTP engines or dedicated columnar warehouses are far cheaper. The single biggest gotcha: it is RAM-priced and RAM-bound, so cost and OOM risk scale with data volume — and despite the "ACID/serializable" framing, SERIALIZABLE is snapshot isolation, not true serializability.

## Sources
- [SAP HANA SET TRANSACTION / isolation levels (SQL Reference)](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-sql-reference-guide/set-transaction-statement-transaction-management)
- [SAP HANA System Replication Guide](https://help.sap.com/docs/SAP_HANA_PLATFORM/6b94445c94ae495c83a19646e7c3fd56/676844172c2442f0bf6c8b080db05ae7.html)
- [SAP HANA Savepoints and Redo Logs](https://help.sap.com/docs/SAP_HANA_PLATFORM/6b94445c94ae495c83a19646e7c3fd56/bee45f05696d4b9596797a7980d403c2.html)
- [Scaling SAP HANA (scale-out)](https://help.sap.com/docs/SAP_HANA_PLATFORM/6b94445c94ae495c83a19646e7c3fd56/a165e192ba374c2a8b17566f89fe8419.html)
- [High-Performance Transaction Processing in SAP HANA (IEEE Data Eng. Bulletin)](https://15799.courses.cs.cmu.edu/fall2013/static/papers/icdebulletin_hana.pdf)
- [Hasso Plattner, "A Common Database Approach for OLTP and OLAP Using an In-Memory Column Database" (SIGMOD 2009)](https://nmeyen.medium.com/the-birth-of-sap-hana-or-a-common-database-approach-for-oltp-and-olap-using-an-in-memory-column-a2d9d648933f)
- [SAP HANA Cloud pricing](https://www.sap.com/products/data-cloud/hana/pricing.html)
- [SAP HANA licensing overview (Redress Compliance)](https://redresscompliance.com/sap-hana-database-licensing-explained-runtime-vs-full-use-and-costs/)
