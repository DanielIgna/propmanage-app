"""SEO price pages — „Cât costă X în {oraș} în {an}" (Sprint A, aprobat de user).

Construiește pagini publice per categorie din Price Observatory (CIP-B).
Sursa datelor: construction.prices.aggregate_prices.
"""
from datetime import datetime, timezone

from construction.prices import aggregate_prices

# slug URL → meta categorie (legacy category din price_observations)
PRICE_SEO = {
    "zugravit":               {"category": "zugravit",             "name": "Zugrăvit & vopsit",              "noun": "zugrăvitul"},
    "montaj-parchet":         {"category": "parchet",              "name": "Montaj & recondiționare parchet", "noun": "montajul de parchet"},
    "gresie-faianta":         {"category": "faianta",              "name": "Montaj gresie & faianță",         "noun": "montajul de gresie și faianță"},
    "handyman":               {"category": "handyman",             "name": "Servicii handyman",               "noun": "un handyman"},
    "gips-carton":            {"category": "gips_carton",          "name": "Gips-carton & compartimentări",   "noun": "lucrările de gips-carton"},
    "montaj-aer-conditionat": {"category": "hvac",                 "name": "Climatizare & HVAC",              "noun": "montajul unui aparat de aer condiționat"},
    "instalatii-electrice":   {"category": "electric",             "name": "Instalații electrice",            "noun": "instalațiile electrice"},
    "instalatii-sanitare":    {"category": "plumbing",             "name": "Instalații sanitare",             "noun": "instalațiile sanitare"},
    "design-interior":        {"category": "interior_design",      "name": "Design interior",                 "noun": "un proiect de design interior"},
    "constructii-zidarie":    {"category": "constructii",          "name": "Construcții & zidărie",           "noun": "lucrările de zidărie"},
    "acoperisuri":            {"category": "acoperisuri",          "name": "Acoperișuri",                     "noun": "un acoperiș nou"},
    "termoizolatii-fatade":   {"category": "fatade_termoizolatii", "name": "Termoizolații & fațade",          "noun": "termoizolarea fațadei"},
    "tamplarie-pvc":          {"category": "tamplarie",            "name": "Tâmplărie & ferestre",            "noun": "montajul tâmplăriei PVC"},
    "amenajari-exterioare":   {"category": "amenajari_exterioare", "name": "Amenajări exterioare",            "noun": "amenajările exterioare"},
}

DISCLAIMER = ("Prețuri orientative bazate pe observații de piață. Cele marcate „preliminar” provin "
              "din cercetare de piață, nu din tranzacții încheiate pe platformă. Oferta finală "
              "depinde de complexitatea lucrării și se stabilește direct cu specialistul.")


def _year() -> int:
    return datetime.now(timezone.utc).year


def _group_by_service(rows: list) -> list:
    """(service, unit) → {mid: {...}, expert: {...}}"""
    grouped = {}
    for r in rows:
        key = (r["service"], r["unit"])
        g = grouped.setdefault(key, {"service": r["service"], "unit": r["unit"], "levels": {}, "preliminary": True})
        g["levels"][r["experience_level"]] = {
            "price_min": r["price_min"], "price_med": r["price_med"], "price_max": r["price_max"],
            "trust_grade": r["trust_grade"],
        }
        if not r["preliminary"]:
            g["preliminary"] = False
    return list(grouped.values())


async def list_seo_pages() -> list:
    """Pentru pagina index /preturi — fiecare categorie cu interval de preț preview."""
    all_rows = await aggregate_prices()
    by_cat = {}
    for r in all_rows:
        by_cat.setdefault(r["category"], []).append(r)
    out = []
    for slug, meta in PRICE_SEO.items():
        rows = by_cat.get(meta["category"], [])
        if not rows:
            continue
        mids = [r for r in rows if r["experience_level"] == "mid"] or rows
        out.append({
            "slug": slug,
            "name": meta["name"],
            "noun": meta["noun"],
            "price_from": min(r["price_min"] for r in mids),
            "price_to": max(r["price_max"] for r in rows),
            "unit_sample": mids[0]["unit"],
            "services_count": len({r["service"] for r in rows}),
            "preliminary": all(r["preliminary"] for r in rows),
        })
    return out


async def build_seo_page(slug: str, city: str = None) -> dict | None:
    meta = PRICE_SEO.get(slug)
    if not meta:
        return None
    rows = await aggregate_prices(meta["category"])
    if not rows:
        return None
    year = _year()
    cities = sorted({r["city"] for r in rows})
    default_city = city if city in cities else ("București" if "București" in cities else cities[0])
    prices_by_city = {c: _group_by_service([r for r in rows if r["city"] == c]) for c in cities}

    # FAQ pentru schema FAQPage (orașul implicit)
    dc_rows = [r for r in rows if r["city"] == default_city]
    gmin = min(r["price_min"] for r in dc_rows)
    gmax = max(r["price_max"] for r in dc_rows)
    top = dc_rows[0]
    faq = [
        {"q": f"Cât costă {meta['noun']} în {default_city} în {year}?",
         "a": f"Prețurile orientative pentru {meta['name'].lower()} în {default_city} variază între {gmin} și {gmax} lei, "
              f"în funcție de serviciu și de nivelul de experiență al specialistului. De exemplu, {top['service']} "
              f"costă în medie {top['price_med']} lei/{top['unit']}."},
        {"q": "De ce diferă prețurile între specialiști?",
         "a": "Prețul depinde de experiența specialistului, complexitatea lucrării, materialele folosite și zona. "
              "Un specialist expert poate costa cu 30-40% mai mult, dar oferă garanții și finisaje superioare."},
        {"q": "Cum primesc o ofertă exactă pentru lucrarea mea?",
         "a": "Creezi gratuit o cerere pe PropManage cu detaliile lucrării și primești oferte concrete de la "
              "specialiști verificați din zona ta, cu plată protejată prin escrow."},
        {"q": "Sunt aceste prețuri garantate?",
         "a": "Nu — sunt prețuri orientative de piață, actualizate periodic. Oferta finală se stabilește direct "
              "cu specialistul, după evaluarea lucrării."},
    ]
    related = [{"slug": s, "name": m["name"]} for s, m in PRICE_SEO.items() if s != slug][:6]
    return {
        "slug": slug,
        "name": meta["name"],
        "noun": meta["noun"],
        "year": year,
        "title": f"Cât costă {meta['noun']} în {default_city} în {year}? Prețuri orientative",
        "description": f"Prețuri orientative {year} pentru {meta['name'].lower()}: între {gmin} și {gmax} lei în "
                       f"{default_city}. Compară niveluri de experiență și primește oferte reale de la specialiști verificați.",
        "cities": cities,
        "default_city": default_city,
        "prices_by_city": prices_by_city,
        "faq": faq,
        "related": related,
        "disclaimer": DISCLAIMER,
    }
