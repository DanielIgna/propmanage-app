import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ArrowLeft, X, Search, PaintRoller, Sparkles, Wrench, Zap, Wind, Hammer,
  PartyPopper, Bell, Settings, CircleCheck, Circle, ScanSearch, Palette,
} from "lucide-react";
import {
  QuestionCard, OptionRadio, StickyCTA, BottomNav, CategoryCard, FeaturedCard,
  TextField, TrustStrip, StepDots, CopyBadge, CJ_ACCENT,
} from "./clientjunior/components";
import { API } from "../DashShared";

// ============================================================================
// Client Junior — UX Lab (rută publică /incepe). Cereri REALE → unified leads.
// Redesign XOS 2026: signature cards foto, tipografie Outfit, dock glass.
// ============================================================================

const IMG_TWIN = "https://images.unsplash.com/photo-1721244654394-36a7bc2da288?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxhcmNoaXRlY3R1cmFsJTIwYmx1ZXByaW50JTIwYnVpbGRpbmd8ZW58MHx8fHwxNzg0OTkwMDEyfDA&ixlib=rb-4.1.0&q=85&w=1200";
const IMG_DESIGN = "https://static.prod-images.emergentagent.com/jobs/c0629304-e2e2-4a6f-8f15-5c4c3ef257d1/images/7b363db9e5f2b9781098798793b0f1746f212980f43a212562902c1e28838a43.jpeg";

const FEATURED = [
  { id: "digital_twin", label: "Digital Twin & Audit Tehnic", icon: ScanSearch, price: "de la RON 1.500", badge: "Serviciu PropManage", image: IMG_TWIN },
  { id: "design_interior", label: "Design Interior", icon: Palette, price: "RON 3.000 – 25.000", badge: "Serviciu PropManage", image: IMG_DESIGN },
];

const CATEGORIES = [
  { id: "zugraveli", label: "Zugrăveli Interioare", icon: PaintRoller, price: "RON 2.000 – 14.500" },
  { id: "curatenie", label: "Curățenie la Domiciliu", icon: Sparkles, price: "RON 150 – 800" },
  { id: "instalatii", label: "Instalații Sanitare", icon: Wrench, price: "RON 200 – 3.500" },
  { id: "electric", label: "Electricitate", icon: Zap, price: "RON 150 – 2.000" },
  { id: "clima", label: "Aer Condiționat", icon: Wind, price: "RON 250 – 1.200" },
  { id: "montaj", label: "Montaj Mobilă", icon: Hammer, price: "RON 100 – 900" },
];

const ALL = [...FEATURED, ...CATEGORIES];

const QUESTIONS = [
  { key: "where", q: "Unde ai nevoie de serviciu?", options: ["Apartament", "Casă"] },
  { key: "size", q: "Cât de mare e lucrarea?", hint: "O estimare e suficientă.", options: ["Mică (1-2 camere)", "Medie (3-4 camere)", "Mare (5+ camere)"] },
  { key: "when", q: "Când ai avea nevoie?", options: ["Cât mai repede", "În următoarele 2 săptămâni", "Doar explorez prețuri"] },
];

// ── Telemetrie UX Lab (anonimă, fire-and-forget) ─────────────────────────────
const sid = () => {
  let s = sessionStorage.getItem("cj_session");
  if (!s) { s = Math.random().toString(36).slice(2, 12); sessionStorage.setItem("cj_session", s); }
  return s;
};
const track = (event, meta = {}) => {
  axios.post(`${API}/public/ux-lab/event`, { session_id: sid(), role: "client_junior", event, meta }).catch(() => {});
};

const Header = ({ title, onBack, onClose }) => (
  <div className="sticky top-0 z-20 xos-topbar">
    <div className="flex items-center gap-3 px-4 py-3.5 max-w-md mx-auto">
      <button onClick={onBack} className="p-2.5 -ml-2" data-testid="cj-flow-back" aria-label="Înapoi"><ArrowLeft className="w-5 h-5 text-slate-700" /></button>
      <span className="flex-1 text-center text-sm font-bold text-slate-900 truncate">{title}</span>
      <button onClick={onClose} className="p-2.5 -mr-2" data-testid="cj-flow-close" aria-label="Închide"><X className="w-5 h-5 text-slate-700" /></button>
    </div>
  </div>
);

