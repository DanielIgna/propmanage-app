// Admin-specific modals: Specialist Documents Review, Dispute Resolve, Open Dispute
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { FileCheck, X, AlertTriangle, Scale, CheckCircle2, XCircle, FileText, Camera, Trash2 } from "lucide-react";
import { formatApiError } from "../auth";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const DOC_TYPE_LABELS = {
  id_card: "Carte de identitate",
  insurance: "Asigurare",
  certification: "Certificare profesională",
  company_cui: "CUI Firmă",
  other: "Alt document",
};

const STATUS_COLORS = {
  approved: "text-emerald-400 bg-emerald-500/15 border-emerald-500/30",
  rejected: "text-red-400 bg-red-500/15 border-red-500/30",
  pending: "text-amber-400 bg-amber-500/15 border-amber-500/30",
};

// ============= SPECIALIST DETAIL & DOCUMENTS REVIEW =============
export const SpecialistDetailModal = ({ specialistId, onClose, onChange }) => {
  const [spec, setSpec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [rejectMode, setRejectMode] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [docRejectFor, setDocRejectFor] = useState(null);
  const [docRejectReason, setDocRejectReason] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/specialists/${specialistId}`);
      setSpec(data);
    } catch (e) { /* noop */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [specialistId]);

  const verify = async () => {
    try {
      await axios.post(`${API}/admin/specialists/${specialistId}/verify`);
      onChange?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
  };

  const reject = async () => {
    if (rejectReason.trim().length < 3) return alert("Motivul trebuie să aibă cel puțin 3 caractere");
    try {
      await axios.post(`${API}/admin/specialists/${specialistId}/reject`, { reason: rejectReason });
      onChange?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
  };

  const reviewDoc = async (docId, status, reason = null) => {
    try {
      await axios.post(`${API}/admin/specialists/${specialistId}/documents/${docId}/review`, { status, reason });
      await load();
      setDocRejectFor(null);
      setDocRejectReason("");
    } catch (e) { alert(formatApiError(e)); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="specialist-detail-modal">
        {loading || !spec ? (
          <div className="text-center text-stone-400 py-8">Se încarcă...</div>
        ) : (
          <>
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-stone-600 to-stone-800 flex items-center justify-center font-medium text-lg">
                  {spec.name?.[0] || "S"}
                </div>
                <div>
                  <h2 className="font-serif text-2xl">{spec.name}</h2>
                  <p className="text-xs text-stone-400">{spec.email} · {spec.phone || "fără telefon"}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/5">{spec.specialty || "Necategorizat"}</span>
                    {spec.verified ? (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400">Verificat</span>
                    ) : spec.tier === "REJECTED" ? (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/15 text-red-400">Respins</span>
                    ) : (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">În așteptare</span>
                    )}
                  </div>
                </div>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="close-spec-detail">
                <X className="w-4 h-4 text-stone-400" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <Mini label="Rating" value={spec.rating ? `${spec.rating}★` : "—"} />
              <Mini label="Recenzii" value={spec.reviews_count || 0} />
              <Mini label="Joburi" value={spec.jobs_done || 0} />
              <Mini label="Tier" value={spec.tier || "—"} />
            </div>

            <h3 className="font-serif text-lg mb-3 flex items-center gap-2"><FileCheck className="w-4 h-4" />Documente ({(spec.documents || []).length})</h3>
            <div className="space-y-2 mb-6">
              {(!spec.documents || spec.documents.length === 0) && (
                <div className="text-xs text-stone-500 text-center py-6 bg-white/5 rounded-xl" data-testid="no-docs">Niciun document încărcat</div>
              )}
              {(spec.documents || []).map(d => (
                <div key={d.id} className="bg-white/5 rounded-xl p-4" data-testid={`doc-${d.id}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileText className="w-5 h-5 text-stone-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{d.name}</div>
                        <div className="text-[10px] text-stone-500">{DOC_TYPE_LABELS[d.type] || d.type}</div>
                      </div>
                    </div>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border ${STATUS_COLORS[d.status] || STATUS_COLORS.pending}`}>
                      {d.status === "approved" ? "Aprobat" : d.status === "rejected" ? "Respins" : "În așteptare"}
                    </span>
                  </div>
                  {d.reason && <div className="text-[11px] text-red-400 mt-2">Motiv: {d.reason}</div>}
                  {docRejectFor === d.id ? (
                    <div className="mt-3 flex gap-2">
                      <input
                        autoFocus
                        value={docRejectReason}
                        onChange={e => setDocRejectReason(e.target.value)}
                        placeholder="Motiv respingere..."
                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-red-500/50"
                        data-testid={`doc-reject-reason-${d.id}`}
                      />
                      <button onClick={() => reviewDoc(d.id, "rejected", docRejectReason || "Document invalid")}
                        className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg text-xs"
                        data-testid={`confirm-doc-reject-${d.id}`}>Respinge</button>
                      <button onClick={() => { setDocRejectFor(null); setDocRejectReason(""); }}
                        className="px-3 py-2 bg-white/5 rounded-lg text-xs">Anulează</button>
                    </div>
                  ) : (
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => setPreviewDoc(d)} className="px-3 py-1.5 bg-white/5 rounded-lg text-xs hover:bg-white/10" data-testid={`view-doc-${d.id}`}>
                        Vizualizează
                      </button>
                      {d.status !== "approved" && (
                        <button onClick={() => reviewDoc(d.id, "approved")} className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs hover:bg-emerald-500/30" data-testid={`approve-doc-${d.id}`}>
                          Aprobă
                        </button>
                      )}
                      {d.status !== "rejected" && (
                        <button onClick={() => setDocRejectFor(d.id)} className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs hover:bg-red-500/30" data-testid={`reject-doc-${d.id}`}>
                          Respinge
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {rejectMode ? (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-4">
                <label className="text-xs uppercase tracking-wider text-red-300 mb-2 block">Motiv respingere</label>
                <textarea
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  rows={3}
                  placeholder="Explică motivul respingerii (vizibil pentru specialist)..."
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500/50 resize-none"
                  data-testid="reject-spec-reason"
                />
                <div className="flex gap-2 mt-3">
                  <button onClick={() => { setRejectMode(false); setRejectReason(""); }} className="flex-1 py-2 bg-white/5 rounded-lg text-xs">Anulează</button>
                  <button onClick={reject} className="flex-1 py-2 bg-red-500 text-white rounded-lg text-xs font-medium" data-testid="confirm-reject-spec">Confirmă respingerea</button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-2 sticky bottom-0 pt-2">
                <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Închide</button>
                {!spec.verified && (
                  <>
                    <button onClick={() => setRejectMode(true)} className="flex-1 py-3 bg-red-500/15 text-red-400 border border-red-500/30 rounded-xl text-sm font-medium" data-testid="reject-spec-btn">
                      <XCircle className="w-4 h-4 inline mr-1" />Respinge specialist
                    </button>
                    <button onClick={verify} className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium" data-testid="verify-spec-btn">
                      <CheckCircle2 className="w-4 h-4 inline mr-1" />Aprobă & Verifică
                    </button>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </motion.div>

      {previewDoc && (
        <div className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4" onClick={() => setPreviewDoc(null)}>
          <div className="max-w-4xl w-full max-h-[90vh] overflow-auto" onClick={e => e.stopPropagation()}>
            {previewDoc.url?.startsWith("data:image") || previewDoc.url?.match(/\.(png|jpe?g|webp|gif)$/i) ? (
              <img src={previewDoc.url} alt={previewDoc.name} className="w-full h-auto rounded-xl" />
            ) : (
              <div className="bg-stone-900 rounded-xl p-8 text-center">
                <FileText className="w-16 h-16 text-stone-500 mx-auto mb-4" />
                <p className="text-sm text-stone-300 mb-3">{previewDoc.name}</p>
                <a href={previewDoc.url} target="_blank" rel="noreferrer" className="text-[#d4ff3a] underline text-sm">Deschide în tab nou</a>
              </div>
            )}
            <button onClick={() => setPreviewDoc(null)} className="mt-4 mx-auto block px-6 py-2 bg-white/10 rounded-full text-sm">Închide previzualizare</button>
          </div>
        </div>
      )}
    </div>
  );
};

const Mini = ({ label, value }) => (
  <div className="bg-white/5 rounded-xl p-3">
    <div className="text-[10px] uppercase tracking-wider text-stone-500">{label}</div>
    <div className="text-lg font-serif">{value}</div>
  </div>
);

// ============= DISPUTE RESOLVE MODAL =============
export const DisputeResolveModal = ({ dispute, onClose, onResolved }) => {
  const [resolution, setResolution] = useState("split");
  const [clientPct, setClientPct] = useState(50);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const amount = dispute.escrow_amount || 0;
  const clientAmt = resolution === "refund_client" ? amount : resolution === "pay_specialist" ? 0 : amount * (clientPct / 100);
  const specialistAmt = resolution === "pay_specialist" ? amount * 0.95 : resolution === "refund_client" ? 0 : (amount - clientAmt) * 0.95;

  const submit = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/admin/disputes/${dispute.id}/resolve`, {
        resolution,
        client_pct: resolution === "split" ? clientPct : null,
        notes,
      });
      onResolved?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="dispute-resolve-modal">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Scale className="w-5 h-5 text-cyan-400" />
            <h2 className="font-serif text-2xl">Rezolvă dispută</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
        </div>

        <div className="bg-white/5 rounded-xl p-4 mb-4">
          <div className="text-xs text-stone-400 mb-1">Lucrare</div>
          <div className="text-sm font-medium mb-2">{dispute.request_title || "—"}</div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div><span className="text-stone-500">Client:</span> {dispute.client_name || "—"}</div>
            <div><span className="text-stone-500">Specialist:</span> {dispute.specialist_name || "—"}</div>
            <div><span className="text-stone-500">Escrow:</span> {amount.toFixed(2)} RON</div>
            <div><span className="text-stone-500">Deschis de:</span> {dispute.opened_by_role}</div>
          </div>
          <div className="mt-3 text-xs">
            <div className="text-stone-500 mb-1">Motiv dispută:</div>
            <div className="text-stone-200 italic">"{dispute.reason}"</div>
          </div>
          {dispute.evidence_urls && dispute.evidence_urls.length > 0 && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {dispute.evidence_urls.map((u, i) => (
                <img key={i} src={u} alt={`evidence-${i}`} className="w-full h-20 object-cover rounded-lg" />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2 mb-4">
          <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Rezoluție</label>
          <ResolveOption checked={resolution === "refund_client"} onChange={() => setResolution("refund_client")}
            label="Rambursare integrală client" desc={`${amount.toFixed(2)} RON → client`} tid="resolve-refund" />
          <ResolveOption checked={resolution === "pay_specialist"} onChange={() => setResolution("pay_specialist")}
            label="Plată integrală specialist" desc={`${(amount * 0.95).toFixed(2)} RON → specialist (−5% taxă)`} tid="resolve-pay" />
          <ResolveOption checked={resolution === "split"} onChange={() => setResolution("split")}
            label="Împărțire" desc="Distribuire procentuală" tid="resolve-split" />
        </div>

        {resolution === "split" && (
          <div className="mb-4 bg-white/5 rounded-xl p-4">
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Procent rambursare client: {clientPct}%</label>
            <input
              type="range"
              min={0} max={100} step={5}
              value={clientPct}
              onChange={e => setClientPct(parseInt(e.target.value))}
              className="w-full accent-[#d4ff3a]"
              data-testid="dispute-split-slider"
            />
            <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-2">
                <div className="text-stone-400">Client primește</div>
                <div className="font-serif text-lg text-emerald-300">{clientAmt.toFixed(2)} RON</div>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2">
                <div className="text-stone-400">Specialist primește</div>
                <div className="font-serif text-lg text-amber-300">{specialistAmt.toFixed(2)} RON</div>
              </div>
            </div>
          </div>
        )}

        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          placeholder="Note interne (opțional)..."
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50 resize-none mb-4"
          data-testid="dispute-notes"
        />

        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Anulează</button>
          <button onClick={submit} disabled={loading} className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium" data-testid="confirm-resolve">
            {loading ? "..." : "Confirmă rezoluția"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const ResolveOption = ({ checked, onChange, label, desc, tid }) => (
  <button onClick={onChange} className={`w-full text-left p-3 rounded-xl border ${checked ? "border-[#d4ff3a]/50 bg-[#d4ff3a]/5" : "border-white/10 bg-white/5"} transition`} data-testid={tid}>
    <div className="flex items-start gap-3">
      <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5 ${checked ? "border-[#d4ff3a] bg-[#d4ff3a]" : "border-stone-600"}`}>
        {checked && <div className="w-1.5 h-1.5 bg-black rounded-full m-auto mt-0.5" />}
      </div>
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-[11px] text-stone-400">{desc}</div>
      </div>
    </div>
  </button>
);

// ============= OPEN DISPUTE MODAL (Client or Specialist) =============
export const OpenDisputeModal = ({ requestId, requestTitle, onClose, onOpened }) => {
  const [reason, setReason] = useState("");
  const [evidenceUrls, setEvidenceUrls] = useState([]);
  const [loading, setLoading] = useState(false);

  const onPickFiles = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 5 - evidenceUrls.length);
    const newOnes = await Promise.all(files.map(f => new Promise(res => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.readAsDataURL(f);
    })));
    setEvidenceUrls([...evidenceUrls, ...newOnes]);
  };

  const submit = async () => {
    if (reason.trim().length < 10) return alert("Motivul trebuie să aibă cel puțin 10 caractere");
    setLoading(true);
    try {
      await axios.post(`${API}/requests/${requestId}/dispute`, { reason, evidence_urls: evidenceUrls });
      onOpened?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="open-dispute-modal">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <h2 className="font-serif text-2xl">Deschide dispută</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
        </div>
        <p className="text-xs text-stone-400 mb-5">Lucrarea: <span className="text-stone-200">{requestTitle}</span></p>

        <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Motiv detaliat (min. 10 caractere)</label>
        <textarea
          value={reason}
          onChange={e => setReason(e.target.value)}
          rows={5}
          placeholder="Descrie clar problema: ce s-a întâmplat, ce nu corespunde acordului, ce dorești să se rezolve..."
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-amber-500/50 resize-none mb-4"
          data-testid="dispute-reason"
        />

        <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Dovezi foto (opțional, max 5)</label>
        <div className="grid grid-cols-3 gap-2 mb-4">
          {evidenceUrls.map((u, i) => (
            <div key={i} className="relative aspect-square bg-white/5 rounded-lg overflow-hidden">
              <img src={u} alt={`ev-${i}`} className="w-full h-full object-cover" />
              <button onClick={() => setEvidenceUrls(evidenceUrls.filter((_, idx) => idx !== i))} className="absolute top-1 right-1 p-1 bg-black/70 rounded-full">
                <Trash2 className="w-3 h-3 text-red-400" />
              </button>
            </div>
          ))}
          {evidenceUrls.length < 5 && (
            <label className="aspect-square bg-white/5 border border-dashed border-white/20 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:bg-white/10" data-testid="add-evidence">
              <Camera className="w-5 h-5 text-stone-500 mb-1" />
              <span className="text-[10px] text-stone-500">Adaugă</span>
              <input type="file" accept="image/*" multiple className="hidden" onChange={onPickFiles} />
            </label>
          )}
        </div>

        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 mb-4">
          <div className="text-[11px] text-amber-300">
            ⚠ Deschiderea unei dispute îngheață fondurile din escrow. Un administrator va analiza cazul și va decide distribuirea fondurilor.
          </div>
        </div>

        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Anulează</button>
          <button onClick={submit} disabled={loading} className="flex-1 py-3 bg-amber-500 text-black rounded-xl text-sm font-medium" data-testid="submit-dispute">
            {loading ? "..." : "Deschide dispută"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// ============= SPECIALIST DOCUMENTS UPLOAD (self) =============
export const SpecialistDocumentsModal = ({ onClose }) => {
  const [docs, setDocs] = useState([]);
  const [type, setType] = useState("id_card");
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/specialist/documents`);
      setDocs(data);
    } catch (e) { /* noop */ }
  };
  useEffect(() => { load(); }, []);

  const onPickFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 4 * 1024 * 1024) return alert("Fișierul depășește 4 MB");
    const reader = new FileReader();
    reader.onload = () => { setFile(reader.result); if (!name) setName(f.name); };
    reader.readAsDataURL(f);
  };

  const upload = async () => {
    if (!file || !name) return alert("Selectează fișierul și introdu un nume");
    setLoading(true);
    try {
      await axios.post(`${API}/specialist/documents`, { type, name, url: file });
      setFile(null); setName(""); setType("id_card");
      await load();
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Sigur ștergi documentul?")) return;
    try { await axios.delete(`${API}/specialist/documents/${id}`); await load(); }
    catch (e) { alert(formatApiError(e)); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="my-documents-modal">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-serif text-2xl">Documentele mele</h2>
            <p className="text-xs text-stone-400 mt-1">Încarcă documentele pentru verificare. Vor fi revizuite de echipa noastră.</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
        </div>

        <div className="bg-white/5 rounded-xl p-4 mb-5">
          <h3 className="text-sm font-medium mb-3">Încarcă document nou</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <select value={type} onChange={e => setType(e.target.value)} className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid="doc-type-select">
              {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Nume document" className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid="doc-name-input" />
          </div>
          <label className="block bg-black/30 border border-dashed border-white/20 rounded-lg px-3 py-4 text-center cursor-pointer hover:bg-black/40" data-testid="doc-file-input">
            <span className="text-xs text-stone-400">{file ? "Fișier selectat ✓" : "Click pentru a selecta fișier (max 4MB)"}</span>
            <input type="file" accept="image/*,application/pdf" className="hidden" onChange={onPickFile} />
          </label>
          <button onClick={upload} disabled={loading || !file} className="mt-3 w-full btn-accent py-2 rounded-lg text-sm font-medium disabled:opacity-50" data-testid="upload-doc-btn">
            {loading ? "..." : "Încarcă"}
          </button>
        </div>

        <h3 className="text-sm font-medium mb-3">Documente încărcate ({docs.length})</h3>
        <div className="space-y-2">
          {docs.length === 0 && <div className="text-xs text-stone-500 text-center py-6 bg-white/5 rounded-xl">Niciun document încă</div>}
          {docs.map(d => (
            <div key={d.id} className="bg-white/5 rounded-xl p-3 flex items-center justify-between" data-testid={`my-doc-${d.id}`}>
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <FileText className="w-4 h-4 text-stone-400 flex-shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm truncate">{d.name}</div>
                  <div className="text-[10px] text-stone-500">{DOC_TYPE_LABELS[d.type] || d.type}</div>
                  {d.reason && <div className="text-[10px] text-red-400 mt-0.5">Motiv: {d.reason}</div>}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border ${STATUS_COLORS[d.status] || STATUS_COLORS.pending}`}>
                  {d.status === "approved" ? "Aprobat" : d.status === "rejected" ? "Respins" : "În așteptare"}
                </span>
                {d.status !== "approved" && (
                  <button onClick={() => remove(d.id)} className="p-1.5 hover:bg-red-500/10 rounded-lg" data-testid={`remove-doc-${d.id}`}>
                    <Trash2 className="w-3.5 h-3.5 text-red-400" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};
