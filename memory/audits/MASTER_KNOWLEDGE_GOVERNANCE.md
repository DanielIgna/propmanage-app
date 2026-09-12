# MASTER_KNOWLEDGE_GOVERNANCE

> **Status**: Constitutional. Governs every document inside the PropManage Enterprise Knowledge Center.
> **Effective**: 2026-07-31.
> **Scope**: This document defines the rules by which every other document exists, evolves, relates, and is governed. It does NOT redefine any existing document.
> **Precedence**: This is the Single Source of Truth for Knowledge Governance. Where an existing document contains governance rules that contradict this document, the newer statements of this document apply for future decisions; existing artifacts remain valid until superseded.
> **Referenced by**: every future Board Directive, Execution Order, Audit, and Roadmap decision that concerns documents in the Knowledge Center.

---

## 1. Purpose

The Knowledge Center exists to be **the enterprise's long-term memory and constitutional archive**. Every strategic decision, architectural choice, operational rule, and learned lesson is written down, versioned, and made discoverable, so that:

- Decisions are **traceable** to their evidence and their authors.
- Institutional knowledge **survives** turnover of humans and AI agents.
- The platform **evolves on record**, not on undocumented tribal knowledge.
- Any auditor — human or AI — can, in minutes, reconstruct the reasoning behind any past decision.
- Future development is grounded in what is written, not what is assumed.

The Knowledge Center is not a wiki. It is a constitutional archive. Its integrity is more valuable than the speed with which it is updated.

---

## 2. Core Principles

Seven principles govern every act of writing, reading, editing, or removing a document.

### 2.1 Single Source of Truth (SSOT)
For any given topic, exactly **one** document holds the authoritative statement. All other documents that touch that topic must reference (not copy) the SSOT. When two documents disagree, the one designated SSOT wins by definition.

### 2.2 Traceability
Every statement of consequence — a rule, a metric, a decision — must be attributable. Documents declare:
- **Origin**: which interview, audit, directive, or research report produced this statement.
- **Author** (human or AI agent) and **date**.
- **Evidence path**: link to the underlying artifact whenever possible.

Statements without traceability are **claims**, not knowledge. Claims may exist in Draft documents but must not exist in Active canonical documents.

### 2.3 Auditability
Any document can be inspected at any time and its history reconstructed. Version snapshots must be preserved (never destructive edits on canonical docs). The audit trail is expected to answer:
- What did this document say on date X?
- Who changed it and why?
- What decision followed from that state?

### 2.4 Versioning
Canonical documents are versioned. The current version is the canonical file (no version suffix). Historical versions live alongside with dated suffixes (`*_YYYY-MM-DD.md`). No historical version is ever deleted.

### 2.5 Human + AI Governance
Both humans and AI agents are legitimate authors. The Knowledge Center does not privilege one over the other on the axis of authorship. It does, however, differentiate them on the axis of **authority**: certain document classes can only be **approved** by humans (see §11).

### 2.6 Evidence Before Assumptions
No canonical document should assert what is not evidenced. Aspirational content is permitted, but must be **explicitly marked** (see Document Types §5). The default reading of any Active canonical document is: "this is real, not aspirational, not a hypothesis."

### 2.7 Canonical Over Duplicated Knowledge
Duplication is not merely inefficient — it is dangerous. Two documents that both purport to be authoritative on the same topic create legal ambiguity in decision-making. The Knowledge Center is built to prevent this: every canonical claim exists exactly once.

---

## 3. Document Hierarchy

The Knowledge Center recognizes a **document hierarchy** parallel to the **authority hierarchy** defined in `GOVERNANCE_HIERARCHY.md` (9 levels: Constitution → Directives → Standards → Playbooks → Principles → Health → Cognitive Engine → Copilot → Autonomous Enterprise).

The document hierarchy has **five tiers**, each with its own governance rules:

