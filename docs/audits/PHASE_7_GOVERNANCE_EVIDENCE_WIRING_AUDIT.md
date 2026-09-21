# PHASE 7 — GOVERNANCE EVIDENCE WIRING AUDIT

**Artifact type:** T3 Platform Audit (Generated). Not canonical. Not a Board Directive.  
**Date:** 2026-09-22  
**Author:** Cursor agent (forensic audit only)  
**Scope:** How existing Knowledge Center Phase 2–6 sensors could connect to existing PropManage governance through *evidence wiring*.  
**Method:** Inspected the live repository (Git, code, tests, APIs, UI, registries, governance documents). Prior chat is not treated as evidence.  
**Constraint:** No implementation. No canonical writes. No registry writes. No new engines.

Classification used throughout:

| Tag | Meaning |
|---|---|
| **FACT** | Directly present in a named file or in running code. |
| **EVIDENCE** | The path / quote / test that supports the fact. |
| **INFERENCE** | A reading of those facts. Not authority. |
| **PROPOSAL** | A recommended next step. Not decided. |
| **UNKNOWN** | Inspected and still not established. Not false. Not invalid. Not untrusted. |

States that must stay distinct:

| State | Meaning in this audit |
|---|---|
| DOCUMENTED | A KC artifact exists that describes the thing. |
| IMPLEMENTED | Code / tests / runtime exist. |
| EVIDENCED | A named source (code, Git, test, registry edge) supports a claim. |
| CONNECTED | Two systems read or write each other’s outputs. |
| AUTOMATED | A scheduled or on-demand job produces the output. |
| AUTONOMOUS | The system mutates product or canon without Founder approval. |

---

## 1. Executive Summary

**FACT:**
Phase 2, 4, and 5 exist as uncommitted Python sensors. Phase 6 exists as a generated audit file plus a coverage-corpus exclusion. Phase 3 has no dedicated engine file and no persisted Phase 3 report in the repository.

**EVIDENCE:**
`git status --porcelain` shows untracked `backend/knowledge_coverage.py`, `backend/knowledge_history.py`, `backend/knowledge_reconciliation.py`, their tests, and `docs/audits/`. `docs/audits/` contains only `PHASE_6_GOVERNANCE_INTEGRATION_AUDIT.md`. Repository search finds no `knowledge_forensic.py` and no `PHASE_3_*` audit file.

**FACT:**
Those sensors compute evidence on demand. They do not persist it. They do not write Constitution, Directives, SSOT, Function Map, MPS, or `enterprise_registry.json`. They are Founder-only at the API boundary.

**EVIDENCE:**
Each engine sets `canonical_promotion_allowed = False` and `engine_writes_nothing()` forbids `insert_one` / `write_text` / `unlink`. Routes in `backend/routes/knowledge_center.py` call `_require_owner` before `build_coverage_report`, `build_history_report`, and `build_reconciliation_report`.

**FACT:**
The existing governance architecture already names Truth (D161), continuous platform audit (D116), continuous alignment (D149), learning (D162), operational autonomy (FN-021), PREFLIGHT, Founder Approval Gate (FG-0), and MKG §7.4 Conflict Resolution Notes.

**INFERENCE:**
The missing piece is not a new governance engine. The missing piece is wiring: Phase 2–6 evidence does not enter D161 reports, D116/D149 (which have no engines), D162/FN-021, PREFLIGHT runtime, Founder Gate, MKG §7.4 notes, or MASTER_PLATFORM_STATE.

**FACT:**
`enterprise_registry.json` has a Knowledge Center engine node pointing at `knowledge_center.py`. It has no nodes for Phase 2–6. Registry-node absence is not capability absence.

**PROPOSAL:**
Reuse the existing sensors, existing KC APIs, existing D161 label set, existing PREFLIGHT protocol, and existing MKG §7.4 note class. Do not create Truth Engine v2, Alignment Engine v2, Platform Audit Engine v2, or a second autonomy loop.

**UNKNOWN:**
Whether the Founder wants Phase 2–6 represented as registry nodes, persisted as ledger entries, or left as on-demand Founder-only reports.

---

## 2. Repository Evidence

### 2.1 Branch and HEAD

| Item | Value |
|---|---|
| Branch | `main` |
| Local HEAD | `12db435f24d35ec72dac4cec549bd4995b63fc23` |
| HEAD date / subject | 2026-09-19 · Igna Daniel · Continue PropManage Knowledge Center and evidence work |
| `origin/main` | `252f562020b0f0382c73bb97bca2c2ae96eb1c06` |
| `emergent/main` | `2f71a85ca2fd524b3d86fb8d46ff81257fbbe263` |
| vs origin | LOCAL_AHEAD · `0` origin-only / `2` local-not-origin |
| vs emergent | DIVERGED · `5` emergent-only / `10` local-not-emergent |
| remotes | `emergent` → `propmanage-online.git` · `origin` → `propmanage-app.git` |

**FACT:**
Phase 2–6 sensor files are not in HEAD. They exist only in the working tree.

**EVIDENCE:**
`git status --porcelain` at audit time:

```
 M backend/routes/knowledge_center.py
 M frontend/public/sitemap-*.xml
 M frontend/src/pages/admin/KnowledgeCenter.jsx
?? backend/knowledge_coverage.py
?? backend/knowledge_history.py
?? backend/knowledge_reconciliation.py
?? backend/tests/test_knowledge_coverage_iter240.py
?? backend/tests/test_knowledge_history_iter241.py
?? backend/tests/test_knowledge_reconciliation_iter242.py
?? docs/audits/
```

### 2.2 Relevant commits already in Git

| Commit | Date | Relevance |
|---|---|---|
| `12db435` | 2026-09-19 | KC + evidence work (7B–10C / identity / ledger first appear here) |
| `b03a9ba` | 2026-09-19 | KC path alignment for local and Emergent |
| `252f562` | 2026-09-18 | origin HEAD · Pages Functions proxy |
| `743ca6e` and earlier | 2026-09-18 | product / CI; `.emergent` removal lineage |
| `0953203`…`6c2bcf2` | 2026-09-18 | emergent-agent-e1 auto-generated changes |

**FACT:**
No commit message names Phase 2, Phase 4, Phase 5, or Phase 6 engines. Those files are untracked.

### 2.3 Phase 2–6 implementation locations

