import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import {
  ShieldCheck, BadgeCheck, FileText, Home, CalendarClock, Printer, ChevronDown,
  Sparkles, Lock, Ruler, DoorOpen, Flame, Layers, ArrowRight, CircleHelp,
} from "lucide-react";
import { initPassportTracking, trackPassport } from "../lib/passportTracker";
import { HouseHealthAxisSnapshot } from "../components/HouseHealthAxisCard";

const API = process.env.REACT_APP_BACKEND_URL;

const TYPE_LABEL = { apartment: "Apartament", house: "Casă", commercial: "Spațiu comercial", land: "Teren" };
const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString("ro-RO", { day: "numeric", month: "long", year: "numeric" }); } catch { return ""; } };

const ScoreRing = ({ value, label, sub, testid }) => (
  <div className="glass rounded-3xl p-5 text-center" data-testid={testid}>
    <div className="font-serif text-4xl font-medium" style={{ color: value >= 50 ? "#d4ff3a" : "#f5f5f4" }}>{value}<span className="text-lg text-stone-500">/100</span></div>
    <div className="mt-1 text-sm font-medium text-stone-200">{label}</div>
    <div className="mt-0.5 text-[11px] text-stone-500">{sub}</div>
  </div>
);

export default function PublicPassportPage() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [showTrust, setShowTrust] = useState(false);
  const [showAllHistory, setShowAllHistory] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/public/passport/${slug}`)
      .then(r => setData(r.data))
      .catch(() => setErr(true));
  }, [slug]);

  useEffect(() => {
    if (data?.slug) return initPassportTracking(data.slug);
  }, [data?.slug]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!data) return;
    document.title = `${data.property.name} — Pașaportul Casei | PropManage`;
    let m = document.querySelector('meta[name="description"]');
    if (!m) { m = document.createElement("meta"); m.name = "description"; document.head.appendChild(m); }
    m.content = `Profilul public de încredere al proprietății ${data.property.name}: documentație, istoric verificat și scoruri de încredere pe PropManage.`;
    let c = document.querySelector('link[rel="canonical"]');
    if (!c) { c = document.createElement("link"); c.rel = "canonical"; document.head.appendChild(c); }
    c.href = `${window.location.origin}/p/${data.slug}`;
    let ld = document.getElementById("passport-jsonld");
    if (!ld) { ld = document.createElement("script"); ld.type = "application/ld+json"; ld.id = "passport-jsonld"; document.head.appendChild(ld); }
    ld.textContent = JSON.stringify({
      "@context": "https://schema.org", "@type": "Accommodation",
      name: data.property.name, url: `${window.location.origin}/p/${data.slug}`,
      ...(data.property.surface ? { floorSize: { "@type": "QuantitativeValue", value: data.property.surface, unitCode: "MTK" } } : {}),
      ...(data.property.rooms ? { numberOfRooms: data.property.rooms } : {}),
      additionalProperty: [{ "@type": "PropertyValue", name: "Scor de încredere PropManage", value: `${data.scores.trust.score}/100` }],
    });
  }, [data]);

  if (err) return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 flex items-center justify-center p-8" data-testid="passport-not-found">
      <div className="text-center max-w-sm">
        <Lock className="w-10 h-10 mx-auto text-stone-600" />
        <h1 className="mt-4 font-serif text-2xl">Acest pașaport nu este public</h1>
        <p className="mt-2 text-sm text-stone-500">Proprietarul nu a activat încă profilul public al acestei proprietăți.</p>
        <Link to="/" className="mt-6 inline-block px-6 py-3 rounded-full bg-[#d4ff3a] text-black text-sm font-bold">Descoperă PropManage</Link>
      </div>
    </div>
  );
  if (!data) return <div className="min-h-screen bg-[#0a0a0b]" />;

  const p = data.property;
  const trust = data.scores.trust;
  const earned = data.badges.filter(b => b.earned);
  // PPOS P3a-M7: intrările consecutive identice se grupează; istoricul e colapsat la 5
  const groupedMilestones = [];
  (data.milestones || []).forEach((m) => {
    const last = groupedMilestones[groupedMilestones.length - 1];
    if (last && last.title === m.title && last.detail === m.detail) last.count += 1;
    else groupedMilestones.push({ ...m, count: 1 });
  });
  const visibleMilestones = showAllHistory ? groupedMilestones : groupedMilestones.slice(0, 5);
  const hl = data.document_highlights;
  const hlItems = hl ? [
    ["Planuri tehnice", hl.plans], ["Manuale", hl.manuals], ["Garanții", hl.warranties],
    ["Facturi & contracte", hl.invoices], ["Rapoarte tehnice", hl.reports], ["Fotografii", hl.photos],
  ].filter(([, n]) => n > 0) : [];

  return (
    <div className="grain min-h-screen bg-[#0a0a0b] text-stone-100 print:bg-white print:text-black">
      {/* mini-nav */}
      <nav className="flex items-center justify-between px-5 sm:px-10 py-4 print:hidden">
        <Link to="/" className="font-serif text-lg tracking-tight" data-testid="passport-logo">PropManage</Link>
        <div className="flex items-center gap-2">
          <button onClick={() => window.print()} className="p-2.5 rounded-full glass" title="Versiune printabilă" data-testid="passport-print">
            <Printer className="w-4 h-4" />
          </button>
          <Link to="/register" onClick={() => trackPassport(slug, "cta_click")} className="px-4 py-2.5 rounded-full bg-[#d4ff3a] text-black text-xs font-bold" data-testid="passport-viral-cta-top">
            Creează pașaportul casei tale
          </Link>
        </div>
      </nav>

      {/* Antet brandat — vizibil DOAR pe versiunea printabilă (pentru bancă/notar) */}
      <div className="hidden print:flex items-start justify-between border-b-2 border-slate-900 mx-8 pt-2 pb-3 mb-4" data-testid="passport-print-header">
        <div>
          <div className="font-serif text-2xl font-bold text-slate-900 leading-none">PropManage</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 mt-1">Pașaportul Casei · Profil de încredere</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-slate-900">{p.name}</div>
          {p.address && <div className="text-[11px] text-slate-500">{p.address}</div>}
          <div className="text-[10px] text-slate-500 mt-1">Emis: {fmtDate(new Date().toISOString())} · propmanage.ro/p/{data.slug}</div>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-5 pb-16">
        {/* hero */}
        <header className="mt-4" data-testid="passport-hero">
          {data.photo_url ? (
            <img src={`${API}${data.photo_url}`} alt={p.name} className="w-full h-52 sm:h-72 object-cover rounded-3xl border border-white/10" data-testid="passport-photo" />
          ) : (
            <div className="w-full h-40 sm:h-52 rounded-3xl border border-white/10 flex items-center justify-center" style={{ background: "linear-gradient(135deg, #14532d 0%, #052e16 100%)" }}>
              <Home className="w-12 h-12 text-lime-300/60" />
            </div>
          )}
          <div className="mt-5 flex items-start justify-between gap-4">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#d4ff3a]">Pașaportul Casei · Profil de încredere</div>
              <h1 className="mt-1.5 font-serif text-3xl sm:text-4xl font-medium tracking-tight" data-testid="passport-name">{p.name}</h1>
              {p.address && <div className="mt-1 text-sm text-stone-400" data-testid="passport-address">{p.address}</div>}
            </div>
            <div className="shrink-0 text-right print:hidden">
              <img src={`${API}/api/public/passport/${data.slug}/qr.png`} alt="QR pașaport" className="w-20 h-20 rounded-xl bg-white p-1" data-testid="passport-qr" />
              <div className="mt-1 text-[9px] text-stone-500">identitate QR permanentă</div>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-300" data-testid="passport-facts">
            <span className="glass px-3 py-1.5 rounded-full inline-flex items-center gap-1.5"><Home className="w-3.5 h-3.5 text-[#d4ff3a]" /> {TYPE_LABEL[p.type] || p.type}</span>
            {p.surface && <span className="glass px-3 py-1.5 rounded-full inline-flex items-center gap-1.5"><Ruler className="w-3.5 h-3.5 text-[#d4ff3a]" /> {p.surface} mp</span>}
            {p.rooms && <span className="glass px-3 py-1.5 rounded-full inline-flex items-center gap-1.5"><DoorOpen className="w-3.5 h-3.5 text-[#d4ff3a]" /> {p.rooms} camere</span>}
            {p.year_built && <span className="glass px-3 py-1.5 rounded-full inline-flex items-center gap-1.5"><CalendarClock className="w-3.5 h-3.5 text-[#d4ff3a]" /> construită în {p.year_built}</span>}
            {p.heating && <span className="glass px-3 py-1.5 rounded-full inline-flex items-center gap-1.5"><Flame className="w-3.5 h-3.5 text-[#d4ff3a]" /> {String(p.heating).replace(/_/g, " ")}</span>}
          </div>
          {data.last_updated && <div className="mt-2 text-[11px] text-stone-500" data-testid="passport-updated">Ultima actualizare: {fmtDate(data.last_updated)}</div>}
        </header>

        {/* scores */}
        {data.scores.completeness && (
          <section className="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-3" data-testid="passport-scores">
            <ScoreRing value={trust.score} label="Scor de încredere" sub="doar dovezi verificabile" testid="passport-trust-score" />
            <ScoreRing value={data.scores.completeness.score} label="Casă documentată" sub={`${data.scores.completeness.docs_count} documente în cartea casei`} testid="passport-completeness" />
            {data.scores.maintenance
              ? <ScoreRing value={data.scores.maintenance.score} label={data.scores.maintenance.label} sub={data.scores.maintenance.source} testid="passport-maintenance" />
              : <div className="glass rounded-3xl p-5 text-center hidden sm:block"><Sparkles className="w-6 h-6 mx-auto text-[#d4ff3a]" /><div className="mt-2 text-xs text-stone-400">Istoria acestei case se scrie pe PropManage</div></div>}
          </section>
        )}

        {/* House Health A→G — rezumat partajabil (progresul celor 7 capitole) */}
        {data.scores.completeness?.items && (
          <section className="mt-4" data-testid="passport-axis-public">
            <HouseHealthAxisSnapshot completeness={data.scores.completeness} theme="dark" />
          </section>
        )}

        {/* trust explainer */}
        <section className="mt-4 glass rounded-3xl p-5" data-testid="passport-trust-explainer">
          <button onClick={() => setShowTrust(!showTrust)} aria-expanded={showTrust} className="w-full flex items-center gap-2 text-left" data-testid="passport-trust-toggle">
            <CircleHelp className="w-4 h-4 text-[#d4ff3a] shrink-0" />
            <span className="flex-1 text-sm font-medium">De ce există acest scor?</span>
            <ChevronDown className={`w-4 h-4 text-stone-500 transition-transform ${showTrust ? "rotate-180" : ""}`} />
          </button>
          {showTrust && (
            <div className="mt-3 text-xs text-stone-400 leading-relaxed">
              <p>{trust.explanation}</p>
              <div className="mt-3 space-y-1.5">
                {trust.factors.map(f => (
                  <div key={f.id} className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${f.earned > 0 ? "bg-[#d4ff3a]" : "bg-stone-700"}`} />
                    <span className="flex-1 text-stone-300">{f.label}</span>
                    <span className="font-bold text-stone-400">{f.earned}/{f.max}</span>
                  </div>
                ))}
              </div>
              {trust.missing.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Ce ar crește scorul</div>
                  {trust.missing.map((m, i) => <div key={i} className="mt-1">+{m.gain} · {m.label} — {m.why}</div>)}
                </div>
              )}
            </div>
          )}
        </section>

        {/* badges */}
        <section className="mt-6" data-testid="passport-badges">
          <h2 className="text-base font-medium text-stone-200">Verificări</h2>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {data.badges.map(b => (
              <div key={b.id} className={`rounded-2xl p-3 border ${b.earned ? "border-[#d4ff3a]/30 bg-[#d4ff3a]/5" : "border-white/5 opacity-40"}`} data-testid={`passport-badge-${b.id}`}>
                {b.earned ? <BadgeCheck className="w-4 h-4 text-[#d4ff3a]" /> : <ShieldCheck className="w-4 h-4 text-stone-600" />}
                <div className="mt-1.5 text-[11px] font-medium text-stone-300 leading-tight">{b.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* design concept — intenție de amenajare (concept validat profesional, opt-in owner) */}
        {data.design_concept && (
          <section className="mt-6" data-testid="passport-design-concept">
            <h2 className="text-base font-medium text-stone-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#d4ff3a]" /> Concept de amenajare
            </h2>
            <div className="mt-3 glass rounded-3xl overflow-hidden border border-white/10">
              {data.design_concept.render_url && (
                <img
                  src={`${API}${data.design_concept.render_url}`}
                  alt="Concept de design validat"
                  className="w-full h-52 sm:h-64 object-cover"
                  data-testid="passport-concept-render"
                />
              )}
              <div className="p-5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                    <ShieldCheck className="w-3 h-3" /> Validat profesional
                  </span>
                  {data.design_concept.style && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-white/5 text-stone-300 border border-white/10">{data.design_concept.style}</span>
                  )}
                </div>
                {data.design_concept.title && <div className="mt-2 font-serif text-lg text-white">{data.design_concept.title}</div>}
                {data.design_concept.summary && <p className="mt-1 text-sm text-stone-400 leading-relaxed">{data.design_concept.summary}</p>}
                {(data.design_concept.palette || []).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {data.design_concept.palette.map((hex, i) => (
                      <span key={i} className="w-6 h-6 rounded-md border border-white/20" style={{ backgroundColor: hex }} />
                    ))}
                  </div>
                )}
                {data.design_concept.validated_by_name && (
                  <div className="mt-3 text-[11px] text-stone-500">Verificat de {data.design_concept.validated_by_name}{data.design_concept.validated_at ? ` · ${fmtDate(data.design_concept.validated_at)}` : ""}</div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* milestones */}
        {groupedMilestones.length > 0 && (
          <section className="mt-8" data-testid="passport-timeline">
            <h2 className="text-base font-medium text-stone-200">Istoricul casei</h2>
            <div className="mt-3 space-y-0">
              {visibleMilestones.map((m, i) => (
                <div key={i} className="flex gap-3 pb-4 relative">
                  {i < visibleMilestones.length - 1 && <div className="absolute left-[7px] top-5 bottom-0 w-px bg-white/10" />}
                  <span className="mt-1 w-3.5 h-3.5 rounded-full shrink-0 border-2 border-[#0a0a0b]" style={{ background: m.type === "work" ? "#d4ff3a" : "#57866b" }} />
                  <div>
                    <div className="text-sm font-medium text-stone-200">{m.title}{m.count > 1 ? <span className="ml-1.5 text-[10px] font-bold text-stone-500">×{m.count}</span> : null}</div>
                    <div className="text-[11px] text-stone-500">{m.detail} · {fmtDate(m.date)}</div>
                  </div>
                </div>
              ))}
            </div>
            {!showAllHistory && groupedMilestones.length > 5 && (
              <button onClick={() => setShowAllHistory(true)} data-testid="passport-timeline-more"
                className="mt-1 inline-flex items-center gap-1.5 px-4 py-2 rounded-full glass text-xs font-medium text-stone-300 hover:text-white transition-colors">
                Vezi tot istoricul ({groupedMilestones.length}) <ChevronDown className="w-3.5 h-3.5" />
              </button>
            )}
          </section>
        )}

        {/* document highlights */}
        {hlItems.length > 0 && (
          <section className="mt-6" data-testid="passport-highlights">
            <h2 className="text-base font-medium text-stone-200">Dovezi în cartea casei</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {hlItems.map(([label, n]) => (
                <span key={label} className="glass px-3.5 py-2 rounded-full text-xs text-stone-300 inline-flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#d4ff3a]" /> {label} · <b>{n}</b>
                </span>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-stone-500">Documentele complete rămân private și se transferă integral noului proprietar la vânzare.</p>
          </section>
        )}

        {/* buyer meaning + viral */}
        <section className="mt-10 rounded-3xl p-6 sm:p-8 text-black" style={{ background: "linear-gradient(135deg, #b3e600, #d4ff3a)" }} data-testid="passport-viral">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-black/60">Ce înseamnă acest pașaport</div>
          <h2 className="mt-2 font-serif text-2xl sm:text-3xl font-medium leading-snug">Această proprietate are identitate, istoric și dovezi — nu doar promisiuni.</h2>
          <p className="mt-2 text-sm text-black/70">Fiecare document, lucrare și garanție rămâne înregistrată permanent. Casa ta merită la fel.</p>
          <Link to="/register" onClick={() => trackPassport(slug, "cta_click")} className="mt-5 inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-black text-[#d4ff3a] text-sm font-bold" data-testid="passport-viral-cta">
            Creează gratuit pașaportul casei tale <ArrowRight className="w-4 h-4" />
          </Link>
        </section>

        <footer className="mt-8 text-center text-[11px] text-stone-600">
          Pașaport generat de <Link to="/" className="text-stone-400 underline">PropManage</Link> — cartea de service a casei tale · <Layers className="w-3 h-3 inline" /> date verificate prin Truth Engine
        </footer>
      </main>
    </div>
  );
}
