// Admin KYC Review queue + detail modal — placed inside Operator/Admin dashboard.
import React, { useState, useEffect } from "react";
import axios from "axios";
import { ShieldCheck, Eye, CheckCircle2, XCircle, RefreshCw, Sparkles, AlertTriangle, Zap, Settings } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_TONE = {
  uploaded:  "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  reviewing: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300",
  approved:  "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  rejected:  "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
};

const AIVerificationPanel = ({ doc, kycId, onRerun }) => {
  const [busy, setBusy] = useState(false);
  const ai = doc?.ai_verification;
  const score = ai?.match_score;
  const flags = ai?.flags || [];

  const scoreTone = score === null || score === undefined
    ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
    : score >= 90 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
    : score >= 60 ? "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300"
    : score >= 30 ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"
    : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300";

  const rerun = async () => {
    setBusy(true);
    try {
      await axios.post(`${API}/kyc/admin/${kycId}/ai-verify`);
      onRerun?.();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare AI verify");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl p-4 mb-4 bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-500/5 dark:to-indigo-500/5 border border-violet-200/60 dark:border-violet-500/20" data-testid="ai-verification-panel">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-500" />
          <span className="font-medium text-sm">AI Verification</span>
          <span className="text-[10px] text-slate-500">Claude Sonnet 4.5 vision</span>
        </div>
        <button
          onClick={rerun}
          disabled={busy}
          className="text-[11px] px-2 py-1 rounded-md bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 hover:bg-violet-200 disabled:opacity-50 flex items-center gap-1"
          data-testid="ai-rerun"
        >
          <RefreshCw className={`w-3 h-3 ${busy ? "animate-spin" : ""}`} />
          {busy ? "Rulează…" : ai ? "Re-rulează" : "Rulează acum"}
        </button>
      </div>
      {!ai ? (
        <div className="text-xs text-slate-500" data-testid="ai-not-run">
          AI nu a fost rulat încă. Click <strong>Rulează acum</strong> pentru analiză vizuală automată.
        </div>
      ) : ai.error ? (
        <div className="text-xs text-red-600 dark:text-red-400 flex items-start gap-1.5" data-testid="ai-error">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>Eroare AI: {ai.error}</span>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            {ai.recommendation && (
              <span className={`px-3 py-1.5 rounded-lg text-xs font-bold ${ai.recommendation === "approve"
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                : "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"}`} data-testid="ai-recommendation">
                {ai.recommendation === "approve" ? "✓ Recomandat spre aprobare" : "⚠ Necesită review manual"}
              </span>
            )}
            <div className={`px-3 py-1.5 rounded-lg ${scoreTone}`} data-testid="ai-score">
              <span className="text-[10px] uppercase tracking-wider opacity-70">Match score</span>
              <span className="ml-2 font-bold text-lg">{score !== null && score !== undefined ? `${score}/100` : "—"}</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {flags.map((f, i) => {
                const negative = /poor|blur_high|covered|mismatch|suspicious|screen_capture|no_id_visible|uncertain/.test(f);
                return (
                  <span
                    key={i}
                    className={`text-[10px] font-mono px-2 py-0.5 rounded ${negative ? "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300" : "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"}`}
                    data-testid={`ai-flag-${i}`}
                  >
                    {f}
                  </span>
                );
              })}
            </div>
          </div>
          {ai.summary && (
            <div className="text-xs text-slate-600 dark:text-slate-300 italic" data-testid="ai-summary">
              {`"${ai.summary}"`}
            </div>
          )}
          {ai.ran_at && (
            <div className="text-[10px] text-slate-500">Rulat: {new Date(ai.ran_at).toLocaleString("ro-RO")}</div>
          )}
        </div>
      )}
    </div>
  );
};

const DocPreview = ({ src, label }) => {
  const [zoom, setZoom] = useState(false);
  if (!src) return <div className="rounded-lg bg-slate-100 dark:bg-slate-800 h-48 flex items-center justify-center text-xs text-slate-500">— lipsă —</div>;
  return (
    <>
      <button
        onClick={() => setZoom(true)}
        className="block w-full rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 hover:border-violet-500 transition"
        data-testid={`kyc-preview-${label}`}
      >
        <img src={src} alt={label} className="w-full h-48 object-cover" />
      </button>
      {zoom && (
        <div className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center p-4" onClick={() => setZoom(false)}>
          <img src={src} alt={label} className="max-w-full max-h-full rounded-xl" />
        </div>
      )}
    </>
  );
};

const KYCDetailModal = ({ kycId, onClose, onDecision }) => {
  const [doc, setDoc] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!kycId) return;
    axios.get(`${API}/kyc/admin/${kycId}`).then((r) => setDoc(r.data)).catch(() => onClose());
  }, [kycId]);  // eslint-disable-line react-hooks/exhaustive-deps

  const decide = async (action) => {
    if (action === "reject" && !note.trim()) {
      alert("Motivul respingerii e obligatoriu.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/kyc/admin/${kycId}/${action}`, { note: note.trim() });
      onDecision(action);
      onClose();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    } finally {
      setBusy(false);
    }
  };

  if (!kycId) return null;
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-5xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="kyc-review-modal"
      >
        {doc ? (
          <>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-xl flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-violet-500" />
                  Review KYC
                </h3>
                <div className="text-xs text-slate-500 mt-1">
                  {doc.user_email} · trimis {new Date(doc.submitted_at).toLocaleString("ro-RO")}
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2 py-1 rounded-full uppercase ${STATUS_TONE[doc.status]}`}>{doc.status}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Buletin · Față</div>
                <DocPreview src={doc.id_front} label="id-front" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Buletin · Verso</div>
                <DocPreview src={doc.id_back} label="id-back" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Selfie</div>
                <DocPreview src={doc.selfie} label="selfie" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4 text-sm">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Nume pe buletin</div>
                <div className="font-medium">{doc.full_name_on_id || "—"}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500">CNP masked</div>
                <div className="font-mono">{doc.national_id_masked || "—"}</div>
              </div>
            </div>

            {/* AI Verification panel */}
            <AIVerificationPanel doc={doc} kycId={kycId} onRerun={() => {
              setDoc(null);
              axios.get(`${API}/kyc/admin/${kycId}`).then((r) => setDoc(r.data)).catch(() => {});
            }} />

            {["uploaded", "reviewing"].includes(doc.status) && (
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4 space-y-3">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Notă review (obligatorie la respingere, opțională la aprobare)"
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
                  rows={2}
                  data-testid="kyc-review-note"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={onClose}
                    className="text-sm px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    data-testid="kyc-review-close"
                  >
                    Închide
                  </button>
                  <button
                    onClick={() => decide("reject")}
                    disabled={busy}
                    className="text-sm px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 flex items-center gap-1.5"
                    data-testid="kyc-review-reject"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Respinge
                  </button>
                  <button
                    onClick={() => decide("approve")}
                    disabled={busy}
                    className="text-sm px-4 py-2 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-50 flex items-center gap-1.5"
                    data-testid="kyc-review-approve"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Aprobă & VERIFY
                  </button>
                </div>
              </div>
            )}

            {doc.review_note && (
              <div className="mt-3 p-3 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs italic">
                {`Notă review: "${doc.review_note}" — de ${doc.reviewed_by_email}`}
              </div>
            )}
          </>
        ) : (
          <div className="py-12 text-center text-sm text-slate-500">Se încarcă documentele…</div>
        )}
      </div>
    </div>
  );
};

export const AdminKYCQueue = () => {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState("uploaded");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [autoApprove, setAutoApprove] = useState({ enabled: false, min_score: 92, block_on_negative_flags: true });

  const loadConfig = async () => {
    try {
      const r = await axios.get(`${API}/kyc/admin/config/auto-approve`);
      setAutoApprove(r.data);
    } catch {
      // silent
    }
  };
  const saveConfig = async () => {
    try {
      await axios.put(`${API}/kyc/admin/config/auto-approve`, autoApprove);
      setConfigOpen(false);
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare la salvare config");
    }
  };
  useEffect(() => { loadConfig(); }, []);

  const load = async (status = filter) => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/kyc/admin/queue?status=${status}&limit=80`);
      setItems(r.data?.items || []);
      setCounts(r.data?.counts || {});
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(filter); }, [filter]);  // eslint-disable-line react-hooks/exhaustive-deps

  const filterChip = (key, label) => {
    const count = key === "all"
      ? Object.values(counts).reduce((a, b) => a + b, 0)
      : (counts[key] || 0);
    return (
      <button
        key={key}
        onClick={() => setFilter(key)}
        className={`text-[11px] px-3 py-1.5 rounded-md ${filter === key ? "bg-violet-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"}`}
        data-testid={`kyc-filter-${key}`}
      >
        {label} ({count})
      </button>
    );
  };

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5" data-testid="admin-kyc-queue">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="font-serif text-lg flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-violet-500" />
          KYC · Verificări Identitate
          <span className="text-[10px] text-slate-500 font-normal">({items.length} {filter})</span>
          {autoApprove.enabled && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300 flex items-center gap-1" data-testid="auto-approve-active">
              <Zap className="w-3 h-3" /> Auto ≥ {autoApprove.min_score}
            </span>
          )}
        </h3>
        <div className="flex gap-1 flex-wrap">
          {filterChip("uploaded", "În așteptare")}
          {filterChip("reviewing", "În revizie")}
          {filterChip("approved", "Aprobate")}
          {filterChip("rejected", "Respinse")}
          {filterChip("all", "Toate")}
          <button
            onClick={() => load(filter)}
            className="text-[11px] px-2 py-1.5 rounded-md bg-slate-100 dark:bg-slate-800"
            data-testid="kyc-refresh"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setConfigOpen(true)}
            className="text-[11px] px-2 py-1.5 rounded-md bg-violet-100 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 hover:bg-violet-200 flex items-center gap-1"
            data-testid="kyc-config-toggle"
            title="Config auto-approve"
          >
            <Settings className="w-3 h-3" />
            Auto
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-8 text-center text-sm text-slate-500">Se încarcă…</div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center text-sm text-slate-500" data-testid="kyc-queue-empty">
          Nicio cerere {filter !== "all" ? filter : ""}.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((it) => (
            <div
              key={it.id}
              className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-violet-400 transition"
              data-testid={`kyc-row-${it.id}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs">{it.user_email}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${STATUS_TONE[it.status] || ""}`}>{it.status}</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {it.full_name_on_id || it.user_name} · trimis {new Date(it.submitted_at).toLocaleString("ro-RO")}
                  {it.reviewed_at && ` · revizuit ${new Date(it.reviewed_at).toLocaleString("ro-RO")}`}
                </div>
              </div>
              <button
                onClick={() => setSelected(it.id)}
                className="text-xs px-3 py-1.5 rounded-md bg-violet-500 text-white hover:bg-violet-600 flex items-center gap-1"
                data-testid={`kyc-review-${it.id}`}
              >
                <Eye className="w-3 h-3" />
                Review
              </button>
            </div>
          ))}
        </div>
      )}

      <KYCDetailModal
        kycId={selected}
        onClose={() => setSelected(null)}
        onDecision={() => load(filter)}
      />

      {configOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setConfigOpen(false)}>
          <div
            className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
            data-testid="kyc-config-modal"
          >
            <h3 className="font-serif text-lg flex items-center gap-2 mb-2">
              <Zap className="w-5 h-5 text-violet-500" />
              Auto-Approve KYC
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Aprobă automat KYC-urile cu scor AI ridicat. Cazurile borderline rămân în review manual.
              <strong className="text-violet-600 dark:text-violet-400"> Doar super-admin poate modifica.</strong>
            </p>

            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoApprove.enabled}
                  onChange={(e) => setAutoApprove({ ...autoApprove, enabled: e.target.checked })}
                  className="w-4 h-4 accent-violet-500"
                  data-testid="config-enabled"
                />
                <div>
                  <div className="text-sm font-medium">Activează auto-approve</div>
                  <div className="text-[11px] text-slate-500">KYC se aprobă singur dacă AI confirmă cu scor mare</div>
                </div>
              </label>

              <div>
                <label className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
                  Scor minim pentru auto-approve: <strong className="text-violet-600 dark:text-violet-400">{autoApprove.min_score}</strong>
                </label>
                <input
                  type="range"
                  min={50}
                  max={100}
                  step={1}
                  value={autoApprove.min_score}
                  onChange={(e) => setAutoApprove({ ...autoApprove, min_score: parseInt(e.target.value, 10) })}
                  className="w-full mt-2 accent-violet-500"
                  data-testid="config-min-score"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                  <span>50 (permisiv)</span>
                  <span>92 (recomandat)</span>
                  <span>100 (strict)</span>
                </div>
              </div>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoApprove.block_on_negative_flags}
                  onChange={(e) => setAutoApprove({ ...autoApprove, block_on_negative_flags: e.target.checked })}
                  className="w-4 h-4 accent-violet-500"
                  data-testid="config-block-negative"
                />
                <div>
                  <div className="text-sm font-medium">Blochează auto-approve dacă AI ridică flag-uri negative</div>
                  <div className="text-[11px] text-slate-500">Recomandat ON. Flag-uri: blur, screen_capture, suspicious, etc.</div>
                </div>
              </label>
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setConfigOpen(false)}
                className="text-sm px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800"
                data-testid="config-cancel"
              >
                Anulează
              </button>
              <button
                onClick={saveConfig}
                className="text-sm px-5 py-2 rounded-lg bg-violet-500 text-white hover:bg-violet-600 font-medium"
                data-testid="config-save"
              >
                Salvează
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
