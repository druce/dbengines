---
name: Datomic
slug: datomic
rank: 150
data_model: Relational (immutable, time-aware; Datalog)
license: Apache-2.0 (binaries only; source-available NO — closed-source, free of charge)
summary: Immutable, time-travel relational DB with Datalog queries, a single-writer transactor, and query logic embedded in the application process.
last_researched: 2026-06-04
confidence: high
---

# Datomic

> An append-only, immutable database where every change is a timestamped fact (datom), queries run *inside your app* as a library, and you can query the database "as of" any past instant — at the cost of a single global writer.

## When to use

**Use Datomic if:**
- ✅ History, auditability, and "as-of" time travel are first-class requirements (finance, healthcare, compliance — where the audit log *is* the product).
- ✅ Your workload is read-heavy with moderate write volume, and you value reads that run in-process against cached immutable indexes.
- ✅ Your team is comfortable with Clojure and Datalog and wants one of the few databases with a clean Jepsen result (isolation stronger than its docs claim).

**Avoid Datomic if:**
- ❌ You have high write throughput — the single transactor serializes all writes and is a hard ceiling.
- ❌ You need large-scale OLAP/analytics, blob/time-series ingestion, or geospatial/vector workloads.
- ❌ You compose transaction functions expecting serializability — within one transaction they execute against the start-of-transaction snapshot and can silently violate invariants.

