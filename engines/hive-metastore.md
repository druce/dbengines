---
name: Apache Hive Metastore
slug: hive-metastore
adjacent: true
rank: n/a
category: catalog
data_model: Lakehouse metadata catalog (table/partition registry)
license: Apache License 2.0 (permissive)
summary: The original "card catalog" of the data lake — a Thrift service over an RDBMS that maps table/partition names to schemas and file locations; ubiquitous, ageing, and hard to kill.
last_researched: 2026-06-04
confidence: high
---

# Apache Hive Metastore

> The de-facto legacy catalog of the Hadoop/lake world: a Thrift service backed by a relational DB that stores *where the data is and what its schema is* — not the data, not a query engine — and that two decades of engines still speak by default.

## Identity / role
- **What it is:** a metadata service (HMS) plus a backing relational database. It stores definitions of databases, tables, partitions, columns, types, storage formats, SerDe info, and the physical **location** (HDFS/S3/GCS path) of the underlying files. It is the canonical [data-catalog](../concepts/data-catalog.md) of the Hadoop ecosystem.
- **What it is NOT:** it is **not a query engine** (engines like [trino](trino.md), [apache-spark-sql](apache-spark-sql.md), Presto, [apache-flink](apache-flink.md) call it but execute themselves), **not a storage layer** (it points at files, it doesn't hold them), and **not a table format** — it predates and is distinct from [open-table-formats](../concepts/open-table-formats.md) like Iceberg/Delta/Hudi, though those formats often *use* HMS as their catalog.
- Born inside Apache Hive to make HDFS directories look like SQL tables; it now long outlives Hive's query engine and table format, both of which are largely legacy while HMS persists. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) (it serves the OLAP/[lakehouse](../concepts/lakehouse.md) world).

## How it fits
- **Two layers:** (1) a stateless **Thrift service** (the "metastore server", shippable since Hive 3 as a *standalone metastore* with no Hive runtime dependency); (2) a **backing RDBMS** — typically MySQL, PostgreSQL, MariaDB, Oracle, or SQL Server — accessed via DataNucleus/JDO ORM. All durable metadata lives in the RDBMS; the Thrift tier is the API surface.
- **Deployment modes:** *embedded* (in-process Derby, dev only), *local* (RDBMS over JDBC, metastore in the client JVM), and *remote* (standalone Thrift service shared by many engines — the production norm).
- **The problem it solves:** schema-on-read over a pile of files. An engine asks HMS "what columns/types/partitions does `db.table` have and where are its files?" and gets back enough to plan a scan. This decouples compute from a shared metadata source of truth.
- **Pairs with:** [apache-spark-sql](apache-spark-sql.md), [trino](trino.md), Presto, [apache-flink](apache-flink.md), Apache Hudi, [databricks](databricks.md) (historically), and cloud variants. AWS Glue Data Catalog is an HMS-API-compatible managed reimplementation. Iceberg ships a `HiveCatalog` so Iceberg tables can be registered in HMS; Delta also leans on it. Most Iceberg deployments today still front their table metadata with HMS in practice.

## Guarantees & consistency
- **Catalog metadata operations** are backed by RDBMS transactions, so create/alter/drop of tables and partitions inherit the backing DB's ACID guarantees ([isolation-levels](../concepts/isolation-levels.md)). Consistency of the catalog is only as strong as the chosen RDBMS and its HA setup.
- **Data-file ACID is NOT inherent.** Classic Hive external tables give no atomic multi-file commit; correctness across readers/writers depended on directory conventions. Hive later added **Hive ACID** transactions managed by `DbTxnManager`/`DbLockManager`, which store locks and transaction state in the metastore and use **heartbeats** to reap dead clients' locks ([Hive Transactions docs](https://hive.apache.org/docs/latest/user/hive-transactions-acid/)). This locking governs Hive-managed ACID tables — it is not what gives [Iceberg/Delta](../concepts/open-table-formats.md) tables their snapshot isolation (those formats implement their own atomic commit; HMS may only hold a pointer or a lock).
- **CAP/[cap-pacelc](../concepts/cap-pacelc.md):** N/A for the service itself (stateless); availability/consistency are properties of the backing RDBMS deployment (e.g. single primary vs. replicated MySQL).
- **[Durability](../concepts/wal-and-durability.md):** metadata durability = the RDBMS's WAL/fsync. Lose/un-backed-up RDBMS = lose the catalog (the data files survive but become unaddressable).

## Interfaces & integration
- **API:** a **Thrift** API (`hive_metastore.thrift`) with bindings in many languages; an HTTP transport for Thrift also exists. There is no native REST/JSON catalog API — a key gap versus the modern [Iceberg REST Catalog](../concepts/open-table-formats.md) spec (introduced 2022).
- **Clients/consumers:** Hive, [apache-spark-sql](apache-spark-sql.md) (its default catalog), [trino](trino.md)/Presto, [apache-flink](apache-flink.md), Hudi sync, Impala, and many BI/ETL tools. AWS Glue, Google Dataproc Metastore, and Azure HDInsight provide managed HMS-compatible endpoints.
- **Interop reality:** the Thrift/HMS interface is the lowest-common-denominator "lingua franca" of lake catalogs — almost every engine can read it, which is exactly why it is so hard to displace despite its age.

## Operations & maturity
- **Maturity:** extremely high — production-hardened since the late 2000s, the single most widely deployed lake catalog. Governed by the Apache Hive project (ASF community, vendor-neutral).
- **Ops burden:** you run and back up a stateful **RDBMS** plus the Thrift tier; HA means HA for that DB. Schema migrations between Hive versions (`schematool`) are a known sharp edge.
- **Known failure modes / limits:** the backing RDBMS is the scaling bottleneck. **Partition explosion** is the classic pain — tables with millions of partitions turn metadata ops (enumeration, drop, MSCK repair) into heavy multi-row RDBMS queries that can saturate the DB; Cloudera guidance caps a single query at ~10,000 partitions ([Cloudera tuning](https://docs.cloudera.com/cdp-private-cloud-base/7.3.1/hive-metastore/topics/hive-hms-tune.html)). The Thrift round-trips add latency on heavy calls (partition listing); the bottleneck is I/O to the RDBMS, not CPU ([lakeFS analysis](https://lakefs.io/blog/hive-metastore-it-didnt-age-well/)). Some operators horizontally scale the backend (e.g. MySQL → TiDB) to cope.
- **Governance gaps:** no built-in fine-grained access control, lineage, or multi-table transactions — those were bolted on by external systems (Ranger/Sentry) or are absent.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, fully open ([license-taxonomy](../concepts/license-taxonomy.md)). The standalone metastore is shippable independently of the Hive query engine.
- **Open vs. vendor-controlled:** open and community-governed (ASF). Managed compatible flavors (AWS Glue Data Catalog, Dataproc Metastore) are proprietary services with per-request/per-object pricing and possible behavioral drift from upstream HMS.
- **Cost model (self-host):** free software; real cost is operating the backing RDBMS + Thrift service (compute, storage, HA, DBA time).

## Bottom line
- Reach for HMS when you need the **maximally compatible** catalog that every lake engine already understands, or when you're on existing Hadoop/Hive infrastructure — it is reliable, free, and battle-tested. Avoid standing up a *new* greenfield catalog on it: it has no REST API, weak governance, and its RDBMS backend chokes on partition-heavy tables. **Biggest gotcha / anti-pattern:** treating it as a scalable, self-managing service — it is a thin Thrift shell over a single relational DB that you must tune, scale, and back up, and tables with millions of partitions will make that DB the bottleneck for your whole platform. For new lakehouses, prefer an Iceberg REST catalog (Polaris, Lakekeeper, Nessie) or [Unity Catalog](databricks.md) and keep HMS only for compatibility.

## Sources
- [Apache Hive Design (HMS architecture)](https://cwiki.apache.org/confluence/display/hive/design)
- [hive_metastore.thrift (API definition)](https://github.com/apache/hive/blob/master/standalone-metastore/metastore-common/src/main/thrift/hive_metastore.thrift)
- [Apache Hive metastore overview (Cloudera)](https://docs-archive.cloudera.com/runtime/7.2.0/hive-hms-overview/index.html)
- [Hive Transactions (Hive ACID), DbTxnManager/DbLockManager](https://hive.apache.org/docs/latest/user/hive-transactions-acid/)
- [Hive Locking](https://cwiki.apache.org/confluence/display/Hive/Locking)
- [Tuning the metastore — partition limits (Cloudera)](https://docs.cloudera.com/cdp-private-cloud-base/7.3.1/hive-metastore/topics/hive-hms-tune.html)
- [Hive Metastore: it didn't age well (lakeFS)](https://lakefs.io/blog/hive-metastore-it-didnt-age-well/)
- [Why Hive Metastore is still unbeatable (S. Sinchenko)](https://semyonsinchenko.github.io/ssinchenko/post/data-catalogs/)
- [Iceberg Catalogs 2025 (e6data)](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management)
- [Horizontally scaling HMS: MySQL → TiDB](https://medium.com/swlh/horizontally-scaling-the-hive-metastore-database-by-migrating-from-mysql-to-tidb-4636fed170ce)
