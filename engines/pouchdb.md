---
name: PouchDB
slug: pouchdb
rank: 133
data_model: Document
license: Apache License 2.0 (permissive)
summary: In-browser/Node.js JSON document store that speaks the CouchDB replication protocol — the standard pick for offline-first sync apps.
last_researched: 2026-06-04
confidence: high
---

# PouchDB

> An embedded JavaScript document database that emulates the [couchdb](couchdb.md) API and replicates over the CouchDB replication protocol, so apps can read/write offline locally and sync bidirectionally when connectivity returns.

## When to use

**Use PouchDB if:**
- ✅ You're building an offline-first web/mobile app or PWA whose per-user data must work offline and sync bidirectionally
- ✅ Your backend is in the CouchDB family (self-hosted CouchDB, IBM Cloudant, Couchbase Sync Gateway)
- ✅ You want optimistic local UIs with read-your-writes locally and a small embedded JS library (Apache 2.0, no fees)
- ✅ You want flexible schemaless JSON CRUD with Mango/map-reduce queries in the browser or Node

**Avoid PouchDB if:**
- ❌ Your app doesn't detect `_conflicts` and merge intentionally — the automatic conflict "winner" is deterministic but arbitrary, not semantically correct, so users will silently lose edits
- ❌ You need multi-document transactions or strong cross-replica consistency — writes are single-document atomic only (`bulkDocs` is not atomic)
- ❌ You need a server-side primary database, large per-client datasets, heavy analytics, or relational joins
- ❌ You're not on the CouchDB replication protocol — there's no generic CDC/Kafka/dbt sync path, and browser storage quotas can silently evict data

