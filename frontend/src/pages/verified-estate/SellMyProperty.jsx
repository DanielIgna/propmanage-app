import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Box, Sparkles, ArrowRight, FileText, Calendar,
  CheckCircle2, CreditCard, AlertCircle, Loader2, Building2
} from "lucide-react";
import axios from "axios";
import { useDynamicSEO } from "@/lib/useDynamicSEO";
import { EcosystemFlow } from "@/components/ecosystem/EcosystemFlow";
import { ServiceDetailModal } from "@/components/ecosystem/ServiceDetailModal";

const API = process.env.REACT_APP_BACKEND_URL;

const PackageCard = ({ id, title, price, features, badge, selected, onSelect, detailsLabel, onDetails }) => (
  <div
    className={`text-left p-6 rounded-3xl border-2 transition-all w-full flex flex-col ${
      selected
        ? "border-[#d4ff3a] bg-[#d4ff3a]/5"
        : "border-white/10 bg-[#0e0e10] hover:border-white/30"
    }`}
    data-testid={`pkg-${id}`}
  >
    {badge && (
      <div className="self-start text-[10px] font-bold tracking-wider text-black bg-[#d4ff3a] px-2.5 py-1 rounded-full mb-3">
        {badge}
      </div>
    )}
    <h3 className="font-serif text-2xl mb-1">{title}</h3>
    <div className="font-serif text-3xl mb-4 text-[#d4ff3a]">
      {Number(price).toLocaleString("ro-RO")} <span className="text-sm text-stone-400">RON</span>
    </div>
    <ul className="space-y-2 mb-5">
      {features.map((f, i) => (
        <li key={i} className="text-sm text-stone-300 flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#d4ff3a] mt-0.5 shrink-0" />
          {f}
        </li>
      ))}
    </ul>
    <div className="mt-auto space-y-2">
      <button
        type="button"
        onClick={() => onSelect(id)}
        className={`w-full py-2.5 rounded-full text-sm font-bold transition-colors ${
          selected ? "bg-[#d4ff3a] text-black" : "bg-white/10 text-white hover:bg-white/20"
        }`}
        data-testid={`pkg-select-${id}`}
      >
        {selected ? "✓ Pachet selectat" : "Alege pachetul"}
      </button>
      {onDetails && (
        <button
          type="button"
          onClick={onDetails}
          className="w-full py-2.5 rounded-full text-sm font-bold border border-white/15 text-stone-300 hover:border-[#d4ff3a]/60 hover:text-white transition-colors"
          data-testid={`pkg-details-${id}`}
        >
          {detailsLabel}
        </button>
      )}
    </div>
  </div>
);

