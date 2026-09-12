// FranchiseApplyPage — /devino-francizat
// Pagină publică de aplicare pentru francizare PropManage.
// Formularul intră în unified leads cu source=franchise_application.
import React, { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Building2, ArrowRight, CheckCircle2, MapPin, Users, TrendingUp,
  ShieldCheck, Sparkles, Zap, Wallet, Award, Cpu, Send, Loader2, AlertCircle,
} from "lucide-react";
import { useDynamicSEO } from "../lib/useDynamicSEO";

const API = process.env.REACT_APP_BACKEND_URL;

const INVESTMENT_OPTIONS = [
  { key: "10-25k",  label: "10.000 – 25.000 EUR",  hint: "Start-up local, oraș mic" },
  { key: "25-50k",  label: "25.000 – 50.000 EUR",  hint: "Oraș mediu, echipă de 3-5" },
  { key: "50-100k", label: "50.000 – 100.000 EUR", hint: "Oraș mare, echipă completă" },
  { key: "100k+",   label: "Peste 100.000 EUR",    hint: "Multi-oraș, master-franchise" },
];

const BENEFITS = [
  { icon: Building2, title: "Teritoriu exclusiv", desc: "Un singur francizat pe oraș. Piață protejată contractual pe 5 ani." },
  { icon: Cpu, title: "Platformă completă", desc: "Digital Twin, marketplace verificat, escrow, AI Concierge — la cheie." },
  { icon: TrendingUp, title: "Model probat", desc: "Marketplace + comisioane + abonamente. Break-even estimat la 8-14 luni." },
  { icon: Users, title: "Rețea națională", desc: "Peer-to-peer între francizați, sharing best practices, evenimente lunare." },
  { icon: ShieldCheck, title: "Suport 360°", desc: "Training la lansare, playbook operațional, suport marketing și IT continuu." },
  { icon: Award, title: "Brand recunoscut", desc: "Marketing coordonat național + campanii locale co-finanțate." },
];

const STAGES = [
  { n: "01", t: "Aplici online", d: "Completezi formularul. Prima evaluare în 48h." },
  { n: "02", t: "Interviu de calificare", d: "Video-call 60 min: viziune, resurse, plan local." },
  { n: "03", t: "Studiu de piață", d: "Analizăm împreună orașul, competiția, potențialul." },
  { n: "04", t: "Contract & training", d: "Semnare franciză, onboarding intensiv 3 săptămâni." },
  { n: "05", t: "Lansare oficială", d: "Kick-off în oraș cu suport marketing HQ." },
];

const FAQ = [
  { q: "Care este taxa de intrare și royalty?", a: "Taxă de intrare între 12.000 și 35.000 EUR (în funcție de dimensiunea orașului), plus royalty de 6% din revenue-ul lunar. Nu există taxe ascunse." },
  { q: "Pot fi francizat fără experiență în real estate?", a: "Da. Cerem însă experiență în management, vânzări sau servicii. Training-ul de 3 săptămâni acoperă specificul industriei." },
  { q: "Cât durează până la profitabilitate?", a: "Break-even mediu la 8-14 luni, în funcție de mărimea orașului și de rata de acquisition specialiști + clienți." },
  { q: "Rămân proprietar pe firma mea?", a: "Da, ești antreprenor local independent, cu contract de franciză. Beneficiezi de brand, tehnologie și suport, dar operezi propria ta afacere." },
];

