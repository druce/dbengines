---
name: SAP IQ
slug: sap-iq
rank: 113
data_model: Relational (columnar)
license: Proprietary (commercial, source-available to licensees only)
summary: Mature columnar analytic RDBMS (ex-Sybase IQ) with a shared-disk multiplex grid; an OLAP data-warehouse engine, not for OLTP.
last_researched: 2026-06-04
confidence: medium
---

# SAP IQ

> A long-lived column-store analytic RDBMS (formerly Sybase IQ) built for compressed, index-heavy data warehousing at terabyte–petabyte scale, with a shared-disk "multiplex" grid that scales compute and SAN storage independently — a batch-load OLAP engine, never an OLTP one.

## When to use

**Use SAP IQ if:**
- ✅ You are an existing SAP/Sybase shop running a large, compressed, batch-loaded data warehouse on SAN storage.
- ✅ You want columnar analytics at TB–PB scale without paying for an all-in-memory engine like [sap-hana](sap-hana.md) — data need not fit in RAM.
- ✅ You want compute and SAN storage to scale independently via the shared-disk multiplex grid, and you have DBAs to tune per-column index types.

**Avoid SAP IQ if:**
- ❌ You need OLTP, high-rate single-row inserts/updates, or low-latency operational apps — its write model is built for bulk loads, and table-level write serialization (only partly relaxed by the RLV row store) chokes transactional throughput.
- ❌ It is greenfield cloud-native analytics — consumption-priced columnar warehouses ([snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [amazon-redshift](amazon-redshift.md), [clickhouse](clickhouse.md)) win on cost, elasticity, and operability.
- ❌ You want a managed/serverless or k8s-idiomatic deployment — it is on-prem/IaaS lift-and-shift with shrinking mindshare and a concentrated talent pool.

## Identity
- **Taxonomy / data model:** Relational, column-oriented. Marketed as an "RDBMS for big-data analytics." Descended from Expressway Technologies' 1990s column engine, productized by Sybase as Sybase IQ (1995), rebranded SAP IQ after SAP's 2010 Sybase acquisition ([Wikipedia: SAP IQ](https://en.wikipedia.org/wiki/SAP_IQ)).
- **Storage model:** Column store, not [lsm-vs-btree](../concepts/lsm-vs-btree.md) B-tree style. Heavy reliance on bitmap and N-bit tiered indexes with LZW-style compression; columns are stored and compressed independently, and most query work is index-driven rather than full scans ([TechTarget](https://www.techtarget.com/searchdatamanagement/feature/A-look-inside-the-SAP-IQ-column-oriented-database)). See [columnar-storage](../concepts/columnar-storage.md). A separate in-memory **RLV (Row-Level Versioned) delta store** absorbs high-velocity writes before merge into the main column store ([SAP IQ RLV admin guide, 16.2](https://help.sap.com/doc/a89afcaa84f21015869c8dc6a82ff342/16.2.0/en-US/SAP_IQ_Administration_In-Memory_Row-Level_Versioning_en.pdf)).
- **Workload:** OLAP / data warehousing. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — the typical SAP architecture pairs IQ as the enterprise data warehouse with [sap-hana](sap-hana.md) or [sap-adaptive-server](sap-adaptive-server.md) handling operational/transactional workloads. ⚠️ unverified — any "real-time analytics" positioning refers to the RLV delta store for fast loads, not concurrent OLTP transaction processing.

## Distribution & consistency
- **CAP under partition:** Effectively **CP** within a multiplex. The architecture is shared-disk (single shared SAN copy of data) with a single **coordinator** node owning the catalog and serializing committed writes ([Sybase Infocenter: Multiplex Architecture](https://infocenter.sybase.com/help/topic/com.sybase.infocenter.dc01839.1600/doc/html/san1278444285622.html)); it is a clustered DB over shared storage, not a partition-tolerant distributed system in the Dynamo sense. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — not characterized in PACELC terms by SAP. Practically: consistency comes from the single shared store + coordinator; the relevant tradeoff is load/merge latency vs. read freshness, not a tunable consistency dial.
- **Default isolation & what's achievable:** Readers get **snapshot/versioned reads** with no read locks; a query sees a committed version of the table as of its start. Writes to the main store historically serialize at **table granularity** (effectively one writer per table). The RLV store adds **row-level snapshot versioning**, allowing multiple concurrent writers to the same table provided they touch different rows; a table-level (TLV) write transaction blocks all RLV writers until it ends ([RLV admin guide](https://help.sap.com/doc/a89afcaa84f21015869c8dc6a82ff342/16.2.0/en-US/SAP_IQ_Administration_In-Memory_Row-Level_Versioning_en.pdf)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Within a multiplex there is one shared data copy; "reader" and "read-write" nodes attach to it — this is a shared-disk cluster, not log-shipping replication. Cross-site DR/replication is handled with external tooling. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo/Cassandra-style per-query consistency levels.
- **Clock dependency:** No correctness dependence on synchronized clocks; coordinator-mediated commit, not [clocks-and-time](../concepts/clocks-and-time.md) timestamp ordering.

## Schema
- **Schema-on-write,** rigid relational schema; tables and typed columns defined up front.
- **Migration/evolution:** Standard SQL DDL. ⚠️ unverified — granular online-DDL/lock behavior; given the table-level write model, schema changes generally take table-level locks and should be treated as offline/maintenance operations.
- **Type system:** Standard SQL scalar types, dates/times/intervals, plus optional add-on libraries for full-text search, word/text indexing, and geospatial/word indexing. No native JSON document or vector-search model in the modern sense. ⚠️ unverified — current JSON support breadth.

## Query interface
- **Language:** ANSI **SQL** with OLAP/analytic extensions; Transact-SQL compatibility inherited from the Sybase lineage (shares the SQL Anywhere catalog engine). Stored procedures in SQL and Transact-SQL ([Wikipedia](https://en.wikipedia.org/wiki/SAP_IQ)).
- **Transactions:** Multi-statement transactional, but tuned for batch DML rather than high-frequency small writes. ACID semantics with snapshot reads; "ACID" here is a warehouse-grade guarantee with table- or row-level write serialization, not high-concurrency OLTP serializable workloads.
- **Native vs app-side:** Native joins, aggregations, window/analytic functions, and a rich library of column indexes (bitmap, HG/high-group, HNG, LF/low-fast, N-bit, datetime) chosen per column to accelerate predicates and grouping.
- **Stored procedures / UDFs:** SQL and T-SQL stored procedures; C/C++ and Java UDFs (in-process and external).

## Scaling & topology
- **Horizontal via Multiplex grid:** Add server nodes for query/load concurrency and add SAN capacity independently; compute and storage scale out separately because all nodes share one storage copy ([InfoWorld](https://www.infoworld.com/article/2621970/sap-s-sybase-adds-scalability-to-iq-analytic-database.html), [SAP Community: shared-nothing multiplex, IQ 16 SP10](https://community.sap.com/t5/technology-blogs-by-sap/extreme-scale-out-with-iq-16-sp10-shared-nothing-multiplex/ba-p/13154041)).
- **Sharding:** No app-visible sharding — data is one logical store on shared disk; "scale" is achieved by spreading queries across nodes, not by hash/range partitioning shards. Later releases (16 SP10) added a shared-nothing multiplex variant for extreme scale-out.
- **Read replicas / read consistency:** Reader nodes serve queries against the shared store with snapshot consistency; the coordinator owns writes.
- **Storage/compute separation:** Yes — a defining feature. Compute nodes and SAN storage provision and scale independently; conceptually adjacent to [storage-compute-separation](../concepts/storage-compute-separation.md), though via shared SAN rather than object storage.

## Performance & durability
- **Write path:** Optimized for **bulk/incremental batch load** (the IQ Loading Engine: client- and server-side bulk load, incremental batch, concurrent multi-table load). Durability via [wal-and-durability](../concepts/wal-and-durability.md)-style transaction logging plus the shared store; RLV delta store is in-memory and merges to disk, so its crash/data-loss window depends on checkpoint/merge configuration. ⚠️ unverified — precise RLV-store crash-recovery loss window.
- **Throughput/latency:** Strong on large scan/aggregation analytic queries against compressed columns; poor for many small concurrent point writes (the classic column-store tradeoff). ⚠️ unverified — published p99 figures.
- **Compaction / GC:** Version-store cleanup reclaims obsolete row versions; RLV-to-main merges are background operations whose tuning affects load throughput and read freshness.

## Operations & maturity
- **Backup/restore:** Native backup/restore including incremental and virtual backups; point-in-time recovery via transaction logs. ⚠️ unverified — exact PITR granularity.
- **Observability:** SQL plans/EXPLAIN, monitoring via SAP Control Center / Sybase Central and web-based admin; system tables and stored-procedure-based diagnostics.
- **Upgrade story:** Versioned in-place upgrades; multiplex upgrades are a coordinated, planned-maintenance activity rather than zero-downtime rolling. Day-2 burden centers on index design, load scheduling, and SAN management — it rewards DBAs who tune index types per column.
- **Maturity:** 30-year lineage, thousands of production sites (BI/DW, e.g. comScore, CoreLogic, IRS per [Wikipedia](https://en.wikipedia.org/wiki/SAP_IQ)); current release line is SAP IQ 16, with **16.2** the latest release (documentation dated 2025-06-16) and 16.1 SP05 (March 2025) also maintained ([SAP IQ 16.2 User Guide](https://help.sap.com/doc/a89e7ed684f21015a097b9f852254a1b/16.2.0/en-US/SAP_IQ_Introduction_to_SAP_IQ.pdf)). **No Jepsen report exists** (single shared-store cluster, outside Jepsen's usual target class). Known limitation: not built for high-concurrency small-write OLTP.

## Ecosystem & people
- **Canonical use cases:** Large compressed data warehouses and data marts, ad-hoc BI/reporting over big historical datasets, regulatory/financial analytics; often the EDW tier beneath [sap-hana](sap-hana.md).
- **Anti-patterns:** OLTP, high-rate single-row inserts/updates, low-latency operational apps, microservice-per-row workloads, greenfield cloud-native analytics where columnar lakehouses ([clickhouse](clickhouse.md), [snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [amazon-redshift](amazon-redshift.md)) are now the default.
- **Drivers/connectors:** ODBC, JDBC, ADO.NET, OLE DB; client libs for Java, C/C++, PHP, Perl, Python, Ruby; ETL/BI tool integration; CDC and tight integration with SAP/Sybase tooling.
- **Community & support:** Enterprise, vendor-driven (SAP) rather than a large open community; documentation is extensive but spread across legacy Sybase Infocenter and help.sap.com. Shrinking mindshare versus modern cloud warehouses; engineer availability is concentrated among incumbent SAP/Sybase shops.

## Licensing & cost
- **License:** **Proprietary, commercial.** Not open source — source is available only to licensees. Licensed options (e.g. multiplex/VLDB management, in-database analytics, security/encryption) are sold à la carte ([Sybase IQ 16 Guide to Licensed Options](https://infocenter.sybase.com/help/topic/com.sybase.infocenter.dc01646.1603/doc/pdf/iqlicense.pdf)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Primarily self-managed (on-prem or on cloud IaaS with attached/SAN storage). No first-party serverless offering; lock-in via SAP/Sybase-specific T-SQL, index types, and multiplex operations.
- **Cost model:** Per-core/per-CPU enterprise licensing plus options and support; capital-heavy and tends to be expensive at scale relative to consumption-priced cloud warehouses. ⚠️ unverified — current SAP price list specifics.

## Hardware / deployment
- **Resource profile:** Disk/IO- and memory-sensitive; benefits from large RAM for caching and the RLV in-memory store, but does **not** require the full dataset to fit in RAM (contrast with in-memory [sap-hana](sap-hana.md)) — a key reason IQ persists for cheap petabyte-scale cold/warm warehouses.
- **Storage assumptions:** Designed around shared **SAN** storage; tolerant of network-attached enterprise storage rather than assuming local NVMe.
- **Footprint:** Single-node or clustered **multiplex** grid; enterprise server software, not embedded or serverless.
- **Deployment:** On-prem traditionally; runs on Windows Server, Linux, and Unix (Solaris, HP-UX, AIX). Cloud deployment is lift-and-shift onto IaaS; not a cloud-native managed service, and k8s/StatefulSet operation is non-idiomatic.

## Bottom line
Reach for SAP IQ if you are an existing SAP/Sybase shop running a large, compressed, batch-loaded data warehouse on SAN storage and want columnar analytics without paying for an all-in-memory engine like HANA. Do not reach for it for OLTP, high-concurrency small writes, or greenfield cloud analytics — modern consumption-priced columnar warehouses ([snowflake](snowflake.md), [google-bigquery](google-bigquery.md), [amazon-redshift](amazon-redshift.md), [clickhouse](clickhouse.md)) win on cost, elasticity, and operability. The biggest gotcha: its write model is built for bulk loads, and table-level write serialization (only partly relaxed by the row-level RLV store) makes it a poor fit for anything resembling transactional throughput.

## Sources
- [SAP IQ — Wikipedia](https://en.wikipedia.org/wiki/SAP_IQ)
- [A look inside the SAP IQ column-oriented database — TechTarget](https://www.techtarget.com/searchdatamanagement/feature/A-look-inside-the-SAP-IQ-column-oriented-database)
- [SAP Sybase IQ Multiplex Architecture — Sybase Infocenter](https://infocenter.sybase.com/help/topic/com.sybase.infocenter.dc01839.1600/doc/html/san1278444285622.html)
- [SAP IQ 16.2 Administration: In-Memory Row-Level Versioning (RLV)](https://help.sap.com/doc/a89afcaa84f21015869c8dc6a82ff342/16.2.0/en-US/SAP_IQ_Administration_In-Memory_Row-Level_Versioning_en.pdf)
- [Sybase IQ 16 Guide to Licensed Options](https://infocenter.sybase.com/help/topic/com.sybase.infocenter.dc01646.1603/doc/pdf/iqlicense.pdf)
- [Extreme Scale Out with IQ 16 SP10 — Shared-Nothing Multiplex (SAP Community)](https://community.sap.com/t5/technology-blogs-by-sap/extreme-scale-out-with-iq-16-sp10-shared-nothing-multiplex/ba-p/13154041)
- [SAP's Sybase adds scalability to IQ analytic database — InfoWorld](https://www.infoworld.com/article/2621970/sap-s-sybase-adds-scalability-to-iq-analytic-database.html)
