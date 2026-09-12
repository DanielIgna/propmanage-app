"""Property Passport — Trust Profile public (Sprint CX-3).

Nu un PDF: cartea de identitate digitală a proprietății. Profil public de încredere,
partajabil (link + QR permanent), cu confidențialitate controlată de proprietar.
Toate scorurile și badge-urile derivă EXCLUSIV din semnale reale (Truth Engine).
"""
import html as _html
import io
import re
import secrets
from collections import Counter
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from db import db
from deps import get_current_user
from routes.property_dna import _load_property_for
from routes.property_documents import _completeness
from storage_client import get_object

router = APIRouter(prefix="/api", tags=["property_passport"])
public_router = APIRouter(prefix="/api", tags=["property_passport_public"])

DEFAULT_PRIVACY = {
    "show_address": False,
    "show_photo": True,
    "show_documents": True,
    "show_timeline": True,
    "show_scores": True,
    "show_design_concept": False,
}

PRIVACY_LABELS = {
    "show_address": "Adresa completă",
    "show_photo": "Fotografia casei",
    "show_documents": "Rezumatul documentelor",
    "show_timeline": "Istoricul lucrărilor",
    "show_scores": "Scorurile casei",
    "show_design_concept": "Conceptul de design (validat)",
}


def _base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f"{scheme}://{host}"


async def _prop_by_slug(slug: str) -> dict:
    prop = await db.properties.find_one({"passport.slug": slug, "passport.enabled": True})
    if not prop:
        raise HTTPException(404, "Pașaportul nu există sau nu este public")
    return prop


# ── Trust Score: factori 100% verificabili, cu explicații ────────────────────
async def _trust_score(prop_id: str) -> dict:
    docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}},
        {"category": 1, "provenance": 1, "verification_status": 1},
    ).to_list(500)
    documented = [d for d in docs if d.get("provenance") == "documented" or d.get("verification_status") == "verified"]
    cats = Counter(d.get("category") for d in docs)
    twin = await db.twins.find_one({"property_id": prop_id}, {"status": 1})
    works = await db.requests.count_documents({"property_id": prop_id, "status": "confirmed"})
    warranties = await db.warranties.count_documents({"property_id": prop_id, "status": "active"})
    maint = await db.maintenance_logs.count_documents({"property_id": prop_id})
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)}, {"dna_attributes": 1})
    dna_attrs = len([v for v in ((prop or {}).get("dna_attributes") or {}).values() if (v or {}).get("value") is not None])

    factors = []

    def add(fid, label, earned, mx, why):
        factors.append({"id": fid, "label": label, "earned": earned, "max": mx, "done": earned >= mx, "why": why})

    add("verified_docs", "Documente verificate", min(len(documented) * 5, 20), 20,
        "Documente adăugate de specialiști sau verificate de platformă — nu doar declarate.")
    add("twin", "Digital Twin validat", 20 if (twin or {}).get("status") == "approved" else (5 if twin else 0), 20,
        "Structura casei a fost validată de un operator PropManage.")
    add("audit", "Audit tehnic", 15 if cats.get("raport_inspectie") else 0, 15,
        "Un raport de inspecție tehnică există în cartea casei.")
    add("works", "Lucrări cu dovadă", (15 if works >= 1 else 0) + (5 if works >= 3 else 0), 20,
        "Lucrări finalizate prin platformă, cu plată protejată și istoric imutabil.")
    add("warranty", "Garanții active", 10 if warranties else 0, 10,
        "Lucrările recente sunt acoperite de garanții înregistrate.")
    add("maintenance", "Mentenanță dovedită", 10 if maint else 0, 10,
        "Există jurnal de întreținere validat.")
    add("dna", "Profil tehnic completat", 5 if dna_attrs >= 3 else 0, 5,
        "Atributele tehnice ale casei (an, structură, încălzire) sunt declarate.")

    score = sum(f["earned"] for f in factors)
    missing = [{"label": f["label"], "gain": f["max"] - f["earned"], "why": f["why"]}
               for f in sorted(factors, key=lambda x: x["max"] - x["earned"], reverse=True) if not f["done"]]
    return {"score": score, "max": 100, "factors": factors, "missing": missing[:4],
            "explanation": "Scorul de încredere măsoară doar dovezi verificabile: documente, validări, lucrări cu plată protejată și garanții — niciodată declarații."}


def _maintenance_score(prop: dict) -> dict | None:
    vals = [prop.get(f) for f in ("structure_health", "utilities_health", "documents_health") if isinstance(prop.get(f), (int, float))]
    if not vals:
        return None
    return {"score": round(sum(vals) / len(vals)), "label": "Sănătatea casei", "source": "măsurat din evenimente dovedite"}