| Tier | Name | Purpose | Example categories |
|---|---|---|---|
| **T0** | Constitutional | Foundational, quasi-immutable. Changes require full-board process. | Constitution, System Zero |
| **T1** | Directive | Strategic decisions with binding force. | Board Directives, Executive Orders, Board Resolutions |
| **T2** | Canonical Reference | Long-lived authoritative reference documents. | Enterprise Standards, Enterprise Principles, Enterprise Playbooks, Ownership Matrix, MASTER_PLATFORM_STATE, Product Blueprint, Architecture |
| **T3** | Operational | Living operational documents. Actively updated. | Roadmaps, Enterprise Metrics, Enterprise Health, Enterprise Score, Platform Audits, Digital Twin, Finance, Strategy, Governance procedures |
| **T4** | Working Artifacts | Research, drafts, experimental, learning material. | Interviews, patterns, research reports, reuse audits, case libraries, memory dumps, CEO mode prompts |

**Rules of inheritance and precedence**:

- **Higher tiers govern lower tiers.** A T3 document may not contradict a T2 document; a T2 document may not contradict a T1 document.
- **A T4 document may propose changes to higher tiers**, but only via the formal pipeline (§8). It cannot unilaterally change them.
- **Every T2, T3, T4 document declares its parent** — the higher-tier document(s) it derives from or serves.
- **Constitutional documents (T0) can only be amended** by explicit Board process. This document itself is T0.

The five-tier document hierarchy is the mechanism by which the 9-level authority hierarchy is enacted in written form.

---

## 4. Authority Matrix

For each document type, the following roles are defined:

- **Owner** — accountable for keeping the document accurate, evolving, and coherent.
- **Approver** — has final say for promotion to Active / for amendments.
- **Editors** — permitted to open changes (drafts, reviews).
- **Archivers** — can move a document to Archived state.
- **Promoters** — can promote a Draft to Active.
- **AI permission** — what AI agents may do without human review.

| Category | Tier | Owner | Approver | Editors | AI may create | AI may edit | AI may archive |
|---|---|---|---|---|---|---|---|
| **Constitution** | T0 | Founder | Founder + Board | Founder | ❌ | ❌ (suggest only) | ❌ |
| **System Zero** | T0 | Founder | Founder | Founder | ❌ | ❌ | ❌ |
| **Board Directives** | T1 | Founder | Founder | Founder + Board members | ❌ | ❌ | ❌ |
| **Board Resolutions** | T1 | Founder | Founder | Founder | ❌ | ❌ | ❌ |
| **Executive Orders** | T1 | Founder | Founder | Founder | ❌ | ❌ | ❌ |
| **AI Charters** | T1 | Founder | Founder | Founder | ❌ | ❌ | ❌ |
| **Enterprise Standards** | T2 | Architecture Owner | Founder | Architecture team + AI (draft) | ✅ Draft only | ✅ Draft only | ❌ |
| **Enterprise Principles** | T2 | Founder | Founder | Founder | ❌ | ✅ Draft only | ❌ |
| **Enterprise Playbooks** | T2 | Ops Owner | Founder | Ops team + AI | ✅ Draft only | ✅ Draft only | ❌ |
| **Ownership Matrix** | T2 | Architecture Owner | Founder | Architecture team + AI | ✅ Draft only | ✅ Draft only | ❌ |
| **MASTER_PLATFORM_STATE** | T2 | Auditor (AI or human) | Founder | AI + auditor | ✅ new snapshots | ✅ current canonical | ❌ (no version deleted) |
| **Product Blueprint** | T2 | Product Owner | Founder | Product team + AI (draft) | ✅ Draft only | ✅ Draft only | ❌ |
| **Architecture** | T2 | Architecture Owner | Founder | Architecture team + AI | ✅ Draft only | ✅ Draft only | ❌ |
| **Executive Prompts / CEO Mode** | T2 | Founder | Founder | Founder + AI (variation) | ✅ variants | ✅ variants | ❌ |
| **Enterprise Metrics / Health / Score** | T3 | Metrics Owner | Founder | AI + metrics owner | ✅ recalculations | ✅ formulas via registry | ✅ superseded formulas |
| **Roadmaps** | T3 | Founder | Founder | Founder + AI (draft entries) | ✅ Draft entries | ✅ status updates | ❌ |
| **Platform Audits** | T3 | Auditor | Founder | AI auditor + human | ✅ new audit | ❌ (append only) | ❌ (never delete) |
| **Governance procedures** | T3 | Founder | Founder | Founder | ❌ | ✅ Draft only | ❌ |
| **Strategy** | T3 | Founder | Founder | Founder | ❌ | ✅ Draft only | ❌ |
| **Digital Twin / Finance** (domain docs) | T3 | Domain Owner | Founder | Domain team + AI | ✅ Draft only | ✅ Draft only | ✅ superseded |
| **Case Library** | T4 | Any editor | Owner review | Anyone | ✅ | ✅ | ✅ |
| **Memory (learning dumps, agent journals)** | T4 | AI agent | None | AI + auditor | ✅ | ✅ | ✅ old entries per retention |
| **Interviews (Research)** | T4 | Research analyst | Founder | Research analyst + AI transcript | ✅ transcripts | ✅ corrections only | ❌ (never delete raw evidence) |
| **Patterns, Research Reports** | T4 | Research analyst | Founder | Research analyst + AI drafts | ✅ Draft only | ✅ Draft only | ✅ superseded |
| **Reuse Audits** | T4 | Auditor (AI or human) | Founder | AI + Founder | ✅ Draft only | ✅ Draft only | ❌ (audit trail) |

