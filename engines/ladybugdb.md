---
name: LadybugDB
slug: ladybugdb
adjacent: true
rank: n/a
category: graph
data_model: Graph (embedded property graph)
license: MIT (permissive)
summary: Embedded "SQLite/DuckDB for graphs" — an MIT-licensed, in-process columnar property-graph engine speaking Cypher, the community fork of Kuzu after Apple acqui-hired the team and archived it (Oct 2025).
last_researched: 2026-06-04
confidence: medium
---

# LadybugDB

> An embedded, in-process **columnar property-graph** database that speaks Cypher — the "SQLite/DuckDB for graphs": no server, ships inside your app/agent/notebook, with vectorized query processing and no-copy attach to SQLite/DuckDB/Parquet/Arrow. It is the **community fork of [Kuzu](https://github.com/kuzudb/kuzu)** continued after Apple acqui-hired the Kuzu team and the original repo was archived on 2025-10-10.

## When to use

**Use LadybugDB if:**
- ✅ You want an **embedded, zero-ops graph** store inside your app/agent/notebook (on-device, edge, serverless) — the [embedded](../concepts/embedded-databases.md) "SQLite/DuckDB for graphs" niche — rather than running a server like [neo4j](neo4j.md)/[memgraph](memgraph.md).
- ✅ Your graph work is **analytical** (multi-hop traversals, joins, pattern-matching) and benefits from **columnar storage + vectorized/factorized execution**, queried in **Cypher**.
- ✅ You want to **join a graph against existing tabular data** with **no-copy attach** to SQLite/DuckDB/Parquet/Arrow — useful for GraphRAG / AI-agent memory that travels with the process.

**Avoid LadybugDB if:**
- ❌ You need a **networked multi-writer server with HA, failover, or horizontal sharding** — this is a single-node embedded library, not a cluster (use [neo4j](neo4j.md)/[memgraph](memgraph.md) or a distributed graph engine).
- ❌ You need a **mature, battle-tested system** — it is a **2025 fork**, small/young community, with **no Jepsen report** and a short production track record.
- ❌ You need a **high-write transactional OLTP system of record** — it is analytical and **single-writer** embedded; this is the biggest gotcha.

## Identity
- **Taxonomy / data model:** embedded **property graph** ([graph-data-model](../concepts/graph-data-model.md)) — typed **node and relationship tables** (a *structured* property graph, schema-on-write). LadybugDB adds **multiple labels per node** (`:Person:Employee`), removing Kuzu's one-label-per-node constraint.
- **Storage model:** **columnar**, disk-based, with **CSR (columnar-sparse-row) adjacency lists** for graph joins and a **single-file** database format (inherited from Kuzu v0.11.0+). Not a B-tree/[LSM](../concepts/lsm-vs-btree.md) row store. See [columnar-storage](../concepts/columnar-storage.md). Query engine uses **vectorized and factorized processing** (compresses intermediate results instead of materializing every row).
- **Workload:** analytical graph queries — multi-hop traversal/join/pattern-match — leaning [OLAP-ish](../concepts/oltp-olap-htap.md), not OLTP. Not HTAP.

## Distribution & consistency
- **CAP under partition:** N/A — single-process / embedded; no distributed cluster. Durability rests on the local filesystem/object store, not a quorum protocol. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** N/A — single-node embedded.
- **Default isolation & what's achievable:** ⚠️ unverified for the fork — inherited from Kuzu, which provided **ACID transactions with serializable isolation** and **single-writer / multiple-reader** concurrency. Confirm against LadybugDB's own docs before relying on it. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** None built in — embedded; HA/replication would be bolted on externally (copy/ship the file). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No — single embedded writer; no per-query consistency knobs.
- **Clock dependency:** No dependency on synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, structured.** You declare typed **node tables** and **relationship tables** (with typed properties) before loading; this is closer to a relational schema than to a schemaless graph.
- **Migration / evolution:** DDL is via Cypher (`CREATE`/`ALTER`/`DROP` node & rel tables). ⚠️ unverified — online-DDL/locking semantics not confirmed for the fork.
- **Type system:** typed scalar properties plus lists/structs, **vector** columns (vector index extension) and **full-text** indices ([full-text-search](../concepts/full-text-search.md), [vector-search-ann](../concepts/vector-search-ann.md)).

## Query interface
- **Language:** **Cypher** (openCypher dialect). Not a SQL engine — graph-first.
- **Transactions:** `BEGIN`/`COMMIT`/`ROLLBACK` with ACID semantics ⚠️ unverified for the fork (inherited from Kuzu).
- **Native vs app-side:** native graph **traversals, joins, pattern matching**, plus **vector search** and **full-text** via built-in indices/extensions. **No-copy scan/attach** of external SQLite/DuckDB/Parquet/Arrow datasets lets you query/join graph + tabular data together.
- **Stored procedures / UDFs:** ⚠️ unverified — Kuzu supported some built-in functions; custom UDF surface for the fork not confirmed here.

## Scaling & topology
- **Vertical only.** Single-node embedded; bounded by the host's CPU/memory/disk. "Bigger box" is the scaling story.
- **Sharding / partitioning:** none — single-file database.
- **Read replicas / read consistency:** none native; multiple processes can open the same file (read fan-out) subject to the single-writer model.
- **Storage/compute separation:** N/A in the embedded core; the **no-copy external-data attach** (Arrow/DuckDB/Parquet) is the interop equivalent, letting compute read data it doesn't own. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** ⚠️ unverified — Kuzu used a WAL; durability is the local filesystem's once a commit lands. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** in-process (no network/IPC round-trip); **vectorized + factorized columnar execution** targets fast analytical traversals. Vendor positioning claims "**~10x faster queries**" than Kuzu via columnar optimization (first-party number — verify on your workload).
- **Compaction / GC:** ⚠️ unverified for the fork.

## Operations & maturity
- **Backup/restore:** copy the single-file database (self-contained, portable); no documented native PITR/WAL-replay confirmed here.
- **Observability:** library-level (logs, Cypher `EXPLAIN`/profile via the query engine). ⚠️ unverified — no SQL-grade slow-query/metrics suite confirmed.
- **Upgrade story:** library version bumps (pip/cargo/npm); single-binary install via `curl`/Homebrew with zero external dependencies.
- **Maturity:** **very young** — forked in 2025 after Apple acqui-hired the Kuzu team and the upstream repo was archived (2025-10-10). It inherits Kuzu's real engineering base (CSR storage, vectorized engine, vector/FTS indices) but has a short independent track record, a small (if active) community, and **no Jepsen report**.

## Ecosystem & people
- **Canonical use cases:** **AI-agent memory / GraphRAG** that travels with the process; on-device/edge knowledge graphs; embedded graph analytics; graph queries joined to local tabular data. **Marketed for highly regulated industries** wanting embedded (no-server) graph. **Anti-patterns:** networked multi-writer server; OLTP system of record; very large distributed graphs needing horizontal scale.
- **Drivers / connectors:** **Python, Node.js, Rust** SDKs; attach/scan **SQLite, DuckDB, Parquet, Arrow** (and Postgres/Iceberg/Delta in the Kuzu lineage). Pairs with LangChain/LlamaIndex-style agent stacks.
- **Community size, support, docs:** nascent fork community succeeding Kuzu; docs at [docs.ladybugdb.com](https://docs.ladybugdb.com/). Low learning curve for anyone who knows Cypher; production depth (durability, concurrency, day-2 ops) is where to verify carefully given its youth.

## Licensing & cost
- **OSS license:** **MIT** (permissive), positioned as "forever open source" — no copyleft, no source-available relicensing. See [license-taxonomy](../concepts/license-taxonomy.md). Open single-file format and standard Cypher keep lock-in low.
- **Self-managed vs managed:** self-host the embedded library (free; you pay only the infra you run it on). No managed cloud service documented here.
- **Cost model:** free library; "cost" is the host hardware.

## Hardware / deployment
- **Resource profile:** **disk-first columnar**, memory-mapped/vectorized access; benefits from cores + RAM for big traversals but does not require the whole graph in RAM (contrast with in-memory [memgraph](memgraph.md)).
- **Storage assumptions:** local NVMe/SSD ideal for the single-file database; ⚠️ unverified — behavior over network/shared filesystems not confirmed.
- **Footprint:** **embedded library** (in-process, no daemon) — see [embedded-databases](../concepts/embedded-databases.md); ships inside binaries, containers, notebooks, serverless functions; single-binary install, zero external deps.
- **Deployment:** self-hosted embedded anywhere (edge/embedded/cloud); not a StatefulSet/server.

## Bottom line
Reach for LadybugDB when you want an **embedded, MIT-licensed graph database** with no server — Cypher, columnar+vectorized for analytical traversals, ideal for **AI-agent memory/GraphRAG** and on-device knowledge graphs, and able to join graph data with local SQLite/DuckDB/Parquet/Arrow via no-copy attach. It is the **"SQLite/DuckDB for graphs,"** the local counterpoint to server engines like [neo4j](neo4j.md)/[memgraph](memgraph.md). Don't use it as a multi-writer networked server, an OLTP system of record, or for very large distributed graphs. The single biggest gotcha: it is a **2025 community fork of Kuzu** (archived after Apple's acqui-hire) — single-writer, single-node, **no Jepsen**, and a short track record, so verify durability/transaction guarantees against its own docs before betting production data on it.

## Sources
- [LadybugDB website (embedded columnar graph, MIT, use cases)](https://ladybugdb.com/)
- [LadybugDB GitHub](https://github.com/LadybugDB/ladybug) · [docs](https://docs.ladybugdb.com/)
- [dbdb.io — LadybugDB (C++, MIT, embedded, Cypher, 2025 fork of Kuzu)](https://dbdb.io/db/ladybugdb)
- [Kuzu's legacy and the new wave of embedded graph databases (gdotv) — CSR storage, vectorized/factorized execution, multiple-labels, no-copy attach, Apple acqui-hire + Oct 2025 archival](https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/)
- [Kuzu (archived upstream)](https://github.com/kuzudb/kuzu)
