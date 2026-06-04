---
name: SingleStore
slug: singlestore
rank: 93
data_model: Relational (distributed HTAP)
license: Proprietary (closed-source binary; NOT source-available); free self-managed tier up to 8 vCPU / 32 GB RAM
summary: Distributed MySQL-wire-compatible HTAP SQL engine that unifies rowstore + columnstore into one "Universal Storage" table; fast analytics with OLTP-ish writes, but only READ COMMITTED isolation.
last_researched: 2026-06-04
confidence: high
---

# SingleStore

> Shared-nothing, MySQL-compatible distributed SQL engine (formerly MemSQL) that fuses an in-memory rowstore and a compressed columnstore into a single table type to serve transactional and analytical workloads at once — at the price of capping isolation at READ COMMITTED.

## Identity
- **Taxonomy / data model:** Relational, distributed. SQL with MySQL dialect compatibility; also stores JSON, geospatial, full-text, and vector ([vector-search-ann](../concepts/vector-search-ann.md)) types in the same tables.
- **Storage model:** Hybrid. "Universal Storage" is a disk-backed columnstore organized as an [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM tree with row-segments (~million-row chunks called *segments*), plus secondary **hash indexes** and seekable/sparse compression to make point reads and updates cheap on columnar data ([SingleStore: Pushing HTAP Forward](https://www.singlestore.com/blog/pushing-htap-databases-forward-with-singlestoredb/), [Universal Storage docs](https://docs.singlestore.com/cloud/create-a-database/columnstore/universal-storage/)). A pure in-memory rowstore table type also still exists.
- **Workload:** Genuinely [oltp-olap-htap](../concepts/oltp-olap-htap.md) HTAP, and the physical separation mechanism is real (not vague marketing): a single table is **internally a columnstore with an in-memory rowstore-backed write/delta region**; recent writes land row-oriented and are flushed/merged into compressed column segments by background LSM merges ([dbdb.io](https://dbdb.io/db/singlestore)). So OLTP and OLAP share one copy of the data rather than separate replicas.

## Distribution & consistency
- **CAP under partition:** CP-leaning. With recommended synchronous replication a partition whose replica is unreachable cannot commit, so it favors consistency over availability of that shard. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition it sacrifices availability (PC); else (no partition) it is tunable — sync durability + sync replication favors consistency (EC), async modes favor latency (EL). ⚠️ unverified — SingleStore does not publish a formal PACELC classification; this is inferred from its replication/durability options.
- **Default isolation & what's achievable:** **READ COMMITTED only — this is the ceiling, not just the default** ([SingleStore Support: READ COMMITTED](https://support.singlestore.com/hc/en-us/articles/10492204337812-READ-COMMITTED-in-SingleStore)). No REPEATABLE READ, no SNAPSHOT, no SERIALIZABLE. It uses [mvcc](../concepts/mvcc.md) (non-blocking reads, row-level write locks) but exposes only read-committed semantics, so non-repeatable reads and write skew are possible within a transaction. Any "ACID" claim here means **ACID at READ COMMITTED**, not serializable — note this when comparing to engines that offer SSI. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-leader per partition. HA pairs leaf nodes; each leaf holds half **primary** partitions and half **replica** partitions for its pair, replicating both directions ([Replication & Durability docs](https://docs.singlestore.com/db/v9.0/user-and-cluster-administration/high-availability-and-disaster-recovery/replication-and-durability-concepts/)). Sync replication acks the commit only after the replica has it; async does not. Cross-cluster replication gives a read-only secondary for DR. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Not per-query Dynamo-style levels; consistency is governed by database-level sync/async **replication** and sync/async **durability** settings, not per-statement.
- **Clock dependency:** No TrueTime/HLC-style clock-based correctness; ordering is per-partition leader-driven, not clock-driven. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Rigid relational schema; `CREATE TABLE` requires column definitions. JSON columns give schema-on-read flexibility within a typed column.
- **Migration/evolution:** Supports online `ALTER TABLE` (online ADD COLUMN and many changes) but some DDL is heavier; DDL is coordinated by the master aggregator. ⚠️ unverified — exact set of fully-online vs locking ALTER operations varies by version; confirm against the target version's docs.
- **Type system:** Standard SQL types plus native JSON, geospatial, full-text (search index), and **vector** types with ANN indexes ([vector-search-ann](../concepts/vector-search-ann.md)).

## Query interface
- **Language:** SQL, **MySQL wire-protocol compatible** (existing MySQL drivers/clients connect), with extensions for distributed/columnstore features.
- **Transactions:** Full multi-statement ACID transactions, but only at READ COMMITTED (see above). Distributed cross-partition transactions are supported with two-phase coordination via the aggregator.
- **Native vs app-side:** Native distributed joins, aggregations, window functions, and secondary (hash) indexes. Cross-shard joins are most efficient when tables share a shard key or one side is a replicated **reference** table; otherwise data is reshuffled across the network.
- **Stored procedures / UDFs:** Yes — stored procedures, UDFs, and TVFs in SQL, plus extensions (Wasm-based UDFs in recent versions).

## Scaling & topology
- **Horizontal, shared-nothing.** Aggregator nodes (one master + child aggregators) route queries; leaf nodes store partitions ([Cluster Components docs](https://docs.singlestore.com/db/v8.9/introduction/distributed-architecture/cluster-components/)). Sharded tables hash on the **SHARD KEY** (or random for keyless); reference tables replicate fully to every node.
- **Resharding pain:** Number of partitions is fixed at database creation; rebalancing moves partitions across leaves but the partition count itself is not trivially changed — pick partition count/shard keys carefully up front. ⚠️ unverified — exact online-reshard capabilities depend on version.
- **Read replicas:** Replica partitions exist for HA; reads from replicas/secondary clusters can lag (async). Primary-partition reads are consistent.
- **Storage/compute separation:** Yes in the cloud (Helios) "bottomless" architecture — columnstore data persists to object storage (S3/blob) with leaf-local cache, decoupling storage from compute. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Per-partition write-ahead transaction log + periodic in-memory snapshots; recovery replays the log from the last snapshot ([Transaction Logs & Snapshots docs](https://docs.singlestore.com/db/v9.0/user-and-cluster-administration/high-availability-and-disaster-recovery/transaction-logs-snapshots/usage/)). **Data-loss window depends on config:** with default **async durability** a transaction is acked from memory and written to disk asynchronously, so a single-node crash before flush can lose recent transactions unless **sync replication** put it on the pair first; **sync durability** flushes the log before ack. See [wal-and-durability](../concepts/wal-and-durability.md). Note: async replication + sync durability is a disallowed combination.
- **Throughput/latency:** Strong analytical scan throughput (vectorized, SIMD, columnar) and good concurrent ingest; columnstore point lookups are accelerated by hash indexes but still trail a pure in-memory rowstore for the heaviest OLTP. ⚠️ unverified — no vendor-neutral p99 benchmarks reviewed here.
- **Compaction / GC:** Background LSM merges compact column segments and apply the delete bitmap / merge the rowstore delta into columnar form; merge activity can affect p99 on write-heavy workloads (general LSM behavior).

## Operations & maturity
- **Backup/restore:** Full and incremental backups to object storage; snapshot + log enable point-in-time recovery. Cloud handles backups automatically.
- **Observability:** `EXPLAIN`/`PROFILE` query plans, information_schema and management views, slow-query and workload monitoring; visual Studio/dashboard tooling.
- **Upgrade story:** Rolling upgrades for clusters; Helios upgrades are managed by SingleStore. Day-2 burden for self-managed includes capacity/partition planning and HA pair management.
- **Maturity:** Production since the MemSQL era (~2013); used at scale for real-time analytics. **No public Jepsen report exists** for SingleStore/MemSQL as of this writing — its READ COMMITTED ceiling means it is not a candidate for serializable-correctness claims, and concurrency anomalies (write skew, non-repeatable read) are expected by design, not bugs.

## Ecosystem & people
- **Canonical use cases:** Real-time analytics / operational analytics, dashboards over fresh data, ingest-and-query pipelines (built-in **Pipelines** ingest from Kafka, S3, GCS, etc., with wildcard/glob support), AI/vector + SQL hybrid search, replacing a MySQL+OLAP two-system stack with one.
- **Anti-patterns:** Workloads needing serializable isolation or repeatable-read snapshots; very high-contention single-row OLTP where a dedicated row-store/OLTP engine fits better; small single-node apps (operational overhead and cost are aimed at scale); deep cross-shard transactional graphs.
- **Drivers/connectors:** Any MySQL driver/ORM; CDC out, Kafka/S3/GCS pipelines in, dbt, Spark connector, BI tools (Tableau/Looker/Power BI via MySQL).
- **Community/support:** Commercial vendor (SingleStore Inc.) with paid support; smaller community than MySQL/Postgres; docs are good. Learning curve is moderate — SQL/MySQL-familiar, but distributed shard-key and partition design must be learned.

## Licensing & cost
- **License:** **Proprietary, closed-source commercial — not OSI open source, and not even "source-available":** the core engine ships as a binary and its source is not published (only ecosystem tools/connectors under [SingleStore Labs](https://github.com/singlestore-labs) are open source). Self-managed is **free up to 8 vCPU and 32 GB RAM** across core features ([SingleStore free self-managed announcement](https://www.singlestore.com/blog/singlestore-free-tier-here-for-good/)); beyond that it is paid. There is also a free shared cloud tier. See [license-taxonomy](../concepts/license-taxonomy.md) — treat this as a closed commercial product, not Apache/MIT and not BSL/SSPL source-available. (No post-2018 relicensing event of an OSS project — it was never under a permissive OSS license.)
- **Self-managed vs managed:** Both. Helios is the fully managed cloud (AWS/Azure/GCP).
- **Lock-in:** MySQL-wire compatibility eases client portability, but Universal Storage, Pipelines, vector/columnstore extensions, and Helios bottomless storage are proprietary; migrating off is non-trivial.
- **Cost model:** Self-managed licensed by **units** (1 unit ≈ 8 vCPU / 64 GB RAM / 1 TB cache) on leaf hosts. Helios is consumption-based: **compute credits per workspace-hour (~$3.96/credit list)** plus per-GB-month storage ([Helios pricing](https://www.singlestore.com/cloud-pricing/)). At scale, compute (always-on workspaces) dominates cost; cheap-at-small does not always hold.

## Hardware / deployment
- **Resource profile:** Memory-hungry — rowstore tables live entirely in RAM, and even Universal Storage relies on large memory for the write region, caches, and query execution; also CPU-bound for vectorized scans. Working set should fit in RAM/local cache for best latency.
- **Storage assumptions:** Local NVMe/SSD for leaf cache and logs; cloud uses object storage as the durable backing tier behind that cache.
- **Footprint:** Distributed clustered (aggregators + leaves); not embedded. Cloud serverless-ish via Helios workspaces, but compute is provisioned, not per-query serverless.
- **Deployment:** SaaS (Helios) or on-prem/self-managed; container/k8s supported via the SingleStore Operator (StatefulSets for leaves), with the usual stateful-set storage caveats.

## Bottom line
Reach for SingleStore when you want **one MySQL-compatible system that ingests fast and answers analytical queries on fresh data** — operational analytics, real-time dashboards, and SQL+vector hybrid workloads where running separate OLTP and OLAP systems is the pain you're escaping. Do **not** reach for it if you need serializable or even repeatable-read isolation, if your workload is small enough for a single Postgres/MySQL node, or if you want true OSS licensing. **The single biggest gotcha: isolation tops out at READ COMMITTED** — there is no snapshot or serializable mode, so application-visible anomalies (non-repeatable reads, write skew) are by design and must be handled in app logic.

## Sources
- [SingleStore — dbdb.io](https://dbdb.io/db/singlestore)
- [Pushing HTAP Databases Forward With SingleStoreDB](https://www.singlestore.com/blog/pushing-htap-databases-forward-with-singlestoredb/)
- [Universal Storage docs](https://docs.singlestore.com/cloud/create-a-database/columnstore/universal-storage/)
- [Cluster Components / Distributed Architecture docs](https://docs.singlestore.com/db/v8.9/introduction/distributed-architecture/cluster-components/)
- [Replication and Durability Concepts docs](https://docs.singlestore.com/db/v9.0/user-and-cluster-administration/high-availability-and-disaster-recovery/replication-and-durability-concepts/)
- [Transaction Logs and Snapshots docs](https://docs.singlestore.com/db/v9.0/user-and-cluster-administration/high-availability-and-disaster-recovery/transaction-logs-snapshots/usage/)
- [READ COMMITTED in SingleStore (Support)](https://support.singlestore.com/hc/en-us/articles/10492204337812-READ-COMMITTED-in-SingleStore)
- [SingleStore Free Self-Managed Tier](https://www.singlestore.com/blog/singlestore-free-tier-here-for-good/)
- [SingleStore Helios Pricing](https://www.singlestore.com/cloud-pricing/)
