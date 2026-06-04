---
name: Realm
slug: realm
rank: 58
data_model: Document (embedded object database)
license: Apache 2.0 (permissive); cloud sync service deprecated by MongoDB
summary: Embedded object database for mobile apps; the cloud sync that defined it is being shut down, leaving an Apache-2.0 local store.
last_researched: 2026-06-04
confidence: high
---

# Realm

> An embedded, object-oriented, zero-copy mobile database (Core Data / SQLite replacement) whose headline feature — Atlas Device Sync — MongoDB has deprecated, leaving the on-device engine as an open-source orphan.

## When to use

**Use Realm if:**
- ✅ You want a fast, ergonomic local object store on mobile (iOS/Swift, Android/Kotlin, React Native, .NET/MAUI, Flutter) as a Core Data or SQLite replacement
- ✅ You value live, lazily-evaluated, auto-updating query results (`Results`) with change notifications for reactive UIs
- ✅ You want zero-copy mmap reads (no marshaling) and full multi-statement ACID within a single device file
- ✅ You're fine with an Apache-2.0, self-contained embedded engine and don't need SQL

**Avoid Realm if:**
- ❌ You're starting a new project that needs managed cloud sync — MongoDB deprecated Atlas Device Sync (and the Device SDKs) with end-of-life 2025-09-30, so you'd build on a sunset platform without active vendor support
- ❌ You need a server-side/backend datastore, SQL, ad-hoc analytics, multi-writer concurrency, or horizontal scale
- ❌ You hold long-lived read transactions — pinned MVCC versions cause unbounded file growth (a classic Realm bloat gotcha)
- ❌ You pass live objects across threads — objects/Results are thread-confined and require a thread-safe reference or freezing

## Identity
- **Taxonomy / data model:** Embedded object database. Data is modeled as language-native objects (classes/structs) persisted in Tables; objects can hold Lists, Sets, and Dictionaries. Closest to a [document-data-model](../concepts/document-data-model.md) but objects are *live* — accessors point at the store, not a deserialized copy. See [embedded-databases](../concepts/embedded-databases.md).
- **Storage model:** Column-oriented on-disk layout — each property stored contiguously via adaptive-width Arrays and B+Trees, with a `SlabAlloc` allocator ([lsm-vs-btree](../concepts/lsm-vs-btree.md) — it is B-tree-family, not LSM). The file is **memory-mapped** for zero-copy reads: an object accessor dereferences directly into the mmap'd file, no serialize/deserialize step ([dbdb.io](https://dbdb.io/db/realm)).
- **Workload:** OLTP-style on-device reads/writes for a single app process (plus multi-process access). Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Built in C++ (realm-core) with SDK bindings.

