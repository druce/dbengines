---
name: JanusGraph
slug: janusgraph
rank: 127
data_model: Graph
license: Apache License 2.0 (permissive)
summary: Apache-licensed distributed property graph that layers Gremlin/TinkerPop over a pluggable Cassandra/HBase/Bigtable store — scales horizontally but inherits the backend's eventual consistency and weak transactional guarantees.
last_researched: 2026-06-04
confidence: medium
---

# JanusGraph

> A horizontally-scalable Apache TinkerPop property graph that is really a Gremlin query layer bolted onto a separate wide-column store (Cassandra/HBase/Bigtable) — so its consistency, durability, and "ACID" story are whatever that backend gives you, which on the usual backends is *not* serializable and *not* multi-row atomic.

## When to use

**Use JanusGraph if:**
- ✅ You need an open, vendor-neutral (Apache 2.0, Linux Foundation) property graph that scales horizontally on commodity/Hadoop infrastructure
- ✅ You already run Cassandra/HBase/Bigtable and your team can operate a multi-tier distributed system
- ✅ Your workload is large connected-data graphs — knowledge graphs, fraud/identity, recommendation, network topology, master data
- ✅ You want Gremlin/TinkerPop with native OLAP via Spark/Hadoop

**Avoid JanusGraph if:**
- ❌ On its common backends it is eventually consistent and not ACID — no serializable isolation or multi-row atomic writes, and even uniqueness locks depend on synchronized clocks
- ❌ Your graph fits on one node (the 3-system stack overhead is unjustified — consider [neo4j](neo4j.md))
- ❌ You need strict cross-entity serializability, ultra-low-latency single-key lookups, or lack the ops capacity for storage + search + graph tiers

