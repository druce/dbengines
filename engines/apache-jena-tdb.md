---
name: Apache Jena - TDB
slug: apache-jena-tdb
rank: 107
data_model: RDF triplestore
license: Apache License 2.0 (permissive)
summary: Embedded single-node RDF/SPARQL triplestore for the Java/Jena ecosystem; serializable transactions, no clustering.
last_researched: 2026-06-04
confidence: high
---

# Apache Jena - TDB

> A native, embedded, single-machine RDF triplestore for Java — the persistent storage layer under the Jena/Fuseki SPARQL stack, with serializable single-writer transactions but no built-in clustering or replication.

## When to use

**Use Apache Jena - TDB if:**
- ✅ You need a free, standards-compliant single-machine RDF/SPARQL triplestore embedded in a Java app or behind Fuseki
- ✅ You want genuine serializable ACID transactions (single-writer MRSW, consistent reader snapshots)
- ✅ You're building knowledge graphs, RDF/linked-data publishing, or ontology-backed apps needing SPARQL + OWL/RDFS reasoning
- ✅ Your dataset fits on one node and you can scale by adding RAM/faster disk

**Avoid Apache Jena - TDB if:**
- ❌ More than one JVM may touch the same files — concurrent multi-JVM access is unsupported and risks data corruption (biggest gotcha)
- ❌ Your graph outgrows one server — there is no sharding, replication, or built-in HA
- ❌ You have high-concurrency write workloads — there is exactly one writer at a time
- ❌ You run TDB2 with long-lived read transactions and skip periodic compaction — dead blocks accumulate and disk bloats

