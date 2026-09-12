// AutonomyOrchestratorPage — dispecerul transversal de autonomie (Sprint 1).
// Route: /admin/orchestrator
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Workflow, ChevronLeft, Loader2, RefreshCcw, Zap, Clock, CheckCircle2,
  AlertTriangle, ShieldAlert, Play, Timer, Gauge, MailWarning, FlaskConical,
  Brain, HeartPulse, ClipboardCheck,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const OUTCOME_META = {
  auto_resolved: { label: "Auto-rezolvat", color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  retry_scheduled: { label: "Retry programat", color: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30" },
  blocked_config: { label: "Blocat de config (fără retry)", color: "bg-orange-500/15 text-orange-300 border-orange-500/30" },
  failed_suppressed: { label: "Eșuat (escaladare suprimată)", color: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
  monitored: { label: "Monitorizat", color: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  escalated: { label: "Escaladat la om", color: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
  error: { label: "Eroare playbook", color: "bg-red-500/15 text-red-300 border-red-500/30" },
  skipped_disabled: { label: "Playbook oprit", color: "bg-stone-500/15 text-stone-300 border-stone-500/30" },
  recommended: { label: "Recomandat (neexecutat)", color: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  observed: { label: "Observat", color: "bg-stone-500/15 text-stone-300 border-stone-500/30" },
};

const AUTHORITY_META = {
  1: { label: "Observator", color: "text-stone-400" },
  2: { label: "Consilier", color: "text-amber-300" },
  3: { label: "Supravegheat", color: "text-sky-300" },
  4: { label: "Autonom", color: "text-violet-300" },
  5: { label: "Autonomie totală", color: "text-emerald-300" },
};

const PLAYBOOK_ICON = {
  smoke_fail_to_qa: FlaskConical,
  autonomy_reflex: Gauge,
  webhook_retry_guardian: MailWarning,
};

const StatCard = ({ icon: Icon, label, value, accent }) => (
  <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4" data-testid={`orch-stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
    <div className="flex items-center gap-2 text-xs text-stone-400 uppercase tracking-wider">
      <Icon className={`w-3.5 h-3.5 ${accent}`} /> {label}
    </div>
    <div className="text-2xl font-bold text-white mt-1.5">{value}</div>
  </div>
);

const PlaybookCard = ({ pb, gov, onToggle, onSimulate, onAuthority, simulating }) => {
  const Icon = PLAYBOOK_ICON[pb.id] || Workflow;
  const oc = OUTCOME_META[pb.last_outcome] || null;
  const confPct = gov ? Math.round((gov.confidence || 0) * 100) : null;
  const confColor = confPct === null ? "" : confPct >= 70 ? "text-emerald-300" : confPct >= 40 ? "text-amber-300" : "text-rose-300";
  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4 flex flex-col gap-3" data-testid={`playbook-${pb.id}`}>
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-500/30">
          <Icon className="w-4 h-4 text-violet-300" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-white">{pb.name}</div>
          <div className="text-xs text-stone-400 mt-1 leading-relaxed">{pb.description}</div>
        </div>
        <button
          onClick={() => onToggle(pb)}
          className={`relative w-10 h-5.5 h-6 rounded-full transition-colors ${pb.enabled ? "bg-emerald-500" : "bg-stone-700"}`}
          title={pb.enabled ? "Dezactivează" : "Activează"}
          data-testid={`toggle-${pb.id}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${pb.enabled ? "left-[18px]" : "left-0.5"}`} />
        </button>
      </div>
      {gov && (
        <div className="flex items-center gap-2 flex-wrap text-[11px]">
          <span className="text-stone-500 uppercase font-bold tracking-wider text-[10px]">Autoritate</span>
          <select
            value={gov.authority_level}
            onChange={(e) => onAuthority(pb.id, Number(e.target.value))}
            className="bg-stone-800 border border-stone-700 rounded-lg px-2 py-1 text-stone-200 text-[11px] focus:outline-none focus:border-violet-500"
            data-testid={`authority-select-${pb.id}`}
          >
            {[1, 2, 3, 4, 5].map(l => (
              <option key={l} value={l}>Nivel {l} · {AUTHORITY_META[l].label}</option>
            ))}
          </select>
          <span className={`px-2 py-0.5 rounded-lg bg-stone-800 ${confColor}`} title={`Încredere calculată din ultimele ${gov.confidence_runs} rulări`} data-testid={`confidence-${pb.id}`}>
            <Brain className="w-3 h-3 inline mr-1 -mt-0.5" />{confPct}% {gov.confidence_runs > 0 ? `(${gov.confidence_runs} rulări)` : "(fără istoric)"}
          </span>
        </div>
      )}
      <div className="flex items-center gap-2 flex-wrap text-[11px] text-stone-400">
        <span className="px-2 py-0.5 rounded-lg bg-stone-800">{pb.runs_total} rulări</span>
        {pb.last_run_at && <span className="px-2 py-0.5 rounded-lg bg-stone-800">ultima: {new Date(pb.last_run_at).toLocaleString("ro-RO")}</span>}
        {oc && <span className={`px-2 py-0.5 rounded-lg border ${oc.color}`}>{oc.label}</span>}
        <div className="flex-1" />
        <button
          onClick={() => onSimulate(pb.signal_kind)}
          disabled={simulating || !pb.enabled}
          className="px-2.5 py-1 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white flex items-center gap-1 font-medium"
          data-testid={`simulate-${pb.id}`}
        >
          {simulating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} Simulează
        </button>
      </div>
    </div>
  );
};

const LedgerEntry = ({ e }) => {
  const oc = OUTCOME_META[e.outcome] || OUTCOME_META.monitored;
  return (
    <div className="border border-stone-800 rounded-2xl p-4 bg-stone-900/30" data-testid={`ledger-entry-${e.id}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-semibold text-white">{e.playbook_name}</span>
        {e.test && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">TEST</span>}
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-lg border ${oc.color}`}>{oc.label}</span>
        <div className="flex-1" />
        {(e.minutes_saved || 0) > 0 && (
          <span className="text-[11px] text-emerald-300 flex items-center gap-1"><Timer className="w-3 h-3" /> ~{e.minutes_saved} min salvate</span>
        )}
        <span className="text-[11px] text-stone-500">{new Date(e.ts).toLocaleString("ro-RO")}</span>
      </div>
      {(e.steps || []).length > 0 && (
        <div className="mt-2.5 space-y-1.5">
          {e.steps.map((s, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              {s.ok
                ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                : <AlertTriangle className="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0" />}
              <div>
                <span className="text-stone-300 font-medium">{s.action}</span>
                <span className="text-stone-500"> — {s.detail}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function AutonomyOrchestratorPage() {
  const [overview, setOverview] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, l, g, d] = await Promise.all([
        ax.get("/api/admin/orchestrator/overview"),
        ax.get("/api/admin/orchestrator/ledger", { params: { limit: 50 } }),
        ax.get("/api/admin/orchestrator/governance"),
        ax.get("/api/admin/orchestrator/decisions", { params: { limit: 20 } }),
      ]);
      setOverview(o.data);
      setLedger(l.data?.items || []);
      setGovernance(g.data);
      setDecisions(d.data?.items || []);
    } catch (e) {
      setMsg(`❌ ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const govByPlaybook = React.useMemo(() => {
    const map = {};
    (governance?.playbooks || []).forEach(p => { map[p.id] = p; });
    return map;
  }, [governance]);

  const setAuthority = async (playbookId, level) => {
    try {
      await ax.post(`/api/admin/orchestrator/playbooks/${playbookId}/authority`, { level });
      setGovernance(g => ({
        ...g,
        playbooks: g.playbooks.map(p => p.id === playbookId ? { ...p, authority_level: level } : p),
      }));
      setMsg(`✅ Autoritate '${playbookId}' setată la nivel ${level} (${AUTHORITY_META[level].label}).`);
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const forceWatchdog = async () => {
    try {
      const r = await ax.post("/api/admin/orchestrator/watchdog-tick");
      setMsg(`🩺 Watchdog: ${r.data.jobs_checked} joburi verificate, ${r.data.healed.length} reînviate, ${r.data.failing_jobs.length} cu eșecuri repetate, ${r.data.stuck_retries} retry-uri deblocate.`);
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const forceReview = async () => {
    try {
      const r = await ax.post("/api/admin/orchestrator/decision-review");
      setMsg(`📋 Review: ${r.data.decisions_reviewed} decizii analizate, ${r.data.downgrades.length} degradări de autoritate.`);
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const toggle = async (pb) => {
    try {
      await ax.post(`/api/admin/orchestrator/playbooks/${pb.id}/toggle`, { enabled: !pb.enabled });
      setOverview(o => ({ ...o, playbooks: o.playbooks.map(x => x.id === pb.id ? { ...x, enabled: !pb.enabled } : x) }));
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const simulate = async (kind) => {
    setSimulating(true);
    setMsg(null);
    try {
      const r = await ax.post(`/api/admin/orchestrator/simulate/${kind}`);
      const out = r.data?.ledger?.outcome;
      setMsg(`✅ Semnal '${kind}' simulat → ${OUTCOME_META[out]?.label || out}. Vezi ledger-ul de mai jos.`);
      await load();
    } catch (e) {
      setMsg(`❌ ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const forceRetryTick = async () => {
    try {
      const r = await ax.post("/api/admin/orchestrator/retry-tick");
      setMsg(`🔁 Retry tick: ${r.data.processed} procesate, ${r.data.sent} trimise, ${r.data.rescheduled} reprogramate, ${r.data.failed_permanent} eșuate definitiv.`);
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const resumeBlocked = async () => {
    try {
      const r = await ax.post("/api/admin/orchestrator/retry-queue/resume-blocked");
      setMsg(`📬 ${r.data.resumed} emailuri repuse în coadă${r.data.tick ? ` — tick imediat: ${r.data.tick.sent} trimise, ${r.data.tick.blocked_config} re-blocate` : ""}.`);
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8" data-testid="orchestrator-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-6">
          <Link to="/admin" className="text-stone-500 hover:text-white flex items-center gap-1 text-sm" data-testid="orch-back-link">
            <ChevronLeft className="w-4 h-4" /> Admin
          </Link>
          <span className="text-stone-700">·</span>
          <Workflow className="w-5 h-5 text-violet-400" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">Autonomy Orchestrator</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">Sprint 1 · Self-Healing</span>
          <div className="flex-1" />
          <Link to="/admin/autonomy" className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="orch-to-autonomy">
            <Gauge className="w-3.5 h-3.5" /> Autonomy Engine
          </Link>
          <button onClick={forceWatchdog} className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="orch-watchdog-tick">
            <HeartPulse className="w-3.5 h-3.5" /> Watchdog
          </button>
          <button onClick={forceReview} className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="orch-decision-review">
            <ClipboardCheck className="w-3.5 h-3.5" /> Review decizii
          </button>
          <button onClick={forceRetryTick} className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="orch-retry-tick">
            <RefreshCcw className="w-3.5 h-3.5" /> Forțează retry tick
          </button>
        </div>

        {msg && (
          <div className="mb-4 px-4 py-2.5 rounded-xl bg-stone-900/60 border border-stone-700 text-sm text-stone-200" data-testid="orch-message">{msg}</div>
        )}

        {loading && !overview ? (
          <div className="p-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-stone-500" /></div>
        ) : overview && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
              <StatCard icon={Zap} label="Acțiuni azi" value={overview.today.actions} accent="text-violet-400" />
              <StatCard icon={Timer} label="Minute salvate azi" value={`~${overview.today.minutes_saved}`} accent="text-emerald-400" />
              <StatCard icon={CheckCircle2} label="Auto-rezolvate azi" value={overview.today.auto_resolved} accent="text-emerald-400" />
              <StatCard icon={ShieldAlert} label="Escaladări azi" value={overview.today.escalated} accent="text-rose-400" />
              <StatCard icon={Clock} label="Minute salvate total" value={`~${overview.total_minutes_saved}`} accent="text-cyan-400" />
            </div>

            {governance?.snapshot && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6" data-testid="governance-snapshot">
                <StatCard icon={Brain} label="Decizii 24h" value={governance.snapshot.decisions_24h} accent="text-violet-400" />
                <StatCard icon={Play} label="Executate 24h" value={governance.snapshot.executed_24h} accent="text-emerald-400" />
                <StatCard icon={AlertTriangle} label="Recomandate 24h" value={governance.snapshot.recommended_24h} accent="text-amber-400" />
                <StatCard icon={HeartPulse} label="Self-healing 7 zile" value={governance.snapshot.self_healing_events_7d} accent="text-cyan-400" />
              </div>
            )}

            <div className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">Playbook-uri active · Autoritate & Încredere</div>
            <div className="grid lg:grid-cols-3 gap-3 mb-8">
              {overview.playbooks.map(pb => (
                <PlaybookCard key={pb.id} pb={pb} gov={govByPlaybook[pb.id]} onToggle={toggle} onSimulate={simulate} onAuthority={setAuthority} simulating={simulating} />
              ))}
            </div>

            {decisions.length > 0 && (
              <>
                <div className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">Decision Memory — ledger append-only</div>
                <div className="border border-stone-800 rounded-2xl bg-stone-900/30 divide-y divide-stone-800/60 mb-8" data-testid="decision-memory-list">
                  {decisions.map(d => (
                    <div key={d.id} className="px-4 py-2.5 flex items-center gap-2 flex-wrap text-xs" data-testid={`decision-${d.id}`}>
                      <span className="font-semibold text-stone-200">{d.playbook_name}</span>
                      {d.test && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-amber-500/15 text-amber-300">TEST</span>}
                      <span className={`px-1.5 py-0.5 rounded border ${(OUTCOME_META[d.decided] || OUTCOME_META.monitored).color}`}>
                        {d.decided === "executed" ? "Executat" : (OUTCOME_META[d.decided]?.label || d.decided)}
                      </span>
                      <span className={`${AUTHORITY_META[d.authority_level]?.color || "text-stone-400"}`}>Nivel {d.authority_level}</span>
                      <span className="text-stone-500">încredere {Math.round((d.confidence || 0) * 100)}%</span>
                      <div className="flex-1" />
                      <span className="text-stone-500">{d.outcome}</span>
                      <span className="text-stone-600">{new Date(d.ts).toLocaleString("ro-RO")}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="flex items-center gap-2 mb-3">
              <div className="text-xs font-bold uppercase tracking-wider text-stone-500">Ledger — ce a făcut orchestratorul</div>
              {overview.retry_pending > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30" data-testid="orch-retry-pending">
                  {overview.retry_pending} retry în coadă
                </span>
              )}
              {overview.retry_blocked_config > 0 && (
                <>
                  <span className="text-[10px] px-2 py-0.5 rounded-lg bg-orange-500/15 text-orange-300 border border-orange-500/30" data-testid="orch-retry-blocked">
                    {overview.retry_blocked_config} emailuri blocate de config
                  </span>
                  <button onClick={resumeBlocked} className="text-[10px] px-2 py-0.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-medium" data-testid="orch-resume-blocked">
                    Reia emailurile blocate
                  </button>
                </>
              )}
            </div>
            {ledger.length === 0 ? (
              <div className="p-10 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="orch-ledger-empty">
                Niciun eveniment încă. Simulează un semnal din cardurile de mai sus pentru a vedea cascada completă.
              </div>
            ) : (
              <div className="space-y-3" data-testid="orch-ledger-list">
                {ledger.map(e => <LedgerEntry key={e.id} e={e} />)}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
