---
name: Consensus (Raft & Paxos)
slug: consensus-raft-paxos
summary: How a cluster agrees on one value (or one log order) despite failures — the backbone of leader election and strongly-consistent replication.
last_researched: 2026-06-04
---

# Consensus — Raft & Paxos

> Consensus protocols let a group of nodes **agree on a single value or a single ordering of a log**
> even when some nodes crash or messages are lost. They are how strongly-consistent distributed
> databases elect leaders and replicate writes without split-brain.

## What they guarantee
A correct consensus protocol provides **safety** (never two conflicting decisions) always, and
**liveness** (eventually decides) when a majority is up and the network is reasonably timely. They
need a **majority quorum** (⌊N/2⌋+1), so they tolerate ⌊(N-1)/2⌋ failures — 1 of 3, 2 of 5. They
assume crash-stop, not Byzantine, faults.

## Paxos vs Raft
- **Paxos** ([Lamport](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)) — the original;
  correct but notoriously hard to understand and to implement faithfully. **Multi-Paxos** extends it
  to a replicated log. Used in [google-cloud-spanner](../engines/google-cloud-spanner.md), Chubby, and many internal systems.
- **Raft** ([Ongaro & Ousterhout](https://raft.github.io/raft.pdf)) — designed for understandability;
  decomposes into **leader election + log replication + safety**. A single leader appends to
  followers' logs; a new election (randomized timeouts, term numbers) recovers from leader loss.
  Used in [etcd](../engines/etcd.md), [cockroachdb](../engines/cockroachdb.md), [tidb](../engines/tidb.md) (per-Raft-group), [yugabytedb](../engines/yugabytedb.md), Consul.

## Where it shows up in databases
- **Leader election / failover** without split-brain (vs the ad-hoc promotion risk in
  [replication-models](replication-models.md)).
- **Strongly-consistent write replication** — commit once a majority has the log entry (the EC/PC
  case of [cap-pacelc](cap-pacelc.md)).
- **Per-shard consensus groups** — sharded systems run one Raft group per shard
  ([cockroachdb](../engines/cockroachdb.md) ranges, [tidb](../engines/tidb.md) regions) so consensus scales horizontally.
- **Configuration/metadata stores** — [etcd](../engines/etcd.md), ZooKeeper (ZAB, a Paxos-like protocol) hold cluster
  membership and locks.

## Caveats to flag
Consensus gives linearizable agreement on the **log**, but end-to-end correctness still depends on
read handling (leader leases vs quorum reads can serve stale data if misconfigured) and on
[clock](clocks-and-time.md) assumptions for leases. "Uses Raft" ≠ "fully linearizable for reads" —
check the read path.
