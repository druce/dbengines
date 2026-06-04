---
name: DolphinDB
slug: dolphindb
rank: 65
data_model: Time-series (multi-model)
license: Proprietary, closed-source (binary-only core; free Community Edition with node/core limits; paid Enterprise)
summary: High-performance distributed columnar time-series database with a built-in vectorized scripting language, purpose-built for quant finance and IoT tick data.
last_researched: 2026-06-04
confidence: medium
---

# DolphinDB

> A C++ columnar time-series engine fused with its own array/vectorized programming language and streaming runtime — extremely fast for financial tick data and factor research, but a single-vendor, closed-source (binary-only core) ecosystem you script in DolphinDB's dialect, not standard SQL.

## Identity
- **Taxonomy / data model:** Primarily a distributed **time-series** database, but effectively multi-model: it ships several pluggable storage engines — TSDB (LSM-based, row-column hybrid PAX layout), OLAP (pure columnar), PKEY (primary-key dedup/upsert), IMOLTP (in-memory row store with B+tree), and VECTORDB (ANN vector search) ([about](https://docs.dolphindb.com/en/about_dolphindb.html)). See [time-series-storage](../concepts/time-series-storage.md), [columnar-storage](../concepts/columnar-storage.md), [vector-search-ann](../concepts/vector-search-ann.md).
- **Storage model:** Columnar on disk with lossless compression (LZ4, Zstandard, delta-of-delta, Chimp, dictionary) ([about](https://docs.dolphindb.com/en/about_dolphindb.html)). The TSDB and PKEY engines are built on a proprietary **LSM-tree** ([TSDB engine](https://docs.dolphindb.com/en/Tutorials/tsdb_engine.html)); the OLAP engine is plain columnar append-style. See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** OLAP/analytics and stream processing first, with OLTP-ish capabilities via the PKEY/IMOLTP engines. It markets itself as handling OLTP, OLAP, and streaming on one platform; in practice the "OLTP" path is point upserts and in-memory row tables, not high-concurrency transactional app workloads. Treat the unified claim as HTAP-by-separate-engines (you pick the engine per table), not a single physical store. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP** for both data and metadata. Metadata lives on controllers in a [consensus-raft-paxos](../concepts/consensus-raft-paxos.md) Raft group that needs a majority quorum to make progress ([HA deployment](https://docs.dolphindb.com/en/Tutorials/ha_cluster_deployment.html)); data writes use two-phase commit across replica nodes, so a partition that loses quorum stalls rather than diverges. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** roughly **PC/EC** — favors consistency under partition, and the synchronous 2PC write path favors consistency over latency in normal operation. ⚠️ unverified — DolphinDB does not publish a formal PACELC classification; this is inferred from its 2PC + Raft design.
- **Default isolation & what's achievable:** **Snapshot isolation** via MVCC; the docs explicitly claim "ACID ... and supports snapshot isolation" ([about](https://docs.dolphindb.com/en/about_dolphindb.html), [distributed transaction](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)). Note the gap behind the "ACID" label: it is **snapshot isolation, not serializable** — read-write skew anomalies are possible. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Write conflicts:** configurable `atomic` mode. `TRANS` aborts conflicting concurrent writes to preserve atomicity; `CHUNK` retries per-chunk and **explicitly cannot guarantee overall atomicity** (partial writes possible on failure) ([distributed transaction](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)). Choosing CHUNK trades the "A" in ACID for throughput — a real gotcha.
- **Replication:** synchronous multi-replica writes coordinated by 2PC for strong replica consistency ([distributed transaction](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)); streaming subsystem uses Raft-based replication for HA ([streaming HA](https://docs.dolphindb.com/en/Tutorials/streamingHA.html)). Single-leader-style metadata via Raft. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited — `atomic` mode tunes write-conflict atomicity, not per-query read consistency levels (no Dynamo/Cassandra-style quorum knobs).
- **Clock dependency:** ⚠️ unverified — no documented reliance on synchronized clocks (TrueTime/HLC) for correctness; ordering appears commit-ID based. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Tables are typed and columnar; you define column types up front. Partitioning scheme is declared at database creation (VALUE, RANGE, HASH, LIST, COMPO/composite).
- **Migration/evolution:** supports `addColumn`/schema changes; ⚠️ unverified — extent of fully-online, non-locking DDL on large DFS tables is not clearly documented. Repartitioning an existing database is painful and generally means rewriting data.
- **Type system:** rich numeric/temporal types (nanosecond timestamps, multiple date/time types), strings/symbols, arrays/array-vectors, BLOB, plus native vector columns for ANN search via VECTORDB ([about](https://docs.dolphindb.com/en/about_dolphindb.html)). Geospatial support is limited compared to general-purpose engines.

## Query interface
- **Language:** SQL-92-style SQL **extended** with non-standard clauses (`pivot by`, `cgroup by`, `context by`, window joins like `asof join` / `window join`) ([about](https://docs.dolphindb.com/en/about_dolphindb.html)). Crucially, the primary interface is DolphinDB's own **vectorized, array-oriented scripting language** (imperative + functional + APL-like vector ops), not portable SQL. This is the steepest part of the learning curve.
- **Transactions:** distributed multi-partition transactions via 2PC with MVCC snapshot isolation ([distributed transaction](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)). Not designed for many small concurrent OLTP transactions; designed for large batch ingests/updates that must be all-or-nothing.
- **Native vs app-side:** native joins (incl. time-series asof/window joins), aggregations, window functions, and 2,000+ built-in functions ([about](https://docs.dolphindb.com/en/about_dolphindb.html)). Strong native analytics is the whole point.
- **Stored procedures / UDFs:** yes — written in the DolphinDB language; user-defined functions and modules are first-class, and analytics typically run server-side in the engine.

## Scaling & topology
- **Horizontal**, shared-nothing distributed file system: controller nodes hold metadata, data nodes hold chunks/replicas, compute nodes run queries ([HA deployment](https://docs.dolphindb.com/en/Tutorials/ha_cluster_deployment.html)). Compute nodes can be separated from data nodes (a partial [storage-compute-separation](../concepts/storage-compute-separation.md) story).
- **Sharding:** partition-based ([sharding-partitioning](../concepts/sharding-partitioning.md)); partitioning is **manually designed** (you choose the scheme/granularity) — good partition design is essential for performance and changing it later is costly (resharding ≈ rewrite).
- **Read replicas:** replicas serve fault tolerance and read load balancing; because writes are 2PC-synchronous, replica reads are consistent rather than stale.
- **Storage/compute separation:** supports cloud/object-storage tiering in newer/enterprise builds; the classic deployment is local-disk shared-nothing. ⚠️ unverified — exact maturity of S3-backed storage tiers.

## Performance & durability
- **Write path:** in-memory buffer → sorted level files (LSM) for TSDB/PKEY; redo logs provide WAL-style durability ([distributed transaction](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)). Data-loss window depends on redo-log/cache-engine flush settings; ⚠️ unverified — default fsync/flush cadence and the resulting crash data-loss window are not clearly documented and should be tested before production.
- **Throughput/latency:** marketed as sub-millisecond streaming latency and very high ingest/query throughput; independent benchmarks (e.g. quant shops) corroborate it is among the fastest for columnar tick-data scans and factor computation. p99 behavior is generally good for sequential time-range scans.
- **Compaction / GC:** LSM level-file compaction in TSDB/PKEY incurs background write amplification (typical [lsm-vs-btree](../concepts/lsm-vs-btree.md) tradeoff); MVCC retains old versions until commit resolves. ⚠️ unverified — detailed compaction tuning impact on p99 under heavy concurrent update load.

## Operations & maturity
- **Backup/restore:** native backup/restore of DFS tables; cluster replication for DR. PITR is not a first-class advertised feature the way it is in RDBMSs. ⚠️ unverified — granular PITR support.
- **Observability:** built-in metrics, cluster web UI, function-level profiling, and slow-job/job-status introspection; Grafana datasource plugin for dashboards ([about](https://docs.dolphindb.com/en/about_dolphindb.html)).
- **Upgrade story:** clustered rolling upgrades possible with HA controllers/replicas; ⚠️ unverified — degree of zero-downtime guarantees across major versions. Day-2 burden centers on partition design and capacity planning.
- **Maturity:** production-proven in Chinese and global quant/finance shops and IoT; documentation is thorough but historically China-first (some pages stronger in Chinese). **No public [jepsen](../concepts/jepsen.md) report exists** — the snapshot-isolation/ACID claims have not been independently formally verified, which matters given the CHUNK-mode atomicity caveat. ⚠️ unverified — absence of Jepsen means consistency claims rest on vendor docs.

## Ecosystem & people
- **Canonical use cases:** high-frequency/tick market data storage and replay, quantitative factor research and backtesting, real-time stream computing, IoT sensor time-series ([quant examples](https://docs.dolphindb.com/en/Tutorials/quant_finance_examples.html)).
- **Anti-patterns:** general-purpose OLTP / web app backends; teams that need portable ANSI SQL and a broad ORM ecosystem; small/simple workloads where the licensing, learning curve of the DolphinDB language, and operational footprint are not justified; heavy geospatial or document workloads.
- **Drivers/connectors:** official Python, Java, C++, C#, Go, JavaScript APIs with HA auto-reconnect/failover; Grafana plugin; connectors for Kafka, and integrations into the quant Python data stack (pandas-like). Smaller third-party/BI/dbt ecosystem than mainstream databases.
- **Community/support:** vendor-driven (DolphinDB Inc.), commercial support available; community smaller and more finance/China-centric than Postgres/ClickHouse. Docs quality good but uneven in English.

## Licensing & cost
- **Proprietary and closed-source**, not OSS and not truly source-available: the core database **server ships as binaries** governed by a license file, and its source is not published — only the client APIs, plugins, and tooling are open (Apache-2.0) on [GitHub](https://github.com/orgs/dolphindb/repositories). Free **Community Edition** has hard limits (capped at 2 nodes / 2 cores / 8 GB RAM per node) gated by the license file; **Enterprise Edition** removes limits and is paid ([standalone deployment](https://docs.dolphindb.com/en/Tutorials/standalone_deployment.html)). On the [license-taxonomy](../concepts/license-taxonomy.md) axis this is a closed-source commercial product with a free tier, not open-core/source-available — do not treat Community Edition as a production-scale free tier.
- **Self-managed** primarily; also offered via cloud marketplaces (e.g. AWS Marketplace) and managed/cloud builds.
- **Lock-in:** high — the query/analytics layer is written in DolphinDB's proprietary language, so migrating off means rewriting logic, not just re-pointing SQL.
- **Cost model:** ⚠️ unverified — Enterprise pricing is quote-based (per-core/per-node licensing typical); not publicly listed.

## Hardware / deployment
- **Resource profile:** CPU- and memory-hungry for in-memory vectorized compute and streaming; benefits heavily from large RAM, though disk-resident DFS tables do not require the full dataset to fit in RAM. Fast local NVMe strongly recommended for the LSM write/compaction path.
- **Storage assumptions:** designed around fast local disks (NVMe); network-attached/object storage is supported in newer builds but the latency-sensitive path expects local SSD.
- **Footprint:** runs **single-node** (great for dev/research, even embedded-ish single binary) up to large **clusters**; also serverless-ish via managed cloud offerings. See [embedded-databases](../concepts/embedded-databases.md) for the single-node analytic comparison.
- **Deployment:** on-prem, cloud VMs, AWS Marketplace; Docker/Kubernetes deployment supported (StatefulSet for data nodes given local-disk affinity).

## Bottom line
Reach for DolphinDB if you are a quant/finance or IoT team that needs to ingest, store, and compute over huge volumes of time-series/tick data in one fast platform, and you are willing to invest in learning its array-programming language. Do not reach for it as a general-purpose transactional or web-app database, or if you need portable ANSI SQL, a broad open-source ecosystem, or a permissive license. The single biggest gotcha: the headline "ACID + snapshot isolation" is real only in `TRANS` atomic mode — `CHUNK` mode trades away atomicity for throughput, there is no independent [jepsen](../concepts/jepsen.md) verification, and the whole stack is single-vendor closed-source (binary-only core) with heavy language lock-in.

## Sources
- [About DolphinDB (official docs)](https://docs.dolphindb.com/en/about_dolphindb.html)
- [Distributed Transaction (official docs)](https://docs.dolphindb.com/en/3.00.3/Database/DatabaseandDistributedComputing/distributed_transaction.html)
- [TSDB Storage Engine (official docs)](https://docs.dolphindb.com/en/Tutorials/tsdb_engine.html)
- [Primary Key Storage Engine (official docs)](https://docs.dolphindb.com/en/Database/primary_key_storage_eng.html)
- [High-availability Cluster Deployment (official docs)](https://docs.dolphindb.com/en/Tutorials/ha_cluster_deployment.html)
- [High Availability in Streaming (official docs)](https://docs.dolphindb.com/en/Tutorials/streamingHA.html)
- [Quantitative Finance Examples (official docs)](https://docs.dolphindb.com/en/Tutorials/quant_finance_examples.html)
- [Selecting a Database for an Algorithmic Trading System (Proof Trading)](https://medium.com/prooftrading/selecting-a-database-for-an-algorithmic-trading-system-2d25f9648d02)
