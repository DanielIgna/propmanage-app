// SEO-optimized landing page for /marketplace/:slug routes.
// Examples:
//   /marketplace/electrician                 → all electricians in RO
//   /marketplace/electrician-bucuresti       → electricians serving București
//   /marketplace/design-interior-cluj-napoca → designers in Cluj-Napoca
//
// Each combination renders a unique H1, intro, JSON-LD (LocalBusiness if city
// is set), and internal links to sibling pages — drives long-tail local search.
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import { Building2, Star, CheckCircle2, MapPin, Shield, Award, Sparkles, ArrowRight } from "lucide-react";
import { RatingBadge } from "../components/RatingBadge";
import { useSEO } from "../hooks/useSEO";
import {
  parseLandingSlug, SEO_CITY_MAP, SEO_CATEGORY_MAP, TOP_CITIES_FOR_LINKING,
} from "../utils/seoSlugs";
import { HealthScoreBadge } from "../components/HealthScoreBadge";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const SITE_URL = "https://propmanage.ro";

// ============= Slug-not-found fallback (renders noindex) =============
const NotFoundLanding = ({ slug }) => {
  useSEO({
    title: "Pagină negăsită · PropManage Marketplace",
    description: "Această categorie sau oraș nu există în marketplace-ul PropManage.",
    noindex: true,
  });
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <h1 className="font-serif text-4xl mb-3">404</h1>
        <p className="text-stone-400 mb-6">
          Nu am găsit o pagină pentru <code className="text-[#d4ff3a]">/{slug}</code>.
        </p>
        <Link to="/marketplace" className="inline-block bg-[#d4ff3a] text-black px-6 py-2.5 rounded-full text-sm font-semibold">
          Vezi toți specialiștii
        </Link>
      </div>
    </div>
  );
};

// ============= SEO intro copy per category (used as page H2 + body) =============
const CATEGORY_INTROS = {
  "electric": "Electricienii verificați PropManage execută instalații electrice complete, repară prize și întrerupătoare defecte, înlocuiesc tablouri vechi cu cele moderne și asigură conformitate ANRE.",
  "plumbing": "Instalatorii verificați PropManage rezolvă urgent scurgeri, înfundări, înlocuiri de robineți și boilere, montează țevi PEX/cupru și asigură garanție pe lucrare.",
  "hvac": "Specialiștii HVAC verificați PropManage instalează și întrețin aparate de aer condiționat, sisteme de încălzire în pardoseală, centrale termice și ventilație industrială.",
  "interior_design": "Designerii interior PropManage creează concepte personalizate pentru apartamente și case, randări 3D realiste, listă completă materiale și asistență la achiziții.",
  "carpentry": "Tâmplarii PropManage realizează mobilă la comandă (bucătărie, dressing, dulapuri), refac uși și ferestre din lemn, montează parchet și execută finisaje complexe.",
  "painting": "Zugravii PropManage execută zugrăveli interior/exterior, tencuieli decorative, pregătire pereți, izolare fonică și aplicare lavabile premium cu garanție.",
  "cleaning": "Firmele de curățenie PropManage oferă servicii de menaj profesional, curățenie post-construcție, igienizare canapele și covoare, abonamente recurente la preț avantajos.",
  "appliance_repair": "Tehnicienii service electrocasnice PropManage repară mașini de spălat, frigidere, plite, hote și aparate de aer condiționat — diagnostic gratuit la domiciliu.",
  "gardening": "Grădinarii PropManage proiectează și întrețin grădini private, instalează sisteme de irigație automatizate, tund gardul viu și amenajează curți cu gazon rulou.",
};

const TRUST_BULLETS = [
  { icon: Shield,     title: "Specialiști verificați", desc: "Documente, asigurare și certificări validate manual de echipa noastră." },
  { icon: Star,       title: "Recenzii reale",          desc: "Doar clienți care au plătit prin platformă pot lăsa o recenzie." },
  { icon: Award,      title: "Plată escrow",            desc: "Banii sunt eliberați doar după ce confirmi că lucrarea e finalizată." },
  { icon: Sparkles,   title: "Suport în 30 secunde",    desc: "AI Concierge răspunde 24/7, echipă umană în zilele lucrătoare." },
];

