"""SH-001 · House Journey & Readiness — motorul evoluției proprietății.

COMPUNE exclusiv motoare existente (zero logică duplicată):
`_completeness` Cartea Casei (scorul real pe 14 itemi) · `user_context` (semnale) ·
`_book_completeness`/`_twin_progress` (ASM-001) · Imobile Verificate (listings + gates,
NEATINS — doar citit) · config PB (praguri Admin, zero hardcodare).

Livrează: Journey L1→L7 · House Readiness (5 dimensiuni, ponderi config) ·
recomandări înlănțuite · FairPrice data contract (`fairprice_signals`, sursa FP-001).
Principiu: măsurăm cât de DOCUMENTATĂ/verificată/transparentă e casa, nu cât de perfectă.
"""
import logging
from datetime import datetime, timezone

from db import db
from propbenefits.config import get_config
from propbenefits.copilot import _book_completeness, _twin_progress
from propbenefits.eligibility import user_context

logger = logging.getLogger("propmanage.journey")


def _iso():
    return datetime.now(timezone.utc).isoformat()


LEVEL_LABELS = [
    (1, "casa_creata", "Casa înregistrată"),
    (2, "cartea_casei", "Cartea Casei începută"),
    (3, "digital_twin", "Digital Twin în dezvoltare"),
    (4, "house_health", "House Health activ"),
    (5, "doc_verificata", "Documentație verificată"),
    (6, "imobil_verificat", "Imobil Verificat"),
    (7, "publicat", "Publicat prin PropManage"),
]

# Recomandări înlănțuite — efecte reale, filtrate după starea Journey-ului
_CHAIN_FIRST = {
    "docs_for_benefit": "crește documentarea Cărții Casei",
    "activate_twin": "pornește Digital Twin-ul casei",
    "house_health": "activează scorul de sănătate al casei",
    "use_benefit": "valoarea beneficiului intră în casa ta",
    "claim_opportunity": "beneficiul intră în portofelul casei",
    "storage_upgrade": "Cartea Casei poate crește fără limite",
    "storage_cleanup": "faci loc documentelor care contează",
    "recommend_specialist": "crește încrederea comunității",
    "almost_ambassador": "devii vocea de încredere a comunității",
    "support_deal": "negocierea comunității avansează",
    "invite_neighbor": "comunitatea ta devine mai puternică",
    "renew_subscription": "beneficiile și scorul rămân active",
}


def chain_for_action(action_id: str, journey: dict | None) -> list:
    chain = [_CHAIN_FIRST.get(action_id, "faci pasul cu impact maxim")]
    doc_actions = action_id in ("docs_for_benefit", "activate_twin", "house_health", "storage_upgrade")
    if doc_actions:
        chain.append("crește House Readiness")
    chain.append("crește Subscription Health")
    lvl = (journey or {}).get("current_level") or 0
    if doc_actions and lvl < 5:
        chain.append("te apropii de Documentație verificată")
    if lvl < 6:
        chain.append("te apropii de Imobil Verificat")
    chain.append("pregătești casa pentru FairPrice")
    return chain


def _req(label, done, cta=None, hint=None):
    return {"label": label, "done": bool(done), "cta": cta, "hint": hint if not done else None}


async def _listing_for(user: dict):
    return await db.verified_estate_listings.find_one(
        {"owner_email": user.get("email")}, sort=[("created_at", -1)])


def _gates_pass(listing: dict | None) -> tuple:
    """(all_pass, gates_reqs) din gates_status al modulului Imobile Verificate (doar citit)."""
    if not listing:
        return False, []
    gates = listing.get("gates_status") or {}
    reqs = []
    for key, g in gates.items():
        if isinstance(g, dict):
            reqs.append(_req(g.get("label") or key.replace("_", " "), g.get("pass"),
                             cta="/imobile-verificate/sell", hint=g.get("reason")))
    return bool(reqs) and all(r["done"] for r in reqs), reqs


