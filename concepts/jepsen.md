---
name: Jepsen
slug: jepsen
summary: Kyle Kingsbury's black-box distributed-systems testing framework that injects faults (partitions, clock skew, crashes) and checks whether a database actually delivers its claimed consistency — it usually doesn't, at least at first.
last_researched: 2026-06-04
---

# Jepsen

> [Jepsen](https://jepsen.io) is a testing framework and a body of analyses (by Kyle Kingsbury,
> "aphyr") that subject distributed databases to **realistic faults** — network partitions, process
> crashes, clock skew, membership changes — while a client hammers them, then check the recorded
> history against the consistency model the database **claims**. A Jepsen result is the closest
> thing this field has to an independent, adversarial audit.

## How it works
- Drives concurrent operations against a real cluster while a **nemesis** injects faults.
- Records a history of invocations and completions.
- Checks that history with consistency checkers — notably **Elle**, which finds transactional
  isolation anomalies ([isolation-levels](isolation-levels.md)) — for violations of linearizability, serializability,
  snapshot isolation, etc. (see [cap-pacelc](cap-pacelc.md)).

## Why it matters
Marketing claims ("strongly consistent", "ACID") routinely diverge from behavior under partition.
Jepsen has repeatedly found **acknowledged writes lost**, stale reads, and isolation weaker than
advertised — frequently at default settings. Many vendors fixed real bugs in response, so a *recent*
Jepsen pass is meaningful; an old one may not reflect the current version.

## Recurring findings on engines in this wiki
- [mongodb](../engines/mongodb.md) — multiple analyses found anomalies/lost updates; safe behavior needs non-default
  `w:majority` + majority/snapshot read concern.
- [elasticsearch](../engines/elasticsearch.md) — lost acknowledged writes under partition (it is a search index, not a system
  of record — see [full-text-search](full-text-search.md)).
- [mariadb](../engines/mariadb.md) / Galera — found far weaker than its claimed isolation (2026).
- Several [consistency](cap-pacelc.md) claims for distributed SQL ([cockroachdb](../engines/cockroachdb.md), [tidb](../engines/tidb.md),
  [yugabytedb](../engines/yugabytedb.md)) and [redis](../engines/redis.md) failover have been examined; read the specific report and version.

## How to use it on engine pages
If a Jepsen report exists, **cite it and state the version tested and the verdict** — especially any
gap between claim and observed behavior. Note whether safe behavior requires non-default settings.
Absence of a Jepsen report is itself worth noting for systems that claim strong distributed guarantees.
