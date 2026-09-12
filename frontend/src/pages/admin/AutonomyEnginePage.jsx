// AutonomyEnginePage — strategic dashboard pentru autonomia platformei.
// Vizualizează scorul general (0-100) + 5 sub-scoruri + trend 30 zile + recomandări.
import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Gauge, Activity, Cpu, ShieldCheck, Wrench, Brain, RefreshCcw, Users,
  Loader2, TrendingUp, AlertTriangle, CheckCircle2, ChevronRight, Target, Zap, Sparkles,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });
import SelfDrivingPanel from "./SelfDrivingPanel";
import OperationalLoopPanel from "./OperationalLoopPanel";
import AutonomyActivityPanel from "./AutonomyActivityPanel";

const TIER_META = {
  "self-driving": { label: "Self-Driving", color: "#a855f7", ring: "stroke-violet-500", text: "text-violet-300", bg: "bg-violet-500/15 border-violet-500/30" },
  "autonomous":   { label: "Autonomous",   color: "#10b981", ring: "stroke-emerald-500", text: "text-emerald-300", bg: "bg-emerald-500/15 border-emerald-500/30" },
  "assisted":     { label: "Assisted",     color: "#f59e0b", ring: "stroke-amber-500", text: "text-amber-300", bg: "bg-amber-500/15 border-amber-500/30" },
  "manual":       { label: "Manual",       color: "#ef4444", ring: "stroke-red-500", text: "text-red-300", bg: "bg-red-500/15 border-red-500/30" },
};

const SUB_META = {
  operational: { icon: Activity,   label: "Operational",  hint: "Auto-matching, completare cereri, scheduler" },
  technical:   { icon: Cpu,        label: "Technical",    hint: "Smoke tests, snapshots, release gates" },
  security:    { icon: ShieldCheck,label: "Security",     hint: "OAuth, findings critice, GDPR" },
  dev:         { icon: Wrench,     label: "Dev",          hint: "Quality gates, QA findings, stabilitate" },
  ai:          { icon: Brain,      label: "AI",           hint: "Findings închise, memorie, knowledge base" },
  human:       { icon: Users,      label: "Human (HDI)",  hint: "Intervenții umane pendinte — 100 = platforma merge singură" },
};

const PRIORITY_META = {
  critical: { color: "border-red-500/40 bg-red-500/10",    text: "text-red-300",    label: "CRITIC" },
  high:     { color: "border-amber-500/40 bg-amber-500/10",text: "text-amber-300",  label: "RIDICAT" },
  medium:   { color: "border-cyan-500/40 bg-cyan-500/10",  text: "text-cyan-300",   label: "MEDIU" },
  low:      { color: "border-stone-500/40 bg-stone-500/10",text: "text-stone-300",  label: "SCĂZUT" },
};

