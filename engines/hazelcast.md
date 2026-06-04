---
name: Hazelcast
slug: hazelcast
rank: 68
data_model: Key-value (in-memory data grid)
license: Apache 2.0 + Hazelcast Community License (open core); Enterprise commercial
summary: In-memory distributed data grid + stream-processing engine; fast AP caches by default, with an opt-in Raft-backed CP subsystem for the few things that must be linearizable.
last_researched: 2026-06-04
confidence: high
---

# Hazelcast

> A JVM-embedded in-memory data grid that gives you fast partitioned AP maps/caches plus an integrated stream-processing engine (ex-Jet), with a separate Raft-based CP subsystem you must explicitly use when you need real linearizability.

## Identity
- **Taxonomy / data model:** distributed in-memory data grid (IMDG); primarily a partitioned key-value store (`IMap`, `ICache`) plus distributed collections (queue, set, list, ringbuffer), concurrency primitives (locks, semaphores, atomics), pub/sub, and a SQL/stream engine. Multi-model in practice but key-value at the core. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** in-memory primary store, data partitioned across cluster members (271 partitions by default) with one configurable backup replica. Not LSM/B-tree — it is a hash-partitioned heap/off-heap store, not a disk engine ([lsm-vs-btree](../concepts/lsm-vs-btree.md) is largely N/A). Optional on-disk **Persistence** (Enterprise) and **Tiered Storage** spill memory to disk; the High-Density (off-heap) store avoids GC pressure.
- **Workload:** OLTP-style low-latency caching/serving, plus stream/batch processing via the embedded engine (formerly **Hazelcast Jet**, merged into the core in 5.0). Not an analytical warehouse. SQL exists for querying maps and streams, not for ad-hoc OLAP over large cold datasets.

