"""CIP-B — Price Observatory service layer.

Collection: price_observations
  {id, category (legacy), service, city, unit, price_min, price_med, price_max,
   experience_level (beginner|mid|expert), source (seed|admin_manual|csv_import),
   notes, created_by, created_at}

Trust grading la agregare: A = ≥3 observații, B = 2, C = 1.
`preliminary` = toate observațiile din combo provin din seed (date orientative).
"""
import logging
import uuid
from datetime import datetime, timezone

from db import db

logger = logging.getLogger("propmanage.prices")

CITIES = [("București", 1.0), ("Cluj-Napoca", 0.95), ("Timișoara", 0.85)]
LEVELS = [("mid", 1.0), ("expert", 1.35)]
UNITS = {"mp", "ml", "buc", "ora", "proiect", "zi"}
EXPERIENCE_LEVELS = ["beginner", "mid", "expert"]

# (category, service, unit, min, med, max) — prețuri orientative piață RO (nivel mid, București)
PRICE_BASE = [
    ("zugravit", "Vopsea lavabilă (2 straturi)", "mp", 12, 18, 28),
    ("zugravit", "Glet & șlefuire", "mp", 14, 22, 35),
    ("parchet", "Montaj parchet laminat", "mp", 18, 25, 40),
    ("parchet", "Raschetare & paluxare", "mp", 25, 38, 55),
    ("faianta", "Montaj gresie / faianță", "mp", 60, 85, 130),
    ("faianta", "Placare piatră naturală", "mp", 120, 170, 260),
    ("handyman", "Intervenție handyman", "ora", 60, 90, 140),
    ("handyman", "Asamblare mobilier", "buc", 80, 150, 300),
    ("gips_carton", "Perete gips-carton (simplu placat)", "mp", 55, 75, 110),
    ("gips_carton", "Tavan fals cu scafe", "mp", 70, 95, 150),
    ("hvac", "Montaj AC split (9-12k BTU)", "buc", 350, 500, 800),
    ("hvac", "Montaj centrală termică", "buc", 800, 1200, 2000),
    ("electric", "Instalație electrică completă", "mp", 45, 65, 100),
    ("electric", "Înlocuire tablou electric", "buc", 400, 650, 1100),
    ("plumbing", "Instalație sanitară baie completă", "proiect", 2500, 4000, 7000),
    ("plumbing", "Montaj obiect sanitar", "buc", 120, 200, 350),
    ("interior_design", "Proiect design interior", "mp", 40, 70, 150),
    ("constructii", "Zidărie cărămidă / BCA", "mp", 70, 100, 160),
    ("acoperisuri", "Montaj țiglă metalică", "mp", 45, 65, 100),
    ("fatade_termoizolatii", "Termosistem polistiren 10cm", "mp", 90, 130, 190),
    ("tamplarie", "Montaj fereastră PVC", "buc", 150, 250, 450),
    ("amenajari_exterioare", "Montaj pavele", "mp", 45, 70, 110),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def seed_price_observations() -> dict:
    """Idempotent — ~132 observații orientative (22 servicii × 3 orașe × 2 niveluri)."""
    existing = await db.price_observations.count_documents({})
    if existing > 0:
        return {"seeded": False, "rows": existing}
    docs = []
    for category, service, unit, pmin, pmed, pmax in PRICE_BASE:
        for city, cm in CITIES:
            for level, lm in LEVELS:
                k = cm * lm
                docs.append({
                    "id": uuid.uuid4().hex,
                    "category": category,
                    "service": service,
                    "city": city,
                    "unit": unit,
                    "price_min": round(pmin * k),
                    "price_med": round(pmed * k),
                    "price_max": round(pmax * k),
                    "experience_level": level,
                    "source": "seed",
                    "notes": "Date orientative de piață (preliminar)",
                    "created_by": "seed",
                    "created_at": _now(),
                })
    await db.price_observations.insert_many([{**d} for d in docs])
    logger.info(f"[prices] seeded {len(docs)} observations")
    return {"seeded": True, "rows": len(docs)}


def _trust_grade(n: int) -> str:
    return "A" if n >= 3 else ("B" if n == 2 else "C")


async def aggregate_prices(category: str = None, city: str = None) -> list:
    """Agregare per (category, service, city, unit, experience_level)."""
    match = {}
    if category and category != "all":
        match["category"] = category
    if city and city != "all":
        match["city"] = city
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"category": "$category", "service": "$service", "city": "$city",
                    "unit": "$unit", "level": "$experience_level"},
            "price_min": {"$avg": "$price_min"},
            "price_med": {"$avg": "$price_med"},
            "price_max": {"$avg": "$price_max"},
            "observations": {"$sum": 1},
            "sources": {"$addToSet": "$source"},
        }},
        {"$sort": {"_id.category": 1, "_id.service": 1, "_id.city": 1, "_id.level": 1}},
    ]
    out = []
    async for row in db.price_observations.aggregate(pipeline):
        g = row["_id"]
        sources = row.get("sources") or []
        out.append({
            "category": g["category"],
            "service": g["service"],
            "city": g["city"],
            "unit": g["unit"],
            "experience_level": g["level"],
            "price_min": round(row["price_min"] or 0),
            "price_med": round(row["price_med"] or 0),
            "price_max": round(row["price_max"] or 0),
            "observations": row["observations"],
            "trust_grade": _trust_grade(row["observations"]),
            "preliminary": sources == ["seed"],
        })
    return out
