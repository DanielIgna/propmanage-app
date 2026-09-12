// Passport Analytics tracker (EO-026) — first-party, fără cookies de tracking.
const API = process.env.REACT_APP_BACKEND_URL;
const REF_KEY = "pm_passport_ref";
const VID_KEY = "pm_vid";
const REF_TTL = 30 * 24 * 3600 * 1000;

const vid = () => {
  let v = localStorage.getItem(VID_KEY);
  if (!v) {
    v = (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}${Math.random().toString(36).slice(2)}`)
      .replace(/-/g, "").slice(0, 32);
    localStorage.setItem(VID_KEY, v);
  }
  return v;
};

const srcFromUrl = () => {
  try { return new URLSearchParams(window.location.search).get("src") || ""; } catch { return ""; }
};

export const trackPassport = (slug, event, extra = {}) => {
  try {
    const body = JSON.stringify({
      visitor_id: vid(), event,
      referrer: document.referrer || "",
      src: extra.src || srcFromUrl(),
      duration_s: extra.duration_s || 0,
      screen_w: extra.screen_w || 0,
    });
    const url = `${API}/api/public/passport/${slug}/track`;
    if (navigator.sendBeacon) navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    else fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
  } catch { /* noop */ }
};

export const initPassportTracking = (slug) => {
  try { localStorage.setItem(REF_KEY, JSON.stringify({ slug, visitor_id: vid(), ts: Date.now() })); } catch { /* noop */ }
  const t0 = Date.now();
  trackPassport(slug, "view", { screen_w: window.innerWidth });
  const onLeave = () => trackPassport(slug, "leave", { duration_s: Math.min(Math.round((Date.now() - t0) / 1000), 3600) });
  window.addEventListener("pagehide", onLeave);
  return () => window.removeEventListener("pagehide", onLeave);
};

// După register: atribuie contul nou pașaportului care l-a adus (first-touch).
export const sendPassportConversion = () => {
  try {
    const ref = JSON.parse(localStorage.getItem(REF_KEY) || "null");
    if (!ref || Date.now() - ref.ts > REF_TTL) return;
    fetch(`${API}/api/track/passport-conversion`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: ref.slug, visitor_id: ref.visitor_id }),
    }).then(() => localStorage.removeItem(REF_KEY)).catch(() => {});
  } catch { /* noop */ }
};
