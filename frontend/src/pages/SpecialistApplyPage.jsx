import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ArrowLeft, X, PaintRoller, Sparkles, Wrench, Zap, Wind, Hammer,
  PartyPopper, Ruler, ScanSearch, Briefcase, Banknote, BadgeCheck,
  Phone, FileCheck, Rocket,
} from "lucide-react";
import {
  QuestionCard, OptionRadio, StickyCTA, CategoryCard, FeaturedCard,
  TextField, TrustStrip, StepDots, CopyBadge, CJ_GREEN,
} from "./dashboard/clientjunior/components";
import { API } from "./DashShared";

// ============================================================================
// Devino specialist — UX Lab (rută publică /devino-specialist).
// Aplicații REALE → unified leads (source=specialist_entry). Telemetrie se_*.
// ============================================================================

const FEATURED = [
  { id: "designer_arhitect", label: "Designer / Arhitect", icon: Ruler, price: "Proiecte Design Interior", badge: "Echipa PropManage",
    image: "https://static.prod-images.emergentagent.com/jobs/c0629304-e2e2-4a6f-8f15-5c4c3ef257d1/images/7b363db9e5f2b9781098798793b0f1746f212980f43a212562902c1e28838a43.jpeg" },
  { id: "auditor_tehnic", label: "Auditor tehnic / Inginer", icon: ScanSearch, price: "Proiecte Digital Twin & Audit", badge: "Echipa PropManage",
    image: "https://images.unsplash.com/photo-1721244654394-36a7bc2da288?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxhcmNoaXRlY3R1cmFsJTIwYmx1ZXByaW50JTIwYnVpbGRpbmd8ZW58MHx8fHwxNzg0OTkwMDEyfDA&ixlib=rb-4.1.0&q=85&w=800" },
];

const TRADES = [
  { id: "instalatii", label: "Instalator sanitar", icon: Wrench, price: "cerere constantă" },
  { id: "electric", label: "Electrician", icon: Zap, price: "cerere constantă" },
  { id: "finisaje", label: "Zugrav / Finisaje", icon: PaintRoller, price: "cerere mare" },
  { id: "clima", label: "Climatizare (HVAC)", icon: Wind, price: "sezonier intens" },
  { id: "montaj", label: "Montator mobilă", icon: Hammer, price: "cerere constantă" },
  { id: "curatenie", label: "Curățenie profesională", icon: Sparkles, price: "recurent" },
];

const ALL = [...FEATURED, ...TRADES];

const QUESTIONS = [
  { key: "experience", q: "Câtă experiență ai în meserie?", options: ["Sub 2 ani", "2 – 5 ani", "Peste 5 ani"] },
  { key: "availability", q: "Cum vrei să lucrezi cu noi?", hint: "Poți schimba oricând.", options: ["Full-time", "Part-time / weekend", "Doar proiecte mari"] },
];

const SE_TRUST = [
  [Briefcase, "Lucrări constante"],
  [Banknote, "Plăți garantate"],
  [BadgeCheck, "Înscriere gratuită"],
];

const sid = () => {
  let s = sessionStorage.getItem("se_session");
  if (!s) { s = Math.random().toString(36).slice(2, 12); sessionStorage.setItem("se_session", s); }
  return s;
};
const track = (event, meta = {}) => {
  axios.post(`${API}/public/ux-lab/event`, { session_id: sid(), role: "specialist_entry", event, meta }).catch(() => {});
};

const Header = ({ title, onBack, onClose }) => (
  <div className="flex items-center gap-3 px-4 py-3.5 bg-white border-b border-slate-100">
    <button onClick={onBack} className="p-2.5 -ml-2" data-testid="se-flow-back" aria-label="Înapoi"><ArrowLeft className="w-5 h-5 text-slate-700" /></button>
    <span className="flex-1 text-center text-sm font-bold text-slate-900 truncate">{title}</span>
    <button onClick={onClose} className="p-2.5 -mr-2" data-testid="se-flow-close" aria-label="Închide"><X className="w-5 h-5 text-slate-700" /></button>
  </div>
);