| Phase | Implementation | Tests | API | UI |
|---|---|---|---|---|
| 2 Coverage | `backend/knowledge_coverage.py` | `backend/tests/test_knowledge_coverage_iter240.py` (16 tests) | `GET /api/founder/knowledge/coverage` · `GET /coverage/changes` | Knowledge Center tab **Coverage / Drift** calls `/coverage` |
| 3 Bidirectional forensic | **No module.** No `PHASE_3_*` file in `docs/audits/` | None dedicated | None dedicated | None |
| 4 History | `backend/knowledge_history.py` | `backend/tests/test_knowledge_history_iter241.py` (14 tests) | `GET /api/founder/knowledge/coverage/history` | History block is attached onto the Phase 2 report; UI does not call `/coverage/history` |
| 5 Reconciliation | `backend/knowledge_reconciliation.py` | `backend/tests/test_knowledge_reconciliation_iter242.py` (9 tests) | `GET /api/founder/knowledge/coverage/reconciliation` | **No UI call** |
| 6 Governance integration | `docs/audits/PHASE_6_GOVERNANCE_INTEGRATION_AUDIT.md` + `is_generated_phase_audit()` in coverage | `test_generated_phase_audit_is_not_a_coverage_mention` | None (report is a file) | Visible in KC tree as a docs file; excluded from coverage mentions |

### 2.4 Tests run during this audit

| Command | Result | Pass / fail | Introduced by this phase? |
|---|---|---|---|
| `cd backend && ./venv/bin/python -m pytest tests/test_knowledge_coverage_iter240.py tests/test_knowledge_history_iter241.py tests/test_knowledge_reconciliation_iter242.py -q --tb=no` | 39 passed, 1 warning in 317.01s | 39 / 0 | No. Warning is Starlette `python_multipart` PendingDeprecationWarning in venv. No production or test files were changed except this audit report. |

**FACT:**
This phase added no production code. Failures were not introduced because no tests failed.

---

## 3. Existing Governance Architecture

Two written hierarchies exist. They are not the same object.

### 3.1 Nine-level authority (`memory/GOVERNANCE_HIERARCHY.md`)

```
LEVEL 1 — Board Constitution
LEVEL 2 — Board Directives
LEVEL 3 — Enterprise Standards
LEVEL 4 — Enterprise Playbooks
LEVEL 5 — Enterprise Principles
LEVEL 6 — Enterprise Health
LEVEL 7 — Enterprise Cognitive Engine
LEVEL 8 — Founder Copilot
LEVEL 9 — Autonomous Enterprise
```

**FACT:**
Precedence is written: higher levels govern lower levels.

### 3.2 Five-tier document hierarchy (`MASTER_KNOWLEDGE_GOVERNANCE.md` §3)

| Tier | Class | Examples present in repo |
|---|---|---|
| T0 | Constitutional | Product Constitution · `MASTER_KNOWLEDGE_GOVERNANCE.md` |
| T1 | Board / Orders | Board Directives · Execution Orders |
| T2 | Standards / living state | SSOT · Canonical Registry · Function Map · MPS (contested living file) |
| T3 | Audits / metrics | Platform audits · this file · Phase 6 |
| T4 | Working artifacts | Interviews / research / generated snapshots |

**FACT:**
MKG §3 states the five-tier *document* hierarchy is how the nine-level hierarchy is enacted in writing.

### 3.3 Registries and maps actually present

| Artifact | Path | Role discovered |
|---|---|---|
| SSOT | `memory/registries/SSOT_REGISTRY.md` | Topic → OwnerDocument. MPS topic points at `MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md` |
| Canonical System Registry | `memory/registries/CANONICAL_SYSTEM_REGISTRY.md` | System → code. Second implementation requires Founder approval |
| Function Map | `memory/registries/FUNCTION_MAP.md` | FN-001–021. Last update line: 2026-06. FN-003 API list does **not** include `/coverage*` |
| Enterprise Relationship Registry | `backend/data/enterprise_registry.json` | Proven edges only. Principle: “Doar relații dovedite… nu inferăm.” |
| PREFLIGHT | `memory/prompts/PREFLIGHT_GATE.md` | Pre-implementation STOP / Conflict Protocol. Document, not a runtime engine |
| Founder Approval Gate | `backend/founder_gate/` | FG-0 registry of 13 critical *product* actions. `enforcement_active: False` |
| MKG §7 / §11 | `memory/audits/MASTER_KNOWLEDGE_GOVERNANCE.md` | Conflict Resolution Notes · AI may not auto-write T0/T1 or Active T2–T3 |

### 3.4 Three different “Founder Gate” objects

**FACT:**
The phrase “Founder Gate” names three different things.

| Object | What it is | Enforcement |
|---|---|---|
| MKG §4 / §11 | Document promotion / conflict approval | Written rule. No runtime hook from Phase 2–6 |
| PREFLIGHT_GATE.md | Agent protocol before code | Human/agent discipline. No Python importer of Phase 2–6 |
| `founder_gate` FG-0 | Dual-verification for 13 product actions (pricing, Stripe, bulk delete, deploy, …) | Foundation only. Flag default OFF. No KC coverage slugs |

**INFERENCE:**
Wiring Phase 2–6 into “Founder Gate” without specifying which of the three is a scope error.

### 3.5 Named engines vs files

| Named authority | Document | Implementation file found? |
|---|---|---|
| D161 Truth Engine | `BOARD_DIRECTIVE_161_TRUTH_ENGINE.md` | No `truth_engine.py`. Labels used in `lead_followup.py` and (partially) KC health |
| D116 Continuous Platform Audit | `BOARD_DIRECTIVE_116_CONTINUOUS_PLATFORM_AUDIT_ENGINE.md` | No engine file |
| D149 Continuous Alignment | `BOARD_DIRECTIVE_149_CONTINUOUS_ALIGNMENT_ENGINE.md` | No engine file |
| D162 Enterprise Learning | `BOARD_DIRECTIVE_162_ENTERPRISE_LEARNING_ENGINE.md` | `backend/learning_engine.py` — commercial outcome scan, not KC |
| FN-021 Autonomy Loop | Function Map + `backend/autonomy/loop.py` | Implemented for Analytics + `admin_ai_findings` `stale_project` |
| D153 Decision Journal | `BOARD_DIRECTIVE_153_ENTERPRISE_DECISION_JOURNAL.md` | No `decision_journal.py`. `ai_decision_ledger` is a different, narrower store |
| D132 Executive Memory | `BOARD_DIRECTIVE_132_EXECUTIVE_MEMORY_ENGINE.md` | No engine file |
| D146 Synthesis | `BOARD_DIRECTIVE_146_ENTERPRISE_SYNTHESIS_ENGINE.md` | No engine file |
| D167 Enterprise Genome | `BOARD_DIRECTIVE_167_ENTERPRISE_GENOME.md` | No genome engine file |
| D126 Digital Property Genome | `BOARD_DIRECTIVE_126_DIGITAL_PROPERTY_GENOME.md` | Property-domain directive, not KC wiring |

---

## 4. Phase 2–6 Evidence Inventory

