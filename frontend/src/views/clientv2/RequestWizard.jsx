import React, { useState, useEffect } from "react";
import axios from "axios";
import { ArrowLeft, PaintRoller, Building, Briefcase, Wrench, Zap, Wind, Palette, Hammer, PartyPopper } from "lucide-react";
import { API } from "../DashShared";
import { formatApiError } from "../../auth";
import { GREEN, GREEN_SOFT, CTA, AmountInput } from "./ui";

const CATS = [
  ["zugravit", "Zugrăvit", PaintRoller], ["parchet", "Parchet", Building], ["faianta", "Faianță / Gresie", Building],
  ["handyman", "Handyman", Briefcase], ["gips_carton", "Gips-carton", Hammer], ["hvac", "HVAC / Climatizare", Wind],
  ["electric", "Electric", Zap], ["plumbing", "Sanitar", Wrench], ["interior_design", "Design Interior", Palette],
];

// Wizard „Solicită" — o întrebare pe ecran (model Client Junior), POST real la /requests
export const RequestWizard = ({ property, onClose, onCreated }) => {
  const [step, setStep] = useState(0);
  // budget_estimate is a string during editing (avoids cursor jump / "0" prefix); parsed at submit.
  const [form, setForm] = useState({ category: "", title: "", description: "", priority: "normal", budget_estimate: "200", subcategory: "", taxonomy_node_id: null });
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  // GI-2 Intent Score: început → (finalizat | abandonat)
  useEffect(() => {
    let created = false;
    window.__pmWizardCreated = () => { created = true; };
    import("../../lib/analytics").then(({ trackIntent }) => trackIntent("request_started")).catch(() => {});
    return () => {
      if (!created) import("../../lib/analytics").then(({ trackIntent }) => trackIntent("request_abandoned")).catch(() => {});
      delete window.__pmWizardCreated;
    };
  }, []);
  // CIP-B: hint preț orientativ pentru categoria selectată
  const [priceHint, setPriceHint] = useState(null);
  useEffect(() => {
    if (!form.category) { setPriceHint(null); return; }
    axios.get(`${API}/construction/prices/public`, { params: { category: form.category } })
      .then(r => {
        const rows = (r.data?.items || []).filter(x => x.experience_level === "mid");
        if (!rows.length) { setPriceHint(null); return; }
        const byUnit = {};
        rows.forEach(x => { (byUnit[x.unit] = byUnit[x.unit] || []).push(x); });
        const [unit, list] = Object.entries(byUnit).sort((a, b) => b[1].length - a[1].length)[0];
        const min = Math.min(...list.map(x => x.price_min));
        const med = Math.round(list.reduce((s, x) => s + x.price_med, 0) / list.length);
        setPriceHint(`${min.toLocaleString("ro-RO")}–${med.toLocaleString("ro-RO")} RON/${unit}`);
      })
      .catch(() => setPriceHint(null));
  }, [form.category]);
  // CIP-A: nomenclator ierarhic public (doar noduri vizibile) → chips subcategorii
  const [taxonomy, setTaxonomy] = useState({});
  useEffect(() => {
    axios.get(`${API}/construction/taxonomy/public`)
      .then(r => {
        const map = {};
        (r.data?.tree || []).forEach(root => { map[root.legacy_category] = root.children || []; });
        setTaxonomy(map);
      })
      .catch(() => setTaxonomy({}));
  }, []);

  const submit = async () => {
    setLoading(true);
    try {
      const payload = { ...form, budget_estimate: parseFloat(form.budget_estimate) || 0, property_id: property.id, photos: [] };
      const { data } = await axios.post(`${API}/requests`, payload);
      if (window.__pmWizardCreated) window.__pmWizardCreated();
      // Funnel comercial (etapa 4): cerere creată real în db.requests (+ semnalul existent offer_requested)
      import("../../lib/analytics").then(({ trackIntent, trackConversion }) => { trackIntent("request_created"); trackIntent("offer_requested"); trackConversion("first_request"); }).catch(() => {});
      onCreated(data);
      setDone(true);
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col" style={{ background: GREEN_SOFT }} data-testid="v2-wizard-done">
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <span className="w-20 h-20 rounded-full flex items-center justify-center mb-5" style={{ background: "#d4ff3a" }}>
            <PartyPopper className="w-9 h-9 text-black" />
          </span>
          <h1 className="text-2xl font-black text-slate-900">Am primit cererea ta!</h1>
          <p className="mt-2 text-sm text-slate-600 max-w-xs">Specialiștii verificați vor trimite oferte. Te anunțăm imediat ce apar.</p>
        </div>
        <div className="px-5 pb-8 max-w-md mx-auto w-full">
          <CTA testid="v2-wizard-go-jobs" onClick={() => onClose("jobs")}>Mergi la lucrările mele</CTA>
        </div>
      </div>
    );
  }

  const steps = [
    {
      q: "Ce serviciu ai nevoie?",
      valid: !!form.category,
      body: (
        <div>
          <div className="grid grid-cols-2 gap-2.5">
            {CATS.map(([id, label, Icon]) => (
              <button key={id} onClick={() => setForm(f => ({ ...f, category: id, subcategory: "", taxonomy_node_id: null }))} data-testid={`v2-wiz-cat-${id}`}
                className={`rounded-2xl border-2 p-3.5 text-left transition-colors ${form.category === id ? "border-[#34C759] bg-[#34C759]/5" : "border-slate-200 bg-white"}`}>
                <Icon className="w-5 h-5" style={{ color: GREEN }} />
                <div className="mt-1.5 text-xs font-bold text-slate-900">{label}</div>
              </button>
            ))}
          </div>
          {form.category && (taxonomy[form.category] || []).length > 0 && (
            <div className="mt-5 cv2-fade" data-testid="v2-wiz-subcats">
              <div className="text-xs font-bold text-slate-500">Detaliază (opțional)</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(taxonomy[form.category] || []).map(sub => (
                  <button key={sub.id} data-testid={`v2-wiz-subcat-${sub.id}`}
                    onClick={() => setForm(f => f.taxonomy_node_id === sub.id
                      ? { ...f, subcategory: "", taxonomy_node_id: null }
                      : { ...f, subcategory: sub.name, taxonomy_node_id: sub.id })}
                    className={`px-3 py-2 rounded-full border-2 text-xs font-semibold transition-colors ${form.taxonomy_node_id === sub.id ? "border-[#34C759] bg-[#34C759]/10 text-slate-900" : "border-slate-200 bg-white text-slate-600"}`}>
                    {sub.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ),
    },
    {
      q: "Descrie pe scurt lucrarea",
      valid: form.title.trim().length >= 3 && form.description.trim().length >= 3,
      body: (
        <div className="space-y-3">
          <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Titlu (ex: Zugrăvit living)"
            className="w-full px-4 py-3.5 rounded-2xl border-2 border-slate-200 text-sm outline-none focus:border-[#34C759]" data-testid="v2-wiz-title" />
          <textarea rows={4} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Detalii: suprafață, culori, termen…"
            className="w-full px-4 py-3.5 rounded-2xl border-2 border-slate-200 text-sm outline-none focus:border-[#34C759]" data-testid="v2-wiz-desc" />
        </div>
      ),
    },
    {
      q: "Cât de urgentă e lucrarea?",
      valid: true,
      body: (
        <div className="space-y-3">
          {[["normal", "Program normal", "specialiștii răspund în 24-48h"], ["urgent", "🔥 Urgent", "apare primul în lista specialiștilor"]].map(([v, l, s]) => (
            <button key={v} onClick={() => setForm(f => ({ ...f, priority: v }))} data-testid={`v2-wiz-prio-${v}`}
              className={`w-full rounded-2xl border-2 p-4 text-left ${form.priority === v ? "border-[#34C759] bg-[#34C759]/5" : "border-slate-200 bg-white"}`}>
              <div className="text-sm font-black text-slate-900">{l}</div>
              <div className="text-[11px] text-slate-400">{s}</div>
            </button>
          ))}
          <label className="block text-xs font-bold text-slate-500 pt-1">Buget estimat (RON)
            <AmountInput value={form.budget_estimate}
              onChange={(raw) => setForm(f => ({ ...f, budget_estimate: raw }))}
              className="mt-1.5 w-full px-4 py-3.5 rounded-2xl border-2 border-slate-200 text-sm font-normal outline-none focus:border-[#34C759]" data-testid="v2-wiz-budget" />
          </label>
          {priceHint && (
            <div className="text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2" data-testid="v2-wiz-price-hint">
              💡 Preț orientativ piață pentru această categorie: <span className="font-bold text-slate-700">{priceHint}</span>
              <span className="text-slate-400"> (date preliminare)</span>
            </div>
          )}
        </div>
      ),
    },
  ];
  const s = steps[step];

  return (
    <div className="fixed inset-0 z-50 bg-[#FAFBFA] flex flex-col" data-testid="v2-wizard">
      <div className="flex items-center gap-3 px-4 py-3.5 bg-white border-b border-slate-100">
        <button onClick={() => (step === 0 ? onClose() : setStep(step - 1))} data-testid="v2-wiz-back"><ArrowLeft className="w-5 h-5 text-slate-700" /></button>
        <span className="flex-1 text-center text-sm font-bold text-slate-900">Solicitare nouă · {property?.name}</span>
        <span className="w-5" />
      </div>
      <div className="h-1.5 bg-slate-100"><div className="h-full rounded-r-full transition-all" style={{ width: `${((step + 1) / (steps.length + 1)) * 100}%`, background: GREEN }} /></div>
      <div className="flex-1 overflow-y-auto px-5 pt-6 pb-28 max-w-md mx-auto w-full">
        <div key={step} className="cv2-fade">
          <div className="text-[10px] font-black uppercase tracking-wider" style={{ color: GREEN }}>Pasul {step + 1} din {steps.length}</div>
          <h2 className="mt-1 text-2xl font-black text-slate-900 leading-snug">{s.q}</h2>
          <div className="mt-5">{s.body}</div>
        </div>
      </div>
      <div className="fixed bottom-0 left-0 right-0 px-5 pb-6 pt-3 bg-gradient-to-t from-white via-white to-transparent">
        <div className="max-w-md mx-auto">
          <CTA disabled={!s.valid || loading} testid="v2-wiz-continue"
            onClick={() => (step < steps.length - 1 ? setStep(step + 1) : submit())}>
            {loading ? "Se trimite…" : step < steps.length - 1 ? "Continuă" : "Trimite cererea"}
          </CTA>
        </div>
      </div>
    </div>
  );
};