export default function FranchiseApplyPage() {
  useDynamicSEO({
    title: "Devino francizat PropManage — Aplică acum",
    description: "Deschide franciza PropManage în orașul tău. Model probat, platformă completă, teritoriu exclusiv. Investiție de la 10.000 EUR.",
    canonical: "/devino-francizat",
  });

  const [form, setForm] = useState({
    name: "", email: "", phone: "", city: "", occupation: "",
    investment: "", experience: "", message: "", consent: false,
  });
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (status === "loading") return;
    setStatus("loading");
    setErrorMsg("");
    try {
      await axios.post(`${API}/api/public/franchise-application`, form);
      setStatus("success");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      const msg = err?.response?.data?.detail || "A apărut o eroare. Încearcă din nou sau scrie-ne direct.";
      setErrorMsg(msg);
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div className="min-h-screen bg-stone-950 text-white flex items-center justify-center px-6 py-24" data-testid="franchise-apply-success">
        <div className="max-w-xl text-center">
          <div className="w-20 h-20 rounded-full bg-[#d4ff3a]/15 border border-[#d4ff3a]/40 flex items-center justify-center mx-auto mb-8">
            <CheckCircle2 className="w-10 h-10 text-[#d4ff3a]" strokeWidth={1.5} />
          </div>
          <h1 className="font-serif text-5xl md:text-6xl mb-6 leading-tight" data-testid="franchise-success-title">
            Aplicația ta a fost <span className="italic text-[#d4ff3a]">primită</span>.
          </h1>
          <p className="text-lg text-stone-400 leading-relaxed mb-10">
            Echipa noastră analizează aplicația și te va contacta în maximum 48 de ore la <span className="text-white font-medium">{form.email}</span> sau <span className="text-white font-medium">{form.phone}</span>.
          </p>
          <div className="glass-strong rounded-2xl p-6 text-left mb-8 border border-white/10">
            <div className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-3">Ce urmează</div>
            <ol className="space-y-3 text-sm text-stone-300">
              <li className="flex gap-3"><span className="font-mono text-[#d4ff3a]">01.</span> Primești confirmarea pe email în câteva minute.</li>
              <li className="flex gap-3"><span className="font-mono text-[#d4ff3a]">02.</span> Un partener development te sună pentru pre-calificare.</li>
              <li className="flex gap-3"><span className="font-mono text-[#d4ff3a]">03.</span> Programăm interviu video de 60 minute.</li>
            </ol>
          </div>
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-stone-400 hover:text-white transition-colors" data-testid="franchise-back-home">
            ← Înapoi la PropManage
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-950 text-white" data-testid="franchise-apply-page">
      {/* HERO */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 dotted-bg opacity-20" />
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] rounded-full bg-[#d4ff3a] blur-[160px] opacity-10" />

        <div className="max-w-6xl mx-auto relative">
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full mb-8" data-testid="franchise-hero-badge">
            <div className="w-2 h-2 rounded-full bg-[#d4ff3a] pulse-dot" />
            <span className="text-xs tracking-wide text-stone-300">Program de francizare · Ediția 2026</span>
          </div>

          <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl leading-[0.95] tracking-tight mb-8 max-w-4xl" data-testid="franchise-hero-title">
            Devino <span className="italic gradient-text">francizat</span><br />PropManage.
          </h1>

          <p className="text-lg md:text-xl text-stone-400 max-w-2xl mb-10 leading-relaxed">
            Deschide operațiunea PropManage în orașul tău. Model probat, tehnologie la cheie, teritoriu exclusiv. Primul lot: <span className="text-white font-medium">10 orașe în România</span>.
          </p>

          <div className="flex flex-col sm:flex-row gap-4">
            <a href="#apply" className="btn-accent px-8 py-4 rounded-full font-medium inline-flex items-center gap-2 group" data-testid="franchise-cta-apply">
              Aplică acum
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="#how" className="glass px-8 py-4 rounded-full font-medium inline-flex items-center gap-2 hover:bg-white/10 transition-colors" data-testid="franchise-cta-how">
              Cum funcționează
            </a>
          </div>

          {/* Stats */}
          <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-8 pt-10 border-t border-white/5">
            {[
              { v: "10", l: "Orașe disponibile" },
              { v: "5 ani", l: "Exclusivitate teritorială" },
              { v: "8-14L", l: "Break-even mediu" },
              { v: "6%", l: "Royalty flat" },
            ].map((s, i) => (
              <div key={i} data-testid={`franchise-stat-${i}`}>
                <div className="font-serif text-4xl md:text-5xl font-medium">{s.v}</div>
                <div className="text-xs uppercase tracking-wider text-stone-500 mt-2">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* BENEFITS */}
      <section className="py-24 px-6 relative">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16 max-w-3xl">
            <div className="inline-flex items-center gap-3 mb-6">
              <span className="font-mono text-xs text-[#d4ff3a]">01</span>
              <div className="w-12 h-px bg-[#d4ff3a]" />
              <span className="text-xs uppercase tracking-[0.2em] text-stone-400">De ce PropManage</span>
            </div>
            <h2 className="font-serif text-4xl md:text-6xl tracking-tight mb-6" data-testid="franchise-benefits-title">
              Nu-ți dăm un brand. Îți dăm o <span className="italic">infrastructură</span>.
            </h2>
            <p className="text-lg text-stone-400 leading-relaxed">
              Marketplace-ul, Digital Twin, escrow-ul, AI-ul și CRM-ul — toate rulează pentru tine. Tu construiești comunitatea locală de specialiști și clienți.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {BENEFITS.map((b, i) => (
              <div key={i} className="glass-strong p-8 rounded-3xl hover:border-[#d4ff3a]/30 transition-all" data-testid={`franchise-benefit-${i}`}>
                <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 flex items-center justify-center mb-5">
                  <b.icon className="w-5 h-5 text-[#d4ff3a]" strokeWidth={1.5} />
                </div>
                <h3 className="font-serif text-xl mb-2">{b.title}</h3>
                <p className="text-sm text-stone-400 leading-relaxed">{b.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-24 px-6 relative">
        <div className="absolute inset-0 dotted-bg opacity-20" />
        <div className="max-w-6xl mx-auto relative">
          <div className="mb-16 max-w-3xl">
            <div className="inline-flex items-center gap-3 mb-6">
              <span className="font-mono text-xs text-[#d4ff3a]">02</span>
              <div className="w-12 h-px bg-[#d4ff3a]" />
              <span className="text-xs uppercase tracking-[0.2em] text-stone-400">Procesul de aplicare</span>
            </div>
            <h2 className="font-serif text-4xl md:text-6xl tracking-tight mb-6" data-testid="franchise-stages-title">
              De la aplicație la lansare, în <span className="italic">5 pași</span>.
            </h2>
          </div>

          <div className="grid md:grid-cols-5 gap-4">
            {STAGES.map((s, i) => (
              <div key={i} className="glass rounded-2xl p-6" data-testid={`franchise-stage-${i}`}>
                <div className="font-mono text-xs text-[#d4ff3a] mb-4">{s.n}</div>
                <div className="font-serif text-lg mb-2">{s.t}</div>
                <div className="text-xs text-stone-400 leading-relaxed">{s.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* APPLICATION FORM */}
      <section id="apply" className="py-24 px-6 relative">
        <div className="max-w-4xl mx-auto">
          <div className="mb-12 text-center max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-3 mb-6 justify-center">
              <span className="font-mono text-xs text-[#d4ff3a]">03</span>
              <div className="w-12 h-px bg-[#d4ff3a]" />
              <span className="text-xs uppercase tracking-[0.2em] text-stone-400">Formular de aplicare</span>
            </div>
            <h2 className="font-serif text-4xl md:text-6xl tracking-tight mb-6" data-testid="franchise-form-title">
              Aplică pentru <span className="italic">franciza ta</span>.
            </h2>
            <p className="text-stone-400">
              Toate câmpurile sunt confidențiale. Te contactăm în maximum 48 de ore.
            </p>
          </div>

          <form onSubmit={submit} className="glass-strong rounded-3xl p-8 md:p-10 space-y-6" data-testid="franchise-apply-form">
            {status === "error" && (
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm" data-testid="franchise-form-error">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-5">
              <Field label="Nume complet *" testId="franchise-field-name">
                <input required value={form.name} onChange={(e) => upd("name", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors"
                  placeholder="Andrei Popescu" data-testid="franchise-input-name" />
              </Field>
              <Field label="Email *" testId="franchise-field-email">
                <input required type="email" value={form.email} onChange={(e) => upd("email", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors"
                  placeholder="andrei@exemplu.ro" data-testid="franchise-input-email" />
              </Field>
              <Field label="Telefon *" testId="franchise-field-phone">
                <input required value={form.phone} onChange={(e) => upd("phone", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors"
                  placeholder="+40 7XX XXX XXX" data-testid="franchise-input-phone" />
              </Field>
              <Field label="Oraș de interes *" testId="franchise-field-city">
                <input required value={form.city} onChange={(e) => upd("city", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors"
                  placeholder="Cluj-Napoca" data-testid="franchise-input-city" />
              </Field>
              <div className="md:col-span-2">
                <Field label="Ocupație curentă / companie" testId="franchise-field-occupation">
                  <input value={form.occupation} onChange={(e) => upd("occupation", e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors"
                    placeholder="ex: antreprenor, manager real estate, developer" data-testid="franchise-input-occupation" />
                </Field>
              </div>
            </div>

            {/* Investment tier */}
            <div>
              <div className="text-sm font-medium text-stone-300 mb-3">Capacitate de investiție *</div>
              <div className="grid md:grid-cols-2 gap-3" data-testid="franchise-field-investment">
                {INVESTMENT_OPTIONS.map((opt) => (
                  <button key={opt.key} type="button" onClick={() => upd("investment", opt.key)}
                    className={`text-left p-4 rounded-2xl border transition-all ${form.investment === opt.key ? "bg-[#d4ff3a]/10 border-[#d4ff3a]/50" : "bg-white/[0.03] border-white/10 hover:bg-white/[0.06]"}`}
                    data-testid={`franchise-invest-${opt.key}`}>
                    <div className="flex items-center gap-2">
                      <div className={`w-4 h-4 rounded-full border-2 ${form.investment === opt.key ? "border-[#d4ff3a] bg-[#d4ff3a]" : "border-stone-500"}`} />
                      <span className="font-medium">{opt.label}</span>
                    </div>
                    <div className="text-xs text-stone-400 mt-1 ml-6">{opt.hint}</div>
                  </button>
                ))}
              </div>
            </div>

            <Field label="Experiență relevantă (management, vânzări, real estate, servicii)" testId="franchise-field-experience">
              <textarea rows={3} value={form.experience} onChange={(e) => upd("experience", e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors resize-none"
                placeholder="Ce experiență ai care te-ar ajuta să conduci o operațiune PropManage local?" data-testid="franchise-input-experience" />
            </Field>

            <Field label="De ce vrei să devii francizat PropManage?" testId="franchise-field-message">
              <textarea rows={4} value={form.message} onChange={(e) => upd("message", e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none transition-colors resize-none"
                placeholder="Motivația ta, viziunea pentru orașul tău, planurile pe 5 ani..." data-testid="franchise-input-message" />
            </Field>

            <label className="flex items-start gap-3 cursor-pointer group" data-testid="franchise-field-consent">
              <input type="checkbox" required checked={form.consent} onChange={(e) => upd("consent", e.target.checked)}
                className="mt-1 w-4 h-4 accent-[#d4ff3a]" data-testid="franchise-input-consent" />
              <span className="text-sm text-stone-400 leading-relaxed">
                Sunt de acord ca datele mele să fie procesate în scopul evaluării aplicației de francizare, conform{" "}
                <Link to="/privacy" className="text-[#d4ff3a] hover:underline">Politicii de Confidențialitate</Link>. *
              </span>
            </label>

            <button type="submit" disabled={status === "loading"}
              className="w-full btn-accent px-8 py-4 rounded-full font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group"
              data-testid="franchise-submit-btn">
              {status === "loading" ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Se trimite...</>
              ) : (
                <>Trimite aplicația <Send className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>
              )}
            </button>

            <p className="text-xs text-stone-500 text-center">
              Datele tale sunt securizate. Contact garantat în maximum 48 de ore.
            </p>
          </form>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 px-6 relative">
        <div className="max-w-4xl mx-auto">
          <div className="mb-12 text-center">
            <div className="inline-flex items-center gap-3 mb-6 justify-center">
              <span className="font-mono text-xs text-[#d4ff3a]">04</span>
              <div className="w-12 h-px bg-[#d4ff3a]" />
              <span className="text-xs uppercase tracking-[0.2em] text-stone-400">Întrebări frecvente</span>
            </div>
            <h2 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="franchise-faq-title">
              Ce vrei să știi înainte să <span className="italic">aplici</span>.
            </h2>
          </div>

          <div className="space-y-3">
            {FAQ.map((f, i) => (
              <details key={i} className="glass rounded-2xl p-6 group" data-testid={`franchise-faq-${i}`}>
                <summary className="font-serif text-lg cursor-pointer flex items-center justify-between gap-4 list-none">
                  {f.q}
                  <span className="text-[#d4ff3a] group-open:rotate-45 transition-transform text-2xl leading-none">+</span>
                </summary>
                <p className="mt-4 text-sm text-stone-400 leading-relaxed">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="py-20 px-6 relative">
        <div className="max-w-4xl mx-auto text-center">
          <Sparkles className="w-8 h-8 text-[#d4ff3a] mx-auto mb-6" strokeWidth={1.5} />
          <h2 className="font-serif text-4xl md:text-5xl tracking-tight mb-6">
            Fii primul în <span className="italic">orașul tău</span>.
          </h2>
          <p className="text-stone-400 max-w-xl mx-auto mb-8">
            Doar un francizat pe oraș. Odată alocat, teritoriul este blocat 5 ani. Aplică acum ca să nu-ți pierzi șansa.
          </p>
          <a href="#apply" className="btn-accent px-8 py-4 rounded-full font-medium inline-flex items-center gap-2 group" data-testid="franchise-footer-cta">
            Rezervă-ți orașul
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>
      </section>
    </div>
  );
}

const Field = ({ label, children, testId }) => (
  <div data-testid={testId}>
    <label className="block text-sm font-medium text-stone-300 mb-2">{label}</label>
    {children}
  </div>
);
