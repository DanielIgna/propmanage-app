// Cost & ROI Tracker — quantifies the value of Autopilot on admin time saved.
// Shows hours saved + money saved (RON) + per-source breakdown.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Coins, Clock, TrendingUp, RefreshCw, Sparkles } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const SOURCE_ICONS = {
  auto_tune_runs: "✨",
  daily_sweep_runs: "🧹",
  auto_matched_requests: "🎯",
  auto_resolved_qa_findings: "🐛",
  auto_approved_kyc: "🪪",
  ai_top_match_notifications: "🔔",
};

const formatRON = (n) =>
  new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(n || 0);

export const CostRoiCard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);

  const load = async (windowDays = days) => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/autonomy/roi`, {
        params: { days: windowDays },
      });
      setData(r.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(days);
  }, [days]);

  return (
    <AdminCard
      testid="cost-roi-card"
      title={
        <div className="flex items-center gap-2">
          <Coins className="w-4 h-4 text-emerald-500" />
          <span>Cost &amp; ROI Tracker</span>
          <span className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-normal">
            economii Autopilot
          </span>
        </div>
      }
      action={
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value, 10))}
            className="text-[11px] px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none"
            data-testid="cost-roi-window"
          >
            <option value={7}>7 zile</option>
            <option value={30}>30 zile</option>
            <option value={90}>90 zile</option>
            <option value={365}>1 an</option>
          </select>
          <button
            onClick={() => load(days)}
            disabled={loading}
            className="text-[11px] px-2 py-1 rounded-md text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 disabled:opacity-50 inline-flex items-center gap-1"
            data-testid="cost-roi-refresh"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      }
    >
      {!data && loading && (
        <div className="text-xs text-slate-500 py-4">Se calculează...</div>
      )}
      {!data && !loading && (
        <div className="text-xs text-slate-500 italic py-4">
          Nu pot calcula ROI — verifică /api/admin/autonomy/roi.
        </div>
      )}
      {data && (
        <>
          {/* Hero KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <div
              className="rounded-xl p-4 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/30"
              data-testid="cost-roi-money"
            >
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 font-bold">
                <Coins className="w-3 h-3" /> Bani economisiți
              </div>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 tabular-nums">
                {formatRON(data.money_saved_ron)} RON
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                la rata {formatRON(data.hourly_rate_ron)} RON/h admin
              </div>
            </div>

            <div
              className="rounded-xl p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border border-cyan-500/30"
              data-testid="cost-roi-hours"
            >
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-cyan-700 dark:text-cyan-300 font-bold">
                <Clock className="w-3 h-3" /> Timp salvat
              </div>
              <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400 mt-1 tabular-nums">
                {data.hours_saved}h
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                ≈ {Math.round(data.hours_saved / 8)} zile lucru admin
              </div>
            </div>

            <div
              className="rounded-xl p-4 bg-gradient-to-br from-fuchsia-500/10 to-violet-500/5 border border-fuchsia-500/30"
              data-testid="cost-roi-events"
            >
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-fuchsia-700 dark:text-fuchsia-300 font-bold">
                <Sparkles className="w-3 h-3" /> Evenimente automate
              </div>
              <div className="text-2xl font-bold text-fuchsia-600 dark:text-fuchsia-400 mt-1 tabular-nums">
                {data.breakdown.reduce((sum, b) => sum + (b.count || 0), 0)}
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                în ultimele {data.window_days} zile
              </div>
            </div>
          </div>

          {/* Per-source breakdown */}
          <div className="space-y-1.5" data-testid="cost-roi-breakdown">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-1.5 flex items-center gap-1.5">
              <TrendingUp className="w-3 h-3" />
              Defalcare pe surse automate
            </div>
            {data.breakdown.map((b, i) => {
              const pct = data.total_minutes_saved > 0
                ? Math.round((b.minutes_total / data.total_minutes_saved) * 100)
                : 0;
              return (
                <div
                  key={b.source}
                  className="flex items-center gap-3 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                  data-testid={`cost-roi-row-${b.source}`}
                >
                  <span className="text-base">{SOURCE_ICONS[b.source] || "•"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] text-slate-700 dark:text-slate-200 truncate">{b.label}</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">
                      {b.count} × {b.minutes_per_event}min
                    </div>
                  </div>
                  <div className="w-20 hidden md:block">
                    <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                      <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  <div className="text-right tabular-nums w-24 shrink-0">
                    <div className="text-[12px] font-bold text-slate-700 dark:text-slate-200">
                      {Math.round(b.minutes_total / 60 * 10) / 10}h
                    </div>
                    <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                      {formatRON((b.minutes_total / 60) * data.hourly_rate_ron)} RON
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-200/60 dark:border-slate-700/50 text-[10px] text-slate-500 dark:text-slate-400">
            💡 Estimări conservatoare: 5min/cerere auto-matched · 15min/KYC auto-aprobat · 30min/Auto-Tune.
            Configurabil prin <code>?hourly_rate=</code>.
          </div>
        </>
      )}
    </AdminCard>
  );
};

export default CostRoiCard;
