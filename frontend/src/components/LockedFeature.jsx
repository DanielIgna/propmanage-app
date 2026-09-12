/**
 * LockedFeature — card reutilizabil pentru feature-uri gated (Task 1, extins Task 5).
 *
 * Uz:
 *   <LockedFeature featureId="house_health_basic" nudgeId="dashboard.hh">
 *     ...conținut dezvăluit doar dacă user-ul are entitlement
 *   </LockedFeature>
 *
 * mode="compact" pentru pill inline, mode="full" pentru card mare.
 *
 * Copy vine central din NUDGE_COPY (upgradeNudge.js).
 * Analytics extension point: trackNudge(nudgeId, 'view'|'click').
 */
import React, { useEffect } from "react";
import { Lock, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEntitlements } from "../hooks/useEntitlements";
import { getNudgeCopy, trackNudge } from "../lib/upgradeNudge";

export const LockedFeature = ({
  featureId,
  nudgeId, // ex: "dashboard.house_health" — folosit pentru analytics
  title,
  description,
  ctaLabel,
  ctaHref,
  mode = "full", // full | compact
  children,
  testid,
}) => {
  const { entitlements, loading, hasFeature } = useEntitlements();
  const navigate = useNavigate();
  const copy = getNudgeCopy(featureId);

  // Fire "view" event când nudge-ul devine vizibil (o singură dată per render)
  useEffect(() => {
    if (!loading && !hasFeature(featureId) && nudgeId) {
      trackNudge(nudgeId, "view");
    }
  }, [loading, hasFeature, featureId, nudgeId]);

  if (loading) return <>{children}</>;
  if (hasFeature(featureId)) return <>{children}</>;

  const finalTitle = title || copy.title;
  const finalDescription = description || copy.description;
  const finalCta = ctaLabel || copy.cta_label;
  const finalHref = ctaHref || copy.cta_href;
  const tierLabel = entitlements?.tier_label || "Gratuit";

  const goCta = () => {
    if (nudgeId) trackNudge(nudgeId, "click");
    try { navigate(finalHref); }
    catch { window.location.href = finalHref; }
  };

  if (mode === "compact") {
    return (
      <div data-testid={testid || `locked-${featureId}`}
        className="inline-flex flex-wrap items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-[11px] font-bold text-amber-800 max-w-full">
        <Lock className="w-3.5 h-3.5 shrink-0" />
        <span className="truncate">{copy.short_reason}</span>
        <button onClick={goCta} className="ml-1 text-amber-900 underline shrink-0"
          data-testid={`locked-${featureId}-cta-compact`}>
          {finalCta}
        </button>
      </div>
    );
  }

  return (
    <div data-testid={testid || `locked-${featureId}`}
      className="rounded-3xl border-2 border-dashed border-amber-200 bg-gradient-to-br from-amber-50 to-white p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="w-11 h-11 rounded-2xl bg-amber-100 flex items-center justify-center shrink-0">
          <Lock className="w-5 h-5 text-amber-700" />
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
            {tierLabel} · {copy.tier_label}
          </div>
          <div className="mt-0.5 text-base font-black text-slate-900 leading-tight">{finalTitle}</div>
          <div className="mt-1 text-[12px] text-slate-600 leading-relaxed">{finalDescription}</div>
          <button onClick={goCta}
            data-testid={`locked-${featureId}-cta`}
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-black text-black hover:opacity-90 max-w-full whitespace-nowrap"
            style={{ background: "#d4ff3a" }}>
            <Sparkles className="w-3.5 h-3.5 shrink-0" /> {finalCta}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LockedFeature;
