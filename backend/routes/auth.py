"""Auth router: register, login, logout, me, ws-token, dual-role, profile, password,
GDPR export/delete, referral, support/contact, push subscribe, 2FA, Google OAuth,
digest preference/preview."""
import os
import io
import logging
import jwt
import asyncio
import secrets
import base64 as b64
import httpx
import pyotp
import qrcode
from typing import Optional, Dict, List, Literal, Any
import uuid
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from pydantic import BaseModel, Field

from db import db
from core_utils import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    serialize_doc, set_auth_cookies, JWT_SECRET, JWT_ALGORITHM,
)
from deps import get_current_user, require_role, block_in_impersonation, block_impersonation_dep
from services import send_email, VAPID_PUBLIC_KEY
from models import (
    RegisterIn, LoginIn, TotpVerifyIn, ALLOWED_SPECIALTIES, ConsentUpdateIn,
)
from email_service import send_template, tpl_welcome
from digest import DIGEST_BUILDERS, run_daily_digests

logger = logging.getLogger(__name__)


# --- Admin whitelist enforcement ---
def _admin_whitelist() -> set:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def _enforce_admin_role(user: dict) -> dict:
    """If user email is in ADMIN_EMAILS → ensure role=admin. Otherwise demote off admin.
    Sub-admins (with admin_scope set) are EXEMPT — they keep / are promoted to role=admin.
    Returns the (possibly mutated) user dict; persists changes to DB."""
    if not user:
        return user
    email = (user.get("email") or "").lower()
    role = user.get("role")
    whitelist = _admin_whitelist()
    has_scope = bool(user.get("admin_scope"))  # sub-admin marker
    if email in whitelist and role != "admin":
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"role": "admin"}})
        user["role"] = "admin"
    elif has_scope and role != "admin":
        # Sub-admin lost role somehow → restore it (so login flow always promotes them)
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"role": "admin"}})
        user["role"] = "admin"
    elif email not in whitelist and role == "admin" and not has_scope:
        # demote stray admins to operator (keeps moderate access for testing)
        # but NEVER demote sub-admins (who are intentionally given role=admin with a scope)
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"role": "operator"}})
        user["role"] = "operator"
    return user

router = APIRouter(prefix="/api", tags=["auth"])


