"""Iter 166 — Certification & Production Readiness (AIB-010) backend tests (HTTP, sync)."""
import os

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
VERDICTS = ("Ready for Production", "Production Ready with Warnings",
            "Ready for Pilot", "Not Ready")


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", "1!nasov01ADMIN")


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def certificate(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/certification/run", timeout=180)
    assert r.status_code == 200
    return r.json()


def test_release_certificate_structure(certificate):
    c = certificate
    assert c["verdict"] in VERDICTS
    assert c["version"] == "1.0.0"
    for f in ("scores", "certified_components", "experimental_components", "failed_components",
              "components", "critical_issues", "minor_issues", "recommendations",
              "architecture", "health", "explainability", "stress", "pilot_readiness"):
        assert f in c, f"câmp lipsă în certificat: {f}"


def test_all_nine_components_audited(certificate):
    ids = {comp["id"] for comp in certificate["components"]}
    assert ids == {f"AIB-00{i}" for i in range(1, 10)}
    assert not certificate["failed_components"], \
        f"componente picate: {certificate['failed_components']}"
    assert len(certificate["certified_components"]) >= 8


def test_guardian_scores(certificate):
    s = certificate["scores"]
    assert set(s) == {"ai_brain_score", "reliability_score",
                      "explainability_score", "stability_score"}
    assert all(0 <= v <= 100 for v in s.values())
    assert s["ai_brain_score"] >= 85 and s["explainability_score"] >= 95


def test_verdict_certified_for_pilot(certificate):
    assert certificate["verdict"] != "Not Ready", \
        f"AI Brain necertificat: {certificate['critical_issues']}"
    assert not certificate["critical_issues"]


def test_health_checks(certificate):
    h = certificate["health"]
    for f in ("latencies_ms", "memory_mb", "cpu_load_1m", "recent_log_errors",
              "internal_errors", "slow_engines"):
        assert f in h
    assert not h["internal_errors"], h["internal_errors"]
    for engine in ("mongodb_ping", "context_engine", "process_engine",
                   "decision_engine", "knowledge_graph", "llm_roundtrip"):
        assert engine in h["latencies_ms"], f"latență nemăsurată: {engine}"
    assert h["memory_mb"] > 0


def test_explainability_100(certificate):
    e = certificate["explainability"]
    assert e["recommendations_checked"] > 50
    assert e["explainability_score"] >= 95, \
        f"recomandări nejustificate: {e['unjustified_samples']}"


def test_stress_zero_errors(certificate):
    st = certificate["stress"]
    assert st["concurrent_operations"] >= 50
    assert st["error_count"] == 0, st["errors"]
    assert st["pass"] is True


def test_pilot_readiness_levels(certificate):
    levels = {p["level"]: p for p in certificate["pilot_readiness"]}
    assert set(levels) == {"pilot_13_apartamente", "pilot_100_apartamente",
                           "scale_1000_apartamente"}
    assert levels["pilot_13_apartamente"]["verdict"] in ("ready", "ready_with_warnings"), \
        levels["pilot_13_apartamente"]["blockers"]


def test_certificate_persisted(admin_session, certificate):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/certification/latest", timeout=30)
    assert r.status_code == 200
    assert r.json()["generated_at"] == certificate["generated_at"]


def test_tech_debt_scanner(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/certification/debt", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for f in ("unused_api_module_candidates", "possibly_unused_process_states",
              "abandoned_processes", "guardian_open_findings", "note"):
        assert f in d
    assert "read-only" in d["note"]


def test_status_includes_certification(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/status", timeout=30)
    d = r.json()
    assert d["version"] == "1.0.0"
    assert "certification" in d["capabilities"]
    assert d["certification"] and d["certification"]["verdict"] in VERDICTS


def test_certification_admin_only(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/certification/latest", timeout=15)
    assert r.status_code in (401, 403)
    r2 = client_session.post(f"{BASE_URL}/api/admin/ai-brain/certification/run", timeout=15)
    assert r2.status_code in (401, 403)
