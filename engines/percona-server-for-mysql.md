---
name: Percona Server for MySQL
slug: percona-server-for-mysql
rank: 129
data_model: Relational
license: GPLv2 (copyleft, open source)
summary: Drop-in MySQL fork that bundles MySQL Enterprise-equivalent features (audit, thread pool, encryption, MyRocks) for free, plus deeper instrumentation.
last_researched: 2026-06-04
confidence: high
---

# Percona Server for MySQL

> A free, GPL drop-in replacement for Oracle MySQL Community Edition that adds enterprise-grade observability, security, and an LSM storage engine (MyRocks) without per-core licensing — but it is still single-node MySQL, with the same replication and consistency caveats.

## When to use

**Use Percona Server for MySQL if:**
- ✅ You run MySQL in production and want Enterprise-tier features (audit log, thread pool, encryption, PAM auth, hot non-blocking XtraBackup) for free under GPL
- ✅ You have write-heavy or storage-cost-sensitive data that benefits from the MyRocks LSM engine's low write amplification
- ✅ You want deeper MySQL instrumentation — per-table/index/user/thread stats, extended slow-query log, PMM dashboards
- ✅ You want to avoid Oracle per-core licensing with a 100% wire-compatible drop-in (every MySQL driver, ProxySQL, Debezium works unchanged)

**Avoid Percona Server for MySQL if:**
- ❌ You expect synchronous multi-master HA from plain Percona Server — that requires the separate Percona XtraDB **Cluster** product; this engine has MySQL's ordinary async replication and split-brain risk
- ❌ You need analytical/OLAP workloads — no columnar engine; use ClickHouse or a warehouse
- ❌ You need automatic failover or built-in sharding — both require external tooling (Orchestrator, ProxySQL, Vitess)
- ❌ You rely on InnoDB REPEATABLE READ being true snapshot isolation — Jepsen found MySQL's RR permits lost updates, write skew, and read skew

