---
name: Storage/Compute Separation
slug: storage-compute-separation
summary: Decoupling the durable storage layer from elastic stateless compute over shared (usually object) storage — the architecture behind Snowflake, BigQuery, Aurora, and Neon.
last_researched: 2026-06-04
---

# Storage/Compute Separation

> Classic "shared-nothing" databases bind data to the node that owns it, so you scale storage and
> compute together. **Storage/compute separation** puts durable data in a shared layer (object
> store or a distributed storage service) and runs **stateless, elastic compute** on top — scale,
> pay for, and fail each independently.

## Why it matters
- **Independent elasticity** — spin compute up/down (or to zero) without moving data; grow storage
  without adding query nodes.
- **Workload isolation** — multiple compute clusters read the same data without contending
  (Snowflake's multi-warehouse model; readers don't block the writer).
- **Cheap, durable storage** — object stores (S3/GCS/Azure Blob) give 11-nines durability and low
  $/GB; compute becomes a transient, swappable resource.
- **Fast clone/branch & time-travel** — copy-on-write metadata over immutable storage enables
  zero-copy clones and point-in-time reads.

The cost: **latency**. Object storage has high per-request latency, so these systems lean heavily on
caching (local SSD), columnar formats, and large-batch I/O — which is why the pattern fits
[OLAP](oltp-olap-htap.md) far better than latency-sensitive OLTP.

## Variants
- **Warehouse on object storage** — columnar data in S3/GCS/Blob, elastic compute clusters:
  [snowflake](../engines/snowflake.md) (the canonical design), [google-bigquery](../engines/google-bigquery.md) (Dremel + Colossus), [databricks](../engines/databricks.md)
  (lakehouse over Parquet/Delta), [amazon-redshift](../engines/amazon-redshift.md) (RA3 + managed storage), [clickhouse](../engines/clickhouse.md) Cloud.
- **OLTP with disaggregated storage** — keep transactional semantics but push the storage/redo layer
  to a shared service: [amazon-aurora](../engines/amazon-aurora.md) ("the log is the database" — ships redo, not pages),
  Neon and [alibaba-cloud-polardb](../engines/alibaba-cloud-polardb.md) for [postgresql](../engines/postgresql.md)/[mysql](../engines/mysql.md).
- **Lakehouse / open table formats** — Iceberg, Delta, Hudi let many engines (Snowflake, Databricks,
  Trino) compute over the *same* open storage, decoupling vendor compute from data.

## How to use it on engine pages
If an engine claims this pattern, say **what the shared storage is** (object store? custom redo
service?), **whether compute is truly stateless/elastic** (scale to zero? multiple independent
clusters?), and the **latency/caching** implications. Contrast with shared-nothing sharding (see
[replication-models](replication-models.md)). Relates to cost models — compute and storage are billed separately, which
is both the appeal and the bill-shock risk.
