// Operations Center — inima operațională până la PMF (Directivă COO)
// Vizibilitate + execuție: pipeline leads, plăți manuale, gaps specialiști, raport COO, One Win.
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList, Loader2, RefreshCcw, Phone, Mail, MessageCircle, Banknote,
  AlertTriangle, Trophy, Users, TrendingUp, CheckCircle2, StickyNote, Bot, Zap
} from "lucide-react";
import { InspectorButton } from "../../components/founder/InspectorButton";
import axios from "axios";
import { OpsGapsPanel } from "./OpsGapsPanel";
import { OpsPaymentsPanel } from "./OpsPaymentsPanel";

const API = process.env.REACT_APP_BACKEND_URL;

const STAGE_LABELS = {
  new: "Nou", contacted: "Contactat", qualified: "Calificat", audit_scheduled: "Audit programat",
  audit_completed: "Audit finalizat", offer_sent: "Ofertă trimisă", waiting_decision: "Așteaptă decizia",
  payment_received: "Plată primită", project_active: "Proiect activ", completed: "Finalizat",
  follow_up: "Follow-up", lost: "Pierdut", won: "Câștigat",
};
const METHOD_LABELS = { cash: "Cash", bank_transfer: "Transfer bancar", pos: "POS", payment_link: "Link de plată", manual_stripe: "Stripe manual", other: "Altă metodă" };