## Identity
- **Taxonomy / data model:** Relational, but modeled as immutable **datoms** — five-tuples of `[entity, attribute, value, transaction, added?]`. Closer to RDF/EAV than to a table-and-row store. Queried with **Datalog** (a logic query language), not SQL. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Not a row- or column-store in the usual sense. Datomic keeps four covering index trees sorted in different orders — **EAVT** (row-like), **AEVT** (column-like), **AVET** (value lookup), **VAET** (reverse refs / graph navigation) — persisted as immutable, structurally-shared sorted trees in a pluggable backing store ([docs](https://docs.datomic.com/datomic-overview.html)). Because nodes are immutable, it behaves like a copy-on-write persistent data structure rather than [LSM or in-place B-tree](../concepts/lsm-vs-btree.md) mutation; there is no overwrite and no [mvcc](../concepts/mvcc.md)-style vacuum of old versions — old facts are retained by design.
- **Workload:** OLTP-leaning with strong read scaling; **not** an analytics/OLAP engine and not HTAP. Writes are serialized through one transactor (low write throughput); reads scale out across many peers/clients. Good for read-heavy transactional apps that value history and auditability.

## Distribution & consistency
- **CAP under partition:** Effectively **CP**. Writes go through a single active transactor backed by a storage service whose conditional-put / compare-and-set provides the safety boundary; if the writer or storage is unreachable, writes stop rather than diverge. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Partition → sacrifices availability of writes (CP). Else → tunable: `d/sync`/`db-after` gives you strict freshness at higher latency, while ordinary peer reads serve cached immutable data at very low latency, trading recency for speed.
- **Default isolation & what's achievable:** All transactions are **serialized in a single total order** by the lone transactor, so the inter-transaction isolation is **serializable** — and Jepsen found it stronger than documented: histories were Serializable, single-peer sessions were **Strong Session Serializable**, and write-only / `d/sync` reads were **Strict (Strong) Serializable** ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)). See [isolation-levels](../concepts/isolation-levels.md). **The real gotcha is intra-transaction:** transaction functions within a single transaction all see the database *as of the start* (concurrent, not serial). Two `:db/cas` on the same attribute both observe the original value; multiple increments collapse into one. Jepsen demonstrated a "pseudo write-skew" where one transaction both approved and denied a grant because the two functions produced non-conflicting assertions ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)).
- **Replication:** Single-leader writes. The transactor writes durably to a shared storage service (which itself may be replicated). A **standby transactor** takes over on failover. Jepsen noted the "single writer" claim is slightly inaccurate: during failover a standby and a still-live transactor can briefly run concurrently, but storage's compare-and-set under sequential consistency prevents safety violations ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Per-read, yes: peers/clients read consistent local immutable snapshots; call `d/sync` (or transact) when you need to be guaranteed current.
- **Clock dependency:** Correctness does **not** rest on synchronized wall clocks; ordering comes from the single transactor and storage CAS, not timestamps. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, but flexible/sparse:** attributes must be declared (value type + cardinality) before use, yet *any entity can have any attribute* — there are no rigid tables. Closer to a typed EAV graph than to fixed relations.
- **Migration/evolution:** Adding attributes is a normal transaction — no table rewrite, no lock; new attributes are simply new facts. You cannot retroactively change an attribute's type/cardinality freely, and because data is immutable, "removing" data means **retraction** (a new fact) or `excision` for true deletion (e.g., GDPR).
- **Type system:** scalars (long, bigint, double, bigdec, boolean, instant, uuid, string, keyword), byte arrays, refs (entity references — first-class for graph-like navigation), components, tuples, and cardinality-many sets. No native geospatial or vector types.

## Query interface
- **Language:** **Datalog** (Clojure-data syntax), plus a pull API for hierarchical entity fetch and a low-level index/`datoms` API. Not SQL. Recursive rules make graph/tree traversal natural.
- **Transactions:** full **multi-statement ACID**, atomic, serialized in a total order ([docs](https://docs.datomic.com/datomic-overview.html)). Writes are assert/retract of datoms; transaction functions run server-side for read-modify-write atomicity (with the concurrent-within-tx caveat above).
- **Native vs app-side:** joins, aggregations, and recursive rules are native to Datalog and execute **in the application process** (peer/client) against cached indexes — the query engine is a library, not a server. All four index orders give native, declared-free secondary access.
- **Stored procedures / UDFs:** **transaction functions** and query functions written in **Clojure/Java**, executing in the transactor (tx fns) or peer (query fns).

## Scaling & topology
- **Vertical vs horizontal:** **Writes scale vertically only** — "only one transaction can occur at a time in a given database" ([docs](https://docs.datomic.com/datomic-overview.html)); the transactor is a throughput ceiling. **Reads scale horizontally and trivially** because immutable data can be copied into any number of peers/caches.
- **Sharding:** No write sharding within a database. Horizontal scale comes from many readers, not partitioned writers; very large write volume is the classic anti-pattern. To scale writes you split into multiple databases (app-level).
- **Read replicas / consistency:** Every peer is effectively a consistent read replica holding cached immutable segments; reads are snapshot-consistent and you opt into freshness with `d/sync`.
- **Storage/compute separation:** Yes, strongly. Storage is a pluggable backing service; the transactor (write) and peers/clients (read+query) are separate compute. **Datomic Pro** supported pluggable storage (e.g., DynamoDB, relational SQL, Cassandra-class stores); **Datomic Cloud** is AWS-native, automating transactor nodes, SSD caches, Auto Scaling groups, load balancers, and Lambda/**Ions** application entry points ([docs](https://docs.datomic.com/datomic-overview.html)). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Transactions are **flushed to durable storage before the client is acknowledged** ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)), so the crash data-loss window is effectively nil for acked writes — durability is delegated to the storage service's own fsync/replication. See [wal-and-durability](../concepts/wal-and-durability.md). Jepsen found **no durability bugs**.
- **Throughput/latency:** Reads are very low latency (in-process queries over local cache, no network round trip per query). **Write throughput is intentionally bounded** by the single serial transactor. p99 read latency depends on cache warmth — a cold peer must fetch index segments from storage; a warm peer is memory-fast.
- **Compaction / GC:** No overwrite-in-place, so no vacuum of dead row versions. Background **indexing** periodically merges the in-memory log into the persistent index trees; immutable segments are garbage-collected once unreferenced. History accumulates unless you explicitly excise — storage grows with change volume.

## Operations & maturity
- **Backup/restore, PITR:** Backup/restore is supported; **point-in-time is intrinsic** — `d/as-of`, `d/since`, and the full history view let you query any past state without a special PITR mechanism. That time-travel is the headline feature.
- **Observability:** metrics callbacks, transactor/peer logs, and query introspection; queries are ordinary data structures you can inspect. No SQL `EXPLAIN`, but the Datalog engine and `datoms`/index APIs are transparent.
- **Upgrade story / day-2:** Pro requires you to run and supervise transactors (primary + standby) and provision storage and caches yourself. Jepsen flagged that a transactor will **self-terminate after a short timeout (default ~5s) of storage connectivity loss**; the documented mitigation is a supervisor/daemon to restart it ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)). Cloud automates most of this on AWS.
- **Maturity:** Production since ~2012; battle-tested at scale at **Nubank** (which acquired Cognitect and owns Datomic). The **Jepsen report (2024) found no safety bugs** and behavior stronger than documented ([Jepsen 2024](https://jepsen.io/analyses/datomic-pro-1.0.7075)) — a rare clean result. Known failure modes are conceptual (single-writer throughput; intra-transaction concurrent semantics) rather than correctness defects.

## Ecosystem & people
- **Canonical use cases:** read-heavy transactional systems needing auditability, full history, and "what did we know at time T" — finance, healthcare, compliance, anything where the audit log *is* the product. The Clojure community is the core constituency.
- **Anti-patterns:** high-write-throughput workloads (single transactor), large-scale analytics/OLAP, blob/time-series ingestion, geospatial or vector workloads, and teams unwilling to adopt Clojure/Datalog. If you need to delete/overwrite at high volume, the immutable model fights you.
- **Drivers / connectors:** Native Clojure (peer/client libraries) and a Java API; Cloud exposes Ions and Lambda entry points. CDC-by-design via the transaction log (you can subscribe to the tx stream). Limited mainstream ORM/BI/dbt/Kafka tooling compared to SQL engines — ecosystem is smaller and Clojure-centric.
- **Community / support / docs:** small but devoted community; **commercial support from Nubank**; documentation is good and design-paper-quality. Learning curve is steep for SQL-trained teams (Datalog + immutability + in-process query model).

## Licensing & cost
- **License:** Since **April 2023** all editions are **free of licensing fees**; binaries are distributed under **Apache-2.0** via Maven Central / AWS Marketplace ([Datomic blog, Apr 2023](https://blog.datomic.com/2023/04/datomic-is-free.html); [Nubank](https://building.nubank.com/datomic-is-available-free-of-licensing-fees/)). **Critical nuance:** this is *not* open source — the Apache-2.0 grant covers the **object/binary form only**; the source remains **closed and developed privately at Nubank** ([Datomic blog](https://blog.datomic.com/2023/04/datomic-is-free.html)). Free-of-charge ≠ source-available. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Pro is self-managed anywhere; Cloud is AWS-only and operationally managed via CloudFormation. **Cloud is AWS lock-in**; Pro lock-in is via Datalog + the immutable model rather than license.
- **Cost model:** software is now $0; you pay only for infrastructure (storage service, transactor/peer compute, caches) and optional Nubank enterprise support. At scale, cost tracks your storage growth (history is retained) and read fleet size.

## Hardware / deployment
- **Resource profile:** memory-bound on the read side — peers cache index segments in RAM (and SSD on Cloud); a large cache / working set in memory is what makes reads fast. The transactor is modest but is the write bottleneck.
- **Storage assumptions:** delegated to the backing service; SSD-backed caches strongly recommended (Cloud uses SSD-backed valcaches). Tolerant of network-attached storage since durability lives in the storage service.
- **Footprint:** clustered/distributed (transactor + peers + storage), not embedded and not single-binary. Datomic Cloud is effectively serverless-on-AWS for the operator.
- **Deployment:** Pro on-prem or any cloud; Cloud is SaaS-like but inside *your* AWS account (CloudFormation, Auto Scaling, ALB, Lambda/Ions). Not a typical k8s StatefulSet target — Cloud assumes native AWS primitives.

## Bottom line
Reach for Datomic when history, auditability, and "as-of" time travel are first-class requirements, your write volume is moderate, your reads dominate, and your team is comfortable with Clojure and Datalog — it is one of very few databases with a *clean* Jepsen result and isolation stronger than its own docs claim. Avoid it for write-heavy, analytics, geospatial/vector, or non-Clojure shops. **Biggest gotcha:** the single transactor caps write throughput, and within a single transaction, functions execute against the start-of-transaction snapshot concurrently — composing transaction functions can silently violate invariants you'd assume serializability protects.

## Sources
- [Datomic Overview (official docs)](https://docs.datomic.com/datomic-overview.html)
- [Jepsen: Datomic Pro 1.0.7075 (2024)](https://jepsen.io/analyses/datomic-pro-1.0.7075)
- [Datomic is Free (Datomic blog, Apr 2023)](https://blog.datomic.com/2023/04/datomic-is-free.html)
- [Datomic Cloud is Free (Datomic blog, Jun 2023)](https://blog.datomic.com/2023/06/datomic-cloud-is-free.html)
- [Datomic is available free of licensing fees (Nubank)](https://building.nubank.com/datomic-is-available-free-of-licensing-fees/)
- [Database of Databases — Datomic](https://dbdb.io/db/datomic)