| Phase | Capability | Evidence Produced | Storage | API | Founder-only | Mutates Canon | Current Status |
|---|---|---|---|---|---|---|---|
| 2 | Knowledge ↔ Code coverage on a 10-area watchlist | Per-area `DOCUMENTED` / `PARTIALLY_DOCUMENTED` / `UNDOCUMENTED` / `STALE` / `UNKNOWN`; candidates; duplicates; Function Map delta; dependency gaps from registry edges only; change records; inspectable metrics (no overall score) | None. Computed in process | `GET /api/founder/knowledge/coverage` · `/coverage/changes` | Yes (`_require_owner`) | No | IMPLEMENTED · EVIDENCED · on-demand AUTOMATED · not CONNECTED to governance write-paths · not AUTONOMOUS · **uncommitted** |
| 3 | Bidirectional forensic (KC→Code / Code→KC / claims) | No dedicated report in repo. Bidirectional *behavior* is split: Code→KC in Phase 2 `classify_area`; KC→Code / claims in Phase 4 `verify_claim` / `historical_area`; product-vs-knowledge matrix in Phase 5 | None as Phase 3 | None as Phase 3 | N/A | No | DOCUMENTED only in Phase 6 prose and this file. **Capability PARTIALLY IMPLEMENTED inside Phases 2/4/5. Phase 3 sensor ABSENT as a named module** |
| 4 | Git provenance | First/last seen; origin `EMERGENT` / `CURSOR` / `HUMAN` / `UNKNOWN`; pickaxe mentions; claim provenance; Function Map / MPS historical delta; migration trace | None. Derived from Git each call. No duplicate Git store | `GET /api/founder/knowledge/coverage/history` | Yes | No | IMPLEMENTED · EVIDENCED · on-demand · UI PARTIAL (history piggybacks on `/coverage`) · **uncommitted** |
| 5 | Migration reconciliation | Emergent/origin/local exclusive commits; three-state matrix; working-tree buckets; file-level location; canonical conflict rows with `winner_chosen: False`; in-memory Founder decision queue | None. Computed in process | `GET /api/founder/knowledge/coverage/reconciliation` | Yes | No | IMPLEMENTED · EVIDENCED · API exists · **UI NOT CONNECTED** · queue not persisted · **uncommitted** |
| 6 | Governance integration + generated-audit protection | Written alignment audit; `is_generated_phase_audit()` excludes `PHASE_*AUDIT*` filenames from coverage mentions | Phase 6 file on disk under `docs/audits/` (untracked). Exclusion is code in Phase 2 | No Phase 6 API | File is in KC tree (Founder-visible). Exclusion is automatic when coverage runs | No (protection prevents self-satisfaction; does not rewrite canon) | Phase 6 report DOCUMENTED/IMPLEMENTED as a file. Protection IMPLEMENTED in coverage. Not a governance consumer |

### 4.1 Per-phase A–J

#### Phase 2

| Question | Finding | Class |
|---|---|---|
| A. Observes | 10 `WATCH_AREAS` (7B, 8B, 9C, 10C, Building Identity, Trust Boundary, Source Ledger, path alignment, Document Vault, HartaBlocuri) plus Function Map / Canonical / SSOT / MPS text | FACT |
| B. Produces | Coverage statuses, candidates (never canonical), duplicate groups, FN drift delta, registry dependency rows, git-status change records, health metric counts | FACT |
| C. Stored | Not stored | FACT |
| D. API | `/coverage`, `/coverage/changes` | FACT |
| E. Persist vs compute | Compute on demand | FACT |
| F. Registry relationship | Reads `enterprise_registry.json`. Has no node of its own. Some watch areas have `registry_node_ids`; several are empty | FACT |
| G. Governance can consume? | Only if a human or another system calls the API. No consumer in D116/D149/D161/D162/FN-021/PREFLIGHT/MPS writers | FACT |
| H. Founder-only | Yes at HTTP. Python functions are importable without auth | FACT |
| I. Mutates | No | FACT |
| J. Autonomous | No | FACT |

#### Phase 3

| Question | Finding | Class |
|---|---|---|
| A–J | No Phase 3 engine, route, test file, or `docs/audits/PHASE_3_*` report exists | FACT |
| — | Bidirectional checks exist only as functions inside Phases 2, 4, and 5 | FACT |
| — | Treating “Phase 3” as an independent sensor would invent a node | INFERENCE |

#### Phase 4

| Question | Finding | Class |
|---|---|---|
| A. Observes | Git log / pickaxe / authors / subjects; coverage areas; seeded `PROVENANCE_CLAIMS` | FACT |
| B. Produces | Origin labels EMERGENT/CURSOR/HUMAN/UNKNOWN; timelines; claim verification; FN/MPS history deltas | FACT |
| C–E | Not stored; computed; Git is the index | FACT |
| D. API | `/coverage/history`; also `attach_history()` mutates the in-memory Phase 2 dict only | FACT |
| F. Registry | Reads the same files as Phase 2. No history node | FACT |
| G–J | Same as Phase 2: Founder HTTP, no canon write, no autonomy | FACT |

#### Phase 5

| Question | Finding | Class |
|---|---|---|
| A. Observes | `emergent/main`, `origin/main`, HEAD, working tree, canonical conflict specs | FACT |
| B. Produces | Three-state matrix, commit inspections, file-level locations, `canonical_conflicts` with `winner_chosen: False`, `founder_decision_queue` list | FACT |
| C. Stored | Queue is a function return, not a journal | FACT |
| D. API | `/coverage/reconciliation` | FACT |
| G. Governance consume | No writer of Conflict Resolution Notes, PREFLIGHT events, or `admin_approvals` | FACT |
| I. Mutates | `winner_chosen` is hardcoded False. Tests snapshot MPS bytes before/after | FACT |

#### Phase 6

| Question | Finding | Class |
|---|---|---|
| A. Observes | Governance documents vs Phase 2–5 (written audit) | FACT |
| B. Produces | `PHASE_6_GOVERNANCE_INTEGRATION_AUDIT.md` | FACT |
| C. Stored | Untracked file under `docs/audits/` | FACT |
| F. Registry | No Phase 6 node | FACT |
| Protection | `is_generated_phase_audit` skips `PHASE_*AUDIT*` from coverage corpus | FACT |
| I. Mutates canon | No | FACT |

---

## 5. Evidence Flow Map

```
REALITY / CODE / GIT / TESTS
        ↓  CONNECTED
KC OBSERVATION  (filesystem SSOT + watchlist + Git)
        ↓  CONNECTED
PHASE 2–6 EVIDENCE  (in-memory JSON reports)
        ↓  PARTIAL  (Founder UI sees Phase 2+4; Phase 5 API unused by UI)
EXISTING GOVERNANCE  (MKG, D116, D149, D161, D162, FN-021, registries)
        ↓  NOT CONNECTED
FOUNDER GATE  (MKG §11 / PREFLIGHT / FG-0 — three objects, none ingest Phase 2–6)
        ↓  NOT CONNECTED
CANONICAL DECISION
        ↓  UNKNOWN as a closed loop  (humans may still edit files outside this chain)
PRODUCT / CODE
        ↓  CONNECTED  (next coverage run will see new files)
NEW EVIDENCE
```

