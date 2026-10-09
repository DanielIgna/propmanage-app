// Server-side fetches for SSR routes (rendered per request: always fresh).
const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8001").replace(/\/$/, "");

/** { status, data } — status 0 when the backend is unreachable/slow. */
export async function fetchBackend(path) {
  try {
    const r = await fetch(`${BACKEND_URL}${path}`, {
      headers: { "X-PM-Client": "propmanage-app" },
      signal: AbortSignal.timeout(2500),
      cache: "no-store",
    });
    return { status: r.status, data: r.ok ? await r.json() : null };
  } catch {
    return { status: 0, data: null };
  }
}

export async function getBackendJson(path, fallback = null) {
  const { data } = await fetchBackend(path);
  return data ?? fallback;
}

export const getCms = () => getBackendJson("/api/cms/public", {});
