---
name: VictoriaMetrics
slug: victoriametrics
rank: 141
data_model: Time-series
license: Apache 2.0 (permissive); cluster + enterprise features are source-available/commercial
summary: Cost-efficient, high-cardinality-tolerant time-series DB; a drop-in Prometheus/Graphite backend with PromQL+ (MetricsQL).
last_researched: 2026-06-04
confidence: high
---

# VictoriaMetrics

> A fast, resource-cheap time-series database aimed at being a long-term, horizontally scalable backend for Prometheus-style metrics — it trades transactions and strong consistency for ingest throughput, cheap storage, and a ~1-second crash data-loss window.

## Identity
- **Taxonomy / data model:** Time-series. Numeric float samples keyed by a metric name + arbitrary label set (the Prometheus/OpenMetrics data model). Append-mostly; not a general-purpose store. There is a sibling product, VictoriaLogs, for logs — out of scope here.
- **Storage model:** Custom [LSM](../concepts/lsm-vs-btree.md)-style engine inspired by ClickHouse's MergeTree, with columnar, per-column compression (Gorilla-style delta encoding for timestamps, ZSTD-like for values) ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)). Data is buffered in RAM, periodically flushed into immutable "parts," then background-merged — low write amplification, no per-sample update-in-place. See [columnar-storage](../concepts/columnar-storage.md), [time-series-storage](../concepts/time-series-storage.md).
- **Workload:** OLAP-ish analytical reads over time-series + very high-rate ingest. Not OLTP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Optimized for monitoring/observability query patterns (range queries, rollups), not point lookups or row updates.

## Distribution & consistency
- **Single-node:** no distribution concerns — N/A. Single-node is the recommended default and scales vertically; the vendor states it handles "up to 100 million active time series and 2 million samples per second" based on real usage ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)).
- **CAP under partition:** Cluster version is **AP** — it explicitly "prioritizes availability over data consistency," remaining available for ingest and query when components are temporarily down ([cluster docs](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)). See [cap-pacelc](../concepts/cap-pacelc.md). Queries may return *partial results* by default; set `-search.denyPartialResponse` on `vmselect` to fail instead of returning incomplete data ([cluster docs](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)).
- **PACELC:** Under partition, favors Availability (PA); else, favors Latency/throughput (EL). There is no quorum/consensus protocol gating writes.
- **Isolation / "ACID":** None in the transactional sense. No multi-sample transactions, no isolation levels — writes are independent appends. See [isolation-levels](../concepts/isolation-levels.md). Treat any "reliable" claim as durability-of-appends, not ACID.
- **Replication:** Cluster `vminsert` writes N copies of each sample to N distinct `vmstorage` nodes (`-replicationFactor=N`); `vmselect` de-duplicates at query time ([cluster docs](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)). The factor is **best-effort, not strict**: `vminsert` writes synchronously to N nodes when they are up, but if a `vmstorage` node is down it proceeds with fewer copies (logging "cannot make a copy"), and lost replicas are **not auto-rebuilt** (by design, to avoid runaway re-replication) ([issue #2613](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/2613)). The vendor recommends relying on replicated durable disks (e.g., cloud persistent disks) for durability rather than VM-level replication ([cluster docs](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)). See [replication-models](../concepts/replication-models.md). No leader election; no split-brain because there is no consensus to split.
- **Tunable consistency:** Coarse only — `-replicationFactor` plus the partial-response toggle. No per-query consistency levels.
- **Clock dependency:** Samples carry caller-supplied timestamps; correctness does not rely on synchronized cluster clocks for consensus (there is none). Out-of-order/duplicate samples are handled by optional dedup. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read / schemaless:** No predefined schema. New metric names and labels are accepted on ingest automatically. The "schema" effectively lives in whatever the exporters emit. High label cardinality is the main operational hazard (memory pressure, slow queries).
- **Migration / DDL:** No DDL, no `ALTER`. Adding/removing labels is just a change in what gets written; there is no online-migration or table-lock concept.
- **Type system:** Float64 sample values + string labels + int64 timestamps. No JSON/arrays/geospatial/vector types — it is deliberately narrow.

## Query interface
- **Language:** **MetricsQL**, a backward-compatible superset of PromQL that fixes several PromQL rough edges ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)). Also exposes the Graphite query API and ingest for InfluxDB line protocol, OpenTSDB, Graphite, CSV/JSON, Prometheus `remote_write` and native formats.
- **Transactions:** None. Writes are atomic per sample only; no multi-statement transactions.
- **Native vs app-side:** Rich server-side aggregation/rollups/rate functions via MetricsQL; no SQL joins. "Joining" across series is done with PromQL-style label matching, not relational joins.
- **Stored procedures / UDFs:** None. Recording/alerting rules run in the companion `vmalert` component, not in-engine.

