// Auth Context for PropManage
import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";
import { supabase } from "./lib/supabase";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;
axios.defaults.withCredentials = true;
// Anti-CSRF (SEC-002): header custom pe TOATE apelurile app-ului — formularele
// HTML cross-site nu pot seta headere custom, deci mutațiile /api/admin fără
// acest header sunt respinse de backend.
axios.defaults.headers.common["X-PM-Client"] = "propmanage-app";

// Supabase Auth: trimite access token-ul curent (auto-refresh de supabase-js) ca Bearer.
axios.interceptors.request.use(async (config) => {
  if (!supabase || config.headers?.Authorization) return config;
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const applySupabaseSession = async (s) => {
  if (supabase && s?.access_token && s?.refresh_token) {
    await supabase.auth.setSession({ access_token: s.access_token, refresh_token: s.refresh_token });
  }
};

// Task 5: global 402 interceptor. Când server-ul răspunde cu 402 entitlement_required,
// emitem un CustomEvent pe window ca UI-ul să afișeze un nudge friendly în loc de eroare
// tehnică. NU înghițim eroarea — componenta care a făcut cererea poate face al său flow.
axios.interceptors.response.use(
  (r) => r,
  (error) => {
    try {
      if (error?.response?.status === 402) {
        const detail = error.response.data?.detail || {};
        const feature = detail.feature || detail.required_feature;
        if (feature && typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("pm:entitlement_denied", {
            detail: { feature, message: detail.message, current_tier: detail.current_tier },
          }));
        }
      }
    } catch { /* silent */ }
    return Promise.reject(error);
  }
);

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); // null = checking, false = not auth, object = auth
  
  // Token reîmprospătat → actualizează și cookie-ul httpOnly (download-uri, <img>, link-uri directe).
  useEffect(() => {
    if (!supabase) return;
    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "TOKEN_REFRESHED" && session?.access_token) {
        axios.post(`${API}/auth/supabase/session`, null, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        }).catch(() => {});
      }
    });
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    // Skip auth probe on intentionally-public routes (avoids noisy 401s).
    const path = window.location.pathname;
    if (path.startsWith("/report-respond/")) {
      setUser(false);
      return;
    }
    // No session hint (never logged in on this browser) → skip /me probe entirely.
    if (!localStorage.getItem("pm_session_hint")) {
      setUser(false);
      return;
    }
    axios.get(`${API}/auth/me`)
      .then(r => {
        setUser(r.data);
        import("@/lib/analytics").then(({ identify }) => identify(r.data?.id, r.data?.role)).catch(() => {});
      })
      .catch(() => { localStorage.removeItem("pm_session_hint"); setUser(false); });
  }, []);
  
  const login = async (email, password, totp_code) => {
    const payload = { email, password };
    if (totp_code) payload.totp_code = totp_code;
    const { data } = await axios.post(`${API}/auth/login`, payload);
    await applySupabaseSession(data.supabase_session);
    delete data.supabase_session;
    localStorage.setItem("pm_session_hint", "1");
    setUser(data);
    try { const { identify } = await import("@/lib/analytics"); identify(data?.id, data?.role); } catch { /* noop */ }
    return data;
  };
  
  const register = async (payload) => {
    try { const { trackFunnel } = await import("@/lib/analytics"); trackFunnel("signup_started"); } catch { /* noop */ }
    const { data } = await axios.post(`${API}/auth/register`, payload);
    await applySupabaseSession(data.supabase_session);
    delete data.supabase_session;
    localStorage.setItem("pm_session_hint", "1");
    try {
      const { trackFunnel, identify } = await import("@/lib/analytics");
      trackFunnel("account_created");
      identify(data?.id, data?.role);
    } catch { /* noop */ }
    setUser(data);
    return data;
  };
  
  const logout = async () => {
    await axios.post(`${API}/auth/logout`);
    if (supabase) await supabase.auth.signOut({ scope: "local" }).catch(() => {});
    localStorage.removeItem("pm_session_hint");
    try { const { identify } = await import("@/lib/analytics"); identify(null); } catch { /* noop */ }
    setUser(false);
  };
  
  const refreshUser = async () => {
    const { data } = await axios.get(`${API}/auth/me`);
    localStorage.setItem("pm_session_hint", "1");
    setUser(data);
    return data;
  };
  
  return (
    <AuthContext.Provider value={{ user, login, register, logout, refreshUser, API }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
};

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return err?.message || "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(e => e.msg || JSON.stringify(e)).join(" ");
  if (detail && typeof detail === "object" && detail.message) return detail.message;
  return String(detail);
}
