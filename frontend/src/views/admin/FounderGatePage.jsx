// FounderGatePage — Phase FG-0 visualization (read-only)
//
// Displays the 13 protected critical actions registry + current gate state.
// NO controls — gate is foundation-only. Phase FG-2+ will add controls.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ShieldCheck, ShieldAlert, ChevronLeft, Loader2, Lock,
  Coins, Database, Settings, ShieldQuestion, CheckCircle2,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const CATEGORY_META = {
  financial:  { label: "Financiar",   icon: Coins,         color: "amber" },
  data:       { label: "Date",        icon: Database,      color: "blue" },
  security:   { label: "Securitate",  icon: ShieldAlert,   color: "red" },
  governance: { label: "Guvernanță",  icon: ShieldCheck,   color: "violet" },
};

const SEVERITY_COLOR = {
  critical: "bg-red-500/10 border-red-500/40 text-red-300",
  high:     "bg-amber-500/10 border-amber-500/40 text-amber-300",
};

const CAT_COLOR = (c) => ({
  amber:  "bg-amber-500/10 border-amber-500/30 text-amber-300",
  blue:   "bg-blue-500/10 border-blue-500/30 text-blue-300",
  red:    "bg-red-500/10 border-red-500/30 text-red-300",
  violet: "bg-violet-500/10 border-violet-500/30 text-violet-300",
}[c]);

const FounderGatePage = () => {
  const [status, setStatus] = useState(null);
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [s, a] = await Promise.all([
          ax.get("/api/admin/founder-gate/status"),
          ax.get("/api/admin/founder-gate/critical-actions"),
        ]);
        setStatus(s.data);
        setItems(a.data.items || []);
        setStats(a.data.stats);
      } finally { setLoading(false); }
    })();
  }, []);

  // Group items by category
  const grouped = items.reduce((acc, it) => {
    (acc[it.category] = acc[it.category] || []).push(it);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="fg-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5 text-red-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="fg-title">
              Founder Approval <span className="italic gradient-text">Gate</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Acțiuni critice protejate de dublă verificare (email + SMS). Listă imutabilă, definită prin decizie founder.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="text-center text-stone-400 flex items-center justify-center gap-2 py-10">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
          </div>
        ) : (
          <>
            {/* STATUS BANNER */}
            <div className="rounded-2xl border border-amber-500/40 bg-amber-500/5 p-5 mb-6 flex items-start gap-3" data-testid="fg-status-banner">
              <ShieldQuestion className="w-6 h-6 text-amber-300 shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className="text-base font-semibold text-amber-200">Status: Foundation Only — Gate Inactive</span>
                  <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-200 font-mono">
                    Phase {status?.phase || "FG-0"}
                  </span>
                </div>
                <p className="text-xs text-stone-300 leading-relaxed">{status?.note}</p>
                <div className="mt-3 flex items-center gap-3 flex-wrap text-[11px]">
                  <span className="text-stone-500">Feature flag <code className="bg-white/10 px-1 rounded">{status?.feature_flag}</code> =</span>
                  <span className={`px-2 py-0.5 rounded-full font-mono ${status?.feature_flag_value ? "bg-emerald-500/15 text-emerald-300" : "bg-stone-500/15 text-stone-300"}`}>
                    {String(status?.feature_flag_value)}
                  </span>
                  <span className="text-stone-500">·</span>
                  <span className="text-stone-500">Enforcement</span>
                  <span className="px-2 py-0.5 rounded-full font-mono bg-red-500/15 text-red-300">
                    {status?.enforcement_active ? "ACTIVE" : "INACTIVE"}
                  </span>
                  <span className="text-stone-500">·</span>
                  <span className="text-stone-500">Next: {status?.next_phase}</span>
                </div>
              </div>
            </div>

            {/* STATS CARDS */}
            {stats && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <StatCard label="Acțiuni protejate" value={stats.total} icon={Lock} color="violet" />
                <StatCard label="Critical" value={stats.by_severity?.critical || 0} icon={ShieldAlert} color="red" />
                <StatCard label="High" value={stats.by_severity?.high || 0} icon={ShieldAlert} color="amber" />
                <StatCard label="Cer SMS" value={stats.requires_sms_count} icon={Settings} color="blue" />
              </div>
            )}

            {/* GROUPED LIST */}
            <div className="space-y-6">
              {Object.entries(grouped).map(([cat, actions]) => {
                const meta = CATEGORY_META[cat] || { label: cat, icon: Lock, color: "violet" };
                const Icon = meta.icon;
                return (
                  <div key={cat} data-testid={`fg-category-${cat}`}>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full border ${CAT_COLOR(meta.color)}`}>
                        <Icon className="w-3 h-3" /> {meta.label}
                      </span>
                      <span className="text-[10px] text-stone-500">{actions.length} acțiuni</span>
                    </div>
                    <div className="grid gap-2">
                      {actions.map((a) => (
                        <div key={a.slug} className="bg-[#0e0e10] border border-white/10 rounded-xl p-4" data-testid={`fg-action-${a.slug}`}>
                          <div className="flex items-start gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap mb-1">
                                <span className="font-mono text-[10px] text-stone-500">{a.slug}</span>
                                <span className={`inline-block text-[10px] uppercase px-1.5 py-0.5 rounded border ${SEVERITY_COLOR[a.severity]}`}>{a.severity}</span>
                                {a.requires_sms && (
                                  <span className="text-[10px] uppercase px-1.5 py-0.5 rounded border bg-blue-500/10 border-blue-500/30 text-blue-300">SMS</span>
                                )}
                              </div>
                              <div className="text-sm font-semibold text-white">{a.label}</div>
                              <div className="text-xs text-stone-400 mt-1">{a.description}</div>
                              {a.example_endpoints && a.example_endpoints.length > 0 && (
                                <div className="text-[10px] font-mono text-stone-500 mt-2 flex flex-wrap gap-1">
                                  {a.example_endpoints.map((e, i) => (
                                    <code key={i} className="bg-white/5 px-1.5 py-0.5 rounded">{e}</code>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* FOOTER NOTE */}
            <div className="mt-8 bg-violet-500/5 border border-violet-500/30 rounded-2xl p-4 text-xs text-violet-100 flex items-start gap-3" data-testid="fg-footer-note">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-violet-300" />
              <div>
                <strong>Phase FG-0 complete.</strong> Această pagină este pur informativă — nu poți modifica registry-ul din UI (e hardcoded în cod pentru imutabilitate).
                Următorul pas: <strong>Phase FG-1</strong> (Twilio integration) — necesită creare cont Twilio trial gratuit înainte.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon: Icon, color }) => (
  <div className={`rounded-xl border p-4 ${CAT_COLOR(color)}`}>
    <div className="flex items-center justify-between">
      <div className="text-[10px] uppercase tracking-wider">{label}</div>
      <Icon className="w-4 h-4 opacity-60" />
    </div>
    <div className="text-3xl font-mono mt-2 text-white">{value}</div>
  </div>
);

export default FounderGatePage;
