import { PublicPageClient } from "../public-pages";
import { metadataForPath } from "../seo";
import { getCms } from "../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath(["cookies"]);
}

export default async function Page() {
  return <PublicPageClient path="/cookies" cms={await getCms()} />;
}
