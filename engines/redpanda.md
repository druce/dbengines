---
name: Redpanda
slug: redpanda
adjacent: true
rank: n/a
category: streaming-platform
data_model: Event log / Kafka-compatible streaming platform
license: Source-available (Redpanda BSL, converts to Apache-2.0 after 4 years) + RCL for enterprise features
summary: Kafka-API-compatible streaming log rewritten in C++ — single binary, no JVM, no ZooKeeper, Raft per partition.
last_researched: 2026-06-04
confidence: high
---

# Redpanda

> A drop-in Kafka-protocol streaming log written in C++ (Seastar, thread-per-core), shipping as one self-contained binary with Raft replication instead of a JVM + ZooKeeper/KRaft stack — built for low tail latency and simpler ops, at the cost of being a single-vendor project.

## When to use

**Use Redpanda if:**
- ✅ You want Kafka semantics with lower p99 latency and dramatically simpler ops — one binary, no JVM, no ZooKeeper/KRaft.
- ✅ You run on a small number of fast-NVMe nodes where per-partition Raft + fsync-on-majority pays off.
- ✅ Existing Kafka clients/connectors should work unchanged, and you want streams to land directly as Iceberg tables.

**Avoid Redpanda if:**
- ❌ You need ASF-governed open-source neutrality — the BSL forbids competing-service use and the project is single-vendor.
- ❌ Your storage is slow or network-attached — the thread-per-core + fsync-on-majority design assumes fast local disks, and on slow storage you lose the latency advantage that justifies it.
- ❌ You expect it to *process* data — it is a log, not a stream-processing or query engine; you still need Flink/clients downstream.
- ❌ You need the Tiered Storage / Iceberg features for free — those are paid enterprise (RCL) add-ons.

## Identity / role
- **What it is:** an append-only, partitioned, replicated **event log / streaming platform** that speaks the Kafka wire protocol. It is transport + durable buffer for event streams, the same role [apache-kafka](apache-kafka.md) plays. See [streaming-platforms](../concepts/streaming-platforms.md).
- **What it is NOT:** not a database and not a query engine — you do not run analytical SQL over the log itself. It is a log, not a store you query; downstream consumers ([apache-flink](apache-flink.md), [clickhouse](clickhouse.md), [apache-spark-sql](apache-spark-sql.md), stream processors, materialized-view engines) do the computation. It is also not a stream-processing engine in the [apache-flink](apache-flink.md) sense — processing is done by external Kafka clients (its bundled **Redpanda Connect**, formerly Benthos, handles connectors/transforms; lightweight WASM "data transforms" run in-broker).
- **Positioning vs Kafka:** same external contract (Kafka API, partitions, consumer groups, offsets), different implementation — a single C++ binary that bundles broker, Raft consensus, Schema Registry, and an HTTP/REST proxy, with no separate JVM or coordination tier.