## Identity
- **Taxonomy / data model:** Schemaless JSON document store; documents keyed by `_id`, versioned by `_rev`. Conceptually a client-side port of [couchdb](couchdb.md) ([docs](https://pouchdb.com/guides/)). Multi-master by design.
- **Storage model:** Pluggable adapter pattern over a key-value backend ([adapters](https://pouchdb.com/adapters.html)). Browser default is **IndexedDB**; Node.js default is **LevelDB** (an [LSM-tree](../concepts/lsm-vs-btree.md) via `leveldown`). WebSQL adapter is deprecated as of v7.0.0. In-memory, LocalStorage (experimental), and Cordova/Capacitor SQLite adapters exist. On-disk format is whatever the underlying adapter uses — PouchDB does not define its own file format.
- **Workload:** OLTP-style single-document reads/writes for client apps; not analytical. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** AP. PouchDB is built to keep working while disconnected and reconcile later — the offline replica accepts writes during a partition and merges on reconnect ([replication guide](https://pouchdb.com/guides/replication.html)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, favors availability (A); else (connected) it still favors latency/availability over global consistency — replication is asynchronous and eventually consistent, never a synchronous distributed commit.
- **Default isolation & what's achievable:** Single-node engine; each `put`/`post`/`remove`/`bulkDocs` is atomic at the single-document level using optimistic concurrency on `_rev` ([mvcc](../concepts/mvcc.md)-style). A stale `_rev` write fails with a **409 conflict** (an "immediate conflict") that the app must retry ([conflicts guide](https://pouchdb.com/guides/conflicts.html)). There are **no multi-document transactions** — calling this "ACID" is misleading; durability + per-document atomicity, but no cross-document isolation or atomic batches. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Multi-master / peer-to-peer over the [CouchDB replication protocol](https://docs.couchdb.org/en/stable/replication/protocol.html) (HTTP REST + revision trees). Async only; `live`/`retry` options give continuous sync with `paused`/`active`/`change` events. Filtered and one-shot replication supported. See [replication-models](../concepts/replication-models.md).
- **Conflict handling:** Conflicts are a first-class, expected outcome, not an error. **Eventual conflicts** (two replicas edit the same doc offline) do not throw; both revisions are stored in the revision tree and every node deterministically picks the *same* winner with **no coordination** ([conflicts guide](https://pouchdb.com/guides/conflicts.html)). ⚠️ unverified — per the CouchDB algorithm the winner is the revision with the longest revision history, with ties broken by comparing `_rev` strings and taking the highest in lexicographic (ASCII) order; the PouchDB/CouchDB guides confirm the choice is "deterministic but arbitrary" without documenting the exact tie-break on these pages. The "loser" is retained and surfaced via `db.get(id, {conflicts: true})` as `_conflicts`. **The app is fully responsible for meaningful merge** — the automatic winner is arbitrary-but-consistent, not semantically correct. This is the single biggest mental-model gotcha. See [crdts](../concepts/crdts.md) for an alternative auto-merge approach PouchDB does *not* use.
- **Tunable consistency?** No quorum/consistency-level knobs (it is single-node locally); consistency is governed by the sync topology you build.
- **Clock dependency:** None for correctness — revision trees and deterministic winner selection do not rely on wall-clock time. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Schemaless JSON; any structure allowed. Validation lives in app code (or in CouchDB `validate_doc_update` functions on the server side).
- **Migration/evolution:** No DDL, no locks — schema changes are just writing differently shaped documents; migrations are app-level (lazy on read, or batch rewrite). Index changes (`createIndex`) build secondary indexes incrementally.
- **Type system:** JSON only (objects, arrays, strings, numbers, booleans, null). Binary data via document **attachments**. No native geospatial/vector/interval types; full-text and geo require plugins or external services.

## Query interface
- **Language:** JavaScript API only — no SQL. Primitives: `get`/`put`/`post`/`remove`/`bulkDocs`/`allDocs`. Two query styles: **map/reduce views** (`db.query`, CouchDB-compatible design documents) and **Mango**, a Mongo-style JSON selector (`db.find` via `pouchdb-find`) with `createIndex` for secondary indexes ([API](https://pouchdb.com/api.html)).
- **Transactions:** Single-document atomic writes only; `bulkDocs` is a batch but **not an atomic transaction** (per-doc success/failure). No multi-statement ACID.
- **Native vs app-side:** Secondary indexes native (map/reduce + Mango). No joins — denormalize, use linked/emitted-key view tricks, or resolve app-side. Aggregations only via reduce functions in views.
- **Stored procedures / UDFs:** Map/reduce and (for sync targets) validation functions are written in JavaScript. No server-side procedural language beyond that.

## Scaling & topology
- **Vertical vs horizontal:** It is an **embedded, single-node** database per client; "scaling" means many independent replicas each holding their own (often per-user) dataset, all syncing to a central [couchdb](couchdb.md)/Cloudant/Couchbase Sync Gateway. No sharding of a single local DB.
- **Sharding / partitioning:** N/A locally. Scale-out lives on the server tier you sync to.
- **Read replicas / read consistency:** Every PouchDB instance *is* a full local replica; local reads are immediately consistent with local writes, but may lag the server until replication completes (read-your-writes locally, eventual across peers).
- **Storage/compute separation:** N/A — embedded; storage and compute are co-located in the client. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Durability is delegated to the adapter — IndexedDB transactions in the browser, LevelDB ([WAL](../concepts/wal-and-durability.md) + SSTables) in Node. Data-loss window is governed by the browser/OS and the underlying store's fsync behavior, not by PouchDB directly. ⚠️ unverified — PouchDB does not document an explicit per-write fsync/group-commit policy of its own; durability semantics are effectively those of IndexedDB/LevelDB.
- **Throughput/latency:** Tuned for modest client datasets. IndexedDB performance is the practical ceiling; large `bulkDocs`, big attachments, and deep revision trees degrade it. p99 is dominated by IndexedDB transaction overhead and by view/index (re)building on first query. ⚠️ unverified — no authoritative published p99 benchmarks; treat as workload-dependent.
- **Browser quotas:** Subject to per-origin storage quotas; browsers can evict data under storage pressure, and historically iOS had tight (~50MB) limits prompting use of the SQLite adapter ([adapters](https://pouchdb.com/adapters.html)). Not a database for large datasets per client.
- **Compaction / GC:** Revision metadata accumulates; `db.compact()` reclaims space by dropping old non-leaf revision bodies. `revs_limit` caps tracked history — set it too low and replication can lose the ability to relate incoming revisions, manufacturing spurious conflicts ([compact guide](https://pouchdb.com/guides/compact-and-destroy.html)).

## Operations & maturity
- **Backup/restore, PITR:** No built-in PITR. "Backup" = replicate to another PouchDB/CouchDB endpoint (or dump/load via `pouchdb-replication-stream`). Durability/recovery story rests on the central server you sync to.
- **Observability:** Replication emits `change`/`paused`/`active`/`denied`/`error`/`complete` events; `db.info()` for stats; debug logging via `PouchDB.debug.enable`. No EXPLAIN-style planner output; index usage for Mango can be inspected via the `explain` option.
- **Upgrade story:** It is a bundled JS library — "upgrade" = ship a new app version with a newer PouchDB. v7→v8→v9 are mostly compatible; the on-disk IndexedDB schema is migrated by the library. Day-2 burden is mostly on the server tier and on app-level conflict-resolution code.
- **Maturity:** Mature and widely deployed since ~2012; **donated to the Apache Software Foundation and currently an *incubating* podling — it entered incubation 2025-04-15 and has not yet graduated to a top-level project** ([Apache incubator status](https://incubator.apache.org/projects/pouchdb.html)). Latest release PouchDB 9.0.0 (2024-05-24, [release notes](https://pouchdb.com/2024/05/24/pouchdb-9.0.0.html)). **No Jepsen report** (and it would not be a natural target — single-node local store; correctness questions live in the CouchDB-protocol layer). Known failure modes: silent browser eviction of data, unbounded revision-tree growth without compaction, and apps that ignore conflicts and silently lose user edits.

## Ecosystem & people
- **Canonical use cases:** Offline-first and field/mobile apps, PWAs, optimistic local UIs, intermittent-connectivity scenarios — anywhere a per-user dataset must work offline and sync to [couchdb](couchdb.md), IBM Cloudant, or Couchbase Sync Gateway.
- **Anti-patterns:** Large multi-tenant datasets in one local DB; anything needing multi-document transactions, strong cross-replica consistency, server-authoritative validation without a CouchDB-family backend, heavy analytics, or relational joins. Not a server-side primary database.
- **Drivers / connectors:** Rich plugin ecosystem (`pouchdb-find`, `pouchdb-authentication`, adapters, `pouchdb-replication-stream`). Framework bindings (e.g. `use-pouchdb` for React). [RxDB](https://rxdb.info/) is a popular reactive layer that can sit on PouchDB. Syncs natively only with CouchDB-protocol servers — no generic CDC/Kafka/dbt integration.
- **Community / docs:** Strong, well-organized official docs and guides; active but niche (offline-first) community; commercial support typically via the CouchDB/Cloudant/Couchbase ecosystem rather than PouchDB itself. Learning curve is low for basic CRUD, steep for correct conflict resolution and view design.

## Licensing & cost
- **License:** **Apache License 2.0**, permissive — the project was Apache-2.0 licensed long before it joined the ASF, and is now hosted under the Apache **Incubator** ([GitHub](https://github.com/apache/pouchdb), [incubator status](https://incubator.apache.org/projects/pouchdb.html)). No post-2018 relicensing risk. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** The library is free and self-managed/embedded. Cost lives in the **sync backend**: self-hosted [couchdb](couchdb.md) (free, Apache 2.0), IBM Cloudant (managed, usage-priced), or Couchbase Sync Gateway. No PouchDB licensing fees.
- **Lock-in:** Low at the library layer (Apache 2.0, open protocol), but you are committed to the **CouchDB replication protocol** for the server side.
- **Cost model:** Library is free; backend cost scales with the managed CouchDB/Cloudant service you choose (per-storage/per-request for Cloudant), not with PouchDB.

## Hardware / deployment
- **Resource profile:** Constrained by the client device. IndexedDB/LevelDB are disk-backed, but indexes and some adapter operations are memory-sensitive; the experimental LocalStorage adapter keeps all doc IDs in memory and can crash on larger DBs ([adapters](https://pouchdb.com/adapters.html)). Working set should comfortably fit per-user client storage.
- **Storage assumptions:** Local device storage (IndexedDB in browser, local disk in Node). No NVMe/network-attached assumptions; not designed for large or shared volumes.
- **Footprint:** **Embedded** — a JavaScript library bundled into a browser app or Node process. See [embedded-databases](../concepts/embedded-databases.md). No standalone server, no cluster.
- **Deployment:** Ships inside the client app; the server side (CouchDB/Cloudant/Sync Gateway) is the deployed/operated component. PouchDB itself has no k8s/StatefulSet story.

## Bottom line
Reach for PouchDB when you need an **offline-first** web/mobile app whose local data must sync bidirectionally with a CouchDB-family backend — it is the de-facto standard for exactly that. Do **not** reach for it as a general server database, for large per-client datasets, or when you need multi-document transactions or strong consistency. The biggest gotcha: its automatic conflict "winner" is deterministic but **arbitrary**, not semantically correct — if your app does not detect `_conflicts` and merge intentionally, users will silently lose edits.

## Sources
- [PouchDB Introduction / Guides](https://pouchdb.com/guides/)
- [PouchDB Adapters](https://pouchdb.com/adapters.html)
- [PouchDB Conflicts guide](https://pouchdb.com/guides/conflicts.html)
- [PouchDB Replication guide](https://pouchdb.com/guides/replication.html)
- [PouchDB Compacting and destroying](https://pouchdb.com/guides/compact-and-destroy.html)
- [PouchDB API Reference](https://pouchdb.com/api.html)
- [PouchDB 9.0.0 release](https://pouchdb.com/2024/05/24/pouchdb-9.0.0.html)
- [apache/pouchdb (GitHub)](https://github.com/apache/pouchdb)
- [CouchDB Replication Protocol](https://docs.couchdb.org/en/stable/replication/protocol.html)
- [CouchDB Replication and conflict model](https://docs.couchdb.org/en/stable/replication/conflicts.html)
