// House Health Card — F1 Foundation. Shown on ClientDashboard.
// Renders nothing when feature flag is OFF (graceful degradation).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Heart, Lock, ChevronRight, Calendar, FileText, BadgeCheck, AlertCircle, Sparkles } from "lucide-react";
import { API } from "./DashShared";
import { getNudgeCopy, trackNudge } from "../lib/upgradeNudge";

const CLASSIFICATION_THEME = {
  Excellent: { label: "Excellent", bg: "bg-emerald-500/15", text: "text-emerald-300", ring: "ring-emerald-400/40" },
  Good:      { label: "Good",      bg: "bg-sky-500/15",      text: "text-sky-300",      ring: "ring-sky-400/40" },
  Fair:      { label: "Fair",      bg: "bg-amber-500/15",    text: "text-amber-300",    ring: "ring-amber-400/40" },
  "Needs Attention": { label: "Needs Attention", bg: "bg-rose-500/15", text: "text-rose-300", ring: "ring-rose-400/40" },
};

const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("ro-RO", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  catch { return "—"; }
};

const HouseHealthCard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const flag = await axios.get(`${API}/house-health/feature-flag`).catch(() => ({ data: { enabled: false } }));
        if (!flag?.data?.enabled) {
          setEnabled(false);
          return;
        }
        setEnabled(true);
        const r = await axios.get(`${API}/house-health/dashboard`);
        setData(r.data || null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (!enabled || loading) return null;
  if (!data || data.enabled === false) return null;

  // Locked state — no DT
  if (data.locked && data.lock_reason === "no_twin") {
    return (
      <div
        className="rounded-3xl border border-stone-700/60 bg-gradient-to-br from-stone-900/60 to-stone-800/40 p-5 mb-4"
        data-testid="house-health-card-locked-twin"
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-stone-700/50 flex items-center justify-center shrink-0">
            <Lock className="w-5 h-5 text-stone-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs uppercase tracking-wider text-stone-500 font-bold">House Health</div>
            <div className="text-sm font-semibold text-stone-200 mt-0.5">Disponibil cu Digital Twin</div>
            <div className="text-xs text-stone-400 mt-1.5">{data.lock_message}</div>
            <a
              href="/digital-twin"
              className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 mt-2.5"
              data-testid="house-health-cta-twin"
            >
              Creează Digital Twin <ChevronRight className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Locked state — no subscription (but DT exists) · Task 5 nudge Basic
  if (data.locked && data.lock_reason === "no_subscription") {
    const copy = getNudgeCopy("house_health_basic");
    return <HouseHealthNudge data={data} copy={copy} />;
  }

  // Active state — full card
  const cls = CLASSIFICATION_THEME[data.classification] || CLASSIFICATION_THEME.Good;
  const score = data.score_overall;

  return (
    <div
      className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 via-cyan-500/5 to-stone-900/40 p-5 mb-4"
      data-testid="house-health-card-active"
    >
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shrink-0 shadow-lg shadow-emerald-500/30">
          <Heart className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-xs uppercase tracking-wider text-emerald-300 font-bold">House Health</div>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                data.subscription?.status === "active"
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "bg-amber-500/20 text-amber-300"
              }`}
              data-testid="house-health-sub-status"
            >
              {(data.subscription?.status || "trial").toUpperCase()}
            </span>
          </div>
          <div className="text-base font-bold text-stone-100 mt-0.5">
            {data.twin?.name || "Proprietatea ta"}
          </div>

          {/* Score + Classification */}
          <div className="flex items-center gap-3 mt-3">
            <div className={`tabular-nums text-3xl font-extrabold ${cls.text}`} data-testid="house-health-score">
              {score != null ? `${score}` : "—"}
              <span className="text-sm font-medium text-stone-500">/100</span>
            </div>
            <div className={`text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider ${cls.bg} ${cls.text} ring-1 ${cls.ring}`}>
              {data.classification || "Pending"}
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-3 text-xs">
            <div className="px-2.5 py-1.5 rounded-lg bg-stone-800/40 border border-stone-700/40">
              <div className="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">Ultima eval.</div>
              <div className="text-stone-200 font-medium flex items-center gap-1 mt-0.5">
                <Calendar className="w-3 h-3 text-stone-400" />
                {fmtDate(data.last_evaluation_date)}
              </div>
            </div>
            <div className="px-2.5 py-1.5 rounded-lg bg-stone-800/40 border border-stone-700/40">
              <div className="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">Următoarea</div>
              <div className="text-stone-200 font-medium flex items-center gap-1 mt-0.5">
                <AlertCircle className="w-3 h-3 text-amber-400" />
                {fmtDate(data.next_evaluation_date)}
              </div>
            </div>
            <div className="px-2.5 py-1.5 rounded-lg bg-stone-800/40 border border-stone-700/40 col-span-2 sm:col-span-1">
              <div className="text-[10px] uppercase tracking-wider text-stone-500 font-semibold">Documente</div>
              <div className="text-stone-200 font-medium flex items-center gap-1 mt-0.5">
                <FileText className="w-3 h-3 text-stone-400" />
                {data.documents_count ?? 0} fișiere
              </div>
            </div>
          </div>

          <a
            href={`/house-health/${data.twin?.id || ""}`}
            className="mt-3.5 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-white text-xs font-semibold shadow hover:from-emerald-400 hover:to-cyan-400"
            data-testid="house-health-cta-view"
          >
            Vezi Sănătatea Casei
            <ChevronRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
};

export default HouseHealthCard;
export { HouseHealthCard };

/**
 * Task 5: nudge consistent Basic (dark card, aliniat cu design existent HH).
 * Copy central din upgradeNudge.js, CTA → /pricing, tracking pe view + click.
 */
const HouseHealthNudge = ({ data, copy }) => {
  useEffect(() => { trackNudge("dashboard.house_health", "view"); }, []);
  const goPricing = () => {
    trackNudge("dashboard.house_health", "click");
    window.location.href = copy.cta_href;
  };
  return (
    <div
      className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-cyan-500/5 p-5 mb-4"
      data-testid="house-health-card-locked-sub"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shrink-0 shadow-lg shadow-emerald-500/30">
          <Heart className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs uppercase tracking-wider text-emerald-300 font-bold">
            House Health · {copy.tier_label}
          </div>
          <div className="text-base font-bold text-stone-100 mt-0.5">{copy.title}</div>
          <div className="text-xs text-stone-400 mt-1.5">{copy.short_reason}</div>
          <div className="text-[11px] text-stone-500 mt-2 leading-relaxed">
            <BadgeCheck className="w-3 h-3 inline mr-1 text-emerald-400" />
            Documentație tehnică · recomandări · istoric intervenții
          </div>
          <button
            className="mt-3 px-4 py-2 rounded-full font-black text-black text-xs shadow inline-flex items-center gap-1.5 max-w-full"
            style={{ background: "#d4ff3a" }}
            data-testid="house-health-cta-subscribe"
            onClick={goPricing}
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0" /> {copy.cta_label}
          </button>
        </div>
      </div>
    </div>
  );
};
