---
name: RethinkDB
slug: rethinkdb
rank: 114
data_model: Document
license: Apache 2.0 (permissive; relicensed 2017 from AGPLv3)
summary: Pioneering real-time JSON document DB whose changefeeds push live query updates; technically solid but commercially dead — now a community/Linux Foundation project.
last_researched: 2026-06-04
confidence: high
---

# RethinkDB

> The first mainstream "push" database — its changefeeds stream live query result deltas to clients — but the company shut down in 2016, and despite an Apache relicense it remains a niche, low-momentum project.

## When to use

**Use RethinkDB if:**
- ✅ You specifically want live, composable query subscriptions (changefeeds) for real-time apps — live dashboards, collaborative/multiplayer apps, chat, presence.
- ✅ You want a schemaless JSON document store with unusually rich server-side joins, aggregations, and secondary indexes via ReQL.
- ✅ It is a self-hosted, low-stakes context where you can accept an essentially unmaintained project.

**Avoid RethinkDB if:**
- ❌ It is a new production system in 2026 — the company died in 2016, there is no commercial backing, and you are betting against the calendar.
- ❌ You need multi-document transactions, heavy analytics, very high write throughput, or a managed cloud offering.
- ❌ You rely on default linearizability — `read_mode=single` (the default) is *not* linearizable; you must combine `majority` read + `majority` acks + `hard` durability.

