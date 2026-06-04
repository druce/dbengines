---
name: Apache Phoenix
slug: apache-phoenix
rank: 119
data_model: Relational (SQL skin over Apache HBase)
license: Apache License 2.0 (permissive)
summary: SQL + JDBC layer over HBase that turns a wide-column store into a relational-looking OLTP database, inheriting HBase's strengths and all of its operational weight.
last_researched: 2026-06-04
confidence: medium
---

# Apache Phoenix

> A thin SQL/JDBC relational facade over [apache-hbase](apache-hbase.md) that gives low-latency point lookups and range scans on wide-column data — but it is HBase underneath, so it carries HBase's CP semantics, HDFS/ZooKeeper dependencies, and operational burden, and its "ACID transactions" remain effectively beta.

## When to use

**Use Apache Phoenix if:**
- ✅ You already run HBase and want relational SQL, JDBC, and secondary indexes instead of hand-coding HBase scans.
- ✅ You have high-write operational stores with point/prefix-range query patterns (salted time-series, entitlement/lookup tables).
- ✅ You need strongly-consistent secondary indexes over existing HBase data on an established Hadoop/HBase footprint.

**Avoid Apache Phoenix if:**
- ❌ It's a greenfield project — you're really adopting HBase + HDFS + ZooKeeper, an enormous tax versus PostgreSQL or managed distributed SQL.
- ❌ You need rock-solid multi-row ACID — transactions are beta with a churned manager history (Tephra retired, Omid now default).
- ❌ You run ad-hoc analytical/join-heavy BI workloads, or queries not aligned to the row-key prefix.

## Identity
- **Taxonomy / data model:** relational SQL skin (tables, columns, types, secondary indexes, views, JDBC) projected onto [apache-hbase](apache-hbase.md)'s wide-column [LSM](../concepts/lsm-vs-btree.md) store. A Phoenix table maps to an HBase table; rows are keyed by a composite primary key encoded into the HBase row key. Not a standalone engine — it is a client library + HBase coprocessors.
- **Storage model:** HBase-backed, so [LSM-tree](../concepts/lsm-vs-btree.md) (memstore + HFiles on HDFS), log-structured with background compaction. Primary key column order *is* the physical sort order of the row key; column families map to HBase column families. No independent on-disk format of its own.
- **Workload:** OLTP-leaning — point lookups and bounded range scans keyed by the leading PK columns. It pushes aggregation/filtering into server-side coprocessors and parallelizes scans by region boundaries on the client, so it can do operational analytics, but it is **not** an OLAP/columnar warehouse. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Full table scans (queries not aligned to the row-key prefix, absent a covering index) are slow.

