---
name: Multi-Model
slug: multi-model
summary: One engine exposing several data models (relational, document, graph, key-value, etc.) over a shared core — convenience and fewer systems to run, but usually with one model first-class and the rest bolted on.
last_researched: 2026-06-04
---

# Multi-Model

> A **multi-model** database supports more than one data model — some combination of relational,
> document, [graph](graph-data-model.md), key-value, [wide-column](wide-column.md), time-series, [vector](vector-search-ann.md),
> or search — through one engine and (often) one query layer. The pitch: store polyglot data without
> running a zoo of specialized systems.

## Two routes to multi-model
- **Extended relational** — a mature RDBMS adds models as types/extensions: [postgresql](../engines/postgresql.md) (JSONB,
  PostGIS, pgvector, AGE graph), [oracle](../engines/oracle.md), [microsoft-sql-server](../engines/microsoft-sql-server.md), [sap-hana](../engines/sap-hana.md). The relational
  core stays first-class; other models ride on top.
- **NoSQL-origin multi-model** — engines designed to span models: [arangodb](../engines/arangodb.md) (document+graph+KV),
  [microsoft-azure-cosmos-db](../engines/microsoft-azure-cosmos-db.md) (document/graph/KV/table APIs), [couchbase](../engines/couchbase.md), [orientdb](../engines/orientdb.md),
  [redis](../engines/redis.md) (modules: JSON, search, vector, time-series), [fauna](../engines/fauna.md), [intersystems-iris](../engines/intersystems-iris.md),
  [datastax-enterprise](../engines/datastax-enterprise.md).

## The honest caveat
"Multi-model" rarely means equally good at every model. There is usually **one primary model** that
is fully optimized and secondary models that are convenient but slower, less expressive, or less
operationally mature than a purpose-built engine. The db-engines.com "(also: …)" convention reflects
this — list the engine under its *primary* model.

The trade-off is **consolidation vs specialization**: one system to operate, back up, and secure
versus best-in-class performance and features per workload. For moderate scale, consolidation often
wins; at extreme scale or demanding latency, the specialized engine usually does.

## How to use it on engine pages
Name the **primary** model and which secondary models are genuinely first-class vs bolted-on. Be
specific about what the non-primary models *can't* do (e.g. the graph layer lacks Cypher; the vector
index lacks filtering). Resist repeating marketing "does everything" claims — say where each model
is actually competitive. In [index](../index.md), file the engine under its primary model with "(also: …)".
