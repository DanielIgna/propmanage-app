import React from "react";
import { ShieldCheck, Target, Star, ChevronRight, CircleCheck, Circle } from "lucide-react";
import { PMCard, PMPillButton, PMChip, PMEmptyState } from "../../components/pm";

// ============================================================================
// Specialist Entry Home — UX Lab. Experiență simplificată pentru tier ENTRY:
// 3 pași clari + oportunități cu un singur CTA. Reversibil (switch full).
// ============================================================================

const StepRow = ({ done, label, action, onAction, testid }) => (
  <div className="flex items-center gap-3 py-2.5" data-testid={testid}>
    {done
      ? <CircleCheck className="w-5 h-5 text-[var(--pm-primary)] shrink-0" aria-hidden="true" />
      : <Circle className="w-5 h-5 text-stone-600 shrink-0" aria-hidden="true" />}
    <span className={`flex-1 text-sm ${done ? "text-stone-500 line-through" : "font-semibold"}`}>{label}</span>
    {!done && action && (
      <PMPillButton variant="ghost" size="sm" className="min-h-[44px]" onClick={onAction} testid={`${testid}-action`}>{action}</PMPillButton>
    )}
  </div>
);

export const SpecialistEntryHome = ({ user, open, mine, onAccept, onVerify, onGoJobs, onSwitchFull }) => {
  const hasJob = mine.length > 0;
  const hasDone = mine.some(r => r.status === "confirmed" || r.status === "completed");
  const doneCount = [!!user?.verified, hasJob, hasDone].filter(Boolean).length;
  const topOpen = open.slice(0, 5);
  return (
    <div className="max-w-2xl lg:max-w-5xl mx-auto pm-fade-in" data-testid="spec-entry-home">
      <div className="lg:grid lg:grid-cols-[1fr_1.2fr] lg:gap-10 lg:items-start">
      <div className="space-y-8">
      <div>
        <h2 className="xos-display text-3xl lg:text-4xl font-light tracking-tight">Salut, <span className="font-medium">{user?.name?.split(" ")[0] || "specialist"}</span>!</h2>
        <p className="text-sm text-stone-400 mt-1.5">Hai să obții prima lucrare. Doar 3 pași.</p>
      </div>

      <PMCard testid="spec-entry-checklist">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] font-bold uppercase tracking-[0.18em] flex items-center gap-2" style={{ color: "var(--pm-text-variant)" }}>
            <ShieldCheck className="w-4 h-4 text-[var(--pm-primary)]" aria-hidden="true" /> Primii tăi pași
          </h3>
          <span className="text-[11px] font-black text-[var(--pm-primary)]" data-testid="spec-entry-progress-badge">{doneCount}/3 completat</span>
        </div>
        <div className="h-1 rounded-full bg-white/10 mb-2" role="progressbar" aria-valuenow={doneCount} aria-valuemin={0} aria-valuemax={3}>
          <div className="h-full rounded-full bg-[var(--pm-primary)] transition-all duration-300" style={{ width: `${(doneCount / 3) * 100}%` }} />
        </div>
        <div className="divide-y divide-white/5">
          <StepRow done={!!user?.verified} label="Verifică-ți contul (badge VERIFIED)" action="Începe" onAction={onVerify} testid="spec-entry-step-verify" />
          <StepRow done={hasJob} label="Acceptă prima oportunitate" testid="spec-entry-step-first-job" />
          <StepRow done={hasDone} label="Finalizează lucrarea și ia prima recenzie" action={hasJob ? "Vezi lucrarea" : null} onAction={onGoJobs} testid="spec-entry-step-review" />
        </div>
      </PMCard>

      <aside role="complementary" aria-label="Progres către nivelul următor" className="flex items-center justify-between pt-2">
        <span className="text-xs text-stone-500 flex items-center gap-1.5">
          <Star className="w-3.5 h-3.5" aria-hidden="true" /> La 3 lucrări finalizate urci la nivelul următor
        </span>
        <button onClick={onSwitchFull} data-testid="spec-entry-switch-full"
          aria-describedby="spec-entry-adv-hint"
          className="text-xs font-semibold text-stone-400 hover:text-white flex items-center gap-1.5 min-h-[44px] transition-colors">
          <span id="spec-entry-adv-hint" className="sr-only">Statistici, rapoarte, filtre și setări avansate</span>
          <span className="text-[9px] font-black uppercase tracking-wide bg-white/10 text-stone-400 rounded-full px-2 py-0.5">Avansat</span>
          Dashboard complet <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
      </aside>
      </div>

      <div data-testid="spec-entry-opportunities" aria-live="polite" className="mt-8 lg:mt-0">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.18em] mb-3 flex items-center gap-2" style={{ color: "var(--pm-text-variant)" }}>
          <Target className="w-4 h-4 text-[var(--pm-primary)]" aria-hidden="true" /> Oportunități pentru tine
        </h3>
        {topOpen.length === 0 ? (
          <PMEmptyState icon={Target} title="Nicio oportunitate acum"
            description="Primești o notificare imediat ce apare o lucrare în zona ta." />
        ) : (
          <div className="space-y-3">
            {topOpen.map((r, i) => (
              <div key={r.id} className="cj-reveal" style={{ animationDelay: `${i * 0.04}s` }}>
              <PMCard accent={r.priority === "urgent" ? "urgent" : "default"} className="transition-transform duration-300 hover:-translate-y-0.5" testid={`spec-entry-opp-${r.id}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    {r.priority === "urgent" && <PMChip variant="error" className="mb-1">URGENT</PMChip>}
                    <div className="font-semibold text-sm truncate">{r.title}</div>
                    <div className="text-xs text-stone-400 mt-1">Estimat: <span className="font-mono font-semibold text-white">{r.budget_estimate} RON</span></div>
                  </div>
                  <PMPillButton variant="primary" onClick={() => onAccept(r)} testid={`spec-entry-accept-${r.id}`}>
                    Acceptă
                  </PMPillButton>
                </div>
              </PMCard>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
};
