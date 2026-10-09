// Admin Productivity Score widget (super-only).
// Shows per-admin metrics: score, success rate, active days, approvals reviewed.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { TrendingUp, Award, Activity, CheckCircle2, RefreshCw } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const SCOPE_TONE = {
  general:  "bg-violet-100  text-violet-700  dark:bg-violet-500/15  dark:text-violet-300",
  testing:  "bg-cyan-100    text-cyan-700    dark:bg-cyan-500/15    dark:text-cyan-300",
  frontend: "bg-pink-100    text-pink-700    dark:bg-pink-500/15    dark:text-pink-300",
  backend:  "bg-blue-100    text-blue-700    dark:bg-blue-500/15    dark:text-blue-300",
  security: "bg-red-100     text-red-700     dark:bg-red-500/15     dark:text-red-300",
  ai:       "bg-amber-100   text-amber-700   dark:bg-amber-500/15   dark:text-amber-300",
  ops:      "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
};

const scoreColor = (s) => {
  if (s >= 75) return { bg: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400", label: "TOP" };
  if (s >= 50) return { bg: "bg-amber-500",   text: "text-amber-600 dark:text-amber-400",     label: "OK" };
  if (s >  0)  return { bg: "bg-orange-500",  text: "text-orange-600 dark:text-orange-400",   label: "LOW" };
  return            { bg: "bg-slate-400",     text: "text-slate-500 dark:text-slate-400",     label: "IDLE" };
};

const ScoreRing = ({ score }) => {
  const tone = scoreColor(score);
  const dash = (score / 100) * 100;
  return (
    <div className="relative w-14 h-14 flex items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15.91" fill="none" className="stroke-slate-200 dark:stroke-slate-700" strokeWidth="3" />
        <circle
          cx="18" cy="18" r="15.91"
          fill="none"
          className={tone.bg.replace("bg-", "stroke-")}
          strokeWidth="3"
          strokeDasharray={`${dash}, 100`}
          strokeLinecap="round"
        />
      </svg>
      <span className={`text-sm font-bold ${tone.text}`}>{score}</span>
    </div>
  );
};

// 7-day sparkline showing daily success rate (0-100).
// Empty points are rendered as gray dots so idle days are still visible.
const Sparkline = ({ values = [], days = [], width = 90, height = 32 }) => {
  if (!values || values.length === 0) return null;
  const max = 100;
  const padX = 3;
  const padY = 3;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;
  const n = values.length;
  const step = n > 1 ? innerW / (n - 1) : 0;
  const points = values.map((v, i) => ({
    x: padX + i * step,
    y: padY + innerH - (Math.max(0, Math.min(100, v)) / max) * innerH,
    v,
    day: days[i],
  }));
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  // Area fill = path + bottom corners
  const areaPath = `${path} L ${points[points.length - 1].x.toFixed(1)} ${(padY + innerH).toFixed(1)} L ${padX} ${(padY + innerH).toFixed(1)} Z`;

  const first = values[0];
  const last = values[values.length - 1];
  const trend = last > first + 5 ? "up" : last < first - 5 ? "down" : "flat";
  const lineColor = trend === "up" ? "stroke-emerald-500 fill-emerald-500" : trend === "down" ? "stroke-red-500 fill-red-500" : "stroke-slate-400 fill-slate-400";
  const areaColor = trend === "up" ? "fill-emerald-400/15" : trend === "down" ? "fill-red-400/15" : "fill-slate-400/10";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="inline-block"
      data-testid="sparkline"
    >
      <title>{days.map((d, i) => `${d}: ${values[i]}%`).join("\n")}</title>
      <path d={areaPath} className={areaColor} stroke="none" />
      <path d={path} className={lineColor} strokeWidth="1.5" fill="none" />
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={i === points.length - 1 ? 2.2 : 1.4}
          className={p.v === 0 ? "fill-slate-400 stroke-slate-400" : lineColor}
        />
      ))}
    </svg>
  );
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
    if (diffMin < 1) return "acum";
    if (diffMin < 60) return `acum ${diffMin}m`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `acum ${diffH}h`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 30) return `acum ${diffD}z`;
    return d.toLocaleDateString("ro-RO", { day: "2-digit", month: "short" });
  } catch {
    return iso;
  }
};

