// PropManage Business Design System — componente standard obligatorii
// Ordine pagină: Titlu → Tabs → ActionBar → KPI → AI Insights → Grafice → Tabele → Acțiuni → Export
import React, { useMemo, useState } from "react";
import {
  Brain, ArrowRight, Search, Download, RefreshCw, TrendingUp, TrendingDown,
  FileText, ChevronUp, ChevronDown, AlertTriangle,
} from "lucide-react";
import { SEMANTIC, BADGE_STYLES, BUTTON_STYLES, CARD } from "./tokens";

export { SEMANTIC, CHART_COLORS, CHART, SP, GRID12, CARD, BADGE_STYLES, BUTTON_STYLES } from "./tokens";

// ── Butoane: primary / secondary / ghost / danger / success ─────────────────
export const DSButton = ({ variant = "primary", icon: Icon, children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-colors disabled:opacity-50 ${BUTTON_STYLES[variant]} ${className}`}
    {...props}
  >
    {Icon && <Icon className="w-3.5 h-3.5" />}
    {children}
  </button>
);

// ── Badge-uri: NEW / AI / BETA / LIVE / ACTIVE / WARNING / ERROR ─────────────
export const DSBadge = ({ type = "NEW", children, className = "" }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wide ${BADGE_STYLES[type] || BADGE_STYLES.NEW} ${className}`}>
    {children || type}
  </span>
);

