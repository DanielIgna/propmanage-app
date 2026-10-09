// PlatformRoadmapPage — Evolution board: ce e construit vs ce rămâne, per modul.
// Cod culoare: ROȘU = urgent · GALBEN = prioritar · VERDE = îmbunătățire.
// AI Analyzer (Claude) analizează tot board-ul și recomandă ordinea de construire.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Map, Sparkles, CheckCircle2, Circle, ChevronDown, ChevronUp,
  AlertTriangle, Flame, Zap, Leaf, Brain, RefreshCw, TrendingUp,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const PRIORITY_META = {
  urgent:      { label: "URGENT",       icon: Flame, dot: "bg-rose-500",  cls: "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/40", badge: "bg-rose-500 text-white" },
  priority:    { label: "PRIORITAR",    icon: Zap,   dot: "bg-amber-400", cls: "bg-amber-50 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/40", badge: "bg-amber-400 text-slate-900" },
  improvement: { label: "ÎMBUNĂTĂȚIRE", icon: Leaf,  dot: "bg-emerald-500", cls: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/40", badge: "bg-emerald-500 text-white" },
};

const STATUS_META = {
  done:        { label: "Construit",    cls: "text-emerald-600 dark:text-emerald-300" },
  in_progress: { label: "În lucru",     cls: "text-amber-600 dark:text-amber-300" },
  planned:     { label: "De construit", cls: "text-slate-500 dark:text-slate-400" },
};

const ModuleCard = ({ m, onPatch, busy }) => {
  const [open, setOpen] = useState(false);
  const pm = PRIORITY_META[m.priority] || PRIORITY_META.improvement;
  const sm = STATUS_META[m.status] || STATUS_META.planned;
  return (
    <div className={`rounded-2xl border p-4 space-y-3 ${pm.cls}`} data-testid={`rm-module-${m.key}`}>
      <div className="flex items-start gap-3">
        <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${pm.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded ${pm.badge}`}>{pm.label}</span>
            <span className={`text-[10px] font-bold ${sm.cls}`}>{sm.label}</span>
            <span className="text-[10px] text-slate-400">{m.group}</span>
          </div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white mt-1">{m.title}</h4>
        </div>
        <button onClick={() => setOpen(!open)} className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" data-testid={`rm-toggle-${m.key}`}>
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-white/70 dark:bg-slate-900/50 rounded-full overflow-hidden border border-slate-200 dark:border-slate-700">
          <div className={`h-full ${m.progress >= 100 ? "bg-emerald-500" : m.progress >= 40 ? "bg-lime-400" : "bg-amber-400"}`} style={{ width: `${m.progress || 0}%` }} />
        </div>
        <span className="text-xs font-black text-slate-700 dark:text-slate-200 w-10 text-right">{m.progress || 0}%</span>
      </div>

      {open && (
        <div className="space-y-3 pt-1" data-testid={`rm-detail-${m.key}`}>
          {m.built?.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 mb-1">✓ Construit</div>
              <ul className="space-y-1">
                {m.built.map((b, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-700 dark:text-slate-200">
                    <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 text-emerald-500 shrink-0" />{b}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {m.remaining?.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">○ De construit</div>
              <ul className="space-y-1">
                {m.remaining.map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <Circle className="w-3.5 h-3.5 mt-0.5 text-slate-400 shrink-0" />{r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {m.notes && <div className="text-[11px] italic text-slate-500">{m.notes}</div>}
          <div className="flex items-center gap-2 flex-wrap pt-1">
            <span className="text-[10px] text-slate-400 mr-1">Setează:</span>
            {Object.entries(PRIORITY_META).map(([k, v]) => (
              <button key={k} disabled={busy || m.priority === k} onClick={() => onPatch(m.key, { priority: k })}
                className={`text-[9px] font-black uppercase px-2 py-1 rounded ${m.priority === k ? v.badge : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-500"}`}
                data-testid={`rm-set-${k}-${m.key}`}>
                {v.label}
              </button>
            ))}
            {Object.entries(STATUS_META).map(([k, v]) => (
              <button key={k} disabled={busy || m.status === k} onClick={() => onPatch(m.key, { status: k, ...(k === "done" ? { progress: 100 } : {}) })}
                className={`text-[9px] font-bold px-2 py-1 rounded ${m.status === k ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900" : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-500"}`}
                data-testid={`rm-status-${k}-${m.key}`}>
                {v.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function PlatformRoadmapPage() {
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    try {
      const [r, a] = await Promise.all([
        ax.get("/admin/roadmap"),
        ax.get("/admin/roadmap/analysis/latest"),
      ]);
      setData(r.data);
      setAnalysis(a.data.result ? { ...a.data.result, generated_at: a.data.generated_at } : null);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const onPatch = async (key, patch) => {
    setBusy(true);
    try {
      await ax.patch(`/admin/roadmap/${key}`, patch);
      await load();
    } catch (e) { /* silent */ }
    setBusy(false);
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      const r = await ax.post("/admin/roadmap/analyze");
      setAnalysis(r.data);
    } catch (e) { /* silent */ }
    setAnalyzing(false);
  };

  const items = (data?.items || []).filter((m) => filter === "all" || m.priority === filter);
  const counts = data?.counts || {};

  return (
    <AdminLayoutMetronic
      title="Roadmap · Evoluția Platformei"
      subtitle="Ce e construit · ce e în lucru · ce rămâne — ROȘU urgent · GALBEN prioritar · VERDE îmbunătățire"
    >
      {loading ? <DSSkeleton kpis={4} blocks={1} /> : (
        <div className="space-y-6" data-testid="roadmap-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={TrendingUp} label="Progres general"  value={`${data?.overall_progress ?? 0}%`} accent="ai"      testid="rm-kpi-progress" />
            <KpiCard icon={Flame}      label="Urgente (roșu)"    value={counts.urgent ?? 0}                accent="critical"  testid="rm-kpi-urgent" />
            <KpiCard icon={Zap}        label="Prioritare (galben)" value={counts.priority ?? 0}            accent="warning" testid="rm-kpi-priority" />
            <KpiCard icon={CheckCircle2} label="Module construite" value={`${counts.done ?? 0}/${data?.total ?? 0}`} accent="success" testid="rm-kpi-done" />
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Brain className="w-4 h-4 text-lime-500" /> AI Analyzer — analiză peste tot board-ul</span>}
            action={<DSButton variant="primary" icon={analyzing ? RefreshCw : Sparkles} disabled={analyzing} onClick={runAnalysis} data-testid="rm-analyze-btn">{analyzing ? "Claude analizează…" : "Analizează cu AI"}</DSButton>}
            testid="rm-analysis"
          >
            {!analysis && !analyzing && <EmptyState icon={Brain} title="Nicio analiză încă" hint="AI-ul citește toate modulele (construit vs rămas) și îți spune exact ce să construiești săptămâna asta, quick wins și riscuri." />}
            {analyzing && <DSSkeleton kpis={0} blocks={1} />}
            {analysis && !analyzing && (
              <div className="space-y-4" data-testid="rm-analysis-body">
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{analysis.verdict}</p>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30">
                    <div className="text-[10px] font-black uppercase tracking-wider text-rose-700 dark:text-rose-300 mb-1.5">🎯 Priorități săptămâna asta</div>
                    <ul className="space-y-1 text-xs text-slate-700 dark:text-slate-200 list-decimal ml-4">
                      {(analysis.top_priorities || []).map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                  <div className="p-3 rounded-xl bg-lime-50 dark:bg-lime-500/10 border border-lime-200 dark:border-lime-500/30">
                    <div className="text-[10px] font-black uppercase tracking-wider text-lime-700 dark:text-lime-300 mb-1.5">⚡ Quick wins</div>
                    <ul className="space-y-1 text-xs text-slate-700 dark:text-slate-200 list-disc ml-4">
                      {(analysis.quick_wins || []).map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                </div>
                {analysis.risks?.length > 0 && (
                  <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
                    <div className="text-[10px] font-black uppercase tracking-wider text-amber-700 dark:text-amber-300 mb-1.5"><AlertTriangle className="w-3 h-3 inline mr-1" />Riscuri dacă amânăm</div>
                    <ul className="space-y-1 text-xs text-slate-700 dark:text-slate-200 list-disc ml-4">
                      {analysis.risks.map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                )}
                {analysis.overlaps?.length > 0 && (
                  <div className="text-xs text-slate-500"><b>Suprapuneri de consolidat:</b> {analysis.overlaps.join(" · ")}</div>
                )}
                {analysis.generated_at && <div className="text-[10px] text-slate-400">Generat: {new Date(analysis.generated_at).toLocaleString("ro-RO")}</div>}
              </div>
            )}
          </AdminCard>

          <div className="flex gap-2 flex-wrap">
            {["all", "urgent", "priority", "improvement"].map((f) => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${filter === f ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900" : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"}`}
                data-testid={`rm-filter-${f}`}>
                {f === "all" ? `Toate (${data?.total ?? 0})` : `${PRIORITY_META[f].label} (${counts[f] || 0})`}
              </button>
            ))}
          </div>

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((m) => <ModuleCard key={m.key} m={m} onPatch={onPatch} busy={busy} />)}
          </div>
          {!items.length && <EmptyState icon={Map} title="Niciun modul pe acest filtru" hint="Schimbă filtrul de prioritate." />}
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
