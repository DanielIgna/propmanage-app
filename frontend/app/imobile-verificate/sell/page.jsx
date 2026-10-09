import { ClientOnly } from "../../[...slug]/client";
import { metadataForPath } from "../../seo";

// Seller form: stays in the client-side SPA (static segment wins over [id]).
export const dynamic = "force-dynamic"; // metadata from the Page Registry stays editable
export async function generateMetadata() {
  return metadataForPath(["imobile-verificate", "sell"]);
}

export default function SellPage() {
  return <ClientOnly />;
}
