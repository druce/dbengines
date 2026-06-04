---
name: Embedded Databases
slug: embedded-databases
summary: Databases that run in-process as a library, not a separate server — no network, no daemon, the data lives next to the application. SQLite, DuckDB, RocksDB, and friends.
last_researched: 2026-06-04
---

# Embedded Databases

> An **embedded** database runs **in-process** as a linked library: no separate server, no network
> hop, no connection pool, often a single file (or a directory) on local disk. The application *is*
> the database process.

## Defining traits
- **In-process** — function calls, not client/server RPC; microsecond latency, no network failure
  modes, trivial deployment (ship a library + a file).
- **Single-machine** — durability and scale are bounded by the host; HA/replication, if any, is
  bolted on externally (litestream, rqlite, Turso/libSQL for [sqlite](../engines/sqlite.md)).
- **Concurrency model varies** — typically one process; writer concurrency is the key limit
  ([sqlite](../engines/sqlite.md) is single-writer with WAL-mode concurrent readers).

## The main flavors
- **Relational, OLTP** — [sqlite](../engines/sqlite.md) (the most-deployed DB on earth: phones, browsers, apps), [h2](../engines/h2.md),
  [apache-derby](../engines/apache-derby.md), [hypersql](../engines/hypersql.md), [firebird](../engines/firebird.md) (embedded mode), [sap-sql-anywhere](../engines/sap-sql-anywhere.md), [interbase](../engines/interbase.md).
- **Embedded OLAP** — [duckdb](../engines/duckdb.md) ("SQLite for analytics"): vectorized [columnar](columnar-storage.md)
  engine for local analytical queries over Parquet/CSV/Arrow.
- **Embedded key-value / storage engines** — [rocksdb](../engines/rocksdb.md), [leveldb](../engines/leveldb.md), [lmdb](../engines/lmdb.md), Berkeley DB
  ([oracle-berkeley-db](../engines/oracle-berkeley-db.md)): not user-facing databases but the **storage layer** inside bigger
  systems ([rocksdb](../engines/rocksdb.md) powers many distributed DBs).
- **Embedded document / mobile** — [realm](../engines/realm.md), [pouchdb](../engines/pouchdb.md), [couchbase](../engines/couchbase.md) Lite: on-device stores with
  sync to a server.

## When to reach for one
Edge/mobile/desktop apps, CLI tools, tests, caches, single-node analytics, and as the on-disk engine
inside a larger system. **Anti-pattern:** a shared multi-client system of record — you want a server
DB ([postgresql](../engines/postgresql.md), etc.) once multiple machines must write concurrently.

## How to use it on engine pages
Mark footprint as embedded; note the concurrency limit (single-writer?), durability model
([wal-and-durability](wal-and-durability.md)), whether replication exists at all, and the library/language bindings.
Contrast with client/server and [serverless](storage-compute-separation.md) footprints.
