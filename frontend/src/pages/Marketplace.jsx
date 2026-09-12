// Public Marketplace + 2FA Setup + Property Timeline
import React, { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import { Building2, Star, CheckCircle2, Search, Filter, ArrowLeft, Shield, QrCode, Copy, Check, Calendar, Wrench, AlertTriangle, CreditCard, MapPin } from "lucide-react";
import { useAuth, formatApiError } from "../auth";
import { useSEO } from "../hooks/useSEO";
import { PMCard, PMPillButton, PMChip, PMSectionHeader, PMEmptyState } from "../components/pm";
import { MarketplaceBenefitStrip } from "../components/pb/PbEverywhere";
import { EcosystemFlow } from "../components/ecosystem/EcosystemFlow";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ============= PUBLIC MARKETPLACE =============
export const PublicMarketplace = () => {
  const [specialists, setSpecialists] = useState([]);
  const [filters, setFilters] = useState({ category: "", verified_only: false, sort: "rating" });
  const [loading, setLoading] = useState(true);

  useSEO({
    title: filters.category
      ? `Specialiști ${filters.category} verificați · Marketplace PropManage`
      : "Marketplace specialiști verificați · PropManage",
    description: filters.category
      ? `Găsește cei mai buni specialiști ${filters.category} verificați pentru proprietatea ta. Recenzii reale, plăți escrow, garanție lucrare.`
      : "Descoperă peste 100 de specialiști verificați (instalatori, electricieni, designeri, zugravi) pentru proprietatea ta. Plăți escrow, recenzii reale, garanție lucrare.",
    canonical: filters.category
      ? `https://propmanage.ro/marketplace?category=${encodeURIComponent(filters.category)}`
      : "https://propmanage.ro/marketplace",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      "name": "Marketplace Specialiști PropManage",
      "url": "https://propmanage.ro/marketplace",
      "description": "Listă de specialiști verificați pentru proprietăți rezidențiale în România.",
      "isPartOf": { "@type": "WebSite", "name": "PropManage", "url": "https://propmanage.ro" },
      "breadcrumb": {
        "@type": "BreadcrumbList",
        "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Acasă", "item": "https://propmanage.ro/" },
          { "@type": "ListItem", "position": 2, "name": "Marketplace", "item": "https://propmanage.ro/marketplace" },
        ],
      },
    },
  });

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.verified_only) params.set("verified_only", "true");
    params.set("sort", filters.sort);
    setLoading(true);
    axios.get(`${API}/marketplace/specialists?${params}`)
      .then(r => setSpecialists(r.data))
      .catch(() => setSpecialists([]))
      .finally(() => setLoading(false));
  }, [filters]);

  // PPOS P3a-M5 — prezentare defensivă publică: statusurile de moderare nu se afișează niciodată
  const visibleSpecialists = specialists.filter(
    s => !["REJECTED", "SUSPENDED", "BLOCKED"].includes(String(s.tier || "").toUpperCase())
  );
  const PUBLIC_TIERS = ["VERIFIED", "ADVANCED", "PREMIUM", "TOP"];

  return (
    <div className="pm-page-bg">
      <header className="pm-topbar">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link to="/ghiduri" className="hidden sm:inline"><PMPillButton variant="ghost" size="sm">Ghiduri</PMPillButton></Link>
            <Link to="/login"><PMPillButton variant="primary" size="sm">Conectare</PMPillButton></Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="pm-fade-in">
          <PMChip variant="primary" className="mb-3">MARKETPLACE PROPMANAGE</PMChip>
          <h1 className="font-serif text-4xl sm:text-6xl tracking-tight mb-3" data-testid="mkt-title">Specialiști verificați</h1>
          <p className="text-stone-400 mb-6 max-w-xl">Descoperă cei mai buni profesioniști pentru proprietatea ta. Recenzii reale, plăți escrow, garanție lucrare.</p>
          <div className="pm-card-glass !p-4 mb-8" data-testid="mkt-ecosystem-flow">
            <EcosystemFlow dark compact activeKey="specialists" />
          </div>
        </div>

        <MarketplaceBenefitStrip />

        {/* Filters */}
        <div className="pm-card-glass !p-4 mb-6 flex flex-wrap gap-3 items-center pm-fade-in-delay-1">
          <select value={filters.category} onChange={e => setFilters({...filters, category: e.target.value})}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50" data-testid="mkt-cat">
            <option value="">Toate categoriile</option>
            <option value="hvac">HVAC</option>
            <option value="electric">Electric</option>
            <option value="plumbing">Sanitar</option>
            <option value="other">Altele</option>
          </select>
          <label className="flex items-center gap-2 text-sm cursor-pointer px-4 py-2 bg-white/5 border border-white/10 rounded-full hover:bg-white/10 transition-colors">
            <input type="checkbox" checked={filters.verified_only} onChange={e => setFilters({...filters, verified_only: e.target.checked})} className="rounded accent-[var(--pm-primary)]" data-testid="mkt-verified" />
            <CheckCircle2 className="w-4 h-4 text-[var(--pm-primary)]" />
            <span>Doar verificați</span>
          </label>
          <select value={filters.sort} onChange={e => setFilters({...filters, sort: e.target.value})}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm ml-auto focus:outline-none focus:border-[var(--pm-primary)]/50" data-testid="mkt-sort">
            <option value="rating">Cele mai bune ratinguri</option>
            <option value="reviews">Cele mai multe recenzii</option>
            <option value="recent">Cei mai noi</option>
          </select>
        </div>

        <div className="text-xs text-stone-500 mb-4">{loading ? "Se încarcă..." : `${visibleSpecialists.length} specialiști`}</div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 pm-fade-in-delay-2">
          {visibleSpecialists.map((s, i) => (
            <motion.div key={s.id}
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
              <PMCard className="hover:!border-[var(--pm-primary)]/30 transition-all group h-full flex flex-col" testid={`mkt-card-${s.id}`}>
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--pm-primary)] to-[var(--pm-primary-dim)] flex items-center justify-center font-bold text-black shrink-0 text-lg">
                    {s.name?.[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <div className="font-semibold truncate">{s.name}</div>
                      {s.verified && <CheckCircle2 className="w-4 h-4 text-[var(--pm-primary)] shrink-0 fill-[var(--pm-primary)]/20" />}
                    </div>
                    <div className="text-xs text-stone-400 capitalize">{s.specialty || "Specialist"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs mb-4 flex-wrap flex-1">
                  {s.trust?.trust_score != null && (
                    <div className="flex items-center gap-1 bg-[var(--pm-primary)]/10 border border-[var(--pm-primary)]/30 text-[var(--pm-primary)] px-2.5 py-1 rounded-full" data-testid={`mkt-trust-score-${s.id}`}>
                      <span className="font-black">Trust {s.trust.trust_score}</span>
                      <span className="opacity-70">/100</span>
                    </div>
                  )}
                  {(s.trust?.confirmed_jobs || 0) > 0 && (
                    <div className="flex items-center gap-1 bg-sky-500/15 border border-sky-500/30 text-sky-300 px-2.5 py-1 rounded-full" data-testid={`mkt-confirmed-${s.id}`}>
                      <span className="font-semibold">{s.trust.confirmed_jobs}</span>
                      <span className="opacity-70">lucrări confirmate</span>
                    </div>
                  )}
                  {(s.trust?.ambassadors || 0) > 0 && (
                    <div className="flex items-center gap-1 bg-violet-500/15 border border-violet-500/30 text-violet-300 px-2.5 py-1 rounded-full" data-testid={`mkt-ambassadors-${s.id}`}>
                      <span>🏅</span>
                      <span className="font-semibold">{s.trust.ambassadors}</span>
                      <span className="opacity-70">{s.trust.ambassadors === 1 ? "ambasador" : "ambasadori"}</span>
                    </div>
                  )}
                  {(s.trust?.community_value || 0) > 0 && (
                    <div className="flex items-center gap-1 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-2.5 py-1 rounded-full" data-testid={`mkt-community-value-${s.id}`}>
                      <span className="font-semibold">{s.trust.community_value} RON</span>
                      <span className="opacity-70">beneficii generate comunității</span>
                    </div>
                  )}
                  {s.trust?.rebook_show && (
                    <div className="flex items-center gap-1 bg-rose-500/15 border border-rose-500/30 text-rose-300 px-2.5 py-1 rounded-full" data-testid={`mkt-rebook-${s.id}`}>
                      <span>❤️</span>
                      <span className="font-semibold">{s.trust.rebook_pct}%</span>
                      <span className="opacity-70">ar angaja din nou</span>
                    </div>
                  )}
                  {(s.trust?.recommenders || 0) > 0 && (
                    <div className="flex items-center gap-1 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-2.5 py-1 rounded-full" data-testid={`mkt-recommenders-${s.id}`}>
                      <span className="font-semibold">{s.trust.recommenders}</span>
                      <span className="opacity-70">{s.trust.recommenders === 1 ? "proprietar recomandă" : "proprietari recomandă"}</span>
                    </div>
                  )}
                  {(s.reviews_count || 0) >= 1 ? (
                    <div className="flex items-center gap-1 bg-amber-500/15 border border-amber-500/30 text-amber-300 px-2.5 py-1 rounded-full">
                      <Star className="w-3 h-3 fill-current" />
                      <span className="font-semibold">{s.rating || "—"}</span>
                      <span className="opacity-70">({s.reviews_count})</span>
                    </div>
                  ) : (
                    <span className="px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-stone-400" data-testid={`mkt-new-${s.id}`}>Nou pe platformă</span>
                  )}
                  {PUBLIC_TIERS.includes(String(s.tier || "").toUpperCase()) && <PMChip variant="primary">{s.tier}</PMChip>}
                </div>
                <Link to={`/specialists/${s.id}`} className="block" data-testid={`mkt-view-${s.id}`}>
                  <PMPillButton variant="ghost" className="w-full">
                    Vezi profil
                  </PMPillButton>
                </Link>
              </PMCard>
            </motion.div>
          ))}
        </div>

        {specialists.length === 0 && !loading && (
          (filters.category || filters.verified_only) ? (
            <PMEmptyState
              icon={Search}
              title="Niciun specialist găsit"
              description="Încearcă să ajustezi filtrele sau revino mai târziu."
            />
          ) : (
            /* GBOS P0 — marketplace-ul nu arată niciodată „gol": early access onest */
            <div className="pm-card-glass !p-8 sm:!p-12 text-center" data-testid="mkt-early-access">
              <PMChip variant="primary" className="mb-4">EARLY ACCESS</PMChip>
              <h2 className="font-serif text-3xl sm:text-4xl mb-3">Construim rețeaua de încredere, oraș cu oraș</h2>
              <p className="text-stone-400 max-w-xl mx-auto mb-8">
                Primii specialiști intră pe platformă prin recomandările proprietarilor — nu prin reclame.
                Fiecare profil vine cu recenzii verificate din lucrări reale, plăți escrow și garanție.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link to="/register?role=specialist" data-testid="mkt-ea-specialist">
                  <PMPillButton variant="primary">Sunt specialist — vreau primele cereri</PMPillButton>
                </Link>
                <Link to="/register" data-testid="mkt-ea-owner">
                  <PMPillButton variant="ghost">Sunt proprietar — las prima cerere</PMPillButton>
                </Link>
              </div>
            </div>
          )
        )}

        {/* SEO internal-link block — surfaces all category/city landing pages */}
        <section className="mt-16 pt-10 border-t border-white/5" data-testid="mkt-seo-links">
          <h2 className="font-serif text-2xl mb-4">Caută după categorie și oraș</h2>
          <p className="text-stone-400 text-sm mb-6 max-w-2xl">
            Vezi specialiști verificați filtrați pe specialitate și oraș — pagini dedicate cu profile, recenzii și prețuri.
          </p>
          <div className="space-y-5">
            {[
              { cat: "electrician",            plural: "Electricieni" },
              { cat: "instalator",             plural: "Instalatori" },
              { cat: "hvac",                   plural: "Specialiști HVAC" },
              { cat: "design-interior",        plural: "Designeri interior" },
              { cat: "tamplar",                plural: "Tâmplari" },
              { cat: "zugrav",                 plural: "Zugravi" },
              { cat: "firma-curatenie",        plural: "Firme de curățenie" },
              { cat: "service-electrocasnice", plural: "Service electrocasnice" },
              { cat: "gradinar",               plural: "Grădinari" },
            ].map(({ cat, plural }) => (
              <div key={cat}>
                <Link to={`/marketplace/${cat}`} className="text-sm font-medium text-[#d4ff3a] hover:underline">
                  {plural} →
                </Link>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {[
                    ["bucuresti", "București"], ["cluj-napoca", "Cluj-Napoca"],
                    ["timisoara", "Timișoara"], ["iasi", "Iași"],
                    ["brasov", "Brașov"], ["constanta", "Constanța"],
                    ["sibiu", "Sibiu"], ["oradea", "Oradea"], ["craiova", "Craiova"], ["ploiesti", "Ploiești"],
                  ].map(([slug, name]) => (
                    <Link
                      key={slug}
                      to={`/marketplace/${cat}-${slug}`}
                      className="text-[11px] text-stone-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full px-2.5 py-1 transition"
                    >
                      {name}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};

// ============= 2FA SETUP MODAL =============
export const TwoFASetupModal = ({ onClose, currentlyEnabled }) => {
  const [step, setStep] = useState("intro"); // intro | setup | verify | disable
  const [qrData, setQrData] = useState(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const beginSetup = async () => {
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/auth/2fa/setup`);
      setQrData(data);
      setStep("setup");
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  const verify = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/auth/2fa/verify`, { code });
      setStep("done");
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  const disable = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/auth/2fa/disable`, { code });
      alert("2FA dezactivat");
      onClose(true);
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  const copySecret = () => {
    navigator.clipboard.writeText(qrData.secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6" onClick={() => onClose(false)}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-md w-full max-h-[90vh] overflow-auto no-scrollbar" onClick={e => e.stopPropagation()} data-testid="2fa-modal">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#d4ff3a]/15 flex items-center justify-center">
            <Shield className="w-4 h-4 text-[#d4ff3a]" />
          </div>
          <h2 className="font-serif text-2xl">Autentificare în 2 pași</h2>
        </div>

        {step === "intro" && !currentlyEnabled && (
          <>
            <p className="text-sm text-stone-400 mb-6">Adaugă un strat suplimentar de securitate contului tău. Vei avea nevoie de o aplicație authenticator (Google Authenticator, Authy, 1Password).</p>
            <button onClick={beginSetup} disabled={loading} className="w-full btn-accent py-3 rounded-xl text-sm font-medium" data-testid="2fa-start">
              {loading ? "..." : "Activează 2FA"}
            </button>
          </>
        )}

        {currentlyEnabled && step === "intro" && (
          <>
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 mb-4 text-sm text-emerald-300">
              ✓ 2FA este activ pe contul tău
            </div>
            <p className="text-sm text-stone-400 mb-4">Pentru a dezactiva 2FA, introdu codul curent din aplicația authenticator:</p>
            <input value={code} onChange={e => setCode(e.target.value)} placeholder="123456" maxLength={6}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-center text-2xl tracking-widest font-mono mb-4"
              data-testid="2fa-disable-code" />
            <button onClick={disable} disabled={loading || code.length !== 6} className="w-full bg-red-500/20 border border-red-500/40 text-red-300 py-3 rounded-xl text-sm font-medium disabled:opacity-50" data-testid="2fa-disable-btn">
              {loading ? "..." : "Dezactivează 2FA"}
            </button>
          </>
        )}

        {step === "setup" && qrData && (
          <>
            <p className="text-sm text-stone-400 mb-4">1. Scanează codul QR cu aplicația ta authenticator:</p>
            <div className="bg-white rounded-2xl p-4 flex items-center justify-center mb-4">
              <img src={qrData.qr_code} alt="QR" className="w-48 h-48" data-testid="2fa-qr" />
            </div>
            <p className="text-sm text-stone-400 mb-2">Sau introdu manual codul:</p>
            <div className="flex gap-2 mb-4">
              <input value={qrData.secret} readOnly className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono" />
              <button onClick={copySecret} className="px-3 bg-white/10 rounded-xl flex items-center gap-1 text-xs" data-testid="2fa-copy">
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                {copied ? "Copiat!" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-stone-400 mb-2">2. Introdu codul afișat în aplicație:</p>
            <input value={code} onChange={e => setCode(e.target.value)} placeholder="123456" maxLength={6}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-center text-2xl tracking-widest font-mono mb-4"
              data-testid="2fa-code" />
            <button onClick={verify} disabled={loading || code.length !== 6} className="w-full btn-accent py-3 rounded-xl text-sm font-medium disabled:opacity-50" data-testid="2fa-verify">
              {loading ? "..." : "Verifică și activează"}
            </button>
          </>
        )}

        {step === "done" && (
          <div className="text-center py-6">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mb-4">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h3 className="font-serif text-2xl mb-2">2FA activat!</h3>
            <p className="text-sm text-stone-400 mb-6">Contul tău este acum mult mai sigur.</p>
            <button onClick={() => onClose(true)} className="w-full btn-accent py-3 rounded-xl text-sm font-medium" data-testid="2fa-done">Gata</button>
          </div>
        )}
      </motion.div>
    </div>
  );
};

// ============= PROPERTY TIMELINE =============
const eventIcon = (type) => {
  switch (type) {
    case "request_created": return AlertTriangle;
    case "specialist_assigned": return Wrench;
    case "work_completed": return CheckCircle2;
    case "confirmed": return CreditCard;
    default: return Calendar;
  }
};
const eventColor = (type) => {
  switch (type) {
    case "request_created": return "amber";
    case "specialist_assigned": return "blue";
    case "work_completed": return "purple";
    case "confirmed": return "emerald";
    default: return "stone";
  }
};

export const PropertyTimelineModal = ({ propertyId, onClose }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    axios.get(`${API}/properties/${propertyId}/timeline`)
      .then(r => setData(r.data))
      .catch(() => setData({ events: [], property: null }));
  }, [propertyId]);

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 sm:p-8 max-w-2xl w-full max-h-[90vh] overflow-auto no-scrollbar" onClick={e => e.stopPropagation()} data-testid="timeline-modal">
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="text-xs uppercase tracking-wider text-stone-400 mb-1">Timeline proprietate</div>
            <h2 className="font-serif text-2xl">{data?.property?.name || "Se încarcă..."}</h2>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-white text-xl">×</button>
        </div>

        {!data && <div className="text-center py-8 text-stone-500">Se încarcă...</div>}
        {data && data.events.length === 0 && <div className="text-center py-12 text-stone-500 text-sm">Nicio activitate înregistrată încă</div>}

        <div className="relative pl-8">
          {/* Vertical line */}
          {data && data.events.length > 0 && <div className="absolute left-3 top-3 bottom-3 w-px bg-white/10" />}
          
          {data?.events.map((e, i) => {
            const Icon = eventIcon(e.type);
            const color = eventColor(e.type);
            return (
              <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                className="relative mb-6" data-testid={`timeline-event-${i}`}>
                <div className={`absolute -left-8 top-0 w-6 h-6 rounded-full bg-${color}-500/20 border-2 border-${color}-500/40 flex items-center justify-center`}>
                  <Icon className={`w-3 h-3 text-${color}-400`} />
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="font-medium text-sm">{e.title}</div>
                  <div className="text-xs text-stone-400 mt-0.5">{e.description}</div>
                  <div className="text-[10px] text-stone-500 mt-2">
                    {new Date(e.timestamp).toLocaleString("ro-RO", { dateStyle: "medium", timeStyle: "short" })}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
};
