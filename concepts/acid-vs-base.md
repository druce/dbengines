---
name: ACID vs BASE
slug: acid-vs-base
summary: The two consistency philosophies — ACID (correctness-first: transactions are all-or-nothing and isolated) vs BASE (availability-first: stay up and converge later). It's a spectrum, not a binary, and most real systems sit in between.
last_researched: 2026-06-04
---

# ACID vs BASE

> Two opposing design philosophies for how a database treats consistency. **ACID** prioritizes
> correctness — a transaction either fully happens or not at all, and concurrent transactions don't
> corrupt each other. **BASE** prioritizes availability and scale — accept temporary inconsistency
> and let replicas converge. The deliberately cute acronyms (acid vs base, chemistry pun) frame a
> real trade-off, but treat it as a **spectrum**, not a binary.

## ACID
The transactional guarantee, classically of relational systems ([postgresql](../engines/postgresql.md), [oracle](../engines/oracle.md),
[microsoft-sql-server](../engines/microsoft-sql-server.md), [mysql](../engines/mysql.md)):
- **Atomicity** — all-or-nothing; partial transactions roll back ([WAL/undo](wal-and-durability.md)).
- **Consistency** — a transaction moves the DB from one valid state to another (constraints hold).
- **Isolation** — concurrent transactions don't see each other's partial work; *how much* is the
  isolation level, and "ACID" often quietly means snapshot isolation, not serializable — see
  [isolation-levels](isolation-levels.md).
- **Durability** — once committed, it survives a crash; the strength depends on fsync/replication and
  leaves a possible data-loss window — see [wal-and-durability](wal-and-durability.md).

## BASE
The NoSQL/Dynamo-lineage philosophy ([apache-cassandra](../engines/apache-cassandra.md), [riak-kv](../engines/riak-kv.md), [amazon-dynamodb](../engines/amazon-dynamodb.md),
[couchdb](../engines/couchdb.md)):
- **Basically Available** — the system answers (possibly stale) even during failures/partitions.
- **Soft state** — state may change over time without new input as replicas reconcile.
- **Eventual consistency** — given no new writes, replicas *eventually* converge to the same value.

BASE is the practical face of choosing **AP** under [CAP](cap-pacelc.md): to stay available under a
partition you give up immediate consistency. Convergence mechanisms include read-repair,
last-write-wins (which silently drops writes — beware [clock skew](clocks-and-time.md)), and
[CRDTs](crdts.md) (conflict-free merges).

## It's a spectrum, and the labels lie
- **Tunable systems** straddle both: [amazon-dynamodb](../engines/amazon-dynamodb.md), [apache-cassandra](../engines/apache-cassandra.md), and [mongodb](../engines/mongodb.md) let
  you pick per-operation consistency (strong/quorum vs eventual) — see [cap-pacelc](cap-pacelc.md).
- **NewSQL** ([google-cloud-spanner](../engines/google-cloud-spanner.md), [cockroachdb](../engines/cockroachdb.md), [yugabytedb](../engines/yugabytedb.md)) deliberately delivers
  ACID *and* horizontal scale, refuting "you must pick BASE to scale" — at a latency cost
  ([consensus-raft-paxos](consensus-raft-paxos.md), [clocks-and-time](clocks-and-time.md)).
- **"ACID" is frequently overstated** — verify against [jepsen](jepsen.md); many systems only deliver their
  claimed guarantees with non-default settings (e.g. [mongodb](../engines/mongodb.md) majority concerns).

## How to use it on engine pages
Don't label an engine simply "ACID" or "BASE." State the concrete guarantee: default + achievable
[isolation](isolation-levels.md), the [CAP/PACELC](cap-pacelc.md) behavior, whether consistency is
tunable per query, and the durability/data-loss window. This concept is the framing behind the
consistency question in [decision-guide](../decision-guide.md).
