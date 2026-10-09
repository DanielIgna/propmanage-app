// AI Admin Tour — guided spotlight tour showcasing AI capabilities for new admins.
// 6 steps: each highlights a real DOM element via getBoundingClientRect overlay.
// Auto-triggers once per admin (flag: ai_admin_tour_seen). Manual replay via "Reia tur" button.
import React, { useEffect, useState, useCallback, useRef } from "react";
import axios from "axios";
import { X, ChevronRight, ChevronLeft, Sparkles, RotateCcw } from "lucide-react";
import { useAuth } from "../../auth";
import { API } from "../DashShared";

const STEPS = [
  {
    target: '[data-testid="admin-header-health-badge"]',
    placement: "bottom",
    title: "AI Health Score — mereu vizibil",
    body: "Aici vezi instant starea AI a platformei (0-100). Click oricând pentru detalii complete. Când scorul scade sub 60, badge-ul pulsează roșu și primești alertă.",
    icon: "❤️",
  },
  {
    target: '[data-testid="admin-nav-ai"]',
    placement: "right",
    title: "AI Investigator — comanda centrală",
    body: "Tab-ul tău AI. Combină scanere deterministice cu Claude Sonnet 4.5 pentru a detecta anomalii, propune fix-uri și răspunde la întrebări despre platformă.",
    icon: "🤖",
    triggerNav: "ai",
  },
  {
    target: '[data-testid="ai-health-score"]',
    placement: "bottom",
    title: "Score Card detaliat",
    body: "Vezi cele 3 sub-scoruri (Findings, Eficacitate, Concierge) cu pondere și trend 14 zile. Snapshot zilnic salvat automat.",
    icon: "📊",
    waitMs: 600,
  },
  {
    target: '[data-testid="finding-repair-"], [data-testid^="finding-repair-"]',
    placement: "top",
    title: "Repair Suggester per Finding",
    body: "Pentru fiecare anomalie, click pe icoana ✦ ca să primești de la Claude un plan structurat: pași concreți, rollback, verificare. Aprobi/respingi, NU se execută automat.",
    icon: "🛠️",
  },
  {
    target: '[data-testid="repair-trend-chart"]',
    placement: "top",
    title: "Repair Audit Log + Trend",
    body: "Eficacitate per pattern de finding + heatmap GitHub-style pe 4-12 săptămâni. Vezi care fix-uri AI funcționează și care nu.",
    icon: "📈",
  },
  {
    target: '[data-testid="effectiveness-alert-config"]',
    placement: "top",
    title: "Alertă email automată",
    body: "Activează cron-ul Luni 09:00: primești email când eficacitatea AI scade sub pragul setat. Anti-spam ISO-week dedupe. Click Simulare ca să testezi.",
    icon: "🔔",
  },
  {
    target: '[data-testid="admin-nav-concierge"]',
    placement: "right",
    title: "Concierge & Security",
    body: "AI Concierge pentru clienți/specialiști/operatori cu protecție bot/VPN/GEO + prompt-injection filter + PII redaction. Toate blocările apar și ca findings în Investigator.",
    icon: "🛡️",
    triggerNav: "concierge",
  },
];

const PADDING = 8;
const BUBBLE_W = 360;
const BUBBLE_H_EST = 230;