const SectionTitle = ({ children }) => (
  <h2 className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">{children}</h2>
);

const HomeView = ({ onPickCategory }) => {
  const [query, setQuery] = useState("");
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const filtered = query ? ALL.filter(c => norm(c.label).includes(norm(query))) : null;
  return (
    <div className="pb-28" data-testid="cj-home-view">
      <header className="sticky top-0 z-20 xos-topbar">
        <div className="px-5 py-3.5 flex items-center gap-2 max-w-5xl mx-auto">
          <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: CJ_ACCENT }}>
            <Sparkles className="w-4 h-4 text-black" aria-hidden="true" />
          </span>
          <span className="xos-display text-base font-semibold tracking-tight text-slate-900">propmanage</span>
        </div>
      </header>
      <div className="max-w-5xl mx-auto">
        <div className="px-5 pt-8 md:pt-12 cj-reveal">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#166534]">Experience OS · Servicii pentru casă</p>
          <h1 className="mt-2 xos-display text-4xl md:text-5xl font-light tracking-tighter text-slate-900 leading-[1.05]">
            Ce vrei să <span className="font-semibold">rezolvi</span> azi?
          </h1>
        </div>
        <div className="px-5 mt-6 md:max-w-xl">
          <label className="relative block">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" aria-hidden="true" />
            <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Caută un serviciu…" data-testid="cj-search-input"
              aria-label="Caută un serviciu"
              className="w-full min-h-[54px] pl-12 pr-4 py-3.5 rounded-full border border-slate-200 bg-white text-base shadow-sm outline-none focus:border-[#166534] transition-colors" />
          </label>
        </div>
        <TrustStrip />
        {filtered ? (
          <div className="mt-7 px-5 space-y-3 md:grid md:grid-cols-2 md:gap-3 md:space-y-0">
            {filtered.map(c => (
              c.badge
                ? <FeaturedCard key={c.id} icon={c.icon} label={c.label} sub={c.price} badge={c.badge} image={c.image} onClick={() => onPickCategory(c)} testid={`cj-feat-${c.id}`} />
                : <CategoryCard key={c.id} icon={c.icon} label={c.label} sub={c.price} onClick={() => onPickCategory(c)} testid={`cj-grid-${c.id}`} />
            ))}
            {filtered.length === 0 && <p className="text-center text-sm text-slate-500 py-8 md:col-span-2" data-testid="cj-search-empty">Nu am găsit servicii pentru „{query}"</p>}
          </div>
        ) : (
          <>
            <section className="mt-9 px-5 cj-reveal" style={{ animationDelay: "0.1s" }}>
              <SectionTitle>Serviciile noastre semnătură</SectionTitle>
              <div className="mt-3 grid gap-3 md:grid-cols-2 md:gap-4">
                {FEATURED.map(c => (
                  <FeaturedCard key={c.id} icon={c.icon} label={c.label} sub={c.price} badge={c.badge} image={c.image}
                    onClick={() => onPickCategory(c)} testid={`cj-feat-${c.id}`} />
                ))}
              </div>
            </section>
            <section className="mt-9 px-5 pb-4 cj-reveal" style={{ animationDelay: "0.2s" }}>
              <SectionTitle>Servicii pentru casă și șantier</SectionTitle>
              <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
                {CATEGORIES.map(c => (
                  <CategoryCard key={c.id} icon={c.icon} label={c.label} sub={c.price} onClick={() => onPickCategory(c)} testid={`cj-grid-${c.id}`} />
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
};

const ContactStep = ({ contact, setContact, touched, setTouched }) => {
  const phoneBad = touched.phone && contact.phone.replace(/\D/g, "").length < 9;
  const nameBad = touched.name && contact.name.trim().length < 3;
  const emailBad = touched.email && contact.email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(contact.email);
  return (
    <div className="px-5 pt-6" data-testid="cj-contact-step">
      <h2 className="xos-display text-2xl md:text-3xl font-medium tracking-tight text-slate-900 leading-snug">Unde îți trimitem ofertele?</h2>
      <p className="mt-1.5 text-sm text-slate-500">Doar 2 câmpuri obligatorii. Fără spam, promitem.</p>
      <div className="mt-5 space-y-3">
        <TextField label="Numele tău" required value={contact.name} onChange={v => setContact(c => ({ ...c, name: v }))}
          onBlur={() => setTouched(t => ({ ...t, name: true }))} error={nameBad ? "Numele pare prea scurt." : ""}
          autoComplete="name" placeholder="ex: Andrei Popescu" testid="cj-contact-name" />
        <TextField label="Telefon" required value={contact.phone} onChange={v => setContact(c => ({ ...c, phone: v }))}
          onBlur={() => setTouched(t => ({ ...t, phone: true }))} error={phoneBad ? "Numărul pare incomplet — verifică cifrele." : ""}
          type="tel" inputMode="tel" autoComplete="tel" placeholder="ex: 07xx xxx xxx" testid="cj-contact-phone" />
        <TextField label="Email" optional value={contact.email} onChange={v => setContact(c => ({ ...c, email: v }))}
          onBlur={() => setTouched(t => ({ ...t, email: true }))} error={emailBad ? "Adresa de email nu pare validă." : ""}
          type="email" inputMode="email" autoComplete="email" placeholder="ex: andrei@email.ro" testid="cj-contact-email" />
        <p className="-mt-1 text-[11px] text-slate-500">Cu email primești automat actualizări despre ofertele tale.</p>
        <label className="flex items-start gap-3 cursor-pointer min-h-[44px]" data-testid="cj-consent-label">
          <input type="checkbox" checked={contact.consent} onChange={e => setContact(c => ({ ...c, consent: e.target.checked }))}
            data-testid="cj-consent-checkbox" className="mt-0.5 w-5 h-5 rounded border-slate-300 accent-[#166534]" />
          <span className="text-xs text-slate-600">Sunt de acord cu prelucrarea datelor pentru a primi oferte de la specialiști verificați (GDPR).</span>
        </label>
      </div>
    </div>
  );
};

const FlowView = ({ category, onDone, onExit }) => {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [contact, setContact] = useState({ name: "", phone: "", email: "", consent: false });
  const [touched, setTouched] = useState({});

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onExit(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onExit]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const total = QUESTIONS.length + 1;
  const isContact = step === QUESTIONS.length;
  const progress = ((step + 1) / total) * 100;

  useEffect(() => { if (isContact) track("cj_contact_view", { category: category.id }); }, [isContact, category.id]);

  const phoneOk = contact.phone.replace(/\D/g, "").length >= 9;
  const canSubmit = contact.name.trim().length >= 3 && phoneOk && contact.consent;

  const submit = async () => {
    setSending(true); setError("");
    try {
      const r = await axios.post(`${API}/public/client-junior/request`, {
        name: contact.name, phone: contact.phone, email: contact.email,
        category: category.id, category_label: category.label, answers, consent: contact.consent,
      });
      track("cj_submitted", { category: category.id });
      onDone(answers, r.data.request_number);
    } catch (e) {
      setError(e?.response?.data?.detail || "Nu am putut trimite cererea. Verifică datele și încearcă din nou.");
    } finally { setSending(false); }
  };

  const next = () => {
    if (isContact) return submit();
    track("cj_step", { step: QUESTIONS[step].key, category: category.id });
    setStep(step + 1);
  };

  const q = !isContact ? QUESTIONS[step] : null;
  const selected = q ? answers[q.key] : null;
  const stepLabels = [...QUESTIONS.map(x => x.q), "Datele tale"];
  const shortLabels = ["Locație", "Detalii", "Termen", "Contact"];
  return (
    <div className="pb-36" data-testid="cj-flow-view">
      <Header title={category.label} onBack={() => (step === 0 ? onExit() : setStep(step - 1))} onClose={onExit} />
      <div className="h-1 bg-slate-100" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={total}>
        <div className="h-full transition-all duration-300 rounded-r-full" style={{ width: `${progress}%`, background: CJ_ACCENT }} data-testid="cj-progress-bar" />
      </div>
      <div className="md:max-w-md md:mx-auto">
        <div>
          <div className="px-5 pt-4 flex items-center justify-between gap-3">
            <StepDots total={total} current={step} labels={stepLabels} shortLabels={shortLabels} onJump={setStep} />
            <span className="text-xs text-slate-500">Preț mediu: <span className="font-bold text-slate-900 font-mono">{category.price}</span></span>
          </div>
          {isContact ? (
            <ContactStep contact={contact} setContact={setContact} touched={touched} setTouched={setTouched} />
          ) : (
            <QuestionCard question={q.q} hint={q.hint}>
              {q.options.map((opt, i) => (
                <OptionRadio key={opt} label={opt} selected={selected === opt} testid={`cj-option-${q.key}-${i}`}
                  onSelect={() => setAnswers(a => ({ ...a, [q.key]: opt }))} />
              ))}
            </QuestionCard>
          )}
          {error && <p className="px-5 mt-3 text-sm font-semibold text-rose-600" role="alert" data-testid="cj-submit-error">{error}</p>}
        </div>
      </div>
      <StickyCTA label={isContact ? (sending ? "Se trimite…" : "Trimite cererea") : "Continuă"}
        disabled={isContact ? (!canSubmit || sending) : !selected} onClick={next} testid="cj-continue-btn" />
    </div>
  );
};

const NEXT_STEPS = [
  "Analizăm cererea și o trimitem specialiștilor potriviți",
  "Primești oferte de la specialiști verificați, în max. 24h",
  "Alegi oferta care îți place și programezi lucrarea",
];

const ConfirmView = ({ category, requestNumber, onGoJobs }) => (
  <div className="min-h-screen pb-10 flex flex-col bg-[#EDF7EF]" data-testid="cj-confirm-view">
    <div className="flex-1 flex flex-col items-center justify-center px-6 text-center pt-12">
      <span className="w-20 h-20 rounded-full flex items-center justify-center mb-6 shadow-[0_16px_48px_-16px_rgba(204,255,0,0.6)]" style={{ background: CJ_ACCENT }}>
        <PartyPopper className="w-9 h-9 text-black" aria-hidden="true" />
      </span>
      <h1 className="xos-display text-3xl font-medium tracking-tight text-slate-900 leading-snug">Cererea ta a fost trimisă!</h1>
      <p className="mt-2 text-sm text-slate-600 flex items-center justify-center gap-1 flex-wrap">{category.label} · Nr. <CopyBadge value={requestNumber} testid="cj-request-number" /></p>
      <div className="mt-6 w-full max-w-sm rounded-3xl bg-white border border-slate-100 p-5 text-left shadow-sm">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Ce urmează</h2>
        <ol className="mt-3">
          {NEXT_STEPS.map((s, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="flex flex-col items-center self-stretch">
                <span className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-black text-black shrink-0" style={{ background: CJ_ACCENT }}>{i + 1}</span>
                {i < NEXT_STEPS.length - 1 && <span className="w-px flex-1 min-h-[16px] bg-[#166534]/30" aria-hidden="true" />}
              </span>
              <span className="text-sm text-slate-700 pb-4">{s}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
    <div className="px-5 mt-8 space-y-2 max-w-md mx-auto w-full">
      <button onClick={onGoJobs} data-testid="cj-go-jobs-btn"
        className="w-full min-h-[52px] py-4 rounded-full text-base font-bold text-black shadow-[0_10px_36px_-12px_rgba(204,255,0,0.55)] active:scale-[0.98] transition-transform" style={{ background: CJ_ACCENT }}>
        Vezi cererea mea
      </button>
      <a href="/register" data-testid="cj-create-account-link"
        className="block w-full min-h-[44px] py-2.5 text-center text-sm font-semibold text-[#166534]">
        Creează cont gratuit — urmărești ofertele live
      </a>
    </div>
  </div>
);

const QUESTION_LABELS = { where: "Unde ai nevoie de serviciu?", size: "Cât de mare e lucrarea?", when: "Când ai avea nevoie?" };

const JobsView = ({ request }) => (
  <div className="pb-24 max-w-md mx-auto" data-testid="cj-jobs-view">
    <div className="px-5 pt-6"><h1 className="xos-display text-2xl font-medium tracking-tight text-slate-900">Lucrările mele</h1></div>
    {!request ? (
      <div className="px-6 py-16 text-center text-sm text-slate-500" data-testid="cj-jobs-empty">Nicio lucrare încă. Solicită primul serviciu din tab-ul „Solicită".</div>
    ) : (
      <div className="mx-5 mt-4 rounded-3xl border border-slate-100 bg-white shadow-sm p-5" data-testid="cj-job-card">
        <div className="font-black text-slate-900">{request.category.label}</div>
        <div className="mt-4 space-y-0">
          <div className="flex items-start gap-3">
            <div className="flex flex-col items-center"><CircleCheck className="w-5 h-5 text-[#166534]" aria-hidden="true" /><span className="w-px h-8 bg-slate-200" /></div>
            <div className="text-sm font-bold text-slate-900">Cerere trimisă — așteaptă oferte</div>
          </div>
          <div className="flex items-start gap-3">
            <Circle className="w-5 h-5 text-slate-300" aria-hidden="true" />
            <div className="text-sm font-medium text-slate-500">Alege-ți profesionistul</div>
          </div>
        </div>
        <div className="mt-5 pt-4 border-t border-slate-100 space-y-3">
          {Object.entries(request.answers).map(([k, v]) => (
            <div key={k}>
              <div className="text-xs font-bold text-slate-900">{QUESTION_LABELS[k]}</div>
              <div className="text-sm text-slate-600">{v}</div>
            </div>
          ))}
          <div>
            <div className="text-xs font-bold text-slate-900">Numărul cererii</div>
            <div className="text-sm text-slate-600 font-mono">{request.number}</div>
          </div>
        </div>
      </div>
    )}
  </div>
);

const PlaceholderView = ({ icon: Icon, title, text, testid }) => (
  <div className="px-6 py-20 text-center" data-testid={testid}>
    <Icon className="w-10 h-10 mx-auto text-slate-300" aria-hidden="true" />
    <h2 className="mt-3 xos-display text-xl font-medium text-slate-900">{title}</h2>
    <p className="mt-1 text-sm text-slate-500">{text}</p>
  </div>
);

export default function ClientJuniorDashboard() {
  const [tab, setTab] = useState("home");
  const [view, setView] = useState("home"); // home | flow | confirm
  const [category, setCategory] = useState(null);
  const [request, setRequest] = useState(null);
  const [requestNumber, setRequestNumber] = useState(null);

  useEffect(() => { track("cj_view"); }, []);

  const startFlow = (c) => { track("cj_flow_start", { category: c.id }); setCategory(c); setView("flow"); };
  const finishFlow = (answers, number) => {
    setRequest({ category, answers, number });
    setRequestNumber(number);
    setView("confirm");
  };
  const goHome = () => { setView("home"); setTab("home"); };

  return (
    <div className="min-h-screen bg-[#FAFBFA] cv2-scope" data-testid="client-junior-page">
      <div className="min-h-screen">
        {view === "flow" ? (
          <FlowView category={category} onDone={finishFlow} onExit={goHome} />
        ) : view === "confirm" ? (
          <ConfirmView category={category} requestNumber={requestNumber} onGoJobs={() => { setView("home"); setTab("jobs"); }} />
        ) : (
          <>
            {tab === "home" && <HomeView onPickCategory={startFlow} />}
            {tab === "jobs" && <JobsView request={request} />}
            {tab === "notifications" && <PlaceholderView icon={Bell} title="Notificări" text="Vei vedea aici ofertele și noutățile tale." testid="cj-notifications-view" />}
            {tab === "settings" && <PlaceholderView icon={Settings} title="Setări" text="Profil, notificări și preferințe — în curând." testid="cj-settings-view" />}
            <BottomNav active={tab} onChange={setTab} />
          </>
        )}
      </div>
    </div>
  );
}
