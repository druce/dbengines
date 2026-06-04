---
name: MariaDB
slug: mariadb
rank: 13
data_model: Relational (multi-model via pluggable storage engines)
license: GPLv2 (server); client libs LGPLv2.1; some add-on tools BSL/source-available
summary: GPLv2 fork of MySQL with a pluggable-engine architecture and active-active Galera clustering — but Jepsen found Galera far weaker than its claimed isolation.
last_researched: 2026-06-04
confidence: high
---

# MariaDB

> A community-governed, drop-in MySQL fork that stays GPLv2 forever and adds pluggable storage engines (Aria, ColumnStore) and multi-primary Galera clustering — but its distributed mode delivers far less consistency than it advertises ([Jepsen 12.1.2, 2026](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2)).

## Identity
- **Taxonomy / data model:** primarily relational; multi-model in the [mysql](mysql.md) tradition via pluggable storage engines (InnoDB for OLTP, Aria for crash-safe non-transactional, ColumnStore for columnar OLAP, Spider for sharding, plus native JSON functions, computed columns, and a system-versioned "temporal" tables feature).
- **Storage model:** default **InnoDB** is a row-store on a clustered B+tree ([lsm-vs-btree](../concepts/lsm-vs-btree.md)); **Aria** is row-store/heap (MyISAM successor, crash-safe but not ACID by default); **ColumnStore** is true columnar with extent-map storage for OLAP. On-disk format is InnoDB-compatible but has diverged from MySQL since ~5.7.
- **Workload:** OLTP by default (InnoDB). HTAP is offered but **physically separated, not unified**: ColumnStore runs as a separate columnar engine/cluster and MaxScale routes OLTP queries to InnoDB servers and OLAP queries to ColumnStore. There is no single unified store serving both. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **Single-node InnoDB:** CP-style ACID on one node; CAP is N/A for a single instance.
- **Galera Cluster (multi-primary):** ⚠️ The marketing claims an isolation level "between Serializable and Repeatable Read," "no replica lag," and "no lost transactions." [Jepsen's March 2026 analysis of 12.1.2](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) found the opposite: even in **healthy clusters** it exhibited **Lost Update (P4)** (MDEV-38977), **G-single** cycles, and **Stale Reads** (acknowledged committed transactions becoming invisible, every few minutes; MDEV-38999) — providing **neither Snapshot Isolation nor Repeatable Read**. All four reported issues were unresolved at report time. See [isolation-levels](../concepts/isolation-levels.md).
- **CAP under partition:** Galera is quorum-based — a minority partition goes "non-Primary" and stops serving (CP-leaning availability), but [Jepsen](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) (testing 12.1.2 **through 12.2.2**) found it **lost committed transactions** under coordinated process crashes when run with the documented "safer, recommended" setting `innodb_flush_log_at_trx_commit=0` (MDEV-38974); switching to `=1` significantly reduced but **did not eliminate** loss under crashes + network partitions (MDEV-38976). So neither C nor full durability is actually guaranteed as claimed. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition, minority side refuses writes (toward C/consistency); else (normal operation) Galera adds commit-time certification latency but provides weaker-than-snapshot isolation — effectively trading latency without delivering the consistency the latency would imply.
- **Default isolation:** InnoDB default is **REPEATABLE READ** ([MariaDB docs](https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/migrating-to-mariadb/migrating-to-mariadb-from-sql-server/mariadb-transactions-and-isolation-levels-for-sql-server-users)); SERIALIZABLE available. Newer `--innodb-snapshot-isolation=true` makes REPEATABLE READ abort on write/write conflicts to actually prevent Lost Update ([Jepsen blog, 2024](https://jepsen.io/blog/2024-11-07-mariadb-snapshot-isolation)) — but Jepsen still found anomalies in Galera. Treat "ACID" claims for Galera with skepticism; for single-node InnoDB they hold under default RR (with the usual RR caveats — see [mvcc](../concepts/mvcc.md)).
- **Replication:** (1) classic **single-leader async/semi-sync** binlog replication ([replication-models](../concepts/replication-models.md)); semi-sync only guarantees a replica *received* the event, not applied it. (2) **Galera** = "virtually synchronous," certification-based multi-primary replication. Failover via quorum; split-brain prevented by odd node count + quorum (minority goes non-Primary).
- **Tunable consistency?** Per-session isolation level and `wsrep_sync_wait` (causal-read enforcement) in Galera; binlog replicas can serve stale reads.
- **Clock dependency:** does not rely on synchronized clocks for correctness ([clocks-and-time](../concepts/clocks-and-time.md)); no TrueTime/HLC requirement.

## Schema
- **Schema-on-write**, rigid relational schema. JSON stored as LONGTEXT with JSON functions (not a native binary type as in MySQL 5.7+); dynamic columns offer a semi-structured escape hatch.
- **Migration:** supports online DDL for many `ALTER` operations via InnoDB; some `ALTER`s still copy/lock the table. Tools like `gh-ost`/`pt-online-schema-change` commonly used for large tables.
- **Type system:** standard SQL types plus native **IPv4/IPv6 (INET4/INET6)**, UUID type, geospatial (OpenGIS), computed/virtual columns, system-versioned (temporal) tables, and JSON functions. Native **VECTOR type with a VECTOR INDEX** (modified HNSW; `VEC_DISTANCE_EUCLIDEAN/COSINE` functions) is in mainline — GA since 11.7 ([MariaDB 11.7 GA with Vector Search](https://mariadb.com/resources/blog/announcing-mariadb-community-server-11-7-ga-with-vector-search-and-mariadb-community-server-11-8-rc/), [Vector Overview docs](https://mariadb.com/docs/server/reference/sql-structure/vectors/vector-overview)).

## Query interface
- **Language:** SQL, MySQL-compatible dialect (drop-in for most MySQL apps); adds CTEs, window functions, `RETURNING`, sequences, and Oracle-compatibility mode (`sql_mode=ORACLE` with PL/SQL-like syntax).
- **Transactions:** full multi-statement ACID on InnoDB; Aria/MyISAM are non-transactional. DDL is not transactional (implicit commit).
- **Native:** secondary indexes, joins, aggregations, window functions all native and server-side.
- **Stored procedures / UDFs:** SQL/PSM stored procedures, triggers, events; UDFs in C/C++; Oracle PL/SQL subset in Oracle mode.

## Scaling & topology
- **Vertical first.** Horizontal scaling via: read replicas (async binlog), Galera (multi-primary, but write throughput does not scale — every node certifies every write), Spider engine (manual sharding by federating tables across servers), or formerly **Xpand** distributed SQL (auto-sharded, shared-nothing, strongly consistent — but **Xpand is discontinued**).
- **Resharding:** Spider/manual sharding is operationally painful; Galera does not shard at all.
- **Read replicas:** async replicas can return stale data; Galera nodes can be made causal via `wsrep_sync_wait`.
- **Storage/compute separation:** not in mainline server; SkySQL managed service and ColumnStore (S3-backed object storage option) offer partial separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** InnoDB redo log (WAL) + doublewrite buffer; `innodb_flush_log_at_trx_commit` controls fsync (1 = fsync each commit, 0/2 = up to ~1s data-loss window). ⚠️ Galera docs historically recommended `=0` as "safe," which [Jepsen](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) showed causes committed-transaction loss on coordinated crashes — a real data-loss gotcha. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** strong single-node OLTP; Galera adds certification round-trip latency at commit and does **not** scale write throughput (all nodes apply all writes). Large transactions and hotspots cause certification conflicts/rollbacks that hurt p99.
- **Compaction/GC:** InnoDB purge threads reclaim old MVCC versions; long-running transactions bloat the undo log/history list and degrade p99 (classic InnoDB pitfall, same as [mysql](mysql.md)).

## Operations & maturity
- **Backup/restore:** `mariadb-backup` (physical, hot), `mariadb-dump` (logical), binlog-based PITR, snapshots. Galera supports SST/IST for node provisioning.
- **Observability:** EXPLAIN/ANALYZE query plans, slow query log, performance_schema, optional Query Response Time plugin.
- **Upgrade:** rolling upgrades supported (replicas first; Galera rolling node upgrades). Day-2 burden moderate; Galera operations (SST storms, flow control, certification conflicts) raise the bar.
- **Maturity:** very mature fork (since 2009), huge production base, packaged as default MySQL in many Linux distros (RHEL, Debian). **Known failure modes:** Galera write-conflict rollbacks, SST cluster stalls, and the documented isolation/durability gaps. **Jepsen results exist and are damning for Galera:** [12.1.2 (2026)](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) found lost updates, stale reads, and lost committed transactions; [2024 snapshot-isolation blog](https://jepsen.io/blog/2024-11-07-mariadb-snapshot-isolation) covers the `innodb-snapshot-isolation` work. All four 12.1.2 issues were unresolved at report time.

## Ecosystem & people
- **Canonical use cases:** drop-in MySQL replacement for OLTP web/app backends; teams wanting a GPLv2-governed, non-Oracle MySQL; WordPress/CMS/LAMP stacks; HA via Galera where the consistency bar is modest.
- **Anti-patterns:** financial/correctness-critical workloads on Galera multi-primary (use single-leader with `innodb-snapshot-isolation` or a strongly-consistent distributed SQL like [cockroachdb](cockroachdb.md)/[tidb](tidb.md) instead); write-scaling via Galera (it does not scale writes); heavy OLAP on InnoDB (use ColumnStore or a real warehouse).
- **Drivers/connectors:** MySQL-protocol compatible — works with virtually all MySQL drivers/ORMs, plus MariaDB Connectors (C/J/ODBC/Python/Node). CDC via binlog (Debezium, Maxwell); dbt, Kafka, BI tools all supported.
- **Community/support:** governed by the MariaDB Foundation (server) and commercially by MariaDB plc; strong docs, large community, multiple commercial support vendors. Low learning curve for anyone who knows MySQL.

## Licensing & cost
- **MariaDB Server: GPLv2** — and the project commits it stays GPLv2 forever; the BSL applies only to some add-on commercial products, not the server ([MariaDB BSL FAQ](https://mariadb.com/bsl-faq-mariadb/), [licensing FAQ](https://mariadb.com/docs/general-resources/community/community/faq/licensing-questions/licensing-faq)). Client libraries are LGPLv2.1.
- **Source-available add-ons:** MaxScale shipped under the **Business Source License (BSL)** (free non-prod, auto-converts to GPLv2 after ~4 years). MaxScale 21.06 reverted to GPLv2 on its change date in June 2024, but newer MaxScale releases (e.g. 24.08) ship under BSL again with their own future change dates ([MaxScale licensing overview, MariaDB.org 2024](https://mariadb.org/wp-content/uploads/2024/10/MaxScale-Overview.pdf)). This is a notable post-2018 source-available pattern — see [license-taxonomy](../concepts/license-taxonomy.md). Server itself is unaffected.
- **Self-managed vs managed:** self-host the GPLv2 server freely; **SkySQL** is the managed cloud offering (spun out as an independent company in Dec 2023, then re-acquired by MariaDB plc in Aug 2025 and folded into MariaDB Cloud). **Lock-in risk** is low for the core server (true MySQL-protocol compatibility), higher if you adopt proprietary tooling (MaxScale enterprise features, former Xpand).
- **Cost model:** OSS server free; commercial subscriptions per-server/per-core; managed SkySQL per-instance. Galera adds node cost without write-throughput benefit, so it can be expensive for the consistency it (under-)delivers.

## Hardware / deployment
- **Resource profile:** InnoDB is memory-sensitive (buffer pool should hold the hot working set) and disk-I/O bound on writes; CPU matters for Galera certification. Working set need not fully fit RAM but performance degrades sharply if the buffer pool is too small.
- **Storage assumptions:** NVMe/SSD strongly preferred for OLTP; tolerates network-attached storage (EBS) with higher fsync latency. ColumnStore can use S3-style object storage.
- **Footprint:** single-node, async-replicated, or Galera-clustered; not embedded. Server daemon model.
- **Deployment:** on-prem or any cloud; SkySQL SaaS; good container/k8s story (official images, MariaDB Operator for StatefulSets) though stateful clustering carries the usual k8s caveats.

## Bottom line
Reach for MariaDB when you want a mature, genuinely-GPLv2, non-Oracle MySQL for single-node or read-replicated OLTP — it is an excellent drop-in with extra features (window functions, temporal tables, Oracle mode, pluggable engines). Do **not** reach for Galera multi-primary expecting the "between Serializable and Repeatable Read, no lost transactions" guarantees it advertises: [Jepsen (2026)](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) found lost updates, stale reads, and lost committed transactions even in healthy clusters, and the docs' "safe" durability setting actively enables data loss. The single biggest gotcha: Galera's advertised consistency and the reality diverge sharply — and it scales reads, not writes.

## Sources
- [Jepsen: MariaDB Galera Cluster 12.1.2 (March 2026)](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2)
- [Jepsen blog: MariaDB Snapshot Isolation (2024)](https://jepsen.io/blog/2024-11-07-mariadb-snapshot-isolation)
- [MariaDB docs: Transactions and Isolation Levels](https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/migrating-to-mariadb/migrating-to-mariadb-from-sql-server/mariadb-transactions-and-isolation-levels-for-sql-server-users)
- [MariaDB docs: Storage Engines Overview](https://mariadb.com/docs/server/server-usage/storage-engines/storage-engines-storage-engines-overview)
- [MariaDB docs: What is MariaDB Galera Cluster](https://mariadb.com/docs/galera-cluster/readme/mariadb-galera-cluster-guide)
- [MariaDB docs: ColumnStore Architectural Overview](https://mariadb.com/docs/analytics/mariadb-columnstore/architecture/columnstore-architectural-overview)
- [MariaDB BSL FAQ](https://mariadb.com/bsl-faq-mariadb/)
- [MariaDB Licensing FAQ](https://mariadb.com/docs/general-resources/community/community/faq/licensing-questions/licensing-faq)
- [MariaDB.org: a true open source project](https://mariadb.org/mariadb-true-open-source-project/)
