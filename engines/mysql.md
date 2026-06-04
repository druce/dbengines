---
name: MySQL
slug: mysql
rank: 2
data_model: Relational
license: GPLv2 (Community) + Oracle commercial (dual license)
summary: The ubiquitous open-source OLTP relational DB; safe and battle-tested, but its default "REPEATABLE READ" is weaker than the name implies.
last_researched: 2026-06-04
confidence: high
---

# MySQL

> The world's most-deployed open-source relational database — easy to run, enormous ecosystem, owned by Oracle under a dual GPL/commercial license — whose biggest gotcha is that its default isolation level fails to deliver true repeatable-read semantics.

## Identity
- **Taxonomy / data model:** relational (SQL). Multi-model in a limited sense: native `JSON` type and a document-store API (X Protocol / MySQL Shell) layered on InnoDB, plus spatial/GIS types. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** pluggable storage engines. Default is **InnoDB** — a clustered-index row-store on a [B+tree](../concepts/lsm-vs-btree.md) with [mvcc](../concepts/mvcc.md) (undo logs). Legacy **MyISAM** (non-transactional, table-level locking) is deprecated for data and survives mainly in old schemas and the `mysql` system tables (now also InnoDB in 8.0+). MEMORY, ARCHIVE, CSV, NDB exist for niche uses.
- **Workload:** primarily **OLTP**. Not an analytics engine; large aggregations are slow. Oracle's **HeatWave** (managed-only) bolts on an in-memory columnar accelerator for HTAP/analytics, but stock MySQL is row-store OLTP only — treat any general "HTAP" claim as HeatWave-specific.

