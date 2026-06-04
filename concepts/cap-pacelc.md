---
name: CAP & PACELC
slug: cap-pacelc
summary: Why a partitioned distributed DB must trade consistency for availability — and why PACELC adds the latency-vs-consistency tradeoff that matters even when the network is healthy.
last_researched: 2026-06-04
---

# CAP & PACELC

> CAP says: under a network **partition**, a distributed store can keep serving (**A**vailable) or
> stay **C**onsistent, not both. PACELC adds the part CAP ignores: **E**lse (no partition), you
> still trade **L**atency vs **C**onsistency.

## CAP, precisely
Consistency here means **linearizability** (every read sees the latest committed write), not the
"C" of ACID. The theorem ([Gilbert & Lynch's proof](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf)
of [Brewer's conjecture](https://en.wikipedia.org/wiki/CAP_theorem)) only bites **during a
partition**. When the network is healthy you can have both — so CAP is a statement about failure
behavior, not steady state.

- **CP** — on partition, refuse the side that can't guarantee consistency (reject writes / reads).
  Most leader-based SQL systems and consensus stores: [postgresql](../engines/postgresql.md) failover, [google-cloud-spanner](../engines/google-cloud-spanner.md),
  [etcd](../engines/etcd.md), [cockroachdb](../engines/cockroachdb.md).
- **AP** — stay up on both sides, reconcile later (last-write-wins, CRDTs, read-repair). Dynamo-style:
  [apache-cassandra](../engines/apache-cassandra.md), [riak-kv](../engines/riak-kv.md), [amazon-dynamodb](../engines/amazon-dynamodb.md) (tunable).

"CA" is not a real operating point for a distributed system — you cannot opt out of partitions.

## PACELC — the more useful lens
[Abadi's PACELC](https://en.wikipedia.org/wiki/PACELC_design_principle): **if Partition then (A or C),
Else (L or C)**. The *else* clause captures the everyday tradeoff: synchronous replication to a
quorum buys consistency at the cost of latency (PC/EC); async replication or reading a local replica
buys latency at the cost of staleness (PA/EL).

- **PC/EC** — consistency first, always: [google-cloud-spanner](../engines/google-cloud-spanner.md), [cockroachdb](../engines/cockroachdb.md).
- **PA/EL** — availability/latency first: [apache-cassandra](../engines/apache-cassandra.md), [amazon-dynamodb](../engines/amazon-dynamodb.md) (defaults).
- Many systems are **tunable per-query** (Dynamo/Cassandra consistency levels, [mongodb](../engines/mongodb.md) read/write
  concerns), so a single label undersells them — state the *default* and what's achievable.

## How to use it on engine pages
CAP is coarse — one bit. Prefer to state: behavior under partition (does it reject writes or keep
serving?), replication sync/async (see [replication-models](replication-models.md)), the steady-state latency cost, and
whether consistency is tunable per query. A "highly available and strongly consistent" marketing
line almost always means *strongly consistent until a partition, then unavailable* — say which.

Linearizability also interacts with isolation (see [isolation-levels](isolation-levels.md)): a system can be
serializable but not linearizable (stale snapshots), or linearizable per-key but not serializable
across keys.

**Mental model:** the partition-time **A-vs-C** choice is the distributed-systems face of the
broader [acid-vs-base](acid-vs-base.md) dichotomy — CP/EC leans ACID (correctness-first), AP/EL leans BASE
(availability-first). Most real systems are tunable points on that spectrum, not one extreme.
