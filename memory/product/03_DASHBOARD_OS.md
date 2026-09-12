# 03 · DASHBOARD OS (propunere Faza 2 — spre aprobare Fondator)
Șablon unic de prezentare („RoleShell") cu 6 sloturi fixe, configurat per rol+maturitate. Doar presentation layer.

## Sloturile (ordine imuabilă)
1. **Welcome** — nume + context scurt (1 rând).
2. **Next Action** — UN card hero cu UN CTA. Sursa: starea reală a contului.
3. **Progress** — UN singur sistem de progres per rol (client: pașii casei; specialist: tier progress). Dispare când nu mai e relevant.
4. **Alerts** — plăți în așteptare, confirmări, expirări (max 3, restul „vezi toate").
5. **Recent** — ultimele evenimente, traduse uman, colapsate la 3.
6. **Optional** — Descoperă/upsell contextual: MAXIM 1 card, doar dacă nu contrazice Next Action.

## Configurația per rol (rezumat; matrice completă în 05)
- **Client J0**: 1+2. Atât.
- **Client J1-J2**: 1+2+3 (pașii 2-3: document, audit).
- **Client Verified**: 1-5 + Sănătatea casei (scor unic).
- **Client Premium**: 1-6 (Copilot devine sursa slotului 2; Twin/Marketplace/Mentenanță în nav).
- **Specialist Entry**: modelul existent `SpecialistEntryHome` (validat 86/100) = implementarea de referință a shell-ului.
- **Specialist Junior/Verified**: 1-5 (Next = cerere nouă/ofertă; Progress = tier, real).
- **Specialist Advanced+**: 1-6 (+Cockpit pipeline ca slot 5/6; zero elemente de onboarding).

## Reguli hero (slot 2)
- Un client cu plată în așteptare NU vede alt CTA primar pe ecran (Solicită/upsell devin text-links).
- CTA-ul hero nu se repetă nicăieri altundeva pe ecran (tile-urile duplicate dispar).

## Property Hub → „Casa mea" (3 straturi)
1. Scor UNIC „Sănătatea casei" + next step + CTA.
2. 3 secțiuni colapsate: Cartea casei (documente+pașaport) · Casa în detaliu (twin, active, date) · Istoric.
3. 1 card Descoperă contextual.
PVI/Maturity/Risc = drill-down, nu carduri de prim rang.
