---
name: PostGIS
slug: postgis
rank: 28
data_model: Spatial extender (relational; vector/raster geospatial types) for PostgreSQL
license: GPL v2 (copyleft) — extension to PostgreSQL
summary: The de facto open-source spatial database; turns PostgreSQL into a full OGC-compliant GIS engine, inheriting all of Postgres's consistency and operational behavior.
last_researched: 2026-06-04
confidence: high
---

# PostGIS

> PostGIS is not a standalone database — it is a [postgresql](postgresql.md) extension that adds OGC-standard geometry/geography/raster types and spatial indexing, making Postgres the strongest open-source GIS engine; everything about its consistency, transactions, and operations is inherited from [postgresql](postgresql.md).

## Identity
- **Taxonomy / data model:** Spatial extender for [postgresql](postgresql.md). Adds `geometry`, `geography`, `raster`, and topology types plus ~500 spatial functions on top of the relational model. Implements the OGC Simple Features for SQL spec and ISO SQL/MM. It is *not* a separate engine — it ships as a Postgres extension (`CREATE EXTENSION postgis`).
- **Storage model:** Row-store (Postgres heap), inherited from [postgresql](postgresql.md) ([lsm-vs-btree](../concepts/lsm-vs-btree.md): Postgres is B-tree/heap, not LSM). Geometries store as a compact serialized binary (EWKB-derived) in the row; large geometries TOAST out-of-line and compress. Spatial indexes are R-Tree-over-GiST, with SP-GiST and BRIN also available.
- **Workload:** Primarily OLTP geospatial, but heavily used for analytical spatial queries (joins on `ST_Intersects`, nearest-neighbor, aggregation). Not HTAP — it is whatever [postgresql](postgresql.md) is for a given query. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP / PACELC:** Inherited from [postgresql](postgresql.md). Single-node Postgres is CP-ish only in the trivial sense (no partitions on one node); with streaming replication it is single-leader, async or sync. See [cap-pacelc](../concepts/cap-pacelc.md). PostGIS adds no distribution of its own.
- **Default isolation & what's achievable:** Postgres defaults to Read Committed; Repeatable Read (snapshot) and Serializable (SSI) are available. PostGIS operations are ordinary SQL inside Postgres transactions and obey [mvcc](../concepts/mvcc.md) and [isolation-levels](../concepts/isolation-levels.md) exactly like any other Postgres data — full ACID, genuinely serializable when requested (not "ACID" meaning merely snapshot).
- **Replication:** Single-leader streaming/logical replication via [postgresql](postgresql.md); sync or async; failover via Patroni/repmgr/managed services. See [replication-models](../concepts/replication-models.md). ⚠️ unverified — logical replication of spatial types works but ordering/identity edge cases for raster are rarely exercised in the wild.
- **Tunable consistency?** No per-query consistency levels; same model as Postgres.
- **Clock dependency:** None for correctness; standard Postgres. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Rigid relational columns; geometry columns are typed and constrained by SRID and geometry subtype (e.g. `geometry(Point,4326)`), enforced at write time. The `spatial_ref_sys` table holds EPSG/SRID coordinate-system definitions; `geometry_columns` is a view exposing registered spatial columns.
- **Migration/evolution:** Inherits Postgres online DDL — adding a column or index is mostly non-blocking (`CREATE INDEX CONCURRENTLY`), but type-changing `ALTER` and adding a SRID-checked constraint can rewrite/lock the table. PostGIS minor upgrades require running `ALTER EXTENSION postgis UPDATE` and sometimes `postgis_extensions_upgrade()`.
- **Type system:** Rich — `geometry` (planar, fast), `geography` (geodetic on a spheroid, accurate over long distances/poles), `raster`, network topology, plus all native Postgres JSON/arrays/intervals. 2D/3D/4D (Z, M) coordinates; SFCGAL backend for true 3D solids.

