// RepairAuditLog — analytics per finding pattern: shows which AI repair suggestions
// are actually effective (applied/decided ratio) vs which patterns the LLM struggles with.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { BarChart3, TrendingUp, TrendingDown, RefreshCw, ChevronRight, Trophy, AlertOctagon, X, Calendar, Bell, BellOff, Send, History } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const WINDOWS = [
  { id: 7, label: "7 zile" },
  { id: 30, label: "30 zile" },
  { id: 90, label: "90 zile" },
];

const fmtPct = (v) => (v == null ? "—" : `${v}%`);

const Bar = ({ pct, color }) => (
  <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
    <div className={`h-full ${color} transition-all`} style={{ width: `${Math.min(100, Math.max(0, pct || 0))}%` }} />
  </div>
);

const Stat = ({ label, value, color }) => (
  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-2.5">
    <div className={`text-2xl font-semibold ${color || "text-slate-900 dark:text-slate-100"}`}>{value}</div>
    <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">{label}</div>
  </div>
);

// Color a cell based on effectiveness and activity volume
const cellColor = (c) => {
  if (!c || c.count === 0) return "bg-slate-100 dark:bg-slate-800/50 border-slate-200/50 dark:border-slate-700/40";
  if (c.decided === 0) return "bg-slate-200 dark:bg-slate-700 border-slate-300/60 dark:border-slate-600/60"; // pending
  const e = c.effectiveness_pct;
  if (e >= 80) return "bg-emerald-500 border-emerald-600";
  if (e >= 50) return "bg-emerald-300 border-emerald-400 dark:bg-emerald-500/60";
  if (e >= 30) return "bg-amber-400 border-amber-500";
  return "bg-red-400 border-red-500";
};

const WD_LABELS = ["L", "Ma", "Mi", "J", "V", "S", "D"];

