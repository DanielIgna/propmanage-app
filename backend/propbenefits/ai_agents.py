"""PropBenefits · Agenți AI — AI Success Manager + AI Growth Advisor.

Success Manager: UN obiectiv — succesul utilizatorului. Propune permanent
următoarea acțiune cu cel mai mare impact. Nu notifică inutil — acționează contextual.
Growth Advisor: agent pentru Admin — analizează retenție/campanii/abonamente/orașe
și propune acțiuni concrete (determinist + sinteză LLM prin ai_core, REUSE AI Brain).
"""
import logging
from datetime import datetime, timezone, timedelta

from db import db
from propbenefits import eligibility, ledger, opportunities
from propbenefits.health import subscription_health, ecosystem_health

logger = logging.getLogger("propmanage.propbenefits")


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _now()).isoformat()


def _act(aid, title, value, cta, impact):
    """value = valoarea pentru utilizator (nu funcția); impact = estimare 1-10."""
    return {"id": aid, "title": title, "value": value, "cta_path": cta, "impact": impact}


# ---------------------------------------------------------------------------
# AI Success Manager (per utilizator)
# ---------------------------------------------------------------------------
async def success_manager(user: dict) -> dict:
    ctx = await eligibility.user_context(user)
    health = await subscription_health(user, ctx)
    wallet = await ledger.wallet_summary(ctx["uid"])
    feed = await opportunities.feed(user, limit=3)
    candidates = []

    if wallet["counts"].get("available"):
        soon = sorted(wallet["available"], key=lambda b: b.get("expires_at") or "")[0]
        candidates.append(_act("use_benefit",
                               f"Casa ta are un beneficiu câștigat care așteaptă: „{soon['title']}”",
                               "L-ai câștigat prin comunitate — folosește-l înainte să expire, casa ta merită.",
                               "/client?tab=benefits", 9))
    if ctx["documents"] < 5:
        doc_pct = min(95, ctx["documents"] * 20)
        missing = max(1, 3 - ctx["documents"])
        candidates.append(_act("docs_for_benefit",
                               f"Casa ta este documentată în proporție de {doc_pct}%",
                               f"Cu încă {missing} documente, istoricul tehnic devine mult mai complet — și vei avea acces la beneficii suplimentare atunci când sunt disponibile.",
                               "/client?tab=property", 8))
    if ctx["twins"] == 0:
        candidates.append(_act("activate_twin",
                               "Casa ta nu are încă geamăn digital",
                               "Finalizează Digital Twin și deblochezi Campaniile Premium, Beneficiile Exclusive și un nivel superior de membru.",
                               "/digital-twin", 8))
    if not ctx["hh_score"] and ctx["properties"] > 0:
        candidates.append(_act("house_health",
                               "Casa ta nu are încă un scor de sănătate",
                               "House Health îți arată exact ce merită îngrijit — iar verificările din campaniile active cresc scorul și îți aduc puncte de progres.",
                               "/house-health", 7))
    # ST-001: stocare aproape plină → upgrade (free) sau curățenie (house_health)
    try:
        from storage_service import quota_status
        stq = await quota_status(ctx["uid"])
        if stq and stq["pct"] >= stq["thresholds"][0]:
            if stq["tier"] == "free":
                candidates.append(_act("storage_upgrade",
                                       f"Spațiul de stocare al casei tale este {round(stq['pct'])}% plin",
                                       f"Ai folosit {stq['used_human']} din {stq['quota_human']}. Cu abonamentul House Health primești 5 GB — de 20 de ori mai mult spațiu pentru documentele și amintirile casei.",
                                       "/house-health/upgrade", 9 if stq["pct"] >= stq["thresholds"][1] else 7))
            else:
                candidates.append(_act("storage_cleanup",
                                       f"Spațiul de stocare este {round(stq['pct'])}% plin ({stq['used_human']} din {stq['quota_human']})",
                                       "Șterge documentele sau versiunile vechi ca să faci loc pentru ce contează cu adevărat.",
                                       "/client?tab=property", 6))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[success_manager] storage candidate failed: {e}")
    if feed["opportunities"]:
        top = feed["opportunities"][0]
        candidates.append(_act("claim_opportunity",
                               f"Comunitatea a pregătit pentru casa ta: „{top['title']}”",
                               (top.get("why") or ["Este relevantă pentru casa ta."])[0],
                               "/client?tab=benefits", 7))
    if ctx["subscription_active"] and ctx.get("subscription_expires_at"):
        try:
            days = (datetime.fromisoformat(str(ctx["subscription_expires_at"]).replace("Z", "+00:00")) - _now()).days
            if 0 <= days <= 14:
                # Coordonare 24h cu Renewal Reminder Email: dacă email-ul a fost
                # trimis recent, nu dublăm mesajul de renewal în aceeași zi.
                email_recent = False
                try:
                    from routes.renewal_reminders import renewal_email_sent_recently
                    email_recent = await renewal_email_sent_recently(ctx["uid"])
                except Exception:  # noqa: BLE001
                    email_recent = False
                if not email_recent:
                    candidates.append(_act("renew_subscription",
                                           f"Grija pentru casa ta expiră în {days} zile",
                                           "Reînnoiește abonamentul ca să păstrezi beneficiile active, scorul House Health și puterea comunității de partea ta.",
                                           "/house-health/upgrade", 10))
        except Exception:  # noqa: BLE001
            pass
    if ctx["referrals_claimed"] == 0 and ctx["completed_jobs"] >= 1:
        candidates.append(_act("invite_neighbor",
                               "Un vecin în plus = o comunitate mai puternică pentru casa ta",
                               "Când vecinul invitat își activează abonamentul sau primul serviciu, amândoi primiți un Beneficiu Comunitate.",
                               "/client?tab=settings", 6))

    # PB-003: Community Trust — recomandă, devino ambasador, susține negocierile
    community = []
    try:
        unrecommended = None
        async for req in db.requests.find({"client_id": ctx["uid"], "status": {"$in": ["completed", "confirmed"]},
                                           "specialist_id": {"$ne": None}}).sort("confirmed_at", -1).limit(3):
            if not await db.recommendations.find_one({"request_id": str(req["_id"]), "owner_id": ctx["uid"]}, {"_id": 1}):
                unrecommended = req
                break
        if unrecommended:
            community.append(_act("recommend_specialist",
                                  f"Recomandă specialistul care a lucrat la casa ta ({unrecommended.get('specialist_name') or 'specialistul tău'})",
                                  "Recomandarea ta ajută comunitatea — iar când produce o lucrare confirmată, primești un Beneficiu Comunitate.",
                                  "/client?tab=jobs", 7))
        from propbenefits.trust_engine import ambassador_status, deals_demand
        amb = await ambassador_status(ctx["uid"])
        if not amb["is_ambassador"] and amb["validated"] > 0 and amb["remaining"] == 1:
            community.append(_act("almost_ambassador",
                                  "Mai ai un pas până la statutul de Community Ambassador",
                                  "Încă o recomandare validată și primești badge-ul, beneficiul de ambasador și prioritate la campaniile exclusive.",
                                  "/client?tab=benefits", 9))
        demand = await deals_demand()
        near = next((d for d in demand if d["status"] in ("negociere", "in_lucru")
                     and 0 < (d.get("target_supporters") or 25) - d["counts"]["sustin"] <= 30), None)
        if near:
            need = (near.get("target_supporters") or 25) - near["counts"]["sustin"]
            community.append(_act("support_deal",
                                  f"Negocierea „{near['title']}” mai are nevoie de {need} susținători",
                                  "Susținerea ta apropie comunitatea de un acord mai valoros pentru toți.",
                                  "/client?tab=benefits", 5))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[success_manager] trust candidates failed: {e}")
    community.sort(key=lambda a: -a["impact"])
    candidates.extend(community)

    candidates.sort(key=lambda a: -a["impact"])
    top3_ids = {a["id"] for a in candidates[:3]}
    return {
        "health": {"score": health["score"], "status": health["status"]},
        "next_action": candidates[0] if candidates else None,
        "secondary": candidates[1:3],
        # PB-003: slot dedicat comunității — acțiunile de trust nu sunt niciodată îngropate
        "community_action": next((a for a in community if a["id"] not in top3_ids), None),
        "membership": feed["membership"]["level"],
        "generated_at": _iso(),
    }


