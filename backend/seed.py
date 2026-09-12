"""Idempotent seed for demo accounts, properties, requests, twins, regions, portfolio."""
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from db import db
from core_utils import hash_password, verify_password

logger = logging.getLogger(__name__)


async def seed():
    """Seed demo accounts + properties + sample requests (idempotent)."""
    await db.users.create_index("email", unique=True)

    demo_users = [
        {"email": "client@propmanage.io", "password": "Client123!", "name": "Andrei Popescu", "role": "client", "phone": "+40 712 345 678"},
        {"email": "specialist@propmanage.io", "password": "Spec123!", "name": "Mihai Ionescu", "role": "specialist", "specialty": "hvac", "phone": "+40 723 456 789"},
        {"email": "specialist2@propmanage.io", "password": "Spec123!", "name": "Elena Dumitru", "role": "specialist", "specialty": "plumbing", "phone": "+40 734 567 890"},
        {"email": "pending@propmanage.io", "password": "Spec123!", "name": "Vasile Constantinescu", "role": "specialist", "specialty": "electric", "phone": "+40 745 678 901", "_pending": True},
        {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN", "name": "Administrator", "role": "admin", "phone": ""},
        {"email": "operator@propmanage.io", "password": "Op123!", "name": "Lucian Stan", "role": "operator", "phone": ""},
    ]

    user_ids = {}
    for u in demo_users:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            user_ids[u["email"]] = str(existing["_id"])
            update_fields = {}
            if not verify_password(u["password"], existing["password_hash"]):
                update_fields["password_hash"] = hash_password(u["password"])
            if u["role"] == "specialist":
                update_fields["coverage_zones"] = ["Bucuresti-Sector1", "Bucuresti-Sector2"]
                update_fields["service_categories"] = [u.get("specialty"), "interior_design"] if u.get("specialty") else ["interior_design"]
                update_fields["availability_status"] = existing.get("availability_status") or "available"
                if u.get("_pending") and existing.get("verified"):
                    update_fields["verified"] = False
                    update_fields["tier"] = None
                    update_fields["rating"] = None
                    update_fields["reviews_count"] = 0
                    if not (existing.get("documents") or []):
                        now_iso = datetime.now(timezone.utc).isoformat()
                        update_fields["documents"] = [
                            {"id": str(uuid.uuid4()), "type": "id_card", "name": "CI Vasile Constantinescu.pdf", "url": "data:application/pdf;base64,JVBERi0xLjQK", "status": "pending", "uploaded_at": now_iso},
                            {"id": str(uuid.uuid4()), "type": "certification", "name": "Atestat ANRE electrician.jpg", "url": "https://via.placeholder.com/600x400.jpg?text=Atestat+ANRE", "status": "pending", "uploaded_at": now_iso},
                            {"id": str(uuid.uuid4()), "type": "insurance", "name": "Asigurare RCA.pdf", "url": "data:application/pdf;base64,JVBERi0xLjQK", "status": "pending", "uploaded_at": now_iso},
                        ]
            elif u["role"] == "client":
                update_fields["zone"] = existing.get("zone") or "Bucuresti-Sector1"
                if (existing.get("tokens") or 0) < 3000:
                    update_fields["tokens"] = 3500
            if update_fields:
                await db.users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            continue
        doc = {
            "email": u["email"],
            "password_hash": hash_password(u["password"]),
            "name": u["name"],
            "role": u["role"],
            "phone": u.get("phone", ""),
            "wallet_balance": 800.0 if u["role"] == "specialist" else (5000.0 if u["role"] == "client" else 0.0),
            "tokens": 3500 if u["role"] == "client" else 0,
            "rating": 4.9 if u["role"] == "specialist" and not u.get("_pending") else None,
            "reviews_count": 24 if u["role"] == "specialist" and not u.get("_pending") else 0,
            "verified": u["role"] == "specialist" and not u.get("_pending"),
            "tier": "VERIFIED" if u["role"] == "specialist" and not u.get("_pending") else None,
            "specialty": u.get("specialty"),
            "zone": "Bucuresti-Sector1" if u["role"] == "client" else None,
            "coverage_zones": ["Bucuresti-Sector1", "Bucuresti-Sector2"] if u["role"] == "specialist" else [],
            "service_categories": [u.get("specialty"), "interior_design"] if u["role"] == "specialist" and u.get("specialty") else [],
            "availability_status": "available" if u["role"] == "specialist" else None,
            "documents": [
                {"id": str(uuid.uuid4()), "type": "id_card", "name": "CI Vasile Constantinescu.pdf", "url": "data:application/pdf;base64,placeholder", "status": "pending", "uploaded_at": datetime.now(timezone.utc).isoformat()},
                {"id": str(uuid.uuid4()), "type": "certification", "name": "Atestat ANRE electrician.pdf", "url": "data:application/pdf;base64,placeholder", "status": "pending", "uploaded_at": datetime.now(timezone.utc).isoformat()},
            ] if u.get("_pending") else [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        res = await db.users.insert_one(doc)
        user_ids[u["email"]] = str(res.inserted_id)

    # Seed property for client
    client_id = user_ids.get("client@propmanage.io")
    if client_id:
        existing_prop = await db.properties.find_one({"owner_id": client_id})
        if not existing_prop:
            prop = {
                "name": "Skyline Loft A4",
                "address": "Str. Unirii 42, București",
                "type": "apartment",
                "surface": 92.0,
                "rooms": 3,
                "owner_id": client_id,
                "health_score": 75,
                "structure_health": 90,
                "utilities_health": 82,
                "documents_health": 100,
                "twin_unlocked": True,
                "wallet_unlocked": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            prop_res = await db.properties.insert_one(prop)
            prop_id = str(prop_res.inserted_id)

            spec_id = user_ids.get("specialist@propmanage.io")
            sample_requests = [
                {
                    "client_id": client_id, "client_name": "Andrei Popescu",
                    "property_id": prop_id, "property_name": "Skyline Loft A4",
                    "category": "hvac", "title": "Reparație Centrală Termică",
                    "description": "Centrala face zgomot ciudat și nu mai încălzește optim.",
                    "priority": "urgent", "budget_estimate": 450.0,
                    "status": "in_progress", "specialist_id": spec_id, "specialist_name": "Mihai Ionescu",
                    "escrow_amount": 450.0, "escrow_status": "held",
                    "created_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
                    "assigned_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
                    "started_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                },
                {
                    "client_id": client_id, "client_name": "Andrei Popescu",
                    "property_id": prop_id, "property_name": "Skyline Loft A4",
                    "category": "electric", "title": "Înlocuire prize bucătărie",
                    "description": "Două prize din bucătărie nu mai funcționează.",
                    "priority": "normal", "budget_estimate": 200.0,
                    "status": "open", "specialist_id": None, "specialist_name": None,
                    "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                },
                {
                    "client_id": client_id, "client_name": "Andrei Popescu",
                    "property_id": prop_id, "property_name": "Skyline Loft A4",
                    "category": "plumbing", "title": "Scurgere baie",
                    "description": "Scurgere detectată sub chiuvetă.",
                    "priority": "urgent", "budget_estimate": 350.0,
                    "status": "open",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
            for r in sample_requests:
                await db.requests.insert_one(r)

    # Seed sample Digital Twin APPROVED (so client has access to Interior Design flow)
    if client_id:
        prop_for_twin = await db.properties.find_one({"owner_id": client_id})
        if prop_for_twin:
            from bson import ObjectId  # local import to avoid top-level coupling
            prop_id_str = str(prop_for_twin["_id"])
            existing_twin = await db.twins.find_one({"property_id": prop_id_str})
            now_iso = datetime.now(timezone.utc).isoformat()
            twin_doc = {
                "property_id": prop_id_str,
                "status": "approved",
                "rooms": [
                    {"id": str(uuid.uuid4()), "name": "Living", "type": "living", "area": 32, "x": 50, "y": 50, "w": 220, "h": 180},
                    {"id": str(uuid.uuid4()), "name": "Dormitor", "type": "bedroom", "area": 16, "x": 280, "y": 50, "w": 160, "h": 130},
                    {"id": str(uuid.uuid4()), "name": "Bucătărie", "type": "kitchen", "area": 12, "x": 50, "y": 240, "w": 140, "h": 120},
                    {"id": str(uuid.uuid4()), "name": "Baie", "type": "bathroom", "area": 6, "x": 200, "y": 240, "w": 90, "h": 120},
                    {"id": str(uuid.uuid4()), "name": "Hol", "type": "hallway", "area": 8, "x": 300, "y": 200, "w": 140, "h": 160},
                ],
                "assets": [
                    {"id": str(uuid.uuid4()), "type": "boiler", "name": "Centrală termică", "x": 220, "y": 280, "condition": "good"},
                    {"id": str(uuid.uuid4()), "name": "Panou electric", "type": "electric_panel", "x": 330, "y": 220, "condition": "good"},
                    {"id": str(uuid.uuid4()), "name": "HVAC living", "type": "hvac", "x": 150, "y": 120, "condition": "fair"},
                ],
                "requested_at": now_iso,
                "validated_at": now_iso,
                "created_at": now_iso,
            }
            if existing_twin:
                # Self-heal: ensure demo twin remains approved (resilient to test data drift)
                if existing_twin.get("status") != "approved":
                    await db.twins.update_one(
                        {"_id": existing_twin["_id"]},
                        {"$set": {"status": "approved", "validated_at": now_iso}}
                    )
            else:
                await db.twins.insert_one(twin_doc)

    # Seed portfolio (idempotent)
    if await db.portfolio.count_documents({}) == 0:
        spec1 = await db.users.find_one({"email": "specialist@propmanage.io"})
        spec2 = await db.users.find_one({"email": "specialist2@propmanage.io"})
        if spec1 and spec2:
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.portfolio.insert_many([
                {"specialist_id": str(spec1["_id"]), "specialist_name": spec1.get("name"), "title": "Sistem HVAC Premium - Vila Pipera",
                 "description": "Instalare sistem complet de climatizare cu 4 unități interioare, ventilație controlată și recuperator de căldură.",
                 "category": "hvac", "style": None, "cover_image": "https://picsum.photos/seed/portfolio-hvac-pipera/800/600",
                 "gallery": ["https://picsum.photos/seed/portfolio-hvac-pipera-1/800/600"], "location": "Pipera", "surface": 220.0, "created_at": now_iso},
                {"specialist_id": str(spec1["_id"]), "specialist_name": spec1.get("name"), "title": "Renovare baie loft industrial",
                 "description": "Refacere completă instalație sanitară + climatizare locală pentru o baie cu duș italian și caldă.",
                 "category": "hvac", "style": "industrial", "cover_image": "https://picsum.photos/seed/portfolio-bath-industrial/800/600",
                 "gallery": [], "location": "București Centru", "surface": 18.0, "created_at": now_iso},
                {"specialist_id": str(spec2["_id"]), "specialist_name": spec2.get("name"), "title": "Bucătărie modernă deschisă",
                 "description": "Refacere completă rețea sanitară + instalare insulă centrală cu chiuvetă și mașină de spălat vase.",
                 "category": "plumbing", "style": "modern", "cover_image": "https://picsum.photos/seed/portfolio-kitchen-modern/800/600",
                 "gallery": ["https://picsum.photos/seed/portfolio-kitchen-modern-1/800/600"], "location": "Cluj-Napoca", "surface": 32.0, "created_at": now_iso},
            ])

    # Seed regions — comprehensive Romanian list
    from romania_zones import ROMANIAN_ZONES
    for country, city, zone in ROMANIAN_ZONES:
        existing = await db.regions.find_one({"country": country, "city": city, "zone": zone})
        if not existing:
            await db.regions.insert_one({
                "country": country, "city": city, "zone": zone,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    # Write test credentials
    creds_path = Path(__file__).resolve().parent.parent / "memory" / "test_credentials.md"
    creds_path.parent.mkdir(exist_ok=True)
    creds_path.write_text("""# PropManage Test Credentials

## Demo Accounts (Pre-seeded, idempotent)

| Role | Email | Password |
|------|-------|----------|
| Client | client@propmanage.io | Client123! |
| Specialist (HVAC, verified) | specialist@propmanage.io | Spec123! |
| Specialist (Plumbing, verified) | specialist2@propmanage.io | Spec123! |
| Admin | admin@propmanage.io | Admin123! |
| Operator | operator@propmanage.io | Op123! |

## Auth Endpoints
- POST /api/auth/login - Body: {email, password}
- POST /api/auth/register - Body: {email, password, name, role}
- POST /api/auth/logout
- GET /api/auth/me

## Test Flow
1. Login as client → see properties + requests
2. Login as specialist → see open requests, accept lead (pays 45 RON)
3. Login as admin → see stats, verify specialists
4. Login as operator → validate maintenance logs

Client starts with 5000 RON wallet + 250 tokens
Specialists start with 800 RON wallet, 4.9 rating, 24 reviews, VERIFIED tier
""")
    logger.info("Seed complete. Demo accounts ready.")
