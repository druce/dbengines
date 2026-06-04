---
name: Sphinx
slug: sphinx
rank: 63
data_model: Search engine
license: GPLv2 (v1–2.x, open source) → proprietary/source-available (v3+); see note
summary: Veteran C++ full-text search server with a MySQL-protocol query interface; the open-source line is effectively frozen and the live successor is the Manticore fork.
last_researched: 2026-06-04
confidence: high
---

# Sphinx

> A fast, lean C++ full-text indexer/search daemon from 2001 that pioneered SQL-over-MySQL-protocol search, now bifurcated into a closed-source v3 line and the actively-maintained open-source [Manticore Search](sphinx.md) fork — pick the fork.

## Identity
- **Taxonomy / data model:** Dedicated full-text [full-text-search](../concepts/full-text-search.md) search engine, not a primary datastore. Documents = sets of full-text fields + typed attributes (int, bigint, float, bool, string, MVA, JSON). Often run alongside an OLTP source DB rather than as the system of record.
- **Storage model:** Inverted index ([lsm-vs-btree](../concepts/lsm-vs-btree.md) is the wrong axis here; this is an inverted-index engine). Two backends: **disk indexes** (immutable, built in batch by the `indexer` process; only attributes can be updated in place, full-text content cannot) and **RT (real-time) indexes** (a RAM chunk + immutable disk chunks merged on the fly — an LSM-like layout where commits land in RAM and periodically flush to disk). The name reportedly derives from "SQL Phrase Index." On-disk format is Sphinx-proprietary index files.
- **Workload:** Read-heavy full-text search / retrieval; not OLTP, not OLAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Classic deployment pattern is a search sidecar that indexes rows pulled from MySQL/PostgreSQL/MSSQL/ODBC.

