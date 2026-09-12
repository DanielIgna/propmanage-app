"""Design Intelligence Engine — P1a Layout Optimizer, P1b Component Optimizer, P1c Evolution Engine.

Every proposal carries an Impact Score (0-100) computed server-side from:
  ux_benefit (0-100) × 45% + users_reach (0-100) × 35% + inverse effort × 10% + inverse risk × 10%.

Evolution pipeline: proposed → testing → approved → applied | rejected.
Token-based proposals apply LIVE via db.design_tokens with a snapshot for rollback.
No proposal is applied without explicit admin action.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_role
from routes.design_audit import PAGES, _find_page
from routes.design_studio import COMPONENT_LIBRARY, _deep_merge, _get_active

router = APIRouter(prefix="/api/admin/design-intelligence", tags=["design-intelligence"])
logger = logging.getLogger("propmanage.design_intelligence")

VALID_STATUSES = ["proposed", "testing", "approved", "applied", "rejected"]
TRANSITIONS = {
    "start_test": {"from": ["proposed"], "to": "testing"},
    "approve":    {"from": ["testing", "proposed"], "to": "approved"},
    "reject":     {"from": ["proposed", "testing", "approved"], "to": "rejected"},
    "apply":      {"from": ["approved"], "to": "applied"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _impact_score(ux_benefit: int, users_reach: int, effort: int, risk: int) -> dict[str, Any]:
    ux = max(0, min(100, int(ux_benefit)))
    reach = max(0, min(100, int(users_reach)))
    eff = max(1, min(5, int(effort)))
    rsk = max(1, min(5, int(risk)))
    inv_effort = 100 - (eff - 1) * 25
    inv_risk = 100 - (rsk - 1) * 25
    score = round(ux * 0.45 + reach * 0.35 + inv_effort * 0.10 + inv_risk * 0.10)
    return {
        "score": score,
        "ux_benefit": ux,
        "users_reach": reach,
        "effort": eff,
        "risk": rsk,
        "tier": "high" if score >= 70 else "medium" if score >= 40 else "low",
    }


def _clean_token_patch(raw: Any) -> dict | None:
    """Keep only token groups we allow AI to touch (colors/radii/components/typography/spacing/shadows)."""
    if not isinstance(raw, dict) or not raw:
        return None
    allowed = {"colors", "radii", "components", "typography", "spacing", "shadows"}
    out = {}
    for k, v in raw.items():
        if k in allowed and isinstance(v, dict) and v:
            out[k] = {str(kk): str(vv) for kk, vv in v.items()}
    return out or None


def _normalize_proposals(raw_list: Any, source: str, target: str, target_label: str) -> list[dict]:
    out = []
    for p in (raw_list or [])[:6]:
        if not isinstance(p, dict) or not p.get("title"):
            continue
        impact = _impact_score(
            p.get("ux_benefit", 50), p.get("users_reach", 50),
            p.get("effort", 3), p.get("risk", 2),
        )
        out.append({
            "id": uuid.uuid4().hex[:12],
            "source": source,
            "target": target,
            "target_label": target_label,
            "title": str(p.get("title"))[:140],
            "description": str(p.get("description") or "")[:600],
            "change_type": p.get("change_type") if p.get("change_type") in ("layout", "tokens", "content", "navigation", "component") else "layout",
            "ux_law": str(p.get("ux_law") or "")[:60],
            "token_patch": _clean_token_patch(p.get("token_patch")),
            "impact": impact,
            "status": "proposed",
            "created_at": _now(),
            "history": [{"at": _now(), "action": "proposed", "by": "ai"}],
        })
    return out


def _fallback_layout_proposals(page: dict) -> list[dict]:
    raw = [
        {"title": f"Progressive disclosure pe {page['label']}", "description": "Grupează acțiunile secundare într-un meniu colapsabil pentru a reduce alegerile simultane sub 7 (Hick's Law).",
         "change_type": "layout", "ux_law": "Hick's Law", "ux_benefit": 65, "users_reach": 70, "effort": 2, "risk": 1},
        {"title": "CTA principal în thumb zone pe mobil", "description": "Mută butonul de acțiune primară în zona inferioară accesibilă cu degetul mare (bottom 25% viewport).",
         "change_type": "layout", "ux_law": "Fitts' Law", "ux_benefit": 60, "users_reach": 55, "effort": 2, "risk": 1},
        {"title": "Chunking vizual pe secțiuni", "description": "Împarte conținutul în grupuri de max 5-7 elemente cu heading-uri clare (Miller's Law).",
         "change_type": "content", "ux_law": "Miller's Law", "ux_benefit": 50, "users_reach": 60, "effort": 3, "risk": 1},
    ]
    return _normalize_proposals(raw, "layout_optimizer", page["key"], page["label"])


def _fallback_component_proposals(comp: dict) -> list[dict]:
    raw = [
        {"title": f"Touch target ≥44px pe {comp['label']}", "description": "Asigură dimensiune minimă 44×44px pentru orice zonă interactivă a componentei (WCAG + mobile-first).",
         "change_type": "component", "ux_law": "Fitts' Law", "ux_benefit": 55, "users_reach": 80, "effort": 2, "risk": 1},
        {"title": f"Stare focus vizibilă pe {comp['label']}", "description": "Adaugă ring de focus cu culoarea primary pentru navigare tastatură (WCAG AA).",
         "change_type": "component", "ux_law": "WCAG AA", "ux_benefit": 45, "users_reach": 40, "effort": 1, "risk": 1},
    ]
    return _normalize_proposals(raw, "component_optimizer", comp["key"], comp["label"])


class LayoutAnalyzePayload(BaseModel):
    page_key: str


class ComponentAnalyzePayload(BaseModel):
    component_key: str


# ── P1a — LAYOUT OPTIMIZER ────────────────────────────────────────────────────
@router.post("/layout/analyze")
async def layout_analyze(payload: LayoutAnalyzePayload, admin=Depends(require_role("admin"))):
    page = _find_page(payload.page_key)
    if not page:
        raise HTTPException(404, f"Pagină necunoscută: {payload.page_key}")

    audit = await db.design_audit_cache.find_one({"key": page["key"]}, {"_id": 0})
    audit_ctx = ""
    if audit and audit.get("result"):
        r = audit["result"]
        audit_ctx = (
            f"\nScoruri audit existente: mobile={r.get('mobile_score')}, desktop={r.get('desktop_score')}, "
            f"hicks={r.get('hicks_law_score')}, fitts={r.get('fitts_law_score')}, miller={r.get('millers_law_score')}, "
            f"cognitive_load={r.get('cognitive_load')}. Constatări: {'; '.join(map(str, (r.get('findings') or [])[:3]))}"
        )

    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești Layout Optimizer AI pentru PropManage (platformă românească property services). "
            "Design System: lime brand, tokens CSS variables, card rounded-2xl alb/slate-800, mobile-first. "
            "Propui modificări CONCRETE de layout per pagină, fiecare susținută de o lege UX "
            "(Hick, Miller, Fitts, Jakob, Nielsen, WCAG, Mobile-first). "
            "Pentru fiecare propunere estimezi: ux_benefit (0-100, cât de mult îmbunătățește UX), "
            "users_reach (0-100, % utilizatori afectați), effort (1-5, 1=trivial 5=refactor major), "
            "risk (1-5, 1=zero risc regresie). Dacă propunerea se poate implementa prin design tokens "
            "(culori/radii/spacing), include token_patch (ex: {\"radii\": {\"lg\": \"16px\"}}), altfel omite. "
            "Răspunde STRICT JSON: {\"proposals\": [{\"title\": str scurt RO, \"description\": str RO ≤400c acționabil, "
            "\"change_type\": \"layout|tokens|content|navigation\", \"ux_law\": str, "
            "\"ux_benefit\": int, \"users_reach\": int, \"effort\": int, \"risk\": int, \"token_patch\": obj|null}]}. "
            "Maxim 5 propuneri, doar cele cu valoare reală. Fii critic și specific paginii."
        )
        prompt = (
            f"Pagina: {page['label']} ({page['path']}, zonă={page['zone']}).\n"
            f"Conținut: {page['brief']}{audit_ctx}\n\n"
            f"Generează propuneri de optimizare layout cu estimări de impact."
        )
        result = await claude_json(system=system, prompt=prompt, session_prefix=f"layout-opt-{page['key']}")
        proposals = _normalize_proposals(result.get("proposals"), "layout_optimizer", page["key"], page["label"])
        if not proposals:
            raise ValueError("Zero propuneri valide")
        ai_generated = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[design-intel] layout LLM fail ({page['key']}): {e} — fallback")
        proposals = _fallback_layout_proposals(page)
        ai_generated = False

    if proposals:
        await db.design_proposals.insert_many([{**p} for p in proposals])
    return {"proposals": proposals, "ai_generated": ai_generated, "page": page}


# ── P1b — COMPONENT OPTIMIZER ─────────────────────────────────────────────────
@router.post("/components/analyze")
async def component_analyze(payload: ComponentAnalyzePayload, admin=Depends(require_role("admin"))):
    comp = next((c for c in COMPONENT_LIBRARY if c["key"] == payload.component_key), None)
    if not comp:
        raise HTTPException(404, f"Componentă necunoscută: {payload.component_key}")

    active = await _get_active()
    tokens = active["tokens"]
    colors = tokens.get("colors", {})
    comps = tokens.get("components", {})

    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești Component Optimizer AI pentru Design System-ul PropManage. "
            "Analizezi o componentă din bibliotecă și tokens-urile active pe care le consumă, "
            "și propui optimizări concrete (contrast WCAG, touch targets, consistență, stări hover/focus, densitate). "
            "Pentru fiecare propunere: ux_benefit (0-100), users_reach (0-100 — componentele folosite peste tot au reach mare), "
            "effort (1-5), risk (1-5). Dacă fix-ul e realizabil prin tokens, include token_patch "
            "(doar grupuri: colors/radii/components/typography/spacing/shadows). "
            "Răspunde STRICT JSON: {\"proposals\": [{\"title\": str RO, \"description\": str RO ≤400c, "
            "\"change_type\": \"component|tokens\", \"ux_law\": str, \"ux_benefit\": int, \"users_reach\": int, "
            "\"effort\": int, \"risk\": int, \"token_patch\": obj|null}]}. Max 4 propuneri, doar valoroase."
        )
        prompt = (
            f"Componenta: {comp['label']} (key={comp['key']}, categorie={comp['category']}).\n"
            f"Tokens consumate: {', '.join(comp['tokens'])}.\n"
            f"Valori active relevante: primary={colors.get('primary')}, on_primary={colors.get('on_primary')}, "
            f"surface={colors.get('surface')}, text={colors.get('text')}, border={colors.get('border')}, "
            f"button_style={comps.get('button_style')}, card_style={comps.get('card_style')}, "
            f"table_density={comps.get('table_density')}.\n\n"
            f"Propune optimizări cu estimări de impact."
        )
        result = await claude_json(system=system, prompt=prompt, session_prefix=f"comp-opt-{comp['key']}")
        proposals = _normalize_proposals(result.get("proposals"), "component_optimizer", comp["key"], comp["label"])
        if not proposals:
            raise ValueError("Zero propuneri valide")
        ai_generated = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[design-intel] component LLM fail ({comp['key']}): {e} — fallback")
        proposals = _fallback_component_proposals(comp)
        ai_generated = False

    if proposals:
        await db.design_proposals.insert_many([{**p} for p in proposals])
    return {"proposals": proposals, "ai_generated": ai_generated, "component": comp}


# ── P1c — EVOLUTION ENGINE (pipeline + apply/rollback) ────────────────────────
@router.get("/proposals")
async def list_proposals(status: str | None = None, source: str | None = None, limit: int = 100,
                         _admin=Depends(require_role("admin"))):
    q: dict[str, Any] = {}
    if status:
        q["status"] = status
    if source:
        q["source"] = source
    out = []
    cursor = db.design_proposals.find(q, {"_id": 0}).sort("created_at", -1).limit(max(1, min(limit, 300)))
    async for doc in cursor:
        out.append(doc)
    return {"proposals": out, "total": len(out)}


@router.get("/summary")
async def intelligence_summary(_admin=Depends(require_role("admin"))):
    counts = {s: 0 for s in VALID_STATUSES}
    scores: list[int] = []
    top: list[dict] = []
    async for doc in db.design_proposals.find({}, {"_id": 0}):
        counts[doc.get("status", "proposed")] = counts.get(doc.get("status", "proposed"), 0) + 1
        sc = (doc.get("impact") or {}).get("score")
        if isinstance(sc, int):
            scores.append(sc)
        if doc.get("status") in ("proposed", "testing", "approved"):
            top.append(doc)
    top.sort(key=lambda d: -(d.get("impact") or {}).get("score", 0))
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "avg_impact": round(sum(scores) / len(scores), 1) if scores else None,
        "top_pending": top[:5],
    }


@router.post("/proposals/{proposal_id}/advance")
async def advance_proposal(proposal_id: str, action: str = Body(..., embed=True),
                           admin=Depends(require_role("admin"))):
    t = TRANSITIONS.get(action)
    if not t:
        raise HTTPException(400, f"Acțiune invalidă: {action}. Valide: {list(TRANSITIONS)}")
    doc = await db.design_proposals.find_one({"id": proposal_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Propunere inexistentă")
    if doc["status"] not in t["from"]:
        raise HTTPException(400, f"Tranziție invalidă: {doc['status']} → {t['to']} (acțiune {action})")

    admin_email = admin.get("email") or "admin"
    update: dict[str, Any] = {"status": t["to"], "updated_at": _now()}
    applied_result = None

    if action == "apply":
        patch = doc.get("token_patch")
        if patch:
            active = await _get_active()
            snapshot = active["tokens"]
            merged = _deep_merge(snapshot, patch)
            await db.design_tokens.update_one(
                {"_id": "active"},
                {"$set": {"tokens": merged, "preset_id": "custom", "updated_at": _now()}},
                upsert=True,
            )
            update["applied_snapshot"] = snapshot
            update["applied_at"] = _now()
            applied_result = {"tokens_applied": True, "patch": patch}
        else:
            update["applied_at"] = _now()
            applied_result = {"tokens_applied": False, "note": "Modificare non-token — necesită implementare manuală în cod. Marcată ca aplicată pentru tracking."}

    await db.design_proposals.update_one(
        {"id": proposal_id},
        {"$set": update, "$push": {"history": {"at": _now(), "action": action, "by": admin_email}}},
    )
    fresh = await db.design_proposals.find_one({"id": proposal_id}, {"_id": 0})
    return {"proposal": fresh, "applied": applied_result}


@router.post("/proposals/{proposal_id}/rollback")
async def rollback_proposal(proposal_id: str, admin=Depends(require_role("admin"))):
    doc = await db.design_proposals.find_one({"id": proposal_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Propunere inexistentă")
    if doc["status"] != "applied":
        raise HTTPException(400, "Rollback disponibil doar pentru propuneri aplicate.")
    snapshot = doc.get("applied_snapshot")
    if snapshot:
        await db.design_tokens.update_one(
            {"_id": "active"},
            {"$set": {"tokens": snapshot, "preset_id": "custom", "updated_at": _now()}},
            upsert=True,
        )
    admin_email = getattr(admin, "email", None) or (admin.get("email") if isinstance(admin, dict) else "admin")
    await db.design_proposals.update_one(
        {"id": proposal_id},
        {"$set": {"status": "approved", "updated_at": _now()},
         "$unset": {"applied_snapshot": "", "applied_at": ""},
         "$push": {"history": {"at": _now(), "action": "rollback", "by": admin_email}}},
    )
    fresh = await db.design_proposals.find_one({"id": proposal_id}, {"_id": 0})
    return {"proposal": fresh, "tokens_restored": bool(snapshot)}


@router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, _admin=Depends(require_role("admin"))):
    res = await db.design_proposals.delete_one({"id": proposal_id, "status": {"$in": ["rejected", "proposed"]}})
    if res.deleted_count == 0:
        raise HTTPException(400, "Se pot șterge doar propuneri în status proposed sau rejected.")
    return {"ok": True}


@router.get("/targets")
async def list_targets(_admin=Depends(require_role("admin"))):
    """Pages + components available for analysis."""
    return {
        "pages": [{"key": p["key"], "label": p["label"], "zone": p["zone"], "path": p["path"]} for p in PAGES],
        "components": [{"key": c["key"], "label": c["label"], "category": c["category"]} for c in COMPONENT_LIBRARY],
    }
