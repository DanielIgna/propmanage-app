// UX-001 · AchievementsCard — între Copilotul Casei și Drumul Casei Tale.
// 🏆 Ultimul achievement · 📈 Ultimul progres · 🎯 Următorul obiectiv · ⭐ Următorul unlock
// + grila de insigne cu explainability completă + celebrări discrete (CSS, fără agresivitate).
import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Trophy, TrendingUp, Target, Star, ChevronDown, X, Lock } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const Row = ({ icon: Icon, color, label, value, tid }) => (
  <div className="flex items-start gap-2.5 py-1.5" data-testid={tid}>
    <Icon className="w-4 h-4 shrink-0 mt-0.5" style={{ color }} />
    <div className="min-w-0">
      <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">{label}</div>
      <div className="text-[11px] font-bold text-slate-700 leading-snug">{value}</div>
    </div>
  </div>
);

const Celebration = ({ ev, onClose, animate }) => (
  <div className={`rounded-2xl border border-[#166534]/20 bg-[#F0FBF4] p-3 flex items-start gap-2.5 ${animate ? "cv2-celebrate" : ""}`}
    data-testid={`celebration-${ev.type}`}>
    <span className="text-xl shrink-0">{ev.icon}</span>
    <div className="flex-1 min-w-0">
      <div className="text-xs font-black text-slate-900">{ev.title}</div>
      {ev.message && <div className="text-[10px] text-slate-500 leading-snug mt-0.5">{ev.message}</div>}
      {ev.unlock && <div className="text-[10px] font-bold text-[#166534] mt-0.5">⭐ Deblocat: {ev.unlock}</div>}
    </div>
    <button onClick={onClose} className="shrink-0 text-slate-300" data-testid="celebration-dismiss"><X className="w-3.5 h-3.5" /></button>
  </div>
);

const BadgeDetail = ({ b }) => (
  <div className="mt-2 rounded-xl bg-slate-50 p-3 space-y-1.5 text-[10px] leading-snug" data-testid={`badge-detail-${b.id}`}>
    {[["De ce l-am primit?", b.why], ["Ce înseamnă?", b.meaning],
      ["Ce beneficii îmi aduce?", b.benefit], ["Ce urmează?", b.next]].map(([q, a]) => a && (
      <div key={q} className="flex gap-2">
        <span className="shrink-0 w-28 font-black text-slate-500">{b.earned ? q : q.replace("l-am primit?", "l-aș primi?")}</span>
        <span className="text-slate-600">{a}</span>
      </div>
    ))}
  </div>
);

export const AchievementsCard = () => {
  const [d, setD] = useState(null);
  const [events, setEvents] = useState([]);
  const [showGrid, setShowGrid] = useState(false);
  const [openBadge, setOpenBadge] = useState(null);

  const load = useCallback(() => {
    axios.get(`${API}/api/engagement/summary`).then(r => {
      setD(r.data);
      if (r.data?.new_events?.length) setEvents(r.data.new_events);
    }).catch(() => {});
  }, []);
  useEffect(() => {
    load();
    window.addEventListener("propmanage:doc-uploaded", load);
    return () => window.removeEventListener("propmanage:doc-uploaded", load);
  }, [load]);

  if (!d || d.enabled === false) return null;

  return (
    <div className="mx-5 mt-3 lg:mx-0 lg:mt-4 cv2-fade" data-testid="achievements-card">
      <div className="rounded-3xl border border-slate-100 bg-white shadow-sm p-4 lg:p-5">
        {events.length > 0 && (
          <div className="space-y-2 mb-3" data-testid="celebrations">
            {events.map((ev, i) => (
              <Celebration key={i} ev={ev} animate={d.animations_enabled}
                onClose={() => setEvents(es => es.filter((_, j) => j !== i))} />
            ))}
          </div>
        )}

        <div className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-2xl bg-amber-50 flex items-center justify-center shrink-0">
            <Trophy className="w-4 h-4 text-amber-500" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900 leading-none">Realizările casei</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{d.badges_earned_count}/{d.badges.length} insigne obținute</div>
          </div>
          <button onClick={() => setShowGrid(v => !v)} data-testid="achievements-grid-toggle"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-slate-50 border border-slate-100 text-[10px] font-bold text-slate-500">
            Insigne <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showGrid ? "rotate-180" : ""}`} />
          </button>
        </div>

        <div className="mt-2 divide-y divide-slate-50">
          <Row icon={Trophy} color="#f59e0b" label="Ultimul achievement" tid="last-achievement"
            value={d.last_achievement ? `${d.last_achievement.icon} ${d.last_achievement.label}` : "Încă niciunul — primul e la un pas distanță"} />
          <Row icon={TrendingUp} color="#166534" label="Ultimul progres" tid="last-progress"
            value={d.last_progress ? `${d.last_progress.title}${d.last_progress.effect ? ` · ${d.last_progress.effect}` : ""}` : "Fă primul pas cu Copilotul Casei"} />
          <Row icon={Target} color="#0ea5e9" label="Următorul obiectiv" tid="next-objective"
            value={d.next_objective ? `${d.next_objective.label}${d.next_objective.missing?.[0] ? ` — ${d.next_objective.missing[0].label}` : ""}` : "Ai atins nivelul maxim 🎉"} />
          <Row icon={Star} color="#a855f7" label="Beneficiul care urmează" tid="next-unlock"
            value={d.next_unlock ? `${d.next_unlock.label} (la Nivelul ${d.next_unlock.level})` : "Toate beneficiile de nivel sunt deblocate"} />
        </div>

        {showGrid && (
          <div className="mt-3 grid grid-cols-2 gap-2" data-testid="achievements-grid">
            {d.badges.map(b => (
              <div key={b.id}>
                <button onClick={() => setOpenBadge(openBadge === b.id ? null : b.id)}
                  data-testid={`badge-${b.id}`}
                  className={`w-full flex items-center gap-2 rounded-2xl border p-2.5 text-left transition-colors ${b.earned ? "border-amber-100 bg-amber-50/50" : "border-slate-100 bg-slate-50/50 opacity-70"}`}>
                  <span className={`text-lg shrink-0 ${b.earned ? "" : "grayscale"}`}>{b.icon}</span>
                  <span className={`flex-1 text-[10px] font-bold leading-tight ${b.earned ? "text-slate-800" : "text-slate-400"}`}>{b.label}</span>
                  {!b.earned && <Lock className="w-3 h-3 text-slate-300 shrink-0" />}
                </button>
                {openBadge === b.id && <BadgeDetail b={b} />}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AchievementsCard;
