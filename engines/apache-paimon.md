---
name: Apache Paimon
slug: apache-paimon
adjacent: true
rank: n/a
category: table-format
data_model: Open lakehouse table format (LSM-based, primary-key + append)
license: Apache License 2.0 (permissive)
summary: LSM-tree open table format built for high-throughput streaming upserts and native changelog (CDC) on object storage; the streaming-first cousin of Iceberg.
last_researched: 2026-06-04
confidence: medium
---

# Apache Paimon

> An open lakehouse table format that puts an LSM-tree on top of object storage so streaming engines can do high-rate primary-key upserts and emit a native changelog — trading some batch-read efficiency for streaming freshness that [apache-iceberg](apache-iceberg.md)/[delta-lake](delta-lake.md) don't match natively.

## Identity / role
- Paimon is a **table format / lake storage layer**, not a query engine and not a streaming transport. It defines how data and metadata files sit in object storage and how engines ([apache-flink](apache-flink.md), [Apache Spark](apache-spark-sql.md)/[apache-spark-sql](apache-spark-sql.md), [trino](trino.md), [starrocks](starrocks.md), [clickhouse](clickhouse.md), Doris, Hive, Presto) read and write them. It is the same layer of the [lakehouse](../concepts/lakehouse.md) stack as [Iceberg, Delta, and Hudi](../concepts/open-table-formats.md).
- What it is **not**: it is not a database (no own compute/optimizer), not a message bus (it is a table, not a log — though it can produce a changelog stream), and not a catalog by itself (it ships a catalog API backed by filesystem/Hive/JDBC/REST).
- Origin: started as **Flink Table Store**, a Flink subproject; donated to the ASF incubator and renamed Paimon; graduated to a **Top-Level Project in March/April 2024** ([ASF announcement](https://www.globenewswire.com/en/news-release/2024/04/16/2863688/17401/en/Apache-Software-Foundation-Announces-New-Top-Level-Project-Apache-Paimon.html)). Heavy Alibaba/Ververica involvement.

## How it fits
- Architecture: data lives in **partitions → buckets**, and **each bucket is its own LSM tree** (sorted runs across levels, RocksDB-style leveled compaction). Writes buffer in memory and flush to sorted data files; metadata is an Iceberg-like tree per snapshot — a numbered snapshot file points to manifest-list → manifest → data files ([Vanlightly](https://jack-vanlightly.com/analyses/2024/7/3/understanding-apache-paimon-consistency-model-part-1)). This LSM design is the key differentiator from the copy-on-write/merge-on-read of [apache-iceberg](apache-iceberg.md), [delta-lake](delta-lake.md), and [apache-hudi](apache-hudi.md), and is what gives it minute/second-level upsert visibility.
- Problem it solves: cheap, high-throughput **streaming upserts and deletes by primary key** directly into a lake table, plus the ability to **read the table back as a CDC changelog stream** — the canonical Flink CDC → lake pattern (database [change-data-capture](../concepts/change-data-capture.md) landed into a queryable, mergeable table). Pairs most tightly with [apache-flink](apache-flink.md) (its native home) for ingest, and with [trino](trino.md)/[starrocks](starrocks.md)/[apache-spark-sql](apache-spark-sql.md) for query.
- Two table kinds: **primary-key tables** (upsert/merge) and **append-only tables** (log/event data, with small-file auto-compaction and ordered stream reads).
- **Merge engines** decide what happens when two rows share a PK: `deduplicate` (keep last), `partial-update` (column-wise fill-in across streams), `aggregation` (running aggregates), `first-row` (keep earliest). This is more semantically rich than other formats' upsert.

## Guarantees & consistency
- **Snapshot isolation** via numbered, gapless snapshot files; each commit atomically publishes a new snapshot root, so readers see a consistent point-in-time view. Concurrent writers use **optimistic concurrency** with conflict checks on commit ([Vanlightly](https://jack-vanlightly.com/analyses/2024/7/3/understanding-apache-paimon-consistency-model-part-1)). See [isolation-levels](../concepts/isolation-levels.md). ⚠️ unverified — exact behavior of two writers racing on the same bucket (retry vs. hard failure) is implementation-specific and version-dependent; validate against your Paimon version.
- **Streaming read consistency:** with Flink, data is visible only after a checkpoint, so streaming reads inherit Flink's transactional, **exactly-once** checkpoint semantics ([docs](https://paimon.apache.org/docs/master/primary-key-table/changelog-producer/)). The lake table itself is the durable store; durability tracks the object store's, with the [data-loss window](../concepts/wal-and-durability.md) bounded by the producer's checkpoint interval rather than a per-row WAL.
- **Changelog producers** (how a correct UPDATE_BEFORE/UPDATE_AFTER changelog is emitted for downstream streaming consumers): `input` (trust the source is already a complete changelog, e.g. DB CDC), `lookup` (look up prior values before commit; recommended default), `full-compaction` (diff successive full compactions — correct but expensive). Choice is a correctness/cost tradeoff: `none`/`input` on non-changelog input can emit wrong downstream changes ([docs](https://paimon.apache.org/docs/master/primary-key-table/changelog-producer/)).
- **Deletion vectors** (RoaringBitmap per bucket) mark deleted rows without rewriting files, giving merge-on-read tables faster point reads; readers skip uncompacted level-0 when DVs are enabled.
- CAP: N/A — it is a storage format over an object store, not a replicated distributed database; consistency is the object store's plus snapshot-commit atomicity.

## Interfaces & integration
- **Write/ingest:** primarily [apache-flink](apache-flink.md) (SQL + DataStream, the most mature path), [apache-spark-sql](apache-spark-sql.md); Flink CDC connectors do whole-database sync into Paimon.
- **Read/query:** [apache-flink](apache-flink.md), [apache-spark-sql](apache-spark-sql.md), [trino](trino.md), Presto, [starrocks](starrocks.md), Doris, [clickhouse](clickhouse.md), Hive — via Paimon catalog/connector plugins. SQL is the main interface; there is also a Java API.
- **Catalog:** filesystem, Hive Metastore, JDBC, and a REST catalog. ⚠️ unverified — breadth/maturity of the REST catalog and any Iceberg-compatibility/export bridge varies by version; confirm before relying on cross-format interop.
- Read maturity outside Flink/Spark is generally younger than Iceberg's broad engine support; verify connector versions.

## Operations & maturity
- **Deployment:** no service to run for the format itself — it is files in object storage plus engine plugins. Operational burden moves to the **writer job (usually a long-running Flink streaming job)** and to **compaction**: LSM tables need ongoing compaction (inline in the writer or as dedicated compaction jobs) or read amplification and small-file counts degrade query latency. This is the main day-2 cost.
- **Maturity:** TLP since 2024; production use is concentrated around Flink-heavy shops (notably in China — Alibaba, ByteDance, and others). Younger and narrower ecosystem than [apache-iceberg](apache-iceberg.md); fewer independent third-party validations. No public Jepsen report.
- **Known sharp edges:** wrong `changelog-producer` choice producing incorrect downstream CDC; compaction lag under high write rates; over-bucketing/under-bucketing hurting parallelism (bucket count is a real tuning knob); reads from engines other than Flink/Spark lagging in features.
- **Governance:** ASF community project, but de-facto roadmap leadership and committer concentration lean heavily toward Alibaba/Ververika. ⚠️ unverified — degree of contributor diversity today.

## Licensing & cost
- **[License](../concepts/license-taxonomy.md):** Apache License 2.0 — fully permissive, vendor-neutral, no source-available/relicensing traps.
- Open and self-hostable; the only cost is your object storage + compute engines. Managed offerings exist (e.g. Alibaba Cloud Realtime Compute for Flink); no single canonical vendor SaaS the way Databricks anchors [delta-lake](delta-lake.md). Lock-in risk is low at the format level but you inherit a strong gravitational pull toward Flink for the streaming-write path.

## Bottom line
- Reach for Paimon when your central requirement is **high-throughput streaming upserts/deletes by primary key into a lake**, or you need the lake table to **emit a correct CDC changelog** for downstream streaming — especially if Flink is already your processing engine. Its LSM design genuinely beats Iceberg/Delta/Hudi on continuous mutation freshness.
- Do **not** pick it for batch-only analytics, broad multi-engine BI interop, or "we already standardized on Iceberg" shops — [apache-iceberg](apache-iceberg.md) has wider engine/catalog support and a bigger, more diverse community. The biggest gotcha: you are signing up for **continuous compaction management and a correct changelog-producer configuration**; get either wrong and you get degraded read latency or silently incorrect downstream change streams.

## Sources
- [Apache Paimon official docs](https://paimon.apache.org/docs/master/)
- [Changelog Producer — Paimon docs](https://paimon.apache.org/docs/master/primary-key-table/changelog-producer/)
- [apache/paimon on GitHub](https://github.com/apache/paimon)
- [Jack Vanlightly — Understanding Apache Paimon's Consistency Model, Part 1](https://jack-vanlightly.com/analyses/2024/7/3/understanding-apache-paimon-consistency-model-part-1)
- [ASF announcement: Paimon graduates to Top-Level Project (2024)](https://www.globenewswire.com/en/news-release/2024/04/16/2863688/17401/en/Apache-Software-Foundation-Announces-New-Top-Level-Project-Apache-Paimon.html)
- [Ververica — Apache Paimon: the Streaming Lakehouse](https://www.ververica.com/blog/apache-paimon-the-streaming-lakehouse)
