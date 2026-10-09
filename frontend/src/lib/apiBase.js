// Smart API base URL detection.
// Falls back to window.location.origin if the configured URL points to a
// different host than the one the user is currently on. This protects against
// stale build-time NEXT_PUBLIC_BACKEND_URL when the custom domain isn't yet live
// (e.g. propmanage.ro DNS not propagated yet).
function resolveApiBase() {
  const configured = (process.env.NEXT_PUBLIC_BACKEND_URL || "").trim();
  if (typeof window === "undefined") return configured;

  if (!configured) return window.location.origin;

  try {
    const configuredHost = new URL(configured).host;
    const currentHost = window.location.host;

    // If we're served from a different host than the configured backend URL,
    // prefer same-origin to avoid Network Error / CORS issues during transitions
    // (e.g. custom domain not yet reachable). The backend is reachable on the
    // current origin via /api/* through Emergent's Kubernetes ingress.
    if (configuredHost !== currentHost) {
      return window.location.origin;
    }
  } catch (e) {
    return window.location.origin;
  }

  return configured;
}

export const API_BASE = resolveApiBase();
export default API_BASE;
