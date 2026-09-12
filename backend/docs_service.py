"""PropManage — Internal Documentation & Training Center.

Stores role-specific training documents (Client, Specialist, Operator, Admin, QA)
and provides:
  - Admin CRUD endpoints for managing docs.
  - Tokenized share links (`/help/{token}`) that bypass login.
  - PDF generation (reportlab) for email attachments.
  - Auto-send to new users on registration (welcome email with role doc).

Document content lives in Python dicts (single source of truth, easy to edit
without DB migrations). DB stores only: metadata, versioning, share tokens,
read-tracking events.
"""
from __future__ import annotations

import os
import io
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
)
from reportlab.lib.enums import TA_LEFT

from db import db
from docs_content import get_doc, all_doc_meta

logger = logging.getLogger("propmanage.docs")

SHARE_TOKEN_TTL_DAYS = 30


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def _pdf_styles():
    """Define brand-aware paragraph styles."""
    styles = getSampleStyleSheet()
    base = styles["Normal"]
    return {
        "title": ParagraphStyle(
            "DocTitle", parent=base, fontName="Helvetica-Bold",
            fontSize=22, leading=28, textColor=colors.HexColor("#0a0a0b"),
            spaceAfter=4, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle", parent=base, fontName="Helvetica",
            fontSize=11, leading=16, textColor=colors.HexColor("#666"),
            spaceAfter=24,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base, fontName="Helvetica-Bold",
            fontSize=16, leading=20, textColor=colors.HexColor("#0a0a0b"),
            spaceBefore=18, spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base, fontName="Helvetica-Bold",
            fontSize=12, leading=16, textColor=colors.HexColor("#333"),
            spaceBefore=12, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", parent=base, fontName="Helvetica",
            fontSize=10.5, leading=15, textColor=colors.HexColor("#222"),
            spaceAfter=8, alignment=TA_LEFT,
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base, fontName="Helvetica-Oblique",
            fontSize=10, leading=14, textColor=colors.HexColor("#1a4a1a"),
            leftIndent=12, rightIndent=12, spaceBefore=6, spaceAfter=12,
            backColor=colors.HexColor("#f0f8e6"), borderColor=colors.HexColor("#7cb342"),
            borderWidth=0, borderPadding=8,
        ),
        "code": ParagraphStyle(
            "Code", parent=base, fontName="Courier",
            fontSize=9, leading=12, textColor=colors.HexColor("#333"),
            backColor=colors.HexColor("#f6f6f6"), leftIndent=8, rightIndent=8,
            spaceBefore=4, spaceAfter=10, borderPadding=6,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base, fontName="Helvetica",
            fontSize=8, leading=10, textColor=colors.HexColor("#888"),
        ),
    }


def _md_to_html(text: str) -> str:
    """Tiny markdown-ish to HTML for reportlab Paragraph (bold + italic + br).
    Italic uses _text_ but only at word boundaries (so identifiers like
    `twin_pins` are NOT mangled)."""
    import re
    text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # Italic: underscore must be at start/end-of-string OR adjacent to whitespace/punctuation
    text = re.sub(r"(^|[\s(>])_([^_\n]+)_(?=[\s).,;:!?<]|$)", r"\1<i>\2</i>", text)
    text = text.replace("\n", "<br/>")
    return text


def render_doc_pdf(doc_slug: str, doc_override=None) -> bytes:
    """Render a PropManage doc to a PDF byte string.

    If `doc_override` is provided (a doc dict with overrides already applied),
    it is used directly. Otherwise the registry copy is used as-is.
    """
    doc = doc_override or get_doc(doc_slug)
    if not doc:
        raise ValueError(f"Unknown doc slug: {doc_slug}")

    s = _pdf_styles()
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=doc["title"], author="PropManage",
    )

    story: list = []
    # Title block
    story.append(Paragraph(doc["title"], s["title"]))
    if doc.get("subtitle"):
        story.append(Paragraph(doc["subtitle"], s["subtitle"]))

    for section in doc["sections"]:
        story.append(Paragraph(section["heading"], s["h2"]))
        for block in section.get("body", []):
            if isinstance(block, str):
                story.append(Paragraph(_md_to_html(block), s["body"]))
            elif block.get("type") == "h3":
                story.append(Paragraph(block["text"], s["h3"]))
            elif block.get("type") == "list":
                for item in block["items"]:
                    story.append(Paragraph(f"• {_md_to_html(item)}", s["body"]))
            elif block.get("type") == "callout":
                title = block.get("title", "")
                body = block.get("body", "")
                story.append(Paragraph(
                    f"<b>{_md_to_html(title)}</b><br/>{_md_to_html(body)}",
                    s["callout"],
                ))
            elif block.get("type") == "code":
                story.append(Paragraph(block["text"].replace(" ", "&nbsp;"), s["code"]))
            elif block.get("type") == "image_placeholder":
                # In PDF we render a text note since animations don't translate
                story.append(Paragraph(
                    f"<i>[Animație interactivă: {block.get('caption', 'demonstrație')} — disponibilă în versiunea online]</i>",
                    s["callout"],
                ))
        story.append(Spacer(1, 6))

    # FAQ
    if doc.get("faq"):
        story.append(PageBreak())
        story.append(Paragraph("Întrebări frecvente", s["h2"]))
        for f in doc["faq"]:
            story.append(Paragraph(f["q"], s["h3"]))
            story.append(Paragraph(_md_to_html(f["a"]), s["body"]))

    # Footer
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        f"Documentația PropManage — versiunea {doc.get('version', '1.0')} — generat la "
        f"{datetime.now(timezone.utc).strftime('%d %b %Y')}. Pentru întrebări: contact@propmanage.ro",
        s["footer"],
    ))

    pdf.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tokenized share links
