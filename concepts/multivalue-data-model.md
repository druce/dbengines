---
name: MultiValue Data Model
slug: multivalue-data-model
summary: The PICK-lineage "nested relational" model — records whose fields can themselves hold lists (multivalues) and lists-of-lists, queried via an embedded BASIC 4GL. Niche but still running line-of-business apps.
last_researched: 2026-06-04
---

# MultiValue Data Model

> The **MultiValue** (a.k.a. PICK, post-relational, "nested relational") model stores variable-length
> records whose individual fields can contain **multiple values** — and even nested
> sub-multivalues — instead of forcing first-normal-form atomic columns. One MultiValue record can
> hold what relational design would split across a parent table and several child tables.

## How it works
- A **file** holds **items** (records) keyed by an ID; each item has **attributes** (fields), and an
  attribute can hold a **multivalued** list, with **subvalues** below that — three dimensions in one
  record. Schema is light/late-bound; layout often lives in dictionaries and application code.
- Data is typically ASCII, delimiter-separated. Access is by key and via a 4GL — an embedded
  **BASIC** dialect (DataBASIC) — tightly coupling apps to the data.
- It deliberately **violates first normal form**: the multivalue *is* the join, so common parent-child
  relationships are read without an actual join.

## Strengths and anti-patterns
- **Strengths:** very fast key-and-list access for the modeled app; compact; decades-stable
  line-of-business apps (ERP, retail, healthcare, government) keep running on it cheaply.
- **Anti-patterns:** ad-hoc relational/analytical querying, integration with SQL/BI tooling,
  and finding engineers — it's a small, aging talent pool. Schema-in-code hides structure.

## Lineage & engines
Born from Dick Pick's 1960s work; the family includes [UniData and UniVerse](../engines/unidata-universe.md)
(Rocket Software), D3, jBASE, and OpenQM. Related to the pre-relational lineage in
[hierarchical-data-model](hierarchical-data-model.md); conceptually a precursor to today's [document](document-data-model.md)
model (nested data as a first-class citizen, value-based rather than pointer-based).

## How to use it on engine pages
Relevant to [unidata-universe](../engines/unidata-universe.md) and [adabas](../engines/adabas.md)-style legacy engines. Note the 4GL coupling, the
non-1NF nested records, and the "chosen only because the app already requires it" reality.
