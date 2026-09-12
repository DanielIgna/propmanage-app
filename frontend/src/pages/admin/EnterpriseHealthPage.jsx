// Enterprise Health (D122) — scorul de sănătate al întregii companii, 11 domenii evidence-based
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { HeartPulse, Loader2, RefreshCcw, AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";
import axios from "axios";
import { EhDomainCard } from "./EhDomainCard";
import { InspectorButton } from "../../components/founder/InspectorButton";

const API = process.env.REACT_APP_BACKEND_URL;

const Trend = ({ v }) => {
  if (v == null) return <Minus className="w-3.5 h-3.5 text-stone-600" />;
  if (v > 0.5) return <span className="inline-flex items-center gap-0.5 text-emerald-400 text-xs"><TrendingUp className="w-3.5 h-3.5" />+{v}</span>;
  if (v < -0.5) return <span className="inline-flex items-center gap-0.5 text-red-400 text-xs"><TrendingDown className="w-3.5 h-3.5" />{v}</span>;
  return <span className="text-stone-500 text-xs">stabil</span>;
};

const AlertCard = ({ alert }) => (
  <div className={`rounded-2xl border p-5 ${alert.severity === "critical" ? "border-red-500/30 bg-red-500/5" : "border-amber-500/25 bg-amber-500/5"}`}
    data-testid={`eh-alert-${alert.domain}`}>
    <div className="flex items-center justify-between gap-3 mb-2">
      <div className="flex items-center gap-2">
        <AlertTriangle className={`w-4 h-4 ${alert.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
        <span className="font-serif text-lg">{alert.label}</span>
        <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full ${alert.severity === "critical" ? "bg-red-500/15 text-red-300" : "bg-amber-500/15 text-amber-300"}`}>
          {alert.severity === "critical" ? "Critic" : "Atenție"} · {alert.score}
        </span>
      </div>
    </div>
    <div className="text-xs text-stone-400 mb-1"><span className="text-stone-500 uppercase tracking-wide text-[10px]">Cauză:</span> {alert.cause}</div>
    <div className="text-xs text-stone-400 mb-3"><span className="text-stone-500 uppercase tracking-wide text-[10px]">Impact:</span> {alert.business_impact}</div>
    <div className="space-y-1.5 mb-3">
      {alert.top_actions.map((a, i) => (
        <div key={i} className="flex items-start justify-between gap-3 text-xs bg-white/[0.03] rounded-lg px-3 py-2">
          <span className="text-stone-200">{i + 1}. {a.action}</span>
          {a.estimated_gain_pts > 0 && <span className="text-emerald-400 shrink-0">+{a.estimated_gain_pts}p</span>}
        </div>
      ))}
    </div>
    <div className="text-[11px] text-[#d4ff3a]">{alert.estimated_effect}</div>
  </div>
);

export default function EnterpriseHealthPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/enterprise-health`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se calculează Enterprise Health...</div>;
  if (!data) return (
    <div className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center text-stone-400 gap-4" data-testid="eh-error">
      <span>Nu am putut calcula Enterprise Health.</span>
      <button onClick={load} className="pm-btn pm-btn-secondary"><RefreshCcw className="w-3.5 h-3.5" /> Încearcă din nou</button>
    </div>
  );

  const o = data.overall;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3" data-testid="eh-title">
              <HeartPulse className="w-8 h-8 text-[#d4ff3a]" /> Enterprise Health
            </h1>
            <p className="text-sm text-stone-400 mt-1">Pulsul operațional al companiei. Fiecare scor e calculat doar din dovezi măsurabile — click pe domeniu pentru formula completă (D151).</p>
          </div>
          <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="eh-refresh"><RefreshCcw className="w-3.5 h-3.5" /> Recalculează</button>
        </div>

        {/* Overall score */}
        <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-8 mb-8 flex items-center justify-between flex-wrap gap-6" data-testid="eh-overall">
          <div className="flex items-center gap-6">
            <div className="relative">
              <div className="font-serif text-7xl" style={{ color: o.band.color }} data-testid="eh-overall-score">{Math.round(o.score)}</div>
              <div className="text-xs text-stone-500 text-center">/ 100</div>
            </div>
            <div>
              <div className="text-xl font-medium" style={{ color: o.band.color }}>{o.band.label}</div>
              <div className="text-xs text-stone-400 mt-1 flex items-center gap-2">
                {o.previous != null && <span>Anterior: {o.previous}</span>}
                <Trend v={o.trend_30d} />
              </div>
            </div>
          </div>
          <div className="text-right text-xs text-stone-500">
            {data.enterprise_score && (
              <div className="mb-2" data-testid="eh-enterprise-score" title={data.enterprise_score.formula}>
                <span className="text-stone-400">Enterprise Score: </span>
                <span className="font-serif text-2xl" style={{ color: data.enterprise_score.band.color }}>{Math.round(data.enterprise_score.score)}</span>
              </div>
            )}
            <div>{data.alerts.length} {data.alerts.length === 1 ? "domeniu sub prag" : "domenii sub prag"}</div>
            <div className="mt-1">Actualizat: {String(data.generated_at).slice(0, 16).replace("T", " ")}</div>
            <div className="mt-2 flex justify-end"><InspectorButton widgetId="health.overall" /></div>
          </div>
        </div>

        {/* Domains */}
        <div className="grid md:grid-cols-2 gap-3 mb-10" data-testid="eh-domains">
          {data.domains.map(d => <EhDomainCard key={d.key} domain={d} onChanged={load} />)}
        </div>

        {/* Alerts */}
        {data.alerts.length > 0 && (
          <div data-testid="eh-alerts">
            <h2 className="font-serif text-2xl mb-4 flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-amber-400" /> Alerte — sub pragul de sănătate</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {data.alerts.map(a => <AlertCard key={a.domain} alert={a} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
