// LegalGate — soft access gate for strategic contributors with pending mandatory docs.
// Renders nothing for compliant users. Shows a blocking modal for non-compliant strategic contributors.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useLocation } from "react-router-dom";
import { ShieldCheck, AlertTriangle, FileText, ArrowRight, X } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

export const LegalGate = () => {
  const location = useLocation();
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let mounted = true;
    if (!localStorage.getItem("pm_session_hint")) return undefined;
    ax.get("/api/legal/me/status")
      .then(r => { if (mounted) setStatus(r.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, [location.pathname]);

  // Don't show the gate while user is actively on the legal sign page or public/login pages.
  const HIDDEN_PATHS = ["/legal/sign", "/login", "/register", "/privacy", "/terms"];
  if (HIDDEN_PATHS.some(p => location.pathname === p || location.pathname.startsWith(p + "/"))) return null;
  if (!status || dismissed) return null;
  if (!status.is_strategic_contributor) return null;
  if (status.compliant) return null;

  const pendingCount = (status.pending || []).length;
  const expiredCount = (status.expired || []).length;
  const total = (status.required || []).length;

  return (
    <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-sm" data-testid="legal-gate-modal">
      <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-rose-300 dark:border-rose-500/40 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-rose-50 dark:bg-rose-500/10">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Acțiune juridică necesară</h2>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            title="Amână (rezolvă cât mai curând)"
            data-testid="legal-gate-dismiss"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">
          <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
            Ești înregistrat drept <strong>Strategic Contributor</strong> în PropManage. Pentru continuarea colaborării trebuie să accepți digital toate documentele juridice obligatorii.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-rose-200 dark:border-rose-500/30 p-3 bg-rose-50/60 dark:bg-rose-500/5">
              <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">{pendingCount}</div>
              <div className="text-[11px] uppercase text-rose-700 dark:text-rose-300">de semnat</div>
            </div>
            <div className="rounded-lg border border-amber-200 dark:border-amber-500/30 p-3 bg-amber-50/60 dark:bg-amber-500/5">
              <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{expiredCount}</div>
              <div className="text-[11px] uppercase text-amber-700 dark:text-amber-300">versiune depășită</div>
            </div>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <FileText className="w-3 h-3" /> {total} documente obligatorii (NDA, contract colaborare, cesiune IP, securitate, acces infrastructură, regulament).
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <Link
            to="/legal/sign"
            onClick={() => setDismissed(true)}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium flex items-center gap-1.5"
            data-testid="legal-gate-open"
          >
            <ShieldCheck className="w-4 h-4" /> Vezi și semnează acum <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LegalGate;
