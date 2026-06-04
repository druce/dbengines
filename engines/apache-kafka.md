---
name: Apache Kafka
slug: apache-kafka
adjacent: true
rank: n/a
category: streaming-platform
data_model: Distributed, partitioned, replicated commit log (event log)
license: Apache License 2.0 (permissive)
summary: The de-facto distributed event log — a durable, ordered, replayable transport that sits between producers and consumers, not a database you query.
last_researched: 2026-06-04
confidence: high
---

# Apache Kafka

> A horizontally scalable, durable, replayable commit log for event streams — the default backbone for moving events between systems, with per-partition ordering and (opt-in) exactly-once semantics, but **not** a query engine or a system of record you ask questions of.

## Identity / role
- **What it is:** a distributed, partitioned, replicated **append-only log**. Topics are split into partitions; each partition is an ordered, immutable sequence of records addressed by monotonic offset. Producers append; consumers read by offset and can rewind/replay. Retention is by time or size (or compacted by key), independent of whether anyone has consumed — this replayability is the core differentiator from traditional message queues. See [streaming-platforms](../concepts/streaming-platforms.md).
- **What it is NOT:** not a database — there is no ad-hoc query, no secondary indexes, no joins over stored data. You cannot "look up record X"; you read partitions sequentially from an offset. It is a **transport and buffer**, not a system of record, and not [OLTP/OLAP](../concepts/oltp-olap-htap.md) storage. Stream processing (joins, aggregations, windowing) requires a separate layer: Kafka Streams, [apache-flink](apache-flink.md), ksqlDB, or a [streaming database](../concepts/streaming-databases.md).
- **Where it sits:** the durable spine of an event-driven architecture and the standard substrate for [CDC](../concepts/change-data-capture.md) (via Debezium), log/metrics pipelines, and feeding [real-time-olap](../concepts/real-time-olap.md) stores ([clickhouse](clickhouse.md), [apache-druid](apache-druid.md), [starrocks](starrocks.md)) and lakehouses.