## Identity
- **Taxonomy / data model:** RDF triplestore / quad store (named graphs). Data is RDF terms organized as triples (S,P,O) or quads (G,S,P,O); queried with SPARQL. See [graph-data-model](../concepts/graph-data-model.md), [graph-data-model](../concepts/graph-data-model.md).
- **Storage model:** Row-equivalent triple store. A **node table** dictionary-encodes every RDF term to an 8-byte NodeId (B+Tree-backed, heavily cached); triples/quads are stored in multiple covering **B+Tree indexes** (SPO/POS/OSP permutations for triples, more for quads), so each index alone answers a pattern with no secondary lookup ([architecture](https://jena.apache.org/documentation/tdb/architecture.html)). Custom B+Tree implementation, memory-mapped files on 64-bit JVMs. Some XSD types (integers, decimals, dates, booleans, floats) are inlined directly into the NodeId. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM — it is B+Tree-based; TDB2 adds copy-on-write.
- **Workload:** OLTP-ish graph reads/writes plus SPARQL analytical queries on a single node — effectively OLTP-on-RDF, not OLAP at scale. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** N/A — single-node embedded store. No partitioning model exists; for multi-client access you front it with the Fuseki HTTP server (still a single backing store).
- **PACELC:** N/A — single node. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** **Serializable** — the docs call it "the highest isolation level" ([TDB transactions](https://jena.apache.org/documentation/tdb/tdb_transactions.html)). Achieved trivially because there is at most one writer at a time (MRSW), so write-write conflicts cannot occur; readers see a consistent snapshot. This is genuine ACID, not "ACID-meaning-snapshot." See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** None built in. No leader/follower, no quorum. See [replication-models](../concepts/replication-models.md). Multi-JVM access to the same files on disk is **explicitly unsupported and "high risk of data corruption"** — Jena auto-detects and blocks concurrent JVMs ([TDB transactions](https://jena.apache.org/documentation/tdb/tdb_transactions.html)). Replication/HA must be built externally (e.g., RDF Delta change-streaming for Fuseki).
- **Tunable consistency?** No — always serializable.
- **Clock dependency:** None. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** RDF is schemaless at the store level; "schema" lives in RDFS/OWL vocabularies and optional reasoners, not enforced storage constraints.
- **Migration/evolution:** No fixed table schema, so no `ALTER`/online-DDL concept. You add/remove triples. Note: **TDB2 on-disk format is not compatible with TDB1** ([TDB2](https://jena.apache.org/documentation/tdb2/)) — moving between them is an export/reload migration.
- **Type system:** Full RDF/XSD typed literals (integers, decimals, dates, dateTime, doubles, booleans, strings with language tags), IRIs, blank nodes. TDB2 preserves numeric datatypes/`xsd:double` more faithfully than TDB1. No native vector/geospatial indexing in the core store (GeoSPARQL via add-on modules).

## Query interface
- **Language:** **SPARQL 1.1** (Query, Update, Graph Store Protocol) via the Jena ARQ engine; also the Jena Java Model/Graph API for programmatic access. Served over HTTP by apache-jena-fuseki.
- **Transactions:** Full multi-statement ACID transactions; **TDB2 is transactional-only (no autocommit)**, TDB1 allowed non-transactional use (discouraged). Update transactions in TDB2 can be arbitrarily large; TDB1 transactions were capped at "a few tens of millions of triples" because changes were held in memory until indexes updated ([TDB2](https://jena.apache.org/documentation/tdb2/)).
- **Native vs app-side:** Joins, aggregations, property paths, subqueries, named-graph queries are all native to SPARQL/ARQ. Statistics-based BGP (basic graph pattern) optimizer with quad-rewriting.
- **Stored procedures / UDFs:** No stored procedures. Custom SPARQL functions and property functions can be registered in Java; reasoning via Jena's rule engine / RDFS / OWL reasoners (app-side, computed over the store).

## Scaling & topology
- **Vertical, not horizontal.** Scales by giving one machine more RAM (for mmap'd index caching) and faster disk. **No sharding, no resharding** — a dataset must fit on one node.
- **Read replicas:** None natively. You can run read-only Fuseki copies fed by external change replication, but TDB itself has no replica concept.
- **Storage/compute separation:** No — local files, mmap'd by the JVM. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** TDB1 uses **write-ahead journaling** ([wal-and-durability](../concepts/wal-and-durability.md)) — changes go to a journal then flush to the main indexes at a checkpoint. TDB2 uses **copy-on-write [mvcc](../concepts/mvcc.md)**: a writer writes new copies of modified B+Tree blocks; commit makes the new root visible; old blocks linger until no reader references them. Crash recovery replays/rolls back to the last committed state. Data-loss window: committed transactions are durable to disk; ⚠️ unverified — exact fsync grouping/commit-flush semantics and whether a crash mid-flush can lose a just-acked commit are not spelled out in the public docs.
- **Throughput/latency:** Strong single-node query performance with mmap'd indexes warm; throughput is bounded by the **single-writer** constraint — concurrent writers serialize, so write-heavy multi-client workloads bottleneck. Reads scale with cores. ⚠️ unverified — no authoritative published p99 tail-latency numbers.
- **Compaction / GC:** TDB2's copy-on-write means dead blocks accumulate; space is reclaimed by an **offline/online `compact`** operation (Fuseki has a compact endpoint). Long-running read transactions pin old blocks and delay reclamation — the main day-2 space gotcha. TDB1 has no compaction but can fragment.

## Operations & maturity
- **Backup/restore:** Dump to RDF (N-Quads/TriG) via `tdb2.tdbdump` / Fuseki backup; restore by reload. File-level copy is safe only when no JVM is attached. No native PITR.
- **Observability:** Fuseki exposes metrics (Prometheus), query logging, and SPARQL `EXPLAIN`-style ARQ query-plan logging is available via Java/logging config. Slow-query visibility is log-based.
- **Upgrade story:** Library/jar upgrade within a major line is usually drop-in; **TDB1 → TDB2 requires a dump-and-reload** (incompatible format). No rolling-upgrade clustering since there is no cluster.
- **Maturity:** Mature, long-lived Apache top-level project; widely used in semantic-web, knowledge-graph, library/cultural-heritage, and life-sciences settings. **No Jepsen report exists** (single-node, so distributed-consistency testing does not apply). Known failure modes: data corruption from multi-JVM access to the same files; disk bloat from un-compacted TDB2 with long readers.

## Ecosystem & people
- **Canonical use cases:** Embedded or single-server knowledge graphs, RDF/linked-data publishing, ontology-backed apps needing SPARQL + OWL/RDFS reasoning, reference triplestore behind apache-jena-fuseki. **Anti-patterns:** datasets bigger than one machine; high-concurrency write workloads (single writer); applications needing HA/replication/sharding out of the box; teams not on the JVM; pure-OLAP analytics over billions of triples where a clustered/columnar store fits better.
- **Drivers / connectors:** Java-first (Jena API); any HTTP/SPARQL client via Fuseki; RDF4J and rdflib can talk to its SPARQL endpoint; RDF Delta for change replication. No first-class CDC/Kafka/dbt integration.
- **Community:** Active ASF community, mailing lists, good reference docs (though some pages are terse). Learning curve = SPARQL + RDF modeling + Jena Java API. Small ops footprint; typically run by one or two engineers.

## Licensing & cost
- **License:** **Apache License 2.0** — permissive, no post-2018 relicensing concerns. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** Self-managed/embedded only; no official managed cloud service. No lock-in beyond the RDF/SPARQL standards (data is portable RDF).
- **Cost model:** Free software; cost is the single server's RAM/disk/CPU. Scales cheaply small; the ceiling is one machine, so it does not get cheaper-per-triple by adding nodes (you cannot add nodes).

## Hardware / deployment
- **Resource profile:** Memory-sensitive — performance leans heavily on OS page cache for mmap'd B+Tree indexes, so more RAM relative to dataset size = better. Working set need not fully fit in RAM, but hot indexes should. **64-bit JVM required for the mmap path**; 32-bit JVMs fall back to a small in-heap block cache and are address-space limited (~1.5 GB).
- **Storage assumptions:** Local disk; NVMe/SSD strongly preferred for cold reads and compaction. Not designed for network-attached/EBS-latency storage.
- **Footprint:** Embedded library in a JVM process, or single-node server via Fuseki. No clustered mode.
- **Deployment:** On-prem or single container; Fuseki ships as a Docker image and runs fine as a single k8s Deployment/StatefulSet with a persistent volume — but it is single-instance, not a distributed StatefulSet.

## Bottom line
Reach for TDB/TDB2 when you need a free, standards-compliant, single-machine RDF triplestore with real serializable ACID transactions inside a Java app or behind Fuseki — it is the default open-source SPARQL store. Do not reach for it if your graph outgrows one server, if you need write concurrency, or if you need built-in HA/replication/sharding. The single biggest gotcha: **only one JVM may touch the files** (concurrent access risks corruption) and TDB2 needs periodic **compaction** or it bloats — plus there is exactly one writer at a time.

## Sources
- [Apache Jena - TDB Transactions](https://jena.apache.org/documentation/tdb/tdb_transactions.html)
- [Apache Jena - TDB Architecture](https://jena.apache.org/documentation/tdb/architecture.html)
- [Apache Jena - TDB2](https://jena.apache.org/documentation/tdb2/)
- [Apache Jena - TDB index](https://jena.apache.org/documentation/tdb/)
- [Apache Jena - Fuseki](https://jena.apache.org/documentation/fuseki2/)
- [Apache Jena - Jena Transactions](https://jena.apache.org/documentation/txn/)
- [Apache Jena - Home (license Apache-2.0)](https://jena.apache.org/)
