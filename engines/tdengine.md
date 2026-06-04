---
name: TDengine
slug: tdengine
rank: 95
data_model: Time-series
license: AGPL-3.0 (OSS core); proprietary TDengine Enterprise / Cloud
summary: Purpose-built IIoT/IoT time-series DB with a one-table-per-device "supertable" model, columnar TSDB storage, and Raft replication.
last_researched: 2026-06-04
confidence: medium
---

# TDengine

> A purpose-built time-series database for industrial IoT that shards one physical table per device under a "supertable" schema, stores data columnar/compressed, and replicates via Raft — fast for high-cardinality sensor ingestion, narrow for anything that isn't time-series.

## Identity
- **Taxonomy / data model:** Time-series database (TSDB). See [time-series-storage](../concepts/time-series-storage.md) and the [oltp-olap-htap](../concepts/oltp-olap-htap.md) workload axis. The defining abstraction is the **supertable (STable)**: a schema template carrying a data schema plus **tags**, from which one **subtable per data-collection point** (device/sensor) is auto-created ([supertable](https://tdengine.com/supertable/)). This "one table per device" partitioning is the core design choice — it reduces write contention and lets per-device queries avoid full scans, but pushes cardinality into the number of tables.
- **Storage model:** Columnar on disk; time-series data is stored "in a highly compressed, columnar format" partitioned by device and time interval ([TSDB docs](https://docs.tdengine.com/inside-tdengine/architecture/)). Not a classic [lsm-vs-btree](../concepts/lsm-vs-btree.md) engine — it uses an append-oriented TSDB file format fed from an in-memory buffer and a [WAL](../concepts/wal-and-durability.md), with time-range data files (the layout is closer to time-partitioned columnar blocks than a B-tree). See [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** OLTP-style high-throughput ingest + time-range analytical queries (downsampling, interval aggregation, last-value). Effectively time-series OLTP+lightweight-OLAP, not general HTAP — there is no separate columnar replica or row/column split to flag; everything is the one columnar time-series store.

## Distribution & consistency
- **Cluster roles:** **dnode** (physical node), **vnode** (virtual node = data shard, the unit of replication), **mnode** (management/metadata node), **qnode** (query compute) ([architecture](https://docs.tdengine.com/inside-tdengine/architecture/)). Metadata (mnodes) and data (vnodes) both replicate via Raft. See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **CAP under partition:** **CP** in the Raft-based 3-replica and dual-replica modes — they keep a quorum/leader and refuse progress without one, prioritizing consistency over availability. The **active-active** mode is **AP** (stays up on either side, reconciles via WAL sync). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Raft modes ≈ **PC/EC** (consistency under partition; consistent reads from leader else-case). Active-active ≈ **PA/EL** — available under partition, eventual convergence. ⚠️ unverified — TDengine does not publish a formal PACELC classification; this is inferred from its [replication](../concepts/replication-models.md) modes.
- **Replication modes** ([HA docs](https://docs.tdengine.com/operation/ha/), [dual-replica/active-active overview](https://tdengine.medium.com/balancing-reliability-cost-mastering-tdengines-dual-replica-and-active-active-solutions-2bf56e3dd141)):
  - **Triple replica (replica 3):** standard Raft, strong consistency, tolerates one node loss.
  - **Dual replica + arbitrator:** two data copies plus a lightweight arbitrator node; here leader/failover decisions are made by the **mnode** (assigning an "Assigned Leader") rather than by pure Raft voting, using the arbitrator to avoid split-brain ([three-replica vs dual-replica HA docs](https://docs.tdengine.com/operation/ha/)); strong consistency, lower storage cost, but "cannot tolerate consecutive failures."
  - **Active-active:** two independent clusters synced via taosX/WAL; **eventual consistency only**, available as long as one instance is alive.
- **Default isolation / "ACID":** TDengine markets reliability but is **not a general-purpose transactional DB**. There are no multi-statement transactions; the safe mental model is **single-row / single-write atomicity**, and even that breaks down for batch schemaless writes — "schemaless ingestion does not provide atomicity for writing multiple rows" (some rows can succeed while others fail) ([schemaless docs](https://docs.tdengine.com/developer-guide/schemaless-ingestion/)). ⚠️ unverified — TDengine does not document a named SQL [isolation level](../concepts/isolation-levels.md); treat reads as last-write-wins per (table, timestamp) with no snapshot/serializable guarantees.
- **Tunable consistency:** coarse — chosen at the replication-mode level (Raft strong vs active-active eventual), not per query.
- **Clock dependency:** rows are keyed by a client-or-server timestamp; correctness of ordering/de-dup depends on sane timestamps, but it does **not** rely on TrueTime/HLC-style synchronized clocks for transactional correctness. See [clocks-and-time](../concepts/clocks-and-time.md).
- **Jepsen:** ⚠️ unverified — no published Jepsen analysis of TDengine was found.

## Schema
- **Schema-on-write** for the SQL path: a supertable defines fixed columns + tags; subtables inherit it. Also supports **schemaless ingestion** (InfluxDB line protocol, OpenTSDB telnet/JSON), which auto-creates supertables/columns/tags on the fly ([schemaless docs](https://docs.tdengine.com/developer-guide/schemaless-ingestion/)).
- **Migration/evolution:** `ALTER STABLE`/`ALTER TABLE` to add/drop/modify columns and tags; tag changes propagate to subtables. ⚠️ unverified — exact online-DDL locking characteristics under load are not documented in sources reviewed.
- **Type system:** timestamp (the mandatory first column, microsecond/nanosecond precision configurable), integer/unsigned/float/double, bool, `binary`/`varchar`/`nchar` strings, `varbinary`, `json` (tag-oriented), `geometry`, and `decimal` (precision+scale) added in 3.3.6 ([data types](https://docs.tdengine.com/tdengine-reference/sql-manual/data-types/)). No native vector/embedding type for ANN search; not a full-text engine.

## Query interface
- **Language:** SQL dialect ("TAOS SQL") with time-series extensions — `INTERVAL` windowing, `FILL`, `PARTITION BY`, `LAST`/`LAST_ROW`, `TWA`/time-weighted aggregates, `STATE_WINDOW`/`SESSION` windows. REST and connector access via taosAdapter (InfluxDB/OpenTSDB-compatible write endpoints).
- **Transactions:** **none** in the relational sense — no `BEGIN/COMMIT` multi-statement ACID. Single inserts are atomic per row; batch writes are not all-or-nothing.
- **Native vs app-side:** aggregations, downsampling, interval/window functions are native and the main strength. Cross-table joins are limited and time-series oriented; this is not a JOIN-heavy analytics engine. Tags act as the indexed dimension for filtering/grouping across subtables.
- **Stored procedures / UDFs:** user-defined functions supported (C, and Python). A built-in **stream processing** engine supports continuous/rollup queries; WAL doubles as a **data subscription / message-queue** consumer interface.

## Scaling & topology
- **Horizontal:** scale out by adding dnodes; data is sharded across **vnodes** (each vnode owns a set of subtables/time ranges) and replicated by Raft. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding/partitioning:** automatic — partition by table (device) and by time interval into time-range data files; resharding is handled by vnode rebalancing across dnodes. ⚠️ unverified — operational pain of large rebalances under sources reviewed.
- **Read replicas:** followers in a Raft group; consistent reads come from the leader. Reads served from followers are subject to replication lag (and in active-active, eventual consistency).
- **Storage/compute separation:** **qnodes** separate query compute from storage vnodes within a cluster (compute offload), but this is not Snowflake/Aurora-style elastic object-store separation. TDengine **Cloud** offers a managed tiered-storage variant. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** incoming points are appended to an in-memory buffer and the **WAL** (append mode) before being flushed to columnar TSDB files; leader and follower vnodes write memory+WAL identically ([architecture](https://docs.tdengine.com/inside-tdengine/architecture/)). See [wal-and-durability](../concepts/wal-and-durability.md). fsync is configurable (periodic flush interval), so a tail of recently-acked writes can be lost on crash if WAL fsync is asynchronous; Raft 3-replica reduces single-node data-loss exposure. ⚠️ unverified — exact default fsync cadence varies by version/config.
- **Notable:** WAL is **retained as a persistent queue**, not deleted immediately, so downstream consumers (data subscription, stream processing) read from it ([architecture overview](https://www.simplyblock.io/glossary/what-is-tdengine/)).
- **Throughput/latency:** designed for very high ingest rates on time-series workloads with strong columnar compression; vendor benchmarks claim large advantages over InfluxDB/others — treat those as ⚠️ vendor benchmarks, not independent. p99 behavior depends on flush/compaction cycles; no independent tail-latency data found.
- **Compaction/GC:** time-partitioned files plus configurable **retention (`KEEP`)** and **multi-tier storage** (hot/warm/cold) move/expire old data; compaction merges data files. p99 impact during flush/compaction not quantified in sources reviewed.

## Operations & maturity
- **Backup/restore:** snapshot/backup tooling exists; PITR-style recovery leans on WAL retention. ⚠️ unverified — granular PITR guarantees from sources reviewed.
- **Observability:** **taosKeeper** exports metrics, **TDinsight** Grafana dashboards visualize cluster/node/read-write/resource status; SQL `EXPLAIN` for query plans; slow-query and monitoring logs ([components](https://docs.tdengine.com/tdengine-reference/components/), [monitoring](https://docs.tdengine.com/operations-and-maintenance/monitor-your-cluster/)).
- **Upgrade story:** rolling cluster upgrades supported in clustered mode; **3.0 was a major rewrite** from 2.x (cluster/storage changes) and migration between major versions is non-trivial. ⚠️ unverified — downtime specifics per upgrade path.
- **Maturity:** open-sourced 2019 (taosdata), widely deployed in Chinese industrial-IoT/power/manufacturing contexts; sizeable GitHub presence. Known constraints: narrow data model, no general transactions, schemaless batch non-atomicity, and a 3.0 architecture still maturing relative to incumbents. No Jepsen.

## Ecosystem & people
- **Canonical use cases:** IIoT/IoT telemetry, smart manufacturing, power/energy, vehicle/fleet telemetry, infrastructure & DevOps metrics, data-historian replacement (AVEVA PI/Historian, OPC-UA/DA ingestion via taosX).
- **Anti-patterns:** general-purpose OLTP, relational apps needing multi-row transactions/joins, document/graph workloads, full-text or vector/ANN search, and low-cardinality non-time-keyed data. If your data has no timestamp dimension, it is the wrong tool.
- **Connectors/drivers:** Java (JDBC), Go, Rust, Python, C/C++, C#, Node.js; REST. **taosAdapter** gives InfluxDB/OpenTSDB line-protocol compatibility and Telegraf/StatsD/collectd ingestion. **taosX** (Enterprise) is the no-code pipeline (Kafka, MQTT, MySQL/PostgreSQL/Oracle, CSV, PI/Historian). Grafana integration is first-class.
- **Community/support:** active OSS project plus commercial vendor (TDengine Inc., formerly TAOS Data); docs are reasonable but partly translated. Learning curve is low for the SQL+time-series subset, higher for cluster ops.

## Licensing & cost
- **OSS license:** core **TDengine OSS is AGPL-3.0** — copyleft with the network/SaaS clause; self-hosting and modifying is fine, but offering it as a service can trigger source-availability obligations ([open source](https://tdengine.com/open-source/)). See [license-taxonomy](../concepts/license-taxonomy.md). Clustering is included in OSS. ⚠️ note — earlier 2.x had an MIT core for some pieces; 3.0 OSS is AGPL.
- **Proprietary tiers:** **TDengine Enterprise** (adds taosX pipelines, multi-level storage, dual-replica/active-active tooling, security) and **TDengine Cloud** (managed) are commercial. Some HA/replication and connector features are Enterprise-only — a real OSS-vs-paid feature split to weigh.
- **Cost model:** self-managed OSS is free (compute/storage only); Enterprise per-node/subscription; Cloud consumption-based. Lock-in risk is moderate via the supertable/tag model and Enterprise-only pipelines.

## Hardware / deployment
- **Resource profile:** ingest path is disk/IO- and CPU-bound (compression); a hot in-memory buffer + cache helps recent-data reads, but the **full dataset need not fit in RAM** — multi-tier storage targets cold data on cheaper media.
- **Storage assumptions:** benefits from NVMe/local SSD for the hot tier and high write throughput; tolerates cheaper/network storage for cold tiers.
- **Footprint:** single-node, clustered, **edge-to-cloud** (lightweight edge instances syncing to a central cluster), and managed Cloud. Not an embedded library.
- **Deployment:** on-prem or SaaS (TDengine Cloud); Docker/Kubernetes supported (StatefulSet for vnode data). ⚠️ unverified — k8s operator maturity from sources reviewed.

## Bottom line
Reach for TDengine when you have high-volume, high-device-count time-series/IIoT telemetry, want SQL with built-in windowing/downsampling, and value the one-table-per-device model plus InfluxDB/OpenTSDB-compatible ingestion. Do **not** use it as a general database: no multi-statement transactions, no real joins, no full-text/vector search, and batch schemaless writes are not atomic. The single biggest gotcha is the **OSS-vs-Enterprise split on HA and pipelines** combined with **AGPL-3.0** — verify that the replication mode and connectors you need aren't behind the commercial tier, and that AGPL fits your distribution model, before committing.

## Sources
- [TDengine architecture (internals docs)](https://docs.tdengine.com/inside-tdengine/architecture/)
- [High Availability docs](https://docs.tdengine.com/operation/ha/)
- [Supertable concept](https://tdengine.com/supertable/)
- [Schemaless ingestion docs](https://docs.tdengine.com/developer-guide/schemaless-ingestion/)
- [SQL data types](https://docs.tdengine.com/tdengine-reference/sql-manual/data-types/)
- [Components reference (taosAdapter/taosKeeper/taosX/TDinsight)](https://docs.tdengine.com/tdengine-reference/components/)
- [Open Source / licensing](https://tdengine.com/open-source/)
- [Dual-replica & active-active overview (vendor blog)](https://tdengine.medium.com/balancing-reliability-cost-mastering-tdengines-dual-replica-and-active-active-solutions-2bf56e3dd141)
- [db-engines TDengine entry](https://db-engines.com/en/system/TDengine)
