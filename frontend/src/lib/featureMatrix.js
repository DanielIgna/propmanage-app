// Feature matrix — pure rules engine.
// Returns "available" | "locked" | "hidden" given user state + feature key.
// Keep this file dependency-free (no React, no axios).

export const FEATURES = {
  // SPECIALIST features
  "spec.dashboard": { requires: { roles: ["specialist"] } },
  "spec.profile": { requires: { roles: ["specialist"] } },
  "spec.verification": { requires: { roles: ["specialist"] } },
  "spec.documents": { requires: { roles: ["specialist"] } },
  "spec.requests_received": { requires: { roles: ["specialist"] } },
  "spec.messages": { requires: { roles: ["specialist"] } },
  // Intermediate
  "spec.statistics": { requires: { roles: ["specialist"], verified: true } },
  "spec.offers": { requires: { roles: ["specialist"], verified: true } },
  "spec.marketing": { requires: { roles: ["specialist"], maturity: ["intermediate", "advanced"] } },
  // Advanced
  "spec.automations": { requires: { roles: ["specialist"], maturity: ["advanced"] } },
  "spec.ai_suggestions": { requires: { roles: ["specialist"], maturity: ["advanced"] } },
  "spec.financial_analytics": { requires: { roles: ["specialist"], maturity: ["advanced"] } },

  // CLIENT features
  "client.dashboard": { requires: { roles: ["client"] } },
  "client.properties": { requires: { roles: ["client"] } },
  "client.requests": { requires: { roles: ["client"] } },
  "client.wallet": { requires: { roles: ["client"] } },
  "client.house_health": { requires: { roles: ["client"], hh_subscription: "active" } },
  "client.digital_twin": { requires: { roles: ["client"] } },

  // ADMIN features (sub-scope aware)
  "admin.dashboard": { requires: { roles: ["admin"] } },
  "admin.users": { requires: { roles: ["admin"], scope_any: ["general", "ops", null] } },
  "admin.security": { requires: { roles: ["admin"], scope_any: ["security", "general", null] } },
  "admin.testing": { requires: { roles: ["admin"], scope_any: ["testing", "general", null] } },
  "admin.frontend": { requires: { roles: ["admin"], scope_any: ["frontend", "general", null] } },
  "admin.backend": { requires: { roles: ["admin"], scope_any: ["backend", "general", null] } },
};

/**
 * Compute access level for a feature.
 * @param {object} user — { role, verified, maturity_level, admin_scope, hh_subscription_status }
 * @param {string} key — feature key from FEATURES
 * @returns {"available" | "locked" | "hidden"}
 */
export function canUse(user, key) {
  const feature = FEATURES[key];
  if (!feature) return "hidden";
  const req = feature.requires || {};
  if (!user) return "hidden";

  // Role check (hard gate)
  if (req.roles && !req.roles.includes(user.role)) return "hidden";

  // Verification check (soft gate → "locked" instead of "hidden")
  if (req.verified === true && !user.verified) return "locked";

  // Maturity check (soft gate)
  if (req.maturity) {
    const userLevel = user.maturity_level || (user.role === "specialist" ? "beginner" : "n_a");
    if (!req.maturity.includes(userLevel)) return "locked";
  }

  // House Health subscription
  if (req.hh_subscription === "active" && user.hh_subscription_status !== "active") return "locked";

  // Admin sub-scope
  if (req.scope_any) {
    const scope = user.admin_scope || null;
    if (!req.scope_any.includes(scope)) return "hidden";
  }

  return "available";
}

/** Reason explanation for a locked feature — used in tooltips. */
export function lockedReason(user, key) {
  const feature = FEATURES[key];
  if (!feature) return "";
  const req = feature.requires || {};
  if (req.verified && !user?.verified) return "Finalizează verificarea contului pentru activare.";
  if (req.maturity) {
    const userLevel = user?.maturity_level || "beginner";
    if (userLevel === "beginner") return "Acceptă primul lead ca să deblochezi această funcție.";
    if (userLevel === "intermediate") return "Finalizează 10 lucrări ca să accesezi nivelul Advanced.";
  }
  if (req.hh_subscription === "active") return "Activează abonamentul House Health pentru această secțiune.";
  return "Funcție restricționată.";
}
