import React, { lazy, Suspense } from "react";
import { Route } from "react-router-dom";
import { RADACINI_ENABLED } from "./config";
import { RadaciniLayout } from "./RadaciniLayout";

const Panou = lazy(() => import("./pages/Panou"));
const Profil = lazy(() => import("./pages/Profil"));
const Terenuri = lazy(() => import("./pages/Terenuri"));
const TerenDetaliu = lazy(() => import("./pages/TerenDetaliu"));
const TerenurileMele = lazy(() => import("./pages/TerenurileMele"));
const TerenForm = lazy(() => import("./pages/TerenForm"));
const Operator = lazy(() => import("./pages/Operator"));
const Personal = lazy(() => import("./pages/Personal"));
const Setari = lazy(() => import("./pages/Setari"));
const Cereri = lazy(() => import("./pages/Cereri"));
const CerereDetaliu = lazy(() => import("./pages/CerereDetaliu"));
const Acorduri = lazy(() => import("./pages/Acorduri"));
const AcordDetaliu = lazy(() => import("./pages/AcordDetaliu"));
const Proiecte = lazy(() => import("./pages/Proiecte"));
const ProiectDetaliu = lazy(() => import("./pages/ProiectDetaliu"));
// Pagina Progres există doar în dev; în build-ul de producție importul dispare (NODE_ENV e înlocuit la build).
const Progres = process.env.NODE_ENV !== "production" ? lazy(() => import("./pages/Progres")) : null;
const Piata = lazy(() => import("./pages/Piata"));
const AnuntDetaliu = lazy(() => import("./pages/AnuntDetaliu"));
const AnuntForm = lazy(() => import("./pages/AnuntForm"));
const Rezervari = lazy(() => import("./pages/Rezervari"));
const Login = lazy(() => import("./pages/Login"));

export function radaciniRoutes() {
  if (!RADACINI_ENABLED) return null;
  return (
    <>
    {/* Intrarea Rădăcini e în afara layout-ului (layout-ul cere cont). */}
    <Route path="/radacini/login" element={<Suspense fallback={null}><Login /></Suspense>} />
    <Route path="/radacini" element={<RadaciniLayout />}>
      <Route index element={<Panou />} />
      <Route path="profil" element={<Profil />} />
      <Route path="terenuri" element={<Terenuri />} />
      <Route path="terenuri/:id" element={<TerenDetaliu />} />
      <Route path="terenurile-mele" element={<TerenurileMele />} />
      <Route path="terenurile-mele/nou" element={<TerenForm />} />
      <Route path="terenurile-mele/:id/editare" element={<TerenForm />} />
      <Route path="cereri" element={<Cereri />} />
      <Route path="cereri/:id" element={<CerereDetaliu />} />
      <Route path="acorduri" element={<Acorduri />} />
      <Route path="acorduri/:id" element={<AcordDetaliu />} />
      <Route path="operator" element={<Operator />} />
      <Route path="personal" element={<Personal />} />
      <Route path="setari" element={<Setari />} />
      <Route path="proiecte" element={<Proiecte />} />
      <Route path="proiecte/:id" element={<ProiectDetaliu />} />
      <Route path="piata" element={<Piata />} />
      <Route path="piata/nou" element={<AnuntForm />} />
      <Route path="piata/:id" element={<AnuntDetaliu />} />
      <Route path="piata/:id/editare" element={<AnuntForm />} />
      <Route path="rezervari" element={<Rezervari />} />
      {Progres && <Route path="progres" element={<Progres />} />}
    </Route>
    </>
  );
}