## How it fits
- **Architecture:** thread-per-core ([Seastar](https://seastar.io/)) C++ runtime that pins shards to cores and uses its own memory/IO scheduler, avoiding JVM garbage-collection pauses. Each topic partition is its own [Raft](../concepts/consensus-raft-paxos.md) group (vs Kafka's ISR + KRaft controller model), so replication and leadership are per-partition. No external metadata store — cluster metadata is itself Raft-replicated internally. ([architecture overview](https://github.com/redpanda-data/redpanda))
- **Problem it solves:** removes Kafka's operational sprawl (JVM tuning, GC pauses, separate ZooKeeper/KRaft, page-cache reliance) and targets lower, more predictable p99 latency on the same or fewer nodes.
- **Tiered Storage (enterprise):** offloads cold log segments to object storage (S3 / GCS / Azure Blob), keeping hot data on local NVMe — a [storage-compute-separation](../concepts/storage-compute-separation.md)-style move that decouples retention from local disk size. ([tiered storage docs](https://docs.redpanda.com/current/manage/tiered-storage/))
- **Iceberg Topics (enterprise):** can materialize topic data into [apache-iceberg](apache-iceberg.md) tables in object storage, mapped via Schema Registry (Avro/Protobuf) or key_value mode, so streams land directly in a [lakehouse](../concepts/lakehouse.md) queryable by [snowflake](snowflake.md) / [apache-spark-sql](apache-spark-sql.md) / [trino](trino.md) / [clickhouse](clickhouse.md) without a separate ETL/sink connector. ([Iceberg topics docs](https://docs.redpanda.com/current/manage/iceberg/about-iceberg-topics/))
- **Pairs with:** any Kafka client/connector ecosystem, [CDC](../concepts/change-data-capture.md) tooling (Debezium), stream processors ([apache-flink](apache-flink.md), Kafka Streams), and CDC/analytics sinks.

## Guarantees & consistency
- **Durability:** with `acks=all`, Redpanda **fsyncs to disk on a majority of replicas before acknowledging** — it does not rely on the OS page cache the way Kafka traditionally does. This narrows the [data-loss window](../concepts/wal-and-durability.md) but costs latency/throughput; weaker `acks` settings trade durability for speed. ([durability docs](https://docs.redpanda.com/current/develop/produce-data/configure-producers/))
- **Replication consistency:** per-partition [Raft](../concepts/consensus-raft-paxos.md) — a write commits only after majority quorum, giving leader-based strong consistency for a single partition's log. There are no cross-partition transactional guarantees beyond the Kafka transaction protocol.
- **Delivery semantics:** at-least-once by default; **idempotent producer** (`enable.idempotence=true`, requires `acks=all`) deduplicates retries; **exactly-once (EOS)** is available via Kafka-style transactions (atomic multi-partition writes, read-process-write). ([transactions docs](https://docs.redpanda.com/current/develop/transactions/)) Note: "exactly-once" here is the Kafka EOS contract within the cluster — end-to-end EOS still depends on consumer behavior and is not magic.
- **Isolation:** consumers can read `read_committed` to hide aborted-transaction writes. The Kafka transaction model permits write-write interleaving (a G0-style cycle) between concurrent transactions — this is a protocol property, not Redpanda-specific.
- **Jepsen:** [Jepsen tested Redpanda 21.10.1 (2022)](https://jepsen.io/analyses/redpanda-21.10.1) and found serious safety issues at the time — duplicate writes despite idempotence, inconsistent offsets from a Raft commit bug, **lost/stale acknowledged messages even at `acks=all` + `read_committed`**, aborted reads, and lost transactional writes. Most were fixed by 21.11.15; Redpanda also defaulted idempotence on. Treat pre-22.x as unsafe and follow the report's config guidance (idempotence on, `acks=all`, adequate replication). The report praised it as easy to install and operate.
- **CAP:** per-partition Raft is **CP** under partition — a partition with no quorum-electable leader rejects writes rather than diverging. See [cap-pacelc](../concepts/cap-pacelc.md).

## Interfaces & integration
- **Wire protocol:** Kafka API — existing Kafka clients (librdkafka/confluent-kafka, kafka-python, Sarama, Kafka Streams) and most connectors work unchanged. ⚠️ unverified — compatibility is broad but not 100%; very new or obscure broker APIs can lag.
- **Bundled:** Schema Registry (Confluent-compatible REST), Kafka REST/HTTP proxy, and `rpk` CLI — all in the one binary; **Redpanda Connect** (Benthos-derived) supplies connectors and stream transforms; in-broker **WASM data transforms** for lightweight per-record processing.
- **Read/write interop:** because it is Kafka-compatible, the same producers/consumers/connectors that integrate Kafka with [apache-flink](apache-flink.md), [clickhouse](clickhouse.md), Druid, Snowpipe, etc. apply. Iceberg Topics additionally expose stream data to any [Iceberg](../concepts/open-table-formats.md) reader.

## Operations & maturity
- **Deployment:** single statically-linked binary; Kubernetes operator and Helm charts; managed **Redpanda Cloud** (BYOC and fully hosted). Fewer moving parts than Kafka — no ZooKeeper/KRaft to run.
- **Ops burden:** lower setup/coordination overhead, but the thread-per-core model expects fast local disks (NVMe) and benefits from careful CPU/core sizing; it is more sensitive to slow/network-attached storage than Kafka's page-cache approach.
- **Maturity:** company founded 2019, GA-grade by ~2021; widely deployed in production. Younger and far less battle-tested than [apache-kafka](apache-kafka.md), and the early Jepsen results are a reminder that the distributed-systems surface took time to harden.
- **Governance:** **single-vendor** project (Redpanda Data, Inc.), not an Apache Software Foundation community project. Roadmap, releases, and the source-available license are controlled by the vendor — a key contrast with Kafka's ASF governance.

## Licensing & cost
- **Core:** **Redpanda Business Source License (BSL)** — source-available, free to self-host, but you may not offer Redpanda as a competing managed streaming service; each commit's BSL grant **converts to Apache-2.0 four years later**. ([license post](https://www.redpanda.com/blog/bsl-source-available-license)) This is *not* OSI open source. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Enterprise features:** Tiered Storage, Iceberg Topics, data balancing, remote read replicas, SSO/RBAC, audit logging are under the **Redpanda Community License (RCL)** and require a paid/enterprise license (new clusters get a 30-day trial). ([licensing overview](https://docs.redpanda.com/current/get-started/licensing/overview/))
- **Cost model:** self-managed = your hardware + enterprise license for advanced features; Redpanda Cloud is usage/throughput-based managed pricing. Lock-in risk is moderate — the Kafka API is portable, but Tiered Storage layout, Iceberg integration, and enterprise features are vendor-specific.

## Bottom line
- Reach for Redpanda when you want Kafka semantics with **lower p99 latency and dramatically simpler operations** (one binary, no JVM/ZooKeeper) — especially on a small number of fast-NVMe nodes, or when you want streams to land directly as [apache-iceberg](apache-iceberg.md) tables. Do **not** reach for it if you need ASF-governed open-source neutrality (the BSL forbids competing-service use and the project is single-vendor), if your durability/correctness bar is uncompromising on a pre-22.x build, or if you expect it to *process* data — it is a log, not a stream-processing engine or a query engine, so you still need [apache-flink](apache-flink.md)/clients downstream. Biggest gotcha: the thread-per-core + fsync-on-majority design assumes fast local disks; on slow or network-attached storage you lose the latency advantage that is its main reason to exist, and the Tiered Storage / Iceberg features that justify the spend are paid enterprise add-ons.

## Sources
- [Redpanda GitHub (architecture / "no JVM, no ZooKeeper")](https://github.com/redpanda-data/redpanda)
- [Redpanda docs — Transactions & delivery semantics](https://docs.redpanda.com/current/develop/transactions/)
- [Redpanda docs — Configure Producers (idempotence, acks, fsync)](https://docs.redpanda.com/current/develop/produce-data/configure-producers/)
- [Jepsen: Redpanda 21.10.1 (2022)](https://jepsen.io/analyses/redpanda-21.10.1)
- [Redpanda licensing overview (BSL + RCL)](https://docs.redpanda.com/current/get-started/licensing/overview/)
- [Redpanda blog — "free and Source Available" (BSL announcement)](https://www.redpanda.com/blog/bsl-source-available-license)
- [Redpanda docs — Tiered Storage](https://docs.redpanda.com/current/manage/tiered-storage/)
- [Redpanda docs — Iceberg Topics](https://docs.redpanda.com/current/manage/iceberg/about-iceberg-topics/)