## Distribution & consistency
- **Single-node, on-device.** CAP is largely **N/A — single-node**; the device file is the database. Distribution historically came from Atlas Device Sync (see below), an offline-first replication layer to MongoDB Atlas, not a peer cluster.
- **Concurrency / isolation:** [mvcc](../concepts/mvcc.md) via copy-on-write. Each transaction opens a consistent snapshot of the whole database; readers never block writers ([dbdb.io](https://dbdb.io/db/realm)). This is effectively **snapshot isolation** — a read transaction sees a single fixed version, so dirty reads, non-repeatable reads, and phantoms are excluded within it. Because there is only ever one writer at a time (global write lock) operating against the latest snapshot, the local engine avoids the write-skew anomaly that distinguishes plain snapshot isolation from serializable. See [isolation-levels](../concepts/isolation-levels.md).
- **Writes:** single global write lock — exactly one writer at a time per Realm file; writers do not block readers (MVCC). Commits are durable via a two-phase commit / atomic pointer swap.
- **Replication (Device Sync):** when it existed, conflict resolution was operation-based, automatic, last-writer-wins-flavored with server reconciliation against MongoDB Atlas — offline-first, eventually consistent toward the cloud copy. See [replication-models](../concepts/replication-models.md). **This service is deprecated** (below); treat sync as a sunset feature.
- **Clock dependency:** none for the local engine (snapshot/version based, not clock-ordered). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** You declare object classes with typed properties; the file enforces them. Schema lives in app code and is compiled into the model.
- **Migration/evolution:** explicit, versioned migrations. Bump `schemaVersion` and supply a migration block; additive changes can be near-automatic, but removing/renaming/retyping requires a migration closure. Migrations run synchronously at open and rewrite affected data — can be slow on large files; no online/concurrent DDL (it is an embedded single-file store).
- **Type system:** primitives, `Date`, `Data`/blob, `Decimal128`, `ObjectId`, `UUID`, embedded objects, to-one/to-many relationships, and typed collections (List, Set, Map/Dictionary). No native geospatial in the local SDKs historically (geo queries were a sync/Atlas feature); ⚠️ unverified — vector/ANN support is not a Realm feature.

## Query interface
- **Language:** API-only — a fluent, type-safe query builder per SDK (e.g. RealmSwift `where`/type-safe key paths, Realm Kotlin `query`) plus a string predicate dialect (NSPredicate-style / RQL "Realm Query Language"). **No SQL.**
- **Live results:** queries return lazily-evaluated, auto-updating collections (`Results`) that reflect the latest committed version and emit change notifications. This is the defining ergonomic feature.
- **Transactions:** full multi-statement ACID *within a single file* (`write {}` blocks). No cross-database/distributed transactions.
- **Joins/aggregations:** relationship traversal via object graph (follow references) rather than relational joins; basic aggregates (count/sum/avg/min/max) on collections. No window functions, no server-side query planner you tune.
- **Stored procedures / UDFs:** none in the local engine (logic lives in app code).

## Scaling & topology
- **Vertical only, per device.** Each Realm file is meant to fit a single device's data; there is no sharding, no horizontal scale-out of the local store.
- **Read replicas / read consistency:** N/A locally. "Scale" was historically the cloud: Device Sync fanned per-user partitions/flexible-sync subsets to/from MongoDB Atlas.
- **Storage/compute separation:** N/A — embedded, storage and compute are the app process. See [storage-compute-separation](../concepts/storage-compute-separation.md) (not applicable).

## Performance & durability
- **Write path:** copy-on-write with an append-style commit; on commit the engine fsyncs and atomically swaps the top-ref pointer (two-phase commit), giving crash safety with no torn writes. **Data-loss window:** an uncommitted write transaction is lost on crash; committed transactions are durable. See [wal-and-durability](../concepts/wal-and-durability.md) (Realm uses COW + atomic pointer swap rather than a classic redo WAL).
- **Throughput/latency:** very fast reads due to zero-copy mmap (no marshaling); writes are serialized by the single write lock, so write-heavy concurrent workloads contend. Reads scale across threads/processes.
- **File growth / compaction:** COW + MVCC means old versions are retained until no reader references them; long-lived read transactions (a "pinned version") prevent reclamation and the file **grows unbounded** — a classic Realm gotcha. Manual `compact` (or auto-compact on open) reclaims space; pinned versions are the usual cause of bloat ([version-retention discussion](https://medium.com/@Zhuinden/understanding-realm-version-retention-and-synchronization-9a513c2445bb)).

## Operations & maturity
- **Backup/restore/PITR:** the database is a single file (plus auxiliary `.lock`/`.management`/`.note`); back up by copying the file (ideally compacted/closed). No PITR; with Device Sync, the server copy in Atlas was the durable backstop.
- **Observability:** change notifications and a debug-time Realm Studio GUI to inspect files. No production metrics/slow-query log surface — it is an embedded library.
- **Upgrade story:** SDK upgrades may bump the file format version, triggering an automatic in-place file upgrade on first open (one-way; old SDKs can't read newer file formats). Plan around this. Releases still ship (realm-swift v20.0.4 dated Feb 2026), but MongoDB declared the **Atlas Device SDKs (formerly Realm) end-of-life on 2025-09-30** — not just Device Sync — so these are now community-maintained open-source artifacts without active vendor support, and **20.x and later drop cloud sync support** ([realm-js Device Sync deprecation discussion](https://github.com/realm/realm-js/discussions/6884), [MongoDB EOL update](https://www.mongodb.com/community/forums/t/update-to-end-of-life-and-deprecation-notice/297168)).
- **Maturity / known failure modes:** mature on-device engine (acquired by MongoDB 2019), large install base in mobile apps. Known pitfalls: objects/Results are **thread-confined** (cannot pass a live object across threads without a thread-safe reference or freezing it), file bloat from pinned versions, and slow synchronous migrations. No public Jepsen report — and it would be largely inapplicable to a single-node embedded store. ⚠️ unverified — no formal-verification result located.

## Ecosystem & people
- **Canonical use cases:** offline-first mobile apps (iOS/Swift, Android/Kotlin, React Native, .NET/MAUI, Flutter via Realm Dart) needing a fast local store with reactive UI bindings; replacing Core Data or SQLite where the live-object/notification model is a win.
- **Anti-patterns:** server-side / backend datastore (it is not a server DB); anything needing SQL, ad-hoc analytics, multi-writer concurrency, or horizontal scale; **new projects that require managed cloud sync** — that capability is being retired, so building on Device Sync today is building on a sunset platform.
- **Drivers/connectors:** SDKs for Swift/Obj-C, Kotlin/Java, React Native (JS/TS), .NET, Flutter/Dart. CDC/Kafka/dbt/BI — N/A (embedded). Inspection via Realm Studio.
- **Community/support:** large community and docs from the MongoDB era; **commercial support is winding down** post-deprecation, and momentum is shifting to alternatives (SwiftData, GRDB, Core Data, ObjectBox, SQLite/[sqlite](sqlite.md)) plus sync alternatives (PowerSync, WatermelonDB, couchbase-lite, etc.).

## Licensing & cost
- **License:** **Apache 2.0** (permissive) for realm-core and the SDKs ([realm-swift](https://github.com/realm/realm-swift)). See [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 relicensing of the *client* engine; the change is **product deprecation**, not a license flip.
- **Self-managed vs managed:** the local DB is fully self-contained, free, embeddable. MongoDB **deprecated on 2024-09-09** both the managed pieces (Atlas Device Sync, Atlas App Services, Edge Server) *and* the Atlas Device SDKs (formerly Realm) themselves; the sync/App-Services backend and SDK support reached **end-of-life on 2025-09-30** ([MongoDB community forum](https://www.mongodb.com/community/forums/t/device-sync-and-edge-server-are-deprecated/296035), [EOL update](https://www.mongodb.com/community/forums/t/update-to-end-of-life-and-deprecation-notice/297168)). The Apache-2.0 client source remains, but MongoDB no longer actively backs it.
- **Lock-in / cost:** local engine has no cost and no lock-in beyond the file format. The lock-in risk was Device Sync — and that is precisely what is going away, forcing migrations.

## Hardware / deployment
- **Resource profile:** lightweight; designed for phones. Memory use is dominated by the mmap and the working set actually touched (zero-copy means you don't pay to load unused data). Not required to fit all data in RAM.
- **Storage assumptions:** local flash storage on a mobile device; single file. No network-attached storage assumptions.
- **Footprint:** **embedded** library linked into the app process; also supports in-memory mode and multi-process access to one file. Not clustered, not serverless.
- **Deployment:** ships inside the mobile/desktop app binary. No on-prem/SaaS server to run for the local DB; Device Sync (the SaaS half) is the deprecated component.

## Bottom line
Reach for Realm if you want a fast, ergonomic, reactive **local** object store on mobile and you value live auto-updating objects over SQL. Do **not** start a new project that depends on its managed cloud sync — MongoDB deprecated Atlas Device Sync (announced Sept 2024) with shutdown slated for Sept 30, 2025, so the differentiator that made Realm "Realm" is leaving; you'd be adopting an Apache-2.0 local engine whose vendor stewardship and sync story are evaporating. Biggest day-2 gotchas: thread-confined live objects and unbounded file growth from pinned MVCC versions.

## Sources
- [Database of Databases — Realm](https://dbdb.io/db/realm) (architecture, MVCC/COW, isolation, zero-copy)
- [realm/realm-swift (GitHub)](https://github.com/realm/realm-swift) (Apache 2.0 license, encryption, current 20.x releases)
- [Device Sync Deprecation — realm/realm-js Discussion #6884](https://github.com/realm/realm-js/discussions/6884)
- [Device Sync and Edge Server are Deprecated — MongoDB community forum](https://www.mongodb.com/community/forums/t/device-sync-and-edge-server-are-deprecated/296035)
- [Understanding Realm: Version Retention and Synchronization (file bloat / pinned versions)](https://medium.com/@Zhuinden/understanding-realm-version-retention-and-synchronization-9a513c2445bb)
- [Realm (database) — Wikipedia](https://en.wikipedia.org/wiki/Realm_(database))