## Identity
- **Taxonomy / data model:** Labeled property graph (vertices, edges, properties), accessed via [graph-data-model](../concepts/graph-data-model.md) and the Gremlin traversal language. Successor fork of TitanDB, brought under open governance in 2017 and later into the Linux Foundation (LF AI & Data). See [graph-data-model](../concepts/graph-data-model.md).
- **Storage model:** No native storage engine of its own. It is a graph *engine* over a pluggable storage backend, with an adjacency-list encoding mapped onto a wide-column key→column-family layout. On-disk format and [lsm-vs-btree](../concepts/lsm-vs-btree.md) characteristics are entirely the backend's: Cassandra/ScyllaDB (LSM), HBase/Bigtable (LSM), or BerkeleyDB (B-tree, single-node). Mixed (search) indexes live in a separate index backend — Elasticsearch, Solr, or embedded Lucene. See [wide-column](../concepts/wide-column.md), [full-text-search](../concepts/full-text-search.md).
- **Workload:** OLTP-style graph traversals with native OLAP via Apache Spark/Hadoop (Gremlin `SparkGraphComputer`). Not HTAP in any unified sense — analytical traversals run as a separate batch job over the same store, not on a columnar replica. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Inherits the backend. With Cassandra (the typical choice) it is effectively **AP / eventually consistent** — JanusGraph documents these as "eventually-consistent storage backends." With HBase/Bigtable the backend is CP at the row level. JanusGraph itself adds no global consensus layer. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** On Cassandra: **PA/EL** — under partition it stays available and reconciles later; absent partition it favors latency (tunable per-query consistency on the C* side). On HBase: closer to **PC/EC**. ([JanusGraph docs — eventual consistency](https://docs.janusgraph.org/advanced-topics/eventual-consistency/))
- **Default isolation & what's achievable:** This is the load-bearing caveat. Per the docs, **"JanusGraph transactions are not necessarily ACID. They can be so configured on BerkeleyDB, but they are not generally so on Cassandra or HBase"** because **"the underlying storage system does not provide serializable isolation or multi-row atomic writes and the cost of simulating those properties would be substantial."** ([JanusGraph docs — transactions](https://docs.janusgraph.org/basics/transactions/)) Within a single transaction you get snapshot-style consistency of the read-set; across transactions on a distributed backend you get optimistic concurrency with last-write-wins reconciliation, not serializability. Treat any blanket "ACID graph database" claim as true only on single-node BerkeleyDB. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Delegated to the backend (Cassandra leaderless quorum R+W>N; HBase single-leader-per-region via HDFS). Failover/split-brain behavior is the backend's. See [replication-models](../concepts/replication-models.md).
- **Consistency-critical writes / locking:** Because eventually-consistent backends give no isolation, JanusGraph must acquire **locks** to enforce uniqueness constraints and consistency on those properties; locking is **off by default** for efficiency. Two providers: a backend-agnostic key-consistent timestamp-lock, and a Cassandra-specific Astyanax-recipe lock. ([JanusGraph docs — eventual consistency](https://docs.janusgraph.org/advanced-topics/eventual-consistency/))
- **Clock dependency:** Both locking mechanisms **require synchronized clocks across the cluster**; timestamp-based conflict resolution also depends on clock skew being bounded. A real correctness dependency on NTP-grade clocks. See [clocks-and-time](../concepts/clocks-and-time.md).
- **Tunable consistency?** Yes, indirectly — via the backend's consistency levels (e.g., Cassandra `read`/`write` consistency) plus JanusGraph's per-element consistency modifiers (`LOCK`, `FORK`).

## Schema
- **Schema-on-write (explicit, flexible).** JanusGraph has an explicit schema of vertex labels, edge labels, and property keys with cardinality and data types, but it can be configured to auto-create schema elements on first use (schema-on-read-ish). Recommended practice is to define schema up front.
- **Migration/evolution:** Schema elements can be added online. Some changes (renaming, changing index status) require a managed, sometimes multi-step reindex workflow; you generally cannot drop/redefine a property key in place. Reindexing existing data is a batch job (MapReduce/Spark or the management API).
- **Type system:** Property keys typed (String, numeric types, Boolean, Date, Geoshape, UUID, arrays). Native geospatial via Geoshape; full-text/geo/numeric-range search only through a mixed index backend (ES/Solr/Lucene). No native vector/ANN type.

## Query interface
- **Language:** Gremlin (Apache TinkerPop) — an imperative/functional traversal DSL, not SQL. Accessible embedded (JVM), over the Gremlin Server via WebSocket/HTTP, or by language drivers. No declarative pattern language like Cypher natively (some compatibility layers exist externally).
- **Transactions:** TinkerPop-style — a transaction opens on first operation per thread, closed via `commit()`/`rollback()`. Multi-statement within a transaction, but ACID guarantees are backend-limited (see above). Supports thread-independent transactions (`createThreadedTx()`) and high concurrency within one transaction.
- **Native vs app-side:** Traversals, joins-as-graph-walks, and aggregations are native to Gremlin. Composite indexes (exact-match, backend-native) and mixed indexes (range/full-text/geo via ES/Solr) accelerate vertex lookups; absent a suitable index, global queries degrade to full scans.
- **Stored procedures / UDFs:** No SQL stored procedures. Custom logic via Gremlin steps/closures (Groovy), JVM-side custom functions, and pluggable index/storage adapters.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal — adding storage nodes (Cassandra/HBase) grows capacity and throughput. JanusGraph (Gremlin Server) instances are stateless and scale independently of the storage tier.
- **Sharding/partitioning:** Data is partitioned by the backend's key distribution (Cassandra token ring / HBase region splits). Supernodes (very high-degree vertices) are a classic hotspot; JanusGraph offers vertex-cut partitioning for them but it must be planned. Resharding is the backend's concern. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** Provided by the backend; on Cassandra reads from replicas are eventually consistent unless quorum is configured.
- **Storage/compute separation:** Yes by design — graph compute (Gremlin Server) is fully decoupled from the storage and index tiers. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Durability is the backend's: Cassandra commitlog + memtable/SSTable, HBase WAL on HDFS. Data-loss window on crash = the backend's fsync/commitlog policy (e.g., Cassandra's periodic commitlog sync can lose the last ~10s of writes by default). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Good for deep traversals when the working set is indexed and cache-resident; JanusGraph maintains a database-level cache and per-transaction cache. p99 tail is dominated by (a) backend compaction/repair, (b) supernode traversals, and (c) cross-store fan-out (lookups hitting many partitions/regions). Multi-hop traversals that touch many keys can have wide tails on distributed backends.
- **Compaction/vacuum/GC:** Inherited from the backend — Cassandra compaction and anti-entropy repair, HBase compaction — both with the usual p99 impact. JVM GC on Gremlin Server is an additional tail-latency source.

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** Delegated to the backend (Cassandra snapshots/medusa, HBase snapshots, BerkeleyDB file copy) plus separate backup of the index backend. No unified built-in PITR across graph+index — keeping store and index consistent after restore is an operator responsibility.
- **Observability:** Metrics via Metrics/JMX (and Ganglia/Graphite reporters); Gremlin `profile()`/`explain()` for traversal plans; plus all the backend's own tooling. Operating JanusGraph means operating *three* systems (graph servers, storage backend, index backend).
- **Upgrade story:** Rolling at the Gremlin Server tier; backend upgrades follow Cassandra/HBase procedures. Day-2 burden is high — you own the operational complexity of a distributed store, a search cluster, and the graph layer, plus reindex jobs.
- **Maturity & failure modes:** Production-proven at large scale (e.g., used at IBM, and graph platforms at major firms). Known failure modes: supernode hotspots, ghost/phantom vertices and stale index entries after partial failures, the clock-synchronization dependency for locking, and surprises from assuming ACID on Cassandra. **⚠️ unverified —** no formal Jepsen analysis of JanusGraph is known to exist; its safety properties are effectively those of the chosen backend (Cassandra/HBase have their own Jepsen histories).

## Ecosystem & people
- **Canonical use cases:** Large connected-data graphs needing horizontal scale on commodity/Hadoop infrastructure — knowledge graphs, fraud/identity graphs, recommendation, network/IT topology, master data. Pairs well with existing Cassandra/HBase shops.
- **Anti-patterns:** Applications needing strict cross-entity ACID/serializability (use a relational or single-node graph); small graphs that fit one node (the 3-system operational overhead is unjustified — consider [neo4j](neo4j.md) or an embedded store); ultra-low-latency single-key lookups (a KV store is simpler); workloads dominated by supernodes without partitioning planning.
- **Drivers/connectors:** Any TinkerPop-compatible Gremlin driver (Java, Python `gremlinpython`, .NET, JS, Go). Integrates with Spark/Hadoop for OLAP. CDC/Kafka/dbt/BI integration is mostly via the backend or custom; not a first-class story.
- **Community/support:** Active open-source community under the Linux Foundation; no single dominant commercial vendor offering managed JanusGraph (some hosted/consulting options exist). Docs are reasonable but assume you understand the backend. Steep learning curve: Gremlin + distributed-store operations.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, no post-2018 relicensing. Genuinely open and vendor-neutral (Linux Foundation governance). See [license-taxonomy](../concepts/license-taxonomy.md). Note the index backends differ: Elasticsearch went source-available (SSPL/Elastic License) in 2021 before re-adding AGPL in 2024; Solr/Lucene remain Apache 2.0.
- **Self-managed vs managed:** Predominantly self-managed. No flagship first-party managed cloud service; you run it yourself (often on Cassandra/HBase you also manage). Low software lock-in (open standards: TinkerPop/Gremlin), but high *operational* commitment.
- **Cost model:** No license cost; cost is infrastructure + heavy operational labor for the multi-tier stack. Cheap-at-small is misleading — the minimum viable production footprint (storage cluster + index cluster + graph servers) is substantial.

## Hardware / deployment
- **Resource profile:** Memory-sensitive (JVM heap + caches on Gremlin Server; backend caches matter a lot); traversal performance is best when hot data fits in RAM/caches. Backend tier is disk- and CPU-bound per its own profile. Working set does not have to fit in RAM but performance falls off a cliff when it does not.
- **Storage assumptions:** Follows the backend — NVMe/local-SSD strongly preferred for Cassandra/HBase; tolerates network-attached storage poorly for write-heavy workloads.
- **Footprint:** Clustered/distributed for real use; embeddable single-node mode via BerkeleyDB + Lucene for dev/small graphs. JVM-based throughout.
- **Deployment:** On-prem or self-managed cloud; container/Kubernetes-friendly (stateless Gremlin Server in Deployments, backend as StatefulSets) but you wear the StatefulSet operational realities of the storage and search clusters.

## Bottom line
Reach for JanusGraph when you need an **open, vendor-neutral, horizontally-scalable property graph** on top of infrastructure you already run (Cassandra/HBase/Bigtable) and your team is comfortable operating a multi-tier distributed system. Do **not** reach for it if you need real serializable ACID across entities, if your graph fits on one node, or if you lack the ops capacity for a 3-system stack — a single-node graph DB will be far less painful. The single biggest gotcha: on its common backends JanusGraph is **eventually consistent and not ACID**; correctness of its uniqueness/consistency locks even depends on synchronized clocks — so design assuming last-write-wins, not transactions.

## Sources
- [JanusGraph docs — Transactions](https://docs.janusgraph.org/basics/transactions/)
- [JanusGraph docs — Eventually-Consistent Storage Backends](https://docs.janusgraph.org/advanced-topics/eventual-consistency/)
- [JanusGraph homepage / overview](https://janusgraph.org/)
- [GitHub — JanusGraph/janusgraph (Apache 2.0)](https://github.com/JanusGraph/janusgraph)
- [JanusGraph joins LF AI & Data](https://lfaidata.foundation/blog/2021/01/12/janusgraph-joins-lf-ai-data-as-new-incubation-project/)
- [Wikipedia — JanusGraph (history, Titan fork)](https://en.wikipedia.org/wiki/JanusGraph)
- [IBM — Database Deep Dives: JanusGraph](https://www.ibm.com/think/insights/database-deep-dives-janusgraph)
