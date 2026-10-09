// Shared, de-duplicated fetches for public config used by several components on the same page.
const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const _cache = new Map();

function once(key, path) {
  if (!_cache.has(key)) {
    const p = fetch(`${API}${path}`)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .then((data) => {
        if (data === null) _cache.delete(key); // allow a retry later
        return data;
      });
    _cache.set(key, p);
  }
  return _cache.get(key);
}

export const getAppSettingsPublic = () => once("app-settings", "/api/app-settings/public");
export const getTrackConfig = () => once("track-config", "/api/track/config");

/** Forget cached values (e.g. after an admin saves settings). */
export const invalidatePublicConfig = () => _cache.clear();
