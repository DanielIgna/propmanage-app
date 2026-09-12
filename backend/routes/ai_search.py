"""AI Search — interogări în limbaj natural peste datele platformei (modulul 13).

„arată-mi proiectele peste 20.000 lei", „specialiști fără portofoliu", „cereri din Cluj".
Claude traduce query-ul în filtre STRICT whitelisted → execuție Mongo sigură.
Fallback determinist pe pattern-uri comune dacă LLM-ul nu răspunde.
"""
import logging
import re
from typing import Any

from fastapi import APIRouter, Body, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/ai-search", tags=["ai-search"])
logger = logging.getLogger("propmanage.ai_search")

# Whitelist strict: colecție → câmpuri permise → operatori permiși
SCHEMA: dict[str, dict[str, Any]] = {
    "requests": {
        "fields": {
            "status": ["eq"], "category": ["eq"], "county": ["eq"],
            "budget": ["gte", "lte"], "escrow_amount": ["gte", "lte"],
            "escrow_status": ["eq"], "title": ["contains"], "created_at": ["gte", "lte"],
        },
        "display": ["title", "category", "county", "status", "budget", "escrow_amount", "escrow_status", "created_at"],
        "label": "Cereri",
    },
    "users": {
        "fields": {
            "role": ["eq"], "county": ["eq"], "specialty": ["eq", "missing"],
            "verified": ["eq"], "rating": ["gte", "lte"], "last_seen": ["lte", "gte"],
            "email": ["contains"], "name": ["contains"],
        },
        "display": ["name", "email", "role", "specialty", "county", "verified", "rating", "last_seen"],
        "label": "Utilizatori",
    },
    "payment_transactions": {
        "fields": {
            "amount": ["gte", "lte"], "payment_status": ["eq"], "user_email": ["contains"],
            "created_at": ["gte", "lte"],
        },
        "display": ["user_email", "amount", "currency", "payment_status", "created_at"],
        "label": "Plăți",
    },
}


def _build_mongo(collection: str, filters: list[dict]) -> dict[str, Any] | None:
    schema = SCHEMA.get(collection)
    if not schema:
        return None
    q: dict[str, Any] = {}
    for f in filters[:8]:
        field, op, value = f.get("field"), f.get("op"), f.get("value")
        allowed = schema["fields"].get(field)
        if not allowed or op not in allowed:
            continue
        if op == "eq":
            q[field] = value
        elif op == "gte":
            q.setdefault(field, {})["$gte"] = value
        elif op == "lte":
            q.setdefault(field, {})["$lte"] = value
        elif op == "contains":
            q[field] = {"$regex": re.escape(str(value)), "$options": "i"}
        elif op == "missing":
            q["$or"] = q.get("$or", []) + [{field: None}, {field: {"$exists": False}}, {field: ""}]
    return q


def _fallback_parse(query: str) -> dict[str, Any]:
    ql = query.lower()
    m = re.search(r"(\d[\d.,]*)\s*(lei|ron)", ql)
    amount = float(m.group(1).replace(".", "").replace(",", ".")) if m else None
    counties = ["cluj", "bucurești", "bucuresti", "ilfov", "brașov", "brasov", "timiș", "timis", "iași", "iasi", "constanța", "constanta"]
    county = next((c for c in counties if c in ql), None)
    county_map = {"bucuresti": "București", "brasov": "Brașov", "timis": "Timiș", "iasi": "Iași", "constanta": "Constanța", "cluj": "Cluj", "ilfov": "Ilfov", "bucurești": "București", "brașov": "Brașov", "timiș": "Timiș", "iași": "Iași", "constanța": "Constanța"}

    if "specialist" in ql or "specialiști" in ql:
        filters = [{"field": "role", "op": "eq", "value": "specialist"}]
        if "fără portofoliu" in ql or "fara portofoliu" in ql or "fără specialitate" in ql or "profil incomplet" in ql:
            filters.append({"field": "specialty", "op": "missing", "value": True})
        if county:
            filters.append({"field": "county", "op": "eq", "value": county_map[county]})
        return {"collection": "users", "filters": filters, "explain": "Fallback: specialiști filtrați determinist"}
    if "plăți" in ql or "plati" in ql or "escrow" in ql and amount:
        f = [{"field": "amount", "op": "gte", "value": amount}] if amount else []
        return {"collection": "payment_transactions", "filters": f, "explain": "Fallback: plăți"}
    filters = []
    if amount:
        filters.append({"field": "budget", "op": "gte", "value": amount})
    if county:
        filters.append({"field": "county", "op": "eq", "value": county_map[county]})
    if "inactiv" in ql:
        return {"collection": "users", "filters": [{"field": "role", "op": "eq", "value": "client"}], "explain": "Fallback: clienți (filtrare inactivitate limitată)"}
    return {"collection": "requests", "filters": filters, "explain": "Fallback: cereri filtrate determinist"}


@router.post("")
async def ai_search(query: str = Body(..., embed=True), _admin=Depends(require_role("admin"))):
    query = query.strip()[:300]
    parsed = None
    ai_generated = False
    try:
        from orchestrator.llm import claude_json
        schema_parts = []
        for col, s in SCHEMA.items():
            field_descs = ", ".join(f"{f}[{'/'.join(ops)}]" for f, ops in s["fields"].items())
            schema_parts.append(f"{col} (câmpuri: {field_descs})")
        schema_desc = "; ".join(schema_parts)
        system = (
            "Ești motorul AI Search al PropManage. Traduci întrebări în română în filtre structurate. "
            f"Colecții disponibile: {schema_desc}. Operatori: eq, gte, lte, contains, missing. "
            "Sume în lei = numere. Date ISO pentru created_at/last_seen (azi e 2026-06). "
            "Răspunde STRICT JSON: {\"collection\": str, \"filters\": [{\"field\": str, \"op\": str, \"value\": any}], "
            "\"explain\": str RO ≤120c despre cum ai interpretat}. Folosește DOAR câmpuri/operatori din listă."
        )
        result = await claude_json(system=system, prompt=f"Întrebare: {query}", session_prefix="ai-search")
        if result.get("collection") in SCHEMA:
            parsed = result
            ai_generated = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai-search] LLM fail: {e} — fallback")
    if not parsed:
        parsed = _fallback_parse(query)

    collection = parsed["collection"]
    mongo_q = _build_mongo(collection, parsed.get("filters") or [])
    schema = SCHEMA[collection]
    projection = {f: 1 for f in schema["display"]}
    projection["_id"] = 0
    rows = []
    async for doc in db[collection].find(mongo_q, projection).sort("created_at", -1).limit(50):
        rows.append(doc)

    return {
        "query": query,
        "collection": collection,
        "collection_label": schema["label"],
        "columns": schema["display"],
        "filters_applied": parsed.get("filters") or [],
        "explain": parsed.get("explain") or "",
        "ai_generated": ai_generated,
        "rows": rows,
        "total": len(rows),
    }
