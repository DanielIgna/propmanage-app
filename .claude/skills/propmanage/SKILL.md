---
name: propmanage
description: Core rules, architecture map and resource IDs for the PropManage project (Next.js on Cloudflare Workers, FastAPI on Railway, Supabase). Load for any PropManage code task; load propmanage-ssr / propmanage-db / propmanage-deploy only when that area is touched.
---

# PropManage — bază

## Reguli
- Română, scurt: ce s-a schimbat, ce s-a testat, ce rămâne. Nu pomeni site-ul live decât dacă ești întrebat.
- Fără commit/push/deploy fără să întrebi.

## Economie de tokeni
- Nu re-explora: harta și ID-urile de aici sunt sursa de adevăr; citește doar fișierele pe care le modifici.
- Căutări țintite (`rg -n`, `sed -n 'a,bp'`); nu citi integral `src/App.js`, `routes/*.py` (mii de linii).
- Ieșiri limitate (`| head`, `| tail -n 20`, doar erori); fără suite complete de teste, fără polling repetat.
- Apeluri de tool-uri independente în paralel; răspuns final 3–6 bullet-uri.

## Hartă
| Zonă | Unde | Skill detaliat |
|---|---|---|
| Frontend Next.js 16.3 (App Router), SPA React Router în `app/[...slug]`, ecrane `src/views/` | `frontend/` | `propmanage-ssr` |
| Backend FastAPI, rute `backend/routes/`, auth `deps.py`/`supabase_auth.py` | `backend/` | — |
| Date: Supabase Postgres (schema `app`, JSONB) prin `backend/pgmongo.py`; fișiere Supabase Storage | `backend/db.py`, `storage_client.py` | `propmanage-db` |
| AI `llm_chat.py` (Anthropic/Gemini), plăți `stripe_checkout.py` | `backend/` | — |
| Deploy Railway + Cloudflare | `backend/Dockerfile`, `frontend/wrangler.jsonc` | `propmanage-deploy` |
| Knowledge Center: fișiere `memory/`, `docs/` | `routes/knowledge_center.py` | — |

## ID-uri și resurse
- GitHub `DanielIgna/propmanage-app`: `main` = sursa de deploy, branch de lucru `3D`.
- Supabase `nvkcxcquksdtodgikznc` (eu-west-1): schema `app`, bucket `propmanage-files`.
- Railway: proiect `dcd46bb6-3cb7-4269-af0a-439fcbbf138f`, serviciu `9b2b3bff-4e08-4c10-bd58-b6d265e75a1c`, env `c0303ffe-040b-4684-93fe-8f7db568e4e3`, URL `https://backend-production-e5b7d.up.railway.app`.
- Cloudflare: worker `propmanage-app` → `https://propmanage-app.danieligna1.workers.dev`.
- Local: backend `cd backend && ./venv/bin/python -m uvicorn server:app --port 8001`; frontend `cd frontend && yarn dev` (3000). Conturi demo: `backend/seed.py` (doar local). Mongo local oprit.