## Distribution & consistency
- **CAP under partition:** a classic single-leader async-replication MySQL deployment is effectively **CP-ish on the primary, AP-ish on replicas** (replicas serve stale reads, no quorum). **Group Replication / InnoDB Cluster** is a quorum system: it favors **CP** — a minority partition stops accepting writes. CAP is coarse; see [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition, Group Replication sacrifices availability for consistency (minority blocks). Else (normal operation) classic async replication chooses **latency over consistency** (replicas lag); Group Replication adds tunable consistency that can choose consistency at the cost of latency.
- **Default isolation & what's achievable:** default is **REPEATABLE READ** ([source](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)). Available: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE. **Major claim-vs-reality divergence:** Jepsen (2023, MySQL 8.0.34) found MySQL's REPEATABLE READ does **not** satisfy PL-2.99 Repeatable Read and even violates Snapshot Isolation — observing **G2-item, read skew (G-single), lost updates, and internal-consistency violations** ([Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34)). Single-node **SERIALIZABLE** did appear to satisfy PL-3, but Jepsen found **SERIALIZABLE was not actually serializable on AWS RDS MySQL clusters** (fractured-read-like anomalies). READ UNCOMMITTED and READ COMMITTED appeared to meet their (weaker) guarantees. Practically: do not rely on the isolation-level name; use explicit `SELECT ... FOR UPDATE`/locking for correctness-critical paths. Under REPEATABLE READ, InnoDB uses **next-key (gap) locks** to suppress phantoms ([InnoDB locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)); switching to READ COMMITTED disables most gap locking. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **single-leader** by default. The leader writes a **binary log (binlog)**; replicas pull and replay it. Modes: **asynchronous** (default, data-loss window on primary crash), **semi-synchronous** (primary waits for ≥1 replica to acknowledge receipt — not apply — bounding but not eliminating loss). **Group Replication** is a quorum/Paxos group (multi-leader-capable) built on a homegrown Paxos variant, **XCom** ([source](https://dev.mysql.com/blog-archive/the-king-is-dead-long-live-the-king-our-homegrown-paxos-based-consensus/)). Failover: manual or via orchestrators (Orchestrator, MySQL Router + InnoDB Cluster); classic async replication has a real **split-brain / lost-write** risk on failover. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes, in Group Replication via `group_replication_consistency` (`EVENTUAL` … `BEFORE`/`AFTER`/`BEFORE_AND_AFTER`/`BEFORE_ON_PRIMARY_FAILOVER`) to prevent stale reads after failover, trading latency/availability for consistency ([source](https://dev.mysql.com/doc/refman/8.4/en/group-replication-configuring-consistency-guarantees.html)). Classic replication has no per-query consistency level.
- **Clock dependency:** correctness does **not** rest on synchronized clocks (no TrueTime/HLC-style ordering); ordering comes from binlog/GTID and Paxos, not wall clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid, typed columns. The `JSON` column type allows schemaless documents within a typed table (schema-on-read for that column).
- **Migration/evolution:** InnoDB supports **online DDL** for many `ALTER` operations (`ALGORITHM=INPLACE`/`INSTANT`); `INSTANT` add/drop column is metadata-only since 8.0. But some `ALTER`s still **rebuild the table / take metadata locks** and block writes — large-table migrations commonly use external tools (pt-online-schema-change, gh-ost).
- **Type system:** integers/decimals, `DATETIME`/`TIMESTAMP`, `JSON` (with functional indexes and generated columns), spatial/GIS types, `ENUM`/`SET`. No native array type; no rich interval type. Vector type (`VECTOR`) added in MySQL 9.0 for embeddings — relatively new, see [mariadb](mariadb.md)/competitors for maturity comparison.

## Query interface
- **Language:** SQL, broadly following the standard with MySQL-isms. 8.0+ added window functions, CTEs (incl. recursive), and `LATERAL`. Historically loose: silent type coercion and (pre-8.0 default) permissive `sql_mode`; modern defaults are stricter (`STRICT_TRANS_TABLES`, `ONLY_FULL_GROUP_BY`).
- **Transactions:** full multi-statement **ACID** on InnoDB (with the isolation caveats above). DDL is **not transactional** (no rollback of `ALTER`/`CREATE`), though 8.0 made DDL atomic at the data-dictionary level (crash-safe, not user-rollbackable).
- **Native vs app-side:** secondary indexes, joins, subqueries, aggregations, window functions, full-text indexes (InnoDB), spatial indexes — all native. Foreign keys enforced by InnoDB.
- **Stored procedures / UDFs:** stored procedures, functions, triggers, events in MySQL's procedural SQL; native UDFs in C/C++ loadable plugins. The procedural language is weaker/slower than PL/pgSQL.

## Scaling & topology
- **Vertical-first.** Horizontal scaling is **read-scaling via replicas**; write-scaling requires **application-level sharding** (no built-in automatic sharding in community MySQL). Vitess (CNCF, the YouTube/PlanetScale layer) provides transparent sharding on top of MySQL but is a separate system.
- **Read replicas:** common and easy, but **reads are eventually consistent** (replica lag) unless using Group Replication consistency levels or routing reads to the primary.
- **Storage/compute separation:** not in stock MySQL. Cloud variants do this: **Amazon Aurora MySQL** (shared distributed storage), **PlanetScale** (Vitess), Alibaba PolarDB. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** InnoDB writes to the **redo log** (WAL) and **doublewrite buffer**; the **binlog** is separate (used for replication + PITR). Durability hinges on two knobs: `innodb_flush_log_at_trx_commit` (1 = fsync redo every commit = durable; 2/0 = faster, can lose ~1s of commits on OS/host crash) and `sync_binlog` (1 = fsync binlog every commit). The **fully durable** config is `innodb_flush_log_at_trx_commit=1` + `sync_binlog=1` (the modern default); relaxing either widens the **data-loss window on crash**. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** strong OLTP throughput for point lookups and short transactions; well-understood tuning (buffer pool sizing dominates). Tail latency hurt by lock contention (gap locks on secondary indexes are a classic p99 trap) and by purge/checkpoint stalls.
- **Compaction / vacuum / GC:** no LSM compaction. InnoDB has a **purge** thread that reclaims old MVCC undo (row versions); a long-running transaction holding back the read view causes **undo/history-list bloat** and degraded performance — the analog of Postgres's bloat/vacuum problem.

## Operations & maturity
- **Backup/restore, PITR:** logical dumps (`mysqldump`, `mysqlpump`), physical hot backup (Percona XtraBackup; Oracle's MySQL Enterprise Backup is commercial-only). **PITR** via binlog replay from a base backup. Snapshots via filesystem/cloud volume snapshots.
- **Observability:** `EXPLAIN`/`EXPLAIN ANALYZE`, `performance_schema`, `sys` schema, slow-query log. The optimizer is decent but historically less sophisticated than Postgres's; plan stability and missing hints have improved in 8.0+.
- **Upgrade story:** in-place major upgrades (e.g., 5.7→8.0) require care (data-dictionary upgrade, deprecated features); rolling upgrades possible with replication. Day-2 burden is moderate and very well-documented.
- **Maturity:** extremely high — 30 years in production at massive scale (Facebook, Booking, Shopify, etc.). Known failure modes: replica lag, gap-lock deadlocks, online-DDL surprises, and the isolation anomalies above. **Jepsen result exists** and is unflattering on isolation-level naming ([Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34)).

## Ecosystem & people
- **Canonical use cases:** general-purpose OLTP, web/SaaS backends, WordPress/Drupal/the LAMP stack, read-heavy workloads with replica fan-out. **Anti-patterns:** analytics/OLAP and large ad-hoc aggregations (use [clickhouse](clickhouse.md)/[duckdb](duckdb.md)/a warehouse); workloads needing genuine serializability out of the box (use [postgresql](postgresql.md) or test carefully); write-heavy workloads requiring transparent horizontal sharding (use Vitess/[cockroachdb](cockroachdb.md)/[tidb](tidb.md)).
- **Drivers / ORMs / connectors:** universal driver coverage (JDBC, Python, Go, Node, PHP); every major ORM; first-class CDC via binlog (Debezium, Maxwell); dbt, Kafka Connect, all BI tools.
- **Community & support:** huge community, abundant talent (low learning curve, small teams can run it), excellent docs. Commercial support from Oracle (MySQL Enterprise) and third parties (Percona). Forks shift the politics: [mariadb](mariadb.md) (community fork, diverging) and [percona-server-for-mysql](percona-server-for-mysql.md) (drop-in, extra observability/features) are alternatives to Oracle's distribution.

## Licensing & cost
- **OSS license & flavor:** **dual-licensed** — MySQL Community Edition under **GPLv2** (copyleft), and a separate **Oracle commercial license** for those who can't accept GPL (e.g., embedding in closed-source products). Client libraries also fall under GPL with the FOSS License Exception. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable. Managed options: Oracle MySQL HeatWave (HeatWave columnar engine is managed-only), AWS RDS/Aurora MySQL, Google Cloud SQL, Azure, PlanetScale. **Lock-in risk** comes mainly from cloud-proprietary layers (Aurora storage, HeatWave) rather than core MySQL.
- **Cost model:** core software free (GPL). Costs are operational/managed-service (per-instance/per-core/per-GB on clouds) or commercial-license/support fees from Oracle. Cheap at small scale; cloud-managed cost scales with instances + storage + IOPS.

## Hardware / deployment
- **Resource profile:** memory-sensitive — performance is dominated by the **InnoDB buffer pool** (cache hot working set in RAM); the full dataset need not fit in RAM, but the working set should. CPU matters for concurrent OLTP; can be I/O-bound on cold/write-heavy workloads.
- **Storage assumptions:** happiest on **local NVMe/SSD**; tolerates network-attached storage (EBS, Aurora) with tuning. fsync latency directly affects commit latency in the durable config.
- **Footprint:** single-node by default; **clustered** via Group Replication/InnoDB Cluster or NDB Cluster; **not embedded** (it's a server process — contrast [sqlite](sqlite.md)/[duckdb](duckdb.md)).
- **Deployment:** runs on-prem, VMs, containers, and Kubernetes (operators exist: Oracle's MySQL Operator, Percona Operator, Vitess); StatefulSet realities (stable storage, careful failover) apply as with any stateful DB.

## Bottom line
Reach for MySQL when you want a proven, low-friction OLTP database with the deepest talent pool and ecosystem on earth, and your scaling story is "big primary + read replicas" or Vitess. Avoid it for analytics, and be skeptical of the isolation-level labels: the single biggest gotcha is that **default REPEATABLE READ is demonstrably weaker than its name** ([Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34)) — design for it with explicit locking, or prefer [postgresql](postgresql.md) if you want correctness guarantees that match their labels.

## Sources
- [MySQL 8.4 Reference Manual — Transaction Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)
- [MySQL 8.4 Reference Manual — InnoDB Locking (gap/next-key locks)](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)
- [Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34)
- [MySQL — Group Replication consistency guarantees](https://dev.mysql.com/doc/refman/8.4/en/group-replication-configuring-consistency-guarantees.html)
- [MySQL — XCom / Paxos-based consensus](https://dev.mysql.com/blog-archive/the-king-is-dead-long-live-the-king-our-homegrown-paxos-based-consensus/)
- [MySQL 8.4 Reference Manual — InnoDB Cluster](https://dev.mysql.com/doc/refman/8.4/en/mysql-innodb-cluster-introduction.html)
