// /preturi/:slug — pagină SEO „Cât costă X în {oraș} în {an}?"
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Building2, ArrowRight, ShieldCheck, Info, ChevronDown } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

const API = process.env.REACT_APP_BACKEND_URL;
const SITE_URL = "https://propmanage.ro";

const FaqItem = ({ q, a }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-white/10 rounded-2xl overflow-hidden">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left text-sm font-semibold text-stone-200 hover:bg-white/[0.03]">
        {q} <ChevronDown className={`w-4 h-4 shrink-0 text-stone-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <p className="px-5 pb-4 text-sm text-stone-400 leading-relaxed">{a}</p>}
    </div>
  );
};

export default function PreturiPage() {
  const { slug } = useParams();
  const [page, setPage] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [city, setCity] = useState(null);
  const [pulse, setPulse] = useState(null);

  useEffect(() => {
    setPage(null); setNotFound(false); setCity(null); setPulse(null);
    fetch(`${API}/api/construction/prices/seo-pages/${slug}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(d => { setPage(d); setCity(d.default_city); })
      .catch(() => setNotFound(true));
    fetch(`${API}/api/construction/prices/seo-pages/${slug}/pulse`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setPulse)
      .catch(() => {});
  }, [slug]);

  useSEO(page ? {
    title: `${page.title} · PropManage`,
    description: page.description,
    canonical: `${SITE_URL}/preturi/${page.slug}`,
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": page.faq.map(f => ({
        "@type": "Question", "name": f.q,
        "acceptedAnswer": { "@type": "Answer", "text": f.a },
      })),
    },
  } : {});

  if (notFound) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] text-stone-100 flex flex-col items-center justify-center gap-4">
        <p className="text-stone-400">Pagina de prețuri nu există.</p>
        <Link to="/preturi" className="btn-accent px-5 py-2.5 rounded-full text-sm">Vezi toate prețurile</Link>
      </div>
    );
  }

  const rows = page && city ? (page.prices_by_city[city] || []) : [];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/preturi" className="text-xs text-stone-400 hover:text-white">Toate prețurile</Link>
          <span className="mx-1" />
          <ThemeSwitcher />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        {!page ? (
          <div className="space-y-4">
            <div className="h-10 w-2/3 rounded bg-white/5 animate-pulse" />
            <div className="h-64 rounded-2xl bg-white/5 animate-pulse" />
          </div>
        ) : (
          <>
            <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb">
              <Link to="/" className="hover:text-stone-200">Acasă</Link>
              <span>/</span>
              <Link to="/preturi" className="hover:text-stone-200">Prețuri</Link>
              <span>/</span>
              <span className="text-stone-300">{page.name}</span>
            </nav>

            <h1 className="text-4xl sm:text-5xl font-serif font-semibold leading-tight max-w-3xl" data-testid="preturi-h1">
              Cât costă {page.noun} în {city} în {page.year}?
            </h1>
            <p className="mt-4 text-stone-400 max-w-2xl">{page.description}</p>

            {/* Market Pulse (Faza 5 — Marketplace Intelligence) */}
            {pulse && (pulse.requests_30d > 0 || pulse.active_specialists > 0) && (
              <div className="mt-6 inline-flex flex-wrap items-center gap-x-5 gap-y-2 rounded-2xl border border-[#d4ff3a]/20 bg-[#d4ff3a]/5 px-5 py-3 text-xs" data-testid="preturi-market-pulse">
                <span className="flex items-center gap-1.5 font-bold text-stone-200">
                  <span className="w-2 h-2 rounded-full bg-[#d4ff3a] animate-pulse" /> Piața acum
                </span>
                {pulse.requests_30d > 0 && <span className="text-stone-400"><strong className="text-stone-200">{pulse.requests_30d}</strong> {pulse.requests_30d === 1 ? "cerere" : "cereri"} în ultimele 30 zile</span>}
                {pulse.active_specialists > 0 && <span className="text-stone-400"><strong className="text-stone-200">{pulse.active_specialists}</strong> specialiști activi</span>}
                {pulse.open_now > 0 && <span className="text-stone-400"><strong className="text-stone-200">{pulse.open_now}</strong> {pulse.open_now === 1 ? "cerere deschisă" : "cereri deschise"} acum</span>}
              </div>
            )}

            {/* Selector oraș */}
            <div className="mt-8 flex flex-wrap gap-2" data-testid="preturi-city-tabs">
              {page.cities.map(c => (
                <button key={c} onClick={() => setCity(c)} data-testid={`preturi-city-${c}`}
                  className={`px-4 py-2 rounded-full text-sm font-bold transition-colors ${city === c ? "bg-[#d4ff3a] text-black" : "bg-white/5 text-stone-300 border border-white/10 hover:bg-white/10"}`}>
                  {c}
                </button>
              ))}
            </div>

            {/* Tabel prețuri */}
            <div className="mt-6 rounded-2xl border border-white/10 overflow-hidden" data-testid="preturi-table">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase text-stone-500 bg-white/[0.03] border-b border-white/10">
                      <th className="px-4 py-3">Serviciu</th>
                      <th className="px-4 py-3">UM</th>
                      <th className="px-4 py-3">Standard (lei)</th>
                      <th className="px-4 py-3">Expert (lei)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(r => (
                      <tr key={r.service} className="border-b border-white/5 hover:bg-white/[0.03]">
                        <td className="px-4 py-3 font-semibold text-stone-200">
                          {r.service}
                          {r.preliminary && <span className="ml-2 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400">preliminar</span>}
                        </td>
                        <td className="px-4 py-3 text-stone-400">{r.unit}</td>
                        <td className="px-4 py-3">
                          {r.levels.mid ? <><b className="text-[#d4ff3a]">{r.levels.mid.price_med}</b> <span className="text-stone-500 text-xs">({r.levels.mid.price_min}–{r.levels.mid.price_max})</span></> : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {r.levels.expert ? <><b className="text-stone-100">{r.levels.expert.price_med}</b> <span className="text-stone-500 text-xs">({r.levels.expert.price_min}–{r.levels.expert.price_max})</span></> : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="mt-4 flex items-start gap-2 text-xs text-stone-500 max-w-2xl">
              <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {page.disclaimer}
            </div>

            {/* CTA */}
            <div className="mt-12 rounded-3xl border border-[#d4ff3a]/20 bg-[#d4ff3a]/5 p-8 text-center">
              <ShieldCheck className="w-8 h-8 text-[#d4ff3a] mx-auto" />
              <h2 className="mt-3 text-lg font-semibold">Primește oferte reale pentru {page.name.toLowerCase()}</h2>
              <p className="mt-1 text-sm text-stone-400 max-w-lg mx-auto">Cerere gratuită → oferte de la specialiști verificați → plată protejată prin escrow.</p>
              <Link to="/register" data-testid="preturi-cta"
                className="mt-4 inline-flex items-center gap-2 btn-accent px-6 py-3 rounded-full text-sm font-medium">
                Cere oferte gratuit <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {/* FAQ */}
            <div className="mt-12">
              <h2 className="text-lg font-semibold mb-4">Întrebări frecvente</h2>
              <div className="space-y-3" data-testid="preturi-faq">
                {page.faq.map((f, i) => <FaqItem key={i} q={f.q} a={f.a} />)}
              </div>
            </div>

            {/* Related */}
            <div className="mt-12">
              <h2 className="text-sm font-bold uppercase text-stone-500 mb-3">Alte prețuri utile</h2>
              <div className="flex flex-wrap gap-2">
                {page.related.map(r => (
                  <Link key={r.slug} to={`/preturi/${r.slug}`}
                    className="px-3 py-1.5 rounded-full text-xs font-semibold bg-white/5 border border-white/10 text-stone-300 hover:border-[#d4ff3a]/40 hover:text-[#d4ff3a] transition-colors">
                    {r.name}
                  </Link>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
