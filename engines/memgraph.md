---
name: Memgraph
slug: memgraph
rank: 137
data_model: Graph
license: Business Source License 1.1 (source-available; converts to Apache 2.0)
summary: In-memory C++ property-graph DB with Neo4j-compatible Cypher; fast real-time analytics and GraphRAG, but durability and HA carry caveats.
last_researched: 2026-06-04
confidence: high
---

# Memgraph

> An in-memory, C++ property-graph database speaking Neo4j-compatible Cypher, positioned for real-time graph analytics, streaming, and GraphRAG — fast because it holds the graph in RAM, with durability and high availability that need careful configuration.

## When to use

**Use Memgraph if:**
- ✅ You need low-latency, real-time graph queries or analytics in Cypher on a dataset that fits in RAM
- ✅ You want a faster, lighter Neo4j alternative for streaming graphs (Kafka/Pulsar) and GraphRAG / AI memory
- ✅ You can use existing Cypher/Bolt clients and want in-engine graph algorithms via MAGE (Python/C++/Rust)
- ✅ Native vector search alongside the graph (for GraphRAG) is useful to you

**Avoid Memgraph if:**
- ❌ Your graph vastly exceeds available RAM — unless you accept the much slower on-disk RocksDB mode
- ❌ You need horizontal write sharding or serializable isolation — it is single-writer with no serializable level
- ❌ You require an independently audited HA/no-data-loss story — failover is Enterprise-only and no Jepsen report exists
- ❌ You assume "ACID" and "open-source" at face value — ACID applies only to `IN_MEMORY_TRANSACTIONAL` (analytical mode has none) and the license is BSL, not OSI-open

