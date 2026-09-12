/**
 * PricingPage — /pricing
 *
 * Afișează DINAMIC planurile din `hh_plans` (admin-managed = SSOT).
 * Fără prețuri/feature-uri hardcodate — totul vine din:
 *   - GET  /api/house-health/plans           (planuri active, sortate)
 *   - GET  /api/me/entitlements              (tier curent)
 *   - POST /api/house-health/checkout-session {plan_slug, origin_url}  (Stripe)
 *
 * Diferențiere vizuală între tiere: PRO = recomandat, PREMIUM = stil premium.
 */
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { Check, Sparkles, Loader2, ShieldCheck, ArrowLeft, Lock, Crown, Gem } from "lucide-react";
import { API } from "./DashShared";
import { useEntitlements, clearEntitlementCache } from "../hooks/useEntitlements";
import { formatApiError } from "../auth";

const FREE_FEATURES = [
  "Adaugă proprietatea și profilul de bază",
  "Dosar Tehnic al proprietății",
  "Vizualizează starea documentelor",
];

// slug plan → rang (pentru „ai deja acces")
const SLUG_RANK = { basic: 1, pro: 2, premium: 3 };
const TIER_RANK = { FREE: 0, CLIENT_BASIC: 1, CLIENT_PRO: 2, CLIENT_PREMIUM: 3 };

// stil vizual per slug
const STYLE = {
  basic: { accent: "#166534", chipBg: "#166534", icon: ShieldCheck, level: "Nivel 2", ring: "#166534" },
  pro: { accent: "#0f766e", chipBg: "#0f766e", icon: Crown, level: "Nivel 3", ring: "#0f766e" },
  premium: { accent: "#7c3aed", chipBg: "#7c3aed", icon: Gem, level: "Nivel 4", ring: "#7c3aed" },
};

const PlanCard = ({ plan, entitlements, entLoading, busySlug, onCheckout }) => {
  const st = STYLE[plan.slug] || STYLE.basic;
  const Icon = st.icon;
  const recommended = plan.slug === "pro";
  const premium = plan.slug === "premium";
  const userRank = TIER_RANK[entitlements?.tier] ?? 0;
  const hasAccess = userRank >= (SLUG_RANK[plan.slug] ?? 99);
  const busy = busySlug === plan.slug;

  return (
    <div
      className={`relative rounded-3xl border-2 p-6 flex flex-col ${premium ? "bg-slate-900 text-white" : "bg-white"} ${recommended ? "shadow-xl" : "shadow-sm"}`}
      style={{ borderColor: recommended || premium ? st.ring : "#e2e8f0" }}
      data-testid={`pricing-card-${plan.slug}`}
    >
      {recommended && (
        <div className="absolute -top-3 left-6 px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-[0.16em] text-black" style={{ background: "#d4ff3a" }}>
          Recomandat
        </div>
      )}
      {premium && (
        <div className="absolute -top-3 left-6 px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-[0.16em] text-white" style={{ background: st.chipBg }}>
          Property Intelligence
        </div>
      )}

      <div className="flex items-center gap-2">
        <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: st.chipBg }}>
          <Icon className="w-4 h-4 text-[#d4ff3a]" />
        </span>
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.16em]" style={{ color: premium ? "#d4ff3a" : st.accent }}>{st.level}</div>
          <div className={`text-lg font-black leading-tight ${premium ? "text-white" : "text-slate-900"}`}>{plan.name}</div>
        </div>
      </div>

      <div className="mt-5">
        <span className={`text-4xl font-black ${premium ? "text-white" : "text-slate-900"}`}>{Number(plan.price_eur)}€</span>
        <span className={`text-[12px] font-bold ml-1 ${premium ? "text-slate-400" : "text-slate-500"}`}>/lună</span>
      </div>
      <div className={`mt-1 text-[10px] font-bold ${premium ? "text-slate-400" : "text-slate-400"}`}>
        {plan.trial_days > 0 ? `${plan.trial_days} zile trial · ` : ""}Anulezi oricând
      </div>

      {plan.description && (
        <p className={`mt-3 text-[11px] leading-relaxed ${premium ? "text-slate-300" : "text-slate-500"}`}>{plan.description}</p>
      )}

      <ul className="mt-4 space-y-1.5 flex-1" data-testid={`pricing-${plan.slug}-features`}>
        {(plan.features || []).map((f, i) => (
          <li key={i} className={`flex items-start gap-2 text-[12px] ${premium ? "text-slate-200" : "text-slate-800"}`}>
            <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: premium ? "#d4ff3a" : st.accent }} />
            <span className="font-medium">{f}</span>
          </li>
        ))}
      </ul>

      {hasAccess ? (
        <div
          className={`mt-6 rounded-xl px-4 py-2.5 text-center text-[11px] font-black ${premium ? "bg-white/10 text-[#d4ff3a]" : "bg-emerald-50 border border-emerald-200 text-emerald-800"}`}
          data-testid={`pricing-${plan.slug}-current`}
        >
          Ai deja acces · {entitlements?.tier_label}
        </div>
      ) : entLoading ? (
        <button disabled className="mt-6 w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-black text-black opacity-60" style={{ background: "#d4ff3a" }}>
          <Loader2 className="w-4 h-4 animate-spin" /> Se pregătește...
        </button>
      ) : (
        <button
          onClick={() => onCheckout(plan.slug)}
          disabled={busy}
          data-testid={`pricing-${plan.slug}-cta`}
          className="mt-6 w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-black text-black hover:opacity-90 disabled:opacity-60"
          style={{ background: "#d4ff3a" }}
        >
          {busy ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Deschidem checkout-ul...</>
          ) : (
            <><Sparkles className="w-4 h-4" /> Activează {plan.name}</>
          )}
        </button>
      )}
    </div>
  );
};

