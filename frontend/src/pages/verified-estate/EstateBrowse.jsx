import React, { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Building2, MapPin, Bed, Maximize2, ShieldCheck, Box, ArrowRight,
  Search, Sparkles, ExternalLink, X, CheckCircle2, LayoutGrid, Map as MapIcon
} from "lucide-react";
import axios from "axios";
import { EstateMapView } from "./EstateMapView";
import { useDynamicSEO } from "@/lib/useDynamicSEO";
import { EcosystemFlow } from "@/components/ecosystem/EcosystemFlow";
import { ServiceDetailModal } from "@/components/ecosystem/ServiceDetailModal";
import { NextStep } from "@/components/ecosystem/NextStep";

const API = process.env.REACT_APP_BACKEND_URL;

const formatPrice = (ron) => {
  if (!ron) return "—";
  return new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(ron) + " RON";
};

const formatEur = (eur) => {
  if (eur == null) return null;
  return "≈ " + new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(eur) + " EUR";
};

const fmtRateDate = (d) => (d ? d.split("-").reverse().join(".") : "");

const VerifiedBadge = ({ size = "md" }) => (
  <div
    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#d4ff3a]/15 border border-[#d4ff3a]/40 text-[#d4ff3a] ${size === "lg" ? "text-sm" : "text-[10px]"} font-semibold tracking-wide`}
    data-testid="verified-badge"
  >
    <ShieldCheck className={size === "lg" ? "w-4 h-4" : "w-3 h-3"} />
    <span>VERIFIED TWIN</span>
  </div>
);

