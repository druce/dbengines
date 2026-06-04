---
name: Apache Polaris
slug: apache-polaris
adjacent: true
rank: n/a
category: catalog
data_model: Iceberg REST catalog (metastore + access control)
license: Apache License 2.0 (permissive)
summary: Open, vendor-neutral Iceberg REST catalog with RBAC and credential vending; the metadata-pointer + governance layer for a multi-engine lakehouse.
last_researched: 2026-06-04
confidence: high
---

# Apache Polaris

> A standalone, open-source implementation of the Iceberg REST Catalog API that tracks table metadata pointers and centralizes access control (RBAC + short-lived credential vending) so many engines can share one copy of [Iceberg](../concepts/open-table-formats.md) data.

## Identity / role
- **What it IS:** a *catalog service* for the [lakehouse](../concepts/lakehouse.md). It implements the Apache Iceberg REST Catalog API, maps table/namespace names to the current Iceberg metadata-file pointer, performs the atomic pointer swap on commit, and enforces who may read/write what. It also vends short-lived cloud-storage credentials to engines.
- **What it is NOT:** it is **not a query engine** (it plans nothing, scans no data, runs no SQL), **not a storage layer** (data + Parquet/metadata live in your S3/ADLS/GCS object store), and **not the table format itself** (Iceberg is the format; Polaris is a catalog *for* it). It is also not a general-purpose data catalog / discovery + lineage product in the [data-catalog](../concepts/data-catalog.md) sense — it is a technical metastore + authorization gateway, not a business glossary.
- Co-created by Snowflake and Dremio, donated to the ASF in **Aug 2024**, incubated ~18 months, and graduated to a **Top-Level Project in Feb 2026**. ⚠️ unverified — exact graduation date; reported by secondary sources, not yet confirmed against an ASF announcement.

