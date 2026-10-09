// Admin Tour v2.0 — Onboarding for new features (Autonomy, Twin, Cost & ROI).
// Lightweight tooltip overlay that auto-runs once per super-admin user.
// Marked complete via POST /api/admin/tour/complete.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { X, ChevronRight, Sparkles, Gauge, Bot, Coins } from "lucide-react";
import { API } from "../DashShared";

const STEPS = [
  {
    icon: Gauge,
    title: "Autonomy Engine",
    body: "Sistemul calculează 5 sub-scoruri (operational/technical/security/dev/ai) → tier (self-driving, autonomous, etc.). Vezi badge-ul în top-bar.",
    cta: "Vezi Autonomy",
    href: "/admin/autonomy",
    color: "from-violet-500 to-fuchsia-600",
  },
  {
    icon: Sparkles,
    title: "Auto-Tune to Self-Driving",
    body: "Buton mare gradient în pagina Autonomy. Un click → seed AI + repair + concierge + dismiss findings + snapshot. Boost-uiește scorul la 94+. Idempotent.",
    cta: "Mergi la Autonomy",
    href: "/admin/autonomy",
    color: "from-fuchsia-500 to-violet-600",
  },
  {
    icon: Bot,
    title: "Twin Orchestrator",
    body: "Chat AI super-admin. Întreabă orice: \u201eCare e tier-ul?\u201d, \u201eRulează Auto-Tune\u201d, \u201eProgramează snapshot mâine la 9\u201d. Acțiunile au confirm + token TTL.",
    cta: "Deschide Twin",
    href: "/admin/twin",
    color: "from-cyan-500 to-fuchsia-500",
  },
  {
    icon: Coins,
    title: "Cost & ROI Tracker",
    body: "Card pe dashboard care arată cât timp + bani salvează Autopilot (vs admin manual). Default 150 RON/h. Selector 7/30/90/365 zile.",
    cta: "Înapoi la Dashboard",
    href: "/admin",
    color: "from-emerald-500 to-cyan-500",
  },
];

const AdminTourV2 = ({ onClose }) => {
  const [idx, setIdx] = useState(0);
  const [closing, setClosing] = useState(false);

  const markDone = async () => {
    if (closing) return;
    setClosing(true);
    try {
      await axios.post(`${API}/admin/tour/complete`);
    } catch {
      // best-effort
    }
    onClose?.();
  };

  const next = () => {
    if (idx < STEPS.length - 1) setIdx(idx + 1);
    else markDone();
  };

  const step = STEPS[idx];
  const Icon = step.icon;
  const isLast = idx === STEPS.length - 1;

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="admin-tour-v2-overlay"
    >
      <div
        className="relative max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6"
        data-testid="admin-tour-v2-card"
      >
        <button
          onClick={markDone}
          className="absolute top-3 right-3 w-7 h-7 rounded-full hover:bg-slate-800 text-slate-400 hover:text-slate-200 flex items-center justify-center"
          data-testid="admin-tour-v2-close"
          aria-label="Skip"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-violet-300 font-bold mb-3">
          <Sparkles className="w-3 h-3" />
          Tour v2.0 · {idx + 1} / {STEPS.length}
        </div>

        <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg mb-3`}>
          <Icon className="w-7 h-7 text-white" />
        </div>

        <h3 className="text-xl font-bold text-slate-100 mb-2" data-testid="admin-tour-v2-title">
          {step.title}
        </h3>
        <p className="text-sm text-slate-300 leading-relaxed" data-testid="admin-tour-v2-body">
          {step.body}
        </p>

        {/* Progress dots */}
        <div className="flex gap-1.5 mt-5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i === idx ? "bg-violet-400" : i < idx ? "bg-violet-700" : "bg-slate-700"
              }`}
            />
          ))}
        </div>

        <div className="flex items-center gap-2 mt-5">
          <button
            onClick={markDone}
            className="text-xs text-slate-400 hover:text-slate-200 px-3 py-2"
            data-testid="admin-tour-v2-skip"
          >
            Skip tot
          </button>
          <a
            href={step.href}
            onClick={() => markDone()}
            className="text-xs px-3 py-2 rounded-lg border border-slate-600 hover:border-violet-400 text-slate-200"
            data-testid="admin-tour-v2-goto"
          >
            {step.cta}
          </a>
          <button
            onClick={next}
            className="ml-auto px-4 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white text-sm font-semibold shadow inline-flex items-center gap-1.5"
            data-testid="admin-tour-v2-next"
          >
            {isLast ? "Gata" : "Următorul"}
            {!isLast && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * AdminTourV2Wrapper — auto-mounts the tour for super-admins who haven't
 * completed it yet. Place once in AdminLayoutMetronic.
 */
export const AdminTourV2Wrapper = () => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${API}/admin/tour/status`);
        if (!cancelled && !r?.data?.completed) {
          // Small delay so the page paints first
          setTimeout(() => !cancelled && setShow(true), 1200);
        }
      } catch {
        // ignore
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!show) return null;
  return <AdminTourV2 onClose={() => setShow(false)} />;
};

export default AdminTourV2;
