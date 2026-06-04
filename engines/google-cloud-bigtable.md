---
name: Google Cloud Bigtable
slug: google-cloud-bigtable
rank: 104
data_model: Wide-column
license: Proprietary (managed cloud service)
summary: Google's managed, horizontally scalable wide-column store — the original Bigtable from the 2006 paper, sold as a service with single-row atomicity and no cross-row transactions.
last_researched: 2026-06-04
confidence: high
---

# Google Cloud Bigtable

> Managed petabyte-scale wide-column key-value store with single-digit-millisecond latency and linear node scaling — but only single-row atomicity, no SQL transactions, and eventual consistency once you replicate across clusters.

## Identity
- **Taxonomy / data model:** Wide-column / sparse multidimensional sorted map. The cell key is the four-tuple (row key, column family, column qualifier, timestamp); cells hold versioned values. This is the same model as the [Bigtable 2006 paper](https://research.google.com/archive/bigtable-osdi06.pdf) and the conceptual ancestor of [apache-hbase](apache-hbase.md), [apache-cassandra](apache-cassandra.md), and [apache-accumulo](apache-accumulo.md). See [wide-column](../concepts/wide-column.md).
- **Storage model:** [LSM-tree](../concepts/lsm-vs-btree.md). Data is written to SSTables (persistent, ordered, immutable maps) on [Colossus](https://docs.cloud.google.com/bigtable/docs/overview), Google's distributed filesystem. Compute (nodes) is separated from storage (Colossus) — see [storage-compute-separation](../concepts/storage-compute-separation.md). Rows are range-partitioned into *tablets*; nodes hold pointers to tablets, not the data itself, so rebalancing and failure recovery move pointers rather than bytes.
- **Workload:** OLTP-style high-throughput key-value / wide-column reads and writes; also used as an analytics/time-series serving layer. Not an analytics query engine (no aggregations/joins in the storage engine; SQL support is limited — see Query interface). Not [HTAP](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** Effectively **CP for a single cluster** (a single-cluster instance is strongly consistent and atomic in arrival order ([docs](https://docs.cloud.google.com/bigtable/docs/overview))). With replication across clusters it leans **AP** — clusters stay serving and reconcile later. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** On partition (multi-cluster), favors availability over consistency (AP); else (no partition), tunable per app profile — single-cluster routing favors consistency/latency-from-one-cluster, multi-cluster routing favors availability with eventual consistency. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation:** No general isolation model — there are no multi-row transactions. **All reads/writes are atomic at the single-row level only**, including multi-column mutations in one operation, read-modify-write, and check-and-mutate ([docs](https://docs.cloud.google.com/bigtable/docs/writes)). ⚠️ unverified — Bigtable does not publish a standard [isolation level](../concepts/isolation-levels.md) because it does not offer multi-statement transactions; treat it as "single-row atomicity, no snapshot isolation across rows."
- **Replication:** Leaderless / **multi-primary** — every cluster in an instance accepts reads and writes; changes propagate asynchronously (typically seconds to minutes) ([replication overview](https://docs.cloud.google.com/bigtable/docs/replication-overview)). Up to 8 regions, one cluster per zone (⚠️ unverified — current docs state the per-instance limit as "up to 8 regions, one cluster per zone" and no longer publish a fixed total-cluster cap). Conflict resolution is **last-write-wins by server timestamp** on the cell four-tuple ([docs](https://docs.cloud.google.com/bigtable/docs/replication-overview)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** Via **app profiles** + routing policy. Single-cluster routing → strong consistency and read-your-writes; multi-cluster routing → eventual consistency (read-your-writes only with row-affinity). Single-row transactions (read-modify-write, check-and-mutate) **cannot be used with multi-cluster routing** because they would create cross-cluster conflicts ([docs](https://docs.cloud.google.com/bigtable/docs/routing)). After failover, even single-cluster setups revert to eventual consistency until unreplicated writes catch up ([docs](https://docs.cloud.google.com/bigtable/docs/replication-overview)).
- **Clock dependency:** Conflict resolution depends on server-side timestamps; clock skew can affect which write "wins" under last-write-wins. No TrueTime guarantee here (that is [Cloud Spanner](google-cloud-spanner.md)). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read, mostly.** You define tables and column families up front; column qualifiers are dynamic (created on write), and tables are sparse — absent columns cost nothing. Rows can have wildly different columns.
- **Migration/evolution:** Adding column families is an online operation; the on-disk format is schemaless within a family, so adding/removing qualifiers needs no DDL. Garbage-collection policies (max versions, max age) are set per column family.
- **Type system:** Values are uninterpreted **byte strings** (no native typed columns at the storage layer). Aggregate column types (e.g. SUM/MIN/MAX counters) exist as a newer feature. No native JSON/geospatial/vector types; structure lives in app code and row-key design.

## Query interface
- **Language:** API-first. Native gRPC/REST client libraries (Java, Go, Python, C#, Node.js, Ruby, C++); a **drop-in [HBase](apache-hbase.md) API** (Java) for portability; **GoogleSQL** read-only query support (relatively limited — point/range scans, filters), not a full transactional SQL surface.
- **Transactions:** Single-row only — read-modify-write (incl. atomic increments) and check-and-mutate (conditional). **No multi-row, no multi-statement ACID transactions** ([docs](https://docs.cloud.google.com/bigtable/docs/overview)).
- **Native vs app-side:** No joins, no secondary indexes, no server-side aggregations beyond aggregate cells. Access patterns must be designed into the **row key** (Bigtable's only index). Filters run server-side on scans.
- **Stored procedures / UDFs:** None.

## Scaling & topology
- **Horizontal** by adding nodes; throughput scales roughly linearly with node count. Sharding is **automatic** — tablets split/merge and rebalance with no manual resharding, the headline advantage over self-managed [apache-hbase](apache-hbase.md)/[apache-cassandra](apache-cassandra.md). Partitioning is range-based on the lexicographically sorted row key, so **bad key design (monotonic keys / timestamps as prefix) causes hotspotting** — the single biggest operational gotcha.
- **Autoscaling:** Clusters can autoscale node count on CPU/storage utilization, or be resized manually with no downtime.
- **Read replicas / read consistency:** Replication is multi-primary, not read-replica; reads from a non-write cluster are eventually consistent unless routed single-cluster or with row-affinity.
- **Storage/compute separation:** Yes — data on Colossus, nodes are stateless compute. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Writes hit a commit log (WAL) and an in-memory memtable on Colossus, then flush to SSTables; Colossus provides the durability and replication of the bytes. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact fsync/group-commit semantics and crash data-loss window are not publicly documented in detail; durability is delegated to Colossus's replicated storage, so the practical data-loss window for an acknowledged write is effectively zero on a single cluster.
- **Throughput/latency:** Designed for **single-digit-millisecond** reads/writes at high QPS; an in-memory tier (Preview) targets **sub-millisecond reads** ([docs](https://docs.cloud.google.com/bigtable/docs/in-memory-overview)). p99 tail latency is sensitive to hotspotting and to compaction; Google publishes guidance to keep CPU below ~70% to protect tail latency.
- **Compaction / GC:** Background compaction rewrites SSTables (documentation notes compaction happens roughly weekly on average) to drop deleted/expired cells; garbage collection enforces per-family version/age limits. Compaction is managed by Google but still competes for cluster resources and can affect p99.

## Operations & maturity
- **Backup/restore:** Native table backups (schema + data), restorable to new tables across regions/projects. ⚠️ unverified — continuous point-in-time recovery to an arbitrary timestamp is not a first-class feature the way it is in some RDBMS; recovery is backup-based plus replication.
- **Observability:** Cloud Monitoring metrics, Key Visualizer (heatmap to spot hotspots), CPU/latency dashboards. No EXPLAIN-style planner (limited query surface).
- **Upgrade story:** Fully managed — no version upgrades, patching, or compaction tuning by the user; node resizing and failover are online. Day-2 burden is largely **row-key/schema design and cost control**, not infrastructure.
- **Maturity:** Very high — the production lineage traces to Google's internal Bigtable (2005+) behind Search, Maps, Gmail; GA as a cloud product since 2016. No public Jepsen report exists for Cloud Bigtable; its consistency story is documented rather than independently formally verified.

## Ecosystem & people
- **Canonical use cases:** Time-series and IoT data, ad-tech, fraud/personalization serving, user-activity and graph-adjacency storage, large-scale operational metrics — anything with a clear key-based access pattern and huge volume. Backs HBase migrations to GCP.
- **Anti-patterns:** Small datasets (cost-inefficient below ~1 TB / few nodes); workloads needing multi-row transactions, joins, ad-hoc analytics, or secondary indexes (use [google-cloud-spanner](google-cloud-spanner.md), [postgresql](postgresql.md), or [google-bigquery](google-bigquery.md)); use cases requiring strong cross-region consistency with availability (Spanner instead).
- **Connectors:** HBase API compatibility; Dataflow/Beam, Dataproc/Spark/Hadoop connectors; CDC via change streams to Dataflow/Pub-Sub; integration with [google-bigquery](google-bigquery.md) (federated queries/export). Strong fit inside the GCP data stack, weaker outside it.
- **Community/support:** Backed by Google Cloud support; docs quality is high. Learning curve centers on schema/row-key design, not operations.

## Licensing & cost
- **License:** Proprietary, managed-only cloud service — there is no self-hostable Bigtable (the closest open analog is [apache-hbase](apache-hbase.md)/[apache-accumulo](apache-accumulo.md)). See [license-taxonomy](../concepts/license-taxonomy.md). A local emulator exists for development only.
- **Self-managed vs managed:** Managed-only; lock-in is real but mitigated by HBase-API compatibility (apps can in principle target HBase). GoogleSQL and GCP-specific tooling deepen lock-in.
- **Cost model:** Per-node-hour (≈ $0.65/node/hour, region-dependent) + per-GB storage (SSD ≈ $0.17/GB-month, HDD ≈ $0.026/GB-month) + network egress ([pricing](https://cloud.google.com/bigtable/pricing)); 1-year/3-year committed-use discounts (~20%+). **Expensive at small scale** (you pay for nodes even when idle) and **cheap per-unit at large scale** — the classic inversion. Replication multiplies node + storage cost per cluster.

## Hardware / deployment
- **Resource profile:** CPU-bound at the node tier for throughput; storage decoupled to Colossus, so data volume does not need to fit in RAM (an in-memory tier exists for hot data). Working set need not fit in RAM.
- **Storage assumptions:** Network-attached distributed storage (Colossus), not local disk; SSD vs HDD is a per-instance choice trading latency for cost.
- **Footprint:** Clustered, regional service (clusters are zonal; instances span zones/regions). No embedded mode; a local emulator for dev only.
- **Deployment:** SaaS only on Google Cloud — no on-prem, no k8s self-hosting. Provisioned and scaled via GCP console/API/Terraform.

## Bottom line
Reach for Cloud Bigtable when you have a massive, high-throughput key-value or time-series workload with a clean key-based access pattern and want Google to handle sharding, rebalancing, and durability. Do **not** reach for it if you need multi-row transactions, joins, secondary indexes, ad-hoc SQL analytics, or you have a small dataset — it is overkill and overpriced below a terabyte. The single biggest gotcha is **row-key design**: monotonic or poorly distributed keys create hotspots that no amount of nodes will fix, and "ACID" here means single-row atomicity only, with eventual consistency the moment you replicate across clusters.

## Sources
- [Bigtable overview | Google Cloud Documentation](https://docs.cloud.google.com/bigtable/docs/overview)
- [Replication overview | Bigtable](https://docs.cloud.google.com/bigtable/docs/replication-overview)
- [Routing options | Bigtable](https://docs.cloud.google.com/bigtable/docs/routing)
- [Writes | Bigtable](https://docs.cloud.google.com/bigtable/docs/writes)
- [In-memory tier overview | Bigtable](https://docs.cloud.google.com/bigtable/docs/in-memory-overview)
- [Bigtable pricing | Google Cloud](https://cloud.google.com/bigtable/pricing)
- [Bigtable: A Distributed Storage System for Structured Data (OSDI 2006)](https://research.google.com/archive/bigtable-osdi06.pdf)
- [Google Cloud Bigtable | db-engines.com](https://db-engines.com/en/system/Google+Cloud+Bigtable)
