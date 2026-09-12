// AdaptiveExplorer — AIB-008 · Adaptive Intelligence Engine (tab în /admin/ai-brain).
// Comportamente observate, feedback pe recomandări, blocaje, recalibrări, încrederea AI.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BrainCog, Loader2, ScanEye, ThumbsUp, ThumbsDown, Gauge, Users, TrendingDown, Sparkles,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const Stat = ({ label, value, tone = "" }) => (
  <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3 text-center">
    <div className={`text-xl font-black ${tone || "text-white"}`}>{value ?? "—"}</div>
    <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-0.5">{label}</div>
  </div>
);

export const AdaptiveExplorer = () => {
  const [ov, setOv] = useState(null);
  const [roles, setRoles] = useState([]);
  const [proc, setProc] = useState(null);
  const [email, setEmail] = useState("client@propmanage.io");
  const [profile, setProfile] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    ax.get("/api/admin/ai-brain/adaptive/overview").then(r => setOv(r.data)).catch(() => {});
    ax.get("/api/admin/ai-brain/adaptive/roles").then(r => setRoles(r.data.items)).catch(() => {});
    ax.get("/api/admin/ai-brain/adaptive/processes").then(r => setProc(r.data)).catch(() => {});
  }, []);

  const inspect = async (e) => {
    e?.preventDefault(); setBusy(true);
    try {
      const { data } = await ax.get("/api/admin/ai-brain/adaptive/behavior", { params: { email } });
      setProfile(data);
    } catch (ex) { setProfile({ error: ex?.response?.data?.detail || ex.message }); }
    finally { setBusy(false); }
  };

  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="adaptive-explorer">
      <div className="flex items-center gap-2 mb-3">
        <BrainCog className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Adaptive Intelligence — AIB-008 · Learning Without Machine Learning</div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4" data-testid="ai-adaptive-stats">
        <Stat label="Recomandări urmate" value={ov?.followed} tone="text-emerald-300" />
        <Stat label="Recomandări ignorate" value={ov?.ignored} tone="text-rose-300" />
        <Stat label="Încredere medie AI" value={ov?.avg_confidence != null ? `${ov.avg_confidence}%` : "—"} tone="text-[#d4ff3a]" />
        <Stat label="Decizii urmărite" value={ov?.decisions_tracked} />
      </div>

      {(ov?.recalibrations || []).length > 0 && (
        <div className="mb-4" data-testid="ai-recalibrations">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
            <Gauge className="w-3 h-3 text-[#d4ff3a]" /> Reguli recalibrate din feedback real
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ov.recalibrations.map(r => (
              <span key={r.kind} className={`text-[10px] font-bold px-2 py-1 rounded-lg border ${r.score_adjustment > 0 ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/25" : "bg-rose-500/10 text-rose-300 border-rose-500/25"}`}>
                {r.kind}: {r.score_adjustment > 0 ? "+" : ""}{r.score_adjustment}p ({Math.round(r.acceptance * 100)}% urmate, n={r.n})
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-4">
        <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="ai-role-profiles">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1">
            <Users className="w-3 h-3 text-[#d4ff3a]" /> Role Learning — comportament pe roluri
          </div>
          <div className="space-y-1.5 max-h-48 overflow-auto">
            {roles.map(r => (
              <div key={r.role} className="text-[11px] text-stone-300 flex items-center gap-2">
                <span className="font-bold text-white w-24 shrink-0">{r.role}</span>
                <span className="text-stone-500">{r.users} utilizatori</span>
                <span className="flex-1 truncate text-stone-400">
                  {(r.top_modules || []).slice(0, 3).map(m => m.module).join(" · ") || "fără navigație încă"}
                </span>
                {r.acceptance_rate != null && (
                  <span className={r.acceptance_rate >= 0.5 ? "text-emerald-300" : "text-rose-300"}>
                    {Math.round(r.acceptance_rate * 100)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="ai-process-learning">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1">
            <TrendingDown className="w-3 h-3 text-amber-400" /> Process Learning — blocaje & optimizări
          </div>
          <div className="space-y-1 max-h-48 overflow-auto text-[11px]">
            {(proc?.bottlenecks || []).slice(0, 4).map((b, i) => (
              <div key={i} className="text-stone-300">🔸 <b>{b.process}</b> — blocaj în «{b.state}» ({b.stuck} instanțe)</div>
            ))}
            {(proc?.degradations || []).map((d, i) => (
              <div key={i} className="text-rose-300">▼ {d.process_id}: stagnare {Math.round(d.stale_ratio_before * 100)}% → {Math.round(d.stale_ratio_now * 100)}%</div>
            ))}
            {(proc?.efficient_processes || []).slice(0, 3).map((p, i) => (
              <div key={i} className="text-emerald-300">✓ {p.process} — eficient ({Math.round(p.ratio * 100)}% stagnare)</div>
            ))}
            {(proc?.possibly_unused_states || []).slice(0, 3).map((u, i) => (
              <div key={i} className="text-stone-500">∅ {u.process}: starea «{u.state}» — {u.note}</div>
            ))}
          </div>
        </div>
      </div>

      <form onSubmit={inspect} className="flex gap-2 mb-3">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email utilizator"
          className="flex-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="ai-behavior-email" />
        <button disabled={busy} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="ai-behavior-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ScanEye className="w-3.5 h-3.5" />} Profil comportamental
        </button>
      </form>
      {profile && !profile.error && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 text-[11px]" data-testid="ai-behavior-profile">
          <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500 mb-1">Module frecvente</div>
            {(profile.top_modules || []).map(m => (
              <div key={m.module} className="text-stone-300">{m.module} — {m.visits} vizite · {Math.round((m.time_ms || 0) / 60000)}min</div>
            ))}
            {profile.usual_start_module && <div className="text-[#d4ff3a] mt-1 flex items-center gap-1"><Sparkles className="w-3 h-3" /> începe de obicei cu «{profile.usual_start_module}»</div>}
          </div>
          <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500 mb-1">Feedback pe recomandări</div>
            <div className="flex items-center gap-3">
              <span className="text-emerald-300 flex items-center gap-1"><ThumbsUp className="w-3 h-3" /> {profile.followed} urmate</span>
              <span className="text-rose-300 flex items-center gap-1"><ThumbsDown className="w-3 h-3" /> {profile.ignored} ignorate</span>
            </div>
            {(profile.persistent_recommendations || []).map((p, i) => (
              <div key={i} className="text-stone-500 mt-1">↻ «{p.title}» văzută de {p.seen_count} ori fără acțiune</div>
            ))}
          </div>
          <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500 mb-1">Fluxuri obișnuite</div>
            {(profile.common_flows || []).map((f, i) => (
              <div key={i} className="text-stone-300">{f.from} → {f.to} <span className="text-stone-600">×{f.count}</span></div>
            ))}
            {!(profile.common_flows || []).length && <div className="text-stone-600">Prea puțină navigație încă.</div>}
          </div>
        </div>
      )}
      {profile?.error && <div className="text-xs text-rose-300" data-testid="ai-behavior-error">{profile.error}</div>}
    </div>
  );
};
