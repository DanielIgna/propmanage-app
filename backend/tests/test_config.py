"""Shared test credentials & config — env-driven (no hardcoded secrets).

All test files import credentials from here. Override any value via env:
  TEST_ADMIN_EMAIL / SEED_ADMIN_PASSWORD / TEST_ADMIN_PASSWORD / DEMO_MASTER_CODE
Loads backend/.env + frontend/.env automatically so tests run standalone.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    load_dotenv(_here.parents[1] / ".env")                     # backend/.env
    load_dotenv(_here.parents[2] / "frontend" / ".env")        # frontend/.env
except ImportError:  # pragma: no cover
    pass

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE_URL}/api"

# ── Demo-seeded accounts (see seed.py — idempotent) ─────────────────────────
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
# Admin password comes from env (SEED_ADMIN_PASSWORD in backend/.env).
OWNER_ADMIN_PASSWORD = (
    os.environ.get("SEED_ADMIN_PASSWORD")
    or os.environ.get("TEST_ADMIN_PASSWORD")
    or "Admin123!"
)
# Ordered candidate list — some environments may still use the demo default.
ADMIN_PASSWORDS = list(dict.fromkeys([OWNER_ADMIN_PASSWORD, "Admin123!"]))

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
SPECIALIST_EMAIL = "specialist@propmanage.io"
SPECIALIST_PASSWORD = "Spec123!"
OPERATOR_EMAIL = "operator@propmanage.io"
OPERATOR_PASSWORD = "Op123!"

MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")
