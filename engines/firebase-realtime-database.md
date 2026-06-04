---
name: Firebase Realtime Database
slug: firebase-realtime-database
rank: 36
data_model: Document (one large JSON tree)
license: Proprietary / managed-only (Google Cloud)
summary: Google's managed, single-region JSON-tree store that pushes live updates to connected clients; great for small realtime apps, painful past one database's scale.
last_researched: 2026-06-04
confidence: high
---

# Firebase Realtime Database

> A managed, schemaless single-region store holding all data as one big JSON tree that streams diffs to subscribed clients in real time — optimized for client sync and offline-first mobile, not for querying, large datasets, or horizontal scale.

## When to use

**Use Firebase Realtime Database if:**
- ✅ You need dead-simple, ultra-low-latency (~10 ms typical) push sync of small JSON state to many mobile/web clients — presence, chat, live dashboards, game state.
- ✅ You want offline-first mobile with local caching and automatic merge-on-reconnect, with minimal backend to run.
- ✅ Your data and traffic stay within one database's ceilings (~200k connections, ~1k writes/sec, single region).

**Avoid Firebase Realtime Database if:**
- ❌ You need real queries — a query can sort or filter on one property but not both, there are no joins or aggregations, and reads are deep (you pay egress on the whole subtree, the biggest cost trap).
- ❌ You have large datasets, need relational integrity, or must scale past one database — sharding is manual across separate databases in app code.
- ❌ You want rich queries and better scaling — Google itself now usually steers new apps to [google-cloud-firestore](google-cloud-firestore.md).
- **Taxonomy / data model:** NoSQL document store, but unusual: the *entire* database is one JSON tree, not a collection of documents. No tables or rows; data is nodes keyed by path ([docs](https://firebase.google.com/docs/database/web/structure-data)). See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Server-side storage format is proprietary and opaque (no on-disk format exposed; managed-only). Clients hold a local cache and receive incremental updates. Conceptually a tree-of-JSON, not row- or column-oriented.
- **Workload:** OLTP-ish — small reads/writes synced to many clients. Emphatically **not** analytical: queries are deep by default and return entire subtrees ([rtdb-vs-firestore](https://firebase.google.com/docs/database/rtdb-vs-firestore)). No aggregation/OLAP path. Not HTAP.

## Distribution & consistency
- **CAP under partition:** Server side is a single-region primary (CP-leaning — clients that cannot reach it cannot durably commit). Client side is explicitly **AP/offline-first**: writes are accepted into the local cache offline and merged on reconnect, so a client can be live and stale relative to the server. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition (client offline) it favors availability locally and reconciles later; else (connected) it favors low latency — Google cites typical response times under ~10 ms ([rtdb-vs-firestore](https://firebase.google.com/docs/database/rtdb-vs-firestore)). Server is the single source of truth.
- **Default isolation / what is achievable:** No SQL isolation levels. Atomicity is provided only via `transaction()` (optimistic, read-modify-write with automatic retry) which is **atomic on a single subtree**, and via multi-path `update()` which atomically writes a set of fanned-out paths ([rtdb-vs-firestore](https://firebase.google.com/docs/database/rtdb-vs-firestore)). No cross-tree / multi-region serializable transactions. The "realtime consistency" claim means *eventual convergence of client caches*, not serializability. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Internal, single-region, managed by Google; topology is not exposed. Cross-region durability is not a configurable single-database property — you replicate by sharding into separate databases. See [replication-models](../concepts/replication-models.md). No multi-leader/quorum knobs surfaced to users.
- **Tunable consistency?** No. No per-query consistency levels.
- **Clock dependency:** No user-facing clock contract; server timestamps available via `ServerValue.TIMESTAMP`. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Schemaless JSON; structure lives in app code and in **Security Rules** (a JSON-based rule language) which can also enforce `.validate` type/shape constraints at write time.
- **Migration/evolution:** No DDL, no `ALTER`. Schema changes are app-side; denormalized/fanned-out copies must be migrated manually (one of the main operational pains).
- **Type system:** JSON primitives only — string, number, boolean, null, and nested objects/arrays (arrays are stored as integer-keyed objects). No native geospatial, vector, decimal, or date types; strings capped at 10 MB, keys 768 bytes ([limits](https://firebase.google.com/docs/database/usage/limits)).

## Query interface
- **Language:** API-only via SDKs (Web/JS, Android, iOS, Admin) and a REST API. No SQL, no query DSL. Reads are listeners on a path (`on`/`once`); ordering/filtering via `orderByChild/Key/Value` + `startAt/endAt/equalTo/limitTo`.
- **Big limitation:** a query can **sort or filter on one property, but not both/multiple** ([rtdb-vs-firestore](https://firebase.google.com/docs/database/rtdb-vs-firestore)); queries are **deep** (always return the whole subtree). No joins, no `WHERE` over multiple fields, no aggregations.
- **Transactions:** `transaction()` (single-subtree optimistic) and atomic multi-path `update()`; no general multi-statement ACID.
- **Native vs app-side:** Joins, multi-field filters, and aggregations are all app-side. Denormalization / fan-out is the prescribed pattern.
- **Stored procedures / UDFs:** None in-database. Server-side logic runs in **Cloud Functions** triggered on RTDB writes (JS/TS/other) — external to the engine.

## Scaling & topology
- **Vertical vs horizontal:** A single database is a vertically-scaled, single-region instance. **Hard ceilings: ~200,000 simultaneous connections, ~1,000 writes/second, ~100,000 simultaneous responses/second, 64 MB/min sustained write throughput** ([limits](https://firebase.google.com/docs/database/usage/limits)).
- **Sharding:** Manual only — beyond the per-database ceiling you create multiple databases and shard data across them in app code (no auto-resharding; cross-shard queries are your problem). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** No user-managed replicas; clients read from their local cache plus server stream. A client's view can lag the server while offline or syncing.
- **Storage/compute separation:** Not exposed/relevant — fully managed. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Managed and not user-tunable (no WAL/fsync knobs). Server commit is durable once acknowledged; the realistic data-loss window is **client-side**: writes buffered in the offline cache are lost if the device is wiped before reconnect. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Designed for low-latency small writes and live fan-out (~10 ms typical responses per Google). p99 degrades sharply as you approach the connection/write ceilings, and **deep reads of large subtrees are a classic tail-latency and cost trap** (you pay to download the whole subtree). Single response capped at 256 MB.
- **Compaction / vacuum / GC:** None user-visible (fully managed).

## Operations & maturity
- **Backup/restore, PITR:** Automated daily backups available on the Blaze plan; manual JSON import/export. No fine-grained PITR comparable to a relational DB.
- **Observability:** Firebase console usage metrics (connections, storage, downloaded bytes), the Firebase Profiler tool for read/write hot spots, and Cloud Monitoring. No `EXPLAIN`/query-plan concept (query model is too thin to need one).
- **Upgrade story:** Zero — fully managed SaaS, no version/upgrade burden. Day-2 burden shifts to **data modeling, Security Rules correctness, denormalization maintenance, and cost control**.
- **Maturity:** Very mature (launched ~2012, Google-acquired 2014); huge production footprint in mobile/web. No public Jepsen report. Known failure modes: runaway egress cost from deep reads; the "one giant tree" anti-scaling; security-rule misconfig data leaks; single-region availability.

## Ecosystem & people
- **Canonical use cases:** Presence, chat, live dashboards, collaborative cursors, game state, IoT telemetry sync, anything that needs push-to-client and offline-first mobile with minimal backend.
- **Anti-patterns:** Anything needing rich queries, multi-field filtering, server-side aggregation/reporting, large datasets, strong relational integrity, or scale beyond one database's ceilings. For most new Firebase apps Google itself steers users to **[google-cloud-firestore](google-cloud-firestore.md)** (richer queries, multi-region, better scaling); RTDB remains preferred for the very lowest-latency, highest-frequency small-state sync.
- **Drivers/connectors:** First-party SDKs (Web, Android, iOS, Flutter, Unity, C++, Admin for Node/Java/Python/Go); REST API; Cloud Functions triggers; streaming export to BigQuery via integration. No native CDC/Kafka/dbt — analytics requires export.
- **Community/support:** Large community, Google commercial support via GCP, good docs. Low learning curve to start; the hard part is data-model discipline.

## Licensing & cost
- **License:** Proprietary, **managed-only** — no self-hosted option, full vendor lock-in to Google Cloud (Firebase Emulator exists for local dev only). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Cost model:** Bills on **storage ($5/GB-month) and data downloaded/egress** — *not* per operation and *not* per connection ([billing](https://firebase.google.com/docs/database/usage/billing)). Free Spark tier (1 GB stored, 10 GB/month download, 100 connections); Blaze pay-as-you-go above that. The gotcha: because reads are deep, **egress cost scales with subtree size, not row count** — a badly nested tree can produce surprise bills. Higher bandwidth rate than Firestore's per-op model in many workloads.

## Hardware / deployment
- **Resource profile:** N/A to the user — fully managed; you do not provision RAM/CPU/disk. Working-set-in-RAM concerns are Google's, not yours.
- **Storage assumptions:** Opaque/managed.
- **Footprint:** Serverless managed cloud service, single region per database. Local **Emulator Suite** for dev/test. No embedded/self-managed mode.
- **Deployment:** SaaS only; no on-prem, no k8s/StatefulSet (the SDK embeds in your app/clients).

## Bottom line
Reach for Firebase Realtime Database when you need dead-simple, ultra-low-latency push sync of small JSON state to many mobile/web clients with offline support and no backend to run. Do not reach for it if you need real queries (multi-field filter/sort), aggregations, large datasets, relational integrity, or scale past one database — and even then Google now usually recommends [google-cloud-firestore](google-cloud-firestore.md) instead. The single biggest gotcha: queries are deep and you pay egress on the whole subtree, so naive nesting yields both slow reads and runaway bills; the related trap is the ~200k-connection / 1k-writes-per-second single-region ceiling that forces manual sharding.

## Sources
- [Firebase Realtime Database docs](https://firebase.google.com/docs/database)
- [Structure your data](https://firebase.google.com/docs/database/web/structure-data)
- [Choose a database: Firestore or Realtime Database](https://firebase.google.com/docs/database/rtdb-vs-firestore)
- [Realtime Database limits](https://firebase.google.com/docs/database/usage/limits)
- [Understand Realtime Database billing](https://firebase.google.com/docs/database/usage/billing)
- [db-engines system entry](https://db-engines.com/en/system/Firebase+Realtime+Database)
