// Server-side fetches for SSR routes (rendered per request: always fresh).
const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8001").replace(/\/$/, "");

export async function getBackendJson(path, fallback = null) {
  try {
    const r = await fetch(`${BACKEND_URL}${path}`, {
      headers: { "X-PM-Client": "propmanage-app" },
      signal: AbortSignal.timeout(2500),
      cache: "no-store",
    });
    return r.ok ? await r.json() : fallback;
  } catch {
    return fallback;
  }
}

export const getCms = () => getBackendJson("/api/cms/public", {});
