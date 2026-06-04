---
name: Apache Solr
slug: apache-solr
rank: 21
data_model: Search engine
license: Apache License 2.0 (permissive)
summary: Mature Lucene-based search/IR platform; rich querying and faceting, run as a CP distributed cluster (SolrCloud) coordinated by ZooKeeper — not a primary store.
last_researched: 2026-06-04
confidence: high
---

# Apache Solr

> The veteran open-source enterprise search server: an inverted-index full-text engine on top of lucene, with deep faceting, geospatial and (since 9.0) dense-vector search — best treated as a secondary search layer, not a system of record.

## Identity
- **Taxonomy / data model:** Search engine ([full-text-search](../concepts/full-text-search.md)); document-oriented over a flat field/schema model. Built on Apache Lucene; closest sibling is [elasticsearch](elasticsearch.md) / [opensearch](opensearch.md) (also Lucene). Multi-model only loosely (vectors, spatial, JSON facets).
- **Storage model:** Lucene inverted index plus stored fields, doc-values (columnar) for sorting/faceting, and a per-shard transaction log. Index segments are **immutable**, written once and later merged — append + merge rather than in-place update; conceptually LSM-like rather than B-tree (see [lsm-vs-btree](../concepts/lsm-vs-btree.md)). On-disk format is Lucene's segment files.
- **Workload:** Search/IR and analytics-style faceting/aggregation, i.e. read-heavy OLAP-ish queries over text ([oltp-olap-htap](../concepts/oltp-olap-htap.md)). Not OLTP — no general multi-document transactions. "Near-real-time" search, not low-latency point-write transactional behavior.

