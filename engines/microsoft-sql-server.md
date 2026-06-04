---
name: Microsoft SQL Server
slug: microsoft-sql-server
rank: 3
data_model: Relational (multi-model)
license: Commercial / source-available (no OSS license); free Express & Developer editions
summary: Microsoft's flagship commercial RDBMS — mature single-node OLTP/HTAP with T-SQL, lock-based READ COMMITTED by default, and Always On HA; now runs on Linux.
last_researched: 2026-06-04
confidence: high
---

# Microsoft SQL Server

> The mature, full-featured commercial relational database for Windows-and-Linux shops: rock-solid single-node OLTP with optional columnstore HTAP, T-SQL everywhere, and per-core licensing that gets expensive fast at scale.

## Identity
- **Taxonomy / data model:** primarily relational (SQL), multi-model via native JSON (typed `json` data type added in SQL Server 2025), XML, spatial (geometry/geography), graph (`NODE`/`EDGE` tables), and vector search (native `vector` type GA in SQL Server 2025; DiskANN approximate vector indexing is in public preview, not GA, as of the 2025 RTM ([Azure SQL Dev Blog](https://devblogs.microsoft.com/azure-sql/sql-server-2025-embraces-vectors-setting-the-foundation-for-empowering-your-data-with-ai/))). See [oltp-olap-htap](../concepts/oltp-olap-htap.md) for the workload axis.
- **Storage model:** default disk-based **row-store** B-tree (clustered/heap); optional **columnstore** indexes (clustered or nonclustered) for analytics; [lsm-vs-btree](../concepts/lsm-vs-btree.md) — SQL Server is B-tree-based, not LSM. In-Memory OLTP ("Hekaton") tables use lock-free hash and Bw-tree indexes ([Hekaton paper, Diaconu et al. 2013](https://www.microsoft.com/en-us/research/wp-content/uploads/2013/06/Hekaton-Sigmod2013-final.pdf)).
- **Workload:** OLTP-first; HTAP via **real-time operational analytics** — a nonclustered columnstore index over a row-store table, or a clustered columnstore over a memory-optimized table, lets analytic scans run against live OLTP data without a separate warehouse ([Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/get-started-with-columnstore-for-real-time-operational-analytics)). This is the concrete physical separation: OLTP reads/writes hit the row B-tree; analytic queries hit the columnstore copy of the same rows.

## Distribution & consistency
- **CAP under partition:** Single-leader replicated system; effectively **CP** in synchronous-commit Always On (writes block / failover preserves committed data). ⚠️ unverified — no public Jepsen report exists for SQL Server, so partition behavior is characterized from docs, not adversarial testing. CAP is coarse — see [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition, sync-commit AGs favor Consistency (writes stall until a synchronized secondary hardens the log, or fail over without data loss); Else, you trade Latency vs Consistency by choosing sync- vs async-commit replicas ([Availability modes, Microsoft Learn](https://learn.microsoft.com/en-us/sql/database-engine/availability-groups/windows/availability-modes-always-on-availability-groups)). Async-commit secondaries always lag and only support forced failover **with possible data loss**.
- **Default isolation & what's achievable:** default is **READ COMMITTED implemented with locking** (statement sees each row as of the moment it is read; readers take shared locks that block writers) — *not* MVCC by default. Full ladder up to **SERIALIZABLE** (via range locks) is available. Row-versioning ([mvcc](../concepts/mvcc.md)) is opt-in: `READ_COMMITTED_SNAPSHOT ON` (RCSI) transparently makes READ COMMITTED statement-level snapshot (readers don't block writers); `ALLOW_SNAPSHOT_ISOLATION ON` enables transaction-level SNAPSHOT ([Microsoft Learn — Snapshot isolation](https://learn.microsoft.com/en-us/dotnet/framework/data/adonet/sql/snapshot-isolation-in-sql-server)). Note: "ACID" here means serializable is *available*, but the shipped default is locking read committed — see [isolation-levels](../concepts/isolation-levels.md). Version store lives in `tempdb`, which becomes a hotspot under RCSI.
- **Replication:** single-leader. **Always On Availability Groups** are the modern HA/DR story: up to 5 synchronous-commit replicas (incl. primary) supporting automatic failover when synchronized; additional async replicas for DR; readable secondaries. Older mechanisms: Failover Cluster Instances (shared storage), transactional/merge/snapshot replication, log shipping, database mirroring (deprecated). See [replication-models](../concepts/replication-models.md). Split-brain is arbitrated by the cluster quorum (Windows Server Failover Cluster, or Pacemaker on Linux).
- **Tunable consistency?** Not Dynamo-style per-query consistency levels. You choose isolation level per session/query and replica sync mode per replica; reads from readable secondaries are eventually consistent (subject to redo lag).
- **Clock dependency:** correctness does not rest on synchronized physical clocks (no TrueTime/HLC analog); ordering is via log sequence numbers (LSN) on a single primary. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational by default; flexible via `sql_variant`, XML, and the native `json` type (2025). Enforced constraints, FKs, check constraints, computed columns.
- **Migration/evolution:** many `ALTER` operations are metadata-only (add nullable column), but some rewrite the table and take locks. **Online index rebuild** (Enterprise) and **resumable online index/DDL** reduce blocking; Standard edition has fewer online options.
- **Type system:** rich — `decimal`/`money`, `datetime2`/`datetimeoffset`, `uniqueidentifier`, spatial geometry/geography, XML, `json` (2025), `vector` (2025), `hierarchyid`, computed columns, sequences, temporal (system-versioned) tables.

## Query interface
- **Language:** **T-SQL** (Transact-SQL), Microsoft's procedural SQL dialect; broadly ANSI-SQL-compliant for core DML with proprietary extensions. Window functions, CTEs (incl. recursive), `MERGE`, `OPENJSON`/`FOR JSON`, full graph query syntax (`MATCH`).
- **Transactions:** full multi-statement ACID; explicit `BEGIN TRAN`/`COMMIT`/`ROLLBACK`, savepoints, distributed transactions (MS DTC).
- **Native vs app-side:** native secondary indexes (incl. filtered, included-column, columnstore), joins, aggregations, window functions — all server-side.
- **Stored procedures / UDFs:** T-SQL stored procs, scalar/table-valued functions, triggers; **CLR integration** for procedures/functions in .NET languages (C#); natively-compiled stored procs for In-Memory OLTP. External Python/R/Java via Machine Learning Services / external languages.

## Scaling & topology
- **Vertical-first.** Scale-up is the primary story; SQL Server has **no built-in automatic horizontal sharding**. Horizontal partitioning of a single instance is via **table partitioning** (partition functions/schemes) — single-node, not distributed. Application-level sharding or third-party patterns are required for true scale-out. ⚠️ unverified — Azure SQL Hyperscale / Azure SQL Database (see [microsoft-azure-sql-database](microsoft-azure-sql-database.md)) provide cloud scale-out variants but are separate products.
- **Read replicas:** readable secondaries in Always On AGs; reads are eventually consistent (redo lag), can offload reporting and backups.
- **Storage/compute separation:** not in box SQL Server (monolithic). The Hyperscale architecture in Azure SQL is the separated-storage variant — see [storage-compute-separation](../concepts/storage-compute-separation.md) and [microsoft-azure-sql-database](microsoft-azure-sql-database.md).

## Performance & durability
- **Write path:** write-ahead log ([wal-and-durability](../concepts/wal-and-durability.md)); transactions are durable once the log record is hardened (fsync) at commit. **Data-loss window:** zero on a single instance with default durability; **delayed durability** (opt-in) batches log flushes for throughput at the cost of a small loss window on crash. In sync-commit AGs, commit waits for a secondary to harden the log (no loss on failover); async-commit risks loss equal to redo lag.
- **Throughput/latency profile:** strong OLTP throughput; In-Memory OLTP (Hekaton) uses optimistic [mvcc](../concepts/mvcc.md) and lock/latch-free structures for high-contention workloads. Tail latency sensitive to `tempdb` contention (esp. under RCSI/snapshot), lock escalation, and parameter-sniffing plan regressions.
- **Compaction / vacuum / GC:** no LSM compaction. Row-version cleanup runs against the `tempdb` version store; ghost-record cleanup and index fragmentation require periodic index maintenance. In-Memory OLTP has a background garbage collector for stale row versions.

## Operations & maturity
- **Backup/restore, PITR:** full/differential/transaction-log backups; **point-in-time restore** from log chain; backup compression and encryption; backup to URL (Azure Blob); snapshots.
- **Observability:** detailed `EXPLAIN`-equivalent **query execution plans** (estimated/actual), Query Store (captures plan history and regressions), Extended Events, Dynamic Management Views (DMVs), slow-query and deadlock diagnostics.
- **Upgrade story:** in-place or side-by-side upgrades; rolling upgrades possible across Always On replicas to minimize downtime. Day-2 burden: index/statistics maintenance, `tempdb` sizing, plan-regression management, licensing audits.
- **Maturity:** decades of production track record across enterprise OLTP. Known failure modes: parameter sniffing, lock escalation/blocking under locking READ COMMITTED, `tempdb` bottlenecks, long-running implicit transactions. ⚠️ unverified — **no Jepsen report exists** for SQL Server / Always On AGs; distributed-consistency claims are not independently adversarially verified.

## Ecosystem & people
- **Canonical use cases:** enterprise line-of-business OLTP, .NET application backends, departmental and mid-market apps, mixed OLTP+operational-reporting via columnstore. **Anti-patterns:** internet-scale write sharding (no native auto-shard), petabyte cloud-native analytics warehousing (use a dedicated warehouse), cost-sensitive massive-core deployments (per-core licensing inverts), schemaless/document-first apps.
- **Drivers / ORMs / connectors:** ODBC, JDBC, ADO.NET, OLE DB; first-class with Entity Framework / .NET; SSIS (ETL), Change Data Capture and Change Tracking, CDC connectors to Kafka/Debezium, dbt adapter (`dbt-sqlserver`), Power BI and most BI tools.
- **Community & support:** very large community, extensive Microsoft Learn docs (high quality), broad consultant/DBA availability, commercial Microsoft support. Moderate learning curve; teams of any size; T-SQL/DBA talent widely available.

## Licensing & cost
- **License:** proprietary/commercial, **no OSS license** (source-available reference only). See [license-taxonomy](../concepts/license-taxonomy.md). **Free editions:** Express (capped — up to 50 GB/database in 2025, limited cores/RAM) for production small apps; Developer (full Enterprise feature set, non-production only) — and a new **Standard Developer** edition in 2025 ([SQL Server 2025 editions, Microsoft Learn](https://learn.microsoft.com/en-us/sql/sql-server/editions-and-components-of-sql-server-2025)).
- **Editions:** **Enterprise** (per-core only; all features incl. unlimited online ops, advanced HA, unlimited memory), **Standard** (per-core *or* Server+CAL; capped at 32 cores / 256 GB RAM in 2025, limited HA), Web, Express, Developer ([SAMexpert](https://samexpert.com/sql-server-2025-licensing-update/)).
- **Self-managed vs managed:** self-managed on Windows or **Linux** (RHEL/Ubuntu/SLES; 2025 supports RHEL 10 / Ubuntu 24.04) and containers; managed variants are Azure SQL Database / Managed Instance ([microsoft-azure-sql-database](microsoft-azure-sql-database.md)). Lock-in via T-SQL dialect, SSIS/SSRS/SSAS, and CLR extensions.
- **Cost model:** **per-core** (Enterprise) or **per-core / Server+CAL** (Standard), with optional Software Assurance for benefits like license mobility and unlimited virtualization. Cheap at small scale (Express free), expensive at high core counts — the model inverts as you scale cores/RAM.

## Hardware / deployment
- **Resource profile:** memory-hungry (buffer pool caches data pages); benefits from large RAM holding the working set, though it does not require the whole dataset in RAM (disk-based engine). In-Memory OLTP tables *must* fit in memory. CPU-bound under heavy analytic/columnstore queries.
- **Storage assumptions:** prefers low-latency local NVMe/SSD, especially for `tempdb` and the transaction log; tolerates network-attached/SAN storage but log-write latency is the critical path.
- **Footprint:** single-node or clustered (FCI / Always On); not embedded and not serverless in-box (LocalDB is a lightweight dev variant). Serverless tiers exist only in Azure SQL.
- **Deployment:** on-prem, IaaS VMs, containers (official Linux images), Kubernetes (deployable but stateful-set realities — storage/quorum care needed); SaaS only via Azure SQL family.

## Bottom line
Reach for SQL Server when you have a Windows/.NET-centric enterprise, need a mature single-node OLTP database with strong tooling (Query Store, plans, Always On HA) and optional columnstore HTAP, and can absorb per-core licensing. Do not reach for it if you need native horizontal write-scale-out, cloud-native separated storage/compute (use [microsoft-azure-sql-database](microsoft-azure-sql-database.md) Hyperscale or another engine), or want to avoid commercial licensing costs. **Biggest gotcha:** the default isolation is *locking* READ COMMITTED, so reader/writer blocking surprises teams used to MVCC engines like [postgresql](postgresql.md) — turning on RCSI fixes the blocking but shifts pressure onto `tempdb`.

## Sources
- [Editions and components of SQL Server 2025 — Microsoft Learn](https://learn.microsoft.com/en-us/sql/sql-server/editions-and-components-of-sql-server-2025)
- [Snapshot isolation in SQL Server — Microsoft Learn](https://learn.microsoft.com/en-us/dotnet/framework/data/adonet/sql/snapshot-isolation-in-sql-server)
- [Availability modes for an availability group — Microsoft Learn](https://learn.microsoft.com/en-us/sql/database-engine/availability-groups/windows/availability-modes-always-on-availability-groups)
- [Get started with columnstore for real-time operational analytics — Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/get-started-with-columnstore-for-real-time-operational-analytics)
- [Hekaton: SQL Server's Memory-Optimized OLTP Engine (Diaconu et al., SIGMOD 2013)](https://www.microsoft.com/en-us/research/wp-content/uploads/2013/06/Hekaton-Sigmod2013-final.pdf)
- [SQL Server 2025 licensing update — SAMexpert](https://samexpert.com/sql-server-2025-licensing-update/)