| Connection | Classification | Evidence |
|---|---|---|
| Reality → KC Observation | CONNECTED | `knowledge_center._all_files()` reads `memory/` + `docs/`; coverage reads implementations/tests; history/reconciliation call Git |
| KC Observation → Phase 2–6 Evidence | CONNECTED | `build_coverage_report` / `build_history_report` / `build_reconciliation_report` |
| Phase 2 Evidence → KC UI | CONNECTED | `KnowledgeCenter.jsx` `ax.get('/api/founder/knowledge/coverage')` |
| Phase 4 Evidence → KC UI | PARTIAL | History is attached by `attach_history`; `/coverage/history` is registered but not called by the UI |
| Phase 5 Evidence → KC UI | NOT CONNECTED | No `/coverage/reconciliation` string in `KnowledgeCenter.jsx` |
| Phase 3 Evidence → anything | NOT CONNECTED | No Phase 3 artifact |
| Phase 2–6 → enterprise_registry | NOT CONNECTED | Sensors read the registry. Registry has no Phase 2–6 nodes or edges |
| Phase 2–6 → D161 reports | NOT CONNECTED | D161 labels appear in `lead_followup.py`, not in coverage/history/reconciliation payloads |
| Phase 2–6 → D116 | NOT CONNECTED | D116 has no engine to consume them |
| Phase 2–6 → D149 | NOT CONNECTED | D149 has no engine |
| Phase 2–6 → PREFLIGHT | NOT CONNECTED | PREFLIGHT is a markdown protocol. No import of coverage |
| Phase 2–6 → FG-0 Founder Gate | NOT CONNECTED | FG-0 slugs are financial/data/security/governance *product* actions. No coverage slug. `enforcement_active: False` |
| Phase 2–6 → MKG §7.4 Notes | NOT CONNECTED | Zero Conflict Resolution Note files. Queue is ephemeral |
| Phase 2–6 → D162 / `learning_engine.py` | NOT CONNECTED | Learning scans `ai_decision_ledger` commercial outcomes |
| Phase 2–6 → FN-021 | NOT CONNECTED | Loop observes Analytics + `admin_ai_findings` pattern `stale_project`. Comment says “Knowledge Center” but the collection is operational findings, not KC coverage |
| Phase 2–6 → MPS | NOT CONNECTED | Coverage *reads* `MASTER_PLATFORM_STATE.md`. Nothing writes coverage metrics into MPS |
| Phase 2–6 → Function Map | PARTIAL | Coverage *reads* FN text and proposes a delta. It does not write FN-003’s missing `/coverage*` APIs |
| Founder Gate → Canonical Decision | PARTIAL | MKG/PREFLIGHT describe the stop. No ticket/queue object is created from Phase 5 conflicts |
| Canonical Decision → Product | UNKNOWN as automation | Humans can edit. No closed-loop writer from this chain |
| Product → New Evidence | CONNECTED | Next on-demand run re-observes Git and files |

**Where the chain currently stops:** after Phase 2–6 JSON is returned to a Founder HTTP client (and, for Phase 2/4, rendered). It does not enter governance consumers.

---

## 6. Enterprise Registry Integration

**FACT:**
`enterprise_registry.json` version 1.0 states: only proven relationships from real code. Edges carry `evidence`, `evidence_type`, `confidence`, `verification_status`, `last_verified` (KC-related edges last verified 2026-07-26).

**FACT:**
Existing KC-related nodes (capability present *and* registered):

| Node | Type | Ref |
|---|---|---|
| `engine:knowledge_center` | engine | `backend/routes/knowledge_center.py` |
| `api:knowledge_tree` | api | `GET /api/founder/knowledge/*` |
| `dash:knowledge_center_page` | dashboard | `KnowledgeCenter.jsx` |
| `doc:execution_order_002` | document | EO 002 |
| `doc:memory_rules` | document | Memory Rule 001 |
| `doc:d161` | document | Truth Engine directive |
| `engine:learning_engine` | engine | `learning_engine.py` |

**FACT:**
Proven KC edges: `e41` Memory Rules → KC; `e42` EO 002 → KC; `e43` KC → API; `e44` API → dashboard. D161 proven edge `e27` is `doc:d161` → `metric:report_24h` (lead follow-up), **not** toward coverage.

**FACT:**
Grep of `enterprise_registry.json` finds no `knowledge_coverage`, `knowledge_history`, `knowledge_reconciliation`, `MASTER_KNOWLEDGE_GOVERNANCE`, `PREFLIGHT`, `D116`, `D149`, `D162`, or `FN-021`.

| Capability | Registry Node | Proven Relationship | Evidence | Missing Wiring |
|---|---|---|---|---|
| Phase 2 coverage | **Absent** | None | No node id; capability exists as untracked module | Node would be needed *only if* governance traversal must see the sensor. Capability is not absent |
| Phase 3 bidirectional | **Absent** | None | No module, so a node would be a false proven edge | Do not invent a node for a missing module |
| Phase 4 history | **Absent** | None | Same as Phase 2 | Optional child of `engine:knowledge_center` if Founder wants traversal |
| Phase 5 reconciliation | **Absent** | None | Same | Same |
| Phase 6 audit file | **Absent** | None | File exists under `docs/audits/` | T3 generated audit; MKG does not require a registry node for every T3 file |
| D161 | Present `doc:d161` | Proven to follow-up 24h report only | `e27` | No edge from D161 to KC coverage |
| D116 | **Absent** | None | Directive file exists; no engine | Registry-node absence ≠ directive absence |
| D149 | **Absent** | None | Directive file exists; no engine | Same |
| D162 | **Absent** as doc node | `engine:learning_engine` exists | Outcome scan proven to `ai_decision_ledger` / `ai_outcomes` | Learning engine node is not a D162 document node and does not cite KC |
| FN-021 | **Absent** | None | Loop file + Function Map row exist | Registry-node absence ≠ function absence |
| PREFLIGHT | **Absent** | None | File exists | Same |

**INFERENCE:**
Phase 2–6 cannot participate in registry-based relationship traversal because they have no proven edges. That is a wiring/registry gap, not proof that the sensors are invalid.

**PROPOSAL:**
If the Founder wants traversal, add nodes as children of the *existing* `engine:knowledge_center` after the files are committed, with evidence pointing at the real modules. Do not create a second registry.

**UNKNOWN:**
Whether the Founder wants those nodes at all. EO 002 already warned against creating new governance documents without need. A registry node is not a new engine, but it is a Founder-owned proven-edge decision.

---

## 7. Truth Engine Integration

### 7.1 What D161 actually is

**FACT:**
D161 is a Board Directive, not a Python package. Required report labels:

`Measured` · `Observed` · `Estimated` · `Predicted` · `Assumed` · `Generated`

Companion rules: if evidence disappears → `UNKNOWN`, never SUCCESS; Estimated must carry confidence; predictions must not be reported as results.

