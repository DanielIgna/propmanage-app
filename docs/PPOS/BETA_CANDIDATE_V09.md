# PROPMANAGE BETA CANDIDATE v0.9 — READINESS PACKAGE
Status: LIVRAT · Data: 27 Iun 2026 · Owner: Product Team (EO v5.0 SPRINT MODE)
Bază de dovezi: iteration_138–142 (E2E 100%), PPOS scorecard, LAUNCH_READINESS_REPORT_1_0, PRODUCTION_READINESS_CHECKLIST.

---

## 1. BETA READINESS REPORT
- **Verdict: BETA CANDIDATE READY (funcțional).** Toate journey-urile trec 100% (iteration_138/139), UX-ul PPOS P3a→P3d + Sprint Polish livrat și regresat (iteration_140/141/142 — zero regresii).
- Desktop = workspace profesional (client 8+4, specialist Mission Control split-view, Property Hub record page Notion-style). Mobil = task-first, stivă simplă, FAB, bottom nav.
- Scoruri UX (ultimul re-audit + estimare post P3b-d): media platformă ~75 → ~85 (desktop autentificat a crescut de la ~52 prin workspace-uri). Gate-ul 95 se re-măsoară la auditul de 5 faze (după feedback beta real).
- **Blocante NON-cod (doar Fondator)**: Stripe LIVE claim · Resend DNS (Rackhost) · redeploy prod fără `SEED_DEMO_DATA` + purge demo.

## 2. CRITICAL ISSUES (cod)
- **Niciunul deschis.** Ultimul (logout fără redirect) fixat + verificat în iteration_142. Zero bug-uri critice în ultimele 3 rulări de testare.

## 3. NICE-TO-HAVE IMPROVEMENTS
1. HomeSkeleton pe right-rail-ul clientului (flash gol ~2s la mount — cosmetic, notat de QA).
2. Lazy-render pe secțiunile off-screen din Property Hub mobil (paint inițial mai ușor).
3. Tabel real cu sortare/bulk pentru „Lucrările mele" specialist (acum grid 2 col — suficient pt beta).
4. Focus-trap + ESC pe drawere/sheets (a11y avansat).
5. Mini-map / căutare globală client (CTRL+K există în backlogul admin).

## 4. FOUNDER CHECKLIST (înainte de invitații)
- [ ] Stripe: claim cont LIVE (checkout-ul e gata, webhook + poll implementate).
- [ ] Resend: DNS pe domeniul propriu (Rackhost) — emailurile tranzacționale + follow-up autonom se activează singure după verificare.
- [ ] Redeploy producție FĂRĂ `SEED_DEMO_DATA=true` + rulează `POST /api/admin/beta/purge-demo` (dry_run întâi!) pe prod.
- [ ] Verifică https://propmanage.ro după purge (landing, register, /scorul-casei).
- [ ] Invită 10–20 proprietari + 5–10 specialiști reali (lista EO-026).
- [ ] Urmărește Beta Cockpit (/admin/beta-cockpit) — gate-urile 80/70/50/50 + VoC.

## 5. FIRST USER JOURNEY CHECKLIST (proprietar nou)
- [x] Register (telefon opțional) → /client cu UN singur pas ghidat (hero J0, zero zgomot).
- [x] Adaugă proprietatea = 1 click din hero.
- [x] Pasul 2: primul document → celebrare „Casa ta are acum memorie".
- [x] Scor „Sănătatea casei" + pasul următor permanent vizibil (desktop right panel).
- [x] Solicită ofertă → oferte → escrow → confirmare → recenzie (E2E 100%, iteration_138).
- [x] Pașaport public + QR + share (slug testat).
- [x] Tur „?" on-demand, cookie compact, feedback din Setări.

## 6. DESKTOP QA CHECKLIST (1920)
- [x] Client Home: workspace 8+4, hero+alerts main, casa+Copilot dreapta sticky, CTA unic.
- [x] Specialist: Mission Control split (listă procesabilă + KPI rail sticky), dock desktop, cockpit doar ADVANCED+.
- [x] Property Hub: record page (sub-nav 5 secțiuni + main + scor sticky), lățime completă.
- [x] Lucrările mele: grid 2 coloane.
- [x] Navigație: una per device (top tabs client / dock specialist), zero bottom-nav mobil pe desktop.
- [x] Ambele teme (dark/light) lizibile — verificat programatic (iteration_142).

## 7. MOBILE QA CHECKLIST (390)
- [x] Stivă task-first, KPI-urile primele la specialist, hero primul la client.
- [x] Bottom nav 5 zone + FAB central client; 4 zone specialist; ținte ≥44px.
- [x] Zero overlap-uri (cookie compact, feedback mutat, tur on-demand).
- [x] Property Hub stivă completă neschimbată; sub-nav/panel desktop ascunse.
- [x] Grid-urile desktop colapsează corect (verificat programatic gridTemplateColumns).

## 8. PERFORMANCE CHECKLIST
- [x] Payload pașaport public ~110ms (Measured, iteration_135).
- [x] Imagini lazy + gradient overlays CSS (fără imagini duplicate).
- [x] Rate limiting 120 req/min pe rutele publice (TD-07 închis).
- [x] Build production compilează fără erori (doar warnings ESLint minore).
- [ ] Post-beta: code-splitting pe rutele admin (bundle mare, nu afectează clientul).

