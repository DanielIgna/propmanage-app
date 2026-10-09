// Problem detail page for /probleme-casa/:slug (problem/solution SEO intent).
// Mirrors the guide template design; adds Article + FAQPage + BreadcrumbList JSON-LD
// and internal links down to relevant services (marketplace), guides and sibling problems.
import React, { useState } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, Clock, Calendar, ArrowRight, ArrowLeft, ChevronDown, AlertTriangle } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { PROBLEME, getProblemaBySlug } from "../data/problemeCasa";
import { SEO_CATEGORY_MAP } from "../utils/seoSlugs";

const SITE_URL = "https://propmanage.ro";

const renderBodyBlock = (block, i) => {
  if (typeof block === "string") {
    const parts = block.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={i} className="text-stone-300 leading-relaxed mb-4">
        {parts.map((part, j) =>
          part.startsWith("**") && part.endsWith("**")
            ? <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>
            : <span key={j}>{part}</span>
        )}
      </p>
    );
  }
  if (block.type === "list") {
    return (
      <ul key={i} className="mb-5 space-y-2">
        {block.items.map((item, j) => {
          const parts = item.split(/(\*\*[^*]+\*\*)/g);
          return (
            <li key={j} className="text-stone-300 leading-relaxed pl-5 relative">
              <span className="absolute left-0 top-2 w-1.5 h-1.5 rounded-full bg-[#d4ff3a]" />
              {parts.map((part, k) =>
                part.startsWith("**") && part.endsWith("**")
                  ? <strong key={k} className="text-white font-semibold">{part.slice(2, -2)}</strong>
                  : <span key={k}>{part}</span>
              )}
            </li>
          );
        })}
      </ul>
    );
  }
  if (block.type === "callout") {
    return (
      <div key={i} className="my-6 rounded-2xl border border-[#d4ff3a]/30 bg-[#d4ff3a]/5 p-5">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-[#d4ff3a] mb-2">
          <AlertTriangle className="w-3 h-3" /> {block.title}
        </div>
        <div className="text-stone-200 text-sm leading-relaxed">{block.body}</div>
      </div>
    );
  }
  return null;
};

