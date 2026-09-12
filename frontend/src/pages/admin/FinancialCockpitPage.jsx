// FinancialCockpitPage — vedere financiară completă: revenue, escrow, MRR/ARR, TVA, cash flow 30z.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Wallet, Lock, Snowflake, Unlock, Repeat, Receipt, TrendingUp, RefreshCw, Percent, Sparkles } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });
const lei = (v) => `${(v ?? 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} lei`;

export default function FinancialCockpitPage() {
  const [data, setData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [genInsights, setGenInsights] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [r, i] = await Promise.all([
        ax.get("/admin/financial-cockpit"),
        ax.get("/admin/financial-cockpit/insights/latest"),
      ]);
      setData(r.data);
      setInsights(i.data.insights ? i.data : null);
    } catch (e) { /* silent */ }
    setLoading(false);
  };

  const generateInsights = async () => {
    setGenInsights(true);
    try {
      const r = await ax.post("/admin/financial-cockpit/insights");
      setInsights(r.data);
    } catch (e) { /* silent */ }
    setGenInsights(false);
  };

  useEffect(() => { load(); }, []);

  const rev = data?.revenue || {};
  const esc = data?.escrow || {};
  const subs = data?.subscriptions || {};
  const maxDay = Math.max(1, ...(data?.cash_flow_30d || []).map((d) => d.amount));

  return (
    <AdminLayoutMetronic
      title="Financial Cockpit"
      subtitle="Revenue · Escrow · Abonamente MRR/ARR · Comisioane · TVA estimat · Cash Flow — toate din datele reale"
    >
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : (
        <div className="space-y-6" data-testid="financial-cockpit-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Wallet}     label="Revenue 30 zile"  value={lei(rev.last_30d)} trend={rev.growth_pct != null ? `${rev.growth_pct > 0 ? "+" : ""}${rev.growth_pct}%` : null} accent="success" testid="fc-kpi-rev30" />
            <KpiCard icon={Lock}       label="Escrow blocat"    value={lei(esc.held?.amount)}   accent="warning"  testid="fc-kpi-escrow" />
            <KpiCard icon={Repeat}     label="MRR (abonamente)" value={lei(subs.mrr_ron)}       accent="ai"       testid="fc-kpi-mrr" />
            <KpiCard icon={Receipt}    label={`TVA estimat (${data?.vat?.rate_pct}%)`} value={lei(data?.vat?.estimated_30d)} accent="info" testid="fc-kpi-vat" />
          </div>

          <div className="grid lg:grid-cols-3 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><Lock className="w-4 h-4 text-amber-500" /> Escrow — stare completă</span>} testid="fc-escrow">
              <div className="space-y-2.5">
                {[
                  { k: "held", label: "Blocat (neconfirmat)", icon: Lock, cls: "text-amber-600 dark:text-amber-300" },
                  { k: "frozen", label: "Înghețat (dispute)", icon: Snowflake, cls: "text-rose-600 dark:text-rose-300" },
                  { k: "released", label: "Eliberat", icon: Unlock, cls: "text-emerald-600 dark:text-emerald-300" },
                ].map(({ k, label, icon: Icon, cls }) => (
                  <div key={k} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={`fc-escrow-${k}`}>
                    <span className={`flex items-center gap-2 text-sm font-medium ${cls}`}><Icon className="w-4 h-4" /> {label}</span>
                    <span className="text-sm font-black text-slate-900 dark:text-white">{lei(esc[k]?.amount)} <span className="text-[10px] text-slate-400 font-medium">({esc[k]?.count || 0})</span></span>
                  </div>
                ))}
                <div className="flex items-center justify-between p-2.5 rounded-xl border border-lime-200 dark:border-lime-500/30 bg-lime-50 dark:bg-lime-500/10" data-testid="fc-commission">
                  <span className="flex items-center gap-2 text-sm font-medium text-lime-800 dark:text-lime-200"><Percent className="w-4 h-4" /> Comision estimat</span>
                  <span className="text-sm font-black text-lime-800 dark:text-lime-200">{lei(data?.commissions?.released_escrow_take_est)}</span>
                </div>
                <div className="text-[10px] text-slate-400">{data?.commissions?.rate_note}</div>
              </div>
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2"><Repeat className="w-4 h-4 text-lime-500" /> Abonamente recurente</span>} testid="fc-subs">
              <div className="space-y-3">
                <div className="text-3xl font-black text-slate-900 dark:text-white">{subs.active ?? 0} <span className="text-sm font-medium text-slate-400">active</span></div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 text-center">
                    <div className="text-[10px] uppercase font-bold text-slate-400">MRR</div>
                    <div className="text-lg font-black text-slate-900 dark:text-white">{lei(subs.mrr_ron)}</div>
                    <div className="text-[10px] text-slate-400">≈ {subs.mrr_eur ?? 0} EUR</div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 text-center">
                    <div className="text-[10px] uppercase font-bold text-slate-400">ARR</div>
                    <div className="text-lg font-black text-slate-900 dark:text-white">{lei(subs.arr_ron)}</div>
                    <div className="text-[10px] text-slate-400">proiecție 12 luni</div>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500">Sursă: abonamente House Health active × preț plan.</div>
              </div>
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2"><Wallet className="w-4 h-4 text-emerald-500" /> Revenue total</span>} testid="fc-revenue">
              <div className="space-y-2.5">
                <div className="flex justify-between text-sm"><span className="text-slate-500">Total încasat (all-time)</span><span className="font-black text-slate-900 dark:text-white">{lei(rev.total_paid)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-500">Ultimele 30 zile</span><span className="font-black text-emerald-600 dark:text-emerald-300">{lei(rev.last_30d)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-500">30 zile anterioare</span><span className="font-bold text-slate-700 dark:text-slate-200">{lei(rev.prev_30d)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-500">Plăți în așteptare</span><span className="font-bold text-amber-600 dark:text-amber-300">{lei(rev.pending_amount)}</span></div>
              </div>
            </AdminCard>
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><TrendingUp className="w-4 h-4 text-lime-500" /> Cash Flow — 30 zile ({lei(data?.cash_flow_total_30d)})</span>}
            action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="fc-refresh">Refresh</DSButton>}
            testid="fc-cashflow"
          >
            <div className="flex items-end gap-[3px] h-32" data-testid="fc-cashflow-bars">
              {(data?.cash_flow_30d || []).map((d) => (
                <div key={d.date} className="flex-1 group relative">
                  <div className={`w-full rounded-t ${d.amount > 0 ? "bg-lime-400" : "bg-slate-100 dark:bg-slate-700"}`} style={{ height: `${Math.max(3, (d.amount / maxDay) * 120)}px` }} />
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block text-[9px] bg-slate-900 text-white px-1.5 py-0.5 rounded whitespace-nowrap z-10">
                    {d.date.slice(5)} · {lei(d.amount)}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between text-[9px] text-slate-400 mt-1">
              <span>{data?.cash_flow_30d?.[0]?.date}</span>
              <span>{data?.cash_flow_30d?.[data.cash_flow_30d.length - 1]?.date}</span>
            </div>
          </AdminCard>

          <AdminCard
            title={<span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-lime-500" /> AI Insights — Financial</span>}
            action={<DSButton variant="primary" icon={genInsights ? RefreshCw : Sparkles} disabled={genInsights} onClick={generateInsights} data-testid="fc-insights-btn">{genInsights ? "Analizează…" : "Generează insights"}</DSButton>}
            testid="fc-insights"
          >
            {genInsights && <DSSkeleton kpis={0} blocks={1} />}
            {!genInsights && !insights && <div className="text-sm text-slate-500">AI-ul citește cifrele reale (revenue, escrow, MRR) și îți spune ce se mișcă și unde e riscul.</div>}
            {!genInsights && insights && (
              <div className="space-y-2" data-testid="fc-insights-body">
                {(insights.insights || []).map((ins, i) => (
                  <div key={i} className={`p-3 rounded-xl border text-sm ${ins.severity === "warning" ? "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30" : ins.severity === "positive" ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30" : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700"}`} data-testid={`fc-insight-${i}`}>
                    <div className="font-bold text-slate-900 dark:text-white">{ins.title}</div>
                    <div className="text-xs text-slate-600 dark:text-slate-300">{ins.body}</div>
                  </div>
                ))}
                <div className="text-[10px] text-slate-400">{insights.ai_generated ? "Claude · date reale" : "Fallback"} · {insights.generated_at && new Date(insights.generated_at).toLocaleString("ro-RO")}</div>
              </div>
            )}
          </AdminCard>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