## Query interface
- **Language:** SQL (PostgreSQL dialect) with spatial functions/operators (`ST_*`, `&&` bounding-box overlap, `<->` KNN distance). No separate DSL. Standards: OGC Simple Features SQL and SQL/MM.
- **Transactions:** Full multi-statement ACID via Postgres.
- **Native joins/indexes/aggregations:** Native spatial joins (predicate functions over GiST), spatial aggregates (`ST_Union`, `ST_Collect`, `ST_ClusterDBSCAN`), nearest-neighbor via the index-assisted `<->` operator. Raster map-algebra functions. MVT (`ST_AsMVT`) for vector-tile serving directly from SQL.
- **Stored procedures / UDFs:** Full Postgres PL/pgSQL, PL/Python, etc. Many GIS pipelines push logic into SQL functions.

## Scaling & topology
- **Vertical vs horizontal:** Primarily vertical (scale the box). Read replicas via streaming replication; replica reads are consistent up to replication lag (eventually consistent if async).
- **Sharding:** No native spatial sharding. Horizontal scale comes from [citus](citus.md) (distributed Postgres) — which supports PostGIS columns and can co-locate by a distribution key, but spatial joins across shards are limited and resharding is painful. Manual partitioning by region/time is common.
- **Storage/compute separation:** Not in core; available via managed Postgres platforms (Aurora PostgreSQL with PostGIS, Neon, AlloyDB) that implement [storage-compute-separation](../concepts/storage-compute-separation.md) at the Postgres layer.

## Performance & durability
- **Write path:** Postgres WAL with configurable `fsync`/`synchronous_commit`; group commit. Data-loss window on crash is the Postgres window (zero with `synchronous_commit=on` + sync replica; up to `wal_writer_delay` worth otherwise). See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Spatial query speed lives or dies on the GiST index. A correct query first filters by bounding box (`&&`, index-assisted) then refines with the exact predicate (`ST_Intersects`); missing the index turns a join into a full-scan cross-product. p99 is dominated by index selectivity and TOAST detoasting of large geometries; very large/complex polygons can blow up CPU in the refinement step.
- **Index types:** GiST (R-Tree, the default and most versatile), SP-GiST, and BRIN (good for very large, spatially-clustered tables where storing per-block bounding boxes is cheap). `ANALYZE` matters — the planner needs geometry stats to choose the spatial index.
- **Compaction / vacuum:** Inherits Postgres [mvcc](../concepts/mvcc.md) bloat and autovacuum behavior; heavy update/delete churn on spatial tables bloats both heap and GiST indexes, hurting p99 until vacuumed/reindexed.

## Operations & maturity
- **Backup/restore, PITR:** Full Postgres `pg_dump`/`pg_basebackup`/PITR. Caveat: restoring a dump requires the matching PostGIS extension version installed first, or the dump fails to load — a classic upgrade footgun.
- **Observability:** Standard Postgres — `EXPLAIN (ANALYZE, BUFFERS)` shows whether the spatial index was used, `pg_stat_statements`, slow-query log. Reading spatial plans is the core operational skill.
- **Upgrade story:** Two-layer upgrades — Postgres major-version upgrades (pg_upgrade/dump-reload, brief downtime) *and* PostGIS extension upgrades (`ALTER EXTENSION ... UPDATE`). Mismatched PostGIS/GEOS/PROJ library versions across nodes cause subtle result differences; keep them aligned.
- **Maturity:** Very mature (since 2001), the reference open-source GIS database, used by governments, OSM tooling, logistics, and mapping companies. No Jepsen report specific to PostGIS exists; its consistency story is [postgresql](postgresql.md)'s, which has been studied (Postgres has had documented serializability/isolation analyses). Known failure modes are Postgres's plus geometry-validity bugs (invalid polygons causing GEOS exceptions — `ST_MakeValid` is your friend) and result drift across GEOS versions.

