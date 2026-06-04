---
name: Amazon Neptune
slug: amazon-neptune
rank: 100
data_model: Graph (RDF + property graph)
license: Proprietary (managed-only AWS service)
summary: AWS's managed multi-model graph DB — property-graph (Gremlin/openCypher) and RDF (SPARQL) on shared Aurora-style 6-way storage; CP, snapshot-isolation reads.
last_researched: 2026-06-04
confidence: high
---

# Amazon Neptune

> AWS's fully managed, single-writer graph database that speaks both property-graph (Gremlin, openCypher) and RDF (SPARQL) over the same Aurora-style distributed storage — convenient, locked-in, and not horizontally scalable for writes.

## When to use

**Use Amazon Neptune if:**
- ✅ You're on AWS and want a zero-ops graph database for read-heavy OLTP traversal — fraud detection, identity/entity resolution, recommendation and knowledge graphs, network topology
- ✅ Your write workload fits within a single writer instance and you want Aurora-style durability (6-way / 3-AZ storage, snapshot-isolation reads)
- ✅ You want optionality between property-graph (Gremlin/openCypher) and RDF (SPARQL) without standing up your own engine

**Avoid Amazon Neptune if:**
- ❌ You need horizontal write scaling or multi-region active-active writes — all writes go through one instance with no write sharding (the single biggest gotcha)
- ❌ You need read-your-writes off replicas (replica reads are eventually consistent; you must hit the writer endpoint) or one engine spanning both PG and RDF in a single query
- ❌ You want portability off AWS or an open, self-hostable graph DB (prefer [neo4j](neo4j.md)/[arangodb](arangodb.md), or [graphdb](graphdb.md)/[virtuoso](virtuoso.md) for RDF)

