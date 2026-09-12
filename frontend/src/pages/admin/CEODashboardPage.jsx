// CEODashboardPage — vedere strategică doar pentru owner (super-admin).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Crown, TrendingUp, Wallet, Lock, Users, Inbox, AlertTriangle, RefreshCw, ExternalLink, Repeat, Gem, ShieldCheck, Layers, Home } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton, EmptyState } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });
const lei = (v) => `${(v ?? 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} lei`;

const COLOR = { green: "#10b981", yellow: "#f59e0b", red: "#f43f5e" };

export default function CEODashboardPage() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await ax.get("/admin/ceo");
      setData(r.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const rev = data?.revenue || {};
  const c = 2 * Math.PI * 40;

  return (
    <AdminLayoutMetronic
      title="CEO Dashboard"
      subtitle="Vedere strategică pentru owner — Business Score, Revenue, Cash Flow, prioritățile AI"
    >
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : err ? (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-sm" data-testid="ceo-error">
          <AlertTriangle className="w-4 h-4 inline mr-1.5" />{err}
        </div>
      ) : (
        <div className="space-y-6" data-testid="ceo-dashboard-root">
          <div className="grid lg:grid-cols-4 gap-4">
            <AdminCard className="lg:col-span-1" title={<span className="flex items-center gap-2"><Crown className="w-4 h-4 text-lime-500" /> Business Score</span>} testid="ceo-score">
              <div className="flex flex-col items-center">
                <svg width="110" height="110" viewBox="0 0 110 110">
                  <circle cx="55" cy="55" r="40" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-100 dark:text-slate-700" />
                  <circle cx="55" cy="55" r="40" fill="none" stroke={COLOR[data?.business_color] || COLOR.yellow} strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={c} strokeDashoffset={c * (1 - (data?.business_score || 0) / 100)} transform="rotate(-90 55 55)" />
                  <text x="55" y="62" textAnchor="middle" className="fill-slate-900 dark:fill-white" fontSize="26" fontWeight="900">{Math.round(data?.business_score ?? 0)}</text>
                </svg>
                <a href="/admin/business-health" className="text-[11px] text-lime-700 dark:text-lime-300 font-bold underline mt-1" data-testid="ceo-health-link">Vezi Business Health →</a>
              </div>
            </AdminCard>

            <div className="lg:col-span-3 grid grid-cols-2 lg:grid-cols-3 gap-4">
              <KpiCard icon={Wallet}  label="Revenue 30z" value={lei(rev.last_30d)} trend={rev.growth_pct != null ? `${rev.growth_pct > 0 ? "+" : ""}${rev.growth_pct}%` : null} accent="success" testid="ceo-kpi-revenue" />
              <KpiCard icon={TrendingUp} label="Cash Flow" value={data?.cash_flow_status || "—"} accent={data?.cash_flow_status === "OK" ? "success" : "warning"} testid="ceo-kpi-cashflow" />
              <KpiCard icon={Lock}    label="Escrow blocat" value={lei(data?.escrow_held?.amount)} accent="warning" testid="ceo-kpi-escrow" />
              <KpiCard icon={Repeat} label="MRR / ARR" value={`${lei(data?.mrr_ron)} / ${lei(data?.arr_ron)}`} accent="ai" testid="ceo-kpi-mrr" />
              <KpiCard icon={Inbox}   label="Cereri noi 24h" value={data?.new_requests_24h ?? 0} accent="info" testid="ceo-kpi-requests" />
              <KpiCard icon={Users}   label="Utilizatori noi 24h" value={data?.new_users_24h ?? 0} accent="neutral" testid="ceo-kpi-users" />
            </div>
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Gem className="w-4 h-4 text-lime-500" /> Value Loop — valoarea creată în ecosistem</span>}
            testid="ceo-value-loop"
          >
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              <div className="p-3 rounded-xl bg-slate-900 dark:bg-slate-800 text-white" data-testid="ceo-vl-pvi">
                <div className="text-[10px] font-black uppercase tracking-wide text-lime-400 flex items-center gap-1"><Gem className="w-3 h-3" /> PVI mediu</div>
                <div className="text-2xl font-black mt-1">{data?.value_loop?.avg_pvi ?? 0}<span className="text-sm text-slate-400 font-semibold">/100</span></div>
                <div className="text-[10px] text-slate-400">Property Value Index · maturitatea documentării</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="ceo-vl-scored">
                <div className="text-[10px] font-black uppercase tracking-wide text-slate-400 flex items-center gap-1"><Home className="w-3 h-3" /> Proprietăți scorate</div>
                <div className="text-2xl font-black mt-1 text-slate-900 dark:text-white">{data?.value_loop?.properties_scored ?? 0}<span className="text-sm text-slate-400 font-semibold">/{data?.value_loop?.properties_total ?? 0}</span></div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="ceo-vl-warranties">
                <div className="text-[10px] font-black uppercase tracking-wide text-slate-400 flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Garanții active</div>
                <div className="text-2xl font-black mt-1 text-slate-900 dark:text-white">{data?.value_loop?.active_warranties ?? 0}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="ceo-vl-enrichments">
                <div className="text-[10px] font-black uppercase tracking-wide text-slate-400 flex items-center gap-1"><Layers className="w-3 h-3" /> Îmbogățiri Twin</div>
                <div className="text-2xl font-black mt-1 text-slate-900 dark:text-white">{data?.value_loop?.twin_enrichments ?? 0}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="ceo-vl-maturity">
                <div className="text-[10px] font-black uppercase tracking-wide text-slate-400 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Twin Maturity mediu</div>
                <div className="text-2xl font-black mt-1 text-slate-900 dark:text-white">L{data?.maturity?.avg_level ?? 0}<span className="text-sm text-slate-400 font-semibold">/5</span></div>
                <div className="text-[10px] text-slate-400">{data?.maturity?.scanned ?? 0} proprietăți evaluate{data?.property_risks ? ` · ${data.property_risks.active_risks} riscuri active` : ""}</div>
              </div>
            </div>
          </AdminCard>

          <div className="grid lg:grid-cols-2 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-lime-500" /> AI spune: prioritățile tale azi</span>}
              action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="ceo-refresh">Refresh</DSButton>}
              testid="ceo-priorities"
            >
              {!(data?.top_priorities || []).length && (
                <EmptyState icon={Crown} title="Nicio prioritate generată" hint="Generează recomandările din AI Command Center — top 3 nerezolvate apar automat aici." />
              )}
              <div className="space-y-2">
                {(data?.top_priorities || []).map((p, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid={`ceo-priority-${i}`}>
                    <span className="w-6 h-6 rounded-full bg-lime-400 text-slate-900 text-xs font-black flex items-center justify-center shrink-0">{i + 1}</span>
                    <div className="flex-1">
                      <div className="text-sm font-bold text-slate-900 dark:text-white">{p.action}</div>
                      <div className="text-xs text-slate-500">{p.why}</div>
                    </div>
                    {p.link && <a href={p.link} className="shrink-0 p-1.5 text-slate-400 hover:text-lime-600" data-testid={`ceo-priority-open-${i}`}><ExternalLink className="w-4 h-4" /></a>}
                  </div>
                ))}
              </div>
            </AdminCard>

            <AdminCard title="Departamente — puls rapid" testid="ceo-departments">
              <div className="grid grid-cols-2 gap-2">
                {(data?.departments || []).map((d) => (
                  <div key={d.key} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={`ceo-dept-${d.key}`}>
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{d.label}</span>
                    <span className="text-sm font-black" style={{ color: COLOR[d.color] }}>{d.score}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 text-[11px] text-slate-500">
                Trend marketplace 7z: <b>{data?.marketplace_trend_pct != null ? `${data.marketplace_trend_pct > 0 ? "+" : ""}${data.marketplace_trend_pct}%` : "—"}</b> · {data?.warnings_count ?? 0} alerte active în Command Center
              </div>
            </AdminCard>
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
