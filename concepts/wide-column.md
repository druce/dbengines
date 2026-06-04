---
name: Wide-Column Stores
slug: wide-column
summary: The Bigtable-derived model — a sparse, distributed, sorted map keyed by (row, column-family, column, timestamp) — built for massive write throughput and linear scale, not joins or ad-hoc queries.
last_researched: 2026-06-04
---

# Wide-Column Stores

> A **wide-column** store (a.k.a. column-family / Bigtable-style) is, at heart, a **sparse,
> distributed, persistent, sorted multi-dimensional map**: keys are `(row key, column family,
> column qualifier, timestamp)` → value. Rows can have millions of columns, different rows can have
> different columns, and absent columns cost nothing (sparse).

## Don't confuse it with columnar
Despite the name, wide-column is **not** the same as [columnar (OLAP) storage](columnar-storage.md).
Wide-column is a **data model** for scalable operational workloads; physically it's usually an
[LSM-tree](lsm-vs-btree.md) grouping data by **column family**, not a scan-optimized analytical
column-store. Columnar storage is about reading few columns over many rows fast; wide-column is about
flexible sparse rows and write scale.

## Design traits
- **Row key = the index.** Data is partitioned and sorted by row key ([sharding-partitioning](sharding-partitioning.md));
  efficient access is by key or key range. Choose the row key for your query and to avoid hot spots.
- **No joins, limited ad-hoc query.** Denormalize and model tables per query pattern. Secondary
  indexes are limited or expensive.
- **Tunable consistency / high availability.** Dynamo-influenced ones ([apache-cassandra](../engines/apache-cassandra.md),
  [scylladb](../engines/scylladb.md)) are leaderless/[AP](cap-pacelc.md) with quorum tuning; Bigtable-lineage ones
  ([apache-hbase](../engines/apache-hbase.md), [google-cloud-bigtable](../engines/google-cloud-bigtable.md)) are CP with a single server per region per tablet.
- **Massive write throughput & linear scale** are the headline strengths.

## Engines
[apache-cassandra](../engines/apache-cassandra.md), [scylladb](../engines/scylladb.md), [apache-hbase](../engines/apache-hbase.md), [google-cloud-bigtable](../engines/google-cloud-bigtable.md),
[datastax-enterprise](../engines/datastax-enterprise.md), [apache-accumulo](../engines/apache-accumulo.md), [microsoft-azure-table-storage](../engines/microsoft-azure-table-storage.md). Lineage:
Google's Bigtable paper (2006) and Amazon's Dynamo paper (2007) — see [apache-cassandra](../engines/apache-cassandra.md), which
blends both.

## Anti-patterns
Joins, ad-hoc analytical queries, strong cross-row transactions, and workloads where you can't design
the schema around known access patterns. For analytics use [columnar](columnar-storage.md) OLAP; for
rich transactions use relational.

## How to use it on engine pages
State the lineage (Bigtable-CP vs Dynamo-AP), the partition/clustering key model, consistency tuning,
secondary-index limits, and the query language (CQL, etc.). Stress the schema-per-query-pattern
discipline as the main gotcha.
