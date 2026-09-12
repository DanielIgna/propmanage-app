// BI-MOE Dashboard — Design System standard (TabBar → ActionBar → KPI → AI Insights → Tabele)
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  TrendingUp, AlertTriangle, DollarSign, Users, Target, Award,
  Activity, Crown, Wrench, UserPlus, FolderOpen, Wallet, Repeat, UserX,
} from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import {
  KpiCard, AIInsightCard, ChartCard, DataTable, DSSkeleton, DSBadge, EmptyState, ActionBar, TabBar, CARD,
} from "../../design-system";

const useFetch = (url) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    axios.get(url).then(r => setData(r.data)).catch(() => setData({ error: true })).finally(() => setLoading(false));
  }, [url]);
  return { data, loading };
};

const OverviewTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/overview`);
  const [insights, setInsights] = useState(null);
  useEffect(() => {
    axios.get(`${API}/admin/insights/rule?module=bi`).then(r => setInsights(r.data)).catch(() => {});
  }, []);
  if (loading) return <DSSkeleton kpis={8} blocks={0} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" hint="Reîncearcă cu butonul de refresh." />;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={Users} label="Total useri" value={data.total_users} accent="info" testid="kpi-total-users" />
        <KpiCard icon={Wrench} label="Specialiști activi" value={data.active_specialists} accent="ai" />
        <KpiCard icon={Users} label="Clienți activi" value={data.active_clients} accent="info" />
        <KpiCard icon={UserPlus} label="Useri noi (30z)" value={data.new_users_30d} accent="success" />
        <KpiCard icon={FolderOpen} label="Cereri noi (30z)" value={data.new_requests_30d} accent="info" />
        <KpiCard icon={Target} label="Finalizate (30z)" value={data.completed_30d} accent="success" />
        <KpiCard icon={AlertTriangle} label="Cereri deschise" value={data.open_requests} accent="warning" />
        <KpiCard icon={Wallet} label="Revenue 30z (RON)" value={Number(data.revenue_30d_ron || 0).toLocaleString("ro-RO")} accent="success" />
      </div>
      <AIInsightCard
        bullets={insights?.bullets || []} alerts={insights?.alerts || []}
        recommendations={insights?.recommendations || []}
        loading={!insights} llmModule="bi" testid="bi-ai-insights"
      />
    </div>
  );
};

const alertBadge = (a) => {
  if (!a) return null;
  const type = a === "no_specialists" ? "ERROR" : a === "undersupplied" ? "WARNING" : "NEW";
  return <DSBadge type={type}>{a.replace(/_/g, " ")}</DSBadge>;
};

const DemandTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/demand-index?days=30`);
  if (loading) return <DSSkeleton kpis={0} blocks={2} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <DataTable
        title="Top categorii (cereri vs specialiști)"
        columns={[
          { key: "category", label: "Categorie" },
          { key: "requests", label: "Cereri" },
          { key: "specialists", label: "Specialiști" },
          { key: "alert", label: "Alertă", sortable: false, render: r => alertBadge(r.alert) },
        ]}
        rows={(data.categories || []).slice(0, 20)}
        searchKeys={["category"]}
        exportName="bi-demand-categorii"
        emptyTitle="Fără cereri în perioadă"
        testid="demand-categories"
      />
      <DataTable
        title="Top zone"
        columns={[
          { key: "zone", label: "Zonă" },
          { key: "requests", label: "Cereri" },
        ]}
        rows={(data.zones || []).slice(0, 20)}
        searchKeys={["zone"]}
        exportName="bi-demand-zone"
        emptyTitle="Fără date pe zone"
        testid="demand-zones"
      />
    </div>
  );
};

const FeesTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/fee-analytics?days=30`);
  if (loading) return <DSSkeleton kpis={4} blocks={1} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={Target} label="Total oferte" value={data.total_offers} accent="info" />
        <KpiCard icon={TrendingUp} label="Win rate" value={`${data.win_rate_pct}%`} accent="success" />
        <KpiCard icon={DollarSign} label="Avg fee câștigat" value={`${data.avg_fee_won_ron} RON`} accent="info" />
        <KpiCard icon={Wallet} label="Revenue (RON)" value={Number(data.revenue_from_fees_ron || 0).toLocaleString("ro-RO")} accent="success" />
      </div>
      <AIInsightCard
        bullets={(data.recommendations || []).map(r => r.msg)}
        actionLabel="Recomandări auto-analizate"
        testid="fee-recommendations"
      />
    </div>
  );
};

const FunnelTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/conversion-funnel?days=30`);
  if (loading) return <DSSkeleton kpis={0} blocks={1} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  return (
    <ChartCard title={`Conversion Funnel (${data.window_days} zile)`} subtitle={`Completion rate: ${data.completion_rate_pct}% · Abandonate: ${data.abandoned}`} testid="funnel-chart">
      <div className="space-y-3">
        {data.steps.map((s, i) => (
          <div key={s.name} data-testid={`funnel-step-${i}`}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-600 dark:text-slate-300">{s.name}</span>
              <span className="text-slate-400 tabular-nums">{s.count} · <strong className="text-blue-600 dark:text-blue-400">{s.pct_of_total}%</strong></span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full" style={{ width: `${s.pct_of_total}%` }} />
            </div>
          </div>
        ))}
      </div>
    </ChartCard>
  );
};

const SpecialistsTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/specialist-performance?limit=10`);
  if (loading) return <DSSkeleton kpis={0} blocks={2} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  const cols = [
    { key: "name", label: "Specialist" },
    { key: "rating", label: "Rating", render: r => <span className="tabular-nums">★{r.rating}</span> },
    { key: "performance_score", label: "Scor", render: r => <span className="font-bold tabular-nums">{r.performance_score}</span> },
  ];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <DataTable title="🏆 Top 10 performance" columns={cols} rows={data.top || []} emptyTitle="Fără date de performanță" testid="spec-top" />
      <DataTable
        title="⚠️ Bottom 10 (verifică manual)"
        columns={[...cols.slice(0, 2), { key: "low_rating_flag", label: "Flag", sortable: false, render: r => r.low_rating_flag ? <DSBadge type="ERROR">LOW</DSBadge> : null }, cols[2]]}
        rows={data.bottom || []}
        emptyTitle="Fără date"
        testid="spec-bottom"
      />
    </div>
  );
};

const CandidatesTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/premium-candidates`);
  if (loading) return <DSSkeleton kpis={0} blocks={1} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  return (
    <div className="space-y-3" data-testid="premium-candidates-list">
      <p className="text-xs text-slate-400">
        Praguri: {data.thresholds?.min_completed_jobs} joburi · rating {data.thresholds?.min_rating} · {data.thresholds?.min_reviews} recenzii
      </p>
      <DataTable
        title="Candidați PREMIUM (gata sau aproape)"
        columns={[
          { key: "name", label: "Nume" },
          { key: "current_tier", label: "Tier curent", render: r => <DSBadge type={r.current_tier === "PREMIUM" ? "LIVE" : "ACTIVE"}>{r.current_tier}</DSBadge> },
          { key: "rating", label: "Rating", render: r => <span className="tabular-nums">★{r.rating}</span> },
          { key: "completed_jobs", label: "Joburi" },
          { key: "reviews", label: "Reviews" },
          { key: "overall_pct", label: "Progres", render: r => (
            <span className={`font-bold ${r.ready ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
              {r.overall_pct}% {r.ready && "✓ READY"}
            </span>
          ) },
        ]}
        rows={data.items || []}
        emptyTitle="Niciun candidat"
        emptyHint="Apar candidații care ating cel puțin 60% din praguri."
        testid="premium-candidates-table"
      />
    </div>
  );
};

const AlertsTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/alerts`);
  if (loading) return <DSSkeleton kpis={0} blocks={1} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  if ((data.items || []).length === 0) {
    return <EmptyState icon={Activity} title="🟢 Niciun alert" hint="Platforma rulează normal." testid="alerts-empty" />;
  }
  return (
    <div className="space-y-3" data-testid="alerts-list">
      {data.items.map((a, i) => (
        <div key={i} className={`${CARD} p-4 ${a.severity === "high" ? "border-red-300 dark:border-red-500/40" : "border-amber-300 dark:border-amber-500/40"}`} data-testid={`alert-${i}`}>
          <div className="flex items-start gap-3">
            <AlertTriangle className={`w-5 h-5 mt-0.5 shrink-0 ${a.severity === "high" ? "text-red-500" : "text-amber-500"}`} />
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] uppercase tracking-wider text-slate-400">{a.type.replace(/_/g, " ")}</span>
                <DSBadge type={a.severity === "high" ? "ERROR" : "WARNING"}>{a.severity}</DSBadge>
              </div>
              <div className="text-sm text-slate-700 dark:text-slate-200">{a.msg}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const ClientsTab = () => {
  const { data, loading } = useFetch(`${API}/admin/bi/client-analysis?days=90`);
  if (loading) return <DSSkeleton kpis={4} blocks={0} />;
  if (data?.error) return <EmptyState icon={AlertTriangle} title="Eroare la încărcare" />;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KpiCard icon={Users} label="Clienți cu cereri" value={data.total_clients_with_requests} accent="info" />
      <KpiCard icon={Target} label="Avg cereri/client" value={data.avg_requests_per_client} accent="info" />
      <KpiCard icon={Repeat} label="Repeat clients" value={data.repeat_clients} accent="success" />
      <KpiCard icon={UserX} label="One-time clients" value={data.one_time_clients} accent="warning" />
    </div>
  );
};

export const BIMoePage = () => {
  const [tab, setTab] = useState("overview");
  const [bump, setBump] = useState(0);
  return (
    <AdminLayoutMetronic active="bi_moe" title="Business Intelligence" subtitle="Analize agregate & recomandări · READ-ONLY — nicio decizie automată">
      <div className="space-y-6" data-testid="bi-moe-page">
        <div className="flex flex-wrap items-center gap-2">
          <TabBar
            tabs={[
              ["overview", "Overview", Activity],
              ["demand", "Demand Index", TrendingUp],
              ["fees", "Fee Analytics", DollarSign],
              ["funnel", "Funnel", Target],
              ["specialists", "Performance", Award],
              ["candidates", "Premium", Crown],
              ["alerts", "Alerts", AlertTriangle],
              ["clients", "Clienți", Users],
            ]}
            active={tab} onChange={setTab} testidPrefix="bi-tab"
          />
          <div className="ml-auto">
            <ActionBar onRefresh={() => setBump(b => b + 1)} testidPrefix="bi" />
          </div>
        </div>
        <div key={bump}>
          {tab === "overview" && <OverviewTab />}
          {tab === "demand" && <DemandTab />}
          {tab === "fees" && <FeesTab />}
          {tab === "funnel" && <FunnelTab />}
          {tab === "specialists" && <SpecialistsTab />}
          {tab === "candidates" && <CandidatesTab />}
          {tab === "alerts" && <AlertsTab />}
          {tab === "clients" && <ClientsTab />}
        </div>
      </div>
    </AdminLayoutMetronic>
  );
};

export default BIMoePage;
