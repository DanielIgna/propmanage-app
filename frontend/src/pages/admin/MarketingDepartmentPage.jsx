// AI Marketing & Growth Department — Phase 1 Core AI Brain
// Route: /admin/marketing
import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { useLocation } from "react-router-dom";
import CampaignsTab from "./marketing/CampaignsTab";
import PerformanceTab from "./marketing/PerformanceTab";
import {
  Megaphone, ChevronLeft, Loader2, Sparkles, TrendingUp, TrendingDown,
  Users, ShoppingBag, DollarSign, BarChart3, Send, MessageCircle,
  AlertTriangle, Lightbulb, Target, MapPin, Zap, Crown, UserX, X,
  Copy, RefreshCw, ChevronRight, Rocket, Brain, Wand2, Activity,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const RON = (n) => `${Number(n || 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} RON`;

const KpiCard = ({ icon: Icon, label, value, sub, color = "text-violet-500", testid }) => (
  <div className="rounded-xl p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900" data-testid={testid}>
    <div className="flex items-center justify-between mb-1">
      <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium">{label}</span>
      <Icon className={`w-4 h-4 ${color}`} />
    </div>
    <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
    {sub != null && <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{sub}</div>}
  </div>
);

const TabButton = ({ active, onClick, children, testid }) => (
  <button
    onClick={onClick}
    data-testid={testid}
    className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
      active
        ? "bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white shadow-md"
        : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
    }`}
  >
    {children}
  </button>
);

// ---------- Dashboard tab ----------
const DashboardTab = ({ data }) => (
  <div className="space-y-6" data-testid="mkt-tab-dashboard">
    <div>
      <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><Users className="w-4 h-4 text-blue-500" /> Utilizatori</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={Users} label="Total utilizatori" value={data.users.total} testid="kpi-users-total" />
        <KpiCard icon={TrendingUp} label="Noi (30 zile)" value={data.users.new_30d}
          sub={`${data.users.new_30d_growth > 0 ? "↑" : "↓"} ${Math.abs(data.users.new_30d_growth)}% vs 30z anterioare`}
          color={data.users.new_30d_growth >= 0 ? "text-emerald-500" : "text-rose-500"} testid="kpi-users-new" />
        <KpiCard icon={Zap} label="Activi" value={data.users.active}
          sub={`${data.users.retention_rate}% retenție`} color="text-emerald-500" testid="kpi-users-active" />
        <KpiCard icon={UserX} label="Churn rate" value={`${data.users.churn_rate}%`}
          sub={`${data.users.inactive} inactivi`} color="text-amber-500" testid="kpi-users-churn" />
      </div>
    </div>

    <div>
      <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><Crown className="w-4 h-4 text-violet-500" /> Clienți</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={Users} label="Total clienți" value={data.clients.total} testid="kpi-clients-total" />
        <KpiCard icon={TrendingUp} label="Noi (30 zile)" value={data.clients.new_30d} color="text-emerald-500" testid="kpi-clients-new" />
        <KpiCard icon={RefreshCw} label="Recurenți" value={data.clients.recurring} color="text-violet-500" testid="kpi-clients-recurring" />
        <KpiCard icon={DollarSign} label="Valoare medie" value={RON(data.clients.avg_order_value)}
          sub={`LTV ~${RON(data.clients.estimated_ltv)}`} color="text-fuchsia-500" testid="kpi-clients-aov" />
      </div>
    </div>

    <div>
      <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><Target className="w-4 h-4 text-amber-500" /> Specialiști</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={Users} label="Total" value={data.specialists.total} testid="kpi-spec-total" />
        <KpiCard icon={Zap} label="Activi" value={data.specialists.active}
          sub={`${data.specialists.inactive} inactivi`} color="text-emerald-500" testid="kpi-spec-active" />
        <KpiCard icon={BarChart3} label="Ocupare" value={`${data.specialists.occupancy_rate}%`} color="text-blue-500" testid="kpi-spec-occupancy" />
        <KpiCard icon={DollarSign} label="Venit mediu" value={RON(data.specialists.avg_revenue_per_specialist)}
          sub={`${data.specialists.accept_rate}% acceptare`} color="text-fuchsia-500" testid="kpi-spec-revenue" />
      </div>
    </div>

    <div>
      <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><DollarSign className="w-4 h-4 text-emerald-500" /> Financiar</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={DollarSign} label="Venit total" value={RON(data.financial.total_revenue)} color="text-emerald-500" testid="kpi-fin-total" />
        <KpiCard icon={TrendingUp} label="Venit lunar" value={RON(data.financial.monthly_revenue)}
          sub={`${data.financial.monthly_growth_pct > 0 ? "↑" : "↓"} ${Math.abs(data.financial.monthly_growth_pct)}% MoM`}
          color={data.financial.monthly_growth_pct >= 0 ? "text-emerald-500" : "text-rose-500"} testid="kpi-fin-monthly" />
        <KpiCard icon={Sparkles} label="Profit estimat" value={RON(data.financial.profit_estimated)} color="text-violet-500" testid="kpi-fin-profit" />
        <KpiCard icon={BarChart3} label="Taxe (TVA 19%)" value={RON(data.financial.taxes_collected)} color="text-amber-500" testid="kpi-fin-taxes" />
      </div>

      {data.financial.by_category.length > 0 && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Top venit pe categorie</h4>
            <div className="space-y-1.5">
              {data.financial.by_category.slice(0, 6).map((c, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 dark:text-slate-200 truncate">{c.category}</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">{RON(c.revenue)} <span className="text-xs text-slate-400">·{c.orders}</span></span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Top venit pe județ</h4>
            <div className="space-y-1.5">
              {data.financial.by_county.slice(0, 6).map((c, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 dark:text-slate-200 flex items-center gap-1"><MapPin className="w-3 h-3 text-blue-500" />{c.county}</span>
                  <span className="font-bold text-violet-600 dark:text-violet-400">{RON(c.revenue)} <span className="text-xs text-slate-400">·{c.orders}</span></span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>

    <div>
      <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><ShoppingBag className="w-4 h-4 text-cyan-500" /> Marketplace</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={Target} label="Conversie" value={`${data.marketplace.conversion_rate}%`} color="text-emerald-500" testid="kpi-mkt-conv" />
        <KpiCard icon={TrendingDown} label="Abandon" value={`${data.marketplace.abandonment_rate}%`} color="text-rose-500" testid="kpi-mkt-abandon" />
        <KpiCard icon={Sparkles} label="Finalizare" value={`${data.marketplace.completion_rate}%`} color="text-violet-500" testid="kpi-mkt-completion" />
        <KpiCard icon={ShoppingBag} label="Total comenzi" value={data.marketplace.funnel.posted} color="text-blue-500" testid="kpi-mkt-orders" />
      </div>
      {data.marketplace.most_ordered.length > 0 && (
        <div className="mt-4 bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
          <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Top servicii comandate</h4>
          <div className="flex flex-wrap gap-2">
            {data.marketplace.most_ordered.map((s, i) => (
              <div key={i} className="px-3 py-1.5 rounded-full bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-sm">
                <span className="font-medium text-cyan-700 dark:text-cyan-300">{s.category}</span>
                <span className="text-xs text-slate-500 ml-2">{s.orders} comenzi</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  </div>
);

// ---------- AI sections ----------
const AISection = ({ endpoint, title, color, icon: Icon, renderer, testid, mode = "post" }) => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const generate = async () => {
    setBusy(true); setErr("");
    try {
      const r = mode === "post" ? await ax.post(endpoint) : await ax.get(endpoint);
      setData(r.data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };
  useEffect(() => {
    if (mode === "get") generate();
    // eslint-disable-next-line
  }, []);
  return (
    <div className="space-y-4" data-testid={testid}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2"><Icon className={`w-5 h-5 ${color}`} /> {title}</h3>
        {mode === "post" && (
          <button onClick={generate} disabled={busy}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white text-sm font-medium disabled:opacity-50 flex items-center gap-1.5"
            data-testid={`${testid}-btn`}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {busy ? "Claude analizează…" : (data ? "Regenerează" : "Generează cu AI")}
          </button>
        )}
      </div>
      {err && <div className="text-rose-500 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{err}</div>}
      {busy && !data && <div className="text-center py-10"><Loader2 className="w-7 h-7 animate-spin mx-auto text-violet-500" /></div>}
      {data && renderer(data, generate)}
    </div>
  );
};

const InsightsRenderer = (data) => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
    {(data.insights || []).map((i, idx) => (
      <div key={idx}
        className={`p-4 rounded-xl border ${
          i.severity === "critical" ? "border-rose-300 bg-rose-50 dark:bg-rose-500/10 dark:border-rose-500/30"
          : i.severity === "warning" ? "border-amber-300 bg-amber-50 dark:bg-amber-500/10 dark:border-amber-500/30"
          : "border-blue-300 bg-blue-50 dark:bg-blue-500/10 dark:border-blue-500/30"
        }`} data-testid={`insight-${idx}`}>
        <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
          <h4 className="font-bold text-slate-900 dark:text-white text-sm">{i.title}</h4>
          <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-white/70 dark:bg-slate-900/70 text-slate-700 dark:text-slate-200">{i.category}</span>
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-200">{i.body}</p>
        {i.metric && <div className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 font-mono">{i.metric}</div>}
      </div>
    ))}
  </div>
);

const RecsRenderer = (data) => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div>
      <h4 className="text-xs uppercase tracking-wider text-violet-600 dark:text-violet-400 font-bold mb-2 flex items-center gap-1"><Megaphone className="w-3 h-3" /> Marketing</h4>
      <div className="space-y-2">
        {(data.marketing || []).map((r, i) => (
          <div key={i} className="p-3 rounded-xl border border-violet-200 dark:border-violet-500/30 bg-violet-50/40 dark:bg-violet-500/5" data-testid={`rec-mkt-${i}`}>
            <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
              <h5 className="font-bold text-slate-900 dark:text-white text-sm">{r.action}</h5>
              <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                r.priority === "high" ? "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300"
                : r.priority === "medium" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
                : "bg-slate-100 text-slate-700"
              }`}>{r.priority}</span>
            </div>
            <div className="text-xs text-slate-500 mb-1">{r.audience}</div>
            <div className="text-sm text-slate-700 dark:text-slate-200">{r.expected_impact}</div>
            {r.budget_ron > 0 && <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold mt-1">Buget: {r.budget_ron} RON</div>}
          </div>
        ))}
      </div>
    </div>
    <div>
      <h4 className="text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400 font-bold mb-2 flex items-center gap-1"><Rocket className="w-3 h-3" /> Business</h4>
      <div className="space-y-2">
        {(data.business || []).map((r, i) => (
          <div key={i} className="p-3 rounded-xl border border-blue-200 dark:border-blue-500/30 bg-blue-50/40 dark:bg-blue-500/5" data-testid={`rec-biz-${i}`}>
            <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
              <h5 className="font-bold text-slate-900 dark:text-white text-sm">{r.action}</h5>
              <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                r.priority === "high" ? "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300"
                : "bg-slate-100 text-slate-700"
              }`}>{r.priority}</span>
            </div>
            <p className="text-sm text-slate-700 dark:text-slate-200">{r.why}</p>
          </div>
        ))}
      </div>
    </div>
  </div>
);

const SegmentsRenderer = (data) => (
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
    {Object.entries(data.buckets).map(([key, b]) => (
      <div key={key} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900" data-testid={`segment-${key}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider text-slate-500">{b.label}</span>
          <Users className="w-4 h-4 text-violet-500" />
        </div>
        <div className="text-3xl font-bold text-slate-900 dark:text-white mb-1">{b.count}</div>
        <div className="text-xs text-violet-600 dark:text-violet-400 font-medium">→ {b.action}</div>
      </div>
    ))}
  </div>
);

