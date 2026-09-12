// XOSRegistryPanel — Registrul de widget-uri (Etapa 1.1, Experience OS Foundation, D6:A)
import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { BookOpen, Plus, Check, CircleDot } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_STYLE = {
  active: "text-lime-700 bg-lime-50 border-lime-300 dark:text-lime-300 dark:bg-lime-900/20",
  experimental: "text-amber-700 bg-amber-50 border-amber-300 dark:text-amber-300 dark:bg-amber-900/20",
  legacy: "text-slate-500 bg-slate-50 border-slate-300 dark:bg-slate-800",
};

export const XOSRegistryPanel = ({ onChanged }) => {
  const [data, setData] = useState(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ id: "", label: "", desc: "", surface: "client_home", class: "EXPERIMENTAL" });

  const load = () => ax.get("/api/admin/xos/registry").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const patch = async (e, fields) => {
    try {
      await ax.patch(`/api/admin/xos/registry/${e.surface}/${e.id}`, fields);
      toast.success(`Widget «${e.label}» actualizat.`);
      load();
      onChanged?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Eroare.");
    }
  };

  const add = async () => {
    try {
      await ax.post("/api/admin/xos/registry", form);
      toast.success("Widget înregistrat. Va apărea în Layout Builder după activare + implementare renderer.");
      setAdding(false);
      setForm({ id: "", label: "", desc: "", surface: "client_home", class: "EXPERIMENTAL" });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Eroare.");
    }
  };

  if (!data) return null;
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3" data-testid="xos-registry-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-black flex items-center gap-2"><BookOpen className="w-4 h-4 text-lime-600" /> Registrul de Widget-uri (sursa unică de adevăr)</h2>
          <p className="text-[11px] text-slate-400 mt-0.5">Regula D6:A — orice widget nou intră prin registru. Nu se șterge nimic: statusul «legacy» îl scoate din Layout Builder.</p>
        </div>
        <button onClick={() => setAdding(!adding)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs border border-dashed border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800" data-testid="registry-add-btn">
          <Plus className="w-3.5 h-3.5" /> Înregistrează widget
        </button>
      </div>

      {adding && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3" data-testid="registry-add-form">
          <input value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })} placeholder="id (ex: house_health)" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs w-40" data-testid="registry-form-id" />
          <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="Etichetă" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs w-44" data-testid="registry-form-label" />
          <input value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} placeholder="Descriere" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs flex-1 min-w-[160px]" />
          <select value={form.class} onChange={(e) => setForm({ ...form, class: e.target.value })} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs">
            {data.classes.map((c) => <option key={c}>{c}</option>)}
          </select>
          <button onClick={add} className="px-3 py-1.5 rounded-lg text-xs font-bold bg-lime-500 text-black hover:bg-lime-400" data-testid="registry-form-save">Salvează</button>
        </div>
      )}

      <div className="space-y-1.5">
        {data.entries.map((e) => (
          <div key={`${e.surface}-${e.id}`} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 dark:border-slate-800 px-3 py-2" data-testid={`registry-row-${e.id}`}>
            <code className="text-[11px] font-bold text-slate-700 dark:text-slate-200 w-32 truncate">{e.id}</code>
            <span className="text-xs text-slate-500 flex-1 min-w-[140px] truncate">{e.label} — {e.desc}</span>
            <span className="text-[10px] font-black text-slate-400">{e.surface}</span>
            <select value={e.class} onChange={(ev) => patch(e, { class: ev.target.value })}
              className="bg-transparent border border-slate-200 dark:border-slate-700 rounded-lg px-1.5 py-1 text-[10px] font-bold" data-testid={`registry-class-${e.id}`}>
              {data.classes.map((c) => <option key={c}>{c}</option>)}
            </select>
            <select value={e.status} onChange={(ev) => patch(e, { status: ev.target.value })}
              className={`border rounded-full px-2 py-1 text-[10px] font-black ${STATUS_STYLE[e.status]}`} data-testid={`registry-status-${e.id}`}>
              {data.statuses.map((st) => <option key={st}>{st}</option>)}
            </select>
            <span className={`inline-flex items-center gap-1 text-[10px] font-bold ${e.implemented ? "text-lime-600" : "text-amber-500"}`} title={e.implemented ? "Renderer implementat în frontend" : "Necesită implementare renderer în cod"}>
              {e.implemented ? <Check className="w-3 h-3" /> : <CircleDot className="w-3 h-3" />}
              {e.implemented ? "renderer" : "fără renderer"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default XOSRegistryPanel;