**Universal rule**: **any promotion from Draft to Active, at any tier, requires explicit human Approver action.** AI agents cannot self-promote content to Active state on documents T0-T3. Only T4 working artifacts may be Active-by-default (as they are working material, not canon).

---

## 5. Canonical Documents — Types and Definitions

To eliminate confusion, seven document **states of nature** are defined. Every document in the Knowledge Center belongs to exactly one type at any given time.

### 5.1 Canonical
An Active, Approved document that constitutes the authoritative statement on its topic. If contradicted by another document, the Canonical wins. Every T0, T1, T2 document is Canonical or must be moving toward becoming Canonical (via Draft → Review → Approved lifecycle).

### 5.2 Derived
A document whose content is entirely derivable from other Canonical documents. Examples: a dashboard that displays MASTER_PLATFORM_STATE data, a Research Report that synthesizes Interviews. Derived documents must declare their sources explicitly. If a source changes, the Derived document is stale until refreshed.

### 5.3 Generated
A document produced automatically by an AI agent or a script. Generated documents are Draft-by-default. They become Canonical only via explicit human approval. Auto-generated audits are Generated until reviewed.

### 5.4 Temporary
A short-lived working document expected to be superseded or archived within a defined window (typically <90 days). Meeting notes, sprint plans, transitional migration guides. Must declare an expiration or supersedence intent.

### 5.5 Experimental
A document proposing a new approach, hypothesis, or design not yet validated. Marked as Experimental. Cannot be cited as authority for a decision. Becomes Canonical (or is discarded) once its hypothesis is tested.

### 5.6 Archived
A document that was once Canonical but is no longer Active. It remains readable and searchable, but is no longer cited as authority. Every reference to it in an Active document must be updated to point to its successor or removed.

### 5.7 Historical
A snapshot (versioned) of a Canonical document at a past point in time. Preserved permanently. Never edited. Cited in audits, trace analyses, and dispute resolution.

**A document may transition between types**, but transitions are governed by lifecycle rules (§6).

---

## 6. Lifecycle

Every document, regardless of tier, passes through a well-defined lifecycle. Not every document reaches every stage.

```
       ┌─────────┐
       │  DRAFT  │  Editor works, no external authority
       └────┬────┘
            │  Editor submits for review
            ▼
       ┌─────────┐
       │ REVIEW  │  Approver examines, comments, requests changes
       └────┬────┘
            │  Approver approves
            ▼
       ┌─────────┐
       │APPROVED │  Ready to be Active; awaiting publication/promotion
       └────┬────┘
            │  Promoter activates
            ▼
       ┌─────────┐
       │ ACTIVE  │  Canonical. Cited by other docs and by decisions.
       └────┬────┘
            │  Conditions change → superseded or invalidated
            ▼
       ┌───────────┐
       │DEPRECATED │  No longer authoritative. Successor identified.
       └─────┬─────┘
             │  All references updated
             ▼
       ┌──────────┐
       │ ARCHIVED │  Read-only. Preserved. Cannot be cited as authority.
       └──────────┘
```

