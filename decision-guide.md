---
name: Decision Guide
slug: decision-guide
summary: Which database should I use? A walk-top-to-bottom tree derived from the 150 researched engine pages — ask the four questions first, then jump to your workload.
last_researched: 2026-06-04
---

# Which Database Should I Use?

> Built **from the data** in this wiki (150 engines), per [CLAUDE](CLAUDE.md) §8. Walk it top to bottom in a
> couple of minutes. Leaves name linked engine candidates with the **key trade-off** and the
> **anti-pattern** (when *not* to pick it). Every claim links to a page — follow it before betting on it.

---

## Ask these four first

These four questions eliminate the most candidates fastest. Answer them, then go to the matching
section.

1. **What is the primary job?** (data model + workload) — the biggest filter:
   transactional app DB (OLTP) · analytics/reporting (OLAP) · document · key-value/cache ·
   graph · time-series/metrics · full-text search · vector/AI retrieval · stream processing ·
   spatial · *several of these at once* (→ [multi-model](concepts/multi-model.md), but verify each model is first-class).
   See [oltp-olap-htap](concepts/oltp-olap-htap.md).
2. **Scale & topology?** single-node / embedded · single-primary + read replicas ·
   horizontally sharded · globally distributed (multi-region writes). Most workloads are smaller
   than people think — don't buy distribution you won't use. See [sharding-partitioning](concepts/sharding-partitioning.md),
   [replication-models](concepts/replication-models.md).
3. **Operations & licensing?** self-hosted vs managed/serverless; is cloud lock-in acceptable;
   do you require **permissive** OSS (Apache/MIT/BSD) vs tolerate **source-available** (SSPL/BSL)
   or **proprietary**? See [license-taxonomy](concepts/license-taxonomy.md).
4. **Consistency & durability needs?** strict-serializable / strong vs tunable / eventual; what is
   your acceptable **data-loss window** on crash? The framing mental model is [acid-vs-base](concepts/acid-vs-base.md)
   (correctness-first vs availability-first — a spectrum, not a binary). See [isolation-levels](concepts/isolation-levels.md),
   [cap-pacelc](concepts/cap-pacelc.md), [wal-and-durability](concepts/wal-and-durability.md). Beware "ACID"/"serializable" that is really snapshot
   isolation, and verify distributed-consistency claims against [jepsen](concepts/jepsen.md).

**The single most common right answer:** for a general transactional application, default to
**[postgresql](engines/postgresql.md)** until you have a concrete reason not to. Most "we need NoSQL/distributed" instincts
are premature.

---

## 1. Transactional application database (OLTP)

**Start here unless you have a specific reason to leave.**

- **Default, self-hosted, permissive:** [postgresql](engines/postgresql.md) — real SERIALIZABLE via SSI, vast extension
  ecosystem (JSON, [spatial](engines/postgis.md), pgvector). ✗ no built-in sharding; watch vacuum/bloat at scale.
- **Ubiquitous, simple, huge hiring pool:** [mysql](engines/mysql.md) / [mariadb](engines/mariadb.md) — easy, battle-tested. ✗ default
  "REPEATABLE READ" is weaker than its name ([jepsen](concepts/jepsen.md)); MariaDB Galera consistency is overstated.
  [percona-server-for-mysql](engines/percona-server-for-mysql.md) for free enterprise-grade extras.
- **Microsoft shop:** [microsoft-sql-server](engines/microsoft-sql-server.md) — mature, T-SQL, columnstore HTAP. ✗ per-core cost.
- **Already on Oracle / extreme OLTP+options:** [oracle](engines/oracle.md) — deepest feature set. ✗ cost and
  audit/licensing traps; "SERIALIZABLE" is snapshot isolation.
- **Embedded / single-file / edge:** [sqlite](engines/sqlite.md) (the default; single-writer), [duckdb](engines/duckdb.md) (if the
  embedded workload is *analytical*), [h2](engines/h2.md)/[hypersql](engines/hypersql.md)/[apache-derby](engines/apache-derby.md) (JVM/test),
  [realm](engines/realm.md)/[pouchdb](engines/pouchdb.md) (mobile/offline). See [embedded-databases](concepts/embedded-databases.md). ✗ not multi-writer servers.
