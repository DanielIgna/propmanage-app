import { ClientOnly } from "./client";

// Catch-all: every path not claimed by a dedicated App Router route renders the SPA.
export default function Page() {
  return <ClientOnly />;
}
