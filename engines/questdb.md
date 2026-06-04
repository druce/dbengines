---
name: QuestDB
slug: questdb
rank: 78
data_model: Time-series
license: Apache 2.0 (open core; Enterprise is proprietary)
summary: Single-node columnar time-series DB optimized for fast ILP ingest and SQL; clustering/HA is Enterprise-only.
last_researched: 2026-06-04
confidence: high
---

# QuestDB

> A high-throughput, single-node columnar time-series engine that pairs InfluxDB-line-protocol ingest with PostgreSQL-flavored SQL; horizontal scale and replication live behind the Enterprise license.

## When to use

**Use QuestDB if:**
- ✅ You need to firehose time-ordered data (market ticks, metrics, IoT/sensor telemetry) into one fast box with multi-million-rows/sec ingest
- ✅ You want PostgreSQL-dialect SQL with time-series extensions (`SAMPLE BY`, `LATEST ON`, `ASOF JOIN`) and the Postgres wire protocol
- ✅ You want HTAP-on-one-engine for time-series — fast ILP ingest plus sub-second analytical scans over time ranges
- ✅ You want Apache-2.0 OSS for a single big NVMe node with minimal operational ceremony

**Avoid QuestDB if:**
- ❌ You expect general OLTP/CRUD — the biggest functional gotcha is no single-row deletes (drop whole partitions), no multi-table transactions, and no foreign keys
- ❌ You need native multi-node sharding on the open-source tier — replication, failover, and security are Enterprise-gated; OSS is genuinely single-node
- ❌ You have high-cardinality `SYMBOL` columns or frequent random updates (copy-on-write write amplification)
- ❌ You need independently-verified distributed consistency — no public Jepsen report, and default commit mode doesn't fsync per commit (power-loss window)

## Identity
- **Taxonomy / data model:** Time-series database with a relational SQL surface. Tables are time-partitioned; a designated timestamp column drives storage order. See [time-series-storage](../concepts/time-series-storage.md).
- **Storage model:** Column-store. Each column is its own memory-mapped file in QuestDB's native binary format, time-partitioned (by hour/day/month/year), with older partitions tierable to Apache Parquet on object storage ([storage engine docs](https://questdb.com/docs/architecture/storage-engine/)). Write path is row-oriented (append-fast WAL); read path is columnar — not an [lsm-vs-btree](../concepts/lsm-vs-btree.md) design but an append-mostly columnar log with copy-on-write updates.
- **Workload:** OLTP-style high-velocity ingest + OLAP-style analytical scans over time ranges — effectively HTAP-on-one-engine for time-series, achieved by separating a row-based write path from a column-based read path rather than by separate replicas/stores. Not a general-purpose OLTP database (no row-level deletes, no FKs). See [oltp-olap-htap](../concepts/oltp-olap-htap.md), [columnar-storage](../concepts/columnar-storage.md).