export const AdminProductivity = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/sub-admins/productivity`);
      setItems(r.data?.items || []);
    } catch {
      // 403 = not super
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const topPerformer = items.find((i) => i.score > 0);
  const avg = items.length > 0
    ? Math.round((items.reduce((s, i) => s + i.score, 0) / items.length) * 10) / 10
    : 0;
  const active = items.filter((i) => i.metrics.actions_30d > 0).length;

  return (
    <AdminCard
      testid="admin-productivity"
      title={
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-500" />
          <span>Admin Productivity Score</span>
          <span className="text-[10px] text-slate-500 font-normal">ultimele 30 zile · {items.length} admini</span>
        </div>
      }
      action={
        <button
          onClick={load}
          disabled={loading}
          className="text-[11px] text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 flex items-center gap-1 disabled:opacity-50"
          data-testid="productivity-refresh"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      }
    >
      {/* Summary row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="rounded-xl p-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-500/20" data-testid="prod-summary-avg">
          <div className="text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 font-medium">Scor mediu echipă</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{avg}</div>
        </div>
        <div className="rounded-xl p-3 bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200/60 dark:border-cyan-500/20" data-testid="prod-summary-active">
          <div className="text-[10px] uppercase tracking-wider text-cyan-700 dark:text-cyan-300 font-medium">Admini activi (30z)</div>
          <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400 mt-1">
            {active} <span className="text-sm font-normal text-cyan-500/70">/ {items.length}</span>
          </div>
        </div>
        <div className="rounded-xl p-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-500/20" data-testid="prod-summary-top">
          <div className="text-[10px] uppercase tracking-wider text-amber-700 dark:text-amber-300 font-medium flex items-center gap-1">
            <Award className="w-3 h-3" />
            Top performer
          </div>
          <div className="text-sm font-mono text-amber-700 dark:text-amber-300 mt-1 truncate">
            {topPerformer ? topPerformer.email : "—"}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-8 text-center text-sm text-slate-500" data-testid="productivity-loading">Se încarcă scorurile…</div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center text-sm text-slate-500" data-testid="productivity-empty">
          Nu ești super-admin sau nu există date.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 pr-3">Admin</th>
                <th className="py-2 pr-3">Scope</th>
                <th className="py-2 pr-3">Scor</th>
                <th className="py-2 pr-3 text-center">Acțiuni 30z</th>
                <th className="py-2 pr-3 text-center">Succes</th>
                <th className="py-2 pr-3 text-center">Zile active</th>
                <th className="py-2 pr-3 text-center">Aprobări</th>
                <th className="py-2 pr-3">Ultima acțiune</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => {
                const tone = scoreColor(it.score);
                return (
                  <tr key={it.id} className="border-b border-slate-100 dark:border-slate-800" data-testid={`productivity-row-${it.id}`}>
                    <td className="py-3 pr-3">
                      <div className="font-mono text-xs">{it.email}</div>
                      <div className="text-[10px] text-slate-500">{it.name} · {it.admin_seniority}</div>
                    </td>
                    <td className="py-3 pr-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${SCOPE_TONE[it.admin_scope] || SCOPE_TONE.general}`}>
                        {it.admin_scope}
                      </span>
                    </td>
                    <td className="py-3 pr-3">
                      <div className="flex items-center gap-2">
                        <ScoreRing score={it.score} />
                        <div className="flex flex-col gap-0.5">
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${tone.text} w-fit`}>{tone.label}</span>
                          <Sparkline values={it.sparkline || []} days={it.sparkline_days || []} />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <div className="font-bold">{it.metrics.actions_30d}</div>
                      <div className="text-[10px] text-slate-500">
                        <span className="text-emerald-500">{it.metrics.allowed}</span>
                        {" / "}
                        <span className="text-red-500">{it.metrics.denied}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <div className="text-sm">{it.metrics.success_rate_pct}%</div>
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Activity className="w-3 h-3 text-cyan-500" />
                        <span>{it.metrics.active_days_30d}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-amber-500" />
                        <span>{it.metrics.approvals_reviewed}</span>
                      </div>
                      {it.metrics.approvals_requested > 0 && (
                        <div className="text-[9px] text-slate-500">{it.metrics.approvals_requested} cerute</div>
                      )}
                    </td>
                    <td className="py-3 pr-3 text-[11px] text-slate-500 whitespace-nowrap">
                      {fmtTime(it.metrics.last_action_ts)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
        💡 <strong>Formulă scor</strong>: 60% rata succes (allowed/total) + 25% zile active (max 20/30) + 15% aprobări revizuite (max 5).
        Sparkline = success rate zilnic ultimele 7 zile (verde = uptrend, roșu = downtrend, gri = flat/idle).
        Idle = 0 acțiuni · Low &lt; 50 · OK 50-74 · Top ≥ 75.
      </div>
    </AdminCard>
  );
};