# ============= REGISTER =============
async def _record_consent(user_id: str, email: str, consent_type: str, accepted: bool, ip: str = "", user_agent: str = "", source: str = "register"):
    """Append immutable entry to consent_audit_log. Never raises."""
    try:
        await db.consent_audit_log.insert_one({
            "user_id": user_id,
            "email": email,
            "consent_type": consent_type,  # terms | privacy | marketing | cookies_*
            "accepted": bool(accepted),
            "ip": ip[:64],
            "user_agent": user_agent[:200],
            "source": source,  # register | settings | cookie_banner
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as _e:  # noqa: BLE001
        import logging
        logging.getLogger("propmanage.consent").warning(f"[consent_audit_log] {_e}")


def _gen_email_verification_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


@router.post("/auth/register")
async def register(data: RegisterIn, request: Request, response: Response):
    email = data.email.lower()
    # GDPR gate: terms + privacy MUST be accepted explicitly
    if not data.terms_accepted:
        raise HTTPException(400, "Trebuie să accepți Termenii și Condițiile pentru a continua")
    if not data.privacy_policy_accepted:
        raise HTTPException(400, "Trebuie să accepți Politica de Confidențialitate pentru a continua")
    # Phone: obligatoriu doar pentru specialiști (EO-006 F6 — progressive disclosure pentru clienți)
    phone_raw = (data.phone or "").strip()
    import re
    phone_digits = re.sub(r"[^\d+]", "", phone_raw) if phone_raw else ""
    if phone_raw and not phone_digits:
        raise HTTPException(400, "Format telefon invalid. Folosește +40 7XX XXX XXX sau 07XX XXX XXX")
    if data.role == "specialist" and not phone_digits:
        raise HTTPException(400, "Numărul de telefon este obligatoriu pentru specialiști")
    if phone_digits and not re.match(r"^\+?\d{8,15}$", phone_digits):
        raise HTTPException(400, "Format telefon invalid. Folosește +40 7XX XXX XXX sau 07XX XXX XXX")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    now_iso = datetime.now(timezone.utc).isoformat()
    verif_token = _gen_email_verification_token()
    verif_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    from tenancy import resolve_tenant_slug
    tenant_id = await resolve_tenant_slug(request)
    user = {
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "tenant_id": tenant_id,
        "phone": phone_digits,
        "wallet_balance": 500.0 if data.role == "specialist" else 0.0,
        "tokens": 0,
        "rating": 5.0 if data.role == "specialist" else None,
        "reviews_count": 0,
        "verified": False,
        "tier": "ENTRY" if data.role == "specialist" else None,
        "created_at": now_iso,
        # GDPR + verification
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        "marketing_consent": bool(data.marketing_consent),
        "consent_updated_at": now_iso,
        "email_verified": False,
        "phone_verified": False,
        "email_verification_token": verif_token,
        "email_verification_expires_at": verif_expires,
    }
    if data.role == "specialist":
        cats = data.service_categories or ([data.specialty] if data.specialty else [])
        cats = [c for c in cats if c]
        if not cats:
            raise HTTPException(400, "Selectează cel puțin o categorie de specialitate")
        invalid = [c for c in cats if c not in ALLOWED_SPECIALTIES]
        if invalid:
            raise HTTPException(400, f"Categorii invalide: {', '.join(invalid)}")
        user["specialty"] = data.specialty or cats[0]
        user["service_categories"] = cats
        user["coverage_zones"] = data.coverage_zones or []
        user["availability_status"] = "available"
        user["documents"] = []
    elif data.role == "client":
        user["zone"] = data.zone
    if data.referrer_id:
        try:
            sponsor = await db.users.find_one({"_id": ObjectId(data.referrer_id)})
            if sponsor and not sponsor.get("deleted"):
                user["referrer_id"] = data.referrer_id
                user["referral_bonus_paid"] = False
        except Exception:
            pass
    result = await db.users.insert_one(user)
    uid = str(result.inserted_id)
    # Record consent in immutable audit log
    ip = (request.client.host if request and request.client else "") or ""
    ua = request.headers.get("user-agent", "") if request else ""
    await _record_consent(uid, email, "terms", True, ip, ua, source="register")
    await _record_consent(uid, email, "privacy", True, ip, ua, source="register")
    await _record_consent(uid, email, "marketing", bool(data.marketing_consent), ip, ua, source="register")
    access = create_access_token(uid, email, data.role)
    refresh = create_refresh_token(uid)
    set_auth_cookies(response, access, refresh)
    user["id"] = uid
    user.pop("_id", None)
    user.pop("password_hash", None)
    user.pop("email_verification_token", None)  # never leak to FE
    await send_template(tpl_welcome, data.name, data.role, to=email)
    # Send email verification link (best-effort)
    try:
        from email_service import tpl_email_verification
        await send_template(tpl_email_verification, data.name, verif_token, to=email)
    except Exception as _e:  # noqa: BLE001
        import logging
        logging.getLogger("propmanage.auth").warning(f"[EmailVerify] send failed: {_e}")
    # Sprint C bonus — Welcome voucher for new specialists (50% off first lead fee)
    if data.role == "specialist":
        try:
            from routes.marketplace_offers import issue_welcome_voucher_for_specialist
            await issue_welcome_voucher_for_specialist(uid, email)
        except Exception as _e:  # noqa: BLE001
            import logging
            logging.getLogger("propmanage.auth").warning(f"[WelcomeVoucher] failed: {_e}")
    # Community auto-welcome post (Feb 2026) — for all new users with MEMBER_OF_THE_WEEK badge
    try:
        from routes.community import auto_create_welcome_topic
        await auto_create_welcome_topic(user_id=uid, user_name=data.name, role=data.role)
    except Exception as _e:  # noqa: BLE001
        import logging
        logging.getLogger("propmanage.auth").warning(f"[CommunityWelcome] failed: {_e}")
    # Schedule 3-email onboarding drip for new specialists (Day 1, 3, 7) — best-effort
    if data.role == "specialist":
        try:
            from onboarding_emails import enqueue_specialist_onboarding
            await enqueue_specialist_onboarding(uid, email, data.name)
        except Exception as _e:  # noqa: BLE001
            import logging
            logging.getLogger("propmanage.auth").warning(f"[Onboarding] enqueue failed: {_e}")
    # Auto-send role-specific training doc (best-effort, non-blocking)
    try:
        from docs_service import email_doc_to_user
        from docs_content import get_doc
        # Map user role to doc slug (qa users would be admins; specialist/operator/client/admin)
        doc_slug = data.role if get_doc(data.role) else None
        if doc_slug:
            await email_doc_to_user(
                doc_slug, email,
                recipient_name=data.name,
                include_pdf=True,
                sent_by="auto-onboarding",
            )
    except Exception as e:
        import logging
        logging.getLogger("propmanage.auth").warning(f"[Onboarding] doc send failed: {e}")
    return user


# ============= LOGIN (with rate limit + 2FA) =============
_login_attempts: Dict[str, List[datetime]] = {}
LOGIN_MAX_ATTEMPTS = 8
LOGIN_WINDOW_SECONDS = 60


def _check_login_rate_limit(ip: str):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    attempts = [t for t in _login_attempts.get(ip, []) if t > cutoff]
    _login_attempts[ip] = attempts
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Prea multe încercări. Reîncearcă în 60 secunde.")


def _record_failed_login(ip: str):
    _login_attempts.setdefault(ip, []).append(datetime.now(timezone.utc))


@router.post("/auth/login")
async def login(data: LoginIn, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(ip)
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        _record_failed_login(ip)
        raise HTTPException(401, "Invalid credentials")

    if user.get("totp_enabled"):
        if not data.totp_code:
            raise HTTPException(202, {"error": "totp_required", "message": "2FA code required"})
        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(data.totp_code, valid_window=1):
            _record_failed_login(ip)
            raise HTTPException(401, "Invalid 2FA code")

    # Sub-admin lockout: deactivated admins cannot log in
    if user.get("role") == "admin" and user.get("is_active") is False:
        raise HTTPException(403, "Cont dezactivat. Contactează super-administratorul.")

    _login_attempts.pop(ip, None)
    user = await _enforce_admin_role(user)
    uid = str(user["_id"])
    # Track last_seen for beta engagement analytics
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}}
    )
    access = create_access_token(uid, email, user.get("role", "client"))
    refresh = create_refresh_token(uid)
    set_auth_cookies(response, access, refresh)
    # Clean any leftover impersonation stash cookie so a fresh login never
    # auto-resumes a previous "View as User" session. Without this, an admin
    # who closed the browser mid-impersonation would re-open the app and still
    # see the red "Vizionezi ca …" banner from the past session.
    response.delete_cookie("admin_access_token", path="/")
    return serialize_doc(user)


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    # Also clear any stashed admin token (impersonation safety)
    response.delete_cookie("admin_access_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    # Load tutorial seen flag fresh from DB so it reflects across sessions
    doc = await db.users.find_one(
        {"_id": ObjectId(user["id"])},
        {
            "tutorial_seen": 1, "ai_admin_tour_seen": 1, "dashboard_tour_completed": 1,
            "email": 1, "role": 1, "password_hash": 1, "google_auth": 1,
            "dual_role_enabled": 1, "active_view": 1,
            "avatar": 1, "avatar_source": 1, "picture": 1,
            "experience_tier": 1, "experience_tier_locked": 1,
            "admin_scope": 1, "admin_seniority": 1, "tenant_id": 1,
        },
    )
    user["tutorial_seen"] = bool((doc or {}).get("tutorial_seen", False))
    user["tenant_id"] = (doc or {}).get("tenant_id") or "main"
    user["ai_admin_tour_seen"] = bool((doc or {}).get("ai_admin_tour_seen", False))
    user["dashboard_tour_completed"] = bool((doc or {}).get("dashboard_tour_completed", False))
    # `has_password` lets frontend show "Backup password" button only for Google-only accounts
    user["has_password"] = bool((doc or {}).get("password_hash"))
    user["google_auth"] = bool((doc or {}).get("google_auth"))
    # Dual-role view state (multi-profile system)
    user["dual_role_enabled"] = bool((doc or {}).get("dual_role_enabled", False))
    user["active_view"] = (doc or {}).get("active_view") or user.get("role")
    # SELF-HEALING: prevent the impossible state where dual_role_enabled=True
    # but the user has NO specialist profile data (no service_categories, no
    # coverage_zones, no specialist_onboarded_at) AND role is not "specialist".
    # This state can be reached via manual DB edits / admin testing and would
    # cause the dashboard guard (DashShared) to bounce the user to the wrong
    # role-specific dashboard. Auto-correct it here so the user gets a coherent
    # session on the very next request.
    if user["dual_role_enabled"] and user.get("role") != "specialist":
        has_spec_profile = bool(
            (doc or {}).get("service_categories")
            or (doc or {}).get("coverage_zones")
            or (doc or {}).get("specialist_onboarded_at")
            or (doc or {}).get("specialist_profile_id")
        )
        if not has_spec_profile:
            await db.users.update_one(
                {"_id": ObjectId(user["id"])},
                {"$set": {"dual_role_enabled": False, "active_view": user.get("role")}},
            )
            user["dual_role_enabled"] = False
            user["active_view"] = user.get("role")
            try:
                import logging as _lg
                _lg.getLogger("propmanage.auth").info(
                    "[auth/me] self-healed dual_role state for user=%s role=%s "
                    "(had dual_role_enabled=True but no specialist profile)",
                    user.get("email"), user.get("role"),
                )
            except Exception:  # noqa: BLE001
                pass
    # Avatar metadata for source-aware UI (Google sync / uploaded)
    user["avatar"] = (doc or {}).get("avatar") or user.get("avatar")
    user["avatar_source"] = (doc or {}).get("avatar_source")
    user["picture"] = (doc or {}).get("picture") or ""
    # Experience tier (Progressive Disclosure) — default "junior" for legacy users
    user["experience_tier"] = (doc or {}).get("experience_tier") or "junior"
    user["experience_tier_locked"] = bool((doc or {}).get("experience_tier_locked", False))
    # Enforce admin whitelist on every /me call to catch direct DB tampering or stale tokens.
    if doc:
        fresh = {
            "_id": doc["_id"],
            "email": doc.get("email"),
            "role": doc.get("role"),
            "admin_scope": doc.get("admin_scope"),  # sub-admin marker — exempts from demotion
        }
        await _enforce_admin_role(fresh)
        user["role"] = fresh["role"]
    # `impersonation` field is already injected by get_current_user when applicable.
    return user


class PasswordForgotIn(BaseModel):
    email: str


class PasswordResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/auth/password/forgot")
async def password_forgot(data: PasswordForgotIn):
    """Send a password reset magic link to the user's email if the account exists.
    Always returns 200 + identical message (no email enumeration leak).
    Token is signed JWT with 1h TTL + single-use via jti rotation."""
    email = data.email.strip().lower()
    if not email or "@" not in email:
        # Same response — don't leak validation
        return {"ok": True, "message": "Dacă există un cont cu acest email, vei primi un link în câteva minute."}
    user = await db.users.find_one({"email": email})
    if user and not user.get("banned"):
        token_payload = {
            "sub": str(user["_id"]),
            "email": email,
            "type": "password_reset",
            "jti": secrets.token_urlsafe(12),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        # Store jti so it can only be used once
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "pw_reset_jti": token_payload["jti"],
                "pw_reset_requested_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
        front_url = os.environ.get("FRONTEND_URL", "https://propmanage.ro")
        reset_url = f"{front_url}/reset-password?token={token}"
        name = user.get("name") or "utilizator"
        html = (
            f"<div style='font-family: Inter, sans-serif; max-width:560px; margin:0 auto; "
            f"background:#0a0a0b; color:#fafaf9; padding:24px; border-radius:12px;'>"
            f"<h2 style='font-family: Georgia, serif; color:#d4ff3a;'>Resetează parola PropManage</h2>"
            f"<p>Salut {name},</p>"
            f"<p>Ai cerut resetarea parolei pentru contul <strong>{email}</strong>.</p>"
            f"<p style='margin:24px 0;text-align:center;'>"
            f"<a href='{reset_url}' style='display:inline-block;background:#d4ff3a;color:#0a0a0b;"
            f"padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;'>"
            f"Setează parolă nouă</a></p>"
            f"<p style='color:#a8a29e;font-size:13px;'>Link-ul expiră în <strong>1 oră</strong> și poate fi folosit o singură dată.</p>"
            f"<p style='color:#a8a29e;font-size:13px;'>Dacă NU ai cerut tu această resetare, ignoră emailul — parola ta veche rămâne neschimbată.</p>"
            f"<hr style='border:none;border-top:1px solid #292524; margin:24px 0;'/>"
            f"<p style='color:#78716c;font-size:11px;text-align:center;word-break:break-all;'>"
            f"Dacă butonul nu funcționează, deschide acest link în browser:<br/>{reset_url}</p>"
            f"</div>"
        )
        try:
            await send_email(email, "Resetează parola PropManage", html)
        except Exception as e:
            logger.warning(f"Failed to send reset email to {email}: {e}")
    # Always return success to prevent email enumeration
    return {"ok": True, "message": "Dacă există un cont cu acest email, vei primi un link în câteva minute."}


@router.post("/auth/password/reset")
async def password_reset(data: PasswordResetIn):
    """Consume reset token + set new password. Token must be valid + match stored jti."""
    try:
        payload = jwt.decode(data.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(400, "Token invalid.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Link-ul a expirat. Cere un nou link de resetare.")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Token invalid sau corupt.")

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(404, "Utilizator inexistent.")
    if user.get("banned"):
        raise HTTPException(403, "Cont suspendat.")
    if user.get("pw_reset_jti") != payload.get("jti"):
        raise HTTPException(400, "Link-ul a fost deja folosit. Cere un nou link de resetare.")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": hash_password(data.new_password),
            "pw_reset_jti": None,
            "pw_reset_used_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    return {"ok": True, "email": user.get("email")}


@router.post("/auth/password/send-backup")
async def send_backup_password(user: dict = Depends(get_current_user)):
    """Generate a temporary password, set it on the account, and email it to the user.
    Designed for users logged-in via Google OAuth who have no password and need a
    backup login method (e.g. when SSO is down or on a different device).
    """
    block_in_impersonation(user, "generarea parolei de backup")
    db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not db_user:
        raise HTTPException(404, "Utilizator inexistent.")

    # Generate a strong, human-readable temp password
    temp_pw = secrets.token_urlsafe(9)  # 12-char base64 (e.g. "Vh3K8L_4mPq")
    await db.users.update_one(
        {"_id": db_user["_id"]},
        {"$set": {
            "password_hash": hash_password(temp_pw),
            "password_temp_issued_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    # Send email with the temp password (we never log it server-side)
    email = db_user.get("email")
    name = db_user.get("name") or "utilizator"
    front_url = os.environ.get("FRONTEND_URL", "https://propmanage.ro")
    html = (
        f"<div style='font-family: Inter, sans-serif; max-width:560px; margin:0 auto; "
        f"background:#0a0a0b; color:#fafaf9; padding:24px; border-radius:12px;'>"
        f"<h2 style='font-family: Georgia, serif; color:#d4ff3a;'>Parola ta de backup PropManage</h2>"
        f"<p>Salut {name},</p>"
        f"<p>Ai cerut o parolă de backup pentru contul <strong>{email}</strong>.</p>"
        f"<p>Folosește această parolă pentru a te loga la "
        f"<a href='{front_url}/login' style='color:#d4ff3a;'>{front_url}/login</a> "
        f"când Google OAuth nu este disponibil:</p>"
        f"<div style='background:#fff; color:#0a0a0b; font-family: monospace; font-size:18px; "
        f"font-weight:bold; padding:12px 16px; border-radius:8px; letter-spacing:1px; text-align:center; margin:16px 0;'>"
        f"{temp_pw}"
        f"</div>"
        f"<p style='color:#a8a29e; font-size:13px;'>⚠ Această parolă <strong>înlocuiește</strong> orice "
        f"parolă veche de pe contul tău. Recomandăm să o schimbi imediat după login (Profil → Setări → Parolă).</p>"
        f"<p style='color:#a8a29e; font-size:13px;'>Dacă NU ai cerut tu această parolă, contul tău poate fi "
        f"compromis. Loghează-te imediat și schimbă-o, sau scrie la "
        f"<a href='mailto:contact@propmanage.ro' style='color:#d4ff3a;'>contact@propmanage.ro</a>.</p>"
        f"<hr style='border:none;border-top:1px solid #292524; margin:24px 0;'/>"
        f"<p style='color:#78716c; font-size:11px; text-align:center;'>"
        f"PropManage · operat de VINTAGE FURNITURE S.R.L. · CUI 35250247 · {front_url}</p>"
        f"</div>"
    )
    try:
        await send_email(email, "Parola ta de backup PropManage", html)
    except Exception as e:
        logger.warning(f"Failed to send backup password email to {email}: {e}")
        # Don't reveal email-send failure to the user beyond a generic message;
        # the password IS set in DB regardless, so future logins work.
        raise HTTPException(502, "Parola a fost generată dar email-ul nu a putut fi trimis. Contactează support.")

    return {"ok": True, "email_to": email, "expires_note": "Parola nu expiră — schimb-o din Setări după login."}


@router.post("/auth/tutorial-seen")
async def mark_tutorial_seen(user: dict = Depends(get_current_user)):
    """Mark the first-login tutorial as completed/dismissed by the user."""
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"tutorial_seen": True, "tutorial_seen_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"ok": True}


@router.post("/auth/tutorial-reset")
async def reset_tutorial(user: dict = Depends(get_current_user)):
    """Allow user to re-trigger the tutorial."""
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$unset": {"tutorial_seen": "", "tutorial_seen_at": "", "dashboard_tour_completed": "", "dashboard_tour_completed_at": ""}}
    )
    return {"ok": True}


@router.post("/auth/dashboard-tour-done")
async def mark_dashboard_tour_done(user: dict = Depends(get_current_user)):
    """Mark the role-specific Driver.js dashboard tour as completed/dismissed."""
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"dashboard_tour_completed": True, "dashboard_tour_completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"ok": True}


@router.post("/auth/ai-admin-tour-seen")
async def mark_ai_admin_tour_seen(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"ai_admin_tour_seen": True, "ai_admin_tour_seen_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"ok": True}


@router.post("/auth/ai-admin-tour-reset")
async def reset_ai_admin_tour(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$unset": {"ai_admin_tour_seen": "", "ai_admin_tour_seen_at": ""}}
    )
    return {"ok": True}


@router.get("/auth/ws-token")
async def ws_token(user: dict = Depends(get_current_user)):
    """Issue a short-lived JWT for WebSocket connections."""
    token = create_access_token(user["id"], user["email"], user["role"])
    return {"token": token}


# ============= DUAL-ROLE SWITCHER =============
class SwitchViewIn(BaseModel):
    view: Literal["client", "specialist"]


@router.post("/auth/switch-view")
async def switch_view(data: SwitchViewIn, user: dict = Depends(get_current_user)):
    """Toggle active view for users who have BOTH client + specialist profiles.

    Eligibility: `dual_role_enabled=True` (set when client onboarded to specialist
    via /auth/become-specialist) OR existing verified specialist (legacy path).
    """
    dual_enabled = bool(user.get("dual_role_enabled"))
    is_legacy_verified_spec = user.get("role") == "specialist" and user.get("verified")
    if not (dual_enabled or is_legacy_verified_spec):
        raise HTTPException(
            403,
            "Profilul dublu nu este activ. Adaugă întâi profilul de Specialist din Setări → 'Devino Specialist'.",
        )
    # Additional integrity check: if switching to "specialist", verify a real
    # specialist profile exists. Prevents desynced state where dual_role_enabled
    # is true but no specialist data is set.
    if data.view == "specialist" and user.get("role") != "specialist":
        full = await db.users.find_one({"_id": ObjectId(user["id"])})
        has_spec_profile = bool(
            (full or {}).get("service_categories")
            or (full or {}).get("coverage_zones")
            or (full or {}).get("specialist_onboarded_at")
            or (full or {}).get("specialist_profile_id")
        )
        if not has_spec_profile:
            # Self-heal: clear stale dual-role flag.
            await db.users.update_one(
                {"_id": ObjectId(user["id"])},
                {"$set": {"dual_role_enabled": False, "active_view": user.get("role")}},
            )
            raise HTTPException(
                403,
                "Nu ai un profil de Specialist activ. Adaugă unul din Setări → 'Devino Specialist'.",
            )
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"active_view": data.view}}
    )
    refreshed = await db.users.find_one({"_id": ObjectId(user["id"])})
    return serialize_doc(refreshed)


# ============= BECOME SPECIALIST (Client → dual-role upgrade) =============
class BecomeSpecialistIn(BaseModel):
    phone: str = Field(min_length=8, max_length=30)
    service_categories: list[str] = Field(min_length=1, max_length=10)
    coverage_zones: list[str] = Field(min_length=1, max_length=20)
    bio: Optional[str] = Field(default=None, max_length=1000)


@router.post("/auth/become-specialist")
async def become_specialist(
    data: BecomeSpecialistIn,
    user: dict = Depends(get_current_user),
):
    """Promote a client account to ALSO be a specialist (dual-role).

    - Keeps `role='client'` and `dual_role_enabled=True` so the user can switch
      between views. The specialist features rely on `dual_role_enabled` OR role.
    - Adds specialist fields: service_categories, coverage_zones, phone, bio.
    - Does NOT auto-verify. Specialist must upload KYC docs to get `verified=True`.
    - Enqueues 3-email onboarding drip (same as native specialist signup).
    """
    if user.get("role") not in ("client", "specialist"):
        raise HTTPException(403, "Doar utilizatorii Client pot deveni Specialiști.")
    if user.get("dual_role_enabled"):
        raise HTTPException(400, "Ai deja un profil dual de Specialist activ.")
    # Reject native specialists who haven't opted into dual-mode — their account is
    # already a specialist account. Dual-mode is for clients who additionally want
    # to offer services.
    if user.get("role") == "specialist":
        raise HTTPException(400, "Contul tău este deja un cont de Specialist. Profilul dual este pentru clienții care vor să devină și specialiști.")

    uid = ObjectId(user["id"])
    now_iso = datetime.now(timezone.utc).isoformat()
    patch = {
        "dual_role_enabled": True,
        "active_view": "specialist",  # New specialists start in specialist view
        "service_categories": data.service_categories,
        "coverage_zones": data.coverage_zones,
        "phone": data.phone,
        "bio": data.bio or "",
        # Reset verification — KYC must be completed in specialist dashboard
        "verified": False,
        "tier": None,
        "rating": user.get("rating"),
        "reviews_count": user.get("reviews_count", 0),
        # Wallet stays the same — no welcome bonus, since this is an upgrade
        "specialist_onboarded_at": now_iso,
    }
    # Also set role='specialist' so existing require_role("specialist") guards work
    # while keeping `dual_role_enabled` to allow swapping back to client view.
    patch["role"] = "specialist"

    await db.users.update_one({"_id": uid}, {"$set": patch})

    # Enqueue specialist onboarding emails (best-effort)
    try:
        from onboarding_emails import enqueue_specialist_onboarding
        await enqueue_specialist_onboarding(str(uid), user["email"], user.get("name", ""))
    except Exception as _e:  # noqa: BLE001
        logger.warning(f"[BecomeSpecialist] onboarding enqueue failed: {_e}")

    refreshed = await db.users.find_one({"_id": uid})
    return serialize_doc(refreshed)


# ============= AVATAR FROM GOOGLE =============
@router.post("/auth/refresh-google-avatar")
async def refresh_google_avatar(user: dict = Depends(get_current_user)):
    """Re-apply the stored Google profile picture as the user's avatar.

    Only works for users who linked their Google account (`google_auth=True`)
    AND haven't manually uploaded an avatar (`avatar_source != 'uploaded'`).
    The picture URL is the one captured at the latest Google sign-in.
    """
    doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not doc:
        raise HTTPException(404, "Utilizator inexistent.")
    if not doc.get("google_auth"):
        raise HTTPException(400, "Contul tău nu este conectat cu Google. Re-loghează-te cu Google ca să sincronizezi fotografia.")
    picture = doc.get("picture") or ""
    if not picture:
        raise HTTPException(400, "Google nu a furnizat o fotografie la ultima autentificare.")
    await db.users.update_one(
        {"_id": doc["_id"]},
        {"$set": {"avatar": picture, "avatar_source": "google"}},
    )
    refreshed = await db.users.find_one({"_id": doc["_id"]})
    return serialize_doc(refreshed)


# ============= DUAL-ROLE SWITCHER (legacy alias removed) =============


# ============= PROFILE / PASSWORD =============
class ProfileUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=30)
    zone: Optional[str] = Field(default=None, max_length=80)
    avatar: Optional[str] = Field(default=None, max_length=2_000_000)
    # Specialist-only fields — allowed only when current user has role=specialist (validated below)
    service_categories: Optional[list[str]] = Field(default=None, max_length=20)
    coverage_zones: Optional[list[str]] = Field(default=None, max_length=20)


@router.patch("/auth/profile")
async def update_profile(data: ProfileUpdateIn, user: dict = Depends(get_current_user)):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    # Specialist-scope guard: refuse to set categories/zones on a non-specialist account
    # (dual-role users with role=specialist already passes this check)
    if user.get("role") != "specialist":
        update.pop("service_categories", None)
        update.pop("coverage_zones", None)
    if not update:
        raise HTTPException(400, "Niciun câmp de actualizat.")
    # Track avatar source: if user uploads an avatar, mark it as 'uploaded' so
    # Google re-sync (or auto-refresh) doesn't override their choice.
    if "avatar" in update:
        update["avatar_source"] = "uploaded" if update["avatar"] else None
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    refreshed = await db.users.find_one({"_id": ObjectId(user["id"])})
    return serialize_doc(refreshed)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


@router.post("/auth/change-password")
async def change_password(data: ChangePasswordIn, user: dict = Depends(block_impersonation_dep("schimbarea parolei"))):
    db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not db_user or not verify_password(data.current_password, db_user.get("password_hash", "")):
        raise HTTPException(401, "Parola curentă este incorectă.")
    if data.current_password == data.new_password:
        raise HTTPException(400, "Parola nouă trebuie să fie diferită de cea curentă.")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    return {"ok": True}


# ============= GDPR EXPORT & DELETE =============
@router.post("/auth/account-export")
async def account_export(user: dict = Depends(get_current_user)):
    uid = user["id"]
    db_user = serialize_doc(await db.users.find_one({"_id": ObjectId(uid)}))
    properties = [serialize_doc(d) for d in await db.properties.find({"owner_id": uid}).to_list(500)]
    requests_as_client = [serialize_doc(d) for d in await db.requests.find({"client_id": uid}).to_list(500)]
    requests_as_specialist = [serialize_doc(d) for d in await db.requests.find({"specialist_id": uid}).to_list(500)]
    notifications = [serialize_doc(d) for d in await db.notifications.find({"user_id": uid}).to_list(500)]
    transactions = [serialize_doc(d) for d in await db.transactions.find({"user_id": uid}).to_list(500)]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": db_user,
        "properties": properties,
        "requests_as_client": requests_as_client,
        "requests_as_specialist": requests_as_specialist,
        "notifications": notifications,
        "transactions": transactions,
    }


class AccountDeleteIn(BaseModel):
    password: str
    confirmation: str


@router.post("/auth/account-delete")
async def account_delete(data: AccountDeleteIn, response: Response, user: dict = Depends(block_impersonation_dep("ștergerea contului"))):
    if data.confirmation != "STERGE":
        raise HTTPException(400, "Confirmarea trebuie să fie exact 'STERGE'.")
    db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not db_user or not verify_password(data.password, db_user.get("password_hash", "")):
        raise HTTPException(401, "Parolă incorectă.")
    anonymized = f"deleted_{user['id'][:8]}@propmanage.deleted"
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {
            "email": anonymized,
            "name": "Utilizator șters",
            "phone": None,
            "avatar": None,
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted": True,
        }}
    )
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True, "message": "Cont șters. Datele asociate au fost anonimizate conform GDPR."}