const ForecastRenderer = (data) => {
  if (data.note) return <div className="text-sm text-slate-500 text-center py-8">{data.note}</div>;
  const s = data.summary;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard icon={DollarSign} label="Venit prognozat 30z" value={RON(s.expected_revenue_next_30d)} color="text-emerald-500" testid="forecast-rev" />
        <KpiCard icon={ShoppingBag} label="Comenzi prognozate" value={s.expected_orders_next_30d} color="text-blue-500" testid="forecast-orders" />
        <KpiCard icon={s.trend === "up" ? TrendingUp : TrendingDown} label="Trend" value={s.trend.toUpperCase()}
          color={s.trend === "up" ? "text-emerald-500" : "text-rose-500"} testid="forecast-trend" />
        <KpiCard icon={BarChart3} label="Pantă" value={s.trend_slope} testid="forecast-slope" />
      </div>
      <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
        <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Prognoză venit zilnică (30 zile)</h4>
        <div className="flex items-end gap-1 h-32">
          {data.forecast_30d.map((f, i) => {
            const max = Math.max(...data.forecast_30d.map(x => x.predicted_revenue), 1);
            const h = (f.predicted_revenue / max) * 100;
            return (
              <div key={i} className="flex-1 bg-gradient-to-t from-violet-500 to-fuchsia-400 rounded-t hover:opacity-80 transition-opacity"
                style={{ height: `${h}%`, minHeight: "4px" }} title={`Ziua ${f.day}: ${RON(f.predicted_revenue)}`} />
            );
          })}
        </div>
      </div>
    </div>
  );
};

