// BugMemoryAggregatorPage — Phase 1 final dashboard (read-only).
//
// Unified view across QA Copilot findings + AI Investigator findings, with
// search and severity/source filters. Reuses /api/admin/bug-memory routes.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Bug, ChevronLeft, Loader2, Search, Filter, AlertTriangle,
  ShieldAlert, Activity, Sparkles, RefreshCw, XCircle, Database,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const SEVERITY_COLOR = {
  P0: "bg-red-500/15 border-red-500/50 text-red-300",
  P1: "bg-amber-500/15 border-amber-500/50 text-amber-300",
  P2: "bg-blue-500/15 border-blue-500/50 text-blue-300",
  P3: "bg-stone-500/15 border-stone-500/50 text-stone-300",
};

const SOURCE_META = {
  qa_copilot:      { label: "QA Copilot",      icon: Sparkles,    badge: "bg-blue-500/10 border-blue-500/40 text-blue-300" },
  ai_investigator: { label: "AI Investigator", icon: ShieldAlert, badge: "bg-violet-500/10 border-violet-500/40 text-violet-300" },
};

const SEVERITY_OPTIONS = ["", "P0", "P1", "P2", "P3"];
const SOURCE_OPTIONS = [
  { value: "", label: "Toate sursele" },
  { value: "qa_copilot", label: "QA Copilot" },
  { value: "ai_investigator", label: "AI Investigator" },
];

const BugMemoryAggregatorPage = () => {
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [bySeverity, setBySeverity] = useState({});
  const [bySource, setBySource] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [severity, setSeverity] = useState("");
  const [source, setSource] = useState("");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null); // null = not searched

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setRefreshing(true);
      try {
        const params = { limit: 60 };
        if (severity) params.severity = severity;
        if (source) params.source = source;
        const [s, r] = await Promise.all([
          ax.get("/api/admin/bug-memory/stats"),
          ax.get("/api/admin/bug-memory/recent", { params }),
        ]);
        if (cancelled) return;
        setStats(s.data);
        setItems(r.data.items || []);
        setBySeverity(r.data.by_severity || {});
        setBySource(r.data.by_source || {});
      } finally {
        if (!cancelled) {
          setRefreshing(false);
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [severity, source]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const params = { limit: 60 };
      if (severity) params.severity = severity;
      if (source) params.source = source;
      const [s, r] = await Promise.all([
        ax.get("/api/admin/bug-memory/stats"),
        ax.get("/api/admin/bug-memory/recent", { params }),
      ]);
      setStats(s.data);
      setItems(r.data.items || []);
      setBySeverity(r.data.by_severity || {});
      setBySource(r.data.by_source || {});
    } finally {
      setRefreshing(false);
    }
  };

  const performSearch = async (q) => {
    setSearching(true);
    try {
      const { data } = await ax.get("/api/admin/bug-memory/search", {
        params: { q, limit: 30 },
      });
      setSearchResults(data);
    } finally {
      setSearching(false);
    }
  };

  const runSearch = (e) => {
    e?.preventDefault();
    const q = query.trim();
    if (q.length < 2) {
      setSearchResults(null);
      return;
    }
    performSearch(q);
  };

  const clearSearch = () => {
    setQuery("");
    setSearchResults(null);
  };

  const displayItems = searchResults ? searchResults.items : items;
  const displayCount = searchResults ? searchResults.total : items.length;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="bm-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
            <Bug className="w-5 h-5 text-amber-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="bm-title">
              Bug Memory <span className="italic gradient-text">Aggregator</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Vedere unificată: findings QA Copilot + AI Investigator. <strong>Read-only</strong> — nu modifici findings de aici (folosește modulele originale).
            </p>
          </div>
          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-stone-300"
            data-testid="bm-refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center text-stone-400 flex items-center justify-center gap-2 py-10">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
          </div>
        ) : (
          <>
            {/* STATS */}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="bm-stats">
                <StatCard label="QA findings" value={stats.qa_findings} icon={Sparkles} color="blue" />
                <StatCard label="AI Investigator" value={stats.ai_investigator_findings} icon={ShieldAlert} color="violet" />
                <StatCard label="Total findings" value={stats.total} icon={Database} color="amber" />
                <StatCard label="Afișate acum" value={displayCount} icon={Activity} color="emerald" />
              </div>
            )}

            {/* SEARCH */}
            <form onSubmit={runSearch} className="flex items-center gap-2 mb-4" data-testid="bm-search-form">
              <div className="flex-1 relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Caută în toate findings (ex: timeout, 401, undefined, ObjectId)..."
                  className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-[#0e0e10] border border-white/10 text-sm text-white placeholder:text-stone-500 focus:outline-none focus:border-white/30"
                  data-testid="bm-search-input"
                />
              </div>
              <button
                type="submit"
                disabled={searching || query.trim().length < 2}
                className="px-4 py-2.5 rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-200 text-sm hover:bg-amber-500/25 disabled:opacity-50"
                data-testid="bm-search-submit"
              >
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Caută"}
              </button>
              {searchResults !== null && (
                <button
                  type="button"
                  onClick={clearSearch}
                  className="px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-stone-300 text-sm hover:bg-white/10"
                  data-testid="bm-search-clear"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              )}
            </form>

            {/* FILTERS (only when not in search mode) */}
            {!searchResults && (
              <div className="flex items-center gap-2 flex-wrap mb-4" data-testid="bm-filters">
                <span className="text-xs text-stone-500 inline-flex items-center gap-1">
                  <Filter className="w-3.5 h-3.5" /> Filtre:
                </span>
                <div className="flex items-center gap-1">
                  {SEVERITY_OPTIONS.map(s => (
                    <button
                      key={s || "all"}
                      onClick={() => setSeverity(s)}
                      className={`px-2.5 py-1 text-[11px] rounded-lg border transition-colors ${
                        severity === s
                          ? "bg-white/10 border-white/30 text-white"
                          : "bg-[#0e0e10] border-white/10 text-stone-400 hover:text-white"
                      }`}
                      data-testid={`bm-filter-severity-${s || "all"}`}
                    >
                      {s || "Toate severitățile"}
                      {s && bySeverity[s] !== undefined && (
                        <span className="ml-1 text-stone-500">({bySeverity[s]})</span>
                      )}
                    </button>
                  ))}
                </div>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="px-2.5 py-1 text-[11px] rounded-lg bg-[#0e0e10] border border-white/10 text-stone-300 focus:outline-none focus:border-white/30"
                  data-testid="bm-filter-source"
                >
                  {SOURCE_OPTIONS.map(o => (
                    <option key={o.value || "all"} value={o.value}>{o.label}</option>
                  ))}
                </select>
                {(severity || source) && (
                  <button
                    onClick={() => { setSeverity(""); setSource(""); }}
                    className="text-[10px] text-stone-500 hover:text-white underline"
                    data-testid="bm-filter-reset"
                  >
                    Reset
                  </button>
                )}
              </div>
            )}

            {/* RESULTS */}
            <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-2">
              {displayItems.length === 0 ? (
                <div className="text-center py-10 text-stone-500 text-sm" data-testid="bm-empty">
                  {searchResults
                    ? `Niciun rezultat pentru "${query}".`
                    : "Niciun finding cu filtrele curente."}
                </div>
              ) : (
                <div className="divide-y divide-white/5" data-testid="bm-list">
                  {displayItems.map((item, i) => (
                    <BugItemRow key={`${item.source}-${item.id || i}`} item={item} highlighted={!!searchResults} />
                  ))}
                </div>
              )}
            </div>

            {/* FOOTER NOTE */}
            <div className="mt-6 text-[11px] text-stone-500 bg-violet-500/5 border border-violet-500/30 rounded-xl p-3">
              <strong className="text-violet-200">Phase 1 complete.</strong> Acest dashboard este pur de observabilitate.
              Acțiunile pe findings (rezolvare, dismiss, regenerare prompt) rămân în modulele originale:{" "}
              <Link to="/admin/qa-copilot" className="underline hover:text-white">QA Copilot</Link>
              {" • "}
              <Link to="/admin/ai-control" className="underline hover:text-white">AI Control Center</Link>.
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon: Icon, color }) => {
  const cls = {
    emerald: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    amber:   "border-amber-500/30 bg-amber-500/5 text-amber-300",
    violet:  "border-violet-500/30 bg-violet-500/5 text-violet-300",
    blue:    "border-blue-500/30 bg-blue-500/5 text-blue-300",
  }[color];
  return (
    <div className={`rounded-xl border p-4 ${cls}`}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider">{label}</div>
        <Icon className="w-4 h-4 opacity-60" />
      </div>
      <div className="text-3xl font-mono mt-2 text-white">{value ?? 0}</div>
    </div>
  );
};

