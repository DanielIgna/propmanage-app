# PropManage — CHANGELOG (Knowledge Sync · Digital Twin)

Rol: jurnal cronologic al schimbărilor semnificative + sincronizărilor de cunoștințe. Documentele canonice (sursa de adevăr) rămân: `audits/PROPERTY_TWIN_CANONICAL_v1.0.md` (Digital Twin) și `audits/MASTER_PLATFORM_STATE.md` (stare platformă). Separă mereu: LIVE/DEPLOYED · PREVIEW/BUILT · PLANNED/NEXT · IDEA/FUTURE.

---

## 2026-06 · HartaBlocuri Phase 1 — Contextul clădirii + Admin Import Center + Typology prep — PREVIEW/BUILT
Continuare a integrării HartaBlocuri (aditiv, nedistructiv). Testat: iteration_222 — backend 8/8, frontend 100%.

**Contextul clădirii (client)** — `PropertyTechnicalRecord.jsx > HartaBlocuriCard`
- Card „Date externe HartaBlocuri — neverificate de PropManage" cu toate câmpurile (nume/adresă/localitate/cartier/lat-lng/an/regim/niveluri/apartamente/scări/lift/structură/eră/dezvoltator/finisaje/risc seismic/distribuție camere).
- Planuri = thumbnail-uri hotlink către hartablocuri.ro (tab nou, atribuire vizibilă). Poze absente în fișier.
- Backend: `_serialize_building` + `_serialize_hartablocuri` adaugă `hartablocuri`, `conflicts`, `typology` la `GET /api/properties/{id}/building-context`.

**Admin Import Center** — `/admin/hartablocuri` (`HartaBlocuriAdmin.jsx`), 4 tab-uri:
- Overview (statistici + rulare import dry-run/real, idempotent), Loturi Import (batches), Blocuri (filtre sursă all/propmanage/hartablocuri/both + status), Conflicte (rezolvare per câmp).
- Endpoint-uri noi: `GET /api/admin/hartablocuri/conflicts`, `GET .../buildings/{id}`, `POST .../buildings/{id}/conflicts/resolve`.
- Rezolvare conflict: `confirm`=valoarea HartaBlocuri devine activă; `reject`=rămâne PropManage. Ambele păstrează valoarea brută HB + `context.conflict_history[]` (fără ștergere).

**Typology Engine (DOAR pregătire date)** — `context.typology` cu `{raw, normalized, source}` pentru period/year/era/height_regime/structure/entrances/apartments/rooms_breakdown/neighborhood. Backfilled pe 3404 blocuri. Fără clasificare/UI activată.

**Knowledge Center**: doc nou `/app/memory/audits/HARTABLOCURI_INTEGRATION.md` (apare automat în Enterprise Knowledge Center, categoria Platform Audits).

**Garanții respectate**: Building Health / Twin Maturity / PVI / Cartea Casei / Digital Twin / abonamente NEATINSE. Adăugarea manuală de blocuri rămâne funcțională. Import EXCLUSIV județul Cluj.

**Rămas înainte de SEO programatic**: validare reală extinsă a datelor pe teren (opțional), apoi pagini publice SEO per bloc/cartier care consumă aceeași entitate Building.


## 2026-06 · HartaBlocuri Cluj — import + discovery public „Găsește-ți blocul" — PREVIEW/BUILT
Integrare aditivă a bazei externe HartaBlocuri Cluj în entitatea `buildings` existentă (NU sistem paralel).