### 7.2 Where those labels already exist

| Location | Labels used | Proven? |
|---|---|---|
| `lead_followup.build_execution_report_24h` | `measured` list + `estimated` with formula/confidence; `truth_note` cites D161 | Yes · registry `e27` |
| `knowledge_center.py` document health | `confidence`: `Measured` if registry-referenced, else `Verified` if Founder verbatim, else `Estimated` | Partial. `Verified` is **not** a D161 class |
| Phase 2–5 reports | Coverage/recon/origin vocabularies, not D161 classes | No D161 mapping |

### 7.3 Can Phase 2–6 outputs already be represented as D161 classes?

| Candidate mapping | Supported today? | Class |
|---|---|---|
| Git first-seen / commit hashes / file existence | Could be **Measured** (real Git/fs events) | INFERENCE — no code maps them |
| Coverage status DOCUMENTED/UNDOCUMENTED | Heuristic over needles — closest to **Estimated** or **Generated** | INFERENCE |
| Origin EMERGENT/CURSOR/HUMAN | Needle/author heuristic — **Estimated**, not Measured | INFERENCE |
| Seeded claims in Phase 4 | Mix of Measured (file exists) and Estimated (iteration from filename) | INFERENCE |
| Phase 5 `winner_chosen: False` | **Observed** only if a human recorded it; today it is Generated by the auditor | INFERENCE |
| UNKNOWN | Already used in Phase 2–5; compatible with D161 “evidence disappeared / unproven” | FACT that the word exists; UNKNOWN whether Founder wants it unified |

**FACT:**
No function in Phase 2–6 emits `evidence_classification` or `truth_note`.

**FACT:**
This audit does not create Truth Engine v2 and does not promote findings to canonical truth.

### 7.4 Smallest integration point with the *existing* architecture

**PROPOSAL:**
Add an optional `d161` field on the *existing* coverage/history/reconciliation JSON, using the existing D161 vocabulary and the existing “nu inferăm” rule: only attach a class when the source is named (Git object, file stat, registry edge). Do not build `truth_engine.py`. Do not write MPS. Do not auto-promote.

**UNKNOWN:**
Whether the Founder wants that field. Without it, Phase 2–6 remain evidential but outside D161’s report contract.

---

## 8. D116 / D149 Integration

### 8.1 D116 Continuous Platform Audit Engine

| Question | Answer | Class |
|---|---|---|
| Documentation only? | Yes, as an engine | FACT |
| Implementation file? | No `platform_audit_engine.py` / equivalent | FACT |
| Inputs | Specified as the whole platform (pages, APIs, docs, directives, …) | FACT (directive text) |
| Outputs | Monthly report; classes Already Exists / Partially Exists / Duplicate / Unused / Deprecated / Conflicting / Incomplete / Missing | FACT (directive text) |
| Can Phase 2–6 already be consumed? | No consumer exists | FACT |
| Minimum missing connection | A reader — PREFLIGHT checklist or a T3 Platform Audit section — that *cites* coverage statuses instead of a new engine | PROPOSAL |

**INFERENCE:**
Phase 2 statuses (`DOCUMENTED` / `PARTIALLY_DOCUMENTED` / `UNDOCUMENTED` / `STALE` / `DUPLICATE_CANDIDATE` / `CONFLICT_CANDIDATE`) are near-synonyms of D116’s classify list for the *knowledge* slice only. They are not D116.

### 8.2 D149 Continuous Alignment Engine

| Question | Answer | Class |
|---|---|---|
| Documentation only? | Yes | FACT |
| Implementation file? | No `alignment_engine.py` | FACT |
| Inputs / outputs | Align Vision…Knowledge…CX. No schema in code | FACT |
| Can Phase 2–6 be consumed? | No | FACT |
| Minimum missing connection | None until D149 has a consumer. Do not implement D149 to wire coverage | PROPOSAL |

**FACT:**
`memory/PLATFORM_AUDIT_2026.md` is a dated narrative audit, not a D116 engine.

**PROPOSAL:**
Do not create Alignment Engine v2 or Platform Audit Engine v2. If D116 classification is needed, reuse Phase 2’s existing classify list as *supporting evidence* inside PREFLIGHT / a human T3 audit.

---

## 9. Learning / Autonomy Integration

### 9.1 D162 and `learning_engine.py`

**FACT:**
D162 requires every completed action to answer six learning questions and forbids unevidenced learning from entering Enterprise Memory.

**FACT:**
`backend/learning_engine.py` implements a last-touch commercial outcome scan over `ai_decision_ledger` (engagement / conversion / request / revenue). Registry edges `e36` / `e37` prove writes to `ai_decision_ledger` and `ai_outcomes`.

**FACT:**
`learning_engine.py` does not import `knowledge_coverage`, `knowledge_history`, or `knowledge_reconciliation`.

**INFERENCE:**
`learning_engine.py` is a **partial implementation** of D162 in the commercial-lead domain. It is not a second learning engine. It also does not observe KC evidence.

### 9.2 FN-021 / `autonomy/loop.py`

**FACT:**
FN-021 is VERIFIED in Function Map. Loop: OBSERVE Analytics → FINDING `admin_ai_findings` → ACT `admin_todos` / `admin_approvals` → VERIFY → LEARN.

**FACT:**
A second observer, `observe_knowledge_findings()`, reads Mongo `admin_ai_findings` where `pattern ∈ {stale_project}`. The comment calls this “Knowledge Center.” The query does not read `memory/`, coverage reports, or Phase 5 conflicts.

**FACT:**
Human gate for MEDIUM/HIGH is `admin_approvals`, not FG-0 and not MKG Conflict Resolution Notes.

**FACT:**
Phase 2–6 cannot currently enter this pipeline: there is no writer from coverage into `admin_ai_findings`.

### 9.3 Outcome

| Path | Observes KC Phase 2–6? |
|---|---|
| `learning_engine.run_outcome_scan` | No |
| FN-021 analytics detectors | No |
| FN-021 `observe_knowledge_findings` | No (different “knowledge”) |
| `autonomy/engine.py` scoring | Counts `admin_ai_findings`, not coverage |

**PROPOSAL:**
Do not create another learning engine or autonomy loop. If KC evidence should be learned, the minimal path is a Founder-approved, non-destructive finding type written into the *existing* `admin_ai_findings` with a distinct `source` (not `analytics_loop`) and no SAFE auto-act on canonical files.

**UNKNOWN:**
Whether the Founder wants operational autonomy to see documentation drift at all.

---

## 10. Conflict Resolution Integration

### 10.1 What MKG §7.4 actually says

**FACT:**
If tier precedence, SSOT, and recency all fail, the conflict escalates to the Founder for a **Conflict Resolution Note** — a short document filed in Governance, referenced by both conflicting documents. MKG §11.4: resolving such a Note requires human approval. MKG §7.5: the losing document is never silently overwritten.

