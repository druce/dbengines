---
name: CouchDB
slug: couchdb
rank: 61
data_model: Document
license: Apache License 2.0 (permissive)
summary: HTTP/JSON document store built around bidirectional replication and offline-first sync; AP, eventually consistent, app-resolved conflicts.
last_researched: 2026-06-04
confidence: high
---

# CouchDB

> An Erlang document database whose entire design centers on multi-master replication and offline-first sync — choose it when devices/sites must work disconnected and reconcile later, not when you need cross-document transactions or rich queries.

## When to use

**Use CouchDB if:**
- ✅ You need offline-first mobile/edge clients (with PouchDB) that take local writes and reconcile later via the CouchDB Replication Protocol.
- ✅ You want multi-master, partition-tolerant availability across sites that each accept local writes.
- ✅ Your documents are self-contained content/config records and you can consume changes via the resumable `_changes` feed.

**Avoid CouchDB if:**
- ❌ You need multi-document transactions — "ACID" here is per-document only; concurrent edits surface as conflicts your app must detect and resolve.
- ❌ You need joins, ad hoc analytical queries, or strong/linearizable consistency (it is AP, eventually consistent).
- ❌ You need low-latency, high-throughput OLTP — the HTTP-per-operation model and JS view server add overhead.

## Identity
- **Taxonomy / data model:** schemaless JSON document store; documents are addressed by ID and carry an explicit `_rev` revision token. Each document version is immutable. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** per-database **append-only B-tree** keyed by document ID and by an update-sequence ID; index/data updates are written only at the end of the file ([overview](https://docs.couchdb.org/en/stable/intro/overview.html)). Not LSM and not in-place B-tree updates — see [lsm-vs-btree](../concepts/lsm-vs-btree.md). Old revisions accumulate until [compaction](https://docs.couchdb.org/en/stable/intro/overview.html) rewrites the file. On-disk format is the `.couch` file plus separate view-index files.
- **Workload:** OLTP-ish single-document reads/writes and sync; **not** an analytics engine. No HTAP claim — ad hoc aggregation is done through precomputed MapReduce views, not interactive scans.

## Distribution & consistency
- **CAP under partition:** **AP** — it stays available and reconciles later; data is only [eventually consistent](https://docs.couchdb.org/en/stable/intro/consistency.html). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition it favors Availability; Else it favors Latency over Consistency (quorum reads/writes use only a configurable subset of replicas). Unverified-flag: ⚠️ unverified — CouchDB has no formal PACELC self-classification; this is inferred from its documented AP + tunable-quorum behavior.
- **Default isolation & what's achievable:** **document-level ACID only** ([overview](https://docs.couchdb.org/en/stable/intro/overview.html)) — a single-document add/edit/delete is all-or-nothing via [mvcc](../concepts/mvcc.md). There are **no multi-document transactions** and no snapshot/serializable isolation across documents. The "ACID" label is true per-document but does **not** mean cross-document atomicity — treat that divergence as the key gotcha. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** **multi-master / bidirectional** incremental replication over HTTP; asynchronous. Concurrent edits produce **conflicts, not silent overwrites** — CouchDB deterministically picks a "winning" revision (the branch with the longest revision history, ties broken by highest revision-ID sort order — *not* by timestamp or "latest" edit) but preserves losers in the document's revision history for the app to resolve ([replication & conflict model](https://docs.couchdb.org/en/stable/replication/conflicts.html)). Failover/split-brain: every node keeps serving; "split-brain" is the normal operating mode and is resolved by replication + app-side conflict handling. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Yes within a single cluster: per-request `r` and `w` quorum parameters over `n` shard replicas (defaults `n=3`, `r=w=2`) ([sharding docs](https://docs.couchdb.org/en/stable/cluster/sharding.html)). Note: `_view`, `_find`, and `_search` read only **one** copy regardless of `r` (effective quorum of 1).
- **Clock dependency:** none for correctness — conflict-winner selection is deterministic over revision-history length and revision-ID sort order, not timestamps. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** No declared schema; structure lives in application code and in view/Mango index definitions.
- **Migration/evolution:** no `ALTER`; you change shape by writing new document fields and (optionally) migrating documents lazily. Adding a new MapReduce view triggers a full index build on first query.
- **Type system:** standard JSON types plus binary **attachments** stored alongside documents. No native geospatial/vector/interval types (geo via the deprecated GeoCouch extension or app-side; ⚠️ unverified — no first-class vector index).

## Query interface
- **Language:** HTTP/REST is the primary API (every operation is a URL). Two query layers: **MapReduce views** (JavaScript or Erlang map/reduce in design documents, incrementally materialized) and **Mango** — a JSON declarative query (`_find`) modeled on MongoDB's query syntax with secondary indexes. Full-text search is optional and add-on: the legacy Clouseau/Dreyfus (`_search`) and, since 3.4, **Nouveau** — a from-scratch Lucene-based engine (Java 21) intended to replace it ([Nouveau docs](https://docs.couchdb.org/en/stable/ddocs/nouveau.html)).
- **Transactions:** single-document atomicity only; no multi-statement/multi-document ACID.
- **Native vs app-side:** **no server-side joins**; joins are done by view emit-key collation tricks or in the app. Aggregations come from MapReduce reduce functions, not ad hoc SQL. Secondary indexes are native (views and Mango indexes), and are sharded.
- **Stored procedures / UDFs:** map/reduce functions, `_update` and `_show`/`_list` handlers, and validation functions — written in **JavaScript** (Erlang and other query servers possible).

## Scaling & topology
- **Vertical & horizontal.** Native clustering since 2.0 (the BigCouch merge): databases are split into `q` shards, each replicated `n` times across nodes, using a Dynamo-style ring with quorum reads/writes ([sharding docs](https://docs.couchdb.org/en/stable/cluster/sharding.html)).
- **Sharding:** shard count `q` is fixed at database creation; **resharding is painful** (historically required recreating the DB; live shard splitting was added in 3.x but rebalancing remains a manual, operationally heavy task). ⚠️ unverified — exact 3.x reshard automation maturity.
- **Read replicas / read consistency:** all replicas are writable peers, not read-only followers; reads honor the `r` quorum, so a read may return stale or conflicting data depending on quorum and replication lag.
- **Storage/compute separation:** none — shared-nothing nodes own local disk. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** crash-only, **append-only** writes; a commit flushes document/index data then writes the DB header twice in duplicate 4 KB blocks, so a surviving header guarantees coherency after a crash ([overview](https://docs.couchdb.org/en/stable/intro/overview.html)). Since 3.0 the old `delayed_commits` batching option was **removed — all writes are now full commits** (fsync'd before the write is acknowledged), closing the data-loss window that existed when `delayed_commits=true` was the historical default; `/_ensure_full_commit` is retained as a no-op for old replicators ([3.0 release notes](https://docs.couchdb.org/en/stable/whatsnew/3.0.html)). See [wal-and-durability](../concepts/wal-and-durability.md). (There is no separate WAL — the data file *is* the log.)
- **Throughput/latency profile:** moderate; the HTTP-per-operation model and JavaScript view server add overhead. Not built for high-throughput OLTP or low p99 under heavy write load.
- **Compaction/GC:** old revisions and tombstones accumulate and must be reclaimed by **compaction**, which rewrites the file to a new copy while staying online ([overview](https://docs.couchdb.org/en/stable/intro/overview.html)). Compaction is I/O- and space-intensive (needs room for a second copy) and is a common day-2 p99 / disk-usage pain point. View indexes need separate compaction.

## Operations & maturity
- **Backup/restore:** file-level copy of `.couch` files (with care), or replicate to another instance as a live backup. No built-in PITR; point-in-time recovery is approximated via replication targets.
- **Observability:** `/_stats`, `/_active_tasks`, per-node metrics, and the **Fauxton** web UI for inspecting nodes, shards, and cluster status; `_explain` for Mango queries.
- **Upgrade:** rolling upgrades across a cluster are supported within a major line; cross-major upgrades (e.g. 1.x→2.x→3.x) historically required dump/reload or replication.
- **Maturity:** mature (created 2005, top-level Apache project), production-proven at CERN, United Airlines in-flight systems, and as the engine behind IBM Cloudant. **Jepsen:** no official jepsen.io analysis exists; the independent [awreece/jepsen-couchdb](https://github.com/awreece/jepsen-couchdb) test (an old, version-unpinned experiment) confirms the expected behavior — under partition CouchDB is AP and returns/accepts divergent values that must be reconciled (the experiment reported significant data "loss"/inaccessibility under concurrent updates), i.e. it does not provide linearizability and never claimed to. ⚠️ unverified — no modern, version-pinned Jepsen analysis of clustered CouchDB exists.

## Ecosystem & people
- **Canonical use cases:** offline-first mobile/edge apps that sync when reconnected; multi-datacenter or multi-site masters that each take local writes; content/config stores where documents are self-contained. The killer feature is the **CouchDB Replication Protocol**, shared with **[pouchdb](pouchdb.md)** (in-browser/in-device) for transparent client↔server sync.
- **Anti-patterns:** anything needing multi-document transactions, foreign keys/joins, ad hoc analytical queries, strong/linearizable consistency, or low-latency high-throughput OLTP — reach for [postgresql](postgresql.md), a quorum store like [apache-cassandra](apache-cassandra.md), or a stronger document DB like [mongodb](mongodb.md) instead.
- **Drivers/connectors:** the HTTP API means any HTTP client works; mature libraries across languages; PouchDB for JS; CDC-like consumption via the `_changes` feed (a first-class, resumable change stream). BI/dbt integration is weak — it is not a SQL warehouse.
- **Community/support:** active Apache community; commercial support and managed hosting historically via IBM Cloudant (API-compatible). Docs are good; learning curve is the conflict/replication mental model, not the API.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable; managed option is IBM Cloudant (Cloudant adds proprietary features like search and query enhancements → some lock-in if you depend on them).
- **Cost model:** OSS is free (compute + disk you provision); Cloudant is consumption-based (provisioned throughput / per-request + storage). Disk cost is notable because of revision retention and compaction headroom.

## Hardware / deployment
- **Resource profile:** **disk-bound** (append-only growth + compaction needs free space); RAM helps cache B-trees but the working set need not fit in RAM. View builds are CPU-bound on the JavaScript query server.
- **Storage assumptions:** local disk; compaction is more comfortable on fast NVMe but tolerant of commodity storage. Needs free space ≥ roughly the live data size for compaction.
- **Footprint:** single-node, clustered (shared-nothing), or embedded-on-device via the protocol-compatible PouchDB. Runs fine in containers/k8s as a StatefulSet with persistent volumes.
- **Deployment:** on-prem or self-hosted cloud; managed via Cloudant.

## Bottom line
Reach for CouchDB when **offline-first sync and multi-master, partition-tolerant availability** are the requirement — disconnected mobile/edge clients (with PouchDB) that must accept local writes and reconcile later are its sweet spot. Do **not** pick it for multi-document transactions, joins, ad hoc analytics, or anything needing strong consistency. The single biggest gotcha: "document-level ACID" is real but **per-document only**, and concurrent edits surface as conflicts your application code must detect (via `_changes`/conflicts) and resolve — if you ignore them, "winning revisions" silently mask divergent data.

## Sources
- [CouchDB Technical Overview (storage, ACID, crash-safety, compaction, views)](https://docs.couchdb.org/en/stable/intro/overview.html)
- [CouchDB Eventual Consistency docs](https://docs.couchdb.org/en/stable/intro/consistency.html)
- [CouchDB Shard Management / quorum (r, w, n, q)](https://docs.couchdb.org/en/stable/cluster/sharding.html)
- [Apache CouchDB — Wikipedia (license, history, BigCouch/Cloudant, version 3.5.2)](https://en.wikipedia.org/wiki/Apache_CouchDB)
- [awreece/jepsen-couchdb — independent partition test](https://github.com/awreece/jepsen-couchdb)
