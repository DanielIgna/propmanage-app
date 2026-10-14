import React, { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Polygon, Polyline, CircleMarker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const DEFAULT_CENTER = [46.7712, 23.6236]; // Cluj-Napoca

const round6 = (n) => Math.round(n * 1e6) / 1e6;

function ClickCapture({ onPick }) {
  useMapEvents({
    click(e) {
      onPick({ lat: round6(e.latlng.lat), lng: round6(e.latlng.lng) });
    },
  });
  return null;
}

// GeoJSON Polygon -> vârfuri [{lat,lng}] (fără punctul de închidere)
const toVertices = (g) => {
  const ring = g?.type === "Polygon" ? g.coordinates?.[0] : null;
  if (!Array.isArray(ring) || ring.length < 4) return [];
  return ring.slice(0, -1).map(([lng, lat]) => ({ lat, lng }));
};
const toGeometry = (v) => {
  const ring = v.map((p) => [p.lng, p.lat]);
  return { type: "Polygon", coordinates: [[...ring, ring[0]]] };
};

const btn =
  "rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-40";

// Punct: value {lat,lng} · onChange({lat,lng}). Click pe hartă = punctul terenului.
// Poligon (opțional): polygon = GeoJSON Polygon | null · onPolygonChange(geojson | null).
// Dacă onPolygonChange lipsește, componenta se comportă ca înainte (doar punct).
export default function LocationPicker({ value, onChange, height = "320px", polygon = null, onPolygonChange }) {
  const polyEnabled = typeof onPolygonChange === "function";
  const [mode, setMode] = useState("point");
  const [vertices, setVertices] = useState(() => toVertices(polygon));
  const closed = !!polygon;

  // Sincronizare când poligonul vine din exterior (încărcare teren).
  useEffect(() => {
    if (polygon) setVertices(toVertices(polygon));
  }, [polygon]);

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

  if (typeof window === "undefined") return null;

  const addVertex = (p) => {
    if (closed) return;
    setVertices((v) => (v.length >= 100 ? v : [...v, p]));
  };
  const undo = () => {
    if (closed) onPolygonChange(null);
    setVertices((v) => v.slice(0, -1));
  };
  const clear = () => {
    setVertices([]);
    onPolygonChange(null);
  };
  const close = () => {
    if (vertices.length >= 3) onPolygonChange(toGeometry(vertices));
  };

  const center = value ? [value.lat, value.lng] : vertices.length ? [vertices[0].lat, vertices[0].lng] : DEFAULT_CENTER;
  const pts = vertices.map((v) => [v.lat, v.lng]);
  const polyMode = polyEnabled && mode === "polygon";

  return (
    <div className="relative isolate space-y-2" data-testid="radacini-location-picker">
      {polyEnabled && (
        <div className="flex flex-wrap items-center gap-2" data-testid="radacini-picker-controls">
          <button type="button" className={`${btn} ${mode === "point" ? "bg-slate-100 dark:bg-white/10" : ""}`} onClick={() => setMode("point")} data-testid="radacini-picker-mod-punct">
            Punct
          </button>
          <button type="button" className={`${btn} ${mode === "polygon" ? "bg-slate-100 dark:bg-white/10" : ""}`} onClick={() => setMode("polygon")} data-testid="radacini-picker-mod-poligon">
            Poligon (opțional)
          </button>
          {mode === "polygon" && (
            <>
              <button type="button" className={btn} onClick={undo} disabled={!vertices.length} data-testid="radacini-picker-anuleaza">
                Anulează ultimul vârf
              </button>
              <button type="button" className={btn} onClick={clear} disabled={!vertices.length && !closed} data-testid="radacini-picker-sterge">
                Șterge poligonul
              </button>
              <button type="button" className={btn} onClick={close} disabled={closed || vertices.length < 3} data-testid="radacini-picker-inchide">
                Închide poligonul
              </button>
            </>
          )}
        </div>
      )}
      <MapContainer center={center} zoom={value || vertices.length ? 15 : 11} scrollWheelZoom={false} style={{ height, width: "100%", borderRadius: "1rem" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
        <ClickCapture onPick={polyMode ? addVertex : onChange} />
        {value && <Marker position={[value.lat, value.lng]} icon={icon} />}
        {polyEnabled && closed && pts.length >= 3 && (
          <Polygon positions={pts} pathOptions={{ color: "#d4ff3a", weight: 3, fillColor: "#d4ff3a", fillOpacity: 0.25 }} />
        )}
        {polyEnabled && !closed && pts.length > 1 && <Polyline positions={pts} pathOptions={{ color: "#d4ff3a", weight: 3, dashArray: "6 6" }} />}
        {polyEnabled && !closed && pts.map((p, i) => <CircleMarker key={i} center={p} radius={5} pathOptions={{ color: "#0a0a0b", fillColor: "#d4ff3a", fillOpacity: 1, weight: 2 }} />)}
      </MapContainer>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {polyMode
          ? closed
            ? "Poligon închis. Folosește „Anulează ultimul vârf” sau „Șterge poligonul” ca să-l modifici."
            : `Apasă pe hartă pentru fiecare colț al terenului (${vertices.length} ${vertices.length === 1 ? "vârf" : "vârfuri"}, minim 3), apoi „Închide poligonul”.`
          : "Apasă pe hartă ca să marchezi terenul."}{" "}
        {value ? `Punct: ${value.lat.toFixed(5)}, ${value.lng.toFixed(5)}` : "Niciun punct selectat."}
      </p>
    </div>
  );
}