**FACT:**
`MASTER_KNOWLEDGE_GOVERNANCE_AUDIT.md` records that Conflict Resolution Note has no formal document class and no SLA (G7, M6).

**FACT:**
Repository search for `Conflict Resolution Note` / `conflict_resolution_note` / `CONFLICT_RESOLUTION` in `*.py` returned **zero** files. Glob for `*CONFLICT*NOTE*` returned **zero** files.

### 10.2 What Phase 2–6 actually do with conflicts

| Observed conflict type | SOURCE | CONFLICT | CURRENT HANDLING | CANONICAL AUTHORITY | FOUNDER ACTION REQUIRED |
|---|---|---|---|---|---|
| MPS family (3 files readable as living state) | Phase 5 `CANONICAL_CONFLICT_SPECS` `mps_family` | LIVING_VS_DATED_SNAPSHOT | Row in in-memory `canonical_conflicts`; `winner_chosen: False` | MKG §7 + SSOT row + PREFLIGHT §9 | Yes — which file is living |
| FN-005 path vs `DocumentVault.jsx` | Phase 5 `function_map_vs_code` | REGISTRY_PATH_VS_IMPLEMENTATION | Same | Function Map owner (Founder) | Yes — living map vs frozen snapshot |
| SSOT vs Canonical vs Function Map | Phase 5 `ssot_vs_canonical_vs_fn` | MULTI_REGISTRY_AUTHORITY | Same | MKG + each registry’s own charter | Yes — authority for implementation rows |
| HartaBlocuri integration vs Source Ledger | Phase 5 `hartablocuri_split` | Doc vs later module | Same | Integration doc owner | Yes |
| HISTORICAL_COPY / VERSION_COPY duplicates | Phase 2 `detect_duplicates` → Phase 5 rows | Duplicate family | Listed; “do not delete” | MKG §7.5 traceability | Yes before any archive |
| Coverage STALE / UNDOCUMENTED | Phase 2 classify | Drift, not always a §7 conflict | Candidate + backlog | MKG §11.2 AI may *suggest* | Yes before any new Active doc |
| Emergent-only BSON dump | Phase 5 three-state | REMOTE_ONLY product | Queue item `bson_dump_remote` | Product + remotes | Yes — cherry-pick or leave |
| Uncommitted Phase 2–5 engines | Working tree | Not a document conflict | Queue item `commit_phase24` | Founder commit policy | Yes — commit or leave |

**FACT:**
Current handling produces **nothing persistent**: no Conflict Resolution Note, no decision-journal row, no Founder Gate event, no `admin_approvals` item. Only an API JSON field and (for Phase 2) UI badges.

**PROPOSAL:**
When the Founder resolves one of the above, file a MKG §7.4 Note by hand (or by authorized Draft). Do not auto-resolve. Do not rewrite the losing document.

---

## 11. Documentation Coverage Integration

Three different “coverage” ideas exist. They are not wired together.

| Metric | Where defined | Implemented? | Calculated live? | Exposed? | Connected to MPS? | Displayed in KC? | Consumed by governance? |
|---|---|---|---|---|---|---|---|
| MKG §10 **Documentation Coverage** | `% of implemented modules with at least one referenced doc`; target ≥ 90%. MKG: “Implementation is out of scope for this document.” | Documented formula only | No engine of this formula | No API | MKG §10.2 says metrics *may* appear in MPS snapshots. No live feed | No | No |
| MPS Living Governance **Knowledge Coverage** / **Documentation Coverage** | `MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md` §2.6 / Part 4 | Static estimates (~75% / ~70%) written 2026-07-31 | No | Only as markdown numbers | They *are* inside a dated living-governance file. SSOT names that file as MPS OwnerDocument | Not as KC Coverage tab | Human-readable only |
| Phase 2 `metrics.knowledge_coverage` | Counts of watch-area statuses; `overall_score: None` | Yes | On demand | `/coverage` | **No.** Phase 2 *reads* `MASTER_PLATFORM_STATE.md` (a different path than the SSOT OwnerDocument) and flags silence as STALE. It does not write MPS | Yes, Coverage / Drift metrics | No writer |

**FACT:**
SSOT topic “Master Platform State” → `memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md`. Phase 2 constant `DOC_PLATFORM_STATE` → `memory/audits/MASTER_PLATFORM_STATE.md`. That is a wiring/authority mismatch already listed as a Phase 5 conflict.

**FACT:**
`tenancy.coverage_report` and `/admin/research-coverage` are different products (tenant isolation / research). Not MKG documentation coverage.

**INFERENCE:**
The MKG Documentation Coverage metric is DOCUMENTED, not IMPLEMENTED as a calculator, not CONNECTED to MPS as a live value. Phase 2 is a *different* implemented watchlist metric. Creating a second documentation-coverage system would be a duplicate. The gap is wiring, not a missing concept.

**PROPOSAL:**
If MPS should show a live number, reuse Phase 2’s inspectable counts (or a Founder-approved subset that matches the MKG definition). Do not add `documentation_coverage_v2.py`. Do not auto-overwrite MPS.

---

## 12. Duplicate Architecture Check

Inspected by behavior, not by name alone.

