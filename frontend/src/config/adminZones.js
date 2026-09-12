// ============================================================================
// ADMIN ZONES REGISTRY — separarea completă Business vs Infrastructure
// ----------------------------------------------------------------------------
// REGULĂ DE ARHITECTURĂ (obligatorie pentru orice modul admin viitor):
//   Orice secțiune nouă din NAV_SECTIONS (AdminLayoutMetronic.jsx) TREBUIE să
//   declare `zone: "business"` sau `zone: "infrastructure"`.
//   NU se creează module mixte. NU se amestecă meniurile între zone.
// ============================================================================

export const ADMIN_ZONES = {
  business: {
    id: "business",
    label: "Business Administration",
    short: "Business",
    description: "Utilizatori · Marketplace · Financiar · Marketing · Suport",
    accent: "blue",
  },
  infrastructure: {
    id: "infrastructure",
    label: "Infrastructure & Development",
    short: "Infra & Dev",
    description: "Sistem · Security · Monitoring · AI Lab · Development",
    accent: "violet",
  },
};

// Roluri pregătite pentru activare ulterioară (enforcement: "prepared").
// Fiecare rol primește acces doar la zona/secțiunile necesare.
// Oglindit în backend: /app/backend/routes/admin_zones.py
export const ADMIN_ZONE_ROLES = [
  { id: "business_administrator", label: "Business Administrator", zones: ["business"] },
  { id: "operations_manager", label: "Operations Manager", zones: ["business"], sections: ["operations", "users", "properties"] },
  { id: "finance_manager", label: "Finance Manager", zones: ["business"], sections: ["finance", "analytics"] },
  { id: "marketplace_manager", label: "Marketplace Manager", zones: ["business"], sections: ["city_partners", "properties"] },
  { id: "support_manager", label: "Support Manager", zones: ["business"], sections: ["support_compliance", "users"] },
  { id: "content_manager", label: "Content Manager", zones: ["business"], sections: ["content", "marketing_growth"] },
  { id: "infrastructure_administrator", label: "Infrastructure Administrator", zones: ["infrastructure"] },
  { id: "developer", label: "Developer", zones: ["infrastructure"], sections: ["infra_dev", "ai_lab"] },
  { id: "devops", label: "DevOps", zones: ["infrastructure"], sections: ["infra_system", "infra_security", "infra_dev"] },
  { id: "system_administrator", label: "System Administrator", zones: ["infrastructure"] },
  { id: "super_admin", label: "Super Admin", zones: ["business", "infrastructure"] },
];

// ── Zona activă (persistată per browser) ────────────────────────────────────
const ZONE_KEY = "pm_admin_zone";
export const ZONE_EVENT = "pm:admin-zone-changed";

export const getStoredZone = () => {
  const z = localStorage.getItem(ZONE_KEY);
  return z === "infrastructure" ? "infrastructure" : "business";
};

export const setStoredZone = (zone) => {
  localStorage.setItem(ZONE_KEY, zone);
  window.dispatchEvent(new CustomEvent(ZONE_EVENT, { detail: { zone } }));
};
