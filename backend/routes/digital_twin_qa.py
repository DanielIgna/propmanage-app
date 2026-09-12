"""Digital Twin AI Q&A — Phase 2 of AI Ecosystem.

Lets users ask natural-language questions about a Digital Twin project.
The AI receives context built from existing collections:
  - digital_twin_projects (project meta)
  - digital_twin_models (uploaded files: GLB/IFC/SKP)
  - digital_twin_plans (2D floor plans with rooms)
  - digital_twin_pins (annotations: equipment, finishes, etc.)
  - digital_twin_comments (pin discussion threads)

The endpoint stores conversation history in `digital_twin_qa_sessions` and
persists memorable facts to ai_memories (scope=client_agent or admin_agent).

Read-only on twin data — never mutates the project.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_current_user
from db import db
from ai_core.provider import call_llm, ecosystem_enabled
from ai_core import memory as ai_memory

logger = logging.getLogger("propmanage.dt_qa")

router = APIRouter(prefix="/api/digital-twin/qa", tags=["digital-twin-qa"])


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


_SYSTEM = """You are the Property & Digital Twin AI assistant for PropManage — a Romanian property platform. Answer in Romanian.
You receive structured EVIDENCE about a property and its Digital Twin: 2D rooms, 3D models, equipment pins,
plus property identity, House Health, documents, completed works and AI-generated (orientative) models.

CRITICAL — evidence & trust rules:
- Ground EVERY claim in the provided evidence. NEVER invent numbers, materials, brands, dimensions or routes.
- Each evidence block is labelled with its trust type — always reflect the trust level in your answer:
  · DECLARAT de proprietar (owner-declared) → "conform declarației proprietarului".
  · DOCUMENTAT (documents) → "conform documentelor".
  · REZULTAT LUCRĂRI (from works) → "rezultat din lucrări".
  · MOTOR/DERIVAT (House Health) → "scor derivat de motorul House Health".
  · INFERAT (AI-generated) → spune clar "estimare orientativă (AI), neverificată".
