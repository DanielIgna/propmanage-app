# SSOT REGISTRY

**Artifact Type**: REGISTRY
**Owner**: Fondator (danieligna1@gmail.com)
**Last Review**: 2026-02-06
**Schema**: Topic · OwnerDocument · AuthorityTier · Status · LastReview · Notes
**Purpose**: Enumerates the Single-Source-of-Truth mapping for every governance topic on PropManage. For any listed topic, the row's `OwnerDocument` is the canonical statement — any other document that references the topic must defer to it.

> This registry does not contain narrative prose. It contains structured facts. To add a new topic: (1) verify no equivalent SSOT already exists in this registry; (2) confirm the OwnerDocument is Active and Approved; (3) append a row respecting the schema; (4) bump `Last Review`.

## Schema Fields

| Field | Description |
|---|---|
| Topic | The subject of the SSOT statement. Short, canonical noun-phrase. |
| OwnerDocument | Repository path to the document holding the authoritative statement. |
| AuthorityTier | `Constitutional` · `Board Directive` · `Enterprise Standard` · `Draft`. |
| Status | `Active` · `Draft` · `Deprecated`. Only `Active` rows are canonical. |
| LastReview | ISO date (`YYYY-MM-DD`) of last verification by the Owner. |
| Notes | Contextual annotation. Kept short. |

## Entries

| Topic | OwnerDocument | AuthorityTier | Status | LastReview | Notes |
|---|---|---|---|---|---|
| Governance Hierarchy | memory/audits/MASTER_KNOWLEDGE_GOVERNANCE.md | Constitutional | Active | 2026-07-31 | Constitutional archive governing every document in the Knowledge Center. |
| Master Platform State | memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md | Constitutional | Active | 2026-07-31 | Living record of platform state, capabilities, and unresolved risks. |
| Artifact Types | memory/audits/MASTER_KNOWLEDGE_GOVERNANCE.md | Constitutional | Active | 2026-02-06 | Six artifact types: DOCUMENT · REGISTRY · GRAPH · LEDGER · INDEX · CATALOG. Only DOCUMENT and REGISTRY populated. |
| Board Directives | memory/board/directives/ | Constitutional | Active | 2026-02-06 | Every `BD-*` file is authoritative for its stated scope. Feature-freeze BD-RDPE currently in force. |
| Knowledge Center | memory/audits/MASTER_KNOWLEDGE_GOVERNANCE.md | Constitutional | Active | 2026-07-31 | Enterprise KC exists to be the platform's long-term memory and constitutional archive. |
| Research-Driven Product Evolution | memory/audits/BOARD_DIRECTIVE_RESEARCH_DRIVEN_EVOLUTION.md | Board Directive | Active | 2026-07-31 | New features frozen until 15-20 field interviews with association presidents complete. |
| Canonical System Registry | memory/registries/CANONICAL_SYSTEM_REGISTRY.md | Enterprise Standard | Active | 2026-06 | Registrul sistem → implementare canonică (SoT, rute, DB, consumeri). Obligatoriu în preflight. |
| Preflight Gate (pre-implementare) | memory/prompts/PREFLIGHT_GATE.md | Enterprise Standard | Active | 2026-06 | Poartă obligatorie: Knowledge before Code, Change Intent, Conflict Protocol, politica de audit. Post-Task 8R. |
| Property Twin Architecture (2D+3D · Anchor) | memory/audits/PROPERTY_TWIN_CANONICAL_v1.0.md | Enterprise Standard | Active | 2026-06 | Taxonomie umbrelă 2D(`twins`)+3D(`digital_twin_projects`). P0/P1/P0.1 Property Anchor = PRODUCTION-LIVE. §9: Next Stage I/II/III (AI Design Concepts, validare profesională, Q&A grounded, ancorare în masă, comparație, ofertă din concept validat, notificare, materiale reale/City Partners, catalog admin, alegere câștigător, concept în pașaport, ofertă cu poze) = DELIVERED IN PREVIEW (redeploy Fondator pt. LIVE). Reguli integritate + City Partner Products + known issue `.skp`/Trimble + next roadmap. Deprecă orice referință la `twins` ca „legacy/migrat". |
