# LEARNINGS — Remediere Task 8 (Iun 2026)

## Lecții arhitecturale (a nu se repeta)
1. **Verifică ÎNTOTDEAUNA dacă un feature există înainte de a construi un router nou.** Task 8 a construit `routes/design_tokens.py` deși `design_studio.py` + `DesignTokensProvider` existau și erau conectate la runtime. Testele funcționale (23/23 PASS) NU garantează corectitudine arhitecturală — dead write path-ul trecea toate testele dar nu afecta UI-ul.
2. **Grep obligatoriu înainte de features noi**: `design_tokens`, `_id:"active"`, colecția țintă, CSS vars consumate de frontend.
3. **Backup-ul trebuie să captureze starea pe care o consumă RUNTIME-ul**, nu o copie paralelă — altfel restore-ul raportează succes fals.
4. **Ingress-ul de preview Emergent RESCRIE header-ul Origin** către `*.emergentcf.cloud` — verificarea CSRF pe Origin e neutralizată extern; apărarea corectă = header custom (`X-PM-Client`) setat global de axios (auth.js) + verificat în middleware server.py.
5. **Numărătorile din documentație se verifică în cod** (`grep -c scheduler.add_job`), nu se copiază din claim-uri anterioare.

## Mecanisme canonice stabilite (folosește-le, nu crea altele)
- Design tokens: DOAR `design_studio.py` → `{_id:"active"}`. Sanitizare: `_reject_dangerous_deep` (importabilă din design_studio).
- Snapshot config: `admin_console.py` SNAPSHOT_PARTS (cms/settings/trust_weights/presets/design_tokens/pages/site_menu/feature_config).
- Precedență: Runtime → Snapshots → settings_snapshots → config_io → admin_backups. `pages_versions` nu se restaurează NICIODATĂ.
- Coordonare mesaje renewal: ledger `renewal_reminders` cu kind (`basic_expiry_7d` email / `copilot_renew_nudge` in-app), fereastră 24h.
- Scope map middleware: orice endpoint admin NOU trebuie mapat în `middleware_scope.py` SCOPE_RULES (altfel sub-adminii limitați îl pot accesa).
- CSRF: mutațiile /api/admin cu Origin prezent cer `X-PM-Client: propmanage-app` — apelurile fetch() noi către /api/admin trebuie să includă header-ul (axios îl are global).
