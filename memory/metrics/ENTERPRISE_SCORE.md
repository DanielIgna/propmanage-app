# ENTERPRISE SCORE (document derivat — poate fi rezumat)

**Sursa de adevăr:** `GET /api/enterprise-health` (backend `routes/enterprise_health.py`) + Formula Registry (D151, `board/directives/BOARD_DIRECTIVE_151_ENTERPRISE_HEALTH_FORMULA_REGISTRY.md`).

Enterprise Score = media ponderată a domeniilor din Formula Registry (fiecare domeniu = sumă ponderată de
metrici cu țintă, subscor 0–100). Domeniile includ: Product/Twin coverage, Design Quality, Operations,
Growth, Marketplace, Trust, Knowledge, Revenue, Autonomy, Quality/QA, Learning (AI outcomes).

- Istoric: colecția `enterprise_health_history` (snapshot zilnic via scheduler).
- Fiecare metrică are: `label`, `source`, `weight`, `target`, subscor calculat live din DB.
- Alertele indică metrica cu cel mai mare câștig potențial (gain = (target − subscor) × pondere).

Regulă: formula NU se modifică fără actualizarea Formula Registry (D151) și consemnare în Decision Register.
