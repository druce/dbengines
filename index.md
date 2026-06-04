# Database Engines — Index

Catalog of all engine pages, grouped by primary data model, sorted by db-engines rank within each
group. A multi-model engine is listed under its primary model with "(also: …)".

Format: `- **[slug](engines/slug.md)** (rank N) — one-liner.`

## Relational

- **[oracle](engines/oracle.md)** (rank 1) — Heavyweight commercial multi-model RDBMS; deep OLTP/HTAP features and MVCC, but snapshot-isolation-as-"serializable" and per-core options-priced licensing dominate the decision.
- **[mysql](engines/mysql.md)** (rank 2) — Ubiquitous open-source OLTP relational DB (InnoDB/MVCC); battle-tested, but default "REPEATABLE READ" is weaker than its name (Jepsen).
- **[microsoft-sql-server](engines/microsoft-sql-server.md)** (rank 3) — Microsoft's flagship commercial RDBMS; mature single-node OLTP/HTAP with T-SQL, locking READ COMMITTED by default, Always On HA, now on Linux.
- **[postgresql](engines/postgresql.md)** (rank 4) — Battle-tested permissive-licensed relational DB; the safe default for OLTP, with a deep extension ecosystem (JSONB, PostGIS, pgvector) and real SERIALIZABLE via SSI.
- **[snowflake](engines/snowflake.md)** (rank 6) — Managed cloud data warehouse that pioneered storage/compute separation; elastic per-second compute over columnar object storage, near-zero tuning, easy to overspend.
- **[ibm-db2](engines/ibm-db2.md)** (rank 9) — Mature IBM commercial RDBMS (z/OS + LUW); solid ACID OLTP plus optional BLU columnar analytics, but proprietary and legacy-leaning outside IBM shops.
- **[sqlite](engines/sqlite.md)** (rank 11) — Zero-config, single-file embedded relational engine; serializable, single-writer, public domain, and the most-deployed DB on earth.
- **[mariadb](engines/mariadb.md)** (rank 13) — GPLv2 MySQL fork with pluggable engines and Galera multi-primary clustering; Jepsen (2026) found Galera far weaker than its claimed isolation.
- **[microsoft-azure-sql-database](engines/microsoft-azure-sql-database.md)** (rank 14) — Managed PaaS SQL Server engine on Azure; RCSI-default, ADR-always-on, Hyperscale decouples compute/storage to 128 TB; managed-only and Azure-locked.
- **[apache-hive](engines/apache-hive.md)** (rank 15) — Original SQL-on-Hadoop batch warehouse; a query layer plus metastore over files, with snapshot-isolation ACID on managed ORC tables only.
- **[microsoft-access](engines/microsoft-access.md)** (rank 17) — File-based Windows desktop relational DB with a forms/reports RAD layer; great for single-user and tiny LAN workgroups, but a shared file (not a server) that corrupts under concurrent network writes.
- **[google-bigquery](engines/google-bigquery.md)** (rank 19) — Serverless, columnar, separated storage/compute cloud data warehouse on GCP; ANSI SQL, billed by bytes scanned or slots; OLAP not OLTP.
- **[sap-hana](engines/sap-hana.md)** (rank 22) — In-memory columnar HTAP relational engine under SAP's S/4HANA stack; proprietary, RAM-priced, SERIALIZABLE is really snapshot isolation.
- **[teradata](engines/teradata.md)** (rank 23) — Original shared-nothing MPP data warehouse; lock-based serializable SQL at petabyte scale, now cloud-consumption packaged.
- **[filemaker](engines/filemaker.md)** (rank 24) — Apple/Claris proprietary low-code RAD platform with a bundled single-server relational engine; build SMB business apps fast, not a scalable standalone DBMS.
- **[sap-adaptive-server](engines/sap-adaptive-server.md)** (rank 25) — Mature lock-based OLTP relational engine (former Sybase ASE); T-SQL, single-node with HADR failover, now in SAP maintenance mode.
- **[clickhouse](engines/clickhouse.md)** (rank 26) — Apache-2.0 columnar OLAP engine for blazing analytical scans; eventually consistent, snapshot isolation, async updates, not OLTP.
- **[apache-spark-sql](engines/apache-spark-sql.md)** (rank 27) — Distributed OLAP SQL/dataframe query engine over a lakehouse; storage-compute separated, ACID only via Delta/Iceberg, not a database.
- **[postgis](engines/postgis.md)** (rank 28) — Spatial extender turning PostgreSQL into the de facto open-source GIS engine; full ACID and SQL spatial joins via GiST indexes, but no native spatial sharding.
- **[microsoft-fabric](engines/microsoft-fabric.md)** (rank 33) — Microsoft's SaaS analytics platform: T-SQL Warehouse, Spark Lakehouse, KQL real-time and Power BI sharing one Delta-Parquet lake (OneLake), billed by shared capacity units.
- **[firebird](engines/firebird.md)** (rank 34) — Lightweight open-source SQL RDBMS forked from InterBase; multi-generational MVCC, tiny embeddable footprint, but single-node with a niche ecosystem.
- **[microsoft-azure-synapse-analytics](engines/microsoft-azure-synapse-analytics.md)** (rank 35) — Azure's MPP columnar cloud data warehouse (former SQL DW) with serverless lake-SQL and Spark; in maintenance mode as Microsoft pushes Fabric.
- **[amazon-redshift](engines/amazon-redshift.md)** (rank 37) — AWS columnar MPP cloud data warehouse; Postgres-dialect SQL for OLAP, RA3 storage/compute separation and a serverless mode.
- **[informix](engines/informix.md)** (rank 38) — Mature low-admin object-relational OLTP engine with native time-series and spatial; proprietary (IBM-owned, HCL-developed) with a shrinking talent pool.
- **[apache-impala](engines/apache-impala.md)** (rank 40) — Open-source MPP SQL-on-Hadoop/lakehouse query engine for fast interactive OLAP over HDFS/S3/Kudu/Iceberg; owns no storage, no real multi-statement transactions.
- **[duckdb](engines/duckdb.md)** (rank 42) — Embedded columnar OLAP engine ("SQLite for analytics"): vectorized, single-file, MIT-licensed, single-node only.
- **[amazon-aurora](engines/amazon-aurora.md)** (rank 44) — AWS's MySQL/PostgreSQL-compatible OLTP engine with disaggregated, 6-way quorum-replicated cloud storage; single-writer, fast failover, AWS-only.
- **[vertica](engines/vertica.md)** (rank 47) — Shared-nothing columnar MPP analytics warehouse descended from C-Store; uses projections instead of indexes, with an Eon mode separating compute from S3-style communal storage.
- **[dbase](engines/dbase.md)** (rank 49) — Original 1980s PC database; a single-file xBase engine whose .dbf format outlived the now-niche product.
- **[h2](engines/h2.md)** (rank 50) — Pure-Java embedded/server SQL database; the standard in-process test DB, not a production HA system.
- **[trino](engines/trino.md)** (rank 53) — Storage-less distributed MPP SQL engine that federates queries across data lakes and databases; an analytics query layer, not a database.
- **[netezza](engines/netezza.md)** (rank 55) — IBM's FPGA-accelerated MPP analytics appliance; scan-optimized SQL warehousing, no indexes, now also a cloud/OpenShift service.
- **[presto](engines/presto.md)** (rank 59) — Facebook-born storage-less MPP SQL engine that federates queries across data lakes and external sources; Apache-2.0, now overshadowed by its faster-moving Trino fork.
- **[greenplum](engines/greenplum.md)** (rank 60) — PostgreSQL-derived shared-nothing MPP analytics warehouse; mature OLAP workhorse that Broadcom closed-sourced in 2024, spawning Apache Cloudberry and EDB forks.
- **[cockroachdb](engines/cockroachdb.md)** (rank 71) — Geo-distributed, Postgres-wire NewSQL; serializable-by-default over Raft-replicated auto-sharded ranges; survives zone/region loss (RPO≈0) at a consensus-latency tax.
- **[tidb](engines/tidb.md)** (rank 73) — MySQL-compatible distributed NewSQL/HTAP DB; Raft-replicated row store (TiKV) plus columnar replica (TiFlash), auto-sharding and snapshot isolation.
- **[interbase](engines/interbase.md)** (rank 74) — Veteran embeddable/server SQL RDBMS that pioneered MVCC; now a niche Embarcadero commercial engine with column-level encryption and Change Views CDC.
- **[openedge](engines/openedge.md)** (rank 79) — Progress's proprietary 4GL-plus-RDBMS application platform; a single-leader OLTP relational engine adopted because the app is already written in ABL (e.g. QAD ERP).
- **[alibaba-cloud-polardb](engines/alibaba-cloud-polardb.md)** (rank 81) — Alibaba's Aurora-style cloud-native relational DB: one writer + up to 15 readers over shared storage (PolarFS), MySQL/PostgreSQL/Oracle-compatible, managed-only with tunable replica consistency.
- **[sap-sql-anywhere](engines/sap-sql-anywhere.md)** (rank 85) — Self-managing embeddable relational engine for occasionally-connected edge/mobile apps, with mature MobiLink/SQL Remote sync; default isolation is READ UNCOMMITTED.
- **[microsoft-azure-data-explorer](engines/microsoft-azure-data-explorer.md)** (rank 87) — Managed Azure columnar analytics engine (Kusto/KQL) for append-only telemetry, logs, and time series; near-real-time OLAP, not OLTP.
- **[ingres](engines/ingres.md)** (rank 88) — One of the original 1970s relational databases, now a mature single-node OLTP DBMS from Actian; stable but a legacy choice.
- **[apache-derby](engines/apache-derby.md)** (rank 91) — Pure-Java embeddable SQL database (a.k.a. Java DB); fine for tests and small JVM apps, but retired to read-only in Oct 2025.
- **[singlestore](engines/singlestore.md)** (rank 93) — Distributed MySQL-compatible HTAP SQL engine fusing rowstore + columnstore into one "Universal Storage" table; fast analytics + ingest, but isolation tops out at READ COMMITTED.
- **[google-cloud-spanner](engines/google-cloud-spanner.md)** (rank 94) — Google's globally-distributed relational DB delivering strict serializability across regions via TrueTime clocks; CP, managed-only, lock-in heavy.
- **[hypersql](engines/hypersql.md)** (rank 99) — Pure-Java embeddable SQL database (HSQLDB) with deep SQL-standard coverage; the JVM's go-to in-memory test/desktop DB, single-node only.
- **[oceanbase](engines/oceanbase.md)** (rank 109) — Ant/Alibaba distributed SQL DB; Paxos-replicated, MySQL/Oracle-compatible, built for financial-grade OLTP at extreme scale.
- **[sap-iq](engines/sap-iq.md)** (rank 113) — Mature columnar analytic RDBMS (ex-Sybase IQ) with a shared-disk multiplex grid; an OLAP data-warehouse engine, not for OLTP.
- **[citus](engines/citus.md)** (rank 116) — PostgreSQL extension that shards tables across worker nodes for scale-out OLTP and real-time analytics; cross-shard writes are atomic via 2PC but reads lack a distributed snapshot.
- **[yugabytedb](engines/yugabytedb.md)** (rank 117) — Spanner-inspired distributed SQL with a PostgreSQL-wire-compatible query layer over a Raft-replicated, RocksDB-based shard store; CP, HLC clocks, Apache 2.0.
- **[apache-phoenix](engines/apache-phoenix.md)** (rank 119) — SQL + JDBC relational layer over Apache HBase; great if you already run HBase, heavy operational tax otherwise, ACID transactions still beta.
- **[gbase](engines/gbase.md)** (rank 120) — Chinese-domestic MPP columnar analytical warehouse (GBase 8a); a Greenplum/Vertica-class OLAP engine for 信创 government/telecom/bank deployments, plus unrelated OLTP (8s) and distributed (8c) products under the same brand.
- **[4d](engines/4d.md)** (rank 122) — Decades-old proprietary relational DB fused with its own 4GL/IDE for business apps; single-server, manual record locking, async log-shipping HA.
- **[percona-server-for-mysql](engines/percona-server-for-mysql.md)** (rank 129) — GPL MySQL fork bundling Enterprise-equivalent features (hot backups, audit, thread pool, encryption, MyRocks) and deep instrumentation for free.
- **[maxdb](engines/maxdb.md)** (rank 134) — SAP's legacy single-node ANSI-SQL-92 OLTP RDBMS (ex-Adabas D / SAP DB), now end-of-life in favor of HANA.
- **[exasol](engines/exasol.md)** (rank 136) — Proprietary in-memory shared-nothing MPP columnar SQL warehouse for fast analytics; auto-indexing and self-tuning, but closed-source and OLAP-only.
- **[starrocks](engines/starrocks.md)** (rank 139) — Vectorized MPP columnar OLAP warehouse for sub-second real-time analytics and lakehouse querying (Iceberg/Hudi/Hive/Delta); RC-only transactions.
- **[planetscale](engines/planetscale.md)** (rank 142) — Managed sharded MySQL on Vitess (now also Postgres) with branch-and-deploy schema workflow; cross-shard transactions are best-effort, and it's paid-only.
- **[edb-postgres](engines/edb-postgres.md)** (rank 144) — EnterpriseDB's commercial Postgres distribution; Oracle compatibility, TDE, and async multi-master replication bolted onto upstream PostgreSQL.
- **[datomic](engines/datomic.md)** (rank 150) — Immutable, time-travel relational DB with Datalog queries, in-process query engine, and a single-writer transactor; serializable (Jepsen-clean), free-of-charge but closed-source.

