// Approval queue page — visible to all admins.
// Super: sees all. Senior: sees scope + own. Junior: sees own.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ClipboardCheck, CheckCircle2, XCircle, Clock } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatusBadge = ({ status }) => {
  const map = {
    pending: { c: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300", l: "PENDING" },
    approved: { c: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300", l: "APPROVED" },
    rejected: { c: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300", l: "REJECTED" },
    failed: { c: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300", l: "FAILED" },
  };
  const cfg = map[status] || map.pending;
  return <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cfg.c}`}>{cfg.l}</span>;
};

export const AdminApprovals = () => {
  const focusId = React.useMemo(() => new URLSearchParams(window.location.search).get("focus"), []);
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState(() => (focusId ? "all" : "pending"));
  const [loading, setLoading] = useState(true);
  const [focusMissing, setFocusMissing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/approvals?status=${filter}&limit=100`);
      setItems(r.data?.items || []);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [filter]);

  // Deep-link: /admin?tab=approvals&focus=<id> → evidențiază approval-ul exact (fără fallback homepage)
  useEffect(() => {
    if (!focusId || loading) return;
    const exists = items.some(a => a.id === focusId);
    setFocusMissing(!exists);
    if (exists) {
      const timer = setTimeout(() => {
        const el = document.getElementById(`approval-${focusId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [focusId, loading, items]);

  const approve = async (id) => {
    const note = prompt("Notă aprobare (opțional):", "");
    if (note === null) return; // cancelled
    try {
      const r = await axios.post(`${API}/admin/approvals/${id}/approve`, { note });
      alert(`Aprobat. Status execuție: ${r.data.execution_status || "ok"}`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    }
  };
  const reject = async (id) => {
    const note = prompt("Motiv respingere:", "");
    if (note === null) return;
    try {
      await axios.post(`${API}/admin/approvals/${id}/reject`, { note });
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-approvals-page">
      <AdminCard
        testid="approvals-list"
        title={
          <div className="flex items-center gap-2">
            <ClipboardCheck className="w-4 h-4 text-amber-500" />
            <span>Aprobări Admin</span>
            <span className="text-[10px] text-slate-500 font-normal">({items.length})</span>
          </div>
        }
        action={
          <div className="flex gap-1">
            {["pending", "approved", "rejected", "all"].map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`text-[11px] px-3 py-1.5 rounded-md ${filter === s ? "bg-violet-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"}`}
                data-testid={`filter-${s}`}
              >
                {s}
              </button>
            ))}
          </div>
        }
      >
        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500">Se încarcă…</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500" data-testid="approvals-empty">
            Nicio cerere {filter !== "all" ? filter : ""} în prezent.
          </div>
        ) : (
          <div className="space-y-2">
            {focusMissing && (
              <div className="rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300" data-testid="approval-focus-missing">
                Approval indisponibil (a fost decis sau nu mai există).
              </div>
            )}
            {items.map((a) => (
              <div
                key={a.id}
                id={`approval-${a.id}`}
                className={`rounded-xl border p-4 bg-slate-50 dark:bg-slate-800/50 ${focusId === a.id ? "border-violet-500 ring-2 ring-violet-500/40" : "border-slate-200 dark:border-slate-700"}`}
                data-testid={`approval-${a.id}`}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <code className="font-mono text-sm font-bold">{a.action}</code>
                      <StatusBadge status={a.status} />
                      <span className="text-[10px] uppercase tracking-wider text-slate-500">scope: {a.scope}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      <Clock className="w-3 h-3 inline mr-1" />
                      Cerută de <strong>{a.requested_by_email}</strong> ({a.requested_by_seniority}) · {new Date(a.created_at).toLocaleString("ro-RO")}
                    </div>
                    {a.decided_at && (
                      <div className="text-xs text-slate-500 mt-1">
                        Decisă de <strong>{a.decided_by_email}</strong> · {new Date(a.decided_at).toLocaleString("ro-RO")}
                        {a.decision_note && <span className="italic"> · "{a.decision_note}"</span>}
                      </div>
                    )}
                    <details className="mt-2">
                      <summary className="text-[11px] text-slate-500 cursor-pointer hover:text-slate-700">Vezi payload + execuție</summary>
                      <pre className="mt-2 text-[10px] font-mono bg-slate-100 dark:bg-slate-900 p-2 rounded overflow-x-auto">
{JSON.stringify({ payload: a.payload, execution_result: a.execution_result, execution_error: a.execution_error }, null, 2)}
                      </pre>
                    </details>
                  </div>
                  {a.status === "pending" && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => approve(a.id)}
                        className="text-xs px-3 py-1.5 rounded-md bg-emerald-500 text-white hover:bg-emerald-600 flex items-center gap-1"
                        data-testid={`approve-${a.id}`}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        Aprobă
                      </button>
                      <button
                        onClick={() => reject(a.id)}
                        className="text-xs px-3 py-1.5 rounded-md bg-red-500 text-white hover:bg-red-600 flex items-center gap-1"
                        data-testid={`reject-${a.id}`}
                      >
                        <XCircle className="w-3 h-3" />
                        Respinge
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </AdminCard>
    </div>
  );
};
