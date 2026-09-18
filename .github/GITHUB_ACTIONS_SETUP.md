# GitHub Actions Setup

## Mirror propmanage-online → propmanage-app

`propmanage-online` este sursa de adevăr. Workflow-ul `.github/workflows/mirror-to-app.yml` copiază automat toate branch-urile și tag-urile spre `DanielIgna/propmanage-app` la fiecare push (și manual, din tab-ul Actions).

Nu șterge branch-uri care există doar pe `propmanage-app` (de exemplu `chore/local-dev-setup` rămâne acolo până îl ștergi tu).

### Secret obligatoriu

`GITHUB_TOKEN` nu poate scrie într-un alt repo. Pe **propmanage-online** trebuie secretul `MIRROR_TOKEN`.

1. Creează un fine-grained PAT: <https://github.com/settings/personal-access-tokens/new>
   - Resource owner: `DanielIgna`
   - Repository access: **Only select repositories** → `propmanage-app` (nu `propmanage-online`)
   - Repository permissions:
     - **Contents: Read and write**
     - **Workflows: Read and write** (obligatoriu — push-ul copiază fișiere `.github/workflows`)
     - **Metadata: Read** (se activează singur)
   - Expiration: cât vrei (recomandat 1 an, apoi reînnoiești)
2. Copiază token-ul.
3. În **propmanage-online** → Settings → Secrets and variables → Actions → New repository secret:
   - Name: `MIRROR_TOKEN`
   - Value: token-ul de la pasul 2
4. Push workflow-ul pe `main` în `propmanage-online` (remote `emergent`).
5. Rulează o dată **Actions → Mirror to propmanage-app → Run workflow** ca să verifici.

Dacă PAT-ul există deja: **Settings → Developer settings → Fine-grained tokens → tokenul tău → Edit** și adaugă `propmanage-app` + permisiunile de mai sus. Nu trebuie secret nou dacă e același token.

### 403 `Permission to propmanage-app.git denied to DanielIgna`

Token-ul e valid, dar n-are write pe destinație. Cauze uzuale:
- PAT-ul e legat de `propmanage-online` în loc de `propmanage-app`
- Contents e doar **Read**, nu **Read and write**
- lipsește **Workflows: Read and write**

După corectare: Actions → job-ul eșuat → **Re-run jobs**.

După asta, fiecare `git push` pe `propmanage-online` actualizează și `propmanage-app`.

---

# Smoke Test Workflow

Acest fișier explică cum activezi smoke test-ul automat în GitHub după ce conectezi repo-ul cu "Save to GitHub".

## 🚀 Pași rapizi (3 minute)

### 1. Push codul în GitHub
Folosește butonul **"Save to GitHub"** din interfața Emergent ca să sincronizezi `/app/.github/workflows/smoke-test.yml` cu repo-ul tău GitHub.

### 2. Configurează variabilele în repo
Mergi la **GitHub repo → Settings → Secrets and variables → Actions**:

**Variables** (Variables tab — publice, nu sensibile):
| Nume | Valoare | Default dacă lipsește |
|---|---|---|
| `SMOKE_BASE_URL` | `https://phased-document.preview.emergentagent.com` | `https://phased-document.preview.emergentagent.com` |
| `SMOKE_ADMIN_EMAIL` | `admin@propmanage.io` | `admin@propmanage.io` |

**Secrets** (Secrets tab — criptat):
| Nume | Valoare |
|---|---|
| `SMOKE_ADMIN_PASSWORD` | `Admin123!` (parola admin demo) |

> ⚠️ Pentru producție, NU stoca aici parola admin reală. Folosește un cont demo separat sau cere echipei Emergent să-ți creeze un cont read-only de smoke-testing.

### 3. Activează workflow-ul
GitHub Actions activează automat workflow-ul pe baza fișierului `.github/workflows/smoke-test.yml`. Verifică în tab-ul **Actions** după primul push.

### 4. Actualizează badge-ul în README
În `README.md`, înlocuiește `USER/REPO` cu numele tău real de repo (ex: `vlad/propmanage`):

```diff
- [![Dashboard Smoke Test](https://github.com/USER/REPO/actions/...
+ [![Dashboard Smoke Test](https://github.com/vlad/propmanage/actions/...
```

## 🔁 Ce face workflow-ul

Triggers:
- Fiecare **Pull Request** spre `main`/`master`
- Fiecare **push direct** în `main`/`master`
- **Manual** (tab Actions → Run workflow)

Pași:
1. Checkout cod
2. Setup Python 3.11 + cache pip
3. Install Playwright + Chromium (~30s)
4. Run `python backend/tests/test_dashboards_smoke.py` (~90s)
5. Upload log-uri ca artifact dacă eșuează (debugging)

Timeout: 5 minute (safe margin).

## 🛡️ Beneficii

- **Blochează merge-ul** în main dacă cad teste → bug-uri ca iter66 (TierProgressWidget undefined) **NU mai ajung niciodată** în producție
- **Badge verde în README** → arată profesionalism investitorilor + dev-eri
- **Istoric vizibil** în tab-ul Actions → poți vedea când și de ce a căzut
- **Zero cost** pe planul GitHub Free (2000 min/lună incluse, smoke test = ~3 min)

## ❓ Troubleshooting

**Q: Smoke test cade cu "Failed to login as admin"**  
A: Verifică `SMOKE_ADMIN_PASSWORD` secret e setat corect.

**Q: Toate testele cad cu "Failed to impersonate"**  
A: Probabil endpoint-ul `/api/admin/impersonate` necesită un reason mai lung sau JWT. Verifică log-urile din artifacts.

**Q: Pot rula contra producției?**  
A: Da — pune `SMOKE_BASE_URL=https://propmanage.ro` în Variables. Recomandare: rulează numai pe `workflow_dispatch` (manual) ca să nu spamezi producția la fiecare PR.

**Q: Pot rula doar specifice profile?**  
A: Editează `PROFILES` în `test_dashboards_smoke.py`. Filtrare prin env vars e enhancement viitor.
