import React, { useEffect } from "react";
import { MapContainer, TileLayer, Circle, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";

const DEFAULT_CENTER = [46.7712, 23.6236]; // Cluj-Napoca
const RADIUS_M = 700; // coordonatele publice sunt rotunjite la 2 zecimale (~1 km)

function FitToPoints({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng])).pad(0.05);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  }, [map, points]);
  return null;
}

// Hartă Rădăcini cu zone aproximative (cerc), nu puncte exacte.
// points: [{id, lat, lng, title, subtitle?, href?}]
export default function ApproxMap({ points = [], height = "380px", emptyLabel = "Niciun teren de afișat." }) {
  const withCoords = points.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));
  return (
    <div className="relative rounded-3xl overflow-hidden border border-white/10" style={{ height }} data-testid="radacini-approx-map">
      <MapContainer center={DEFAULT_CENTER} zoom={10} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
        <FitToPoints points={withCoords} />
        {withCoords.map((p) => (
          <Circle key={p.id} center={[p.lat, p.lng]} radius={RADIUS_M}
            pathOptions={{ color: "#d4ff3a", weight: 2, fillColor: "#d4ff3a", fillOpacity: 0.25 }}>
            <Popup>
              <div style={{ minWidth: 160 }}>
                <div style={{ fontWeight: 600 }}>{p.title}</div>
                {p.subtitle && <div style={{ fontSize: 12, color: "#666", margin: "2px 0 6px" }}>{p.subtitle}</div>}
                {p.href && <Link to={p.href}>Vezi detalii →</Link>}
              </div>
            </Popup>
          </Circle>
        ))}
      </MapContainer>
      {!withCoords.length && (
        <div className="absolute inset-x-0 bottom-3 mx-auto w-fit rounded-full bg-black/70 px-3 py-1 text-xs text-stone-300 z-[400]">{emptyLabel}</div>
      )}
    </div>
  );
}
