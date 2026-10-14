"""Composesorate (S9 C): calendar statutar, finanțe și distribuții cu prescriere, scor de transparență, jurnal, alerte membru."""
import calendar
import inspect
import logging
import math
from datetime import date, datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .assoc_core import (  # noqa: F401
    DEFAULT_RULES, merged_rules, load_assoc_or_404, assoc_access, require_assoc_roles, write_audit, active_members,
    share_totals,
)
from .bridge import block_in_impersonation, db, get_current_user
from .common import RadaciniRoute, now_iso, oid_or_404, today_bucharest
from .legal_terms import require_terms

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

ACTIVE_STATUSES = ("confirmed", "active")
WRITER_ROLES = ("manager", "operator", "council")
OBLIGATION_ROLES = ("manager", "operator", "council")
CASHIER_COUNCIL = ("president", "cashier")
NEAR_DAYS = 365
EPS = 0.01


# ---------- utilitare ----------
async def _maybe(v):
    return await v if inspect.isawaitable(v) else v


def _aid(assoc: dict) -> str:
    return str(assoc.get("_id") or assoc.get("id"))


def _aid_q(aid: str) -> dict:
    vals = [aid]
    if ObjectId.is_valid(aid):
        vals.append(ObjectId(aid))
    return {"$in": vals}


async def _load(assoc_id: str) -> dict:
    return await _maybe(load_assoc_or_404(assoc_id))


async def _access(user: dict, assoc: dict) -> dict:
    return await _maybe(assoc_access(user, assoc)) or {"role": None}


async def _rules(assoc: dict) -> dict:
    try:
        r = await _maybe(merged_rules(assoc))
    except Exception:  # noqa: BLE001
        r = None
    return r or {**DEFAULT_RULES, **(assoc.get("rules") or {})}


async def _audit(user: dict, assoc: dict, access: dict, action: str, target_type: str, target_id, before=None, after=None):
    """Adaptor tolerant la semnătura write_audit (mapare după numele parametrilor)."""
    cands = {
        "assoc_id": _aid(assoc), "association_id": _aid(assoc), "assoc": assoc, "association": assoc,
        "user": user, "actor": user, "actor_user_id": str(user.get("id")), "actor_role": access.get("role"),
        "role": access.get("role"), "access": access, "action": action, "target_type": target_type,
        "target_id": str(target_id), "before": before, "after": after,
    }
    fn = write_audit
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        params = []
    kwargs = {p.name: cands[p.name] for p in params if p.name in cands}
    missing = [p.name for p in params if p.default is inspect.Parameter.empty
               and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) and p.name not in kwargs]
    if params and not missing:
        await _maybe(fn(**kwargs))
        return
    await _maybe(fn(_aid(assoc), user, action, target_type, str(target_id), before, after))


def _parse_date(s) -> Optional[date]:
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    if not isinstance(s, str) or len(s) < 10:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 feb
        return d.replace(year=d.year + years, day=28)


