"""PropManage router: AI Brain (AIB-001 discovery + AIB-002 context awareness)."""
from fastapi import APIRouter, Depends, HTTPException, Body

from deps import require_role, get_current_user
from db import db
from ai_brain.core import ai_brain_status, run_discovery
from ai_brain import registry, context as ctx

router = APIRouter(prefix="/api/admin/ai-brain", tags=["ai-brain"])
user_router = APIRouter(prefix="/api/ai-brain", tags=["ai-brain-context"])


def _uid(user: dict) -> str:
    return user.get("id") or str(user.get("_id", ""))


@router.get("/status")
async def status(user=Depends(require_role("admin"))):
    return await ai_brain_status()


@router.post("/discover")
async def discover(user=Depends(require_role("admin"))):
    return await run_discovery(trigger=f"manual:{user.get('email')}")


@router.get("/registry/{kind}")
async def registry_get(kind: str, q: str = "", limit: int = 200, user=Depends(require_role("admin"))):
    if kind not in registry.KINDS:
        raise HTTPException(404, f"Kind necunoscut. Disponibile: {', '.join(registry.KINDS)}")
    return await registry.get(kind, q=q, limit=min(limit, 1000))


# ============================================================================
# AIB-002 · Context Awareness — endpoint-uri utilizator autentificat
# ============================================================================
@user_router.get("/context")
async def my_context(path: str = "", entity_id: str = None, action: str = None,
                     user=Depends(get_current_user)):
    return await ctx.resolve_context(user, path=path, entity_id=entity_id, action=action)


@user_router.post("/navigation")
async def record_navigation(payload: dict = Body(...), user=Depends(get_current_user)):
    path = (payload.get("path") or "").strip()
    if not path.startswith("/"):
        raise HTTPException(400, "path invalid")
    return await ctx.record_navigation(_uid(user), path, role=user.get("role"))


@user_router.get("/navigation")
async def my_navigation(limit: int = 20, user=Depends(get_current_user)):
    return await ctx.navigation_history(_uid(user), limit=min(limit, 100))


@user_router.post("/conversation")
async def conversation_append(payload: dict = Body(...), user=Depends(get_current_user)):
    session_id = (payload.get("session_id") or "").strip()
    content = (payload.get("content") or "").strip()
    if not session_id or not content:
        raise HTTPException(400, "session_id și content sunt obligatorii")
    return await ctx.conversation_append(
        _uid(user), session_id, payload.get("role") or "user", content,
        entities=payload.get("entities"), topic=payload.get("topic"))


@user_router.get("/conversation/{session_id}")
async def conversation_get(session_id: str, user=Depends(get_current_user)):
    doc = await ctx.conversation_get(_uid(user), session_id)
    if not doc:
        raise HTTPException(404, "Conversație inexistentă")
    return doc


@user_router.get("/conversations")
async def conversation_list(user=Depends(get_current_user)):
    return {"items": await ctx.conversation_list(_uid(user))}


