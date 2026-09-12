// MentorWidget — AIB-004 · AI Mentor. Widget reutilizabil în orice modul.
// <MentorWidget path="/client" />            → recomandări + tips + ghid onboarding
// <SmartEmptyState resource="properties" />  → empty state inteligent (de ce + pasul următor)
import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Compass, Lightbulb, ArrowRight, Loader2, RotateCcw, Sparkles, Users } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const jget = (url) => fetch(`${API}${url}`, { credentials: "include" })
  .then(async r => { if (!r.ok) throw new Error(r.status); return r.json(); });
const jpost = (url, body) => fetch(`${API}${url}`, {
  method: "POST", credentials: "include",
  headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
}).then(async r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const MentorActions = ({ actions, onNavigate, focus }) => {
  const navigate = useNavigate();
  const [hidden, setHidden] = useState([]);
  const refs = useRef({});
  // Deep-link: potrivește recomandarea relevantă contextului (Copilot → „Vezi alte recomandări").
  const matchId = useMemo(() => {
    if (!focus || !actions?.length) return null;
    const fp = String(focus.focus_path || "").toLowerCase();
    const ft = String(focus.focus_title || "").toLowerCase();
    const fi = String(focus.focus_id || "").toLowerCase();
    const m = actions.find(a =>
      (fi && String(a.id || "").toLowerCase() === fi)
      || (fp && String(a.cta_path || "").toLowerCase().includes(fp))
      || (ft && String(a.title || "").toLowerCase().includes(ft)));
    return m?.id || null;
  }, [focus, actions]);
  useEffect(() => {
    if (matchId && refs.current[matchId]) {
      try { refs.current[matchId].scrollIntoView({ block: "center", behavior: "smooth" }); } catch { /* noop */ }
    }
  }, [matchId]);
  if (!actions?.length) return null;
  const sendFeedback = (id, action) => {
    jpost("/api/ai-brain/decisions/feedback", { decision_id: id, action }).catch(() => {});
  };
  const visible = actions.filter(a => !hidden.includes(a.id));
  if (!visible.length) return null;
  return (
    <div className="space-y-2" data-testid="mentor-actions">
      {visible.map(a => (
        <div key={a.id} ref={el => { refs.current[a.id] = el; }} className="flex items-stretch gap-1">
          <button onClick={() => { sendFeedback(a.id, "accepted"); (onNavigate || navigate)(a.cta_path); }}
            className={`flex-1 text-left flex items-start gap-3 rounded-2xl border bg-stone-900/40 p-3 transition-colors group ${a.id === matchId ? "border-[#d4ff3a] ring-1 ring-[#d4ff3a]/60 bg-[#d4ff3a]/5" : "border-stone-800 hover:border-[#d4ff3a]/50"}`}
            data-testid={`mentor-action-${a.id}`}>
            <span className="mt-0.5 w-6 h-6 rounded-lg bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center shrink-0">
              <ArrowRight className="w-3 h-3 text-[#d4ff3a] group-hover:translate-x-0.5 transition-transform" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13px] font-bold text-white">{a.title}</span>
              <span className="block text-[11px] text-stone-400 mt-0.5">{a.reason}</span>
            </span>
            {a.score != null && (
              <span className="flex flex-col items-end gap-0.5 shrink-0">
                <span className="text-[10px] font-black px-1.5 py-0.5 rounded bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/25"
                  data-testid={`mentor-action-score-${a.id}`}>{a.score}</span>
                {a.confidence != null && (
                  <span className="text-[9px] text-stone-500" data-testid={`mentor-action-confidence-${a.id}`}>
                    încredere {a.confidence}%
                  </span>
                )}
              </span>
            )}
          </button>
          {a.score != null && (
            <button onClick={() => { sendFeedback(a.id, "dismissed"); setHidden(h => [...h, a.id]); }}
              title="Nu e relevant pentru mine"
              className="px-1.5 rounded-xl text-stone-600 hover:text-rose-300 hover:bg-rose-500/10 text-xs"
              data-testid={`mentor-action-dismiss-${a.id}`}>✕</button>
          )}
        </div>
      ))}
    </div>
  );
};

export const MentorTips = ({ tips }) => {
  if (!tips?.length) return null;
  return (
    <div className="space-y-1.5" data-testid="mentor-tips">
      {tips.map((t, i) => (
        <div key={i} className="flex items-start gap-2 text-[11px] text-amber-200/90 bg-amber-500/10 border border-amber-500/25 rounded-xl px-3 py-2">
          <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-300" /> {t.text}
        </div>
      ))}
    </div>
  );
};