# ============= REFERRAL =============
@router.get("/auth/referral")
async def referral_info(user: dict = Depends(get_current_user)):
    uid = user["id"]
    referred = await db.users.count_documents({"referrer_id": uid})
    converted = await db.users.count_documents({"referrer_id": uid, "referral_bonus_paid": True})
    return {
        "user_id": uid,
        "referred_total": referred,
        "converted_total": converted,
        "tokens_per_conversion": 500,
        "referral_url": f"/register?ref={uid}",
    }


# ============= SUPPORT / CONTACT =============
class ContactIn(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=5, max_length=5000)


@router.post("/support/contact")
async def support_contact(data: ContactIn, user: dict = Depends(get_current_user)):
    """Save contact message to DB + email all admin/operator users so they can respond.

    Persisted in `support_messages` collection for the admin/operator inbox.
    Configure recipients via env `SUPPORT_EMAIL` (fallback) — but ALL admin + operator
    accounts are notified by default so no message is missed.
    """
    safe_subject = data.subject.strip()
    safe_message_html = data.message.strip().replace("\n", "<br/>")
    msg_id = uuid.uuid4().hex
    now_iso = datetime.now(timezone.utc).isoformat()
    # 1) Persist in DB so admin/operator inbox UI can list it
    doc = {
        "id": msg_id,
        "user_id": user.get("id") or str(user.get("_id")),
        "user_name": user.get("name") or "—",
        "user_email": user.get("email") or "—",
        "user_role": user.get("role") or "client",
        "subject": safe_subject[:200],
        "message": data.message.strip()[:5000],
        "status": "new",  # new | in_progress | resolved
        "assigned_to": None,
        "resolved_at": None,
        "resolved_by": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.support_messages.insert_one(doc)
    # 2) Collect all admin + operator emails so they all see the inbox notification
    recipients: List[str] = []
    async for u in db.users.find({"role": {"$in": ["admin", "operator"]}}, {"email": 1}):
        if u.get("email"):
            recipients.append(u["email"])
    fallback = os.environ.get("SUPPORT_EMAIL", "admin@propmanage.io")
    if not recipients:
        recipients = [fallback]
    # 3) Send notifications (fire-and-forget)
    body_admin = (
        f"<h2>Mesaj nou de contact · #{msg_id[:8]}</h2>"
        f"<p><b>De la:</b> {doc['user_name']} ({doc['user_email']})</p>"
        f"<p><b>Rol:</b> {doc['user_role']}</p>"
        f"<p><b>Subiect:</b> {safe_subject}</p>"
        f"<hr/><div>{safe_message_html}</div>"
        f"<hr/><p style='font-size:11px;color:#666'>Răspunde direct pe email la <b>{doc['user_email']}</b> sau gestionează din "
        f"<a href='https://propmanage.ro/admin/support-inbox'>Admin Inbox</a>.</p>"
    )
    for em in recipients:
        asyncio.create_task(send_email(em, f"[PropManage Contact] {safe_subject}", body_admin))
    # 4) Confirmation to sender
    body_user = (
        f"<h2>Mesajul tău a fost primit</h2>"
        f"<p>Salut {user.get('name','')},</p>"
        f"<p>Confirmăm primirea mesajului tău cu subiectul: <b>{safe_subject}</b>.</p>"
        f"<p>Echipa PropManage îți va răspunde în maximum 24h pe adresa <b>{doc['user_email']}</b>.</p>"
        f"<p style='font-size:11px;color:#666'>ID ticket: <code>#{msg_id[:8]}</code></p>"
    )
    if user.get("email"):
        asyncio.create_task(send_email(user["email"], "Am primit mesajul tău - PropManage", body_user))
    return {"ok": True, "id": msg_id}


# ============= ADMIN / OPERATOR SUPPORT INBOX =============
@router.get("/support/inbox")
async def support_inbox_list(
    status: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_role("admin", "operator")),
):
    """List contact messages. Filter by status (new / in_progress / resolved)."""
    q: Dict[str, Any] = {}
    if status in ("new", "in_progress", "resolved"):
        q["status"] = status
    cursor = db.support_messages.find(q).sort("created_at", -1).limit(min(max(int(limit), 1), 500))
    items = []
    async for m in cursor:
        m["_id"] = str(m.get("_id"))
        items.append(m)
    # Counters
    counts = {"new": 0, "in_progress": 0, "resolved": 0}
    async for c in db.support_messages.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        if c.get("_id") in counts:
            counts[c["_id"]] = c.get("n", 0)
    return {"items": items, "counts": counts, "total": len(items)}