### 6.1 Transition rules

- **Draft → Review**: any Editor with permission on that document type. Automatic if AI-generated on T2-T3 docs (a Draft cannot become Canonical without Review).
- **Review → Approved**: only by the designated Approver for the document category.
- **Approved → Active**: only by a Promoter. Different from Approver to enforce two-person integrity on T0/T1 (Approver = Founder, Promoter may be operational).
- **Active → Deprecated**: only by Owner, with named successor OR explicit obsolescence rationale. Requires that all Active references be updated within a grace window (default: 30 days).
- **Deprecated → Archived**: automatic after the grace window, unless a dispute is open.
- **Any state → any earlier state**: **not permitted directly.** A superseded document can be reactivated only by creating a NEW version and going through Draft → Review → Approved → Active.

### 6.2 Idle detection

Documents Active for longer than their **freshness window** (defined per category in §10) trigger a review reminder. This is not enforcement — it is signal. The Owner may reaffirm freshness with a dated stamp.

### 6.3 Amendment vs replacement

- **Amendment**: minor changes to an Active document. Version history preserved. Editor + Approver required. Applied to T2 and lower.
- **Replacement**: new document supersedes old; old is Deprecated → Archived. Required for major structural changes to T2, and any change to T0/T1.

---

## 7. Conflict Resolution

When two Active documents disagree on the same topic, one of the following resolution paths applies, in the following order:

### 7.1 Tier precedence
The document at the higher tier wins. A T2 Canonical wins against a T3 Roadmap; a T1 Directive wins against a T2 Standard.

### 7.2 SSOT designation
Within the same tier, if one of the documents is designated SSOT for the topic in question, it wins. Every topic must have a designated SSOT (see §9.5 "Orphan Topics" as an integrity failure).

### 7.3 Recency
If both are at the same tier and neither is a designated SSOT, the more recent Active version wins. This is the fallback rule; it is inferior to §7.1 and §7.2 because it can produce silent drift.

### 7.4 Escalation
If precedence, SSOT, and recency all fail (rare), the conflict escalates to the Founder for a **Conflict Resolution Note** — a short document recording the decision, filed in Governance, referenced by both conflicting documents.

### 7.5 Traceability preservation
No conflict resolution ever silently overwrites the losing document. The losing document either:
- Is Deprecated with a note pointing to the winner, OR
- Remains Active but with an explicit note ("This document is subordinate to X on topic Y").

Loss of traceability during conflict resolution is a governance defect.

---

## 8. Dependency Rules

Changes in one canonical document ripple. The dependency graph defines the ripple path.

### 8.1 Downstream cascade

```
Constitution (T0) changed
   └─► All Board Directives (T1) must be reviewed for compatibility
         └─► All Standards / Playbooks (T2) must be reviewed
               └─► All Roadmaps / Metrics (T3) must be reviewed
                     └─► All Working Artifacts (T4) may need adjustment
```

- **Cascade obligation**: when a higher-tier document changes, the Owner of that document notifies (via a Dependency Impact Note) the Owners of every document that declares it as a parent.
- **Grace period**: 30 days by default for T2 review post-T1 change; 60 days for T3; 90 days for T4.
- **Blocking**: if a downstream review fails (i.e., a T2 document cannot be reconciled with a new T1), the T1 change may be paused and the conflict escalated per §7.4.

### 8.2 Upstream propagation

Changes at lower tiers may generate proposals for upstream changes:
- Persistent contradictions between multiple T3 metrics and a T2 principle → propose T2 amendment.
- Multiple T4 patterns converging on same missing capability → propose T3 Roadmap addition.
- New T4 research invalidating a T2 assumption → propose T2 revision.

