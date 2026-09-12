import React, { useEffect, useState } from "react";
import axios from "axios";
import { CalendarClock, Plus, Check, X, Send, Sparkles } from "lucide-react";
import { API } from "../pages/DashShared";
import { formatApiError } from "../auth";
import { GREEN, CTA, Sheet } from "../pages/clientv2/ui";

const CAT_LABELS = {
  zugravit: "Zugrăvit", parchet: "Parchet", faianta: "Faianță / Gresie", handyman: "Handyman",
  gips_carton: "Gips-carton", hvac: "HVAC / Climatizare", electric: "Electric", plumbing: "Sanitar",
  interior_design: "Design Interior",
};
const FREQS = [[3, "la 3 luni"], [6, "la 6 luni"], [12, "anual"], [24, "la 2 ani"], [36, "la 3 ani"]];
const fmtDate = (d) => new Date(`${d}T00:00:00`).toLocaleDateString("ro-RO", { day: "numeric", month: "short", year: "numeric" });

const StatusChip = ({ status }) => {
  const map = {
    overdue: ["Termen depășit", "bg-rose-50 text-rose-500"],
    due_soon: ["În curând", "bg-amber-50 text-amber-600"],
    ok: ["Planificat", "bg-slate-50 text-slate-500"],
  };
  const [label, cls] = map[status] || map.ok;
  return <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${cls}`}>{label}</span>;
};

const AddTaskSheet = ({ properties, defaultPropId, templates, existingTitles, onClose, onAdded }) => {
  const [custom, setCustom] = useState(false);
  const [form, setForm] = useState({ property_id: defaultPropId, title: "", category: "handyman", frequency_months: 12, next_due: "" });
  const [loading, setLoading] = useState(false);

  const add = async (payload) => {
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/maintenance/tasks`, payload);
      onAdded(data);
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  return (
    <Sheet title="Adaugă în calendar" onClose={onClose} testid="mc-add-sheet">
      <div className="space-y-3">
        {properties.length > 1 && (
          <select value={form.property_id} onChange={e => setForm(f => ({ ...f, property_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-add-property">
            {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
        {!custom ? (
          <>
            <p className="text-xs text-slate-400">Alege dintre reviziile standard — le adaugi cu un singur tap.</p>
            <div className="grid grid-cols-1 gap-2">
              {templates.map(t => {
                const added = existingTitles.has(`${form.property_id}|${t.title}`);
                return (
                  <button key={t.key} disabled={added || loading} onClick={() => add({ property_id: form.property_id, template_key: t.key })}
                    data-testid={`mc-tpl-${t.key}`}
                    className={`flex items-center gap-3 rounded-2xl border p-3.5 text-left transition-colors ${added ? "border-slate-100 bg-slate-50 opacity-60" : "border-slate-200 bg-white active:scale-[0.99]"}`}>
                    <span className="w-9 h-9 rounded-xl bg-[#34C759]/10 flex items-center justify-center shrink-0">
                      {added ? <Check className="w-4 h-4" style={{ color: GREEN }} /> : <CalendarClock className="w-4 h-4" style={{ color: GREEN }} />}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm font-bold text-slate-900">{t.title}</span>
                      <span className="block text-[11px] text-slate-400">{CAT_LABELS[t.category] || t.category} · {FREQS.find(([m]) => m === t.frequency_months)?.[1] || `la ${t.frequency_months} luni`}</span>
                    </span>
                    {!added && <Plus className="w-4 h-4 text-slate-300 shrink-0" />}
                  </button>
                );
              })}
            </div>
            <button onClick={() => setCustom(true)} data-testid="mc-add-custom-toggle" className="w-full py-3 rounded-full bg-slate-50 text-xs font-bold text-slate-600">
              + Task personalizat
            </button>
          </>
        ) : (
          <form onSubmit={(e) => { e.preventDefault(); add({ ...form, next_due: form.next_due || undefined }); }} className="space-y-3">
            <input required minLength={3} placeholder="ex: Verificare acoperiș" value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-custom-title" />
            <div className="grid grid-cols-2 gap-2">
              <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-custom-category">
                {Object.entries(CAT_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
              </select>
              <select value={form.frequency_months} onChange={e => setForm(f => ({ ...f, frequency_months: parseInt(e.target.value) }))}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-custom-freq">
                {FREQS.map(([m, label]) => <option key={m} value={m}>{label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-500">Prima scadență (opțional)</label>
              <input type="date" value={form.next_due} onChange={e => setForm(f => ({ ...f, next_due: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-custom-due" />
            </div>
            <CTA testid="mc-custom-submit" disabled={loading}>{loading ? "..." : "Adaugă în calendar"}</CTA>
            <button type="button" onClick={() => setCustom(false)} className="w-full py-2 text-xs font-bold text-slate-400">← Înapoi la reviziile standard</button>
          </form>
        )}
      </div>
    </Sheet>
  );
};

const RequestSheet = ({ task, trusted, onClose, onDone }) => {
  const match = trusted.find(s => s.categories?.includes(task.category) || s.last_category === task.category) || trusted[0];
  const [mode, setMode] = useState(match ? "direct" : "open");
  const [form, setForm] = useState({ description: "", budget_estimate: "" });
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/maintenance/tasks/${task.id}/request`, {
        mode, specialist_id: mode === "direct" ? match?.specialist_id : undefined,
        description: form.description || undefined,
        budget_estimate: form.budget_estimate ? parseFloat(form.budget_estimate) : null,
      });
      setCreated(data);
      onDone?.(data);
    } catch (e2) { alert(formatApiError(e2)); }
    finally { setLoading(false); }
  };

  return (
    <Sheet title={created ? "Cerere trimisă" : task.title} onClose={onClose} testid="mc-request-sheet">
      {created ? (
        <div className="text-center py-6" data-testid="mc-request-success">
          <Check className="w-12 h-12 mx-auto rounded-full p-2.5 text-white" style={{ background: GREEN }} />
          <h3 className="mt-3 text-lg font-black text-slate-900">
            {created.direct_specialist_name ? `Trimisă direct către ${created.direct_specialist_name}` : "Publicată — primești oferte în curând"}
          </h3>
          <p className="mt-1 text-sm text-slate-400">O găsești în tabul „Lucrări". Taskul rămâne în calendar și se reprogramează după finalizare.</p>
          <div className="mt-5 max-w-[220px] mx-auto"><CTA testid="mc-request-done" onClick={onClose}>Am înțeles</CTA></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          {match && (
            <div className="space-y-2">
              <button type="button" onClick={() => setMode("direct")} data-testid="mc-req-direct"
                className={`w-full flex items-center gap-3 rounded-2xl border-2 p-3.5 text-left ${mode === "direct" ? "border-[#34C759] bg-[#34C759]/5" : "border-slate-200 bg-white"}`}>
                <span className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-black shrink-0" style={{ background: GREEN }}>{(match.name || "S")[0]}</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-bold text-slate-900">Direct la {match.name}</span>
                  <span className="block text-[11px] text-slate-400">A mai lucrat la tine · fără licitație · taxa lui de lead 0</span>
                </span>
              </button>
              <button type="button" onClick={() => setMode("open")} data-testid="mc-req-open"
                className={`w-full flex items-center gap-3 rounded-2xl border-2 p-3.5 text-left ${mode === "open" ? "border-[#34C759] bg-[#34C759]/5" : "border-slate-200 bg-white"}`}>
                <span className="w-9 h-9 rounded-xl bg-slate-50 flex items-center justify-center shrink-0"><Sparkles className="w-4 h-4 text-slate-400" /></span>
                <span className="flex-1">
                  <span className="block text-sm font-bold text-slate-900">Publică pentru oferte</span>
                  <span className="block text-[11px] text-slate-400">Compari mai multe oferte din marketplace</span>
                </span>
              </button>
            </div>
          )}
          <textarea rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder={`Detalii (opțional) — ex: programare „${task.title}” săptămâna viitoare`}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm resize-none" data-testid="mc-req-desc" />
          <input type="number" min="0" value={form.budget_estimate} onChange={e => setForm(f => ({ ...f, budget_estimate: e.target.value }))}
            placeholder="Buget estimat RON (opțional)" className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="mc-req-budget" />
          <CTA testid="mc-req-submit" disabled={loading}>
            <Send className="w-4 h-4 inline mr-1 -mt-0.5" />{loading ? "Se trimite..." : mode === "direct" && match ? `Trimite direct către ${match.name.split(" ")[0]}` : "Publică cererea"}
          </CTA>
        </form>
      )}
    </Sheet>
  );
};

export const MaintenanceCalendar = ({ properties = [], prop, onRequestCreated }) => {
  const [tasks, setTasks] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [trusted, setTrusted] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [requestFor, setRequestFor] = useState(null);

  const load = () => axios.get(`${API}/maintenance/tasks`).then(r => setTasks(r.data?.tasks || [])).catch(() => {});
  useEffect(() => {
    Promise.all([
      load(),
      axios.get(`${API}/maintenance/templates`).then(r => setTemplates(r.data?.templates || [])).catch(() => {}),
      axios.get(`${API}/trusted-specialists`).then(r => setTrusted(r.data?.specialists || [])).catch(() => {}),
    ]).finally(() => setLoaded(true));
  }, []);

  if (!loaded || properties.length === 0) return null;
  const existingTitles = new Set(tasks.map(t => `${t.property_id}|${t.title}`));

  const complete = async (t) => {
    try { await axios.post(`${API}/maintenance/tasks/${t.id}/complete`); load(); }
    catch (e) { alert(formatApiError(e)); }
  };
  const remove = async (t) => {
    if (!window.confirm(`Ștergi „${t.title}" din calendar?`)) return;
    try { await axios.delete(`${API}/maintenance/tasks/${t.id}`); load(); }
    catch (e) { alert(formatApiError(e)); }
  };

  return (
    <div className="px-5 pt-8 pb-4 lg:max-w-3xl" data-testid="mc-section">
      <div className="flex items-center gap-2 px-1">
        <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5 flex-1">
          <CalendarClock className="w-3.5 h-3.5" style={{ color: GREEN }} /> Calendar mentenanță
        </h3>
        <button onClick={() => setShowAdd(true)} data-testid="mc-add-btn"
          className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-slate-900 text-white text-[11px] font-bold">
          <Plus className="w-3.5 h-3.5" /> Adaugă
        </button>
      </div>
      {tasks.length === 0 ? (
        <button onClick={() => setShowAdd(true)} data-testid="mc-empty-cta"
          className="mt-3 w-full rounded-3xl border-2 border-dashed border-slate-200 bg-white p-5 text-left">
          <div className="text-sm font-black text-slate-900">Previne problemele scumpe</div>
          <p className="mt-1 text-xs text-slate-400">Adaugă reviziile periodice (centrală, clima, coș de fum...) — îți amintim când e scadent și soliciți oferta în 1 click.</p>
          <span className="mt-3 inline-block text-xs font-bold" style={{ color: GREEN }}>Configurează în 30 de secunde →</span>
        </button>
      ) : (
        <div className="mt-3 space-y-2">
          {tasks.map(t => (
            <div key={t.id} className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid={`mc-task-${t.id}`}>
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-black text-slate-900 truncate">{t.title}</div>
                  <div className="text-[11px] text-slate-400">
                    {fmtDate(t.next_due)}{properties.length > 1 && t.property_name ? ` · ${t.property_name}` : ""}{t.last_done ? ` · ultima: ${fmtDate(t.last_done)}` : ""}
                  </div>
                </div>
                <StatusChip status={t.status} />
                <button onClick={() => remove(t)} aria-label="Șterge task" data-testid={`mc-task-del-${t.id}`} className="p-1 -mr-1 text-slate-300 hover:text-rose-400"><X className="w-4 h-4" /></button>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button onClick={() => setRequestFor(t)} data-testid={`mc-task-request-${t.id}`}
                  className="py-2.5 rounded-full text-xs font-black text-white" style={{ background: GREEN }}>
                  Solicită ofertă
                </button>
                <button onClick={() => complete(t)} data-testid={`mc-task-done-${t.id}`}
                  className="py-2.5 rounded-full bg-slate-50 text-xs font-bold text-slate-600 flex items-center justify-center gap-1">
                  <Check className="w-3.5 h-3.5" /> Am rezolvat-o
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showAdd && (
        <AddTaskSheet properties={properties} defaultPropId={prop?.id || properties[0]?.id} templates={templates}
          existingTitles={existingTitles} onClose={() => setShowAdd(false)} onAdded={() => { load(); }} />
      )}
      {requestFor && (
        <RequestSheet task={requestFor} trusted={trusted} onClose={() => setRequestFor(null)}
          onDone={() => { load(); onRequestCreated?.(); }} />
      )}
    </div>
  );
};
