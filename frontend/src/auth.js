// Auth Context for PropManage
import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
axios.defaults.withCredentials = true;
// Anti-CSRF (SEC-002): header custom pe TOATE apelurile app-ului — formularele
// HTML cross-site nu pot seta headere custom, deci mutațiile /api/admin fără
// acest header sunt respinse de backend.
axios.defaults.headers.common["X-PM-Client"] = "propmanage-app";

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
  
  useEffect(() => {
    // CRITICAL: If returning from Emergent OAuth callback, skip the /me check.
    // AuthCallback will exchange the session_id and establish the session first.
    if (window.location.hash?.includes("session_id=")) {
      return;
    }
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
    localStorage.setItem("pm_session_hint", "1");
    setUser(data);
    try { const { identify } = await import("@/lib/analytics"); identify(data?.id, data?.role); } catch { /* noop */ }
    return data;
  };
  
  const register = async (payload) => {
    try { const { trackFunnel } = await import("@/lib/analytics"); trackFunnel("signup_started"); } catch { /* noop */ }
    const { data } = await axios.post(`${API}/auth/register`, payload);
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
  return String(detail);
}
