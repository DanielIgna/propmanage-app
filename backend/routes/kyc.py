"""KYC (Know Your Customer) — specialist identity verification.

Pipeline:
  not_started → uploaded → reviewing → approved | rejected

Specialist uploads 3 documents (base64-encoded, < 3MB each):
  - id_front: front side of national ID
  - id_back: back side of national ID
  - selfie: live selfie holding the ID

Admin (or any sub-admin with scope=security) can approve/reject from a
review queue. On approve: sets ``user.verified=true``, ``tier=VERIFIED``,
``kyc_approved_at`` timestamp, and runs the existing tier milestone hook.

Storage: documents persisted in the ``kyc_documents`` collection. Base64
strings (max ~3MB each) — small enough for MongoDB document size limits.
Future migration target: object storage via Emergent integration.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role

logger = logging.getLogger("propmanage.kyc")
router = APIRouter(prefix="/api/kyc", tags=["kyc"])

MAX_B64_SIZE = 4_500_000  # ~3.4MB binary after base64 decode

KycStatus = Literal["not_started", "uploaded", "reviewing", "approved", "rejected"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_data_url(b64: str) -> str:
    if not b64:
        return ""
    if b64.startswith("data:"):
        # data:image/jpeg;base64,XXXXXX
        try:
            return b64.split(",", 1)[1]
        except IndexError:
            return ""
    return b64


def _validate_image(name: str, b64: str) -> None:
    if not b64:
        raise HTTPException(400, f"Câmpul '{name}' este obligatoriu")
    if len(b64) > MAX_B64_SIZE:
        raise HTTPException(413, f"'{name}' depășește limita de ~3MB")


class KYCUploadIn(BaseModel):
    id_front: str = Field(..., description="Base64 (with or without data:url prefix)")
    id_back: str
    selfie: str
    full_name_on_id: Optional[str] = None
    national_id_number: Optional[str] = None  # CNP (masked server-side)


class KYCDecisionIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


def _public_payload(doc: dict, include_files: bool = False) -> dict:
    """Serialize a kyc_documents row safely. Files are heavy → omit by default."""
    payload = {
        "id": doc.get("id"),
        "user_id": doc.get("user_id"),
        "user_email": doc.get("user_email"),
        "user_name": doc.get("user_name"),
        "status": doc.get("status"),
        "submitted_at": doc.get("submitted_at"),
        "reviewed_at": doc.get("reviewed_at"),
        "reviewed_by_email": doc.get("reviewed_by_email"),
        "review_note": doc.get("review_note"),
        "full_name_on_id": doc.get("full_name_on_id"),
        "national_id_masked": doc.get("national_id_masked"),
    }
    if include_files:
        payload["id_front"] = doc.get("id_front")
        payload["id_back"] = doc.get("id_back")
        payload["selfie"] = doc.get("selfie")
    # AI verification result (lightweight, always include if present)
    ai = doc.get("ai_verification")
    if ai:
        payload["ai_verification"] = {
            "ran_at": ai.get("ran_at"),
            "model": ai.get("model"),
            "match_score": ai.get("match_score"),
            "flags": ai.get("flags") or [],
            "summary": ai.get("summary"),
            "recommendation": ai.get("recommendation"),
            "error": ai.get("error"),
        }
    return payload


def _mask_cnp(cnp: Optional[str]) -> Optional[str]:
    if not cnp:
        return None
    s = "".join(ch for ch in cnp if ch.isdigit())
    if len(s) < 6:
        return "***"
    return f"{s[:3]}******{s[-2:]}"


async def _run_ai_verification(kyc_id: str) -> dict:
    """Call Claude Sonnet vision to cross-check ID + selfie. Returns score + flags.

    Stored on the kyc_documents row as ``ai_verification``. Never raises —
    on error, sets ``error`` field and an empty score.
    """
    import os
    import json
    doc = await db.kyc_documents.find_one({"id": kyc_id})
    if not doc:
        return {"error": "kyc_not_found"}

    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        return {"error": "EMERGENT_LLM_KEY missing"}

    result = {
        "ran_at": _now_iso(),
        "model": "claude-sonnet-4-5-20250929",
        "match_score": None,
        "flags": [],
        "summary": "",
        "raw": "",
        "error": None,
    }
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

        # Strip any data: url prefix already done at upload time; values are pure base64
        id_front_img = ImageContent(image_base64=doc.get("id_front", ""))
        selfie_img = ImageContent(image_base64=doc.get("selfie", ""))

        system_msg = (
            "You are a KYC document verification assistant. You receive a national ID "
            "(front side) and a live selfie of the same person. Your job: return a "
            "STRICT JSON object only — no markdown, no commentary. The schema is:\n"
            "{\"match_score\": <0-100>, \"flags\": [<short_string>, ...], \"summary\": <one-line>}\n\n"
            "Scoring rules:\n"
            " - 90-100 = clearly same person, ID readable, no manipulation\n"
            " - 60-89  = likely same, minor quality issues (blur, lighting)\n"
            " - 30-59  = uncertain, document or face partially obscured\n"
            " - 0-29   = mismatch or suspicious (different person, fake ID, screen capture)\n\n"
            "Flag examples: \"face_match_good\", \"face_match_uncertain\", \"text_blur_high\", "
            "\"selfie_lighting_poor\", \"id_partially_covered\", \"possible_screen_capture\", "
            "\"selfie_no_id_visible\", \"id_country_unsupported\".\n\n"
            "Respond with ONLY the JSON object."
        )
        user_text = "Verify these two images: first is the national ID front; second is the live selfie."

        chat = LlmChat(
            api_key=key,
            session_id=f"kyc-verify-{kyc_id}",
            system_message=system_msg,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        text = await chat.send_message(UserMessage(
            text=user_text,
            file_contents=[id_front_img, selfie_img],
        ))
        result["raw"] = (text or "")[:2000]

        # Parse JSON best-effort (Claude sometimes wraps in ```json fences)
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
            ms = parsed.get("match_score")
            if isinstance(ms, (int, float)):
                result["match_score"] = max(0, min(100, int(ms)))
            flags = parsed.get("flags") or []
            if isinstance(flags, list):
                result["flags"] = [str(f)[:60] for f in flags][:10]
            result["summary"] = str(parsed.get("summary", ""))[:200]
        except Exception as e:  # noqa: BLE001
            result["error"] = f"parse_error: {str(e)[:80]}"
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[kyc.ai_verify] {kyc_id}: {e}")
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    # Recommendation mode (GDPR-safe): AI recomandă, adminul decide
    _NEGATIVE_FLAGS = {
        "possible_screen_capture", "id_partially_covered", "selfie_no_id_visible",
        "id_country_unsupported", "face_match_uncertain",
    }
    ms = result.get("match_score")
    if result.get("error") or ms is None:
        result["recommendation"] = "review"
    elif ms >= 85 and not (set(result.get("flags") or []) & _NEGATIVE_FLAGS):
        result["recommendation"] = "approve"
    else:
        result["recommendation"] = "review"

    # Persist
    await db.kyc_documents.update_one(
        {"id": kyc_id},
        {"$set": {"ai_verification": result}},
    )

    # Orchestrator: KYC pre-validation reporter (ledger + notificare admin)
    try:
        from orchestrator.engine import emit_signal
        owner = await db.users.find_one({"_id": ObjectId(doc["user_id"])}, {"name": 1}) if doc.get("user_id") else None
        await emit_signal("kyc_prevalidated", {
            "kyc_id": kyc_id,
            "user_name": (owner or {}).get("name"),
            "recommendation": result["recommendation"],
            "match_score": result.get("match_score"),
            "flags": result.get("flags") or [],
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[kyc.ai_verify] orchestrator signal failed: {e}")

    # Auto-approve gate (config in app_settings.kyc_auto_approve)
    try:
        settings = await db.app_settings.find_one({"_id": "app_settings"}) or {}
        cfg = (settings.get("kyc_auto_approve") or {})
        enabled = bool(cfg.get("enabled"))
        min_score = int(cfg.get("min_score", 92))
        block_negative = bool(cfg.get("block_on_negative_flags", True))
        if enabled and result.get("match_score") is not None and result["match_score"] >= min_score:
            has_negative = False
            if block_negative:
                neg_patterns = (
                    "poor", "blur_high", "covered", "mismatch", "suspicious",
                    "screen_capture", "no_id_visible", "uncertain", "fake",
                    "verification_impossible", "no_visual_data", "images_not_loaded",
                )
                for f in result.get("flags", []):
                    fl = str(f).lower()
                    if any(p in fl for p in neg_patterns):
                        has_negative = True
                        break
            if not has_negative:
                # auto-approve mirroring kyc_approve()
                fresh_doc = await db.kyc_documents.find_one({"id": kyc_id})
                if fresh_doc and fresh_doc.get("status") in {"uploaded", "reviewing"}:
                    now_iso = _now_iso()
                    auto_note = f"Auto-approved by AI (score {result['match_score']}/100, no negative flags)."
                    await db.kyc_documents.update_one(
                        {"id": kyc_id},
                        {"$set": {
                            "status": "approved",
                            "reviewed_at": now_iso,
                            "reviewed_by": "system_ai",
                            "reviewed_by_email": "ai-auto@propmanage.io",
                            "review_note": auto_note,
                            "auto_approved": True,
                        }},
                    )
                    # Promote the user
                    try:
                        from bson import ObjectId as _OID
                        spec = await db.users.find_one({"_id": _OID(fresh_doc["user_id"])})
                        if spec and spec.get("role") == "specialist":
                            await db.users.update_one(
                                {"_id": spec["_id"]},
                                {"$set": {
                                    "verified": True,
                                    "tier": "VERIFIED",
                                    "verified_at": now_iso,
                                    "kyc_id": kyc_id,
                                    "kyc_approved_at": now_iso,
                                }},
                            )
                            try:
                                from services import notify
                                await notify(
                                    fresh_doc["user_id"],
                                    "✅ KYC aprobat automat",
                                    f"AI a confirmat identitatea (scor {result['match_score']}/100). Contul tău este acum VERIFIED.",
                                    type_="kyc_approved",
                                    link="/specialist",
                                )
                            except Exception:  # noqa: BLE001
                                pass
                    except Exception as e:  # noqa: BLE001
                        logger.warning(f"[kyc.auto_approve] promote user failed: {e}")
                    logger.info(f"[kyc] auto-approved {kyc_id} (score={result['match_score']})")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[kyc.auto_approve_gate] {e}")

    return result


@router.post("/admin/{kyc_id}/ai-verify")
async def admin_run_ai_verify(kyc_id: str, user: dict = Depends(require_role("admin"))):
    """Manually re-run AI verification (e.g. after a model update)."""
    result = await _run_ai_verification(kyc_id)
    return {"ok": True, "ai_verification": result}


# ============================================================================
# AUTO-APPROVE CONFIG (super-admin only)
# ============================================================================
class AutoApproveConfig(BaseModel):
    enabled: bool = False
    min_score: int = Field(92, ge=50, le=100)
    block_on_negative_flags: bool = True


@router.get("/admin/config/auto-approve")
async def get_auto_approve_config(user: dict = Depends(require_role("admin"))):
    doc = await db.app_settings.find_one({"_id": "app_settings"}) or {}
    cfg = doc.get("kyc_auto_approve") or {}
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "min_score": int(cfg.get("min_score", 92)),
        "block_on_negative_flags": bool(cfg.get("block_on_negative_flags", True)),
    }


@router.put("/admin/config/auto-approve")
async def set_auto_approve_config(
    payload: AutoApproveConfig,
    user: dict = Depends(require_role("admin")),
):
    # Only super admin can change this guardrail
    from sub_admin_deps import is_super_admin
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate modifica auto-approve.")
    await db.app_settings.update_one(
        {"_id": "app_settings"},
        {"$set": {"kyc_auto_approve": payload.model_dump(), "kyc_auto_approve_updated_at": _now_iso(), "kyc_auto_approve_updated_by": user["id"]}},
        upsert=True,
    )
    return {"ok": True, **payload.model_dump()}



@router.get("/status")
async def my_kyc_status(user: dict = Depends(get_current_user)):
    """Return the current user's KYC state (any role can call)."""
    latest = await db.kyc_documents.find_one(
        {"user_id": user["id"]},
        sort=[("submitted_at", -1)],
    )
    if not latest:
        return {
            "status": "not_started",
            "can_upload": user.get("role") == "specialist",
            "verified_in_user_doc": bool(user.get("verified")),
        }
    return {
        **_public_payload(latest, include_files=False),
        "can_upload": latest.get("status") in {"rejected", "not_started"},
        "verified_in_user_doc": bool(user.get("verified")),
    }


