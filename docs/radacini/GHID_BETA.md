# Rădăcini — ghid pentru beta-ul închis

Versiune 0.1 · 2026-10-28. Pentru fondator și pentru testerii invitați (5–15 persoane).

## 1. Ce testează invitații
Fiecare tester parcurge cel puțin un traseu complet, cu date inventate (fără terenuri sau persoane reale în beta):
1. **Cont și profil:** autentificare, acceptarea termenilor, onboarding, profil Rădăcini.
2. **Teren:** publicare teren (locație aproximativă pe hartă), fotografii, editare, arhivare.
3. **Cerere → acord → proiect:** un alt tester cere terenul, negociază prin mesaje, se semnează acordul, apare proiectul (culturi, activități, contribuții).
4. **Recoltă și piață:** recoltă înregistrată, anunț în piață, rezervare, finalizare și evaluare.
5. **Comunitate și gospodărie:** intrare într-o comunitate, postare, vot; gospodărie cu un membru adult.
6. **Composesorate (demo „Valea Verde”):** citire registru, documente, ședințe. Datele sunt fictive.
7. **Pe telefon:** cel puțin un traseu de pe mobil (inclusiv instalarea ca aplicație, PWA).

### Cum raportează problemele
- **Conținut nepotrivit:** butonul „Raportează” de pe anunț, teren sau comunitate. Decizia apare în **Raportări**.
- **Erori și sugestii:** un email către fondator cu: ce pagină, ce ai făcut, ce te așteptai să se întâmple, ce s-a întâmplat, captură de ecran, telefon sau calculator și browserul. Fără parole sau date personale în capturi.
- Erorile neprevăzute ale serverului se înregistrează automat (doar ruta și tipul erorii, 14 zile) și se văd în **Administrare → Sistem**.

## 2. Emailul de invitație (text propus)

> **Subiect:** Invitație: testează Rădăcini (beta închis)
>
> Bună,
>
> Te invit să testezi **Rădăcini**, platforma prin care proprietarii de teren și cei care vor să cultive lucrează împreună: terenuri, acorduri, proiecte, recoltă și piață locală.
>
> **Ce îți cer:** 2–3 sesiuni de câte 20–30 de minute în următoarele două săptămâni, cu date inventate. Lista de pași e în ghidul atașat.
>
> **Cum intri:** te autentifici cu adresa aceasta de email la [adresa aplicației]/radacini. Accesul e permis doar adreselor invitate.
>
> **Ce se întâmplă cu datele:** sunt date de test; la final le ștergem. Politica de confidențialitate și termenii sunt în aplicație, la „Despre”.
>
> Pentru orice problemă, răspunde direct la acest email (cu o captură de ecran, dacă poți).
>
> Mulțumesc!
> [Numele fondatorului]

## 3. Pașii fondatorului (Railway) — doar după aprobarea ta
Variabilele se setează pe serviciul backend (Railway → Variables). Fiecare salvare repornește serviciul.

| Variabilă | Valoare | Rol |
|---|---|---|
| `RADACINI_ENABLED` | `true` | pornește API-ul Rădăcini (cât e `false`, `/api/radacini/*` răspunde 404) |
| `RADACINI_ALLOWED_EMAILS` | `a@exemplu.ro,b@exemplu.ro` | lista albă a beta-ului; restul primesc 403. Super-adminul are mereu acces |
| `RADACINI_OPERATOR_NAME`, `_LEGAL_FORM`, `_CUI`, `_REG_NO`, `_ADDRESS`, `_EMAIL`, `_PHONE`, `_DPO_EMAIL` | datele operatorului | apar pe pagina publică „Operator” și în documentele legale |
| `RESEND_API_KEY` | cheia Resend | emailurile de notificare „Rădăcini: …” (fără ea: doar notificări în aplicație) |
| `RADACINI_PUBLIC_URL` (opțional) | adresa publică | linkurile din emailuri, dacă Rădăcini are domeniu propriu |
| `PG_POOL_MAX` (opțional) | `10` | doar împreună cu portul **6543** (pooler tranzacție) în `SUPABASE_DB_URL`; vezi `TEST_INCARCARE.md` |

Pe frontend (Cloudflare, la build): `NEXT_PUBLIC_RADACINI_ENABLED=true`; opțional `NEXT_PUBLIC_RADACINI_TILE_URL` și `NEXT_PUBLIC_RADACINI_TILE_ATTRIBUTION` (furnizor de hartă cu contract, vezi `DPIA_CIORNA.md`).

**Ordinea recomandată:**
1. Datele operatorului și `RESEND_API_KEY`.
2. `RADACINI_ALLOWED_EMAILS` (înainte de pornire, ca nimeni din afara listei să nu intre).
3. `RADACINI_ENABLED=true`, apoi build-ul frontend cu `NEXT_PUBLIC_RADACINI_ENABLED=true`.
4. Smoke test: PropManage merge normal; `/api/radacini/health` răspunde; un cont din listă intră, unul din afara ei primește mesajul de beta închis.
5. Schimbarea pe portul 6543 + `PG_POOL_MAX=10` doar separat, cu smoke test pe tot PropManage.

**Oprire de urgență:** `RADACINI_ENABLED=false` (datele rămân, modulul dispare).

## 4. Prima săptămână
- Zilnic: **Administrare → Sistem** (erori, configurare) și egress-ul Supabase.
- Săptămânal: feedback-ul testerilor, prioritizat în `ROADMAP.md`.
- La final: ștergerea datelor de test (`scripts.radacini_purge_demo`), păstrând demo-ul „Valea Verde”.
