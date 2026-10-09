// Server-side SEO for the catch-all SPA route: per-path <title>, description, Open Graph,
// canonical and robots, so crawlers get correct metadata before any JavaScript runs.
// Source of truth for public pages = the backend Page Registry (/api/public/pages/{key}),
// the same data admins edit; dynamic pages fetch their entity.

import { DI_PAGES, DI_STYLES, DI_LOCAL_CITIES } from "@/data/designInterior";
import { getLocalContent } from "@/data/designInteriorLocal";

const SITE_URL = "https://propmanage.ro";
const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8001").replace(/\/$/, "");

// Page Registry keys by route (db.pages.route).
const REGISTRY_ROUTES = {
  "/": "home",
  "/pricing": "pricing",
  "/de-ce-noi": "whyus",
  "/imobile-verificate": "estate",
  "/imobile-verificate/sell": "sell",
  "/marketplace": "marketplace",
  "/design-interior": "interior_design",
  "/design-exterior": "design_exterior",
  "/arhitectura": "arhitectura",
  "/digital-twin": "digital_twin",
  "/community": "community",
  "/demo": "demo",
  "/login": "login",
  "/register": "register",
  "/devino-specialist": "devino_specialist",
  "/devino-francizat": "devino_francizat",
  "/privacy": "privacy",
  "/terms": "terms",
  "/cookies": "cookies",
  "/trust": "trust",
};

// Authenticated / transactional areas: never indexed.
const PRIVATE_PREFIXES = [
  "/admin", "/client", "/specialist", "/operator", "/dashboard", "/settings", "/kyc", "/auth",
  "/verify-email", "/report-respond", "/property/", "/franchise_admin", "/franciza", "/components-v2",
  "/status", "/privacy/notices",
  "/pricing", // plans require login: anonymous visitors are sent to /login
];

async function getJson(path) {
  try {
    const r = await fetch(`${BACKEND_URL}${path}`, {
      headers: { "X-PM-Client": "propmanage-app" },
      signal: AbortSignal.timeout(2500),
      next: { revalidate: 300 },
    });
    return r.ok ? await r.json() : null;
  } catch {
    return null; // backend slow/down: fall back to the layout defaults
  }
}

function build({ path, title, description, ogTitle, ogDescription, ogImage, noindex }) {
  const meta = { alternates: { canonical: path } };
  if (title) meta.title = title;
  if (description) meta.description = description;
  if (noindex) meta.robots = { index: false, follow: false };
  const og = { url: `${SITE_URL}${path}` };
  if (ogTitle || title) og.title = ogTitle || title;
  if (ogDescription || description) og.description = ogDescription || description;
  if (ogImage) og.images = [{ url: ogImage }];
  meta.openGraph = og;
  meta.twitter = { title: og.title, description: og.description, ...(ogImage ? { images: [ogImage] } : {}) };
  return meta;
}

// Routes behind <ServiceGate> in the SPA (non-admins are redirected to "/" while the service is off).
const GATED_SERVICES = [{ prefix: "/marketplace", service: "specialisti" }];

async function serviceDisabled(path) {
  const gate = GATED_SERVICES.find((g) => path === g.prefix || path.startsWith(`${g.prefix}/`));
  if (!gate) return false;
  const vis = await getJson("/api/public/service-visibility");
  const svc = vis?.services?.[gate.service];
  return !!vis && !(svc && svc.active && svc.visible_site);
}

export async function metadataForPath(slug) {
  const path = "/" + (slug || []).map(decodeURIComponent).join("/");

  if (await serviceDisabled(path)) {
    return build({ path: "/", noindex: true });
  }

  if (PRIVATE_PREFIXES.some((p) => path === p || path.startsWith(p.endsWith("/") ? p : `${p}/`))) {
    return build({ path, noindex: true });
  }

  const key = REGISTRY_ROUTES[path];
  if (key) {
    const page = await getJson(`/api/public/pages/${key}`);
    if (page) {
      return build({
        path,
        title: page.seo_title || undefined,
        description: page.seo_description || undefined,
        ogTitle: page.og_title || undefined,
        ogDescription: page.og_description || undefined,
        noindex: page.status && page.status !== "active",
      });
    }
    return build({ path });
  }

  const estate = path.match(/^\/imobile-verificate\/([^/]+)$/);
  if (estate) {
    const listing = await getJson(`/api/verified-estate/listings/${encodeURIComponent(estate[1])}`);
    if (listing?.title) {
      const desc = (listing.description || "").replace(/\s+/g, " ").slice(0, 160);
      const photo = (listing.gallery || listing.photos || listing.images || [])[0];
      return build({
        path,
        title: `${listing.title} · Imobil Verificat | PropManage`,
        description: desc || undefined,
        ogImage: typeof photo === "string" ? photo : photo?.url,
      });
    }
  }

  // Design interior: content pages, styles and local (city) pages — same rules as DesignInteriorPage.
  const style = path.match(/^\/design-interior\/stil\/([^/]+)$/);
  if (style && DI_STYLES[style[1]]) {
    const st = DI_STYLES[style[1]];
    return build({ path, title: st.title, description: st.description });
  }
  const di = path.match(/^\/design-interior\/([^/]+)$/);
  if (di && DI_PAGES[di[1]]) {
    const pg = DI_PAGES[di[1]];
    return build({ path, title: pg.title, description: pg.description });
  }
  if (di && DI_LOCAL_CITIES[di[1]]) {
    const cityName = DI_LOCAL_CITIES[di[1]];
    const content = getLocalContent(di[1]);
    const gate = await getJson(`/api/public/seo/gate?path=${encodeURIComponent(path)}`);
    const gated = gate ? gate.index === false : !content;
    const meta = build({
      path: gated && gate?.canonical ? new URL(gate.canonical, SITE_URL).pathname : path,
      title: content
        ? `Design interior ${cityName}: proiect, renovare și implementare | PropManage`
        : `Design interior ${cityName}: designeri verificați | PropManage`,
      description: content
        ? content.intro.slice(0, 155)
        : `Design interior în ${cityName}: lucrează cu designeri verificați, cu portofolii și recenzii reale. Proiect + implementare la cheie, plată protejată prin escrow.`,
      noindex: gated,
    });
    return meta;
  }
  if (style || di) {
    // Unknown slug: the SPA redirects to /design-interior.
    return build({ path: "/design-interior", noindex: true });
  }

  // Other public pages set their final title client-side; the canonical must still be their own URL.
  return build({ path });
}
