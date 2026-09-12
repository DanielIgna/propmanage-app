# BOARD DIRECTIVES 012 / 013 / 014 — EXECUTION GOVERNANCE (permanente, 25 Iul 2026)

## 012 — Implementation Safety Mode
Stabilitatea codului > viteza de livrare. Modul funcțional NU se refactorizează / redenumește /
mută / rescrie — DOAR se extinde. Permise: endpoint nou, componentă nouă, tabel nou, serviciu nou,
eveniment nou. Interzise fără aprobare Board: rewrite, refactor mare, cleanup arhitectură/foldere/
naming, "implementare mai bună". Fiecare livrare include: Risk Level, Backward Compatibility,
Files Modified, Regression Risk, Rollback Plan. Regression risk HIGH → STOP, cere aprobare Board.

## 013 — Development Governance Mode
Arhitectura ÎNCHISĂ (GI-0/4/5/5P/6/7 aprobate). Priorități: 1 Working > 2 Stable > 3 Comercial >
4 UX > 5 Arhitectură. Checklist obligatoriu pre-implementare: există deja? → extinde;
se poate cu servicii existente? → reutilizează; modifică comportament existent? → regresie;
cere refactor? → STOP (aprobare Board); se poate cu mai puțin cod? → alege varianta simplă.
Fiecare implementare: Purpose, Business Value, Customer Value, Technical Risk, Regression Risk,
Files Modified, DB Changes, Rollback Plan, DoD, Tests Executed.
Fiecare sprint se încheie cu: ce s-a construit / valoare comercială / problema clientului rezolvată /
cod reutilizat / datorie tehnică creată / datorie tehnică eliminată.
Recompensa = mai puțin cod, mai puțină complexitate, mai multă stabilitate, mai multă valoare.
Interzise implicit: duplicate (servicii/API/DB/module AI/agenți/dashboards/concepte/logică) +
documente noi de arhitectură necerute. Feature nou doar cu valoare comercială măsurabilă.

## 014 — Product First
La opțiuni multiple valide → alege ce crește valoarea PRODUSULUI Digital Twin.
Niciodată: platforma înaintea produsului, AI înaintea valorii pentru client, arhitectura înaintea
adopției. Cele 4 întrebări per sprint: 1) Face Twin-ul mai valoros? 2) Clientul înțelege feature-ul?
3) Ajută la vânzare? 4) Reduce efortul clientului? — majoritar NU → amână.
Digital Twin = nucleul; totul există ca să-i crească valoarea.
