---
name: Apache Cassandra
slug: apache-cassandra
rank: 10
data_model: Wide-column
license: Apache License 2.0 (permissive)
summary: Leaderless, masterless wide-column store built for write-heavy, multi-DC workloads with tunable consistency; pay for that scale-out with weak transactions and heavy data-modeling discipline.
last_researched: 2026-06-04
confidence: high
---

# Apache Cassandra

> A masterless, AP-leaning wide-column store ([replication-models](../concepts/replication-models.md) leaderless quorum) optimized for high write throughput and multi-region availability — at the cost of joins, ad-hoc queries, and strong transactions.

## Identity
- **Taxonomy / data model:** Wide-column (partitioned row store, "Bigtable-style" + Dynamo distribution). Data lives in tables keyed by a partition key + clustering columns; columns are sparse and per-row. Modeled query-first, not relationship-first. See [wide-column](../concepts/wide-column.md).
- **Storage model:** [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM-tree. Writes hit a commit log + in-memory memtable, flushed to immutable SSTables; reads merge SSTables + memtable. 5.0 adds trie-based memtables/SSTable index format (BTI) for lower memory and faster reads. Write-optimized; reads pay a merge/compaction cost.
- **Workload:** OLTP-style at scale, but better described as high-volume operational key/partition lookups, not relational OLTP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). **Not HTAP** — no native analytics engine; OLAP is done by bolting on Spark (DataStax/Apache Spark connector) reading the SSTables. Wrong tool for ad-hoc analytical queries.

## Distribution & consistency
- **CAP under partition:** AP by design (Dynamo lineage) — stays available and reconciles via [replication-models](../concepts/replication-models.md) hinted handoff, read repair, and anti-entropy repair. You can *configure toward* CP per query by raising consistency levels, but the base model is availability-first. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PA/EL — under Partition favors Availability; Else favors Latency over Consistency (the default tunables let stale/divergent reads through). Raising CL trades that latency back for consistency.
- **Default isolation & what's achievable:** No multi-row/multi-partition ACID transactions in the classic engine. Single-row writes are atomic and isolated; `BATCH` gives atomicity (all-or-nothing) but **not isolation** across partitions. "Lightweight transactions" (LWT, `IF`/`IF NOT EXISTS`) provide compare-and-set linearizable on a single partition via Paxos. ⚠️ Marketing/docs framing of LWT as "linearizable" diverged sharply from reality: Jepsen found the original LWT a "broken implementation of Paxos" that could drop 1–5% of acknowledged writes *without a partition* ([Jepsen: Cassandra](https://aphyr.com/posts/294-jepsen-cassandra)); a later linearizability violation on list append/prepend was filed as [CASSANDRA-16368](https://issues.apache.org/jira/browse/CASSANDRA-16368). Paxos v2 (4.1) addressed performance/correctness gaps but LWT remains single-partition and expensive. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Leaderless, fully masterless. Every replica is equal; coordinator node fans writes to N replicas. Quorum tunable per query: `ONE`, `QUORUM`, `LOCAL_QUORUM`, `EACH_QUORUM`, `ALL`, etc. R+W>N yields strong-ish consistency on a partition. No failover/split-brain election because there is no leader — any reachable replica serves traffic. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes — this is the headline feature; consistency level is set per statement, independently for reads and writes.
- **Clock dependency:** ⚠️ Real correctness hazard. Last-write-wins conflict resolution uses cell timestamps, by default the coordinator's wall clock. Clock skew can cause a logically newer write to be silently discarded; LWT list ops bug above stemmed from node-local timestamps. NTP discipline is operationally mandatory. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Tables and column types are defined up front (CQL `CREATE TABLE`); rigid in that the partition/clustering key choice locks your access patterns. Schema changes propagate via gossip — historically a source of "schema disagreement" if applied concurrently.
- **Migration/evolution:** `ALTER TABLE` add/drop column is cheap (metadata only, no table rewrite — SSTables are immutable). You generally cannot change primary key or repartition without creating a new table and migrating. Resharding ≈ rebuild.
- **Type system:** Scalars, collections (list/set/map), UDTs, counters, `time`/`timestamp`/`date`, `inet`, `blob`. **5.0 adds a native `vector<float, n>` type** for ANN/embedding workloads. No native geospatial. JSON is supported as an I/O convenience over typed columns, not a native document type.

