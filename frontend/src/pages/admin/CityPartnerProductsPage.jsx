// City Partner Products — Admin CRUD catalog of REAL materials (super-admin).
// Route: /admin/city-partner-products
// Powers Digital Twin design-concept materials pricing (partner product > market fallback).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ShoppingBag, Plus, Loader2, X, Save, Edit3, Trash2, ExternalLink, Search } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const UNITS = ["buc", "mp", "ml", "set", "m", "kg", "litru", "pachet"];

const ProductForm = ({ initial, partners, onSave, onClose, saving }) => {
  const [f, setF] = useState(() => ({
    name: initial?.name || "",
    brand: initial?.brand || "",
    category: initial?.category || "",
    unit: initial?.unit || "buc",
    price_min: initial?.price_min ?? "",
    price_max: initial?.price_max ?? "",
    currency: initial?.currency || "RON",
    partner_id: initial?.partner_id || "",
    url: initial?.url || "",
    tags: (initial?.tags || []).join(", "),
    active: initial?.active ?? true,
  }));
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const submit = (e) => {
    e.preventDefault();
    onSave({
      name: f.name.trim(),
      brand: f.brand.trim() || null,
      category: f.category.trim() || null,
      unit: f.unit,
      price_min: Number(f.price_min) || 0,
      price_max: f.price_max === "" ? null : Number(f.price_max),
      currency: f.currency || "RON",
      partner_id: f.partner_id || null,
      url: f.url.trim() || null,
      tags: f.tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean),
      active: !!f.active,
    });
  };
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="product-form-modal">
      <form onSubmit={submit} className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">{initial ? "Editează produs" : "Adaugă produs / material"}</h2>
          <button type="button" onClick={onClose} className="text-slate-400" data-testid="product-form-close"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Denumire produs *</label>
            <input required value={f.name} onChange={(e) => set("name", e.target.value)} data-testid="product-name"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" placeholder="ex: Parchet stratificat stejar natural" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Brand</label>
            <input value={f.brand} onChange={(e) => set("brand", e.target.value)} data-testid="product-brand"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Categorie</label>
            <input value={f.category} onChange={(e) => set("category", e.target.value)} data-testid="product-category"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" placeholder="ex: pardoseli" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Unitate</label>
            <select value={f.unit} onChange={(e) => set("unit", e.target.value)} data-testid="product-unit"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white">
              {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Monedă</label>
            <input value={f.currency} onChange={(e) => set("currency", e.target.value)} data-testid="product-currency"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Preț minim *</label>
            <input required type="number" step="0.01" value={f.price_min} onChange={(e) => set("price_min", e.target.value)} data-testid="product-price-min"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Preț maxim</label>
            <input type="number" step="0.01" value={f.price_max} onChange={(e) => set("price_max", e.target.value)} data-testid="product-price-max"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Partener (City Partner)</label>
            <select value={f.partner_id} onChange={(e) => set("partner_id", e.target.value)} data-testid="product-partner"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white">
              <option value="">— fără partener —</option>
              {partners.map((p) => <option key={p.id} value={p.id}>{p.company} · {p.city}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Link produs</label>
            <input value={f.url} onChange={(e) => set("url", e.target.value)} data-testid="product-url"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" placeholder="https://…" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tag-uri (separate prin virgulă) — folosite pentru potrivirea cu materialele conceptului</label>
            <input value={f.tags} onChange={(e) => set("tags", e.target.value)} data-testid="product-tags"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" placeholder="parchet, stejar, lemn" />
          </div>
          <label className="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
            <input type="checkbox" checked={f.active} onChange={(e) => set("active", e.target.checked)} data-testid="product-active" />
            Activ (vizibil pentru potrivire în concepte)
          </label>
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-medium inline-flex items-center gap-2 disabled:opacity-50" data-testid="product-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează
          </button>
        </div>
      </form>
    </div>
  );
};

export default function CityPartnerProductsPage() {
  const [items, setItems] = useState(null);
  const [partners, setPartners] = useState([]);
  const [q, setQ] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const { data } = await ax.get("/api/admin/city-partner-products", { params: q ? { q } : {} });
      setItems(data.items || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
      setItems([]);
    }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line
  useEffect(() => {
    ax.get("/api/admin/city-partners").then((r) => setPartners(r.data.items || [])).catch(() => {});
  }, []);

  const save = async (payload) => {
    setSaving(true); setErr(null);
    try {
      if (editing) await ax.patch(`/api/admin/city-partner-products/${editing.id}`, payload);
      else await ax.post("/api/admin/city-partner-products", payload);
      setShowForm(false); setEditing(null);
      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la salvare.");
    } finally {
      setSaving(false);
    }
  };

  const del = async (id) => {
    if (!window.confirm("Ștergi acest produs din catalog?")) return;
    try { await ax.delete(`/api/admin/city-partner-products/${id}`); await load(); }
    catch (e) { setErr(e?.response?.data?.detail || "Eroare la ștergere."); }
  };

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto" data-testid="city-partner-products-page">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <ShoppingBag className="w-5 h-5 text-emerald-500" /> Catalog Materiale — City Partners
        </h1>
        <button onClick={() => { setEditing(null); setShowForm(true); }} data-testid="add-product-btn"
          className="px-4 py-2 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-medium inline-flex items-center gap-2">
          <Plus className="w-4 h-4" /> Adaugă produs
        </button>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
        Produsele reale de la parteneri au prioritate în prețurile orientative din conceptele Digital Twin. Când nu există potrivire, sistemul revine pe prețurile de piață.
      </p>

      <div className="flex items-center gap-2 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} data-testid="product-search"
            placeholder="Caută după nume, brand, tag…" className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white" />
        </div>
        <button onClick={load} className="px-3 py-2 rounded-lg text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">Caută</button>
      </div>

      {err && <div className="mb-3 text-sm text-rose-600 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-lg p-2" data-testid="products-error">{err}</div>}

      {items === null ? (
        <div className="py-16 text-center text-slate-500"><Loader2 className="w-5 h-5 animate-spin inline mr-2" />Se încarcă…</div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center text-slate-500 border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl" data-testid="products-empty">
          <ShoppingBag className="w-10 h-10 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Catalog gol. Adaugă produse reale de la parteneri pentru prețuri orientative în concepte.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800" data-testid="products-table">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Produs</th>
                <th className="text-left px-4 py-2">Partener</th>
                <th className="text-right px-4 py-2">Preț</th>
                <th className="text-left px-4 py-2">Tag-uri</th>
                <th className="text-center px-4 py-2">Activ</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((p) => (
                <tr key={p.id} className="text-slate-800 dark:text-slate-200" data-testid={`product-row-${p.id}`}>
                  <td className="px-4 py-2.5">
                    <div className="font-medium flex items-center gap-1.5">
                      {p.name}
                      {p.url && <a href={p.url} target="_blank" rel="noreferrer" className="text-emerald-500"><ExternalLink className="w-3.5 h-3.5" /></a>}
                    </div>
                    <div className="text-[11px] text-slate-500">{[p.brand, p.category].filter(Boolean).join(" · ")}</div>
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">{p.partner_name || "—"}</td>
                  <td className="px-4 py-2.5 text-right font-mono whitespace-nowrap">
                    {(p.price_min ?? 0).toLocaleString()}{p.price_max && p.price_max !== p.price_min ? `–${p.price_max.toLocaleString()}` : ""} <span className="text-slate-400">{p.currency}/{p.unit}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {(p.tags || []).slice(0, 4).map((t) => <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">{t}</span>)}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={`inline-block w-2 h-2 rounded-full ${p.active ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-600"}`} />
                  </td>
                  <td className="px-4 py-2.5 text-right whitespace-nowrap">
                    <button onClick={() => { setEditing(p); setShowForm(true); }} className="text-slate-400 hover:text-emerald-500 mr-2" data-testid={`product-edit-${p.id}`}><Edit3 className="w-4 h-4" /></button>
                    <button onClick={() => del(p.id)} className="text-slate-400 hover:text-rose-500" data-testid={`product-delete-${p.id}`}><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <ProductForm
          initial={editing}
          partners={partners}
          saving={saving}
          onSave={save}
          onClose={() => { setShowForm(false); setEditing(null); }}
        />
      )}
    </div>
  );
}
