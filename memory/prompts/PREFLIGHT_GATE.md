# PREFLIGHT GATE — Knowledge Center ca poartă obligatorie pre-implementare

**Artifact Type**: DOCUMENT (protocol operațional)
**Owner**: Fondator (danieligna1@gmail.com)
**Status**: ACTIVE · OBLIGATORIU pentru orice agent/task de implementare
**Emitent**: Iun 2026 (Governance Hardening post-Task 8R)
**Poziție în ierarhie**: derivat din `MASTER_KNOWLEDGE_GOVERNANCE.md`; NU rescrie arhitectura — o protejează.

---

## 0. Principii (în această ordine)
KNOWLEDGE BEFORE CODE · CANONICAL BEFORE NEW · REUSE BEFORE CREATE · CONFLICT BEFORE GUESS · TARGETED VERIFICATION BEFORE FORENSIC AUDIT · DOCUMENT ONCE · ONE SOURCE OF TRUTH · STOP WHEN THE TASK IS DONE.

## 1. Preflight obligatoriu (NU e audit complet — max ~10 minute)
Înainte de ORICE implementare, agentul răspunde la:
1. Capabilitatea există deja? (caută în `registries/CANONICAL_SYSTEM_REGISTRY.md`, `SSOT_REGISTRY.md`, `FUNCTION_MAP.md`, `MASTER_PLATFORM_STATE`, cod: `grep` pe rute/colecții/componente)
2. Există implementare echivalentă?
3. Există rute/API pentru asta?
4. Există colecții/documente DB pentru asta?
5. Există implementare canonică? Care?
6. Care e Source of Truth curent?
7. Clasificare task: **NEW / EXTEND / MODIFY / CONSOLIDATE / REMOVE**

Clasificare obligatorie a ceea ce găsești: `NEW · EXISTING · EXTENSION · DUPLICATE · CONFLICT · DEPRECATED`.
Dacă există implementare → default: **REUSE / EXTEND / CONSOLIDATE**, NU a doua implementare.

## 2. CHANGE INTENT obligatoriu (declarat înainte de cod)
```
TASK INTENT: NEW / EXTEND / MODIFY / CONSOLIDATE / REMOVE
Implementare existentă: ...
Implementare canonică: ...
Source of Truth: ...
Rute existente: ...
Structuri DB existente: ...
Consumeri frontend/backend existenți: ...
Documente KC relevante: ...
De ce NU e duplicat: ...
Scope așteptat: ...
```
Dacă aceste fapte nu pot fi stabilite → **STOP** + raportează conflict de guvernanță.

## 3. Protocol de CONFLICT (KC vs runtime/cod)
NU ghici. NU crea altă implementare. NU rescrie silențios documentația. NU șterge silențios implementarea existentă. Raportează:
```
CONFLICT DETECTED
Knowledge Center spune: ...
Runtime/codul spune: ...
Duplicat potențial: ...
Source of Truth potențial: ...
Decizie Fondator/canonică necesară: ...
```
Apoi **STOP**.

## 4. Prevenirea duplicării — căutare țintită obligatorie
Înainte de a crea: rută · endpoint · colecție DB · document DB · pagină React · provider · serviciu · job scheduler · sistem de backup · sistem de configurare · pagină admin · feature flag · sistem de design tokens · sistem de documentare —
caută în: KC (`/app/memory`, `/app/docs`) · MASTER_PLATFORM_STATE · CANONICAL_SYSTEM_REGISTRY · cod existent · rute existente · structuri DB existente · consumeri frontend. Echivalent găsit → reuse/extend. A doua implementare cere justificare explicită + aprobare canonică.

## 5. Documentația NU declară „NEW" fără dovadă
Orice document generat distinge: **PRE-EXISTING · NEW · MODIFIED · MIGRATED · DEPRECATED · REMOVED**.
O colecție/rută/job/serviciu nu e „NEW" doar pentru că task-ul curent nu știa de ea. (Eșecul exact: `db.design_tokens` declarat „colecție nouă" în Task 8 deși pre-exista și era consumat de runtime.)

## 6. Politica de audit — reducerea abuzului de audit
Workflow implicit: **Preflight KC → implementare țintită → teste țintite → update documentație → STOP.**
Audit forensic complet DOAR la: conflict de Source of Truth · duplicat detectat · risc de migrare DB · problemă de securitate · regresie majoră · schimbare de arhitectură · blocker de producție · contradicție canonic-vs-runtime · cerere explicită a Fondatorului. Altfel: doar verificarea minimă țintită.