const EffectivenessTrend = () => {
  const [weeks, setWeeks] = useState(4);
  const [data, setData] = useState(null);
  const [hovered, setHovered] = useState(null);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/admin/ai/repair-suggestions/trend?weeks=${weeks}`);
      setData(r.data);
    } catch { /* ignore */ }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [weeks]);

  if (!data) return null;

  // Build a 7-rows × N-cols grid. Cells are sequential by date.
  const cells = data.cells || [];
  const grid = Array.from({ length: 7 }, () => []);
  cells.forEach((c) => { grid[c.weekday].push(c); });

  const t = data.totals || {};
  const delta = t.trend_delta_pct;
  const trendUp = delta != null && delta > 0;
  const trendDown = delta != null && delta < 0;

  return (
    <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-700 p-4" data-testid="repair-trend-chart">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <Calendar className="w-4 h-4 text-purple-500" />
        <div className="font-semibold text-sm">Trend eficacitate AI ({weeks * 7} zile)</div>
        <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 ml-auto" data-testid="trend-weeks-selector">
          {[2, 4, 8, 12].map(w => (
            <button
              key={w}
              onClick={() => setWeeks(w)}
              className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition-colors ${
                weeks === w ? "bg-white dark:bg-slate-900 text-purple-600 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
              data-testid={`trend-weeks-${w}`}
            >{w}săpt</button>
          ))}
        </div>
      </div>

      {/* Trend stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3 text-xs">
        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400">Activitate total</div>
          <div className="text-lg font-semibold text-slate-800 dark:text-slate-200 tabular-nums">{t.count}</div>
        </div>
        <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 p-2">
          <div className="text-[10px] uppercase tracking-wider text-blue-600 dark:text-blue-300">Aplicate</div>
          <div className="text-lg font-semibold text-blue-700 dark:text-blue-300 tabular-nums">{t.applied}</div>
        </div>
        <div className="rounded-lg bg-purple-50 dark:bg-purple-500/10 p-2">
          <div className="text-[10px] uppercase tracking-wider text-purple-600 dark:text-purple-300">Eficacitate rolling</div>
          <div className="text-lg font-semibold text-purple-700 dark:text-purple-300 tabular-nums">{t.rolling_effectiveness_pct != null ? `${t.rolling_effectiveness_pct}%` : "—"}</div>
        </div>
        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400">Delta față de prima jumătate</div>
          <div className={`text-lg font-semibold tabular-nums inline-flex items-center gap-1 ${trendUp ? "text-emerald-600 dark:text-emerald-400" : trendDown ? "text-red-600 dark:text-red-400" : "text-slate-500"}`}>
            {trendUp && <TrendingUp className="w-4 h-4" />}
            {trendDown && <TrendingDown className="w-4 h-4" />}
            {delta != null ? `${delta > 0 ? "+" : ""}${delta} pp` : "—"}
          </div>
        </div>
      </div>

      {/* Heatmap grid */}
      <div className="flex items-start gap-2 overflow-x-auto pb-2">
        {/* Y-axis weekday labels */}
        <div className="flex flex-col gap-1 text-[9px] text-slate-400 pt-1 shrink-0">
          {WD_LABELS.map((wd, i) => (
            <div key={i} className="h-4 leading-4 w-3 text-right tabular-nums">{wd}</div>
          ))}
        </div>
        {/* Columns: 7 rows × N weeks. Build by iterating weeks then weekdays */}
        <div className="flex gap-1" data-testid="trend-grid">
          {Array.from({ length: weeks }).map((_, wIdx) => (
            <div key={wIdx} className="flex flex-col gap-1">
              {WD_LABELS.map((_wd, dayIdx) => {
                const c = grid[dayIdx][wIdx]; // ordered by date asc per weekday
                if (!c) return <div key={dayIdx} className="w-4 h-4" />;
                return (
                  <button
                    key={dayIdx}
                    onMouseEnter={() => setHovered(c)}
                    onMouseLeave={() => setHovered(prev => (prev === c ? null : prev))}
                    className={`w-4 h-4 rounded-sm border ${cellColor(c)} transition-transform hover:scale-125 hover:ring-2 hover:ring-purple-400 cursor-pointer`}
                    title={`${c.date} · ${c.count} sugestii · ${c.applied}/${c.decided} aplicate (${c.effectiveness_pct != null ? c.effectiveness_pct + "%" : "—"})`}
                    data-testid={`trend-cell-${c.date}`}
                  />
                );
              })}
            </div>
          ))}
        </div>
        {/* Legend */}
        <div className="ml-auto flex flex-col gap-1 text-[10px] text-slate-500 shrink-0 pt-1">
          <div className="font-bold uppercase tracking-wider">Legendă</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-slate-100 dark:bg-slate-800/50 border border-slate-200" /> 0 sugestii</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-slate-200 dark:bg-slate-700 border border-slate-300" /> pending</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-red-400 border border-red-500" /> &lt;30%</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-amber-400 border border-amber-500" /> 30-50%</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-emerald-300 border border-emerald-400" /> 50-80%</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-emerald-500 border border-emerald-600" /> ≥80%</div>
        </div>
      </div>

      {/* Hover detail */}
      <div className="mt-2 text-[11px] text-slate-500 min-h-[16px]" data-testid="trend-hover">
        {hovered ? (
          <span>
            <b>{hovered.date}</b> · {hovered.count} sugestii · {hovered.applied} aplicate / {hovered.decided} decise · {hovered.effectiveness_pct != null ? `eficacitate ${hovered.effectiveness_pct}%` : "fără decizii"}
          </span>
        ) : (
          <span className="italic">Plimbă cursorul peste celule pentru detalii zilnice.</span>
        )}
      </div>
    </div>
  );
};

const LowEffectivenessAlertConfig = () => {
  const [cfg, setCfg] = useState(null);
  const [draft, setDraft] = useState(null);
  const [recipInput, setRecipInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const load = async () => {
    const r = await axios.get(`${API}/admin/ai/effectiveness-alert/config`);
    setCfg(r.data); setDraft(r.data);
    setRecipInput((r.data.recipients || []).join(", "));
  };
  useEffect(() => { load(); }, []);

  if (!cfg || !draft) return null;
  const dirty = JSON.stringify(cfg) !== JSON.stringify(draft) || recipInput !== (cfg.recipients || []).join(", ");

  const save = async () => {
    setSaving(true);
    try {
      const recipients = recipInput.split(",").map(s => s.trim()).filter(Boolean);
      const r = await axios.put(`${API}/admin/ai/effectiveness-alert/config`, {
        enabled: draft.enabled,
        threshold_pct: draft.threshold_pct,
        window_days: draft.window_days,
        min_decided: draft.min_decided,
        recipients,
      });
      setCfg(r.data); setDraft(r.data);
      setRecipInput((r.data.recipients || []).join(", "));
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const runTest = async (dryRun) => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await axios.post(`${API}/admin/ai/effectiveness-alert/test`, { dry_run: dryRun, force: true });
      setTestResult(r.data);
    } catch (e) {
      setTestResult({ error: e?.response?.data?.detail || e.message });
    } finally {
      setTesting(false);
    }
  };

  const loadHistory = async () => {
    const r = await axios.get(`${API}/admin/ai/effectiveness-alert/history`);
    setHistory(r.data?.items || []);
    setShowHistory(true);
  };

  return (
    <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-700 p-4" data-testid="effectiveness-alert-config">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {draft.enabled ? <Bell className="w-4 h-4 text-amber-500" /> : <BellOff className="w-4 h-4 text-slate-400" />}
        <div className="font-semibold text-sm">Alertă email — eficacitate AI sub prag</div>
        <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ${
          draft.enabled ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
        }`}>{draft.enabled ? "ON" : "OFF"}</span>
        <div className="ml-auto flex items-center gap-2">
          <AdminBtn variant="secondary" onClick={loadHistory} data-testid="alert-history-btn"><History className="w-3.5 h-3.5" /> Istoric</AdminBtn>
          <AdminBtn variant="secondary" onClick={() => runTest(true)} disabled={testing} data-testid="alert-test-dry"><RefreshCw className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} /> Simulare</AdminBtn>
          <AdminBtn variant="secondary" onClick={() => runTest(false)} disabled={testing} data-testid="alert-test-send"><Send className="w-3.5 h-3.5" /> Trimite-mi acum</AdminBtn>
          <AdminBtn variant={dirty ? "primary" : "secondary"} onClick={save} disabled={!dirty || saving} data-testid="alert-save">{saving ? "..." : dirty ? "Salvează" : "Salvat"}</AdminBtn>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
        {/* Enabled toggle */}
        <button
          type="button"
          onClick={() => setDraft({ ...draft, enabled: !draft.enabled })}
          className={`text-left rounded-xl border p-3 transition-colors ${
            draft.enabled ? "bg-emerald-50 border-emerald-300 dark:bg-emerald-500/10 dark:border-emerald-500/40" : "bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700"
          }`}
          data-testid="alert-enabled-toggle"
        >
          <div className="font-medium text-sm mb-1 flex items-center gap-1">
            {draft.enabled ? <Bell className="w-3.5 h-3.5 text-emerald-600" /> : <BellOff className="w-3.5 h-3.5 text-slate-400" />}
            Cron weekly
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">Luni 09:00 Europe/București · click pentru toggle</div>
        </button>

        {/* Threshold slider */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="font-medium text-sm mb-1">Prag eficacitate</div>
          <div className="flex items-center gap-2">
            <input
              type="range" min="10" max="95" step="5" value={draft.threshold_pct}
              onChange={e => setDraft({ ...draft, threshold_pct: parseInt(e.target.value, 10) })}
              className="flex-1 accent-amber-500"
              data-testid="alert-threshold-slider"
            />
            <span className="text-base font-semibold tabular-nums text-amber-600 dark:text-amber-400 w-12 text-right">{draft.threshold_pct}%</span>
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Alertă dacă rolling &lt; acest prag</div>
        </div>

        {/* Window days */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="font-medium text-sm mb-1">Fereastră rolling (zile)</div>
          <input
            type="number" min="1" max="60" value={draft.window_days}
            onChange={e => setDraft({ ...draft, window_days: Math.max(1, parseInt(e.target.value || "1", 10)) })}
            className="w-full px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="alert-window-days"
          />
          <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Câte zile înapoi calculează eficacitatea</div>
        </div>

        {/* Min decided */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="font-medium text-sm mb-1">Min. decizii necesare</div>
          <input
            type="number" min="1" value={draft.min_decided}
            onChange={e => setDraft({ ...draft, min_decided: Math.max(1, parseInt(e.target.value || "1", 10)) })}
            className="w-full px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="alert-min-decided"
          />
          <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Anti-spam: nu alertăm cu puține date</div>
        </div>
      </div>

      {/* Recipients */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 mb-3">
        <div className="font-medium text-sm mb-1">Destinatari email</div>
        <input
          type="text" value={recipInput} onChange={e => setRecipInput(e.target.value)}
          placeholder="admin@propmanage.io, alt-admin@propmanage.io (gol = toți adminii)"
          className="w-full px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-mono"
          data-testid="alert-recipients"
        />
        <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Lista separată prin virgulă. Dacă e gol, sistemul folosește toate emailurile cu rol admin.</div>
      </div>

      {/* Last state preview */}
      {cfg.last_state && (
        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2.5 text-xs text-slate-600 dark:text-slate-300 flex flex-wrap items-center gap-3" data-testid="alert-last-state">
          <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400">Ultima verificare</span>
          {cfg.last_check_at && <span>{new Date(cfg.last_check_at).toLocaleString("ro-RO")}</span>}
          <span>·</span>
          <span>Eficacitate: <b>{cfg.last_state.effectiveness_pct != null ? `${cfg.last_state.effectiveness_pct}%` : "—"}</b></span>
          <span>· Aplicate: <b className="text-blue-600 dark:text-blue-400">{cfg.last_state.applied || 0}</b>/{cfg.last_state.decided || 0} decise</span>
          {cfg.last_state.alert_triggered && <span className="ml-auto text-amber-600 dark:text-amber-400 font-semibold">🔔 Alertă trimisă</span>}
          {cfg.last_state.skip_reason && <span className="ml-auto text-slate-400 italic">skip: {cfg.last_state.skip_reason}</span>}
        </div>
      )}

      {/* Test result inline */}
      {testResult && (
        <div className={`mt-3 rounded-lg p-3 text-xs border ${
          testResult.error ? "bg-red-50 border-red-200 dark:bg-red-500/10 dark:border-red-500/30" :
          testResult.alert_triggered ? "bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30" :
          "bg-emerald-50 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/30"
        }`} data-testid="alert-test-result">
          {testResult.error ? (
            <span>❌ {testResult.error}</span>
          ) : testResult.alert_triggered ? (
            <span>
              🔔 <b>Alertă declanșată</b>: eficacitate {testResult.effectiveness_pct}% &lt; prag.
              {testResult.sent ? " Email-ul a fost trimis." : " Simulare — nu s-a trimis."}
              {testResult.send_result?.recipients?.length ? ` → ${testResult.send_result.recipients.join(", ")}` : ""}
            </span>
          ) : (
            <span>
              ✅ <b>Fără alertă</b>: {testResult.skip_reason || "eficacitate ok"}.
              {testResult.effectiveness_pct != null ? ` Eficacitate: ${testResult.effectiveness_pct}%` : ""}
            </span>
          )}
        </div>
      )}

      {/* History modal */}
      {showHistory && (
        <div className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setShowHistory(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()} data-testid="alert-history-modal">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
              <div className="font-semibold text-sm">Istoric alerte trimise</div>
              <button onClick={() => setShowHistory(false)} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {history.length === 0 && <div className="text-center py-8 text-slate-400 text-sm italic">Niciun email de alertă trimis încă</div>}
              {history.map(h => (
                <div key={h._id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 text-xs" data-testid={`alert-history-${h._id}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-700 dark:text-slate-200">{new Date(h.sent_at).toLocaleString("ro-RO")}</span>
                    <span className="text-[10px] text-slate-400">săpt. {h.iso_week}</span>
                    <span className="ml-auto px-1.5 py-0.5 rounded text-[9px] bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300 font-bold">{h.state?.effectiveness_pct}%</span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">
                    Aplicate: <b>{h.state?.applied || 0}</b>/<b>{h.state?.decided || 0}</b> decise · prag <b>{h.cfg_snapshot?.threshold_pct}%</b> · fereastră <b>{h.cfg_snapshot?.window_days}z</b>
                  </div>
                  {h.state?.last_sent_to?.length && (
                    <div className="text-[10px] text-slate-400 mt-1">→ {h.state.last_sent_to.join(", ")}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const RepairAuditLog = () => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [drill, setDrill] = useState(null); // {pattern, items}

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/ai/repair-suggestions/audit?days=${days}`);
      setData(r.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  const openDrill = async (pattern) => {
    try {
      const r = await axios.get(`${API}/admin/ai/repair-suggestions/by-pattern/${encodeURIComponent(pattern)}?days=${Math.max(days, 90)}`);
      setDrill({ pattern, items: r.data?.items || [] });
    } catch {
      setDrill({ pattern, items: [] });
    }
  };

  if (!data) {
    return (
      <AdminCard title={<div className="flex items-center gap-2"><BarChart3 className="w-4 h-4 text-indigo-500" /> Repair Audit Log</div>}>
        <div className="text-slate-400 text-sm italic py-4 text-center">Se încarcă...</div>
      </AdminCard>
    );
  }

  const { rows, totals, best_pattern, worst_pattern } = data;

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><BarChart3 className="w-4 h-4 text-indigo-500" /> Repair Audit Log <span className="text-[10px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">NEW</span></div>}
      action={
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5" data-testid="audit-window-selector">
            {WINDOWS.map(w => (
              <button
                key={w.id}
                onClick={() => setDays(w.id)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  days === w.id ? "bg-white dark:bg-slate-900 text-indigo-600 shadow-sm" : "text-slate-500 dark:text-slate-400 hover:text-slate-700"
                }`}
                data-testid={`audit-window-${w.id}`}
              >{w.label}</button>
            ))}
          </div>
          <AdminBtn variant="secondary" onClick={load}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></AdminBtn>
        </div>
      }
    >
      {/* Global stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
        <Stat label="Sugestii totale" value={totals.total} />
        <Stat label="Aplicate" value={totals.applied} color="text-blue-600 dark:text-blue-400" />
        <Stat label="Aprobate (neaplicate)" value={totals.approved} color="text-emerald-600 dark:text-emerald-400" />
        <Stat label="Respinse" value={totals.rejected} color="text-red-600 dark:text-red-400" />
        <Stat label="Eficacitate globală" value={fmtPct(totals.global_effectiveness_pct)} color="text-indigo-600 dark:text-indigo-400" />
      </div>

      {/* Trend heatmap */}
      <EffectivenessTrend />

      {/* Low-effectiveness alert config (Phase 47D) */}
      <LowEffectivenessAlertConfig />

      {/* Best / Worst */}
      {(best_pattern || worst_pattern) && (
        <div className="grid md:grid-cols-2 gap-3 mb-4">
          {best_pattern && (
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 p-3">
              <div className="flex items-center gap-2 mb-1">
                <Trophy className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[10px] uppercase tracking-wider font-bold text-emerald-700 dark:text-emerald-300">Cel mai eficient pattern</span>
              </div>
              <div className="font-medium text-sm text-emerald-900 dark:text-emerald-200">{best_pattern.pattern_label}</div>
              <div className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
                {best_pattern.effectiveness_pct}% applied / decided · {best_pattern.applied}/{best_pattern.total} sugestii
              </div>
            </div>
          )}
          {worst_pattern && worst_pattern.pattern !== best_pattern?.pattern && (
            <div className="rounded-xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 p-3">
              <div className="flex items-center gap-2 mb-1">
                <AlertOctagon className="w-4 h-4 text-red-600 dark:text-red-400" />
                <span className="text-[10px] uppercase tracking-wider font-bold text-red-700 dark:text-red-300">Cel mai puțin eficient</span>
              </div>
              <div className="font-medium text-sm text-red-900 dark:text-red-200">{worst_pattern.pattern_label}</div>
              <div className="text-xs text-red-700 dark:text-red-300 mt-1">
                {worst_pattern.effectiveness_pct}% applied / decided · LLM-ul se descurcă greu — verifică prompt-ul.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Per-pattern table */}
      {rows.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm italic">Nicio sugestie de fix în fereastra selectată.</div>
      ) : (
        <div className="overflow-x-auto" data-testid="repair-audit-rows">
          <table className="w-full text-xs">
            <thead className="text-slate-500 uppercase tracking-wider">
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="text-left px-2 py-2">Pattern</th>
                <th className="text-right px-2 py-2">Total</th>
                <th className="text-right px-2 py-2">Aplicate</th>
                <th className="text-right px-2 py-2">Aprobate</th>
                <th className="text-right px-2 py-2">Respinse</th>
                <th className="text-left px-2 py-2 w-[140px]">Apply rate</th>
                <th className="text-right px-2 py-2">Eficacitate</th>
                <th className="text-right px-2 py-2">Avg min</th>
                <th className="text-right px-2 py-2">Avg regen</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((r) => {
                const effGood = (r.effectiveness_pct ?? 0) >= 70;
                const effBad = r.effectiveness_pct != null && r.effectiveness_pct < 30;
                return (
                  <tr key={r.pattern} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer" onClick={() => openDrill(r.pattern)} data-testid={`audit-row-${r.pattern}`}>
                    <td className="px-2 py-2">
                      <div className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-[260px]" title={r.pattern_label}>{r.pattern_label}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{r.pattern}</div>
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums">{r.total}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-blue-600 dark:text-blue-400">{r.applied}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-emerald-600 dark:text-emerald-400">{r.approved}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-red-600 dark:text-red-400">{r.rejected}</td>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] tabular-nums text-slate-500 w-9">{r.apply_rate_pct}%</span>
                        <div className="flex-1"><Bar pct={r.apply_rate_pct} color="bg-blue-500" /></div>
                      </div>
                    </td>
                    <td className={`px-2 py-2 text-right font-semibold tabular-nums ${effGood ? "text-emerald-600 dark:text-emerald-400" : effBad ? "text-red-600 dark:text-red-400" : "text-slate-500"}`}>
                      {effGood && <TrendingUp className="w-3 h-3 inline mr-0.5" />}
                      {effBad && <TrendingDown className="w-3 h-3 inline mr-0.5" />}
                      {fmtPct(r.effectiveness_pct)}
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-500">{r.avg_minutes}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-500">{r.avg_regenerations}</td>
                    <td className="px-2 py-2 text-slate-400"><ChevronRight className="w-3.5 h-3.5" /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-3 text-[11px] text-slate-400 italic">
        Eficacitate = aplicate / (aplicate + aprobate + respinse). Patternul "best" trebuie să aibă ≥ 3 decizii. Click pe rând → drill-down.
      </div>

      {/* Drill-down modal */}
      {drill && (
        <div className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setDrill(null)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-3xl w-full max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()} data-testid="audit-drill-modal">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
              <div className="font-semibold text-sm">Sugestii pentru <span className="font-mono text-indigo-600 dark:text-indigo-400">{drill.pattern}</span></div>
              <button onClick={() => setDrill(null)} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {drill.items.length === 0 && <div className="text-center py-8 text-slate-400 text-sm italic">Nicio sugestie</div>}
              {drill.items.map(s => (
                <div key={s.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 text-xs" data-testid={`audit-drill-item-${s.id}`}>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider font-bold ${
                      s.status === "applied" ? "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300" :
                      s.status === "approved" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300" :
                      s.status === "rejected" ? "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300" :
                      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    }`}>{s.status}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider font-bold ${
                      s.risk_level === "high" ? "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300" :
                      s.risk_level === "medium" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300" :
                      "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300"
                    }`}>risc {s.risk_level}</span>
                    <span className="ml-auto text-[10px] text-slate-400">{s.created_at ? new Date(s.created_at).toLocaleDateString("ro-RO") : ""}</span>
                  </div>
                  <div className="text-slate-700 dark:text-slate-300 mb-1">{s.summary}</div>
                  {s.decision_note && <div className="text-[10px] italic text-slate-500 mt-1">📝 "{s.decision_note}"</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AdminCard>
  );
};

export default RepairAuditLog;
