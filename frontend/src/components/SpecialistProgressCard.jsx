// PPOS P3a-M4 — THE single progress system for specialists.
// Derives everything from real account state (canonical user.tier + live data).
// Replaces: GettingStartedWidget + WelcomeChecklist + TierToolsPanel locked list + TierProgressWidget.
import React from "react";
import { Link } from "react-router-dom";
import { Trophy, ArrowRight, Unlock } from "lucide-react";
import { getNextTierProgress } from "../lib/tierProgression";
import { PMChip, PMProgress } from "./pm";

export const SpecialistProgressCard = ({ user, mine = [], onGoLeads, className = "" }) => {
  if (!user || user === false) return null;
  const progress = getNextTierProgress(user);

  const steps = [];
  if (!(user.service_categories || []).length) {
    steps.push({ id: "services", label: "Configurează serviciile pe care le stăpânești", to: "/specialist/capabilities" });
  }
  if ((mine || []).length === 0 && !(user.jobs_completed > 0)) {
    steps.push({ id: "first-job", label: "Acceptă prima oportunitate", onClick: onGoLeads });
  }
  const visibleSteps = steps.slice(0, 2);

  if (!progress && visibleSteps.length === 0) return null;

  const pending = progress?.requirements?.find((r) => !r.done);

  return (
    <div className={`pm-card !p-4 ${className}`} data-testid="spec-progress-card">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-[var(--pm-surface-high)] text-[var(--pm-primary)] flex items-center justify-center shrink-0">
          <Trophy className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-[var(--pm-text)]">Progresul tău</div>
          <div className="text-xs text-stone-400 flex items-center gap-1.5 flex-wrap">
            Nivel actual: <PMChip variant="primary" testid="spec-progress-tier">{user.tier || "ENTRY"}</PMChip>
            {progress && <span>→ {progress.nextTier}</span>}
          </div>
        </div>
      </div>

      {progress && (
        <div className="mt-2">
          <PMProgress value={progress.overallPct} showValue testid="spec-progress-bar" />
          <div className="mt-1.5 text-xs text-stone-400" data-testid="spec-progress-pending">
            {pending ? `Următoarea cerință: ${pending.label} (${pending.current.toFixed(pending.min < 10 ? 1 : 0)}/${pending.min})` : "Toate cerințele îndeplinite — promovare automată în curând!"}
          </div>
        </div>
      )}

      {visibleSteps.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {visibleSteps.map((s) => (
            <div key={s.id} className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2" data-testid={`spec-progress-step-${s.id}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--pm-primary)] shrink-0" />
              <span className="text-xs text-stone-200 flex-1">{s.label}</span>
              {s.to ? (
                <Link to={s.to} className="text-xs font-semibold text-[var(--pm-primary)] inline-flex items-center gap-0.5" data-testid={`spec-progress-go-${s.id}`}>
                  Mergi <ArrowRight className="w-3 h-3" />
                </Link>
              ) : (
                <button onClick={s.onClick} className="text-xs font-semibold text-[var(--pm-primary)] inline-flex items-center gap-0.5" data-testid={`spec-progress-go-${s.id}`}>
                  Mergi <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {progress?.unlocks?.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-white/5 text-[11px] text-stone-400 flex items-center gap-1.5" data-testid="spec-progress-next-unlock">
          <Unlock className="w-3 h-3 text-[var(--pm-primary)] shrink-0" />
          Următoarea deblocare: <span className="text-stone-200 font-medium">{progress.unlocks[0]}</span> — la nivelul {progress.nextTier}
        </div>
      )}
    </div>
  );
};

export default SpecialistProgressCard;
