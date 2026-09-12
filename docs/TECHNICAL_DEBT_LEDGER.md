# 🧾 TECHNICAL DEBT LEDGER — PropManage
**Directiva 073 · Registru de investiții, nu listă de probleme · Început: Iulie 2026**

| ID | Componentă | Scurtătura luată | Motiv | Risc | Impact business | Efort fix | Prioritate | Deadline recomandat |
|---|---|---|---|---|---|---|---|---|
| TD-01 | VerifiedEstateAdmin (mark-sold) | `window.prompt` pentru prețul de vânzare, nu modal shadcn | Viteză Faza A | UX rudimentar pe mobil admin | Scăzut (uz intern, rar) | 2h | P3 | La Faza B |
| TD-02 | Verified Estate seeds | 2 listinguri demo publicate coexistă cu date reale | Pagina publică să nu fie goală pre-lansare | Confuzie clienți reali la lansare | MEDIU la lansare comercială | 1h (script unpublish) | **P1 — înainte de primul client real** | La activarea Stripe LIVE |
| TD-03 | Audit workflow (Gate 3) | `recommendations_total/accepted` = câmpuri manuale, fără entitate raport audit | Decizie Board (Faza B amânată — D-003) | Eroare umană, nescalabil >10 imobile/lună | MEDIU la scalare | 20–25 credite | P2 (=Faza B) | După prima tranzacție |
| TD-04 | Facturare | e-Factura RO inexistentă | Nefezabil pre-revenue | Neconformitate legală la volum B2B | RIDICAT la volum | 15–20 credite | **P1 legal** | Înainte de >5 facturi B2B/lună |
| TD-05 | first_revenue.py | `started_at` reparsat din ISO la fiecare call; milestone first_invoice hardcodat `done=False` | Simplitate | Neglijabil | Neglijabil | 30 min | P4 | Oportunist |
| TD-06 | Email delivery | Fallback pe console când Resend e blocat | DNS extern nefixat | Emailuri de confirmare nelivrate în producție | RIDICAT (extern) | 0 dev — acțiune Founder DNS | **P0 extern** | Imediat (Founder) |
| TD-07 | lead_magnets.py | Fără rate limiting pe POST /api/public/lead-magnet (endpoint public, trigger de email) | Viteză G1 | Spam/abuz posibil la trafic mare | Scăzut acum, MEDIU la trafic | 2h (slowapi per IP) | P2 | La primele semne de abuz sau >100 leads/zi |

## Bilanț per Sprint
| Sprint | Debt nou | Debt rezolvat | Total activ | Trend |
|---|---|---|---|---|
| Faza A (Iul 2026) | +3 (TD-01, TD-02, TD-05) | 0 | 6 | baseline |

**Regulă de alarmă (D073)**: dacă un debt amenință securitatea / venitul / performanța / scalabilitatea / încrederea → acțiune imediată, indiferent de sprint. Actual: TD-06 și TD-02 sunt legate direct de venit → ambele au owner și deadline.
