import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Activity, RefreshCw, Loader2, CheckCircle2, Clock, XCircle,
  UserCheck, GraduationCap, ShieldAlert, ArrowRight, Scale, GitBranch,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

// CE A FĂCUT / AȘTEAPTĂ / A EȘUAT / NECESITĂ OM / A ÎNVĂȚAT
const CATEGORIES = [
  { key: "DID", label: "Ce a făcut", icon: CheckCircle2, cls: "text-emerald-300 border-emerald-500/30 bg-emerald-500/[0.07]" },
  { key: "WAITING", label: "Ce așteaptă", icon: Clock, cls: "text-sky-300 border-sky-500/30 bg-sky-500/[0.07]" },
  { key: "NEEDS_HUMAN", label: "Necesită om", icon: UserCheck, cls: "text-amber-300 border-amber-500/30 bg-amber-500/[0.07]" },
  { key: "FAILED", label: "Ce a eșuat", icon: XCircle, cls: "text-rose-300 border-rose-500/30 bg-rose-500/[0.07]" },
  { key: "BLOCKED", label: "Blocat (guvernanță)", icon: ShieldAlert, cls: "text-orange-300 border-orange-500/30 bg-orange-500/[0.07]" },
  { key: "LEARNED", label: "Ce a învățat", icon: GraduationCap, cls: "text-violet-300 border-violet-500/30 bg-violet-500/[0.07]" },
];

const Stat = ({ label, value, hint, accent }) => (
  <div className="rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5" data-testid={`activity-stat-${label}`}>
    <div className={`text-lg font-bold ${accent || "text-stone-100"}`}>{value ?? "—"}</div>
    <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-0.5">{label}</div>
    {hint && <div className="text-[10px] text-stone-600 mt-0.5">{hint}</div>}
  </div>
);