async def compute_journey(user: dict, ctx: dict = None, book: dict = None, twin: dict = None) -> dict:
    """Journey L1→L7 + Readiness + persistă semnalele FairPrice. Totul din date reale."""
    jcfg = (await get_config()).get("journey") or {}
    min_comp = int(jcfg.get("doc_verified_min_completeness", 60))
    req_cats = jcfg.get("doc_verified_required_categories") or ["act_proprietate", "cadastru", "certificat_energetic"]
    min_docs = int(jcfg.get("book_started_min_docs", 1))

    uid = user.get("id") or str(user.get("_id", ""))
    ctx = ctx or await user_context(user)
    book = book or await _book_completeness(uid)
    twin = twin or await _twin_progress(uid)
    prop = await db.properties.find_one({"owner_id": uid})
    items = {i["id"]: i for i in book.get("items", [])}

    def ok(iid):
        return bool(items.get(iid, {}).get("done"))

    listing = await _listing_for(user)
    published = bool(listing and listing.get("status") in ("published", "sold"))
    gates_ok, gate_reqs = _gates_pass(listing)

    cat_labels = {"act_proprietate": "Act de proprietate", "cadastru": "Cadastru / Carte funciară",
                  "certificat_energetic": "Certificat energetic", "plan_tehnic": "Plan tehnic",
                  "raport_inspectie": "Raport de inspecție", "foto": "Fotografii"}

    levels = []

    def lvl(n, key, label, reqs, done=None, in_progress=False, cta=None, note=None):
        done = all(r["done"] for r in reqs) if done is None else done
        status = "done" if done else ("in_progress" if (in_progress or any(r["done"] for r in reqs)) else "missing")
        pct = 100 if done else (round(100 * sum(1 for r in reqs if r["done"]) / len(reqs)) if reqs else 0)
        levels.append({"level": n, "key": key, "label": label, "status": status, "pct": pct,
                       "requirements": reqs, "cta": cta, "note": note})

    lvl(1, "casa_creata", "Casa înregistrată",
        [_req("Proprietatea adăugată în platformă", bool(prop), "property", "Adaugă proprietatea ta")],
        cta="property")
    lvl(2, "cartea_casei", "Cartea Casei începută",
        [_req(f"Minim {min_docs} document{'e' if min_docs > 1 else ''} încărcat{'e' if min_docs > 1 else ''}",
              book.get("docs_count", 0) >= min_docs, "property", "Încarcă primul document")],
        in_progress=bool(prop), cta="property")
    lvl(3, "digital_twin", "Digital Twin în dezvoltare",
        [_req("Proiect Digital Twin creat", twin.get("has_project"), "/digital-twin", "Creează geamănul digital"),
         _req("Model 3D încărcat", twin.get("pct", 0) >= 80, "/digital-twin", "Încarcă modelul 3D")],
        cta="/digital-twin")
    lvl(4, "house_health", "House Health activ",
        [_req("Scorul de sănătate al casei generat", bool(ctx.get("hh_score")), "/house-health",
              "Generează scorul House Health")],
        in_progress=bool(ctx.get("subscription_active")), cta="/house-health")
    l5_reqs = [_req(f"Completitudine Cartea Casei ≥ {min_comp}% (acum {book.get('score', 0)}%)",
                    book.get("score", 0) >= min_comp, "property")]
    for c in req_cats:
        l5_reqs.append(_req(cat_labels.get(c, c), ok(c), "property", f"Încarcă: {cat_labels.get(c, c)}"))
    lvl(5, "doc_verificata", "Documentație verificată", l5_reqs, cta="property")
    l6_reqs = gate_reqs or [_req("Solicită verificarea prin Imobile Verificate", False,
                                 "/imobile-verificate/sell", "Pornește procesul de verificare")]
    lvl(6, "imobil_verificat", "Imobil Verificat", l6_reqs,
        done=published or gates_ok, in_progress=bool(listing), cta="/imobile-verificate/sell",
        note="Publicarea NU e blocată de un scor mic — PropManage certifică doar că informațiile sunt autentice și transparente. Nivelul proprietății ți-l asumi tu.")
    lvl(7, "publicat", "Publicat prin PropManage",
        [_req("Anunț publicat în Imobile Verificate", published, "/imobile-verificate/sell")],
        done=published, in_progress=bool(listing), cta="/imobile-verificate/sell")

    current = 0
    for L in levels:
        if L["status"] == "done":
            current = L["level"]
        else:
            break
    nxt = next((L for L in levels if L["status"] != "done"), None)

    readiness = await _readiness(items, ctx, book, twin, listing, published or gates_ok, min_comp, jcfg)

    result = {
        "property": ({"id": str(prop["_id"]), "name": prop.get("name") or prop.get("address")} if prop else None),
        "levels": levels,
        "current_level": current,
        "current_label": next((lb for n, _k, lb in LEVEL_LABELS if n == current), "Început de drum"),
        "next_level": ({"level": nxt["level"], "label": nxt["label"],
                        "missing": [r for r in nxt["requirements"] if not r["done"]][:3],
                        "cta": nxt["cta"]} if nxt else None),
        "readiness": readiness,
        "generated_at": _iso(),
    }
    if prop:
        try:
            await _persist_fairprice_signals(uid, str(prop["_id"]), result, ctx, book, twin, listing, published or gates_ok)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[journey] fairprice signals persist failed: {e}")
    return result