| Apparent pair | What each actually does | Classification |
|---|---|---|
| D116 vs Phase 2 | D116 = directive listing platform-wide classes. Phase 2 = watchlist coverage detector | **DOCUMENTATION ONLY** (D116) vs **PARTIAL IMPLEMENTATION** of the knowledge slice (Phase 2). **DIFFERENT SCOPE** |
| D149 vs Phase 2–5 | D149 = align Vision…CX. Phase 2–5 = knowledge/git evidence | **DOCUMENTATION ONLY**. **DIFFERENT SCOPE** |
| D161 vs Phase 2 statuses | D161 = truth class of a number. Phase 2 = documentation state of an area | **DIFFERENT SCOPE**. Same word “UNKNOWN” only |
| KC health `Measured/Verified/Estimated` vs D161 | Health score confidence; `Verified` is extra-vocabulary | **PARTIAL IMPLEMENTATION** / **DIFFERENT SCOPE** |
| D162 vs `learning_engine.py` | Directive is enterprise learning. Code is commercial last-touch outcomes | **PARTIAL IMPLEMENTATION**. **DIFFERENT SCOPE** from KC |
| D162 vs FN-021 LEARN | Loop “learn” auto-resolves operational findings | **DIFFERENT SCOPE** |
| FN-021 `observe_knowledge_findings` vs Phase 2 | Mongo `stale_project` vs filesystem coverage | **SAME SYSTEM / DIFFERENT NAME** is false. **DIFFERENT SCOPE**. Name collision only |
| D153 Decision Journal vs `ai_decision_ledger` | Journal is strategic decisions. Ledger is AI follow-up / execution reports | **DIFFERENT SCOPE**. Journal is **DOCUMENTATION ONLY** |
| D132 Executive Memory vs KC filesystem | Directive to store lessons. KC is the document archive | **DOCUMENTATION ONLY** vs **IMPLEMENTED** archive. Not the same engine |
| D146 Synthesis vs coverage report | Directive to merge evidence into one conclusion. Coverage refuses an overall score | **DOCUMENTATION ONLY**. Coverage deliberately avoids synthesis-as-score |
| D167 Genome vs anything | Ten genes as doctrine | **DOCUMENTATION ONLY**. No genome engine |
| D126 Digital Property Genome vs D167 | Property DNA vs enterprise genes | **DIFFERENT SCOPE** |
| FG-0 vs PREFLIGHT vs MKG §11 | Product dual-verify vs agent protocol vs document promotion | **DIFFERENT SCOPE** (three gates) |
| Phase 2 coverage vs FN-013 Research Coverage vs `tenancy.coverage_report` | Watchlist vs research vs tenant | **DIFFERENT SCOPE** |
| Phase 5 queue vs D153 Journal vs `admin_approvals` | Ephemeral list vs (absent) journal vs operational approvals | **PARTIAL IMPLEMENTATION** (queue) · **DOCUMENTATION ONLY** (D153) · **IMPLEMENTED** (approvals, unused by KC) |
| `PLATFORM_AUDIT_2026.md` vs D116 | One dated narrative | **DOCUMENTATION ONLY** |
| Phase 6 audit vs this Phase 7 audit | Integration vs wiring | **DIFFERENT SCOPE**. Not a second governance engine |
| Enterprise registry vs SSOT vs Canonical vs Function Map | Proven runtime graph vs topic owners vs system canon vs FN rows | **DIFFERENT SCOPE**. Phase 5 already flags multi-registry authority as a conflict, not a merge |

**FACT:**
No second Truth Engine, Alignment Engine, or Autonomy Loop was found as code.

---

## 13. Governance Boundary Check

The following remain Founder-controlled. No Phase 2–6 code grants them to an agent.

| Boundary | Still Founder-controlled? | Evidence |
|---|---|---|
| Canonical promotion | Yes | `CANONICAL_PROMOTION_ALLOWED = False`; candidates explicitly non-canonical |
| Conflict resolution | Yes | `winner_chosen: False`; no Note writer |
| Governance authority changes | Yes | No writes to MKG / hierarchy |
| SSOT changes | Yes | SSOT only read |
| Registry authority changes | Yes | `enterprise_registry.json` not written by sensors |
| Constitutional changes | Yes | No T0 writes |
| Board Directive changes | Yes | Directives only read |
| Execution Order changes | Yes | EO files only read |
| Autonomous rewriting of canonical knowledge | Yes | `engine_writes_nothing`; tests snapshot MPS/FN bytes |

**FACT:**
FG-0 does not enforce even its own 13 product actions (`enforcement_active: False`).

**FACT:**
The audit system DETECTS and REPORTS. It does not DECIDE canonical truth. It does not silently mutate governance.

This Phase 7 file is itself a T3 generated audit. `is_generated_phase_audit` will exclude it from coverage mentions if coverage is run after this file exists. That is protection, not promotion.

---

## 14. Wiring Gap Matrix

| Gap | Evidence | Existing Component | Minimal Connection | Risk | Founder Decision Required |
|---|---|---|---|---|---|
| Phase 2–6 uncommitted | `git status` untracked engines | Git | Commit or leave working-tree-only | Engines can be lost if the tree is cleaned | Yes |
| No registry nodes for Phase 2/4/5 | Grep registry empty | `enterprise_registry.json` + existing `engine:knowledge_center` | Optional proven nodes/edges after commit | False completeness if nodes added without evidence | Yes |
| Phase 5 API unused by UI | No `/reconciliation` in JSX | `KnowledgeCenter.jsx` | Call existing GET | Low (display only) | No (unless UI policy requires it) |
| Phase 4 dedicated API unused | UI uses attached history only | Same | Optional; already PARTIAL | Low | No |
| Phase 3 named sensor missing | No module | Phases 2/4/5 functions | Do **not** add a module; document the split | Inventing Phase 3 as a node would be a false edge | Yes only if Founder wants a named Phase 3 artifact |
| D161 labels not on KC reports | No `evidence_classification` in sensors | D161 vocabulary + `lead_followup` pattern | Optional field on existing JSON | Mislabeling heuristic as Measured | Yes |
| D116/D149 have no engine | No py files | PREFLIGHT + Phase 2 classify | Cite coverage in PREFLIGHT answers; do not build engines | Duplicate architecture if engines are created | Yes only if Founder wants D116/D149 implemented as code (this audit recommends no) |
| PREFLIGHT does not call coverage | Markdown protocol | `PREFLIGHT_GATE.md` + `/coverage` | Agent reads existing API/report during Change Intent | Process drift if ignored | No code change required |
| FG-0 unrelated to KC conflicts | Slug list + `enforcement_active: False` | MKG §11 / PREFLIGHT | Keep FG-0 for product actions; use MKG Notes for knowledge conflicts | Conflating gates | Yes if someone proposes KC slugs on FG-0 |
| Conflicts not persisted | In-memory queue; zero Notes | MKG §7.4 | Founder-authored Note when a conflict is actually decided | Silent loss of decisions | Yes at decision time |
| FN-021 does not see coverage | `stale_project` only | `admin_ai_findings` | Optional distinct source; no SAFE act on canon | Autonomy over documents | Yes |
| Learning engine ignores KC | Outcome scan on ledger only | `learning_engine.py` | Do not extend unless Founder wants KC outcomes tracked | Scope creep / second brain | Yes |
| Documentation coverage ≠ MPS live metric | MKG formula unimplemented; MPS has 2026-07-31 estimates; Phase 2 counts watch areas | MKG §10 + Phase 2 metrics + MPS | Reuse Phase 2 counts as *input to a human MPS edit* | Second coverage system; wrong MPS file | Yes (which MPS file + which formula) |
| SSOT MPS path ≠ Phase 2 MPS path | SSOT → Living Governance 2026-07-31; coverage reads `MASTER_PLATFORM_STATE.md` | SSOT + Phase 5 conflict `mps_family` | Founder names the living file; then point the reader at it | Dual living state | Yes |
| FN-003 omits `/coverage*` | Function Map API list stops at `/architecture` | `FUNCTION_MAP.md` | Founder-authored delta if FN is living | Stale map | Yes (living vs historical FN) |
| Generated audits in KC tree | Phase 6/7 files under `docs/` | `is_generated_phase_audit` | Keep exclusion. Do not count audits as product docs | Self-satisfying coverage if exclusion removed | No |

---

## 15. Recommended Minimal Wiring

No implementation code. Minimum architecture if the Founder later authorizes work:

