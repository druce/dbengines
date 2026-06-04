---
name: Sharding & Partitioning
slug: sharding-partitioning
summary: Splitting data across nodes (sharding) or within a node (partitioning) to scale beyond one machine — and the resharding, hot-spot, and cross-shard-transaction pain it brings.
last_researched: 2026-06-04
---

# Sharding & Partitioning

> **Partitioning** divides a table into chunks; **sharding** spreads those chunks across nodes so
> the dataset and load exceed one machine. It's how databases scale **horizontally** — and the
> source of most distributed-DB operational pain.

## Partitioning schemes
- **Range** — contiguous key ranges per shard. Great for range scans; risks **hot spots** if writes
  cluster at one end (e.g. monotonic timestamps/IDs all hit the last shard).
- **Hash** — hash the key to spread load evenly. Kills hot spots but destroys range-scan locality.
- **Directory / lookup** — an explicit map of key→shard; flexible, but the map is a dependency.
- **Geo / list** — partition by region or category (data residency, locality).

A good **shard/partition key** is the crux: high cardinality, even access distribution, and aligned
with the most common query so requests hit one shard, not all of them (**scatter-gather**).

## The hard parts
- **Resharding / rebalancing** — adding nodes means moving data. Consistent hashing and
  virtual-node/range-split designs ([apache-cassandra](../engines/apache-cassandra.md), [cockroachdb](../engines/cockroachdb.md) ranges, [tidb](../engines/tidb.md) regions)
  make this online; naive modulo-N hashing forces a near-total reshuffle.
- **Cross-shard transactions & joins** — a transaction spanning shards needs 2PC or distributed
  consensus (latency, coordinator failure modes); cross-shard joins mean network shuffles. Many
  systems restrict transactions to a single shard/partition key.
- **Hot shards** — skewed keys (a celebrity user, a popular tenant) overload one node regardless of
  shard count.

## Auto vs manual
- **Auto-sharding** — the system splits/moves/balances ranges transparently: [google-cloud-spanner](../engines/google-cloud-spanner.md),
  [cockroachdb](../engines/cockroachdb.md), [tidb](../engines/tidb.md), [yugabytedb](../engines/yugabytedb.md), [mongodb](../engines/mongodb.md), [apache-hbase](../engines/apache-hbase.md), [amazon-dynamodb](../engines/amazon-dynamodb.md).
- **Manual / middleware** — you choose keys and add shards: [citus](../engines/citus.md) and [planetscale](../engines/planetscale.md)/Vitess for
  [postgresql](../engines/postgresql.md)/[mysql](../engines/mysql.md), classic application-level sharding. More control, more toil.

## How to use it on engine pages
State whether scaling is vertical-only or horizontal; the partitioning scheme; auto vs manual
(and resharding pain); whether cross-shard transactions/joins are supported and at what cost. Relates
to [replication-models](replication-models.md) (each shard is usually itself replicated) and [consensus-raft-paxos](consensus-raft-paxos.md)
(per-shard consensus groups).
