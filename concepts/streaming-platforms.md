---
name: Streaming Platforms
slug: streaming-platforms
summary: The durable, replayable event log that sits between producers and consumers — Kafka, Pulsar, Redpanda, Kinesis. A system of record for events, not a queryable database.
last_researched: 2026-06-04
---

# Streaming Platforms

> A **streaming platform** is a distributed, append-only, **durable and replayable log** of events
> (records) organized into topics/partitions. Producers append; many consumers read independently at
> their own offset. It decouples services, buffers spikes, and is the backbone of event-driven and
> real-time architectures — but it is a **transport + log**, not a database you query by key.

## Core model
- **Topic → partitions** — ordering is guaranteed **within a partition**, not across; the partition
  key sets ordering and parallelism (see [sharding-partitioning](sharding-partitioning.md)).
- **Offsets + retention** — consumers track an offset; data is retained by time/size (or compacted
  to keep the latest per key), so streams are **replayable** — reprocess history by rewinding.
- **Durability via replication** — partitions are replicated across brokers; a write is acked when
  enough replicas have it (see [replication-models](replication-models.md), [wal-and-durability](wal-and-durability.md)). Producers choose
  acks=all for no-loss vs lower latency.
- **Delivery semantics** — at-least-once by default; **exactly-once** within the platform via
  idempotent producers + transactions (consumed by stream processors — see [streaming-databases](streaming-databases.md)).

## The platforms
- **[apache-kafka](../engines/apache-kafka.md)** — the de facto standard; huge ecosystem (Kafka Connect, Streams, Schema
  Registry). Historically JVM + (now removed) ZooKeeper → KRaft consensus ([consensus-raft-paxos](consensus-raft-paxos.md)).
- **[apache-pulsar](../engines/apache-pulsar.md)** — broker/storage separation (Apache BookKeeper), native multi-tenancy,
  geo-replication, and tiered storage; unifies queuing and streaming.
- **[redpanda](../engines/redpanda.md)** — Kafka-API-compatible, C++ (no JVM, no ZooKeeper), thread-per-core for low tail
  latency; drop-in for Kafka clients.
- **Amazon Kinesis** — AWS managed streaming; simple, AWS-integrated, lower ceiling than Kafka.

## Where it sits vs a database
The log is the **source of truth for events**; to *query* state you feed it into a
[stream processor / streaming database](streaming-databases.md) (materialized views), a
[real-time OLAP store](real-time-olap.md) (Pinot/Druid/ClickHouse), a [lakehouse](lakehouse.md) (via
[CDC](change-data-capture.md)/sinks), or a serving DB. Kafka topics can also act as the transport for
**CDC** out of operational databases ([debezium](../engines/debezium.md)).

## How to use it on adjacent pages
Note ordering scope (per-partition), delivery/durability semantics and the no-loss config, retention
vs compaction, consensus/metadata mechanism, and the ecosystem. Stress the anti-pattern: it is not a
key-value store or an ad-hoc query engine.
