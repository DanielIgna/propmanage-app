# Rădăcini — costuri estimate pentru pilot (EUR/lună)

Versiune 1.0 · 2026-10-14. **Toate cifrele sunt estimări de verificat**, în intervale, nu prețuri exacte. Tarifele furnizorilor se schimbă: se verifică pe paginile lor de preț înainte de decizie. Curs orientativ: 1 USD ≈ 0,9 EUR (de verificat). TVA exclus unde nu e specificat.

## 1. Ipoteze (explicit)

| Parametru | 100 membri | 300 membri | 500 membri |
|---|---|---|---|
| Membri activi lunar (din total) | 60% | 50% | 45% |
| Cereri API / membru activ / zi | 15 | 15 | 15 |
| **Cereri API / lună** | ~27 000 | ~67 000 | ~101 000 |
| Dimensiune medie răspuns JSON | 15 KB | 15 KB | 15 KB |
| Fotografii încărcate / membru (total pilot) | 5 | 5 | 5 |
| Mărime medie fotografie stocată (JPEG ≤ 1600 px, fără EXIF; limita codului: 5 MB încărcare, 6 poze/obiect) | 350 KB | 350 KB | 350 KB |
| Fotografii vizualizate / membru activ / lună (fără miniaturi, la dimensiune întreagă) | 60 | 60 | 60 |
| E-mailuri / membru / lună (notificări, invitații, acorduri) | 20 | 20 | 20 |
| **E-mailuri / lună** | 2 000 | 6 000 | 10 000 |
| Vizualizări hartă / membru activ / lună (≈ 25 plăci/vizualizare) | 20 | 20 | 20 |
| **Plăci de hartă / lună** | ~30 000 | ~75 000 | ~110 000 |
| Geocodări (terenuri noi + căutări) / lună | 100 | 300 | 500 |

Derivate (orientativ):
- **Stocare foto**: 100 × 5 × 0,35 MB ≈ 0,2 GB · 300 ≈ 0,5 GB · 500 ≈ 0,9 GB. Baza de date: sub 0,5 GB în pilot.
- **Egress API**: 27k × 15 KB ≈ 0,4 GB · 67k ≈ 1 GB · 101k ≈ 1,5 GB.
- **Egress foto (fără miniaturi)**: 60 × 0,35 MB × membri activi → ~1,3 GB · ~3,2 GB · ~4,7 GB.
- **Egress total estimat**: ~2 GB · ~4 GB · ~6 GB pe lună. Trafic de crawlere, retry-uri și interogări `pgmongo` care citesc mai multe documente decât returnează pot multiplica de 3–10× (vezi riscul de mai jos).

## 2. Costuri pe servicii

### 2.1 Supabase (bază de date, auth, storage)
- Plan: se verifică planul real al proiectului (planul **Free** are cote mici de egress/stocare; **Pro** ~25 USD/lună include, orientativ, 250 GB egress, 100 GB stocare și 8 GB bază de date — de verificat).
- **Risc cunoscut în acest proiect: egress-ul Supabase este deja peste cotă** (vezi `e45e4cb` și `audit-agro-faza0.md` §8: stratul `pgmongo` încarcă în memorie documentele candidate; fără blob-uri în JSONB). Pe planul Free, depășirea poate duce la restricționarea proiectului; pe Pro, depășirea se taxează (~0,09 USD/GB peste cotă — de verificat).
- Pilotul Rădăcini adaugă puțin trafic față de cota Pro (2–6 GB/lună estimat din ipoteze), dar nu rezolvă depășirea existentă a proiectului comun.
- Estimare: **Pro obligatoriu pentru pilot** (recomandat) → ~23 EUR/lună; depășiri: 0–10 EUR/lună în scenarii normale, mai mult dacă interogările rămân neoptimizate.

### 2.2 Railway (backend FastAPI)
- Hobby ~5 USD/lună incluzând credit de utilizare, apoi consum (CPU/RAM/rețea); Pro ~20 USD/lună + consum (de verificat).
- Pilot mic (1 instanță, trafic de mai sus): consum de ~5–15 USD/lună.
- Notă: rate limit-ul e în memorie (nu protejează la mai multe instanțe) — de luat în calcul dacă se scalează.

### 2.3 Cloudflare Workers (frontend Next.js, OpenNext)
- Plan Workers Paid ~5 USD/lună (include 10 M cereri/lună — de verificat). Pilotul e mult sub limită.
- Fără costuri suplimentare pentru DNS/CDN pe plan gratuit.

### 2.4 Hărți
- Actual: plăci **OpenStreetMap** gratuite, cu limite din politica de utilizare (fără trafic intens/comercial mare, atribuire obligatorie, fără pre-încărcare în masă; de verificat politica actuală). Aproape de 100 de membri e OK; peste ~100 000 plăci/lună sau când produsul devine vizibil public, se recomandă furnizor dedicat.
- Furnizori de plăci (de verificat): MapTiler (plan gratuit ~100 000 cereri/lună; planuri plătite de la ~25 USD/lună), Stadia Maps, Mapbox, Thunderforest. Estimare pentru 300–500 membri: **0–25 EUR/lună**.
- **Geocodare Google** (opțională; PropManage are deja integrare Google): ~5 USD/1000 cereri după nivelul gratuit lunar (de verificat). La 100–500 geocodări/lună: **0–3 EUR/lună**. Alternativă: Nominatim cu limită de 1 cerere/secundă și fără uz intens.

