// Admin incidents manager — post incident, post updates, resolve.
// Companion to /status public page.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { AlertOctagon, Plus, MessageSquarePlus, CheckCircle2, Trash2, X } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const SEVERITIES = [
  { value: "minor",    label: "Minor",  color: "text-amber-700 dark:text-amber-300" },
  { value: "major",    label: "Major",  color: "text-orange-700 dark:text-orange-300" },
  { value: "critical", label: "Critic", color: "text-red-700 dark:text-red-300" },
];

const STATUSES = [
  { value: "investigating", label: "Investigăm" },
  { value: "identified",    label: "Identificat" },
  { value: "monitoring",    label: "Monitorizăm" },
  { value: "resolved",      label: "Rezolvat" },
];

const COMPONENTS = [
  { value: "api",                 label: "API" },
  { value: "database",            label: "Bază de date" },
  { value: "ai_concierge",        label: "AI Concierge" },
  { value: "payments",            label: "Plăți" },
  { value: "email",               label: "Email" },
  { value: "authentication",      label: "Autentificare" },
  { value: "push_notifications",  label: "Push" },
];

export const IncidentsCard = () => {
  const [items, setItems] = useState([]);
  const [creating, setCreating] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/admin/incidents?days=60`);
      setItems(r.data.items || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const deleteIncident = async (id) => {
    if (!window.confirm("Ștergi definitiv acest incident? Acțiunea nu poate fi anulată.")) return;
    try {
      await axios.delete(`${API}/admin/incidents/${id}`);
      load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const activeCount = items.filter(i => i.status !== "resolved").length;

  return (
    <AdminCard
      title={
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-orange-500" />
          <span>Incidente publice (Status Page)</span>
          {activeCount > 0 && (
            <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">
              {activeCount} în curs
            </span>
          )}
        </div>
      }
      action={
        <AdminBtn variant="primary" onClick={() => setCreating(true)} data-testid="incident-new-btn">
          <Plus className="w-3.5 h-3.5" /> Postează incident
        </AdminBtn>
      }
    >
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 leading-relaxed">
        Incidentele postate aici sunt vizibile public pe <code className="text-[10px] bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">/status</code>.
        Folosește pentru transparență când o componentă pică. Update-urile arată progresul investigării.
      </p>

      {creating && <NewIncidentModal onClose={() => setCreating(false)} onCreated={() => { setCreating(false); load(); }} />}
      {updatingId && (
        <UpdateIncidentModal
          incident={items.find(i => i.id === updatingId)}
          onClose={() => setUpdatingId(null)}
          onUpdated={() => { setUpdatingId(null); load(); }}
        />
      )}

      {items.length === 0 ? (
        <div className="text-center py-6 text-slate-400 italic text-xs" data-testid="incidents-empty">
          Niciun incident postat încă. Click "Postează incident" pentru a deschide unul.
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto" data-testid="incidents-list">
          {items.map(inc => {
            const sev = SEVERITIES.find(s => s.value === inc.severity) || SEVERITIES[0];
            const isActive = inc.status !== "resolved";
            const st = STATUSES.find(s => s.value === inc.status);
            return (
              <div
                key={inc.id}
                className={`rounded-lg border p-3 ${
                  isActive
                    ? "border-amber-300 bg-amber-50 dark:border-amber-500/40 dark:bg-amber-500/10"
                    : "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50"
                }`}
                data-testid={`admin-incident-${inc.id}`}
              >
                <div className="flex items-start gap-2 mb-1">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className={`text-[10px] uppercase font-bold ${sev.color}`}>{sev.label}</span>
                      <span className="text-[10px] uppercase font-bold text-slate-500">·</span>
                      <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-300">{st?.label || inc.status}</span>
                      {(inc.components || []).map(c => {
                        const compLabel = COMPONENTS.find(comp => comp.value === c)?.label || c;
                        return <span key={c} className="text-[9px] uppercase font-medium px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{compLabel}</span>;
                      })}
                    </div>
                    <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">{inc.title}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {new Date(inc.started_at).toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      {inc.duration_minutes != null && <> · durată: {inc.duration_minutes} min</>}
                      {" · "}{(inc.updates || []).length} update-uri
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {isActive && (
                      <button
                        onClick={() => setUpdatingId(inc.id)}
                        className="p-1.5 rounded text-blue-600 hover:bg-blue-100 dark:text-blue-300 dark:hover:bg-blue-500/20"
                        title="Adaugă update"
                        data-testid={`incident-update-btn-${inc.id}`}
                      >
                        <MessageSquarePlus className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => deleteIncident(inc.id)}
                      className="p-1.5 rounded text-red-600 hover:bg-red-100 dark:text-red-300 dark:hover:bg-red-500/20"
                      title="Șterge"
                      data-testid={`incident-delete-btn-${inc.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AdminCard>
  );
};


