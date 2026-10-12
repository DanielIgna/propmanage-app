"""GET /api/media/<key> — media moved out of documents by media_store (photos, avatars, documents).

Keys are random (media/<collection>/<uuid>.<ext>), so no auth: the link is the capability.
Content never changes for a key, so responses are immutable-cached by browsers/CDN, and a small
in-process LRU avoids re-reading hot objects from Storage.
"""
import asyncio
import re
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Response

import storage_client

router = APIRouter(prefix="/api/media", tags=["media"])

_KEY = re.compile(r"^media/[a-z_]+/[0-9a-f]{32}\.[a-z0-9]{2,5}$")
_CACHE: "OrderedDict[str, tuple[bytes, str]]" = OrderedDict()
_CACHE_MAX_BYTES = 64 * 1024 * 1024
_cache_bytes = 0
_INLINE_SAFE = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "application/pdf"}


def _remember(key: str, data: bytes, ctype: str) -> None:
    global _cache_bytes
    if len(data) > _CACHE_MAX_BYTES // 8:
        return
    _CACHE[key] = (data, ctype)
    _cache_bytes += len(data)
    while _cache_bytes > _CACHE_MAX_BYTES and _CACHE:
        _, (old, _ct) = _CACHE.popitem(last=False)
        _cache_bytes -= len(old)


@router.get("/{key:path}")
async def get_media(key: str):
    if not _KEY.match(key):
        raise HTTPException(404, "Not found")
    hit = _CACHE.get(key)
    if hit:
        _CACHE.move_to_end(key)
        data, ctype = hit
    else:
        try:
            data, ctype = await asyncio.to_thread(storage_client.get_object, key)
        except Exception:  # noqa: BLE001
            raise HTTPException(404, "Not found")
        _remember(key, data, ctype)
    headers = {"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"}
    if (ctype or "").split(";")[0].strip().lower() not in _INLINE_SAFE:  # svg/html/...: no script on our origin
        headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        headers["Content-Disposition"] = "attachment"
    return Response(content=data, media_type=ctype, headers=headers)