## Distribution & consistency
- **Two regimes — this is the central fact about Hazelcast:**
  - **AP (default) data structures** — `IMap`, `ICache`, queues, sets, etc. Use partitioning + lazy/async backup replication, *not* consensus. They favor availability; under failure or partition, writes can be **lost** ([Hazelcast docs explicitly state increments "can be lost if a member fails"](https://docs.hazelcast.com/hazelcast/5.5/cp-subsystem/cp-subsystem)). No linearizability.
  - **CP subsystem** — opt-in, Raft-backed ([consensus-raft-paxos](../concepts/consensus-raft-paxos.md)) structures: `FencedLock`, `IAtomicLong`, `IAtomicReference`, `ICountDownLatch`, `ISemaphore` (and `CPMap`, which is **Enterprise-only**, added in 5.4 ([CPMap docs](https://docs.hazelcast.com/hazelcast/5.5/data-structures/cpmap))). These are **linearizable** and prefer **consistency over availability** during partitions ([docs](https://docs.hazelcast.com/hazelcast/5.5/cp-subsystem/cp-subsystem); [3.12 intro](https://hazelcast.com/blog/hazelcast-imdg-3-12-introduces-cp-subsystem/)). **Note (5.5):** the open-source CP subsystem is *deprecated in the Community Edition* and no longer recommended for production; Hazelcast positions the persistence-backed CP subsystem as Enterprise ([Community Edition changes](https://hazelcast.com/blog/changes-to-community-edition/)).
- **CAP under partition:** depends on which API you use. AP structures = **AP** (stay up, may lose/diverge data). CP subsystem = **CP** (majority side serves, minority gets operation timeouts). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** AP structures ≈ **PA/EL** (available under partition; favor latency else). CP subsystem ≈ **PC/EC** (refuse on minority partition; pay latency for consistency).
- **Default isolation & what's achievable:** there is no global SQL transaction isolation in the classic relational sense. Hazelcast offers a transaction API over maps/queues with `ONE_PHASE` and `TWO_PHASE` modes giving read-committed-style behavior, but these run on AP structures and are not a substitute for serializable cross-key ACID. Real linearizable semantics exist only inside the CP subsystem, per-object. ⚠️ unverified — there is no documented multi-key serializable transaction guarantee across the grid. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** intra-cluster is single-leader-per-partition with synchronous-or-async backups (`backup-count`, `async-backup-count`). Cross-datacenter is **WAN Replication** (Enterprise), which is async multi-cluster — eventually consistent, last-writer-wins style; not for strong cross-region consistency. See [replication-models](../concepts/replication-models.md).
- **Split-brain:** AP side uses a **split-brain protection** (quorum) setting plus **merge policies** (e.g. `PutIfAbsentMergePolicy`, `LatestUpdateMergePolicy`) to reconcile on heal — meaning silent conflict resolution and possible lost updates by design. The CP subsystem prevents split-brain outright by requiring a Raft majority.
- **Tunable consistency:** yes, but coarse — you choose AP vs CP per data structure, and tune backup counts and quorum sizes, rather than per-query consistency levels.
- **Clock dependency:** correctness of the CP subsystem rests on Raft, not on synchronized clocks. AP merge policies like "latest update" *do* compare timestamps, so wall-clock skew can affect which write wins on merge. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Maps store arbitrary serialized objects; there is no enforced schema on write. SQL and predicates query over fields via reflection or the **Compact/Portable** serialization formats that expose a queryable schema.
- **Migration/evolution:** schema lives in app code / serialization config; Compact serialization supports field evolution without a central DDL. No locking `ALTER` because there is no rigid table schema. SQL `CREATE MAPPING` declares how to read a map as a table.
- **Type system:** standard Java/serialized types; JSON via `HazelcastJsonValue` with queryable fields; geospatial and vector search are not core strengths. No native interval/array DB types like a relational engine.

## Query interface
- **Language:** Java/JVM API is primary (also clients for .NET, C++, Python, Node.js, Go). **SQL** (ANSI-ish) queries maps and streaming sources; a predicate API and distributed `EntryProcessor` for server-side compute. Stream/batch pipelines via the Jet-derived Pipeline API.
- **Transactions:** map/queue transaction API (1PC/2PC), single-object atomicity on AP structures, linearizable single-object operations (CAS, atomics) on CP. No general multi-statement SQL ACID across many keys.
- **Native vs app-side:** native secondary indexes (sorted/hash/bitmap) on map fields; native aggregations and predicate queries run in-cluster (data-local execution); SQL joins exist but joins across large distributed maps are limited compared to a real RDBMS.
- **Stored procedures / UDFs:** `EntryProcessor` and `ExecutorService` run user Java code on the members holding the data (move-compute-to-data). User-defined SQL functions are limited.

## Scaling & topology
- **Horizontal, peer-to-peer.** Members form a cluster (no master node); data auto-partitions and rebalances when members join/leave. Elastic scale-out is a headline feature.
- **Sharding:** automatic via consistent partitioning (fixed 271 partitions by default), with automatic data migration on membership change — resharding is largely transparent, though large rebalances move a lot of memory and can stress the network.
- **Read replicas / read consistency:** backups are not read by default (reads go to the primary partition owner) unless `read-backup-data` is enabled, which then allows **stale reads**. Near-cache on clients trades freshness for latency.
- **Storage/compute separation:** classic embedded mode co-locates storage and compute in the JVM. Client-server mode separates app from data tier, but members still own both storage and compute — not a Snowflake/Aurora-style disaggregation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** in-memory by default; durability comes from in-cluster backup replicas (sync or async), **not** a WAL. A crash before a backup is acknowledged loses that write. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Durability on disk:** **Persistence** (Enterprise) writes map/JCache entries and CP subsystem state to disk for fast member/cluster restart; without it, a full cluster restart loses all data. ⚠️ unverified — exact fsync/group-commit semantics of Persistence are version-specific; treat the "data-loss window" as nonzero unless sync backups + persistence are explicitly configured.
- **Throughput/latency:** sub-millisecond reads/writes for in-memory AP operations are typical; designed for high throughput. CP operations pay Raft round-trip latency. p99 tails are driven by **JVM GC** (mitigated by the off-heap High-Density store), partition migration during scaling, and network.
- **Compaction/vacuum/GC:** no LSM compaction. The dominant tail-latency factor is JVM garbage collection on the heap store; off-heap storage is the standard remedy. Eviction/expiry policies (LRU/LFU/TTL) bound memory.

## Operations & maturity
- **Backup/restore, PITR:** Enterprise Persistence + Tiered Storage provide disk durability and faster restarts; there is no true point-in-time-recovery log like an RDBMS. Backups here mean replica copies, not snapshot archives by default.
- **Observability:** Management Center (web UI), JMX/Prometheus metrics, slow-operation detection, SQL `EXPLAIN` for query plans, diagnostics logs.
- **Upgrade story:** **rolling upgrades** of members are supported in Enterprise; OSS upgrades may require more care. Day-2 burden centers on JVM/GC tuning, memory sizing, partition-migration impact, and split-brain merge-policy choices.
- **Maturity:** mature (since 2008), widely deployed for caching and grids. **Jepsen:** the AP core (Hazelcast 3.8.3) was tested and found to **lose updates / not be safe under partition** as expected for an AP system ([Jepsen analysis 3.8.3](https://hazelcast.com/blog/jepsen-analysis-hazelcast-3-8-3/)). The **CP subsystem was then built and Jepsen-tested** (`IAtomicLong`, `IAtomicReference`, `ISemaphore`, `FencedLock`); Hazelcast reported fixing all discovered bugs and maintaining linearizability across client/server failures and partitions ([Testing the CP Subsystem with Jepsen](https://hazelcast.com/blog/testing-the-cp-subsystem-with-jepsen/)). Note the CP test suite used a **static CP member set and did not crash CP members** during runs — a known coverage gap.

## Ecosystem & people
- **Canonical use cases:** distributed caching / cache-aside in front of an RDBMS, session/store clustering, fast key-value serving, distributed locks/semaphores (via CP), real-time stream processing and stateful enrichment, microservice data sharing.
- **Anti-patterns:** system of record for critical data without Enterprise persistence + sync backups (AP loses writes); needing serializable multi-key transactions; large-scale OLAP/analytics over cold data; cross-region strong consistency (WAN is async); treating default `IMap` as if it were linearizable — it is not.
- **Drivers/connectors:** clients in Java, .NET, C++, Python, Node.js, Go; JCache (JSR-107) and Spring Cache integration; connectors for Kafka, JDBC/CDC sources, files, S3 via the pipeline engine; integrates as a Hibernate/JPA L2 cache.
- **Community/support:** established open-source community, commercial support from Hazelcast, Inc., good docs, managed **Hazelcast Cloud (Viridian)** offering. Learning curve moderate; the AP-vs-CP distinction is the main conceptual trap.

## Licensing & cost
- **OSS license & flavor:** **open core**. Most of the core is **Apache 2.0**, but a growing set of modules (e.g. `hazelcast-sql`, and various features) are under the **source-available Hazelcast Community License** — which is **identical to the Confluent Community License 1.0** (an "Excluded Purpose"/no-competing-SaaS clause) ([announcement](https://hazelcast.com/blog/announcing-the-hazelcast-community-license/)). The `hazelcast-sql` module specifically moved from Apache 2.0 to the Community License (post-2018 relicensing). Enterprise features (High-Density store, Persistence, WAN replication, security suite, CP subsystem persistence, `CPMap`, rolling upgrades) are **commercial-only** ([editions docs](https://docs.hazelcast.com/hazelcast/5.6/getting-started/editions)). As of 5.5 the open-source CP subsystem is **deprecated in the Community Edition** and steered toward Enterprise ([Community Edition changes](https://hazelcast.com/blog/changes-to-community-edition/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** both — self-host OSS/Enterprise, or use Hazelcast Cloud (managed). Lock-in risk via Enterprise-only durability/security features.
- **Cost model:** Enterprise is license/subscription-based (typically per-node/per-cluster); managed cloud is consumption-based. Cost at scale is driven by **RAM** (this is an in-memory grid) — large datasets get expensive fast versus disk-based stores.

## Hardware / deployment
- **Resource profile:** **memory-bound** — the working set (or all data) generally must fit in cluster RAM (Tiered Storage relaxes this in Enterprise). CPU matters for stream processing and serialization; GC tuning is significant on the heap store.
- **Storage assumptions:** primarily RAM; disk only for Persistence/Tiered Storage, where local NVMe is preferred for restart speed. Network bandwidth matters for partition migration and backups.
- **Footprint:** **embedded** (library inside your JVM app) or **client-server** (dedicated member cluster). Clustered by design; no single-node-only embedded DB story like SQLite.
- **Deployment:** on-prem, cloud, or managed; first-class **Kubernetes** support with auto-discovery and a Helm/operator path; StatefulSet realities (stable identity, persistent volumes for Enterprise persistence) apply.

## Bottom line
Reach for Hazelcast when you need a fast, elastic, JVM-native distributed cache or data grid with optional integrated stream processing, and you understand that the default `IMap`/`ICache` structures are **AP and can lose writes** — Jepsen confirmed the AP core is not safe under partition, by design. Use the **CP subsystem** (Raft, Jepsen-tested linearizable) for the small set of objects that genuinely need locks/atomics with correctness. Do not use it as a durable system of record without Enterprise persistence and synchronous backups, and never assume a default map is consistent. The single biggest gotcha: the strong-consistency story applies only to CP-subsystem structures you explicitly opt into — everything else is eventually-consistent in-memory state.

## Sources
- [CP Subsystem | Hazelcast Documentation (5.5)](https://docs.hazelcast.com/hazelcast/5.5/cp-subsystem/cp-subsystem)
- [Hazelcast IMDG 3.12 Introduces CP Subsystem](https://hazelcast.com/blog/hazelcast-imdg-3-12-introduces-cp-subsystem/)
- [Testing the CP Subsystem with Jepsen](https://hazelcast.com/blog/testing-the-cp-subsystem-with-jepsen/)
- [Jepsen Analysis on Hazelcast 3.8.3](https://hazelcast.com/blog/jepsen-analysis-hazelcast-3-8-3/)
- [Hazelcast editions and distributions (5.6 docs)](https://docs.hazelcast.com/hazelcast/5.6/getting-started/editions)
- [Hazelcast Editions and Licenses (5.0 docs)](https://docs.hazelcast.com/hazelcast/5.0/getting-started/editions)
- [Changes to Community Edition (CP subsystem deprecation)](https://hazelcast.com/blog/changes-to-community-edition/)
- [CPMap | Hazelcast Documentation (Enterprise)](https://docs.hazelcast.com/hazelcast/5.5/data-structures/cpmap)
- [Announcing the Hazelcast Community License](https://hazelcast.com/blog/announcing-the-hazelcast-community-license/)
- [Hazelcast Architecture | Documentation](https://docs.hazelcast.com/hazelcast/5.5/architecture/architecture)
