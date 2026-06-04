---
name: Apache Kudu
slug: apache-kudu
adjacent: true
rank: n/a
category: real-time-olap
data_model: Columnar storage engine for mutable analytic tables
license: Apache License 2.0 (permissive)
summary: Columnar storage engine that takes fast scans AND low-latency random updates — closing the HDFS/Parquet gap of "either bulk-immutable or row-by-row," but it needs a separate query engine on top.
last_researched: 2026-06-04
confidence: high
---

# Apache Kudu

> A distributed, columnar **storage engine** (not a query engine) that supports both fast OLAP scans and low-latency random inserts/updates/deletes — built to replace the awkward HDFS+Parquet ("immutable") plus HBase ("mutable") two-system pattern for changing analytic data.

## Identity / role
- **What it is:** a storage engine for structured, mutable, analytic data. Tables have a fixed schema, a typed primary key, and are range/hash-partitioned into **tablets**; each tablet is Raft-replicated across tablet servers. Columnar on-disk layout for scan speed.
- **What it is NOT:** it is *not* a SQL engine, not a general OLTP database, and not a file format. You almost always pair it with [apache-impala](apache-impala.md) (or [apache-spark-sql](apache-spark-sql.md)) for SQL — Kudu itself exposes only an insert/scan/mutate API plus predicate pushdown. Contrast with [real-time-olap](../concepts/real-time-olap.md) stores like [clickhouse](clickhouse.md)/[apache-druid](apache-druid.md)/[starrocks](starrocks.md) that bundle storage + query in one process.
- **Niche:** the gap between immutable bulk analytics ([columnar-storage](../concepts/columnar-storage.md) like Parquet/[open-table-formats](../concepts/open-table-formats.md)) and random-access KV ([apache-hbase](apache-hbase.md)). It is "[HTAP](../concepts/oltp-olap-htap.md)-ish" only in the narrow sense of mutable-yet-scannable; it is firmly analytic, append-mostly.

## How it fits
- **Architecture:** one or more **masters** (catalog + tablet placement, Raft-replicated) and many **tablet servers**. A table is split by primary key into tablets; each tablet has typically 3 (or 5) replicas with a Raft-elected leader that accepts writes and replicates to followers. A write is acked once persisted on a **majority** of replicas. See [consensus-raft-paxos](../concepts/consensus-raft-paxos.md).
- **Dual storage structure (the key trick):** to serve both fast columnar scans and O(log n) random updates — contradictory goals — each tablet keeps a row-set design: recent inserts in an in-memory MemRowSet (row-format), flushed to immutable columnar **DiskRowSets**, with updates/deletes captured in separate **delta stores** (REDO/UNDO deltas) that are compacted back into base data over time. This is conceptually [LSM-like](../concepts/lsm-vs-btree.md) (memstore + flushed files + compaction), but base files are columnar rather than row SSTables.
- **What it pairs with:** [apache-impala](apache-impala.md) for low-latency SQL; [apache-spark-sql](apache-spark-sql.md) for batch/ML; NiFi/Kafka/[apache-flink](apache-flink.md) for streaming ingest; apache-nifi connectors. Not part of the [lakehouse](../concepts/lakehouse.md) open-table-format world — it owns its own storage on local disk, not object storage.

