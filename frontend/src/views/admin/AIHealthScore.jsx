// AI Health Score — top-level platform-AI fitness widget.
// Combines findings, repair effectiveness, and concierge block-rate into a single 0-100 score.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Activity, RefreshCw, TrendingUp, TrendingDown, AlertTriangle, Wrench, MessageSquare, Sparkles } from "lucide-react";
import { API } from "../DashShared";

const COLORS = {
  emerald: { ring: "#10b981", bg: "from-emerald-500/20 to-emerald-500/5", text: "text-emerald-600 dark:text-emerald-400", bar: "bg-emerald-500" },
  amber: { ring: "#f59e0b", bg: "from-amber-500/20 to-amber-500/5", text: "text-amber-600 dark:text-amber-400", bar: "bg-amber-500" },
  red: { ring: "#ef4444", bg: "from-red-500/20 to-red-500/5", text: "text-red-600 dark:text-red-400", bar: "bg-red-500" },
};

const Sparkline = ({ data, color = "#10b981" }) => {
  if (!data || data.length < 2) {
    return <div className="h-8 flex items-center justify-center text-[10px] text-slate-400 italic">Trend va apărea după 2+ zile</div>;
  }
  const w = 280, h = 32, pad = 2;
  const max = 100, min = 0;
  const xStep = (w - pad * 2) / Math.max(1, data.length - 1);
  const points = data.map((d, i) => {
    const x = pad + i * xStep;
    const y = pad + ((max - d.overall) / (max - min)) * (h - pad * 2);
    return `${x},${y}`;
  }).join(" ");
  const area = `M${pad},${h} L${points.split(" ").join(" L")} L${w - pad},${h} Z`;
  return (
    <svg width={w} height={h} className="block">
      <path d={area} fill={color} opacity="0.15" />
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {data.map((d, i) => {
        const x = pad + i * xStep;
        const y = pad + ((max - d.overall) / (max - min)) * (h - pad * 2);
        return <circle key={i} cx={x} cy={y} r="1.5" fill={color} />;
      })}
    </svg>
  );
};

const ScoreRing = ({ score, color, size = 140, strokeWidth = 12 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
  const c = COLORS[color] || COLORS.emerald;
  return (
    <div className="relative inline-block" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="currentColor" strokeWidth={strokeWidth} fill="none" className="text-slate-200 dark:text-slate-700" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          stroke={c.ring} strokeWidth={strokeWidth} fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease-out" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className={`text-4xl font-bold tabular-nums ${c.text}`}>{score}</div>
        <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">din 100</div>
      </div>
    </div>
  );
};

const SubScore = ({ icon: Icon, label, score, color, detail, weight }) => {
  const c = COLORS[color] || COLORS.emerald;
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white/50 dark:bg-slate-900/30" data-testid={`health-sub-${label}`}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon className={`w-3.5 h-3.5 ${c.text}`} />
        <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400">{label}</span>
        <span className="ml-auto text-[10px] text-slate-400">×{Math.round(weight * 100)}%</span>
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className={`text-2xl font-bold tabular-nums ${c.text}`}>{score}</span>
        <span className="text-[10px] text-slate-400">/100</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mb-1.5">
        <div className={`h-full ${c.bar} transition-all`} style={{ width: `${score}%` }} />
      </div>
      <div className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">{detail}</div>
    </div>
  );
};

export const AIHealthScore = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/ai/health-score?days=7`);
      setData(r.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (!data) {
    return (
      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 p-6 text-center text-slate-400 text-sm italic" data-testid="health-score-loading">
        Calculez scorul AI Health...
      </div>
    );
  }

  const c = COLORS[data.color] || COLORS.emerald;
  const m = data.metrics;
  const findingsDetail = `${m.findings.total_open} open · ${m.findings.by_severity.critical || 0} critic · ${m.findings.by_severity.high || 0} high`;
  const effDetail = m.effectiveness.neutral
    ? "Insuficiente decizii (neutru 70)"
    : `${m.effectiveness.applied}/${m.effectiveness.decided} aplicate (${m.effectiveness.effectiveness_pct}%)`;
  const concDetail = m.concierge.neutral
    ? "Fără trafic concierge (neutru 80)"
    : `${m.concierge.blocked}/${m.concierge.total} blocate (${m.concierge.block_rate_pct}%)`;

  const deltaUp = data.delta_7d != null && data.delta_7d > 0;
  const deltaDown = data.delta_7d != null && data.delta_7d < 0;

  return (
    <div className={`rounded-2xl border border-slate-200 dark:border-slate-700 bg-gradient-to-br ${c.bg} p-5 mb-4`} data-testid="ai-health-score">
      <div className="flex items-center gap-2 mb-4">
        <Activity className={`w-5 h-5 ${c.text}`} />
        <div className="font-semibold text-base">AI Health Score</div>
        <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-white/70 dark:bg-black/30 ${c.text}`}>{data.grade}</span>
        {data.delta_7d != null && (
          <span className={`text-xs font-semibold inline-flex items-center gap-1 ${deltaUp ? "text-emerald-600 dark:text-emerald-400" : deltaDown ? "text-red-600 dark:text-red-400" : "text-slate-500"}`} data-testid="health-delta">
            {deltaUp && <TrendingUp className="w-3.5 h-3.5" />}
            {deltaDown && <TrendingDown className="w-3.5 h-3.5" />}
            {data.delta_7d > 0 ? "+" : ""}{data.delta_7d} pp 7z
          </span>
        )}
        <button
          onClick={load}
          className="ml-auto p-1.5 rounded-lg hover:bg-white/40 dark:hover:bg-black/30 text-slate-500"
          aria-label="Reîncarcă"
          data-testid="health-refresh"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="grid lg:grid-cols-[160px,1fr] gap-5 items-center">
        <div className="flex justify-center lg:justify-start">
          <ScoreRing score={data.overall} color={data.color} />
        </div>
        <div className="space-y-3">
          <div className="grid sm:grid-cols-3 gap-2.5">
            <SubScore
              icon={AlertTriangle}
              label="Findings"
              score={m.findings.score}
              color={m.findings.score >= 75 ? "emerald" : m.findings.score >= 60 ? "amber" : "red"}
              detail={findingsDetail}
              weight={m.findings.weight}
            />
            <SubScore
              icon={Wrench}
              label="Repair eficacitate"
              score={m.effectiveness.score}
              color={m.effectiveness.score >= 75 ? "emerald" : m.effectiveness.score >= 60 ? "amber" : "red"}
              detail={effDetail}
              weight={m.effectiveness.weight}
            />
            <SubScore
              icon={MessageSquare}
              label="Concierge"
              score={m.concierge.score}
              color={m.concierge.score >= 75 ? "emerald" : m.concierge.score >= 60 ? "amber" : "red"}
              detail={concDetail}
              weight={m.concierge.weight}
            />
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white/50 dark:bg-slate-900/30">
            <div className="flex items-center gap-1.5 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400">Trend 14 zile</span>
            </div>
            <Sparkline data={data.trend} color={c.ring} />
            <div className="text-[10px] text-slate-400 italic mt-1">
              {data.trend.length} {data.trend.length === 1 ? "punct" : "puncte"} înregistrate · scor zilnic stocat automat
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIHealthScore;
