---
name: InterBase
slug: interbase
rank: 74
data_model: Relational (embeddable)
license: Proprietary / commercial (Embarcadero); free ToGo Lite tier
summary: Veteran embeddable/server SQL RDBMS that pioneered MVCC; today a niche commercial engine tied to the Delphi/RAD Studio ecosystem with strong column-level encryption and Change Views CDC.
last_researched: 2026-06-04
confidence: high
---

# InterBase

> A small-footprint, low-administration relational engine that invented multi-version concurrency control and now survives as a commercial embedded/server DB inside the Embarcadero (Delphi/C++Builder) world, distinguished by built-in column-level encryption and "Change Views" change tracking.

## Identity
- **Taxonomy / data model:** single-model relational RDBMS, SQL-92-oriented. Deployable as an embedded library *or* a shared-everything client/server. ([dbdb.io](https://dbdb.io/db/interbase))
- **Storage model:** disk-oriented, row-store; on-disk pages with a B-tree variant for indexes; index compression limited to prefix/suffix on keys. ([dbdb.io](https://dbdb.io/db/interbase)) Historically significant as the origin of [mvcc](../concepts/mvcc.md) — its "Multi-Generational Architecture" (MGA) keeps multiple row versions so readers never block writers. ([Embarcadero](https://www.embarcadero.com/products/interbase), [dbdb.io](https://dbdb.io/db/interbase)) See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP / operational. Targeted at embedded apps, point-of-sale, field/mobile, and small-to-mid client/server deployments — not analytics. Not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) and [embedded-databases](../concepts/embedded-databases.md).

## Distribution & consistency
- **CAP under partition:** N/A as a distributed system — InterBase is a single-node engine (embedded or one server process). No native multi-node clustering / sharding, so [cap-pacelc](../concepts/cap-pacelc.md) does not meaningfully apply.
- **PACELC:** N/A — single-node.
- **Default isolation & what's achievable:** three levels — SNAPSHOT (the default; snapshot isolation, a stable committed view as of transaction start), SNAPSHOT TABLE STABILITY (most restrictive, table-level locking that lets only one transaction modify the tables it touches), and READ COMMITTED. ([Comparing isolation levels — docwiki](https://docwiki.embarcadero.com/InterBase/2020/en/Comparing_SNAPSHOT,_READ_COMMITTED,_and_SNAPSHOT_TABLE_STABILITY), [dbdb.io](https://dbdb.io/db/interbase)) Snapshot isolation is delivered via MGA/[mvcc](../concepts/mvcc.md). There is no separately named SQL "SERIALIZABLE" level; SNAPSHOT TABLE STABILITY is the closest serialization guarantee but achieves it via coarse table locking rather than predicate/SSI techniques. Treat SNAPSHOT as snapshot isolation, not full serializability. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** no built-in multi-node replication in the core engine. Change data capture is handled application-side via **Change Views**, a subscription mechanism that tracks row inserts/updates/deletes at column-level granularity over a disconnected period using the multi-generational architecture. ([Embarcadero docwiki](https://docwiki.embarcadero.com/InterBase/2020/en/Change_Views), [Idera blog](https://blog.idera.com/developer-tools/interbase-feature-spotlight-change-views/)) See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** N/A — single-node.
- **Clock dependency:** none for correctness — single-node, no distributed clock requirements. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write:** rigid relational schema; DDL for tables, domains, constraints, views, triggers, stored procedures, and generators (sequences). ([Embarcadero docwiki](https://docwiki.embarcadero.com/InterBase/2020/en/Change_Views))
- **Migration/evolution:** standard `ALTER TABLE` DDL. ⚠️ unverified — InterBase's online-DDL/locking behavior for schema changes under concurrent load is not clearly documented; assume `ALTER` may take locks.
- **Type system:** standard SQL types plus BLOBs (with filters), arrays, and BOOLEAN. Built-in **column-level encryption** is a first-class feature (see below). ⚠️ unverified — no native JSON, geospatial, or vector types as core features.

## Query interface
- **Language:** SQL (SQL-92 oriented; uses "SQL dialect" versioning carried over from the Borland lineage). ([dbdb.io](https://dbdb.io/db/interbase)) Cost-based optimizer supporting nested-loop and sort-merge joins; user-overridable plans via the `PLAN` clause. ([dbdb.io](https://dbdb.io/db/interbase))
- **Transactions:** full multi-statement ACID transactions; a transaction is explicitly started and can take a snapshot or live (read committed) view. ([Embarcadero](https://www.embarcadero.com/products/interbase))
- **Native vs app-side:** native joins, aggregations, secondary indexes (auto-created for PRIMARY KEY, FOREIGN KEY, UNIQUE). ([dbdb.io](https://dbdb.io/db/interbase))
- **Stored procedures / UDFs:** stored procedures and triggers in InterBase's PSQL procedural language; external UDFs historically supported. ([Embarcadero docwiki](https://docwiki.embarcadero.com/InterBase/2020/en/Change_Views))

## Scaling & topology
- **Vertical vs horizontal:** vertical only. Editions cap CPU/core counts (e.g., Desktop scales to ~4 cores; Server edition documented up to dozens of cores and unlimited users). ([Embarcadero product editions](https://www.embarcadero.com/products/interbase/product-editions))
- **Sharding/partitioning:** none native. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas:** no native replica topology; cross-database sync is done via Change Views / application logic rather than streaming replication.
- **Storage/compute separation:** none — local files, monolithic engine. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** InterBase XE7 added optional **journaling / write-ahead logging** ([wal-and-durability](../concepts/wal-and-durability.md)); when a journal is created, write operations to the main database become asynchronous while journal-file I/O is always synchronous, so all changes hit durable storage before commit. ([Enabling Journaling — XE7 docwiki](http://docwiki.embarcadero.com/InterBase/XE7/en/Enabling_Journaling_and_Creating_Journal_Files), [InterBase features — Embarcadero](https://www.embarcadero.com/products/interbase/features/fast-lightweight)) Combined with MGA, the engine maintains old row versions until garbage-collected. ⚠️ unverified — group-commit details and the precise crash data-loss window when journaling is *not* enabled are not clearly published; the legacy "forced writes" setting governs whether ordinary page writes are synchronous.
- **Throughput/latency:** positioned as "ultra-fast" and low-footprint for embedded/SMB workloads; ⚠️ unverified — no independent published p99/tail benchmarks. Treat vendor performance claims as marketing.
- **Compaction / GC:** MGA accumulates obsolete row versions; reclamation is via **background garbage collection** in the native multi-threaded server plus periodic sweep. ([Embarcadero](https://www.embarcadero.com/products/interbase)) Like other MVCC engines, long-running snapshot transactions can hold back GC and bloat the database (analogous to PostgreSQL vacuum pressure). See [mvcc](../concepts/mvcc.md).

## Operations & maturity
- **Backup/restore:** logical backup/restore via `gbak`; **online backup** is enabled by the multi-generational architecture (readers don't block the backup). ([Embarcadero](https://www.embarcadero.com/products/interbase)) ⚠️ unverified — full PITR support details.
- **Observability:** query plans via `PLAN`/optimizer output; ⚠️ unverified — extent of built-in metrics and slow-query logging is limited compared to PostgreSQL/SQL Server.
- **Upgrade story:** version upgrades typically via backup/restore across major versions; ⚠️ unverified — rolling-upgrade story (single-node, so usually entails downtime).
- **Maturity:** very mature lineage — created by Jim Starkey in 1984, acquired by Borland (1991), forked into open-source [firebird](firebird.md) (2000), and now owned and maintained by Embarcadero/Idera (acquired 2008). ([dbdb.io](https://dbdb.io/db/interbase)) Stable but a shrinking niche. **No Jepsen report exists** (single-node engine, not a target for distributed-consistency testing).

## Ecosystem & people
- **Canonical use cases:** embedded databases shipped inside desktop/mobile applications, especially Delphi/C++Builder (RAD Studio) apps; field/disconnected apps that sync deltas via Change Views; deployments needing strong at-rest encryption with near-zero DBA administration.
- **Anti-patterns:** large-scale OLAP/analytics; horizontally scaled, distributed, or high-write multi-node systems; greenfield projects with no tie to the Delphi/Embarcadero stack (where [postgresql](postgresql.md), [sqlite](sqlite.md), or [firebird](firebird.md) are more obvious choices). For a free, open-source descendant with similar architecture, prefer [firebird](firebird.md).
- **Drivers/connectors:** tight integration with Delphi/C++Builder (FireDAC, dbExpress); ODBC/JDBC and ADO.NET (InterBase for .NET) drivers exist. Smaller third-party CDC/Kafka/dbT/BI ecosystem than mainstream engines.
- **Community/support:** small, vendor-driven community; commercial support via Embarcadero. Docs are decent (docwiki) but the developer mindshare is modest and declining.

## Licensing & cost
- **License flavor:** proprietary/commercial — not open source. ([Embarcadero](https://www.embarcadero.com/products/interbase)) A free **ToGo Lite** tier exists with size/feature limits; **ToGo Pro** (paid subscription) unlocks encryption, larger DB size, and Change Views. ([Embarcadero ToGo subscription](https://www.embarcadero.com/products/interbase/togo/subscription-license)) See [license-taxonomy](../concepts/license-taxonomy.md). (Contrast with [firebird](firebird.md), the open-source fork of the same codebase, under the InterBase Public License / IDPL.)
- **Self-managed vs managed:** self-managed only; no first-party managed cloud service.
- **Lock-in:** moderate — proprietary engine and deep coupling to the Embarcadero toolchain; migration off typically targets [firebird](firebird.md) or [postgresql](postgresql.md).
- **Cost model:** per-deployment / per-edition licensing for Desktop and Server editions; ToGo is per-system or subscription for embedded deployments. ([Embarcadero licensing](https://www.embarcadero.com/products/InterBase/licensing-options), [product editions](https://www.embarcadero.com/products/interbase/product-editions)) Specific list pricing is not published publicly.

## Hardware / deployment
- **Resource profile:** lightweight, low-footprint; designed to run on modest hardware without a dedicated DBA. Working set need not fit entirely in RAM (disk-oriented row store).
- **Storage assumptions:** local file storage; no special NVMe/network-attached requirements.
- **Footprint:** flexible — deeply **embeddable** (ToGo) inside an application binary, or a standalone server process. Cross-platform: Windows, Linux, macOS, Solaris, Android, iOS. ([dbdb.io](https://dbdb.io/db/interbase), [Embarcadero ToGo](https://docwiki.embarcadero.com/RADStudio/Sydney/en/InterBase_ToGo))
- **Deployment:** on-prem / embedded; not a SaaS. ⚠️ unverified — Kubernetes/StatefulSet patterns are not a documented focus; it is typically shipped inside apps rather than orchestrated.

## Bottom line
Reach for InterBase if you are building Delphi/C++Builder (RAD Studio) applications that need a near-zero-administration embedded SQL database with strong built-in column-level encryption and the Change Views delta-tracking feature for occasionally-connected sync. Don't reach for it for analytics, distributed/horizontally-scaled systems, or any greenfield project without an Embarcadero tie — its open-source sibling [firebird](firebird.md) or mainstream [postgresql](postgresql.md)/[sqlite](sqlite.md) will usually serve better and cheaper. The single biggest gotcha: it is a proprietary, single-vendor, single-node engine with a shrinking ecosystem and no public benchmarks — you are betting on Embarcadero, not a broad community.

## Sources
- [Embarcadero — InterBase product page](https://www.embarcadero.com/products/interbase)
- [Database of Databases — InterBase](https://dbdb.io/db/interbase)
- [Change Views — InterBase docwiki](https://docwiki.embarcadero.com/InterBase/2020/en/Change_Views)
- [Idera blog — InterBase Feature Spotlight: Change Views](https://blog.idera.com/developer-tools/interbase-feature-spotlight-change-views/)
- [Embarcadero — Product Editions](https://www.embarcadero.com/products/interbase/product-editions)
- [Embarcadero — Licensing Options](https://www.embarcadero.com/products/InterBase/licensing-options)
- [Embarcadero — InterBase ToGo Subscription License](https://www.embarcadero.com/products/interbase/togo/subscription-license)
- [Embarcadero docwiki — InterBase ToGo](https://docwiki.embarcadero.com/RADStudio/Sydney/en/InterBase_ToGo)
