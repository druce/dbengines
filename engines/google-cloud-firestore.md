---
name: Google Cloud Firestore
slug: google-cloud-firestore
rank: 45
data_model: Document
license: Proprietary (managed cloud service; client SDKs Apache-2.0)
summary: Serverless, strongly-consistent document database with realtime sync; great for mobile/web apps, wrong for big relational joins or per-document hotspots.
last_researched: 2026-06-04
confidence: high
---

# Google Cloud Firestore

> A fully-managed, serverless document database built on Spanner-class infrastructure that pairs strong consistency and ACID transactions with realtime client sync and offline support — provided you denormalize, design keys to avoid hotspots, and accept per-operation billing.

## Identity
- **Taxonomy / data model:** Document store. Data is collections → documents → fields, with documents holding nested maps/arrays and subcollections. Two operating modes: **Native mode** (document API, realtime listeners, offline SDKs) and **Datastore mode** (entity API, server-side, no realtime). A newer **Enterprise edition** adds MongoDB wire-protocol compatibility ([MongoDB compatibility GA Aug 2025](https://firebase.blog/posts/2025/08/firestore-mongodb-general-availability/)).
- **Storage model:** Two logical tables — Documents and Indexes — partitioned into "splits" (key ranges) spread across storage servers; documents ordered lexicographically by key ([Understand reads and writes at scale](https://docs.cloud.google.com/firestore/native/docs/understand-reads-writes-scale)). ⚠️ unverified — the underlying physical storage engine is not documented publicly; "LSM-tree-backed / Spanner/Bigtable lineage" is a widely-repeated inference, not stated in the official scale doc. See [lsm-vs-btree](../concepts/lsm-vs-btree.md). On-disk format is opaque/managed.
- **Workload:** OLTP-oriented, optimized for many small point reads/writes and realtime fan-out, not analytics. Not HTAP — no columnar/analytical path; export to BigQuery for OLAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP. Writes go through the split leader via Paxos; on partition the system favors consistency over availability of the affected splits ([scale docs](https://docs.cloud.google.com/firestore/native/docs/understand-reads-writes-scale)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PC/EC — consistent under partition, and in normal operation it pays coordination latency to keep reads strongly consistent (it does not trade consistency for latency by default).
- **Default isolation & what's achievable:** **Serializable (standard/Native edition).** Google states Firestore "guarantees serializable isolation of transactions… serialized and isolated by commit time" ([Transaction serializability and isolation](https://firebase.google.com/docs/firestore/transaction-data-contention); [Data contention in transactions](https://docs.cloud.google.com/firestore/native/docs/transaction-data-contention)). This is a genuinely strong claim (stronger than typical NoSQL "ACID = single-doc atomicity") because it inherits Spanner's TrueTime-backed model. **Caveat:** the **Enterprise edition (MongoDB compatibility)** defaults to **snapshot isolation** with optimistic concurrency (default read concern `snapshot`); serializable behavior there requires the `linearizable` read concern ([Enterprise behavior differences](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/behavior-differences)). See [isolation-levels](../concepts/isolation-levels.md). Default reads outside transactions are strongly consistent (latest committed value as of read start).
- **Replication:** Synchronous replication across zones using **Paxos**; one replica is leader per split and serves writes ([scale docs](https://docs.cloud.google.com/firestore/native/docs/understand-reads-writes-scale)). Multi-region configs replicate across regions and survive loss of an entire region while still serving strongly-consistent reads. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency?** Minimal. No per-query eventual-vs-strong toggle like Dynamo/Cassandra; strong consistency is the default and near-only mode. Concurrency mode is configurable: standard edition defaults **PESSIMISTIC** (document locks), Enterprise defaults **OPTIMISTIC** ([data contention docs](https://cloud.google.com/firestore/native/docs/transaction-data-contention)).
- **Clock dependency:** Yes — inherits Spanner's TrueTime atomic/GPS clock model to order transactions by commit time. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Schemaless: each document defines its own fields; the "schema" lives in app code and Security Rules. No `ALTER TABLE`; adding/removing fields is per-document.
- **Migration/evolution:** No global online DDL needed because there is no global schema. Adding an indexed field triggers backfill of composite/single-field indexes; large backfills take time but are online.
- **Type system:** strings, numbers (int64/double), booleans, timestamps, geopoints, arrays, nested maps, references, and bytes. No native vector index in standard Firestore historically, but **vector search (KNN)** is now supported via dedicated vector indexes; see [vector-search-ann](../concepts/vector-search-ann.md). Enterprise edition adds more MongoDB-style types/operators.

## Query interface
- **Language:** Native SDK query API (filters, ordering, cursors) across Android/iOS/Web/Admin SDKs; REST and gRPC. Datastore mode uses GQL. Enterprise edition exposes the **MongoDB query language / wire protocol** with 200+ added operators including cross-collection joins and aggregation stages ([MongoDB compatibility blog](https://cloud.google.com/blog/products/databases/firestore-with-mongodb-compatibility-is-now-ga)).
- **Transactions:** Full multi-statement ACID transactions (reads then writes, all-or-nothing). Batched writes for atomic multi-doc writes without reads. Client libraries auto-retry on contention.
- **Native vs app-side:** Single-field indexes are automatic; composite indexes are explicit (must be declared). **No native relational joins** in standard mode — you denormalize or do app-side fan-out. Aggregations limited to `count()`, `sum()`, `avg()`; complex analytics require export. Realtime listeners (`onSnapshot`) push incremental query result changes to clients.
- **Stored procedures / UDFs:** None in-database. Server-side logic runs in Cloud Functions triggered by Firestore events.

## Scaling & topology
- **Vertical vs horizontal:** Fully horizontal and automatic — serverless; the service auto-splits key ranges as load grows. No node sizing or capacity planning.
- **Sharding/partitioning:** Automatic range-partitioning by document key. The pain moves to **data modeling**: the **500/50/5 rule** caps cold-start ramp (start ~500 ops/sec on a collection, then +50% every 5 min) ([scale docs](https://docs.cloud.google.com/firestore/native/docs/understand-reads-writes-scale)). Monotonic keys/timestamps and sequential document IDs create index hotspots — a real, frequently-hit gotcha.
- **Read replicas / read consistency:** Replication is internal; reads are strongly consistent by default, no separate read-replica endpoint to reason about.
- **Storage/compute separation:** Yes, serverless model fully separates storage from on-demand compute; you never provision nodes. See [storage-compute-separation](../concepts/storage-compute-separation.md). (Enterprise edition introduces a provisioned/Spanner-style cost model — see Licensing.)

## Performance & durability
- **Write path:** Writes committed via Paxos to a quorum of zone replicas before ack; durable on commit with effectively no single-zone data-loss window. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Excellent for high-fan-out small reads/writes; per-collection throughput scales horizontally. **Per-document write ceiling ~1 write/sec sustained** (a single document cannot be split further), so high-contention counters/aggregates must use sharded-counter patterns. p99 is generally good but degrades sharply under hotspotting — a poorly chosen key turns a scalable workload into a single-split bottleneck.
- **Compaction/GC:** Managed and invisible to the user (LSM compaction handled by the service).

## Operations & maturity
- **Backup/restore:** Scheduled backups, managed export/import to Cloud Storage, and **Point-in-Time Recovery** covering the last 7 days ([MongoDB GA blog](https://firebase.blog/posts/2025/08/firestore-mongodb-general-availability/)).
- **Observability:** Cloud Monitoring metrics, Key Visualizer for hotspot diagnosis, query-explain support, and audit logs. No traditional slow-query log; you reason via metrics and explain.
- **Upgrade story:** Zero — fully managed, no version upgrades or maintenance windows for the user.
- **Maturity:** Production-proven at very large scale, descended from Datastore (2008) and Firebase Realtime DB; backed by Spanner-class infra. ⚠️ unverified — there is **no public Jepsen report** for Firestore; the serializability claim rests on Google's own documentation and Spanner's published model rather than independent formal verification. Known failure modes are operator-side: hotspotting, runaway read costs, and missing composite indexes (queries fail until index built).

## Ecosystem & people
- **Canonical use cases:** Mobile/web apps needing realtime sync + offline (chat, collaboration, presence, live dashboards), user profiles, game state, and serverless backends tightly coupled to Firebase/GCP.
- **Anti-patterns:** Heavy relational/JOIN-rich workloads; analytics/OLAP; very high-write single-entity counters; workloads with monotonic keys; cost-sensitive apps doing huge full-collection scans (per-document read billing punishes this). It is the wrong tool when you need ad-hoc SQL analytics or strict cost predictability under scan-heavy access.
- **Drivers/connectors:** First-class Firebase SDKs (all major platforms), Admin SDKs, REST/gRPC, MongoDB drivers (Enterprise), CDC, and managed BigQuery export for analytics/BI. dbt/BI tools integrate via the BigQuery export, not directly.
- **Community & docs:** Large Firebase developer community, excellent official docs, gentle learning curve for app developers; the hard part is data modeling, not setup.

## Licensing & cost
- **License:** Proprietary managed service (no self-hosting). Client SDKs are open source (Apache-2.0). Not an open-source database; no source-available controversy. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Managed-only, GCP-exclusive. Lock-in is significant (proprietary API, Security Rules, realtime model), though MongoDB-compatibility Enterprise edition softens API lock-in somewhat.
- **Cost model:** **Per-operation + storage + network.** Standard edition: ~$0.03/100K reads, $0.09/100K writes, $0.01/100K deletes, $0.15/GB-month storage; free tier 50K reads / 20K writes / 20K deletes / 1 GB per day ([Firestore pricing](https://cloud.google.com/firestore/pricing)). Enterprise edition prices in **Read/Write Units** (4 KiB read tranches, 1 KiB write units) at roughly $0.05/1M reads, $0.26/1M writes, $0.24/GB storage ([Enterprise pricing](https://cloud.google.com/firestore/enterprise/pricing)). **Cost behavior at scale inverts the usual intuition:** cheap when small, but read-heavy or scan-heavy workloads can get very expensive because you pay per document returned — list views and fan-out reads are the budget killers.

## Hardware / deployment
- **Resource profile:** N/A to the user — serverless; no RAM/disk/CPU provisioning. Working set need not fit in RAM (range-partitioned disk storage).
- **Storage assumptions:** Managed SSD-backed storage in Google's infrastructure; latency tolerances are Google's problem.
- **Footprint:** Serverless, multi-tenant managed service; single-region or multi-region location chosen at database creation (immutable). No embedded mode.
- **Deployment:** SaaS only, GCP. No on-prem, no k8s/StatefulSet (client apps connect via SDK/REST).

## Bottom line
Reach for Firestore when building realtime, offline-capable mobile/web apps on GCP/Firebase and you want serverless scaling with genuinely strong (serializable) transactions and zero ops. Do not reach for it for relational/JOIN-heavy data, analytics, or scan-heavy workloads where per-operation billing and the lack of native joins bite hard. The single biggest gotcha: **data modeling discipline** — monotonic keys/timestamps and per-document write contention (~1 write/sec/doc) silently throttle throughput, and naive read patterns can produce shocking bills.

## Sources
- [Understand reads and writes at scale — Firestore (Google Cloud)](https://docs.cloud.google.com/firestore/native/docs/understand-reads-writes-scale)
- [Transactions and batched writes — Firestore](https://cloud.google.com/firestore/native/docs/manage-data/transactions)
- [Transaction serializability and isolation — Firestore (Firebase)](https://firebase.google.com/docs/firestore/transaction-data-contention)
- [Data contention in transactions — Firestore](https://cloud.google.com/firestore/native/docs/transaction-data-contention)
- [Choosing between Native mode and Datastore mode](https://docs.cloud.google.com/datastore/docs/firestore-or-datastore)
- [Firestore with MongoDB compatibility is now GA (Firebase blog, Aug 2025)](https://firebase.blog/posts/2025/08/firestore-mongodb-general-availability/)
- [Announcing Firestore with MongoDB compatibility (Google Cloud blog)](https://cloud.google.com/blog/products/databases/firestore-with-mongodb-compatibility-is-now-ga)
- [Firestore pricing — Standard](https://cloud.google.com/firestore/pricing)
- [Firestore Enterprise pricing](https://cloud.google.com/firestore/enterprise/pricing)