# ============================================================================
# AIB-003 · Explainability Engine — Context First, grounding real, cache per rol
# ============================================================================
@user_router.post("/explain/page")
async def explain_page(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain import explain
    path = (payload.get("path") or "").strip()
    if not path.startswith("/"):
        raise HTTPException(400, "path invalid")
    return await explain.explain_page(user, path)


@user_router.post("/explain/component")
async def explain_component(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain import explain
    path = (payload.get("path") or "").strip()
    ref = (payload.get("component") or "").strip()
    if not path.startswith("/") or not ref:
        raise HTTPException(400, "path și component sunt obligatorii")
    return await explain.explain_component(user, path, ref)


@user_router.post("/explain/process")
async def explain_process(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain import explain
    path = (payload.get("path") or "").strip()
    if not path.startswith("/"):
        raise HTTPException(400, "path invalid")
    return await explain.explain_process(user, path)


# ============================================================================
# AIB-004 · AI Mentor — copilot contextual per rol
# ============================================================================
@user_router.get("/mentor")
async def mentor(path: str, replay: bool = False, include_guide: bool = False,
                 user=Depends(get_current_user)):
    from ai_brain import mentor as mentor_svc
    if not path.startswith("/"):
        raise HTTPException(400, "path invalid")
    return await mentor_svc.mentor_advise(user, path, replay=replay, include_guide=include_guide)


@user_router.post("/mentor/empty-state")
async def mentor_empty_state(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain import mentor as mentor_svc
    path = (payload.get("path") or "").strip()
    resource = (payload.get("resource") or "").strip()
    if not path.startswith("/") or not resource:
        raise HTTPException(400, "path și resource sunt obligatorii")
    return await mentor_svc.empty_state(user, path, resource)


# ============================================================================
# AIB-005 · Knowledge Intelligence Engine
# ============================================================================
@user_router.post("/explain/relationship")
async def explain_relationship(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain import graph
    question = (payload.get("question") or "").strip()
    if len(question) < 3:
        raise HTTPException(400, "question e obligatoriu")
    return await graph.explain_relationship(user, question)


@router.post("/graph/build")
async def graph_build(user=Depends(require_role("admin"))):
    from ai_brain import graph
    return await graph.build_graph()


@router.get("/graph/overview")
async def graph_overview(user=Depends(require_role("admin"))):
    from ai_brain import graph
    return await graph.overview()


@router.get("/graph/search")
async def graph_search(q: str = "", kind: str = "", user=Depends(require_role("admin"))):
    from ai_brain import graph
    return {"items": await graph.search_nodes(q=q, kind=kind)}


@router.get("/graph/node")
async def graph_node(id: str, user=Depends(require_role("admin"))):
    from ai_brain import graph
    d = await graph.node_detail(id)
    if not d["node"]:
        raise HTTPException(404, "Nod inexistent")
    return d


@router.get("/graph/impact")
async def graph_impact(id: str, user=Depends(require_role("admin"))):
    from ai_brain import graph
    return await graph.impact(id)


@router.get("/graph/modules/{module}/related")
async def graph_related_modules(module: str, user=Depends(require_role("admin"))):
    from ai_brain import graph
    return {"module": module, "related": await graph.related_modules(module, exclude_hubs=False)}


# ============================================================================
# AIB-006 · Process Intelligence Engine
# ============================================================================
@router.post("/processes/build")
async def processes_build(user=Depends(require_role("admin"))):
    from ai_brain.process import build_processes
    return await build_processes(run_id=f"manual:{user.get('email')}")


@router.get("/processes")
async def processes_list(kind: str = "", user=Depends(require_role("admin"))):
    from ai_brain.process import list_processes
    return {"items": await list_processes(kind=kind)}


@router.get("/processes/{pid}")
async def process_detail(pid: str, user=Depends(require_role("admin"))):
    from ai_brain.process import get_process
    p = await get_process(pid)
    if not p:
        raise HTTPException(404, "Proces inexistent")
    return p


@router.get("/processes/{pid}/state")
async def process_state_inspect(pid: str, email: str, entity_id: str = None,
                                user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    from ai_brain.process import process_state
    return await process_state(target, process_id=pid, entity_id=entity_id)


@user_router.get("/process/state")
async def my_process_state(path: str = "", process_id: str = None, entity_id: str = None,
                           user=Depends(get_current_user)):
    from ai_brain.process import process_state
    return await process_state(user, process_id=process_id, entity_id=entity_id, path=path)


# ============================================================================
# AIB-007 · Decision Intelligence Engine
# ============================================================================
@user_router.get("/decisions")
async def my_decisions(path: str = "", user=Depends(get_current_user)):
    from ai_brain.decision import next_best_decisions
    return {"items": await next_best_decisions(user, path)}


async def _decision_actor(payload: dict, user: dict) -> dict:
    """Admin poate explica/simula deciziile altui utilizator (payload.email)."""
    email = (payload.get("email") or "").strip().lower()
    if email and email != user.get("email") and user.get("role") in ("admin", "super_admin"):
        target = await db.users.find_one({"email": email})
        if not target:
            raise HTTPException(404, f"Utilizator inexistent: {email}")
        target["id"] = target.get("id") or str(target["_id"])
        return target
    return user


@user_router.post("/decisions/explain")
async def decision_explain(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain.decision import explain_decision
    did = (payload.get("decision_id") or "").strip()
    if not did:
        raise HTTPException(400, "decision_id e obligatoriu")
    actor = await _decision_actor(payload, user)
    return await explain_decision(actor, did, question=(payload.get("question") or "").strip())


@user_router.post("/decisions/simulate")
async def decision_simulate(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain.decision import simulate_decision
    did = (payload.get("decision_id") or "").strip()
    if not did:
        raise HTTPException(400, "decision_id e obligatoriu")
    actor = await _decision_actor(payload, user)
    return await simulate_decision(actor, did)


@router.get("/decisions/rules")
async def decisions_rules(user=Depends(require_role("admin"))):
    from ai_brain.decision import decision_rules
    return decision_rules()


@router.get("/decisions/priorities")
async def decisions_priorities(user=Depends(require_role("admin"))):
    from ai_brain.decision import platform_priorities
    return {"items": await platform_priorities()}


@router.get("/decisions/inspect")
async def decisions_inspect(email: str, path: str = "", user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    from ai_brain.decision import next_best_decisions
    return {"email": email, "role": target.get("role"),
            "items": await next_best_decisions(target, path)}


# ============================================================================
# AIB-010 · Certification & Production Readiness
# ============================================================================
@router.post("/certification/run")
async def certification_run(user=Depends(require_role("admin"))):
    from ai_brain.certification import run_certification
    return await run_certification(trigger=f"manual:{user.get('email')}")


@router.get("/certification/latest")
async def certification_latest(user=Depends(require_role("admin"))):
    from ai_brain.certification import latest_certificate
    cert = await latest_certificate()
    if not cert:
        raise HTTPException(404, "Nicio certificare rulată încă — folosește POST /certification/run")
    return cert


@router.get("/certification/debt")
async def certification_debt(user=Depends(require_role("admin"))):
    from ai_brain.certification import tech_debt_scan
    return await tech_debt_scan()


# ============================================================================
# AIB-009 · Collaborative Intelligence Engine
# ============================================================================
@user_router.get("/collaboration/state")
async def my_collaboration_state(path: str = "", process_id: str = None, entity_id: str = None,
                                 user=Depends(get_current_user)):
    from ai_brain.collaboration import collaboration_state
    return await collaboration_state(user, process_id=process_id, entity_id=entity_id, path=path)


@router.post("/collaboration/sweep")
async def collaboration_sweep(user=Depends(require_role("admin"))):
    from ai_brain.collaboration import sla_sweep
    return await sla_sweep(run_id=f"manual:{user.get('email')}")


@router.get("/collaboration/overview")
async def collaboration_overview_ep(user=Depends(require_role("admin"))):
    from ai_brain.collaboration import collaboration_overview
    return await collaboration_overview()


@router.get("/collaboration/handoffs/{pid}")
async def collaboration_handoffs(pid: str, user=Depends(require_role("admin"))):
    from ai_brain.collaboration import handoff_map
    from ai_brain.process import get_process
    p = await get_process(pid)
    if not p:
        raise HTTPException(404, "Proces inexistent")
    return {"process_id": pid, "process_name": p["name"], "actors": p.get("actors") or [],
            "handoffs": handoff_map(p)}


@router.get("/collaboration/notifications")
async def collaboration_notifications(user=Depends(require_role("admin"))):
    items = [n async for n in db.ai_brain_notifications.find(
        {"status": "active"}, {"_id": 0}).sort("priority", -1).limit(50)]
    return {"items": items}


@router.get("/collaboration/state")
async def collaboration_state_inspect(pid: str, email: str, entity_id: str = None,
                                      user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    from ai_brain.collaboration import collaboration_state
    return await collaboration_state(target, process_id=pid, entity_id=entity_id)


# ============================================================================
# AIB-008 · Adaptive Intelligence Engine
# ============================================================================
@user_router.post("/decisions/feedback")
async def decision_feedback(payload: dict = Body(...), user=Depends(get_current_user)):
    from ai_brain.adaptive import record_feedback
    did = (payload.get("decision_id") or "").strip()
    action = (payload.get("action") or "").strip()
    if not did or not action:
        raise HTTPException(400, "decision_id și action sunt obligatorii")
    res = await record_feedback(user, did, action)
    if not res["ok"]:
        raise HTTPException(400, res["reason"])
    return res


@user_router.get("/profile")
async def my_behavior_profile(user=Depends(get_current_user)):
    from ai_brain.adaptive import build_user_profile
    return await build_user_profile(user)


@router.get("/adaptive/overview")
async def adaptive_overview(user=Depends(require_role("admin"))):
    from ai_brain.adaptive import adaptive_overview as ov
    return await ov()


@router.get("/adaptive/roles")
async def adaptive_roles(user=Depends(require_role("admin"))):
    from ai_brain.adaptive import role_profiles
    return {"items": await role_profiles()}


@router.get("/adaptive/processes")
async def adaptive_processes(user=Depends(require_role("admin"))):
    from ai_brain.adaptive import process_learning
    return await process_learning()


@router.get("/adaptive/behavior")
async def adaptive_behavior(email: str, user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    from ai_brain.adaptive import build_user_profile
    return await build_user_profile(target)


# ============================================================================
# CORE-001 · Product Intelligence — Live Product Map + snapshots + report
# ============================================================================
@router.get("/product-map")
async def product_map(refresh: bool = False, user=Depends(require_role("admin"))):
    from ai_brain.product_intelligence import get_product_map
    return await get_product_map(refresh=refresh)


@router.post("/product-map/snapshot")
async def product_map_snapshot(body: dict = None, user=Depends(require_role("admin"))):
    from ai_brain.product_intelligence import save_snapshot
    return await save_snapshot((body or {}).get("label", ""), user.get("email", "admin"))


@router.get("/product-map/snapshots")
async def product_map_snapshots(user=Depends(require_role("admin"))):
    from ai_brain.product_intelligence import list_snapshots
    return {"items": await list_snapshots()}


@router.get("/product-map/snapshots/compare")
async def product_map_compare(a: str, b: str, user=Depends(require_role("admin"))):
    from ai_brain.product_intelligence import compare_snapshots
    return await compare_snapshots(a, b)


@router.get("/product-map/report")
async def product_map_report(user=Depends(require_role("admin"))):
    from ai_brain.product_intelligence import generate_report
    return await generate_report()


# ============================================================================
# AIB-002 · Context Inspector — admin analizează contextul oricărui utilizator
# ============================================================================
@router.get("/context/inspect")
async def context_inspect(email: str, path: str = "", entity_id: str = None,
                          user=Depends(require_role("admin"))):
    target = await db.users.find_one({"email": email.strip().lower()})
    if not target:
        raise HTTPException(404, f"Utilizator inexistent: {email}")
    target["id"] = target.get("id") or str(target["_id"])
    return {
        "context": await ctx.resolve_context(target, path=path, entity_id=entity_id),
        "navigation": await ctx.navigation_history(target["id"], limit=15),
        "conversations": await ctx.conversation_list(target["id"], limit=5),
    }