class SupportStatusUpdate(BaseModel):
    status: str = Field(..., description="new | in_progress | resolved")


@router.patch("/support/inbox/{msg_id}")
async def support_inbox_update(
    msg_id: str,
    payload: SupportStatusUpdate,
    user: dict = Depends(require_role("admin", "operator")),
):
    if payload.status not in ("new", "in_progress", "resolved"):
        raise HTTPException(400, "Status invalid.")
    update = {
        "status": payload.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.status == "resolved":
        update["resolved_at"] = update["updated_at"]
        update["resolved_by"] = user.get("email") or user.get("id")
    if payload.status == "in_progress":
        update["assigned_to"] = user.get("email") or user.get("id")
    r = await db.support_messages.update_one({"id": msg_id}, {"$set": update})
    if r.matched_count == 0:
        raise HTTPException(404, "Mesaj inexistent.")
    return {"ok": True}


@router.get("/support/contact-info")
async def support_contact_info():
    """Public: returns the support email shown in the Contact modal so users can
    also write directly without using the in-app form. Configured via env
    SUPPORT_CONTACT_EMAIL (preferred) or SUPPORT_EMAIL (fallback)."""
    email = os.environ.get("SUPPORT_CONTACT_EMAIL") or os.environ.get("SUPPORT_EMAIL") or "contact@propmanage.ro"
    return {"email": email, "response_time": "24h"}


# ============= WEB PUSH SUBSCRIPTIONS =============
class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    expirationTime: Optional[int] = None


@router.get("/push/vapid-public-key")
async def push_vapid_public():
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(503, "Push notifications nu sunt configurate pe server.")
    return {"public_key": VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
async def push_subscribe(data: PushSubscriptionIn, user: dict = Depends(get_current_user)):
    await db.push_subscriptions.update_one(
        {"endpoint": data.endpoint},
        {"$set": {
            "user_id": user["id"],
            "endpoint": data.endpoint,
            "keys": {"p256dh": data.keys.p256dh, "auth": data.keys.auth},
            "expiration_time": data.expirationTime,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
         "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"ok": True}


@router.post("/push/unsubscribe")
async def push_unsubscribe(data: PushSubscriptionIn, user: dict = Depends(get_current_user)):
    await db.push_subscriptions.delete_one({"endpoint": data.endpoint, "user_id": user["id"]})
    return {"ok": True}


# ============= 2FA (TOTP) =============
@router.post("/auth/2fa/setup")
async def setup_2fa(user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "configurarea 2FA")
    secret = pyotp.random_base32()
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"totp_pending_secret": secret}}
    )
    issuer = "PropManage"
    otp_uri = pyotp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name=issuer)
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = f"data:image/png;base64,{b64.b64encode(buf.getvalue()).decode()}"
    return {"secret": secret, "otp_uri": otp_uri, "qr_code": qr_data_url}


@router.post("/auth/2fa/verify")
async def verify_2fa(data: TotpVerifyIn, user: dict = Depends(block_impersonation_dep("activarea 2FA"))):
    full_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    secret = full_user.get("totp_pending_secret")
    if not secret:
        raise HTTPException(400, "No 2FA setup in progress")
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(401, "Invalid code")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"totp_enabled": True, "totp_secret": secret}, "$unset": {"totp_pending_secret": ""}}
    )
    return {"ok": True, "enabled": True}


