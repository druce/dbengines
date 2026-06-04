---
name: WAL & Durability
slug: wal-and-durability
summary: Write-ahead logging, fsync policy, and group commit — the machinery behind the "D" in ACID, and the knobs that set your crash data-loss window.
last_researched: 2026-06-04
---

# WAL & Durability

> Durability (the **D** in ACID) means a committed write survives a crash. The near-universal
> mechanism is the **write-ahead log**: append the change to a sequential log and `fsync` it
> *before* acknowledging the commit. The fsync policy is the dial between throughput and data loss.

## Write-ahead logging
Append-only log of changes written **before** the corresponding data pages are updated
([B-tree](lsm-vs-btree.md) pages or memtable flushes). On crash, replay the log to recover committed
work and roll back the rest. Sequential log writes are cheap; the data files can be updated lazily.
Names vary: WAL ([postgresql](../engines/postgresql.md), [sqlite](../engines/sqlite.md)), **redo log** + binlog ([mysql](../engines/mysql.md) InnoDB), **transaction
log** ([microsoft-sql-server](../engines/microsoft-sql-server.md)), **redo/undo** ([oracle](../engines/oracle.md)), commit log ([apache-cassandra](../engines/apache-cassandra.md)).

## The fsync tradeoff — your data-loss window
- **fsync on every commit** — durable to the moment of ack; bounded by disk fsync latency
  (~ms on SSD). Safe default.
- **Group commit** — batch many transactions' fsyncs into one, amortizing the cost: higher
  throughput, durability preserved, slight latency add. Standard in modern engines.
- **Relaxed / async / periodic flush** — ack before fsync (e.g. MySQL
  `innodb_flush_log_at_trx_commit=0/2`, [postgresql](../engines/postgresql.md) `synchronous_commit=off`, Mongo `j:false`).
  Faster, but a crash loses the last interval of "committed" writes — an explicit, **non-zero
  data-loss window**.

Distributed durability adds replication: a write durable on one node can still be lost if that node
dies before replicating — see sync vs async in [replication-models](replication-models.md). "Durable" should specify
*durable where* (local disk vs majority of replicas).

## Gotchas to flag
- **Lying disks / `fsync` not honored** — virtualized or misconfigured storage may ack fsync without
  persisting; defeats the WAL guarantee.
- **OS page cache vs O_DIRECT** — a write to the cache is not on disk.
- **Default settings** — many engines ship durable-by-default, but managed/perf-tuned configs often
  relax it. State the default and the window on engine pages.

Relates to [cap-pacelc](cap-pacelc.md) (a partition can force a choice between losing the unreplicated tail and
refusing writes) and [mvcc](mvcc.md) (undo/version data is itself logged).
