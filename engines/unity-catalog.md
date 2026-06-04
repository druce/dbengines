---
name: Unity Catalog
slug: unity-catalog
adjacent: true
rank: n/a
category: catalog
data_model: Lakehouse governance & metadata catalog
license: Apache 2.0 (OSS server, LF AI & Data) — managed Databricks version is proprietary
summary: Databricks' lakehouse governance catalog; an OSS Apache-2.0 metastore (Iceberg-REST/Hive-compatible) whose serious access-control, lineage, and discovery features live only in the proprietary managed service.
last_researched: 2026-06-04
confidence: medium
---

# Unity Catalog

> A governance/metadata catalog for the lakehouse — it stores *what tables exist and who can touch them*, not data and not query results — split into a thin Apache-2.0 OSS server and a much richer proprietary Databricks-managed product.

## Identity / role
- **What it is:** a centralized catalog and governance layer for [lakehouse](../concepts/lakehouse.md) assets — tables, files ("volumes"), functions, ML models, and AI tools — over a three-level namespace (`catalog.schema.object`). It holds metadata, access policies, lineage, and audit, and vends short-lived storage credentials to engines.
- **What it is NOT:** not a query engine (it does not execute SQL — [databricks](databricks.md)/[apache-spark-sql](apache-spark-sql.md)/[trino](trino.md) do), not a storage/[table format](../concepts/open-table-formats.md) (that's [apache-iceberg](apache-iceberg.md)/[delta-lake](delta-lake.md)/Hudi), and not a database. It is the control plane that sits *beside* compute and object storage. See [oltp-olap-htap](../concepts/oltp-olap-htap.md) for the workload axis it governs (mostly OLAP/lakehouse).
- **Two distinct things share the name:** (1) **Unity Catalog OSS** — Apache-2.0 server donated to LF AI & Data (Linux Foundation), open-sourced June 2024; (2) the **Databricks-managed Unity Catalog** — the proprietary, deeply-integrated governance product inside the Databricks platform. The OSS project is *not* a drop-in replacement for the managed service.

## How it fits
- **Architecture:** a metastore service exposing REST APIs over an OpenAPI spec. Engines query it for table metadata and storage locations; UC then performs **credential vending** — issuing short-lived, scoped cloud credentials (S3/ADLS/GCS) so the engine reads/writes object storage directly while UC enforces policy centrally ([Databricks credential-vending docs](https://docs.databricks.com/aws/en/external-access/credential-vending)).
- **Problem it solves:** one governance plane across many engines and table formats instead of per-engine ACLs and a sprawl of Hive metastores. Pairs naturally with [delta-lake](delta-lake.md) and, via UniForm, with [apache-iceberg](apache-iceberg.md) and Hudi clients.
- **For external Iceberg engines:** UC implements the **Iceberg REST Catalog (IRC)** API, so [trino](trino.md), Dremio, [apache-spark-sql](apache-spark-sql.md), [starrocks](starrocks.md), [duckdb](duckdb.md), Daft, and others can use UC as their Iceberg catalog ([interop blog](https://www.databricks.com/blog/expanded-interoperability-unity-catalog-open-apis)). IRC gives read/write/create on managed Iceberg tables and **read-only** on Delta tables with Iceberg reads enabled (UniForm).

## Guarantees & consistency
- **Not a transactional data store** — ACID for table data is provided by the underlying [table format](../concepts/open-table-formats.md) (Delta/Iceberg snapshot isolation), not by the catalog. UC tracks the current table pointer/metadata; the format's commit protocol provides the [isolation](../concepts/isolation-levels.md).
- **Catalog metadata operations** (create table, grant, alter) are transactional against UC's own backing store; CAP/[isolation-levels](../concepts/isolation-levels.md) are largely **N/A** at the data layer — UC is a metadata service, not the path data durability flows through.
- **Credential-vending security model:** access is enforced by UC handing out *short-lived scoped* credentials rather than long-lived keys; the gotcha is that once an engine holds vended credentials it talks to object storage directly, so revocation/row-and-column masking depends on the engine honoring UC policy. ⚠️ unverified — no public Jepsen-style audit of UC's consistency or policy-enforcement guarantees exists.
- **Enforcement gap (important):** fine-grained controls (row filters, column masks, dynamic views) are enforced primarily by Databricks compute runtimes in the managed product; external engines getting raw vended credentials may bypass those finer policies unless the integration enforces them. Treat "fine-grained governance everywhere" as a managed-product/marketing claim, not an OSS guarantee.

## Interfaces & integration
- **APIs:** OpenAPI-defined Unity REST API; **Apache Iceberg REST Catalog** compatible; **Apache Hive metastore** API compatible ([open-sourcing blog](https://www.databricks.com/blog/open-sourcing-unity-catalog)).
- **Objects governed:** catalogs → schemas → tables, **volumes** (unstructured files), **functions**, **ML models** (MLflow), and AI tools.
- **Formats:** [delta-lake](delta-lake.md) (native), [apache-iceberg](apache-iceberg.md) and Hudi via Delta UniForm, plus Parquet/CSV/JSON.
- **Engines/tools:** [databricks](databricks.md), [apache-spark-sql](apache-spark-sql.md), [trino](trino.md), Dremio, [starrocks](starrocks.md), [duckdb](duckdb.md), Daft, PuppyGraph, Spice AI, Microsoft Fabric, Salesforce Data Cloud, and any IRC-speaking engine.
- **OSS vs managed feature split:** OSS focuses on client interoperability and table/credential access. Managed-only (as of the v0.x OSS roadmap): automatic **column-level lineage**, the **Catalog Explorer** discovery UI, Delta Sharing, broad write/views/access-control APIs, and runtime-enforced row/column security. See [data-catalog](../concepts/data-catalog.md).

## Operations & maturity
- **Deployment:** OSS server is a standalone Java/Spring service you self-host (plus a CLI/UI); the managed version is fully operated by Databricks across AWS/Azure/GCP.
- **Maturity:** managed UC is GA, widely deployed, and the default governance layer for Databricks customers — production-proven at scale. OSS UC is young (open-sourced mid-2024), thinner, and evolving; governed by LF AI & Data but with development heavily Databricks-driven.
- **Known failure modes / cautions:** the OSS project lacks the managed UI, managed lineage, and turnkey fine-grained security; relying on OSS expecting parity leads to gaps. Vendor-gravity: the richest features remain inside Databricks, so "open catalog" interoperability is real for *reads/IRC* but governance depth is not portable.
- **Governance:** OSS hosted at LF AI & Data (Linux Foundation); the strategic catalog product is Databricks-controlled.

## Licensing & cost
- **OSS server:** Apache 2.0 (permissive) — see [license-taxonomy](../concepts/license-taxonomy.md); self-host free.
- **Managed:** proprietary, bundled into the Databricks platform; no separate per-seat list price — cost is part of Databricks consumption (DBUs). Lock-in risk is via the proprietary governance/lineage/security features and tight Databricks integration, not the open APIs.

## Bottom line
- Reach for **managed Unity Catalog** if you live on [databricks](databricks.md) and want one governance plane (lineage, discovery, row/column security, audit) over your lakehouse — it is the strongest integrated lakehouse catalog and increasingly the standard IRC endpoint other engines can read. Reach for **UC OSS** mainly to give external Iceberg/Hive engines a catalog and credential-vending without buying Databricks. The biggest gotcha/anti-pattern: assuming **OSS == managed** — the OSS server is a thin interop layer, and the governance teeth (fine-grained enforcement, automatic lineage, the discovery UI) only fully materialize inside the proprietary Databricks service. Also note the rival [apache-polaris](apache-polaris.md) (Snowflake-backed Iceberg REST catalog) competes for the same "open catalog" position.

## Sources
- [Open sourcing Unity Catalog (Databricks blog, 2024)](https://www.databricks.com/blog/open-sourcing-unity-catalog)
- [Unity Catalog product page](https://www.databricks.com/product/unity-catalog) and [unitycatalog.io](https://unitycatalog.io/)
- [Expanded interoperability with Unity Catalog Open APIs](https://www.databricks.com/blog/expanded-interoperability-unity-catalog-open-apis)
- [Credential vending for external system access](https://docs.databricks.com/aws/en/external-access/credential-vending)
- [What is Unity Catalog? (Databricks docs)](https://docs.databricks.com/aws/en/data-governance/unity-catalog/)
- [Unity Catalog limitations (Atlan)](https://atlan.com/know/databricks-unity-catalog-limitations/) (secondary, on OSS vs managed gaps)
