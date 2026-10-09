---
name: propmanage
description: Use for ANY change in the PropManage project (frontend React/CRA, backend FastAPI+Mongo, Supabase auth/DB, Cloudflare worker). Holds the project's architecture, run commands and working rules.
---

# PropManage — reguli de lucru

## Stil răspuns
- Română, scurt, la subiect. Doar: ce s-a schimbat, ce s-a testat, ce rămâne.
- Fără recapitulări lungi.
- NU face `git commit`/`push` fără să întrebi întâi.

## Structură
- `frontend/` — **Next.js 16.3 (App Router)** + React 19, Yarn **1.22** (`cd frontend && yarn dev`, port 3000). Aplicația existentă (React Router, `src/App.js`, ecrane în `src/views/`) rulează client-only din `app/[[...slug]]`; paginile noi/SEO se fac ca rute App Router în `app/`. Variabile publice: `NEXT_PUBLIC_*`. `/api` și `/uploads` → backend prin `rewrites` (`BACKEND_URL`, implicit localhost:8001).
- Deploy frontend: Cloudflare Workers prin OpenNext — `cd frontend && BACKEND_URL=<railway> yarn deploy` (worker `propmanage-app`). Next fixat la 16.3.x până OpenNext suportă 16.4 (eroare `preview-props.json`).
- `backend/` — FastAPI + MongoDB (motor), `./venv/bin/uvicorn server:app --port 8001`. Rute în `routes/`, dependențe auth în `deps.py`.
- Backend pe Railway (Dockerfile `backend/Dockerfile`, build din rădăcina repo-ului, include `memory/` + `docs/`).

## Supabase
- Proiect: `propmanage` (ref `nvkcxcquksdtodgikznc`). Chei în `frontend/.env` (`REACT_APP_SUPABASE_*`, doar publishable) și `backend/.env` (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`).
- Clienți: `frontend/src/lib/supabase.js`, `backend/supabase_client.py` (`get_supabase()`).
- Orice tabel nou în `public`: RLS activat + politici explicite; rulează `get_advisors` după DDL.
- Cheia secretă NICIODATĂ în frontend.

## Migrare Mongo → Supabase (în curs, branch `feat/supabase-migration`)
- Plan + inventar: `docs/migration/collections.md`. Decizii: arhitectura A (frontend → backend → DB), păstrăm loguri + conturi demo.
- Schema `app` (NU expusă în Data API): o tabelă JSONB per colecție (`id` = Mongo `_id`, `data jsonb`, GIN `jsonb_path_ops`), RLS fără politici. Colecție nouă → `select app.create_collection('nume')` într-o migrare.
- Backend pe Supabase: `DB_BACKEND=postgres` → `backend/pgmongo.py` (fațadă Motor peste JSONB; SQL prefiltrează, mongomock aplică semantica Mongo). Test diferențial: `supabase_migration/verify_adapter.py`. Import date: `supabase_migration/import_mongo_dump.py`.
- Fișiere: `STORAGE_BACKEND=supabase` → `storage_client.py` scrie în bucket privat `propmanage-files` (aceleași căi `propmanage/...`). Copiere din Emergent: `supabase_migration/copy_objects.py`.
- Migrări SQL în `supabase/migrations/` (aplicate și prin MCP `apply_migration`).

## Autentificare (Supabase Auth + profil Mongo)
- `backend/supabase_auth.py` — verificare JWT (JWKS, ES256), admin API GoTrue, sesiuni.
- Login/register (`routes/auth.py`): parola verificată pe hash-ul bcrypt din Mongo (sursa de adevăr), apoi `_start_session` sincronizează userul în Supabase (migrare leneșă) și întoarce `supabase_session`.
- Mongo `users.supabase_id` leagă cele două (index unic sparse).
- `deps.get_current_user`: încearcă cookie `access_token`, apoi `Authorization: Bearer`; acceptă JWT Supabase și JWT legacy HS256 (impersonare, Google OAuth, fallback).
- Frontend `src/auth.js`: `setSession` după login, interceptor axios adaugă Bearer, `TOKEN_REFRESHED` → `POST /api/auth/supabase/session` (actualizează cookie-ul).
- Schimbare parolă oriunde → actualizează `password_hash` în Mongo; pentru sincronizare imediată apelează `supabase_auth.set_password(supabase_id, pw)`.
- Google prin Supabase: buton în `pages/Auth.jsx` (activ dacă `REACT_APP_SUPABASE_GOOGLE=true`) → `signInWithOAuth` (PKCE) → `/auth/callback?sb=1` → `exchangeCodeForSession` → `POST /api/auth/supabase/oauth` (leagă/creează userul Mongo prin `_upsert_google_user`). Fluxurile Google direct/Emergent rămân ca fallback.
- Rol/permisiuni: DOAR din Mongo (`require_role`), niciodată din `user_metadata` Supabase.

## Verificare după modificări
1. Backend: `./venv/bin/python -c "import routes.auth"` + request real pe 8001.
2. Frontend: deschide pagina în preview, verifică consola.
3. Login demo: conturile din `backend/seed.py`.

## De curățat înainte de producție
- Ruta `/test-supabase` (`frontend/src/pages/SupabaseTestPage.jsx`) și tabelul `public.test_users`.
