// Smoke Test card — runs an E2E health probe (login → CRUD → logout) against
// the live API. Triggered manually by admin; results stored in DB for history.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { PlayCircle, CheckCircle2, XCircle, Clock, ChevronDown, ChevronUp, History, ExternalLink, Bell, BellOff, Users } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

export const SmokeTestCard = () => {
  const [running, setRunning] = useState(false);
  const [runningAll, setRunningAll] = useState(false);
  const [lastRun, setLastRun] = useState(null);
  const [allRolesReport, setAllRolesReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [monitor, setMonitor] = useState(null);
  const [monitorBusy, setMonitorBusy] = useState(false);

  const loadHistory = async () => {
    try {
      const r = await axios.get(`${API}/admin/smoke-test/history?limit=10`);
      setHistory(r.data.items || []);
      if (!lastRun && r.data.items?.length) setLastRun(r.data.items[0]);
    } catch { /* ignore */ }
  };

  const loadMonitor = async () => {
    try {
      const r = await axios.get(`${API}/admin/smoke-test/monitor/config`);
      setMonitor(r.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadHistory(); loadMonitor(); }, []);

  const runTest = async () => {
    setRunning(true);
    try {
      const params = baseUrl.trim() ? `?base_url=${encodeURIComponent(baseUrl.trim())}` : "";
      const r = await axios.post(`${API}/admin/smoke-test/run${params}`);
      setLastRun(r.data);
      loadHistory();
    } catch (e) {
      window.alert(`Smoke test eșuat: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const runAllRoles = async () => {
    setRunningAll(true);
    try {
      const params = baseUrl.trim() ? `?base_url=${encodeURIComponent(baseUrl.trim())}` : "";
      const r = await axios.post(`${API}/admin/smoke-test/run-all-roles${params}`);
      setAllRolesReport(r.data);
      loadHistory();
    } catch (e) {
      window.alert(`Run-all-roles eșuat: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRunningAll(false);
    }
  };

  const toggleMonitor = async () => {
    if (!monitor) return;
    setMonitorBusy(true);
    try {
      const next = !monitor.enabled;
      const payload = { enabled: next };
      // When enabling, also save the current target URL the admin picked
      if (next && baseUrl.trim()) payload.base_url = baseUrl.trim();
      const r = await axios.post(`${API}/admin/smoke-test/monitor/config`, payload);
      setMonitor(r.data);
    } catch (e) {
      window.alert(`Eroare toggle monitor: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setMonitorBusy(false);
    }
  };

  return (
    <AdminCard
      title={
        <div className="flex items-center gap-2">
          <PlayCircle className="w-4 h-4 text-emerald-500" />
          <span>Smoke Test E2E</span>
          <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">NEW</span>
        </div>
      }
      action={
        <div className="flex items-center gap-2">
          <AdminBtn
            variant="secondary"
            onClick={runAllRoles}
            disabled={runningAll || running}
            data-testid="smoke-test-run-all-roles-btn"
          >
            <Users className={`w-3.5 h-3.5 ${runningAll ? "animate-pulse" : ""}`} />
            {runningAll ? "Testez toate..." : "Toate rolurile"}
          </AdminBtn>
          <AdminBtn
            variant="primary"
            onClick={runTest}
            disabled={running || runningAll}
            data-testid="smoke-test-run-btn"
          >
            <PlayCircle className={`w-3.5 h-3.5 ${running ? "animate-pulse" : ""}`} />
            {running ? "Se rulează..." : "Rulează test"}
          </AdminBtn>
        </div>
      }
    >
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 leading-relaxed">
        Probă reală E2E: login → /auth/me → creare apartament → listare → ștergere → logout.
        Folosește un cont demo izolat, marchează datele cu prefix <code className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px]">[SMOKE ID]</code> și
        face cleanup la final. Rulează în {"<"}1 secundă.
      </p>

      {/* Auto-monitor toggle */}
      {monitor && (
        <div
          className={`flex items-center gap-3 p-3 rounded-lg border mb-3 ${
            monitor.enabled
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
              : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700"
          }`}
          data-testid="smoke-monitor-banner"
        >
          {monitor.enabled
            ? <Bell className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            : <BellOff className="w-4 h-4 text-slate-400 shrink-0" />
          }
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-medium ${monitor.enabled ? "text-emerald-700 dark:text-emerald-300" : "text-slate-600 dark:text-slate-300"}`}>
              Monitorizare automată: {monitor.enabled ? "ACTIVĂ" : "INACTIVĂ"}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {monitor.enabled
                ? <>Rulează la fiecare {monitor.interval_minutes} min pe <code className="text-[10px]">{monitor.base_url}</code>. Email alertă la admin doar dacă pică ceva (cooldown 3h). {monitor.last_status && <>Ultim status: <strong className={monitor.last_status === "ok" ? "text-emerald-600" : "text-red-600"}>{monitor.last_status.toUpperCase()}</strong>.</>}</>
                : "Activează pentru a primi alertă pe email când smoke test-ul detectează probleme pe domeniul live."
              }
            </div>
          </div>
          <button
            onClick={toggleMonitor}
            disabled={monitorBusy}
            className={`px-3 py-1.5 rounded-full text-xs font-medium shrink-0 transition ${
              monitor.enabled
                ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                : "bg-slate-700 hover:bg-slate-800 dark:bg-slate-200 dark:hover:bg-white dark:text-slate-900 text-white"
            }`}
            data-testid="smoke-monitor-toggle"
          >
            {monitorBusy ? "..." : monitor.enabled ? "Dezactivează" : "Activează"}
          </button>
        </div>
      )}

      {/* Target URL input (optional override) */}
      <div className="flex items-center gap-2 mb-3 text-xs">
        <label className="text-slate-500 dark:text-slate-400 shrink-0">Target:</label>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="http://localhost:8001 (default — backend curent)"
          className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-emerald-400"
          data-testid="smoke-test-base-url-input"
        />
        <button
          onClick={() => setBaseUrl("https://propmanage.ro")}
          className="text-emerald-600 dark:text-emerald-400 hover:underline shrink-0"
          data-testid="smoke-test-target-prod"
        >
          Prod
        </button>
      </div>

      {allRolesReport && <AllRolesReport report={allRolesReport} />}

      {lastRun && <RunReport run={lastRun} />}

      {/* History toggle */}
      <button
        onClick={() => setShowHistory(s => !s)}
        className="mt-3 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 flex items-center gap-1"
        data-testid="smoke-test-history-toggle"
      >
        <History className="w-3 h-3" />
        {showHistory ? "Ascunde istoricul" : `Istoric (${history.length} rulări)`}
        {showHistory ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {showHistory && history.length > 0 && (
        <div className="mt-2 space-y-1 max-h-64 overflow-y-auto" data-testid="smoke-test-history-list">
          {history.map((h) => (
            <button
              key={h.id}
              onClick={() => setLastRun(h)}
              className={`w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs border ${
                h.ok
                  ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
                  : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
              } hover:opacity-80 transition`}
              data-testid={`smoke-history-${h.id}`}
            >
              {h.ok ? <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" /> : <XCircle className="w-3 h-3 text-red-500 shrink-0" />}
              <span className="font-mono text-[10px] text-slate-500 truncate">{h.id?.slice(0, 8)}</span>
              <span className="text-slate-700 dark:text-slate-300">{h.passed}/{h.total}</span>
              <span className="text-slate-400 truncate flex-1">{new Date(h.started_at).toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
              <span className="text-slate-400">{h.total_duration_ms}ms</span>
              <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
            </button>
          ))}
        </div>
      )}
    </AdminCard>
  );
};

const RunReport = ({ run }) => {
  return (
    <div
      className={`rounded-xl border p-3 ${
        run.ok
          ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
          : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
      }`}
      data-testid="smoke-test-run-report"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          {run.ok
            ? <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            : <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          }
          <div>
            <div className={`font-semibold text-sm ${run.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
              {run.ok ? "TOATE PASS" : "EȘUAT"} · {run.passed}/{run.total}
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
              {run.base_url} · {new Date(run.started_at).toLocaleString("ro-RO")}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">{run.total_duration_ms}ms</div>
          <div className="text-[9px] uppercase tracking-wider text-slate-400">durată totală</div>
        </div>
      </div>

      <div className="space-y-1">
        {run.steps?.map((s, i) => (
          <div
            key={i}
            className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-xs ${
              s.ok
                ? "bg-white/60 dark:bg-emerald-500/5"
                : "bg-red-100 dark:bg-red-500/15"
            }`}
            data-testid={`smoke-step-${i}`}
          >
            {s.ok
              ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              : <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
            }
            <span className="flex-1 text-slate-700 dark:text-slate-200 truncate">{s.name}</span>
            {s.status_code && (
              <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                s.ok ? "bg-emerald-200/60 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200"
                     : "bg-red-200/60 text-red-800 dark:bg-red-500/20 dark:text-red-200"
              }`}>
                {s.status_code}
              </span>
            )}
            <span className="text-slate-400 font-mono text-[10px] flex items-center gap-0.5 shrink-0">
              <Clock className="w-2.5 h-2.5" />{s.duration_ms}ms
            </span>
          </div>
        ))}
      </div>

      {!run.ok && (
        <div className="mt-2 text-[11px] space-y-1">
          {run.steps?.filter(s => !s.ok).map((s, i) => (
            <div key={i} className="bg-red-100/60 dark:bg-red-500/15 rounded-md p-2 text-red-700 dark:text-red-300">
              <div className="font-semibold mb-0.5">{s.name}</div>
              <div className="font-mono text-[10px] break-all opacity-80">{s.error || "(no error message)"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


const ROLE_META = {
  client:     { label: "Client",     emoji: "👤", color: "blue" },
  specialist: { label: "Specialist", emoji: "🔧", color: "purple" },
  operator:   { label: "Operator",   emoji: "🏢", color: "amber" },
  admin:      { label: "Admin",      emoji: "🛡️", color: "red" },
};

const AllRolesReport = ({ report }) => {
  return (
    <div
      className={`rounded-xl border p-3 mb-3 ${
        report.ok
          ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
          : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
      }`}
      data-testid="smoke-test-all-roles-report"
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          {report.ok
            ? <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            : <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          }
          <div>
            <div className={`font-semibold text-sm ${report.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
              Toate rolurile: {report.summary.passed_roles}/{report.summary.total_roles} OK
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
              {report.base_url} · paralel · {new Date(report.started_at).toLocaleString("ro-RO")}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">{report.total_duration_ms}ms</div>
          <div className="text-[9px] uppercase tracking-wider text-slate-400">durată (max)</div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-2">
        {report.roles?.map((r) => {
          const meta = ROLE_META[r.role] || { label: r.role, emoji: "?", color: "slate" };
          return (
            <div
              key={r.role}
              className={`rounded-lg border p-3 ${
                r.ok
                  ? "bg-white/60 dark:bg-emerald-500/5 border-emerald-200/60 dark:border-emerald-500/20"
                  : "bg-red-100 dark:bg-red-500/15 border-red-300 dark:border-red-500/40"
              }`}
              data-testid={`smoke-role-${r.role}`}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{meta.emoji}</span>
                  <div>
                    <div className="text-sm font-semibold capitalize">{meta.label}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{r.passed}/{r.total} · {r.total_duration_ms}ms</div>
                  </div>
                </div>
                {r.ok
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  : <XCircle className="w-5 h-5 text-red-500" />
                }
              </div>
              <div className="space-y-0.5">
                {r.steps?.map((s, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-[11px] py-0.5">
                    {s.ok
                      ? <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                      : <XCircle className="w-3 h-3 text-red-500 shrink-0" />
                    }
                    <span className="flex-1 truncate text-slate-600 dark:text-slate-300">{s.name}</span>
                    {s.status_code && (
                      <span className={`font-mono text-[9px] px-1 py-0.5 rounded ${
                        s.ok ? "bg-emerald-200/50 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300"
                             : "bg-red-200/60 text-red-700 dark:bg-red-500/20 dark:text-red-300"
                      }`}>{s.status_code}</span>
                    )}
                    <span className="text-slate-400 font-mono text-[9px] shrink-0">{s.duration_ms}ms</span>
                  </div>
                ))}
              </div>
              {!r.ok && r.steps?.filter(s => !s.ok).map((s, i) => s.error && (
                <div key={i} className="mt-2 bg-red-100/60 dark:bg-red-500/15 rounded p-1.5 text-[10px] font-mono text-red-700 dark:text-red-300 break-all">
                  {s.error?.slice(0, 200)}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};
