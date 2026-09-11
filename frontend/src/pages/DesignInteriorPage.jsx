// Design Interior cluster template — renders content pages, style pages and
// GATED local (city) pages. SEO via useSEO (server-truth gate for local pages).
import React, { useState, useEffect, useMemo } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import {
  Building2, ArrowRight, ChevronDown, CheckCircle2, MapPin, Sparkles, Star,
} from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { DI_PAGES, DI_STYLES, DI_LOCAL_CITIES } from "../data/designInterior";

const SITE_URL = "https://propmanage.ro";
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const bold = (s) => s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
  p.startsWith("**") && p.endsWith("**")
    ? <strong key={i} className="text-stone-100 font-semibold">{p.slice(2, -2)}</strong>
    : <React.Fragment key={i}>{p}</React.Fragment>);

const Shell = ({ children, testid }) => (
  <div className="min-h-screen bg-[#0a0a0b] text-stone-100" data-testid={testid}>
    <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
            <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
          </div>
          <span className="font-serif text-lg font-semibold">PropManage</span>
        </Link>
        <Link to="/design-interior" className="text-xs text-stone-400 hover:text-white" data-testid="di-to-hub">Design interior</Link>
      </div>
    </header>
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14">{children}</main>
    <footer className="border-t border-white/5 mt-16 py-8 px-6 text-center text-xs text-stone-500">
      © {new Date().getFullYear()} PropManage · <Link to="/design-interior" className="hover:text-stone-300">Design interior</Link> · <Link to="/terms" className="hover:text-stone-300">Termeni</Link>
    </footer>
  </div>
);

const Breadcrumb = ({ trail }) => (
  <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
    {trail.map((t, i) => (
      <React.Fragment key={i}>
        {i > 0 && <span>/</span>}
        {t.to ? <Link to={t.to} className="hover:text-stone-200">{t.label}</Link> : <span className="text-stone-300">{t.label}</span>}
      </React.Fragment>
    ))}
  </nav>
);

const Sections = ({ sections }) => (
  <div className="space-y-8 mt-8">
    {sections.map((s, i) => (
      <section key={i} data-testid={`di-section-${i}`}>
        <h2 className="font-serif text-2xl mb-3 text-white">{s.h2}</h2>
        {(s.body || []).map((p, j) => <p key={j} className="text-stone-300 leading-relaxed mb-3">{bold(p)}</p>)}
        {s.bullets && (
          <ul className="space-y-2 mt-2">
            {s.bullets.map((b, k) => (
              <li key={k} className="flex gap-2.5 text-stone-300"><CheckCircle2 className="w-4 h-4 text-[#d4ff3a] shrink-0 mt-1" /><span>{bold(b)}</span></li>
            ))}
          </ul>
        )}
      </section>
    ))}
  </div>
);

const FAQ = ({ faq }) => {
  const [open, setOpen] = useState(0);
  if (!faq?.length) return null;
  return (
    <div className="mt-12" data-testid="di-faq">
      <h2 className="font-serif text-2xl mb-4 text-white">Întrebări frecvente</h2>
      <div className="space-y-2">
        {faq.map((f, i) => (
          <div key={i} className="glass-strong rounded-xl overflow-hidden">
            <button onClick={() => setOpen(open === i ? -1 : i)} className="w-full flex items-center justify-between px-5 py-4 text-left" data-testid={`di-faq-q-${i}`}>
              <span className="font-medium text-stone-100">{f.q}</span>
              <ChevronDown className={`w-4 h-4 text-stone-400 transition-transform ${open === i ? "rotate-180" : ""}`} />
            </button>
            {open === i && <div className="px-5 pb-4 text-stone-400 leading-relaxed">{bold(f.a)}</div>}
          </div>
        ))}
      </div>
    </div>
  );
};

const Related = ({ related }) => (
  related?.length ? (
    <div className="mt-12" data-testid="di-related">
      <h2 className="font-serif text-xl mb-4 text-white">Vezi și</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        {related.map((r, i) => (
          <Link key={i} to={r.to} className="glass-strong rounded-xl px-4 py-3 flex items-center justify-between hover:bg-white/[0.06] transition group" data-testid={`di-related-${i}`}>
            <span className="text-sm text-stone-200">{r.label}</span>
            <ArrowRight className="w-4 h-4 text-stone-500 group-hover:text-[#d4ff3a] transition" />
          </Link>
        ))}
      </div>
    </div>
  ) : null
);

