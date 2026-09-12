import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { Repeat, Play, Loader2, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STAGES = ["OBSERVE", "DETECT", "FINDING", "DECIDE", "ACT", "VERIFY", "RECORD", "LEARN"];

const CLASS_STYLE = {
  SAFE: "text-emerald-300 border-emerald-500/40 bg-emerald-500/10",
  REVERSIBLE: "text-emerald-300 border-emerald-500/40 bg-emerald-500/10",
  MEDIUM: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  HIGH: "text-rose-300 border-rose-500/40 bg-rose-500/10",
};

// Operational Autonomy Loop (FN-021): Analytics → Finding → Decizie → Acțiune → Verify → Learn
export default function OperationalLoopPanel() {
  const [policy, setPolicy] = useState(null);
  const [lastRun, setLastRun] = useState(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  const loadRuns = async () => {
    try {
      const { data } = await ax.get("/api/admin/autonomy/loop/runs", { params: { limit: 1 } });
      setLastRun((data.items || [])[0] || null);
    } catch { /* noop */ }
  };

  useEffect(() => {
    ax.get("/api/admin/autonomy/loop/policy").then(r => setPolicy(r.data)).catch(() => {});
    loadRuns();
  }, []);

  const runLoop = async () => {
    if (running) return;
    setRunning(true); setErr(null);
    try {
      const { data } = await ax.post("/api/admin/autonomy/loop/run");
      setLastRun(data.run);
    } catch (e) {
      const s = e?.response?.status;
      setErr(s === 404 ? "Endpoint indisponibil — necesită REDEPLOY la producție." : (e?.response?.data?.detail || "Eroare la rularea loop-ului"));
    } finally { setRunning(false); }
  };

  const steps = lastRun?.steps || [];

  return (
    <div className="mt-6 bg-[#0e0e10] border border-violet-500/25 rounded-3xl p-6" data-testid="loop-panel">
      <div className="flex items-start gap-3 flex-wrap">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-violet-500/15 border border-violet-500/30">
          <Repeat className="w-5 h-5 text-violet-300" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-stone-100">Loop Operațional</h3>
          <p className="text-xs text-stone-400 mt-0.5">
            Analytics → Knowledge (findings) → Decizie → Acțiune → Verify → Learn. Reutilizează admin_ai_findings, admin_todos, admin_approvals.
          </p>
        </div>
        <button onClick={runLoop} disabled={running} data-testid="loop-run-btn"
          className="pm-btn pm-btn-sm bg-violet-500/15 border border-violet-500/40 text-violet-200 hover:bg-violet-500/25 disabled:opacity-50 inline-flex items-center gap-1.5">
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Rulează…" : "Rulează loop"}
        </button>
      </div>

      {/* Stages */}
      <div className="mt-4 flex flex-wrap items-center gap-1.5" data-testid="loop-stages">
        {STAGES.map((s, i) => (
          <React.Fragment key={s}>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md bg-white/5 border border-white/10 text-stone-300">{s}</span>
            {i < STAGES.length - 1 && <ArrowRight className="w-3 h-3 text-stone-600" />}
          </React.Fragment>
        ))}
      </div>

      {err && (
        <div className="mt-4 text-xs text-rose-200 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="loop-error">{err}</div>
      )}

      {/* Last run summary */}
      {lastRun && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid="loop-run-result">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className={`px-2 py-0.5 rounded-full border ${lastRun.outcome === "applied" ? "text-emerald-300 border-emerald-500/40 bg-emerald-500/10" : "text-stone-300 border-stone-600 bg-stone-500/10"}`}>
              {lastRun.outcome === "applied" ? "APLICAT" : "FĂRĂ SCHIMBĂRI"}
            </span>
            <span className="text-stone-400">observații: <b className="text-stone-200">{lastRun.observations}</b></span>
            <span className="text-stone-400">findings noi: <b className="text-stone-200">{lastRun.findings_created}</b></span>
            <span className="text-stone-400">task-uri: <b className="text-stone-200">{lastRun.actions_taken?.todo ?? 0}</b></span>
            <span className="text-stone-400">aprobări: <b className="text-stone-200">{lastRun.actions_taken?.approval ?? 0}</b></span>
            <span className="text-stone-400">învățat (rezolvate): <b className="text-stone-200">{lastRun.learned?.auto_resolved ?? 0}</b></span>
            <span className="ml-auto text-[10px] text-stone-500">{lastRun.started_at ? new Date(lastRun.started_at).toLocaleString("ro-RO") : ""}</span>
          </div>

          {steps.length === 0 && (
            <div className="mt-3 text-xs text-emerald-300 inline-flex items-center gap-1.5" data-testid="loop-no-signal">
              <CheckCircle2 className="w-3.5 h-3.5" /> Nicio fricțiune peste prag — sistemul e sănătos.
            </div>
          )}

          <div className="mt-3 space-y-2">
            {steps.map((st, i) => (
              <div key={i} className="rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid={`loop-step-${i}`}>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono text-stone-300">{st.detector}</span>
                  <span className="text-stone-500">·</span>
                  <span className="font-mono text-violet-300">{st.route}</span>
                  {st.action_class && <span className={`px-2 py-0.5 rounded-full border text-[10px] ${CLASS_STYLE[st.action?.type === "approval" ? "MEDIUM" : "SAFE"]}`}>{st.decision}</span>}
                  {st.decision && !st.action_class && <span className={`px-2 py-0.5 rounded-full border text-[10px] ${st.human_gate ? CLASS_STYLE.MEDIUM : CLASS_STYLE.SAFE}`}>{st.decision}</span>}
                  {st.verify?.ok ? (
                    <span className="ml-auto text-[10px] text-emerald-300 inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> verificat</span>
                  ) : (
                    <span className="ml-auto text-[10px] text-rose-300 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {st.error ? "eroare" : "neverificat"}</span>
                  )}
                </div>
                {st.hypothesis && <div className="mt-1.5 text-[11px] text-stone-400"><span className="text-stone-500">Ipoteză:</span> {st.hypothesis}</div>}
                <div className="mt-1.5 flex flex-wrap gap-3 text-[11px]">
                  {st.action?.type === "todo" && st.action?.todo_id && <Link to={`/admin/todo?focus=${st.action.todo_id}`} className="text-[#d4ff3a] hover:underline" data-testid={`loop-step-${i}-todo`}>→ Vezi task-ul</Link>}
                  {st.action?.type === "approval" && st.action?.approval_id && <Link to={`/admin?tab=approvals&focus=${st.action.approval_id}`} className="text-amber-300 hover:underline" data-testid={`loop-step-${i}-approval`}>→ Aprobare (gate uman)</Link>}
                  {st.action?.type === "blocked_governance" && <span className="text-amber-300" data-testid={`loop-step-${i}-blocked`}>⛔ Blocat de guvernanță (autopilot OFF)</span>}
                  <span className="text-stone-600">actor: {st.actor}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Policy */}
      {policy && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid="loop-policy">
          <div className="text-xs font-semibold text-stone-200 flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5 text-amber-400" /> Politică de acțiune (risc)</div>
          <div className="mt-2 grid gap-1.5 text-[11px] text-stone-400">
            <div><span className="text-emerald-300 font-semibold">SAFE/REVERSIBLE</span> → auto-execuție (task admin_todos, reversibil).</div>
            <div><span className="text-amber-300 font-semibold">MEDIUM/HIGH</span> → doar propunere, aprobare umană obligatorie (admin_approvals).</div>
            <div className="text-stone-500">Praguri: bounce ≥ {policy.thresholds?.bounce_min_pct}% pe ≥ {policy.thresholds?.bounce_min_sessions} sesiuni · conversie cerere &lt; {policy.thresholds?.funnel_max_conversion_pct}% pe ≥ {policy.thresholds?.funnel_min_started} începute · idempotent {policy.thresholds?.dedup_window_hours}h.</div>
          </div>
        </div>
      )}
    </div>
  );
}
