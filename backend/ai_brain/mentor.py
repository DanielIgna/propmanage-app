"""AI Brain · AI Mentor (AIB-004) — copilot contextual per rol.

Punct unic de interacțiune inteligentă: onboarding contextual (o dată per modul,
reluabil), Next Best Action (max 3, REALE — derivate determinist din starea DB a
utilizatorului), Smart Empty States, Contextual Tips (detectare blocaj din Navigation
Context). Reutilizează integral: Context Engine, Explainability (ghidul de onboarding
= explain_page, cu cache-ul lui per rol), Registry. Zero infrastructură paralelă,
zero auto-execuție (conform sprintului).
"""
from datetime import datetime, timezone, timedelta

from db import db
from ai_brain.context import resolve_context, navigation_history


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _action(aid, title, reason, cta_path, priority=2) -> dict:
    return {"id": aid, "title": title, "reason": reason, "cta_path": cta_path, "priority": priority}


# ---------------------------------------------------------------------------
# Next Best Action — reguli deterministe pe starea REALĂ din DB, per rol
# ---------------------------------------------------------------------------
async def _actions_client(user: dict) -> list:
    uid = user.get("id") or str(user.get("_id", ""))
    out = []
    props = await db.properties.count_documents({"owner_id": uid})
    if props == 0:
        out.append(_action("add_property", "Adaugă prima proprietate",
                           "Fără proprietate nu poți folosi Digital Twin, House Health sau cererile de ofertă.",
                           "/client?tab=property", 1))
        return out
    twins = await db.digital_twin_projects.count_documents({"owner_id": uid})
    # PB-001: Mentor folosește PropBenefits — comunică valoarea, nu funcția
    try:
        from propbenefits.ai_agents import success_manager
        sm = await success_manager(user)
        if sm.get("next_action"):
            a = sm["next_action"]
            out.append(_action(f"pb_{a['id']}", a["title"], a["value"], a["cta_path"], 1))
    except Exception:  # noqa: BLE001
        pass
    if twins == 0:
        out.append(_action("activate_twin", "Activează Digital Twin",
                           f"Ai {props} propriet{'ăți' if props > 1 else 'ate'} dar niciun twin digital — copia 3D e baza întregului ecosistem.",
                           "/digital-twin", 1))
    docs = await db.property_documents.count_documents({"owner_id": uid, "deleted": {"$ne": True}})
    if docs == 0:
        out.append(_action("upload_documents", "Încarcă documentele proprietății",
                           "Cartea casei goală = pasaport incomplet și scor House Health scăzut.",
                           "/client?tab=property", 2))
    reqs = await db.requests.count_documents({"client_id": uid})
    if reqs == 0:
        out.append(_action("first_request", "Creează prima cerere de ofertă",
                           "Specialiștii verificați îți pot trimite oferte doar după ce publici o cerere.",
                           "/client?tab=jobs", 2))
    else:
        out.append(_action("house_health", "Vezi House Health",
                           "Scorul de sănătate al casei se actualizează pe baza lucrărilor și documentelor tale.",
                           "/house-health", 3))
    return out


async def _actions_specialist(user: dict) -> list:
    uid = user.get("id") or str(user.get("_id", ""))
    out = []
    if not user.get("specialty") or not user.get("zone"):
        out.append(_action("complete_profile", "Completează-ți profilul",
                           "Fără specializare și zonă nu primești cereri potrivite.", "/specialist", 1))
    active = await db.requests.count_documents({"specialist_id": uid})
    if active == 0:
        out.append(_action("browse_requests", "Vezi cererile disponibile",
                           "Există cereri deschise în marketplace — prima lucrare îți pornește ratingul.",
                           "/specialist", 1))
    if not user.get("verified"):
        out.append(_action("get_verified", "Obține statutul Verificat",
                           "Specialiștii verificați primesc de 3x mai multe oferte acceptate.", "/specialist", 2))
    return out


async def _actions_admin(user: dict) -> list:
    out = []
    arch_open = await db.architecture_guardian_tasks.count_documents({"status": "open"})
    prod_open = await db.product_guardian_tasks.count_documents({"status": "open"})
    if arch_open + prod_open:
        out.append(_action("guardian_tasks", f"Rezolvă {arch_open + prod_open} task-uri Guardian",
                           "Guardienii au găsit probleme deschise de arhitectură/produs.", "/admin/repair-center", 1))
    blocked = await db.orchestrator_retry_queue.count_documents({"status": "blocked_by_config"})
    if blocked:
        out.append(_action("resume_blocked", f"Reia {blocked} emailuri blocate",
                           "Emailuri păstrate după eroare de config — se livrează cu un click după fix.",
                           "/admin/orchestrator", 1))
    out.append(_action("ai_brain", "Vezi AI Brain",
                       "Harta completă a platformei + Context Inspector.", "/admin/ai-brain", 3))
    return out


async def next_best_actions(user: dict) -> list:
    role = user.get("role") or ""
    if role == "client":
        actions = await _actions_client(user)
    elif role == "specialist":
        actions = await _actions_specialist(user)
    elif role in ("admin", "super_admin"):
        actions = await _actions_admin(user)
    else:
        actions = []
    return sorted(actions, key=lambda a: a["priority"])[:3]