const GrowthRenderer = (data) => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div>
      <h4 className="text-xs uppercase tracking-wider text-amber-600 dark:text-amber-400 font-bold mb-2 flex items-center gap-1"><MapPin className="w-3 h-3" /> Județe sub-deservite</h4>
      {data.underserved_geo.length === 0 ? (
        <div className="text-sm text-slate-500 text-center py-6">Acoperire echilibrată.</div>
      ) : (
        <div className="space-y-2">
          {data.underserved_geo.map((u, i) => (
            <div key={i} className="p-3 rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50/40 dark:bg-amber-500/5" data-testid={`underserved-${i}`}>
              <div className="flex items-center justify-between flex-wrap gap-1">
                <span className="font-bold text-slate-900 dark:text-white">{u.county}</span>
                <span className="text-xs text-amber-700 dark:text-amber-300 font-bold">{u.demand_per_specialist} cereri / specialist</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">{u.demand_30d} cereri · {u.specialists} specialiști</div>
              <div className="text-xs text-violet-600 dark:text-violet-400 font-medium mt-1">→ {u.opportunity}</div>
            </div>
          ))}
        </div>
      )}
    </div>
    <div>
      <h4 className="text-xs uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-bold mb-2 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Categorii cu creștere accelerată</h4>
      {data.high_growth_categories.length === 0 ? (
        <div className="text-sm text-slate-500 text-center py-6">Fără variații semnificative.</div>
      ) : (
        <div className="space-y-2">
          {data.high_growth_categories.map((g, i) => (
            <div key={i} className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-500/5" data-testid={`growth-${i}`}>
              <div className="flex items-center justify-between flex-wrap gap-1">
                <span className="font-bold text-slate-900 dark:text-white">{g.category}</span>
                <span className="text-xs text-emerald-700 dark:text-emerald-300 font-bold">+{g.growth_pct}%</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">{g.previous} → {g.current} cereri</div>
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
);

const FutureIdeasRenderer = (data) => (
  <div className="space-y-5">
    <div className="p-4 rounded-xl bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10 border border-violet-200 dark:border-violet-500/30">
      <h4 className="font-bold text-violet-700 dark:text-violet-300 mb-1 flex items-center gap-2"><Lightbulb className="w-4 h-4" /> Roadmap viitor</h4>
      <p className="text-sm text-slate-700 dark:text-slate-200">Aceste module sunt pregătite pentru implementare în fazele următoare. Spune-mi când vrei să încep oricare dintre ele.</p>
    </div>
    {data.phases.map((phase, pi) => (
      <div key={pi} className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
        <h4 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
          <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300">{phase.phase.split(" — ")[0]}</span>
          {phase.phase.split(" — ")[1]}
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {phase.items.map((item) => (
            <div key={item.id} className="p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-violet-400 dark:hover:border-violet-500/50 transition-colors" data-testid={`idea-${item.id}`}>
              <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
                <h5 className="font-bold text-slate-900 dark:text-white text-sm">{item.title}</h5>
                <div className="flex items-center gap-1.5">
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                    item.priority === "P1" ? "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300"
                    : item.priority === "P2" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                  }`}>{item.priority}</span>
                  <span className="text-[10px] text-slate-500">~{item.effort_days}z</span>
                </div>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300">{item.description}</p>
              {item.requires_keys && (
                <div className="text-[10px] text-amber-600 dark:text-amber-400 mt-1.5 font-mono">⚠ Necesită: {item.requires_keys.join(", ")}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

// ---------- Copilot chat tab ----------
const CopilotTab = () => {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Salut! Sunt AI Marketing Copilot. Întreabă-mă orice despre datele tale: ce să promovezi, unde să investești, ce județe au potențial, de ce au scăzut comenzile etc." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sid, setSid] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setMessages(m => [...m, { role: "user", text }]);
    setInput(""); setBusy(true);
    try {
      const r = await ax.post("/api/admin/marketing/copilot", { session_id: sid, message: text });
      setSid(r.data.session_id);
      setMessages(m => [...m, { role: "assistant", text: r.data.reply }]);
    } catch (e) {
      setMessages(m => [...m, { role: "assistant", text: "Eroare: " + (e.response?.data?.detail || e.message), error: true }]);
    } finally { setBusy(false); }
  };

  const suggestions = [
    "Ce servicii să promovez luna asta?",
    "În ce județe să investesc buget?",
    "Care e categoria cea mai profitabilă?",
    "De ce a crescut/scăzut abandonul?",
  ];

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col" style={{ height: "65vh" }} data-testid="mkt-tab-copilot">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`} data-testid={`msg-${i}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl text-sm whitespace-pre-wrap ${
              m.role === "user" ? "bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white"
              : m.error ? "bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-500/30"
              : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100"
            }`}>{m.text}</div>
          </div>
        ))}
        {busy && <div className="flex justify-start"><div className="bg-slate-100 dark:bg-slate-800 p-3 rounded-2xl"><Loader2 className="w-4 h-4 animate-spin text-violet-500" /></div></div>}
        <div ref={endRef} />
      </div>
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => setInput(s)} className="text-xs px-2 py-1 rounded-full bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 hover:bg-violet-100" data-testid={`suggest-${i}`}>{s}</button>
          ))}
        </div>
      )}
      <div className="border-t border-slate-200 dark:border-slate-800 p-3 flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()}
          placeholder="Întreabă AI Marketing Copilot…" disabled={busy}
          className="flex-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          data-testid="copilot-input" />
        <button onClick={send} disabled={busy || !input.trim()}
          className="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white text-sm font-medium disabled:opacity-50 flex items-center gap-1.5" data-testid="copilot-send">
          <Send className="w-4 h-4" /> Trimite
        </button>
      </div>
    </div>
  );
};

