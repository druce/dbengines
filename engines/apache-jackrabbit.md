---
name: Apache Jackrabbit
slug: apache-jackrabbit
rank: 75
data_model: Content repository (JCR)
license: Apache License 2.0 (permissive)
summary: Java content repository implementing the JCR 2.0 spec; a hierarchical node/property tree with versioning, full-text search and observation — best known as the storage engine under Adobe AEM (via its Oak successor).
last_researched: 2026-06-04
confidence: high
---

# Apache Jackrabbit

> The reference implementation of the Java Content Repository (JCR 2.0) standard — a hierarchical, schema-flexible content store with built-in versioning, full-text search, and change observation; in practice almost always encountered as its rewritten successor **Jackrabbit Oak**, the repository underneath Adobe Experience Manager.

## When to use

**Use Apache Jackrabbit if:**
- ✅ You need a hierarchical content repository — versioned, ACL-rich, full-text-searchable, observable content in a Java stack
- ✅ You are building on or alongside Adobe Experience Manager / CRX (the dominant consumer of Oak)
- ✅ Your workload is read-skewed CMS/DAM/document management with flexible per-node schema (node types + mixins)
- ✅ You maintain index discipline and run revision/blob GC and segment compaction as day-2 chores

**Avoid Apache Jackrabbit if:**
- ❌ You run queries without an explicitly created index — they silently fall back to full-repository traversal and destroy performance (biggest gotcha)
- ❌ You need serializable transactions — it gives snapshot isolation only, and write skew is documented
- ❌ You need relational/transactional OLTP, analytics/aggregation, joins across heterogeneous datasets, or very high write throughput
- ❌ You don't want a JVM/embedded-library deployment, or you want app-level sharding of the content tree (it leans on MongoDB/RDB instead)

Note: "Apache Jackrabbit" covers two related codebases. *Jackrabbit 2* ("classic") is the original JCR 2.0 reference implementation. *Jackrabbit Oak* is a ground-up rewrite (started ~2012) with a different concurrency and storage model, and is the version in production use today (e.g. Adobe AEM 6+ / CRX). This page covers both, defaulting to Oak's behavior where they diverge because Oak is what you will actually run. ([Oak docs](https://jackrabbit.apache.org/oak/docs/), [JCR home](https://jackrabbit.apache.org/jcr/index.html))

