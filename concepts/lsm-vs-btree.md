---
name: LSM-Tree vs B-Tree
slug: lsm-vs-btree
summary: The two dominant on-disk storage structures — B-trees (update-in-place, read-optimized) vs LSM-trees (append/compact, write-optimized) — and the read/write/space amplification each pays.
last_researched: 2026-06-04
---

# LSM-Tree vs B-Tree

> The on-disk index structure decides an engine's write/read/space tradeoff. **B-trees** update in
> place and excel at reads; **LSM-trees** buffer writes in memory and flush sorted runs, excelling
> at writes — at the cost of background compaction.

## B-Tree (and B+Tree)
Balanced tree of fixed-size pages, updated **in place**. Leaf pages hold the data (or pointers);
lookups and range scans are O(log n) with few seeks. The default for most relational engines:
[postgresql](../engines/postgresql.md), [mysql](../engines/mysql.md) (InnoDB), [oracle](../engines/oracle.md), [microsoft-sql-server](../engines/microsoft-sql-server.md), [sqlite](../engines/sqlite.md).
- **Strengths:** fast point reads and range scans; predictable, low read amplification; mature.
- **Costs:** random writes (in-place updates dirty random pages); write amplification from full-page
  writes / page splits; needs a [WAL](wal-and-durability.md) for crash safety; pages fragment over time.

## LSM-Tree (Log-Structured Merge)
Writes go to an in-memory **memtable** + a WAL, then flush as immutable sorted files (**SSTables**)
at level 0; a background **compaction** process merges levels to control read cost and reclaim space.
Used by [rocksdb](../engines/rocksdb.md), [leveldb](../engines/leveldb.md), [apache-cassandra](../engines/apache-cassandra.md), [scylladb](../engines/scylladb.md), [apache-hbase](../engines/apache-hbase.md), and as a
WiredTiger option under [mongodb](../engines/mongodb.md).
- **Strengths:** sequential, high-throughput writes; good compression; write-heavy and ingest-heavy
  workloads.
- **Costs:** **read amplification** (a key may live in several levels → Bloom filters needed);
  **space amplification** (obsolete versions until compacted); **write amplification** (data
  rewritten across compactions); compaction competes for I/O and spikes **p99 latency**.

## The amplification triangle
You cannot minimize all three of **read**, **write**, and **space** amplification at once — tuning
(compaction strategy: leveled vs tiered, memtable size, Bloom bits) trades among them. LSM also
folds [mvcc](mvcc.md) version cleanup and deletes (via **tombstones**) into compaction, which is why
tombstone buildup and compaction backlog are classic Cassandra/Scylla operational issues.

## How to use it on engine pages
Name the structure, and tie it to behavior: B-tree → watch fragmentation and update-in-place write
amplification; LSM → watch compaction-driven p99 spikes, space amplification, and tombstones. Many
engines offer both or a pluggable storage layer — say which is default.
