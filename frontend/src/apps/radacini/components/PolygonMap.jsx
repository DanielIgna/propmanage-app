import React, { useMemo } from "react";
import { MapContainer, TileLayer, Polygon } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Hartă read-only cu poligonul terenului. geometry = GeoJSON Polygon ([lng, lat]).
export default function PolygonMap({ geometry, height = "280px" }) {
  const ring = useMemo(() => {
    const r = geometry?.type === "Polygon" ? geometry.coordinates?.[0] : null;
    if (!Array.isArray(r)) return [];
    return r.filter((c) => Array.isArray(c) && Number.isFinite(c[0]) && Number.isFinite(c[1])).map(([lng, lat]) => [lat, lng]);
  }, [geometry]);
  const bounds = useMemo(() => (ring.length ? L.latLngBounds(ring) : null), [ring]);

  if (typeof window === "undefined" || ring.length < 3) return null;

  return (
    <div className="relative isolate rounded-3xl overflow-hidden border border-white/10" style={{ height }} data-testid="radacini-polygon-map">
      <MapContainer key={ring.map((c) => c.join(",")).join("|")} bounds={bounds.pad(0.2)} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
        <Polygon positions={ring} pathOptions={{ color: "#d4ff3a", weight: 3, fillColor: "#d4ff3a", fillOpacity: 0.25 }} />
      </MapContainer>
    </div>
  );
}
