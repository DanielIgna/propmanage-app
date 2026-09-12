// ProductionReadiness — AIB-010 · Certification & Production Readiness (tab în /admin/ai-brain).
// Release Certificate: verdict, scoruri Guardian, health, stress, pilot readiness, probleme.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  ShieldCheck, Loader2, PlayCircle, Activity, AlertTriangle, AlertOctagon,
  CheckCircle2, FlaskConical, Gauge, Building2, Wrench,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const VERDICT_STYLE = {
  "Ready for Production": "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  "Production Ready with Warnings": "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40",
  "Ready for Pilot": "bg-amber-500/10 text-amber-300 border-amber-500/40",
  "Not Ready": "bg-rose-500/15 text-rose-300 border-rose-500/40",
};

const ScoreRing = ({ label, value }) => (
  <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3 text-center" data-testid={`pr-score-${label}`}>
    <div className={`text-2xl font-black ${value >= 90 ? "text-emerald-300" : value >= 70 ? "text-[#d4ff3a]" : "text-rose-300"}`}>{value}</div>
    <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-0.5">{label}</div>
  </div>
);

export const ProductionReadiness = () => {
  const [cert, setCert] = useState(null);
  const [debt, setDebt] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    ax.get("/api/admin/ai-brain/certification/latest").then(r => setCert(r.data)).catch(() => {});
  }, []);

  const run = async () => {
    setBusy(true);
    try {
      const { data } = await ax.post("/api/admin/ai-brain/certification/run", {}, { timeout: 180000 });
      setCert(data);
    } finally { setBusy(false); }
  };

  const loadDebt = () => ax.get("/api/admin/ai-brain/certification/debt").then(r => setDebt(r.data)).catch(() => {});

  const s = cert?.scores;
  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="production-readiness">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <ShieldCheck className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Production Readiness — AIB-010 · Certification</div>
        <div className="flex-1" />
        <button onClick={run} disabled={busy}
          className="px-3 py-1.5 text-[11px] rounded-lg bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="pr-run-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <PlayCircle className="w-3 h-3" />}
          {busy ? "Certificare în curs (~15s)…" : "Rulează certificarea"}
        </button>
      </div>

      {!cert ? (
        <div className="text-xs text-stone-500">Nicio certificare încă — apasă «Rulează certificarea» pentru primul Release Certificate.</div>
      ) : (
        <div className="space-y-4">
          <div className={`rounded-2xl border p-4 flex items-center gap-4 ${VERDICT_STYLE[cert.verdict] || VERDICT_STYLE["Not Ready"]}`} data-testid="pr-verdict">
            <ShieldCheck className="w-8 h-8 shrink-0" />
            <div className="flex-1">
              <div className="text-lg font-black">{cert.verdict}</div>
              <div className="text-[11px] opacity-80">
                AI Brain v{cert.version} · certificat {new Date(cert.generated_at).toLocaleString("ro-RO")} · {cert.certified_components.length}/9 componente certificate · audit {Math.round(cert.duration_ms / 1000)}s
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <ScoreRing label="AI Brain" value={s.ai_brain_score} />
            <ScoreRing label="Reliability" value={s.reliability_score} />
            <ScoreRing label="Explainability" value={s.explainability_score} />
            <ScoreRing label="Stability" value={s.stability_score} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="pr-components">
              <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-300" /> Componente auditate
              </div>
              <div className="space-y-1 max-h-52 overflow-auto">
                {cert.components.map(c => (
                  <div key={c.id} className="flex items-center gap-2 text-[11px]">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${c.status === "certified" ? "bg-emerald-400" : c.status === "experimental" ? "bg-amber-400" : "bg-rose-400"}`} />
                    <span className="font-bold text-white">{c.id}</span>
                    <span className="text-stone-400 flex-1 truncate">{c.name}</span>
                    <span className="text-stone-600">{c.passed}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="pr-health">
              <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1">
                <Activity className="w-3 h-3 text-sky-300" /> Health & performanță
              </div>
              <div className="space-y-1 text-[11px] text-stone-300 max-h-52 overflow-auto">
                {Object.entries(cert.health.latencies_ms).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-stone-400">{k}</span>
                    <span className={v > 2000 && k !== "llm_roundtrip" ? "text-rose-300" : "text-white font-bold"}>{v}ms</span>
                  </div>
                ))}
                <div className="flex justify-between"><span className="text-stone-400">memorie backend</span><span className="text-white font-bold">{cert.health.memory_mb}MB</span></div>
                <div className="flex justify-between"><span className="text-stone-400">CPU load 1m</span><span className="text-white font-bold">{cert.health.cpu_load_1m}</span></div>
                <div className="flex justify-between"><span className="text-stone-400">erori recente în loguri</span><span>{cert.health.recent_log_errors}</span></div>
              </div>
            </div>

            <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="pr-stress">
              <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1">
                <FlaskConical className="w-3 h-3 text-violet-300" /> Stress & Load (concurent)
              </div>
              <div className="space-y-1 text-[11px] text-stone-300">
                <div className="flex justify-between"><span className="text-stone-400">operațiuni concurente</span><span className="text-white font-bold">{cert.stress.concurrent_operations}</span></div>
                <div className="flex justify-between"><span className="text-stone-400">timp total</span><span className="text-white font-bold">{cert.stress.total_ms}ms</span></div>
                <div className="flex justify-between"><span className="text-stone-400">medie / operațiune</span><span className="text-white font-bold">{cert.stress.avg_ms_per_op}ms</span></div>
                <div className="flex justify-between"><span className="text-stone-400">erori</span><span className={cert.stress.error_count ? "text-rose-300 font-bold" : "text-emerald-300 font-bold"}>{cert.stress.error_count}</span></div>
                <div className="text-[10px] text-stone-500 mt-1">
                  {Object.entries(cert.stress.breakdown || {}).map(([k, v]) => `${k}×${v}`).join(" · ")}
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-stone-800">
                <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1 flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-[#d4ff3a]" /> Pilot Readiness
                </div>
                {cert.pilot_readiness.map(p => (
                  <div key={p.level} className="flex items-center gap-2 text-[11px]" data-testid={`pr-pilot-${p.level}`}>
                    <span className={`w-2 h-2 rounded-full shrink-0 ${p.verdict === "ready" ? "bg-emerald-400" : p.verdict === "ready_with_warnings" ? "bg-amber-400" : "bg-rose-400"}`} />
                    <span className="text-stone-300 flex-1">{p.level.replace(/_/g, " ")}</span>
                    <span className="text-stone-500">{p.verdict === "ready" ? "pregătit" : p.verdict === "ready_with_warnings" ? "cu avertismente" : "nepregătit"}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {(cert.critical_issues.length > 0 || cert.minor_issues.length > 0 || cert.recommendations.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3" data-testid="pr-critical">
                <div className="text-[10px] font-black uppercase text-rose-300 mb-1.5 flex items-center gap-1"><AlertOctagon className="w-3 h-3" /> Critice ({cert.critical_issues.length})</div>
                {cert.critical_issues.map((i, k) => <div key={k} className="text-[11px] text-rose-200/90">• {i}</div>)}
                {!cert.critical_issues.length && <div className="text-[11px] text-stone-500">Nicio problemă critică.</div>}
              </div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3" data-testid="pr-minor">
                <div className="text-[10px] font-black uppercase text-amber-300 mb-1.5 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Minore ({cert.minor_issues.length})</div>
                {cert.minor_issues.map((i, k) => <div key={k} className="text-[11px] text-amber-200/90">• {i}</div>)}
              </div>
              <div className="rounded-xl border border-stone-800 bg-stone-900/40 p-3" data-testid="pr-recommendations">
                <div className="text-[10px] font-black uppercase text-stone-400 mb-1.5 flex items-center gap-1"><Gauge className="w-3 h-3" /> Recomandări</div>
                {cert.recommendations.map((i, k) => <div key={k} className="text-[11px] text-stone-300">• {i}</div>)}
              </div>
            </div>
          )}

          <div>
            <button onClick={loadDebt} className="text-[11px] font-bold text-stone-400 hover:text-white flex items-center gap-1.5" data-testid="pr-debt-btn">
              <Wrench className="w-3 h-3" /> {debt ? "Technical Debt Scanner" : "Deschide Technical Debt Scanner →"}
            </button>
            {debt && (
              <div className="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-2 text-[11px]" data-testid="pr-debt">
                <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3 max-h-44 overflow-auto">
                  <div className="text-[10px] uppercase text-stone-500 mb-1">Module API fără apeluri frontend (candidate)</div>
                  {(debt.unused_api_module_candidates || []).map((u, i) => (
                    <div key={i} className="text-stone-400"><b className="text-stone-300">{u.module}</b> — {u.example}</div>
                  ))}
                </div>
                <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3 max-h-44 overflow-auto">
                  <div className="text-[10px] uppercase text-stone-500 mb-1">Stări de proces posibil inutile · procese abandonate</div>
                  {(debt.possibly_unused_process_states || []).map((u, i) => (
                    <div key={i} className="text-stone-400">∅ {u.process}: «{u.state}»</div>
                  ))}
                  {(debt.abandoned_processes || []).map((a, i) => (
                    <div key={i} className="text-rose-300/80">▼ {a.process}: {a.stale}/{a.total} stagnate</div>
                  ))}
                  <div className="text-stone-600 mt-1">{debt.note}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
