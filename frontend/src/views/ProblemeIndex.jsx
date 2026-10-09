// Index (hub) page for /probleme-casa — lists all house-problem solution articles.
// Problem/solution SEO intent; mirrors the /ghiduri hub design.
import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, Clock, ArrowRight, AlertTriangle, BookOpen } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { PROBLEME } from "../data/problemeCasa";

const SITE_URL = "https://propmanage.ro";

export const ProblemeIndex = () => {
  useSEO({
    title: "Probleme frecvente în casă: cauze, soluții și costuri 2026 | PropManage",
    description:
      "De la infiltrații și mucegai la fisuri și umezeală — ghiduri clare cu cauzele reale ale problemelor casei tale, soluțiile corecte, costul orientativ și când chemi un specialist verificat.",
    canonical: `${SITE_URL}/probleme-casa`,
    jsonLd: {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "CollectionPage",
          "name": "Probleme frecvente în casă",
          "url": `${SITE_URL}/probleme-casa`,
          "inLanguage": "ro-RO",
          "publisher": { "@type": "Organization", "name": "PropManage", "url": SITE_URL },
          "hasPart": PROBLEME.map((p) => ({
            "@type": "Article",
            "headline": p.h1,
            "url": `${SITE_URL}/probleme-casa/${p.slug}`,
            "datePublished": p.publishedAt,
            "dateModified": p.updatedAt,
            "description": p.description,
          })),
        },
        {
          "@type": "BreadcrumbList",
          "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
            { "@type": "ListItem", "position": 2, "name": "Probleme casă", "item": `${SITE_URL}/probleme-casa` },
          ],
        },
      ],
    },
  });

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100" data-testid="probleme-index">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/ghiduri" className="text-xs text-stone-400 hover:text-white flex items-center gap-1" data-testid="probleme-to-ghiduri">
            <BookOpen className="w-3 h-3" /> Ghiduri
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        {/* Breadcrumbs */}
        <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
          <Link to="/" className="hover:text-stone-200">Acasă</Link>
          <span>/</span>
          <span className="text-stone-300">Probleme casă</span>
        </nav>

        {/* Hero */}
        <div className="mb-12 max-w-3xl">
          <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
            <AlertTriangle className="w-3 h-3" />
            Probleme frecvente · soluții verificate
          </div>
          <h1 className="font-serif text-4xl sm:text-6xl tracking-tight mb-4" data-testid="probleme-h1">
            Probleme frecvente în casă și cum le rezolvi corect
          </h1>
          <p className="text-stone-400 text-lg leading-relaxed">
            Infiltrații, mucegai, fisuri sau umezeală? Vezi cauzele reale, soluțiile durabile și costul orientativ pentru fiecare problemă — plus când merită să chemi un specialist verificat.
          </p>
        </div>

        {/* Problem cards grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="probleme-grid">
          {PROBLEME.map((p, i) => (
            <motion.div
              key={p.slug}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                to={`/probleme-casa/${p.slug}`}
                className="block glass-strong rounded-2xl p-6 hover:bg-white/[0.06] transition group h-full"
                data-testid={`problema-card-${p.slug}`}
              >
                <div className="text-[10px] uppercase tracking-wider font-semibold text-[#d4ff3a] mb-3">{p.tag}</div>
                <h2 className="font-serif text-xl leading-tight mb-3 group-hover:text-[#d4ff3a] transition">{p.h1}</h2>
                <p className="text-sm text-stone-400 leading-relaxed mb-4 line-clamp-3">{p.description}</p>
                <div className="flex items-center justify-between text-xs text-stone-500 pt-3 border-t border-white/5">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    {p.readMins} min citire
                  </span>
                  <span className="flex items-center gap-1 text-stone-400 group-hover:text-[#d4ff3a] transition">
                    Citește <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 glass-strong rounded-3xl p-8 sm:p-10 text-center">
          <h2 className="font-serif text-3xl mb-3">Ai o problemă în casă?</h2>
          <p className="text-stone-400 mb-6 max-w-xl mx-auto">
            Postează o cerere gratuit și primești oferte de la specialiști verificați, cu recenzii reale și plată protejată prin escrow, în mai puțin de 24 de ore.
          </p>
          <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-8 py-3 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">
            Începe gratuit
          </Link>
        </div>
      </main>

      <footer className="border-t border-white/5 mt-16 py-8 px-6 text-center text-xs text-stone-500">
        © {new Date().getFullYear()} PropManage · operat de Vintage Furniture S.R.L. (CUI 35250247) · <Link to="/terms" className="hover:text-stone-300">Termeni</Link> · <Link to="/privacy" className="hover:text-stone-300">Confidențialitate</Link>
      </footer>
    </div>
  );
};

export default ProblemeIndex;