const ExternalAuditModal = ({ open, onClose }) => {
  const [form, setForm] = useState({
    external_listing_url: "",
    property_address: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/verified-estate/external-audit-request`, form);
      setDone(true);
    } catch (err) {
      alert(err?.response?.data?.detail || "Eroare la trimitere.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur flex items-center justify-center p-4" data-testid="external-audit-modal">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[#0e0e10] border border-white/10 rounded-3xl max-w-lg w-full p-8 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-start justify-between mb-6">
          <div>
            <h3 className="font-serif text-2xl mb-1">Solicită audit & Digital Twin</h3>
            <p className="text-sm text-stone-400">Pentru un imobil identificat pe altă platformă</p>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-white" data-testid="ext-audit-close"><X className="w-5 h-5" /></button>
        </div>
        {done ? (
          <div className="text-center py-8">
            <CheckCircle2 className="w-14 h-14 text-[#d4ff3a] mx-auto mb-4" />
            <h4 className="font-serif text-xl mb-2">Cerere primită ✓</h4>
            <p className="text-sm text-stone-400 mb-6">Echipa noastră îți va contacta în maxim 24 de ore pentru a programa auditul.</p>
            <button onClick={onClose} className="btn-accent px-6 py-2.5 rounded-full text-sm" data-testid="ext-audit-done">Închide</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-wider">Link imobil extern *</label>
              <input required type="url" placeholder="https://..." value={form.external_listing_url} onChange={e => setForm({ ...form, external_listing_url: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="ext-audit-url" />
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-wider">Adresă proprietate *</label>
              <input required value={form.property_address} onChange={e => setForm({ ...form, property_address: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="ext-audit-address" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-stone-400 uppercase tracking-wider">Nume *</label>
                <input required value={form.contact_name} onChange={e => setForm({ ...form, contact_name: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="ext-audit-name" />
              </div>
              <div>
                <label className="text-xs text-stone-400 uppercase tracking-wider">Telefon</label>
                <input value={form.contact_phone} onChange={e => setForm({ ...form, contact_phone: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="ext-audit-phone" />
              </div>
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-wider">Email *</label>
              <input required type="email" value={form.contact_email} onChange={e => setForm({ ...form, contact_email: e.target.value })} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="ext-audit-email" />
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-wider">Notițe</label>
              <textarea rows={3} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Ex: vreau să cumpăr, am buget până la 200.000 RON" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm resize-none" data-testid="ext-audit-notes" />
            </div>
            <button type="submit" disabled={submitting} className="w-full btn-accent py-3 rounded-full font-medium mt-2 disabled:opacity-50" data-testid="ext-audit-submit">
              {submitting ? "Se trimite..." : "Trimite cererea"}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
};

const TrustBadge = ({ score }) => {
  const cls = score === "A+" ? "pm-trust-A-plus" : score === "A" ? "pm-trust-A" : score === "B" ? "pm-trust-B" : "pm-trust-C";
  return <span className={`pm-trust-badge ${cls}`} data-testid="trust-badge">Trust {score}</span>;
};

const ListingCard = ({ item }) => (
  <Link
    to={`/imobile-verificate/${item.id}`}
    className="group relative bg-[#0e0e10] border border-white/10 rounded-3xl overflow-hidden hover:border-[#d4ff3a]/40 transition-all"
    data-testid={`listing-card-${item.id}`}
  >
    <div className="aspect-[4/3] relative overflow-hidden bg-gradient-to-br from-stone-900 to-stone-800">
      {item.cover_image_url ? (
        <img src={item.cover_image_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-stone-700"><Building2 className="w-20 h-20" /></div>
      )}
      <div className="absolute top-3 left-3 flex flex-col gap-1.5">
        <VerifiedBadge />
        {item.trust_score && <TrustBadge score={item.trust_score} />}
      </div>
      <div className="absolute top-3 right-3 flex flex-col gap-1.5 items-end">
        <div className="bg-black/60 backdrop-blur px-2.5 py-1 rounded-full flex items-center gap-1 text-[10px] text-stone-200">
          <Box className="w-3 h-3" /> 3D Twin
        </div>
        {item.transaction_type && (
          <div className={`px-2.5 py-1 rounded-full text-[10px] font-semibold ${item.transaction_type === "rent" ? "bg-cyan-500/20 text-cyan-300" : "bg-violet-500/20 text-violet-300"}`}>
            {item.transaction_type === "rent" ? "Închiriere" : "Vânzare"}
          </div>
        )}
      </div>
    </div>
    <div className="p-5">
      <div className="flex items-center gap-1.5 text-xs text-stone-400 mb-2">
        <MapPin className="w-3 h-3" />{item.city} {item.address ? `· ${item.address}` : ""}
      </div>
      <h3 className="font-serif text-xl mb-3 leading-snug line-clamp-2 group-hover:text-[#d4ff3a] transition-colors">{item.title}</h3>
      <div className="flex items-center justify-between text-xs text-stone-400 mb-4">
        <span className="flex items-center gap-1"><Bed className="w-3.5 h-3.5" /> {item.rooms} cam.</span>
        <span className="flex items-center gap-1"><Maximize2 className="w-3.5 h-3.5" /> {item.surface_sqm} m²</span>
        <span className="flex items-center gap-1"><Sparkles className="w-3.5 h-3.5" /> recomandări {item.recommendations_pct}%</span>
      </div>
      <div className="flex items-center justify-between pt-4 border-t border-white/5">
        <div>
          <div className="text-[10px] text-stone-500 uppercase tracking-wider">Preț</div>
          <div className="font-serif text-2xl">{formatPrice(item.price_ron)}</div>
          {item.price_eur != null && (
            <div className="text-xs text-stone-400" data-testid={`estate-eur-${item.id}`}
              title={item.exchange_rate_date ? `Calculat la cursul BNR din ${fmtRateDate(item.exchange_rate_date)}` : ""}>
              {formatEur(item.price_eur)}
            </div>
          )}
        </div>
        <div className="text-[#d4ff3a] flex items-center gap-1 text-xs">
          Detalii <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
        </div>
      </div>
    </div>
  </Link>
);

export const EstateBrowse = () => {
  useDynamicSEO("estate", {
    title: "Imobile Verificate — Case și Apartamente Verificate cu Audit Tehnic | PropManage",
    description: "Imobile verificate cu audit tehnic complet și Digital Twin: case de vânzare verificate și apartamente verificate, anunțuri imobiliare cu audit tehnic și proprietăți verificate digital twin. Cumperi cu încredere, vinzi cu credibilitate.",
  });
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCity, setFilterCity] = useState("");
  const [filterRooms, setFilterRooms] = useState("");
  const [filterPriceMax, setFilterPriceMax] = useState("");
  const [filterTransaction, setFilterTransaction] = useState("");
  const [showExtModal, setShowExtModal] = useState(false);
  const [detailKind, setDetailKind] = useState(null);
  const [viewMode, setViewMode] = useState("grid"); // grid | map

  useEffect(() => {
    let active = true;
    setLoading(true);
    const params = {};
    if (filterCity) params.city = filterCity;
    if (filterRooms) params.rooms = Number(filterRooms);
    if (filterPriceMax) params.price_max = Number(filterPriceMax);
    if (filterTransaction) params.transaction_type = filterTransaction;
    axios.get(`${API}/api/verified-estate/listings`, { params })
      .then(r => { if (active) setItems(r.data?.items || []); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [filterCity, filterRooms, filterPriceMax, filterTransaction]);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      {/* Hero */}
      <section className="relative pt-32 pb-16 px-6 overflow-hidden">
        <div className="absolute inset-0 dotted-bg opacity-30" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full bg-[#d4ff3a] blur-[150px] opacity-10" />
        <div className="max-w-7xl mx-auto relative">
          <Link to="/" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-6">
            ← Înapoi la PropManage
          </Link>
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full" data-testid="estate-hero-badge">
              <ShieldCheck className="w-3.5 h-3.5 text-[#d4ff3a]" />
              <span className="text-xs tracking-wide text-stone-300">Imobile Verificate · 100% cu Digital Twin</span>
            </div>
          </div>
          <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl tracking-tight leading-[0.95] mb-6 max-w-5xl" data-testid="estate-hero-title">
            Imobile <span className="italic gradient-text">Verificate</span>.<br />
            Zero surprize.
          </h1>
          <p className="text-lg text-stone-400 max-w-2xl mb-6">
            <strong className="text-white">Case de vânzare verificate</strong> și <strong className="text-white">apartamente verificate</strong>: fiecare imobil listat aici a trecut prin <strong className="text-white">audit tehnic complet</strong>,
            are <strong className="text-white">Digital Twin</strong> propriu și a obținut minimum
            <strong className="text-white"> 90% recomandări acceptate</strong> de proprietar.
            Anunțuri imobiliare cu audit tehnic și proprietăți verificate digital twin — cumperi cu încredere, vinzi cu credibilitate.
          </p>
          <div className="flex flex-wrap gap-2 mb-8 text-xs">
            <button onClick={() => setDetailKind("audit")} className="px-3.5 py-1.5 rounded-full border border-white/15 text-stone-300 hover:border-[#d4ff3a]/60 hover:text-white font-bold transition-colors" data-testid="estate-audit-details">
              Ce înseamnă auditul? →
            </button>
            <button onClick={() => setDetailKind("twin")} className="px-3.5 py-1.5 rounded-full border border-white/15 text-stone-300 hover:border-[#d4ff3a]/60 hover:text-white font-bold transition-colors" data-testid="estate-twin-details">
              Ce conține Digital Twin? →
            </button>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link to="/imobile-verificate/sell" className="btn-accent px-8 py-3.5 rounded-full font-medium inline-flex items-center justify-center gap-2" data-testid="estate-sell-cta">
              <Building2 className="w-4 h-4" /> Vinde-ți imobilul cu noi
            </Link>
            <button onClick={() => setShowExtModal(true)} className="glass px-8 py-3.5 rounded-full font-medium inline-flex items-center justify-center gap-2 hover:bg-white/10 transition-colors" data-testid="estate-external-cta">
              <ExternalLink className="w-4 h-4" /> Audit pentru imobil din altă platformă
            </button>
          </div>
          <div className="mt-10 p-5 rounded-3xl bg-white/[0.03] border border-white/10" data-testid="estate-ecosystem-flow">
            <EcosystemFlow dark compact activeKey="twin_update" />
          </div>
        </div>
      </section>

      {/* Filters */}
      <section className="px-6 py-8 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          {/* Sale/Rent Toggle */}
          <div className="inline-flex bg-white/5 rounded-full p-1 mb-4" data-testid="transaction-toggle">
            {[
              { v: "", l: "Toate" },
              { v: "sale", l: "Vânzare" },
              { v: "rent", l: "Închiriere" },
            ].map(opt => (
              <button
                key={opt.v}
                onClick={() => setFilterTransaction(opt.v)}
                className={`px-4 py-1.5 text-xs font-medium rounded-full transition-colors ${filterTransaction === opt.v ? "bg-[#d4ff3a] text-black" : "text-stone-400 hover:text-white"}`}
                data-testid={`toggle-${opt.v || "all"}`}
              >
                {opt.l}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="relative md:col-span-2">
              <Search className="w-4 h-4 text-stone-500 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Caută după oraș (ex: București)"
                value={filterCity}
                onChange={e => setFilterCity(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl pl-11 pr-4 py-3 text-sm"
                data-testid="filter-city"
              />
            </div>
            <select value={filterRooms} onChange={e => setFilterRooms(e.target.value)} className="bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm" data-testid="filter-rooms">
              <option value="">Camere (orice)</option>
              <option value="1">1 cam.</option>
              <option value="2">2 cam.</option>
              <option value="3">3 cam.</option>
              <option value="4">4 cam.</option>
              <option value="5">5+ cam.</option>
            </select>
            <input
              type="number"
              placeholder="Preț max (RON)"
              value={filterPriceMax}
              onChange={e => setFilterPriceMax(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm"
              data-testid="filter-price-max"
            />
          </div>
        </div>
      </section>

      {/* Listings grid */}
      <section className="px-6 py-12">
        <div className="max-w-7xl mx-auto">
          {loading ? (
            <div className="text-center text-stone-400 py-20" data-testid="estate-loading">Se încarcă imobilele...</div>
          ) : items.length === 0 ? (
            <div className="text-center py-20" data-testid="estate-empty">
              <Building2 className="w-16 h-16 text-stone-700 mx-auto mb-4" />
              <h3 className="font-serif text-2xl mb-2">Nu am găsit imobile cu aceste filtre</h3>
              <p className="text-sm text-stone-400 max-w-md mx-auto">
                Verifică din nou mai târziu. Adăugăm imobile noi după ce trec prin toate verificările noastre.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <h2 className="font-serif text-3xl" data-testid="estate-count">{items.length} {items.length === 1 ? "imobil verificat" : "imobile verificate"}</h2>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-stone-400 hidden md:block">Toate cu audit + Digital Twin</div>
                  <div className="inline-flex bg-white/5 rounded-full p-1" data-testid="view-toggle">
                    <button onClick={() => setViewMode("grid")} className={`px-3 py-1.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5 transition-colors ${viewMode === "grid" ? "bg-[#d4ff3a] text-black" : "text-stone-400 hover:text-white"}`} data-testid="view-grid">
                      <LayoutGrid className="w-3.5 h-3.5" /> Grid
                    </button>
                    <button onClick={() => setViewMode("map")} className={`px-3 py-1.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5 transition-colors ${viewMode === "map" ? "bg-[#d4ff3a] text-black" : "text-stone-400 hover:text-white"}`} data-testid="view-map">
                      <MapIcon className="w-3.5 h-3.5" /> Hartă
                    </button>
                  </div>
                </div>
              </div>
              {viewMode === "grid" ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {items.map((it, i) => (
                    <motion.div key={it.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: i * 0.05 }}>
                      <ListingCard item={it} />
                    </motion.div>
                  ))}
                </div>
              ) : (
                <EstateMapView items={items} />
              )}
            </>
          )}
        </div>
      </section>

      {/* Why Verified Section */}
      <section className="px-6 py-20 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-serif text-4xl md:text-5xl mb-12 text-center">De ce <span className="italic gradient-text">Imobile Verificate</span>?</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: ShieldCheck, t: "Audit complet", d: "Fiecare imobil trece printr-un audit tehnic detaliat realizat de specialiștii noștri verificați înainte de listare." },
              { icon: Box, t: "Digital Twin obligatoriu", d: "Tur virtual 3D pentru fiecare imobil. Vezi exact ce cumperi înainte să te deplasezi." },
              { icon: Sparkles, t: "90% recomandări acceptate", d: "Listăm doar imobile unde proprietarul a acceptat și implementat minimum 90% din recomandările noastre." },
            ].map((b, i) => (
              <div key={i} className="glass-strong p-8 rounded-3xl" data-testid={`why-card-${i}`}>
                <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center mb-5">
                  <b.icon className="w-5 h-5 text-[#d4ff3a]" />
                </div>
                <h3 className="font-serif text-2xl mb-3">{b.t}</h3>
                <p className="text-sm text-stone-400 leading-relaxed">{b.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-8" data-testid="estate-guides">
        <h2 className="font-serif text-3xl md:text-4xl tracking-tight mb-2">Ghiduri pentru o cumpărare sigură</h2>
        <p className="text-stone-400 mb-8 max-w-2xl">Tot ce trebuie să știi înainte să cumperi un apartament — verificare, documente, audit tehnic și Digital Twin.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            ["/ghiduri/verificare-apartament-inainte-de-cumparare", "Verificarea apartamentului înainte de cumpărare"],
            ["/ghiduri/ce-documente-verifici-cumparare-apartament", "Ce documente verifici la cumpărare"],
            ["/ghiduri/probleme-tehnice-apartament-inainte-cumparare", "Ce probleme tehnice urmărești"],
            ["/ghiduri/riscuri-cumparare-apartament-bloc-vechi", "Riscuri la cumpărarea într-un bloc vechi"],
            ["/ghiduri/imobile-verificate-cum-functioneaza", "Cum funcționează Imobile Verificate"],
            ["/ghiduri/audit-tehnic-apartament-pret", "Audit tehnic apartament: preț"],
            ["/ghiduri/ce-este-digital-twin-locuinta", "Ce este Digital Twin-ul locuinței"],
            ["/ghiduri/verificare-imobil-digital-twin", "Cum se leagă verificarea de Digital Twin"],
          ].map(([to, label], i) => (
            <Link key={i} to={to} data-testid={`estate-guide-${i}`}
              className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-4 flex items-start justify-between gap-3 hover:bg-white/[0.06] hover:border-emerald-400/40 transition group">
              <span className="text-sm text-stone-200 leading-snug">{label}</span>
              <ArrowRight className="w-4 h-4 text-stone-500 flex-shrink-0 mt-0.5 group-hover:text-emerald-400 transition" />
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-16">
        <NextStep
          dark
          title="Ai o proprietate? Transform-o în Imobil Verificat"
          desc="Audit tehnic + Digital Twin = credibilitate maximă la vânzare și preț corect, susținut de date."
          to="/imobile-verificate/sell"
          cta="Începe procesul"
        />
      </section>

      <ExternalAuditModal open={showExtModal} onClose={() => setShowExtModal(false)} />
      {detailKind && (
        <ServiceDetailModal
          kind={detailKind}
          dark
          onClose={() => setDetailKind(null)}
          primaryCta={{
            label: detailKind === "audit" ? "Solicită Audit" : "Solicită Digital Twin",
            onClick: () => navigate("/imobile-verificate/sell"),
          }}
        />
      )}
    </div>
  );
};

export default EstateBrowse;