const HomeView = ({ onPickTrade }) => {
  const [showAll, setShowAll] = useState(() => typeof window !== "undefined" && window.innerWidth >= 768);
  return (
  <div className="pb-16" data-testid="se-home-view">
    <a href="#se-apply-start" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:px-4 focus:py-2 focus:rounded-full focus:text-sm focus:font-bold focus:text-[#166534] focus:shadow-lg" data-testid="se-skip-link">
      Sari direct la aplicare
    </a>
    <div className="px-5 pt-6 flex items-center gap-2">
      <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: CJ_GREEN }}>
        <Sparkles className="w-4 h-4 text-white" aria-hidden="true" />
      </span>
      <span className="text-lg font-black text-slate-900">propmanage</span>
    </div>
    <div className="md:grid md:grid-cols-2 md:gap-10 md:items-start md:px-3">
    <div className="cj-reveal">
    <div className="px-5 mt-4">
      <h1 className="text-2xl md:text-3xl font-black text-slate-900 leading-snug">Câștigă din meseria ta, fără să alergi după clienți</h1>
      <p className="mt-2 text-sm text-slate-500">Alege meseria, spune-ne 2 lucruri despre tine și te sunăm noi în 24h.</p>
      <a href="#se-apply-start" data-testid="se-hero-cta"
        className="mt-4 inline-flex w-full md:w-auto items-center justify-center min-h-[52px] px-8 rounded-full text-base font-bold text-white shadow-lg shadow-[#166534]/30 active:scale-[0.98] transition-transform"
        style={{ background: CJ_GREEN }}>
        Aplică gratuit — te sunăm în 24h
      </a>
    </div>
    <TrustStrip items={SE_TRUST} />
    <div className="mt-7 px-5">
      <h2 id="se-apply-start" className="text-base font-black text-slate-900">Roluri în echipa proiectelor noastre</h2>
      <div className="mt-3 space-y-4">
        {FEATURED.map(c => (
          <FeaturedCard key={c.id} icon={c.icon} label={c.label} sub={c.price} badge={c.badge} image={c.image}
            onClick={() => onPickTrade(c)} testid={`se-feat-${c.id}`} />
        ))}
      </div>
    </div>
    </div>
    <div className="mt-7 px-5 md:mt-16 cj-reveal" style={{ animationDelay: "0.1s" }}>
      <h2 className="text-base font-black text-slate-900">Meserii căutate pe șantierele noastre</h2>
      {!showAll ? (
        <button onClick={() => setShowAll(true)} data-testid="se-show-all-trades"
          className="mt-3 w-full min-h-[56px] flex items-center justify-between rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-left active:bg-slate-50 transition-colors">
          <span className="text-sm font-bold text-slate-900">Vezi toate meseriile ({TRADES.length})</span>
          <span className="text-xs font-semibold text-[#166534]">instalator · electrician · zugrav…</span>
        </button>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-3" data-testid="se-trades-grid">
          {TRADES.map(c => (
            <CategoryCard key={c.id} icon={c.icon} label={c.label} sub={c.price} onClick={() => onPickTrade(c)} testid={`se-trade-${c.id}`} />
          ))}
        </div>
      )}
    </div>
    </div>
  </div>
  );
};

const ContactStep = ({ contact, setContact, touched, setTouched }) => {
  const phoneBad = touched.phone && contact.phone.replace(/\D/g, "").length < 9;
  const nameBad = touched.name && contact.name.trim().length < 3;
  const cityBad = touched.city && !contact.city.trim();
  const emailBad = touched.email && contact.email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(contact.email);
  return (
    <div className="px-5 pt-6" data-testid="se-contact-step">
      <h2 className="text-2xl font-black text-slate-900 leading-snug">Cum te contactăm?</h2>
      <p className="mt-1.5 text-sm text-slate-500">Te sunăm în max. 24h pentru activare. Fără spam.</p>
      <div className="mt-5 space-y-3">
        <TextField label="Numele tău" required value={contact.name} onChange={v => setContact(c => ({ ...c, name: v }))}
          onBlur={() => setTouched(t => ({ ...t, name: true }))} error={nameBad ? "Numele pare prea scurt." : ""}
          autoComplete="name" placeholder="ex: Mihai Georgescu" testid="se-contact-name" />
        <TextField label="Orașul în care lucrezi" required value={contact.city} onChange={v => setContact(c => ({ ...c, city: v }))}
          onBlur={() => setTouched(t => ({ ...t, city: true }))} error={cityBad ? "Avem nevoie de oraș ca să-ți trimitem lucrări din zonă." : ""}
          autoComplete="address-level2" placeholder="ex: Cluj-Napoca" testid="se-contact-city" />
        <TextField label="Telefon" required value={contact.phone} onChange={v => setContact(c => ({ ...c, phone: v }))}
          onBlur={() => setTouched(t => ({ ...t, phone: true }))} error={phoneBad ? "Numărul pare incomplet — verifică cifrele." : ""}
          type="tel" inputMode="tel" autoComplete="tel" placeholder="ex: 07xx xxx xxx" testid="se-contact-phone" />
        <TextField label="Email" optional value={contact.email} onChange={v => setContact(c => ({ ...c, email: v }))}
          onBlur={() => setTouched(t => ({ ...t, email: true }))} error={emailBad ? "Adresa de email nu pare validă." : ""}
          type="email" inputMode="email" autoComplete="email" placeholder="ex: mihai@email.ro" testid="se-contact-email" />
        <label className="flex items-start gap-3 cursor-pointer min-h-[44px]" data-testid="se-consent-label">
          <input type="checkbox" checked={contact.consent} onChange={e => setContact(c => ({ ...c, consent: e.target.checked }))}
            data-testid="se-consent-checkbox" className="mt-0.5 w-5 h-5 rounded border-slate-300 accent-[#166534]" />
          <span className="text-xs text-slate-600">Sunt de acord cu prelucrarea datelor pentru înscrierea ca specialist PropManage (GDPR).</span>
        </label>
      </div>
    </div>
  );
};

