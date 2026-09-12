// IT Collaborators Hub — Admin page (super-admin only) for managing the internal/external dev team.
// Route: /admin/it-collaborators
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import {
  Code2, Users, Plus, Trash2, Edit3, X, Loader2, ChevronLeft,
  Bot, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, Bug,
  Save, Star, Sparkles, Mail, MapPin, DollarSign, Calendar, Activity,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const ROLE_OPTIONS = [
  { value: "frontend", label: "Frontend", color: "text-pink-600 dark:text-pink-400 bg-pink-100 dark:bg-pink-500/15" },
  { value: "backend", label: "Backend", color: "text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-500/15" },
  { value: "fullstack", label: "Full-stack", color: "text-violet-600 dark:text-violet-400 bg-violet-100 dark:bg-violet-500/15" },
  { value: "qa", label: "QA", color: "text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/15" },
  { value: "devops", label: "DevOps", color: "text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/15" },
  { value: "ai", label: "AI/ML", color: "text-cyan-600 dark:text-cyan-400 bg-cyan-100 dark:bg-cyan-500/15" },
  { value: "pm", label: "Product Manager", color: "text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700/40" },
  { value: "design", label: "Design", color: "text-fuchsia-600 dark:text-fuchsia-400 bg-fuchsia-100 dark:bg-fuchsia-500/15" },
  { value: "mobile", label: "Mobile", color: "text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-500/15" },
  { value: "other", label: "Altul", color: "text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/40" },
];

const SENIORITY_OPTIONS = ["junior", "mid", "senior", "principal"];
const STATUS_OPTIONS = [
  { value: "active", label: "Activ", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400" },
  { value: "paused", label: "Pauzat", color: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400" },
  { value: "archived", label: "Arhivat", color: "bg-slate-100 text-slate-600 dark:bg-slate-700/40 dark:text-slate-400" },
];

const roleMeta = (v) => ROLE_OPTIONS.find(r => r.value === v) || ROLE_OPTIONS[ROLE_OPTIONS.length - 1];
const statusMeta = (v) => STATUS_OPTIONS.find(s => s.value === v) || STATUS_OPTIONS[0];

// ─── Editor modal ───────────────────────────────────────────────────────────
const CollaboratorForm = ({ initial, onSave, onClose, saving }) => {
  const [form, setForm] = useState(() => ({
    name: initial?.name || "",
    email: initial?.email || "",
    role: initial?.role || "frontend",
    seniority: initial?.seniority || "mid",
    tech_stack: (initial?.tech_stack || []).join(", "),
    status: initial?.status || "active",
    hourly_rate: initial?.hourly_rate || "",
    location: initial?.location || "",
    notes: initial?.notes || "",
    started_at: initial?.started_at || "",
  }));
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      tech_stack: form.tech_stack.split(",").map(s => s.trim()).filter(Boolean),
      hourly_rate: form.hourly_rate === "" ? null : Number(form.hourly_rate),
    };
    onSave(payload);
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="collab-form-modal">
      <form onSubmit={submit} className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">{initial ? "Editează colaborator" : "Adaugă colaborator IT"}</h2>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Nume *</label>
            <input required value={form.name} onChange={e => set("name", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-name" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Email *</label>
            <input required type="email" value={form.email} onChange={e => set("email", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-email" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Rol *</label>
            <select value={form.role} onChange={e => set("role", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-role">
              {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Seniority</label>
            <select value={form.seniority} onChange={e => set("seniority", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-seniority">
              {SENIORITY_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Status</label>
            <select value={form.status} onChange={e => set("status", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-status">
              {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tech stack (separate prin virgulă)</label>
            <input value={form.tech_stack} onChange={e => set("tech_stack", e.target.value)} placeholder="React, FastAPI, MongoDB" className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-tech" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tarif orar (€)</label>
            <input type="number" step="0.01" value={form.hourly_rate} onChange={e => set("hourly_rate", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-rate" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Locație</label>
            <input value={form.location} onChange={e => set("location", e.target.value)} placeholder="București / Remote / Cluj" className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-location" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Început colaborare</label>
            <input type="date" value={form.started_at?.slice(0, 10) || ""} onChange={e => set("started_at", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-started" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Note interne</label>
            <textarea value={form.notes} onChange={e => set("notes", e.target.value)} rows={3} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm" data-testid="collab-notes" />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="collab-cancel">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="collab-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {initial ? "Salvează modificările" : "Adaugă"}
          </button>
        </div>
      </form>
    </div>
  );
};

// ─── Metrics quick editor ──────────────────────────────────────────────────
const MetricsEditor = ({ collab, onClose, onSaved }) => {
  const [form, setForm] = useState({
    bugs_introduced: collab.metrics?.bugs_introduced || 0,
    tasks_completed: collab.metrics?.tasks_completed || 0,
    review_score: collab.metrics?.review_score || 0,
    last_sprint: collab.metrics?.last_sprint || "",
  });
  const [saving, setSaving] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await ax.post(`/api/admin/it-collaborators/${collab.id}/metrics`, {
        bugs_introduced: Number(form.bugs_introduced),
        tasks_completed: Number(form.tasks_completed),
        review_score: Number(form.review_score),
        last_sprint: form.last_sprint || null,
      });
      onSaved(data);
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    } finally { setSaving(false); }
  };
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="metrics-modal">
      <form onSubmit={submit} className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Update metrici — {collab.name}</h2>
          <button type="button" onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Bug-uri introduse</label>
            <input type="number" value={form.bugs_introduced} onChange={e => setForm({ ...form, bugs_introduced: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="metrics-bugs" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Task-uri închise</label>
            <input type="number" value={form.tasks_completed} onChange={e => setForm({ ...form, tasks_completed: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="metrics-tasks" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Review score (0–10)</label>
            <input type="number" step="0.1" min="0" max="10" value={form.review_score} onChange={e => setForm({ ...form, review_score: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="metrics-review" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Last sprint</label>
            <input value={form.last_sprint} onChange={e => setForm({ ...form, last_sprint: e.target.value })} placeholder="2026-W08" className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="metrics-sprint" />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg text-slate-600">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="metrics-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează
          </button>
        </div>
      </form>
    </div>
  );
};

// ─── Main page ─────────────────────────────────────────────────────────────
const ITCollaboratorsHubPage = ({ embedded = false }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("active");
  const [filterRole, setFilterRole] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [metricsTarget, setMetricsTarget] = useState(null);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const params = {};
      if (filterStatus && filterStatus !== "all") params.status = filterStatus;
      if (filterRole) params.role = filterRole;
      const { data } = await ax.get("/api/admin/it-collaborators", { params });
      setItems(data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [filterStatus, filterRole]);

  const save = async (payload) => {
    setSaving(true);
    try {
      if (editing) {
        const { data } = await ax.patch(`/api/admin/it-collaborators/${editing.id}`, payload);
        setItems(it => it.map(x => x.id === data.id ? data : x));
      } else {
        const { data } = await ax.post("/api/admin/it-collaborators", payload);
        setItems(it => [data, ...it]);
      }
      setFormOpen(false); setEditing(null);
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    } finally { setSaving(false); }
  };

  const del = async (collab) => {
    if (!window.confirm(`Arhivează ${collab.name}? (status → archived)`)) return;
    try {
      await ax.delete(`/api/admin/it-collaborators/${collab.id}`);
      setItems(it => it.map(x => x.id === collab.id ? { ...x, status: "archived" } : x));
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    }
  };

  const stats = useMemo(() => {
    const active = items.filter(i => i.status === "active");
    const totalTasks = active.reduce((s, i) => s + (i.metrics?.tasks_completed || 0), 0);
    const totalBugs = active.reduce((s, i) => s + (i.metrics?.bugs_introduced || 0), 0);
    const avgReview = active.length ? active.reduce((s, i) => s + (i.metrics?.review_score || 0), 0) / active.length : 0;
    return { totalActive: active.length, totalTasks, totalBugs, avgReview };
  }, [items]);

  return (
    <div className={embedded ? "" : "min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8"} data-testid="it-collaborators-page">
      {!embedded && (
        <div className="mb-6 flex items-center gap-3">
          <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm">
            <ChevronLeft className="w-4 h-4" /> Admin
          </Link>
          <span className="text-slate-300">·</span>
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-blue-500" />
            <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">IT Collaborators Hub</h1>
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard icon={Users} label="Colaboratori activi" value={stats.totalActive} color="text-blue-500" />
        <StatCard icon={CheckCircle2} label="Task-uri total" value={stats.totalTasks} color="text-emerald-500" />
        <StatCard icon={Bug} label="Bug-uri introduse" value={stats.totalBugs} color="text-rose-500" />
        <StatCard icon={Star} label="Review score mediu" value={stats.avgReview.toFixed(1)} color="text-amber-500" />
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 p-0.5">
          {STATUS_OPTIONS.concat([{ value: "all", label: "Toți" }]).map(s => (
            <button
              key={s.value}
              onClick={() => setFilterStatus(s.value)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                filterStatus === s.value
                  ? "bg-blue-600 text-white"
                  : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
              data-testid={`filter-status-${s.value}`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <select value={filterRole} onChange={e => setFilterRole(e.target.value)} className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100" data-testid="filter-role">
          <option value="">Toate rolurile</option>
          {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <div className="flex-1" />
        <button
          onClick={() => navigate("/admin/it-collaborators/copilot")}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white flex items-center gap-1.5"
          data-testid="open-copilot"
        >
          <Bot className="w-3.5 h-3.5" /> AI Performance Copilot
        </button>
        <button
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5"
          data-testid="add-collaborator"
        >
          <Plus className="w-3.5 h-3.5" /> Adaugă colaborator
        </button>
      </div>

      {/* List */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {loading && <div className="p-10 flex items-center justify-center text-slate-500"><Loader2 className="w-5 h-5 animate-spin" /></div>}
        {error && <div className="p-6 text-rose-500 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {error}</div>}
        {!loading && !error && items.length === 0 && (
          <div className="p-10 text-center text-sm text-slate-500 dark:text-slate-400">
            Niciun colaborator. Apasă „Adaugă colaborator” pentru a începe.
          </div>
        )}
        {!loading && items.length > 0 && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.map(c => {
              const role = roleMeta(c.role);
              const st = statusMeta(c.status);
              const m = c.metrics || {};
              return (
                <div key={c.id} className="p-4 flex flex-wrap items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`collab-row-${c.id}`}>
                  <div className="flex-1 min-w-[200px]">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">{c.name}</span>
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${role.color}`}>{role.label}</span>
                      <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500">{c.seniority}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${st.color}`}>{st.label}</span>
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-3">
                      <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{c.email}</span>
                      {c.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{c.location}</span>}
                      {c.hourly_rate != null && <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{c.hourly_rate}€/h</span>}
                    </div>
                    {(c.tech_stack || []).length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {c.tech_stack.slice(0, 6).map(t => (
                          <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div className="text-center"><div className="text-emerald-500 font-bold">{m.tasks_completed || 0}</div><div className="text-[10px] text-slate-400">tasks</div></div>
                    <div className="text-center"><div className="text-rose-500 font-bold">{m.bugs_introduced || 0}</div><div className="text-[10px] text-slate-400">bugs</div></div>
                    <div className="text-center"><div className="text-amber-500 font-bold">{(m.review_score || 0).toFixed(1)}</div><div className="text-[10px] text-slate-400">review</div></div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setMetricsTarget(c)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Update metrici" data-testid={`metrics-${c.id}`}>
                      <Activity className="w-4 h-4" />
                    </button>
                    <button onClick={() => { setEditing(c); setFormOpen(true); }} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Editează" data-testid={`edit-${c.id}`}>
                      <Edit3 className="w-4 h-4" />
                    </button>
                    {c.status !== "archived" && (
                      <button onClick={() => del(c)} className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10" title="Arhivează" data-testid={`delete-${c.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {formOpen && (
        <CollaboratorForm
          initial={editing}
          saving={saving}
          onClose={() => { setFormOpen(false); setEditing(null); }}
          onSave={save}
        />
      )}
      {metricsTarget && (
        <MetricsEditor
          collab={metricsTarget}
          onClose={() => setMetricsTarget(null)}
          onSaved={(updated) => {
            setItems(it => it.map(x => x.id === updated.id ? updated : x));
            setMetricsTarget(null);
          }}
        />
      )}
    </div>
  );
};

const StatCard = ({ icon: Icon, label, value, color }) => (
  <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <Icon className={`w-4 h-4 ${color}`} />
    </div>
    <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
  </div>
);

export default ITCollaboratorsHubPage;
export { ITCollaboratorsHubPage };
