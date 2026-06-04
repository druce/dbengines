---
name: Graphite
slug: graphite
rank: 67
data_model: Time-series (monitoring)
license: Apache 2.0 (permissive)
summary: File-based RRD-style metrics store with fixed-size archives and on-write downsampling; simple and battle-tested, but it pre-allocates disk per metric and has no real distributed story.
last_researched: 2026-06-04
confidence: high
---

# Graphite

> A 2008-era operational-metrics stack (Carbon + Whisper + graphite-web) that stores each metric as a fixed-size, RRD-like file with built-in retention/rollups — cheap and proven for dashboards, but it pre-allocates disk per series, fakes clustering with hash-ring relays, and has no transactions or strong consistency.

## Identity
- **Taxonomy / data model:** [time-series-storage](../concepts/time-series-storage.md) database for operational/monitoring metrics. Data model is dead simple: `(metric.path.dotted, value, unix_timestamp)`. Hierarchical dot-delimited metric names (`servers.web01.cpu.load`), no tags in the original design (tagging was bolted on later in Graphite 1.1).
- **Storage model:** Row-of-floats per archive in a **fixed-size, file-based format** called Whisper (one `.whisper` file per metric series), modeled on RRDtool (round-robin database) ([Whisper docs](https://graphite.readthedocs.io/en/stable/whisper.html)). Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) — it is pre-allocated flat files of big-endian double + timestamp pairs, written in-place. An alternate backend, Ceres, exists but Whisper is the canonical store. Not [columnar-storage](../concepts/columnar-storage.md).
- **Workload:** OLAP-ish read-mostly time-series queries over a high-write metrics ingest. Not OLTP, not HTAP — there is no general query workload, only metric writes and time-range graph reads. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Core Whisper/Carbon is **single-node**; "clustering" is achieved by sharding metrics across independent Carbon nodes via a consistent-hash relay (`carbon-relay`, `carbon-c-relay`, `carbon-relay-ng`). There is no cross-node consensus or transaction, so CAP is N/A in the strict sense — each metric lives on one (or, with relay replication, two) node(s) and queries fan out and merge. A partition makes the unreachable shard's metrics simply unavailable; surviving shards keep serving. See [cap-pacelc](../concepts/cap-pacelc.md), [replication-models](../concepts/replication-models.md).
- **PACELC:** N/A — no distributed consistency protocol. Replication, where used, is best-effort fire-and-forget duplication by the relay, not a quorum.
- **Default isolation & what's achievable:** No transactions, no isolation levels — writes are last-write-wins overwrites of fixed time slots. There is no ACID claim to scrutinize here ([isolation-levels](../concepts/isolation-levels.md) is not applicable).
- **Replication:** Optional and crude. `carbon-relay` can send each metric to N downstream nodes (typically 2) for redundancy; replicas are picked as the next non-colliding node(s) on the hash ring — you cannot pin *which* node holds a replica, and without `DIVERSE_REPLICAS=True` both copies can even land on the same physical host ([carbon issue #333](https://github.com/graphite-project/carbon/issues/333), [scaling notes](https://medium.com/teads-engineering/scaling-graphite-in-a-cloud-environment-6a92fb495e5)). No automatic failover, no reconciliation — two replicas can silently diverge if one node was down during a write window. There is no anti-entropy; `carbonate`/`whisper-fill` are manual repair tools.
- **Tunable consistency?** No.
- **Clock dependency:** Relies on the producing client's wall-clock timestamp (or server receive time if absent). Skewed client clocks land data in the wrong slot. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Schemaless metric namespace — any new dotted metric name auto-creates a Whisper file on first write. Retention/rollup "schema" is config-driven: `storage-schemas.conf` (retention archives) and `storage-aggregation.conf` (rollup function) are matched by regex against the metric name **at file-creation time**.
- **Migration/evolution:** Changing retention or aggregation in config does **not** rewrite existing files — you must run `whisper-resize.py` per file to apply new retention, which rebuilds the file. This is the classic Graphite operational footgun: editing the config "does nothing" to already-created metrics.
- **Type system:** Numeric only — one double-precision float per point. No strings, no multi-field points (each measurement is its own metric path), no native geospatial/JSON/vectors. Tags (key=value, since 1.1.1) add a secondary tag index (a pluggable TagDB — default local SQLite/MySQL/Postgres, or Redis) ([Graphite tag support docs](https://graphite.readthedocs.io/en/stable/tags.html)) but the underlying storage is still one file per resolved series.

## Query interface
- **Language:** Not SQL. The render API takes a `target` expression composed of **Graphite functions** (`sumSeries()`, `movingAverage()`, `summarize()`, `aliasByNode()`, `derivative()`, etc.) over wildcarded metric globs (`servers.*.cpu.load`). API-only / HTTP render endpoint returning PNG, JSON, CSV, etc.
- **Transactions:** None.
- **Native vs app-side:** Aggregation and time-series math are native via the function library (one of Graphite's genuine strengths — a rich, composable function set). No joins in the relational sense; "joins" are metric-glob fan-in. Secondary indexing only via the optional tag index.
- **Stored procedures / UDFs:** None in the SQL sense; you extend by writing Python functions into graphite-web, not as runtime UDFs.

## Scaling & topology
- **Vertical vs horizontal:** Primarily **vertical** — a single Carbon/Whisper node is bounded by disk IOPS. Horizontal scaling is **manual sharding** via a consistent-hash relay tier feeding many `carbon-cache` nodes. See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Sharding pain:** Significant. Adding/removing a node changes the hash ring and requires **rebalancing** (moving Whisper files with `carbonate`); the legacy hash ring has only 64k slots and is uneven, causing hotspots ([scaling notes](https://medium.com/teads-engineering/scaling-graphite-in-a-cloud-environment-6a92fb495e5)). This is the central reason large shops migrate off Graphite or move to a Cassandra-backed store ([apache-cassandra](apache-cassandra.md)) via the Cyanite/Metrictank ecosystem.
- **Read replicas / read consistency:** graphite-web can federate over multiple data nodes (`CLUSTER_SERVERS`) and merge results; reads can be stale or partial if a shard is down. No notion of consistent reads.
- **Storage/compute separation:** None in core Graphite. (Hosted variants and Metrictank/Cassandra backends decouple this externally.) See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** No WAL. `carbon-cache` buffers incoming points **in RAM** and flushes to Whisper files in batches; the fixed-size layout means each archive update is a single contiguous in-place disk write ([Whisper docs](https://graphite.readthedocs.io/en/stable/whisper.html)). **Crash → data-loss window** = whatever was buffered in carbon-cache and not yet flushed (can be many seconds to minutes under `MAX_UPDATES_PER_SECOND` throttling). Whisper itself is not crash-safe against torn writes; a power loss mid-write can corrupt a file. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Bounded by random-write IOPS — one seek/write per metric per flush. The fixed-size archive design makes reads predictable (one contiguous read serves a time range), but high-cardinality ingest (millions of metrics) overwhelms a single node's disk, the well-known scaling wall. SSD/NVMe is effectively mandatory at scale.
- **Compaction / vacuum / GC:** **None** — and that is the point of the RRD design. Files never grow (fixed size, round-robin overwrite of the oldest slot), so there is no compaction, no GC, no p99 spikes from background merges. The flip side: every slot is pre-allocated whether or not data exists, so **sparse/short-lived metrics waste disk** and you pay full file size up front.

## Operations & maturity
- **Backup/restore, PITR:** Backup = copy the Whisper files (they are self-contained). No PITR concept; the data *is* the time series. Snapshotting is filesystem-level.
- **Observability:** Graphite is itself a monitoring tool; carbon exposes internal metrics about itself. graphite-web has no EXPLAIN/query-plan concept (queries are function pipelines). Slow renders are diagnosed via the render API and logs.
- **Upgrade story:** Components (carbon, whisper, graphite-web) upgrade independently; Whisper file format is stable across versions, so upgrades are low-risk. Day-2 burden is real: hash-ring rebalancing, per-file retention resizes, disk-IOPS capacity planning, and storing tons of small files.
- **Maturity:** Very mature (since ~2008, open-sourced 2008, Apache 2.0). Widely deployed historically; **largely in maintenance mode** as Prometheus ([prometheus](prometheus.md)), [victoriametrics](victoriametrics.md), [influxdb](influxdb.md), and Grafana-native stacks took over new deployments. No Jepsen report — Graphite is not a consensus/replicated system, so Jepsen-style linearizability testing does not apply.

## Ecosystem & people
- **Canonical use cases:** Operational dashboards and ops metrics where you push pre-aggregated metrics (often via StatsD), with fixed known retention. Pairs ubiquitously with **StatsD** (metric aggregation), **collectd**, and **Grafana** (the dominant viz front-end; Graphite remains a first-class Grafana datasource).
- **Anti-patterns / when it is the wrong tool:** High-cardinality / dynamic-label metrics (Whisper pre-allocates a file per series — cardinality explosions kill it); event/log data; anything needing tags-first querying, pull-based scraping, or alerting rules (use [prometheus](prometheus.md)); anything needing horizontal elasticity without manual resharding; precise raw retention of irregular/sparse series. Push model means you instrument-and-emit rather than scrape.
- **Drivers / connectors:** Plaintext line protocol (`metric value timestamp\n`), pickle protocol, and AMQP ingestion; the carbon plaintext protocol is a de-facto standard many other TSDBs (InfluxDB, VictoriaMetrics) accept for migration. Grafana, Graphite-API, Graphios, Diamond, etc.
- **Community/support/docs:** Docs are decent and stable; community is mature but quieter now. Commercial/hosted Graphite available (e.g., MetricFire/Hosted Graphite, Grafana Cloud Graphite). Learning curve is low for basics; operational scaling is the hard part.

## Licensing & cost
- **OSS license & flavor:** **Apache License 2.0** — permissive, no post-2018 relicensing drama. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Predominantly self-managed; hosted offerings exist (MetricFire/Hosted Graphite, Grafana Cloud).
- **Lock-in:** Low — open format, open protocol; the carbon line protocol is widely emulated, making migration off Graphite straightforward at the ingest layer.
- **Cost model:** Free software; cost is your infrastructure — dominated by **disk** (pre-allocated per metric) and IOPS. At small scale it is extremely cheap; at large cardinality the per-file disk and rebalancing toil make TCO invert versus modern compressed columnar TSDBs ([victoriametrics](victoriametrics.md), [clickhouse](clickhouse.md)-backed stacks).

## Hardware / deployment
- **Resource profile:** **Disk-IOPS-bound** above all (random writes, one per metric per flush); carbon-cache is RAM-buffered so memory matters for write batching; CPU is light. Working set need not fit in RAM, but the filesystem page cache strongly affects read latency.
- **Storage assumptions:** SSD/NVMe strongly recommended at any real metric count; spinning disk falls over on random I/O. Local disk preferred — network-attached storage latency hurts the per-file write pattern.
- **Footprint:** Single-node core, optionally a manually-sharded cluster behind relays. Not embedded, not serverless.
- **Deployment:** On-prem or VM/container; runs on k8s but Whisper's many-small-files + IOPS profile makes StatefulSet-on-network-storage a poor fit. Pairs with StatsD/collectd agents and Grafana.

## Bottom line
Reach for Graphite when you have a **bounded, known set of metric series**, want dead-simple push-based ingest (StatsD → carbon), fixed retention with automatic rollups, and a rich graphing function library — at small/medium scale it is cheap, predictable, and has no GC surprises. Do **not** choose it for new high-cardinality, tag-driven, or pull-based monitoring (use [prometheus](prometheus.md) / [victoriametrics](victoriametrics.md)) or where you need elastic horizontal scaling without manual resharding. The single biggest gotcha: Whisper **pre-allocates a fixed-size file per metric at first write**, so cardinality explosions silently eat disk and editing retention config does nothing to existing files until you resize each one by hand.

## Sources
- [Whisper database format — Graphite docs](https://graphite.readthedocs.io/en/stable/whisper.html)
- [graphite-project/whisper (GitHub)](https://github.com/graphite-project/whisper)
- [Carbon & Whisper architecture walkthrough](https://franklinangulo.com/blog/2014/5/17/step-by-step-carbon-whisper)
- [The Carbon Daemons (MetricFire)](https://www.metricfire.com/blog/the-carbon-daemons-graphite-monitoring/)
- [Scaling Graphite in a cloud environment (Teads Engineering)](https://medium.com/teads-engineering/scaling-graphite-in-a-cloud-environment-6a92fb495e5)
- [Graphite/Scaling (Wikimedia Wikitech)](https://wikitech.wikimedia.org/wiki/Graphite/Scaling)