## Distribution & consistency
- **CAP under partition:** N/A for open-source single-node. Enterprise replication has two modes: classic single-primary (primary uploads WAL to object store; replicas pull and apply, async, may lag) and **multi-primary ingestion**, where multiple primaries write concurrently and a [FoundationDB](https://www.foundationdb.org/) cluster acts as the distributed sequencer assigning unique monotonic transaction IDs ([multi-primary ingestion docs](https://questdb.com/docs/operations/multi-primary-ingestion/)). Replication to object store is async, so this is a CP-leaning ingest path with eventually-consistent read replicas. See [cap-pacelc](../concepts/cap-pacelc.md), [replication-models](../concepts/replication-models.md).
- **PACELC:** Effectively single-node (EL tradeoff only): tuned for latency. Enterprise async replicas favor availability of reads over freshness (replicas can be stale).
- **Default isolation:** Read Committed; tables are MVCC-style (multiple data versions) so readers see consistent committed snapshots during concurrent writes ([dbdb.io](https://dbdb.io/db/questdb), [transactional table glossary](https://questdb.com/glossary/transactional-table/)). The "ACID" claim is real at the single-table level — atomic, durable, isolated commits per WAL transaction — but there are **no multi-table/multi-statement transactions**. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Enterprise-only. Primary writes WAL to S3 / Azure Blob / NFS; replicas download and replay it; auto-failover (a suitable replica is promoted to primary on failure) and multi-region read replicas are managed features ([HA overview](https://questdb.com/docs/high-availability/overview/)). Enterprise also offers **multi-primary ingestion** (multiple concurrent write nodes coordinated by a FoundationDB sequencer), so "single-leader" is no longer the only Enterprise topology ([multi-primary docs](https://questdb.com/docs/operations/multi-primary-ingestion/)). Open-source has no built-in replication or failover.
- **Tunable consistency?** No per-query consistency levels.
- **Clock dependency:** Correctness does not rest on synchronized cluster clocks; the per-table **Sequencer** assigns monotonic transaction numbers across parallel WALs as the single source of truth (in Enterprise multi-primary, that role is played by a FoundationDB cluster issuing globally unique, auto-incrementing transaction IDs rather than wall-clock time). The designated timestamp is application/ingest-supplied data, not a consensus clock. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Tables have fixed typed columns; ILP can auto-create columns/tables on first write (schema inferred from the line), which is convenient but can lead to accidental schema drift.
- **Migration/evolution:** `ALTER TABLE ADD/DROP/RENAME COLUMN` supported. `UPDATE` is transactional copy-on-write (writes a new column file), so heavy updates inflate disk usage ([updating data](https://questdb.com/docs/operations/updating-data/)).
- **Type system:** numeric types, `SYMBOL` (dictionary-encoded low-cardinality strings, optionally hash-indexed), `VARCHAR`/`STRING`, `TIMESTAMP`, `BOOLEAN`, `UUID`, geohash, arrays (incl. multi-dimensional `DOUBLE[]`). No native JSON document type, no foreign keys.

## Query interface
- **Language:** SQL, PostgreSQL-dialect-compatible, with time-series extensions: `SAMPLE BY` (downsampling), `LATEST ON`, and temporal joins `ASOF JOIN`, `LT JOIN`, `SPLICE JOIN`, plus newer `WINDOW JOIN` / `HORIZON JOIN` / lateral joins ([join docs](https://questdb.com/docs/query/sql/join/)). Accessible via Postgres wire protocol, REST/HTTP, and a web console.
- **Transactions:** Single-table atomic commits only. **No multi-statement BEGIN/COMMIT spanning tables.**
- **Native vs app-side:** Native INNER/LEFT/CROSS joins (nested-loop and hash), aggregations, window functions, and the temporal joins above. Indexing limited to `SYMBOL` columns; no general secondary indexes (queries rely on timestamp partitioning + columnar scans).
- **Stored procedures / UDFs:** No general stored-procedure or UDF facility. ⚠️ unverified — no user-defined-function language is documented as of mid-2026.
- **DELETE:** No single-row delete; you can `DROP` whole partitions or rebuild the table to remove rows ([modifying data](https://questdb.com/docs/operations/updating-data/)). This is the biggest functional gotcha for anyone expecting OLTP CRUD.

## Scaling & topology
- **Vertical first.** QuestDB is fundamentally single-node and optimized to saturate one big box (many cores, NVMe). Enterprise multi-primary ingestion spreads *writes* across nodes, but there is still **no automatic horizontal sharding of the dataset across nodes** ([sharding/multi-primary issue #4957](https://github.com/questdb/questdb/issues/4957), open as of mid-2026); marketing that mentions "distribute data across nodes" should be read as parallel ingest + replication, not a sharded store.
- **Sharding/partitioning:** Time partitioning within a node only; resharding across machines is a manual/application concern.
- **Read replicas:** Enterprise only; replicas pull WAL from object storage and serve consistent (possibly stale) reads.
- **Storage/compute separation:** Partial and Enterprise-leaning — WAL and cold Parquet tiers can live on object storage, and replicas reconstruct state from that shared WAL, approximating shared-storage replication. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Parallel WALs (multiple concurrent writers) coordinated by the Sequencer; commits are acknowledged fast, then a background job merges/dedups data into columnar storage, resolving out-of-order rows ([WAL concept](https://questdb.com/docs/concepts/write-ahead-log/)). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Durability / data-loss window:** Committed WAL transactions survive an OS-managed restart and are replayed. **By default QuestDB does not fsync on every commit** — it relies on OS-level durability (dirty pages flushed by the OS), so a sudden power loss can lose recently committed-but-unflushed data; an opt-in **sync-commit / `cairo.commit.mode=sync`** mode fsyncs each commit at the cost of throughput ([storage engine docs](https://questdb.com/docs/architecture/storage-engine/)). ⚠️ unverified — the exact default flush interval is not precisely documented; the community has reported active-partition loss on power loss with default settings.
- **Throughput/latency:** Marketed and benchmarked (by QuestDB) for multi-million-rows/sec ingest and sub-second analytical scans; vendor benchmarks vs TimescaleDB/InfluxDB are self-published and should be treated as directional, not neutral ([vendor benchmark](https://questdb.com/blog/timescaledb-vs-questdb-comparison/)).
- **Compaction/GC:** Java + C++ core written to avoid JVM garbage collection on the hot path (off-heap, memory-mapped). Out-of-order ingest triggers partition rewrites/merges; `UPDATE` copy-on-write and heavy O3 ingestion are the main sources of write amplification and p99 spikes.

## Operations & maturity
- **Backup/restore:** Snapshot/checkpoint mechanism for consistent backups; cold data in Parquet on object storage. ⚠️ unverified — point-in-time recovery granularity is not clearly documented for open-source.
- **Observability:** Web console with query plans (`EXPLAIN`), Prometheus metrics endpoint, query logging.
- **Upgrade story:** Single-node upgrades generally require a restart (brief downtime); Enterprise replicas enable rolling-ish read availability. Day-2 burden centers on disk capacity planning (copy-on-write/O3 write amplification) and avoiding unbounded `SYMBOL` cardinality.
- **Maturity:** Production-used in fintech/trading and IoT/observability; active OSS project. **No public Jepsen report exists** — distributed-consistency claims (Enterprise replication) are unverified by independent formal testing. ⚠️ unverified — no third-party Jepsen/formal analysis as of mid-2026.

## Ecosystem & people
- **Canonical use cases:** financial market/tick data, trading systems, IoT/sensor telemetry, application & infrastructure metrics — anything write-heavy, time-ordered, and queried by time range.
- **Anti-patterns:** general-purpose OLTP/CRUD (no row deletes, no multi-table transactions, no FKs); high-cardinality dimension explosions in `SYMBOL` columns; workloads needing native multi-node sharding on the open-source tier; frequent random updates (copy-on-write cost). Queries without a timestamp filter force full scans.
- **Drivers/connectors:** Postgres wire protocol means most Postgres clients/BI tools work; first-party ILP clients (Python, Java, Go, C/C++, Rust, .NET, Node); Grafana, Kafka (via connectors/ILP), Telegraf. dbt support via the Postgres adapter is partial. See [full-text-search](../concepts/full-text-search.md) — N/A, no full-text search.
- **Community/support:** Mid-sized OSS community; commercial support via QuestDB Enterprise/Cloud. Docs are good for SQL/ingest, thinner on durability internals. Low learning curve for anyone who knows SQL.

## Licensing & cost
- **OSS license:** Apache 2.0 (permissive) for the core engine ([GitHub](https://github.com/questdb/questdb)). **Enterprise is proprietary/source-available** and gates replication, RBAC/security, ZFS compression, multi-tier blob storage, and 24×7 support — a classic open-core split. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-host OSS; QuestDB Cloud (managed) and Enterprise (self-managed licensed) for HA/security. Lock-in risk is mainly the native storage format and Enterprise-only HA features.
- **Cost model:** OSS free; Cloud is instance/usage-based; Enterprise is commercial licensing. Cost scales with the size of the single node (vertical) plus object-storage tiers — cheap at small scale, with vertical-scaling ceilings at very large scale.

## Hardware / deployment
- **Resource profile:** Disk/IO-bound for ingest and scans, CPU-bound for analytical queries; benefits from many cores. Working set need not fit in RAM (memory-mapped columnar files), but more RAM improves cache hit rates.
- **Storage assumptions:** Strongly prefers fast local NVMe for the hot tier; network-attached/object storage is intended for cold Parquet tiers and Enterprise replication WAL, not the hot path.
- **Footprint:** Single-node server (also embeddable as a Java library). Clustered/HA only via Enterprise.
- **Deployment:** Self-hosted (binary, Docker), Kubernetes-friendly as a StatefulSet, AWS Marketplace AMI, and managed QuestDB Cloud.

## Bottom line
Reach for QuestDB when you need to firehose time-ordered data (market ticks, metrics, sensors) into one fast box and run SQL/time-series analytics with minimal operational ceremony. Do not reach for it as a general OLTP store — no row deletes, no multi-table transactions, no foreign keys — or when you need native multi-node sharding without paying for Enterprise. The single biggest gotcha: the open-source tier is genuinely single-node (replication, failover, and security are Enterprise-gated), and there is no independent Jepsen validation of its distributed-consistency claims.

## Sources
- [QuestDB architecture overview](https://questdb.com/docs/architecture/questdb-architecture/)
- [Storage engine](https://questdb.com/docs/architecture/storage-engine/)
- [Write-Ahead Log concept](https://questdb.com/docs/concepts/write-ahead-log/)
- [JOIN keyword docs](https://questdb.com/docs/query/sql/join/)
- [Updating / modifying data](https://questdb.com/docs/operations/updating-data/)
- [High-availability / replication overview](https://questdb.com/docs/high-availability/overview/)
- [Transactional table glossary](https://questdb.com/glossary/transactional-table/)
- [dbdb.io entry on QuestDB](https://dbdb.io/db/questdb)
- [GitHub: questdb/questdb (Apache 2.0)](https://github.com/questdb/questdb)
- [Sharding / multi-primary issue #4957](https://github.com/questdb/questdb/issues/4957)
- [Vendor benchmark vs TimescaleDB](https://questdb.com/blog/timescaledb-vs-questdb-comparison/)
