# Database Engines Research Wiki

A cross-linked reference covering the **top ~150 database engines** (by
[db-engines.com ranking](https://db-engines.com/en/ranking)) plus the **adjacent data-platform
technologies** that shape real database decisions (lakehouse table formats, streaming platforms,
streaming/real-time databases, CDC, catalogs, query engines) and the **theory concepts** behind
them.

Each engine page answers, quickly: *what is it, how does it behave under stress, and when is it the
wrong tool?* — with light citations, explicit confidence levels, and honest `⚠️ unverified` flags
where claims couldn't be confirmed.

## Start here

- **[Decision guide](decision-guide.md)** — *"Which database should I use?"* Four questions, then a
  branching tree to candidates with the key trade-off **and** the anti-pattern.
- **[Index](index.md)** — full catalog, grouped by data model, one line each.

## Layout

| Path | What's in it |
|------|--------------|
| [`engines/`](engines/) | One page per engine. Ranked db-engines **and** adjacent tech (the latter flagged `adjacent: true`, `rank: n/a`, with a `category:`). |
| [`concepts/`](concepts/) | Shared theory — [CAP/PACELC](concepts/cap-pacelc.md), [isolation levels](concepts/isolation-levels.md), [ACID vs BASE](concepts/acid-vs-base.md), [LSM vs B-tree](concepts/lsm-vs-btree.md), [lakehouse](concepts/lakehouse.md), and more. Explained once, linked everywhere. |
| [`index.md`](index.md) | Catalog of every page. |
| [`decision-guide.md`](decision-guide.md) | The "which DB?" tree. |
| [`ranking.md`](ranking.md) | The worklist (top-150 + a separate adjacent-tech table). |
| [`CLAUDE.md`](CLAUDE.md) | The schema: conventions and workflows this wiki is built and maintained under. |
| [`log.md`](log.md) | Append-only operations log. |
| [`tools/`](tools/) | Maintenance scripts (link conversion + link checker). |

Coverage: **150 ranked engines + 19 adjacent technologies + 34 concept pages.**

## Conventions

- **Cross-links** are standard relative markdown links (GitHub-native). The wiki was originally
  authored with Obsidian `[[wikilinks]]` and converted via [`tools/wikilinks_to_md.py`](tools/wikilinks_to_md.py).
- **Confidence** is recorded per page (`high`/`medium`/`low`); specific unverifiable claims carry an
  inline `⚠️ unverified —` prefix.
- **Sourcing** prefers primary sources (official docs, design papers, [Jepsen](concepts/jepsen.md))
  over marketing; CAP/PACELC, isolation, and Jepsen claims are cited.

## Maintenance

```sh
python3 tools/check_links.py        # verify all internal links resolve; flag stray wikilinks
python3 tools/wikilinks_to_md.py    # (idempotent) convert any [[wikilinks]] to markdown links
```

This is an **LLM-maintained** wiki: the research, writing, and cross-linking are done by Claude
under the schema in [`CLAUDE.md`](CLAUDE.md); a human curates scope and asks questions.

### How this wiki was bootstrapped

The wiki was built with Claude Code (Opus 4.8) over three sessions, transcripts of which are
checked in:

1. **[`convo0.txt`](convo0.txt)** — used Claude to brainstorm the rubric: the set of concerns /
   dimensions every database engine should be evaluated against (data taxonomy, CAP placement,
   schema model, query language, hardware profile, licensing, etc.). This became the engine-page
   template.
2. **[`convo1.txt`](convo1.txt)** — wrote [`CLAUDE.md`](CLAUDE.md) (the schema + workflows) to
   bootstrap the full wiki using Karpathy's knowledge-base methodology — a folder of cross-linked
   markdown the LLM writes and a human reads.
3. **[`convo2.txt`](convo2.txt)** — the long-running session that researched and drafted the wiki,
   then began the manual review pass, addressing issues and improvements.

> ⚠️ **Caveat:** content is AI-generated from web research and may contain errors or go stale
> (rankings and licenses change). Pages note their `last_researched` date. Verify against primary
> sources before making decisions that matter.

## License

Documentation/content: **[CC BY 4.0](LICENSE)**. Scripts under `tools/`: **MIT** (see [LICENSE](LICENSE)).
