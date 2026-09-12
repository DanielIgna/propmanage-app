import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  BarChart3, Users, MousePointerClick, UserPlus, Building2, Wallet, Plus, QrCode, Trash2,
  Link2, Megaphone, Settings2, CheckCircle2, Flame, FlaskConical, Repeat, TrendingDown, MessageCircle,
  GitCompareArrows, X, Workflow, TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar, PieChart, Pie, Cell, LabelList, ReferenceLine, Legend,
} from "recharts";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { toast } from "sonner";
import {
  KpiCard, AIInsightCard, ChartCard, DataTable, EmptyState, DSSkeleton, ActionBar, TabBar,
  DSButton, DSBadge, CHART, CHART_COLORS,
} from "../../design-system";
import { HeatmapTab } from "./analytics/HeatmapTab";
import { BounceTab } from "./analytics/BounceTab";
import { RetentionTab } from "./analytics/RetentionTab";
import { AbTestingTab } from "./analytics/AbTestingTab";
import { WhatsAppTab } from "./analytics/WhatsAppTab";

const SOURCE_COLORS = { whatsapp: "#25D366", facebook: "#1877F2", google: "#EA4335", direct: "#64748b", qr: "#8b5cf6", admin: "#f59e0b", other: "#0ea5e9" };

// Presete extinse — de la Azi la 12 luni (istoric persistent pentru comparații)
const PERIOD_PRESETS = [
  ["day", "Azi"], ["week", "7z"], ["month", "30z"],
  ["60d", "60z"], ["90d", "90z"], ["6m", "6L"], ["12m", "12L"], ["ytd", "YTD"],
];

const trendOf = (k, kp, key) => {
  const prev = kp?.[key];
  if (!prev) return null;
  return Math.round(((k[key] ?? 0) - prev) / prev * 100);
};

// Format X-axis adaptiv în funcție de granularitate (day/week/month)
const formatBucket = (day, granularity) => {
  if (!day) return "";
  if (granularity === "month") return day.slice(0, 7); // YYYY-MM
  return day.slice(5); // MM-DD (day/week)
};