const BugItemRow = ({ item, highlighted }) => {
  const sm = SOURCE_META[item.source] || { label: item.source, icon: Bug, badge: "bg-stone-500/10 border-stone-500/40 text-stone-300" };
  const SIcon = sm.icon;
  const sevCls = SEVERITY_COLOR[item.severity] || SEVERITY_COLOR.P2;
  return (
    <div className="px-4 py-3 flex items-start gap-3 hover:bg-white/[0.02]" data-testid={`bm-item-${item.id || item.source}`}>
      <div className="shrink-0 mt-1 flex flex-col items-center gap-1">
        <span className={`inline-flex items-center gap-1 text-[10px] uppercase px-1.5 py-0.5 rounded border ${sm.badge}`}>
          <SIcon className="w-2.5 h-2.5" /> {sm.label}
        </span>
        <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded border ${sevCls}`}>{item.severity || "P2"}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white font-medium truncate">{item.summary || "(fără titlu)"}</div>
        {item.text && (
          <div className="text-xs text-stone-400 mt-1 line-clamp-2">{item.text}</div>
        )}
        <div className="text-[10px] text-stone-500 mt-1.5 flex items-center gap-2 flex-wrap">
          {item.category && <span className="font-mono">{item.category}</span>}
          {item.session_title && (
            <span className="text-stone-400">· Sesiune: {item.session_title}</span>
          )}
          {item.ts && <span>· {new Date(item.ts).toLocaleString("ro-RO")}</span>}
          {highlighted && item.score !== undefined && (
            <span className="ml-auto text-amber-400">score: {item.score}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default BugMemoryAggregatorPage;
