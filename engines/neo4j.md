---
name: Neo4j
slug: neo4j
rank: 20
data_model: Graph
license: GPLv3 (Community) + proprietary commercial (Enterprise) — open-core
summary: The market-leading native property-graph database; Cypher + index-free adjacency make deep traversals cheap, but it is a single-writer system that does not horizontally shard a connected graph.
last_researched: 2026-06-04
confidence: high
---

# Neo4j

> The default choice for connected-data and deep-traversal workloads: a native property-graph store with index-free adjacency and the Cypher language, but a single-leader, read-committed engine whose writes do not scale horizontally across one graph.

## When to use

**Use Neo4j if:**
- ✅ Your problem *is* the relationships — multi-hop traversals, pattern matching, fraud rings, knowledge graphs, GraphRAG/agent memory
- ✅ Index-free adjacency turns SQL self-join nightmares into cheap pointer chases at constant per-hop cost
- ✅ You want the most mature graph ecosystem — Cypher/GQL, GDS algorithms, native vector type, broad drivers and tooling
- ✅ Your active graph and indexes fit in RAM/page cache and read scaling via async replicas suffices

**Avoid Neo4j if:**
- ❌ You need horizontally write-scalable graph writes — it is single-leader and does **not** transparently shard a connected graph's topology (Infinigraph shards only properties)
- ❌ You need serializable isolation out of the box — default is read-committed; higher isolation requires manual write locks
- ❌ You run bulk analytical scans over the whole dataset (use a warehouse/OLAP engine) or store weakly-connected flat tabular/KV data ([postgresql](postgresql.md) is cheaper)
- ❌ You need clustering/HA/RBAC/PITR for free — those are Enterprise/Aura only; Community is GPLv3 single-instance

