---
name: propmanage
description: Use for ANY change in the PropManage project (Next.js frontend on Cloudflare Workers, FastAPI backend on Railway, Supabase Postgres/Auth/Storage). Holds the project's architecture, run commands and working rules.
---

# PropManage — reguli de lucru

## Stil răspuns
- Română, scurt, la subiect. Doar: ce s-a schimbat, ce s-a testat, ce rămâne.
- Fără recapitulări lungi. Nu pomeni site-ul live (propmanage.ro / Emergent) decât dacă utilizatorul întreabă.
- NU face `git commit`/`push`/deploy fără să întrebi întâi.
- **`DanielIgna/propmanage-online` (GitHub) e DOAR CITIRE**: codul vechi Mongo + Emergent din producție rămâne exact cum e. Nu adăuga remote, nu face push/branch/PR, nu lega Railway/Cloudflare/Supabase de el, nu schimba DNS-ul propmanage.ro. Lucrul nou merge doar în `DanielIgna/propmanage-app` (remote-ul `origin` al acestui folder — numele folderului e înșelător). Funcționalități din propmanage-online se portează citind de acolo și scriind doar aici.

## Arhitectură
- **Frontend** `frontend/` — Next.js 16.3 (App Router) + React 19, Yarn 1.22. Dev: `cd frontend && yarn dev` (port 3000; `/api` și `/uploads` → `BACKEND_URL` prin `rewrites`, implicit `localhost:8001`).
  - Aplicația (React Router, `src/App.js`, ecrane în `src/views/`) rulează client-only din `app/[...slug]` (catch-all).
  - Pagini publice randate pe server (SSR, per request): `/` (`app/page.jsx`), `/design-interior/**`, `/imobile-verificate` + `/[id]`, `/de-ce-noi`, `/trust`, `/privacy`, `/terms`, `/cookies`. Folosesc `app/ssr-shell.jsx` (provideri + router React Router care predă navigarea către Next) și `app/server-data.js` (fetch backend pe server).
  - Pagină nouă SSR: rută în `app/`, componentă client cu `SsrShell path=…`, date inițiale ca prop (`initial…`), fără acces la `window`/`localStorage` în render (doar în efecte); module care ating `window` la import (Leaflet) → `next/dynamic` cu `ssr:false`.
  - Metadata pe server pentru toate rutele: `app/seo.js` (Page Registry `/api/public/pages/{key}`, canonical propriu, `noindex` pe zone private, pe `/pricing` și pe servicii dezactivate).
  - Variabile publice: `NEXT_PUBLIC_*` (`NEXT_PUBLIC_BACKEND_URL` gol = same-origin).
  - Deploy: Cloudflare Workers prin OpenNext — `cd frontend && BACKEND_URL=<railway> yarn deploy` (worker `propmanage-app`, https://propmanage-app.danieligna1.workers.dev). Test local runtime Workers: `npx opennextjs-cloudflare build && npx opennextjs-cloudflare preview`.
  - Next fixat la 16.3.x până OpenNext suportă 16.4 (eroare `preview-props.json`).
- **Backend** `backend/` — FastAPI. Local: `./venv/bin/uvicorn server:app --port 8001`. Railway (vezi ID-uri mai jos): `backend/Dockerfile`, build din rădăcina repo-ului (include `memory/` + `docs/` pentru Knowledge Center).
- **Supabase** (proiect `propmanage`, ref `nvkcxcquksdtodgikznc`):
  - Date: schema `app` (NU expusă în Data API), o tabelă JSONB per colecție. Codul folosește API-ul Motor/Mongo prin `backend/pgmongo.py` (SQL prefiltrează, mongomock aplică semantica Mongo). `db.py` = doar Postgres (`SUPABASE_DB_URL`, `PG_SCHEMA`).
  - Colecție nouă → creată automat la primul insert; indexuri unice prin `create_index(..., unique=True)`.
  - Fișiere: `storage_client.py` → bucket privat `propmanage-files`.
  - Auth: Supabase Auth (`supabase_auth.py`); roluri DOAR din `users.role` (niciodată din `user_metadata`); `ADMIN_EMAILS` decide adminii.
  - Migrări SQL în `supabase/migrations/`. Orice tabel nou în `public`: RLS + politici explicite. Cheia secretă NICIODATĂ în frontend.
- **AI / plăți**: `llm_chat.py` (Anthropic `ANTHROPIC_API_KEY`, Gemini `GEMINI_API_KEY` pentru imagini), `stripe_checkout.py` (SDK oficial; webhook cere `STRIPE_WEBHOOK_SECRET`).
- **Securitate**: CORS/CSRF doar `propmanage.ro/.io`, localhost și originile exacte din `CORS_ORIGINS` (fără `*.workers.dev`/`*.pages.dev`).

## Economie de tokeni (obligatoriu)
- **Nu re-explora**: arhitectura, ID-urile și comenzile de mai jos sunt sursa de adevăr; citește doar fișierele pe care le modifici.
- Caută țintit (`grep -n`, `rg -l`, `sed -n 'a,bp'`); nu `cat` fișiere mari (`App.js`, `routes/*.py` au mii de linii), nu liste lungi de `ls`.
- Limitează ieșirile: `| head`, `| tail -n 20`, `--stat`, `-q`; nu afișa loguri complete de build/test — doar erorile (`grep -E "error|Error|FAIL"`).
- Nu rula suita completă de teste sau build-uri lungi fără motiv; rulează doar testul/pagina afectată. Build OpenNext + preview doar înainte de deploy.
- Fără verificări repetate ale aceluiași lucru, fără polling des (Railway build ≈ 3–5 min, verifică o dată la final).
- Lucru independent → apeluri de tool-uri în paralel; răspunsuri finale scurte (tabel mic sau 3–6 bullet-uri).
- Nu porni sub-agenți și nu încărca skill-uri/documentație externă dacă informația e deja aici.

## ID-uri și resurse (nu le mai căuta)
- GitHub: `DanielIgna/propmanage-app` — `main` (sursa de deploy), branch de lucru `3D`. Read-only: `DanielIgna/propmanage-online`.
- Supabase: proiect `nvkcxcquksdtodgikznc` (eu-west-1), schema date `app`, bucket `propmanage-files`.
- Railway: proiect `dcd46bb6-3cb7-4269-af0a-439fcbbf138f`, serviciu `backend` `9b2b3bff-4e08-4c10-bd58-b6d265e75a1c`, env `production` `c0303ffe-040b-4684-93fe-8f7db568e4e3`; URL `https://backend-production-e5b7d.up.railway.app`; deploy automat din `main` (doar la schimbări în `backend/`, `memory/`, `docs/`).
- Cloudflare: worker `propmanage-app` → `https://propmanage-app.danieligna1.workers.dev` (deploy manual: `cd frontend && BACKEND_URL=https://backend-production-e5b7d.up.railway.app yarn deploy`).
- Local: backend `cd backend && ./venv/bin/uvicorn server:app --port 8001`; frontend `cd frontend && yarn dev` (port 3000). Mongo local e oprit (nu mai e folosit).

## Verificare după modificări
1. Backend: `./venv/bin/python -c "import server"` + request real pe 8001.
2. Frontend: pagina în preview, consola fără erori de hidratare; pentru SSR verifică textul din HTML (`curl`).
3. Înainte de deploy: build + preview OpenNext (runtime Workers).
4. Login demo: conturile din `backend/seed.py` (doar local).
