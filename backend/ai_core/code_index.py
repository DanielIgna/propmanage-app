"""Codebase Index — read-only snapshot of project file paths.

Used by QA Copilot's code-aware mode to prevent the AI from hallucinating
non-existent file paths. We index once at startup and cache in-process.

Only emits relative paths under /app/backend and /app/frontend/src.
"""
import os
import time
import logging

logger = logging.getLogger("propmanage.ai_core.code_index")

_ROOTS = ("/app/backend", "/app/frontend/src")
_INCLUDED_EXTS = (".py", ".js", ".jsx", ".ts", ".tsx", ".css")
_EXCLUDED_DIRS = {"__pycache__", "node_modules", ".git", "build", "dist", "tests"}

_cache_paths: list[str] = []
_cache_ts: float = 0.0
_CACHE_TTL = 600  # 10 minutes


def _scan() -> list[str]:
    out = []
    for root in _ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for fn in filenames:
                if not fn.endswith(_INCLUDED_EXTS):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, "/app")
                out.append(rel)
    out.sort()
    return out


def list_paths(force_refresh: bool = False) -> list[str]:
    """Return cached list of relative file paths. Refreshes every 10 minutes."""
    global _cache_paths, _cache_ts
    now = time.time()
    if force_refresh or not _cache_paths or (now - _cache_ts) > _CACHE_TTL:
        _cache_paths = _scan()
        _cache_ts = now
        logger.info(f"[code_index] refreshed: {len(_cache_paths)} files")
    return _cache_paths


def build_index_summary(max_per_section: int = 40) -> str:
    """Build a compact text summary for injection into LLM prompts.

    Groups: backend/routes, backend/, frontend/src/pages, frontend/src/components.
    """
    paths = list_paths()
    groups = {
        "backend_routes": [p for p in paths if p.startswith("backend/routes/")][:max_per_section],
        "backend_other": [p for p in paths if p.startswith("backend/") and not p.startswith("backend/routes/")][:max_per_section],
        "frontend_pages": [p for p in paths if p.startswith("frontend/src/pages/")][:max_per_section],
        "frontend_components": [p for p in paths if p.startswith("frontend/src/components/")][:max_per_section],
        "frontend_lib": [p for p in paths if p.startswith("frontend/src/lib/")][:20],
    }
    parts = []
    for label, items in groups.items():
        if not items:
            continue
        parts.append(f"## {label} ({len(items)} files)")
        parts.extend(f"- {p}" for p in items)
    return "\n".join(parts)


def validate_paths(suspected: list[str]) -> dict:
    """Check which suspected paths actually exist in the index.

    Returns: {"valid": [...], "invalid": [...]}
    Matching is permissive: exact match OR endswith match (so AI can say
    'frontend/src/pages/SpecialistDashboard.jsx' or just 'SpecialistDashboard.jsx').
    """
    paths = set(list_paths())
    valid, invalid = [], []
    for s in suspected or []:
        if not s:
            continue
        s_norm = s.strip().lstrip("/").replace("/app/", "")
        if s_norm in paths:
            valid.append(s_norm)
            continue
        # Endswith fallback
        match = next((p for p in paths if p.endswith(s_norm) or p.endswith(os.path.basename(s_norm))), None)
        if match and os.path.basename(s_norm) == os.path.basename(match):
            valid.append(match)
        else:
            invalid.append(s)
    return {"valid": valid, "invalid": invalid}