# ---------------------------------------------------------------------------
# Contextual Tips — detectare blocaj din Navigation Context (discret, nu intruziv)
# ---------------------------------------------------------------------------
async def contextual_tips(user: dict, path: str) -> list:
    uid = user.get("id") or str(user.get("_id", ""))
    nav = await navigation_history(uid, limit=12)
    tips = []
    clean = path.split("?")[0]
    recent = [e for e in nav["events"]
              if (datetime.now(timezone.utc) - datetime.fromisoformat(e["ts"])) < timedelta(minutes=30)]
    same_page = [e for e in recent if e["path"] == clean]
    if len(same_page) >= 4:
        tips.append({"kind": "stuck_loop",
                     "text": f"Ai revenit de {len(same_page)} ori pe această pagină în ultima jumătate de oră. "
                             "Apasă «Pagina» ca AI Brain să-ți explice fiecare secțiune, sau «Procesul» ca să vezi pasul următor."})
    last_long = next((e for e in recent if e.get("duration_ms", 0) > 5 * 60 * 1000), None)
    if last_long:
        tips.append({"kind": "long_dwell",
                     "text": f"Ai petrecut peste 5 minute pe {last_long['path']}. Dacă ceva nu e clar, "
                             "cere-i mentorului să-ți explice pagina."})
    return tips[:2]


# ---------------------------------------------------------------------------
# Onboarding — o dată per (user, modul), reluabil manual
# ---------------------------------------------------------------------------
async def _onboarding_state(user: dict, module: str, replay: bool) -> bool:
    uid = user.get("id") or str(user.get("_id", ""))
    if replay:
        return True
    seen = await db.ai_brain_mentor_seen.find_one({"user_id": uid, "module": module})
    if seen:
        return False
    await db.ai_brain_mentor_seen.insert_one({"user_id": uid, "module": module, "seen_at": _now()})
    return True


# ---------------------------------------------------------------------------
# Mentor Core — punct unic
# ---------------------------------------------------------------------------
async def mentor_advise(user: dict, path: str, replay: bool = False, include_guide: bool = False) -> dict:
    ctx = await resolve_context(user, path=path)
    module = ctx["location"]["module"]
    show_onboarding = await _onboarding_state(user, module, replay)
    guide = None
    if include_guide and show_onboarding:
        from ai_brain.explain import explain_page
        guide = await explain_page(user, path)
    # AIB-005 · Cross Navigation: module conexe din Knowledge Graph
    related = []
    try:
        from ai_brain.graph import related_modules
        related = await related_modules(module, limit=4)
    except Exception:  # noqa: BLE001
        pass
    # AIB-006 · Process Intelligence: procesul activ real al utilizatorului
    process = None
    try:
        from ai_brain.process import mentor_summary
        process = await mentor_summary(user, path)
    except Exception:  # noqa: BLE001
        pass
    # AIB-007 · Decision Intelligence: Next Best Decision (înlocuiește Next Best Action)
    decisions = []
    try:
        from ai_brain.decision import next_best_decisions
        decisions = await next_best_decisions(user, path)
    except Exception:  # noqa: BLE001
        pass
    if decisions:
        actions = [{"id": d["id"], "title": d["title"],
                    "source_action_id": d.get("source_action_id"),
                    "reason": (d["reasons"] or [d["resolves"]])[0],
                    "cta_path": d["cta_path"], "priority": i + 1, "score": d["score"],
                    "confidence": d.get("confidence")}
                   for i, d in enumerate(decisions[:3])]
    else:
        actions = await next_best_actions(user)
    # AIB-008 · Personal Mentor: insights discrete din comportamentul real
    insights = []
    try:
        from ai_brain.adaptive import personal_insights
        insights = await personal_insights(user, path)
    except Exception:  # noqa: BLE001
        pass
    # AIB-009 · Collaborative Intelligence: cine trebuie să acționeze acum
    collaboration = None
    try:
        from ai_brain.collaboration import mentor_collab
        collaboration = await mentor_collab(user, path)
    except Exception:  # noqa: BLE001
        pass
    return {
        "role": ctx["user"]["role"],
        "module": module,
        "path": path,
        "onboarding": {"show": show_onboarding, "guide": guide},
        "actions": actions,
        "decisions": decisions[:3],
        "insights": insights,
        "collaboration": collaboration,
        "tips": await contextual_tips(user, path),
        "related_modules": related,
        "process": process,
        "generated_at": _now(),
    }


# ---------------------------------------------------------------------------
# Smart Empty States — de ce e gol + pasul următor (determinist, real)
# ---------------------------------------------------------------------------
EMPTY_STATES = {
    "properties": ("Nu ai adăugat încă nicio proprietate.",
                   "Adaugă prima proprietate — e fundația pentru twin, documente și cereri.", "/client?tab=property"),
    "requests": ("Nu ai creat încă nicio cerere de ofertă.",
                 "Publică prima cerere și specialiștii verificați îți trimit oferte.", "/client?tab=jobs"),
    "documents": ("Cartea casei e goală — niciun document încărcat.",
                  "Încarcă actele proprietății ca să-ți crești scorul House Health.", "/client?tab=property"),
    "twins": ("Nu există încă un Digital Twin pentru proprietățile tale.",
              "Activează Digital Twin — copia 3D a locuinței tale.", "/digital-twin"),
    "offers": ("Nu ai încă lucrări atribuite.",
               "Vezi cererile deschise din zona și specializarea ta.", "/specialist"),
    "leads": ("Nu ai încă niciun lead înregistrat.",
              "Adaugă primul lead cu butonul «Lead nou».", "/partner/marketplace"),
}


async def empty_state(user: dict, path: str, resource: str) -> dict:
    ctx = await resolve_context(user, path=path)
    reason, step, cta = EMPTY_STATES.get(resource, (
        "Nu există date aici încă.", "Explorează acțiunile recomandate de mentor.", path))
    actions = await next_best_actions(user)
    return {"resource": resource, "reason": reason, "next_step": step, "cta_path": cta,
            "role": ctx["user"]["role"], "related_actions": actions[:1]}