- **Managed, minimal ops (cloud OK):** [amazon-aurora](engines/amazon-aurora.md) (MySQL/Postgres-compatible, disaggregated
  storage), [microsoft-azure-sql-database](engines/microsoft-azure-sql-database.md), [alibaba-cloud-polardb](engines/alibaba-cloud-polardb.md), [edb-postgres](engines/edb-postgres.md). ✗ cloud
  lock-in; AWS/Azure-only.

### Need to scale OLTP horizontally or across regions?
- **Distributed SQL (NewSQL), strong consistency:** [cockroachdb](engines/cockroachdb.md) (serializable, Postgres-wire,
  survives region loss, BSL), [yugabytedb](engines/yugabytedb.md) (Postgres-wire, Apache-2.0, HLC clocks),
  [google-cloud-spanner](engines/google-cloud-spanner.md) (strict serializability via TrueTime, managed-only),
  [tidb](engines/tidb.md) (MySQL-wire, HTAP), [oceanbase](engines/oceanbase.md) (financial-grade, MySQL/Oracle-compat). ✗ all pay a
  consensus-latency tax ([consensus-raft-paxos](concepts/consensus-raft-paxos.md)); overkill below ~single-node-saturation scale.
- **Shard an existing Postgres/MySQL:** [citus](engines/citus.md) (Postgres extension; cross-shard reads lack a
  distributed snapshot), [planetscale](engines/planetscale.md) (managed Vitess MySQL/Postgres; cross-shard txns
  best-effort). ✗ you must pick shard keys well — see [sharding-partitioning](concepts/sharding-partitioning.md).
- **Strict-serializable + immutability/audit:** [datomic](engines/datomic.md) (Datalog, time-travel, Jepsen-clean).
  ✗ closed-source, single-writer transactor.

---

## 2. Analytics / reporting / data warehouse (OLAP)

Column-stores and MPP — see [columnar-storage](concepts/columnar-storage.md). **Anti-pattern for all of these: OLTP / many small
writes / point lookups.**

- **Managed cloud warehouse, near-zero tuning:** [snowflake](engines/snowflake.md) (storage/compute separation, easy to
  overspend), [google-bigquery](engines/google-bigquery.md) (serverless, billed by bytes scanned), [amazon-redshift](engines/amazon-redshift.md),
  [microsoft-fabric](engines/microsoft-fabric.md) / [microsoft-azure-synapse-analytics](engines/microsoft-azure-synapse-analytics.md) (Synapse now legacy → Fabric). ✗
  cost surprises; vendor lock-in.
- **Lakehouse (own your open storage):** see the dedicated subsection just below.

