---
name: Prometheus
slug: prometheus
rank: 46
data_model: Time-series
license: Apache 2.0 (permissive)
summary: Pull-based metrics monitoring TSDB for operational telemetry; single-node and intentionally not durable/clustered on its own.
last_researched: 2026-06-04
confidence: high
---

# Prometheus

> The de facto open-source standard for infrastructure/application metrics monitoring: a single-node pull-scraping time-series DB with PromQL and alerting, deliberately not a durable distributed store — long-term/HA needs Thanos/Mimir/Cortex on top.

## Identity
- **Taxonomy / data model:** [time-series-storage](../concepts/time-series-storage.md) database purpose-built for operational monitoring metrics, not a general DBMS. Data model is label-set + sample: a metric is identified by a name plus a set of key/value labels, and each series is a stream of `(int64 timestamp, value)` points. Values were historically `float64` only; [native histograms](https://prometheus.io/docs/specs/native_histograms/) add a sparse-bucket composite sample type.
- **Storage model:** custom append-optimized columnar-ish chunk store ("the TSDB"). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) in the classic sense: recent samples live in an in-memory **head block** (mutable, ~2h), backed by a [wal-and-durability](../concepts/wal-and-durability.md) WAL; older data is flushed to immutable on-disk **2-hour blocks** (chunks + inverted index mapping labels→series), then [merged by compaction](https://prometheus.io/docs/prometheus/latest/storage/) into larger blocks. See [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** OLTP-of-metrics ingest (high-rate appends) + interactive/alerting reads over recent data. Not OLAP, not HTAP — analytical/ad-hoc cross-cutting queries over long history are an anti-pattern on vanilla Prometheus. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** N/A as a cluster — vanilla Prometheus is **single-node**; there is no built-in replication or consensus. The docs state plainly: "local storage… is not clustered or replicated. Thus, it is not arbitrarily scalable or durable in the face of drive or node outages." ([storage docs](https://prometheus.io/docs/prometheus/latest/storage/)) See [cap-pacelc](../concepts/cap-pacelc.md).
- **HA pattern (not built-in):** run two identical Prometheus servers scraping the same targets; deduplicate at query time (e.g. via Thanos/Mimir). This is "redundant independent collectors," not a consistent cluster — the two servers can disagree on which samples they captured.
- **PACELC:** N/A — single-node.
- **Isolation / transactions:** none in any SQL sense. Appends are per-sample; there is no multi-statement transaction and no [isolation-levels](../concepts/isolation-levels.md) guarantee. Prometheus does provide a [query-time isolation/staleness](https://promcon.io/2017-munich/slides/staleness-in-prometheus-2-0.pdf) mechanism (a scrape's samples become visible atomically, and `NaN` stale markers handle disappeared series) — but do not read this as ACID.
- **Replication:** none natively. Durable replication is delegated to remote-write sinks (Thanos receive, grafana-mimir, cortex, VictoriaMetrics, etc.). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** N/A.
- **Clock dependency:** samples are timestamped at scrape time by the Prometheus server (server clock); rate/increase math assumes reasonably sane clocks but there is no TrueTime/HLC requirement. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** schema-on-write but effectively schemaless — series are created implicitly the first time a metric name + label set is seen. No `CREATE TABLE`. High-cardinality label sets (e.g. user IDs, unbounded labels) are the dominant operational footgun: each unique label combination is a new series and memory/index cost grows accordingly.
- **Migration / DDL:** none — there is no DDL. "Evolving the schema" means relabeling at scrape/ingest time (`relabel_configs`).
- **Type system:** values are `float64`; counters, gauges, summaries, and (client-side) classic histograms are conventions, not enforced types. [Native histograms](https://prometheus.io/docs/specs/native_histograms/) add a real composite type. Exemplars (trace links) can attach to samples. No JSON/geospatial/vector types — wrong tool for those.

## Query interface
- **Language:** [PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/), a functional DSL for selecting and aggregating time series over time ranges — not SQL, no joins in the relational sense (it has label-matching vector binops instead). Access is via HTTP API; Grafana is the usual visualization layer.
- **Transactions:** none.
- **Native vs app-side:** aggregations, rate/increase, quantile estimation, and range/instant vectors are native. There is an inverted index on labels (so "secondary indexes" on labels are inherent), but no relational joins, no foreign keys.
- **Stored procedures / UDFs:** none. Precomputation is done via **recording rules**; **alerting rules** evaluate PromQL expressions and fire to Alertmanager.

## Scaling & topology
- **Vertical vs horizontal:** primarily **vertical** — a single server scales with RAM/CPU/disk. Horizontal scaling is achieved by **functional/hash sharding across multiple independent Prometheus servers** (manual: split targets), then querying via thanos or grafana-mimir for a global view. There is no auto-resharding; rebalancing means re-partitioning your scrape config. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Federation:** hierarchical `/federate` lets one Prometheus scrape aggregated series from others — useful for rollups, not for full long-term storage.
- **Remote write:** the standard path to scale-out — Prometheus (or [agent mode](https://prometheus.io/docs/prometheus/latest/prometheus_agent/), which disables local querying/storage and only scrapes+forwards) ships samples to a horizontally scalable backend.
- **Read replicas / read consistency:** N/A — no replicas. Querying a remote backend gives that backend's consistency, not Prometheus's.
- **Storage/compute separation:** none in vanilla Prometheus (local disk). The ecosystem add-ons (Thanos, Mimir, Cortex) provide object-storage-backed separation. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** scrape → append to in-memory head + append to [wal-and-durability](../concepts/wal-and-durability.md) WAL (128 MB segments; compression optional, roughly halves WAL size). Head is flushed to immutable 2h blocks on disk. WAL fsync is not per-sample synchronous-on-commit the way an OLTP DB does — durability is "good enough for metrics," not transactional.
- **Data-loss window on crash:** WAL replay recovers in-memory data on restart, but **backups taken without a snapshot can lose everything since the last block was cut — typically up to ~2 hours** ([storage docs](https://prometheus.io/docs/prometheus/latest/storage/)); use the admin snapshot API for consistent backups. A lost/corrupt local disk loses local data outright (no replication).
- **Throughput/latency:** designed for very high sample-append rates on a single node and fast recent-range queries; p99 is dominated by query fan-out over many series and by head GC. Wide/high-cardinality queries and long lookbacks blow up memory and tail latency.
- **Compaction / GC:** background [compaction](https://prometheus.io/docs/prometheus/latest/storage/) merges 2h blocks into larger ones (up to ~10% of retention or 31 days). Compaction and head churn are the main p99/memory pressure sources; retention is by time (default 15d) or size, with expired blocks deleted in the background.

## Operations & maturity
- **Backup/restore, PITR:** snapshot via the admin API (`/api/v1/admin/tsdb/snapshot`), then copy the data dir; restore by placing blocks back. No true PITR — granularity is the block.
- **Observability:** Prometheus is the observability tool — it self-exposes `/metrics`, exposes the TSDB status/cardinality endpoints, and PromQL doubles as introspection. Query plans are minimal (no EXPLAIN like an RDBMS); slow queries are diagnosed via query log and metrics.
- **Upgrade story:** single static Go binary, no external deps — upgrades are stop/swap/start; format is backward-compatible across 2.x/3.x within documented bounds. Day-2 burden is mostly capacity/cardinality management and bolting on long-term storage + HA.
- **Maturity:** extremely mature and ubiquitous — CNCF **graduated** (2018, second after Kubernetes), the de facto Kubernetes monitoring standard. No Jepsen report exists, and one would be largely moot: ⚠️ unverified — no formal-verification/Jepsen analysis is published, but it is unnecessary because vanilla Prometheus makes no distributed-consistency claims to test. Known failure modes: cardinality explosions, OOM on large queries, single-node durability loss.

## Ecosystem & people
- **Canonical use cases:** infrastructure and application metrics, alerting (with Alertmanager), Kubernetes/cloud-native monitoring, SLO dashboards via Grafana.
- **Anti-patterns:** event logging, high-cardinality/per-request data, billing/audit data needing exactness and durability, long-term analytical history on a single node, anything needing transactions or strong durability. It is sampled monitoring data, explicitly "not… 100% accurate" for billing-grade use ([FAQ](https://prometheus.io/docs/introduction/faq/)).
- **Ecosystem:** huge — hundreds of exporters, native client libraries, OpenMetrics/OTLP ingestion, Pushgateway for batch jobs, Grafana for viz, and the remote-write ecosystem (thanos, grafana-mimir, cortex, [victoriametrics](victoriametrics.md)) for HA + long-term storage. The Prometheus exposition/remote-write formats are widely adopted standards.
- **Community / docs / learning curve:** very large community, good docs, abundant tutorials. PromQL has a real learning curve; the hard part operationally is cardinality discipline.

## Licensing & cost
- **License:** [Apache 2.0](https://www.cncf.io/projects/prometheus/) — permissive, no post-2018 relicensing drama. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** fully self-hostable; managed offerings exist (Grafana Cloud, Amazon Managed Service for Prometheus, etc.) typically built on Mimir/Cortex/Thanos.
- **Lock-in:** low — open formats; the main "lock-in" is choosing a remote-write backend.
- **Cost model:** software is free; cost is your infra. At scale, costs are driven by series cardinality and retention, and managed offerings usually bill per-sample-ingested and/or per-query — which can invert sharply with high cardinality.

## Hardware / deployment
- **Resource profile:** **memory-bound** — RAM scales with active series cardinality and head size; also disk-IO and CPU sensitive during compaction/queries. Working set (head) must fit in RAM.
- **Storage assumptions:** local disk; SSD/NVMe strongly preferred for compaction and query IO. Network-attached storage is discouraged for the local TSDB.
- **Footprint:** single static binary, single node (or agent-mode forwarder). Not embedded, not natively clustered.
- **Deployment:** very container/Kubernetes-friendly (the canonical Prometheus Operator + StatefulSet pattern); on-prem or cloud. StatefulSet realities: it's stateful local disk, so node loss = data loss unless paired with remote storage.

## Bottom line
Reach for Prometheus when you need battle-tested, open-source operational **metrics monitoring and alerting** for cloud-native/Kubernetes systems — it's the default and the ecosystem is enormous. Do **not** treat it as a durable, scalable, or accurate system of record: it's single-node, can lose up to ~2h of data on disk loss, and has no replication or transactions out of the box. The single biggest gotcha is **label cardinality** — unbounded labels silently explode memory and can OOM the server; the second is realizing that any "production HA + long-term + global query" story requires bolting on thanos, grafana-mimir, or cortex.

## Sources
- [Prometheus — Storage (local TSDB, WAL, compaction, durability)](https://prometheus.io/docs/prometheus/latest/storage/)
- [Prometheus — Querying basics (PromQL data model)](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus — Native histograms spec](https://prometheus.io/docs/specs/native_histograms/)
- [Prometheus — Agent mode](https://prometheus.io/docs/prometheus/latest/prometheus_agent/)
- [Prometheus — FAQ (not 100% accurate; not for billing)](https://prometheus.io/docs/introduction/faq/)
- [Staleness and isolation in Prometheus 2.0 (Brian Brazil, PromCon)](https://promcon.io/2017-munich/slides/staleness-in-prometheus-2-0.pdf)
- [CNCF — Prometheus project (Apache 2.0, graduated 2018)](https://www.cncf.io/projects/prometheus/)
