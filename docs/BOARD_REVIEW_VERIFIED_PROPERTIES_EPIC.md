# 🏛️ BOARD REVIEW — EPIC: Verified Properties Commercial Engine
**Conform Board Directive 057 · Iunie 2026 · Bazat pe auditul `/app/docs/VERIFIED_PROPERTIES_AUDIT_2026.md`**

---

## 1. Status implementare actuală
- Modul izolat funcțional: 818 linii backend (`verified_estate.py`) + 5 pagini frontend (1.275 linii).
- Achiziție (seller landing + checkout), moderare (Kanban + 4 Gates), listare publică cu Trust Score — TOATE funcționale.
- **Commercial Readiness: 62%.** Bucla de monetizare LIVE este ruptă (webhook Stripe nu procesează comenzile VE; nu există flux de vânzare/comision).

## 2. Componente reutilizabile
`payments.py` webhook · `verified_estate_orders` · `email_sequences` drip/newsletter · `house_health_plans+billing` · `digital_twin` projects/members · `auth/register` · `user_timeline`.

## 3. Funcționalitate lipsă (GAP)
G1 webhook Stripe LIVE pt. VE (P0) · G2 flux vânzare + comision (P0) · G3 audit workflow structurat (P1) · G4 onboarding cumpărător (P1) · G5 Cartea Digitală a Casei (P1) · G6 twin real pe detaliu (P2) · G7 attach servicii premium (P2).

## 4. Riscuri
- **R1 (extern, P0):** Stripe LIVE neactivat de Founder → chiar și cu G1 fixat, banii reali nu circulă.
- **R2 (extern, P0):** DNS Resend nefixat pe Rackhost → emailurile de confirmare comandă nu pleacă în producție.
- **R3 (legal, P1):** e-Factura RO obligatorie pentru facturarea B2B — trebuie înainte de volum comercial.
- **R4 (operational):** fără audit workflow structurat (G3), scalarea depinde de introducere manuală în admin.
- **R5 (tehnic, scăzut):** modul izolat cu feature flag → risc de regresie minim.

---

## 5. OPINIILE EXECUTIVILOR

### CEO — „Ne apropie de poziția de lider?"
- **Opinie:** DA. Verified Properties e diferențiatorul #1 vs. Storia/Imobiliare.ro (ei listează, noi VERIFICĂM). Faza A e obligatorie.
- **Risc:** lansarea completă A→D fără cerere validată consumă 90 credite pe un flux netestat comercial.
- **Recomandare:** GO Faza A, apoi validare cu 3–5 clienți reali. **Confidence: 90%.**

### CTO — „Se poate construi mai simplu?"
- **Opinie:** Faza A e minimă și chirurgicală: extindere webhook existent + un status + un calcul. Zero refactor. Fazele C (handover) au complexitate reală (transfer ownership, conturi).
- **Risc:** a construi Cartea Digitală (G5) înainte de prima vânzare reală = infrastructură pentru zero utilizatori.
- **Recomandare:** GO A. B–D doar după prima tranzacție. **Confidence: 95%.**

### CPO — „Înțelege un utilizator nou?"
- **Opinie:** UX 7/10, fluxul vânzător e clar. Butonul „Deschide Digital Twin" care duce la `/demo` (G6) e o promisiune falsă — afectează încrederea exact pe pagina unde vindem încredere.
- **Recomandare:** GO A + include micro-fix G6 (link twin real sau ascunde butonul dacă nu există twin — cost ~1 credit). **Confidence: 85%.**

### CMO — „De ce ar alege un client PropManage?"
- **Opinie:** „Singura platformă unde imobilele sunt verificate tehnic" = mesaj de campanie perfect. Dar nu putem face marketing pe un checkout care funcționează doar în demo.
- **Oportunitate:** Traseul C (audit imobil de pe Storia) e un cal troian de achiziție subestimat — merită promovare după Faza A.
- **Recomandare:** GO A urgent; campanie doar după Stripe LIVE + Resend DNS. **Confidence: 88%.**

### CFO — „E investiția justificată?"
- **Opinie:** Faza A: 15–20 credite → deblocheză ~8.800 RON/tranzacție. Amortizare la PRIMA comandă. Cel mai bun ROI disponibil acum în tot backlog-ul.
- **Risc:** Fazele B–D (60–70 credite) înainte de venit validat = speculație. e-Factura (R3) trebuie bugetată înainte de volum.
- **Recomandare:** GO A. STOP după A până la prima tranzacție reală. **Confidence: 92%.**

### COO — „Poate rula cu mai puțină muncă manuală?"
- **Opinie:** Azi fluxul post-plată e 100% manual (agent completează listing, audit, reco). Acceptabil la volum mic (<10 imobile/lună). G3 devine necesar doar la scalare.
- **Recomandare:** GO A; B când depășim 10 comenzi/lună. **Confidence: 85%.**

### Customer Success Director — „Ne vor recomanda clienții?"
- **Opinie:** Gates + Trust Score = mecanica de încredere corectă. Dar dacă un client plătește 1.300 RON și confirmarea de plată nu ajunge (R2 Resend) sau comanda rămâne „pending" (G1), încrederea moare la prima interacțiune.
- **Recomandare:** GO A condiționat de rezolvarea R1+R2 de către Founder în paralel. **Confidence: 87%.**

### CHAIRMAN — sinteză și supraveghere
- Aliniere cu Constituția și North Star: DA (Digital Twin rămâne nucleul; Verified Properties e canalul comercial al Twin-ului).
- Dezacord în Board: **niciunul pe Faza A** (unanimitate). Dezacord parțial pe momentul Fazelor B–D → rezolvat prin condiția „prima tranzacție reală înainte de B".
- **Commercial Gate:** valoare client DA · încredere DA · conversie DA · venit recurent DA (prin D, ulterior) · simplificare DA (reuse, zero refactor).

---

## 6. DECIZIA BOARD-ULUI

# ✅ APPROVED WITH CONDITIONS

**Aprobat:** FAZA A — Verified Properties Commercial Engine (15–20 credite)
1. Webhook Stripe LIVE procesează `verified_estate_orders` (G1)
2. Status `sold/reserved` + calcul comision 2.5% + jurnal tranzacție (G2)
3. Micro-fix G6: buton Twin real sau ascuns (cerința CPO, ~1 credit)

**Condiții:**
- C1: Founder activează Stripe LIVE (acțiune externă, blocker existent)
- C2: Founder fixează DNS Resend pe Rackhost (acțiune externă, blocker existent)
- C3: Fazele B–D NU pornesc fără GO separat + minim 1 tranzacție reală validată

**Respins pentru acum:** lansarea simultană A→D (90 credite) — cost speculativ, împotriva principiului „măsoară înainte să investești" (Directive 058).

*Decizia finală aparține Founderului (Directive 058).*