const Modal = ({ title, onClose, children }) => (
  <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div onClick={e => e.stopPropagation()} className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 max-w-lg w-full max-h-[90vh] overflow-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg text-slate-800 dark:text-slate-200">{title}</h3>
        <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
          <X className="w-4 h-4" />
        </button>
      </div>
      {children}
    </div>
  </div>
);


const NewIncidentModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ title: "", severity: "minor", components: [], message: "" });
  const [busy, setBusy] = useState(false);

  const toggleComp = (c) => {
    setForm(f => ({ ...f, components: f.components.includes(c) ? f.components.filter(x => x !== c) : [...f.components, c] }));
  };

  const submit = async () => {
    if (form.title.length < 4 || form.message.length < 4) {
      window.alert("Titlul și mesajul trebuie să aibă minim 4 caractere.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/admin/incidents`, form);
      onCreated();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Postează incident nou" onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Titlu</label>
          <input
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
            placeholder="Ex: Email delivery delayed"
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm"
            data-testid="incident-title-input"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Severitate</label>
          <div className="flex gap-2">
            {SEVERITIES.map(s => (
              <button
                key={s.value}
                onClick={() => setForm({ ...form, severity: s.value })}
                className={`flex-1 py-2 rounded-lg text-xs font-medium border transition ${
                  form.severity === s.value
                    ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                    : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                }`}
                data-testid={`incident-sev-${s.value}`}
              >{s.label}</button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Componente afectate</label>
          <div className="flex flex-wrap gap-1.5">
            {COMPONENTS.map(c => (
              <button
                key={c.value}
                onClick={() => toggleComp(c.value)}
                className={`text-xs px-2 py-1 rounded-full border transition ${
                  form.components.includes(c.value)
                    ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                    : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                }`}
                data-testid={`incident-comp-${c.value}`}
              >{c.label}</button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Mesaj inițial (vizibil public)</label>
          <textarea
            value={form.message}
            onChange={e => setForm({ ...form, message: e.target.value })}
            rows={4}
            placeholder="Ex: Investigăm o întârziere în trimiterea emailurilor. Toate cererile sunt înregistrate, doar trimiterea e amânată."
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm"
            data-testid="incident-message-input"
          />
        </div>
        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="flex-1 py-2 rounded-lg text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">Anulează</button>
          <button
            onClick={submit}
            disabled={busy}
            className="flex-1 py-2 rounded-lg text-sm bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60"
            data-testid="incident-create-submit"
          >
            {busy ? "Postez..." : "Postează"}
          </button>
        </div>
      </div>
    </Modal>
  );
};


const UpdateIncidentModal = ({ incident, onClose, onUpdated }) => {
  const [status, setStatus] = useState("identified");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (!incident) return null;

  const submit = async () => {
    if (message.length < 4) {
      window.alert("Mesajul trebuie să aibă minim 4 caractere.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/admin/incidents/${incident.id}/update`, { status, message });
      onUpdated();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`Update pentru: ${incident.title}`} onClose={onClose}>
      <div className="space-y-3">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-2 text-xs text-slate-600 dark:text-slate-300">
          <span className="font-semibold">Status curent:</span> {STATUSES.find(s => s.value === incident.status)?.label || incident.status} · {(incident.updates || []).length} update-uri postate
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Status nou</label>
          <div className="grid grid-cols-2 gap-2">
            {STATUSES.map(s => (
              <button
                key={s.value}
                onClick={() => setStatus(s.value)}
                className={`py-2 rounded-lg text-xs font-medium border transition ${
                  status === s.value
                    ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                    : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                }`}
                data-testid={`incident-update-status-${s.value}`}
              >
                {s.value === "resolved" && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" />}
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1 block">Mesaj (vizibil public)</label>
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            rows={4}
            placeholder="Ex: Cauza identificată — rate limit la provider. Rezolvăm acum."
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm"
            data-testid="incident-update-message-input"
          />
        </div>

        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="flex-1 py-2 rounded-lg text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">Anulează</button>
          <button
            onClick={submit}
            disabled={busy}
            className="flex-1 py-2 rounded-lg text-sm bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60"
            data-testid="incident-update-submit"
          >
            {busy ? "Salvez..." : status === "resolved" ? "Marchează rezolvat" : "Postează update"}
          </button>
        </div>
      </div>
    </Modal>
  );
};