## Identity
- **Taxonomy / data model:** native labeled property graph — nodes, typed directed relationships, and key/value properties on both. See [graph-data-model](../concepts/graph-data-model.md). Not multi-model: it is graph-first (no document/relational facade).
- **Storage model:** native graph storage using **index-free adjacency** — each node holds direct pointers to its incident relationships, so a hop is a pointer chase rather than an index lookup, making traversal cost independent of total graph size ([Neo4j: native graph storage](https://neo4j.com/labs/agent-memory/explanation/graph-architecture/)). Historically fixed-size record files; Neo4j 5 (2023) added the **block format** that packs related data into contiguous on-disk blocks for better page-cache locality and scale ([Neo4j 5 announcement](https://neo4j.com/blog/news/announcing-neo4j-5-graph-database/)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md)-style; this is a bespoke graph layout. Property values and full-text/vector indexes are backed by Apache Lucene.
- **Workload:** OLTP graph queries (fraud rings, recommendations, network/IT topology, knowledge graphs, identity/access). Analytics run via the separate **Graph Data Science (GDS)** library (PageRank, community detection, embeddings). See [oltp-olap-htap](../concepts/oltp-olap-htap.md). The **Infinigraph** architecture (GA Sept 2025, Enterprise; AuraDB later) targets unified operational+analytical (HTAP-style) at 100TB+ via **property sharding**: per Neo4j's docs, the graph *topology* (nodes/relationships) stays in a single **graph shard**, while node/relationship **properties** are distributed across multiple **property shards** ([Neo4j: sharded property databases](https://neo4j.com/docs/operations-manual/current/scalability/sharded-property-databases/overview/), [Infinigraph GA blog](https://neo4j.com/blog/graph-database/infinigraph-is-generally-available/)). So the "HTAP at scale" mechanism is property distribution, *not* sharding of the connected topology; the write path remains single-leader. Performance/SLA claims at 100TB+ remain vendor-stated.

## Distribution & consistency
- **CAP under partition:** **CP** — Core servers form a [Raft](../concepts/consensus-raft-paxos.md) group; a write requires a majority quorum, so a minority partition cannot accept writes (it refuses/redirects to preserve consistency) ([Neo4j clustering intro](https://neo4j.com/docs/operations-manual/current/clustering/introduction/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition, **PC** (sacrifice availability of the minority side for consistency); else **EL** at the cluster edge — read replicas serve scalable but **asynchronously replicated, possibly stale** reads, trading latency/throughput for freshness. The default single-instance/primary path favors consistency.
- **Default isolation:** **read-committed** ([Neo4j transaction management](https://neo4j.com/docs/java-reference/4.4/transaction-management/index.html)). Writes are fully ACID and atomic per transaction; reads see only committed data but **non-repeatable reads and read skew are possible** within a traversal. Serializable is *not* a setting — you approximate higher isolation by **manually acquiring write locks** on nodes/relationships in Cypher ([same source]). So "fully ACID" here means durable atomic transactions at read-committed, **not serializable**. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** single-leader. Core servers replicate the transaction log via Raft (synchronous to a majority); **read replicas** stream changes asynchronously and never vote. Failover: Raft elects a new leader (default election timeout ~seconds). No multi-leader/active-active write within one database; cross-region active-active is not supported for a single graph. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Via **causal consistency + bookmarks**: a write returns a bookmark; passing it to a later session guarantees that session reads at least that write ("read-your-writes" / monotonic reads) even when routed to a replica ([Neo4j clustering intro](https://neo4j.com/docs/operations-manual/current/clustering/introduction/)). Without bookmarks, replica reads can be stale.
- **Clock dependency:** none for correctness — safety rests on Raft quorum, not synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).
- **Jepsen:** ⚠️ no published Jepsen analysis of Neo4j exists as of this writing ([Jepsen analyses](https://jepsen.io/analyses)); cluster safety claims are not externally formally verified.

## Schema
- **Schema-on-write vs read:** effectively **schema-optional / schema-on-read** — labels and properties are flexible; you can add optional **constraints** (uniqueness, node/relationship property existence, property type — Enterprise) and **indexes** to impose rigor incrementally.
- **Migration / DDL:** creating indexes/constraints is online (background-populated). There is no heavy `ALTER TABLE`; schema evolution is mostly additive via new labels/relationship types and data-rewriting Cypher.
- **Type system:** scalars, lists, temporal (date/time/duration), spatial **point** (geospatial), and a first-class native **vector** type for embeddings (drivers/Bolt/Cypher/storage), backed by Lucene **HNSW** vector indexes ([Neo4j native vector type](https://neo4j.com/blog/developer/introducing-neo4j-native-vector-data-type/)). No native nested-JSON document type (properties are flat scalars/lists). See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** **Cypher**, the originating declarative graph language (ASCII-art pattern matching), now standardized as the basis of ISO **GQL**; Neo4j tracks GQL alignment. Also a Bolt binary protocol and HTTP API.
- **Transactions:** full **multi-statement ACID** transactions within a single database; cross-database/Fabric (composite) transactions are read-oriented and not globally atomic across shards.
- **Native vs app-side:** traversals, variable-length paths, shortest-path, joins-as-traversals, and aggregations are native; secondary indexes (range, text, point, full-text, vector) are native. Graph algorithms (PageRank, Louvain, node embeddings, etc.) via the **GDS** library.
- **Stored procedures / UDFs:** user-defined procedures and functions in **Java** (the APOC standard-library is the canonical example); callable from Cypher.

## Scaling & topology
- **Vertical vs horizontal:** primarily **vertical (scale-up)** for writes — a single graph has one write leader and the **working set benefits from fitting in the page cache/RAM**. Read throughput scales horizontally via read replicas.
- **Sharding:** Neo4j does **not** auto-shard a single connected graph across machines for writes. **Fabric / composite databases** (v4+, simplified in v5) let you query multiple databases/shards as one logical graph, but you choose the shard boundaries manually and cross-shard traversals are expensive/limited ([Neo4j 5](https://neo4j.com/blog/news/announcing-neo4j-5-graph-database/)). **Infinigraph** (GA Sept 2025) targets 100TB+ single graphs, but per Neo4j's own docs it shards only **properties** across property shards while keeping the graph **topology in a single graph shard** — i.e., it does **not** transparently shard a connected graph's topology, and the write path is still single-leader ([Neo4j: sharded property databases](https://neo4j.com/docs/operations-manual/current/scalability/sharded-property-databases/overview/), [Infinigraph GA blog](https://neo4j.com/blog/graph-database/infinigraph-is-generally-available/)).
- **Autonomous Clustering (v5):** declarative placement — you state desired primary/secondary copy counts and the cluster places/rebalances databases automatically across servers ([Neo4j 5](https://neo4j.com/blog/news/announcing-neo4j-5-graph-database/)).
- **Read replicas:** asynchronous; reads are eventually consistent unless gated by a bookmark. Routing drivers send writes to the leader and balance reads.
- **Storage/compute separation:** classic deployment couples storage+compute. **Aura** (managed) and Aura serverless analytics decouple to varying degrees. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** transactions append to a **transaction log (WAL)**; durability depends on fsync/log-flush configuration and group commit. With synchronous Raft to a majority, a committed write survives minority node loss; the local crash data-loss window is the unflushed-log tail per node. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** excels at **deep multi-hop traversals** (constant per-hop cost via index-free adjacency) where relational JOINs would explode; sub-20ms point traversals are typical for cached graphs. Write throughput is bounded by the single leader and quorum round-trips. p99 is sensitive to **page-cache misses** (graph spilling to disk) and to GC pauses (JVM).
- **Compaction/GC:** runs on the **JVM**, so heap sizing and GC tuning materially affect tail latency on large heaps. Store files are not LSM-compacted; reclaiming space from large deletes may require store maintenance. Lucene index merges add background I/O.

## Operations & maturity
- **Backup/restore:** online backups, **point-in-time restore** from full+differential backups and transaction logs (Enterprise), plus a built-in **consistency checker** for store integrity ([Neo4j consistency checker](https://neo4j.com/docs/operations-manual/current/backup-restore/consistency-checker/)).
- **Observability:** `EXPLAIN`/`PROFILE` query plans, query logging, JMX/Prometheus metrics, Neo4j Browser and Bloom for visualization.
- **Upgrade:** rolling upgrades supported within a cluster (Enterprise); Neo4j 5 is an LTS line. Major-version migrations (e.g., 4.4 → 5) have breaking changes ([4.4→5 breaking changes](https://neo4j.com/docs/upgrade-migration-guide/current/version-5/migration/breaking-changes/)).
- **Maturity:** the most widely deployed graph database, mature drivers and tooling, large production track record. Known failure modes: write-throughput ceiling on a single leader, JVM GC tail latency, costly cross-Fabric traversals, and supernode/dense-node hotspots. ⚠️ no Jepsen report — clustering safety is vendor-tested, not independently verified.

## Ecosystem & people
- **Canonical use cases:** fraud detection, recommendation engines, identity & access / network topology, master-data and knowledge graphs, GraphRAG/agent memory backing LLMs. **Anti-patterns:** high-volume write-scaling beyond one node, bulk analytical scans over the whole dataset (use a warehouse/[OLAP](../concepts/oltp-olap-htap.md) engine), simple flat tabular/KV workloads (a relational DB or [postgresql](postgresql.md) is cheaper and simpler), and data with little connectivity (the graph model adds no value).
- **Drivers/connectors:** official drivers for Java, Python, JavaScript, .NET, Go; Bolt protocol; Spring Data Neo4j; **APOC** utility library; **GDS** for algorithms; Kafka/CDC connectors and a Spark connector; BI via JDBC.
- **Community:** very large developer community, GraphAcademy training, strong docs. Cypher has a moderate learning curve for those coming from SQL; thinking in traversals/patterns is the real ramp.

## Licensing & cost
- **OSS license & flavor:** **open-core**. Community Edition is **GPLv3** (copyleft, single-instance, no clustering/RBAC/online-backup/hot-backup) ([Neo4j repo](https://github.com/neo4j/neo4j)). **Enterprise Edition** is under a **proprietary commercial license** and is no longer published as source on GitHub ([Neo4j open-core FAQ](https://neo4j.com/open-core-and-neo4j/)). Historically Enterprise was AGPLv3, then AGPLv3 + Commons Clause (v3.4, May 2018), then closed-source commercial starting with v3.5 (late 2018) — a notable **2018-era relicensing tightening** away from open source ([Neo4j open-core FAQ](https://neo4j.com/open-core-and-neo4j/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** self-host either edition; **Neo4j Aura** is the managed cloud (AuraDB operational, Aura Graph Analytics serverless). Clustering, security/RBAC, multi-database, and PITR are Enterprise/Aura-only — a meaningful lock-in/feature gate vs Community.
- **Cost model:** Enterprise is typically licensed per-instance/per-core (negotiated); Aura is consumption/size-based. Costs rise with RAM (graph wants to be cached) and with the number of cluster cores; Community is free but operationally limited (no clustering/HA).

## Hardware / deployment
- **Resource profile:** **memory-bound** — best performance when the active graph (and its indexes) fit in the **page cache/RAM**; cache misses to disk dominate p99. JVM heap must also be sized for query state and GDS. CPU matters for traversal-heavy and GDS workloads.
- **Storage assumptions:** **NVMe/local SSD** strongly preferred; random-access graph traversal is latency-sensitive and tolerates network-attached storage poorly.
- **Footprint:** single-node (Community) or clustered Core+Replica (Enterprise); not embedded in the SQLite sense (there is an embedded Java API, but it is not the common deployment). Aura provides serverless/SaaS.
- **Deployment:** Docker images and Helm charts; k8s deployment as StatefulSets is supported but stateful-graph operational realities (persistent volumes, careful rolling restarts of the Raft group) apply.

## Bottom line
Reach for Neo4j when your problem **is** the relationships — multi-hop traversals, pattern matching, fraud rings, knowledge graphs, GraphRAG — where index-free adjacency turns queries that would be self-join nightmares in SQL into cheap pointer chases. Do **not** reach for it as a horizontally write-scalable system, a bulk analytics warehouse, or a general-purpose store for weakly-connected tabular data. The single biggest gotcha: **writes are single-leader and the graph does not transparently shard** — plan capacity around one write node and a RAM-resident working set, and remember the default isolation is only **read-committed** (serializable requires manual locking).

## Sources
- [Neo4j clustering introduction — Operations Manual](https://neo4j.com/docs/operations-manual/current/clustering/introduction/)
- [Neo4j transaction management & isolation — Java Reference](https://neo4j.com/docs/java-reference/4.4/transaction-management/index.html)
- [Neo4j 5 announcement (Autonomous Clustering, Fabric, block format)](https://neo4j.com/blog/news/announcing-neo4j-5-graph-database/)
- [Neo4j native vector data type & HNSW indexes](https://neo4j.com/blog/developer/introducing-neo4j-native-vector-data-type/)
- [Neo4j open-core licensing FAQ](https://neo4j.com/open-core-and-neo4j/)
- [Neo4j GitHub repo (GPLv3 Community / commercial Enterprise)](https://github.com/neo4j/neo4j)
- [Neo4j consistency checker — Operations Manual](https://neo4j.com/docs/operations-manual/current/backup-restore/consistency-checker/)
- [Neo4j 4.4 → 5 breaking changes](https://neo4j.com/docs/upgrade-migration-guide/current/version-5/migration/breaking-changes/)
- [Neo4j — sharded property databases (Infinigraph) Operations Manual](https://neo4j.com/docs/operations-manual/current/scalability/sharded-property-databases/overview/)
- [Neo4j — Infinigraph is generally available (GA blog, Sept 2025)](https://neo4j.com/blog/graph-database/infinigraph-is-generally-available/)
- [The Register — Neo4j property sharding (Infinigraph), 2025](https://www.theregister.com/2025/09/11/neo4j_property_sharding_to_address_scalability_challenge/)
- [Jepsen analyses index (no Neo4j report)](https://jepsen.io/analyses)
