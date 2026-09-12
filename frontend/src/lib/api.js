// lib/api.js — clientul HTTP unic al platformei (TD-05, Blueprint Art. 2/5).
// Orice pagină nouă folosește DOAR acest client. Migrarea paginilor vechi: progresiv.
import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  withCredentials: true,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401 && !window.location.pathname.startsWith("/login")) {
      const p = window.location.pathname;
      const isProtected = ["/client", "/specialist", "/admin", "/operator", "/partner"].some((x) => p.startsWith(x));
      if (isProtected) window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const apiErr = (e, fallback = "A apărut o eroare") =>
  e?.response?.data?.detail || e?.message || fallback;