def _deadline(year: int, md: str) -> Optional[date]:
    try:
        m, d = md.split("-")
        return date(year, int(m), int(d))
    except (ValueError, AttributeError):
        return None


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _num(v, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise HTTPException(400, f"{name}: valoare numerică pozitivă necesară.")
    return round(float(v), 2)


def _can_write(access: dict, council_roles=None) -> bool:
    role = access.get("role")
    if role in ("manager", "operator"):
        return True
    if role == "council":
        return council_roles is None or access.get("council_role") in council_roles
    return False


async def _members(aid: str) -> list:
    return await db.radacini_assoc_members.find({"association_id": _aid_q(aid)}).to_list(20000)


# ---------- calendar ----------
def _status(deadline: date, evidence_date: Optional[date], today: date) -> str:
    if evidence_date is not None:
        return "done" if evidence_date <= deadline else "late"
    return "missed" if today > deadline else "upcoming"


async def compute_obligations(assoc: dict, year: int, rules: dict) -> list:
    aid = _aid(assoc)
    q = {"association_id": _aid_q(aid)}
    today = today_bucharest()
    meetings = await db.radacini_assoc_meetings.find(q).to_list(2000)
    docs = await db.radacini_assoc_documents.find(q).to_list(5000)
    manual = await db.radacini_assoc_obligation_evidence.find({**q, "year": year}).to_list(500)
    man = {}
    for e in manual:
        e = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in e.items()}
        e["id"] = e.pop("_id", None)
        man.setdefault(e.get("key"), []).append(e)

    def man_date(key):
        ds = [(_parse_date(e.get("date")) or _parse_date(e.get("created_at"))) for e in man.get(key, [])]
        ds = [d for d in ds if d]
        return min(ds) if ds else None

    def first(dates):
        dates = [d for d in dates if d]
        return min(dates) if dates else None

    def meeting_dates(kind):
        return [_parse_date(m.get("date")) for m in meetings if m.get("kind") == kind and not m.get("cancelled")
                and (_parse_date(m.get("date")) or date.min).year == year]

    def doc_dates(typ, lo=None, hi=None):
        out = []
        for d in docs:
            dd = _parse_date(d.get("date"))
            if d.get("type") != typ or not dd or dd.year != year:
                continue
            if lo and dd < lo or hi and dd > hi:
                continue
            out.append(dd)
        return out

    items = []

    def add(key, title, kind, deadline, ev_date, source):
        if not deadline:
            return
        m = man_date(key)
        if ev_date is None or (m and m < ev_date):
            ev_date, source = (m, "manual") if m else (ev_date, source)
        items.append({
            "key": key, "title": title, "kind": kind, "year": year, "deadline": deadline.isoformat(),
            "status": _status(deadline, ev_date, today), "evidence_date": ev_date.isoformat() if ev_date else None,
            "evidence_source": source if ev_date else None, "manual_evidence": man.get(key, []),
        })

    aga = sorted(meeting_dates("aga_ordinary"))
    for md in rules.get("aga_months_deadlines") or []:
        dl = _deadline(year, md)
        if not dl:
            continue
        # ultima ședință ținută până la termen, altfel prima de după (târziu)
        before = [d for d in aga if d <= dl]
        ev = before[0] if before else (aga[0] if aga else None)
        add(f"aga_ordinary_{md}", f"AGA ordinară până la {md}", "aga", dl, ev, "meeting")
    if rules.get("balance_deadline"):
        add("balance", "Bilanț aprobat/publicat", "balance", _deadline(year, rules["balance_deadline"]),
            first(doc_dates("balance")), "document")
    bm = int(rules.get("budget_month") or 11)
    bud = [_parse_date(d.get("date")) for d in docs if "buget" in str(d.get("title") or "").lower()
           and (_parse_date(d.get("date")) or date.min).year == year]
    for m in meetings:
        md = _parse_date(m.get("date"))
        if md and md.year == year and any("buget" in str((x or {}).get("title") or "").lower()
                                           for x in (m.get("decisions") or [])):
            bud.append(md)
    add("budget", "Buget aprobat", "budget", _month_end(year, bm), first(bud), "meeting_or_document")
    if rules.get("pasture_plan_deadline"):
        add("pasture_plan", "Plan de pășunat", "pasture_plan", _deadline(year, rules["pasture_plan_deadline"]), None, "manual")
    for qm in rules.get("censor_check_months") or [3, 6, 9, 12]:
        try:
            qm = int(qm)
        except (TypeError, ValueError):
            continue
        lo, hi = date(year, max(qm - 2, 1), 1), _month_end(year, qm)
        add(f"censor_q{(qm - 1) // 3 + 1}", f"Raport cenzori (luna {qm})", "censor", hi,
            first(doc_dates("censor_report", lo, hi)), "document")
    add("registry_update", "Actualizarea anuală a registrului", "registry", date(year, 12, 31), None, "manual")
    return items


def _year_arg(year: Optional[int]) -> int:
    y = year or today_bucharest().year
    if not 2000 <= y <= 2100:
        raise HTTPException(400, "An invalid.")
    return y


@router.get("/assoc/{assoc_id}/obligations")
async def obligations(assoc_id: str, year: Optional[int] = None, user: dict = Depends(get_current_user)):
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    if not acc.get("role"):
        raise HTTPException(403, "Acces interzis.")
    y = _year_arg(year)
    items = await compute_obligations(assoc, y, await _rules(assoc))
    summary = {s: sum(1 for i in items if i["status"] == s) for s in ("done", "late", "missed", "upcoming")}
    return {"year": y, "items": items, "summary": summary}