## Query interface
- **Language:** CQL (Cassandra Query Language) — SQL-*looking* DSL but deliberately restricted: no joins, no subqueries, no arbitrary `WHERE` (must hit partition key, or use `ALLOW FILTERING` which scans and is an anti-pattern). Not SQL-standard.
- **Transactions:** Single-row atomic; `BATCH` = atomic-not-isolated; LWT = single-partition CAS via Paxos. No general multi-partition ACID in shipped releases. **CEP-15 "Accord"** (leaderless, Reorder-Buffer/EPaxos-style protocol) aims to add globally strict-serializable general transactions ([CEP-15](https://cwiki.apache.org/confluence/display/CASSANDRA/CEP-15:+General+Purpose+Transactions)); ⚠️ unverified exact ship date — as of June 2026 it is targeted for the 6.0 line, depends on the [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)-adjacent Cluster Metadata Service (CEP-21/CMS), and is not yet in a GA release.
- **Native vs app-side:** No joins/aggregations across partitions natively. Secondary indexes: legacy 2i and SASI are largely superseded by **Storage-Attached Indexing (SAI)** in 5.0 (recommended; indexes memtables+SSTables, lower storage overhead) ([Cassandra docs: SAI](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/indexing/sai/sai-concepts.html)). Even with SAI, fan-out queries across all partitions are costly — denormalize instead.
- **Stored procedures / UDFs:** UDFs/UDAs in Java (and historically JavaScript/scripting, since restricted/deprecated for security). No stored procedures in the relational sense.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal is the whole point — linear-ish scale-out by adding nodes. Data auto-distributed by consistent hashing over a token ring (virtual nodes / vnodes by default).
- **Sharding:** Automatic via partition-key hashing; no manual shard placement. Resharding is implicit (token reassignment on node add/remove with streaming). Pain points: hot partitions from bad key choice, and large-partition tombstone problems.
- **Read replicas / consistency:** No primary/replica distinction; all replicas are read+write. Read consistency is whatever CL you request; `LOCAL_QUORUM` is the multi-DC default for bounded latency.
- **Storage/compute separation:** No — classic Cassandra co-locates compute and local storage (shared-nothing). Separation is a hosted/fork concern, not native. See [storage-compute-separation](../concepts/storage-compute-separation.md). Multi-DC replication (NetworkTopologyStrategy) is first-class and a core strength.

## Performance & durability
- **Write path:** Append to commit log (durability) + memtable; ack per CL. `commitlog_sync` is `periodic` by default (fsync every ~10s) → **data-loss window of up to that interval on crash**; `batch`/`group` sync trade latency for durability. See [wal-and-durability](../concepts/wal-and-durability.md). Writes are very fast (no read-before-write except LWT/counters).
- **Throughput/latency:** Excellent write throughput and predictable low-latency point reads on well-modeled partitions. **p99 tail is the classic weakness:** dominated by compaction, repair, GC pauses (JVM), and tombstone scans. Read-heavy or wide-scan workloads expose this.
- **Compaction / GC:** LSM compaction (STCS / LCS / TWCS / 5.0 unified UCS) reclaims space and merges SSTables; competes with live traffic for IO and inflates p99. **Tombstones** (deletes/TTL expiry) are a notorious operational footgun — large tombstone counts make reads slow or fail until `gc_grace_seconds` passes and compaction purges them. JVM heap tuning matters.

## Operations & maturity
- **Backup/restore:** `nodetool snapshot` (hard-links immutable SSTables), incremental backups, plus restore tooling (e.g. Medusa). No built-in cluster-wide PITR; point-in-time is approximated via snapshots + commitlog archiving.
- **Observability:** Rich JMX/metrics (Prometheus exporters), `nodetool` (status, tpstats, compactionstats, tablestats), `EXPLAIN`/tracing via `TRACING ON`, slow-query logging. Day-2 burden is real: repair scheduling (Reaper), compaction tuning, tombstone watch.
- **Upgrade story:** Rolling, node-by-node, no downtime — a genuine strength. Constraint: cannot run repairs/streaming across mixed major versions; finish the rollout promptly. SSTable format upgrades may need `upgradesstables`.
- **Maturity:** Very mature (Facebook origin 2008, top-tier ASF project, runs at Apple/Netflix/Instagram scale). Known failure modes: tombstone overload, hot/large partitions, clock-skew LWW data loss, GC pauses, repair-induced load. **Jepsen:** the foundational [aphyr Jepsen analysis](https://aphyr.com/posts/294-jepsen-cassandra) found LWT/Paxos correctness bugs; many were since fixed (Paxos v2), but the lesson stands — use LWT sparingly and don't trust pre-fix versions for linearizable claims.

## Ecosystem & people
- **Canonical use cases:** Write-heavy time-series/event/IoT data, messaging/feeds, user activity, sensor data, multi-region always-on systems where you can model around known query patterns. **Anti-patterns:** ad-hoc analytics, relational/joined data, strong cross-entity transactions, small datasets that fit one box (overkill), queue-like workloads with high delete/tombstone churn, anything needing flexible unplanned queries.
- **Drivers / connectors:** First-party DataStax drivers (Java, Python, Go, Node, C#, etc.); CDC available (commit-log based, somewhat coarse); Kafka connectors; Spark connector for batch/analytics; dbt via community adapters. BI tools generally need an intermediary.
- **Community/support:** Large community; commercial support and managed offerings from DataStax (Astra DB), Instaclustr/NetApp, Amazon (Keyspaces is API-compatible), Aiven. Docs are good but data modeling has a **steep learning curve** — the failure mode is engineers treating it like SQL.

## Licensing & cost
- **OSS license:** Apache License 2.0 — permissive, no post-2018 relicensing drama (contrast Elastic/MongoDB/Redis). Genuinely open. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Both. Self-host the OSS freely; or managed (Astra serverless, Keyspaces per-request, Instaclustr per-node). Lock-in risk is low for core CQL, higher if you adopt vendor-proprietary serverless semantics.
- **Cost model:** Self-managed = per-node hardware/ops (and the ops cost is non-trivial). Managed varies: per-node (Instaclustr), per-request + storage serverless (Astra, Keyspaces). At scale, cheap horizontally but the operational headcount is the real cost.

## Hardware / deployment
- **Resource profile:** Disk-IO + CPU bound on compaction/repair; memory matters for memtables, key/row cache, and JVM heap (GC tuning critical). Working set need not fit in RAM, but read latency degrades when it doesn't.
- **Storage assumptions:** Local SSD/NVMe strongly preferred; LSM compaction is IO-hungry. Network-attached storage works but adds tail latency and is discouraged for hot data.
- **Footprint:** Clustered, shared-nothing; minimum sensible deployment is a multi-node ring (single node defeats the purpose). Not embedded, not serverless natively (serverless is a hosted abstraction).
- **Deployment:** On-prem or any cloud; k8s via K8ssandra / Cass Operator with StatefulSets + persistent local volumes. StatefulSet realities (stable identity, ordered scaling, PV pinning) apply.

## Bottom line
Reach for Cassandra when you have known, write-heavy access patterns at large scale across multiple regions and need always-on availability — and you have the team to model data query-first and operate compaction/repair. Do **not** reach for it for ad-hoc queries, joins, strong multi-row transactions, small datasets, or as a drop-in SQL database. The single biggest gotcha: it is masterless and tunable, but consistency and durability are *your* configuration responsibility — wrong consistency levels, clock skew, tombstone buildup, or treating it like SQL will silently bite you. (For a same-API, C++ alternative claiming lower tail latency, see [scylladb](scylladb.md).)

## Sources
- [Apache Cassandra documentation — Guarantees](https://cassandra.apache.org/doc/stable/cassandra/architecture/guarantees.html)
- [Apache Cassandra 5.0 announcement](https://cassandra.apache.org/_/blog/Apache-Cassandra-5.0-Announcement.html)
- [Cassandra docs — Storage-Attached Indexing (SAI)](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/indexing/sai/sai-concepts.html)
- [Cassandra docs — Vector Search](https://cassandra.apache.org/doc/latest/cassandra/vector-search/concepts.html)
- [Jepsen: Cassandra (aphyr)](https://aphyr.com/posts/294-jepsen-cassandra)
- [CASSANDRA-16368 — LWT linearizability violation on list ops](https://issues.apache.org/jira/browse/CASSANDRA-16368)
- [CEP-15: General Purpose Transactions (Accord)](https://cwiki.apache.org/confluence/display/CASSANDRA/CEP-15:+General+Purpose+Transactions)
- [endoflife.date — Apache Cassandra versions](https://endoflife.date/apache-cassandra)
