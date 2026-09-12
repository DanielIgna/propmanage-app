// Marketing Performance Loop tab — track actual vs predicted + Claude learnings
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  TrendingUp, TrendingDown, Loader2, Sparkles, BarChart3,
  AlertTriangle, Target, Brain, Award, AlertCircle, DollarSign,
  Activity, RefreshCw, GitBranch,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const RON = (n) => `${Number(n || 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} RON`;
const PCT = (n) => `${n >= 0 ? "+" : ""}${Number(n || 0).toFixed(1)}%`;

const KpiBox = ({ icon: Icon, label, value, sub, color = "text-violet-500", testid }) => (
  <div className="rounded-xl p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900" data-testid={testid}>
    <div className="flex items-center justify-between mb-1">
      <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium">{label}</span>
      <Icon className={`w-4 h-4 ${color}`} />
    </div>
    <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
    {sub != null && <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{sub}</div>}
  </div>
);

const AccuracyBar = ({ label, value }) => {
  // value = avg absolute delta % — lower is better
  const score = Math.max(0, 100 - value);
  const color = score >= 80 ? "from-emerald-500 to-emerald-400" : score >= 60 ? "from-amber-500 to-amber-400" : "from-rose-500 to-rose-400";
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-slate-600 dark:text-slate-300">{label}</span>
        <span className="font-bold text-slate-900 dark:text-white">{score.toFixed(0)}% acuratețe <span className="text-slate-400 font-normal">(±{value.toFixed(1)}%)</span></span>
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${color} transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
};

