"""Idempotent, retry-safe sitemap regeneration triggered by SEO-relevant events
(e.g. specialist verification changing a service×city gate state).

Reuses the EXISTING SSOT (routes.public.write_sitemap_file / build_sitemap_xml) —
no second gate or sitemap implementation. Records events in db.seo_events so
Admin → SEO (Sitemap + Alerts) can show last regeneration + failures.
"""
import logging
import re
from datetime import datetime, timezone

from db import db

logger = logging.getLogger(__name__)


async def regenerate_sitemap(reason: str = "manual", source: str = "system") -> dict:
    """Full recompute from SSOT → write static sitemap files. Idempotent & retry-safe."""
    started = datetime.now(timezone.utc)
    event = {"type": "sitemap_regen", "reason": reason, "source": source,
             "started_at": started.isoformat()}
    try:
        from routes.public import write_sitemap_file, build_sitemap_xml
        await write_sitemap_file()
        xml = await build_sitemap_xml()
        event.update({
            "ok": True,
            "url_count": len(re.findall(r"<loc>", xml)),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[seo_regen] OK reason={reason} urls={event['url_count']}")
    except Exception as e:  # noqa: BLE001
        logger.exception("[seo_regen] failed")
        event.update({"ok": False, "error": str(e)[:500],
                      "finished_at": datetime.now(timezone.utc).isoformat()})
    try:
        await db.seo_events.insert_one(dict(event))
    except Exception:  # noqa: BLE001
        pass
    return event


async def on_specialist_verification_changed(spec_id: str, source: str = "verify") -> None:
    """Fire-and-forget hook after a verification change. Safe to call repeatedly."""
    await regenerate_sitemap(reason=f"specialist_verification:{spec_id}", source=source)