@router.post("/auth/2fa/disable")
async def disable_2fa(data: TotpVerifyIn, user: dict = Depends(block_impersonation_dep("dezactivarea 2FA"))):
    full_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not full_user.get("totp_enabled"):
        raise HTTPException(400, "2FA not enabled")
    totp = pyotp.TOTP(full_user["totp_secret"])
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(401, "Invalid code")
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$unset": {"totp_enabled": "", "totp_secret": ""}}
    )
    return {"ok": True, "enabled": False}


@router.get("/auth/2fa/status")
async def status_2fa(user: dict = Depends(get_current_user)):
    full_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    return {"enabled": bool(full_user.get("totp_enabled"))}


# ============= GOOGLE OAUTH (Own project — Direct Google flow) =============
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleCallbackIn(BaseModel):
    code: str = Field(..., min_length=10, max_length=2048)
    redirect_uri: str = Field(..., min_length=10, max_length=512)


@router.post("/auth/google/callback")
async def google_direct_callback(payload: GoogleCallbackIn, response: Response, request: Request):
    """Direct Google OAuth flow — uses our own Google Cloud project (not Emergent).

    Frontend sends the `code` returned by Google + the exact redirect_uri that
    was used. Backend exchanges code → access_token at Google, fetches user
    profile at Google's userinfo endpoint, then creates/updates the user and
    issues the same JWT cookies as the Emergent flow. Downstream user model
    identical (google_auth=True, avatar_source='google', etc.).
    """
    started_at = datetime.now(timezone.utc)

    def _base_event(**extra):
        ev = {
            "event_type": "google_oauth_direct",
            "flow": "direct",
            "started_at": started_at.isoformat(),
            "ip": request.client.host if request.client else None,
        }
        ev.update(extra)
        return ev

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        await _record_oauth_health(_base_event(outcome="config_error", final_status=500), started_at)
        raise HTTPException(500, "Server misconfigured: GOOGLE_CLIENT_ID/SECRET missing.")

    # Step 1: exchange authorization code for access_token at Google
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            token_r = await http.post(_GOOGLE_TOKEN_URL, data={
                "code": payload.code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": payload.redirect_uri,
                "grant_type": "authorization_code",
            })
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as e:
        logger.error(f"[google_direct_callback] token network error: {e}")
        await _record_oauth_health(_base_event(outcome="network", final_status=503, last_error=f"{type(e).__name__}: {e}"), started_at)
        raise HTTPException(503, f"Google OAuth token endpoint unreachable: {type(e).__name__}") from e

    if token_r.status_code != 200:
        logger.warning(f"[google_direct_callback] token exchange failed status={token_r.status_code} body={token_r.text[:300]}")
        await _record_oauth_health(_base_event(outcome="token_refused", final_status=401, upstream_status=token_r.status_code, last_error=token_r.text[:300]), started_at)
        raise HTTPException(
            401,
            f"Google a refuzat schimbul de cod (HTTP {token_r.status_code}). "
            f"Detaliu: {token_r.text[:200]}. Verifică redirect_uri să fie whitelisted în Google Cloud Console."
        )
    tokens = token_r.json()
    access_token = tokens.get("access_token")
    if not access_token:
        await _record_oauth_health(_base_event(outcome="no_token", final_status=401), started_at)
        raise HTTPException(401, "Google nu a returnat access_token.")

    # Step 2: fetch user profile
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            ui_r = await http.get(_GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as e:
        await _record_oauth_health(_base_event(outcome="userinfo_network", final_status=503, last_error=f"{type(e).__name__}: {e}"), started_at)
        raise HTTPException(503, f"Google userinfo unreachable: {type(e).__name__}") from e

    if ui_r.status_code != 200:
        await _record_oauth_health(_base_event(outcome="userinfo_refused", final_status=401, upstream_status=ui_r.status_code), started_at)
        raise HTTPException(401, f"Google userinfo refuzat (HTTP {ui_r.status_code}).")
    profile = ui_r.json()
    email = (profile.get("email") or "").lower()
    if not email:
        await _record_oauth_health(_base_event(outcome="no_email", final_status=400), started_at)
        raise HTTPException(400, "Google nu a returnat email.")
    name = profile.get("name") or ""
    picture = profile.get("picture") or ""

    # Step 3: upsert user (identical logic to Emergent flow)
    existing = await db.users.find_one({"email": email})
    if existing:
        patch = {"picture": picture, "name": name, "google_auth": True}
        if existing.get("avatar_source") != "uploaded":
            patch["avatar"] = picture
            patch["avatar_source"] = "google" if picture else None
        await db.users.update_one({"_id": existing["_id"]}, {"$set": patch})
        user = await db.users.find_one({"_id": existing["_id"]})
        uid = str(user["_id"])
    else:
        new_user = {
            "email": email, "name": name, "picture": picture,
            "tenant_id": "main",
            "avatar": picture or None, "avatar_source": "google" if picture else None,
            "role": "client", "google_auth": True, "password_hash": "",
            "wallet_balance": 0.0, "tokens": 0,
            "rating": None, "reviews_count": 0, "verified": False, "tier": None,
            "phone": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.users.insert_one(new_user)
        uid = str(result.inserted_id)
        user = new_user
        user["_id"] = result.inserted_id

    user = await _enforce_admin_role(user)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}}
    )
    access = create_access_token(uid, email, user.get("role", "client"))
    refresh = create_refresh_token(uid)
    set_auth_cookies(response, access, refresh)
    # Success (uses same helper for consistency with failure branches)
    await _record_oauth_health(_base_event(outcome="success", final_status=200, email=email), started_at)
    return serialize_doc(user)


