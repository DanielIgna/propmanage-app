// Operator-specific components: Twins List + 2D Floorplan Editor + Validator
//
// PROPERTY TWIN · STRATUL 2D (decizie Fondator, 27 Aug 2026): această suprafață operează pe
// colecția `twins` (camere + geometrie + active poziționate) = stratul 2D structurat, client-facing.
// NU e duplicat cu OperatorDigitalTwin.jsx — acela e stratul 3D profesional (`digital_twin_projects`).
// Ambele sunt suprafețe operator ale ACELUIAȘI Property Twin (2D + 3D), expuse ca tab-uri în
// OperatorDashboard ("twins" vs "dt_pro"). Consolidare = clarificare non-breaking, FĂRĂ ștergere.
import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import {
  X, Building2, Layers, Plus, Trash2, CheckCircle2, RotateCcw, Square,
  Bed, ChefHat, Bath, ArrowRight, Wrench, Zap, Wind, Droplet, Box, Save
} from "lucide-react";
import { formatApiError } from "../auth";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROOM_TYPES = {
  living: { label: "Living", color: "#d4ff3a", icon: Square },
  bedroom: { label: "Dormitor", color: "#7aa3ff", icon: Bed },
  kitchen: { label: "Bucătărie", color: "#ffb86b", icon: ChefHat },
  bathroom: { label: "Baie", color: "#5be8d4", icon: Bath },
  hallway: { label: "Hol", color: "#a0a0a8", icon: ArrowRight },
  balcony: { label: "Balcon", color: "#c4a8e6", icon: Square },
  office: { label: "Birou", color: "#ff8fab", icon: Square },
  storage: { label: "Depozit", color: "#888893", icon: Box },
  other: { label: "Alta", color: "#666674", icon: Square },
};

const ASSET_TYPES = {
  hvac: { label: "HVAC", icon: Wind, color: "text-cyan-400" },
  boiler: { label: "Centrală", icon: Wind, color: "text-amber-400" },
  electric_panel: { label: "Panou Electric", icon: Zap, color: "text-yellow-400" },
  water_meter: { label: "Contor Apă", icon: Droplet, color: "text-blue-400" },
  gas_meter: { label: "Contor Gaz", icon: Wind, color: "text-orange-400" },
  appliance: { label: "Electrocasnic", icon: Box, color: "text-purple-400" },
  lighting: { label: "Iluminat", icon: Zap, color: "text-amber-300" },
  plumbing: { label: "Sanitar", icon: Droplet, color: "text-cyan-300" },
  other: { label: "Altul", icon: Box, color: "text-stone-400" },
};

const CONDITION_COLORS = {
  good: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  fair: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  needs_service: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  critical: "bg-red-500/20 text-red-300 border-red-500/30",
};

const STATUS_LABELS = {
  draft: { label: "Ciornă", color: "bg-stone-500/20 text-stone-300" },
  pending_validation: { label: "În validare", color: "bg-amber-500/20 text-amber-300" },
  approved: { label: "Aprobat", color: "bg-emerald-500/20 text-emerald-300" },
  needs_revision: { label: "Necesită revizie", color: "bg-red-500/20 text-red-300" },
};

function uid() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

