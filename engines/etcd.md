---
name: etcd
slug: etcd
rank: 52
data_model: Key-value (consensus / coordination store)
license: Apache License 2.0 (permissive)
summary: Strict-serializable Raft-backed key-value store for small, critical config/coordination data; the brain behind Kubernetes, not a general-purpose database.
last_researched: 2026-06-04
confidence: high
---

# etcd

> A small, strongly-consistent (strict-serializable) [Raft](../concepts/consensus-raft-paxos.md) key-value store for coordination and configuration — superb for cluster metadata, wrong for anything large or write-heavy.

## Identity
- **Taxonomy / data model:** Distributed key-value store specialized for **coordination/configuration**, not bulk data. Flat byte-string keys, range queries over a sorted keyspace, plus watches, leases, and a transaction primitive.
- **Storage model:** Single-node embedded **B+tree** via [BoltDB/bbolt](https://etcd.io/docs/v3.5/learning/data_model/) on each member (B-tree family, see [lsm-vs-btree](../concepts/lsm-vs-btree.md)); an **[MVCC](../concepts/mvcc.md)** layer keeps every revision of the keyspace until compacted. Each write bumps a global monotonic `revision`. Whole DB file is mmap'd, so the dataset is effectively bounded by RAM ([etcd maintenance docs](https://etcd.io/docs/v3.4/op-guide/maintenance/)).
- **Workload:** [OLTP-ish](../concepts/oltp-olap-htap.md) but extreme small-data / metadata niche — high read fanout, modest write rate, tiny total size (default 2 GB quota, recommended max **8 GB**, [maintenance docs](https://etcd.io/docs/v3.4/op-guide/maintenance/)). Not OLAP, not HTAP, not a primary app datastore.

## Distribution & consistency
- **CAP under partition:** **CP** — a minority partition cannot reach quorum and **refuses writes (and linearizable reads)** to preserve consistency; it sacrifices availability. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** **PC/EC** — under Partition it chooses Consistency; Else it still favors Consistency (linearizable reads pay a quorum round-trip) unless you opt into serializable reads for latency.
- **Default isolation:** **Strict serializability** for KV reads, writes, and multi-key transactions. Jepsen confirmed it: "we observed nothing but strict-serializable consistency for reads, writes, and even multi-key transactions, during process pauses, crashes, clock skew, network partitions, and membership changes" ([Jepsen etcd 3.4.3, 2020](https://jepsen.io/analyses/etcd-3.4.3)). This is a genuinely strong guarantee — stronger than most engines that claim "ACID." See [isolation-levels](../concepts/isolation-levels.md).
- **Tunable consistency:** Reads only. **Linearizable reads** (default) go through a quorum/ReadIndex round-trip; **serializable reads** are served by any single member, cheaper but can return stale data ([API guarantees](https://etcd.io/docs/v3.5/learning/api_guarantees/)). Writes are always linearizable via Raft.
- **Replication:** Single-leader **Raft** [consensus-raft-paxos](../concepts/consensus-raft-paxos.md); writes commit only after a **quorum** (majority) of members persist them to the [WAL](../concepts/wal-and-durability.md). Automatic leader election on failure; **no split-brain** — a minority cannot elect a leader or commit. See [replication-models](../concepts/replication-models.md).
- **Clock dependency:** Correctness does **not** depend on synchronized clocks; Raft uses logical terms/indices. Clock skew only affects election-timeout tuning, not safety (Jepsen tested under clock skew with no anomalies). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** — schemaless byte keys and values; structure lives entirely in the application (e.g., Kubernetes encodes protobuf objects under `/registry/...`).
- **Migration/evolution:** No schema, so no DDL. The notable evolution pain is the **v2→v3 API/storage break** (different data model, gRPC vs HTTP); v2 store is removed in v3.6+. No table locks because there are no tables.
- **Type system:** None — keys and values are opaque `[]byte`. No JSON/array/geospatial/vector types. Values have a hard per-value and request size limit (default 1.5 MB request).

## Query interface
- **Language:** **gRPC API** (with a gRPC-gateway JSON/HTTP shim) and the `etcdctl` CLI — **no SQL, no query DSL**. Primitives: `Put`, `Get`/`Range`, `Delete`, `Watch`, `Lease`, `Txn`, `Compact`.
- **Transactions:** A **single-shot compare-and-swap transaction** (`Txn`): a list of comparisons (on value/version/revision/lease) guarding `then`/`else` op blocks, applied atomically. **No interactive/multi-statement transactions** — you cannot hold a transaction open across round-trips.
- **Native vs app-side:** No joins, no aggregations, no secondary indexes. Range scans over the sorted keyspace are the only "query." Everything richer is app-side.
- **Stored procedures / UDFs:** None.
- **Coordination primitives:** **Watches** (ordered streaming of changes from a revision), **leases** (TTL-based key expiry; clients keep-alive), and recipes for **locks/elections** built on these.

## Scaling & topology
- **Vertical, not horizontal.** etcd does **not shard** — every member holds a full copy of the keyspace. You scale reads by adding members, but **writes do not scale out** (quorum cost grows with cluster size).
- **Cluster size:** Odd numbers, typically **3 or 5**. More members = more fault tolerance but **slower writes**; >7 is discouraged. Kubernetes strongly recommends a **static 5-member cluster** at supported scale ([Kubernetes etcd ops](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)).
- **Read replicas / learners:** Non-voting **learner** members can be added to catch up before promotion; reads from any member are serializable (possibly stale) unless linearizable mode is requested.
- **Resharding pain:** N/A — there is no sharding to reshard. The flip side: there is **no horizontal write path**, so etcd hits a hard ceiling that bigger machines only partly relieve.
- **Storage/compute separation:** None — shared-nothing, each member is local disk + local B-tree. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Every write is appended to a per-member **WAL and fsync'd** before the leader counts the replica, then committed once a quorum acks ([wal-and-durability](../concepts/wal-and-durability.md)). With default `fsync` durability the **data-loss window on a crash is effectively zero for committed writes** — a committed write survives a minority of node losses. Disk **fsync latency dominates** etcd's write latency; slow disks (especially network EBS-style volumes) wreck it.
- **Throughput/latency:** Tuned for **low-latency small writes** (single-digit to tens of ms commit on NVMe), thousands of writes/s, and high read throughput. Sensitive to **disk fsync p99 and network RTT between members**; the official guidance is dedicated fast local SSDs and a low-latency network ([performance guide](https://etcd.io/docs/v3.7/op-guide/performance/)).
- **Compaction / GC:** MVCC keeps **all revisions** until you **compact** (auto or manual). Compaction frees logical history but **fragments** BoltDB; reclaiming space to the filesystem requires a **separate `defrag`**, which **locks the member's DB** (blocking) — a real day-2 p99/availability hazard ([maintenance docs](https://etcd.io/docs/v3.4/op-guide/maintenance/)). Forgetting to compact triggers `mvcc: database space exceeded`, after which the cluster goes **read-only** until alarm is cleared.

## Operations & maturity
- **Backup/restore:** Online `etcdctl snapshot save` produces a consistent point-in-time snapshot; restore rebuilds a new cluster from it. **No built-in continuous PITR** — recovery granularity is your snapshot cadence. ⚠️ unverified — third-party operators add scheduled snapshotting, not core PITR.
- **Observability:** Rich **Prometheus metrics** (commit/fsync latency histograms, Raft proposal stats, leader changes), gRPC health/`endpoint status`, and `alarm` reporting. No query planner (no queries to plan); no slow-query log.
- **Upgrade story:** **Rolling, one minor version at a time** (e.g., 3.4→3.5→3.6); members are replaced one by one while quorum is maintained. Downgrades are historically painful/limited. Day-2 burden is real: quota/compaction/defrag management, disk-latency monitoring, and careful member replacement.
- **Maturity:** Very mature, **CNCF graduated (Nov 2020)**, the backing store of essentially every Kubernetes cluster. **Jepsen (3.4.3, 2020):** KV/txn behavior was strict-serializable; watches delivered every change in order **except** an undocumented edge case where watching from **revision 0** starts at `current+1` instead of 1 ([Jepsen](https://jepsen.io/analyses/etcd-3.4.3)). Known failure modes: **distributed locks do NOT guarantee mutual exclusion** — Jepsen saw multiple holders and ~18% lost updates with short leases, and found a bug where the server didn't re-validate the lease after a client regained the lock. Use **fencing tokens** (the lock key's revision) and treat locks as optimizations, not safety. The DB-going-read-only on quota exhaustion is the most common operational outage.

## Ecosystem & people
- **Canonical use cases:** Kubernetes control-plane state; service discovery; distributed config; leader election; feature flags; lightweight locks/coordination. Used by Kubernetes, patroni-style HA controllers (also ZooKeeper territory), Consul competes here, and CoreDNS/Calico-style infra.
- **Anti-patterns:** **Application/business data**, large values, blobs, high-volume event streams, anything that grows past a few GB or needs high write throughput — etcd will throttle, exhaust quota, and go read-only. It is **not** a cache (use [redis](redis.md)) and **not** a general KV database (use [amazon-dynamodb](amazon-dynamodb.md), [apache-cassandra](apache-cassandra.md), or a relational DB). Do not rely on its locks for correctness.
- **Drivers/connectors:** Official Go client; community clients (Python, Java/jetcd, Rust, etc.). Integrates via gRPC; no native CDC/Kafka/dbt/BI tooling (the **Watch** API is the change feed). Kubernetes is the dominant "connector."
- **Community/support:** Large, active CNCF community; excellent docs; commercial support via Kubernetes vendors (Red Hat, etc.) rather than a single etcd company. Learning curve is low to operate naively, **steep to operate safely at scale** (compaction/defrag/disk tuning).

## Licensing & cost
- **License:** **Apache 2.0**, permissive — no post-2018 relicensing, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Almost always **self-managed** (or managed *implicitly* inside a managed Kubernetes control plane like EKS/GKE/AKS, where the cloud runs etcd for you). No dominant standalone etcd-as-a-service.
- **Lock-in:** Minimal — open protocol, open data model. Migration risk is operational, not licensing.
- **Cost model:** Just infrastructure (3–5 nodes with fast SSDs); no per-core/per-GB licensing. Cost is dominated by needing **dedicated low-latency disks** and the ops time to run it correctly.

## Hardware / deployment
- **Resource profile:** **Disk-fsync-bound** on writes and **memory-bound** on dataset size — the entire BoltDB file is **mmap'd**, so plan for the dataset (≤8 GB recommended) plus headroom to live in RAM. CPU is rarely the bottleneck.
- **Storage assumptions:** Wants **dedicated, low-latency local SSD/NVMe**. Network-attached/burstable disks (and noisy-neighbor IOPS) cause leader elections and latency spikes; etcd is famously sensitive to disk and peer-network jitter ([performance guide](https://etcd.io/docs/v3.7/op-guide/performance/)).
- **Footprint:** **Clustered** (3–5 voting members) for HA; can run single-node for dev. Embeddable as a Go library but typically run as a standalone cluster.
- **Deployment:** On-prem or cloud; extremely **k8s-friendly** (it *is* k8s's store) and commonly run via StatefulSets/operators (e.g., etcd-operator) — but StatefulSet etcd needs real PersistentVolumes with good IOPS, anti-affinity across nodes/AZs, and careful disruption budgets.

## Bottom line
Reach for etcd when you need a **small, fiercely consistent** store for cluster metadata, configuration, service discovery, or leader election and you value **strict serializability and a clean Raft failure model** over scale. Do **not** use it as an application database, a cache, a queue, or for anything more than a few GB or write-heavy — it will throttle and go read-only. The single biggest gotcha: **its distributed locks/leases do not guarantee mutual exclusion** (Jepsen-confirmed), so always use fencing tokens; the close runner-up is the **compaction → defrag → quota** treadmill that silently turns your cluster read-only if neglected.

## Sources
- [etcd API guarantees (official)](https://etcd.io/docs/v3.5/learning/api_guarantees/)
- [etcd data model (official)](https://etcd.io/docs/v3.5/learning/data_model/)
- [etcd maintenance: compaction, defrag, quota (official)](https://etcd.io/docs/v3.4/op-guide/maintenance/)
- [etcd performance / hardware guidance (official)](https://etcd.io/docs/v3.7/op-guide/performance/)
- [Jepsen: etcd 3.4.3 (Kyle Kingsbury, 2020)](https://jepsen.io/analyses/etcd-3.4.3)
- [etcd blog: Jepsen 3.4.3 results](https://etcd.io/blog/2020/jepsen-343-results/)
- [Kubernetes: operating etcd clusters](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [CNCF: etcd graduation announcement (2020)](https://www.cncf.io/announcements/2020/11/24/cloud-native-computing-foundation-announces-etcd-graduation/)
- [etcd-io/etcd (GitHub, license + source)](https://github.com/etcd-io/etcd)
