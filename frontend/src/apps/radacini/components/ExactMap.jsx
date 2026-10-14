import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Hartă read-only cu punctul exact al terenului (vizibil doar părților unui acord semnat).
export default function ExactMap({ lat, lng, height = "280px" }) {
  const icon = useMemo(
    () =>
      L.divIcon({
        className: "pm-marker",
        html: `<div style="background:#d4ff3a;width:22px;height:22px;border-radius:50%;border:3px solid #0a0a0b;box-shadow:0 0 0 2px #d4ff3a66;"></div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      }),
    []
  );

  if (typeof window === "undefined" || !Number.isFinite(lat) || !Number.isFinite(lng)) return null;

  return (
    <div className="relative isolate rounded-3xl overflow-hidden border border-white/10" style={{ height }} data-testid="radacini-exact-map">
      <MapContainer key={`${lat}:${lng}`} center={[lat, lng]} zoom={16} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
        <Marker position={[lat, lng]} icon={icon} />
      </MapContainer>
    </div>
  );
}
