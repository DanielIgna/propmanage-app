import React, { lazy } from "react";
import { Route } from "react-router-dom";
import { RADACINI_ENABLED } from "./config";
import { RadaciniLayout } from "./RadaciniLayout";

const Panou = lazy(() => import("./pages/Panou"));
const Setari = lazy(() => import("./pages/Setari"));

export function radaciniRoutes() {
  if (!RADACINI_ENABLED) return null;
  return (
    <Route path="/radacini" element={<RadaciniLayout />}>
      <Route index element={<Panou />} />
      <Route path="setari" element={<Setari />} />
    </Route>
  );
}
