---
name: Replication Models
slug: replication-models
summary: Single-leader vs multi-leader vs leaderless quorum; synchronous vs asynchronous; and the failover/split-brain story that determines your data-loss window.
last_researched: 2026-06-04
---

# Replication Models

> Replication copies data across nodes for durability, availability, and read scaling. The shape
> (who accepts writes) and the timing (when is a write "done") set your consistency, failover, and
> data-loss behavior.

## Topologies
- **Single-leader (primary/replica)** — one node takes writes, streams a log to followers. Simple,
  no write conflicts. Reads from followers may be **stale**. Failover requires electing/promoting a
  replica. The default for [postgresql](../engines/postgresql.md), [mysql](../engines/mysql.md), [microsoft-sql-server](../engines/microsoft-sql-server.md), [mongodb](../engines/mongodb.md) replica
  sets, [oracle](../engines/oracle.md) Data Guard.
- **Multi-leader** — multiple nodes accept writes (e.g. multi-region, or active-active). Buys write
  locality/availability but introduces **write-write conflicts** needing resolution (LWW, app logic,
  CRDTs). Operationally treacherous.
- **Leaderless / quorum** — any replica takes writes; consistency from **R + W > N** quorum
  overlap, with read-repair and hinted handoff. Dynamo-style: [apache-cassandra](../engines/apache-cassandra.md), [riak-kv](../engines/riak-kv.md),
  [amazon-dynamodb](../engines/amazon-dynamodb.md). Tunable per-operation.

## Sync vs async — the data-loss knob
- **Synchronous** — leader waits for replica(s) to ack before committing. No data loss on leader
  failure, but a slow/unavailable replica stalls writes (latency + availability cost). See the EC
  case of [cap-pacelc](cap-pacelc.md).
- **Asynchronous** — leader commits immediately, ships the log after. Fast, but a leader crash loses
  the unreplicated tail — a real **data-loss window**. See [wal-and-durability](wal-and-durability.md).
- **Semi-sync / quorum-sync** — wait for *some* (e.g. one replica, or a majority) — the common
  middle ground (MySQL semi-sync, [postgresql](../engines/postgresql.md) `synchronous_commit`/quorum, majority-ack systems).

## Failover & split-brain
The dangerous part. If a leader is wrongly presumed dead and a second is promoted, two leaders
accept divergent writes (**split-brain**). Defenses: **fencing/STONITH**, **quorum/consensus** for
leader election (see [consensus-raft-paxos](consensus-raft-paxos.md)), generation/epoch numbers, and leases tied to
[clocks](clocks-and-time.md). Async failover that promotes a behind replica silently **loses
acknowledged writes** — note this explicitly on engine pages.

## How to use it on engine pages
State: topology, sync/async (and whether tunable), how failover is triggered (manual / automatic /
consensus), whether follower reads are consistent, and the worst-case data-loss window. Relates to
[cap-pacelc](cap-pacelc.md) and [isolation-levels](isolation-levels.md).