## 7. Finalizarea task-ului NU creează scope nou
După task: VERIFICĂ → DOCUMENTEAZĂ → ACTUALIZEAZĂ starea canonică → **STOP**.
Sugestiile (ex. Specialist Basic Entitlement, Client PRO/PREMIUM, Theme Scheduler etc.) rămân **BACKLOG/PROPOSALS** până la autorizare explicită a Fondatorului. Sugestiile AI nu devin scope de implementare de la sine.

## 8. Protocol de update al Knowledge Center
La finalul fiecărui task de implementare (doar dacă implementarea chiar a schimbat ceva), înregistrează: ce s-a schimbat · ce NU s-a schimbat · Source of Truth canonic · componente new/modified/deprecated · rute afectate · structuri DB afectate · teste · status migrare · status deploy · conflicte nerezolvate · next action doar dacă e autorizat explicit.
Înainte de a crea un document nou: caută documentul canonic existent. **EXTEND/UPDATE > CREATE.** Zero documente duplicate pe același concept.

## 9. Protecția MASTER_PLATFORM_STATE
MASTER_PLATFORM_STATE rămâne documentul canonic de guvernanță validat uman. Agenții NU rescriu silențios decizii arhitecturale. Dacă realitatea implementării diferă de arhitectura documentată → înregistrează discrepanța + cere update-ul de guvernanță. Documentele task-specific nu devin surse de adevăr concurente.

## 10. Documentele EXECUTION_ORDER
EO-urile sunt ÎNREGISTRĂRI DE TASK, nu surse de arhitectură concurente. Descriu ce s-a întâmplat în task și FAC REFERINȚĂ la KC/MASTER_PLATFORM_STATE/CANONICAL_SYSTEM_REGISTRY în loc să redefinească arhitectura independent.

---

## 11. Validare istorică — gate-ul ar fi prins Task 8 ÎNAINTE de cod

| # | Eșec Task 8 | Cum îl prindea preflight-ul |
|---|---|---|
| A | `db.design_tokens` declarat NOU | Preflight Q4 („există colecție DB?") → `grep design_tokens backend/` găsea `design_studio.py` scriind în `{_id:"active"}`; DB avea doc-ul; clasificare corectă: **EXISTING**, nu NEW |
| B | Design Studio exista deja (mai bogat, conectat la runtime) | Preflight Q1/Q5 → `DesignStudioPage.jsx` + ruta `/admin/design-studio` + `DesignTokensProvider` erau în cod; registrul ar fi avut rândul „Design Tokens → design_studio CANONICAL" → verdict: **DUPLICATE** → REUSE/EXTEND, nu router nou |
| C | 4 sisteme backup/config paralele | Preflight Q2 → căutarea „snapshot/backup/export" găsea `admin_console`, `settings_snapshots`, `admin_backups`; Change Intent „De ce NU e duplicat" nu putea fi completat → **STOP + conflict** înainte de config_io paralel |
| D | „Preview Overlay" fals etichetat | Preflight Q3 → `pages_registry.py::admin_preview` exista; clasificare **EXTENSION** cu semantică de clarificat, nu feature „nou"; regula §5 interzicea claim-ul de overlay fără renderer |
| E | Renewal/Copilot aveau comportament înrudit | Preflight Q2 → `grep renew` găsea `renew_subscription` în `propbenefits/`; Change Intent cerea declararea consumatorilor existenți → coordonarea se proiecta ÎNAINTE de cod |
| F | „Al 21-lea job" declarat fără numărare | Regula §5 (zero claim fără dovadă) + rândul „Scheduler" din registru („numără înainte să declari") → `grep -c scheduler.add_job` = 70 (+2) → claim imposibil |
| G | Fallback silent al impersonării pe useri REALI (incident prod 24 Aug 2026) | Preflight Q1 („capabilitatea există deja?") + Q5 („implementare canonică?") → căutarea „impersonate/quick-switch" găsea `impersonation.py` cu allowlist STRICT; regula anti-„NEW fără dovadă" (§5) + rândul „Conturi demo quick-switch" din registru („INTERZIS fallback pe useri reali") → orice cale alternativă care rezolvă email → user via lookup pe rol în loc de allowlist era clasificată **CONFLICT** înainte de cod, cu STOP obligatoriu până la decizia Fondator. Lecția: guvernanța protejează nu doar împotriva declarațiilor false „NEW", ci și împotriva rutelor silențioase care ocolesc source-of-truth-ul (allowlist) în favoarea unei date runtime (rolul user-ului) care poate fi drift-uită. |

**Concluzie**: dacă gate-ul exista înainte de Task 8, duplicarea/conflictul era detectat(ă) ÎNAINTE de cod, iar auditul forensic + remedierea (Task 8R) nu ar fi fost necesare. Rândul G extinde validarea la clasa „silent-fallback pe date runtime în locul source-of-truth-ului declarativ" — clasă distinctă de eșec, prevenită prin aceeași disciplină preflight.
