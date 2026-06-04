---
name: Ehcache
slug: ehcache
rank: 89
data_model: Key-value (in-process Java cache)
license: Apache 2.0 (Ehcache lib + OSS Terracotta Server); commercial Terracotta features from IBM
summary: The de-facto JVM-embedded key-value cache (JSR-107/JCache), with an optional Terracotta clustered tier for cross-JVM sharing — a cache library, not a database of record.
last_researched: 2026-06-04
confidence: high
---

# Ehcache

> The default in-process cache for Java/Hibernate/Spring apps: a tiered (heap → off-heap → disk/clustered) key-value store that is a transient performance layer, not a system of record — it explicitly drops disk-tier data on an unclean JVM crash.

## When to use

**Use Ehcache if:**
- ✅ You have a JVM app (especially Hibernate second-level cache or Spring `@Cacheable`) needing a standard JSR-107/JCache in-process cache in front of a real DB.
- ✅ You want to scale a single process's cache vertically into large off-heap working sets (tested to ~6 TB off-heap) outside GC reach.
- ✅ You need cross-JVM shared caching via the Terracotta clustered tier, with a choice of eventual or strong consistency per cache.

**Avoid Ehcache if:**
- ❌ You need a system of record: the OSS disk tier wipes itself on an unclean crash ("persistent" means survives a clean shutdown only) — crash-consistent restart needs the commercial Terracotta Fast-Restart store.
- ❌ You expect cross-node consistency without the Terracotta tier — each JVM caches independently and stale reads across instances are the norm.
- ❌ You need queries, secondary indexes, joins, or analytics — it is API-only get/put (Ehcache 3 dropped the 2.x Search API).
- **Taxonomy / data model:** Embedded key-value cache for the JVM, exposing a `Map`-like get/put interface and implementing the [JSR-107 JCache](../concepts/license-taxonomy.md) standard API. It is a caching *library* that lives in your application's heap, not a standalone database server. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) — it sits in front of an OLTP system of record, not as one.
- **Storage model:** Tiered. Heap tier (on-heap Java objects, no serialization, fastest); off-heap tier (direct memory outside GC, requires serialization); disk tier (persistent file store); clustered tier (data held in a [Terracotta Server Array](../concepts/storage-compute-separation.md) shared across JVMs). Multi-tier setups must be "pyramidal" (heap < off-heap < disk/clustered), a heap tier is always required, and disk + clustered tiers cannot be combined ([tiering docs](https://www.ehcache.org/documentation/3.3/tiering.html)). On-disk format is a Terracotta proprietary serialized store, not a queryable file format. Not [LSM or B-tree](../concepts/lsm-vs-btree.md) — it is a hash-based cache keyed by object identity.
- **Workload:** Caching layer for OLTP read paths (Hibernate second-level cache, Spring `@Cacheable`, session storage). Not analytical, not HTAP — no scans, no aggregation, no query engine.

## Distribution & consistency
- **Single-node default:** Without the clustered tier, Ehcache is in-process and per-JVM — each application instance has its own independent cache, so "consistency" across nodes is N/A and stale reads across instances are the norm.
- **Clustered tier ([CAP](../concepts/cap-pacelc.md)):** With Terracotta, two consistency modes are offered: **eventual** ("the visibility of a write operation is not guaranteed when the operation returns", monotonic per-client) and **strong** ("when a write operation returns other clients will be able to observe it immediately", at higher write latency) ([clustered-cache docs](https://www.ehcache.org/documentation/3.5/clustered-cache.html)). Strong mode is effectively CP (writes coordinate through the active server); eventual mode is AP-leaning (writes return without cross-client visibility).
- **PACELC:** ⚠️ unverified — not stated in PACELC terms by the docs. In practice: under partition the client loses the clustered tier and falls back to its local tiers; else, strong mode trades latency for consistency (EL/C) while eventual mode favors latency (EL/L).
- **Isolation:** Per-key atomic operations (`putIfAbsent`, `replace`, etc.). Multi-key transactional isolation is **not** part of the core cache; see Query interface for the separate XA/JTA support, which is a v2.x feature. Do not read "ACID" into a clustered cache — see [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** The Terracotta Server Array uses partitioned "Mirror Groups" (a.k.a. "stripes"): each group has exactly one **active** server plus one or more **mirror** (hot-standby) servers that replicate the active's data, and on active failure an **election** promotes a fully-synchronized mirror to active while clients continue ([Terracotta/BigMemory HA docs](https://documentation.softwareag.com/terracotta/terracotta_439/bigmemory-max/webhelp/bigmemory-max-webhelp/co-arch_cluster_with_ha.html)). This is single-leader-per-partition replication; see [replication-models](../concepts/replication-models.md). ⚠️ unverified — no public [Jepsen](https://jepsen.io) report exists for the Terracotta consistency claims, so the strong-consistency guarantee under partition/failover is vendor-asserted, not independently verified.
- **Tunable consistency:** Yes, per clustered cache (eventual vs strong).
- **Clock dependency:** No correctness dependency on synchronized clocks; consistency is server-coordinated, not timestamp-ordered. See [clocks-and-time](../concepts/clocks-and-time.md). TTL/TTI expiry uses local clocks (cosmetic, not a correctness boundary).

## Schema
- **Schema-on-read / schemaless:** No schema. Entries are typed key→value pairs `Cache<K,V>` defined in Java generics; the "schema" lives entirely in application code.
- **Migration/evolution:** N/A — no DDL. Changing serialized value classes across versions risks deserialization failures in off-heap/disk/clustered tiers; you manage serializer compatibility yourself.
- **Type system:** Whatever Java types you cache; non-heap tiers require the value be serializable (Java serialization or a custom `Serializer`). No native JSON/geospatial/vector/interval types — it stores opaque serialized blobs.

## Query interface
- **Language:** API-only. The JSR-107 `javax.cache` / JCache API plus Ehcache's native `org.ehcache` API — get/put/remove/`putIfAbsent`/CAS-style `replace`. No query language, no secondary indexes, no joins, no aggregation. (Ehcache 2.x had a "Search API"; Ehcache 3 does not.)
- **Transactions:** Core cache offers **single-key atomicity** only. Ehcache 2.x supported full XA — "a fully XA compliant resource participating in two-phase commit and recovery" — so a cache change commits or rolls back with the DB in the same JTA transaction ([2.8 transactions docs](https://www.ehcache.org/documentation/2.8/apis/transactions.html)). ⚠️ unverified — XA support in Ehcache 3 is more limited than 2.x; confirm against the 3.x version you deploy.
- **Native vs app-side:** No server-side joins/indexes/aggregations — all read logic is application-side. Cache loaders/writers (write-through, write-behind) integrate with the backing store; write-behind is **not** recommended with XA caches because the deferred write cannot join the same transaction.
- **Stored procedures / UDFs:** None.

## Scaling & topology
- **Vertical:** Scale a single JVM's cache by adding off-heap memory — Ehcache has been tested storing up to 6 TB off-heap in a single process ([Terracotta features](https://www.terracotta.org/about/features.html)).
- **Horizontal:** Only via the Terracotta Server Array, which auto-partitions keys by consistent hashing across active/mirror Mirror Groups. Resharding/rebalancing is managed by the server tier. Without Terracotta there is no horizontal sharing — each app node caches independently.
- **Read replicas:** Mirror servers are hot standbys, not load-balanced read replicas; reads go to the active for a partition. Local heap/off-heap tiers act as near-cache in front of the clustered tier.
- **Storage/compute separation:** The clustered topology separates cache storage (Terracotta servers) from compute (app JVMs holding a hot subset) — see [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** In-memory first. The **disk tier persists only on a clean `close()`** — "Ehcache 3 only offers persistence in the case of clean shutdowns. If the JVM crashes there is no data integrity guarantee," and Ehcache **wipes the disk store** on detecting an unclean shutdown ([tiering docs](https://www.ehcache.org/documentation/3.3/tiering.html)). So the open-source disk tier is **not** a durable WAL-backed store — the crash data-loss window is *everything*. See [wal-and-durability](../concepts/wal-and-durability.md). (The commercial Terracotta "Fast Restart"/FRS store adds crash-consistent restartable persistence; that is a paid IBM feature, not in the OSS build.)
- **Throughput/latency:** Heap-tier reads are sub-microsecond (no serialization); off-heap/disk add serialization cost; clustered tier adds a network round trip (and, in strong mode, a coordination round trip on writes). p99 is dominated by GC pauses when large data is kept on-heap — the off-heap tier exists precisely to move bulk data out of GC reach.
- **Compaction / GC:** No LSM compaction. The relevant GC concern is the **JVM garbage collector**: large on-heap caches cause long stop-the-world pauses and p99 spikes; off-heap storage mitigates this. Eviction is by configured capacity (LRU-ish) and TTL/TTI expiry.

## Operations & maturity
- **Backup/restore / PITR:** None in the OSS cache model — it is a transient cache; the system of record is your backing database. The commercial Terracotta tier adds restartable persistence and backup tooling.
- **Observability:** JMX/statistics API, cache hit/miss/eviction counters, JSR-107 management/statistics MXBeans. No query plans (no queries). The commercial Terracotta Management Console adds cluster-wide monitoring.
- **Upgrade story:** Library upgrade = bump the dependency and redeploy the app; no rolling DB upgrade. Major version jumps (2.x → 3.x) are **breaking** — the 3.x API and config were rewritten and are not source-compatible with 2.x. Clustered/Terracotta server upgrades follow the Terracotta server lifecycle.
- **Maturity:** Very mature; created by Greg Luck in 2003, project control acquired by Terracotta (2009), then Software AG (2011), and the Terracotta/Ehcache business passed to IBM via IBM's 2024 acquisition of Software AG's StreamSets/webMethods enterprise products ([IBM newsroom, July 2024](https://newsroom.ibm.com/2024-07-01-IBM-Completes-Acquisition-of-StreamSets-and-webMethods,-Bolstering-its-Automation,-Data-and-AI-Portfolios)). Ehcache **3.11.1** (Aug 2024) is described in its own release notes as "the first new release under IBM ownership"; it bundles the Terracotta Platform 5.10.x server tier ([GitHub releases](https://github.com/ehcache/ehcache3/releases)). Known failure modes: GC pauses from oversized on-heap caches; silent staleness when used per-JVM without the clustered tier; disk-store wipe on crash. ⚠️ unverified — no Jepsen analysis of the clustered consistency modes exists.

## Ecosystem & people
- **Canonical use cases:** Hibernate/JPA second-level cache, Spring Cache abstraction (`@Cacheable`), HTTP session caching, read-through caching of a slow backing store, reference-data caching. Since Hibernate 6 the standard plug-in path is via JCache using `org.ehcache.jsr107.EhcacheCachingProvider`.
- **Anti-patterns:** Using it as a database of record (no durability guarantee on crash); expecting cross-node consistency without the Terracotta tier (each JVM is independent); caching huge datasets on-heap (GC pauses); anything needing queries, secondary indexes, or analytics. For a remote shared cache without bundling Terracotta, [redis](redis.md) or [memcached](memcached.md) are the usual alternatives; on the JVM, [hazelcast](hazelcast.md) and [apache-ignite](apache-ignite.md) compete on the distributed side.
- **Drivers/connectors:** It is itself a Java library (Maven/Gradle dependency). Integrates with Spring, Hibernate, and any JCache consumer. No native CDC/Kafka/dbt/BI connectors — it is a cache, not a data source.
- **Community/support/docs:** Large historical install base via Hibernate; docs at ehcache.org are solid but version-fragmented (2.x vs 3.x differ substantially). Commercial support from IBM/Terracotta. Learning curve is low for the basic library; the clustered Terracotta deployment is meaningfully more complex.

## Licensing & cost
- **OSS license:** The Ehcache 3 library is **Apache License 2.0** (permissive) ([Ehcache license page](https://www.ehcache.org/about/license.html)). The open-source Terracotta Server is now also stated to be under the **Apache License 2.0** ([Terracotta license page](https://www.terracotta.org/about/license.html)) — earlier owners had distributed it under the Terracotta Public License 2.0 (a Mozilla-Public-License-style license), so older references to "TPL 2.0" are stale; verify for the version you ship. See [license-taxonomy](../concepts/license-taxonomy.md). The OSS-vs-commercial split is open-source core with paid Fast-Restart persistence, advanced management, and security available in commercially supported versions from IBM.
- **Self-managed vs managed:** Self-managed; embed the library and (optionally) run your own Terracotta servers. No first-party SaaS. Lock-in is low for the OSS cache API (JSR-107 is portable) but higher once you depend on commercial Terracotta features.
- **Cost model:** OSS library is free; commercial Terracotta is licensed (per-server / enterprise terms via IBM). Cost scales with the Terracotta server footprint, not per-query.

## Hardware / deployment
- **Resource profile:** Memory-bound — the whole point is keeping hot data in RAM (heap or off-heap). Off-heap lets a single process hold multi-TB working sets outside GC. CPU cost is mostly serialization for non-heap tiers.
- **Storage assumptions:** Disk tier is local file storage (NVMe/SSD beneficial); it is a cache spill/restart store, not a durable database, so storage-latency tolerance is loose. Clustered tier holds data in Terracotta server off-heap memory.
- **Footprint:** **Embedded** in the application JVM (single-node library) by default; **clustered** when paired with a Terracotta Server Array. No serverless model.
- **Deployment:** Library ships inside your app artifact. Terracotta servers run on-prem or in containers (official Docker images exist); k8s deployment of the server array is a StatefulSet-style stateful workload. See [embedded-databases](../concepts/embedded-databases.md).

## Bottom line
Reach for Ehcache when you have a JVM application (especially Hibernate/Spring) that needs a fast, standard (JSR-107) in-process cache in front of a real database — it is the path-of-least-resistance JVM cache and scales vertically to large off-heap working sets. Do **not** treat it as a system of record or assume cross-node consistency: without the Terracotta tier each JVM caches independently, and the open-source disk tier **wipes itself on an unclean crash**. The single biggest gotcha is exactly that durability cliff — "persistent" in the OSS build means "survives a clean shutdown," not "survives a crash"; crash-consistent restart requires the commercial Terracotta Fast-Restart store.

## Sources
- [Ehcache 3 tiering documentation](https://www.ehcache.org/documentation/3.3/tiering.html) (tiers, valid combinations, clean-shutdown-only persistence)
- [Ehcache 3.5 clustered cache documentation](https://www.ehcache.org/documentation/3.5/clustered-cache.html) (eventual vs strong consistency)
- [Ehcache 2.8 transactions documentation](https://www.ehcache.org/documentation/2.8/apis/transactions.html) (XA/JTA support)
- [Ehcache 3.1 JSR-107 provider documentation](https://www.ehcache.org/documentation/3.1/107.html)
- [Terracotta features](https://www.terracotta.org/about/features.html) (6 TB off-heap "tested at 6TB RAM in a single process")
- [Terracotta/BigMemory high-availability docs](https://documentation.softwareag.com/terracotta/terracotta_439/bigmemory-max/webhelp/bigmemory-max-webhelp/co-arch_cluster_with_ha.html) (Mirror Groups / stripes, active+mirror, election failover)
- [Ehcache license page](https://www.ehcache.org/about/license.html) and [Terracotta license page](https://www.terracotta.org/about/license.html) (Apache 2.0)
- [Ehcache 3 GitHub releases](https://github.com/ehcache/ehcache3/releases) (3.11.1, "first new release under IBM ownership")
- [IBM completes acquisition of StreamSets and webMethods, July 2024](https://newsroom.ibm.com/2024-07-01-IBM-Completes-Acquisition-of-StreamSets-and-webMethods,-Bolstering-its-Automation,-Data-and-AI-Portfolios)
- [Ehcache — Wikipedia](https://en.wikipedia.org/wiki/Ehcache) (history, ownership)
