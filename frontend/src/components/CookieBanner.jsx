// PropManage — GDPR Cookie Consent. PPOS P3a-M2: compact bottom-left card,
// equal-prominence choices, never covers navigation or the page's primary CTA.
// Stores prefs in localStorage + (if logged in) syncs to /api/cookies/consent.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Cookie, X } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const STORAGE_KEY = "pm_cookie_consent_v1";

export const CookieBanner = () => {
  const [open, setOpen] = useState(false);
  const [customize, setCustomize] = useState(false);
  const [prefs, setPrefs] = useState({
    functional: true,   // always true — cannot be disabled (auth, sessions)
    analytics: false,
    marketing: false,
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setOpen(true);
      } else {
        const saved = JSON.parse(raw);
        setPrefs({ functional: true, analytics: !!saved.analytics, marketing: !!saved.marketing });
      }
    } catch {
      setOpen(true);
    }
  }, []);

  // Mobile: rezervă spațiu sub conținut cât timp banner-ul e deschis, ca să nu acopere
  // CTA-uri (ex. „Explorează mai mult"). Pe desktop banner-ul stă în colț, fără impact.
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const apply = () => document.documentElement.style.setProperty("--pm-cookie-h", (open && !mq.matches) ? "168px" : "0px");
    apply();
    mq.addEventListener("change", apply);
    return () => {
      mq.removeEventListener("change", apply);
      document.documentElement.style.setProperty("--pm-cookie-h", "0px");
    };
  }, [open]);

  const persist = async (choice) => {
    const final = { functional: true, ...choice };
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...final, ts: new Date().toISOString() }));
    setPrefs(final);
    setOpen(false);
    setCustomize(false);
    // Anunță că alegerea de cookie a fost făcută (turul de bun venit poate porni acum).
    try { window.dispatchEvent(new CustomEvent("pm-cookie-consent")); } catch { /* noop */ }
    // GDPR — propagă alegerea către Google Consent Mode v2 (Google Ads AW-18423416296).
    // Marketing → cookies publicitare/remarketing (ad_*); Statistice → analytics_storage.
    try {
      if (typeof window.gtag === "function") {
        window.gtag("consent", "update", {
          ad_storage: final.marketing ? "granted" : "denied",
          ad_user_data: final.marketing ? "granted" : "denied",
          ad_personalization: final.marketing ? "granted" : "denied",
          analytics_storage: final.analytics ? "granted" : "denied",
        });
      }
    } catch (e) { /* noop */ }
    // GDPR — PostHog (statistici) pornește DOAR la consimțământul „Statistice".
    try {
      if (window.posthog) {
        if (final.analytics) window.posthog.opt_in_capturing();
        else window.posthog.opt_out_capturing();
      }
    } catch (e) { /* noop */ }
    try {
      await axios.post(`${API}/api/cookies/consent`, {
        functional_cookies_accepted: true,
        analytics_cookies_accepted: !!final.analytics,
        marketing_cookies_accepted: !!final.marketing,
      }, { withCredentials: true });
    } catch (e) {
      console.warn("[CookieBanner] sync failed:", e?.message);
    }
  };

  const acceptAll = () => persist({ analytics: true, marketing: true });
  const rejectOptional = () => persist({ analytics: false, marketing: false });
  const saveCustom = () => persist({ analytics: prefs.analytics, marketing: prefs.marketing });

  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); setCustomize(true); }}
        className="pm-float-left-2 w-9 h-9 rounded-full bg-[#0f0f0f] border border-white/10 hover:border-[#ccff00]/40 flex items-center justify-center opacity-50 hover:opacity-100 transition-opacity"
        title="Schimbă preferințele cookie"
        data-testid="cookie-banner-reopen"
      >
        <Cookie className="w-4 h-4 text-stone-300" />
      </button>
    );
  }

  return (
    <div className="pm-float-left-1 pm-float-panel w-[min(360px,calc(100vw-2rem))]" data-testid="cookie-banner">
      <div className="rounded-2xl bg-[#0a0a0a]/95 backdrop-blur-xl border border-white/10 shadow-2xl p-4">
        <div className="flex items-start gap-2.5">
          <Cookie className="w-4 h-4 text-[#ccff00] shrink-0 mt-0.5" />
          <p className="text-[11px] leading-snug flex-1" style={{ color: "#d6d3d1" }}>
            <span className="font-semibold" style={{ color: "#fafafa" }}>Cookie-uri:</span> funcționale obligatorii · statistice &amp; marketing opționale.
          </p>
          <button onClick={rejectOptional} className="p-1 rounded-full hover:bg-white/10 text-stone-500 hover:text-stone-300 transition-colors shrink-0" data-testid="cookie-banner-close" title="Refuză opționale">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {customize && (
          <div className="mt-3 space-y-1.5" data-testid="cookie-banner-customize">
            <label className="flex items-center gap-2 opacity-60 cursor-not-allowed">
              <input type="checkbox" checked={true} disabled className="w-3.5 h-3.5 accent-stone-500 shrink-0" />
              <span className="text-[11px] font-medium" style={{ color: "#d6d3d1" }}>Funcționale <span className="text-stone-500">(obligatorii)</span></span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={prefs.analytics}
                onChange={e => setPrefs(p => ({ ...p, analytics: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#ccff00] shrink-0"
                data-testid="cookie-pref-analytics" />
              <span className="text-[11px] font-medium" style={{ color: "#d6d3d1" }}>Statistice</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={prefs.marketing}
                onChange={e => setPrefs(p => ({ ...p, marketing: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#ccff00] shrink-0"
                data-testid="cookie-pref-marketing" />
              <span className="text-[11px] font-medium" style={{ color: "#d6d3d1" }}>Marketing</span>
            </label>
          </div>
        )}

        <div className="mt-3 flex items-center gap-1.5 flex-wrap">
          <button onClick={acceptAll} className="px-3.5 py-1.5 rounded-full text-[11px] font-semibold bg-white/10 border border-white/15 hover:bg-white/15 transition-colors" style={{ color: "#fafafa" }} data-testid="cookie-accept-all">
            Accept toate
          </button>
          <button onClick={rejectOptional} className="px-3.5 py-1.5 rounded-full text-[11px] font-semibold bg-white/10 border border-white/15 hover:bg-white/15 transition-colors" style={{ color: "#fafafa" }} data-testid="cookie-reject-optional">
            Refuz
          </button>
          {!customize ? (
            <button onClick={() => setCustomize(true)} className="px-2.5 py-1.5 rounded-full text-[11px] font-medium text-stone-400 hover:text-stone-200 transition-colors" data-testid="cookie-customize">
              Personalizează
            </button>
          ) : (
            <button onClick={saveCustom} className="px-3 py-1.5 rounded-full text-[11px] font-bold text-[#ccff00] hover:bg-white/5 transition-colors" data-testid="cookie-save-custom">
              Salvează
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CookieBanner;
