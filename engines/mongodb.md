---
name: MongoDB
slug: mongodb
rank: 5
data_model: Document
license: Server Side Public License (SSPL) — source-available, not OSI-approved
summary: The dominant document database; flexible BSON model and easy scale-out. Default write concern is now `w:majority` (since 5.0), closing the historical durability gap Jepsen exposed in 3.x–4.2; default read concern is still `local`, so causal/transactional guarantees still require explicit majority read concern.
last_researched: 2026-06-04
confidence: high
---

# MongoDB

> The default document database: developer-friendly BSON/JSON model, single-leader replica sets, and horizontal sharding. Since 5.0 the default write concern is `w:majority` (durable by default), but the default read concern is still `local`, so "ACID"/causal-consistency claims still only fully hold when you also opt into `readConcern:majority`/`snapshot`; the weak `w:1` defaults that lost data in every Jepsen test (3.x–4.2) are no longer the out-of-box behavior.

## Identity
- **Taxonomy / data model:** document (BSON — binary JSON with extra types). Multi-model in practice: also serves key-value, geospatial, time-series collections (5.0+), and vector search (via Atlas Vector Search). Not relational. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** WiredTiger is the default storage engine since 3.2 — a B-tree-based row/document store with MVCC and document-level concurrency, compressed (snappy default). Historically supported pluggable engines (MMAPv1 removed in 4.2; in-memory engine in Enterprise). Not LSM by default. See [lsm-vs-btree](../concepts/lsm-vs-btree.md), [mvcc](../concepts/mvcc.md).
- **Workload:** primarily OLTP / operational. Aggregation pipeline handles moderate analytics; not a columnar OLAP engine. No real HTAP — Atlas offers separate analytics nodes and a columnar "Search/Online Archive" path, but heavy analytics typically offload to a separate system (Atlas Data Federation, BI Connector, or external warehouse).

