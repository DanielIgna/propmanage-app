// MarketplacePartnerPortal — self-service pentru role=marketplace_partner.
// Route: /partner/marketplace · API: /api/marketplace-partner/{me,stats,leads}
// Creat de Product Guardian: backend-ul exista, UI-ul lipsea — 4 parteneri reali aterizau pe landing.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Award, Loader2, Plus, Users, TrendingUp, BadgeEuro, Target, X,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STAGE_META = {
  new: { label: "Nou", cls: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  qualified: { label: "Calificat", cls: "bg-violet-500/15 text-violet-300 border-violet-500/30" },
  contacted: { label: "Contactat", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  converted: { label: "Convertit", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  lost: { label: "Pierdut", cls: "bg-stone-500/15 text-stone-400 border-stone-600/30" },
};

const Stat = ({ icon: Icon, label, value }) => (
  <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4" data-testid={`mp-stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
    <div className="flex items-center gap-2 text-xs text-stone-400 uppercase tracking-wider">
      <Icon className="w-3.5 h-3.5 text-[#d4ff3a]" /> {label}
    </div>
    <div className="text-2xl font-bold text-white mt-1.5">{value}</div>
  </div>
);

const AddLeadModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ lead_name: "", lead_phone: "", lead_email: "", estimated_value: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const { data } = await ax.post("/api/marketplace-partner/leads", {
        lead_name: form.lead_name,
        lead_phone: form.lead_phone || null,
        lead_email: form.lead_email || null,
        estimated_value: Number(form.estimated_value) || 0,
        notes: form.notes || null,
        stage: "new",
      });
      onCreated(data);
      onClose();
    } catch (ex) {
      setErr(ex?.response?.data?.detail || ex.message);
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-[80] bg-black/70 flex items-center justify-center p-4" data-testid="mp-add-lead-modal">
      <form onSubmit={submit} className="w-full max-w-md bg-stone-900 border border-stone-700 rounded-2xl p-5 space-y-3">
        <div className="flex items-center">
          <h2 className="text-white font-bold">Lead nou</h2>
          <button type="button" onClick={onClose} className="ml-auto text-stone-400 hover:text-white" data-testid="mp-lead-close"><X className="w-4 h-4" /></button>
        </div>
        {err && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="mp-lead-error">{err}</div>}
        <input required minLength={2} placeholder="Nume client *" value={form.lead_name}
          onChange={e => setForm(f => ({ ...f, lead_name: e.target.value }))}
          className="w-full bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="mp-lead-name" />
        <input placeholder="Telefon" value={form.lead_phone}
          onChange={e => setForm(f => ({ ...f, lead_phone: e.target.value }))}
          className="w-full bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="mp-lead-phone" />
        <input type="email" placeholder="Email" value={form.lead_email}
          onChange={e => setForm(f => ({ ...f, lead_email: e.target.value }))}
          className="w-full bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="mp-lead-email" />
        <input type="number" min="0" placeholder="Valoare estimată (EUR)" value={form.estimated_value}
          onChange={e => setForm(f => ({ ...f, estimated_value: e.target.value }))}
          className="w-full bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="mp-lead-value" />
        <textarea placeholder="Note" rows={2} value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          className="w-full bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="mp-lead-notes" />
        <button disabled={busy} className="w-full py-2.5 rounded-xl bg-[#d4ff3a] text-stone-900 font-bold text-sm disabled:opacity-50" data-testid="mp-lead-submit">
          {busy ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Adaugă lead"}
        </button>
      </form>
    </div>
  );
};

export default function MarketplacePartnerPortal() {
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, s, l] = await Promise.all([
        ax.get("/api/marketplace-partner/me"),
        ax.get("/api/marketplace-partner/stats"),
        ax.get("/api/marketplace-partner/leads"),
      ]);
      setMe(m.data); setStats(s.data); setLeads(l.data.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="min-h-screen bg-stone-950 flex items-center justify-center" data-testid="mp-portal-loading"><Loader2 className="w-6 h-6 animate-spin text-stone-500" /></div>;
  if (error) return (
    <div className="min-h-screen bg-stone-950 flex items-center justify-center p-6">
      <div className="text-center max-w-sm" data-testid="mp-portal-error">
        <Award className="w-8 h-8 text-stone-600 mx-auto mb-3" />
        <p className="text-sm text-stone-300">{error}</p>
        <p className="text-xs text-stone-500 mt-2">Contactează echipa PropManage dacă crezi că e o eroare.</p>
      </div>
    </div>
  );

  const p = stats?.partner || {};
  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8" data-testid="mp-partner-portal">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-6">
          <Award className="w-5 h-5 text-[#d4ff3a]" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">{p.company || me?.user?.name}</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/30">Partener Marketplace{p.tier ? ` · ${p.tier}` : ""}</span>
          <div className="flex-1" />
          <button onClick={() => setShowAdd(true)}
            className="px-4 py-1.5 text-xs rounded-lg bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5"
            data-testid="mp-add-lead-btn">
            <Plus className="w-3.5 h-3.5" /> Lead nou
          </button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <Stat icon={Users} label="Lead-uri" value={stats?.leads_total ?? 0} />
          <Stat icon={Target} label="Convertite" value={stats?.leads_by_stage?.converted ?? 0} />
          <Stat icon={TrendingUp} label="Rată conversie" value={`${stats?.conversion_rate ?? 0}%`} />
          <Stat icon={BadgeEuro} label="Venit generat" value={`€${stats?.revenue_generated ?? 0}`} />
        </div>

        <div className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">Lead-urile tale</div>
        {leads.length === 0 ? (
          <div className="p-10 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="mp-no-leads">
            Niciun lead încă. Adaugă primul lead cu butonul de sus.
          </div>
        ) : (
          <div className="border border-stone-800 rounded-2xl bg-stone-900/30 divide-y divide-stone-800/60" data-testid="mp-leads-list">
            {leads.map(l => (
              <div key={l.id} className="px-4 py-3 flex items-center gap-3 flex-wrap text-sm" data-testid={`mp-lead-${l.id}`}>
                <span className="font-semibold text-white">{l.lead_name}</span>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${(STAGE_META[l.stage] || STAGE_META.new).cls}`}>
                  {(STAGE_META[l.stage] || STAGE_META.new).label}
                </span>
                {l.lead_phone && <span className="text-xs text-stone-400">{l.lead_phone}</span>}
                <div className="flex-1" />
                {Number(l.estimated_value) > 0 && <span className="text-xs text-stone-400">est. €{l.estimated_value}</span>}
                <span className="text-[11px] text-stone-600">{l.created_at ? new Date(l.created_at).toLocaleDateString("ro-RO") : ""}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {showAdd && <AddLeadModal onClose={() => setShowAdd(false)} onCreated={() => load()} />}
    </div>
  );
}
