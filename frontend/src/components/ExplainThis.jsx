// ExplainThis — AIB-003/004 · AI Mentor global.
// Buton discret «✨ AI Mentor» (doar autentificați). Tab implicit: Mentor (recomandări +
// onboarding contextual, auto-deschis la primul acces într-un modul). Tabs: Pagina/Procesul.
// Admin/super_admin: în plus «🔍 Explică o componentă».
import React, { useState, useCallback, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles, X, Loader2, ScanSearch, Route as RouteIcon, Compass } from "lucide-react";
import { MentorWidget } from "./MentorWidget";

const API = process.env.REACT_APP_BACKEND_URL;

const post = (url, body) =>
  fetch(`${API}${url}`, {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async r => { if (!r.ok) throw new Error((await r.json()).detail || r.status); return r.json(); });

const Md = ({ text }) => (
  <div className="text-[13px] leading-relaxed text-stone-200 space-y-1" data-testid="explain-text">
    {String(text || "").split("\n").map((ln, i) => {
      if (ln.startsWith("## ")) return <div key={i} className="text-[11px] font-black uppercase tracking-wider text-[#d4ff3a] pt-3">{ln.slice(3)}</div>;
      if (ln.startsWith("- ") || ln.startsWith("* ")) return <div key={i} className="pl-3">• {ln.slice(2).replace(/\*\*/g, "")}</div>;
      return <div key={i}>{ln.replace(/\*\*/g, "")}</div>;
    })}
  </div>
);

export const ExplainThis = ({ role }) => {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("mentor");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);
  const [compRef, setCompRef] = useState("");
  const isDev = role === "admin" || role === "super_admin";
  // Pe Home-ul Client (/client) AI Mentor NU mai apare ca element separat concurent cu
  // Copilotul Casei. Funcționalitatea rămâne 100% accesibilă din Copilot (eveniment pm-open-mentor).
  const onClientArea = location.pathname.startsWith("/client");

  // Copilotul Casei deschide AI Mentor complet (recomandări, scoruri, procese, istoric).
  const [mentorFocus, setMentorFocus] = useState(null);
  useEffect(() => {
    const h = (e) => { setMentorFocus(e?.detail || null); setTab("mentor"); setResult(null); setErr(null); setOpen(true); };
    window.addEventListener("pm-open-mentor", h);
    return () => window.removeEventListener("pm-open-mentor", h);
  }, []);

  const run = useCallback(async (kind, extra = {}) => {
    setTab(kind); setBusy(true); setErr(null); setResult(null);
    try {
      const d = await post(`/api/ai-brain/explain/${kind}`, { path: location.pathname, ...extra });
      setResult(d);
    } catch (e) { setErr(String(e.message || e)); } finally { setBusy(false); }
  }, [location.pathname]);

  // Onboarding inteligent: auto-deschide mentorul la primul acces într-un modul nou.
  useEffect(() => {
    if (!localStorage.getItem("pm_session_hint")) return;
    if (location.pathname.startsWith("/client")) return; // pe Home Client, ghidul trăiește în Copilot
    const module = location.pathname.split("/")[1] || "root";
    const key = `pm_mentor_checked_${module}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    fetch(`${API}/api/ai-brain/mentor?path=${encodeURIComponent(location.pathname)}`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.onboarding?.show) { setTab("mentor"); setOpen(true); } })
      .catch(() => {});
  }, [location.pathname]);

  if (!localStorage.getItem("pm_session_hint")) return null;
  return (
    <>
      {!onClientArea && (
      <button onClick={() => { setTab("mentor"); setOpen(true); }}
        className="pm-float-left-1 flex items-center gap-1.5 px-3 py-2 rounded-full bg-stone-900/90 border border-stone-700 text-[11px] font-bold text-stone-200 hover:border-[#d4ff3a]/60 hover:text-white shadow-lg backdrop-blur transition-colors"
        data-testid="explain-page-btn" title="AI Mentor — ghidul tău contextual">
        <Sparkles className="w-3.5 h-3.5 text-[#d4ff3a]" /> AI Mentor
      </button>
      )}
      {open && (
        <div className="fixed inset-y-0 left-0 z-[75] w-full sm:w-[420px] bg-stone-950 border-r border-stone-800 shadow-2xl flex flex-col" data-testid="explain-panel">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-stone-800">
            <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
            <div className="text-sm font-bold text-white">AI Mentor</div>
            <span className="text-[10px] text-stone-500 truncate">{location.pathname}</span>
            <div className="flex-1" />
            <button onClick={() => setOpen(false)} className="text-stone-400 hover:text-white" data-testid="explain-close-btn"><X className="w-4 h-4" /></button>
          </div>
          <div className="flex gap-1.5 px-4 py-2 border-b border-stone-800/60">
            <button onClick={() => { setTab("mentor"); setResult(null); setErr(null); }}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-lg flex items-center gap-1 ${tab === "mentor" ? "bg-[#d4ff3a] text-stone-900" : "bg-stone-800 text-stone-300 hover:text-white"}`}
              data-testid="mentor-tab-btn"><Compass className="w-3 h-3" /> Mentor</button>
            <button onClick={() => run("page")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg ${tab === "page" ? "bg-[#d4ff3a] text-stone-900" : "bg-stone-800 text-stone-300 hover:text-white"}`} data-testid="explain-run-page">Pagina</button>
            <button onClick={() => run("process")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg flex items-center gap-1 ${tab === "process" ? "bg-[#d4ff3a] text-stone-900" : "bg-stone-800 text-stone-300 hover:text-white"}`} data-testid="explain-run-process"><RouteIcon className="w-3 h-3" /> Procesul</button>
            {isDev && (
              <form className="flex gap-1.5 flex-1" onSubmit={e => { e.preventDefault(); if (compRef) run("component", { component: compRef }); }}>
                <input value={compRef} onChange={e => setCompRef(e.target.value)} placeholder="data-testid / etichetă buton"
                  className="flex-1 min-w-0 bg-stone-900 border border-stone-700 rounded-lg px-2 py-1 text-[10px] text-white" data-testid="explain-component-input" />
                <button className="px-2 py-1 text-[10px] font-bold rounded-lg bg-stone-800 text-stone-300 hover:text-white flex items-center gap-1" data-testid="explain-run-component">
                  <ScanSearch className="w-3 h-3" /> Componenta
                </button>
              </form>
            )}
          </div>
          <div className="flex-1 overflow-auto p-4">
            {tab === "mentor" ? (
              <MentorWidget path={location.pathname === "/client" ? "/client" : location.pathname} focus={mentorFocus} autoGuide onNavigate={(p) => { setOpen(false); window.location.href = p; }} />
            ) : (
              <>
                {busy && (
                  <div className="flex items-center gap-2 text-xs text-stone-400" data-testid="explain-loading">
                    <Loader2 className="w-4 h-4 animate-spin text-[#d4ff3a]" /> AI Brain analizează contextul tău real…
                  </div>
                )}
                {err && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="explain-error">{err}</div>}
                {result && !busy && (
                  <>
                    <Md text={result.explanation} />
                    <div className="mt-4 text-[10px] text-stone-600" data-testid="explain-meta">
                      {result.cached ? "instant (cache)" : result.model || ""}
                      {result.found_in ? ` · găsit în ${result.found_in}` : ""}
                      {result.grounded_on?.component ? ` · ancorat pe ${result.grounded_on.component}` : ""}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
};