1. **Reuse, do not replace.** Keep `knowledge_coverage.py`, `knowledge_history.py`, `knowledge_reconciliation.py`, existing KC routes, existing D161 label set, existing PREFLIGHT text, existing MKG §7.4 Note class, existing `enterprise_registry.json`, existing FN-021 loop, existing `learning_engine.py`.
2. **Preserve evidence.** Continue compute-on-demand from Git/filesystem. Do not create a parallel evidence database unless the Founder later requires persistence. If persistence is wanted, the existing `ai_decision_ledger` / a T3 snapshot file is closer than a new store — but KC conflicts are not commercial outcomes; do not overload the ledger without a decision.
3. **One display completion (optional, non-governance):** Founder-only UI already has Coverage/Drift. Point it at the *existing* `/coverage/reconciliation` GET if the Founder wants to see Phase 5 without a new engine.
4. **D161 adapter, not Truth Engine v2:** If reports must speak D161, add a classification object on the existing payloads. Measured only for Git/fs/registry-backed fields. Heuristic statuses stay Estimated/Generated. UNKNOWN stays UNKNOWN.
5. **PREFLIGHT as the consumer, not D116-the-engine:** Agents already must search Canonical / SSOT / Function Map / MPS. Add “read `/coverage` statuses for the touched watch area” to that human protocol. That is the D116 reuse-before-build check for the knowledge slice.
6. **Founder Gate:** Do not attach KC conflicts to FG-0 SMS/email. Use MKG §11 / PREFLIGHT STOP / a written Conflict Resolution Note. FG-0 remains the product dual-verification foundation.
7. **Registry:** After a commit decision, optional proven nodes under `engine:knowledge_center`. No inferred edges. No node for Phase 3 until a Phase 3 module exists.
8. **MPS / Documentation Coverage:** Do not auto-write MPS. If a number is needed, a human MPS edit may cite Phase 2 inspectable counts. Resolve the living-file conflict first.
9. **Autonomy / learning:** Do not feed coverage into SAFE auto-todos. If a finding is wanted, it must be MEDIUM/HIGH or Founder-only display. No autonomous canonical rewrite.
10. **No new governance engines.**

Priority order encoded above: existing reuse → minimal integration → evidence preservation → Founder Gate (the MKG/PREFLIGHT one) → no new engines.

---

## 16. Founder Decision Queue

Only decisions that require Founder authority. Not implementation tickets.

| ID | Decision | Why Founder |
|---|---|---|
| `commit_phase246` | Commit Phase 2/4/5 engines, tests, KC route/UI, and Phase 6–7 audit files — or leave them uncommitted | Recoverability vs. keeping sensors experimental. Does not canonicalize product doctrine |
| `mps_living_file` | Which MPS file is living, and must September code appear in it? | SSOT vs coverage reader vs dated copies. MKG §7 |
| `fn_living_or_historical` | Is Function Map a living map or a 2026-06 snapshot? | Controls whether missing `/coverage*` and 7B–10C rows are defects |
| `doc_coverage_formula` | Which documentation-coverage number is official: MKG §10, MPS 2026-07-31 estimate, or Phase 2 watch-area counts? | Prevents a second metric becoming silent canon |
| `registry_nodes_for_sensors` | Represent Phase 2/4/5 as proven registry nodes after commit? | Registry is Founder-owned proven graph. Absence ≠ invalid sensors |
| `d161_on_kc_reports` | Attach D161 classes to coverage/history/reconciliation fields? | Changes how truth is *labeled*, not what is true |
| `persist_conflicts` | When a Phase 5 conflict is decided, file a MKG §7.4 Note (and where)? | Note resolution is mandatory-human under MKG §11.4 |
| `fn021_sees_kc` | May FN-021 observe documentation drift at all? | Autonomy boundary. Default from this audit: no SAFE mutation of canon |
| `phase3_named_artifact` | Should Phase 3 remain a split of 2/4/5, or become a named document only? | Naming a missing module as a registry capability would be false |
| `d116_d149_stay_docs` | Keep D116/D149 as directives without engines? | Creating those engines would duplicate Phase 2 + PREFLIGHT |

**Not manufactured:** whether 7B/8B/9C get dedicated KC documents, BSON dump cherry-pick, or 10B status — those remain on the Phase 5 queue and are product/knowledge content decisions, not wiring decisions. They are not repeated here except as already-open Phase 5 items the Founder still owns.

---

## 17. Final Classification

Classify the *current wiring system* separately. Do not combine into one score.

### DOCUMENTED

**Yes, largely.** MKG, GOVERNANCE_HIERARCHY, D116, D149, D161, D162, D153, PREFLIGHT, Function Map FN-003/FN-021, EO 002, Phase 6 audit, and this Phase 7 audit describe the intended chain. Phase 3 as a standalone phase is **not** documented as a repo artifact.

### IMPLEMENTED

**Partial.** Phase 2/4/5 sensors + Founder APIs + Phase 2 UI + generated-audit exclusion are implemented (uncommitted). D161 labels implemented for lead follow-up, not KC. FN-021 and `learning_engine.py` implemented for commercial/operational loops. D116, D149, D153, D132, D146, D167, MKG §10 calculator, Conflict Resolution Note workflow, FG-0 enforcement: **not implemented** as those names.

### EVIDENCED

**Yes, for the sensors.** Git, files, tests (39 passed this run), and registry edges for *other* systems evidence what exists. Phase 2–6 themselves have **no proven registry evidence**. UNKNOWN must not be read as false.

### CONNECTED

**No, as a governance loop.** Connected: Reality → Observation → Phase 2–6 JSON → (partial) KC UI. Not connected: Evidence → D116/D149/D161/D162/FN-021/PREFLIGHT/FG-0/MKG Notes/MPS write-path → Founder Gate → Canon.

### AUTOMATED

**On-demand only.** HTTP GET computes reports. No scheduler tick for coverage. FN-021 and lead-follow-up *are* scheduled, but they do not run these sensors. FG-0 does not automate approvals.

### AUTONOMOUS

**No.** Phase 2–6 cannot promote, resolve, or rewrite. FN-021 autonomy does not include KC canon. D156/D161 autonomous execution is lead follow-up, not knowledge governance.

---

### Closing classification block

**FACT:**
The chain that exists today is: reality is observable; observation is implemented; evidence is produced; governance is written; Founder authority is reserved; the sockets between evidence and governance are empty.

**EVIDENCE:**
Repository files and tests cited above. 39/39 Phase 2/4/5 tests passed. Canonical trees were not modified by this phase except the addition of this audit file under `docs/audits/`.

**INFERENCE:**
Implementation of “governance evidence wiring” is a connection problem, not a missing-brain problem.

**PROPOSAL:**
Authorize nothing from this file automatically. Review §16. Then, if desired, perform the smallest wiring in §15.

**UNKNOWN:**
Which of the §16 decisions the Founder will take.

---

*End of Phase 7. STOP. No wiring implemented. No commit. No publish. No deploy. No new engine.*
