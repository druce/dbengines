---
name: Ingres
slug: ingres
rank: 88
data_model: Relational
license: Proprietary / source-available (Actian; GPL fork existed but is effectively abandoned)
summary: One of the original 1970s relational databases, now a single-node OLTP DBMS sold by Actian; mature and stable but a legacy choice.
last_researched: 2026-06-04
confidence: high
---

# Ingres

> A foundational 1970s relational DBMS — academic ancestor of [postgresql](postgresql.md) and others — that survives as Actian's single-node OLTP product: solid, conventional, and chosen mainly to keep decades-old applications running.

## Identity
- **Taxonomy / data model:** Relational (SQL, and historically QUEL — the query language [postgresql](postgresql.md)'s predecessor also used). Originated at UC Berkeley (Stonebraker/Wong, 1973), commercialized 1980, now owned by Actian. The "Actian X" brand (Ingres + Vector's X100 columnar engine, introduced 2017) was withdrawn in mid-2024; its hybrid capabilities were folded into the current **Actian Ingres 12.0** release (launched 2024-06-04) ([Actian press release](https://www.actian.com/company/press-releases/actian-launches-ingres-12-0-database/), [dbdb.io](https://dbdb.io/db/ingres), [Wikipedia](https://en.wikipedia.org/wiki/Ingres_(database))).
- **Storage model:** Disk-oriented row-store (N-ary storage model) by default. Actian Ingres bundles a second engine, **X100** (the columnar/vectorized engine from actian-vector), so a single database can hold both traditional row (Ingres) tables and X100 columnar tables and join across them in one query — row tables for OLTP, column tables for analytics ([Actian docs — Hybrid Transaction and Analytics Processing](https://docs.actian.com/actianingres/12.0/DatabaseAdmin/Hybrid.htm), [dbdb.io](https://dbdb.io/db/ingres)). See [lsm-vs-btree](../concepts/lsm-vs-btree.md) — Ingres is B-tree/ISAM-family, not LSM. On-disk default index structure is **ISAM**; B+tree, hash, and R-tree are also offered.
- **Workload:** Primarily OLTP. The HTAP ("Hybrid Transaction and Analytics Processing") story is physical engine separation *within one database*: OLTP runs on the classic row engine, analytics on the embedded X100/Vector columnar+vectorized engine over separately-declared columnar tables, with cross-engine joins supported in a single query ([Actian docs](https://docs.actian.com/actianingres/12.0/DatabaseAdmin/Hybrid.htm)). It is not a separate-replica topology; both engines share one instance. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). For serious analytics, actian-vector is the dedicated product.

## Distribution & consistency
- **CAP under partition:** N/A as a distributed quorum system — Ingres is a **single-node, shared-everything** DBMS ([dbdb.io](https://dbdb.io/db/ingres)). Cross-node replication is asynchronous (Ingres Replicator), so a multi-site deployment is effectively AP-leaning with eventual convergence, not a partition-tolerant CP cluster. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** On a single node, no partition tradeoff; latency/consistency is the local lock-vs-MVCC choice (below). With Replicator, the else-case is async lag (AP-style).
- **Default isolation & what's achievable:** Supports READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE. Under MVCC, READ UNCOMMITTED is silently promoted to READ COMMITTED (and forced read-only) and REPEATABLE READ is silently promoted to SERIALIZABLE ([Actian docs](https://docs.actian.com/ingres/12.0/DatabaseAdmin/Lock_Level_MVCC_and_Isolation_Levels.htm)). **Important divergence:** Ingres "SERIALIZABLE" under MVCC is implemented as transaction-start snapshot + first-committer-wins write conflict detection (error `E_US125B`, "unable to serialize", aborts the statement) — this is **snapshot isolation**, which permits write-skew, not true serializability. Read this as snapshot isolation, not serializable. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). (Without MVCC tables, Ingres falls back to two-phase locking with deadlock detection.)
- **Replication:** **Ingres Replicator** provides asynchronous, peer-to-peer / multi-master replication, and can also push to heterogeneous targets (Oracle, SQL Server, DB2) via Enterprise Access ([Wikipedia](https://en.wikipedia.org/wiki/Ingres_(database))). Failover/split-brain handling is left to the replication config and operator; there is no built-in consensus leader election. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Per-session/per-statement isolation levels and lock level (row/MVCC/page/table/database), but not Dynamo-style per-query quorum tuning.
- **Clock dependency:** No reliance on synchronized clocks for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write,** rigid relational schema enforced at write time.
- **Migration/evolution:** Conventional `ALTER TABLE` DDL; online/non-locking DDL is limited and version-dependent. ⚠️ unverified — extent of online (non-blocking) `ALTER` support in current releases not confirmed from primary docs.
- **Type system:** Standard SQL scalar types, dates/intervals, decimals, and BLOBs. ⚠️ unverified — native JSON / geospatial / vector type support is not clearly documented and should not be assumed; Ingres is a classic relational type system, not a modern multi-type engine.

## Query interface
- **Language:** SQL (its own dialect, broadly entry-level SQL-standard) plus the legacy **QUEL** language. Embedded SQL/QUEL for C, and OpenAPI C bindings ([dbdb.io](https://dbdb.io/db/ingres)).
- **Transactions:** Full multi-statement ACID.
- **Native vs app-side:** Native joins (optimizer picks nested-loop, hash, or sort-merge), secondary indexes, aggregations, and a cost-based query optimizer.
- **Stored procedures / UDFs:** Database procedures in Ingres's procedural SQL; row/statement triggers ("rules") supported.

## Scaling & topology
- **Vertical vs horizontal:** Primarily **vertical** (scale the single node). No native auto-sharding; horizontal scale-out is achieved by application partitioning + Ingres Replicator, not transparent distribution.
- **Sharding/partitioning:** Table partitioning is available for large tables; resharding is a manual, planned operation.
- **Read replicas:** Achieved via Replicator (asynchronous) — replicas may lag and are not guaranteed read-your-writes. ⚠️ unverified — synchronous read-replica option not confirmed.
- **Storage/compute separation:** No. Classic coupled storage+compute single node. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Write-ahead logging with a recovery/logging subsystem (transaction log + recovery process). Group commit and fsync behavior are tunable via DBMS configuration; the data-loss window on crash depends on commit/flush settings. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact default fsync/group-commit semantics not pulled from primary docs.
- **Throughput/latency:** Competent single-node OLTP throughput; mature, predictable engine. ⚠️ unverified — no recent public p99/tail benchmarks located; treat performance claims as workload-dependent.
- **Compaction/vacuum/GC:** MVCC version cleanup and periodic table reorganization/`modify` operations (e.g., to rebuild ISAM/B-tree structure) are part of routine maintenance; neglected tables degrade over time. ⚠️ unverified — p99 impact of version cleanup not separately documented.

## Operations & maturity
- **Backup/restore:** `ckpdb` (checkpoint), journaling, and rollforward/PITR-style recovery via the transaction log and journals.
- **Observability:** Query plans via the optimizer (`set qep` / explain-equivalent), logging/auditing facilities, and Visual DBA / command-line admin tools.
- **Upgrade story:** In-place version upgrades; rolling/zero-downtime upgrade is not a built-in feature for a single node. Day-2 burden is classic enterprise RDBMS administration — backups, journals, table reorgs.
- **Maturity:** Very mature (40+ years), stable, with a long production track record in government and enterprise back-office systems. **No public Jepsen report exists** for Ingres. Its main risk is ecosystem/skills decline, not engine instability.

## Ecosystem & people
- **Canonical use cases:** Maintaining and extending long-lived enterprise/government OLTP applications already built on Ingres; conventional single-node transactional workloads where stability matters more than scale-out.
- **Anti-patterns:** New greenfield projects (pick [postgresql](postgresql.md)); web-scale horizontal scale-out; cloud-native distributed/HA requirements; modern document/JSON/vector workloads. It is the wrong tool when you need an active community and a deep hiring pool.
- **Drivers/connectors:** ODBC, JDBC, .NET, OpenAPI/embedded SQL; Enterprise Access gateways to other DBMSs. Modern CDC/Kafka/dbt/BI integration is thin compared to mainstream engines.
- **Community/support:** Small community; commercial support from Actian. Documentation exists (Actian docs site) but the talent pool is shrinking and skewing legacy.

## Licensing & cost
- **OSS license & flavor:** Effectively **proprietary** today, sold by Actian. Ingres was open-sourced under CA (the "Ingres r3" GPL release) in the mid-2000s, but that lineage is effectively abandoned/unmaintained, and the current product is closed/commercial ([dbdb.io](https://dbdb.io/db/ingres)). Treat it as proprietary for planning. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-managed on-prem/VM primarily; Actian markets cloud deployment options. Lock-in via proprietary engine, QUEL, and Ingres-specific procedures.
- **Cost model:** Commercial per-deployment/per-core licensing from Actian (contact-sales). ⚠️ unverified — current list pricing/metric not public.

## Hardware / deployment
- **Resource profile:** Disk-oriented; working set need not fit fully in RAM, though buffer cache (DMF cache) sizing drives performance. Mixed disk/CPU bound depending on workload.
- **Storage assumptions:** Conventional block storage; benefits from fast local NVMe but tolerates network-attached storage. No special hardware requirements.
- **Footprint:** Single-node server (clustered/HA only on specific platforms, e.g., Solaris SPARC cluster option). Not embedded, not serverless.
- **Deployment:** On-prem / VM / cloud VM; container/k8s deployment possible but it is a stateful single-node DBMS, not a cloud-native distributed system.

## Bottom line
Reach for Ingres only if you already run it: it is a mature, stable, conventional single-node relational engine that keeps decades-old OLTP applications alive and well-supported by Actian. Do not choose it for anything new — [postgresql](postgresql.md) gives you the same relational heritage with a vastly larger ecosystem, real licensing freedom, and modern types. The biggest gotcha is the isolation naming: Ingres "SERIALIZABLE" under MVCC is snapshot isolation (first-committer-wins, `E_US125B`), so it admits write-skew despite the label.

## Sources
- [Database of Databases — Ingres](https://dbdb.io/db/ingres)
- [Ingres (database) — Wikipedia](https://en.wikipedia.org/wiki/Ingres_(database))
- [Actian Ingres 12.0 — Lock Level, MVCC and Isolation Levels](https://docs.actian.com/ingres/12.0/DatabaseAdmin/Lock_Level_MVCC_and_Isolation_Levels.htm)
- [Actian Ingres 12.0 — Hybrid Transaction and Analytics Processing](https://docs.actian.com/actianingres/12.0/DatabaseAdmin/Hybrid.htm)
- [Actian Launches Ingres 12.0 Database (press release, 2024-06-04)](https://www.actian.com/company/press-releases/actian-launches-ingres-12-0-database/)
- [Ingres 11.0 Documentation](https://docs.actian.com/ingres/11.0/index.html)
