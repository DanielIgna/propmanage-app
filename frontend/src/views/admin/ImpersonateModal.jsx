// Admin → "Intră în contul lui" modal: collect reason (GDPR audit) before starting impersonation.
import React, { useState } from "react";
import axios from "axios";
import { ShieldAlert, X, ArrowRight, Loader2 } from "lucide-react";
import { API } from "../DashShared";

const MIN_REASON = 10;
const MAX_REASON = 500;

export const ImpersonateModal = ({ user, onClose }) => {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const submit = async () => {
    setErr(null);
    if (reason.trim().length < MIN_REASON) {
      setErr(`Motivul trebuie să aibă cel puțin ${MIN_REASON} caractere (audit GDPR).`);
      return;
    }
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/admin/impersonate`, {
        user_id: user.id,
        reason: reason.trim(),
      });
      // Hard navigate so AuthProvider re-fetches /me with the new cookie
      window.location.href = data?.redirect_to || `/${user.role}`;
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 w-full max-w-md p-6"
        data-testid="impersonate-modal"
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-red-100 dark:bg-red-500/15 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Intră în contul utilizatorului</h3>
              <div className="text-xs text-slate-500">Sesiunea va fi jurnalizată GDPR.</div>
            </div>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 mb-4 text-sm">
          <div><strong>{user.name || "—"}</strong> · <span className="text-slate-500">{user.email}</span></div>
          <div className="text-xs text-slate-500 mt-0.5">Rol: <span className="uppercase tracking-wider">{user.role}</span></div>
        </div>

        <label className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
          Motiv (obligatoriu, min {MIN_REASON} caractere)
        </label>
        <textarea
          rows={4}
          maxLength={MAX_REASON}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Ex: Suport ticket #4521 — clientul nu vede ultima factură escrow."
          className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
          data-testid="impersonate-reason"
        />
        <div className="text-[10px] text-right text-slate-500 mt-0.5">{reason.length}/{MAX_REASON}</div>

        <div className="mt-3 text-[11px] text-slate-500 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg p-2.5 leading-relaxed">
          <strong className="text-amber-700 dark:text-amber-400">Notă GDPR:</strong> sesiunea expiră automat în 2 ore.
          Schimbarea parolei, 2FA și ștergerea contului sunt blocate. Toate acțiunile rămân auditabile.
        </div>

        {err && <div className="mt-3 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg p-2" data-testid="impersonate-error">{err}</div>}

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700">Anulează</button>
          <button
            onClick={submit}
            disabled={busy || reason.trim().length < MIN_REASON}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold"
            data-testid="impersonate-confirm"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
            Intră în cont
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImpersonateModal;
