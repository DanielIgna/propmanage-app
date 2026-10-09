// PropManage — Email Verification Banner
// Non-blocking banner shown to logged-in users with email_verified=false.
import React, { useState } from "react";
import axios from "axios";
import { Mail, X, Loader2, CheckCircle2 } from "lucide-react";
import { useAuth } from "../auth";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const DISMISS_KEY = "pm_email_verify_dismissed_session";

export const EmailVerificationBanner = () => {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState(sessionStorage.getItem(DISMISS_KEY) === "1");
  const [sending, setSending] = useState(false);
  const [sentMsg, setSentMsg] = useState("");
  const [error, setError] = useState("");

  if (!user || user === false) return null;
  if (user.email_verified) return null;
  if (user.consent_grandfathered) return null; // existing users — grandfather, never bother
  if (dismissed) return null;

  const resend = async () => {
    setSending(true); setError(""); setSentMsg("");
    try {
      await axios.post(`${API}/api/auth/resend-verification`, {}, { withCredentials: true });
      setSentMsg("Email trimis! Verifică inbox-ul (și SPAM).");
    } catch (e) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      if (status === 429) setError(detail || "Așteaptă câteva minute înainte de retrimitere.");
      else setError(detail || "Eroare la trimitere.");
    } finally { setSending(false); }
  };

  const close = () => {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  };

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2.5" data-testid="email-verify-banner">
      <div className="max-w-7xl mx-auto flex items-center gap-3 flex-wrap">
        <Mail className="w-4 h-4 text-amber-300 shrink-0" />
        <div className="text-xs text-amber-100 flex-1 min-w-[200px]">
          {sentMsg ? (
            <span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> {sentMsg}</span>
          ) : error ? (
            <span className="text-red-300">{error}</span>
          ) : (
            <>Confirmă adresa de email <strong>{user.email}</strong> pentru a debloca toate funcționalitățile.</>
          )}
        </div>
        {!sentMsg && (
          <button onClick={resend} disabled={sending}
            className="text-xs px-3 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-medium flex items-center gap-1.5 disabled:opacity-50"
            data-testid="email-verify-resend">
            {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mail className="w-3 h-3" />}
            Retrimite emailul
          </button>
        )}
        <button onClick={close} className="text-amber-300/60 hover:text-amber-300" data-testid="email-verify-dismiss" title="Închide până la următorul login">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

export default EmailVerificationBanner;
