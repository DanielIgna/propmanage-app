import React, { useEffect, useState } from "react";
import axios from "axios";
import { Heart, Star, ShieldCheck, CircleCheck, Send } from "lucide-react";
import { API } from "../pages/DashShared";
import { formatApiError } from "../auth";
import { GREEN, CTA, Sheet } from "../pages/clientv2/ui";

const CAT_LABELS = {
  zugravit: "Zugrăvit", parchet: "Parchet", faianta: "Faianță / Gresie", handyman: "Handyman",
  gips_carton: "Gips-carton", hvac: "HVAC / Climatizare", electric: "Electric", plumbing: "Sanitar",
  interior_design: "Design Interior",
};
const catLabel = (c) => CAT_LABELS[c] || c || "Serviciu";

const RebookModal = ({ spec, properties, onClose, onDone }) => {
  const [form, setForm] = useState({
    property_id: spec.last_property_id && properties.some(p => p.id === spec.last_property_id)
      ? spec.last_property_id : (properties[0]?.id || ""),
    category: spec.last_category || spec.categories?.[0] || "handyman",
    title: "", description: "", budget_estimate: "",
  });
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/trusted-specialists/${spec.specialist_id}/rebook`, {
        ...form,
        budget_estimate: form.budget_estimate ? parseFloat(form.budget_estimate) : null,
      });
      setCreated(data);
      onDone?.(data);
    } catch (err) { alert(formatApiError(err)); }
    finally { setLoading(false); }
  };

  return (
    <Sheet title={created ? "Cerere trimisă" : `Re-angajează pe ${spec.name.split(" ")[0]}`} onClose={onClose} testid="rebook-modal">
      {created ? (
        <div className="text-center py-6" data-testid="rebook-success">
          <CircleCheck className="w-12 h-12 mx-auto" style={{ color: GREEN }} />
          <h3 className="mt-3 text-lg font-black text-slate-900">Trimisă direct către {spec.name}</h3>
          <p className="mt-1 text-sm text-slate-400">Nu intră la licitație — doar {spec.name.split(" ")[0]} o vede și taxa lui de lead este 0. Primești notificare când acceptă.</p>
          <div className="mt-5 max-w-[220px] mx-auto"><CTA testid="rebook-done" onClick={onClose}>Am înțeles</CTA></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <p className="text-xs text-slate-400 leading-relaxed">
            Cererea ajunge <span className="font-bold text-slate-600">doar la {spec.name}</span>, fără licitație publică. Pentru că îl re-angajezi, taxa lui de lead este 0 RON.
          </p>
          {properties.length > 1 && (
            <div>
              <label className="text-[11px] font-bold text-slate-500">Proprietatea</label>
              <select value={form.property_id} onChange={e => setForm(f => ({ ...f, property_id: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="rebook-property">
                {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="text-[11px] font-bold text-slate-500">Categoria</label>
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="rebook-category">
              {Object.entries(CAT_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-500">Ce ai nevoie?</label>
            <input required minLength={3} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder={`ex: ${catLabel(form.category)} — o cameră`}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="rebook-title" />
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-500">Detalii</label>
            <textarea required minLength={3} rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Descrie pe scurt lucrarea — specialistul cunoaște deja proprietatea."
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm resize-none" data-testid="rebook-desc" />
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-500">Buget estimat (RON, opțional)</label>
            <input type="number" min="0" value={form.budget_estimate} onChange={e => setForm(f => ({ ...f, budget_estimate: e.target.value }))}
              placeholder="ex: 500" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="rebook-budget" />
          </div>
          <CTA testid="rebook-submit" disabled={loading}>
            <Send className="w-4 h-4 inline mr-1 -mt-0.5" />{loading ? "Se trimite..." : `Trimite direct către ${spec.name.split(" ")[0]}`}
          </CTA>
        </form>
      )}
    </Sheet>
  );
};

export const TrustedSpecialists = ({ properties = [], onRebooked }) => {
  const [list, setList] = useState([]);
  const [rebookFor, setRebookFor] = useState(null);

  useEffect(() => {
    axios.get(`${API}/trusted-specialists`).then(r => setList(r.data?.specialists || [])).catch(() => {});
  }, []);

  if (list.length === 0) return null;

  return (
    <div className="px-5 pt-8 pb-4" data-testid="trusted-specialists-section">
      <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 px-1 flex items-center gap-1.5">
        <Heart className="w-3.5 h-3.5 text-rose-400" /> Specialiștii mei de încredere
      </h3>
      <p className="mt-1 px-1 text-xs text-slate-400">Re-angajezi în 1 minut — cererea merge direct la specialist, fără licitație.</p>
      <div className="mt-3 space-y-2">
        {list.map(s => (
          <div key={s.specialist_id} className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid={`trusted-card-${s.specialist_id}`}>
            <div className="flex items-center gap-3">
              <span className="w-11 h-11 rounded-full flex items-center justify-center text-white text-sm font-black shrink-0" style={{ background: GREEN }}>
                {(s.name || "S")[0].toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-black text-slate-900 truncate">{s.name}</span>
                  {s.verified && <ShieldCheck className="w-4 h-4 shrink-0" style={{ color: GREEN }} />}
                </div>
                <div className="text-[11px] text-slate-400 truncate">
                  {catLabel(s.last_category)}{s.city ? ` · ${s.city}` : ""}
                </div>
              </div>
              {s.active && (
                <button onClick={() => setRebookFor(s)} data-testid={`rebook-btn-${s.specialist_id}`}
                  className="shrink-0 px-4 py-2.5 rounded-full text-xs font-black text-white active:scale-[0.97] transition-transform"
                  style={{ background: GREEN }}>
                  Re-angajează
                </button>
              )}
            </div>
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-50 text-slate-500" data-testid={`trusted-jobs-${s.specialist_id}`}>
                {s.jobs_together} {s.jobs_together === 1 ? "lucrare împreună" : "lucrări împreună"}
              </span>
              {s.my_rating && (
                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 flex items-center gap-1">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" /> {s.my_rating} de la tine
                </span>
              )}
              {s.rebook?.show && s.rebook.pct !== null && (
                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-rose-50 text-rose-500">❤️ {s.rebook.pct}% l-ar angaja din nou</span>
              )}
              {s.last_job_at && (
                <span className="text-[10px] text-slate-400">ultima: {new Date(s.last_job_at).toLocaleDateString("ro-RO")}</span>
              )}
            </div>
          </div>
        ))}
      </div>
      {rebookFor && <RebookModal spec={rebookFor} properties={properties} onClose={() => setRebookFor(null)} onDone={onRebooked} />}
    </div>
  );
};
