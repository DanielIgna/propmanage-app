import { EstateDetailClient } from "../client";
import { metadataForPath } from "../../seo";
import { notFound } from "next/navigation";
import { fetchBackend, getCms } from "../../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { id } = await params;
  return metadataForPath(["imobile-verificate", id]);
}

export default async function EstateDetailPage({ params }) {
  const { id } = await params;
  const [cms, res] = await Promise.all([
    getCms(),
    fetchBackend(`/api/verified-estate/listings/${encodeURIComponent(id)}`),
  ]);
  if (res.status === 404) notFound(); // backend unreachable (status 0): let the client retry instead
  return <EstateDetailClient path={`/imobile-verificate/${id}`} cms={cms} listing={res.data} />;
}
