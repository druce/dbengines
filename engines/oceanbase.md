---
name: OceanBase
slug: oceanbase
rank: 109
data_model: Relational (distributed)
license: Mulan Public License v2 (MulanPubL-2.0, copyleft; NOT OSI-approved) — open-core; enterprise edition proprietary
summary: Alibaba/Ant-built distributed SQL DB, Paxos-replicated and MySQL/Oracle-compatible, engineered for financial-grade OLTP at extreme scale.
last_researched: 2026-06-04
confidence: medium
---

# OceanBase

> A shared-nothing distributed relational database from Ant Group, using Multi-Paxos for strongly-consistent replication and MySQL/Oracle wire-compatibility, built for high-volume financial OLTP (with HTAP ambitions) on commodity hardware.

## When to use

**Use OceanBase if:**
- ✅ You need MySQL/Oracle-compatible SQL with strong Paxos consistency and true horizontal scale-out for heavy financial-grade OLTP
- ✅ You are migrating MySQL/Oracle and want scale-out without an app rewrite (wire + PL/SQL compatibility)
- ✅ You have the operational muscle to run a multi-zone (3-zone, 3-replica) distributed database
- ✅ High compression on commodity hardware and distributed transactions (2PC over Paxos) justify the complexity at scale

**Avoid OceanBase if:**
- ❌ Your workload is single-node or small — operational overhead dwarfs a plain MySQL/Postgres
- ❌ You need pure ad-hoc analytics/data-warehouse ([clickhouse](clickhouse.md) or [snowflake](snowflake.md) fit better)
- ❌ You rely on "financial-grade" claims without your own testing — there is **no public Jepsen/independent verification**
- ❌ Your team lacks distributed-DB depth, or you can't tune LSM major compaction to protect p99

