// AIActivityStream — live timeline of autonomous AI actions across PropManage.
// Pulls /api/admin/ai-activity, auto-refreshes every 60s, color-coded by severity.
import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  Activity, Gauge, Zap, AlertTriangle, CheckCircle2, Search, ShieldCheck,
  Shield, Save, Loader2, RefreshCcw, Sparkles,
} from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const ICON_MAP = {
  Activity, Gauge, Zap, AlertTriangle, CheckCircle2, Search, ShieldCheck, Shield, Save, Sparkles,
};

const SEVERITY_STYLES = {
  info:     { dot: "bg-blue-500",    text: "text-blue-700 dark:text-blue-300",       border: "border-blue-200 dark:border-blue-500/30",       bg: "bg-blue-50 dark:bg-blue-500/10" },
  success:  { dot: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-300", border: "border-emerald-200 dark:border-emerald-500/30", bg: "bg-emerald-50 dark:bg-emerald-500/10" },
  warning:  { dot: "bg-amber-500",   text: "text-amber-700 dark:text-amber-300",     border: "border-amber-200 dark:border-amber-500/30",     bg: "bg-amber-50 dark:bg-amber-500/10" },
  critical: { dot: "bg-red-500",     text: "text-red-700 dark:text-red-300",         border: "border-red-200 dark:border-red-500/30",         bg: "bg-red-50 dark:bg-red-500/10" },
};

const formatRelative = (iso) => {
  if (!iso) return "—";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "—";
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return "acum";
  if (diff < 3600) return `acum ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `acum ${Math.floor(diff / 3600)}h`;
  if (diff < 604800) return `acum ${Math.floor(diff / 86400)}z`;
  return new Date(iso).toLocaleDateString("ro-RO");
};

const ActivityRow = ({ event }) => {
  const Icon = ICON_MAP[event.icon] || Activity;
  const s = SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.info;
  return (
    <div className="flex items-start gap-3 group" data-testid={`ai-activity-row-${event.kind}`}>
      <div className="relative flex flex-col items-center pt-1">
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${s.bg} ${s.border} border shrink-0`}>
          <Icon className={`w-3.5 h-3.5 ${s.text}`} />
        </div>
        <div className="w-px flex-1 bg-slate-200 dark:bg-white/5 mt-1 group-last:hidden" style={{ minHeight: 8 }} />
      </div>
      <div className="flex-1 min-w-0 pb-3">
        <div className="flex items-baseline gap-2 flex-wrap">
          <div className={`text-sm font-medium ${s.text}`}>{event.title}</div>
          <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-full ${s.bg} ${s.border} ${s.text} border`}>
            {event.severity}
          </span>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 ml-auto font-mono">{formatRelative(event.ts)}</span>
        </div>
        {event.summary && (
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{event.summary}</div>
        )}
      </div>
    </div>
  );
};

const KindFilter = ({ counts, active, onChange }) => {
  const entries = Object.entries(counts || {});
  if (entries.length === 0) return null;
  return (
    <div className="flex gap-1.5 flex-wrap text-[11px]">
      <button
        onClick={() => onChange(null)}
        className={`px-2 py-1 rounded-full border transition-colors ${
          !active
            ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white"
            : "bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10"
        }`}
        data-testid="ai-activity-filter-all"
      >
        Tot
      </button>
      {entries.map(([kind, n]) => (
        <button
          key={kind}
          onClick={() => onChange(kind)}
          className={`px-2 py-1 rounded-full border transition-colors ${
            active === kind
              ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white"
              : "bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10"
          }`}
          data-testid={`ai-activity-filter-${kind}`}
        >
          {kind.replace(/[._]/g, " ")} · {n}
        </button>
      ))}
    </div>
  );
};

export const AIActivityStream = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const timerRef = useRef(null);

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const { data } = await ax.get("/api/admin/ai-activity", { params: { hours: 168, limit: 60 } });
      setData(data);
      setLastRefresh(new Date());
      // Reset auto-refresh timer on any successful load so manual refresh
      // doesn't cause a near-immediate auto-refresh after.
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = setInterval(() => load(true), 60000);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false);
    // Auto-refresh every 60s
    timerRef.current = setInterval(() => load(true), 60000);
    return () => clearInterval(timerRef.current);
  }, []);

  const items = (data?.items || []).filter(e => !filter || e.kind === filter);
  const sev = data?.summary?.by_severity || {};

  return (
    <AdminCard testid="ai-activity-stream">
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-2xl bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/30 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-base">Activity AI — ce face platforma singură</h3>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300 border border-violet-300/40">
                Live · 60s
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Timeline unificat al acțiunilor autonome: snapshot-uri, auto-match, scan-uri AI, findings detectate, smoke tests. Ultimele 7 zile.
            </p>
            <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1" data-testid="ai-activity-sev-info"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> {sev.info || 0} info</span>
              <span className="flex items-center gap-1" data-testid="ai-activity-sev-success"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> {sev.success || 0} success</span>
              <span className="flex items-center gap-1" data-testid="ai-activity-sev-warning"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> {sev.warning || 0} warn</span>
              <span className="flex items-center gap-1" data-testid="ai-activity-sev-critical"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /> {sev.critical || 0} critic</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => load(false)}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 disabled:opacity-50 transition-colors shrink-0"
          data-testid="ai-activity-refresh"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCcw className="w-3.5 h-3.5" />}
          Reîmprospătează
        </button>
      </div>

      {data?.summary?.by_kind && (
        <div className="mb-3">
          <KindFilter counts={data.summary.by_kind} active={filter} onChange={setFilter} />
        </div>
      )}

      {error && (
        <div className="text-xs text-red-600 dark:text-red-400 flex items-center gap-2 py-3">
          <AlertTriangle className="w-3.5 h-3.5" /> {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 py-6 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă activitatea...
        </div>
      )}

      {data && items.length === 0 && !loading && (
        <div className="text-sm text-slate-500 dark:text-slate-400 italic py-6 text-center" data-testid="ai-activity-empty">
          Niciun eveniment în ultimele 7 zile{filter ? ` pentru ${filter}` : ""}.
        </div>
      )}

      {items.length > 0 && (
        <div className="max-h-[500px] overflow-y-auto pr-1" data-testid="ai-activity-list">
          {items.map((e, i) => (
            <ActivityRow key={`${e.kind}-${e.ts}-${i}`} event={e} />
          ))}
        </div>
      )}

      {lastRefresh && (
        <div className="text-[10px] text-slate-400 dark:text-slate-500 text-right mt-2 font-mono">
          Ultimul refresh: {lastRefresh.toLocaleTimeString("ro-RO")}
        </div>
      )}
    </AdminCard>
  );
};

export default AIActivityStream;
