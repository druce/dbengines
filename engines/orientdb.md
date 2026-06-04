---
name: OrientDB
slug: orientdb
rank: 103
data_model: Multi-model (document + graph + key-value + object)
license: Apache 2.0 (permissive)
summary: Java multi-model DB (graph+document) with RID pointer-based traversal and SQL; technically capable but effectively orphaned after SAP dropped support, with a fragile distributed layer.
last_researched: 2026-06-04
confidence: high
---

# OrientDB

> A single-engine multi-model database (graph + document + key-value + object) with O(1) pointer-based edge traversal and a SQL dialect — capable on a single node, but its distributed layer is fragile and the project has been effectively orphaned since SAP withdrew commercial support in 2021.

## Identity
- **Taxonomy / data model:** [multi-model](../concepts/multi-model.md) DBMS combining graph, document, key-value, and object models in one core engine (not adapters over a single model). Relationships are stored as direct physical links between records via Record IDs (RIDs), giving constant-time edge traversal without index lookups or JOINs. See [graph-data-model](../concepts/graph-data-model.md).
- **Storage model:** "plocal" (paginated local) is the primary engine — page-oriented disk storage with [WAL](../concepts/wal-and-durability.md), B-tree and extendible-hash indexes, and surrogate keys (RIDs) encoding cluster + physical position. Row/record-oriented, not columnar; not an [LSM](../concepts/lsm-vs-btree.md) store. An in-memory engine also exists.
- **Workload:** OLTP-oriented (operational graph/document workloads, traversals, connected-data queries). Not an analytics engine; no columnar store, no MPP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** Configurable, but in practice CP-leaning when `writeQuorum` is set to a majority. OrientDB claims strong consistency only if `writeQuorum` is the majority of nodes ([docs](https://orientdb.dev/docs/3.1.x/distributed/Distributed-Architecture.html)). With lower quorum it is AP and can diverge. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no formal PACELC characterization published. Practically: under partition (P) it sacrifices availability for consistency only at majority quorum; else (E) it favors latency, since transactions are optimistic and locks are taken only at commit.
- **Default isolation:** READ COMMITTED is the default and the **only** level available over the remote (network) protocol; REPEATABLE READ is available only with embedded `plocal`/`memory` connections ([docs](https://orientdb.dev/docs/3.1.x/internals/Transactions.html)). Concurrency control is optimistic [MVCC](../concepts/mvcc.md) — record versions are checked at commit; no serializable isolation. An "ACID" claim here means single-node ACID with read-committed/repeatable-read, **not** serializability. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** multi-master ("multi-master" per project tagline) — every node accepts reads and writes; replication and cluster membership historically coordinated by **Hazelcast**. Distributed commits use a two-phase-commit-style protocol with optimistic locking applied at commit time. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** yes, via per-cluster `writeQuorum` / `readQuorum` settings.
- **Clock dependency:** ⚠️ unverified — no documented reliance on synchronized clocks (no TrueTime/HLC scheme); ordering rests on record versions and the commit protocol. See [clocks-and-time](../concepts/clocks-and-time.md).
- **Split-brain caveat:** OrientDB's reliance on Hazelcast for distributed locking led to split-brain / lock-safety problems, prompting the team to write their own distributed lock manager and reduce Hazelcast to startup metadata consensus, with plans to remove it entirely ([OrientDB distributed docs / engineering notes](https://orientdb.dev/docs/3.1.x/distributed/Distributed-Architecture.html)). ⚠️ unverified — no published independent [Jepsen](https://jepsen.io/) report exists for OrientDB; treat distributed-mode safety claims with caution and test before relying on them.

## Schema
- **Schema model:** flexible — supports schema-full, schema-less, and schema-mixed classes. You can enforce types and constraints per property or leave records open. Effectively schema-on-write where defined, schema-on-read otherwise.
- **Migration/evolution:** classes and properties can be altered at runtime via SQL DDL (`CREATE CLASS`, `ALTER PROPERTY`); largely online for schema metadata. ⚠️ unverified — locking behavior of large data-rewriting alters is not well documented.
- **Type system:** rich — strings, numerics, dates, embedded and linked records, lists/sets/maps, binary, plus links (RIDs) and edge/vertex types. Geospatial support via a spatial module. No native vector/ANN type.

## Query interface
- **Language:** an extended **SQL** dialect with graph traversal constructs (`MATCH`, `TRAVERSE`, `MOVE`), plus **Gremlin** (via TinkerPop integration) for graph queries. Not SQL-standard compliant. No Cypher.
- **Transactions:** full multi-statement ACID on a single node (optimistic MVCC); distributed transactions via 2PC-style commit with the caveats above.
- **Native vs app-side:** native graph traversal (pointer-following), secondary indexes (unique, notunique, full-text, spatial), aggregations, and projections. JOINs are replaced by link traversal.
- **Stored procedures / UDFs:** server-side functions in JavaScript (and other JVM scripting), callable from SQL/REST.

## Scaling & topology
- **Vertical vs horizontal:** scales vertically well; horizontal scaling via the multi-master distributed cluster. Sharding is supported by manually splitting a class across clusters/nodes — **manual, not automatic**, and resharding is operationally painful. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas:** all nodes are full replicas accepting reads/writes; read consistency depends on `readQuorum` (read-one can be stale; majority reads cost latency).
- **Storage/compute separation:** none — storage and compute are co-located per node. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WAL with paginated atomic operations; fsync policy is configurable. Default async/group-commit behavior trades a small crash data-loss window for throughput; tunable toward durability. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** strong single-node traversal performance owing to RID pointer-chasing (no index lookup per hop). ⚠️ unverified — no recent, credible, independent p99/tail benchmarks; vendor benchmarks are dated and should not be taken as fact.
- **Compaction / GC:** page-based storage with JVM garbage collection; long GC pauses on the JVM heap can affect tail latency. ⚠️ unverified — no detailed public GC/compaction tuning data.

## Operations & maturity
- **Backup/restore:** online non-blocking backup, export/import, and incremental backup (incremental backup was historically an enterprise-only feature; verify availability in the open-source build). PITR support is limited compared to mature RDBMSs.
- **Observability:** SQL `EXPLAIN`/profiling, query metrics, and a Studio web console; slow-query visibility is basic.
- **Upgrade story:** version upgrades historically required care and sometimes export/import across majors; rolling upgrades in distributed mode are not a strong suit. Day-2 burden is meaningful given the thin maintenance team.
- **Maturity:** mature codebase (since 2010) but **declining maintenance**. Created by Luca Garulli; sponsor OrientDB Ltd was acquired by CallidusCloud (2017), then SAP via the $2.4B CallidusCloud deal (2018). SAP **stopped commercial support on Sept 1, 2021** ([GitHub issue #9734](https://github.com/orientechnologies/orientdb/issues/9734)); Garulli left to build ArcadeDB. Development continues as low-volume community-driven bugfix releases on the 3.2.x line (3.2.53 in June 2026 per [GitHub releases](https://github.com/orientechnologies/orientdb/releases); patch cadence is roughly monthly, but these are stability/security fixes, not feature work). Note: SAP Enterprise OrientDB's capabilities were themselves open-sourced under Apache 2.0 as an "enterprise agent" add-on in Jan 2022 ([announcement](https://orientdb.dev/news/enterprise-agent-open-source/)); SAP's own maintenance of that product ended Dec 31, 2023. The OrientDB storage-engine author (Andrii Lomakin) later forked the codebase as **YouTrackDB** (Dec 30, 2024), now developed by **JetBrains** ([dbdb.io](https://dbdb.io/db/youtrackdb)). Known failure modes center on the distributed/Hazelcast layer (split-brain, lock safety). No published Jepsen report.

## Ecosystem & people
- **Canonical use cases:** connected/graph data with mixed document attributes where you want one engine instead of stitching a graph DB and a document DB; master-data and relationship-heavy operational apps.
- **Anti-patterns:** new greenfield projects (maintenance risk), large-scale OLAP/analytics, workloads needing serializable isolation, and high-stakes multi-master deployments requiring proven partition safety. For graph specifically, [neo4j](neo4j.md) is more actively maintained; for multi-model alternatives consider [arangodb](arangodb.md) or arcadedb.
- **Drivers/connectors:** Java (native + JDBC), REST/HTTP, TinkerPop/Gremlin, and community drivers for Python/Node/.NET. CDC/Kafka/dbt/BI integration is thin and dated.
- **Community size, support, docs:** community is small and shrinking; no first-party commercial support since SAP exited (SAP "Enterprise OrientDB" exists but is legacy). Docs are extensive but aging and span multiple version trees; learning curve is moderate.

## Licensing & cost
- **OSS license:** Apache 2.0 — fully permissive. SAP's former enterprise build was the commercial flavor, but its capabilities were open-sourced under Apache 2.0 as an "enterprise agent" add-on in Jan 2022, so there is effectively no open-core split today. No post-2018 relicensing to source-available. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-managed only; no first-party managed cloud service. Some legacy SAP/AWS Marketplace listings exist but are not actively positioned.
- **Lock-in:** low at the license level (permissive); practical lock-in via the OrientDB SQL dialect and RID-based modeling. Migration off is non-trivial because of the proprietary query/graph constructs.
- **Cost model:** free (self-hosted); cost is operational/staffing, dominated by the maintenance and risk burden of an under-maintained engine.

## Hardware / deployment
- **Resource profile:** JVM-based; memory-sensitive (heap + page cache), benefits from large RAM for the working set; CPU for traversal, disk for durability. Working set need not fully fit in RAM but performance degrades when it spills.
- **Storage assumptions:** local disk; NVMe/SSD strongly preferred for the paginated WAL/storage. No special network-storage design.
- **Footprint:** single-node or clustered (multi-master); also embeddable as a Java library (in-process `plocal`/`memory`). See [embedded-databases](../concepts/embedded-databases.md). Not serverless.
- **Deployment:** on-prem / self-hosted; runs in containers and on k8s as a StatefulSet, but clustered StatefulSet operations inherit the distributed-layer fragility.

## Bottom line
Reach for OrientDB only if you already run it, or need a single embeddable JVM engine that unifies graph and document data on one node and you can live with read-committed isolation. Do **not** pick it for new projects, analytics, serializable workloads, or production multi-master clusters that demand proven partition safety — the distributed layer (historically Hazelcast-based) has documented split-brain/lock issues and no published Jepsen validation. The single biggest gotcha: the project lost its commercial backer when SAP dropped support in 2021, so you are betting on a small community maintainer — prefer actively maintained alternatives like arcadedb, [arangodb](arangodb.md), or [neo4j](neo4j.md).

## Sources
- [OrientDB — Wikipedia](https://en.wikipedia.org/wiki/OrientDB)
- [OrientDB Transactions (official docs, 3.1.x)](https://orientdb.dev/docs/3.1.x/internals/Transactions.html)
- [OrientDB Distributed Architecture (official docs, 3.1.x)](https://orientdb.dev/docs/3.1.x/distributed/Distributed-Architecture.html)
- [GitHub: orientechnologies/orientdb](https://github.com/orientechnologies/orientdb)
- [GitHub issue #9734 — SAP dropped support Sept 1 2021](https://github.com/orientechnologies/orientdb/issues/9734)
- [OrientDB development statistics of 2025](https://orientdb.dev/news/orientdb-development-stats-2025/)
- [GitHub releases — orientdb (latest 3.2.53, June 2026)](https://github.com/orientechnologies/orientdb/releases)
- [SAP Enterprise OrientDB open-sourced (Jan 2022)](https://orientdb.dev/news/enterprise-agent-open-source/)
- [Database of Databases — OrientDB](https://dbdb.io/db/orientdb)
- [Database of Databases — YouTrackDB (JetBrains fork)](https://dbdb.io/db/youtrackdb)
- [Jepsen (no OrientDB report exists; referenced for testing methodology)](https://jepsen.io/)