## Distribution & consistency
- **CAP under partition:** **CP**, inherited from [apache-hbase](apache-hbase.md) — each region is served by exactly one RegionServer; under partition the affected regions are unavailable for writes/reads until reassignment rather than serving divergent data. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition, favors **C** over **A** (regions go offline); Else, favors **C** over **L** (single-writer-per-region path, HDFS replication on the write path). See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation:** non-transactional tables give HBase's per-row atomicity only — no cross-row/cross-table isolation; concurrent readers see committed single-row state. With `TRANSACTIONAL=true`, Phoenix layers **snapshot isolation** via an external transaction manager using MVCC ([mvcc](../concepts/mvcc.md)); readers see only commits that completed before their transaction began, and conflicting concurrent writes to the same rows abort at commit ([snapshot isolation, not serializable](https://phoenix.apache.org/transactions.html)). See [isolation-levels](../concepts/isolation-levels.md). ⚠️ unverified — exact serializability anomalies (e.g. write skew) are not characterized in primary docs; treat as classic SI.
- **"ACID" caveat — the load-bearing divergence:** transactions are documented as **beta** ([Phoenix transactions docs](https://phoenix.apache.org/transactions.html)). The original transaction manager, **Apache Tephra**, has been **retired** (community decision, [PHOENIX-6624](https://issues.apache.org/jira/browse/PHOENIX-6624); Tephra depended on an old libthrift with a high-severity CVE and the Attic-archived Twill). **Apache Omid** became the default ACID provider via a pluggable transaction-abstraction layer (TAL), selected when `TRANSACTION_PROVIDER` is unspecified ([Omid project](https://omid.incubator.apache.org/); [Adaltas — Omid as default Phoenix transaction processor](https://www.adaltas.com/en/2018/05/24/omid-scalable-and-highly-available-transaction-processing-for-apache-phoenix/)). ⚠️ unverified — the official `transactions.html` page is stale and still documents only Tephra (it does not mention Omid or Tephra's retirement), so the Omid-default claim rests on secondary sources and the Tephra-retirement JIRA rather than current primary docs. Net: cross-row ACID exists but is lightly used in production, version-sensitive, and adds a separate transaction-server component. Most deployments run **non-transactional** tables and rely on single-row atomicity plus strongly-consistent indexes.
- **Replication:** no replication of its own — durability/replication is HDFS block replication (typically 3x) under HBase. Single-leader per region (one RegionServer owns a region); failover is HBase region reassignment via ZooKeeper. See [replication-models](../concepts/replication-models.md). Cross-cluster replication is HBase replication.
- **Tunable consistency?** No Dynamo-style per-query levels. Reads are strongly consistent (single owning RegionServer).
- **Clock dependency:** HBase cell versions are timestamp-based; Omid uses a centralized timestamp oracle (TSO) for transaction ordering rather than wall-clock synchronization, so it does **not** require TrueTime/HLC-style synced clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, relational and rigid at the Phoenix layer (DDL: `CREATE TABLE`, typed columns, NOT NULL on PK). Phoenix can also map onto pre-existing HBase tables as schema-on-read views.
- **Migration:** `ALTER TABLE` to add columns is metadata-only and cheap (HBase is schemaless underneath, so adding a column does not rewrite data). Adding a secondary index can require an async MapReduce/rebuild job over existing data.
- **Type system:** SQL scalar types, `ARRAY`, sequences, and functional/expression indexes. As of Phoenix **5.3.0 (Oct 2025)** there is a native document type via **BSON/JSON** columns with server-side `BSON_VALUE`/`BSON_CONDITION_EXPRESSION`/`BSON_UPDATE_EXPRESSION` functions for projecting, filtering, and atomically mutating document fields ([Salesforce eng — adding document data support](https://engineering.salesforce.com/evolving-apache-phoenix-overcoming-5-challenges-to-add-document-data-support/)). No native geospatial type. No native vector/ANN. Composite primary keys are first-class and central to performance.

## Query interface
- **Language:** SQL via a **JDBC driver** (thin and thick clients; the Phoenix Query Server exposes Avatica/thin protocol). Dialect targets ~SQL:2003 subset with HBase-specific DDL properties (`SALT_BUCKETS`, `COLUMN_ENCODED_BYTES`, `TRANSACTIONAL`).
- **Transactions:** single-row atomic by default (HBase); full multi-statement cross-table ACID only on `TRANSACTIONAL=true` tables via Omid (beta — see above).
- **Native vs app-side:** server-side aggregation, filtering, `GROUP BY`, ordering, and joins (hash join and sort-merge join) execute in HBase coprocessors. **Secondary indexes** are native: *global* indexes (a separate HBase table; only used when the query is fully covered by the index) and *local* indexes (co-located in the same region as base data, cheaper writes, used even for non-covered queries) ([Salesforce eng blog on strongly-consistent global indexes](https://engineering.salesforce.com/the-design-of-strongly-consistent-global-secondary-indexes-in-apache-phoenix-part-1-90b90bda4210/)). Joins are supported but Phoenix is not a join-heavy analytical engine — large joins are an anti-pattern.
- **Stored procedures / UDFs:** no stored procedures; user-defined functions in Java.

## Scaling & topology
- **Horizontal**, by inheriting HBase auto-sharding: data splits into **regions** by row-key range, distributed across RegionServers; regions split/merge automatically. No separate Phoenix sharding layer.
- **Hot-spotting / salting:** monotonic row keys (timestamps, sequences) hotspot a single region. Phoenix's `SALT_BUCKETS` (1–256) prepends a hash byte to spread writes; rule of thumb is buckets ≈ number of RegionServers ([Salted Tables](https://phoenix.apache.org/salted.html)). Salting is a write-time design decision and is hard to change later — picking it wrong is the classic resharding-style pain.
- **Read replicas:** reads come from the single owning RegionServer (strongly consistent). HBase region-replica reads (timeline-consistent stale reads) exist at the HBase layer but are not the Phoenix default.
- **Storage/compute separation:** partial — compute (RegionServers) is separate from storage (HDFS/object store), but RegionServers own regions statefully; this is not Snowflake/Aurora-style elastic separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** HBase WAL on HDFS then memstore; durability governed by HBase WAL sync settings. Data-loss window depends on WAL flush policy and HDFS replication — synchronous WAL gives no loss on single-node crash; deferred/async WAL trades durability for throughput. Secondary-index maintenance requires `hbase.regionserver.wal.codec` set for custom WAL edits. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** strong at high-volume writes and prefix-aligned point/range reads; tail latency dominated by HBase realities — **compaction storms, region splits, and JVM GC pauses** are the main p99 offenders, plus a cold-start hit when reading from HFiles vs memstore.
- **Compaction / GC:** HBase minor/major compactions reclaim space and merge HFiles; major compaction is I/O-heavy and a well-known p99 disruptor often scheduled off-peak. JVM garbage collection on RegionServers contributes to latency tails.

## Operations & maturity
- **Backup/restore, PITR:** uses HBase snapshots, `Export`/`Import`, and HBase replication; no Phoenix-specific PITR. Snapshots are HBase-level.
- **Observability:** JDBC `EXPLAIN` shows the scan/index plan; HBase metrics (JMX), RegionServer UIs, and slow-query visibility via HBase logging. Index state (`ACTIVE`/`DISABLED`/`REBUILD`) is queryable and must be monitored — a failed index write flips the index to needing rebuild.
- **Upgrade story:** coupled tightly to HBase versions (current line: **5.3.x** — 5.3.0 (Oct 2025) and 5.3.1 (May 2026) support HBase 2.5/2.6; 5.2.1 supported HBase 2.4/2.5/2.6 — [release notes](https://phoenix.apache.org/release_notes.html)); upgrades are HBase-cluster upgrades with matching Phoenix coprocessor jars on every RegionServer — heavyweight, version-matrix-sensitive, day-2 burden is real.
- **Maturity:** mature where HBase is mature (heavy use historically at Salesforce, which drives much of Phoenix development). Known failure modes: index/data divergence on non-transactional global indexes (mitigated by the strongly-consistent global index redesign), salting mistakes, and the largely-abandoned Tephra path. ⚠️ unverified — **no public Jepsen report on Apache Phoenix** is known as of 2026; consistency claims rest on the HBase/Omid designs, not independent formal testing.

## Ecosystem & people
- **Canonical use cases:** SQL access over existing HBase data; high-write operational stores with point/prefix-range query patterns (time-series-ish event tables with salting, entitlement/lookup tables, large operational tables needing secondary indexes) on an existing Hadoop/HBase footprint.
- **Anti-patterns:** greenfield projects without an existing HBase/Hadoop cluster (the operational tax — HDFS + ZooKeeper + RegionServers — is enormous for what a single-node relational DB would do); ad-hoc analytical/join-heavy BI workloads; workloads needing rock-solid multi-row ACID (transactions are beta); anything where [postgresql](postgresql.md) or a managed cloud DB would suffice. If you want SQL-on-NoSQL but not HBase, compare [apache-cassandra](apache-cassandra.md) + its CQL or a [cockroachdb](cockroachdb.md)/[yugabytedb](yugabytedb.md)-style distributed SQL instead.
- **Connectors:** JDBC; Phoenix Query Server (Avatica thin client); Spark, Hive, Pig, MapReduce integrations. As of **5.3.0** Phoenix ships a **native CDC** feature (row-level change streams, ordered/partitioned events with pre/post images, built on max-lookback + uncovered indexes — [PHOENIX-7001](https://issues.apache.org/jira/browse/PHOENIX-7001)) in addition to HBase-level replication/CDC. BI tools connect over JDBC but performance assumes prefix-aligned queries.
- **Community:** Apache top-level project; smaller and quieter community than mainstream SQL engines, heavily steered by Salesforce; docs are adequate but uneven and partly stale (transaction docs still say "beta"). Learning curve is really the HBase learning curve.

## Licensing & cost
- **License:** **Apache License 2.0**, permissive ([license-taxonomy](../concepts/license-taxonomy.md)); no post-2018 relicensing, no source-available restrictions.
- **Self-managed vs managed:** primarily self-managed on a Hadoop/HBase cluster. Available in managed Hadoop platforms (e.g. Cloudera, historically Azure HDInsight, AWS EMR HBase). No first-party serverless offering.
- **Lock-in:** low at the license level; practical lock-in is to the HBase/Hadoop operational stack, not to Phoenix.
- **Cost model:** no license cost; cost is the cluster — per-node RegionServers + HDFS storage + ZooKeeper, sized for memory and disk. Economics are poor at small scale (cluster overhead dominates) and improve only at genuinely large data volumes where HBase pays off.

## Hardware / deployment
- **Resource profile:** memory-hungry JVM RegionServers (block cache + memstore), disk-bound on HDFS, with CPU spent on compaction and coprocessor execution. Working set need not fit in RAM, but block-cache hit rate drives read latency.
- **Storage assumptions:** designed for commodity local disks under HDFS; benefits from fast disks but tolerates spinning media better than a pure in-memory store. NVMe helps compaction/read tails.
- **Footprint:** **clustered only** — there is no embedded/single-binary mode; minimum viable deployment is an HBase cluster (HDFS + ZooKeeper + HMaster + RegionServers), plus an Omid TSO if using transactions.
- **Deployment:** on-prem Hadoop or cloud-hosted HBase; k8s deployment is possible but HBase-on-k8s StatefulSet operations are nontrivial (stable network identity, persistent volumes, ZooKeeper quorum).

## Bottom line
Reach for Phoenix when you **already run HBase** and want relational SQL, JDBC, and secondary indexes over it instead of hand-coding HBase scans — that is its sweet spot and it does it well. Do **not** pick it as a greenfield database: you are really adopting HBase + HDFS + ZooKeeper, an enormous operational footprint for what a single [postgresql](postgresql.md) node or a managed distributed SQL store ([cockroachdb](cockroachdb.md), [yugabytedb](yugabytedb.md)) would handle with far less pain. The single biggest gotcha: its ACID transactions are still **beta** with a churned transaction-manager history (Tephra retired, Omid now default), so design for single-row atomicity + strongly-consistent secondary indexes, and treat multi-row ACID as a fragile bonus rather than a guarantee.

## Sources
- [Apache Phoenix — official site](https://phoenix.apache.org/)
- [Phoenix Transactions (beta) docs](https://phoenix.apache.org/transactions.html)
- [Phoenix Salted Tables](https://phoenix.apache.org/salted.html)
- [Phoenix Release Notes](https://phoenix.apache.org/release_notes.html)
- [PHOENIX-6624 — Retire Tephra (JIRA)](https://issues.apache.org/jira/browse/PHOENIX-6624)
- [Apache Omid project](https://omid.incubator.apache.org/)
- [The Design of Strongly Consistent Global Secondary Indexes in Apache Phoenix — Salesforce Engineering](https://engineering.salesforce.com/the-design-of-strongly-consistent-global-secondary-indexes-in-apache-phoenix-part-1-90b90bda4210/)
- [Apache HBase ACID semantics](https://hbase.apache.org/acid-semantics.html)