## Identity
- **Taxonomy / data model:** distributed JSON document store. Schemaless documents, organized in tables and databases. The headline feature is **changefeeds**: subscribe to a query and receive a stream of changes as the underlying data mutates ([changefeeds docs](https://rethinkdb.com/docs/changefeeds/ruby/)).
- **Storage model:** custom log-structured storage engine with a B-tree index layer, inspired by BTRFS; uses block-level [mvcc](../concepts/mvcc.md) (snapshots the B-tree per shard so reads and writes proceed concurrently) ([dbdb.io](https://dbdb.io/db/rethinkdb)). On-disk format is RethinkDB-proprietary, not [LSM](../concepts/lsm-vs-btree.md).
- **Workload:** OLTP-ish document store optimized for **real-time read-heavy push workloads**, not analytics. Map/reduce-style aggregations exist but it is not an OLAP/HTAP engine — no columnar store, no separate analytic replica. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** with majority writes — a primary that loses quorum stops accepting writes; an arbitrary voting replica is elected primary when more than half the voting replicas survive ([consistency docs](https://rethinkdb.com/docs/consistency/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition → C (refuses minority writes); Else → tunable, defaults toward **Latency** because the default read mode is `single` (in-memory primary read) and only `majority` read trades latency for consistency.
- **Default isolation & what's achievable:** **single-document linearizability only** — and only when you combine `write_acks=majority` + `durability=hard` + `read_mode=majority`. RethinkDB guarantees "linearizability of individual atomic operations on individual documents," explicitly *not* multi-key transactions ([consistency docs](https://rethinkdb.com/docs/consistency/)). There is no general multi-document transaction / serializable mode; "ACID" here means per-document atomicity, not [serializable](../concepts/isolation-levels.md). Note the default `read_mode=single` returns primary in-memory values and is **not** linearizable.
- **Replication:** **single-leader (primary replica) per shard**; failover uses **Raft** for cluster membership / table config and primary election ([Jepsen 2.2.3](https://jepsen.io/analyses/rethinkdb-2-2-3-reconfiguration); the public docs describe the behavior but [do not name Raft](https://rethinkdb.com/docs/consistency/)). Writes are async to secondaries; acknowledgement waits for a majority of voting replicas by default. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency:** yes — per-query `read_mode` (`single` / `majority` / `outdated`) and per-table `write_acks` (`majority` / `single`) and `durability` (`hard` / `soft`).
- **Clock dependency:** none for correctness (Raft term/log based, not [clock-based](../concepts/clocks-and-time.md)).

## Schema
- **Schema-on-read:** schemaless JSON documents; schema lives in application code. No `ALTER`-style migrations because there is no enforced schema; you reshape documents in app logic / update queries.
- **Migration/evolution:** index creation is online (background); changing sharding/replication is a live reconfiguration (the operation Jepsen found buggy in 2.2.3 — see below).
- **Type system:** JSON types plus binary objects, native **geospatial** types and geo indexes, and date/time. No native vector type. Secondary indexes are first-class (simple, compound, multi, and arbitrary-function indexes).

## Query interface
- **Language:** **ReQL**, an embedded DSL that chains methods in the host language (official drivers: JavaScript/Node, Python, Ruby, Java). Not SQL. Queries are composed as language expressions, not strings — reduces injection risk but means no SQL tooling compatibility.
- **Transactions:** **single-document atomicity only**; no multi-statement / multi-document ACID transactions.
- **Native vs app-side:** native server-side **joins** (eqJoin, innerJoin, outerJoin), aggregations, map/reduce, and secondary indexes — unusually rich for a NoSQL document store. Subqueries and changefeeds compose in ReQL.
- **Stored procedures / UDFs:** no stored procedures; logic is expressed inline in ReQL, including anonymous functions written in the driver language.

## Scaling & topology
- **Horizontal:** **range-sharded** tables (auto-split by key range) with configurable replica count per table. Resharding triggers data movement and is a live cluster reconfiguration — historically the fragile path.
- **Read replicas:** secondaries can serve reads; `read_mode=outdated` reads from any replica (may be stale), `majority` reads are consistent but slower, `single` reads only from the primary.
- **Storage/compute separation:** no — shared-nothing nodes own their storage. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) design.

## Performance & durability
- **Write path:** per-table `durability=hard` (default) commits to disk before ack; `soft` acks before fsync, creating a **data-loss window** on crash. Docs warn that writes run in `single`/`soft` mode "might be lost" after failures ([consistency docs](https://rethinkdb.com/docs/consistency/)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** the architecture favors low-latency real-time pushes over raw write throughput; ⚠️ unverified — no current authoritative p99 benchmarks; the project is largely dormant so published numbers predate modern hardware.
- **Compaction / GC:** log-structured engine performs background garbage collection of stale blocks; ⚠️ unverified — limited recent data on its p99 impact under sustained write load.

## Operations & maturity
- **Backup/restore:** `rethinkdb dump`/`restore` (logical, archive-based); no built-in continuous PITR. Snapshotting is the consistent-snapshot ([mvcc](../concepts/mvcc.md)) used internally, not an operator backup feature.
- **Observability:** built-in web admin UI with cluster/table status, an integrated data explorer, and per-table stats; ReQL has no `EXPLAIN`-equivalent as rich as SQL planners.
- **Upgrade story:** rolling upgrades across the cluster; day-2 burden is now dominated by the project being **effectively unmaintained at production-grade pace** (no commercial vendor).
- **Maturity / Jepsen:** **two Jepsen reports.** [2.1.5 (2016)](https://aphyr.com/posts/329-jepsen-rethinkdb-2-1-5) confirmed linearizable single-key ops under majority read+write with hard durability through partitions — a genuinely good result. [2.2.3 reconfiguration (2016)](https://jepsen.io/analyses/rethinkdb-2-2-3-reconfiguration) found **nonlinearizable histories** (stale reads, illegal CAS, lost acknowledged writes) when randomized partitions coincided with cluster reconfiguration, traced to a Raft node-ID reuse bug violating Raft's stable-storage assumption; **patched in 2.2.4**.

## Ecosystem & people
- **Canonical use cases:** real-time apps — live dashboards, multiplayer/collaborative apps, chat, presence, leaderboards — where changefeeds replace polling or a separate pub/sub layer.
- **Anti-patterns:** anything needing multi-document transactions, heavy analytics, very high write throughput, or a long-supported managed cloud offering. Picking it new in 2026 carries serious **abandonment / talent-availability risk**.
- **Drivers / connectors:** official JS/Python/Ruby/Java drivers plus many community drivers (Go, etc.). Sparse modern CDC/Kafka/dbt/BI integration — changefeeds are the native "CDC," but third-party connector support is thin and aging.
- **Community:** small, post-shutdown volunteer community under the Linux Foundation. Docs quality is good (a legacy of the original team). Learning curve: easy ReQL onramp; small operational team viable but unsupported.

## Licensing & cost
- **License:** **Apache 2.0** (permissive). Originally **AGPLv3** (strong copyleft), **relicensed to Apache 2.0 in February 2017** after CNCF purchased the source and contributed it to the Linux Foundation ([CNCF announcement](https://www.cncf.io/blog/2017/02/06/cncf-purchases-rethinkdb-source-code-contributes-linux-foundation-apache-license/)). A rare *loosening* of license post-2018-era trend. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed only:** no first-party managed service; no major cloud offers a managed RethinkDB. Self-host on your own infra.
- **Cost model:** free OSS; cost is purely your infrastructure + the operational/risk cost of running unmaintained software.

## Hardware / deployment
- **Resource profile:** benefits from RAM for the working set and primary in-memory reads (`single` mode reads from memory), but does not require the full dataset in RAM; disk-bound for durable writes.
- **Storage assumptions:** local disk per node (shared-nothing); fsync latency matters for `hard` durability — NVMe/local SSD preferred over high-latency network storage.
- **Footprint:** clustered shared-nothing or single-node; not embedded, not serverless.
- **Deployment:** self-hosted on-prem / VMs / containers; community Docker images exist. ⚠️ unverified — no first-party Kubernetes operator; StatefulSet deployment is community-driven.

## Bottom line
Reach for RethinkDB only if you want its specific superpower — **live, composable query subscriptions (changefeeds)** — in a self-hosted, low-stakes context and accept that the project is essentially in maintenance limbo. It earned a clean Jepsen result for single-key linearizability under majority settings, so the core is sound, but the **defaults (`read_mode=single`) are not linearizable** and there are no multi-document transactions. The single biggest gotcha is non-technical: the company died in 2016, there is no commercial backing, and starting a new production system on it in 2026 is a bet against the calendar — modern alternatives (Postgres LISTEN/NOTIFY + logical replication, [MongoDB](mongodb.md) change streams, Supabase Realtime) cover the changefeed use case with live ecosystems.

## Sources
- [RethinkDB consistency guarantees (official docs)](https://rethinkdb.com/docs/consistency/)
- [RethinkDB changefeeds (official docs)](https://rethinkdb.com/docs/changefeeds/ruby/)
- [RethinkDB FAQ (official)](https://rethinkdb.com/faq)
- [Jepsen: RethinkDB 2.1.5 (Aphyr, 2016)](https://aphyr.com/posts/329-jepsen-rethinkdb-2-1-5)
- [Jepsen: RethinkDB 2.2.3 reconfiguration (2016)](https://jepsen.io/analyses/rethinkdb-2-2-3-reconfiguration)
- [CNCF purchases RethinkDB source, relicenses Apache 2.0 (2017)](https://www.cncf.io/blog/2017/02/06/cncf-purchases-rethinkdb-source-code-contributes-linux-foundation-apache-license/)
- [RethinkDB is shutting down (company blog, 2016)](https://rethinkdb.com/blog/rethinkdb-shutdown/)
- [Database of Databases — RethinkDB](https://dbdb.io/db/rethinkdb)
- [RethinkDB — Wikipedia](https://en.wikipedia.org/wiki/RethinkDB)
