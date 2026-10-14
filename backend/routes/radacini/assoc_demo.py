"""Composesorate (S9 demo): „Composesoratul Demo Valea Verde” — date integral fictive, doar pentru super-admin.

`POST /assoc/demo/seed` creează asociația cu registru, documente, ședințe, mandat, petiție, cereri și finanțe;
`POST /assoc/demo/reset` șterge tot ce poartă `demo_seed` (și fișierele create de seed). Routerul trebuie montat
ÎNAINTEA `assoc_core.router`, altfel `/assoc/demo/...` e prins de `/assoc/{id}`.
"""
import asyncio
import copy
import hashlib
import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

import storage_client

from .assoc_core import DEFAULT_RULES, write_audit
from .bridge import block_in_impersonation, db
from .common import RadaciniRoute, now_iso, today_bucharest
from .test_accounts import PERSONAS, _email, _ensure, require_super_admin

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

TAG = {"demo_seed": True, "is_demo": True}
NAME = "Composesoratul Demo Valea Verde"
COLLS = ["radacini_assoc_members", "radacini_assoc_claims", "radacini_assoc_audit", "radacini_assoc_documents",
         "radacini_assoc_doc_access", "radacini_assoc_meetings", "radacini_assoc_mandates",
         "radacini_assoc_petitions", "radacini_assoc_requests", "radacini_assoc_obligation_evidence",
         "radacini_assoc_finance_years", "radacini_assoc_distributions"]

FIRST = ["Gheorghe", "Ioan", "Vasile", "Nicolae", "Dumitru", "Petru", "Mihai", "Pavel", "Traian", "Teodor", "Simion",
         "Florin", "Alexandru", "Radu", "Ilie", "Constantin", "Maria", "Ana", "Elena", "Floarea", "Ioana", "Safta",
         "Rodica", "Aurelia", "Viorica", "Domnica", "Livia", "Cornelia"]
LAST = ["Moldovan", "Pop", "Rusu", "Crișan", "Barbu", "Câmpean", "Dragoș", "Fărcaș", "Gherman", "Hațegan", "Man",
        "Neagu", "Oprea", "Pașca", "Rotar", "Sabău", "Todea", "Ursu", "Vlad", "Zaha", "Bolboacă", "Cosma", "Domșa",
        "Mureșan", "Lazăr", "Roman", "Tohăneanu", "Bota"]


def _d(d: date) -> str:
    return d.isoformat()


def _ts(d: date, h: int = 10) -> str:
    return datetime(d.year, d.month, d.day, h, 0, tzinfo=timezone.utc).isoformat()


def _add_years(d: date, y: int) -> date:
    try:
        return d.replace(year=d.year + y)
    except ValueError:
        return d.replace(year=d.year + y, day=28)


def _minus_months(d: date, months: int) -> date:
    m = d.year * 12 + (d.month - 1) - months
    y, mo = divmod(m, 12)
    return date(y, mo + 1, min(d.day, 28))


def _pdf(title: str) -> bytes:
    """PDF minimal valid, cu o linie de titlu (ASCII)."""
    t = "".join(c if 32 <= ord(c) < 127 and c not in "()\\" else "-" for c in title)[:80]
    stream = f"BT /F1 14 Tf 72 720 Td (DEMO - {t}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return bytes(out)


async def _persona_ids(admin: dict) -> dict:
    ids: dict = {}
    for _ in range(2):
        ids = {}
        for p in PERSONAS:
            u = await db.users.find_one({"email": _email(p["key"])})
            if u and u.get("radacini_test_persona") == p["key"]:
                ids[p["key"]] = str(u["_id"])
        if len(ids) == len(PERSONAS):
            return ids
        await _ensure(admin)
    raise HTTPException(409, "Conturile de test nu au putut fi pregătite.")


def _fmt(s: float) -> str:
    return f"{s:g}".replace(".", ",")


