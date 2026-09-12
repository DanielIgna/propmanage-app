"""AI Brain · Explainability Engine (AIB-003).

Explică pagini, componente și procese folosind EXCLUSIV infrastructura existentă:
Discovery/Registry (AIB-001), Context Engine (AIB-002) și ai_core.provider.call_llm
(Emergent LLM Key, deja integrat în platformă). Fără RAG/vector DB/Knowledge Graph.

CONTEXT FIRST: nicio explicație nu se generează înainte de resolve_context (rol, pagină,
modul, permisiuni). Grounding-ul include anatomia REALĂ a paginii (extrasă din sursa
componentei React: secțiuni, butoane, data-testid-uri) — răspunsurile nu pot fi generice.
Cache per (rută, rol, anatomie) în db.ai_brain_explanations — o pagină neschimbată se
explică o singură dată per rol.
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from db import db
from ai_brain import registry
from ai_brain.context import resolve_context

FRONTEND_SRC = Path("/app/frontend/src")

SYSTEM_PROMPT = """Ești AI Brain, ghidul integrat al platformei PropManage (administrare
imobiliară, Digital Twin, House Health, marketplace de specialiști — România).
Explici utilizatorului EXACT unde se află, pe baza datelor reale primite (context + anatomia
paginii). REGULI STRICTE:
- Răspunde DOAR în română, adresare cu «tu».
- Folosește EXCLUSIV informațiile din payload — nu inventa funcționalități, butoane sau pași.
- Adaptează explicația la ROLUL utilizatorului; nu descrie acțiuni la care nu are acces.
- Fii concret și scurt: fără introduceri pompoase, fără «desigur!».
- Format Markdown cu secțiunile cerute în mesaj."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


async def _component_file(component: str) -> Path | None:
    reg = await registry.get("pages", q=component, limit=500)
    for p in reg["data"]:
        if p["name"] == component:
            return FRONTEND_SRC / p["file"]
    return None


def _page_anatomy(src: str) -> dict:
    testids = re.findall(r'data-testid="([^"]+)"', src)
    headings = re.findall(r">\s*([A-ZĂÂÎȘȚ][^<>{}\n]{3,70})\s*<", src)
    buttons = re.findall(r"<button[^>]*>\s*\{?[^<>{}]*?([A-ZĂÂÎȘȚa-zăâîșț][^<>{}\n]{2,50})<", src)
    links = sorted({m for m in re.findall(r'\bto="(/[^"]+)"', src) if "${" not in m})
    return {
        "testids": sorted(set(testids))[:40],
        "headings": list(dict.fromkeys(h.strip() for h in headings))[:30],
        "buttons": list(dict.fromkeys(b.strip() for b in buttons))[:20],
        "outgoing_links": links[:20],
    }


def _anatomy_hash(anatomy: dict) -> str:
    return hashlib.sha1(str(sorted(anatomy.items())).encode(), usedforsecurity=False).hexdigest()[:12]


async def _grounding(user: dict, path: str) -> tuple:
    ctx = await resolve_context(user, path=path)
    component = (ctx["location"].get("route") or {}).get("component")
    src = ""
    if component:
        f = await _component_file(component)
        src = _read(f) if f else ""
    anatomy = _page_anatomy(src) if src else {}
    mods = await registry.get("modules", q=ctx["location"]["module"], limit=5)
    related = mods["data"][:3]
    grounding = {
        "user": {"role": ctx["user"]["role"], "tier": ctx["user"].get("tier"),
                 "experience_tier": ctx["user"].get("experience_tier")},
        "page": {"path": path, "module": ctx["location"]["module"],
                 "component": component, "known_route": ctx["location"]["known_route"]},
        "entity": ctx.get("entity"),
        "permissions": ctx["permissions"],
        "available_actions": ctx["available_actions"][:20],
        "page_anatomy": anatomy,
        "related_modules": related,
        "navigation_trail": ctx["workflow"]["trail"],
    }
    return ctx, grounding, anatomy


