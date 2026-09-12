// ServiceHubLanding — pagină generică de serviciu CMS-driven (modelul Interior Intelligence).
// Folosită de /design-exterior și /arhitectura. Conținutul vine din /api/services/{slug}/content.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Sparkles, ArrowRight, Check, ChevronDown, Home, MapPin, Wrench, Layers,
} from "lucide-react";
import { API } from "./DashShared";
import { useDynamicSEO } from "../lib/useDynamicSEO";

const ax = axios.create({ baseURL: API });

const Section = ({ id, children, className = "" }) => (
  <section id={id} className={`max-w-6xl mx-auto px-5 sm:px-8 ${className}`}>{children}</section>
);

const FAQItem = ({ q, a, idx }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-stone-100">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between gap-4 py-4 text-left" data-testid={`sh-faq-${idx}`}>
        <span className="font-bold text-stone-800 text-sm">{q}</span>
        <ChevronDown className={`w-4 h-4 text-stone-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <p className="pb-4 text-sm text-stone-600 leading-relaxed">{a}</p>}
    </div>
  );
};

const LeadForm = ({ slug, content }) => {
  const [form, setForm] = useState({ name: "", email: "", phone: "", city: "", budget: "", message: "" });
  const [sent, setSent] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await ax.post(`/services/${slug}/leads`, form);
      setSent(r.data.message);
    } catch (_e) {
      setSent(null);
    } finally {
      setBusy(false);
    }
  };

  if (sent) return (
    <div className="p-8 rounded-3xl bg-emerald-50 border border-emerald-200 text-center" data-testid="sh-form-success">
      <div className="text-2xl mb-2">✓</div>
      <div className="font-black text-emerald-900">{sent}</div>
    </div>
  );
  const inputCls = "w-full px-4 py-3 rounded-xl border border-stone-200 bg-white text-sm text-stone-800 focus:border-emerald-600 focus:outline-none";
  return (
    <form onSubmit={submit} className="grid sm:grid-cols-2 gap-3" data-testid="sh-lead-form">
      <input required placeholder="Nume complet *" value={form.name} onChange={set("name")} className={inputCls} data-testid="sh-form-name" />
      <input required type="email" placeholder="Email *" value={form.email} onChange={set("email")} className={inputCls} data-testid="sh-form-email" />
      <input placeholder="Telefon" value={form.phone} onChange={set("phone")} className={inputCls} data-testid="sh-form-phone" />
      <select value={form.city} onChange={set("city")} className={inputCls} data-testid="sh-form-city">
        <option value="">Oraș / zonă</option>
        {(content.local_cities || []).map((c) => <option key={c} value={c}>{c}</option>)}
        <option value="alta">Altă localitate</option>
      </select>
      <select value={form.budget} onChange={set("budget")} className={`${inputCls} sm:col-span-2`} data-testid="sh-form-budget">
        <option value="">Buget estimat</option>
        {(content.budgets || []).map((b) => <option key={b} value={b}>{b}</option>)}
      </select>
      <textarea placeholder="Descrie proiectul (opțional)" value={form.message} onChange={set("message")} rows={3} className={`${inputCls} sm:col-span-2`} data-testid="sh-form-message" />
      <button type="submit" disabled={busy} className="sm:col-span-2 py-3.5 rounded-xl bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors disabled:opacity-50" data-testid="sh-form-submit">
        {busy ? "Se trimite..." : "Trimite cererea →"}
      </button>
    </form>
  );
};

export default function ServiceHubLanding({ slug }) {
  const [content, setContent] = useState(null);
  useDynamicSEO(`service_${slug}`, {
    title: content?.seo?.title,
    description: content?.seo?.description,
  });

  useEffect(() => {
    setContent(null);
    ax.get(`/services/${slug}/content`).then((r) => setContent(r.data)).catch(() => {});
  }, [slug]);

  useEffect(() => {
    if (!content) return;
    const ld = document.createElement("script");
    ld.type = "application/ld+json";
    ld.id = "sh-jsonld";
    ld.text = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": [
        { "@type": "ProfessionalService", "name": `${content.brand?.name} ${content.brand?.suffix}`,
          "provider": { "@type": "Organization", "name": "PropManage" },
          "areaServed": ["România", ...(content.local_cities || [])], "description": content.seo?.description },
        { "@type": "FAQPage", "mainEntity": (content.faq || []).map((f) => ({ "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a } })) },
      ],
    });
    document.head.appendChild(ld);
    let canon = document.querySelector('link[rel="canonical"]');
    if (!canon) { canon = document.createElement("link"); canon.rel = "canonical"; document.head.appendChild(canon); }
    canon.href = window.location.origin + (content.seo?.canonical || `/${slug}`);
    return () => { document.getElementById("sh-jsonld")?.remove(); };
  }, [content, slug]);

  if (!content) return <div className="min-h-screen bg-white flex items-center justify-center text-stone-400">Se încarcă…</div>;

  const brand = content.brand || {};
  const scrollToForm = () => document.getElementById("formular")?.scrollIntoView({ behavior: "smooth" });

  return (
    <div className="min-h-screen bg-white text-stone-800" data-testid={`service-hub-${slug}`} style={{ fontFamily: "inherit" }}>
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-stone-100">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2 shrink-0" data-testid="sh-nav-home">
            <Home className="w-5 h-5 text-emerald-700" />
            <span className="font-black text-stone-900 leading-none">{brand.name}<span className="block text-[10px] font-semibold text-stone-400 tracking-wide">{brand.suffix}</span></span>
          </Link>
          <button onClick={scrollToForm} className="px-5 py-2.5 rounded-full bg-emerald-700 text-white text-sm font-bold hover:bg-emerald-800 transition-colors shrink-0" data-testid="sh-nav-cta">Cere ofertă</button>
        </div>
      </header>

      {/* HERO */}
      <Section className="pt-12 sm:pt-16 pb-10">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-bold mb-5" data-testid="sh-hero-brand">
            <Sparkles className="w-3.5 h-3.5" /> {brand.name} {brand.suffix} · {brand.tagline}
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-stone-900 leading-[1.1] tracking-tight">{content.hero?.h1}</h1>
          <p className="mt-5 text-stone-600 text-base leading-relaxed max-w-2xl">{content.hero?.subtitle}</p>
          <div className="mt-6 flex flex-wrap items-center gap-1.5" data-testid="sh-journey">
            {(content.journey || []).map((j, i) => (
              <React.Fragment key={j}>
                <span className="px-2.5 py-1 rounded-full bg-stone-100 text-stone-700 text-[11px] font-bold">{j}</span>
                {i < content.journey.length - 1 && <ArrowRight className="w-3 h-3 text-emerald-600" />}
              </React.Fragment>
            ))}
          </div>
          <div className="mt-7 flex flex-wrap gap-3">
            <button onClick={scrollToForm} className="px-6 py-3.5 rounded-full bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors" data-testid="sh-cta-primary">{content.hero?.cta_primary}</button>
            <button onClick={scrollToForm} className="px-6 py-3.5 rounded-full border-2 border-stone-200 text-stone-700 font-bold hover:border-emerald-600 hover:text-emerald-800 transition-colors" data-testid="sh-cta-secondary">{content.hero?.cta_secondary}</button>
          </div>
        </div>
      </Section>

      {/* POZIȚIONARE */}
      {content.positioning && (
        <Section className="py-8">
          <div className="rounded-3xl bg-stone-50 border border-stone-100 p-6 sm:p-8 flex flex-col lg:flex-row lg:items-center gap-6" data-testid="sh-positioning">
            <div className="flex-1">
              <h2 className="text-lg font-black text-stone-900 flex items-center gap-2"><MapPin className="w-5 h-5 text-emerald-700" /> {content.positioning.title}</h2>
              <p className="mt-2 text-sm text-stone-600 leading-relaxed">{content.positioning.text}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(content.positioning.badges || []).map((b, i) => (
                <span key={i} className="px-3 py-1.5 rounded-full bg-white border border-emerald-200 text-emerald-800 text-xs font-bold">{b}</span>
              ))}
            </div>
          </div>
        </Section>
      )}

      {/* BENEFICII */}
      <Section className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-8">De ce prin PropManage</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {(content.benefits || []).map((b, i) => (
            <div key={i} className="p-6 rounded-3xl bg-stone-50 border border-stone-100 hover:border-emerald-200 transition-colors" data-testid={`sh-benefit-${i}`}>
              <div className="w-10 h-10 rounded-2xl bg-emerald-700 text-white flex items-center justify-center mb-3"><Check className="w-5 h-5" /></div>
              <h3 className="font-bold text-stone-900 mb-1">{b.title}</h3>
              <p className="text-sm text-stone-600">{b.text}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* PROCES */}
      <Section id="proces" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-10">Cum decurge procesul</h2>
        <div className="space-y-10">
          {(content.process_phases || []).map((ph, pi) => (
            <div key={pi} data-testid={`sh-phase-${pi}`}>
              <div className="flex items-baseline gap-3 mb-4">
                <span className="text-xs font-black uppercase tracking-widest text-emerald-700">Faza {pi + 1}</span>
                <h3 className="text-lg font-black text-stone-900">{ph.phase}</h3>
                <span className="hidden sm:inline text-xs text-stone-400">{ph.intro}</span>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {ph.steps.map((s) => (
                  <div key={s.n} className="p-5 rounded-3xl border border-stone-100 bg-white shadow-sm hover:border-emerald-200 transition-colors" data-testid={`sh-step-${s.n}`}>
                    <div className="text-3xl font-black text-emerald-700/20 mb-2">{String(s.n).padStart(2, "0")}</div>
                    <h4 className="font-bold text-stone-900 text-sm mb-1">{s.title}</h4>
                    <p className="text-xs text-stone-500">{s.text}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* HIGHLIGHT (dark) */}
      {content.highlight && (
        <Section className="py-14">
          <div className="rounded-[2rem] bg-stone-900 text-white p-8 sm:p-12" data-testid="sh-highlight">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 text-xs font-bold mb-5"><Layers className="w-3.5 h-3.5" /> Ecosistemul în acțiune</div>
            <h2 className="text-2xl sm:text-3xl font-black leading-tight max-w-2xl">{content.highlight.title}</h2>
            <p className="mt-4 text-stone-300 text-sm leading-relaxed max-w-2xl">{content.highlight.intro}</p>
            <div className="mt-7 flex flex-wrap gap-2">
              {(content.highlight.items || []).map((c, i) => (
                <span key={i} className="px-3.5 py-2 rounded-full bg-white/5 border border-white/10 text-stone-200 text-xs font-semibold" data-testid={`sh-highlight-item-${i}`}>{c}</span>
              ))}
            </div>
            <p className="mt-7 text-emerald-300/90 text-sm font-semibold max-w-2xl">{content.highlight.outro}</p>
          </div>
        </Section>
      )}

      {/* IMPLEMENTARE */}
      {content.implementation && (
        <Section id="implementare" className="py-14">
          <div className="rounded-[2rem] bg-emerald-50 border border-emerald-100 p-8 sm:p-12" data-testid="sh-impl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white text-emerald-800 text-xs font-bold mb-5"><Wrench className="w-3.5 h-3.5" /> De la proiect la realitate</div>
            <h2 className="text-2xl sm:text-3xl font-black text-stone-900 leading-tight max-w-2xl">{content.implementation.title}</h2>
            <p className="mt-4 text-sm text-stone-600 leading-relaxed max-w-2xl">{content.implementation.intro}</p>
            <div className="mt-7 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {(content.implementation.points || []).map((p, i) => (
                <div key={i} className="flex items-start gap-2 p-3.5 rounded-2xl bg-white border border-emerald-100">
                  <Check className="w-3.5 h-3.5 text-emerald-700 mt-0.5 shrink-0" />
                  <span className="text-xs font-semibold text-stone-700">{p}</span>
                </div>
              ))}
            </div>
            <button onClick={scrollToForm} className="mt-8 px-6 py-3.5 rounded-full bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors" data-testid="sh-impl-cta">Pornește procesul →</button>
          </div>
        </Section>
      )}

      {/* ECOSISTEM */}
      {content.ecosystem && (
        <Section id="ecosistem" className="py-14">
          <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">{content.ecosystem.title}</h2>
          <p className="text-sm text-stone-500 mb-8 max-w-2xl">{content.ecosystem.intro}</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {(content.ecosystem.links || []).map((s, i) => (
              <Link key={i} to={s.href} className="p-5 rounded-3xl border border-stone-100 hover:border-emerald-300 hover:shadow-lg transition-all group" data-testid={`sh-eco-${i}`}>
                <h3 className="font-bold text-stone-900 text-sm group-hover:text-emerald-800">{s.title} →</h3>
                <p className="text-xs text-stone-500 mt-1">{s.text}</p>
              </Link>
            ))}
          </div>
        </Section>
      )}

      {/* FORMULAR */}
      <Section id="formular" className="py-14">
        <div className="rounded-[2rem] bg-stone-50 border border-stone-100 p-6 sm:p-10">
          <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">Programează consultanța gratuită</h2>
          <p className="text-sm text-stone-500 mb-7">Completezi în 2 minute · primești răspuns în 24-48h · fără nicio obligație.</p>
          <LeadForm slug={slug} content={content} />
        </div>
      </Section>

      {/* FAQ */}
      <Section id="faq" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-6">Întrebări frecvente</h2>
        <div itemScope itemType="https://schema.org/FAQPage">
          {(content.faq || []).map((f, i) => <FAQItem key={i} q={f.q} a={f.a} idx={i} />)}
        </div>
      </Section>

      {/* ARTICOL SEO */}
      <Section className="py-14 pb-24">
        <article className="prose-sm max-w-3xl">
          {(content.seo_article || []).map((s, i) => (
            <div key={i} className="mb-8" data-testid={`sh-article-${i}`}>
              <h2 className="text-xl font-black text-stone-900 mb-3">{s.h2}</h2>
              <p className="text-sm text-stone-600 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </article>
      </Section>

      <footer className="border-t border-stone-100 py-8 text-center text-xs text-stone-400">
        {brand.name} {brand.suffix} · © {new Date().getFullYear()} PropManage · <Link to="/" className="hover:text-emerald-700">propmanage.io</Link>
      </footer>
    </div>
  );
}
