// MarketplacePartnersPage — Admin list + AI Copilot for the Marketplace Partners Ecosystem.
// Route: /admin/marketplace-partners
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import {
  ShoppingBag, Plus, Loader2, ChevronLeft, X, Save, Edit3, Eye, KeyRound,
  Sparkles, TrendingUp, AlertTriangle, Trash2, Award, FileText, Mail,
  MapPin, Tag, Building, Bot, RotateCcw,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });
import { KpiCard, AIInsightCard } from "../../design-system";

const TIER_META = {
  basic: { label: "Basic", color: "bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300" },
  verified: { label: "Verified", color: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300" },
  premium: { label: "Premium", color: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300" },
  strategic: { label: "Strategic", color: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  exclusive: { label: "Exclusive", color: "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-500/15 dark:text-fuchsia-300" },
};
const STATUS_META = {
  prospect: { label: "Prospect", color: "bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300" },
  onboarding: { label: "Onboarding", color: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  active: { label: "Activ", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  paused: { label: "Pauzat", color: "bg-slate-200 text-slate-700" },
  terminated: { label: "Încetat", color: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};

const PartnerForm = ({ initial, onSave, onClose, saving, categories, tiers, packages }) => {
  const [f, setF] = useState(() => ({
    company: initial?.company || "",
    cui: initial?.cui || "",
    contact_name: initial?.contact_name || "",
    contact_email: initial?.contact_email || "",
    contact_phone: initial?.contact_phone || "",
    website: initial?.website || "",
    city: initial?.city || "",
    county: initial?.county || "",
    categories: initial?.categories || [],
    zones: (initial?.zones || []).join(", "),
    tier: initial?.tier || "basic",
    status: initial?.status || "prospect",
    package: initial?.package || "starter",
    notes: initial?.notes || "",
  }));
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  const toggleCat = (c) => setF(x => ({ ...x, categories: x.categories.includes(c) ? x.categories.filter(y => y !== c) : [...x.categories, c] }));

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="mkt-form-modal">
      <form onSubmit={e => { e.preventDefault(); onSave({ ...f, zones: f.zones.split(",").map(s => s.trim()).filter(Boolean) }); }} className="w-full max-w-3xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">{initial ? "Editează partener" : "Adaugă partener marketplace"}</h2>
          <button type="button" onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto">
          {[
            ["Companie *", "company"], ["CUI", "cui"], ["Persoană contact *", "contact_name"],
            ["Email *", "contact_email"], ["Telefon", "contact_phone"], ["Website", "website"],
            ["Oraș *", "city"], ["Județ", "county"],
          ].map(([lbl, k]) => (
            <div key={k}>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{lbl}</label>
              <input type={k === "contact_email" ? "email" : "text"} required={lbl.includes("*")} value={f[k]} onChange={e => set(k, e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                data-testid={`mkt-field-${k}`} />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Nivel partener</label>
            <select value={f.tier} onChange={e => set("tier", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="mkt-field-tier">
              {(tiers || ["basic", "verified", "premium", "strategic", "exclusive"]).map(t => <option key={t} value={t}>{TIER_META[t]?.label || t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Pachet</label>
            <select value={f.package} onChange={e => set("package", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="mkt-field-package">
              {(packages || ["starter", "business", "premium", "enterprise"]).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Status</label>
            <select value={f.status} onChange={e => set("status", e.target.value)} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="mkt-field-status">
              {Object.entries(STATUS_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Zone deservite (separate prin virgulă)</label>
            <input value={f.zones} onChange={e => set("zones", e.target.value)} placeholder="Cluj, Mureș, Bistrița"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="mkt-field-zones" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Categorii produse / servicii ({f.categories.length})</label>
            <div className="flex flex-wrap gap-1.5 p-2 rounded-lg border border-slate-200 dark:border-slate-700 max-h-32 overflow-y-auto">
              {(categories || []).map(c => {
                const on = f.categories.includes(c);
                return (
                  <button type="button" key={c} onClick={() => toggleCat(c)}
                    className={`text-[11px] px-2 py-1 rounded-full transition-colors ${on ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 font-medium" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 hover:bg-slate-200"}`}
                    data-testid={`mkt-cat-${c.replace(/\s+/g, '-')}`}>{c}</button>
                );
              })}
            </div>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Note interne</label>
            <textarea value={f.notes} onChange={e => set("notes", e.target.value)} rows={2}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="mkt-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}{initial ? "Salvează" : "Adaugă"}
          </button>
        </div>
      </form>
    </div>
  );
};

const CopilotPanel = ({ open, onClose }) => {
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const run = async () => {
    setBusy(true); setErr(""); setReport(null);
    try {
      const { data } = await ax.post("/api/admin/marketplace-partners/copilot/analyze");
      setReport(data);
    } catch (e) { setErr(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="mkt-copilot-panel">
      <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2"><Bot className="w-4 h-4 text-cyan-500" /> AI Marketplace Copilot</h3>
          <button onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          {!report && !busy && (
            <button onClick={run} className="w-full px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium flex items-center justify-center gap-2" data-testid="run-mkt-copilot">
              <Sparkles className="w-4 h-4" /> Analizează parteneri & oportunități
            </button>
          )}
          {busy && <div className="text-center py-6"><Loader2 className="w-6 h-6 animate-spin mx-auto text-cyan-500" /><p className="text-sm text-slate-500 mt-2">Claude analizează ecosistemul…</p></div>}
          {err && <div className="text-rose-500 text-sm">{err}</div>}
          {report && (
            <div className="space-y-4 text-sm">
              <div className="p-4 rounded-xl bg-cyan-50 dark:bg-cyan-500/10">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold uppercase text-cyan-700 dark:text-cyan-300">Growth score</span>
                  <span className="text-2xl font-bold text-cyan-700 dark:text-cyan-300">{report.growth_score}/100</span>
                </div>
                <p className="text-slate-700 dark:text-slate-200">{report.summary}</p>
              </div>
              {report.hot_categories?.length > 0 && (
                <div><h4 className="font-bold mb-1.5 text-emerald-700 dark:text-emerald-400">🔥 Categorii hot</h4>
                  {report.hot_categories.map((c, i) => <div key={i} className="py-1 text-xs"><strong>{c.name}</strong> · {c.reason}</div>)}
                </div>
              )}
              {report.top_converters?.length > 0 && (
                <div><h4 className="font-bold mb-1.5 text-blue-700 dark:text-blue-400">▲ Top converters</h4>
                  {report.top_converters.map((c, i) => <div key={i} className="py-1 text-xs"><strong>{c.company}</strong> · {c.reason}</div>)}
                </div>
              )}
              {report.commercial_opportunities?.length > 0 && (
                <div><h4 className="font-bold mb-1.5 text-violet-700 dark:text-violet-400">💼 Oportunități comerciale</h4>
                  <ul className="list-disc pl-5 space-y-1 text-xs">{report.commercial_opportunities.map((o, i) => <li key={i}>{o}</li>)}</ul>
                </div>
              )}
              {report.pricing_recommendations?.length > 0 && (
                <div><h4 className="font-bold mb-1.5 text-amber-700 dark:text-amber-400">💰 Recomandări preț</h4>
                  <ul className="list-disc pl-5 space-y-1 text-xs">{report.pricing_recommendations.map((o, i) => <li key={i}>{o}</li>)}</ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PresentationModal = ({ partner, onClose }) => {
  const [busy, setBusy] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    ax.post(`/api/admin/marketplace-partners/${partner.id}/presentation`)
      .then(r => setData(r.data))
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false));
  }, [partner.id]);
  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="mkt-presentation-modal">
      <div className="w-full max-w-3xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-cyan-500 to-blue-600 text-white sticky top-0">
          <h3 className="font-bold flex items-center gap-2"><FileText className="w-4 h-4" /> Prezentare AI · {partner.company}</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          {busy && <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto text-cyan-500" /><p className="text-sm text-slate-500 mt-2">Claude generează prezentarea personalizată…</p></div>}
          {err && <div className="text-rose-500">{err}</div>}
          {data && (
            <>
              {data.slides?.map((s, i) => (
                <div key={i} className="mb-5 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-xs text-slate-400 mb-1">Slide {i + 1}</div>
                  <h4 className="font-bold text-slate-900 dark:text-white mb-2">{s.title}</h4>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700 dark:text-slate-200">
                    {(s.bullets || []).map((b, j) => <li key={j}>{b}</li>)}
                  </ul>
                </div>
              ))}
              {data.key_takeaway && (
                <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-cyan-50 to-blue-50 dark:from-cyan-500/10 dark:to-blue-500/10 border border-cyan-200 dark:border-cyan-500/30">
                  <div className="text-xs font-bold uppercase text-cyan-700 dark:text-cyan-300 mb-1">Key takeaway</div>
                  <p className="text-sm text-slate-800 dark:text-slate-100">{data.key_takeaway}</p>
                </div>
              )}
              {data.estimated_opportunity_text && (
                <div className="mt-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30">
                  <div className="text-xs font-bold uppercase text-emerald-700 dark:text-emerald-300 mb-1">Oportunitate estimată</div>
                  <p className="text-sm text-slate-800 dark:text-slate-100">{data.estimated_opportunity_text}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const MarketplacePartnersPage = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterTier, setFilterTier] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [presentPartner, setPresentPartner] = useState(null);
  const [creds, setCreds] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterStatus !== "all") params.status = filterStatus;
      if (filterTier !== "all") params.tier = filterTier;
      const [a, b] = await Promise.all([
        ax.get("/api/admin/marketplace-partners", { params }),
        ax.get("/api/admin/marketplace-partners/stats"),
      ]);
      setItems(a.data?.items || []);
      setStats(b.data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [filterStatus, filterTier]);

  const save = async (payload) => {
    setSaving(true);
    try {
      if (editing) {
        const { data } = await ax.patch(`/api/admin/marketplace-partners/${editing.id}`, payload);
        setItems(arr => arr.map(x => x.id === data.id ? data : x));
      } else {
        const { data } = await ax.post("/api/admin/marketplace-partners", payload);
        setItems(arr => [data, ...arr]);
      }
      setFormOpen(false); setEditing(null);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const archive = async (p) => {
    if (!window.confirm(`Încetează colaborarea cu ${p.company}?`)) return;
    try {
      await ax.delete(`/api/admin/marketplace-partners/${p.id}`);
      setItems(arr => arr.map(x => x.id === p.id ? { ...x, status: "terminated" } : x));
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const restore = async (p) => {
    if (!window.confirm(`Reactivezi colaborarea cu ${p.company}?`)) return;
    try {
      const { data } = await ax.patch(`/api/admin/marketplace-partners/${p.id}`, { status: "active" });
      setItems(arr => arr.map(x => x.id === p.id ? data : x));
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const createLogin = async (p) => {
    if (!window.confirm(`Creezi un cont MARKETPLACE_PARTNER pentru ${p.company}?`)) return;
    try {
      const { data } = await ax.post(`/api/admin/marketplace-partners/${p.id}/create-login`);
      setCreds({ ...data, partner: p });
      load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="marketplace-partners-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <ShoppingBag className="w-5 h-5 text-violet-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Marketplace Partners Ecosystem</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/15 text-violet-700 dark:text-violet-400">V1 · ENTERPRISE</span>
        <div className="flex-1" />
        <button onClick={() => setCopilotOpen(true)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white flex items-center gap-1.5" data-testid="open-mkt-copilot">
          <Bot className="w-3.5 h-3.5" /> AI Marketplace Copilot
        </button>
      </div>

      {stats && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <KpiCard icon={Building} label="Parteneri total" value={stats.total_partners} accent="info" testid="mkt-kpi-total" />
            <KpiCard icon={Award} label="Activi" value={stats.by_status?.active || 0} accent="success" testid="mkt-kpi-active" />
            <KpiCard icon={TrendingUp} label="Lead-uri" value={stats.total_leads} accent="warning" testid="mkt-kpi-leads" />
            <KpiCard icon={Tag} label="Conversii" value={stats.leads_by_stage?.converted || 0} accent="ai" testid="mkt-kpi-conversions" />
          </div>
          <div className="mb-6">
            <AIInsightCard
              bullets={[
                `${stats.by_status?.active || 0} din ${stats.total_partners || 0} parteneri sunt activi${stats.total_partners ? ` (${Math.round((stats.by_status?.active || 0) / stats.total_partners * 100)}%)` : ""}.`,
                ...(stats.total_leads ? [`${stats.total_leads} lead-uri generate, ${stats.leads_by_stage?.converted || 0} convertite${stats.total_leads ? ` (${Math.round((stats.leads_by_stage?.converted || 0) / stats.total_leads * 100)}% conversie)` : ""}.`] : []),
                ...(stats.top_categories?.[0] ? [`Categoria cu cei mai mulți parteneri: «${stats.top_categories[0].name}» (${stats.top_categories[0].count}).`] : []),
              ]}
              alerts={(stats.by_status?.prospect || 0) > (stats.by_status?.active || 0) ? [`${stats.by_status.prospect} prospecți așteaptă onboarding — mai mulți decât partenerii activi.`] : []}
              recommendations={["Rulează AI Marketplace Copilot pentru analiza completă a ecosistemului."]}
              onAction={() => setCopilotOpen(true)} actionLabel="Rulează AI Copilot"
              llmModule="marketplace" testid="mkt-ai-insights"
            />
          </div>
        </>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="filter-status">
          <option value="all">Toate statusurile</option>
          {Object.entries(STATUS_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <select value={filterTier} onChange={e => setFilterTier(e.target.value)} className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="filter-tier">
          <option value="all">Toate nivelurile</option>
          {Object.entries(TIER_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <div className="flex-1" />
        <button onClick={() => { setEditing(null); setFormOpen(true); }} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5" data-testid="add-mkt-partner">
          <Plus className="w-3.5 h-3.5" /> Adaugă partener
        </button>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {loading && <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-slate-400" /></div>}
        {error && <div className="p-6 text-rose-500 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {error}</div>}
        {!loading && items.length === 0 && !error && <div className="p-10 text-center text-sm text-slate-500">Niciun partener marketplace. Apasă „Adaugă partener” pentru a începe.</div>}
        {!loading && items.length > 0 && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.map(p => {
              const tier = TIER_META[p.tier] || TIER_META.basic;
              const st = STATUS_META[p.status] || STATUS_META.prospect;
              return (
                <div key={p.id} className="p-4 flex flex-wrap items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`mkt-row-${p.id}`}>
                  <div className="flex-1 min-w-[240px]">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">{p.company}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${tier.color}`}>{tier.label}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${st.color}`}>{st.label}</span>
                      {p.package && <span className="text-[10px] uppercase text-slate-400">{p.package}</span>}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-3 flex-wrap">
                      <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{p.city}{p.county ? `, ${p.county}` : ""}</span>
                      <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{p.contact_email}</span>
                      {p.cui && <span className="text-[10px]">CUI: {p.cui}</span>}
                    </div>
                    {p.categories?.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {p.categories.slice(0, 5).map(c => <span key={c} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">{c}</span>)}
                        {p.categories.length > 5 && <span className="text-[10px] text-slate-400">+{p.categories.length - 5}</span>}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setPresentPartner(p)} className="p-1.5 rounded-lg text-cyan-500 hover:bg-cyan-50 dark:hover:bg-cyan-500/10" title="Generează prezentare AI" data-testid={`pitch-${p.id}`}><FileText className="w-4 h-4" /></button>
                    {!p.linked_user_id && (
                      <button onClick={() => createLogin(p)} className="p-1.5 rounded-lg text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-500/10" title="Creează cont partener" data-testid={`login-${p.id}`}><KeyRound className="w-4 h-4" /></button>
                    )}
                    <button onClick={() => { setEditing(p); setFormOpen(true); }} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Editează" data-testid={`edit-${p.id}`}><Edit3 className="w-4 h-4" /></button>
                    {p.status !== "terminated" && (
                      <button onClick={() => archive(p)} className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10" title="Încetează" data-testid={`archive-${p.id}`}><Trash2 className="w-4 h-4" /></button>
                    )}
                    {p.status === "terminated" && (
                      <button onClick={() => restore(p)} className="p-1.5 rounded-lg text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-500/10" title="Restaurează partenerul" data-testid={`restore-${p.id}`}><RotateCcw className="w-4 h-4" /></button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {stats?.top_categories?.length > 0 && (
        <div className="mt-6 bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
            <Tag className="w-3.5 h-3.5 text-violet-500" /> Top categorii
          </div>
          <div className="flex flex-wrap gap-2">
            {stats.top_categories.map(c => (
              <span key={c.name} className="text-xs px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
                {c.name} <span className="text-violet-500 font-bold ml-1">{c.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {formOpen && (
        <PartnerForm
          initial={editing}
          saving={saving}
          categories={stats?.available_categories}
          tiers={stats?.tiers}
          packages={stats?.packages}
          onClose={() => { setFormOpen(false); setEditing(null); }}
          onSave={save}
        />
      )}
      <CopilotPanel open={copilotOpen} onClose={() => setCopilotOpen(false)} />
      {presentPartner && <PresentationModal partner={presentPartner} onClose={() => setPresentPartner(null)} />}
      {creds && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60" data-testid="creds-modal">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-amber-300 dark:border-amber-500/40">
            <div className="px-6 py-4 border-b bg-amber-50 dark:bg-amber-500/10 flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-amber-600" />
              <h3 className="font-bold text-slate-900 dark:text-white">Cont creat pentru {creds.partner.company}</h3>
            </div>
            <div className="p-6 space-y-3">
              <div><div className="text-[11px] uppercase font-bold text-slate-500">Email</div><code className="text-sm">{creds.email}</code></div>
              {creds.temp_password && (
                <div><div className="text-[11px] uppercase font-bold text-slate-500">Parolă temporară (afișată O SINGURĂ DATĂ)</div>
                  <code className="block px-2 py-1 mt-1 bg-slate-100 dark:bg-slate-800 rounded text-sm font-mono">{creds.temp_password}</code>
                </div>
              )}
              <p className="text-[11px] text-amber-600">Trimite credențialele prin canal sigur.</p>
              <button onClick={() => setCreds(null)} className="w-full mt-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm">OK, am salvat</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketplacePartnersPage;
export { MarketplacePartnersPage };
