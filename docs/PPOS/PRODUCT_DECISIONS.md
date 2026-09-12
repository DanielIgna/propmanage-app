# PRODUCT DECISIONS — registru
Regula Fondatorului: fiecare funcționalitate are documentul scurt: Problema · Soluția · Utilizatorul · KPI · Impact venit · Impact încredere · Criterii de succes. Dacă nu poate fi completat → NU intră în dezvoltare.

Format intrare:
```
Decision #NNN · data · status (PROPUS/APROBAT/RESPINS/IMPLEMENTAT)
Problema: … · Soluția: … · Utilizatorul: … · KPI: …
Impact venit: … · Impact încredere: …
Alternativă respinsă + de ce: …
Criterii de succes: …
```

---

Decision #001 · Iun 2026 · status: **IMPLEMENTAT** (GO Fondator + Council unanim; testat 100% — iteration_140)
Problema: primul ecran după login e blocat de 4 overlay-uri; specialistul matur vede 4 sisteme de progres contradictorii; marketplace public afișează stări imposibile.
Soluția: Faza P3a „Igienă & onestitate" (8 modificări, doar presentation layer) — `SPEC_P3A_IMPLEMENTATION.md` · Rezultat: `P3A_BEFORE_AFTER_REPORT.md` (media 68→~75, zero regresii, NO REGRESSION PASS).
Utilizatorul: toți (primul login) + specialiști VERIFIED+ + vizitatori marketplace.
KPI: TTFV, activare J0→J1, bounce pe marketplace, VoC beta.
Impact venit: indirect-mare (încrederea = conversie; time-to-cash pe plăți).
Impact încredere: direct-critic (elimină contradicțiile și datele imposibile publice).
Alternativă respinsă: accordion/colaps pentru elementele contradictorii — respinsă: nu reduce complexitatea și păstrează minciuna în UI.
Criterii de succes: scoruri re-audit ≥ ținte (specialist 52→70+, marketplace 58→80+); zero overlap pe mobil 390; zero „REJECTED"/★5(0) public.

Decision #002 · Iun 2026 · status: PROPUS
Problema: desktopul autentificat = coloană mobilă întinsă (31-52% din lățime folosită); zero productivitate desktop.
Soluția: PPOS-005 Desktop OS (workspace model, split views, tabele) aplicat în P3b/P3c/P3d.
Utilizatorul: specialiști (volum), proprietari power, admin.
KPI: timp per sarcină, scroll depth, task completion desktop.
Impact venit: retenția specialiștilor (instrumentul lor de lucru zilnic).
Impact încredere: platforma arată a software enterprise, nu a site.
Alternativă respinsă: „responsive tweaks" pe layoutul actual — respinsă: rămâne Mobile XL, exact ce interzice PPOS-015.
Criterii de succes: scor desktop per pagină ≥90 la re-audit.