def _fallback_explanation(grounding: dict, kind: str) -> str:
    p = grounding["page"]
    parts = [f"## Unde te afli\nEști în modulul **{p['module']}**, pe pagina `{p['path']}`"
             + (f" (componenta {p['component']})." if p["component"] else ".")]
    if grounding["page_anatomy"].get("headings"):
        parts.append("## Secțiuni pe această pagină\n" + "\n".join(f"- {h}" for h in grounding["page_anatomy"]["headings"][:10]))
    if grounding["available_actions"]:
        parts.append("## Ce poți face aici\n" + "\n".join(
            f"- {a['method']} {a['path']}" for a in grounding["available_actions"][:8]))
    parts.append("_Explicația AI detaliată e temporar indisponibilă — aceasta e varianta structurală._")
    return "\n\n".join(parts)


async def _cached(key: str) -> dict | None:
    doc = await db.ai_brain_explanations.find_one({"key": key}, {"_id": 0})
    if doc:
        await db.ai_brain_explanations.update_one({"key": key}, {"$inc": {"hits": 1}})
    return doc


async def _store(key: str, kind: str, path: str, role: str, text: str, model: str, extra: dict = None):
    await db.ai_brain_explanations.update_one(
        {"key": key},
        {"$set": {"key": key, "kind": kind, "path": path, "role": role, "text": text,
                  "model": model, "created_at": _now(), **(extra or {})},
         "$setOnInsert": {"hits": 0}},
        upsert=True)


async def explain_page(user: dict, path: str) -> dict:
    ctx, grounding, anatomy = await _grounding(user, path)
    route_pattern = (ctx["location"].get("route") or {}).get("path") or path
    key = hashlib.sha1(f"page|{route_pattern}|{ctx['user']['role']}|{_anatomy_hash(anatomy)}".encode(), usedforsecurity=False).hexdigest()
    cached = await _cached(key)
    if cached:
        return {"explanation": cached["text"], "cached": True, "model": cached.get("model"),
                "grounded_on": {"module": grounding["page"]["module"], "component": grounding["page"]["component"]}}

    from ai_core.provider import call_llm
    user_msg = (
        "Explică această pagină pentru utilizatorul curent. Structură obligatorie (Markdown, în română):\n"
        "## Ce este această pagină (scopul, cui îi este destinată)\n"
        "## Ce poți face aici (acțiuni concrete pentru rolul tău)\n"
        "## Secțiunile paginii (explică fiecare secțiune/card/buton REAL din page_anatomy)\n"
        "## Legătura cu alte module (doar din related_modules/outgoing_links)\n"
        "## Următorii pași recomandați (2-3, concreți, pe baza acțiunilor disponibile)\n\n"
        f"DATE REALE:\n{grounding}"
    )
    res = await call_llm(SYSTEM_PROMPT, user_msg, session_id=f"explain-{key[:12]}")
    if res.get("error") or not res.get("text"):
        return {"explanation": _fallback_explanation(grounding, "page"), "cached": False,
                "model": "fallback", "grounded_on": {"module": grounding["page"]["module"],
                                                     "component": grounding["page"]["component"]}}
    await _store(key, "page", route_pattern, ctx["user"]["role"], res["text"], res.get("model", ""))
    return {"explanation": res["text"], "cached": False, "model": res.get("model"),
            "grounded_on": {"module": grounding["page"]["module"], "component": grounding["page"]["component"]}}


async def explain_component(user: dict, path: str, component_ref: str) -> dict:
    ctx, grounding, anatomy = await _grounding(user, path)
    ref = component_ref.strip()[:80]
    snippet, found_in = "", None
    comp = (ctx["location"].get("route") or {}).get("component")
    files = []
    if comp:
        f = await _component_file(comp)
        if f:
            files.append(f)
    for f in files + [p for p in (FRONTEND_SRC / "components").glob("*.jsx")]:
        src = _read(f)
        idx = src.find(ref)
        if idx >= 0:
            snippet = src[max(0, idx - 300):idx + 500]
            found_in = str(f.relative_to(FRONTEND_SRC))
            break
    key = hashlib.sha1(f"component|{path}|{ctx['user']['role']}|{ref}".encode(), usedforsecurity=False).hexdigest()
    cached = await _cached(key)
    if cached:
        return {"explanation": cached["text"], "cached": True, "found_in": cached.get("found_in")}

    from ai_core.provider import call_llm
    user_msg = (
        f"Explică componenta «{ref}» de pe pagina {path}. Structură (Markdown, română):\n"
        "## Ce este\n## Ce face\n## Când o folosești\n## Ce procese afectează\n## Permisiuni necesare\n\n"
        f"CONTEXT UTILIZATOR: {grounding['user']} · modul {grounding['page']['module']}\n"
        f"COD SURSĂ REAL (fragment din {found_in or 'negăsit — spune sincer că nu ai găsit componenta'}):\n{snippet[:1200]}\n"
        f"ACȚIUNI API DISPONIBILE ROLULUI: {grounding['available_actions'][:10]}"
    )
    res = await call_llm(SYSTEM_PROMPT, user_msg, session_id=f"explain-{key[:12]}")
    text = res.get("text") or f"Nu am găsit componenta «{ref}» pe această pagină."
    if res.get("text"):
        await _store(key, "component", path, ctx["user"]["role"], text, res.get("model", ""),
                     {"component_ref": ref, "found_in": found_in})
    return {"explanation": text, "cached": False, "found_in": found_in, "model": res.get("model")}


