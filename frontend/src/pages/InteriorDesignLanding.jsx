// InteriorDesignLanding — /design-interior · serviciu independent, acces liber.
// Identitate vizuală proprie: minimalist premium, alb + gri deschis + lemn natur + accente verzi.
import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Sofa, Sparkles, ArrowRight, Check, Star, ChevronDown, MessageCircle,
  Send, Ruler, Palette, Wallet, Home, X, Scan, ClipboardCheck, Network,
  ShieldCheck, MapPin, Layers, Wrench,
} from "lucide-react";
import { API } from "./DashShared";
import { useDynamicSEO } from "../lib/useDynamicSEO";
import { trackLeadFormConversion } from "../lib/analytics";
import { EcosystemFlow } from "../components/ecosystem/EcosystemFlow";
import { ServiceDetailModal } from "../components/ecosystem/ServiceDetailModal";
import { NextStep } from "../components/ecosystem/NextStep";

const ax = axios.create({ baseURL: API });

const Section = ({ id, children, className = "" }) => (
  <section id={id} className={`max-w-6xl mx-auto px-5 sm:px-8 ${className}`}>{children}</section>
);

const FAQItem = ({ q, a, idx }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-stone-200" itemScope itemProp="mainEntity" itemType="https://schema.org/Question">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between gap-4 py-4 text-left" data-testid={`id-faq-${idx}`}>
        <span className="font-semibold text-stone-800" itemProp="name">{q}</span>
        <ChevronDown className={`w-4 h-4 text-emerald-700 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="pb-4 text-sm text-stone-600 leading-relaxed" itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
          <span itemProp="text">{a}</span>
        </div>
      )}
    </div>
  );
};

const AssistantWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "assistant", text: "Bună! Sunt asistentul de design interior. Întreabă-mă despre stiluri, bugete, culori, iluminat sau amenajarea oricărei camere. 🛋" }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await ax.post("/interior-design/assistant", { question: q, session_id: sessionId });
      setSessionId(r.data.session_id);
      setMessages((m) => [...m, { role: "assistant", text: r.data.answer }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "A apărut o eroare — te rog reîncearcă." }]);
    }
    setBusy(false);
  };

  return (
    <>
      <button onClick={() => setOpen(!open)} className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full bg-emerald-700 text-white shadow-xl flex items-center justify-center hover:bg-emerald-800 transition-colors" data-testid="id-assistant-fab" aria-label="Asistent AI design interior">
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>
      {open && (
        <div className="fixed bottom-24 right-5 z-50 w-[92vw] max-w-sm rounded-2xl bg-white shadow-2xl border border-stone-200 flex flex-col overflow-hidden" data-testid="id-assistant-panel">
          <div className="px-4 py-3 bg-emerald-700 text-white text-sm font-bold flex items-center gap-2"><Sparkles className="w-4 h-4" /> Asistent Design Interior</div>
          <div className="flex-1 max-h-80 overflow-y-auto p-3 space-y-2 bg-stone-50">
            {messages.map((m, i) => (
              <div key={i} className={`text-sm p-2.5 rounded-xl max-w-[85%] ${m.role === "user" ? "ml-auto bg-emerald-700 text-white" : "bg-white border border-stone-200 text-stone-700"}`} data-testid={`id-assistant-msg-${i}`}>{m.text}</div>
            ))}
            {busy && <div className="text-xs text-stone-400 p-2">Asistentul scrie…</div>}
            <div ref={endRef} />
          </div>
          <div className="p-2 border-t border-stone-200 flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="ex: ce buget pentru un living de 25mp?" className="flex-1 px-3 py-2 rounded-xl border border-stone-200 text-sm" data-testid="id-assistant-input" />
            <button onClick={send} disabled={busy} className="w-10 h-10 rounded-xl bg-emerald-700 text-white flex items-center justify-center disabled:opacity-40" data-testid="id-assistant-send"><Send className="w-4 h-4" /></button>
          </div>
        </div>
      )}
    </>
  );
};

const LeadForm = ({ content }) => {
  const [form, setForm] = useState({ name: "", email: "", phone: "", style: "", budget: "", surface_mp: "", rooms: "", city: "", message: "", consult_date: "", lead_type: "proiect" });
  const [sent, setSent] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await ax.post("/interior-design/leads", { ...form, surface_mp: form.surface_mp ? Number(form.surface_mp) : null });
      setSent(r.data.message);
      trackLeadFormConversion(); // Google Ads lead-form conversion (doar pe succes)
    } catch (err) {
      setSent("A apărut o eroare — verifică emailul și reîncearcă.");
    }
    setBusy(false);
  };

  if (sent) {
    return (
      <div className="p-8 rounded-3xl bg-emerald-50 border border-emerald-200 text-center" data-testid="id-form-success">
        <Check className="w-10 h-10 text-emerald-700 mx-auto mb-2" />
        <p className="font-bold text-emerald-900">{sent}</p>
      </div>
    );
  }
  const inputCls = "w-full px-4 py-3 rounded-xl border border-stone-200 bg-white text-sm text-stone-800 focus:border-emerald-600 focus:outline-none";
  return (
    <form onSubmit={submit} className="grid sm:grid-cols-2 gap-3" data-testid="id-lead-form">
      <div className="sm:col-span-2 flex gap-2 flex-wrap">
        {[["proiect", "Solicită proiect"], ["oferta", "Cere ofertă"], ["consultanta", "Consultanță designer"]].map(([v, l]) => (
          <button type="button" key={v} onClick={() => setForm((f) => ({ ...f, lead_type: v }))}
            className={`px-4 py-2 rounded-full text-sm font-bold transition-colors ${form.lead_type === v ? "bg-emerald-700 text-white" : "bg-stone-100 text-stone-600 hover:bg-stone-200"}`} data-testid={`id-type-${v}`}>{l}</button>
        ))}
      </div>
      <input required placeholder="Nume complet *" value={form.name} onChange={set("name")} className={inputCls} data-testid="id-form-name" />
      <input required type="email" placeholder="Email *" value={form.email} onChange={set("email")} className={inputCls} data-testid="id-form-email" />
      <input placeholder="Telefon" value={form.phone} onChange={set("phone")} className={inputCls} data-testid="id-form-phone" />
      <select value={form.city} onChange={set("city")} className={inputCls} data-testid="id-form-city">
        <option value="">Oraș…</option>
        {(content.local_cities || []).map((c) => <option key={c} value={c}>{c}</option>)}
        <option value="alt">Alt oraș / remote</option>
      </select>
      <select value={form.style} onChange={set("style")} className={inputCls} data-testid="id-form-style">
        <option value="">Stil dorit…</option>
        {(content.styles || []).map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
      <select value={form.budget} onChange={set("budget")} className={inputCls} data-testid="id-form-budget">
        <option value="">Buget estimat…</option>
        {(content.budgets || []).map((b) => <option key={b} value={b}>{b}</option>)}
      </select>
      <input type="number" min="10" placeholder="Suprafață (mp)" value={form.surface_mp} onChange={set("surface_mp")} className={inputCls} data-testid="id-form-surface" />
      <input placeholder="Camere de amenajat (ex: living + bucătărie)" value={form.rooms} onChange={set("rooms")} className={inputCls} data-testid="id-form-rooms" />
      {form.lead_type === "consultanta" && (
        <input type="date" value={form.consult_date} onChange={set("consult_date")} className={inputCls} data-testid="id-form-date" title="Data dorită pentru consultanță" />
      )}
      <textarea placeholder="Descrie proiectul (opțional) — poți menționa și linkuri către poze/plan" value={form.message} onChange={set("message")} rows={3} className={`${inputCls} sm:col-span-2`} data-testid="id-form-message" />
      <button type="submit" disabled={busy} className="sm:col-span-2 py-3.5 rounded-xl bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2" data-testid="id-form-submit">
        {busy ? "Se trimite…" : <>Trimite cererea — e gratuit <ArrowRight className="w-4 h-4" /></>}
      </button>
      <p className="sm:col-span-2 text-[11px] text-stone-400 text-center">Fără abonament, fără obligații. Primești oferte în 24-48h.</p>
    </form>
  );
};

const ANCHORS = [
  { id: "proces", label: "Proces" },
  { id: "digital-twin", label: "Digital Twin" },
  { id: "audit", label: "Audit" },
  { id: "implementare", label: "Implementare" },
  { id: "stiluri", label: "Stiluri" },
  { id: "ecosistem", label: "Ecosistem" },
  { id: "faq", label: "FAQ" },
];

const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

export default function InteriorDesignLanding() {
  const [content, setContent] = useState(null);
  const [detailKind, setDetailKind] = useState(null);
  useDynamicSEO("interior_design", {
    title: content?.seo?.title || "Design Interior & Arhitectură de Interior | Amenajări Interioare la Cheie — Interior Intelligence by PropManage",
    description: content?.seo?.description || "Design interior, arhitectură de interior, design interior și implementare, amenajări interioare la cheie și randări 3D fotorealiste cu specialiști verificați.",
  });

  useEffect(() => {
    ax.get("/interior-design/content").then((r) => setContent(r.data)).catch(() => {});
  }, []);

  // URL hash ↔ modal state sync. Browser Back/Forward restaurează corect modal-ul.
  useEffect(() => {
    const parseHash = () => {
      const m = (window.location.hash || "").match(/^#detail-(audit|twin|process)$/);
      return m ? m[1] : null;
    };
    setDetailKind(parseHash());
    const onHash = () => setDetailKind(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const openDetail = (kind) => {
    if (window.location.hash === `#detail-${kind}`) { setDetailKind(kind); return; }
    window.history.pushState(null, "", `${window.location.pathname}#detail-${kind}`);
    setDetailKind(kind);
  };
  const closeDetail = () => {
    if ((window.location.hash || "").startsWith("#detail-")) {
      window.history.back(); // triggers hashchange → setDetailKind(null)
    } else {
      setDetailKind(null);
    }
  };

  useEffect(() => {
    if (!content || !window.location.hash) return;
    const el = document.getElementById(window.location.hash.slice(1));
    if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth" }), 150);
  }, [content]);

  useEffect(() => {
    if (!content) return;
    const ld = document.createElement("script");
    ld.type = "application/ld+json";
    ld.id = "id-jsonld";
    ld.text = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": [
        { "@type": "ProfessionalService", "name": "Interior Intelligence by PropManage",
          "alternateName": "Design Interior, Arhitectură de Interior & Implementare",
          "provider": { "@type": "Organization", "name": "PropManage" },
          "areaServed": ["România", ...(content.local_cities || [])],
          "description": content.seo?.description,
          "serviceType": ["Design interior", "Arhitectură de interior", "Audit locuință", "Scanare 3D / Digital Twin", "Management proiect renovare"] },
        { "@type": "BreadcrumbList", "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Acasă", "item": window.location.origin + "/" },
          { "@type": "ListItem", "position": 2, "name": "Interior Intelligence", "item": window.location.origin + "/design-interior" }]},
        { "@type": "FAQPage", "mainEntity": (content.faq || []).map((f) => ({ "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a } })) },
      ],
    });
    document.head.appendChild(ld);
    let canon = document.querySelector('link[rel="canonical"]');
    if (!canon) { canon = document.createElement("link"); canon.rel = "canonical"; document.head.appendChild(canon); }
    canon.href = window.location.origin + "/design-interior";
    return () => { document.getElementById("id-jsonld")?.remove(); };
  }, [content]);

  if (!content) return <div className="min-h-screen bg-white flex items-center justify-center text-stone-400">Se încarcă…</div>;

  const brand = content.brand || { name: "Interior Intelligence", suffix: "by PropManage", tagline: "" };
  const phases = content.process_phases || [];
  const twin = content.digital_twin || {};
  const audit = content.audit || {};
  const impl = content.implementation || {};
  const stylesSec = content.styles_showcase || {};
  const eco = content.ecosystem || {};
  const scrollToForm = () => scrollTo("formular");

  return (
    <div className="min-h-screen bg-white text-stone-800" data-testid="interior-design-root" style={{ fontFamily: "inherit" }}>
      {/* Header propriu, temă luminoasă */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-stone-100">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2 shrink-0" data-testid="id-nav-home">
            <Home className="w-5 h-5 text-emerald-700" />
            <span className="font-black text-stone-900 leading-none">{brand.name}<span className="block text-[10px] font-semibold text-stone-400 tracking-wide">{brand.suffix}</span></span>
          </Link>
          <nav className="hidden lg:flex items-center gap-1" data-testid="id-anchor-nav" aria-label="Secțiuni">
            {ANCHORS.map((a) => (
              <button key={a.id} onClick={() => scrollTo(a.id)} className="px-3 py-1.5 rounded-full text-xs font-bold text-stone-500 hover:text-emerald-800 hover:bg-emerald-50 transition-colors" data-testid={`id-anchor-${a.id}`}>{a.label}</button>
            ))}
          </nav>
          <button onClick={scrollToForm} className="px-5 py-2.5 rounded-full bg-emerald-700 text-white text-sm font-bold hover:bg-emerald-800 transition-colors shrink-0" data-testid="id-nav-cta">Cere ofertă</button>
        </div>
      </header>

      {/* HERO */}
      <Section className="pt-12 sm:pt-16 pb-10">
        <div className="grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-bold mb-5" data-testid="id-hero-brand">
              <Sparkles className="w-3.5 h-3.5" /> {brand.name} {brand.suffix} · {brand.tagline}
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-stone-900 leading-[1.1] tracking-tight">{content.hero.h1}</h1>
            <p className="mt-5 text-stone-600 text-base leading-relaxed max-w-lg">{content.hero.subtitle}</p>
            <div className="mt-6 flex flex-wrap items-center gap-1.5" data-testid="id-journey">
              {(content.journey || []).map((j, i) => (
                <React.Fragment key={j}>
                  <span className="px-2.5 py-1 rounded-full bg-stone-100 text-stone-700 text-[11px] font-bold">{j}</span>
                  {i < content.journey.length - 1 && <ArrowRight className="w-3 h-3 text-emerald-600" />}
                </React.Fragment>
              ))}
            </div>
            <div className="mt-7 flex flex-wrap gap-3">
              <button onClick={scrollToForm} className="px-6 py-3.5 rounded-full bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors" data-testid="id-cta-primary">{content.hero.cta_primary}</button>
              <button onClick={scrollToForm} className="px-6 py-3.5 rounded-full border-2 border-stone-200 text-stone-700 font-bold hover:border-emerald-600 hover:text-emerald-800 transition-colors" data-testid="id-cta-secondary">{content.hero.cta_secondary}</button>
              <button onClick={scrollToForm} className="px-6 py-3.5 rounded-full text-emerald-800 font-bold hover:bg-emerald-50 transition-colors" data-testid="id-cta-tertiary">{content.hero.cta_tertiary} →</button>
            </div>
          </div>
          <img src={content.hero.image} alt={content.hero.image_alt} className="rounded-3xl shadow-2xl w-full object-cover aspect-[3/2]" loading="eager" data-testid="id-hero-image" />
        </div>
      </Section>

      {/* POZIȚIONARE — național + Cluj/Transilvania */}
      {content.positioning && (
        <Section className="py-8">
          <div className="rounded-3xl bg-stone-50 border border-stone-100 p-6 sm:p-8 flex flex-col lg:flex-row lg:items-center gap-6" data-testid="id-positioning">
            <div className="flex-1">
              <h2 className="text-lg font-black text-stone-900 flex items-center gap-2"><MapPin className="w-5 h-5 text-emerald-700" /> {content.positioning.title}</h2>
              <p className="mt-2 text-sm text-stone-600 leading-relaxed">{content.positioning.text}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(content.positioning.badges || []).map((b, i) => (
                <span key={i} className="px-3 py-1.5 rounded-full bg-white border border-emerald-200 text-emerald-800 text-xs font-bold" data-testid={`id-pos-badge-${i}`}>{b}</span>
              ))}
            </div>
          </div>
        </Section>
      )}

      {/* BENEFICII */}
      <Section className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-8">De ce Interior Intelligence, nu un studio clasic</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {content.benefits.map((b, i) => (
            <div key={i} className="p-6 rounded-3xl bg-stone-50 border border-stone-100 hover:border-emerald-200 transition-colors" data-testid={`id-benefit-${i}`}>
              <div className="w-10 h-10 rounded-2xl bg-emerald-700 text-white flex items-center justify-center mb-3">{[<Network />, <Scan />, <ShieldCheck />, <Wallet />, <Palette />, <ClipboardCheck />][i % 6]}</div>
              <h3 className="font-bold text-stone-900 mb-1">{b.title}</h3>
              <p className="text-sm text-stone-600">{b.text}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* PROCESUL — 17 etape, 5 faze */}
      <Section id="proces" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">Un singur proces. 17 etape. Zero improvizație.</h2>
        <p className="text-sm text-stone-500 mb-10 max-w-2xl">Toate serviciile — de la consultanță la House Health — sunt etape ale aceluiași proces integrat. Poți alege module separate, dar puterea reală e în întreg.</p>
        <div className="space-y-10">
          {phases.map((ph, pi) => (
            <div key={pi} data-testid={`id-phase-${pi}`}>
              <div className="flex items-baseline gap-3 mb-4">
                <span className="text-xs font-black uppercase tracking-widest text-emerald-700">Faza {pi + 1}</span>
                <h3 className="text-lg font-black text-stone-900">{ph.phase}</h3>
                <span className="hidden sm:inline text-xs text-stone-400">{ph.intro}</span>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
                {ph.steps.map((s) => (
                  <div key={s.n} className="p-5 rounded-3xl border border-stone-100 bg-white shadow-sm hover:border-emerald-200 transition-colors" data-testid={`id-step-${s.n}`}>
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

      {/* DIGITAL TWIN */}
      <Section id="digital-twin" className="py-14">
        <div className="rounded-[2rem] bg-stone-900 text-white p-8 sm:p-12" data-testid="id-twin-section">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 text-xs font-bold mb-5"><Scan className="w-3.5 h-3.5" /> Tehnologia din spatele procesului</div>
          <h2 className="text-2xl sm:text-3xl font-black leading-tight max-w-2xl">{twin.title}</h2>
          <p className="mt-4 text-stone-300 text-sm leading-relaxed max-w-2xl">{twin.intro}</p>
          <div className="mt-7 flex flex-wrap gap-2">
            {(twin.contains || []).map((c, i) => (
              <span key={i} className="px-3.5 py-2 rounded-full bg-white/5 border border-white/10 text-stone-200 text-xs font-semibold" data-testid={`id-twin-item-${i}`}>{c}</span>
            ))}
          </div>
          {twin.modular_note && (
            <div className="mt-6 p-4 rounded-2xl bg-white/5 border border-white/10 max-w-2xl" data-testid="id-twin-modular-note">
              <div className="text-[10px] font-black uppercase tracking-widest text-emerald-300 mb-1.5">Soluție modulară</div>
              <p className="text-xs text-stone-300 leading-relaxed">{twin.modular_note}</p>
            </div>
          )}
          <p className="mt-7 text-emerald-300/90 text-sm font-semibold max-w-2xl">{twin.outro}</p>
          <button onClick={() => openDetail("twin")} className="mt-6 px-6 py-3 rounded-full bg-emerald-500 text-white font-bold hover:bg-emerald-400 transition-colors" data-testid="id-twin-details-btn">
            Vezi tot ce conține Digital Twin →
          </button>
        </div>
      </Section>

      {/* AUDIT */}
      <Section id="audit" className="py-14">
        <div className="grid lg:grid-cols-2 gap-10 items-start">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-bold mb-5"><ClipboardCheck className="w-3.5 h-3.5" /> Diagnostic tehnic, nu inspecție vizuală</div>
            <h2 className="text-2xl sm:text-3xl font-black text-stone-900 leading-tight">{audit.title}</h2>
            <p className="mt-4 text-sm text-stone-600 leading-relaxed">{audit.intro}</p>
            {audit.key_message && (
              <div className="mt-5 p-4 rounded-2xl bg-emerald-50 border-l-4 border-emerald-600" data-testid="id-audit-key-message">
                <p className="text-sm font-bold text-emerald-900 italic leading-relaxed">&bdquo;{audit.key_message}&rdquo;</p>
              </div>
            )}
            {audit.modular_note && (
              <div className="mt-4 p-4 rounded-2xl bg-stone-50 border border-stone-200" data-testid="id-audit-modular-note">
                <div className="text-[10px] font-black uppercase tracking-widest text-emerald-700 mb-1.5">Metodologie modulară</div>
                <p className="text-xs text-stone-700 leading-relaxed">{audit.modular_note}</p>
              </div>
            )}
            <p className="mt-4 text-sm text-stone-700 font-semibold">{audit.outro}</p>
            <button onClick={() => openDetail("audit")} className="mt-6 px-6 py-3 rounded-full bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors" data-testid="id-audit-details-btn">
              Află tot ce include Auditul →
            </button>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            {(audit.points || []).map((p, i) => (
              <div key={i} className="flex items-start gap-2.5 p-4 rounded-2xl bg-stone-50 border border-stone-100" data-testid={`id-audit-point-${i}`}>
                <Check className="w-4 h-4 text-emerald-700 mt-0.5 shrink-0" />
                <span className="text-sm text-stone-700">{p}</span>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* STILURI */}
      <Section id="stiluri" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">{stylesSec.title || "Putem lucra în orice stil"}</h2>
        <p className="text-sm text-stone-500 mb-8 max-w-2xl">{stylesSec.intro}</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(stylesSec.items || []).map((s, i) => (
            <div key={i} className="p-5 rounded-3xl border border-stone-100 bg-white hover:border-emerald-200 hover:shadow-md transition-all" data-testid={`id-style-${i}`}>
              <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3"><Palette className="w-4 h-4" /></div>
              <h3 className="font-bold text-stone-900 text-sm">{s.name}</h3>
              <p className="text-xs text-stone-500 mt-1">{s.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* PORTOFOLIU */}
      <Section className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-8">Proiecte & portofoliu</h2>
        <div className="grid sm:grid-cols-2 gap-5">
          {content.portfolio.map((p, i) => (
            <figure key={i} className="group rounded-3xl overflow-hidden relative" data-testid={`id-portfolio-${i}`}>
              <img src={p.image} alt={p.image_alt} loading="lazy" className="w-full aspect-[3/2] object-cover group-hover:scale-105 transition-transform duration-500" />
              <figcaption className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/70 to-transparent text-white">
                <div className="font-bold text-sm">{p.title}</div>
                <div className="text-xs opacity-80">{p.location}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </Section>

      {/* IMPLEMENTARE */}
      <Section id="implementare" className="py-14">
        <div className="rounded-[2rem] bg-emerald-50 border border-emerald-100 p-8 sm:p-12" data-testid="id-impl-section">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white text-emerald-800 text-xs font-bold mb-5"><Wrench className="w-3.5 h-3.5" /> De la PDF la realitate</div>
          <h2 className="text-2xl sm:text-3xl font-black text-stone-900 leading-tight max-w-2xl">{impl.title}</h2>
          <p className="mt-4 text-sm text-stone-600 leading-relaxed max-w-2xl">{impl.intro}</p>
          <div className="mt-7 grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {(impl.points || []).map((p, i) => (
              <div key={i} className="flex items-start gap-2 p-3.5 rounded-2xl bg-white border border-emerald-100" data-testid={`id-impl-point-${i}`}>
                <Check className="w-3.5 h-3.5 text-emerald-700 mt-0.5 shrink-0" />
                <span className="text-xs font-semibold text-stone-700">{p}</span>
              </div>
            ))}
          </div>
          <button onClick={scrollToForm} className="mt-8 px-6 py-3.5 rounded-full bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition-colors" data-testid="id-impl-cta">Pornește procesul →</button>
        </div>
      </Section>

      {/* ECOSISTEM */}
      <Section id="ecosistem" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">{eco.title || "Parte dintr-un ecosistem complet"}</h2>
        <p className="text-sm text-stone-500 mb-6 max-w-2xl">{eco.intro}</p>
        <div className="mb-8 p-5 rounded-3xl bg-stone-50 border border-stone-100" data-testid="id-canonical-flow">
          <EcosystemFlow />
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {(eco.links || []).map((s, i) => (
            <Link key={i} to={s.href} className="p-5 rounded-3xl border border-stone-100 hover:border-emerald-300 hover:shadow-lg transition-all group" data-testid={`id-eco-${i}`}>
              <h3 className="font-bold text-stone-900 text-sm group-hover:text-emerald-800">{s.title} →</h3>
              <p className="text-xs text-stone-500 mt-1">{s.text}</p>
            </Link>
          ))}
        </div>
        <NextStep
          title="Vinde sau cumpără cu istoric tehnic complet"
          desc="Proprietățile care trec prin acest proces devin Imobile Verificate — cu audit, Digital Twin și credibilitate maximă la vânzare."
          to="/imobile-verificate"
          cta="Vezi Imobilele Verificate"
        />
      </Section>

      {/* RECENZII */}
      <Section className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-8">Ce spun clienții</h2>
        <div className="grid sm:grid-cols-3 gap-5">
          {content.reviews.map((r, i) => (
            <blockquote key={i} className="p-6 rounded-3xl bg-stone-50 border border-stone-100" data-testid={`id-review-${i}`}>
              <div className="flex gap-0.5 mb-2">{Array.from({ length: r.rating }).map((_, j) => <Star key={j} className="w-4 h-4 fill-amber-400 text-amber-400" />)}</div>
              <p className="text-sm text-stone-700 italic">"{r.text}"</p>
              <footer className="mt-3 text-xs font-bold text-stone-500">{r.name} · {r.city}</footer>
            </blockquote>
          ))}
        </div>
      </Section>

      {/* FORMULAR */}
      <Section id="formular" className="py-14">
        <div className="rounded-[2rem] bg-stone-50 border border-stone-100 p-6 sm:p-10">
          <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-2">Programează consultanța gratuită</h2>
          <p className="text-sm text-stone-500 mb-7">Completezi în 2 minute · primești răspuns în 24-48h · fără nicio obligație.</p>
          <LeadForm content={content} />
        </div>
      </Section>

      {/* FAQ */}
      <Section id="faq" className="py-14">
        <h2 className="text-2xl sm:text-3xl font-black text-stone-900 mb-6">Întrebări frecvente</h2>
        <div itemScope itemType="https://schema.org/FAQPage">
          {content.faq.map((f, i) => <FAQItem key={i} q={f.q} a={f.a} idx={i} />)}
        </div>
      </Section>

      {/* ARTICOL SEO */}
      <Section className="py-14">
        <article className="prose-sm max-w-3xl">
          {content.seo_article.map((s, i) => (
            <div key={i} className="mb-8" data-testid={`id-article-${i}`}>
              <h2 className="text-xl font-black text-stone-900 mb-3">{s.h2}</h2>
              <p className="text-sm text-stone-600 leading-relaxed">{s.body}</p>
            </div>
          ))}
          <h3 className="text-base font-black text-stone-900 mb-3">Explorează design interior</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 not-prose mb-6" data-testid="id-topic-graph">
            {[
              ["/design-interior/apartament", "Design apartament"],
              ["/design-interior/casa", "Design casă"],
              ["/design-interior/pret", "Preț design interior"],
              ["/design-interior/renovare", "Design pentru renovare"],
              ["/design-interior/3d", "Randări 3D & Digital Twin"],
              ["/design-interior/implementare", "Design cu implementare"],
              ["/design-interior/living", "Design living"],
              ["/design-interior/bucatarie", "Design bucătărie"],
              ["/design-interior/dormitor", "Design dormitor"],
              ["/design-interior/baie", "Design baie"],
              ["/design-interior/apartament-2-camere", "Apartament 2 camere"],
              ["/design-interior/apartament-mic", "Apartament mic"],
              ["/design-interior/birouri", "Design birouri"],
              ["/design-interior/spatii-comerciale", "Design spații comerciale"],
              ["/design-interior/cabinete-medicale", "Design cabinete medicale"],
              ["/design-interior/saloane", "Design saloane"],
            ].map(([to, label]) => (
              <Link key={to} to={to} className="px-3.5 py-2.5 rounded-xl border border-stone-100 text-sm font-semibold text-stone-700 hover:border-emerald-300 hover:text-emerald-800 transition-colors" data-testid={`id-topic-${to}`}>{label}</Link>
            ))}
          </div>
          <h3 className="text-base font-black text-stone-900 mb-3">Stiluri de design interior</h3>
          <div className="flex flex-wrap gap-2 not-prose mb-6" data-testid="id-style-links">
            {[["modern","Modern"],["scandinavian","Scandinav"],["minimalist","Minimalist"],["japandi","Japandi"],["industrial","Industrial"],["mediterranean","Mediteranean"],["classic","Clasic"],["rustic","Rustic"],["boho","Boho"]].map(([s, l]) => (
              <Link key={s} to={`/design-interior/stil/${s}`} className="px-3 py-1.5 rounded-full bg-stone-50 border border-stone-200 text-xs font-bold text-stone-600 hover:border-emerald-300 hover:text-emerald-800 transition-colors" data-testid={`id-stil-${s}`}>{l}</Link>
            ))}
          </div>
          <h3 className="text-base font-black text-stone-900 mb-2">Design interior în orașul tău</h3>
          <div className="flex flex-wrap gap-2 not-prose" data-testid="id-city-links">
            {[["bucuresti","București"],["cluj-napoca","Cluj-Napoca"],["brasov","Brașov"],["timisoara","Timișoara"],["iasi","Iași"],["oradea","Oradea"],["sibiu","Sibiu"]].map(([s, l]) => (
              <Link key={s} to={`/design-interior/${s}`} className="px-3 py-1.5 rounded-full bg-stone-50 border border-stone-200 text-xs font-bold text-stone-600 hover:border-emerald-300 hover:text-emerald-800 transition-colors" data-testid={`id-city-${s}`}>{l}</Link>
            ))}
          </div>
          <h3 className="text-base font-black text-stone-900 mb-2 mt-6">Zone și localități</h3>
          <div className="flex flex-wrap gap-2 not-prose" data-testid="id-zone-links">
            {[["floresti","Florești"],["baciu","Baciu"],["apahida","Apahida"],["marasti-cluj","Mărăști (Cluj)"],["gheorgheni-cluj","Gheorgheni (Cluj)"],["baneasa","Băneasa"],["otopeni","Otopeni"],["corbeanca","Corbeanca"],["buftea","Buftea"],["balotesti","Balotești"],["militari","Militari"],["titan","Titan"],["pipera","Pipera"]].map(([s, l]) => (
              <Link key={s} to={`/design-interior/${s}`} className="px-3 py-1.5 rounded-full bg-stone-50 border border-stone-200 text-xs font-bold text-stone-600 hover:border-emerald-300 hover:text-emerald-800 transition-colors" data-testid={`id-zone-${s}`}>{l}</Link>
            ))}
          </div>
        </article>
      </Section>

      <footer className="border-t border-stone-100 py-8 text-center text-xs text-stone-400">
        {brand.name} {brand.suffix} · © {new Date().getFullYear()} PropManage · VINTAGE FURNITURE S.R.L. · <Link to="/" className="hover:text-emerald-700">propmanage.io</Link>
      </footer>

      <AssistantWidget />
      {detailKind && (
        <ServiceDetailModal
          kind={detailKind}
          onClose={closeDetail}
          onKindChange={openDetail}
          primaryCta={{
            label: detailKind === "audit" ? "Solicită Audit" : "Solicită Digital Twin",
            onClick: scrollToForm,
          }}
        />
      )}
    </div>
  );
}
