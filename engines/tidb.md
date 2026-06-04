---
name: TiDB
slug: tidb
rank: 73
data_model: Relational (distributed NewSQL / HTAP)
license: Apache 2.0 (permissive); managed via TiDB Cloud
summary: MySQL-wire-compatible distributed SQL DB with Raft-replicated KV storage and a columnar HTAP replica; horizontal scale and snapshot isolation, at distributed-2PC latency.
last_researched: 2026-06-04
confidence: high
---

# TiDB

> MySQL-protocol-compatible distributed SQL engine (PingCAP) that decouples a stateless SQL layer from Raft-replicated row storage (TiKV) and an asynchronous columnar replica (TiFlash), giving horizontal scale + Snapshot Isolation for OLTP and real-time analytics in one cluster — at the cost of distributed-transaction latency.

## When to use

**Use TiDB if:**
- ✅ You have a large MySQL-shaped OLTP workload that outgrew a single node and want automatic horizontal sharding without app-level sharding
- ✅ You want genuine HTAP — fresh analytics on transactional data (columnar TiFlash) without an ETL-to-warehouse pipeline
- ✅ You value MySQL wire-protocol compatibility (drop-in for many apps), online DDL, and Apache 2.0 / no-lock-in OSS
- ✅ You need horizontal scale with automatic Region rebalancing and Raft-based HA

**Avoid TiDB if:**
- ❌ You have small/single-node workloads — multi-component cluster overhead and per-txn TSO + 2PC latency aren't worth it (use MySQL/PostgreSQL)
- ❌ You need ultra-low-latency single-row OLTP (the TSO round-trip + distributed 2PC tax is real)
- ❌ You need true SERIALIZABLE isolation — the default "Repeatable Read" is really Snapshot Isolation, so write skew is possible
- ❌ You rely on MySQL stored procedures/triggers/foreign keys, or you'd re-enable transaction auto-retry (the Jepsen finding means doing so silently loses SI)

