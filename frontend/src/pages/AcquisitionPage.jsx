import React from "react";
import { Link, useLocation, Navigate } from "react-router-dom";
import { ArrowRight, Check, HelpCircle } from "lucide-react";
import { useSEO } from "../hooks/useSEO";
import { getAcqByPath } from "../data/acquisitionSeo";

const SITE_URL = "https://propmanage.ro";
const ACCENT = "#d4ff3a";

const track = (event) => {
  try { if (window.gtag) window.gtag("event", event); } catch (e) { /* noop */ }
};

const CTAButton = ({ cta, testid }) => (
  <Link
    to={cta.to}
    onClick={() => track("acq_cta_click")}
    data-testid={testid}
    className="inline-flex items-center gap-2 rounded-full px-7 py-3.5 font-semibold text-stone-900 transition-transform hover:scale-[1.03]"
    style={{ backgroundColor: ACCENT }}
  >
    {cta.label} <ArrowRight className="w-4 h-4" />
  </Link>
);

export default function AcquisitionPage() {
  const { pathname } = useLocation();
  const page = getAcqByPath(pathname);

  const canonical = page ? `${SITE_URL}${page.path}` : `${SITE_URL}${pathname}`;
  useSEO({
    title: page ? page.title : "PropManage",
    description: page ? page.description : "",
    canonical,
    noindex: !page,
    jsonLd: page ? {
      "@context": "https://schema.org",
      "@graph": [
        { "@type": "WebPage", "name": page.title, "description": page.description, "url": canonical },
        { "@type": "BreadcrumbList", "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
          { "@type": "ListItem", "position": 2, "name": page.badge, "item": canonical },
        ] },
        ...(page.faq?.length ? [{ "@type": "FAQPage", "mainEntity": page.faq.map((f) => ({
          "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a },
        })) }] : []),
      ],
    } : null,
  });

  if (!page) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen bg-[#0b0d0a] text-stone-100" data-testid={`acq-page-${page.audience}`}>
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-14 sm:py-20">
        {/* Breadcrumb */}
        <nav className="text-xs text-stone-500 mb-6 flex items-center gap-2" data-testid="acq-breadcrumb">
          <Link to="/" className="hover:text-stone-300">Acasă</Link>
          <span>/</span>
          <span className="text-stone-400">{page.badge}</span>
        </nav>

        {/* Hero */}
        <div className="inline-flex items-center gap-1.5 text-xs rounded-full px-3 py-1 mb-5 border" style={{ color: ACCENT, borderColor: `${ACCENT}33`, backgroundColor: `${ACCENT}14` }}>
          {page.badge}
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl tracking-tight mb-5" data-testid="acq-h1">{page.h1}</h1>
        <p className="text-stone-300 text-lg leading-relaxed mb-8">{page.intro}</p>
        <CTAButton cta={page.cta} testid="acq-cta-hero" />

        {/* Sections */}
        <div className="mt-14 space-y-12">
          {page.sections.map((s, i) => (
            <section key={i} data-testid={`acq-section-${i}`}>
              <h2 className="font-serif text-2xl sm:text-3xl mb-4">{s.h2}</h2>
              {s.body?.map((p, j) => (
                <p key={j} className="text-stone-300 leading-relaxed mb-3">{p}</p>
              ))}
              {s.bullets?.length ? (
                <ul className="mt-4 space-y-2.5">
                  {s.bullets.map((b, k) => (
                    <li key={k} className="flex items-start gap-3 text-stone-200">
                      <Check className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: ACCENT }} />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>

        {/* Mid CTA */}
        <div className="mt-14 rounded-2xl border border-white/10 bg-white/[0.03] p-7 text-center" data-testid="acq-midcta">
          <p className="text-stone-200 text-lg mb-5">Gata să începi? Este gratuit.</p>
          <CTAButton cta={page.cta} testid="acq-cta-mid" />
        </div>

        {/* FAQ */}
        {page.faq?.length ? (
          <section className="mt-14" data-testid="acq-faq">
            <h2 className="font-serif text-2xl sm:text-3xl mb-6">Întrebări frecvente</h2>
            <div className="space-y-5">
              {page.faq.map((f, i) => (
                <div key={i} className="border-b border-white/5 pb-5">
                  <h3 className="flex items-start gap-2 text-stone-100 font-medium mb-2">
                    <HelpCircle className="w-4 h-4 mt-1 flex-shrink-0" style={{ color: ACCENT }} />
                    {f.q}
                  </h3>
                  <p className="text-stone-400 leading-relaxed pl-6">{f.a}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {/* Related */}
        {page.related?.length ? (
          <section className="mt-14" data-testid="acq-related">
            <h2 className="font-serif text-xl mb-5">Continuă cu</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {page.related.map((r, i) => (
                <Link key={i} to={r.to} className="rounded-xl border border-white/10 px-4 py-3 flex items-center justify-between hover:bg-white/[0.05] transition group" data-testid={`acq-related-${i}`}>
                  <span className="text-sm text-stone-200">{r.label}</span>
                  <ArrowRight className="w-4 h-4 text-stone-500 group-hover:text-[color:var(--acc)] transition" style={{ "--acc": ACCENT }} />
                </Link>
              ))}
            </div>
          </section>
        ) : null}

        {/* Final CTA */}
        <div className="mt-16 text-center">
          <CTAButton cta={page.cta} testid="acq-cta-final" />
        </div>
      </div>
    </div>
  );
}
