// Overview: Design System order — KPI (trend) → AI Insights → Grafice → Financiar → Panouri operaționale (progressive disclosure)
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Users, Briefcase, DollarSign, Scale, ChevronDown, Bot } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, AIInsightCard } from "../../design-system";
import { IncidentCadenceHeatmap } from "./IncidentCadenceHeatmap";
import { MorningBriefing } from "./MorningBriefing";
import { AutoMatchPanel } from "./AutoMatchPanel";
import { AIActivityStream } from "./AIActivityStream";
import { WeeklyBriefingControl } from "./WeeklyBriefingControl";
import { AutopilotActivityCard } from "./AutopilotActivityCard";
import { CostRoiCard } from "./CostRoiCard";

const halfTrend = (series, key) => {
  if (!series || series.length < 4) return null;
  const mid = Math.floor(series.length / 2);
  const prev = series.slice(0, mid).reduce((s, x) => s + (x[key] || 0), 0);
  const cur = series.slice(mid).reduce((s, x) => s + (x[key] || 0), 0);
  return prev ? Math.round((cur - prev) / prev * 100) : null;
};

export const AdminOverview = () => {
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [finance, setFinance] = useState(null);
  const [opsOpen, setOpsOpen] = useState(false);

  useEffect(() => {
    axios.get(`${API}/admin/stats`).then(r => setStats(r.data)).catch(() => {});
    axios.get(`${API}/admin/analytics?days=14`).then(r => setAnalytics(r.data)).catch(() => {});
    axios.get(`${API}/admin/finance/overview`).then(r => setFinance(r.data)).catch(() => {});
  }, []);

  const maxJobs = analytics?.series?.reduce((m, s) => Math.max(m, s.jobs_created, s.jobs_confirmed), 1) || 1;
  const jobsTrend = halfTrend(analytics?.series, "jobs_created");

  const insights = useMemo(() => {
    if (!analytics) return { bullets: [], alerts: [], recommendations: [] };
    const bullets = [], alerts = [], recommendations = [];
    if (jobsTrend !== null && jobsTrend !== 0) bullets.push(`Cererile au ${jobsTrend > 0 ? "crescut" : "scăzut"} cu ${Math.abs(jobsTrend)}% în ultima săptămână față de precedenta.`);
    const topSpec = analytics.top_specialists?.[0];
    if (topSpec) bullets.push(`Top specialist: ${topSpec.name} — ${topSpec.jobs} joburi, ${Number(topSpec.revenue).toLocaleString("ro")} RON.`);
    const topCat = [...(analytics.by_category || [])].sort((a, b) => b.value - a.value)[0];
    if (topCat) bullets.push(`Categoria «${topCat.name}» domină cererea (${topCat.value} cereri).`);
    if ((analytics.disputes?.open || 0) > 0) alerts.push(`${analytics.disputes.open} dispute deschise necesită triaj.`);
    if (finance && finance.escrow_held > 0) bullets.push(`${Number(finance.escrow_held).toLocaleString("ro")} RON securizați în escrow.`);
    if (jobsTrend !== null && jobsTrend < 0) recommendations.push("Cererile sunt în scădere — verifică funnel-ul de achiziție în Analytics & Growth.");
    if ((analytics.disputes?.open || 0) > 0) recommendations.push("Rulează AI Triage pe disputele deschise din secțiunea Dispute & NC.");
    return { bullets, alerts, recommendations };
  }, [analytics, finance, jobsTrend]);

  return (
    <div className="space-y-6">
      <MorningBriefing />

      {/* 1. KPI strategice */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={Users} label="Useri total" value={stats?.users ?? "—"} accent="info" testid="kpi-users" />
        <KpiCard icon={Briefcase} label="Joburi active" value={stats?.active_jobs ?? "—"} trend={jobsTrend} accent="warning" testid="kpi-jobs" />
        <KpiCard icon={DollarSign} label="GMV (14z)" value={analytics ? `${analytics.gmv.toLocaleString("ro")} RON` : "—"} accent="success" testid="kpi-gmv" />
        <KpiCard icon={Scale} label="Dispute deschise" value={analytics?.disputes?.open ?? 0} accent="critical" testid="kpi-disputes" />
      </div>

      {/* 2. AI Insights — obligatoriu după KPI */}
      <AIInsightCard bullets={insights.bullets} alerts={insights.alerts} recommendations={insights.recommendations}
        loading={!analytics} llmModule="overview" testid="admin-ai-insights" />

      {/* 3. Grafice */}
      <div className="grid lg:grid-cols-3 gap-4">
        <AdminCard className="lg:col-span-2" title="Activitate ultimele 14 zile" testid="chart-activity">
          <div className="h-64 flex items-end gap-1.5">
            {(analytics?.series || []).map((s, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
                <div className="w-full flex flex-col gap-0.5 items-stretch" style={{ height: "200px", justifyContent: "flex-end" }}>
                  <div className="bg-emerald-500 dark:bg-emerald-400 rounded-t transition-all hover:opacity-80"
                    style={{ height: `${(s.jobs_created / maxJobs) * 100}%`, minHeight: "2px" }} title={`${s.jobs_created} cereri`} />
                  <div className="bg-lime-400 dark:bg-lime-300 rounded-t opacity-80"
                    style={{ height: `${(s.jobs_confirmed / maxJobs) * 100}%`, minHeight: "2px" }} title={`${s.jobs_confirmed} confirmate`} />
                </div>
                <div className="text-[9px] text-slate-500 dark:text-slate-500 -rotate-45 origin-top-left whitespace-nowrap mt-1">{s.date}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-4 text-xs text-slate-600 dark:text-slate-400">
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded bg-emerald-500" /> Cereri create</div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded bg-lime-400" /> Confirmate</div>
          </div>
        </AdminCard>

        <AdminCard title="Top Specialiști" testid="top-specialists">
          <div className="space-y-3">
            {(analytics?.top_specialists || []).slice(0, 5).map((s, i) => (
              <div key={s.id} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-lime-400 flex items-center justify-center text-stone-900 text-sm font-bold">{i + 1}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{s.name}</div>
                  <div className="text-[11px] text-slate-500">{s.jobs} joburi · {Number(s.revenue).toLocaleString("ro")} RON</div>
                </div>
              </div>
            ))}
            {!analytics?.top_specialists?.length && <div className="text-sm text-slate-500">Date insuficiente</div>}
          </div>
        </AdminCard>
      </div>

      {/* 4. Financiar + categorii */}
      <div className="grid lg:grid-cols-2 gap-4">
        <AdminCard title="Finanțe — Sold global" testid="finance-overview-card">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider">Total în wallets</div>
              <div className="text-2xl font-bold mt-1">{(finance?.total_wallet || 0).toLocaleString("ro")} RON</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider">Escrow Held</div>
              <div className="text-2xl font-bold mt-1">{(finance?.escrow_held || 0).toLocaleString("ro")} RON</div>
            </div>
          </div>
          <div className="mt-5 pt-5 border-t border-slate-100 dark:border-slate-800">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Tranzacții 30z (per tip)</div>
            <div className="space-y-1.5">
              {(finance?.tx_by_type || []).map(t => (
                <div key={t.type} className="flex justify-between text-sm">
                  <span className="capitalize">{t.type}</span>
                  <span className="font-medium">{t.count}× · {Number(t.total).toLocaleString("ro")} RON</span>
                </div>
              ))}
            </div>
          </div>
        </AdminCard>

        <AdminCard title="Distribuție categorii" testid="category-distribution">
          <div className="space-y-2">
            {(analytics?.by_category || []).map(c => {
              const total = analytics.by_category.reduce((s, x) => s + x.value, 0) || 1;
              const pct = (c.value / total) * 100;
              return (
                <div key={c.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="capitalize">{c.name}</span>
                    <span className="text-slate-500">{c.value} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-lime-400" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
            {!analytics?.by_category?.length && <div className="text-sm text-slate-500">Niciun dată</div>}
          </div>
        </AdminCard>
      </div>

      {/* 5. Panouri operaționale AI — progressive disclosure (Hick's Law) */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden" data-testid="admin-ops-panels">
        <button onClick={() => setOpsOpen(o => !o)} data-testid="admin-ops-toggle"
          className="w-full flex items-center gap-2 px-4 py-3 text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50">
          <Bot className="w-4 h-4 text-violet-500" /> Panouri operaționale AI (Autopilot, Cost & ROI, Auto-Match, Briefing, Activitate)
          <ChevronDown className={`w-4 h-4 ml-auto text-slate-400 transition-transform ${opsOpen ? "rotate-180" : ""}`} />
        </button>
        {opsOpen && (
          <div className="p-4 space-y-6 border-t border-slate-100 dark:border-slate-700">
            <AutopilotActivityCard />
            <CostRoiCard />
            <AutoMatchPanel />
            <WeeklyBriefingControl />
            <AIActivityStream />
            <IncidentCadenceHeatmap />
          </div>
        )}
      </div>
    </div>
  );
};