### Lakehouse: own your open storage
Architecture, not a product — open columnar files + an [open table format](concepts/open-table-formats.md) +
a [catalog](concepts/data-catalog.md), queried by many decoupled engines. See [lakehouse](concepts/lakehouse.md). Decide three things:
- **Table format** — [apache-iceberg](engines/apache-iceberg.md) (vendor-neutral default, broadest engine support) ·
  [delta-lake](engines/delta-lake.md) (if you're on [databricks](engines/databricks.md)/Spark; UniForm exposes Iceberg metadata) ·
  [apache-hudi](engines/apache-hudi.md) / [apache-paimon](engines/apache-paimon.md) (streaming/CDC **upserts**: Hudi batch-leaning, Paimon
  Flink-native LSM). ✗ table-format ACID is *table-level optimistic*, not row-level — bad for OLTP.
- **Engine over it** — [databricks](engines/databricks.md) (managed Spark+Delta), [trino](engines/trino.md)/[presto](engines/presto.md) (federated SQL),
  [apache-spark-sql](engines/apache-spark-sql.md) (batch/ETL), [dremio](engines/dremio.md) (Arrow, BI acceleration), [clickhouse](engines/clickhouse.md)/[starrocks](engines/starrocks.md)
  (fast reads), [duckdb](engines/duckdb.md) (single-node), or even [snowflake](engines/snowflake.md) reading Iceberg. ✗ these are compute
  layers — transactions come from the table format, not the engine.
- **Catalog** — [apache-polaris](engines/apache-polaris.md) (open Iceberg REST, vendor-neutral) · [unity-catalog](engines/unity-catalog.md)
  (Databricks governance) · [hive-metastore](engines/hive-metastore.md) (legacy lingua franca). The catalog arbitrates
  multi-engine ACID — all writers must share one.
- **Self-hosted / real-time OLAP:** [clickhouse](engines/clickhouse.md) (blazing scans, eventually consistent),
  [starrocks](engines/starrocks.md) / [apache-druid](engines/apache-druid.md) (sub-second slice-and-dice), [exasol](engines/exasol.md) / [vertica](engines/vertica.md) /
  [greenplum](engines/greenplum.md) / [sap-iq](engines/sap-iq.md) / [teradata](engines/teradata.md) / [netezza](engines/netezza.md) / [gbase](engines/gbase.md) (MPP, legacy→modern spectrum).
- **Embedded analytics:** [duckdb](engines/duckdb.md) — "SQLite for analytics", single-node, vectorized. ✗ not multi-user.
- **HTAP (one system for both):** [singlestore](engines/singlestore.md) (RC only), [sap-hana](engines/sap-hana.md) (RAM-priced), [tidb](engines/tidb.md)
  (row+columnar replica), [oracle](engines/oracle.md)/[microsoft-sql-server](engines/microsoft-sql-server.md) columnstore. Always verify the
  **physical separation** mechanism — see [oltp-olap-htap](concepts/oltp-olap-htap.md).

---

## 3. Document store (JSON, flexible schema)

See [document-data-model](concepts/document-data-model.md).

- **General document DB:** [mongodb](engines/mongodb.md) — dominant, easy scale-out. ✗ safe consistency needs
  non-default `w:majority` + majority/snapshot reads; weak defaults lost data in every [jepsen](concepts/jepsen.md) test.
- **Managed / serverless:** [google-cloud-firestore](engines/google-cloud-firestore.md) (serializable, mobile sync),
  [amazon-documentdb](engines/amazon-documentdb.md) (Mongo-API, real feature gaps), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md) (multi-API,
  five consistency levels), [ibm-cloudant](engines/ibm-cloudant.md), [cloudkit](engines/cloudkit.md) (Apple-only). ✗ lock-in.
- **Offline-first / sync:** [couchdb](engines/couchdb.md) / [pouchdb](engines/pouchdb.md) / [ibm-cloudant](engines/ibm-cloudant.md) (CouchDB replication protocol),
  [couchbase](engines/couchbase.md) (memory-first, SQL++), [firebase-realtime-database](engines/firebase-realtime-database.md) (small realtime apps),
  [realm](engines/realm.md) (mobile). ✗ AP/eventual; app-resolved conflicts (see [crdts](concepts/crdts.md)).
- **.NET-native:** [ravendb](engines/ravendb.md). ✗ Jepsen found isolation claims overstated.

---

## 4. Key-value / cache / coordination

See [key-value-store](concepts/key-value-store.md). **Most of these are caches, not systems of record.**

- **In-memory cache / data structures:** [redis](engines/redis.md) / [valkey](engines/valkey.md) (Valkey = BSD fork after Redis
  relicensed), [memcached](engines/memcached.md) (minimalist, volatile), [hazelcast](engines/hazelcast.md) / [apache-ignite](engines/apache-ignite.md) /
  [gemfire](engines/gemfire.md) / [oracle-coherence](engines/oracle-coherence.md) / [ehcache](engines/ehcache.md) / [infinispan](engines/infinispan.md) (JVM data grids). ✗ async
  replication → poor system of record.
- **Durable, scale-out KV:** [amazon-dynamodb](engines/amazon-dynamodb.md) (serverless, single-digit-ms, design for access
  patterns), [aerospike](engines/aerospike.md) (flash-optimized sub-ms, multi-record ACID since 8.0), [riak-kv](engines/riak-kv.md)
  (Dynamo-style + [crdts](concepts/crdts.md); ✗ LWW default silently drops writes), [oracle-nosql](engines/oracle-nosql.md). 
