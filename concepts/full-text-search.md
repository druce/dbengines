---
name: Full-Text Search
slug: full-text-search
summary: The inverted index — map terms to the documents containing them — plus analysis and relevance ranking (TF-IDF/BM25); the engine behind keyword search, log analytics, and SIEM.
last_researched: 2026-06-04
---

# Full-Text Search

> Full-text search finds documents by their **content**, ranked by relevance, not by exact key
> lookup. The core structure is the **inverted index**: a dictionary mapping each term to a posting
> list of the documents (and positions) where it appears.

## The pipeline
1. **Analysis** — tokenize text, lowercase, remove stop words, apply stemming/lemmatization,
   synonyms, n-grams, language-specific rules. Query text is analyzed the same way so terms match.
2. **Inverted index** — term → postings (doc IDs + term frequencies + positions). Positions enable
   phrase and proximity queries. Lucene-family indexes are immutable segments merged in the
   background (an [LSM](lsm-vs-btree.md)-like write path).
3. **Relevance ranking** — score matches by **TF-IDF** or, by default in modern engines, **BM25**
   (term frequency saturation + document-length normalization). Boosting, field weights, and
   function scoring tune results.

## Capabilities beyond keywords
Faceting/aggregations, highlighting, fuzzy/typo tolerance, autocomplete, geo and numeric filters,
and increasingly **hybrid search** combining BM25 with [vector ANN](vector-search-ann.md) for semantic
relevance (rank fusion / RRF).

## Engines
- **Lucene-based** — [elasticsearch](../engines/elasticsearch.md), [opensearch](../engines/opensearch.md), [apache-solr](../engines/apache-solr.md): distributed search + JSON
  document store + analytics.
- **Other dedicated** — [splunk](../engines/splunk.md) (machine data / SIEM, schema-on-read), [algolia](../engines/algolia.md) and
  [coveo](../engines/coveo.md) (hosted), [meilisearch](../engines/meilisearch.md), [sphinx](../engines/sphinx.md), [amazon-cloudsearch](../engines/amazon-cloudsearch.md).
- **In-database FTS** — [postgresql](../engines/postgresql.md) (`tsvector`/GIN), [mysql](../engines/mysql.md)/[mariadb](../engines/mariadb.md) FULLTEXT,
  [sqlite](../engines/sqlite.md) FTS5, [mongodb](../engines/mongodb.md) text/Atlas Search, [clickhouse](../engines/clickhouse.md).

## Consistency caveat
Search engines are typically **near-real-time** (a refresh interval makes writes searchable, not
instantly) and historically weak as a **system of record** — e.g. [elasticsearch](../engines/elasticsearch.md) lost
acknowledged writes under partition in Jepsen testing (see [jepsen](jepsen.md), [cap-pacelc](cap-pacelc.md)). Treat them
as a queryable index fed from a durable primary store, not the primary itself.

## How to use it on engine pages
Note the index structure (inverted/Lucene), the analysis/ranking model (BM25?), NRT vs synchronous
visibility, hybrid/vector support, and whether it's safe as a primary store or an index downstream
of one.
