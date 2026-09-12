# DESIGN SPECIFICATION — toate fazele (gate de aprobare per fază)
Status: SPRE APROBARE FAZĂ CU FAZĂ · Owner: Product Council · Regula: nicio implementare fără specificație aprobată. P3a e detaliată complet în `SPEC_P3A_IMPLEMENTATION.md`.

> Notă de fazare actualizată (PPOS-015): P3b/P3c/P3d livrează fiecare DOUĂ prezentări — desktop workspace (PPOS-005) + mobil task-first (PPOS-006) — pe aceleași API-uri.

---

## FAZA P3a — IGIENĂ & ONESTITATE
1. **Problema actuală**: 4 overlay-uri simultane la primul login; specialist matur cu 4 sisteme de progres contradictorii; 9 unelte blocate listate; marketplace public cu „REJECTED"/★5(0); jargon de sistem netradus; CTA duplicat pentru aceeași plată; „Feedback beta" acoperă bottom nav pe mobil.
2. **Cauza rădăcină**: feature-uri livrate în momente diferite, fiecare cu propriul sistem de stare care NU citește realitatea contului; două câmpuri de tier (`tier` vs `experience_tier`) citite inconsecvent de UI; overlay-uri adăugate independent fără buget de atenție comun; randare publică neprotejată la date imposibile.
3. **Impact utilizator**: primele 10 secunde pierdute; neîncredere („platforma nu știe cine sunt"); vizitatorii văd contra-dovezi de încredere pe pagina care vinde încredere.
4. **Soluția propusă**: 8 modificări chirurgicale, exclusiv presentation layer (detaliu în SPEC_P3A): tur on-demand, cookie compact, feedback mutat, UN sistem de progres specialist derivat din date, unelte blocate ascunse, marketplace defensiv, dicționar de traducere evenimente, timeline pașaport colapsat, dedupe CTA plată.
5. **Before → After**: specialist VERIFIED vede „Nivel JUNIOR + 0/6 pași + primul lead 0/1 + 100% către ADVANCED" → vede UN card „Progresul tău: VERIFIED → ADVANCED" (sau nimic); marketplace cu „TEST/REJECTED/★5(0)" → doar specialiști aprobați, „Nou pe platformă" fără recenzii.
6. **Efort estimat**: 1 sesiune de dezvoltare (S-M per modificare; niciun endpoint nou).
7. **Impact business așteptat**: încredere beta (VoC), TTFV mai mic, bounce mai mic pe marketplace, time-to-cash pe plăți (CTA unic).
8. **Îmbunătățire scor UX estimată**: Specialist 52→~70 · Marketplace 58→~80 · Pașaport 80→~85 · Property Hub 55→~60 (doar jargon) · Client activ 72→~76 · media platformă 68→~75.
9. **Ecrane modificate**: `/client`, `/specialist`, `/marketplace`, `/p/{slug}`, global (cookie banner, tur, feedback, chat).
10. **Riscuri**: descoperirea funcțiilor scade fără tur auto (mitigare: „?" vizibil + tooltip discret prima dată); ascunderea specialiștilor neaprobați scade numărul afișat (mitigare: doar test/neaprobați dispar); starea quest-urilor vine din `/api/me/quests` (mitigare: filtrare de prezentare, recompensele backend rămân intacte).

## FAZA P3b — CLIENT DASHBOARD OS (desktop + mobil)
1. Problema: dashboardul client nu crește cu utilizatorul (J0 vede AI/Descoperă; toate tier-urile văd la fel); desktop = coloană ~880px cu spațiu mort; alertele sub tile-uri.
2. Cauza: un singur layout pentru toate stările + „mobile stretched".
3. Impact: activare sub potențial (pasul 1-2-3 concurează cu zgomot); desktopul nu ajută managementul.
4. Soluția: RoleShell (PPOS-007) cu matricea J0→P + desktop workspace 8+4 (main + right context panel cu starea casei și Copilot) (PPOS-005 §4.3); eliminarea tile-urilor duplicat.
5. Before → After: J0 vede hero+CTA și ATÂT; activul vede hero tranzacție + alerts + context panel; desktopul folosește ≥80% lățime utilă.
6. Efort: 1-2 sesiuni. 7. Impact: activare J0→J1, conversie audit. 8. Scor estimat: Client nou 78→92+, Client activ 72→92+, desktop 58→90+. 9. Ecrane: `/client` (HomeV2 + shell), navigație client. 10. Riscuri: regresii pe fluxuri existente (mitigare: feature flag `pm_client_ui` există + testing agent full).

## FAZA P3c — SPECIALIST DASHBOARD OS „Mission Control" (desktop + mobil)
1. Problema: admin-panel cu tot ce s-a construit; fără tabele deși procesează volum; bottom nav pe desktop.
2. Cauza: acumulare de module fără shell; layout unic mobil.
3. Impact: retenția specialiștilor (instrumentul zilnic de venit).
4. Soluția: modelul Entry extins pe tier-uri (PPOS-007) + desktop split view Linear-style: tabel cereri/lucrări cu filtre/sortare/bulk + right panel detaliu + KPI strip sticky (PPOS-005 §4.1); Cockpit doar Advanced+.
5. Before → After: 10 secțiuni stivuite → „Astăzi: 1 cerere nouă" + listă procesabilă cu detaliu lateral.
6. Efort: 2 sesiuni. 7. Impact: viteza de răspuns la cereri (SLA <1h), venit specialist. 8. Scor: 52→90+, desktop 48→90+. 9. Ecrane: `/specialist` complet. 10. Riscuri: obiceiuri formate ale utilizatorilor beta (mitigare: flag + „înapoi la vechiul dashboard" temporar).

## FAZA P3d — PROPERTY HUB „CASA MEA" (desktop + mobil)
1. Problema: pagină-fluviu, 5 scoruri concurente, formulare mereu deschise; desktop 31% lățime.
2. Cauza: fiecare sprint și-a adăugat cardul; fără ierarhie de scoruri.
3. Impact: proprietarul nu poate răspunde „cum stă casa mea?" → nu vede valoarea → nu plătește auditul.
4. Soluția: record page Notion-style (PPOS-005 §4.2): left sub-nav secțiuni, right panel sticky cu UN scor+next step, documente ca tabel, editare inline; PVI/Maturity/Risc = drill-down.
5. Before → After: 6 ecrane de scroll → 1 ecran cu 5 secțiuni navigabile și scor permanent vizibil.
6. Efort: 2 sesiuni. 7. Impact: conversie audit/twin (next step permanent vizibil). 8. Scor: 55→90+, desktop 42→90+. 9. Ecrane: tab Proprietăți/`PropertyHubV2`. 10. Riscuri: cea mai mare suprafață (mitigare: secțiune cu secțiune, flag, testare la fiecare pas).

## FAZA P4 — NAVIGAȚIE
1-3. Problema/cauza/impact: navigație duplicată (header+bottom+tile-uri) = confuzie și întreținere dublă. 4. Soluția: o navigație per device (PPOS-004); eliminarea tile-urilor duplicat rămase. 5. Before→After: 3 căi spre Lucrări → 1. 6. Efort: 0.5 sesiune. 7. Impact: consistență. 8. Scor: +2-4 global. 9. Ecrane: shell client+specialist. 10. Risc: minim.

## FAZA P5 — MOBILE
1-3. Overlap-uri, thumb-zone, liste necolapsate rămase. 4. Soluția: PPOS-006 aplicat + re-test 390 pe toate paginile modificate. 5. 6. Efort: 0.5-1 sesiune. 7. Impact: beta users pe telefon (majoritatea). 8. Scor mobil: →90+. 9. Toate ecranele modificate. 10. Risc: minim.

## FAZA P6 — RE-AUDIT & ROLLOUT
Re-scoring complet (PPOS-010), fix-uri sub 95, Product Decisions actualizate, GO/NO-GO beta din perspectiva experienței, apoi rollout producție (redeploy de către Fondator).
