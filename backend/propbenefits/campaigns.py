"""PropBenefits · Campaign Engine (PB-001.2) — campanii create de admin FĂRĂ cod."""
import uuid
from datetime import datetime, timezone

from db import db
from propbenefits.config import CAMPAIGN_KINDS, CAMPAIGN_STATUSES
from propbenefits import ledger, eligibility, membership


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_campaign(data: dict, partial: bool = False) -> dict:
    errors = []
    if not partial or "title" in data:
        if not str(data.get("title", "")).strip():
            errors.append("Titlul este obligatoriu.")
    if not partial or "kind" in data:
        if data.get("kind") not in CAMPAIGN_KINDS:
            errors.append(f"kind invalid — permise: {', '.join(CAMPAIGN_KINDS)}")
    if "status" in data and data["status"] not in CAMPAIGN_STATUSES:
        errors.append(f"status invalid — permise: {', '.join(CAMPAIGN_STATUSES)}")
    for k in ("budget_total", "max_claims", "max_per_user", "priority"):
        if k in data and data[k] is not None:
            try:
                if float(data[k]) < 0:
                    errors.append(f"{k} nu poate fi negativ.")
            except (TypeError, ValueError):
                errors.append(f"{k} trebuie să fie numeric.")
    if "priority" in data and data.get("priority") and not (1 <= int(data["priority"]) <= 5):
        errors.append("priority trebuie să fie 1-5.")
    if not partial or "benefit" in data:
        b = data.get("benefit") or {}
        if not str(b.get("title", "")).strip():
            errors.append("benefit.title este obligatoriu.")
    if errors:
        raise ValueError(" · ".join(errors))
    return data


ALLOWED_FIELDS = ("title", "description", "kind", "status", "starts_at", "ends_at", "city",
                  "budget_total", "max_claims", "max_per_user", "priority",
                  "eligibility", "estimated_impact", "benefit")


async def create_campaign(data: dict, created_by: str) -> dict:
    validate_campaign(data)
    doc = {k: data.get(k) for k in ALLOWED_FIELDS}
    doc.update({
        "id": uuid.uuid4().hex[:12],
        "status": data.get("status", "draft"),
        "priority": int(data.get("priority") or 3),
        "budget_total": float(data.get("budget_total") or 0),
        "budget_used": 0.0,
        "max_claims": int(data.get("max_claims") or 0),
        "claims_count": 0,
        "max_per_user": int(data.get("max_per_user") or 1),
        "eligibility": data.get("eligibility") or {},
        "estimated_impact": data.get("estimated_impact") or {},
        "created_by": created_by, "created_at": _now(), "updated_at": _now(),
    })
    await db.pb_campaigns.insert_one({**doc})
    return doc


async def update_campaign(cid: str, patch: dict) -> dict:
    validate_campaign(patch, partial=True)
    clean = {k: v for k, v in patch.items() if k in ALLOWED_FIELDS}
    if not clean:
        raise ValueError("Niciun câmp valid de actualizat.")
    clean["updated_at"] = _now()
    res = await db.pb_campaigns.update_one({"id": cid}, {"$set": clean})
    if not res.matched_count:
        raise LookupError("Campanie inexistentă.")
    return await db.pb_campaigns.find_one({"id": cid}, {"_id": 0})


async def list_campaigns(status: str = None, kind: str = None) -> list:
    q = {}
    if status:
        q["status"] = status
    if kind:
        q["kind"] = kind
    return await db.pb_campaigns.find(q, {"_id": 0}).sort([("priority", -1), ("created_at", -1)]).to_list(200)


def _in_period(c: dict) -> bool:
    now = _now()
    if c.get("starts_at") and c["starts_at"] > now:
        return False
    if c.get("ends_at") and c["ends_at"] < now:
        return False
    return True


async def active_campaigns() -> list:
    docs = await db.pb_campaigns.find({"status": "active"}, {"_id": 0}).to_list(200)
    return [c for c in docs if _in_period(c)]


async def claim(user: dict, campaign_id: str) -> dict:
    """Revendicare beneficiu dintr-o campanie — verifică eligibilitate, limite, buget (atomic)."""
    c = await db.pb_campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not c:
        return {"error": "Campanie inexistentă.", "code": 404}
    if c["status"] != "active" or not _in_period(c):
        return {"error": "Campania nu este activă.", "code": 409}
    if c.get("kind") == "community":
        return {"error": "Beneficiul de comunitate se acordă automat la activarea invitatului.", "code": 409}

    ctx = await eligibility.user_context(user)
    mem = await membership.compute_membership(ctx)
    ranks = await membership.level_ranks()
    ev = eligibility.evaluate(ctx, c.get("eligibility") or {}, mem["level"]["rank"], ranks)
    if not ev["eligible"]:
        return {"error": "Nu ești încă eligibil pentru această oportunitate.",
                "failed": ev["failed"], "code": 403}

    if c.get("max_per_user") and await ledger.user_claims_for_campaign(ctx["uid"], campaign_id) >= c["max_per_user"]:
        return {"error": "Ai folosit deja acest beneficiu.", "code": 409}

    value = float((c.get("benefit") or {}).get("value_estimate", 0))
    guard = {"id": campaign_id, "status": "active"}
    if c.get("max_claims"):
        guard["claims_count"] = {"$lt": c["max_claims"]}
    if c.get("budget_total"):
        guard["budget_used"] = {"$lte": c["budget_total"] - value}
    res = await db.pb_campaigns.update_one(guard, {"$inc": {"claims_count": 1, "budget_used": value}})
    if not res.modified_count:
        return {"error": "Campania și-a atins limita de participanți sau bugetul.", "code": 409}

    entry = await ledger.grant(ctx["uid"], c.get("benefit") or {}, source="campaign",
                               campaign_id=campaign_id)
    return {"ok": True, "benefit": entry}
