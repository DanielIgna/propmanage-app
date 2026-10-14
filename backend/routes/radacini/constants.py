"""Enumerări Rădăcini — sursa de adevăr pentru GET /meta și pentru validări."""

INTERESTS = [
    {"id": "grow", "label": "Vreau să cultiv"},
    {"id": "consume", "label": "Vreau produse locale"},
    {"id": "land", "label": "Am teren"},
    {"id": "sell", "label": "Vând produse"},
    {"id": "exchange", "label": "Schimb produse"},
    {"id": "community", "label": "Comunitate și evenimente"},
]

# `requestable`: modelele `sale` și `joint_project` pot fi afișate în ofertele terenurilor, dar cererile pe ele
# sunt blocate până la avizul juridic (POST /parcels/{id}/requests -> 409).
OFFER_MODELS = [
    {"id": "rent", "label": "Arendă / închiriere", "requestable": True},
    {"id": "harvest_share", "label": "Cultivare la parte din recoltă", "requestable": True},
    {"id": "fixed_fee", "label": "Cultivare contra sumă fixă", "requestable": True},
    {"id": "mixed", "label": "Model mixt", "requestable": True},
    {"id": "sale", "label": "Vânzare", "requestable": False},
    {"id": "joint_project", "label": "Proiect comun", "requestable": False},
]
LEGAL_GATE_MESSAGE = "Acest model necesită aviz juridic și nu e încă disponibil în platformă."

WATER_SOURCES = [
    {"id": "well", "label": "Fântână"},
    {"id": "river", "label": "Râu / pârâu"},
    {"id": "network", "label": "Rețea"},
    {"id": "irrigation", "label": "Sistem de irigații"},
    {"id": "none", "label": "Fără sursă cunoscută"},
]

LOCALITIES = [
    "Cluj-Napoca", "Florești", "Apahida", "Baciu", "Feleacu", "Gilău", "Jucu", "Bonțida",
    "Gherla", "Dej", "Turda", "Câmpia Turzii", "Huedin", "Aghireșu", "Sânpaul", "Chinteni",
    "Vultureni", "Ciurila", "Tureni", "Mociu",
]

COUNTY = "Cluj"

# Centre aproximative (lat, lng) ale localităților din județul Cluj: folosite doar la filtrul pe rază din piață
# (`GET /listings?near_locality=&radius_km=`), nu pentru locații exacte.
LOCALITY_CENTERS = {
    "Cluj-Napoca": (46.7712, 23.6236),
    "Florești": (46.7440, 23.4890),
    "Apahida": (46.8100, 23.7490),
    "Baciu": (46.7930, 23.5230),
    "Feleacu": (46.7250, 23.5900),
    "Gilău": (46.7547, 23.3719),
    "Jucu": (46.8850, 23.6750),
    "Bonțida": (46.9344, 23.8183),
    "Gherla": (47.0261, 23.9078),
    "Dej": (47.1450, 23.8800),
    "Turda": (46.5667, 23.7833),
    "Câmpia Turzii": (46.5469, 23.8800),
    "Huedin": (46.8683, 23.0356),
    "Aghireșu": (46.9167, 23.2500),
    "Sânpaul": (46.8667, 23.6667),
    "Chinteni": (46.8570, 23.5240),
    "Vultureni": (46.8500, 23.4300),
    "Ciurila": (46.6750, 23.5000),
    "Tureni": (46.5800, 23.6600),
    "Mociu": (46.7700, 24.0600),
}

INTEREST_IDS = {i["id"] for i in INTERESTS}
OFFER_MODEL_IDS = {m["id"] for m in OFFER_MODELS}
REQUESTABLE_MODEL_IDS = {m["id"] for m in OFFER_MODELS if m["requestable"]}
WATER_SOURCE_IDS = {w["id"] for w in WATER_SOURCES}

CROP_FAMILIES = [
    {"id": "solanacee", "label": "Solanacee"},
    {"id": "cucurbitacee", "label": "Cucurbitacee"},
    {"id": "brasicacee", "label": "Brasicacee"},
    {"id": "liliacee", "label": "Liliacee"},
    {"id": "leguminoase", "label": "Leguminoase"},
    {"id": "umbelifere", "label": "Umbelifere"},
    {"id": "cereale", "label": "Cereale"},
    {"id": "asteracee", "label": "Asteracee"},
    {"id": "rozacee", "label": "Rozacee"},
    {"id": "other", "label": "Altele"},
]