export const MentorWidget = ({ path, onNavigate, autoGuide = false, focus = null }) => {
  const location = useLocation();
  const p = path || location.pathname;
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async (replay = false) => {
    setBusy(true);
    try {
      const d = await jget(`/api/ai-brain/mentor?path=${encodeURIComponent(p)}&replay=${replay}&include_guide=${autoGuide || replay}`);
      setData(d);
    } catch { setData(null); } finally { setBusy(false); }
  }, [p, autoGuide]);
  useEffect(() => { load(); }, [load]);

  if (busy) return (
    <div className="flex items-center gap-2 text-xs text-stone-400 py-3" data-testid="mentor-loading">
      <Loader2 className="w-4 h-4 animate-spin text-[#d4ff3a]" /> Mentorul analizează unde te afli…
    </div>
  );
  if (!data) return null;
  return (
    <div className="space-y-4" data-testid="mentor-widget">
      <MentorTips tips={data.tips} />
      {(data.insights || []).length > 0 && (
        <div className="space-y-1.5" data-testid="mentor-insights">
          {data.insights.map((ins, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px] text-violet-200/90 bg-violet-500/10 border border-violet-500/25 rounded-xl px-3 py-2"
              data-testid={`mentor-insight-${ins.kind}`}>
              <Sparkles className="w-3.5 h-3.5 mt-0.5 shrink-0 text-violet-300" /> {ins.text}
            </div>
          ))}
        </div>
      )}
      {data.collaboration && (
        <div className={`flex items-start gap-2 text-[11px] rounded-xl px-3 py-2 border ${
          data.collaboration.you_act
            ? "text-[#d4ff3a] bg-[#d4ff3a]/5 border-[#d4ff3a]/25"
            : data.collaboration.delayed
              ? "text-rose-300 bg-rose-500/10 border-rose-500/25"
              : "text-stone-300 bg-stone-900/50 border-stone-800"}`}
          data-testid="mentor-collaboration">
          <Users className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>
            {data.collaboration.message}
            {data.collaboration.sla?.ratio > 0.7 && !data.collaboration.you_act && (
              <span className="block text-[10px] text-stone-500 mt-0.5">
                ⏱ {Math.round(data.collaboration.sla.hours_in_stage)}h în etapă · SLA ~{Math.round(data.collaboration.sla.sla_hours)}h
              </span>
            )}
          </span>
        </div>
      )}
      {data.process && (
        <div className="rounded-2xl border border-sky-500/25 bg-sky-500/5 p-3" data-testid="mentor-process">
          <div className="text-[10px] font-black uppercase tracking-wider text-sky-300 mb-1.5">
            Procesul tău activ · {data.process.name}
          </div>
          {data.process.current_state ? (
            <div className="text-[12px] text-stone-200" data-testid="mentor-process-state">
              Etapa <b className="text-white">{data.process.current_state}</b> ({(data.process.step_index ?? 0) + 1}/{data.process.total_steps})
              {data.process.next?.length > 0 && <> · urmează <b className="text-sky-200">{data.process.next[0]}</b></>}
              {data.process.who_acts?.length > 0 && (
                <span className="block text-[11px] text-stone-400 mt-0.5">Acționează: {data.process.who_acts.join(", ")}</span>
              )}
            </div>
          ) : (
            <div className="text-[12px] text-stone-300" data-testid="mentor-process-state">Proces nepornit încă — vezi pașii recomandați mai jos.</div>
          )}
          {(data.process.blockers || []).map((b, i) => (
            <div key={i} className="mt-1.5 text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/25 rounded-lg px-2 py-1"
              data-testid="mentor-process-blocker">{b.text}</div>
          ))}
        </div>
      )}
      {data.onboarding?.guide?.explanation && (
        <div className="rounded-2xl border border-[#d4ff3a]/25 bg-[#d4ff3a]/5 p-3" data-testid="mentor-onboarding">
          <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider text-[#d4ff3a] mb-2">
            <Sparkles className="w-3 h-3" /> Ghid — prima dată în acest modul
          </div>
          <div className="text-[12px] leading-relaxed text-stone-200 max-h-52 overflow-auto whitespace-pre-wrap">
            {String(data.onboarding.guide.explanation).replace(/##\s?/g, "▸ ").replace(/\*\*/g, "")}
          </div>
        </div>
      )}
      {data.related_modules?.length > 0 && (
        <div data-testid="mentor-related">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5">Module conexe (din Knowledge Graph)</div>
          <div className="flex flex-wrap gap-1.5">
            {data.related_modules.map(m => (
              <button key={m.module} onClick={() => (onNavigate || ((p) => { window.location.href = p; }))(`/${m.module}`)}
                className="text-[10px] font-bold px-2 py-1 rounded-lg bg-stone-800 text-stone-300 hover:text-white border border-stone-700 hover:border-[#d4ff3a]/40"
                data-testid={`mentor-related-${m.module}`}>
                {m.module}
              </button>
            ))}
          </div>
        </div>
      )}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Compass className="w-3.5 h-3.5 text-[#d4ff3a]" />
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-400">Următorii pași recomandați pentru tine</div>
          <div className="flex-1" />
          <button onClick={() => load(true)} className="text-[10px] text-stone-500 hover:text-stone-300 flex items-center gap-1" data-testid="mentor-replay-btn">
            <RotateCcw className="w-3 h-3" /> Reia ghidul
          </button>
        </div>
        {data.actions?.length
          ? <MentorActions actions={data.actions} onNavigate={onNavigate} focus={focus} />
          : <div className="text-xs text-stone-500" data-testid="mentor-no-actions">Ești la zi — nicio acțiune urgentă. Bravo!</div>}
      </div>
    </div>
  );
};

export const SmartEmptyState = ({ resource, path, className = "" }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [d, setD] = useState(null);
  useEffect(() => {
    jpost("/api/ai-brain/mentor/empty-state", { path: path || location.pathname, resource })
      .then(setD).catch(() => {});
  }, [resource, path, location.pathname]);
  if (!d) return <div className={`text-sm text-stone-500 ${className}`}>Nu există date.</div>;
  return (
    <div className={`text-center p-8 border border-dashed border-stone-700 rounded-2xl ${className}`} data-testid={`smart-empty-${resource}`}>
      <Compass className="w-6 h-6 text-[#d4ff3a] mx-auto mb-2" />
      <div className="text-sm font-bold text-white">{d.reason}</div>
      <div className="text-xs text-stone-400 mt-1">{d.next_step}</div>
      <button onClick={() => navigate(d.cta_path)}
        className="mt-3 px-4 py-1.5 text-xs rounded-lg bg-[#d4ff3a] text-stone-900 font-bold"
        data-testid={`smart-empty-cta-${resource}`}>
        Hai să facem asta <ArrowRight className="w-3 h-3 inline ml-1" />
      </button>
    </div>
  );
};
