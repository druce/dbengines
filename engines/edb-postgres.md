---
name: EDB Postgres
slug: edb-postgres
rank: 144
data_model: Relational
license: Proprietary (source-available core PostgreSQL + closed EDB extensions; commercial subscription)
summary: EnterpriseDB's commercial PostgreSQL distribution — adds Oracle compatibility, TDE, and multi-master replication on top of upstream Postgres.
last_researched: 2026-06-04
confidence: high
---

# EDB Postgres

> A commercially-licensed PostgreSQL distribution from EnterpriseDB whose real selling points are Oracle-compatibility (PL/SQL, packages, SQL*Loader-alike) and enterprise add-ons (TDE, multi-master replication) — it *is* Postgres, with proprietary layers bolted on.

"EDB Postgres" is an umbrella for EnterpriseDB's distributions, most notably **EDB Postgres Advanced Server (EPAS)**. EPAS = upstream [postgresql](postgresql.md) + closed-source EDB enhancements. The lower tier, **EDB Postgres Extended Server (PGE)**, is closer to community Postgres but adds TDE and tighter [EDB Postgres Distributed](edb-postgres.md) integration ([EDB distributions](https://www.enterprisedb.com/docs/edb-postgres-ai/databases/postgres_distributions/)). Where this page says nothing EDB-specific, [postgresql](postgresql.md) semantics apply unchanged.