# ---------------------------------------------------------------------------

async def create_share_token(doc_slug: str, created_by: str,
                              recipient_email: Optional[str] = None,
                              recipient_user_id: Optional[str] = None,
                              ttl_days: int = SHARE_TOKEN_TTL_DAYS) -> str:
    """Generate a one-time URL-safe token for accessing a doc without login."""
    if not get_doc(doc_slug):
        raise ValueError(f"Unknown doc: {doc_slug}")
    token = secrets.token_urlsafe(24)
    await db.docs_share_tokens.insert_one({
        "_id": token,
        "doc_slug": doc_slug,
        "created_by": created_by,
        "recipient_email": recipient_email,
        "recipient_user_id": recipient_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat(),
        "opened_count": 0,
    })
    return token


async def resolve_share_token(token: str) -> Optional[dict]:
    """Look up + increment open counter. Returns the doc payload or None."""
    rec = await db.docs_share_tokens.find_one({"_id": token})
    if not rec:
        return None
    # TTL check
    try:
        expires = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            return None
    except Exception:  # noqa: BLE001
        return None

    await db.docs_share_tokens.update_one(
        {"_id": token},
        {"$inc": {"opened_count": 1}, "$set": {"last_opened_at": datetime.now(timezone.utc).isoformat()}},
    )

    doc = get_doc(rec["doc_slug"])
    if not doc:
        return None
    return {"doc": doc, "token_meta": {k: v for k, v in rec.items() if k != "_id"}}


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

async def email_doc_to_user(doc_slug: str, recipient_email: str,
                             recipient_name: Optional[str] = None,
                             include_pdf: bool = True,
                             sent_by: str = "system") -> dict:
    """Compose + send the doc to recipient via Resend.
    Always includes the tokenized link; PDF attachment is optional (default ON)."""
    from email_service import _layout, send_email
    import base64

    doc = get_doc(doc_slug)
    if not doc:
        return {"sent": False, "reason": "doc_not_found"}

    token = await create_share_token(doc_slug, sent_by, recipient_email=recipient_email)
    app_url = os.environ.get("APP_PUBLIC_URL", "https://propmanage.ro")
    share_url = f"{app_url}/help/{token}"

    greeting = f"Bună {recipient_name.split()[0]}," if recipient_name else "Bună,"

    body_html = f"""
      <p>{greeting}</p>
      <p>{doc.get('email_intro') or 'Echipa PropManage îți trimite ghidul oficial pentru rolul tău în platformă.'}</p>
      <div style="background:#1a1a1f; border-radius:14px; padding:18px; margin:18px 0;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d4ff3a; font-weight:700; margin-bottom:6px;">Ghid</div>
        <div style="color:#ffffff; font-size:17px; font-weight:600; margin-bottom:10px;">{doc['title']}</div>
        <div style="color:#c8c8cc; font-size:13px;">{doc.get('subtitle', '')}</div>
      </div>
      <p>Poți deschide ghidul direct în browser (link valabil 30 de zile, fără login necesar):</p>
      <p>
        <a href="{share_url}" style="display:inline-block; padding:12px 24px; background:#d4ff3a; color:#0a0a0b; text-decoration:none; border-radius:999px; font-weight:700; font-size:13px;">
          Deschide ghidul
        </a>
      </p>
      {('<p style="color:#888; font-size:13px;">📎 Ghidul este atașat și ca PDF (pentru offline / printare).</p>' if include_pdf else '')}
      <p style="color:#666; font-size:11px; margin-top:20px;">Linkul expiră în 30 de zile. Pentru un link nou, scrie-i administratorului tău.</p>
    """

    html = _layout(
        title=doc["title"],
        preheader=doc.get("subtitle", ""),
        body_html=body_html,
        cta_url=share_url,
        cta_label="Deschide ghidul",
    )

    attachments = None
    if include_pdf:
        try:
            pdf_bytes = render_doc_pdf(doc_slug)
            attachments = [{
                "filename": f"PropManage-{doc_slug}.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
                "type": "application/pdf",
            }]
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Docs] PDF render failed: {e}")

    subject = f"📘 Ghid PropManage · {doc['title']}"
    res = await send_email(recipient_email, subject, html, attachments=attachments)

    # Record send event
    try:
        await db.docs_send_events.insert_one({
            "doc_slug": doc_slug,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "sent_by": sent_by,
            "token": token,
            "include_pdf": include_pdf,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "ok": bool(res.get("ok")),
        })
    except Exception:  # noqa: BLE001
        pass

    return {"sent": bool(res.get("ok")), "token": token, "share_url": share_url}


def list_docs_meta() -> list[dict]:
    """For admin UI — list all available docs with metadata."""
    return all_doc_meta()



async def resolve_doc_with_overrides(doc_slug: str):
    """Return a deep-copied doc dict with any `db.doc_overrides` patches applied."""
    import copy
    base = get_doc(doc_slug)
    if not base:
        return None
    try:
        from qa_content_audit import get_overrides_for_doc
        overrides = await get_overrides_for_doc(doc_slug)
    except Exception:  # noqa: BLE001
        overrides = {}
    if not overrides:
        return base
    doc = copy.deepcopy(base)
    for (sec_idx, blk_idx), patch in overrides.items():
        try:
            doc["sections"][sec_idx]["body"][blk_idx] = patch
        except (IndexError, KeyError, TypeError):
            continue
    return doc
