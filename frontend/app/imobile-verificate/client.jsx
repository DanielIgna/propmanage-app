"use client";

import { Routes, Route } from "react-router-dom";
import { SsrShell } from "../ssr-shell";
import { EstateBrowse } from "@/views/verified-estate/EstateBrowse";
import { EstateDetail } from "@/views/verified-estate/EstateDetail";

export function EstateBrowseClient({ cms, items }) {
  return (
    <SsrShell path="/imobile-verificate" cms={cms}>
      <EstateBrowse initialItems={items} />
    </SsrShell>
  );
}

export function EstateDetailClient({ path, cms, listing }) {
  return (
    <SsrShell path={path} cms={cms}>
      <Routes>
        <Route path="/imobile-verificate/:id" element={<EstateDetail initialListing={listing} />} />
      </Routes>
    </SsrShell>
  );
}
