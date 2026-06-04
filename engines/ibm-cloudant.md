---
name: IBM Cloudant
slug: ibm-cloudant
rank: 111
data_model: Document
license: Proprietary managed service (built on Apache CouchDB, Apache 2.0)
summary: Managed, CouchDB-compatible JSON document DBaaS on IBM Cloud, built for offline-first sync and eventual consistency.
last_researched: 2026-06-04
confidence: medium
---

# IBM Cloudant

> Fully managed, CouchDB-API-compatible JSON document database whose defining feature is master-master replication and offline-first sync — at the cost of eventual consistency and app-managed write conflicts.

## When to use

**Use IBM Cloudant if:**
- ✅ You want a hands-off, CouchDB-API-compatible JSON store and your killer requirement is robust offline-first replication/sync (mobile, edge, PouchDB).
- ✅ You need multi-region eventually-consistent JSON storage or IoT ingestion of independent documents, and your app can handle write conflicts in code.
- ✅ You want managed operations (IBM handles upgrades, backups, compaction) with a CouchDB escape hatch for self-hosting to avoid lock-in.

**Avoid IBM Cloudant if:**
- ❌ You need multi-document transactions, strong cross-region consistency, server-side joins, or ad-hoc analytics — atomicity is per single document only.
- ❌ You have high write contention on the *same* document — Cloudant silently accumulates conflicting revisions in `_conflicts` that your app must resolve or suffer bloat and "lost" updates (the biggest gotcha).
- ❌ You count on the FoundationDB-based Transaction Engine for in-region strong consistency — IBM de-funded it in 2022 and removed the docs; the mainstream engine remains eventually consistent.

