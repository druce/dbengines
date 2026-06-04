---
name: License Taxonomy
slug: license-taxonomy
summary: Permissive vs copyleft vs source-available vs proprietary — and the post-2018 wave of relicensing (SSPL, BSL, Elastic, Confluent) that moved engines out of true open source.
last_researched: 2026-06-04
---

# License Taxonomy

> "Open source" has become a contested label. What matters operationally: **can you run, modify, and
> offer it as a service without legal risk, and who can sue you?** The categories below, roughly
> permissive → restrictive.

## The categories
- **Permissive (OSI open source)** — Apache 2.0, MIT, BSD, [postgresql](../engines/postgresql.md) License. Use, modify,
  embed, resell, offer as a service — almost no obligations. Examples: [postgresql](../engines/postgresql.md), [sqlite](../engines/sqlite.md)
  (public domain), [clickhouse](../engines/clickhouse.md) (Apache 2.0), [duckdb](../engines/duckdb.md) (MIT).
- **Copyleft (OSI open source)** — GPL/AGPL, LGPL. Free to use, but distributing modifications (GPL)
  or offering over a network (**AGPL**) requires sharing source. [mysql](../engines/mysql.md) is GPL (with an Oracle
  commercial dual license for embedders who can't accept GPL); [mariadb](../engines/mariadb.md) server GPL.
- **Source-available (NOT OSI open source)** — source is visible but a clause restricts competing
  use, usually "you may not offer this as a managed service":
  - **SSPL** (Server Side Public License) — [mongodb](../engines/mongodb.md) (2018), [elasticsearch](../engines/elasticsearch.md) (2021, later also
    re-added AGPL as an option in 2024). Drafted to stop cloud providers offering it as SaaS.
  - **BSL / BUSL** (Business Source License) — time-delayed: restricted now, converts to an open
    license (often Apache) after N years. [cockroachdb](../engines/cockroachdb.md) (moved to BSL then a custom CRL license),
    [singlestore](../engines/singlestore.md), Sentry, HashiCorp products.
  - **Elastic License (ELv2)**, **Confluent Community License** — similar "no SaaS competition" gist.
- **Proprietary / commercial** — closed source, per-core / per-socket / per-seat. [oracle](../engines/oracle.md),
  [microsoft-sql-server](../engines/microsoft-sql-server.md), [sap-hana](../engines/sap-hana.md), [teradata](../engines/teradata.md). Often with free-tier editions
  (Express/Developer) carved out.
- **Managed-only** — no license to self-host at all; you rent the service: [snowflake](../engines/snowflake.md),
  [google-bigquery](../engines/google-bigquery.md), [amazon-dynamodb](../engines/amazon-dynamodb.md), [google-cloud-spanner](../engines/google-cloud-spanner.md).

## The post-2018 relicensing wave
A series of OSS databases relicensed to **source-available** to stop hyperscalers (chiefly AWS) from
monetizing them as managed services without contributing back. Consequences for users:
- **Forks** — the old OSS license forks live on: OpenSearch (from [elasticsearch](../engines/elasticsearch.md)), Valkey (from
  [redis](../engines/redis.md), after Redis moved to RSALv2/SSPL in 2024), [amazon-documentdb](../engines/amazon-documentdb.md) (Mongo-compatible).
- **Vendor lock pressure** — relicensing is paired with steering users to the vendor's own cloud.

## How to use it on engine pages
State the **exact license and flavor**, flag any **post-2018 relicense** (and from what), note
whether it's **self-hostable or managed-only**, and call out lock-in via proprietary extensions.
"Open source" alone is insufficient — say *which* license and whether it's OSI-approved.