## Document

- **[mongodb](engines/mongodb.md)** (rank 5) — Dominant document (BSON) database; easy scale-out and flexible schema, but safe consistency/durability needs non-default majority concerns (Jepsen found data loss at defaults).
- **[firebase-realtime-database](engines/firebase-realtime-database.md)** (rank 36) — Google's managed single-region JSON-tree store that pushes live updates to offline-first clients; great for small realtime apps, painful past one database's scale.
- **[couchbase](engines/couchbase.md)** (rank 43) — Memory-first distributed JSON document store with SQL++ querying and integrated KV/search/analytics/vector services; fast and durable single-cluster, last-write-wins across datacenters.
- **[google-cloud-firestore](engines/google-cloud-firestore.md)** (rank 45) — Serverless GCP document DB with realtime sync, offline SDKs, and serializable transactions; great for mobile/web, wrong for joins, analytics, or per-doc hotspots.
- **[realm](engines/realm.md)** (rank 58) — Embedded object database for mobile (zero-copy mmap, live objects, MVCC); Apache-2.0 local store whose cloud sync MongoDB is shutting down (Sept 2025).
- **[couchdb](engines/couchdb.md)** (rank 61) — HTTP/JSON document store built for bidirectional multi-master replication and offline-first sync; AP, eventually consistent, document-only ACID, app-resolved conflicts.
- **[google-cloud-datastore](engines/google-cloud-datastore.md)** (rank 84) — Google's serverless auto-scaling NoSQL entity store with ACID transactions; now a legacy API surface over the Firestore storage engine.
- **[ibm-cloudant](engines/ibm-cloudant.md)** (rank 111) — Managed CouchDB-compatible JSON document DBaaS on IBM Cloud, built for offline-first sync and eventual consistency.
- **[ravendb](engines/ravendb.md)** (rank 112) — .NET-native multi-model document DB with ACID single-doc writes and eventually-consistent indexes; Jepsen found its isolation claims overstated.
- **[rethinkdb](engines/rethinkdb.md)** (rank 114) — Real-time JSON document DB with live changefeeds; Jepsen-clean for single-key linearizability but commercially dead since 2016 (now Apache 2.0 / Linux Foundation).
- **[cloudkit](engines/cloudkit.md)** (rank 115) — Apple's managed iCloud BaaS record store (public/private/shared databases); zero ops, no joins/aggregations, total Apple lock-in.
- **[amazon-documentdb](engines/amazon-documentdb.md)** (rank 124) — AWS's proprietary, Aurora-style MongoDB-API document database; managed-only, snapshot-isolation transactions, but a re-implementation with real MongoDB feature gaps.
- **[pouchdb](engines/pouchdb.md)** (rank 133) — In-browser/Node.js JSON document store that speaks the CouchDB replication protocol; the standard pick for offline-first sync apps.
- **[rockset](engines/rockset.md)** (rank 135) — Managed real-time analytics DB that auto-indexed schemaless JSON (row + columnar + inverted Converged Index) on RocksDB-Cloud for low-latency SQL; acquired by OpenAI and shut down to outside customers in 2024.

