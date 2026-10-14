"""Rădăcini S9-A — Composesorate: asociații, registru de membri, participare, revendicări.

Colecții: `radacini_associations`, `radacini_assoc_members`, `radacini_assoc_claims`, `radacini_assoc_audit`
(jurnal doar cu adăugare, fără rută de ștergere). Helperii publici de la începutul fișierului sunt folosiți și de
`assoc_governance.py` / `assoc_accountability.py`; semnăturile lor sunt stabile.
"""
import csv
import io
import logging
import math
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, get_current_user, is_super_admin, serialize_doc
from .common import RadaciniRoute, get_optional_user, load_owners, mark_demo, now_iso, oid_or_404, safe_notify
from .staff import get_staff

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

DEFAULT_RULES: dict = {
    "aga_months_deadlines": ["04-30", "11-30"], "balance_deadline": "03-31", "budget_month": 11,
    "pasture_plan_deadline": "10-31", "convocation_days": 15, "quorum_first": "majority_shares",
    "second_convocation_day": 7,
    "major_quorum": {"members_majority": True, "shares_fraction": 0.6667},
    "extraordinary_petition": {"members_fraction": 0.25, "shares_fraction": 0.25},
    "agenda_petition": {"members_fraction": 0.10, "days_before": 5},
    "proxy_limits": {"max_members": 5, "max_shares_fraction": 0.05},
    "max_member_shares_fraction": 0.05, "contest_days": 15, "prescription_years": 5,
    "profit_split": {"council_max": 0.10, "reserve_max": 0.20, "charity_max": 0.20, "investment_max": 0.20},
    "info_request_days": 30, "censor_check_months": [3, 6, 9, 12],
}

COUNCIL_ROLES = ("president", "vice_president", "secretary", "cashier", "forest_pasture")
MEMBER_STATUSES = ("unknown", "contacted", "confirmed", "active", "deceased", "heir_pending")
ACTIVE_STATUSES = ("confirmed", "active")
ASSOC_TYPES = ("composesorat", "obste", "asociatie_pastorala")
MAX_IMPORT_ROWS = 5000
MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_SHARES = 1_000_000.0
_CODE_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,24}$")
_LIST_LIMIT = 20000


# ------------------------------------------------------------------------------------------ helperi publici

def merged_rules(assoc: dict) -> dict:
    """Regulile asociației peste valorile implicite (îmbinare pe un nivel pentru sub-dicționare)."""
    out: dict = {}
    custom = (assoc or {}).get("rules") or {}
    for k, default in DEFAULT_RULES.items():
        if isinstance(default, dict):
            merged = dict(default)
            if isinstance(custom.get(k), dict):
                merged.update(custom[k])
            out[k] = merged
        elif isinstance(default, list):
            out[k] = list(custom[k]) if isinstance(custom.get(k), list) else list(default)
        else:
            out[k] = custom[k] if k in custom and custom[k] is not None else default
    return out


async def load_assoc_or_404(assoc_id: str) -> dict:
    doc = await db.radacini_associations.find_one({"_id": oid_or_404(assoc_id)})
    if not doc:
        raise HTTPException(404, "Asociația nu există.")
    return doc


async def assoc_access(user: Optional[dict], assoc: dict) -> dict:
    """Rolul utilizatorului în asociație: manager | operator | council | censor | member | claimant | None."""
    res: dict = {"role": None, "council_role": None, "member": None}
    if not user:
        return res
    uid, aid = str(user["id"]), str(assoc["_id"])
    rows = await db.radacini_assoc_members.find({"association_id": aid, "user_id": uid}).limit(10).to_list(10)
    row = next((r for r in rows if r.get("council_role")), rows[0] if rows else None)
    if row:
        res["member"] = row
        res["council_role"] = row.get("council_role")
    staff = await get_staff(user)
    if staff and (staff["role"] == "manager" or is_super_admin(user)):
        res["role"] = "manager"
    elif staff and staff["role"] == "operator" and uid in (assoc.get("operator_user_ids") or []):
        res["role"] = "operator"
    elif row and row.get("council_role") == "censor":
        res["role"] = "censor"
    elif row and row.get("council_role") in COUNCIL_ROLES:
        res["role"] = "council"
    elif row and row.get("status") in ACTIVE_STATUSES:
        res["role"] = "member"
    else:
        pending = await db.radacini_assoc_claims.find_one({"association_id": aid, "user_id": uid, "status": "pending"})
        if pending:
            res["role"] = "claimant"
    return res


def require_assoc_roles(access: dict, *roles) -> None:
    if access.get("role") not in roles:
        raise HTTPException(403, "Nu ai drepturile necesare în această asociație.")


