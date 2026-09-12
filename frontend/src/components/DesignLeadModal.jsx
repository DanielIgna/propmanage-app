// Shared "Cere ofertă pentru design interior" modal.
// Reuses the EXISTING lead flow (POST /api/interior-design/leads) — NO second lead
// system / no parallel backend. Carries attribution (landing page, source/medium/
// campaign, DI slug, SEO cluster) and fires the existing tracking events.
import React, { useState, useEffect } from "react";
import axios from "axios";
import { X, CheckCircle2, ArrowRight, Loader2 } from "lucide-react";
import { trackIntent, trackLeadFormConversion, getLeadAttribution } from "../lib/analytics";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STYLE_OPTIONS = [
  "modern", "scandinavian", "minimalist", "industrial", "japandi",
  "mediterranean", "classic", "rustic", "boho",
];
const BUDGET_OPTIONS = [
  "sub 5.000 €", "5.000 – 10.000 €", "10.000 – 20.000 €", "20.000 – 40.000 €", "peste 40.000 €",
];
const CITY_OPTIONS = [
  "București", "Cluj-Napoca", "Brașov", "Timișoara", "Iași", "Sibiu", "Oradea", "Constanța",
];

export const DesignLeadModal = ({ open, onClose, context = {} }) => {
  const { di_slug = "", seo_cluster = "design_interior", style = "", city = "", lead_type = "oferta" } = context;
  const [form, setForm] = useState({
    name: "", email: "", phone: "", style: "", budget: "", surface_mp: "",
    rooms: "", city: "", message: "", lead_type: "oferta",
  });
  const [sent, setSent] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    if (open) {
      setForm((f) => ({ ...f, style: style || f.style, city: city || f.city, lead_type: lead_type || "oferta" }));
      setSent(null);
      trackIntent("lead_started");
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const attr = getLeadAttribution();
      await axios.post(`${API}/interior-design/leads`, {
        ...form,
        surface_mp: form.surface_mp ? Number(form.surface_mp) : null,
        landing_page: typeof window !== "undefined" ? window.location.pathname : "",
        di_slug,
        seo_cluster,
        source: attr.source,
        medium: attr.medium,
        campaign: attr.campaign,
        referrer: attr.referrer,
      });
      setSent("Mulțumim! Un designer verificat te va contacta în 24-48h.");
      trackLeadFormConversion();       // Google Ads lead conversion (doar pe succes)
      trackIntent("lead_submitted");   // funnel: organic → SEO page → CTA → lead
    } catch (err) {
      setSent("A apărut o eroare — verifică emailul și reîncearcă.");
    }
    setBusy(false);
  };

  const inputCls = "w-full px-4 py-2.5 rounded-xl border border-white/10 bg-white/[0.04] text-sm text-stone-100 placeholder:text-stone-500 focus:border-[#d4ff3a]/50 focus:outline-none";

  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4" data-testid="di-lead-modal">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="di-lead-backdrop" />
      <div className="relative w-full sm:max-w-lg max-h-[92vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl bg-[#111113] border border-white/10 p-6 sm:p-8 shadow-2xl">
        <button onClick={onClose} className="absolute right-4 top-4 text-stone-500 hover:text-white transition" data-testid="di-lead-close" aria-label="Închide">
          <X className="w-5 h-5" />
        </button>

        {sent ? (
          <div className="text-center py-8" data-testid="di-lead-success">
            <CheckCircle2 className="w-12 h-12 text-[#d4ff3a] mx-auto mb-3" />
            <p className="font-serif text-xl text-white mb-2">Cererea a fost trimisă</p>
            <p className="text-stone-400 text-sm">{sent}</p>
            <button onClick={onClose} className="mt-6 inline-block bg-white/10 text-white px-6 py-2.5 rounded-full text-sm font-medium hover:bg-white/[0.15] transition" data-testid="di-lead-success-close">Închide</button>
          </div>
        ) : (
          <>
            <h2 className="font-serif text-2xl text-white mb-1">Cere ofertă pentru design interior</h2>
            <p className="text-stone-400 text-sm mb-5">Primești oferte de la designeri verificați, cu portofolii și recenzii reale. Fără obligații, plată protejată prin escrow.</p>
            <form onSubmit={submit} className="grid sm:grid-cols-2 gap-3" data-testid="di-lead-form">
              <div className="sm:col-span-2 flex gap-2 flex-wrap">
                {[["oferta", "Cere ofertă"], ["proiect", "Solicită proiect"], ["consultanta", "Consultanță"]].map(([v, l]) => (
                  <button type="button" key={v} onClick={() => setForm((f) => ({ ...f, lead_type: v }))}
                    className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${form.lead_type === v ? "bg-[#d4ff3a] text-black" : "bg-white/[0.06] text-stone-300 hover:bg-white/10"}`}
                    data-testid={`di-lead-type-${v}`}>{l}</button>
                ))}
              </div>
              <input required placeholder="Nume complet *" value={form.name} onChange={set("name")} className={inputCls} data-testid="di-lead-name" />
              <input required type="email" placeholder="Email *" value={form.email} onChange={set("email")} className={inputCls} data-testid="di-lead-email" />
              <input placeholder="Telefon" value={form.phone} onChange={set("phone")} className={inputCls} data-testid="di-lead-phone" />
              <select value={form.city} onChange={set("city")} className={inputCls} data-testid="di-lead-city">
                <option value="">Oraș…</option>
                {CITY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                <option value="alt">Alt oraș / remote</option>
              </select>
              <select value={form.style} onChange={set("style")} className={inputCls} data-testid="di-lead-style">
                <option value="">Stil dorit…</option>
                {STYLE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={form.budget} onChange={set("budget")} className={inputCls} data-testid="di-lead-budget">
                <option value="">Buget estimat…</option>
                {BUDGET_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
              <input type="number" min="10" placeholder="Suprafață (mp)" value={form.surface_mp} onChange={set("surface_mp")} className={inputCls} data-testid="di-lead-surface" />
              <input placeholder="Camere (ex: living + bucătărie)" value={form.rooms} onChange={set("rooms")} className={inputCls} data-testid="di-lead-rooms" />
              <textarea placeholder="Descrie proiectul (opțional)" value={form.message} onChange={set("message")} rows={3} className={`${inputCls} sm:col-span-2`} data-testid="di-lead-message" />
              <button type="submit" disabled={busy} className="sm:col-span-2 py-3 rounded-xl bg-[#d4ff3a] text-black font-semibold hover:bg-[#bfe632] transition disabled:opacity-50 flex items-center justify-center gap-2" data-testid="di-lead-submit">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Trimite cererea — e gratuit <ArrowRight className="w-4 h-4" /></>}
              </button>
              <p className="sm:col-span-2 text-[11px] text-stone-500 text-center">Fără abonament, fără obligații. Primești oferte în 24-48h.</p>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default DesignLeadModal;