async def _badges(prop_id: str, trust: dict, compl: dict) -> list:
    f = {x["id"]: x for x in trust["factors"]}
    return [
        {"id": "verified_documentation", "label": "Documentație verificată", "earned": f["verified_docs"]["earned"] > 0},
        {"id": "digital_twin", "label": "Digital Twin", "earned": f["twin"]["done"]},
        {"id": "property_dna", "label": "Property DNA", "earned": f["dna"]["done"]},
        {"id": "technical_audit", "label": "Audit tehnic", "earned": f["audit"]["earned"] > 0},
        {"id": "verified_specialists", "label": "Specialiști verificați", "earned": f["works"]["earned"] > 0},
        {"id": "verified_maintenance", "label": "Mentenanță dovedită", "earned": f["maintenance"]["earned"] > 0},
        {"id": "verified_warranty", "label": "Garanție activă", "earned": f["warranty"]["earned"] > 0},
        {"id": "documented_property", "label": "Casă documentată", "earned": compl["score"] >= 50},
    ]


async def _milestones(prop_id: str) -> list:
    events = []
    reqs = await db.requests.find({"property_id": prop_id, "status": "confirmed"}).to_list(50)
    for r in reqs:
        events.append({"type": "work", "title": r.get("title") or "Lucrare finalizată",
                       "detail": "Lucrare finalizată prin PropManage, cu plată protejată",
                       "date": r.get("confirmed_at") or r.get("updated_at") or r.get("created_at")})
    docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}).to_list(300)
    CAT_MILESTONE = {
        "raport_inspectie": "Audit / inspecție tehnică", "plan_tehnic": "Plan tehnic arhivat",
        "certificat_energetic": "Certificat energetic înregistrat", "act_proprietate": "Act de proprietate arhivat",
        "cadastru": "Cadastru / CF arhivat",
    }
    for d in docs:
        if d.get("category") in CAT_MILESTONE:
            events.append({"type": "document", "title": CAT_MILESTONE[d["category"]],
                           "detail": "Document păstrat permanent în cartea casei",
                           "date": d.get("doc_date") or d.get("uploaded_at")})
        if d.get("warranty_end"):
            events.append({"type": "warranty", "title": "Garanție înregistrată",
                           "detail": f"Valabilă până la {d['warranty_end']}", "date": d.get("uploaded_at")})
    events = [e for e in events if e.get("date")]
    events.sort(key=lambda e: str(e["date"]), reverse=True)
    return events[:12]


async def _public_payload(prop: dict, request: Request) -> dict:
    prop_id = str(prop["_id"])
    privacy = {**DEFAULT_PRIVACY, **(prop.get("passport", {}).get("privacy") or {})}
    slug = prop["passport"]["slug"]
    compl = await _completeness(prop_id, prop)
    trust = await _trust_score(prop_id)
    badges = await _badges(prop_id, trust, compl)
    attrs = prop.get("dna_attributes") or {}

    def attr(k):
        return (attrs.get(k) or {}).get("value")

    docs_cats = Counter()
    if privacy["show_documents"]:
        rows = await db.property_documents.find(
            {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}, {"category": 1}).to_list(500)
        docs_cats = Counter(d.get("category") for d in rows)

    has_photo = privacy["show_photo"] and await db.property_documents.count_documents(
        {"property_id": prop_id, "category": "foto", "deleted": {"$ne": True}}) > 0

    last_events = await db.activity_events.find({"property_id": prop_id}).sort("created_at", -1).limit(1).to_list(1)
    last_updated = (last_events[0].get("created_at") if last_events else None) or prop.get("created_at")

    # Concept în Pașaport — doar concept VALIDAT profesional, opt-in explicit al proprietarului.
    design_concept = None
    if privacy.get("show_design_concept"):
        vc = await db.digital_twin_design_concepts.find_one(
            {"property_id": prop_id, "status": "verified"},
            sort=[("validated_at", -1), ("created_at", -1)])
        if vc:
            cc = vc.get("concept") or {}
            design_concept = {
                "title": cc.get("title"),
                "style": (vc.get("inputs") or {}).get("style"),
                "summary": cc.get("summary"),
                "palette": [p.get("hex") for p in (cc.get("palette") or []) if p.get("hex")][:6],
                "render_url": f"/api/public/passport/{slug}/design-concept-render" if vc.get("render_object_path") else None,
                "validated_by_name": vc.get("validated_by_name"),
                "validated_at": vc.get("validated_at"),
            }

    return {
        "slug": slug,
        "share_url": f"{_base_url(request)}/api/p/{slug}",
        "property": {
            "name": prop.get("name"),
            "type": prop.get("type"),
            "surface": prop.get("surface"),
            "rooms": prop.get("rooms"),
            "address": prop.get("address") if privacy["show_address"] else None,
            "year_built": attr("year_built"),
            "heating": attr("heating_type"),
            "roof": attr("roof_type"),
            "structure": attr("structure_type"),
        },
        "photo_url": f"/api/public/passport/{slug}/photo" if has_photo else None,
        "scores": {
            "trust": trust,
            "completeness": {"score": compl["score"], "next_step": compl["next_step"], "docs_count": compl["docs_count"], "items": compl["items"]} if privacy["show_scores"] else None,
            "maintenance": _maintenance_score(prop) if privacy["show_scores"] else None,
        },
        "badges": badges,
        "milestones": await _milestones(prop_id) if privacy["show_timeline"] else [],
        "document_highlights": {
            "plans": docs_cats.get("plan_tehnic", 0), "manuals": docs_cats.get("manual", 0),
            "warranties": docs_cats.get("garantie", 0), "invoices": docs_cats.get("factura", 0) + docs_cats.get("contract", 0),
            "reports": docs_cats.get("raport_inspectie", 0), "photos": docs_cats.get("foto", 0),
            "total": sum(docs_cats.values()),
        } if privacy["show_documents"] else None,
        "privacy": privacy,
        "last_updated": str(last_updated) if last_updated else None,
        "twin_status": ((await db.twins.find_one({"property_id": prop_id}, {"status": 1})) or {}).get("status"),
        "design_concept": design_concept,
    }


