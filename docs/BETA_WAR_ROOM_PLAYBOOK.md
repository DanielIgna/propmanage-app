# PROPMANAGE BETA WAR ROOM — PLAYBOOK OPERAȚIONAL
Status: ACTIV · Data: 27 Iun 2026 · Mod: BETA WAR ROOM (feature freeze non-critic)
Regula supremă: **următorul ciclu de dezvoltare e condus de comportamentul REAL al utilizatorilor, nu de presupuneri.**

---

## 1. FOUNDER LAUNCH CHECKLIST (execuție, în ordine)
1. [ ] **Stripe LIVE**: claim cont → verifică în War Room (/admin/war-room) că statusul devine „live".
2. [ ] **Resend DNS** (Rackhost): adaugă înregistrările → verifică /admin (integration_health) → follow-up-ul autonom pornește singur.
3. [ ] **Prod curat**: redeploy FĂRĂ `SEED_DEMO_DATA` → `POST /api/admin/beta/purge-demo` cu `dry_run:true` (verifică lista) → apoi `dry_run:false`. NU în preview!
4. [ ] Smoke pe https://propmanage.ro: landing → register → adaugă proprietate → upload document → /scorul-casei.
5. [ ] Trimite invitațiile valului 1 (5 proprietari + 3 specialiști „prieteni").
6. [ ] Bookmark zilnic: **/admin/beta-cockpit** (funnel+VoC) · **/admin/beta-issues** (board) · **/admin/war-room** (venit).

## 2. BETA COCKPIT DASHBOARD — LIVE ✅
`/admin/beta-cockpit` (super-admin): vizitatori, înregistrări REALE (interni excluși), funnel proprietari 6 pași, funnel specialiști, **TTFV median** (register→primul document), Passport Analytics rollup, cereri suport, **gate-urile EO-026** (80/70/50/50), Voice of Customer. Ferestre 7/30/90 zile.

## 3. USER FEEDBACK COLLECTION — LIVE ✅
- **VoC widget** în dashboardurile client+specialist (Setări → „Feedback beta"; 6 întrebări, dedupe pe zi) → colecția `beta_feedback` → vizibil în Beta Cockpit.
- Cereri suport → agregate în cockpit; leads → Unified Leads.
- **Regulă War Room**: orice feedback acționabil devine issue pe board (§4) în aceeași zi.

## 4. ISSUE PRIORITIZATION BOARD — LIVE ✅ (nou)
`/admin/beta-issues` (super-admin): adaugi rapid bug/feature/feedback cu severitate P0–P3, filtrezi pe status, schimbi severitate/status inline. API: `POST/GET/PATCH /api/admin/beta/issues`.
- **P0** = blocant beta (user nu poate continua / date pierdute / plată eșuată) → fix <24h.
- **P1** = major (flux principal degradat) → fix <72h.
- **P2/P3** = batch săptămânal, decis la Weekly Review.

## 5. ANALYTICS DASHBOARD — LIVE ✅
- Funnel public → register: `GET /api/admin/growth/funnel` + Beta Cockpit (conversie vizitatori).
- Passport: per proprietate (panoul „Statistici" al ownerului) + rollup admin.
- Surse: UTM pe share (/scorul-casei, pașaport) → apar în funnel.

## 6. FIRST WEEK MONITORING CHECKLIST (zilnic, ~15 min)
- [ ] Beta Cockpit (7z): înregistrări noi? funnel-ul unde pierde? TTFV?
- [ ] Beta Issues: P0/P1 deschise? (ținta: 0 P0 la finalul zilei)
- [ ] VoC nou? → transformă în issues.
- [ ] War Room: plăți reale? escrow blocat?
- [ ] Notification Center: anomalii/urgențe.
- [ ] Un mesaj personal către fiecare user nou din ziua respectivă (founder touch).

## 7. DAILY BETA REPORT — TEMPLATE (max 10 rânduri, în /admin/beta-cockpit + board)
```
ZIUA N · [data]
Utilizatori noi: X proprietari / Y specialiști · Activare pas 1: Z%
TTFV median: N min · Funnel blocaj principal: [pasul]
P0 deschise: N · P1 deschise: N · Fixate azi: N
VoC azi: [1 citat semnificativ]
Venit real: X RON (cumulat: Y)
Acțiunea de mâine: [UNA singură, cea mai valoroasă]
```

## 8. WEEKLY BETA REVIEW — TEMPLATE
```
SĂPTĂMÂNA N · [interval]
1. Gate-urile EO-026: activare 80%→[..]% · document 70%→[..]% · cerere 50%→[..]% · specialist activ 50%→[..]%
2. TTFV trend: [..] → [..] min
3. Top 3 blocaje funnel (cu dovezi din cockpit/VoC)
4. Issues: deschise/fixate/livrate · P0 recurente?
5. Ce spun userii (3 citate: pozitiv / negativ / surprinzător)
6. Decizie ciclu următor (PPOS Council): fix-uri claritate vs CX-4 vs pivot — DOAR pe date
7. Founder actions necesare
```

## 9. CRITICAL BUG WORKFLOW (P0)
1. Detectare (user/VoC/suport/anomalie) → **issue P0 pe board în <15 min** (sursa + email reporter).
2. Reproducere pe preview → RCA → fix DOAR presentation/config dacă se poate; orice fix pe API/DB = mesaj explicit către Fondator (regula HIGH-RISK rămâne).
3. Test regresie țintit (testing agent la nevoie) → deploy → status „fixed".
4. Confirmare cu userul raportor → „shipped" + notă în Daily Report.
5. Post-mortem 3 rânduri în notes: cauză, de ce a scăpat, prevenție.

## 10. FEATURE REQUEST WORKFLOW
1. Cerere (VoC/direct) → issue `feature` pe board, severitate implicită P3.
2. La Weekly Review: se ridică la P2 DOAR dacă ≥3 useri diferiți o cer SAU deblochează un gate EO-026.
3. Filtrul PPOS: crește claritate/încredere/activare/venit? Dacă nu — „wont_fix" cu motiv onest.
4. **Feature freeze**: nimic nou nu se construiește decât dacă rezolvă o problemă REALĂ descoperită în beta.

## 11. USER JOURNEY TRACKING — LIVE ✅
`/admin/user-timeline`: cronologia completă per user (cont→verificare→cereri→match→escrow→plăți→review). Folosește-l la fiecare user blocat (înainte să-l suni, vezi exact unde s-a oprit).

## 12. ACTIVATION FUNNEL TRACKING — LIVE ✅
Beta Cockpit funnel proprietari: register → proprietate → document → pașaport → cerere → plată; specialiști: register → profil → verificare → primul accept → prima lucrare. Măsurat DOAR pe conturi reale.

## 13. TIME TO FIRST VALUE — LIVE ✅
TTFV = register → primul document încărcat (mediană, în cockpit). Țintă beta: **<15 min**. Secundar: register → prima cerere; specialist: register → primul accept.

## 14. BETA SUCCESS KPIs (gate-urile deciziei post-beta)
| KPI | Țintă | Unde se măsoară |
|---|---|---|
| Activare pas 1 (proprietate adăugată) | ≥80% | Beta Cockpit gate 1 |
| Primul document încărcat | ≥70% | gate 2 |
| Prima cerere de serviciu | ≥50% | gate 3 |
| Specialist activ (≥1 accept) | ≥50% | gate 4 |
| TTFV median | <15 min | cockpit KPI |
| VoC „recomandă" | ≥70% da | cockpit VoC |
| P0 deschise la final de zi | 0 | Issues Board |
| Prima plată reală | ≥1 | War Room |

**Decizie post-beta**: toate gate-urile verzi → scale (val 2 + CX-4); 2+ roșii → fix-uri de claritate și repetă valul; contradicții → AI Product Review 2.0 pe date reale + PPOS Council.
