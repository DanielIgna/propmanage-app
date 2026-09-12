// CityPartnerDetailPage — Admin detail view: onboarding wizard + leads + create-login.
// Route: /admin/city-partners/:id
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Building2, ChevronLeft, ChevronRight, Loader2, CheckCircle2, Circle,
  Users, Plus, Mail, Phone, MapPin, TrendingUp, KeyRound, Copy, X,
  AlertTriangle, Save, Edit3,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STAGE_COLORS = {
  introduced: "bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300",
  contacted: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  onboarded: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  converted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  lost: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
};

const ONBOARDING_STEPS = [
  "Prezentare oficială",
  "Introducere în ecosistem",
  "Prezentare pe grupurile disponibile",
  "Invitație către administratori",
  "Creare conturi platformă",
  "Urmărire social media",
  "Activare campanii locale",
];

const LeadForm = ({ onClose, onSave, saving }) => {
  const [f, setF] = useState({ lead_name: "", lead_email: "", lead_phone: "", source: "", stage: "introduced", notes: "" });
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <form onSubmit={e => { e.preventDefault(); onSave(f); }} className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Adaugă lead nou</h3>
          <button type="button" onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-3">
          <input required placeholder="Nume lead *" value={f.lead_name} onChange={e => setF({ ...f, lead_name: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-name" />
          <input type="email" placeholder="Email" value={f.lead_email} onChange={e => setF({ ...f, lead_email: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-email" />
          <input placeholder="Telefon" value={f.lead_phone} onChange={e => setF({ ...f, lead_phone: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-phone" />
          <input placeholder="Sursă (ex: WhatsApp, evenim. local)" value={f.source} onChange={e => setF({ ...f, source: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-source" />
          <select value={f.stage} onChange={e => setF({ ...f, stage: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-stage">
            {Object.keys(STAGE_COLORS).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <textarea placeholder="Note" rows={2} value={f.notes} onChange={e => setF({ ...f, notes: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="lead-notes" />
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-sm text-slate-600 rounded-lg hover:bg-slate-100">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="lead-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează
          </button>
        </div>
      </form>
    </div>
  );
};

const CityPartnerDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [partner, setPartner] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [leadFormOpen, setLeadFormOpen] = useState(false);
  const [savingLead, setSavingLead] = useState(false);
  const [creds, setCreds] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [p, l] = await Promise.all([
        ax.get(`/api/admin/city-partners/${id}`),
        ax.get(`/api/admin/city-partners/${id}/leads`),
      ]);
      setPartner(p.data);
      setLeads(l.data?.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [id]);

  const setStep = async (step) => {
    try {
      const { data } = await ax.post(`/api/admin/city-partners/${id}/onboarding-step`, { step });
      setPartner(data);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const addLead = async (payload) => {
    setSavingLead(true);
    try {
      const { data } = await ax.post(`/api/admin/city-partners/${id}/leads`, payload);
      setLeads(arr => [data, ...arr]);
      setLeadFormOpen(false);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSavingLead(false); }
  };

  const updateLeadStage = async (leadId, stage) => {
    try {
      const { data } = await ax.patch(`/api/admin/city-partners/leads/${leadId}`, { stage });
      setLeads(arr => arr.map(x => x.id === data.id ? data : x));
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const createLogin = async () => {
    if (!window.confirm(`Creezi un cont CITY_PARTNER pentru ${partner.company}?`)) return;
    try {
      const { data } = await ax.post(`/api/admin/city-partners/${id}/create-login`);
      setCreds(data);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;
  if (error) return <div className="p-8 text-rose-500"><AlertTriangle className="w-4 h-4 inline mr-1" /> {error}</div>;
  if (!partner) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="city-partner-detail">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin/city-partners" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Parteneri</Link>
        <span className="text-slate-300">·</span>
        <Building2 className="w-5 h-5 text-cyan-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">{partner.company}</h1>
        <span className="text-xs text-slate-500">{partner.city}{partner.county ? `, ${partner.county}` : ""}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: contact + actions */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Contact</div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200"><Users className="w-4 h-4 text-slate-400" />{partner.contact_name}</div>
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200"><Mail className="w-4 h-4 text-slate-400" />{partner.contact_email}</div>
              {partner.contact_phone && <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200"><Phone className="w-4 h-4 text-slate-400" />{partner.contact_phone}</div>}
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200"><MapPin className="w-4 h-4 text-slate-400" />{partner.city}{partner.county ? `, ${partner.county}` : ""}</div>
            </div>
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
              <div><div className="text-slate-400">Apartamente</div><div className="font-bold text-slate-900 dark:text-white">{partner.units_managed}</div></div>
              <div><div className="text-slate-400">Ritm creștere</div><div className="font-bold text-slate-900 dark:text-white">{partner.growth_rate || "—"}</div></div>
              <div className="col-span-2"><div className="text-slate-400">Tip portofoliu</div><div className="font-medium text-slate-700 dark:text-slate-200">{partner.portfolio_type || "—"}</div></div>
            </div>
            {partner.notes && <div className="mt-3 text-xs text-slate-500 italic">„{partner.notes}”</div>}
          </div>

          {/* Cont partener */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5" /> Cont City Partner
            </div>
            {partner.linked_user_id
              ? <div className="text-sm text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4" /> Cont activ — partenerul poate accesa portalul</div>
              : <>
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">Generează credențiale dedicate ca partenerul să acceseze portalul propriu (vede doar lead-urile sale).</p>
                <button onClick={createLogin} className="w-full px-3 py-2 rounded-lg bg-emerald-600 text-white text-xs font-medium flex items-center justify-center gap-1.5" data-testid="create-login">
                  <KeyRound className="w-3.5 h-3.5" /> Creează cont CITY_PARTNER
                </button>
              </>
            }
            {creds?.temp_password && (
              <div className="mt-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
                <div className="text-[11px] font-bold uppercase text-amber-700 dark:text-amber-300 mb-1">Parolă temporară (afișată O SINGURĂ DATĂ)</div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-white dark:bg-slate-900 px-2 py-1 rounded font-mono text-slate-900 dark:text-slate-100">{creds.temp_password}</code>
                  <button onClick={() => navigator.clipboard.writeText(creds.temp_password)} className="p-1 rounded hover:bg-amber-100 dark:hover:bg-amber-500/20" title="Copiază"><Copy className="w-3.5 h-3.5" /></button>
                </div>
                <div className="text-[10px] text-amber-700 dark:text-amber-300 mt-1">Trimite-o partenerului prin canal sigur. Email: <strong>{creds.email}</strong></div>
              </div>
            )}
          </div>
        </div>

        {/* Right: onboarding + leads */}
        <div className="lg:col-span-2 space-y-4">
          {/* Onboarding wizard */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800" data-testid="onboarding-wizard">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <ChevronRight className="w-3.5 h-3.5" /> Flux onboarding (7 pași)
              </div>
              <span className="text-xs text-slate-500"><strong className="text-slate-900 dark:text-white">{partner.onboarding_step}/7</strong> {partner.onboarding_complete && "· COMPLET"}</span>
            </div>
            <div className="space-y-1.5">
              {ONBOARDING_STEPS.map((step, i) => {
                const stepNo = i + 1;
                const done = stepNo <= partner.onboarding_step;
                return (
                  <button key={i} onClick={() => setStep(done && stepNo === partner.onboarding_step ? stepNo - 1 : stepNo)}
                    className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-colors ${done ? "bg-emerald-50 dark:bg-emerald-500/10" : "hover:bg-slate-50 dark:hover:bg-slate-800"}`}
                    data-testid={`onboarding-step-${stepNo}`}>
                    {done ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> : <Circle className="w-4 h-4 text-slate-300 shrink-0" />}
                    <span className={`text-sm flex-1 ${done ? "text-slate-900 dark:text-white" : "text-slate-600 dark:text-slate-400"}`}><strong>{stepNo}.</strong> {step}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Leads */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" /> Lead-uri ({leads.length})
              </div>
              <button onClick={() => setLeadFormOpen(true)} className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-xs font-medium flex items-center gap-1" data-testid="add-lead">
                <Plus className="w-3 h-3" /> Adaugă lead
              </button>
            </div>
            {leads.length === 0
              ? <div className="p-8 text-center text-sm text-slate-500">Niciun lead înregistrat încă pentru acest partener.</div>
              : <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {leads.map(l => (
                  <div key={l.id} className="p-3 flex items-center gap-3" data-testid={`lead-row-${l.id}`}>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{l.lead_name}</div>
                      <div className="text-[11px] text-slate-500 truncate">
                        {l.lead_email || "—"} · {l.source || "fără sursă"} · {l.introduced_at ? new Date(l.introduced_at).toLocaleDateString("ro-RO") : ""}
                      </div>
                    </div>
                    <select value={l.stage} onChange={e => updateLeadStage(l.id, e.target.value)} className={`text-[10px] font-bold uppercase px-1.5 py-1 rounded ${STAGE_COLORS[l.stage] || STAGE_COLORS.introduced} border-0`} data-testid={`lead-stage-${l.id}`}>
                      {Object.keys(STAGE_COLORS).map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    {l.revenue_generated > 0 && <span className="text-xs font-bold text-emerald-600">{l.revenue_generated} RON</span>}
                  </div>
                ))}
              </div>
            }
          </div>
        </div>
      </div>

      {leadFormOpen && <LeadForm onClose={() => setLeadFormOpen(false)} onSave={addLead} saving={savingLead} />}
    </div>
  );
};

export default CityPartnerDetailPage;
export { CityPartnerDetailPage };