## 9. ACCESSIBILITY CHECKLIST
- [x] Focus-visible global (outline lime pe dark / verde închis pe light) — WCAG 2.4.7.
- [x] Aria-labels pe toate butoanele icon-only din headere (bell, help, temă, logout).
- [x] Contrast reparat pe cardurile „Pasul următor" în ambele teme.
- [x] Progressbar-uri cu role/aria-valuenow (PVI, completeness).
- [ ] Post-beta: focus-trap în sheets/drawere, skip-links, audit screen-reader complet.

## 10. TOP 20 BETA RISKS (condensat pe categorii, cu mitigare)
1. **Emailuri nelivrate** (DNS neverificat) → gate-ul de siguranță ține coada; acțiune Fondator. (R critic #1)
2. **Date demo în prod** → purge + SEED gating implementate; execuția e pe Fondator. (#2)
3. **Stripe test-mode la primul client real** → War Room arată statusul; claim înainte de invitații. (#3)
4. Primii utilizatori nu văd valoare în <5 min → onboarding J0 cu UN pas; de măsurat TTFV în Beta Cockpit. (#4)
5. Specialiști fără oportunități reale în zonă → seed de cereri reale de la proprietarii invitați întâi. (#5)
6. Obiceiuri formate pe UI-ul vechi la beta-userii existenți → flag „dashboard clasic" există. (#6)
7. Frica de date personale (adresă) → pașaport cu adresa ASCUNSĂ implicit + privacy toggles. (#7)
8. Recenzii/rating-uri goale par suspecte → „Nou pe platformă" (P3a M5). (#8)
9. Mobile Safari edge-cases (nu s-a testat pe device fizic iOS) → test manual Fondator la primii useri. (#9)
10. Încărcare documente mari pe 4G → limită 25MB + progres vizibil; de monitorizat. (#10)
11. Un singur admin operațional (bus factor) → conturi admin scoped există. (#11)
12. Suport: cereri beta fără SLA → Beta Cockpit agregă cererile; definește SLA 24h. (#12)
13. e-Factura lipsă la prima factură B2B → TD-04, plan post-primul-venit. (#13)
14. Confuzie 4 sisteme twin istorice (G2) → ascunse din UI-ul principal; unificare = post-beta. (#14)
15. AI Copilot răspunde generic → prompturi pe date reale; de monitorizat VoC. (#15)
16. Scoruri multiple derutante rămase în drill-down-uri → ierarhia P3d (UN scor primar). (#16)
17. Performanță listă >100 lucrări → paginare există pe API; UI virtualizare post-beta. (#17)
18. GDPR: export/ștergere cont la cerere → fluxuri există în Trust Center; de comunicat. (#18)
19. Browser vechi (Safari 14-) fără focus-visible → degradare grațioasă, nu blocant. (#19)
20. Feedback beta zgomotos/contradictoriu → VoC structurat (6 întrebări) + decizie prin PPOS Council. (#20)

## 11. RECOMMENDED BETA LAUNCH PLAN
1. **Săpt. 0**: Fondator închide cele 3 blocante (Stripe/DNS/purge+redeploy). Smoke pe prod.
2. **Săpt. 1**: 5 proprietari „prieteni" + 3 specialiști (val 1) — observație directă, fix-uri rapide zilnice (FAST EXECUTION rămâne activ).
3. **Săpt. 2-3**: extindere la 20 proprietari + 10 specialiști (val 2) — urmărește gate-urile EO-026 (80% activare pas 1, 70% document, 50% cerere, 50% specialist activ) în Beta Cockpit.
4. **Săpt. 4**: AI Product Review 2.0 pe date REALE + decizia CX-4 (calendar mentenanță) vs pivot.
- Canale: invitații personale + /scorul-casei ca lead magnet + share pașaport (viral loop există).
- Regula: niciun feature nou în valul 1 — doar fix-uri de claritate/încredere.

## 12. RECOMMENDED POST-BETA ROADMAP
- **P0 (imediat după feedback)**: fix-urile din VoC · audit complet la 5 faze (gate 95) · e-Factura (TD-04, legal).
- **P1**: Trust Profile Engine / Market Standard Levels 0-5 (suspendat prin ordin — reluare cu GO) · G2 unificarea twin + repoziționare House Health · CX-4 calendar mentenanță → marketplace.
- **P2**: AI Timeline & Property Intelligence Story · D2 AI Designer Matching + Team Builder (gate: ≥5 proiecte reale) · owner lifecycle tracker Imobile Verificate + pricing automatizat.
- **P3**: transfer proprietate cu istoric (S5) · Owner AI (S6) · Admin Desktop polish (Stripe-density, audit separat) · Local SEO orașe (G2 growth).

---
*Top 50 UX improvements & Top 20 revenue opportunities & Top 20 tech debt: registrele existente rămân sursa de adevăr — `/app/docs/EXPERIENCE_ARCHITECTURE_EO008.md` (47 UX improvements reale), `/app/docs/PRODUCT_REVIEW_1_0.md` §Top 10 + oportunități venit, `/app/docs/TECHNICAL_DEBT_LEDGER.md`. Acest pachet NU le duplică (Truth Engine D161: fără liste umflate artificial).*
