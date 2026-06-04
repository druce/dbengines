---
name: Isolation Levels
slug: isolation-levels
summary: The ANSI levels, the anomalies they do and don't prevent, and why "serializable" on the label often means snapshot isolation in practice.
last_researched: 2026-06-04
---

# Isolation Levels

> Isolation is the **I** in ACID: how much concurrent transactions can interfere. The ANSI SQL
> levels are defined by which **anomalies** they forbid — and vendors implement them inconsistently,
> so the label rarely tells you the real guarantee.

## The anomalies
- **Dirty read** — read another transaction's uncommitted write.
- **Non-repeatable read** — re-reading a row returns a different committed value.
- **Phantom** — a re-run query returns a different *set* of rows (inserts/deletes).
- **Write skew** — two transactions each read an overlapping set, then write disjoint rows; both
  commit, violating an invariant neither alone broke. **Snapshot isolation permits write skew.**
- **Lost update** — two read-modify-writes, one clobbers the other.

## ANSI levels (weakest → strongest)
| Level | Forbids |
|---|---|
| Read Uncommitted | (nothing — dirty reads allowed) |
| Read Committed | dirty reads |
| Repeatable Read | + non-repeatable reads |
| Serializable | + phantoms; result equiv. to *some* serial order |

The ANSI definitions are famously underspecified; the [Berenson et al. "A Critique of ANSI SQL
Isolation Levels"](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-95-51.pdf)
paper added **Snapshot Isolation (SI)** as a distinct level the standard missed.

## Snapshot Isolation — the great mislabel
SI gives every transaction a consistent snapshot as of its start; first-committer-wins on conflicts.
It prevents dirty/non-repeatable reads and (in practice) phantoms, **but allows write skew**, so it
is *not* serializable. Critically, several engines call SI "SERIALIZABLE":
- [oracle](../engines/oracle.md) — its `SERIALIZABLE` is snapshot isolation; true serializability is not offered.
- Many MVCC systems default to Read Committed and offer SI as "Repeatable Read."

True serializability requires extra machinery:
- **SSI** (Serializable Snapshot Isolation) — [postgresql](../engines/postgresql.md) detects dangerous read/write
  dependency cycles and aborts a transaction; real serializable on top of [mvcc](mvcc.md).
- **2PL / strict 2PL** — lock-based, e.g. [microsoft-sql-server](../engines/microsoft-sql-server.md) `SERIALIZABLE` (range locks).
- **Deterministic / external-consistency** — [google-cloud-spanner](../engines/google-cloud-spanner.md), [cockroachdb](../engines/cockroachdb.md).

## How to use it on engine pages
Always state the **default** level and what's **achievable**. Flag any "ACID"/"serializable" claim
that is really SI. Note the mechanism (locking vs MVCC vs SSI) because it determines whether you pay
in blocking (readers block writers) or in aborts/retries (serialization failures). See [mvcc](mvcc.md) and
[cap-pacelc](cap-pacelc.md) (serializable ≠ linearizable).
