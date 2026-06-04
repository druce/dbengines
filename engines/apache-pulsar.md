---
name: Apache Pulsar
slug: apache-pulsar
adjacent: true
rank: n/a
category: streaming-platform
data_model: Distributed pub/sub + segmented log (compute/storage separated, tiered storage)
license: Apache License 2.0 (permissive)
summary: Multi-tenant pub/sub messaging + streaming with brokers decoupled from BookKeeper storage, giving elastic scaling and built-in tiered storage — at the cost of more moving parts than Kafka.
last_researched: 2026-06-04
confidence: high
---

# Apache Pulsar

> A distributed pub/sub and streaming platform whose defining bet is **separating stateless serving (brokers) from segmented log storage (Apache BookKeeper)** — enabling independent scaling, instant broker failover, and native tiered storage to object stores, but requiring you to operate multiple tiers.

## Identity / role
- Apache Pulsar is a **messaging/event-streaming transport and durable log**, not a database and not a query engine. It is the pipe between producers and consumers, with persistence — closest peer is [apache-kafka](apache-kafka.md) (and adjacent to [streaming-platforms](../concepts/streaming-platforms.md)).
- It unifies two patterns usually served by separate systems: **queueing** (RabbitMQ-style competing consumers via Shared subscriptions) and **streaming/log** (Kafka-style replayable partitions). One topic can be consumed both ways depending on subscription type.
- It is multi-tenant from the ground up: `tenant/namespace/topic` hierarchy with per-tenant auth, quotas, TTL, and isolation policies — a real differentiator vs Kafka's flatter model.
- It does **not** do SQL analytics, joins, or materialized views itself. Stream processing is bolted on via lightweight Pulsar Functions or external engines like [apache-flink](apache-flink.md). For real-time analytics on the data, you sink to [clickhouse](clickhouse.md)/[apache-druid](apache-druid.md)/[starrocks](starrocks.md) or a [lakehouse](../concepts/lakehouse.md).

