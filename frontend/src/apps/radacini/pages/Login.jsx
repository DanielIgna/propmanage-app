import React, { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, Sprout } from "lucide-react";
import { toast } from "sonner";
import { useAuth, formatApiError } from "../../../auth";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { supabase } from "../../../lib/supabase";

// Intrarea în Rădăcini: același cont ca în PropManage, dar cu identitatea Rădăcini.
// `next` e acceptat doar dacă rămâne în /radacini (fără redirecționări în afara aplicației).
const safeNext = (raw) =>
  raw && /^\/radacini(?:[/?#]|$)/.test(raw) && !raw.startsWith("/radacini/login") ? raw : "/radacini";

// Login Google: același flux ca în PropManage (aceeași adresă de întoarcere /auth/callback, deja înregistrată).
// Înainte de redirect salvăm destinația Rădăcini; AuthCallback o citește și te aduce înapoi aici.
function startGoogleLogin(next) {
  try {
    sessionStorage.setItem("pm_oauth_next", next);
  } catch { /* storage indisponibil: după login ajungi în panoul rolului */ }
  const redirectUri = window.location.origin + "/auth/callback";
  if (supabase && process.env.NEXT_PUBLIC_SUPABASE_GOOGLE === "true") {
    supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${redirectUri}?sb=1`, queryParams: { prompt: "select_account" } },
    });
    return;
  }
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  if (!googleClientId) {
    toast.error("Autentificarea cu Google nu este configurată. Folosește email și parolă.");
    return;
  }
  const params = new URLSearchParams({
    client_id: googleClientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid email profile",
    access_type: "online",
    prompt: "select_account",
  });
  window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export default function Login() {
  const { user, login } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = safeNext(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const prev = document.title;
    document.title = "Intră în cont · Rădăcini";
    return () => {
      document.title = prev;
    };
  }, []);

  if (user) return <Navigate to={next} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim(), password, totpCode || undefined);
      navigate(next, { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      // Backend-ul cere codul 2FA prin 202 / detail.error="totp_required" (același flux ca în PropManage).
      if (status === 202 || detail?.error === "totp_required" || formatApiError(err).includes("totp_required")) {
        setNeedsTotp(true);
      } else {
        setError(formatApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 bg-slate-50 dark:bg-[#0b0c0d]" data-testid="radacini-login">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-emerald-600/15 flex items-center justify-center mb-3">
            <Sprout className="w-6 h-6 text-emerald-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Rădăcini</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Pământ, oameni și hrană locală — județul Cluj</p>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] p-6 space-y-4"
        >
          <div className="space-y-1.5">
            <Label htmlFor="rad-email">Email</Label>
            <Input id="rad-email" type="email" autoComplete="email" required value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="nume@exemplu.ro" data-testid="radacini-login-email" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="rad-password">Parolă</Label>
            <Input id="rad-password" type="password" autoComplete="current-password" required value={password}
              onChange={(e) => setPassword(e.target.value)} data-testid="radacini-login-password" />
          </div>
          {needsTotp && (
            <div className="space-y-1.5">
              <Label htmlFor="rad-totp">Cod de autentificare (2FA)</Label>
              <Input id="rad-totp" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)} data-testid="radacini-login-totp" />
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400" role="alert" data-testid="radacini-login-error">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5"
            data-testid="radacini-login-submit"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Intră în Rădăcini
          </button>
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <div className="flex-1 h-px bg-slate-200 dark:bg-white/10" />
            sau
            <div className="flex-1 h-px bg-slate-200 dark:bg-white/10" />
          </div>
          <button
            type="button"
            onClick={() => startGoogleLogin(next)}
            className="w-full flex items-center justify-center gap-3 rounded-xl bg-white text-black border border-slate-200 py-2.5 text-sm font-medium hover:bg-slate-100"
            data-testid="radacini-google-login"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continuă cu Google
          </button>
          <p className="text-xs text-center text-slate-500 dark:text-slate-400">
            Nu ai cont?{" "}
            <Link to={`/register?next=${encodeURIComponent(next)}`} className="font-semibold text-emerald-600 hover:underline">
              Creează unul
            </Link>
            <br />
            Contul este același cu cel din PropManage.
          </p>
          <p className="text-xs text-center text-slate-500 dark:text-slate-400">
            <Link to="/radacini/despre" className="hover:underline">Despre și contact</Link>
            {" · "}
            <Link to="/radacini/termeni" className="hover:underline">Termeni</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