Proposals travel via the standard Draft pipeline. **Upstream changes never happen implicitly.**

### 8.3 Specific dependency paths

Documented for clarity (this list is illustrative, not exhaustive):

- **Product Blueprint** (T2) → **Architecture** (T2) → **Roadmaps** (T3) → **Execution Orders** (T1 override) → **Metrics** (T3) → **Platform Audits** (T3)
- **Board Directives** (T1) → **Standards / Playbooks / Principles** (T2) → all operational docs
- **Enterprise Metrics** (T3) → **Enterprise Health / Score** (T3) → **CEO Briefing** (T3, if formalized)
- **Interviews** (T4) → **Patterns** (T4) → **Research Reports** (T4) → **Reuse Audits** (T4) → **PRD** (T2 update) → **Roadmap** (T3 update)

Every canonical document should declare, in its header or in a manifest section, its **upstream parents** and **downstream children** where known.

---

## 9. Knowledge Integrity

Six integrity defects must be actively prevented:

### 9.1 Duplicate truth
Two documents both claim authority on the same topic. Mitigation: SSOT designation is mandatory; auditor tool (future) flags topical overlap.

### 9.2 Circular governance
Document A cites Document B as authority; Document B cites Document A as authority. Neither is grounded. Mitigation: every cited authority must ultimately trace to a T0/T1 or to observable evidence (interview, metric, code).

### 9.3 Orphan documents
A document exists but is not referenced by, and does not reference, any other canonical document. Two possible root causes: (a) it is truly disconnected, or (b) it is meaningful but the graph is incomplete. Mitigation: quarterly Orphan Review; either connect or archive.

### 9.4 Dead documents
Active documents that have not been reviewed in a period far exceeding their freshness window (e.g., 2+ years for a T3 that should be refreshed annually). Mitigation: freshness monitoring (§10).

### 9.5 Orphan topics
A topic (a concept, a metric, a decision) referenced by multiple documents, but with no document designated SSOT for it. Mitigation: SSOT registry (may be a section within this document or a companion).

### 9.6 Zombie directives
Directives that were superseded in intent but never explicitly Deprecated. Continues to be citable, misleading readers. Mitigation: whenever a Board Directive is superseded, its Archived state must be explicit and immediate.

### 9.7 Conflicting authority
Two Approvers claim authority over the same document. Mitigation: exactly one Approver per document per category, defined in the Authority Matrix (§4).

---

## 10. Governance Metrics

The Knowledge Center's health is itself measurable. Nine metrics are defined; each has a rationale and a proposed calculation. Implementation is out of scope for this document; targets and formulas are provided so any future observer knows what "healthy" looks like.

| Metric | What it measures | Target |
|---|---|---|
| **Governance Health** | Composite of the below, weighted | ≥ 85% |
| **Canonical Coverage** | % of active topics with a designated SSOT | ≥ 95% |
| **Documentation Coverage** | % of implemented modules with at least one referenced doc | ≥ 90% |
| **Review Latency** | Median days between change proposal and Approver decision | ≤ 7 days (T2), ≤ 3 days (T1) |
| **Dependency Integrity** | % of canonical docs where declared parents and children all resolve | ≥ 98% |
| **Conflict Count** | Number of open conflicts (§7) at any given time | ≤ 3 concurrent |
| **Freshness Score** | % of Active docs within their freshness window | ≥ 80% |
| **Ownership Coverage** | % of canonical docs with a named Owner and named Approver | 100% |
| **Orphan Rate** | % of documents without declared parents or children | ≤ 5% |

### 10.1 Freshness windows (default per tier)

- T0: 24 months (Constitution rarely changes)
- T1: 12 months
- T2: 6 months
- T3: 3 months
- T4 Interviews / Research Reports: no freshness expiration (evidence is timeless once captured, but interpretations may be revised)
- T4 Case Library / Memory: 6 months (patterns evolve)

An Owner may override the default by declaring an explicit freshness statement in the document.

