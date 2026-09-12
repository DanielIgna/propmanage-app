// SH-001 · Drumul Casei Tale — stepper L1→L7 + House Readiness, sub Copilotul Casei.
// Totul calculat din date reale (GET /api/journey/house). Explicabil, expandabil, cu CTA.
import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { Map, Check, ChevronDown, ChevronRight, CircleDashed, Circle, Gauge, ShieldCheck } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const GREEN = "#166534";

const StepIcon = ({ status }) => {
  if (status === "done") return <span className="w-6 h-6 rounded-full bg-[#34C759] flex items-center justify-center shrink-0"><Check className="w-3.5 h-3.5 text-white" /></span>;
  if (status === "in_progress") return <span className="w-6 h-6 rounded-full border-2 border-amber-400 bg-amber-50 flex items-center justify-center shrink-0"><CircleDashed className="w-3.5 h-3.5 text-amber-500" /></span>;
  return <span className="w-6 h-6 rounded-full border-2 border-slate-200 bg-white flex items-center justify-center shrink-0"><Circle className="w-3 h-3 text-slate-300" /></span>;
};

const statusLabel = { done: "Gata", in_progress: "În lucru", missing: "Lipsește" };
const statusCls = {
  done: "bg-emerald-50 text-emerald-700",
  in_progress: "bg-amber-50 text-amber-600",
  missing: "bg-slate-100 text-slate-400",
};

export const HouseJourneyCard = ({ go }) => {
  const [j, setJ] = useState(null);
  const [openLevel, setOpenLevel] = useState(null);
  const [showReadiness, setShowReadiness] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    axios.get(`${API}/api/journey/house`).then(r => setJ(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    load();
    window.addEventListener("propmanage:doc-uploaded", load);
    return () => window.removeEventListener("propmanage:doc-uploaded", load);
  }, [load]);

  const run = (p) => {
    if (!p) return;
    if (["property", "benefits", "request", "maintenance", "dna", "assets"].includes(p) || p.startsWith("upload:")) go?.("property");
    else if (p.startsWith("/")) navigate(p);
  };

  if (!j) return null;
  const r = j.readiness;

  return (
    <div className="mx-5 mt-3 lg:mx-0 lg:mt-4 cv2-fade" data-testid="journey-widget">
      <div className="rounded-3xl border border-slate-100 bg-white shadow-sm p-4 lg:p-5">
        <div className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-2xl bg-slate-100 flex items-center justify-center shrink-0">
            <Map className="w-4 h-4" style={{ color: GREEN }} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900 leading-none">Drumul Casei Tale</div>
            <div className="text-[10px] text-slate-400 mt-0.5" data-testid="journey-current-level">
              Nivel {j.current_level}/7 · {j.current_label}
            </div>
          </div>
          <button onClick={() => setShowReadiness(v => !v)} data-testid="journey-readiness-toggle"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-slate-50 border border-slate-100 active:scale-[0.97]">
            <Gauge className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs font-black text-slate-700" data-testid="journey-readiness-score">{r?.score ?? 0}</span>
            <span className="text-[9px] text-slate-400">Readiness</span>
          </button>
        </div>

        {showReadiness && r && (
          <div className="mt-3 rounded-2xl bg-slate-50 p-3" data-testid="journey-readiness-panel">
            <div className="text-[10px] text-slate-500 leading-snug mb-2">{r.note}</div>
            {r.dimensions.map(d => (
              <div key={d.key} className="py-1.5" data-testid={`journey-readiness-${d.key}`}>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold text-slate-600 flex-1">{d.label}</span>
                  <span className="text-[10px] font-black text-slate-500">{d.pct}%</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-slate-200/70 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${d.pct}%`, background: d.pct >= 75 ? "#34C759" : d.pct >= 40 ? "#f59e0b" : "#cbd5e1" }} />
                </div>
                {d.missing.length > 0 && (
                  <div className="mt-1 text-[9px] text-slate-400">Lipsește: {d.missing.map(m => m.label).join(" · ")}</div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 relative">
          {j.levels.map((L, idx) => (
            <div key={L.key} className="relative flex gap-3" data-testid={`journey-step-${L.key}`}>
              {idx < j.levels.length - 1 && (
                <span className={`absolute left-3 top-6 bottom-0 w-0.5 -translate-x-1/2 ${L.status === "done" ? "bg-[#34C759]/40" : "bg-slate-100"}`} />
              )}
              <StepIcon status={L.status} />
              <div className="flex-1 min-w-0 pb-3.5">
                <button onClick={() => setOpenLevel(openLevel === L.level ? null : L.level)}
                  className="w-full flex items-center gap-2 text-left" data-testid={`journey-step-toggle-${L.key}`}>
                  <span className={`text-xs font-black flex-1 ${L.status === "done" ? "text-slate-400" : "text-slate-800"}`}>{L.label}</span>
                  <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full ${statusCls[L.status]}`}>{statusLabel[L.status]}</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-300 transition-transform ${openLevel === L.level ? "rotate-180" : ""}`} />
                </button>
                {openLevel === L.level && (
                  <div className="mt-2 rounded-xl bg-slate-50 p-2.5 space-y-1.5" data-testid={`journey-step-detail-${L.key}`}>
                    {L.requirements.map((req, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className={`mt-0.5 w-3.5 h-3.5 rounded-full flex items-center justify-center shrink-0 ${req.done ? "bg-[#34C759]" : "border border-slate-300"}`}>
                          {req.done && <Check className="w-2 h-2 text-white" />}
                        </span>
                        <span className={`text-[11px] leading-snug ${req.done ? "text-slate-400" : "text-slate-600 font-bold"}`}>{req.label}</span>
                      </div>
                    ))}
                    {L.note && (
                      <div className="flex items-start gap-1.5 pt-1 text-[9px] text-slate-400 leading-snug">
                        <ShieldCheck className="w-3 h-3 shrink-0 mt-0.5" />{L.note}
                      </div>
                    )}
                    {L.status !== "done" && (
                      <button onClick={() => run(L.requirements.find(rq => !rq.done)?.cta || L.cta)}
                        data-testid={`journey-step-cta-${L.key}`}
                        className="mt-1 w-full py-2 rounded-full text-[11px] font-black text-black flex items-center justify-center gap-1"
                        style={{ background: "#ccff00" }}>
                        Continuă acest pas <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {j.next_level && (
          <div className="mt-1 rounded-2xl border border-[#166534]/15 bg-[#F0FBF4] p-3" data-testid="journey-next-hint">
            <span className="text-[10px] font-black uppercase tracking-wider text-[#166534]">Următorul nivel</span>
            <div className="text-xs font-bold text-slate-800 mt-0.5">{j.next_level.label}</div>
            {j.next_level.missing?.[0] && (
              <div className="text-[10px] text-slate-500 mt-0.5">Îți lipsește: {j.next_level.missing.map(m => m.label).join(" · ")}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default HouseJourneyCard;