# ============= GOOGLE OAUTH (Emergent-managed) =============
@router.post("/auth/google/session")
async def google_session_exchange(request: Request, response: Response):
    """Exchange Emergent session_id for our JWT cookie + user record.

    Calls upstream `demobackend.emergentagent.com` to verify the session and
    retrieve the Google profile. Retries up to 3× with exponential backoff so
    transient upstream slowness (often 5-15s on cold start) doesn't yield a
    520/origin-empty response that users see as "Autentificare Google eșuată".
    Every attempt is recorded in `oauth_health` collection for the
    /admin/auth-health dashboard.
    """
    started_at = datetime.now(timezone.utc)
    health_event = {
        "event_type": "google_oauth_exchange",
        "started_at": started_at.isoformat(),
        "attempts": 0,
        "outcome": None,  # "success" | "user_error" | "upstream_5xx" | "network" | "exhausted"
        "final_status": None,
        "upstream_status": None,
        "duration_ms": None,
        "ip": request.client.host if request.client else None,
    }
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        health_event["outcome"] = "user_error"
        health_event["final_status"] = 400
        await _record_oauth_health(health_event, started_at)
        raise HTTPException(400, "Lipsește header-ul X-Session-ID")
    upstream_status = None
    upstream_body = None
    last_err = None
    data = None
    # Retry loop: 2 attempts, 15s timeout each + 2s backoff between → max ~32s total.
    # MUST stay under the Kubernetes ingress proxy timeout (typically 60s) or the
    # browser sees a generic 502 Bad Gateway from the ingress instead of our 503.
    for attempt in range(2):
        health_event["attempts"] = attempt + 1
        try:
            async with httpx.AsyncClient(timeout=15) as http_client:
                r = await http_client.get(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                    headers={"X-Session-ID": session_id}
                )
                upstream_status = r.status_code
                upstream_body = (r.text or "")[:300]
                health_event["upstream_status"] = upstream_status
                if r.status_code == 200:
                    data = r.json()
                    break
                # 4xx → user-fixable (session expired, redirect URL not whitelisted) — no retry
                if 400 <= r.status_code < 500:
                    logger.warning(f"Emergent OAuth user error: status={upstream_status} body={upstream_body[:200]}")
                    health_event["outcome"] = "user_error"
                    health_event["final_status"] = 401
                    await _record_oauth_health(health_event, started_at)
                    raise HTTPException(
                        401,
                        f"Emergent OAuth a refuzat sesiunea (upstream HTTP {upstream_status}). "
                        f"Detaliu: {upstream_body[:200]}. Cauze posibile: (1) session_id expirat — încearcă din nou rapid, "
                        f"(2) propmanage.ro/auth/callback nu este whitelisted în panoul OAuth Emergent — "
                        f"contactează support@emergent.sh."
                    )
                # 5xx upstream → transient, will retry
                last_err = f"upstream HTTP {r.status_code}"
                logger.warning(f"Emergent OAuth transient {r.status_code} (attempt {attempt+1}/2): {upstream_body[:120]}")
        except HTTPException:
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as e:
            last_err = f"network: {type(e).__name__}: {e}"
            logger.warning(f"Emergent OAuth network error (attempt {attempt+1}/2): {last_err}")
        if attempt < 1:
            await asyncio.sleep(2)  # short backoff to stay under ingress timeout
    if data is None:
        # Both attempts failed — return a SAFE 503 with JSON body so the browser
        # gets an actionable detail instead of a generic ingress 502/520.
        logger.error(f"Emergent OAuth exhausted retries: {last_err}")
        health_event["outcome"] = "exhausted"
        health_event["final_status"] = 503
        health_event["last_error"] = last_err
        await _record_oauth_health(health_event, started_at)
        raise HTTPException(
            503,
            f"Serverul Emergent OAuth nu răspunde (2 încercări, ultima: {last_err}). "
            "Încearcă din nou peste 1-2 minute sau folosește email + parolă."
        )

    email = data.get("email", "").lower()
    name = data.get("name", "")
    picture = data.get("picture", "")

    existing = await db.users.find_one({"email": email})
    if existing:
        # Always refresh stored Google picture so the user can "Refresh from Google"
        # later, but ONLY apply it as the active avatar if they haven't uploaded
        # a custom one.
        patch = {"picture": picture, "name": name, "google_auth": True}
        if existing.get("avatar_source") != "uploaded":
            patch["avatar"] = picture
            patch["avatar_source"] = "google" if picture else None
        await db.users.update_one({"_id": existing["_id"]}, {"$set": patch})
        user = await db.users.find_one({"_id": existing["_id"]})
        uid = str(user["_id"])
    else:
        new_user = {
            "email": email,
            "name": name,
            "picture": picture,
            "tenant_id": "main",
            "avatar": picture or None,
            "avatar_source": "google" if picture else None,
            "role": "client",
            "google_auth": True,
            "password_hash": "",
            "wallet_balance": 0.0,
            "tokens": 0,
            "rating": None,
            "reviews_count": 0,
            "verified": False,
            "tier": None,
            "phone": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.users.insert_one(new_user)
        uid = str(result.inserted_id)
        user = new_user
        user["_id"] = result.inserted_id

    user = await _enforce_admin_role(user)
    # Track last_seen for beta engagement analytics
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}}
    )
    access = create_access_token(uid, email, user.get("role", "client"))
    refresh = create_refresh_token(uid)
    set_auth_cookies(response, access, refresh)
    # Mark success in oauth_health (best-effort, never block response on this)
    try:
        await db.oauth_health.insert_one({
            "event_type": "google_oauth_exchange",
            "started_at": started_at.isoformat(),
            "outcome": "success",
            "final_status": 200,
            "upstream_status": 200,
            "attempts": health_event["attempts"],
            "duration_ms": int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
            "email": email,
        })
    except Exception:  # noqa: BLE001
        pass
    return serialize_doc(user)


async def _record_oauth_health(event: dict, started_at: datetime) -> None:
    """Best-effort write to oauth_health collection — never raises."""
    try:
        event["duration_ms"] = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        await db.oauth_health.insert_one(event)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[oauth_health] write failed: {e}")


