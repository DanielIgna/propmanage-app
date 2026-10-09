// Manual Tester — Admin page for human-driven QA test runs.
// Route: /admin/manual-tester
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Check, X, MinusCircle, Save, Sparkles, ChevronLeft, Download,
  Loader2, AlertCircle, Plus, Bot, RotateCcw, TrendingUp, TrendingDown, Minus, Activity,
} from "lucide-react";
import { API } from "../DashShared";
import { ThemeSwitcher } from "../../components/ThemeSwitcher";

const STATUS_META = {
  pass: { label: "PASS", cls: "bg-emerald-500 text-stone-950 border-emerald-500" },
  fail: { label: "FAIL", cls: "bg-rose-500 text-white border-rose-500" },
  skip: { label: "SKIP", cls: "bg-stone-600 text-stone-100 border-stone-600" },
};

const ManualTesterPage = () => {
  const [view, setView] = useState("runner"); // runner | trends
  const [suites, setSuites] = useState([]);
  const [activeSuite, setActiveSuite] = useState(null);
  const [loading, setLoading] = useState(true);
  // results: { [caseId]: { status, notes } }
  const [results, setResults] = useState({});
  const [extraCases, setExtraCases] = useState([]); // AI-suggested ones, scoped to active suite
  const [aiBusy, setAiBusy] = useState(false);
  const [aiTopic, setAiTopic] = useState("");
  const [aiError, setAiError] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const [previousRuns, setPreviousRuns] = useState([]);
  const [label, setLabel] = useState("");
  const [env, setEnv] = useState("preview");

  useEffect(() => {
    const load = async () => {
      try {
        const r = await axios.get(`${API}/admin/manual-tester/suites`);
        setSuites(r.data?.suites || []);
        if ((r.data?.suites || []).length > 0) setActiveSuite(r.data.suites[0].id);
      } finally { setLoading(false); }
    };
    load();
    axios.get(`${API}/admin/manual-tester/runs`, { params: { limit: 8 } })
      .then((r) => setPreviousRuns(r.data?.items || []))
      .catch(() => {});
    // Try to restore an in-progress session
    try {
      const cached = JSON.parse(localStorage.getItem("manual_tester_draft") || "{}");
      if (cached?.results) setResults(cached.results);
      if (cached?.extraCases) setExtraCases(cached.extraCases);
      if (cached?.label) setLabel(cached.label);
      if (cached?.env) setEnv(cached.env);
    } catch (_e) { /* ignore */ }
  }, []);

  // Persist draft to localStorage on every change.
  useEffect(() => {
    localStorage.setItem("manual_tester_draft", JSON.stringify({ results, extraCases, label, env }));
  }, [results, extraCases, label, env]);

  const suite = useMemo(() => suites.find((s) => s.id === activeSuite), [suites, activeSuite]);
  const allCases = useMemo(() => {
    if (!suite) return [];
    return [...suite.cases, ...extraCases.filter((c) => c._suite_id === suite.id)];
  }, [suite, extraCases]);

  const summary = useMemo(() => {
    const tot = Object.keys(results).length;
    const pass = Object.values(results).filter((r) => r.status === "pass").length;
    const fail = Object.values(results).filter((r) => r.status === "fail").length;
    const skip = Object.values(results).filter((r) => r.status === "skip").length;
    return { tot, pass, fail, skip };
  }, [results]);

  const setStatus = (caseId, status) => {
    setResults((prev) => ({ ...prev, [caseId]: { ...prev[caseId], status, case_id: caseId } }));
  };
  const setNotes = (caseId, notes) => {
    setResults((prev) => ({ ...prev, [caseId]: { ...prev[caseId], notes, case_id: caseId } }));
  };

  const aiSuggest = async () => {
    setAiError("");
    if (!aiTopic.trim()) { setAiError("Introdu un topic (ex: 'edge cases pe checkout Stripe')."); return; }
    setAiBusy(true);
    try {
      const ctx = suite ? `Suite curentă: ${suite.name} (${suite.description}).` : "";
      const r = await axios.post(`${API}/admin/manual-tester/suggest`, { topic: aiTopic, context: ctx });
      const newCases = (r.data?.cases || []).map((c) => ({ ...c, _suite_id: suite?.id, ai_suggested: true }));
      setExtraCases((prev) => [...prev, ...newCases]);
      setAiTopic("");
    } catch (e) {
      setAiError(e?.response?.data?.detail || "Eroare AI");
    } finally {
      setAiBusy(false);
    }
  };

  const saveRun = async () => {
    if (Object.keys(results).length === 0) { setSavedMsg("Marchează cel puțin un caz înainte de salvare."); return; }
    setSaving(true); setSavedMsg("");
    try {
      const payload = {
        suite_id: activeSuite,
        label: label || `Run ${new Date().toLocaleString("ro-RO")}`,
        environment: env,
        results: Object.values(results).filter((r) => r.status),
      };
      await axios.post(`${API}/admin/manual-tester/runs`, payload);
      setSavedMsg(`✓ Salvat cu succes! ${payload.results.length} cazuri.`);
      // Reload runs list
      const r = await axios.get(`${API}/admin/manual-tester/runs`, { params: { limit: 8 } });
      setPreviousRuns(r.data?.items || []);
    } catch (e) {
      setSavedMsg(`✗ Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ label, env, summary, results, extraCases }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `manual_tester_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const resetDraft = () => {
    if (!window.confirm("Resetezi sesiunea curentă? (Rezultatele nesalvate se pierd.)")) return;
    setResults({}); setExtraCases([]); setLabel(""); setSavedMsg("");
    localStorage.removeItem("manual_tester_draft");
  };

  if (loading) return <div className="min-h-screen bg-stone-950 text-stone-400 flex items-center justify-center">Se încarcă...</div>;

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="max-w-7xl mx-auto p-4 sm:p-6">
        <Link to="/admin" className="text-stone-400 hover:text-stone-200 inline-flex items-center gap-1 text-sm mb-4">
          <ChevronLeft className="w-4 h-4" /> Înapoi Admin
        </Link>

        <div className="flex items-center justify-between flex-wrap gap-4 mb-5">
          <div>
            <h1 className="text-2xl font-bold">🧪 Tester Manual</h1>
            <p className="text-xs text-stone-400">QA driven by humans · {suites.length} suite-uri · {suites.reduce((s, x) => s + x.cases.length, 0)} cazuri</p>
          </div>
          <div className="flex items-center gap-3">
            <ThemeSwitcher />
            <div className="flex gap-1 p-1 bg-stone-900/60 border border-stone-800 rounded-lg">
              <button
                onClick={() => setView("runner")}
                data-testid="mt-view-runner"
                className={`px-3 py-1.5 rounded text-xs font-semibold inline-flex items-center gap-1.5 ${view === "runner" ? "bg-emerald-500 text-stone-950" : "text-stone-400"}`}
              >
                <Check className="w-3.5 h-3.5" /> Runner
              </button>
              <button
                onClick={() => setView("trends")}
                data-testid="mt-view-trends"
                className={`px-3 py-1.5 rounded text-xs font-semibold inline-flex items-center gap-1.5 ${view === "trends" ? "bg-violet-500 text-white" : "text-stone-400"}`}
              >
                <Activity className="w-3.5 h-3.5" /> Trends 30d
              </button>
            </div>
            {view === "runner" && <SummaryBadge summary={summary} />}
          </div>
        </div>

        {view === "trends" ? <TrendsPanel /> : (
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
          {/* Sidebar suites */}
          <aside className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 h-fit" data-testid="mt-sidebar">
            {suites.map((s) => {
              const isActive = activeSuite === s.id;
              const tested = s.cases.filter((c) => results[c.id]).length;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSuite(s.id)}
                  data-testid={`mt-suite-${s.id}`}
                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 text-sm mb-0.5 transition-colors ${
                    isActive ? "bg-emerald-500/15 text-emerald-300 font-semibold" : "text-stone-300 hover:bg-stone-800"
                  }`}
                >
                  <span>{s.icon}</span>
                  <span className="flex-1">{s.name}</span>
                  <span className="text-[10px] text-stone-500 tabular-nums">{tested}/{s.cases.length}</span>
                </button>
              );
            })}

            <div className="border-t border-stone-800 mt-3 pt-3 space-y-2 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-0.5">Etichetă run</div>
                <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="ex: smoke pre-deploy"
                  className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1 text-xs" data-testid="mt-label" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-0.5">Mediu</div>
                <select value={env} onChange={(e) => setEnv(e.target.value)} className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1 text-xs" data-testid="mt-env">
                  <option value="preview">Preview</option>
                  <option value="production">Production</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <button onClick={saveRun} disabled={saving} data-testid="mt-save"
                  className="px-3 py-1.5 rounded-lg bg-emerald-500 text-stone-950 text-xs font-bold inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
                  {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  Salvează run
                </button>
                <button onClick={exportJson}
                  className="px-3 py-1.5 rounded-lg bg-stone-800 text-stone-200 text-xs font-semibold inline-flex items-center justify-center gap-1.5">
                  <Download className="w-3 h-3" /> Export JSON
                </button>
                <button onClick={resetDraft} data-testid="mt-reset"
                  className="px-3 py-1.5 rounded-lg bg-stone-800 text-rose-400 hover:bg-rose-500/15 text-xs font-semibold inline-flex items-center justify-center gap-1.5">
                  <RotateCcw className="w-3 h-3" /> Reset draft
                </button>
              </div>
              {savedMsg && <div className="text-[11px] text-stone-300">{savedMsg}</div>}
            </div>
          </aside>

          {/* Test cases panel */}
          <section className="space-y-3">
            {suite && (
              <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="mt-suite-header">
                <h2 className="text-lg font-bold">{suite.icon} {suite.name}</h2>
                <p className="text-sm text-stone-400 mt-0.5">{suite.description}</p>
              </div>
            )}

            {/* AI suggester */}
            <div className="bg-violet-500/5 border border-violet-500/30 rounded-2xl p-4" data-testid="mt-ai-box">
              <div className="flex items-center gap-2 mb-2">
                <Bot className="w-4 h-4 text-violet-300" />
                <span className="text-sm font-bold text-violet-200">AI sugerează cazuri noi pentru suite-ul curent</span>
              </div>
              <div className="flex gap-2 flex-wrap">
                <input value={aiTopic} onChange={(e) => setAiTopic(e.target.value)}
                  placeholder='ex: "edge cases pe upload document mare"' data-testid="mt-ai-topic"
                  className="flex-1 min-w-[200px] bg-stone-800 border border-stone-700 rounded px-3 py-1.5 text-sm" />
                <button onClick={aiSuggest} disabled={aiBusy} data-testid="mt-ai-go"
                  className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-xs font-bold inline-flex items-center gap-1.5 disabled:opacity-50">
                  {aiBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  Sugerează
                </button>
              </div>
              {aiError && <div className="text-xs text-rose-400 mt-2 flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" /> {aiError}</div>}
            </div>

            {allCases.map((c, i) => (
              <TestCaseRow
                key={c.id}
                caseObj={c}
                index={i}
                result={results[c.id]}
                onStatus={(s) => setStatus(c.id, s)}
                onNotes={(n) => setNotes(c.id, n)}
              />
            ))}

            {allCases.length === 0 && (
              <div className="text-stone-500 italic text-sm p-4">
                Niciun caz în acest suite (încă). Folosește AI mai sus pentru a genera unele.
              </div>
            )}

            {previousRuns.length > 0 && (
              <PreviousRuns runs={previousRuns} />
            )}
          </section>
        </div>
        )}
      </div>
    </div>
  );
};

const SummaryBadge = ({ summary }) => (
  <div className="flex items-center gap-3 bg-stone-900/40 border border-stone-800 rounded-xl px-4 py-2" data-testid="mt-summary">
    <span className="text-[11px] uppercase tracking-wider text-stone-500 font-bold">Progres</span>
    <span className="text-emerald-400 font-bold tabular-nums">{summary.pass} <span className="text-stone-500 text-[11px]">pass</span></span>
    <span className="text-rose-400 font-bold tabular-nums">{summary.fail} <span className="text-stone-500 text-[11px]">fail</span></span>
    <span className="text-stone-400 font-bold tabular-nums">{summary.skip} <span className="text-stone-500 text-[11px]">skip</span></span>
    <span className="text-stone-300 font-bold tabular-nums">{summary.tot} <span className="text-stone-500 text-[11px]">total</span></span>
  </div>
);

const TestCaseRow = ({ caseObj, index: i, result, onStatus, onNotes }) => {
  const [open, setOpen] = useState(false);
  const status = result?.status;
  return (
    <div className={`bg-stone-900/40 border rounded-xl p-3 transition-colors ${
      status === "pass" ? "border-emerald-500/40 bg-emerald-500/5" :
      status === "fail" ? "border-rose-500/40 bg-rose-500/5" :
      status === "skip" ? "border-stone-600 bg-stone-800/20" :
      "border-stone-800"
    }`} data-testid={`mt-case-${caseObj.id}`}>
      <div className="flex items-start gap-3">
        <div className="text-[11px] text-stone-500 font-mono mt-0.5 tabular-nums w-6">#{i + 1}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-stone-100">{caseObj.title}</span>
            {caseObj.ai_suggested && (
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 inline-flex items-center gap-0.5">
                <Sparkles className="w-2.5 h-2.5" /> AI
              </span>
            )}
            {status && (
              <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold border ${STATUS_META[status].cls}`}>
                {STATUS_META[status].label}
              </span>
            )}
          </div>
          <button onClick={() => setOpen(!open)} className="text-[11px] text-stone-400 hover:text-stone-200 mt-0.5">
            {open ? "Ascunde detalii" : "Vezi pași & rezultat așteptat"}
          </button>
          {open && (
            <div className="mt-2 space-y-2 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-0.5">Pași</div>
                <ol className="list-decimal list-inside text-stone-300 space-y-0.5">
                  {(caseObj.steps || []).map((s, si) => <li key={si}>{s}</li>)}
                </ol>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-0.5">Rezultat așteptat</div>
                <div className="text-stone-200 italic">{caseObj.expected}</div>
              </div>
            </div>
          )}
          {(status === "fail" || result?.notes) && (
            <textarea
              value={result?.notes || ""}
              onChange={(e) => onNotes(e.target.value)}
              placeholder="Note / detalii bug, screenshot URL, console error..."
              rows={2}
              data-testid={`mt-notes-${caseObj.id}`}
              className="w-full mt-2 bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-xs"
            />
          )}
        </div>
        <div className="flex gap-1 shrink-0">
          <button onClick={() => onStatus("pass")} data-testid={`mt-pass-${caseObj.id}`}
            className={`w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors ${status === "pass" ? "bg-emerald-500 text-stone-950" : "bg-stone-800 text-stone-400 hover:bg-emerald-500/15 hover:text-emerald-300"}`}>
            <Check className="w-4 h-4" />
          </button>
          <button onClick={() => onStatus("fail")} data-testid={`mt-fail-${caseObj.id}`}
            className={`w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors ${status === "fail" ? "bg-rose-500 text-white" : "bg-stone-800 text-stone-400 hover:bg-rose-500/15 hover:text-rose-300"}`}>
            <X className="w-4 h-4" />
          </button>
          <button onClick={() => onStatus("skip")} data-testid={`mt-skip-${caseObj.id}`}
            className={`w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors ${status === "skip" ? "bg-stone-600 text-stone-100" : "bg-stone-800 text-stone-400 hover:bg-stone-700"}`}>
            <MinusCircle className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const PreviousRuns = ({ runs }) => (
  <div className="mt-6 bg-stone-900/40 border border-stone-800 rounded-2xl p-4">
    <h3 className="text-sm font-bold mb-2">Run-uri anterioare</h3>
    <ul className="space-y-1 text-xs">
      {runs.map((r) => (
        <li key={r.id} className="flex items-center gap-3 px-2 py-1.5 rounded hover:bg-stone-800/40">
          <div className="text-stone-500 tabular-nums">{new Date(r.created_at).toLocaleString("ro-RO")}</div>
          <div className="flex-1 truncate text-stone-200">{r.label || `Run ${r.id.slice(0, 6)}`}</div>
          <span className="text-stone-500">{r.environment}</span>
          <span className="text-emerald-400 font-bold tabular-nums">{r.summary.pass}P</span>
          <span className="text-rose-400 font-bold tabular-nums">{r.summary.fail}F</span>
          <span className="text-stone-400 font-bold tabular-nums">{r.summary.skip}S</span>
          <span className="text-stone-500 text-[10px]">de {r.tester_email}</span>
        </li>
      ))}
    </ul>
  </div>
);

// ============================================================================
// COMPOUNDING QA — Trends panel
// ============================================================================
const TrendsPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/admin/manual-tester/trends`, { params: { days } })
      .then((r) => setData(r.data)).catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <div className="text-stone-400 text-sm flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă tendințele...</div>;
  if (!data || data.overall.total_runs === 0) {
    return (
      <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-6 text-center" data-testid="mt-trends-empty">
        <Activity className="w-10 h-10 mx-auto text-stone-600 mb-2" />
        <div className="text-stone-300 font-bold">Niciun run în ultimele {days} zile</div>
        <p className="text-xs text-stone-500 mt-1">Rulează cel puțin un test manual ca să apară tendințele aici.</p>
      </div>
    );
  }

  const o = data.overall;

  return (
    <div className="space-y-4">
      {/* Window selector + KPIs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 p-1 bg-stone-900/60 border border-stone-800 rounded-lg" data-testid="mt-trends-window">
          {[7, 14, 30, 90].map((d) => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold ${days === d ? "bg-violet-500 text-white" : "text-stone-400 hover:text-stone-200"}`}
              data-testid={`mt-trends-window-${d}`}
            >
              {d}d
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <KPI label="Run-uri" value={o.total_runs} />
          <KPI label="Cazuri executate" value={o.total_cases_executed} />
          <KPI label="Avg pass-rate" value={`${o.avg_pass_rate}%`} accent={o.avg_pass_rate >= 80 ? "emerald" : o.avg_pass_rate >= 60 ? "amber" : "rose"} />
          <KPI label="Total failures" value={o.total_failures} accent={o.total_failures > 0 ? "rose" : "stone"} />
        </div>
      </div>

      {/* Alerts */}
      {data.alerts.length > 0 && (
        <div className="space-y-2" data-testid="mt-trends-alerts">
          {data.alerts.map((a) => (
            <div key={a.suite_id} className={`p-3 rounded-xl border ${a.severity === "high" ? "border-rose-500/50 bg-rose-500/10" : "border-amber-500/50 bg-amber-500/10"} flex items-start gap-3`}>
              <AlertCircle className={`w-5 h-5 mt-0.5 ${a.severity === "high" ? "text-rose-400" : "text-amber-400"}`} />
              <div className="flex-1">
                <div className="font-bold text-stone-100">⚠ Regression detectat: <span className="underline">{a.suite_name}</span></div>
                <div className="text-xs text-stone-300 mt-0.5">{a.message}</div>
              </div>
              <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold ${a.severity === "high" ? "bg-rose-500 text-white" : "bg-amber-500 text-stone-950"}`}>
                {a.severity === "high" ? "Critical" : "Warning"}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* By-suite cards */}
      <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4">
        <h3 className="text-sm font-bold mb-3">Pass-rate per suite (ultimele {days} zile)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="mt-trends-by-suite">
          {data.by_suite.map((s) => <SuiteTrendCard key={s.suite_id} suite={s} />)}
        </div>
      </div>

      {/* Timeline */}
      {data.timeline.length > 0 && (
        <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4">
          <h3 className="text-sm font-bold mb-3">Activitate zilnică</h3>
          <TimelineChart timeline={data.timeline} />
        </div>
      )}
    </div>
  );
};

const KPI = ({ label, value, accent = "stone" }) => {
  const colorCls = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    rose: "text-rose-400",
    stone: "text-stone-200",
  }[accent];
  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-lg px-3 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold">{label}</div>
      <div className={`text-lg font-bold tabular-nums ${colorCls}`}>{value}</div>
    </div>
  );
};

const SuiteTrendCard = ({ suite }) => {
  const TrendIcon = suite.trend === "up" ? TrendingUp : suite.trend === "down" ? TrendingDown : Minus;
  const trendColor = suite.trend === "up" ? "text-emerald-400" : suite.trend === "down" ? "text-rose-400" : "text-stone-400";
  const rateColor = suite.latest_pass_rate >= 80 ? "text-emerald-400" : suite.latest_pass_rate >= 60 ? "text-amber-400" : "text-rose-400";
  return (
    <div className="p-3 bg-stone-800/30 border border-stone-800 rounded-xl" data-testid={`mt-trends-card-${suite.suite_id}`}>
      <div className="flex items-start gap-2 mb-2">
        <span className="text-xl shrink-0">{suite.suite_icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-stone-100 truncate">{suite.suite_name}</div>
          <div className="text-[11px] text-stone-500">{suite.total_runs} run-uri · {suite.total_cases} cazuri</div>
        </div>
        <div className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold inline-flex items-center gap-0.5 ${trendColor} bg-stone-800`}>
          <TrendIcon className="w-3 h-3" /> {suite.delta_pct > 0 ? "+" : ""}{suite.delta_pct}%
        </div>
      </div>
      <div className="flex items-end justify-between mb-1">
        <div>
          <div className={`text-2xl font-black tabular-nums ${rateColor}`}>{suite.latest_pass_rate}%</div>
          <div className="text-[10px] text-stone-500">latest · avg {suite.avg_pass_rate}%</div>
        </div>
        <Sparkline history={suite.history} />
      </div>
      {/* Mini progress bar */}
      <div className="h-1 bg-stone-800 rounded-full overflow-hidden">
        <div className={`h-full ${suite.latest_pass_rate >= 80 ? "bg-emerald-500" : suite.latest_pass_rate >= 60 ? "bg-amber-500" : "bg-rose-500"}`}
          style={{ width: `${suite.latest_pass_rate}%` }} />
      </div>
    </div>
  );
};

const Sparkline = ({ history }) => {
  if (!history || history.length === 0) return null;
  const W = 100, H = 30;
  const max = 100;
  const points = history.map((p, i) => {
    const x = (i / Math.max(1, history.length - 1)) * W;
    const y = H - (p.pass_rate / max) * H;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="opacity-80">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-violet-400" />
      {history.map((p, i) => {
        const x = (i / Math.max(1, history.length - 1)) * W;
        const y = H - (p.pass_rate / max) * H;
        const c = p.pass_rate >= 80 ? "#10b981" : p.pass_rate >= 60 ? "#f59e0b" : "#ef4444";
        return <circle key={i} cx={x} cy={y} r="1.5" fill={c} />;
      })}
    </svg>
  );
};

const TimelineChart = ({ timeline }) => {
  const maxTotal = Math.max(...timeline.map((t) => t.pass + t.fail + t.skip), 1);
  return (
    <div className="space-y-1.5" data-testid="mt-trends-timeline">
      {timeline.map((t) => {
        const tot = t.pass + t.fail + t.skip;
        return (
          <div key={t.date} className="flex items-center gap-2 text-xs">
            <div className="w-20 text-stone-500 tabular-nums">{t.date}</div>
            <div className="flex-1 h-5 bg-stone-800 rounded flex overflow-hidden">
              <div className="bg-emerald-500" style={{ width: `${(t.pass / maxTotal) * 100}%` }} title={`${t.pass} pass`} />
              <div className="bg-rose-500" style={{ width: `${(t.fail / maxTotal) * 100}%` }} title={`${t.fail} fail`} />
              <div className="bg-stone-600" style={{ width: `${(t.skip / maxTotal) * 100}%` }} title={`${t.skip} skip`} />
            </div>
            <div className="w-20 text-right text-stone-400 tabular-nums">
              <span className="text-emerald-400">{t.pass}</span>·<span className="text-rose-400">{t.fail}</span>·<span className="text-stone-500">{t.skip}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ManualTesterPage;
