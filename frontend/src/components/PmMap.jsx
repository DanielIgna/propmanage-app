import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import axios from "axios";
import { MapPin, ExternalLink } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ── Provider abstraction ────────────────────────────────────────────────────
// Google Maps când GOOGLE_MAPS_ENABLED=true + cheie; altfel fallback Leaflet
// pe tiles OpenStreetMap (fără cheie — funcțional în Preview).
let _gmp = null;
const loadGoogle = (key) => {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (_gmp) return _gmp;
  _gmp = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = `https://maps.googleapis.com/maps/api/js?key=${key}`;
    s.async = true; s.defer = true; s.onload = () => res(window.google.maps); s.onerror = rej;
    document.head.appendChild(s);
  });
  return _gmp;
};

export const useMapsConfig = () => {
  const [cfg, setCfg] = useState(null);
  useEffect(() => {
    let mounted = true;
    axios.get(`${API}/public/maps/config`)
      .then(r => mounted && setCfg(r.data))
      .catch(() => mounted && setCfg({ enabled: false, api_key: null, provider: "fallback" }));
    return () => { mounted = false; };
  }, []);
  return cfg;
};

const limeIcon = () => L.divIcon({
  className: "pm-marker",
  html: `<div style="background:#d4ff3a;width:22px;height:22px;border-radius:50%;border:3px solid #0a0a0b;box-shadow:0 0 0 2px #d4ff3a66;"></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

// ── Google multi-marker renderer ─────────────────────────────────────────────
const GoogleMarkersMap = ({ points, apiKey, height }) => {
  const ref = useRef(null);
  useEffect(() => {
    let cancelled = false;
    loadGoogle(apiKey).then((maps) => {
      if (cancelled || !ref.current) return;
      const first = points[0];
      const map = new maps.Map(ref.current, {
        center: { lat: first?.lat ?? 44.4268, lng: first?.lng ?? 26.1025 },
        zoom: 12, mapTypeId: "roadmap", disableDefaultUI: false,
      });
      const bounds = new maps.LatLngBounds();
      points.forEach((p) => {
        const mk = new maps.Marker({ position: { lat: p.lat, lng: p.lng }, map });
        bounds.extend(mk.getPosition());
        const link = p.href
          ? `<a href="${esc(p.href)}" style="display:inline-block;background:#0a0a0b;color:#fff;font-size:12px;padding:4px 10px;border-radius:999px;text-decoration:none;">${esc(p.hrefLabel || "Vezi detalii")} →</a>`
          : "";
        const html = `<div style="font-family:inherit;min-width:160px;"><div style="font-weight:600;margin-bottom:2px;">${esc(p.title)}</div><div style="font-size:12px;color:#666;margin-bottom:6px;">${esc(p.subtitle || "")}</div>${p.price ? `<div style="font-family:monospace;margin-bottom:6px;">${esc(p.price)}</div>` : ""}${p.provenanceLabel ? `<div style="font-size:11px;color:#a8a29e;margin-bottom:6px;">${esc(p.provenanceLabel)}</div>` : ""}${link}</div>`;
        const iw = new maps.InfoWindow({ content: html });
        mk.addListener("click", () => iw.open(map, mk));
      });
      if (points.length > 1) map.fitBounds(bounds, 60);
      else if (points.length === 1) map.setZoom(16);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [points, apiKey]);
  return <div ref={ref} style={{ height, width: "100%", borderRadius: "1.5rem", background: "#0e0e10" }} data-testid="pm-map-google" />;
};

// ── Leaflet fallback (OpenStreetMap, key-free) ───────────────────────────────
const LeafletMarkersMap = ({ points, height }) => {
  const mapRef = useRef(null);
  const center = points.length > 0 ? [points[0].lat, points[0].lng] : [44.4268, 26.1025];
  useEffect(() => {
    if (mapRef.current && points.length > 1) {
      const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng]));
      mapRef.current.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
    }
  }, [points]);
  return (
    <MapContainer center={center} zoom={points.length === 1 ? 16 : 12}
      style={{ height, width: "100%", borderRadius: "1.5rem", background: "#0e0e10" }} ref={mapRef}
      data-testid="pm-map-fallback">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((p) => (
        <Marker key={p.id} position={[p.lat, p.lng]} icon={limeIcon()}>
          <Popup>
            <div className="text-sm" data-testid={`pm-popup-${p.id}`}>
              <div className="font-semibold mb-1">{p.title}</div>
              {p.subtitle && <div className="text-xs text-stone-500 mb-2">{p.subtitle}</div>}
              {p.price && <div className="font-mono text-base mb-2" style={{ color: "#0a0a0b" }}>{p.price}</div>}
              {p.provenanceLabel && <div className="text-[11px] text-stone-500 mb-2">{p.provenanceLabel}</div>}
              {p.href && (
                <a href={p.href} className="inline-block bg-[#0a0a0b] text-white text-xs px-3 py-1.5 rounded-full" data-testid={`pm-popup-link-${p.id}`}>
                  {p.hrefLabel || "Vezi detalii"} →
                </a>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

// Multi-marker map — provider ales automat din config.
export const PmMarkersMap = ({ points = [], height = "70vh", emptyLabel = "Niciun rezultat cu coordonate." }) => {
  const cfg = useMapsConfig();
  const withCoords = (points || []).filter((p) => p.lat && p.lng);
  if (cfg === null) {
    return <div style={{ height }} className="rounded-3xl bg-white/[0.03] border border-white/10 flex items-center justify-center text-stone-500 text-sm" data-testid="pm-map-loading">Se încarcă harta…</div>;
  }
  const useGoogle = cfg?.enabled && cfg?.api_key;
  return (
    <div className="relative" data-testid="pm-markers-map">
      {withCoords.length === 0 ? (
        <div style={{ height }} className="rounded-3xl bg-white/[0.03] border border-white/10 flex items-center justify-center">
          <p className="text-stone-300 text-sm">{emptyLabel}</p>
        </div>
      ) : useGoogle ? (
        <GoogleMarkersMap points={withCoords} apiKey={cfg.api_key} height={height} />
      ) : (
        <LeafletMarkersMap points={withCoords} height={height} />
      )}
    </div>
  );
};

// Single-marker preview — pentru confirmarea clădirii.
export const PmMiniMap = ({ lat, lng, label, height = "220px" }) => {
  const cfg = useMapsConfig();
  const gref = useRef(null);
  const useGoogle = cfg?.enabled && cfg?.api_key && lat && lng;
  useEffect(() => {
    if (!useGoogle) return;
    let cancelled = false;
    loadGoogle(cfg.api_key).then((maps) => {
      if (cancelled || !gref.current) return;
      const m = new maps.Map(gref.current, { center: { lat, lng }, zoom: 17, mapTypeId: "hybrid", disableDefaultUI: true });
      new maps.Marker({ position: { lat, lng }, map: m });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [useGoogle, lat, lng, cfg?.api_key]);

  if (!lat || !lng) {
    return (
      <div style={{ height }} className="rounded-2xl border border-white/10 bg-white/[0.03] flex items-center justify-center text-stone-500 text-xs" data-testid="pm-minimap-nocoords">
        Fără coordonate pentru previzualizare.
      </div>
    );
  }
  if (useGoogle) {
    return <div ref={gref} style={{ height }} className="w-full rounded-2xl border border-white/10" data-testid="pm-minimap-google" />;
  }
  return (
    <div style={{ height }} className="rounded-2xl border border-white/10 bg-white/[0.03] flex flex-col items-center justify-center gap-2" data-testid="pm-minimap-fallback">
      <MapPin className="w-6 h-6 text-[#d4ff3a]" />
      <div className="text-xs text-stone-400">{label || "Locație pe hartă"}</div>
      <a href={`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`} target="_blank" rel="noreferrer"
        className="text-xs text-[#d4ff3a] inline-flex items-center gap-1" data-testid="pm-minimap-gmaps-link">
        Deschide în Google Maps <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  );
};

export default PmMarkersMap;