### 10.2 Reporting

Governance metrics are reported in Platform Audits (T3) as part of the periodic MASTER_PLATFORM_STATE snapshot. They may also feed the CEO Briefing when the CEO Briefing is formalized.

---

## 11. AI Governance

The Knowledge Center welcomes AI as a co-author but establishes strict boundaries.

### 11.1 What AI may create autonomously

- **T4 Working Artifacts**: interview transcripts, pattern draft docs, research report drafts, reuse audit drafts, generated snapshots (Platform Audits as Generated), memory entries, agent journals.
- **T3 Draft entries**: recalculated metrics, updated freshness statuses, roadmap draft entries derived from validated patterns.
- **T2 Draft revisions**: proposed changes to Standards, Playbooks, Blueprint, Architecture. Never Active without human Approver.
- **New categories in Knowledge Center**: never. Category taxonomy is founder-controlled.

### 11.2 What AI may suggest

- Amendments to any T0-T2 document, framed explicitly as a suggestion, filed as a Draft.
- Deprecation candidates for documents that appear stale or superseded.
- Merge proposals for duplicated topics.
- Conflict flags with proposed resolutions.

### 11.3 What AI may never change automatically

- **Constitutional documents (T0)**: no auto-write ever.
- **Board Directives (T1)**: no auto-write ever.
- **Executive Orders (T1)**: no auto-write ever.
- **Any document currently Active** (T2-T3): no destructive edit. AI produces a Draft revision, never overwrites Active content.
- **Archived documents**: never rewritten.
- **Historical snapshots**: never rewritten.

### 11.4 When human approval is mandatory

- Any transition from Draft to Active on T0-T3 documents.
- Any transition from Active to Deprecated on T0-T2 documents.
- Any transition from Active to Archived on T0-T2 documents.
- Creation of a new SSOT designation.
- Resolution of a Conflict Resolution Note (§7.4).
- Any change to this document (MASTER_KNOWLEDGE_GOVERNANCE).

### 11.5 AI attribution

AI-authored content must be identifiable. Convention: a `--- AI-generated by [agent name] on [date] ---` footer, or equivalent metadata line. This is not a warning; it is a factual attribution, equivalent to a human byline.

### 11.6 AI accountability

An AI agent that produces a Draft is the **author** of that Draft; the Approver is accountable for admitting it to Active state. The AI is accountable for the accuracy of its Draft (traceability, citation of sources); the Approver is accountable for the judgment of activation.

---

## 12. Knowledge Evolution — Scaling from 100 to 10,000 documents

The Knowledge Center is designed to remain coherent as it grows. Coherence is not automatic; it is enforced by rules that scale.

### 12.1 100 documents (current, ~207 as of 2026-07-31)

At this scale, all governance can be manual. A human can read every category monthly. Category taxonomy fits in one screen. Cross-references are traceable by hand.

**Practices sufficient at this scale**:
- Manual Owner and Approver tracking.
- Manual freshness review (quarterly).
- Manual orphan detection.
- No search-scale problems.

### 12.2 500 documents

Manual review becomes impractical. Categorization must be strictly enforced (no free-floating docs). Freshness monitoring should be surfaced in a dashboard (not necessarily automated). SSOT registry must be explicit — cannot be reconstructed from memory.

**Practices to add**:
- SSOT registry as a formal document.
- Dependency graph as a formal document (or generated view).
- Category audit (are we accumulating categories carelessly?).
- Search indexing tuned (full-text works, but semantic clustering starts to matter).

### 12.3 1,000 documents

The Knowledge Center becomes an asset in its own right — a competitive moat, a training corpus. Governance overhead now consumes real time. Automated monitoring of governance metrics (§10) becomes worth the effort.

**Practices to add**:
- Automated freshness alerts.
- Automated orphan detection.
- Automated conflict detection (topical overlap analysis).
- Structured metadata (front-matter) on every canonical document — Owner, Approver, tier, parents, children, SSOT declarations. Free-form Markdown continues, but with a machine-parseable header.
- Semantic search on top of full-text.
- Retention policy for T4 working artifacts (5+ years old, without citations, may auto-archive).

