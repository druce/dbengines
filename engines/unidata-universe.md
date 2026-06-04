---
name: UniData, UniVerse
slug: unidata-universe
rank: 121
data_model: Multivalue (PICK / nested-relational)
license: Commercial / proprietary (closed source)
summary: Rocket's two PICK-derived MultiValue databases — schema-light, ASCII nested-relational stores driven by embedded BASIC, kept alive by legacy ERP and vertical apps.
last_researched: 2026-06-04
confidence: high
---

# UniData, UniVerse

> Two closely-related, commercially-supported descendants of the 1960s PICK operating system: single-node MultiValue ("nested relational") databases where records can hold multivalued attributes inline, queried via a 4GL BASIC dialect rather than SQL — still in production mainly because rewriting the apps built on them is harder than maintaining them.

## When to use

**Use UniData, UniVerse if:**
- ✅ You already run one — the value is the decades of working MultiValue BASIC application code on top, not the engine itself
- ✅ Your line-of-business records are naturally hierarchical/multivalued and benefit from embedding child data inline rather than joining
- ✅ Keyed transactional access on a single node is the workload, and you can keep hashed files correctly sized
- ✅ You want vendor-supported, mature OLTP for an existing ERP/distribution/healthcare/finance app

**Avoid UniData, UniVerse if:**
- ❌ You neglect file sizing — hashed-file overflow silently destroys p99 latency unless you actively run RESIZE maintenance (the biggest gotcha)
- ❌ You assume "ACID" by default — isolation is real only if the app explicitly locks (READU) and transacts; the default NO.ISOLATION idiom gives no isolation
- ❌ It's a greenfield project — single-node only, no native sharding, weak analytics/BI/CDC, and a shrinking talent pool
- ❌ You need horizontal scale-out, cloud-native elasticity, or OLAP/ad-hoc BI at scale