const FaqItem = ({ q, a, index }) => {
  const [open, setOpen] = useState(index === 0);
  return (
    <div className="border-b border-white/5 last:border-b-0">
      <button onClick={() => setOpen(!open)} className="w-full text-left py-4 flex items-center justify-between gap-4 group" data-testid={`problem-faq-question-${index}`}>
        <span className="font-medium text-stone-100 group-hover:text-[#d4ff3a] transition">{q}</span>
        <ChevronDown className={`w-4 h-4 text-stone-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="pb-5 text-stone-300 text-sm leading-relaxed" data-testid={`problem-faq-answer-${index}`}>{a}</div>}
    </div>
  );
};

export const ProblemaPage = () => {
  const { slug } = useParams();
  const problem = getProblemaBySlug(slug);

  useSEO(problem ? {
    title: problem.title,
    description: problem.description,
    canonical: `${SITE_URL}/probleme-casa/${problem.slug}`,
    jsonLd: {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Article",
          "headline": problem.h1,
          "description": problem.description,
          "url": `${SITE_URL}/probleme-casa/${problem.slug}`,
          "datePublished": problem.publishedAt,
          "dateModified": problem.updatedAt,
          "inLanguage": "ro-RO",
          "author": { "@type": "Organization", "name": "PropManage", "url": SITE_URL },
          "publisher": { "@type": "Organization", "name": "PropManage", "url": SITE_URL, "logo": { "@type": "ImageObject", "url": `${SITE_URL}/og-cover.svg` } },
          "mainEntityOfPage": `${SITE_URL}/probleme-casa/${problem.slug}`,
        },
        {
          "@type": "FAQPage",
          "mainEntity": problem.faq.map(f => ({ "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a } })),
        },
        {
          "@type": "BreadcrumbList",
          "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
            { "@type": "ListItem", "position": 2, "name": "Probleme casă", "item": `${SITE_URL}/probleme-casa` },
            { "@type": "ListItem", "position": 3, "name": problem.h1, "item": `${SITE_URL}/probleme-casa/${problem.slug}` },
          ],
        },
      ],
    },
  } : { title: "Problemă negăsită · PropManage", noindex: true });

  if (!problem) return <Navigate to="/probleme-casa" replace />;

  const relatedProblems = (problem.relatedProblems || [])
    .map(s => PROBLEME.find(p => p.slug === s)).filter(Boolean).slice(0, 3);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100" data-testid="problema-page">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/probleme-casa" className="text-xs text-stone-400 hover:text-white flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Toate problemele
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
          <Link to="/" className="hover:text-stone-200">Acasă</Link><span>/</span>
          <Link to="/probleme-casa" className="hover:text-stone-200">Probleme casă</Link><span>/</span>
          <span className="text-stone-300 truncate max-w-xs">{problem.h1}</span>
        </nav>

        <article>
          <div className="mb-8">
            <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
              <AlertTriangle className="w-3 h-3" /> {problem.tag}
            </div>
            <h1 className="font-serif text-3xl sm:text-5xl tracking-tight leading-tight mb-4" data-testid="problema-h1">{problem.h1}</h1>
            <p className="text-stone-400 text-lg leading-relaxed mb-4">{problem.description}</p>
            <div className="flex items-center gap-4 text-xs text-stone-500 pb-6 border-b border-white/5">
              <span className="flex items-center gap-1.5"><Calendar className="w-3 h-3" /> Actualizat {new Date(problem.updatedAt).toLocaleDateString("ro-RO", { day: "numeric", month: "long", year: "numeric" })}</span>
              <span className="flex items-center gap-1.5"><Clock className="w-3 h-3" /> {problem.readMins} min citire</span>
            </div>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="prose-style" data-testid="problema-body">
            {problem.sections.map((s, i) => (
              <section key={i} className="mb-10">
                <h2 className="font-serif text-2xl sm:text-3xl text-white mb-4 mt-2">{s.heading}</h2>
                <div>{s.body.map(renderBodyBlock)}</div>
              </section>
            ))}
          </motion.div>

          {problem.faq?.length > 0 && (
            <section className="mt-12 pt-10 border-t border-white/5" data-testid="problema-faq">
              <h2 className="font-serif text-2xl sm:text-3xl text-white mb-6">Întrebări frecvente</h2>
              <div>{problem.faq.map((f, i) => <FaqItem key={i} q={f.q} a={f.a} index={i} />)}</div>
            </section>
          )}

          {problem.relatedCategories?.length > 0 && (
            <section className="mt-12 pt-10 border-t border-white/5" data-testid="problema-services">
              <h2 className="font-serif text-2xl text-white mb-2">Găsește specialiști verificați</h2>
              <p className="text-sm text-stone-400 mb-6">Cere oferte de la specialiști verificați, cu recenzii reale și plată protejată prin escrow.</p>
              <div className="flex flex-wrap gap-2.5">
                {problem.relatedCategories.map(catSlug => {
                  const cat = SEO_CATEGORY_MAP[catSlug];
                  if (!cat) return null;
                  return (
                    <Link key={catSlug} to={`/marketplace/${catSlug}`} className="text-sm font-semibold text-[#d4ff3a] hover:underline inline-flex items-center gap-1 bg-[#d4ff3a]/5 border border-[#d4ff3a]/20 rounded-full px-4 py-2">
                      {cat.plural} verificați <ArrowRight className="w-3 h-3" />
                    </Link>
                  );
                })}
                <Link to="/preturi" className="text-sm font-semibold text-stone-300 hover:text-white inline-flex items-center gap-1 bg-white/5 border border-white/10 rounded-full px-4 py-2">
                  Vezi prețuri orientative <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </section>
          )}

          {problem.relatedGuides?.length > 0 && (
            <section className="mt-10" data-testid="problema-guides">
              <h3 className="text-sm font-semibold text-stone-200 mb-3">Ghiduri utile</h3>
              <div className="flex flex-wrap gap-2">
                {problem.relatedGuides.map(g => (
                  <Link key={g} to={`/ghiduri/${g}`} className="text-[12px] text-stone-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full px-3 py-1.5 transition">
                    {g.replace(/-/g, " ")}
                  </Link>
                ))}
              </div>
            </section>
          )}

          <div className="mt-12 glass-strong rounded-3xl p-8 text-center" data-testid="problema-cta">
            <h2 className="font-serif text-2xl mb-2">Ai această problemă în casă?</h2>
            <p className="text-stone-400 text-sm mb-5 max-w-md mx-auto">Postează o cerere gratuit și primești oferte de la specialiști verificați, cu plată protejată prin escrow.</p>
            <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-7 py-2.5 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">Începe gratuit</Link>
          </div>
        </article>

        {relatedProblems.length > 0 && (
          <section className="mt-16 pt-10 border-t border-white/5">
            <h2 className="font-serif text-2xl text-white mb-5">Vezi și</h2>
            <div className="grid sm:grid-cols-3 gap-4">
              {relatedProblems.map(p => (
                <Link key={p.slug} to={`/probleme-casa/${p.slug}`} className="glass-strong rounded-2xl p-5 hover:bg-white/[0.06] transition group" data-testid={`related-problem-${p.slug}`}>
                  <div className="text-[10px] uppercase tracking-wider font-semibold text-[#d4ff3a] mb-2">{p.tag}</div>
                  <div className="font-serif text-base leading-tight mb-2 group-hover:text-[#d4ff3a] transition line-clamp-2">{p.h1}</div>
                  <div className="text-xs text-stone-500 flex items-center gap-1"><Clock className="w-3 h-3" /> {p.readMins} min</div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-white/5 mt-16 py-8 px-6 text-center text-xs text-stone-500">
        © {new Date().getFullYear()} PropManage · operat de Vintage Furniture S.R.L. (CUI 35250247) · <Link to="/terms" className="hover:text-stone-300">Termeni</Link> · <Link to="/privacy" className="hover:text-stone-300">Confidențialitate</Link>
      </footer>
    </div>
  );
};

export default ProblemaPage;