async def write_audit(assoc_id: str, actor: dict, actor_role: str, action: str, target_type: str,
                      target_id: Optional[str], before=None, after=None) -> None:
    """Jurnal de răspundere (doar adăugare). Nu aruncă niciodată."""
    try:
        doc = {
            "association_id": str(assoc_id),
            "actor_user_id": str(actor.get("id")) if actor else None,
            "actor_name": (actor or {}).get("name"),
            "actor_role": actor_role,
            "action": action,
            "target_type": target_type,
            "target_id": None if target_id is None else str(target_id),
            "at": now_iso(),
        }
        if before is not None:
            doc["before"] = serialize_doc(before) if isinstance(before, dict) else before
        if after is not None:
            doc["after"] = serialize_doc(after) if isinstance(after, dict) else after
        imp = (actor or {}).get("impersonation")
        if imp:
            doc["impersonated_by"] = {k: imp.get(k) for k in ("admin_id", "admin_email", "log_id")}
        await db.radacini_assoc_audit.insert_one(mark_demo(doc))
    except Exception:  # noqa: BLE001
        log.warning("radacini: jurnalul asociației nu a putut fi scris (%s)", action, exc_info=True)


async def _all_members(assoc_id: str) -> list:
    return await db.radacini_assoc_members.find({"association_id": str(assoc_id)}).limit(_LIST_LIMIT).to_list(_LIST_LIMIT)


async def active_members(assoc_id) -> list:
    """Rândurile confirmate/active, legate de un cont de utilizator."""
    rows = await _all_members(assoc_id)
    return [r for r in rows if r.get("status") in ACTIVE_STATUSES and r.get("user_id")]


