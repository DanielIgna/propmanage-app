// Utilitare conturi de test: cache local al personelor (user_id) pentru comutarea din bara de impersonare.
import { api } from "../../lib/api";

const CACHE_KEY = "radacini_test_personas";

export const cachePersonas = (items) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(items.filter((p) => p.user_id)));
  } catch {
    /* ignorat */
  }
};

export const loadCachedPersonas = () => {
  try {
    const v = JSON.parse(localStorage.getItem(CACHE_KEY) || "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
};

// Necesită sesiunea de admin (nu una de impersonare). Redirecționează spre /radacini.
export const impersonatePersona = async (persona) => {
  await api.post("/admin/impersonate", {
    user_id: persona.user_id,
    reason: `Test Rădăcini: rolul ${persona.label}`,
  });
  window.location.href = "/radacini";
};
