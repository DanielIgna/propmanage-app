// ASM-001 · Copilotul Casei — primul widget din Home. Compune toate motoarele:
// Scorul Casei · Rezumat AI · Pasul cu impact maxim (explicabil) · Onboarding ·
// Progres · Beneficii · Comunitate · Storage · Subscription · Timeline AI.
import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, ChevronRight, ChevronDown, Check, Clock, Gift, Users, HardDrive,
  HeartPulse, History, BadgeCheck, Trophy, Box, BookOpen, CircleHelp, Flag, Star, Brain,
} from "lucide-react";
import { chapterForNextStep } from "../../lib/houseHealthAxis";

const API = process.env.REACT_APP_BACKEND_URL;
const GREEN = "#166534";
const LIME = "#d4ff3a";
const pctColor = (p) => (p >= 95 ? "#ef4444" : p >= 80 ? "#f59e0b" : "#34C759");

const ScoreRing = ({ score }) => {
  const r = 26, c = 2 * Math.PI * r;
  return (
    <div className="relative w-16 h-16 shrink-0" data-testid="copilot-house-score">
      <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={LIME} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * Math.min(100, score)) / 100}
          style={{ transition: "stroke-dashoffset 0.8s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-black text-slate-900 leading-none">{score}</span>
        <span className="text-[8px] font-bold text-slate-400">/100</span>
      </div>
    </div>
  );
};

const ExplainRow = ({ label, value }) => (
  <div className="flex gap-2 text-[11px]">
    <span className="shrink-0 font-black text-slate-500 w-24">{label}</span>
    <span className="text-slate-600 leading-snug">{value}</span>
  </div>
);