## Scaling & topology
- **Vertical (single-node)** is the recommended path for most deployments; one binary handles ingest, storage, query.
- **Horizontal (cluster):** four stateless-ish roles — `vminsert` (write fan-out + sharding), `vmselect` (query scatter-gather + dedup), `vmstorage` (the only stateful tier), plus `vmagent`/`vmalert` helpers. Series are sharded across `vmstorage` nodes consistently by labels.
- **Resharding:** Adding `vmstorage` nodes raises ingest/query capacity for *new* data; existing data is not auto-rebalanced and stays on its original nodes — a notable operational caveat for capacity planning ([cluster docs](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** Reads may be partial during node loss (see Distribution). With `-replicationFactor=N`, a full query response survives up to N-1 lost `vmstorage` nodes.
- **Storage/compute separation:** Not in the Snowflake sense — `vmstorage` owns local disk. `vminsert`/`vmselect` are stateless compute that can scale independently, which is a partial separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** **No WAL — by design.** The author argues a separate WAL is wasteful for high-ingest TSDBs ([Valyala, "WAL usage looks broken in modern TSDBs"](https://valyala.medium.com/wal-usage-looks-broken-in-modern-time-series-databases-b62a627ab704)). Instead, incoming samples buffer in RAM and flush to disk on a ~1-second interval (`-inmemoryDataFlushInterval`, default 1s) ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Data-loss window on crash:** **~1 second** of un-flushed in-memory samples on power loss / SIGKILL / OOM. Parts are written and fsynced atomically, so a crash mid-write leaves no corrupt parts — partially written parts are deleted on restart ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)). Net: durable up to roughly the last second; unsuited where every datapoint must be guaranteed.
- **Throughput/latency:** Designed for very high ingest (single-node millions of samples/s; cluster hundreds of millions/s per vendor) with low memory per active series; strong compression ratios. p99 query latency is generally good but degrades with high cardinality and during heavy background merges.
- **Compaction / GC:** Background merging of parts (LSM-style). Merges consume disk I/O and CPU and can raise p99 transiently; there is no vacuum-style bloat. Retention is enforced by dropping old parts; optional **deduplication** and **downsampling** reduce storage.

## Operations & maturity
- **Backup/restore:** `vmbackup`/`vmrestore` (incremental, to S3/GCS/local). PITR is approximate — snapshot-based, not log-replay; you restore to a snapshot, not an arbitrary instant.
- **Observability:** Exposes its own Prometheus-format metrics, a cardinality explorer for finding high-cardinality offenders, query tracing/EXPLAIN-style tracing, and slow-query logging.
- **Upgrade story:** Single-node upgrades want a graceful shutdown; cluster supports rolling/zero-downtime updates of roles ([docs FAQ](https://docs.victoriametrics.com/victoriametrics/faq/)). Day-2 burden is low relative to Thanos/Cortex — fewer moving parts, no external object-store dependency required.
- **Maturity:** Widely deployed as a Prometheus long-term store and Cortex/Thanos alternative; large active OSS user base. **No published Jepsen report** — consistency claims here come from vendor docs and issue trackers, not formal verification. ⚠️ unverified — the AP/partial-response behavior has not been independently formally tested.
- **Known failure modes:** silent partial query results if `-search.denyPartialResponse` is left off; complete sample loss (not just one replica) when `dropSamplesOnOverload=true` because drops happen *before* replication ([issue #4798](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/4798)); cardinality blow-ups causing OOM.

## Ecosystem & people
- **Canonical use cases:** Long-term, cost-efficient storage for Prometheus/Grafana monitoring; a single-binary replacement for Thanos/Cortex/Mimir; Graphite/InfluxDB/OpenTSDB backend consolidation; very high active-series counts.
- **Anti-patterns:** Anything needing transactions, exact per-record durability, relational/document data, or strong read-after-write consistency across a partitioned cluster. Not a metrics-plus-events-plus-traces single store (use VictoriaLogs/other tools for logs/traces).
- **Connectors:** First-class Grafana datasource; ingests Prometheus `remote_write`, InfluxDB line protocol, Graphite, OpenTSDB, CSV/JSON, DataDog; `vmagent` for scraping/relay, `vmalert` for rules. No dbt/CDC relevance (it is metrics, not OLAP tables).
- **Community/support:** Healthy OSS community, responsive maintainers, good docs; commercial support and VictoriaMetrics Cloud (managed) available. Learning curve is low for anyone who knows Prometheus/PromQL.

## Licensing & cost
- **License:** Core single-node and cluster are **Apache 2.0** (permissive — see [license-taxonomy](../concepts/license-taxonomy.md)). However, **Enterprise features** (downsampling at scale, multi-tenant niceties, some backup/automation, retention filters) are **source-available/commercial**, not Apache. Verify which features you need are in the OSS build before committing. No known post-2018 relicensing of the core to SSPL/BSL.
- **Self-managed vs managed:** Both — run it yourself (binaries/Docker/k8s/Helm/operator) or VictoriaMetrics Cloud.
- **Lock-in:** Low at the data-protocol level (speaks Prometheus/Graphite/Influx); moderate if you depend on Enterprise-only features.
- **Cost model:** OSS = your hardware (its big selling point is low RAM/disk/CPU per series vs alternatives). Enterprise/Cloud are commercially priced. Cost scales mainly with active series count and retention.

## Hardware / deployment
- **Resource profile:** Memory scales with *active* time series (cardinality), not total samples; disk scales with retained samples (heavily compressed). CPU-light at ingest, busier during merges/heavy queries. Working set need not fit in RAM, but per-series index does pressure memory.
- **Storage assumptions:** Local SSD/NVMe strongly preferred for `vmstorage`; the design tolerates ordinary disks better than WAL-heavy TSDBs because of large sequential writes and low write amplification.
- **Footprint:** Single static Go binary (single-node) or a small set of binaries (cluster). No external dependencies (no ZooKeeper/etcd/object store required for core operation).
- **Deployment:** On-prem or any cloud; first-class k8s support via Helm charts and the VictoriaMetrics Operator; `vmstorage` runs as a StatefulSet with persistent volumes. SaaS via VictoriaMetrics Cloud.

## Bottom line
Reach for VictoriaMetrics when you need a cheap, operationally simple, horizontally scalable long-term store for Prometheus-style metrics and you can tolerate an AP, ~1-second-data-loss-window model. Do **not** use it as a general database, where you need transactions or exact-once durability, or where a partitioned cluster must return strongly consistent reads. The single biggest gotcha: by default a degraded cluster returns *partial* query results silently — enable `-search.denyPartialResponse` (and understand that `-replicationFactor` is best-effort, not a strict durability guarantee).

## Sources
- [VictoriaMetrics FAQ (official docs)](https://docs.victoriametrics.com/victoriametrics/faq/)
- [Cluster version (official docs)](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)
- [Valyala — "WAL usage looks broken in modern time series databases"](https://valyala.medium.com/wal-usage-looks-broken-in-modern-time-series-databases-b62a627ab704)
- [GitHub issue #2613 — "Replication factor is not strict"](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/2613)
- [GitHub issue #4798 — dropSamplesOnOverload vs replicationFactor](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/4798)
- [GitHub repository / README](https://github.com/VictoriaMetrics/VictoriaMetrics)