## Identity
- **Taxonomy / data model:** [graph-data-model](../concepts/graph-data-model.md) — multi-model. Two distinct models that do *not* interoperate within one cluster: **property graph** (queryable with Apache TinkerPop **Gremlin** and **openCypher**) and **RDF** (queryable with **SPARQL**). You pick the model per dataset; you cannot query RDF triples with Gremlin or vice-versa.
- **Storage model:** purpose-built graph storage on a shared, log-structured cluster volume modeled on the Aurora architecture (separate storage tier replicated 6 ways across 3 AZs) ([What Is Amazon Neptune?](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)). Not a row/column SQL engine; quad/triple-oriented internally. Uses a [storage-compute-separation](../concepts/storage-compute-separation.md) design.
- **Workload:** OLTP graph workloads — "designed to support highly concurrent online transactional processing (OLTP) workloads over data graphs" ([Transaction Semantics](https://docs.aws.amazon.com/neptune/latest/userguide/transactions.html)). For analytic/whole-graph algorithms and vector search, AWS sells a *separate* engine, **Neptune Analytics** (in-memory, m-NCU billed) — so this is not HTAP in one engine; the two workloads are physically separate products. See [oltp-olap-htap](../concepts/oltp-olap-htap.md).

## Distribution & consistency
- **CAP under partition:** **CP**. Single writer instance; on partition/failure it fails over rather than accepting divergent writes. See [cap-pacelc](../concepts/cap-pacelc.md).
- **PACELC:** under partition favors consistency (PC); else (E) it trades latency for consistency by routing strongly-consistent reads to the writer and offering only eventually-consistent reads from replicas.
- **Default isolation & what's achievable:** read-only queries run under **snapshot isolation** via [mvcc](../concepts/mvcc.md) — no dirty reads, no non-repeatable reads, no phantoms, and read queries take no locks. Mutation queries' reads run under **READ COMMITTED**, but Neptune goes beyond it: by taking record/range locks while reading it also rules out non-repeatable and phantom reads for mutations ([Transaction Isolation Levels in Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/transactions-neptune.html)). AWS markets Neptune as "ACID compliant with immediate consistency on the primary writer instance, and eventual consistency on the read replica instances" ([FAQs](https://aws.amazon.com/neptune/faqs/)) — in practice this is snapshot-isolation reads + lock-based READ COMMITTED mutations, not globally serializable across replicas. See [isolation-levels](../concepts/isolation-levels.md).
- **Replication:** single-leader. One writer + up to 15 read replicas sharing the same underlying storage volume (replicas do not re-do writes, which keeps replica lag low) ([intro](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)). Failover promotes a replica automatically. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** Reads from the writer are strongly consistent; reads from replicas are **eventually consistent** with replication lag exposed as a CloudWatch metric. No Dynamo-style per-query quorum tuning.
- **Clock dependency:** ⚠️ unverified — no published reliance on synchronized physical clocks (TrueTime/HLC) for correctness; consistency derives from the single-writer + shared-log design, not clocks. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema model:** **schema-on-read / schemaless** at the data layer. Property graph imposes no predefined vertex/edge schema; RDF is open-world by nature. Constraints and shape live in the application.
- **Migration/evolution:** no rigid DDL to alter; new labels/properties/predicates can be added by simply writing them. Engine-version upgrades, however, can require maintenance windows.
- **Type system:** property values are typed (string, numeric, date, boolean); RDF carries XSD-typed literals and IRIs. No native columnar vectors in Neptune Database — **vector search lives in the separate Neptune Analytics engine**, not the OLTP DB. Geospatial is limited (no rich native spatial indexing comparable to PostGIS).

## Query interface
- **Languages:** **Gremlin** (TinkerPop traversal), **openCypher** (Neo4j-style), and **SPARQL 1.1** — accessed over HTTP/WebSocket endpoints. Property-graph data is reachable via both Gremlin and openCypher; RDF only via SPARQL ([SPARQL access](https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-sparql.html)).
- **Transactions:** ACID transactions with defined semantics; Gremlin and SPARQL specs themselves do not define concurrency semantics, so Neptune layers its own ([Transaction Semantics](https://docs.aws.amazon.com/neptune/latest/userguide/transactions.html)). Conflicting concurrent mutations are resolved with **lock-based concurrency control**: range/gap locks plus a lock-wait timeout (up to 60s) that rolls back the blocked transaction, and immediate rollback on detected deadlocks ([Transaction Isolation Levels in Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/transactions-neptune.html)). Note: gap locks can produce **false conflicts** — under high load roughly 3-4% of write queries can fail this way — so clients must implement retries.
- **Native vs app-side:** joins/traversals, pattern matching, and aggregations are native to the query languages. No SQL, no general window functions; cross-model joins (PG↔RDF) are not supported.
- **Stored procedures / UDFs:** ⚠️ unverified — no general server-side stored-procedure language; logic lives client-side. Integrations (e.g. SageMaker for Neptune ML) are external rather than in-DB UDFs.

## Scaling & topology
- **Vertical vs horizontal:** primarily **vertical** for writes — a single writer instance; you scale write capacity by resizing the instance (or via Serverless NCU autoscaling), not by sharding. Reads scale **horizontally** via up to 15 replicas. No automatic write sharding/partitioning across nodes — this is the key ceiling.
- **Sharding/resharding:** none in the user-facing sense; the storage tier auto-grows in 10 GB segments up to a max cluster volume of **128 TiB** (64 TiB in China/GovCloud regions), transparent to the user ([Neptune storage](https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage.html)). No manual resharding, but also no way to split the write workload across nodes.
- **Read replicas & consistency:** replicas serve eventually-consistent reads with low lag (shared storage). Use the writer endpoint for read-your-writes.
- **Storage/compute separation:** yes — Aurora-style separation; storage replicated 6×/3 AZ independent of compute instances. Cross-region via **Neptune Global Database** (async replication, secondary region promotable for DR). See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** writes go through the distributed log-structured storage; the cluster volume is replicated as **6 copies of each 10 GB segment across 3 AZs**, so a write is durable once acknowledged by a write quorum of storage nodes — the design tolerates loss of 2 copies without affecting write availability and 3 without affecting read availability ([Neptune storage](https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage.html)). **Data-loss window on crash is effectively near-zero** for committed writes given quorum durability; uncommitted in-flight work is lost. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** in-memory-optimized, scale-up query evaluation; AWS claims hundreds of thousands of reads/sec across replicas. Write throughput is bounded by the single writer. ⚠️ unverified — no public independent p99 tail benchmarks; performance is highly sensitive to whether the working set fits in instance RAM (cold/spilled traversals degrade sharply).
- **Compaction/GC:** MVCC versions are reclaimed internally; the managed storage layer handles compaction. ⚠️ unverified — AWS does not publish vacuum/compaction tuning knobs, as it is fully managed.

## Operations & maturity
- **Backup/restore, PITR, snapshotting:** continuous backups to S3 with **point-in-time restore** within the retention window, plus manual snapshots; backup storage up to 100% of cluster storage is free ([pricing](https://aws.amazon.com/neptune/pricing/)).
- **Observability:** CloudWatch metrics (including replication lag), audit logs, slow-query/`explain` facilities per query language. No deep on-host access (managed service).
- **Upgrade story:** AWS-managed engine version upgrades; minor upgrades can be near-online but major versions may require a maintenance window / brief downtime. Day-2 burden is low (no patching, backups automated) at the cost of zero control.
- **Maturity:** GA since 2018, mature within the AWS ecosystem and used in production for fraud, identity, knowledge-graph workloads. **No public Jepsen report exists** for Neptune (confirmed absent from [jepsen.io/analyses](https://jepsen.io/analyses) as of 2026-06). Known limitations: single-writer write ceiling, eventual-consistency surprises on replicas, and the PG/RDF model split.

## Ecosystem & people
- **Canonical use cases:** fraud detection, identity/entity resolution, recommendation graphs, knowledge graphs, network/IT topology, and RDF/linked-data applications. With **Neptune ML** (GNN inference via SageMaker) for graph predictions and **Neptune Analytics** for algorithms + [vector-search-ann](../concepts/vector-search-ann.md) backing GenAI/GraphRAG.
- **Anti-patterns:** write-heavy workloads that exceed a single writer; multi-region active-active writes; teams wanting to avoid AWS lock-in; workloads needing one engine to span both property-graph and RDF; sub-millisecond ultra-high-write OLTP. If you need an open, self-hostable graph DB use [neo4j](neo4j.md) or [arangodb](arangodb.md); for RDF specifically, [graphdb](graphdb.md) / [virtuoso](virtuoso.md).
- **Drivers/connectors:** standard TinkerPop, openCypher, and SPARQL clients; AWS bulk-loader from S3, CDC via Neptune Streams, integration with Glue, SageMaker, Lambda, and BI through query endpoints. No native dbt graph support.
- **Community/support:** no independent OSS community (proprietary); support is via AWS. Docs are solid AWS-quality. Learning curve dominated by choosing/learning Gremlin vs openCypher vs SPARQL and Neptune's transaction/consistency model.

## Licensing & cost
- **License:** **proprietary, managed-only** AWS service — not open source, not self-hostable. No relicensing drama because it was never OSS. See [license-taxonomy](../concepts/license-taxonomy.md).
- **Self-managed vs managed:** managed-only. Strong lock-in: data lives in AWS; while query languages (Gremlin/openCypher/SPARQL) are portable standards, the operational stack, Streams, Global Database, ML, and Analytics are AWS-specific.
- **Cost model:** provisioned **per-instance-hour** + storage **per GB-month** (~$0.10) + **I/O per million requests** (~$0.20), with free backup up to 100% of storage; or **Serverless** billed **per Neptune Capacity Unit (NCU, ~2 GB RAM)** per second, autoscaling 1–128 NCUs at roughly $0.1098/NCU-hour ([Serverless](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless.html), [pricing](https://aws.amazon.com/neptune/pricing/)). Neptune Analytics bills separate **memory-optimized NCUs (m-NCUs)**. I/O-based billing can surprise on traversal-heavy workloads; large in-memory instances get expensive fast.

## Hardware / deployment
- **Resource profile:** **memory-bound** — in-memory-optimized query evaluation; performance falls off when the working graph does not fit in instance RAM. Replicas add CPU/RAM for read fan-out.
- **Storage assumptions:** abstracted away — the managed Aurora-style storage tier (network-attached, multi-AZ) handles durability; users do not provision disks.
- **Footprint:** clustered managed service (1 writer + ≤15 replicas) or serverless; **not embeddable**, not on-prem.
- **Deployment:** SaaS-only within AWS VPC. No k8s/StatefulSet self-hosting; integrates with AWS networking/IAM.

## Bottom line
Reach for Neptune if you're already on AWS, want a zero-ops graph database, and your workload is read-heavy OLTP graph traversal that fits within a single writer — especially if you want optionality between property-graph and RDF. Do **not** choose it if you need horizontal write scaling, multi-region active-active writes, portability off AWS, or one engine spanning both graph models. The single biggest gotcha: **all writes go through one instance and there is no write sharding** — plus replica reads are eventually consistent, so read-your-writes requires hitting the writer endpoint.

## Sources
- [What Is Amazon Neptune? (official docs)](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)
- [Transaction Semantics in Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/transactions.html)
- [Transaction Isolation Levels in Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/transactions-neptune.html)
- [Definition of Isolation Levels](https://docs.aws.amazon.com/neptune/latest/userguide/transactions-isolation-levels.html)
- [Amazon Neptune FAQs](https://aws.amazon.com/neptune/faqs/)
- [Accessing the graph with SPARQL](https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-sparql.html)
- [Amazon Neptune Serverless](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless.html)
- [Amazon Neptune Pricing](https://aws.amazon.com/neptune/pricing/)
