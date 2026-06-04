---
name: TigerGraph
slug: tigergraph
rank: 128
data_model: Graph
license: Proprietary (not OSS); free Community Edition (single-server, up to 300 GB) and older free Enterprise Edition (up to 50 GB)
summary: Native parallel (MPP) property-graph database with a C++ engine and the GSQL accumulator language, built for deep multi-hop analytics at scale.
last_researched: 2026-06-04
confidence: medium
---

# TigerGraph

> A native massively-parallel property-graph database whose accumulator-based GSQL language and C++ engine target deep (5+ hop) traversals and graph analytics at scale, where Neo4j-style pointer-chasing engines bog down.

## When to use

**Use TigerGraph if:**
- ✅ You need deep multi-hop traversals (3+ hops) or graph algorithms over large, distributed graphs in real time
- ✅ Your use case is fraud/AML, entity resolution, 360-degree customer views, recommendation, or GraphRAG/knowledge-graph + vector retrieval
- ✅ You want a native parallel (MPP) property-graph engine that outpaces pointer-chasing engines on deep queries, and will invest in the GSQL accumulator model
- ✅ You need hybrid graph + ANN vector search (TigerVector, v4.2+) in one engine

**Avoid TigerGraph if:**
- ❌ You only need simple 1-hop lookups, general OLTP, or document/blob storage (a relational or KV store is cheaper)
- ❌ Your graph fits one node — Neo4j or relational recursive CTEs may be simpler and cheaper
- ❌ You need it open source — it is proprietary/closed-source; free tiers are size-capped (Community Edition up to 300 GB single-server, older Enterprise free tier 50 GB)
- ❌ You require true serializable isolation or zero-downtime resharding — isolation is read-committed (no Jepsen report), and cluster repartitioning needs downtime

