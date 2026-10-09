"use client";

import dynamic from "next/dynamic";

// The existing React Router SPA, rendered client-side only (same behaviour as CRA).
// Pages move to server rendering one by one as real App Router routes.
const App = dynamic(() => import("@/spa-entry"), { ssr: false });

export function ClientOnly() {
  return <App />;
}
