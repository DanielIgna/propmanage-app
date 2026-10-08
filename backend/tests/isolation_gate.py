"""Fail-closed contract for the pytest process.

This module must not import the application, dotenv, or a MongoDB client.
It only reads process environment variables and test source text.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

TEST_API = "http://localhost:8002"
TEST_MONGO_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "propmanage_test"
DEV_DB_NAME = "propmanage_db"
DEV_API_PORT = 8001

_MONGO_LITERAL = re.compile(
    r"^(?:MONGO_URL|DB_NAME|_MONGO_URL|_DB_NAME)\s*=\s*['\"]"
)
_PROD_HOST = re.compile(r"https?://(?:www\.)?propmanage\.ro", re.I)
_ENV_OPEN = re.compile(r"open\(\s*[^)\n]*\.env")


class IsolationGateError(RuntimeError):
    """Raised when pytest is not explicitly pointed at the isolated test environment."""


def _required(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise IsolationGateError(
            f"{name} is missing. pytest refuses to start. "
            "Export the test contract; development env files are not read."
        )
    return str(value).strip()


def _api_destination(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port
    return f"{parsed.scheme}://{host}:{port}" if port else f"{parsed.scheme}://{host}"


def enforce_test_environment() -> None:
    """Reject every configuration except the local isolated test contract."""
    api = _required("REACT_APP_BACKEND_URL").rstrip("/")
    mongo = _required("MONGO_URL")
    db_name = _required("DB_NAME")

    lowered = api.lower()
    if "emergent" in lowered:
        raise IsolationGateError(
            "REACT_APP_BACKEND_URL points at an Emergent preview host. "
            "pytest will not continue."
        )
    if "propmanage.ro" in lowered:
        raise IsolationGateError(
            "REACT_APP_BACKEND_URL points at propmanage.ro. "
            "Production is never a pytest target."
        )
    destination = _api_destination(api)
    if destination.endswith(f":{DEV_API_PORT}") or ":8001" in destination:
        raise IsolationGateError(
            "REACT_APP_BACKEND_URL points at the development API port 8001. "
            "pytest will not continue."
        )
    if api != TEST_API:
        raise IsolationGateError(
            "REACT_APP_BACKEND_URL is not the isolated test API "
            f"{TEST_API}. pytest will not continue."
        )

    if "://" in mongo and "@" in mongo.split("://", 1)[1]:
        raise IsolationGateError(
            "MONGO_URL contains credentials. The test contract is the local "
            "server without credentials. pytest will not continue."
        )
    if mongo.startswith("mongodb+srv") or "mongodb.net" in mongo.lower():
        raise IsolationGateError(
            "MONGO_URL is not the local MongoDB server. "
            "Atlas and other remote hosts are refused."
        )
    if mongo not in {TEST_MONGO_URL, TEST_MONGO_URL + "/"}:
        raise IsolationGateError(
            "MONGO_URL is not mongodb://localhost:27017. "
            "pytest will not fall back to another database server."
        )

    if db_name == DEV_DB_NAME:
        raise IsolationGateError(
            "DB_NAME is propmanage_db, the development database. "
            "pytest will not continue."
        )
    if db_name != TEST_DB_NAME:
        raise IsolationGateError(
            "DB_NAME is not propmanage_test. "
            "An empty or other database name is refused."
        )


def _literal_mongo_assignment(text: str) -> bool:
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if "os.environ" in line:
            continue
        if _MONGO_LITERAL.match(line):
            return True
    return False


def _opens_env_file(text: str) -> bool:
    if _ENV_OPEN.search(text):
        return True
    return "open(" in text and "'.env'" in text or "open(" in text and '".env"' in text


def classify_test_file(path: Path) -> tuple[str | None, str]:
    """Return ('blocker'|'latent'|None, reason) from source text only."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    blockers: list[str] = []
    if "/app/backend/.env" in text or "/app/frontend/.env" in text:
        blockers.append("reads an /app env file")
    if "load_dotenv(" in text:
        blockers.append("calls load_dotenv")
    if _literal_mongo_assignment(text):
        blockers.append("assigns a literal MongoDB URL or database name")
    if "PREVIEW_API" in text:
        blockers.append("uses PREVIEW_API instead of the test API contract")
    if _opens_env_file(text):
        blockers.append("opens a .env file")
    if blockers:
        return "blocker", "; ".join(blockers)

    latent: list[str] = []
    if "emergentagent.com" in text or "emergent.host" in text:
        latent.append("Emergent host fallback")
    if DEV_DB_NAME in text:
        latent.append("development database name fallback")
    if "localhost:8001" in text or "127.0.0.1:8001" in text:
        latent.append("development API port fallback")
    for raw in text.splitlines():
        if "propmanage.ro" in raw and re.search(
            r"BASE_URL|SMOKE_BASE_URL|API\s*=|getenv|environ", raw
        ):
            latent.append("production host literal")
            break
    if latent:
        return "latent", "; ".join(dict.fromkeys(latent))
    return None, ""
