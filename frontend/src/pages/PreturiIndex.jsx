// /preturi — index SEO: prețuri orientative per categorie de lucrări
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ArrowRight, Coins, ShieldCheck } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

const API = process.env.REACT_APP_BACKEND_URL;
const SITE_URL = "https://propmanage.ro";

export default function PreturiIndex() {
  const [items, setItems] = useState(null);
  const year = new Date().getFullYear();

  useEffect(() => {
    fetch(`${API}/api/construction/prices/seo-pages`).then(r => r.json()).then(d => setItems(d.items || [])).catch(() => setItems([]));
  }, []);

  useSEO({
    title: `Prețuri lucrări & renovări ${year} · Cât costă? · PropManage`,
    description: `Prețuri orientative ${year} pentru zugrăvit, parchet, gresie, instalații electrice și sanitare, HVAC și alte lucrări. Compară costuri și primește oferte de la specialiști verificați.`,
    canonical: `${SITE_URL}/preturi`,
    jsonLd: items?.length ? {
      "@context": "https://schema.org",
      "@type": "ItemList",
      "name": `Prețuri lucrări ${year}`,
      "itemListElement": items.map((it, i) => ({
        "@type": "ListItem", "position": i + 1, "name": it.name, "url": `${SITE_URL}/preturi/${it.slug}`,
      })),
    } : undefined,
  });

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/imobile-verificate" className="text-xs text-stone-400 hover:text-white">Imobile Verificate</Link>
          <span className="mx-1" />
          <ThemeSwitcher />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
          <Link to="/" className="hover:text-stone-200">Acasă</Link>
          <span>/</span>
          <span className="text-stone-300">Prețuri</span>
        </nav>

        <div className="mb-12 max-w-3xl">
          <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
            <Coins className="w-3 h-3" />
            Observator de prețuri · actualizat {year}
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-serif font-semibold leading-tight">
            Cât costă lucrările în {year}?
          </h1>
          <p className="mt-4 text-stone-400 text-base max-w-2xl">
            Prețuri orientative de piață pentru cele mai căutate lucrări la locuință — pe orașe și niveluri
            de experiență. Apoi primești oferte reale de la specialiști verificați.
          </p>
        </div>

        {items === null ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-36 rounded-2xl bg-white/5 animate-pulse" />)}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="preturi-index-grid">
            {items.map(it => (
              <Link key={it.slug} to={`/preturi/${it.slug}`} data-testid={`preturi-card-${it.slug}`}
                className="group rounded-2xl border border-white/10 bg-white/[0.03] p-5 hover:border-[#d4ff3a]/40 hover:bg-white/[0.06] transition-colors">
                <h2 className="text-base font-semibold text-stone-100">{it.name}</h2>
                <div className="mt-2 text-2xl font-black text-[#d4ff3a]">
                  {it.price_from}–{it.price_to} <span className="text-sm font-semibold text-stone-400">lei/{it.unit_sample}</span>
                </div>
                <div className="mt-1 text-xs text-stone-500">{it.services_count} servicii · {it.preliminary ? "orientativ" : "date platformă"}</div>
                <div className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-stone-300 group-hover:text-[#d4ff3a] transition-colors">
                  Vezi prețurile <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="mt-16 rounded-3xl border border-[#d4ff3a]/20 bg-[#d4ff3a]/5 p-8 text-center">
          <ShieldCheck className="w-8 h-8 text-[#d4ff3a] mx-auto" />
          <h2 className="mt-3 text-lg font-semibold">Vrei o ofertă exactă, nu doar orientativă?</h2>
          <p className="mt-1 text-sm text-stone-400 max-w-lg mx-auto">Creezi gratuit o cerere și primești oferte de la specialiști verificați, cu plată protejată prin escrow.</p>
          <Link to="/register" data-testid="preturi-index-cta"
            className="mt-4 inline-flex items-center gap-2 btn-accent px-6 py-3 rounded-full text-sm font-medium">
            Cere oferte gratuit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>
    </div>
  );
}
