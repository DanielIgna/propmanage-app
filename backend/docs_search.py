"""Markdown rendering + full-text search across the docs registry."""
from __future__ import annotations
from typing import Optional
from docs_content import DOCS_CONTENT, get_doc


def _inline(text: str) -> str:
    """Already markdown-ish (**bold**, _italic_) — return as-is."""
    return text or ""


def _block_to_md(block) -> list[str]:
    out: list[str] = []
    if isinstance(block, str):
        out.append(_inline(block))
        return out
    t = block.get("type")
    if t == "h3":
        out.append(f"### {block['text']}")
    elif t == "list":
        for it in block.get("items", []):
            out.append(f"- {_inline(it)}")
    elif t == "callout":
        variant = block.get("variant", "info")
        emoji = {"info": "ℹ️", "warn": "⚠️", "success": "✅"}.get(variant, "📌")
        out.append(f"> {emoji} **{block.get('title', '')}**")
        body = _inline(block.get("body", ""))
        for line in body.split("\n"):
            out.append(f"> {line}")
    elif t == "code":
        out.append("```")
        out.append(block.get("text", ""))
        out.append("```")
    elif t == "steps":
        for i, s in enumerate(block.get("items", []), 1):
            out.append(f"{i}. **{s.get('title', '')}** — {_inline(s.get('body', ''))}")
    elif t in ("image_placeholder", "screencast", "lottie"):
        cap = block.get("caption", "")
        src = block.get("src", "")
        out.append(f"_[Media: {cap} — `{src}`]_")
    return out


def render_doc_markdown(slug: str) -> Optional[str]:
    doc = get_doc(slug)
    if not doc:
        return None
    lines: list[str] = [
        f"# {doc['title']}",
        "",
        f"_{doc.get('subtitle', '')}_",
        "",
        f"**Versiune**: {doc.get('version', '1.0')} · **Actualizat**: {doc.get('updated_at', '')} · **Rol**: {doc.get('role', '')}",
        "",
        "---",
        "",
    ]
    for section in doc["sections"]:
        lines.append(f"## {section['heading']}")
        lines.append("")
        for block in section.get("body", []):
            lines.extend(_block_to_md(block))
            lines.append("")
        lines.append("")

    if doc.get("faq"):
        lines.append("## Întrebări frecvente")
        lines.append("")
        for f in doc["faq"]:
            lines.append(f"### {f['q']}")
            lines.append("")
            lines.append(_inline(f["a"]))
            lines.append("")

    lines.append("---")
    lines.append("_Documentație PropManage — generată automat. Vezi versiunea online pentru animații interactive._")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Full-text search
# ----------------------------------------------------------------------------

def _normalize(s: str) -> str:
    s = (s or "").lower()
    # Replace Romanian diacritics
    return (s.replace("ă", "a").replace("â", "a").replace("î", "i")
              .replace("ș", "s").replace("ş", "s").replace("ț", "t").replace("ţ", "t"))


def _extract_text_from_block(block) -> str:
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return ""
    parts = []
    if block.get("type") == "list":
        parts.extend(block.get("items", []))
    elif block.get("type") == "callout":
        parts.append(block.get("title", ""))
        parts.append(block.get("body", ""))
    elif block.get("type") == "code":
        parts.append(block.get("text", ""))
    elif block.get("type") == "steps":
        for s in block.get("items", []):
            parts.append(s.get("title", ""))
            parts.append(s.get("body", ""))
    elif block.get("type") in ("h3",):
        parts.append(block.get("text", ""))
    else:
        parts.append(block.get("caption", ""))
    return " ".join(p for p in parts if p)


def _snippet_around(text: str, query: str, width: int = 80) -> str:
    """Return a ~160-char snippet centered on the first match of query."""
    norm = _normalize(text)
    q = _normalize(query)
    idx = norm.find(q)
    if idx < 0:
        return text[:width * 2]
    start = max(0, idx - width)
    end = min(len(text), idx + len(q) + width)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def search_docs(query: str, limit: int = 20) -> list[dict]:
    """Full-text search across all docs.
    Returns hits with: doc_slug, doc_title, section_idx, section_heading, snippet, kind."""
    q = query.strip()
    if len(q) < 2:
        return []
    qn = _normalize(q)
    hits: list[dict] = []

    for slug, doc in DOCS_CONTENT.items():
        # Title match
        if qn in _normalize(doc["title"]):
            hits.append({
                "doc_slug": slug, "doc_title": doc["title"],
                "kind": "title", "section_heading": "(titlu)",
                "snippet": doc["title"], "score": 100,
            })

        for sidx, section in enumerate(doc["sections"]):
            heading = section.get("heading", "")
            if qn in _normalize(heading):
                hits.append({
                    "doc_slug": slug, "doc_title": doc["title"],
                    "kind": "heading", "section_idx": sidx,
                    "section_heading": heading,
                    "snippet": heading, "score": 80,
                })
            for block in section.get("body", []):
                txt = _extract_text_from_block(block)
                if txt and qn in _normalize(txt):
                    hits.append({
                        "doc_slug": slug, "doc_title": doc["title"],
                        "kind": "body", "section_idx": sidx,
                        "section_heading": heading,
                        "snippet": _snippet_around(txt, q),
                        "score": 50,
                    })

        for fidx, f in enumerate(doc.get("faq", [])):
            blob = f["q"] + " " + f["a"]
            if qn in _normalize(blob):
                hits.append({
                    "doc_slug": slug, "doc_title": doc["title"],
                    "kind": "faq", "faq_idx": fidx,
                    "section_heading": "FAQ",
                    "snippet": _snippet_around(blob, q),
                    "score": 60,
                })

    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]
