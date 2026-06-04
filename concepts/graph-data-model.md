---
name: Graph Data Model
slug: graph-data-model
summary: Model data as nodes and edges so relationships are first-class — fast multi-hop traversals that would be expensive recursive joins in a relational store. Property-graph vs RDF.
last_researched: 2026-06-04
---

# Graph Data Model

> A graph database stores **nodes** (entities) and **edges** (relationships), both optionally
> carrying properties. The point is **relationship traversal**: following connections is a cheap
> pointer-hop instead of a repeated relational join, so multi-hop queries (friends-of-friends,
> fraud rings, lineage) stay fast as depth grows.

## Two model families
- **Property graph (LPG)** — nodes/edges with labels and key-value properties. Queried with
  **Cypher** ([neo4j](../engines/neo4j.md)), **Gremlin** (Apache TinkerPop), or the new ISO **GQL** standard. Engines:
  [neo4j](../engines/neo4j.md), [memgraph](../engines/memgraph.md), [tigergraph](../engines/tigergraph.md), [nebulagraph](../engines/nebulagraph.md), [janusgraph](../engines/janusgraph.md), [arangodb](../engines/arangodb.md),
  [orientdb](../engines/orientdb.md), [amazon-neptune](../engines/amazon-neptune.md).
- **RDF triplestore** — data as `(subject, predicate, object)` triples; a W3C standard model queried
  with **SPARQL**, with formal semantics and ontologies (OWL/RDFS) for reasoning/inference. Engines:
  [graphdb](../engines/graphdb.md), [stardog](../engines/stardog.md), [virtuoso](../engines/virtuoso.md), [apache-jena-tdb](../engines/apache-jena-tdb.md), [amazon-neptune](../engines/amazon-neptune.md) (supports both).

## Index-free adjacency
Native graph engines (notably [neo4j](../engines/neo4j.md)) store edges as direct pointers between node records
("index-free adjacency"), so traversal cost is independent of total graph size — the structural
advantage over relational recursive joins. Non-native graph layers on top of [wide-column](wide-column.md) or
relational stores ([janusgraph](../engines/janusgraph.md) on [apache-cassandra](../engines/apache-cassandra.md)/[apache-hbase](../engines/apache-hbase.md)) trade some of that for
scale and storage reuse.

## Strengths and anti-patterns
- **Strengths:** deep/variable-length traversals, pathfinding, pattern matching, recommendation,
  knowledge graphs, fraud/network analysis, increasingly graph-RAG.
- **Anti-patterns:** bulk analytical scans/aggregations over all nodes (a columnar OLAP store wins),
  simple tabular CRUD (relational is simpler), and very high write throughput on supernodes.

## How to use it on engine pages
State property-graph vs RDF (or both), the query language (Cypher/Gremlin/GQL/SPARQL), whether it's
native (index-free adjacency) or layered on another store, transaction support, and how/whether it
shards a graph (graph partitioning is hard — see [sharding-partitioning](sharding-partitioning.md)).
