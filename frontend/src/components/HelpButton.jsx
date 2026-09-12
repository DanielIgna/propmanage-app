// PPOS P3a-M1 — Help "?" button: opens the guided tour ON DEMAND (never auto).
import React, { useEffect, useState } from "react";
import { CircleHelp } from "lucide-react";
import { useAuth } from "../auth";

const HINT_KEY = "pm_tour_hint_seen";

export const HelpButton = ({ light = false }) => {
  const { user } = useAuth();
  const [hintSeen, setHintSeen] = useState(() => localStorage.getItem(HINT_KEY) === "1");

  const showHint = !!user && user !== false && !hintSeen && user.dashboard_tour_completed !== true;

  useEffect(() => {
    if (!showHint) return;
    const dismiss = () => { localStorage.setItem(HINT_KEY, "1"); setHintSeen(true); };
    document.addEventListener("click", dismiss, { once: true });
    return () => document.removeEventListener("click", dismiss);
  }, [showHint]);

  if (!user || user === false) return null;

  const openTour = () => {
    localStorage.setItem(HINT_KEY, "1");
    setHintSeen(true);
    window.dispatchEvent(new Event("pm-open-tour"));
  };

  return (
    <div className="relative shrink-0">
      <button
        onClick={openTour}
        data-testid="help-tour-button"
        title="Ghid și tur ghidat"
        aria-label="Deschide ghidul"
        className={light
          ? "relative w-10 h-10 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-600 hover:bg-slate-100 transition-colors"
          : "relative w-9 h-9 rounded-full border border-white/10 flex items-center justify-center text-stone-300 hover:bg-white/5 transition-colors"}
      >
        <CircleHelp style={{ width: 18, height: 18 }} />
        {showHint && <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#ccff00] animate-pulse" aria-hidden="true" />}
      </button>
      {showHint && (
        <span
          data-testid="help-tour-hint"
          className={`absolute right-0 top-full mt-2 z-50 whitespace-nowrap rounded-xl px-3 py-1.5 text-[11px] font-semibold shadow-lg ${light ? "bg-slate-900 text-white" : "bg-white text-slate-900"}`}
        >
          Ghidul e aici oricând
        </span>
      )}
    </div>
  );
};

export default HelpButton;
