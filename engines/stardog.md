---
name: Stardog
slug: stardog
rank: 123
data_model: RDF / graph (multi-model)
license: Proprietary / closed-source (commercial; free tier available, not OSS)
summary: Enterprise RDF/SPARQL knowledge-graph platform with OWL reasoning, virtual graphs, and an LLM "Voicebox" layer; full-replication HA cluster, not sharded.
last_researched: 2026-06-04
confidence: medium
---

# Stardog

> A proprietary RDF triple/quad store with W3C-standard SPARQL + OWL reasoning, virtual graphs over external sources, and a built-in vector store for LLM-grounded querying — strongly consistent but replicated full-copy, so it scales reads, not data volume.

## Identity
- **Taxonomy / data model:** RDF graph database (triples/quads), addressed via the W3C semantic-web stack. Multi-model in the sense that it can federate relational, document, and other sources as virtual-graphs and includes an embedded vector store, but the core model is RDF, not labeled-property-graph (LPG) like [neo4j](neo4j.md). See [graph-data-model](../concepts/graph-data-model.md) and [graph-data-model](../concepts/graph-data-model.md).
- **Storage model:** "Mastiff" storage engine built on [rocksdb](rocksdb.md), i.e. an LSM-tree, replacing the older B-tree engine; the move to LSM (since Stardog 7.0) improved small-write/batch performance, and Stardog adopted MVCC for snapshot isolation in the same rework ([Mastiff Beta announcement](https://community.stardog.com/t/stardog-7-0-0-mastiff-beta-1/1425)). See [lsm-vs-btree](../concepts/lsm-vs-btree.md).
- **Workload:** Mixed transactional + analytical graph queries. Stardog markets "low latency and high throughput query performance for transactional queries without sacrificing the performance of analytical queries" ([features](https://www.stardog.com/platform/features/high-performance-graph-database/)) — treat the HTAP-ish claim as a single-store-serves-both pitch, not physical OLTP/OLAP separation; there is no separate columnar replica. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** CP — strong consistency is enforced; under a network partition disconnected nodes are expelled and cannot serve reads/writes until they resynchronize ([HA cluster docs](https://docs.stardog.com/high-availability-cluster/)). A write requires acknowledgment from every non-failing node, so loss of quorum stops writes. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PC/EC — consistent under partition (P→C); in normal operation it favors consistency over latency (E→C), since a commit blocks on a cluster-wide commit lock and replication to all live peers.
- **Default isolation & what's achievable:** SNAPSHOT isolation by default; SERIALIZABLE is available via the `transaction.isolation` option. Under SNAPSHOT there are no locks and write-skew is possible (the docs show a counter-increment anomaly); on conflict the transaction with the highest commit timestamp wins. SERIALIZABLE uses an exclusive lock, so effectively one write transaction at a time ([transactions docs](https://docs.stardog.com/operating-stardog/database-administration/transactions)). The "ACID-compliant" marketing claim is accurate but the *default* is snapshot, not serializable — verify your isolation setting. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** Full replication across all cluster nodes (every node holds all data), coordinated by an external apache-zookeeper ensemble (3/5/7 nodes). One node is Coordinator, others Participants; on Coordinator failure a new one is elected. Writes are synchronous to all available nodes before ack. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo-style per-query consistency levels; the system is strongly consistent by design. Isolation is tunable (snapshot/serializable), not consistency-vs-latency.
- **Clock dependency:** SNAPSHOT conflict resolution uses commit timestamps. ⚠️ unverified — whether these are logical or wall-clock and any clock-skew exposure is not documented in sources reviewed; correctness does not appear to rest on synchronized clocks the way [google-cloud-spanner](google-cloud-spanner.md)'s does. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read:** Effectively schema-flexible (schema-on-read). RDF is self-describing; you can load triples without a fixed schema, and OWL/RDFS ontologies + SHACL constraints add optional schema/validation on top.
- **Migration/evolution:** Ontologies and constraints are themselves data (triples), so "schema" evolution is data mutation rather than table-locking DDL. No fixed columnar layout to `ALTER`.
- **Type system:** RDF literals with XSD datatypes (string, numeric, dateTime, etc.), IRIs, language-tagged strings; geospatial support; embedded vector store for embeddings (Stardog 10 / 2024.1) enabling semantic search. See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** SPARQL (W3C), plus SPARQL* (RDF-star), and GraphQL ([features](https://www.stardog.com/platform/features/high-performance-graph-database/)). Natural-language querying via the LLM-backed "Voicebox" layer that translates questions to graph queries ([Voicebox docs](https://docs.stardog.com/voicebox/)).
- **Transactions:** Full multi-statement ACID transactions; nested transactions unsupported ([transactions docs](https://docs.stardog.com/operating-stardog/database-administration/transactions)).
- **Native vs app-side:** Joins, aggregations, and path queries are native SPARQL. OWL 2 reasoning is applied at query time (the "Blackout" reasoner covers OWL 2 profiles; "Stride" beta adds more expressive user-defined rules with negation/aggregation but less OWL coverage) ([inference engine](https://docs.stardog.com/inference-engine/)). Virtual Graphs map external relational/NoSQL/CSV sources to RDF and query them in situ ([virtual graphs](https://docs.stardog.com/virtual-graphs/)).
- **Stored procedures / UDFs:** User-defined rules (Datalog-style, via SWRL/Stardog Rules). ⚠️ unverified — general-purpose stored-procedure support beyond rules and SPARQL extension functions.

## Scaling & topology
- **Vertical vs horizontal:** Primarily vertical for data volume — the cluster is full-replication, not sharded, so total dataset size is bounded by a single node's capacity. Horizontal nodes add read throughput and HA, not capacity ([HA cluster docs](https://docs.stardog.com/high-availability-cluster/)). This is the key scaling limitation versus sharded stores.
- **Sharding:** None (no automatic partitioning of the graph across nodes). See [sharding-partitioning](../concepts/sharding-partitioning.md).
- **Read replicas / read consistency:** Any node can serve reads and returns the globally consistent state; reads are strongly consistent because writes commit everywhere before ack. Larger clusters improve read scaling but degrade write throughput.
- **Storage/compute separation:** ⚠️ unverified — no documented Aurora/Neon-style separation; nodes are stateful with local storage. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Committed writes are durable by default. Optional transaction logging (`transaction.logging`) enables point-in-time recovery; RocksDB provides the underlying [wal-and-durability](../concepts/wal-and-durability.md) WAL. ⚠️ unverified — exact fsync/group-commit policy and the precise data-loss window on crash are not spelled out in sources reviewed.
- **Throughput/latency:** Marketed at ~500K triples/sec bulk load on a "modest server" and thousands of queries/sec on a single node ([features](https://www.stardog.com/platform/features/high-performance-graph-database/)) — vendor figures, treat as best-case. The LSM (Mastiff) engine specifically improved small-batch write latency. ⚠️ unverified — independent p99 tail-latency benchmarks; no public [jepsen](../concepts/jepsen.md) report exists for Stardog.
- **Compaction / GC:** Inherits RocksDB LSM compaction; compaction can affect write-amplification and tail latency under heavy ingest (general LSM behavior — see [lsm-vs-btree](../concepts/lsm-vs-btree.md)).

## Operations & maturity
- **Backup/restore, PITR:** Database backup/restore supported; point-in-time recovery via transaction logging.
- **Observability:** Metrics endpoints, cluster-wide lock/transaction metrics, query plans/profiling for SPARQL.
- **Upgrade story:** ⚠️ unverified — rolling-upgrade specifics; cluster nodes resync from peers via ZooKeeper-tracked last-committed transaction UUIDs when rejoining, which supports node replacement.
- **Maturity:** Commercial product since the early 2010s (Stardog Union, originally from Clark & Parsia); used in regulated/enterprise data-integration settings. No Jepsen analysis published. Known structural limitation: full-replication caps single-graph size and write throughput scales inversely with cluster size.

## Ecosystem & people
- **Canonical use cases:** Enterprise knowledge graphs, data fabric / virtualized data integration across silos, semantic data catalogs, ontology-driven reasoning, and LLM grounding / GraphRAG via the embedded vector store + Voicebox ("Safety RAG" / hallucination-reduction pitch — [Voicebox launch](https://venturebeat.com/ai/stardog-launches-voicebox-an-llm-powered-layer-to-query-enterprise-data)).
- **Anti-patterns:** Not for very-large-scale graphs needing horizontal data sharding (no sharding); not a drop-in for [neo4j](neo4j.md)-style property-graph apps (RDF/SPARQL learning curve); overkill for simple OLTP or a plain document/relational workload; write-heavy multi-node clusters suffer because every write goes to every node.
- **Drivers/connectors:** SPARQL HTTP endpoint, RDF4J/Jena-compatible APIs, JDBC for BI tools, Stardog Studio IDE, virtual-graph connectors to RDBMSs, MongoDB, Elasticsearch, Cassandra, CSV/JSON.
- **Community/support:** Commercial vendor with active community forum and docs; smaller ecosystem than mainstream graph or relational engines; RDF/OWL skill set is specialized and relatively scarce.

## Licensing & cost
- **OSS license & flavor:** Proprietary, **closed-source** commercial product — Stardog explicitly states it "is not open source" ([pricing](https://www.stardog.com/pricing/)). This is *not* "source-available" in the SSPL/BSL/Elastic sense: the engine's source is not published under a restrictive license; only peripheral client libraries/tutorials (e.g., stardog-clj, stardog-examples) are on GitHub under permissive licenses. A free tier ("Stardog Free", renewable 1-year license; "Stardog Cloud" managed starter) exists with limits — Free lacks HA/clustering, caching, backups, LDAP, and full connectors ([pricing](https://www.stardog.com/pricing/)). See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only:** Both — self-hosted (on-prem / AWS Marketplace) and Stardog Cloud managed "Semantic AI platform".
- **Lock-in:** Core data is standards-based RDF/SPARQL (portable), reducing data lock-in; but reasoning config, virtual-graph mappings, and Voicebox/AI features are proprietary.
- **Cost model:** Commercial subscription; public per-node/per-core pricing not disclosed in sources reviewed (enterprise sales). ⚠️ unverified — pricing specifics.

## Hardware / deployment
- **Resource profile:** Memory- and CPU-bound for query/reasoning; reasoning and large SPARQL joins are RAM-hungry. Working set benefits from fitting in RAM; LSM storage tolerates larger-than-RAM data on disk. ⚠️ unverified — exact "must fit in RAM" thresholds.
- **Storage assumptions:** Local fast disk (NVMe preferred) for the RocksDB store; LSM design is friendlier to commodity SSDs than spinning disk.
- **Footprint:** Single-node server or full-replication HA cluster + separate ZooKeeper ensemble; not embedded, not serverless. Cloud-managed option available.
- **Deployment:** SaaS (Stardog Cloud) or on-prem / cloud VMs / AWS Marketplace; containerizable. StatefulSet-style deployment with persistent local storage plus a ZooKeeper quorum.

## Bottom line
Reach for Stardog when the problem is **enterprise data integration and reasoning** — heterogeneous silos unified as a standards-based RDF knowledge graph, OWL/rules inference, virtual graphs that query sources in place, and increasingly LLM grounding via its vector store and Voicebox. Do not reach for it if you need to shard a massive graph horizontally, want a property-graph/Cypher model, or run a write-heavy workload across many nodes. The single biggest gotcha: the cluster is **full-replication, not sharded** — it gives you HA and read scaling but caps dataset size to one node and makes writes *slower* as you add nodes; and the default isolation is **snapshot, not serializable**, so write-skew is possible unless you opt into SERIALIZABLE.

## Sources
- [Stardog HA Cluster documentation](https://docs.stardog.com/high-availability-cluster/)
- [Stardog Transactions documentation](https://docs.stardog.com/operating-stardog/database-administration/transactions)
- [Stardog Inference Engine documentation](https://docs.stardog.com/inference-engine/)
- [Stardog Virtual Graphs documentation](https://docs.stardog.com/virtual-graphs/)
- [Stardog Voicebox documentation](https://docs.stardog.com/voicebox/)
- [Stardog 7.0.0 Mastiff (RocksDB/LSM + MVCC) Beta announcement](https://community.stardog.com/t/stardog-7-0-0-mastiff-beta-1/1425)
- [High-performance graph database (features)](https://www.stardog.com/platform/features/high-performance-graph-database/)
- [Stardog pricing](https://www.stardog.com/pricing/)
- [VentureBeat: Stardog launches Voicebox](https://venturebeat.com/ai/stardog-launches-voicebox-an-llm-powered-layer-to-query-enterprise-data)
