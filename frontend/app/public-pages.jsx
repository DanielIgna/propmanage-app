"use client";

import { SsrShell } from "./ssr-shell";
import WhyUsPage from "@/views/WhyUsPage";
import TrustCenterPage from "@/views/TrustCenterPage";
import { PrivacyPage, TermsPage, CookiePolicyPage } from "@/views/LegalPages";

// Simple public SPA pages rendered on the server (no route params, no server data).
const PAGES = {
  "/de-ce-noi": WhyUsPage,
  "/trust": TrustCenterPage,
  "/privacy": PrivacyPage,
  "/terms": TermsPage,
  "/cookies": CookiePolicyPage,
};

export function PublicPageClient({ path, cms, initialData = null }) {
  const Page = PAGES[path];
  return (
    <SsrShell path={path} cms={cms}>
      <Page initialData={initialData} />
    </SsrShell>
  );
}