## Guarantees & consistency
- **Single-row writes are atomic and strict-serializable within a tablet.** [Multi-row writes are NOT atomic unless wrapped in a multi-tablet transaction](https://kudu.apache.org/docs/transaction_semantics.html); a failed row in a batch yields a per-row error, not a rollback.
- **Multi-table/multi-tablet transactions exist** (since ~1.15/CDP) but are limited: [INSERT / INSERT_IGNORE only, read-committed isolation, with wait-die deadlock avoidance](https://kudu.apache.org/docs/transaction_semantics.html). Not general-purpose ACID — no UPDATE/DELETE in a transaction. ⚠️ unverified — whether later releases broadened transactional DML beyond INSERT.
- **Read modes** ([isolation-levels](../concepts/isolation-levels.md)): `READ_LATEST` (default, read-committed, no repeatable reads); `READ_AT_SNAPSHOT` (repeatable snapshot at a timestamp; server waits until the timestamp is "safe"); `READ_YOUR_WRITES` (session monotonicity). Default cluster mode is **snapshot consistency**.
- **External consistency** is tunable ([Kudu docs](https://kudu.apache.org/docs/transaction_semantics.html)): `CLIENT_PROPAGATED` (default — externally consistent for a single client automatically; cross-client requires manually propagating a timestamp token) and `COMMIT_WAIT` (experimental, Spanner-style; waits out clock uncertainty for true external consistency).
- **Clock dependency:** correctness of snapshot/strict-serializable reads uses a hybrid logical+physical clock; `COMMIT_WAIT` in particular [requires tight NTP sync and pays a 100ms–1s latency penalty](https://kudu.apache.org/docs/transaction_semantics.html). See [clocks-and-time](../concepts/clocks-and-time.md). Tablet servers can crash if clock skew exceeds the configured bound — a known operational gotcha.
- **CAP:** CP for a tablet — a tablet stays available for reads/writes only while a majority of its replicas are up; otherwise it refuses writes rather than diverge. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Durability:** per-tablet write-ahead log fsync'd before majority ack ([wal-and-durability](../concepts/wal-and-durability.md)); data-loss window is bounded by Raft majority survival.
- No Jepsen report I could find. ⚠️ unverified — no public Jepsen analysis of Kudu's consistency claims.

## Interfaces & integration
- **APIs:** native C++, Java, and Python client libraries (insert/upsert/update/delete/scan with predicate + projection pushdown). No native SQL.
- **SQL via engines:** [apache-impala](apache-impala.md) is the canonical low-latency SQL front end (full DML + DDL on Kudu tables); [apache-spark-sql](apache-spark-sql.md) via the Spark-Kudu connector. Also Hive and Presto/[trino](trino.md) connectors exist.
- **Ingest:** Kafka/NiFi/Spark streaming; the old kudu-mapreduce and Flume sink integrations were removed (use Spark/Impala/NiFi instead).
- **Schema:** strongly typed, schema-on-write, required primary key; supports column encodings (dictionary, bitshuffle, RLE) and per-column compression. Limited online schema evolution (add/drop/rename columns); primary key is immutable and cannot be changed after creation.

## Operations & maturity
- **Deployment:** a clustered, stateful system (masters + tablet servers) running on local disk (NVMe/SSD strongly preferred). Not embedded, not serverless, not object-storage-backed. k8s StatefulSet deployment is possible but it is a classic on-prem/colocated-with-Impala Hadoop-era component.
- **Maturity:** Apache top-level project since 2016; production-proven, especially in cloudera CDP deployments for time-series, IoT, fraud, and operational-reporting workloads. Stable, but **project velocity has slowed markedly** — it is a mature, niche system rather than a fast-moving one.
- **Known failure modes:** clock-skew-induced crashes; Raft leader-lock contention causing tablet-service queue overflows ([KUDU-2727](https://issues.apache.org/jira/browse/KUDU-2727)); hot-spotting on monotonic primary keys (mitigate with hash partitioning); scaling limits — historically guidance was on the order of low-thousands of tablets per server and recommended total data per tablet server in the low single-digit TB range (verify against current limits). ⚠️ unverified — exact current scaling ceilings.
- **Governance:** ASF community project; development and commercial support have been heavily Cloudera-driven, which is also a concentration risk as Cloudera's focus shifts.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, no source-available restrictions. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Open vs vendor:** genuinely open and self-hostable; no single-vendor cloud lock-in for the engine itself, though most production use is bundled inside Cloudera CDP/CDH.
- **Cost model:** no per-query/serverless pricing — you pay for the cluster (compute + local SSD) you run. Managed offering is effectively "via Cloudera," not a standalone Kudu SaaS.

## Bottom line
- Reach for Kudu when you have **fast-arriving, frequently-updated structured data that must also be scanned analytically in near-real-time** (IoT/time-series, change-data feeds, mutable dimension/fact tables) and you are already in an Impala/Spark/Cloudera stack on local disk. It uniquely solves "mutable + columnar + scannable" in one engine.
- Do **not** reach for it as a standalone database (no SQL of its own), for general OLTP (no rich multi-row ACID), or for a cloud-native [lakehouse](../concepts/lakehouse.md) on object storage — Kudu wants local SSD and a query engine on top, and the modern open-table-format world ([open-table-formats](../concepts/open-table-formats.md) + [trino](trino.md)/[databricks](databricks.md)) or a self-contained [real-time-olap](../concepts/real-time-olap.md) store ([clickhouse](clickhouse.md)/[starrocks](starrocks.md)/[apache-druid](apache-druid.md)) has absorbed much of its mind-share. **Biggest gotcha:** it depends on synchronized clocks for its consistency guarantees, and excessive clock skew can crash tablet servers outright.

## Sources
- [Apache Kudu — Overview](https://kudu.apache.org/overview.html)
- [Apache Kudu — Transaction Semantics](https://kudu.apache.org/docs/transaction_semantics.html)
- [Apache Kudu — Consistency in Apache Kudu, Part 1](https://kudu.apache.org/2017/09/18/kudu-consistency-pt1.html)
- [Apache Kudu — FAQ](https://kudu.apache.org/faq.html)
- [Kudu whitepaper (kudu.tex, apache/kudu)](https://github.com/apache/kudu/blob/master/docs/whitepaper/kudu.tex)
- [Cloudera — Apache Kudu Concepts and Architecture](https://docs.cloudera.com/documentation/enterprise/6/6.3/topics/kudu_concepts_architecture.html)
- [KUDU-2727 — Raft consensus lock contention](https://issues.apache.org/jira/browse/KUDU-2727)
