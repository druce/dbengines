---
name: Google Cloud Datastore
slug: google-cloud-datastore
rank: 84
data_model: Document
license: Proprietary (managed cloud service)
summary: Google's serverless, auto-scaling NoSQL document store — now a legacy API surface ("Datastore mode") in front of the Firestore storage engine.
last_researched: 2026-06-04
confidence: high
---

# Google Cloud Datastore

> A fully managed, serverless schemaless document/entity store with strongly consistent transactions and effortless horizontal scaling — but it is now legacy: new projects get a Firestore database in "Datastore mode," and the original eventually-consistent Datastore is superseded.

## Identity
- **Taxonomy / data model:** Document/entity store (NoSQL). Data is organized into *kinds* (≈ tables), *entities* (≈ rows, schemaless property bags), grouped into *entity groups* via *ancestor paths*. Not relational, not a KV store — closer to a hierarchical document model. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** Underlying engine is Firestore's storage layer, built on Google's distributed infrastructure (historically Megastore/Bigtable lineage; ⚠️ unverified — current internal storage substrate is not publicly documented in detail). LSM-style on-disk behavior is implied by the Bigtable heritage ([lsm-vs-btree](../concepts/lsm-vs-btree.md)) but not officially specified. All queries are index-backed: every property is auto-indexed, and composite indexes are explicitly declared.
- **Workload:** OLTP only — point lookups, key/ancestor queries, small transactional writes. Not an analytics engine; no aggregation/JOIN/scan-heavy OLAP. No HTAP.

