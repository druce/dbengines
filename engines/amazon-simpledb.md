---
name: Amazon SimpleDB
slug: amazon-simpledb
rank: 147
data_model: Key-value (also: document / wide-column-ish, schemaless attribute store)
license: Proprietary, managed-only (AWS service)
summary: AWS's original (2007) schemaless, auto-indexed attribute store; effectively frozen since DynamoDB, closed to new customers July 2024.
last_researched: 2026-06-04
confidence: high
---

# Amazon SimpleDB

> A pre-DynamoDB AWS NoSQL store where every attribute is auto-indexed and everything is a string — historically interesting, long superseded, and closed to new customers since July 2024.

## When to use

**Use Amazon SimpleDB if:**
- ✅ You're a legacy user with an existing domain that works — there is essentially no reason to newly adopt it
- ✅ You needed a tiny schemaless attribute store where auto-indexing every attribute avoided index design (historical metadata/index store alongside S3)
- ✅ Your data and queries fit the hard caps (10 GB / 1 billion attributes per domain) and you want per-read tunable consistency plus conditional-write CAS

**Avoid Amazon SimpleDB if:**
- ❌ It's any new project — it's closed to new customers (since July 2024), feature-frozen 10+ years; use [amazon-dynamodb](amazon-dynamodb.md) or [amazon-aurora](amazon-aurora.md)/RDS instead
- ❌ You have numeric/date-heavy data — everything is stored as UTF-8 strings, so sorting and ranges silently break unless the app zero-pads and ISO-encodes every value (the single biggest gotcha)
- ❌ You need joins, aggregations beyond `count(*)`, multi-item transactions, large/analytical workloads, or high write throughput

## Identity
- **Taxonomy / data model:** schemaless attribute-value store. Hierarchy is *domain → item → (attribute, value) pairs*; an item can have up to 256 name/value pairs and attributes may be **multi-valued** ([attribute name-value pairs per item = 256](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html)). Sits between key-value and document. There is no native schema — attributes appear per-item.
- **Storage model:** managed, opaque. Every attribute is **automatically indexed** — there is no concept of a primary-vs-secondary index, and **all values are stored and compared as UTF-8 strings**, so numbers/dates must be zero-padded and ISO-formatted by the application to sort/range correctly. On-disk format and engine internals are undocumented AWS internals.
- **Workload:** small-scale OLTP-ish lookups and simple filtered queries. Not OLAP, not HTAP. See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Hard ceilings make it unsuitable for large or analytical workloads ([10 GB / 1 billion attributes per domain](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html)).

