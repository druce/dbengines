---
name: Decision Guide
slug: decision-guide
summary: Which database should I use? A decision guide derived from the 150 researched engine pages — ask the four questions first, then jump to your workload.
last_researched: 2026-06-04
---

# Which Database Should I Use?

> Built **from the data** in this wiki (top 150 engines from [db-engines.com](https://db-engines.com/en/ranking)), following the Karpathy wiki methodology in [CLAUDE](CLAUDE.md) §8.

---

## Ask these four questions first:

1. **What is the #1 job?** (data model + workload): transactional app DB (OLTP) · analytics/reporting (OLAP) · document · key-value/cache · graph · time-series/metrics · full-text search · vector/AI retrieval · stream processing · spatial · *several of these at once* (→ [multi-model](concepts/multi-model.md), but verify each model is first-class). See [oltp-olap-htap](concepts/oltp-olap-htap.md).
2. **Scale & topology?** single-node / embedded · single-primary + read replicas · horizontally sharded · globally distributed (multi-region writes). Most workloads are smaller than people think — don't buy distribution you won't use. See [sharding-partitioning](concepts/sharding-partitioning.md), [replication-models](concepts/replication-models.md).
3. **Consistency & durability needs?** strict-serializable / strong vs tunable / eventual; what is your acceptable **data-loss window** on crash? The framing mental model is [acid-vs-base](concepts/acid-vs-base.md) (correctness-first vs availability-first — a spectrum, not a binary). See [isolation-levels](concepts/isolation-levels.md), [cap-pacelc](concepts/cap-pacelc.md), [wal-and-durability](concepts/wal-and-durability.md). Beware "ACID"/"serializable" that is really snapshot isolation, and verify distributed-consistency claims against [jepsen](concepts/jepsen.md).
4. **Operations & licensing?** self-hosted vs managed/serverless; is cloud lock-in acceptable; do you require **permissive** OSS (Apache/MIT/BSD) vs tolerate **source-available** (SSPL/BSL) or **proprietary**? See [license-taxonomy](concepts/license-taxonomy.md).

In general, start simple at top left and move down as necessary and then to the left based on scale.

---

## At-a-glance: data model × deployment

| Do you need…                                      | Data model      | Embedded (in-process)                                             | Self-hosted server (single node)                                                                                                                        | Distributed (self-hosted scale-out)                                                                                         | Managed / SaaS                                                                                                                                                                                          |
| ------------------------------------------------- | --------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vanilla row-column schema with ACID transactions? | **OLTP**        | [sqlite](engines/sqlite.md)                                       | [postgresql](engines/postgresql.md) · [mysql](engines/mysql.md) · [microsoft-sql-server](engines/microsoft-sql-server.md) · [oracle](engines/oracle.md) | [cockroachdb](engines/cockroachdb.md) · [yugabytedb](engines/yugabytedb.md) · [tidb](engines/tidb.md)                       | [amazon-aurora](engines/amazon-aurora.md) · [microsoft-azure-sql-database](engines/microsoft-azure-sql-database.md) · [google-cloud-spanner](engines/google-cloud-spanner.md) · [neon](engines/neon.md) |
| Schema-less JSON documents?                       | **Document**    | [realm](engines/realm.md) · [pouchdb](engines/pouchdb.md)         | [mongodb](engines/mongodb.md) · [couchdb](engines/couchdb.md)                                                                                           | [mongodb](engines/mongodb.md) (sharded) · [couchbase](engines/couchbase.md)                                                 | [google-cloud-firestore](engines/google-cloud-firestore.md) · [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md)                                                                         |
| Read-mostly for analytics over big data?          | **OLAP**        | [duckdb](engines/duckdb.md)                                       | [clickhouse](engines/clickhouse.md) · [starrocks](engines/starrocks.md)                                                                                 | [apache-druid](engines/apache-druid.md) · [greenplum](engines/greenplum.md) · [trino](engines/trino.md)                     | [snowflake](engines/snowflake.md) · [google-bigquery](engines/google-bigquery.md) · MotherDuck                                                                                                          |
| Fast cache?                                       | **Key-value**   | [rocksdb](engines/rocksdb.md) · [lmdb](engines/lmdb.md)           | [redis](engines/redis.md) · [valkey](engines/valkey.md)                                                                                                 | [aerospike](engines/aerospike.md) · [riak-kv](engines/riak-kv.md)                                                           | [amazon-dynamodb](engines/amazon-dynamodb.md)                                                                                                                                                           |
| Massive write by key?                             | **Wide-column** | —                                                                 | — *(clustered by nature)*                                                                                                                               | [apache-cassandra](engines/apache-cassandra.md) · [scylladb](engines/scylladb.md) · [apache-hbase](engines/apache-hbase.md) | [google-cloud-bigtable](engines/google-cloud-bigtable.md) · [datastax-enterprise](engines/datastax-enterprise.md)                                                                                       |
| Deep relationship traversals and graph algos?     | **Graph**       | [ladybugdb](engines/ladybugdb.md)                                 | [neo4j](engines/neo4j.md) · [memgraph](engines/memgraph.md)                                                                                             | [janusgraph](engines/janusgraph.md) · [nebulagraph](engines/nebulagraph.md)                                                 | [amazon-neptune](engines/amazon-neptune.md)                                                                                                                                                             |
| Metrics and time series?                          | **Time-series** | — *(use [duckdb](engines/duckdb.md)/[sqlite](engines/sqlite.md))* | [timescaledb](engines/timescaledb.md) · [influxdb](engines/influxdb.md) · [questdb](engines/questdb.md)                                                 | [victoriametrics](engines/victoriametrics.md) · [apache-druid](engines/apache-druid.md)                                     | [microsoft-azure-data-explorer](engines/microsoft-azure-data-explorer.md) · Timescale Cloud                                                                                                             |
| Full-text-search?                                 | **Full-text**   | [sqlite](engines/sqlite.md) FTS5 · [tantivy](engines/tantivy.md)  | [elasticsearch](engines/elasticsearch.md) · [apache-solr](engines/apache-solr.md)                                                                       | [elasticsearch](engines/elasticsearch.md) · [opensearch](engines/opensearch.md)                                             | [algolia](engines/algolia.md) · [microsoft-azure-ai-search](engines/microsoft-azure-ai-search.md)                                                                                                       |
| Semantic / AI retrieval (embeddings, RAG) ?       | **Vector**      | [lancedb](engines/lancedb.md) · [chroma](engines/chroma.md)       | [qdrant](engines/qdrant.md) · [weaviate](engines/weaviate.md)                                                                                           | [milvus](engines/milvus.md) · [qdrant](engines/qdrant.md)                                                                   | [pinecone](engines/pinecone.md)                                                                                                                                                                         |

Reading the columns as a **scaling ladder**: start as far left as your workload allows (embedded is the cheapest to operate) and move right only when scale, concurrency, or HA forces it — most workloads never need the right two columns. Several engines span multiple columns (e.g. [clickhouse](engines/clickhouse.md), [mongodb](engines/mongodb.md),[qdrant](engines/qdrant.md) run single-node *and* clustered); they're listed where they're the most natural pick.

---

## 1. Transactional application database (OLTP)

**Start here unless you have a specific reason to leave.**

- **Default, self-hosted, permissive:** [postgresql](engines/postgresql.md) — real SERIALIZABLE via SSI, vast extension ecosystem (JSON, [spatial](engines/postgis.md), pgvector). ❌ no built-in sharding; watch vacuum/bloat at scale.
- **Ubiquitous, simple, huge hiring pool:** [mysql](engines/mysql.md) / [mariadb](engines/mariadb.md) — easy, battle-tested. ❌ default "REPEATABLE READ" is weaker than its name ([jepsen](concepts/jepsen.md)); MariaDB Galera consistency is overstated. [percona-server-for-mysql](engines/percona-server-for-mysql.md) for free enterprise-grade extras.
- **Microsoft shop:** [microsoft-sql-server](engines/microsoft-sql-server.md) — mature, T-SQL, columnstore HTAP. ❌ per-core cost.
- **Already on Oracle / extreme OLTP+options:** [oracle](engines/oracle.md) — deepest feature set. ❌ cost and audit/licensing traps; "SERIALIZABLE" is snapshot isolation.
- **Enterprise / mainframe relational:** [ibm-db2](engines/ibm-db2.md) (Db2 LUW *and* z/OS mainframe, deep SQL, BLU columnar HTAP), [sap-adaptive-server](engines/sap-adaptive-server.md) (Sybase ASE), [informix](engines/informix.md),  [ingres](engines/ingres.md)/[openedge](engines/openedge.md) (choose only if the app already mandates it). ❌ cost and shrinking talent pools.
- **Embedded / single-file / edge:** [sqlite](engines/sqlite.md) (the default; single-writer), [h2](engines/h2.md)/[hypersql](engines/hypersql.md)/[apache-derby](engines/apache-derby.md) (JVM/test), [firebird](engines/firebird.md) (server *or* embedded), [sap-sql-anywhere](engines/sap-sql-anywhere.md) (edge/sync), [realm](engines/realm.md)/[pouchdb](engines/pouchdb.md) (mobile/offline), [microsoft-access](engines/microsoft-access.md) (desktop/file, single-user). See [embedded-databases](concepts/embedded-databases.md). ❌ not multi-writer servers.
- **Managed, minimal ops (cloud OK):** hyperscaler-managed relational — [amazon-aurora](engines/amazon-aurora.md) (MySQL/Postgres-compatible, disaggregated storage), [microsoft-azure-sql-database](engines/microsoft-azure-sql-database.md) (managed SQL Server), [alibaba-cloud-polardb](engines/alibaba-cloud-polardb.md), [edb-postgres](engines/edb-postgres.md). ❌ cloud lock-in; AWS/Azure-only.
  - **Hosted Postgres — baselines:** **Amazon RDS** / **Google Cloud SQL** / **Azure Database for PostgreSQL** run stock community Postgres (you pick the version, they handle patching/backups/HA); **AlloyDB** is Google's Postgres-compatible engine with separated storage/compute + a columnar engine for HTAP. ❌ still per-cloud lock-in; not as cheap-at-small as the serverless players.
  - **Serverless / scale-to-zero + DB branching:** [neon](engines/neon.md) — separated storage/compute, copy-on-write **database branching**, scale-to-zero, Apache-2.0 (Databricks-owned since 2025) · **Supabase** — a Firebase-style backend-as-a-service on *real* Postgres (auth, realtime, storage, auto REST/GraphQL via PostgREST) on dedicated instances with no per-query cold start. ❌ Neon trades a small cold-start latency for scale-to-zero; Supabase is a whole app platform, not just a DB.
  - **Vanilla Postgres, multi-cloud, low lock-in:** **Crunchy Bridge** / **Snowflake Postgres** (enterprise-grade Postgres from Crunchy Data, Snowflake-owned since 2025) · **Aiven** (one console across AWS/GCP/Azure) · **Render** / **Railway** / **Fly.io** / **DigitalOcean** (developer-platform managed Postgres). ❌ thinner enterprise/DBA tooling than the hyperscalers; smaller-vendor longevity risk.

### Need to scale OLTP horizontally or across regions?
- **Distributed SQL (NewSQL), strong consistency:** [cockroachdb](engines/cockroachdb.md) (serializable, Postgres-wire, survives region loss, BSL), [yugabytedb](engines/yugabytedb.md) (Postgres-wire, Apache-2.0, HLC clocks), [google-cloud-spanner](engines/google-cloud-spanner.md) (strict serializability via TrueTime, managed-only), [tidb](engines/tidb.md) (MySQL-wire, HTAP), [oceanbase](engines/oceanbase.md) (financial-grade, MySQL/Oracle-compat). ❌ all pay a consensus-latency tax ([consensus-raft-paxos](concepts/consensus-raft-paxos.md)); overkill below ~single-node-saturation scale.
- **Shard an existing Postgres/MySQL:** [citus](engines/citus.md) (Postgres extension; cross-shard reads lack a distributed snapshot), [planetscale](engines/planetscale.md) (managed Vitess MySQL/Postgres; cross-shard txns best-effort). ❌ you must pick shard keys well — see [sharding-partitioning](concepts/sharding-partitioning.md).
- **Strict-serializable + immutability/audit:** [datomic](engines/datomic.md) (Datalog, time-travel, Jepsen-clean). ❌ closed-source, single-writer transactor.


---
## 2. Document store (JSON, flexible schema)

See [document-data-model](concepts/document-data-model.md).

- **General document DB:** [mongodb](engines/mongodb.md) — dominant, easy scale-out. ❌ safe consistency needs non-default `w:majority` + majority/snapshot reads; weak defaults lost data in every [jepsen](concepts/jepsen.md) test.
- **Managed / serverless:** [google-cloud-firestore](engines/google-cloud-firestore.md) (serializable, mobile sync), [amazon-documentdb](engines/amazon-documentdb.md) (Mongo-API, real feature gaps), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md) (multi-API, five consistency levels), [ibm-cloudant](engines/ibm-cloudant.md), [cloudkit](engines/cloudkit.md) (Apple-only). ❌ lock-in.
- **Offline-first / sync:** [couchdb](engines/couchdb.md) / [pouchdb](engines/pouchdb.md) / [ibm-cloudant](engines/ibm-cloudant.md) (CouchDB replication protocol), [couchbase](engines/couchbase.md) (memory-first, SQL++), [firebase-realtime-database](engines/firebase-realtime-database.md) (small realtime apps), [realm](engines/realm.md) (mobile). ❌ AP/eventual; app-resolved conflicts (see [crdts](concepts/crdts.md)).
- **.NET-native:** [ravendb](engines/ravendb.md). ❌ Jepsen found isolation claims overstated.

---
## 3. Analytics / reporting / data warehouse (OLAP)

Column-stores and MPP — see [columnar-storage](concepts/columnar-storage.md). **Anti-pattern for all of these: OLTP / many small writes / point lookups.**

- **Managed cloud warehouse, near-zero tuning:** [snowflake](engines/snowflake.md) (storage/compute separation, easy to overspend), [google-bigquery](engines/google-bigquery.md) (serverless, billed by bytes scanned), [amazon-redshift](engines/amazon-redshift.md), [microsoft-fabric](engines/microsoft-fabric.md) / [microsoft-azure-synapse-analytics](engines/microsoft-azure-synapse-analytics.md) (Synapse now legacy → Fabric). ❌ cost surprises; vendor lock-in.
- **Lakehouse (own your open storage):** Architecture, not a product — open columnar files + an [open table format](concepts/open-table-formats.md) + a [catalog](concepts/data-catalog.md), queried by many decoupled engines. See [lakehouse](concepts/lakehouse.md). Decide three things:
  - **Table format** — [apache-iceberg](engines/apache-iceberg.md) (vendor-neutral default, broadest engine support) · [delta-lake](engines/delta-lake.md) (if you're on [databricks](engines/databricks.md)/Spark; UniForm exposes Iceberg metadata) · [apache-hudi](engines/apache-hudi.md) / [apache-paimon](engines/apache-paimon.md) (streaming/CDC **upserts**: Hudi batch-leaning, Paimon Flink-native LSM). ❌ table-format ACID is *table-level optimistic*, not row-level — bad for OLTP.
  - **Engine over it** — [databricks](engines/databricks.md) (managed Spark+Delta), [trino](engines/trino.md)/[presto](engines/presto.md) (federated SQL), [apache-spark-sql](engines/apache-spark-sql.md) (batch/ETL), [apache-impala](engines/apache-impala.md) (MPP low-latency SQL on HDFS/Iceberg), [apache-hive](engines/apache-hive.md) (batch SQL, the legacy workhorse), [apache-drill](engines/apache-drill.md) (schema-free SQL over files), [dremio](engines/dremio.md) (Arrow, BI acceleration), [clickhouse](engines/clickhouse.md)/[starrocks](engines/starrocks.md) (fast reads), [duckdb](engines/duckdb.md) (single-node), [datafusion](engines/datafusion.md) (embeddable Rust/Arrow engine you build on), or even [snowflake](engines/snowflake.md) reading Iceberg. ❌ these are compute layers — transactions come from the table format, not the engine.
  - **Catalog** — [apache-polaris](engines/apache-polaris.md) (open Iceberg REST, vendor-neutral) · [unity-catalog](engines/unity-catalog.md) (Databricks governance) · [hive-metastore](engines/hive-metastore.md) (legacy lingua franca). The catalog arbitrates multi-engine ACID — all writers must share one.
- **Self-hosted / real-time OLAP:** [clickhouse](engines/clickhouse.md) (blazing scans, eventually consistent), [starrocks](engines/starrocks.md) / [apache-druid](engines/apache-druid.md) (sub-second slice-and-dice), [exasol](engines/exasol.md) / [vertica](engines/vertica.md) / [greenplum](engines/greenplum.md) / [sap-iq](engines/sap-iq.md) / [teradata](engines/teradata.md) / [netezza](engines/netezza.md) / [gbase](engines/gbase.md) (MPP, legacy→modern spectrum).
- **HTAP (one system for both):** [singlestore](engines/singlestore.md) (RC only), [sap-hana](engines/sap-hana.md) (RAM-priced), [tidb](engines/tidb.md) (row+columnar replica), [oracle](engines/oracle.md)/[microsoft-sql-server](engines/microsoft-sql-server.md) columnstore. Always verify the **physical separation** mechanism — see [oltp-olap-htap](concepts/oltp-olap-htap.md).

---

## 4. Key-value, wide-column & coordination

See [key-value-store](concepts/key-value-store.md). **Most of these are caches, not systems of record.**

- **In-memory cache / data structures:** [redis](engines/redis.md) / [valkey](engines/valkey.md) (Valkey = BSD fork after Redis relicensed), [memcached](engines/memcached.md) (minimalist, volatile), [hazelcast](engines/hazelcast.md) / [apache-ignite](engines/apache-ignite.md) / [gemfire](engines/gemfire.md) / [oracle-coherence](engines/oracle-coherence.md) / [ehcache](engines/ehcache.md) / [infinispan](engines/infinispan.md) (JVM data grids). ❌ async replication → poor system of record.
- **Durable, scale-out KV:** [amazon-dynamodb](engines/amazon-dynamodb.md) (serverless, single-digit-ms, design for access patterns), [aerospike](engines/aerospike.md) (flash-optimized sub-ms, multi-record ACID since 8.0), [riak-kv](engines/riak-kv.md) (Dynamo-style + [crdts](concepts/crdts.md); ❌ LWW default silently drops writes), [oracle-nosql](engines/oracle-nosql.md), [google-cloud-datastore](engines/google-cloud-datastore.md) (managed document-KV; ❌ every query needs a pre-built index), [microsoft-azure-table-storage](engines/microsoft-azure-table-storage.md) (cheap managed KV; ❌ PartitionKey is a one-way design door).
- **Wide-column / column-family (huge write throughput, sparse tables):** [apache-cassandra](engines/apache-cassandra.md) (AP, leaderless, tunable consistency, linear write scale; ❌ no multi-row ACID, LWW drops concurrent writes under clock skew), [scylladb](engines/scylladb.md) (C++ Cassandra-compatible, lower p99; ❌ source-available relicense), [datastax-enterprise](engines/datastax-enterprise.md) (supported Cassandra + search/analytics/graph), [apache-hbase](engines/apache-hbase.md) / [google-cloud-bigtable](engines/google-cloud-bigtable.md) (CP, strong per-row consistency on HDFS/Colossus; ❌ row-key hotspotting and no secondary indexes), [apache-accumulo](engines/apache-accumulo.md) (cell-level security), [apache-phoenix](engines/apache-phoenix.md) (SQL skin over HBase). ❌ all are wrong for ad-hoc queries, joins, or multi-row transactions — you design around the row/partition key up front.
- **Strongly-consistent config/coordination:** [etcd](engines/etcd.md) (strict-serializable Raft; the brain of Kubernetes). ❌ small critical data only, not a general DB.
- **Embedded storage engine (inside your app or another DB):** [rocksdb](engines/rocksdb.md) / [leveldb](engines/leveldb.md) (LSM), [lmdb](engines/lmdb.md) / [oracle-berkeley-db](engines/oracle-berkeley-db.md) (B-tree). See [lsm-vs-btree](concepts/lsm-vs-btree.md), [embedded-databases](concepts/embedded-databases.md).

---

## 5. Graph

See [graph-data-model](concepts/graph-data-model.md).

- **Property graph, deep traversals:** [neo4j](engines/neo4j.md) (market leader, Cypher, index-free adjacency). ❌ single-leader, read-committed, doesn't shard a connected graph.
- **In-memory / real-time graph:** [memgraph](engines/memgraph.md) (Neo4j-compatible Cypher). ❌ HA is Enterprise-only.
- **Embedded / in-process (no server):** [ladybugdb](engines/ladybugdb.md) — the "SQLite/DuckDB for graphs": embedded property-graph engine, Cypher, columnar + vectorized for fast analytical traversals, with native SQLite interop; ships inside your app/agent process (popular for AI-agent memory). Community fork continuing **Kuzu** after it was archived Oct 2025. ❌ single-node embedded, young/just-forked — no HA/clustering, not a multi-writer server.
- **Distributed / huge graphs:** [janusgraph](engines/janusgraph.md) (over Cassandra/HBase/Bigtable; ❌ not ACID on common backends), [nebulagraph](engines/nebulagraph.md) (trillions of edges; ❌ no general ACID), [tigergraph](engines/tigergraph.md) (MPP analytics).
- **Managed:** [amazon-neptune](engines/amazon-neptune.md) (property graph + RDF). ❌ single-writer, AWS lock-in.
- **RDF / knowledge graph / SPARQL + reasoning:** [graphdb](engines/graphdb.md), [stardog](engines/stardog.md), [virtuoso](engines/virtuoso.md), [apache-jena-tdb](engines/apache-jena-tdb.md) (embedded, single-node). ❌ triplestores, not general app DBs.

---

## 6. Time-series / metrics / IoT

See [time-series-storage](concepts/time-series-storage.md).

- **Metrics & monitoring:** [prometheus](engines/prometheus.md) (pull-scrape, PromQL; ❌ single-node, not durable alone) → scale/long-term with [victoriametrics](engines/victoriametrics.md) (high-cardinality, ~1s data-loss window). [graphite](engines/graphite.md) (legacy RRD-style).
- **General TSDB with SQL:** [timescaledb](engines/timescaledb.md) (Postgres extension, full ACID; ❌ single-node now), [influxdb](engines/influxdb.md) (v3 = columnar/Parquet rewrite), [questdb](engines/questdb.md) (fast ingest; ❌ HA Enterprise-only).
- **IoT/industrial:** [tdengine](engines/tdengine.md), [apache-iotdb](engines/apache-iotdb.md), [dolphindb](engines/dolphindb.md). **Finance/tick data:** [kdb](engines/kdb.md) (the standard; ❌ closed, idiosyncratic q language, non-ACID), [dolphindb](engines/dolphindb.md).
- **Event analytics over time:** [apache-druid](engines/apache-druid.md), [microsoft-azure-data-explorer](engines/microsoft-azure-data-explorer.md) (Kusto/KQL), [clickhouse](engines/clickhouse.md).

---

## 7. Full-text search

See [full-text-search](concepts/full-text-search.md). **All are secondary indexes fed from a durable primary — not systems of record** (e.g. [elasticsearch](engines/elasticsearch.md) lost acknowledged writes under partition, [jepsen](concepts/jepsen.md)).

- **Self-hosted, Lucene-based** (Lucene = the open-source Java full-text indexing library underneath all three): [elasticsearch](engines/elasticsearch.md) — the engine at the heart of the **ELK Stack** (Elasticsearch store + **L**ogstash/Beats ingest + **K**ibana viz; now SSPL/AGPL; logs/observability/SIEM/vectors) · [opensearch](engines/opensearch.md) (Apache-2.0 fork, with OpenSearch Dashboards + Data Prepper) · [apache-solr](engines/apache-solr.md) (mature, CP SolrCloud).
- **Managed / hosted:** [algolia](engines/algolia.md) (sub-50ms instant search), [microsoft-azure-ai-search](engines/microsoft-azure-ai-search.md) (full-text + vector + RAG), [coveo](engines/coveo.md) (enterprise/commerce), [amazon-cloudsearch](engines/amazon-cloudsearch.md) (legacy).
- **Lightweight / single-node:** [meilisearch](engines/meilisearch.md) (typo-tolerant; ❌ weak HA/scale), [sphinx](engines/sphinx.md) (frozen → Manticore fork). **Logs/SIEM at scale:** [splunk](engines/splunk.md) (schema-on-read; ❌ expensive) — the open(-ish) alternatives are the **ELK Stack** or [opensearch](engines/opensearch.md).

---

## 8. Vector / AI retrieval (RAG)

See [vector-search-ann](concepts/vector-search-ann.md). Decide: **dedicated vector DB** vs **add vectors to a DB you already run** (pgvector in [postgresql](engines/postgresql.md), [redis](engines/redis.md), [mongodb](engines/mongodb.md), [elasticsearch](engines/elasticsearch.md) — usually enough until high scale/QPS).

- **Embedded / in-process (no server):** [lancedb](engines/lancedb.md) — the "SQLite for vector + AI data": Apache-2.0, ships inside your app/Lambda/notebook and keeps **vectors + metadata + multimodal blobs** in one versioned columnar Lance table, **local-disk-first** (sub-10ms p95 on NVMe) or over the same table on S3/GCS/Azure. ❌ a single OSS process tops out ~10–50 QPS and *cold object-store* reads cost hundreds of ms — high-QPS low-latency serving needs the paid Enterprise tier; not a transactional system of record.
- **Managed/serverless:** [pinecone](engines/pinecone.md) (API-only, no self-host). ❌ eventually consistent, lock-in.
- **Open-source, scale:** [milvus](engines/milvus.md) (billion-scale, disaggregated), [qdrant](engines/qdrant.md) (rich payload filtering, Rust), [weaviate](engines/weaviate.md) (hybrid BM25+vector, RAG modules), [chroma](engines/chroma.md) (dev-first, embeddable → serverless cloud). ❌ none are ACID systems of record; pair with a primary store.

---

## 9. Specialized & "it's not really a database"

- **Spatial / GIS:** [postgis](engines/postgis.md) (the de facto open-source GIS engine, on [postgresql](engines/postgresql.md)), [spatialite](engines/spatialite.md) (embedded, on [sqlite](engines/sqlite.md)). ❌ PostGIS has no native spatial sharding.
- **Stream processing / streaming / CDC:** see the dedicated **Streaming** section (§10) below.
- **Multidimensional/MOLAP (financial planning):** [oracle-essbase](engines/oracle-essbase.md). ❌ single-node, proprietary.
- **Content repository (CMS/DAM):** [apache-jackrabbit](engines/apache-jackrabbit.md) (JCR; engine under Adobe AEM).
- **Multi-model "do several at once":** [arangodb](engines/arangodb.md) (doc+graph+KV, one query language; ❌ cluster ACID only within a shard), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md), [marklogic](engines/marklogic.md) (doc+RDF+search, real multi-doc ACID; ❌ costly), [intersystems-iris](engines/intersystems-iris.md) (healthcare; ❌ defaults to READ UNCOMMITTED), [fauna](engines/fauna.md) (❌ service shut down 2025). Read [multi-model](concepts/multi-model.md) first — one model is usually first-class and the rest bolted on.
- **MultiValue / mainframe / legacy** (choose only if the app already requires it): [adabas](engines/adabas.md), [unidata-universe](engines/unidata-universe.md), [maxdb](engines/maxdb.md), [dbase](engines/dbase.md), [filemaker](engines/filemaker.md), [4d](engines/4d.md), [openedge](engines/openedge.md), [ingres](engines/ingres.md), [informix](engines/informix.md), [interbase](engines/interbase.md), [sap-adaptive-server](engines/sap-adaptive-server.md).

---

## 10. Streaming, real-time & event-driven

Moving and acting on events as they happen. These compose into a pipeline — pick one per layer, not one tool for all of it. See [streaming-platforms](concepts/streaming-platforms.md), [streaming-databases](concepts/streaming-databases.md), [change-data-capture](concepts/change-data-capture.md), [real-time-olap](concepts/real-time-olap.md).

- **Event log / transport (the backbone):** [apache-kafka](engines/apache-kafka.md) (de facto standard, huge ecosystem) · [apache-pulsar](engines/apache-pulsar.md) (broker/storage separation, multi-tenant, geo) · [redpanda](engines/redpanda.md) (Kafka-API, C++, no JVM/ZooKeeper, lower p99; ❌ single-vendor BSL). ❌ none is a queryable database or system of record — it's a replayable log.
- **Get changes OUT of an operational DB (CDC):** [debezium](engines/debezium.md) (log-based, the standard) → onto Kafka or into [apache-flink](engines/apache-flink.md). Use for replication, cache/[search](engines/elasticsearch.md) sync, and feeding the lake. ❌ ordering/exactly-once only hold end-to-end; sinks must dedupe/upsert.
- **Transform / compute on streams:** [apache-flink](engines/apache-flink.md) (stateful, event-time, exactly-once — the heavyweight), Kafka Streams / ksqlDB (Kafka-native). ❌ processors aren't queryable stores by themselves.
- **Continuously-fresh SQL views (streaming databases):** [materialize](engines/materialize.md) (Postgres-wire, strict-serializable incremental views) · [risingwave](engines/risingwave.md) (Postgres-wire, state on object storage) · [ksqldb](engines/ksqldb.md) (Kafka-native; now largely superseded by Flink). Use when you want `CREATE MATERIALIZED VIEW` that stays current. ❌ not for heavy ad-hoc OLAP.
- **Serve fresh data for ad-hoc analytics (real-time OLAP sinks):** [apache-pinot](engines/apache-pinot.md) (high-QPS user-facing) · [apache-druid](engines/apache-druid.md) (time-series slice-and-dice) · [clickhouse](engines/clickhouse.md) (general fast scans) · [apache-doris](engines/apache-doris.md) / [starrocks](engines/starrocks.md) (MPP with real JOINs). See [real-time-olap](concepts/real-time-olap.md). ❌ append/ingest oriented — not OLTP, not a system of record.
- **Mutable analytic storage:** [apache-kudu](engines/apache-kudu.md) (fast scans + random updates, paired with Impala/Spark) — when lake table formats' update story is too coarse.

## Cross-cutting filters (apply to any leaf above)

- **License red flags:** post-2018 relicensing to source-available (SSPL: [mongodb](engines/mongodb.md), [elasticsearch](engines/elasticsearch.md); BSL: [cockroachdb](engines/cockroachdb.md), [scylladb](engines/scylladb.md)) — if you need permissive OSS or to offer it as a service, prefer [postgresql](engines/postgresql.md), [valkey](engines/valkey.md), [opensearch](engines/opensearch.md), [clickhouse](engines/clickhouse.md), [milvus](engines/milvus.md). See [license-taxonomy](concepts/license-taxonomy.md).
- **Managed-only (no self-host):** [snowflake](engines/snowflake.md), [google-bigquery](engines/google-bigquery.md), [google-cloud-spanner](engines/google-cloud-spanner.md), [amazon-dynamodb](engines/amazon-dynamodb.md), [pinecone](engines/pinecone.md), [microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md), [cloudkit](engines/cloudkit.md) — accept lock-in or rule them out.
- **"Strongly consistent" claims:** verify against [jepsen](concepts/jepsen.md) and check whether safe behavior needs non-default settings — it often does ([mongodb](engines/mongodb.md), [redis](engines/redis.md), [mariadb](engines/mariadb.md) Galera, [riak-kv](engines/riak-kv.md)).
- **Lakehouse interop & lock-in:** if you want many engines on one copy of data, standardize on [apache-iceberg](engines/apache-iceberg.md) + an open [catalog](concepts/data-catalog.md) ([apache-polaris](engines/apache-polaris.md)) over Delta+Unity unless you're committed to [databricks](engines/databricks.md). All writers must share one catalog or multi-engine ACID breaks.
- **ACID vs BASE framing:** don't accept the label — pin the concrete guarantee (default+achievable isolation, CAP/PACELC, tunable?, data-loss window). See [acid-vs-base](concepts/acid-vs-base.md).

---

## Maintenance

Re-derive the question order and leaves as coverage grows or engines change status; record changes in [log](log.md) under `decision-guide`. This version derived from 150 engine pages researched 2026-06-04.