export const SellMyProperty = () => {
  useDynamicSEO("sell", { title: "Vinde-ți imobilul · PropManage" });
  const [pricing, setPricing] = useState(null);
  const [step, setStep] = useState(1);
  const [selectedPackage, setSelectedPackage] = useState("bundle");
  const [form, setForm] = useState({
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    property_address: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);
  const [detailKind, setDetailKind] = useState(null);

  useEffect(() => {
    axios.get(`${API}/api/verified-estate/pricing`).then(r => setPricing(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    // detect ?paid=1 redirect from Stripe
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("session_id");
    if (params.get("paid") === "1" && sid) {
      setStep(4);
      axios.get(`${API}/api/verified-estate/checkout/status/${sid}`)
        .then(r => setPaymentResult(r.data))
        .catch(() => setPaymentResult({ status: "unknown" }));
    }
  }, []);

  const submitCheckout = async () => {
    if (!form.contact_name || !form.contact_email || !form.property_address) {
      alert("Te rog completează numele, emailul și adresa proprietății.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/api/verified-estate/checkout`, {
        package: selectedPackage,
        ...form,
      });
      if (res.data?.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (err) {
      alert(err?.response?.data?.detail || "Eroare la procesare.");
      setSubmitting(false);
    }
  };

  if (!pricing) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <section className="pt-28 pb-12 px-6 relative overflow-hidden">
        <div className="absolute inset-0 dotted-bg opacity-30" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full bg-[#d4ff3a] blur-[150px] opacity-10" />
        <div className="max-w-5xl mx-auto relative">
          <Link to="/imobile-verificate" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-6">
            ← Înapoi la Imobile Verificate
          </Link>
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full mb-6">
            <ShieldCheck className="w-3.5 h-3.5 text-[#d4ff3a]" />
            <span className="text-xs tracking-wide text-stone-300">Pentru proprietari · Comision {pricing.commission_pct}%</span>
          </div>
          <h1 className="font-serif text-4xl md:text-6xl tracking-tight leading-[0.95] mb-6" data-testid="sell-hero-title">
            Vinde-ți imobilul cu <span className="italic gradient-text">credibilitate</span>.
          </h1>
          <p className="text-base md:text-lg text-stone-400 max-w-2xl mb-8">
            Te ajutăm să vinzi mai rapid și la un preț corect. Auditul tehnic + Digital Twin cresc încrederea cumpărătorilor și valoarea percepută a imobilului.
          </p>

          {/* Stepper */}
          <div className="flex items-center gap-2 mb-8 text-xs">
            {[
              { n: 1, l: "Alege pachet" },
              { n: 2, l: "Date contact" },
              { n: 3, l: "Plată" },
              { n: 4, l: "Confirmare" },
            ].map((s, i, arr) => (
              <React.Fragment key={s.n}>
                <div className={`flex items-center gap-2 ${step >= s.n ? "text-[#d4ff3a]" : "text-stone-500"}`} data-testid={`step-${s.n}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold ${step >= s.n ? "bg-[#d4ff3a] text-black" : "bg-white/10"}`}>
                    {step > s.n ? <CheckCircle2 className="w-4 h-4" /> : s.n}
                  </div>
                  <span className="hidden md:inline">{s.l}</span>
                </div>
                {i < arr.length - 1 && <div className={`h-px flex-1 ${step > s.n ? "bg-[#d4ff3a]" : "bg-white/10"}`} />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 pb-24">
        <div className="max-w-5xl mx-auto">
          {step === 1 && (
            <div data-testid="step-1-content">
              <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 mb-8" data-testid="sell-ecosystem-flow">
                <EcosystemFlow dark activeKey="audit" />
              </div>
              <h2 className="font-serif text-2xl md:text-3xl mb-6">1. Alege pachetul potrivit</h2>
              <div className="grid md:grid-cols-3 gap-4 mb-8">
                <PackageCard
                  id="audit"
                  title="Doar Audit"
                  price={pricing.audit_ron}
                  features={["Inspecție completă imobil", "Raport tehnic PDF", "Recomandări personalizate", "Estimare cost reparații"]}
                  selected={selectedPackage === "audit"}
                  onSelect={setSelectedPackage}
                  detailsLabel="Află tot ce include Auditul"
                  onDetails={() => setDetailKind("audit")}
                />
                <PackageCard
                  id="bundle"
                  title="Audit + Digital Twin"
                  price={pricing.bundle_ron}
                  badge="PROCESUL COMPLET · RECOMANDAT"
                  features={["Auditul descoperă — diagnoza completă", "Digital Twin memorează — copia digitală vie", "Un singur proces, nu două produse", "Eligibil pentru listare publică"]}
                  selected={selectedPackage === "bundle"}
                  onSelect={setSelectedPackage}
                  detailsLabel="Vezi toate cele 17 etape"
                  onDetails={() => setDetailKind("process")}
                />
                <PackageCard
                  id="twin"
                  title="Doar Digital Twin"
                  price={pricing.twin_ron}
                  features={["Pentru imobile cu audit deja făcut", "Modelare 3D + mapare instalații", "Vizualizare in browser", "Embed pe orice site"]}
                  selected={selectedPackage === "twin"}
                  onSelect={setSelectedPackage}
                  detailsLabel="Vezi tot ce conține"
                  onDetails={() => setDetailKind("twin")}
                />
              </div>
              <div className="bg-[#d4ff3a]/8 border border-[#d4ff3a]/30 rounded-2xl p-5 flex items-start gap-3 mb-8" data-testid="commission-info">
                <Sparkles className="w-5 h-5 text-[#d4ff3a] shrink-0 mt-0.5" />
                <div className="text-sm">
                  <strong className="text-[#d4ff3a]">Comision avantajos {pricing.commission_pct}%</strong> la finalizarea vânzării (vs. 5–6% standard).
                  <span className="block text-stone-300 mt-1">{pricing.notes}</span>
                </div>
              </div>
              <button onClick={() => setStep(2)} className="pm-btn pm-btn-primary pm-btn-lg" data-testid="step-1-next">
                Continuă <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {step === 2 && (
            <div data-testid="step-2-content">
              <h2 className="font-serif text-2xl md:text-3xl mb-6">2. Date de contact și proprietate</h2>
              <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 max-w-2xl space-y-3">
                <div>
                  <label className="text-xs text-stone-400 uppercase tracking-wider">Nume complet *</label>
                  <input value={form.contact_name} onChange={e => setForm({ ...form, contact_name: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="sell-name" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-stone-400 uppercase tracking-wider">Email *</label>
                    <input type="email" value={form.contact_email} onChange={e => setForm({ ...form, contact_email: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="sell-email" />
                  </div>
                  <div>
                    <label className="text-xs text-stone-400 uppercase tracking-wider">Telefon</label>
                    <input value={form.contact_phone} onChange={e => setForm({ ...form, contact_phone: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="sell-phone" />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-stone-400 uppercase tracking-wider">Adresă proprietate *</label>
                  <input value={form.property_address} onChange={e => setForm({ ...form, property_address: e.target.value })} placeholder="Ex: Bd. Aviatorilor 15, București" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="sell-address" />
                </div>
                <div>
                  <label className="text-xs text-stone-400 uppercase tracking-wider">Notițe (opțional)</label>
                  <textarea rows={3} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Ex: apartament 3 camere, vreau evaluare urgentă" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm resize-none" data-testid="sell-notes" />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(1)} className="pm-btn pm-btn-secondary" data-testid="step-2-back">← Înapoi</button>
                <button onClick={() => setStep(3)} className="pm-btn pm-btn-primary pm-btn-lg" data-testid="step-2-next">
                  Continuă la plată <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div data-testid="step-3-content">
              <h2 className="font-serif text-2xl md:text-3xl mb-6">3. Confirmare și plată</h2>
              <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 max-w-2xl" data-testid="checkout-summary">
                <div className="text-xs text-stone-400 uppercase tracking-wider mb-3">Rezumat comandă</div>
                <div className="flex items-center justify-between pb-4 border-b border-white/5">
                  <div>
                    <div className="font-medium">
                      {selectedPackage === "audit" ? "Audit complet imobil"
                        : selectedPackage === "twin" ? "Digital Twin creation"
                        : "Bundle: Audit + Digital Twin"}
                    </div>
                    <div className="text-xs text-stone-400 mt-1">Pentru: {form.property_address}</div>
                  </div>
                  <div className="font-serif text-3xl">
                    {(selectedPackage === "audit" ? pricing.audit_ron
                      : selectedPackage === "twin" ? pricing.twin_ron
                      : pricing.bundle_ron).toLocaleString("ro-RO")} <span className="text-sm text-stone-400">RON</span>
                  </div>
                </div>
                <div className="flex items-start gap-3 mt-5 p-3 bg-[#d4ff3a]/8 rounded-xl">
                  <Sparkles className="w-4 h-4 text-[#d4ff3a] shrink-0 mt-0.5" />
                  <div className="text-xs text-stone-300">
                    La finalizarea vânzării, costul Digital Twin se scade din comisionul de {pricing.commission_pct}% → în practică, Twin-ul devine GRATUIT.
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 mt-6">
                  <button onClick={() => setStep(2)} className="pm-btn pm-btn-secondary" data-testid="step-3-back">← Înapoi</button>
                  <button onClick={submitCheckout} disabled={submitting} className="pm-btn pm-btn-primary pm-btn-lg flex-1" data-testid="step-3-pay">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                    {submitting ? "Se procesează..." : "Plătește cu Stripe"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div data-testid="step-4-content">
              {paymentResult?.status === "paid" ? (
                <div className="bg-[#0e0e10] border border-[#d4ff3a]/40 rounded-3xl p-10 max-w-2xl text-center">
                  <CheckCircle2 className="w-16 h-16 text-[#d4ff3a] mx-auto mb-4" />
                  <h2 className="font-serif text-3xl mb-2">Plată reușită! 🎉</h2>
                  <p className="text-stone-300 mb-6">
                    Comandă: <span className="font-mono text-xs">{paymentResult.session_id}</span><br />
                    Suma: <strong>{Number(paymentResult.amount_ron).toLocaleString("ro-RO")} RON</strong>
                    {paymentResult.demo_mode && (
                      <span className="block mt-2 text-xs text-amber-400">⚠️ Mod DEMO — fără tranzacție reală.</span>
                    )}
                  </p>
                  <p className="text-sm text-stone-400 mb-6">
                    Echipa noastră te va contacta în maxim 24 de ore pentru a programa auditul.
                  </p>
                  <Link to="/imobile-verificate" className="pm-btn pm-btn-primary" data-testid="step-4-back-home">
                    Înapoi la Imobile Verificate
                  </Link>
                </div>
              ) : (
                <div className="bg-[#0e0e10] border border-amber-500/40 rounded-3xl p-10 max-w-2xl text-center">
                  <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
                  <h2 className="font-serif text-3xl mb-2">Verificare plată...</h2>
                  <p className="text-stone-400">Așteptăm confirmarea.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {detailKind && (
        <ServiceDetailModal
          kind={detailKind}
          dark
          onClose={() => setDetailKind(null)}
          primaryCta={{
            label: detailKind === "audit" ? "Solicită Audit" : detailKind === "twin" ? "Solicită Digital Twin" : "Începe procesul complet",
            onClick: () => {
              setSelectedPackage(detailKind === "process" ? "bundle" : detailKind === "twin" ? "twin" : "audit");
              setStep(1);
            },
          }}
        />
      )}
    </div>
  );
};

export default SellMyProperty;