# ---------------------------------------------------------------------------
# House Readiness — cât de PREGĂTITĂ (documentată) e casa, pe 5 dimensiuni
# ---------------------------------------------------------------------------
async def _readiness(items, ctx, book, twin, listing, verified, min_comp, jcfg) -> dict:
    weights = jcfg.get("readiness_weights") or {"administrare": 20, "mentenanta": 20, "audit": 20,
                                                "finantare": 20, "vanzare": 20}

    def ok(iid):
        return bool(items.get(iid, {}).get("done"))

    def chk(label, done, action=None):
        return {"label": label, "done": bool(done), "action": action}

    dims = [
        {"key": "administrare", "label": "Administrare", "checks": [
            chk("Act de proprietate", ok("act_proprietate"), "upload:act_proprietate"),
            chk("Atribute DNA completate", ok("dna_attrs"), "dna"),
            chk("Facturi / contracte lucrări", ok("facturi"), "upload:factura"),
            chk("Instalații mapate", ok("assets"), "assets"),
        ]},
        {"key": "mentenanta", "label": "Mentenanță", "checks": [
            chk("Jurnal de mentenanță", ok("maintenance"), "maintenance"),
            chk("Garanții / manuale echipamente", ok("garantii_manuale"), "upload:garantie"),
            chk("Lucrare confirmată prin platformă", ok("works"), "request"),
            chk("Garanție activă", ok("warranty"), "request"),
        ]},
        {"key": "audit", "label": "Audit", "checks": [
            chk("Raport de inspecție / audit tehnic", ok("audit"), "upload:raport_inspectie"),
            chk("Plan / schiță tehnică", ok("plan_tehnic"), "upload:plan_tehnic"),
            chk("Scor House Health generat", bool(ctx.get("hh_score")), "/house-health"),
            chk("Digital Twin început", twin.get("pct", 0) >= 40, "/digital-twin"),
        ]},
        {"key": "finantare", "label": "Finanțare", "checks": [
            chk("Act de proprietate", ok("act_proprietate"), "upload:act_proprietate"),
            chk("Cadastru / Carte funciară", ok("cadastru"), "upload:cadastru"),
            chk("Certificat energetic", ok("certificat_energetic"), "upload:certificat_energetic"),
            chk("Fotografii ale casei", ok("foto"), "upload:foto"),
        ]},
        {"key": "vanzare", "label": "Vânzare", "checks": [
            chk(f"Completitudine Cartea Casei ≥ {min_comp}%", book.get("score", 0) >= min_comp, "property"),
            chk("Fotografii ale casei", ok("foto"), "upload:foto"),
            chk("Model Digital Twin", twin.get("pct", 0) >= 80, "/digital-twin"),
            chk("Verificare Imobile Verificate", bool(verified), "/imobile-verificate/sell"),
        ]},
    ]
    total_w = sum(weights.get(d["key"], 20) for d in dims) or 100
    score = 0.0
    for d in dims:
        done = sum(1 for c in d["checks"] if c["done"])
        d["pct"] = round(100 * done / len(d["checks"]))
        d["weight"] = weights.get(d["key"], 20)
        d["missing"] = [{"label": c["label"], "action": c["action"]} for c in d["checks"] if not c["done"]]
        score += d["pct"] * d["weight"]
    return {"score": int(round(score / total_w)), "max": 100, "dimensions": dims,
            "note": "House Readiness măsoară cât de bine este DOCUMENTATĂ casa — nu cât de perfectă este."}


