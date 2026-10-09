import { PublicPageClient } from "../public-pages";
import { metadataForPath } from "../seo";
import { getBackendJson, getCms } from "../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath(["trust"]);
}

export default async function Page() {
  const [cms, stats] = await Promise.all([getCms(), getBackendJson("/api/public/trust-stats")]);
  return <PublicPageClient path="/trust" cms={cms} initialData={stats} />;
}