## Key-value

- **[redis](engines/redis.md)** (rank 8) — In-memory data-structure server; default cache/queue/session store, now multi-model (JSON, search, vector), but async replication makes it a poor system of record.
- **[amazon-dynamodb](engines/amazon-dynamodb.md)** (rank 18) — Fully managed serverless key-value/document store with predictable single-digit-ms latency at any scale; you design for its access patterns, not the reverse.
- **[memcached](engines/memcached.md)** (rank 39) — Minimalist multi-threaded in-memory KV cache; volatile by design, sharded entirely client-side, no persistence or replication.
- **[etcd](engines/etcd.md)** (rank 52) — Strict-serializable Raft KV store for small critical config/coordination data; the brain behind Kubernetes, not a general-purpose DB.
- **[hazelcast](engines/hazelcast.md)** (rank 68) — In-memory distributed data grid; fast AP caches by default, opt-in Raft-backed CP subsystem for linearizable locks/atomics, plus embedded stream processing.
- **[rocksdb](engines/rocksdb.md)** (rank 76) — Embeddable LSM-tree key-value engine; the single-node storage substrate inside other databases, not a database you run by itself.
- **[aerospike](engines/aerospike.md)** (rank 77) — Flash-optimized distributed KV/document store (RAM index + NVMe data) for predictable sub-ms OLTP at scale; opt-in strong consistency, multi-record ACID since 8.0.
- **[oracle-nosql](engines/oracle-nosql.md)** (rank 83) — Oracle's sharded single-master KV/JSON store on Berkeley DB JE with per-request tunable consistency/durability, but transactions limited to one shard key.
- **[ehcache](engines/ehcache.md)** (rank 89) — JVM-embedded JSR-107 key-value cache with tiered heap/off-heap/disk storage and an optional Terracotta clustered tier; a cache library, not a database of record.
- **[riak-kv](engines/riak-kv.md)** (rank 90) — Dynamo-style leaderless AP key-value store with tunable quorums and CRDTs; safe with sibling-merging but its last-write-wins default silently drops writes (Jepsen: up to 91% loss).
- **[gemfire](engines/gemfire.md)** (rank 102) — Java in-memory data grid (OSS core: Apache Geode) for low-latency caching, partitioned regions, and WAN replication; Read Committed, ACID only on colocated data, not a SQL/analytics DB.
- **[valkey](engines/valkey.md)** (rank 106) — Linux Foundation BSD-licensed fork of Redis 7.2.4; same in-memory KV engine and best-effort-cache consistency, with added multithreaded I/O.
- **[lmdb](engines/lmdb.md)** (rank 125) — Embedded copy-on-write B+tree KV store; lock-free MVCC readers, single writer, crash-proof by design, no compaction or WAL.
- **[infinispan](engines/infinispan.md)** (rank 130) — Apache-licensed JVM in-memory data grid for distributed caching, session clustering, and JCache; cache first, database second.
- **[leveldb](engines/leveldb.md)** (rank 132) — Google's lightweight embedded ordered key-value LSM library; single-process, library-only, permissive BSD, now barely maintained (RocksDB is its successor).
- **[oracle-coherence](engines/oracle-coherence.md)** (rank 145) — Java in-memory data grid: auto-partitioned key-value cache with synchronous backups and data-local compute; a caching tier, not a system of record.
- **[amazon-simpledb](engines/amazon-simpledb.md)** (rank 147) — AWS's original 2007 schemaless auto-indexed attribute store; string-only, 10 GB/domain, feature-frozen and closed to new customers since July 2024.
- **[oracle-berkeley-db](engines/oracle-berkeley-db.md)** (rank 149) — Mature embedded transactional KV library (B-tree/hash/queue); AGPLv3 relicensing in 2013 gutted adoption.

