---
name: Infinispan
slug: infinispan
rank: 130
data_model: Key-value (in-memory data grid)
license: Apache 2.0 (permissive); Red Hat Data Grid is the commercial build
summary: JVM in-memory key/value data grid for distributed caching, with optional query, transactions, and persistence — a cache first, a database second.
last_researched: 2026-06-04
confidence: high
---

# Infinispan

> A clustered, JVM-native in-memory key/value data grid (the engine behind Red Hat Data Grid) built primarily as a distributed cache — it can do transactions, query, and disk persistence, but its consistency model is weaker than a real database and that is the load-bearing caveat.

## When to use

**Use Infinispan if:**
- ✅ You need a clustered, JVM-friendly in-memory data grid for distributed caching, HTTP session/state clustering, or a JCache/Hibernate L2 cache.
- ✅ You are in a Red Hat / Quarkus / Keycloak ecosystem and want commercial hardening via Red Hat Data Grid, with cross-site DR.
- ✅ You want elastic scale-out with multi-protocol access (Hot Rod, REST, Memcached, RESP/Redis) and optional Ickle/Lucene query.

**Avoid Infinispan if:**
- ❌ You treat it as a system of record — its own design docs state it provides neither linearizability nor session consistency, only READ_COMMITTED/REPEATABLE_READ (the biggest gotcha).
- ❌ You need serializable transactions, guaranteed durability, or atomic multi-key ops — `putAll`/`clear` are not truly atomic across nodes, and values can "go backwards" during topology changes.
- ❌ You cannot keep the working set in cluster RAM, or you take its "ACID transactions" claim at face value under partitions, async replication, or rebalancing.

## Identity
- **Taxonomy / data model:** Distributed key/value store / in-memory data grid (IMDG). Values can be opaque blobs or Protobuf-encoded objects; secondary capabilities include full-text/relational query via the Ickle language (Lucene-backed) and continuous queries. Not a relational engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).
- **Storage model:** In-memory first (JVM heap or off-heap native memory), with optional persistent cache stores (RocksDB ([lsm-vs-btree](../concepts/lsm-vs-btree.md)), single-file, JDBC, etc.) used as write-through/write-behind backing or overflow, not as a primary B-tree/LSM datastore. Entries are partitioned across nodes by consistent hashing with a configurable number of owners.
- **Workload:** OLTP-style point lookups and caching (get/put by key), session storage, and event-driven processing. Query exists but is a secondary index path, not an OLAP engine. Not HTAP.

