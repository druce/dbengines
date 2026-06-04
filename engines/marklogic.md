---
name: MarkLogic
slug: marklogic
rank: 72
data_model: Multi-model (Document + RDF triples + Search + Vector)
license: Proprietary / source-available developer license (Progress Software)
summary: Enterprise document + semantic NoSQL engine with genuine multi-document ACID, a built-in search engine, and an XQuery/JavaScript runtime — powerful, expensive, and idiosyncratic.
last_researched: 2026-06-04
confidence: medium
---

# MarkLogic

> A proprietary, multi-model (XML/JSON document + RDF triple + full-text search) NoSQL database that — unusually for NoSQL — offers real multi-document, multi-statement ACID transactions and a deep universal index, aimed at large enterprise/government data-integration workloads.

## When to use

**Use MarkLogic if:**
- ✅ You must integrate messy heterogeneous documents (XML/JSON) plus a knowledge graph (RDF/SPARQL) and full-text search in one engine
- ✅ You need genuine multi-document, multi-statement ACID transactions over semi-structured content (rare for NoSQL)
- ✅ You are building an "operational data hub" for enterprise/government/publishing/finance, often search- and regulation-heavy
- ✅ You have (or can fund) XQuery/MarkLogic specialist DBAs and enterprise budget

**Avoid MarkLogic if:**
- ❌ It is enterprise-priced and proprietary lock-in (XQuery + MarkLogic-specific index model), and its strong ACID claims are vendor-asserted with no public Jepsen verification
- ❌ You need plain relational/KV OLTP (overkill and costly) or columnar analytics/BI warehousing
- ❌ You are a cost- or talent-constrained team, or lack the discipline that forest/stand/merge tuning demands

