// Individual guide article page for /ghiduri/:slug
// Renders structured content + FAQ + internal links to /marketplace landing pages
// with Article + FAQPage JSON-LD for Google rich snippets.
import React, { useState } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, Clock, Calendar, ArrowRight, ArrowLeft, ChevronDown, BookOpen } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { GHIDURI, getGhidBySlug } from "../data/ghiduri";
import { SEO_CATEGORY_MAP } from "../utils/seoSlugs";
import { LeadMagnetCTA } from "../components/LeadMagnetCTA";

const SITE_URL = "https://propmanage.ro";

// ---- body block renderer (supports strings, lists, callouts) ----
const renderBodyBlock = (block, i) => {
  if (typeof block === "string") {
    // Process inline **bold** markdown
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
        <div className="text-[10px] uppercase tracking-wider font-bold text-[#d4ff3a] mb-2">{block.title}</div>
        <div className="text-stone-200 text-sm leading-relaxed">{block.body}</div>
      </div>
    );
  }
  return null;
};

// ---- FAQ accordion item ----
const FaqItem = ({ q, a, index }) => {
  const [open, setOpen] = useState(index === 0);
  return (
    <div className="border-b border-white/5 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left py-4 flex items-center justify-between gap-4 group"
        data-testid={`faq-question-${index}`}
      >
        <span className="font-medium text-stone-100 group-hover:text-[#d4ff3a] transition">{q}</span>
        <ChevronDown className={`w-4 h-4 text-stone-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="pb-5 text-stone-300 text-sm leading-relaxed" data-testid={`faq-answer-${index}`}>
          {a}
        </div>
      )}
    </div>
  );
};

// ---- Page ----
export const GhidPage = () => {
  const { slug } = useParams();
  const guide = getGhidBySlug(slug);

  // SEO must be called unconditionally (rules of hooks)
  useSEO(guide ? {
    title: guide.title,
    description: guide.description,
    canonical: `${SITE_URL}/ghiduri/${guide.slug}`,
    jsonLd: {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Article",
          "headline": guide.h1,
          "description": guide.description,
          "url": `${SITE_URL}/ghiduri/${guide.slug}`,
          "datePublished": guide.publishedAt,
          "dateModified": guide.updatedAt,
          "inLanguage": "ro-RO",
          "author": { "@type": "Organization", "name": "PropManage", "url": SITE_URL },
          "publisher": {
            "@type": "Organization",
            "name": "PropManage",
            "url": SITE_URL,
            "logo": { "@type": "ImageObject", "url": `${SITE_URL}/og-cover.svg` },
          },
          "mainEntityOfPage": `${SITE_URL}/ghiduri/${guide.slug}`,
        },
        {
          "@type": "FAQPage",
          "mainEntity": guide.faq.map(f => ({
            "@type": "Question",
            "name": f.q,
            "acceptedAnswer": { "@type": "Answer", "text": f.a },
          })),
        },
        {
          "@type": "BreadcrumbList",
          "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
            { "@type": "ListItem", "position": 2, "name": "Ghiduri", "item": `${SITE_URL}/ghiduri` },
            { "@type": "ListItem", "position": 3, "name": guide.h1, "item": `${SITE_URL}/ghiduri/${guide.slug}` },
          ],
        },
      ],
    },
  } : { title: "Ghid negăsit · PropManage", noindex: true });

  if (!guide) return <Navigate to="/ghiduri" replace />;

  // Related guides — exclude current, pick first 3
  const relatedGuides = GHIDURI.filter(g => g.slug !== guide.slug).slice(0, 3);

  // Build internal link CTAs for each related category × top cities
  const TOP_CITIES = [
    ["bucuresti", "București"], ["cluj-napoca", "Cluj-Napoca"],
    ["timisoara", "Timișoara"], ["iasi", "Iași"], ["brasov", "Brașov"],
    ["constanta", "Constanța"], ["sibiu", "Sibiu"], ["oradea", "Oradea"],
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/ghiduri" className="text-xs text-stone-400 hover:text-white flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Toate ghidurile
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        {/* Breadcrumbs */}
        <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
          <Link to="/" className="hover:text-stone-200">Acasă</Link>
          <span>/</span>
          <Link to="/ghiduri" className="hover:text-stone-200">Ghiduri</Link>
          <span>/</span>
          <span className="text-stone-300 truncate max-w-xs">{guide.h1}</span>
        </nav>

        {/* Article header */}
        <article>
          <div className="mb-8">
            <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
              <BookOpen className="w-3 h-3" />
              {guide.tag}
            </div>
            <h1 className="font-serif text-3xl sm:text-5xl tracking-tight leading-tight mb-4" data-testid="ghid-h1">
              {guide.h1}
            </h1>
            <p className="text-stone-400 text-lg leading-relaxed mb-4">{guide.description}</p>
            <div className="flex items-center gap-4 text-xs text-stone-500 pb-6 border-b border-white/5">
              <span className="flex items-center gap-1.5"><Calendar className="w-3 h-3" /> Actualizat {new Date(guide.updatedAt).toLocaleDateString("ro-RO", { day: "numeric", month: "long", year: "numeric" })}</span>
              <span className="flex items-center gap-1.5"><Clock className="w-3 h-3" /> {guide.readMins} min citire</span>
            </div>
          </div>

          {/* Article body */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="prose-style"
            data-testid="ghid-body"
          >
            {guide.sections.map((s, i) => (
              <section key={i} className="mb-10">
                <h2 className="font-serif text-2xl sm:text-3xl text-white mb-4 mt-2">{s.heading}</h2>
                <div>{s.body.map(renderBodyBlock)}</div>
              </section>
            ))}
          </motion.div>

          {/* FAQ section */}
          {guide.faq && guide.faq.length > 0 && (
            <section className="mt-12 pt-10 border-t border-white/5" data-testid="ghid-faq">
              <h2 className="font-serif text-2xl sm:text-3xl text-white mb-6">Întrebări frecvente</h2>
              <div>
                {guide.faq.map((f, i) => <FaqItem key={i} q={f.q} a={f.a} index={i} />)}
              </div>
            </section>
          )}

          {/* Internal links: relevant marketplace landing pages */}
          {guide.relatedCategories && guide.relatedCategories.length > 0 && (
            <section className="mt-12 pt-10 border-t border-white/5" data-testid="ghid-internal-links">
              <h2 className="font-serif text-2xl text-white mb-2">Găsește specialiști pentru lucrarea ta</h2>
              <p className="text-sm text-stone-400 mb-6">Specialiști verificați, recenzii reale, plăți escrow.</p>
              <div className="space-y-5">
                {guide.relatedCategories.map(catSlug => {
                  const cat = SEO_CATEGORY_MAP[catSlug];
                  if (!cat) return null;
                  return (
                    <div key={catSlug}>
                      <Link to={`/marketplace/${catSlug}`}
                        className="text-sm font-semibold text-[#d4ff3a] hover:underline inline-flex items-center gap-1"
                      >
                        {cat.plural} verificați <ArrowRight className="w-3 h-3" />
                      </Link>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {TOP_CITIES.map(([citySlug, cityName]) => (
                          <Link
                            key={citySlug}
                            to={`/marketplace/${catSlug}-${citySlug}`}
                            className="text-[11px] text-stone-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full px-2.5 py-1 transition"
                          >
                            {cityName}
                          </Link>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Lead magnets — Growth OS G1 */}
          <LeadMagnetCTA />

          {/* Bottom CTA */}
          <div className="mt-12 glass-strong rounded-3xl p-8 text-center" data-testid="ghid-cta">
            <h2 className="font-serif text-2xl mb-2">Vrei să începi lucrarea?</h2>
            <p className="text-stone-400 text-sm mb-5 max-w-md mx-auto">
              Postează o cerere gratuit și primești 3-5 oferte de la specialiști verificați în 24h.
            </p>
            <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-7 py-2.5 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">
              Începe gratuit
            </Link>
          </div>
        </article>

        {/* Related guides */}
        {relatedGuides.length > 0 && (
          <section className="mt-16 pt-10 border-t border-white/5">
            <h2 className="font-serif text-2xl text-white mb-5">Citește și</h2>
            <div className="grid sm:grid-cols-3 gap-4">
              {relatedGuides.map(g => (
                <Link key={g.slug} to={`/ghiduri/${g.slug}`}
                  className="glass-strong rounded-2xl p-5 hover:bg-white/[0.06] transition group"
                  data-testid={`related-${g.slug}`}
                >
                  <div className="text-[10px] uppercase tracking-wider font-semibold text-[#d4ff3a] mb-2">{g.tag}</div>
                  <div className="font-serif text-base leading-tight mb-2 group-hover:text-[#d4ff3a] transition line-clamp-2">{g.h1}</div>
                  <div className="text-xs text-stone-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {g.readMins} min
                  </div>
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

export default GhidPage;
