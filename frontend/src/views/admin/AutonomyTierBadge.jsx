// Compact Autonomy Tier badge for the admin top-bar.
// Shows: tier label, general score, 7-day sparkline. Click → /admin/autonomy.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Gauge } from "lucide-react";
import { API } from "../DashShared";

const TIER_THEME = {
  "self-driving": {
    label: "Self-Driving",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    text: "text-emerald-600 dark:text-emerald-400",
    stroke: "#10b981",
    dot: "bg-emerald-500",
  },
  autonomous: {
    label: "Autonomous",
    bg: "bg-sky-500/10",
    border: "border-sky-500/40",
    text: "text-sky-600 dark:text-sky-400",
    stroke: "#0ea5e9",
    dot: "bg-sky-500",
  },
  assisted: {
    label: "Assisted",
    bg: "bg-amber-500/10",
    border: "border-amber-500/40",
    text: "text-amber-600 dark:text-amber-400",
    stroke: "#f59e0b",
    dot: "bg-amber-500",
  },
  manual: {
    label: "Manual",
    bg: "bg-slate-500/10",
    border: "border-slate-500/40",
    text: "text-slate-600 dark:text-slate-400",
    stroke: "#64748b",
    dot: "bg-slate-500",
  },
};

const REFRESH_MS = 5 * 60_000; // poll every 5 min (matches engine cache TTL)

// Tiny inline sparkline (SVG) — receives an array of numbers 0..100
const Sparkline = ({ values, stroke, width = 48, height = 18 }) => {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="opacity-90">
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts.join(" ")}
      />
    </svg>
  );
};

export const AutonomyTierBadge = ({ dark }) => {
  const [data, setData] = useState(null);
  const [trend, setTrend] = useState([]);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      const [s, h] = await Promise.all([
        axios.get(`${API}/admin/autonomy/score`),
        axios.get(`${API}/admin/autonomy/history?days=7`),
      ]);
      setData(s.data);
      const series = (h.data?.items || [])
        .map((it) => Number(it?.scores?.general))
        .filter((n) => Number.isFinite(n));
      setTrend(series);
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

  const score = Math.round(data?.scores?.general ?? 0);
  const tier = data?.tier || "manual";
  const theme = TIER_THEME[tier] || TIER_THEME.manual;

  // Compute 7d delta if we have ≥ 2 points
  let delta = null;
  if (trend.length >= 2) {
    delta = Math.round(trend[trend.length - 1] - trend[0]);
  }

  const deltaLabel =
    delta == null ? "" : ` · ${delta > 0 ? "+" : ""}${delta}pp 7z`;

  return (
    <Link
      to="/admin/autonomy"
      title={`Autonomy: ${score}/100 (${theme.label})${deltaLabel}`}
      className={`hidden sm:flex items-center gap-2 pl-2 pr-2.5 py-1 rounded-lg border ${theme.border} ${theme.bg} ${
        dark ? "hover:bg-slate-800/60" : "hover:bg-white"
      } transition-colors`}
      data-testid="admin-header-autonomy-badge"
    >
      <span className="relative flex items-center justify-center">
        <Gauge className={`w-4 h-4 ${theme.text}`} />
        <span className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${theme.dot} ring-2 ${dark ? "ring-slate-900" : "ring-white"}`} />
      </span>
      <div className="flex flex-col items-start leading-none">
        <span className={`text-[9px] uppercase tracking-wider font-bold ${dark ? "text-slate-500" : "text-slate-400"}`}>
          Autonomy
        </span>
        <span className={`text-[11px] font-semibold ${theme.text}`} data-testid="autonomy-tier-label">
          {theme.label}
        </span>
      </div>
      <span className={`tabular-nums text-sm font-bold ${theme.text}`} data-testid="autonomy-tier-score">
        {score}
      </span>
      {trend.length >= 2 && (
        <span className="hidden md:inline-block" data-testid="autonomy-tier-sparkline">
          <Sparkline values={trend} stroke={theme.stroke} />
        </span>
      )}
      {delta != null && Math.abs(delta) > 0 && (
        <span
          className={`hidden lg:inline-block text-[10px] font-bold tabular-nums ${
            delta > 0 ? "text-emerald-500" : "text-rose-500"
          }`}
          data-testid="autonomy-tier-delta"
        >
          {delta > 0 ? "▲" : "▼"}
          {Math.abs(delta)}
        </span>
      )}
    </Link>
  );
};

export default AutonomyTierBadge;
