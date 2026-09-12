# PropManage — Autonomous Evolution Roadmap
**Direcție strategică:** Self-Driving Property Management Platform  
**Filosofie:** Emergent = *Chief Autonomy Officer*. Fiecare propunere trebuie să răspundă la o singură întrebare — *„Ce intervenție umană elimină?"*  
**Data analiză:** Feb 2026  
**Autor:** Emergent (E1) — pe baza infrastructurii reale a codebase-ului.

---

## 0. Rezumat executiv

PropManage **NU** are nevoie de module noi. Are nevoie de un **strat transversal de orchestrare a autonomiei** care să conecteze modulele existente într-un sistem care se conduce singur.

### Ce am descoperit în audit (infra reală, nu presupuneri):
- **111 route files** backend, **80+ pagini admin** frontend.
- **30+ cron-jobs** APScheduler active (daily sweep, snapshots, digests, monitors, auto-match, warranty release).
- **Autonomy Engine** deja calculează scoruri pe 5 dimensiuni: `operational`, `technical`, `security`, `dev`, `ai`.
- **Daily Autopilot Sweep** rulează la 04:15 — dar face doar 2 lucruri: close stale findings + refresh snapshot.
- **Bug Memory + QA Copilot + AI Governance + Security Guard + Data Integrity** — există dar rulează în silozuri.
- **Morning Briefing** + **Founder Digest** — există dar sunt read-only (raportare, nu acțiune).

### Concluzia critică
**80% din infrastructura de autonomie e deja construită.** Ce lipsește este un **Orchestrator** care să:
1. Observe simultan toate semnalele (cross-module).
2. Coreleze cauze (nu doar raporteze simptome).
3. Ia decizii automate în cascadă (try → escalate → notify).
4. Învețe din fiecare incident (feedback loop).
5. Escaladeze la om DOAR când toate strategiile automate au eșuat.

**Human Dependency azi:** admin verifică briefing zilnic + rezolvă manual 15-20 finding-uri/săptămână + intervine pe disputes, KYC, marketplace.  
**Human Dependency țintă (12 luni):** admin verifică doar rapoartele săptămânale + intervine < 3 ori/săptămână pe cazuri edge.

---

## 1. Analiză modul cu modul

Format uniform:
> **Face azi | Dependență umană | Poate deveni autonom | Detectează | Repară | Învață | KPI nou | Agent AI**

---

