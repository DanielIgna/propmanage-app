"""Design Studio — Admin control panel over the entire UI.

Manages the platform's design tokens (colors, typography, radii, shadows, spacing,
component styles) via a live editor. Any change propagates instantly to all pages
that consume CSS variables. Includes named presets, per-role overrides, and a
Design Lock policy record.

Endpoints:
  GET  /api/admin/design-studio/tokens        — current active tokens (public read)
  PUT  /api/admin/design-studio/tokens        — admin update active tokens
  POST /api/admin/design-studio/reset         — admin reset to Default preset
  GET  /api/admin/design-studio/presets       — list all presets (built-in + custom)
  POST /api/admin/design-studio/presets       — save current tokens as new preset
  POST /api/admin/design-studio/presets/apply — apply a preset by id
  DELETE /api/admin/design-studio/presets/{id}— delete custom preset
  GET  /api/admin/design-studio/lock          — Design Lock policy status
  PUT  /api/admin/design-studio/lock          — toggle Design Lock enforcement

The tokens document is a single Mongo doc keyed {_id: "active"}.

════════════════════════════════════════════════════════════════════════
SOURCE OF TRUTH — Design Tokens (canonic, post-remediere Iun 2026):
  WRITE PATH (unic):   acest router → db.design_tokens {_id: "active"}
  READ RUNTIME:        GET /api/admin/design-studio/tokens (public read)
  FRONTEND CONSUMER:   contexts/DesignTokensProvider.jsx → CSS vars --pm-*
  ADMIN UI:            pages/admin/DesignStudioPage.jsx (/admin/design-studio)
  BACKUP CANONIC:      admin_console.py snapshots (partea "design_tokens")
  PORTABILITATE JSON:  routes/config_io.py (citește/scrie TOT {_id: "active"})
  AUDIT:               admin_audit_log (target.type = "design_tokens")
Orice alt path de scriere pentru design tokens este INTERZIS — dead-path-ul
Task 8 (routes/design_tokens.py, {_id: "design_tokens"}) a fost eliminat.
════════════════════════════════════════════════════════════════════════
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/design-studio", tags=["design-studio"])
logger = logging.getLogger("propmanage.design_studio")

# ── Value hygiene + audit unificat (portate din dead-path-ul Task 8 eliminat) ─
_DANGEROUS_SUBSTRINGS = ("javascript:", "expression(", "<script", "</script",
                         "onerror=", "onload=", "@import", "url(")
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _reject_dangerous_deep(obj: Any, path: str = "") -> None:
    """Respinge tentative de CSS/JS injection în orice valoare string (recursiv)."""
    if isinstance(obj, str):
        lower = obj.lower()
        for token in _DANGEROUS_SUBSTRINGS:
            if token in lower:
                raise HTTPException(400, f"Valoare respinsă ({path or 'token'}): conține '{token}'")
        if len(obj) > 300:
            raise HTTPException(400, f"Valoare prea lungă ({path or 'token'})")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _reject_dangerous_deep(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_dangerous_deep(v, f"{path}[{i}]")


async def _audit_design(action: str, user: Any, before: Any = None, after: Any = None) -> None:
    """Audit unificat în admin_audit_log (target.type=design_tokens) — vizibil în Config History."""
    u = user if isinstance(user, dict) else {}
    try:
        await db.admin_audit_log.insert_one({
            "action": action,
            "actor_id": str(u.get("id") or u.get("_id") or ""),
            "actor_name": u.get("name") or u.get("email") or "",
            "actor_email": u.get("email") or "",
            "target": {"type": "design_tokens", "id": "active", "label": action},
            "before": before,
            "after": after,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("[design_studio] audit insert failed: %s", exc)

# ── Default token set — the "PropManage Default" preset (lime brand). ────────
DEFAULT_TOKENS: dict[str, Any] = {
    "colors": {
        "primary":       "#d4ff3a",  # lime brand
        "primary_dim":   "#a3e635",
        "on_primary":    "#0a0d0c",
        "accent_ink":    "#3f6212",  # accent as text on light bg
        "bg":            "#fafaf9",
        "bg_dark":       "#0a0d0c",
        "surface":       "#ffffff",
        "surface_dark":  "#131817",
        "surface_high":  "#f5f5f4",
        "surface_high_dark": "#1a201e",
        "border":        "#e7e5e4",
        "border_dark":   "#232a28",
        "text":          "#1c1917",
        "text_dark":     "#f5f5f4",
        "text_muted":    "#78716c",
        "text_muted_dark": "#a8a29e",
        "success":       "#10b981",
        "warning":       "#f59e0b",
        "danger":        "#f43f5e",
        "info":          "#06b6d4",
    },
    "typography": {
        "sans": "'Geist', -apple-system, sans-serif",
        "serif": "'Fraunces', serif",
        "mono": "'Geist Mono', 'JetBrains Mono', monospace",
        "base_size": "16px",
        "scale_ratio": "1.2",  # modular scale for headings
        "weight_body": "400",
        "weight_bold": "700",
    },
    "radii": {
        "sm": "10px",
        "md": "14px",
        "lg": "20px",
        "xl": "24px",
        "pill": "999px",
    },
    "shadows": {
        "sm": "0 1px 2px rgba(0,0,0,0.06)",
        "md": "0 4px 12px rgba(0,0,0,0.10)",
        "lg": "0 12px 32px rgba(0,0,0,0.16)",
        "glow_primary": "0 0 32px -8px rgba(212, 255, 58, 0.4)",
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "16px",
        "lg": "24px",
        "xl": "32px",
        "2xl": "48px",
    },
    "components": {
        "button_style":    "pill",       # pill | rounded | sharp
        "input_style":     "rounded",    # rounded | sharp | underline
        "card_style":      "elevated",   # elevated | flat | glass
        "table_density":   "comfortable",# comfortable | compact | dense
        "sidebar_style":   "solid",      # solid | translucent
        "header_style":    "sticky",     # sticky | static | floating
        "badge_style":     "pill",       # pill | square
        "chart_theme":     "brand",      # brand | mono | vivid
        "kpi_variant":     "bordered",   # bordered | filled | ghost
    },
    "layout": {
        "container_max": "1440px",
        "sidebar_width": "288px",
        "header_height": "64px",
        "grid_cols": 12,
    },
}


BUILTIN_PRESETS: list[dict[str, Any]] = [
    {"id": "default",    "name": "PropManage Default", "builtin": True, "description": "Lime brand · light/dark unitar", "tokens": DEFAULT_TOKENS},
    {"id": "corporate",  "name": "Corporate Slate", "builtin": True,
     "description": "Albastru corporate · serif conservativ",
     "tokens": {
         **DEFAULT_TOKENS,
         "colors": {**DEFAULT_TOKENS["colors"], "primary": "#3b82f6", "primary_dim": "#2563eb", "on_primary": "#ffffff", "accent_ink": "#1e40af"},
         "typography": {**DEFAULT_TOKENS["typography"], "sans": "'Inter', system-ui, sans-serif"},
         "radii": {**DEFAULT_TOKENS["radii"], "sm": "6px", "md": "8px", "lg": "12px", "xl": "16px"},
         "components": {**DEFAULT_TOKENS["components"], "button_style": "rounded", "card_style": "flat"},
     }},
    {"id": "minimal_dark","name": "Minimal Dark", "builtin": True,
     "description": "Full dark · minim decorativ · focus contrast",
     "tokens": {
         **DEFAULT_TOKENS,
         "colors": {**DEFAULT_TOKENS["colors"], "primary": "#f5f5f4", "primary_dim": "#e7e5e4", "on_primary": "#0a0d0c", "accent_ink": "#f5f5f4"},
         "components": {**DEFAULT_TOKENS["components"], "card_style": "flat", "sidebar_style": "translucent"},
     }},
    {"id": "warm_linen", "name": "Warm Linen", "builtin": True,
     "description": "Warmneutral · beige · roșu Sienna",
     "tokens": {
         **DEFAULT_TOKENS,
         "colors": {**DEFAULT_TOKENS["colors"], "primary": "#c2410c", "primary_dim": "#9a3412", "on_primary": "#ffffff", "accent_ink": "#7c2d12",
                    "bg": "#fefaf4", "surface": "#fff8ec", "surface_high": "#f5ead6"},
         "typography": {**DEFAULT_TOKENS["typography"], "sans": "'Fraunces', serif"},
     }},
    {"id": "neon_lab",   "name": "Neon Lab", "builtin": True,
     "description": "Cyberpunk · lime + magenta · glass",
     "tokens": {
         **DEFAULT_TOKENS,
         "colors": {**DEFAULT_TOKENS["colors"], "primary": "#d4ff3a", "on_primary": "#0a0d0c", "accent_ink": "#a3e635",
                    "bg_dark": "#000000", "surface_dark": "#0a0a0a", "surface_high_dark": "#171717"},
         "components": {**DEFAULT_TOKENS["components"], "card_style": "glass", "button_style": "pill"},
         "shadows": {**DEFAULT_TOKENS["shadows"], "glow_primary": "0 0 48px -4px rgba(212, 255, 58, 0.6)"},
     }},
    {"id": "material_you","name": "Material You", "builtin": True,
     "description": "Google Material 3 · rounded · vivid",
     "tokens": {
         **DEFAULT_TOKENS,
         "colors": {**DEFAULT_TOKENS["colors"], "primary": "#6750a4", "primary_dim": "#4f378b", "on_primary": "#ffffff", "accent_ink": "#4f378b"},
         "radii": {"sm": "12px", "md": "20px", "lg": "28px", "xl": "36px", "pill": "999px"},
         "components": {**DEFAULT_TOKENS["components"], "card_style": "elevated", "button_style": "pill"},
     }},
]


class TokensPayload(BaseModel):
    colors: dict[str, str] | None = None
    typography: dict[str, str] | None = None
    radii: dict[str, str] | None = None
    shadows: dict[str, str] | None = None
    spacing: dict[str, str] | None = None
    components: dict[str, str] | None = None
    layout: dict[str, Any] | None = None


class CascadePayload(BaseModel):
    primary: str = Field(default="#d4ff3a", description="Culoare principală (brand) — hex")
    accent: str = Field(default="#a3e635", description="Culoare accent secundară — hex")
    neutral: str = Field(default="#1c1917", description="Neutral ink (text pe light) — hex")
    surface_light: str = Field(default="#fafaf9", description="Fundal light — hex")
    surface_dark: str = Field(default="#0a0d0c", description="Fundal dark — hex")
    apply: bool = Field(default=False, description="Dacă true, aplică imediat pe tokens active")


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _mix(a: str, b: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(a); r2, g2, b2 = _hex_to_rgb(b)
    return _rgb_to_hex(int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t))


def _luminance(h: str) -> float:
    r, g, b = [c / 255 for c in _hex_to_rgb(h)]
    def _lin(c: float) -> float: return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ink(bg: str) -> str:
    """Return black or white ink for best contrast on background."""
    return "#0a0d0c" if _luminance(bg) > 0.5 else "#f5f5f4"


def _cascade(primary: str, accent: str, neutral: str, surface_light: str, surface_dark: str) -> dict[str, Any]:
    """Deterministically derive the full color token set from 3-5 base hexes."""
    # Derive complementary shades
    primary_dim = _mix(primary, "#000000", 0.15)         # darker primary
    accent_ink  = _mix(accent, neutral, 0.35)             # accent as text (readable)
    on_primary  = _contrast_ink(primary)
    surface_high_light = _mix(surface_light, neutral, 0.05)
    surface_high_dark  = _mix(surface_dark, "#ffffff", 0.08)
    border_light = _mix(surface_light, neutral, 0.12)
    border_dark  = _mix(surface_dark, "#ffffff", 0.14)
    text_light = neutral
    text_dark  = _mix(surface_dark, "#ffffff", 0.94)
    text_muted_light = _mix(neutral, surface_light, 0.4)
    text_muted_dark  = _mix(text_dark, surface_dark, 0.5)
    return {
        "primary":      primary,
        "primary_dim":  primary_dim,
        "on_primary":   on_primary,
        "accent_ink":   accent_ink,
        "bg":           surface_light,
        "bg_dark":      surface_dark,
        "surface":      "#ffffff" if _luminance(surface_light) > 0.9 else surface_light,
        "surface_dark": surface_dark,
        "surface_high": surface_high_light,
        "surface_high_dark": surface_high_dark,
        "border":       border_light,
        "border_dark":  border_dark,
        "text":         text_light,
        "text_dark":    text_dark,
        "text_muted":   text_muted_light,
        "text_muted_dark": text_muted_dark,
        # Semantic — keep universal (verde/portocaliu/roșu/cyan)
        "success":  "#10b981",
        "warning":  "#f59e0b",
        "danger":   "#f43f5e",
        "info":     "#06b6d4",
    }


class PresetSavePayload(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: str = ""


def _deep_merge(a: dict, b: dict) -> dict:
    out = {**a}
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


async def _get_active() -> dict[str, Any]:
    doc = await db.design_tokens.find_one({"_id": "active"})
    if not doc:
        # seed with default
        await db.design_tokens.update_one({"_id": "active"}, {"$set": {"_id": "active", "tokens": DEFAULT_TOKENS, "preset_id": "default", "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        return {"tokens": DEFAULT_TOKENS, "preset_id": "default", "updated_at": datetime.now(timezone.utc).isoformat()}
    return {"tokens": doc.get("tokens") or DEFAULT_TOKENS, "preset_id": doc.get("preset_id"), "updated_at": doc.get("updated_at")}


async def seed_builtin_presets() -> None:
    for p in BUILTIN_PRESETS:
        await db.design_presets.update_one({"id": p["id"]}, {"$set": p}, upsert=True)


# ── PUBLIC READ (tokens are needed by every page, not admin-only) ────────────
@router.get("/tokens")
async def get_tokens():
    """Return the currently active design tokens — used by DesignTokensProvider."""
    active = await _get_active()
    return active


@router.put("/tokens")
async def update_tokens(payload: TokensPayload, admin=Depends(require_role("admin"))):
    active = await _get_active()
    current = active["tokens"]
    patch = payload.model_dump(exclude_none=True)
    _reject_dangerous_deep(patch)
    merged = _deep_merge(current, patch)
    await db.design_tokens.update_one(
        {"_id": "active"},
        {"$set": {"tokens": merged, "preset_id": "custom", "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await _audit_design("design_tokens.update", admin,
                        before={"preset_id": active.get("preset_id"), "tokens": current},
                        after={"preset_id": "custom", "tokens": merged})
    return {"tokens": merged, "preset_id": "custom"}


@router.post("/reset")
async def reset_tokens(admin=Depends(require_role("admin"))):
    active = await _get_active()
    await db.design_tokens.update_one(
        {"_id": "active"},
        {"$set": {"tokens": DEFAULT_TOKENS, "preset_id": "default", "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await _audit_design("design_tokens.reset", admin,
                        before={"preset_id": active.get("preset_id")},
                        after={"preset_id": "default"})
    return {"tokens": DEFAULT_TOKENS, "preset_id": "default"}


# ── PRESETS ──────────────────────────────────────────────────────────────────
@router.get("/presets")
async def list_presets(_admin=Depends(require_role("admin"))):
    await seed_builtin_presets()
    out = []
    async for doc in db.design_presets.find({}, {"_id": 0}):
        out.append(doc)
    # sort builtins first
    out.sort(key=lambda x: (not x.get("builtin", False), x.get("name", "")))
    return {"presets": out}


@router.post("/presets")
async def save_preset(payload: PresetSavePayload, _admin=Depends(require_role("admin"))):
    active = await _get_active()
    slug = payload.name.lower().replace(" ", "_")[:40]
    doc = {
        "id": f"custom_{slug}",
        "name": payload.name,
        "description": payload.description,
        "builtin": False,
        "tokens": active["tokens"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.design_presets.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
    return doc


@router.post("/presets/apply")
async def apply_preset(preset_id: str = Body(..., embed=True), admin=Depends(require_role("admin"))):
    preset = await db.design_presets.find_one({"id": preset_id}, {"_id": 0})
    if not preset:
        # try built-in
        preset = next((p for p in BUILTIN_PRESETS if p["id"] == preset_id), None)
        if not preset:
            raise HTTPException(404, f"Preset necunoscut: {preset_id}")
    tokens = preset["tokens"]
    _reject_dangerous_deep(tokens)  # SEC-003: sanitizare uniformă pe orice write path
    active = await _get_active()
    await db.design_tokens.update_one(
        {"_id": "active"},
        {"$set": {"tokens": tokens, "preset_id": preset_id, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await _audit_design("design_tokens.preset_apply", admin,
                        before={"preset_id": active.get("preset_id")},
                        after={"preset_id": preset_id})
    return {"tokens": tokens, "preset_id": preset_id}


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str, _admin=Depends(require_role("admin"))):
    p = await db.design_presets.find_one({"id": preset_id})
    if not p:
        raise HTTPException(404, f"Preset {preset_id} nu există")
    if p.get("builtin"):
        raise HTTPException(400, "Nu poți șterge un preset built-in.")
    await db.design_presets.delete_one({"id": preset_id})
    return {"ok": True}


# ── DESIGN LOCK ──────────────────────────────────────────────────────────────
DEFAULT_LOCK = {
    "enabled": True,
    "rules": [
        "Nu se folosesc culori hardcoded — doar CSS variables (--pm-*).",
        "Nu se folosesc valori de spacing custom — doar tokens (--pm-space-*).",
        "Butoanele folosesc DSButton sau PMPillButton — nu <button> stilizat direct.",
        "Cardurile folosesc CARD sau pm-card — nu <div> cu bg-white + border ad-hoc.",
        "Badge-urile folosesc DSBadge sau pm-chip — nu <span> stilizat direct.",
        "Tabelele folosesc DataTable — nu <table> nativ pentru date de business.",
        "Formularele folosesc componente unificate — text, select, textarea din Design System.",
        "Fonturile: doar Geist (sans) și Fraunces (serif) — fără fonturi ad-hoc.",
    ],
    "updated_at": None,
}


@router.get("/lock")
async def get_lock(_admin=Depends(require_role("admin"))):
    doc = await db.design_lock.find_one({"_id": "policy"})
    if not doc:
        d = {**DEFAULT_LOCK, "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.design_lock.update_one({"_id": "policy"}, {"$set": {"_id": "policy", **d}}, upsert=True)
        return d
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/lock")
async def update_lock(enabled: bool = Body(..., embed=True), _admin=Depends(require_role("admin"))):
    await db.design_lock.update_one(
        {"_id": "policy"},
        {"$set": {"enabled": enabled, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    doc = await db.design_lock.find_one({"_id": "policy"})
    return {k: v for k, v in (doc or {}).items() if k != "_id"}


# ── COMPONENT LIBRARY registry (used by future Component Explorer / Dev Mode) ─
COMPONENT_LIBRARY = [
    {"key": "kpi_card",     "label": "KPI Card",       "category": "data",       "tokens": ["colors.surface", "colors.text", "radii.lg", "shadows.sm"]},
    {"key": "ai_insight",   "label": "AI Insight Card","category": "data",       "tokens": ["colors.primary", "colors.text", "radii.lg"]},
    {"key": "chart_card",   "label": "Chart Card",     "category": "data",       "tokens": ["colors.surface", "colors.border", "radii.lg"]},
    {"key": "data_table",   "label": "Data Table",     "category": "data",       "tokens": ["colors.surface", "colors.border", "components.table_density"]},
    {"key": "ds_button",    "label": "Button",         "category": "input",      "tokens": ["colors.primary", "components.button_style", "radii.md"]},
    {"key": "ds_badge",     "label": "Badge",          "category": "display",    "tokens": ["components.badge_style", "radii.pill"]},
    {"key": "pm_card",      "label": "Card",           "category": "layout",     "tokens": ["colors.surface", "components.card_style", "radii.lg", "shadows.md"]},
    {"key": "pm_pill",      "label": "Pill Button",    "category": "input",      "tokens": ["colors.primary", "radii.pill", "shadows.glow_primary"]},
    {"key": "pm_chip",      "label": "Chip / Tag",     "category": "display",    "tokens": ["colors.surface_high", "radii.pill"]},
    {"key": "empty_state",  "label": "Empty State",    "category": "display",    "tokens": ["colors.text_muted"]},
    {"key": "sidebar_item", "label": "Sidebar Item",   "category": "navigation", "tokens": ["colors.primary", "components.sidebar_style"]},
    {"key": "topbar",       "label": "Top Bar",        "category": "navigation", "tokens": ["colors.bg", "components.header_style"]},
    {"key": "bottom_nav",   "label": "Bottom Nav",     "category": "navigation", "tokens": ["colors.bg", "colors.primary"]},
    {"key": "fab",          "label": "Floating Action","category": "input",      "tokens": ["colors.primary", "shadows.glow_primary"]},
    {"key": "form_input",   "label": "Form Input",     "category": "input",      "tokens": ["colors.surface", "components.input_style", "radii.md"]},
    {"key": "toast",        "label": "Toast / Alert",  "category": "feedback",   "tokens": ["colors.surface", "radii.md", "shadows.lg"]},
    {"key": "skeleton",     "label": "Skeleton Loader","category": "feedback",   "tokens": ["colors.surface_high"]},
]


@router.get("/components")
async def list_components(_admin=Depends(require_role("admin"))):
    return {"components": COMPONENT_LIBRARY, "total": len(COMPONENT_LIBRARY)}


# ── FUTURE BUILDER MODULES — schema placeholders (return "in implementare") ──
BUILDER_MODULES_STATUS = {
    "page_builder":       {"status": "planned",        "eta": "Q2 2026", "note": "Layout drag&drop pentru dashboard-uri pe rol."},
    "menu_manager":       {"status": "in_development", "eta": "Q1 2026", "note": "Editează NAV_SECTIONS din DB, nu din cod."},
    "button_manager":     {"status": "planned",        "eta": "Q2 2026", "note": "Registry butoane per pagină cu vizibilitate pe rol."},
    "form_builder":       {"status": "planned",        "eta": "Q2 2026", "note": "Schema-driven forms din JSON."},
    "table_builder":      {"status": "planned",        "eta": "Q2 2026", "note": "Config coloane / filtre / sortare per tabel."},
    "dashboard_builder":  {"status": "planned",        "eta": "Q2 2026", "note": "Widget picker + grid drag&drop."},
    "developer_mode":     {"status": "beta",           "eta": "Q1 2026", "note": "Inspecție componente + tokens folosite."},
}


@router.get("/builder-status")
async def builder_status(_admin=Depends(require_role("admin"))):
    return {"modules": BUILDER_MODULES_STATUS}


# ── PALETTE CASCADE — derive full 20-color token set from 3-5 base hexes ─────
@router.post("/palette-cascade")
async def palette_cascade(payload: CascadePayload, admin=Depends(require_role("admin"))):
    """Given 3-5 base hex codes, deterministically derive the full color palette
    (light+dark, borders, muted text, on-primary contrast ink, semantic accents)
    and optionally apply it to the active tokens.
    """
    for field in ("primary", "accent", "neutral", "surface_light", "surface_dark"):
        val = getattr(payload, field)
        if not _HEX_RE.match(val or ""):
            raise HTTPException(400, f"{field} trebuie să fie hex valid (#rgb sau #rrggbb)")
    derived = _cascade(payload.primary, payload.accent, payload.neutral, payload.surface_light, payload.surface_dark)
    active = await _get_active()
    new_tokens = {**active["tokens"], "colors": derived}
    if payload.apply:
        await db.design_tokens.update_one(
            {"_id": "active"},
            {"$set": {"tokens": new_tokens, "preset_id": "custom", "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        await _audit_design("design_tokens.palette_cascade", admin,
                            before={"preset_id": active.get("preset_id")},
                            after={"preset_id": "custom", "base": {"primary": payload.primary, "accent": payload.accent}})
    return {"colors": derived, "tokens": new_tokens, "applied": payload.apply}
