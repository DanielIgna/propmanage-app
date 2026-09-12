"""
DIAGNOSTIC — dry-run pentru driftul conturilor demo de impersonare.

RULEZI TU (Fondator) acest script în producție (sau în orice mediu) după
`python audit_demo_accounts_drift.py`. Scriptul NU modifică nimic.
Raportează DOAR:
  - conturi lipsă (nu există în DB dar sunt în allowlist)
  - conturi cu rol drift-uit (există dar au rol diferit față de allowlist)
  - conturi cu tier drift-uit (rol OK, dar tier diferit)
  - conturi fără flagul `is_demo_account=True`
  - conturi care există în DB cu email @propmanage.io dar NU sunt în allowlist
    (candidați REMOVE sau DUPLICATE)

Motiv: incident 24 Aug 2026 (client.beta impersonare cădea pe user real
Mihăilă Petru); protecția din impersonation.py acum refuză impersonarea
la drift de rol (409). Însă driftul rămâne în DB și blochează impersonarea
UX admin. Acest script identifică driftul înainte de decizia Fondator
privind migrarea țintită.

Guvernanță aplicabilă: PREFLIGHT_GATE §6 (contradicție canonic-vs-runtime =
condiție legitimă pentru audit țintit + escalare Fondator).

Utilizare:
  cd /app/backend
  python -m scripts.audit_demo_accounts_drift

Ieșire: JSON structurat + tabel human-readable la stdout. Cod de ieșire:
  0 = zero drift
  1 = drift găsit (pentru integrare în CI/monitoring, dacă vrei ulterior)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

# Import canonic allowlist — SINGURA sursă validă.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routes.impersonation import DEMO_IMPERSONATION_ACCOUNTS  # noqa: E402


async def audit() -> dict[str, Any]:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL / DB_NAME lipsesc din environment.")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    report = {
        "checked_emails": len(DEMO_IMPERSONATION_ACCOUNTS),
        "missing_from_db": [],
        "role_drift": [],
        "tier_drift": [],
        "flag_missing": [],
        "unlisted_propmanage_io": [],
        "healthy": [],
    }

    # 1. Verifică fiecare email din allowlist
    for email, spec in DEMO_IMPERSONATION_ACCOUNTS.items():
        doc = await db.users.find_one({"email": email})
        if not doc:
            report["missing_from_db"].append({
                "email": email,
                "expected_role": spec["role"],
                "expected_tier": spec.get("tier"),
                "expected_name": spec["name"],
            })
            continue

        actual_role = doc.get("role")
        actual_tier = doc.get("tier")
        actual_flag = bool(doc.get("is_demo_account"))

        drift_entry = {
            "email": email,
            "expected_role": spec["role"],
            "actual_role": actual_role,
            "expected_tier": spec.get("tier"),
            "actual_tier": actual_tier,
            "is_demo_account": actual_flag,
            "user_id": str(doc["_id"]),
        }

        if actual_role != spec["role"]:
            report["role_drift"].append(drift_entry)
        elif actual_tier != spec.get("tier"):
            report["tier_drift"].append(drift_entry)
        elif not actual_flag:
            report["flag_missing"].append(drift_entry)
        else:
            report["healthy"].append({
                "email": email,
                "role": actual_role,
                "tier": actual_tier,
            })

    # 2. Detectează conturi @propmanage.io care NU sunt în allowlist
    allowlist_emails = set(DEMO_IMPERSONATION_ACCOUNTS.keys())
    cursor = db.users.find({"email": {"$regex": "@propmanage\\.io$"}})
    async for doc in cursor:
        email = (doc.get("email") or "").lower()
        if email not in allowlist_emails:
            report["unlisted_propmanage_io"].append({
                "email": email,
                "role": doc.get("role"),
                "tier": doc.get("tier"),
                "is_demo_account": bool(doc.get("is_demo_account")),
                "user_id": str(doc["_id"]),
            })

    client.close()
    return report


def print_report(report: dict[str, Any]) -> int:
    print("=" * 78)
    print("DIAGNOSTIC — DRIFT CONTURI DEMO IMPERSONARE (dry-run, zero modificări)")
    print("=" * 78)
    print(f"\nEmailuri verificate (allowlist canonic): {report['checked_emails']}\n")

    def section(title: str, items: list, formatter):
        marker = "✅" if not items else "⚠️ "
        print(f"{marker} {title}: {len(items)}")
        for it in items:
            print(f"   - {formatter(it)}")
        print()

    section(
        "MISSING FROM DB (allowlist zice că trebuie să existe, DB nu are)",
        report["missing_from_db"],
        lambda x: f"{x['email']} → aștept role={x['expected_role']}, tier={x['expected_tier']}",
    )
    section(
        "ROLE DRIFT (există dar are ALT rol — BLOCHEAZĂ impersonarea)",
        report["role_drift"],
        lambda x: f"{x['email']}: expected role={x['expected_role']} · actual role={x['actual_role']}",
    )
    section(
        "TIER DRIFT (rol OK, dar tier diferit — UX inconsistent)",
        report["tier_drift"],
        lambda x: f"{x['email']}: expected tier={x['expected_tier']} · actual tier={x['actual_tier']}",
    )
    section(
        "FLAG MISSING (rol+tier OK, dar is_demo_account nu e True — audit gap)",
        report["flag_missing"],
        lambda x: f"{x['email']}: is_demo_account={x['is_demo_account']}",
    )
    section(
        "UNLISTED @propmanage.io (există în DB, NU e în allowlist — candidat REMOVE sau DUPLICATE)",
        report["unlisted_propmanage_io"],
        lambda x: f"{x['email']}: role={x['role']}, tier={x['tier']}, demo_flag={x['is_demo_account']}",
    )

    print(f"✅ HEALTHY: {len(report['healthy'])} conturi aliniate cu allowlist-ul canonic.\n")

    total_issues = (
        len(report["missing_from_db"])
        + len(report["role_drift"])
        + len(report["tier_drift"])
        + len(report["flag_missing"])
        + len(report["unlisted_propmanage_io"])
    )

    print("-" * 78)
    if total_issues == 0:
        print("✅ ZERO drift detectat. Allowlist-ul canonic și DB sunt aliniate.")
    else:
        print(f"⚠️  DRIFT DETECTAT: {total_issues} conturi cu probleme.")
        print("   URMĂTORUL PAS (decizia Fondator, per PREFLIGHT_GATE §3):")
        print("   1) Verifică fiecare rând drift-uit (poate fi conștient — ex. cont abandonat).")
        print("   2) Dacă vrei repair: autorizează un script de migrare țintită separat.")
        print("      Acest audit rămâne read-only.")
    print("-" * 78)

    # JSON structurat la sfârșit pentru integrare programatică
    print("\n--- MACHINE-READABLE JSON ---")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if total_issues == 0 else 1


async def main() -> int:
    report = await audit()
    return print_report(report)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
