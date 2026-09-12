"""
PRODUCTION SAFETY CHECK — READ-ONLY comprehensiv.

Scope: verificarea prerequisites pentru orice migrare/cleanup demo accounts
sau redeploy Beta impersonation remediation.

Guvernanță aplicabilă:
- PREFLIGHT_GATE §6: contradicție canonic-vs-runtime = audit țintit permis.
- Governance Activation Report Phase 8: 0 writes, 0 deletions, 0 migrations,
  0 deployments. Acest script respectă TOATE aceste constrângeri.

Cele 5 secțiuni:
  1. DEMO ACCOUNTS — clasificare A/B/C/D/E pentru fiecare @propmanage.io
  2. PAYMENT SAFETY — cross-check financial references pt candidații deletable
  3. IMPERSONATION SAFETY — cine a fost impersonat vs. useri reali
  4. DEMO ALLOWLIST — diff runtime DB vs. allowlist canonic
  5. DEPLOYMENT READINESS — prereqs pentru redeploy fix impersonare

Utilizare:
  cd /app/backend
  python -m scripts.production_safety_check

  # Sau, pentru raport JSON pur (pt automatizare):
  python -m scripts.production_safety_check --json

Ieșire:
  Stdout: raport human-readable + JSON structurat.
  Exit code: 0 dacă PRODUCTION SAFE TO PROCEED, 1 dacă PRODUCTION BLOCKED.

CONSTRÂNGERI stricte:
  - Zero writes în DB.
  - Zero delete.
  - Zero migrate.
  - Zero deploy.
  - Zero mutații pe orice colecție.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routes.impersonation import DEMO_IMPERSONATION_ACCOUNTS  # noqa: E402

# ------------------------------------------------------------------
# Clasificatori — regex / seturi pentru clasificare A/B/C/D/E
# ------------------------------------------------------------------
PRESEEDED_NON_ALLOWLIST_DEMOS = {
    # Conturi preseedate în seed scripts, dar NU în allowlist quick-switch.
    # Motiv istoric: seed pre-Task 8, folosite manual pentru testing.
    "specialist2@propmanage.io",
    "franciza.cluj@propmanage.io",
    "admin@propmanage.io",  # admin canonic, nu se impersonează
}

# Emailurile din allowlist canonic sunt OFFICIAL DEMO (A)
ALLOWLIST_EMAILS = set(DEMO_IMPERSONATION_ACCOUNTS.keys())

# Pattern-uri clare TEST/E2E (B/C)
E2E_PATTERNS = [
    re.compile(r"^test_[0-9a-f]{8}@propmanage\.io$"),           # test_XXXXXXXX
    re.compile(r"^test_p52_[0-9a-f]+@propmanage\.io$"),         # test_p52_*
    re.compile(r"^test_diag[0-9]+@propmanage\.io$"),            # test_diag2, test_diag3
    re.compile(r"^specnew_[0-9a-f]{6}@propmanage\.io$"),        # specnew_XXXXXX
    re.compile(r"^e2e[_.-].+@propmanage\.io$"),
    re.compile(r"^cx[0-9]*[._-]audit.+@propmanage\.io$"),
]

# Pattern-uri sub-admini / roluri de servicii — preseedate dar NU official
SUB_ADMIN_PATTERNS = [
    re.compile(r"^(backend|frontend|general|ops|security|marketing|temp)\.admin@propmanage\.io$"),
]

# Pattern-uri ambigue TEST (candidați B, dar necesită confirmare)
AMBIGUOUS_TEST_PATTERNS = [
    re.compile(r"^entry\.demo@propmanage\.io$"),
    re.compile(r"^pending@propmanage\.io$"),
    re.compile(r"^mp\.partner\.test@propmanage\.io$"),
]


def classify_email(email: str, user_doc: dict) -> str:
    """Returnează clasificarea A/B/C/D/E. NU decide ștergerea — doar clasifică."""
    email_l = email.lower()
    if email_l in ALLOWLIST_EMAILS or email_l in PRESEEDED_NON_ALLOWLIST_DEMOS:
        return "A"  # OFFICIAL DEMO — protected
    if any(p.match(email_l) for p in E2E_PATTERNS):
        return "C"  # E2E ACCOUNT — candidate cleanup
    if any(p.match(email_l) for p in SUB_ADMIN_PATTERNS):
        # Sub-admini de servicii sunt candidați TEST (B) — dar cu prudență
        # (unii pot fi folosiți în CI/CD). Vezi financial refs pentru decizie.
        return "B"
    if any(p.match(email_l) for p in AMBIGUOUS_TEST_PATTERNS):
        return "B"  # TEST candidate, dar cu review manual
    return "D"  # UNKNOWN — MUST NOT DELETE fără review Fondator


async def count_financial_refs(db, user_id: str, email: str) -> dict[str, Any]:
    """Numără toate referințele financiare/marketplace pentru un user.
    NU modifică nimic. Rezultat = 0 pentru toate → candidat safe.
    Orice > 0 → escalare la clasa E (POSSIBLE REAL/USED)."""
    refs = {}
    refs["payment_transactions_client"] = await db.payment_transactions.count_documents({"client_id": user_id})
    refs["payment_transactions_email"] = await db.payment_transactions.count_documents({"user_email": email})
    refs["transactions_by_user"] = await db.transactions.count_documents({"user_id": user_id})
    refs["hh_subscriptions"] = await db.hh_subscriptions.count_documents({"user_id": user_id})
    refs["pb_ledger"] = await db.pb_ledger.count_documents({"user_id": user_id})
    refs["properties_owned"] = await db.properties.count_documents({"owner_id": user_id})
    refs["requests_as_client"] = await db.requests.count_documents({"client_id": user_id})
    refs["requests_as_specialist"] = await db.requests.count_documents({"specialist_id": user_id})
    refs["marketplace_offers"] = await db.marketplace_offers.count_documents({
        "$or": [{"client_id": user_id}, {"specialist_id": user_id}]
    })
    # Stripe references (dacă colecția există)
    try:
        refs["stripe_customers"] = await db.stripe_customers.count_documents({"user_id": user_id})
    except Exception:
        refs["stripe_customers"] = 0
    try:
        refs["stripe_subscriptions"] = await db.stripe_subscriptions.count_documents({"user_id": user_id})
    except Exception:
        refs["stripe_subscriptions"] = 0
    try:
        refs["wallet"] = await db.wallet.count_documents({"user_id": user_id})
    except Exception:
        refs["wallet"] = 0

    refs["total"] = sum(v for v in refs.values() if isinstance(v, int))
    # Flag: cel puțin o referință financiară REALĂ (non-demo)
    refs["has_real_payment"] = (
        refs["payment_transactions_client"] > 0
        or refs["transactions_by_user"] > 0
        or refs["stripe_customers"] > 0
        or refs["stripe_subscriptions"] > 0
    )
    return refs


async def audit_impersonation_history(db) -> dict[str, Any]:
    """Section 3: impersonation safety.
    Verifică dacă vreun user real a fost impersonat (target NU e demo)."""
    total_logs = await db.impersonation_logs.count_documents({})

    # Ia toți target-users care NU sunt în allowlist ȘI nu au is_demo_account=True
    suspicious = []
    seen_targets = set()
    cursor = db.impersonation_logs.find({}).sort("started_at", -1).limit(500)
    async for log in cursor:
        target_email = (log.get("target_user_email") or "").lower()
        target_id = log.get("target_user_id")
        if not target_email:
            continue
        key = (target_id, target_email)
        if key in seen_targets:
            continue
        seen_targets.add(key)

        # E în allowlist? = OK
        if target_email in ALLOWLIST_EMAILS:
            continue
        if target_email in PRESEEDED_NON_ALLOWLIST_DEMOS:
            continue

        # Verifică dacă user-ul e demo_account
        target_doc = await db.users.find_one({"_id": target_id}) if target_id else None
        if target_doc and target_doc.get("is_demo_account"):
            continue

        # Suspicious — user real a fost impersonat
        suspicious.append({
            "target_email": target_email,
            "target_user_id": str(target_id) if target_id else None,
            "target_user_name": log.get("target_user_name"),
            "target_user_role": log.get("target_user_role"),
            "admin_email": log.get("admin_email"),
            "started_at": log.get("started_at"),
            "ended_at": log.get("ended_at"),
            "duration_seconds": log.get("duration_seconds"),
            "reason": log.get("reason"),
            "ip": log.get("ip"),
            "target_is_demo_flag": bool(target_doc.get("is_demo_account")) if target_doc else None,
            "target_exists_now": bool(target_doc),
        })

    return {
        "total_impersonation_logs": total_logs,
        "distinct_targets_checked_last_500": len(seen_targets),
        "suspicious_real_user_access": suspicious,
    }


async def check_deployment_readiness(db) -> dict[str, Any]:
    """Section 5: deployment readiness pentru fix impersonare Beta."""
    readiness = {}

    # 5.1 — fix codat în impersonation.py (verifică prezența strong guard)
    import inspect
    from routes import impersonation as imp_module
    src = inspect.getsource(imp_module)
    readiness["fallback_guard_present"] = "Impersonare refuzată" in src and "raise HTTPException(409" in src
    readiness["allowlist_size"] = len(DEMO_IMPERSONATION_ACCOUNTS)
    readiness["ensure_demo_endpoint_present"] = "ensure-demo-target" in src

    # 5.2 — governance docs prezente
    docs_ok = True
    for path in [
        "/app/memory/prompts/PREFLIGHT_GATE.md",
        "/app/memory/registries/CANONICAL_SYSTEM_REGISTRY.md",
    ]:
        if not os.path.exists(path):
            docs_ok = False
            break
    readiness["governance_docs_present"] = docs_ok

    # 5.3 — impersonation_logs colecție are indexuri necesare
    try:
        indexes = await db.impersonation_logs.index_information()
        readiness["impersonation_logs_indexes"] = list(indexes.keys())
    except Exception as e:
        readiness["impersonation_logs_indexes_error"] = str(e)

    # 5.4 — CSRF guard prezent
    try:
        with open("/app/backend/server.py") as f:
            server_src = f.read()
        readiness["csrf_origin_guard_present"] = "_csrf_origin_guard" in server_src or "X-PM-Client" in server_src
    except Exception:
        readiness["csrf_origin_guard_present"] = None

    # 5.5 — test_credentials.md documentează contul Beta
    try:
        with open("/app/memory/test_credentials.md") as f:
            creds = f.read()
        readiness["test_credentials_covers_beta"] = "client.beta" in creds or "beta@propmanage" in creds
    except Exception:
        readiness["test_credentials_covers_beta"] = None

    return readiness


async def run_full_check() -> dict[str, Any]:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL / DB_NAME lipsesc.")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    now_iso = datetime.now(timezone.utc).isoformat()
    report = {
        "generated_at": now_iso,
        "environment_db": db_name,
        "sections": {},
    }

    # ============================================================
    # SECTION 1 — DEMO ACCOUNTS CLASSIFICATION
    # ============================================================
    section1 = {"A_official_demo": [], "B_test": [], "C_e2e": [], "D_unknown": [], "E_possible_real": []}
    cursor = db.users.find({"email": {"$regex": "@propmanage\\.io$"}}).sort("created_at", 1)
    async for doc in cursor:
        email = (doc.get("email") or "").lower()
        user_id = str(doc["_id"])
        role = doc.get("role")
        tier = doc.get("tier")
        is_demo = bool(doc.get("is_demo_account"))
        created_at = doc.get("created_at")
        last_login = doc.get("last_login_at") or doc.get("last_active_at")

        # Financial refs — mandatory pentru clasa E
        refs = await count_financial_refs(db, user_id, email)

        # Impersonation ref count
        imp_count = await db.impersonation_logs.count_documents({"target_user_id": user_id})

        base_class = classify_email(email, doc)

        # ELEVARE la E dacă are payment/subscription real
        if refs["has_real_payment"] and base_class in ("B", "C", "D"):
            base_class = "E"

        entry = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "tier": tier,
            "is_demo_account": is_demo,
            "created_at": str(created_at) if created_at else None,
            "last_activity": str(last_login) if last_login else None,
            "financial_refs": refs,
            "impersonation_target_count": imp_count,
            "classification": base_class,
        }

        if base_class == "A":
            section1["A_official_demo"].append(entry)
        elif base_class == "B":
            section1["B_test"].append(entry)
        elif base_class == "C":
            section1["C_e2e"].append(entry)
        elif base_class == "D":
            section1["D_unknown"].append(entry)
        else:
            section1["E_possible_real"].append(entry)

    section1["counts"] = {k: len(v) for k, v in section1.items() if k != "counts"}
    report["sections"]["1_demo_accounts"] = section1

    # ============================================================
    # SECTION 2 — PAYMENT SAFETY (deja capturate în section 1)
    # ============================================================
    # Extrage din section1: candidații deletable (B+C+D fără financial refs)
    candidates_safe_to_delete = []
    candidates_blocked = []
    for grp in ("B_test", "C_e2e", "D_unknown"):
        for entry in section1[grp]:
            if entry["financial_refs"]["total"] == 0 and entry["impersonation_target_count"] == 0:
                candidates_safe_to_delete.append({
                    "user_id": entry["user_id"],
                    "email": entry["email"],
                    "classification": entry["classification"],
                    "reason": "zero financial + zero impersonation refs",
                })
            else:
                candidates_blocked.append({
                    "user_id": entry["user_id"],
                    "email": entry["email"],
                    "classification": entry["classification"],
                    "refs_total": entry["financial_refs"]["total"],
                    "impersonation_count": entry["impersonation_target_count"],
                    "reason": "has references — MUST NOT DELETE",
                })
    report["sections"]["2_payment_safety"] = {
        "candidates_safe_to_delete_after_founder_approval": candidates_safe_to_delete,
        "candidates_blocked_by_refs": candidates_blocked,
        "safe_count": len(candidates_safe_to_delete),
        "blocked_count": len(candidates_blocked),
    }

    # ============================================================
    # SECTION 3 — IMPERSONATION SAFETY
    # ============================================================
    report["sections"]["3_impersonation_safety"] = await audit_impersonation_history(db)

    # ============================================================
    # SECTION 4 — DEMO ALLOWLIST DIFF
    # ============================================================
    section4 = {
        "missing_official_demos": [],
        "unexpected_demos": [],
        "role_drift": [],
        "tier_drift": [],
        "demo_flag_drift": [],
    }
    for email, spec in DEMO_IMPERSONATION_ACCOUNTS.items():
        doc = await db.users.find_one({"email": email})
        if not doc:
            section4["missing_official_demos"].append({
                "email": email,
                "expected_role": spec["role"],
                "expected_tier": spec.get("tier"),
            })
            continue
        if doc.get("role") != spec["role"]:
            section4["role_drift"].append({
                "email": email,
                "expected": spec["role"],
                "actual": doc.get("role"),
                "user_id": str(doc["_id"]),
            })
        # Tier compare case-insensitive
        exp_tier = spec.get("tier")
        act_tier = doc.get("tier")
        if (exp_tier or "") != (act_tier or "") and (exp_tier or "").upper() != (act_tier or "").upper():
            section4["tier_drift"].append({
                "email": email,
                "expected": exp_tier,
                "actual": act_tier,
                "user_id": str(doc["_id"]),
            })
        elif exp_tier and act_tier and exp_tier != act_tier:
            # Case-only diff (VERIFIED vs verified)
            section4["tier_drift"].append({
                "email": email,
                "expected": exp_tier,
                "actual": act_tier,
                "cosmetic": True,
                "user_id": str(doc["_id"]),
            })
        if not doc.get("is_demo_account"):
            section4["demo_flag_drift"].append({
                "email": email,
                "user_id": str(doc["_id"]),
                "note": "is_demo_account=False sau lipsă",
            })
    # unexpected_demos: useri cu is_demo_account=True dar NU în allowlist
    cursor = db.users.find({"is_demo_account": True})
    async for doc in cursor:
        email = (doc.get("email") or "").lower()
        if email not in ALLOWLIST_EMAILS and email not in PRESEEDED_NON_ALLOWLIST_DEMOS:
            section4["unexpected_demos"].append({
                "email": email,
                "user_id": str(doc["_id"]),
                "role": doc.get("role"),
            })
    report["sections"]["4_demo_allowlist_diff"] = section4

    # ============================================================
    # SECTION 5 — DEPLOYMENT READINESS
    # ============================================================
    report["sections"]["5_deployment_readiness"] = await check_deployment_readiness(db)

    # ============================================================
    # VERDICT
    # ============================================================
    blockers = []
    # Blocker 1: impersonare pe useri reali
    s3 = report["sections"]["3_impersonation_safety"]
    if s3["suspicious_real_user_access"]:
        blockers.append(
            f"IMPERSONARE PE USER REAL detectată: "
            f"{len(s3['suspicious_real_user_access'])} target-uri suspecte. "
            f"Verifică istoric înainte de cleanup."
        )
    # Blocker 2: role drift pe conturile canonice
    s4 = report["sections"]["4_demo_allowlist_diff"]
    if s4["role_drift"]:
        blockers.append(
            f"ROLE DRIFT pe {len(s4['role_drift'])} conturi din allowlist canonic. "
            f"Blochează impersonarea pt aceste roluri."
        )
    # Blocker 3: fix guard absent
    s5 = report["sections"]["5_deployment_readiness"]
    if not s5.get("fallback_guard_present"):
        blockers.append("FALLBACK GUARD absent din impersonation.py — redeploy critic.")
    if not s5.get("governance_docs_present"):
        blockers.append("Governance docs LIPSESC — nu redeploya fără PREFLIGHT_GATE + CANONICAL_SYSTEM_REGISTRY.")

    report["verdict"] = {
        "status": "PRODUCTION SAFE TO PROCEED" if not blockers else "PRODUCTION BLOCKED",
        "blockers": blockers,
        "safe_to_delete_after_approval_count": report["sections"]["2_payment_safety"]["safe_count"],
        "requires_founder_review_count": (
            len(report["sections"]["1_demo_accounts"]["D_unknown"])
            + len(report["sections"]["1_demo_accounts"]["E_possible_real"])
            + report["sections"]["2_payment_safety"]["blocked_count"]
        ),
    }

    client.close()
    return report


def format_report(report: dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("PRODUCTION SAFETY CHECK — READ-ONLY (zero writes, zero deletes, zero migrations)")
    lines.append("=" * 80)
    lines.append(f"Generat: {report['generated_at']}")
    lines.append(f"DB: {report['environment_db']}")
    lines.append("")

    # Section 1
    s1 = report["sections"]["1_demo_accounts"]
    lines.append("─" * 80)
    lines.append("SECTION 1 — DEMO ACCOUNTS CLASSIFICATION")
    lines.append("─" * 80)
    for cls, label in [
        ("A_official_demo", "A · OFFICIAL DEMO (protected)"),
        ("B_test", "B · TEST ACCOUNT (candidate cleanup)"),
        ("C_e2e", "C · E2E ACCOUNT (candidate cleanup)"),
        ("D_unknown", "D · UNKNOWN (MUST NOT DELETE — Founder review)"),
        ("E_possible_real", "E · POSSIBLE REAL/USED (MUST NOT DELETE)"),
    ]:
        entries = s1[cls]
        lines.append(f"\n  {label}: {len(entries)} conturi")
        for e in entries[:100]:  # limit output
            fin = e["financial_refs"]
            note = ""
            if fin["has_real_payment"]:
                note = " ⚠️ HAS PAYMENT"
            if e["impersonation_target_count"]:
                note += f" · impersonated {e['impersonation_target_count']}×"
            lines.append(
                f"    - {e['email']:<50} role={e['role']:<12} tier={str(e['tier']):<10} "
                f"refs={fin['total']:<4} demo_flag={e['is_demo_account']}{note}"
            )
        if len(entries) > 100:
            lines.append(f"    ... ({len(entries) - 100} entries additionale în JSON output)")

    # Section 2
    s2 = report["sections"]["2_payment_safety"]
    lines.append("\n" + "─" * 80)
    lines.append("SECTION 2 — PAYMENT SAFETY")
    lines.append("─" * 80)
    lines.append(f"\n  Candidați safe to delete (zero refs): {s2['safe_count']}")
    lines.append(f"  Blocked de referințe: {s2['blocked_count']}")
    if s2["candidates_blocked_by_refs"]:
        lines.append("\n  ⚠️  BLOCKED (au refs — MUST NOT DELETE):")
        for c in s2["candidates_blocked_by_refs"][:30]:
            lines.append(
                f"    - {c['email']:<50} class={c['classification']} "
                f"refs={c['refs_total']} imp={c['impersonation_count']}"
            )

    # Section 3
    s3 = report["sections"]["3_impersonation_safety"]
    lines.append("\n" + "─" * 80)
    lines.append("SECTION 3 — IMPERSONATION SAFETY (last 500 logs)")
    lines.append("─" * 80)
    lines.append(f"\n  Total logs: {s3['total_impersonation_logs']}")
    lines.append(f"  Distinct targets checked: {s3['distinct_targets_checked_last_500']}")
    if s3["suspicious_real_user_access"]:
        lines.append(f"\n  🚨 SUSPICIOUS — impersonare pe useri NEDEMO ({len(s3['suspicious_real_user_access'])} cazuri):")
        for c in s3["suspicious_real_user_access"][:20]:
            mut = "N/A" if c.get("ended_at") else "still-active"
            lines.append(
                f"    - target={c['target_email']:<40} role={c['target_user_role']:<10} "
                f"by={c['admin_email']:<30} at={c['started_at']}"
            )
            lines.append(
                f"      reason={c['reason']!r:<40} target_exists_now={c['target_exists_now']} "
                f"demo_flag={c['target_is_demo_flag']}"
            )
    else:
        lines.append("  ✅ Zero impersonări suspecte pe useri reali (bazat pe last 500 logs).")

    # Section 4
    s4 = report["sections"]["4_demo_allowlist_diff"]
    lines.append("\n" + "─" * 80)
    lines.append("SECTION 4 — DEMO ALLOWLIST DIFF (DB vs. canonical allowlist)")
    lines.append("─" * 80)
    for key, label in [
        ("missing_official_demos", "Missing official demos (allowlist zice că trebuie, DB nu are)"),
        ("role_drift", "🚨 ROLE DRIFT (blochează impersonarea)"),
        ("tier_drift", "TIER DRIFT (UX inconsistent)"),
        ("demo_flag_drift", "DEMO FLAG missing/false pe cont canonic"),
        ("unexpected_demos", "UNEXPECTED demo=True dar NU în allowlist"),
    ]:
        entries = s4[key]
        marker = "  ✅" if not entries else "  ⚠️ "
        lines.append(f"\n{marker} {label}: {len(entries)}")
        for e in entries[:30]:
            lines.append(f"    - {json.dumps(e, ensure_ascii=False)}")

    # Section 5
    s5 = report["sections"]["5_deployment_readiness"]
    lines.append("\n" + "─" * 80)
    lines.append("SECTION 5 — DEPLOYMENT READINESS (fix impersonare)")
    lines.append("─" * 80)
    lines.append(f"\n  {'✅' if s5.get('fallback_guard_present') else '❌'} fallback_guard_present (impersonation.py refuză drift): {s5.get('fallback_guard_present')}")
    lines.append(f"  {'✅' if s5.get('ensure_demo_endpoint_present') else '❌'} ensure-demo-target endpoint: {s5.get('ensure_demo_endpoint_present')}")
    lines.append(f"  {'✅' if s5.get('governance_docs_present') else '❌'} governance docs present: {s5.get('governance_docs_present')}")
    lines.append(f"  {'✅' if s5.get('csrf_origin_guard_present') else '❌'} CSRF guard present: {s5.get('csrf_origin_guard_present')}")
    lines.append(f"  Allowlist size: {s5.get('allowlist_size')}")
    lines.append(f"  Indexuri impersonation_logs: {s5.get('impersonation_logs_indexes', [])}")

    # Verdict
    v = report["verdict"]
    lines.append("\n" + "=" * 80)
    if v["status"].startswith("PRODUCTION SAFE"):
        lines.append(f"🟢 {v['status']}")
    else:
        lines.append(f"🔴 {v['status']}")
    lines.append("=" * 80)
    if v["blockers"]:
        lines.append("\nBLOCKERS (necesită decizie Fondator):")
        for b in v["blockers"]:
            lines.append(f"  - {b}")
    lines.append("")
    lines.append(f"Candidați safe to delete după aprobare Fondator: {v['safe_to_delete_after_approval_count']}")
    lines.append(f"Conturi ce necesită Founder review manual: {v['requires_founder_review_count']}")
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--limit", type=int, default=None, help="Limit output entries per class")
    args = parser.parse_args()

    report = await run_full_check()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_report(report))
        print("\n--- MACHINE-READABLE JSON (trailing) ---")
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    return 0 if report["verdict"]["status"].startswith("PRODUCTION SAFE") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
