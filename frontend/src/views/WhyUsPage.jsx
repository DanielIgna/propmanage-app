import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ShieldCheck, Box, CheckCircle2, X, ArrowRight, Sparkles, FileText,
  TrendingUp, Calculator, Star, Award, Eye, Layers, Building2, ChevronDown,
  Zap, Heart, Quote
} from "lucide-react";
import { useDynamicSEO } from "@/lib/useDynamicSEO";

const SEO = ({ title, description }) => {
  React.useEffect(() => {
    document.title = title;
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "description";
      document.head.appendChild(meta);
    }
    meta.content = description;

    // Open Graph
    const setMeta = (property, content) => {
      let el = document.querySelector(`meta[property="${property}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute("property", property);
        document.head.appendChild(el);
      }
      el.content = content;
    };
    setMeta("og:title", title);
    setMeta("og:description", description);
    setMeta("og:type", "website");
  }, [title, description]);

  // Schema.org structured data
  React.useEffect(() => {
    const scriptId = "ldjson-de-ce-noi";
    let s = document.getElementById(scriptId);
    if (s) s.remove();
    const data = {
      "@context": "https://schema.org",
      "@type": "Service",
      "name": "PropManage Imobile Verificate",
      "description": description,
      "provider": {
        "@type": "Organization",
        "name": "PropManage",
        "url": "https://propmanage.ro"
      },
      "areaServed": { "@type": "Country", "name": "Romania" },
      "offers": {
        "@type": "Offer",
        "description": "Comision 2.5% la vânzare cu audit + Digital Twin incluse"
      }
    };
    s = document.createElement("script");
    s.type = "application/ld+json";
    s.id = scriptId;
    s.text = JSON.stringify(data);
    document.head.appendChild(s);
  }, [description]);

  return null;
};

const FAQ_ITEMS = [
  {
    q: "Cum garantezi că un imobil este verificat?",
    a: "Fiecare imobil trece prin 4 gate-uri obligatorii: (1) audit tehnic complet realizat de specialiști acreditați, (2) Digital Twin 3D al imobilului, (3) minimum 90% recomandări acceptate și implementate de proprietar, (4) aprobare manuală de echipa noastră. Niciun imobil nu este listat fără aceste verificări.",
  },
  {
    q: "De ce ar plăti cineva comision dacă pune anunț gratis pe altă platformă?",
    a: "Pentru că un imobil cu audit + Digital Twin se vinde MAI REPEDE și la un PREȚ MAI MARE. Cumpărătorii știu exact ce cumpără (zero surprize) → încredere → ofertă apropiată de prețul cerut. Plus, scoți costul auditului din comision la finalizarea vânzării.",
  },
  {
    q: "Cât durează tot procesul, de la audit la listare?",
    a: "În medie 7-10 zile lucrătoare: 1-2 zile programare audit, 2-3 zile raport + recomandări, 3-5 zile pentru Digital Twin. Pentru imobile urgente avem opțiune express (3-4 zile).",
  },
  {
    q: "Ce se întâmplă cu Digital Twin după vânzare?",
    a: "Devine proprietatea noului proprietar. Îl poate folosi pentru renovări, decorări, sau ca portofoliu de portofoliu pentru închirieri ulterioare. Includem și manualul tehnic complet al imobilului.",
  },
  {
    q: "Am găsit deja un imobil pe altă platformă. Mă puteți ajuta cu auditul?",
    a: "Da! Avem flow special 'Audit pentru imobil din altă platformă' — programăm auditul + creăm Digital Twin pentru orice imobil, indiferent unde l-ai găsit. Te ajută să iei o decizie informată înainte de a-ți face o ofertă.",
  },
];

const TESTIMONIALS = [
  {
    name: "Mihaela R.",
    role: "Proprietar · Aviatorilor",
    quote: "Vândut în 11 zile la prețul cerut. Cumpărătorul a venit deja convins după turul 3D, fără 5 vizionări inutile.",
    rating: 5,
  },
  {
    name: "Bogdan T.",
    role: "Cumpărător · Pipera",
    quote: "Am evitat o gafă de 60.000 € — raportul de audit a descoperit probleme la fundație pe care vânzătorul nu le menționa.",
    rating: 5,
  },
  {
    name: "Andreea S.",
    role: "Investitor real-estate",
    quote: "Cel mai bun produs din piața RO. Trust Score-ul îmi spune în 3 secunde dacă merită vizionarea fizică.",
    rating: 5,
  },
];

const COMPARISON_ROWS = [
  { feat: "Verificare tehnică a imobilului", us: true, them: false, note_us: "Audit complet · 30+ puncte", note_them: "Doar declarația proprietarului" },
  { feat: "Tur 3D Digital Twin", us: true, them: false, note_us: "Inclus în fiecare listing", note_them: "Doar fotografii statice" },
  { feat: "Raport audit PDF disponibil", us: true, them: false, note_us: "Public, descărcabil", note_them: "Inexistent" },
  { feat: "Comision vânzare", us: "2.5%", them: "5–6%", note_us: "Cu Twin bonus = ~2%", note_them: "Standard piață" },
  { feat: "Cumpărători preverificați", us: true, them: false, note_us: "Cerere structurată", note_them: "Apel direct fără filtru" },
  { feat: "Trust Score per imobil", us: "A+ / A / B / C", them: "—", note_us: "Calculat automat", note_them: "N/A" },
  { feat: "Recomandări upgrade preimplementate", us: true, them: false, note_us: "Min. 90% acceptate", note_them: "N/A" },
  { feat: "Servicii post-vânzare incluse", us: true, them: false, note_us: "Mutare, renovare, design", note_them: "Doar tranzacția" },
  { feat: "Volum listings", us: "Sute, premium", them: "Sute de mii, mixt", note_us: "Calitate selectată", note_them: "Cantitate" },
  { feat: "Timp mediu vânzare", us: "~14 zile", them: "~70 zile", note_us: "Cumpărători hotărâți", note_them: "Multe vizionări" },
];

const ComparisonRow = ({ row, idx }) => {
  const usValue = row.us === true ? <CheckCircle2 className="w-5 h-5 text-[#d4ff3a]" /> : row.us === false ? <X className="w-5 h-5 text-red-400" /> : <span className="font-semibold text-[#d4ff3a]">{row.us}</span>;
  const themValue = row.them === true ? <CheckCircle2 className="w-5 h-5 text-[#d4ff3a]" /> : row.them === false ? <X className="w-5 h-5 text-red-400" /> : <span className="font-semibold text-stone-300">{row.them}</span>;
  return (
    <motion.tr
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: idx * 0.04 }}
      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`comparison-row-${idx}`}
    >
      <td className="py-4 px-4 md:px-6 align-top">
        <div className="font-medium text-sm md:text-base text-white">{row.feat}</div>
      </td>
      <td className="py-4 px-4 md:px-6 text-center align-top bg-[#d4ff3a]/[0.04]">
        <div className="flex items-center justify-center mb-1">{usValue}</div>
        <div className="text-[10px] md:text-xs text-stone-400">{row.note_us}</div>
      </td>
      <td className="py-4 px-4 md:px-6 text-center align-top">
        <div className="flex items-center justify-center mb-1">{themValue}</div>
        <div className="text-[10px] md:text-xs text-stone-500">{row.note_them}</div>
      </td>
    </motion.tr>
  );
};

const SavingsCalculator = () => {
  const [price, setPrice] = useState(350000);
  const ourCommission = useMemo(() => price * 0.025, [price]);
  const theirCommission = useMemo(() => price * 0.055, [price]);
  const savings = useMemo(() => theirCommission - ourCommission, [theirCommission, ourCommission]);
  const fmt = (n) => new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(n);

  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 md:p-10" data-testid="savings-calculator">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 flex items-center justify-center">
          <Calculator className="w-6 h-6 text-[#d4ff3a]" />
        </div>
        <div>
          <h3 className="font-serif text-2xl md:text-3xl">Cât economisești cu noi?</h3>
          <p className="text-xs md:text-sm text-stone-400 mt-1">Comparație directă comision 2.5% (PropManage) vs 5.5% (medie piață)</p>
        </div>
      </div>

      <div className="mb-6">
        <label className="text-xs text-stone-400 uppercase tracking-wider">Preț estimat imobil (RON)</label>
        <input
          type="range"
          min="50000"
          max="2000000"
          step="10000"
          value={price}
          onChange={e => setPrice(Number(e.target.value))}
          className="w-full mt-3 accent-[#d4ff3a]"
          data-testid="calc-price-slider"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-stone-500">50.000 RON</span>
          <span className="font-serif text-3xl text-[#d4ff3a]" data-testid="calc-price-value">{fmt(price)} RON</span>
          <span className="text-xs text-stone-500">2.000.000 RON</span>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-white/5 rounded-2xl p-5 text-center">
          <div className="text-xs text-stone-400 uppercase tracking-wider mb-2">Comision standard piață (5.5%)</div>
          <div className="font-serif text-3xl text-red-300 mb-1" data-testid="calc-them">{fmt(theirCommission)}</div>
          <div className="text-xs text-stone-500">RON pierdere</div>
        </div>
        <div className="bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 rounded-2xl p-5 text-center">
          <div className="text-xs text-[#d4ff3a] uppercase tracking-wider mb-2">Comision PropManage (2.5%)</div>
          <div className="font-serif text-3xl text-[#d4ff3a] mb-1" data-testid="calc-us">{fmt(ourCommission)}</div>
          <div className="text-xs text-stone-400">RON cu tot serviciul inclus</div>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-5 text-center">
          <div className="text-xs text-emerald-300 uppercase tracking-wider mb-2">Economisești</div>
          <div className="font-serif text-3xl text-emerald-300 mb-1" data-testid="calc-savings">{fmt(savings)}</div>
          <div className="text-xs text-stone-400">RON · în plus în buzunarul tău</div>
        </div>
      </div>

      <Link to="/imobile-verificate/sell" className="mt-6 pm-btn pm-btn-primary pm-btn-lg w-full justify-center" data-testid="calc-cta-sell">
        Vinde-ți imobilul cu noi · Începe acum <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
};

const FAQItem = ({ q, a, idx }) => {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div className="border-b border-white/5" data-testid={`faq-item-${idx}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between text-left py-5 group"
        data-testid={`faq-toggle-${idx}`}
      >
        <span className="font-serif text-lg md:text-xl group-hover:text-[#d4ff3a] transition-colors">{q}</span>
        <ChevronDown className={`w-5 h-5 text-stone-400 transition-transform ${open ? "rotate-180 text-[#d4ff3a]" : ""}`} />
      </button>
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="pb-5 text-sm text-stone-300 leading-relaxed"
        >
          {a}
        </motion.div>
      )}
    </div>
  );
};