### 12.4 10,000 documents

At this scale, the Knowledge Center is a knowledge graph, not a folder. Categories become facets. Documents connect via typed relationships (`derives_from`, `supersedes`, `implements`, `contradicts`). AI-assisted navigation becomes essential, not optional. Governance itself is a discipline with dedicated ownership.

**Practices to add**:
- Formal Knowledge Center curator role (human or AI-led team).
- Cross-doc integrity validators run continuously.
- Deprecation cadence: automated proposals reviewed by curator.
- Documents that have been un-referenced for 12+ months are candidates for automatic Archived, subject to human confirmation.
- The Knowledge Center itself is periodically audited (meta-audit), scored, and reported to executives.

### 12.5 Scaling invariants

Regardless of scale, five invariants hold:

1. **No canonical claim exists in two places.** Duplication is the primary enemy at all scales.
2. **Every canonical document has a named Owner and Approver.** Ownership is not optional.
3. **Every document is either connected to the graph, or it is archived.** Orphans are not tolerated indefinitely.
4. **Every change is traceable to its author, date, and evidence.** Anonymity is not permitted for canonical changes.
5. **Constitutional documents (T0) change only via explicit Board process.** This is inviolable.

---

## Appendix A — Referenced foundational documents

This document does not redefine, but formally references, the following existing canonical documents:

- `GOVERNANCE_HIERARCHY.md` — 9-level authority hierarchy. This document (MASTER_KNOWLEDGE_GOVERNANCE) is the document-lifecycle projection of that authority hierarchy.
- `constitution/EXECUTIVE_CONSTITUTION.md` — Executive constitutional foundation.
- `constitution/PROPMANAGE_PRODUCT_CONSTITUTION.md` — Product constitutional foundation.
- `ENTERPRISE_STANDARDS.md`, `ENTERPRISE_PRINCIPLES.md`, `ENTERPRISE_PLAYBOOKS.md` — T2 canonical references.
- `MASTER_PLATFORM_STATE.md` (Platform Audits) — T2 canonical for platform implementation state.
- `RESEARCH_DRIVEN_PRODUCT_EVOLUTION_2026-07-31.md` + `BOARD_DIRECTIVE_RESEARCH_DRIVEN_EVOLUTION.md` — the methodology by which T4 research becomes T2/T3 upgrades.
- `Ownership Matrix` (in chat, pending migration to a canonical file in `/app/memory/audits/`) — T2 canonical for module ownership.

These references are asserted, not defined. If any of these documents change, this document is unaffected unless the change concerns governance mechanics themselves (in which case an amendment to this document is required, per §6.3).

---

## Appendix B — Amendment procedure for this document

This document is T0 Constitutional. Its amendment procedure is deliberately restrictive.

1. **Proposal**: any Editor may file a Draft amendment as a companion document (`MASTER_KNOWLEDGE_GOVERNANCE_AMENDMENT_YYYY-MM-DD_topic.md`), never by editing the canonical file.
2. **Review**: minimum 7-day open review.
3. **Approval**: Founder approves.
4. **Promotion**: a new canonical version is issued (`MASTER_KNOWLEDGE_GOVERNANCE_YYYY-MM-DD.md` versioned + canonical copy updated).
5. **Prior version**: archived permanently under the versioned filename.

No emergency amendment procedure exists. If an urgent governance issue arises that this document cannot resolve, the Founder issues a Board Directive as override; the Directive stands until this document is formally amended to incorporate it.

---

## Metadata

- **Version**: 1.0
- **Effective**: 2026-07-31
- **Tier**: T0 (Constitutional)
- **Owner**: Founder
- **Approver**: Founder
- **Parent documents**: `GOVERNANCE_HIERARCHY.md`, `constitution/EXECUTIVE_CONSTITUTION.md`
- **Children (documents this one governs)**: every document in the Knowledge Center
- **Next scheduled review**: 2027-07-31 (or on amendment)
