---
name: CloudKit
slug: cloudkit
rank: 115
data_model: Document (record-oriented BaaS)
license: Proprietary (Apple-managed-only)
summary: Apple's managed iCloud backend-as-a-service — per-user record store with public/private/shared databases, no servers to run but locked to the Apple platform.
last_researched: 2026-06-04
confidence: medium
---

# CloudKit

> Apple's serverless iCloud datastore for apps: a schema-light record store split into per-user private, app-wide public, and shared databases, with zero ops but total Apple lock-in.

## Identity
- **Taxonomy / data model:** Document/record-oriented backend-as-a-service (BaaS), not a self-hostable database engine. Apps store `CKRecord` objects (key-value field bags) of a named `CKRecord.Type`, grouped into `CKRecordZone`s, inside `CKDatabase`s, inside a `CKContainer`. Record types are roughly tables, fields roughly columns ([Apple: Designing with CloudKit](https://developer.apple.com/icloud/cloudkit/designing/)).
- **Storage model:** Opaque managed service. Apple has confirmed CloudKit is built on the [FoundationDB Record Layer](https://www.foundationdb.org/files/record-layer-paper.pdf) (a Protocol-Buffers structured-record layer over the FoundationDB ordered KV store), a fact Apple confirmed when it open-sourced the Record Layer in January 2019 ([FoundationDB blog: Announcing the Record Layer](https://www.foundationdb.org/blog/announcing-record-layer/)). CloudKit migrated off an earlier Cassandra-backed design — Cassandra had no concurrency within a zone and scoped multi-record atomic operations to a single partition ([Engineer's Codex: How Apple built iCloud](https://read.engineerscodex.com/p/how-apple-built-icloud-to-store-billions)). FoundationDB itself is an ordered KV store whose default on-disk engine is a **B-tree** ([lsm-vs-btree](../concepts/lsm-vs-btree.md)) — historically a SQLite-based engine (`ssd-2`), with the newer prefix-compressed B+tree "Redwood" engine; an optional RocksDB (LSM) engine also exists, but B-tree is the default, not LSM ([FoundationDB storage engines](https://apple.github.io/foundationdb/redwood.html)). On-disk format is not exposed to CloudKit developers.
- **Workload:** OLTP-ish app sync — point reads/writes of small records, zone-delta sync, query subscriptions. Not OLAP; no analytics, joins, or aggregations server-side. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** Not exposed as a tunable system; it is a hosted cloud service. The underlying FoundationDB is a CP store (strict serializability), but CloudKit's developer-facing contract across zones/databases behaves closer to **eventually consistent** for sync — clients reconcile via change tokens, and there is no developer-visible global-consistency guarantee across the whole container. ⚠️ unverified — Apple does not publish a formal CAP/PACELC classification for CloudKit. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no published PACELC characterization. In practice latency dominates the developer experience (network round-trips to iCloud), and cross-device propagation is asynchronous.
- **Default isolation & what's achievable:** The FoundationDB substrate provides serializable transactions ([Record Layer paper](https://www.foundationdb.org/files/record-layer-paper.pdf)). CloudKit exposes atomicity only **within a single zone**: a `CKModifyRecordsOperation` with `isAtomic = true` against records in one **custom zone** is all-or-nothing ([Apple: CKModifyRecordsOperation.isAtomic](https://developer.apple.com/documentation/cloudkit/ckmodifyrecordsoperation/isatomic)), but there is **no cross-zone or cross-database transaction**. Custom zones exist only in the private/shared databases; the public database has only a default zone and offers no batch atomicity guarantee. So "ACID" applies only to single-zone batches, not to the API as a whole. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Managed by Apple across iCloud data centers; topology not exposed. Conflict handling is client-mediated — writes carry a `recordChangeTag`; a stale tag yields a `serverRecordChanged` error and the app must merge ([Apple forums / docs](https://developer.apple.com/icloud/cloudkit/designing/)). This is optimistic-concurrency / last-writer-arbitration, not server-side CRDT merge. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No. No quorum/consistency-level knobs.
- **Clock dependency:** None exposed to developers; correctness rests on change-tag/change-token sequencing, not on synchronized client clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Hybrid. In the **development** environment the schema auto-creates from the first record saved (schema-on-write, inferred). In **production** the schema is locked; you must promote schema changes via the CloudKit Dashboard/`cktool`, and you can only add fields/indexes, not remove or retype existing ones without a reset ([Apple: Designing with CloudKit](https://developer.apple.com/icloud/cloudkit/designing/)).
- **Migration/evolution:** Additive only in production (new record types, new fields, new indexes). No destructive online DDL; field type changes require schema reset (dev) and are effectively forbidden once in production. This is a notable operational rigidity.
- **Type system:** Strings, numbers (int/double), dates, bytes, locations (`CLLocation`, geo-queryable), references (`CKRecord.Reference` — pointer to another record, optionally with cascade-delete), lists/arrays of these, and **assets** (`CKAsset`, large binary blobs stored separately). No native JSON document type, no vectors, no nested objects beyond references.

## Query interface
- **Language:** API-only. Native Swift/Obj-C `CloudKit` framework, plus **CloudKit JS** and the **CloudKit Web Services** REST API (records/modify, records/query, assets, zones/changes, subscriptions) for web/server access via API tokens or server-to-server keys ([CloudKit Web Services Reference](https://developer.apple.com/library/archive/documentation/DataManagement/Conceptual/CloudKitWebServicesReference/SettingUpWebServices.html)). Queries use `NSPredicate`/`CKQuery` — single record type, with filters and sorts on indexed fields. No SQL.
- **Transactions:** Single-zone atomic batch writes only; no multi-statement/multi-zone ACID.
- **Native vs app-side:** **No server-side joins, no aggregations, no GROUP BY.** Queries are single-record-type. References must be followed client-side. Secondary indexes exist but must be explicitly enabled per field (queryable/sortable/searchable) in the schema.
- **Stored procedures / UDFs:** None. No server-side code execution.

## Scaling & topology
- **Vertical vs horizontal:** Fully managed and horizontally scaled by Apple; developers do not provision or shard. The natural sharding unit is the **per-user private database** — each user's data lives in their own iCloud account/quota, which is what lets CloudKit scale to billions of small databases ([Record Layer paper](https://www.foundationdb.org/files/record-layer-paper.pdf)).
- **Sharding (auto/manual):** Automatic and opaque; no resharding for the developer.
- **Read replicas / read consistency:** Not exposed. Reads after writes within a session are generally read-your-writes for the writing device; cross-device reads are eventually consistent via change-token sync.
- **Storage/compute separation:** Inherent to the SaaS model; not a developer concern. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Opaque. Durability is Apple's responsibility; backed by FoundationDB which uses WAL-style durable commits. Developer-visible data-loss window is effectively "what hasn't yet synced to iCloud" — unsynced local changes can be lost if the device fails before upload. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Network-bound; every operation is a round-trip to iCloud. The hard ceiling is the documented **request-rate / quota** limits (see Licensing & cost), not engine internals. ⚠️ unverified — Apple publishes no p99 latency or throughput SLAs for CloudKit.
- **Compaction/vacuum/GC:** Fully managed; not exposed. Deleted records and unreferenced assets are reclaimed by Apple.

## Operations & maturity
- **Backup/restore, PITR:** ⚠️ unverified — no developer-facing backup/PITR/snapshot feature. You cannot take a point-in-time snapshot of the public database; data protection relies entirely on Apple. Export is DIY via the API.
- **Observability:** CloudKit Dashboard provides telemetry, schema management, record browsing, and request logs; `cktool` (Xcode 13+) gives CLI access to the management API. No EXPLAIN/query-plan tooling; query performance is a black box.
- **Upgrade story:** Zero — fully managed; no version upgrades for the developer. Schema promotion (dev→production) is the closest analog and is one-way/additive.
- **Maturity:** Production since 2014 (WWDC14), underpins many first-party and third-party Apple-ecosystem apps; mature for its niche. Known failure modes: opaque outages tied to iCloud, `quotaExceeded` and rate-limit errors under load, and merge-conflict handling pushed onto the app. **No Jepsen report exists** (it is not a self-hostable distributed DB to test). ⚠️ unverified — no public formal-verification or Jepsen analysis of CloudKit specifically.

## Ecosystem & people
- **Canonical use cases:** Syncing a user's app data across their own Apple devices (the private database is the killer feature — free per-user storage on the user's iCloud quota); app-wide read-mostly shared catalogs (public database); CloudKit Sharing for collaborative documents (shared database). Tight integration with **Core Data + CloudKit** (`NSPersistentCloudKitContainer`) for transparent local-store sync.
- **Anti-patterns:** Cross-platform apps (no Android/web-first story beyond the limited JS/REST API and no non-Apple auth); anything needing joins, aggregations, full-text analytics, or server-side logic; teams wanting portability or an exit path; write-heavy/high-fan-out workloads that hit the per-second request limits; apps needing strong cross-zone transactions.
- **Drivers/ORMs/connectors:** Native Apple SDKs; CloudKit JS; CloudKit Web Services REST. No CDC, no Kafka connector, no dbt, no BI integration — it is a closed endpoint, not a queryable warehouse.
- **Community / support / docs:** Large Apple-developer community; docs are decent for the native path but thin and partly archived for Web Services. Learning curve is moderate; the conflict-merge and schema-promotion models are the common stumbling blocks.

## Licensing & cost
- **License:** Proprietary, Apple-managed-only. Not open source; cannot be self-hosted. See [license-taxonomy](../concepts/license-taxonomy.md). (Note: the *substrate* FoundationDB and its Record Layer are Apache-2.0 open source, but CloudKit-the-service is not.)
- **Self-managed vs managed-only:** Managed-only — there is no on-prem option.
- **Lock-in:** Severe. Records, zones, sharing, auth (iCloud account), and the API are Apple-specific; migrating off requires re-architecting both data and identity. Requires an Apple Developer Program membership.
- **Cost model:** **Private-database data counts against each end user's personal iCloud quota — free to the developer.** Only the **public database** counts against the app's pooled quota, which scales with user count; Apple's published baseline free tier is 10 GB asset storage, 100 MB DB storage, 2 GB/day transfer, and ~40 requests/sec, all scaling up with active users ([Apple WWDC14 / developer docs](https://wwdcnotes.com/documentation/wwdcnotes/wwdc14-208-introducing-cloudkit/)). Historically published overage rates were roughly $100 per extra 10 req/s, $0.10/GB transfer, $3/GB DB storage, and $0.03/GB asset storage. ⚠️ unverified — Apple has de-emphasized the per-unit price schedule on current developer pages, a long-standing point of developer confusion ([Apple Developer Forums](https://developer.apple.com/forums/thread/715649)); confirm current rates before relying on them.

## Hardware / deployment
- **Resource profile:** N/A to the developer — no servers to size. Client-side cost is network and the local cache/Core Data store.
- **Storage assumptions:** Managed by Apple; not exposed.
- **Footprint:** Serverless SaaS endpoint. No single-node/cluster/embedded option.
- **Deployment:** SaaS-only, Apple-hosted. No on-prem, no k8s, no StatefulSet — irrelevant by design. Reachable from Apple platforms natively and from web/servers via CloudKit JS / Web Services REST.

## Bottom line
Reach for CloudKit if you are building an Apple-platform app and want per-user data sync "for free" with zero backend to operate — the private database charging against the *user's* iCloud quota is genuinely hard to beat economically. Do not reach for it if you need cross-platform reach, server-side queries/joins/aggregations, an exit path, or strong cross-zone transactions. The single biggest gotcha: it is a sync service, not a queryable database — there are **no joins, no aggregations, and conflict resolution plus additive-only schema promotion are pushed onto your app**, and you are permanently locked to Apple's ecosystem.

## Sources
- [Apple: Designing with CloudKit](https://developer.apple.com/icloud/cloudkit/designing/)
- [CloudKit Web Services Reference: Composing Requests](https://developer.apple.com/library/archive/documentation/DataManagement/Conceptual/CloudKitWebServicesReference/SettingUpWebServices.html)
- [WWDC14-208: Introducing CloudKit (limits/quotas)](https://wwdcnotes.com/documentation/wwdcnotes/wwdc14-208-introducing-cloudkit/)
- [FoundationDB Record Layer: A Multi-Tenant Structured Datastore (paper)](https://www.foundationdb.org/files/record-layer-paper.pdf)
- [Engineer's Codex: How Apple built iCloud to store billions of databases (Cassandra→FoundationDB)](https://read.engineerscodex.com/p/how-apple-built-icloud-to-store-billions)
- [Apple Developer Forums: Current CloudKit pricing](https://developer.apple.com/forums/thread/715649)
- [cktool — Apple Developer](https://developer.apple.com/icloud/ck-tool/)