## Identity
- **Taxonomy / data model:** relational, SQL. A near-source-compatible fork of upstream Oracle [mysql](mysql.md), tracking the same major versions (8.0, 8.4). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** default engine is **Percona XtraDB**, an enhanced InnoDB (B-tree / clustered-index row store, [lsm-vs-btree](../concepts/lsm-vs-btree.md), [mvcc](../concepts/mvcc.md)). Also ships **MyRocks** (RocksDB-based LSM engine) for write-heavy, space-constrained workloads ([Percona docs](https://docs.percona.com/percona-server/8.0/feature-comparison.html)). TokuDB was deprecated and removed in 8.0 ([changed-in-version notes](https://docs.percona.com/percona-server/8.0/changed_in_version.html)).
- **Workload:** OLTP. Not HTAP — no columnar engine; analytics rely on read replicas or external warehouses, same as upstream MySQL.

## Distribution & consistency
- **CAP under partition:** inherits MySQL's model. A single node is CP-trivial; async replication topologies are effectively **AP-leaning** (replicas can lag/serve stale reads, no automatic quorum). For a true CP cluster, pair with [Percona XtraDB Cluster](percona-server-for-mysql.md) / Galera (synchronous, [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)-adjacent certification) — that is a separate product, not this engine. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** as deployed with default async replication — **PA/EL**: tolerates partition by letting replicas diverge, and in normal operation favors latency (async commit to replicas) over consistency. Semi-sync replication shifts the else-case toward consistency at a latency cost.
- **Default isolation & what's achievable:** InnoDB/XtraDB defaults to **REPEATABLE READ** (snapshot via MVCC, with next-key locking to limit phantoms); READ COMMITTED and SERIALIZABLE are available. "ACID" here is real at the single-node InnoDB level, but note that InnoDB's RR is *not* true snapshot isolation: Jepsen's analysis of upstream MySQL 8.0.34 (whose InnoDB semantics Percona Server tracks) found RR substantially weaker than its name implies — it permits lost updates, write skew (G2-item), read skew (G-single), and non-repeatable reads ([Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34)). Even SERIALIZABLE was found violable on RDS under non-default settings. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** single-leader binlog replication, async by default; **semi-synchronous** optional. Multi-source replication supported. Failover is not automatic — needs external tooling (Orchestrator, MHA, ProxySQL). Split-brain is possible with naive promotion. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels (not a Dynamo-style system). You choose async vs semi-sync at the topology level.
- **Clock dependency:** none for correctness (GTIDs are logical, not clock-based). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; `CREATE/ALTER TABLE` enforced.
- **Migration / online DDL:** InnoDB online DDL (many ALTERs are in-place/concurrent in 8.0); for the rest, teams typically use `pt-online-schema-change` or `gh-ost` to avoid long locks. Percona adds the original `pt-osc` tooling in its Toolkit.
- **Type system:** full MySQL types — native JSON, generated columns, spatial/geospatial (GIS), full-text indexes. No native vector type in the 8.0/8.4 LTS lines that Percona Server tracks: Oracle added the `VECTOR` type in MySQL **9.0** (the Innovation track), not 8.4 ([MySQL VECTOR docs](https://dev.mysql.com/doc/refman/9.7/en/vector.html)), and Percona Server has no 9.x release as of mid-2026.

## Query interface
- **Language:** SQL (MySQL dialect; broadly SQL:standard-compatible with MySQL extensions).
- **Transactions:** full multi-statement ACID on InnoDB/XtraDB; MyRocks supports transactions but with engine-specific limitations (e.g., gap-lock semantics differ).
- **Native vs app-side:** native joins, subqueries, window functions, CTEs (8.0+), aggregations, secondary indexes.
- **Stored procedures / UDFs:** SQL stored procedures/functions/triggers; UDFs in C/C++. Plus Percona-specific UDFs and extra `INFORMATION_SCHEMA` tables (95 vs MySQL's ~65) for diagnostics ([feature comparison](https://docs.percona.com/percona-server/8.0/feature-comparison.html)).

## Scaling & topology
- **Vertical first:** scales up on a single primary. Horizontal write scaling requires app-side sharding (Vitess, ProxySQL routing) or moving to a cluster product.
- **Sharding:** no built-in auto-sharding; manual/app-managed. Resharding is painful, as with all vanilla MySQL.
- **Read replicas:** binlog read replicas; reads are **eventually consistent** by default (replication lag), unless using semi-sync + read-after-write routing.
- **Storage/compute separation:** none — local storage, monolithic node. See [storage-compute-separation](../concepts/storage-compute-separation.md) for the contrast.

## Performance & durability
- **Write path:** InnoDB redo log (WAL) + binlog; `innodb_flush_log_at_trx_commit=1` + `sync_binlog=1` gives durable commit (data-loss window ≈ 0 on crash); relaxing those trades a small loss window for throughput. Group commit reduces fsync cost. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput / latency:** XtraDB adds buffer-pool mutex splitting, improved flushing, and extra tunables aimed at high-concurrency p99 stability vs stock InnoDB. MyRocks gives much lower write amplification and smaller on-disk footprint for write-heavy data, at the cost of read/range overhead typical of LSM.
- **Compaction / GC:** XtraDB uses InnoDB purge (history-list cleanup for MVCC); long-running transactions bloat the history list and hurt p99. MyRocks has LSM compaction with its own stall/p99 characteristics.

## Operations & maturity
- **Backup/restore, PITR:** **Percona XtraBackup** (free, hot, non-blocking physical backup) is the flagship companion; **backup locks** (`LOCK TABLES FOR BACKUP`) avoid the global read lock. Binlog-based PITR. ([feature comparison](https://docs.percona.com/percona-server/8.0/feature-comparison.html)).
- **Observability:** strongest selling point — per-table, per-index, per-user, per-thread statistics, extended slow-query log (with query plan/InnoDB stats), userstat, and Percona Monitoring and Management (PMM) for metrics/dashboards. EXPLAIN/optimizer same as MySQL.
- **Upgrade story:** in-place upgrade from MySQL CE or prior Percona versions; rolling upgrades via replication. Day-2 burden ≈ standard MySQL (replication management, schema-change tooling, backup ops).
- **Maturity:** very mature; widely run in production for 15+ years; Percona is a major MySQL support vendor. No Jepsen report targets Percona Server *by name*, but the relevant analyses cover its building blocks: Jepsen's [MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) report (the InnoDB engine Percona Server tracks) and Aphyr's [Percona XtraDB Cluster](https://aphyr.com/posts/328-jepsen-percona-xtradb-cluster) and [MariaDB Galera Cluster 12.1.2](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) reports (the synchronous-cluster path, i.e. [Percona XtraDB Cluster](percona-server-for-mysql.md)) — Galera was found to allow lost updates and lose committed transactions on crash. Known failure modes are MySQL's: replication lag, long-transaction history-list bloat, online-DDL edge cases.

## Ecosystem & people
- **Canonical use cases:** teams that want MySQL Enterprise-class features (audit logging, thread pool, encryption, PAM auth, hot backups) without Oracle licensing; write-heavy or storage-cost-sensitive workloads via MyRocks; anyone wanting deeper MySQL instrumentation.
- **Anti-patterns:** need for true synchronous multi-master HA (use [Percona XtraDB Cluster](percona-server-for-mysql.md) / [mariadb](mariadb.md) Galera or vitess); analytical/OLAP workloads (use [clickhouse](clickhouse.md), a warehouse); applications already happy on MySQL CE with no need for the extra features (less reason to switch).
- **Drivers / connectors:** 100% MySQL wire-protocol compatible — every MySQL driver/ORM, ProxySQL, [debezium](debezium.md) CDC, Kafka Connect, dbt, and BI tools work unchanged.
- **Community / support:** large MySQL ecosystem; Percona offers commercial support/managed services; docs are thorough and version-specific. Learning curve = MySQL.

## Licensing & cost
- **License:** **GPLv2**, fully open source, no source-available restrictions — notably it keeps as free/OSS several things Oracle gates behind MySQL **Enterprise** (audit log, thread pool, PAM, encryption extensions) ([Percona](https://www.percona.com/alternative-to-enterprise-mysql)). No post-2018 relicensing to SSPL/BSL. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-managed software is free; Percona monetizes support, consulting, and managed services. No feature paywall and minimal lock-in (drop-in compatible both directions with upstream MySQL, modulo Percona-only features like MyRocks/userstat).
- **Cost model:** software is $0; cost is hardware + optional support subscription. Scales cheaply because there is no per-core license; at large fleets, support/ops labor dominates.

## Hardware / deployment
- **Resource profile:** memory-bound for XtraDB (working set / hot pages should fit the InnoDB buffer pool); MyRocks is more disk/space-efficient and tolerant of larger-than-RAM datasets.
- **Storage assumptions:** local NVMe/SSD strongly preferred for redo+data; works on network-attached storage with latency penalty.
- **Footprint:** single-node server (clustered only via separate products). Not embedded, not serverless.
- **Deployment:** on-prem or any cloud VM; Docker images and the Percona Kubernetes Operator for MySQL provide k8s/StatefulSet deployment with automated backups and orchestration.

## Bottom line
Reach for Percona Server for MySQL when you run MySQL in production and want Enterprise-tier features — hot non-blocking backups, audit logging, thread pool, encryption, and far deeper instrumentation — for free under GPL, plus MyRocks for write-heavy or storage-constrained data. Do not reach for it expecting different distribution/consistency than MySQL: it is still single-leader async-replicated and needs external tooling for failover and sharding. Biggest gotcha: people conflate it with Percona XtraDB **Cluster** — only the Cluster product gives synchronous multi-master HA; plain Percona Server has MySQL's ordinary replication and split-brain risks.

## Sources
- [Percona Server feature comparison vs MySQL CE/Enterprise](https://docs.percona.com/percona-server/8.0/feature-comparison.html)
- [List of features by Percona Server version](https://docs.percona.com/percona-server/8.0/changed_in_version.html)
- [Percona XtraDB storage engine docs](https://docs.percona.com/percona-server/innovation-release/percona-xtradb.html)
- [Percona: alternative to Enterprise MySQL](https://www.percona.com/alternative-to-enterprise-mysql)
- [Percona Server for MySQL — Wikipedia](https://en.wikipedia.org/wiki/Percona_Server_for_MySQL)
- [Percona Server 8.4.8-8 release notes](https://docs.percona.com/percona-server/8.4/release-notes/8.4.8-8.html)
- [Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) (InnoDB isolation)
- [Jepsen: Percona XtraDB Cluster](https://aphyr.com/posts/328-jepsen-percona-xtradb-cluster) and [MariaDB Galera Cluster 12.1.2](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2)
- [MySQL VECTOR type (added in 9.0)](https://dev.mysql.com/doc/refman/9.7/en/vector.html)
