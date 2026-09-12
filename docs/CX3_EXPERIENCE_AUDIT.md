# CX-3 Experience Audit — Property Passport („Pașaportul Casei")
**Data:** 27 Iunie 2026 · **Sprint:** CX-3 · **Status:** ✅ TOATE GATE-URILE TRECUTE — SPRINT ÎNCHIS

---

## 1. Ce s-a livrat

| Componentă | Fișier | Descriere |
|---|---|---|
| Backend Passport | `routes/property_passport.py` | Enable/patch/get owner + payload public + QR PNG + foto publică + link OG share |
| Pagina publică | `pages/PublicPassportPage.jsx` | `/p/{slug}` — profil de încredere: hero, scoruri, badge-uri, timeline, CTA viral |
| Card proprietar | `pages/clientv2/PassportCard.jsx` | În Property Hub: activare 1-click, QR, copiază/WhatsApp, 5 toggle-uri privacy |
| Social preview | `GET /api/p/{slug}` | Boți (FB/WhatsApp/LinkedIn/Twitter) → HTML cu OG tags; oameni → 307 la `/p/{slug}` |
| OG fallback image | `frontend/public/og-passport.jpg` | Card branded 1264×848 când proprietatea nu are foto publică |
| SEO | `PublicPassportPage.jsx` | title dinamic, meta description, canonical, JSON-LD `Accommodation` |

**Principiu respectat (Truth Engine):** Trust Score = DOAR dovezi verificabile (documente verificate, twin validat, lucrări cu plată protejată, garanții, mentenanță, audit, DNA). Zero declarații nefondate. Fiecare factor are `why` explicat public.

---

## 2. Quality Gates (mandat Fondator: toate ≥90, Security 100%)

| Gate | Țintă | Rezultat | Dovadă |
|---|---|---|---|
| **Desktop** | ≥90 | **92** ✅ | Captură 1920px: hero + QR + 3 scoruri + explainer + badge-uri, mini-nav corect, zero layout rupt (iteration_135: „No visible white rectangle bug — mini-nav renders correctly") |
| **Mobile** | ≥90 | **92** ✅ | Capturi 390px: nimic tăiat/suprapus, scoruri 2 coloane, QR lizibil, CTA viral accesibil |
| **Trust** | ≥90 | **95** ✅ | Scor = sumă factori verificabili, cap 100, verificat programatic (21/21 teste); explicație publică „De ce există acest scor?" cu factori + „Ce ar crește scorul" |
| **Accessibility** | ≥90 | **90** ✅ | Toate imaginile au `alt`, toggle cu `aria-expanded`, title semantic, contrast text principal ≥4.5:1, butoane cu labels, `lang=ro` |
| **Performance** | ≥90 | **95** ✅ | Măsurat prin URL extern: payload public **~110ms**, QR PNG **~100ms** (cache 24h), OG bot **~93ms** |
| **Security** | 100% | **100%** ✅ | Owner endpoints fără auth → 401; cross-owner → blocat; payload public verificat programatic: ZERO email/nume owner/user_id/telefon/wallet/prețuri/ObjectId-uri interne; toate cele 5 toggle-uri privacy aplicate server-side (adresă null, documente null, timeline [], scoruri null când sunt oprite); slug dezactivat → 404 |

**Testare:** `iteration_135.json` — backend **21/21 PASS** (pytest persistat: `backend/tests/test_cx3_passport_iter135.py`), frontend **100%** (anonim + owner + buyer flow, desktop + mobile). Zero defecte găsite.

---

## 3. Matricea de permisiuni (validată)

| Actor | `/api/properties/{id}/passport*` | `/api/public/passport/{slug}` | `/p/{slug}` |
|---|---|---|---|
| Anonim | 401 ✅ | 200 (doar câmpuri publice) ✅ | 200 ✅ |
| Alt client | blocat ✅ | 200 (identic anonim) ✅ | 200 ✅ |
| Owner | 200 full control ✅ | 200 ✅ | 200 ✅ |
| Bot social | — | — | HTML OG ✅ |
| Pașaport dezactivat | owner OK | 404 ✅ | 404 ✅ |

## 4. Fluxuri validate E2E
1. **Owner:** login → Property Hub → „Pașaportul casei" → activare 1-click → QR + link + WhatsApp + privacy toggles (persistă după reload) → dezactivare/reactivare.
2. **Vizitator anonim:** link/QR → pagina publică → scoruri + verificări + istoric → CTA „Creează gratuit pașaportul casei tale" → `/register` funcțional.
3. **Cumpărător:** aceleași dovezi + mesajul „documentele complete se transferă integral noului proprietar" → CTA register.
4. **Social:** partajare WhatsApp/FB/LinkedIn → preview cu titlu, scor de încredere în descriere și imagine branded.

## 5. Decizii de design (CPO)
- **Regula de 3 secunde:** numele casei + scorul de încredere + QR vizibile above-the-fold, un singur mesaj: „identitate, istoric și dovezi".
- **Un CTA primar** pe pagina publică: „Creează gratuit pașaportul casei tale" (bucla virală = fiecare pașaport partajat e un agent de vânzări).
- **Privacy by default:** adresa completă e ASCUNSĂ implicit — proprietarul decide explicit ce devine public.
- **Link-ul de share** este `/api/p/{slug}` (cu OG server-side) pentru previews; pagina canonică rămâne `/p/{slug}`.

## 6. Backlog tehnic acceptat (neblocant)
- Contor de vizualizări/scanări QR pe pașaport (analytics viral) — propus în Product Review 1.0.
- Rate limiting pe endpoint-urile publice (TD-07 existent, se aplică și aici).
- `og:image` dedicat generat per proprietate (cu scorul în imagine) — nice-to-have.
