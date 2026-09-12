// House Health Admin Panel — F4.1: Plans CRUD + Scoring config.
// Route: /admin/house-health (admin-only)
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Heart, Plus, Trash2, Edit3, Save, X, Loader2, Sliders,
  Package, Check, AlertCircle, ChevronLeft
} from "lucide-react";
import { Link } from "react-router-dom";
import { API } from "../DashShared";
import { ThemeSwitcher } from "../../components/ThemeSwitcher";

const EMPTY_PLAN = {
  slug: "", name: "", description: "",
  price_eur: 0, currency: "EUR", billing_period: "monthly",
  trial_days: 0, features: [], stripe_price_id: "",
  lead_commission_pct: 10, sort_order: 0, active: true,
};

const AdminHouseHealthPage = () => {
  const [tab, setTab] = useState("plans");

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-5">
          <Link to="/admin" className="text-stone-400 hover:text-stone-200 inline-flex items-center gap-1 text-sm" data-testid="hh-admin-back">
            <ChevronLeft className="w-4 h-4" /> Înapoi în Admin
          </Link>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Heart className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">House Health · Admin</h1>
            <p className="text-xs text-stone-400">Configurare planuri abonament și formula scor proprietate</p>
          </div>
          <ThemeSwitcher />
        </div>

        <div className="flex gap-2 mb-5">
          <button
            onClick={() => setTab("plans")}
            data-testid="hh-admin-tab-plans"
            className={`px-4 py-2 rounded-lg text-sm font-semibold inline-flex items-center gap-2 transition-colors ${
              tab === "plans" ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40" : "bg-stone-900 text-stone-300 border border-stone-800 hover:border-stone-700"
            }`}
          >
            <Package className="w-4 h-4" /> Planuri
          </button>
          <button
            onClick={() => setTab("scoring")}
            data-testid="hh-admin-tab-scoring"
            className={`px-4 py-2 rounded-lg text-sm font-semibold inline-flex items-center gap-2 transition-colors ${
              tab === "scoring" ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40" : "bg-stone-900 text-stone-300 border border-stone-800 hover:border-stone-700"
            }`}
          >
            <Sliders className="w-4 h-4" /> Formula scor
          </button>
        </div>

        {tab === "plans" ? <PlansTab /> : <ScoringTab />}
      </div>
    </div>
  );
};