## Wide-column

- **[apache-cassandra](engines/apache-cassandra.md)** (rank 10) — Masterless, AP wide-column store with tunable consistency; great for write-heavy multi-DC workloads, poor for joins, ad-hoc queries, and strong transactions.
- **[apache-hbase](engines/apache-hbase.md)** (rank 31) — Bigtable-style wide-column store on HDFS; strongly consistent per row (CP), petabyte-scale, but SQL-less and operationally heavy.
- **[scylladb](engines/scylladb.md)** (rank 66) — C++ shard-per-core Cassandra clone: same CQL/data model, much lower tail latency and higher node density, AP with tunable consistency and LWT; relicensed source-available in 2025.
- **[datastax-enterprise](engines/datastax-enterprise.md)** (rank 86) — Proprietary, support-backed Apache Cassandra distribution bundling search, analytics, graph, and vector into one AP wide-column package (now an IBM product).
- **[microsoft-azure-table-storage](engines/microsoft-azure-table-storage.md)** (rank 96) — Cheap schemaless key-value/wide-column store keyed on (PartitionKey, RowKey); single-partition transactions only, no secondary indexes.
- **[google-cloud-bigtable](engines/google-cloud-bigtable.md)** (rank 104) — Google's managed, auto-sharding wide-column store (the original Bigtable as a service); single-row atomicity only, no cross-row transactions, eventual consistency across clusters.
- **[apache-accumulo](engines/apache-accumulo.md)** (rank 108) — BigTable-style wide-column store on HDFS; distinguished by per-cell visibility labels for fine-grained security (NSA-born, gov/intel niche).