## How it fits
- **Two-layer architecture**, an instance of [storage-compute-separation](../concepts/storage-compute-separation.md):
  - **Brokers** — stateless serving layer handling connections, auth, topic lookup, and dispatch. No topic data lives on a broker, so a broker can be killed/replaced and topics reassigned almost instantly with no data movement.
  - **Apache BookKeeper (bookies)** — the stateful storage layer. BookKeeper is a distributed write-ahead log; see [wal-and-durability](../concepts/wal-and-durability.md). A topic partition is **not** one file on one node (Kafka's model) — it is a sequence of **ledgers (segments)** striped across bookies. New ledgers can land on fresh bookies, so adding storage capacity needs no partition rebalancing/reshuffle.
  - **Metadata/coordination** — historically Apache ZooKeeper for cluster metadata and BookKeeper coordination. Pulsar is moving to a pluggable metadata store and the **Oxia** project to reduce/replace ZooKeeper dependence (see [consensus-raft-paxos](../concepts/consensus-raft-paxos.md)).
- **Tiered storage:** older log segments are offloaded from BookKeeper to cheap object storage (S3, GCS, Azure Blob via Apache jclouds), transparently to consumers — lets a topic keep effectively unbounded history without paying hot-storage prices. This is a built-in feature, not a separate connector.
- **Geo-replication** is native: asynchronous cross-region/cross-cluster topic replication configured at the namespace level; on failover a consumer can resume from its position in another cluster.
- Pairs with: [apache-flink](apache-flink.md) (stream processing), Kafka-compatible apps via the **KoP (Kafka-on-Pulsar)** protocol handler, Pulsar IO connectors for sources/sinks, and [change-data-capture](../concepts/change-data-capture.md) feeds via Debezium-based connectors.

## Guarantees & consistency
- **Durability:** writes are persisted to BookKeeper and acknowledged only after they reach a configurable quorum of bookies (write quorum / ack quorum); BookKeeper fsyncs to its journal before ack. The crash data-loss window depends on `ackQuorum` and journal/fsync settings — at safe defaults, an acked write survives bookie loss up to the redundancy you configured. ([BookKeeper / Pulsar architecture docs](https://pulsar.apache.org/docs/3.3.x/concepts-architecture-overview/))
- **Delivery semantics:** default is **at-least-once**; **at-most-once** is available (no redelivery). **Exactly-once** producer dedup (idempotent producer) exists per-topic, and as of Pulsar 2.8 a **Transaction API** provides atomic produce + acknowledge across multiple topics/partitions — Pulsar markets this as "effectively-once." In practice end-to-end exactly-once still requires either Pulsar transactions or idempotent sinks downstream; the message bus alone does not make a non-idempotent consumer exactly-once. ([Pulsar transactions docs](https://pulsar.apache.org/docs/3.1.x/txn-what/), [StreamNative on effectively-once](https://streamnative.io/blog/exactly-once-semantics-transactions-pulsar))
- **Ordering** depends on the subscription type:
  - **Exclusive** / **Failover** — single active consumer per (partition) subscription → ordered.
  - **Shared** — round-robin across many consumers → **no ordering guarantee** (the queue/work-distribution mode).
  - **Key_Shared** — multiple consumers but all messages of a given key go to one consumer → per-key ordering with parallelism.
  - ([Pulsar messaging concepts](https://pulsar.apache.org/docs/next/concepts-messaging/))
- **Event-time vs processing-time:** Pulsar carries publish time and an optional event time on each message; windowing/event-time semantics are the job of the processor (Pulsar Functions or [apache-flink](apache-flink.md)), not the broker.
- **CAP/[isolation-levels](../concepts/isolation-levels.md):** N/A as a strict DB transaction model. Within a cluster, BookKeeper favors consistency/durability (quorum-acked writes); cross-region geo-replication is **asynchronous**, so it is eventually consistent across regions and can lose un-replicated tail data on a regional loss.

## Interfaces & integration
- **Clients:** official Java, Go, Python, C++, C#, Node.js; binary Pulsar protocol. Also WebSocket and a REST admin API.
- **Protocol handlers:** KoP (Kafka API), MoP (MQTT), AoP (AMQP 0.9.1) — lets existing Kafka/MQTT/RabbitMQ clients talk to Pulsar with reduced rewrite.
- **Stream processing:** **Pulsar Functions** (lightweight Java/Python/Go functions deployed on the cluster) for simple transforms/routing; **Pulsar IO** connectors for source/sink integration; heavyweight processing via [apache-flink](apache-flink.md).
- **Schema:** built-in schema registry (Avro, JSON, Protobuf, primitives) with schema enforcement and evolution per topic — registry is integral, not a separate service as in classic Kafka.
- **Downstream:** sink connectors to data warehouses, [clickhouse](clickhouse.md), Elasticsearch, object stores; commonly feeds [real-time-olap](../concepts/real-time-olap.md) stores and lakehouse tables.

## Operations & maturity
- **Maturity:** Apache top-level project (graduated 2018; originated at Yahoo). Production-proven at large scale (Yahoo, Tencent, Verizon Media, Splunk/StreamNative customers). Healthy ASF community plus commercial vendor **StreamNative** (founded by Pulsar creators) offering managed cloud.
- **Ops burden — the central trade-off:** you run **three tiers** — brokers, BookKeeper bookies, and a metadata store (ZooKeeper/Oxia) — vs Kafka's increasingly single-tier KRaft model. More components to deploy, monitor, tune, and reason about (BookKeeper journal/ledger disk layout, bookie ensemble placement, broker load balancing). This complexity is the most-cited reason teams pick Kafka instead, and is partly why some orgs (notably Twitter) abandoned BookKeeper-based stacks. ([Kafka vs Pulsar overviews](https://www.instaclustr.com/blog/kafka-versus-pulsar/))
- **Failure modes:** broker failover is fast (stateless) and a strength; the operational risk concentrates in BookKeeper (bookie disk/journal saturation, ledger placement under node loss) and in ZooKeeper as a metadata bottleneck at high topic counts — the motivation for Oxia. Tiered-storage offload adds dependence on object-store availability/latency for backlog reads.
- **Scaling:** scale brokers and bookies independently; add storage with no partition reshuffle. Strong fit for **very high topic/partition counts** and multi-tenant fleets.
- **Observability:** Prometheus metrics, per-topic stats via admin API, Pulsar Manager UI.

## Licensing & cost
- **License:** Apache License 2.0 — permissive, no source-available rug-pull; see [license-taxonomy](../concepts/license-taxonomy.md). The core is genuinely open and ASF-governed, not vendor-controlled.
- **Self-host vs managed:** fully self-hostable (k8s via the official Helm chart / operators). Managed offerings: **StreamNative Cloud**, plus DataStax Astra Streaming (note: DataStax has wound down/changed some Pulsar offerings over time) and others.
- **Cost model:** self-managed = infrastructure + non-trivial operational headcount (three tiers). Tiered storage materially lowers retention cost by pushing cold data to object storage. Managed services bill on throughput/storage/usage.

## Bottom line
- Reach for Pulsar when you need **multi-tenancy at scale, very large topic counts, native geo-replication, unified queue + stream semantics on one platform, and cheap unbounded retention via tiered storage** — and you have the operational maturity to run brokers + BookKeeper + a metadata store. It is technically excellent and arguably more elegant than Kafka's architecture for elasticity.
- Do **not** reach for it if you want the lowest-operational-overhead message bus, have a small team, or live in the Kafka ecosystem (tooling, hiring, and connector breadth still favor [apache-kafka](apache-kafka.md)). **Biggest gotcha:** the operational complexity of the multi-tier (BookKeeper + ZooKeeper) stack — and the trap of assuming the Shared subscription preserves ordering (it does not; use Key_Shared or Failover when order matters).

## Sources
- [Apache Pulsar — Architecture Overview](https://pulsar.apache.org/docs/3.3.x/concepts-architecture-overview/)
- [Apache Pulsar — Messaging concepts (subscriptions, delivery)](https://pulsar.apache.org/docs/next/concepts-messaging/)
- [Apache Pulsar — Tiered Storage](https://pulsar.apache.org/docs/next/concepts-tiered-storage/)
- [Apache Pulsar — Multi-tenancy](https://pulsar.apache.org/docs/next/concepts-multi-tenancy/)
- [Apache Pulsar — Geo-replication](https://pulsar.apache.org/docs/next/administration-geo/)
- [Apache Pulsar — Transactions](https://pulsar.apache.org/docs/3.1.x/txn-what/)
- [StreamNative — Exactly-once / transactions in Pulsar](https://streamnative.io/blog/exactly-once-semantics-transactions-pulsar)
- [StreamNative — Moving toward a ZooKeeper-less Pulsar (Oxia)](https://streamnative.io/blog/moving-toward-zookeeper-less-apache-pulsar)
- [Instaclustr — Kafka vs Pulsar comparison](https://www.instaclustr.com/blog/kafka-versus-pulsar/)
- [Confluent — Kafka vs Pulsar](https://www.confluent.io/kafka-vs-pulsar/)