export const WhyUsPage = () => {
  useDynamicSEO("whyus", {
    title: "De ce PropManage · Imobile cu Audit + Digital Twin · Comision 2.5%",
    description: "O platformă imobiliară unde fiecare imobil are audit tehnic + Digital Twin obligatorii. Comision 2.5%."
  });
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <SEO
        title="De ce PropManage · Imobile cu Audit + Digital Twin · Comision 2.5%"
        description="O platformă imobiliară unde fiecare imobil are audit tehnic + Digital Twin obligatorii. Comision 2.5%. Cumpără cu încredere. Vinde cu credibilitate."
      />

      {/* HERO */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 dotted-bg opacity-30" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#d4ff3a] blur-[170px] opacity-10" />
        <div className="max-w-6xl mx-auto relative">
          <Link to="/" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-6">
            ← Înapoi la PropManage
          </Link>
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full mb-8" data-testid="hero-badge">
            <Sparkles className="w-3.5 h-3.5 text-[#d4ff3a]" />
            <span className="text-xs tracking-wide text-stone-300">O abordare diferită pentru piața imobiliară</span>
          </div>
          <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl tracking-tight leading-[0.9] mb-8 max-w-5xl" data-testid="why-hero-title">
            Facem lucrurile <span className="italic gradient-text">altfel</span>.
          </h1>
          <p className="text-base md:text-xl text-stone-400 max-w-3xl mb-10 leading-relaxed">
            Piața imobiliară din România are deja multe opțiuni. Noi nu am vrut să fim încă una.
            <strong className="text-white"> Am construit un model diferit</strong>: o platformă unde fiecare imobil
            trece prin audit tehnic și are Digital Twin 3D. Mai puține surprize. Mai multă încredere.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link to="/imobile-verificate" className="pm-btn pm-btn-primary pm-btn-lg" data-testid="hero-cta-browse">
              <Building2 className="w-4 h-4" /> Vezi imobile verificate
            </Link>
            <Link to="/imobile-verificate/sell" className="pm-btn pm-btn-secondary pm-btn-lg" data-testid="hero-cta-sell">
              <ArrowRight className="w-4 h-4" /> Vinde-ți imobilul
            </Link>
          </div>
        </div>
      </section>

      {/* 3 PILLARS */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-serif text-4xl md:text-5xl mb-3 text-center">Ce face <span className="italic gradient-text">PropManage</span> aparte</h2>
          <p className="text-center text-sm md:text-base text-stone-400 mb-14 max-w-2xl mx-auto">Un model fundamental nou, nu o variație a celor existente.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: ShieldCheck, color: "lime",
                t: "Verificat sau nu listat",
                d: "Niciun imobil nu apare public fără audit tehnic complet realizat de specialiștii noștri. Zero anunțuri necalificate.",
                stat: "100%", statLabel: "imobile auditate"
              },
              {
                icon: Box, color: "cyan",
                t: "Tur 3D obligatoriu",
                d: "Digital Twin pentru fiecare imobil. Cumpărătorii văd exact ce primesc înainte de prima vizionare fizică.",
                stat: "100%", statLabel: "imobile cu Twin"
              },
              {
                icon: TrendingUp, color: "emerald",
                t: "Comision avantajos",
                d: "2.5% în loc de 5-6% standard în piață. Iar costul Digital Twin se scade din comision la finalizare = practic gratis.",
                stat: "~50%", statLabel: "economie comision"
              },
            ].map((p, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-[#0e0e10] border border-white/10 rounded-3xl p-8 hover:border-[#d4ff3a]/30 transition-colors"
                data-testid={`pillar-${i}`}
              >
                <div className={`w-14 h-14 rounded-2xl bg-${p.color}-500/10 border border-${p.color}-500/30 flex items-center justify-center mb-6`}>
                  <p.icon className={`w-6 h-6 text-${p.color}-400`} />
                </div>
                <h3 className="font-serif text-2xl mb-3">{p.t}</h3>
                <p className="text-sm text-stone-400 leading-relaxed mb-6">{p.d}</p>
                <div className="pt-5 border-t border-white/5">
                  <div className="font-serif text-4xl text-[#d4ff3a]">{p.stat}</div>
                  <div className="text-xs text-stone-500 mt-1">{p.statLabel}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* COMPARISON TABLE */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-serif text-4xl md:text-5xl mb-3 text-center">Ce primești <span className="italic gradient-text">la noi</span></h2>
          <p className="text-center text-sm md:text-base text-stone-400 mb-12 max-w-2xl mx-auto">10 elemente care fac diferența. Tu alegi ce contează pentru tine.</p>
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl overflow-hidden">
            <table className="w-full" data-testid="comparison-table">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.02]">
                  <th className="py-4 px-4 md:px-6 text-left text-xs uppercase tracking-wider text-stone-500">Element</th>
                  <th className="py-4 px-4 md:px-6 text-center bg-[#d4ff3a]/[0.08]">
                    <div className="font-serif text-base md:text-lg text-[#d4ff3a]">PropManage</div>
                    <div className="text-[10px] text-stone-400">Imobile Verificate</div>
                  </th>
                  <th className="py-4 px-4 md:px-6 text-center">
                    <div className="font-serif text-base md:text-lg text-stone-300">Platforme clasice</div>
                    <div className="text-[10px] text-stone-500">model anunțuri standard</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_ROWS.map((r, i) => (
                  <ComparisonRow key={i} row={r} idx={i} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* SAVINGS CALCULATOR */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-4xl mx-auto">
          <SavingsCalculator />
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-serif text-4xl md:text-5xl mb-3 text-center">Ce spun cei care <span className="italic gradient-text">au folosit</span> platforma</h2>
          <p className="text-center text-sm md:text-base text-stone-400 mb-12">Lucrăm cu cumpărători hotărâți și proprietari serioși.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6"
                data-testid={`testimonial-${i}`}
              >
                <Quote className="w-6 h-6 text-[#d4ff3a]/40 mb-3" />
                <p className="text-sm text-stone-200 leading-relaxed mb-5 italic">"{t.quote}"</p>
                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                  <div>
                    <div className="font-medium text-sm">{t.name}</div>
                    <div className="text-xs text-stone-400">{t.role}</div>
                  </div>
                  <div className="flex gap-0.5">
                    {[...Array(t.rating)].map((_, idx) => (
                      <Star key={idx} className="w-3.5 h-3.5 text-[#d4ff3a] fill-[#d4ff3a]" />
                    ))}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-serif text-4xl md:text-5xl mb-3 text-center">Întrebări <span className="italic gradient-text">frecvente</span></h2>
          <p className="text-center text-sm md:text-base text-stone-400 mb-12">Răspunsurile pe care le cauți, înainte să te decizi.</p>
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl px-6 py-2">
            {FAQ_ITEMS.map((item, i) => (
              <FAQItem key={i} q={item.q} a={item.a} idx={i} />
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="px-6 py-24 border-t border-white/5">
        <div className="max-w-5xl mx-auto text-center relative">
          <div className="absolute inset-0 dotted-bg opacity-30" />
          <Award className="w-12 h-12 text-[#d4ff3a] mx-auto mb-6 relative" />
          <h2 className="font-serif text-4xl md:text-6xl mb-6 relative">
            Gata să cumperi <span className="italic gradient-text">altfel</span>?
          </h2>
          <p className="text-base md:text-lg text-stone-400 max-w-2xl mx-auto mb-10 relative">
            Răsfoiește imobile verificate sau înscrie-ți proprietatea pentru o vânzare credibilă.
            Niciun risc — auditul + Twin se plătesc doar dacă listezi.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center relative">
            <Link to="/imobile-verificate" className="pm-btn pm-btn-primary pm-btn-lg" data-testid="final-cta-browse">
              <Eye className="w-4 h-4" /> Explorează imobile verificate
            </Link>
            <Link to="/imobile-verificate/sell" className="pm-btn pm-btn-secondary pm-btn-lg" data-testid="final-cta-sell">
              <Building2 className="w-4 h-4" /> Vinde-ți imobilul
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default WhyUsPage;