const PerformanceTab = () => {
  const [summary, setSummary] = useState(null);
  const [learnings, setLearnings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [genBusy, setGenBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [sumR, lR] = await Promise.all([
        ax.get("/api/admin/marketing/performance/summary"),
        ax.get("/api/admin/marketing/performance/learnings/active"),
      ]);
      setSummary(sumR.data);
      setLearnings(lR.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const generateLearnings = async () => {
    setGenBusy(true); setError("");
    try {
      const r = await ax.post("/api/admin/marketing/performance/learnings/generate");
      setLearnings({ ...r.data, active: true });
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setGenBusy(false); }
  };

  if (loading) return <div className="text-center py-12"><Loader2 className="w-7 h-7 animate-spin mx-auto text-slate-400" /></div>;
  if (error) return <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 text-sm border border-rose-200 dark:border-rose-500/30"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>;
  if (!summary) return null;

  return (
    <div className="space-y-6" data-testid="mkt-tab-performance">
      {/* Empty state */}
      {summary.logs_count === 0 ? (
        <div className="p-8 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 text-center" data-testid="perf-empty">
          <Activity className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="font-bold text-slate-900 dark:text-white mb-1">Marketing Performance Loop</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Niciun log de performanță încă. Aprobă o campanie, rulează-o pe Meta/Google Ads, apoi loghează rezultatele reale prin butonul &quot;Loghează performanță&quot; din pagina campaniei. Sistemul va calcula automat deltas vs predicted KPIs.
          </p>
        </div>
      ) : (
        <>
          {/* Totals */}
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-fuchsia-500" /> Totaluri agregate ({summary.logs_count} loguri)</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <KpiBox icon={DollarSign} label="Total cheltuit" value={RON(summary.totals.spent_ron)} color="text-rose-500" testid="perf-spent" />
              <KpiBox icon={Target} label="Total leads" value={summary.totals.leads} color="text-emerald-500" testid="perf-leads" />
              <KpiBox icon={Activity} label="Total clicks" value={summary.totals.clicks?.toLocaleString("ro-RO")}
                sub={`${summary.totals.impressions?.toLocaleString("ro-RO")} impresii`} color="text-blue-500" testid="perf-clicks" />
              <KpiBox icon={Award} label="Conversii" value={summary.totals.conversions} color="text-violet-500" testid="perf-conversions" />
            </div>
          </div>

          {/* Accuracy */}
          {Object.keys(summary.accuracy || {}).length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2"><GitBranch className="w-4 h-4 text-violet-500" /> Acuratețe predicții AI</h3>
              <div className="space-y-3" data-testid="perf-accuracy">
                <AccuracyBar label="Impresii" value={summary.accuracy.impressions_avg_abs_delta_pct} />
                <AccuracyBar label="Click-uri" value={summary.accuracy.clicks_avg_abs_delta_pct} />
                <AccuracyBar label="Leads" value={summary.accuracy.leads_avg_abs_delta_pct} />
                <AccuracyBar label="CPC" value={summary.accuracy.cpc_avg_abs_delta_pct} />
              </div>
            </div>
          )}

          {/* Top performers vs worst */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
              <h4 className="text-sm font-bold text-emerald-700 dark:text-emerald-400 mb-3 flex items-center gap-1.5"><TrendingUp className="w-4 h-4" /> Top performers (leads vs predicție)</h4>
              <div className="space-y-2">
                {summary.top_performers.map((p) => (
                  <div key={p.id} className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-sm" data-testid={`top-${p.id}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 dark:text-white">{p.leads} leads</span>
                      <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400">{PCT(p.deltas?.leads_delta_pct)}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">Cheltuit: {RON(p.spent_ron)} · CPL: {RON(p.deltas?.cpl_actual_ron)}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
              <h4 className="text-sm font-bold text-rose-700 dark:text-rose-400 mb-3 flex items-center gap-1.5"><TrendingDown className="w-4 h-4" /> Slab performante (de optimizat)</h4>
              <div className="space-y-2">
                {summary.worst_performers.map((p) => (
                  <div key={p.id} className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-sm" data-testid={`worst-${p.id}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 dark:text-white">{p.leads} leads</span>
                      <span className="text-xs font-bold text-rose-700 dark:text-rose-400">{PCT(p.deltas?.leads_delta_pct)}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">Cheltuit: {RON(p.spent_ron)} · CPL: {RON(p.deltas?.cpl_actual_ron)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* By category */}
          {summary.by_category?.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
              <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Performanță pe categorie</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                      <th className="text-left py-2">Categorie</th>
                      <th className="text-right">Leads</th>
                      <th className="text-right">Spent</th>
                      <th className="text-right">CPL</th>
                      <th className="text-right">Campanii</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_category.map((c, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800/50" data-testid={`cat-row-${i}`}>
                        <td className="py-2 font-medium text-slate-900 dark:text-white">{c.category}</td>
                        <td className="text-right font-bold text-emerald-600 dark:text-emerald-400">{c.leads}</td>
                        <td className="text-right text-slate-600 dark:text-slate-300">{RON(c.spent_ron)}</td>
                        <td className="text-right text-slate-600 dark:text-slate-300">{RON(c.cpl_ron)}</td>
                        <td className="text-right text-slate-400">{c.campaigns_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* AI Learnings */}
      <div className="bg-gradient-to-br from-violet-50 to-fuchsia-50 dark:from-violet-500/10 dark:to-fuchsia-500/10 rounded-xl p-5 border border-violet-200 dark:border-violet-500/30">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Brain className="w-4 h-4 text-violet-500" /> Învățăminte AI (calibrare automată)
          </h3>
          <button onClick={generateLearnings} disabled={genBusy || summary.logs_count < 3}
            title={summary.logs_count < 3 ? "Necesare minim 3 loguri de performanță" : ""}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
            data-testid="generate-learnings-btn">
            {genBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {genBusy ? "Claude analizează…" : (learnings?.learnings?.length ? "Regenerează" : "Generează învățăminte")}
          </button>
        </div>

        {!learnings?.learnings?.length ? (
          <div className="text-sm text-slate-600 dark:text-slate-300 text-center py-4" data-testid="learnings-empty">
            <AlertCircle className="w-5 h-5 inline mr-1 text-slate-400" />
            Niciun set de învățăminte activ. {summary.logs_count >= 3
              ? `Apasă "Generează învățăminte" pentru a permite AI-ului să analizeze istoricul și să calibreze KPI-urile viitoare.`
              : `Necesare minim 3 loguri de performanță (acum: ${summary.logs_count}).`}
          </div>
        ) : (
          <>
            <div className="text-xs text-slate-500 mb-3">
              Aplicate automat la următoarele drafts · Sample size: {learnings.sample_size} loguri · Generate la {new Date(learnings.generated_at).toLocaleString("ro-RO")}
            </div>
            <div className="space-y-2" data-testid="learnings-list">
              {learnings.learnings.map((l, i) => (
                <div key={i} className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-violet-200 dark:border-violet-500/30" data-testid={`learning-${i}`}>
                  <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300">{l.category}</span>
                      <span className="text-[10px] uppercase font-bold text-slate-500">{l.metric}</span>
                    </div>
                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                      l.confidence === "high" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300"
                      : l.confidence === "medium" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
                      : "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                    }`}>{l.confidence}</span>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-200">{l.observation}</p>
                  <p className="text-xs text-violet-600 dark:text-violet-400 mt-1 font-mono">→ {l.adjustment}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Performance log modal — used inside CampaignsTab DetailModal
export const LogPerformanceModal = ({ campaignId, predictedKpis, onClose, onLogged }) => {
  const [form, setForm] = useState({ impressions: 0, clicks: 0, leads: 0, conversions: 0, spent_ron: 0, notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const r = await ax.post(`/api/admin/marketing/campaigns/${campaignId}/performance`, {
        impressions: Number(form.impressions),
        clicks: Number(form.clicks),
        leads: Number(form.leads),
        conversions: Number(form.conversions),
        spent_ron: Number(form.spent_ron),
        notes: form.notes,
      });
      onLogged(r.data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="log-performance-modal">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white">
          <h3 className="font-bold flex items-center gap-2"><Activity className="w-4 h-4" /> Loghează performanță reală</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white">✕</button>
        </div>
        <div className="p-5 space-y-3">
          {predictedKpis && (
            <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-xs text-slate-600 dark:text-slate-300">
              <strong>Predicție AI:</strong> {predictedKpis.expected_impressions || "?"} impresii · {predictedKpis.expected_clicks || "?"} clicks · {predictedKpis.expected_leads || "?"} leads · CPC {predictedKpis.expected_cpc_ron || "?"} RON
            </div>
          )}
          {[
            { key: "impressions", label: "Impresii reale", placeholder: "ex: 15000" },
            { key: "clicks", label: "Click-uri reale", placeholder: "ex: 420" },
            { key: "leads", label: "Leads generați", placeholder: "ex: 35" },
            { key: "conversions", label: "Conversii", placeholder: "ex: 8" },
            { key: "spent_ron", label: "Buget cheltuit (RON)", placeholder: "ex: 280" },
          ].map(f => (
            <div key={f.key}>
              <label className="text-xs uppercase text-slate-500 font-medium mb-1 block">{f.label}</label>
              <input type="number" min={0} value={form[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.placeholder}
                className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
                data-testid={`log-${f.key}`} />
            </div>
          ))}
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1 block">Notițe (opțional)</label>
            <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
              data-testid="log-notes" />
          </div>
          {err && <div className="text-rose-500 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{err}</div>}
          <button onClick={submit} disabled={busy}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="log-submit">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
            Salvează log
          </button>
        </div>
      </div>
    </div>
  );
};

export default PerformanceTab;
