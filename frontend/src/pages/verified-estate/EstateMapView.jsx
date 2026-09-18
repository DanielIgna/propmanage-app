import React from "react";
import { PmMarkersMap } from "../../components/PmMap";

const formatPrice = (ron) => {
  if (!ron) return "—";
  return new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(ron) + " RON";
};

// Harta „Imobile Verificate" — folosește providerul unificat (Google când e
// activat + cheie, altfel fallback OpenStreetMap fără cheie). Afișează doar
// listările publicate (deja publice prin decizia proprietarului de a vinde).
export const EstateMapView = ({ items }) => {
  const points = (items || [])
    .filter((it) => it.lat && it.lng)
    .map((it) => ({
      id: it.id,
      lat: it.lat,
      lng: it.lng,
      title: it.title,
      subtitle: `${it.city || ""}${it.address ? ` · ${it.address}` : ""}`,
      price: formatPrice(it.price_ron),
      href: `/imobile-verificate/${it.id}`,
      hrefLabel: "Vezi detalii",
      derived: Boolean(it.location?.derived),
      provenanceLabel: it.location?.provenance_label || (it.location?.derived ? "Locație derivată · neverificată" : null),
    }));

  const hasDerived = points.some((p) => p.derived);

  return (
    <div data-testid="estate-map-view">
      <PmMarkersMap points={points} height="70vh" emptyLabel="Niciun imobil cu coordonate geografice." />
      {hasDerived && (
        <p className="text-[11px] text-stone-500 mt-2 px-1" data-testid="estate-map-derived-note">
          Unele locații sunt derivate din clădire (HartaBlocuri / geocoding) și neverificate.
        </p>
      )}
    </div>
  );
};

export default EstateMapView;
