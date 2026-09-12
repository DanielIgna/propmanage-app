// Lead Magnet #2 — „Checklist cumpărare apartament" (Growth OS G1, Directiva 088)
// 25 verificări interactive + email capture → alimentează Traseul C (audit pre-achiziție).
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ArrowLeft, CheckCircle2, ClipboardCheck, Loader2, Mail } from "lucide-react";
import axios from "axios";
import { useSEO } from "../../hooks/useSEO";

const API = process.env.REACT_APP_BACKEND_URL;
const SITE_URL = "https://propmanage.ro";

const CATEGORIES = [
  { name: "Acte & juridic", items: [
    "Extras de Carte Funciară actualizat (max 30 zile)",
    "Verifică sarcini, ipoteci sau litigii pe imobil",
    "Certificat energetic valabil",
    "Carte tehnică / planurile apartamentului",
    "Adeverință fără datorii la asociație și utilități",
  ]},
  { name: "Structură & clădire", items: [
    "Fisuri în pereți sau tavane (mai ales diagonale)",
    "Clasa de risc seismic a clădirii (bulina roșie!)",
    "Starea fațadei și a acoperișului",
    "Subsolul: uscat, fără miros de igrasie",
    "Modificările structurale au autorizație",
  ]},
  { name: "Instalații", items: [
    "Vârsta instalației electrice + împământare",
    "Tablou electric cu siguranțe automate",
    "Presiunea și culoarea apei la robinet",
    "Materialul țevilor (PEX/PPR vs plumb/oțel vechi)",
    "Centrala termică: vârstă + revizii la zi",
    "Verificarea instalației de gaz este valabilă",
  ]},
  { name: "Interior & finisaje", items: [
    "Urme de umiditate/mucegai (colțuri, spatele mobilei)",
    "Ferestre: etanșeitate și izolare fonică",
    "Pardoseli drepte, fără denivelări",
    "Uși și feronerie funcționale",
    "Igrasie sau condens în baie",
  ]},
  { name: "Zonă & costuri", items: [
    "Costuri lunare reale (cere facturi de iarnă!)",
    "Vecinii și liniștea — vizitează la ore diferite",
    "Locuri de parcare disponibile",
    "Dezvoltări viitoare planificate în zonă",
  ]},
];

const TOTAL = CATEGORIES.reduce((s, c) => s + c.items.length, 0);