const LeadRow = ({ lead, stages, onUpdate, busy }) => {
  const [note, setNote] = useState("");
  return (
    <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3.5" data-testid={`ops-lead-${lead.id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-sm font-medium text-white truncate">{lead.name || "Fără nume"} <span className="text-[10px] text-stone-500 ml-1">· {lead.source}</span></div>
          <div className="text-xs text-stone-400 truncate">{lead.email || "—"} · {lead.phone || "fără tel"} {lead.city ? `· ${lead.city}` : ""}</div>
          {lead.next_action && <div className="text-[11px] text-[#d4ff3a] mt-1">→ {lead.next_action}</div>}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {lead.phone && <a href={`tel:${lead.phone}`} className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10" title="Sună" data-testid={`ops-call-${lead.id}`}><Phone className="w-3.5 h-3.5 text-emerald-400" /></a>}
          {lead.phone && <a href={`https://wa.me/${String(lead.phone).replace(/[^0-9]/g, "")}`} target="_blank" rel="noreferrer" className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10" title="WhatsApp"><MessageCircle className="w-3.5 h-3.5 text-emerald-400" /></a>}
          {lead.email && <a href={`mailto:${lead.email}`} className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10" title="Email"><Mail className="w-3.5 h-3.5 text-cyan-400" /></a>}
          <select
            value={lead.stage || "new"}
            onChange={(e) => onUpdate(lead.id, { stage: e.target.value })}
            disabled={busy === lead.id}
            className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5 text-stone-200"
            data-testid={`ops-stage-select-${lead.id}`}
          >
            {stages.map(s => <option key={s} value={s}>{STAGE_LABELS[s] || s}</option>)}
            {!stages.includes(lead.stage) && lead.stage && <option value={lead.stage}>{STAGE_LABELS[lead.stage] || lead.stage}</option>}
          </select>
        </div>
      </div>
      <div className="flex gap-2 mt-2">
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Notă / next action..."
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-[#d4ff3a]"
          data-testid={`ops-note-input-${lead.id}`} />
        <button onClick={() => { if (note.trim()) { onUpdate(lead.id, { note, next_action: note }); setNote(""); } }}
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-stone-300 inline-flex items-center gap-1"
          data-testid={`ops-note-save-${lead.id}`}>
          <StickyNote className="w-3 h-3" /> Salvează
        </button>
      </div>
    </div>
  );
};

const PendingOrderRow = ({ order, methods, onPay, busy }) => {
  const [open, setOpen] = useState(false);
  const [method, setMethod] = useState("bank_transfer");
  const [ref, setRef] = useState("");
  return (
    <div className="bg-white/[0.02] border border-amber-500/20 rounded-xl p-3.5" data-testid={`ops-order-${order.id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="text-sm font-medium">{order.label || order.package} · <span className="text-[#d4ff3a]">{Number(order.amount_ron).toLocaleString("ro-RO")} RON</span>{order.demo_mode && <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded ml-2">DEMO</span>}</div>
          <div className="text-xs text-stone-400">{order.contact_name} · {order.contact_email} · {order.contact_phone || "fără tel"}</div>
          <div className="text-[11px] text-stone-500">{order.property_address}</div>
        </div>
        <button onClick={() => setOpen(!open)} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid={`ops-pay-toggle-${order.id}`}>
          <Banknote className="w-3.5 h-3.5" /> Plată manuală
        </button>
      </div>
      {open && (
        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-white/5" data-testid={`ops-pay-form-${order.id}`}>
          <select value={method} onChange={(e) => setMethod(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5" data-testid={`ops-pay-method-${order.id}`}>
            {methods.map(m => <option key={m} value={m}>{METHOD_LABELS[m] || m}</option>)}
          </select>
          <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="Referință (opțional)" className="flex-1 min-w-[140px] bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs outline-none" data-testid={`ops-pay-ref-${order.id}`} />
          <button onClick={() => onPay(order.id, method, ref)} disabled={busy === order.id}
            className="pm-btn pm-btn-success pm-btn-sm" data-testid={`ops-pay-confirm-${order.id}`}>
            {busy === order.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Confirmă VERIFIED
          </button>
        </div>
      )}
    </div>
  );
};

const AutonomousFollowupPanel = () => {
  const [st, setSt] = useState(null);
  const [running, setRunning] = useState(false);
  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/api/admin/leads/followup/status`, { withCredentials: true }); setSt(r.data); } catch (e) { console.error(e); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const runNow = async () => {
    setRunning(true);
    try {
      const r = await axios.post(`${API}/api/admin/leads/followup/run-cycle`, {}, { withCredentials: true });
      alert(`Ciclu executat: ${r.data.sent || 0} trimise · ${r.data.queued || 0} în coadă · ${r.data.failed || 0} eșuate`);
      await load();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); } finally { setRunning(false); }
  };
  if (!st) return null;
  const active = st.config?.enabled || st.config?.nurture_enabled;
  const live = st.email_gate?.live;
  const lastRun = st.last_runs?.[0];
  return (
    <div className="bg-[#0e0e10] rounded-2xl border border-emerald-500/20 p-5 mb-8" data-testid="ops-autonomous-followup">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Bot className="w-4 h-4 text-emerald-400" />
          <span className="font-serif text-lg">Follow-up Autonom Lead-uri</span>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${active ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-stone-500/10 border-stone-500/30 text-stone-400"}`} data-testid="af-status-badge">{active ? "AUTONOMIE L2 ACTIVĂ" : "INACTIV"}</span>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${live ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-amber-500/10 border-amber-500/30 text-amber-300"}`} data-testid="af-email-gate">{live ? "EMAIL LIVE" : "EMAIL BLOCAT (DNS Resend) — lead-urile intră în coadă"}</span>
          <InspectorButton widgetId="ops.autonomous_followup" />
        </div>
        <button onClick={runNow} disabled={running} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="af-run-now">
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />} Rulează ciclul acum
        </button>
      </div>
      <div className="flex flex-wrap gap-x-8 gap-y-2 mt-3 text-xs text-stone-400">
        <div data-testid="af-pending-warm">Candidați warm 48h: <span className="text-white font-medium">{st.pending?.warm_48h ?? 0}</span></div>
        <div data-testid="af-pending-nurture">Candidați nurture 7z: <span className="text-white font-medium">{st.pending?.nurture_7d ?? 0}</span></div>
        <div data-testid="af-sent-30d">Trimise 30z: <span className="text-emerald-300 font-medium">{st.log_30d?.sent || 0}</span></div>
        <div data-testid="af-queued-30d">În coadă 30z: <span className="text-amber-300 font-medium">{st.log_30d?.queued_blocked || 0}</span></div>
        <div data-testid="af-last-run">Ultimul ciclu: <span className="text-stone-200">{lastRun ? new Date(lastRun.at).toLocaleString("ro-RO") : "—"}</span></div>
      </div>
    </div>
  );
};

export default function OperationsCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [stageFilter, setStageFilter] = useState("");
  const [winText, setWinText] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/api/admin/operations`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const updateLead = async (id, payload) => {
    setBusy(id);
    try { await axios.patch(`${API}/api/admin/operations/leads/${id}`, payload, { withCredentials: true }); await load(); }
    catch (e) { alert(e?.response?.data?.detail || "Eroare"); } finally { setBusy(null); }
  };
  const payOrder = async (orderId, method, reference) => {
    if (!window.confirm(`Confirmi înregistrarea plății manuale (${METHOD_LABELS[method]})? Comanda devine PLĂTITĂ + VERIFIED.`)) return;
    setBusy(orderId);
    try { await axios.post(`${API}/api/admin/operations/manual-payment`, { order_id: orderId, method, reference }, { withCredentials: true }); await load(); }
    catch (e) { alert(e?.response?.data?.detail || "Eroare"); } finally { setBusy(null); }
  };
  const saveWin = async () => {
    if (!winText.trim()) return;
    try { await axios.post(`${API}/api/admin/operations/win`, { text: winText }, { withCredentials: true }); setWinText(""); await load(); }
    catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
  };

  if (loading || !data) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă Operations Center...</div>;

  const c = data.coo_report || {};
  const leads = (data.leads || []).filter(l => !stageFilter || l.stage === stageFilter);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3" data-testid="ops-title">
              <ClipboardList className="w-8 h-8 text-[#d4ff3a]" /> Operations Center
            </h1>
            <p className="text-sm text-stone-400 mt-1">Condu compania dintr-un singur ecran. Nimic nu intră fără owner, nimic nu iese fără rezultat.</p>
          </div>
          <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="ops-refresh"><RefreshCcw className="w-3.5 h-3.5" /> Refresh</button>
        </div>

        {/* One Win Per Day */}
        <div className="bg-[#0e0e10] rounded-2xl border border-[#d4ff3a]/20 p-5 mb-6" data-testid="ops-one-win">
          <div className="flex items-center gap-2 mb-2"><Trophy className="w-4 h-4 text-[#d4ff3a]" /><span className="font-serif text-lg">One Win Per Day</span></div>
          <div className="text-xs text-stone-400 mb-3">
            Ieri: <span className="text-stone-200">{data.one_win?.yesterday?.text || "—"}</span> · Azi: <span className="text-stone-200">{data.one_win?.today?.text || "încă nimic"}</span>
          </div>
          <div className="flex gap-2">
            <input value={winText} onChange={(e) => setWinText(e.target.value)} placeholder="Victoria de azi (ex: primul lead calificat contactat)..." className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-[#d4ff3a]" data-testid="ops-win-input" />
            <button onClick={saveWin} className="pm-btn pm-btn-success pm-btn-sm" data-testid="ops-win-save"><CheckCircle2 className="w-3.5 h-3.5" /> Salvează</button>
          </div>
        </div>

        {/* COO Report */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6" data-testid="ops-coo-report">
          {[
            { l: "Leads noi azi", v: c.new_leads_today, icon: Users },
            { l: "Leads deschise", v: c.open_leads, icon: ClipboardList },
            { l: "Venit pending (RON)", v: Number(c.revenue_pending_ron || 0).toLocaleString("ro-RO"), icon: Banknote },
            { l: "Plăți reale primite", v: c.payments_received_real, icon: TrendingUp },
          ].map((s, i) => (
            <div key={i} className="pm-stat-card"><div className="pm-stat-icon-badge bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/20"><s.icon className="w-5 h-5" /></div><div className="font-serif text-2xl mb-1">{s.v}</div><div className="text-xs text-stone-400">{s.l}</div></div>
          ))}
        </div>
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 mb-8 flex flex-wrap gap-x-8 gap-y-2 text-sm" data-testid="ops-bottleneck">
          <div><span className="text-stone-400 text-xs uppercase tracking-wide">Bottleneck:</span> <span className="text-amber-300">{c.biggest_bottleneck}</span></div>
          <div><span className="text-stone-400 text-xs uppercase tracking-wide">Acțiunea #1:</span> <span className="text-[#d4ff3a]">{c.top_founder_action}</span></div>
        </div>

        {/* Autonomie L2 — EXECUTION ORDER 001 */}
        <AutonomousFollowupPanel />

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Pipeline */}
          <div className="lg:col-span-2 bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ops-pipeline">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
              <h2 className="font-serif text-xl">Pipeline Leads ({leads.length})</h2>
              <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5" data-testid="ops-stage-filter">
                <option value="">Toate stage-urile</option>
                {(data.stages || []).map(s => <option key={s} value={s}>{STAGE_LABELS[s] || s}</option>)}
              </select>
            </div>
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
              {leads.length === 0
                ? <p className="text-sm text-stone-500">Niciun lead {stageFilter ? "în acest stage" : "încă"}. Distribuie /scorul-casei pentru primele leads.</p>
                : leads.map(l => <LeadRow key={l.id} lead={l} stages={data.stages} onUpdate={updateLead} busy={busy} />)}
            </div>
          </div>

          <div className="space-y-6">
            {/* Waiting payment */}
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ops-waiting-payment">
              <h2 className="font-serif text-xl mb-1">Așteaptă plata ({(data.ve_orders_pending || []).length})</h2>
              <p className="text-[11px] text-stone-500 mb-4">Plăți manuale (cash/transfer/POS) active până la Stripe LIVE — marcate VERIFIED.</p>
              <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
                {(data.ve_orders_pending || []).length === 0
                  ? <p className="text-sm text-stone-500">Nicio comandă pending.</p>
                  : data.ve_orders_pending.map(o => <PendingOrderRow key={o.id} order={o} methods={data.manual_methods} onPay={payOrder} busy={busy} />)}
              </div>
            </div>

            {/* Specialist gaps — sumar rapid (detalii în Gap Engine mai jos) */}
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ops-gaps">
              <h2 className="font-serif text-xl mb-1 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Gaps specialiști</h2>
              <p className="text-[11px] text-stone-500 mb-4">Cereri fără specialist = oportunități de recrutare. Detalii + alocare mai jos.</p>
              <div className="space-y-2">
                {(data.gaps || []).length === 0
                  ? <p className="text-sm text-stone-500">Toate cererile au specialist. 🎉</p>
                  : data.gaps.map(g => (
                    <div key={g.category} className="flex items-center justify-between text-sm bg-white/[0.02] border border-white/10 rounded-xl px-3.5 py-2.5" data-testid={`ops-gap-${g.category}`}>
                      <div><span className="text-stone-200 capitalize">{g.category}</span><span className="text-[11px] text-stone-500 ml-2">{g.waiting_requests} cereri</span></div>
                      <span className="text-xs text-amber-300">{Number(g.est_lost_revenue_ron).toLocaleString("ro-RO")} RON</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* VE queues */}
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ops-ve-queues">
              <h2 className="font-serif text-xl mb-3">Imobile Verificate</h2>
              <div className="space-y-2 text-sm">
                <Link to="/admin/imobile-verificate" className="flex justify-between hover:text-[#d4ff3a] transition"><span>Cereri cumpărători noi</span><span className="text-[#d4ff3a]">{data.inquiries_new}</span></Link>
                <Link to="/admin/imobile-verificate" className="flex justify-between hover:text-[#d4ff3a] transition"><span>Cereri audit extern noi</span><span className="text-[#d4ff3a]">{data.external_requests_new}</span></Link>
              </div>
            </div>
          </div>
        </div>

        {/* Specialist Gap Engine — filtrare / alocare / export */}
        <OpsGapsPanel onChanged={load} />

        {/* Manual Payment Mode — plăți VERIFIED legate de Lead + Client + Proiect */}
        <OpsPaymentsPanel leads={data.leads || []} methods={data.manual_methods || []} onChanged={load} />
      </div>
    </div>
  );
}
