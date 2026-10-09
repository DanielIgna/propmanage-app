"use client";

import { SsrShell } from "./ssr-shell";
import { LandingPage } from "@/landing/LandingPage";

export function LandingClient({ cms }) {
  return (
    <SsrShell path="/" cms={cms}>
      <LandingPage />
    </SsrShell>
  );
}
