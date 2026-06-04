---
name: Clocks & Time
slug: clocks-and-time
summary: When distributed correctness depends on synchronized clocks — TrueTime, HLCs, and the failure modes when clock assumptions are violated.
last_researched: 2026-06-04
---

# Clocks & Time

> In a distributed database, **time is how you order events across machines**. Some systems lean on
> physical clocks for correctness (ordering, leases, consistency); when those clocks drift or skew
> beyond assumptions, those guarantees can silently break. Always ask: *does correctness rest on
> clock synchronization, and what happens when it's wrong?*

## Why clocks are hard
Wall clocks on different machines disagree (skew) and jump (NTP corrections, leap seconds, VM
pauses). You cannot assume monotonic, synchronized time. The classic alternative is **logical time**
— Lamport clocks and vector clocks order events by causality without physical clocks, but don't give
you real-time bounds.

## The main approaches
- **Logical / Lamport & vector clocks** — capture happens-before/causality only. Used for causal
  consistency and conflict detection (e.g. [apache-cassandra](../engines/apache-cassandra.md) uses timestamps for last-write-wins;
  [riak-kv](../engines/riak-kv.md) uses vector clocks).
- **Hybrid Logical Clocks (HLC)** — combine a physical-time component with a logical counter, giving
  causally-consistent timestamps close to wall time without needing tight sync. Used by
  [cockroachdb](../engines/cockroachdb.md), [yugabytedb](../engines/yugabytedb.md), [mongodb](../engines/mongodb.md) (cluster time for causal consistency).
- **TrueTime (bounded uncertainty)** — [google-cloud-spanner](../engines/google-cloud-spanner.md) uses GPS/atomic clocks to expose an
  *interval* `[earliest, latest]` and **waits out the uncertainty** ("commit wait") to provide
  **external consistency** (linearizability) on globally distributed transactions
  ([Spanner OSDI 2012](https://research.google/pubs/pub39966/)).

## The failure modes to flag
- **LWW timestamp data loss** — in clock-ordered last-write-wins systems ([apache-cassandra](../engines/apache-cassandra.md)),
  a node with a fast clock can make an *older* write win, silently dropping a newer one. Skew = lost
  data, not just staleness.
- **Stale leader leases** — leases timed by local clocks can let a deposed leader believe it's still
  valid during a pause, risking split-brain (see [consensus-raft-paxos](consensus-raft-paxos.md), [replication-models](replication-models.md)).
- **Bounded-skew assumptions** — [cockroachdb](../engines/cockroachdb.md)'s `max-offset` assumes clocks stay within a bound;
  exceed it and a node may be unable to guarantee consistency (it shuts down to stay safe).

## How to use it on engine pages
Note explicitly whether correctness depends on synchronized clocks, which model it uses (logical /
HLC / TrueTime), the assumed skew bound, and what happens when that bound is violated (stale reads,
lost writes, or self-fencing). Relates to [cap-pacelc](cap-pacelc.md) and [isolation-levels](isolation-levels.md) (external
consistency is stronger than serializability).
