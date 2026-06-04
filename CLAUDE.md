# Database Engines Research Wiki — Schema & Workflows

This repository is an **LLM-maintained wiki** about database engines, built on Karpathy's
knowledge-base pattern: a folder of cross-linked markdown files that *you* (Claude) write and
maintain, that a human reads and queries. This file is the **schema** — it defines the
conventions and the workflows. Follow it exactly.

> The human curates scope and asks questions. You do all the research, writing, cross-linking,
> and bookkeeping. The human reads; you write.

---

## 1. Goal & scope

Build a research wiki covering the **top 150 database engines** by
[db-engines.com ranking](https://db-engines.com/en/ranking).

For each engine, produce a page that lets a technical reader quickly understand *what it is, how
it behaves under stress, and when it is the wrong tool*. The dimensions to cover are fixed — see
the **engine page template** (§4).

**Adjacent data-platform technologies.** The wiki also covers technologies that are *not* ranked
db-engines but materially shape a database decision — lakehouse **table formats** (Iceberg, Delta),
**streaming platforms** (Kafka), **streaming/real-time databases**, **CDC**, **catalogs**, and
**query engines**. These live in `engines/` alongside ranked engines, distinguished by frontmatter
(`adjacent: true`, `rank: n/a`, plus a `category:`); they are excluded from the top-150 ranking and
worklist (§7), and tracked in a separate `ranking.md` section. Add one when an engine page keeps
linking it or when the decision guide (§8) needs it.

**Research mode: active.** You research engines yourself via web search and doc fetches. You do
not wait for the human to supply sources. If the human *does* drop an authoritative source
(official docs, a paper, a Jepsen report), it takes precedence over secondary sources.

**Sourcing: light citations.** Cite a source inline for:
- any contentious, surprising, or version-specific claim,
- every CAP/PACELC, isolation-level, and consistency claim,
- every Jepsen / formal-verification result.
General, uncontroversial knowledge does not need an inline citation. When you assert something
you could not verify, **flag it** explicitly (see §4, confidence markers). Prefer primary sources
(official docs, the engine's own design papers, Jepsen) over blogs and marketing pages. Never
state a marketing claim ("fully ACID", "infinitely scalable") as fact — attribute it and, where
possible, say what it actually means in practice.

---

## 2. Directory structure

```
dbengine/
├── CLAUDE.md            # this file — the schema (conventions + workflows)
├── index.md            # catalog of all pages, grouped by data model, one-liner each
├── log.md              # append-only operations log
├── ranking.md          # the top-150 worklist with per-engine status
├── decision-guide.md   # "which DB should I use?" question tree (built AFTER research — §8)
├── engines/            # one page per engine; also adjacent tech (adjacent: true) e.g. apache-iceberg.md
└── concepts/           # shared theory pages linked from engine pages, e.g. concepts/cap-pacelc.md
```

`engines/` holds both **ranked db-engines** and **adjacent technologies** (§1); they are the same
file shape and link the same way (relative markdown links — see §3), distinguished only by
frontmatter (`adjacent: true`, `rank: n/a`, `category:`). The index (§5) and `ranking.md` keep them
in separate sections.

**Naming:** files are lowercase kebab-case of the canonical engine name.
`PostgreSQL` → `engines/postgresql.md`, `Amazon DynamoDB` → `engines/amazon-dynamodb.md`,
`Microsoft SQL Server` → `engines/microsoft-sql-server.md`. Record the exact db-engines display
name in frontmatter (`name:`) so the slug stays predictable.

---

## 3. Cross-linking

Connect pages with **standard relative markdown links** (GitHub renders these natively). The repo
was converted from Obsidian `[[wikilinks]]` by `tools/wikilinks_to_md.py` — author new links in
markdown form. The target is the page file, path relative to the *linking* file:
- from an `engines/` or `concepts/` page: `[postgresql](postgresql.md)` (same dir),
  `[mvcc](../concepts/mvcc.md)` (cross dir)
- from a root doc (`index.md`, `decision-guide.md`): `[oracle](engines/oracle.md)`

Use the slug or a readable phrase as the link text. Link liberally — but if a target page doesn't
exist yet, leave the term as **plain text** rather than a broken link (a path that 404s is worse
than no link). Run `tools/check_links.py` to catch broken links and stray wikilinks.
**Do not re-explain theory on every engine page.** Explain CAP/PACELC, isolation levels, LSM vs
B-tree, etc. *once* in `concepts/` and link to it. Create a concept page the first time an engine
page needs it. Suggested seed concepts (create on first reference):
`cap-pacelc`, `isolation-levels`, `replication-models`, `consensus-raft-paxos`,
`lsm-vs-btree`, `mvcc`, `storage-compute-separation`, `oltp-olap-htap`, `wal-and-durability`,
`license-taxonomy`, `clocks-and-time`.

---

## 4. Engine page template

Every page in `engines/` uses this exact structure. Keep each section to a few tight sentences —
this is a reference, not an essay. Omit a row only if genuinely N/A (say "N/A — single-node").

````markdown
---
name: PostgreSQL                 # exact db-engines display name
slug: postgresql
rank: 4                          # current db-engines rank
data_model: Relational           # primary model (see index.md categories)
license: PostgreSQL License (permissive)
summary: Battle-tested open-source relational DB; the safe default for OLTP.
last_researched: 2026-06-04
confidence: high                 # high | medium | low — overall page confidence
---

# PostgreSQL

> One-sentence summary. **This line is the most important on the page** — it is what gets read
> first to decide whether the rest is relevant. Make it earn its place.

## Identity
- **Taxonomy / data model:** relational, document, KV, wide-column, graph, time-series, vector,
  search, multi-model, object, ... See [oltp-olap-htap](../concepts/oltp-olap-htap.md) for the workload axis.
- **Storage model:** row-store / column-store / hybrid; [lsm-vs-btree](../concepts/lsm-vs-btree.md); on-disk format.
- **Workload:** OLTP / OLAP / HTAP. **If it claims HTAP, say how it physically separates the two**
  (separate replicas, columnar secondary index, delta store, etc.) — vague HTAP claims get flagged.

## Distribution & consistency
- **CAP under partition:** CP (refuses writes to stay consistent) or AP (stays up, reconciles
  later)? CAP is coarse — see [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** the partition behavior *and* the else-case latency-vs-consistency tradeoff.
- **Default isolation & what's achievable:** read committed / snapshot / serializable. Note when
  an "ACID" claim really means snapshot isolation, not serializable. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** single-leader / multi-leader / leaderless quorum (R+W>N); sync vs async;
  failover & split-brain story. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** per-query consistency levels (Dynamo/Cassandra-style)?
- **Clock dependency:** does correctness rest on synchronized clocks (TrueTime, HLCs)?
  See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write vs schema-on-read;** rigid / flexible / schemaless (note: "schemaless" usually
  means the schema lives in app code).
- **Migration/evolution:** online DDL, or does `ALTER` lock the table?
- **Type system:** native JSON, arrays, geospatial, vectors, intervals, etc.

## Query interface
- **Language:** SQL (which dialect / standard compliance), a DSL (CQL, AQL, Cypher/GQL, PromQL),
  or API-only (get/put)?
- **Transactions:** full multi-statement ACID / single-row atomicity / none.
- **Native vs app-side:** secondary indexes, joins, aggregations, window functions.
- **Stored procedures / UDFs** and in what language.

## Scaling & topology
- **Vertical vs horizontal;** sharding (auto vs manual, resharding pain), partitioning scheme.
- **Read replicas** and whether reads from them are consistent.
- **Storage/compute separation** (Snowflake/Aurora/Neon pattern)? See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** WAL, fsync policy, group commit; **data-loss window on crash.**
  See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency profile;** tail (p99) behavior, not just averages.
- **Compaction / vacuum / GC** behavior and its impact on p99.

## Operations & maturity
- **Backup/restore, PITR, snapshotting.**
- **Observability:** metrics, EXPLAIN/query plans, slow-query logs.
- **Upgrade story** (rolling / downtime) and the day-2 operational burden.
- **Maturity:** production track record, known failure modes, **Jepsen result if one exists**
  (cite it).

## Ecosystem & people
- **Canonical use cases** — and the **anti-patterns** where it's the wrong tool.
- **Drivers / ORMs / connectors** (CDC, Kafka, dbt, BI tools).
- **Community size, commercial support, docs quality;** learning curve and typical team size;
  engineer availability.

## Licensing & cost
- **OSS license & flavor:** permissive (Apache/MIT/BSD) vs copyleft vs source-available
  (SSPL, BSL/Elastic, Confluent Community). Note any post-2018 relicensing. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed-only;** lock-in via proprietary extensions.
- **Cost model:** per-node / per-core / per-GB / per-query-serverless — and how it behaves at
  scale (cheap-at-small often inverts).

## Hardware / deployment
- **Resource profile:** memory-bound / disk-bound / CPU-bound; must the working set (or all data)
  fit in RAM?
- **Storage assumptions:** NVMe vs spinning, local vs network-attached (EBS-style latency
  tolerance).
- **Footprint:** single-node / clustered / embedded (SQLite/DuckDB/RocksDB style) / serverless.
- **Deployment:** SaaS vs on-prem; container/k8s friendliness, StatefulSet realities.

## Bottom line
2–4 sentences: who should reach for this, who should not, and the single biggest gotcha.

## Sources
- [Official docs](...)
- [Jepsen report](...) (if any)
- ...
````

**Confidence markers.** Use overall `confidence:` in frontmatter, and inline `⚠️ unverified —`
prefix on any specific claim you could not confirm from a credible source. Better an honest flag
than a confident error.

**Adjacent (non-ranked) pages.** Use the same template, lighter. Frontmatter replaces `rank: N` with
`adjacent: true`, `rank: n/a`, and adds `category:` ∈ `table-format` · `streaming-platform` ·
`streaming-database` · `real-time-olap` · `query-engine` · `catalog` · `cdc`. Keep all sections but
mark genuinely-inapplicable ones `N/A — <reason>` (e.g. isolation levels on a table format). The
load-bearing one-liner and the **Bottom line** (with its anti-pattern) are still required.

---

## 5. index.md

A content catalog grouped by **data model**, with a one-line summary per engine and a relative `[link](path.md)`.
Keep it sorted by rank within each group. Categories (a multi-model engine appears under its
primary model, with a "(also: …)" note):

`Relational` · `Document` · `Key-value` · `Wide-column` · `Graph` · `Time-series` ·
`Search engine` · `Vector` · `Multi-model` · `Object` · `Other`

Each line: `- **[slug](engines/slug.md)** (rank N) — one-liner.`

**Adjacent technologies** go in a separate trailing section `## Adjacent / data platform (not
ranked)`, sub-grouped by `category` (table formats, streaming platforms, streaming/real-time
databases, real-time OLAP, query engines, catalogs, CDC). Their lines read
`- **[slug](engines/slug.md)** (adjacent) — one-liner.` (no rank).

---

## 6. log.md

Append-only. One line per operation, newest at the bottom, consistent prefix:

```
## [YYYY-MM-DD] <operation> | <engine or scope>
```

`operation` ∈ `ingest` (new page), `update` (revised page), `lint`, `bootstrap`, `decision-guide`.
Add a half-line of what changed. Never rewrite history.

---

## 7. Workflows

### 7.0 Bootstrap (run once)
1. Fetch [db-engines.com/en/ranking](https://db-engines.com/en/ranking) and capture the top 150
   (rank, name, data model, score).
2. Write them to `ranking.md` as a checklist, each with `status: todo`.
3. Initialize `index.md` groups (empty) and append a `bootstrap` line to `log.md`.

### 7.1 Research one engine (`ingest`)
1. Pick the next `todo` from `ranking.md`; set it `in-progress`.
2. Research, prioritizing: official docs → design papers → Jepsen → db-engines entry → reputable
   secondary sources. Resolve conflicts toward primary sources; note unresolved conflicts.
3. Write `engines/<slug>.md` from the template. Fill every section; flag what you couldn't verify.
4. Create any `concept` page you linked that doesn't exist yet.
5. Add the engine to `index.md` under its primary model.
6. Set `status: done` (with date) in `ranking.md`; append an `ingest` line to `log.md`.

### 7.2 Batch research
Process the next N `todo` engines. **This is parallelizable** — each engine page is independent,
so the human may fan this out across subagents (one engine per agent). When doing so: each agent
writes only its own `engines/<slug>.md` and returns the one-liner + index category; the
orchestrator does the shared-file edits (`index.md`, `ranking.md`, `log.md`) to avoid write
conflicts. Concept pages: if two agents need the same new concept, create a stub and let the
orchestrator reconcile during lint.

### 7.3 Query
Answer the human's question against the wiki. Read the relevant pages (use the one-line summaries
and `index.md` to decide which), synthesize, and **cite the pages** you used. If the answer is
reusable and not already captured, offer to promote it to a new page (a concept page or an entry
in `decision-guide.md`).

### 7.4 Lint (health check)
Periodically, or on request:
- **Contradictions:** claims that conflict across pages.
- **Stale:** `last_researched` older than ~6 months, or a known major release since.
- **Orphans:** pages no page links to; **missing backlinks:** A links B but B should link A.
- **Coverage:** `todo` engines remaining; sections left empty or thin.
- **Unsourced contentious claims** lacking a citation or `⚠️` flag.
Report findings and fix the cheap ones; append a `lint` line to `log.md`.

---

## 8. decision-guide.md — build AFTER research

Do **not** design the decision tree up front. Build it once enough engine pages exist, by reading
the actual data. The goal: **the fewest, highest-signal questions first**, then drill down to the
best answer fastest.

Process:
1. After a substantial batch of engines is researched, analyze which dimensions partition the
   space most cleanly (likely workload OLTP/OLAP/HTAP, consistency/distribution needs, scale &
   topology, data model, license constraints — but **let the data decide the order**, not this
   list).
2. Identify the 2–4 questions that, asked first, eliminate the most candidates. State them as the
   fixed "always ask these first" questions.
3. Then a branching tree drilling to leaves. Each leaf names `engine` candidates with the
   key trade-off **and** the anti-pattern (when *not* to pick it).
4. Re-derive the question order whenever coverage materially grows; record changes in `log.md`
   under `decision-guide`.

Keep it usable as a checklist a human can walk top-to-bottom in a couple minutes.

---

## 9. Style

- Reference, not essay. Tight sentences. No marketing voice.
- Be specific and falsifiable ("snapshot isolation by default; serializable available via SSI"
  beats "strong consistency").
- When an engine's claim and its real-world behavior diverge, say so — that divergence is the
  most valuable thing on the page.
- The one-line summary at the top of each page is load-bearing. Write it last, after you
  understand the engine.