// ---------- Main page ----------
const MarketingDepartmentPage = () => {
  const location = useLocation();
  const initialTab = new URLSearchParams(location.search).get("tab") || "dashboard";
  const [tab, setTab] = useState(initialTab);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = new URLSearchParams(location.search).get("tab");
    if (t) setTab(t);
  }, [location.search]);

  useEffect(() => {
    ax.get("/api/admin/marketing/dashboard")
      .then(r => setDashboard(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, []);

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: BarChart3 },
    { id: "campaigns", label: "Campanii", icon: Wand2 },
    { id: "performance", label: "Performance Loop", icon: Activity },
    { id: "insights", label: "AI Insights", icon: Brain },
    { id: "recommendations", label: "Recomandări", icon: Target },
    { id: "segments", label: "Segmente", icon: Users },
    { id: "forecast", label: "Predictive", icon: TrendingUp },
    { id: "growth", label: "Growth", icon: Rocket },
    { id: "copilot", label: "Copilot AI", icon: MessageCircle },
    { id: "future", label: "Idei viitoare", icon: Lightbulb },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="marketing-department-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <Megaphone className="w-5 h-5 text-fuchsia-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">AI Marketing & Growth Department</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-fuchsia-100 dark:bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400">Faza 1 · Core AI Brain</span>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1" data-testid="mkt-tabs">
        {tabs.map(t => (
          <TabButton key={t.id} active={tab === t.id} onClick={() => setTab(t.id)} testid={`tab-${t.id}`}>
            <span className="flex items-center gap-1.5"><t.icon className="w-3.5 h-3.5" /> {t.label}</span>
          </TabButton>
        ))}
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 text-sm border border-rose-200 dark:border-rose-500/30"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>}

      {loading ? (
        <div className="text-center py-20"><Loader2 className="w-7 h-7 animate-spin mx-auto text-slate-400" /></div>
      ) : (
        <>
          {tab === "dashboard" && dashboard && <DashboardTab data={dashboard} />}
          {tab === "campaigns" && <CampaignsTab />}
          {tab === "performance" && <PerformanceTab />}
          {tab === "insights" && (
            <AISection endpoint="/api/admin/marketing/insights" title="AI Business Intelligence Engine"
              color="text-violet-500" icon={Brain} renderer={InsightsRenderer} testid="mkt-tab-insights" />
          )}
          {tab === "recommendations" && (
            <AISection endpoint="/api/admin/marketing/recommendations" title="AI Recommendation Engine"
              color="text-fuchsia-500" icon={Target} renderer={RecsRenderer} testid="mkt-tab-recommendations" />
          )}
          {tab === "segments" && (
            <AISection endpoint="/api/admin/marketing/segments" title="Customer Segmentation Engine"
              color="text-blue-500" icon={Users} renderer={SegmentsRenderer} testid="mkt-tab-segments" mode="get" />
          )}
          {tab === "forecast" && (
            <AISection endpoint="/api/admin/marketing/forecast" title="AI Predictive Analytics"
              color="text-emerald-500" icon={TrendingUp} renderer={ForecastRenderer} testid="mkt-tab-forecast" mode="get" />
          )}
          {tab === "growth" && (
            <AISection endpoint="/api/admin/marketing/growth" title="Growth Engine"
              color="text-amber-500" icon={Rocket} renderer={GrowthRenderer} testid="mkt-tab-growth" mode="get" />
          )}
          {tab === "copilot" && <CopilotTab />}
          {tab === "future" && (
            <AISection endpoint="/api/admin/marketing/future-ideas" title="Idei viitoare — Marketing Roadmap"
              color="text-violet-500" icon={Lightbulb} renderer={FutureIdeasRenderer} testid="mkt-tab-future" mode="get" />
          )}
        </>
      )}
    </div>
  );
};

export default MarketingDepartmentPage;
export { MarketingDepartmentPage };
