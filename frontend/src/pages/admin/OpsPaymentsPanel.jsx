// Manual Payment Mode — plăți VERIFIED legate de Lead + Client + Proiect (până la Stripe LIVE)
import React, { useEffect, useState, useCallback } from "react";
import { Banknote, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
const METHOD_LABELS = { cash: "Cash", bank_transfer: "Transfer bancar", pos: "POS", payment_link: "Link de plată", manual_stripe: "Stripe manual", other: "Altă metodă" };

export const OpsPaymentsPanel = ({ leads = [], methods = [], onChanged }) => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ amount_ron: "", method: "bank_transfer", reference: "", lead_id: "", customer_name: "", customer_email: "" });

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/api/admin/operations/manual-payments`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const setLead = (id) => {
    const lead = leads.find(l => l.id === id);
    setForm(f => ({ ...f, lead_id: id, customer_name: lead?.name || f.customer_name, customer_email: lead?.email || f.customer_email }));
  };

  const submit = async () => {
    if (!form.amount_ron || Number(form.amount_ron) <= 0) { alert("Introdu o sumă validă."); return; }
    if (!form.customer_name.trim() && !form.lead_id) { alert("Numele clientului este obligatoriu (sau alege un lead)."); return; }
    if (!window.confirm(`Confirmi plata manuală de ${form.amount_ron} RON (${METHOD_LABELS[form.method]})? Va fi marcată VERIFIED.`)) return;
    setBusy(true);
    try {
      await axios.post(`${API}/api/admin/operations/manual-payments`, { ...form, amount_ron: Number(form.amount_ron) }, { withCredentials: true });
      setForm({ amount_ron: "", method: "bank_transfer", reference: "", lead_id: "", customer_name: "", customer_email: "" });
      await load();
      onChanged && onChanged();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la înregistrare"); } finally { setBusy(false); }
  };

  const payments = data?.payments || [];
  const totals = data?.totals || {};

  return (
    <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6 mt-6" data-testid="ops-payments-panel">
      <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2 className="font-serif text-xl flex items-center gap-2"><Banknote className="w-4 h-4 text-[#d4ff3a]" /> Plăți manuale (Manual Payment Mode)</h2>
          <p className="text-[11px] text-stone-500 mt-0.5">Cash · Transfer · POS · Link · Stripe manual — fiecare plată VERIFIED, legată de Lead + Client + Proiect.</p>
        </div>
        <div className="text-right">
          <div className="font-serif text-2xl text-[#d4ff3a]" data-testid="payments-total">{Number(totals.total_ron || 0).toLocaleString("ro-RO")} RON</div>
          <div className="text-[11px] text-stone-500">{totals.count || 0} plăți verificate</div>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4 mb-4" data-testid="payment-form">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          <input type="number" min="1" value={form.amount_ron} onChange={(e) => setForm(f => ({ ...f, amount_ron: e.target.value }))} placeholder="Sumă (RON) *"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-[#d4ff3a]" data-testid="payment-amount" />
          <select value={form.method} onChange={(e) => setForm(f => ({ ...f, method: e.target.value }))} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-2" data-testid="payment-method">
            {methods.map(m => <option key={m} value={m}>{METHOD_LABELS[m] || m}</option>)}
          </select>
          <select value={form.lead_id} onChange={(e) => setLead(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-2" data-testid="payment-lead">
            <option value="">Fără lead asociat</option>
            {leads.map(l => <option key={l.id} value={l.id}>{l.name || l.email || "Lead"} · {l.source}</option>)}
          </select>
          <input value={form.customer_name} onChange={(e) => setForm(f => ({ ...f, customer_name: e.target.value }))} placeholder="Nume client *"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-[#d4ff3a]" data-testid="payment-customer-name" />
          <input value={form.customer_email} onChange={(e) => setForm(f => ({ ...f, customer_email: e.target.value }))} placeholder="Email client"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-[#d4ff3a]" data-testid="payment-customer-email" />
          <input value={form.reference} onChange={(e) => setForm(f => ({ ...f, reference: e.target.value }))} placeholder="Referință (nr. tranzacție / chitanță)"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-[#d4ff3a]" data-testid="payment-reference" />
        </div>
        <button onClick={submit} disabled={busy} className="pm-btn pm-btn-success pm-btn-sm mt-3" data-testid="payment-submit">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Înregistrează plata VERIFIED
        </button>
      </div>

      <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1" data-testid="payments-list">
        {payments.length === 0
          ? <p className="text-sm text-stone-500">Nicio plată manuală înregistrată încă.</p>
          : payments.map(p => (
            <div key={p.id} className="flex items-center justify-between gap-3 text-sm bg-white/[0.02] border border-white/10 rounded-xl px-3.5 py-2.5" data-testid={`payment-row-${p.id}`}>
              <div className="min-w-0">
                <div className="text-stone-200 truncate">
                  <span className="text-[#d4ff3a] font-medium">{Number(p.amount_ron).toLocaleString("ro-RO")} RON</span>
                  <span className="text-stone-400"> · {METHOD_LABELS[p.method] || p.method}</span>
                  {p.customer_name && <span> · {p.customer_name}</span>}
                </div>
                <div className="text-[11px] text-stone-500 truncate">
                  {String(p.verified_at).slice(0, 10)}
                  {p.lead_name && <span> · Lead: {p.lead_name}</span>}
                  {p.request_title && <span> · Proiect: {p.request_title}</span>}
                  {p.reference && <span> · Ref: {p.reference}</span>}
                </div>
              </div>
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5 shrink-0">
                <ShieldCheck className="w-3 h-3" /> VERIFIED
              </span>
            </div>
          ))}
      </div>
    </div>
  );
};
