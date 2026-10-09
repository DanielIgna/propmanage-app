"use client";

import { Routes, Route } from "react-router-dom";
import { SsrShell } from "../ssr-shell";
import InteriorDesignLanding from "@/views/InteriorDesignLanding";
import { DesignInteriorPage } from "@/views/DesignInteriorPage";

export function DesignInteriorHubClient({ cms, content }) {
  return (
    <SsrShell path="/design-interior" cms={cms}>
      <InteriorDesignLanding initialContent={content} />
    </SsrShell>
  );
}

export function DesignInteriorDetailClient({ path, cms }) {
  return (
    <SsrShell path={path} cms={cms}>
      <Routes>
        <Route path="/design-interior/stil/:slug" element={<DesignInteriorPage kind="style" />} />
        <Route path="/design-interior/:slug" element={<DesignInteriorPage kind="page" />} />
      </Routes>
    </SsrShell>
  );
}