## Distribution & consistency
- **CAP under partition:** Not a meaningful CP/AP classification — Sphinx is a search index over an external source of truth, with no built-in replication or quorum in the open-source line. A "distributed index" is just **scatter-gather sharding** across `searchd` nodes; if a shard node is partitioned away, queries against it fail or return partial results (configurable), there is no consensus or automatic reconciliation. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A in the formal sense — no replication protocol to trade off. Else-case behavior is latency-optimized single-node retrieval.
- **Default isolation & what's achievable:** RT-index writes are transactional **per session** — changes accumulate in a per-thread accumulator until `COMMIT`, then apply atomically ([sphinxsearch.com RT binlog docs](http://sphinxsearch.com/docs/current/rt-binlog.html)). This is single-index atomic batch apply, **not** multi-statement cross-index ACID and **not** classic SQL isolation levels — do not read it as serializable. See [isolation-levels](../concepts/isolation-levels.md). Searches see committed data; there is no MVCC snapshot guarantee comparable to a relational DB ([mvcc](../concepts/mvcc.md)).
- **Replication:** None native in open-source Sphinx (2.x). High availability is achieved by indexing the same source into multiple independent nodes and load-balancing/mirroring at the distributed-index layer (agent mirrors). There is no leader election or split-brain protocol. See [replication-models](../concepts/replication-models.md). ⚠️ unverified — the proprietary v3 line's exact replication features are not documented in public open sources.
- **Tunable consistency?** No per-query consistency levels.
- **Clock dependency:** None for correctness. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Index schema (full-text fields + attribute columns) is declared in `sphinx.conf` or via SphinxQL DDL for RT indexes. Documents not matching the declared fields are not indexed coherently.
- **Migration/evolution:** Schema changes to disk indexes generally require a **full re-index** from source (run `indexer`, then hot-swap via `rotate`). RT index schema is fixed at creation; altering field/attribute layout typically means rebuild + reimport. Attribute values on disk indexes can be updated online (`UPDATE`), but full-text content cannot — content updates require re-indexing.
- **Type system:** integers, bigint, floats, booleans, timestamps, strings, multi-value attributes (MVA), and JSON attributes. Geodistance functions available. No native vector/ANN search in the open-source Sphinx line (vector search arrived later in the [Manticore Search](sphinx.md) fork) — see [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** **SphinxQL** — a MySQL-wire-protocol SQL subset (SELECT plus INSERT/REPLACE/DELETE on RT indexes), the recommended interface; **SphinxAPI** — native client libraries (PHP, Python, Ruby, Perl, Java); **SphinxSE** — a pluggable MySQL/MariaDB storage engine that proxies queries to `searchd`. Because it speaks the MySQL protocol, any MySQL client/driver can talk to it.
- **Transactions:** Single-RT-index atomic batch commit (`BEGIN`/`COMMIT`); no multi-statement, multi-index ACID. Disk indexes are not transactional (attribute `UPDATE` is in-place, content is immutable).
- **Native vs app-side:** Full-text matching, ranking (BM25 and weighted/expression rankers), phrase/proximity/boolean operators, faceting, grouping/aggregation (`GROUP BY`, `COUNT`, `SUM`), and `ORDER BY` are native and fast. **No joins** across indexes in the engine — denormalize at index time or join app-side against the source DB.
- **Stored procedures / UDFs:** Supports user-defined functions via C/C++ plugins (compiled `.so`); no general stored-procedure language.

## Scaling & topology
- **Vertical vs horizontal:** Scales vertically per node; horizontally via **manual sharding** into a "distributed index" that fans queries out to local shards and/or remote `searchd` agents and merges results. Resharding = re-plan the index layout and re-index from source (manual, no auto-rebalancing) — see [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas:** Achieved by indexing identical source data into multiple nodes and listing them as agent mirrors; reads from mirrors are as consistent as their last index build/commit (no automatic propagation guarantee).
- **Storage/compute separation:** None — index files are local to each `searchd` node. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) architecture.

## Performance & durability
- **Write path:** RT-index commits land in a RAM chunk; with binary logging enabled, every committed transaction is written to a **binlog** that is replayed after an unclean shutdown to restore state since the last good on-disk flush ([RT binlog docs](http://sphinxsearch.com/docs/current/rt-binlog.html)). The data-loss window is governed by `rt_flush_period` and the binlog fsync mode (`binlog_flush`): the **default is mode 2** — flush every transaction to the OS but `fsync` only once per second — so an OS/host crash can lose up to ~1s of committed transactions, while mode 1 fsyncs every transaction (safest, slowest) and mode 0 flushes+syncs once per second ([RT binlog docs](http://sphinxsearch.com/docs/current/rt-binlog.html)). See [wal-and-durability](../concepts/wal-and-durability.md). Disk indexes built by `indexer` are durable once written and hot-swapped.
- **Throughput/latency:** Historically very fast and memory-efficient for full-text retrieval on a single node; low query latency is its calling card. Specific p99/tail numbers are workload- and version-specific and not benchmarked here.
- **Compaction / vacuum / GC:** RT indexes merge RAM chunks into disk chunks and merge disk chunks over time (LSM-style compaction); `OPTIMIZE INDEX` consolidates disk chunks. Heavy merges can affect tail latency, as with any LSM-style store. Disk indexes need periodic full rebuilds to reclaim space and reflect deletes.

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** No turnkey backup tool. Disk indexes can be re-created from the source DB at any time (the source is the real backup). RT indexes are backed up by copying index files + binlog (with care around flush state). No first-class PITR.
- **Observability:** `SHOW META`, `SHOW STATUS`, query/profiling output, and a query log; `EXPLAIN`-style plans are limited compared to a relational optimizer.
- **Upgrade story:** Index format can change across major versions, sometimes requiring re-index; daemon upgrades are a restart (no rolling-upgrade protocol in OSS). Day-2 burden centers on keeping the index in sync with the source DB (delta indexes + periodic main rebuilds, or RT writes from the app).
- **Maturity:** Mature, battle-tested codebase (2001–) widely deployed in the 2000s–2010s. **Known failure mode: project stagnation.** OSS development stalled around 2016–2017; bug fixes lagged, prompting the May 2017 [Manticore Search](sphinx.md) fork from Sphinx 2.3.2 ([Manticore: 3 years after forking from Sphinx](https://manticoresearch.com/blog/manticore-search-3-years-after-forking-from-sphinx/)). v3.x development resumed in December 2018 but as a **closed-source binary release** (latest reported v3.7.1, March 2024 per [Wikipedia](https://en.wikipedia.org/wiki/Sphinx_(search_engine))). No public Jepsen report exists.

## Ecosystem & people
- **Canonical use cases:** Fast full-text search/autocomplete/faceted search bolted onto a relational app (MySQL/PostgreSQL), log/text retrieval, geo + text filtering — where you want speed and a SQL-like interface and don't need a full document store.
- **Anti-patterns:** Primary system of record (it isn't durable storage in the usual sense — re-indexable from source); workloads needing cross-document joins, rich distributed consistency/replication, JSON document CRUD, or modern vector/semantic search out of the box; teams wanting active upstream development on an open-source license — for those, reach for [Manticore Search](sphinx.md), [elasticsearch](elasticsearch.md), [opensearch](opensearch.md), or [postgresql](postgresql.md) full-text/`pg_trgm`.
- **Drivers/connectors:** Any MySQL driver (via SphinxQL), SphinxAPI clients, SphinxSE for MySQL/MariaDB. Created by Andrew Aksyonoff (Sphinx Technologies Inc.). Community has largely migrated to the Manticore fork; commercial support for Sphinx comes from Sphinx Technologies. Docs are dated and frozen for the OSS line.

## Licensing & cost
- **OSS license & flavor:** Versions 1.x–2.x are **GPLv2** (copyleft), with a separate commercial license available for proprietary embedding ([db-engines / dbdb.io](https://dbdb.io/db/sphinx)). **Version 3+ is not open source** — distributed as proprietary binaries, a relicensing-style shift away from GPL (the most important licensing fact on this page). See [license-taxonomy](../concepts/license-taxonomy.md). The GPLv3 open-source continuation is the [Manticore Search](sphinx.md) fork, not Sphinx itself.
- **Self-managed vs managed-only:** Self-managed only; no first-party managed cloud.
- **Lock-in:** Low — index is rebuildable from your source DB, and the MySQL-protocol interface is portable to the API-compatible Manticore fork.
- **Cost model:** Free (GPLv2) for the OSS 2.x line; commercial licensing/support negotiated for proprietary use and for v3.

## Hardware / deployment
- **Resource profile:** Memory-conscious by design; RT indexes keep a RAM chunk so hot working set benefits from RAM, but full data need not fit in memory. CPU matters for ranking/merging; disk I/O matters for large disk indexes.
- **Storage assumptions:** Local disk per node (NVMe/SSD ideal for merge-heavy RT workloads); not designed for network-attached storage separation.
- **Footprint:** Single daemon (`searchd`) per node; clustered only via manual distributed-index sharding/mirroring. Not embedded, not serverless — see [embedded-databases](../concepts/embedded-databases.md) for the contrast.
- **Deployment:** On-prem / self-hosted; runs on Linux, *BSD, macOS, Solaris, Windows. Container-friendly as a stateless daemon over a mounted index volume, but no native k8s operator.

## Bottom line
Sphinx is a fast, lean, proven full-text engine whose biggest gotcha is its **bifurcated identity**: the open-source line (GPLv2, ≤2.3.x) is effectively frozen, while v3+ is closed-source — so "Sphinx" no longer means a maintained open-source product. New projects wanting this engine's speed and MySQL-protocol ergonomics should almost always choose the actively-developed open-source fork [Manticore Search](sphinx.md) (which added replication, JSON, and vector search), and teams needing rich distributed search should evaluate [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md). Reach for Sphinx itself only to maintain an existing deployment.

## Sources
- [Sphinx (search engine) — Wikipedia](https://en.wikipedia.org/wiki/Sphinx_(search_engine))
- [Database of Databases — Sphinx (dbdb.io)](https://dbdb.io/db/sphinx)
- [Sphinx official docs — RT index & binary logging](http://sphinxsearch.com/docs/current/rt-binlog.html)
- [Sphinx official site / docs](http://sphinxsearch.com/)
- [Manticore Search: 3 years after forking from Sphinx](https://manticoresearch.com/blog/manticore-search-3-years-after-forking-from-sphinx/)
- [Manticore Search vs Sphinx comparison](https://manticoresearch.com/comparison/vs-sphinx/)