### 1.1 Autonomy Engine (`/backend/autonomy/`)
1. **Azi:** Calculează scoruri (0-100) pe 5 axe la 03:15; salvează snapshot; alertă la downgrade tier; auto-tune weights luni la 04:00.
2. **Dependență umană:** Admin citește scorul și decide ce să facă. Motorul nu acționează.
3. **Autonom:** Auto-tune weights ✅. **Lipsește:** auto-*execution* când scorul scade (ex: „ops sub 70 → declanșează sweep-uri suplimentare de reparare").
4. **Detectează:** Tier downgrade, componente sub target.
5. **Repară:** Nimic azi. **Poate:** trigger `daily_autopilot_sweep` on-demand când o axă scade brusc (>5 puncte în 24h).
6. **Învață:** Nu. **Poate:** corelație scor↔evenimente (ex: „scăderea `security` corelează cu spike incidents").
7. **KPI nou:** `Autonomy MTTR` — Mean Time To Recovery pentru fiecare axă scăzută.
8. **Agent AI:** `AutonomyReflex` — sub-agent care ascultă snapshoturi, detectează degradări și declanșează sweep-uri corective.

---

### 1.2 Autopilot (`/backend/autonomy/autopilot.py`)
1. **Azi:** Rulează 04:15 zilnic. Închide QA findings stale (>14d) + AI findings stale (>30d) + refresh snapshot.
2. **Dependență umană:** Admin trebuie să creeze manual reguli noi de sweep când apare un pattern.
3. **Autonom:** ✅ deja. **Lipsește:** sweep-uri contextuale (nu doar time-based).
4. **Detectează:** doar staleness.
5. **Repară:** ✅ auto-close stale findings.
6. **Învață:** Nu. **Poate:** dacă un tip de finding e mereu închis automat fără intervenție → propune să nu mai fie creat de la început.
7. **KPI nou:** `Sweep Impact Score` — cât % din findings sunt rezolvate de sweep vs manual.
8. **Agent AI:** `SweepStrategist` — decide zilnic ce sweep-uri să ruleze (nu doar cele fixe).

---

### 1.3 AI Performance Copilot + AI Dev Team + AI PM
1. **Azi:** Copilot analizează cod și propune sugestii; Dev Team = catalogul agenților; AI PM face breakdown de feature în todos.
2. **Dependență umană:** Admin trebuie să apese „inject todos", „analyze", „resolve finding".
3. **Autonom:** **Poate:** auto-inject todos când Bug Memory detectează pattern recurent (>3 ocurențe).
4. **Detectează:** Cod cu risc, feature-uri prea complexe.
5. **Repară:** Sugestii, nu execuție directă.
6. **Învață:** ✅ parțial (memories există în `ai_control`). **Lipsește:** feedback după acceptare/respingere sugestie.
7. **KPI nou:** `Suggestion Adoption Rate` + `Bug Prevention Rate` (bugs prevenite vs bugs escapate).
8. **Agent AI:** `AutoPatchProposer` — la fiecare deploy failure/exception recurentă, generează automat un PR-draft (todo cu prompt gata).

---

### 1.4 AI Investigator + Bug Memory Aggregator
1. **Azi:** Bug Memory adună findings din QA/AI/Repair/Incidents într-o unică vizualizare căutabilă.
2. **Dependență umană:** Admin caută manual când suspectează un pattern.
3. **Autonom:** **Poate:** scan zilnic care detectează clustere de bug-uri (n-gram pe titlu/descriere).
4. **Detectează:** ✅ bug-uri similare (search). **Lipsește:** auto-clustering.
5. **Repară:** Nu. **Poate:** auto-open finding „Meta-bug: 5 bug-uri similare — investigate root cause".
6. **Învață:** ✅ acumulare istoric. **Lipsește:** ranking cauze root repetate.
7. **KPI nou:** `Recurring Bug Rate` (bug-uri care revin după fix).
8. **Agent AI:** `PatternHunter` — rulează la 05:00 zilnic, scan pe bug memory, produce raport „top 3 root causes recurente".

---

### 1.5 QA Copilot (`qa_copilot.py`)
1. **Azi:** Sesiuni QA cu findings și prompt-uri către Emergent.
2. **Dependență umană:** Admin creează sesiuni, adaugă finding-uri, generează prompt.
3. **Autonom:** **Poate:** creare automată de sesiuni când Smoke Test eșuează (există deja `smoke_test_monitor`).
4. **Detectează:** Nu detectează, doar înregistrează.
5. **Repară:** Nu. **Poate:** auto-generate prompt după 3 finding-uri similare.
6. **Învață:** Nu direct. Se leagă de Bug Memory.
7. **KPI nou:** `QA-to-Fix Cycle Time` (media între finding creat și rezolvat).
8. **Agent AI:** `QAOrchestrator` — pipeline complet: smoke test fail → creează sesiune → adaugă finding → generează prompt → notifică founder.

---

### 1.6 Documentation (`docs_ai.py`, `docs_routes.py`, `operating_manual.py`)
1. **Azi:** Docs generate AI + manual operațional.
2. **Dependență umană:** Admin actualizează după fiecare feature nou.
3. **Autonom:** **Poate:** hook post-deploy → detectează endpoints noi → generează secțiune doc.
4. **Detectează:** Diff-uri de rute noi/schimbate.
5. **Repară:** ✅ auto-doc generation e fezabilă.
6. **Învață:** Nu. **Poate:** track ce secțiuni sunt citite (dacă lipsește vizite, marchează „stale doc").
7. **KPI nou:** `Doc Coverage %` (endpoints documentate / total).
8. **Agent AI:** `DocKeeper` — auto-update doc când detectează rute noi în OpenAPI.

---

### 1.7 Audit (`admin_content_audit.py`, `admin_term_audit.py`, `LegalAuditPage`)
1. **Azi:** Audit conținut + termeni + GDPR (read-only).
2. **Dependență umană:** Admin rulează manual.
3. **Autonom:** **Poate:** rulare săptămânală automată (nu există cron).
4. **Detectează:** Conținut non-conform. **Poate:** flag automat.
5. **Repară:** Nu direct. **Poate:** propune replace strings sau desființare feature.
6. **Învață:** Nu.
7. **KPI nou:** `Audit Debt` (issue-uri deschise > 30 zile).
8. **Agent AI:** `ComplianceWatcher` — rulează weekly, raportează dacă audit-debt crește.

---

### 1.8 Marketplace + Marketplace Partners + Marketplace Offers
1. **Azi:** Listare specialiști, oferte pe cereri, matching hibrid (rating+fee+zone).
2. **Dependență umană:** Admin aprobă KYC, moderează dispute, terminează parteneri.
3. **Autonom:** ✅ auto-match cron (:23 la fiecare oră). **Lipsește:** onboarding automat.
4. **Detectează:** Rating scăzut, no-response, fraudă potențială.
5. **Repară:** **Poate:** auto-suspend specialist cu >3 dispute deschise în 30d.
6. **Învață:** ✅ scoring hibrid ajustabil.
7. **KPI nou:** `Marketplace Health Score` (dispute rate + response time + client satisfaction).
8. **Agent AI:** `MarketplaceMedic` — monitorizează sănătatea marketplace-ului și acționează pe outlieri.

---

### 1.9 Financial (Wallet, Payments, Warranty Release)
1. **Azi:** Stripe checkout, escrow, `warranty_auto_release` la 06:00.
2. **Dependență umană:** Admin verifică webhook-uri eșuate, reconciliere.
3. **Autonom:** ✅ warranty release + Stripe webhooks.
4. **Detectează:** Webhook fail, sold negativ (există în data_integrity).
5. **Repară:** **Poate:** auto-retry webhook, auto-flag tranzacții suspecte.
6. **Învață:** Nu.
7. **KPI nou:** `Reconciliation Gap` (fonduri necontabilizate).
8. **Agent AI:** `FinanceReconciler` — rulează nightly, cross-check Stripe ↔ DB, alertă doar la discrepanțe.

---

### 1.10 Requests + Disputes + Reviews
1. **Azi:** Requests → offers → in_progress → completed → confirmed. Dispute manuală. Reviews v2.
2. **Dependență umană:** Admin rezolvă disputes (cel mai time-consuming task).
3. **Autonom:** **Poate:** dispute triage automat (categorii: „no-show", „quality", „price") + first-response AI.
4. **Detectează:** Requests blocate în „open" >72h fără oferte; disputes fără mesaj client 5+ zile.
5. **Repară:** **Poate:** auto-notify + auto-close abandonate.
6. **Învață:** Din pattern dispute rezolvate — ce specialiști au repeat issues.
7. **KPI nou:** `Dispute Auto-Resolution Rate`.
8. **Agent AI:** `DisputeMediator` — face triage inițial + propune rezoluție cu 3 argumente.

---

### 1.11 Monitoring (Healthcheck, Smoke Test, Incidents, Auth Health)
1. **Azi:** 5+ cron-uri: `health_ping` (15min), `smoke_test_monitor` (30min), `auth_health_alert` (15min), `incident_spike_alert` (weekly).
2. **Dependență umană:** Admin primește alertă și decide.
3. **Autonom:** ✅ deja rulează. **Lipsește:** acțiune automată post-detectare.
4. **Detectează:** ✅ excelent.
5. **Repară:** Nu. **Poate:** auto-restart supervisor la 3 fail-uri consecutive; auto-create QA session la smoke fail.
6. **Învață:** Nu.
7. **KPI nou:** `Mean Time Between Failures (MTBF)` + `Auto-Recovery Rate`.
8. **Agent AI:** `SREPilot` — răspunde la fiecare alertă cu 1 din 3: retry, escalate, ignore-with-reason.

---

### 1.12 Security (`security_guard.py`, `AISecurityCenterPage`, KYC)
1. **Azi:** Rate limiting, IP guard, event log, KYC manual queue.
2. **Dependență umană:** Admin aprobă KYC (bottleneck major), review evenimente critice.
3. **Autonom:** ✅ block automat pe abuse. **Lipsește:** KYC pre-validation AI.
4. **Detectează:** ✅ bot, datacenter IP, rate abuse.
5. **Repară:** ✅ auto-block/rate limit.
6. **Învață:** Nu direct.
7. **KPI nou:** `KYC Auto-Approve Rate` + `False Positive Block Rate`.
8. **Agent AI:** `KYCTriage` — pre-validează docs (OCR + document integrity + face match) și auto-aprobă cazurile clare (est. 70%).

---

### 1.13 Development (`admin_dev_velocity`, `ai_dev_team`, `deprecation_pulse`, `future_ideas`)
1. **Azi:** Velocity raport weekly, deprecation pulse thu-09:30, future ideas backlog.
2. **Dependență umană:** Fondator citește digest, decide priorități.
3. **Autonom:** **Poate:** auto-prioritize backlog după business metrics (revenue impact).
4. **Detectează:** Feature-uri neatinse >60d → candidat deprecation.
5. **Repară:** Nu (aici uman e ok).
6. **Învață:** ✅ future ideas se acumulează.
7. **KPI nou:** `Feature Adoption vs Cost` — separă feature-uri „waste".
8. **Agent AI:** `RoadmapAdvisor` — corelează utilizare + cost AI + business impact → propune ce să deprecate/promovezi.

---

### 1.14 Statistics + Analytics Growth
1. **Azi:** Analytics events, campaigns, UTM, PDF export.
2. **Dependență umană:** Admin analizează dashboard.
3. **Autonom:** **Poate:** anomaly detection (drop trafic, spike bounce).
4. **Detectează:** Nu automat.
5. **Repară:** Nu.
6. **Învață:** ✅ campaign performance.
7. **KPI nou:** `Anomaly Alert Count`.
8. **Agent AI:** `GrowthSentinel` — daily scan pentru anomalii statistice cu explicație root.

---

### 1.15 Marketing (`marketing_campaigns`, `marketing_growth`, `marketing_performance`)
1. **Azi:** Campanii, growth tracking, performance.
2. **Dependență umană:** Admin creează campanii manual.
3. **Autonom:** **Poate (P3-P4):** auto-generate creative variations, A/B test automat, auto-kill underperformers.
4. **Detectează:** CTR/CAC/ROI slabe.
5. **Repară:** **Poate:** pause creative sub prag ROI.
6. **Învață:** ✅ istoric campanii.
7. **KPI nou:** `Campaign Auto-Optimization Coverage`.
8. **Agent AI:** `AdOptimizer` — se conectează la Meta/Google Ads (Phase 3 din backlog).

---

### 1.16 Notifications
1. **Azi:** Notif in-app + email.
2. **Dependență umană:** Admin trimite manual în cazuri edge.
3. **Autonom:** ✅ event-triggered.
4. **Detectează:** N/A.
5. **Repară:** N/A.
6. **Învață:** **Poate:** open rate, engagement per template.
7. **KPI nou:** `Notification Fatigue Index` (unsub rate + ignore rate).
8. **Agent AI:** `NotifCurator` — throttle inteligent, evită spam-ul (max N notif/user/zi).

---

### 1.17 Digital Twin + House Health + Property Timeline
1. **Azi:** Twin 3D, house health score, timeline istoric.
2. **Dependență umană:** User completează manual date twin.
3. **Autonom:** **Poate:** auto-update house health când request-uri se închid; auto-recomand când componente expiră.
4. **Detectează:** Componente cu garanție expirată, mentenanță lipsă.
5. **Repară:** **Poate:** auto-generate request preventiv pentru client (cu confirmare).
6. **Învață:** Istoric mentenanță per tip locuință.
7. **KPI nou:** `Preventive Requests %`.
8. **Agent AI:** `HomeGuardian` — proactively suggest mentenanță pe baza istoric + sezon.

---

## 2. Descoperiri critice (redundanțe & gaps)

### 2.1 Ce **NU** trebuie construit (există deja)
- ❌ Nou modul de scoring — există `autonomy/engine.py`.
- ❌ Nou scheduler — există APScheduler cu 30+ jobs.
- ❌ Nou sistem findings — există în QA/AI/Repair/Bug Memory.
- ❌ Nou dashboard admin — există 80+ pagini.
- ❌ Nou sistem alerting — există briefings + digests + notifications.

### 2.2 Ce **lipsește** cu adevărat (gap-uri reale)
| Gap | Impact | Prioritate |
|---|---|---|
| **Cross-module correlation** (nimic nu conectează Security spike ↔ Autonomy drop ↔ Bug pattern) | 🔴 Very High | P1 |
| **Auto-execution** după detectare (totul e read-only după alertă) | 🔴 Very High | P1 |
| **Escalation cascade** (try automat 1 → 2 → 3 → notify uman) | 🔴 High | P2 |
| **Feedback loop** (ce s-a rezolvat automat vs manual, cu ce cost) | 🟡 Medium | P2 |
| **Reflex triggers** (evenimente business → răspuns automat imediat, nu doar cron) | 🟡 Medium | P3 |
| **KYC/Dispute AI triage** | 🟠 High (unlock uman) | P3 |
| **Anomaly detection statistic** peste toate seriile de KPI | 🟢 Medium | P4 |

---

## 3. Concept central: **Autonomy Orchestrator**

Un singur serviciu backend nou (~500 linii) care:

```
[Signal Bus] ← consumă tot: cron ticks, incidents, findings, security events, autonomy snapshots
        ↓
[Correlator] → grupează semnale pe „situație" (ex: „ops score −8pts + 3 incidents in 1h + spike 5xx")
        ↓
[Playbook Engine] → pentru fiecare situație, o cascadă:
   1. Try automated fix A (ex: rerun sweep)
   2. If fail → Try B (ex: notify sub-admin)
   3. If fail → Try C (ex: create QA session + prompt Emergent-ready)
   4. If all fail → escalate to founder
        ↓
[Ledger] → înregistrează CE a încercat + REZULTAT + MINUTE UMAN SALVATE
        ↓
[Learner] → weekly, ajustează thresholds & playbooks (auto-tune extins)
```

**Punctul cheie:** *NU e un modul nou. E un dispecer transversal peste modulele existente.*

---

## 4. ROADMAP — pe priorități

### 🔴 PRIORITATE 1 — Self-Healing Infrastructure
> **Obiectiv:** Sistemul se repară singur pentru bug-uri operaționale banale.

| Feature | Impact | Complexitate | Dependențe | ROI (min umane / săpt.) | Human Dep. −% |
|---|---|---|---|---|---|
| **Autonomy Reflex** (score drop → auto sweep) | 🔴🔴🔴 | 🟢 Low | autonomy/engine, autopilot | ~90 min | −15% |
| **Smoke-Fail → Auto QA Session** | 🔴🔴🔴 | 🟢 Low | qa_copilot, admin_smoketest | ~120 min | −20% |
| **Webhook Retry Guardian** (Stripe/Resend fail → retry backoff, alert doar >3x) | 🔴🔴 | 🟢 Low | wallet, payments | ~60 min | −10% |
| **Data Integrity Auto-Fix** (orphan cleanup safe cases) | 🔴🔴 | 🟡 Med | admin_data_integrity | ~45 min | −8% |
| **Auth Health Reflex** (spike fail login → auto-block IP + notify) | 🔴🔴 | 🟢 Low | security_guard, auth | ~30 min | −5% |

- **Intervenție umană eliminată:** ~5h/săpt. admin verificare briefing + intervenție manuală
- **Poate rula fără fondator?** DA
- **Poate rula fără administrator?** DA (99% cazuri; edge cases escaladate)
- **Ce lipsește pentru 100%?** Zero-touch supervisor auto-restart în K8s (nu în scope aplicație).

---

### 🟠 PRIORITATE 2 — Operational Autopilot
> **Obiectiv:** Operațiuni zilnice (requests, disputes, marketplace) fără atingere umană pentru cazurile clare.

| Feature | Impact | Complexitate | Dependențe | ROI | Human Dep. −% |
|---|---|---|---|---|---|
| **Dispute AI Triage** (categorii + first response + propunere rezoluție) | 🔴🔴🔴 | 🟡 Med (LLM) | disputes, ai, LLM key | ~180 min | −25% |
| **KYC Auto-Approve** (OCR + doc integrity + face match; 70% auto) | 🔴🔴🔴 | 🔴 High | kyc, LLM vision | ~240 min | −30% |
| **Marketplace Medic** (auto-suspend >3 disputes/30d + auto-reactivate curat >90d) | 🔴🔴 | 🟢 Low | marketplace, disputes | ~90 min | −12% |
| **Request Stuck Resolver** (>72h fără oferte → auto-boost + notif specialiști) | 🟠🟠 | 🟢 Low | requests, matching, notifications | ~60 min | −8% |
| **Notification Fatigue Curator** (max N/user/zi, throttle inteligent) | 🟠 | 🟢 Low | notifications | ~20 min | −3% |

- **Intervenție umană eliminată:** ~10h/săpt.
- **Poate rula fără fondator?** DA
- **Poate rula fără administrator?** 80% da; KYC edge cases (docs suspicioase) escaladate.
- **Ce lipsește?** Legal review de la avocat pentru „auto-approve KYC" în UE (GDPR).

---

### 🟡 PRIORITATE 3 — Business Automation
> **Obiectiv:** Decizii business (roadmap, deprecation, growth) semi-automate cu propuneri argumentate.

| Feature | Impact | Complexitate | Dependențe | ROI | Human Dep. −% |
|---|---|---|---|---|---|
| **Roadmap Advisor** (adoption ↔ cost AI ↔ revenue → recomand deprecation/promotion) | 🔴🔴 | 🟡 Med | ai_governance, admin_dev_velocity, future_ideas | ~120 min | −15% |
| **Doc Keeper** (auto-doc on new endpoint) | 🟠 | 🟢 Low | docs_ai, openapi | ~30 min | −5% |
| **Finance Reconciler** (nightly Stripe ↔ DB cross-check) | 🔴🔴 | 🟡 Med | wallet, payments | ~60 min | −8% |
| **Pattern Hunter** (Bug Memory clustering + „meta-bug" auto-open) | 🔴🔴 | 🟡 Med | bug_memory_aggregator, LLM | ~90 min | −12% |
| **Compliance Watcher** (weekly audit + audit-debt trending) | 🟠 | 🟢 Low | admin_content_audit, admin_term_audit | ~30 min | −4% |

- **Intervenție umană eliminată:** ~5.5h/săpt. (fondator + admin).
- **Poate rula fără fondator?** Parțial — propunerile strategice cer confirmare.
- **Poate rula fără administrator?** DA.
- **Ce lipsește?** Definirea explicită a „revenue impact" per feature (nu există KPI unified).

---

### 🟢 PRIORITATE 4 — Predictive AI
> **Obiectiv:** Sistemul prezice probleme înainte să apară.

| Feature | Impact | Complexitate | Dependențe | ROI | Human Dep. −% |
|---|---|---|---|---|---|
| **Growth Sentinel** (anomaly detection statistic pe toate KPI-urile) | 🔴🔴 | 🟡 Med | analytics_growth, marketing_performance | ~90 min | −8% |
| **HomeGuardian** (proactive maintenance suggestion per client) | 🔴🔴 | 🟡 Med | digital_twin, house_health, property_timeline | ~indirect: retention +% | client-facing |
| **Churn Predictor** (specialist inactivity + client abandonment) | 🔴🔴 | 🔴 High | matching, reviews_v2 | ~indirect | strategic |
| **Cost Forecaster** (AI spend projection, alertă pre-budget) | 🟠 | 🟡 Med | ai_governance costs | ~30 min | −4% |

- **Intervenție umană eliminată direct:** modest (~2h/săpt.). **Efect indirect:** retention, revenue.
- **Poate rula fără fondator?** DA.
- **Poate rula fără administrator?** DA.
- **Ce lipsește?** Dataset suficient (>6 luni istoric) pentru modele predictive robuste.

---

### 🔵 PRIORITATE 5 — Marketplace Automation
> **Obiectiv:** Marketplace-ul se auto-organizează, curăță, optimizează.

| Feature | Impact | Complexitate | Dependențe | ROI | Human Dep. −% |
|---|---|---|---|---|---|
| **Specialist Auto-Onboarding** (docs upload → KYC triage → profile bootstrap) | 🔴🔴🔴 | 🔴 High | kyc auto, specialist_profile, specialist_progression | ~indirect: scaling | growth |
| **Ad Optimizer** (Meta/Google Ads API — Phase 3 backlog) | 🔴🔴🔴 | 🔴 High | marketing_campaigns, external APIs | ~indirect: CAC −20% | growth |
| **AI Content Studio** (Social Media AI — Phase 2 backlog) | 🔴🔴 | 🟡 Med | LLM, marketing_growth | ~indirect | growth |
| **Dynamic Fee Optimizer** (fee marketplace ajustat pe categorie + demand) | 🟠 | 🟡 Med | marketplace_offers | ~indirect | revenue |
| **Trust Auto-Boost** (reviews + response time → auto-featured spots) | 🟠 | 🟢 Low | reviews_v2, marketplace, trust | ~indirect | growth |

- **Intervenție umană eliminată:** relativ mică (~2h/săpt.), dar efect **scalability** major.
- **Poate rula fără fondator?** DA.
- **Poate rula fără administrator?** DA (după calibrare inițială).
- **Ce lipsește?** Bugete Ads + credentiale Meta/Google (P0 blocker P5).

---

## 5. Autonomy Orchestrator — arhitectura sugerată (fără implementare)

```
/backend/orchestrator/
  ├── bus.py              # signal ingestion (in-memory + Mongo tail)
  ├── correlator.py       # groupare semnale în „situații"
  ├── playbooks/          # YAML/py descriptors, per situație
  │   ├── score_drop.yaml
  │   ├── smoke_fail.yaml
  │   ├── webhook_fail.yaml
  │   ├── dispute_stuck.yaml
  │   └── ...
  ├── executor.py         # rulează cascade (try A → B → C → escalate)
  ├── ledger.py           # log tot ce s-a încercat + rezultat + ROI
  └── learner.py          # weekly auto-tune thresholds & playbooks
```

**Interoperabilitate:** consumă hook-urile existente (`autopilot_runs`, `incidents`, `qa_findings`, `security_events`, `autonomy_snapshots`). **Nu duplică nimic.**

**Pagină admin nouă:** doar 1 — `AutonomyOrchestratorPage` — vizualizare live „ce a făcut orchestratorul azi + minute umane salvate + situații escaladate".

---

## 6. Ordonare finală după valoarea autonomiei

| # | Propunere | Umane eliminate/săpt. | Necesită fondator? | Necesită admin? | Rating Autonomie |
|---|---|---|---|---|---|
| 1 | Autonomy Orchestrator (schelet) | fundație | NU | NU | ⭐⭐⭐⭐⭐ |
| 2 | Smoke-Fail → Auto QA Session | ~120 min | NU | NU | ⭐⭐⭐⭐⭐ |
| 3 | Autonomy Reflex | ~90 min | NU | NU | ⭐⭐⭐⭐⭐ |
| 4 | KYC Auto-Approve | ~240 min | NU | 70% NU | ⭐⭐⭐⭐⭐ |
| 5 | Dispute AI Triage | ~180 min | NU | 60% NU | ⭐⭐⭐⭐⭐ |
| 6 | Webhook Retry Guardian | ~60 min | NU | NU | ⭐⭐⭐⭐ |
| 7 | Marketplace Medic | ~90 min | NU | NU | ⭐⭐⭐⭐ |
| 8 | Pattern Hunter | ~90 min | NU | NU | ⭐⭐⭐⭐ |
| 9 | Finance Reconciler | ~60 min | NU | NU | ⭐⭐⭐⭐ |
| 10 | Roadmap Advisor | ~120 min | 50% (aprobare) | NU | ⭐⭐⭐ |
| 11 | Data Integrity Auto-Fix | ~45 min | NU | NU | ⭐⭐⭐ |
| 12 | Growth Sentinel | ~90 min | NU | NU | ⭐⭐⭐ |
| 13 | Doc Keeper | ~30 min | NU | NU | ⭐⭐⭐ |
| 14 | HomeGuardian (client-facing) | retention | NU | NU | ⭐⭐⭐ |
| 15 | Ad Optimizer (P5) | CAC | NU | NU | ⭐⭐⭐ |
| 16 | Compliance Watcher | ~30 min | NU | NU | ⭐⭐ |
| 17 | Cost Forecaster | ~30 min | NU | NU | ⭐⭐ |
| 18 | Notification Curator | ~20 min | NU | NU | ⭐⭐ |
| 19 | Churn Predictor | strategic | NU | NU | ⭐⭐ |
| 20 | Dynamic Fee Optimizer | revenue | 50% | NU | ⭐⭐ |

**Total intervenție umană estimată redusă în 6 luni:** ~22 ore/săptămână (admin + fondator combinat) → **90% autonomie operațională**.

---

## 7. Metrici de urmărit (pentru Emergent = Chief Autonomy Officer)

Fiecare feature livrat trebuie să răspundă la 5 întrebări. Emergent le raportează în briefing:

1. **Ce intervenție umană elimină concret?** (task numit, workflow numit)
2. **Câte minute economisește pe săptămână?** (măsurat, nu estimat)
3. **Câte decizii automatizează?** (count, cu breakdown auto/escalate)
4. **Poate rula fără fondator?** DA/NU + de ce
5. **Poate rula fără administrator?** DA/NU + de ce + ce lipsește pentru DA

**KPI global nou:** `Human Dependency Index (HDI)` = (ore intervenție umană / săptămână) / (număr activ users). Țintă: scădere continuă lună de lună.

---

## 8. Recomandare finală (concentrat)

1. **NU** mai adăuga module noi. **DA** — construiește Orchestrator-ul + primele 3 playbook-uri (P1).
2. **NU** duplica infrastructura. **DA** — expune tot ca „signal source" pentru orchestrator.
3. **NU** măsura succes în feature count. **DA** — măsura succes în `Human Dependency Index` scăzând.
4. **Fondator = target la ridicat**: platforma trebuie să meargă 2 săptămâni fără fondator online și doar 1 escalation critic/săpt.
5. **Admin = target la mediu**: doar review săptămânal de rapoarte, nu intervenție zilnică.

**Ordinea concretă de dezvoltare (recomandat pentru Emergent):**
- Sprint 1 (~30-40 credite): Autonomy Orchestrator core + 3 playbooks P1 (Smoke-Fail, Autonomy Reflex, Webhook Retry).
- Sprint 2 (~30-40 credite): Dispute AI Triage + Marketplace Medic + Pattern Hunter.
- Sprint 3 (~40-50 credite): KYC Auto-Approve (necesită LLM vision + juridic).
- Sprint 4+: P3-P5 în funcție de business needs.

---

**Fin document. Fără cod scris. Fără fișier de aplicație atins.**
