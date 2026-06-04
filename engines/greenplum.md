---
name: Greenplum
slug: greenplum
rank: 60
data_model: Relational (MPP, PostgreSQL-derived)
license: Source-available since May 2024 (was Apache-2.0); proprietary VMware Tanzu Greenplum
summary: PostgreSQL-derived shared-nothing MPP analytics warehouse — a mature OLAP workhorse that Broadcom closed-sourced in 2024, spawning Apache Cloudberry and EDB forks.
last_researched: 2026-06-04
confidence: high
---

# Greenplum

> A PostgreSQL-based shared-nothing MPP data warehouse for multi-terabyte OLAP, now closed-source under Broadcom — the open-source future lives in its forks (apache-cloudberry, EDB WarehousePG).

## When to use

**Use Greenplum if:**
- ✅ You need a mature, SQL-rich on-prem/private-cloud MPP warehouse with PostgreSQL compatibility over many terabytes to petabytes.
- ✅ Your workload is OLAP/batch analytics and ELT-heavy, with in-database ML (MADlib) and geospatial (PostGIS) at scale.
- ✅ You want familiar PostgreSQL SQL (window functions, CTEs, grouping sets) and parallel bulk loads via gpfdist/COPY.

**Avoid Greenplum if:**
- ❌ You need true SERIALIZABLE isolation — it silently degrades to REPEATABLE READ (no predicate locking), the load-bearing gotcha.
- ❌ Your workload is OLTP, high-concurrency single-row writes, or low-latency point lookups — the coordinator bottleneck and heap MVCC bloat make it a poor fit.
- ❌ You want an open-source future or elastic cloud-burst analytics — Broadcom closed-sourced it in 2024 (the OSS line is a dead-end upstream); evaluate apache-cloudberry, EDB WarehousePG, or a storage-compute-separated warehouse instead.

## Identity
- **Taxonomy / data model:** Relational, SQL, [OLAP](../concepts/oltp-olap-htap.md). Built on PostgreSQL (Greenplum 7 tracks PostgreSQL 12, per [Broadcom/Tanzu Greenplum architecture docs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-arch_overview.html)). MPP = "shared-nothing": one coordinator plus many independent PostgreSQL segment instances, each owning a slice of every table.
- **Storage model:** Hybrid. Default tables are PostgreSQL heap (row store). Append-optimized (AO) tables add column-orientation, compression (zlib/zstd/quicklz; RLE only on column-oriented AO), and per-block checksums ([Broadcom docs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-arch_overview.html)). It is **B-tree, not LSM** ([lsm-vs-btree](../concepts/lsm-vs-btree.md)); columnar AO is the analytics format, not a delta-merge store.
- **Workload:** OLAP/batch analytics and large-scale ELT. Not an OLTP engine — heap MVCC bloat and the coordinator bottleneck make high-rate single-row writes a poor fit. Not HTAP in any meaningful sense.

## Distribution & consistency
- **CAP under partition:** CP-leaning, single-cluster ([cap-pacelc](../concepts/cap-pacelc.md)). It is not a geo-distributed quorum system; a segment-host failure is handled by **mirror failover**, not by sacrificing consistency. If a primary and its mirror are both down, the cluster halts rather than serving partial data.
- **PACELC:** Effectively PC/EC for a single datacenter cluster — it prioritizes consistency, and the latency tradeoff is intra-cluster (interconnect + slowest-segment straggler), not WAN replication. ⚠️ unverified — no formal PACELC classification is published; this is inferred from architecture.
- **Default isolation & what's achievable:** Default **READ COMMITTED**. REPEATABLE READ is supported. Crucially, **`SERIALIZABLE` silently falls back to `REPEATABLE READ`** — Greenplum's snapshot MVCC lacks predicate locking, so true serializability is unavailable despite the SQL keyword being accepted ([Broadcom MVCC docs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-about_mvcc.html)). `READ UNCOMMITTED` also behaves as READ COMMITTED. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md). This is the load-bearing gotcha: do not assume serializable semantics.
- **Replication:** Single-leader per data slice — each primary segment streams a transaction log to a **mirror segment on a different host** ([Broadcom HA docs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-about_ha.html)). Synchronous mirroring; automatic failover to the mirror on primary loss. The coordinator has an optional standby coordinator. See [replication-models](../concepts/replication-models.md). Distributed commit across segments uses **two-phase commit**; failure on any segment rolls back all.
- **Tunable consistency?** No per-query consistency levels (not a Dynamo-style design).
- **Clock dependency:** None for correctness — does not rely on synchronized clocks ([clocks-and-time](../concepts/clocks-and-time.md)).

