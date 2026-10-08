"""Pytest session gate for the isolated test environment.

Development stays on propmanage_db and port 8001.
This process refuses to start unless it is explicitly pointed at
propmanage_test and http://localhost:8002.
"""
import sys
from pathlib import Path

import pytest
import requests

from tests.isolation_gate import (
    TEST_API,
    IsolationGateError,
    classify_test_file,
    enforce_test_environment,
)

try:
    enforce_test_environment()
except IsolationGateError as exc:
    raise pytest.UsageError(str(exc)) from exc

from tests.test_config import OWNER_ADMIN_PASSWORD  # noqa: E402
import os  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}

_BLOCKED: list[tuple[str, str]] = []


def pytest_ignore_collect(collection_path, config):  # noqa: ARG001
    """Do not import files that can ignore the test contract."""
    path = Path(str(collection_path))
    if path.suffix != ".py" or not path.name.startswith("test_"):
        return False
    if not path.is_file():
        return False
    kind, reason = classify_test_file(path)
    if kind == "blocker":
        _BLOCKED.append((path.name, reason))
        return True
    return False


def pytest_collection_finish(session):
    """Refuse a green full run while bypass files still exist."""
    latent: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in session.items:
        path = Path(str(item.fspath))
        if path.name in seen:
            continue
        seen.add(path.name)
        kind, reason = classify_test_file(path)
        if kind == "latent":
            latent.append((path.name, reason))

    if _BLOCKED:
        lines = [
            "TEST ISOLATION GATE: collection refused.",
            "No test body ran. Blocker files were not imported and made no database calls from this gate.",
            "",
            "Pass 2 blockers — these files bypass the contract or load an env file:",
        ]
        for name, reason in _BLOCKED:
            lines.append(f"  - {name}: {reason}")
        if latent:
            lines.append("")
            lines.append(
                "Latent fallbacks were collected and were not executed "
                "because this session was refused:"
            )
            for name, reason in latent:
                lines.append(f"  - {name}: {reason}")
        lines.append("")
        lines.append(
            "The suite is not fully isolated. "
            "A full directory run stays refused until those files are migrated."
        )
        pytest.exit("\n".join(lines), returncode=3)

    if latent:
        text = "\n".join(f"  - {name}: {reason}" for name, reason in latent)
        print(
            "\nTEST ISOLATION: contract accepted for this selection.\n"
            "These files still contain unsafe fallbacks (Pass 2). "
            "They are running only because the test contract is already exported:\n"
            f"{text}\n",
            file=sys.stderr,
        )


@pytest.fixture(scope="session", autouse=True)
def reset_demo_state():
    """Re-baseline demo accounts on the isolated test API only."""
    try:
        enforce_test_environment()
    except IsolationGateError as exc:
        pytest.fail(str(exc))
    if BASE_URL != TEST_API:
        pytest.fail(
            "Demo reset refused. The fixture only calls the isolated test API."
        )

    session = requests.Session()
    try:
        login = session.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    except requests.RequestException as exc:
        pytest.fail(
            "Isolated test API is unavailable. "
            f"Demo reset was not skipped. {type(exc).__name__}: {exc}"
        )
    if login.status_code != 200:
        pytest.fail(
            "Login to the isolated test API failed with "
            f"HTTP {login.status_code}. Demo reset was not skipped."
        )
    try:
        reset = session.post(f"{API}/admin/demo/reset", timeout=20)
    except requests.RequestException as exc:
        pytest.fail(
            "Isolated test API is unavailable during demo reset. "
            f"The error was not ignored. {type(exc).__name__}: {exc}"
        )
    if reset.status_code != 200:
        pytest.fail(
            "Demo reset on the isolated test API failed with "
            f"HTTP {reset.status_code}. The session was not continued."
        )
    yield
