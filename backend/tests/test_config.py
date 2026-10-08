"""Shared test credentials.

The pytest process does not load backend/.env or frontend/.env.
REACT_APP_BACKEND_URL, MONGO_URL, and DB_NAME must already be exported.
See TEST_ENVIRONMENT.md.
"""
import os

from tests.isolation_gate import enforce_test_environment

enforce_test_environment()

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
OWNER_ADMIN_PASSWORD = (
    os.environ.get("SEED_ADMIN_PASSWORD")
    or os.environ.get("TEST_ADMIN_PASSWORD")
    or "Admin123!"
)
ADMIN_PASSWORDS = list(dict.fromkeys([OWNER_ADMIN_PASSWORD, "Admin123!"]))

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
SPECIALIST_EMAIL = "specialist@propmanage.io"
SPECIALIST_PASSWORD = "Spec123!"
OPERATOR_EMAIL = "operator@propmanage.io"
OPERATOR_PASSWORD = "Op123!"

MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")