## Distribution & consistency
- **CAP under partition:** AP-leaning by design — historically read/write availability was favored and reads were eventually consistent. See [cap-pacelc](../concepts/cap-pacelc.md). AWS does not publish a formal CAP/PACELC characterization; ⚠️ unverified — precise partition-time write behavior (whether writes are refused during a partition) is not documented.
- **PACELC:** ⚠️ unverified — no official PACELC statement. In practice it behaves PA/EL (favors availability and low latency, exposing eventual consistency) unless you opt into consistent reads, in which case latency rises.
- **Default isolation & what's achievable:** no transactions and no isolation levels in the SQL sense. Atomicity is per-operation only (a `PutAttributes`/`DeleteAttributes` on one item). There is **no multi-item or multi-statement transaction**. "Optimistic concurrency" is achievable via **conditional put/delete**: an operation applies only if a named single-valued attribute equals an expected value, letting apps build version-number CAS loops ([conditional puts/deletes, 2010](https://aws.amazon.com/blogs/aws/amazon-simpledb-consistency-enhancements/)). Compare [isolation-levels](../concepts/isolation-levels.md), [mvcc](../concepts/mvcc.md).
- **Replication:** SimpleDB keeps **multiple copies of each domain** across an AWS Region; a successful write durably persists to all copies ([Consistency docs](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/ConsistencySummary.html)). Replication topology is internal and not exposed. See [replication-models](../concepts/replication-models.md).
- **Tunable consistency:** yes, per-read. Reads are **eventually consistent by default** (typically converge within ~1 second); pass `ConsistentRead=true` on `GetAttributes`/`Select` to read all writes acknowledged before the read, at higher latency / lower throughput ([Consistency docs](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/ConsistencySummary.html), [consistency enhancements, Feb 2010](https://aws.amazon.com/blogs/aws/amazon-simpledb-consistency-enhancements/)).
- **Clock dependency:** none exposed to users; no TrueTime/HLC-style API. See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-read.** Fully schemaless: no `CREATE TABLE`-style column definitions; attributes are created implicitly on write and differ per item. The "schema" lives in application code.
- **Migration/evolution:** trivial in the sense that adding/removing attributes is just writing different data — no DDL, no `ALTER`, no online-migration concept. Conversely there is no enforcement, defaults, or constraints.
- **Type system:** **everything is a UTF-8 string.** No native numeric, boolean, date, JSON, geospatial, or vector types. Numeric ordering and ranges require app-side zero-padding/offset encoding. Multi-valued attributes are supported natively.

## Query interface
- **Language:** an API plus a **SQL-like `Select` expression** (`SELECT ... FROM domain WHERE ... ORDER BY ... LIMIT ...`) over a single domain. Core API: `CreateDomain`, `DeleteDomain`, `PutAttributes`, `BatchPutAttributes`, `GetAttributes`, `DeleteAttributes`, `BatchDeleteAttributes`, `Select`, `DomainMetadata`. No JDBC/ODBC; accessed via AWS SDK / HTTP query API.
- **Transactions:** none across items; single-item atomic writes plus conditional (CAS) writes only.
- **Native vs app-side:** **no joins** (queries cannot span domains), no aggregations beyond `count(*)`, no window functions, no foreign keys. All attributes are auto-indexed so equality/range/`LIKE` filters work without index management, but you give up control over index cost.
- **Stored procedures / UDFs:** none.

## Scaling & topology
- **Vertical vs horizontal:** scaling is **manual, app-driven sharding across domains** (250 domains/account by default, raisable). Each domain caps at [10 GB and 1 billion attributes](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html). There is no auto-sharding within or across domains — partitioning logic is entirely the application's responsibility, and resharding means rewriting data.
- **Read replicas / read consistency:** replication is internal; you don't manage replicas. Read consistency is chosen per request (see above), not per replica.
- **Storage/compute separation:** N/A as a user-facing concept — fully managed, opaque service. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** managed; a successful write is acknowledged only after durable persistence to all domain copies ([Consistency docs](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/ConsistencySummary.html)). fsync/group-commit internals are not exposed; data-loss window on a fully-acked write is effectively zero per AWS's durability claim. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** designed for low-latency small requests, not high throughput. Hard query limits dominate the profile: **`Select` execution capped at 5 seconds, max 2500 items and 1 MB per response, ≤20 unique attributes and ≤20 comparisons per expression** ([Limits](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html)). Large scans must be paginated with `NextToken`. ⚠️ unverified — AWS publishes no official p99 latency figures.
- **Compaction / vacuum / GC:** none user-visible; fully managed and abstracted.

## Operations & maturity
- **Backup/restore, PITR:** no native snapshot/PITR. Late additions include domain **export** (rate-limited: [5 exports per domain and 25 per account in a rolling 24h window](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html)). Practical backup historically meant scripting `Select` dumps. No IAM-grade fine control comparable to modern services.
- **Observability:** minimal. `DomainMetadata` gives item/attribute counts and sizes; standard CloudWatch coverage is thin; no query plans or slow-query logs.
- **Upgrade story:** none for the user — fully managed, no versions to manage. Day-2 burden is mostly working *around* the limits and string-only typing.
- **Maturity:** launched 2007 (beta), GA 2009; one of AWS's oldest services. **No new features for over a decade** — superseded by [amazon-dynamodb](amazon-dynamodb.md). **Closed to new customers effective July 25, 2024**; existing customers retain access and AWS says it continues security/availability/performance maintenance but adds no features ([AWS service closures, 2024](https://awsinsider.net/articles/2024/08/01/aws-closes-door-to-some-services.aspx), [devclass](https://devclass.com/2024/07/31/aws-quietly-freezes-codecommit-now-closed-to-new-customers-also-breaking-its-control-tower-templates/)). No public Jepsen report exists.

## Ecosystem & people
- **Canonical use cases (historical):** metadata/index storage alongside amazon-s3, small flexible-schema catalogs, simple per-item lookups where auto-indexing avoided index design. **Anti-patterns:** anything large (>10 GB/domain), analytical/aggregating queries, joins, high write throughput, strongly-typed/numeric-heavy data, or any *new* project — DynamoDB or Aurora/RDS are the modern choices.
- **Drivers/connectors:** available in legacy AWS SDKs (Java/Python/etc.) and the HTTP query API. Little to no modern CDC/Kafka/dbt/BI integration; effectively absent from current data tooling.
- **Community/support:** essentially dormant. Docs remain online but the community has long migrated. Learning curve is small but the knowledge is increasingly stranded.

## Licensing & cost
- **License:** proprietary, **managed-only AWS service** — no self-hosting, no OSS edition. Not a license-taxonomy case (see [license-taxonomy](../concepts/license-taxonomy.md)); the relevant lock-in is the AWS-proprietary API.
- **Lock-in:** high — the data model and `Select` dialect are AWS-specific; migration means an app rewrite (typically to DynamoDB).
- **Cost model:** usage-based — machine-hours of box utilization, data transfer, and structured-data storage per GB-month, with a historical free tier. ⚠️ unverified — current pricing is largely irrelevant since the service is closed to new customers and rarely chosen.

## Hardware / deployment
- **Resource profile:** N/A to the user — fully managed; AWS owns the hardware. No working-set/RAM tuning is exposed.
- **Storage assumptions:** opaque managed storage; not user-configurable.
- **Footprint:** cloud-only, regional managed service. Not embeddable, not self-hostable, not containerizable.
- **Deployment:** SaaS only, single AWS partition/Region per domain; no on-prem or k8s story.

## Bottom line
SimpleDB is a historical artifact: AWS's first NoSQL store, notable for auto-indexing every attribute, string-only values, per-read tunable consistency, and conditional-write CAS. **Reach for it: essentially never** — it is closed to new customers (since July 2024), feature-frozen for 10+ years, and capped at 10 GB per domain. Anyone evaluating it today should use [amazon-dynamodb](amazon-dynamodb.md) (key-value/document at scale) or [amazon-aurora](amazon-aurora.md)/RDS (relational) instead. The biggest gotcha for the few legacy users: **all data is stored as strings**, so numeric and date sorting/ranges silently break unless the app zero-pads and ISO-encodes every value.

## Sources
- [Amazon SimpleDB — Consistency](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/ConsistencySummary.html)
- [Amazon SimpleDB — Limits](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/SDBLimits.html)
- [Amazon SimpleDB Consistency Enhancements (consistent reads + conditional put/delete), AWS Blog, Feb 2010](https://aws.amazon.com/blogs/aws/amazon-simpledb-consistency-enhancements/)
- [Performing a Conditional Put — SimpleDB docs](https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/ConditionalPut.html)
- [Amazon SimpleDB FAQs](https://aws.amazon.com/simpledb/faqs/)
- [AWS Closes Door to Some Services, Including SimpleDB (AWSInsider, Aug 2024)](https://awsinsider.net/articles/2024/08/01/aws-closes-door-to-some-services.aspx)
- [AWS quietly freezes CodeCommit, SimpleDB and more (devclass, Jul 2024)](https://devclass.com/2024/07/31/aws-quietly-freezes-codecommit-now-closed-to-new-customers-also-breaking-its-control-tower-templates/)
- [Amazon SimpleDB — Wikipedia](https://en.wikipedia.org/wiki/Amazon_SimpleDB)
