"""Pydantic models + literals + constants used across the app."""
from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["client", "specialist", "admin", "operator"]

ALLOWED_SPECIALTIES = {
    "hvac", "electric", "plumbing", "interior_design", "carpentry",
    "painting", "cleaning", "appliance_repair", "gardening", "other",
    # New: interior finishing specialties (managed by interior designer projects)
    "parchet", "zugravit", "faianta", "handyman", "gips_carton",
}

# Interior design constants
DESIGN_CONCEPT_PRICE_PER_ROOM = 2200.0  # RON / room (fixed)
DESIGN_MAX_TOKEN_DISCOUNT_PCT = 50      # tokens can cover at most 50% of price


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    role: Role = "client"
    phone: Optional[str] = None
    specialty: Optional[str] = None
    service_categories: Optional[List[str]] = None
    coverage_zones: Optional[List[str]] = None
    zone: Optional[str] = None
    referrer_id: Optional[str] = None
    # GDPR consent — terms + privacy MUST be True for register to succeed
    terms_accepted: Optional[bool] = False
    privacy_policy_accepted: Optional[bool] = False
    marketing_consent: Optional[bool] = False


class ConsentUpdateIn(BaseModel):
    marketing_consent: Optional[bool] = None
    functional_cookies_accepted: Optional[bool] = None
    analytics_cookies_accepted: Optional[bool] = None
    marketing_cookies_accepted: Optional[bool] = None
    # User can re-accept terms/privacy (e.g., after policy update)
    terms_accepted: Optional[bool] = None
    privacy_policy_accepted: Optional[bool] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TotpVerifyIn(BaseModel):
    code: str


class PropertyIn(BaseModel):
    name: str
    address: str
    type: str
    surface: float
    rooms: int


class PropertyUpdateIn(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    type: Optional[str] = None
    surface: Optional[float] = None
    rooms: Optional[int] = None


class RegionIn(BaseModel):
    country: str
    city: str
    zone: str


class SpecialistZonesIn(BaseModel):
    zones: List[str]
    categories: List[str]


class AvailabilityIn(BaseModel):
    status: Literal["available", "busy", "offline"]
    available_hours: Optional[Dict] = None


class ServiceAvailabilityIn(BaseModel):
    region_id: str
    service: str
    state: Literal["active", "inactive", "limited", "premium_only"]
    min_specialists: int = 1


class RequestIn(BaseModel):
    property_id: str
    category: str
    title: str
    description: str
    priority: Literal["low", "normal", "medium", "high", "urgent"] = "normal"
    budget_estimate: Optional[float] = None
    county: Optional[str] = None
    photos: Optional[List[str]] = None
    taxonomy_node_id: Optional[str] = None
    subcategory: Optional[str] = None

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, v):
        """Normalize legacy + UI variants: 'medium' → 'normal' for backward compat."""
        if v is None:
            return "normal"
        v = str(v).lower().strip()
        if v in ("medium", "med"):
            return "normal"
        return v


class OfferIn(BaseModel):
    request_id: str
    price: float
    eta_hours: int
    message: str


class ReviewIn(BaseModel):
    # job_id kept optional for backward compatibility; the canonical id is the URL path param.
    job_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    # GBOS P0.3 — Trust Marketplace (Rebook > stele)
    would_hire_again: Optional[Literal["yes", "no", "not_sure"]] = None
    would_recommend: Optional[bool] = None


class DocumentIn(BaseModel):
    type: Literal["id_card", "insurance", "certification", "company_cui", "other"]
    name: str
    url: str


class DocumentReviewIn(BaseModel):
    status: Literal["approved", "rejected"]
    reason: Optional[str] = None


class SpecialistRejectIn(BaseModel):
    reason: str = Field(min_length=3)


class DisputeOpenIn(BaseModel):
    reason: str = Field(min_length=10)
    evidence_urls: Optional[List[str]] = None


class DisputeResolveIn(BaseModel):
    resolution: Literal["refund_client", "pay_specialist", "split"]
    client_pct: Optional[int] = None
    notes: Optional[str] = None


# ============= DIGITAL TWIN MODELS =============
class TwinRoom(BaseModel):
    id: str
    name: str
    type: Literal["living", "bedroom", "kitchen", "bathroom", "hallway", "balcony", "office", "storage", "other"]
    area: float = 0
    x: float = 0
    y: float = 0
    w: float = 100
    h: float = 100


class TwinAsset(BaseModel):
    id: str
    type: Literal["hvac", "boiler", "electric_panel", "water_meter", "gas_meter", "appliance", "lighting", "plumbing", "other"]
    name: str
    room_id: Optional[str] = None
    # P1 — identitate canonică unică: leagă poziționarea 2D de activul din `property_assets` (SSOT).
    # Optional & non-destructiv: ONE ASSET IDENTITY + MULTIPLE CONTEXTS.
    asset_ref: Optional[str] = None
    x: float = 0
    y: float = 0
    condition: Literal["good", "fair", "needs_service", "critical"] = "good"
    last_service_date: Optional[str] = None
    notes: Optional[str] = None


class TwinUpsertIn(BaseModel):
    rooms: List[TwinRoom] = []
    assets: List[TwinAsset] = []
    model_url: Optional[str] = None
    notes: Optional[str] = None


class TwinValidateIn(BaseModel):
    action: Literal["approve", "request_revision"]
    notes: Optional[str] = None


# ============= INTERIOR DESIGN =============
class DesignConceptIn(BaseModel):
    property_id: str
    room_ids: List[str] = Field(min_length=1)
    tokens_to_use: int = Field(ge=0, default=0)
    style_preference: Optional[str] = None
    notes: Optional[str] = None


class DesignPhaseQuoteIn(BaseModel):
    request_id: str
    phase_name: str = Field(min_length=3)
    description: str
    price: float = Field(gt=0)
    estimated_days: int = Field(ge=1)


class DesignPhaseAcceptIn(BaseModel):
    quote_id: str


class PortfolioItemIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    style: Optional[str] = None
    category: Literal["interior_design", "renovation", "hvac", "electric", "plumbing", "carpentry", "other"] = "interior_design"
    cover_image: str
    gallery: List[str] = Field(default_factory=list, max_length=12)
    completion_date: Optional[str] = None
    location: Optional[str] = None
    surface: Optional[float] = None
    project_type: Optional[str] = Field(default=None, max_length=60)
    services: Optional[List[str]] = Field(default=None, max_length=20)
    role: Optional[str] = Field(default=None, max_length=60)
    budget_range: Optional[str] = Field(default=None, max_length=40)
    tags: Optional[List[str]] = Field(default=None, max_length=25)
    before_image: Optional[str] = None
    after_image: Optional[str] = None
    video_url: Optional[str] = Field(default=None, max_length=300)
    tour_url: Optional[str] = Field(default=None, max_length=300)
    awards: Optional[str] = Field(default=None, max_length=200)
    client_review: Optional[str] = Field(default=None, max_length=1000)
    is_public: bool = True
