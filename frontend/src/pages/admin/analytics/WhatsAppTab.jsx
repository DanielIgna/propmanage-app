import React, { useEffect, useState } from "react";
import axios from "axios";
import { MessageCircle, Users, UserPlus, Copy, Loader2 } from "lucide-react";
import { API } from "../../DashShared";
import { toast } from "sonner";

const MEDIUMS = [["group", "Grupuri"], ["channel", "Canale"], ["private", "Privat"], ["status", "Status"]];

export const WhatsAppTab = ({ period }) => {
  const [data, setData] = useState(null);
  const [gen, setGen] = useState({ medium: "group", campaign: "" });

  useEffect(() => {
    setData(null);
    axios.get(`${API}/admin/analytics/whatsapp?period=${period}`).then(r => setData(r.data)).catch(() => {});
  }, [period]);

  if (!data) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>;

  const base = window.location.origin;
  const slug = gen.campaign.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const genLink = `${base}/?utm_source=whatsapp&utm_medium=${gen.medium}${slug ? `&utm_campaign=${slug}` : ""}`;
  const mediumMap = Object.fromEntries(data.by_medium.map(m => [m.key, m]));

  return (
    <div className="space-y-4" data-testid="ag-whatsapp-tab">
      <div className="grid grid-cols-3 gap-3">
        {[["Sesiuni din WhatsApp", data.summary.sessions, MessageCircle], ["Vizitatori unici", data.summary.visitors, Users], ["Conturi create", data.summary.accounts_created, UserPlus]].map(([label, val, Icon]) => (
          <div key={label} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid={`wa-kpi-${label.toLowerCase().replace(/[^a-z]+/g, '-')}`}>
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"><Icon className="w-4 h-4 text-[#25D366]" /> {label}</div>
            <div className="mt-1 text-3xl font-black text-slate-900 dark:text-white">{val}</div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
        <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">Pe tip de distribuție (utm_medium)</h3>
        <div className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="wa-medium-grid">
          {MEDIUMS.map(([key, label]) => {
            const m = mediumMap[key] || { sessions: 0, visitors: 0, accounts_created: 0 };
            return (
              <div key={key} className="rounded-xl bg-slate-50 dark:bg-slate-700/40 p-3" data-testid={`wa-medium-${key}`}>
                <div className="text-xs font-bold text-slate-500">WhatsApp {label}</div>
                <div className="mt-1 text-2xl font-black text-slate-900 dark:text-white">{m.visitors}</div>
                <div className="text-[11px] text-slate-400">{m.sessions} sesiuni · {m.accounts_created} conturi</div>
              </div>
            );
          })}
        </div>
        {mediumMap["nespecificat"] && (
          <p className="mt-2 text-[11px] text-slate-400">+ {mediumMap["nespecificat"].visitors} vizitatori WhatsApp fără utm_medium (link-uri vechi / referrer).</p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-x-auto">
        <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm p-4 pb-0">Pe campanie (utm_campaign)</h3>
        <table className="w-full text-sm mt-2" data-testid="wa-campaign-table">
          <thead><tr className="text-left text-[11px] uppercase text-slate-400 border-b border-slate-100 dark:border-slate-700">
            <th className="px-4 py-2">Campanie</th><th className="px-4 py-2">Vizitatori</th><th className="px-4 py-2">Sesiuni</th><th className="px-4 py-2">Conturi</th>
          </tr></thead>
          <tbody>
            {data.by_campaign.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-400 text-xs">Fără trafic WhatsApp în perioadă — distribuie un link cu UTM (generator mai jos).</td></tr>}
            {data.by_campaign.map(c => (
              <tr key={c.key} className="border-b border-slate-50 dark:border-slate-700/50">
                <td className="px-4 py-2 font-mono text-xs">{c.label}</td>
                <td className="px-4 py-2 font-bold">{c.visitors}</td>
                <td className="px-4 py-2">{c.sessions}</td>
                <td className="px-4 py-2">{c.accounts_created}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-2xl border-2 border-dashed border-[#25D366]/40 bg-[#25D366]/5 p-4" data-testid="wa-link-generator">
        <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm flex items-center gap-1.5"><MessageCircle className="w-4 h-4 text-[#25D366]" /> Generator link UTM pentru WhatsApp</h3>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="text-xs font-bold text-slate-500">Tip distribuție
            <select value={gen.medium} onChange={e => setGen(g => ({ ...g, medium: e.target.value }))} data-testid="wa-gen-medium"
              className="mt-1 block px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-normal">
              {MEDIUMS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="text-xs font-bold text-slate-500 flex-1 min-w-[180px]">Nume campanie
            <input value={gen.campaign} onChange={e => setGen(g => ({ ...g, campaign: e.target.value }))} data-testid="wa-gen-campaign"
              placeholder="ex: presedinti_bloc" className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-normal" />
          </label>
          <button onClick={() => { navigator.clipboard.writeText(genLink); toast.success("Link copiat — lipește-l în WhatsApp"); }} data-testid="wa-gen-copy"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white" style={{ background: "#25D366" }}>
            <Copy className="w-3.5 h-3.5" /> Copiază linkul
          </button>
        </div>
        <div className="mt-2 text-xs font-mono text-slate-500 break-all" data-testid="wa-gen-link">{genLink}</div>
        <p className="mt-2 text-[11px] text-slate-400">Vizitele din acest link apar aici, în sursele de trafic (WhatsApp) și în Microsoft Clarity (filtrare după utm_source/medium/campaign).</p>
      </div>
    </div>
  );
};
