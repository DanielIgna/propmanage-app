// ExperienceSpacesPage — Phase ES-0 placeholder dashboard.
// Shows the module status, allows admin to toggle the feature flag, and
// surfaces the granular submodule controls. Future phases add:
//   ES-1 → Spaces & Calendar widgets
//   ES-2 → Bookings table
//   ES-3 → Revenue cards
//   ES-6 → AI Manager insights
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Sparkles, Loader2, Power, AlertCircle, CheckCircle2, Lock,
  Calendar, Briefcase, Camera, Users, Brain, BarChart3, Coins,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const MODULE_META = {
  spaces:       { icon: Briefcase, label: "Spaces",         hint: "CRUD spații + Digital Twin" },
  bookings:     { icon: Calendar,  label: "Bookings",       hint: "Rezervări + calendar atomic" },
  payments:     { icon: Coins,     label: "Payments",       hint: "Stripe + revenue split" },
  providers:    { icon: Users,     label: "Providers",      hint: "Fotograf, decor, catering, etc." },
  ai_manager:   { icon: Brain,     label: "AI Manager",     hint: "Insights zilnice + conversational" },
  digital_twin: { icon: Camera,    label: "Digital Twin",   hint: "3D viewer + asset registry" },
  analytics:    { icon: BarChart3, label: "Analytics",      hint: "Rapoarte ocupare + venit" },
};

