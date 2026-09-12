# RELEASE CHECKLIST (UI)
Înainte de orice merge de UI:
1. UX Review trecut (cele 7 întrebări din `08_PRODUCT_QA.md`) — aprobare automată INTERZISĂ.
2. Un singur CTA primar per ecran, ordinea 1-6 respectată.
3. Zero elemente vizibile pe care userul curent nu le poate folosi.
4. Mobil 390 verificat: fără suprapuneri, thumb-zone OK.
5. Empty states complete; zero jargon de sistem; zero stări imposibile (★5(0), REJECTED public).
6. data-testid pe toate elementele interactive.
7. Scor pagină ≥95 (self-audit) + testare (testing agent / capturi).
8. API/DB/permisiuni neatinse; feature flag/rollback disponibil.