// FN-021 · Autonomy Activity — vizibilitate + metrici REALE peste infrastructura existentă
export default function AutonomyActivityPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const { data } = await ax.get("/api/admin/autonomy/activity");
      setData(data);
    } catch (e) {
      const s = e?.response?.status;
      setErr(s === 404 ? "Endpoint indisponibil — necesită REDEPLOY la producție." : (e?.response?.data?.detail || "Eroare la încărcarea activității"));
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const m = data?.metrics || {};
  const queue = data?.queue || [];
  const counts = data?.counts || {};
  const byCat = (k) => queue.filter((it) => it.category === k);

  return (
    <div className="mt-6 bg-[#0e0e10] border border-violet-500/25 rounded-3xl p-6" data-testid="activity-panel">
      <div className="flex items-start gap-3 flex-wrap">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-violet-500/15 border border-violet-500/30">
          <Activity className="w-5 h-5 text-violet-300" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-stone-100">Autonomy Activity</h3>
          <p className="text-xs text-stone-400 mt-0.5">
            Ce face autonomia REAL: coadă unică + metrici derivate din ledgere (loop, self-driving, aprobări, knowledge). Fără date sintetice.
          </p>
        </div>
        <button onClick={load} disabled={loading} data-testid="activity-refresh-btn"
          className="pm-btn pm-btn-sm bg-violet-500/15 border border-violet-500/40 text-violet-200 hover:bg-violet-500/25 disabled:opacity-50 inline-flex items-center gap-1.5">
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Reîmprospătează
        </button>
      </div>

      {err && <div className="mt-4 text-xs text-rose-200 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="activity-error">{err}</div>}

      {/* Metrici reale */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2" data-testid="activity-metrics">
        <Stat label="Acțiuni autonome" value={m.autonomous_actions_total} hint={`loop ${m.autonomous_actions_loop ?? 0} · self-driving ${m.self_driving_actions_applied ?? 0}`} accent="text-[#d4ff3a]" />
        <Stat label="Verificate" value={m.autonomous_actions_verified} hint={m.autonomous_resolution_rate_pct != null ? `${m.autonomous_resolution_rate_pct}% rez.` : null} accent="text-emerald-300" />
        <Stat label="Escaladate la om" value={m.human_escalations} hint={m.human_escalation_rate_pct != null ? `${m.human_escalation_rate_pct}% rată` : null} accent="text-amber-300" />
        <Stat label="Eșecuri" value={m.autonomous_failures} accent={m.autonomous_failures ? "text-rose-300" : "text-stone-100"} />
        <Stat label="Reversări" value={m.actions_requiring_reversal} accent={m.actions_requiring_reversal ? "text-rose-300" : "text-stone-100"} />
        <Stat label="Cunoștințe (verificate)" value={m.knowledge_records_from_verified_outcomes} accent="text-violet-300" />
        <Stat label="Recomandări executate" value={m.recommendations_executed} hint={`verif. ${m.recommendations_verified ?? 0} · pending ${m.recommendations_pending ?? 0}`} />
        <Stat label="Blocat guvernanță" value={m.blocked_by_governance} accent={m.blocked_by_governance ? "text-orange-300" : "text-stone-100"} />
        <Stat label="Timp mediu rezolvare" value={m.avg_resolution_time_min != null ? `${m.avg_resolution_time_min}m` : "—"} />
        <Stat label="Rulări loop" value={m.loop_runs} hint={`ultimele ${m.window_days ?? 90}z`} />
      </div>

      {/* Dispute triage summary */}
      {m.disputes && m.disputes.disputes_total_open > 0 && (
        <div className="mt-4 rounded-2xl border border-amber-500/25 bg-amber-500/[0.05] p-4" data-testid="activity-disputes-summary">
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-200">
            <Scale className="w-4 h-4" /> Triaj dispute — {m.disputes.disputes_triaged}/{m.disputes.disputes_total_open} triate
            <span className="ml-auto text-[10px] text-stone-500">rezolvarea rămâne 100% umană</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-1 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200" data-testid="disputes-high">{m.disputes.disputes_high_priority} HIGH</span>
            <span className="px-2 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-200">{m.disputes.disputes_medium_priority} MEDIUM</span>
            <span className="px-2 py-1 rounded-lg bg-stone-500/15 border border-stone-500/30 text-stone-300">{m.disputes.disputes_low_priority} LOW</span>
            <span className="px-2 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-200" data-testid="disputes-ready">{m.disputes.disputes_ready_for_human_decision} gata de decizie</span>
            <span className="px-2 py-1 rounded-lg bg-sky-500/15 border border-sky-500/30 text-sky-200" data-testid="disputes-waiting">{m.disputes.disputes_waiting_information} așteaptă info</span>
            <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-stone-400">confidence mediu {m.disputes.dispute_triage_avg_confidence ?? "—"}</span>
          </div>
        </div>
      )}

      {/* Lifecycle summary */}
      {m.lifecycle && m.lifecycle.lifecycle_actions_total > 0 && (
        <div className="mt-3 rounded-2xl border border-emerald-500/25 bg-emerald-500/[0.05] p-4" data-testid="activity-lifecycle-summary">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-200">
            <GitBranch className="w-4 h-4" /> Lifecycle proiecte (active→on_hold autonom · on_hold→archived cu aprobare)
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-200" data-testid="lifecycle-onhold">{m.lifecycle.lifecycle_on_hold_autonomous} on_hold autonom (verificat)</span>
            <span className="px-2 py-1 rounded-lg bg-violet-500/15 border border-violet-500/30 text-violet-200">{m.lifecycle.lifecycle_archived_after_approval} archived (după aprobare)</span>
            <span className="px-2 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-200">{m.lifecycle.lifecycle_awaiting_human_approval} așteaptă aprobare</span>
            <span className="px-2 py-1 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200" data-testid="lifecycle-blocked">{m.lifecycle.lifecycle_blocked} blocate</span>
          </div>
        </div>
      )}

      {/* Coada de acțiuni grupată */}
      <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-3" data-testid="activity-queue">
        {CATEGORIES.map(({ key, label, icon: Icon, cls }) => {
          const items = byCat(key);
          return (
            <div key={key} className={`rounded-2xl border p-3 ${cls}`} data-testid={`activity-cat-${key}`}>
              <div className="flex items-center gap-2 text-xs font-semibold">
                <Icon className="w-4 h-4" /> {label}
                <span className="ml-auto text-[11px] px-1.5 py-0.5 rounded-full bg-white/10">{counts[key] || 0}</span>
              </div>
              <div className="mt-2 space-y-2">
                {items.length === 0 && <div className="text-[11px] text-stone-500">—</div>}
                {items.map((it, i) => (
                  <div key={i} className="rounded-lg bg-black/20 border border-white/5 px-2.5 py-2" data-testid={`activity-item-${key}-${i}`}>
                    <div className="flex items-center gap-1.5 text-[10px] text-stone-400">
                      <span className="font-mono">{it.source}</span>
                      {it.priority && ["high", "critical"].includes(it.priority) && <span className="px-1 rounded bg-rose-500/20 text-rose-300 font-semibold">{it.priority}</span>}
                      {it.dispute_category && <span className="px-1 rounded bg-white/10 text-stone-300">{it.dispute_category}</span>}
                      {it.confidence != null && <span className="text-stone-500">conf {it.confidence}</span>}
                      {it.count > 1 && <span className="px-1 rounded bg-white/10 text-stone-300">×{it.count}</span>}
                      <span className="ml-auto uppercase tracking-wide">{it.status}</span>
                    </div>
                    <div className="mt-1 text-[11px] text-stone-200 leading-snug">{it.proposed_action}</div>
                    {it.result && <div className="mt-0.5 text-[10px] text-stone-500">{it.result}</div>}
                    {it.escalation_reason && <div className="mt-0.5 text-[10px] text-amber-300/80">⚠ {it.escalation_reason}</div>}
                    <div className="mt-1 flex flex-wrap gap-2 text-[10px]">
                      {it.todo_id && <Link to={`/admin/todo?focus=${it.todo_id}`} className="text-[#d4ff3a] hover:underline inline-flex items-center gap-0.5" data-testid={`activity-item-${key}-${i}-todo`}>Task <ArrowRight className="w-2.5 h-2.5" /></Link>}
                      {it.approval_id && <Link to={`/admin?tab=approvals&focus=${it.approval_id}`} className="text-amber-300 hover:underline inline-flex items-center gap-0.5" data-testid={`activity-item-${key}-${i}-approval`}>Aprobare <ArrowRight className="w-2.5 h-2.5" /></Link>}
                      {it.source === "automation_rule" && <Link to="/admin/automation" className="text-sky-300 hover:underline">Reguli</Link>}
                      {it.source === "audit_anomaly" && <Link to="/admin/audit" className="text-rose-300 hover:underline">Audit</Link>}
                      {it.source === "dispute" && <Link to="/admin?tab=disputes" className="text-amber-300 hover:underline">Vezi disputa</Link>}
                      {it.source === "project_lifecycle" && it.project_id && <Link to={`/projects/${it.project_id}`} className="text-emerald-300 hover:underline">Proiect</Link>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