## Graph

- **[neo4j](engines/neo4j.md)** (rank 20) — Market-leading native property-graph DB; Cypher + index-free adjacency make deep traversals cheap, but it is single-leader, read-committed, and does not shard a connected graph.
- **[amazon-neptune](engines/amazon-neptune.md)** (rank 100) — Managed AWS graph DB; property-graph (Gremlin/openCypher) + RDF (SPARQL) on Aurora-style storage; CP, single-writer, snapshot-isolation reads.
- **[graphdb](engines/graphdb.md)** (rank 105) — Ontotext RDF/SPARQL triplestore with materialized OWL/RDFS inference and a Raft-based HA (replication, not sharding) cluster; proprietary, read-committed isolation.
- **[apache-jena-tdb](engines/apache-jena-tdb.md)** (rank 107) — Embedded single-node RDF/SPARQL triplestore for Java; serializable single-writer ACID transactions, no clustering.
- **[stardog](engines/stardog.md)** (rank 123) — Enterprise RDF/SPARQL knowledge-graph engine with OWL reasoning, virtual graphs, and an LLM vector layer; CP, full-replication HA cluster, snapshot isolation by default.
- **[janusgraph](engines/janusgraph.md)** (rank 127) — Apache-licensed distributed Gremlin/TinkerPop property graph over pluggable Cassandra/HBase/Bigtable storage; scales horizontally but inherits eventual consistency and is not ACID on its common backends.
- **[tigergraph](engines/tigergraph.md)** (rank 128) — Native MPP property-graph DB with C++ engine and accumulator-based GSQL, built for deep multi-hop analytics at scale (proprietary; free up to 50 GB).
- **[nebulagraph](engines/nebulagraph.md)** (rank 131) — Shard-nothing distributed property graph on RocksDB + Multi-Raft; scales to trillions of edges but offers no general ACID transactions.
- **[memgraph](engines/memgraph.md)** (rank 137) — In-memory C++ property-graph DB with Neo4j-compatible Cypher; fast real-time analytics and GraphRAG, but ACID only in transactional mode and HA/auto-failover are Enterprise-only.

