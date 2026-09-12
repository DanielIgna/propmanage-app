import React from "react";
import { useNavigate } from "react-router-dom";
import { ClipboardList, MessageSquare, Clock, CreditCard, Star, AlertTriangle, CircleCheck, ChevronRight } from "lucide-react";
import { GREEN, CTA, Steps, stepForStatus, StatusChip } from "./ui";

export const JobsV2 = ({ requests, actions }) => {
  const navigate = useNavigate();
  const active = requests.filter(r => r.status !== "confirmed");
  const history = requests.filter(r => r.status === "confirmed");

  if (requests.length === 0) {
    return (
      <div className="px-6 py-16 text-center" data-testid="v2-jobs-empty">
        <ClipboardList className="w-10 h-10 mx-auto text-slate-300" />
        <h2 className="mt-3 text-lg font-black text-slate-900">Nicio lucrare încă</h2>
        <p className="mt-1 text-sm text-slate-400">Solicită primul serviciu — durează 1 minut.</p>
        <div className="mt-5 max-w-[240px] mx-auto"><CTA testid="v2-jobs-empty-cta" onClick={actions.openWizard}>Solicită un serviciu</CTA></div>
      </div>
    );
  }

  const Card = ({ r }) => (
    <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid={`v2-job-${r.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-black text-slate-900 truncate">{r.title}</div>
          <div className="text-[10px] text-slate-400">{r.category} · {r.priority}{r.specialist_name ? ` · ${r.specialist_name}` : ""}</div>
        </div>
        <StatusChip status={r.status} />
      </div>
      {r.status !== "confirmed" && <div className="mt-3"><Steps current={stepForStatus(r.status)} /></div>}
      <div className="mt-3 space-y-2">
        {r.status === "open" && (
          <CTA testid={`v2-job-offers-${r.id}`} onClick={() => navigate(`/client/requests/${r.id}/offers`)}>Vezi ofertele</CTA>
        )}
        {r.status === "assigned" && !r.escrow_amount && (
          <CTA testid={`v2-job-pay-${r.id}`} onClick={() => actions.payEscrow(r.id)}><CreditCard className="w-4 h-4 inline mr-1 -mt-0.5" />Plătește avansul (escrow)</CTA>
        )}
        {r.status === "completed" && (
          <CTA testid={`v2-job-confirm-${r.id}`} onClick={() => actions.confirmRequest(r.id, r)}>Confirmă & eliberează plata</CTA>
        )}
        {r.status === "confirmed" && r.specialist_id && (
          <CTA subtle testid={`v2-job-review-${r.id}`} onClick={() => actions.setReviewFor(r)}><Star className="w-4 h-4 inline mr-1 -mt-0.5" style={{ color: GREEN }} />Evaluează specialistul</CTA>
        )}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {r.specialist_id && ["assigned", "in_progress", "completed"].includes(r.status) ? (
          <button onClick={() => actions.setChatRequest(r.id)} data-testid={`v2-job-chat-${r.id}`} className="py-2 rounded-full bg-slate-50 text-[11px] font-bold text-slate-600 flex items-center justify-center gap-1"><MessageSquare className="w-3.5 h-3.5" />Chat</button>
        ) : <span />}
        <button onClick={() => actions.setTimelineRequestId(r.id)} data-testid={`v2-job-timeline-${r.id}`} className="py-2 rounded-full bg-slate-50 text-[11px] font-bold text-slate-600 flex items-center justify-center gap-1"><Clock className="w-3.5 h-3.5" />Timeline</button>
        {r.specialist_id && ["assigned", "in_progress", "completed"].includes(r.status) && !r.disputed ? (
          <button onClick={() => actions.setDisputeFor(r)} data-testid={`v2-job-dispute-${r.id}`} className="py-2 rounded-full bg-slate-50 text-[11px] font-bold text-amber-600 flex items-center justify-center gap-1"><AlertTriangle className="w-3.5 h-3.5" />Problemă</button>
        ) : <span />}
      </div>
      {r.disputed && <div className="mt-2 text-center text-[11px] font-bold text-amber-600 bg-amber-50 rounded-full py-2">⚠ Dispută în analiză</div>}
    </div>
  );

  return (
    <div className="px-5 pb-8 space-y-3 cv2-fade" data-testid="v2-jobs-view">
      {active.length > 0 && <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 px-1">Active ({active.length})</h3>}
      {active.map(r => <Card key={r.id} r={r} />)}
      {history.length > 0 && (
        <>
          <h3 className="pt-3 text-[11px] font-black uppercase tracking-wider text-slate-400 px-1">Istoric ({history.length})</h3>
          {history.map(r => (
            <button key={r.id} onClick={() => actions.setTimelineRequestId(r.id)} data-testid={`v2-job-hist-${r.id}`}
              className="w-full flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm text-left">
              <CircleCheck className="w-5 h-5 shrink-0" style={{ color: GREEN }} />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-slate-900 truncate">{r.title}</div>
                <div className="text-[10px] text-slate-400">finalizat{r.specialist_name ? ` · ${r.specialist_name}` : ""}</div>
              </div>
              {r.specialist_id && (
                <span onClick={(e) => { e.stopPropagation(); actions.setReviewFor(r); }} className="text-[10px] font-bold px-2 py-1 rounded-full bg-slate-50 text-slate-500 flex items-center gap-1"><Star className="w-3 h-3" style={{ color: GREEN }} />Evaluează</span>
              )}
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
          ))}
        </>
      )}
    </div>
  );
};