## Identity
- **Taxonomy / data model:** [document-data-model](../concepts/document-data-model.md) store of schemaless JSON documents, each addressed by an `_id` and versioned by a `_rev`. API- and wire-compatible with [couchdb](couchdb.md); Cloudant is essentially CouchDB-as-a-service with IBM's clustering layer (historically BigCouch) on top.
- **Storage model:** append-only, copy-on-write B-tree per database file (the CouchDB on-disk format); writes never overwrite in place, which is what enables [mvcc](../concepts/mvcc.md) and crash-only design. Not [LSM](../concepts/lsm-vs-btree.md). A "Cloudant on Transaction Engine" variant — the commercial productization of the FoundationDB-based next-generation CouchDB (intended as CouchDB 4.x) — was announced in 2020, but **IBM de-funded the FoundationDB-based CouchDB rewrite in March 2022 and refocused on CouchDB 3.x** ([The Register, 2022-03-15](https://www.theregister.com/2022/03/15/ibm_cloudant_couchdb/)); the TE docs have since been removed from IBM's docs repo. Treat TE as a discontinued/legacy path, not a current default.
- **Workload:** OLTP-style document CRUD and sync; small point/range reads and writes, MapReduce/secondary-index queries. Not an analytics engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** Classic Cloudant (CouchDB lineage) is **AP** — it stays available and reconciles divergent writes later via conflict flagging rather than refusing writes ([CouchDB consistency docs](https://docs.couchdb.org/en/stable/intro/consistency.html)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition → favors Availability; Else → favors Latency over Consistency (eventually consistent quorum reads). ⚠️ unverified — PACELC is not stated in IBM's own terms; this is inferred from the documented eventual-consistency behavior.
- **Default isolation & what's achievable:** No multi-document transactions in classic Cloudant — atomicity is **per single document only**. Cloudant is **eventually consistent** across cluster nodes ([Cloudant MVCC / conflicts FAQ](https://github.com/ibm-cloud-docs/Cloudant/blob/master/faqs/document-version-conflicts-faq.md)). The **Transaction Engine** offering (announced 2020) claimed **in-region strong consistency** with read-your-writes and linearizable single-document operations, built on the FoundationDB-based next-gen CouchDB — FoundationDB itself provides strict serializability ([FoundationDB](https://apple.github.io/foundationdb/transaction-manifesto.html)). ⚠️ unverified — **IBM stopped funding the FoundationDB-based CouchDB in March 2022** ([The Register](https://www.theregister.com/2022/03/15/ibm_cloudant_couchdb/)) and removed the TE docs, so the current status of any in-production TE consistency guarantee is uncertain; do not assume TE is an available, supported option today. The default, mainstream Cloudant remains eventually consistent. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** master-master (multi-leader), asynchronous, document-level [replication](../concepts/replication-models.md). Each database is sharded with replicas (classic default N=3); reads/writes take quorum parameters (`r`, `w`). ⚠️ unverified — exact default quorum values; community testing on the BigCouch/CouchDB clustering layer reported consistency anomalies even at r=w=quorum ([BigCouch issue #55](https://github.com/cloudant/bigcouch/issues/55)).
- **Tunable consistency?** Yes — per-request `r`/`w` quorum parameters in the classic engine. Conflicts are not silently resolved correctly: when two replicas diverge, both pick the *same deterministic winner* but the loser is retained in `_conflicts`, and **the application must detect and merge** ([conflicts FAQ](https://github.com/ibm-cloud-docs/Cloudant/blob/master/faqs/document-version-conflicts-faq.md)). This is the single biggest operational gotcha.
- **Clock dependency:** No reliance on synchronized clocks for correctness; conflict winner selection is deterministic on revision data, not wall-clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** schema-on-read. Schemaless JSON; the schema lives in application code. No DDL, no `ALTER`, so "migrations" are application-driven document rewrites.
- **Migration/evolution:** adding fields is free; changing shape requires rewriting documents and rebuilding affected secondary indexes (a view rebuild scans the whole database and can be expensive).
- **Type system:** JSON scalars, arrays, nested objects. Geospatial querying is available (Cloudant Geo). No native vector type. No referential integrity / foreign keys.

## Query interface
- **Language:** HTTP/REST + JSON (the CouchDB API). Three query mechanisms: **Cloudant Query / Mango** (declarative, MongoDB-`find()`-inspired selectors; donated upstream as CouchDB Mango — [CouchDB Mango](https://blog.couchdb.org/2016/08/03/feature-mango-query/)), **MapReduce views** (JavaScript `map`/`emit`, the only path to aggregation — [Cloudant views](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-views-mapreduce)), and **Cloudant Search** (Lucene full-text, see [full-text-search](../concepts/full-text-search.md)).
- **Transactions:** single-document atomicity only. Bulk-update endpoint is *not* transactional. ⚠️ unverified — the discontinued Transaction Engine variant advertised in-region consistency, but db-engines and IBM docs describe Cloudant as supporting only atomic operations *within a single document*, with no general multi-document transactions; TE never became the mainstream offering and was de-funded in 2022.
- **Native vs app-side:** secondary indexes are native (Mango/views/search); **no server-side joins** — joins are app-side or via view-collation tricks. Aggregation only through MapReduce reduce functions.
- **Stored procedures / UDFs:** JavaScript design documents (map/reduce, validation `validate_doc_update`, show/list, update handlers). No general stored-procedure language.

## Scaling & topology
- **Vertical vs horizontal:** horizontal. Databases are sharded (Q shards) with N replicas across the cluster; the service scales by **provisioned throughput capacity** (reads/sec, writes/sec, global queries/sec) plus storage ([provisioned capacity FAQ](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-faq-provisioned-throughput-capacity-model)).
- **Sharding:** shard count is fixed at database creation (CouchDB limitation) — resharding means create-new-and-replicate, which is painful at scale. (CouchDB 3.x added a live shard-splitting API, but resharding remains a heavy operation.)
- **Read replicas / read consistency:** quorum reads from replicas may be stale (eventual consistency). Cross-region is achieved by configuring replication between separate Cloudant instances — explicitly eventual.
- **Storage/compute separation:** the mainstream engine couples storage and compute per node; the (now de-funded) FoundationDB-based Transaction Engine was designed to move toward separation. See [storage-compute-separation](../concepts/storage-compute-separation.md). ⚠️ unverified — degree of separation in the current managed offering.

## Performance & durability
- **Write path:** append-only writes to the per-database file; durability via replication to N replicas before/around acknowledging the configured `w` quorum. See [wal-and-durability](../concepts/wal-and-durability.md). Data-loss window depends on `w` and replica placement; a write acked at `w=1` can be lost if that node fails before replicating. ⚠️ unverified — IBM's fsync/group-commit specifics for the managed service.
- **Throughput/latency:** governed by provisioned capacity blocks (min Standard plan: 100 reads/s, 50 writes/s, 5 global queries/s — [pricing](https://github.com/ibm-cloud-docs/Cloudant/blob/master/offerings/pricing.md)); requests beyond the provisioned rate are **HTTP 429 throttled**, which is the dominant tail-latency surprise — p99 spikes come from rate limiting, not storage.
- **Compaction / GC:** append-only files require **compaction** to reclaim space from old revisions and deleted docs; the managed service handles this, but view index rebuilds and compaction can transiently affect performance. Old `_rev`s are not retained as a usable version history after compaction.

## Operations & maturity
- **Backup/restore:** IBM-managed continuous backups; logical backup via replication or `couchbackup` tooling. PITR is not a first-class CouchDB feature; recovery is replication/snapshot-based. ⚠️ unverified — managed PITR granularity.
- **Observability:** request metrics, IBM Cloud Monitoring integration, `_explain` for Mango query plans, active-task introspection for view builds/replication.
- **Upgrade story:** fully managed — IBM handles upgrades; no customer-side rolling-upgrade burden. Day-2 burden shifts to **application-level conflict handling** and capacity tuning.
- **Maturity:** mature lineage (Cloudant founded ~2010, acquired by IBM 2014; CouchDB dates to 2005). Known failure mode: **silent write conflicts** that accumulate in `_conflicts` if the app never resolves them, bloating documents and indexes. No official Jepsen report for Cloudant specifically; independent CouchDB/BigCouch testing flagged quorum/consistency anomalies ([jepsen-couchdb](https://github.com/garbados/jepsen-couchdb), [BigCouch #55](https://github.com/cloudant/bigcouch/issues/55)) — treat classic Cloudant as eventually consistent, not linearizable.

## Ecosystem & people
- **Canonical use cases:** offline-first and mobile/edge apps that sync (the PouchDB / CouchDB replication protocol is the headline feature), multi-region eventually-consistent JSON storage, IoT ingestion of independent documents.
- **Anti-patterns:** anything needing multi-document transactions, strong cross-region consistency, ad-hoc analytics/joins, or high write contention on the *same* document (guarantees conflict churn). Wrong tool for relational workloads or for reporting.
- **Drivers / connectors:** official SDKs (Node, Java, Python, Go), full PouchDB/CouchDB replication compatibility, Kafka/CDC via the `_changes` feed (the changes feed is a natural CDC source). BI/dbt integration is weak — not its niche.
- **Community / support:** rides the Apache CouchDB community for the core engine; IBM provides commercial support and SLAs. Docs are decent; the learning curve is the conflict/MVCC mental model, not the API.

## Licensing & cost
- **License:** the managed service is **proprietary**; the underlying engine is Apache CouchDB under **Apache 2.0** (permissive). No post-2018 relicensing of CouchDB itself. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Cloudant is **managed-only** on IBM Cloud. For self-hosting, run open-source CouchDB (compatible API) — that is the practical lock-in escape hatch.
- **Lock-in:** moderate — wire-compatible with CouchDB, so data and replication protocol are portable; IBM-specific features (capacity model, IAM, Transaction Engine internals) are not.
- **Cost model:** **provisioned throughput capacity** (per-block reads/writes/global-queries per second) + storage (per GB), pro-rated hourly; 99.95% SLA on Standard ([pricing FAQ](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-faq-pricing)). Cheap at small scale; cost can invert if you over-provision for peak rate or hit throttling and must buy headroom.

## Hardware / deployment
- **Resource profile:** I/O- and capacity-bound in practice (the provisioned rate is the real ceiling, not RAM). View building is CPU/IO heavy. Working set need not fit in RAM.
- **Storage assumptions:** SSD-backed managed storage; no customer storage tuning.
- **Footprint:** clustered managed service (single-tenant "Dedicated" and multi-tenant "Standard" isolation tiers). Not embedded; for embedded use the relative is PouchDB. See [embedded-databases](../concepts/embedded-databases.md).
- **Deployment:** SaaS on IBM Cloud only (no general k8s/on-prem deploy of Cloudant itself; CouchDB covers that case).

## Bottom line
Reach for Cloudant when you want a hands-off, CouchDB-compatible JSON store whose killer feature is robust offline-first replication/sync (mobile, edge, multi-region eventual consistency) and you are willing to handle write conflicts in application code. Do not reach for it if you need multi-document transactions, strong cross-region consistency, joins, or analytics — and do not count on the Transaction Engine's "in-region strong consistency", since IBM de-funded the underlying FoundationDB-based CouchDB in 2022. The single biggest gotcha: under concurrent updates Cloudant does not error — it silently accumulates conflicting revisions in `_conflicts`, and if your app never resolves them you get document bloat and "lost" updates that were actually just losing-side revisions.

## Sources
- [IBM Cloudant MVCC / document-version-conflicts FAQ](https://github.com/ibm-cloud-docs/Cloudant/blob/master/faqs/document-version-conflicts-faq.md)
- [The Register: IBM ends backing of FoundationDB version of CouchDB (2022)](https://www.theregister.com/2022/03/15/ibm_cloudant_couchdb/) (Transaction Engine / next-gen CouchDB de-funded; IBM's TE docs have since been removed)
- [IBM Cloudant pricing](https://github.com/ibm-cloud-docs/Cloudant/blob/master/offerings/pricing.md) and [pricing FAQ](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-faq-pricing)
- [IBM Cloudant provisioned throughput capacity model FAQ](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-faq-provisioned-throughput-capacity-model)
- [IBM Cloudant MapReduce views](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-views-mapreduce)
- [Apache CouchDB eventual consistency](https://docs.couchdb.org/en/stable/intro/consistency.html)
- [CouchDB Mango query feature](https://blog.couchdb.org/2016/08/03/feature-mango-query/)
- [FoundationDB transaction manifesto (strict serializability)](https://apple.github.io/foundationdb/transaction-manifesto.html)
- [jepsen-couchdb (community)](https://github.com/garbados/jepsen-couchdb) and [BigCouch consistency issue #55](https://github.com/cloudant/bigcouch/issues/55)
