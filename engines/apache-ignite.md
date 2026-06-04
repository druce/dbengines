---
name: Apache Ignite
slug: apache-ignite
rank: 97
data_model: Multi-model (in-memory)
license: Apache License 2.0 (permissive)
summary: In-memory distributed key-value/SQL data grid that bolts on disk persistence; ACID for key-value, weaker (and historically half-finished) for distributed SQL.
last_researched: 2026-06-04
confidence: medium
---

# Apache Ignite

> Memory-first distributed cache/compute grid with a SQL veneer — strong as a transactional key-value grid in front of a system of record, weak and rough as a primary transactional SQL database.

## When to use

**Use Apache Ignite if:**
- ✅ You need a horizontally-scalable, ACID-capable distributed in-memory key-value / data grid to accelerate or front a system of record
- ✅ You want a compute grid for co-located parallel processing (compute-to-data affinity)
- ✅ You need read-through/write-through caching, session/state store, or high-speed KV with the working set in RAM
- ✅ Your team has JVM and distributed-systems operational depth (GC, off-heap, WAL/checkpoint, baseline topology tuning)

**Avoid Apache Ignite if:**
- ❌ You treat it as a drop-in primary transactional SQL database — distributed transactional SQL was shipped beta then removed in 2.x; strong ACID lives in the key-value API, not distributed SQL (biggest gotcha)
- ❌ You need rock-solid, independently-verified distributed consistency — no official Jepsen report exists
- ❌ Your workload is pure OLAP/data-warehouse — there is no separate columnar engine, so "HTAP" just means SQL over the same row caches
- ❌ You run 2.x without split-brain protection config, or lack the RAM the in-memory story assumes

