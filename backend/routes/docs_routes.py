"""PropManage — Internal Documentation API.

Endpoints:
  - Public:
    - GET /api/help/{token}        — open a tokenized share link (no auth)
    - GET /api/help/{token}/pdf    — download PDF version via token

  - Admin only:
    - GET  /api/admin/docs                   — list all available docs (meta)
    - GET  /api/admin/docs/{slug}            — get full doc content (JSON)
    - GET  /api/admin/docs/{slug}/pdf        — download PDF directly
    - POST /api/admin/docs/{slug}/send       — email doc to a list of recipients
    - GET  /api/admin/docs/send-events       — recent send history
    - GET  /api/admin/docs/share-tokens      — active share tokens + analytics
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response

from deps import require_role
from docs_service import (
    render_doc_pdf, email_doc_to_user, list_docs_meta,
    resolve_share_token,
)
from docs_search import render_doc_markdown, search_docs
from docs_content import get_doc
from db import db

logger = logging.getLogger("propmanage.routes.docs")

# Public viewer (no auth) ----------------------------------------------------
public_router = APIRouter(prefix="/api/help", tags=["public-help"])


@public_router.get("/{token}")
async def open_share_token(token: str):
    """Open a tokenized doc — no auth needed. Used by /help/{token} on frontend."""
    res = await resolve_share_token(token)
    if not res:
        raise HTTPException(404, "Link invalid sau expirat")
    return res


@public_router.get("/{token}/pdf")
async def download_share_pdf(token: str):
    """Download the PDF version via a share token (no auth)."""
    res = await resolve_share_token(token)
    if not res:
        raise HTTPException(404, "Link invalid sau expirat")
    doc_slug = res["doc"]["slug"]
    try:
        pdf_bytes = render_doc_pdf(doc_slug)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[Docs] PDF render via token failed: {e}")
        raise HTTPException(500, "PDF render failed") from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="PropManage-{doc_slug}.pdf"'},
    )


# Admin -----------------------------------------------------------------------
admin_router = APIRouter(prefix="/api/admin/docs", tags=["admin-docs"])


@admin_router.get("")
async def admin_list_docs(user: dict = Depends(require_role("admin"))):
    return {"docs": list_docs_meta()}


@admin_router.get("/{slug}")
async def admin_get_doc(slug: str, user: dict = Depends(require_role("admin"))):
    from docs_service import resolve_doc_with_overrides
    doc = await resolve_doc_with_overrides(slug)
    if not doc:
        raise HTTPException(404, "Doc not found")
    return doc


@admin_router.get("/{slug}/pdf")
async def admin_download_pdf(slug: str, user: dict = Depends(require_role("admin"))):
    if not get_doc(slug):
        raise HTTPException(404, "Doc not found")
    try:
        from docs_service import resolve_doc_with_overrides
        resolved = await resolve_doc_with_overrides(slug)
        pdf_bytes = render_doc_pdf(slug, doc_override=resolved)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"PDF render failed: {e}") from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="PropManage-{slug}.pdf"'},
    )


@admin_router.get("/{slug}/markdown")
async def admin_download_markdown(slug: str, user: dict = Depends(require_role("admin"))):
    """Plain markdown export — easy to paste into Slack / Notion / email."""
    md = render_doc_markdown(slug)
    if md is None:
        raise HTTPException(404, "Doc not found")
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="PropManage-{slug}.md"'},
    )


@admin_router.get("/admin/search")
async def admin_search_docs(q: str, limit: int = 20, user: dict = Depends(require_role("admin"))):
    """Full-text search across all docs. Used by Cmd+K palette."""
    return {"query": q, "hits": search_docs(q, limit=min(limit, 50))}


@admin_router.post("/{slug}/send")
async def admin_send_doc(
    slug: str,
    recipients: list[dict] = Body(..., embed=True,
                                   description="List of {email, name?} objects"),
    include_pdf: bool = Body(True, embed=True),
    user: dict = Depends(require_role("admin")),
):
    """Email the doc to a list of recipients. Each recipient gets:
       - personalized share token (different per recipient for tracking)
       - HTML email with CTA
       - PDF attachment (if include_pdf=true)
    """
    if not get_doc(slug):
        raise HTTPException(404, "Doc not found")
    if not recipients:
        raise HTTPException(400, "No recipients provided")
    if len(recipients) > 50:
        raise HTTPException(400, "Maximum 50 recipients per batch")

    results = []
    for r in recipients:
        email = (r.get("email") or "").strip()
        if not email or "@" not in email:
            results.append({"email": email, "sent": False, "reason": "invalid_email"})
            continue
        try:
            res = await email_doc_to_user(
                slug, email,
                recipient_name=r.get("name"),
                include_pdf=include_pdf,
                sent_by=user.get("email", "admin"),
            )
            results.append({"email": email, **res})
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Docs] send to {email} failed: {e}")
            results.append({"email": email, "sent": False, "reason": str(e)})

    sent_count = sum(1 for r in results if r.get("sent"))
    logger.info(f"[Docs] admin {user.get('email')} sent '{slug}' to {sent_count}/{len(recipients)}")
    return {"sent": sent_count, "total": len(recipients), "results": results}


@admin_router.post("/{slug}/send-to-role")
async def admin_send_doc_to_role(
    slug: str,
    role: str = Body(..., embed=True, description="client | specialist | operator | admin"),
    verified_only: bool = Body(False, embed=True),
    include_pdf: bool = Body(True, embed=True),
    limit: int = Body(200, embed=True, le=500),
    user: dict = Depends(require_role("admin")),
):
    """Bulk send doc to all users of a given role (max 500)."""
    if not get_doc(slug):
        raise HTTPException(404, "Doc not found")

    q = {"role": role, "deleted": {"$ne": True}}
    if verified_only:
        q["verified"] = True
    cursor = db.users.find(q, {"email": 1, "name": 1}).limit(limit)
    recipients = [{"email": u.get("email"), "name": u.get("name")} async for u in cursor]
    if not recipients:
        return {"sent": 0, "total": 0, "results": []}

    sent_count = 0
    results = []
    for r in recipients:
        try:
            res = await email_doc_to_user(
                slug, r["email"],
                recipient_name=r.get("name"),
                include_pdf=include_pdf,
                sent_by=user.get("email", "admin"),
            )
            if res.get("sent"):
                sent_count += 1
            results.append({"email": r["email"], **res})
        except Exception as e:  # noqa: BLE001
            results.append({"email": r["email"], "sent": False, "reason": str(e)})

    logger.info(f"[Docs] bulk-send '{slug}' to role={role}: {sent_count}/{len(recipients)}")
    return {"sent": sent_count, "total": len(recipients), "results": results[:20]}  # cap response


@admin_router.get("/admin/send-events")
async def admin_list_send_events(
    limit: int = 50,
    user: dict = Depends(require_role("admin")),
):
    cursor = db.docs_send_events.find({}).sort("sent_at", -1).limit(min(limit, 200))
    items = []
    async for e in cursor:
        e["_id"] = str(e["_id"])
        items.append(e)
    return {"items": items}


@admin_router.get("/admin/share-tokens")
async def admin_list_share_tokens(
    limit: int = 50,
    user: dict = Depends(require_role("admin")),
):
    """Active share tokens with open analytics."""
    cursor = db.docs_share_tokens.find({}).sort("created_at", -1).limit(min(limit, 200))
    items = []
    async for t in cursor:
        items.append({
            "token_id": t["_id"][:8] + "...",
            "full_token": t["_id"],
            "doc_slug": t.get("doc_slug"),
            "recipient_email": t.get("recipient_email"),
            "created_by": t.get("created_by"),
            "created_at": t.get("created_at"),
            "expires_at": t.get("expires_at"),
            "opened_count": t.get("opened_count", 0),
            "last_opened_at": t.get("last_opened_at"),
        })
    return {"items": items}