// ============= TWIN EDITOR/VALIDATOR =============
export const TwinEditorModal = ({ propertyId, onClose, onSaved }) => {
  const [twin, setTwin] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(null); // {kind:"room"|"asset", id}
  const [dragInfo, setDragInfo] = useState(null);
  const [tool, setTool] = useState("select"); // select, add_room, add_asset
  const [newRoomType, setNewRoomType] = useState("living");
  const [newAssetType, setNewAssetType] = useState("hvac");
  const [validateMode, setValidateMode] = useState(null); // null, approve, revision
  const [validationNotes, setValidationNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const canvasRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/operator/twins/${propertyId}`);
      setTwin(data);
      setRooms(data.rooms || []);
      setAssets(data.assets || []);
    } catch (e) { /* noop */ }
  };
  useEffect(() => { load(); }, [propertyId]);

  const selectedRoom = selected?.kind === "room" ? rooms.find(r => r.id === selected.id) : null;
  const selectedAsset = selected?.kind === "asset" ? assets.find(a => a.id === selected.id) : null;

  const canvasCoords = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(e.clientX - rect.left, rect.width)),
      y: Math.max(0, Math.min(e.clientY - rect.top, rect.height)),
    };
  };

  const onCanvasClick = (e) => {
    if (tool === "add_room") {
      const p = canvasCoords(e);
      const newRoom = { id: uid(), name: ROOM_TYPES[newRoomType].label, type: newRoomType, area: 10, x: p.x - 60, y: p.y - 50, w: 120, h: 100 };
      setRooms([...rooms, newRoom]);
      setSelected({ kind: "room", id: newRoom.id });
      setTool("select");
    } else if (tool === "add_asset") {
      const p = canvasCoords(e);
      const newAsset = { id: uid(), type: newAssetType, name: ASSET_TYPES[newAssetType].label, x: p.x, y: p.y, condition: "good" };
      setAssets([...assets, newAsset]);
      setSelected({ kind: "asset", id: newAsset.id });
      setTool("select");
    } else if (e.target === canvasRef.current) {
      setSelected(null);
    }
  };

  const startDrag = (e, kind, id) => {
    if (tool !== "select") return;
    e.stopPropagation();
    const p = canvasCoords(e);
    const item = kind === "room" ? rooms.find(r => r.id === id) : assets.find(a => a.id === id);
    setDragInfo({ kind, id, offsetX: p.x - item.x, offsetY: p.y - item.y });
    setSelected({ kind, id });
  };

  const onCanvasMove = (e) => {
    if (!dragInfo) return;
    const p = canvasCoords(e);
    const nx = p.x - dragInfo.offsetX;
    const ny = p.y - dragInfo.offsetY;
    if (dragInfo.kind === "room") {
      setRooms(rooms.map(r => r.id === dragInfo.id ? { ...r, x: Math.max(0, nx), y: Math.max(0, ny) } : r));
    } else {
      setAssets(assets.map(a => a.id === dragInfo.id ? { ...a, x: Math.max(0, nx), y: Math.max(0, ny) } : a));
    }
  };

  const endDrag = () => setDragInfo(null);

  const updateSelected = (changes) => {
    if (selectedRoom) setRooms(rooms.map(r => r.id === selectedRoom.id ? { ...r, ...changes } : r));
    if (selectedAsset) setAssets(assets.map(a => a.id === selectedAsset.id ? { ...a, ...changes } : a));
  };

  const deleteSelected = () => {
    if (selectedRoom) setRooms(rooms.filter(r => r.id !== selectedRoom.id));
    if (selectedAsset) setAssets(assets.filter(a => a.id !== selectedAsset.id));
    setSelected(null);
  };

  const save = async (silent = false) => {
    setSaving(true);
    try {
      await axios.post(`${API}/operator/twins/${propertyId}`, { rooms, assets, notes: twin?.notes });
      if (!silent) alert("Twin salvat");
      onSaved?.();
    } catch (e) { alert(formatApiError(e)); }
    finally { setSaving(false); }
  };

  const submitValidation = async (action) => {
    setSaving(true);
    try {
      // Save first
      await axios.post(`${API}/operator/twins/${propertyId}`, { rooms, assets });
      await axios.post(`${API}/operator/twins/${propertyId}/validate`, { action, notes: validationNotes });
      onSaved?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setSaving(false); }
  };

  if (!twin) return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="text-stone-400">Se încarcă...</div>
    </div>
  );

  const statusInfo = STATUS_LABELS[twin.status] || STATUS_LABELS.draft;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-4">
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl w-full max-w-6xl h-[95vh] flex flex-col overflow-hidden" data-testid="twin-editor">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3 min-w-0">
            <Layers className="w-5 h-5 text-[#d4ff3a] flex-shrink-0" />
            <div className="min-w-0">
              <div className="font-serif text-lg truncate">{twin.property_name || "Twin"}</div>
              <div className="flex items-center gap-2 text-[10px]">
                <span className={`px-2 py-0.5 rounded-full uppercase tracking-wider ${statusInfo.color}`}>{statusInfo.label}</span>
                <span className="text-stone-500">{rooms.length} camere · {assets.length} asset-uri</span>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="close-twin"><X className="w-4 h-4 text-stone-400" /></button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-black/30 flex-wrap">
          <ToolBtn active={tool === "select"} onClick={() => setTool("select")} icon={Square} label="Selectează" tid="tool-select" />
          <div className="h-6 w-px bg-white/10" />
          <ToolBtn active={tool === "add_room"} onClick={() => setTool("add_room")} icon={Plus} label="Cameră" tid="tool-room" />
          <select value={newRoomType} onChange={e => setNewRoomType(e.target.value)} className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs" data-testid="room-type-select">
            {Object.entries(ROOM_TYPES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <div className="h-6 w-px bg-white/10" />
          <ToolBtn active={tool === "add_asset"} onClick={() => setTool("add_asset")} icon={Plus} label="Asset" tid="tool-asset" />
          <select value={newAssetType} onChange={e => setNewAssetType(e.target.value)} className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs" data-testid="asset-type-select">
            {Object.entries(ASSET_TYPES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <div className="flex-1" />
          <button onClick={() => save()} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs disabled:opacity-50" data-testid="save-twin">
            <Save className="w-3.5 h-3.5" />Salvează ciornă
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 flex overflow-hidden">
          {/* Canvas */}
          <div className="flex-1 bg-[#0a0a0b] overflow-hidden relative">
            <div
              ref={canvasRef}
              onClick={onCanvasClick}
              onMouseMove={onCanvasMove}
              onMouseUp={endDrag}
              onMouseLeave={endDrag}
              className="absolute inset-0"
              style={{
                backgroundImage: "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
                backgroundSize: "20px 20px",
                cursor: tool === "select" ? "default" : "crosshair",
              }}
              data-testid="twin-canvas"
            >
              {/* Rooms */}
              {rooms.map(r => {
                const cfg = ROOM_TYPES[r.type] || ROOM_TYPES.other;
                const isSel = selected?.kind === "room" && selected.id === r.id;
                return (
                  <div
                    key={r.id}
                    onMouseDown={(e) => startDrag(e, "room", r.id)}
                    className="absolute rounded-lg flex items-center justify-center text-xs select-none transition"
                    style={{
                      left: r.x, top: r.y, width: r.w, height: r.h,
                      backgroundColor: `${cfg.color}15`,
                      border: `2px solid ${isSel ? cfg.color : cfg.color + "55"}`,
                      cursor: tool === "select" ? "move" : "inherit",
                      boxShadow: isSel ? `0 0 0 3px ${cfg.color}33` : "none",
                    }}
                    data-testid={`room-${r.id}`}
                  >
                    <div className="text-center pointer-events-none">
                      <div className="font-medium" style={{ color: cfg.color }}>{r.name}</div>
                      <div className="text-[10px] text-stone-400">{r.area} m²</div>
                    </div>
                  </div>
                );
              })}
              {/* Assets */}
              {assets.map(a => {
                const cfg = ASSET_TYPES[a.type] || ASSET_TYPES.other;
                const Ic = cfg.icon;
                const isSel = selected?.kind === "asset" && selected.id === a.id;
                return (
                  <div
                    key={a.id}
                    onMouseDown={(e) => startDrag(e, "asset", a.id)}
                    className={`absolute w-9 h-9 rounded-full bg-black/80 border-2 flex items-center justify-center cursor-move transition ${isSel ? "border-[#d4ff3a] scale-110" : "border-white/30"}`}
                    style={{ left: a.x - 18, top: a.y - 18 }}
                    title={a.name}
                    data-testid={`asset-${a.id}`}
                  >
                    <Ic className={`w-4 h-4 ${cfg.color}`} />
                  </div>
                );
              })}
              {/* Empty state hint */}
              {rooms.length === 0 && assets.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-center">
                    <Building2 className="w-12 h-12 text-stone-700 mx-auto mb-2" />
                    <div className="text-sm text-stone-500">Canvas gol</div>
                    <div className="text-[11px] text-stone-600 mt-1">Selectează &quot;Cameră&quot; sau &quot;Asset&quot; și click pe canvas</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="w-72 border-l border-white/10 bg-black/30 overflow-y-auto p-4">
            {selectedRoom && (
              <div>
                <div className="text-xs uppercase tracking-wider text-stone-400 mb-3">Cameră selectată</div>
                <Field label="Nume" value={selectedRoom.name} onChange={v => updateSelected({ name: v })} tid="room-name" />
                <FieldSelect label="Tip" value={selectedRoom.type} options={Object.entries(ROOM_TYPES).map(([k,v]) => [k, v.label])} onChange={v => updateSelected({ type: v })} tid="room-type" />
                <Field label="Suprafață (m²)" type="number" value={selectedRoom.area} onChange={v => updateSelected({ area: parseFloat(v) || 0 })} tid="room-area" />
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Lățime (px)" type="number" value={selectedRoom.w} onChange={v => updateSelected({ w: parseFloat(v) || 60 })} tid="room-w" />
                  <Field label="Înălțime (px)" type="number" value={selectedRoom.h} onChange={v => updateSelected({ h: parseFloat(v) || 60 })} tid="room-h" />
                </div>
                <button onClick={deleteSelected} className="w-full mt-3 py-2 bg-red-500/15 text-red-400 border border-red-500/30 rounded-lg text-xs flex items-center justify-center gap-1" data-testid="delete-room">
                  <Trash2 className="w-3 h-3" />Șterge cameră
                </button>
              </div>
            )}
            {selectedAsset && (
              <div>
                <div className="text-xs uppercase tracking-wider text-stone-400 mb-3">Asset selectat</div>
                <Field label="Nume" value={selectedAsset.name} onChange={v => updateSelected({ name: v })} tid="asset-name" />
                <FieldSelect label="Tip" value={selectedAsset.type} options={Object.entries(ASSET_TYPES).map(([k,v]) => [k, v.label])} onChange={v => updateSelected({ type: v })} tid="asset-type" />
                <FieldSelect label="Stare" value={selectedAsset.condition} options={[["good","Bună"],["fair","Acceptabilă"],["needs_service","Necesită service"],["critical","Critică"]]} onChange={v => updateSelected({ condition: v })} tid="asset-condition" />
                <button onClick={deleteSelected} className="w-full mt-3 py-2 bg-red-500/15 text-red-400 border border-red-500/30 rounded-lg text-xs flex items-center justify-center gap-1" data-testid="delete-asset">
                  <Trash2 className="w-3 h-3" />Șterge asset
                </button>
              </div>
            )}
            {!selectedRoom && !selectedAsset && (
              <div className="space-y-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-stone-400 mb-2">Sumar twin</div>
                  <div className="space-y-1 text-xs">
                    <Summary label="Proprietate" value={twin.property_name || "—"} />
                    <Summary label="Adresă" value={twin.property_address || "—"} />
                    <Summary label="Suprafață" value={twin.property_surface ? `${twin.property_surface} m²` : "—"} />
                    <Summary label="Camere mapate" value={`${rooms.length}`} />
                    <Summary label="Suprafață mapată" value={`${rooms.reduce((s,r) => s + (r.area || 0), 0)} m²`} />
                    <Summary label="Asset-uri" value={`${assets.length}`} />
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wider text-stone-400 mb-2">Asset-uri</div>
                  <div className="space-y-1">
                    {assets.map(a => {
                      const cfg = ASSET_TYPES[a.type] || ASSET_TYPES.other;
                      const Ic = cfg.icon;
                      return (
                        <button key={a.id} onClick={() => setSelected({ kind: "asset", id: a.id })} className="w-full flex items-center justify-between gap-2 p-2 bg-white/5 hover:bg-white/10 rounded-lg text-left">
                          <div className="flex items-center gap-2 min-w-0">
                            <Ic className={`w-3.5 h-3.5 ${cfg.color}`} />
                            <span className="text-xs truncate">{a.name}</span>
                          </div>
                          <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded-full border ${CONDITION_COLORS[a.condition] || CONDITION_COLORS.good}`}>{a.condition}</span>
                        </button>
                      );
                    })}
                    {assets.length === 0 && <div className="text-[11px] text-stone-500 text-center py-2">Niciun asset</div>}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-white/10 p-4 bg-black/30">
          {validateMode ? (
            <div>
              <textarea
                value={validationNotes}
                onChange={e => setValidationNotes(e.target.value)}
                rows={2}
                placeholder={validateMode === "approve" ? "Note opționale pentru client..." : "Explică ce anume necesită revizie..."}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50 resize-none mb-3"
                data-testid="validation-notes"
              />
              <div className="flex gap-2">
                <button onClick={() => { setValidateMode(null); setValidationNotes(""); }} className="flex-1 py-2 bg-white/5 rounded-lg text-xs">Anulează</button>
                <button onClick={() => submitValidation(validateMode)} disabled={saving} className={`flex-1 py-2 rounded-lg text-xs font-medium ${validateMode === "approve" ? "btn-accent" : "bg-amber-500 text-black"}`} data-testid={`confirm-${validateMode}`}>
                  {saving ? "..." : (validateMode === "approve" ? "Confirmă aprobare" : "Trimite înapoi")}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row gap-2">
              <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Închide</button>
              {twin.status !== "approved" && (
                <button onClick={() => setValidateMode("revision")} className="flex-1 py-3 bg-amber-500/15 border border-amber-500/40 text-amber-300 rounded-xl text-sm font-medium flex items-center justify-center gap-2" data-testid="req-revision">
                  <RotateCcw className="w-4 h-4" />Cere revizie
                </button>
              )}
              {twin.status !== "approved" && (
                <button onClick={() => setValidateMode("approve")} className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2" data-testid="approve-twin">
                  <CheckCircle2 className="w-4 h-4" />Aprobă twin
                </button>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

const ToolBtn = ({ active, onClick, icon: Ic, label, tid }) => (
  <button onClick={onClick} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition ${active ? "bg-[#d4ff3a] text-black font-medium" : "bg-white/5 hover:bg-white/10 text-stone-300"}`} data-testid={tid}>
    <Ic className="w-3.5 h-3.5" />{label}
  </button>
);

const Field = ({ label, value, onChange, type = "text", tid }) => (
  <div className="mb-3">
    <label className="text-[10px] uppercase tracking-wider text-stone-500 block mb-1">{label}</label>
    <input
      type={type}
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
      className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-[#d4ff3a]/50"
      data-testid={tid}
    />
  </div>
);

const FieldSelect = ({ label, value, options, onChange, tid }) => (
  <div className="mb-3">
    <label className="text-[10px] uppercase tracking-wider text-stone-500 block mb-1">{label}</label>
    <select value={value} onChange={e => onChange(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-[#d4ff3a]/50" data-testid={tid}>
      {options.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
    </select>
  </div>
);

const Summary = ({ label, value }) => (
  <div className="flex justify-between py-1 border-b border-white/5 last:border-0">
    <span className="text-stone-500">{label}</span>
    <span className="text-stone-300">{value}</span>
  </div>
);

// Export status labels for external use
export { STATUS_LABELS as TWIN_STATUS_LABELS };