## Identity
- **Taxonomy / data model:** Multi-model. Primarily a distributed key-value store / in-memory data grid (IMDG), with a SQL layer over the same caches, plus compute grid, service grid, and streaming. Often used as a caching/compute tier rather than a primary database. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Row-oriented, page-based off-heap "durable memory" allocator. Ignite 2.x persists via WAL + checkpointed page store. Ignite 3 (GA Feb 2025) offers an LSM-tree-based storage option (RocksDB-backed) alongside a B-tree/page store ([GridGain: Ignite 3 Alpha 3 — Calcite, Raft, LSM-Tree](https://www.gridgain.com/resources/blog/apache-ignite-3-alpha-3-apache-calcite-raft-and-lsm-tree)). See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP-leaning key-value/grid workload with limited distributed SQL analytics. Marketed as HTAP, but ⚠️ unverified — there is no separate columnar/analytical store; SQL runs over the same row-oriented caches, so "HTAP" here means "you can run SQL on operational data," not physically separated analytical and transactional engines. Treat the HTAP claim as vague.

## Distribution & consistency
- **CAP under partition:** CP-leaning. In Ignite 3, partitions are replicated via Raft and require a quorum, so a minority partition stops serving writes ([Ignite 3 architecture](https://ignite.apache.org/blog/getting-to-know-apache-ignite-3.html)). In Ignite 2.x, replication is primary/backup (not consensus-based); behavior under network partition depends on cache mode and is weaker. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, the Raft-based design favors consistency over availability (PC). Else (no partition), it favors latency — in-memory reads/writes are local-and-fast; default ATOMIC caches give per-key atomicity without transaction coordination overhead.
- **Default isolation & what's achievable:** For `TRANSACTIONAL` key-value caches: `OPTIMISTIC`/`PESSIMISTIC` concurrency × `READ_COMMITTED`/`REPEATABLE_READ`/`SERIALIZABLE` isolation ([Ignite transactions docs](https://apacheignite.readme.io/docs/transactions)). Optimistic + Serializable is deadlock-free via version (XidVersion) conflict detection, throwing `TransactionOptimisticException` on conflict for app retry. ⚠️ unverified — these isolation guarantees apply to **key-value** transactions; their formal correctness has not been independently verified (no official Jepsen report exists). **Distributed transactional SQL** relied on `TRANSACTIONAL_SNAPSHOT`/MVCC, which gave snapshot isolation but was shipped beta-only in 2.7, deprecated in 2.12, and **removed in 2.16** ([GitHub issue #11538](https://github.com/apache/ignite/issues/11538)). So in current Ignite 2.x, multi-statement ACID SQL transactions are effectively gone; ACID lives in the key-value API. Ignite 3 (GA Feb 2025, 3.1 since) reintroduces MVCC + snapshot isolation as a first-class transaction protocol covering both SQL and KV ([Ignite 3 MVCC blog](https://ignite.apache.org/blog/apache-ignite-3-architecture-part-7.html)); ⚠️ unverified — whether Ignite 3 offers serializable above snapshot isolation, and any independent verification of its correctness, are not confirmed. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Ignite 2.x: partitioned cache with synchronous or async backups (primary/backup), or fully `REPLICATED` mode. Ignite 3: per-partition Raft groups; the Raft leader is the primary replica ([Ignite 3 architecture](https://ignite.apache.org/blog/getting-to-know-apache-ignite-3.html)). See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Split-brain:** Ignite 2.x has no built-in split-brain protection at the consensus layer (a known operational hazard; often paired with a segmentation/ZooKeeper discovery plugin). Ignite 3's Raft (JRaft) provides quorum-based split-brain protection out of the box.
- **Tunable consistency?** Yes, coarsely: per-cache atomicity mode (`ATOMIC` vs `TRANSACTIONAL`) and sync/async backup writes; read-from-backup toggles.
- **Clock dependency:** Ignite 3 uses Hybrid Logical Clocks (HLC) to order transactions for MVCC snapshots. ⚠️ unverified — exact correctness sensitivity to clock skew not independently audited. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Dual. Caches can be schemaless key-value (arbitrary objects). To use SQL, you define a schema (`CREATE TABLE` / `QueryEntity` annotations) over the cache. Ignite 3 is more schema-first/table-centric.
- **Migration/evolution:** `ALTER TABLE ADD/DROP COLUMN` and online index creation supported. ⚠️ unverified — locking behavior of DDL under concurrent load not confirmed.
- **Type system:** Java/.NET/C++ object types in caches; SQL types incl. standard scalars; native handling of POJOs via binary format. Geospatial via H2's geometry in 2.x. No native vector/ANN type as of last research.

## Query interface
- **Language:** ANSI-99-subset SQL. Ignite 2.x SQL engine was built on **H2** (embedded, and long the default); a newer **Apache Calcite**-based engine was added as an *experimental* feature in 2.13 ([Ignite 2.13 release blog](https://ignite.apache.org/blog/apache-ignite-2-13-0.html)) and stabilized over later 2.x releases, replacing H2's non-distributed optimizer ([Calcite SQL engine docs](https://ignite.apache.org/docs/latest/SQL/sql-calcite)). Ignite 3's SQL engine is Calcite-based from the start. Also key-value API (get/put/invoke), ScanQuery, compute (MapReduce-style), continuous queries, and a Spark/JDBC/ODBC integration.
- **Transactions:** Full multi-statement ACID via **key-value `TRANSACTIONAL` caches** (Java/.NET/C++ API). Distributed multi-statement **SQL** transactions are **not available** in current 2.x (MVCC removed in 2.16); SQL DML is atomic per-statement only. Ignite 3 restores transactional SQL via MVCC.
- **Native vs app-side:** Distributed joins (with affinity co-location for performance; non-collocated joins are expensive), aggregations, secondary indexes — all native. Cross-partition joins without collocation can be slow or require explicit enabling.
- **Stored procedures / UDFs:** No SQL stored procedures; instead compute tasks / `ComputeJob`, cache `EntryProcessor` (`invoke`), and continuous queries written in Java/.NET/C++.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — data auto-partitioned across nodes using rendezvous (consistent-hashing-style) affinity. Add nodes to grow capacity/throughput.
- **Sharding:** Automatic partitioning by affinity key; rebalancing on topology change. **Baseline topology** pins which nodes own persistent data so the cluster doesn't rebalance/lose data on transient restarts ([GridGain: baseline topology](https://www.gridgain.com/resources/blog/apache-ignites-baseline-topology-explained)). Resharding/rebalance can be I/O-heavy; the baseline mechanism exists precisely to manage that pain.
- **Read replicas:** Backups can serve reads (`readFromBackup`); reads from a backup may be stale relative to the primary unless within a transaction. Ignite 3 routes consistent reads through the primary/Raft leader.
- **Storage/compute separation:** No — Ignite co-locates storage and compute by design (data affinity + compute-to-data). Not a Snowflake/Aurora-style separated architecture. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** With native persistence, writes hit off-heap pages and are made durable via WAL (configurable fsync modes: `DEFAULT`/`LOG_ONLY`/`BACKGROUND`, trading durability for throughput) plus periodic checkpoints to the page store. **Data-loss window on crash:** with `BACKGROUND`/`LOG_ONLY` WAL modes, a node crash can lose recent writes; `FSYNC` mode minimizes the window at a throughput cost. Pure in-memory mode (no persistence) loses all data on full-cluster restart. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** In-memory key-value ops are low-latency; throughput scales with nodes. ⚠️ unverified — published p99/tail numbers are vendor-sourced (GridGain) and workload-specific.
- **Compaction/vacuum/GC:** Two GC concerns. (1) JVM GC: large on-heap usage causes stop-the-world pauses, which is why durable memory is off-heap — but Java GC on metadata/query buffers can still spike p99. (2) Checkpointing: periodic page-store checkpoints cause I/O bursts that affect tail latency. Ignite 3's LSM option introduces background compaction with its own p99 implications.

## Operations & maturity
- **Backup/restore, PITR:** Cache dumps added in 2.16; snapshots (full/incremental) of native persistence supported; PITR is limited compared to mature RDBMSs. Backup/restore tooling is rougher than Postgres/MySQL.
- **Observability:** JMX/metrics, system views (SQL over `SYS` schema), `EXPLAIN` for SQL plans, monitoring via GridGain Control Center or third-party (Grafana). Slow-query logging available.
- **Upgrade story:** Rolling restarts possible for in-memory; persistent storage upgrades between major versions (e.g., 2.x → 3.x) are a migration, not a drop-in rolling upgrade — Ignite 3 is a substantial rewrite with different storage and APIs. Day-2 burden is non-trivial: JVM tuning, off-heap sizing, checkpoint/WAL tuning, baseline topology management, and discovery/split-brain config.
- **Maturity:** Mature (Apache top-level since 2015, donated from GridGain). **No official jepsen.io report exists** — Ignite's distributed-transaction correctness has not been the subject of an Aphyr/Jepsen engagement. (An academic paper applied the open-source Jepsen *framework* to Ignite — ["Analysis of Consistency for In Memory Data Grid Apache Ignite", IEEE 2019](https://ieeexplore.ieee.org/document/8880744) — but ⚠️ unverified: its specific findings/verdict and tested version were not accessible during this check.) Known failure modes: split-brain in 2.x without extra config; the long-running, ultimately-abandoned MVCC/transactional-SQL effort (beta in 2.7, removed in 2.16) is a notable maturity scar — production multi-statement SQL transactions were never delivered in the 2.x line.

## Ecosystem & people
- **Canonical use cases:** Distributed in-memory cache / data grid in front of an RDBMS; high-speed key-value store; compute grid for co-located parallel processing; read-through/write-through caching; session/state store. Strong fit as an acceleration layer.
- **Anti-patterns:** Using it as your only transactional SQL system of record (transactional SQL is incomplete/removed in 2.x); pure OLAP/data-warehouse workloads (no columnar engine); workloads needing rock-solid independently-verified distributed consistency (no Jepsen); teams without JVM/distributed-systems operational depth.
- **Drivers/connectors:** Java, .NET, C++, Python (thin client), Node.js, REST; JDBC/ODBC; Spark, Kafka (sink/source), Spring Data, Hibernate L2 cache; CDC available in 2.x+.
- **Community/support:** Active Apache community; primary commercial backer is **GridGain** (managed/enterprise distribution). Docs are decent but split across versions (2.x readme.io legacy docs vs new site, and a separate Ignite 3 doc set), which makes research confusing. Steep learning curve.

## Licensing & cost
- **OSS license:** **Apache License 2.0** — permissive, no post-2018 relicensing drama. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-managed open source; GridGain offers a commercial enterprise build and managed cloud (GridGain Nebula). Lock-in risk is moderate via GridGain-specific features (e.g., Control Center, enterprise security, rolling-upgrade tooling).
- **Cost model:** Free OSS (you pay for infrastructure — heavy RAM). GridGain commercial is per-node/subscription. At scale, the dominant cost is RAM, since the working set is expected to fit in memory for the performance story to hold.

## Hardware / deployment
- **Resource profile:** Memory-bound. The value proposition assumes the hot/working data set fits in RAM (off-heap); native persistence lets data exceed RAM but then it behaves more like a disk DB with a memory cache. Also CPU/JVM-sensitive (GC tuning matters).
- **Storage assumptions:** NVMe/local SSD strongly preferred for the WAL and page store; network-attached storage hurts checkpoint/WAL latency.
- **Footprint:** Clustered (multi-node JVM processes). Can run embedded in a JVM app, but typically deployed as a standalone cluster. Not serverless.
- **Deployment:** On-prem or any cloud; Kubernetes operator exists (StatefulSets for persistent nodes). StatefulSet realities: persistent volume per node + baseline topology means node identity matters across restarts.

## Bottom line
Reach for Apache Ignite when you need a horizontally-scalable, ACID-capable distributed in-memory **key-value/compute grid** to accelerate or sit in front of a system of record, and your team can handle JVM/distributed-systems operations. Do **not** treat it as a drop-in primary transactional **SQL** database: distributed transactional SQL was shipped beta, then deprecated and removed in 2.x (the Ignite 3 rewrite, GA Feb 2025, reintroduces it via MVCC), and there is no official (jepsen.io) verification of its consistency. The single biggest gotcha: the gap between the "distributed ACID SQL database" marketing and the reality that strong ACID guarantees in production 2.x live in the key-value API, not in distributed SQL.

## Sources
- [Apache Ignite transactions (concurrency modes & isolation levels)](https://apacheignite.readme.io/docs/transactions)
- [Apache Ignite — Distributed ACID transactions (feature page)](https://ignite.apache.org/features/acid-transactions.html)
- [GitHub issue #11538 — Why is MVCC being removed (deprecated 2.12, removed 2.16)](https://github.com/apache/ignite/issues/11538)
- [Apache Ignite 2.16.0 release notes (cache dumps, Calcite stabilization)](https://ignite.apache.org/blog/apache-ignite-2-16-0.html)
- [Calcite-based SQL engine docs](https://ignite.apache.org/docs/latest/SQL/sql-calcite)
- [Getting to know Apache Ignite 3 (Raft, primary replica, MVCC)](https://ignite.apache.org/blog/getting-to-know-apache-ignite-3.html)
- [Apache Ignite 3 architecture part 7 — MVCC transactions](https://ignite.apache.org/blog/apache-ignite-3-architecture-part-7.html)
- [GridGain — Ignite 3 Alpha 3: Calcite, Raft, LSM-Tree](https://www.gridgain.com/resources/blog/apache-ignite-3-alpha-3-apache-calcite-raft-and-lsm-tree)
- [GridGain — Baseline topology explained](https://www.gridgain.com/resources/blog/apache-ignites-baseline-topology-explained)
- [Multi-tier (durable memory) storage architecture](https://ignite.apache.org/arch/multi-tier-storage.html)
- [Apache Ignite 2.13.0 — new experimental Calcite SQL engine](https://ignite.apache.org/blog/apache-ignite-2-13-0.html)
- ["Analysis of Consistency for In Memory Data Grid Apache Ignite" (IEEE, 2019) — academic use of the Jepsen framework](https://ieeexplore.ieee.org/document/8880744)
