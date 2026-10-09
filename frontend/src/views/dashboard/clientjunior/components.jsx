import React from "react";
import { Check, Search, Briefcase, Bell, Settings, ChevronRight, ShieldCheck, Clock, BadgeCheck, Copy as CopyIcon } from "lucide-react";

// Ink accent AA pe alb (light); în dark cv2-scope se remapează automat la #ccff00
export const CJ_GREEN = "#166534";
export const CJ_GREEN_SOFT = "rgba(21,128,61,0.08)";
// Accent luminos brand (fill) — text negru obligatoriu peste el
export const CJ_ACCENT = "#ccff00";

// ── QuestionCard: o singură întrebare pe ecran (Hick's Law) ──────────────────
export const QuestionCard = ({ question, hint, children }) => (
  <div className="px-5 pt-6" data-testid="cj-question-card">
    <h2 className="xos-display text-2xl md:text-3xl font-medium tracking-tight text-slate-900 leading-snug">{question}</h2>
    {hint && <p className="mt-1.5 text-sm text-slate-500">{hint}</p>}
    <div className="mt-5 space-y-3">{children}</div>
  </div>
);

// ── OptionRadio: opțiune mare (≥56px), feedback instant ──────────────────────
export const OptionRadio = ({ label, selected, onSelect, testid }) => (
  <button onClick={onSelect} data-testid={testid} role="radio" aria-checked={selected}
    className={`w-full min-h-[56px] flex items-center gap-3 px-4 py-4 rounded-2xl border text-left transition-colors ${
      selected ? "border-[#166534] bg-[#166534]/5" : "border-slate-200 bg-white hover:border-slate-300 active:bg-slate-50"}`}>
    <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
      selected ? "border-transparent bg-[#ccff00]" : "border-slate-300 bg-white"}`}>
      {selected && <Check className="w-3.5 h-3.5 text-black" strokeWidth={3.5} />}
    </span>
    <span className={`text-base ${selected ? "font-bold text-slate-900" : "font-medium text-slate-700"}`}>{label}</span>
  </button>
);

// ── StickyCTA: un singur buton principal, mereu vizibil (Fitts) ──────────────
export const StickyCTA = ({ label, onClick, disabled, secondary, testid }) => (
  <div className="fixed bottom-0 left-0 right-0 z-[60] px-5 pb-5 pt-3 bg-gradient-to-t from-white via-white to-transparent">
    <div className="max-w-md mx-auto space-y-2">
      <button onClick={onClick} disabled={disabled} data-testid={testid || "cj-sticky-cta"} aria-disabled={disabled}
        className={`w-full min-h-[52px] py-4 rounded-full text-base font-bold transition-transform ${
          disabled ? "bg-slate-200 text-slate-500" : "bg-[#ccff00] text-black active:scale-[0.98] shadow-[0_10px_36px_-12px_rgba(204,255,0,0.55)]"}`}>
        {label}
      </button>
      {secondary && (
        <button onClick={secondary.onClick} data-testid="cj-secondary-cta"
          className="w-full min-h-[44px] py-2 text-sm font-semibold text-rose-600">{secondary.label}</button>
      )}
    </div>
  </div>
);

// ── StepDots: pași clickabili cu stare + label vizibil (Nielsen: recunoaștere) ─
export const StepDots = ({ total, current, labels, shortLabels, onJump }) => (
  <ol className="flex items-start gap-2.5" aria-label={`Pasul ${current + 1} din ${total}`} data-testid="cj-step-dots">
    {Array.from({ length: total }).map((_, i) => {
      const done = i < current;
      return (
        <li key={i} className="flex flex-col items-center gap-0.5">
          <button onClick={() => done && onJump(i)} disabled={!done} title={labels?.[i]}
            data-testid={`cj-step-dot-${i}`} aria-label={`${labels?.[i] || `Pasul ${i + 1}`}${done ? " — completat, apasă pentru a edita" : i === current ? " — pasul curent" : ""}`}
            aria-current={i === current ? "step" : undefined}
            className={`min-w-[28px] min-h-[28px] rounded-full text-[11px] font-black flex items-center justify-center transition-colors ${
              done ? "bg-[#ccff00] text-black cursor-pointer cj-dot-pop" :
              i === current ? "border-2 border-[#166534] text-[#166534] bg-white" :
              "border-2 border-slate-200 text-slate-400 bg-white"}`}>
            {done ? <Check className="w-3.5 h-3.5" strokeWidth={3.5} /> : i + 1}
          </button>
          {shortLabels?.[i] && (
            <span className={`text-[9px] font-bold leading-none ${i === current ? "text-[#166534]" : "text-slate-500"}`}>{shortLabels[i]}</span>
          )}
        </li>
      );
    })}
  </ol>
);

// ── TextField: câmp cu label vizibil permanent (Nielsen — recunoaștere) ──────
export const TextField = ({ label, optional, required, value, onChange, onBlur, error, type = "text", autoComplete, placeholder, testid, inputMode }) => (
  <label className="block">
    <span className="text-sm font-bold text-slate-900">
      {label} {required && <span className="text-rose-600" aria-hidden="true">*</span>}{optional && <span className="font-medium text-slate-500">(opțional)</span>}
    </span>
    <input value={value} onChange={(e) => onChange(e.target.value)} onBlur={onBlur} type={type} inputMode={inputMode}
      autoComplete={autoComplete} placeholder={placeholder} data-testid={testid} aria-label={label} aria-invalid={!!error} aria-required={!!required}
      className={`mt-1.5 w-full min-h-[52px] px-4 py-3.5 rounded-2xl border bg-white text-base text-slate-900 outline-none transition-colors ${
        error ? "border-rose-400 focus:border-rose-500" : "border-slate-200 focus:border-[#166534]"}`} />
    <span aria-live="polite" className="block min-h-[2px]">
      {error && <span className="mt-1 block text-xs font-semibold text-rose-600 cj-reveal" data-testid={`${testid}-error`}>{error}</span>}
    </span>
  </label>
);

// ── TrustStrip: 3 elemente de încredere, uppercase, separate cu bullets ──────
const TRUST = [
  [ShieldCheck, "Specialiști verificați"],
  [Clock, "Răspuns în 24h"],
  [BadgeCheck, "Gratuit, fără obligații"],
];

export const TrustStrip = ({ items }) => (
  <div className="px-5 mt-5 flex items-center gap-2.5 flex-wrap" data-testid="cj-trust-strip">
    {(items || TRUST).map(([Icon, label], i) => (
      <React.Fragment key={label}>
        {i > 0 && <span className="w-1 h-1 rounded-full bg-slate-300 shrink-0" aria-hidden="true" />}
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
          <Icon className="w-3.5 h-3.5 shrink-0 text-[#166534]" aria-hidden="true" />{label}
        </span>
      </React.Fragment>
    ))}
  </div>
);

// ── CopyBadge: număr cerere cu copy-to-clipboard + feedback 1.2s ─────────────
export const CopyBadge = ({ value, testid }) => {
  const [copied, setCopied] = React.useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(value).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };
  return (
    <button onClick={copy} data-testid={testid} aria-label={`Copiază numărul ${value}`}
      className="inline-flex items-center gap-1.5 font-mono font-bold text-slate-900 min-h-[32px] px-2 py-0.5 rounded-lg hover:bg-black/5 transition-colors">
      {value}
      {copied ? <Check className="w-3.5 h-3.5 text-[#166534]" aria-hidden="true" /> : <CopyIcon className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />}
      <span aria-live="polite" className="sr-only">{copied ? "Copiat în clipboard" : ""}</span>
    </button>
  );
};

// ── BottomNav: max 4 destinații (Hick), glass dock, target ≥48px (Fitts) ─────
const NAV_ITEMS = [
  ["home", "Solicită", Search],
  ["jobs", "Lucrările mele", Briefcase],
  ["notifications", "Notificări", Bell],
  ["settings", "Setări", Settings],
];

export const BottomNav = ({ active, onChange }) => (
  <nav className="fixed bottom-0 left-0 right-0 z-30 xos-dock" data-testid="cj-bottom-nav" aria-label="Navigare principală">
    <div className="max-w-md mx-auto grid grid-cols-4">
      {NAV_ITEMS.map(([id, label, Icon]) => (
        <button key={id} onClick={() => { window.scrollTo({ top: 0 }); onChange(id); }} data-testid={`cj-nav-${id}`}
          aria-label={label} aria-current={active === id ? "page" : undefined}
          className="flex flex-col items-center gap-1 py-3 min-h-[56px]">
          <Icon className={`w-5 h-5 ${active === id ? "text-[#166534]" : "text-slate-400"}`} strokeWidth={active === id ? 2.5 : 2} aria-hidden="true" />
          <span className={`text-[10px] ${active === id ? "font-bold text-[#166534]" : "font-medium text-slate-500"}`}>{label}</span>
        </button>
      ))}
    </div>
  </nav>
);

// ── CategoryCard: serviciu "commodity" — tipografic minimal, fără chip repetitiv ─
export const CategoryCard = ({ icon: Icon, label, sub, onClick, testid }) => (
  <button onClick={onClick} data-testid={testid} aria-label={`Solicită ${label}`}
    className="group w-full min-h-[96px] rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-transform duration-300 hover:-translate-y-1 hover:shadow-lg active:scale-[0.98]">
    <Icon className="w-5 h-5 text-slate-400 group-hover:text-[#166534] transition-colors" strokeWidth={1.8} aria-hidden="true" />
    <div className="mt-3 text-sm font-bold text-slate-900 leading-tight">{label}</div>
    {sub && <div className="mt-1 text-[11px] font-mono text-slate-500">{sub}</div>}
  </button>
);

// ── FeaturedCard: serviciile semnătură (Digital Twin, Design) — fotografie hero ─
export const FeaturedCard = ({ icon: Icon, label, sub, badge, image, onClick, testid }) => (
  <button onClick={onClick} data-testid={testid} aria-label={`Solicită ${label}`}
    className="group relative w-full h-40 md:h-52 rounded-3xl overflow-hidden text-left shadow-lg transition-transform duration-300 hover:-translate-y-1 active:scale-[0.99]">
    {image ? (
      <img src={image} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
    ) : (
      <span className="absolute inset-0 bg-slate-900" aria-hidden="true" />
    )}
    <span className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/10" aria-hidden="true" />
    <span className="relative z-10 flex h-full flex-col justify-end p-5">
      <span className="text-[9px] font-bold uppercase tracking-[0.22em] text-[#ccff00]">{badge}</span>
      <span className="mt-1 flex items-end justify-between gap-3">
        <span className="min-w-0">
          <span className="block xos-display text-xl md:text-2xl font-medium leading-tight xos-on-image">{label}</span>
          <span className="mt-0.5 block text-xs font-mono xos-on-image-muted">{sub}</span>
        </span>
        <span className="shrink-0 w-10 h-10 rounded-full bg-white/15 backdrop-blur-md border border-white/25 flex items-center justify-center transition-transform duration-300 group-hover:translate-x-1">
          <ChevronRight className="w-5 h-5 xos-on-image" aria-hidden="true" />
        </span>
      </span>
    </span>
  </button>
);
