---
name: ScyllaDB
slug: scylladb
rank: 66
data_model: Wide-column (Cassandra-compatible)
license: Source-available (since 2025.1); ScyllaDB OSS 6.2 was the final AGPLv3 release
summary: C++ rewrite of Cassandra — same CQL/data model, far better p99 and per-node throughput, now source-available.
last_researched: 2026-06-04
confidence: high
---

# ScyllaDB

> A drop-in-compatible Cassandra clone rewritten in C++ on a shard-per-core architecture for dramatically lower tail latency and higher density — an AP wide-column store that bolts strong consistency onto topology (Raft) and conditional writes (LWT/Paxos) without changing the core data path.

## When to use

**Use ScyllaDB if:**
- ✅ You have a Cassandra- or DynamoDB-shaped workload (high write throughput, simple access patterns, horizontal scale) hurt by tail latency, JVM GC pauses, or node count/cost.
- ✅ You want the C++/Seastar shard-per-core design's better p99/p999 and per-node density — fewer, denser nodes for lower TCO.
- ✅ You can run on many cores + fast local NVMe (it pins cores and manages its own memory/IO).

**Avoid ScyllaDB if:**
- ❌ You need joins, OLAP, multi-key ACID transactions, or strong-consistency-by-default — plain CQL writes are **not isolated by design** (destructive per-cell upserts), and strong consistency is scoped to single-partition LWT CAS and Raft-backed metadata only.
- ❌ You require a true OSS license — it moved to source-available in 2025.1; you are pinned to 6.2/AGPL forever otherwise.
- ❌ Your storage is network-attached/EBS-style — that undermines the entire low-tail-latency value proposition.
- ❌ Your workload is tombstone-heavy (frequent updates/deletes to the same row) or has unbounded partition growth.

## Identity
- **Taxonomy / data model:** Wide-column / partitioned row store, CQL-compatible with Apache [apache-cassandra](apache-cassandra.md) (same data model, query language, SSTable format, drivers). Multi-model only loosely: it ships a [amazon-dynamodb](amazon-dynamodb.md)-compatible API (Alternator) and CQL.
- **Storage model:** [LSM-tree](../concepts/lsm-vs-btree.md) on disk (SSTables, size-tiered/leveled/incremental/time-window compaction strategies), row-oriented within partitions. The differentiator is the runtime, not the storage: the Seastar framework gives a **shard-per-core, shared-nothing, thread-per-core** design with its own user-space scheduler, async I/O, and (optionally) a custom userspace memory allocator. Each CPU core owns a slice of data and runs without locks.
- **Workload:** OLTP-style high-throughput point/range reads and writes at scale; **not** OLAP. No joins, no ad-hoc analytics. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP — analytics requires exporting to a separate system (Spark connector exists but ScyllaDB itself is a serving store).

