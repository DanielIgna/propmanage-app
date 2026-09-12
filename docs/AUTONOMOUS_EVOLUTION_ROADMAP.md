# PropManage Autonomous Evolution Roadmap
**Rol: Chief Autonomy Officer (CAO) · Data: 11 Iunie 2026 · Tip: STRICT analiză și planificare — zero implementare**

> Principiul CAO: întrebarea nu mai este „ce modul mai construim?", ci **„cum elimin următoarea intervenție umană?"**
> Scopul nu este o aplicație mai mare. Scopul este o aplicație care funcționează singură.

---

## 0. Ce strat de autonomie EXISTĂ deja (ca să nu dublăm nimic)

Constatare esențială: **Autonomy Orchestrator-ul propus EXISTĂ deja ca fundație** (`orchestrator/engine.py` + `playbooks.py`, Sprint 1-3). Nu trebuie construit — trebuie **extins**.

| Componentă existentă | Ce face azi |
|---|---|
| **Autonomy Engine** (`autonomy/engine.py`) | Scor autonomie 94.4 (tier self-driving), determinist, read-only, 4 axe |
| **Autonomy Autopilot** (`autonomy/autopilot.py`) | Bootstrap automat: smoke monitor, auto-match schedule, settings snapshots |
| **Autonomy Orchestrator** (`orchestrator/`) | Flow semnal → playbook → ledger. **9 playbook-uri LIVE**: smoke_fail_to_qa, autonomy_reflex, webhook_retry_guardian, category_visibility_gate, dispute_ai_triage, medic (suspendare specialiști cu dispute), etc. |
| **Control Tower** | „Problemele vin sortate, cu soluția atașată" — Attention Layer + Autonomy Report |
| **AI Command Center** (nou, Iun 2026) | Feed zilnic + Top 5 recomandări AI, interconectat cu Business Health |
| **Business Health** (nou) | 8 scoruri departamentale, snapshot zilnic, roșu → alertă automată |
| **Automation Center** (nou) | 3 reguli Dacă→Atunci cu executor real (dar rulare MANUALĂ — gap-ul #1) |
| **Notification Center AI** (nou) | Agregare prioritizată + ack |
| **Smoke Test auto-monitor** | Rulează la 30 min, alertă la FAIL |
| **Security Guard** (Phase 47) | Heuristici deterministe, blocare fără LLM, mirror în findings |
| **Marketing Performance Loop** | Buclă închisă predict→measure→learn→recalibrate (singura buclă de învățare completă din platformă) |

**Concluzie**: platforma e la **Autonomy Level 2.5** — detectează mult, propune mult, execută puțin fără om. Gap-ul principal nu e detecția, ci **execuția autonomă + bucla de învățare generalizată**.

---

## 1. Analiza per modul (cele 8 întrebări CAO)

Format per modul: **①** ce face azi · **②** dependență umană · **③** ce poate deveni autonom · **④** ce detectează automat · **⑤** ce poate repara automat · **⑥** ce poate învăța per incident · **⑦** KPI nou · **⑧** AI Agent necesar

### 1.1 Autonomy Engine
① Scor 0-100 pe 4 axe, recomandări statice. ② Omul citește scorul și decide; auto-tune doar lunea. ③ Scăderea de scor să declanșeze direct playbook corectiv (parțial există: `autonomy_reflex`). ④ Drift pe orice axă. ⑤ Re-rulare seed/sweep pe axa căzută. ⑥ Care sweep-uri au recuperat scorul și în cât timp. ⑦ **MTTR-Autonomy** (minute de la drift la recuperare fără om). ⑧ Nu unul nou — extinderea `autonomy_reflex` la toate axele.

### 1.2 Autonomy Orchestrator ⭐ (stratul transversal cerut)
① 9 playbook-uri semnal→acțiune cu ledger. ② Omul activează/dezactivează playbook-uri; multe semnale nu au încă emitenți. ③ **Orice alertă din Command Center / Business Health / Notification Center să devină semnal** — azi sunt doar afișate. ④ Tot ce emit modulele. ⑤ Tot ce au playbook. ⑥ Ledger-ul există dar nu e minat: rata de succes per playbook trebuie să regleze automat agresivitatea. ⑦ **Interventions Prevented/săptămână** + **Playbook Success Rate**. ⑧ **Escalation Judge** — mic agent care decide: rezolv singur / reîncerc / escaladez la om (cu buget de încercări).

### 1.3 AI Performance Copilot (IT Copilot)
① Analiză echipă dev la cerere, digest duminical. ② Omul apasă „analizează"; omul citește. ③ Rulare automată la fiecare sprint + injectare concluziilor în ToDo Board (endpoint bulk există deja). ④ Colaborator at-risk, sprint risk. ⑤ Nimic (domeniu uman) — dar poate PRE-completa acțiunile. ⑥ Ce recomandări au fost acceptate de fondator (feedback loop pe utilitate). ⑦ **Recommendation Acceptance Rate**. ⑧ Nu — e deja agentul; îi lipsește doar autonomia de rulare.

### 1.4 AI Investigator
① Findings + investigații la cerere, daily auto-scan 03:00. ② Omul triază findings. ③ Findings low-risk cu fix cunoscut → direct în retry/sweep; doar high → om. ④ Anomalii, erori, pattern-uri. ⑤ Ce are playbook (ex: reseed, retry). ⑥ Fingerprint-ul incidentului → Bug Memory (parțial există). ⑦ **Auto-Closed Findings %**. ⑧ Folosește Escalation Judge (1.2) — nu agent separat.

### 1.5 QA Copilot + Bug Memory
① Sesiuni QA asistate; Bug Memory = view unificat findings QA+AI. ② Omul creează sesiuni, omul leagă bug-urile de cauze. ③ `smoke_fail_to_qa` există — extins: orice 500 repetat creează sesiune QA automat. ④ Regresii (Trends 30d există). ⑤ Nimic direct — dar poate genera pașii de reproducere automat. ⑥ **Cel mai valoros**: „acest simptom → această cauză → acest fix" ca knowledge base interogabilă de orice playbook. ⑦ **Repeat-Bug Rate** (bug-uri cu fingerprint deja văzut). ⑧ **Root-Cause Matcher** — la orice incident nou, caută în Bug Memory și atașează fix-ul istoric la alertă.

### 1.6 Documentation (docs_ai + Operating Manual)
① Upload + chunking + căutare; manual operațional static. ② Omul actualizează manualul după fiecare feature. ③ Generare automată de secțiuni de manual din PRD/CHANGELOG la fiecare release. ④ Documente expirate / contradicții (nu azi — propus). ⑤ Regenerare secțiuni stale. ⑥ Ce întrebări pun adminii și nu găsesc răspuns → gap-uri doc. ⑦ **Doc Freshness %**. ⑧ **Doc Keeper** — low priority, ROI mic vs restul.

### 1.7 Audit (admin_actions_log, legal, demo activity)
① Loghează tot; anomaly detector e în backlog P0 (PRD). ② Omul citește logurile doar când e o problemă. ③ Detectorul de anomalii din PRD (500+ endpoint-uri/oră, 10+ 4xx/5min, out-of-scope) → semnal orchestrator, nu doar email. ④ Comportament anormal demo/admin. ⑤ Blocare temporară cont demo suspect (reversibilă, cu notificare). ⑥ Praguri auto-calibrate pe baseline-ul fiecărui user. ⑦ **Anomalies Auto-Contained %**. ⑧ **Audit Sentinel** = anomaly detectorul din PRD + acțiune de containment.

### 1.8 Marketplace (requests, matching, offers)
① Smart matching zone-based, auto-match schedule pornit de autopilot, medic suspendă specialiști problematici. ② Omul intervine la cereri >48h (azi doar alertate), la categorii fără supply. ③ **Cererea blocată să se auto-repare**: re-matching cu rază extinsă → notificare push top 3 specialiști → ridicare lead fee temporară → abia apoi om. ④ Cereri stale, deficit categorii (Marketplace Intel). ⑤ Escaladare progresivă de matching (3 trepte automate). ⑥ Ce treaptă a deblocat cererea per categorie/județ → strategia devine adaptivă. ⑦ **Requests Self-Resolved %** (deblocate fără om). ⑧ **Matchmaker Agent** — playbook nou pe semnalul `request_stale_24h`.

### 1.9 Financial (payments, escrow, cockpit)
① Cockpit complet, webhook_retry_guardian pentru plăți eșuate. ② Omul confirmă escrow-uri (21.150 lei blocați azi), omul urmărește plăți pending. ③ **Escrow nudge automat**: la X zile held → reminder client → la Y zile → propunere de auto-release cu aprobare 1-tap (nu auto-release fără om — risc juridic). Plăți initiated >24h → email recovery automat. ④ Escrow stale, pending payments, drift MRR. ⑤ Retry plăți, remindere, recovery emails. ⑥ Ce nudge convertește (rata de confirmare per template). ⑦ **Escrow Age P90** (zile până la confirmare). ⑧ **Treasury Agent** — 2 playbook-uri noi pe semnale `escrow_stale`, `payment_abandoned`.

### 1.10 Requests (ciclul de viață)
① Creare→match→escrow→complete; reminder e regulă manuală în Automation Center. ② Omul apasă „Rulează acum". ③ **Gap-ul #1 al platformei: scheduler-ul pentru regulile active** — infrastructura APScheduler există (15+ joburi deja). ④ Tot (regulile există). ⑤ Tot ce au regulile. ⑥ Rata de rezolvare post-reminder per tip de regulă. ⑦ **Rules Auto-Run/săptămână**. ⑧ Niciun agent — un singur job orar care rulează regulile `enabled=true`.

### 1.11 Monitoring (healthcheck, smoketest, status, incidents)
① Smoke la 30 min cu alertă; incidents postate MANUAL de admin. ② Omul creează incidentul pe /status după ce primește alerta. ③ **Smoke FAIL persistent (2 consecutive) → incident auto-creat pe /status + auto-resolved la recuperare**. ④ Downtime, degradare. ⑤ Restart-level fixes nu (sandbox), dar comunicarea publică da. ⑥ MTTR istoric per tip de probă. ⑦ **Incidents Auto-Published %**. ⑧ Playbook `smoke_fail_to_incident` — extensie 20 linii logică la ce există.

### 1.12 Security (security_guard, ai_security, KYC)
① Guard determinist blochează exfiltrare; KYC auto-approve ≥92 ACTIV (singura decizie de business deja complet autonomă!). ② Omul revizuiește KYC 30-91 scor; omul citește security events. ③ Lărgirea benzii auto: auto-reject <15 cu flags negative clare (azi doar auto-approve). ④ Fraud patterns, brute force. ⑤ Blocare progresivă (există în guard). ⑥ Scorurile KYC contestate → recalibrarea pragului. ⑦ **KYC Human-Review %** (țintă: sub 20%). ⑧ Nu — extindere config existent.

### 1.13 Development (ai_dev_team, dev_velocity, architecture board)
① Analiză cod read-only, velocity săptămânal. ② Omul decide refactorizări. ③ Findings de cod → ToDo Board automat (convenția bulk există). ④ Datorie tehnică, drift arhitectural. ⑤ Nimic (nu auto-modificăm cod în producție — decizie corectă). ⑥ Ce findings au devenit bug-uri reale → prioritizare predictivă. ⑦ **Findings→Bug Conversion Rate**. ⑧ Nu — ROI mic, risc mare.

### 1.14 Statistics (bi_moe, analytics_growth)
① Dashboard-uri + AI Insights la cerere. ② Omul deschide pagina ca să afle că ceva a scăzut. ③ **Insights push, nu pull**: delta >X% pe orice KPI cheie → semnal orchestrator → apare în Command Center/Notification fără vreun click. ④ Anomalii de trend. ⑤ Nimic — dar alimentează Matchmaker/Treasury/Marketing agents. ⑥ Ce delte s-au dovedit false alarms → praguri adaptive. ⑦ **Time-to-Awareness** (minute de la eveniment la alertă). ⑧ **Pulse Watcher** — job zilnic care compară KPI vs baseline.

### 1.15 Marketing (growth, campaigns, performance loop)
① Cea mai matură buclă: Auto-Trigger scan → draft campanie → approve → measure → learn → recalibrate. ② Omul apasă scan (există și cron?), omul aprobă (corect), omul loghează performanța MANUAL. ③ Scan-ul pe cron zilnic; **logging performanță automat** când vin API keys Meta/Google (Faza 3 din PRD — dependență externă). ④ Oportunități MoM ≥30%. ⑤ Draft-uri gata de aprobat. ⑥ Deja învață (calibration hints). ⑦ **Campaigns Auto-Drafted/săptămână**. ⑧ Există — îi lipsește doar cron-ul + integrarea externă.

### 1.16 Module noi (Command Center, Business Health, Notification, CEO)
① Agregă și prioritizează. ② Omul deschide pagina și apasă „Generează". ③ **Generare automată dimineața (cron 07:00) + email către fondator** — infrastructura Resend + scheduler există. ④ Tot. ⑤ Nimic direct — sunt stratul de decizie. ⑥ Ce recomandări sunt bifate done vs ignorate → AI-ul învață ce contează pentru TINE. ⑦ **Recommendations Done Rate**. ⑧ Nu — cron + un prompt îmbunătățit cu istoricul done/ignored.

---

## 2. Roadmap pe 5 priorități

Legendă: Impact/Complexitate/ROI pe scară 1-5 · RIU = Reducerea Intervenției Umane (min/săptămână estimat)

### 🔴 PRIORITATE 1 — Self-Healing Infrastructure
| # | Propunere | Impact | Complex. | Dependențe | ROI | RIU |
|---|---|---|---|---|---|---|
| 1.1 | **Scheduler pentru Automation Center** — job orar rulează regulile enabled | 5 | 1 | APScheduler (există) | ⭐5 | ~90 min/săpt |
| 1.2 | **Smoke FAIL → incident auto pe /status** + auto-resolve | 4 | 1 | smoketest + incidents (există) | 5 | ~30 min/incident |
| 1.3 | **Autonomy Reflex extins pe toate axele** + MTTR-Autonomy KPI | 4 | 2 | autonomy_reflex (există) | 4 | ~45 min/săpt |
| 1.4 | **Root-Cause Matcher** — incident nou → fix istoric din Bug Memory atașat automat la alertă | 4 | 2 | bug_memory (există) | 4 | ~20 min/incident |

**CAO check 1.1** (exemplu): Elimină apăsarea manuală „Rulează acum" ×3 reguli ×zilnic. Economisește ~90 min/săpt. Automatizează ~21 decizii/săpt. Fără fondator? **DA**. Fără admin? **DA** (regulile au fost deja aprobate prin enable). Lipsă: nimic — o zi de lucru.

### 🟠 PRIORITATE 2 — Operational Autopilot
| # | Propunere | Impact | Complex. | Dependențe | ROI | RIU |
|---|---|---|---|---|---|---|
| 2.1 | **Command Center pe cron 07:00 + email digest fondator** | 5 | 1 | Resend + scheduler (există) | 5 | ~60 min/săpt |
| 2.2 | **Alerte → semnale orchestrator** (Business Health roșu, Notification items emit semnal, nu doar UI) | 5 | 2 | orchestrator (există) | 5 | ~120 min/săpt |
| 2.3 | **Escalation Judge** — agent decide rezolv/reîncerc/escaladez, cu buget | 5 | 3 | 2.2 | 4 | ~90 min/săpt |
| 2.4 | **Audit Sentinel** (anomaly detector din PRD P0) + containment auto pe conturi demo | 4 | 2 | demo_activity_logs (există) | 4 | ~30 min/săpt |
| 2.5 | **Pulse Watcher** — KPI delta → alertă push (Time-to-Awareness) | 4 | 2 | analytics (există) | 4 | ~45 min/săpt |

**CAO check 2.3**: Elimină triajul uman al alertelor low/medium. ~50 decizii/săpt automatizate. Fără fondator? DA. Fără admin? **PARȚIAL** — high severity escaladează intenționat la om (corect, nu e o lipsă, e design).

### 🟡 PRIORITATE 3 — Business Automation
| # | Propunere | Impact | Complex. | Dependențe | ROI | RIU |
|---|---|---|---|---|---|---|
| 3.1 | **Matchmaker Agent** — cereri stale: escaladare 3 trepte automată (rază → push top3 → boost) | 5 | 3 | matching (există) | 5 | ~120 min/săpt |
| 3.2 | **Treasury Agent** — escrow stale nudges + payment recovery emails | 5 | 2 | Resend (există) | 5 | ~90 min/săpt |
| 3.3 | **KYC bandă lărgită** — auto-reject <15 cu flags clare (azi doar auto-approve ≥92) | 3 | 1 | kyc config (există) | 4 | ~30 min/săpt |
| 3.4 | **Recomandări done/ignored → feedback în promptul AI** (AI-ul învață preferințele fondatorului) | 4 | 1 | command_center_recos (există) | 4 | calitate, nu timp |

**CAO check 3.2**: Elimină urmărirea manuală a 46 escrow-uri blocate (21.150 lei azi). ~15 decizii/săpt. Fără fondator? DA. Fără admin? **NU pentru release-ul efectiv al banilor** — de ce: risc juridic/financiar; ce lipsește: politică asumată de auto-release + prag valoric (decizie de business, nu tehnică).

### 🟢 PRIORITATE 4 — Predictive AI
| # | Propunere | Impact | Complex. | Dependențe | ROI | RIU |
|---|---|---|---|---|---|---|
| 4.1 | **Findings→Bug prediction** — prioritizare findings după probabilitatea de a deveni bug real | 3 | 3 | bug memory istoric | 3 | ~30 min/săpt |
| 4.2 | **Praguri adaptive** — false alarms reduc sensibilitatea per semnal automat | 4 | 3 | 2.2 ledger | 4 | ~20 min/săpt |
| 4.3 | **Business Health forecast** — snapshot-urile zilnice (există de azi) → predicție 7 zile per departament | 3 | 2 | business_health_history | 3 | anticipare |
| 4.4 | **Churn predictor clienți** — scorare inactivitate → alimentează client_reactivation automat | 4 | 3 | automation_center | 4 | ~40 min/săpt |

### 🔵 PRIORITATE 5 — Marketplace Automation
| # | Propunere | Impact | Complex. | Dependențe | ROI | RIU |
|---|---|---|---|---|---|---|
| 5.1 | **Auto-Trigger scan pe cron zilnic** (azi buton) | 4 | 1 | există tot | 5 | ~15 min/săpt |
| 5.2 | **Deficit → campanie recrutare draft automat** (Marketplace Intel × Campaign Generator) | 5 | 2 | ambele există | 5 | ~60 min/săpt |
| 5.3 | **Marketing performance logging automat** | 5 | 4 | ⚠️ chei API Meta/Google (extern) | 3 | ~60 min/săpt |
| 5.4 | **Dynamic lead fee** în limite setate (Autonomy Level 4) | 4 | 4 | 3.1 matur + politică | 3 | strategic |

---

## 3. Ordinea finală după valoarea adusă autonomiei

1. **Scheduler Automation Center** (1.1) — o zi de lucru, deblochează tot Level 3
2. **Alerte → semnale orchestrator** (2.2) — transformă 4 module de afișare în 4 module de acțiune
3. **Command Center cron + email** (2.1) — fondatorul nu mai deschide aplicația ca să afle
4. **Matchmaker Agent** (3.1) — atacă direct metrica de business (cereri blocate)
5. **Treasury Agent** (3.2) — 21.150 lei blocați azi e cel mai scump „todo" al platformei
6. **Escalation Judge** (2.3) — creierul triajului
7. **Smoke → incident auto** (1.2) — transparență fără om
8. **Audit Sentinel** (2.4) — era deja P0 în PRD
9. **Pulse Watcher** (2.5)
10. **Root-Cause Matcher** (1.4)
… restul conform tabelelor.

## 4. KPI global nou: Human Dependency Index (HDI)
`HDI = intervenții umane necesare/săptămână` — măsurat din: alerte neescaladate automat + butoane „Rulează/Generează" apăsate manual + decizii în cozi (KYC review, dispute, escrow). **Ținta trimestrului: -60%.** Se afișează în Autonomy Engine ca a 5-a axă.

## 5. Ce NU propunem (anti-bloat, conform mandatului)
- Niciun modul UI nou — toate propunerile folosesc paginile existente.
- Nicio auto-modificare de cod în producție (Development rămâne read-only).
- Niciun auto-release de bani fără aprobare 1-tap (risc juridic).
- Doc Keeper, forecast-uri exotice — ROI mic, amânate explicit.

---
*Document generat de agentul Emergent în rol de CAO. Nicio linie de cod nu a fost modificată, nicio colecție nu a fost scrisă pentru acest task.*
