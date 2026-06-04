---
name: Alibaba Cloud PolarDB
slug: alibaba-cloud-polardb
rank: 81
data_model: Relational (cloud-native, shared-storage)
license: Source-available / managed cloud service (PolarDB-for-PostgreSQL open-sourced under Apache 2.0; managed PolarDB is proprietary)
summary: Alibaba's Aurora-style cloud-native relational DB — one writer, up to 15 readers over a shared distributed disk, MySQL/PostgreSQL/Oracle wire-compatible, with tunable read-replica consistency.
last_researched: 2026-06-04
confidence: medium
---

# Alibaba Cloud PolarDB

> Alibaba's answer to Amazon Aurora: storage-compute separation over a shared distributed filesystem (PolarFS), giving one primary plus up to 15 read replicas that all see the same disk — fast read scale-out and no data copying, but a single writer and a managed-only (mostly) deployment.

## Identity
- **Taxonomy / data model:** Relational. Sold in three engine flavors: PolarDB for MySQL, PolarDB for PostgreSQL, and PolarDB for PostgreSQL (Compatible with Oracle). A separate product, **[PolarDB-X](alibaba-cloud-polardb.md)**, is the shared-nothing distributed-SQL sibling (do not conflate — different architecture).
- **Storage model:** Row-store inheriting the upstream engine's on-disk format (InnoDB B-tree for MySQL; heap + WAL for PostgreSQL). See [lsm-vs-btree](../concepts/lsm-vs-btree.md). The distinguishing layer is **PolarFS**, a user-space distributed filesystem using RDMA, NVMe and SPDK to give near-local-SSD write latency over shared storage ([PolarFS, VLDB 2018](https://dl.acm.org/doi/10.14778/3229863.3229872)).
- **Workload:** Primarily OLTP. Markets HTAP via PolarDB-MySQL's columnar index ("In-Memory Column Index" / IMCI) and parallel query — physical separation is a **columnar secondary representation** plus elastic read-only nodes, not just a vague claim. See [oltp-olap-htap](../concepts/oltp-olap-htap.md), [columnar-storage](../concepts/columnar-storage.md).

