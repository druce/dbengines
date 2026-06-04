---
name: Document Data Model
slug: document-data-model
summary: Store data as self-contained, nested documents (JSON/BSON) keyed by ID — schema-flexible and a natural fit for object-shaped data, at the cost of cross-document joins and global constraints.
last_researched: 2026-06-04
---

# Document Data Model

> A document database stores records as **self-describing, hierarchical documents** — typically
> JSON or binary JSON (BSON) — each identified by a key. A document holds nested objects and arrays,
> so an entire aggregate (an order with its line items) lives in one record instead of spread across
> joined tables.

## Defining traits
- **Schema-flexible (schema-on-read).** Documents in a collection need not share a shape; the
  "schema" effectively lives in application code. Great for evolving/heterogeneous data, risky when
  it hides silent inconsistencies.
- **Aggregate-oriented.** Data accessed together is stored together — fewer reads to assemble an
  object, no join for the common case. The flip side: data shared across aggregates is duplicated or
  needs application-side joins.
- **Rich secondary indexing & query.** Modern document stores index nested fields and run
  expressive queries/aggregation pipelines — more than early key-value-flavored stores.

## Strengths and anti-patterns
- **Strengths:** content/catalog/user-profile/CMS data, rapidly changing schemas, object-shaped
  domains, developer velocity (maps to app objects).
- **Anti-patterns:** highly relational data with many-to-many joins, workloads needing global
  constraints/foreign keys, and analytics across documents (a relational or
  [columnar](columnar-storage.md) store fits better). Denormalization shifts the burden of consistency
  to the application.

## Transactions & consistency
Single-document writes are atomic almost everywhere; **multi-document ACID** is newer and often
carries caveats and performance cost ([mongodb](../engines/mongodb.md) since 4.0/4.2). Distributed document stores expose
tunable consistency and have had notable [jepsen](jepsen.md) findings — read the [isolation-levels](isolation-levels.md) and
[cap-pacelc](cap-pacelc.md) story per engine, not the "ACID" label.

## Engines
[mongodb](../engines/mongodb.md) (BSON, the category leader), [couchbase](../engines/couchbase.md), [couchdb](../engines/couchdb.md), [amazon-documentdb](../engines/amazon-documentdb.md),
[google-cloud-firestore](../engines/google-cloud-firestore.md), [google-cloud-datastore](../engines/google-cloud-datastore.md), [firebase-realtime-database](../engines/firebase-realtime-database.md),
[ravendb](../engines/ravendb.md), [ibm-cloudant](../engines/ibm-cloudant.md), [rethinkdb](../engines/rethinkdb.md), [realm](../engines/realm.md)/[pouchdb](../engines/pouchdb.md) (embedded/sync),
[cloudkit](../engines/cloudkit.md). Many relational and [multi-model](multi-model.md) engines add JSON document types
([postgresql](../engines/postgresql.md) JSONB, etc.).

## How to use it on engine pages
Note BSON/JSON, schema-on-read flexibility, indexing of nested fields, single- vs multi-document
transaction support (and caveats), and the join/denormalization trade-off. Distinguish a true
document store from a relational engine with a JSON column.
