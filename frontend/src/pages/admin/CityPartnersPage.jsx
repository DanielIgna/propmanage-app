// City Partners — Admin list + detail + create modal.
// Route: /admin/city-partners
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2, Plus, Users, MapPin, TrendingUp, Loader2, ChevronLeft, X,
  Save, Edit3, Eye, KeyRound, Mail, Phone, AlertTriangle, Trash2,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_META = {
  lead: { label: "Lead", color: "bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300" },
  onboarding: { label: "Onboarding", color: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  active: { label: "Activ", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  paused: { label: "Pauzat", color: "bg-slate-200 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300" },
  terminated: { label: "Încetat", color: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};

const PartnerForm = ({ initial, onSave, onClose, saving }) => {
  const [f, setF] = useState(() => ({
    company: initial?.company || "",
    contact_name: initial?.contact_name || "",
    contact_email: initial?.contact_email || "",
    contact_phone: initial?.contact_phone || "",
    city: initial?.city || "",
    county: initial?.county || "",
    units_managed: initial?.units_managed || 0,
    growth_rate: initial?.growth_rate || "",
    portfolio_type: initial?.portfolio_type || "",
    started_at: initial?.started_at?.slice(0, 10) || "",
    status: initial?.status || "lead",
    notes: initial?.notes || "",
  }));
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="partner-form-modal">
      <form onSubmit={e => { e.preventDefault(); onSave({ ...f, units_managed: Number(f.units_managed) || 0 }); }}
        className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">{initial ? "Editează partener" : "Adaugă partener strategic"}</h2>
          <button type="button" onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
          {[
            ["Companie *", "company", "text", true],
            ["Persoană contact *", "contact_name", "text", true],
            ["Email contact *", "contact_email", "email", true],
            ["Telefon", "contact_phone", "tel", false],
            ["Oraș *", "city", "text", true],
            ["Județ / Sector", "county", "text", false],
            ["Apartamente administrate", "units_managed", "number", false],
            ["Ritm creștere", "growth_rate", "text", false, "ex: +8%/lună"],
            ["Tip portofoliu", "portfolio_type", "text", false, "ex: Condominii rezidențiale"],
            ["Început colaborare", "started_at", "date", false],
          ].map(([lbl, key, type, req, ph]) => (
            <div key={key}>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{lbl}</label>
              <input type={type} required={req} placeholder={ph || ""} value={f[key]} onChange={e => set(key, e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                data-testid={`partner-field-${key}`} />
            </div>
          ))}
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Status</label>
            <select value={f.status} onChange={e => set("status", e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="partner-field-status">
              {Object.entries(STATUS_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Note interne</label>
            <textarea value={f.notes} onChange={e => set("notes", e.target.value)} rows={2}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="partner-field-notes" />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="partner-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}{initial ? "Salvează" : "Adaugă"}
          </button>
        </div>
      </form>
    </div>
  );
};

const CityPartnersPage = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([
        ax.get("/api/admin/city-partners", { params: filterStatus !== "all" ? { status: filterStatus } : {} }),
        ax.get("/api/admin/city-partners/stats"),
      ]);
      setItems(a.data?.items || []);
      setStats(b.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [filterStatus]);

  const save = async (payload) => {
    setSaving(true);
    try {
      if (editing) {
        const { data } = await ax.patch(`/api/admin/city-partners/${editing.id}`, payload);
        setItems(arr => arr.map(x => x.id === data.id ? data : x));
      } else {
        const { data } = await ax.post("/api/admin/city-partners", payload);
        setItems(arr => [data, ...arr]);
      }
      setFormOpen(false); setEditing(null);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const archive = async (p) => {
    if (!window.confirm(`Marchează ${p.company} ca încetat?`)) return;
    try {
      await ax.delete(`/api/admin/city-partners/${p.id}`);
      setItems(arr => arr.map(x => x.id === p.id ? { ...x, status: "terminated" } : x));
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="city-partners-page">
      <div className="mb-6 flex items-center gap-3">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-cyan-500" />
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Strategic City Partnership</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-400">V1 · Pilot</span>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <StatCard icon={Users} label="Parteneri total" value={stats.total_partners} color="text-blue-500" />
          <StatCard icon={TrendingUp} label="Activi" value={stats.by_status?.active || 0} color="text-emerald-500" />
          <StatCard icon={MapPin} label="Lead-uri introduse" value={stats.total_leads} color="text-amber-500" />
          <StatCard icon={Building2} label="Conversii" value={stats.leads_by_stage?.converted || 0} color="text-violet-500" />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 p-0.5">
          {[["all", "Toți"], ["lead", "Lead"], ["onboarding", "Onboarding"], ["active", "Activ"], ["paused", "Pauzat"]].map(([k, lbl]) => (
            <button key={k} onClick={() => setFilterStatus(k)} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filterStatus === k ? "bg-blue-600 text-white" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}`} data-testid={`filter-${k}`}>
              {lbl}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <button onClick={() => { setEditing(null); setFormOpen(true); }} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5" data-testid="add-partner">
          <Plus className="w-3.5 h-3.5" /> Adaugă partener
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {loading && <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-slate-400" /></div>}
        {error && <div className="p-6 text-rose-500 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {error}</div>}
        {!loading && items.length === 0 && !error && <div className="p-10 text-center text-sm text-slate-500">Niciun partener. Apasă „Adaugă partener” pentru a începe.</div>}
        {!loading && items.length > 0 && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.map(p => {
              const st = STATUS_META[p.status] || STATUS_META.lead;
              return (
                <div key={p.id} className="p-4 flex flex-wrap items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`partner-row-${p.id}`}>
                  <div className="flex-1 min-w-[220px]">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">{p.company}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${st.color}`}>{st.label}</span>
                      <span className="text-[10px] text-slate-400">{p.city}{p.county ? `, ${p.county}` : ""}</span>
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-3 flex-wrap">
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" />{p.contact_name}</span>
                      <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{p.contact_email}</span>
                      {p.contact_phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{p.contact_phone}</span>}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      {p.units_managed} apart. · {p.growth_rate || "—"} · {p.portfolio_type || "—"}
                    </div>
                  </div>
                  <div className="text-center text-xs">
                    <div className="text-slate-900 dark:text-white font-bold">{p.onboarding_step}/7</div>
                    <div className="text-[10px] text-slate-400">onboarding</div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => navigate(`/admin/city-partners/${p.id}`)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Detalii" data-testid={`view-${p.id}`}><Eye className="w-4 h-4" /></button>
                    <button onClick={() => { setEditing(p); setFormOpen(true); }} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Editează" data-testid={`edit-${p.id}`}><Edit3 className="w-4 h-4" /></button>
                    {p.status !== "terminated" && (
                      <button onClick={() => archive(p)} className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10" title="Încetează" data-testid={`archive-${p.id}`}><Trash2 className="w-4 h-4" /></button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {stats?.top_partners?.length > 0 && (
        <div className="mt-6 bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-500" /> Top parteneri (după lead-uri)
          </div>
          <div className="space-y-2">
            {stats.top_partners.map((t, i) => (
              <div key={t.partner_id} className="flex items-center justify-between text-sm">
                <span className="font-semibold text-slate-900 dark:text-white">{i + 1}. {t.company}</span>
                <span className="text-xs text-slate-500">{t.city} · {t.lead_count} lead-uri · {t.revenue || 0} RON</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {formOpen && <PartnerForm initial={editing} saving={saving} onClose={() => { setFormOpen(false); setEditing(null); }} onSave={save} />}
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

export default CityPartnersPage;
export { CityPartnersPage };