# ---------------------------------------------------------------------------
# AI Growth Advisor (Admin) — determinist + sinteză LLM, cache 6h
# ---------------------------------------------------------------------------
async def growth_advisor(refresh: bool = False) -> dict:
    if not refresh:
        cached = await db.pb_advisor_reports.find_one({}, {"_id": 0}, sort=[("generated_at", -1)])
        if cached and cached["generated_at"] > _iso(_now() - timedelta(hours=6)):
            return cached

    eco = await ecosystem_health()
    now = _iso()
    camps = await db.pb_campaigns.find({}, {"_id": 0}).to_list(200)
    camp_stats = [{"title": c["title"], "kind": c["kind"], "status": c["status"],
                   "claims": c.get("claims_count", 0), "max_claims": c.get("max_claims", 0),
                   "budget_used": c.get("budget_used", 0), "budget_total": c.get("budget_total", 0)}
                  for c in camps]
    pending_ref = await db.pb_referral_pending.count_documents({"status": "pending_activation"})
    activated_ref = await db.pb_referral_pending.count_documents({"status": "activated"})
    at_risk = await db.pb_subscription_health.count_documents({"status": "at_risk"})
    watch = await db.pb_subscription_health.count_documents({"status": "watch"})
    expiring = await db.hh_subscriptions.count_documents(
        {"status": "active", "expires_at": {"$gt": now, "$lt": _iso(_now() + timedelta(days=30))}})
    cities = await db.properties.aggregate([
        {"$group": {"_id": {"$ifNull": ["$city", "necunoscut"]}, "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 5}]).to_list(5)

    findings = []
    if at_risk:
        findings.append(f"{at_risk} abonați au Subscription Health „at risk” — AI Success Manager are acțiuni pregătite; verifică lista și contactează-i pe primii 3.")
    if expiring:
        findings.append(f"{expiring} abonamente expiră în următoarele 30 de zile — campanie de reînnoire cu Beneficiu Activ recomandată.")
    stalled = [c for c in camp_stats if c["status"] == "active" and c["claims"] == 0]
    if stalled:
        findings.append(f"{len(stalled)} campanii active fără nicio revendicare ({', '.join(s['title'] for s in stalled[:3])}) — verifică eligibilitatea sau vizibilitatea lor.")
    if pending_ref:
        findings.append(f"{pending_ref} recomandări în așteptarea activării — un impuls de activare (Beneficiu de bun venit vizibil) le poate converti.")
    if not findings:
        findings.append("Nicio alertă critică — concentrează-te pe creșterea campaniilor cu cele mai multe revendicări.")

    summary_text = ""
    try:
        from ai_core.provider import call_llm
        from propbenefits.health import north_star
        ns = await north_star()
        metrics_txt = (f"NORTH STAR: {ns['healthy']} abonamente sănătoase din ținta de 3000 (active: {ns['active']}; "
                       f"dimensiuni: {[(d['label'], d['value']) for d in ns['dimensions']]}) · "
                       f"Ecosystem Health {eco['score']}/100 · retenție 30z {eco['components'][1]['value']}% · "
                       f"campanii: {[(c['title'], c['claims']) for c in camp_stats[:6]]} · "
                       f"referral: {activated_ref} activate / {pending_ref} pending · "
                       f"at-risk {at_risk} · watch {watch} · expiră 30z {expiring} · orașe top {[(c['_id'], c['n']) for c in cities]}")
        r = await call_llm(
            "Ești AI Growth Advisor pentru PropManage (Home Graph, România). Răspunzi DOAR în română, "
            "concis, acționabil. OBIECTIV COMUN (North Star, împărțit cu AI Success Manager): 3.000 de abonamente "
            "ACTIVE și SĂNĂTOASE — abonați care folosesc platforma, își întrețin locuințele, beneficiază de campanii "
            "și recomandă alți membri. REGULĂ: PropManage nu vinde reduceri — construiește valoare pentru proprietari "
            "prin puterea comunității. Format: 3-5 acțiuni numerotate, fiecare cu impactul estimat asupra North Star.",
            f"Datele reale ale platformei azi: {metrics_txt}. Constatări deterministe: {findings}. Propune acțiunile săptămânii.")
        summary_text = r.get("text", "")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[growth_advisor] LLM synthesis failed: {e}")

    report = {
        "generated_at": _iso(),
        "ecosystem_score": eco["score"],
        "metrics": {"subscriptions_active": eco["components"][0]["value"],
                    "retention_pct": eco["components"][1]["value"],
                    "at_risk": at_risk, "watch": watch, "expiring_30d": expiring,
                    "referral_pending": pending_ref, "referral_activated": activated_ref,
                    "top_cities": [{"city": c["_id"], "properties": c["n"]} for c in cities]},
        "campaigns": camp_stats,
        "findings": findings,
        "ai_recommendations": summary_text,
    }
    await db.pb_advisor_reports.insert_one({**report})
    return report