def _sources(i: int, s: float) -> list:
    n = 100 + i * 3
    if s == 0.333333:
        return [f"Nr {n}=0,25", f"Nr {n + 1}=0,083333"]
    if s == 0.5 and i % 2:
        return [f"Nr {n}=0,25", f"Nr {n + 1}=0,25"]
    return [f"Nr {n}={_fmt(s)}"]


def _build_members(aid: str, uids: dict, now: str) -> list:
    rng = random.Random(9)
    shares = [1.0] * 34 + [0.5] * 8 + [0.333333] * 5 + [0.25] * 4 + [0.2] * 2 + [0.166667] * 2 + [0.125, 0.083333, 0.066667]
    rng.shuffle(shares)
    statuses = ["active"] * 6 + ["confirmed"] * 4 + ["deceased"] * 8 + ["contacted"] * 15 + ["unknown"] * 25
    names, used = [], set()
    while len(names) < 62:
        n = f"{rng.choice(LAST)} {rng.choice(FIRST)}"
        if n not in used:
            used.add(n)
            names.append(n)
    special = {  # index (0-based) -> (nume, user, council_role, cote)
        0: ("Ion Pop", uids["proprietar"], "president", 1.0),
        1: ("Vasile Crișan", uids["operator"], "censor", 1.0),
        2: (None, None, "secretary", None), 3: (None, None, "cashier", None),
        6: ("Maria Ionescu", uids["familie"], None, 0.5),
    }
    rows = []
    for i in range(58):
        code = f"M{i + 1:03d}"
        nm, uid, role, sh = special.get(i, (None, None, None, None))
        sh = sh if sh is not None else shares[i]
        loc = "Valea Verde" if i % 3 else "Dealu Mic"
        rows.append({
            "association_id": aid, "code": code, "name": nm or names[i], "shares": sh,
            "sources": _sources(i, sh), "status": statuses[i], "locality": loc, "council_role": role,
            "user_id": uid, "created_at": now, "updated_at": now, **TAG})
    # moștenitori în curs (cote 0, ca la aprobarea unei revendicări de moștenire)
    rows.append({"association_id": aid, "code": "M059", "name": "Andrei Rusu", "shares": 0.0, "sources": [],
                 "status": "heir_pending", "locality": "Valea Verde", "council_role": None, "user_id": uids["consumator"],
                 "relation": "fiu", "heir_of_code": "M011", "created_at": now, "updated_at": now, **TAG})
    rows.append({"association_id": aid, "code": "M060", "name": f"{names[60]}", "shares": 0.0, "sources": [],
                 "status": "heir_pending", "locality": "Dealu Mic", "council_role": None, "user_id": None,
                 "relation": "nepoată", "heir_of_code": "M012", "created_at": now, "updated_at": now, **TAG})
    return rows