def _process_fallback(pstate: dict, trail: list, path: str) -> str:
    if not (pstate and pstate.get("found")):
        return ("## Pașii parcurși\n" + ("\n".join(f"- {t}" for t in reversed(trail)) if trail else "- (început)")
                + f"\n\n## Pasul curent\n- {path}")
    parts = [f"## În ce proces te afli\nProcesul **{pstate['process']['name']}**"
             + (f" — {pstate['entity']['label']}." if pstate.get("entity") else " (nepornit încă).")]
    if pstate.get("current_state"):
        parts.append(f"## Etapa curentă\n**{pstate['current_state']}** "
                     f"(pasul {pstate['step_index'] + 1}/{pstate['total_steps']})")
    if pstate.get("completed_steps"):
        parts.append("## Pași finalizați\n" + "\n".join(f"- {s}" for s in pstate["completed_steps"]))
    if pstate.get("next_actions"):
        parts.append("## Ce urmează\n" + "\n".join(
            f"- «{t['to']}» — acționează: {t['actor']}" for t in pstate["next_actions"][:3]))
    if pstate.get("blockers"):
        parts.append("## Blocaje\n" + "\n".join(f"- {b['text']}" for b in pstate["blockers"]))
    return "\n\n".join(parts)


async def explain_process(user: dict, path: str) -> dict:
    ctx, grounding, anatomy = await _grounding(user, path)
    # AIB-006: ancorare pe starea REALĂ a procesului (Process Intelligence Engine)
    pstate = None
    try:
        from ai_brain.process import process_state
        pstate = await process_state(user, path=path)
    except Exception:  # noqa: BLE001
        pstate = None
    pkey = ""
    if pstate and pstate.get("found"):
        pkey = (f"{pstate['process']['id']}|{pstate.get('current_state')}|"
                f"{(pstate.get('entity') or {}).get('id')}|{len(pstate.get('blockers') or [])}")
    key = hashlib.sha1(
        f"process|{path}|{ctx['user']['role']}|{pkey}|{'>'.join(grounding['navigation_trail'][:5])}".encode(), usedforsecurity=False).hexdigest()
    cached = await _cached(key)
    if cached:
        return {"explanation": cached["text"], "cached": True,
                "trail": grounding["navigation_trail"], "process_state": pstate}

    from ai_core.provider import call_llm
    user_msg = (
        "Explică procesul de business în care se află utilizatorul, pe baza stării REALE "
        "din Process Intelligence Engine. Structură (Markdown, română):\n"
        "## În ce proces te afli\n## Etapa curentă și pașii finalizați\n"
        "## Ce urmează și cine trebuie să acționeze (din next_actions/who_acts)\n"
        "## Blocaje și cum le rezolvi (DOAR din blockers — dacă lista e goală, spune explicit că nu există blocaje)\n\n"
        f"STAREA REALĂ A PROCESULUI:\n{pstate}\n\n"
        f"CONTEXT NAVIGARE (trail):\n{grounding['navigation_trail']}"
    )
    res = await call_llm(SYSTEM_PROMPT, user_msg, session_id=f"explain-{key[:12]}")
    if res.get("error") or not res.get("text"):
        return {"explanation": _process_fallback(pstate, grounding["navigation_trail"], path),
                "cached": False, "model": "fallback",
                "trail": grounding["navigation_trail"], "process_state": pstate}
    await _store(key, "process", path, ctx["user"]["role"], res["text"], res.get("model", ""))
    return {"explanation": res["text"], "cached": False, "model": res.get("model"),
            "trail": grounding["navigation_trail"], "process_state": pstate}
