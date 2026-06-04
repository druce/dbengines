---
name: InterSystems IRIS
slug: intersystems-iris
rank: 118
data_model: Multi-model
license: Proprietary / commercial (source-available SDK; free Community Edition, no production use)
summary: Commercial multi-model DBMS built on the MUMPS "globals" engine; one physical store projected as relational, object, document, and key-value, deeply entrenched in healthcare.
last_researched: 2026-06-04
confidence: high
---

# InterSystems IRIS

> A proprietary multi-model data platform — successor to Caché — where SQL tables, objects, JSON documents, and key-value all sit on one MUMPS-derived multidimensional "global" store; powerful and battle-tested in healthcare, but with an unusual default of READ UNCOMMITTED isolation and a niche, closed ecosystem.

## Identity
- **Taxonomy / data model:** [multi-model](../concepts/multi-model.md). One unified engine exposes the same data as relational (SQL), object, document (JSON), key-value, and the underlying multidimensional sparse array ("globals") simultaneously — InterSystems markets this as "store once, access as any model" with no mapping layer ([data models](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=PAGE_multimodel)). Lineage: IRIS (GA 2019) absorbs the capabilities of InterSystems Caché + Ensemble, both M/mumps-rooted.
- **Storage model:** all data lives in **globals** — B-tree-backed, tree-structured sparse multidimensional arrays, accessed without an intervening file-system abstraction ([globals intro](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AFL_GLOBALS)). Effectively a B-tree / ordered-KV engine (not [LSM](../concepts/lsm-vs-btree.md)); row-oriented by default, with columnar storage available for analytic tables in recent versions.
- **Workload:** primarily OLTP, but positioned as HTAP/"translytical." Physical separation for analytics is at the storage-layout level, not a separate engine or replica: selected tables (or columns) use **columnar storage** — values encoded in ~64K-value chunks via a `$vector` datatype with vectorized query processing — while transactional tables stay row-oriented, and mixed row/columnar layouts are supported on one table ([columnar storage](https://community.intersystems.com/post/when-use-columnar-storage)). So OLTP and OLAP share the same store and journal; isolation is by layout (and optionally read-scaled ECP application servers), not by a dedicated analytics replica. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** InterSystems publishes no explicit CAP positioning and no [Jepsen-style](../concepts/cap-pacelc.md) analysis, but the mirroring (HA) design is single-primary: a synchronous backup retrieves and acknowledges the primary's journal records before they are durable, and an optional **arbiter** mediates failover decisions so the mirror promotes the backup (with no committed-data loss) rather than serving divergent writes — i.e. CP-leaning behavior under partition ([mirroring architecture](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GHA_mirror_set)). The arbiter prevents split-brain by ensuring only one failover member becomes primary. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — not characterized by the vendor.
- **Default isolation & what's achievable:** **the SQL default isolation is READ UNCOMMITTED** when not inside an explicit transaction or when none is specified ([SET TRANSACTION](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_settransaction)). This is a major divergence from the usual "ACID database" expectation — out of the box, queries can read dirty, partially-applied, or to-be-rolled-back values. Higher levels are opt-in: READ COMMITTED, and READ VERIFIED (re-checks conditions against newly committed data) ([SET TRANSACTION](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_settransaction)). At the global/lock layer, transactions are atomic and durable; without locks they behave like READ UNCOMMITTED, and SERIALIZABLE is achievable only by explicit application locking ([transactions in globals](https://community.intersystems.com/post/transactions-global-intersystems-iris)). So "ACID" here means atomic+durable journaled writes, **not** snapshot or serializable isolation by default. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **mirroring** = single-primary with a synchronous failover (backup) member plus optional async DR members; automatic, no-data-loss failover mediated by an arbiter ([mirroring architecture](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GHA_mirror_set)). Enterprise Cache Protocol (ECP) adds distributed caching application servers that read a remote data server with cache coherency maintained by the data server. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Per-transaction isolation level (above); no Dynamo-style per-query quorum tuning.
- **Clock dependency:** no documented reliance on synchronized clocks for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** schema-on-write for SQL/object classes (classes define persistent tables); schema-on-read available via dynamic objects and document (JSON) APIs over globals. The same class can be reached as a table and as an object.
- **Migration/evolution:** schema is defined via ObjectScript class definitions; recompiling classes regenerates storage maps. ⚠️ unverified — extent of online/non-locking DDL on large populated tables is not clearly documented.
- **Type system:** native SQL types plus object types, JSON (dynamic objects/arrays), and a first-class **VECTOR** type with `VECTOR_COSINE()` / `VECTOR_DOT_PRODUCT()` and a disk-based ANN index added in recent releases ([vector search overview](https://community.intersystems.com/post/overview-vector-search-functionality)). See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** InterSystems SQL (a broadly standard dialect with proprietary extensions), the object access layer, document/JSON APIs, direct global access, and **ObjectScript** (the M-derived procedural language); **Embedded Python** is also supported server-side.
- **Transactions:** full multi-statement transactions with `START/COMMIT/ROLLBACK` and savepoints, atomic and durable — but see the READ UNCOMMITTED default above.
- **Native vs app-side:** native secondary indexes, joins, aggregations, window functions in SQL; bitmap and bitslice indexes for analytics.
- **Stored procedures / UDFs:** yes — class methods exposed as stored procedures, written in ObjectScript, SQL, or Python.

## Scaling & topology
- **Vertical vs horizontal:** strong vertical scaling; horizontal via **sharding** (tables partitioned into row-set shards across data nodes) and **ECP** application-server scale-out for compute/cache ([sharding guide](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSCALE_SHARDING)).
- **Sharding:** declared per table; rows hash-distributed across data nodes. Resharding/redistribution after adding nodes is an operational exercise. ⚠️ unverified — degree of automatic rebalancing.
- **Read replicas:** ECP application servers cache data locally and read from the data server; mirror async members can serve reads. Reads honor the configured isolation level (so consistency depends on level chosen).
- **Storage/compute separation:** ECP separates the caching/compute tier (application servers) from the data server, a partial [storage-compute-separation](../concepts/storage-compute-separation.md) pattern; not a cloud object-store-backed architecture like Aurora/Snowflake.

## Performance & durability
- **Write path:** write-ahead **journaling** (the journal is the WAL equivalent) plus the write daemon flushing the database cache; commits are journaled for durability and crash recovery. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact fsync/group-commit policy and the worst-case data-loss window on crash are not detailed in sources reviewed.
- **Throughput/latency:** the globals engine is known for very low-latency point access and high transactional throughput, the basis of its healthcare reputation. ⚠️ unverified — no independent p99/tail benchmarks reviewed; vendor figures only.
- **Compaction / GC:** B-tree globals do not have LSM-style background compaction; space management and journal purging are the relevant maintenance tasks. No vacuum-equivalent bloat problem like [MVCC](../concepts/mvcc.md) vacuum.

## Operations & maturity
- **Backup/restore, PITR:** online backup, external (snapshot-friendly) backup, and journal-based roll-forward for point-in-time recovery.
- **Observability:** SQL query plans / `EXPLAIN`, SQL statistics, system metrics (via `^PERFMON`/`^mgstat` and a Prometheus-compatible metrics endpoint), and audit/journal logs.
- **Upgrade story:** in-place version upgrades; mirroring enables reduced-downtime rolling upgrades of the pair. Day-2 burden is non-trivial and skill-specific — ObjectScript/M expertise is scarce.
- **Maturity:** very mature lineage (Caché dates to 1997; M to the 1960s–70s), heavily production-proven in hospitals, EHRs (e.g., Epic historically runs on Caché/M), and financial back offices. **No public [Jepsen](../concepts/consensus-raft-paxos.md) report exists.** ⚠️ unverified — distributed-correctness claims rest on vendor documentation, not third-party verification.

## Ecosystem & people
- **Canonical use cases:** healthcare/clinical systems (IRIS for Health adds FHIR, HL7, interoperability), high-throughput transactional apps needing object+SQL on one store, integration/interoperability hubs (Ensemble heritage). Anti-patterns: teams wanting open-source/no-lock-in, cloud-native object-store separation, commodity SQL skills, or a simple drop-in OLAP warehouse — IRIS's value depends on its proprietary stack and M/ObjectScript expertise.
- **Drivers / connectors:** JDBC/ODBC, .NET, Python (including Embedded Python and DB-API), Node.js, native global APIs; ⚠️ unverified — breadth of CDC/Kafka/dbt/BI integrations versus mainstream engines; ecosystem is far smaller than Postgres/MySQL.
- **Community & docs:** active vendor-run Developer Community and thorough official docs; commercial support from InterSystems. Learning curve is steep due to ObjectScript and the globals mental model; engineer availability is limited.

## Licensing & cost
- **License:** **proprietary/commercial**, not open source. A free **Community Edition** is downloadable for development/learning but is not licensed for production and is capacity-limited. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-managed on-prem/cloud, containers, and an InterSystems IRIS cloud/managed offering. Lock-in is significant: ObjectScript, globals, and the multi-model projection are proprietary with no compatible alternative.
- **Cost model:** ⚠️ unverified — pricing is **quote-only**; InterSystems does not publish list prices ([pricing reference](https://www.g2.com/products/intersystems-iris/pricing)). Historically license-based (cores/users/capacity); expect enterprise-tier costs that grow with scale.

## Hardware / deployment
- **Resource profile:** benefits heavily from a large global buffer (database cache) in RAM; working set in memory drives its low-latency reputation, though it is not strictly an in-memory DB and persists to disk.
- **Storage assumptions:** durability tied to fast local storage (NVMe/SSD) for journals and database files; works on network-attached storage but latency-sensitive for the write daemon/journal.
- **Footprint:** single-node, clustered (mirror + sharded + ECP), and containerized; not embedded and not a true serverless engine, though a managed cloud option exists.
- **Deployment:** on-prem, all major clouds (marketplace images), Kubernetes via the InterSystems Kubernetes Operator (IKO); StatefulSet-style stateful deployment.

## Bottom line
Reach for InterSystems IRIS if you live in healthcare/interoperability or already run Caché/Ensemble and want one engine serving SQL, objects, documents, and KV over the same data with proven transactional throughput. Avoid it if you value open source, commodity skills, cloud-native storage/compute separation, or transparent pricing — it is a deeply proprietary, niche stack. The single biggest gotcha: **SQL defaults to READ UNCOMMITTED isolation**, so "ACID" here guarantees atomic, durable journaled writes but not consistent reads unless you explicitly raise the isolation level or take locks.

## Sources
- [Data Models — InterSystems IRIS docs](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=PAGE_multimodel)
- [Introduction to Globals — InterSystems IRIS docs](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AFL_GLOBALS)
- [SET TRANSACTION (SQL) — isolation levels](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_settransaction)
- [Transactions in Global InterSystems IRIS — Developer Community](https://community.intersystems.com/post/transactions-global-intersystems-iris)
- [Horizontally Scaling with Sharding — Scalability Guide](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSCALE_SHARDING)
- [Vector Search overview — Developer Community](https://community.intersystems.com/post/overview-vector-search-functionality)
- [Licensing — InterSystems IRIS docs](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=PAGE_licensing)
- [InterSystems IRIS product page](https://www.intersystems.com/products/intersystems-iris/)
