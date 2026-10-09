import { redirect } from "next/navigation";
import { DesignInteriorDetailClient } from "../../client";
import { metadataForPath } from "../../../seo";
import { getCms } from "../../../server-data";
import { DI_STYLES } from "@/data/designInterior";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { slug } = await params;
  return metadataForPath(["design-interior", "stil", slug]);
}

export default async function DesignInteriorStyle({ params }) {
  const { slug } = await params;
  if (!DI_STYLES[slug]) redirect("/design-interior");
  return <DesignInteriorDetailClient path={`/design-interior/stil/${slug}`} cms={await getCms()} />;
}
