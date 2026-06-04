---
name: RavenDB
slug: ravendb
rank: 112
data_model: Document (multi-model)
license: AGPLv3 / commercial (dual-licensed; Community free tier); clients MIT
summary: .NET-native document database with ACID single-doc transactions, eventually-consistent indexes, and a Raft cluster — but Jepsen found its "ACID" claims overstated under concurrency.
last_researched: 2026-06-04
confidence: high
---

# RavenDB

> A developer-friendly .NET document store that pairs ACID document writes with eventually-consistent background indexes, but whose marketed isolation guarantees did not hold up under [Jepsen](https://jepsen.io/analyses/ravendb-6.0.2) testing — read the consistency section before trusting "ACID" here.

## When to use

**Use RavenDB if:**
- ✅ You're a .NET/C# shop wanting a document store with excellent tooling (Studio), built-in full-text search, time series, and easy embedding of related data
- ✅ You run small-to-mid clusters where developer velocity matters
- ✅ You want multi-model features (counters, time series, attachments, revisions, vector search in v7) with easy ETL out to SQL/OLAP/Kafka/Elasticsearch
- ✅ You can use explicit optimistic concurrency and cluster-wide (Raft) transactions where correctness matters

**Avoid RavenDB if:**
- ❌ You rely on its "ACID" branding for multi-key correctness — [Jepsen 6.0.2](https://jepsen.io/analyses/ravendb-6.0.2) found silent lost updates under default settings and fractured reads even in cluster-wide "serializable" mode
- ❌ You need a write to be immediately queryable — indexes are eventually consistent by design (queries can return stale results)
- ❌ You need heavy ad-hoc analytics/OLAP or relational joins (joins are limited to includes/multi-map indexes)
- ❌ You're outside the .NET ecosystem or planning very large multi-petabyte sharded deployments (sharding is still maturing)

## Identity
- **Taxonomy / data model:** document database (JSON documents in named collections), multi-model — adds counters, [time-series](https://ravendb.net/features/time-series/distributed-time-series), attachments/blobs, a graph-query layer, and (since v7, Feb 2025) [vector search](https://ravendb.net/articles/ravendb-version-6-0-is-now-live). See [document-data-model](../concepts/document-data-model.md).
- **Storage model:** B-tree-based; data persisted by RavenDB's in-house **Voron** managed storage engine, an mmap + copy-on-write B+tree with a write-ahead log ([docs](https://docs.ravendb.net/7.2/server/storage/storage-engine/)). Not LSM — see [lsm-vs-btree](../concepts/lsm-vs-btree.md). Search indexes are separate structures built by Lucene or RavenDB's native **Corax** engine ([docs](https://ravendb.net/docs/article-page/6.0/csharp/indexes/search-engine/corax)).
- **Workload:** OLTP document store. Not HTAP — analytics is offloaded via ETL (SQL/OLAP/Kafka/Elasticsearch) rather than an in-engine columnar path. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **Layered CAP — and this is the key gotcha.** The *cluster/config layer* (powered by Raft, see [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)) is **CP**: schema, index definitions, and cluster-wide transactions need a quorum and refuse to proceed without one. The *document/database layer* is **AP**: ordinary writes commit to one node and replicate asynchronously, staying available under partition and reconciling later ([RavenDB CAP/ACID article](https://ravendb.net/articles/cap-and-acid-optimization-strategies-for-database-consistency-and-availability)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition the document layer favors A (PA); else it favors latency over consistency (EL) for normal writes. Cluster-wide transactions invert this to PC/EC. Mixed within one engine depending on write mode.
- **Default isolation & what's actually achievable:** RavenDB documents single-node sessions as snapshot isolation and cluster-wide transactions as serializable. **[Jepsen 6.0.2 (2024)](https://jepsen.io/analyses/ravendb-6.0.2) contradicted both:** default single-node transactions without optimistic concurrency exhibited **lost updates** (81 lost updates across 975 keys in a 5-second run); with optimistic concurrency enabled, transactions showed **fractured reads** (observing partial effects of other transactions, violating even Read Atomic); and even cluster-wide "serializable" transactions exhibited fractured reads. Jepsen also noted RavenDB's CEO clarified that a "transaction" spans only a single HTTP request, contradicting docs that portray a session as an interactive business transaction. Treat the "ACID" marketing as **single-document atomicity by default, not multi-key isolation** — flag any reliance on the stronger claim. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** document layer is **multi-master / leaderless async replication** between cluster members; conflicts on the same document are detected via change vectors and resolved by a configurable strategy (latest-wins or a resolver script). See [replication-models](../concepts/replication-models.md). Cluster-wide writes go through Raft and require majority ack.
- **Tunable consistency:** per-write choice between single-node (async, fast) and cluster-wide (Raft, consistent) transactions; reads can request "wait for index" / "wait for replication" semantics.
- **Clock dependency:** conflict resolution uses change vectors (logical clocks), not wall-clock — so it does not depend on synchronized time the way TrueTime systems do. See [clocks-and-time](../concepts/clocks-and-time.md). ⚠️ unverified — exact change-vector merge semantics not confirmed from primary docs in this pass.

## Schema
- **Schema-on-read.** Documents are schemaless JSON; structure lives in application code. No table DDL.
- **Migration/evolution:** no rigid schema to migrate; index definitions *are* versioned cluster state and deploying a new index triggers a (potentially expensive) background re-index rather than locking data.
- **Type system:** JSON types plus first-class **counters**, **time series**, **attachments**, document **revisions** (versioning), and **vector** fields (v7).

## Query interface
- **Language:** **RQL** (RavenDB Query Language), a SQL-like DSL translated from the LINQ/fluent client API ([query docs](https://docs.ravendb.net/7.2/querying/overview)). Also a graph-query syntax and full-text search via analyzers.
- **Transactions:** ACID single-document writes; multi-document atomic writes within one session/HTTP request; optional cluster-wide (Raft) transactions for cross-node atomicity with compare-exchange. See the consistency caveats above.
- **Native vs app-side:** queries are always served by an **index**; if none exists RavenDB auto-creates one. Map/reduce indexes provide aggregations; joins are limited (handled via includes/related-document loading and multi-map indexes rather than relational joins). Indexes are **eventually consistent** by design — a query may return stale results until the background indexer catches up.
- **Stored procedures / UDFs:** index definitions and ETL/subscription scripts are written in JavaScript; patch operations use JS. No SQL-style stored procedures.

## Scaling & topology
- **Vertical + horizontal.** Replication gives HA and read scaling; **sharding** (introduced v6.0, [docs](https://ravendb.net/docs/article-page/6.0/csharp/sharding/overview)) distributes one database's documents across autonomous shards by document-ID prefix/bucket.
- **Sharding maturity:** relatively new; some features are unsupported on sharded databases ([unsupported list](https://ravendb.net/docs/article-page/6.0/csharp/sharding/unsupported)), and resharding is a managed operation. ⚠️ unverified — production track record of sharding at scale is limited; treat as newer than the core replication path.
- **Read replicas:** any node can serve reads; reads from a node may lag the writer (async replication) unless you wait-for-replication or use cluster-wide consistency.
- **Storage/compute separation:** no — shared-nothing nodes with local Voron storage. Not an Aurora/Neon-style design. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Voron uses a write-ahead log + copy-on-write B+trees; a committed single-node transaction is fsync'd to that node's WAL before acknowledging, so the crash data-loss window on a single node is small. **But** because document replication is async, a node failure after local commit and before replication can lose acknowledged writes for readers on other nodes. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Corax shifts work to indexing time for faster, more predictable query latency than Lucene, especially cold queries ([Corax article](https://ravendb.net/articles/corax-lucene-benchmarks-and-lies)). ⚠️ unverified — no independent p99 benchmarks reviewed; vendor numbers only.
- **Compaction/GC:** Voron compaction reclaims space; indexes rebuild in the background. Background indexing competes with write load and can lengthen the window of index staleness under heavy ingest.

## Operations & maturity
- **Backup/restore:** logical and snapshot backups, scheduled backups, and incremental backups to local/S3/Azure/GCS; point-in-time-style restore via incremental backup chains. ⚠️ unverified — exact PITR granularity not confirmed from primary docs here.
- **Observability:** built-in Studio (web admin UI) with query explain, index stats, ongoing-task monitoring, and metrics; integrates with monitoring via SNMP/Prometheus-style endpoints.
- **Upgrade story:** rolling upgrades across cluster nodes are supported; the Studio and stable on-disk format ease day-2 work. Single-binary deployment (.NET) keeps the operational surface small.
- **Maturity:** mature codebase (v1 circa 2010, full rewrite in 4.0), commercially backed by Hibernating Rhinos. **Known failure mode: the isolation gap surfaced by [Jepsen 6.0.2](https://jepsen.io/analyses/ravendb-6.0.2)** — silent lost updates under default settings and fractured reads even in the strongest mode. This is the single most important maturity caveat.

## Ecosystem & people
- **Canonical use cases:** .NET/C# application backends needing a document store with strong tooling, full-text search, and easy embedding of related data; small-to-mid clusters where developer velocity matters.
- **Anti-patterns:** workloads that require true serializable multi-key transactions or guaranteed no-lost-updates without app-level optimistic concurrency (given Jepsen findings); heavy ad-hoc analytics/OLAP; very large multi-petabyte sharded deployments where sharding is still maturing; teams outside the .NET ecosystem (Java/Python/Node clients exist but the center of gravity is .NET).
- **Drivers/connectors:** first-class .NET client (MIT-licensed), plus Java, Node.js, Python, Go, C++, PHP clients; ETL out to SQL, OLAP (Parquet/data lake), Elasticsearch, Kafka, RabbitMQ; Kafka/RabbitMQ "sinks" to ingest. CDC-style integration via the ETL/subscriptions mechanism.
- **Community/support:** smaller community than MongoDB/Postgres; commercial support and managed cloud from the vendor; docs are extensive but, per Jepsen, historically internally inconsistent on consistency semantics.

## Licensing & cost
- **License:** dual-licensed **AGPLv3 / commercial**; the server is AGPL or paid, and **client APIs were relicensed to MIT** (so embedding the driver doesn't trigger AGPL) ([Ayende on 4.0 licensing](https://ayende.com/blog/178434/ravendb-4-0-licensing-pricing)). A free **Community** tier runs fully-featured on limited resources. AGPL is copyleft, not source-available/SSPL — see [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** both — self-host (any cloud/on-prem) or **RavenDB Cloud** (managed, pay-as-you-go). Lock-in is moderate (RQL, Voron, JS index/ETL scripts are RavenDB-specific).
- **Cost model:** per-core commercial tiers (Professional/Enterprise); ⚠️ unverified figures — roughly ~$4.5K (Professional) to ~$7.9K (Enterprise) for a 6-core server per secondary sources; Cloud is consumption-based. Verify current pricing at [cloud.ravendb.net/pricing](https://cloud.ravendb.net/pricing).

## Hardware / deployment
- **Resource profile:** memory-sensitive (Voron mmaps data; OS page cache matters), disk-bound for write/index throughput; benefits from fast SSD/NVMe. Working set ideally fits in RAM for hot queries but data need not fully fit in memory.
- **Storage assumptions:** local fast disk preferred for Voron; tolerant of cloud block storage but fsync latency directly affects commit latency.
- **Footprint:** single-node, clustered, or embedded (can run in-process). Single self-contained .NET binary.
- **Deployment:** SaaS (RavenDB Cloud) or on-prem; container/Kubernetes-friendly though stateful (StatefulSet with persistent volumes; mind Voron's reliance on stable local storage).

## Bottom line
Reach for RavenDB if you are a .NET shop that wants a document database with excellent developer tooling, built-in full-text search, time series, and easy ETL, at small-to-mid cluster scale. Do **not** rely on its "ACID" branding for multi-key correctness: [Jepsen 6.0.2](https://jepsen.io/analyses/ravendb-6.0.2) found lost updates under default settings and fractured reads even in cluster-wide "serializable" mode, so safe concurrent updates require explicit optimistic concurrency and careful design. The single biggest gotcha is the gap between the marketed isolation guarantees and the tested behavior — plus the standing reminder that indexes are eventually consistent, so a write is not immediately queryable.

## Sources
- [Jepsen: RavenDB 6.0.2 (2024)](https://jepsen.io/analyses/ravendb-6.0.2)
- [RavenDB docs — Voron storage engine](https://docs.ravendb.net/7.2/server/storage/storage-engine/)
- [RavenDB docs — Corax search engine](https://ravendb.net/docs/article-page/6.0/csharp/indexes/search-engine/corax)
- [RavenDB docs — Cluster-wide transactions](https://docs.ravendb.net/7.1/server/clustering/cluster-transactions/)
- [RavenDB docs — Sharding overview](https://ravendb.net/docs/article-page/6.0/csharp/sharding/overview) and [unsupported features](https://ravendb.net/docs/article-page/6.0/csharp/sharding/unsupported)
- [RavenDB — CAP and ACID optimization strategies](https://ravendb.net/articles/cap-and-acid-optimization-strategies-for-database-consistency-and-availability)
- [RavenDB 6.0 features](https://ravendb.net/why-ravendb/ravendb-60-features) · [v6.0 launch](https://ravendb.net/articles/ravendb-version-6-0-is-now-live)
- [Ayende — RavenDB 4.0 licensing & pricing](https://ayende.com/blog/178434/ravendb-4-0-licensing-pricing)
- [RavenDB Cloud pricing](https://cloud.ravendb.net/pricing)
- [Wikipedia — RavenDB](https://en.wikipedia.org/wiki/RavenDB)