## Distribution & consistency
- **CAP under partition:** **AP by default** — leaderless, every replica accepts writes; the cluster stays available and reconciles later via hinted handoff, read-repair, and anti-entropy repair. See [cap-pacelc](../concepts/cap-pacelc.md), [replication-models](../concepts/replication-models.md). You can *tune toward CP* per query (QUORUM/SERIAL), but the underlying model is Dynamo-style eventual consistency, same as [apache-cassandra](apache-cassandra.md).
- **PACELC:** **PA/EL** in the Dynamo lineage — under partition favors availability; else (normal operation) favors latency over consistency, with the tradeoff chosen per-request via [consistency level](../concepts/cap-pacelc.md).
- **Tunable consistency:** per-query consistency levels (ONE / QUORUM / LOCAL_QUORUM / ALL / SERIAL etc.). R+W>N gives "strong" read-your-writes-ish behavior but **not** linearizability for plain writes ([conflicting concurrent writes resolve last-write-wins by timestamp, cell-by-cell](https://docs.scylladb.com/manual/stable/kb/consistency.html)).
- **Default isolation & what's achievable:** Plain CQL writes are **not isolated** — an INSERT is a destructive per-cell upsert; concurrent writes can interleave at the cell level. For atomic conditional writes there are **Lightweight Transactions (LWT)** using a Paxos round (`IF NOT EXISTS` / `IF <cond>`), giving linearizable single-partition compare-and-set at high latency cost (multiple round trips). There are **no general multi-partition ACID transactions**. Calling ScyllaDB "ACID" is wrong; it is single-partition CAS via Paxos, otherwise eventually consistent. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** leaderless quorum, configurable replication factor per keyspace, rack/DC-aware (NetworkTopologyStrategy), async multi-DC replication. No single leader for the data path. **Cluster metadata (schema + topology)** moved to **[Raft](../concepts/consensus-raft-paxos.md)** and is strongly consistent and serialized by a centralized topology coordinator (default since 6.0 / 2025.1) — this fixed the historically dangerous concurrent-schema/topology-change failure modes.
- **Clock dependency:** correctness of LWW conflict resolution and LWT timestamps depends on client/coordinator timestamps; clock skew can cause silent write loss or stale reads (inherited Cassandra behavior). See [clocks-and-time](../concepts/clocks-and-time.md). Not TrueTime-grade — no clock-bound waiting.

## Schema
- **Schema-on-write:** keyspaces/tables/columns are declared; CQL is typed. Static schema with flexible per-row sparse columns. Collections (map/set/list), UDTs, counters, and a native `vector` type (vector search added in recent releases). No native geospatial.
- **Migration/evolution:** online `ALTER TABLE` (add/drop columns) is cheap and non-locking. Schema changes are now Raft-serialized so they no longer risk the schema-disagreement split-brain that plagued Cassandra/early Scylla.
- **Type system:** standard CQL types plus collections, UDTs, counters, TTL per cell, frozen types, tuples, and vectors. JSON is supported as an I/O convenience (`INSERT JSON`), not a first-class document model.

## Query interface
- **Language:** **CQL** (Cassandra Query Language — SQL-like but deliberately restricted: no joins, no subqueries, no arbitrary `WHERE` without a matching index/partition key). Also an **Alternator** API wire-compatible with Amazon [amazon-dynamodb](amazon-dynamodb.md).
- **Transactions:** single-partition conditional writes via **LWT/Paxos**; `BATCH` gives atomicity (not isolation) within a partition. No cross-partition ACID.
- **Native vs app-side:** secondary indexes (global and local) and materialized views exist but with caveats (eventual consistency of views; secondary indexes are a fan-out). Aggregations are limited (`COUNT`, `SUM` etc. with severe performance caveats on large partitions). **Joins are app-side.** Data modeling is query-first / denormalized.
- **Stored procedures / UDFs:** UDFs/UDAs supported via **Lua** and **WebAssembly (Wasm)**; far less central than in an RDBMS.

## Scaling & topology
- **Horizontal, shared-nothing:** consistent-hash ring, automatic partitioning by partition key. **Tablets** (default since 2025.1) replaced/augmented vnodes: data is split into tablets that are dynamically split, merged, and rebalanced across nodes by the Raft-driven load balancer. This makes adding/removing nodes much faster and enables mixed-instance-type clusters and faster elasticity than classic Cassandra token ranges.
- **Resharding pain:** historically vnode rebalancing was slow/manual-ish; tablets largely fix this — node bootstrap/decommission is incremental and parallel.
- **Read replicas / consistency:** all replicas are equal; read consistency is whatever the per-query consistency level dictates. Multi-DC async replication for geo-distribution.
- **Storage/compute separation:** classically **no** — local NVMe, data co-located with compute. **ScyllaDB X Cloud** (managed) moves toward more elastic separation, but the self-managed engine is shared-nothing local-disk. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** commitlog ([WAL](../concepts/wal-and-durability.md)) + memtable → flush to SSTable. Commitlog fsync is **periodic by default** (configurable batch/group commit), so the default config has a **data-loss window** (a few ms to the commitlog sync period) on simultaneous-node crash; replication factor is the real durability backstop, not single-node fsync. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** the headline strength — shard-per-core + the Seastar I/O scheduler and **workload prioritization** deliver predictable **low p99/p999** and very high per-node throughput, letting users run far fewer/denser nodes than Cassandra for the same load. This is the main reason to choose it over [apache-cassandra](apache-cassandra.md).
- **Compaction/GC behavior:** LSM compaction runs continuously; ScyllaDB's scheduler isolates compaction and repair from foreground queries to protect p99 (a key advantage vs JVM-GC-induced tail spikes in Cassandra — no JVM, no GC pauses). Large partitions and tombstone-heavy delete patterns still hurt, as in any LSM/Cassandra-lineage store.

## Operations & maturity
- **Backup/restore:** snapshots (hard-link based); PITR-style and managed backup via ScyllaDB Manager / Cloud. Repair (anti-entropy) is a routine operational chore, automated by Manager.
- **Observability:** Prometheus metrics + Grafana dashboards (strong), `nodetool`-equivalent, tracing, `EXPLAIN`-like query introspection is weak (CQL plans are simple by design).
- **Upgrade story:** rolling upgrades, no downtime; day-2 burden centers on compaction tuning, repair scheduling, and large-partition/tombstone hygiene — lighter than Cassandra operationally but still a real distributed-systems commitment.
- **Maturity & Jepsen:** mature, production-proven (Discord, Comcast, others). **Jepsen analyzed Scylla 4.2-rc3 ([jepsen.io/analyses/scylla-4.2-rc3](https://jepsen.io/analyses/scylla-4.2-rc3))** and found serious safety bugs: LWT aborted reads, stale reads tens of seconds old in healthy clusters, **split-brain from incorrect row-hash calculation (ignoring null columns)**, and split-brain across membership changes; it also confirmed that **plain writes are not isolated** ("insert is a destructive operation by design", inherited from Cassandra). Most data-path bugs were fixed by 4.3-rc1, but **membership-change split-brain persisted** at report time and the no-isolation-on-plain-writes property is by design. The later **Raft-based topology coordinator (6.0+)** specifically addresses the concurrent-membership-change class of problems. Treat "strong consistency" claims as scoped to LWT single-partition CAS and to metadata, not to general reads/writes.

## Ecosystem & people
- **Canonical use cases:** high-write, low-latency serving at scale — time-series/IoT, messaging/feeds, user/session/event stores, ad-tech, anywhere Cassandra fit but its tail latency and node count hurt. Drop-in migration target for Cassandra and DynamoDB cost reduction.
- **Anti-patterns:** anything needing multi-key ACID transactions, joins, ad-hoc/OLAP queries, strong serializable isolation on ordinary writes, or strict-consistency-by-default. Frequent updates/deletes to the same row (tombstones), unbounded partition growth, and read-heavy relational workloads are poor fits. Not a system of record for money-movement unless you carefully constrain to LWT.
- **Drivers/connectors:** Cassandra CQL drivers work unchanged; ScyllaDB ships shard-aware drivers for better routing. CDC (native CDC tables), Kafka connectors, Spark, and the DynamoDB-compatible Alternator API. Good Prometheus/Grafana integration. Smaller community than Cassandra but active and vendor-backed.
- **Docs quality:** good. Learning curve = Cassandra's data-modeling discipline (denormalize, model by query) plus Seastar-specific ops tuning.

## Licensing & cost
- **License:** **Source-available since ScyllaDB 2025.1 (April 2025).** [ScyllaDB OSS 6.2 was the final AGPLv3 open-source release](https://www.scylladb.com/2025/04/08/announcing-scylladb-2025-1/); the company consolidated the old dual OSS/Enterprise streams into one **source-available** product, ending the truly-open-source line. This is a **post-2018-style relicensing away from OSS** — see [license-taxonomy](../concepts/license-taxonomy.md). A free tier of full-featured Enterprise is offered to the community but [with usage restrictions](https://www.theregister.com/2025/06/18/scylladb_license_change/): [capped at 10TB total disk and 50 vCPUs across all clusters per organization](https://www.scylladb.com/source-available-faq/). If you require a true OSS license, you are pinned to 6.2 / AGPL forever.
- **Self-managed vs managed:** self-managed (source-available binaries) or **ScyllaDB Cloud / X Cloud** (managed DBaaS on AWS/GCP).
- **Lock-in:** CQL/Cassandra compatibility limits engine lock-in (you can move to Cassandra), but Scylla-specific features (Alternator, workload prioritization, tablets behaviors) and the license change are the real lock-in considerations. Cost model: per-node/per-core for self-managed; consumption-based for Cloud. The economic pitch is **fewer, denser nodes** → lower TCO vs Cassandra/DynamoDB.

## Hardware / deployment
- **Resource profile:** CPU-and-I/O-bound by design; thrives on **many cores + fast local NVMe**. Working set need not fit in RAM (LSM on disk), but more RAM = better cache hit rate. Pins itself to cores and manages memory/IO itself, so it expects dedicated machines, not noisy multi-tenant hosts.
- **Storage assumptions:** **local NVMe SSD strongly preferred**; network-attached/EBS-style latency undermines the whole low-tail-latency value proposition.
- **Footprint:** clustered distributed server; no embedded mode. Self-tuning to hardware (`scylla_setup`).
- **Deployment:** on-prem, cloud VMs, Kubernetes via **ScyllaDB Operator** (StatefulSets with local NVMe and CPU pinning — works but demands careful node-shape and storage choices), or managed Cloud.

## Bottom line
Reach for ScyllaDB when you have a Cassandra- or DynamoDB-shaped workload (high write throughput, simple access patterns, horizontal scale) and you are being hurt by tail latency, JVM GC pauses, or node count/cost — the C++/Seastar shard-per-core design genuinely delivers better p99 and density. Do **not** reach for it if you need joins, OLAP, multi-key ACID transactions, or strong-consistency-by-default; its real consistency story is per-query tunable AP plus single-partition LWT CAS, and **plain writes are not isolated by design**. The single biggest gotchas: (1) the 2025 move to a **source-available license** ended the OSS line, and (2) don't trust "strongly consistent" marketing beyond LWT and Raft-backed metadata — Jepsen documented real split-brain and write-loss bugs (mostly fixed, but the design-level no-isolation property remains).

## Sources
- [Consistency in ScyllaDB — official docs](https://docs.scylladb.com/manual/stable/kb/consistency.html)
- [Lightweight Transactions — official docs](https://docs.scylladb.com/manual/stable/features/lwt.html)
- [Jepsen: Scylla 4.2-rc3](https://jepsen.io/analyses/scylla-4.2-rc3)
- [Jepsen and ScyllaDB — vendor writeup](https://www.scylladb.com/2020/12/23/jepsen-and-scylla-putting-consistency-to-the-test/)
- [Data Distribution with Tablets — official docs](https://docs.scylladb.com/manual/stable/architecture/tablets.html)
- [ScyllaDB 6.0: Tablets & Strongly-Consistent Topology Updates](https://www.scylladb.com/2024/06/12/introducing-scylladb-6-0-with-tablets-and-strongly-consistent-topology-updates/)
- [Announcing ScyllaDB 2025.1 (first source-available release)](https://www.scylladb.com/2025/04/08/announcing-scylladb-2025-1/)
- [Why We're Moving to a Source Available License](https://www.scylladb.com/2024/12/18/why-were-moving-to-a-source-available-license/)
- [The Register: ScyllaDB aims to lower costs after license shift](https://www.theregister.com/2025/06/18/scylladb_license_change/)