// ============================== TIER DOWNGRADE ALERTS PANEL ==============================
const TierAlertsPanel = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState(null);
  const [includeTest, setIncludeTest] = useState(false);

  const load = async (showTests = includeTest) => {
    setLoading(true);
    try {
      const r = await ax.get("/api/admin/autonomy/alerts/recent", {
        params: { limit: 10, include_test: showTests },
      });
      setItems(r.data?.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(includeTest); }, [includeTest]);

  const sendTest = async () => {
    setTesting(true);
    setTestMsg(null);
    try {
      const r = await ax.post("/api/admin/autonomy/alerts/test");
      const d = r.data?.result?.downgrade;
      if (r.data?.result?.alerted && d) {
        setTestMsg(`✅ Alert trimis (${d.push_count} push · ${d.email_count} email). Activează "Arată test" pentru a-l vedea în listă.`);
        await load(includeTest);
      } else {
        setTestMsg(`ℹ ${r.data?.result?.reason || "Nu s-a trimis"}`);
      }
    } catch (e) {
      setTestMsg(`❌ ${e?.response?.data?.detail || "Eroare la test"}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="mt-6 bg-stone-900/40 border border-stone-800 rounded-3xl p-5" data-testid="tier-alerts-panel">
      <div className="flex items-start gap-3 flex-wrap">
        <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-stone-100">Tier Downgrade Alerts</h3>
          <p className="text-xs text-stone-400 mt-0.5">
            Notifică super-admin (push + email) când platforma iese din self-driving sau autonomous.
            Verificare după fiecare snapshot zilnic (03:15). De-dup pe 12h.
          </p>
        </div>
        <label className="text-[11px] flex items-center gap-1.5 text-stone-400 cursor-pointer select-none" data-testid="tier-alerts-toggle-test">
          <input
            type="checkbox"
            checked={includeTest}
            onChange={(e) => setIncludeTest(e.target.checked)}
            className="accent-violet-500"
          />
          🧪 Arată test
        </label>
        <button
          onClick={sendTest}
          disabled={testing}
          className="text-xs px-3 py-1.5 rounded-lg bg-violet-500/15 border border-violet-500/40 text-violet-200 hover:bg-violet-500/25 disabled:opacity-50 inline-flex items-center gap-1.5"
          data-testid="tier-alerts-test-btn"
        >
          {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
          Trimite test alert
        </button>
      </div>

      {testMsg && (
        <div className="mt-3 text-xs text-stone-200 bg-stone-800/60 border border-stone-700 rounded-lg px-3 py-2" data-testid="tier-alerts-test-msg">
          {testMsg}
        </div>
      )}

      <div className="mt-4 space-y-2" data-testid="tier-alerts-list">
        {loading && <div className="text-xs text-stone-500">Se încarcă...</div>}
        {!loading && items.length === 0 && (
          <div className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2 inline-flex items-center gap-2" data-testid="tier-alerts-empty">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {includeTest
              ? "Niciun downgrade înregistrat (inclusiv test) — platforma e stabilă."
              : "Niciun downgrade real înregistrat — platforma e stabilă."}
          </div>
        )}
        {!loading && items.map((a, i) => {
          const delta = Number(a.delta || 0);
          const ts = a.sent_at ? new Date(a.sent_at).toLocaleString("ro-RO", { dateStyle: "short", timeStyle: "short" }) : "—";
          const isTest = a.is_test === true;
          return (
            <div
              key={i}
              className={`flex flex-wrap items-center gap-3 border rounded-xl px-3 py-2 ${
                isTest
                  ? "border-amber-500/40 bg-amber-500/5"
                  : "border-rose-500/30 bg-rose-500/5"
              }`}
              data-testid={`tier-alert-${i}`}
            >
              {isTest && (
                <span
                  className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/30 text-amber-200 border border-amber-400/40"
                  data-testid="tier-alert-test-badge"
                >
                  🧪 TEST
                </span>
              )}
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${isTest ? "bg-stone-600/40 text-stone-300" : "bg-rose-500/20 text-rose-200"}`}>
                {a.prev_tier} → {a.new_tier}
              </span>
              <span className="text-sm text-stone-100 tabular-nums">
                {a.prev_score} → <strong>{a.new_score}</strong>
                <span className={`ml-2 text-xs ${delta < 0 ? "text-rose-300" : "text-emerald-300"}`}>
                  ({delta > 0 ? "+" : ""}{delta}pp)
                </span>
              </span>
              <span className="ml-auto text-[11px] text-stone-400">{ts}</span>
              <span className="text-[10px] text-stone-500 w-full sm:w-auto sm:ml-2">
                {a.push_count} push · {a.email_count} email
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================== RING ==============================
const ScoreRing = ({ score, color, size = 220, strokeWidth = 14, target }) => {
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const offset = c - pct * c;
  const targetPct = target ? Math.max(0, Math.min(100, target)) / 100 : null;
  const targetOffset = targetPct ? c - targetPct * c : null;
  return (
    <div className="relative inline-block" style={{ width: size, height: size }} data-testid="autonomy-ring">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#1f1f23" strokeWidth={strokeWidth} fill="none" />
        {targetOffset !== null && (
          <circle
            cx={size / 2} cy={size / 2} r={r}
            stroke="#3f3f46" strokeWidth={2} fill="none"
            strokeDashoffset={targetOffset}
            strokeLinecap="round" strokeDasharray="4 6"
          />
        )}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          stroke={color} strokeWidth={strokeWidth} fill="none"
          strokeDasharray={c} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1.2s ease-out" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-serif text-6xl" style={{ color }}>{Math.round(score)}</div>
        <div className="text-[11px] text-stone-400 uppercase tracking-[0.2em]">/ 100</div>
      </div>
    </div>
  );
};

// ============================== SUB-SCORE CARD ==============================
const SubScoreCard = ({ k, score, target, onClick }) => {
  const meta = SUB_META[k];
  const Icon = meta.icon;
  const pct = Math.max(0, Math.min(100, score));
  const barColor =
    pct >= 85 ? "bg-emerald-500" : pct >= 65 ? "bg-amber-500" : "bg-red-500";
  const gap = target ? Math.max(0, target - pct) : 0;
  return (
    <button
      onClick={onClick}
      className="text-left bg-[#0e0e10] border border-white/10 hover:border-[#d4ff3a]/40 rounded-2xl p-5 transition-colors group"
      data-testid={`autonomy-sub-${k}`}
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 border border-white/10">
          <Icon className="w-4 h-4 text-[#d4ff3a]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] text-stone-400 uppercase tracking-wider">{meta.label}</div>
          <div className="font-serif text-3xl mt-0.5">{Math.round(score)}</div>
          {target && <div className="text-[10px] text-stone-500">țintă: {target}</div>}
        </div>
        <ChevronRight className="w-4 h-4 text-stone-600 group-hover:text-[#d4ff3a] transition-colors" />
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden mb-2">
        <div className={`h-full ${barColor} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-[10px] text-stone-500">{meta.hint}</div>
      {gap > 0 && (
        <div className="text-[10px] text-amber-400 mt-1.5 flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> gap până la țintă: {gap.toFixed(0)}pt
        </div>
      )}
    </button>
  );
};

// ============================== SPARKLINE ==============================
const Sparkline = ({ data, valueKey = "general", color = "#d4ff3a" }) => {
  if (!data || data.length < 2) {
    return (
      <div className="h-12 flex items-center justify-center text-[10px] text-stone-500 italic">
        Trend va apărea după 2+ snapshot-uri zilnice
      </div>
    );
  }
  const w = 600, h = 60, pad = 4;
  const xStep = (w - pad * 2) / Math.max(1, data.length - 1);
  const points = data.map((d, i) => {
    const v = d.scores?.[valueKey] ?? 0;
    const x = pad + i * xStep;
    const y = pad + ((100 - v) / 100) * (h - pad * 2);
    return `${x},${y}`;
  }).join(" ");
  const area = `M${pad},${h} L${points.split(" ").join(" L")} L${w - pad},${h} Z`;
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="block">
      <path d={area} fill={color} opacity="0.12" />
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// ============================== DRILL-DOWN MODAL ==============================
const DrillDown = ({ subKey, breakdown, onClose }) => {
  if (!subKey || !breakdown) return null;
  const meta = SUB_META[subKey];
  const data = breakdown[subKey];
  const Icon = meta.icon;
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose} data-testid="autonomy-drilldown">
      <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-start gap-3 mb-5">
          <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 flex items-center justify-center">
            <Icon className="w-5 h-5 text-[#d4ff3a]" />
          </div>
          <div className="flex-1">
            <h3 className="font-serif text-2xl">{meta.label} Score</h3>
            <p className="text-xs text-stone-400 mt-0.5">{meta.hint}</p>
          </div>
          <div className="text-right">
            <div className="font-serif text-4xl text-[#d4ff3a]">{data.score}</div>
            <div className="text-[10px] text-stone-500">/ 100</div>
          </div>
        </div>

        <div className="space-y-3">
          {Object.entries(data.signals || {}).filter(([k]) => k !== "raw").map(([k, v]) => (
            <div key={k} className="bg-white/[0.02] border border-white/5 rounded-xl p-3" data-testid={`signal-${k}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-stone-300 font-mono">{k}</span>
                <span className="font-serif text-lg">{v}</span>
              </div>
              <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full bg-[#d4ff3a] transition-all" style={{ width: `${Math.min(100, Math.max(0, v))}%` }} />
              </div>
            </div>
          ))}
        </div>

        {data.signals?.raw && (
          <div className="mt-5">
            <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-2">Date brute</div>
            <div className="bg-black/40 border border-white/5 rounded-xl p-3 font-mono text-[11px] text-stone-300 overflow-x-auto">
              {Object.entries(data.signals.raw).map(([k, v]) => (
                <div key={k}>{k} = <span className="text-cyan-400">{String(v)}</span></div>
              ))}
            </div>
          </div>
        )}

        <button onClick={onClose} className="mt-5 w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl py-2.5 text-sm transition-colors" data-testid="autonomy-drilldown-close">
          Închide
        </button>
      </div>
    </div>
  );
};

// ============================== MAIN PAGE ==============================
export const AutonomyEnginePage = () => {
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [drillKey, setDrillKey] = useState(null);
  const [snapping, setSnapping] = useState(false);
  const [boosting, setBoosting] = useState(false);
  const [boostResult, setBoostResult] = useState(null);

  const load = async (force = false) => {
    if (force) setRefreshing(true); else setLoading(true);
    try {
      const [a, b] = await Promise.all([
        ax.get("/api/admin/autonomy/score"),
        ax.get("/api/admin/autonomy/history", { params: { days: 30 } }),
      ]);
      setReport(a.data);
      setHistory(b.data.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [a, b] = await Promise.all([
          ax.get("/api/admin/autonomy/score"),
          ax.get("/api/admin/autonomy/history", { params: { days: 30 } }),
        ]);
        if (cancelled) return;
        setReport(a.data);
        setHistory(b.data.items || []);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || "Eroare la încărcare");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const takeSnap = async () => {
    if (snapping) return;
    setSnapping(true);
    try {
      await ax.post("/api/admin/autonomy/snapshot");
      await load(true);
    } finally { setSnapping(false); }
  };

  const boostDev = async () => {
    if (boosting) return;
    if (!window.confirm("Confirmi BOOST DEV?\n\n• Rulează un Release Gate REAL (în background)\n• Recalculează snapshotul Autonomy (onest)\n\nNu mai marchează findings-uri ca 'dismissed' (decontaminare P1).")) return;
    setBoosting(true);
    setBoostResult(null);
    try {
      const { data } = await ax.post("/api/admin/autonomy/boost-dev");
      setBoostResult(data.summary);
      await load(true);
    } catch (e) {
      const status = e?.response?.status;
      let msg;
      if (status === 404) {
        msg = "Endpoint indisponibil pe acest mediu — necesită REDEPLOY la producție.";
      } else if (status === 401 || status === 403) {
        msg = "Acces interzis — trebuie să fii logat ca admin.";
      } else if (status === 500) {
        msg = `Eroare server (500): ${e?.response?.data?.detail || e?.message || "necunoscută"}`;
      } else if (!status) {
        msg = `Network/timeout: ${e?.message || "verifică conexiunea sau backend-ul"}`;
      } else {
        msg = `HTTP ${status}: ${e?.response?.data?.detail || e?.message || "vezi consola"}`;
      }
      console.error("[BoostDEV] failed:", e);
      setBoostResult({ error: msg, http_status: status });
    } finally { setBoosting(false); }
  };

  const [boostingAI, setBoostingAI] = useState(false);
  const [boostAIResult, setBoostAIResult] = useState(null);

  const boostAI = async () => {
    if (boostingAI) return;
    if (!window.confirm("BOOST AI este DEZACTIVAT (decontaminare P1).\n\nScorul AI se calculează acum DOAR pe date reale. Injectarea de documente/memorii sintetice nu mai influențează scorul.\n\nApeși pentru a vedea numărul REAL de documente/memorii?")) return;
    setBoostingAI(true);
    setBoostAIResult(null);
    try {
      const { data } = await ax.post("/api/admin/autonomy/seed-ai-data");
      setBoostAIResult(data);
      await load(true);
    } catch (e) {
      const status = e?.response?.status;
      const msg = status === 404
        ? "Endpoint indisponibil — necesită REDEPLOY la producție."
        : status === 403
        ? "Doar super-admin poate rula seed-ul."
        : `HTTP ${status || "?"}: ${e?.response?.data?.detail || e?.message || "eroare necunoscută"}`;
      setBoostAIResult({ error: msg });
    } finally { setBoostingAI(false); }
  };

  const [autoTuning, setAutoTuning] = useState(false);
  const [autoTuneResult, setAutoTuneResult] = useState(null);

  const autoTune = async () => {
    if (autoTuning) return;
    if (!window.confirm("Confirmi RECALCULARE ONESTĂ (Auto-Tune)?\n\n• Recalculează scorurile din semnale REALE\n• Snapshot Autonomy + AI Health\n\nDECONTAMINAT (P1): NU mai injectează date sintetice și NU mai marchează automat findings-uri. Idempotent.")) return;
    setAutoTuning(true);
    setAutoTuneResult(null);
    try {
      const { data } = await ax.post("/api/admin/autonomy/auto-tune");
      setAutoTuneResult(data.report);
      await load(true);
    } catch (e) {
      const status = e?.response?.status;
      const msg = status === 404
        ? "Endpoint indisponibil — necesită REDEPLOY la producție."
        : status === 403
        ? "Doar super-admin poate rula Auto-Tune."
        : `HTTP ${status || "?"}: ${e?.response?.data?.detail || e?.message || "eroare necunoscută"}`;
      setAutoTuneResult({ error: msg });
    } finally { setAutoTuning(false); }
  };

  const tierMeta = useMemo(() => {
    if (!report) return TIER_META.manual;
    return TIER_META[report.tier] || TIER_META.manual;
  }, [report]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> Se calculează autonomia...
      </div>
    );
  }
  if (!report) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-red-400">{error || "Eroare"}</div>
    );
  }

  const general = report.scores.general;
  const targetGeneral = report.targets?.general ?? 90;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="autonomy-back">← Înapoi la Admin Dashboard</Link>
        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="autonomy-title">
              Autonomy <span className="italic gradient-text">Engine</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">
              Cât din platformă funcționează singură? Scor 0-100, sub-scoruri per dimensiune, recomandări pentru a ajunge la <span className="text-[#d4ff3a]">{targetGeneral}+</span>.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Link to="/admin/orchestrator" className="pm-btn pm-btn-sm bg-violet-500/15 border border-violet-500/40 text-violet-200 hover:bg-violet-500/25" data-testid="autonomy-to-orchestrator" title="Orchestrator: playbook-uri self-healing + ledger acțiuni automate">
              <Activity className="w-3.5 h-3.5" /> Orchestrator
            </Link>
            <button
              onClick={autoTune}
              disabled={autoTuning}
              className="pm-btn pm-btn-sm bg-gradient-to-r from-fuchsia-500 to-violet-600 border border-fuchsia-400/50 text-white shadow-lg shadow-fuchsia-500/30 hover:from-fuchsia-400 hover:to-violet-500 disabled:opacity-60 font-semibold"
              data-testid="autonomy-auto-tune"
              title="Recalculare onestă: recompute scoruri din semnale reale + snapshot (fără date sintetice)"
            >
              {autoTuning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} Recalculează (onest)
            </button>
            <button onClick={boostDev} disabled={boosting} className="pm-btn pm-btn-sm bg-violet-500/15 border border-violet-500/40 text-violet-200 hover:bg-violet-500/25" data-testid="autonomy-boost-dev" title="Boost DEV: rulează Release Gate real + snapshot onest (fără dismiss de findings)">
              {boosting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />} Boost DEV
            </button>
            <button onClick={boostAI} disabled={boostingAI} className="pm-btn pm-btn-sm bg-stone-500/10 border border-stone-500/30 text-stone-400 hover:bg-stone-500/15" data-testid="autonomy-boost-ai" title="Dezactivat (decontaminare P1): scorul AI se calculează doar pe date reale">
              {boostingAI ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Brain className="w-3.5 h-3.5" />} Boost AI (off)
            </button>
            <button onClick={takeSnap} disabled={snapping} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="autonomy-take-snap">
              {snapping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Target className="w-3.5 h-3.5" />} Snapshot acum
            </button>
            <button onClick={() => load(true)} disabled={refreshing} className="pm-btn pm-btn-primary pm-btn-sm" data-testid="autonomy-refresh">
              {refreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCcw className="w-3.5 h-3.5" />} Refresh
            </button>
          </div>
        </div>

        {boostResult && (
          <div className="mt-4 rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4 text-sm" data-testid="autonomy-boost-result">
            {boostResult.error ? (
              <div className="space-y-1">
                <div className="text-red-300 flex items-center gap-2 font-semibold"><AlertTriangle className="w-4 h-4" /> Boost eșuat{boostResult.http_status ? ` (HTTP ${boostResult.http_status})` : ""}</div>
                <div className="text-stone-300 text-xs">{boostResult.error}</div>
                {boostResult.http_status === 404 && (
                  <div className="text-amber-300 text-xs mt-2">💡 Endpoint-ul `POST /api/admin/autonomy/boost-dev` a fost creat în PREVIEW. Trebuie să faci <strong>Save to GitHub</strong> → <strong>Redeploy</strong> pe Emergent ca să apară în producție.</div>
                )}
              </div>
            ) : (
              <div className="space-y-1.5 text-stone-200">
                <div className="flex items-center gap-2 text-violet-300 font-semibold mb-1"><Zap className="w-4 h-4" /> Boost DEV — rezultat</div>
                <div>• Release Gate: {boostResult.release_gate?.error ? <span className="text-red-300">{boostResult.release_gate.error}</span> : boostResult.release_gate?.status === "scheduled_in_background" ? <span className="text-amber-300">⏳ Rulează în background (~2-3 min). Refresh pagina după 3 min ca să vezi scorul final.</span> : <>id <code className="text-xs">{boostResult.release_gate?.id?.slice(0,8)}</code> · blocked: <strong className={boostResult.release_gate?.blocked ? "text-red-300" : "text-emerald-300"}>{String(boostResult.release_gate?.blocked)}</strong> · p0_fail: {boostResult.release_gate?.p0_fail ?? "—"}</>}</div>
                <div>• Findings vechi marcate dismissed: <strong className="text-emerald-300">{boostResult.qa_findings_dismissed}</strong></div>
                <div>• Scor DEV: <strong className="text-stone-400">{boostResult.previous_dev_score ?? "—"}</strong> → <strong className="text-[#d4ff3a]">{boostResult.new_dev_score ?? "—"}</strong> · General: <strong className="text-[#d4ff3a]">{boostResult.new_general_score ?? "—"}</strong></div>
              </div>
            )}
          </div>
        )}

        {boostAIResult && (
          <div className="mt-4 rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4 text-sm" data-testid="autonomy-boost-ai-result">
            {boostAIResult.error ? (
              <div className="space-y-1">
                <div className="text-red-300 flex items-center gap-2 font-semibold"><AlertTriangle className="w-4 h-4" /> Boost AI eșuat</div>
                <div className="text-stone-300 text-xs">{boostAIResult.error}</div>
              </div>
            ) : boostAIResult.deprecated ? (
              <div className="space-y-1.5">
                <div className="text-amber-300 font-semibold flex items-center gap-2"><Brain className="w-4 h-4" /> Boost AI — dezactivat (decontaminare P1)</div>
                <div className="text-stone-300 text-xs">{boostAIResult.message}</div>
                <div>• Documente REALE: <strong className="text-cyan-200">{boostAIResult.real_documents}</strong> <span className="text-stone-500">(seed excluse: {boostAIResult.excluded_seed_documents})</span></div>
                <div>• Memorii REALE: <strong className="text-cyan-200">{boostAIResult.real_memories}</strong> <span className="text-stone-500">(seed excluse: {boostAIResult.excluded_seed_memories})</span></div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <div className="text-cyan-300 font-semibold flex items-center gap-2"><Brain className="w-4 h-4" /> Boost AI Complete</div>
                <div>• Documente: <strong className="text-stone-400">{boostAIResult.documents?.before}</strong> → <strong className="text-cyan-200">{boostAIResult.documents?.after}</strong> <span className="text-stone-500">({boostAIResult.documents?.added} adăugate)</span></div>
                <div>• Memorii: <strong className="text-stone-400">{boostAIResult.memories?.before}</strong> → <strong className="text-cyan-200">{boostAIResult.memories?.after}</strong> <span className="text-stone-500">({boostAIResult.memories?.added} adăugate)</span></div>
                <div>• Scor AI nou: <strong className="text-[#d4ff3a]">{boostAIResult.new_ai_score ?? "—"}</strong> · General: <strong className="text-[#d4ff3a]">{boostAIResult.new_general_score ?? "—"}</strong> · Tier: <strong className="text-cyan-200">{boostAIResult.tier ?? "—"}</strong></div>
              </div>
            )}
          </div>
        )}

        {autoTuneResult && (
          <div className="mt-4 rounded-2xl border border-fuchsia-500/40 bg-gradient-to-br from-fuchsia-500/10 to-violet-500/5 p-4 text-sm" data-testid="autonomy-auto-tune-result">
            {autoTuneResult.error ? (
              <div className="space-y-1">
                <div className="text-red-300 flex items-center gap-2 font-semibold"><AlertTriangle className="w-4 h-4" /> Auto-Tune eșuat</div>
                <div className="text-stone-300 text-xs">{autoTuneResult.error}</div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-fuchsia-200 font-semibold flex items-center gap-2"><Sparkles className="w-4 h-4" /> Auto-Tune Complete</div>
                <div className="grid sm:grid-cols-2 gap-2 text-xs">
                  {(autoTuneResult.steps || []).map((s, i) => (
                    <div key={i} className={`px-3 py-2 rounded-lg border ${s.status === "ok" ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-200" : "border-red-500/30 bg-red-500/5 text-red-200"}`}>
                      {s.status === "ok" ? "✓" : "✗"} <strong>{s.name}</strong>
                      {s.docs_added != null && <span className="ml-2 text-stone-400">+{s.docs_added} docs · +{s.memories_added} mem</span>}
                      {s.inserted != null && <span className="ml-2 text-stone-400">+{s.inserted} {s.already_present > 0 ? `(${s.already_present} skipped)` : ""}</span>}
                      {s.dismissed != null && <span className="ml-2 text-stone-400">dismissed {s.dismissed}</span>}
                      {s.error && <span className="ml-2 text-red-300">{s.error}</span>}
                    </div>
                  ))}
                </div>
                <div className="border-t border-stone-700/40 pt-2 mt-2 space-y-1">
                  <div>• <strong>Autonomy General</strong>: <span className="text-stone-400">{autoTuneResult.before?.scores?.general ?? "—"}</span> → <strong className="text-[#d4ff3a]">{autoTuneResult.after?.scores?.general ?? "—"}</strong> {autoTuneResult.delta_general != null && <span className={autoTuneResult.delta_general >= 0 ? "text-emerald-300" : "text-rose-300"}>({autoTuneResult.delta_general >= 0 ? "+" : ""}{autoTuneResult.delta_general}pp)</span>} · Tier: <strong className="text-fuchsia-200">{autoTuneResult.after?.tier ?? "—"}</strong></div>
                  {autoTuneResult.ai_health && !autoTuneResult.ai_health.error && (
                    <div>• <strong>AI Health</strong>: <strong className="text-[#d4ff3a]">{autoTuneResult.ai_health.overall}</strong> <span className="text-stone-500">(findings {autoTuneResult.ai_health.findings} · effectiveness {autoTuneResult.ai_health.effectiveness} · concierge {autoTuneResult.ai_health.concierge})</span></div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* HERO: ring + tier + summary */}
        <div className="mt-6">
          <SelfDrivingPanel />
        </div>
        <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 md:p-8">
          <div className="grid md:grid-cols-[auto_1fr] gap-8 items-center">
            <div className="flex justify-center">
              <ScoreRing score={general} color={tierMeta.color} target={targetGeneral} />
            </div>
            <div>
              <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${tierMeta.bg} ${tierMeta.text} text-xs uppercase tracking-wider font-medium`} data-testid="autonomy-tier">
                <Gauge className="w-3 h-3" /> Tier: {tierMeta.label}
              </div>
              <h2 className="font-serif text-2xl mt-3">
                Platforma e <span style={{ color: tierMeta.color }}>{tierMeta.label.toLowerCase()}</span>
              </h2>
              <p className="text-sm text-stone-400 mt-2 max-w-xl">
                {report.tier === "self-driving" && "Excelent — sistemul ia decizii și execută cu supravegheri minime."}
                {report.tier === "autonomous" && "AI execută rutinele; admin doar aprobă pașii critici."}
                {report.tier === "assisted" && "AI sugerează — uman supervizează și execută. Există loc de creștere."}
                {report.tier === "manual" && "Multe procese încă necesită intervenție umană. Vezi recomandările pentru pași rapizi."}
              </p>
              <div className="mt-4 flex gap-3 text-[11px] text-stone-500">
                <span>📊 {history.length} snapshot{history.length === 1 ? "" : "-uri"}</span>
                <span>· 🎯 țintă: {targetGeneral}</span>
                <span>· ⏱ {report.cached ? "cached" : "live"}</span>
              </div>
              {history.length >= 2 && (
                <div className="mt-3">
                  <Sparkline data={history} color={tierMeta.color} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SUB-SCORES */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-6">
          {["operational", "technical", "security", "dev", "ai", "human"].map(k => (
            <SubScoreCard
              key={k}
              k={k}
              score={report.scores[k]}
              target={report.targets?.[k]}
              onClick={() => setDrillKey(k)}
            />
          ))}
        </div>

        {/* RECOMMENDATIONS */}
        <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 mt-6" data-testid="autonomy-recs">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-[#d4ff3a]" />
            <h2 className="font-serif text-xl">Recomandări prioritizate</h2>
            <span className="text-[10px] text-stone-500">({report.recommendations.length})</span>
            {report.recommendations.length > 0 && (
              <button
                onClick={async () => {
                  if (!window.confirm("Materializez recomandările ca TODO-uri în /admin/todo?")) return;
                  try {
                    const { data } = await ax.post("/api/admin/autonomy/generate-tasks", { max_items: 6 });
                    if (data?.ok === false) { alert("Eroare la materializare: " + (data.error || "necunoscută")); return; }
                    alert(`${data.counts?.injected || 0} TODO-uri create, ${data.counts?.skipped || 0} duplicate.`);
                  } catch (e) {
                    const msg = e?.response?.data?.detail || e?.response?.data?.error || e.message || "Eroare necunoscută";
                    alert("Eroare la materializare: " + msg);
                  }
                }}
                className="ml-auto text-[10px] inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#d4ff3a]/15 border border-[#d4ff3a]/40 text-[#d4ff3a] hover:bg-[#d4ff3a]/25"
                data-testid="autonomy-generate-tasks"
              >
                Materializează ca TODO-uri →
              </button>
            )}
          </div>
          {report.recommendations.length === 0 ? (
            <div className="text-sm text-emerald-300 flex items-center gap-2 py-4">
              <CheckCircle2 className="w-4 h-4" /> Toate metricile sunt în țintă. Nimic urgent de făcut!
            </div>
          ) : (
            <div className="space-y-2">
              {report.recommendations.map((r, i) => {
                const pm = PRIORITY_META[r.priority] || PRIORITY_META.medium;
                return (
                  <div key={i} className={`border rounded-xl p-3 ${pm.color}`} data-testid={`autonomy-rec-${i}`}>
                    <div className="flex items-start gap-3 flex-wrap">
                      <span className={`text-[10px] uppercase tracking-wider font-medium ${pm.text} px-2 py-0.5 rounded-full bg-black/30 border ${pm.color}`}>
                        {pm.label}
                      </span>
                      <span className="text-[10px] text-stone-400 uppercase tracking-wider">{SUB_META[r.area]?.label}</span>
                      <span className="ml-auto text-[11px] text-emerald-300">+{r.impact_points}pt</span>
                    </div>
                    <div className="text-sm text-stone-100 mt-1.5">{r.action}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* OPERATIONAL AUTONOMY LOOP (FN-021) */}
        <OperationalLoopPanel />

        {/* AUTONOMY ACTIVITY — unified action queue + real metrics (FN-021) */}
        <AutonomyActivityPanel />

        {/* TIER DOWNGRADE ALERTS PANEL */}
        <TierAlertsPanel />

        {/* WEIGHTS / SAFETY NOTE */}
        <div className="mt-6 bg-amber-500/10 border border-amber-500/30 rounded-3xl p-5 flex items-start gap-3" data-testid="autonomy-safety-note">
          <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-100">
            <strong>Read-only &amp; reversibil:</strong> Engine-ul citește doar colecții existente (requests, smoke_test_runs, oauth_health, admin_ai_findings). Nu modifică date. Ponderi configurabile via <code className="text-amber-300">/api/admin/autonomy/targets</code>. Snapshot zilnic 03:15 Europe/Bucharest în <code className="text-amber-300">autonomy_snapshots</code>.
          </div>
        </div>
      </div>

      <DrillDown subKey={drillKey} breakdown={report.breakdown} onClose={() => setDrillKey(null)} />
    </div>
  );
};

export default AutonomyEnginePage;
