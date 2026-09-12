# SPRINT 2 — CONSOLIDATION_PLAN.md
**Regim:** ANALIZĂ + PROPUNERE. Nicio migrare, nicio ștergere fără aprobarea Product Owner-ului per etapă.
**Principiu director:** *un singur motor per responsabilitate* (Master Audit F2) · Strategie: **façade + migrare incrementală**, niciodată big-bang. Colecțiile vechi NU se șterg — se marchează read-only/legacy după migrare, conform regulilor Platform Core.
**D5-C:** toate modelele țintă au `tenant_id:"main"` din prima zi.

---

## 2.1 LEADS — 5 colecții → 1 (`leads`)
**RECOMANDAT PRIMUL: cel mai mic risc, cele mai puține date (21 documente total).**

### Stare actuală (măsurat în DB)
| Colecție | Docs | Schemă reală | Consumatori (fișiere) |
|---|---|---|---|
| `marketplace_leads` | 8 | lead_name/email/phone, partner_id, product_category, estimated_value, revenue_generated, stage, source, notes | 4 |
| `city_partner_leads` | 9 | la fel + conversion_date, cross_ref_done, introduced_at | 2 |
| `partner_leads` | 0 | goală | 1 |
| `interior_design_leads` | 0 (curățată de teste) | id, name/email/phone, budget, surface_mp, style, city, lead_type, score, segment, triaged_by, status | 2 |
| `demo_leads` | 4 | name, email, company, role, message, status, source | 1 |

### Model țintă `leads`
```
{ id, tenant_id: "main",
  source: "marketplace_partner" | "city_partner" | "interior_design" | "demo" | ...,
  name, email, phone,
  stage: "new"|"contacted"|"qualified"|"won"|"lost",   // stage+status unificate
  score: 0-100, segment: "hot"|"warm"|"nurture",        // triage AI rulează pe TOATE sursele (azi doar pe interior)
  partner_id?, revenue_generated?, notes?,
  meta: { ...câmpuri specifice sursei: product_category, budget, surface_mp, company, cross_ref_done... },
  created_at, updated_at, created_by? }
```
**Decizie de mapare:** câmpurile comune urcă la rădăcină; specificele intră în `meta` (fără pierdere de date). `stage` normalizat: `new→new`, `contacted/introduced→contacted`, `converted/won→won`.

### Migrare & compatibilitate
1. Modul nou `services/leads_store.py`: `create_lead(source, data)`, `list_leads(source=None, stage=None)`, `update_lead(id, patch)` — cu triage AI integrat la creare pentru toate sursele.
2. Script idempotent de migrare: 21 docs → `leads` (păstrează id-urile vechi în `meta.legacy_id`, colecțiile vechi rămân netratate = rollback natural).
3. Rutele existente (interior_design, city_partners, marketplace_partners, demo) trec pe façade — endpointurile publice NU se schimbă (zero impact frontend).
4. Panourile admin (InteriorDesignAdmin, CityPartners) citesc prin façade filtrat pe `source` — UI neschimbat.
5. Bonus imediat: `weekly_lead_report` (Self-Driving) devine raport pe TOATE lead-urile, nu doar interior design.

**Efort:** ~1 zi · **Risc:** SCĂZUT · **Rollback:** colecțiile vechi intacte · **Câștig:** single view of lead + triage AI universal.

---

## 2.2 CONFIG — 4 sisteme → 1 (`settings` cu namespace-uri)
**AL DOILEA: cel mai mare câștig de mentenanță; risc gestionat prin façade.**

### Stare actuală
| Colecție | Docs | Conținut | Consumatori |
|---|---|---|---|
| `app_settings` | 4 | company, contact, pricing, seo, social, ai_ecosystem | **28 fișiere** (deja quasi-central) |
| `platform_config` | 2 | perechi key/value generice | 2 |
| `platform_settings` | 1 | config tiers/gamification (enabled, threshold_pct, tiers) | 2 |
| `security_config` | 1 | rate limits, geo/vpn/bot block | 2 |

### Model țintă `settings`
```
{ namespace: "company"|"pricing"|"seo"|"social"|"contact"|"ai"|"tiers"|"security"|"platform",
  key: "main" (sau cheie specifică), value: {...}, tenant_id: "main", updated_at, updated_by }
```
### Strategie (fără big-bang — 28 de consumatori!)
1. Façade `services/settings_store.py`: `get_settings(namespace)`, `put_settings(namespace, value, who)` cu **fallback de citire** către colecțiile vechi în tranziție (citește nou → dacă gol, citește vechi) — nimic nu se strică dacă un consumator e migrat mai târziu.
2. Migrare date: 8 documente total — trivial, idempotent.
3. Consumatorii se mută în valuri: întâi cei 6 din platform_config/settings/security (2+2+2 fișiere), apoi cele 28 de referințe app_settings (mecanic: același shape, doar façade).
4. Settings Snapshots (existent) se extinde natural: un singur loc de snapshot = tot configul platformei versionat.
5. Pregătire franciză directă: `tenant_id` pe settings = config ierarhic global→tenant în Sprint 3 fără re-arhitectură.

