---
name: GraphDB
slug: graphdb
rank: 105
data_model: RDF triplestore / graph
license: Proprietary commercial (EE per-core); GraphDB Free is free-to-use but closed-source and license-gated
summary: Ontotext's RDF/SPARQL triplestore whose differentiator is materialized OWL/RDFS reasoning at write time, with a Raft-based HA cluster for the Enterprise edition.
last_researched: 2026-06-04
confidence: high
---

# GraphDB

> A standards-compliant RDF triplestore (RDF4J + W3C SPARQL) built around forward-chaining OWL/RDFS inference materialized at load time; reach for it when semantics, reasoning, and linked-data interchange matter more than raw graph-traversal throughput.

## Identity
- **Taxonomy / data model:** RDF triplestore — the [graph-data-model](../concepts/graph-data-model.md) expressed as subject-predicate-object triples (quads with named graphs), queried in SPARQL. Property-graph engines like [neo4j](neo4j.md) are a different graph model; GraphDB is the W3C semantic-web/linked-data lineage.
- **Storage model:** disk-based, B-tree-style sorted indexes over triples — primarily the PSO (predicate-subject-object) and POS (predicate-object-subject) indexes, plus optional additional indexes (e.g. context/predicate-list) for specific access patterns ([storage docs](https://graphdb.ontotext.com/documentation/10.8/storage.html)). Not an [lsm-vs-btree](../concepts/lsm-vs-btree.md) LSM engine; closer to sorted-index/B-tree on disk. Inferred triples are materialized and stored alongside asserted ones.
- **Workload:** OLTP-ish read-heavy graph/semantic queries with bulk loads; not an analytical [columnar-storage](../concepts/columnar-storage.md) engine and not high-write-throughput. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Its signature is real-time inference at scale rather than HTAP — no HTAP claim to flag.

## Distribution & consistency
- **Topology:** single-node in GraphDB Free; HA clustering only in the Enterprise Edition (EE).
- **CAP under partition:** CP for writes. The EE cluster uses the [Raft](../concepts/consensus-raft-paxos.md) consensus algorithm; an update is committed only when a **majority quorum** of instances commits it locally, so a minority partition cannot accept writes ([cluster docs](https://graphdb.ontotext.com/documentation/11.2/cluster-basics.html)). If 50% or more of nodes are down the cluster refuses INSERT/DELETE. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under Partition → favors Consistency (no writes without quorum). Else → tunable: read consistency mode `none` (default) routes reads to any reachable node (Availability/Latency, possibly stale) while `last_committed` forces reads against a node at the latest committed transaction (Consistency) ([cluster docs](https://graphdb.ontotext.com/documentation/11.2/cluster-basics.html)). So roughly **PC/EL by default, PC/EC** when `last_committed` is set.
- **Isolation:** **read committed**, exposed via RDF4J's `RepositoryConnection`. Pending updates are invisible to others until the whole transaction commits; GraphDB explicitly does **not** guarantee a single transaction executes against one consistent snapshot — i.e. no snapshot isolation / not MVCC-style repeatable reads ([transactions docs](https://graphdb.ontotext.com/documentation/10.8/storage.html)). This is weaker than [mvcc](../concepts/mvcc.md) snapshot engines; see [isolation-levels](../concepts/isolation-levels.md). ⚠️ unverified — exact behavior of concurrent writers (single-writer serialization vs. row-level locking) at the storage layer.
- **Replication:** single-leader via Raft — leader accepts log entries and replicates to followers; automatic leader election and failover. Writes are synchronous to a majority. Quorum requirement prevents split-brain. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** yes, but coarse — only the two read modes above (`none` / `last_committed`); not Dynamo-style per-query R/W quorum levels.
- **Clock dependency:** none for correctness — Raft term/log ordering, not wall-clock timestamps. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read in the RDF sense:** triples can be inserted freely; "schema" is RDFS/OWL ontologies that drive inference rather than a rigid table schema. You can run schemaless or with strict ontology validation via SHACL.
- **Validation / evolution:** SHACL shapes for constraint validation; ontologies and rulesets can evolve, but changing a ruleset generally requires re-inference (recomputing materialized triples), which on large stores is expensive. No "ALTER TABLE locks" concept — but reloading/re-reasoning is the migration cost.
- **Type system:** RDF/XSD datatypes (string, numeric, dateTime, etc.), language-tagged literals, IRIs; geospatial (GeoSPARQL) support; full-text via Lucene/Solr/Elasticsearch connectors; vector/[semantic similarity](../concepts/vector-search-ann.md) via the similarity plugin and (11.2+) vector search in the Elasticsearch/OpenSearch connectors ([release notes](https://graphdb.ontotext.com/documentation/11.2/release-notes.html)).

## Query interface
- **Language:** SPARQL 1.1 (query + update), W3C SPARQL Protocol, and the RDF4J API; all standard RDF serializations (Turtle, RDF/XML, N-Triples, JSON-LD, etc.). This standards compliance is a genuine selling point — portable across RDF4J-compatible stores.
- **Transactions:** multi-statement transactions through RDF4J connections at read-committed isolation (see above). Not full serializable ACID.
- **Native vs app-side:** joins, aggregations, property paths, federation (SPARQL `SERVICE`), and subqueries are all native to SPARQL. **Reasoning is native and materialized** — OWL-Horst/RDFS/OWL2-RL-style rulesets are forward-chained at write time so inferred facts are queryable without runtime reasoning.
- **Stored procedures / UDFs:** JavaScript-based custom functions and a plugin API (Java); connectors (Lucene/Solr/ES/Kafka/ChatGPT) extend functionality. No conventional SQL stored procedures.

## Scaling & topology
- **Vertical first:** a single node scales to billions of statements via file-based indexes; throughput is largely memory- and disk-bound.
- **Horizontal:** the EE cluster is **replication for HA and read scaling, not sharding** — every node holds a full copy; there is no automatic partitioning of the triple set across nodes. So write throughput does not scale out, and dataset size is bounded by a single node's capacity. ⚠️ unverified — any first-party horizontal-sharding/federation-for-scale option beyond SPARQL federation across separate repositories.
- **Read replicas:** followers serve reads; consistency of those reads governed by the `none`/`last_committed` mode.
- **Storage/compute separation:** none — classic shared-nothing replicas with local storage. Not a [storage-compute-separation](../concepts/storage-compute-separation.md) architecture.

## Performance & durability
- **Write path:** transactional with a transaction log; in the cluster a write is acknowledged after majority local commit. See [wal-and-durability](../concepts/wal-and-durability.md). ⚠️ unverified — exact fsync/group-commit policy and the precise single-node crash data-loss window.
- **Throughput/latency:** strong on complex read/inference queries over large graphs; bulk loading is the throughput-sensitive path (loading + materializing inference). Inference materialization shifts cost to write time, making reasoning-heavy reads fast but writes and re-inference slower. ⚠️ unverified — published p99 tail-latency figures; vendor benchmarks (e.g. LDBC SPB) exist but are vendor-run, treat with caution.
- **Compaction / GC:** standard JVM heap management (GraphDB is a Java/JVM engine) — GC pauses can affect tail latency on large heaps. No LSM-style compaction. Deleting asserted triples can trigger retraction of dependent inferred triples, which is non-trivial work.

## Operations & maturity
- **Backup/restore:** online and offline backup, repository export/import (RDF dumps); cluster backup tooling in EE. ⚠️ unverified — granular point-in-time-recovery support comparable to RDBMS PITR.
- **Observability:** SPARQL `EXPLAIN`-style query plans / query monitoring in the Workbench UI, JMX/Prometheus metrics, slow-query and abort controls.
- **Upgrade story:** rolling upgrades supported within the EE cluster; major-version jumps may require re-indexing/re-inference. Day-2 burden centers on managing inference/ruleset changes and JVM heap sizing.
- **Maturity:** mature commercial product (Ontotext, since the OWLIM days ~2008), used in publishing, pharma/life sciences, finance, and government knowledge graphs. **No public Jepsen report exists** for GraphDB — its Raft cluster's consistency claims are vendor-stated and have not, to my knowledge, been independently formally verified. ⚠️ unverified — independent verification of cluster consistency under partition/failure.

## Ecosystem & people
- **Canonical use cases:** enterprise knowledge graphs, linked-data publishing, data integration over heterogeneous sources, ontology-driven inference, metadata management, and GraphRAG retrieval feeding LLMs (similarity plugin / ChatGPT connector).
- **Anti-patterns:** high write-throughput OLTP; sharded web-scale workloads needing horizontal write scaling; pure property-graph traversal apps (a property-graph engine like [neo4j](neo4j.md) or [memgraph](memgraph.md) is often a better fit); analytical column-scan workloads; teams without RDF/SPARQL/semantic-web expertise (steep learning curve).
- **Connectors/tooling:** RDF4J ecosystem, Lucene/Solr/Elasticsearch/OpenSearch, Kafka connector (EE), ChatGPT retrieval connector, GraphDB Workbench UI, SHACL validation. Integrates with semantic-web tooling broadly; less first-class dbt/BI integration than SQL engines.
- **Community/support:** commercial support from Ontotext; sizable semantic-web community; docs are detailed and versioned. Learning curve is real — RDF, SPARQL, and OWL reasoning are specialist skills.

## Licensing & cost
- **License:** **proprietary/closed-source.** GraphDB Free is free-to-use but is *not* open source and, since v11.0.0, **every edition (including Free) requires a license file** ([licensing docs](https://graphdb.ontotext.com/documentation/11.2/licensing.html)). Free ships a single-core license. Standard Edition (SE) is discontinued (still supported). Enterprise Edition (EE) is licensed **per server CPU core**, per machine — in a cluster each node is licensed separately. See [license-taxonomy](../concepts/license-taxonomy.md). Note this is the engine ranked at #105; not to be confused with property-graph products that share the generic name "graph database."
- **Self-managed vs managed:** primarily self-managed on-prem; available via Ontotext Cloud / cloud marketplaces. ⚠️ unverified — current fully-managed SaaS pricing details.
- **Lock-in:** low at the *data/query* layer (RDF + SPARQL are standards, exportable to any RDF4J store); higher at the *operational* layer (clustering, connectors, plugins, and inference rulesets are GraphDB-specific).
- **Cost model:** per-core EE licensing — cost scales with cores across all cluster nodes, which can get expensive for large HA deployments since replicas (not shards) each carry a full license.

## Hardware / deployment
- **Resource profile:** JVM, memory- and disk-bound. Indexes and inference benefit heavily from RAM; the working set ideally fits in memory/page cache for good query latency, though file-based indexes allow datasets larger than RAM.
- **Storage assumptions:** local disk; NVMe/SSD strongly preferred for index-heavy random access. Not designed for high-latency network-attached storage.
- **Footprint:** single-node (Free/SE) or clustered replicas (EE); not embedded, not serverless.
- **Deployment:** on-prem, Docker, and Kubernetes (Helm charts exist); StatefulSet-style deployment for the EE cluster with persistent volumes per node and odd node counts (3 or 5) across zones for quorum.

## Bottom line
Choose GraphDB when you need a standards-compliant RDF/SPARQL triplestore with real, materialized OWL/RDFS inference — enterprise knowledge graphs, linked-data publishing, and GraphRAG over ontology-modeled data. Do not choose it for write-heavy OLTP, horizontally sharded web-scale data (the cluster replicates, it does not shard), or property-graph traversal apps better served by [neo4j](neo4j.md). The biggest gotcha: isolation is **read committed, not snapshot/serializable**, the product is **proprietary and now license-gated even for the Free tier**, and the Raft cluster's consistency guarantees are **vendor-stated with no independent Jepsen verification**.

## Sources
- [What is GraphDB? — official docs 11.2](https://graphdb.ontotext.com/documentation/11.2/)
- [Overview of clusters — Raft, quorum, read consistency modes](https://graphdb.ontotext.com/documentation/11.2/cluster-basics.html)
- [Data storage — PSO/POS indexes, read-committed transactions](https://graphdb.ontotext.com/documentation/10.8/storage.html)
- [Licensing — editions, per-core EE, license required since 11.0](https://graphdb.ontotext.com/documentation/11.2/licensing.html)
- [Release notes 11.2 — vector search in ES/OpenSearch connectors](https://graphdb.ontotext.com/documentation/11.2/release-notes.html)
- [Ontotext GraphDB product page](https://www.ontotext.com/products/graphdb/)