CROPS = [
    {"id": "rosii", "label": "Roșii", "family": "solanacee"},
    {"id": "ardei", "label": "Ardei", "family": "solanacee"},
    {"id": "vinete", "label": "Vinete", "family": "solanacee"},
    {"id": "cartofi", "label": "Cartofi", "family": "solanacee"},
    {"id": "castraveti", "label": "Castraveți", "family": "cucurbitacee"},
    {"id": "dovlecei", "label": "Dovlecei", "family": "cucurbitacee"},
    {"id": "dovleac", "label": "Dovleac", "family": "cucurbitacee"},
    {"id": "varza", "label": "Varză", "family": "brasicacee"},
    {"id": "ridichi", "label": "Ridichi", "family": "brasicacee"},
    {"id": "ceapa", "label": "Ceapă", "family": "liliacee"},
    {"id": "usturoi", "label": "Usturoi", "family": "liliacee"},
    {"id": "morcovi", "label": "Morcovi", "family": "umbelifere"},
    {"id": "fasole", "label": "Fasole", "family": "leguminoase"},
    {"id": "mazare", "label": "Mazăre", "family": "leguminoase"},
    {"id": "porumb", "label": "Porumb", "family": "cereale"},
    {"id": "grau", "label": "Grâu", "family": "cereale"},
    {"id": "salata", "label": "Salată", "family": "asteracee"},
    {"id": "capsuni", "label": "Căpșuni", "family": "rozacee"},
]

CROP_STATUSES = [
    {"id": "planned", "label": "Planificată"},
    {"id": "sown", "label": "Semănată"},
    {"id": "growing", "label": "În creștere"},
    {"id": "harvested", "label": "Recoltată"},
]

ACTIVITY_TYPES = [
    {"id": "planting", "label": "Plantare / semănat"},
    {"id": "maintenance", "label": "Întreținere"},
    {"id": "irrigation", "label": "Irigare"},
    {"id": "harvest", "label": "Recoltare"},
    {"id": "work_day", "label": "Zi de lucru în comun"},
    {"id": "other", "label": "Altceva"},
]

CONTRIBUTION_KINDS = [
    {"id": "labor_hours", "label": "Ore de muncă"},
    {"id": "materials", "label": "Materiale"},
    {"id": "money", "label": "Sumă cheltuită (în afara platformei)"},
    {"id": "tools", "label": "Unelte"},
    {"id": "land", "label": "Teren"},
]

LISTING_CATEGORIES = [
    {"id": "legume", "label": "Legume"},
    {"id": "fructe", "label": "Fructe"},
    {"id": "cereale", "label": "Cereale"},
    {"id": "lactate", "label": "Lactate"},
    {"id": "ouă", "label": "Ouă"},
    {"id": "miere", "label": "Miere"},
    {"id": "conserve", "label": "Conserve"},
    {"id": "altele", "label": "Altele"},
]

LISTING_UNITS = [
    {"id": "kg", "label": "kg"},
    {"id": "buc", "label": "buc"},
    {"id": "legătură", "label": "legătură"},
    {"id": "borcan", "label": "borcan"},
    {"id": "litru", "label": "litru"},
]

LISTING_MODES = [
    {"id": "sale", "label": "Vânzare"},
    {"id": "exchange", "label": "Schimb"},
    {"id": "both", "label": "Vânzare sau schimb"},
]

RESERVATION_MODES = [
    {"id": "cash_on_pickup", "label": "Plată la ridicare"},
    {"id": "exchange", "label": "Schimb"},
]

CROP_IDS = {c["id"] for c in CROPS}
CROP_STATUS_IDS = {c["id"] for c in CROP_STATUSES}
ACTIVITY_TYPE_IDS = {a["id"] for a in ACTIVITY_TYPES}
CONTRIBUTION_KIND_IDS = {k["id"] for k in CONTRIBUTION_KINDS}
LISTING_CATEGORY_IDS = {c["id"] for c in LISTING_CATEGORIES}
LISTING_UNIT_IDS = {u["id"] for u in LISTING_UNITS}
LISTING_MODE_IDS = {m["id"] for m in LISTING_MODES}
RESERVATION_MODE_IDS = {m["id"] for m in RESERVATION_MODES}
FAMILY_LABELS = {f["id"]: f["label"] for f in CROP_FAMILIES}

# Limite numerice partajate de validări (S4) și expuse în GET /meta -> limits.
MAX_HARVEST_KG = 1_000_000
MAX_LISTING_QTY = 1_000_000
MAX_LISTING_PRICE_RON = 10_000
QUANTITY_DECIMALS = 3  # cantitățile se rotunjesc la 0,001 înainte de validare

LIMITS = {
    "max_harvest_kg": MAX_HARVEST_KG,
    "max_listing_quantity": MAX_LISTING_QTY,
    "max_listing_price_ron": MAX_LISTING_PRICE_RON,
    "quantity_decimals": QUANTITY_DECIMALS,
}

META = {
    "interests": INTERESTS,
    "offer_models": OFFER_MODELS,
    "water_sources": WATER_SOURCES,
    "localities": LOCALITIES,
    "crops": CROPS,
    "crop_families": CROP_FAMILIES,
    "crop_statuses": CROP_STATUSES,
    "activity_types": ACTIVITY_TYPES,
    "contribution_kinds": CONTRIBUTION_KINDS,
    "listing_categories": LISTING_CATEGORIES,
    "listing_units": LISTING_UNITS,
    "listing_modes": LISTING_MODES,
    "reservation_modes": RESERVATION_MODES,
    "limits": LIMITS,
}

LEGAL_NOTICE = (
    "Acest acord consemnează înțelegerea dintre părți în platforma Rădăcini. "
    "Nu înlocuiește contractul de arendă/închiriere în forma cerută de lege și nici "
    "înregistrarea acestuia la primărie, unde este cazul."
)