## Distribution & consistency
- **CAP under partition:** CP-leaning. As **Firestore in Datastore mode**, all queries are now **strongly consistent** by default unless eventual consistency is explicitly requested ([Choosing between modes](https://docs.cloud.google.com/datastore/docs/firestore-or-datastore)). Legacy classic Datastore was AP for non-ancestor queries (eventually consistent global indexes). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** ⚠️ unverified — no official PACELC statement. In practice: under partition it favors consistency (CP); in normal operation it provides strong consistency, accepting the latency cost of synchronous replication (PC/EC leaning toward C).
- **Default isolation:** **Serializable** isolation — both inside *and* outside transactions, queries and lookups have serializable isolation ("Datastore mode databases enforce serializable isolation") ([Datastore Transactions](https://docs.cloud.google.com/datastore/docs/concepts/transactions)). Read-write transactions use **pessimistic concurrency by default**: reader/writer locks enforce isolation and serializability, so a concurrent transaction touching the same data is delayed (not optimistically retried). An optimistic mode is also selectable. Note: queries/lookups inside a transaction do **not** see that transaction's own earlier writes (they read the snapshot as of transaction start). See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Synchronous, multi-region (in multi-region locations) managed by Google; failover and split-brain handling are fully abstracted from the user. See [replication-models](../concepts/replication-models.md). ⚠️ unverified — the consensus protocol is not publicly documented (Paxos lineage assumed via Megastore/Spanner heritage; [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)).
- **Tunable consistency?** Yes, coarsely: queries can be requested as eventually consistent for lower latency; lookups and ancestor queries are strongly consistent.
- **Clock dependency:** Not exposed to users; no TrueTime-style API surface like [google-cloud-spanner](google-cloud-spanner.md). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Entities are schemaless; each can have different properties. "Kind" is just a label — no enforced column set. The schema lives in application code.
- **Migration/evolution:** No DDL, no `ALTER`, no table locks — add/remove properties freely per entity. Adding a **composite index** requires declaring it and a backfill/build step before queries using it succeed.
- **Type system:** Strings, integers, floats, booleans, timestamps, byte strings, geographical points, array properties, embedded entities, and keys. No native JSON column type (entities themselves are the document). No vector type.

## Query interface
- **Language:** **GQL**, a SQL-like query language, plus client-library query builders. **API-only** at the wire level (REST/gRPC Datastore API). In Datastore mode the database **rejects Firestore-API calls** and vice-versa ([modes doc](https://docs.cloud.google.com/datastore/docs/firestore-or-datastore)).
- **Transactions:** Full multi-statement **ACID** transactions. Classic Datastore capped transactions at **25 entity groups** and **~1 write/sec per entity group**; **Datastore mode removed both limits** ([modes doc](https://docs.cloud.google.com/datastore/docs/firestore-or-datastore)).
- **Native vs app-side:** Automatic single-property indexes; declared composite indexes; ancestor queries scoped to an entity group. **No JOINs**, no relational referential integrity. Aggregations are limited to `count()`, `sum()`, `avg()` (via `runAggregationQuery`), available in the Datastore-mode API ([Aggregation queries](https://cloud.google.com/datastore/docs/aggregation-queries)). Filtering is constrained by the indexes that exist — un-indexed queries fail rather than scan.
- **Stored procedures / UDFs:** None. Logic lives in the application (commonly App Engine / Cloud Functions).

## Scaling & topology
- **Vertical vs horizontal:** Fully **automatic horizontal scaling** — serverless; Google shards transparently. No node sizing, no manual sharding, no resharding pain exposed to the user.
- **Sharding/partitioning:** Automatic, key-range based. Classic Datastore's per-entity-group hotspotting (the 1 write/sec rule) was the main scaling gotcha; lifted in Datastore mode, though key-range hotspots (e.g., monotonically increasing keys) can still cause contention.
- **Read replicas / read consistency:** Managed replicas; strongly consistent reads by default, with an opt-in eventually-consistent fast path.
- **Storage/compute separation:** Yes — serverless, storage and query serving are decoupled and managed by Google. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Synchronous replicated commit; durability is managed and high. Data-loss window on commit is effectively zero once a write acknowledges. See [wal-and-durability](../concepts/wal-and-durability.md). fsync/WAL internals are not user-tunable or publicly documented.
- **Throughput/latency:** Low-latency point lookups and ancestor queries; query latency scales with result-set size, **not** dataset size (index-only). Strongly consistent writes carry replication latency. ⚠️ unverified — Google does not publish official p99 latency SLOs for Datastore-mode operations.
- **Compaction/vacuum/GC:** Fully managed; no user-visible compaction or vacuum knobs. Index maintenance is automatic but adds storage and write cost (each indexed property is a write multiplier).

## Operations & maturity
- **Backup/restore, PITR:** Managed export/import; **point-in-time recovery** and scheduled backups are billed as part of storage ([Firestore pricing](https://cloud.google.com/datastore/pricing)).
- **Observability:** Cloud Monitoring metrics, GQL query plans/index-usage diagnostics, Datastore-specific dashboards. Less rich than a self-hosted RDBMS's EXPLAIN.
- **Upgrade story:** Zero — fully managed, no version upgrades or downtime for the user. Day-2 burden is mostly index management and cost control, not ops.
- **Maturity:** Very mature — originated as the App Engine Datastore (2008), in production at Google scale for >15 years. No public **Jepsen** report exists for Datastore/Datastore mode (⚠️ unverified — none found). Known failure modes: index-explosion costs, hotspot contention on sequential keys, query limitations forcing data-model contortions (ancestor relationships for strong consistency in classic mode).

## Ecosystem & people
- **Canonical use cases:** App Engine / Cloud Functions backends, user profiles, game state, catalogs, mobile/web app data needing serverless scale and ACID per-entity-group transactions.
- **Anti-patterns:** Analytics/reporting (use [google-bigquery](google-bigquery.md)); relational workloads with many-table JOINs (use cloud-sql / [postgresql](postgresql.md)); globally-relational ACID across arbitrary rows (use [google-cloud-spanner](google-cloud-spanner.md)); real-time client sync and offline mobile (use **Firestore Native mode**, which Datastore mode disables). High-fan-out aggregation or full scans.
- **Drivers/connectors:** Official client libraries (Java, Python, Go, Node.js, C#, PHP, Ruby), gRPC/REST. CDC/streaming and BI integrations are weaker than Firestore Native; Dataflow connectors exist for export to [google-bigquery](google-bigquery.md).
- **Community:** Established but **declining** — Google steers new users to Firestore. Docs are good but increasingly framed as "Datastore mode of Firestore." Commercial support via Google Cloud.

## Licensing & cost
- **License:** Proprietary, managed-only — no self-hosted or open-source option. See [license-taxonomy](../concepts/license-taxonomy.md). (The free open emulator exists for local dev only.)
- **Self-managed vs managed-only:** Managed-only; **vendor lock-in** to GCP is significant (proprietary API, no portable on-prem build).
- **Cost model:** Per-operation serverless. Roughly **$0.18 / 100k writes**, **$0.02 / 100k deletes**, reads billed per entity plus per batch of 1000 index entries, and **~$0.18 / GB-month** storage including index/PITR overhead ([Firestore pricing](https://cloud.google.com/datastore/pricing)); generous free tier. **Cost behavior at scale:** each indexed property multiplies write cost and storage — heavy auto-indexing can make writes surprisingly expensive; read-heavy index scans add up. Cheap at small scale, can invert if indexing is not pruned.

## Hardware / deployment
- **Resource profile:** N/A to the user — serverless, no instances to size. Performance is index/operation-bound, not RAM/CPU/disk-bound from the user's view.
- **Storage assumptions:** Fully abstracted (Google's infrastructure); no NVMe-vs-network choices.
- **Footprint:** Serverless managed service; **no** embedded/on-prem deployment. A local emulator covers dev/test only.
- **Deployment:** SaaS on GCP only; regional or multi-regional location chosen at database creation. No k8s/StatefulSet — there is nothing to deploy.

## Bottom line
Reach for Datastore (Datastore mode) when you want a zero-ops, auto-scaling NoSQL store with real ACID transactions behind a GCP App Engine/Functions backend and you don't need JOINs, analytics, or relational integrity. **Do not** start a new project on the classic Datastore mindset: Google now provisions a **Firestore database in Datastore mode** and recommends Firestore — choosing Native mode instead unlocks real-time sync and offline that Datastore mode disables. The single biggest gotcha is **indexing cost and the legacy data-modeling tax**: every property is indexed (multiplying write/storage cost), and classic strong-consistency patterns forced awkward ancestor hierarchies — verify which mode/limits actually apply to your project before designing around old constraints.

## Sources
- [Choosing between Native mode and Datastore mode (Google Cloud)](https://docs.cloud.google.com/datastore/docs/firestore-or-datastore)
- [Datastore Transactions (Google Cloud)](https://docs.cloud.google.com/datastore/docs/concepts/transactions)
- [Datastore Aggregation queries (Google Cloud)](https://cloud.google.com/datastore/docs/aggregation-queries)
- [Balancing Strong and Eventual Consistency with Datastore (Google Cloud)](https://docs.cloud.google.com/datastore/docs/articles/balancing-strong-and-eventual-consistency-with-google-cloud-datastore)
- [Structuring Data for Strong Consistency (Google Cloud)](https://cloud.google.com/datastore/docs/concepts/structuring_for_strong_consistency)
- [Firestore in Datastore mode pricing (Google Cloud)](https://cloud.google.com/datastore/pricing)
