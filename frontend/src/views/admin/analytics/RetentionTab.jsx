import React, { useEffect, useState } from "react";
import axios from "axios";
import { Repeat, Loader2 } from "lucide-react";
import { API } from "../../DashShared";

const cellBg = (pct) => `rgba(59,130,246,${Math.min(0.9, 0.08 + pct / 110)})`;

export const RetentionTab = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    axios.get(`${API}/admin/analytics/retention?weeks=8`).then(r => setData(r.data)).catch(() => {});
  }, []);

  if (!data) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>;
  const maxWeeks = Math.max(1, ...data.cohorts.map(c => c.retention.length));

  return (
    <div className="space-y-4" data-testid="ag-retention-tab">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[["Vizitatori totali (istoric)", data.summary.total_visitors, "retention-kpi-total"],
          ["Vizitatori care revin", data.summary.returning_visitors, "retention-kpi-returning"],
          ["Rata de revenire", `${data.summary.returning_pct}%`, "retention-kpi-pct"]].map(([label, val, tid]) => (
          <div key={label} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid={tid}>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</div>
            <div className="mt-1 text-3xl font-black text-slate-900 dark:text-white">{val}</div>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 overflow-x-auto">
        <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-1 flex items-center gap-1.5">
          <Repeat className="w-4 h-4 text-blue-500" /> Cohorte săptămânale — % vizitatori care revin
        </h3>
        <p className="text-[11px] text-slate-400 mb-3">Fiecare rând = vizitatorii noi din acea săptămână. S0 = săptămâna primei vizite, S1+ = revin în săptămânile următoare.</p>
        <table className="text-xs" data-testid="retention-cohort-table">
          <thead>
            <tr className="text-left text-[10px] uppercase text-slate-400">
              <th className="pr-3 py-1.5">Cohortă (săpt.)</th>
              <th className="pr-3 py-1.5">Vizitatori</th>
              {Array.from({ length: maxWeeks }, (_, i) => <th key={i} className="px-1 py-1.5 text-center w-14">S{i}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.cohorts.map(c => (
              <tr key={c.cohort_week}>
                <td className="pr-3 py-1 font-mono text-slate-600 dark:text-slate-300">{c.cohort_week.slice(5)}</td>
                <td className="pr-3 py-1 font-bold text-slate-900 dark:text-white">{c.size}</td>
                {Array.from({ length: maxWeeks }, (_, i) => {
                  const r = c.retention[i];
                  return (
                    <td key={i} className="px-0.5 py-0.5">
                      {r && c.size > 0 ? (
                        <div className="rounded-md text-center py-1.5 font-bold text-white" style={{ background: cellBg(r.pct) }} title={`${r.active} vizitatori`}>
                          {r.pct}%
                        </div>
                      ) : <div className="py-1.5" />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {data.cohorts.every(c => c.size === 0) && <p className="text-center text-slate-400 text-sm py-6">Fără vizitatori încă — cohortele se populează pe măsură ce vin vizitatori.</p>}
      </div>
    </div>
  );
};
