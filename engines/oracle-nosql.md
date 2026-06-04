---
name: Oracle NoSQL
slug: oracle-nosql
rank: 83
data_model: Key-value / document (multi-model)
license: Apache 2.0 (Community Edition client/server); proprietary Oracle Commercial (Enterprise Edition) — see [license-taxonomy](../concepts/license-taxonomy.md)
summary: Oracle's sharded, single-master key-value/JSON store on a Berkeley DB JE engine, with per-operation tunable consistency and durability but no general multi-row transactions.
last_researched: 2026-06-04
confidence: medium
---

# Oracle NoSQL

> A horizontally-sharded, single-master key-value/document store built on Berkeley DB Java Edition, whose headline feature is per-request tunable consistency + durability — and whose biggest limitation is that "transactions" are confined to rows sharing a shard key.

## Identity
- **Taxonomy / data model:** Multi-model on a key-value core. Supports opaque key-value, a tabular model (since v3.0), and schemaless JSON (JSON collection tables). Multi-model in the [oltp-olap-htap](../concepts/oltp-olap-htap.md) sense but fundamentally a KV/document engine. ([Oracle docs — introduction](https://docs.oracle.com/en/database/other-databases/nosql-database/25.3/concepts/introduction.html))
- **Storage model:** Row/record-oriented. Underlying storage engine is **Oracle Berkeley DB Java Edition (JE)**, whose on-disk format is a **log-structured (append-only) B-tree** with cleaner/compaction — relevant for write amplification and p99. See [lsm-vs-btree](../concepts/lsm-vs-btree.md). ([Oracle docs](https://docs.oracle.com/en/database/other-databases/nosql-database/25.3/concepts/introduction.html))
- **Workload:** OLTP — low-latency point reads/writes and short range scans on the shard key. Not an analytics engine; OLAP is offloaded via Hive/Big Data SQL/Hadoop integration, not run in-engine. Not HTAP.

## Distribution & consistency
- **CAP under partition:** Configurable per the **durability/consistency policy you choose**, so it spans CP and AP. With absolute consistency + synchronous (all-replica) durability it behaves CP; with eventual consistency reads from replicas it behaves AP. ([Wikipedia — Oracle NoSQL](https://en.wikipedia.org/wiki/Oracle_NoSQL_Database)) See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Effectively **PA/EL or PC/EC depending on policy** — the per-operation `Consistency` and `Durability` knobs are exactly a PACELC tradeoff dial. Absolute consistency forces master reads (higher latency, stronger); eventual consistency reads replicas (lower latency, possibly stale). ([Oracle durability & consistency functions](https://docs.oracle.com/en/database/other-databases/nosql-database/23.3/c-driver-kv/durability-and-consistency-functions.html))
- **Default isolation & what's achievable:** No begin/end transactions and **no general multi-statement transactions**; "every data modification takes place in a single system-managed transaction." Atomicity/isolation are **not configurable**; only consistency and durability are. ⚠️ unverified — Oracle docs do not name a SQL-standard isolation level (e.g. snapshot/serializable); the guarantee they state is that concurrent transactions "do not interfere" and yield the same result serial or parallel, which describes serializable-style isolation *within a single operation's scope* but should not be read as cross-operation serializability. ([Oracle — transactions in NoSQL](https://docs.oracle.com/en/database/other-databases/nosql-database/25.1/nsdev/transactions-nosql-database.html)) See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **Single-master per shard (replication group).** Writes go to the master and propagate to replicas; durability policy controls whether commit waits for none/simple-majority/all replicas (sync vs async ack). On master failure, surviving nodes hold a **Paxos-based election** to choose a new master. See [replication-models](../concepts/replication-models.md) and [consensus-raft-paxos](../concepts/consensus-raft-paxos.md). ([Oracle docs](https://docs.oracle.com/en/database/other-databases/nosql-database/25.3/concepts/introduction.html))
- **Tunable consistency:** Yes — per-read: **absolute** (read master, freshest), **version-based** (≥ a given version, for read-modify-write), **time-based** (bounded staleness), and **none/eventual** (any replica). ([Oracle consistency](https://docs.oracle.com/en/database/other-databases/nosql-database/18.3/concepts/consistency.html))
- **Clock dependency:** Time-based consistency relies on lag estimates between master and replicas. ⚠️ unverified — exact clock-skew assumptions for time-based consistency not confirmed from primary docs. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs read:** Both. Fixed-schema tables (schema-on-write), JSON collection tables (schema-on-read / schemaless beyond the primary key), and hybrid tables mixing typed columns with JSON. ([SQL for NoSQL intro](https://docs.oracle.com/en/database/other-databases/nosql-database/22.2/sqlfornosql/introduction-sql.html))
- **Migration/evolution:** DDL via SQL for Oracle NoSQL (CREATE/ALTER TABLE, CREATE INDEX). ⚠️ unverified — online vs locking behavior of `ALTER TABLE` and index builds not confirmed from primary docs.
- **Type system:** Typed scalars, records, arrays, maps, JSON, plus **GeoJSON geospatial** functions and a large-object (LOB) streaming API for audio/video. Secondary indexes on non-primary-key fields and on JSON paths. ([Wikipedia](https://en.wikipedia.org/wiki/Oracle_NoSQL_Database))

## Query interface
- **Language:** **SQL for Oracle NoSQL Database** — a SQL-like, Select-From-Where declarative language for **read-only queries plus DDL**. Writes are done through the CRUD driver APIs, not via INSERT/UPDATE in the same general way as a relational SQL engine. ([SQL beginner's guide](https://docs.oracle.com/en/database/other-databases/nosql-database/12.2.4.5/sqlfornosql/sql-queries.html))
- **Transactions:** **Single-operation only.** Atomic multi-row writes/reads are possible **only when rows share the same shard key** (e.g. parent-child rows in a table hierarchy commit together); there is no cross-shard or cross-key-group transaction. ([Oracle transactions](https://docs.oracle.com/en/database/other-databases/nosql-database/25.1/nsdev/transactions-nosql-database.html))
- **Native vs app-side:** Native secondary indexes and aggregation; **joins are limited** — parent-child joins exist on-prem via table hierarchies, but **joins are not available in the Cloud Service** (no child tables). Cross-entity joins are otherwise app-side. ([SQL for NoSQL — query language ref](https://docs.oracle.com/en-us/iaas/nosql-database/doc/query-language-reference.html))
- **Stored procedures / UDFs:** ⚠️ unverified — no general server-side stored-procedure/UDF mechanism found; logic lives in application code.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal. Data is hash-partitioned into **partitions** assigned to **shards (replication groups)**; each Storage Node hosts one or more Replication Nodes per its capacity.
- **Sharding (auto/manual, resharding):** Sharding is automatic over partitions; the store supports **elastic expansion** — add Storage Nodes and run a topology rebalance/redistribute to spread partitions. Resharding is an online admin operation rather than a manual key-range cut. ⚠️ unverified — degree of p99 disruption during redistribution not confirmed.
- **Read replicas:** Each shard's replicas serve reads; **read consistency from replicas depends on the chosen consistency policy** (eventual reads may be stale; absolute forces the master).
- **Storage/compute separation:** No — shared-nothing, storage co-located with compute on Storage Nodes. The managed Cloud Service abstracts capacity (provisioned read/write units + storage) but is not a Snowflake/Aurora-style disaggregated architecture. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Berkeley DB JE writes to an append-only log; durability policy sets the **fsync/ack policy** — `SYNC` (fsync to disk), `WRITE_NO_SYNC` (to OS buffer), or `NO_SYNC`, combined with replica-ack requirement (none / simple majority / all). The **data-loss window on crash is exactly what you trade away**: `NO_SYNC` + no replica ack can lose recent writes; `SYNC` + all-replicas minimizes loss at latency cost. ([Oracle durability functions](https://docs.oracle.com/en/database/other-databases/nosql-database/23.3/c-driver-kv/durability-and-consistency-functions.html)) See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Marketed for low, predictable latency on KV point ops. ⚠️ unverified — no independent published p99 benchmark located; treat vendor latency claims as marketing, not measured fact.
- **Compaction / GC:** Berkeley DB JE runs a **log cleaner** to reclaim space from the append-only log; like any background compaction it can add CPU/IO and affect tail latency. JVM **garbage collection** is an additional p99 factor since the engine is Java. ⚠️ unverified — magnitude of GC/cleaner impact on p99 not confirmed from primary sources.

## Operations & maturity
- **Backup/restore, PITR:** Snapshot-based backup of the store; restore from snapshot. ⚠️ unverified — continuous PITR-style recovery support not confirmed from primary docs.
- **Observability:** Admin CLI, web-based admin console, metrics, and SQL EXPLAIN-style query plans for SQL for NoSQL. ⚠️ unverified — slow-query log specifics not confirmed.
- **Upgrade story:** Rolling upgrades across Storage Nodes are supported. ⚠️ unverified — exact rolling-upgrade constraints/version-skew rules not confirmed.
- **Maturity:** Mature (Berkeley DB JE lineage; GA since ~2011, tabular model v3.0). **No Jepsen report exists** for Oracle NoSQL as of this writing — its distributed-correctness claims have not been independently formally tested, which is notable given the tunable-consistency surface. Known design constraint (not a bug): the lack of general multi-key transactions.

## Ecosystem & people
- **Canonical use cases:** Low-latency profile/session/sensor/lookup data keyed by a natural shard key; JSON document storage where access is by primary/shard key; Oracle shops wanting a KV store that integrates with the broader Oracle stack. **Anti-patterns:** workloads needing cross-entity ACID transactions, ad-hoc multi-table joins, or heavy analytics; teams not already in the Oracle ecosystem (smaller community, more lock-in than open alternatives like [apache-cassandra](apache-cassandra.md), [scylladb](scylladb.md), [mongodb](mongodb.md), or [amazon-dynamodb](amazon-dynamodb.md)).
- **Drivers/connectors:** Java, Python, Node.js, .NET, C, and REST SDKs (client APIs Apache-2.0). Hadoop/Hive/Big Data SQL integration; queryable from Oracle Database via external tables. ⚠️ unverified — first-class Kafka/CDC and dbt connectors not confirmed.
- **Community/support/docs:** Oracle-published docs are thorough; community is small relative to mainstream NoSQL engines. Commercial support via Oracle (EE) and the managed Cloud Service.

## Licensing & cost
- **OSS license & flavor:** **Community Edition** ships under **Apache License 2.0** (permissive) in current releases; client APIs/SDKs are open source under Apache 2.0. Note: older CE releases (≤ ~12.x) were licensed under **AGPL v3**, and the CE relicensed to Apache 2.0 in the ~22.x timeframe — i.e. it moved *toward* a more permissive license, the opposite of the SSPL/BSL trend. **Enterprise Edition** is under a proprietary Oracle Commercial License. Freemium model. ([Oracle NoSQL 22.1 License](https://docs.oracle.com/en/database/other-databases/nosql-database/22.1/license/index.html), [Wikipedia](https://en.wikipedia.org/wiki/Oracle_NoSQL_Database)) See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Both — self-managed CE/EE on-prem, or **Oracle NoSQL Database Cloud Service** (managed, auto-scaling, provisioned read/write units + storage, hourly billing).
- **Lock-in:** Cloud Service capacity-unit model and Oracle-ecosystem integration create vendor lock-in; the SQL-for-NoSQL dialect and table-hierarchy model are non-portable.
- **Cost model:** Self-managed = your hardware (per-node). Cloud Service = **per provisioned read/write throughput units + per-GB storage**, billed hourly; throughput-provisioned cost can invert against cheaper self-managed at steady high scale.

## Hardware / deployment
- **Resource profile:** Memory-sensitive (JVM heap + JE cache); best when the **B-tree internal nodes / hot working set fit in the JE cache**, though full dataset need not fit in RAM. CPU cost from JVM GC.
- **Storage assumptions:** Local disk per Storage Node; benefits from NVMe for the append-only log. Shared-nothing, so it does not assume network-attached storage.
- **Footprint:** Clustered (multi-Storage-Node) for production; can run single-node for dev. Also offered serverless-ish as the Cloud Service. Not an embedded engine (though it sits *on* the embeddable Berkeley DB JE).
- **Deployment:** On-prem self-managed or Oracle Cloud SaaS. ⚠️ unverified — Kubernetes/StatefulSet operator maturity not confirmed.

## Bottom line
Reach for Oracle NoSQL if you are already an Oracle shop and need a horizontally-scalable KV/JSON store with **fine-grained, per-request control over the consistency/durability/latency tradeoff** ([cap-pacelc](../concepts/cap-pacelc.md)) and your access is shard-key-centric. Avoid it if you need general multi-key/cross-shard transactions, ad-hoc joins, or analytics — or if you want a large open community and portability, where [apache-cassandra](apache-cassandra.md), [scylladb](scylladb.md), [mongodb](mongodb.md), or [amazon-dynamodb](amazon-dynamodb.md) are stronger. The single biggest gotcha: **"transactions" only span rows sharing a shard key** — there is no begin/end and no cross-shard atomicity, so model your data hierarchy around that constraint up front.

## Sources
- [Oracle NoSQL Database — Introduction (Concepts, 25.3)](https://docs.oracle.com/en/database/other-databases/nosql-database/25.3/concepts/introduction.html)
- [Oracle NoSQL — Transactions in NoSQL Database (25.1)](https://docs.oracle.com/en/database/other-databases/nosql-database/25.1/nsdev/transactions-nosql-database.html)
- [Oracle NoSQL — Consistency (18.3 concepts)](https://docs.oracle.com/en/database/other-databases/nosql-database/18.3/concepts/consistency.html)
- [Oracle NoSQL — Durability and Consistency Functions (23.3 C driver)](https://docs.oracle.com/en/database/other-databases/nosql-database/23.3/c-driver-kv/durability-and-consistency-functions.html)
- [Introduction to SQL for Oracle NoSQL Database (22.2)](https://docs.oracle.com/en/database/other-databases/nosql-database/22.2/sqlfornosql/introduction-sql.html)
- [Getting Started with SQL for Oracle NoSQL Database (12.2.4.5)](https://docs.oracle.com/en/database/other-databases/nosql-database/12.2.4.5/sqlfornosql/sql-queries.html)
- [Oracle NoSQL Database Cloud Service — Query Language Reference](https://docs.oracle.com/en-us/iaas/nosql-database/doc/query-language-reference.html)
- [Wikipedia — Oracle NoSQL Database](https://en.wikipedia.org/wiki/Oracle_NoSQL_Database)
- [oracle/nosql on GitHub](https://github.com/oracle/nosql)
