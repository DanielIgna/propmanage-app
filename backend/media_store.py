"""Base64 media out of the database: data URLs are uploaded to Storage, documents keep a short link.

Images/PDFs embedded as `data:<mime>;base64,...` in documents were read on every query that touched
them (hundreds of KB per row = most of the database egress). `externalize_doc` runs as pgmongo's
`before_write` hook for MEDIA_FIELDS: each large data URL goes to Supabase Storage under
`media/<collection>/<uuid>.<ext>` and is replaced by `/api/media/<key>` (served by routes/media.py,
immutable-cached). Keys are random, so the link itself is the access token (like a signed URL).
"""
import asyncio
import base64
import binascii
import logging
import re
import uuid

import storage_client

log = logging.getLogger("propmanage.media")

MEDIA_FIELDS = {
    "requests": ("photos",),
    "users": ("avatar", "documents"),
    "marketing_campaigns": ("images",),
}
MIN_BYTES = 2048          # tiny inline images (icons, 1px placeholders) stay inline
URL_PREFIX = "/api/media/"
_DATA_URL = re.compile(r"^data:([\w.+-]+/[\w.+-]+)(?:;[\w=.+-]+)*;base64,", re.I)
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif",
        "image/svg+xml": "svg", "application/pdf": "pdf", "image/heic": "heic"}


def _upload(collection: str, mime: str, raw: bytes) -> str:
    key = f"media/{collection}/{uuid.uuid4().hex}.{_EXT.get(mime.lower(), 'bin')}"
    storage_client.put_object(key, raw, mime)
    return URL_PREFIX + key


async def _from_b64(collection: str, mime: str, b64: str) -> str | None:
    try:
        raw = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError):
        return None
    if len(raw) < MIN_BYTES:
        return None
    return await asyncio.to_thread(_upload, collection, mime, raw)


async def _walk(collection: str, value):
    """Return `value` with large data URLs (and {"data", "mime_type"} blobs) replaced by links."""
    if isinstance(value, str):
        m = _DATA_URL.match(value)
        if m and len(value) > MIN_BYTES:
            return await _from_b64(collection, m.group(1), value[m.end():]) or value
        return value
    if isinstance(value, list):
        return [await _walk(collection, v) for v in value]
    if isinstance(value, dict):
        blob = value.get("data")
        if isinstance(blob, str) and len(blob) > MIN_BYTES and value.get("mime_type") and not blob.startswith("data:"):
            url = await _from_b64(collection, value["mime_type"], blob)
            if url:
                value = {k: v for k, v in value.items() if k != "data"} | {"url": url}
        return {k: await _walk(collection, v) for k, v in value.items()}
    return value


async def externalize_doc(collection: str, doc: dict):
    """pgmongo before_write hook: a copy of `doc` with MEDIA_FIELDS externalized, or None if unchanged.
    Never raises (on upload failure the inline value is kept)."""
    fields = [f for f in MEDIA_FIELDS.get(collection, ()) if doc.get(f)]
    if not fields:
        return None
    out = dict(doc)
    for f in fields:
        try:
            out[f] = await _walk(collection, doc[f])
        except Exception as e:  # noqa: BLE001
            log.warning(f"[media] {collection}.{f}: upload failed, kept inline: {e}")
    return out