- **Strongly-consistent config/coordination:** [etcd](engines/etcd.md) (strict-serializable Raft; the brain of
  Kubernetes). ✗ small critical data only, not a general DB.
- **Embedded storage engine (inside your app or another DB):** [rocksdb](engines/rocksdb.md) / [leveldb](engines/leveldb.md) (LSM),
  [lmdb](engines/lmdb.md) / [oracle-berkeley-db](engines/oracle-berkeley-db.md) (B-tree). See [lsm-vs-btree](concepts/lsm-vs-btree.md), [embedded-databases](concepts/embedded-databases.md).

---

## 5. Graph

See [graph-data-model](concepts/graph-data-model.md).

- **Property graph, deep traversals:** [neo4j](engines/neo4j.md) (market leader, Cypher, index-free adjacency). ✗
  single-leader, read-committed, doesn't shard a connected graph.
- **In-memory / real-time graph:** [memgraph](engines/memgraph.md) (Neo4j-compatible Cypher). ✗ HA is Enterprise-only.
- **Distributed / huge graphs:** [janusgraph](engines/janusgraph.md) (over Cassandra/HBase/Bigtable; ✗ not ACID on common
  backends), [nebulagraph](engines/nebulagraph.md) (trillions of edges; ✗ no general ACID), [tigergraph](engines/tigergraph.md) (MPP analytics).
- **Managed:** [amazon-neptune](engines/amazon-neptune.md) (property graph + RDF). ✗ single-writer, AWS lock-in.
- **RDF / knowledge graph / SPARQL + reasoning:** [graphdb](engines/graphdb.md), [stardog](engines/stardog.md), [virtuoso](engines/virtuoso.md),
  [apache-jena-tdb](engines/apache-jena-tdb.md) (embedded, single-node). ✗ triplestores, not general app DBs.

---

## 6. Time-series / metrics / IoT

See [time-series-storage](concepts/time-series-storage.md).

- **Metrics & monitoring:** [prometheus](engines/prometheus.md) (pull-scrape, PromQL; ✗ single-node, not durable alone) →
  scale/long-term with [victoriametrics](engines/victoriametrics.md) (high-cardinality, ~1s data-loss window). [graphite](engines/graphite.md)
  (legacy RRD-style).
- **General TSDB with SQL:** [timescaledb](engines/timescaledb.md) (Postgres extension, full ACID; ✗ single-node now),
  [influxdb](engines/influxdb.md) (v3 = columnar/Parquet rewrite), [questdb](engines/questdb.md) (fast ingest; ✗ HA Enterprise-only).
- **IoT/industrial:** [tdengine](engines/tdengine.md), [apache-iotdb](engines/apache-iotdb.md), [dolphindb](engines/dolphindb.md). **Finance/tick data:** [kdb](engines/kdb.md)
  (the standard; ✗ closed, idiosyncratic q language, non-ACID), [dolphindb](engines/dolphindb.md).
- **Event analytics over time:** [apache-druid](engines/apache-druid.md), [microsoft-azure-data-explorer](engines/microsoft-azure-data-explorer.md) (Kusto/KQL),
  [clickhouse](engines/clickhouse.md).

---

## 7. Full-text search

See [full-text-search](concepts/full-text-search.md). **All are secondary indexes fed from a durable primary — not systems of
record** (e.g. [elasticsearch](engines/elasticsearch.md) lost acknowledged writes under partition, [jepsen](concepts/jepsen.md)).

- **Self-hosted Lucene:** [elasticsearch](engines/elasticsearch.md) (now SSPL/AGPL; logs/observability/vectors),
  [opensearch](engines/opensearch.md) (Apache-2.0 fork), [apache-solr](engines/apache-solr.md) (mature, CP SolrCloud). 
- **Managed / hosted:** [algolia](engines/algolia.md) (sub-50ms instant search), [microsoft-azure-ai-search](engines/microsoft-azure-ai-search.md)
  (full-text + vector + RAG), [coveo](engines/coveo.md) (enterprise/commerce), [amazon-cloudsearch](engines/amazon-cloudsearch.md) (legacy).
