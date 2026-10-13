import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
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

// value: {lat,lng} | null · onChange({lat,lng}). Click pe hartă = punctul terenului.
export default function LocationPicker({ value, onChange, height = "320px" }) {
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

  const center = value ? [value.lat, value.lng] : DEFAULT_CENTER;
  return (
    <div className="relative isolate space-y-2" data-testid="radacini-location-picker">
      <MapContainer
        center={center}
        zoom={value ? 15 : 11}
        scrollWheelZoom={false}
        style={{ height, width: "100%", borderRadius: "1rem" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <ClickCapture onPick={onChange} />
        {value && <Marker position={[value.lat, value.lng]} icon={icon} />}
      </MapContainer>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Apasă pe hartă ca să marchezi terenul.{" "}
        {value ? `Selectat: ${value.lat.toFixed(5)}, ${value.lng.toFixed(5)}` : "Nicio locație selectată."}
      </p>
    </div>
  );
}
