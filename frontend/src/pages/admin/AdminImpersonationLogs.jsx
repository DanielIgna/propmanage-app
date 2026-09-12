// Admin panel — audit log of all impersonation sessions (GDPR transparency).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ShieldAlert, Search, Clock, User as UserIcon } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
};
const fmtDur = (s) => {
  if (s == null) return "—";
  const m = Math.floor(s / 60), r = s % 60;
  return `${m}m ${r}s`;
};

export const AdminImpersonationLogs = () => {
  const [data, setData] = useState({ items: [], total: 0 });
  const [q, setQ] = useState("");
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    axios.get(`${API}/admin/impersonation-logs`, { params: { skip, limit: 25 } })
      .then(r => setData(r.data)).catch(() => {})
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [skip]);

  const filtered = q
    ? data.items.filter(it =>
        (it.admin_email || "").toLowerCase().includes(q.toLowerCase()) ||
        (it.target_user_email || "").toLowerCase().includes(q.toLowerCase()) ||
        (it.reason || "").toLowerCase().includes(q.toLowerCase())
      )
    : data.items;

  return (
    <div className="space-y-4" data-testid="impersonation-logs">
      <AdminCard>
        <div className="flex items-center gap-3 flex-wrap">
          <ShieldAlert className="w-5 h-5 text-red-500" />
          <h2 className="text-lg font-semibold flex-1">Jurnal impersonare</h2>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Caută admin / target / motiv..."
              className="pl-9 pr-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
              data-testid="impersonation-logs-search"
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Fiecare sesiune de impersonare este jurnalizată GDPR cu admin, utilizator țintă, motiv, IP, user-agent și durată. Utilizatorul țintă poate accesa istoricul prin <em>Setări → Date și confidențialitate</em>.
        </p>
      </AdminCard>

      <AdminCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Început</th>
                <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Admin</th>
                <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Utilizator țintă</th>
                <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Motiv</th>
                <th className="text-right py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Durată</th>
                <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">IP</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(it => (
                <tr key={it.id} className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30" data-testid={`imp-log-${it.id}`}>
                  <td className="py-2.5 px-3 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">{fmtDate(it.started_at)}</td>
                  <td className="py-2.5 px-3">
                    <div className="font-medium">{it.admin_name || "—"}</div>
                    <div className="text-[11px] text-slate-500">{it.admin_email}</div>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="font-medium">{it.target_user_name || "—"}</div>
                    <div className="text-[11px] text-slate-500">{it.target_user_email} <span className="uppercase text-[9px] tracking-wider ml-1 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800">{it.target_user_role}</span></div>
                  </td>
                  <td className="py-2.5 px-3 max-w-[300px]">
                    <div className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2" title={it.reason}>{it.reason}</div>
                  </td>
                  <td className="py-2.5 px-3 text-right tabular-nums">
                    {it.ended_at ? (
                      <span className="text-xs text-emerald-600 dark:text-emerald-400">{fmtDur(it.duration_seconds)}</span>
                    ) : (
                      <span className="text-xs text-amber-600 dark:text-amber-400 inline-flex items-center gap-1"><Clock className="w-3 h-3" />activă</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-slate-500 font-mono">{it.ip || "—"}</td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan="6" className="text-center py-8 text-slate-500" data-testid="imp-logs-empty">Nicio sesiune de impersonare înregistrată.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex justify-between items-center pt-4 mt-2 text-sm">
          <div className="text-slate-500">Total: {data.total}</div>
          <div className="flex gap-2">
            <AdminBtn variant="secondary" onClick={() => setSkip(Math.max(0, skip - 25))} disabled={skip === 0}>← Anterior</AdminBtn>
            <AdminBtn variant="secondary" onClick={() => setSkip(skip + 25)} disabled={skip + 25 >= data.total}>Următor →</AdminBtn>
          </div>
        </div>
      </AdminCard>
    </div>
  );
};

export default AdminImpersonationLogs;
