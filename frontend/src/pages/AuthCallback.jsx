// AuthCallback - handles TWO Google OAuth flows:
//   1. DIRECT flow (own Google Cloud project): `?code=...` query param → POST /api/auth/google/callback
//   2. EMERGENT flow (legacy fallback): `#session_id=...` URL fragment → POST /api/auth/google/session
// The button in Auth.jsx picks the flow at redirect-time based on REACT_APP_GOOGLE_CLIENT_ID.
// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS BEYOND WHAT'S BELOW.
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../auth";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AuthCallback = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const processed = useRef(false);
  const [error, setError] = useState("");
  const [flowLabel, setFlowLabel] = useState("");

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    // ---- Flow detection ----
    // 1) Direct Google OAuth returns `?code=...` (+ optionally `?state=...`).
    // 2) Emergent-managed OAuth returns `#session_id=...` in the URL fragment.
    const search = new URLSearchParams(window.location.search);
    const oauthCode = search.get("code");
    const oauthError = search.get("error"); // e.g. access_denied when user cancels
    const hashMatch = window.location.hash.match(/session_id=([^&]+)/);

    if (oauthError) {
      setError(`Google a returnat eroare: ${oauthError}. Încearcă din nou.`);
      return;
    }

    if (oauthCode) {
      // ============ DIRECT flow ============
      setFlowLabel("direct");
      const redirectUri = window.location.origin + "/auth/callback";
      (async () => {
        try {
          const { data } = await axios.post(
            `${API}/auth/google/callback`,
            { code: oauthCode, redirect_uri: redirectUri },
            { withCredentials: true }
          );
          // Clear query params from URL so back-button doesn't re-trigger the exchange
          window.history.replaceState(null, "", window.location.pathname);
          const me = await refreshUser();
          if (!me) {
            setError("Autentificarea Google a reușit dar cookie-ul a fost blocat. Activează cookies pentru propmanage.ro și încearcă din nou.");
            return;
          }
          navigate(`/${data.role || "client"}`, { replace: true });
        } catch (e) {
          const status = e?.response?.status;
          const detail = e?.response?.data?.detail || e.message || "Autentificare eșuată";
          setError(`[${status || "network"}] ${detail}`);
          console.error("[GoogleOAuth direct] Failed:", status, detail, e);
        }
      })();
      return;
    }

    if (hashMatch) {
      // ============ EMERGENT fallback flow ============
      setFlowLabel("emergent");
      const sessionId = hashMatch[1];
      (async () => {
        try {
          const { data } = await axios.post(
            `${API}/auth/google/session`,
            {},
            { headers: { "X-Session-ID": sessionId }, withCredentials: true }
          );
          window.history.replaceState(null, "", window.location.pathname);
          const me = await refreshUser();
          if (!me) {
            setError("Autentificarea Google a reușit dar cookie-ul a fost blocat. Activează cookies pentru propmanage.ro și încearcă din nou.");
            return;
          }
          navigate(`/${data.role || "client"}`, { replace: true });
        } catch (e) {
          const status = e?.response?.status;
          const hasDetail = !!e?.response?.data?.detail;
          let detail = e?.response?.data?.detail || e.message || "Autentificare eșuată";
          const isGatewayErr = status && !hasDetail && (status === 502 || status === 504 || (status >= 520 && status <= 524));
          if (isGatewayErr) {
            detail = `Serverul Emergent OAuth (upstream) e momentan inaccesibil sau prea lent (HTTP ${status} — ${status === 502 ? "Bad Gateway" : status === 504 ? "Gateway Timeout" : "Cloudflare origin empty"}). ` +
              "Încearcă din nou peste 30s-1min, sau folosește email + parolă mai jos.";
            axios.post(`${API}/auth/health-beacon`, {
              status_code: status,
              where: "auth_callback",
              note: (e.message || "").slice(0, 200),
            }).catch(() => {});
          } else if (status === 503 && hasDetail) {
            detail = e.response.data.detail;
          }
          setError(`[${status || "network"}] ${detail}`);
          console.error("[GoogleOAuth emergent] Failed:", status, detail, e);
        }
      })();
      return;
    }

    // Neither `code` nor `session_id` present → nothing to do
    navigate("/login");
  }, [navigate, refreshUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b] text-stone-100 px-6">
      <div className="max-w-md w-full text-center space-y-4">
        {!error ? (
          <>
            <div className="inline-block w-12 h-12 border-2 border-[#d4ff3a] border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-sm text-stone-400">
              Se finalizează autentificarea{flowLabel ? ` (${flowLabel})` : ""}...
            </p>
          </>
        ) : (
          <>
            <div className="text-5xl">🔐</div>
            <h1 className="text-2xl font-serif">Autentificare Google eșuată</h1>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-left text-xs text-red-300 font-mono break-words" data-testid="oauth-error-detail">
              {error}
            </div>
            <div className="text-xs text-stone-400 space-y-2 text-left bg-white/[0.03] rounded-lg p-3">
              <p className="font-semibold text-stone-300">Ce poți încerca:</p>
              <ol className="list-decimal pl-5 space-y-1">
                <li>Verifică că <code>{window.location.origin}/auth/callback</code> este în lista Authorized Redirect URIs din Google Cloud Console</li>
                <li>Șterge cookies pentru <strong>{window.location.hostname}</strong> și încearcă din nou</li>
                <li>Folosește email + parolă în loc de Google (mai sigur cross-site)</li>
              </ol>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate("/login")}
                className="flex-1 px-4 py-2 rounded-lg bg-[#d4ff3a] text-stone-950 text-sm font-semibold"
                data-testid="oauth-error-back"
              >
                Înapoi la login
              </button>
              <button
                onClick={() => window.location.href = "mailto:contact@propmanage.ro?subject=Problema Google OAuth pe propmanage.ro&body=" + encodeURIComponent("Eroare: " + error)}
                className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-stone-300 text-xs"
              >
                Raportează
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