## Ecosystem & people
- **Canonical use cases:** Storing and querying vector geodata (points/lines/polygons), nearest-store / radius search, geofencing, routing inputs (with pgRouting), spatial joins (which feature contains this point), vector-tile serving, raster analysis. The default backend for QGIS, GeoServer, MapServer, and many web maps.
- **Anti-patterns:** Planet-scale write-heavy spatial workloads needing horizontal sharding (PostGIS doesn't auto-shard spatially); pure high-QPS lat/long radius lookups where a purpose-built geospatial KV/index ([redis](redis.md) GEO, Elasticsearch geo) may be simpler; massive raster/imagery archives (object storage + tiling often beats in-DB raster). If you don't need transactions or SQL joins, the relational overhead is wasted.
- **Drivers/connectors:** Everything that talks to [postgresql](postgresql.md) — every ORM (GeoDjango, GeoAlchemy2, Rails + RGeo), GDAL/OGR, QGIS, GeoServer, dbt, CDC via Debezium/logical replication, BI tools. pgRouting for network routing builds on top.
- **Community/support/docs:** Large, active OSGeo-governed community; excellent reference docs and the well-known "Introduction to PostGIS" workshop. Commercial support from Crunchy Data and the managed cloud vendors. Learning curve is SQL plus spatial concepts (SRIDs/projections trip up newcomers constantly).

## Licensing & cost
- **OSS license:** GPL v2 (copyleft) — note this is *stricter* than [postgresql](postgresql.md)'s permissive PostgreSQL License. Using PostGIS does not force your application to be GPL (it's a database you query over the wire), but redistributing modified PostGIS is governed by GPL. See [license-taxonomy](../concepts/license-taxonomy.md). No post-2018 relicensing; it has always been GPL.
- **Self-managed vs managed:** Both. Self-host anywhere Postgres runs; or managed (AWS RDS/Aurora, GCP Cloud SQL/AlloyDB, Azure, Crunchy Bridge, Neon, Supabase) where PostGIS is a one-click extension. Minimal lock-in beyond standard Postgres.
- **Cost model:** Free software. Cost = the underlying Postgres deployment (per-node/instance, storage, IOPS). Scales cheaply on a single beefy node; cost inverts only when you need many replicas or hit the vertical ceiling.

## Hardware / deployment
- **Resource profile:** Mixed. Index/working set should fit in RAM (`shared_buffers`/OS cache) for fast spatial filtering; the exact-geometry refinement step is CPU-bound for complex shapes; large geometries/rasters are disk- and I/O-bound (TOAST). Geodetic (`geography`) math is more CPU-heavy than planar (`geometry`).
- **Storage assumptions:** NVMe/SSD strongly preferred (random index access); tolerates network-attached storage as well as Postgres does (EBS-class latency is fine for most workloads).
- **Footprint:** Single-node or clustered (via Postgres replication / [citus](citus.md)). Not embedded, not serverless on its own (though serverless-style managed Postgres with PostGIS exists, e.g. Neon, Aurora Serverless).
- **Deployment:** SaaS or on-prem; container/k8s-friendly via the official `postgis/postgis` image and Postgres operators (CloudNativePG, Crunchy PGO), with StatefulSet realities of any stateful Postgres.

## Bottom line
Reach for PostGIS when you have spatial data and already want — or can live within — a single-node-to-replicated [postgresql](postgresql.md): it gives you genuine ACID, real SQL spatial joins, and the richest open-source GIS function library, all for free. Don't reach for it expecting automatic horizontal scaling of spatial workloads (you'll be hand-rolling [citus](citus.md) or partitioning) or as a lightweight geo-lookup cache. The single biggest gotcha: spatial performance is entirely a function of GiST indexing and the bbox-then-refine query pattern — and a second, version-specific one: PostGIS/GEOS/PROJ version mismatches across nodes and at restore time silently change results or break dump loads.

## Sources
- [PostGIS official site](https://postgis.net/)
- [PostGIS documentation / manual](https://postgis.net/docs/)
- [PostGIS spatial indexing (workshop)](http://postgis.net/workshops/postgis-intro/indexing.html)
- [PostGIS release notes (3.6.2, Feb 2026)](https://postgis.net/docs/release_notes.html)
- [Crunchy Data — PostGIS performance: indexing and EXPLAIN](https://www.crunchydata.com/blog/postgis-performance-indexing-and-explain)
- [pgEdge — PostGIS spatial indexes (GiST/SP-GiST/BRIN)](https://docs.pgedge.com/postgis/development/data-management/spatial-indexes/)
- [PostGIS — Wikipedia](https://en.wikipedia.org/wiki/PostGIS)