// ============= Main component =============
export const MarketplaceLanding = () => {
  const { slug } = useParams();
  const parsed = parseLandingSlug(slug);
  const [specialists, setSpecialists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gate, setGate] = useState(null);

  useEffect(() => {
    if (!parsed) {
      setLoading(false);
      return;
    }
    const params = new URLSearchParams();
    params.set("category", parsed.categoryDb);
    if (parsed.cityLabel) params.set("city", parsed.cityLabel);
    setLoading(true);
    axios.get(`${API}/marketplace/specialists?${params}`)
      .then(r => setSpecialists(Array.isArray(r.data) ? r.data : []))
      .catch(() => setSpecialists([]))
      .finally(() => setLoading(false));
  }, [parsed?.categorySlug, parsed?.citySlug]);

  // Indexability Gate (server-side SSOT) — thin service×city pages get noindex + canonical→parent.
  useEffect(() => {
    if (!parsed) { setGate(null); return; }
    const path = `/marketplace/${parsed.categorySlug}${parsed.citySlug ? "-" + parsed.citySlug : ""}`;
    axios.get(`${API}/public/seo/gate?path=${encodeURIComponent(path)}`)
      .then(r => setGate(r.data))
      .catch(() => setGate(null));
  }, [parsed?.categorySlug, parsed?.citySlug]);

  // SEO computed BEFORE early return — must run hook unconditionally
  const seoData = (() => {
    if (!parsed) return { title: "Pagină negăsită", description: "" };
    const cityPart = parsed.cityLabel ? ` în ${parsed.cityLabel}` : " în România";
    const cityPart2 = parsed.cityLabel ? ` din ${parsed.cityLabel}` : " din România";
    const title = `${parsed.categoryPlural} verificați${cityPart} · PropManage Marketplace`;
    const description = parsed.cityLabel
      ? `Caută ${parsed.categoryLabel.toLowerCase()} în ${parsed.cityLabel}? Vezi ${parsed.categoryPlural.toLowerCase()} verificați cu recenzii reale, plăți escrow și garanție pe lucrare. Cere ofertă gratuit în 2 minute.`
      : `${parsed.categoryPlural} verificați în România. Profile cu recenzii reale, plăți escrow protejate și garanție pe lucrare. Compară prețuri și cere ofertă în 2 minute.`;
    const canonical = `${SITE_URL}/marketplace/${parsed.categorySlug}${parsed.citySlug ? "-" + parsed.citySlug : ""}`;

    const jsonLd = {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Service",
          "serviceType": parsed.categoryLabel,
          "name": `${parsed.categoryPlural}${cityPart2}`,
          "description": description,
          "provider": {
            "@type": "Organization",
            "name": "PropManage",
            "url": SITE_URL,
          },
          "areaServed": parsed.cityLabel
            ? { "@type": "City", "name": parsed.cityLabel, "containedInPlace": { "@type": "Country", "name": "România" } }
            : { "@type": "Country", "name": "România" },
          "offers": { "@type": "Offer", "priceCurrency": "RON", "availability": "https://schema.org/InStock" },
        },
        {
          "@type": "BreadcrumbList",
          "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "Acasă", "item": `${SITE_URL}/` },
            { "@type": "ListItem", "position": 2, "name": "Marketplace", "item": `${SITE_URL}/marketplace` },
            { "@type": "ListItem", "position": 3, "name": parsed.categoryLabel, "item": `${SITE_URL}/marketplace/${parsed.categorySlug}` },
            ...(parsed.cityLabel ? [{
              "@type": "ListItem", "position": 4,
              "name": parsed.cityLabel,
              "item": `${SITE_URL}/marketplace/${parsed.categorySlug}-${parsed.citySlug}`,
            }] : []),
          ],
        },
      ],
    };

    return { title, description, canonical, jsonLd };
  })();

  const gated = !!(gate && gate.index === false);
  useSEO({
    title: seoData.title,
    description: seoData.description,
    canonical: gated && gate.canonical ? gate.canonical : seoData.canonical,
    jsonLd: seoData.jsonLd,
    noindex: !parsed || gated,
  });

  if (!parsed) return <NotFoundLanding slug={slug} />;

  const cityPart = parsed.cityLabel ? ` în ${parsed.cityLabel}` : " în România";
  const intro = CATEGORY_INTROS[parsed.categoryDb] || `${parsed.categoryPlural} verificați pe PropManage.`;

  // Sibling cities for cross-linking (top cities minus current one)
  const siblingCities = TOP_CITIES_FOR_LINKING
    .filter(c => c !== parsed.citySlug)
    .slice(0, 9);

  // Sibling categories (same city, other specialties)
  const siblingCategories = Object.keys(SEO_CATEGORY_MAP)
    .filter(k => k !== parsed.categorySlug);

  // Relevant guides per category (drives users to long-form content)
  const GUIDES_PER_CATEGORY = {
    "electrician":            [{ slug: "cost-instalatie-electrica-apartament", title: "Cât costă o instalație electrică apartament" }, { slug: "cum-functioneaza-escrow-lucrari", title: "Cum funcționează plata escrow" }],
    "instalator":             [{ slug: "cum-verifici-instalator", title: "Cum verifici un instalator înainte să-l angajezi" }, { slug: "cum-functioneaza-escrow-lucrari", title: "Cum funcționează plata escrow" }],
    "hvac":                   [{ slug: "cum-verifici-instalator", title: "Cum verifici un specialist înainte să-l angajezi" }, { slug: "cost-renovare-apartament-2-camere", title: "Cât costă o renovare apartament 2 camere" }],
    "design-interior":        [{ slug: "cum-alegi-designer-interior", title: "Cum alegi un designer interior" }, { slug: "cost-renovare-apartament-2-camere", title: "Cât costă o renovare 2 camere" }],
    "zugrav":                 [{ slug: "cum-alegi-zugrav-bun", title: "Cum alegi un zugrav bun" }, { slug: "cost-renovare-apartament-2-camere", title: "Cât costă o renovare 2 camere" }],
    "tamplar":                [{ slug: "cost-renovare-apartament-2-camere", title: "Cât costă o renovare apartament 2 camere" }, { slug: "cum-alegi-designer-interior", title: "Cum alegi un designer interior" }],
    "firma-curatenie":        [{ slug: "cum-functioneaza-escrow-lucrari", title: "Cum funcționează plata escrow" }, { slug: "cost-renovare-apartament-2-camere", title: "Buget renovare apartament" }],
    "service-electrocasnice": [{ slug: "cum-verifici-instalator", title: "Cum verifici un specialist" }, { slug: "cum-functioneaza-escrow-lucrari", title: "Cum funcționează plata escrow" }],
    "gradinar":               [{ slug: "cum-functioneaza-escrow-lucrari", title: "Cum funcționează plata escrow" }, { slug: "cum-alegi-designer-interior", title: "Cum alegi un designer interior" }],
  };
  const relatedGuides = GUIDES_PER_CATEGORY[parsed.categorySlug] || [];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      {/* Header */}
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/login" className="text-xs text-stone-400 hover:text-white">Conectare</Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Breadcrumbs (clickable, visible) */}
        <nav className="text-xs text-stone-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="Breadcrumb" data-testid="seo-breadcrumbs">
          <Link to="/" className="hover:text-stone-200">Acasă</Link>
          <span>/</span>
          <Link to="/marketplace" className="hover:text-stone-200">Marketplace</Link>
          <span>/</span>
          <Link to={`/marketplace/${parsed.categorySlug}`} className="hover:text-stone-200">{parsed.categoryLabel}</Link>
          {parsed.cityLabel && (
            <>
              <span>/</span>
              <span className="text-stone-300">{parsed.cityLabel}</span>
            </>
          )}
        </nav>

        {/* Hero */}
        <div className="mb-10">
          {parsed.cityLabel && (
            <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
              <MapPin className="w-3 h-3" />
              {parsed.cityLabel}
            </div>
          )}
          <h1 className="font-serif text-4xl sm:text-6xl tracking-tight mb-4" data-testid="seo-h1">
            {parsed.categoryPlural} verificați{cityPart}
          </h1>
          <p className="text-stone-400 text-lg max-w-3xl leading-relaxed">{intro}</p>
        </div>

        {/* Trust bullets row */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-12">
          {TRUST_BULLETS.map((b, i) => (
            <div key={i} className="glass-strong rounded-2xl p-4">
              <b.icon className="w-4 h-4 text-[#d4ff3a] mb-2" />
              <div className="font-medium text-sm mb-1">{b.title}</div>
              <div className="text-xs text-stone-400 leading-relaxed">{b.desc}</div>
            </div>
          ))}
        </div>

        {/* Specialists results */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-2xl">Specialiști disponibili</h2>
          <div className="text-xs text-stone-500">{loading ? "Se încarcă..." : `${specialists.length} rezultate`}</div>
        </div>

        {!loading && specialists.length === 0 ? (
          <div className="glass-strong rounded-2xl p-8 sm:p-12 text-center" data-testid="seo-empty-state">
            <p className="text-stone-300 mb-2 text-lg">
              Momentan nu avem {parsed.categoryPlural.toLowerCase()} listați{parsed.cityLabel ? ` în ${parsed.cityLabel}` : ""}.
            </p>
            <p className="text-stone-500 text-sm mb-6 max-w-md mx-auto">
              Postează o cerere și echipa noastră îți va găsi în 24h un specialist verificat din această categorie.
            </p>
            <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-6 py-2.5 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition" data-testid="seo-empty-cta">
              Postează cerere gratuit
            </Link>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
            {specialists.map((s, i) => (
              <motion.div key={s.id}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.04, 0.6) }}
                className="glass-strong rounded-2xl p-5 hover:bg-white/[0.06] transition" data-testid={`seo-card-${s.id}`}>
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-stone-600 to-stone-800 flex items-center justify-center font-medium shrink-0">
                    {s.name?.[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <div className="font-medium truncate">{s.name}</div>
                      {s.verified && <CheckCircle2 className="w-3.5 h-3.5 text-[#d4ff3a] shrink-0" />}
                    </div>
                    <div className="text-[11px] text-stone-400 capitalize">{s.specialty || parsed.categoryLabel}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs mb-2">
                  <RatingBadge rating={s.rating} reviewsCount={s.reviews_count} size="sm" />
                  {s.tier && <span className="text-[9px] bg-[#d4ff3a]/15 text-[#d4ff3a] px-2 py-0.5 rounded-full uppercase tracking-wider">{s.tier}</span>}
                </div>
                <div className="mb-4">
                  <HealthScoreBadge health={s.health} size="sm" />
                </div>
                <Link to={`/specialists/${s.id}`} className="w-full text-center bg-white/5 hover:bg-white/10 py-2 rounded-xl text-xs font-medium block">
                  Vezi profil
                </Link>
              </motion.div>
            ))}
          </div>
        )}

        {/* Internal-link block: sibling cities */}
        {siblingCities.length > 0 && (
          <section className="mb-10" data-testid="seo-sibling-cities">
            <h2 className="font-serif text-xl mb-4">
              {parsed.categoryPlural} și în alte orașe
            </h2>
            <div className="flex flex-wrap gap-2">
              {siblingCities.map(cs => (
                <Link key={cs} to={`/marketplace/${parsed.categorySlug}-${cs}`}
                  className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-full px-3 py-1.5 transition flex items-center gap-1.5">
                  {parsed.categoryLabel} în {SEO_CITY_MAP[cs]}
                  <ArrowRight className="w-3 h-3 opacity-50" />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Internal-link block: sibling categories */}
        <section className="mb-10" data-testid="seo-sibling-categories">
          <h2 className="font-serif text-xl mb-4">
            Alte servicii{parsed.cityLabel ? ` în ${parsed.cityLabel}` : ""}
          </h2>
          <div className="flex flex-wrap gap-2">
            {siblingCategories.map(cs => (
              <Link key={cs} to={`/marketplace/${cs}${parsed.citySlug ? "-" + parsed.citySlug : ""}`}
                className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-full px-3 py-1.5 transition flex items-center gap-1.5">
                {SEO_CATEGORY_MAP[cs].plural}
                {parsed.cityLabel ? ` în ${parsed.cityLabel}` : ""}
                <ArrowRight className="w-3 h-3 opacity-50" />
              </Link>
            ))}
          </div>
        </section>

        {/* Internal-link block: relevant guides */}
        {relatedGuides.length > 0 && (
          <section className="mb-10" data-testid="seo-related-guides">
            <h2 className="font-serif text-xl mb-1">Înainte să angajezi, citește</h2>
            <p className="text-xs text-stone-500 mb-4">Ghiduri evergreen scrise de echipa PropManage.</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {relatedGuides.map(g => (
                <Link key={g.slug} to={`/ghiduri/${g.slug}`}
                  className="glass-strong rounded-2xl p-4 hover:bg-white/[0.06] transition group flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#d4ff3a]/10 flex items-center justify-center shrink-0">
                    <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-stone-100 group-hover:text-[#d4ff3a] transition truncate">{g.title}</div>
                    <div className="text-[11px] text-stone-500">Ghid PropManage</div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-stone-500 group-hover:text-[#d4ff3a] transition shrink-0" />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Bottom CTA */}
        <div className="glass-strong rounded-3xl p-8 sm:p-10 text-center" data-testid="seo-bottom-cta">
          <h2 className="font-serif text-3xl mb-3">Nu găsești ce cauți?</h2>
          <p className="text-stone-400 mb-6 max-w-xl mx-auto">
            Postează o cerere gratuit și primești 3-5 oferte de la {parsed.categoryPlural.toLowerCase()} verificați{cityPart} în 24h.
          </p>
          <Link to="/register" className="inline-block bg-[#d4ff3a] text-black px-8 py-3 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">
            Începe gratuit
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-16 py-8 px-6 text-center text-xs text-stone-500">
        © {new Date().getFullYear()} PropManage · operat de Vintage Furniture S.R.L. (CUI 35250247) · <Link to="/terms" className="hover:text-stone-300">Termeni</Link> · <Link to="/privacy" className="hover:text-stone-300">Confidențialitate</Link> · <Link to="/status" className="hover:text-stone-300">Status</Link>
      </footer>
    </div>
  );
};

export default MarketplaceLanding;
