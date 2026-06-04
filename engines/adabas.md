---
name: Adabas
slug: adabas
rank: 98
data_model: Multivalue (mainframe; inverted-list / "Adaptable DAta BASe")
license: Proprietary commercial (Software AG)
summary: 1970s-era high-performance mainframe DBMS with multivalued/periodic-group records and inverted-list indexing; still runs core systems at banks, insurers, and governments, but is firmly legacy.
last_researched: 2026-06-04
confidence: high
---

# Adabas

> A 50-year-old proprietary mainframe DBMS built on inverted lists and multivalued records, tightly paired with the Natural language — extremely fast and durable for the workloads it was designed for, but a closed, legacy ecosystem most teams are trying to migrate off, not onto.

## Identity
- **Taxonomy / data model:** Non-relational. Best classified as a **multivalue / inverted-list** DBMS ("Adaptable DAta BASe"). Records live in files; fields can be elementary, **multiple-value (MU)** fields, or **periodic groups (PE)** that repeat — i.e. arrays and nested repeating structures inside a single record, which collapses many-to-one relationships that an RDBMS would normalize into separate tables. ([Wikipedia: ADABAS](https://en.wikipedia.org/wiki/ADABAS), [Software AG: field types / format buffers](https://documentation.softwareag.com/adabas/ada854mfr/comref/fmtbuf.htm))
- **Storage model:** Row/record store with a separate **inverted-list index** (the "Associator"): descriptors (indexed fields) are organized by value, comprising a normal index (NI) plus upper indexes (UI). Each record has an internal sequence number (**ISN**). Physical layout = Associator (indexes/metadata) + Data Storage. Not [lsm-vs-btree](../concepts/lsm-vs-btree.md)-style; it is a bespoke inverted-list + ISN-address scheme predating both. ([Software AG: Adabas Design](https://documentation.softwareag.com/adabas/ada744mfr/adamf/concepts/cfdesign.htm))
- **Workload:** OLTP — designed for very high-throughput transactional record access on the mainframe. Not an analytics engine; SQL/BI access is bolted on via the separate SQL Gateway (see below). See [oltp-olap-htap](../concepts/oltp-olap-htap.md). Not HTAP.

## Distribution & consistency
- **CAP under partition:** Largely **N/A — single shared database** served by one or more nuclei on a mainframe; Adabas Cluster Services / Parallel Services provide scale-out *within* a sysplex/single image against **one physical database**, not a partition-tolerant distributed system. The model is shared-data clustering, not quorum replication, so classic [cap-pacelc](../concepts/cap-pacelc.md) framing fits poorly; treat as a CP-style single-authority system. ([Software AG: Adabas Parallel Services](https://documentation.softwareag.com/adabas/asm831/intro/asmcintr.htm), [Cluster Services](https://documentation.softwareag.com/adabas/als841/introduction/others.htm))
- **PACELC:** Not meaningfully applicable to the single-database deployment; it is a tightly-coupled mainframe system, not a latency-vs-consistency tunable cluster. See [cap-pacelc](../concepts/cap-pacelc.md).
- **Default isolation & what's achievable:** Transactions are user-defined logical units bounded by **OP/ET/BT** commands; records placed in **hold status** are locked for update, giving record-level locking and serialized update access. ⚠️ unverified — Adabas predates the ANSI SQL isolation vocabulary and does not advertise a standard isolation level; behavior is closest to record-level locking with read access to committed data rather than a named [isolation-levels](../concepts/isolation-levels.md) tier. Treat any "ACID" claim as: atomic transactions + record locking + crash recovery, *not* SQL serializable semantics. ([Software AG: Using Adabas — transactions](https://documentation.softwareag.com/adabas/ada744mfr/adamf/concepts/cfusing.htm))
- **Replication:** **Event Replicator for Adabas** pushes selected data **asynchronously** to other Adabas databases, third-party RDBMSs, or messaging systems by predefined rules — a CDC/feed mechanism, not synchronous multi-master. ([Software AG: Event Replicator](https://www.softwareag.com/en_corporate/resources/adabas-natural/ds/event-replicator.html)) See [replication-models](../concepts/replication-models.md).
- **Tunable consistency?** No Dynamo-style per-query consistency levels.
- **Clock dependency:** No dependence on synchronized clocks for correctness (single-authority nucleus). See [clocks-and-time](../concepts/clocks-and-time.md).

## Schema
- **Schema-on-write.** Each file has a **Field Definition Table (FDT)** defining fields, MU/PE structures, and descriptors. Records must conform; it is not schemaless.
- **Migration/evolution:** Field definitions are relatively rigid; structural changes (new fields, changing MU/PE, re-indexing descriptors) typically require utility runs (e.g. unload/reload, ADADBS-type operations) rather than online `ALTER`. ⚠️ unverified — extent of fully-online schema change in current versions; historically schema evolution on Adabas is an offline/utility operation, a frequent migration pain point.
- **Type system:** Alphanumeric, numeric (packed/unpacked/binary/fixed/floating), with MU (repeating values — default cap of **191 occurrences** per MU field/PE group, raisable to ~65,534 via the ADADBS MUPEX / ADACMP MUPEX function, subject to the compressed record fitting in a Data Storage block) ([Software AG: MUPEX](https://documentation.softwareag.com/adabas/azp843/util/adadbs-MUPEX.htm)) and PE (repeating groups). No native JSON/geospatial/vector types; these are foreign to its 1970s design. ([Software AG: field types](https://infocenter.informationbuilders.com/wf8005/topic/pubdocs/Adapter_Admin/source/topic22.htm))

## Query interface
- **Language:** Primary access is the **Adabas direct call (ADBS) API** — a command-code interface (L-codes for reads, A/N/E for add/update/delete, S for search) with control block + format/record/search buffers, callable from COBOL, PL/I, Assembler, etc. In practice most applications are written in Software AG's **natural** 4GL, which sits on top of Adabas. SQL is *not* native — **Adabas SQL Gateway** provides an ODBC/JDBC SQL layer over Adabas for BI tools (Cognos, Crystal Reports, Excel, etc.). ([Software AG: accessing Adabas](https://documentation.softwareag.com/natural/nat827mf/pg/pg_dbms_ada.htm), [SQL Gateway](https://www.softwareag.com/en/resources/adabas-natural/adabas-sql-gateway/))
- **Transactions:** Full multi-command transactions via ET (commit) / BT (back out), including a **subtransaction** concept via ET/BT options. ([Software AG: Using Adabas](https://documentation.softwareag.com/adabas/ada744mfr/adamf/concepts/cfusing.htm))
- **Native vs app-side:** Inverted-list descriptors give fast indexed search and **super-descriptors** (composite indexes). There are no SQL joins natively — relationships are either modeled inside records (MU/PE) or resolved in application code (Natural). Aggregations/window functions are app-side or via the SQL Gateway.
- **Stored procedures / UDFs:** No SQL stored procedures in the RDBMS sense; business logic lives in Natural programs (and Adabas user exits / triggers via Natural).

## Scaling & topology
- **Vertical vs horizontal:** Primarily **vertical** (scale up the mainframe). Horizontal scaling is **within** a single logical database via **Adabas Parallel Services** (up to ~31 nuclei across engines on one OS image) and **Adabas Cluster Services** (multiple nuclei across a z/OS Parallel Sysplex), all hitting **one physical database**. ([Parallel Services](https://documentation.softwareag.com/adabas/asm831/intro/asmcintr.htm))
- **Sharding:** No automatic application-transparent sharding across independent nodes; data is partitioned manually across files/components if at all. Resharding is a manual reorganization exercise.
- **Read replicas:** No native read-replica fan-out for query offload; the Event Replicator can feed downstream copies asynchronously (eventually consistent).
- **Storage/compute separation:** No — classic coupled storage+compute on mainframe DASD. See [storage-compute-separation](../concepts/storage-compute-separation.md).

## Performance & durability
- **Write path:** Durability via **protection logs (PLOG)** and command/recovery logging plus checkpoints; the nucleus buffers Associator/Data blocks in a buffer pool and writes are protected so committed (ET'd) transactions survive crashes. On restart, **auto-backout** rolls back any in-flight (uncommitted) transactions to leave the DB consistent. ([Software AG: Restart and Recovery](https://documentation.softwareag.com/adabas/ada823mfr/adamf/operator/recovery.htm)) Data-loss window: committed transactions are protected; uncommitted work at crash is discarded. See [wal-and-durability](../concepts/wal-and-durability.md).
- **Throughput/latency:** Historically prized for very high transaction rates and low, predictable latency on mainframe hardware — the inverted-list + ISN direct-address design minimizes I/O. ⚠️ unverified — no public independent p99 benchmarks; performance claims come from the vendor and long production track record rather than neutral tests.
- **Compaction / GC:** Periodic **reorganization** (ADAORD/ADADBS utilities) reclaims space and rebuilds Associator/Data extents; not a continuous background compaction model. Index/space fragmentation is managed via scheduled utility runs, an operator burden rather than an automatic process.

## Operations & maturity
- **Backup/restore, PITR:** Mature utility suite — ADASAV (save/restore), protection logs enabling **forward recovery / regenerate** and roll-back to a point in time via REGENERATE/BACKOUT against PLOGs. ([Restart and Recovery](https://documentation.softwareag.com/adabas/ada823mfr/adamf/operator/recovery.htm))
- **Observability:** **Adabas Review** monitors command/transaction activity and performance; standard mainframe SMF/operator interfaces apply. No SQL `EXPLAIN`; tuning is via descriptor design and buffer-pool/ADARUN parameters. ([ADARUN parameters](https://documentation.softwareag.com/adabas/wcp651mfr/ref/adarun.htm))
- **Upgrade story:** Version upgrades are planned mainframe change events (often with utility conversion of files), not rolling cloud-style upgrades. Day-2 burden is high and **skills-bound** — it requires scarce Adabas/Natural mainframe DBAs.
- **Maturity:** Extremely mature (first released ~1970–71) with decades of production use in banks, insurers, and government. **No Jepsen report exists** (it is not a modern distributed DB and predates that testing tradition). Known issue is not correctness but **obsolescence risk**: dwindling expertise and migration cost. ([Wikipedia: ADABAS](https://en.wikipedia.org/wiki/ADABAS))

## Ecosystem & people
- **Canonical use cases:** Long-lived high-volume mainframe OLTP systems — core banking, insurance policy/claims, government records (e.g. tax, social services) — typically written in natural. **Anti-patterns:** any greenfield system; cloud-native or microservice architectures; analytics/ad-hoc SQL workloads; teams without mainframe/Adabas skills. For new builds reach for [postgresql](postgresql.md), [oracle](oracle.md), or a purpose-fit modern engine, not Adabas.
- **Drivers / connectors:** Adabas SQL Gateway (ODBC/JDBC), Event Replicator (CDC to RDBMS/Kafka-style messaging), and adapters from BI/integration vendors. A large modernization industry exists to **migrate off** Adabas/Natural (AWS, Azure rehost guidance; IBM ModernSystems and third-party converters). ([Azure rehost guidance](https://learn.microsoft.com/en-us/azure/architecture/example-scenario/mainframe/rehost-adabas-software-ag), [AWS modernization](https://aws.amazon.com/blogs/apn/modernize-natural-and-adabas-workloads-on-aws-with-ibm-modernsystems-accelerator/))
- **Community / support:** Commercial support from the vendor; small, aging, specialized community. Docs are thorough (vendor documentation site) but the learning curve is steep and the talent pool is shrinking.

## Licensing & cost
- **License:** **Proprietary, closed-source commercial**, developed and sold by **Software AG** (db-engines lists Software AG as the developer). Software AG was taken private by **Silver Lake** (2023) and subsequently broke itself up — selling webMethods/StreamSets to IBM and other lines off — but **Adabas & Natural was *retained* and spun out as one of two standalone businesses within Software GmbH/Software AG (alongside ARIS), not sold to a third party**. ([Software AG: Adabas & Natural and ARIS launch as standalone](https://www.softwareag.com/en/blog/insights/adabas-natural-and-aris-launch-as-standalone/), [diginomica: Software AG retrenches to ARIS and A&N](https://diginomica.com/software-ag-retrenches-aris-adabas-natural)) (An earlier draft of this page claimed the line was sold to Rocket Software — that is incorrect as of 2025; Adabas & Natural remains under Software AG/Silver Lake.) Not [license-taxonomy](../concepts/license-taxonomy.md) OSS at all — no permissive/copyleft/source-available option.
- **Self-managed vs managed:** Self-managed on customer mainframe/LUW; no first-party serverless/SaaS offering. Heavy lock-in via the proprietary data model and the Natural application stack — the single biggest reason migrations are expensive.
- **Cost model:** Traditional enterprise mainframe licensing (per-MIPS/MSU / per-engine plus annual maintenance), with add-ons (Cluster Services, Parallel Services, Event Replicator, SQL Gateway, Review) priced separately. Costs scale with mainframe capacity and are a common driver of modernization business cases. ⚠️ unverified — current list pricing not public.

## Hardware / deployment
- **Resource profile:** Tuned for mainframe — benefits from large buffer pools (memory) to cache Associator/Data blocks; otherwise disk-I/O-bound against DASD. Working set need not fit entirely in RAM, but buffer-pool sizing dominates performance.
- **Storage assumptions:** Mainframe DASD (and LUW disk for the Linux/Unix/Windows port); designed around block I/O, not modern NVMe-specific optimizations.
- **Footprint:** Server/clustered on **IBM z/OS** (also z/VSE, BS2000) with an **Adabas for LUW** (Linux/Unix/Windows) edition. Not embedded, not serverless.
- **Deployment:** On-prem mainframe primarily; "cloud" usage is via rehosting/emulation (Azure/AWS mainframe rehost) rather than a native cloud service. Not container/k8s-native.

## Bottom line
Reach for Adabas only if you already run it: it remains a fast, durable, battle-tested OLTP engine for the mainframe core systems it was built for, and ripping it out is risky and costly. **Do not** choose it for anything new — it is a closed, proprietary, multivalue mainframe DBMS with no SQL-native query layer, scarce talent, and per-MIPS licensing. The single biggest gotcha is **lock-in plus skills risk**: the data model and the Natural application layer are deeply intertwined, so the real cost is the application rewrite, not just the data migration — and the vendor/ownership picture (Software AG broken up and taken private by Silver Lake, with Adabas & Natural carved out as a standalone unit) adds long-term-roadmap uncertainty.

## Sources
- [Wikipedia: ADABAS](https://en.wikipedia.org/wiki/ADABAS)
- [Software AG documentation — Adabas Design (inverted lists, Associator, ISN)](https://documentation.softwareag.com/adabas/ada744mfr/adamf/concepts/cfdesign.htm)
- [Software AG documentation — Using Adabas (ET/BT transactions, hold status, subtransactions)](https://documentation.softwareag.com/adabas/ada744mfr/adamf/concepts/cfusing.htm)
- [Software AG documentation — Restart and Recovery (auto-backout, PLOG, regenerate)](https://documentation.softwareag.com/adabas/ada823mfr/adamf/operator/recovery.htm)
- [Software AG documentation — ADARUN parameters](https://documentation.softwareag.com/adabas/wcp651mfr/ref/adarun.htm)
- [Software AG documentation — Adabas Parallel Services](https://documentation.softwareag.com/adabas/asm831/intro/asmcintr.htm)
- [Software AG documentation — Adabas Cluster Services and other products](https://documentation.softwareag.com/adabas/als841/introduction/others.htm)
- [Software AG documentation — accessing Adabas from Natural](https://documentation.softwareag.com/natural/nat827mf/pg/pg_dbms_ada.htm)
- [Software AG — Adabas SQL Gateway](https://www.softwareag.com/en/resources/adabas-natural/adabas-sql-gateway/)
- [Software AG — Event Replicator for Adabas](https://www.softwareag.com/en_corporate/resources/adabas-natural/ds/event-replicator.html)
- [Information Builders — Adabas field types (MU/PE)](https://infocenter.informationbuilders.com/wf8005/topic/pubdocs/Adapter_Admin/source/topic22.htm)
- [Microsoft Learn — Rehost Adabas/Natural on Azure](https://learn.microsoft.com/en-us/azure/architecture/example-scenario/mainframe/rehost-adabas-software-ag)
- [AWS — Modernize Natural/Adabas workloads](https://aws.amazon.com/blogs/apn/modernize-natural-and-adabas-workloads-on-aws-with-ibm-modernsystems-accelerator/)
