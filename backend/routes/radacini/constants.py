"""Enumerări Rădăcini — sursa de adevăr pentru GET /meta și pentru validări."""

INTERESTS = [
    {"id": "grow", "label": "Vreau să cultiv"},
    {"id": "consume", "label": "Vreau produse locale"},
    {"id": "land", "label": "Am teren"},
    {"id": "sell", "label": "Vând produse"},
    {"id": "exchange", "label": "Schimb produse"},
    {"id": "community", "label": "Comunitate și evenimente"},
]

OFFER_MODELS = [
    {"id": "rent", "label": "Arendă / închiriere"},
    {"id": "harvest_share", "label": "Cultivare la parte din recoltă"},
    {"id": "fixed_fee", "label": "Cultivare contra sumă fixă"},
    {"id": "mixed", "label": "Model mixt"},
    {"id": "sale", "label": "Vânzare"},
    {"id": "joint_project", "label": "Proiect comun"},
]

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

INTEREST_IDS = {i["id"] for i in INTERESTS}
OFFER_MODEL_IDS = {m["id"] for m in OFFER_MODELS}
WATER_SOURCE_IDS = {w["id"] for w in WATER_SOURCES}

META = {
    "interests": INTERESTS,
    "offer_models": OFFER_MODELS,
    "water_sources": WATER_SOURCES,
    "localities": LOCALITIES,
}