## Identity
- **Taxonomy / data model:** relational (multi-model in the same sense as Postgres: native JSON/JSONB, arrays, geospatial via PostGIS, vectors via pgvector).
- **Storage model:** row-store heap tables, B-tree primary index, MVCC versioning — identical to upstream Postgres ([lsm-vs-btree](../concepts/lsm-vs-btree.md), [mvcc](../concepts/mvcc.md)). On-disk format is standard Postgres, optionally encrypted at rest via EDB TDE (AES-128/256, v15+) ([TDE docs](https://www.enterprisedb.com/docs/tde/latest/)).
- **Workload:** OLTP-first, like [postgresql](postgresql.md). Not an HTAP/analytics engine; for columnar/OLAP you bolt on external tooling. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **Single-node EPAS:** same CAP/isolation story as [postgresql](postgresql.md) — N/A as a distributed system on its own.
- **CAP under partition:** depends on topology. Plain EPAS with streaming physical replication is **CP-ish single-leader**: one writable primary, async or sync standbys. With **[EDB Postgres Distributed](edb-postgres.md) (PGD/BDR)** multi-master mesh, default replication is **asynchronous → AP / eventual consistency** ("within seconds usually") ([PGD conflicts](https://www.enterprisedb.com/docs/pgd/latest/bdr/conflicts/)). See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** PGD default async = **PA/EL** (stays available under partition, favors latency else). Stronger guarantees come from **commit scopes** — Group Commit / Eager All-Node use Raft to reach a quorum (ALL or MAJORITY) commit decision, shifting toward **PC/EC** at the cost of latency ([Group Commit](https://www.enterprisedb.com/docs/pgd/latest/commit-scopes/group-commit/), [Eager replication](https://www.enterprisedb.com/docs/pgd/4/bdr/eager/)). See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Default isolation & what's achievable:** inherits Postgres MVCC — Read Committed default; Repeatable Read = snapshot isolation; Serializable via SSI. See [isolation-levels](../concepts/isolation-levels.md). In async (default) multi-master PGD, cross-node serializability is **not** provided — writers commit conflicting rows that are reconciled later by conflict policy (LWW/CRDT), so single-node isolation does not extend across the mesh. Group Commit's *eager* conflict resolution instead aborts conflicting transactions with a serialization error as part of the commit agreement ([Group Commit](https://www.enterprisedb.com/docs/pgd/latest/commit-scopes/group-commit/)).
- **Replication:** single-leader physical streaming (sync/async) for HA; **multi-master logical** via PGD/BDR. Default async conflict resolution is row-level **last-write-wins**; opt-in **CRDTs** (with column-level conflict detection) instead *merge* concurrent updates for "strong eventual consistency" / mathematically sound convergence rather than discarding a row ([PGD conflicts](https://www.enterprisedb.com/docs/pgd/latest/bdr/conflicts/), [PGD CRDTs](https://www.enterprisedb.com/docs/pgd/latest/conflict-management/crdt/)). Failover/leader election in PGD uses Raft. See [replication-models](../concepts/replication-models.md), [crdts](../concepts/crdts.md).
- **Tunable consistency?** Yes, in PGD via per-transaction/commit-scope settings (async, Group Commit, Eager).
- **Clock dependency:** no TrueTime requirement; conflict resolution uses timestamps for LWW, so clock skew can affect which write "wins" in LWW mode. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write**, rigid relational, same as Postgres; schema-on-read possible via JSONB.
- **Migration/evolution:** standard Postgres online DDL caveats (many `ALTER`s take brief locks; some rewrites are expensive). EPAS adds Oracle-style `EDB*Loader` bulk loading and Oracle-compatible DDL syntax.
- **Type system:** full Postgres types plus Oracle-compatible types (e.g. `NUMBER`, `VARCHAR2`, `DATE` with Oracle semantics) for migration fidelity ([Oracle compatibility](https://www.enterprisedb.com/docs/epas/latest/working_with_oracle_data/02_enhanced_compatibility_features/)).

## Query interface
- **Language:** SQL (PostgreSQL dialect) **plus EDB's SPL**, an Oracle PL/SQL-compatible procedural language — supports Oracle-style stored procedures, functions, triggers, and **packages**, plus Oracle data-dictionary-compatible views and built-in packages (`DBMS_*` analogs) ([compatibility features](https://www.enterprisedb.com/docs/epas/latest/working_with_oracle_data/02_enhanced_compatibility_features/)).
- **Transactions:** full multi-statement ACID on a single node (Postgres MVCC). Across PGD nodes, atomicity is per-node unless a synchronous commit scope is used.
- **Native vs app-side:** native joins, secondary indexes, aggregations, window functions, CTEs — all Postgres.
- **Stored procedures / UDFs:** SPL (Oracle PL/SQL-compatible), PL/pgSQL, and all Postgres PLs (PL/Python, PL/Perl, etc.). **EDB*Plus** gives an Oracle SQL*Plus-style CLI; the Open Client Library mimics Oracle OCI for app portability.

## Scaling & topology
- **Vertical first**, like Postgres. Horizontal write scaling via **[EDB Postgres Distributed](edb-postgres.md)** multi-master mesh (active-active) or read scaling via streaming read replicas.
- **Sharding:** not built into core EPAS; PGD does data distribution/replication rather than transparent hash sharding. ⚠️ unverified — no automatic resharding comparable to a native sharded store.
- **Read replicas:** physical standbys; reads are eventually consistent unless using synchronous replication.
- **Storage/compute separation:** not in the self-managed engine; EDB's managed cloud offerings layer this externally. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** standard Postgres WAL, `fsync`/`synchronous_commit` tunables, group commit — same data-loss window semantics as upstream. See [wal-and-durability](../concepts/wal-and-durability.md). EDB claims TDE adds <7.5% transaction overhead ([TDE launch blog](https://www.enterprisedb.com/blog/TDE-Postgres-Advanced-Server-15-Launch)) — vendor benchmark, treat as directional.
- **Throughput/latency:** essentially Postgres profile. EDB markets PGD logical replication as "up to 5X faster than native logical replication" ([Replication Server vs PGD](https://mktgsite.enterprisedb.com/blog/replication-server7-vs-postgres-distributed5)) — marketing figure, workload-dependent.
- **Compaction/vacuum/GC:** inherits Postgres MVCC bloat and `VACUUM`/autovacuum behavior; long transactions and high churn drive p99 the same way they do on stock Postgres. See [mvcc](../concepts/mvcc.md).

## Operations & maturity
- **Backup/restore, PITR:** standard Postgres PITR plus EDB's **Barman** (backup/recovery manager) tooling; snapshots via underlying storage.
- **Observability:** EXPLAIN/plans, slow-query logging, `pg_stat_*` — all Postgres; EDB Postgres AI / PEM (Postgres Enterprise Manager) adds a GUI monitoring/management console.
- **Upgrade story:** in-place/`pg_upgrade` plus EDB tooling; PGD supports rolling upgrades across the mesh. Day-2 burden is Postgres-like plus the added complexity of the proprietary HA/replication stack.
- **Maturity:** EnterpriseDB is a long-established Postgres vendor and a major upstream contributor; EPAS is widely used in regulated enterprises migrating off Oracle. **No independent jepsen.io / Kyle Kingsbury audit of PGD/BDR exists.** EDB instead ran its *own* validation using the Jepsen framework and published a blog series (Sept 2024); notably that internal testing found "rare cases when update conflicts cause data divergence among nodes," which EDB said it was continuing to refine ([EDB internal Jepsen-framework validation](https://www.enterprisedb.com/blog/validating-edb-postgres-distributed-continuous-high-availability-and-consistency-active)). Treat as vendor-run, not an independent formal audit.

## Ecosystem & people
- **Canonical use cases:** **Oracle migration** (the headline reason to choose EPAS over plain Postgres), regulated enterprises needing vendor support + TDE + active-active HA, organizations standardizing on Postgres but wanting a single commercial throat to choke.
- **Anti-patterns:** greenfield apps with no Oracle baggage (use community [postgresql](postgresql.md) and save the license fee); analytics/OLAP (wrong engine); teams wanting fully open-source, no-lock-in stacks — the value-add layers are proprietary.
- **Drivers/connectors:** full Postgres driver ecosystem (JDBC/ODBC/psql/ORMs), EDB-specific JDBC/.NET/OCI-compatible drivers, dbt/Kafka/BI all work via the Postgres wire protocol; CDC via logical replication.
- **Community/support:** commercial support is the point; docs are thorough; learning curve is Postgres + EDB-specific HA tooling.

## Licensing & cost
- **License:** **proprietary / commercial**. The core is PostgreSQL (permissive), but EDB's enhancements (Oracle compatibility, TDE, EPAS-specific features) are closed and governed by a paid subscription or a restrictive **Limited Use License** (no SaaS resale, no benchmark publication without consent, no reverse engineering) ([EDB licensing](https://www.enterprisedb.com/enterprisedb-licensing-and-business-agreements), [Limited Use License](https://www.enterprisedb.com/limited-use-license)). This is *not* open source — see [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** both — self-managed subscriptions (Developer/Standard/Enterprise tiers), EDB Postgres AI managed cloud, and an IBM-distributed offering.
- **Lock-in:** moderate-to-high — apps written against SPL/packages/Oracle-compat features and EPAS-only catalog views do not run on community Postgres without rework; that is the inverse of the lock-in escape it sells against Oracle.
- **Cost model:** per-core/per-node subscription; cheap relative to Oracle, a premium over free Postgres.

## Hardware / deployment
- **Resource profile:** same as Postgres — benefits from RAM for cache (`shared_buffers` + OS page cache), CPU for query/connection load; working set need not fit in RAM but performance degrades when it doesn't.
- **Storage assumptions:** local NVMe ideal; tolerates network-attached storage with the usual latency caveats.
- **Footprint:** single-node, clustered (streaming HA or PGD mesh); not embedded, not serverless in the core product.
- **Deployment:** on-prem, VM, container, Kubernetes (EDB ships operators including PGD-for-Kubernetes); SaaS via EDB Postgres AI cloud.

## Bottom line
Reach for EDB Postgres when you are **migrating off Oracle** and want PL/SQL, packages, and Oracle-compatible tooling so your existing code mostly just runs — or when you need a commercially-supported Postgres with TDE and active-active multi-master HA in one package. Do not reach for it for greenfield apps (community [postgresql](postgresql.md) is free and equivalent for most needs) or for analytics. The single biggest gotcha: the enterprise value-add is **proprietary and creates its own lock-in**, and the multi-master (PGD) story is **asynchronous/eventually-consistent by default** with only vendor-run (not independent) Jepsen-framework testing — which itself surfaced rare update-conflict data divergence — so strong single-node Postgres isolation does not automatically extend across the replication mesh.

## Sources
- [EDB Postgres distributions overview](https://www.enterprisedb.com/docs/edb-postgres-ai/databases/postgres_distributions/)
- [EPAS Oracle compatibility features](https://www.enterprisedb.com/docs/epas/latest/working_with_oracle_data/02_enhanced_compatibility_features/)
- [EDB Transparent Data Encryption docs](https://www.enterprisedb.com/docs/tde/latest/)
- [EDB Postgres Distributed — conflicts/CRDTs](https://www.enterprisedb.com/docs/pgd/latest/bdr/conflicts/)
- [PGD Group Commit / commit scopes](https://www.enterprisedb.com/docs/pgd/latest/commit-scopes/group-commit/)
- [PGD Eager replication (Raft commit)](https://www.enterprisedb.com/docs/pgd/4/bdr/eager/)
- [PGD CRDTs](https://www.enterprisedb.com/docs/pgd/latest/conflict-management/crdt/)
- [EDB internal Jepsen-framework validation of PGD (blog, Sept 2024)](https://www.enterprisedb.com/blog/validating-edb-postgres-distributed-continuous-high-availability-and-consistency-active)
- [EDB licensing & business agreements](https://www.enterprisedb.com/enterprisedb-licensing-and-business-agreements)
- [EDB Limited Use License](https://www.enterprisedb.com/limited-use-license)
