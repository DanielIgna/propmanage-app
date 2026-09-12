# PPOS-010 · Quality Gates
Status: Draft v1.0 · Owner: Product Council

## Gate-ul suprem
Nicio funcționalitate nouă până ce fluxul existent nu are **≥95/100** (claritate, simplitate, mobil). Sub 95 → redesign din nou.

## NO REGRESSION RULE (Fondator, Iun 2026)
Nicio implementare nu are voie să reducă: **UX Score · Desktop Score · Mobile Score · Performance · Accessibility · Trust**. Dacă ORICE metrică scade la re-audit, implementarea EȘUEAZĂ automat și modificarea respectivă se face rollback imediat. Verificarea se face DUPĂ FIECARE fază (Audit → Implement → Re-audit → doar apoi faza următoare — niciodată trei faze implementate și verificate la final).

## Scoring per pagină (9 dimensiuni)
Claritate · Simplitate · Accesibilitate · Mobil · Performanță · Consistență · Sarcină cognitivă · Impact venit · Încredere → Overall ≥95.

## UX Review (obligatoriu la ORICE schimbare de UI; aprobarea automată e interzisă)
1. Care e UNICA acțiune a ecranului? 2. Câte CTA-uri primare? (>1 = FAIL) 3. Există element nefolosibil de userul curent vizibil? (= FAIL) 4. Testul de 10 secunde trece? 5. Mobil 390: fără suprapuneri, thumb-zone OK? 6. Desktop ≥1280: workspace, nu coloană mobilă? (PPOS-005) 7. Empty states complete? 8. Contrazice vreo stare reală a contului? (= FAIL) 9. Hick/Miller/Progressive Disclosure/Fitts/ierarhie respectate?

## Release Process
Specificație aprobată de Fondator → review Product Council (PPOS-020, unanim) → 3 soluții explorate → implementare STRICT pe specificație (fără layout-uri inventate) → self-audit ≥95 → testare (testing agent + capturi desktop 1920 & mobil 390) → Product Decision înregistrat → rollout cu feature flag + rollback.
Checklist operațional: `/app/memory/product/audits/RELEASE_CHECKLIST.md`.