## Identity
- **Taxonomy / data model:** Distributed relational (SQL). Multi-tenant: each tenant runs in MySQL-compatible **or** Oracle-compatible mode (PL/SQL, Oracle types). ([architecture](https://oceanbase.github.io/oceanbase/architecture/), [dbdb.io](https://dbdb.io/db/oceanbase))
- **Storage model:** Row-store on an **[LSM-tree](../concepts/lsm-vs-btree.md)** engine — in-memory MemTable flushed to on-disk SSTables; baseline (static) + incremental (dynamic) data merged at compaction. Macro blocks (2MB write unit) / micro blocks (16KB read unit), block + row caches. Columnar storage was added (v4.3) for analytics. High compression is a headline claim (vendor cites 70–90% storage reduction vs MySQL — ⚠️ unverified — vendor figure, workload-dependent). ([dbdb.io](https://dbdb.io/db/oceanbase))
- **Workload:** OLTP-first; markets itself as **HTAP**. Physical separation: AP queries read from the same Paxos-replicated dataset, optionally served by **follower replicas** and a **columnar replica/index** (v4.3+) rather than a separate cluster — so it is "one engine" HTAP, not a separate analytics store. ([blog: integrated architecture](https://en.oceanbase.com/blog/13167971328)) See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** — uses [Multi-Paxos](../concepts/consensus-raft-paxos.md) per partition group; a partition that loses its quorum stops serving writes rather than diverging. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EC** — favors consistency under partition; in normal operation a write must reach a Paxos majority before commit (latency cost), and reads go to the leader (or a snapshot) for strong consistency. ([architecture](https://oceanbase.github.io/oceanbase/architecture/))
- **Default isolation & what's achievable:** Default **Read Committed**. **Snapshot Isolation** since v2.0; **Serializable** since v2.2. ([dbdb.io](https://dbdb.io/db/oceanbase)) Concurrency via [MVCC](../concepts/mvcc.md). ⚠️ unverified — whether "Serializable" is true serializability vs. an SI-based variant under all distributed configurations is not confirmed from a primary source here. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **Single-leader per partition** with Paxos log replication to followers; default **3 replicas across 3 zones**, synchronous via Paxos (majority-ack), not async/semi-sync. Automatic leader election and failover on node loss. ([architecture](https://oceanbase.github.io/oceanbase/architecture/)) See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Reads can be **strong** (leader) or **weak/bounded-stale** (follower) per query/session — a tunable read-consistency knob, not Dynamo-style write quorums.
- **Clock dependency:** Uses a **Global Timestamp Service (GTS)** — a monotonically increasing timestamp from a highly-available timestamp Paxos group, not synchronized wall clocks (contrast Spanner's TrueTime). Correctness does **not** rest on bounded clock skew. ([blog: transaction engine](https://en.oceanbase.com/blog/2615446272)) See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** Schema-on-write, rigid relational schema; foreign keys supported.
- **Migration / DDL:** Supports online DDL (vendor claim of non-blocking schema change for many operations); ⚠️ unverified — exact set of operations that avoid table locks not confirmed from primary docs here.
- **Type system:** Standard SQL types, JSON, and (v4.3+) **vector** data type for ANN/[vector search](../concepts/vector-search-ann.md). Oracle-mode adds Oracle-compatible types and PL/SQL.

## Query interface
- **Language:** SQL. High MySQL 5.7/8.0 protocol + syntax compatibility (drivers often work unchanged); separate Oracle-compatibility mode with PL/SQL. ([architecture](https://oceanbase.github.io/oceanbase/architecture/))
- **Transactions:** Full **multi-statement ACID**, including distributed transactions across partitions/nodes via **two-phase commit layered over Paxos** (each 2PC participant is itself Paxos-replicated, so participant failure is masked by re-election). ([blog: transaction engine](https://en.oceanbase.com/blog/2615446272))
- **Native vs app-side:** Native secondary indexes (global and local/partitioned), joins, aggregations, window functions; distributed/parallel query execution.
- **Stored procedures / UDFs:** PL/SQL (Oracle mode) and MySQL-style stored procedures.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal scale-out, shared-nothing. Demonstrated at **1,557 nodes / 3 zones** in the record TPC-C run. ([VLDB paper](https://vldb.org/pvldb/vol15/p3385-xu.pdf))
- **Sharding / partitioning:** Table partitioning (hash/range/list); partitions are the unit of Paxos replication and load balancing. Rebalancing of partition leaders is automatic; resharding pain is reduced vs. manual-shard systems but still a design-time concern.
- **Read replicas & read consistency:** Follower replicas can serve **weak/bounded-stale** reads; leader serves strong reads. Read-only (non-voting) replicas available for scaling reads/analytics.
- **Storage/compute separation:** Core architecture couples storage + compute per node, but OceanBase Cloud / v4.x offers shared-storage and object-storage tiers; see [storage-compute-separation](../concepts/storage-compute-separation.md). ⚠️ unverified — degree of true storage/compute disaggregation in OSS edition.

## Performance & durability
- **Write path:** Paxos transaction log (clog) is the [WAL](../concepts/wal-and-durability.md); a commit is durable once a **Paxos majority** persists the log. Data-loss window on single-node crash is effectively zero given majority durability; a simultaneous majority loss can lose the un-replicated tail. ([architecture](https://oceanbase.github.io/oceanbase/architecture/))
- **Throughput/latency:** Record **707M tpmC** in the 2020 audited TPC-C run (Ant/Alibaba, 1,557 servers). ([TPC FDR](https://tpc.org/results/fdr/tpcc/ant_financial~tpcc~alibaba_cloud_elastic_compute_service_cluster~fdr~2020-05-17~v01.pdf)) Production Alipay peaks cited at ~61M QPS / hundreds of thousands of TPS during Double 11. ⚠️ unverified — published p99 tail latency figures not located; treat throughput records as best-case audited results, not steady-state SLAs.
- **Compaction / GC:** LSM major compaction (full merge of incremental into baseline), minor compaction, and "dump" for light updates. Major compaction is the classic LSM p99 risk; OceanBase mitigates with off-peak scheduling and rotating/alternate compaction across replicas to avoid hitting the serving leader. ([dbdb.io](https://dbdb.io/db/oceanbase))

## Operations & maturity
- **Backup/restore:** Physical + log backup, point-in-time recovery, and snapshots supported.
- **Observability:** EXPLAIN/plan output, internal performance views, SQL diagnostics; OceanBase Cloud Platform (OCP) and ODC tooling for monitoring.
- **Upgrade story:** Rolling upgrade across replicas/zones (multi-replica design enables online upgrade with leader switchover); day-2 burden is non-trivial — multi-zone Paxos, tenant management, and compaction tuning require expertise.
- **Maturity:** Battle-tested at Ant/Alipay since the mid-2010s and adopted by many Chinese banks/enterprises; very strong production track record at scale. **No public [Jepsen](../concepts/jepsen.md) report exists** as of this writing — ⚠️ unverified — independent formal/Jepsen verification of its consistency claims is absent, a notable gap given the financial-grade marketing. Known operational sharp edges: compaction resource spikes, multi-zone latency, and operational complexity.

## Ecosystem & people
- **Canonical use cases:** High-volume financial OLTP (payments, banking core, ledgers) needing strong consistency, HA, and horizontal scale; MySQL/Oracle migration targets seeking scale-out without app rewrite.
- **Anti-patterns:** Single-node or small workloads (operational overhead dwarfs a plain MySQL/Postgres); pure ad-hoc analytics/data-warehouse workloads (a dedicated OLAP/columnar system like [clickhouse](clickhouse.md) or [snowflake](snowflake.md) fits better); teams without distributed-DB operational depth.
- **Drivers / connectors:** MySQL drivers/ORMs work via wire compatibility; CDC via oblogproxy / Flink CDC / Canal-style tooling; integrates with the broader Alibaba/Ant data stack. Community is large in China, smaller globally; English docs improving but thinner than for MySQL/Postgres.

## Licensing & cost
- **OSS license & flavor:** **Mulan Public License v2 (MulanPubL-2.0)** — a **copyleft** license (derivative works must be distributed under the same terms) that is **NOT OSI-approved**. Do **not** confuse it with the *Mulan Permissive Software License v2 (MulanPSL-2.0)*, which is a different, OSI-approved permissive license; OceanBase's GitHub LICENSE explicitly states "OceanBase Database is licensed under the Mulan Public License, Version 2." OceanBase open-sourced its core (open-core model) on 2021-06-01. The enterprise edition and some cloud/management tooling are proprietary. ([GitHub LICENSE](https://github.com/oceanbase/oceanbase), [ScanCode — MulanPubL-2.0 (copyleft)](https://scancode-licensedb.aboutcode.org/mulanpubl-2.0.html)) This is a copyleft license, not a post-2018 source-available relicensing like SSPL/BSL, but it is also not permissive. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-host (Community Edition) or managed via OceanBase Cloud / ApsaraDB on Alibaba Cloud.
- **Lock-in / cost:** Oracle-compatibility mode and OceanBase-specific tooling create some lock-in. Cost is per-node/per-resource (self-managed) or consumption-based (cloud). Distributed multi-zone footprint makes the small-scale cost high; economics improve at large scale where compression and commodity hardware pay off.

## Hardware / deployment
- **Resource profile:** Memory-sensitive (MemTable + caches favor large RAM — benchmark nodes used 712GB RAM) but not strictly in-memory; SSD/NVMe strongly preferred for LSM I/O. CPU-heavy under parallel query.
- **Storage assumptions:** Local SSD/NVMe in classic deployment; cloud/shared-storage tiers in v4.x.
- **Footprint:** Clustered/distributed (minimum sensible deployment is multi-replica, ideally 3 zones); not embedded. Single-node "standalone" mode exists for dev/test.
- **Deployment:** SaaS (OceanBase Cloud, Alibaba Cloud) or on-prem; Kubernetes operator (ob-operator) available for k8s/StatefulSet deployment.

## Bottom line
Reach for OceanBase if you need MySQL/Oracle-compatible SQL with strong (Paxos) consistency and true horizontal scale for heavy financial-grade OLTP, and you have the operational muscle to run a multi-zone distributed database. Do **not** pick it for small/single-node workloads, pure analytics, or teams wanting low-ops simplicity. The biggest gotcha: despite "financial-grade" consistency marketing, there is **no public Jepsen/independent verification**, and its serializable/consistency guarantees should be validated against your own workload — plus LSM major-compaction must be tuned to protect p99.

## Sources
- [OceanBase Developer Guide — Architecture](https://oceanbase.github.io/oceanbase/architecture/)
- [Database of Databases — OceanBase](https://dbdb.io/db/oceanbase)
- [OceanBase blog — Transaction Engine (GTS, 2PC over Paxos)](https://en.oceanbase.com/blog/2615446272)
- [OceanBase blog — Integrated (HTAP) architecture](https://en.oceanbase.com/blog/13167971328)
- [VLDB 2022 — OceanBase: a 707 million tpmC distributed relational database system (PDF)](https://vldb.org/pvldb/vol15/p3385-xu.pdf)
- [TPC-C Full Disclosure Report — Ant Financial / OceanBase 2020 (PDF)](https://tpc.org/results/fdr/tpcc/ant_financial~tpcc~alibaba_cloud_elastic_compute_service_cluster~fdr~2020-05-17~v01.pdf)
- [GitHub — oceanbase/oceanbase (LICENSE: Mulan Public License v2)](https://github.com/oceanbase/oceanbase)
- [ScanCode LicenseDB — Mulan Public License v2 (MulanPubL-2.0, copyleft)](https://scancode-licensedb.aboutcode.org/mulanpubl-2.0.html)
