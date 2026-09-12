import React, { useEffect, useState } from "react";
import axios from "axios";
import { TrendingDown, Timer, Loader2 } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, LabelList } from "recharts";
import { API } from "../../DashShared";

const Stat = ({ label, value, testid }) => (
  <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid={testid}>
    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</div>
    <div className="mt-1 text-3xl font-black text-slate-900 dark:text-white">{value}</div>
  </div>
);

export const BounceTab = ({ period }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    setData(null);
    axios.get(`${API}/admin/analytics/bounce?period=${period}`).then(r => setData(r.data)).catch(() => {});
  }, [period]);

  if (!data) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>;
  const s = data.summary;

  return (
    <div className="space-y-4" data-testid="ag-bounce-tab">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Sesiuni" value={s.sessions} testid="bounce-kpi-sessions" />
        <Stat label="Bounce-uri" value={s.bounces} testid="bounce-kpi-bounces" />
        <Stat label="Bounce rate" value={`${s.bounce_rate_pct}%`} testid="bounce-kpi-rate" />
        <Stat label="Quick bounce (<10s)" value={`${s.quick_bounce_pct}%`} testid="bounce-kpi-quick" />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-2 flex items-center gap-1.5"><TrendingDown className="w-4 h-4 text-rose-500" /> Bounce rate zilnic</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data.series}>
              <defs><linearGradient id="gb" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f43f5e" stopOpacity={0.4} /><stop offset="100%" stopColor="#f43f5e" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
              <XAxis dataKey="day" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} unit="%" />
              <Tooltip formatter={(v) => [`${v}%`, "Bounce"]} />
              <Area type="monotone" dataKey="bounce_pct" stroke="#f43f5e" fill="url(#gb)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm mb-2 flex items-center gap-1.5"><Timer className="w-4 h-4 text-amber-500" /> Distribuție durată sesiuni</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.duration_buckets}>
              <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="sessions" fill="#f59e0b" radius={[6, 6, 0, 0]} barSize={34}>
                <LabelList dataKey="sessions" position="top" style={{ fontSize: 11, fontWeight: 700 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-x-auto">
          <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm p-4 pb-0">Bounce pe surse</h3>
          <table className="w-full text-sm mt-2" data-testid="bounce-by-source-table">
            <thead><tr className="text-left text-[11px] uppercase text-slate-400 border-b border-slate-100 dark:border-slate-700">
              <th className="px-4 py-2">Sursă</th><th className="px-4 py-2">Sesiuni</th><th className="px-4 py-2">Bounce</th>
            </tr></thead>
            <tbody>
              {data.by_source.length === 0 && <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-400 text-xs">Fără date</td></tr>}
              {data.by_source.map(r => (
                <tr key={r.source} className="border-b border-slate-50 dark:border-slate-700/50">
                  <td className="px-4 py-2 font-semibold">{r.source}</td>
                  <td className="px-4 py-2">{r.sessions}</td>
                  <td className="px-4 py-2 font-bold" style={{ color: r.bounce_rate_pct > 60 ? "#f43f5e" : r.bounce_rate_pct > 35 ? "#f59e0b" : "#10b981" }}>{r.bounce_rate_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-x-auto">
          <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm p-4 pb-0">Bounce pe pagini de intrare</h3>
          <table className="w-full text-sm mt-2" data-testid="bounce-by-entry-table">
            <thead><tr className="text-left text-[11px] uppercase text-slate-400 border-b border-slate-100 dark:border-slate-700">
              <th className="px-4 py-2">Pagină de intrare</th><th className="px-4 py-2">Sesiuni</th><th className="px-4 py-2">Bounce</th>
            </tr></thead>
            <tbody>
              {data.entry_pages.length === 0 && <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-400 text-xs">Fără date</td></tr>}
              {data.entry_pages.map(r => (
                <tr key={r.path} className="border-b border-slate-50 dark:border-slate-700/50">
                  <td className="px-4 py-2 font-mono text-xs truncate max-w-[220px]">{r.path}</td>
                  <td className="px-4 py-2">{r.sessions}</td>
                  <td className="px-4 py-2 font-bold" style={{ color: r.bounce_rate_pct > 60 ? "#f43f5e" : r.bounce_rate_pct > 35 ? "#f59e0b" : "#10b981" }}>{r.bounce_rate_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
