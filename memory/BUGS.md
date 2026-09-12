# PropManage — QA Bug Tracker

Format: `BUG #NNN – Titlu` · Status: `Open` | `In Progress` | `Fixed (verificare pending)` | `Closed`

---

## BUG #001 – Text invizibil în input-uri Client V2 (contrast alb pe alb)
- **Status:** Closed
- **Cauză:** Overlay global dark theme peste input-urile V2.
- **Fix:** Override CSS global în `/app/frontend/src/index.css` (Faza 5 UX Refinement).
- **Fișiere:** `frontend/src/index.css`, `frontend/src/pages/clientv2/*`
- **Verificat de user:** ✅

## BUG #002 – Cursor săre la început în input numeric "Buget estimat (RON)"
- **Status:** Closed ✅ (verificat de agent cu playwright: tastare `35000` → `35.000`, append `9` → `350.009`, caret stabil)
- **Simptom:** Utilizatorul scria `250` dar primea `0250`, cursorul repoziționat forțat la începutul câmpului.
- **Cauză root:**
  1. `budget_estimate` era stocat ca **număr** în state, iar `onChange` făcea `parseFloat(e.target.value) || 0` pe fiecare tastă.
  2. `|| 0` forța valoarea la `0` când user ștergea câmpul → afișa "0" → orice tastare producea "02", "025", "0250".
  3. `parseFloat` normaliza valoarea la fiecare tastă (ex: "0250" → 250) → React re-randează cu string nou → browser resetează caret position.
- **Fix aplicat:** State controlat ca **string** în timpul editării, `parseFloat` doar la submit (același pattern ca `WalletSheet` care nu are bug). Adăugat `inputMode="numeric"` pentru keyboard mobil optim.
- **Fișiere modificate:**
  - `frontend/src/pages/clientv2/RequestWizard.jsx` (linia 17: `budget_estimate: "200"`; linii 24, 89-91)
- **Verificat de user:** ⏳
- **Alte input-uri numerice audit-uite:**
  - `PropertyHubV2.jsx` (Wallet topup): ✅ deja folosea string state — no fix needed.
  - Nu există alte `type="number"` în Client V2.

## ENH #001 – Formatare live cu separator de mii pe input-uri de sumă (Revolut-style)
- **Status:** Closed ✅ (verificat de agent cu playwright — formatare live corectă, caret păstrat)
- **Cerință:** Ex: user tastează `35000` → afișează `35.000` live, cu caret păstrat la locul corect.
- **Implementare:**
  - Nouă componentă `AmountInput` în `frontend/src/pages/clientv2/ui.jsx`.
  - Stochează raw digits (string) în state parent; afișează formatat cu `Intl.NumberFormat("ro-RO")`.
  - Restaurează caret position după fiecare re-format prin `useLayoutEffect` (numără cifrele înaintea caret-ului).
  - Optional prop `suffix` pentru ex: "RON" inline.
- **Aplicat în:**
  - `RequestWizard.jsx` — câmp "Buget estimat (RON)".
  - `PropertyHubV2.jsx` (WalletSheet) — câmp "Altă sumă (RON)".
- **Payload backend:** Neschimbat. `parseFloat("35000")` → `35000` (număr) la submit.

---

## Backlog Open (pre-existing)
- **BUG #003 – Resend Custom Domain DNS** — Status: Blocked (user action pe registrar DKIM/SPF)
- **BUG #004 – Restore icon lipsă pentru marketplace partners terminate** — Status: Closed ✅ (buton RotateCcw `restore-{id}` în MarketplacePartnersPage → PATCH status=active; testat E2E iter86)

## BUG #005 – `.skp` (SketchUp) NU e vizualizabil 3D · Trimble Connect URL validation
- **Status:** Open (LIMITARE DE WORKFLOW — NU „fully supported"). Partial-mitigat.
- **Simptom observat (Operator upload):** fișier `.skp` încărcat → conversie eșuează cu „This conversion type is not supported". Calea Trimble Connect respinge un link Google Drive ca invalid (cere URL Trimble Connect / SketchUp).
- **Stare reală (mitigare aplicată în etapă anterioară):** upload-ul `.skp` **funcționează** — fișierul e stocat intact ca arhivă descărcabilă (`conversion_status="unsupported"`), fără crash / fără eroare roșie. UI: „SketchUp (doar descărcabil; exportă `.dae` pentru viewer)".
- **Cauză root:** nu există pipeline server-side (Blender/CloudConvert) `.skp` → `.glb` în infra curentă. Un link Google Drive **NU este** link Trimble Connect și e respins CORECT (nu se confundă storage-ul GDrive cu viewer-ul Trimble/SketchUp).
- **REGULĂ:** NU marca `.skp` drept „fully supported" până când un `.skp` real e încărcat ȘI vizualizat efectiv în Digital Twin.
- **Direcție de rezolvare (viitor, ne-programat):** conversie reală `.skp`→format vizualizabil · SAU integrare validă Trimble Connect (cu validare de tip URL) · SAU altă soluție robustă.
- **Ref canonic:** `audits/PROPERTY_TWIN_CANONICAL_v1.0.md` §9.6.

## BUG #006 – „Acordă acces DT" nu găsea clienți existenți (Operator → Digital Twin Pro)
- **Status:** Fixed ✅ (PREVIEW — necesită redeploy Fondator pentru PRODUCTION). Testat E2E iter211 (A–G = 100%).
- **Raportat pe:** PRODUCTION (`propmanage.ro`). Reprodus și reparat în preview (același cod).
- **Simptom:** clientul „Andrei Popescu" (client@propmanage.io) apare în lista „Clienți cu acces 3D", dar căutarea din modalul „Acordă acces DT" răspundea „Niciun client găsit" pentru orice interogare.
- **Cauză root:** modalul apela `GET /api/admin/search` (require_role **admin**). Operatorul primea **403**, iar `search()` din FE înghițea eroarea în `catch` → `results=[]` → „Niciun client găsit". Deci operatorul NU putea găsi NICIUN client (nu doar Andrei).
- **Fix backend:** endpoint nou operator-scoped `GET /api/operator/digital-twin/search-clients` (`require_role("operator","admin")`), filtrează `role=client`, `$regex` case-insensitive (re.escape) pe `name`+`email`, întoarce `digital_twin_pro` pentru fiecare. (`routes/digital_twin.py`)
- **Fix frontend:** `GrantAccessModal.search()` folosește noul endpoint și citește `r.data.items`; badge „Acces deja acordat" (`already-granted-<id>`) pentru clienții care au deja DT Pro (fără a doua relație — `alreadyGranted()` doar închide+refresh); stare de eroare distinctă de „no results"; loader `grant-search-loading`. (`pages/OperatorDigitalTwin.jsx`)
- **Securitate:** client/specialist → 403; se întorc DOAR `role=client` (specialiști/admini/operatori NU apar); ownership/authorization nemodificate; niciun endpoint public.
- **Rezultat caz concret:** „Andrei Popescu / client@propmanage.io" e găsit după email exact, nume, case-insensitive și parțial, cu badge „Acces deja acordat".
- **Fișiere:** `backend/routes/digital_twin.py` (+`search-clients`, `import re`), `frontend/src/pages/OperatorDigitalTwin.jsx`.


