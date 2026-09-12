// ConstructionIntelligencePage — CIP-A: Nomenclator ierarhic + Visibility Gate + Project Central.
// Route: /admin/construction
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Hammer, ChevronLeft, ChevronRight, ChevronDown, Loader2, RefreshCcw, Plus,
  Pencil, Trash2, Eye, EyeOff, Users, AlertTriangle, Download, Search,
  FolderTree, FolderKanban, Sparkles, CheckCircle2, Coins,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_LABEL = {
  open: "Deschisă", assigned: "Alocată", in_progress: "În lucru",
  completed: "Finalizată", confirmed: "Confirmată", disputed: "În dispută",
};

const KPI = ({ label, value, accent }) => (
  <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4" data-testid={`cip-kpi-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
    <div className="text-xs text-stone-400 uppercase tracking-wider">{label}</div>
    <div className={`text-2xl font-bold mt-1.5 ${accent || "text-white"}`}>{value}</div>
  </div>
);

// ============================ TAXONOMY NODE ============================
const TaxNode = ({ node, depth, expanded, onToggleExpand, onAction }) => {
  const hasChildren = (node.children || []).length > 0;
  const isOpen = expanded.has(node.id);
  return (
    <>
      <div
        className={`flex items-center gap-2 py-2 px-3 rounded-xl hover:bg-stone-800/50 ${!node.is_active ? "opacity-45" : ""}`}
        style={{ marginLeft: depth * 22 }}
        data-testid={`tax-node-${node.id}`}
      >
        <button onClick={() => hasChildren && onToggleExpand(node.id)} className={`w-5 shrink-0 text-stone-500 ${hasChildren ? "" : "invisible"}`} data-testid={`tax-expand-${node.id}`}>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <span className={`text-sm ${depth === 0 ? "font-bold text-white" : depth === 1 ? "font-semibold text-stone-200" : "text-stone-300"}`}>{node.name}</span>
        {node.is_publicly_visible
          ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1"><Eye className="w-3 h-3" /> vizibil</span>
          : <span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-500/15 text-stone-400 border border-stone-600/40 flex items-center gap-1"><EyeOff className="w-3 h-3" /> ascuns</span>}
        {depth === 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 flex items-center gap-1" title="Specialiști verificați în categorie">
            <Users className="w-3 h-3" /> {node.specialist_count}
          </span>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-0.5">
          {depth < 2 && (
            <button onClick={() => onAction("add", node)} className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10" title="Adaugă sub-nod" data-testid={`tax-add-${node.id}`}><Plus className="w-3.5 h-3.5" /></button>
          )}
          <button onClick={() => onAction("rename", node)} className="p-1.5 rounded-lg text-stone-400 hover:bg-stone-700/50" title="Redenumește" data-testid={`tax-rename-${node.id}`}><Pencil className="w-3.5 h-3.5" /></button>
          <button onClick={() => onAction("toggle", node)} className={`p-1.5 rounded-lg hover:bg-amber-500/10 ${node.is_active ? "text-amber-400" : "text-emerald-400"}`} title={node.is_active ? "Dezactivează" : "Activează"} data-testid={`tax-toggle-${node.id}`}>
            {node.is_active ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
          {!hasChildren && (
            <button onClick={() => onAction("delete", node)} className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10" title="Șterge" data-testid={`tax-delete-${node.id}`}><Trash2 className="w-3.5 h-3.5" /></button>
          )}
        </div>
      </div>
      {isOpen && (node.children || []).map(c => (
        <TaxNode key={c.id} node={c} depth={depth + 1} expanded={expanded} onToggleExpand={onToggleExpand} onAction={onAction} />
      ))}
    </>
  );
};

// ============================ TAXONOMY TAB ============================
const TaxonomyTab = ({ onChanged }) => {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(new Set());
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await ax.get("/api/construction/taxonomy");
      setTree(r.data?.tree || []);
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleExpand = (id) => setExpanded(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const action = async (kind, node) => {
    try {
      if (kind === "add") {
        const name = window.prompt(`Nume sub-nod nou în „${node.name}":`);
        if (!name || name.trim().length < 2) return;
        await ax.post("/api/construction/taxonomy", { name: name.trim(), parent_id: node.id });
        setExpanded(prev => new Set(prev).add(node.id));
        setMsg(`✅ „${name.trim()}" adăugat.`);
      } else if (kind === "rename") {
        const name = window.prompt("Nume nou:", node.name);
        if (!name || name.trim().length < 2 || name.trim() === node.name) return;
        await ax.patch(`/api/construction/taxonomy/${node.id}`, { name: name.trim() });
        setMsg("✅ Redenumit.");
      } else if (kind === "toggle") {
        await ax.patch(`/api/construction/taxonomy/${node.id}`, { is_active: !node.is_active });
        setMsg(node.is_active ? `⏸ „${node.name}" dezactivat (+ descendenții ascunși din public).` : `✅ „${node.name}" reactivat.`);
      } else if (kind === "delete") {
        if (!window.confirm(`Ștergi definitiv „${node.name}"?`)) return;
        await ax.delete(`/api/construction/taxonomy/${node.id}`);
        setMsg("🗑 Șters.");
      }
      await load();
      onChanged?.();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const addRoot = async () => {
    const name = window.prompt("Nume categorie rădăcină nouă:");
    if (!name || name.trim().length < 2) return;
    try {
      await ax.post("/api/construction/taxonomy", { name: name.trim() });
      setMsg(`✅ Categoria „${name.trim()}" creată (ascunsă până apare primul specialist verificat).`);
      await load();
      onChanged?.();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
  };

  const refreshVisibility = async () => {
    setRefreshing(true);
    try {
      await ax.post("/api/construction/refresh-visibility");
      setMsg("✅ Visibility gate rulat prin Orchestrator — vezi ledger-ul în /admin/orchestrator.");
      await load();
      onChanged?.();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
    finally { setRefreshing(false); }
  };

  return (
    <div data-testid="cip-taxonomy-tab">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <button onClick={addRoot} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5" data-testid="tax-add-root">
          <Plus className="w-3.5 h-3.5" /> Categorie rădăcină
        </button>
        <button onClick={refreshVisibility} disabled={refreshing} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white flex items-center gap-1.5" data-testid="tax-refresh-visibility">
          {refreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} Rulează Visibility Gate
        </button>
        <div className="flex-1" />
        <span className="text-[11px] text-stone-500">Vizibil public = nod activ + ≥1 specialist verificat în categorie</span>
      </div>
      {msg && <div className="mb-3 px-4 py-2 rounded-xl bg-stone-900/60 border border-stone-700 text-sm text-stone-200" data-testid="tax-message">{msg}</div>}
      <div className="bg-stone-900/30 border border-stone-800 rounded-2xl p-2" data-testid="tax-tree">
        {loading
          ? <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-stone-500" /></div>
          : tree.map(n => <TaxNode key={n.id} node={n} depth={0} expanded={expanded} onToggleExpand={toggleExpand} onAction={action} />)}
      </div>
    </div>
  );
};

// ============================ PROJECTS TAB ============================
const ProjectsTab = ({ categories }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ category: "all", status: "all", city: "", q: "", min_value: "", max_value: "" });

  const params = () => {
    const p = { limit: 100 };
    if (f.category !== "all") p.category = f.category;
    if (f.status !== "all") p.status = f.status;
    if (f.city.trim()) p.city = f.city.trim();
    if (f.q.trim()) p.q = f.q.trim();
    if (f.min_value) p.min_value = f.min_value;
    if (f.max_value) p.max_value = f.max_value;
    return p;
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await ax.get("/api/construction/projects", { params: params() });
      setItems(r.data?.items || []);
    } catch { setItems([]); }
    finally { setLoading(false); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [f]);
  useEffect(() => { const t = setTimeout(load, 350); return () => clearTimeout(t); }, [load]);

  const exportCsv = () => {
    const qs = new URLSearchParams(params()).toString();
    window.open(`${API}/api/construction/projects/export?${qs}`, "_blank");
  };

  const inputCls = "px-3 py-1.5 text-xs rounded-lg border border-stone-700 bg-stone-900 text-stone-200 outline-none focus:border-violet-500";
  return (
    <div data-testid="cip-projects-tab">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <select value={f.category} onChange={e => setF(x => ({ ...x, category: e.target.value }))} className={inputCls} data-testid="proj-filter-category">
          <option value="all">Toate categoriile</option>
          {categories.map(c => <option key={c.legacy_category} value={c.legacy_category}>{c.name}</option>)}
        </select>
        <select value={f.status} onChange={e => setF(x => ({ ...x, status: e.target.value }))} className={inputCls} data-testid="proj-filter-status">
          <option value="all">Toate statusurile</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input value={f.city} onChange={e => setF(x => ({ ...x, city: e.target.value }))} placeholder="Oraș" className={`${inputCls} w-28`} data-testid="proj-filter-city" />
        <input value={f.min_value} onChange={e => setF(x => ({ ...x, min_value: e.target.value }))} placeholder="Buget min" type="number" className={`${inputCls} w-24`} data-testid="proj-filter-min" />
        <input value={f.max_value} onChange={e => setF(x => ({ ...x, max_value: e.target.value }))} placeholder="Buget max" type="number" className={`${inputCls} w-24`} data-testid="proj-filter-max" />
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-stone-500" />
          <input value={f.q} onChange={e => setF(x => ({ ...x, q: e.target.value }))} placeholder="Caută titlu / client / specialist" className={`${inputCls} pl-8 w-56`} data-testid="proj-filter-q" />
        </div>
        <div className="flex-1" />
        <button onClick={exportCsv} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1.5" data-testid="proj-export-csv">
          <Download className="w-3.5 h-3.5" /> Export CSV
        </button>
      </div>
      <div className="bg-stone-900/30 border border-stone-800 rounded-2xl overflow-x-auto" data-testid="proj-table">
        {loading ? <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-stone-500" /></div> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-stone-500 border-b border-stone-800">
                <th className="px-4 py-2.5">Titlu</th><th className="px-3 py-2.5">Categorie</th><th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5 text-right">Buget</th><th className="px-3 py-2.5">Client</th><th className="px-3 py-2.5">Specialist</th>
                <th className="px-3 py-2.5">Oraș</th><th className="px-3 py-2.5">Creat</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-stone-500">Nicio cerere pentru filtrele curente.</td></tr>}
              {items.map(r => (
                <tr key={r.id} className="border-b border-stone-800/60 hover:bg-stone-800/30" data-testid={`proj-row-${r.id}`}>
                  <td className="px-4 py-2.5 text-white font-medium max-w-[220px] truncate">{r.title}{r.subcategory && <div className="text-[10px] text-violet-300 font-normal">{r.subcategory}</div>}</td>
                  <td className="px-3 py-2.5 text-stone-300">{r.category}</td>
                  <td className="px-3 py-2.5"><span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-700/50 text-stone-300">{STATUS_LABEL[r.status] || r.status}</span></td>
                  <td className="px-3 py-2.5 text-right text-stone-200">{r.budget_estimate ? `${Number(r.budget_estimate).toLocaleString("ro-RO")} RON` : "—"}</td>
                  <td className="px-3 py-2.5 text-stone-300">{r.client_name || "—"}</td>
                  <td className="px-3 py-2.5 text-stone-300">{r.specialist_name || "—"}</td>
                  <td className="px-3 py-2.5 text-stone-400">{r.city || "—"}</td>
                  <td className="px-3 py-2.5 text-stone-500 text-xs">{(r.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// ============================ PRICES TAB (CIP-B) ============================
const UNIT_OPTIONS = ["mp", "ml", "buc", "ora", "proiect", "zi"];
const LEVEL_LABEL = { beginner: "Începător", mid: "Intermediar", expert: "Expert" };

const PricesTab = ({ categories }) => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ category: "all", city: "all" });
  const [form, setForm] = useState({ category: "", service: "", city: "", unit: "mp", price_min: "", price_med: "", price_max: "", experience_level: "mid" });
  const [showImport, setShowImport] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [msg, setMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await ax.get("/api/construction/prices/public", { params: { category: f.category, city: f.city } });
      setRows(r.data?.items || []);
    } catch { setRows([]); }
    finally { setLoading(false); }
  }, [f]);
  useEffect(() => { load(); }, [load]);

  const addObservation = async () => {
    setSaving(true);
    try {
      await ax.post("/api/construction/prices", form);
      setMsg(`✅ Observație adăugată: ${form.service} · ${form.city}.`);
      setForm(x => ({ ...x, service: "", price_min: "", price_med: "", price_max: "" }));
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
    finally { setSaving(false); }
  };

  const importCsv = async () => {
    setSaving(true);
    try {
      const r = await ax.post("/api/construction/prices/import-csv", { csv: csvText });
      setMsg(`✅ Import: ${r.data.imported} rânduri · ${r.data.error_count} erori${r.data.errors?.length ? ` (${r.data.errors[0]}…)` : ""}`);
      setCsvText("");
      setShowImport(false);
      await load();
    } catch (e) { setMsg(`❌ ${e?.response?.data?.detail || e.message}`); }
    finally { setSaving(false); }
  };

  const inputCls = "px-3 py-1.5 text-xs rounded-lg border border-stone-700 bg-stone-900 text-stone-200 outline-none focus:border-violet-500";
  return (
    <div data-testid="cip-prices-tab">
      <div className="bg-stone-900/30 border border-stone-800 rounded-2xl p-4 mb-4" data-testid="price-add-form">
        <div className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-2.5">Adaugă observație de preț</div>
        <div className="flex flex-wrap gap-2 items-center">
          <select value={form.category} onChange={e => setForm(x => ({ ...x, category: e.target.value }))} className={inputCls} data-testid="price-form-category">
            <option value="">Categorie…</option>
            {categories.map(c => <option key={c.legacy_category} value={c.legacy_category}>{c.name}</option>)}
          </select>
          <input value={form.service} onChange={e => setForm(x => ({ ...x, service: e.target.value }))} placeholder="Serviciu (ex: Montaj gresie)" className={`${inputCls} w-52`} data-testid="price-form-service" />
          <input value={form.city} onChange={e => setForm(x => ({ ...x, city: e.target.value }))} placeholder="Oraș" className={`${inputCls} w-28`} data-testid="price-form-city" />
          <select value={form.unit} onChange={e => setForm(x => ({ ...x, unit: e.target.value }))} className={inputCls} data-testid="price-form-unit">
            {UNIT_OPTIONS.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
          <select value={form.experience_level} onChange={e => setForm(x => ({ ...x, experience_level: e.target.value }))} className={inputCls} data-testid="price-form-level">
            {Object.entries(LEVEL_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input value={form.price_min} onChange={e => setForm(x => ({ ...x, price_min: e.target.value }))} placeholder="Min" type="number" className={`${inputCls} w-20`} data-testid="price-form-min" />
          <input value={form.price_med} onChange={e => setForm(x => ({ ...x, price_med: e.target.value }))} placeholder="Med" type="number" className={`${inputCls} w-20`} data-testid="price-form-med" />
          <input value={form.price_max} onChange={e => setForm(x => ({ ...x, price_max: e.target.value }))} placeholder="Max" type="number" className={`${inputCls} w-20`} data-testid="price-form-max" />
          <button onClick={addObservation} disabled={saving || !form.category || !form.service || !form.city} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white flex items-center gap-1.5" data-testid="price-form-submit">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Adaugă
          </button>
          <button onClick={() => setShowImport(v => !v)} className="px-3 py-1.5 text-xs font-medium rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="price-import-toggle">
            <Download className="w-3.5 h-3.5 rotate-180" /> Import CSV
          </button>
          <button onClick={() => window.open(`${API}/api/construction/prices/export`, "_blank")} className="px-3 py-1.5 text-xs font-medium rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="price-export">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
        {showImport && (
          <div className="mt-3" data-testid="price-import-panel">
            <textarea value={csvText} onChange={e => setCsvText(e.target.value)} rows={5}
              placeholder={"category,service,city,unit,price_min,price_med,price_max,experience_level\nzugravit,Vopsea lavabilă,București,mp,12,18,28,mid"}
              className="w-full text-xs font-mono rounded-xl border border-stone-700 bg-stone-950 text-stone-200 p-3 outline-none focus:border-violet-500" data-testid="price-import-textarea" />
            <button onClick={importCsv} disabled={saving || !csvText.trim()} className="mt-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white" data-testid="price-import-submit">
              Importă rândurile
            </button>
          </div>
        )}
      </div>

      {msg && <div className="mb-3 px-4 py-2 rounded-xl bg-stone-900/60 border border-stone-700 text-sm text-stone-200" data-testid="price-message">{msg}</div>}

      <div className="flex items-center gap-2 mb-3">
        <select value={f.category} onChange={e => setF(x => ({ ...x, category: e.target.value }))} className={inputCls} data-testid="price-filter-category">
          <option value="all">Toate categoriile</option>
          {categories.map(c => <option key={c.legacy_category} value={c.legacy_category}>{c.name}</option>)}
        </select>
        <input value={f.city === "all" ? "" : f.city} onChange={e => setF(x => ({ ...x, city: e.target.value || "all" }))} placeholder="Oraș (toate)" className={`${inputCls} w-32`} data-testid="price-filter-city" />
        <span className="text-[11px] text-stone-500">Trust: A = ≥3 observații · B = 2 · C = 1 · „preliminar" = date orientative seed</span>
      </div>

      <div className="bg-stone-900/30 border border-stone-800 rounded-2xl overflow-x-auto" data-testid="price-table">
        {loading ? <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-stone-500" /></div> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-stone-500 border-b border-stone-800">
                <th className="px-4 py-2.5">Serviciu</th><th className="px-3 py-2.5">Categorie</th><th className="px-3 py-2.5">Oraș</th>
                <th className="px-3 py-2.5">Nivel</th><th className="px-3 py-2.5 text-right">Min–Med–Max (RON/{"{UM}"})</th>
                <th className="px-3 py-2.5">Trust</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-stone-500">Nicio observație pentru filtrele curente.</td></tr>}
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-stone-800/60 hover:bg-stone-800/30">
                  <td className="px-4 py-2.5 text-white font-medium">{r.service}</td>
                  <td className="px-3 py-2.5 text-stone-400">{r.category}</td>
                  <td className="px-3 py-2.5 text-stone-300">{r.city}</td>
                  <td className="px-3 py-2.5"><span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-700/50 text-stone-300">{LEVEL_LABEL[r.experience_level] || r.experience_level}</span></td>
                  <td className="px-3 py-2.5 text-right text-stone-200 whitespace-nowrap">{r.price_min} – <span className="font-bold text-white">{r.price_med}</span> – {r.price_max} <span className="text-stone-500 text-xs">/{r.unit}</span></td>
                  <td className="px-3 py-2.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.trust_grade === "A" ? "bg-emerald-500/15 text-emerald-300" : r.trust_grade === "B" ? "bg-cyan-500/15 text-cyan-300" : "bg-stone-600/30 text-stone-300"}`}>{r.trust_grade}</span>
                    {r.preliminary && <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300">preliminar</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// ============================ PAGE ============================
export default function ConstructionIntelligencePage() {
  const [tab, setTab] = useState("taxonomy");
  const [ov, setOv] = useState(null);
  const [inviteMsg, setInviteMsg] = useState(null);

  const loadOverview = useCallback(async () => {
    try {
      const r = await ax.get("/api/construction/overview");
      setOv(r.data);
    } catch { setOv(null); }
  }, []);
  useEffect(() => { loadOverview(); }, [loadOverview]);

  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8" data-testid="construction-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-6">
          <Link to="/admin" className="text-stone-500 hover:text-white flex items-center gap-1 text-sm" data-testid="cip-back-link"><ChevronLeft className="w-4 h-4" /> Admin</Link>
          <span className="text-stone-700">·</span>
          <Hammer className="w-5 h-5 text-amber-400" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">Construction Intelligence</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">CIP-A · Fundație</span>
          <div className="flex-1" />
          <Link to="/admin/orchestrator" className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="cip-to-orchestrator">
            <Sparkles className="w-3.5 h-3.5" /> Orchestrator
          </Link>
        </div>

        {ov && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <KPI label="Noduri nomenclator" value={ov.total_nodes} />
              <KPI label="Vizibile public" value={ov.visible_nodes} accent="text-emerald-400" />
              <KPI label="Categorii rădăcină" value={`${ov.roots_visible}/${ov.root_categories}`} accent="text-cyan-400" />
              <KPI label="Ascunse cu potențial" value={ov.hidden_with_potential.length} accent={ov.hidden_with_potential.length ? "text-amber-400" : "text-stone-400"} />
            </div>
            {ov.hidden_with_potential.length > 0 && (
              <div className="mb-4 px-4 py-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-sm text-amber-200" data-testid="cip-hidden-potential">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span className="font-semibold">Oportunitate recrutare — categorii cu cerere de la clienți dar fără specialiști verificați:</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {ov.hidden_with_potential.map(h => (
                    <div key={h.legacy_category} className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-stone-900/50 border border-amber-500/20" data-testid={`hp-item-${h.legacy_category}`}>
                      <span>{h.name} <span className="text-amber-400/80">({h.requests_90d} cereri/90d)</span></span>
                      <button
                        onClick={() => {
                          const link = `${window.location.origin}/register?role=specialist&category=${h.legacy_category}&utm_source=recruitment&utm_campaign=hidden_potential`;
                          navigator.clipboard?.writeText(link);
                          setInviteMsg(`🔗 Link de recrutare copiat pentru „${h.name}": ${link}`);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/90 hover:bg-amber-400 text-stone-950 text-[11px] font-bold flex items-center gap-1"
                        data-testid={`invite-specialists-${h.legacy_category}`}
                      >
                        <Users className="w-3 h-3" /> Invită specialiști
                      </button>
                    </div>
                  ))}
                </div>
                {inviteMsg && <div className="mt-2 text-xs text-emerald-300 break-all" data-testid="invite-copied-msg">{inviteMsg}</div>}
              </div>
            )}
          </>
        )}

        <div className="flex items-center gap-1 mb-4 border-b border-stone-800">
          {[["taxonomy", "Nomenclator", FolderTree], ["projects", "Proiecte (vedere centrală)", FolderKanban], ["prices", "Prețuri (Observatory)", Coins]].map(([id, label, Icon]) => (
            <button key={id} onClick={() => setTab(id)} data-testid={`cip-tab-${id}`}
              className={`px-4 py-2.5 text-sm font-medium flex items-center gap-1.5 border-b-2 -mb-px transition-colors ${tab === id ? "border-amber-400 text-white" : "border-transparent text-stone-500 hover:text-stone-300"}`}>
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </div>

        {tab === "taxonomy" && <TaxonomyTab onChanged={loadOverview} />}
        {tab === "projects" && <ProjectsTab categories={ov?.coverage || []} />}
        {tab === "prices" && <PricesTab categories={ov?.coverage || []} />}
      </div>
    </div>
  );
}
