import { redirect } from "next/navigation";
import { DesignInteriorDetailClient } from "../client";
import { metadataForPath } from "../../seo";
import { getCms } from "../../server-data";
import { DI_PAGES, DI_LOCAL_CITIES } from "@/data/designInterior";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { slug } = await params;
  return metadataForPath(["design-interior", slug]);
}

export default async function DesignInteriorDetail({ params }) {
  const { slug } = await params;
  if (!DI_PAGES[slug] && !DI_LOCAL_CITIES[slug]) redirect("/design-interior");
  return <DesignInteriorDetailClient path={`/design-interior/${slug}`} cms={await getCms()} />;
}
