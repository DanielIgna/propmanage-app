// Specialist Cockpit v1 (Blueprint Phase 3) — Pipeline & Bani + benchmark + Business Assistant
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Target, Send, CheckCircle2, Wallet, TrendingUp, TrendingDown, Sparkles, ArrowRight, Scale } from "lucide-react";
import { API } from "./DashShared";
import { CARD, DSBadge } from "../design-system";

export const SpecialistCockpit = ({ onGo }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    axios.get(`${API}/specialist/cockpit`).then(r => setData(r.data)).catch(() => {});
  }, []);

  if (!data) return null;
  const { pipeline: p, money: m, benchmark: b, assistant_actions: acts } = data;
  const TrendIcon = (m.trend_pct ?? 0) >= 0 ? TrendingUp : TrendingDown;

  return (
    <div className="mb-6 pm-fade-in" data-testid="spec-cockpit">
      {/* Pipeline & Bani */}
      <div className={`${CARD} p-4`}>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100">Pipeline & Bani</h3>
          <DSBadge type="NEW">Cockpit</DSBadge>
          {b && (
            <span className="ml-auto flex items-center gap-1 text-[11px] text-slate-400" data-testid="spec-benchmark">
              <Scale className="w-3.5 h-3.5" />
              Piața ({b.category}): {b.mid_avg ?? "—"}–{b.expert_avg ?? "—"} lei/{b.unit}
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            [Target, "Lead-uri pe categoria ta", p.leads_matched, "opportunities", "spec-pipe-leads"],
            [Send, "Lucrări în derulare", p.offers_active, "jobs", "spec-pipe-active"],
            [CheckCircle2, "Finalizate luna asta", p.done_this_month, "jobs", "spec-pipe-done"],
          ].map(([Icon, label, val, cta, tid]) => (
            <button key={tid} onClick={() => onGo(cta)} data-testid={tid}
              className="text-left rounded-xl p-3 bg-slate-50 dark:bg-white/[0.04] hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors">
              <Icon className="w-4 h-4 text-slate-400" />
              <div className="mt-1.5 xos-num text-3xl text-slate-900 dark:text-white leading-none">{val}</div>
              <div className="mt-1 text-[10px] font-bold uppercase text-slate-400 leading-tight">{label}</div>
            </button>
          ))}
          <div className="rounded-xl p-3 bg-[#ccff00]/10 border border-[#ccff00]/25" data-testid="spec-pipe-money">
            <Wallet className="w-4 h-4" style={{ color: "var(--pm-accent-ink, #3f6212)" }} />
            <div className="mt-1.5 xos-num text-3xl text-slate-900 dark:text-white leading-none">{m.this_month.toLocaleString("ro")} <span className="text-xs font-bold">RON</span></div>
            <div className="mt-1 text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1">
              luna aceasta
              {m.trend_pct !== null && (
                <span className={`flex items-center gap-0.5 normal-case ${m.trend_pct >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  <TrendIcon className="w-3 h-3" />{m.trend_pct > 0 ? "+" : ""}{m.trend_pct}%
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Business Assistant — „Cum câștigi mai mult luna asta?" */}
      <div className={`${CARD} border-violet-200 dark:border-violet-500/30 p-4 mt-4`} data-testid="spec-assistant">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-violet-50 dark:bg-violet-500/15">
            <Sparkles className="w-4 h-4 text-violet-600 dark:text-violet-400" />
          </span>
          <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100">Business Assistant</h3>
          <span className="text-[11px] text-slate-400">Cum câștigi mai mult luna asta?</span>
        </div>
        <div className="space-y-2">
          {acts.map((a, i) => (
            <button key={i} onClick={() => onGo(a.cta)} data-testid={`spec-assistant-action-${a.kind}`}
              className="w-full flex items-start gap-2 text-left rounded-xl px-3 py-2.5 bg-slate-50 dark:bg-white/[0.04] hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 shrink-0" />
              <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{a.text}</span>
              <ArrowRight className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