## Schema
- **Schema-on-write,** rigid relational. PostgreSQL-style DDL.
- **Migration/evolution:** `ALTER TABLE` follows PostgreSQL locking semantics; large rewrites are expensive across all segments. Declarative range/list partitioning with sub-partitions; partition operations (add/exchange/drop) are the standard data-lifecycle tool.
- **Type system:** Full PostgreSQL types — JSON/JSONB, arrays, geospatial (PostGIS available), text/full-text, UUID, ranges. Vector/ANN support is fork- and version-dependent (PGVector-style extensions); ⚠️ unverified — first-class vector indexing in core VMware Greenplum.

## Query interface
- **Language:** SQL (PostgreSQL dialect, PostgreSQL-12-level in GP7). Window functions, CTEs, grouping sets — strong analytical SQL.
- **Transactions:** Full multi-statement ACID, distributed via two-phase commit across segments. Durable but capped at REPEATABLE-READ-equivalent isolation (see above).
- **Native vs app-side:** Native distributed joins, aggregations, and window functions — the planner redistributes/broadcasts rows across the interconnect as needed. Two planners: the legacy Postgres planner and **GPORCA**, a cost-based MPP optimizer; GPORCA can be toggled and sometimes falls back to the Postgres planner for unsupported queries.
- **Stored procedures / UDFs:** PL/pgSQL, PL/Python, PL/Java, PL/R, PL/Perl, plus MADlib for in-database machine learning. External tables (`gpfdist`, S3, PXF) for parallel ELT.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal scale-out across segment hosts is the core design. Each table is hash-distributed on a **distribution key** (or `DISTRIBUTED RANDOMLY`, or replicated). Choosing a skewed key concentrates data/work on a few segments — **data skew is the #1 performance footgun**.
- **Sharding / resharding pain:** Adding hosts requires `gpexpand`, which redistributes data — a heavyweight, planned operation, not elastic auto-resharding. Resharding is real work.
- **Read replicas:** No independent read-scaling replicas; mirrors are passive failover copies, not query-serving. Read scaling = add segments.
- **Storage/compute separation:** Classic Greenplum is **tightly coupled storage+compute** (local disks per segment), the opposite of [storage-compute-separation](../concepts/storage-compute-separation.md) designs like Snowflake. PXF and external tables read external data, but the engine itself is not disaggregated. ⚠️ unverified — extent of object-storage-native tiering in latest Tanzu releases.

## Performance & durability
- **Write path:** PostgreSQL WAL per segment, fsync-based durability ([wal-and-durability](../concepts/wal-and-durability.md)); mirrors receive synchronous log replication, so the committed-data-loss window is small when mirroring is enabled. Bulk loads via `gpfdist`/`COPY` are parallel and the throughput sweet spot.
- **Throughput/latency:** Optimized for high-throughput scans and large joins, not low-latency point queries. **Tail latency is dominated by the slowest segment** — any straggler or skewed partition sets the p99 for the whole query (synchronization-on-the-slowest is inherent to MPP fan-out).
- **Compaction / vacuum / GC:** Heap tables inherit PostgreSQL **VACUUM** and bloat behavior — high-churn heap tables need regular vacuuming or they bloat and slow scans. Append-optimized tables avoid in-place updates but require periodic compaction to reclaim space from updated/deleted rows.

## Operations & maturity
- **Backup/restore:** `gpbackup`/`gprestore` (parallel), legacy `gpcrondump`; PITR is PostgreSQL-WAL-derived but cluster-wide coordination makes it more involved than single-node Postgres.
- **Observability:** PostgreSQL `EXPLAIN`/`EXPLAIN ANALYZE` (with per-segment slice timings — essential for diagnosing skew), pg_catalog/gp_* system views, slow-query logging, and the GPCC (Greenplum Command Center) console in the commercial product.
- **Upgrade story:** Major-version upgrades (e.g., GP6→GP7) historically require `gpupgrade` / backup-restore and meaningful downtime — not seamless rolling upgrades. Day-2 burden is significant: skew management, vacuum scheduling, segment/host capacity planning, and mirror placement.
- **Maturity:** Very mature — production data warehouses since ~2005, PostgreSQL lineage. ⚠️ unverified — no public **Jepsen** report on Greenplum exists as of this writing; correctness claims rest on its single-cluster 2PC design and PostgreSQL heritage, not formal verification. Known failure modes: data skew, coordinator as a single coordination point, VACUUM bloat, interconnect saturation on wide redistributions.