# ---------------------------------------------------------------------------
# FairPrice Data Contract — sursa de adevăr pentru FP-001 (fairprice_signals)
# ---------------------------------------------------------------------------
async def _persist_fairprice_signals(uid, property_id, journey, ctx, book, twin, listing, verified):
    items = {i["id"]: i for i in book.get("items", [])}

    def ok(iid):
        return bool(items.get(iid, {}).get("done"))

    transparency_keys = ["act_proprietate", "cadastru", "certificat_energetic", "foto", "audit"]
    history_keys = ["works", "maintenance", "warranty"]
    signals = {
        "documentare": book.get("score", 0),
        "verificare": 100 if verified else (40 if listing else 0),
        "digital_twin": twin.get("pct", 0),
        "house_health": 100 if ctx.get("hh_score") else (40 if ctx.get("subscription_active") else 0),
        "transparenta": round(100 * sum(1 for k in transparency_keys if ok(k)) / len(transparency_keys)),
        "istoric": round(100 * sum(1 for k in history_keys if ok(k)) / len(history_keys)),
        "mentenanta": next((d["pct"] for d in journey["readiness"]["dimensions"] if d["key"] == "mentenanta"), 0),
    }
    await db.fairprice_signals.update_one(
        {"property_id": property_id},
        {"$set": {"property_id": property_id, "user_id": uid, "signals": signals,
                  "journey_level": journey["current_level"],
                  "readiness_score": journey["readiness"]["score"],
                  "updated_at": _iso()}},
        upsert=True)


async def fairprice_signals(user: dict) -> dict:
    """Semnalele FairPrice pentru proprietatea userului (calculate dacă lipsesc)."""
    uid = user.get("id") or str(user.get("_id", ""))
    prop = await db.properties.find_one({"owner_id": uid}, {"_id": 1})
    if not prop:
        return {"property_id": None, "signals": None,
                "note": "Adaugă o proprietate pentru a genera semnalele FairPrice."}
    doc = await db.fairprice_signals.find_one({"property_id": str(prop["_id"])}, {"_id": 0})
    if not doc:
        await compute_journey(user)
        doc = await db.fairprice_signals.find_one({"property_id": str(prop["_id"])}, {"_id": 0})
    return doc or {"property_id": str(prop["_id"]), "signals": None}


async def journey_summary(user: dict, ctx: dict = None, book: dict = None, twin: dict = None) -> dict:
    """Varianta compactă pentru Copilotul Casei."""
    j = await compute_journey(user, ctx=ctx, book=book, twin=twin)
    return {"current_level": j["current_level"], "current_label": j["current_label"],
            "total_levels": 7, "next_level": j["next_level"],
            "readiness_score": j["readiness"]["score"]}