const FlowView = ({ trade, onDone, onExit }) => {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [contact, setContact] = useState({ name: "", phone: "", city: "", email: "", consent: false });
  const [touched, setTouched] = useState({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const total = QUESTIONS.length + 1;
  const isContact = step === QUESTIONS.length;
  const progress = ((step + 1) / total) * 100;

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onExit(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onExit]);

  useEffect(() => {
    if (!isContact) document.querySelector(`[data-testid="se-option-${QUESTIONS[step].key}-0"]`)?.focus();
  }, [step, isContact]);

  const phoneOk = contact.phone.replace(/\D/g, "").length >= 9;
  const canSubmit = contact.name.trim().length >= 3 && phoneOk && contact.city.trim() && contact.consent;

  const submit = async () => {
    setSending(true); setError("");
    try {
      const r = await axios.post(`${API}/public/specialist-entry/apply`, {
        name: contact.name, phone: contact.phone, email: contact.email, city: contact.city,
        trade: trade.id, trade_label: trade.label,
        experience: answers.experience, availability: answers.availability, consent: contact.consent,
      });
      track("se_submitted", { trade: trade.id });
      onDone(r.data.request_number);
    } catch (e) {
      setError(e?.response?.data?.detail || "Nu am putut trimite aplicația. Verifică datele și încearcă din nou.");
    } finally { setSending(false); }
  };

  const next = () => {
    if (isContact) return submit();
    track("se_step", { step: QUESTIONS[step].key, trade: trade.id });
    setStep(step + 1);
  };

  const q = !isContact ? QUESTIONS[step] : null;
  const selected = q ? answers[q.key] : null;
  const stepLabels = [...QUESTIONS.map(x => x.q), "Datele tale"];
  const shortLabels = ["Experiență", "Program", "Contact"];
  return (
    <div className="pb-36" data-testid="se-flow-view">
      <Header title={trade.label} onBack={() => (step === 0 ? onExit() : setStep(step - 1))} onClose={onExit} />
      <div className="h-1.5 bg-slate-100" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={total}>
        <div className="h-full transition-all duration-300 rounded-r-full" style={{ width: `${progress}%`, background: CJ_GREEN }} data-testid="se-progress-bar" />
      </div>
      <div className="md:max-w-md md:mx-auto">
        <div className="px-5 pt-4">
          <StepDots total={total} current={step} labels={stepLabels} shortLabels={shortLabels} onJump={setStep} />
        </div>
        {isContact ? (
          <ContactStep contact={contact} setContact={setContact} touched={touched} setTouched={setTouched} />
        ) : (
          <QuestionCard question={q.q} hint={q.hint}>
            {q.options.map((opt, i) => (
              <OptionRadio key={opt} label={opt} selected={selected === opt} testid={`se-option-${q.key}-${i}`}
                onSelect={() => setAnswers(a => ({ ...a, [q.key]: opt }))} />
            ))}
          </QuestionCard>
        )}
        {error && <p className="px-5 mt-3 text-sm font-semibold text-rose-600" role="alert" data-testid="se-submit-error">{error}</p>}
      </div>
      <StickyCTA label={isContact ? (sending ? "Se trimite…" : "Trimite aplicația") : "Continuă"}
        disabled={isContact ? (!canSubmit || sending) : !selected} onClick={next} testid="se-continue-btn" />
    </div>
  );
};

const NEXT_STEPS = [
  [FileCheck, "Verificăm datele și experiența ta"],
  [Phone, "Te sunăm în max. 24h pentru activare"],
  [Rocket, "Primești primele oportunități din zona ta"],
];

const ConfirmView = ({ trade, requestNumber }) => (
  <div className="min-h-screen pb-10 flex flex-col bg-[#EDF7EF]" data-testid="se-confirm-view">
    <div className="flex-1 flex flex-col items-center justify-center px-6 text-center pt-12">
      <span className="w-20 h-20 rounded-full flex items-center justify-center mb-6" style={{ background: CJ_GREEN }}>
        <PartyPopper className="w-9 h-9 text-white" aria-hidden="true" />
      </span>
      <h1 className="text-2xl font-black text-slate-900 leading-snug">Aplicația ta a fost trimisă!</h1>
      <p className="mt-2 text-sm text-slate-600 flex items-center justify-center gap-1 flex-wrap">{trade.label} · Nr. <CopyBadge value={requestNumber} testid="se-request-number" /></p>
      <div className="mt-6 w-full max-w-sm rounded-2xl bg-white border border-slate-100 p-5 text-left shadow-sm">
        <h2 className="text-sm font-black text-slate-900">Ce urmează</h2>
        <ol className="mt-3">
          {NEXT_STEPS.map(([Icon, s], i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="flex flex-col items-center self-stretch">
                <span className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ background: CJ_GREEN }}>
                  <Icon className="w-3.5 h-3.5 text-white" aria-hidden="true" />
                </span>
                {i < NEXT_STEPS.length - 1 && <span className="w-px flex-1 min-h-[16px] bg-[#166534]/30" aria-hidden="true" />}
              </span>
              <span className="text-sm text-slate-700 pb-4 pt-1">{s}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
    <div className="px-5 mt-8 space-y-2 max-w-md mx-auto w-full">
      <a href="/register" data-testid="se-create-account-link"
        className="block w-full min-h-[52px] py-4 rounded-full text-center text-base font-bold text-white shadow-lg shadow-[#166534]/30 active:scale-[0.98] transition-transform" style={{ background: CJ_GREEN }}>
        Creează-ți contul de specialist
      </a>
      <a href="/" data-testid="se-back-home-link"
        className="block w-full min-h-[44px] py-2.5 text-center text-sm font-semibold text-[#166534]">
        Înapoi la prima pagină
      </a>
    </div>
  </div>
);

export default function SpecialistApplyPage() {
  const [view, setView] = useState("home"); // home | flow | confirm
  const [trade, setTrade] = useState(null);
  const [requestNumber, setRequestNumber] = useState(null);

  useEffect(() => { track("se_view"); }, []);

  useEffect(() => {
    const root = document.documentElement;
    const prevTheme = root.getAttribute("data-theme");
    const hadDark = root.classList.contains("dark");
    root.setAttribute("data-theme", "light");
    root.classList.remove("dark");
    return () => {
      if (prevTheme) root.setAttribute("data-theme", prevTheme); else root.removeAttribute("data-theme");
      if (hadDark) root.classList.add("dark");
    };
  }, []);

  const startFlow = (t) => { track("se_flow_start", { trade: t.id }); setTrade(t); setView("flow"); };

  return (
    <div className="min-h-screen bg-[#FAFBFA] cv2-scope" data-testid="specialist-apply-page">
      <div className="max-w-md md:max-w-5xl mx-auto min-h-screen bg-white sm:border-x sm:border-slate-100 md:px-6 md:pt-6">
        {view === "flow" ? (
          <FlowView trade={trade} onDone={(n) => { setRequestNumber(n); setView("confirm"); }} onExit={() => setView("home")} />
        ) : view === "confirm" ? (
          <ConfirmView trade={trade} requestNumber={requestNumber} />
        ) : (
          <HomeView onPickTrade={startFlow} />
        )}
      </div>
    </div>
  );
}