## Identity
- **Taxonomy / data model:** A *content repository*, not a general database. Data is a single hierarchical tree of typed **nodes** and **properties** (the JCR model) — think a versioned, queryable, observable filesystem-with-metadata. Node types provide optional schema. It is a [hierarchical-data-model](../concepts/hierarchical-data-model.md) store with document-like flexibility, plus first-class [full-text-search](../concepts/full-text-search.md) and versioning.
- **Storage model:** Pluggable. Oak separates the logical *NodeStore* from physical storage. Two flavors: **SegmentNodeStore (Oak Segment Tar / "TarMK")** — immutable content stored as UUID-identified segments in append-only tar files, optimized for a single node ([Segment Tar overview](https://jackrabbit.apache.org/oak/docs/nodestore/segment/overview.html)); and **DocumentNodeStore** — nodes persisted as documents in **MongoDB** (MongoDocumentStore) or an RDBMS (RDBDocumentStore), for clustering ([DocumentNodeStore](https://jackrabbit.apache.org/oak/docs/nodestore/documentmk.html)). Large binaries go to a separate **BlobStore/DataStore** (filesystem, S3, Azure). Jackrabbit 2 used a different "PersistenceManager" abstraction over DB/filesystem. Not row/column — it is a [hierarchical-data-model](../concepts/hierarchical-data-model.md) revision tree. See [lsm-vs-btree](../concepts/lsm-vs-btree.md) for contrast; Oak segment storage is append-only/immutable, closer in spirit to an LSM than a B-tree.
- **Workload:** OLTP-ish content serving, heavily **read-skewed** (web CMS). Not OLAP, not HTAP. Designed for many concurrent readers and a moderate write rate on a large content tree. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** For the clustered DocumentNodeStore, consistency follows the backing store. On MongoDB, Oak inherits Mongo's CP-leaning behavior; from Oak 1.9.3 the MongoDocumentStore uses **causally-consistent client sessions** on MongoDB 3.6+, which lets it read from secondaries while preserving read-your-writes for that session ([MongoDB DocumentStore](https://jackrabbit.apache.org/oak/docs/nodestore/document/mongo-document-store.html)). Coarse CAP is the wrong lens — see [cap-pacelc](../concepts/cap-pacelc.md); the meaningful guarantee is per-session snapshot semantics, not cluster-wide linearizability.
- **PACELC:** ⚠️ unverified — no formal PACELC characterization exists. Effectively: under partition Oak's availability/consistency tracks the chosen DocumentStore (Mongo/RDB); in normal operation (E) it favors **latency** via snapshot reads and async indexing, accepting bounded staleness.
- **Default isolation & what's achievable:** **Snapshot isolation with a relaxed "first committer wins" strategy.** Each Oak session sees a *stable snapshot* of the repository taken when the session was acquired; it must call `Session.refresh()` to see others' commits ([Oak vs JR2 differences](https://jackrabbit.apache.org/oak/docs/differences.html)). On `save()`, the session's changes are **rebased** onto the current head (re-applying the session's diffs); resolvable conflicts are merged, unresolvable ones leave **conflict markers** on nodes ([conflict handling via rebasing](https://jackrabbit.apache.org/archive/wiki/JCR/Conflict-handling-through-rebasing-branches_115513383.html)). This is [mvcc](../concepts/mvcc.md) snapshot isolation — **not serializable**: Oak explicitly documents that sessions can exhibit **write skew** ([differences](https://jackrabbit.apache.org/oak/docs/differences.html)). JCR "transactions" (JTA/XA) exist but the underlying isolation is still snapshot, so "ACID" here means snapshot-isolated, not serializable.
- **Replication:** No native replication in the repository layer; it delegates. DocumentNodeStore clustering = multiple Oak instances over a **shared** MongoDB/RDBMS, each instance with its own cluster-node id, commits ordered by **revisions** across nodes ([documentmk](https://jackrabbit.apache.org/oak/docs/nodestore/documentmk.html)). Redundancy/failover is the backing store's job (Mongo replica sets). SegmentNodeStore is single-node (cold-standby via file copy / oak-run). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited: MongoDB read preference + causal-consistent sessions let you trade read freshness for secondary offload. No per-query consistency-level API like Cassandra.
- **Clock dependency:** ⚠️ unverified on hard correctness, but revisions embed timestamps and clustered DocumentNodeStore is sensitive to clock skew across cluster nodes; significant skew can cause lease/visibility problems. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Flexible. Nodes have **node types** (`nt:unstructured` is fully schemaless; named types enforce allowed child nodes/properties and mandatory fields). You choose rigidity per node. Mixins add aspects (e.g. `mix:versionable`, `mix:referenceable`).
- **Migration/evolution:** Node-type definitions can be registered/updated at runtime via the JCR NodeTypeManager / CND files; changing existing data to match a stricter type is an app-side migration. No table locks (tree, not tables); large structural reshuffles are typically done with oak-run tooling.
- **Type system:** JCR property types — String, Long, Double, Decimal, Boolean, Date, Binary, Name, Path, Reference/WeakReference, URI; single- and **multi-valued** properties. Binaries stream to the BlobStore. No native geospatial or vector types. Full-text indexing of text/binary content via Tika + Lucene.

## Query interface
- **Language:** **API-first** (the JCR `javax.jcr` Java API: get/set node, traverse, `Session.save()`). Query languages: **JCR-SQL2** and **XPath** (the JCR query languages), plus a QueryObjectModel API ([JCR API](https://jackrabbit.apache.org/jcr/jcr-api.html)). No wire protocol of its own — it is an embedded Java library (optionally exposed over **WebDAV/DAVEX** or remoting).
- **Transactions:** JCR sessions provide transient changes committed atomically per `save()`; multi-`save` transactions via JTA/XA. Underlying isolation is snapshot (see above), so multi-statement "ACID" is really snapshot-isolated, single-committer-wins.
- **Native vs app-side:** Hierarchy traversal and references are native. Queries require **explicit indexes** — Oak deliberately indexes little by default; an unindexed query *traverses the whole repository* and can be catastrophically slow ([differences](https://jackrabbit.apache.org/oak/docs/differences.html)). No SQL joins/aggregations/window functions in the relational sense; JCR-SQL2 has limited joins over the node tree.
- **Stored procedures / UDFs:** None in the DB. Logic lives in the embedding Java application (e.g. AEM components, OSGi services).

## Scaling & topology
- **Vertical vs horizontal:** SegmentNodeStore = **vertical only** (single node, scale up RAM/NVMe). DocumentNodeStore = **horizontal** for the compute/repository tier (multiple Oak instances sharing one MongoDB/RDBMS), but the shared store is the scaling bottleneck and there is no application-level sharding of the content tree itself.
- **Sharding:** No native content sharding; on MongoDB you rely on Mongo's sharding of the underlying document collection. Resharding is a Mongo concern, not Oak's.
- **Read replicas:** Via MongoDB secondaries; reads can be served from secondaries with causal-consistent sessions to preserve read-your-writes ([Mongo DocumentStore](https://jackrabbit.apache.org/oak/docs/nodestore/document/mongo-document-store.html)). Otherwise replicas can be stale.
- **Storage/compute separation:** Partially — DocumentNodeStore + external S3/Azure BlobStore separates compute (Oak instances) from durable storage (Mongo + object store). Not a Snowflake/Aurora-grade design. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** SegmentNodeStore appends immutable segments to tar files; commits create new immutable revisions (copy-on-write up the tree). DocumentNodeStore persists revisions to Mongo/RDB. Durability of the **data-loss window on crash** therefore depends on the backend's fsync/write-concern config (Mongo write concern, RDB commit) — ⚠️ unverified for a precise default window; for Mongo it is governed by the configured write concern. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Tuned for read-heavy CMS workloads with large in-memory caches (node cache, persistent cache). Write throughput on DocumentNodeStore is gated by Mongo round-trips and revision bookkeeping. p99 is sensitive to cache misses (cold reads from Mongo/segment files) and, critically, to **unindexed queries** doing full traversals.
- **Compaction / GC:** Two GC concerns. (1) **Online Revision Cleanup (OnRC)** for the segment store — Estimation → Compaction (rewrite current head into a new generation) → Cleanup (reclaim old segments); runs concurrently with live traffic and must "catch up" with concurrent commits ([Segment Tar overview](https://jackrabbit.apache.org/oak/docs/nodestore/segment/overview.html)). Compaction is historically a notorious operational pain (large repos, heap pressure, long runs) — AEM ships extensive OnRC tuning guidance. (2) **DataStore garbage collection** — mark-and-sweep of unreferenced binaries; if an external DataStore is used it must be triggered **separately** from revision cleanup ([blobstore](https://jackrabbit.apache.org/oak/docs/plugins/blobstore.html)). p99 and disk usage degrade badly if GC is misconfigured or skipped.

## Operations & maturity
- **Backup/restore, PITR:** Segment store backup = file-level copy / oak-run; DocumentNodeStore backup = back up the underlying Mongo/RDB plus the BlobStore. No built-in PITR beyond JCR **versioning** (per-node version history) and revision history (subject to OnRC reclaiming old revisions).
- **Observability:** JMX MBeans for repository internals (cache stats, GC, indexing, async index lag), query EXPLAIN to see which index a query uses, slow-query / traversal warnings in logs (heavily relied on to catch unindexed queries).
- **Upgrade story:** Oak releases are frequent and backward-compatible at the JCR API level; major content/repo migrations (e.g. JR2→Oak, or large AEM upgrades) use the **oak-upgrade** tool and are non-trivial, often offline or with downtime windows. Day-2 burden is real: index maintenance, revision/blob GC, and segment compaction are the recurring operational chores.
- **Maturity:** Very mature and battle-tested **as embedded in Adobe AEM** (one of the largest enterprise CMS deployments worldwide), so the Oak codebase sees heavy production exercise. Outside AEM, standalone Jackrabbit usage is comparatively niche. **Jepsen:** ⚠️ no Jepsen report exists for Jackrabbit/Oak (as of 2026); distributed-correctness claims rest on the backing store (e.g. MongoDB's own Jepsen history) plus Oak's documented snapshot/causal-consistency design, not on independent verification of Oak itself.
- **Known failure modes:** runaway unindexed-query traversals; segment-store compaction failing/running long on huge repos; DataStore GC not run → disk bloat; clock skew across DocumentNodeStore cluster nodes.

## Ecosystem & people
- **Canonical use cases:** Backbone of enterprise WCM/DAM — **Adobe Experience Manager / CRX** is the dominant consumer. Good fit for hierarchical content with versioning, fine-grained ACLs, full-text search, and change observation (CMS, DAM, document management).
- **Anti-patterns:** Wrong tool for relational/transactional OLTP needing serializability, for analytics/aggregation, for very high write throughput, for flat key-value access, or for anything needing joins across heterogeneous datasets. Also a poor fit if you do not want a JVM/embedded-library deployment. Deep, wide trees and ad-hoc unindexed queries are foot-guns.
- **Drivers / connectors:** JCR Java API; access via WebDAV/DAVEX, oak-run CLI; CDC/Kafka/dbt/BI integrations are not first-class (content-repo, not analytics). Tika for content extraction; Lucene for indexing.
- **Community / support:** Apache project, active (Oak 1.6x line shipping into the mid-2020s). Commercial support effectively flows through Adobe (AEM). Docs are thorough but uneven — several Oak architecture pages are explicitly marked incomplete/TODO. Steep learning curve: the JCR model, Oak's MVCC/refresh semantics, and index management all surprise newcomers.

## Licensing & cost
- **OSS license & flavor:** **Apache License 2.0** — permissive, no copyleft, no post-2018 source-available relicensing ([Oak license](https://jackrabbit.apache.org/oak/docs/license.html)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Self-managed open source. The widely-used *managed* form is Adobe AEM (CRX is Adobe's commercial packaging of Oak), which carries Adobe licensing and lock-in via AEM-specific APIs/components — but Oak itself is free.
- **Cost model:** No per-node/per-core licensing for the OSS library; cost is infrastructure (JVM hosts, MongoDB/RDB, object storage for blobs) plus operational effort. At scale, cost is dominated by the MongoDB/RDB tier and the engineering time for index/GC/compaction maintenance. AEM, by contrast, is enterprise-priced.

## Hardware / deployment
- **Resource profile:** **Memory-bound and JVM-heavy.** Heavily reliant on large heap + node/persistent caches; the hot working set should fit in RAM for good p99. Segment compaction can be memory-intensive. CPU matters for query/index and content extraction.
- **Storage assumptions:** Segment store benefits from fast local **NVMe/SSD** (append-only tar files + compaction rewrites). DocumentNodeStore tolerates network-attached storage indirectly via MongoDB. Binaries belong in a BlobStore (filesystem/S3/Azure), not inline.
- **Footprint:** Embedded Java library — runs **in-process** in your JVM/OSGi container (single-node segment) or as a cluster of JVMs over shared Mongo/RDB. Not serverless.
- **Deployment:** On-prem or self-hosted cloud VMs; runnable in containers/k8s but it is a stateful JVM service (StatefulSet realities: persistent volumes for segment store, careful cluster-node-id and lease handling for DocumentNodeStore). No first-party SaaS (AEM-as-a-Cloud-Service is Adobe's hosted offering).

## Bottom line
Reach for Jackrabbit/Oak when you need a **hierarchical content repository** — versioned, ACL-rich, full-text-searchable, observable content in a Java stack — especially if you are building on or alongside AEM. Do not reach for it as a general-purpose database: it gives **snapshot isolation, not serializability** (write skew is documented), it is API-first rather than SQL, and it scales by leaning on MongoDB/RDB rather than sharding the content tree itself. The single biggest gotcha: **queries without an explicitly created index silently fall back to full-repository traversal** and will destroy performance — index discipline (plus diligent revision/blob GC and segment compaction) is the day-2 cost of running it.

## Sources
- [Apache Jackrabbit — JCR home](https://jackrabbit.apache.org/jcr/index.html)
- [Apache Jackrabbit — JCR API](https://jackrabbit.apache.org/jcr/jcr-api.html)
- [Jackrabbit Oak documentation](https://jackrabbit.apache.org/oak/docs/)
- [Oak — Differences to Jackrabbit 2 (MVCC, snapshot isolation, write skew, indexing, observation)](https://jackrabbit.apache.org/oak/docs/differences.html)
- [Oak — Conflict handling through rebasing branches](https://jackrabbit.apache.org/archive/wiki/JCR/Conflict-handling-through-rebasing-branches_115513383.html)
- [Oak — DocumentNodeStore (documentmk)](https://jackrabbit.apache.org/oak/docs/nodestore/documentmk.html)
- [Oak — MongoDB DocumentStore (causal consistency, read preference)](https://jackrabbit.apache.org/oak/docs/nodestore/document/mongo-document-store.html)
- [Oak — Segment Tar overview (TarMK, Online Revision Cleanup / compaction)](https://jackrabbit.apache.org/oak/docs/nodestore/segment/overview.html)
- [Oak — Blob Store (mark-and-sweep DataStore GC)](https://jackrabbit.apache.org/oak/docs/plugins/blobstore.html)
- [Oak — Lucene Index (async indexing)](https://jackrabbit.apache.org/oak/docs/query/lucene.html)
- [Oak — License (Apache 2.0)](https://jackrabbit.apache.org/oak/docs/license.html)
