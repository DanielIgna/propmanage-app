"""Regression — Admin smoke-test credential drift fix (Faza remediation)."""
import importlib
import os


def _reload():
    import routes.admin_smoketest as m
    return importlib.reload(m)


def test_admin_smoke_password_prefers_seed(monkeypatch):
    # Smoke admin credential must follow the SEEDED password, not a stale hardcoded default.
    monkeypatch.delenv("SMOKE_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "SeededSecret!123")
    m = _reload()
    assert m.ROLE_CREDENTIALS["admin"]["password"] == "SeededSecret!123"
    assert m.ROLE_CREDENTIALS["admin"]["email"] == "admin@propmanage.io"


def test_admin_smoke_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("SMOKE_ADMIN_PASSWORD", "ExplicitOverride!")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "SeededSecret!123")
    m = _reload()
    assert m.ROLE_CREDENTIALS["admin"]["password"] == "ExplicitOverride!"


def test_admin_smoke_falls_back_to_admin_password(monkeypatch):
    monkeypatch.delenv("SMOKE_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminEnvPw!")
    m = _reload()
    assert m.ROLE_CREDENTIALS["admin"]["password"] == "AdminEnvPw!"
