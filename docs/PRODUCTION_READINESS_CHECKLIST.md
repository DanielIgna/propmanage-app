# PRODUCTION READINESS CHECKLIST — EO-026 Phase 1 (Foundation)
**Data:** 27 Iunie 2026 · **Producție:** https://propmanage.ro · **Clasa dovezilor:** Measured unde e specificat

Legendă: ✅ verificat · 🟡 parțial / necesită acțiune · 🔴 blocat pe Fondator

| # | Item | Status | Dovadă / Acțiune |
|---|---|---|---|
| 1 | **Stripe LIVE** | 🔴 FONDATOR | Claim cont Stripe LIVE (blocker din Iulie). Codul e gata: webhook + poll fallback (`verified_estate.py::mark_order_paid`). |
| 2 | **Production Email (Resend)** | 🔴 FONDATOR | DNS Resend pe Rackhost neverificat. Gate-ul de siguranță există: emailurile intră în coadă și se trimit automat când DNS-ul e reparat. |
| 3 | **DNS / Domain verification** | 🔴 FONDATOR | propmanage.ro live; de verificat DNS email (SPF/DKIM via Resend). |
| 4 | **HTTPS** | ✅ | Producția servește prin HTTPS (Emergent deploy + propmanage.ro). |
| 5 | **Monitoring** | ✅ | `healthcheck_service.py` — probe Mongo / LLM / email / Stripe / OAuth / VAPID + `integration_health` + Enterprise Health Engine (11 domenii, snapshot zilnic). |
| 6 | **Error logging** | ✅ | Supervisor logs backend + `demo_activity_logs` (status 4xx/5xx) + Audit Sentinel (scan orar: rate_spike, error_burst, scope_probe). |
| 7 | **Backups** | ✅ (platformă) | MongoDB gestionat de platforma Emergent; snapshot-uri settings zilnice (`take_auto_snapshot`, cron 04:00). |
| 8 | **Security** | ✅ | CX-3 gate 100%: owner endpoints 401/403, zero PII în payload public, privacy server-side. RBAC validat pe toate modulele admin (istoric 130+ iterații teste). |
| 9 | **Rate limiting** | ✅ NOU | `rate_limit.py` — 120 req/min per IP pe `/api/public/*`, `/api/p/*`, `/api/track`, `/api/go/*` (configurabil `PUBLIC_RATE_LIMIT_PER_MIN`). TD-07 închis. |
| 10 | **Privacy / GDPR** | ✅ | Consent la register (terms+privacy), cookie banner, Trust Center, account-export + account-delete endpoints, analytics first-party fără cookies de tracking, IP doar hash trunchiat. |
| 11 | **SEO** | ✅ | Sitemap, ghiduri cu JSON-LD FAQ, pașaport cu canonical + JSON-LD Accommodation, title/description dinamice. |
| 12 | **Open Graph** | ✅ | `GET /api/p/{slug}` servește OG pentru boți (FB/WhatsApp/LinkedIn) + fallback `og-passport.jpg`. Testat cu 3 UA-uri de bot (iteration_135). |
| 13 | **Performance** | ✅ Measured | Payload public pașaport ~110ms, QR ~100ms (cache 24h), OG ~93ms — prin URL extern. |
| 14 | **Mobile** | ✅ | Funnel-ul complet auditat la 390px în CX-1/2/3 (scoruri ≥90). |
| 15 | **Analytics** | ✅ NOU | Passport Analytics complet (views/QR/share/sursă/țară/device/browser/timp/bounce/conversii) + tracker first-party existent + Beta Cockpit `/admin/beta-cockpit`. |
| 16 | **Date demo în producție** | 🟡 ACȚIUNE | (a) La deploy: setează env `SEED_DEMO_DATA` diferit de `true` în producție → seeds demo NU se mai recreează. (b) Rulează `POST /api/admin/beta/purge-demo {master_code, dry_run:true}` → verifică counts → repetă cu `dry_run:false` pentru curățare. |

## Acțiuni Fondator (singurele blocante pentru beta)
1. **Stripe LIVE** — claim cont (din chat-ul Emergent / Stripe dashboard).
2. **Resend DNS** — adaugă înregistrările SPF/DKIM în Rackhost → verifică domeniul în Resend.
3. **Redeploy** cu `SEED_DEMO_DATA` nesetat (sau ≠true) în producție + rulează purge-demo (pasul 16).
4. **Invită 10–20 proprietari reali + 5–10 specialiști** (Phase 2 EO-026).

## Ce măsoară platforma automat în beta (Phase 5)
- Beta Cockpit (`/admin/beta-cockpit`): funnel proprietari (cont→proprietate→document→pașaport→share→revenire), funnel specialiști, TTFV median, conversie vizitatori, cereri suport, cele 4 gate-uri de succes EO-026 (80/70/50/50).
- Passport Analytics per proprietate (card „Statistici" în Property Hub) + rollup global.
- Voice of Customer: widget „Feedback beta" în dashboard-urile client/specialist (cele 6 întrebări ale Fondatorului) → vizibil în Beta Cockpit.
