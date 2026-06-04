---
name: Vector Search & ANN
slug: vector-search-ann
summary: Indexing high-dimensional embeddings for approximate-nearest-neighbor similarity search — the storage problem behind semantic search and RAG, trading recall for speed.
last_researched: 2026-06-04
---

# Vector Search & ANN

> A **vector database / index** stores high-dimensional embedding vectors and answers "find the K
> nearest to this query vector" by a distance metric (cosine, dot product, L2). Exact nearest
> neighbor is O(N) per query, so production systems use **Approximate Nearest Neighbor (ANN)** — a
> recall-vs-latency trade.

## Why approximate
Exact search over millions of 768–3072-dim vectors is too slow. ANN indexes accept a small recall
loss to get sub-millisecond queries. **Recall@K** (fraction of true neighbors returned) is the
quality knob; you tune it against latency, memory, and build time.

## The main index families
- **HNSW** (Hierarchical Navigable Small World) — a layered proximity graph; excellent recall/latency,
  high memory, the de facto default. Used by [qdrant](../engines/qdrant.md), [weaviate](../engines/weaviate.md), [milvus](../engines/milvus.md), [elasticsearch](../engines/elasticsearch.md),
  [opensearch](../engines/opensearch.md), pgvector ([postgresql](../engines/postgresql.md)), [redis](../engines/redis.md).
- **IVF** (inverted file / coarse quantization) — cluster vectors, search only nearby cells. Lower
  memory, tunable nprobe.
- **PQ / scalar quantization** — compress vectors (product quantization) to cut memory ~4–32× at some
  recall cost; often combined with IVF (IVF-PQ) or HNSW.
- **DiskANN / disk-based** — keep vectors on SSD for billion-scale at lower RAM ([microsoft-azure-ai-search](../engines/microsoft-azure-ai-search.md)).

## Filtered & hybrid search
Real workloads need **metadata filtering** ("nearest vectors *where tenant=X and date>Y*") — naive
post-filtering breaks recall, so engines do pre-/in-filter integration. **Hybrid search** fuses ANN
with keyword/[full-text-search](full-text-search.md) (BM25) via rank fusion (RRF) — the common pattern for RAG.

## Dedicated vs bolt-on
- **Purpose-built** — [pinecone](../engines/pinecone.md), [milvus](../engines/milvus.md), [qdrant](../engines/qdrant.md), [weaviate](../engines/weaviate.md), [chroma](../engines/chroma.md): scale, filtering,
  and ops tuned for vectors.
- **Added to existing engines** — pgvector, [redis](../engines/redis.md), [mongodb](../engines/mongodb.md), [elasticsearch](../engines/elasticsearch.md),
  [clickhouse](../engines/clickhouse.md), [microsoft-sql-server](../engines/microsoft-sql-server.md) 2025: one fewer system to run, usually fine until very
  large scale or very high QPS.

## How to use it on engine pages
Note the index type(s), the distance metrics, whether filtering is pre/post/integrated, hybrid-search
support, and memory footprint (RAM-resident HNSW vs disk-based). For RAG context, mention quantization
and recall tuning. A "vector support" checkbox says little — the index and filtering story is what matters.
