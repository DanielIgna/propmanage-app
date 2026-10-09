// TierCelebrationBanner — appears once after a tier promotion to celebrate
// the user. Auto-dismisses on click and won't show again until next promotion.
//
// Mount once near the top of ClientDashboard / SpecialistDashboard.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { PartyPopper, X, Sparkles } from "lucide-react";
import { TIER_LABEL } from "./experienceTier";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const TIER_GRADIENT = {
  regular:  "from-blue-500/15 to-blue-500/5 border-blue-500/40",
  verified: "from-emerald-500/15 to-emerald-500/5 border-emerald-500/40",
  pro:      "from-violet-500/15 to-violet-500/5 border-violet-500/40",
};

export const TierCelebrationBanner = () => {
  const [pending, setPending] = useState(null);
  const [dismissing, setDismissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await ax.get("/api/me/tier-celebration");
        if (!cancelled) setPending(data.pending);
      } catch {
        /* user not auth / endpoint missing — silent */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const dismiss = async () => {
    setDismissing(true);
    try {
      await ax.post("/api/me/tier-celebration/dismiss");
      setPending(null);
    } finally {
      setDismissing(false);
    }
  };

  if (!pending) return null;
  const toTier = pending.to;
  const gradientCls = TIER_GRADIENT[toTier] || TIER_GRADIENT.regular;
  const features = pending.new_features_pretty || [];

  return (
    <div
      className={`relative bg-gradient-to-br ${gradientCls} border rounded-2xl p-5 mb-4 overflow-hidden`}
      data-testid="tier-celebration-banner"
    >
      <button
        onClick={dismiss}
        disabled={dismissing}
        className="absolute top-3 right-3 text-stone-400 hover:text-white disabled:opacity-50"
        aria-label="Închide"
        data-testid="tier-celebration-dismiss"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center shrink-0">
          <PartyPopper className="w-6 h-6 text-amber-300" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-stone-400">Felicitări!</div>
          <h3 className="font-serif text-2xl text-white mt-0.5" data-testid="tier-celebration-title">
            Ai fost promovat la <span className="italic">{TIER_LABEL[toTier] || toTier}</span>
          </h3>
          {features.length > 0 && (
            <>
              <p className="text-sm text-stone-300 mt-2">
                Ai deblocat <strong className="text-white">{features.length}</strong> funcții noi:
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {features.map((f, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-white/10 border border-white/20 text-stone-100"
                    data-testid={`tier-celebration-feature-${i}`}
                  >
                    <Sparkles className="w-2.5 h-2.5 text-amber-300" /> {f}
                  </span>
                ))}
              </div>
            </>
          )}
          <button
            onClick={dismiss}
            disabled={dismissing}
            className="mt-3 text-xs text-stone-300 hover:text-white underline disabled:opacity-50"
            data-testid="tier-celebration-acknowledge"
          >
            Am înțeles, mulțumesc!
          </button>
        </div>
      </div>
    </div>
  );
};

export default TierCelebrationBanner;
