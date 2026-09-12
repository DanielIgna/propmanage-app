# PropManage · Screenshot Tour (Feb 24 2026)

Capturi din **preview environment** demonstrând ce am construit/testat în această sesiune.

## 📸 Capturi

### ▶ TEMA NOUĂ "WARM LINEN 2026" (Feb 24 2026)
- `10_light_theme_house_health.jpeg` — House Health în tema light cream cu accente emerald
- `11_light_theme_trends.jpeg` — Trends dashboard în Warm Linen (alerta UX regression vizibilă pe cream cald)
- `12_theme_switcher_open.jpeg` — Dropdown switcher temă deschis în header dashboard (Dark / Warm Linen 2026 cu badge ✓ activ)

### 1️⃣ Tester Manual · Trends 30d (NOU) — `01_manual_tester_trends.png`
Dashboard-ul Compounding QA:
- Selector fereastră: **7d / 14d / 30d / 90d**
- 4 KPI: Run-uri, Cazuri executate, Avg pass-rate, Total failures
- **Alertă auto-detectată**: "Regression UX General — pass-rate scăzut de la 50% la 25%"
- 8 carduri suite sortate ascendent după latest pass-rate (cele degradate sus)
- Sparkline SVG cu puncte colorate per pass-rate
- Timeline zilnic cu bare stacked pass/fail/skip

### 2️⃣ Tester Manual · Runner (gol) — `02_manual_tester_runner.png`
Vizualizarea principală:
- Sidebar: 8 suite-uri cu progres `X/Y`
- AI Suggester (violet) pentru cazuri custom
- 6 cazuri de test pentru "Autentificare & Roluri" cu butoane PASS/FAIL/SKIP
- Controale Salvează run / Export JSON / Reset draft
- Listă run-uri anterioare jos

### 3️⃣ Tester Manual · Runner cu rezultate — `03_manual_tester_with_results.png`
Aceeași pagină după ce am marcat:
- 3 cazuri PASS (verde)
- 1 caz FAIL (roșu) — apare automat câmpul de note pentru bug
- Header arată: 3 pass · 1 fail · 0 skip · 4 total
- Sidebar arată progres `4/6` pe suite-ul Autentificare

### 4️⃣ House Health · Tab Scor — `04_house_health_score.png`
- Sidebar cu cele 9 tab-uri (Scor, Aer, Termic, Umiditate, Electric, Radon, Documentație, Istoric, Recomandări)
- Scor 87/100 GOOD (badge sky)
- Detalii formulă + ultima evaluare + următoarea recomandată
- Tema dark stone

### 5️⃣ House Health · Tab Documentație — `05_house_health_docs.png`
- Formular dual: **Fișier local** vs **Link extern**
- Selectoare categorie + dată
- 4 documente existente afișate: 2 locale (Descarcă) + 2 link-uri Google Drive (Deschide)
- Buton trash pe fiecare

### 6️⃣ House Health · Tab Recomandări — `06_house_health_recommendations.png`
- Legendă cu cele 3 priorități: 🚨 Urgent / ⚠ Recomandat / 👁 Monitorizare
- 7 recomandări URGENT ELECTRIC publicate în marketplace (badge cyan "✓ Publicat în marketplace")
- 1 recomandare RECOMANDAT cu detalii cost + buton publish

### 7️⃣ House Health · Upgrade (Stripe) — `07_house_health_upgrade.png`
- 3 planuri: **Basic 9€** / **Pro 29€** (badge ✨ "Recomandat", centrat, gradient emerald-cyan) / **Premium 79€**
- Trial 7-14 zile, features bullet-pointed
- Comision marketplace per plan (10% / 10% / 5%)
- Footer "🔒 Plată securizată via Stripe"

### 8️⃣ Admin House Health · Planuri — `08_admin_house_health_plans.png`
- Tab "Planuri": 11 planuri (3 default + 8 create în teste)
- Fiecare cu: slug badge, preț, trial, lead commission %
- Butoane editare (creion) + arhivare (trash)
- Plan arhivat afișat cu opacitate redusă + badge "arhivat"

### 9️⃣ Admin House Health · Formula scor — `09_admin_house_health_scoring.png`
- 7 sliders interactive pentru ponderi (Aer / Termic / Umiditate / Electric / Documentație / Mentenanță / Radon)
- Total live: **100.0 / 100** ✓ verde (validare server-side)
- Praguri clasificare: Excellent (92) · Good (78) · Fair (55)
- Buton salvare cu animație
- Audit trail: "Ultima modificare 24.06.2026 17:08 de admin@propmanage.io"

---

## 🧪 Test results sumar

- **Backend pytest**: 55/55 pass (`test_house_health.py` + `test_house_health_f4.py` + `test_house_health_f43_billing.py` + `test_auth_dual_role_healing.py`)
- **Frontend manual**: toate fluxurile House Health + Manual Tester verificate prin smoke test live
- **Bug critic reparat**: dual_role_enabled desincronizat (client demo afișa specialist) — self-healing adăugat în `/auth/me` + 4 teste regression

## 📂 Fișiere create în această sesiune

### Backend
- `/app/backend/routes/house_health.py` (F1+F2+F3)
- `/app/backend/routes/house_health_plans.py` (F4.1)
- `/app/backend/routes/house_health_recommendations.py` (F4.2+F4.4)
- `/app/backend/routes/house_health_billing.py` (F4.3 Stripe)
- `/app/backend/routes/manual_tester.py` (Tester + Trends)
- `/app/backend/routes/auth.py` (self-healing dual-role)
- `/app/backend/tests/test_house_health*.py` (47 teste)
- `/app/backend/tests/test_auth_dual_role_healing.py` (4 teste)

### Frontend
- `/app/frontend/src/pages/HouseHealthPage.jsx` (orchestrator slim)
- `/app/frontend/src/pages/house_health/` (sub-componente)
  - `constants.js`, `ScoreSection.jsx`, `DocumentsSection.jsx`,
    `HistorySection.jsx`, `EvaluationSection.jsx`, `RecommendationsSection.jsx`
- `/app/frontend/src/pages/HouseHealthUpgradePage.jsx` (+ HouseHealthUpgradeSuccess)
- `/app/frontend/src/pages/admin/AdminHouseHealthPage.jsx` (Plans + Scoring)
- `/app/frontend/src/pages/admin/ManualTesterPage.jsx` (Runner + Trends)