## Distribution & consistency
- **CAP under partition:** CP-leaning. A replica set requires a majority to elect/retain a primary; a minority partition has no primary and rejects writes. With the modern `w:majority` default, acknowledged writes survive failover; only weaker explicit concerns (`w:1`) or PSA-arbiter configs that fall back to `w:1` reopen the rollback window. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition, leans toward Consistency (minority side cannot write); Else, the read path still favors Latency over Consistency (default `readConcern:local` can return data that may roll back), while the write path is durable-by-default at `w:majority` since 5.0. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** non-transactional ops are single-document atomic. Multi-document ACID transactions added for replica sets in 4.0 and sharded clusters in 4.2, providing **snapshot isolation** (not serializable) via `readConcern:"snapshot"` + `writeConcern:"majority"`. ["Snapshot" read concern only returns majority-committed data **if** the transaction commits with `w:majority`](https://www.mongodb.com/docs/manual/reference/read-concern-snapshot/) — otherwise guarantees do not hold, even for read-only transactions. See [isolation-levels](../concepts/isolation-levels.md). **Claim-vs-reality:** MongoDB markets "full ACID transactions"; [Jepsen calls this misleading given snapshot isolation's actual guarantees](https://jepsen.io/analyses/mongodb-4.2.6).
- **Replication:** single-leader (one primary per replica set), asynchronous oplog replication to secondaries; Raft-derived election protocol (protocolVersion 1). Failover elects a new primary on a ~10s heartbeat timeout. ⚠️ unverified — the "median new-primary ~12s" figure could not be confirmed from current docs; election time depends on `electionTimeoutMillis` (default 10s) and config. Acknowledged writes made with explicit `w:1` (not the modern default) that are not yet replicated [can be rolled back on failover](https://www.mongodb.com/docs/manual/core/replica-set-elections/); `w:majority` (the default since 5.0) survives failover. Majority-vote elections prevent split-brain. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** Yes — per-operation `writeConcern` (`w:1`, `w:majority`, `w:<n>`, `j:true` for journal fsync) and `readConcern` (`local`, `available`, `majority`, `linearizable`, `snapshot`), plus read preference (`primary`, `primaryPreferred`, `secondary`, `nearest`). [**Defaults since 5.0 are `w:majority` / `readConcern:local`**](https://www.mongodb.com/docs/manual/reference/mongodb-defaults/) (pre-5.0 the write default was `w:1`; PSA/arbiter configs where data-bearing voters ≤ voting majority still default to `w:1`). The remaining default-read-concern `local` is where stale/rollback-able reads and most causal-consistency anomalies still originate.
- **Clock dependency:** uses hybrid logical clocks / cluster time for causal consistency and ordering across the cluster; does not require synchronized wall clocks for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** flexible / schema-on-read by default — documents in a collection need not share a shape; the effective schema lives in application code. Optional [JSON-Schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/) can enforce rules per collection (schema-on-write when enabled).
- **Migration/evolution:** add/remove fields freely without DDL; no table-rewrite ALTER. Index builds are online by default (background/hybrid builds since 4.2). Large-scale reshaping is an application/migration-script concern, not a DDL operation.
- **Type system:** rich BSON types — ObjectId, dates, Decimal128, binary, arrays, embedded documents, geospatial (GeoJSON, 2dsphere indexes), and vector embeddings (Atlas). Native arrays and nested documents are first-class.

## Query interface
- **Language:** MongoDB Query Language (MQL) — a JSON-based query/CRUD API plus the Aggregation Pipeline (a composable stage-based DSL for filtering, joins via `$lookup`, grouping, window functions via `$setWindowFields`). No SQL natively; Atlas SQL / BI Connector provide read-only SQL. Not SQL-standard.
- **Transactions:** single-document writes are always atomic; multi-document, multi-collection ACID transactions available (replica sets 4.0+, sharded 4.2+) with snapshot isolation. [Default 60s transaction time limit](https://www.mongodb.com/docs/manual/core/transactions/); apps must retry on transient/write-conflict errors.
- **Native vs app-side:** secondary indexes (single, compound, multikey, text, geospatial, hashed, partial, TTL, wildcard, vector), `$lookup` joins, aggregations, and window functions all run server-side. Joins are far weaker/costlier than relational engines — the model favors embedding over joining.
- **Stored procedures / UDFs:** no traditional stored procedures. `$function`/`$accumulator` allow server-side JavaScript in aggregation; Atlas provides Triggers and Functions (JS) for event-driven logic. Server-side JS is generally discouraged for hot paths.

## Scaling & topology
- **Vertical vs horizontal:** scales horizontally via sharding. Shard key chosen per collection; **range** or **hashed** sharding. Picking a poor shard key (low cardinality, monotonic) causes hot-spotting/jumbo chunks and is historically painful. [Live `reshardCollection` exists since 5.0](https://www.mongodb.com/docs/manual/sharding/) (and 8.0 `shardAndDistributeCollection`), easing the old "shard key is forever" problem, but resharding is a heavy data-movement operation.
- **Read replicas:** secondaries serve reads under non-primary read preferences; those reads are **asynchronous and may be stale** unless `readConcern:majority`/`linearizable` is used. Causal consistency requires causal sessions plus majority concerns.
- **Storage/compute separation:** classic MongoDB couples storage and compute per node. Atlas adds tiered options (Online Archive, Data Federation, Search nodes) that partially decouple, but the core engine is not a Snowflake/Aurora-style separated architecture. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WiredTiger journal (WAL); checkpoints every 60s by default. `j:true` forces journal fsync before ack. **Data-loss window:** with the modern `w:majority` default, an acknowledged write is on disk (journaled) on a majority of nodes and survives single-node crash and failover. With explicit `w:1`/`j:false`, an acknowledged write can still be lost on a crash before journal flush or rolled back on failover. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency profile:** strong for indexed point lookups and embedded-document reads. Tail (p99) latency degrades with WiredTiger cache pressure, long-running transactions (which pin snapshots and accumulate cache), and balancer/chunk-migration activity on sharded clusters.
- **Compaction / vacuum / GC:** WiredTiger does not auto-return freed space to the OS; `compact` (blocking-ish) or resync reclaims it. MVCC old versions held in cache during long transactions are a known p99 hazard.

## Operations & maturity
- **Backup/restore, PITR:** mongodump/mongorestore for small data; filesystem/volume snapshots for large; Atlas and Ops Manager provide continuous backup with point-in-time recovery from the oplog.
- **Observability:** rich — `explain()` query plans, `mongostat`/`mongotop`, database profiler / slow-query log, `serverStatus`, free monitoring + Atlas dashboards.
- **Upgrade story:** rolling upgrades within a replica set (upgrade secondaries, step down primary). Feature Compatibility Version (FCV) gating must be advanced deliberately; skipping major versions is unsupported. Day-2 burden centers on shard-key/index design and balancer tuning.
- **Maturity:** very mature, large production footprint since ~2009. **Jepsen findings are the key caveat:** across [3.4.0-rc3](https://jepsen.io/analyses/mongodb-3-4-0-rc3), [3.6.4](https://jepsen.io/analyses/mongodb-3-6-4), and [4.2.6](https://jepsen.io/analyses/mongodb-4.2.6), Jepsen found default settings lose acknowledged writes and violate causal consistency. The [4.2.6 report](https://jepsen.io/analyses/mongodb-4.2.6) found that transactions **ignored database/collection-level read/write concerns**, defaulting to `readConcern:local` + `w:1`, and that even at `readConcern:snapshot` + `w:majority` it observed G1c (cyclic info flow), read skew, duplicate/lost writes, and "retrocausal" anomalies (~10% of transactions affected); MongoDB attributed these to a transaction-retry bug (SERVER-48307) patched in 4.2.8. Causal consistency in client sessions only holds with both read and write concern `majority` — [MongoDB updated its docs to say so after the report](https://www.infoq.com/news/2020/05/Jepsen-MongoDB-4-2-6/).

## Ecosystem & people
- **Canonical use cases:** content/catalog/CMS, user profiles, IoT/event ingestion, mobile/app backends, single-view aggregation, real-time analytics on flexible/evolving documents. **Anti-patterns:** workloads needing many-to-many joins or complex relational integrity, strong serializable transactions across many documents, heavy ad-hoc analytical SQL, or any case running an older (<5.0) deployment or a PSA-arbiter topology that silently falls back to `w:1`.
- **Drivers / ORMs / connectors:** official drivers for ~12 languages; ODMs (Mongoose for Node, Spring Data Mongo, Motor/PyMongo). CDC via the [MongoDB Kafka connector and Change Streams](https://www.mongodb.com/docs/manual/changeStreams/); Debezium; Atlas BI Connector / Atlas SQL for BI tools.
- **Community & support:** one of the most popular databases (consistently top-5 on db-engines). Large community, extensive docs (generally good but historically soft-pedaled the concern caveats), commercial support via MongoDB Inc. and Atlas. Low learning curve to start; correct durable/consistent operation requires real understanding of concerns and shard keys.

## Licensing & cost
- **OSS license & flavor:** [Server Side Public License (SSPL) since October 2018](https://www.mongodb.com/legal/licensing/server-side-public-license) for Community Server (previously AGPL v3). SSPL is **source-available, not OSI-approved open source** — [OSI submission was withdrawn in 2019; Debian/Red Hat/Fedora dropped it](https://en.wikipedia.org/wiki/Server_Side_Public_License). Its network clause requires anyone offering MongoDB-as-a-service to open-source their entire service stack. See [license-taxonomy](../concepts/license-taxonomy.md). (Distinct from [amazon-documentdb](amazon-documentdb.md), AWS's MongoDB-API-compatible engine built on Aurora storage — a response to SSPL; not the same codebase and lags in API/version compatibility.)
- **Self-managed vs managed:** both. Community Server (SSPL) self-managed; Enterprise Advanced (commercial); MongoDB Atlas managed cloud (AWS/GCP/Azure). Atlas adds proprietary features (Search, Vector Search, triggers) that create lock-in.
- **Cost model:** self-managed is per-node infra cost; Atlas is per-instance-tier (compute + storage + I/O) and serverless/elastic options bill per-RPU. At scale, Atlas plus cross-AZ replication and backup add up; egress and search nodes are common cost surprises.

## Hardware / deployment
- **Resource profile:** memory-sensitive — best when the working set (indexes + hot documents) fits the WiredTiger cache (default ~50% of RAM − 1 GB). Spilling to disk hurts latency. Mixed CPU/IO bound depending on workload.
- **Storage assumptions:** prefers fast local NVMe or low-latency block storage; tolerates network-attached (EBS) but journal fsync latency matters for `j:true`.
- **Footprint:** clustered (replica set is the minimum recommended unit; standalone for dev only). Sharded clusters add config-server replica set + mongos routers. Not embedded. Atlas Serverless exists.
- **Deployment:** SaaS (Atlas) or on-prem/self-managed. Good Kubernetes story via the official MongoDB Kubernetes Operator (Enterprise/Community); replica sets map to StatefulSets with persistent volumes.

## Bottom line
Reach for MongoDB when your data is naturally document-shaped, the schema evolves fast, and you want easy horizontal scale-out with a friendly developer API — it is excellent for operational app backends, catalogs, and event data. Do not reach for it for heavily relational/join-heavy workloads, strict serializable multi-document transactions, or ad-hoc SQL analytics. **The single biggest gotcha:** the historical unsafe defaults (`w:1`) drove every Jepsen finding from 3.x through 4.2.6, but the write default became `w:majority` in 5.0, so out-of-box durability is now good on modern versions. The remaining traps: the default *read* concern is still `local` (stale/rollback-able reads), causal consistency and transaction guarantees still require explicit `readConcern:majority`/`snapshot`, and PSA-arbiter topologies silently fall back to `w:1`. Verify your version and topology rather than assuming the old defaults.

## Sources
- [MongoDB Manual — Transactions](https://www.mongodb.com/docs/manual/core/transactions/)
- [MongoDB Manual — Read Concern "snapshot"](https://www.mongodb.com/docs/manual/reference/read-concern-snapshot/)
- [MongoDB Manual — Replica Set Elections](https://www.mongodb.com/docs/manual/core/replica-set-elections/)
- [MongoDB Manual — Sharding](https://www.mongodb.com/docs/manual/sharding/)
- [Jepsen: MongoDB 4.2.6](https://jepsen.io/analyses/mongodb-4.2.6)
- [Jepsen: MongoDB 3.6.4](https://jepsen.io/analyses/mongodb-3-6-4)
- [Jepsen: MongoDB 3.4.0-rc3](https://jepsen.io/analyses/mongodb-3-4-0-rc3)
- [InfoQ — Jepsen Disputes MongoDB's Data Consistency Claims](https://www.infoq.com/news/2020/05/Jepsen-MongoDB-4-2-6/)
- [MongoDB — Server Side Public License](https://www.mongodb.com/legal/licensing/server-side-public-license)
- [Wikipedia — Server Side Public License](https://en.wikipedia.org/wiki/Server_Side_Public_License)