## Distribution & consistency
- **CAP under partition:** Configurable per cache via partition-handling strategy. `ALLOW_READ_WRITES` favors availability (AP) and tolerates divergence; `DENY_READ_WRITES` and `ALLOW_READS` push minority partitions into **degraded mode** to favor consistency (CP-leaning) ([Red Hat: Partition Handling](https://docs.redhat.com/en/documentation/red_hat_data_grid/8.1/html/configuring_data_grid/partition_handling)). Default behavior historically does **not** resolve conflicts on merge — clusters heal faster but can keep divergent values ([same docs](https://docs.redhat.com/en/documentation/red_hat_data_grid/8.1/html/configuring_data_grid/partition_handling)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition, you pick A or C via the strategy above. Else (no partition), synchronous replication trades latency for consistency; asynchronous replication trades consistency for latency — async writes invalidate/update remote owners lazily so other nodes can read stale values briefly ([Infinispan READ_COMMITTED docs](https://docs.jboss.org/author/display/ISPN52/READ%20COMMITTED.html)).
- **Default isolation & what's achievable:** Only **READ_COMMITTED** and **REPEATABLE_READ** are supported; default is READ_COMMITTED. There is **no snapshot isolation and no serializability** — overlapping transactions can observe partial writes ([Infinispan consistency-guarantees design doc](https://github.com/infinispan/infinispan-designs/blob/main/Consistency-guarantees-in-Infinispan.asciidoc)). The project's own design doc states Infinispan does **not guarantee linearizability or session consistency** in distributed mode, and a thread reading the same key repeatedly may see values "go backwards" during topology changes ([same doc](https://github.com/infinispan/infinispan-designs/blob/main/Consistency-guarantees-in-Infinispan.asciidoc)). Multi-key ops (`putAll`, `clear`) are **not truly atomic** across nodes ([same doc](https://github.com/infinispan/infinispan-designs/blob/main/Consistency-guarantees-in-Infinispan.asciidoc)). Treat "ACID transactions" claims as single-cache, best-effort — far short of database-grade. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Per-cache mode — **replicated** (full copy on every node), **distributed** (N owners via consistent hash), or **invalidation**. Sync or async. No single Raft/Paxos leader for data; ownership is hash-based and rebalanced on membership change. Split-brain handled by partition-handling strategy + optional merge policy. See [replication-models](../concepts/replication-models.md), [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Tunable consistency:** Yes, coarsely — sync vs async replication, owner count, locking mode (optimistic vs pessimistic), and partition strategy are all per-cache knobs.
- **Clock dependency:** Cross-site async replication uses **vector clocks** for conflict resolution ([Infinispan 11 release notes](https://infinispan.org/blog/2020/06/15/infinispan-11)); correctness within a cluster does not rest on synchronized wall clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** for opaque values; **schema via Protobuf** when using indexed query (you register `.proto` schemas; `application/x-protostream` encoding). Plain caches are schemaless key/value maps.
- **Migration/evolution:** No table DDL. Protobuf schemas evolve by adding fields; reindexing may be needed when indexing config changes. Cache configuration (owners, mode) can be defined at runtime.
- **Type system:** Keys/values are bytes or marshalled objects (Protobuf, Java serialization, JSON, text). Indexed/query types are declared via Protobuf; Lucene-backed full-text and relational predicates available through Ickle.

## Query interface
- **Language:** Primarily a **key/value API** (get/put/replace/remove, conditional ops). Remote access via **Hot Rod** (binary), **REST**, **Memcached**, and **RESP** (Redis-compatible) protocols; embedded access via Java API. Richer querying via **Ickle** (relational + full-text DSL) ([Infinispan features](https://infinispan.org/features/)).
- **Transactions:** JTA/XA transactions on a cache with optimistic or pessimistic locking — but bounded by the weak isolation above (READ_COMMITTED / REPEATABLE_READ only, no serializable, not linearizable). Optimistic + REPEATABLE_READ adds write-skew checks (longer commit) ([Infinispan tuning](https://infinispan.org/docs/stable/titles/tuning/tuning.html)).
- **Native vs app-side:** Secondary indexes and queries are native (Lucene). Cross-cache joins are not a feature. Aggregations and grouping are limited compared to a SQL engine.
- **Stored procedures / UDFs:** Distributed execution via the `ClusterExecutor`/distributed streams API and server-side **tasks/scripts** (deployed Java tasks; JS scripting historically supported). Continuous queries and event listeners cover reactive patterns.

## Scaling & topology
- **Horizontal:** Designed for elastic scale-out. Distributed mode partitions data across nodes by consistent hash with `numOwners` copies; adding/removing nodes triggers automatic rebalancing of segments.
- **Sharding:** Automatic (consistent hashing); no manual shard keys. Resharding is the rebalance process — cheaper than disk-based stores since data is in memory, but rebalancing moves segments and competes with serving traffic.
- **Read replicas / read consistency:** Reads go to owner nodes; in async or under topology change, reads can be stale (no session consistency guarantee, see above).
- **Storage/compute separation:** No. Data lives in the JVM memory of grid nodes; persistence stores are local/shared backing, not a disaggregated storage tier. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** In-memory write applied to owners (sync replication waits for owner acks; async does not). Durability is **optional** — without a persistent cache store, a full-cluster crash loses data; with a store you choose write-through (durable, slower) or write-behind (faster, bounded data-loss window on crash). There is no database-style global WAL; durability semantics are per cache-store. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Sub-millisecond local reads; remote Hot Rod reads add network hops to owners. Off-heap storage avoids GC pressure on large datasets — important because **JVM GC pauses are the dominant p99 tail risk** for on-heap configurations.
- **Compaction / vacuum / GC:** No DB-style compaction for the in-memory grid (eviction policies bound memory: LRU/LFU/size/TTL). RocksDB cache store has its own LSM compaction. JVM garbage collection is the key p99 factor; off-heap is recommended for large grids.

## Operations & maturity
- **Backup/restore:** Cluster/cache backup-and-restore tooling in the server; persistent cache stores provide durability and cross-site replication provides DR. No PITR in the relational sense.
- **Observability:** JMX metrics, Micrometer/Prometheus metrics, query EXPLAIN-style stats are limited; access logs and server logging available. Health/topology exposed via REST and the operator.
- **Upgrade story:** Rolling upgrades supported for the server (and rolling upgrades between major versions via a remote-store shadow-cluster procedure). Day-2 burden centers on JVM/heap tuning, GC, capacity planning for in-memory data, and rebalance impact.
- **Maturity:** Mature, ~15+ years, formerly JBoss Cache lineage; backs Red Hat Data Grid and is widely used for Keycloak/WildFly session clustering. **No public Jepsen report** as of this writing. Known failure modes: split-brain divergence when partition handling is lax, stale reads under async, GC pauses, OOM on undersized heaps. The project's own consistency design doc is unusually candid about its weak guarantees ([consistency design doc](https://github.com/infinispan/infinispan-designs/blob/main/Consistency-guarantees-in-Infinispan.asciidoc)).

## Ecosystem & people
- **Canonical use cases:** L2/distributed cache in front of a database, HTTP session/state clustering (Keycloak, WildFly), JCache (JSR-107) provider, Hibernate 2nd-level cache, event-driven near-cache. **Anti-patterns:** system-of-record where you need serializable transactions, durable correctness, or linearizable reads — it is a cache, not a primary database; also a poor fit if you cannot afford to keep the working set in cluster RAM.
- **Drivers / connectors:** Hot Rod clients (Java, C++, C#, Go, Python, Node.js), REST, Memcached and RESP (Redis) protocols, JCache, Spring Cache/Spring Boot, Hibernate, Quarkus extension. CDC/Kafka integration is not first-class compared to OLTP databases.
- **Community / support:** Open-source community (infinispan.org) plus commercial support and hardening via **Red Hat Data Grid**. Docs are extensive (Infinispan + Red Hat). Learning curve moderate for caching, steep if you push it toward transactional/database use.

## Licensing & cost
- **OSS license:** **Apache 2.0** — permissive, no post-2018 relicensing ([Infinispan features](https://infinispan.org/features/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Fully self-managed open source (embedded library or standalone server) and runnable on Kubernetes/OpenShift via the **Infinispan Operator**. Red Hat Data Grid is the supported subscription build; lock-in is low since the core is Apache-licensed Infinispan.
- **Cost model:** No license fee for OSS; cost is your infrastructure — primarily **RAM** (data is in memory) plus nodes for the desired owner count. Cost scales with dataset size in memory; can get expensive for large grids that must stay resident.

## Hardware / deployment
- **Resource profile:** **Memory-bound.** The working set (and replicas × numOwners) must fit in cluster RAM unless a persistent store is used for overflow. CPU matters for marshalling/query; GC tuning is critical on heap.
- **Storage assumptions:** Persistence (RocksDB/file/JDBC) is optional backing; for those, NVMe helps but the hot path is RAM. No requirement for network-attached storage.
- **Footprint:** Two modes — **embedded library** inside a JVM application, or **standalone clustered server** accessed over Hot Rod/REST/RESP. Single node works for dev; production is clustered.
- **Deployment:** On-prem or cloud; strong Kubernetes/OpenShift story via the Infinispan Operator (StatefulSet-based) and Red Hat Data Grid images. No vendor SaaS from the project itself.

## Bottom line
Reach for Infinispan when you need a clustered, JVM-friendly in-memory data grid for distributed caching, session replication, or a JCache/Hibernate cache — especially in a Red Hat/Quarkus/Keycloak ecosystem, with cross-site DR. Do **not** use it as a system of record or where you need serializable transactions, linearizable reads, or guaranteed durability: its own design docs state it provides neither linearizability nor session consistency and only READ_COMMITTED/REPEATABLE_READ isolation. The single biggest gotcha is treating "ACID transactions" and "consistency" at face value — under partitions, async replication, or rebalancing, values can diverge or go backwards unless you explicitly configure (and pay the latency for) strict partition handling and synchronous replication.

## Sources
- [Infinispan consistency-guarantees design doc (project)](https://github.com/infinispan/infinispan-designs/blob/main/Consistency-guarantees-in-Infinispan.asciidoc)
- [Red Hat Data Grid: Setting Up Partition Handling](https://docs.redhat.com/en/documentation/red_hat_data_grid/8.1/html/configuring_data_grid/partition_handling)
- [Infinispan READ_COMMITTED isolation docs](https://docs.jboss.org/author/display/ISPN52/READ%20COMMITTED.html)
- [Red Hat Data Grid: Configuring transactions](https://docs.redhat.com/en/documentation/red_hat_data_grid/8.4/html/configuring_data_grid_caches/transactions)
- [Infinispan features](https://infinispan.org/features/)
- [Infinispan performance tuning guide](https://infinispan.org/docs/stable/titles/tuning/tuning.html)
- [Infinispan 11 release notes (cross-site, vector clocks)](https://infinispan.org/blog/2020/06/15/infinispan-11)
- [Infinispan Operator guide](https://infinispan.org/docs/infinispan-operator/main/operator.html)
- [Persistent cache stores](https://infinispan.org/cache-store-implementations)