@router.post("/upload")
async def upload_kyc(payload: KYCUploadIn, background_tasks: BackgroundTasks, user: dict = Depends(require_role("specialist"))):
    """Specialist uploads ID front + back + selfie. Idempotent if rejected (creates new row)."""
    id_front = _strip_data_url(payload.id_front)
    id_back = _strip_data_url(payload.id_back)
    selfie = _strip_data_url(payload.selfie)
    _validate_image("id_front", id_front)
    _validate_image("id_back", id_back)
    _validate_image("selfie", selfie)

    # Block re-upload if currently uploaded/reviewing/approved
    latest = await db.kyc_documents.find_one(
        {"user_id": user["id"]},
        sort=[("submitted_at", -1)],
    )
    if latest and latest.get("status") in {"uploaded", "reviewing", "approved"}:
        raise HTTPException(
            409,
            f"KYC deja '{latest.get('status')}'. Așteaptă review-ul administratorului.",
        )

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user.get("email"),
        "user_name": user.get("name"),
        "status": "uploaded",
        "submitted_at": _now_iso(),
        "id_front": id_front,
        "id_back": id_back,
        "selfie": selfie,
        "full_name_on_id": (payload.full_name_on_id or "").strip()[:120] or None,
        "national_id_masked": _mask_cnp(payload.national_id_number),
        # raw CNP stored hashed/encrypted in a real system; we keep masked only for demo
    }
    await db.kyc_documents.insert_one(doc)
    # Fire AI verification in background (Claude Sonnet vision)
    background_tasks.add_task(_run_ai_verification, doc["id"])
    # Notify admins (security scope) + super admin
    try:
        from services import notify
        async for reviewer in db.users.find({
            "role": "admin",
            "$or": [{"admin_scope": "general"}, {"admin_scope": "security"}],
            "is_active": {"$ne": False},
        }):
            try:
                await notify(
                    str(reviewer["_id"]),
                    "📋 KYC nou de revizuit",
                    f"{user.get('email')} a trimis documentele de identitate pentru verificare.",
                    type_="kyc_pending",
                    link="/admin",
                )
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return _public_payload(doc, include_files=False)


