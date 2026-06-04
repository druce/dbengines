---
name: Hierarchical & Network Data Models
slug: hierarchical-data-model
summary: The pre-relational models — data as a tree (hierarchical, IMS) or a graph of pointers (network, CODASYL). Fast for pre-planned navigation, rigid for ad-hoc queries; mostly of historical and mainframe interest.
last_researched: 2026-06-04
---

# Hierarchical & Network Data Models

> Before the relational model, databases organized records by **explicit pointer links** rather than
> by values. The **hierarchical model** arranges records in a tree (each child has one parent); the
> **network model** (CODASYL) generalizes this to a graph where a record can have many parents. You
> navigate by following pre-defined links — fast when access paths are known, painful when they
> aren't.

## Hierarchical (tree)
Parent-child segments; one path to each record. IBM's **IMS** (1966, Apollo program) is the canonical
example — still running mission-critical mainframe OLTP. Querying anything other than the designed
hierarchy is awkward; many-to-many relationships don't fit naturally (you duplicate or add pointers).

## Network (CODASYL graph)
Records linked by named **sets** (owner→member), allowing many-to-many and multiple access paths.
More flexible than hierarchical, but programs must navigate the graph explicitly ("get next within
set") — application code is bound tightly to the physical structure.

## Why relational displaced them
Codd's relational model (1970) replaced navigational pointer-chasing with **declarative,
value-based** queries and physical data independence: you say *what* you want, not *how* to traverse.
That decoupling — plus ad-hoc querying and a clean theory — is why relational won for general use.
See [isolation-levels](isolation-levels.md), [mvcc](mvcc.md) for how relational systems handle concurrency the navigational
era handled manually.

## Echoes today
- **Document model** ([document-data-model](document-data-model.md)) revives hierarchy *within* a record (nested
  JSON) while keeping value-based query.
- **Graph databases** ([graph-data-model](graph-data-model.md)) revive explicit relationship traversal — but
  declaratively (Cypher/Gremlin) and as a first-class, queryable model, not hand-coded navigation.
- **MultiValue** ([multivalue-data-model](multivalue-data-model.md)) is a related pre-/post-relational lineage.

## How to use it on engine pages
Relevant mainly to legacy engines ([adabas](../engines/adabas.md), IMS-style systems) and as context for why relational/
document/graph models exist. Note when an engine is navigational (pointer-based) vs declarative.