class EvidenceIn(BaseModel):
    year: int
    note: str
    document_id: Optional[str] = None
    date: Optional[str] = None

    @field_validator("note")
    @classmethod
    def _note(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 1000:
            raise ValueError("Nota are între 3 și 1000 de caractere.")
        return v

    @field_validator("date")
    @classmethod
    def _d(cls, v):
        if v is not None and _parse_date(v) is None:
            raise ValueError("Data trebuie să fie AAAA-LL-ZZ.")
        return v


@router.post("/assoc/{assoc_id}/obligations/{key}/evidence")
async def add_evidence(assoc_id: str, key: str, body: EvidenceIn, user: dict = Depends(require_terms)):
    block_in_impersonation(user)
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    if acc.get("role") not in OBLIGATION_ROLES:
        raise HTTPException(403, "Doar CA, operatorul sau managerul pot adăuga dovezi.")
    if not 2000 <= body.year <= 2100:
        raise HTTPException(400, "An invalid.")
    known = {i["key"] for i in await compute_obligations(assoc, body.year, await _rules(assoc))}
    if key not in known:
        raise HTTPException(404, "Obligație necunoscută.")
    doc = {
        "association_id": _aid(assoc), "key": key, "year": body.year, "note": body.note,
        "document_id": body.document_id, "date": body.date or today_bucharest().isoformat(),
        "created_by": str(user["id"]), "created_at": now_iso(),
    }
    res = await db.radacini_assoc_obligation_evidence.insert_one(doc)
    await _audit(user, assoc, acc, "obligation_evidence", "obligation", f"{key}:{body.year}", after={
        k: doc[k] for k in ("key", "year", "note", "document_id", "date")})
    return {"id": str(res.inserted_id), "key": key, "year": body.year, "date": doc["date"]}


# ---------- finanțe ----------
class FinanceYearIn(BaseModel):
    year: int
    revenues: dict = {}
    expenses: dict = {}
    net_profit: float
    split: dict


def _split_check(body: FinanceYearIn, rules: dict) -> dict:
    if not 2000 <= body.year <= 2100:
        raise HTTPException(400, "An invalid.")
    for name, d in (("revenues", body.revenues), ("expenses", body.expenses)):
        for k, v in d.items():
            _num(v, f"{name}.{k}")
    net = _num(body.net_profit, "net_profit")
    caps = rules.get("profit_split") or DEFAULT_RULES.get("profit_split") or {}
    sp = {k: _num(body.split.get(k, 0), f"split.{k}") for k in ("council", "reserve", "charity", "investment", "members")}
    for k in ("council", "reserve", "charity", "investment"):
        cap = caps.get(f"{k}_max")
        if cap is not None and sp[k] > net * cap + EPS:
            raise HTTPException(400, f"Partea «{k}» depășește maximul statutar ({cap * 100:g}% din profitul net).")
    others = sp["council"] + sp["reserve"] + sp["charity"] + sp["investment"]
    if others > net + EPS:
        raise HTTPException(400, "Părțile alocate depășesc profitul net.")
    if abs(sp["members"] - (net - others)) > EPS:
        raise HTTPException(400, "Suma pentru membri trebuie să fie profitul net minus celelalte părți.")
    return {"net_profit": net, "split": sp}


@router.post("/assoc/{assoc_id}/finance/years")
async def create_finance_year(assoc_id: str, body: FinanceYearIn, user: dict = Depends(require_terms)):
    block_in_impersonation(user)
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    if not _can_write(acc, CASHIER_COUNCIL):
        raise HTTPException(403, "Doar președintele, casierul, operatorul sau managerul pot înregistra anul financiar.")
    checked = _split_check(body, await _rules(assoc))
    aid = _aid(assoc)
    if await db.radacini_assoc_finance_years.find_one({"association_id": aid, "year": body.year}):
        raise HTTPException(409, "Anul financiar există deja.")
    doc = {
        "association_id": aid, "year": body.year, "revenues": body.revenues, "expenses": body.expenses,
        **checked, "created_by": str(user["id"]), "created_at": now_iso(),
    }
    res = await db.radacini_assoc_finance_years.insert_one(doc)
    await _audit(user, assoc, acc, "finance_year_create", "finance_year", f"{aid}:{body.year}", after={
        "year": body.year, "net_profit": checked["net_profit"], "split": checked["split"]})
    return {"id": str(res.inserted_id), "year": body.year, **checked}


class DistributeIn(BaseModel):
    aga_date: str

    @field_validator("aga_date")
    @classmethod
    def _d(cls, v):
        if _parse_date(v) is None:
            raise ValueError("Data AGA trebuie să fie AAAA-LL-ZZ.")
        return v[:10]


@router.post("/assoc/{assoc_id}/finance/years/{year}/distribute")
async def distribute(assoc_id: str, year: int, body: DistributeIn, user: dict = Depends(require_terms)):
    block_in_impersonation(user)
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    if not _can_write(acc, CASHIER_COUNCIL):
        raise HTTPException(403, "Doar președintele, casierul, operatorul sau managerul pot repartiza.")
    aid = _aid(assoc)
    fy = await db.radacini_assoc_finance_years.find_one({"association_id": aid, "year": year})
    if not fy:
        raise HTTPException(404, "Anul financiar nu există.")
    if await db.radacini_assoc_distributions.find_one({"association_id": aid, "year": year}):
        raise HTTPException(409, "Repartizarea pentru acest an a fost deja făcută.")
    rules = await _rules(assoc)
    total = round(float((fy.get("split") or {}).get("members") or 0), 2)
    rows = [m for m in await _members(aid) if (m.get("shares") or 0) > 0]
    total_shares = sum(float(m["shares"]) for m in rows)
    if not rows or total_shares <= 0:
        raise HTTPException(400, "Registrul nu are membri cu cote.")
    prescribes = _add_years(date.fromisoformat(body.aga_date), int(rules.get("prescription_years") or 5)).isoformat()
    amounts = [round(total * float(m["shares"]) / total_shares, 2) for m in rows]
    diff = round(total - sum(amounts), 2)
    if diff:
        amounts[max(range(len(rows)), key=lambda i: float(rows[i]["shares"]))] += diff
    now = now_iso()
    docs = [{
        "association_id": aid, "year": year, "member_id": str(m["_id"]), "member_code": m.get("code"),
        "amount": round(a, 2), "aga_date": body.aga_date, "prescribes_at": prescribes, "paid_at": None,
        "created_at": now,
    } for m, a in zip(rows, amounts)]
    await db.radacini_assoc_distributions.insert_many(docs)
    await db.radacini_assoc_finance_years.update_one(
        {"_id": fy["_id"]}, {"$set": {"distributed_at": now, "aga_date": body.aga_date}})
    await _audit(user, assoc, acc, "finance_distribute", "finance_year", f"{aid}:{year}", after={
        "year": year, "members": len(docs), "total": total, "prescribes_at": prescribes})
    return {"year": year, "members": len(docs), "total": total, "prescribes_at": prescribes}


def _dist_out(d: dict, today: date) -> dict:
    p = _parse_date(d.get("prescribes_at"))
    out = {
        "id": str(d["_id"]), "year": d.get("year"), "member_id": d.get("member_id"), "member_code": d.get("member_code"),
        "amount": d.get("amount"), "prescribes_at": d.get("prescribes_at"), "paid_at": d.get("paid_at"),
        "days_to_prescription": (p - today).days if p else None,
    }
    out["near_prescription"] = bool(not out["paid_at"] and p and (p - today).days <= NEAR_DAYS)
    return out


def _year_out(y: dict) -> dict:
    return {k: y.get(k) for k in ("year", "revenues", "expenses", "net_profit", "split", "distributed_at", "aga_date")}


@router.get("/assoc/{assoc_id}/finance")
async def finance(assoc_id: str, user: dict = Depends(get_current_user)):
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    role = acc.get("role")
    if role not in ("manager", "operator", "council", "censor", "member"):
        raise HTTPException(403, "Acces interzis.")
    aid = _aid(assoc)
    today = today_bucharest()
    years = await db.radacini_assoc_finance_years.find({"association_id": aid}).sort("year", -1).to_list(100)
    full = role in ("manager", "operator", "council", "censor")
    if full:
        dists = await db.radacini_assoc_distributions.find({"association_id": aid}).to_list(50000)
    else:
        mid = str((acc.get("member") or {}).get("_id") or "")
        dists = await db.radacini_assoc_distributions.find({"association_id": aid, "member_id": mid}).to_list(500) if mid else []
    out = [_dist_out(d, today) for d in dists]
    res = {"years": [_year_out(y) for y in years], "distributions": out}
    if full:
        unpaid = [d for d in out if not d["paid_at"]]
        near = [d for d in unpaid if d["near_prescription"]]
        res["totals"] = {
            "unpaid_count": len(unpaid), "unpaid_amount": round(sum(d["amount"] or 0 for d in unpaid), 2),
            "near_prescription_count": len(near), "near_prescription_amount": round(sum(d["amount"] or 0 for d in near), 2),
        }
    else:
        res["alerts"] = [d for d in out if d["near_prescription"]]
    return res


@router.post("/assoc/distributions/{did}/paid")
async def mark_paid(did: str, user: dict = Depends(require_terms)):
    block_in_impersonation(user)
    d = await db.radacini_assoc_distributions.find_one({"_id": oid_or_404(did)})
    if not d:
        raise HTTPException(404, "Nu există.")
    assoc = await _load(str(d.get("association_id")))
    acc = await _access(user, assoc)
    if not _can_write(acc, CASHIER_COUNCIL):
        raise HTTPException(403, "Doar președintele, casierul sau managerul pot marca plata.")
    if d.get("paid_at"):
        raise HTTPException(409, "Suma este deja marcată ca plătită.")
    now = now_iso()
    await db.radacini_assoc_distributions.update_one(
        {"_id": d["_id"]}, {"$set": {"paid_at": now, "paid_by": str(user["id"])}})
    await _audit(user, assoc, acc, "distribution_paid", "distribution", did,
                 before={"paid_at": None}, after={"paid_at": now, "amount": d.get("amount"), "member_code": d.get("member_code")})
    return {"id": did, "paid_at": now}


# ---------- transparență ----------
async def compute_transparency(assoc: dict, rules: dict) -> dict:
    aid = _aid(assoc)
    q = {"association_id": _aid_q(aid)}
    today = today_bucharest()
    since = today - timedelta(days=365)
    # 1. obligații în ultimele 12 luni
    due = []
    for y in {today.year, today.year - 1}:
        for it in await compute_obligations(assoc, y, rules):
            dl = _parse_date(it["deadline"])
            if dl and since <= dl <= today:
                due.append(it)
    if due:
        ob = sum(1 for i in due if i["status"] == "done") / len(due)
        ob_txt = f"{sum(1 for i in due if i['status'] == 'done')} din {len(due)} obligații cu termen în ultimele 12 luni au fost îndeplinite la timp."
    else:
        ob, ob_txt = 0.5, "Nu există obligații cu termen în ultimele 12 luni (valoare neutră)."
    # 2. documente obligatorii
    docs = await db.radacini_assoc_documents.find(q).to_list(5000)
    limit = today - timedelta(days=13 * 30 + 5)

    def has(typ, recent):
        for d in docs:
            dd = _parse_date(d.get("date"))
            if d.get("type") != typ:
                continue
            if not recent or (dd and dd >= limit):
                return True
        return False

    checks = [("statut", has("statut", False), "Statutul"), ("pv_aga", has("pv_aga", True), "Ultimul PV AGA (13 luni)"),
              ("balance", has("balance", True), "Ultimul bilanț (13 luni)"),
              ("censor_report", has("censor_report", True), "Raportul cenzorilor (13 luni)")]
    dc = sum(1 for c in checks if c[1]) / len(checks)
    dc_txt = "Documente publicate: " + ", ".join(f"{n} {'da' if ok else 'lipsește'}" for _, ok, n in checks) + "."
    # 3. cereri de informații
    reqs = await db.radacini_assoc_requests.find(q).to_list(5000)
    judged, ok_n = 0, 0
    for r in reqs:
        due_at, ans = _parse_date(r.get("due_at")), _parse_date(r.get("answered_at"))
        if ans and due_at:
            judged += 1
            ok_n += ans <= due_at
        elif not ans and due_at and due_at < today:
            judged += 1
    rq = ok_n / judged if judged else 1.0
    rq_txt = (f"{ok_n} din {judged} cereri de informații au primit răspuns în termen." if judged
              else "Nu există cereri cu termen scadent (valoare maximă).")
    # 4. participare
    rows = await _members(aid)
    total = sum(float(m.get("shares") or 0) for m in rows)
    act = sum(float(m.get("shares") or 0) for m in rows if m.get("status") in ACTIVE_STATUSES)
    pt = act / total if total > 0 else 0.0
    pt_txt = f"Cote reprezentate de membri activi: {pt * 100:.0f}% din total."
    comps = [
        {"key": "obligations", "label": "Obligații la timp", "weight": 0.40, "value": round(ob, 4), "explanation": ob_txt},
        {"key": "documents", "label": "Documente obligatorii publicate", "weight": 0.25, "value": round(dc, 4), "explanation": dc_txt},
        {"key": "requests", "label": "Cereri răspunse în termen", "weight": 0.20, "value": round(rq, 4), "explanation": rq_txt},
        {"key": "participation", "label": "Participare", "weight": 0.15, "value": round(pt, 4), "explanation": pt_txt},
    ]
    score = int(round(sum(c["weight"] * c["value"] for c in comps) * 100))
    for c in comps:
        c["points"] = round(c["weight"] * c["value"] * 100, 1)
    return {"score": max(0, min(100, score)), "components": comps}


@router.get("/assoc/{assoc_id}/transparency")
async def transparency(assoc_id: str):
    assoc = await _load(assoc_id)
    res = await compute_transparency(assoc, await _rules(assoc))
    at = now_iso()
    await db.radacini_associations.update_one(
        {"_id": assoc["_id"]}, {"$set": {"transparency_cache": {"score": res["score"], "at": at}}})
    return {**res, "at": at}


# ---------- jurnal ----------
@router.get("/assoc/{assoc_id}/audit")
async def audit(assoc_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    assoc = await _load(assoc_id)
    acc = await _access(user, assoc)
    role = acc.get("role")
    if role not in ("manager", "operator", "council", "censor", "member"):
        raise HTTPException(403, "Acces interzis.")
    limit = max(1, min(limit, 500))
    rows = await db.radacini_assoc_audit.find({"association_id": _aid_q(_aid(assoc))}).sort("at", -1).limit(limit).to_list(limit)
    full = role in ("manager", "operator", "censor")
    items = []
    for r in rows:
        if full:
            e = {k: v for k, v in r.items() if k != "_id"}
            e["id"] = str(r["_id"])
        else:
            e = {k: r.get(k) for k in ("action", "actor_role", "target_type", "at")}
        items.append(e)
    return {"full": full, "items": items}


# ---------- alerte membru ----------
@router.get("/assoc/alerts/mine")
async def alerts_mine(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    today = today_bucharest()
    today_s = today.isoformat()
    rows = await db.radacini_assoc_members.find({"user_id": uid}).to_list(200)
    out = []
    for row in rows:
        aid = str(row.get("association_id"))
        mid = str(row["_id"])
        try:
            assoc = await _load(aid)
        except HTTPException:
            continue
        meets = await db.radacini_assoc_meetings.find(
            {"association_id": _aid_q(aid), "convocations.member_id": mid}).to_list(200)
        conv = []
        for m in meets:
            if str(m.get("date") or "") < today_s:
                continue
            mine = [c for c in (m.get("convocations") or []) if str(c.get("member_id")) == mid]
            if mine and not any(c.get("read_at") for c in mine):
                conv.append({"meeting_id": str(m["_id"]), "kind": m.get("kind"), "date": m.get("date")})
        dists = await db.radacini_assoc_distributions.find(
            {"association_id": _aid_q(aid), "member_id": mid}).to_list(200)
        dd = [_dist_out(d, today) for d in dists]
        near = [d for d in dd if d["near_prescription"] and (d["days_to_prescription"] is None or d["days_to_prescription"] >= 0)]
        pets = await db.radacini_assoc_petitions.find({"association_id": _aid_q(aid)}).to_list(200)
        need_sig = []
        for p in pets:
            if p.get("status") not in (None, "open") or p.get("threshold_met"):
                continue
            sigs = p.get("signatures") or []
            signed = any((s.get("member_id") if isinstance(s, dict) else s) == mid for s in sigs)
            if not signed:
                need_sig.append({"petition_id": str(p["_id"]), "title": p.get("title"), "kind": p.get("kind")})
        obl = await compute_obligations(assoc, today.year, await _rules(assoc))
        overdue = sum(1 for i in obl if i["status"] == "missed")
        out.append({
            "association_id": aid, "association_name": assoc.get("name"), "member_id": mid,
            "unacknowledged_convocations": conv, "distributions_near_prescription": near,
            "petitions_to_sign": need_sig, "overdue_obligations": overdue,
        })
    return {"items": out}
