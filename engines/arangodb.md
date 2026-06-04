---
name: ArangoDB
slug: arangodb
rank: 80
data_model: Multi-model (document, graph, key-value, search, vector)
license: Business Source License 1.1 (source-available, post-2018 relicensing); converts to Apache 2.0 after 4 years
summary: Native multi-model DB (document + graph + KV) with one query language; cluster ACID only holds inside a single shard/OneShard.
last_researched: 2026-06-04
confidence: high
---

# ArangoDB

> A single-engine multi-model store (JSON documents, property graph, key-value) queried by one SQL-like language (AQL) — convenient if you genuinely need graph + document together, but its full ACID guarantee silently degrades to per-shard once you cluster.

## Identity
- **Taxonomy / data model:** Native multi-model — documents (JSON), property graph (edges as documents), and key-value share one storage and one query language (AQL). Also full-text/[full-text-search](../concepts/full-text-search.md) via ArangoSearch and vector search (HNSW, added 3.12.x). See [graph-data-model](../concepts/graph-data-model.md).
- **Storage model:** Single storage engine on [RocksDB](../concepts/lsm-vs-btree.md) (LSM-tree) since 3.7; the older mmap "MMFiles" engine was removed. On-disk values are VelocyPack (compact binary JSON). Document-level locks: writes don't block reads and reads don't block writes ([RocksDB engine docs](https://docs.arangodb.com/3.12/components/arangodb-server/storage-engine/)).
- **Workload:** Primarily OLTP / operational, with graph traversals and Pregel-style graph analytics; ArangoSearch adds search workloads. Not a columnar OLAP engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP. The cluster keeps configuration in an "Agency" (a Raft-based KV store, see [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)); on partition ArangoDB prefers consistency over availability and refuses writes on the minority side ([ArangoDB consensus blog](https://arangodb.com/2017/01/reaching-harnessing-consensus-arangodb/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no official PACELC statement; behavior is effectively PC/EC for metadata (Raft) but data-plane transactions use no global consensus, trading latency for weaker cross-shard guarantees (see below).
- **Default isolation & what's achievable:** Single server or OneShard database = full ACID, with snapshot isolation from RocksDB ([transactions docs](https://docs.arango.ai/arangodb/3.11/develop/transactions/)). In a multi-shard cluster only **local snapshot isolation** holds — each DB-Server sees a consistent snapshot of *its* data, but there is no global snapshot across shards. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **The "ACID" divergence (most important caveat):** ArangoDB markets ACID transactions, but in a sharded cluster that only fully holds for single-document ops and for collections/queries confined to **one shard**. Multi-document/multi-collection transactions spanning shards on multiple DB-Servers are **not atomic on commit** — if a DB-Server fails mid-commit, sub-transactions can commit on some servers and not others, with no global rollback ([transaction limitations](https://docs.arango.ai/arangodb/stable/develop/transactions/limitations/)). Distributed transactions use no global consensus by design — "fast but vulnerable to unexpected server outages." The vendor's own remedy is the OneShard deployment (below).
- **Replication:** Single-leader per shard. Async replication by default; **synchronous** replication (leader waits for in-sync followers) is configurable per collection via `replicationFactor` / `writeConcern`. Failover is orchestrated by the Agency. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited: per-collection sync vs async replication and `writeConcern`; not per-query Dynamo-style read consistency levels.
- **Clock dependency:** No reliance on synchronized physical clocks for correctness (no TrueTime/HLC scheme). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read:** documents are schemaless JSON; an optional per-collection **schema validation** (JSON Schema) can be enabled for schema-on-write enforcement.
- **Migration/evolution:** no rigid table DDL to lock; adding/removing fields is an app concern. Adding **indexes** on large collections is a background build but can be I/O heavy.
- **Type system:** JSON types, arrays, nested objects; geospatial (GeoJSON) indexes; full-text via ArangoSearch analyzers; vector (HNSW) indexes in recent 3.12.x. No native interval/decimal-precision types.

## Query interface
- **Language:** AQL, a declarative SQL-like DSL that expresses document CRUD, graph traversals (`FOR v,e,p IN ... TRAVERSAL`), joins, and aggregations in one query. Not SQL-standard; not Cypher/Gremlin (though there is limited Gremlin support via plugins). Also a REST/HTTP API.
- **Transactions:** multi-statement ACID on single server / OneShard; single-document atomic always; cross-shard multi-document transactions are **not** guaranteed atomic (see above). Stream transactions and JS-based transactions both exist.
- **Native vs app-side:** native joins, secondary indexes (persistent/RocksDB, geo, full-text, vector), aggregations, and graph traversals — no need to denormalize across "tables."
- **Stored procedures / UDFs:** **Foxx** microservice framework runs JavaScript (V8) directly in the DB-Server for custom HTTP endpoints and UDFs.

## Scaling & topology
- **Vertical vs horizontal:** scales horizontally via a Coordinator / DB-Server / Agency cluster. Coordinators are stateless query routers; DB-Servers hold shards.
- **Sharding:** hash-based on shard key(s) (default `_key`). Resharding requires moving shards; changing the number of shards on an existing collection is not a trivial online operation. **SmartGraphs** co-locate graph vertices/edges by a shard key so traversals stay local; **SatelliteCollections** replicate small lookup collections to every DB-Server for local joins (Enterprise features).
- **OneShard:** an Enterprise deployment that pins an entire database to a single DB-Server (still replicated for HA) — restores full multi-collection ACID and cuts network hops, at the cost of that database not scaling out across nodes. This is the recommended pattern when you need real cluster-wide ACID ([OneShard docs](https://docs.arango.ai/arangodb/stable/deploy/oneshard/)).
- **Read replicas:** in-sync followers exist for HA; by default reads go to the leader. Reading from followers is possible but those reads can be stale.
- **Storage/compute separation:** No — DB-Servers own their local storage (shared-nothing). Not an Aurora/Neon-style design. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** RocksDB WAL with group commit; fsync cadence is tunable (`--rocksdb.sync-interval` and sync-on-commit options). Less-than-synchronous settings widen the crash data-loss window. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** steady insert performance even when data exceeds RAM (LSM strength); graph traversal latency depends heavily on locality (hence SmartGraphs). ⚠️ unverified — no authoritative, current p99 tail-latency benchmarks; vendor benchmarks should be treated as marketing.
- **Compaction / GC:** RocksDB background compaction reclaims space and can cause write stalls / p99 spikes under heavy write load — standard LSM behavior; tune compaction and block cache. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).

## Operations & maturity
- **Backup/restore:** logical dumps (`arangodump`/`arangorestore`); Enterprise hot backups (consistent, near-instant snapshots). PITR is not a first-class native feature the way it is in mature RDBMSs (⚠️ unverified for latest versions).
- **Observability:** metrics endpoint (Prometheus-compatible), AQL query profiling / `EXPLAIN` execution plans, slow-query log, and a built-in web UI.
- **Upgrade story:** rolling upgrades supported in cluster; single-server upgrades require restart. Day-2 burden includes RocksDB tuning, shard/replication management, and (post-3.12) license accounting.
- **Maturity & Jepsen:** GA since ~2014; production-used but a niche player (db-engines rank ~80). **Jepsen:** there is **no independent Jepsen report on the whole database.** ArangoDB ran its *Agency* (Raft layer) through the Jepsen *framework* internally and reported it behaved linearizably ([ArangoDB blog](https://arangodb.com/2017/01/reaching-harnessing-consensus-arangodb/)) — that is a vendor self-test of one component, not a third-party audit of cluster transaction safety. Treat cluster transactional-isolation claims as unverified by independent analysis. Known failure mode: the cross-shard commit non-atomicity above.

## Ecosystem & people
- **Canonical use cases:** apps that genuinely need document + graph together (fraud/recommendation graphs, knowledge graphs, network/IT topology), where consolidating onto one engine beats running Postgres + Neo4j. ArangoSearch covers integrated search; recent vector support enables RAG/similarity inside the same store.
- **Anti-patterns:** large-scale columnar analytics/OLAP; workloads needing rock-solid cluster-wide multi-document ACID without accepting OneShard's single-node-per-DB limit; teams wanting a huge talent pool / SQL ecosystem (AQL is a learning curve). If you only need a graph, [neo4j](neo4j.md) has a deeper graph ecosystem; if you only need documents, [mongodb](mongodb.md) has far broader tooling.
- **Drivers/connectors:** official drivers for Java, Go, Python, JS; community ORMs; Foxx for in-DB services. CDC/Kafka and dbt/BI integrations are thinner than for mainstream engines (⚠️ unverified for current maturity).
- **Community/support:** moderate community, much smaller than MongoDB/Neo4j; commercial support and managed cloud from ArangoDB GmbH; docs are reasonably good (now hosted under arango.ai / docs.arango.ai).

## Licensing & cost
- **License:** **Post-2018 relicensing** — Community Edition moved from **Apache 2.0 to BSL 1.1** (source-available) starting with **3.12 (early 2024)**; Change Date 4 years, Change License Apache 2.0 ([licensing blog](https://arango.ai/blog/evolving-arangodbs-licensing-model-for-a-sustainable-future/)). See [license-taxonomy](../concepts/license-taxonomy.md). The precompiled "Community License" caps **non-commercial / internal commercial use at 100 GiB per dataset/cluster** and forbids offering it as a managed service; broader commercial/managed use requires an Enterprise agreement (as of late 2025).
- **Self-managed vs managed:** self-managed Community/Enterprise, plus **ArangoGraph (formerly Oasis)** managed cloud on AWS/GCP/Azure.
- **Lock-in:** AQL, Foxx, SmartGraphs/SatelliteCollections, and OneShard are proprietary/ArangoDB-specific — migrating off is non-trivial. Enterprise-only features (hot backup, SmartGraphs, SatelliteCollections, OneShard) gate the capabilities you most want at scale.
- **Cost model:** Enterprise/cloud is effectively per-node/cluster; the 100 GiB Community cap pushes growing or commercial users toward paid tiers.

## Hardware / deployment
- **Resource profile:** LSM engine handles working sets larger than RAM (disk-bound is acceptable), but block cache / memory still matters for index and traversal performance; graph traversals can be CPU-bound. Working set need not fit in RAM.
- **Storage assumptions:** local fast disk (NVMe/SSD) preferred for RocksDB; shared-nothing, so each DB-Server wants its own local volume.
- **Footprint:** single binary that runs single-node, clustered (Coordinator/DB-Server/Agency), or as a managed service. Not embeddable.
- **Deployment:** on-prem, containers, Kubernetes via the official **ArangoDB Kubernetes Operator** (StatefulSet-based); managed via ArangoGraph.

## Bottom line
Reach for ArangoDB when you truly need document **and** graph (and maybe KV/search/vector) in one engine with one query language, and a single-node or OneShard deployment satisfies your scale — that is its sweet spot. Avoid it for heavy OLAP, for workloads that demand cluster-wide multi-document ACID while still sharding across many nodes, or where a large talent pool and ecosystem matter. The single biggest gotcha: "ACID transactions" is true on a single server / OneShard but **silently degrades to per-shard, non-atomic-on-commit once you shard across DB-Servers** — and there is no independent Jepsen audit of those cluster guarantees.

## Sources
- [Transactions](https://docs.arango.ai/arangodb/3.11/develop/transactions/) and [Transaction limitations](https://docs.arango.ai/arangodb/stable/develop/transactions/limitations/) (official docs — cross-shard atomicity caveat, local snapshot isolation)
- [OneShard deployments](https://docs.arango.ai/arangodb/stable/deploy/oneshard/) (official docs)
- [Storage engine (RocksDB)](https://docs.arangodb.com/3.12/components/arangodb-server/storage-engine/) (official docs)
- [Reaching and harnessing consensus in ArangoDB](https://arangodb.com/2017/01/reaching-harnessing-consensus-arangodb/) (Agency/Raft + internal Jepsen-framework test)
- [Evolving ArangoDB's licensing model (BSL)](https://arango.ai/blog/evolving-arangodbs-licensing-model-for-a-sustainable-future/) and [LICENSE](https://github.com/arangodb/arangodb/blob/devel/LICENSE)
- [ArangoDB — Wikipedia](https://en.wikipedia.org/wiki/ArangoDB) (history, models, company)
