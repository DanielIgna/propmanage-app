// Specialist verification queue + Disputes & nonconformities — reuses existing modals
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Eye, Scale, Clock, AlertTriangle, Flag, Sparkles } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { SpecialistDetailModal, DisputeResolveModal } from "../AdminModals";
import { RequestTimelineModal } from "../ActivityTimeline";
import { API } from "../DashShared";

export const AdminVerification = () => {
  const [pending, setPending] = useState([]);
  const [detailId, setDetailId] = useState(null);

  const load = () => axios.get(`${API}/admin/specialists/pending`).then(r => setPending(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  return (
    <AdminCard title={`Coadă verificare specialiști (${pending.length})`} testid="verification-queue-card">
      {pending.length === 0 && <div className="text-center py-12 text-slate-500 text-sm" data-testid="empty-verification">Niciun specialist în așteptare</div>}
      <div className="space-y-2">
        {pending.map(p => (
          <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30" data-testid={`pending-${p.id}`}>
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center text-white font-medium">{p.name?.[0]}</div>
              <div className="min-w-0">
                <div className="font-medium text-sm">{p.name}</div>
                <div className="text-xs text-slate-500">{p.email} · {p.specialty || "Specialist"} · {(p.documents || []).length} docs</div>
              </div>
            </div>
            <AdminBtn onClick={() => setDetailId(p.id)} data-testid={`review-spec-${p.id}`}>
              <Eye className="w-3.5 h-3.5 inline mr-1" /> Analizează
            </AdminBtn>
          </div>
        ))}
      </div>
      {detailId && <SpecialistDetailModal specialistId={detailId} onClose={() => setDetailId(null)} onChange={load} />}
    </AdminCard>
  );
};

export const AdminDisputes = () => {
  const [disputes, setDisputes] = useState([]);
  const [ncs, setNcs] = useState([]);
  const [resolveDispute, setResolveDispute] = useState(null);
  const [resolveNC, setResolveNC] = useState(null);
  const [timelineId, setTimelineId] = useState(null);

  const load = () => {
    axios.get(`${API}/admin/disputes`).then(r => setDisputes(r.data));
    axios.get(`${API}/admin/nonconformities`).then(r => setNcs(r.data)).catch(() => setNcs([]));
  };
  useEffect(() => { load(); }, []);

  const openDisputes = disputes.filter(d => d.status === "open");
  const openNC = ncs.filter(n => n.status === "open");

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <AdminBtn variant="secondary" onClick={() => window.open(`${API}/admin/export/disputes.csv`, "_blank")} data-testid="export-disputes">
          Export Dispute CSV
        </AdminBtn>
      </div>

      {openNC.length > 0 && (
        <AdminCard title={`Sesizări Operator (${openNC.length})`} testid="nc-card">
          <div className="space-y-2">
            {openNC.map(n => (
              <div key={n.id} className="p-3 rounded-lg border border-orange-200 dark:border-orange-500/30 bg-orange-50 dark:bg-orange-500/5" data-testid={`nc-${n.id}`}>
                <div className="flex items-center gap-2 mb-1.5 text-xs">
                  <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full ${
                    n.severity === "high" ? "bg-red-100 text-red-700" :
                    n.severity === "medium" ? "bg-amber-100 text-amber-700" :
                    "bg-slate-100 text-slate-700"
                  }`}>{n.severity}</span>
                  <span className="font-medium">{n.operator_name}</span>
                  <span className="text-slate-500">· {n.target_type}</span>
                </div>
                <div className="text-sm italic text-slate-700 dark:text-slate-300 mb-2">"{n.reason}"</div>
                <div className="flex gap-2">
                  {n.related_request_id && (
                    <AdminBtn variant="secondary" onClick={() => setTimelineId(n.related_request_id)}>
                      <Clock className="w-3 h-3 inline mr-1" /> Timeline
                    </AdminBtn>
                  )}
                  <AdminBtn variant="primary" onClick={() => setResolveNC(n)} data-testid={`nc-resolve-${n.id}`}>
                    <Scale className="w-3 h-3 inline mr-1" /> Rezolvă
                  </AdminBtn>
                </div>
              </div>
            ))}
          </div>
        </AdminCard>
      )}

      <AdminCard title={`Dispute deschise (${openDisputes.length})`} testid="disputes-open-card">
        {openDisputes.length === 0 && <div className="text-center py-10 text-slate-500 text-sm" data-testid="no-open-disputes">Nicio dispută deschisă</div>}
        <div className="space-y-2">
          {openDisputes.map(d => (
            <div key={d.id} className="p-3 rounded-lg border border-slate-200 dark:border-slate-800" data-testid={`dispute-${d.id}`}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{d.request_title || "Lucrare necunoscută"}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Deschis de {d.opened_by_role} · Client: {d.client_name || "—"} · Specialist: {d.specialist_name || "—"}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">Escrow</div>
                  <div className="font-bold text-amber-600 dark:text-amber-400">{(d.escrow_amount || 0).toFixed(0)} RON</div>
                </div>
              </div>
              <div className="text-sm italic text-slate-600 dark:text-slate-300 mb-3 line-clamp-2">"{d.reason}"</div>
              {d.ai_triage && (
                <div className="mb-3 p-3 rounded-lg bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/25" data-testid={`ai-triage-${d.id}`}>
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-violet-500" />
                    <span className="text-xs font-bold text-violet-700 dark:text-violet-300">Triage AI</span>
                    <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300">{d.ai_triage.category}</span>
                    <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded ${
                      d.ai_triage.severity === "high" ? "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300" :
                      d.ai_triage.severity === "medium" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" :
                      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    }`}>{d.ai_triage.severity}</span>
                    {d.ai_triage.suggested_split?.client_pct !== undefined && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300">
                        split propus: {d.ai_triage.suggested_split.client_pct}% client / {d.ai_triage.suggested_split.specialist_pct}% specialist
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-700 dark:text-slate-300"><strong>Propunere:</strong> {d.ai_triage.proposed_resolution}</div>
                  {(d.ai_triage.arguments || []).length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {d.ai_triage.arguments.map((a, i) => (
                        <li key={i} className="text-[11px] text-slate-500 dark:text-slate-400">• {a}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              <div className="flex gap-2">
                <AdminBtn variant="secondary" onClick={() => setTimelineId(d.request_id)}>
                  <Clock className="w-3 h-3 inline mr-1" /> Timeline
                </AdminBtn>
                <AdminBtn variant="primary" onClick={() => setResolveDispute(d)} data-testid={`resolve-${d.id}`}>
                  <Scale className="w-3 h-3 inline mr-1" /> Mediere
                </AdminBtn>
              </div>
            </div>
          ))}
        </div>
      </AdminCard>

      {disputes.length - openDisputes.length > 0 && (
        <AdminCard title={`Istoric rezolvate (${disputes.length - openDisputes.length})`}>
          <div className="space-y-1.5">
            {disputes.filter(d => d.status === "resolved").slice(0, 10).map(d => (
              <div key={d.id} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between text-sm">
                <div className="min-w-0">
                  <div className="font-medium truncate">{d.request_title}</div>
                  <div className="text-[11px] text-slate-500">{d.resolution} · Client: {(d.client_amount || 0).toFixed(0)} RON · Specialist: {(d.specialist_amount || 0).toFixed(0)} RON</div>
                </div>
                <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">Rezolvată</span>
              </div>
            ))}
          </div>
        </AdminCard>
      )}

      {resolveDispute && <DisputeResolveModal dispute={resolveDispute} onClose={() => setResolveDispute(null)} onResolved={load} />}
      {resolveNC && <NCResolveModal nc={resolveNC} onClose={() => setResolveNC(null)} onResolved={load} />}
      {timelineId && <RequestTimelineModal requestId={timelineId} onClose={() => setTimelineId(null)} />}
    </div>
  );
};

const NCResolveModal = ({ nc, onClose, onResolved }) => {
  const [resolution, setResolution] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/admin/nonconformities/${nc.id}/resolve`, { resolution });
      onResolved?.();
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || "Eroare.");
    } finally { setLoading(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6" onClick={e => e.stopPropagation()} data-testid="nc-resolve-modal">
        <h3 className="text-lg font-semibold mb-3">Rezolvă sesizare</h3>
        <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-500/10 border border-orange-200 dark:border-orange-500/30 text-xs mb-4">
          <div className="font-medium mb-1">{nc.operator_name} ({nc.severity})</div>
          <div className="italic">"{nc.reason}"</div>
        </div>
        <form onSubmit={submit}>
          <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Rezoluție</label>
          <textarea required minLength={3} rows={5} value={resolution} onChange={e => setResolution(e.target.value)}
            placeholder="Descrie acțiunea luată..."
            className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="nc-resolution" />
          <div className="flex gap-2 mt-4">
            <AdminBtn variant="secondary" type="button" onClick={onClose}>Anulează</AdminBtn>
            <AdminBtn type="submit" disabled={loading} data-testid="nc-resolve-submit">{loading ? "..." : "Salvează"}</AdminBtn>
          </div>
        </form>
      </div>
    </div>
  );
};
