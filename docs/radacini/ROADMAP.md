# Rădăcini — pașii următori (după S8)

Stare la 2026-10-14: S1–S8 implementate pe branch-ul `radacini` (testele complete sunt în rulare la scrierea acestui document). Modulul e **oprit implicit în producție**. Nimic nu e pe `main` și nimic nu e lansat.

## Etapa 1 — Închiderea pregătirii pilotului (zile)
| # | Pas | Cine | Rezultat |
|---|---|---|---|
| 1.1 | Rezultatul testelor S1–S8, commit, push | echipa tehnică | branch verde pe GitHub |
| 1.2 | Încerci tu fluxurile cu conturile de test („Generează date demo”) și notezi ce nu e clar | fondator | listă de ajustări UX |
| 1.3 | Trimiți `DOSAR_JURIST.md` unui jurist și ceri oferte pentru revizuire | fondator | termeni revizuiți, deblocarea modelelor „vânzare” și „proiect comun” |
| 1.4 | Validezi `COSTURI_PILOT.md`: plan Supabase (egress deja peste cotă), domeniu de email verificat | fondator + tehnic | buget lunar confirmat |
| 1.5 | Ajustări din 1.2 + texte revizuite de jurist (versiunea nouă a termenilor) | tehnic | versiune de lansare |

## Etapa 2 — Lansare tehnică controlată (decizia ta)
1. Merge `radacini` → `main` cu modulul **oprit** (`RADACINI_ENABLED=false`). Pentru utilizatorii PropManage nu se schimbă nimic.
2. Deploy pe Railway și Cloudflare. Smoke test: PropManage funcționează, iar `/api/radacini/*` răspunde 404 cât e oprit.
3. Pornire în producție doar pentru o listă albă (fondator, testeri). Variabilele se setează doar după aprobare. Pașii, emailul de invitație și ce testează invitații: `GHID_BETA.md`.
4. Monitorizare egress și erori o săptămână.

## Etapa 3 — Pilot Cluj (4–8 săptămâni)
- **Recrutare:** 10–20 de proprietari de teren, 20–50 de familii sau cultivatori, 2–3 operatori de teren (Florești, Gilău, Apahida).
- **Operatorii** verifică terenurile, fac onboarding asistat pentru vârstnici și mediază disputele.
- **Indicatori** (din Administrare): terenuri verificate, acorduri semnate, proiecte active, kg recoltate, rezervări finalizate, dispute.
- **Feedback** săptămânal, cu ajustări rapide.

## Etapa 4 — După pilot (prioritizat după rezultate)
- Abonamentul de 5 €/lună și contul familial (facturare, TVA, termeni „fără cantitate garantată”).
- Gamification separată de drepturi: insigne, obiective sezoniere.
- Livrări și comenzi grupate.
- Legătura cu specialiștii PropManage prin Capability Engine.
- Investiții colective, doar după aviz juridic.
- PostGIS, dacă volumul de căutări geografice o cere.

## Pista nouă — Composesorate
Analiză întâi, implementare după. Vezi `composesorate/ANALIZA_INITIALA.md`.
1. **Faza 0 (acum):** primești lista de documente de trimis, anonimizate.
2. **Faza 1:** analiza complexă pe documentele reale (tipare, probleme, cadru legal de validat cu juristul).
3. **Faza 2:** proiectarea modulului (roluri, registre, transparență, conectarea la piața Rădăcini) și aprobarea ta.
4. **Faza 3:** MVP pe un composesorat pilot (cu acordul conducerii lui).
