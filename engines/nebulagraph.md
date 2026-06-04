---
name: NebulaGraph
slug: nebulagraph
rank: 131
data_model: Graph (distributed property graph)
license: Apache 2.0 (permissive); commercial NebulaGraph Enterprise from VEsoft
summary: Shard-nothing distributed property graph built on RocksDB + Multi-Raft; scales to trillions of edges but offers no general ACID transactions.
last_researched: 2026-06-04
confidence: high
---

# NebulaGraph

> A C++ distributed property-graph database that hash-shards a RocksDB key-value store under Multi-Raft to reach hundreds-of-billions of vertices, trading away general multi-statement transactions for horizontal scale.

## Identity
- **Taxonomy / data model:** Native [graph-data-model](../concepts/graph-data-model.md) — directed property graph (vertices/tags, directed edges, both with typed properties). nGQL is openCypher-compatible. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Key-value under the hood. Each vertex and each edge becomes KV pairs in [lsm-vs-btree](../concepts/lsm-vs-btree.md)-style RocksDB (LSM-tree), the default and most-used store engine ([HBase historically supported](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). An edge is stored as **two KV rows** — an out-edge under the source partition and an in-edge under the destination partition — to make both-direction traversal a local prefix scan ([storage design](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). NebulaGraph ships its own per-partition WAL rather than RocksDB's ([storage engine intro](https://www.nebula-graph.io/posts/nebula-graph-storage-engine-overview)).
- **Workload:** OLTP-ish graph traversal / point lookups with millisecond latency at scale; multi-hop pattern matching. Not an analytics engine — heavy whole-graph algorithms run via the separate NebulaGraph Analytics / Spark connector, not in-engine. Not HTAP.

## Distribution & consistency
- **Architecture:** Three separable services — `graphd` (stateless query/compute), `storaged` (stateful KV + Raft), `metad` (cluster metadata). Compute and storage are decoupled ([architecture overview](https://www.nebula-graph.io/posts/nebula-graph-architecture-overview)).
- **CAP under partition:** **CP** per partition. Each data partition is a [consensus-raft-paxos](../concepts/consensus-raft-paxos.md) Raft group; a partition with no leader quorum refuses writes rather than diverging. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition → consistency (PC). Else, leader-routed strongly-consistent reads/writes favor consistency over latency (EC) within a Raft group; ⚠️ unverified — no published PACELC classification for NebulaGraph.
- **Default isolation & what's achievable:** This is the key divergence. NebulaGraph has **no general multi-statement ACID transactions** ([dbdb.io](https://dbdb.io/db/nebula-graph)). Single-KV writes are atomic via Raft. For edges, the optional **TOSS** ("Transaction On Storage Side", added in v2.6, **disabled by default** behind `enable_experimental_feature` for performance/stability reasons) gives only **eventual consistency** of an edge's two KV rows (out-edge + in-edge succeed or fail together over time), not a serializable transaction ([TOSS post](https://www.nebula-graph.io/posts/nebula-graph-v2.6-toss)). dbdb lists MVCC ([dbdb.io](https://dbdb.io/db/nebula-graph)), but practically there is no isolation level a developer can rely on across statements — treat cross-vertex/edge writes as non-transactional. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Single-leader-per-partition Raft; followers replicate the WAL synchronously to a quorum, then apply to RocksDB asynchronously ([write path](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). Failover is automatic Raft leader election; replica factor is per-space (use odd numbers, e.g. 3). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No per-query consistency levels (not Dynamo/Cassandra-style). Reads go through the partition leader.
- **Clock dependency:** None for correctness — ordering comes from Raft, not synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Tags (vertex types) and edge types declare typed properties; you must `CREATE TAG`/`CREATE EDGE` before inserting. A vertex may carry multiple tags. Schema-flexible in that tags can be added, but not schemaless.
- **Migration/evolution:** `ALTER TAG`/`ALTER EDGE` to add/drop/change properties online. **Partition count is fixed at space-creation time** and cannot be changed afterward — resizing the shard count means creating a new space and re-importing, the biggest schema/topology gotcha ([recommended partition_num discussion](https://github.com/vesoft-inc/nebula/discussions/4281)).
- **Type system:** numeric, string/fixed-string, bool, date/time/datetime/timestamp, geography (geospatial). No native JSON document type; no native vector type. See [sharding-partitioning](../concepts/sharding-partitioning.md).

## Query interface
- **Language:** **nGQL**, a declarative, openCypher-compatible language ([what is NebulaGraph](https://docs.nebula-graph.io/3.8.0/1.introduction/1.what-is-nebula-graph/)); newer versions add ISO-GQL-aligned syntax. Pipe (`|`) composition is idiomatic. Not SQL.
- **Transactions:** None in the general sense — see Distribution. No `BEGIN/COMMIT` multi-statement transactions; only per-KV atomicity and optional eventual-consistency TOSS for edges.
- **Native vs app-side:** Multi-hop traversal, pattern `MATCH`, `GO`, `FETCH`, subgraph and path queries are native. Aggregations/joins are expressed via nGQL pipes. **Indexes:** native composite indexes over multiple properties of one tag/edge type, but **not across multiple tags** and only left-prefix-matchable (RocksDB prefix scan) ([index explained](https://www.nebula-graph.io/posts/nebula-graph-index-explained)). Indexes must exist before they can serve a lookup, and building an index after data load requires `REBUILD INDEX`.
- **Stored procedures / UDFs:** Limited; ⚠️ unverified — no first-class stored-procedure language comparable to PL/pgSQL. Server-side UDFs exist in some builds but are not a primary extensibility path.

## Scaling & topology
- **Horizontal** by design (shard-nothing). Data is hash-partitioned across `storaged` nodes into a fixed number of partitions per space; a built-in **Balancer** redistributes partitions when nodes are added/removed ([architecture overview](https://www.nebula-graph.io/posts/nebula-graph-architecture-overview)).
- **Sharding:** static hash on vertex ID; **resharding is painful** — partition count is immutable per space, so adding capacity rebalances existing partitions but cannot increase their number. New followers must "catch up" the full Raft log/snapshot, temporarily reducing HA ([storage service](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas:** Raft followers exist for HA, not for read scaling — reads are served by the leader, so follower reads are not the scaling lever. Scale reads by adding stateless `graphd` instances.
- **Storage/compute separation:** Yes — stateless `graphd` scales independently of stateful `storaged`. This is decoupled services, not the cloud object-store [storage-compute-separation](../concepts/storage-compute-separation.md) (Snowflake/Neon) pattern; storage is local-disk RocksDB.

## Performance & durability
- **Write path:** Per-partition [wal-and-durability](../concepts/wal-and-durability.md) WAL written by the leader, replicated to a follower quorum, then applied to RocksDB asynchronously ([write path](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). Data-loss window: a write is durable once a Raft quorum has the WAL entry; loss of a quorum before/at commit can lose the most recent un-quorumed writes. ⚠️ unverified — exact fsync policy of the custom WAL.
- **Throughput/latency:** Marketed millisecond multi-hop traversal at hundreds-of-billions-of-vertices scale; real numbers are workload-dependent. p99 is dominated by RocksDB LSM behavior and cross-partition edge fan-out.
- **Compaction / GC:** RocksDB LSM compaction governs space amplification and p99 latency spikes; operators routinely trigger manual `COMPACT` after bulk loads. Many small partitions inflate WAL/Raft overhead and slow recovery ([storage service](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)). See [lsm-vs-btree](../concepts/lsm-vs-btree.md).

## Operations & maturity
- **Backup/restore:** `nebula-br` (Backup & Restore) tool; cluster **snapshots** for point-in-time consistent copies. PITR is snapshot-based rather than continuous-log replay; ⚠️ unverified — granular continuous PITR support.
- **Observability:** `EXPLAIN`/`PROFILE` query plans; metrics exporters and a Dashboard product; slow-query logging available.
- **Upgrade story:** Version upgrades have historically required care (data-format migrations between major versions, e.g. 2.x→3.x); rolling upgrades possible per Raft group but cross-major upgrades can be disruptive. Day-2 burden: managing partition count chosen up front, RocksDB tuning, and Balancer operations.
- **Maturity:** Open-sourced 2019 by VEsoft; active community, production deployments at large Chinese tech firms (Meituan, Tencent, vivo, etc.). VEsoft **self-tests the storage layer with the [Jepsen](https://jepsen.io) framework** (its own `nebula-jepsen` harness checking single-register linearizability of the Raft KV store under chaos injection) ([NebulaGraph's Jepsen practice](https://dev.to/nebulagraph/practice-jepsen-test-framework-in-nebula-graph-eef)), but **no independent Jepsen report by jepsen.io / Kyle Kingsbury exists** — so its consistency claims are not validated by a third party, notable given the no-general-ACID design.

## Ecosystem & people
- **Canonical use cases:** fraud/risk graphs, real-time recommendation, knowledge graphs, social-network and lineage/security graphs at large scale where horizontal sharding is required.
- **Anti-patterns:** workloads needing **cross-entity ACID transactions** (financial ledgers as the system of record), small graphs that fit one node (use [neo4j](neo4j.md) or an embedded engine), heavy global graph analytics in-engine, ad-hoc full-text-heavy search (delegated to Elasticsearch with notable limits — no AND/OR/NOT logic, no result sorting, one property per FT index, no online ES index rebuild) ([full-text restrictions](https://docs.nebula-graph.io/3.5.0-sc/4.deployment-and-installation/6.deploy-text-based-index/1.text-based-index-restrictions/)).
- **Drivers/connectors:** official clients for Java, Python, Go, C++; Spark/Flink connectors, Nebula Exchange (bulk import), Nebula Importer, Studio (web UI), Explorer, Algorithm (Spark-based). CDC into NebulaGraph is connector-/batch-driven rather than a built-in log stream.
- **Community/support:** Mid-tier global popularity (db-engines rank ~131), strong in China; English docs are reasonably thorough but lag Chinese docs. Commercial support and managed cloud from VEsoft.

## Licensing & cost
- **OSS license:** **Apache 2.0** (permissive) for NebulaGraph core ([README — vesoft-inc/nebula](https://github.com/vesoft-inc/nebula)). A **Commons Clause 1.0** rider was added early on (to block cloud providers from reselling the project), but the current core repo's LICENSE is plain Apache 2.0; the Commons Clause is no longer present on master ([license discussion #3247](https://github.com/vesoft-inc/nebula/issues/3247)). See [license-taxonomy](../concepts/license-taxonomy.md). ⚠️ unverified — whether any peripheral tools carry different licenses; the core engine is Apache 2.0.
- **Self-managed vs managed:** Self-host the open-source core freely; VEsoft offers NebulaGraph Enterprise (added management/security/perf features) and a managed cloud offering. Lock-in risk is mainly nGQL/openCypher dialect and the proprietary enterprise features, not the storage format.
- **Cost model:** Open-source = infrastructure only (per-node). Enterprise/cloud is commercial (node/cluster-based pricing); ⚠️ unverified — current list pricing.

## Hardware / deployment
- **Resource profile:** Disk-bound on RocksDB with significant memory for block cache and bloom filters; working set need not fully fit in RAM, but hot data and indexes benefit from large cache. CPU matters for graphd query processing.
- **Storage assumptions:** Local SSD/NVMe strongly preferred for the LSM store; not designed around network-attached block latency.
- **Footprint:** Clustered, multi-process distributed system (graphd + storaged + metad). Not embedded, not serverless. Smallest sensible HA deployment is several nodes (replica factor 3).
- **Deployment:** On-prem or self-managed cloud; official Helm charts and a Kubernetes Operator make StatefulSet deployment workable, plus VEsoft's managed cloud.

## Bottom line
Reach for NebulaGraph when your property graph is genuinely too big for a single node and you need horizontal sharding with Raft-backed HA and millisecond traversals — fraud, recommendation, and large knowledge graphs are the sweet spot. Do **not** use it as a transactional system of record: there are no general multi-statement ACID transactions, and edge consistency is at best eventual via TOSS. The single biggest gotcha is that **partition count is fixed at space creation** — undersize it and you are re-importing the whole space to grow.

## Sources
- [What is NebulaGraph — official docs](https://docs.nebula-graph.io/3.8.0/1.introduction/1.what-is-nebula-graph/)
- [Storage Service — official docs](https://docs.nebula-graph.io/3.2.0/1.introduction/3.nebula-graph-architecture/4.storage-service/)
- [NebulaGraph Architecture overview](https://www.nebula-graph.io/posts/nebula-graph-architecture-overview)
- [An Introduction to NebulaGraph's Storage Engine](https://www.nebula-graph.io/posts/nebula-graph-storage-engine-overview)
- [Introducing TOSS: eventual consistency of edges](https://www.nebula-graph.io/posts/nebula-graph-v2.6-toss)
- [Everything about NebulaGraph Index](https://www.nebula-graph.io/posts/nebula-graph-index-explained)
- [Full-text index restrictions](https://docs.nebula-graph.io/3.5.0-sc/4.deployment-and-installation/6.deploy-text-based-index/1.text-based-index-restrictions/)
- [Database of Databases — Nebula Graph](https://dbdb.io/db/nebula-graph)
- [Practice Jepsen Test Framework in NebulaGraph (self-administered)](https://dev.to/nebulagraph/practice-jepsen-test-framework-in-nebula-graph-eef)
- [License discussion — Commons Clause / Apache 2.0 (issue #3247)](https://github.com/vesoft-inc/nebula/issues/3247)
- [GitHub — vesoft-inc/nebula](https://github.com/vesoft-inc/nebula)
- [recommended partition_num & replica_factor discussion](https://github.com/vesoft-inc/nebula/discussions/4281)
