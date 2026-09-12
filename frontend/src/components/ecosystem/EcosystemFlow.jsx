// EcosystemFlow — fluxul canonic unic (Audit → ... → House Health), identic pe toate paginile.
// Sursă: canonical_flow din /interior-design/content (o singură sursă de adevăr).
import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useEcosystemContent } from "./useEcosystemContent";
import { useServiceVisibility, isServiceEnabled } from "../serviceVisibility";

// Pașii din flux care depind de un serviciu gestionat în Service Manager
const STEP_SERVICE = { specialists: "specialisti" };

export const EcosystemFlow = ({ dark = false, activeKey = null, compact = false }) => {
  const content = useEcosystemContent();
  const services = useServiceVisibility();
  const flow = content?.canonical_flow;
  if (!flow) return null;
  const chip = dark
    ? "bg-white/5 border-white/10 text-stone-200 hover:border-[#d4ff3a]/60 hover:text-white"
    : "bg-stone-50 border-stone-200 text-stone-700 hover:border-emerald-400 hover:text-emerald-900";
  const done = dark
    ? "bg-[#d4ff3a]/10 border-[#d4ff3a]/30 text-[#d4ff3a]/80"
    : "bg-emerald-50 border-emerald-200 text-emerald-700";
  const active = dark
    ? "bg-[#d4ff3a] border-[#d4ff3a] text-black font-black"
    : "bg-emerald-700 border-emerald-700 text-white font-black";
  const arrow = dark ? "text-[#d4ff3a]" : "text-emerald-600";
  const activeIdx = flow.steps.findIndex((s) => s.key === activeKey);
  return (
    <div data-testid="ecosystem-flow">
      {!compact && (
        <>
          <h3 className={`text-lg sm:text-xl font-black ${dark ? "text-white" : "text-stone-900"}`}>{flow.title}</h3>
          <p className={`mt-1 mb-4 text-sm ${dark ? "text-stone-400" : "text-stone-500"}`}>{flow.tagline}</p>
        </>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        {flow.steps.map((s, i) => {
          const svcId = STEP_SERVICE[s.key];
          const gated = svcId && !isServiceEnabled(services, svcId);
          const isDone = activeIdx > -1 && i < activeIdx;
          const cls = `px-2.5 py-1.5 rounded-full border text-[11px] font-bold transition-colors ${
            s.key === activeKey ? active : isDone ? done : chip}`;
          const label = isDone ? `✓ ${s.label}` : s.label;
          return (
            <React.Fragment key={s.key}>
              {gated ? (
                <span title={s.desc} className={`${cls} cursor-default`} data-testid={`eco-flow-${s.key}`}>{label}</span>
              ) : (
                <Link to={s.href} title={s.desc} className={cls} data-testid={`eco-flow-${s.key}`}>{label}</Link>
              )}
              {i < flow.steps.length - 1 && <ArrowRight className={`w-3 h-3 shrink-0 ${arrow}`} />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