## Identity
- **Taxonomy / data model:** Relational (NewSQL); MySQL-compatible SQL. Multi-model-ish via native vector search type for AI workloads. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Hybrid via two engines. **TiKV** = row-oriented distributed KV store built on RocksDB ([lsm-vs-btree](../concepts/lsm-vs-btree.md) — LSM under the hood); **TiFlash** = columnar store ([columnar-storage](../concepts/columnar-storage.md)) kept in sync as a Raft *learner* replica. Data is range-partitioned into "Regions" (default 256 MiB from v8.4.0; 96 MiB before) ([TiDB Region tuning docs](https://docs.pingcap.com/tidb/stable/tune-region-performance/)).
- **Workload:** Genuine **HTAP** with *physical* separation — OLAP queries route to columnar TiFlash replicas, OLTP to row-based TiKV, so analytics does not contend with transactional storage. TiFlash is replicated via Multi-Raft Learner protocol so it does not block TiKV writes and offers the same read consistency ([TiFlash overview](https://docs.pingcap.com/tidb/stable/tiflash-overview/)). This is one of the cleaner HTAP separation stories. Design paper: [TiDB: A Raft-based HTAP Database, VLDB 2020](https://vldb.org/pvldb/vol13/p3072-huang.pdf).

## Distribution & consistency
- **CAP under partition:** **CP**. Each Region is a Raft group; loss of quorum makes that Region unavailable for writes rather than diverging. See [cap-pacelc](../concepts/cap-pacelc.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **PACELC:** PC/EC — under partition it favors consistency (CP); else it still pays cross-node latency for strong consistency (timestamp fetch from PD + 2PC). See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation:** **Snapshot Isolation**, exposed under the MySQL name "Repeatable Read" for compatibility ([Jepsen: TiDB 2.1.7](https://jepsen.io/analyses/tidb-2.1.7)). It does **not** provide MySQL-style repeatable read semantics; the "RR" label is a compatibility alias. SI prevents lost updates within a transaction but is **not serializable** (write-skew is possible). A **Read Committed** level is also available (since v4.0, effective only in pessimistic-transaction mode); **SERIALIZABLE is not offered** ([TiDB isolation-levels docs](https://docs.pingcap.com/tidb/stable/transaction-isolation-levels/)). See [isolation-levels](../concepts/isolation-levels.md).
- **Jepsen:** Tested by Kyle Kingsbury. Early versions (2.1.7–3.0.0-beta) **violated snapshot isolation by default** — two auto-retry mechanisms (`tidb_disable_txn_auto_retry`, `tidb_retry_limit`) blindly re-applied conflicting writes, yielding read skew, lost updates, and behavior "weaker than read committed." With retries disabled, **2.1.8 through 3.0.0-rc.2 passed SI and single-key linearizability**; 3.0.0-rc.2 disabled the retry mechanisms by default ([Jepsen report](https://jepsen.io/analyses/tidb-2.1.7); [PingCAP summary](https://www.pingcap.com/blog/tidb-passes-jepsen-test-for-snapshot-isolation-and-single-key-linearizability/)). The lesson — *do not re-enable transaction auto-retry* — still applies.
- **Replication:** Single-leader **per Region** via Raft (typically 3 replicas); writes commit on majority. Failover is automatic via Raft leader election; no split-brain because a minority partition cannot elect a leader. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited. Reads default to leader/strongly-consistent; stale/follower reads available for latency. Not Dynamo-style per-query quorum levels.
- **Clock dependency:** Correctness rests on a centralized **Timestamp Oracle (TSO)** in the Placement Driver (PD), handing out strictly monotonic global timestamps for the Percolator MVCC protocol — *not* on synchronized wall clocks (unlike Spanner TrueTime). The TSO is a logical-clock single source of truth (HA via Raft within PD). See [clocks-and-time](../concepts/clocks-and-time.md), [mvcc](../concepts/mvcc.md). ([TSO docs](https://docs.pingcap.com/tidbcloud/tso/))

## Schema
- **Schema-on-write**, rigid relational schema (MySQL-like).
- **Migration:** Fully **online DDL** — schema changes (including most `ALTER`/add-index) run without long table locks, using an asynchronous multi-state schema-change protocol. A notable operational advantage over single-node MySQL where some DDL locks.
- **Type system:** MySQL types + native **VECTOR** type and ANN vector indexes for AI/embedding workloads ([vector-search-ann](../concepts/vector-search-ann.md)); JSON; generated columns. Geospatial support is limited vs PostGIS.

## Query interface
- **Language:** SQL, **MySQL 5.7/8.0 wire-protocol and dialect compatible** (drop-in for many MySQL apps; some incompatibilities exist — e.g. no foreign-key enforcement historically, now experimental/supported in recent versions).
- **Transactions:** Full **multi-statement ACID** distributed transactions via Google **Percolator**-style 2PC. Two modes: **pessimistic** (default since v3.0.8, MySQL-like locking) and **optimistic** (write-write conflicts detected only at commit — fails under heavy contention) ([optimistic txn docs](https://docs.pingcap.com/tidb/stable/optimistic-transaction/), [pessimistic txn docs](https://docs.pingcap.com/tidb/stable/pessimistic-transaction/)).
- **Native vs app-side:** Native distributed joins, aggregations, window functions, secondary indexes; analytical queries can be pushed to TiFlash and use the MPP engine.
- **Stored procedures / UDFs:** Limited — historically TiDB did **not** support stored procedures/triggers/events the way MySQL does; check version. ⚠️ unverified — exact current SP/trigger coverage varies by release; treat MySQL stored-procedure parity as incomplete.

## Scaling & topology
- **Horizontal**, designed for it. Add TiDB (SQL/compute), TiKV (storage), or TiFlash nodes independently.
- **Sharding:** **Automatic** range-based via Regions; PD splits/merges and rebalances Regions across TiKV nodes by load — no manual shard keys, no application-level sharding, no painful resharding ([native sharding overview](https://www.mydbops.com/blog/tidb-native-sharding)). This is TiDB's headline value vs sharded MySQL.
- **Read replicas:** Reads served from Raft leaders by default (consistent); follower-read and stale-read modes trade freshness for latency. TiFlash columnar replicas serve analytics consistently (validated via Raft index + MVCC).
- **Storage/compute separation:** Yes — stateless SQL layer is separate from TiKV/TiFlash storage; TiDB Cloud Serverless takes this further with on-demand, scale-to-zero compute and object-storage-backed durability. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** TiKV writes go through RocksDB WAL + Raft log replicated to a majority before commit ([wal-and-durability](../concepts/wal-and-durability.md)). Committed = durable on a quorum; crash data-loss window is bounded by Raft majority durability (no acknowledged-then-lost write under correct config). Distributed 2PC (prewrite + commit) adds latency per write transaction.
- **Throughput/latency:** Scales out linearly for many workloads; **single-transaction latency is higher than a single-node DB** due to TSO round-trip + cross-node 2PC + Raft. p99 is sensitive to PD/TSO health and to RocksDB **compaction** stalls and hot Regions ("hotspots") on monotonic keys.
- **Compaction / GC:** LSM compaction in RocksDB (TiKV) affects write p99; MVCC garbage collection periodically reclaims old versions — GC lag or large transactions can bloat storage and hurt scan latency.

## Operations & maturity
- **Backup/restore:** **BR** (Backup & Restore) does full snapshot backups at a timepoint plus continuous log backup, enabling **PITR**; restore into a new cluster on total failure ([BR FAQ](https://docs.pingcap.com/tidb/stable/backup-and-restore-faq/)).
- **Observability:** Prometheus/Grafana metrics, `EXPLAIN`/`EXPLAIN ANALYZE` query plans, slow-query log, TiDB Dashboard (key visualizer for hotspots).
- **Upgrade:** Rolling upgrades supported (managed by TiUP / TiDB Operator on k8s) with minimal downtime. **Day-2 burden is real** — many moving parts (TiDB, TiKV, PD, TiFlash, TiCDC), capacity planning, hotspot tuning; non-trivial ops without TiDB Cloud.
- **Maturity:** Mature, production-proven at large scale (notably in China; PingCAP). **Jepsen-tested** (see Distribution); known failure modes are write hotspots, optimistic-txn conflict storms, and the historical auto-retry SI violation.
- **Ecosystem connectors:** **TiCDC** for change data capture (Kafka, MySQL, downstream sinks); MySQL drivers/ORMs work directly; dbt and BI tools via MySQL connectors.

## Ecosystem & people
- **Canonical use cases:** Sharded-MySQL replacement that outgrew a single node; large OLTP needing horizontal scale without app-level sharding; HTAP where you want fresh analytics on transactional data without an ETL pipeline to a separate warehouse; increasingly, AI/agent memory with vector search.
- **Anti-patterns:** Single-node or small workloads (operational overhead and per-txn latency aren't worth it — use MySQL/PostgreSQL); ultra-low-latency single-row OLTP where 2PC/TSO round-trips hurt; workloads needing true **serializable** isolation (TiDB tops out at SI — write skew possible); heavy reliance on MySQL stored procedures/triggers/foreign keys; pure OLAP at petabyte scale (a dedicated columnar warehouse like ClickHouse/Snowflake may fit better).
- **Community & support:** Large open-source community, CNCF-adjacent ecosystem (TiKV is a graduated CNCF project), commercial support and managed service from PingCAP. Docs are extensive and good. Learning curve: SQL is familiar (MySQL), but the distributed operational model is not.

## Licensing & cost
- **OSS license:** **Apache 2.0** — permissive, no post-2018 relicensing ([license-taxonomy](../concepts/license-taxonomy.md)). TiKV is a separate CNCF project (also Apache 2.0). No SSPL/BSL trap. Self-hosting is fully viable.
- **Self-managed vs managed:** Both. Self-managed via TiUP / TiDB Operator (k8s). **TiDB Cloud** offers *Serverless/Starter* (on-demand compute+storage, scale-to-zero, free tier ~25 GiB row + 25 GiB column + 250M Request Units/mo) and *Dedicated* (node-based pricing) ([pricing](https://www.pingcap.com/pricing/)).
- **Lock-in:** Low for the OSS engine (MySQL-compatible, Apache-licensed). TiDB Cloud adds the usual managed-service lock-in (Request Unit billing, autoscaling features).
- **Cost model:** Self-hosted = node/hardware cost. Cloud Dedicated = per-instance + provisioned storage + backup + transfer; Serverless = consumption (Request Units + storage). RU-based serverless can be cheap at small scale and harder to predict at large scale.

## Hardware / deployment
- **Resource profile:** Distributed and resource-hungry — TiKV is disk- and memory-intensive (RocksDB block cache), TiDB compute is CPU-bound, TiFlash wants memory + columnar storage. Working set need not fit in RAM, but RAM strongly affects p99.
- **Storage assumptions:** **NVMe/local SSD strongly recommended** for TiKV; sensitive to disk latency under compaction. Network-attached storage degrades performance.
- **Footprint:** **Clustered, multi-component** (TiDB + TiKV + PD minimum; TiFlash/TiCDC optional) — minimum sensible deployment is several nodes. Not embedded; serverless option exists via TiDB Cloud.
- **Deployment:** SaaS (TiDB Cloud on AWS/GCP/Azure/Alibaba, 30+ regions) or on-prem/self-managed; strong **Kubernetes** support via TiDB Operator (StatefulSets for TiKV/PD).

## Bottom line
Reach for TiDB when you have a large MySQL-shaped OLTP workload that has outgrown a single node and you want **automatic horizontal sharding plus fresh analytics in one system** without building app-level sharding or an ETL-to-warehouse pipeline — and you can afford a multi-component distributed cluster. Don't reach for it for small/single-node apps, ultra-low-latency single-row OLTP (the TSO + 2PC tax is real), or anything needing true serializable isolation. **Biggest gotcha:** the default "Repeatable Read" is really **Snapshot Isolation** (write skew possible), and the historical Jepsen finding means you must *never* re-enable transaction auto-retry, or you silently lose SI guarantees.

## Sources
- [TiDB: A Raft-based HTAP Database (VLDB 2020)](https://vldb.org/pvldb/vol13/p3072-huang.pdf)
- [Jepsen: TiDB 2.1.7](https://jepsen.io/analyses/tidb-2.1.7)
- [PingCAP: TiDB Passes Jepsen for Snapshot Isolation & Single-Key Linearizability](https://www.pingcap.com/blog/tidb-passes-jepsen-test-for-snapshot-isolation-and-single-key-linearizability/)
- [TiDB Architecture docs](https://docs.pingcap.com/tidb/stable/tidb-architecture/)
- [TiFlash Overview](https://docs.pingcap.com/tidb/stable/tiflash-overview/)
- [Optimistic transaction model](https://docs.pingcap.com/tidb/stable/optimistic-transaction/)
- [Pessimistic transaction mode](https://docs.pingcap.com/tidb/stable/pessimistic-transaction/)
- [Timestamp Oracle (TSO) docs](https://docs.pingcap.com/tidbcloud/tso/)
- [Backup & Restore FAQ](https://docs.pingcap.com/tidb/stable/backup-and-restore-faq/)
- [TiDB Cloud pricing](https://www.pingcap.com/pricing/)
