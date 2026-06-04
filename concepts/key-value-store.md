---
name: Key-Value Store
slug: key-value-store
summary: The simplest model — a distributed hash map of opaque keys to values — giving O(1) lookups and easy horizontal scale, at the cost of querying only by key.
last_researched: 2026-06-04
---

# Key-Value Store

> A key-value store is a persistent (or in-memory) **map from a unique key to a value**, where the
> value is usually opaque to the database. Access is by key: `get`, `put`, `delete`. Giving up rich
> query is exactly what buys predictable O(1) lookups and trivial [sharding](sharding-partitioning.md).

## Why it scales so well
With no joins, no secondary-query planning, and an opaque value, the system only has to route a key
to a partition and read/write it. That makes key-value stores the easiest model to distribute and
the lowest-latency to operate — the workhorse for caching, sessions, feature flags, queues, and
counters.

## Variants
- **In-memory cache / data structures** — [redis](../engines/redis.md), [valkey](../engines/valkey.md), [memcached](../engines/memcached.md), [hazelcast](../engines/hazelcast.md),
  [apache-ignite](../engines/apache-ignite.md), [ehcache](../engines/ehcache.md), [gemfire](../engines/gemfire.md), [oracle-coherence](../engines/oracle-coherence.md), [infinispan](../engines/infinispan.md): microsecond
  latency, durability optional (see [wal-and-durability](wal-and-durability.md)); often a cache in front of a system of
  record, not the record itself.
- **Persistent / Dynamo-style** — [amazon-dynamodb](../engines/amazon-dynamodb.md), [riak-kv](../engines/riak-kv.md), [aerospike](../engines/aerospike.md),
  [oracle-nosql](../engines/oracle-nosql.md), [amazon-simpledb](../engines/amazon-simpledb.md): durable, horizontally scaled, [AP](cap-pacelc.md)-leaning with
  tunable consistency and sometimes [conflict-free](crdts.md) merges.
- **Embedded storage engines** — [rocksdb](../engines/rocksdb.md), [leveldb](../engines/leveldb.md), [lmdb](../engines/lmdb.md), [oracle-berkeley-db](../engines/oracle-berkeley-db.md),
  [etcd](../engines/etcd.md): libraries ([embedded-databases](embedded-databases.md)) that store ordered KV pairs; the on-disk layer inside
  many larger databases ([LSM or B-tree](lsm-vs-btree.md)). [etcd](../engines/etcd.md) adds [Raft](consensus-raft-paxos.md)
  for strongly-consistent config/coordination.

## Strengths and anti-patterns
- **Strengths:** caching, session/state stores, high-throughput simple lookups, coordination,
  building blocks for other systems.
- **Anti-patterns:** querying by value, ranges, or relationships; reporting/analytics; anything
  needing multi-key transactions or joins (model it elsewhere). "Schema lives in the app."

## How to use it on engine pages
Note in-memory vs persistent, durability/replication model, whether it's a cache or a system of
record, consistency tuning, and any data structures beyond plain values (Redis types, secondary
indexes). Many of these are also [multi-model](multi-model.md) now (Redis JSON/search/vector).
