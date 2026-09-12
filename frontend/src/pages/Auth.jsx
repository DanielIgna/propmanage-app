// PropManage - Auth Pages (Login, Register)
import React, { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, ArrowRight, Sparkles, Languages } from "lucide-react";
import { useAuth, formatApiError } from "../auth";
import { useI18n } from "../i18n";
import { sendPassportConversion } from "../lib/passportTracker";

const Backdrop = () => (
  <div className="fixed inset-0 -z-10">
    <div className="absolute inset-0 bg-[#0a0a0b]" />
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-[#d4ff3a] blur-[200px] opacity-10" />
    <div className="absolute inset-0 dotted-bg opacity-20" />
  </div>
);

const TopBar = () => {
  const { lang, toggle } = useI18n();
  return (
    <div className="absolute top-0 left-0 right-0 flex justify-between items-center p-6 z-10">
      <Link to="/" className="flex items-center gap-2" data-testid="auth-logo">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
          <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
        </div>
        <span className="font-serif text-xl font-semibold">PropManage</span>
      </Link>
      <button onClick={toggle} className="flex items-center gap-2 px-3 py-1.5 glass rounded-full text-xs uppercase tracking-wider" data-testid="lang-toggle">
        <Languages className="w-3.5 h-3.5" />
        {lang.toUpperCase()}
      </button>
    </div>
  );
};

export const LoginPage = () => {
  const { user, login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Read ?next=/path to redirect after login (e.g., from email links)
  const nextPath = new URLSearchParams(window.location.search).get("next");
  const _isSafeNext = (p) => typeof p === "string" && p.startsWith("/") && !p.startsWith("//");
  const safeNext = _isSafeNext(nextPath) ? nextPath : null;

  const roleHome = (role) => ({
    city_partner: "/partner/dashboard",
    marketplace_partner: "/partner/marketplace",
    marketing_manager: "/admin/marketing",
  }[role] || `/${role}`);

  if (user && user !== false) return <Navigate to={safeNext || roleHome(user.role)} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const u = await login(email, password, totpCode || undefined);
      navigate(safeNext || roleHome(u.role));
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      // Backend returns 202 with detail.error="totp_required" via HTTPException; axios sees it as error
      if (status === 202 || (detail && detail.error === "totp_required") || formatApiError(err).includes("totp_required")) {
        setNeedsTotp(true);
        setError("");
      } else {
        setError(formatApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };
  
  // demoLogin eliminat (cod mort cu parolă admin greșită — semnalat de code review iter123)
  
  return (
    <div className="min-h-screen relative flex items-center justify-center p-6">
      <Backdrop />
      <TopBar />
      
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="glass-strong rounded-3xl p-10">
          <h1 className="font-serif text-4xl mb-2" data-testid="login-title">{t("login.title")}</h1>
          <p className="text-sm text-stone-400 mb-4">{t("login.subtitle")}</p>

          {/* Quick-win conversie (Growth Intelligence: /login = pagina #1 de abandon, 35.8%) */}
          <Link to="/register" data-testid="login-new-account-cta"
            className="flex items-center justify-between gap-3 mb-6 p-3.5 rounded-2xl border border-[#d4ff3a]/30 bg-[#d4ff3a]/10 hover:bg-[#d4ff3a]/20 transition group">
            <div>
              <div className="text-sm font-bold text-[#d4ff3a]">Nou pe PropManage?</div>
              <div className="text-xs text-stone-300">Creează cont gratuit într-un minut — Cartea Casei, specialiști verificați, plăți protejate.</div>
            </div>
            <ArrowRight className="w-4 h-4 text-[#d4ff3a] shrink-0 group-hover:translate-x-0.5 transition-transform" />
          </Link>
          
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("common.email")}</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)} required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50 transition"
                placeholder="name@example.com"
                data-testid="login-email"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("common.password")}</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50 transition"
                placeholder="••••••••"
                data-testid="login-password"
              />
            </div>
            {needsTotp && (
              <div>
                <label className="text-xs uppercase tracking-wider text-[#d4ff3a] mb-1.5 block">Cod 2FA (6 cifre)</label>
                <input
                  type="text" value={totpCode} onChange={e => setTotpCode(e.target.value)} required maxLength={6}
                  className="w-full bg-white/5 border border-[#d4ff3a]/30 rounded-xl px-4 py-3 text-center text-2xl tracking-widest font-mono focus:outline-none focus:border-[#d4ff3a]/70"
                  placeholder="123456"
                  data-testid="login-totp"
                  autoFocus
                />
                <div className="text-[10px] text-stone-500 mt-1">Introdu codul din aplicația ta authenticator</div>
              </div>
            )}
            {error && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3" data-testid="login-error">{error}</div>}
            <button type="submit" disabled={loading} className="pm-pill pm-pill-primary pm-pill-lg w-full disabled:opacity-50" data-testid="login-submit">
              {loading ? t("common.loading") : t("login.submit")}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
          
          {/* Google OAuth */}
          {/* REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH */}
          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] text-stone-500 uppercase tracking-wider">sau</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>
          <button
            type="button"
            onClick={() => {
              const redirectUri = window.location.origin + "/auth/callback";
              const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
              if (googleClientId) {
                // Direct Google OAuth (own Cloud project) — brands "PropManage" on Google consent screen
                const params = new URLSearchParams({
                  client_id: googleClientId,
                  redirect_uri: redirectUri,
                  response_type: "code",
                  scope: "openid email profile",
                  access_type: "online",
                  prompt: "select_account",
                });
                window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
              } else {
                // Fallback: Emergent-managed OAuth (legacy — used if own credentials missing)
                window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUri)}`;
              }
            }}
            className="w-full flex items-center justify-center gap-3 bg-white text-black py-3 rounded-xl text-sm font-medium hover:bg-stone-100 transition"
            data-testid="google-login-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continuă cu Google
          </button>
          
          <div className="mt-6 text-center text-xs text-stone-500">
            {t("login.noAccount")} <Link to="/register" className="text-[#d4ff3a] hover:underline" data-testid="login-register-link">{t("login.register")}</Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export const RegisterPage = () => {
  const { user, register } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const _params = new URLSearchParams(window.location.search);
  const referrerId = _params.get("ref");
  // GBOS P0.1 — invitație personală: codul se revendică după primul login (claimPendingInvite)
  const _inviteCode = _params.get("invite");
  if (_inviteCode) localStorage.setItem("pm_invite_code", _inviteCode);
  // PM-PILOT-001 — invitație de bloc: /register?binvite=<buildingId>, revendicată în BuildingHub
  const _bInvite = _params.get("binvite");
  if (_bInvite) localStorage.setItem("pm_building_invite", _bInvite);
  // Recruitment funnel (CIP-A): /register?role=specialist&category=<legacy>
  const _inviteCategory = _params.get("category");
  const _inviteRole = _params.get("role");
  const [form, setForm] = useState({
    email: "", password: "", name: "", role: _inviteRole === "specialist" ? "specialist" : "client", phone: "",
    specialty: _inviteCategory || "hvac",
    service_categories: [_inviteCategory || "hvac"],
    coverage_zones: ["Bucuresti-Sector1"],
    zone: "Bucuresti-Sector1",
    referrer_id: referrerId || undefined,
    terms_accepted: false,
    privacy_policy_accepted: false,
    marketing_consent: false,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  if (user && user !== false) return <Navigate to={`/${user.role}`} replace />;

  const SPECIALTIES = [
    { value: "hvac", label: "HVAC / Climatizare", icon: "🌬" },
    { value: "electric", label: "Electric", icon: "⚡" },
    { value: "plumbing", label: "Sanitar / Instalații apă", icon: "💧" },
    { value: "interior_design", label: "Design Interior", icon: "🏠" },
    { value: "zugravit", label: "Zugrăveli / Finisaje", icon: "🎨" },
    { value: "parchet", label: "Pardoseli / Parchet", icon: "🪵" },
    { value: "faianta", label: "Faianță & Gresie", icon: "🧱" },
    { value: "gips_carton", label: "Gips-carton", icon: "📐" },
    { value: "handyman", label: "Handyman / Reparații", icon: "🔧" },
    { value: "constructii", label: "Construcții / Zidărie", icon: "🏗" },
    { value: "acoperisuri", label: "Acoperișuri", icon: "🏚" },
    { value: "fatade_termoizolatii", label: "Fațade & Termoizolații", icon: "🧊" },
    { value: "tamplarie", label: "Tâmplărie & Ferestre", icon: "🚪" },
    { value: "amenajari_exterioare", label: "Amenajări exterioare", icon: "🌱" },
    { value: "other", label: "Alte servicii", icon: "🛠" },
  ];

  const ZONES = [
    "Bucuresti-Sector1", "Bucuresti-Sector2", "Bucuresti-Sector3",
    "Bucuresti-Sector4", "Bucuresti-Sector5", "Bucuresti-Sector6",
    "Cluj-Centru", "Cluj-Manastur",
    "Timisoara-Iosefin", "Timisoara-Fabric",
    "Iasi-Centru", "Brasov-Centru", "Constanta-Centru",
  ];

  const toggleCategory = (val) => {
    const exists = form.service_categories.includes(val);
    const newCats = exists ? form.service_categories.filter(c => c !== val) : [...form.service_categories, val];
    setForm({ ...form, service_categories: newCats, specialty: newCats[0] || val });
  };

  const toggleZone = (val) => {
    const exists = form.coverage_zones.includes(val);
    setForm({ ...form, coverage_zones: exists ? form.coverage_zones.filter(z => z !== val) : [...form.coverage_zones, val] });
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (form.role === "specialist" && form.service_categories.length === 0) {
        throw new Error("Selectează cel puțin o categorie de specialitate");
      }
      if (form.role === "specialist" && form.coverage_zones.length === 0) {
        throw new Error("Selectează cel puțin o zonă de acoperire");
      }
      const phoneDigits = (form.phone || "").replace(/[^\d+]/g, "");
      if (form.role === "specialist" && !phoneDigits) throw new Error("Numărul de telefon este obligatoriu pentru specialiști");
      if (phoneDigits && !/^\+?\d{8,15}$/.test(phoneDigits)) throw new Error("Format telefon invalid. Folosește +40 7XX XXX XXX sau 07XX XXX XXX");
      if (!form.terms_accepted) throw new Error("Trebuie să accepți Termenii și Condițiile");
      if (!form.privacy_policy_accepted) throw new Error("Trebuie să accepți Politica de Confidențialitate");      const u = await register({ ...form, phone: phoneDigits });
      sendPassportConversion();
      import("../lib/analytics").then(({ trackConversion, identify }) => {
        identify(u.id || u._id || "", u.role || "");
        trackConversion("sign_up");
      }).catch(() => {});
      navigate(`/${u.role}`);
    } catch (err) {
      setError(err.message || formatApiError(err));
    } finally { setLoading(false); }
  };
  
  return (
    <div className="min-h-screen relative flex items-center justify-center p-6 py-12">
      <Backdrop /><TopBar />
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="glass-strong rounded-3xl p-8 sm:p-10">
          {referrerId && (
            <div className="mb-6 bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 rounded-2xl p-4 flex items-start gap-3" data-testid="referral-banner">
              <Sparkles className="w-5 h-5 text-[#d4ff3a] shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-medium text-[#d4ff3a]">Te-ai înregistrat prin invitație 🎉</div>
                <div className="text-stone-400 mt-0.5">Prietenul tău va primi +500 tokeni și Digital Twin activat când finalizezi prima cerere.</div>
              </div>
            </div>
          )}
          <h1 className="font-serif text-4xl mb-2" data-testid="register-title">{t("register.title")}</h1>
          <p className="text-sm text-stone-400 mb-6">{t("register.subtitle")}</p>
          
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("common.name")}</label>
              <input type="text" required value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="register-name" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("common.email")}</label>
              <input type="email" required value={form.email} onChange={e => setForm({...form, email: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="register-email" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("common.password")}</label>
              <input type="password" required minLength={6} value={form.password} onChange={e => setForm({...form, password: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="register-password" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Telefon {form.role === "specialist" ? <span className="text-red-400">*</span> : <span className="text-stone-500 lowercase">(opțional)</span>}</label>
              <input type="tel" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})}
                placeholder="+40 7XX XXX XXX sau 07XX XXX XXX"
                required={form.role === "specialist"}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="register-phone" />
              <div className="text-[10px] text-stone-500 mt-1">{form.role === "specialist" ? "Necesar pentru activare — te sunăm în 24h" : "Îl poți adăuga oricând mai târziu"}</div>
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{t("register.role")}</label>
              <div className="grid grid-cols-2 gap-2">
                {[{v:"client", l:t("register.client")}, {v:"specialist", l:t("register.specialist")}].map(o => (
                  <button type="button" key={o.v} onClick={() => setForm({...form, role: o.v})}
                    className={`py-3 rounded-xl text-sm border transition ${form.role === o.v ? "bg-[#d4ff3a]/15 border-[#d4ff3a]/50 text-white" : "bg-white/5 border-white/10 text-stone-400"}`}
                    data-testid={`register-role-${o.v}`}>{o.l}</button>
                ))}
              </div>
            </div>

            {/* SPECIALIST ONLY: Categories */}
            {form.role === "specialist" && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-4 overflow-hidden">
                <div>
                  <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">
                    Specialitățile tale <span className="text-stone-600">(selectează una sau mai multe)</span>
                  </label>
                  <div className="grid grid-cols-2 gap-2" data-testid="specialty-grid">
                    {SPECIALTIES.map(s => {
                      const sel = form.service_categories.includes(s.value);
                      return (
                        <button type="button" key={s.value} onClick={() => toggleCategory(s.value)}
                          className={`p-3 rounded-xl text-left text-xs border transition ${sel ? "bg-[#d4ff3a]/15 border-[#d4ff3a]/50 text-white" : "bg-white/5 border-white/10 text-stone-400 hover:bg-white/10"}`}
                          data-testid={`spec-${s.value}`}>
                          <div className="flex items-center gap-2">
                            <span className="text-base">{s.icon}</span>
                            <span className="font-medium">{s.label}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                  {form.service_categories.length > 0 && (
                    <div className="mt-2 text-[11px] text-stone-400">
                      Selectat: {form.service_categories.length} {form.service_categories.length === 1 ? "categorie" : "categorii"}
                    </div>
                  )}
                </div>

                <div>
                  <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">
                    Zone de acoperire <span className="text-stone-600">(unde lucrezi)</span>
                  </label>
                  <div className="grid grid-cols-2 gap-1.5 max-h-48 overflow-y-auto pr-1" data-testid="zone-grid">
                    {ZONES.map(z => {
                      const sel = form.coverage_zones.includes(z);
                      return (
                        <button type="button" key={z} onClick={() => toggleZone(z)}
                          className={`px-2.5 py-2 rounded-lg text-[11px] border transition ${sel ? "bg-[#d4ff3a]/15 border-[#d4ff3a]/50 text-white" : "bg-white/5 border-white/10 text-stone-400 hover:bg-white/10"}`}
                          data-testid={`zone-${z}`}>
                          {z.replace(/-/g, " ")}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}

            {/* CLIENT ONLY: Zone */}
            {form.role === "client" && (
              <div>
                <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Zona ta</label>
                <select value={form.zone} onChange={e => setForm({...form, zone: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                  data-testid="register-zone">
                  {ZONES.map(z => <option key={z} value={z}>{z.replace(/-/g, " ")}</option>)}
                </select>
              </div>
            )}

            {error && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3" data-testid="register-error">{error}</div>}

            {/* GDPR consent checkboxes — terms + privacy mandatory, marketing optional */}
            <div className="space-y-2.5 pt-2 border-t border-white/5">
              <label className="flex items-start gap-2.5 cursor-pointer group" data-testid="consent-terms-wrap">
                <input type="checkbox" checked={form.terms_accepted}
                  onChange={e => setForm({...form, terms_accepted: e.target.checked})}
                  className="mt-0.5 w-4 h-4 rounded accent-[#d4ff3a] shrink-0"
                  data-testid="consent-terms" />
                <span className="text-xs text-stone-300 leading-relaxed">
                  Accept <Link to="/terms" target="_blank" className="text-[#d4ff3a] underline hover:no-underline">Termenii și Condițiile</Link> <span className="text-red-400">*</span>
                </span>
              </label>
              <label className="flex items-start gap-2.5 cursor-pointer group" data-testid="consent-privacy-wrap">
                <input type="checkbox" checked={form.privacy_policy_accepted}
                  onChange={e => setForm({...form, privacy_policy_accepted: e.target.checked})}
                  className="mt-0.5 w-4 h-4 rounded accent-[#d4ff3a] shrink-0"
                  data-testid="consent-privacy" />
                <span className="text-xs text-stone-300 leading-relaxed">
                  Accept <Link to="/privacy" target="_blank" className="text-[#d4ff3a] underline hover:no-underline">Politica de Confidențialitate</Link> și prelucrarea datelor mele personale conform GDPR <span className="text-red-400">*</span>
                </span>
              </label>
              <label className="flex items-start gap-2.5 cursor-pointer group" data-testid="consent-marketing-wrap">
                <input type="checkbox" checked={form.marketing_consent}
                  onChange={e => setForm({...form, marketing_consent: e.target.checked})}
                  className="mt-0.5 w-4 h-4 rounded accent-[#d4ff3a] shrink-0"
                  data-testid="consent-marketing" />
                <span className="text-xs text-stone-400 leading-relaxed">
                  Sunt de acord să primesc oferte, promoții și comunicări comerciale prin email, SMS sau telefon (opțional, poți retrage oricând)
                </span>
              </label>
            </div>

            <button type="submit" disabled={loading || !form.terms_accepted || !form.privacy_policy_accepted || (form.role === "specialist" && !form.phone) || !form.name || !form.email} className="btn-accent w-full py-3 rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed" data-testid="register-submit">
              {loading ? t("common.loading") : t("register.submit")}
            </button>
          </form>
          <div className="mt-6 text-center text-xs text-stone-500">
            {t("register.hasAccount")} <Link to="/login" className="text-[#d4ff3a] hover:underline">Conectare</Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