## Time-series

- **[influxdb](engines/influxdb.md)** (rank 30) — Popular open-source time-series DB; v3 is a Rust/Arrow/Parquet rewrite that ditches the TSM engine and Flux for columnar object-storage and SQL.
- **[prometheus](engines/prometheus.md)** (rank 46) — CNCF-graduated pull-scraping metrics TSDB with PromQL and alerting; single-node, not durable/clustered on its own.
- **[kdb](engines/kdb.md)** (rank 51) — Proprietary columnar time-series engine + q array language; the finance-industry standard for high-frequency tick data, blazing on ordered columnar scans but closed, idiosyncratic, and non-ACID.
- **[timescaledb](engines/timescaledb.md)** (rank 62) — PostgreSQL extension adding time-series hypertables, columnar compression, and continuous aggregates; full SQL/ACID but single-node since multi-node removal.
- **[dolphindb](engines/dolphindb.md)** (rank 65) — High-performance distributed columnar time-series DB with a built-in vectorized scripting language, purpose-built for quant finance and IoT tick data.
- **[graphite](engines/graphite.md)** (rank 67) — File-based RRD-style metrics store (Carbon + Whisper); fixed-size per-metric files with built-in rollups, simple but pre-allocates disk and only fakes clustering via hash-ring relays.
- **[questdb](engines/questdb.md)** (rank 78) — Single-node columnar time-series DB with fast ILP ingest and PostgreSQL-flavored SQL; replication/HA is Enterprise-only.
- **[apache-druid](engines/apache-druid.md)** (rank 82) — Distributed columnar OLAP datastore for sub-second slice-and-dice over time-stamped event data; great reads, weak joins, no record-level updates.
- **[tdengine](engines/tdengine.md)** (rank 95) — IIoT/IoT time-series DB with a one-table-per-device "supertable" model, columnar storage, and Raft replication; SQL with time-windowing but no general transactions.
- **[apache-iotdb](engines/apache-iotdb.md)** (rank 138) — Apache time-series DB for industrial IoT; columnar TsFile storage, tree/table data model, and pluggable consensus (Raft for metadata, eventual-consistency IoTConsensus for data); no multi-row transactions.
- **[victoriametrics](engines/victoriametrics.md)** (rank 141) — Cost-efficient, high-cardinality-tolerant Prometheus/Graphite-compatible TSDB (MetricsQL); AP cluster, ~1s data-loss window, no WAL.

## Search engine

- **[elasticsearch](engines/elasticsearch.md)** (rank 12) — Lucene-based distributed search/analytics engine and JSON document store; great for search, logs, and vectors, not a transactional system of record.
- **[splunk](engines/splunk.md)** (rank 16) — Proprietary schema-on-read engine for log/security/observability data; SPL search and analytics over append-only events, not a transactional DB.
- **[apache-solr](engines/apache-solr.md)** (rank 21) — Mature Apache-2.0 Lucene search server; deep faceting/geospatial plus dense-vector ANN, CP SolrCloud over ZooKeeper; secondary index, not a primary store.
- **[opensearch](engines/opensearch.md)** (rank 32) — Apache-2.0 fork of Elasticsearch 7.10; Lucene-backed distributed search, log/observability, and vector engine; near-real-time and non-transactional, not a system of record.
- **[algolia](engines/algolia.md)** (rank 54) — Hosted, in-memory keyword+vector search-as-a-service for sub-50ms instant search, priced per request and per record; a managed secondary index, not a database.
- **[microsoft-azure-ai-search](engines/microsoft-azure-ai-search.md)** (rank 57) — Managed Lucene-based full-text + vector + hybrid search on Azure; a RAG/search retrieval layer with eventual consistency and no transactions, not a system of record.
- **[sphinx](engines/sphinx.md)** (rank 63) — Veteran C++ full-text search server with a MySQL-protocol (SphinxQL) interface; OSS line frozen at GPLv2 2.x, v3+ went closed-source, live successor is the Manticore fork.
- **[coveo](engines/coveo.md)** (rank 110) — Proprietary cloud-only enterprise/commerce search-as-a-service with ML relevance and RAG; a managed secondary index over your source systems, not a self-hostable database.
- **[amazon-cloudsearch](engines/amazon-cloudsearch.md)** (rank 126) — Managed Solr-based AWS search service, now closed to new customers and superseded by OpenSearch.
- **[meilisearch](engines/meilisearch.md)** (rank 148) — MIT-licensed, single-node Rust + LMDB full-text/hybrid search engine; instant typo-tolerant search, weak on horizontal scale and HA.

