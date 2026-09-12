// SelfDrivingPanel — toggles pentru automatizările Self-Driving (țintă 90%+ autonomie).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Bot, Play, CheckCircle2, Loader2 } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const AUTOMATIONS = [
  { key: "low_risk_autopilot", label: "Low-Risk Autopilot", desc: "Auto-închide TODO-uri rezolvate + auto-aprobă acțiuni low-risk (la 2h)", job: "low_risk_autopilot" },
  { key: "self_healing_smoke", label: "Self-Healing Monitor", desc: "Smoke fail → retry automat + fix-uri din Bug Memory; notifică doar la eșec confirmat", job: null },
  { key: "lead_triage", label: "Lead Triage AI", desc: "Fiecare lead scorat automat (hot/warm/nurture) + raport săptămânal luni 09:00", job: "weekly_lead_report" },
  { key: "auto_materialize_todos", label: "Auto-TODO din recomandări", desc: "Recomandările Autonomy devin TODO-uri automat (zilnic 03:45)", job: "auto_materialize_todos" },
  { key: "stale_request_escalation", label: "Auto-escaladare cereri", desc: "Cereri fără oferte >24h → re-notificare specialiști + boost vizibilitate (la 6h)", job: "stale_request_escalation" },
];

export const SelfDrivingPanel = () => {
  const [settings, setSettings] = useState(null);
  const [running, setRunning] = useState("");
  const [lastResult, setLastResult] = useState(null);

  useEffect(() => {
    ax.get("/api/admin/self-driving/settings").then((r) => setSettings(r.data)).catch(() => {});
  }, []);

  const toggle = async (key) => {
    const next = { ...settings, [key]: !settings[key] };
    setSettings(next);
    try { await ax.put("/api/admin/self-driving/settings", { [key]: next[key] }); } catch { setSettings(settings); }
  };

  const runNow = async (job) => {
    setRunning(job);
    try {
      const r = await ax.post(`/api/admin/self-driving/run/${job}`);
      setLastResult({ job, ...r.data });
    } catch { setLastResult({ job, status: "error" }); } finally { setRunning(""); }
  };

  if (!settings) return null;
  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mb-6" data-testid="self-driving-panel">
      <div className="flex items-center gap-2 mb-1">
        <Bot className="w-5 h-5 text-[#d4ff3a]" />
        <h2 className="text-base font-bold text-white">Self-Driving Automations</h2>
        <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-[#d4ff3a]/15 text-[#d4ff3a] border border-[#d4ff3a]/30">țintă 90%+</span>
      </div>
      <p className="text-xs text-stone-400 mb-4">Platforma execută singură rutinele — tu vezi doar rapoartele. Fiecare rulare e logată în ledger.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {AUTOMATIONS.map((a) => (
          <div key={a.key} className="flex items-center gap-3 rounded-xl bg-white/5 border border-white/10 p-3" data-testid={`sd-item-${a.key}`}>
            <button onClick={() => toggle(a.key)}
              className={`shrink-0 w-10 h-6 rounded-full transition-colors relative ${settings[a.key] ? "bg-[#d4ff3a]" : "bg-stone-700"}`}
              data-testid={`sd-toggle-${a.key}`} aria-label={a.label}>
              <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${settings[a.key] ? "left-[18px]" : "left-0.5"}`} />
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-stone-100">{a.label}</div>
              <div className="text-[10px] text-stone-500 leading-snug">{a.desc}</div>
            </div>
            {a.job && (
              <button onClick={() => runNow(a.job)} disabled={running === a.job}
                className="shrink-0 p-1.5 rounded-lg hover:bg-white/10 text-stone-400 hover:text-white disabled:opacity-40"
                title="Rulează acum" data-testid={`sd-run-${a.job}`}>
                {running === a.job ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              </button>
            )}
          </div>
        ))}
      </div>
      {lastResult && (
        <div className="mt-3 flex items-center gap-2 text-[11px] text-stone-400" data-testid="sd-last-result">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#d4ff3a]" />
          Ultima rulare: <b className="text-stone-200">{lastResult.job}</b> → {lastResult.status || "ok"}
          {typeof lastResult.escalated === "number" && ` · ${lastResult.escalated} escaladate`}
          {typeof lastResult.injected === "number" && ` · ${lastResult.injected} TODO-uri create`}
          {typeof lastResult.todos_auto_closed === "number" && ` · ${lastResult.todos_auto_closed} TODO-uri auto-închise · ${lastResult.approvals_auto_approved} aprobări auto`}
        </div>
      )}
    </div>
  );
};

export default SelfDrivingPanel;