# ── OWNER ────────────────────────────────────────────────────────────────────
@router.post("/properties/{prop_id}/passport/enable")
async def enable_passport(prop_id: str, request: Request, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    passport = prop.get("passport") or {}
    if not passport.get("slug"):
        passport["slug"] = secrets.token_urlsafe(8).replace("_", "").replace("-", "")[:10].lower()
        passport["privacy"] = dict(DEFAULT_PRIVACY)
        passport["created_at"] = datetime.now(timezone.utc).isoformat()
    passport["enabled"] = True
    await db.properties.update_one({"_id": prop["_id"]}, {"$set": {"passport": passport}})
    prop["passport"] = passport
    return await owner_passport(prop_id, request, user)


@router.patch("/properties/{prop_id}/passport")
async def update_passport(prop_id: str, request: Request, body: dict = Body(...), user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    passport = prop.get("passport") or {}
    if not passport.get("slug"):
        raise HTTPException(400, "Pașaportul nu a fost activat încă")
    if "enabled" in body:
        passport["enabled"] = bool(body["enabled"])
    if isinstance(body.get("privacy"), dict):
        passport["privacy"] = {**DEFAULT_PRIVACY, **(passport.get("privacy") or {}),
                               **{k: bool(v) for k, v in body["privacy"].items() if k in DEFAULT_PRIVACY}}
    await db.properties.update_one({"_id": prop["_id"]}, {"$set": {"passport": passport}})
    prop["passport"] = passport
    return await owner_passport(prop_id, request, user)


@router.get("/properties/{prop_id}/passport")
async def owner_passport(prop_id: str, request: Request, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    passport = prop.get("passport") or {}
    if not passport.get("slug"):
        return {"enabled": False, "slug": None, "privacy": dict(DEFAULT_PRIVACY), "privacy_labels": PRIVACY_LABELS}
    slug = passport["slug"]
    base = _base_url(request)
    return {
        "enabled": bool(passport.get("enabled")),
        "slug": slug,
        "share_url": f"{base}/api/p/{slug}",
        "page_url": f"{base}/p/{slug}",
        "qr_url": f"{base}/api/public/passport/{slug}/qr.png",
        "privacy": {**DEFAULT_PRIVACY, **(passport.get("privacy") or {})},
        "privacy_labels": PRIVACY_LABELS,
        "preview": await _public_payload(prop, request) if passport.get("enabled") else None,
    }


# ── PUBLIC (fără autentificare) ──────────────────────────────────────────────
BOT_UA = re.compile(
    r"bot|crawl|spider|facebookexternalhit|whatsapp|slack|telegram|twitter|linkedin"
    r"|pinterest|discord|skype|viber|vkshare|embed|preview|quora|redditbot", re.I)


@public_router.get("/p/{slug}")
async def passport_share_link(slug: str, request: Request):
    """Link scurt de share: boții social primesc HTML cu Open Graph, oamenii redirect la /p/{slug}."""
    prop = await _prop_by_slug(slug)
    base = _base_url(request)
    src = request.query_params.get("src", "")
    src_q = f"?src={src}" if re.fullmatch(r"[a-z_]{1,12}", src or "") else ""
    target = f"{base}/p/{slug}{src_q}"
    if not BOT_UA.search(request.headers.get("user-agent", "")):
        return RedirectResponse(target, status_code=307)

    prop_id = str(prop["_id"])
    try:  # EO-026: fiecare preview social generat = semnal de share măsurabil
        await db.passport_events.insert_one({
            "event_id": secrets.token_hex(12), "slug": slug, "property_id": prop_id,
            "type": "og_fetch", "src": src if src_q else "bot",
            "ua": request.headers.get("user-agent", "")[:160],
            "day": datetime.now(timezone.utc).isoformat()[:10],
            "ts": datetime.now(timezone.utc).isoformat()})
    except Exception:  # noqa: BLE001
        pass
    privacy = {**DEFAULT_PRIVACY, **(prop.get("passport", {}).get("privacy") or {})}
    trust = await _trust_score(prop_id)
    docs_count = await db.property_documents.count_documents(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}})
    has_photo = privacy["show_photo"] and await db.property_documents.count_documents(
        {"property_id": prop_id, "category": "foto", "deleted": {"$ne": True}}) > 0
    image = f"{base}/api/public/passport/{slug}/photo" if has_photo else f"{base}/og-passport.jpg"
    name = _html.escape(prop.get("name") or "Proprietate")
    title = f"{name} — Pașaportul Casei | PropManage"
    desc = (f"Scor de încredere {trust['score']}/100 · {docs_count} documente în cartea casei. "
            "Profil public de încredere: identitate, istoric și dovezi verificate — nu doar promisiuni.")
    doc = f"""<!doctype html>
<html lang="ro"><head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{target}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PropManage">
<meta property="og:locale" content="ro_RO">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{target}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1264">
<meta property="og:image:height" content="848">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{image}">
<meta http-equiv="refresh" content="0;url={target}">
</head><body>
<p><a href="{target}">{title}</a></p>
<script>location.replace({target!r});</script>
</body></html>"""
    return HTMLResponse(doc, headers={"Cache-Control": "public, max-age=300"})


@public_router.get("/public/passport/{slug}")
async def public_passport(slug: str, request: Request):
    prop = await _prop_by_slug(slug)
    return await _public_payload(prop, request)


@public_router.get("/public/passport/{slug}/qr.png")
async def passport_qr(slug: str, request: Request):
    prop = await _prop_by_slug(slug)
    import qrcode
    from qrcode.image.pil import PilImage
    url = f"{_base_url(request)}/p/{prop['passport']['slug']}?src=qr"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=PilImage, fill_color="#0a0a0b", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@public_router.get("/public/passport/{slug}/photo")
async def passport_photo(slug: str):
    prop = await _prop_by_slug(slug)
    privacy = {**DEFAULT_PRIVACY, **(prop.get("passport", {}).get("privacy") or {})}
    if not privacy["show_photo"]:
        raise HTTPException(404, "Fotografia nu este publică")
    doc = await db.property_documents.find_one(
        {"property_id": str(prop["_id"]), "category": "foto", "deleted": {"$ne": True}},
        sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(404, "Fără fotografie")
    import asyncio
    data, ct = await asyncio.to_thread(get_object, doc["storage_path"])
    return Response(content=data, media_type=doc.get("content_type") or ct,
                    headers={"Cache-Control": "public, max-age=3600"})


@public_router.get("/public/passport/{slug}/design-concept-render")
async def passport_design_concept_render(slug: str):
    prop = await _prop_by_slug(slug)
    privacy = {**DEFAULT_PRIVACY, **(prop.get("passport", {}).get("privacy") or {})}
    if not privacy.get("show_design_concept"):
        raise HTTPException(404, "Conceptul nu este public")
    vc = await db.digital_twin_design_concepts.find_one(
        {"property_id": str(prop["_id"]), "status": "verified", "render_object_path": {"$ne": None}},
        sort=[("validated_at", -1), ("created_at", -1)])
    if not vc:
        raise HTTPException(404, "Fără render")
    import asyncio
    data, ct = await asyncio.to_thread(get_object, vc["render_object_path"])
    return Response(content=data, media_type=vc.get("render_mime") or ct or "image/png",
                    headers={"Cache-Control": "public, max-age=3600"})