const PricingPage = () => {
  const navigate = useNavigate();
  const { entitlements, loading: entLoading, refresh } = useEntitlements();
  const [plans, setPlans] = useState(null);
  const [busySlug, setBusySlug] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (window.location.search.includes("session_id")) refresh();
  }, [refresh]);

  useEffect(() => {
    axios
      .get(`${API}/house-health/plans`)
      .then((r) => {
        const items = (r.data?.items || []).filter((p) => SLUG_RANK[p.slug]);
        items.sort((a, b) => (SLUG_RANK[a.slug] || 99) - (SLUG_RANK[b.slug] || 99));
        setPlans(items);
      })
      .catch((e) => {
        const status = e?.response?.status;
        if (status === 401 || status === 403) {
          navigate("/login?next=/pricing");
          return;
        }
        setError(formatApiError(e));
        setPlans([]);
      });
  }, [navigate]);

  const isFree = (entitlements?.tier || "FREE") === "FREE";

  const startCheckout = async (slug) => {
    setBusySlug(slug);
    setError(null);
    try {
      const res = await axios.post(`${API}/house-health/checkout-session`, {
        plan_slug: slug,
        origin_url: window.location.origin,
      });
      const url = res.data?.url;
      if (!url) throw new Error("Sesiune de checkout invalidă.");
      clearEntitlementCache();
      window.location.href = url;
    } catch (e) {
      const status = e?.response?.status;
      if (status === 401 || status === 403) {
        navigate("/login?next=/pricing");
        return;
      }
      setError(formatApiError(e));
    } finally {
      setBusySlug(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white" data-testid="pricing-page">
      <div className="max-w-6xl mx-auto px-5 pt-6 flex items-center gap-2">
        <button onClick={() => navigate(-1)} data-testid="pricing-back"
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border-2 border-slate-200 text-[11px] font-bold text-slate-600 hover:bg-slate-100">
          <ArrowLeft className="w-3 h-3" /> Înapoi
        </button>
        <div className="ml-auto text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">
          PropManage · Abonament
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-5 pt-8 text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#d4ff3a]/40 text-[10px] font-black uppercase tracking-[0.14em] text-slate-800">
          <Sparkles className="w-3 h-3" /> Alege planul potrivit casei tale
        </div>
        <h1 className="mt-4 text-4xl sm:text-5xl font-black text-slate-900 leading-[1.05]" data-testid="pricing-heading">
          De la primul pas<br />la Property Intelligence.
        </h1>
        <p className="mt-4 text-base text-slate-600 max-w-xl mx-auto">
          Începe gratuit. Activează House Health când vrei să urmărești starea casei, apoi urcă la Pro sau Premium pe măsură ce casa ta prinde viață.
        </p>
      </div>

      <div className="max-w-6xl mx-auto px-5 mt-12 pb-24 grid md:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
        {/* FREE card */}
        <div className="rounded-3xl border-2 border-slate-200 bg-white p-6 flex flex-col" data-testid="pricing-card-free">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
              <Lock className="w-4 h-4 text-slate-500" />
            </span>
            <div>
              <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Nivel 1</div>
              <div className="text-lg font-black text-slate-900 leading-tight">Gratuit</div>
            </div>
          </div>
          <div className="mt-5">
            <span className="text-4xl font-black text-slate-900">0€</span>
            <span className="text-[12px] font-bold text-slate-500 ml-1">/lună</span>
          </div>
          <div className="mt-1 text-[10px] font-bold text-slate-400">Pentru început · Fără card</div>
          <ul className="mt-4 space-y-1.5 flex-1" data-testid="pricing-free-features">
            {FREE_FEATURES.map((f) => (
              <li key={f} className="flex items-start gap-2 text-[12px] text-slate-700">
                <Check className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
          {isFree ? (
            <div className="mt-6 rounded-xl bg-slate-100 px-4 py-2.5 text-center text-[11px] font-bold text-slate-600" data-testid="pricing-free-current">
              Planul tău actual
            </div>
          ) : (
            <div className="mt-6 text-[10px] text-slate-400 text-center">
              Poți reveni la Gratuit anulând abonamentul.
            </div>
          )}
        </div>

        {/* Dynamic plan cards */}
        {plans === null ? (
          <div className="md:col-span-1 lg:col-span-3 flex items-center justify-center py-16 text-slate-400 gap-2" data-testid="pricing-loading">
            <Loader2 className="w-5 h-5 animate-spin" /> Se încarcă planurile...
          </div>
        ) : (
          plans.map((plan) => (
            <PlanCard key={plan.slug} plan={plan} entitlements={entitlements} entLoading={entLoading} busySlug={busySlug} onCheckout={startCheckout} />
          ))
        )}
      </div>

      {error && (
        <div className="max-w-3xl mx-auto px-5 -mt-16 pb-12" data-testid="pricing-error">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-[12px] text-rose-700">{error}</div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-5 pb-12 text-center text-[10px] text-slate-400">
        Plată securizată prin Stripe · Fără taxe ascunse. Poți gestiona sau anula abonamentul oricând din contul tău.
      </div>
    </div>
  );
};

export default PricingPage;