**Efort:** 1,5-2 zile · **Risc:** MEDIU (mulți consumatori) — mitigat de fallback · **Rollback:** fallback-ul citește vechiul automat.

---

## 2.3 AI CHAT — 4 sisteme → 1 (`ai_sessions`)
**AL TREILEA: date puține, dar 6+ fișiere de rute ating istoricul.**

### Stare actuală
| Colecție | Docs | Formă | Agent |
|---|---|---|---|
| `concierge_messages` | 30 | UN doc per mesaj (role, content, session_id) | Concierge public |
| `marketing_chat_sessions` | 6 | UN doc per sesiune (messages[]) | Marketing admin |
| `interior_assistant_sessions` | 49 | UN doc per sesiune (messages[]) | Design Interior |
| `twin_conversations` | 5 | UN doc per Q&A (question, answer) | Twin QA |

### Model țintă `ai_sessions` (forma per-sesiune — majoritară deja)
```
{ session_id, agent: "concierge"|"marketing"|"interior_design"|"twin_qa"|...,
  user_id?, user_email?, tenant_id: "main",
  messages: [{role, content, ts, meta?}], created_at, updated_at }
```
### Strategie
1. Façade `services/ai_session_store.py`: `append(agent, session_id, role, content, user?)`, `history(agent, session_id, limit)`, `list_sessions(agent)`.
2. Migrare: concierge (30 mesaje → grupare pe session_id), twin (5 Q&A → perechi user/assistant), marketing+interior (copiere directă). Idempotent, legacy intact.
3. Rutele trec pe façade una câte una (concierge_core, interior_design, marketing_growth, twin, admin_ai, gdpr — atenție GDPR: export/ștergere trebuie să vadă noua colecție!).
4. Câștig: memorie AI inspectabilă într-un singur loc + fundație pentru „Agent Runtime unificat" (Audit F6) + GDPR simplu.

**Efort:** 1-1,5 zile · **Risc:** SCĂZUT-MEDIU (GDPR e punctul sensibil — se testează explicit) · **Rollback:** legacy intact.

---

## 2.4 CONTENT — 4 sisteme → 1 sub XOS (ULTIMUL: atinge pagini publice live)
### Stare actuală + verdict per sistem
| Colecție | Docs | Verdict propus |
|---|---|---|
| `site_content` (XOS Content Manager) | 1 | ✅ **MASTER** — rămâne motorul |
| `cms_content` | **0 (goală!)** | retragere directă: codul care o citește trece pe site_content (zero migrare de date) |
| `interior_design_content` | 1 | NU se contopește în chei mărunte — devine primul doc din `service_pages` (pattern „Service Page Factory" din Audit/Faza B: fiecare serviciu = un doc de pagină) |
| `landing_presets` | 3 | nu e content, e feature-flags → se mută la `settings` namespace "landing" (în 2.2) |

### Model țintă
- `site_content` (existent): banner, hero overrides, chei libere — global site.
- `service_pages`: `{slug: "design-interior", seo, hero, benefits, faq, portfolio..., active, tenant_id}` — interior_design_content migrează 1:1, iar Design Exterior/Renovări (Faza B) se nasc direct aici.

**Efort:** 1 zi · **Risc:** MEDIU (pagina publică /design-interior e live și generează lead-uri — se testează E2E după) · **Rollback:** legacy intact.

---

## ORDINEA PROPUSĂ & PLANUL DE EXECUȚIE (fiecare pas = raport + STOP)
| Pas | Ce | Efort | Risc | Gate de aprobare |
|---|---|---|---|---|
| **2.1** | Leads 5→1 + triage universal | ~1 zi | SCĂZUT | aprobare acum |
| **2.2** | Config 4→1 cu fallback façade | 1,5-2 zile | MEDIU | raport după 2.1 |
| **2.3** | AI Chat 4→1 + GDPR verificat | 1-1,5 zile | SCĂZUT-MEDIU | raport după 2.2 |
| **2.4** | Content: cms retras, service_pages născut | 1 zi | MEDIU | raport după 2.3 |

**Reguli respectate:** nimic nu se șterge (legacy = read-only) · migrări idempotente cu `meta.legacy_id` · endpointuri publice neschimbate (zero impact frontend/SEO) · testing agent după fiecare pas · tenant_id peste tot (D5-C) · Blueprint Compatibility Gate: toate 4 unificările REDUC entropie fără features noi → conforme.

**Decizie cerută:** aprobi ordinea 2.1→2.2→2.3→2.4 și încep cu 2.1 (Leads)?