### 2.5 E-mail
- Furnizor folosit de `backend/email_service.py`: **Resend** (preferat) → SendGrid → consolă (în dev). Expeditor configurat prin `SENDER_EMAIL`; fără domeniu verificat se folosește `onboarding@resend.dev` (doar pentru test).
- Resend: plan gratuit ~3 000 e-mailuri/lună și ~100/zi (de verificat); Pro ~20 USD/lună pentru ~50 000 (de verificat).
- 100 membri (~2 000/lună): **gratuit** posibil, dar limita zilnică poate încurca trimiterile în vârf. 300–500 membri (6 000–10 000): **~18–20 EUR/lună**.

### 2.6 Domeniu
- `.ro` ~10–15 EUR/an; `.com` ~10–15 EUR/an (de verificat). ≈ **1 EUR/lună**. Opțional: casetă de e-mail (Google Workspace / alt furnizor) ~6 EUR/utilizator/lună.

### 2.7 Servicii juridice (unică, nu lunară)
Estimare de piață, **de validat cu oferte reale** (onorarii variază mult):
- Revizuire termeni, politică de confidențialitate, șablon de acord, texte UI: **1 000–3 000 EUR**.
- Consultanță punctuală (arendă și înregistrare, DSV/atestat, fiscalitate barter, statut platformă/DSA): **500–1 500 EUR**.
- GDPR (DPIA, ROPA, procedură pentru minori, DPA-uri): **500–2 000 EUR**.
- Total unic: **2 000–6 500 EUR**; tarif orar orientativ 80–200 EUR/oră (de verificat). Deblocarea `sale`/`joint_project` (ASF) este în afara acestui buget și poate depăși semnificativ.
- Opțional lunar: abonament consultanță 100–300 EUR/lună sau asigurare de răspundere civilă (de verificat).

### 2.8 SMS (opțional)
- Pilotul nu trimite SMS. Dacă s-ar adăuga (ex. confirmări de ridicare): ~0,05–0,10 EUR/SMS în România (de verificat, furnizor ex. Twilio/alte).
- 1 SMS/membru/lună → 100: 5–10 EUR · 300: 15–30 EUR · 500: 25–50 EUR.

## 3. Total lunar estimat (fără partea unică juridică)

| Serviciu | 100 membri | 300 membri | 500 membri |
|---|---|---|---|
| Supabase (Pro + depășiri) | 23–30 | 23–35 | 25–45 |
| Railway | 5–12 | 8–15 | 10–20 |
| Cloudflare Workers | 5 | 5 | 5–10 |
| Hărți (plăci + geocodare) | 0 | 0–15 | 10–30 |
| E-mail (Resend) | 0 | 18–20 | 18–20 |
| Domeniu | 1 | 1 | 1 |
| **Subtotal fără opțional** | **~35–50** | **~55–90** | **~70–130** |
| SMS opțional | 5–10 | 15–30 | 25–50 |
| **Total cu SMS** | ~40–60 | ~70–120 | ~95–180 |

În plus, **una singură**: servicii juridice 2 000–6 500 EUR (secțiunea 2.7). Pentru prima lună, juridicul domină costul total.

## 4. Riscuri de cost
1. **Egress Supabase** — deja peste cotă în proiect; costul crește dacă fotografiile se servesc la dimensiune întreagă, dacă listele nu sunt paginate sau dacă `pgmongo` citește colecții mari. Poate deveni singura linie de cost care sare.
2. **Plăci de hartă** — politica OSM; o postare virală sau crawlere pot depăși limita.
3. **E-mail** — limita zilnică Resend; notificări în rafală (anunțuri de comunitate, vot).
4. **Stocare** — fotografiile cresc liniar; fără ștergere/arhivare, 1 GB la 500 membri nu e problemă, dar pozele nereduse ar fi.
5. **Cost de personal/moderare** — nu e inclus (personalul Rădăcini: verificare terenuri, dispute).

## 5. Cum reducem costurile
**Egress / stocare**
- **Miniaturi** (ex. 400 px, ~40 KB) pentru liste și hărți; imaginea mare doar la deschidere. Reduce egress-ul foto cu ~80–90%.
- **Cache**: antete `Cache-Control` lungi pentru fotografii și răspunsuri publice (`/parcels`, `/meta`), cache Cloudflare în fața storage-ului; `ETag`.
- Paginare și proiecții pe toate listele; evitarea citirii de colecții întregi (cache în memorie 5 min pentru KPI există deja, D34).
- Fără blob-uri în JSONB; imagini doar în Storage (deja: JPEG reprocesat, max 1600 px, max 6/obiect).
- Servirea pozelor prin Cloudflare (R2 sau cache) în loc de egress Supabase direct (de evaluat).
- Monitorizarea egress-ului lunar, alertă la 70% din cotă.

**Hărți**: cache de plăci în Cloudflare, nivel de zoom limitat, încărcare la cerere (nu la încărcarea paginii); trecere la furnizor cu plan gratuit mai generos dacă traficul crește.

**E-mail**: rezumate zilnice în loc de e-mail per eveniment; preferințe de notificare; in-app ca implicit.

**Backend**: o singură instanță în pilot, fără joburi periodice (D14, D34).

## 6. Pași înainte de pilot
1. Confirmare plan Supabase actual și rezolvarea depășirii existente de egress.
2. Oferte de la 2–3 juriști (secțiunea 2.7).
3. Alegerea furnizorului de hărți dacă ținta e peste 100 de membri.
4. Domeniu verificat în Resend (expeditor propriu, nu `resend.dev`).
5. Revizuire la 30 de zile cu cifrele reale din facturi și metrici.