## Distribution & consistency
- **CAP under partition:** SolrCloud is **CP** — it favors consistency over availability for writes and prefers consistency for reads, with heuristics that keep some availability ([Lucidworks/Jepsen](https://lucidworks.com/blog/call-maybe-solrcloud-jepsen-flaky-networks/)). Writes route to the shard leader and replicate synchronously to active replicas; if a replica can't be reached it's marked down and must recover. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** Under partition (P) it leans toward C (refuses/queues writes that can't reach the leader/quorum). Else (E) it favors latency once writes hit the leader and replicas, and **reads are eventually consistent across replicas** — different replicas can return different results between commits/recovery ([SOLR-5821](https://issues.apache.org/jira/browse/SOLR-5821)). So roughly **PC/EL** with eventually-consistent reads.
- **Default isolation & what's achievable:** No transactions in the RDBMS sense; no isolation levels. Updates are per-document atomic; a `commit` makes them visible. Optimistic concurrency is available via the `_version_` field (compare-and-set), returning HTTP 409 on version conflict ([Partial Document Updates](https://solr.apache.org/guide/solr/latest/indexing-guide/partial-document-updates.html)). There is no serializable/snapshot isolation across documents; do not model Solr as ACID. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** Single-leader per shard; leader elected via ZooKeeper. Updates flow leader → replicas **synchronously to active replicas** (not a quorum vote). Three replica types: **NRT** (indexes locally, leader-eligible, supports soft-commit/RTG), **TLOG** (keeps tlog, indexes via replication except when leader, leader-eligible), **PULL** (replication-only, not leader-eligible) ([Solr Ref Guide: replica types](https://solr.apache.org/guide/solr/latest/deployment-guide/solrcloud-shards-indexing.html)). See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Limited. `min_rf`/`minReplicationFactor` historically reported achieved replication so the client could retry; reads can target leaders for fresher data but there are no per-query Dynamo-style consistency levels.
- **Clock dependency:** Coordination is via ZooKeeper ([consensus-raft-paxos](../concepts/consensus-raft-paxos.md) — ZAB), not wall clocks; correctness does not rest on synchronized clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write, with options:** Classic mode uses an explicit `managed-schema`/`schema.xml`. "Schemaless" mode does field guessing and auto-adds fields, but that just defers the schema to runtime inference — the schema still exists. Effectively schema-on-write.
- **Migration/evolution:** Adding fields is online via the Schema API. Changing an existing field's type or analysis chain generally requires **reindexing** — there is no online in-place ALTER of field semantics. This reindex burden is a recurring operational gotcha.
- **Type system:** Text (with rich analyzer/tokenizer/filter chains), numerics, dates, booleans, geospatial (points, shapes via JTS/Spatial4j), nested/child documents, and **DenseVectorField** for ANN search (added in 9.0; HNSW via Lucene) ([Dense Vector Search](https://solr.apache.org/guide/solr/latest/query-guide/dense-vector-search.html)). See [vector-search-ann](../concepts/vector-search-ann.md).

## Query interface
- **Language:** HTTP/REST APIs (JSON or XML), not SQL by default. Lucene query syntax plus DSLs: standard/DisMax/eDisMax parsers, JSON Request API, JSON Facet API, `knn`/`vectorSimilarity` parsers for vectors, function queries, and streaming expressions. A **Parallel SQL** interface (limited SQL over Streaming Expressions, JDBC driver) exists but is not the primary path.
- **Transactions:** None multi-document. Per-document atomic add/update/delete; optimistic concurrency via `_version_`. Commits are cluster/collection-wide visibility events, not transactions.
- **Native vs app-side:** Faceting, grouping, highlighting, spellcheck, geospatial, and aggregations are **native and a core strength**. Joins exist (cross-core/block joins) but are constrained and not relational-grade — denormalize instead. No real foreign-key joins.
- **Stored procedures / UDFs:** No stored procedures. Extensibility via Java plugins (analyzers, request handlers, search components, streaming expressions, URPs); **Streaming Expressions** cover much server-side compute. Since 9.8 an **LLM module** can call an external embedding service for text→vector ([Text to Vector](https://solr.apache.org/guide/solr/latest/query-guide/text-to-vector.html)).

## Scaling & topology
- **Vertical vs horizontal:** Horizontal via SolrCloud — a collection is split into **shards**, each shard has **replicas** ([sharding-partitioning](../concepts/sharding-partitioning.md)). Also runs single-node (standalone) for small deployments.
- **Sharding:** Hash-based (compositeId) routing by default, or implicit/manual routing. **Resharding is painful** — changing shard count generally means SPLITSHARD or reindexing into a new collection; there's no seamless online auto-rebalance to arbitrary shard counts.
- **Read replicas & consistency:** Replicas serve reads; non-leader reads can be stale relative to the leader between commits/recovery (eventually consistent). Target leaders for freshest results.
- **Storage/compute separation:** Traditionally shared-nothing local disk per node. Solr can store indexes on HDFS or S3 ("shared storage" / `S3Directory`), edging toward [storage-compute-separation](../concepts/storage-compute-separation.md), but it is not a true separated storage-compute architecture like Snowflake/Aurora. ⚠️ unverified — maturity of S3-backed deployments at scale.

## Performance & durability
- **Write path:** Update → per-replica **transaction log (tlog)** + Lucene index buffer. **Soft commit** makes docs searchable (NRT) without fsync; **hard commit** flushes segments and truncates the tlog (see [wal-and-durability](../concepts/wal-and-durability.md)). Crash recovery replays the tlog. **Data-loss window:** documents indexed since the last hard commit and not durably fsynced (and not on another active replica) can be lost on a crash — tune `autoCommit`/`openSearcher` and `fsync` accordingly.
- **Throughput/latency:** Excellent read/query throughput and faceting performance; near-real-time search latency governed by soft-commit interval. Tail (p99) is sensitive to GC pauses (JVM) and to **segment merges** colliding with query load.
- **Compaction / GC:** Lucene **segment merging** is the compaction analog; large merges cause I/O and p99 spikes. Running on the JVM means GC tuning (heap, G1) directly affects tail latency. Frequent soft commits + heavy merging is the classic p99 trap.

## Operations & maturity
- **Backup/restore:** Collection-level BACKUP/RESTORE (to local, HDFS, or S3). No native point-in-time recovery like an RDBMS — restore granularity is the backup snapshot.
- **Observability:** Metrics API (Dropwizard, Prometheus exporter), Admin UI, per-query `debug`/explain for relevance scoring, slow-query logging. Good visibility into query plans/relevance.
- **Upgrade story:** Rolling upgrades supported within a major line; **cross-major upgrades require reindexing** when the underlying Lucene index format changes (Lucene supports only N-1 back-compat). Day-2 burden: ZooKeeper ensemble operation, JVM/GC tuning, merge/commit tuning, and reindex planning.
- **Maturity:** Very mature (Solr since 2006; SolrCloud since 4.0/2012). **Jepsen-tested** (Lucidworks, 2014): under bridge and transitive partitions SolrCloud showed **no data loss for inserts or compare-and-set**; one major and a few minor bugs were found and fixed in **4.10.2** and shortly after ([Call Me Maybe: SolrCloud](https://lucidworks.com/blog/call-maybe-solrcloud-jepsen-flaky-networks/)). Note: that report is old (4.x) and does not certify linearizability of recent versions. Known failure modes: stale/inconsistent reads across replicas, full ZooKeeper outage freezing cluster state (existing active replicas keep serving, but recovery/elections stall).

## Ecosystem & people
- **Canonical use cases:** Enterprise/site search, e-commerce search and faceted navigation, log/document search, geospatial search, and increasingly hybrid lexical+vector (semantic) search. **Anti-patterns:** as a system of record / primary transactional DB; for relational joins and ACID workloads (use [postgresql](postgresql.md)); for high-frequency mutable single-record updates; greenfield teams who want a managed cloud-native search service often choose [elasticsearch](elasticsearch.md)/[opensearch](opensearch.md) instead.
- **Drivers / connectors:** SolrJ (Java) plus community clients for Python/.NET/PHP/etc.; integrations with Spark, Hadoop/HDFS, Nutch, Tika (rich-doc extraction), and DataImportHandler historically (deprecated). CDC/ingest is typically app- or pipeline-driven (Kafka connectors community-supplied).
- **Community/support:** Large, long-established ASF community; commercial support and tooling from Lucidworks and others. Docs (Solr Reference Guide) are thorough. **Learning curve is steep** — analyzers, schema, commit/merge tuning, and ZooKeeper ops all demand expertise; typical operators are search/IR specialists.

## Licensing & cost
- **OSS license:** **Apache License 2.0** — permissive (see [license-taxonomy](../concepts/license-taxonomy.md)); fully open, no post-2018 relicensing (contrast Elasticsearch's 2021 move to SSPL/Elastic License, which spawned [opensearch](opensearch.md)). Solr stayed Apache-licensed throughout.
- **Self-managed vs managed:** Primarily self-managed (on-prem or your own cloud VMs/k8s). Managed offerings exist via third parties (e.g. Lucidworks Fusion, KandaSearch); no first-party hyperscaler-native managed Solr comparable to managed OpenSearch.
- **Lock-in:** Low at the license level; practical lock-in is in schema/analyzer config and query DSL.
- **Cost model:** No license cost; you pay for nodes (CPU/RAM/disk) and ZooKeeper. Cost scales with index size, replica count, and JVM heap; RAM/heap pressure is the main driver as data grows.

## Hardware / deployment
- **Resource profile:** **Memory-bound** in practice — relies heavily on OS page cache for the Lucene index plus JVM heap for query/facet structures; doc-values and faceting can be RAM-hungry. Not required that all data fit in RAM, but the **hot working set should fit in page cache** for good latency. CPU matters for analysis and vector/ANN scoring.
- **Storage assumptions:** Local **NVMe/SSD** strongly preferred for low merge/query latency; network-attached (EBS/S3) works but adds latency, especially during merges.
- **Footprint:** Single-node standalone or clustered SolrCloud (plus a separate ZooKeeper ensemble; Solr 9 can also use an embedded ZK for dev). Not embeddable as a library in the SQLite sense (though Lucene itself is). Runs on the JVM.
- **Deployment:** On-prem or self-managed cloud; **k8s** support via the official Solr Operator (StatefulSets), with the usual stateful-on-k8s realities (persistent volumes, ZK coordination, ordered restarts).

## Bottom line
Reach for Solr when you need a mature, fully open-source (Apache-2.0) full-text/faceted search engine with strong IR features and you want to run it yourself without source-available licensing strings — it is a peer of Elasticsearch with arguably cleaner licensing. Do not use it as your primary database or for transactional/relational workloads: it has no multi-document ACID, eventually-consistent replica reads, and a real reindex burden on schema/major-version changes. The single biggest gotcha is treating it as a system of record — it is a secondary search index fed from an authoritative store, and crash durability depends on commit/fsync tuning.

## Sources
- [Apache Solr Reference Guide — Cluster Types](https://solr.apache.org/guide/solr/latest/deployment-guide/cluster-types.html)
- [Apache Solr Reference Guide — SolrCloud Shards and Indexing (replica types)](https://solr.apache.org/guide/solr/latest/deployment-guide/solrcloud-shards-indexing.html)
- [Apache Solr Reference Guide — Dense Vector Search](https://solr.apache.org/guide/solr/latest/query-guide/dense-vector-search.html)
- [Apache Solr Reference Guide — Text to Vector / LLM module](https://solr.apache.org/guide/solr/latest/query-guide/text-to-vector.html)
- [Apache Solr Reference Guide — Major Changes in Solr 9](https://solr.apache.org/guide/solr/latest/upgrade-notes/major-changes-in-solr-9.html)
- [Call Me Maybe: SolrCloud, Jepsen, and Flaky Networks (Lucidworks, 2014)](https://lucidworks.com/blog/call-maybe-solrcloud-jepsen-flaky-networks/)
- [SOLR-5821 — Search inconsistency on SolrCloud replicas](https://issues.apache.org/jira/browse/SOLR-5821)
- [Apache Solr — Downloads / versions](https://solr.apache.org/downloads.html)
- [Apache Solr — Wikipedia](https://en.wikipedia.org/wiki/Apache_Solr)
