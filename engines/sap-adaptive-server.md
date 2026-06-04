---
name: SAP Adaptive Server Enterprise
slug: sap-adaptive-server
rank: 25
data_model: Relational
license: Proprietary / commercial (SAP); source-available developer/express editions
summary: Mature lock-based OLTP relational engine — the former Sybase ASE, a Wall Street workhorse now in SAP-led maintenance mode.
last_researched: 2026-06-04
confidence: medium
---

# SAP Adaptive Server Enterprise

> The former Sybase SQL Server / ASE: a battle-tested, T-SQL-compatible, single-node OLTP relational engine that pioneered client-server RDBMS architecture, now in steady maintenance under SAP rather than active feature growth.

## Identity
- **Taxonomy / data model:** Relational ([oltp-olap-htap](../concepts/oltp-olap-htap.md)). SQL with stored procedures; Transact-SQL dialect shared with [microsoft-sql-server](microsoft-sql-server.md) (Microsoft SQL Server forked from the same Sybase codebase circa 1993).
- **Storage model:** Disk-oriented **row-store** ([lsm-vs-btree](../concepts/lsm-vs-btree.md) — uses B+-tree indexes with clustered/non-clustered options, not LSM). Page-based on-disk format (typically 2K–16K pages). Optional **in-memory database (IMDB)** since 15.5/15.7 where a database runs entirely in cache, trading durability for speed ([dbdb.io](https://dbdb.io/db/adaptive-server-enterprise)). Row- and page-level compression available.
- **Workload:** Primarily **OLTP**; handles modest OLAP (star/snowflake) but is not a column-store analytics engine. ⚠️ unverified — ASE is not marketed as HTAP; SAP positions [sap-hana](sap-hana.md) for in-memory/columnar analytics. No physical OLTP/OLAP separation mechanism in ASE itself.

## Distribution & consistency
- **CAP under partition:** N/A as a distributed quorum system — ASE is fundamentally a **single-node** engine. Its HADR/Always-On is a primary + warm-standby replication topology, not a partition-tolerant cluster, so it behaves **CP-like**: on failure you fail over, you do not stay available on both sides. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Effectively a single primary; the consistency-vs-latency knob is in replication mode (sync = no data loss but added commit latency; async = lower latency, possible loss). See [replication-models](../concepts/replication-models.md).
- **Default isolation & what's achievable:** Default is **read committed (level 1)**, enforced by **two-phase locking** ([isolation-levels](../concepts/isolation-levels.md)). All four ANSI levels supported: read uncommitted (level 0 / dirty read), read committed (1), repeatable read (2), serializable (3) ([dbdb.io](https://dbdb.io/db/adaptive-server-enterprise), [SAP KBA 2203206](https://userapps.support.sap.com/sap/support/knowledge/en/2203206)). **Genuine version-based MVCC / snapshot isolation is also available** (opt-in, not the default): row-versioning-backed snapshot isolation was added in the 15.x line, and ASE 16.0 (SP02/SP03) added both **in-memory MVCC** via in-memory row storage (IMRS) and **on-disk MVCC** (versions kept in a temporary database) — in these modes readers and writers do not block each other ([SAP "What's New in ASE 16 SP03"](https://community.sap.com/t5/-/-/m-p/13319136)). The version store carries a maintenance cost (tempdb/IMRS space, version GC). So the default concurrency model is lock-based 2PL, but the snapshot-isolation behavior of [postgresql](postgresql.md) or [oracle](oracle.md) is achievable when explicitly enabled. See [mvcc](../concepts/mvcc.md).
- **Replication:** Single-leader. **HADR / "Always-On"** uses two ASE servers + two SAP Replication Servers + a Fault Manager for automated failover; supports synchronous (zero-data-loss HA), near-synchronous, and asynchronous (DR) modes ([SAP blog, HADR on ASE 16.0](https://blogs.sap.com/2016/09/19/hadr-availability-on-sap-adaptive-server-enterprise-160/)). Split-brain is guarded by the Fault Manager arbitrating failover. Older HA used companion servers with shared storage / OS clustering (e.g., Serviceguard).
- **Tunable consistency?** No per-query consistency levels in the Dynamo sense; tuning is via lock scheme + isolation level per session/query.
- **Clock dependency:** No TrueTime/HLC dependency. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema, declared up front.
- **Migration/evolution:** `ALTER TABLE` supported; some operations are online but many DDL changes acquire locks. ⚠️ unverified — exact online-DDL coverage varies by operation and version; data-copying alters can be blocking.
- **Type system:** standard SQL types plus `text`/`image` LOBs, `identity` columns, user-defined datatypes, `computed columns`, and rudimentary in-row/off-row LOB handling. Limited native JSON (added in later 16.0 SPs). No native vector type. Geospatial support is limited.

## Query interface
- **Language:** SQL via **Transact-SQL (T-SQL)** dialect; client access historically via **Tabular Data Stream (TDS)** wire protocol (shared lineage with SQL Server).
- **Transactions:** full **multi-statement ACID**; explicit `BEGIN TRAN` / `COMMIT` / `ROLLBACK`, savepoints, and two-phase commit (XA) for distributed transactions.
- **Native vs app-side:** native secondary indexes (clustered + non-clustered B+-trees), joins, aggregations, window functions, cost-based optimizer, parallel query execution.
- **Stored procedures / UDFs:** rich T-SQL stored procedures and triggers; **extended stored procedures** compiled as native DLLs/shared libraries; Java in the database (historical).

## Scaling & topology
- **Vertical vs horizontal:** primarily **vertical scale-up** on a single node. No native auto-sharding. Horizontal scale historically via the (now legacy/deprecated) shared-disk **Cluster Edition**.
- **Sharding / partitioning:** table **partitioning** (range, hash, list, round-robin) for manageability and partition-level parallelism, but partitions live within one server, not a distributed cluster.
- **Read replicas:** the HADR standby can serve read-only access; reads there reflect replication lag (eventually consistent vs primary unless sync mode).
- **Storage/compute separation:** No — coupled storage and compute on each node. See [storage-compute-separation](../concepts/storage-compute-separation.md) (this is the pattern ASE does *not* follow).

## Performance & durability
- **Write path:** WAL-based — every database has a **transaction log**; durability via log flush at commit and periodic **checkpoints** that flush dirty pages. See [wal-and-durability](../concepts/wal-and-durability.md). Data-loss window depends on log-flush/replication settings; the in-memory (IMDB) option explicitly relaxes durability for speed.
- **Throughput/latency:** strong, predictable OLTP throughput; row-level (datarows) locking minimizes contention for hot tables; allpages/datapages locking trade concurrency for space/overhead. ⚠️ unverified — no public independent p99 benchmarks; tail latency is sensitive to lock scheme choice and lock contention.
- **Compaction / vacuum / GC:** no LSM compaction; uses in-place page updates. Maintenance burden centers on `update statistics`, `reorg` (to reclaim space / fix fragmentation), and index rebuilds rather than vacuum/compaction.

## Operations & maturity
- **Backup/restore, PITR:** mature `dump database` / `dump transaction` + `load` provide full and transaction-log backups; point-in-time recovery via log replay. Cumulative/incremental dumps supported in 16.0.
- **Observability:** `set showplan`, optimizer trace, MDA monitoring tables, `sp_sysmon`, and the Administration & Management Console (AMC, which replaced the Flash-based Cockpit in 16.0 SP04 — [What's New in 16.0 SP04](https://blogs.sap.com/2020/12/11/whats-new-in-sap-ase-16.0-sp04/)).
- **Upgrade story:** in-place version upgrades; HADR enables reduced-downtime rolling upgrades of the pair. Day-2 burden is meaningful — it is a traditional DBA-heavy engine (device/segment management, lock-scheme tuning, statistics maintenance).
- **Maturity:** very high — 1980s lineage, decades in production on Wall Street and in SAP Business Suite back-end deployments. ⚠️ unverified — **no public Jepsen report exists** for SAP ASE; consistency claims here rest on docs, not formal verification. Known reality: SAP has put ASE into maintenance-focused mode (16.x line; 16.1 update) rather than aggressive feature development.

## Ecosystem & people
- **Canonical use cases:** existing Sybase/ASE OLTP estates; financial-services trading and back-office systems; SAP Business Suite / NetWeaver running on an ASE back end. **Anti-patterns:** greenfield projects (most pick [postgresql](postgresql.md) or a cloud-native engine), large-scale analytics/columnar (use [sap-hana](sap-hana.md) or a warehouse), horizontally scaled web workloads, and teams without Sybase/T-SQL DBA experience.
- **Drivers / connectors:** native TDS, jConnect (JDBC), ODBC, ADO.NET, Open Client/Open Server, Python (`pyodbc`/`python-sybase`). CDC and integration via SAP Replication Server; ⚠️ unverified — third-party CDC/Kafka/dbt support is thinner than for [postgresql](postgresql.md) or [mysql](mysql.md).
- **Community / support:** small and shrinking community relative to mainstream OSS engines; commercial support is via SAP. Docs are comprehensive (legacy Sybase InfoCenter + SAP Help Portal) but dated. Steep learning curve for newcomers; experienced ASE DBAs are an aging, scarce talent pool.

## Licensing & cost
- **License:** **proprietary / commercial**, sold by SAP — not open source. Free **Developer** and capacity-limited **Express** editions exist for non-production use. See [license-taxonomy](../concepts/license-taxonomy.md). (Note: this is unrelated to the post-2018 source-available relicensing wave; ASE was never OSS.)
- **Self-managed vs managed:** primarily self-managed; a **Cloud Edition by IBM Cloud** offers a managed variant. Lock-in via T-SQL extensions, extended stored procedures, and Open Client.
- **Cost model:** per-core / per-CPU commercial licensing plus support contracts. ⚠️ unverified — list pricing is not public; obtained via SAP sales. Generally enterprise-priced, with cost scaling by core count.

## Hardware / deployment
- **Resource profile:** memory- and disk-I/O-sensitive OLTP; working set need not fully fit in RAM (it's disk-oriented with a buffer cache), but the optional IMDB requires the database to fit in memory. CPU usage scales with engine/thread configuration.
- **Storage assumptions:** traditional block storage; benefits from fast NVMe/SSD for log and data devices; tolerates network-attached storage but log latency directly impacts commit latency.
- **Footprint:** **single-node** server (clustered legacy via Cluster Edition; HADR pair for HA). Not embedded, not serverless.
- **Deployment:** on-prem is the norm; runs on Linux, Windows, and several Unix variants; supported on AWS/Azure/GCP IaaS and IBM Cloud managed. k8s deployment is possible but not a first-class story (StatefulSet with persistent volumes); ⚠️ unverified — no widely-used official operator.

## Bottom line
Reach for SAP ASE if you already run a Sybase/ASE estate or an SAP Business Suite back end and need a rock-solid, T-SQL-compatible single-node OLTP engine with a mature backup/HADR story. Do not pick it for greenfield work, analytics/columnar workloads (use [sap-hana](sap-hana.md)), or anything needing horizontal scale-out or a large talent pool — choose [postgresql](postgresql.md) instead. The single biggest gotcha: by default concurrency is lock-based 2PL (real version-based MVCC/snapshot isolation exists but must be explicitly enabled and pays a version-store cost), so lock-scheme choice (allpages vs datapages vs datarows) makes or breaks throughput, and the product is in SAP maintenance mode (16.1, EoMM 2030) rather than active growth.

## Sources
- [Database of Databases — Adaptive Server Enterprise](https://dbdb.io/db/adaptive-server-enterprise)
- [SAP KBA 2203206 — isolation level 0 in ASE](https://userapps.support.sap.com/sap/support/knowledge/en/2203206)
- [HADR Availability on SAP ASE 16.0 (SAP Blogs)](https://blogs.sap.com/2016/09/19/hadr-availability-on-sap-adaptive-server-enterprise-160/)
- [What's New in SAP ASE 16.0 SP04 (SAP Blogs)](https://blogs.sap.com/2020/12/11/whats-new-in-sap-ase-16.0-sp04/)
- [What's New in ASE 16 SP03 — MVCC / IMRS (SAP Community)](https://community.sap.com/t5/-/-/m-p/13319136)
- [SAP Adaptive Server Enterprise product page](https://www.sap.com/products/technology-platform/adaptive-server-enterprise.html)
