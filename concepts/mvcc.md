---
name: MVCC (Multi-Version Concurrency Control)
slug: mvcc
summary: Keep multiple row versions so readers never block writers and vice versa — the dominant concurrency model, paid for with version cleanup (vacuum/undo/compaction).
last_researched: 2026-06-04
---

# MVCC — Multi-Version Concurrency Control

> Instead of locking rows for reads, keep **multiple versions** of each row stamped with
> transaction visibility info. Readers see a consistent snapshot; writers create new versions.
> **Readers don't block writers and writers don't block readers** — the core win.

## How it works
Each transaction sees the version of a row visible as of its snapshot (start time or statement
time). A write creates a new version rather than overwriting in place; old versions linger until no
transaction can still see them, then must be reclaimed. This is what makes [snapshot
isolation](isolation-levels.md) cheap and natural.

## The cost: cleanup, and its p99 tail
Old versions accumulate and must be garbage-collected. The mechanism differs by engine and each has
a characteristic operational pain:
- **[postgresql](../engines/postgresql.md)** — versions stored **in-table**; `VACUUM` (and autovacuum) reclaims dead tuples.
  Neglect causes **table/index bloat** and, in the extreme, transaction-ID wraparound. Vacuum I/O
  shows up in p99.
- **[oracle](../engines/oracle.md)** — old versions reconstructed from a separate **undo** segment/tablespace; risk is
  `ORA-01555 snapshot too old` when undo is undersized for long-running queries.
- **[mysql](../engines/mysql.md)** (InnoDB) — undo logs + **purge** thread; long-open transactions stall purge and
  bloat the undo/history list.
- **[microsoft-sql-server](../engines/microsoft-sql-server.md)** — row-versioning (RCSI/SNAPSHOT) writes old versions to the **version
  store in tempdb**; tempdb pressure is the tell.
- LSM-based stores fold version cleanup into **compaction** (see [lsm-vs-btree](lsm-vs-btree.md)).

## Why it matters
MVCC decouples read and write throughput, but the cleanup work is *deferred*, not free — it surfaces
as background I/O, space amplification, and tail-latency spikes. **Long-running transactions are the
universal enemy**: they pin old versions and prevent reclamation everywhere. On an engine page, note
the GC mechanism and its failure mode. Contrast with pure lock-based (2PL) concurrency in
[isolation-levels](isolation-levels.md).