## Identity
- **Taxonomy / data model:** [MultiValue](../concepts/multivalue-data-model.md) / PICK-derived nested-relational DBMS. Data is stored as ASCII records identified by a unique record ID; fields (attributes) can themselves hold multiple values and sub-values, delimited by field marks (x'FE'), value marks (x'FD') and subvalue marks (x'FC') — i.e. one record can embed what a relational schema would normalize into child tables ([Rocket U2 / Wikipedia](https://en.wikipedia.org/wiki/Rocket_U2), [db-engines](https://db-engines.com/en/system/UniData,UniVerse)). Two products under the "U2" umbrella: **UniVerse** (originally VMARK) and **UniData** (originally Unidata Corp); similar model, different BASIC dialect and tooling.
- **Storage model:** row-oriented hashed files. Records hash by ID into groups within a file; well-sized files give near-O(1) ID lookup, badly-sized ones degrade as groups overflow ("sizing" and periodic file resize/`RESIZE` is a classic day-2 chore). Non-hashed (directory/Type-1) files store source, XML, or text as OS files. On-disk format is pure ASCII, not binary. Not [LSM or B-tree](../concepts/lsm-vs-btree.md) at the primary level — it's hash-organized; secondary indexes are B-tree-like.
- **Workload:** [OLTP](../concepts/oltp-olap-htap.md). Optimized for high-volume transactional line-of-business apps (ERP, distribution, healthcare, finance). Not an analytics/OLAP engine; ad-hoc reporting is done via the built-in query language and is row-at-a-time, not columnar.

## Distribution & consistency
- **CAP under partition:** N/A as a distributed system — the primary store is **single-node** ([db-engines lists partitioning: none](https://db-engines.com/en/system/UniData,UniVerse)). High availability comes from asynchronous replication to standby servers, not a partition-tolerant cluster, so [CAP](../concepts/cap-pacelc.md) does not meaningfully apply to the write path.
- **PACELC:** N/A — single-writer node. With async replication enabled, the else-case favors latency over consistency: replicas lag the primary (see replication below).
- **Default isolation & what's achievable:** lock-based, **configurable isolation levels**. UniVerse defines isolation *levels* from `NO.ISOLATION` (raw MultiValue behavior, no transactional guarantees) up through read-committed, repeatable-read and serializable-style levels, each implemented as a set of locking prerequisites; read-committed is the level Rocket recommends for busy sites ([intl-spectrum: Traditional Locking](http://www.intl-spectrum.com/Article/r403/Locking__Part_2_Traditional_Locking)). See [isolation-levels](../concepts/isolation-levels.md). The important divergence from the marketing: db-engines summarizes ACID as **"configurable"** ([db-engines](https://db-engines.com/en/system/UniData,UniVerse)) — i.e. you only get transactional integrity if the application explicitly takes the right record/file locks and runs inside `TRANSACTION START`/`COMMIT`. The default MultiValue programming idiom (`NO.ISOLATION`) gives no isolation at all. This is application-enforced concurrency, not the optimistic [MVCC](../concepts/mvcc.md) of a modern RDBMS.
- **Replication:** **U2 Data Replication** — asynchronous log-shipping of files and their transactions from a publisher to one or more subscribers, with **source-replica (master-slave)** and **master-master** topologies, in Real-Time, Immediate, or Deferred modes ([Rocket UniVerse Data Replication User Guide v11.3.5, Jan 2023](https://docs-be.rocketsoftware.com/bundle/UniVerse_DataReplicationUserGuide_V1135/raw/resource/enus/UniVerse_DataReplicationUserGuide_V1135.pdf?save_local=true)). Note that "master-master" here is **not active-active on the same data**: a single system can be both a publisher and a subscriber, but any *given file* can be either published or subscribed, **not both** ([Rocket U2 Replication overview, International Spectrum](https://www.intl-spectrum.com/resource/332/U2-Replication-An-Overview-of-our-Scalable-and-Robust-High-Availability-Solution.aspx)) — so there is no native multi-master conflict resolution. Subscribers are normally read-only; standby/failover and failback relationships are supported, including cross-platform (publisher and subscriber need not be the same OS). On failover, incomplete in-flight transactions on the subscriber are detected and logged to `REP_FAILOVER_LOG`. ⚠️ unverified — replication is asynchronous, so a publisher crash can lose transactions not yet shipped; the exact data-loss window is deployment-dependent. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Not in the Dynamo/Cassandra per-query sense. "Tunable" here means choosing an isolation level and replication mode, not quorum reads.
- **Clock dependency:** none for correctness. See [clocks-and-time](../concepts/clocks-and-time.md) — N/A.

## Schema
- **Schema-on-write vs schema-on-read:** effectively **schema-on-read / schema-light**. The file stores opaque delimited records; the meaning of each attribute lives in a separate **dictionary** (D-type / I-type/virtual-attribute definitions) and, ultimately, in the BASIC application code. db-engines describes it as schema-free with optional predefined types ([db-engines](https://db-engines.com/en/system/UniData,UniVerse)).
- **Migration/evolution:** adding an attribute is often a no-op on disk (just a new dictionary entry and code that reads it), which makes evolution cheap — but consistency of older records is the app's problem. No rigid `ALTER TABLE` lock because there is no rigid table.
- **Type system:** values are stored as ASCII strings; typing is optional/by convention. Native first-class support for **multivalued and multi-subvalued attributes** is the differentiator. Dates, times, and numerics are conventions interpreted by code/dictionary, not enforced storage types. No native JSON/geospatial/vector types (JSON/XML are supported as interchange formats, not storage types).

## Query interface
- **Language:** primarily a 4GL **BASIC** — **UniVerse BASIC** / **UniBasic** (UniData) — for procedural data access, plus a non-SQL **query/report language**: **RetrieVe** (UniVerse) and **UniQuery** (UniData). A **SQL mapping layer** exists (UniVerse has a fuller SQL implementation; UniData via ODBC/JDBC/UCI), but SQL is a bolt-on over the MultiValue model, not the native interface ([db-engines](https://db-engines.com/en/system/UniData,UniVerse)). Access also via ODBC, JDBC, OLE DB, UniObjects (.NET/Java/COM), RESTful HTTP and SOAP.
- **Transactions:** full multi-statement transactions via `TRANSACTION START` / `COMMIT` / `ROLLBACK` in BASIC, with record/file locking (`READU` = read-for-update lock, with a `LOCKED` clause to handle contention) ([intl-spectrum](http://www.intl-spectrum.com/Article/r403/Locking__Part_2_Traditional_Locking)). Atomicity/isolation depend on the chosen isolation level and on the app actually locking what it touches.
- **Native vs app-side:** secondary indexes are supported natively; joins and aggregations are typically expressed *within* records (the multivalued model embeds the "join") or done procedurally in BASIC rather than via a relational optimizer. RetrieVe/UniQuery do filtering, sorting and report breaks but are not a cost-based relational engine.
- **Stored procedures / UDFs:** yes — cataloged BASIC subroutines act as stored procedures; triggers are supported, written in U2 BASIC ([db-engines](https://db-engines.com/en/system/UniData,UniVerse)).

## Scaling & topology
- **Vertical vs horizontal:** **vertical**. There is no native sharding/partitioning of a database across nodes ([db-engines: partitioning none](https://db-engines.com/en/system/UniData,UniVerse)); you scale a single server up. Horizontal scaling is limited to offloading reads onto replicas.
- **Sharding:** none native. Any data partitioning is manual at the application/file level.
- **Read replicas:** yes, via U2 Data Replication; subscriber reads are **eventually consistent** (async log apply) and normally read-only.
- **Storage/compute separation:** no — coupled storage and compute on the host. See [storage-compute-separation](../concepts/storage-compute-separation.md) (N/A).

## Performance & durability
- **Write path:** durability is via transaction logging / journaling and the replication log; UniVerse ships a Recoverable File System and transaction logs used for recovery and for feeding replication. ⚠️ unverified — exact fsync/group-commit policy and crash data-loss window are configuration-dependent and not clearly documented in public sources; see [wal-and-durability](../concepts/wal-and-durability.md). With async replication, unshipped committed transactions can be lost if the primary fails before they propagate.
- **Throughput/latency:** hashed-file access gives fast keyed reads/writes when files are correctly sized; the dominant performance variable is **file sizing/overflow**. p99 degrades sharply when hashed files overflow their groups, forcing long chained reads — a well-known operational footgun specific to this storage model. ⚠️ unverified — no public, current independent benchmarks.
- **Compaction / vacuum / GC:** no background compactor; instead, **periodic file resizing** (`RESIZE`, and tools like `guide`/`HASH.HELP` for sizing analysis) is a manual/scheduled maintenance task. Neglecting it is the classic cause of creeping latency.

## Operations & maturity
- **Backup/restore, PITR:** OS-level and U2-specific backup of account/file structures; transaction logs and replication support recovery and standby failover/failback. PITR depends on retained transaction logs. ⚠️ unverified — granularity of point-in-time recovery in public docs.
- **Observability:** query plans in the relational sense are limited (no rich cost-based EXPLAIN); monitoring is via U2-specific tools, OS metrics, and log files. Less introspectable than a mainstream RDBMS.
- **Upgrade story:** in-place version upgrades; rolling upgrades are achievable via replication standbys but generally involve planned maintenance windows. Day-2 burden centers on file sizing, lock contention from long-held `READU` locks, and scarce specialist staffing.
- **Maturity:** very mature — UniVerse/UniData lineage dates to the mid-1980s (PICK roots to the late 1960s), with decades of production use in ERP and vertical apps. **No Jepsen report exists** for UniData/UniVerse. Best-known failure modes are operational (hashed-file overflow, lock contention, deadlocks) rather than novel distributed-systems bugs, because the core is single-node.

## Ecosystem & people
- **Canonical use cases:** long-lived transactional business systems — distribution/wholesale, healthcare, financial services, retail, government — often packaged ERP suites written in MultiValue BASIC where the database and application are deeply intertwined.
- **Anti-patterns:** greenfield projects; analytics/OLAP and ad-hoc BI at scale; anything needing horizontal scale-out, cloud-native elasticity, or a large hiring pool. Choosing this in 2026 for a new system means betting on a shrinking talent market.
- **Drivers/connectors:** ODBC, JDBC, OLE DB, UniObjects for .NET/Java, REST/SOAP gateways; bridges to BI and ETL exist but are not first-class like Postgres/MySQL. CDC/Kafka/dbt integration is weak and usually custom-built around replication logs or extracts.
- **Community/support:** commercial support from Rocket Software; a small but dedicated MultiValue community (u2ug, International Spectrum). Docs are vendor-published and reasonably thorough but behind product gating. Learning curve is steep for anyone coming from SQL — the mental model (records-with-multivalues, BASIC-as-query-engine, explicit locking) is genuinely different.

## Licensing & cost
- **OSS license & flavor:** none — **commercial, proprietary, closed source** ([db-engines](https://db-engines.com/en/system/UniData,UniVerse)). No source-available or open core. See [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 relicensing drama; it was never open.
- **Self-managed vs managed-only:** self-managed on-prem (AIX, HP-UX, Linux, Solaris, Windows). No first-party serverless/managed-cloud DBaaS in the Aurora/Atlas sense, though it can run on cloud VMs.
- **Lock-in:** high. The MultiValue model, embedded BASIC apps, and proprietary file format make migration to another engine a substantial rewrite — which is precisely why these systems persist.
- **Cost model:** traditional per-server / per-user / per-core commercial licensing plus maintenance; pricing is quote-based via Rocket. Not cheap-at-small; economics favor existing deployments, not new ones.

## Hardware / deployment
- **Resource profile:** disk- and I/O-bound for keyed access; benefits from RAM for OS file cache, but data need not fit in RAM. CPU rarely the bottleneck for typical OLTP.
- **Storage assumptions:** local block storage; NVMe/SSD helps overflowed-file scans. No special network-attached-storage design assumptions.
- **Footprint:** single-node server (clustered only for HA standbys via replication). Not embedded, not serverless.
- **Deployment:** on-prem or cloud VM; SaaS-style managed offerings are limited. Container/k8s use is possible but uncommon and not the canonical deployment; StatefulSet-style operation is atypical for this market.

## Bottom line
Reach for UniData or UniVerse essentially only if you already run one: they are well-supported, mature MultiValue databases whose value is the decades of working BASIC application code on top of them, not the engine itself. The model is genuinely good at embedding hierarchical, multivalued business records without joins, and keyed access is fast when files are sized right. Do not pick either for new systems — single-node scaling, no native sharding, lock-based application-managed concurrency, weak analytics/BI/CDC integration, and a shrinking talent pool all argue against it. The single biggest gotcha is operational, not theoretical: **hashed-file sizing/overflow silently destroys p99 latency** if you don't actively maintain it, and "ACID" is only real if your application explicitly locks and transacts — the default idiom gives no isolation.

## Sources
- [Rocket U2 — Wikipedia](https://en.wikipedia.org/wiki/Rocket_U2)
- [UniData, UniVerse — db-engines system properties](https://db-engines.com/en/system/UniData,UniVerse)
- [Rocket UniVerse U2 Data Replication User Guide v11.3.5 (Jan 2023)](https://docs-be.rocketsoftware.com/bundle/UniVerse_DataReplicationUserGuide_V1135/raw/resource/enus/UniVerse_DataReplicationUserGuide_V1135.pdf?save_local=true)
- [International Spectrum — Locking Part 2: Traditional Locking (isolation levels, READU)](http://www.intl-spectrum.com/Article/r403/Locking__Part_2_Traditional_Locking)
- [Rocket UniData product page](https://www.rocketsoftware.com/en-us/products/multivalue/unidata)