export const AIAdminTour = () => {
  const { user, refreshUser } = useAuth();
  const [forceOpen, setForceOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState(null);
  const [closing, setClosing] = useState(false);
  const observerRef = useRef(null);

  const isAdmin = user && user !== false && user.role === "admin";
  const shouldAutoShow = isAdmin && user.ai_admin_tour_seen === false;
  const visible = isAdmin && !closing && (forceOpen || shouldAutoShow);

  // Expose a replay handler globally so menu/headers can trigger it
  useEffect(() => {
    const handler = () => { setStep(0); setClosing(false); setForceOpen(true); };
    window.addEventListener("propmanage:ai-tour-replay", handler);
    return () => window.removeEventListener("propmanage:ai-tour-replay", handler);
  }, []);

  // Track the current target's bounding rect (responsive on scroll/resize)
  const updateRect = useCallback(() => {
    if (!visible) return;
    const cur = STEPS[step];
    if (!cur) return;
    // Selector may contain a fallback (comma-separated). Try each.
    const selectors = cur.target.split(",").map(s => s.trim());
    let el = null;
    for (const sel of selectors) {
      el = document.querySelector(sel);
      if (el) break;
    }
    if (!el) { setRect(null); return; }
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) { setRect(null); return; }
    setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    // Scroll element into view if offscreen
    if (r.top < 80 || r.bottom > window.innerHeight - 80) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [step, visible]);

  useEffect(() => {
    if (!visible) return;
    const cur = STEPS[step];
    if (cur?.triggerNav) {
      window.dispatchEvent(new CustomEvent("propmanage:nav-admin", { detail: { tab: cur.triggerNav } }));
    }
    const delay = cur?.waitMs ?? 250;
    const t = setTimeout(updateRect, delay);
    const interval = setInterval(updateRect, 800); // poll for late-mounted elements
    window.addEventListener("scroll", updateRect, true);
    window.addEventListener("resize", updateRect);
    return () => {
      clearTimeout(t);
      clearInterval(interval);
      window.removeEventListener("scroll", updateRect, true);
      window.removeEventListener("resize", updateRect);
    };
  }, [step, visible, updateRect]);

  const finishTour = async () => {
    setClosing(true);
    setForceOpen(false);
    try {
      await axios.post(`${API}/auth/ai-admin-tour-seen`);
      if (refreshUser) await refreshUser();
    } catch { /* swallow */ }
  };

  const next = () => {
    if (step < STEPS.length - 1) setStep(step + 1);
    else finishTour();
  };

  if (!visible) return null;

  const cur = STEPS[step];
  const totalSteps = STEPS.length;

  // Compute bubble position
  let bubbleStyle = { top: 80, left: 24, maxWidth: BUBBLE_W };
  if (rect) {
    const place = cur.placement || "bottom";
    if (place === "bottom") {
      bubbleStyle = { top: rect.top + rect.height + 16, left: Math.max(12, Math.min(window.innerWidth - BUBBLE_W - 12, rect.left + rect.width / 2 - BUBBLE_W / 2)), maxWidth: BUBBLE_W };
    } else if (place === "right") {
      bubbleStyle = { top: Math.max(12, rect.top), left: Math.min(window.innerWidth - BUBBLE_W - 12, rect.left + rect.width + 16), maxWidth: BUBBLE_W };
    } else if (place === "top") {
      bubbleStyle = { top: Math.max(12, rect.top - BUBBLE_H_EST - 16), left: Math.max(12, Math.min(window.innerWidth - BUBBLE_W - 12, rect.left + rect.width / 2 - BUBBLE_W / 2)), maxWidth: BUBBLE_W };
    } else if (place === "left") {
      bubbleStyle = { top: Math.max(12, rect.top), left: Math.max(12, rect.left - BUBBLE_W - 16), maxWidth: BUBBLE_W };
    }
  } else {
    // Fallback center
    bubbleStyle = { top: "50%", left: "50%", transform: "translate(-50%, -50%)", maxWidth: BUBBLE_W };
  }

  return (
    <>
      {/* Backdrop with cutout for target */}
      <div className="fixed inset-0 z-[80] pointer-events-none" data-testid="ai-tour-overlay">
        <svg className="w-full h-full">
          <defs>
            <mask id="ai-tour-mask">
              <rect x="0" y="0" width="100%" height="100%" fill="white" />
              {rect && (
                <rect
                  x={rect.left - PADDING}
                  y={rect.top - PADDING}
                  width={rect.width + PADDING * 2}
                  height={rect.height + PADDING * 2}
                  rx="12"
                  fill="black"
                />
              )}
            </mask>
          </defs>
          <rect x="0" y="0" width="100%" height="100%" fill="rgba(0,0,0,0.72)" mask="url(#ai-tour-mask)" />
        </svg>

        {/* Pulsing highlight ring */}
        {rect && (
          <div
            className="absolute rounded-xl border-2 border-[#d4ff3a] animate-pulse"
            style={{
              top: rect.top - PADDING,
              left: rect.left - PADDING,
              width: rect.width + PADDING * 2,
              height: rect.height + PADDING * 2,
              boxShadow: "0 0 0 9999px rgba(0,0,0,0)",
            }}
          />
        )}
      </div>

      {/* Tooltip bubble */}
      <div
        className="fixed z-[81] bg-gradient-to-br from-stone-900 to-stone-950 border border-[#d4ff3a]/30 rounded-2xl p-5 shadow-2xl pointer-events-auto"
        style={{ width: BUBBLE_W, ...bubbleStyle }}
        data-testid="ai-tour-bubble"
      >
        <button onClick={finishTour} className="absolute top-3 right-3 p-1.5 hover:bg-white/10 rounded-full" data-testid="ai-tour-close" aria-label="Închide tur">
          <X className="w-3.5 h-3.5 text-stone-400" />
        </button>

        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-[#d4ff3a]" />
          <span className="text-[10px] uppercase tracking-wider text-[#d4ff3a]">AI Tour · {step + 1} / {totalSteps}</span>
        </div>

        <div className="text-4xl mb-2" aria-hidden="true">{cur.icon}</div>
        <h3 className="font-serif text-xl text-white mb-2" data-testid="ai-tour-title">{cur.title}</h3>
        <p className="text-stone-300 text-sm leading-relaxed mb-4">{cur.body}</p>

        <div className="flex gap-1 mb-4">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-[#d4ff3a]" : "bg-white/10"}`} data-testid={`ai-tour-dot-${i}`} />
          ))}
        </div>

        <div className="flex items-center justify-between gap-2">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-xs text-stone-300 disabled:opacity-30 flex items-center gap-1"
            data-testid="ai-tour-prev"
          >
            <ChevronLeft className="w-3 h-3" /> Înapoi
          </button>
          <button
            onClick={finishTour}
            className="text-[11px] text-stone-500 hover:text-stone-300"
            data-testid="ai-tour-skip"
          >
            Sari tot
          </button>
          <button
            onClick={next}
            className="bg-[#d4ff3a] hover:bg-[#bce82e] text-black px-4 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1"
            data-testid="ai-tour-next"
          >
            {step === STEPS.length - 1 ? "Finalizează" : "Mai departe"} <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </>
  );
};

// Replay button: dispatches the event handled by AIAdminTour
export const ReplayAIAdminTourButton = ({ className = "" }) => {
  const trigger = () => window.dispatchEvent(new CustomEvent("propmanage:ai-tour-replay"));
  return (
    <button
      onClick={trigger}
      className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 ${className}`}
      title="Reia tur AI"
      data-testid="ai-tour-replay-btn"
    >
      <RotateCcw className="w-3 h-3" />
      Reia tur
    </button>
  );
};

export default AIAdminTour;
