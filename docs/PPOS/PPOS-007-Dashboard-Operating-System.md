# PPOS-007 · Dashboard Operating System
Status: Draft v1.0 · Owner: Product Council
(Șablonul „RoleShell" — sursă: audit Faza 1; configurat per rol+maturitate; doar presentation layer.)

## Sloturile (ordine imuabilă)
1 **Welcome** (1 rând) → 2 **Next Action** (UN hero, UN CTA, derivat din starea reală) → 3 **Progress** (UN singur sistem per rol; dispare când e complet) → 4 **Alerts** (max 3) → 5 **Recent** (colapsat la 3, tradus uman) → 6 **Optional** (max 1 card Descoperă/upsell, niciodată concurent cu Next Action).

## Matricea client (declanșatoare = DATE, nu etichete)
J0 (0 proprietăți): sloturi 1+2. · J1 (≥1 proprietate): +3 (pasul document). · J2 (≥1 document): +3 (pasul audit). · Verified (audit): +Sănătatea casei/Recomandări/Istoric. · Premium (twin/abonament): tot + Copilot ca sursă a slotului 2.

## Matricea specialist (UN progres: tier ENTRY→TOP)
ENTRY: modelul existent `SpecialistEntryHome` (86/100 — referința shell-ului). JUNIOR: +istoric. VERIFIED: +cereri noi/recenzii/șabloane. ADVANCED: +Cockpit pipeline. PREMIUM/TOP: +capabilități/profil premium/rapoarte. Uneltele blocate: invizibile; 1 rând „Următoarea deblocare: X".

## Reguli hero (slot 2)
- Tranzacție activă neterminată (plată/confirmare) = singurul CTA primar de pe ecran.
- CTA-ul hero nu se repetă nicăieri altundeva pe ecran.
- Niciun checklist nu poate contrazice starea contului (interzis „primul lead 0/1" la 27 lucrări).

## Property Hub → „Casa mea"
UN scor (Sănătatea casei) + next step sus · 3 secțiuni (Cartea casei / Casa în detaliu / Istoric) · 1 Descoperă. PVI/Maturity/Risc = drill-down. Desktop: layout record Notion-style (PPOS-005 §4.2).