class GatewayBeaconIn(BaseModel):
    """Posted by the frontend AuthCallback when it catches a gateway error
    (502 / 504 / 520-524) so we can track ingress-level failures that never
    reached our backend retry loop."""
    status_code: int = Field(..., ge=400, le=599)
    where: Optional[str] = Field(None, max_length=128)  # "auth_callback" etc.
    note: Optional[str] = Field(None, max_length=512)


@router.post("/auth/health-beacon")
async def post_health_beacon(payload: GatewayBeaconIn, request: Request):
    """Public endpoint. Browser pings this when it sees a 5xx that didn't carry
    a JSON body (i.e. ingress-level failure, NOT our backend response). This
    fills the gap in oauth_health where we have no server-side event because
    the request was killed at the proxy.
    """
    now = datetime.now(timezone.utc)
    await db.oauth_health.insert_one({
        "event_type": "gateway_error_observed",
        "started_at": now.isoformat(),
        "outcome": "gateway_error",
        "final_status": payload.status_code,
        "upstream_status": None,
        "attempts": 0,
        "duration_ms": 0,
        "ip": request.client.host if request.client else None,
        "where": payload.where or "unknown",
        "note": payload.note or "",
    })
    return {"ok": True}


def _aggregate_auth_health(events: List[dict], hours: int, raw_limit: int) -> dict:
    total = len(events)
    by_outcome: Dict[str, int] = {}
    durations: List[int] = []
    upstream_5xx: List[dict] = []
    gateway_errors: List[dict] = []  # 502/504/520-524 observed by browser
    for ev in events:
        outcome = ev.get("outcome", "unknown")
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        d = ev.get("duration_ms")
        if isinstance(d, (int, float)) and d > 0:
            durations.append(int(d))
        us = ev.get("upstream_status")
        if isinstance(us, int) and 500 <= us < 600:
            upstream_5xx.append({
                "started_at": ev.get("started_at"),
                "upstream_status": us,
                "attempts": ev.get("attempts"),
                "last_error": ev.get("last_error"),
                "outcome": outcome,
            })
        # Gateway errors come from frontend beacon (502/504/520-524) — these
        # never reached the backend retry loop, so they signal ingress / Cloudflare /
        # K8s proxy issues, NOT upstream Emergent issues.
        fs = ev.get("final_status")
        if outcome == "gateway_error" and isinstance(fs, int) and fs in (502, 504) or (isinstance(fs, int) and 520 <= fs <= 524 and outcome == "gateway_error"):
            gateway_errors.append({
                "started_at": ev.get("started_at"),
                "status": fs,
                "where": ev.get("where"),
            })
    success = by_outcome.get("success", 0)
    success_rate = round((success / total) * 100, 1) if total else None
    durations_sorted = sorted(durations)
    p50 = durations_sorted[len(durations_sorted) // 2] if durations_sorted else None
    p95 = durations_sorted[int(len(durations_sorted) * 0.95)] if durations_sorted else None
    p99 = durations_sorted[int(len(durations_sorted) * 0.99)] if durations_sorted else None
    # 1h gateway error count — for prominent dashboard alert
    now = datetime.now(timezone.utc)
    one_hr_ago = (now - timedelta(hours=1)).isoformat()
    gateway_errors_1h = sum(1 for g in gateway_errors if g["started_at"] >= one_hr_ago)
    upstream_5xx_1h = sum(1 for u in upstream_5xx if u["started_at"] >= one_hr_ago)
    return {
        "window_hours": hours,
        "total_attempts": total,
        "success_rate_pct": success_rate,
        "outcomes": by_outcome,
        "latency_ms": {"p50": p50, "p95": p95, "p99": p99, "samples": len(durations)},
        "upstream_5xx_count": len(upstream_5xx),
        "upstream_5xx_count_1h": upstream_5xx_1h,
        "recent_upstream_5xx": upstream_5xx[:10],
        "gateway_errors_count": len(gateway_errors),
        "gateway_errors_count_1h": gateway_errors_1h,
        "recent_gateway_errors": gateway_errors[:10],
        "recent_events": events[:raw_limit],
    }


async def _build_auth_health_payload(hours: int = 24, raw_limit: int = 20) -> dict:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat()
    cursor = db.oauth_health.find({"started_at": {"$gte": since}}).sort("started_at", -1)
    events: List[dict] = []
    async for ev in cursor:
        ev["_id"] = str(ev.get("_id"))
        events.append(ev)
    payload = _aggregate_auth_health(events, hours, raw_limit)
    # Build hourly buckets for sparkline (oldest → newest, exactly `hours` entries)
    payload["hourly_buckets"] = _build_hourly_buckets(events, now, hours)
    return payload


def _build_hourly_buckets(events: List[dict], now: datetime, hours: int) -> List[dict]:
    """Group events into 1h buckets, oldest first.

    Returns list of {hour_iso, hour_label, total, success, success_rate_pct}.
    """
    buckets = []
    for i in range(hours - 1, -1, -1):  # oldest first
        bucket_start = now - timedelta(hours=i + 1)
        bucket_end = now - timedelta(hours=i)
        bs_iso = bucket_start.isoformat()
        be_iso = bucket_end.isoformat()
        total = 0
        success = 0
        for ev in events:
            ts = ev.get("started_at") or ""
            if bs_iso <= ts < be_iso:
                total += 1
                if ev.get("outcome") == "success":
                    success += 1
        rate = round((success / total) * 100, 1) if total else None
        buckets.append({
            "hour_iso": bs_iso,
            "hour_label": bucket_start.strftime("%H:00"),
            "total": total,
            "success": success,
            "success_rate_pct": rate,
        })
    return buckets


@router.get("/admin/auth-health")
async def admin_auth_health(user: dict = Depends(require_role("admin"))):
    """Real-time Google OAuth health dashboard data (last 24h)."""
    return await _build_auth_health_payload(hours=24, raw_limit=20)


@router.get("/admin/auth-health/export.csv")
async def admin_auth_health_export_csv(user: dict = Depends(require_role("admin"))):
    """Download last-24h OAuth events as CSV — useful for support@emergent.sh tickets."""
    from fastapi.responses import StreamingResponse
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=24)).isoformat()
    cursor = db.oauth_health.find({"started_at": {"$gte": since}}).sort("started_at", -1)
    buf = io.StringIO()
    buf.write("started_at,outcome,final_status,upstream_status,attempts,duration_ms,email,ip,last_error\n")
    async for ev in cursor:
        row = [
            (ev.get("started_at") or "").replace(",", " "),
            (ev.get("outcome") or "").replace(",", " "),
            str(ev.get("final_status") or ""),
            str(ev.get("upstream_status") or ""),
            str(ev.get("attempts") or ""),
            str(ev.get("duration_ms") or ""),
            (ev.get("email") or "").replace(",", " "),
            (ev.get("ip") or "").replace(",", " "),
            (ev.get("last_error") or "").replace(",", " ").replace("\n", " ")[:200],
        ]
        buf.write(",".join(row) + "\n")
    buf.seek(0)
    filename = f"oauth-health-{now.strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===== Early-warning email alert =====
_AUTH_ALERT_COOLDOWN_MIN = 60
_AUTH_ALERT_MIN_SAMPLES = 5
_AUTH_ALERT_THRESHOLD_PCT = 80.0


