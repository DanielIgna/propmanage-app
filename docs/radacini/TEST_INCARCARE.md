# Rădăcini — test de încărcare (2026-10-26)

Script: `backend/scripts/radacini_load_test.py`. Face doar citiri, fiecare utilizator simulat parcurgând traseul panou → terenuri → piață → comunități → proiecte → composesorate. Backend local (Mac, România) către Supabase eu-west-1 (Irlanda). Latența rețelei locale crește toate valorile. Pe Railway trebuie remăsurat, după ce aflăm regiunea serviciului.

## Rezultate

| Configurare | Utilizatori simultani | Cereri/s | p50 tipic | Erori |
|---|---|---|---|---|
| Actuală: pooler sesiune (5432), pool 5 | 5 | 5,4 | 0,6 s | 0 |
| idem | 20 | 7,2 | 2,4 s (proiecte 5,6 s) | 2 / 710 |
| idem | 50 | 7,1 | 6,1 s (proiecte 14 s) | 10 / 1.760 |
| Pooler sesiune, pool 15 | 20 | 19,9 | 0,9 s | **197 / 710**: `EMAXCONNSESSION`, limită 15 conexiuni **în total** |
| **Pooler tranzacție (6543), pool 15** | 20 | 17,6 | 0,8 s | 0 / 710 |
| **idem** | 50 | **24,3** | 2,0 s (proiecte 4,7 s) | 1 / 1.760 |

## Concluzii
1. **Blocajul e la conexiunile cu baza de date.** Pooler-ul Supabase în mod sesiune (portul 5432) permite **15 conexiuni în total**, pentru toți clienții. Producția (Railway), orice backend local și testele își împart aceleași 15 locuri. Un backend local poate deci încetini sau bloca producția.
2. **Soluția:** pooler-ul în mod tranzacție (portul **6543**). Codul e deja compatibil: `statement_cache_size=0`, iar lock-urile sunt la nivel de tranzacție (`pg_advisory_xact_lock`). Pool-ul se configurează acum cu `PG_POOL_MAX` (implicit 5, comportament neschimbat).
3. **Ruta cea mai lentă:** `/radacini/projects` (de ~2,5 ori mai lentă decât restul). Urmează `/listings` și `/admin/system`. Sunt candidate de optimizare, prin mai puține interogări pe cerere.

## Recomandare pentru producție (decizia fondatorului)
- Pe Railway, în `SUPABASE_DB_URL`, portul `5432` se schimbă în `6543` (același host de pooler) și se adaugă `PG_POOL_MAX=10`.
- Testat local cu ambele variabile. Înainte de schimbarea în producție: un smoke test al PropManage (autentificare, liste, plăți demo), pentru că afectează toată aplicația, nu doar Rădăcini.
- Pentru beta închis (5–15 testeri), și configurarea actuală e suficientă.
