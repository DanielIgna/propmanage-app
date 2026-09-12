// Demo Activity Log — what each demo collaborator does on the platform
import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Activity, ChevronLeft, Loader2, AlertTriangle, Search, Users, Eye,
  BarChart3, Clock, X, ArrowDown,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_COLOR = (s) => {
  if (s >= 500) return "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300";
  if (s >= 400) return "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300";
  if (s >= 200) return "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300";
  return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
};

const METHOD_COLOR = (m) => ({
  GET: "text-blue-600 dark:text-blue-400",
  POST: "text-emerald-600 dark:text-emerald-400",
  PUT: "text-amber-600 dark:text-amber-400",
  PATCH: "text-amber-600 dark:text-amber-400",
  DELETE: "text-rose-600 dark:text-rose-400",
}[m] || "text-slate-500");

const DemoActivityPage = () => {
  const [summary, setSummary] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [days, setDays] = useState(7);
  const [emailFilter, setEmailFilter] = useState("");
  const [q, setQ] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const params = { days, limit: 200 };
      if (emailFilter) params.email = emailFilter;
      if (q.trim()) params.q = q.trim();
      const [sR, lR] = await Promise.all([
        ax.get("/api/admin/demo-activity/summary", { params: { days } }),
        ax.get("/api/admin/demo-activity", { params }),
      ]);
      setSummary(sR.data);
      setLogs(lR.data.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days, emailFilter]);

  const onSearch = (e) => { e.preventDefault(); load(); };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="demo-activity-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <Activity className="w-5 h-5 text-cyan-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Demo Activity Log</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-400">Super-admin · audit colaboratori demo</span>
      </div>

      <div className="max-w-6xl">
        <div className="mb-5 p-4 rounded-xl bg-gradient-to-r from-cyan-50 to-blue-50 dark:from-cyan-500/10 dark:to-blue-500/10 border border-cyan-200 dark:border-cyan-500/30">
          <h2 className="font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2"><Eye className="w-4 h-4 text-cyan-500" /> Ce fac colaboratorii demo</h2>
          <p className="text-xs text-slate-600 dark:text-slate-300">
            Fiecare apel API făcut de conturile demo (cele 6 cu badge DEMO) este logat automat: ce pagini vizitează, ce butoane apasă, ce KPI-uri accesează, dacă primesc erori. Folosește pentru a vedea dacă feedback-ul lor e relevant și ce zone trebuie îmbunătățite.
          </p>
        </div>

        {/* Filters */}
        <form onSubmit={onSearch} className="mb-4 flex items-center gap-2 flex-wrap" data-testid="filters">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută acțiune (ex: campanie, dashboard)…"
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sm"
              data-testid="search-q" />
          </div>
          <select value={emailFilter} onChange={e => setEmailFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sm"
            data-testid="email-filter">
            <option value="">Toți utilizatorii ({summary?.users?.length || 0})</option>
            {(summary?.users || []).map(u => (
              <option key={u.email} value={u.email}>{u.email} ({u.total_actions})</option>
            ))}
          </select>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sm"
            data-testid="days-filter">
            <option value={1}>Ultimele 24h</option>
            <option value={7}>Ultimele 7 zile</option>
            <option value={30}>Ultimele 30 zile</option>
            <option value={90}>Ultimele 90 zile</option>
          </select>
          <button type="submit" className="px-3 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-600 text-white text-sm font-medium" data-testid="apply-search">Caută</button>
        </form>

        {error && <div className="mb-4 p-3 rounded-lg bg-rose-50 text-rose-700 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>}

        {loading ? (
          <div className="text-center py-12"><Loader2 className="w-7 h-7 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <>
            {/* Summary cards */}
            {summary && summary.users.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800" data-testid="summary-totals">
                  <h3 className="text-xs uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1"><BarChart3 className="w-3 h-3" /> Total acțiuni</h3>
                  <div className="text-3xl font-bold text-slate-900 dark:text-white">{summary.total_actions}</div>
                  <div className="text-xs text-slate-500 mt-1">în ultimele {summary.days} zile</div>
                </div>
                <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 lg:col-span-2">
                  <h3 className="text-xs uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1"><Users className="w-3 h-3" /> Top utilizatori activi</h3>
                  <div className="space-y-1.5">
                    {summary.users.slice(0, 5).map(u => (
                      <div key={u.email} className="flex items-center justify-between text-sm" data-testid={`user-row-${u.scope}`}>
                        <button onClick={() => setEmailFilter(u.email === emailFilter ? "" : u.email)}
                          className={`text-left flex-1 hover:text-cyan-500 ${emailFilter === u.email ? "text-cyan-600 dark:text-cyan-400 font-bold" : "text-slate-700 dark:text-slate-200"}`}>
                          <code className="text-xs font-mono">{u.email}</code>
                          <span className="text-[10px] uppercase ml-2 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800">{u.scope}</span>
                        </button>
                        <div className="flex items-center gap-3 text-xs">
                          {u.errors > 0 && <span className="text-amber-600 dark:text-amber-400">{u.errors} erori</span>}
                          <span className="font-bold text-slate-900 dark:text-white">{u.total_actions}</span>
                          {u.last_seen && <span className="text-slate-400 text-[10px]">{new Date(u.last_seen).toLocaleString("ro-RO")}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Global top pages */}
            {summary && summary.global_top_pages?.length > 0 && (
              <div className="mb-6 bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2">Pagini accesate global</h3>
                <div className="flex flex-wrap gap-2">
                  {summary.global_top_pages.map((p, i) => (
                    <div key={i} className="px-2.5 py-1 rounded-full bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-xs">
                      <span className="text-slate-700 dark:text-slate-200">{p.label}</span>
                      <span className="font-bold text-cyan-600 dark:text-cyan-400 ml-1.5">{p.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Logs table */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-x-auto">
              <table className="w-full text-sm" data-testid="activity-table">
                <thead className="bg-slate-50 dark:bg-slate-800/50">
                  <tr className="text-xs uppercase text-slate-500">
                    <th className="text-left px-3 py-2.5">Timp</th>
                    <th className="text-left px-3 py-2.5">Utilizator</th>
                    <th className="text-left px-2 py-2.5">Acțiune</th>
                    <th className="text-left px-2 py-2.5">Metoda</th>
                    <th className="text-left px-2 py-2.5">Status</th>
                    <th className="text-right px-3 py-2.5">Timp</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(l => (
                    <tr key={l.id} className="border-t border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30" data-testid={`log-${l.id}`}>
                      <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{new Date(l.ts).toLocaleString("ro-RO")}</td>
                      <td className="px-3 py-2">
                        <code className="text-[11px] font-mono text-slate-700 dark:text-slate-200">{l.email}</code>
                        <div className="text-[10px] uppercase text-slate-400">{l.scope}</div>
                      </td>
                      <td className="px-2 py-2">
                        <div className="text-sm text-slate-900 dark:text-white">{l.label}</div>
                        <code className="text-[10px] font-mono text-slate-400">{l.path}</code>
                      </td>
                      <td className="px-2 py-2"><span className={`text-[10px] font-bold ${METHOD_COLOR(l.method)}`}>{l.method}</span></td>
                      <td className="px-2 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${STATUS_COLOR(l.status_code)}`}>{l.status_code}</span></td>
                      <td className="px-3 py-2 text-right text-[10px] text-slate-400 whitespace-nowrap">{l.duration_ms}ms</td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan="6" className="text-center py-8 text-sm text-slate-500">Nicio activitate găsită în această perioadă.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-3 text-xs text-slate-500 flex items-center justify-between flex-wrap gap-2">
              <span>Afișate: <strong>{logs.length}</strong> acțiuni</span>
              <span>Logare pasivă fire-and-forget · zero impact pe latență</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DemoActivityPage;
