// Read-only Digital Twin viewer for clients + Designers browse panel
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { X, Building, Star, CheckCircle2, Palette, Sparkles, MapPin, Users, SlidersHorizontal, Box, Layers, Maximize2 } from "lucide-react";
import { API } from "./DashShared";
import TwinAIQA from "../components/TwinAIQA";
import DigitalTwinViewer from "../components/DigitalTwinViewer";

const ROOM_COLORS = {
  living: "bg-emerald-500/20 border-emerald-500/40 text-emerald-300",
  bedroom: "bg-indigo-500/20 border-indigo-500/40 text-indigo-300",
  kitchen: "bg-amber-500/20 border-amber-500/40 text-amber-300",
  bathroom: "bg-cyan-500/20 border-cyan-500/40 text-cyan-300",
  hallway: "bg-stone-500/20 border-stone-500/40 text-stone-300",
  balcony: "bg-teal-500/20 border-teal-500/40 text-teal-300",
  office: "bg-purple-500/20 border-purple-500/40 text-purple-300",
  storage: "bg-slate-500/20 border-slate-500/40 text-slate-300",
  other: "bg-white/10 border-white/20 text-stone-300",
};

const ROOM_TYPE_LABELS = {
  living: "Living", bedroom: "Dormitor", kitchen: "Bucătărie",
  bathroom: "Baie", hallway: "Hol", balcony: "Balcon",
  office: "Birou", storage: "Depozit", other: "Altă",
};

const ASSET_LABELS = {
  hvac: "AC / Climatizare", boiler: "Centrală termică", electric_panel: "Panou electric",
  water_meter: "Apometru", gas_meter: "Gaz", appliance: "Electrocasnic",
  lighting: "Iluminat", plumbing: "Sanitar", other: "Altul",
};

const CONDITION_DOT = {
  good: "bg-emerald-400", fair: "bg-amber-400",
  needs_service: "bg-orange-400", critical: "bg-red-400",
};