// ── KPI Card: icon → titlu → valoare mare → evoluție vs perioada trecută ─────
export const KpiCard = ({ icon: Icon, label, value, trend = null, accent = "info", invertTrend = false, onClick, testid }) => {
  const s = SEMANTIC[accent] || SEMANTIC.info;
  const hasTrend = trend !== null && trend !== undefined;
  const good = hasTrend && (invertTrend ? trend <= 0 : trend >= 0);
  const TrendIcon = trend >= 0 ? TrendingUp : TrendingDown;
  return (
    <div
      onClick={onClick}
      data-testid={testid || `kpi-${String(label).toLowerCase().replace(/[^a-z0-9ăâîșț]+/gi, "-")}`}
      className={`${CARD} p-4 min-h-[118px] flex flex-col ${onClick ? "cursor-pointer hover:border-blue-300 dark:hover:border-blue-500/50 transition-colors" : ""}`}
    >
      <div className="flex items-center gap-2">
        {Icon && (
          <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${s.bg}`}>
            <Icon className={`w-4 h-4 ${s.text}`} />
          </span>
        )}
        <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
      </div>
      <div className="mt-2 text-3xl font-black text-slate-900 dark:text-white leading-none">{value}</div>
      <div className="mt-2 flex items-center gap-1 text-[11px] min-w-0">
        {hasTrend ? (
          <>
            <TrendIcon className={`w-3.5 h-3.5 shrink-0 ${good ? "text-emerald-500" : "text-rose-500"}`} />
            <span className={`font-bold ${good ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
              {trend > 0 ? "+" : ""}{trend}%
            </span>
            <span className="text-slate-400 truncate">vs perioada trecută</span>
          </>
        ) : (
          <span className="text-slate-400 truncate">— fără istoric comparabil</span>
        )}
      </div>
    </div>
  );
};

// ── AI Insight Card: obligatoriu după KPI pe orice pagină Business ───────────
// llmModule (opțional): activează „Analiză AI (Claude)" → /api/admin/insights/llm?module=X (cache 6h)
export const AIInsightCard = ({ bullets = [], alerts = [], recommendations = [], onAction, actionLabel = "Vezi recomandări", loading = false, llmModule, testid = "ai-insight-card" }) => {
  const [llm, setLlm] = useState(null);
  const [llmBusy, setLlmBusy] = useState(false);

  const runLlm = async () => {
    setLlmBusy(true);
    try {
      const base = process.env.REACT_APP_BACKEND_URL;
      const res = await fetch(`${base}/api/admin/insights/llm?module=${llmModule}`, { credentials: "include" });
      if (!res.ok) throw new Error();
      setLlm(await res.json());
    } catch { setLlm({ error: true }); }
    setLlmBusy(false);
  };

  const showBullets = llm && !llm.error ? llm.bullets : bullets;
  const showAlerts = llm && !llm.error ? llm.alerts : alerts;
  const showRecs = llm && !llm.error ? llm.recommendations : recommendations;

  return (
  <div className={`${CARD} border-lime-200 dark:border-lime-500/30 p-4`} data-testid={testid}>
    <div className="flex items-center gap-2 flex-wrap">
      <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-lime-50 dark:bg-lime-500/15">
        <Brain className="w-4 h-4 text-lime-700 dark:text-lime-300" />
      </span>
      <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">AI Insights</h3>
      <DSBadge type={llm && !llm.error ? "LIVE" : "AI"}>{llm && !llm.error ? "CLAUDE" : "AI"}</DSBadge>
      {llmModule && (
        <button onClick={runLlm} disabled={llmBusy} data-testid={`${testid}-llm-btn`}
          className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-lime-50 dark:bg-lime-500/15 text-lime-700 dark:text-lime-300 hover:bg-lime-100 dark:hover:bg-lime-500/25 disabled:opacity-50 transition-colors">
          <Brain className={`w-3.5 h-3.5 ${llmBusy ? "animate-pulse" : ""}`} />
          {llmBusy ? "Analizează..." : llm && !llm.error ? "Reanalizează" : "Analiză AI (Claude)"}
        </button>
      )}
    </div>
    {llm?.error && <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">Analiza AI e temporar indisponibilă — se afișează insights-urile standard.</p>}
    {loading || llmBusy ? (
      <div className="mt-3 space-y-2">{[1, 2, 3].map(i => <div key={i} className="h-3 rounded bg-slate-100 dark:bg-slate-700 animate-pulse" style={{ width: `${90 - i * 15}%` }} />)}</div>
    ) : (
      <ul className="mt-3 space-y-1.5">
        {showAlerts.map((a, i) => (
          <li key={`a${i}`} className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {a}
          </li>
        ))}
        {showBullets.map((b, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200">
            <span className="w-1 h-1 rounded-full bg-lime-500 mt-2 shrink-0" /> {b}
          </li>
        ))}
        {llm && !llm.error && showRecs.map((r, i) => (
          <li key={`r${i}`} className="flex items-start gap-2 text-sm font-medium text-lime-700 dark:text-lime-300">
            <ArrowRight className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {r}
          </li>
        ))}
        {!showAlerts.length && !showBullets.length && <li className="text-sm text-slate-400">Colectăm date — insights-urile apar după primele sesiuni.</li>}
      </ul>
    )}
    {(!llm || llm.error) && (recommendations.length > 0 || onAction) && (
      <button
        onClick={onAction}
        data-testid={`${testid}-action`}
        className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-lime-700 dark:text-lime-300 hover:gap-2 transition-all"
      >
        {actionLabel} <ArrowRight className="w-3.5 h-3.5" />
      </button>
    )}
  </div>
  );
};

// ── ChartCard: container standard pentru orice grafic ───────────────────────
export const ChartCard = ({ title, subtitle, actions, children, className = "", testid }) => (
  <div className={`${CARD} p-4 ${className}`} data-testid={testid}>
    <div className="flex items-center justify-between mb-3">
      <div>
        <h3 className="font-bold text-slate-800 dark:text-slate-100">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-1.5">{actions}</div>}
    </div>
    {children}
  </div>
);

// ── EmptyState: nicio pagină goală ───────────────────────────────────────────
export const EmptyState = ({ icon: Icon = Search, title = "Nu există încă date.", hint, action, testid = "ds-empty" }) => (
  <div className="flex flex-col items-center justify-center py-10 px-4 text-center" data-testid={testid}>
    <span className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-700/50 flex items-center justify-center">
      <Icon className="w-5 h-5 text-slate-400" />
    </span>
    <p className="mt-3 text-sm font-bold text-slate-600 dark:text-slate-300">{title}</p>
    {hint && <p className="mt-1 text-xs text-slate-400 max-w-xs">{hint}</p>}
    {action && <div className="mt-3">{action}</div>}
  </div>
);

// ── Skeleton loading unic (fără spinnere diferite) ───────────────────────────
export const DSSkeleton = ({ kpis = 6, blocks = 2 }) => (
  <div className="space-y-6" data-testid="ds-skeleton">
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {Array.from({ length: kpis }).map((_, i) => (
        <div key={i} className={`${CARD} p-4 h-[118px] animate-pulse`}>
          <div className="h-3 w-2/3 rounded bg-slate-100 dark:bg-slate-700" />
          <div className="mt-4 h-8 w-1/2 rounded bg-slate-100 dark:bg-slate-700" />
          <div className="mt-3 h-3 w-3/4 rounded bg-slate-100 dark:bg-slate-700" />
        </div>
      ))}
    </div>
    {Array.from({ length: blocks }).map((_, i) => (
      <div key={i} className={`${CARD} p-4 h-56 animate-pulse`}>
        <div className="h-4 w-40 rounded bg-slate-100 dark:bg-slate-700" />
        <div className="mt-4 h-36 rounded bg-slate-50 dark:bg-slate-700/50" />
      </div>
    ))}
  </div>
);

// ── ActionBar: perioadă · refresh · CSV · PDF — același loc pe toate paginile ─
export const ActionBar = ({ periods = [["day", "Azi"], ["week", "7 zile"], ["month", "30 zile"]], period, onPeriod, onRefresh, loading, onExportCsv, onExportPdf, extra, testidPrefix = "ds" }) => (
  <div className="flex flex-wrap items-center gap-1.5 justify-end" data-testid={`${testidPrefix}-action-bar`}>
    {extra}
    {onPeriod && periods.map(([id, label]) => (
      <button key={id} onClick={() => onPeriod(id)} data-testid={`${testidPrefix}-period-${id}`}
        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${period === id ? "bg-lime-400 text-slate-900" : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700"}`}>
        {label}
      </button>
    ))}
    {onExportCsv && (
      <DSButton variant="secondary" icon={Download} onClick={onExportCsv} data-testid={`${testidPrefix}-export-csv`}>CSV</DSButton>
    )}
    {onExportPdf && (
      <DSButton variant="danger" icon={FileText} onClick={onExportPdf} data-testid={`${testidPrefix}-export-pdf`}>PDF</DSButton>
    )}
    {onRefresh && (
      <button onClick={onRefresh} data-testid={`${testidPrefix}-refresh`}
        className="p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700">
        <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? "animate-spin" : ""}`} />
      </button>
    )}
  </div>
);

// ── TabBar: navigare secundară identică pe toate modulele ────────────────────
export const TabBar = ({ tabs, active, onChange, testidPrefix = "ds-tab" }) => (
  <div className="flex flex-wrap items-center gap-2" data-testid={`${testidPrefix}-bar`}>
    {tabs.map(([id, label, Icon]) => (
      <button key={id} onClick={() => onChange(id)} data-testid={`${testidPrefix}-${id}`}
        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-colors ${active === id ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700"}`}>
        {Icon && <Icon className="w-[18px] h-[18px]" />} {label}
      </button>
    ))}
  </div>
);

