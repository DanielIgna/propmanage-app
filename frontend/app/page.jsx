import { LandingClient } from "./landing-client";
import { metadataForPath } from "./seo";

// Rendered per request: CMS edits show up immediately (no incremental cache on Workers yet).
export const dynamic = "force-dynamic";

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8001").replace(/\/$/, "");

export async function generateMetadata() {
  return metadataForPath([]);
}

// CMS texts are fetched on the server so the landing HTML already contains the final copy.
async function getCms() {
  try {
    const r = await fetch(`${BACKEND_URL}/api/cms/public`, {
      signal: AbortSignal.timeout(2500),
      cache: "no-store",
    });
    return r.ok ? await r.json() : {};
  } catch {
    return {};
  }
}

export default async function Home() {
  return <LandingClient cms={await getCms()} />;
}
