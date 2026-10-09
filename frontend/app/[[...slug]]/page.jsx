import { ClientOnly } from "./client";
import { metadataForPath } from "../seo";

// Per-path metadata rendered on the server (title, description, OG, canonical, robots).
export async function generateMetadata({ params }) {
  const { slug } = await params;
  return metadataForPath(slug);
}

// Catch-all: every path not claimed by a dedicated App Router route renders the SPA.
export default function Page() {
  return <ClientOnly />;
}