// ============================== PLANS TAB ==============================
const PlansTab = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_PLAN);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/house-health/plans`);
      setPlans(r.data?.items || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const startEdit = (p) => {
    setEditingId(p.id);
    setForm({ ...p, features: p.features || [], stripe_price_id: p.stripe_price_id || "" });
    setShowCreate(false);
    setError("");
  };

  const cancelEdit = () => { setEditingId(null); setForm(EMPTY_PLAN); setError(""); };

  const save = async () => {
    setError("");
    try {
      const cleanForm = { ...form, features: form.features.filter(Boolean) };
      if (editingId) {
        await axios.patch(`${API}/admin/house-health/plans/${editingId}`, cleanForm);
      } else {
        await axios.post(`${API}/admin/house-health/plans`, cleanForm);
      }
      setShowCreate(false);
      setEditingId(null);
      setForm(EMPTY_PLAN);
      await load();
    } catch (e) {
      const msg = e?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : JSON.stringify(msg) || "Eroare salvare");
    }
  };

  const archive = async (id) => {
    if (!window.confirm("Arhivezi acest plan? (active = false; nu se șterge definitiv)")) return;
    await axios.delete(`${API}/admin/house-health/plans/${id}`);
    await load();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold">Planuri abonament ({plans.length})</h2>
        <button
          onClick={() => { setShowCreate(true); setEditingId(null); setForm(EMPTY_PLAN); }}
          data-testid="hh-admin-plan-new"
          className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-white text-xs font-semibold inline-flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Plan nou
        </button>
      </div>

      {(showCreate || editingId) && (
        <PlanForm form={form} setForm={setForm} onSave={save} onCancel={cancelEdit} error={error} editing={!!editingId} />
      )}

      {loading && <div className="text-xs text-stone-500">Se încarcă...</div>}
      {!loading && plans.length === 0 && !showCreate && (
        <div className="text-xs text-stone-500 italic p-4 bg-stone-900/40 rounded-xl border border-stone-800">
          Niciun plan încă. Click „Plan nou” pentru a crea primul.
        </div>
      )}

      <ul className="space-y-2" data-testid="hh-admin-plans-list">
        {plans.map((p, i) => (
          <li
            key={p.id}
            data-testid={`hh-admin-plan-${i}`}
            className={`p-4 rounded-xl border ${p.active ? "border-stone-700 bg-stone-900/40" : "border-stone-800 bg-stone-900/20 opacity-60"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base font-bold text-stone-100">{p.name}</span>
                  <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-stone-800 text-stone-400">{p.slug}</span>
                  {!p.active && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-400">arhivat</span>}
                </div>
                <div className="text-xs text-stone-400 mb-2">{p.description || "—"}</div>
                <div className="flex flex-wrap gap-3 text-xs">
                  <span className="text-emerald-300 font-semibold">{p.price_eur} {p.currency} / {p.billing_period === "monthly" ? "lună" : p.billing_period === "yearly" ? "an" : "o dată"}</span>
                  {p.trial_days > 0 && <span className="text-cyan-300">{p.trial_days} zile trial</span>}
                  <span className="text-amber-300">Lead commission: {p.lead_commission_pct}%</span>
                  {p.stripe_price_id && <span className="text-stone-500 text-[10px]">stripe: {p.stripe_price_id}</span>}
                </div>
                {p.features && p.features.length > 0 && (
                  <ul className="mt-2 text-[11px] text-stone-300 list-disc list-inside">
                    {p.features.map((f, fi) => <li key={fi}>{f}</li>)}
                  </ul>
                )}
              </div>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => startEdit(p)} data-testid={`hh-admin-plan-edit-${i}`} className="p-1.5 rounded hover:bg-stone-800 text-stone-400">
                  <Edit3 className="w-4 h-4" />
                </button>
                {p.active && (
                  <button onClick={() => archive(p.id)} data-testid={`hh-admin-plan-archive-${i}`} className="p-1.5 rounded hover:bg-rose-500/15 text-rose-400">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

const PlanForm = ({ form, setForm, onSave, onCancel, error, editing }) => {
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const featuresText = (form.features || []).join("\n");

  return (
    <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-2" data-testid="hh-admin-plan-form">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <FormField label="Slug (unic, lowercase)">
          <input value={form.slug} onChange={(e) => set("slug", e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))} disabled={editing}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm disabled:opacity-50" data-testid="hh-admin-plan-slug" />
        </FormField>
        <FormField label="Nume afișat">
          <input value={form.name} onChange={(e) => set("name", e.target.value)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-name" />
        </FormField>
      </div>
      <FormField label="Descriere">
        <textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={2}
          className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-desc" />
      </FormField>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <FormField label="Preț (€)">
          <input type="number" step="0.01" min="0" value={form.price_eur} onChange={(e) => set("price_eur", parseFloat(e.target.value) || 0)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-price" />
        </FormField>
        <FormField label="Frecvență">
          <select value={form.billing_period} onChange={(e) => set("billing_period", e.target.value)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-period">
            <option value="monthly">Lunar</option>
            <option value="yearly">Anual</option>
            <option value="one_time">O singură dată</option>
          </select>
        </FormField>
        <FormField label="Trial (zile)">
          <input type="number" min="0" value={form.trial_days} onChange={(e) => set("trial_days", parseInt(e.target.value) || 0)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-trial" />
        </FormField>
        <FormField label="Ordine">
          <input type="number" value={form.sort_order} onChange={(e) => set("sort_order", parseInt(e.target.value) || 0)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-sort" />
        </FormField>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <FormField label="Lead commission (%)">
          <input type="number" min="0" max="100" step="0.5" value={form.lead_commission_pct} onChange={(e) => set("lead_commission_pct", parseFloat(e.target.value) || 0)}
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-commission" />
        </FormField>
        <FormField label="Stripe Price ID (optional)">
          <input value={form.stripe_price_id || ""} onChange={(e) => set("stripe_price_id", e.target.value)} placeholder="price_..."
            className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-admin-plan-stripe" />
        </FormField>
      </div>
      <FormField label="Features (câte una pe rând)">
        <textarea value={featuresText} onChange={(e) => set("features", e.target.value.split("\n"))} rows={4}
          placeholder="1 evaluare/an&#10;Storage 1GB&#10;Suport email"
          className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm font-mono" data-testid="hh-admin-plan-features" />
      </FormField>
      <label className="flex items-center gap-2 text-xs text-stone-300">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} data-testid="hh-admin-plan-active" />
        Activ (clienții îl pot vedea)
      </label>
      {error && <div className="text-xs text-rose-400 flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5" /> {error}</div>}
      <div className="flex gap-2 pt-1">
        <button onClick={onSave} data-testid="hh-admin-plan-save"
          className="px-3 py-1.5 rounded-lg bg-emerald-500 text-stone-950 text-xs font-bold inline-flex items-center gap-1.5">
          <Save className="w-3.5 h-3.5" /> Salvează
        </button>
        <button onClick={onCancel} data-testid="hh-admin-plan-cancel"
          className="px-3 py-1.5 rounded-lg bg-stone-800 text-stone-300 text-xs font-semibold inline-flex items-center gap-1.5">
          <X className="w-3.5 h-3.5" /> Anulează
        </button>
      </div>
    </div>
  );
};

const FormField = ({ label, children }) => (
  <div>
    <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-0.5">{label}</div>
    {children}
  </div>
);

// ============================== SCORING TAB ==============================
const WEIGHT_KEYS = [
  { key: "air", label: "Aer", color: "emerald" },
  { key: "thermal", label: "Termic", color: "orange" },
  { key: "humidity", label: "Umiditate", color: "cyan" },
  { key: "electric", label: "Electric", color: "yellow" },
  { key: "docs", label: "Documentație", color: "violet" },
  { key: "maintenance", label: "Mentenanță", color: "rose" },
  { key: "radon", label: "Radon", color: "fuchsia" },
];

const ScoringTab = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/house-health/scoring-config`);
      setConfig(r.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading || !config) return <div className="text-xs text-stone-500">Se încarcă...</div>;

  const total = WEIGHT_KEYS.reduce((s, k) => s + (parseFloat(config.weights[k.key]) || 0), 0);
  const isValid = Math.abs(total - 100) < 0.01;

  const setWeight = (key, v) => setConfig({ ...config, weights: { ...config.weights, [key]: parseFloat(v) || 0 } });
  const setThreshold = (k, v) => setConfig({ ...config, thresholds: { ...config.thresholds, [k]: parseFloat(v) || 0 } });

  const save = async () => {
    setError(""); setSuccess(""); setSaving(true);
    try {
      await axios.put(`${API}/admin/house-health/scoring-config`, {
        weights: config.weights,
        thresholds: config.thresholds,
      });
      setSuccess("Salvat cu succes!");
      setTimeout(() => setSuccess(""), 3000);
      await load();
    } catch (e) {
      const msg = e?.response?.data?.detail;
      setError(Array.isArray(msg) ? msg[0]?.msg : (typeof msg === "string" ? msg : "Eroare salvare"));
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-scoring-weights">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold">Ponderi formulă scor</h2>
          <div className={`text-sm font-bold tabular-nums ${isValid ? "text-emerald-400" : "text-rose-400"}`} data-testid="hh-scoring-total">
            Total: {total.toFixed(1)} / 100 {isValid && <Check className="inline w-4 h-4" />}
          </div>
        </div>
        <p className="text-xs text-stone-400 mb-4">
          Ponderile contribuie la scorul final 0-100. Suma trebuie să fie exact 100. Modificările intră în vigoare imediat la calculul următoarei evaluări.
        </p>
        <div className="space-y-3">
          {WEIGHT_KEYS.map((k) => (
            <div key={k.key} className="flex items-center gap-3" data-testid={`hh-scoring-weight-${k.key}`}>
              <div className="w-28 text-sm font-semibold">{k.label}</div>
              <input
                type="range" min="0" max="50" step="1"
                value={config.weights[k.key]}
                onChange={(e) => setWeight(k.key, e.target.value)}
                className="flex-1 accent-emerald-500"
              />
              <input
                type="number" min="0" max="100" step="0.5"
                value={config.weights[k.key]}
                onChange={(e) => setWeight(k.key, e.target.value)}
                className="w-20 bg-stone-800 border border-stone-700 rounded px-2 py-1 text-sm tabular-nums"
                data-testid={`hh-scoring-input-${k.key}`}
              />
              <div className="w-8 text-xs text-stone-500">%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-scoring-thresholds">
        <h2 className="text-lg font-bold mb-3">Praguri clasificare</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <ThresholdInput label="Excellent (≥)" value={config.thresholds.excellent} onChange={(v) => setThreshold("excellent", v)} color="emerald" testid="hh-scoring-threshold-excellent" />
          <ThresholdInput label="Good (≥)" value={config.thresholds.good} onChange={(v) => setThreshold("good", v)} color="sky" testid="hh-scoring-threshold-good" />
          <ThresholdInput label="Fair (≥)" value={config.thresholds.fair} onChange={(v) => setThreshold("fair", v)} color="amber" testid="hh-scoring-threshold-fair" />
        </div>
        <p className="text-[11px] text-stone-500 mt-2 italic">Constraint: 0 &lt; Fair &lt; Good &lt; Excellent ≤ 100</p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={!isValid || saving}
          data-testid="hh-scoring-save"
          className="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-white text-sm font-bold inline-flex items-center gap-2 disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? "Se salvează..." : "Salvează configurarea"}
        </button>
        {error && <div className="text-xs text-rose-400 flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5" /> {error}</div>}
        {success && <div className="text-xs text-emerald-400 flex items-center gap-1.5"><Check className="w-3.5 h-3.5" /> {success}</div>}
      </div>

      {config.updated_at && (
        <div className="text-[11px] text-stone-500">
          Ultima modificare: {new Date(config.updated_at).toLocaleString("ro-RO")} de {config.updated_by || "—"}
        </div>
      )}
    </div>
  );
};

const ThresholdInput = ({ label, value, onChange, color, testid }) => (
  <div>
    <div className={`text-[10px] uppercase tracking-wider text-${color}-400 font-bold mb-1`}>{label}</div>
    <input
      type="number" min="0" max="100" step="1" value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid={testid}
      className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm tabular-nums"
    />
  </div>
);

export default AdminHouseHealthPage;