async def run_auth_health_alert_check() -> dict:
    """Scheduled task: if Google OAuth success rate drops below 80% in last hour
    AND we have ≥5 attempts AND no alert sent in last 60min → email all admins."""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=1)).isoformat()
    cursor = db.oauth_health.find({"started_at": {"$gte": since}})
    events = []
    async for ev in cursor:
        events.append(ev)
    summary = _aggregate_auth_health(events, hours=1, raw_limit=0)
    total = summary["total_attempts"]
    rate = summary["success_rate_pct"]
    if total < _AUTH_ALERT_MIN_SAMPLES:
        return {"ok": True, "skipped": True, "reason": f"only {total} samples (<{_AUTH_ALERT_MIN_SAMPLES})"}
    if rate is None or rate >= _AUTH_ALERT_THRESHOLD_PCT:
        return {"ok": True, "skipped": True, "reason": f"healthy: {rate}%"}
    last_alert = await db.system_alerts.find_one({"alert_key": "auth_health_low"})
    if last_alert:
        last_sent = last_alert.get("last_sent_at")
        if last_sent:
            try:
                last_dt = datetime.fromisoformat(last_sent)
                age_min = (now - last_dt).total_seconds() / 60
                if age_min < _AUTH_ALERT_COOLDOWN_MIN:
                    return {"ok": True, "skipped": True, "reason": f"cooldown {round(age_min)}min/{_AUTH_ALERT_COOLDOWN_MIN}min"}
            except (ValueError, TypeError):
                pass
    admin_emails = []
    async for adm in db.users.find({"role": "admin"}, {"email": 1}):
        if adm.get("email"):
            admin_emails.append(adm["email"])
    if not admin_emails:
        return {"ok": False, "reason": "no admin emails"}
    lat = summary["latency_ms"]
    outcomes_html = "".join(
        f"<li><strong>{k}</strong>: {v}</li>" for k, v in (summary["outcomes"] or {}).items()
    )
    subject = f"⚠️ PropManage: Google OAuth degradat ({rate}% success rate)"
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #fee2e2; border-left: 4px solid #dc2626; padding: 16px; border-radius: 8px;">
        <h2 style="color: #dc2626; margin: 0 0 8px;">Alertă auth-health · {now.strftime('%Y-%m-%d %H:%M UTC')}</h2>
        <p style="margin: 0; color: #7f1d1d;">Rata de succes Google OAuth a scăzut sub pragul de <strong>{_AUTH_ALERT_THRESHOLD_PCT}%</strong> în ultima oră.</p>
      </div>
      <h3>Sumar ultima oră:</h3>
      <ul>
        <li>Total atempturi: <strong>{total}</strong></li>
        <li>Rata succes: <strong style="color: #dc2626;">{rate}%</strong></li>
        <li>5xx upstream: {summary['upstream_5xx_count']}</li>
        <li>P95 latency: {lat['p95']}ms</li>
      </ul>
      <h3>Distribuție rezultate:</h3>
      <ul>{outcomes_html}</ul>
      <p style="margin-top: 24px;">
        <a href="https://propmanage.ro/admin/auth-health" style="display: inline-block; background: #d4ff3a; color: black; padding: 12px 24px; border-radius: 999px; text-decoration: none; font-weight: bold;">Deschide Dashboard</a>
      </p>
      <p style="font-size: 12px; color: #6b7280; margin-top: 24px;">
        Cooldown: vei primi următoarea alertă cel mai devreme peste {_AUTH_ALERT_COOLDOWN_MIN} minute.<br/>
        Dacă upstream Emergent OAuth e degradat, contactează <a href="mailto:support@emergent.sh">support@emergent.sh</a>.
      </p>
    </div>
    """
    from email_service import send_email as _send_email
    try:
        for em in admin_emails:
            await _send_email(em, subject, html)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[auth_health_alert] email send failed: {e}")
        return {"ok": False, "error": str(e)}
    await db.system_alerts.update_one(
        {"alert_key": "auth_health_low"},
        {"$set": {
            "alert_key": "auth_health_low",
            "last_sent_at": now.isoformat(),
            "last_success_rate": rate,
            "last_total": total,
            "recipients": admin_emails,
        }},
        upsert=True,
    )
    logger.warning(f"[auth_health_alert] EMAIL SENT to {len(admin_emails)} admins: rate={rate}% total={total}")
    return {"ok": True, "sent": True, "recipients": len(admin_emails), "rate": rate}


@router.post("/admin/auth-health/test-alert")
async def admin_auth_health_test_alert(user: dict = Depends(require_role("admin"))):
    """Force-trigger the alert email (skips threshold, cooldown, min-samples). For testing email delivery."""
    global _AUTH_ALERT_THRESHOLD_PCT, _AUTH_ALERT_COOLDOWN_MIN, _AUTH_ALERT_MIN_SAMPLES
    orig_t, orig_c, orig_m = _AUTH_ALERT_THRESHOLD_PCT, _AUTH_ALERT_COOLDOWN_MIN, _AUTH_ALERT_MIN_SAMPLES
    _AUTH_ALERT_THRESHOLD_PCT = 999.0
    _AUTH_ALERT_COOLDOWN_MIN = 0
    _AUTH_ALERT_MIN_SAMPLES = 0
    try:
        result = await run_auth_health_alert_check()
    finally:
        _AUTH_ALERT_THRESHOLD_PCT, _AUTH_ALERT_COOLDOWN_MIN, _AUTH_ALERT_MIN_SAMPLES = orig_t, orig_c, orig_m
    return result


# ============= DIGEST PREFERENCE & PREVIEW =============
class DigestPrefIn(BaseModel):
    enabled: bool


@router.post("/auth/digest-preference")
async def set_digest_preference(data: DigestPrefIn, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"digest_disabled": not data.enabled}}
    )
    return {"ok": True, "digest_disabled": not data.enabled}


@router.post("/admin/digest/trigger")
async def trigger_daily_digest(user: dict = Depends(require_role("admin"))):
    """Manual trigger for testing — sends today's digest to all eligible users."""
    counts = await run_daily_digests()
    return {"ok": True, "counts": counts}


@router.post("/auth/digest/preview")
async def preview_my_digest(user: dict = Depends(get_current_user)):
    builder = DIGEST_BUILDERS.get(user.get("role"))
    if not builder:
        raise HTTPException(400, "Rol fără digest configurat.")
    digest = await builder(user)
    return digest or {"summary": "Niciun conținut relevant astăzi.", "cards": "", "empty": True}


# ============================================================================
# CONSENT MANAGEMENT (GDPR — terms, privacy, marketing, cookies)
# ============================================================================
@router.patch("/me/consent")
async def update_my_consent(data: ConsentUpdateIn, request: Request, user: dict = Depends(get_current_user)):
    """Update user's consent preferences. Records every change in consent_audit_log."""
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(400, "Nothing to update")
    ip = (request.client.host if request and request.client else "") or ""
    ua = request.headers.get("user-agent", "") if request else ""
    updates = {"consent_updated_at": datetime.now(timezone.utc).isoformat()}
    for key, val in payload.items():
        updates[key] = bool(val)
        # Map field to consent_type for audit log
        ctype = key.replace("_accepted", "").replace("_consent", "")
        await _record_consent(user["id"], user["email"], ctype, bool(val), ip, ua, source="settings")
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": updates})
    return {"ok": True, "updated": list(payload.keys())}


@router.post("/cookies/consent")
async def record_cookie_consent(data: ConsentUpdateIn, request: Request):
    """Public endpoint — anonymous users can record cookie preferences (banner)."""
    payload = data.model_dump(exclude_none=True)
    ip = (request.client.host if request and request.client else "") or ""
    ua = request.headers.get("user-agent", "") if request else ""
    # If user is logged in, also persist on their profile
    try:
        user = await get_current_user(request)
    except Exception:
        user = None
    for key, val in payload.items():
        if "cookies" not in key:
            continue
        ctype = key.replace("_accepted", "")
        if user:
            await db.users.update_one(
                {"_id": ObjectId(user["id"])},
                {"$set": {key: bool(val), "consent_updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            await _record_consent(user["id"], user["email"], ctype, bool(val), ip, ua, source="cookie_banner")
        else:
            await _record_consent("anonymous", "", ctype, bool(val), ip, ua, source="cookie_banner")
    return {"ok": True}


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================
@router.get("/auth/verify-email")
async def verify_email(token: str = Query(...)):
    """Verify email via token from link. Idempotent."""
    if not token or len(token) < 16:
        raise HTTPException(400, "Invalid token")
    doc = await db.users.find_one({"email_verification_token": token})
    if not doc:
        raise HTTPException(404, "Token invalid sau expirat")
    expires = doc.get("email_verification_expires_at")
    if expires and isinstance(expires, str):
        try:
            if datetime.fromisoformat(expires.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                raise HTTPException(410, "Token expirat. Cere unul nou.")
        except ValueError:
            pass
    if doc.get("email_verified"):
        return {"ok": True, "already_verified": True}
    await db.users.update_one(
        {"_id": doc["_id"]},
        {"$set": {"email_verified": True, "email_verified_at": datetime.now(timezone.utc).isoformat()},
         "$unset": {"email_verification_token": "", "email_verification_expires_at": ""}},
    )
    return {"ok": True, "verified": True}


_resend_attempts: Dict[str, datetime] = {}

@router.post("/auth/resend-verification")
async def resend_verification(user: dict = Depends(get_current_user)):
    """Re-send verification email. Rate-limited: 1 every 5 minutes per user."""
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    last = _resend_attempts.get(user["id"])
    if last and (datetime.now(timezone.utc) - last).total_seconds() < 300:
        wait_sec = 300 - int((datetime.now(timezone.utc) - last).total_seconds())
        raise HTTPException(429, f"Așteaptă {wait_sec}s înainte de retrimitere")
    token = _gen_email_verification_token()
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"email_verification_token": token, "email_verification_expires_at": expires}},
    )
    try:
        from email_service import tpl_email_verification
        await send_template(tpl_email_verification, user.get("name", ""), token, to=user["email"])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ResendVerify] failed: {e}")
        raise HTTPException(500, "Trimiterea emailului a eșuat")
    _resend_attempts[user["id"]] = datetime.now(timezone.utc)
    return {"ok": True, "sent": True}
