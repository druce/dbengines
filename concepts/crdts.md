---
name: CRDTs (Conflict-free Replicated Data Types)
slug: crdts
summary: Data types whose concurrent updates always merge deterministically without coordination — the math behind multi-leader/AP systems converging without conflicts or a central arbiter.
last_researched: 2026-06-04
---

# CRDTs — Conflict-free Replicated Data Types

> A **CRDT** is a data structure whose replicas can be updated independently and concurrently, and
> always **merge to the same state** without coordination or conflict resolution by the application.
> They make [AP](cap-pacelc.md) / multi-leader replication safe-by-construction for the data types they
> cover.

## The core idea
If the merge operation is **commutative, associative, and idempotent** (a join over a semilattice),
then no matter the order or duplication of updates across replicas, all replicas converge —
**Strong Eventual Consistency**: replicas that have seen the same set of updates are in the same
state. No consensus (see [consensus-raft-paxos](consensus-raft-paxos.md)) is needed on the write path.

## Two styles
- **State-based (CvRDT)** — replicas exchange full state; merge via the join function.
- **Operation-based (CmRDT)** — replicas broadcast operations; needs reliable delivery but smaller
  messages.

## Common types
- **Counters** — G-Counter (grow-only), PN-Counter (inc/dec).
- **Sets** — G-Set, 2P-Set, OR-Set (observed-remove, handles concurrent add/remove).
- **Registers** — LWW-Register (last-write-wins by timestamp — beware [clock skew](clocks-and-time.md)),
  multi-value register.
- **Sequences/text** — RGA, Yjs/Automerge for collaborative editing.

## The catch
CRDTs only solve conflicts for **operations that commute**. They cannot enforce global invariants
that need agreement (e.g. "balance must never go negative", uniqueness constraints) — those still
require coordination. LWW resolution silently **drops** concurrent writes; choose the merge semantics
deliberately.

## Where they show up
[riak-kv](../engines/riak-kv.md) (Riak Data Types), [redis](../engines/redis.md) Enterprise (Active-Active / conflict-free replicated DBs),
[microsoft-azure-cosmos-db](../engines/microsoft-azure-cosmos-db.md) multi-region writes, collaborative apps (Yjs/Automerge),
and many local-first / offline-sync systems. Contrast with last-write-wins and app-side conflict
resolution in [replication-models](replication-models.md).

## How to use it on engine pages
If a multi-leader/AP engine claims automatic conflict resolution, say **how**: CRDTs, LWW (and the
data-loss risk), or app-defined merges — and which invariants it therefore *cannot* guarantee.
