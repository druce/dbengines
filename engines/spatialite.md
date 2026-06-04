---
name: SpatiaLite
slug: spatialite
rank: 143
data_model: Spatial (relational; SQLite spatial extension)
license: MPL 1.1 / GPL 2+ / LGPL 2.1+ tri-license (user's choice)
summary: An embedded spatial DBMS that bolts OGC Simple Features geometry, GEOS analysis, and R*Tree spatial indexing onto SQLite in a single file.
last_researched: 2026-06-04
confidence: high
---

# SpatiaLite

> SQLite plus a full OGC Simple Features geometry layer (GEOS, PROJ, R*Tree index) — a zero-config, single-file spatial database for desktop GIS and embedded use, not a server.

## Identity
- **Taxonomy / data model:** Relational with a spatial extension. It is not a standalone engine — it is a loadable extension (`mod_spatialite`) for [sqlite](sqlite.md) that adds geometry column types, ~hundreds of SQL spatial functions, and metadata tables conformant to the OGC Simple Features SQL spec ([SpatiaLite intro](https://www.gaia-gis.it/gaia-sins/splite-doxy-5.1.0/index.html)). Inherits SQLite's full relational SQL on top.
- **Storage model:** Row-store B-tree on-disk (SQLite's single-file format); geometries stored as a SpatiaLite BLOB encoding (a variant of OGC WKB). See [lsm-vs-btree](../concepts/lsm-vs-btree.md) — SQLite is B-tree, not LSM. Spatial indexing is a separate R*Tree virtual table per geometry column.
- **Workload:** OLTP-flavored embedded/single-user spatial queries and desktop GIS analysis; not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Read-heavy analytical spatial queries are common but run single-process against a local file, not a warehouse.

## Distribution & consistency
- **CAP / PACELC:** N/A — single-node, embedded library. No replication, no clustering, no network protocol. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** Inherits SQLite. Default is `SERIALIZABLE` in practice via coarse database-level locking; with WAL mode, one writer concurrent with multiple readers, readers get a consistent snapshot ([SQLite isolation](https://www.sqlite.org/isolation.html)). This is genuine serializability because there is at most one writer at a time, not MVCC-style concurrent serializable. See [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md) (SQLite WAL gives readers snapshot reads but is not general MVCC).
- **Replication / failover / split-brain:** None natively. See [replication-models](../concepts/replication-models.md). Any replication is external (file copy, Litestream-style WAL shipping, application-level) and not provided by SpatiaLite.
- **Tunable consistency:** N/A.
- **Clock dependency:** None. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Standard SQL DDL. Geometry columns are registered via `AddGeometryColumn()` (declares SRID, dimension, geometry type) which writes into the `geometry_columns` metadata table; you cannot just `ALTER TABLE ... ADD COLUMN geom`. Inherits SQLite's limited `ALTER TABLE` (add column is cheap; dropping/renaming columns gained support in SQLite 3.25+/3.35+).
- **Migration / online DDL:** Single-writer file; DDL takes a write lock but databases are typically small/single-user so locking is rarely a production concern. No online schema change machinery needed because there is no cluster.
- **Type system:** SQLite's dynamic typing (TEXT/INTEGER/REAL/BLOB/NUMERIC) plus SpatiaLite geometry types: POINT, LINESTRING, POLYGON, MULTI* and GEOMETRYCOLLECTION, with 2D/3D (Z), measured (M), and XYZM variants. No native JSON-typed column (SQLite JSON1 functions operate on TEXT). Native SRID/reprojection support via PROJ.

## Query interface
- **Language:** SQL (SQLite dialect) plus OGC spatial SQL functions: `ST_*` / Gaia-prefixed forms — `GeomFromText`, `AsText`, `ST_Area`, `ST_Intersects`, `ST_Buffer`, `ST_Union`, `Transform`, etc. GEOS backs the heavy computational-geometry predicates and operations (`Overlaps`, `Touches`, `Union`, `Buffer`) ([OSGeoLive overview](https://live.osgeo.org/en/overview/spatialite_overview.html)).
- **Transactions:** Full multi-statement ACID (inherited from SQLite — durable, atomic, single-writer).
- **Native vs app-side:** Native joins, aggregations, window functions (SQLite 3.25+), subqueries, and native spatial joins accelerated by the R*Tree index. Spatial index use is **not automatic** — you must join against the `SpatialIndex` virtual table or the R*Tree, or use the `VirtualSpatialIndex` helper, to get index pruning.
- **Stored procedures / UDFs:** No stored-procedure language. UDFs via the SQLite C API (or language bindings). VirtualKNN, VirtualRouting (Dijkstra shortest path), VirtualShape/Text/GeoJSON/XL virtual tables extend query reach ([OSGeoLive](https://live.osgeo.org/en/overview/spatialite_overview.html)).

## Scaling & topology
- **Vertical only.** No sharding, no partitioning, no horizontal scale-out — it is a library writing one file. Scale ceiling is one machine's disk/RAM and SQLite's single-writer model.
- **Read replicas:** None native (copy the file).
- **Storage/compute separation:** None — storage and compute are the same process. See [storage-compute-separation](../concepts/storage-compute-separation.md) for the contrasting pattern.

## Performance & durability
- **Write path:** SQLite's WAL or rollback-journal with configurable `synchronous`/`fsync` policy. With `synchronous=FULL` + WAL, committed transactions survive crash/power loss; `synchronous=NORMAL` in WAL trades a small durability window for speed. Data-loss window is governed entirely by SQLite's fsync settings. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Excellent low-latency point and spatial-index lookups for working sets that fit the OS page cache; no network round-trips. Bulk geometry analysis (GEOS buffer/union over large datasets) is single-threaded and CPU-bound — can be slow on large tables. p99 is dominated by disk page-cache misses and GEOS computation cost, not by compaction (there is none).
- **Compaction / vacuum / GC:** SQLite `VACUUM` to reclaim space and defragment; deleting rows leaves free pages until vacuumed. No background GC; `VACUUM` is a blocking, full-rewrite operation.

## Operations & maturity
- **Backup/restore / PITR:** Copy the file, or use SQLite's online backup API / `.dump`. No built-in PITR (external WAL-shipping tools like Litestream can provide it).
- **Observability:** SQLite `EXPLAIN QUERY PLAN` shows whether the R*Tree spatial index is used; no built-in metrics/slow-query log (it's a library).
- **Upgrade story:** Library/file-format upgrades are in-process; SQLite's on-disk format is famously stable and backward-compatible. Day-2 burden is minimal — there is no server to operate.
- **Maturity:** Mature and stable; current line is 5.1.0 (released 2023-08-04) ([Wikipedia](https://en.wikipedia.org/wiki/SpatiaLite)), maintained by Alessandro Furieri / the gaia-gis project. Widely embedded in QGIS, GDAL/OGR, and GeoDjango. No Jepsen report exists and none is applicable — it is a single-node embedded library with no distributed consistency claims to test. Known limits: single-writer concurrency, single-threaded GEOS analysis, and the smaller contributor base / bus-factor of a project driven largely by one maintainer (⚠️ unverified — current contributor head-count).

## Ecosystem & people
- **Canonical use cases:** Desktop/offline GIS (QGIS native format), mobile/embedded geospatial apps, a portable spatial data interchange format, GDAL/OGR-driven ETL, GeoDjango's lightweight spatial backend, ad-hoc spatial analysis without standing up [postgresql](postgresql.md)/[postgis](postgis.md).
- **Anti-patterns:** Multi-user concurrent-write server workloads, web backends with many simultaneous writers, very large datasets needing horizontal scale, or anything needing replication/HA — reach for [postgis](postgis.md) (PostGIS on [postgresql](postgresql.md)) instead.
- **Drivers / connectors:** First-class in GDAL/OGR, QGIS, GeoDjango, GeoServer, ArcGIS 10.2+. Accessible from any SQLite binding (Python via `pysqlite`/`apsw` with `load_extension`, etc.). CDC/Kafka/dbt/BI integrations are not native to an embedded file.
- **Community / docs / learning curve:** Solid Gaia-GIS docs, a SpatiaLite Cookbook, and OSGeo community presence. Learning curve is low if you know SQL and PostGIS function names (they largely overlap via the `ST_` standard).

## Licensing & cost
- **License:** MPL **1.1** / GPL 2+ / LGPL 2.1+ **tri-license** — the user chooses which one set of terms to apply ([Gaia-GIS intro](https://www.gaia-gis.it/gaia-sins/splite-doxy-5.1.0/index.html); [Wikipedia](https://en.wikipedia.org/wiki/SpatiaLite)). Note it is MPL 1.1, not the newer MPL 2.0. Pure OSS, no post-2018 relicensing, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md). Note dependency licenses (GEOS = LGPL, PROJ = X/MIT, SQLite = public domain) flow through.
- **Self-managed vs managed:** Self-managed only (embedded). No vendor, no managed service, no lock-in beyond the open SpatiaLite BLOB geometry encoding (which GDAL reads/writes freely).
- **Cost model:** Free. Cost is your own hardware; trivially cheap at small scale and simply does not exist as a hosted/serverless product at large scale.

## Hardware / deployment
- **Resource profile:** Disk-bound for I/O, CPU-bound for GEOS geometry operations. Working set need not fit in RAM, but performance is best when hot pages are cached. Memory footprint is tiny (it's a library).
- **Storage assumptions:** Local file on whatever the host provides; benefits from fast local NVMe/SSD. Not designed for high-latency network-attached storage (and SQLite explicitly warns against networked filesystems for concurrent access).
- **Footprint:** Embedded single-file — the SQLite/RocksDB-style category. See [embedded-databases](../concepts/embedded-databases.md). No server process.
- **Deployment:** On-prem / on-device / in-app. Containerizable trivially as a library dependency; no StatefulSet or clustering concerns because there is nothing to cluster.

## Bottom line
Reach for SpatiaLite when you want PostGIS-style spatial SQL without running a server: desktop GIS, offline/mobile apps, portable spatial datasets, and ETL. It is mature, free, and zero-ops. Do not reach for it for concurrent multi-writer, high-throughput, or horizontally scaled workloads — that is [postgis](postgis.md)/[postgresql](postgresql.md) territory. The single biggest gotcha: the spatial R*Tree index is **not used automatically** — queries must explicitly reference the spatial index virtual table to avoid full-table geometry scans.

## Sources
- [SpatiaLite — Gaia-GIS introduction (5.1.0)](https://www.gaia-gis.it/gaia-sins/splite-doxy-5.1.0/index.html)
- [SpatiaLite overview — OSGeoLive 16.0](https://live.osgeo.org/en/overview/spatialite_overview.html)
- [SpatiaLite — Wikipedia](https://en.wikipedia.org/wiki/SpatiaLite)
- [R*Tree Spatial Index — SpatiaLite Cookbook](https://www.gaia-gis.it/gaia-sins/spatialite-cookbook/html/rtree.html)
- [SQLite isolation](https://www.sqlite.org/isolation.html)