**Import (`/app/backend/hartablocuri_import.py`)**
- Parsează foaia „Detalii blocuri" din `/app/backend/data/hartablocuri_cluj.xlsx`. Exclude rândurile `STERGE`/`DE ADĂUGAT` → **3406 înregistrări utile**.
- **Idempotent**: cheie `context.external_sources.hartablocuri.source_record_id` (hash md5 din nume+adresă+coordonate). Reimport ⇒ 0 blocuri noi (update in-place). Index sparse pe source_record_id + `context.norm_address`.
- **Matching cross-source**: adresă normalizată + proximitate coordonate ≤60m; adrese placeholder („Strada ?? nr. ?") NU sunt chei de matching → blocuri distincte. Rezultat: **UN Building cu 2 surse** (PropManage + HartaBlocuri), verificat manual (Phase 18).
- **Non-destructiv**: completează doar câmpuri goale în `context`; diferențele față de date manuale → `context.conflicts[]` (status review), NU suprascrie. Proveniență completă în `context.external_sources.hartablocuri` (raw + plan_urls/photo_urls, verification_status=neverificat). NU activează Digital Twin/Building Health/PVI.
- **Rezultat import real**: 3404 blocuri noi, 2 conflicte reale, 0 erori. Total `buildings` = 3405 (3404 HB + 1 PropManage).
- Colecție nouă `import_batches` (Batch ID, source, file, total/imported/matched/new/duplicates/conflicts/errors).

**Endpoint-uri (`/app/backend/routes/hartablocuri.py`)**
- Public (fără auth): `GET /api/public/buildings/search` (q+city), `/cities`, `/{id}`.
- Admin: `POST /api/admin/hartablocuri/import` (suportă dry_run), `GET .../batches`, `GET .../stats`, `GET .../buildings` (filtre source: all/propmanage/hartablocuri/both · status: unverified/conflict/…).

**Frontend** — `components/BuildingDiscovery.jsx` montat în LandingPage (`App.js`) după `HouseHealthAxisLanding`. Căutare live → rezultate cu badge sursă + „Date externe — neverificate de PropManage" → link `/register?binvite=<id>` (reutilizează mecanismul binvite existent).

**Testare**: iteration_221.json — backend 14/14 PASS, frontend 11/11 criterii PASS, 0 issues.

**RĂMAS (P1, neînceput)**: Phase 7/8/9 UI — afișarea datelor HartaBlocuri + proveniență în „Contextul clădirii" (pagina proprietății) și filtrele sursă/status + panoul de import în „Administrare blocuri".


## 2026-09 · Google Ads tag (AW-857233494) + GDPR Consent Mode v2 — PREVIEW
- Adăugat gtag.js (Google Ads AW-857233494) în `frontend/public/index.html` cu **Google Consent Mode v2**: default `denied` pentru `ad_storage/ad_user_data/ad_personalization/analytics_storage`; citește alegerea salvată (`pm_cookie_consent_v1`) la load.
- `CookieBanner.jsx::persist()` trimite `gtag('consent','update',...)`: Marketing→`ad_*`, Statistice→`analytics_storage`. Verificat e2e (denied la prima vizită → granted la „Accept toate" → denied la „Refuz").
- NELEGAT de Analytics & Growth intern (acela = `/api/track` + `analytics_growth.py` + PostHog). Google Ads trimite doar în consola Google Ads (conversii/remarketing).
- ⚠️ De rezolvat: `LegalPages.jsx` afirmă „doar cookies strict necesare, fără remarketing" — contrazice noul tag Google Ads; PostHog se încarcă încă necondiționat (înainte de consimțământ).
- Necesită REDEPLOY pentru producție.


## 2026-06 · AUTONOMY EXPANSION — Dispute pre-triage + Safe Project Lifecycle — PREVIEW
- **Reutilizat** (fără sistem paralel): triajul Claude existent (`orchestrator/playbooks.py::handle_dispute_opened` → refactorizat în `compute_dispute_triage` reutilizabil), coada `Autonomy Activity`, `admin_approvals` (registry), risk-gates + kill-switch, ledger, mecanismul `verified_outcome`→`ai_memories`.
- **A. Dispute pre-triage** (`autonomy/disputes.py`): OBSERVE→CLASSIFY (Claude)→PRIORITIZE (DETERMINIST, explicabil: vârstă/escrow/severitate/status)→PROPOSE→HUMAN GATE. Adaugă `autonomy_triage` pe documentul disputei (non-destructiv, idempotent). Flag `insufficient_information`. **NICIO auto-rezoluție** (rezolvarea mișcă bani → 100% umană). Backfill pe cele 28 dispute: **28/28 triate — 20 HIGH · 8 MEDIUM · 21 ready-for-human · 7 waiting-info · confidence mediu 0.7 · 0 auto-rezolvate**.
- **B. Safe Project Lifecycle** (`autonomy/lifecycle.py` + `POST /api/admin/autonomy/projects/{id}/lifecycle`): API ÎNGUST cu tranziții explicite validate (nu „update status" generic). `active→on_hold` = **SAFE, auto** (reversibil, stale >30z + fără blocante + kill-switch ON); `on_hold→archived` = **MEDIUM, aprobare umană obligatorie** (executor `project_lifecycle_transition` în admin_approvals). Blocante reale verificate: tranșe `funded`/`warranty_hold`, reclamație garanție, task-uri active. READ-BACK după execuție + audit în `project_lifecycle_actions`. Status nou `archived` adăugat.
- **Integrare în bucla existentă**: OBSERVE #3 = triaj dispute bounded (3/tick, kill-switch gated); `stale_project` → încearcă REAL `active→on_hold` (eligibil) altfel fallback TODO; outcome lifecycle verificat → `verified_outcome`→knowledge. `verify()` extins pentru tip `lifecycle` (read-back stare proiect).
- **Demonstrat REAL în PREVIEW**: 2 proiecte stale+curate mutate autonom `active→on_hold` (verificat + audit), 1 proiect cu blocant → escaladat (TODO), 28 dispute triate. Metrici (reale): lifecycle 2 on_hold autonom / 0 archived / 1 blocat.
- **UI**: `AutonomyActivityPanel.jsx` extins — strip „Triaj dispute" (high/med/ready/waiting/confidence) + „Lifecycle proiecte" (on_hold autonom/archived/awaiting/blocate) + badge-uri prioritate pe itemii din coadă. Aceeași coadă unică (fără al 2-lea sistem).
- **Testare**: `tests/test_autonomy_expansion_p3.py` **26/26 PASS** (triaj non-destructiv + insufficient_info + prioritate deterministă + fără mutație financiară; lifecycle SAFE exec+verificat, invalid rejected, archive blocat de escrow, MEDIUM cere aprobare, kill-switch blochează, idempotent, read-back, knowledge doar după verificare; coadă unică + ledger + metrici). P2 17/17 + P1 12/12 rămân verzi.
- **Scor autonomie NEMANIPULAT**: `recommendation ≠ executed ≠ verified ≠ resolved`. Human score rămâne mic pentru că cele 28 dispute chiar necesită decizie umană — CORECT (reducem bottleneck-ul prin decizii mai rapide/informate, nu prin ascundere). NEMODIFICAT: rezolvarea disputelor, escrow/plăți, formulele de scor, Stripe/Beta.


## 2026-06 · AUTONOMY CORE — închiderea buclei operaționale (vizibil→măsurabil→verificabil→învață) — PREVIEW
- **Ce exista deja** (NU am duplicat): `loop.py` (OBSERVE→DETECT→FINDING→DECIDE→ACT→VERIFY→LEARN pe Analytics + Knowledge findings, risk-gating SAFE/MEDIUM/HIGH, kill-switch `low_risk_autopilot`, ledger `autonomy_loop_runs`, idempotent/bounded); `self_driving.py` (low-risk autopilot, auto-materialize recomandări→TODO, escaladare cereri stale = re-notificare specialiști, weekly lead report); executor aprobări cu registry; scoring cu semnale de bottleneck (Human Dependency).
- **Ce am adăugat (minim, REUTILIZARE, fără sistem paralel — a1+b1)**:
  1. **VERIFIED → Knowledge** (`loop.py::promote_verified_to_knowledge`): fiecare outcome SAFE executat autonom și VERIFICAT OK devine o memorie operațională reutilizabilă REALĂ în `ai_memories` (`source:"verified_outcome"`, `kind:"operational_playbook"`, persistentă), idempotent per `finding_key`. Include backfill bounded din findings reale deja verificate (istoric). → maturitatea memoriei crește ONEST (nu sintetic). Integrat în etapa LEARN a `run_loop_tick` (raportat ca `knowledge_records_created`).
  2. **Read-model UNIFICAT** (`autonomy/activity.py`, `GET /api/admin/autonomy/activity`): o singură COADĂ de acțiuni proiectată din artefactele existente (findings cu `autonomy_action`, TODO-uri, approvals, semnale bottleneck: cereri>48h/reguli oprite/anomalii audit/dispute/recomandări, `ai_memories` verified, `playbook_executions` erori) + **metrici REALE** derivate strict din ledgere: `autonomous_actions_total/verified`, `resolution_rate`, `human_escalation_rate`, `failures`, `blocked_by_governance`, `actions_requiring_reversal`, `avg_resolution_time_min`, `recommendations_executed/verified`, `knowledge_records_from_verified_outcomes`.
  3. **UI „Autonomy Activity"** (`AutonomyActivityPanel.jsx`, montat în `AutonomyEnginePage`): CE A FĂCUT / CE AȘTEAPTĂ / CE NECESITĂ OM / CE A EȘUAT / BLOCAT / CE A ÎNVĂȚAT + strip de metrici. Reutilizează design-ul existent.
- **Gate-uri umane PĂSTRATE (b1)**: NICIO putere nouă de auto-execuție. Anomalii audit + reguli oprite + dispute = DOAR escaladate la om (niciodată auto-acționate); MEDIUM/HIGH → aprobare umană; kill-switch OFF → SAFE blocat (fără execuție). Zero mutații noi pe requests/plăți.
- **Testare**: `tests/test_autonomy_closed_loop_p2.py` = **17/17 PASS** (SAFE+ON→auto+verificat; SAFE+OFF→blocat fără todo; MEDIUM→aprobare fără auto-exec; knowledge idempotent + source=verified_outcome; metrici/coadă corecte). Verificat e2e prin API + UI. Curățat artefact de test `/__loop_probe__` (35 sesiuni + finding + todo + memorie fake).
- **Metrici (PREVIEW, reale)**: acțiuni autonome 8 (loop 2 · self-driving 6), verificate 2 (100% pe loop), escaladări umane 3 (50%), eșecuri 0, blocate guvernanță 1, reversări 0, recomandări executate 1, knowledge din verificate 2, `ai_memories` reale 15 (0 seed). Scor: general 84.1 · ai 49.2 · human 35.0 (human mic = semnal REAL: 28 dispute + bottleneck-uri, acum vizibile în coadă).
- **Bottleneck-uri rămase (reale, human-gated by design)**: 28 dispute, 3 reguli automate oprite, cereri >48h — toate cer decizie umană (nu se auto-rezolvă fără o schimbare de produs care să dea permisiune, ex: API de lifecycle `db.projects`). PRODUCȚIE = necesită redeploy; metricile de prod devin reale după primul tick + snapshot.


## 2026-06 · DECONTAMINARE METRICĂ AUTONOMY (P1) — separă real de seed/synthetic + oprește auto_tune să umfle — PREVIEW
- **Cauza reală găsită**: `auto_tune` (cron săptămânal + butoane manuale) FABRICĂ date sintetice care umflau scorurile: 17 docs seed (`ai_documents.source="autonomy_seed"`), memorii seed (`source^="autonomy_seed"`), 13 decizii repair sintetice + 30 mesaje concierge (`synthetic_for_score_seed:True`), plus mass-dismiss de findings reale. Markerii de sintetic EXISTAU deja pe rânduri → separarea s-a făcut cu mecanismul existent (fără al 2-lea sistem).
- **FIX #1 — calcul scor onest (exclude sintetic)**: `autonomy/engine.py::_score_ai` numără DOAR docs/memorii reale (`REAL_DOC_FILTER`/`REAL_MEMORY_FILTER`), expune `excluded_seed_docs/memories`; `routes/admin_ai.py::_compute_rolling_effectiveness` + `_compute_concierge_score` exclud `synthetic_for_score_seed`. Rezultat PREVIEW: **AI 69.6→49.6, general 86.5→83.9** (scădere ONESTĂ — knowledge base = 3 docs reale, nu 20).
- **FIX #2 — oprit motorul de inflație**: `run_auto_tune_orchestration` NU mai injectează date sintetice și NU mai dismiss-uiește findings (pași marcați `skipped`, flag `decontaminated:True` în `autopilot_runs`); `weekly_auto_tune_job` — eliminat second-pass agresiv (mass-dismiss + re-seed); `/seed-ai-data` (Boost AI) → NO-OP deprecated; `boost-dev` → doar Release Gate real + snapshot (fără dismiss). **Dovadă: rularea auto-tune dă acum delta_general=0.0** (înainte umfla).
- **FIX #3 — DB efectiv curat (audit trail)**: `scripts/decontaminate_autonomy_synthetic.py` (dry-run implicit, `--apply`) a șters DOAR rândurile tagged synthetic (17+13+30), logat în `autonomy_decontamination_log` (batch_id, matched/deleted, sample ids). ZERO date reale atinse.
- **Testare**: `tests/test_decontamination_p1.py` = **12/12 PASS** (injectează 30 docs+120 mem+20 repair+25 concierge sintetice → scorurile NU se mișcă; auto-tune injectează 0 + delta 0). Verificat e2e prin API (score/health-score/auto-tune) + în UI (`/admin/autonomy`: „Recalculează (onest)", „Boost AI (off)", AI=50, general=84).
- **PREVIEW vs PRODUCTION**: reparat + verificat în PREVIEW. Pe PRODUCȚIE contaminarea sintetică EXISTĂ la fel (cron-ul a rulat și acolo) → după redeploy: (1) codul oprește re-injectarea, (2) rulează `python3 -m scripts.decontaminate_autonomy_synthetic --apply` pe prod pentru curățare. Scorul de prod se va corecta ONEST (în jos) la primul snapshot.
- **NEMODIFICAT** (retroactiv): snapshot-uri istorice (`autonomy_snapshots`, `admin_ai_health_history`) — rămân ca audit al calculului vechi; trend-ul va arăta un pas onest în jos după deploy. NU s-au atins requests/users/plăți/Stripe/Beta/Function Map/`.skp`/db.projects.
- **Risc rămas explicit**: contaminarea de tip DEMO/TEST în scorurile bazate pe `db.requests` (PREVIEW: 204/209 cereri = conturi test) NU se rezolvă prin filtru per-scor (ar dubla sistemul de clasificare demo) → aparține task-ului P0 „purge demo/test pe producție". Marcat PREVIEW/PRODUCTION/UNKNOWN în livrabil.


## 2026-06 · EXECUȚIE AUTONOMĂ SAFE REALĂ pe date reale (bucla închisă complet) — PREVIEW
- Adăugată a 2-a sursă REALĂ de OBSERVE în loop (fără duplicare): backlog-ul de findings existent din Knowledge Center (`admin_ai_findings`). Whitelist NON-destructiv → SAFE (`stale_project`); destructive (orphan_twins etc.) NU sunt atinse — rămân la fluxul lor cu aprobare umană (control uman păstrat). Fișier: `autonomy/loop.py` (`observe_knowledge_findings`, `act_on_existing_finding`).
- **Buclă închisă REALĂ executată pe date reale (fără injecție)**: detectat finding real `stale_project` (proiect 6a1ab71b… blocat 30+ zile) → clasificat SAFE (low, non-destructiv) → decis fără aprobare (guvernanță `low_risk_autopilot` ON) → EXECUTAT: task real de remediere în `admin_todos` (id 1648b1ff…) → verificat independent (todo există + finding triaged) → audit în `autonomy_loop_runs` (cu `scores_before`/`scores_after`) → Knowledge Center actualizat (finding `status:triaged` + `autonomy_action`) → Analytics actualizat (`analytics_events`: `autonomy_action_executed`, eveniment de sistem, nu afectează bounce/funnel) → scoruri recalculate (general 86.9→87.0).
- Idempotent/bounded/safe verificat: re-run → 0 duplicate (finding cu `autonomy_action` e exclus din re-detectare). Guvernanță respectată (OFF → `blocked_by_governance`, motiv în ledger). Analytics feedback = capacitatea existentă introdusă în buclă fără duplicare și fără scăderea controlului uman.
- NEMODIFICAT: mecanismul Orphan Twins, requests/users/properties/tranzacții, scoring, Function Map, abonament, Client/Specialist Beta.


## 2026-06 · FIX-uri validare producție Loop Operațional (deep-links + materialize + guvernanță) — PREVIEW
- **#1 Deep-links Loop Operațional**: „Vezi task-ul" → `/admin/todo?focus=<todo_id>` (evidențiază task-ul real), „Aprobare (gate uman)" → `/admin?tab=approvals&focus=<approval_id>` (evidențiază approval-ul real). Fără fallback la homepage; dacă artefactul lipsește → mesaj inline „indisponibil" (`todo-focus-missing` / `approval-focus-missing`). Fișiere: `OperationalLoopPanel.jsx`, `AdminTodoBoard.jsx`, `AdminApprovals.jsx`.
- **#2 „Materializează ca TODO-uri" (500 → JSON valid)**: cauză reală = de-dup regex `^{text[:60]}` cu `[`/`(` din textul recomandării → regex invalid → Mongo error → HTML 500 → `r.json()` crăpa în UI. Fix: `re.escape(...)` la de-dup + endpoint `generate-tasks` returnează mereu JSON (și pe eroare) + frontend pe `axios` (nu `fetch` cu `.json()` orb). Idempotent (fără duplicate). Fișiere: `routes/autonomy.py`, `AutonomyEnginePage.jsx`.
- **#3 Guvernanță/buget**: sursa de adevăr = `self_driving_settings.main.low_risk_autopilot` (kill-switch EXISTENT). Loop-ul îl RESPECTĂ: dacă e OFF → SAFE NU se auto-execută (fail-safe, `outcome:"blocked_by_governance"`, motiv în `autonomy_loop_runs`); MEDIUM/HIGH oricum la aprobare umană. NU există buget monetar separat; limitele per-rulare = `MAX_FINDINGS_PER_RUN`+dedup. Fișiere: `autonomy/loop.py`. Bug fix bonus: finding `blocked_governance` se reîncearcă la re-run (nu mai e tratat ca „handled").
- Testat: `tests/test_loop_fixes_e2e.py` (materialize idempotent + guvernanță ON/OFF PASS) + `test_reports/iteration_215.json` (UI deep-links 100%, fără redirect homepage). Function Map: NEMODIFICAT (per cerință).


## 2026-06 · OPERATIONAL AUTONOMY LOOP (FN-021) — bucla închisă Analytics→Acțiune (PREVIEW, necesită redeploy)
- Construită veriga LIPSĂ a autonomiei: **Analytics → Finding → Decizie(policy risc) → Acțiune → Verify → Learn**. Zero sisteme paralele: findings=`admin_ai_findings`, task-uri=`admin_todos`, aprobări=`admin_approvals`, singura colecție nouă=`autonomy_loop_runs` (ledger). Modul `backend/autonomy/loop.py` + endpoints `/api/admin/autonomy/loop/{run,runs,policy}` + panou UI în `/admin/autonomy` (`OperationalLoopPanel.jsx`) + job scheduler la 3h.
- Detectoare DETERMINISTE peste Analytics existent + funnel comercial: `high_bounce_page` (SAFE→auto todo) și `request_flow_abandonment` (MEDIUM→aprobare umană). Politică risc: SAFE/REVERSIBLE→auto-execuție; MEDIUM/HIGH→gate uman obligatoriu (admin_approvals). Idempotent, bounded, safe-on-rerun.
- E2E controlat PASS (`tests/test_autonomy_loop_e2e.py`): SAFE→todo+finding resolved, MEDIUM→approval+finding open, aprobare umană→remediere, idempotență (fără duplicate la re-run), LEARN (auto-resolve când semnalul dispare). UI 100% (iter214). Function Map: **FN-021 adăugat (VERIFIED)** + **FN-002 PARTIAL→VERIFIED** (dovada = E2E loop, exact „next action" de la FN-002).


## 2026-06 · COMMERCIAL FLOW — Funnel comercial instrumentat + vizibil (PREVIEW, necesită redeploy)
- Instrumentat fluxul comercial REAL existent (VISITOR→CLIENT→PROPRIETATE→CERERE→SPECIALIST→CONTINUARE) cu 7 evenimente, prin trackerul first-party EXISTENT (`analytics.js` `trackIntent` → `POST /api/track`, flag `intent_{signal}` pe `analytics_sessions`). ZERO sistem nou de analytics. Evenimente: `client_flow_opened`, `client_property_selected`, `request_started` (exista), `request_created`, `specialist_flow_opened`, `specialist_action_taken`, `flow_completed`.
- Backend NOU (read-only): `GET /api/admin/analytics/commercial-funnel` (analytics_growth.py) — agregă etapele per vizitator unic + verificare ÎNCRUCIȘATĂ cu `db.requests` real (SSOT): `requests_created_real`, `requests_confirmed_real`, `created_delta`. Răspunde direct la „din cei care intră pe /client, câți încep și câți creează o cerere reală".
- Frontend: tab NOU „Funnel comercial" în `AnalyticsGrowthPage.jsx` (KPI + bar chart 7 etape + card cross-check db.requests). Instrumentare în `ClientDashboardV2.jsx`, `RequestWizard.jsx`, `SpecialistDashboard.jsx`.
- Verificat E2E (iter213, 100% frontend): client creează cerere reală (POST /api/requests → db.requests) → specialist vede/acceptă (POST /accept) → funnel admin reflectă activitatea; cross-check real=1/semnal=1/diff=0. Zero regresii Client/Specialist Beta. NU s-a atins Orphan Twins / entitlements / abonament 9€ / Digital Twin CTA.


## 2026-06 · DATA INTEGRITY — Safe repair pentru Twins orfane (PREVIEW, necesită redeploy)
- Extins scannerul read-only `admin_data_integrity.py` cu remediere sigură pentru „Twins orfane": `GET /api/admin/data-integrity/orphan-twins` (listă+clasificare) și `POST .../orphan-twins/resolve` (arhivează în `twins_orphan_archive` + șterge din `db.twins` + audit în `data_integrity_actions` + re-scan). Re-atașarea deterministă e imposibilă (twins fără `owner_id`/legătură) → acțiune sigură = DELETE arhivat (recuperabil). UI: buton „Șterge toate Twin-urile orfane" + confirmare cu mesaj de protecție în `DataIntegrityCard.jsx`.
- Verificat E2E: 28 orfane reale → arhivate+șterse, orphan=0; protecție confirmată (properties/users/requests/disputes/transactions neatinse); audit 28 SUCCESS; idempotent; confirm=false→400; UI E2E 100% (iter212). Reality Check (read-only) livrat separat.

## 2026-06 · KNOWLEDGE SYNC — Digital Twin Next Stage I/II/III consolidat în docs canonice

**Ce a fost actualizat**
- `audits/PROPERTY_TWIN_CANONICAL_v1.0.md` → adăugat §9 (Next Stage I/II/III delivered in preview): inventar 18 funcționalități, reguli de integritate, decizia City Partner Products, fluxul strategic, known issue `.skp`/Trimble, stare testare, next roadmap, conflict marcat.
- `audits/MASTER_PLATFORM_STATE.md` → secțiunea Property Twin extinsă cu rezumatul Next Stage I/II/III (PREVIEW) + known issue `.skp` + next roadmap; păstrată distincția P0/P1/P0.1 = PRODUCTION-LIVE.
- `INDEX.md` → intrarea canonică Property Twin actualizată; referință CHANGELOG + BUGS #005.
- `BUGS.md` → adăugat BUG #005 (`.skp` nu e vizualizabil 3D; validare URL Trimble Connect).
- `CHANGELOG.md` → creat (acest fișier).
- `PRD.md` → deja conținea secțiunile Next Stage II/III (actualizat la build).

**Funcționalități LIVRATE (BUILT & DELIVERED IN PREVIEW — necesită redeploy Fondator; NU LIVE)**
- Stage I: upload 3D multi-format · AI-3D `inferred` · Q&A grounded · ancorare istorică (zero auto-assign) · mobile.
- Stage II: AI Design Concepts · validare profesională (`inferred→în validare→verified`) · Q&A suggestions · ancorare în masă (același owner) · `ViewerErrorBoundary` · Comparație concepte · Ofertă din concept `verified` (`db.requests`) · Notificare validare (in-app+email) · Materiale reale + preț orientativ. Teste iter207(95%)→iter208(100%).
- Stage III: Catalog Materiale admin (`/admin/city-partner-products`, gol implicit) · Alegere câștigătoare (single-winner server-side) · Concept în Pașaport (opt-in OFF, doar `verified`, OFF→404) · Ofertă cu Poze (render atașat cererii). Teste iter209(F1/2/3=100%)+iter210(F4=100%). Regresie intactă. Date de test curățate.

**PRODUCTION-LIVE (neschimbat)**: P0/P1/P0.1 Property Anchor (22/22 live pe `propmanage.ro`, 28 Aug 2026).

**Decizii de business făcute canonice**
- AI `inferred` ≠ `verified`; doar profesionistul validează; AI nu setează `verified` automat.
- ZERO produse/prețuri/specialiști/oferte inventate; fără date reale → „preț orientativ indisponibil".
- ZERO auto-assignment; o proprietate = un owner; ancorare în masă doar între proiectele aceluiași owner.
- Ofertă din concept doar pentru `verified`; acțiunile reale cer confirmare explicită.
- Publicare concept în Pașaport = opt-in (implicit OFF), doar `verified`.
- City Partner Products: catalog super-admin, produse reale, poate fi gol; rezolvare preț: partener → piață → „indisponibil".

**Known issues**
- `.skp` NU e vizualizabil 3D (upload OK, doar descărcabil); Trimble Connect cere URL valid (link Google Drive respins corect). NU marca `.skp` „fully supported". → BUG #005.

**Next roadmap (NU implementat)**: Import CSV/Excel catalog · Materiale structurate în ofertă · Insignă „Amenajare planificată" Pașaport · Comparație partajabilă · (nuanță) ofertă zero-tap.

**Conflict marcat pentru Fondator**: lista de „next action items neimplementate" din directivă includea itemi deja livrați (comparație-câștigător, concept-în-pașaport, notificare validare, materiale parteneri, parțial ofertă-un-tap). Consemnat starea reală pe baza codului; de confirmat reducerea listei de roadmap.

## 2026-06 — Map Unification (Imobile Verificate) + Building Confirmation (v1.0)
- **Provider hartă unificat:** creat `frontend/src/components/PmMap.jsx` (hook `useMapsConfig` din `/api/public/maps/config`; `PmMarkersMap` multi-marker; `PmMiniMap` single-marker preview). Google Maps când `GOOGLE_MAPS_ENABLED=true` + cheie; altfel fallback Leaflet pe tiles OpenStreetMap (fără cheie). `EstateMapView.jsx` rescris să folosească `PmMarkersMap`.
- **Fix „API KEY REQUIRED":** cauza = tiles CartoDB (`basemaps.cartocdn.com/dark_all`) care cer acum înregistrare. Înlocuite cu OSM standard (`tile.openstreetmap.org`) în fallback. Harta din `/imobile-verificate` funcționează acum în Preview fără cheie.
- **Confirmare explicită a clădirii:** `PropertyTechnicalRecord.jsx` — `attachExisting` nu mai face `window.confirm`; deschide `BuildingConfirmDialog` (nume, adresă, badge confidence Ridicată/Medie/Scăzută, notă proveniență HartaBlocuri „neverificat", preview mini-map, butoane „Confirmă clădirea" / „Nu este clădirea mea"). `attach-building` se apelează DOAR după confirmare explicită.
- **Backend aditiv (read-only):** `property_technical_record.py` `search_buildings_for_ptr` întoarce acum `source`, `provenance`, `match_confidence` (criteriu real de string: query în adresă=high, în nume=medium, altfel low) + fallback lat/lng din raw HartaBlocuri.
- **Boundary intact:** listările Estate rămân public (vânzare, intenționat), harta publică HartaBlocuri = doar centroizi agregați, GIS privat = authz server-side (401/403/200).
- **Teste (iter 228):** backend 100% (8/8), frontend 100%. Cancel dialog → zero mutații. Fără regresii pe SEO/sitemap/HartaBlocuri/Marketplace/House Health/Digital Twin/Google Maps secrets/authz.
- **Observație (out-of-scope, neatinsă):** `/api/properties/mine` întoarce 500 (alias legacy; `/api/properties` funcționează).

## 2026-06 — Admin Edit Preț Listing + Fix Alias /properties/mine (v1.0)
- **Admin editare preț (Imobile Verificate):** `VerifiedEstateAdmin.jsx` — buton „Editează" lângă preț pe fiecare card Kanban + `PriceEditModal` (input Preț RON, Salvează/Anulează, „Preț actualizat."). Folosește PATCH existent `/api/verified-estate/admin/listings/{id}` cu allowlist `ListingPatch` (doar câmpul price_ron trimis). Format RON de afișare nemodificat.
- **Backend validare preț:** `verified_estate.py` `ListingPatch.price_ron` acum `Field(ge=0, le=1_000_000_000)` — respinge negativ/overflow (422). Mass-assignment protejat de allowlist Pydantic. Authz server-side existentă: `require_role("admin","operator")` → non-staff (client) primește 403.
- **Verificat (curl):** admin 285.000→315.000 reflectat în pagina publică a listingului ȘI în cardul din /imobile-verificate (valori identice); client PATCH=403; negativ=422; non-numeric=422; doar price_ron schimbat (title neschimbat). Restaurat la 285.000 după test.
- **Fix alias legacy `/api/properties/mine`:** cauza = ruta cădea pe `/properties/{prop_id}` cu prop_id="mine" → `ObjectId("mine")` arunca → 500. Fix: `properties.py` adăugat `GET /properties/mine` (definit ÎNAINTE de ruta cu param) care deleagă la `list_properties(user)` — aceeași logică/authz. Verificat: unauth=401, auth=200 (listă), canonic `/properties`=200.
- **Fără regresii:** sitemap-blocuri.xml 200, maps/config 200, GIS 401/403/200, buildings/search 200. Neschimbate: HartaBlocuri/import/Truth Layer/GIS/Google Maps/SEO/Marketplace/House Health/Digital Twin/OAuth/schema. Fără deploy/publish.

## 2026-06 — Preț Listing RON + EUR la cursul BNR (v1.0)
- **Sursă:** BNR oficial `https://www.bnr.ro/nbrfxrates.xml` (parsare Cube date + `<Rate currency="EUR">`, multiplier=1). RON = source of truth; EUR = derivat read-only.
- **Serviciu nou:** `backend/bnr_exchange_rate.py` — `get_eur_ron_rate()` (cache DB `bnr_exchange_rates`, refresh LAZY zilnic la prima citire, fallback la ultimul curs BNR valid; None dacă nu există curs → EUR ascuns), `seed_rate()`, `compute_price_eur()`. Fără curs hardcodat/inventat.
- **Seed Preview (o singură dată, în DB nu în cod):** curs REAL BNR **EUR/RON = 5.2438**, `rate_date=2026-06-30`, `source=BNR` (bnr.ro e blocat de WAF în pod → serviciul rulează pe fallback în Preview; în Live va face fetch automat).
- **Formula:** `price_eur = price_ron / eur_ron_bnr`. Ex: 285.000 RON → ≈54.350 EUR; 685.000 → ≈130.630 EUR; 315.000 → ≈60.071 EUR.
- **API (read-only, aditiv):** listing include `price_eur`, `eur_ron_rate`, `exchange_rate_source:"BNR"`, `exchange_rate_date`. Îmbogățire în toate endpoint-urile (public list/detail, admin list/patch). `price_eur` NU e în allowlist `ListingPatch` → mass-assignment ignorat (verificat: PATCH price_eur=999999 → recalculat server-side).
- **UI:** RON principal + „≈ XX.XXX EUR" + „Calculat la cursul BNR din DD.MM.YYYY" în: card public (`EstateBrowse`), detaliu (`EstateDetail`), card admin + preview live în `PriceEditModal` (`VerifiedEstateAdmin`). EUR NU e editabil.
- **Fișiere:** `backend/bnr_exchange_rate.py` (nou), `backend/routes/verified_estate.py`, `frontend/.../EstateBrowse.jsx`, `EstateDetail.jsx`, `VerifiedEstateAdmin.jsx`.
- **Teste (curl + screenshot):** seed OK; RON→EUR corect; public == admin (aceeași valoare/curs/dată); price_eur manual ignorat; no-rate→EUR ascuns; cache same-day (fără request repetat); fallback la ultimul curs; authz intact (client PATCH=403). Fără regresii: properties/mine 200, GIS 200, sitemap-blocuri 200, listings 200. HartaBlocuri/GIS/SEO/Marketplace/House Health/Digital Twin neschimbate. Fără deploy/publish.

## 2026-06 — Corecție Preț Audit (350→2.400 RON) + Hartă Responsive Mobile (v1.0)
### Obj1 — Preț Audit Tehnic 350 → 2.400 RON
- Conținut public/SEO: `frontend/src/data/ghiduri.js` (11 mențiuni: descriere structured-data, „răspuns scurt", pași, CTA, FAQ; bundle recalculat 1.300→**3.350** = audit 2.400 + Twin 950).
- Pagini: `BuyingChecklistPage.jsx`, `HealthScorePage.jsx`.
- Emailuri backend: `routes/lead_magnets.py` (x2).
- Config preț: `routes/app_settings.py` default `audit_ron` 350→2400; `routes/verified_estate.py` default `VE_PRICE_AUDIT_RON` 350→2400; **DB `app_settings.pricing.audit_ron` actualizat 350→2400** (sursa citită de UI dinamic via `/api/app-settings/public` — `SellMyProperty` afișează acum 2.400).
- Admin docs: `AdminDocumentation.jsx` (valori default 2.400).
- NEATINSE: Twin 950, comision 2.5%, logica Stripe, abonamente, produse. Range-uri non-audit păstrate (PRAM 350-600, DIF 200-350). Bundle audit+twin = calcul dinamic (2400+950=3350).
### Obj2 — Hartă vizibilă pe MOBILE
- Cauză: `BlocuriPublic.jsx` randează o hartă Google proprie DOAR când `cfg.enabled` (Google activ). În Preview/mobil (fără cheie) cădea pe `FallbackMap` = o LISTĂ de carduri, NU o hartă → „nu văd harta".
- Fix: `/blocuri` folosește acum `PmMarkersMap` (Google când activ + fallback OSM Leaflet fără cheie, responsive `height: clamp(320px,60vh,520px)`, lățime 100%). Markere = centroizi agregați (aproximativi), notă „Date externe HartaBlocuri — neverificate", fără coordonate exacte (boundary public păstrat).
- „Imobile Verificate" (`EstateMapView`) deja folosea `PmMarkersMap` (OSM fallback) — verificat pe mobil.
- Homepage „Găsește-ți blocul" (`BuildingDiscovery`) rămâne căutare-by-design; harta interactivă publică e la `/blocuri`.
- Verificat: tiles OSM se încarcă (18), markere afișate, fără scroll orizontal, provenance vizibil. Fără regresii: sitemap-blocuri 200, listings 200 (EUR intact), properties/mine 200, GIS 200. Fără deploy/publish.

## 2026-06 — Client Beta Mini-Map + Aliniere Pricing (Twin 15.000 / Bundle 17.400 / Comision 0%) (v1.0)
### Mini-hartă Client Beta „Găsește-ți blocul" (BuildingDiscovery)
- Adăugată mini-hartă responsive sub căutarea text (păstrată): `PmMarkersMap`, `height: clamp(220px,40vh,340px)` (nu full-screen). Markere apăsabile → fluxul existent `/register?binvite={id}`. Afișează sursă + „Date externe — neverificate".
- BOUNDARY: backend `_public_card` (`hartablocuri.py`) expune DOAR `lat_approx`/`lng_approx` (rotunjite la 2 zecimale ≈1km). Coordonatele exacte NU sunt publice (doar în GIS autentificat).
- Fișiere: `backend/routes/hartablocuri.py`, `frontend/src/components/BuildingDiscovery.jsx`.
### Origine preț 17.400 RON + aliniere pricing (confirmat de user)
- 17.400 = `bundle_ron = audit_ron + twin_ron` (calcul în `/api/verified-estate/pricing`, NU hardcodat). Provine din DB `app_settings.pricing`. Valori CANONICE confirmate de user: **Audit 2.400 · Digital Twin 15.000 · Comision 0% · Bundle 17.400 (automat)**.
- Preview era divergent (twin 950 / comision 2,5% / bundle 3.350). Aliniat la canonical: DB Preview `app_settings.pricing` → twin 15000, commission 0; default-uri cod `app_settings.py` DEFAULT_SETTINGS + `verified_estate.py` `PRICE_TWIN_RON`=15000; texte SEO `ghiduri.js` (twin 950→15.000, bundle 3.350→17.400, eliminat claim „comision 2,5% / twin gratuit"); `AdminDocumentation.jsx` (15.000/0%).
- Verificat UI `/imobile-verificate/sell`: Doar Audit 2.400 · Audit+Twin 17.400 · Doar Twin 15.000 · badge „Comision 0%". `/pricing` = bundle 17.400. Zero contradicții numerice între SEO/UI/DB.
- FLAG (nemodificat, decizie de conținut a userului): naratiunea de marketing „Comision 2.5%" din `WhyUsPage.jsx` (secțiunea de comparație 2.5% vs 5-6%) + meta titles/descriptions SEO încă spun 2.5%. Nu am rescris acest value-prop (nu e un câmp de preț; userul gestionează comisionul din admin).
- Regresie: buildings/search 200, blocuri/map 200, sitemap-blocuri 200, properties/mine 200, GIS 200. Fără deploy/publish. Notă: DB Live avea deja twin 15.000/comision 0 (17.400 corect); default-urile de cod se aplică pe Live după un redeploy reușit.

## 2026-06 — Deployment Readiness (production-safety fix) (v1.0)
- Context: producția eșuează la `pull_source: tenant "emergent-gcs" has no plane configured` = DEFECȚIUNE DE PLATFORMĂ Emergent (înainte de build/cod), NU code-fixable.
- FIX cod (singura modificare): `backend/server.py` — jobul programat `reset_demo_accounts` (delete_many nocturn 02:00) e acum gated pe `SEED_DEMO_DATA=='true'` (convenția existentă). Producția rulează cu SEED_DEMO_DATA!=true → jobul distructiv NU rulează în producție (protejează datele reale). Preview păstrează comportamentul. Verificat: backend health 200, log „demo_accounts_reset ENABLED (SEED_DEMO_DATA=true)" în Preview.
- NEMODIFICAT (fals-pozitiv): `.gitignore` blochează `.env` — aplicația e DEJA LIVE (propmanage.ro health 200) cu exact acest `.gitignore`, deci nu a blocat niciodată deploy-ul; Emergent injectează secretele prin pasul MANAGE_SECRETS, nu din `.env` comis. Eliminarea regulii ar comite secrete reale (STRIPE/JWT/GOOGLE/RESEND/SEED_ADMIN_PASSWORD) = regresie de securitate. NU am atins-o.
- Concluzie: niciun blocaj de cod nu cauzează eșecul; cauza rămâne exclusiv defecțiunea de platformă (tenant plane). Necesită echipa Emergent (support@emergent.sh + run IDs). Fără deploy/publish.

## 2026-09 — Production Readiness Investigation (post-deploy) + Google Maps enable fix
- FIX (config, preview): adăugat `GOOGLE_MAPS_ENABLED=true` în `backend/.env`. Cauza „Google Maps neactivat" în prod = flag-ul lipsea COMPLET din secretele deployate (UI-ul Secrets editează doar chei existente, nu adaugă chei noi). Cheia API era prezentă. Necesită redeploy ca să intre în efect (așteaptă aprobare). Preview rămâne fallback (cheie goală) — fără breakage. `maps/config.enabled = (flag AND key)`.
- Geocoding: NEIMPLEMENTAT nicăieri → adrese noi (ex. Aleea Negoiu 8D) nu au coordonate. Cauza-rădăcină a ambelor probleme de hartă. Recomandat flux server-side geocoding (cheie server-side cu Geocoding API, provenance/status, nu suprascrie coord. verificate, eșuare grațioasă) — de implementat DUPĂ aprobare + cheie.
- /imobile-verificate hartă goală: confirmat 0/4 listări au lat/lng în prod. Rămâne goală până listările primesc coordonate (import HB sau manual/geocoding).
- Memorie: limită 512Mi (req 200Mi), 2 replici, HPA/VPA off. 0 restarts, 0 OOMKilled în 24-48h. Doar 503-uri la cold-start ~2-3 min. 512Mi suficient pe baza evidenței curente; 1GB NU e necesar acum; peak/avg necesită un dashboard de metrici (în afara sculelor deployerului).
- AI Health Score 60 vs 74-76: formula IDENTICĂ (0.40·findings + 0.35·effectiveness + 0.25·concierge). Prod: 100/0/80=60. effectiveness=0 pentru că ai_outcomes sunt decise/scanate dar 0 finalizate/aplicate (effectiveness_pct=0). NU e regresie — diferență de date. `admin_ai_repair_suggestions` (36 applied) e alt subsistem, nu alimentează scorul. NEMODIFICAT.
- Regresie HB: 3408 total / 3406 hartablocuri_import / 2 propmanage-only / 0 conflicte — CONFIRMAT în prod.
- Securitate: cheia Google din env (nu hardcodată); `.env` netracked; public building search doar câmpuri publice + coord. aproximate; SEED_DEMO_DATA gating activ. OK.
- Fără deploy/publish. O singură modificare: GOOGLE_MAPS_ENABLED în preview .env.
