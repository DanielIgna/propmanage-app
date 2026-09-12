import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Building2, MapPin, Bed, Maximize2, ShieldCheck, Box, ArrowLeft,
  Calendar, FileText, CheckCircle2, Sparkles, Layers, Mail, Phone, User
} from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const formatPrice = (ron) => {
  if (!ron) return "—";
  return new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(ron) + " RON";
};

const InquiryForm = ({ listing, intent = "viewing", onSuccess }) => {
  const [form, setForm] = useState({ name: "", email: "", phone: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/verified-estate/inquiries`, {
        listing_id: listing.id,
        intent,
        ...form,
      });
      setDone(true);
      onSuccess?.();
    } catch (err) {
      alert(err?.response?.data?.detail || "Eroare la trimitere.");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="text-center py-6" data-testid="inquiry-done">
        <CheckCircle2 className="w-12 h-12 text-[#d4ff3a] mx-auto mb-3" />
        <h4 className="font-serif text-lg mb-2">Cerere trimisă ✓</h4>
        <p className="text-xs text-stone-400">Te vom contacta în 24 de ore.</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3" data-testid={`inquiry-form-${intent}`}>
      <div className="relative">
        <User className="w-4 h-4 text-stone-500 absolute left-3 top-1/2 -translate-y-1/2" />
        <input required placeholder="Nume" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm" />
      </div>
      <div className="relative">
        <Mail className="w-4 h-4 text-stone-500 absolute left-3 top-1/2 -translate-y-1/2" />
        <input required type="email" placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm" />
      </div>
      <div className="relative">
        <Phone className="w-4 h-4 text-stone-500 absolute left-3 top-1/2 -translate-y-1/2" />
        <input placeholder="Telefon (opțional)" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm" />
      </div>
      <textarea rows={3} placeholder="Mesaj sau întrebări..." value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm resize-none" />
      <button type="submit" disabled={submitting} className="w-full btn-accent py-2.5 rounded-xl font-medium text-sm disabled:opacity-50">
        {submitting ? "Se trimite..." : intent === "buy" ? "Trimite intenția de cumpărare" : "Programează vizionare"}
      </button>
    </form>
  );
};

export const EstateDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [galleryIndex, setGalleryIndex] = useState(0);
  const [intent, setIntent] = useState("viewing");

  useEffect(() => {
    let active = true;
    setLoading(true);
    axios.get(`${API}/api/verified-estate/listings/${id}`)
      .then(r => { if (active) setListing(r.data); })
      .catch(() => { if (active) setListing(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (loading) {
    return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400" data-testid="detail-loading">Se încarcă...</div>;
  }

  if (!listing) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-center p-6" data-testid="detail-notfound">
        <div>
          <Building2 className="w-16 h-16 text-stone-700 mx-auto mb-4" />
          <h2 className="font-serif text-2xl mb-2">Imobil indisponibil</h2>
          <p className="text-sm text-stone-400 mb-6">Acest imobil nu mai este public sau a fost retras.</p>
          <Link to="/imobile-verificate" className="btn-accent px-6 py-2.5 rounded-full text-sm">Înapoi la listă</Link>
        </div>
      </div>
    );
  }

  const gallery = listing.gallery && listing.gallery.length > 0 ? listing.gallery : (listing.cover_image_url ? [listing.cover_image_url] : []);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <button onClick={() => navigate(-1)} className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-6" data-testid="detail-back">
          <ArrowLeft className="w-3.5 h-3.5" /> Înapoi
        </button>

        <div className="grid lg:grid-cols-[1.5fr_1fr] gap-8">
          {/* Left: Gallery + Twin + Description */}
          <div className="space-y-6">
            {/* Gallery */}
            <div className="bg-[#0e0e10] rounded-3xl overflow-hidden border border-white/10">
              <div className="aspect-[16/10] relative bg-gradient-to-br from-stone-900 to-stone-800">
                {gallery[galleryIndex] ? (
                  <img src={gallery[galleryIndex]} alt={listing.title} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-stone-700"><Building2 className="w-24 h-24" /></div>
                )}
                <div className="absolute top-4 left-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#d4ff3a]/15 border border-[#d4ff3a]/40 text-[#d4ff3a] text-xs font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5" /> VERIFIED TWIN
                </div>
              </div>
              {gallery.length > 1 && (
                <div className="p-3 flex gap-2 overflow-x-auto">
                  {gallery.map((g, i) => (
                    <button
                      key={i}
                      onClick={() => setGalleryIndex(i)}
                      className={`shrink-0 w-20 h-14 rounded-lg overflow-hidden border-2 ${i === galleryIndex ? "border-[#d4ff3a]" : "border-transparent"}`}
                      data-testid={`gallery-thumb-${i}`}
                    >
                      {/* eslint-disable-next-line */}
                      <img src={g} alt={`Vedere ${i + 1}`} className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Digital Twin Preview Block */}
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="detail-twin-block">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center">
                    <Box className="w-5 h-5 text-[#d4ff3a]" />
                  </div>
                  <div>
                    <div className="text-xs text-stone-400 uppercase tracking-wider">Digital Twin</div>
                    <h3 className="font-serif text-xl">Tur virtual 3D interactiv</h3>
                  </div>
                </div>
                {listing.digital_twin_id ? (
                  <div className="inline-flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-full">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs text-emerald-400">DISPONIBIL</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-2 bg-amber-500/10 px-3 py-1.5 rounded-full">
                    <div className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="text-xs text-amber-400">ÎN PREGĂTIRE</span>
                  </div>
                )}
              </div>
              <div className="aspect-video rounded-2xl bg-gradient-to-br from-cyan-500/10 via-purple-500/5 to-emerald-500/10 border border-white/10 flex items-center justify-center relative overflow-hidden">
                <Box className="w-24 h-24 text-white/20" strokeWidth={0.8} />
                <div className="absolute inset-0 flex items-center justify-center">
                  {String(listing.digital_twin_id || "").startsWith("demo-") ? (
                    <Link to="/demo" target="_blank" className="btn-accent px-5 py-2.5 rounded-full font-medium inline-flex items-center gap-2 text-sm" data-testid="detail-open-twin">
                      <Box className="w-4 h-4" /> Deschide Digital Twin
                    </Link>
                  ) : listing.digital_twin_id ? (
                    <button
                      onClick={() => document.getElementById("inquiry-card")?.scrollIntoView({ behavior: "smooth" })}
                      className="btn-accent px-5 py-2.5 rounded-full font-medium inline-flex items-center gap-2 text-sm"
                      data-testid="detail-request-twin"
                    >
                      <Box className="w-4 h-4" /> Solicită tur 3D ghidat
                    </button>
                  ) : (
                    <div className="text-xs text-stone-300 bg-black/50 px-4 py-2 rounded-full" data-testid="detail-twin-pending">
                      Digital Twin în curs de creare pentru acest imobil
                    </div>
                  )}
                </div>
              </div>
              <p className="text-xs text-stone-400 mt-3">Explorează imobilul în 3D din orice unghi. Vezi sistemele tehnice mapate. Evită vizionări inutile.</p>
            </div>

            {/* Description */}
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6">
              <h3 className="font-serif text-2xl mb-4">Descriere</h3>
              <p className="text-sm text-stone-300 leading-relaxed whitespace-pre-line">{listing.description || "Nu există descriere."}</p>
            </div>

            {/* Audit Report */}
            {listing.audit_report_url && (
              <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6 flex items-center justify-between" data-testid="detail-audit-block">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-[#d4ff3a]" />
                  </div>
                  <div>
                    <div className="font-serif text-lg">Raport audit complet</div>
                    <div className="text-xs text-stone-400">{listing.recommendations_accepted} din {listing.recommendations_total} recomandări acceptate · {listing.recommendations_pct}%</div>
                  </div>
                </div>
                <a href={listing.audit_report_url} target="_blank" rel="noopener noreferrer" className="glass px-4 py-2 rounded-full text-xs font-medium hover:bg-white/10" data-testid="detail-audit-download">Vezi PDF</a>
              </div>
            )}

            {/* Trust Strip */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { icon: ShieldCheck, t: "Audit Tehnic", d: "Verificat de specialiști" },
                { icon: Box, t: "Digital Twin", d: "Tur 3D inclus" },
                { icon: Sparkles, t: `${listing.recommendations_pct}% Reco`, d: "Acceptate de proprietar" },
              ].map((b, i) => (
                <div key={i} className="glass-strong rounded-2xl p-4 text-center" data-testid={`trust-strip-${i}`}>
                  <b.icon className="w-5 h-5 text-[#d4ff3a] mx-auto mb-2" />
                  <div className="text-xs font-medium">{b.t}</div>
                  <div className="text-[10px] text-stone-500 mt-0.5">{b.d}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Sticky info card + inquiry */}
          <div id="inquiry-card" className="lg:sticky lg:top-28 h-fit space-y-4">
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#d4ff3a]/15 border border-[#d4ff3a]/40 text-[#d4ff3a] text-[10px] font-semibold mb-3">
                <ShieldCheck className="w-3 h-3" /> VERIFIED TWIN
              </div>
              <h1 className="font-serif text-3xl leading-tight mb-2" data-testid="detail-title">{listing.title}</h1>
              <div className="flex items-center gap-1.5 text-sm text-stone-400 mb-5">
                <MapPin className="w-3.5 h-3.5" /> {listing.city} {listing.address ? `· ${listing.address}` : ""}
              </div>
              <div className="text-xs text-stone-500 uppercase tracking-wider mb-1">Preț</div>
              <div className="font-serif text-4xl mb-5" data-testid="detail-price">{formatPrice(listing.price_ron)}</div>

              <div className="grid grid-cols-3 gap-3 pb-5 border-b border-white/5 mb-5">
                <div className="text-center">
                  <Bed className="w-4 h-4 text-stone-400 mx-auto mb-1" />
                  <div className="text-xs text-stone-400">Camere</div>
                  <div className="text-sm font-medium">{listing.rooms}</div>
                </div>
                <div className="text-center">
                  <Maximize2 className="w-4 h-4 text-stone-400 mx-auto mb-1" />
                  <div className="text-xs text-stone-400">Suprafață</div>
                  <div className="text-sm font-medium">{listing.surface_sqm} m²</div>
                </div>
                <div className="text-center">
                  <Layers className="w-4 h-4 text-stone-400 mx-auto mb-1" />
                  <div className="text-xs text-stone-400">Etaj</div>
                  <div className="text-sm font-medium">{listing.floor || "—"}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mb-5">
                <button onClick={() => setIntent("viewing")} className={`py-2 rounded-xl text-xs font-medium transition-colors ${intent === "viewing" ? "bg-[#d4ff3a] text-black" : "bg-white/5 text-stone-300"}`} data-testid="intent-viewing">
                  <Calendar className="w-3.5 h-3.5 inline mr-1" /> Vizionare
                </button>
                <button onClick={() => setIntent("buy")} className={`py-2 rounded-xl text-xs font-medium transition-colors ${intent === "buy" ? "bg-[#d4ff3a] text-black" : "bg-white/5 text-stone-300"}`} data-testid="intent-buy">
                  <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" /> Vreau să cumpăr
                </button>
              </div>

              <InquiryForm listing={listing} intent={intent} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EstateDetail;