- **Lightweight / single-node:** [meilisearch](engines/meilisearch.md) (typo-tolerant; ✗ weak HA/scale), [sphinx](engines/sphinx.md)
  (frozen → Manticore fork). **Logs/SIEM at scale:** [splunk](engines/splunk.md) (schema-on-read; ✗ expensive).

---

## 8. Vector / AI retrieval (RAG)

See [vector-search-ann](concepts/vector-search-ann.md). Decide: **dedicated vector DB** vs **add vectors to a DB you already run**
(pgvector in [postgresql](engines/postgresql.md), [redis](engines/redis.md), [mongodb](engines/mongodb.md), [elasticsearch](engines/elasticsearch.md) — usually enough until high
scale/QPS).

- **Managed/serverless:** [pinecone](engines/pinecone.md) (API-only, no self-host). ✗ eventually consistent, lock-in.
- **Open-source, scale:** [milvus](engines/milvus.md) (billion-scale, disaggregated), [qdrant](engines/qdrant.md) (rich payload
  filtering, Rust), [weaviate](engines/weaviate.md) (hybrid BM25+vector, RAG modules), [chroma](engines/chroma.md) (dev-first, embeddable
  → serverless cloud). ✗ none are ACID systems of record; pair with a primary store.

---

## 9. Specialized & "it's not really a database"

- **Spatial / GIS:** [postgis](engines/postgis.md) (the de facto open-source GIS engine, on [postgresql](engines/postgresql.md)),
  [spatialite](engines/spatialite.md) (embedded, on [sqlite](engines/sqlite.md)). ✗ PostGIS has no native spatial sharding.
- **Stream processing / streaming / CDC:** see the dedicated **Streaming** section (§10) below.
- **Multidimensional/MOLAP (financial planning):** [oracle-essbase](engines/oracle-essbase.md). ✗ single-node, proprietary.
- **Content repository (CMS/DAM):** [apache-jackrabbit](engines/apache-jackrabbit.md) (JCR; engine under Adobe AEM).
- **Multi-model "do several at once":** [arangodb](engines/arangodb.md) (doc+graph+KV, one query language; ✗ cluster
  ACID only within a shard), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md), [marklogic](engines/marklogic.md) (doc+RDF+search, real
  multi-doc ACID; ✗ costly), [intersystems-iris](engines/intersystems-iris.md) (healthcare; ✗ defaults to READ UNCOMMITTED),
  [fauna](engines/fauna.md) (✗ service shut down 2025). Read [multi-model](concepts/multi-model.md) first — one model is usually
  first-class and the rest bolted on.
- **MultiValue / mainframe / legacy** (choose only if the app already requires it): [adabas](engines/adabas.md),
  [unidata-universe](engines/unidata-universe.md), [maxdb](engines/maxdb.md), [dbase](engines/dbase.md), [filemaker](engines/filemaker.md), [4d](engines/4d.md), [openedge](engines/openedge.md), [ingres](engines/ingres.md),
  [informix](engines/informix.md), [interbase](engines/interbase.md), [sap-adaptive-server](engines/sap-adaptive-server.md).

---

## 10. Streaming, real-time & event-driven

Moving and acting on events as they happen. These compose into a pipeline — pick one per layer, not
one tool for all of it. See [streaming-platforms](concepts/streaming-platforms.md), [streaming-databases](concepts/streaming-databases.md), [change-data-capture](concepts/change-data-capture.md),
[real-time-olap](concepts/real-time-olap.md).

- **Event log / transport (the backbone):** [apache-kafka](engines/apache-kafka.md) (de facto standard, huge ecosystem) ·
  [apache-pulsar](engines/apache-pulsar.md) (broker/storage separation, multi-tenant, geo) · [redpanda](engines/redpanda.md) (Kafka-API, C++,
  no JVM/ZooKeeper, lower p99; ✗ single-vendor BSL). ✗ none is a queryable database or system of
  record — it's a replayable log.
- **Get changes OUT of an operational DB (CDC):** [debezium](engines/debezium.md) (log-based, the standard) → onto
  Kafka or into [apache-flink](engines/apache-flink.md). Use for replication, cache/[search](engines/elasticsearch.md) sync, and
  feeding the lake. ✗ ordering/exactly-once only hold end-to-end; sinks must dedupe/upsert.