def _shares(r: dict) -> float:
    try:
        v = float(r.get("shares") or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


async def share_totals(assoc_id) -> dict:
    rows = await _all_members(assoc_id)
    act = [r for r in rows if r.get("status") in ACTIVE_STATUSES and r.get("user_id")]
    return {
        "total_shares": round(sum(_shares(r) for r in rows), 8),
        "members_count": len(rows),
        "active_shares": round(sum(_shares(r) for r in act), 8),
        "active_members": len(act),
    }


# ------------------------------------------------------------------------------------------ utilitare

def _manage(access: dict) -> bool:
    return access["role"] in ("manager", "operator")


def _can_edit_registry(access: dict) -> bool:
    return access["role"] in ("manager", "operator", "council")


def _can_see_registry(access: dict) -> bool:
    return access["role"] in ("manager", "operator", "council", "censor")


def _member_view(r: dict) -> dict:
    out = serialize_doc(r)
    out.pop("association_id", None)
    return out


def _total_area(a: dict) -> float:
    total = 0.0
    for p in a.get("patrimony") or []:
        try:
            v = float(p.get("area_ha") or 0)
            if math.isfinite(v):
                total += v
        except (TypeError, ValueError):
            pass
    return round(total, 4)


def _public_view(a: dict, members_count: int) -> dict:
    cache = a.get("transparency_cache")
    score = cache.get("score") if isinstance(cache, dict) else (cache if isinstance(cache, (int, float)) else None)
    return {
        "id": str(a["_id"]),
        "name": a.get("name"),
        "type": a.get("type"),
        "localities": a.get("localities") or [],
        "description": a.get("description") or "",
        "total_area_ha": _total_area(a),
        "members_count": members_count,
        "transparency_score": score,
    }


async def _council_user_ids(assoc_id: str) -> list:
    rows = await db.radacini_assoc_members.find({"association_id": str(assoc_id)}).limit(_LIST_LIMIT).to_list(_LIST_LIMIT)
    return list({r["user_id"] for r in rows if r.get("user_id") and r.get("council_role") in COUNCIL_ROLES})


def _link(assoc_id) -> str:
    return f"/radacini/composesorate/{assoc_id}"


def _parse_shares(raw) -> float:
    s = str(raw if raw is not None else "").strip()
    if not s:
        raise ValueError("Cotele lipsesc.")
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            v = float(a.strip().replace(",", ".")) / float(b.strip().replace(",", "."))
        else:
            v = float(s.replace(",", "."))
    except (ValueError, ZeroDivisionError):
        raise ValueError("Cote invalide.") from None
    if not math.isfinite(v) or v <= 0:
        raise ValueError("Cotele trebuie să fie un număr pozitiv.")
    if v > MAX_SHARES:
        raise ValueError("Cotele sunt prea mari.")
    return round(v, 8)


def _clean_sources(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        v = [p for p in re.split(r"[|;]", v)]
    out = [str(x).strip()[:200] for x in v if str(x).strip()]
    if len(out) > 50:
        raise ValueError("Prea multe surse de cote (maximum 50).")
    return out


def _text(v: Optional[str], lo: int, hi: int, msg: str) -> str:
    v = (v or "").strip()
    if not (lo <= len(v) <= hi):
        raise ValueError(msg)
    return v


# ------------------------------------------------------------------------------------------ modele

class PatrimonyItem(BaseModel):
    cf: Optional[str] = None
    topo: Optional[str] = None
    area_ha: float
    category: Optional[str] = None
    toponym: Optional[str] = None

    @field_validator("area_ha")
    @classmethod
    def _a(cls, v):
        if not math.isfinite(v) or v < 0 or v > 1_000_000:
            raise ValueError("Suprafață invalidă.")
        return v

    @field_validator("cf", "topo", "category", "toponym")
    @classmethod
    def _s(cls, v):
        return None if v is None else v.strip()[:120]


def _check_rules(v: Optional[dict]) -> Optional[dict]:
    if v is None:
        return None
    for k, val in v.items():
        if k not in DEFAULT_RULES:
            raise ValueError(f"Regulă necunoscută: {k}.")
        if type(val) is not type(DEFAULT_RULES[k]) and not (
                isinstance(val, (int, float)) and isinstance(DEFAULT_RULES[k], (int, float))
                and not isinstance(val, bool)):
            raise ValueError(f"Valoare invalidă pentru regula {k}.")
    return v


def _clean_localities(v):
    out = [x.strip()[:80] for x in v if x and x.strip()]
    if len(out) > 30:
        raise ValueError("Prea multe localități.")
    return out


def _clean_legal(v):
    return {k: str(v[k]).strip()[:120] for k in ("cui", "court", "registered_at") if v.get(k)}


def _check_patrimony(v):
    if len(v) > 2000:
        raise ValueError("Prea multe elemente de patrimoniu.")
    return v


class AssocCreate(BaseModel):
    name: str
    type: str = "composesorat"
    localities: list[str] = []
    description: str = ""
    legal: dict = {}
    rules: Optional[dict] = None
    patrimony: list[PatrimonyItem] = []

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return _text(v, 3, 120, "Numele are între 3 și 120 de caractere.")

    @field_validator("type")
    @classmethod
    def _t(cls, v):
        if v not in ASSOC_TYPES:
            raise ValueError("Tip de asociație invalid.")
        return v

    @field_validator("localities")
    @classmethod
    def _l(cls, v):
        return _clean_localities(v)

    @field_validator("description")
    @classmethod
    def _d(cls, v):
        return (v or "").strip()[:4000]

    @field_validator("legal")
    @classmethod
    def _lg(cls, v):
        return _clean_legal(v)

    @field_validator("rules")
    @classmethod
    def _r(cls, v):
        return _check_rules(v)

    @field_validator("patrimony")
    @classmethod
    def _p(cls, v):
        return _check_patrimony(v)


class AssocPatch(BaseModel):
    name: Optional[str] = None
    localities: Optional[list[str]] = None
    description: Optional[str] = None
    legal: Optional[dict] = None
    rules: Optional[dict] = None
    patrimony: Optional[list[PatrimonyItem]] = None
    operator_user_ids: Optional[list[str]] = None

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return None if v is None else _text(v, 3, 120, "Numele are între 3 și 120 de caractere.")

    @field_validator("localities")
    @classmethod
    def _l(cls, v):
        return None if v is None else _clean_localities(v)

    @field_validator("description")
    @classmethod
    def _d(cls, v):
        return None if v is None else v.strip()[:4000]

    @field_validator("legal")
    @classmethod
    def _lg(cls, v):
        return None if v is None else _clean_legal(v)

    @field_validator("rules")
    @classmethod
    def _r(cls, v):
        return _check_rules(v)

    @field_validator("patrimony")
    @classmethod
    def _p(cls, v):
        return None if v is None else _check_patrimony(v)

    @field_validator("operator_user_ids")
    @classmethod
    def _o(cls, v):
        if v is None:
            return None
        if len(v) > 20 or any(not (isinstance(x, str) and len(x) == 24) for x in v):
            raise ValueError("Lista de operatori este invalidă.")
        return list(dict.fromkeys(v))


class MemberIn(BaseModel):
    code: str
    name: str
    shares: float
    sources: list[str] = []
    status: str = "unknown"
    locality: Optional[str] = None
    council_role: Optional[str] = None

    @field_validator("code")
    @classmethod
    def _c(cls, v):
        v = (v or "").strip()
        if not _CODE_RE.match(v):
            raise ValueError("Cod membru invalid (litere, cifre, - _ . , maximum 24).")
        return v

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return _text(v, 2, 120, "Numele are între 2 și 120 de caractere.")

    @field_validator("shares")
    @classmethod
    def _s(cls, v):
        return _parse_shares(v)

    @field_validator("sources")
    @classmethod
    def _src(cls, v):
        return _clean_sources(v)

    @field_validator("status")
    @classmethod
    def _st(cls, v):
        if v not in MEMBER_STATUSES:
            raise ValueError("Stare invalidă.")
        return v

    @field_validator("locality")
    @classmethod
    def _lc(cls, v):
        return None if not v else v.strip()[:80]

    @field_validator("council_role")
    @classmethod
    def _cr(cls, v):
        if v in (None, ""):
            return None
        if v not in COUNCIL_ROLES + ("censor",):
            raise ValueError("Funcție invalidă.")
        return v


class MemberPatch(BaseModel):
    name: Optional[str] = None
    shares: Optional[float] = None
    sources: Optional[list[str]] = None
    status: Optional[str] = None
    locality: Optional[str] = None
    council_role: Optional[str] = None
    clear_council_role: bool = False
    reason: Optional[str] = None
    document_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        return None if v is None else _text(v, 2, 120, "Numele are între 2 și 120 de caractere.")

    @field_validator("shares")
    @classmethod
    def _s(cls, v):
        return None if v is None else _parse_shares(v)

    @field_validator("sources")
    @classmethod
    def _src(cls, v):
        return None if v is None else _clean_sources(v)

    @field_validator("status")
    @classmethod
    def _st(cls, v):
        if v is not None and v not in MEMBER_STATUSES:
            raise ValueError("Stare invalidă.")
        return v

    @field_validator("locality")
    @classmethod
    def _lc(cls, v):
        return None if v is None else v.strip()[:80]

    @field_validator("council_role")
    @classmethod
    def _cr(cls, v):
        if v is not None and v not in COUNCIL_ROLES + ("censor",):
            raise ValueError("Funcție invalidă.")
        return v

    @field_validator("reason")
    @classmethod
    def _rs(cls, v):
        return None if v is None else v.strip()[:500]

    @field_validator("document_id")
    @classmethod
    def _doc(cls, v):
        return None if not v else v.strip()[:64]


class ClaimIn(BaseModel):
    kind: str
    member_code: Optional[str] = None
    name_on_record: Optional[str] = None
    relation: Optional[str] = None
    note: str = ""
    document_ids: list[str] = []

    @field_validator("kind")
    @classmethod
    def _k(cls, v):
        if v not in ("self", "heir"):
            raise ValueError("Tip de revendicare invalid.")
        return v

    @field_validator("member_code", "name_on_record", "relation")
    @classmethod
    def _s(cls, v):
        v = (v or "").strip()
        return v[:120] or None

    @field_validator("note")
    @classmethod
    def _nt(cls, v):
        return (v or "").strip()[:2000]

    @field_validator("document_ids")
    @classmethod
    def _docs(cls, v):
        if len(v) > 10:
            raise ValueError("Cel mult 10 documente.")
        return [str(x).strip()[:64] for x in v if str(x).strip()]


class DecideIn(BaseModel):
    decision: str
    note: Optional[str] = None
    member_id: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def _d(cls, v):
        if v not in ("approve", "reject"):
            raise ValueError("Decizie invalidă.")
        return v

    @field_validator("note")
    @classmethod
    def _n(cls, v):
        return None if v is None else (v.strip()[:1000] or None)


# ------------------------------------------------------------------------------------------ asociații

@router.post("/assoc", status_code=201)
async def create_assoc(body: AssocCreate, user: dict = Depends(get_current_user)):
    staff = await get_staff(user)
    if not (staff and staff["role"] == "manager"):
        raise HTTPException(403, "Doar managerul poate crea asociații.")
    block_in_impersonation(user, "crearea unei asociații")
    now = now_iso()
    doc = mark_demo({
        "name": body.name, "type": body.type, "localities": body.localities, "description": body.description,
        "legal": body.legal, "rules": body.rules or {},
        "patrimony": [p.model_dump() for p in body.patrimony],
        "operator_user_ids": [], "created_by": str(user["id"]), "created_at": now, "updated_at": now,
    })
    res = await db.radacini_associations.insert_one(doc)
    aid = str(res.inserted_id)
    await write_audit(aid, user, "manager", "assoc.create", "association", aid, after={"name": body.name})
    saved = await db.radacini_associations.find_one({"_id": res.inserted_id})
    return {"association": serialize_doc(saved)}


@router.get("/assoc")
async def list_assoc(locality: Optional[str] = Query(None, max_length=80), q: Optional[str] = Query(None, max_length=80)):
    docs = await db.radacini_associations.find({}).sort("name", 1).limit(200).to_list(200)
    if locality:
        loc = locality.strip().lower()
        docs = [d for d in docs if any(loc == str(x).lower() for x in d.get("localities") or [])]
    if q:
        ql = q.strip().lower()
        docs = [d for d in docs if ql in (d.get("name") or "").lower()]
    items = []
    for d in docs:
        n = await db.radacini_assoc_members.count_documents({"association_id": str(d["_id"])})
        items.append(_public_view(d, n))
    return {"items": items}


@router.get("/assoc/claims/mine")
async def my_claims(user: dict = Depends(get_current_user)):
    docs = await db.radacini_assoc_claims.find({"user_id": str(user["id"])}).sort("created_at", -1).limit(100).to_list(100)
    names: dict = {}
    for d in docs:
        aid = d["association_id"]
        if aid not in names:
            a = await db.radacini_associations.find_one({"_id": oid_or_404(aid)}, {"name": 1})
            names[aid] = (a or {}).get("name")
    return {"items": [{**serialize_doc(d), "association_name": names.get(d["association_id"])} for d in docs]}


async def _my_section(user: Optional[dict], assoc: dict) -> Optional[dict]:
    if not user:
        return None
    acc = await assoc_access(user, assoc)
    if acc["role"] is None:
        return None
    return {"role": acc["role"], "council_role": acc["council_role"],
            "member": _member_view(acc["member"]) if acc["member"] else None}


@router.get("/assoc/{assoc_id}")
async def get_assoc(assoc_id: str, user: Optional[dict] = Depends(get_optional_user)):
    assoc = await load_assoc_or_404(assoc_id)
    n = await db.radacini_assoc_members.count_documents({"association_id": str(assoc["_id"])})
    view = _public_view(assoc, n)
    view["legal"] = {k: v for k, v in (assoc.get("legal") or {}).items() if k in ("court", "registered_at")}
    view["patrimony"] = [{k: p.get(k) for k in ("cf", "topo", "area_ha", "category", "toponym")}
                         for p in assoc.get("patrimony") or []]
    view["rules"] = merged_rules(assoc)
    return {"association": view, "my": await _my_section(user, assoc)}


@router.patch("/assoc/{assoc_id}")
async def patch_assoc(assoc_id: str, body: AssocPatch, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "council")
    block_in_impersonation(user, "modificarea asociației")
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise HTTPException(400, "Nimic de modificat.")
    if acc["role"] == "council":
        if "operator_user_ids" in data:
            raise HTTPException(403, "Operatorii îi asignează managerul.")
        if "rules" in data and acc["council_role"] != "president":
            raise HTTPException(403, "Regulile le modifică președintele sau managerul.")
    elif acc["role"] == "manager" and "operator_user_ids" in data:
        pass
    before = {k: assoc.get(k) for k in data}
    data["updated_at"] = now_iso()
    await db.radacini_associations.update_one({"_id": assoc["_id"]}, {"$set": data})
    after = {k: v for k, v in data.items() if k != "updated_at"}
    await write_audit(assoc_id, user, acc["role"], "assoc.update", "association", assoc_id, before=before, after=after)
    saved = await db.radacini_associations.find_one({"_id": assoc["_id"]})
    n = await db.radacini_assoc_members.count_documents({"association_id": assoc_id})
    return {"association": _public_view(saved, n)}


@router.get("/assoc/{assoc_id}/me")
async def assoc_me(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    claims = await db.radacini_assoc_claims.find(
        {"association_id": assoc_id, "user_id": str(user["id"])}).sort("created_at", -1).limit(50).to_list(50)
    return {
        "role": acc["role"], "council_role": acc["council_role"],
        "member": _member_view(acc["member"]) if acc["member"] else None,
        "claims": [serialize_doc(c) for c in claims],
    }


# ------------------------------------------------------------------------------------------ registru

async def _find_member(assoc_id: str, mid: str) -> dict:
    row = await db.radacini_assoc_members.find_one({"_id": oid_or_404(mid)})
    if not row or row.get("association_id") != str(assoc_id):
        raise HTTPException(404, "Membrul nu există.")
    return row


@router.get("/assoc/{assoc_id}/members")
async def list_members(assoc_id: str, status: Optional[str] = Query(None, max_length=20),
                       q: Optional[str] = Query(None, max_length=80),
                       skip: int = Query(0, ge=0, le=100000), limit: int = Query(200, ge=1, le=1000),
                       user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    if not _can_see_registry(acc):
        raise HTTPException(403, "Registrul poate fi consultat doar de conducere, cenzori și operatori.")
    if status and status not in MEMBER_STATUSES:
        raise HTTPException(400, "Stare invalidă.")
    flt: dict = {"association_id": assoc_id}
    if status:
        flt["status"] = status
    rows = await db.radacini_assoc_members.find(flt).sort("code", 1).limit(_LIST_LIMIT).to_list(_LIST_LIMIT)
    if q:
        ql = q.strip().lower()
        rows = [r for r in rows if ql in (r.get("name") or "").lower() or ql in (r.get("code") or "").lower()]
    return {"items": [_member_view(r) for r in rows[skip:skip + limit]], "total": len(rows)}


async def _code_exists(assoc_id: str, code: str) -> bool:
    return await db.radacini_assoc_members.find_one({"association_id": assoc_id, "code": code}) is not None


def _new_member_doc(assoc_id: str, m: dict, now: str) -> dict:
    return mark_demo({
        "association_id": assoc_id, "code": m["code"], "name": m["name"], "shares": m["shares"],
        "sources": m.get("sources") or [], "status": m.get("status") or "unknown",
        "locality": m.get("locality"), "council_role": m.get("council_role"), "user_id": None,
        "created_at": now, "updated_at": now,
    })


@router.post("/assoc/{assoc_id}/members", status_code=201)
async def add_member(assoc_id: str, body: MemberIn, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "operator", "council")
    block_in_impersonation(user, "modificarea registrului")
    if await _code_exists(assoc_id, body.code):
        raise HTTPException(409, "Există deja un membru cu acest cod.")
    doc = _new_member_doc(assoc_id, body.model_dump(), now_iso())
    res = await db.radacini_assoc_members.insert_one(doc)
    saved = await db.radacini_assoc_members.find_one({"_id": res.inserted_id})
    await write_audit(assoc_id, user, acc["role"], "member.add", "member", str(res.inserted_id),
                      after={"code": body.code, "name": body.name, "shares": body.shares})
    return {"member": _member_view(saved)}


@router.post("/assoc/{assoc_id}/members/import")
async def import_members(assoc_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "operator", "council")
    block_in_impersonation(user, "importul registrului")
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(400, "Fișierul depășește 2 MB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "Fișierul trebuie să fie CSV în UTF-8.") from None
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        raise HTTPException(400, "Fișier gol.") from None
    for need in ("code", "name", "shares"):
        if need not in header:
            raise HTTPException(400, f"Lipsește coloana „{need}”.")
    idx = {h: i for i, h in enumerate(header)}

    def cell(row: list, key: str) -> str:
        i = idx.get(key)
        return row[i].strip() if i is not None and i < len(row) else ""

    existing = {r.get("code") for r in await _all_members(assoc_id)}
    seen: set = set()
    errors: list = []
    docs: list = []
    now = now_iso()
    count = 0
    for row in reader:
        line = reader.line_num
        if not row or not any(c.strip() for c in row):
            continue
        count += 1
        if count > MAX_IMPORT_ROWS:
            raise HTTPException(400, f"Maximum {MAX_IMPORT_ROWS} de rânduri per import.")
        try:
            code = cell(row, "code")
            if not _CODE_RE.match(code):
                raise ValueError("Cod membru invalid.")
            if code in existing or code in seen:
                raise ValueError(f"Cod duplicat: {code}.")
            name = _text(cell(row, "name"), 2, 120, "Numele are între 2 și 120 de caractere.")
            shares = _parse_shares(cell(row, "shares"))
            status = cell(row, "status").lower() or "unknown"
            if status not in MEMBER_STATUSES:
                raise ValueError(f"Stare invalidă: {status}.")
            sources = _clean_sources(cell(row, "sources"))
            docs.append(_new_member_doc(assoc_id, {
                "code": code, "name": name, "shares": shares, "sources": sources, "status": status,
                "locality": cell(row, "locality")[:80] or None}, now))
            seen.add(code)
        except ValueError as exc:
            errors.append({"line": line, "error": str(exc)})
    for i in range(0, len(docs), 500):
        await db.radacini_assoc_members.insert_many(docs[i:i + 500])
    await write_audit(assoc_id, user, acc["role"], "member.import", "member", None,
                      after={"imported": len(docs), "errors": len(errors)})
    return {"imported": len(docs), "errors": errors}


@router.patch("/assoc/{assoc_id}/members/{member_id}")
async def patch_member(assoc_id: str, member_id: str, body: MemberPatch, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "operator", "council")
    block_in_impersonation(user, "modificarea registrului")
    row = await _find_member(assoc_id, member_id)
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    reason, doc_id = data.pop("reason", None), data.pop("document_id", None)
    clear_role = data.pop("clear_council_role", False)
    if clear_role:
        data["council_role"] = None
    if not data:
        raise HTTPException(400, "Nimic de modificat.")
    shares_changed = "shares" in data and abs(data["shares"] - _shares(row)) > 1e-9
    if "shares" in data and not shares_changed:
        data.pop("shares")
    if shares_changed:
        if not reason or len(reason) < 3:
            raise HTTPException(400, "Schimbarea cotelor cere un motiv (reason).")
        if row.get("user_id") == str(user["id"]) and acc["role"] == "council":
            raise HTTPException(403, "Nu îți poți modifica singur cotele.")
    if not data:
        raise HTTPException(400, "Nimic de modificat.")
    before = {k: row.get(k) for k in data}
    data["updated_at"] = now_iso()
    await db.radacini_assoc_members.update_one({"_id": row["_id"]}, {"$set": data})
    after = {k: v for k, v in data.items() if k != "updated_at"}
    if reason:
        after["reason"] = reason
    if doc_id:
        after["document_id"] = doc_id
    await write_audit(assoc_id, user, acc["role"], "member.update", "member", member_id, before=before, after=after)
    saved = await db.radacini_assoc_members.find_one({"_id": row["_id"]})
    return {"member": _member_view(saved)}


@router.get("/assoc/{assoc_id}/participation")
async def participation(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    if acc["role"] in (None, "claimant"):
        raise HTTPException(403, "Doar membrii verificați și conducerea văd participarea.")
    rows = await _all_members(assoc_id)
    total = sum(_shares(r) for r in rows)
    act = [r for r in rows if r.get("status") in ACTIVE_STATUSES and r.get("user_id")]
    active_shares = sum(_shares(r) for r in act)
    by_status: dict = {}
    for r in rows:
        b = by_status.setdefault(r.get("status") or "unknown", {"count": 0, "shares": 0.0})
        b["count"] += 1
        b["shares"] = round(b["shares"] + _shares(r), 8)
    heir_of = {r.get("heir_of_member_id") for r in rows if r.get("heir_of_member_id")}
    deceased_unresolved = sum(1 for r in rows if r.get("status") == "deceased" and str(r["_id"]) not in heir_of)
    needed = total / 2
    return {
        "total_shares": round(total, 8), "members_count": len(rows), "active_members": len(act),
        "active_shares": round(active_shares, 8),
        "unknown_shares": round(sum(_shares(r) for r in rows if r.get("status") in ("unknown", "contacted")), 8),
        "deceased_unresolved": deceased_unresolved,
        "quorum_needed_shares": round(needed, 8),
        "quorum_rule": "mai mult de jumătate din cote",
        "quorum_met": active_shares > needed,
        "gap_to_quorum": round(max(0.0, needed - active_shares), 8),
        "by_status": by_status,
    }


# ------------------------------------------------------------------------------------------ revendicări

@router.post("/assoc/{assoc_id}/claims", status_code=201)
async def create_claim(assoc_id: str, body: ClaimIn, user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    block_in_impersonation(user, "revendicarea unei cote")
    uid = str(user["id"])
    if body.kind == "self":
        if not body.member_code:
            raise HTTPException(400, "Indică codul tău din registru (member_code).")
        row = await db.radacini_assoc_members.find_one({"association_id": assoc_id, "code": body.member_code})
        if not row:
            raise HTTPException(404, "Nu există acest cod în registru.")
        if row.get("user_id"):
            raise HTTPException(409, "Acest rând din registru este deja legat de un cont.")
        if await db.radacini_assoc_members.find_one(
                {"association_id": assoc_id, "user_id": uid, "status": {"$ne": "heir_pending"}}):
            raise HTTPException(409, "Ești deja legat de un rând din registru.")
    elif not (body.member_code or body.name_on_record):
        raise HTTPException(400, "Indică codul sau numele din registru al persoanei de la care moștenești.")
    if await db.radacini_assoc_claims.find_one({"association_id": assoc_id, "user_id": uid, "status": "pending"}):
        raise HTTPException(409, "Ai deja o revendicare în așteptare în această asociație.")
    doc = mark_demo({
        "association_id": assoc_id, "user_id": uid, "user_name": user.get("name"), "kind": body.kind,
        "member_code": body.member_code, "name_on_record": body.name_on_record, "relation": body.relation,
        "note": body.note, "document_ids": body.document_ids, "status": "pending", "created_at": now_iso(),
    })
    res = await db.radacini_assoc_claims.insert_one(doc)
    for cid in await _council_user_ids(assoc_id):
        if cid != uid:
            await safe_notify(cid, "Revendicare nouă în registru",
                              f"{user.get('name') or 'Un utilizator'} a depus o revendicare la {assoc.get('name')}.",
                              _link(assoc_id), "info")
    saved = await db.radacini_assoc_claims.find_one({"_id": res.inserted_id})
    return {"claim": serialize_doc(saved)}


@router.get("/assoc/{assoc_id}/claims")
async def list_claims(assoc_id: str, status: Optional[str] = Query(None, max_length=20),
                      user: dict = Depends(get_current_user)):
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "operator", "council", "censor")
    flt: dict = {"association_id": assoc_id}
    if status:
        if status not in ("pending", "approved", "rejected"):
            raise HTTPException(400, "Stare invalidă.")
        flt["status"] = status
    docs = await db.radacini_assoc_claims.find(flt).sort("created_at", -1).limit(500).to_list(500)
    owners = await load_owners(d.get("user_id") for d in docs)
    items = []
    for d in docs:
        v = serialize_doc(d)
        v["claimant_name"] = owners.get(d.get("user_id"), {}).get("name") or d.get("user_name") or ""
        items.append(v)
    return {"items": items}


@router.post("/assoc/claims/{claim_id}/decide")
async def decide_claim(claim_id: str, body: DecideIn, user: dict = Depends(get_current_user)):
    claim = await db.radacini_assoc_claims.find_one({"_id": oid_or_404(claim_id)})
    if not claim:
        raise HTTPException(404, "Revendicarea nu există.")
    assoc_id = claim["association_id"]
    assoc = await load_assoc_or_404(assoc_id)
    acc = await assoc_access(user, assoc)
    require_assoc_roles(acc, "manager", "operator", "council")
    block_in_impersonation(user, "decizia asupra unei revendicări")
    if claim.get("user_id") == str(user["id"]):
        raise HTTPException(403, "Nu poți decide propria revendicare.")
    if claim.get("status") != "pending":
        raise HTTPException(409, "Revendicarea a fost deja decisă.")
    if body.decision == "reject" and not body.note:
        raise HTTPException(400, "Respingerea cere o motivare (note).")
    now = now_iso()
    patch: dict = {"decided_by": str(user["id"]), "decided_at": now, "decision_note": body.note}
    member_id = None
    if body.decision == "approve":
        row = None
        if body.member_id:
            row = await _find_member(assoc_id, body.member_id)
        elif claim.get("member_code"):
            row = await db.radacini_assoc_members.find_one(
                {"association_id": assoc_id, "code": claim["member_code"]})
        if claim["kind"] == "self":
            if not row:
                raise HTTPException(400, "Indică rândul din registru (member_id).")
            if row.get("user_id"):
                raise HTTPException(409, "Rândul este deja legat de un cont.")
            if await db.radacini_assoc_members.find_one(
                    {"association_id": assoc_id, "user_id": claim["user_id"], "status": {"$ne": "heir_pending"}}):
                raise HTTPException(409, "Solicitantul este deja legat de un rând din registru.")
            status = row.get("status") if row.get("status") in ACTIVE_STATUSES else "confirmed"
            await db.radacini_assoc_members.update_one(
                {"_id": row["_id"]},
                {"$set": {"user_id": claim["user_id"], "status": status, "updated_at": now}})
            member_id = str(row["_id"])
            await write_audit(assoc_id, user, acc["role"], "claim.approve_self", "member", member_id,
                              before={"user_id": None, "status": row.get("status")},
                              after={"user_id": claim["user_id"], "status": status, "claim_id": claim_id})
        else:
            base = (row or {}).get("code") or "H"
            n = 1
            while await _code_exists(assoc_id, f"{base}-H{n}"):
                n += 1
            new = {
                "association_id": assoc_id, "code": f"{base}-H{n}",
                "name": claim.get("name_on_record") or claim.get("user_name") or "Moștenitor",
                "shares": 0.0, "sources": [], "status": "heir_pending", "locality": (row or {}).get("locality"),
                "council_role": None, "user_id": claim["user_id"], "relation": claim.get("relation"),
                "heir_of_member_id": str(row["_id"]) if row else None, "claim_id": claim_id,
                "created_at": now, "updated_at": now,
            }
            ins = await db.radacini_assoc_members.insert_one(mark_demo(new))
            member_id = str(ins.inserted_id)
            await write_audit(assoc_id, user, acc["role"], "claim.approve_heir", "member", member_id,
                              after={"code": new["code"], "heir_of_member_id": new["heir_of_member_id"],
                                     "claim_id": claim_id})
        patch["status"] = "approved"
        patch["member_id"] = member_id
    else:
        patch["status"] = "rejected"
        await write_audit(assoc_id, user, acc["role"], "claim.reject", "claim", claim_id,
                          after={"note": body.note})
    await db.radacini_assoc_claims.update_one({"_id": claim["_id"], "status": "pending"}, {"$set": patch})
    await safe_notify(claim["user_id"], "Revendicare " + ("aprobată" if body.decision == "approve" else "respinsă"),
                      f"Revendicarea ta la {assoc.get('name')} a fost "
                      + ("aprobată." if body.decision == "approve" else f"respinsă: {body.note}"),
                      _link(assoc_id), "info")
    saved = await db.radacini_assoc_claims.find_one({"_id": claim["_id"]})
    return {"claim": serialize_doc(saved)}