// ── DataTable: header sticky · sortare · căutare · export · hover ────────────
export const DataTable = ({ title, columns, rows, searchKeys = [], exportName, emptyTitle = "Nu există încă date.", emptyHint, maxHeight = "30rem", testid = "ds-table", headerExtra }) => {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState(null);

  const filtered = useMemo(() => {
    let out = rows || [];
    if (q && searchKeys.length) {
      const needle = q.toLowerCase();
      out = out.filter(r => searchKeys.some(k => String(r[k] ?? "").toLowerCase().includes(needle)));
    }
    if (sort) {
      out = [...out].sort((a, b) => {
        const av = a[sort.key], bv = b[sort.key];
        const c = typeof av === "number" && typeof bv === "number" ? av - bv : String(av ?? "").localeCompare(String(bv ?? ""));
        return sort.dir === "asc" ? c : -c;
      });
    }
    return out;
  }, [rows, q, sort, searchKeys]);

  const toggleSort = (key) => setSort(s => (s?.key !== key ? { key, dir: "desc" } : s.dir === "desc" ? { key, dir: "asc" } : null));

  const exportCsv = () => {
    const head = columns.map(c => `"${c.label}"`).join(",");
    const body = filtered.map(r => columns.map(c => `"${String(r[c.key] ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([`\uFEFF${head}\n${body}`], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${exportName || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className={`${CARD} overflow-hidden`} data-testid={testid}>
      <div className="flex flex-wrap items-center gap-2 p-4 pb-3">
        {title && <h3 className="font-bold text-slate-800 dark:text-slate-100">{title}</h3>}
        <div className="ml-auto flex items-center gap-2">
          {headerExtra}
          {searchKeys.length > 0 && (
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută..." data-testid={`${testid}-search`}
                className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-xs w-36 focus:w-48 transition-all outline-none focus:border-blue-400" />
            </div>
          )}
          {exportName && <DSButton variant="secondary" icon={Download} onClick={exportCsv} data-testid={`${testid}-export`}>CSV</DSButton>}
        </div>
      </div>
      {filtered.length === 0 ? (
        <EmptyState title={emptyTitle} hint={emptyHint} testid={`${testid}-empty`} />
      ) : (
        <div className="overflow-auto" style={{ maxHeight }}>
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-white dark:bg-slate-800">
              <tr className="text-left text-[11px] uppercase text-slate-400 border-b border-slate-100 dark:border-slate-700">
                {columns.map(c => (
                  <th key={c.key} className={`px-4 py-2 whitespace-nowrap ${c.sortable !== false ? "cursor-pointer select-none hover:text-slate-600 dark:hover:text-slate-200" : ""}`}
                    onClick={() => c.sortable !== false && toggleSort(c.key)}>
                    <span className="inline-flex items-center gap-0.5">
                      {c.label}
                      {sort?.key === c.key && (sort.dir === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={r.id || r.key || i} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  {columns.map(c => (
                    <td key={c.key} className="px-4 py-2 whitespace-nowrap">{c.render ? c.render(r) : r[c.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
