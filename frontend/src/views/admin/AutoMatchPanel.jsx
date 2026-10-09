// AutoMatchPanel — Admin tool to bulk-assign unmatched open requests.
// Calls /api/admin/auto-match/preview + /run. Visible on the Admin Overview page.
import React, { useState, useEffect } from "react";
import axios from "axios";
import { Zap, Loader2, CheckCircle2, AlertTriangle, Eye, Sparkles, Clock, Power } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

export const AutoMatchPanel = () => {
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [savingSchedule, setSavingSchedule] = useState(false);

  const loadPreview = async () => {
    setLoadingPreview(true);
    setError(null);
    try {
      const { data } = await ax.post("/api/admin/auto-match/preview");
      setPreview(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la preview");
    } finally { setLoadingPreview(false); }
  };

  const loadSchedule = async () => {
    try {
      const { data } = await ax.get("/api/admin/auto-match/schedule");
      setSchedule(data);
    } catch (_) { /* silent */ }
  };

  useEffect(() => {
    loadPreview();
    loadSchedule();
  }, []);

  const updateSchedule = async (patch) => {
    setSavingSchedule(true);
    try {
      const { data } = await ax.put("/api/admin/auto-match/schedule", patch);
      setSchedule(s => ({ ...(s || {}), schedule: data }));
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la salvare schedule");
    } finally { setSavingSchedule(false); }
  };

  const runMatch = async (dryRun = false) => {
    if (!dryRun && !window.confirm(`Confirmi auto-asignarea a ${preview?.with_match_available || 0} cereri? Acțiunea este reversibilă manual per cerere, dar va trimite notificări către clienți & specialiști.`)) return;
    setRunning(true);
    setError(null);
    try {
      const { data } = await ax.post("/api/admin/auto-match/run", {
        limit: 100,
        min_rating: 0,
        dry_run: dryRun,
      });
      setResult(data);
      if (!dryRun) {
        await loadPreview();
        await loadSchedule();
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la execuție");
    } finally { setRunning(false); }
  };

  const unmatched = preview?.total_unmatched ?? 0;
  const withMatch = preview?.with_match_available ?? 0;
  const noMatch = preview?.no_match_available ?? 0;

  return (
    <AdminCard testid="auto-match-panel">
      <div className="flex items-start gap-4 flex-wrap">
        <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 flex items-center justify-center shrink-0">
          <Zap className="w-5 h-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1 min-w-[260px]">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-base">Auto-Match cereri neatribuite</h3>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300 border border-amber-300/40">
              Boost Operational Autonomy
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Asignează automat cele mai bune specialist-uri pentru cererile rămase fără răspuns &gt; 1h. Folosește matcher-ul existent (zonă + rating + categorie). Lead fee se omite (acțiune admin).
          </p>
          {loadingPreview && (
            <div className="mt-3 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" /> Se analizează cererile...
            </div>
          )}
          {preview && !loadingPreview && (
            <div className="mt-3 grid grid-cols-3 gap-2 max-w-md">
              <div className="rounded-xl px-3 py-2 bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/5">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Neatribuite</div>
                <div className="text-2xl font-semibold" data-testid="auto-match-total">{unmatched}</div>
              </div>
              <div className="rounded-xl px-3 py-2 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30">
                <div className="text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300">Cu match</div>
                <div className="text-2xl font-semibold text-emerald-700 dark:text-emerald-300" data-testid="auto-match-with">{withMatch}</div>
              </div>
              <div className="rounded-xl px-3 py-2 bg-stone-50 dark:bg-stone-500/10 border border-stone-200 dark:border-stone-500/30">
                <div className="text-[10px] uppercase tracking-wider text-stone-700 dark:text-stone-300">Fără match</div>
                <div className="text-2xl font-semibold text-stone-700 dark:text-stone-300" data-testid="auto-match-without">{noMatch}</div>
              </div>
            </div>
          )}
          {error && (
            <div className="mt-3 text-xs text-red-600 dark:text-red-400 flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {error}
            </div>
          )}
          {result && (
            <div className="mt-3 rounded-xl border border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 px-3 py-2.5" data-testid="auto-match-result">
              <div className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="w-4 h-4" />
                {result.dry_run ? "Simulare " : ""}Asignate <strong>{result.assigned_count}</strong> cereri
                {result.skipped_count > 0 && <span className="text-stone-500 ml-1">· {result.skipped_count} sărite</span>}
              </div>
              {result.assigned_count > 0 && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="text-[11px] text-emerald-700 dark:text-emerald-300 underline mt-1"
                  data-testid="auto-match-toggle-details"
                >
                  {expanded ? "Ascunde" : "Vezi"} detalii ({result.assigned.length})
                </button>
              )}
              {expanded && (
                <div className="mt-2 max-h-48 overflow-y-auto text-xs text-stone-600 dark:text-stone-300 font-mono space-y-0.5">
                  {result.assigned.map((a, i) => (
                    <div key={i} className="truncate">
                      <span className="text-emerald-600 dark:text-emerald-400">✓</span> {a.request_id.slice(0, 8)} → {a.specialist_name}
                    </div>
                  ))}
                  {result.skipped.map((s, i) => (
                    <div key={`sk-${i}`} className="truncate text-stone-500">
                      <span className="text-stone-400">×</span> {s.request_id.slice(0, 8)} — {s.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={() => runMatch(true)}
            disabled={running || loadingPreview || unmatched === 0}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="auto-match-dry-run"
          >
            <Eye className="w-3.5 h-3.5" /> Simulează
          </button>
          <button
            onClick={() => runMatch(false)}
            disabled={running || loadingPreview || withMatch === 0}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="auto-match-run"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Asignează {withMatch || ""}
          </button>
        </div>
      </div>

      {/* SCHEDULE SECTION — autonomous mode */}
      {schedule && (
        <div className="mt-5 pt-5 border-t border-slate-200 dark:border-white/10" data-testid="auto-match-schedule">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                schedule.schedule?.enabled
                  ? "bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30"
                  : "bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10"
              }`}>
                <Clock className={`w-4 h-4 ${
                  schedule.schedule?.enabled ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"
                }`} />
              </div>
              <div>
                <div className="text-sm font-semibold flex items-center gap-2">
                  Mod autonom
                  {schedule.schedule?.enabled ? (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-300/40" data-testid="auto-match-schedule-status">
                      Activ · la {schedule.schedule?.interval_hours}h
                    </span>
                  ) : (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-400 border border-slate-200 dark:border-white/10" data-testid="auto-match-schedule-status">
                      Dezactivat
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Cron-ul verifică cererile la fiecare oră și auto-asignează silent când e cazul. Notificările continuă să fie trimise.
                </div>
                {schedule.last_cron_run && (
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 font-mono" data-testid="auto-match-last-cron">
                    Ultima rulare cron: {new Date(schedule.last_cron_run.executed_at).toLocaleString("ro-RO")} · {schedule.last_cron_run.assigned_count} asignate
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={schedule.schedule?.interval_hours || 6}
                onChange={e => updateSchedule({ interval_hours: parseInt(e.target.value) })}
                disabled={savingSchedule}
                className="text-xs bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-amber-400"
                data-testid="auto-match-interval-select"
              >
                <option value={1}>la 1h</option>
                <option value={3}>la 3h</option>
                <option value={6}>la 6h</option>
                <option value={12}>la 12h</option>
                <option value={24}>zilnic</option>
              </select>
              <button
                onClick={() => updateSchedule({ enabled: !schedule.schedule?.enabled })}
                disabled={savingSchedule}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  schedule.schedule?.enabled
                    ? "bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-500/10 dark:hover:bg-red-500/20 dark:text-red-300 border border-red-200 dark:border-red-500/30"
                    : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30"
                }`}
                data-testid="auto-match-schedule-toggle"
              >
                {savingSchedule ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Power className="w-3.5 h-3.5" />}
                {schedule.schedule?.enabled ? "Dezactivează" : "Activează"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminCard>
  );
};

export default AutoMatchPanel;