## Ecosystem & people
- **Canonical use cases:** Multi-terabyte to petabyte on-prem/private-cloud data warehouses, ELT-heavy analytics, in-database ML (MADlib), geospatial analytics at scale. **Anti-patterns:** OLTP / high-concurrency single-row writes, low-latency point lookups, elastic burst workloads, and serializable-isolation-dependent applications.
- **Drivers / connectors:** PostgreSQL wire protocol → psql, JDBC/ODBC, libpq drivers, most BI tools (Tableau, Power BI), and dbt (via Postgres/Greenplum adapters). PXF connects to Hadoop/S3/JDBC sources; CDC via standard Postgres-style tooling is partial.
- **Community & support:** Long-standing user base; commercial support via **Broadcom (VMware Tanzu Greenplum)**. The open-source community fragmented after the 2024 closure — energy moved to apache-cloudberry (Apache Incubator) and EDB's Greenplum-compatible offering. Docs are solid (Broadcom TechDocs + legacy GPDB docs). Learning curve: high for ops (MPP tuning), moderate for SQL (it's PostgreSQL).

## Licensing & cost
- **OSS license & flavor:** Was **Apache-2.0** open source. In **May 2024, Broadcom (post-VMware acquisition) closed-sourced Greenplum** — GitHub repos archived/read-only, community channels shut down; future releases ship only as proprietary **VMware Tanzu Data Suite** ([Broadcom/community accounts](https://en.wikipedia.org/wiki/Greenplum), [Apache Cloudberry blog](https://cloudberry.apache.org/blog/cloudberry-database-enters-the-apache-incubator/)). This is a post-2018-style relicensing event — see [license-taxonomy](../concepts/license-taxonomy.md). The last open-source release line (GP 6/7) remains available but unmaintained upstream.
- **Self-managed vs managed-only:** Self-managed software (on-prem/VM/cloud-VM); also available via cloud marketplaces. Not a serverless SaaS.
- **Lock-in:** Commercial version locks to Broadcom; GPORCA, gp_* tooling, and proprietary connectors are migration friction. Forks (apache-cloudberry, EDB WarehousePG) exist precisely to avoid this.
- **Cost model:** Commercial per-core/per-node subscription licensing; open-source forks are free (infra cost only). At scale, the tightly-coupled storage+compute means you pay for compute even when only storing — the inverse of separated-storage economics.

## Hardware / deployment
- **Resource profile:** Disk-throughput- and memory-bound for analytics; CPU-bound on compression/decompression and complex joins. Working set need not fit in RAM (it's a disk-oriented warehouse), but more RAM reduces spill.
- **Storage assumptions:** Local fast disk per segment (NVMe/SSD ideal); designed for **direct-attached storage**, not network-attached/object stores — segment-local I/O is the throughput engine.
- **Footprint:** Clustered (1 coordinator + N segment hosts, each running multiple segment instances). Not embedded, not single-node-by-design (single-node "demo" installs exist).
- **Deployment:** On-prem and cloud VMs; bare metal common for max I/O. Container/k8s deployments exist but the StatefulSet + local-disk + stable-network requirements make Kubernetes operation nontrivial. ⚠️ unverified — current Broadcom-supported k8s operator status.

## Bottom line
Reach for Greenplum (or, increasingly, its open forks apache-cloudberry / EDB WarehousePG) if you need a mature, SQL-rich, on-prem MPP warehouse with PostgreSQL compatibility and in-database analytics over many terabytes. Avoid it for OLTP, low-latency point queries, elastic cloud-burst analytics, or anything depending on true SERIALIZABLE isolation. The two biggest gotchas: **`SERIALIZABLE` silently degrades to REPEATABLE READ**, and Broadcom's **2024 closed-sourcing** means the open-source version is a dead-end upstream — new green-field projects should evaluate the forks or a storage-compute-separated warehouse instead.

## Sources
- [About the Greenplum Architecture — Broadcom TechDocs (GP7)](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-arch_overview.html)
- [About Concurrency Control (MVCC / isolation) — Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-about_mvcc.html)
- [About Redundancy and Failover — Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/admin_guide-intro-about_ha.html)
- [Greenplum — Wikipedia (history, Broadcom closure)](https://en.wikipedia.org/wiki/Greenplum)
- [Apache Cloudberry enters the Apache Incubator (fork history)](https://cloudberry.apache.org/blog/cloudberry-database-enters-the-apache-incubator/)
- [EDB Postgres AI — Greenplum-compatible open-source alternative](https://www.enterprisedb.com/blog/edb-postgres-ai-introduces-greenplum-compatible-open-source-alternative)
