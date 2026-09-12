// PartnerDashboard — Self-service portal for city_partner role.
// Route: /partner/dashboard
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2, Users, TrendingUp, Plus, LogOut, Loader2, MapPin,
  CheckCircle2, Circle, Save, X, AlertTriangle, Activity, Mail, Bot, Sparkles, Zap,
} from "lucide-react";
import { useAuth } from "../../auth";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STAGE_LBL = {
  introduced: "Introdus",
  contacted: "Contactat",
  onboarded: "Onboarded",
  converted: "Convertit",
  lost: "Pierdut",
};

const STAGE_COLOR = {
  introduced: "bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300",
  contacted: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  onboarded: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  converted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  lost: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
};

const AddLeadModal = ({ onClose, onSave, saving }) => {
  const [f, setF] = useState({ lead_name: "", lead_email: "", lead_phone: "", source: "", notes: "" });
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <form onSubmit={e => { e.preventDefault(); onSave(f); }} className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Adaugă referință (lead)</h3>
          <button type="button" onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-3">
          <input required placeholder="Nume client / asociație *" value={f.lead_name} onChange={e => setF({ ...f, lead_name: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="partner-lead-name" />
          <input type="email" placeholder="Email contact" value={f.lead_email} onChange={e => setF({ ...f, lead_email: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="partner-lead-email" />
          <input placeholder="Telefon" value={f.lead_phone} onChange={e => setF({ ...f, lead_phone: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" />
          <input placeholder="Sursă (ex: recomandare, eveniment)" value={f.source} onChange={e => setF({ ...f, source: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" />
          <textarea placeholder="Note opționale" rows={2} value={f.notes} onChange={e => setF({ ...f, notes: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" />
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm text-slate-600 rounded-lg hover:bg-slate-100">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="partner-lead-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Trimite
          </button>
        </div>
      </form>
    </div>
  );
};

const PartnerDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [m, s, l] = await Promise.all([
        ax.get("/api/partner/me"),
        ax.get("/api/partner/stats"),
        ax.get("/api/partner/leads"),
      ]);
      setMe(m.data);
      setStats(s.data);
      setLeads(l.data?.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const addLead = async (payload) => {
    setSaving(true);
    try {
      const { data } = await ax.post("/api/partner/leads", { ...payload, stage: "introduced" });
      setLeads(arr => [data, ...arr]);
      setAddOpen(false);
      load();  // refresh stats
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const doLogout = async () => { await logout(); navigate("/login"); };

  // ── AI City Partner Copilot ──
  const [nudges, setNudges] = useState(null);
  const [nudgesBusy, setNudgesBusy] = useState(false);
  const runNudges = async () => {
    setNudgesBusy(true);
    try {
      const { data } = await ax.post("/api/partner/copilot/nudges");
      setNudges(data.nudges || []);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setNudgesBusy(false); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;
  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 gap-4">
      <AlertTriangle className="w-10 h-10 text-rose-500" />
      <div className="text-rose-500">{error}</div>
      <button onClick={doLogout} className="px-3 py-1.5 text-sm rounded-lg bg-slate-200 dark:bg-slate-800">Logout</button>
    </div>
  );

  const p = me?.partner;
  const onboarding = me?.onboarding_steps || [];
  const total = stats?.leads_total || 0;
  const conv = stats?.leads_by_stage?.converted || 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950" data-testid="partner-dashboard">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-6xl mx-auto px-4 lg:px-8 py-4 flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Building2 className="w-6 h-6 text-cyan-500" />
            <div>
              <h1 className="text-base lg:text-lg font-bold text-slate-900 dark:text-white">{p?.company}</h1>
              <div className="text-xs text-slate-500 flex items-center gap-1"><MapPin className="w-3 h-3" />{p?.city}</div>
            </div>
          </div>
          <div className="flex-1" />
          <span className="text-[10px] font-bold uppercase px-2 py-1 rounded bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-400">CITY PARTNER · V1</span>
          <Link to="/legal/sign" className="text-xs text-slate-600 hover:text-slate-900 dark:hover:text-white flex items-center gap-1"><Mail className="w-3 h-3" /> Contract</Link>
          <button onClick={doLogout} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" title="Logout" data-testid="partner-logout"><LogOut className="w-4 h-4" /></button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4 lg:p-8">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Bună, {me?.user?.name?.split(" ")[0] || "Partener"}!</h2>

        {/* AI Copilot Nudges */}
        <div className="mb-6 bg-gradient-to-br from-cyan-50 to-blue-50 dark:from-cyan-500/10 dark:to-blue-500/10 rounded-2xl p-5 border border-cyan-200 dark:border-cyan-500/30" data-testid="copilot-nudges-card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <h3 className="font-bold text-slate-900 dark:text-white">AI City Partner Copilot</h3>
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-cyan-200 dark:bg-cyan-500/30 text-cyan-800 dark:text-cyan-200">Claude</span>
            </div>
            <button onClick={runNudges} disabled={nudgesBusy} className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-60" data-testid="run-nudges">
              {nudgesBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
              {nudgesBusy ? "Se generează…" : nudges ? "Re-rulează" : "3 acțiuni săptămâna asta"}
            </button>
          </div>
          {!nudges && !nudgesBusy && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Apasă butonul ca să primești 3 nudge-uri personalizate (bazate pe lead-urile tale curente).
            </p>
          )}
          {nudges && nudges.length === 0 && <p className="text-sm text-slate-500">Niciun nudge generat.</p>}
          {nudges && nudges.length > 0 && (
            <div className="space-y-2.5">
              {nudges.map((n, i) => (
                <div key={i} className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-cyan-100 dark:border-cyan-500/20" data-testid={`nudge-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-cyan-500" />{n.title}</h4>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                      n.priority === "high" ? "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300"
                      : n.priority === "low" ? "bg-slate-100 text-slate-600 dark:bg-slate-700/40 dark:text-slate-300"
                      : "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"
                    }`}>{n.priority}</span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300">{n.body}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <StatCard icon={Users} label="Lead-uri introduse" value={total} color="text-blue-500" />
          <StatCard icon={CheckCircle2} label="Convertite" value={conv} color="text-emerald-500" />
          <StatCard icon={TrendingUp} label="Conversie" value={`${stats?.conversion_rate || 0}%`} color="text-violet-500" />
          <StatCard icon={Activity} label="Onboarding" value={`${p?.onboarding_step}/${stats?.partner?.onboarding_steps_total || 7}`} color="text-amber-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Onboarding tracker (read-only) */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Stadiul colaborării</div>
            <div className="space-y-1.5">
              {onboarding.map((step, i) => {
                const done = (i + 1) <= (p?.onboarding_step || 0);
                return (
                  <div key={i} className="flex items-center gap-3 p-1.5">
                    {done ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> : <Circle className="w-4 h-4 text-slate-300 shrink-0" />}
                    <span className={`text-sm ${done ? "text-slate-900 dark:text-white" : "text-slate-500"}`}>{step}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] text-slate-400 italic">Echipa PropManage actualizează stadiul pe măsură ce avansăm împreună.</p>
          </div>

          {/* Lead-uri */}
          <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" /> Referințele mele ({leads.length})
              </div>
              <button onClick={() => setAddOpen(true)} className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium flex items-center gap-1" data-testid="partner-add-lead">
                <Plus className="w-3 h-3" /> Adaugă referință
              </button>
            </div>
            {leads.length === 0
              ? <div className="p-10 text-center text-sm text-slate-500">Niciun lead introdus încă. Apasă „Adaugă referință” pentru a începe.</div>
              : <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {leads.map(l => (
                  <div key={l.id} className="p-3 flex items-center gap-3" data-testid={`partner-lead-row-${l.id}`}>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{l.lead_name}</div>
                      <div className="text-[11px] text-slate-500 truncate">{l.lead_email || "—"} · {l.source || "—"} · {l.introduced_at ? new Date(l.introduced_at).toLocaleDateString("ro-RO") : ""}</div>
                    </div>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${STAGE_COLOR[l.stage] || STAGE_COLOR.introduced}`}>{STAGE_LBL[l.stage] || l.stage}</span>
                    {l.revenue_generated > 0 && <span className="text-xs font-bold text-emerald-600">{l.revenue_generated} RON</span>}
                  </div>
                ))}
              </div>
            }
          </div>
        </div>

        <p className="mt-6 text-[11px] text-center text-slate-400 italic">
          „Colaborarea este non-exclusivă și nu reprezintă asociere în companie. Funcționalități viitoare doar prin acte adiționale.”
        </p>
      </div>

      {addOpen && <AddLeadModal onClose={() => setAddOpen(false)} onSave={addLead} saving={saving} />}
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

export default PartnerDashboard;
export { PartnerDashboard };
