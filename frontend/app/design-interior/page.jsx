import { DesignInteriorHubClient } from "./client";
import { metadataForPath } from "../seo";
import { getBackendJson, getCms } from "../server-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return metadataForPath(["design-interior"]);
}

export default async function DesignInteriorHub() {
  const [cms, content] = await Promise.all([getCms(), getBackendJson("/api/interior-design/content")]);
  return <DesignInteriorHubClient cms={cms} content={content} />;
}