export default function BuyingChecklistPage() {
  const [checked, setChecked] = useState({});
  const [form, setForm] = useState({ name: "", email: "", consent: false });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  useSEO({
    title: "Checklist cumpărare apartament — 25 de verificări esențiale · PropManage",
    description: "Checklist gratuit cu cele 25 de verificări obligatorii înainte să cumperi un apartament: acte, structură, instalații, umiditate, costuri ascunse.",
    canonical: `${SITE_URL}/checklist-cumparare`,
  });

  const done = Object.values(checked).filter(Boolean).length;

  const toggle = (key) => setChecked((c) => ({ ...c, [key]: !c[key] }));

  const submitEmail = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.consent) { setError("Bifează consimțământul GDPR."); return; }
    setSending(true);
    try {
      await axios.post(`${API}/api/public/lead-magnet`, {
        magnet: "buying_checklist", name: form.name, email: form.email, consent: form.consent,
      });
      setSent(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "A apărut o eroare. Încearcă din nou.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/ghiduri" className="text-xs text-stone-400 hover:text-white flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Ghiduri
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="mb-8">
          <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
            <ClipboardCheck className="w-3 h-3" /> Checklist gratuit · 25 verificări
          </div>
          <h1 className="font-serif text-3xl sm:text-5xl tracking-tight leading-tight mb-3" data-testid="checklist-h1">
            Checklist: verificarea apartamentului înainte de cumpărare
          </h1>
          <p className="text-stone-400 text-lg">Cele 25 de verificări care te scapă de surprize de zeci de mii de RON. Bifează-le pe cele făcute deja.</p>
          <div className="mt-5 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-[#d4ff3a] transition-all" style={{ width: `${(done / TOTAL) * 100}%` }} />
          </div>
          <div className="text-xs text-stone-500 mt-2" data-testid="checklist-progress">{done}/{TOTAL} verificate</div>
        </div>

        <div className="space-y-6">
          {CATEGORIES.map((cat, ci) => (
            <div key={cat.name} className="glass-strong rounded-2xl p-5" data-testid={`checklist-cat-${ci}`}>
              <h2 className="font-serif text-lg mb-3 text-[#d4ff3a]">{ci + 1}. {cat.name}</h2>
              <div className="space-y-1.5">
                {cat.items.map((item, ii) => {
                  const key = `${ci}-${ii}`;
                  return (
                    <button key={key} onClick={() => toggle(key)}
                      className={`w-full text-left text-sm px-3.5 py-2.5 rounded-xl border transition flex items-start gap-2.5 ${checked[key] ? "border-emerald-500/40 bg-emerald-500/5 text-stone-200" : "border-white/10 bg-white/[0.02] text-stone-300 hover:border-white/25"}`}
                      data-testid={`checklist-item-${key}`}
                    >
                      <CheckCircle2 className={`w-4 h-4 shrink-0 mt-0.5 ${checked[key] ? "text-emerald-400" : "text-stone-600"}`} />
                      <span className={checked[key] ? "line-through opacity-70" : ""}>{item}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {!sent ? (
          <form onSubmit={submitEmail} className="glass-strong rounded-2xl p-6 mt-8" data-testid="checklist-email-form">
            <h2 className="font-serif text-xl mb-1 flex items-center gap-2"><Mail className="w-5 h-5 text-[#d4ff3a]" /> Primește checklist-ul complet pe email</h2>
            <p className="text-xs text-stone-400 mb-4">Ca să-l ai la vizionare, cu explicații pentru fiecare punct.</p>
            <div className="grid sm:grid-cols-2 gap-3 mb-3">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Numele tău" className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-[#d4ff3a] outline-none" data-testid="checklist-name-input" />
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="email@exemplu.ro" className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-[#d4ff3a] outline-none" data-testid="checklist-email-input" />
            </div>
            <label className="flex items-start gap-2 text-xs text-stone-400 mb-4 cursor-pointer">
              <input type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} className="mt-0.5" data-testid="checklist-consent-checkbox" />
              Sunt de acord cu prelucrarea datelor conform <Link to="/privacy" className="underline">politicii de confidențialitate</Link>.
            </label>
            {error && <div className="text-xs text-red-400 mb-3" data-testid="checklist-error">{error}</div>}
            <button type="submit" disabled={sending} className="w-full bg-[#d4ff3a] text-black py-3 rounded-full font-semibold hover:bg-[#bfe632] transition inline-flex items-center justify-center gap-2" data-testid="checklist-submit-btn">
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />} Trimite-mi checklist-ul
            </button>
          </form>
        ) : (
          <div className="glass-strong rounded-2xl p-6 mt-8 text-center border border-emerald-500/30" data-testid="checklist-sent-confirmation">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-stone-200">Checklist-ul a fost trimis pe email. Verifică și folderul Spam.</p>
          </div>
        )}

        <div className="glass-strong rounded-3xl p-8 text-center mt-8" data-testid="checklist-audit-cta">
          <h2 className="font-serif text-2xl mb-2">Nu verifica singur. Trimite un specialist.</h2>
          <p className="text-stone-400 text-sm mb-5 max-w-md mx-auto">
            Audit tehnic profesionist înainte de cumpărare — 350 RON. Funcționează și pentru apartamente găsite pe Storia sau Imobiliare.ro.
          </p>
          <Link to="/imobile-verificate/sell" className="inline-block bg-[#d4ff3a] text-black px-7 py-2.5 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">
            Comandă audit înainte de cumpărare →
          </Link>
        </div>
      </main>
    </div>
  );
}
