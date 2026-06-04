---
name: Fauna
slug: fauna
rank: 146
data_model: Multi-model (document-relational)
license: Apache 2.0 (permissive) for the post-shutdown open-sourced core; hosted service was proprietary/managed-only
summary: Serverless document-relational DB with clock-free strictly-serializable transactions (Calvin) — but the managed service shut down May 2025.
last_researched: 2026-06-04
confidence: high
---

# Fauna

> A globally-distributed, serverless document-relational database whose Calvin-based transaction engine delivered strict serializability without synchronized clocks — now defunct as a service (shut down May 30, 2025), with the core being open-sourced.

## Identity
- **Taxonomy / data model:** Multi-model "document-relational" — JSON-like documents in collections, with native relations, indexes, and joins resolved server-side. Marketed as combining document flexibility with relational capability.
- **Storage model:** Distributed, log-structured, append-only temporal store. Every document keeps version history (bitemporal: data is versioned by transaction timestamp), enabling time-travel queries. Closer to [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM lineage than B-tree page-store; on-disk format proprietary.
- **Workload:** OLTP-oriented operational database for app backends; not an analytics/OLAP engine. Not HTAP — no columnar/analytical side. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP — strictly-serializable read-write transactions hold consistency over availability; a partition that loses quorum stops accepting affected writes. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PC/EC — consistent under partition, and in the normal case it favors consistency (transactions go through a global ordered log) at the cost of cross-region commit latency.
- **Default isolation & what's achievable:** Read-write transactions using serialized indexes run at **strict serializability**; read-only transactions and reads from non-serialized indexes get **snapshot isolation** by default, with the option to upgrade reads to strict serializability ([Fauna transaction docs](https://docs.fauna.com/fauna/current/cookbook/data_model/transactions); [Jepsen FaunaDB 2.5.4](https://jepsen.io/analyses/faunadb-2.5.4)). This nuance matters: the "100% ACID / strictly serializable" marketing overstated the default — many real reads were only snapshot-isolated. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Multi-region, multi-active (every replica accepts reads/writes); ordering is established by inserting transactions into a distributed write-ahead transaction log à la Calvin, then deterministically executing in log order ([Consistency without Clocks](https://fauna.com/blog/consistency-without-clocks-faunadb-transaction-protocol)). Single-phase commit, no 2PC. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** Yes in the limited sense above — reads can be issued at serializable or snapshot levels.
- **Clock dependency:** Deliberately **none** — unlike [google-cloud-spanner](google-cloud-spanner.md)'s TrueTime, Calvin orders transactions via the log, so correctness does not rest on bounded clock skew; replicas can be at arbitrary internet distances. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Flexible. Originally schemaless documents; later added **Fauna Schema Language (FSL)** to define collections, fields, constraints, and indexes as code (schema-on-write where declared).
- **Migration/evolution:** Schema-as-code via `.fsl` files through the CLI/dashboard; field changes are non-locking (no fixed table to ALTER). Index builds backfill asynchronously.
- **Type system:** Documents (objects), arrays, strings, numbers, booleans, timestamps, refs (typed document references for relations), sets. Native temporal/time-travel. No native vector or rich geospatial type.

## Query interface
- **Language:** **FQL (Fauna Query Language)** — a composable, TypeScript/Python-flavored functional DSL (the v10 redesign, 2023). Not SQL; relations are resolved by projection/aliasing in FQL rather than JOIN syntax ([FQL docs](https://docs.fauna.com/fauna/current/api/fql/)). API access is over HTTPS (no wire protocol/socket), suiting serverless/edge.
- **Transactions:** Full multi-statement ACID. The model is "transaction-as-request" — each query/request is itself a transaction, simplifying stateless serverless callers.
- **Native vs app-side:** Native indexes, joins/relations, aggregations, and pagination — all server-side. User-defined functions (UDFs) written in FQL, stored in the database.
- **Stored procedures / UDFs:** Yes, FQL UDFs; also attribute-based access control (ABAC) expressible in FQL.

## Scaling & topology
- **Vertical vs horizontal:** Horizontal and fully managed — automatic sharding/partitioning with no user-facing capacity planning, node count, or resharding. "No sharding, no capacity planning" was the core serverless pitch.
- **Read replicas / read consistency:** Multi-active replicas; reads are snapshot-isolated by default, upgradeable to strict serializability — so a replica read can be consistent or fast, by choice.
- **Storage/compute separation:** Serverless, usage-billed; compute and storage were operationally decoupled and elastic from the user's view (managed service, internals proprietary). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Transactions enter a replicated, ordered write-ahead transaction log before deterministic execution (Calvin); durability rests on log replication across replicas. See [wal-and-durability](../concepts/wal-and-durability.md). Data-loss window is governed by replication quorum, not local fsync timing.
- **Throughput/latency:** Single-phase commit avoids 2PC round-trips, but globally strict-serializable writes still pay cross-region consensus latency (tens to >100 ms across regions). Snapshot reads served locally are fast; strictly-serializable reads cost more. HTTPS-per-request adds connection overhead vs persistent socket protocols. ⚠️ unverified — specific p99 numbers not published in primary sources.
- **Compaction / GC:** Temporal/versioned store retains history with a configurable retention window; old versions are garbage-collected after retention. ⚠️ unverified — exact compaction impact on p99 not documented in primary sources.

## Operations & maturity
- **Backup/restore, PITR:** Temporal model gives built-in time-travel reads within the retention window (a form of point-in-time query). As a managed service, backups were operator-handled.
- **Observability:** Dashboard, query performance metrics, FQL query stats. EXPLAIN-style plan introspection was limited compared to mature SQL engines. ⚠️ unverified — depth of slow-query tooling.
- **Upgrade story:** Fully managed — upgrades were transparent (no user-run rolling upgrades), at the cost of zero control and total dependence on the vendor (which proved fatal).
- **Maturity / Jepsen:** A **[Jepsen analysis of FaunaDB 2.5.4](https://jepsen.io/analyses/faunadb-2.5.4)** found real anomalies despite "strict serializability" claims: incomplete bitemporal index versioning caused **read skew on ~60% of index reads** in healthy clusters; **non-monotonic temporal queries**; **pagination without transactional semantics** (missing/duplicated elements); and sporadic **long-fork** violations of snapshot isolation. Fauna fixed nearly all by 2.6.0-rc10. The documentation was described as "sparse, inconsistent, and overly optimistic." Net: a genuinely novel and ambitious design that initially over-claimed its guarantees, then converged toward them.

## Ecosystem & people
- **Canonical use cases:** Serverless/edge/JAMstack app backends needing multi-region consistency without running infrastructure; apps wanting document flexibility plus real transactions and relations.
- **Anti-patterns:** Analytics/OLAP, heavy aggregate scans, large-scale data warehousing; latency-critical single-region OLTP where local Postgres wins; teams unwilling to learn a proprietary DSL (FQL) and accept HTTP-only access and total vendor lock-in. The shutdown is now the dominant anti-pattern: **do not start new projects on the hosted service.**
- **Drivers / connectors:** Official drivers (JS/TS, Python, Go, others), CLI, GraphQL endpoint (legacy). Limited BI/dbt/CDC ecosystem vs SQL incumbents — a consequence of the bespoke API.
- **Community / support:** Small developer community (the company cited ~25k developers); commercial support ended with the service. Docs quality decent for FQL v10 but historically inconsistent (per Jepsen).

## Licensing & cost
- **License:** The hosted service was **proprietary, managed-only**. After announcing wind-down (March 2025), Fauna committed to **open-sourcing the core database, FQL, drivers, and CLI** ([The Future of Fauna](https://fauna.com/blog/the-future-of-fauna); [InfoQ](https://www.infoq.com/news/2025/03/fauna-shuts-down/)). The released core (Scala) is published under the **Apache License 2.0 (permissive)** — copyright "FaunaDB Foundation" ([github.com/fauna/faunadb](https://github.com/fauna/faunadb), LICENSE.txt) — though as of mid-2025 it is an early-stage source dump with no official server releases and only a provisional build script. The drivers/CLI are MPL-2.0. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Was managed-only; self-hosting only becomes possible via the post-shutdown open-source release (Apache-2.0 source published, but ⚠️ unverified — no packaged/production-ready build as of mid-2025).
- **Lock-in:** High — FQL is bespoke and non-portable, HTTP-only access, no SQL wire compatibility. Migrating off requires rewriting the data layer.
- **Cost model:** Serverless usage-based (per read/write/compute/storage), no per-node pricing. Cheap at small scale; ⚠️ unverified — economics at large scale.

## Hardware / deployment
- **Resource profile:** Irrelevant to end users while managed (vendor-operated). The engine is distributed/quorum-based; not an embedded or single-node design.
- **Storage assumptions:** Cloud-hosted multi-region clusters; users never provisioned disks.
- **Footprint:** Serverless SaaS (clustered internally). Not embedded, not single-node.
- **Deployment:** Was SaaS-only (HTTPS API), edge/serverless-friendly by design. On-prem/self-managed only via the open-sourced code (Apache-2.0, Scala); ⚠️ unverified — production-readiness, as the repo had no official releases and only a provisional `mktarball.sh` build script as of mid-2025.

## Bottom line
Fauna was one of the most intellectually interesting operational databases of its era: a document-relational store with a custom functional query language and a Calvin-derived protocol giving strict serializability across the globe *without* relying on synchronized clocks — a real alternative to Spanner's TrueTime approach. But Jepsen showed it initially over-claimed its consistency, and more decisively, the company could not raise capital to sustain a capital-intensive global managed service and **shut the hosted service down on May 30, 2025**. The single biggest gotcha: it was managed-only with deep FQL lock-in, so the shutdown stranded users — do not build new systems on it; watch the open-source release before considering the technology, and otherwise prefer alternatives like [google-cloud-spanner](google-cloud-spanner.md), [cockroachdb](cockroachdb.md), or [mongodb](mongodb.md).

## Sources
- [Jepsen: FaunaDB 2.5.4](https://jepsen.io/analyses/faunadb-2.5.4)
- [Consistency without Clocks: The Fauna Distributed Transaction Protocol](https://fauna.com/blog/consistency-without-clocks-faunadb-transaction-protocol)
- [Transactions in Fauna — docs](https://docs.fauna.com/fauna/current/cookbook/data_model/transactions)
- [Fauna Query Language (FQL) — docs](https://docs.fauna.com/fauna/current/api/fql/)
- [The Future of Fauna (shutdown announcement)](https://fauna.com/blog/the-future-of-fauna)
- [InfoQ: Fauna Shutting Down — Is the Future Open Source?](https://www.infoq.com/news/2025/03/fauna-shuts-down/)
- [The Register: FaunaDB shuts down but hints at open source future](https://www.theregister.com/2025/03/24/faunadb_shut_down/)
- [Database of Databases: FaunaDB](https://dbdb.io/db/faunadb)