## Vector

- **[pinecone](engines/pinecone.md)** (rank 48) — Managed, serverless vector DB for RAG/AI retrieval; object-storage-backed, eventually consistent, API-only, no self-hosting.
- **[milvus](engines/milvus.md)** (rank 56) — Apache-2.0 cloud-native vector DB; disaggregated storage/compute, tunable read consistency, every mainstream ANN index; built for billion-scale similarity search, not transactions.
- **[qdrant](engines/qdrant.md)** (rank 64) — Rust-built vector search engine with rich payload filtering, hybrid search, and tunable read/write consistency; Raft governs metadata, not vector data.
- **[weaviate](engines/weaviate.md)** (rank 70) — AI-native open-source (BSD) vector DB with hybrid BM25+vector search and RAG modules; leaderless tunable-consistency data plane, Raft schema, no ACID.
- **[chroma](engines/chroma.md)** (rank 92) — Apache-2.0 developer-first vector/search DB; embeddable for local RAG, scales to an object-storage-backed serverless cloud (Rust core since 1.0).

## Multi-model

- **[databricks](engines/databricks.md)** (rank 7) — Spark-based lakehouse running SQL/ML over Delta Lake (Parquet + transaction log) on object storage; analytics-first, not OLTP.
- **[microsoft-azure-cosmos-db](engines/microsoft-azure-cosmos-db.md)** (rank 29) — Azure's globally distributed managed multi-model PaaS DB with five tunable consistency levels and wire-compatible NoSQL/Mongo/Cassandra/Gremlin/Table APIs; RU-billed, Azure-only.
- **[marklogic](engines/marklogic.md)** (rank 72) — Proprietary document + RDF + search NoSQL with genuine multi-document ACID (XQuery/JS runtime); enterprise data-integration, costly and idiosyncratic.
- **[arangodb](engines/arangodb.md)** (rank 80) — Native multi-model (document + graph + KV) with one query language (AQL); cluster ACID holds only within a single shard/OneShard.
- **[apache-ignite](engines/apache-ignite.md)** (rank 97) — In-memory distributed KV/SQL data grid with optional disk persistence; ACID for key-value, but distributed transactional SQL was removed in 2.x (reintroduced via Raft+MVCC in Ignite 3).
- **[adabas](engines/adabas.md)** (rank 98) — 1970s proprietary mainframe OLTP DBMS using inverted-list indexing and multivalued/periodic-group records; fast and durable but legacy, closed, and Natural-bound.
- **[virtuoso](engines/virtuoso.md)** (rank 101) — Hybrid SQL/SPARQL multi-model RDBMS and de-facto reference triplestore for the Linked Data web; scale-out, HA, and replication are commercial-only.
- **[orientdb](engines/orientdb.md)** (rank 103) — Java multi-model DB (graph+document+KV+object) with RID pointer traversal and SQL; capable single-node but distributed layer is fragile and project is effectively orphaned since SAP dropped support.
- **[intersystems-iris](engines/intersystems-iris.md)** (rank 118) — Proprietary multi-model platform on the MUMPS globals engine; SQL/object/document/KV over one store, big in healthcare, defaults to READ UNCOMMITTED.
- **[unidata-universe](engines/unidata-universe.md)** (rank 121) — Rocket's PICK-derived MultiValue (nested-relational) DBs; schema-light ASCII records with inline multivalues, queried via 4GL BASIC; legacy-app workhorse.
- **[apache-drill](engines/apache-drill.md)** (rank 140) — schema-free distributed SQL query engine over files and NoSQL stores in place; a query layer, not a database (no transactions/durability).
- **[fauna](engines/fauna.md)** (rank 146) — Serverless document-relational DB with clock-free strictly-serializable (Calvin) transactions; managed service shut down May 2025, core being open-sourced.

## Object


## Other

- **[apache-flink](engines/apache-flink.md)** (rank 41) — Stateful stream-processing engine with exactly-once state semantics and SQL; a compute layer, not a store of record.
- **[oracle-essbase](engines/oracle-essbase.md)** (rank 69) — Veteran multidimensional (MOLAP) cube engine for financial planning, consolidation, and Excel-driven write-back analytics; single-node, proprietary Oracle.
- **[apache-jackrabbit](engines/apache-jackrabbit.md)** (rank 75) — Java content repository implementing JCR 2.0 (hierarchical node tree, versioning, full-text search); snapshot-isolated MVCC via its Oak successor, the engine under Adobe AEM.
- **[spatialite](engines/spatialite.md)** (rank 143) — Embedded spatial extension for SQLite: OGC Simple Features geometry, GEOS analysis, and R*Tree indexing in a single file.

