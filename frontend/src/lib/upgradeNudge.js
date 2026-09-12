/**
 * upgradeNudge — central helper pentru CTA-uri de upgrade (Task 5).
 *
 * Reguli:
 *   - Un SINGUR loc unde definim copy-ul nudge-urilor Basic/Pro (Hick's Law la nivel de cod)
 *   - Analytics = extension point via CustomEvent (nu instalăm provider nou)
 *   - Reutilizează /pricing ca destinație unică de conversie
 *
 * Analytics: componentele apelează trackNudge(nudgeId, 'view' | 'click').
 * Se poate atașa un ascultător global:
 *   window.addEventListener('pm:upgrade_nudge', e => sendToAnalytics(e.detail))
 */

/** Copy centralizat per feature. Adaugă intrări aici, nu în componente. */
export const NUDGE_COPY = {
  house_health_basic: {
    tier: "CLIENT_BASIC",
    tier_label: "PropManage Basic",
    price_eur: 9,
    cta_href: "/pricing",
    title: "Documentează istoricul casei tale",
    description: "House Health Basic este inclus în PropManage Basic. Activează pentru a debloca upload de documente, recomandări și istoricul tehnic.",
    cta_label: "Activează Basic — 9 €/lună",
    short_reason: "Această funcție face parte din PropManage Basic.",
  },
  house_health_advanced: {
    tier: "CLIENT_PRO",
    tier_label: "PropManage Pro",
    price_eur: null,
    cta_href: "/pricing",
    title: "Analiză avansată House Health",
    description: "Funcție avansată de House Health inclusă în planul Pro.",
    cta_label: "Vezi planurile PropManage",
    short_reason: "Această funcție face parte din planul Pro.",
  },
  digital_twin_advanced: {
    tier: "CLIENT_PRO",
    tier_label: "PropManage Pro",
    price_eur: null,
    cta_href: "/pricing",
    title: "Digital Twin Advanced",
    description: "Editarea și colaborarea 3D sunt incluse în planul Pro.",
    cta_label: "Vezi planurile PropManage",
    short_reason: "Această funcție face parte din planul Pro.",
  },
};

const DEFAULT_COPY = {
  tier: "CLIENT_BASIC",
  tier_label: "PropManage Basic",
  price_eur: 9,
  cta_href: "/pricing",
  title: "Disponibil în PropManage Basic",
  description: "Această funcție este inclusă în abonamentul PropManage.",
  cta_label: "Activează Basic — 9 €/lună",
  short_reason: "Această funcție face parte din PropManage Basic.",
};

export const getNudgeCopy = (featureId) => NUDGE_COPY[featureId] || DEFAULT_COPY;

/** Emite un CustomEvent pe window. Fără dependență de vreun provider extern. */
export const trackNudge = (nudgeId, event) => {
  if (!nudgeId || !event) return;
  try {
    const detail = {
      nudge_id: nudgeId,
      event, // 'view' | 'click'
      timestamp: new Date().toISOString(),
      path: typeof window !== "undefined" ? window.location.pathname : null,
    };
    if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
      window.dispatchEvent(new CustomEvent("pm:upgrade_nudge", { detail }));
      window.dispatchEvent(new CustomEvent(`pm:upgrade_nudge_${event}ed`, { detail }));
    }
  } catch { /* silent — never break UI for analytics */ }
};

export default { NUDGE_COPY, getNudgeCopy, trackNudge };
