// Sticky banner shown at the top of the app while an admin is impersonating another user.
// GDPR: always visible, never dismissible (except by stopping impersonation explicitly).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ShieldAlert, LogOut, Clock } from "lucide-react";
import { useAuth } from "../auth";
import { API } from "../pages/DashShared";

const fmtCountdown = (secs) => {
  if (secs <= 0) return "expirat";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
};

export const ImpersonationBanner = () => {
  const { user, refreshUser } = useAuth();
  const imp = user?.impersonation;
  const [busy, setBusy] = useState(false);
  const [remainingSec, setRemainingSec] = useState(null);

  useEffect(() => {
    if (!imp?.started_at) { setRemainingSec(null); return; }
    const start = new Date(imp.started_at).getTime();
    const endAt = start + 7200 * 1000; // 2h TTL (matches backend)
    const tick = () => setRemainingSec(Math.max(0, Math.round((endAt - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [imp?.started_at]);

  if (!imp) return null;

  const stop = async () => {
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/admin/stop-impersonation`);
      await refreshUser();
      window.location.href = data?.redirect_to || "/admin";
    } catch (e) {
      alert(e?.response?.data?.detail || "Nu am putut ieși din impersonare.");
      setBusy(false);
    }
  };

  return (
    <div
      className="sticky top-0 left-0 right-0 z-[100] bg-red-600 text-white shadow-lg border-b border-red-800"
      data-testid="impersonation-banner"
      role="alert"
      aria-live="polite"
    >
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-1.5 sm:py-2 flex items-center gap-2 sm:gap-3 text-sm">
        <ShieldAlert className="w-5 h-5 shrink-0 animate-pulse" />
        <div className="flex-1 min-w-0">
          <div className="font-semibold truncate text-xs sm:text-sm" data-testid="impersonation-banner-target">
            Vizionezi ca <strong>{user.name || user.email}</strong> · rol: <strong>{user.role}</strong>
          </div>
          <div className="hidden sm:block text-[11px] text-red-100 truncate">
            Admin: <strong>{imp.admin_email}</strong> · sesiune jurnalizată GDPR (ID {imp.log_id?.slice(-8)})
          </div>
        </div>
        {remainingSec !== null && (
          <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-full bg-red-700/60 text-[11px] font-mono" data-testid="impersonation-banner-timer">
            <Clock className="w-3 h-3" />
            {fmtCountdown(remainingSec)}
          </div>
        )}
        <button
          onClick={stop}
          disabled={busy}
          className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-full bg-white text-red-700 hover:bg-red-50 text-xs font-bold disabled:opacity-60 shrink-0"
          data-testid="impersonation-banner-stop"
        >
          <LogOut className="w-3.5 h-3.5" />
          {busy ? "Ies..." : <><span className="sm:hidden">Ieși</span><span className="hidden sm:inline">Ieși din impersonare</span></>}
        </button>
      </div>
    </div>
  );
};

export default ImpersonationBanner;