const NextAction = ({ a, run, axisChapter }) => {
  const [open, setOpen] = useState(false);
  if (!a) return null;
  const ex = a.explain || {};
  return (
    <div className="mt-3 rounded-2xl border border-[#166534]/15 bg-[#F0FBF4] p-3.5" data-testid="copilot-next-action">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[9px] font-black uppercase tracking-[0.14em] text-[#166534]">Pasul cu cel mai mare impact</span>
        {axisChapter && (
          <span data-testid="copilot-axis-chapter" title={axisChapter.title}
            className="text-[9px] font-black uppercase tracking-wide px-2 py-0.5 rounded-full bg-slate-900 text-[#d4ff3a]">
            A→G · Cap. {axisChapter.code}
          </span>
        )}
      </div>
      <div className="mt-1 text-sm font-black text-slate-900 leading-snug" data-testid="copilot-next-title">{a.title}</div>
      <p className="mt-1 text-xs text-slate-600 leading-relaxed">{a.value}</p>
      <div className="mt-2 flex items-center gap-2 flex-wrap text-[10px] font-bold text-slate-500">
        {ex.duration && <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white border border-slate-100"><Clock className="w-3 h-3" />{ex.duration}</span>}
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white border border-slate-100">impact {a.impact}/10</span>
      </div>
      <div className="mt-2.5 flex items-center gap-2">
        <button onClick={() => run(a)} data-testid="copilot-next-cta"
          className="flex-1 min-h-[40px] rounded-full text-xs font-black text-black active:scale-[0.98] transition-transform"
          style={{ background: "#ccff00" }}>
          Fă pasul acum
        </button>
        <button onClick={() => setOpen(o => !o)} data-testid="copilot-explain-toggle"
          className="px-3 min-h-[40px] rounded-full text-[11px] font-bold text-slate-500 border border-slate-200 flex items-center gap-1">
          <CircleHelp className="w-3.5 h-3.5" /> De ce?
        </button>
      </div>
      {open && (
        <div className="mt-3 space-y-1.5 rounded-xl bg-white border border-slate-100 p-3" data-testid="copilot-explain">
          <ExplainRow label="De ce?" value={ex.why} />
          <ExplainRow label="Ce câștigi?" value={ex.gain} />
          <ExplainRow label="Ce deblochezi?" value={ex.unlocks} />
          <ExplainRow label="Cât durează?" value={ex.duration} />
          <ExplainRow label="Impact casă" value={ex.house_impact} />
        </div>
      )}
    </div>
  );
};

const Checklist = ({ cl, run }) => {
  if (!cl || cl.complete) return null;
  return (
    <div className="mt-3 rounded-2xl border border-slate-100 bg-white p-3.5" data-testid="copilot-checklist">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-black text-slate-700 flex-1">Primii pași cu Copilotul</span>
        <span className="text-[10px] font-black text-[#166534]" data-testid="copilot-checklist-progress">{cl.done}/{cl.total}</span>
      </div>
      <div className="mt-2 space-y-1.5">
        {cl.steps.map(s => (
          <button key={s.id} onClick={() => !s.done && run({ cta_path: s.cta })} disabled={s.done}
            data-testid={`copilot-check-${s.id}`}
            className={`w-full flex items-center gap-2.5 text-left rounded-xl px-2 py-1.5 ${s.done ? "opacity-60" : "active:bg-slate-50"}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${s.done ? "bg-[#34C759]" : "border-2 border-slate-200"}`}>
              {s.done && <Check className="w-3 h-3 text-white" />}
            </span>
            <span className={`text-xs font-bold flex-1 ${s.done ? "text-slate-400 line-through" : "text-slate-700"}`}>{s.label}</span>
            {!s.done && <ChevronRight className="w-3.5 h-3.5 text-slate-300" />}
          </button>
        ))}
      </div>
    </div>
  );
};

const MiniStat = ({ icon: Icon, label, value, sub, onClick, tid }) => (
  <button onClick={onClick} data-testid={tid}
    className="flex-1 min-w-0 rounded-2xl border border-slate-100 bg-white p-3 text-left active:scale-[0.98] transition-transform">
    <Icon className="w-4 h-4 text-slate-400" />
    <div className="mt-1.5 text-sm font-black text-slate-900 truncate">{value}</div>
    <div className="text-[10px] text-slate-400 truncate">{label}</div>
    {sub && <div className="text-[9px] text-slate-400 truncate mt-0.5">{sub}</div>}
  </button>
);

const Timeline = ({ tl }) => {
  const [open, setOpen] = useState(false);
  if (!tl?.items?.length) return null;
  return (
    <div className="mt-3 rounded-2xl border border-slate-100 bg-white p-3.5" data-testid="copilot-timeline">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-2" data-testid="copilot-timeline-toggle">
        <History className="w-4 h-4 text-slate-400" />
        <span className="text-[11px] font-black text-slate-700 flex-1 text-left">Istoricul Copilotului</span>
        <ChevronDown className={`w-4 h-4 text-slate-300 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {tl.items.map((e, i) => (
            <div key={i} className="flex items-start gap-2.5" data-testid={`copilot-timeline-item-${i}`}>
              <span className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${e.kind === "level_up" ? "bg-amber-400" : e.kind === "milestone" ? "bg-sky-400" : e.kind === "badge" ? "bg-purple-400" : e.status === "done" ? "bg-[#34C759]" : "bg-slate-200"}`}>
                {e.kind === "level_up" ? <Trophy className="w-3 h-3 text-white" />
                  : e.kind === "milestone" ? <Flag className="w-3 h-3 text-white" />
                  : e.kind === "badge" ? <Star className="w-3 h-3 text-white" />
                  : e.status === "done" ? <Check className="w-2.5 h-2.5 text-white" />
                  : <Sparkles className="w-2.5 h-2.5 text-slate-500" />}
              </span>
              <div className="min-w-0">
                <div className="text-[11px] font-bold text-slate-700 leading-snug">{e.title}</div>
                <div className="text-[10px] text-slate-400">
                  {e.kind ? (e.effect || "") : e.status === "done" ? <>Ai făcut-o ✓{e.effect ? ` · ${e.effect}` : ""}</> : "Recomandat acum"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const HouseCopilot = ({ go, completeness, propName }) => {
  const [d, setD] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    axios.get(`${API}/api/copilot/dashboard`).then(r => setD(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    load();
    window.addEventListener("propmanage:doc-uploaded", load);
    return () => window.removeEventListener("propmanage:doc-uploaded", load);
  }, [load]);

  const run = (a) => {
    const p = a?.cta_path || a?.cta || "";
    // Activare document → direct în Cartea casei (fără pasul inutil prin pagina Proprietăți)
    if (a?.id === "docs_for_benefit") {
      window.dispatchEvent(new CustomEvent("propmanage:open-house-book"));
      return;
    }
    if (p.startsWith("/client?tab=")) go?.(p.split("=")[1]);
    else if (["property", "benefits", "jobs", "request", "settings"].includes(p)) go?.(p === "request" ? "home" : p);
    else if (p) navigate(p);
  };

  if (!d) return null;
  const st = d.storage?.personal;
  const sub = d.subscription;
  const amb = d.community?.ambassador;
  const topDeal = d.community?.deals_needing_support?.[0];
  const axisCh = completeness ? chapterForNextStep(completeness) : null;

  return (
    <div className="mx-5 mt-5 lg:mx-0 lg:mt-0 cv2-fade" data-testid="copilot-widget">
      <div className="rounded-3xl border border-slate-100 bg-white shadow-sm p-4 lg:p-5">
        {/* Header: identitate + Scorul Casei */}
        <div className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-2xl flex items-center justify-center shrink-0" style={{ background: "#ccff00" }}>
            <Sparkles className="text-black" style={{ width: 18, height: 18 }} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900 leading-none">Copilotul Casei</div>
            <div className="text-[10px] text-slate-400 mt-0.5 truncate" data-testid="copilot-house-name">
              {propName ? `Casa mea · ${propName}` : "te ghidează spre acțiunea cu cea mai mare valoare"}
            </div>
          </div>
          <ScoreRing score={d.house_score?.score ?? 0} />
        </div>

        {/* Ce este important acum? — un singur rezumat personalizat pe datele reale ale casei */}
        <div className="mt-3 rounded-2xl p-3 bg-slate-50" data-testid="copilot-ai-summary">
          <div className="text-[9px] font-black uppercase tracking-[0.14em] text-slate-400 mb-1">Ce este important acum?</div>
          <p className="text-xs leading-relaxed text-slate-600">
            {d.summary?.text
              || `Casa ta e la ${d.house_score?.score ?? 0}/100.${d.house_score?.top_gap ? ` Acum contează cel mai mult: ${d.house_score.top_gap.label}${d.house_score.top_gap.hint ? ` — ${d.house_score.top_gap.hint}` : ""}.` : ""}`}
          </p>
        </div>

        <NextAction a={d.next_action} run={run} axisChapter={axisCh} />

        {/* O singură suprafață AI: „alte recomandări" deschide Copilotul complet (AI Mentor:
            scoruri, procese, blocaje, Knowledge Graph, istoric, feedback). Restul detaliilor
            casei se dezvăluie progresiv la cerere (Legea lui Hick). */}
        <div className="mt-3 flex items-center gap-2" data-testid="copilot-summary-actions">
          <button onClick={() => window.dispatchEvent(new CustomEvent("pm-open-mentor", { detail: { focus_path: d.next_action?.cta_path || d.next_action?.cta || "", focus_title: d.next_action?.title || "", focus_id: d.next_action?.id || "" } }))} data-testid="copilot-open-mentor"
            className="flex-1 flex items-center justify-center gap-1.5 min-h-[38px] rounded-full text-[11px] font-black text-[#166534] bg-[#166534]/5 active:scale-[0.98] transition-transform">
            <Brain className="w-3.5 h-3.5" /> Vezi alte recomandări
          </button>
          <button onClick={() => setDetailsOpen(o => !o)} data-testid="copilot-details-toggle"
            className="px-3 min-h-[38px] rounded-full text-[11px] font-bold text-slate-500 border border-slate-200 flex items-center gap-1">
            Detalii casă <ChevronDown className={`w-3.5 h-3.5 transition-transform ${detailsOpen ? "rotate-180" : ""}`} />
          </button>
        </div>

        {detailsOpen && (<div data-testid="copilot-details">
        <Checklist cl={d.checklist} run={run} />

        {/* Progres casă */}
        <div className="mt-3 flex gap-2" data-testid="copilot-progress">
          <MiniStat icon={BookOpen} label="Cartea Casei" value={`${d.progress?.book?.pct ?? 0}%`}
            sub={d.progress?.book?.next_step?.label} onClick={() => run({ cta: "property" })} tid="copilot-progress-book" />
          <MiniStat icon={Box} label="Digital Twin" value={`${d.progress?.twin?.pct ?? 0}%`}
            sub={d.progress?.twin?.hint} onClick={() => navigate("/digital-twin")} tid="copilot-progress-twin" />
          <MiniStat icon={Users} label="Nivel membru"
            value={d.progress?.membership?.level?.name || d.progress?.membership?.level || "—"}
            sub={d.progress?.membership?.next_level ? `${d.progress.membership.next_level.points_needed}p până la ${d.progress.membership.next_level.name}` : null}
            onClick={() => run({ cta: "benefits" })} tid="copilot-progress-membership" />
        </div>

        {/* Beneficii */}
        <button onClick={() => run({ cta: "benefits" })} data-testid="copilot-benefits"
          className="mt-3 w-full flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3 text-left active:bg-slate-50">
          <Gift className="w-4 h-4 shrink-0" style={{ color: GREEN }} />
          <span className="flex-1 text-xs font-bold text-slate-700">
            {d.benefits?.available || 0} beneficii active
            {d.benefits?.expiring_soon?.length > 0 && <span className="text-amber-600"> · {d.benefits.expiring_soon.length} expiră curând</span>}
            {d.benefits?.almost_unlocked?.length > 0 && <span className="text-slate-400"> · {d.benefits.almost_unlocked.length} aproape deblocate</span>}
          </span>
          <ChevronRight className="w-4 h-4 text-slate-300" />
        </button>

        {/* Comunitate */}
        <div className="mt-2 rounded-2xl border border-slate-100 bg-white p-3" data-testid="copilot-community">
          <div className="flex items-center gap-2">
            {amb?.is_founding
              ? <Trophy className="w-4 h-4 text-amber-500" />
              : <BadgeCheck className="w-4 h-4" style={{ color: amb?.is_ambassador ? GREEN : "#94a3b8" }} />}
            <span className="text-xs font-bold text-slate-700 flex-1" data-testid="copilot-ambassador-status">
              {amb?.is_founding ? `${amb.founding_badge} 🏆 #${amb.founding_rank}`
                : amb?.is_ambassador ? `${amb.badge} 🏅`
                : amb?.remaining === 1 ? "Încă o recomandare până la Ambassador"
                : `Community Ambassador: ${amb?.validated ?? 0}/${amb?.threshold ?? 2} recomandări`}
            </span>
            {!amb?.is_founding && (amb?.founding_slots_left ?? 0) > 0 && (
              <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 border border-amber-100" data-testid="copilot-founding-slots">
                {amb.founding_slots_left} locuri Founding
              </span>
            )}
          </div>
          {topDeal && (
            <button onClick={() => run({ cta: "benefits" })} data-testid="copilot-top-deal"
              className="mt-2 w-full flex items-center gap-2 rounded-xl bg-slate-50 p-2.5 text-left">
              <span className="text-sm shrink-0">{topDeal.emoji || "🤝"}</span>
              <span className="flex-1 text-[11px] font-bold text-slate-600 leading-snug">
                „{topDeal.title}" mai are nevoie de {topDeal.needed} susținători
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            </button>
          )}
        </div>

        {/* Storage + Subscription Health */}
        <div className="mt-2 grid grid-cols-2 gap-2">
          {st && (
            <div className="rounded-2xl border border-slate-100 bg-white p-3" data-testid="copilot-storage">
              <div className="flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] font-black text-slate-600 flex-1">Stocare</span>
                <span className="text-[10px] font-bold text-slate-400">{st.pct}%</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${Math.min(100, st.pct)}%`, background: pctColor(st.pct) }} />
              </div>
              <div className="mt-1 text-[9px] text-slate-400">{st.used_human} din {st.quota_human}</div>
              {st.warning && d.storage?.upgrade_available && (
                <button onClick={() => navigate("/house-health/upgrade")} data-testid="copilot-storage-upgrade"
                  className="mt-1.5 w-full py-1.5 rounded-full text-[10px] font-black text-black" style={{ background: LIME }}>
                  +5 GB cu House Health
                </button>
              )}
            </div>
          )}
          {sub && (
            <div className="rounded-2xl border border-slate-100 bg-white p-3" data-testid="copilot-subscription">
              <div className="flex items-center gap-1.5">
                <HeartPulse className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] font-black text-slate-600 flex-1">Abonament</span>
                <span className={`text-[10px] font-black ${sub.score >= 70 ? "text-[#166534]" : sub.score >= 40 ? "text-amber-600" : "text-rose-600"}`}>{sub.score}/100</span>
              </div>
              <div className="mt-1 text-[9px] text-slate-400">
                {sub.active ? "House Health activ" : "Fără abonament"}
              </div>
              {sub.upgrade_suggestion && (
                <div className="mt-1.5 text-[9px] font-bold text-slate-500 leading-snug" data-testid="copilot-upgrade-suggestion">
                  {sub.upgrade_suggestion}
                </div>
              )}
            </div>
          )}
        </div>

        <Timeline tl={d.timeline} />
        </div>)}
      </div>
    </div>
  );
};

export default HouseCopilot;
