import { useEffect } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

// Two caches: legacy app_settings (backward compat) + new page registry per key.
let _settingsCache = null;
let _settingsPromise = null;
const _pageCache = new Map();          // key -> resolved bundle
const _pagePromise = new Map();        // key -> in-flight promise

function fetchSettings() {
  if (_settingsCache) return Promise.resolve(_settingsCache);
  if (_settingsPromise) return _settingsPromise;
  _settingsPromise = axios
    .get(`${API}/api/app-settings/public`)
    .then((r) => { _settingsCache = r.data; return _settingsCache; })
    .catch(() => null);
  return _settingsPromise;
}

function fetchPageConfig(pageKey) {
  if (!pageKey) return Promise.resolve(null);
  if (_pageCache.has(pageKey)) return Promise.resolve(_pageCache.get(pageKey));
  if (_pagePromise.has(pageKey)) return _pagePromise.get(pageKey);
  const p = axios
    .get(`${API}/api/public/pages/${pageKey}`)
    .then((r) => { _pageCache.set(pageKey, r.data); return r.data; })
    .catch(() => { _pageCache.set(pageKey, null); return null; });
  _pagePromise.set(pageKey, p);
  return p;
}

function applyMeta(title, description, ogImage, ogTitle, ogDescription) {
  if (title) document.title = title;
  const setNamed = (name, content) => {
    if (!content) return;
    let m = document.querySelector(`meta[name="${name}"]`);
    if (!m) { m = document.createElement("meta"); m.name = name; document.head.appendChild(m); }
    m.content = content;
  };
  const setOG = (prop, content) => {
    if (!content) return;
    let m = document.querySelector(`meta[property="${prop}"]`);
    if (!m) { m = document.createElement("meta"); m.setAttribute("property", prop); document.head.appendChild(m); }
    m.content = content;
  };
  setNamed("description", description);
  setOG("og:title", ogTitle || title);
  setOG("og:description", ogDescription || description);
  setOG("og:image", ogImage);
  // Twitter mirror (best-effort).
  setNamed("twitter:title", ogTitle || title);
  setNamed("twitter:description", ogDescription || description);
}

/**
 * Apply dynamic SEO meta tags. Source-of-truth cascade:
 *   1. db.pages (canonical, via /api/public/pages/{pageKey})
 *   2. db.app_settings.seo.{pageKey}_* (backward compat)
 *   3. fallback prop
 *   4. current document.title
 *
 * `pageKey` is the shared key used across Page Registry + legacy app_settings.
 */
export function useDynamicSEO(pageKey, fallback = {}) {
  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchPageConfig(pageKey), fetchSettings()]).then(([pg, s]) => {
      if (cancelled) return;
      const seo = s?.seo || {};
      const title =
        (pg?.seo_title) ||
        seo[`${pageKey}_title`] ||
        fallback.title ||
        document.title;
      const description =
        (pg?.seo_description) ||
        seo[`${pageKey}_description`] ||
        fallback.description ||
        "";
      const ogTitle = (pg?.og_title) || title;
      const ogDescription = (pg?.og_description) || description;
      const ogImage = seo.og_image || fallback.ogImage || "";
      applyMeta(title, description, ogImage, ogTitle, ogDescription);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [pageKey, fallback.title, fallback.description, fallback.ogImage]);
}

/** Clear all SEO-related caches — call after admin saves SEO to force fresh fetch. */
export function invalidateSEOCache() {
  _settingsCache = null;
  _settingsPromise = null;
  _pageCache.clear();
  _pagePromise.clear();
}
