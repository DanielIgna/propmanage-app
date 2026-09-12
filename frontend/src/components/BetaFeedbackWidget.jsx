// PPOS P3a-M3 — Beta feedback lives in Settings (no floating button):
// the panel opens via the "pm-open-beta-feedback" event; nothing overlaps navigation.
import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { MessageSquareHeart, X, Send, ThumbsUp, ThumbsDown, ChevronRight } from "lucide-react";
import { useAuth } from "../auth";

const API = process.env.REACT_APP_BACKEND_URL;
const QUESTIONS = [
  ["confusing", "Ce ți s-a părut confuz?"],
  ["easy", "Ce a fost ușor?"],
  ["trust", "Ce ți-a dat încredere?"],
  ["almost_quit", "Ce aproape te-a făcut să renunți?"],
  ["impressed", "Ce funcție te-a impresionat cel mai mult?"],
];

// Entry point button — mount inside Settings lists (client + specialist).
export const BetaFeedbackEntry = ({ light = false }) => (
  <button
    onClick={() => window.dispatchEvent(new Event("pm-open-beta-feedback"))}
    data-testid="beta-feedback-open"
    className={light
      ? "w-full flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm text-left"
      : "w-full flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/[0.08] p-3.5 text-left transition-colors"}
  >
    <span className={light ? "w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center" : "w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center"}>
      <MessageSquareHeart className={light ? "w-5 h-5 text-slate-500" : "w-5 h-5 text-[#d4ff3a]"} />
    </span>
    <span className="flex-1">
      <span className={`block text-sm font-black ${light ? "text-slate-900" : "text-stone-100"}`}>Feedback beta</span>
      <span className={`block text-[10px] ${light ? "text-slate-400" : "text-stone-500"}`}>2 minute · citit de fondator</span>
    </span>
    <ChevronRight className={light ? "w-4 h-4 text-slate-300" : "w-4 h-4 text-stone-500"} />
  </button>
);

export const BetaFeedbackWidget = () => {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState({});
  const [recommend, setRecommend] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(() => localStorage.getItem("pm_beta_fb_done") === "1");

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener("pm-open-beta-feedback", onOpen);
    return () => window.removeEventListener("pm-open-beta-feedback", onOpen);
  }, []);

  const show = user && ["client", "specialist"].includes(user.role) &&
    (pathname.startsWith("/client") || pathname.startsWith("/specialist"));
  if (!show || !open) return null;

  const close = () => setOpen(false);
  const submit = async () => {
    setBusy(true); setErr("");
    try {
      await axios.post(`${API}/api/feedback/beta`, { ...answers, recommend });
      localStorage.setItem("pm_beta_fb_done", "1");
      setDone(true);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Nu am putut trimite. Încearcă din nou.");
    } finally { setBusy(false); }
  };

  return (
    <div className="pm-float-left-1 pm-float-panel w-[340px] max-w-[calc(100vw-2rem)] rounded-3xl bg-white border border-slate-200 shadow-2xl p-4" data-testid="beta-feedback-panel">
      <div className="flex items-start gap-2">
        <MessageSquareHeart className="w-5 h-5 text-slate-900 shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="text-sm font-black text-slate-900">Ești în beta — părerea ta decide roadmap-ul</div>
          <div className="text-[11px] text-slate-400">2 minute · citit de fondator</div>
        </div>
        <button onClick={close} data-testid="beta-feedback-close" aria-label="Închide" className="p-1 text-slate-400"><X className="w-4 h-4" /></button>
      </div>
      {done ? (
        <div className="mt-4 rounded-2xl bg-green-50 border border-green-200 p-4 text-center" data-testid="beta-fb-done">
          <div className="text-sm font-black text-green-700">Mulțumim! Feedback-ul tău a fost trimis.</div>
          <button onClick={close} className="mt-3 px-5 py-2 rounded-full text-xs font-bold text-black" style={{ background: "#d4ff3a" }}>Închide</button>
        </div>
      ) : (
        <>
          <div className="mt-3 space-y-2 max-h-[46vh] overflow-y-auto pr-1">
            {QUESTIONS.map(([k, q]) => (
              <div key={k}>
                <label className="text-[11px] font-bold text-slate-500">{q}</label>
                <input value={answers[k] || ""} onChange={e => setAnswers(a => ({ ...a, [k]: e.target.value }))}
                  data-testid={`beta-fb-${k}`} maxLength={500}
                  className="mt-0.5 w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:border-slate-400" />
              </div>
            ))}
            <div>
              <label className="text-[11px] font-bold text-slate-500">Ai recomanda PropManage?</label>
              <div className="mt-1 flex gap-2">
                <button onClick={() => setRecommend(true)} data-testid="beta-fb-recommend-yes"
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold border-2 ${recommend === true ? "border-green-500 bg-green-50 text-green-700" : "border-slate-200 text-slate-500"}`}>
                  <ThumbsUp className="w-3.5 h-3.5" /> Da
                </button>
                <button onClick={() => setRecommend(false)} data-testid="beta-fb-recommend-no"
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold border-2 ${recommend === false ? "border-red-400 bg-red-50 text-red-600" : "border-slate-200 text-slate-500"}`}>
                  <ThumbsDown className="w-3.5 h-3.5" /> Nu
                </button>
              </div>
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-500">De ce?</label>
              <input value={answers.why || ""} onChange={e => setAnswers(a => ({ ...a, why: e.target.value }))}
                data-testid="beta-fb-why" maxLength={500}
                className="mt-0.5 w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:border-slate-400" />
            </div>
          </div>
          {err && <div className="mt-2 text-[11px] font-bold text-red-500" data-testid="beta-fb-error">{err}</div>}
          <button onClick={submit} disabled={busy} data-testid="beta-fb-submit"
            className="mt-3 w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-full text-sm font-black text-black disabled:opacity-60" style={{ background: "#d4ff3a" }}>
            <Send className="w-4 h-4" /> {busy ? "Se trimite…" : "Trimite feedback"}
          </button>
        </>
      )}
    </div>
  );
};