# ============================================================================
# ADMIN / OPERATOR REVIEW ENDPOINTS
# ============================================================================
@router.get("/admin/queue")
async def kyc_queue(
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Admin / operator: list KYC submissions."""
    if user.get("role") not in {"admin", "operator"}:
        raise HTTPException(403, "Admin/operator role required")
    q: dict = {}
    if status and status not in {"all", "default"}:
        q["status"] = status
    elif status is None:
        # default view = pending review
        q["status"] = {"$in": ["uploaded", "reviewing"]}
    # else: "all" → no status filter
    limit = max(1, min(int(limit), 200))
    cursor = db.kyc_documents.find(q, sort=[("submitted_at", -1)]).limit(limit)
    items = [_public_payload(d, include_files=False) async for d in cursor]
    # Counters per status for chips
    counts: dict = {}
    async for d in db.kyc_documents.aggregate([
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]):
        counts[d.get("_id") or "unknown"] = d.get("n", 0)
    return {"items": items, "count": len(items), "counts": counts}


@router.get("/admin/{kyc_id}")
async def kyc_detail(kyc_id: str, user: dict = Depends(get_current_user)):
    """Admin/operator: fetch full KYC doc with base64 files for review modal."""
    if user.get("role") not in {"admin", "operator"}:
        raise HTTPException(403, "Admin/operator role required")
    doc = await db.kyc_documents.find_one({"id": kyc_id})
    if not doc:
        raise HTTPException(404, "KYC not found")
    return _public_payload(doc, include_files=True)


@router.post("/admin/{kyc_id}/approve")
async def kyc_approve(
    kyc_id: str,
    payload: KYCDecisionIn = Body(default=None),
    user: dict = Depends(require_role("admin")),
):
    doc = await db.kyc_documents.find_one({"id": kyc_id})
    if not doc:
        raise HTTPException(404, "KYC not found")
    if doc.get("status") not in {"uploaded", "reviewing"}:
        raise HTTPException(400, f"KYC e deja '{doc.get('status')}'")
    note = (payload.note if payload else None) or ""
    now_iso = _now_iso()
    await db.kyc_documents.update_one(
        {"id": kyc_id},
        {"$set": {
            "status": "approved",
            "reviewed_at": now_iso,
            "reviewed_by": user["id"],
            "reviewed_by_email": user.get("email"),
            "review_note": note[:500],
        }},
    )
    # Promote the user — mirror logic of /api/admin/specialists/{id}/verify
    try:
        from bson import ObjectId as _OID
        spec = await db.users.find_one({"_id": _OID(doc["user_id"])})
        if spec and spec.get("role") == "specialist":
            await db.users.update_one(
                {"_id": spec["_id"]},
                {"$set": {
                    "verified": True,
                    "tier": "VERIFIED",
                    "verified_at": now_iso,
                    "kyc_id": kyc_id,
                    "kyc_approved_at": now_iso,
                }},
            )
            try:
                from services import notify
                await notify(
                    doc["user_id"],
                    "✅ KYC aprobat",
                    "Documentele tale au fost verificate. Contul tău este acum VERIFIED.",
                    type_="kyc_approved",
                    link="/specialist",
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                from routes.tier_milestones import check_tier_milestones
                await check_tier_milestones(doc["user_id"])
            except Exception:  # noqa: BLE001
                pass
            try:
                import asyncio
                from seo_regen import on_specialist_verification_changed
                asyncio.create_task(on_specialist_verification_changed(str(doc["user_id"]), source="kyc_approve"))
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[kyc] failed to promote user after approve: {e}")
    return {"ok": True, "status": "approved", "id": kyc_id}


@router.post("/admin/{kyc_id}/reject")
async def kyc_reject(
    kyc_id: str,
    payload: KYCDecisionIn = Body(default=None),
    user: dict = Depends(require_role("admin")),
):
    doc = await db.kyc_documents.find_one({"id": kyc_id})
    if not doc:
        raise HTTPException(404, "KYC not found")
    if doc.get("status") not in {"uploaded", "reviewing"}:
        raise HTTPException(400, f"KYC e deja '{doc.get('status')}'")
    note = (payload.note if payload else None) or ""
    await db.kyc_documents.update_one(
        {"id": kyc_id},
        {"$set": {
            "status": "rejected",
            "reviewed_at": _now_iso(),
            "reviewed_by": user["id"],
            "reviewed_by_email": user.get("email"),
            "review_note": note[:500],
        }},
    )
    try:
        from services import notify
        await notify(
            doc["user_id"],
            "❌ KYC respins",
            f"Documentele au fost respinse. Motiv: {note or 'necunoscut'}. Poți încărca din nou.",
            type_="kyc_rejected",
            link="/kyc",
        )
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "status": "rejected", "id": kyc_id}
