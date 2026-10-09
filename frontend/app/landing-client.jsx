"use client";

import { useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { Router } from "react-router-dom";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { DesignTokensProvider } from "@/contexts/DesignTokensProvider";
import { I18nProvider } from "@/i18n";
import { AuthProvider } from "@/auth";
import { LandingPage } from "@/landing/LandingPage";
import { trackPageView } from "@/lib/analytics";
import { ServerRenderedContext } from "@/lib/serverRendered";
import "@/lib/backendUrlFallback";

// Browser-only widgets the SPA mounts around every route.
const CookieBanner = dynamic(() => import("@/components/CookieBanner").then((m) => m.CookieBanner), { ssr: false });
const AssistantDock = dynamic(() => import("@/components/AssistantDock").then((m) => m.AssistantDock), { ssr: false });
const Toaster = dynamic(() => import("sonner").then((m) => m.Toaster), { ssr: false });

const LOCATION = { pathname: "/", search: "", hash: "", state: null, key: "default" };

// React Router context for the landing components: <Link>/navigate() hand off to Next.js, which
// renders the target path through the SPA catch-all route.
function NextNavigationRouter({ children }) {
  const router = useRouter();
  const navigator = useMemo(() => {
    const href = (to) => (typeof to === "string" ? to : `${to.pathname || "/"}${to.search || ""}${to.hash || ""}`);
    return {
      createHref: href,
      encodeLocation: (to) => (typeof to === "string" ? new URL(to, "http://x") : to),
      push: (to) => router.push(href(to)),
      replace: (to) => router.replace(href(to)),
      go: (n) => window.history.go(n),
    };
  }, [router]);
  return (
    <Router location={LOCATION} navigator={navigator}>
      {children}
    </Router>
  );
}

export function LandingClient({ cms }) {
  useEffect(() => { trackPageView("/"); }, []);
  return (
    <ServerRenderedContext.Provider value={true}>
    <div className="App">
      <ThemeProvider>
        <DesignTokensProvider>
          <I18nProvider initialCms={cms}>
            <AuthProvider>
              <NextNavigationRouter>
                <LandingPage />
                <AssistantDock />
                <Toaster position="top-right" richColors closeButton />
                <CookieBanner />
              </NextNavigationRouter>
            </AuthProvider>
          </I18nProvider>
        </DesignTokensProvider>
      </ThemeProvider>
    </div>
    </ServerRenderedContext.Provider>
  );
}