- If the evidence does NOT contain the answer, reply EXACTLY: "Această informație nu există în datele proprietății (necunoscut)." Do not guess.
- Be concise and factual. Sum room areas (area_m2) when relevant. For equipment mention pin label + room + type."""


async def _build_context(project_id: str) -> str:
    """Build a compact context string from twin collections."""
    project = await db.digital_twin_projects.find_one({"id": project_id})
    if not project:
        return ""

    parts = [f"# Project: {project.get('name', 'Untitled')}"]
    if project.get("description"):
        parts.append(f"Description: {project['description']}")
    if project.get("address"):
        parts.append(f"Address: {project['address']}")

    # Models
    models = await db.digital_twin_models.find({"project_id": project_id}, {"name": 1, "kind": 1, "format": 1, "uploaded_at": 1, "_id": 0}).to_list(length=20)
    if models:
        parts.append("\n## 3D Models uploaded")
        for m in models:
            parts.append(f"- {m.get('name')} ({m.get('format', '?')}, {m.get('kind', '?')})")

    # Plans + rooms
    plans = await db.digital_twin_plans.find({"project_id": project_id}).to_list(length=20)
    if plans:
        parts.append("\n## 2D Floor Plans & Rooms")
        for p in plans:
            parts.append(f"### {p.get('name', 'Plan')} (level {p.get('level', '?')})")
            for room in (p.get("rooms") or []):
                area = room.get("area_m2")
                area_str = f"{area} m²" if area else "?"
                parts.append(f"  - {room.get('name', 'Room')}: {area_str}, type={room.get('type', '?')}")

    # Pins (equipment, finishes, electric panel locations, etc.)
    pins = await db.digital_twin_pins.find({"project_id": project_id}).to_list(length=200)
    if pins:
        parts.append(f"\n## Pins / Annotations ({len(pins)})")
        for p in pins[:80]:
            label = p.get("label") or p.get("title") or "Pin"
            ptype = p.get("type") or p.get("category") or "info"
            room = p.get("room_name") or "?"
            details = p.get("description") or p.get("notes") or ""
            parts.append(f"- [{ptype}] {label} (camera: {room}) {details[:120]}")

    # Property-level EVIDENCE (only when the project is anchored to a property) — Q&A pe dovezi.
    prop_id = project.get("property_id")
    if prop_id:
        try:
            from bson import ObjectId as _OID
            prop = await db.properties.find_one({"_id": _OID(prop_id)})
        except Exception:  # noqa: BLE001
            prop = None
        if prop:
            parts.append("\n## Proprietate — identitate (DECLARAT de proprietar)")
            parts.append(f"- Nume: {prop.get('name','?')}; adresă: {prop.get('address','?')}; tip: {prop.get('type','?')}; suprafață: {prop.get('surface','?')} m²; camere: {prop.get('rooms','?')}")
            hs = prop.get("health_score")
            if hs is not None:
                parts.append(f"\n## House Health (MOTOR/DERIVAT)\n- Scor sănătate: {hs}/100")
        docs = await db.property_documents.find({"property_id": prop_id}, {"title": 1, "category": 1, "_id": 0}).to_list(length=40)
        if docs:
            parts.append("\n## Documente proprietate (DOCUMENTAT)")
            for d in docs:
                parts.append(f"- {d.get('title','document')} · categorie={d.get('category','?')}")
        works = await db.requests.find(
            {"property_id": prop_id, "status": {"$in": ["completed", "closed", "confirmed", "done"]}},
            {"title": 1, "category": 1, "status": 1, "_id": 0},
        ).to_list(length=40)
        if works:
            parts.append("\n## Lucrări finalizate (REZULTAT LUCRĂRI)")
            for w in works:
                parts.append(f"- {w.get('title') or w.get('category','lucrare')} · status={w.get('status')}")
        ai_models = await db.digital_twin_models.find(
            {"property_id": prop_id, "source": "ai_generated"}, {"filename": 1, "confidence": 1, "_id": 0},
        ).to_list(length=10)
        if ai_models:
            parts.append("\n## Modele 3D generate de AI (INFERAT — orientativ, neverificat)")
            for m in ai_models:
                parts.append(f"- {m.get('filename','model AI')} · confidence={m.get('confidence')}")

    return "\n".join(parts)


# ---------- Schemas ----------
class AskIn(BaseModel):
    project_id: str = Field(min_length=3)
    question: str = Field(min_length=2, max_length=1000)
    session_id: Optional[str] = None


# ---------- Endpoints ----------
@router.post("/ask")
async def ask(payload: AskIn, user: dict = Depends(get_current_user)):
    """Answer a question about a Digital Twin project."""
    if not await ecosystem_enabled():
        return {"answer": "Ecosistemul AI este momentan dezactivat din Admin Settings.", "context_size": 0, "session_id": payload.session_id}

    # Authorization: user must own project OR be admin OR be a member
    project = await db.digital_twin_projects.find_one({"id": payload.project_id})
    if not project:
        raise HTTPException(404, "Project not found")

    owner_ok = str(project.get("owner_id")) == str(user.get("id"))
    member_ok = user.get("id") in (project.get("members") or [])
    admin_ok = user.get("role") in ("admin", "operator")
    if not (owner_ok or member_ok or admin_ok):
        raise HTTPException(403, "Access denied to this project")

    context = await _build_context(payload.project_id)
    if not context:
        return {"answer": "Acest proiect Digital Twin nu are încă date. Adaugă modele 3D, planuri 2D sau pin-uri.", "context_size": 0, "session_id": payload.session_id}

    # Inject relevant prior memories
    memories = await ai_memory.recall(user_id=user.get("email") or user["id"], query=payload.question, scope="client_agent", limit=3)
    mem_block = ""
    if memories:
        mem_block = "\n\n## Prior context from your past questions:\n" + "\n".join(f"- {m['summary']}" for m in memories)

    user_message = (
        f"## Digital Twin Context\n{context}{mem_block}\n\n"
        f"## Question\n{payload.question}\n\nReply in Romanian."
    )

    sid = payload.session_id or uuid.uuid4().hex
    result = await call_llm(_SYSTEM, user_message, session_id=f"dt-qa-{sid[:8]}")
    answer = result.get("text") or "Nu am putut răspunde acum. Încearcă din nou peste un minut."
    if result.get("error"):
        logger.warning(f"[dt_qa] LLM error: {result['error']}")

    # Persist conversation turn
    turn = {
        "id": uuid.uuid4().hex,
        "session_id": sid,
        "project_id": payload.project_id,
        "user_id": user.get("id"),
        "user_email": user.get("email"),
        "question": payload.question,
        "answer": answer,
        "ts": _now_iso(),
    }
    try:
        await db.digital_twin_qa_sessions.insert_one(turn)
    except Exception:  # noqa: BLE001
        pass

    # Persist a compact memory of this exchange so future questions get context
    try:
        await ai_memory.remember(
            user_id=user.get("email") or user["id"],
            scope="client_agent",
            content=f"Întrebare DT '{payload.question[:140]}' → răspuns: {answer[:200]}",
            summary=f"DT[{project.get('name', '?')}]: {payload.question[:140]}",
            source=f"dt_qa:{sid}",
        )
    except Exception:  # noqa: BLE001
        pass

    return {"answer": answer, "context_size": len(context), "session_id": sid, "provider": result.get("provider"), "model": result.get("model")}


@router.get("/suggestions")
async def suggestions(project_id: str = Query(min_length=3), user: dict = Depends(get_current_user)):
    """Întrebări sugerate DERIVATE din dovezile REALE ale proprietății (nu generice, nu decorative).

    Fiecare sugestie apare DOAR dacă evidența corespunzătoare există (camere, documente, lucrări,
    House Health, modele AI, pin-uri). Se trimit prin același pipeline Q&A pe dovezi."""
    project = await db.digital_twin_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(404, "Project not found")
    owner_ok = str(project.get("owner_id")) == str(user.get("id"))
    member_ok = user.get("id") in (project.get("members") or [])
    admin_ok = user.get("role") in ("admin", "operator")
    if not (owner_ok or member_ok or admin_ok):
        raise HTTPException(403, "Access denied")

    out = []

    # Evidence: 2D plans / rooms
    plan = await db.digital_twin_plans.find_one({"project_id": project_id, "rooms.0": {"$exists": True}})
    has_plan_rooms = bool(plan)

    # Evidence: uploaded models + AI models
    models_n = await db.digital_twin_models.count_documents({"project_id": project_id})
    pins_n = await db.digital_twin_pins.count_documents({"project_id": project_id})

    prop_id = project.get("property_id")
    prop = None
    twin_rooms = 0
    docs_n = works_n = 0
    ai_n = 0
    if prop_id:
        try:
            from bson import ObjectId as _OID
            prop = await db.properties.find_one({"_id": _OID(prop_id)})
        except Exception:  # noqa: BLE001
            prop = None
        twin = await db.twins.find_one({"property_id": prop_id}, {"rooms": 1})
        twin_rooms = len((twin or {}).get("rooms") or [])
        docs_n = await db.property_documents.count_documents({"property_id": prop_id})
        works_n = await db.requests.count_documents(
            {"property_id": prop_id, "status": {"$in": ["completed", "closed", "confirmed", "done"]}})
        ai_n = await db.digital_twin_models.count_documents({"property_id": prop_id, "source": "ai_generated"})

    if prop and (prop.get("surface") or prop.get("type")):
        out.append({"text": "Care este suprafața și tipul proprietății?", "based_on": "identitate proprietate"})
    if has_plan_rooms or twin_rooms:
        out.append({"text": "Câte camere sunt și ce tip are fiecare?", "based_on": "camere (plan 2D / twin)"})
        out.append({"text": "Ce suprafață totală însumează camerele?", "based_on": "arii camere"})
    if docs_n:
        out.append({"text": f"Ce documente există pentru proprietate? ({docs_n})", "based_on": "documente"})
    if works_n:
        out.append({"text": "Ce lucrări au fost finalizate până acum?", "based_on": "lucrări finalizate"})
    if prop and prop.get("health_score") is not None:
        out.append({"text": "Care este scorul House Health și ce îl influențează?", "based_on": "House Health"})
    if pins_n:
        out.append({"text": "Ce echipamente/anotări sunt marcate în model?", "based_on": f"{pins_n} pin-uri"})
    if ai_n:
        out.append({"text": "Ce modele 3D orientative (AI) există și cât sunt de complete?", "based_on": "modele AI (inferat)"})
    if models_n and not (has_plan_rooms or twin_rooms):
        out.append({"text": "Ce modele 3D au fost încărcate în proiect?", "based_on": "modele încărcate"})

    return {"suggestions": out[:6], "count": min(len(out), 6), "grounded": True}


@router.get("/history")
async def history(project_id: str = Query(min_length=3), limit: int = 30, user: dict = Depends(get_current_user)):
    """Recent Q&A turns for a project (visible to project members)."""
    project = await db.digital_twin_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(404, "Project not found")
    owner_ok = str(project.get("owner_id")) == str(user.get("id"))
    member_ok = user.get("id") in (project.get("members") or [])
    admin_ok = user.get("role") in ("admin", "operator")
    if not (owner_ok or member_ok or admin_ok):
        raise HTTPException(403, "Access denied")

    cur = db.digital_twin_qa_sessions.find({"project_id": project_id}).sort("ts", -1).limit(int(limit))
    items = []
    async for t in cur:
        t.pop("_id", None)
        items.append(t)
    return {"items": items, "total": len(items)}
