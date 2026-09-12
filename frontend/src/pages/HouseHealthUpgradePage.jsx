// House Health Upgrade Page — F4.3
// Routes:
//   /house-health/upgrade           → plan picker
//   /house-health/upgrade/success   → status poll + activation confirmation
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import {
  Heart, Check, Loader2, Sparkles, AlertCircle, ChevronLeft, CreditCard,
} from "lucide-react";
import { API } from "./DashShared";
import { EcosystemFlow } from "../components/ecosystem/EcosystemFlow";
import { NextStep } from "../components/ecosystem/NextStep";
const HouseHealthUpgradePage = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busySlug, setBusySlug] = useState(null);
  const [error, setError] = useState("");

  const [authRequired, setAuthRequired] = useState(false);

  useEffect(() => {
    axios
      .get(`${API}/house-health/plans`)
      .then((r) => setPlans(r.data?.items || []))
      .catch((e) => {
        setPlans([]);
        if (e?.response?.status === 401) setAuthRequired(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const subscribe = async (slug) => {
    setError("");
    setBusySlug(slug);
    try {
      const r = await axios.post(`${API}/house-health/checkout-session`, {
        plan_slug: slug,
        origin_url: window.location.origin,
      });
      if (r.data?.url) {
        window.location.href = r.data.url;
        return;
      }
      throw new Error("Stripe nu a returnat URL.");
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Eroare la inițierea plății.");
      setBusySlug(null);
    }
  };

  const featured = plans.find((p) => p.slug === "pro") || plans[1];

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        <button
          onClick={() => navigate(-1)}
          data-testid="hh-upgrade-back"
          className="text-stone-400 hover:text-stone-200 inline-flex items-center gap-1 text-sm mb-5"
        >
          <ChevronLeft className="w-4 h-4" /> Înapoi
        </button>

        <div className="flex items-center gap-3 mb-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Heart className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Activează House Health</h1>
            <p className="text-sm text-stone-400">Sănătatea proprietății tale, monitorizată profesional</p>
          </div>
        </div>
        <p className="text-stone-400 max-w-2xl mb-8">
          Modulul Premium <span className="text-emerald-300 font-semibold">House Health</span> îți oferă acces la
          evaluări tehnice de la specialiști verificați, scor de sănătate al proprietății, recomandări personalizate
          și automatizare lead-uri în marketplace cu comision redus.
        </p>
        <div className="mb-8 p-5 rounded-3xl bg-white/[0.03] border border-white/10" data-testid="hh-ecosystem-flow">
          <EcosystemFlow dark compact activeKey="house_health" />
          <p className="text-xs text-stone-500 mt-3">House Health este ultima etapă a procesului PropManage: după audit, Digital Twin și implementare, locuința intră în întreținere monitorizată.</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/40 text-rose-300 text-sm flex items-center gap-2" data-testid="hh-upgrade-error">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center gap-2 text-stone-400">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă planurile...
          </div>
        ) : plans.length === 0 ? (
          authRequired ? (
            <div className="p-8 rounded-3xl bg-white/[0.03] border border-white/10 text-center" data-testid="hh-auth-required">
              <p className="text-stone-300 font-semibold mb-1">Planurile House Health sunt disponibile după autentificare.</p>
              <p className="text-sm text-stone-500 mb-5">Creează-ți cont gratuit sau conectează-te pentru a-ți activa monitorizarea locuinței.</p>
              <div className="flex justify-center gap-3">
                <a href="/auth" className="px-6 py-2.5 rounded-full bg-emerald-500 text-white text-sm font-bold hover:bg-emerald-400 transition-colors" data-testid="hh-login-cta">Conectează-te</a>
                <a href="/register" className="px-6 py-2.5 rounded-full border border-white/15 text-stone-300 text-sm font-bold hover:border-emerald-400/60 hover:text-white transition-colors" data-testid="hh-register-cta">Creează cont</a>
              </div>
            </div>
          ) : (
            <div className="text-stone-500 italic">Niciun plan disponibil momentan.</div>
          )
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="hh-upgrade-plans">
            {plans.map((p) => (
              <PlanCard
                key={p.id}
                plan={p}
                featured={p.id === featured?.id}
                busy={busySlug === p.slug}
                onSubscribe={() => subscribe(p.slug)}
              />
            ))}
          </div>
        )}

        <div className="mt-10 p-5 rounded-2xl bg-stone-900/40 border border-stone-800 text-xs text-stone-400 max-w-3xl">
          <div className="font-bold text-stone-200 mb-1">🔒 Plată securizată via Stripe</div>
          <p>
            Plata este procesată prin Stripe. Datele cardului tău nu trec niciodată prin serverele PropManage.
            Poți anula oricând — accesul rămâne activ până la sfârșitul perioadei plătite.
          </p>
        </div>

        <div className="mt-8">
          <NextStep
            dark
            label="Nu ai încă audit sau Digital Twin?"
            title="Începe procesul de la primul pas"
            desc="House Health funcționează cel mai bine pe o locuință auditată, cu Digital Twin — monitorizarea pornește de la date reale."
            to="/imobile-verificate/sell"
            cta="Solicită Audit + Digital Twin"
          />
        </div>
      </div>
    </div>
  );
};

const PlanCard = ({ plan, featured, busy, onSubscribe }) => {
  const periodLabel = plan.billing_period === "yearly" ? "an" : plan.billing_period === "one_time" ? "o dată" : "lună";
  return (
    <div
      data-testid={`hh-plan-card-${plan.slug}`}
      className={`relative p-6 rounded-2xl border transition-all ${
        featured
          ? "border-emerald-500/60 bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 shadow-2xl shadow-emerald-500/10"
          : "border-stone-800 bg-stone-900/40 hover:border-stone-700"
      }`}
    >
      {featured && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 text-stone-950 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
          <Sparkles className="w-3 h-3" /> Recomandat
        </div>
      )}
      <div className="text-xs uppercase tracking-wider text-stone-400 font-bold mb-1">{plan.slug}</div>
      <h3 className="text-2xl font-bold mb-1">{plan.name}</h3>
      <p className="text-xs text-stone-400 min-h-[3rem]">{plan.description}</p>

      <div className="my-4 flex items-baseline gap-1">
        <span className="text-4xl font-black tabular-nums">{plan.price_eur}</span>
        <span className="text-sm text-stone-400">€ / {periodLabel}</span>
      </div>
      {plan.trial_days > 0 && (
        <div className="text-[11px] text-cyan-300 font-semibold mb-3">
          🎁 {plan.trial_days} zile trial gratuit
        </div>
      )}

      <ul className="space-y-1.5 text-sm mb-5 min-h-[8rem]" data-testid={`hh-plan-features-${plan.slug}`}>
        {(plan.features || []).map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-stone-300">
            <Check className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> <span>{f}</span>
          </li>
        ))}
      </ul>

      <div className="text-[11px] text-stone-500 mb-3">
        Comision marketplace lead-uri: <span className="text-amber-300 font-semibold">{plan.lead_commission_pct}%</span>
      </div>

      <button
        onClick={onSubscribe}
        disabled={busy}
        data-testid={`hh-plan-subscribe-${plan.slug}`}
        className={`w-full py-3 rounded-xl font-bold text-sm inline-flex items-center justify-center gap-2 transition-all ${
          featured
            ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-stone-950 hover:scale-[1.02]"
            : "bg-stone-800 text-stone-100 hover:bg-stone-700"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
        {busy ? "Se redirecționează..." : "Activează acum"}
      </button>
    </div>
  );
};

// ============================================================================
// /house-health/upgrade/success — polls status, activates subscription
// ============================================================================
export const HouseHealthUpgradeSuccess = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const navigate = useNavigate();
  const [state, setState] = useState({ phase: "polling", message: "Verificăm plata..." });
  const [details, setDetails] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setState({ phase: "error", message: "Lipsește session_id." });
      return;
    }
    const MAX_ATTEMPTS = 8;
    const INTERVAL = 2000;
    let cancelled = false;

    const poll = async (attempt) => {
      if (cancelled) return;
      try {
        const r = await axios.get(`${API}/house-health/checkout-status/${sessionId}`);
        const data = r.data;
        setDetails(data);
        if (data.payment_status === "paid") {
          setState({ phase: "success", message: "Plată confirmată! Abonament activat." });
          // Invalidează cache-ul entitlements ca la revenirea în UI să reflecte tier-ul nou
          try {
            const mod = await import("../hooks/useEntitlements");
            mod.clearEntitlementCache?.();
          } catch { /* silent */ }
          return;
        }
        if (data.status === "expired") {
          setState({ phase: "error", message: "Sesiunea de plată a expirat." });
          return;
        }
        if (attempt >= MAX_ATTEMPTS) {
          setState({ phase: "timeout", message: "Verificare în curs. Vei primi un email de confirmare." });
          return;
        }
        setState({ phase: "polling", message: `Verificăm plata... (${attempt + 1}/${MAX_ATTEMPTS})` });
        setTimeout(() => poll(attempt + 1), INTERVAL);
      } catch (e) {
        setState({ phase: "error", message: e?.response?.data?.detail || "Eroare la verificarea plății." });
      }
    };
    poll(0);

    return () => { cancelled = true; };
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-stone-900/60 border border-stone-800 rounded-2xl p-8 text-center" data-testid="hh-upgrade-success-panel">
        {state.phase === "polling" && <Loader2 className="w-12 h-12 mx-auto text-emerald-400 animate-spin mb-4" />}
        {state.phase === "success" && (
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 mx-auto flex items-center justify-center mb-4">
            <Check className="w-9 h-9 text-emerald-400" />
          </div>
        )}
        {(state.phase === "error" || state.phase === "timeout") && (
          <AlertCircle className="w-12 h-12 mx-auto text-amber-400 mb-4" />
        )}

        <h1 className="text-2xl font-bold mb-2">{
          state.phase === "success" ? "Bun venit!" :
          state.phase === "error" ? "Atenție" :
          state.phase === "timeout" ? "Aproape gata" : "Procesăm plata..."
        }</h1>
        <p className="text-stone-400 mb-5" data-testid="hh-upgrade-success-message">{state.message}</p>

        {details && state.phase === "success" && (
          <div className="bg-stone-900 rounded-xl p-4 mb-5 text-left text-sm">
            <div className="text-xs uppercase tracking-wider text-stone-500 font-bold mb-1">Detalii</div>
            <div className="space-y-1 text-stone-300">
              <div>💳 <span className="text-stone-400">Sumă:</span> <span className="tabular-nums">{details.amount} {details.currency?.toUpperCase()}</span></div>
              {details.expires_at && (
                <div>📅 <span className="text-stone-400">Acces până la:</span> {new Date(details.expires_at).toLocaleDateString("ro-RO")}</div>
              )}
            </div>
          </div>
        )}

        <button
          onClick={() => navigate("/")}
          data-testid="hh-upgrade-success-cta"
          className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-stone-950 font-bold text-sm inline-flex items-center gap-2"
        >
          {state.phase === "success" ? "Mergi la Dashboard" : "Înapoi"}
        </button>
      </div>
    </div>
  );
};

export default HouseHealthUpgradePage;
