"""Client Copilot v1 (Blueprint Phase 4) — Home Assistant: „Care e următoarea acțiune pentru casa ta?"

Rule-based next-best-actions + prețuri orientative din Observatory (fără LLM în v1).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/client/copilot", tags=["client-copilot"])

# Sugestii sezoniere: lună → (categorie Observatory, text)
SEASONAL = {
    3: ("acoperisuri", "Primăvara e momentul verificării acoperișului după iarnă"),
    4: ("amenajari_exterioare", "Sezonul amenajărilor exterioare a început"),
    5: ("hvac", "Pregătește aerul condiționat înainte de caniculă — o igienizare previne defecțiunile"),
    6: ("hvac", "Sezon de vârf pentru climatizare — verifică aerul condiționat înainte de valul de căldură"),
    7: ("hvac", "Caniculă — o revizie a climatizării îți protejează echipamentul"),
    9: ("hvac", "Înainte de sezonul rece: revizia centralei termice e obligatorie anual"),
    10: ("fatade_termoizolatii", "Toamna e ultimul moment bun pentru termoizolații înainte de iarnă"),
    11: ("plumbing", "Protejează instalațiile de îngheț — verifică robineții exteriori"),
}


async def _market_hint(category: str) -> str:
    try:
        from construction.prices import aggregate_prices
        rows = await aggregate_prices(category)
        mids = [r for r in rows if r["experience_level"] == "mid"]
        if mids:
            avg = round(sum(r["price_med"] for r in mids) / len(mids))
            return f" (orientativ ~{avg} lei/{mids[0]['unit']} pe piață)"
    except Exception:  # noqa: BLE001
        pass
    return ""


@router.get("")
async def client_copilot(user=Depends(require_role("client"))):
    cid = str(user.get("id") or user.get("_id"))
    actions = []

    properties = await db.properties.find({"owner_id": cid}, {"name": 1, "created_at": 1}).to_list(50)
    my_requests = await db.requests.find(
        {"client_id": cid}, {"status": 1, "category": 1, "specialist_id": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(200)

    open_reqs = [r for r in my_requests if r.get("status") == "open"]
    active = [r for r in my_requests if r.get("status") in ("accepted", "in_progress")]

    # 1. Cerere deschisă veche fără specialist
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    stale = [r for r in open_reqs if not r.get("specialist_id") and str(r.get("created_at") or "") < week_ago]
    if stale:
        actions.append({"kind": "stale_request", "priority": 1,
                        "text": f"Cererea ta «{stale[0].get('category', 'lucrare')}» așteaptă de peste 7 zile — reformulează descrierea sau ajustează bugetul ca să atragi oferte.",
                        "cta": "jobs"})

    # 2. Lucrări active — urmărire
    if active:
        actions.append({"kind": "active_job", "priority": 2,
                        "text": f"Ai {len(active)} {'lucrare activă' if len(active) == 1 else 'lucrări active'} — verifică progresul și comunică cu specialistul.",
                        "cta": "jobs"})

    # 3. Fără proprietate — onboarding
    if not properties:
        actions.append({"kind": "add_property", "priority": 1,
                        "text": "Adaugă prima ta proprietate — Copilotul îți va urmări întreținerea și îți va aminti reviziile importante.",
                        "cta": "property"})

    # 4. Sugestie sezonieră cu preț de piață (doar dacă nu are deja cerere pe categoria respectivă)
    month = datetime.now(timezone.utc).month
    seasonal = SEASONAL.get(month)
    if seasonal and properties:
        cat, text = seasonal
        has_open_on_cat = any(r.get("category") == cat and r.get("status") in ("open", "accepted", "in_progress") for r in my_requests)
        if not has_open_on_cat:
            hint = await _market_hint(cat)
            actions.append({"kind": "seasonal", "priority": 3, "text": f"{text}{hint}.", "cta": "request", "category": cat})

    # 5. Nicio activitate — reactivare blândă
    if not actions:
        actions.append({"kind": "explore", "priority": 4,
                        "text": "Totul e în regulă cu casa ta. Când apare o nevoie, solicită oferte gratuite de la specialiști verificați.",
                        "cta": "request"})

    actions.sort(key=lambda a: a["priority"])
    return {
        "properties_count": len(properties),
        "open_requests": len(open_reqs),
        "active_jobs": len(active),
        "actions": actions[:3],
    }


SUMMARY_CACHE_HOURS = 12


@router.get("/summary")
async def copilot_summary(force: bool = False, user=Depends(require_role("client"))):
    """Rezumat AI (Claude) personalizat pentru casa clientului — cache 12h per user."""
    cid = str(user.get("id") or user.get("_id"))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=SUMMARY_CACHE_HOURS)).isoformat()
    if not force:
        cached = await db.client_copilot_cache.find_one({"client_id": cid, "generated_at": {"$gte": cutoff}}, {"_id": 0})
        if cached:
            return {"summary": cached["summary"], "generated_at": cached["generated_at"], "cached": True}

    properties = await db.properties.find({"owner_id": cid}, {"name": 1, "type": 1, "created_at": 1}).to_list(20)
    reqs = await db.requests.find(
        {"client_id": cid}, {"status": 1, "category": 1, "title": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(30)
    month = datetime.now(timezone.utc).month
    seasonal = SEASONAL.get(month)
    context = {
        "proprietati": [{"nume": p.get("name"), "tip": p.get("type")} for p in properties],
        "cereri_recente": [{"titlu": r.get("title"), "categorie": r.get("category"), "status": r.get("status")} for r in reqs[:10]],
        "luna_curenta": month,
        "sugestie_sezoniera": seasonal[1] if seasonal else None,
    }
    from fastapi import HTTPException
    try:
        from orchestrator.llm import claude_json
        result = await claude_json(
            system=("Ești Copilotul PropManage pentru proprietari de case din România. Primești datele casei unui client "
                    "și livrezi un rezumat scurt, cald și util despre starea proprietății lui și ce merită să facă acum. "
                    "Răspunde STRICT JSON: {\"summary\": \"max 3 propoziții în română, adresare cu tu, concret, fără generalități\"}."),
            prompt=f"Datele clientului:\n{context}\n\nGenerează rezumatul.",
            session_prefix=f"copilot-{cid[:8]}",
        )
        summary = str(result.get("summary") or "").strip()
        if not summary:
            raise ValueError("Rezumat gol")
    except Exception:  # noqa: BLE001
        raise HTTPException(503, "Rezumatul AI e temporar indisponibil — reîncearcă în câteva minute.")

    now = datetime.now(timezone.utc).isoformat()
    await db.client_copilot_cache.update_one(
        {"client_id": cid},
        {"$set": {"client_id": cid, "summary": summary, "generated_at": now}},
        upsert=True,
    )
    return {"summary": summary, "generated_at": now, "cached": False}
