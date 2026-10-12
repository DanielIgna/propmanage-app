---
name: propmanage-ssr
description: How PropManage server-renders public pages with Next.js App Router + the existing React Router SPA (SsrShell, server data, SEO metadata, hydration rules). Use when adding/changing a public page, SEO metadata or sitemap-related frontend code. Invoke as /propmanage-ssr <route> to verify a page.
---

# SSR în PropManage

## Cum e construit
- SPA (React Router, `src/App.js`) rulează client-only din `app/[...slug]/` (catch-all).
- Pagini SSR (per request, `export const dynamic = "force-dynamic"`): `app/page.jsx` (/), `app/design-interior/**`, `app/imobile-verificate/**`, `app/{de-ce-noi,trust,privacy,terms,cookies}` (prin `app/public-pages.jsx`).
- `app/ssr-shell.jsx`: provideri (Theme, DesignTokens, I18n cu `initialCms`, Auth) + router React Router cu `location` fix și navigare predată lui Next. `ServerRenderedContext` = true → hook-urile sar peste fetch-uri duplicate.
- `app/server-data.js`: `getCms()`, `getBackendJson(path)`, `fetchBackend(path)` (status 0 = backend indisponibil).
- `app/seo.js` → `metadataForPath(slug)`: Page Registry, canonical propriu, `noindex` pentru zone private, `/pricing`, servicii dezactivate (`GATED_SERVICES`).

## Pagină nouă SSR
1. Rută `app/<ruta>/page.jsx`: `generateMetadata` → `metadataForPath([...])`; fetch date pe server.
2. Componentă client: `<SsrShell path="/ruta" cms={cms}>` + view-ul existent cu prop `initial…` (view-ul folosește `useState(initial…)` și sare peste fetch-ul inițial).
3. Fără `window`/`localStorage`/`sessionStorage` în render (doar în efecte; `useSessionFlag` pentru sessionStorage). Module care ating `window` la import (Leaflet `PmMap`) → `next/dynamic` cu `ssr:false`.
4. Pagini cu login obligatoriu sau servicii oprite: rămân în SPA + `noindex` în `seo.js`.

## Verificare (/propmanage-ssr <ruta>)
```bash
curl -s localhost:3000<ruta> -o /tmp/p.html && python3 -c "import re,html;s=open('/tmp/p.html').read();b=re.sub(r'<script[\s\S]*?</script>','',s[s.find('<body'):]);t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',b)));print(len(t),'chars');print(re.findall(r'<title>[^<]*|name=\"robots\" content=\"[^\"]*|rel=\"canonical\" href=\"[^\"]*',s)[:3])"
```
Apoi în browser: consola fără erori de hidratare (`read_console_messages` cu pattern `ydrat|did not match`).
