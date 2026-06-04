---
name: Apache Derby
slug: apache-derby
rank: 91
data_model: Relational
license: Apache License 2.0 (permissive)
summary: Pure-Java embeddable SQL database, now a retired (read-only) project; fine for tests and small apps, wrong for production scale.
last_researched: 2026-06-04
confidence: high
---

# Apache Derby

> A 100% Java, zero-install embeddable relational database (also shipped by Oracle as Java DB) — handy for unit tests, demos, and small desktop apps, but the project was retired to read-only status in October 2025 and should not anchor new production systems.

## Identity
- **Taxonomy / data model:** single-node relational SQL database, implemented entirely in Java. Embeds in any JVM via its JDBC driver; also runs as a standalone Network Server. ([Apache Derby](https://db.apache.org/derby/))
- **Storage model:** row-store, B+-tree primary/secondary indexes; heap-organized tables stored in page-based "containers" (one file per conglomerate) with header, data, and allocation pages. Disk-based by default, with an in-memory backend option. See [lsm-vs-btree](../concepts/lsm-vs-btree.md) (Derby is firmly B-tree, not LSM). ([dbdb.io](https://dbdb.io/db/derby))
- **Workload:** OLTP-oriented, low-concurrency. Not an analytics engine and not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Designed for embedded single-user / low-concurrency use, e.g. desktop apps and test harnesses. ([Apache Derby](https://db.apache.org/derby/))

## Distribution & consistency
- **CAP under partition:** N/A — single-node engine; not a distributed datastore. See [cap-pacelc](../concepts/cap-pacelc.md). The optional master/slave log-shipping replication (below) is a warm-standby, not a partition-tolerant cluster.
- **PACELC:** N/A — single-node.
- **Default isolation & what's achievable:** lock-based (no [mvcc](../concepts/mvcc.md)); default is **Read Committed** (Derby's "CS" / cursor stability). All four JDBC levels are supported: Read Uncommitted (UR), Read Committed (CS, default), Repeatable Read (RS), Serializable (RR). Serializable is real serializability enforced via range/predicate locks, not snapshot isolation. ([Configuring isolation levels](https://db.apache.org/derby/docs/10.9/devguide/cdevconcepts22300.html), [Locking, concurrency, and isolation](https://db.apache.org/derby/docs/10.11/devguide/cdevconcepts30291.html)) See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** optional single-master → single-slave **log shipping**; the master streams log records over a TCP connection, the slave redoes them, and on master failure the slave completes recovery and can be promoted. Asynchronous; no automatic failover, no quorum, no multi-master. See [replication-models](../concepts/replication-models.md). ([Replicating databases](https://db.apache.org/derby/docs/10.4/adminguide/cadminreplication.html))
- **Tunable consistency?** Per-connection/per-statement isolation level only (the four JDBC levels). No Dynamo-style quorum tuning.
- **Clock dependency:** none — no distributed clock requirement. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; `CREATE TABLE` with typed columns enforced at write time.
- **Migration/evolution:** supports `ALTER TABLE ADD/DROP COLUMN`, add/drop constraints, etc. DDL is transactional but acquires table locks; ⚠️ unverified — no dedicated online/non-blocking DDL feature, so `ALTER` on a large busy table blocks concurrent access.
- **Type system:** standard SQL types (INTEGER, DECIMAL, VARCHAR, CHAR, DATE, TIME, TIMESTAMP, BLOB, CLOB, BOOLEAN). No native JSON, no array, no geospatial, no vector types. Stored Java objects only via user-defined functions/procedures, not as a column type.

## Query interface
- **Language:** SQL — a core subset of SQL-92 plus selected SQL-99 features, accessed through JDBC (embedded driver `org.apache.derby.jdbc.EmbeddedDriver` or client driver over the Network Server). ([Derby and standards](https://db.apache.org/derby/docs/10.6/devguide/cdevstandards806118.html), [dbdb.io](https://dbdb.io/db/derby))
- **Transactions:** full multi-statement ACID; standard JDBC commit/rollback and savepoints. Strict two-phase locking. ([dbdb.io](https://dbdb.io/db/derby))
- **Native vs app-side:** native joins, aggregations, subqueries, views, secondary indexes, foreign keys, check constraints. Window functions and some advanced SQL are limited/absent (⚠️ unverified — exact window-function coverage varies by version).
- **Stored procedures / UDFs:** yes — written in **Java** and registered to SQL via `CREATE PROCEDURE` / `CREATE FUNCTION`. No PL/SQL-style procedural SQL language.

## Scaling & topology
- **Vertical vs horizontal:** vertical only. No sharding, no partitioning across nodes, no auto-rebalancing.
- **Read replicas:** the master/slave replica is for failover/standby only; per the official docs the slave processes no transactions, "not even read operations," so it cannot serve live read traffic during normal replication. ([Replicating databases](https://db.apache.org/derby/docs/10.4/adminguide/cadminreplication.html))
- **Storage/compute separation:** none — embedded engine sharing the application JVM's process and local files. See [storage-compute-separation](../concepts/storage-compute-separation.md) (does not apply).

## Performance & durability
- **Write path:** Write-Ahead Logging with page-level physical logging and fuzzy checkpointing; recovery locates the latest checkpoint and replays log for redo/undo. fsync-on-commit is the durable default; durability can be relaxed for speed (e.g. the `derby.system.durability=test` mode trades crash-safety for throughput and can lose committed data on crash). See [wal-and-durability](../concepts/wal-and-durability.md). ([dbdb.io](https://dbdb.io/db/derby), [Configuring Derby for Performance and Durability](https://db.apache.org/derby/binaries/DerbyPerfDurability-2006.pdf))
- **Throughput/latency:** adequate for single-user / small-team workloads and embedded use; it is not built for high concurrency or large datasets, and throughput degrades under contention because of lock-based concurrency (no MVCC means readers and writers block each other at higher isolation levels). ⚠️ unverified — no authoritative p99 benchmarks; treat performance as "good enough for small apps, not for scale."
- **Compaction / vacuum / GC:** space from deleted rows is reclaimed lazily; the `SYSCS_UTIL.SYSCS_COMPRESS_TABLE` / `SYSCS_INPLACE_COMPRESS_TABLE` procedures reclaim/compact table storage on demand. No background autovacuum daemon.

## Operations & maturity
- **Backup/restore:** online backup via `SYSCS_UTIL.SYSCS_BACKUP_DATABASE` (read traffic continues, updates briefly blocked); restore by copying the backup. Roll-forward recovery is supported when archive logging is enabled. ([Backing up and restoring databases](https://db.apache.org/derby/docs/10.1/adminguide/cadminhubbkup98797.html))
- **Observability:** JDBC metadata, `derby.log`, optional statement logging and runtime-statistics / `EXPLAIN`-style query plan capture (`derby.language.logQueryPlan`, RUNTIMESTATISTICS). No modern metrics/Prometheus integration.
- **Upgrade story:** in-place database upgrade across Derby versions via the `upgrade=true` connection attribute; no rolling-cluster concept (single node). Day-2 burden is low precisely because there is little to operate — but also little to tune.
- **Maturity:** very mature codebase (descended from IBM Cloudscape; donated to Apache in 2004) and was redistributed by Sun/Oracle as **Java DB** bundled with the JDK through Java 8. **Project status: retired.** Final release **10.17.1.0** (Nov 2023, adds Java SE 21 support); on **Oct 10, 2025** the developers voted to move the project to read-only — development, bug-fixing, and releases have ended, JIRA is read-only, and mailing lists are archived. ([Apache Derby Downloads](https://db.apache.org/derby/derby_downloads.html), [Grokipedia: Apache Derby](https://grokipedia.com/page/Apache_Derby)) No public Jepsen report exists (single-node engine; Jepsen targets distributed systems).

## Ecosystem & people
- **Canonical use cases:** embedded storage for Java desktop/CLI apps, unit/integration test databases (drop-in for "real SQL" in tests), prototyping, teaching, and small departmental apps. Zero install, single jar, starts in-process.
- **Anti-patterns:** anything needing high write concurrency, large data volumes, horizontal scale, analytics, HA with automatic failover, or non-JVM clients as first-class citizens. **Biggest anti-pattern now: choosing it for a new long-lived production system given the project is retired** — prefer [sqlite](sqlite.md), [h2](h2.md), [hypersql](hypersql.md), or [postgresql](postgresql.md) depending on needs.
- **Drivers / connectors:** JDBC only (embedded + network client); usable from any JVM language and via ORMs like Hibernate. No native CDC, no Kafka connector, limited BI/dbt support. Non-JVM access requires the Network Server.
- **Community:** small and now effectively dormant; documentation is thorough but frozen. Learning curve is shallow for any Java developer who knows JDBC/SQL.

## Licensing & cost
- **OSS license:** Apache License 2.0 — permissive, no copyleft, no post-2018 relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** self-managed/embedded only; no vendor SaaS. (Oracle's "Java DB" was the same code, also free.)
- **Lock-in:** minimal — standard SQL/JDBC; ⚠️ Java-only runtime is the main constraint, plus the absence of ongoing security patches now that the project is retired.
- **Cost model:** free; cost is purely the host JVM/process it embeds into.

## Hardware / deployment
- **Resource profile:** lightweight; runs in the application's JVM heap plus a configurable page cache. Working set need not fit entirely in RAM (it is disk-backed), but performance is best when hot pages are cached.
- **Storage assumptions:** local filesystem; no special NVMe or network-storage requirements. Also supports a fully in-memory database for ephemeral/test use.
- **Footprint:** embedded (single jar, in-process) — the SQLite/H2 niche for the JVM — or a small standalone Network Server process.
- **Deployment:** on-prem / in-app only; no first-class k8s/StatefulSet story (you'd run it as a sidecar process or, more typically, embedded in your service).

## Bottom line
Reach for Apache Derby only when you need a pure-Java, zero-install SQL database inside a JVM application or test suite and your workload is small and low-concurrency. Do not use it for production systems at scale, high write concurrency, analytics, or anything needing HA — and given the project went read-only in October 2025 (no further releases or security fixes), strongly prefer actively-maintained embeddable alternatives like [h2](h2.md), [hypersql](hypersql.md), or [sqlite](sqlite.md) for new work. The single biggest gotcha: it is now an end-of-life project, so any production reliance is a standing, unpatched risk.

## Sources
- [Apache Derby home](https://db.apache.org/derby/)
- [Apache Derby downloads / release history](https://db.apache.org/derby/derby_downloads.html)
- [Configuring isolation levels (devguide)](https://db.apache.org/derby/docs/10.9/devguide/cdevconcepts22300.html)
- [Locking, concurrency, and isolation (devguide)](https://db.apache.org/derby/docs/10.11/devguide/cdevconcepts30291.html)
- [Derby and standards (SQL compliance)](https://db.apache.org/derby/docs/10.6/devguide/cdevstandards806118.html)
- [Replicating databases (admin guide)](https://db.apache.org/derby/docs/10.4/adminguide/cadminreplication.html)
- [Backing up and restoring databases (admin guide)](https://db.apache.org/derby/docs/10.1/adminguide/cadminhubbkup98797.html)
- [Configuring Derby for Performance and Durability (Sandstå, 2006)](https://db.apache.org/derby/binaries/DerbyPerfDurability-2006.pdf)
- [Database of Databases — Derby](https://dbdb.io/db/derby)
- [Grokipedia — Apache Derby (project retirement)](https://grokipedia.com/page/Apache_Derby)
