---
name: propmanage-deploy
description: Deploy and verify PropManage — Cloudflare Workers frontend (OpenNext) and Railway backend. Invoke as /propmanage-deploy (asks before deploying). Use for build failures, env vars, Railway/Cloudflare config.
---

# Deploy PropManage (întreabă înainte de deploy)

## Frontend (Cloudflare Worker `propmanage-app`)
```bash
cd frontend && BACKEND_URL=https://backend-production-e5b7d.up.railway.app npx opennextjs-cloudflare build 2>&1 | tail -3
npx opennextjs-cloudflare preview --port 8788   # verifică / /login /api/health (200, fără wrangler:error)
BACKEND_URL=https://backend-production-e5b7d.up.railway.app yarn deploy 2>&1 | grep -E "Deployed|ERROR|Version ID"
```
- Next fixat la 16.3.x (OpenNext nu suportă încă 16.4: eroare `preview-props.json`). `wrangler login` dacă nu e autentificat.
- Fără `_redirects` în `public/` (SPA fallback e făcut de worker).

## Backend (Railway)
- Deploy automat la push pe `main`, doar dacă se schimbă `backend/`, `memory/`, `docs/` sau `.dockerignore`. Build: `backend/Dockerfile` din rădăcina repo-ului.
- Verificare: `list-deployments` (o singură dată, la final) și `curl -s -o /dev/null -w "%{http_code}" https://backend-production-e5b7d.up.railway.app/api/health`.
- Variabile secrete le pune utilizatorul în Railway (Variables → Raw Editor); tu doar pe cele nesecrete. `CORS_ORIGINS` trebuie să conțină URL-ul worker-ului.
- Pe Railway nu seta `RESEND_API_KEY`/Stripe live fără acordul utilizatorului (joburile programate rulează pe date reale).
