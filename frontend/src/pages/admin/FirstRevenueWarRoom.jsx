import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Target, CheckCircle2, Circle, AlertTriangle, RefreshCcw, Loader2,
  CreditCard, Mail, ShoppingCart, Banknote, TrendingUp, User, Wrench, Sun
} from "lucide-react";
import axios from "axios";
import { InspectorButton } from "../../components/founder/InspectorButton";

const API = process.env.REACT_APP_BACKEND_URL;

const StatusPill = ({ ok, label }) => (
  <span className={`inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full font-medium ${ok ? "bg-emerald-500/15 text-emerald-300" : "bg-red-500/15 text-red-300"}`}>
    {ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
    {label}
  </span>
);

const Milestone = ({ m }) => (
  <div className={`rounded-2xl border p-4 ${m.done ? "bg-emerald-500/5 border-emerald-500/30" : "bg-white/[0.02] border-white/10"}`} data-testid={`milestone-${m.id}`}>
    <div className="flex items-start gap-3">
      {m.done
        ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        : <Circle className="w-5 h-5 text-stone-600 shrink-0 mt-0.5" />}
      <div>
        <div className={`text-sm font-medium ${m.done ? "text-emerald-300" : "text-stone-300"}`}>{m.label}</div>
        <div className="text-[11px] text-stone-500 mt-1">
          {m.done ? (m.at ? new Date(m.at).toLocaleString("ro-RO") : "Realizat") : m.detail}
        </div>
      </div>
    </div>
  </div>
);

const BlockerCard = ({ b }) => (
  <div className={`rounded-xl border p-3 ${b.severity === "critical" ? "border-red-500/30 bg-red-500/5" : "border-amber-500/30 bg-amber-500/5"}`} data-testid={`blocker-${b.id}`}>
    <div className="flex items-center gap-2 mb-1">
      <AlertTriangle className={`w-4 h-4 ${b.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
      <span className="text-sm font-medium">{b.title}</span>
      {b.external && <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded">EXTERN</span>}
    </div>
    <p className="text-xs text-stone-400 pl-6">{b.action}</p>
  </div>
);

export default function FirstRevenueWarRoom() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/war-room`, { withCredentials: true });
      setData(r.data);
    } catch (err) {
      console.error("War room load failed", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading || !data) {
    return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă War Room...</div>;
  }

  const p = data.pipeline || {};
  const integ = data.integrations || {};

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight flex items-center gap-3" data-testid="war-room-title">
              <Target className="w-9 h-9 text-[#d4ff3a]" /> First Revenue <span className="italic gradient-text">War Room</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2">Directiva 059/068 · O singură misiune: prima plată reală.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="font-serif text-3xl" data-testid="war-room-days">{data.days_since_start}</div>
              <div className="text-[10px] text-stone-500 uppercase tracking-wider">zile în misiune</div>
            </div>
            <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="war-room-refresh">
              <RefreshCcw className="w-3.5 h-3.5" /> Refresh
            </button>
          </div>
        </div>

        {/* Mission banner */}
        <div className={`rounded-3xl border p-6 mb-8 ${data.mission_complete ? "bg-emerald-500/10 border-emerald-500/40" : "bg-[#d4ff3a]/5 border-[#d4ff3a]/30"}`} data-testid="mission-banner">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-stone-400 mb-1">Misiune</div>
              <div className="font-serif text-2xl">
                {data.mission_complete ? "🏆 PRIMA PLATĂ REALĂ PRIMITĂ — Freeze + Executive Review" : "💰 Generează prima plată reală"}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <StatusPill ok={integ.stripe?.ok} label={`Stripe: ${integ.stripe?.mode?.toUpperCase()}`} />
              <StatusPill ok={integ.resend?.ok} label={`Resend: ${integ.resend?.status}`} />
              <StatusPill ok={integ.checkout?.ok} label="Checkout" />
            </div>
          </div>
        </div>

        {/* Pipeline stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
          {[
            { icon: Banknote, v: `${Number(p.revenue_real_ron || 0).toLocaleString("ro-RO")} RON`, l: "Venit REAL", c: "emerald" },
            { icon: CreditCard, v: p.orders_paid_real || 0, l: "Plăți reale", c: "lime" },
            { icon: ShoppingCart, v: p.orders_pending || 0, l: "Comenzi pending", c: "amber" },
            { icon: Mail, v: (p.inquiries_new || 0) + (p.external_requests_new || 0), l: "Leads noi", c: "cyan" },
            { icon: TrendingUp, v: `${Number(p.commission_net_ron || 0).toLocaleString("ro-RO")} RON`, l: "Comision net", c: "violet" },
            { icon: CreditCard, v: `${Number(p.revenue_demo_ron || 0).toLocaleString("ro-RO")} RON`, l: "Venit demo (test)", c: "stone" },
          ].map((s, i) => (
            <div key={i} className="pm-stat-card" data-testid={`war-stat-${i}`}>
              <div className={`pm-stat-icon-badge bg-${s.c}-500/15 text-${s.c}-400 border border-${s.c}-500/30`}><s.icon className="w-5 h-5" /></div>
              <div className="font-serif text-2xl mb-1">{s.v}</div>
              <div className="text-xs text-stone-400">{s.l}</div>
            </div>
          ))}
        </div>

        {/* Mission 100 — D109 */}
        <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6 mb-10" data-testid="mission-100">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
            <h2 className="font-serif text-2xl flex items-center gap-2"><Target className="w-5 h-5 text-[#d4ff3a]" /> Mission 100 <InspectorButton widgetId="warroom.mission100" /></h2>
            <div className="text-sm text-stone-400">Progres global: <span className="text-[#d4ff3a] font-semibold" data-testid="mission-100-progress">{data.mission_100?.progress_pct ?? 0}%</span></div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {(data.mission_100?.targets || []).map(t => {
              const pct = Math.min(100, Math.round((t.actual / t.target) * 100));
              return (
                <div key={t.id} data-testid={`m100-${t.id}`}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-stone-400">{t.label}</span>
                    <span className={t.actual >= t.target ? "text-emerald-400" : "text-stone-300"}>{t.actual}/{t.target}</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${t.actual >= t.target ? "bg-emerald-400" : "bg-[#d4ff3a]"}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Milestones */}
        <h2 className="font-serif text-2xl mb-4">Milestones — „The Firsts"</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 mb-10" data-testid="milestones-grid">
          {(data.milestones || []).map(m => <Milestone key={m.id} m={m} />)}
        </div>

        {/* Blockers */}
        <div className="grid lg:grid-cols-2 gap-6 mb-10">
          <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="founder-actions">
            <h3 className="font-serif text-xl mb-4 flex items-center gap-2"><User className="w-5 h-5 text-red-400" /> Acțiuni Founder ({(data.founder_actions || []).length})</h3>
            <div className="space-y-3">
              {(data.founder_actions || []).length === 0
                ? <p className="text-sm text-stone-500">Nicio acțiune blocantă la Founder. 🎉</p>
                : data.founder_actions.map(b => <BlockerCard key={b.id} b={b} />)}
            </div>
          </div>
          <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="dev-actions">
            <h3 className="font-serif text-xl mb-4 flex items-center gap-2"><Wrench className="w-5 h-5 text-amber-400" /> Acțiuni Ops/Dev ({(data.dev_actions || []).length})</h3>
            <div className="space-y-3">
              {(data.dev_actions || []).length === 0
                ? <p className="text-sm text-stone-500">Nimic blocant pe partea tehnică/operațională.</p>
                : data.dev_actions.map(b => <BlockerCard key={b.id} b={b} />)}
            </div>
          </div>
        </div>

        {/* Morning briefing */}
        <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="morning-briefing">
          <h3 className="font-serif text-xl mb-4 flex items-center gap-2"><Sun className="w-5 h-5 text-[#d4ff3a]" /> Briefing de dimineață</h3>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { q: "Ce poate genera venit azi?", a: data.briefing?.q1_revenue_today },
              { q: "Ce crește încrederea azi?", a: data.briefing?.q2_trust_today },
              { q: "Ce simplificăm azi?", a: data.briefing?.q3_simplicity_today },
            ].map((x, i) => (
              <div key={i} className="bg-white/[0.03] border border-white/10 rounded-2xl p-4">
                <div className="text-xs text-[#d4ff3a] font-medium mb-2">{x.q}</div>
                <p className="text-sm text-stone-300">{x.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