## Distribution & consistency
- **CAP under partition:** CP-leaning within a region — a single primary holds all writes; on partition/failover the cluster stops accepting writes until a new primary is promoted. Because compute shares one storage layer, this is not a quorum-replication CAP story for the primary path. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, favors consistency (single-writer, RPO=0 via shared storage / VotingDisk). Else (normal operation) it **exposes the latency-vs-consistency knob to the user** through read-replica consistency levels (below) — closer to PC/EL with EL tunable per cluster.
- **Default isolation:** PolarDB for MySQL supports READ UNCOMMITTED, READ COMMITTED (the **default** — note this differs from upstream community MySQL/InnoDB, whose default is REPEATABLE READ), and REPEATABLE READ, and **does not support SERIALIZABLE** ([PolarDB-MySQL FAQ](https://www.alibabacloud.com/help/en/polardb/polardb-for-mysql/faq-7)). PostgreSQL flavor inherits PG isolation (read committed default, serializable via SSI). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Read-replica consistency (the key feature):** four levels via PolarProxy — **eventual** (route freely, may read stale), **session** (read-your-writes within a session; the recommended default), **global** (proxy reads the primary's latest LSN, waits for a read-only node to catch up before routing), and **global high-performance mode** (kernel-level using commit-timestamp/CTS + RDMA). Each level "trades read latency for data freshness" ([docs](https://www.alibabacloud.com/help/en/polardb/polardb-for-mysql/user-guide/consistency-levels)); global mode has a `ConsistTimeout` (20 ms default) after which reads fall back to the primary. The [PolarDB-SCC paper (VLDB 2023)](https://www.vldb.org/pvldb/vol16/p3754-chen.pdf) describes the low-latency strong-consistency read design.
- **Replication:** Within a cluster, the primary and read-only nodes share storage; in-memory state is shipped via a **physical redo-log replication protocol** rather than copying data. PolarFS itself replicates storage chunks via ParallelRaft (a relaxed Raft variant). See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md), [wal-and-durability](../concepts/wal-and-durability.md). Cross-region DR is a separate add-on.
- **Tunable consistency?** Yes — per-cluster/per-session read-consistency level (above). Writes are not tunable; single primary.
- **Clock dependency:** Global high-performance consistency relies on commit timestamps (CTS) propagated over RDMA; correctness does not require externally synchronized wall clocks like TrueTime. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational — inherits MySQL/PostgreSQL/Oracle-compat DDL semantics.
- **Migration/DDL:** Inherits engine DDL. PolarDB-MySQL has issues where long-running transactions on read-only nodes can block DDL (documented mitigations exist), reflecting the shared-storage coupling between writer and readers.
- **Type system:** Full upstream type system — JSON, generated columns, geospatial; Oracle-compat flavor adds PL/SQL and Oracle types. Vector search is available in the PostgreSQL flavor (pgvector-style); ⚠️ unverified — exact vector feature parity vs upstream.

## Query interface
- **Language:** SQL. Wire/dialect compatibility is the selling point — MySQL protocol, PostgreSQL protocol, or Oracle compatibility (PL/SQL) depending on flavor.
- **Transactions:** Full multi-statement ACID on the single primary, at the isolation levels above.
- **Native joins/indexes/aggregations:** Full SQL — joins, window functions, aggregations native. Parallel query and the columnar IMCI accelerate analytics on the same instance.
- **Stored procedures / UDFs:** Yes — SQL/PSM (MySQL), PL/pgSQL, and Oracle PL/SQL in the Oracle-compat flavor.

## Scaling & topology
- **Vertical + horizontal-read:** Scale up node class, and scale out reads by adding up to **15 read-only nodes** (16 total). Adding a read-only node "takes within 5 minutes and requires no data replication" because storage is shared ([architecture docs](https://www.alibabacloud.com/help/en/polardb/polardb-for-oracle/architecture-8)).
- **Writes do not shard:** A single primary handles all writes — this is the architectural ceiling. For write-side horizontal scale you must move to **[PolarDB-X](alibaba-cloud-polardb.md)** (shared-nothing, sharded, Multi-Paxos). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read consistency on replicas:** configurable (see Distribution & consistency).
- **Storage/compute separation:** Yes — the defining property. Storage scales online to **500 TB per instance**; compute scales independently. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Redo log written to PolarFS shared storage; storage chunks replicated via ParallelRaft. **RPO = 0** within a cluster because all nodes share the same durable storage — a compute-node failure or read-only→primary switch loses no committed data ([architecture docs](https://www.alibabacloud.com/help/en/polardb/polardb-for-oracle/architecture-8)). VotingDisk drives second-level failover within a zone. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** PolarFS targets near-local-SSD write latency via user-space RDMA/NVMe/SPDK. Alibaba reports very high TPC-C-style throughput (2 billion tpmC claimed in a 2025 scale-out paper — vendor benchmark, treat as marketing). p99 is dominated by replication-catch-up when strong read consistency is enabled (the `ConsistTimeout` fallback to primary can raise primary load under replication lag).
- **Compaction/vacuum/GC:** Inherits engine behavior (InnoDB purge / PG autovacuum). MVCC garbage on the shared storage affects all readers since they read the same pages.

## Operations & maturity
- **Backup/restore:** Snapshot-based backups on shared storage, PITR, and fast clone/restore leveraging storage-layer snapshots.
- **Observability:** Standard MySQL/PG EXPLAIN and slow-query logs, plus Alibaba Cloud console metrics, DAS (Database Autonomy Service) for diagnostics.
- **Upgrade story:** Managed rolling upgrades; failover behind the single PolarProxy endpoint so connection strings don't change. Day-2 burden is low for the managed service (Alibaba operates it), higher if self-hosting the open-source PostgreSQL variant.
- **Maturity:** Mature, runs large-scale production inside Alibaba (Singles' Day peak loads). Backed by peer-reviewed papers (PolarFS VLDB 2018, Cloud-Native DB at Alibaba VLDB 2019, PolarDB-SCC VLDB 2023). **No public Jepsen report** for PolarDB or PolarDB-X as of this writing — ⚠️ unverified — distributed-isolation claims rest on vendor papers, not independent formal testing.

## Ecosystem & people
- **Canonical use cases:** MySQL/PostgreSQL/Oracle workloads needing read scale-out, large storage (up to 500 TB), and fast elastic readers without re-sharding; lift-and-shift off Oracle (Oracle-compat flavor); e-commerce OLTP with bursty read traffic.
- **Anti-patterns:** Write-bound workloads that exceed a single primary (use [PolarDB-X](alibaba-cloud-polardb.md) or another sharded system); workloads needing SERIALIZABLE on the MySQL flavor; multi-cloud or on-prem-first strategies (PolarDB managed is Alibaba-Cloud-locked); teams needing independent third-party correctness verification.
- **Connectors:** Drop-in MySQL/PostgreSQL drivers and ORMs (it speaks the native protocols); CDC via binlog (MySQL flavor); integrates with Alibaba's DTS, Flink, and analytics stack. dbt/BI tools work through standard MySQL/PG connectors.
- **Community/support:** Large in China, thinner English-language community and docs (machine-translated docs are common). Commercial support via Alibaba Cloud. The PostgreSQL kernel is open-sourced on GitHub (polardb/PolarDB-for-PostgreSQL).

## Licensing & cost
- **License:** Managed PolarDB is a proprietary cloud service. **PolarDB for PostgreSQL** kernel is open-sourced under **Apache 2.0** (permissive); **PolarDB-X** is also open-sourced (Apache 2.0). The fully managed product with PolarFS/PolarProxy is not self-hostable in the same form. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** The headline cloud product is managed-only; the OSS PostgreSQL variant is self-hostable but loses the integrated shared-storage/proxy experience.
- **Lock-in:** Significant — PolarFS, PolarProxy, console tooling, and Oracle-compat extensions tie you to Alibaba Cloud. Wire compatibility eases application portability but not operational portability.
- **Cost model:** Per-node compute (by node class) + per-GB storage (pay-as-you-go on actual usage, autoscaling) + I/O; also a serverless option. Storage-compute separation makes read scale-out comparatively cheap; the single-writer ceiling means very high write rates require the more expensive distributed PolarDB-X.

## Hardware / deployment
- **Resource profile:** Memory- and I/O-bound like its upstream engines; working set need not fit in RAM (durable shared storage), but buffer-pool hit rate drives latency. RDMA network fabric is integral to PolarFS performance.
- **Storage assumptions:** Network-attached **shared** distributed storage (PolarFS) built on NVMe SSDs with RDMA — not local disk. This is the architectural foundation, not a deployment option.
- **Footprint:** Clustered managed service (1 primary + 0–15 read-only nodes sharing one storage volume); also a serverless tier. Not embedded.
- **Deployment:** SaaS on Alibaba Cloud (primary path). On-prem/k8s only via the open-source PostgreSQL/PolarDB-X variants, which is a different operational beast.

## Bottom line
Reach for PolarDB if you're already on Alibaba Cloud and want Aurora-style economics — one writer, cheap elastic read replicas over shared storage, MySQL/PostgreSQL/Oracle compatibility, and RPO=0 within a region — without managing storage replication yourself. Don't reach for it if your bottleneck is write throughput (single primary; you'll need the sharded [PolarDB-X](alibaba-cloud-polardb.md)), if you need SERIALIZABLE on MySQL, or if cloud portability matters (the managed product is Alibaba-locked). Biggest gotcha: read-only nodes can serve stale data by default — you must explicitly choose session or global consistency, and the stronger levels add read latency or push load back onto the primary.

## Sources
- [PolarFS: an ultra-low latency and failure resilient distributed file system (VLDB 2018)](https://dl.acm.org/doi/10.14778/3229863.3229872)
- [Cloud-Native Database Systems at Alibaba: Opportunities and Challenges (VLDB 2019)](https://www.vldb.org/pvldb/vol12/p2263-li.pdf)
- [PolarDB-SCC: A Cloud-Native Database Ensuring Low Latency for Strongly Consistent Reads (VLDB 2023)](https://www.vldb.org/pvldb/vol16/p3754-chen.pdf)
- [PolarDB architecture (Alibaba Cloud docs)](https://www.alibabacloud.com/help/en/polardb/polardb-for-oracle/architecture-8)
- [Consistency levels of PolarDB (Alibaba Cloud docs)](https://www.alibabacloud.com/help/en/polardb/polardb-for-mysql/user-guide/consistency-levels)
- [PolarDB-X architecture (Alibaba Cloud docs)](https://www.alibabacloud.com/help/en/polardb/polardb-for-xscale/architecture-6)
- [dbdb.io — PolarDB](https://dbdb.io/db/polardb)