@router.post("/assoc/demo/seed")
async def seed_demo(admin: dict = Depends(require_super_admin)):
    block_in_impersonation(admin, "crearea scenariului demo")
    if await db.radacini_associations.find_one({"demo_seed": True}):
        raise HTTPException(409, "Scenariul demo există deja. Resetează-l mai întâi.")
    uids = await _persona_ids(admin)
    today = today_bucharest()
    now = now_iso()
    ly = today.year - 1
    last_nov = date(today.year - 1, 11, 15) if today < date(today.year, 11, 15) else date(today.year, 11, 15)
    last_apr = date(today.year, 4, 20) if today >= date(today.year, 4, 20) else date(today.year - 1, 4, 20)

    assoc = {
        "name": NAME, "type": "composesorat", "localities": ["Valea Verde", "Dealu Mic"],
        "description": "Asociație fictivă, creată pentru demonstrație. Toate datele sunt inventate.",
        "legal": {}, "rules": copy.deepcopy(DEFAULT_RULES),
        "patrimony": [
            {"cf": "CF 9001", "topo": None, "area_ha": 300.0, "category": "pășune împădurită", "toponym": "Poiana Mare"},
            {"cf": "CF 9002", "topo": None, "area_ha": 80.0, "category": "pășune împădurită", "toponym": "Fața Dealului"},
        ],
        "operator_user_ids": [], "created_by": str(admin["id"]), "created_at": now, "updated_at": now, **TAG}
    aid = str((await db.radacini_associations.insert_one(assoc)).inserted_id)
    created_paths: list = []
    try:
        rows = _build_members(aid, uids, now)
        res = await db.radacini_assoc_members.insert_many(rows)
        ids = [str(i) for i in res.inserted_ids]
        by_code = {r["code"]: ids[k] for k, r in enumerate(rows)}
        for r, i in zip(rows, ids):
            r["_id"] = i
        by_code_row = {r["code"]: r for r in rows}
        for h, base in (("M059", "M011"), ("M060", "M012")):
            await db.radacini_assoc_members.update_one(
                {"association_id": aid, "code": h}, {"$set": {"heir_of_member_id": by_code[base]}})
        ion, maria = by_code["M001"], by_code["M007"]
        activeish = [r for r in rows if r["status"] in ("active", "confirmed") and r.get("user_id")]
        total_shares = sum(r["shares"] for r in rows)

        ana = {"id": uids["manager"], "name": "Ana Pavel"}
        pres = {"id": uids["proprietar"], "name": "Ion Pop"}
        secr = {"id": "demo-secretar", "name": by_code_row["M003"]["name"]}
        cens = {"id": uids["operator"], "name": "Vasile Crișan"}
        await write_audit(aid, ana, "manager", "assoc.create", "association", aid, after={"name": NAME})
        await write_audit(aid, ana, "manager", "member.import", "association", aid, after={"imported": len(rows)})

        # revendicare de moștenire în așteptare (Andrei)
        await db.radacini_assoc_claims.insert_one({
            "association_id": aid, "user_id": uids["consumator"], "user_name": "Andrei Rusu", "kind": "heir",
            "member_code": "M011", "name_on_record": by_code_row["M011"]["name"], "relation": "fiu",
            "note": "Tatăl meu a decedat; solicit trecerea cotei pe numele meu.", "document_ids": [],
            "status": "pending", "created_at": _ts(today - timedelta(days=6)), **TAG})

        # ---- documente
        async def add_doc(typ, title, d: date, by):
            data = _pdf(title)
            path = f"radacini/assoc/{aid}/docs/{uuid.uuid4().hex}.pdf"
            await asyncio.to_thread(storage_client.put_object, path, data, "application/pdf")
            created_paths.append(path)
            doc = {"association_id": aid, "type": typ, "title": title, "date": _d(d), "visibility": "members",
                   "replaces_id": None, "version": 1, "path": path, "content_type": "application/pdf",
                   "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "uploaded_by": by["id"],
                   "uploaded_role": "council", "created_at": _ts(d), **TAG}
            r = await db.radacini_assoc_documents.insert_one(doc)
            await write_audit(aid, by, "council", "document.upload", "document", str(r.inserted_id),
                              after={"title": title, "sha256": doc["sha256"], "visibility": "members"})
            return str(r.inserted_id)

        cd = date(today.year, 3, 25) if today > date(today.year, 3, 25) else date(ly, 3, 25)
        await add_doc("statut", "Statutul composesoratului (fictiv)", date(2005, 10, 30), secr)
        d_pv = await add_doc("pv_aga", "Proces-verbal AGA ordinară (fictiv)", last_nov, secr)
        d_bal = await add_doc("balance", f"Bilanț {ly} (fictiv)", date(ly, 4, 15), pres)
        await add_doc("censor_report", "Raport cenzor trimestrul I (fictiv)", cd, cens)

        # ---- ședințe
        def conv(r, read):
            return {"member_id": r["_id"], "user_id": r["user_id"], "channel": "app/email",
                    "sent_at": _ts(today - timedelta(days=1)), "delivered": True, "read_at": read}

        first = last_nov - timedelta(days=7)
        past_conv = [conv(r, _ts(first - timedelta(days=2))) for r in activeish]
        pv_ids = [r["_id"] for r in activeish if r["code"] in ("M001", "M002")]
        present = sum(r["shares"] for r in activeish if r["code"] in ("M001", "M002"))
        past = {
            "association_id": aid, "kind": "aga_ordinary", "date": _d(last_nov), "place": "Căminul cultural Valea Verde",
            "agenda": [{"title": "Raportul de activitate și bilanțul", "details": ""},
                       {"title": "Bugetul de venituri și cheltuieli", "details": ""},
                       {"title": "Plan de pășunat", "details": ""}],
            "material_ids": [d_bal], "status": "held", "first_convocation_date": _d(first), "second_convocation": True,
            "first_convocation_quorum_met": False, "convocations": past_conv, "registered_mail_evidence_document_id": None,
            "attendance": {"present_member_ids": pv_ids, "mandate_ids": [], "present_shares": present,
                           "mandated_shares": 0.0, "represented_shares": present, "total_shares": total_shares,
                           "quorum_met": False, "recorded_at": _ts(last_nov, 14), "recorded_by": uids["proprietar"]},
            "decisions": [
                {"title": "Aprobarea bilanțului", "result_text": "Aprobat cu majoritate de voturi.",
                 "votes_for": 2.0, "votes_against": 0.0, "abstentions": 0.0},
                {"title": "Aprobarea bugetului de venituri și cheltuieli", "result_text": "Aprobat.",
                 "votes_for": 2.0, "votes_against": 0.0, "abstentions": 0.0},
                {"title": "Planul de pășunat", "result_text": "Aprobat cu modificări.",
                 "votes_for": 1.0, "votes_against": 1.0, "abstentions": 0.0}],
            "minutes_document_id": d_pv, "contest_until": _d(last_nov + timedelta(days=15)),
            "held_without_quorum": True, "convened_at": _ts(first - timedelta(days=16)),
            "decisions_at": _ts(last_nov, 16), "created_by": uids["proprietar"], "created_at": _ts(first - timedelta(days=20)),
            **TAG}
        pm = str((await db.radacini_assoc_meetings.insert_one(past)).inserted_id)
        await write_audit(aid, pres, "council", "meeting.create", "meeting", pm, after={"kind": "aga_ordinary", "date": _d(last_nov)})
        await write_audit(aid, pres, "council", "meeting.attendance", "meeting", pm,
                          after={"represented_shares": present, "quorum_met": False, "second_convocation": True})
        await write_audit(aid, secr, "council", "meeting.decisions", "meeting", pm, after={"count": 3})

        up_date = today + timedelta(days=20)
        up_conv = [conv(r, None if r["code"] == "M007" else _ts(today)) for r in activeish]
        upcoming = {
            "association_id": aid, "kind": "aga_ordinary", "date": _d(up_date), "place": "Căminul cultural Valea Verde",
            "agenda": [{"title": "Raportul cenzorului", "details": ""}, {"title": "Planul de pășunat", "details": ""},
                       {"title": "Buget", "details": "Proiect de buget pe anul următor"}],
            "material_ids": [d_bal], "status": "convened", "first_convocation_date": None, "second_convocation": False,
            "convocations": up_conv, "registered_mail_evidence_document_id": None, "attendance": None, "decisions": [],
            "minutes_document_id": None, "contest_until": None, "held_without_quorum": False,
            "convened_at": _ts(today - timedelta(days=1)), "convene_warning": None,
            "created_by": uids["proprietar"], "created_at": _ts(today - timedelta(days=2)), **TAG}
        um = str((await db.radacini_assoc_meetings.insert_one(upcoming)).inserted_id)
        await write_audit(aid, pres, "council", "meeting.create", "meeting", um, after={"kind": "aga_ordinary", "date": _d(up_date)})
        await write_audit(aid, pres, "council", "meeting.convene", "meeting", um, after={"notified": len(up_conv)})

        # ---- mandat: Maria îl mandatează pe Ion pentru AGA viitoare
        md = await db.radacini_assoc_mandates.insert_one({
            "association_id": aid, "meeting_id": um, "mandator_member_id": maria, "mandator_user_id": uids["familie"],
            "representative_member_id": ion, "document_id": None, "status": "active",
            "created_at": _ts(today), **TAG})

        # ---- petiție AGA extraordinară (sub prag): Maria + 3 membri
        sig_rows = [by_code_row["M007"], by_code_row["M008"], by_code_row["M009"], by_code_row["M010"]]
        sigs = [{"member_id": r["_id"], "user_id": r.get("user_id"), "shares": r["shares"],
                 "at": _ts(today - timedelta(days=3 - k % 3))} for k, r in enumerate(sig_rows)]
        await db.radacini_assoc_petitions.insert_one({
            "association_id": aid, "kind": "extraordinary_aga", "title": "Convocarea unei AGA extraordinare pentru contractul de pășunat",
            "text": "Solicităm convocarea unei adunări generale extraordinare pentru discutarea contractului de pășunat.",
            "meeting_id": None, "created_by_member_id": maria, "created_by": uids["familie"], "signatures": sigs,
            "status": "open", "rev": len(sigs), "threshold_notified": False, "created_at": _ts(today - timedelta(days=5)), **TAG})

        # ---- cereri de informații
        due_old = today - timedelta(days=15)
        await db.radacini_assoc_requests.insert_one({
            "association_id": aid, "member_id": maria, "user_id": uids["familie"], "subject": "Copia contractului de pășunat",
            "text": "Vă rog să-mi puneți la dispoziție copia contractului de pășunat în vigoare.",
            "due_at": _ts(due_old), "status": "open", "answered_at": None, "answer": None,
            "created_at": _ts(due_old - timedelta(days=30)), **TAG})
        ans_at = _ts(today - timedelta(days=30))
        await db.radacini_assoc_requests.insert_one({
            "association_id": aid, "member_id": maria, "user_id": uids["familie"], "subject": "Procesul-verbal al ultimei AGA",
            "text": "Doresc o copie a procesului-verbal al ultimei adunări generale.",
            "due_at": _ts(today - timedelta(days=10)), "status": "answered", "answered_at": ans_at,
            "answer": {"text": "Documentul este atașat.", "document_id": d_pv, "by": uids["proprietar"], "at": ans_at},
            "created_at": _ts(today - timedelta(days=40)), **TAG})
        await write_audit(aid, pres, "council", "request.answer", "request", None, after={"late": False})

        # ---- dovadă manuală (planul de pășunat); actualizarea registrului rămâne fără dovadă
        await db.radacini_assoc_obligation_evidence.insert_one({
            "association_id": aid, "key": "pasture_plan", "year": ly, "note": "Plan de pășunat afișat la sediu",
            "document_id": None, "date": _d(date(ly, 10, 20)), "created_by": uids["proprietar"],
            "created_at": _ts(date(ly, 10, 20)), **TAG})
        await write_audit(aid, pres, "council", "obligation_evidence", "obligation", f"pasture_plan:{ly}",
                          after={"key": "pasture_plan", "year": ly})

        # ---- finanțe: un an vechi aproape de prescriere + anul trecut
        old_aga = _minus_months(today, 57)  # acum 4 ani și 9 luni -> prescrie în ~3 luni
        fin = [
            (old_aga.year - 1, {"lemn": 30000, "pasunat": 15000, "arenda": 6000},
             {"administrare": 24000, "ocol_silvic": 8000, "taxe": 3000},
             {"council": 1600, "reserve": 3000, "charity": 1000, "investment": 2000}, old_aga, 5),
            (ly, {"lemn": 42000, "pasunat": 18500, "arenda": 6000},
             {"administrare": 21000, "ocol_silvic": 9000, "taxe": 3500},
             {"council": 3000, "reserve": 5000, "charity": 1500, "investment": 4000}, last_apr, 12),
        ]
        drows = [r for r in rows if r["shares"] > 0]
        tsh = sum(r["shares"] for r in drows)
        for year, rev, exp, sp, aga, n_paid in fin:
            net = round(sum(rev.values()) - sum(exp.values()), 2)
            members_part = round(net - sum(sp.values()), 2)
            split = {**{k: float(v) for k, v in sp.items()}, "members": members_part}
            await db.radacini_assoc_finance_years.insert_one({
                "association_id": aid, "year": year, "revenues": rev, "expenses": exp, "net_profit": net, "split": split,
                "distributed_at": _ts(aga), "aga_date": _d(aga), "created_by": uids["proprietar"],
                "created_at": _ts(aga), **TAG})
            amounts = [round(members_part * r["shares"] / tsh, 2) for r in drows]
            amounts[max(range(len(drows)), key=lambda i: drows[i]["shares"])] += round(members_part - sum(amounts), 2)
            presc = _d(_add_years(aga, int(DEFAULT_RULES["prescription_years"])))
            # plătite: primii câțiva membri activi/confirmați, restul neridicate
            payable = [i for i, r in enumerate(drows) if r["status"] in ("active", "confirmed")]
            paid = set(payable[:n_paid]) | set(range(len(drows) - 3)[: max(0, n_paid - len(payable))])
            await db.radacini_assoc_distributions.insert_many([{
                "association_id": aid, "year": year, "member_id": r["_id"], "member_code": r["code"],
                "amount": round(a, 2), "aga_date": _d(aga), "prescribes_at": presc,
                "paid_at": _ts(aga + timedelta(days=20)) if i in paid else None,
                "paid_by": uids["proprietar"] if i in paid else None, "created_at": _ts(aga), **TAG}
                for i, (r, a) in enumerate(zip(drows, amounts))])
            await write_audit(aid, pres, "council", "finance_year_create", "finance_year", f"{aid}:{year}",
                              after={"year": year, "net_profit": net})
            await write_audit(aid, pres, "council", "finance_distribute", "finance_year", f"{aid}:{year}",
                              after={"year": year, "members": len(drows), "total": members_part, "prescribes_at": presc})
        await write_audit(aid, pres, "council", "distribution_paid", "distribution", None, after={"count": "demo"})

        # jurnalul scris prin write_audit nu are `demo_seed` fără env: marcăm tot ce ține de asociație
        await db.radacini_assoc_audit.update_many({"association_id": aid}, {"$set": TAG})
        await db.radacini_assoc_mandates.update_one({"_id": md.inserted_id}, {"$set": {"is_demo": True}})
    except Exception:
        log.exception("radacini: seed demo composesorat a eșuat; se curăță")
        await _purge()
        raise HTTPException(500, "Scenariul demo nu a putut fi creat (storage sau bază de date).") from None
    return {"ok": True, "association_id": aid, "members": len(rows), "name": NAME}


async def _purge() -> dict:
    counts: dict = {}
    assoc_rows = await db.radacini_associations.find({"demo_seed": True}).to_list(100)
    aids = [str(a["_id"]) for a in assoc_rows]
    flt = {"$or": [{"demo_seed": True}, {"association_id": {"$in": aids}}]} if aids else {"demo_seed": True}
    docs = await db.radacini_assoc_documents.find(flt).to_list(5000)
    for d in docs:
        if d.get("path"):
            try:
                await asyncio.to_thread(storage_client.delete_object, d["path"])
            except Exception:  # noqa: BLE001
                log.warning("radacini: fișierul demo nu a putut fi șters", exc_info=True)
    for name in COLLS:
        r = await getattr(db, name).delete_many(flt)
        counts[name] = r.deleted_count
    r = await db.radacini_associations.delete_many({"demo_seed": True})
    counts["radacini_associations"] = r.deleted_count
    return counts


@router.post("/assoc/demo/reset")
async def reset_demo(admin: dict = Depends(require_super_admin)):
    block_in_impersonation(admin, "resetarea scenariului demo")
    return {"ok": True, "deleted": await _purge()}
