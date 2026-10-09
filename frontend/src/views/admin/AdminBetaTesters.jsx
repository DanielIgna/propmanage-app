// Admin Beta Testers — monitor new sign-ups in the last 30 days.
// Provenance (Google OAuth vs email) + activity (requests count) + verified status.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Sparkles, Users, Mail, CheckCircle2, Activity, Calendar, Ban,
} from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
};

const Counter = ({ icon: Icon, label, value, color = "blue" }) => (
  <div className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4`}>
    <div className="flex items-center gap-2 mb-1">
      <Icon className={`w-4 h-4 text-${color}-500`} />
      <div className="text-xs text-slate-500">{label}</div>
    </div>
    <div className="text-2xl font-serif">{value}</div>
  </div>
);

export const AdminBetaTesters = () => {
  const [data, setData] = useState({ items: [], counters: {} });
  const [days, setDays] = useState(30);
  const [roleFilter, setRoleFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/admin/beta-testers`, { params: { days, role: roleFilter } })
      .then(r => setData(r.data)).catch(() => {})
      .finally(() => setLoading(false));
  }, [days, roleFilter]);

  const counters = data.counters || {};
  const items = data.items || [];

  return (
    <div className="space-y-4" data-testid="beta-testers-page">
      <AdminCard>
        <div className="flex items-center gap-3 flex-wrap">
          <Sparkles className="w-5 h-5 text-amber-500" />
          <h2 className="text-lg font-semibold flex-1">Beta Testers</h2>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
            data-testid="beta-days-filter"
          >
            <option value={7}>Ultimele 7 zile</option>
            <option value={14}>Ultimele 14 zile</option>
            <option value={30}>Ultimele 30 zile</option>
            <option value={60}>Ultimele 60 zile</option>
            <option value={90}>Ultimele 90 zile</option>
          </select>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
            data-testid="beta-role-filter"
          >
            <option value="">Toate rolurile</option>
            <option value="client">Doar Client</option>
            <option value="specialist">Doar Specialist</option>
            <option value="operator">Doar Operator</option>
          </select>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Conturile demo (admin/client/specialist/operator@propmanage.io) și admins sunt excluse automat.
        </p>
      </AdminCard>

      {/* Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Counter icon={Users} label="Total beta" value={counters.total || 0} color="blue" />
        <Counter icon={Activity} label="Cu activitate" value={counters.with_requests || 0} color="emerald" />
        <Counter icon={CheckCircle2} label="Verificați" value={counters.verified || 0} color="amber" />
        <Counter icon={Mail} label="Via Google" value={counters?.by_provenance?.google || 0} color="rose" />
      </div>

      {/* Role breakdown */}
      <AdminCard>
        <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Distribuție pe roluri</div>
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Clienți</div>
            <div className="text-2xl font-serif text-blue-600">{counters?.by_role?.client || 0}</div>
          </div>
          <div className="text-center bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Specialiști</div>
            <div className="text-2xl font-serif text-emerald-600">{counters?.by_role?.specialist || 0}</div>
          </div>
          <div className="text-center bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Operatori</div>
            <div className="text-2xl font-serif text-amber-600">{counters?.by_role?.operator || 0}</div>
          </div>
        </div>
      </AdminCard>

      {/* Table */}
      <AdminCard>
        {loading ? (
          <div className="text-center py-6 text-sm text-slate-500">Se încarcă...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-12" data-testid="beta-testers-empty">
            <Sparkles className="w-10 h-10 text-slate-400 mx-auto mb-2" />
            <div className="text-sm text-slate-500">Niciun beta tester în această perioadă.</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">User</th>
                  <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Rol</th>
                  <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Sursă</th>
                  <th className="text-right py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Cereri</th>
                  <th className="text-right py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Wallet</th>
                  <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Înregistrat</th>
                  <th className="text-left py-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500">Ultima activitate</th>
                </tr>
              </thead>
              <tbody>
                {items.map(u => (
                  <tr key={u.id} className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30" data-testid={`beta-row-${u.id}`}>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        {u.picture ? (
                          <img src={u.picture} alt="" className="w-7 h-7 rounded-full object-cover" />
                        ) : (
                          <div className="w-7 h-7 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-xs">
                            {(u.name || "?")[0]?.toUpperCase()}
                          </div>
                        )}
                        <div className="min-w-0">
                          <div className="font-medium truncate">{u.name}</div>
                          <div className="text-[11px] text-slate-500 truncate">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800">{u.role}</span>
                      {u.verified && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 inline ml-1" />}
                      {u.banned && <Ban className="w-3.5 h-3.5 text-red-500 inline ml-1" />}
                    </td>
                    <td className="py-2.5 px-3">
                      {u.provenance === "google" ? (
                        <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">Google</span>
                      ) : (
                        <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400">Email</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right tabular-nums">
                      {u.requests_count > 0 ? (
                        <span className="text-emerald-600 font-semibold">{u.requests_count}</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right tabular-nums text-xs">{Number(u.wallet_balance || 0).toFixed(0)} RON</td>
                    <td className="py-2.5 px-3 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">{fmtDate(u.created_at)}</td>
                    <td className="py-2.5 px-3 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {u.last_seen ? fmtDate(u.last_seen) : <span className="text-slate-400 italic">niciodată</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminCard>
    </div>
  );
};

export default AdminBetaTesters;