- **Transform / compute on streams:** [apache-flink](engines/apache-flink.md) (stateful, event-time, exactly-once — the
  heavyweight), Kafka Streams / ksqlDB (Kafka-native). ✗ processors aren't queryable stores by
  themselves.
- **Continuously-fresh SQL views (streaming databases):** [materialize](engines/materialize.md) (Postgres-wire,
  strict-serializable incremental views) · [risingwave](engines/risingwave.md) (Postgres-wire, state on object storage) ·
  [ksqldb](engines/ksqldb.md) (Kafka-native; now largely superseded by Flink). Use when you want
  `CREATE MATERIALIZED VIEW` that stays current. ✗ not for heavy ad-hoc OLAP.
- **Serve fresh data for ad-hoc analytics (real-time OLAP sinks):** [apache-pinot](engines/apache-pinot.md) (high-QPS
  user-facing) · [apache-druid](engines/apache-druid.md) (time-series slice-and-dice) · [clickhouse](engines/clickhouse.md) (general fast scans) ·
  [apache-doris](engines/apache-doris.md) / [starrocks](engines/starrocks.md) (MPP with real JOINs). See [real-time-olap](concepts/real-time-olap.md). ✗ append/ingest
  oriented — not OLTP, not a system of record.
- **Mutable analytic storage:** [apache-kudu](engines/apache-kudu.md) (fast scans + random updates, paired with Impala/Spark)
  — when lake table formats' update story is too coarse.

## Cross-cutting filters (apply to any leaf above)

- **License red flags:** post-2018 relicensing to source-available (SSPL: [mongodb](engines/mongodb.md),
  [elasticsearch](engines/elasticsearch.md); BSL: [cockroachdb](engines/cockroachdb.md), [scylladb](engines/scylladb.md)) — if you need permissive OSS or to offer it
  as a service, prefer [postgresql](engines/postgresql.md), [valkey](engines/valkey.md), [opensearch](engines/opensearch.md), [clickhouse](engines/clickhouse.md), [milvus](engines/milvus.md).
  See [license-taxonomy](concepts/license-taxonomy.md).
- **Managed-only (no self-host):** [snowflake](engines/snowflake.md), [google-bigquery](engines/google-bigquery.md), [google-cloud-spanner](engines/google-cloud-spanner.md),
  [amazon-dynamodb](engines/amazon-dynamodb.md), [pinecone](engines/pinecone.md), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md), [cloudkit](engines/cloudkit.md) — accept lock-in or
  rule them out.
- **Dead / dying / frozen (avoid for new builds):** [rockset](engines/rockset.md) (shut to outsiders 2024),
  [fauna](engines/fauna.md) (2025), [rethinkdb](engines/rethinkdb.md) (commercially dead), [amazon-simpledb](engines/amazon-simpledb.md) / [amazon-cloudsearch](engines/amazon-cloudsearch.md)
  (closed to new customers), [orientdb](engines/orientdb.md) (orphaned), [maxdb](engines/maxdb.md) (EOL), [apache-derby](engines/apache-derby.md) (read-only).
- **"Strongly consistent" claims:** verify against [jepsen](concepts/jepsen.md) and check whether safe behavior needs
  non-default settings — it often does ([mongodb](engines/mongodb.md), [redis](engines/redis.md), [mariadb](engines/mariadb.md) Galera, [riak-kv](engines/riak-kv.md)).
- **Lakehouse interop & lock-in:** if you want many engines on one copy of data, standardize on
  [apache-iceberg](engines/apache-iceberg.md) + an open [catalog](concepts/data-catalog.md) ([apache-polaris](engines/apache-polaris.md)) over Delta+Unity unless
  you're committed to [databricks](engines/databricks.md). All writers must share one catalog or multi-engine ACID breaks.
- **ACID vs BASE framing:** don't accept the label — pin the concrete guarantee (default+achievable
  isolation, CAP/PACELC, tunable?, data-loss window). See [acid-vs-base](concepts/acid-vs-base.md).

---

## Maintenance

Re-derive the question order and leaves as coverage grows or engines change status; record changes in
[log](log.md) under `decision-guide`. This version derived from 150 engine pages researched 2026-06-04.
