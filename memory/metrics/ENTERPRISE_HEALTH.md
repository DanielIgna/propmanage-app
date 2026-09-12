# ENTERPRISE HEALTH (document derivat — poate fi rezumat)

**Sursa de adevăr:** `GET /api/enterprise-health` + UI `/admin` → Enterprise Health (`EnterpriseHealthPage.jsx`).

- Motor: D122 (Enterprise Health Engine) + D151 (Formula Registry) — implementat și testat (iter. 128–129).
- Benzi: scorurile sunt clasificate pe benzi (critic / atenție / sănătos) via `_band()`.
- Snapshot zilnic în `enterprise_health_history` → trend + context istoric pentru CEO Briefing.
- Consumatori: CEO Briefing Engine (D152), Evolution Council (AI 27), Operations Center.

Obligație (EXECUTION ORDER 001): fiecare execuție autonomă măsurată trebuie să-și reflecte rezultatul
în Enterprise Score (prin metricile de Learning/Operations care citesc `ai_decision_ledger` și `ai_outcomes`).