const CTA = () => (
  <div className="mt-14 glass-strong rounded-3xl p-8 text-center" data-testid="di-cta">
    <h2 className="font-serif text-2xl mb-2 text-white">Gata să începi proiectul?</h2>
    <p className="text-stone-400 mb-5 max-w-lg mx-auto text-sm">Postează cererea și primești oferte de la designeri verificați, cu portofolii și recenzii reale. Plată protejată prin escrow.</p>
    <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-8 py-3 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition" data-testid="di-cta-btn">Începe gratuit</Link>
  </div>
);

// ── Content / style page ─────────────────────────────────────────────────────
const StaticDesignPage = ({ page, canonicalPath, trail, breadcrumbNames }) => {
  useSEO({
    title: page.title,
    description: page.description,
    canonical: `${SITE_URL}${canonicalPath}`,
    jsonLd: {
      "@context": "https://schema.org",
      "@graph": [
        { "@type": "Service", "serviceType": "Design interior", "name": page.h1,
          "description": page.description, "areaServed": { "@type": "Country", "name": "România" },
          "provider": { "@type": "Organization", "name": "PropManage", "url": SITE_URL } },
        { "@type": "BreadcrumbList", "itemListElement": breadcrumbNames.map((b, i) => ({
          "@type": "ListItem", "position": i + 1, "name": b.label, "item": `${SITE_URL}${b.item}` })) },
        ...(page.faq?.length ? [{ "@type": "FAQPage", "mainEntity": page.faq.map(f => ({
          "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a } })) }] : []),
      ],
    },
  });
  return (
    <Shell testid="design-interior-page">
      <Breadcrumb trail={trail} />
      <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
        <Sparkles className="w-3 h-3" /> {page.tag}
      </div>
      <h1 className="font-serif text-4xl sm:text-5xl tracking-tight mb-5" data-testid="di-h1">{page.h1}</h1>
      <p className="text-stone-300 text-lg leading-relaxed">{bold(page.intro)}</p>
      <Sections sections={page.sections} />
      <FAQ faq={page.faq} />
      <Related related={page.related} />
      <CTA />
    </Shell>
  );
};

// ── Local (city) page — GATED by SSOT ────────────────────────────────────────
const LocalDesignPage = ({ citySlug, cityName }) => {
  const [gate, setGate] = useState(null);
  const [specialists, setSpecialists] = useState(null);
  const path = `/design-interior/${citySlug}`;

  useEffect(() => {
    axios.get(`${API}/public/seo/gate?path=${encodeURIComponent(path)}`).then(r => setGate(r.data)).catch(() => setGate(null));
    axios.get(`${API}/marketplace/specialists`, { params: { category: "design-interior", city: cityName, verified_only: true } })
      .then(r => setSpecialists(Array.isArray(r.data) ? r.data : (r.data?.specialists || []))).catch(() => setSpecialists([]));
  }, [citySlug]); // eslint-disable-line

  const gated = !!(gate && gate.index === false);
  useSEO({
    title: `Design interior ${cityName}: designeri verificați | PropManage`,
    description: `Design interior în ${cityName}: lucrează cu designeri verificați, cu portofolii și recenzii reale. Proiect + implementare la cheie, plată protejată prin escrow.`,
    canonical: gated && gate?.canonical ? gate.canonical : `${SITE_URL}${path}`,
    noindex: gated,
    jsonLd: {
      "@context": "https://schema.org",
      "@graph": [
        { "@type": "Service", "serviceType": "Design interior", "name": `Design interior ${cityName}`,
          "areaServed": { "@type": "City", "name": cityName, "containedInPlace": { "@type": "Country", "name": "România" } },
          "provider": { "@type": "Organization", "name": "PropManage", "url": SITE_URL } },
        { "@type": "BreadcrumbList", "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
          { "@type": "ListItem", "position": 2, "name": "Design interior", "item": `${SITE_URL}/design-interior` },
          { "@type": "ListItem", "position": 3, "name": cityName, "item": `${SITE_URL}${path}` },
        ] },
      ],
    },
  });

  const count = specialists?.length ?? null;
  return (
    <Shell testid="design-interior-local">
      <Breadcrumb trail={[{ to: "/", label: "Acasă" }, { to: "/design-interior", label: "Design interior" }, { label: cityName }]} />
      <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
        <MapPin className="w-3 h-3" /> {cityName}
      </div>
      <h1 className="font-serif text-4xl sm:text-5xl tracking-tight mb-5" data-testid="di-h1">Design interior în {cityName}</h1>
      <p className="text-stone-300 text-lg leading-relaxed">
        Cauți un designer de interior în {cityName}? Pe PropManage lucrezi doar cu specialiști verificați, cu portofolii și recenzii reale. Poți lua doar proiectul de design sau poți merge până la implementare la cheie, cu plată protejată prin escrow.
      </p>

      <div className="mt-8 glass-strong rounded-2xl p-6" data-testid="di-local-availability">
        {count === null ? (
          <p className="text-stone-400 text-sm">Se verifică disponibilitatea în {cityName}…</p>
        ) : count >= 3 ? (
          <div>
            <p className="text-stone-200"><strong className="text-[#d4ff3a]">{count} designeri verificați</strong> activi în {cityName}. Vezi profilurile, portofoliile și recenziile lor înainte să ceri o ofertă.</p>
            <div className="grid sm:grid-cols-2 gap-3 mt-4">
              {specialists.slice(0, 6).map((s) => (
                <Link key={s.id || s._id} to={`/specialists/${s.id || s._id}`} className="rounded-xl border border-white/10 px-4 py-3 hover:border-[#d4ff3a]/40 transition" data-testid="di-local-specialist">
                  <div className="text-sm text-stone-100 font-medium">{s.name || s.company_name || "Designer verificat"}</div>
                  <div className="text-xs text-stone-500 flex items-center gap-1 mt-1"><Star className="w-3 h-3 text-amber-400" /> {s.rating ? Number(s.rating).toFixed(1) : "—"} · {s.reviews_count || s.review_count || 0} recenzii</div>
                </Link>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-stone-300 text-sm">
            Momentan avem <strong>{count}</strong> designeri verificați în {cityName} — sub pragul nostru de calitate pentru o pagină locală dedicată. Poți totuși posta o cerere: îți aducem oferte de la designeri verificați care acoperă zona {cityName}.
          </p>
        )}
      </div>

      <div className="mt-8 space-y-4 text-stone-300 leading-relaxed">
        <p>Indiferent de oraș, procesul PropManage este același: <strong className="text-stone-100">Design → Audit → Digital Twin → Proiectare → Implementare</strong>. Astfel, ceea ce vezi în randare corespunde cu ceea ce se poate executa, iar plățile sunt protejate.</p>
      </div>

      <Related related={[
        { to: "/design-interior/apartament", label: "Design interior apartament" },
        { to: "/design-interior/pret", label: "Cât costă designul interior" },
        { to: "/design-interior/renovare", label: "Design pentru renovare" },
        { to: "/marketplace/design-interior", label: "Toți designerii din marketplace" },
      ]} />
      <CTA />
    </Shell>
  );
};

// ── Router entry ─────────────────────────────────────────────────────────────
export const DesignInteriorPage = ({ kind = "page" }) => {
  const { slug } = useParams();

  if (kind === "style") {
    const st = DI_STYLES[slug];
    if (!st) return <Navigate to="/design-interior" replace />;
    return <StaticDesignPage page={st} canonicalPath={`/design-interior/stil/${slug}`}
      trail={[{ to: "/", label: "Acasă" }, { to: "/design-interior", label: "Design interior" }, { label: st.tag }]}
      breadcrumbNames={[{ label: "Acasă", item: "/" }, { label: "Design interior", item: "/design-interior" }, { label: st.tag, item: `/design-interior/stil/${slug}` }]} />;
  }

  const page = DI_PAGES[slug];
  if (page) {
    return <StaticDesignPage page={page} canonicalPath={`/design-interior/${slug}`}
      trail={[{ to: "/", label: "Acasă" }, { to: "/design-interior", label: "Design interior" }, { label: page.tag }]}
      breadcrumbNames={[{ label: "Acasă", item: "/" }, { label: "Design interior", item: "/design-interior" }, { label: page.tag, item: `/design-interior/${slug}` }]} />;
  }

  const cityName = DI_LOCAL_CITIES[slug];
  if (cityName) return <LocalDesignPage citySlug={slug} cityName={cityName} />;

  return <Navigate to="/design-interior" replace />;
};

export default DesignInteriorPage;
