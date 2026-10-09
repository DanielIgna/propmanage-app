import { EstateBrowseClient } from "./client";
import { metadataForPath } from "../seo";
import { getBackendJson, getCms } from "../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath(["imobile-verificate"]);
}

export default async function EstateBrowsePage() {
  const [cms, listings] = await Promise.all([getCms(), getBackendJson("/api/verified-estate/listings")]);
  return <EstateBrowseClient cms={cms} items={listings?.items ?? null} />;
}
