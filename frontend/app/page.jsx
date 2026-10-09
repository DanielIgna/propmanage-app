import { LandingClient } from "./landing-client";
import { metadataForPath } from "./seo";
import { getCms } from "./server-data";

// Rendered per request: CMS edits show up immediately (no incremental cache on Workers yet).
export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath([]);
}

// CMS texts are fetched on the server so the landing HTML already contains the final copy.
export default async function Home() {
  return <LandingClient cms={await getCms()} />;
}
