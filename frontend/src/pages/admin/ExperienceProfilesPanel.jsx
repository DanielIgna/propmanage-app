// ExperienceProfilesPanel — Role Experience Manager (Etapa 1.3, Experience OS Foundation)
import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { UserCog, Save } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const THEME_LABELS = { system: "Sistem", dark: "Întunecat", light: "Luminos" };

export const ExperienceProfilesPanel = () => {
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState("");

  const load = () => ax.get("/api/admin/experience-profiles").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (p) => {
    setSaving(p.role);
    try {
      await ax.put(`/api/admin/experience-profiles/${p.role}`, p);
      toast.success(`Profilul de experiență «${p.role}» salvat.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare.");
    } finally { setSaving(""); }
  };

  const upd = (role, patch) =>
    setData({ ...data, profiles: data.profiles.map((p) => (p.role === role ? { ...p, ...patch } : p)) });

  if (!data) return null;
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3" data-testid="experience-profiles-panel">
      <div>
        <h2 className="text-sm font-black flex items-center gap-2"><UserCog className="w-4 h-4 text-lime-600" /> Role Experience Manager</h2>
        <p className="text-[11px] text-slate-400 mt-0.5">Profilul de experiență per rol: unde intră după login, tema implicită și suprafața de layout.</p>
      </div>
      <div className="space-y-2">
        {data.profiles.map((p) => (
          <div key={p.role} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 dark:border-slate-800 px-3 py-2.5" data-testid={`exp-profile-${p.role}`}>
            <span className="text-xs font-black uppercase text-slate-700 dark:text-slate-200 w-24">{p.role}</span>
            <label className="text-[10px] text-slate-400">Intrare:</label>
            <input value={p.entry_route} onChange={(e) => upd(p.role, { entry_route: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs w-36" data-testid={`exp-entry-${p.role}`} />
            <label className="text-[10px] text-slate-400">Temă:</label>
            <select value={p.default_theme} onChange={(e) => upd(p.role, { default_theme: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs" data-testid={`exp-theme-${p.role}`}>
              {data.themes.map((t) => <option key={t} value={t}>{THEME_LABELS[t] || t}</option>)}
            </select>
            <label className="text-[10px] text-slate-400">Suprafață:</label>
            <select value={p.layout_surface} onChange={(e) => upd(p.role, { layout_surface: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs" data-testid={`exp-surface-${p.role}`}>
              <option value="">—</option>
              {data.surfaces.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button onClick={() => save(p)} disabled={saving === p.role}
              className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-lime-500 text-black hover:bg-lime-400 disabled:opacity-50" data-testid={`exp-save-${p.role}`}>
              <Save className="w-3 h-3" /> {saving === p.role ? "..." : "Salvează"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ExperienceProfilesPanel;