## Adjacent / data platform (not ranked)

Not db-engines-ranked, but they shape database decisions (see [CLAUDE](CLAUDE.md) §1). Filed in `engines/` with `adjacent: true`.

### Table formats (lakehouse)

- **[apache-iceberg](engines/apache-iceberg.md)** (adjacent) — Open lakehouse table format adding ACID, schema/partition evolution, and time travel over object-store files; the de facto multi-engine standard.
- **[delta-lake](engines/delta-lake.md)** (adjacent) — Open ACID table format (Parquet + JSON/checkpoint transaction log) for the lakehouse; native to Spark/Databricks, interops with Iceberg via UniForm.
- **[apache-hudi](engines/apache-hudi.md)** (adjacent) — open lakehouse table format built around record-level upserts/deletes and incremental CDC change streams (CoW/MoR, timeline, record-level index).
- **[apache-paimon](engines/apache-paimon.md)** (adjacent) — LSM-based open table format for high-throughput streaming upserts and native CDC changelog on object storage; Flink-native, the streaming-first cousin of Iceberg.

### Streaming platforms

- **[apache-kafka](engines/apache-kafka.md)** (adjacent) — Distributed, replayable commit log; the de-facto event-streaming backbone for transport, CDC, and pipelines (not a database).
- **[apache-pulsar](engines/apache-pulsar.md)** (adjacent) — Multi-tenant pub/sub + streaming with brokers decoupled from BookKeeper storage; elastic scaling, native geo-replication and tiered storage, at the cost of more moving parts than Kafka.
- **[redpanda](engines/redpanda.md)** (adjacent) — Kafka-API streaming log rewritten in C++ (no JVM/ZooKeeper, Raft per partition); lower p99 and simpler ops, but single-vendor BSL.

### Streaming / real-time databases

- **[materialize](engines/materialize.md)** (adjacent) — Postgres-wire streaming database doing incremental view maintenance on Differential Dataflow, with strict-serializable consistency.
- **[risingwave](engines/risingwave.md)** (adjacent) — Postgres-wire streaming SQL database maintaining incremental materialized views over event streams, with all state on S3-compatible object storage.
- **[ksqldb](engines/ksqldb.md)** (adjacent) — Kafka-native streaming SQL over Kafka Streams; push/pull queries, exactly-once within Kafka, Confluent Community License, now superseded by Flink.

### Real-time OLAP

- **[apache-pinot](engines/apache-pinot.md)** (adjacent) — Distributed columnar real-time OLAP store for sub-second, high-QPS queries on Kafka-fresh data; star-tree pre-aggregation and a deep-store segment model.
- **[apache-doris](engines/apache-doris.md)** (adjacent) — MySQL-protocol MPP columnar warehouse for sub-second real-time analytics with built-in upserts and lakehouse federation.
- **[apache-kudu](engines/apache-kudu.md)** (adjacent) — columnar storage engine for mutable analytic data (fast scans + random updates), paired with Impala/Spark for SQL.

### Query engines

- **[dremio](engines/dremio.md)** (adjacent) — Apache Arrow-based lakehouse SQL engine over object storage, with a semantic layer and Iceberg-materialized Reflections for BI acceleration.
- **[datafusion](engines/datafusion.md)** (adjacent) — Embeddable Rust/Arrow SQL + DataFrame query engine (library) you build databases out of, not a database itself.

### Catalogs / metadata

- **[unity-catalog](engines/unity-catalog.md)** (adjacent) — Databricks' lakehouse governance catalog; OSS Apache-2.0 metastore (Iceberg-REST/Hive-compatible) whose real access-control, lineage, and discovery live only in the managed service.
- **[hive-metastore](engines/hive-metastore.md)** (adjacent) — Apache-licensed Thrift-over-RDBMS catalog that maps lake table/partition names to schemas and file locations; the legacy lingua franca every engine speaks, bottlenecked by its backing DB.
- **[apache-polaris](engines/apache-polaris.md)** (adjacent) — open, vendor-neutral Iceberg REST catalog (Snowflake/Dremio-donated, ASF) with RBAC and credential vending; the metadata-pointer + governance layer for a multi-engine lakehouse.

### Change data capture (CDC)

- **[debezium](engines/debezium.md)** (adjacent) — Open-source log-based CDC that turns a database's transaction log into an ordered stream of row-level change events.
