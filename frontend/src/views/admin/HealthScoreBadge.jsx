// Compact AI Health Score widget for permanent display in admin header.
// Click → navigates to AI Investigator tab. Pulses red when score < 60.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Activity } from "lucide-react";
import { API } from "../DashShared";

const RING_COLOR = {
  emerald: "#10b981",
  amber: "#f59e0b",
  red: "#ef4444",
};

const TEXT_COLOR = {
  emerald: "text-emerald-600 dark:text-emerald-400",
  amber: "text-amber-600 dark:text-amber-400",
  red: "text-red-600 dark:text-red-400",
};

const REFRESH_MS = 60_000; // poll every minute

export const HealthScoreBadge = ({ dark }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/admin/ai/health-score?days=7`);
      setData(r.data);
      setError(false);
    } catch {
      setError(true);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, []);

  if (error || !data) return null;

  const score = data.overall;
  const color = data.color || "emerald";
  const ringColor = RING_COLOR[color] || RING_COLOR.emerald;
  const txt = TEXT_COLOR[color] || TEXT_COLOR.emerald;
  const isCritical = score < 60;

  const size = 32, sw = 4;
  const r = (size - sw) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (Math.max(0, Math.min(100, score)) / 100) * circ;

  const goToAI = () => {
    window.dispatchEvent(new CustomEvent("propmanage:nav-admin", { detail: { tab: "ai" } }));
  };

  return (
    <button
      onClick={goToAI}
      title={`AI Health: ${score}/100 (${data.grade})${data.delta_7d != null ? ` · ${data.delta_7d > 0 ? "+" : ""}${data.delta_7d}pp 7z` : ""}`}
      className={`relative flex items-center gap-2 px-2 py-1 rounded-lg transition-colors ${
        dark ? "hover:bg-slate-800" : "hover:bg-slate-100"
      } ${isCritical ? "animate-pulse" : ""}`}
      data-testid="admin-header-health-badge"
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="currentColor" strokeWidth={sw} fill="none" className={dark ? "text-slate-700" : "text-slate-200"} />
          <circle
            cx={size / 2} cy={size / 2} r={r}
            stroke={ringColor} strokeWidth={sw} fill="none"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.8s ease-out" }}
          />
        </svg>
        <div className={`absolute inset-0 flex items-center justify-center text-[10px] font-bold tabular-nums ${txt}`}>
          {score}
        </div>
      </div>
      <div className="hidden md:flex flex-col items-start leading-none">
        <span className={`text-[9px] uppercase tracking-wider font-bold ${dark ? "text-slate-500" : "text-slate-400"}`}>AI Health</span>
        <span className={`text-[11px] font-semibold ${txt}`}>{data.grade}</span>
      </div>
      {isCritical && (
        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-red-500 ring-2 ring-white dark:ring-slate-900" />
      )}
    </button>
  );
};

export default HealthScoreBadge;