export const ExperienceSpacesPage = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await ax.get("/api/experience-spaces/_admin/config");
      setConfig(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare config");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const updateConfig = async (patch) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await ax.put("/api/experience-spaces/_admin/config", patch);
      setConfig(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la salvare");
    } finally { setSaving(false); }
  };

  const toggleMaster = () => updateConfig({ enable_experience_spaces: !config?.enable_experience_spaces });
  const toggleModule = (k) => updateConfig({
    es_modules_enabled: { ...(config?.es_modules_enabled || {}), [k]: !(config?.es_modules_enabled || {})[k] },
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă Experience Spaces...
      </div>
    );
  }

  const masterOn = !!config?.enable_experience_spaces;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="es-back">← Înapoi la Admin Dashboard</Link>

        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="es-title">
              Experience <span className="italic gradient-text">Spaces</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">
              Business Operating System pentru spații monetizabile (centru educațional kids, evenimente, ateliere). Modul izolat, feature-flagged, MongoDB-only, rollback &lt; 1 min.
            </p>
          </div>
          <button
            onClick={toggleMaster}
            disabled={saving}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border transition-colors ${
              masterOn
                ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/15"
                : "bg-red-500/10 border-red-500/40 text-red-300 hover:bg-red-500/15"
            }`}
            data-testid="es-master-toggle"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Power className="w-4 h-4" />}
            {masterOn ? "Activ — click pentru a opri modulul" : "Dezactivat — click pentru a activa"}
          </button>
        </div>

        {/* STATUS BANNER */}
        <div className={`rounded-2xl p-5 border mt-6 flex items-start gap-3 ${
          masterOn
            ? "bg-emerald-500/5 border-emerald-500/30"
            : "bg-amber-500/5 border-amber-500/30"
        }`} data-testid="es-status-banner">
          {masterOn
            ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            : <Lock className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />}
          <div className="text-sm">
            {masterOn ? (
              <>
                <strong className="text-emerald-300">Modulul Experience Spaces este LIVE</strong> · Phase ES-0 Foundation activă.
                <div className="text-xs text-stone-400 mt-1">
                  Următoarea fază: <strong>ES-1 — Spaces & Calendar</strong> (CRUD spații + availability rules + calendar engine cu buffer).
                </div>
              </>
            ) : (
              <>
                <strong className="text-amber-300">Modulul este în stand-by</strong> — endpoints returnează 403, nimic afectat din restul platformei.
                <div className="text-xs text-stone-400 mt-1">
                  Activează modulul ca să începi configurarea spațiilor.
                </div>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300 flex items-center gap-2" data-testid="es-error">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {/* SUBMODULES */}
        <div className="mt-6">
          <h2 className="text-sm uppercase tracking-wider text-stone-400 mb-3">Submodule (control granular)</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(MODULE_META).map(([k, meta]) => {
              const Icon = meta.icon;
              const on = !!(config?.es_modules_enabled || {})[k];
              return (
                <button
                  key={k}
                  onClick={() => toggleModule(k)}
                  disabled={saving || !masterOn}
                  className={`text-left bg-[#0e0e10] border rounded-2xl p-4 transition-all ${
                    !masterOn
                      ? "opacity-40 cursor-not-allowed border-white/5"
                      : on
                      ? "border-emerald-500/40 hover:border-emerald-500/60"
                      : "border-white/10 hover:border-white/20"
                  }`}
                  data-testid={`es-module-${k}`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      on ? "bg-emerald-500/10 border-emerald-500/30" : "bg-white/5 border-white/10"
                    } border`}>
                      <Icon className={`w-4 h-4 ${on ? "text-emerald-400" : "text-stone-400"}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className="text-sm font-semibold">{meta.label}</div>
                        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${
                          on ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10" : "border-stone-500/40 text-stone-400 bg-stone-500/5"
                        }`}>{on ? "ON" : "OFF"}</span>
                      </div>
                      <div className="text-xs text-stone-500 mt-1">{meta.hint}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* CONFIG DEFAULTS */}
        <div className="mt-6 bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="es-defaults">
          <h2 className="text-sm uppercase tracking-wider text-stone-400 mb-3">Configurare implicită</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: "Revenue Model", v: config?.es_default_revenue_model },
              { label: "Comision implicit", v: `${config?.es_default_commission_pct}%` },
              { label: "Monedă", v: config?.es_default_currency },
              { label: "Timezone", v: config?.es_default_timezone },
            ].map(c => (
              <div key={c.label} className="bg-white/[0.02] border border-white/5 rounded-xl px-3 py-2">
                <div className="text-[10px] uppercase tracking-wider text-stone-400">{c.label}</div>
                <div className="font-mono text-sm text-stone-100 mt-0.5">{c.v}</div>
              </div>
            ))}
          </div>
          <div className="text-[11px] text-stone-500 mt-3">
            💡 Aceste valori se aplică oricărui spațiu nou creat. Pot fi suprascrise per spațiu.
          </div>
        </div>

        {/* PHASE ROADMAP */}
        <div className="mt-6 bg-[#0e0e10] border border-white/10 rounded-2xl p-5">
          <h2 className="text-sm uppercase tracking-wider text-stone-400 mb-3 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-[#d4ff3a]" /> Roadmap MVP (ES-0 → ES-3)
          </h2>
          <div className="space-y-2 text-sm">
            {[
              { id: "ES-0", title: "Foundation", days: 3, status: "done", desc: "Feature flag · scaffolding · middleware · rollback test" },
              { id: "ES-1", title: "Spaces & Calendar", days: 5, status: "next", desc: "CRUD spațiu · availability rules · calendar engine cu buffer + DST" },
              { id: "ES-2", title: "Bookings & Packages", days: 5, status: "planned", desc: "Atomic booking · quote · revenue split · customer dashboard" },
              { id: "ES-3", title: "Payments", days: 4, status: "planned", desc: "Stripe integration · refund · idempotent webhooks" },
              { id: "ES-6", title: "AI Manager", days: 5, status: "parallel", desc: "Daily insights cron · conversational widget (cerut în MVP)" },
            ].map(p => (
              <div key={p.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                  p.status === "done"     ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300" :
                  p.status === "next"     ? "bg-amber-500/10 border-amber-500/40 text-amber-300 animate-pulse" :
                  p.status === "parallel" ? "bg-violet-500/10 border-violet-500/40 text-violet-300" :
                                            "bg-stone-500/10 border-stone-500/40 text-stone-400"
                }`}>{p.id}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm">{p.title} <span className="text-[10px] text-stone-500">({p.days}z)</span></div>
                  <div className="text-[11px] text-stone-500 truncate">{p.desc}</div>
                </div>
                <span className={`text-[10px] uppercase ${
                  p.status === "done"     ? "text-emerald-400" :
                  p.status === "next"     ? "text-amber-400" :
                  p.status === "parallel" ? "text-violet-400" :
                                            "text-stone-500"
                }`}>
                  {p.status === "done" ? "✓ done" : p.status === "next" ? "→ next" : p.status === "parallel" ? "AI" : "planned"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* SAFETY NOTE */}
        <div className="mt-6 bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 text-xs text-amber-100 flex items-start gap-3" data-testid="es-safety">
          <Lock className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <strong>Izolat &amp; reversibil:</strong> Toate colecțiile prefixate <code className="text-amber-300">es_*</code> (es_spaces, es_bookings, es_*). Toate rutele sub <code className="text-amber-300">/api/experience-spaces/*</code>. Niciodată atinge module existente (Properties, Requests, Tenants, Invoices). Rollback prin OFF de mai sus = instant 403 pe toate endpoint-urile, zero impact pe restul platformei.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExperienceSpacesPage;
