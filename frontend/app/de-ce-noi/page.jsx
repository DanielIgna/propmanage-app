import { PublicPageClient } from "../public-pages";
import { metadataForPath } from "../seo";
import { getCms } from "../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath(["de-ce-noi"]);
}

export default async function Page() {
  return <PublicPageClient path="/de-ce-noi" cms={await getCms()} />;
}