## Identity
- **Taxonomy / data model:** Multi-model. Primarily a [document-data-model](../concepts/document-data-model.md) (XML and JSON as first-class fragments) with a native RDF triple store ([graph-data-model](../concepts/graph-data-model.md), queryable via SPARQL), an integrated [full-text-search](../concepts/full-text-search.md) engine, and (from Server 12) native [vector](../concepts/vector-search-ann.md) embeddings. Grew out of an XML database lineage ([Wikipedia](https://en.wikipedia.org/wiki/MarkLogic)).
- **Storage model:** Document/fragment store backed by an [LSM-like](../concepts/lsm-vs-btree.md) structure: documents land in an in-memory **stand**, are journaled, then flushed to immutable on-disk **stands** within a **forest**; background **merges** compact stands (forests cap at 64 stands or become unavailable) ([MarkLogic docs](https://docs.marklogic.com/9.0/guide/concepts/backup-replication)). On-disk fragments carry validity timestamp ranges for [MVCC](../concepts/mvcc.md). A "universal index" (term lists, structure, values, range, geospatial, reverse, triple indexes) is maintained on write.
- **Workload:** Operational + search/analytics over semi-structured content; positioned for data-integration "operational data hubs." Not a columnar OLAP engine. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Search and triple workloads run against the same indexes, but it is not an HTAP columnar system — treat any HTAP framing skeptically.

## Distribution & consistency
- **CAP under partition:** CP-leaning. Updates use locking and two-phase commit across forests; a forest whose host is partitioned away is unavailable for writes unless failover promotes a replica. See [cap-pacelc](../concepts/cap-pacelc.md). ⚠️ unverified — MarkLogic publishes no formal CAP/PACELC classification and there is no public [jepsen](../concepts/jepsen.md) report.
- **PACELC:** ⚠️ unverified — no vendor PACELC statement. In practice: under Partition it favors Consistency (refuse/wait on unavailable forests); Else it favors Consistency/latency-cost via the contemporaneous-timestamp wait described below.
- **Default isolation & what's achievable:** Two transaction types ([MarkLogic docs](https://docs.marklogic.com/9.0/guide/app-dev/transactions)). **Query (read-only) transactions** run at a fixed system timestamp and get a read-consistent / [snapshot](../concepts/mvcc.md)-style view without locks. **Update transactions** acquire reader/writer (exclusive-write) locks on demand, held to commit, and see the latest committed version at first access. This is effectively snapshot isolation for reads plus pessimistic locking for writes — not full serializability across read-write mixes. ⚠️ unverified — "100% ACID" is the vendor's phrasing; it does not mean SERIALIZABLE in the SQL sense. See [isolation-levels](../concepts/isolation-levels.md).
- **MVCC timestamp choice:** Query transactions default to **contemporaneous** (latest committed timestamp; may wait for in-flight transactions) or can be set **nonblocking** (older timestamp, no wait) ([MarkLogic docs](https://docs.marklogic.com/9.0/guide/app-dev/transactions)). Point-in-time queries against historical timestamps are supported.
- **Replication:** Intra-cluster **local-disk failover** keeps replica forests (synchronous journal-driven) for HA; **shared-disk failover** uses a clustered filesystem; **database replication** is asynchronous to a remote DR cluster; **flexible replication** is application-level. See [replication-models](../concepts/replication-models.md). Single-leader-per-forest semantics for writes; split-brain avoided via cluster quorum and a designated security/configuration database. ⚠️ unverified — quorum/fencing details not fully confirmed here.
- **Tunable consistency?** Limited: per-query timestamp/nonblocking choice and point-in-time reads, but not Dynamo-style per-write quorum levels.
- **Clock dependency:** Uses internal monotonic **system timestamps**, not wall-clock — no TrueTime/HLC dependency. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read** for documents (store any XML/JSON; structure indexed automatically). Optional **schema-on-write** validation via XSD/JSON Schema and **TDE** (Template Driven Extraction) to project documents into relational rows/views.
- **Migration/evolution:** No table to ALTER-lock; new document shapes coexist. Adding/removing **range indexes** triggers background reindexing (resource-heavy but online).
- **Type system:** XML, JSON, text, binary; RDF triples; range index types include string/number/date/dateTime; native **geospatial** indexing and search. As of **MarkLogic Server 12** (GA 2025-08-28), the engine natively stores and indexes **dense vector embeddings** with an [ANN vector](../concepts/vector-search-ann.md) index, enabling hybrid full-text + semantic search ([Progress — MarkLogic Server 12 GA](https://www.progress.com/blogs/introducing-marklogic-server-12--built-for-the-genai-era), [Vector Search feature](https://www.progress.com/marklogic/server/features/vector-search)).

## Query interface
- **Language:** **XQuery** and **server-side JavaScript** are the two native runtimes; **SPARQL** for triples; **SQL** via TDE relational views (read-oriented; not a general SQL OLTP surface); a search REST/Optic API and the **Optic API** for combined document/row/triple queries.
- **Transactions:** Full multi-statement, multi-document ACID within a cluster; **XA / two-phase commit** across databases/clusters ([MarkLogic docs](https://docs.marklogic.com/9.0/guide/app-dev/transactions)).
- **Native vs app-side:** Native full-text search, range/aggregate queries, geospatial, joins via Optic; document-level transforms and aggregation run server-side in XQuery/JS.
- **Stored procedures / UDFs:** Server-side modules in XQuery and JavaScript; aggregate UDFs in C++.

## Scaling & topology
- **Vertical and horizontal.** Scales out by adding hosts and **forests**; data is sharded across forests (manual placement or assignment policies). Resharding/rebalancing is online but operationally heavy.
- **E-node / D-node split:** Evaluator nodes (query execution) and Data nodes (forest storage) can be separated — a degree of [storage-compute-separation](../concepts/storage-compute-separation.md), though storage is local/clustered-FS, not object-store-native in the classic sense.
- **Read replicas:** Local-disk replica forests and DR-replica clusters; reads from async DR replicas are not guaranteed current.

## Performance & durability
- **Write path:** In-memory stand + on-disk **journal**; **strict journaling** fsyncs after each commit (required for shared-disk failover, slower) vs **fast journaling**. Data-loss window: with strict journaling, only an OS/host crash before the journal disk write loses the last commit; with relaxed settings the window widens. See [wal-and-durability](../concepts/wal-and-durability.md) ([MarkLogic docs](https://docs.marklogic.com/9.0/guide/concepts/backup-replication)).
- **Throughput/latency:** Strong for indexed search and document retrieval; write throughput bounded by journaling/fsync and merge pressure. ⚠️ unverified — no neutral published p99 benchmarks reviewed.
- **Compaction/GC:** Background **merges** compact stands and purge obsolete MVCC fragments; merges contend for CPU/IO and are the main p99/tail driver. If merges fall behind ingestion the 64-stand-per-forest cap can make a forest unavailable.

## Operations & maturity
- **Backup/restore:** Online backups, incremental backups, journal archiving, and point-in-time recovery; DR via database replication.
- **Observability:** Admin UI, Management/Monitoring REST APIs, query plans/profiling (`xdmp:plan`, `xdmp:query-trace`), Ops Director / monitoring dashboards.
- **Upgrade story:** Cluster upgrades generally require coordination; rolling upgrades supported in recent versions but typically planned with maintenance windows. Day-2 burden is real: forest/stand/merge tuning, index sizing, reindexing, and memory tuning demand specialist DBAs.
- **Maturity:** Mature (since mid-2000s), heavily used in publishing, finance, healthcare, intelligence/government. Known failure modes: merge/ingest imbalance, runaway reindexing, memory pressure from large range indexes. ⚠️ unverified — **no public Jepsen analysis exists**; ACID claims are vendor-asserted and not independently formally verified.

## Ecosystem & people
- **Canonical use cases:** Heterogeneous data integration ("operational data hub"), document/content management, semantic/knowledge-graph apps, regulatory and search-heavy systems needing transactions + search in one engine.
- **Anti-patterns:** High-volume simple KV or relational OLTP (overkill, costly); columnar analytics/BI warehousing; cost-sensitive or small teams; teams without XQuery/MarkLogic expertise.
- **Drivers/connectors:** Java/Node.js client APIs, REST, ODBC (for SQL/BI over TDE views), MLCP (content pump), Data Hub Framework, Kafka/CDC connectors. Smaller ecosystem and talent pool than mainstream OSS databases.
- **Community/support:** Commercial support from Progress; documentation is extensive but the learning curve (XQuery, forests/stands, index model) is steep.

## Licensing & cost
- **License:** Proprietary, closed source. A free **Developer license** unlocks full features for non-production; production needs a paid commercial ("Essential Enterprise" / Enterprise) license. Source-available only in the limited sense of the free dev edition — not open source. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Ownership:** Acquired by **Progress Software in February 2023 (~$355M)** ([Wikipedia](https://en.wikipedia.org/wiki/MarkLogic)).
- **Self-managed vs managed:** Self-managed on-prem/cloud, AWS/Azure marketplace AMIs, and a managed MarkLogic Cloud offering. Lock-in is significant: XQuery/JS server modules, TDE, and the index model are MarkLogic-specific.
- **Cost model:** Per-core / per-node enterprise licensing — expensive, and cost scales with cluster size; cheap-at-small does not apply (it is enterprise-priced from the start). ⚠️ unverified — exact list pricing is not public.

## Hardware / deployment
- **Resource profile:** Memory-hungry (range indexes, in-memory stands, list/expanded-tree caches) and IO-sensitive (journaling, merges); benefits from large RAM and fast local NVMe.
- **Storage assumptions:** Prefers fast local disk; shared-disk failover needs a clustered filesystem; tiered storage supports moving cold forests to cheaper/object storage.
- **Footprint:** Clustered server (E-nodes/D-nodes); not embedded, not serverless in the classic sense.
- **Deployment:** On-prem, cloud VMs, AWS/Azure marketplace, Kubernetes via the MarkLogic Operator/StatefulSets; managed MarkLogic Cloud.

## Bottom line
Reach for MarkLogic when you must integrate messy heterogeneous documents (XML/JSON) plus a knowledge graph and full-text search behind genuine multi-document ACID transactions — a combination few engines offer in one box, which is why publishing, government, and financial enterprises keep it. Avoid it for plain relational/KV OLTP, columnar analytics, or any cost- or talent-constrained team. The biggest gotchas: enterprise pricing and proprietary lock-in (XQuery + MarkLogic-specific index model), plus the operational discipline that forests/stands/merges demand — and note that its strong ACID claims are vendor-asserted with no public Jepsen verification.

## Sources
- [MarkLogic — Wikipedia](https://en.wikipedia.org/wiki/MarkLogic)
- [Understanding Transactions in MarkLogic Server (App Developer's Guide)](https://docs.marklogic.com/9.0/guide/app-dev/transactions)
- [High Availability and Disaster Recovery (Concepts Guide)](https://docs.marklogic.com/9.0/guide/concepts/backup-replication)
- [High Availability of Data Nodes With Failover](https://docs.marklogic.com/9.0/guide/cluster/failover)
- [How MarkLogic Supports ACID Transactions (Progress blog)](https://www.progress.com/blogs/how-marklogic-supports-acid-transactions)
- [MarkLogic Server features (Progress)](https://www.progress.com/marklogic/server/features)