## How it fits
- **Architecture:** a cluster of **brokers** stores partition replicas on local disk (now optionally [tiered to object storage, GA in 3.9](https://kafka.apache.org/39/operations/tiered-storage/)). Each partition has one leader and N-1 followers; producers/consumers talk only to the leader. Cluster metadata and controller election are handled by **KRaft** (a built-in [Raft](../concepts/consensus-raft-paxos.md) quorum of controller nodes) — [ZooKeeper was fully removed in Kafka 4.0 (March 2025)](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/); ZK clusters must migrate to KRaft on a 3.x release before upgrading.
- **Consumer model:** consumer groups partition the workload — each partition is consumed by exactly one member of a group, so **parallelism is bounded by partition count**. Offsets are committed back to an internal `__consumer_offsets` topic. KIP-848 (GA in 4.0) is a new rebalance protocol that cuts stop-the-world rebalances; KIP-932 adds "share groups" (queue-like cooperative consumption) as Early Access.
- **Pairs with:** Kafka Connect (source/sink connectors), Schema Registry (Avro/Protobuf/JSON-Schema governance), Debezium for [change-data-capture](../concepts/change-data-capture.md), and downstream sinks into [snowflake](snowflake.md), [databricks](databricks.md), [Spark](apache-spark-sql.md), object storage, and [real-time-olap](../concepts/real-time-olap.md) engines.

## Guarantees & consistency
- **Durability:** records are durable once written to the leader and replicated to the in-sync replica (ISR) set. `acks=all` + `min.insync.replicas>=2` is the safe config; with `acks=1` (or `unclean.leader.election=true`) you have a real **data-loss window** if the leader dies before replication. fsync is asynchronous by default — Kafka relies on replication across brokers for durability rather than per-message fsync, so a correlated power loss across the ISR can lose un-fsynced data. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Ordering:** guaranteed **only within a partition**, not across a topic. Keyed records hash to the same partition, giving per-key ordering.
- **Delivery semantics:** at-least-once by default; at-most-once if you disable retries; **exactly-once (EOS)** is available via [idempotent producers + transactions (KIP-98)](https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging). Since 3.0 `enable.idempotence=true` and `acks=all` are the producer defaults, giving dedup + ordering per partition. Transactions allow atomic writes across multiple partitions plus an atomic offset commit, enabling exactly-once **consume-transform-produce** within the Kafka boundary. ⚠️ caveat: EOS is end-to-end only within Kafka (and Kafka Streams); a consumer writing to an external system without idempotent sink logic still gets effective at-least-once.
- **CAP:** the metadata/control plane (KRaft) is **CP** — a [Raft](../concepts/consensus-raft-paxos.md) quorum. The data plane is tunably consistent: `acks=all` + ISR is effectively CP for a partition (writes refuse when ISR shrinks below `min.insync.replicas`), while `acks=1`/unclean election trades toward availability and possible loss. See [cap-pacelc](../concepts/cap-pacelc.md). [isolation-levels](../concepts/isolation-levels.md) are N/A — it is a log, not a transactional store, though consumers can set `isolation.level=read_committed` to skip aborted-transaction records. No third-party Jepsen report; the EOS design has been the subject of formal modeling internally rather than an independent Jepsen analysis. ⚠️ unverified — no public independent Jepsen report exists for Kafka.

## Interfaces & integration
- **APIs:** native binary protocol with first-party Java client; rich clients for Go, Python (confluent-kafka / librdkafka), .NET, C/C++, Rust, etc. Core APIs: Producer, Consumer, Admin, plus Kafka Connect and the Kafka Streams library.
- **Query language:** none natively. SQL-over-Kafka comes from external layers — ksqlDB, [Flink SQL](apache-flink.md), Spark Structured Streaming, or [streaming-databases](../concepts/streaming-databases.md) (Materialize, RisingWave) that consume Kafka topics.
- **Ecosystem interop:** hundreds of Connect connectors; the Kafka wire protocol is a de-facto standard re-implemented by Redpanda, WarpStream, AutoMQ, and Azure Event Hubs (Kafka API). Schema Registry enforces serialization contracts. Topics are routinely landed into [open table formats](../concepts/open-table-formats.md) (Iceberg/Delta) for the lakehouse.

## Operations & maturity
- **Maturity:** extremely high — created at LinkedIn (~2011), top-level ASF project, runs at massive scale across most of the Fortune 500. Battle-tested failure modes are well understood.
- **Ops burden:** historically heavy. Partition count planning, rebalancing, ISR/under-replicated-partition monitoring, retention/disk management, and consumer lag are day-2 concerns. KRaft removed the separate ZooKeeper ensemble (big simplification); tiered storage decouples retention from local disk. Cruise Control is commonly used for rebalancing.
- **Known failure modes:** disk-full brokers; uneven partition/leader skew creating hot brokers; "stuck"/rebalance-storm consumer groups (mitigated by KIP-848); silent data loss from `acks=1` + unclean leader election; over-partitioning hurting end-to-end latency and controller load.
- **Governance:** vendor-neutral Apache Software Foundation project. Confluent (founded by the original creators) is the dominant commercial vendor and contributor but does not control the core license.

## Licensing & cost
- **Core:** [Apache License 2.0](https://github.com/apache/kafka) — permissive, true open source. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Caveat:** much of the popular surrounding ecosystem is **not** Apache 2.0. Confluent's Schema Registry, ksqlDB, and many connectors are under the source-available **Confluent Community License** (restricts offering them as a competing managed service). Treat "Kafka is open source" as true for the broker/core, attribute the rest.
- **Self-host vs managed:** runs anywhere (bare metal, k8s via Strimzi, containers). Managed options: Confluent Cloud, AWS MSK, Aiven, plus Kafka-compatible alternatives (Redpanda, WarpStream, AutoMQ) that target lower cost/ops. Cost model self-hosted is dominated by broker count + storage + cross-AZ replication network egress; managed is typically priced per throughput (ingress/egress) + storage + partition/connector count. Cross-AZ replication traffic is a frequently underestimated cloud cost.

## Bottom line
- Reach for Kafka when you need a durable, ordered, **replayable** event backbone that decouples many producers from many consumers at high throughput, or as the transport for CDC and streaming pipelines — it is the safe industry-standard choice with the deepest ecosystem. Do **not** reach for it as a database, a request/reply RPC mechanism, or a low-volume task queue: there are no ad-hoc queries, throughput parallelism is capped by partition count, and the operational and cost overhead is disproportionate for small workloads. **Biggest gotcha:** the defaults are not the durable defaults people assume across the whole path — `acks=1` plus unclean leader election (or treating it as exactly-once when your external sink is not idempotent) silently reintroduces loss or duplicates; EOS is a Kafka-boundary guarantee, not magic end-to-end correctness into external systems.

## Sources
- [Apache Kafka 4.0.0 Release Announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/)
- [Kafka design: message delivery semantics (Confluent docs)](https://docs.confluent.io/kafka/design/delivery-semantics.html)
- [KIP-98: Exactly Once Delivery and Transactional Messaging](https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging)
- [Kafka Tiered Storage (KIP-405) operations docs, GA 3.9](https://kafka.apache.org/39/operations/tiered-storage/)
- [Kafka 4.0 upgrade / KRaft migration docs](https://kafka.apache.org/40/getting-started/upgrade/)
- [Exactly-once with Kafka transactions (Strimzi)](https://strimzi.io/blog/2023/05/03/kafka-transactions/)
- [Apache Kafka source / license (GitHub)](https://github.com/apache/kafka)