## Identity
- **Taxonomy / data model:** native property graph (labeled vertices/edges with typed attributes); not a triple store. See [graph-data-model](../concepts/graph-data-model.md). As of v4.2 (Dec 2024) it also stores vectors as a vertex attribute type (TigerVector) for hybrid graph + ANN search ([TigerVector paper](https://arxiv.org/html/2501.11216v1)), making it loosely [multi-model](../concepts/multi-model.md).
- **Storage model:** custom C++ engine. The **Graph Storage Engine (GSE)** stores topology in a compressed, encoded format across cache/memory/disk tiers; the **Graph Processing Engine (GPE)** executes traversals in parallel ([MPP paper](https://arxiv.org/pdf/1901.08248)). It is *not* an [lsm-vs-btree](../concepts/lsm-vs-btree.md) design — vertices/edges are stored as compressed adjacency structures keyed by internal integer IDs, originally layered over a KV store abstraction ([building on a KV store](https://medium.com/tigergraph/building-a-graph-database-on-a-key-value-store-97c22b2b33d8)). Working set is effectively memory-resident for performance.
- **Workload:** analytical graph (OLAP-style deep traversals, graph algorithms) plus real-time transactional point updates/lookups — vendor positions it for "real-time deep-link analytics." Not general OLTP/OLAP; see [oltp-olap-htap](../concepts/oltp-olap-htap.md). Closer to graph-OLAP than HTAP.

## Distribution & consistency
- **CAP under partition:** ⚠️ unverified — TigerGraph does not publish an explicit CAP classification and there is no Jepsen report. Behavior implies **CP-leaning**: all replicas are kept in sync on every write and a query may fail (and is retried) during a node failure for "typically up to 30 seconds" ([HA cluster docs](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-cluster)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — not stated by vendor. The synchronous-all-replicas write model implies **PC/EC** (consistency favored in both partition and normal operation), at the cost of write latency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** **conflicting sources.** Current official docs state **read-committed isolation** implemented via [mvcc](../concepts/mvcc.md), with "distributed Strong Consistency" where all replicas apply updates in the same order ([Transaction & ACID docs](https://tigergraph.com/docs/tigergraph-server/current/intro/transaction-and-acid)). Older docs and secondary sources claimed **serializable** isolation with "sequential consistency" ([dev forum](https://dev.tigergraph.com/forum/t/what-isolation-levels-does-tigergraph-support/3490)). ⚠️ Treat any "serializable" / "fully ACID" claim with caution — the current authoritative statement is read-committed. See [isolation-levels](../concepts/isolation-levels.md). Each GSQL query / REST++ call is one transaction.
- **Replication:** multi-copy synchronous — **all writes go to all replicas; reads served from any one replica** ([HA cluster docs](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-cluster)). Cluster coordination uses Apache Zookeeper and inter-engine messaging uses Apache Kafka. There is no single global leader in the Raft/Paxos sense documented; ⚠️ unverified — exact failover/commit protocol and split-brain handling are not clearly documented. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** No documented per-query consistency levels (unlike Cassandra/Dynamo).
- **Clock dependency:** none documented; correctness does not appear to rest on synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** **schema-on-write, rigid.** Vertex and edge types with declared, typed attributes must be defined before loading ([schema docs](https://jp-tgdocs.netlify.app/gsql-ref/current/ddl-and-loading/defining-a-graph-schema)).
- **Migration/evolution:** online-ish via `SCHEMA_CHANGE JOB` (ADD/ALTER/DROP vertex/edge types and attributes), but ⚠️ schema changes are **blocked while a node is down** and apply cluster-wide ([HA overview](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-overview)). Not as seamless as schema-on-read document stores.
- **Type system:** standard scalars, lists/sets/maps, datetime, plus **vector/embedding attributes** with auto-built HNSW ANN indexes (v4.2+) ([vector ops](https://docs.tigergraph.com/gsql-ref/4.2/vector/)). See [vector-search-ann](../concepts/vector-search-ann.md). Native geospatial support is limited.

## Query interface
- **Language:** **GSQL** — a SQL-like, Turing-complete graph language whose signature is the `SELECT-FROM-WHERE` block plus the **`ACCUM`/`POST-ACCUM`** clauses and *accumulator* variables that aggregate results from massively parallel vertex/edge compute ([MPP paper](https://arxiv.org/pdf/1901.08248), [GSQL ref](https://docs.tigergraph.com/gsql-ref/4.2/intro/)). Supports installed (compiled) queries and interpreted queries. A subset of **openCypher / GQL** is also supported in recent versions. REST++ API and GraphStudio GUI available.
- **Transactions:** multi-statement ACID per query/REST call; read-committed (see above). No interactive cross-request transaction sessions in the SQL sense.
- **Native vs app-side:** joins/traversals, aggregations, and graph algorithms are native and parallel; a packaged Graph Data Science algorithm library ships separately. Secondary indexes exist but the model is traversal-first.
- **Stored procedures / UDFs:** GSQL queries act as installed procedures; **C++ UDFs** can be registered for custom logic.

## Scaling & topology
- **Vertical vs horizontal:** scales **horizontally** by partitioning the graph across machines (MPP). Partition factor = machines / replication factor; no documented hard upper limit ([HA cluster docs](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-cluster)). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding:** automatic graph partitioning by internal vertex ID; resharding (`Cluster Repartition`) **requires several minutes of cluster downtime** ([repartition docs](https://docs.tigergraph.com/tigergraph-server/current/cluster-and-ha-management/repartition-a-cluster)) — a real operational gotcha.
- **Read replicas:** any replica can serve reads; replicas are kept in sync so cross-replica reads are consistent. Distributed queries may read from a mix of replicas.
- **Storage/compute separation:** the on-prem engine couples storage and compute; **TigerGraph Savanna** (cloud) markets independent scaling of compute and storage ([Savanna](https://www.tigergraph.com/savanna/)). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** committed transactions persisted to disk via **write-ahead logging (WAL)**; transactions over `TransactionStoreMemLimit` (default 4 MB) spill to file, and `TransactionSizeLimit` aborts runaway transactions ([Transaction & ACID docs](https://tigergraph.com/docs/tigergraph-server/current/intro/transaction-and-acid)). See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact fsync policy / crash data-loss window is not documented.
- **Throughput/latency:** strength is **deep multi-hop traversal** throughput via parallel GPE execution; vendor benchmarks claim large advantages over pointer-chasing engines on 3+ hop queries (treat vendor numbers with skepticism). ⚠️ unverified — independent p99/tail latency data is scarce.
- **Compaction / GC:** [mvcc](../concepts/mvcc.md) keeps multiple snapshots; old versions are garbage-collected. ⚠️ unverified — version-GC impact on p99 not documented.

## Operations & maturity
- **Backup/restore:** full and incremental backup/restore and snapshotting supported; PITR is limited compared to mature RDBMSs.
- **Observability:** GraphStudio visual IDE, query plan/profiling for installed queries, Admin Portal metrics, Prometheus/Grafana integration.
- **Upgrade story:** cluster upgrades generally involve coordination/downtime; **schema changes, query installs, and connector loading are unavailable while any node is down** ([HA overview](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-overview)) — partial, not seamless, HA.
- **Maturity:** founded 2012 (GA 2017); used in fraud detection, AML, recommendation, supply chain, and increasingly GraphRAG. Smaller install base than Neo4j. **No Jepsen report exists** — the consistency story rests on vendor claims, hence medium confidence on this page.

## Ecosystem & people
- **Canonical use cases:** real-time fraud/AML, entity resolution, 360-degree customer views, recommendation, network/IT analytics, and GraphRAG/knowledge-graph + vector retrieval.
- **Anti-patterns:** general-purpose OLTP, document/blob storage, simple 1-hop lookups (a relational or KV store is cheaper), small graphs that fit one node (Neo4j or even SQLite-with-recursive-CTEs may be simpler), and teams unwilling to learn the accumulator programming model.
- **Drivers/connectors:** REST++, pyTigerGraph, JDBC, Kafka/Spark connectors, Kafka-based CDC loading, and integrations with LangChain/LlamaIndex for GraphRAG. dbt/BI integration is thinner than the relational ecosystem.
- **Community/support:** active developer forum and free tier; commercial support via TigerGraph. Docs are reasonable but versioned/fragmented; **GSQL has a real learning curve** (accumulators are unlike SQL).

## Licensing & cost
- **License:** **proprietary**, not OSS — there is no Apache/MIT core and the source is not published (⚠️ "source-available" is inaccurate; the engine is closed-source binary distribution). Two free tiers exist: the newer **Community Edition** — free even for production, **single-server only (no clustering)**, capped at **up to 300 GB combined graph + vector storage and up to 16 CPUs** ([Community Edition](https://www.tigergraph.com/community-edition/)) — and the older **free Enterprise Edition** capped at **50 GB graph size** ([editions](https://www.tigergraph.com/comparison-of-tigergraph-editions/)). See [license-taxonomy](../concepts/license-taxonomy.md). Not subject to the SSPL/BSL relicensing wave — it was never open source.
- **Self-managed vs managed:** self-managed **TigerGraph DB** (annual license priced by data capacity) or **Savanna** managed cloud. Lock-in via GSQL/accumulators and proprietary engine is significant.
- **Cost model:** on-prem = capacity-based annual license; Savanna = pay-as-you-go for compute (per workspace size × hours) + storage + add-ons ([Savanna pricing](https://docs.tigergraph.com/savanna/main/overview/pricing)). Memory-heavy workloads make node sizing the dominant cost at scale.

## Hardware / deployment
- **Resource profile:** **memory-bound** — high performance assumes the working set (often the whole graph) is RAM-resident; CPU-parallel during traversals. Generous RAM is the key sizing lever.
- **Storage assumptions:** local NVMe/SSD preferred for the on-disk tier and WAL; not designed around high-latency network storage.
- **Footprint:** single-node or distributed cluster (MPP); not embedded. Savanna provides serverless-ish cloud workspaces.
- **Deployment:** on-prem, self-managed cloud (AMIs / containers), Kubernetes operator available, and the Savanna SaaS. StatefulSet realities apply (persistent volumes, ordered scaling, repartition downtime).

## Bottom line
Reach for TigerGraph when you need **deep multi-hop traversals or graph algorithms over large, distributed graphs in real time** — fraud rings, entity resolution, GraphRAG — and the accumulator/MPP model justifies the learning curve and proprietary lock-in. Do not pick it for simple 1-hop lookups, general OLTP, or small graphs where a relational store or Neo4j is simpler and cheaper. **Biggest gotchas:** it is *not* open source (free tiers are size-capped: Community Edition up to 300 GB single-server, older Enterprise free tier 50 GB), the isolation guarantee is **read-committed** (vendor "serializable/strong consistency" framing should be read carefully and there is **no Jepsen report**), and **cluster repartitioning needs downtime**.

## Sources
- [TigerGraph: A Native MPP Graph Database (arXiv 1901.08248)](https://arxiv.org/pdf/1901.08248)
- [Transaction Processing and ACID Support (official docs)](https://tigergraph.com/docs/tigergraph-server/current/intro/transaction-and-acid)
- [High Availability Cluster Configuration](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-cluster)
- [High Availability (HA) Overview](https://docs.tigergraph.com/tigergraph-server/4.2/cluster-and-ha-management/ha-overview)
- [Cluster Repartition](https://docs.tigergraph.com/tigergraph-server/current/cluster-and-ha-management/repartition-a-cluster)
- [GSQL Language Reference](https://docs.tigergraph.com/gsql-ref/4.2/intro/)
- [Vector Database Operations (GSQL)](https://docs.tigergraph.com/gsql-ref/4.2/vector/)
- [TigerVector: Supporting Vector Search in Graph Databases (arXiv 2501.11216)](https://arxiv.org/html/2501.11216v1)
- [Building a Graph Database on a Key-Value Store](https://medium.com/tigergraph/building-a-graph-database-on-a-key-value-store-97c22b2b33d8)
- [Comparison of TigerGraph Editions](https://www.tigergraph.com/comparison-of-tigergraph-editions/)
- [TigerGraph Savanna Pricing](https://docs.tigergraph.com/savanna/main/overview/pricing)
- [Isolation levels — dev forum](https://dev.tigergraph.com/forum/t/what-isolation-levels-does-tigergraph-support/3490)
