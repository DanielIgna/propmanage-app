// Extracted from AdminQAPlaybook.jsx for maintainability.
import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { CheckCircle2, FileWarning, Loader2, RotateCw, Search, Trash2, Wand2 } from "lucide-react";
import { AdminCard, AdminBtn } from "../AdminLayoutMetronic";
import { API } from "./shared";

export const ContentAuditCard = () => {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [fixingId, setFixingId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("open");

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const url = statusFilter === "ALL" ? `${API}/admin/qa/content-audit/conflicts` : `${API}/admin/qa/content-audit/conflicts?status=${statusFilter}`;
      const { data } = await axios.get(url);
      setConflicts(data.conflicts || []);
    } catch (e) {
      toast.error("Eroare la încărcarea conflictelor");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { reload(); }, [reload]);

  const scan = async () => {
    setScanning(true);
    try {
      const { data } = await axios.post(`${API}/admin/qa/content-audit/scan`);
      toast.success(`Scanare completă: ${data.added} noi · ${data.already_existing} existau · ${data.total_scanned} total detectate`);
      reload();
    } catch {
      toast.error("Eroare la scanare");
    } finally {
      setScanning(false);
    }
  };

  const aiFix = async (cid) => {
    setFixingId(cid);
    try {
      const { data } = await axios.post(`${API}/admin/qa/content-audit/conflicts/${cid}/ai-fix`);
      if (data.error) {
        toast.error(`AI fix failed: ${data.error}`);
      } else {
        toast.success("AI a generat o sugestie de rescriere");
        reload();
      }
    } finally {
      setFixingId(null);
    }
  };

  const apply = async (cid) => {
    if (!confirm("Aplici fix-ul AI? Override-ul se salvează în DB și înlocuiește textul original în PDF/UI fără să modifice codul.")) return;
    try {
      await axios.post(`${API}/admin/qa/content-audit/conflicts/${cid}/apply`, {});
      toast.success("Fix aplicat — vezi documentul actualizat");
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la aplicare");
    }
  };

  const setStatus = async (cid, status) => {
    try {
      await axios.patch(`${API}/admin/qa/content-audit/conflicts/${cid}/status`, { status });
      toast.success(`Marcat ca ${status}`);
      reload();
    } catch {
      toast.error("Eroare la update status");
    }
  };

  const sevBadge = (s) => ({
    high: "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30",
    medium: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
    low: "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30",
  }[s] || "bg-slate-500/15 text-slate-700");

  const statBadge = (s) => ({
    open: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    approved: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
    dismissed: "bg-slate-500/15 text-slate-600 dark:text-slate-400",
    fixed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  }[s] || "bg-slate-500/15");

  return (
    <AdminCard
      title={<span className="inline-flex items-center gap-2"><FileWarning className="w-4 h-4" /> Content Audit · audiență vs. rol în documentație</span>}
      testid="qa-content-audit-card"
      action={
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="text-xs px-2 py-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100" data-testid="qa-audit-filter">
            <option value="ALL">Toate</option>
            <option value="open">Open</option>
            <option value="approved">Aprobate</option>
            <option value="dismissed">Dismissed</option>
            <option value="fixed">Fixed</option>
          </select>
          <button onClick={reload} className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white inline-flex items-center gap-1" data-testid="qa-audit-refresh"><RotateCw className="w-3.5 h-3.5" /></button>
        </div>
      }
    >
      <p className="text-xs text-slate-500 mb-3">
        Sistemul scanează automat fiecare manual și detectează când limbajul nu se potrivește cu audiența (ex: text de tip „banii pe care îi <em>plătești</em>" într-un doc pentru specialist). Aprobi sau respingi fiecare conflict. La aprobare, AI-ul rescrie pasajul corect și se salvează ca <code>override</code> în DB — fără modificare de cod.
      </p>
      <div className="flex gap-2 mb-3 flex-wrap">
        <AdminBtn variant="primary" onClick={scan} disabled={scanning} data-testid="qa-audit-scan-btn">
          {scanning ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Scanare...</> : <><Search className="w-3.5 h-3.5 inline mr-1" /> Scanează toate manualele</>}
        </AdminBtn>
        <span className="text-xs text-slate-500 self-center">Total afișat: <strong>{conflicts.length}</strong></span>
      </div>

      {loading ? (
        <div className="text-xs text-slate-500 py-6 text-center"><Loader2 className="w-4 h-4 inline animate-spin mr-1" /> Se încarcă...</div>
      ) : conflicts.length === 0 ? (
        <div className="text-center py-6 text-sm text-slate-500">
          {statusFilter === "open" ? "🎉 Niciun conflict deschis — documentația ta e curată!" : "Niciun conflict pentru filtrul selectat."}
        </div>
      ) : (
        <ul className="space-y-2 max-h-[420px] overflow-y-auto pr-1" data-testid="qa-audit-conflicts">
          {conflicts.map((c) => {
            const isFixed = c.status === "fixed";
            return (
              <li key={c.id} className="text-xs p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40" data-testid={`qa-audit-${c.id}`}>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <code className="font-mono font-semibold text-slate-900 dark:text-slate-100">{c.doc_slug}</code>
                  <span className="text-slate-500">› {c.section_heading}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${sevBadge(c.severity)}`}>{c.severity}</span>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">audiență greșită: {c.wrong_audience}</span>
                  <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full ${statBadge(c.status)}`}>{c.status}</span>
                </div>
                <p className="text-slate-700 dark:text-slate-200 italic">„{c.block_excerpt}"</p>
                {c.ai_suggested_fix && (
                  <div className="mt-2 p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                    <div className="text-[10px] uppercase tracking-wider text-blue-700 dark:text-blue-300 mb-1">✨ Sugestie AI</div>
                    {c.ai_suggested_fix.title && <div className="font-semibold text-slate-900 dark:text-slate-100">{c.ai_suggested_fix.title}</div>}
                    <div className="text-slate-700 dark:text-slate-200">{c.ai_suggested_fix.body}</div>
                  </div>
                )}
                <div className="flex gap-1 mt-2 flex-wrap">
                  {!isFixed && !c.ai_suggested_fix && (
                    <AdminBtn variant="secondary" onClick={() => aiFix(c.id)} disabled={fixingId === c.id} data-testid={`qa-audit-${c.id}-aifix`}>
                      {fixingId === c.id ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> AI rescrie...</> : <><Wand2 className="w-3.5 h-3.5 inline mr-1" /> Cere fix de la AI</>}
                    </AdminBtn>
                  )}
                  {!isFixed && c.ai_suggested_fix && (
                    <AdminBtn variant="success" onClick={() => apply(c.id)} data-testid={`qa-audit-${c.id}-apply`}>
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" /> Aplică fix-ul
                    </AdminBtn>
                  )}
                  {!isFixed && (
                    <AdminBtn variant="ghost" onClick={() => setStatus(c.id, "dismissed")} data-testid={`qa-audit-${c.id}-dismiss`}>
                      <Trash2 className="w-3.5 h-3.5 inline mr-1" /> Dismiss (false-positive)
                    </AdminBtn>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </AdminCard>
  );
};





// ----------------------------------------------------------------------------
// Terminology Audit — detect inconsistent vocabulary across docs
// ----------------------------------------------------------------------------