// ============= 2D STRUCTURED TWIN PANEL (reusable, self-contained) =============
// Randează stratul 2D al Property Twin: camere + active (SVG top-down) din colecția `twins`.
export const ClientTwin2DPanel = ({ propertyId }) => {
  const [twin, setTwin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    axios.get(`${API}/properties/${propertyId}/twin`)
      .then(r => { if (alive) setTwin(r.data); })
      .catch(() => { if (alive) setTwin({ rooms: [], assets: [], status: "not_requested" }); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [propertyId]);

  const rooms = twin?.rooms || [];
  const assets = twin?.assets || [];
  const bounds = rooms.length ? {
    maxX: Math.max(...rooms.map(r => r.x + r.w)) + 40,
    maxY: Math.max(...rooms.map(r => r.y + r.h)) + 40,
  } : { maxX: 500, maxY: 400 };

  if (loading) return <div className="text-center py-10 text-stone-500" data-testid="twin-2d-loading">Se încarcă planul 2D...</div>;
  if (rooms.length === 0) return (
    <div className="text-center py-10 text-stone-500" data-testid="twin-2d-empty">
      <Building className="w-12 h-12 mx-auto mb-3 opacity-30" />
      Stratul 2D nu are camere definite încă. Operatorul lucrează la el.
    </div>
  );

  return (
    <div className="space-y-5" data-testid="twin-2d-panel">
      {twin?.project_id && <TwinAIQA projectId={twin.project_id} />}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3">
          <div className="text-[10px] uppercase tracking-wider text-emerald-300/80">Camere</div>
          <div className="font-serif text-2xl text-emerald-300">{rooms.length}</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
          <div className="text-[10px] uppercase tracking-wider text-amber-300/80">Asset-uri</div>
          <div className="font-serif text-2xl text-amber-300">{assets.length}</div>
        </div>
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3">
          <div className="text-[10px] uppercase tracking-wider text-purple-300/80">Suprafață totală</div>
          <div className="font-serif text-2xl text-purple-300">{rooms.reduce((s, r) => s + (r.area || 0), 0)}m²</div>
        </div>
      </div>
      <div className="bg-gradient-to-br from-slate-900 via-cyan-950 to-slate-900 border border-white/10 rounded-2xl p-4 overflow-x-auto">
        <svg viewBox={`0 0 ${bounds.maxX} ${bounds.maxY}`} className="w-full" style={{ minHeight: 280 }} data-testid="twin-svg">
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          {rooms.map(r => (
            <g key={r.id} data-testid={`twin-room-${r.id}`}>
              <rect x={r.x} y={r.y} width={r.w} height={r.h}
                fill="rgba(212,255,58,0.05)" stroke="rgba(212,255,58,0.4)" strokeWidth="2" rx="6" />
              <text x={r.x + r.w / 2} y={r.y + r.h / 2 - 6} textAnchor="middle" fill="#d4ff3a" fontSize="14" fontWeight="500">{r.name}</text>
              <text x={r.x + r.w / 2} y={r.y + r.h / 2 + 14} textAnchor="middle" fill="rgba(255,255,255,0.6)" fontSize="11">{r.area}m²</text>
            </g>
          ))}
          {assets.map(a => (
            <g key={a.id} data-testid={`twin-asset-${a.id}`}>
              <circle cx={a.x} cy={a.y} r="8" fill={
                a.condition === "good" ? "#34d399" :
                a.condition === "fair" ? "#fbbf24" :
                a.condition === "needs_service" ? "#fb923c" : "#f87171"
              } />
              <circle cx={a.x} cy={a.y} r="14" fill="currentColor" opacity="0.15">
                <animate attributeName="r" values="14;20;14" dur="2.5s" repeatCount="indefinite" />
              </circle>
            </g>
          ))}
        </svg>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-2">Camere ({rooms.length})</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {rooms.map(r => (
            <div key={r.id} className={`rounded-xl p-3 border ${ROOM_COLORS[r.type] || ROOM_COLORS.other}`}>
              <div className="flex items-center justify-between">
                <div className="font-medium text-sm">{r.name}</div>
                <div className="text-[10px] uppercase tracking-wider opacity-70">{ROOM_TYPE_LABELS[r.type] || r.type}</div>
              </div>
              <div className="text-xs opacity-70 mt-1">{r.area}m²</div>
            </div>
          ))}
        </div>
      </div>
      {assets.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-2">Asset-uri tehnice ({assets.length})</div>
          <div className="space-y-2">
            {assets.map(a => (
              <div key={a.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${CONDITION_DOT[a.condition] || CONDITION_DOT.good}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium">{a.name}</div>
                  <div className="text-[10px] uppercase tracking-wider text-stone-500">{ASSET_LABELS[a.type] || a.type}</div>
                </div>
                <div className="text-[10px] uppercase tracking-wider text-stone-400">{a.condition}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============= 2D TWIN MODAL (thin wrapper — backwards compatible) =============
export const ClientTwinViewerModal = ({ propertyId, propertyName, onClose }) => (
  <motion.div
    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 overflow-y-auto"
    onClick={onClose}
    data-testid="twin-viewer-modal"
  >
    <motion.div
      initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
      className="bg-stone-950 border border-white/10 rounded-3xl w-full max-w-5xl max-h-[90vh] overflow-y-auto"
      onClick={e => e.stopPropagation()}
    >
      <div className="sticky top-0 bg-stone-950/95 backdrop-blur border-b border-white/10 p-5 flex items-center justify-between z-10">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-emerald-400 mb-1">Digital Twin · Structură 2D</div>
          <h2 className="font-serif text-2xl flex items-center gap-2">
            <Building className="w-5 h-5 text-[#d4ff3a]" />{propertyName || "Proprietatea ta"}
          </h2>
        </div>
        <button onClick={onClose} className="w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center" data-testid="close-twin-viewer">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="p-5">
        <ClientTwin2DPanel propertyId={propertyId} />
      </div>
    </motion.div>
  </motion.div>
);

// Protejează experiența unificată dacă un model 3D e corupt/nu se încarcă (nu rescrie viewerul).
class ViewerErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch() { /* swallow — fallback UI takes over */ }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}

// ============= UNIFIED PROPERTY DIGITAL TWIN (P1) =============
// O singură experiență centrată pe proprietate: 2D + 3D = două reprezentări ale ACELEIAȘI proprietăți.
// Reutilizează ClientTwin2DPanel (2D) + DigitalTwinViewer existent (3D). Nu rescrie viewerele.
export const PropertyTwinModal = ({ propertyId, propertyName, dtProjectId, modelUrl, onClose }) => {
  const [overview, setOverview] = useState(null);
  const [tab, setTab] = useState(modelUrl ? "3d" : "2d");
  const [viewer, setViewer] = useState(null); // {id, model_url, name}

  useEffect(() => {
    axios.get(`${API}/properties/${propertyId}/digital-twin`)
      .then(r => setOverview(r.data))
      .catch(() => setOverview(null));
  }, [propertyId]);

  const projects = overview?.twin_3d?.projects || [];
  const primary3d = (dtProjectId && modelUrl)
    ? { id: dtProjectId, model_url: modelUrl, name: propertyName }
    : (projects.find(p => p.model_url) || null);
  const name = overview?.property_name || propertyName || "Proprietatea ta";

  // Full-screen immersive 3D viewer (reused as-is). Închiderea revine la hub-ul Twin.
  if (viewer) {
    const fallback = (
      <div className="fixed inset-0 z-50 bg-stone-950 flex items-center justify-center p-6" data-testid="twin-3d-load-error">
        <div className="max-w-md text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-500/15 border border-red-500/30 flex items-center justify-center mx-auto mb-4">
            <Box className="w-7 h-7 text-red-300" />
          </div>
          <div className="font-serif text-xl text-white mb-2">Modelul 3D nu poate fi încărcat</div>
          <p className="text-sm text-stone-400 mb-5">Fișierul pare corupt sau incomplet. Structura 2D rămâne disponibilă, iar modelul poate fi reîncărcat de proprietar/specialist.</p>
          <button onClick={() => setViewer(null)}
            className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-5 py-2.5 rounded-full text-sm transition"
            data-testid="twin-3d-error-back">
            Înapoi la Digital Twin
          </button>
        </div>
      </div>
    );
    return (
      <ViewerErrorBoundary key={viewer.id} fallback={fallback}>
        <DigitalTwinViewer
          projectId={viewer.id}
          modelUrl={viewer.model_url}
          projectName={viewer.name || name}
          onClose={() => setViewer(null)}
        />
      </ViewerErrorBoundary>
    );
  }

  const TabBtn = ({ id, icon: Icon, label }) => (
    <button
      onClick={() => setTab(id)}
      className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition ${
        tab === id ? "bg-[#d4ff3a] text-stone-900" : "bg-white/5 text-stone-300 hover:bg-white/10"
      }`}
      data-testid={`twin-tab-${id}`}
    >
      <Icon className="w-4 h-4" /> {label}
    </button>
  );

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 overflow-y-auto"
      onClick={onClose}
      data-testid="property-twin-modal"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="bg-stone-950 border border-white/10 rounded-3xl w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-stone-950/95 backdrop-blur border-b border-white/10 p-5 z-10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-emerald-400 mb-1">Digital Twin · Proprietate</div>
              <h2 className="font-serif text-2xl flex items-center gap-2">
                <Building className="w-5 h-5 text-[#d4ff3a]" />{name}
              </h2>
              <p className="text-[11px] text-stone-500 mt-1">Două reprezentări ale aceleiași proprietăți: structură 2D + model 3D.</p>
            </div>
            <button onClick={onClose} className="w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center" data-testid="close-property-twin">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex gap-2">
            <TabBtn id="2d" icon={Layers} label="Structură 2D" />
            <TabBtn id="3d" icon={Box} label="Model 3D" />
          </div>
        </div>

        <div className="p-5">
          {tab === "2d" && <ClientTwin2DPanel propertyId={propertyId} />}
          {tab === "3d" && (
            primary3d?.model_url ? (
              <div className="space-y-4" data-testid="twin-3d-panel">
                <div className="bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 border border-white/10 rounded-2xl p-6 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 flex items-center justify-center mx-auto mb-3">
                    <Box className="w-7 h-7 text-[#d4ff3a]" />
                  </div>
                  <div className="font-serif text-xl text-white mb-1">Model 3D disponibil</div>
                  <p className="text-sm text-stone-400 mb-4">Vizualizare BIM · rotire 360° · X-Ray · pin-uri · măsurători</p>
                  <button
                    onClick={() => setViewer(primary3d)}
                    className="inline-flex items-center gap-2 bg-[#d4ff3a] text-stone-900 font-semibold px-5 py-2.5 rounded-full text-sm hover:bg-[#c8f520] transition"
                    data-testid="open-3d-viewer"
                  >
                    <Maximize2 className="w-4 h-4" /> Deschide viewer imersiv
                  </button>
                </div>
                {projects.length > 1 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-2">Toate modelele proprietății ({projects.length})</div>
                    <div className="space-y-2">
                      {projects.map(p => (
                        <div key={p.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm font-medium truncate">{p.name}</div>
                            <div className="text-[10px] uppercase tracking-wider text-stone-500">{p.models_count} model{p.models_count === 1 ? "" : "e"}</div>
                          </div>
                          {p.model_url ? (
                            <button
                              onClick={() => setViewer({ id: p.id, model_url: p.model_url, name: p.name })}
                              className="text-xs px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 transition shrink-0"
                              data-testid={`open-3d-${p.id}`}
                            >
                              Deschide
                            </button>
                          ) : (
                            <span className="text-[10px] text-stone-500 shrink-0">În procesare</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-stone-500" data-testid="twin-3d-empty">
                <Box className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <div className="text-stone-300 font-medium mb-1">Nu există încă un model 3D pentru această proprietate</div>
                <p className="text-sm">Structura 2D e disponibilă în tab-ul alăturat. Modelul 3D profesional poate fi adus ulterior și se va ancora automat de această proprietate.</p>
              </div>
            )
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

// ============= DESIGNERS BROWSE PANEL (inline) =============
export const DesignersBrowse = ({ onSelect }) => {
  const navigate = useNavigate();
  const [designers, setDesigners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [zone, setZone] = useState("");
  const [style, setStyle] = useState("");
  const [availableZones, setAvailableZones] = useState([]);
  const [availableStyles, setAvailableStyles] = useState([]);

  // Load filter dropdown options once
  useEffect(() => {
    axios.get(`${API}/marketplace/filters?category=interior_design`)
      .then(r => {
        setAvailableZones(r.data.zones || []);
        setAvailableStyles(r.data.styles || []);
      })
      .catch(() => {});
  }, []);

  // Reload designers when filters change
  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ category: "interior_design", verified_only: "true", sort: "rating" });
    if (zone) params.set("zone", zone);
    if (style) params.set("style", style);
    axios.get(`${API}/marketplace/specialists?${params}`)
      .then(r => setDesigners(r.data || []))
      .catch(() => setDesigners([]))
      .finally(() => setLoading(false));
  }, [zone, style]);

  const hasAnyFilters = availableZones.length > 0 || availableStyles.length > 0;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="glass-strong rounded-3xl p-5 sm:p-6 mt-4" data-testid="designers-browse">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-2xl bg-lime-500/15 border border-lime-500/40 flex items-center justify-center">
            <Users className="w-4 h-4 text-purple-300" />
          </div>
          <div>
            <h3 className="font-serif text-lg leading-tight">Designerii noștri</h3>
            <div className="text-[10px] uppercase tracking-wider text-stone-400">
              {loading ? "Caut designeri..." : `${designers.length} ${designers.length === 1 ? "designer" : "designeri"} · verificați`}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasAnyFilters && (
            <button onClick={() => setFiltersOpen(o => !o)}
              className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border flex items-center gap-1 transition ${(zone || style) ? "bg-purple-500/25 text-purple-200 border-purple-500/50" : "bg-white/5 text-stone-400 border-white/10 hover:bg-white/10"}`}
              data-testid="designers-filters-toggle">
              <SlidersHorizontal className="w-3 h-3" />
              Filtre{(zone || style) ? ` · ${[zone, style].filter(Boolean).length}` : ""}
            </button>
          )}
          <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">DESIGN INTERIOR</span>
        </div>
      </div>

      {/* Filter panel */}
      {filtersOpen && hasAnyFilters && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-3 mb-4 space-y-3" data-testid="designers-filters-panel">
          {availableZones.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1.5 flex items-center gap-1">
                <MapPin className="w-3 h-3" />Zonă acoperire
              </div>
              <div className="flex flex-wrap gap-1.5">
                <button onClick={() => setZone("")}
                  className={`text-xs px-3 py-1 rounded-full border transition ${zone === "" ? "bg-[#d4ff3a]/20 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-white/5 text-stone-400 border-white/10 hover:bg-white/10"}`}
                  data-testid="filter-zone-all">Toate</button>
                {availableZones.map(z => (
                  <button key={z} onClick={() => setZone(z)}
                    className={`text-xs px-3 py-1 rounded-full border transition ${zone === z ? "bg-[#d4ff3a]/20 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-white/5 text-stone-400 border-white/10 hover:bg-white/10"}`}
                    data-testid={`filter-zone-${z}`}>{z}</button>
                ))}
              </div>
            </div>
          )}
          {availableStyles.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1.5 flex items-center gap-1">
                <Palette className="w-3 h-3" />Stil portfolio
              </div>
              <div className="flex flex-wrap gap-1.5">
                <button onClick={() => setStyle("")}
                  className={`text-xs px-3 py-1 rounded-full border transition ${style === "" ? "bg-purple-500/20 text-purple-300 border-purple-500/40" : "bg-white/5 text-stone-400 border-white/10 hover:bg-white/10"}`}
                  data-testid="filter-style-all">Toate</button>
                {availableStyles.map(s => (
                  <button key={s} onClick={() => setStyle(s)}
                    className={`text-xs px-3 py-1 rounded-full border capitalize transition ${style === s ? "bg-purple-500/20 text-purple-300 border-purple-500/40" : "bg-white/5 text-stone-400 border-white/10 hover:bg-white/10"}`}
                    data-testid={`filter-style-${s}`}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {(zone || style) && (
            <button onClick={() => { setZone(""); setStyle(""); }} className="text-xs text-stone-500 hover:text-stone-300 underline" data-testid="filter-clear">
              Resetează filtrele
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-stone-500 text-sm">Se caută designeri...</div>
      ) : designers.length === 0 ? (
        <div className="text-center py-8 text-stone-500 text-sm" data-testid="designers-empty">
          <Palette className="w-10 h-10 mx-auto mb-2 opacity-30" />
          Nu am găsit designeri pentru filtrele selectate. Încearcă alte criterii.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {designers.slice(0, 6).map(d => (
            <div key={d.id}
              className="bg-white dark:bg-stone-900 hover:bg-stone-50 dark:hover:bg-stone-800 border border-stone-200 dark:border-stone-800 hover:border-lime-500/50 rounded-2xl p-4 transition-all group flex flex-col"
              data-testid={`designer-card-${d.id}`}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-11 h-11 rounded-2xl bg-lime-500/15 border border-lime-500/30 flex items-center justify-center font-serif text-lg text-lime-700 dark:text-lime-300 shrink-0 overflow-hidden">
                  {d.avatar || d.picture ? <img src={d.avatar || d.picture} alt={d.name} className="w-full h-full object-cover" /> : (d.name || "?").charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm truncate flex items-center gap-1.5 text-stone-900 dark:text-white">
                    {d.name}
                    {d.verified && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-stone-500 dark:text-stone-400">
                    <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                    <span className="text-amber-600 dark:text-amber-300">{d.rating?.toFixed(1) || "—"}</span>
                    <span className="text-stone-500">· {d.reviews_count || 0} recenzii</span>
                  </div>
                </div>
                {d.tier && (
                  <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-lime-500/15 text-lime-700 dark:text-lime-300 border border-lime-500/40 shrink-0">{d.tier}</span>
                )}
              </div>
              {(d.service_categories && d.service_categories.length > 0) && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {d.service_categories.slice(0, 3).map(c => (
                    <span key={c} className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border border-stone-200 dark:border-stone-700">{c.replace("_", " ")}</span>
                  ))}
                </div>
              )}
              <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-2">
                {d.availability_status === "available" ? "✓ Disponibil" : (d.availability_status || "")}
                {d.coverage_zones && d.coverage_zones.length > 0 && ` · ${d.coverage_zones.length} zone`}
              </div>
              <div className="flex gap-2 mt-3 pt-3 border-t border-stone-200 dark:border-stone-800">
                <button
                  onClick={() => navigate(`/specialists/${d.id}`)}
                  className="flex-1 text-xs px-3 py-2 rounded-full bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-200 border border-stone-200 dark:border-stone-700 transition flex items-center justify-center gap-1"
                  data-testid={`designer-view-profile-${d.id}`}
                >
                  Vezi profil
                </button>
                <button
                  onClick={() => onSelect && onSelect(d)}
                  className="flex-1 text-xs px-3 py-2 rounded-full bg-lime-400 hover:bg-lime-500 text-stone-900 font-semibold border border-lime-500 transition flex items-center justify-center gap-1 shadow-sm"
                  data-testid={`designer-request-${d.id}`}
                >
                  <Sparkles className="w-3 h-3" />Solicită
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};