## How it fits
- In an Iceberg lakehouse the catalog is the single source of truth for "what is the current version of this table." Polaris stores that **metadata pointer** and exposes it over the Iceberg REST protocol, so any REST-aware engine queries the same tables without engine-specific catalog plugins. Compare the older Hive Metastore / per-engine catalog approach this replaces.
- **Internal vs external catalogs:** an *internal* catalog is managed by Polaris (read-write — Polaris owns commits); an *external* catalog federates to another Iceberg catalog provider and is **read-only** within Polaris.
- **Persistence:** catalog metadata (namespaces, table pointers, grants, principals) is stored in a metastore backend — the recommended **Relational JDBC** backend (Quarkus-managed datasource; PostgreSQL for production, H2 for dev). The older **EclipseLink** backend is deprecated since 1.0.0 and slated for removal. ([metastores docs](https://polaris.apache.org/releases/1.0.0/metastores/), [relational-jdbc](https://polaris.apache.org/releases/1.5.0/metastores/relational-jdbc/))
- **Storage configs:** per-catalog config for S3 (bucket + role ARN + optional external ID), Azure (container + tenant), and GCS (bucket); Polaris assumes an IAM identity to establish the trust relationship used for credential vending.
- Pairs with engines such as [Apache Spark](apache-spark-sql.md), [trino](trino.md), [Flink](apache-flink.md), [starrocks](starrocks.md), [clickhouse](clickhouse.md), Dremio, Apache Doris, and [snowflake](snowflake.md) — anything that speaks the Iceberg REST API. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Guarantees & consistency
- **Table-level atomicity comes from Iceberg, enforced by the catalog:** a commit is an atomic compare-and-swap of the metadata pointer (optimistic concurrency — a stale commit is rejected and the engine retries). This gives serializable isolation *per table*; see [isolation-levels](../concepts/isolation-levels.md). There are **no multi-table / cross-table transactions** — that is an Iceberg-spec limitation Polaris inherits, not something it adds.
- **Durability** of the pointer follows the metastore backend: with the JDBC backend, the catalog's own consistency/durability is PostgreSQL's. See [wal-and-durability](../concepts/wal-and-durability.md). The data + metadata files themselves rely on object-store durability.
- **CAP:** Polaris is a stateless service over an external DB; availability/consistency are the backing store's. Practically CP-ish — a partitioned/unavailable metastore blocks commits rather than allowing divergent pointers.
- **Delivery semantics:** N/A — this is a request/response catalog, not a streaming/[change-data-capture](../concepts/change-data-capture.md) system.
- ⚠️ unverified — no public Jepsen-style analysis of Polaris commit correctness exists; the atomicity argument rests on the Iceberg spec + the backing RDBMS, not on independent testing of Polaris itself.

## Interfaces & integration
- **Primary API:** the Apache Iceberg REST Catalog OpenAPI spec — so any conformant engine connects with no Polaris-specific driver. Plus Polaris's own management REST API for creating catalogs, principals, roles, and grants.
- **Auth & access control:** OAuth2-style service principals; **RBAC** with two role tiers — *principal roles* granted to principals, and *catalog roles* carrying privileges (on catalogs/namespaces/tables) that are granted to principal roles. 1.2.0+ added finer-grained access and event persistence.
- **Credential vending:** on `loadTable`, Polaris mints temporary, scoped cloud credentials (STS-style) instead of engines holding long-lived keys — the central security selling point. Known gap: Spark's `remove_orphan_files` cannot use vended credentials.
- **Interop:** because Iceberg is readable by Spark, Trino, Flink, StarRocks, Dremio, Snowflake, etc., Polaris is the shared control plane for "one copy of data, many engines."

## Operations & maturity
- **Deployment:** a Quarkus-based Java service, typically run as a container / on Kubernetes (official Helm chart) backed by PostgreSQL. Self-host the OSS, or use a managed offering — **Snowflake Open Catalog** and **Dremio**'s catalog are managed Polaris-based services.
- **Ops burden:** you operate a stateless service tier + a PostgreSQL it depends on (HA, backups, upgrades) — modest, but the metastore is now a critical-path dependency for every commit. The catalog is small-data; scaling is mostly about the RDBMS and the service tier.
- **Maturity:** young but fast-moving and broadly backed (Snowflake, Dremio, Google, Microsoft, Confluent contributors); 1.x series shipping regularly. Real production use exists primarily via the managed Snowflake/Dremio offerings; self-managed OSS in production is still early. Governance: ASF, vendor-neutral — a deliberate contrast to single-vendor catalogs.
- **Known failure modes / gotchas:** metastore as a single point of contention; credential-vending edge cases (orphan-file cleanup); EclipseLink deprecation migration; external (federated) catalogs are read-only.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, genuinely open, ASF-governed (no source-available / BSL strings). See [license-taxonomy](../concepts/license-taxonomy.md). This open footing is the explicit pitch *against* vendor-locked catalogs (Snowflake's framing: "the end of data vendor lock-in").
- **Cost:** the OSS is free; you pay for the infrastructure (service nodes + PostgreSQL + object storage). Managed forms (Snowflake Open Catalog, Dremio) carry their own pricing. Lock-in is low by design — the wire protocol is the open Iceberg REST spec, so migrating off a Polaris-based catalog to another REST catalog is plausible.

## Bottom line
- Reach for Polaris when you want a **vendor-neutral, open catalog** that lets [Spark](apache-spark-sql.md), [trino](trino.md), [snowflake](snowflake.md), Flink, StarRocks, and others read/write *one* set of Iceberg tables with centralized RBAC and short-lived credentials instead of long-lived cloud keys. Best fit for multi-engine Iceberg lakehouses that want to avoid being tied to one engine's catalog.
- **Do not** reach for it if you are single-engine and happy in that engine's native catalog (it adds an operational tier for little gain), if you are not on Iceberg (it is Iceberg-only — not Delta/Hudi), or if you expect a discovery/lineage/business-glossary catalog (wrong category).
- **Biggest gotcha:** it is infrastructure you must run and harden — a PostgreSQL-backed service on the critical commit path — and self-managed OSS maturity still trails the managed Snowflake/Dremio offerings; there is no multi-table transaction story beyond Iceberg's per-table atomicity.

## Sources
- [Apache Polaris — project site](https://polaris.apache.org/)
- [Polaris 1.2.0 Overview / architecture](https://polaris.apache.org/releases/1.2.0/)
- [Metastores (1.0.0)](https://polaris.apache.org/releases/1.0.0/metastores/) · [Relational JDBC (1.5.0)](https://polaris.apache.org/releases/1.5.0/metastores/relational-jdbc/)
- [Snowflake: Introducing Polaris Catalog](https://www.snowflake.com/en/blog/introducing-polaris-catalog/) · [Snowflake engineering: Apache Polaris, the end of data vendor lock-in](https://www.snowflake.com/en/engineering-blog/apache-polaris-iceberg-rest-catalog/)
- [Dremio: Apache Polaris — the catalog standard for Iceberg lakehouses](https://www.dremio.com/blog/apache-polaris-the-catalog-standard-for-lakehouses-and-ai/) · [What's new in 1.2.0](https://www.dremio.com/blog/whats-new-in-apache-polaris-1-2-0-fine-grained-access-event-persistence-and-better-federation/)
