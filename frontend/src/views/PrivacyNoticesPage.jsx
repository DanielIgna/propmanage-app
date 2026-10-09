// Public Privacy Notices page — Phase 49 Part B.
// Per-role privacy notices accessible without login. Each notice has PDF download.
import React from "react";
import { Link } from "react-router-dom";
import { Download, ArrowLeft, Building2, Wrench, Eye, Briefcase, FileSignature } from "lucide-react";
import { API } from "./DashShared";

const NOTICES = [
  {
    id: "client",
    title: "Notificare Confidențialitate — Client",
    icon: Building2,
    color: "from-blue-500 to-cyan-500",
    summary: "Pentru proprietarii care folosesc PropManage pentru a-și gestiona imobile, lansa cereri și efectua plăți escrow.",
    highlights: [
      "Cont, proprietăți, tranzacții, mesaje cu specialiști",
      "10 ani retenție facturi (obligație fiscală)",
      "Stripe, Anthropic, Resend ca sub-procesatori",
    ],
  },
  {
    id: "specialist",
    title: "Notificare Confidențialitate — Specialist",
    icon: Wrench,
    color: "from-emerald-500 to-teal-500",
    summary: "Pentru meseriași verificați care prestează servicii prin marketplace, cu Trust Score și payout către IBAN.",
    highlights: [
      "Documente verificare cu acces strict admin",
      "Trust Score = decizie semi-automatizată (Art. 22)",
      "Drept de review manual al scorului",
    ],
  },
  {
    id: "operator",
    title: "Notificare Confidențialitate — Operator",
    icon: Briefcase,
    color: "from-amber-500 to-orange-500",
    summary: "Pentru personalul intern care validează Digital Twin-uri și raportează incidente. Relație de angajat / colaborator.",
    highlights: [
      "Acces logged la fotografii proprietăți",
      "Audit imutabil al validărilor",
      "Datele clienților strict pentru scopul de validare",
    ],
  },
  {
    id: "visitor",
    title: "Notificare Confidențialitate — Vizitator",
    icon: Eye,
    color: "from-purple-500 to-pink-500",
    summary: "Pentru utilizatorii care vizitează site-ul public fără cont (landing page, marketplace public, status).",
    highlights: [
      "Doar cookies first-party necesare",
      "Fără tracking publicitar (GA, Facebook Pixel)",
      "Demo leads stocate 12 luni",
    ],
  },
  {
    id: "dpa",
    title: "Data Processing Agreement (B2B)",
    icon: FileSignature,
    color: "from-slate-600 to-slate-800",
    summary: "Pentru clienții B2B care folosesc PropManage ca procesator de date. Acord Art. 28 GDPR pentru semnătură.",
    highlights: [
      "Acord standard Art. 28 GDPR",
      "Sub-procesori cu drept de obiecție 14 zile",
      "Audit anual permis Operatorului de Date",
    ],
  },
];

export const PrivacyNoticesPage = () => {
  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link to="/privacy" className="inline-flex items-center gap-2 text-sm text-stone-400 hover:text-stone-200 mb-6">
          <ArrowLeft className="w-4 h-4" /> Înapoi la Politica de Confidențialitate
        </Link>

        <header className="mb-10">
          <h1 className="font-serif text-4xl sm:text-5xl tracking-tight mb-3">Notificări de confidențialitate</h1>
          <p className="text-stone-400 text-base leading-relaxed max-w-3xl">
            În baza Art. 13 și Art. 14 GDPR, am pregătit notificări separate pentru fiecare relație contractuală.
            Alege rolul tău pentru a vedea exact ce date colectăm, de ce și cu cine le partajăm. Fiecare notificare
            este și descărcabilă ca PDF cu semnătură.
          </p>
        </header>

        <div className="grid sm:grid-cols-2 gap-4 mb-12" data-testid="privacy-notices-grid">
          {NOTICES.map((n) => {
            const Icon = n.icon;
            return (
              <div
                key={n.id}
                className="group relative rounded-2xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-colors p-5 flex flex-col"
                data-testid={`notice-card-${n.id}`}
              >
                <div className={`absolute top-0 right-0 left-0 h-0.5 bg-gradient-to-r ${n.color} rounded-t-2xl opacity-60 group-hover:opacity-100 transition-opacity`} />
                <div className="flex items-start gap-3 mb-3">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${n.color} flex items-center justify-center shrink-0`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="font-semibold text-base leading-tight">{n.title}</h2>
                  </div>
                </div>
                <p className="text-sm text-stone-400 leading-relaxed mb-3">{n.summary}</p>
                <ul className="space-y-1.5 mb-4">
                  {n.highlights.map((h, i) => (
                    <li key={i} className="text-xs text-stone-500 flex gap-2">
                      <span className="text-[#d4ff3a] mt-0.5 shrink-0">•</span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-auto flex gap-2">
                  <a
                    href={`${API}/gdpr/pdf/notice/${n.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-full bg-[#d4ff3a] text-black font-medium hover:bg-[#c5f02e] transition-colors"
                    data-testid={`notice-pdf-${n.id}`}
                  >
                    <Download className="w-3.5 h-3.5" /> Descarcă PDF
                  </a>
                  <a
                    href={`${API}/gdpr/pdf/notice/${n.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-full border border-white/10 text-stone-300 hover:bg-white/5"
                    data-testid={`notice-view-${n.id}`}
                  >
                    Citește
                  </a>
                </div>
              </div>
            );
          })}
        </div>

        <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
          <h3 className="font-serif text-2xl mb-2">Mai multă transparență</h3>
          <p className="text-sm text-stone-400 leading-relaxed mb-4">
            Pentru auditul Data Protection Officer punem la dispoziție și documentele tehnice:
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <a href={`${API}/gdpr/documents/ropa`} target="_blank" rel="noreferrer" className="px-4 py-3 rounded-xl border border-white/10 hover:bg-white/5 text-sm" data-testid="public-ropa">
              📋 ROPA (Registru Activități Prelucrare — Art. 30)
            </a>
            <a href={`${API}/gdpr/documents/sub-processors`} target="_blank" rel="noreferrer" className="px-4 py-3 rounded-xl border border-white/10 hover:bg-white/5 text-sm" data-testid="public-subs">
              🌐 Sub-procesatori activi
            </a>
            <a href={`${API}/gdpr/documents/cookies`} target="_blank" rel="noreferrer" className="px-4 py-3 rounded-xl border border-white/10 hover:bg-white/5 text-sm" data-testid="public-cookies">
              🍪 Inventar cookies
            </a>
            <a href={`${API}/gdpr/pdf/dpia`} target="_blank" rel="noreferrer" className="px-4 py-3 rounded-xl border border-white/10 hover:bg-white/5 text-sm" data-testid="public-dpia">
              🤖 DPIA (AI Layer) — PDF
            </a>
          </div>
        </section>

        <footer className="mt-10 text-xs text-stone-500">
          Contact DPO: <a href="mailto:contact@propmanage.ro" className="text-[#d4ff3a] hover:underline">contact@propmanage.ro</a>
          {" · "} Răspuns garantat în 30 zile conform GDPR.
        </footer>
      </div>
    </div>
  );
};

export default PrivacyNoticesPage;