## Identity
- **Taxonomy / data model:** Labeled property graph (nodes, relationships, key-value properties on both), querying via openCypher. See [graph-data-model](../concepts/graph-data-model.md). Multi-model only in the loose sense — it is graph-first, not multi-model.
- **Storage model:** Primarily **in-memory** — the working graph lives in RAM; on-disk artifacts are snapshots + WAL for recovery. Index core is a highly-concurrent **skip list**, not a [B-tree/LSM](../concepts/lsm-vs-btree.md) ([dbdb.io](https://dbdb.io/db/memgraph)). An optional `ON_DISK_TRANSACTIONAL` mode backs storage with **RocksDB** (LSM), trading speed for capacity beyond RAM ([storage modes](https://memgraph.com/blog/memgraph-storage-modes-explained)).
- **Workload:** OLTP-style graph transactions and real-time graph **analytics** ([oltp-olap-htap](../concepts/oltp-olap-htap.md)). Not HTAP in the columnar sense; the split is by **storage mode** not by physical replica/columnar store: `IN_MEMORY_TRANSACTIONAL` (ACID, MVCC) vs `IN_MEMORY_ANALYTICAL` (no isolation, no WAL, faster bulk/analytics) ([storage modes](https://memgraph.com/blog/memgraph-storage-modes-explained)).

## Distribution & consistency
- **CAP under partition:** Single MAIN node owns all writes; it is effectively **CP** for writes (a single writable primary). See [cap-pacelc](../concepts/cap-pacelc.md). ASYNC replicas drift, so reads off replicas are eventually consistent.
- **PACELC:** Under partition, behavior depends on replication mode — `SYNC`/`STRICT_SYNC` favor consistency (writes may stall), `ASYNC` favors availability. Else (no partition), reads from replicas trade consistency for latency.
- **Default isolation:** **Snapshot isolation** via MVCC (delta objects) in the default `IN_MEMORY_TRANSACTIONAL` mode; also offers `READ_COMMITTED` and `READ_UNCOMMITTED` ([transactions](https://memgraph.com/docs/fundamentals/transactions)). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). **Important divergence:** the "ACID" claim holds only in `IN_MEMORY_TRANSACTIONAL`; `IN_MEMORY_ANALYTICAL` has **no isolation and no ACID guarantees** (concurrent writers, no WAL) ([transactions](https://memgraph.com/docs/fundamentals/transactions)). `ON_DISK_TRANSACTIONAL` uses snapshot isolation exclusively. No serializable level offered.
- **Replication:** **Single-leader** (one MAIN, multiple REPLICAs). Modes: `ASYNC` (read scaling, lag), `SYNC` (waits for replica ack), `STRICT_SYNC` (two-phase commit across all replicas for no-data-loss; vendor describes this mode as CP) ([replication](https://memgraph.com/docs/clustering/replication), [how replication works](https://memgraph.com/docs/clustering/replication/how-replication-works)). See [replication-models](../concepts/replication-models.md).
- **Failover / split-brain:** **Automatic failover is Enterprise-only**, driven by RAFT-based coordinators; Community edition requires **manual failover** with custom scripts ([HA license differences](https://memgraph.com/blog/building-high-availability-in-memgraph-license-differences)). Replicas lagging beyond a threshold are ineligible for promotion to limit data loss.
- **Tunable consistency:** Per-replica mode (ASYNC/SYNC/STRICT_SYNC); isolation level settable at GLOBAL/SESSION/NEXT scope.
- **Clock dependency:** No documented dependence on synchronized clocks for correctness (single-writer model). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schema-on-write is optional — property graph is largely **schema-flexible**; labels and properties are dynamic. Optional schema/constraints (existence, uniqueness, type) can be enforced.
- **Migration/evolution:** Adding labels/properties is online and cheap (no fixed table layout). Index/constraint creation is a DDL-like operation.
- **Type system:** Standard Cypher types — strings, numbers, booleans, lists, maps, temporal types; geospatial points. Native **vector search** is supported (since v2.22; vector indexes on nodes and edges, USearch backend), and v3.8 added a single-store vector index that keeps a lightweight reference in native storage — aimed at GraphRAG use cases ([vector search](https://memgraph.com/docs/querying/vector-search)).

## Query interface
- **Language:** **openCypher**, marketed as Neo4j-Cypher-compatible (so existing Cypher and Bolt clients largely work). DSL, not SQL.
- **Transactions:** Full multi-statement ACID in `IN_MEMORY_TRANSACTIONAL`; none in `IN_MEMORY_ANALYTICAL`.
- **Native operations:** Native graph traversal, joins via relationships, pattern matching, aggregations. Indexes are label/label-property skip lists.
- **Stored procedures / UDFs:** Yes — via **MAGE** (Memgraph Advanced Graph Extensions), custom procedures in **Python, C/C++, and Rust**, runnable inside the engine ([MAGE](https://github.com/memgraph/mage)). Includes graph algorithms (PageRank, community detection, pathfinding, etc.).

## Scaling & topology
- **Vertical vs horizontal:** Predominantly **scale-up** — the whole graph must fit in RAM on the MAIN node (or use on-disk/RocksDB mode for larger-than-RAM at lower speed). Writes do **not** shard across nodes.
- **Sharding:** No automatic horizontal write sharding of the graph; this is a single-writer architecture. See [sharding-partitioning](../concepts/sharding-partitioning.md). (An earlier distributed/sharded design was deprecated.)
- **Read replicas:** Yes — REPLICAs serve read traffic; consistency depends on replication mode (ASYNC = stale reads possible).
- **Storage/compute separation:** No — compute and the in-memory graph are co-located on each node. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** In `IN_MEMORY_TRANSACTIONAL`, each change creates a delta; deltas drive the **WAL**, and **periodic + manual snapshots** persist full state ([durability](https://memgraph.com/docs/fundamentals/data-durability)). Memgraph **cannot run on WAL alone — snapshots are mandatory** for recovery. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Data-loss window:** ⚠️ unverified — default WAL fsync/flush cadence not confirmed; with `ASYNC` replication and periodic (non-synchronous) WAL flush, a crash can lose recent transactions. **No-data-loss requires `STRICT_SYNC` (2PC) replication**, and even single-node durability depends on WAL flush settings. `IN_MEMORY_ANALYTICAL` has **no WAL** — a crash loses everything since the last manual `CREATE SNAPSHOT`.
- **Throughput/latency:** In-memory design targets low-latency reads/traversals and high write throughput; ⚠️ unverified — specific p99/tail figures not independently confirmed here (vendor benchmarks exist but are marketing).
- **Compaction / GC:** MVCC deltas require garbage collection of old versions; snapshot creation can be parallelized (`--storage-parallel-snapshot-creation`) but is disk-I/O-bound and can spike latency during the snapshot window.

## Operations & maturity
- **Backup/restore:** Snapshots (periodic/manual) + WAL; `CREATE SNAPSHOT` / `SHOW SNAPSHOTS`. CRON-scheduled snapshots are an **Enterprise** feature. No first-class PITR beyond snapshot+WAL replay.
- **Observability:** Cypher `PROFILE`/`EXPLAIN` query plans, metrics endpoints, and **Memgraph Lab** GUI for visualization and query inspection.
- **Upgrade story:** Kubernetes **rolling upgrades (ISSU)** with minimal downtime in HA (Enterprise); single-node upgrades imply downtime.
- **Maturity:** Founded 2016 (Dominik Tomicevic, Marko Budiselic), written in C++. Smaller install base than Neo4j; rank ~137 on db-engines. **No Jepsen report exists** as of this writing — distributed-safety claims (STRICT_SYNC 2PC, RAFT coordinators, no-data-loss) are **vendor-stated and unverified by independent formal analysis**. ⚠️ unverified — treat HA correctness claims with caution until externally tested.

## Ecosystem & people
- **Canonical use cases:** Real-time graph analytics, fraud/network/cyber analysis, streaming graph updates (Kafka/Pulsar integration), recommendation, and **GraphRAG / AI memory** for agentic AI (current marketing focus).
- **Anti-patterns:** Datasets that vastly exceed available RAM (unless using on-disk RocksDB mode, which forfeits the speed advantage); workloads needing horizontal write sharding; teams needing serializable isolation or a battle-tested HA track record; bulk OLAP where a columnar warehouse fits better.
- **Connectors:** Bolt protocol (Neo4j drivers work), Python/C++/Rust client and procedure APIs, Kafka/Pulsar/Redpanda streaming, Memgraph Lab, MAGE algorithm library, LangChain/GraphRAG integrations.
- **Community/support:** Active OSS-style community and Discord; commercial support via Enterprise. Docs are reasonably good; learning curve eased for anyone with Cypher experience.

## Licensing & cost
- **License:** **Business Source License 1.1** — *source-available, not OSI open source*, despite the project repeatedly branding itself "open-source" ([LICENSE](https://github.com/memgraph/memgraph/blob/master/LICENSE)). BSL restricts offering Memgraph as a competing service; it **converts to Apache 2.0** after the change date. MAGE is also BSL. See [license-taxonomy](../concepts/license-taxonomy.md). **Divergence to flag:** the "open-source" marketing overstates the license — BSL is source-available with commercial-use restrictions.
- **Self-managed vs managed:** Self-managed (Docker/k8s) Community + Enterprise; **Memgraph Cloud** managed offering exists.
- **Lock-in:** Cypher/Bolt compatibility lowers query lock-in vs Neo4j; Enterprise-gated features (auto-failover, HA, multi-tenancy, RBAC, CRON snapshots) create operational lock-in.
- **Cost model:** Community free (BSL terms); Enterprise is commercial license (node/cluster-based, contact-sales). HA and auto-failover require Enterprise.

## Hardware / deployment
- **Resource profile:** **Memory-bound** — the graph (or its hot working set) should fit in RAM for the in-memory modes; CPU matters for traversal-heavy queries. On-disk mode shifts to disk-bound.
- **Storage assumptions:** Local fast disk (NVMe) for snapshot/WAL I/O; snapshotting is I/O-sensitive. RocksDB mode benefits from fast local SSD.
- **Footprint:** Single-node by default; clustered (MAIN + REPLICAs + coordinators) for HA. Not embedded; not serverless.
- **Deployment:** Docker, Docker Compose, **Kubernetes via Helm** (StatefulSets), plus Memgraph Cloud. Good container/k8s story, especially Enterprise HA reference architectures.

## Bottom line
Reach for Memgraph when you need **low-latency, real-time graph queries or analytics in Cypher** on a dataset that fits in RAM, and you want a faster, lighter alternative to Neo4j — especially for streaming graphs and GraphRAG. Avoid it for graphs far larger than memory (unless you accept the slower on-disk mode), for workloads needing horizontal write sharding or serializable isolation, or where an independently audited HA story is mandatory. **Biggest gotcha:** "ACID" and "open-source" are both narrower than they sound — ACID applies only to `IN_MEMORY_TRANSACTIONAL` (analytical mode has none), the license is BSL not OSI-open, and no-data-loss requires `STRICT_SYNC` replication that most defaults do not enable.

## Sources
- [Memgraph docs — Transactions & isolation levels](https://memgraph.com/docs/fundamentals/transactions)
- [Memgraph docs — Data durability](https://memgraph.com/docs/fundamentals/data-durability)
- [Memgraph blog — Storage modes explained](https://memgraph.com/blog/memgraph-storage-modes-explained)
- [Memgraph docs — Replication](https://memgraph.com/docs/clustering/replication)
- [Memgraph blog — Building HA: license differences](https://memgraph.com/blog/building-high-availability-in-memgraph-license-differences)
- [Memgraph LICENSE (BSL 1.1)](https://github.com/memgraph/memgraph/blob/master/LICENSE)
- [MAGE — Memgraph Advanced Graph Extensions](https://github.com/memgraph/mage)
- [Database of Databases — Memgraph](https://dbdb.io/db/memgraph)
- [Memgraph GitHub](https://github.com/memgraph/memgraph)
