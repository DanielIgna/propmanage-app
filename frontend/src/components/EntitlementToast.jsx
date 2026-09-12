/**
 * EntitlementToast — Task 5.
 *
 * Toast global (Sonner) care apare când o cerere backend răspunde 402.
 * User-ul NU vede "HTTP 402" sau "entitlement_required" — vede un mesaj scurt
 * cu CTA "Activează Basic — 9 €/lună" (sau echivalent pentru Pro).
 *
 * Se montează o singură dată în App. Ascultă `pm:entitlement_denied` (emis de
 * interceptor-ul axios din auth.js).
 */
import { useEffect } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { getNudgeCopy, trackNudge } from "../lib/upgradeNudge";

export const EntitlementToast = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const onDenied = (e) => {
      const feature = e?.detail?.feature;
      if (!feature) return;
      const copy = getNudgeCopy(feature);
      // Deduplicate rapid succession pe același feature (rate-limit soft)
      const key = `pm_ent_toast_${feature}`;
      const now = Date.now();
      const last = Number(sessionStorage.getItem(key) || 0);
      if (now - last < 3000) return;
      try { sessionStorage.setItem(key, String(now)); } catch { /* silent */ }

      trackNudge(`toast.${feature}`, "view");
      toast(copy.title, {
        description: copy.short_reason,
        duration: 6000,
        action: {
          label: copy.cta_label,
          onClick: () => {
            trackNudge(`toast.${feature}`, "click");
            try { navigate(copy.cta_href); }
            catch { window.location.href = copy.cta_href; }
          },
        },
      });
    };
    window.addEventListener("pm:entitlement_denied", onDenied);
    return () => window.removeEventListener("pm:entitlement_denied", onDenied);
  }, [navigate]);

  return null;
};

export default EntitlementToast;