// ── Funnel comercial (VISITOR→CLIENT→CERERE→SPECIALIST→FINALIZAT) ──────────────
// Reutilizează trackerul first-party (semnale intent_*) + verificare încrucișată cu db.requests.
const CommercialFunnelTab = ({ data }) => {
  if (!data) return <DSSkeleton kpis={4} blocks={2} />;
  const kpi = data.kpi || {};
  const bc = data.backend_check || {};
  const stages = data.stages || [];
  return (
    <div className="space-y-6" data-testid="ag-commercial-funnel">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={Users} label="Client pe /client" value={kpi.client_visitors ?? 0} accent="info" testid="ag-cf-opened" />
        <KpiCard icon={Workflow} label="Au început o cerere" value={kpi.started ?? 0} accent="warning" testid="ag-cf-started" />
        <KpiCard icon={CheckCircle2} label="Au creat o cerere reală" value={kpi.created ?? 0} accent="success" testid="ag-cf-created" />
        <KpiCard icon={TrendingUp} label="Conversie /client → cerere" value={`${kpi.opened_to_created_pct ?? 0}%`} accent="ai" testid="ag-cf-conversion" />
      </div>

      {/* Strip conversii intermediare — răspunsul direct la întrebarea Fondatorului */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <DSBadge variant="info">Intrat → început: {kpi.opened_to_started_pct ?? 0}%</DSBadge>
        <DSBadge variant="success">Început → cerere: {kpi.started_to_created_pct ?? 0}%</DSBadge>
        <DSBadge variant="ai">Intrat → cerere reală: {kpi.opened_to_created_pct ?? 0}%</DSBadge>
      </div>

      <ChartCard title="Funnel comercial: /client → cerere → specialist → finalizat" testid="ag-cf-chart">
        {stages.every(s => (s.count || 0) === 0) ? (
          <EmptyState title="Fără evenimente încă." hint="Trackerul colectează etapele pe măsură ce clienții și specialiștii folosesc fluxul." />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stages} layout="vertical" margin={{ left: 60 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={175} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={22}>
                <LabelList dataKey="count" position="right" style={{ fontSize: 12, fontWeight: 700 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <div className="rounded-2xl border border-slate-200 bg-white p-4" data-testid="ag-cf-backend-check">
        <div className="text-sm font-bold text-slate-900 mb-3">Verificare încrucișată cu backend-ul (db.requests · SSOT)</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><div className="text-slate-500 text-xs">Cereri reale create</div><div className="font-black text-slate-900" data-testid="ag-cf-real-created">{bc.requests_created_real ?? 0}</div></div>
          <div><div className="text-slate-500 text-xs">Semnal request_created</div><div className="font-black text-slate-900">{bc.signal_request_created ?? 0}</div></div>
          <div><div className="text-slate-500 text-xs">Cereri confirmate</div><div className="font-black text-slate-900">{bc.requests_confirmed_real ?? 0}</div></div>
          <div><div className="text-slate-500 text-xs">Diferență semnal − real</div><div className="font-black text-slate-900">{bc.created_delta ?? 0}</div></div>
        </div>
        <p className="text-[11px] text-slate-400 mt-3">
          „Cereri reale create" e sursa de adevăr (db.requests). Semnalul „request_created" vine din trackerul first-party
          (doar vizitatori cu tracking activ), deci poate diferi de realitate (conturi demo/seed sau tracker blocat de browser).
        </p>
      </div>
    </div>
  );
};

export default function AnalyticsGrowthPage() {
  const [tab, setTab] = useState("overview");
  const [period, setPeriod] = useState("week");
  const [overview, setOverview] = useState(null);
  const [commercialFunnel, setCommercialFunnel] = useState(null);
  const [insights, setInsights] = useState(null);
  const [pages, setPages] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [integrations, setIntegrations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", administrator: "", association: "", apartments_count: 0, channel: "whatsapp", recipients_count: 0 });
  // markers campanii pe grafic "Trafic zilnic"
  const [campaignMarkers, setCampaignMarkers] = useState([]);
  // comparator campanii (2-3 side-by-side)
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelectedIds, setCompareSelectedIds] = useState([]);
  const [compareData, setCompareData] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [o, p, c, i, ins, m, cf] = await Promise.all([
        axios.get(`${API}/admin/analytics/overview?period=${period}`),
        axios.get(`${API}/admin/analytics/pages?period=${period}`),
        axios.get(`${API}/admin/growth/campaigns`),
        axios.get(`${API}/admin/analytics/integrations`),
        axios.get(`${API}/admin/analytics/insights?period=${period}`),
        axios.get(`${API}/admin/analytics/campaign-markers?period=${period}`),
        axios.get(`${API}/admin/analytics/commercial-funnel?period=${period}`),
      ]);
      setOverview(o.data); setPages(p.data.items); setCampaigns(c.data.items); setIntegrations(i.data); setInsights(ins.data);
      setCampaignMarkers(m.data.markers || []);
      setCommercialFunnel(cf.data);
    } catch (e) { toast.error("Eroare la încărcarea datelor analytics"); }
    setLoading(false);
  };
  useEffect(() => { load(); }, [period]); // eslint-disable-line react-hooks/exhaustive-deps

  // Comparator campanii — încarcă/refresh când se schimbă selecția sau perioada
  const runCompare = async (ids) => {
    if (ids.length < 2) { setCompareData(null); return; }
    setCompareLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/growth/campaigns/compare?ids=${ids.join(",")}&period=${period}`);
      setCompareData(data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Eroare la comparație"); }
    setCompareLoading(false);
  };
  useEffect(() => { if (compareMode) runCompare(compareSelectedIds); }, [compareSelectedIds, period, compareMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleCompareId = (id) => {
    setCompareSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : prev.length >= 3 ? prev : [...prev, id]);
  };

  const exportCsv = (report) => window.open(`${API}/admin/analytics/export.csv?report=${report}&period=${period}`, "_blank");

  const createCampaign = async () => {
    if (!form.name.trim()) return toast.error("Numele campaniei e obligatoriu");
    try {
      await axios.post(`${API}/admin/growth/campaigns`, form);
      toast.success("Campanie creată — link + QR generate");
      setShowCreate(false);
      setForm({ name: "", administrator: "", association: "", apartments_count: 0, channel: "whatsapp", recipients_count: 0 });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Eroare la creare"); }
  };

  const deleteCampaign = async (id) => {
    if (!window.confirm("Ștergi campania? Statisticile asociate rămân în istoric.")) return;
    await axios.delete(`${API}/admin/growth/campaigns/${id}`);
    load();
  };

  const saveIntegrations = async () => {
    try {
      const { data } = await axios.put(`${API}/admin/analytics/integrations`, {
        clarity_id: integrations.clarity_id || "", ga4_id: integrations.ga4_id || "",
        meta_pixel_id: integrations.meta_pixel_id || "", tracker_enabled: integrations.tracker_enabled !== false,
        whatsapp_enabled: integrations.whatsapp_enabled !== false,
        whatsapp_phone: integrations.whatsapp_phone || "",
        whatsapp_message: integrations.whatsapp_message || "",
      });
      setIntegrations(data); toast.success("Integrări salvate — scripturile se injectează automat la vizitatori");
    } catch (e) { toast.error("Eroare la salvare"); }
  };

  const sourceData = useMemo(() => (overview?.sources || []).map(s => ({ ...s, fill: SOURCE_COLORS[s.source] || "#0ea5e9" })), [overview]);
  const k = overview?.kpi || {};
  const kp = overview?.kpi_prev || {};

  return (
    <AdminLayoutMetronic active="growth_analytics" title="Analytics & Growth" subtitle="Decizii bazate pe date despre trafic, campanii și conversii">
      <div className="space-y-6" data-testid="analytics-growth-page">
        {/* 1. Navigare secundară (TabBar standard) */}
        <div className="flex flex-wrap items-center gap-2">
          <TabBar
            tabs={[["overview", "Dashboard", BarChart3], ["commercial", "Funnel comercial", Workflow], ["heatmap", "Heatmap", Flame], ["bounce", "Bounce", TrendingDown], ["retention", "Retenție", Repeat], ["abtest", "A/B Testing", FlaskConical], ["whatsapp", "WhatsApp", MessageCircle], ["pages", "Pagini", MousePointerClick], ["campaigns", "Campanii", Megaphone], ["integrations", "Integrări", Settings2]]}
            active={tab} onChange={setTab} testidPrefix="ag-tab"
          />
          {/* 2. Action Bar standard: perioadă · CSV · PDF · refresh */}
          <div className="ml-auto">
            <ActionBar
              periods={PERIOD_PRESETS}
              period={period} onPeriod={setPeriod} onRefresh={load} loading={loading}
              onExportCsv={() => exportCsv("overview")}
              onExportPdf={() => window.open(`${API}/admin/analytics/export.pdf?period=${period}`, "_blank")}
              testidPrefix="ag"
            />
          </div>
        </div>

        {loading && !overview ? (
          <DSSkeleton kpis={6} blocks={2} />
        ) : tab === "overview" && overview ? (
          <>
            {/* 3. KPI Cards standard: icon → titlu → valoare → evoluție */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <KpiCard icon={Users} label="Vizitatori unici" value={k.unique_visitors ?? 0} trend={trendOf(k, kp, "unique_visitors")} accent="info" />
              <KpiCard icon={MousePointerClick} label="Sesiuni" value={k.sessions ?? 0} trend={trendOf(k, kp, "sessions")} accent="info" />
              <KpiCard icon={UserPlus} label="Conturi create" value={k.accounts_created ?? 0} trend={trendOf(k, kp, "accounts_created")} accent="success" />
              <KpiCard icon={Users} label="Specialiști înscriși" value={k.specialists_signed ?? 0} trend={trendOf(k, kp, "specialists_signed")} accent="ai" />
              <KpiCard icon={Building2} label="Proprietăți adăugate" value={k.properties_added ?? 0} trend={trendOf(k, kp, "properties_added")} accent="warning" />
              <KpiCard icon={Wallet} label="Bounce rate" value={`${k.bounce_rate_pct ?? 0}%`} trend={trendOf(k, kp, "bounce_rate_pct")} invertTrend accent="critical" />
            </div>

            {/* 3b. Year-over-Year strip — apare doar când perioada e ≥ 60 zile */}
            {overview.kpi_yoy && (
              <div className="rounded-2xl border border-violet-200 dark:border-violet-500/30 bg-gradient-to-r from-violet-50/70 to-blue-50/50 dark:from-violet-500/10 dark:to-blue-500/10 px-4 py-3" data-testid="ag-yoy-strip">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-[11px] uppercase tracking-wider font-black text-violet-600 dark:text-violet-300">Year-over-Year</span>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    {overview.kpi_yoy.period?.from} → {overview.kpi_yoy.period?.to}
                  </span>
                  <div className="ml-auto grid grid-cols-3 md:grid-cols-6 gap-3 text-center">
                    {[
                      ["Vizitatori", k.unique_visitors, overview.kpi_yoy.unique_visitors],
                      ["Sesiuni", k.sessions, overview.kpi_yoy.sessions],
                      ["Conturi", k.accounts_created, overview.kpi_yoy.accounts_created],
                      ["Specialiști", k.specialists_signed, overview.kpi_yoy.specialists_signed],
                      ["Proprietăți", k.properties_added, overview.kpi_yoy.properties_added],
                      ["Bounce", `${k.bounce_rate_pct ?? 0}%`, `${overview.kpi_yoy.bounce_rate_pct ?? 0}%`],
                    ].map(([label, cur, yoy]) => {
                      const curN = typeof cur === "number" ? cur : parseFloat(cur) || 0;
                      const yoyN = typeof yoy === "number" ? yoy : parseFloat(yoy) || 0;
                      const delta = yoyN ? Math.round((curN - yoyN) / yoyN * 100) : null;
                      const isPositive = (delta ?? 0) > 0;
                      const isBounce = label === "Bounce";
                      const good = isBounce ? !isPositive : isPositive;
                      return (
                        <div key={label} className="min-w-[60px]">
                          <div className="text-[9px] uppercase font-bold text-slate-400">{label}</div>
                          <div className="text-xs font-black text-slate-700 dark:text-slate-200">vs {yoy ?? 0}</div>
                          {delta !== null && (
                            <div className={`text-[10px] font-bold ${good ? "text-emerald-600" : "text-rose-600"}`}>
                              {delta > 0 ? "+" : ""}{delta}%
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* 4. AI Insights — obligatoriu după KPI */}
            <AIInsightCard
              bullets={insights?.bullets || []} alerts={insights?.alerts || []}
              recommendations={insights?.recommendations || []}
              onAction={() => insights?.recommendations?.length && toast.info(insights.recommendations.join(" · "), { duration: 8000 })}
              loading={loading} llmModule="analytics" testid="ag-ai-insights"
            />

            {/* 5. Grafice standard */}
            <div className="grid lg:grid-cols-3 gap-4">
              <ChartCard title={`Trafic ${overview.granularity === "month" ? "lunar" : overview.granularity === "week" ? "săptămânal" : "zilnic"}${campaignMarkers.length > 0 ? ` · ${campaignMarkers.length} marker${campaignMarkers.length > 1 ? "e" : ""}` : ""}`} className="lg:col-span-2" testid="ag-chart-traffic"
                actions={<DSButton variant="ghost" onClick={() => exportCsv("overview")} data-testid="ag-export-overview">CSV</DSButton>}>
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={overview.series} margin={{ top: 15, right: 20, left: 0, bottom: 0 }}>
                    <defs><linearGradient id="gv" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={CHART_COLORS[0]} stopOpacity={0.5} /><stop offset="100%" stopColor={CHART_COLORS[0]} stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray={CHART.gridDash} strokeOpacity={CHART.gridOpacity} />
                    <XAxis dataKey="day" tick={{ fontSize: CHART.tickFontSize }} tickFormatter={(d) => formatBucket(d, overview.granularity)} />
                    <YAxis tick={{ fontSize: CHART.tickFontSize }} allowDecimals={false} />
                    <Tooltip labelFormatter={(d) => `${overview.granularity === "week" ? "Săpt. de la " : overview.granularity === "month" ? "Luna " : ""}${d}`} />
                    <Area type="monotone" dataKey="visitors" name="Vizitatori" stroke={CHART_COLORS[0]} fill="url(#gv)" strokeWidth={CHART.strokeWidth} />
                    <Area type="monotone" dataKey="sessions" name="Sesiuni" stroke={CHART_COLORS[1]} fill="none" strokeWidth={CHART.strokeWidth} />
                    {campaignMarkers.map(m => (
                      <ReferenceLine key={m.id} x={m.day} stroke="#f59e0b" strokeDasharray="4 4"
                        label={{ value: `📣 ${m.name}`, position: "top", fill: "#f59e0b", fontSize: 10, fontWeight: 700 }} />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Surse trafic" testid="ag-chart-sources">
                {sourceData.length === 0 ? <EmptyState title="Fără trafic în perioadă" hint="Sursele apar odată cu primele sesiuni." /> : (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie data={sourceData} dataKey="sessions" nameKey="source" innerRadius={45} outerRadius={80} paddingAngle={2}>
                          {sourceData.map((s, i) => <Cell key={i} fill={s.fill} />)}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {sourceData.map(s => (
                        <span key={s.source} className="flex items-center gap-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                          <span className="w-2 h-2 rounded-full" style={{ background: s.fill }} /> {s.source} ({s.sessions})
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </ChartCard>
            </div>
            <ChartCard title="Funnel conversie" testid="ag-chart-funnel">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={overview.funnel} layout="vertical" margin={{ left: 40 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="step" width={150} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={22}>
                    <LabelList dataKey="count" position="right" style={{ fontSize: 12, fontWeight: 700 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        ) : tab === "commercial" ? (
          <CommercialFunnelTab data={commercialFunnel} />
        ) : tab === "heatmap" ? (
          <HeatmapTab period={period} clarityId={integrations?.clarity_id} />
        ) : tab === "bounce" ? (
          <BounceTab period={period} />
        ) : tab === "retention" ? (
          <RetentionTab />
        ) : tab === "abtest" ? (
          <AbTestingTab />
        ) : tab === "whatsapp" ? (
          <WhatsAppTab period={period} />
        ) : tab === "pages" ? (
          /* 6. Tabel standard: sticky header · sortare · căutare · export · hover */
          <DataTable
            title="Performanța paginilor"
            columns={[
              { key: "path", label: "Pagină", render: r => <span className="font-mono text-xs">{r.path}</span> },
              { key: "views", label: "Vizualizări", render: r => <b>{r.views}</b> },
              { key: "avg_time_sec", label: "Timp mediu", render: r => `${r.avg_time_sec}s` },
              { key: "bounce_rate_pct", label: "Bounce", render: r => `${r.bounce_rate_pct}%` },
            ]}
            rows={pages} searchKeys={["path"]} exportName={`pagini-${period}`}
            emptyTitle="Fără date încă." emptyHint="Trackerul colectează de la primii vizitatori."
            testid="ag-pages-table"
          />
        ) : tab === "campaigns" ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-xs text-slate-500">Indicatori per campanie: primit → deschis → 30s+ → înregistrare → cont → revenit 7z</p>
              <div className="flex gap-2">
                <DSButton variant={compareMode ? "primary" : "secondary"} icon={GitCompareArrows}
                  onClick={() => { setCompareMode(v => !v); if (compareMode) { setCompareSelectedIds([]); setCompareData(null); } }}
                  data-testid="ag-toggle-compare">
                  {compareMode ? "Închide comparator" : "Comparator"}
                </DSButton>
                <DSButton variant="secondary" onClick={() => exportCsv("campaigns")} data-testid="ag-export-campaigns">CSV</DSButton>
                <DSButton variant="primary" icon={Plus} onClick={() => setShowCreate(true)} data-testid="ag-new-campaign">Campanie nouă</DSButton>
              </div>
            </div>
            {compareMode && (
              <div className="rounded-2xl border-2 border-violet-200 dark:border-violet-500/30 bg-violet-50/40 dark:bg-violet-500/5 p-4 space-y-3" data-testid="ag-compare-panel">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-black text-slate-900 dark:text-white text-sm">Compară 2-3 campanii side-by-side</h4>
                    <p className="text-[11px] text-slate-500">Selectat: {compareSelectedIds.length}/3 · Perioada: {period.toUpperCase()}</p>
                  </div>
                  {compareSelectedIds.length > 0 && (
                    <button onClick={() => { setCompareSelectedIds([]); setCompareData(null); }}
                      className="text-xs text-slate-500 hover:text-rose-500 flex items-center gap-1" data-testid="ag-compare-clear">
                      <X className="w-3.5 h-3.5" /> Golește
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {campaigns.map(c => (
                    <button key={c.id} onClick={() => toggleCompareId(c.id)} data-testid={`ag-compare-pick-${c.code}`}
                      disabled={!compareSelectedIds.includes(c.id) && compareSelectedIds.length >= 3}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${compareSelectedIds.includes(c.id) ? "bg-violet-500 text-white" : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"}`}>
                      {compareSelectedIds.includes(c.id) ? "✓ " : ""}{c.name}
                    </button>
                  ))}
                </div>
                {compareLoading && <DSSkeleton blocks={1} />}
                {compareData && compareData.campaigns?.length >= 2 && (
                  <>
                    {/* Chart bare grupate — vizitatori pe campanie */}
                    <ChartCard title="Evoluție vizitatori per campanie" testid="ag-compare-chart">
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={(() => {
                          // Merge series pe key `day` cu column per campanie
                          const map = {};
                          compareData.campaigns.forEach((camp, i) => {
                            (camp.series || []).forEach(row => {
                              if (!map[row.day]) map[row.day] = { day: row.day };
                              map[row.day][`c${i}`] = row.visitors;
                            });
                          });
                          return Object.values(map).sort((a, b) => a.day.localeCompare(b.day));
                        })()}>
                          <CartesianGrid strokeDasharray={CHART.gridDash} strokeOpacity={CHART.gridOpacity} />
                          <XAxis dataKey="day" tick={{ fontSize: CHART.tickFontSize }} tickFormatter={(d) => formatBucket(d, compareData.granularity)} />
                          <YAxis tick={{ fontSize: CHART.tickFontSize }} allowDecimals={false} />
                          <Tooltip />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          {compareData.campaigns.map((camp, i) => (
                            <Bar key={camp.id} dataKey={`c${i}`} name={camp.name} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    </ChartCard>
                    {/* Tabel side-by-side */}
                    <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="ag-compare-table">
                      <table className="min-w-full text-sm">
                        <thead className="bg-slate-50 dark:bg-slate-700/50">
                          <tr>
                            <th className="px-3 py-2 text-left text-[10px] font-black uppercase text-slate-500">Metric</th>
                            {compareData.campaigns.map((camp, i) => (
                              <th key={camp.id} className="px-3 py-2 text-right text-[10px] font-black uppercase" style={{ color: CHART_COLORS[i % CHART_COLORS.length] }}>{camp.name}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            ["Canal", (c) => c.channel],
                            ["Recipients", (c) => c.recipients],
                            ["Vizitatori unici", (c) => c.stats.unique_visitors],
                            ["30s+ pe site", (c) => c.stats.over_30s],
                            ["Început înregistrare", (c) => c.stats.signup_started],
                            ["Conturi create", (c) => c.stats.accounts_created],
                            ["Abonamente", (c) => c.stats.subscriptions],
                            ["Revenit 7z", (c) => c.stats.returned_7d],
                            ["Conversie %", (c) => `${c.stats.conversion_pct}%`],
                          ].map(([label, getter]) => (
                            <tr key={label} className="border-t border-slate-100 dark:border-slate-700/50">
                              <td className="px-3 py-2 font-semibold text-slate-600 dark:text-slate-300">{label}</td>
                              {compareData.campaigns.map(camp => (
                                <td key={camp.id} className="px-3 py-2 text-right font-mono font-bold text-slate-900 dark:text-white">{getter(camp) ?? 0}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
                {compareSelectedIds.length === 1 && (
                  <div className="text-xs text-slate-500 italic">Alege încă o campanie pentru a începe comparația.</div>
                )}
              </div>
            )}
            {showCreate && (
              <div className="rounded-2xl border-2 border-blue-200 dark:border-blue-500/30 bg-white dark:bg-slate-800 p-4 grid md:grid-cols-3 gap-3" data-testid="ag-create-form">
                {[["name", "Nume campanie *"], ["administrator", "Administrator"], ["association", "Asociație"]].map(([kk, label]) => (
                  <label key={kk} className="text-xs font-bold text-slate-500">{label}
                    <input value={form[kk]} onChange={e => setForm(f => ({ ...f, [kk]: e.target.value }))} data-testid={`ag-form-${kk}`}
                      className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" />
                  </label>
                ))}
                <label className="text-xs font-bold text-slate-500">Nr. apartamente
                  <input type="number" value={form.apartments_count} onChange={e => setForm(f => ({ ...f, apartments_count: +e.target.value || 0 }))}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" />
                </label>
                <label className="text-xs font-bold text-slate-500">Persoane care au primit mesajul
                  <input type="number" value={form.recipients_count} onChange={e => setForm(f => ({ ...f, recipients_count: +e.target.value || 0 }))} data-testid="ag-form-recipients"
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" />
                </label>
                <label className="text-xs font-bold text-slate-500">Canal
                  <select value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-normal">
                    {["whatsapp", "facebook", "google", "qr", "admin", "other"].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
                <div className="md:col-span-3 flex gap-2 justify-end">
                  <DSButton variant="secondary" onClick={() => setShowCreate(false)}>Anulează</DSButton>
                  <DSButton variant="primary" onClick={createCampaign} data-testid="ag-form-submit">Creează + generează link & QR</DSButton>
                </div>
              </div>
            )}
            <div className="grid gap-3" data-testid="ag-campaigns-list">
              {campaigns.length === 0 && !showCreate && (
                <EmptyState icon={Megaphone} title="Nicio campanie încă." hint="Creează prima campanie și primești automat link personalizat + QR."
                  action={<DSButton variant="primary" icon={Plus} onClick={() => setShowCreate(true)}>Creează prima campanie</DSButton>} />
              )}
              {campaigns.map(c => (
                <div key={c.id} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-black text-slate-900 dark:text-white">{c.name}</span>
                    <DSBadge type="ACTIVE">{c.channel}</DSBadge>
                    <span className="text-xs text-slate-400">{c.administrator}{c.association ? ` · ${c.association}` : ""}{c.apartments_count ? ` · ${c.apartments_count} ap.` : ""} · trimis {String(c.sent_at || "").slice(0, 10)}</span>
                    <div className="ml-auto flex items-center gap-1.5">
                      <button onClick={() => { navigator.clipboard.writeText(c.url); toast.success("Link copiat"); }} title={c.url}
                        className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-bold bg-blue-50 dark:bg-blue-500/15 text-blue-600 dark:text-blue-300" data-testid={`ag-copy-${c.code}`}>
                        <Link2 className="w-3.5 h-3.5" /> {c.code}
                      </button>
                      <a href={`${API}/admin/growth/campaigns/${c.id}/qr`} className="p-1.5 rounded-lg bg-violet-50 dark:bg-violet-500/15 text-violet-600 dark:text-violet-300" title="Descarcă QR" data-testid={`ag-qr-${c.code}`}>
                        <QrCode className="w-4 h-4" />
                      </a>
                      <button onClick={() => deleteCampaign(c.id)} className="p-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/15 text-rose-500"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>
                  <div className="mt-3 grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2 text-center">
                    {[["Primit", c.stats?.recipients], ["Deschis", c.stats?.opened], ["Vizitatori", c.stats?.unique_visitors], ["30s+", c.stats?.over_30s],
                      ["Început înreg.", c.stats?.signup_started], ["Conturi", c.stats?.accounts_created], ["Abonamente", c.stats?.subscriptions],
                      ["Revenit 7z", c.stats?.returned_7d], ["Conversie", `${c.stats?.conversion_pct ?? 0}%`]].map(([label, val]) => (
                      <div key={label} className="rounded-xl bg-slate-50 dark:bg-slate-700/40 py-2">
                        <div className="text-lg font-black text-slate-900 dark:text-white">{val ?? 0}</div>
                        <div className="text-[9px] uppercase font-bold text-slate-400">{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : tab === "integrations" && integrations ? (
          <div className="max-w-xl rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 space-y-4" data-testid="ag-integrations">
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Integrări externe (modulare)</h3>
            <p className="text-xs text-slate-500">Lipești ID-ul → scriptul se injectează automat pentru vizitatori. Fără modificări de cod.</p>
            {[["clarity_id", "Microsoft Clarity Project ID", "ex: xj5fspkgjj — recording sesiuni + heatmaps"],
              ["ga4_id", "Google Analytics 4 Measurement ID", "ex: G-XXXXXXXXXX"],
              ["meta_pixel_id", "Meta Pixel ID", "ex: 1234567890"]].map(([kk, label, hint]) => (
              <label key={kk} className="block text-xs font-bold text-slate-500">{label}
                <input value={integrations[kk] || ""} onChange={e => setIntegrations(s => ({ ...s, [kk]: e.target.value.trim() }))} data-testid={`ag-int-${kk}`}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-mono font-normal" placeholder={hint} />
              </label>
            ))}
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={integrations.tracker_enabled !== false} onChange={e => setIntegrations(s => ({ ...s, tracker_enabled: e.target.checked }))} />
              Tracker first-party activ (vizitatori, sesiuni, funnel)
            </label>
            <div className="pt-3 border-t border-slate-100 dark:border-slate-700 space-y-3" data-testid="ag-int-whatsapp">
              <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm flex items-center gap-1.5"><MessageCircle className="w-4 h-4 text-[#25D366]" /> Widget WhatsApp (buton flotant)</h4>
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={integrations.whatsapp_enabled !== false} onChange={e => setIntegrations(s => ({ ...s, whatsapp_enabled: e.target.checked }))} data-testid="ag-int-wa-enabled" />
                Activ pe toate paginile publice (dreapta-jos)
              </label>
              <label className="block text-xs font-bold text-slate-500">Număr de telefon (editabil oricând)
                <input value={integrations.whatsapp_phone || ""} onChange={e => setIntegrations(s => ({ ...s, whatsapp_phone: e.target.value.trim() }))} data-testid="ag-int-wa-phone"
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-mono font-normal" placeholder="+40790541342" />
              </label>
              <label className="block text-xs font-bold text-slate-500">Mesaj predefinit
                <input value={integrations.whatsapp_message || ""} onChange={e => setIntegrations(s => ({ ...s, whatsapp_message: e.target.value }))} data-testid="ag-int-wa-message"
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" placeholder="Bună! Doresc informații despre PropManage." />
              </label>
            </div>
            <DSButton variant="primary" icon={CheckCircle2} onClick={saveIntegrations} data-testid="ag-int-save">Salvează integrările</DSButton>
          </div>
        ) : null}
      </div>
    </AdminLayoutMetronic>
  );
}
