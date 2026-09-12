// Digital Twin 3D viewer — orchestrator (Phase C + D + E + H).
// Wires the Canvas/scene/tools/pins. Sub-components live in ./viewer/*
import React, { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import axios from "axios";
import {
  Eye, EyeOff, Layers, RotateCcw, Box as BoxIcon, Sparkles, Wand2, Loader2, Palette, ShieldCheck, GitCompare,
} from "lucide-react";
import { API } from "../pages/DashShared";
import { FACE_STYLES, TOOLS, SECTION_AXES } from "./viewer/constants";
import { DemoHouse, ModelWithEvents, ResetCamera, MultiLayerScene } from "./viewer/ViewerScene";
import { MeasureMarkers } from "./viewer/MeasureSection";
import { PinMarker, PinDraftModal, PinThreadModal } from "./viewer/PinSystem";
import DigitalTwinQAPanel from "./DigitalTwinQAPanel";
import DesignConceptStudio from "./DesignConceptStudio";
import ModelValidationPanel from "./ModelValidationPanel";
import ConceptComparison from "./ConceptComparison";
import ViewerErrorBoundary from "./ViewerErrorBoundary";

// Captures the WebGL canvas to a PNG data URL on demand.
const CanvasCapture = ({ captureFnRef }) => {
  const { gl, scene, camera } = useThree();
  useEffect(() => {
    captureFnRef.current = () => {
      try {
        gl.render(scene, camera);
        return gl.domElement.toDataURL("image/png");
      } catch (e) {
        console.error("canvas capture error", e);
        return null;
      }
    };
    return () => { captureFnRef.current = null; };
  }, [gl, scene, camera, captureFnRef]);
  return null;
};

const ViewerOverlay = ({ faceStyle, layersHidden, layersTotal, tool, pinCount }) => (
  <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-stone-900/85 backdrop-blur border border-white/10 text-[11px] text-stone-300 flex items-center gap-4 max-w-[90vw] overflow-x-auto">
    <span>Tool: <strong className="text-emerald-300">{tool}</strong></span>
    <span>Mod: <strong className="text-emerald-300">{faceStyle}</strong></span>
    {layersTotal > 0 && (
      <span>Layers: <strong className="text-stone-200">{layersTotal - layersHidden}/{layersTotal}</strong></span>
    )}
    {pinCount > 0 && <span>📌 <strong className="text-stone-200">{pinCount}</strong></span>}
    <span className="text-stone-500 whitespace-nowrap">Drag · Scroll · Shift+drag</span>
  </div>
);

export const DigitalTwinViewer = ({ projectId, modelUrl, projectName, onClose, onOpenPlans, embedded = false, compactSidebar = false, highlightPinId = null, onPinSelect = null, trimbleEmbedUrl: trimbleEmbedUrlProp = null }) => {
  const [faceStyle, setFaceStyle] = useState("shaded");
  const [hiddenLayers, setHiddenLayers] = useState(new Set());
  const [layers, setLayers] = useState([]);
  const [resetTick, setResetTick] = useState(0);
  const [error] = useState(null);
  const [trimbleEmbedUrl, setTrimbleEmbedUrl] = useState(trimbleEmbedUrlProp);
  // "three" = our viewer (default), "trimble" = SketchUp Connect iframe
  const [viewMode, setViewMode] = useState("three");

  // Phase D — Tool mode + section + measure
  const [tool, setTool] = useState("orbit");
  const [sectionAxis, setSectionAxis] = useState(null);
  const [sectionPos, setSectionPos] = useState(0);
  const [measurePts, setMeasurePts] = useState([]);

  // Phase E — Pins
  const [pins, setPins] = useState([]);
  const [pinDraft, setPinDraft] = useState(null);
  const [pinOpen, setPinOpen] = useState(null);
  // Phase I — Canvas screenshot capture
  const captureFnRef = useRef(null);

  // Q&A on evidence + AI-3D orientative generation
  const [qaOpen, setQaOpen] = useState(false);
  const [designOpen, setDesignOpen] = useState(false);
  const [validationOpen, setValidationOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [isPro, setIsPro] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiMsg, setAiMsg] = useState(null);
  const [viewerResetKey, setViewerResetKey] = useState(0);

  useEffect(() => {
    if (!projectId) return;
    axios.get(`${API}/auth/me`).then((r) => {
      setIsPro(["admin", "operator"].includes(r.data?.role));
    }).catch(() => {});
  }, [projectId]);

  const reloadLayers = () => {
    if (!projectId) return;
    axios.get(`${API}/digital-twin/projects/${projectId}/models`)
      .then(r => setProjectLayers(r.data.models || []))
      .catch(() => {});
  };

  const handleAiGenerate = async () => {
    if (!projectId || aiBusy) return;
    setAiBusy(true); setAiMsg(null);
    try {
      await axios.post(`${API}/digital-twin/projects/${projectId}/ai-generate`);
      setAiMsg({ kind: "ok", text: "Model AI orientativ generat (inferred, neverificat)." });
      reloadLayers();
    } catch (e) {
      setAiMsg({ kind: "err", text: e?.response?.data?.detail || e.message || "Generarea AI a eșuat." });
    } finally {
      setAiBusy(false);
      setTimeout(() => setAiMsg(null), 5000);
    }
  };

  // Hide the dev-only React Error Overlay iframe while viewer is open.
  useEffect(() => {
    const STYLE_ID = "dt-suppress-error-overlay";
    let styleEl = document.getElementById(STYLE_ID);
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ID;
      styleEl.textContent = `
        body > iframe[style*="z-index: 2147483647"],
        iframe#webpack-dev-server-client-overlay { display: none !important; }
      `;
      document.head.appendChild(styleEl);
    }
    return () => { styleEl?.remove(); };
  }, []);

  // Load existing pins for this project
  useEffect(() => {
    if (!projectId) return;
    axios.get(`${API}/digital-twin/projects/${projectId}/pins`)
      .then(r => setPins(r.data.items || []))
      .catch(() => setPins([]));
  }, [projectId]);

  // Fetch Trimble Connect embed URL if not provided via prop
  useEffect(() => {
    if (trimbleEmbedUrlProp || !projectId) return;
    axios.get(`${API}/digital-twin/projects/${projectId}`)
      .then(r => setTrimbleEmbedUrl(r.data.trimble_embed_url || null))
      .catch(() => {});
  }, [projectId, trimbleEmbedUrlProp]);

  // Phase 56 — Multi-layer: fetch all uploaded .glb models for the project so
  // we can render the X-Ray "glass walls" overlay (electric + plumbing + structure).
  const [projectLayers, setProjectLayers] = useState([]);   // backend metadata
  const [layerOverrides, setLayerOverrides] = useState({}); // { model_id: { visible, opacity } }
  useEffect(() => {
    if (!projectId) return;
    axios.get(`${API}/digital-twin/projects/${projectId}/models`)
      .then(r => setProjectLayers(r.data.models || []))
      .catch(() => setProjectLayers([]));
  }, [projectId]);

  // Build the layer list passed to the renderer. Falls back to a single-model
  // setup if the project has only one upload (backwards-compat).
  const renderLayers = useMemo(() => {
    if (!projectLayers.length) return null;
    const backend = process.env.REACT_APP_BACKEND_URL || "";
    return projectLayers.map((m) => {
      const o = layerOverrides[m.id] || {};
      const url = (m.public_path || m.url || "").startsWith("http")
        ? (m.public_path || m.url)
        : `${backend}${m.public_path || m.url || ""}`;
      // Map face style to per-layer opacity:
      //   xray   → force 25% opacity (glass walls)
      //   wireframe → very low opacity to emphasise edges
      //   else → use the layer's natural opacity (structure=opaque, MEP=45%)
      let effectiveOpacity = (o.opacity ?? m.layer_opacity ?? 1.0);
      if (faceStyle === "xray") effectiveOpacity = Math.min(effectiveOpacity, 0.25);
      else if (faceStyle === "wireframe") effectiveOpacity = 0.15;
      else if (faceStyle === "white") {
        // White mode: structure stays solid, MEPs become highlights
        if (m.layer_type === "structure") effectiveOpacity = 1.0;
      }
      const color = faceStyle === "white" ? "#e7e5e4" : (m.layer_color || "#c8b89a");
      return {
        id: m.id,
        url,
        label: m.layer_label || m.filename,
        layer_type: m.layer_type,
        color,
        opacity: effectiveOpacity,
        visible: o.visible !== undefined ? o.visible : (m.layer_visible !== false),
      };
    });
  }, [projectLayers, layerOverrides, faceStyle]);

  const toggleProjectLayer = (modelId) => {
    setLayerOverrides((prev) => {
      const cur = prev[modelId] || {};
      const layerMeta = projectLayers.find(m => m.id === modelId);
      const wasVisible = cur.visible !== undefined ? cur.visible : (layerMeta?.layer_visible !== false);
      return { ...prev, [modelId]: { ...cur, visible: !wasVisible } };
    });
  };

  const setProjectLayerOpacity = (modelId, op) => {
    setLayerOverrides((prev) => ({ ...prev, [modelId]: { ...(prev[modelId] || {}), opacity: op } }));
  };

  const url = modelUrl
    ? (modelUrl.startsWith("http") ? modelUrl : `${process.env.REACT_APP_BACKEND_URL || ""}${modelUrl}`)
    : null;
  const isDefaultModel = !modelUrl;

  const toggleLayer = (key) => {
    setHiddenLayers((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Clipping plane is rebuilt whenever axis or position changes.
  const clippingPlanes = useMemo(() => {
    if (!sectionAxis) return [];
    const axisDef = SECTION_AXES.find((a) => a.id === sectionAxis);
    if (!axisDef) return [];
    return [new THREE.Plane(axisDef.normal.clone(), sectionPos)];
  }, [sectionAxis, sectionPos]);

  const onMeshClick = (e) => {
    const pt = e.point;
    if (tool === "measure") {
      setMeasurePts((prev) => prev.length >= 2 ? [pt.clone()] : [...prev, pt.clone()]);
    } else if (tool === "pin") {
      setPinDraft({
        position: { x: +pt.x.toFixed(3), y: +pt.y.toFixed(3), z: +pt.z.toFixed(3) },
        title: "",
        description: "",
        category: "defect",
        priority: "normal",
      });
    }
  };

  const submitPin = async () => {
    if (!pinDraft || !pinDraft.title.trim() || !projectId) return;
    try {
      const { data } = await axios.post(`${API}/digital-twin/projects/${projectId}/pins`, {
        position: pinDraft.position,
        title: pinDraft.title.trim(),
        description: pinDraft.description.trim(),
        category: pinDraft.category,
        priority: pinDraft.priority,
      });
      setPins((arr) => [data, ...arr]);
      setPinDraft(null);
    } catch (e) {
      alert("Eroare la salvare pin: " + (e?.response?.data?.detail || e.message));
    }
  };

  const deletePin = async (id) => {
    if (!window.confirm("Ștergi acest pin și toate comentariile?")) return;
    try {
      await axios.delete(`${API}/digital-twin/pins/${id}`);
      setPins((arr) => arr.filter(x => x.id !== id));
      setPinOpen(null);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  const updatePinStatus = async (id, status) => {
    try {
      const { data } = await axios.patch(`${API}/digital-twin/pins/${id}`, { status });
      setPins((arr) => arr.map(x => x.id === id ? data : x));
      setPinOpen(data);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  return (
    <div className={(embedded ? "relative w-full h-full" : "fixed inset-0 z-40") + " bg-stone-950 flex"} data-testid="dt-viewer">
      {/* Sidebar */}
      <aside className={(compactSidebar ? "w-56" : "w-72") + " shrink-0 bg-stone-900 border-r border-white/10 flex flex-col"}>
        <div className="px-4 py-4 border-b border-white/10">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold mb-1">Digital Twin</div>
          <h2 className="font-serif text-lg text-white truncate">{projectName || "Demo Hyper-Model"}</h2>
          {isDefaultModel && (
            <div className="mt-1 text-[10px] text-amber-400/80">Model demo public · încarcă modelul tău în setări</div>
          )}
        </div>

        <div className="px-4 py-4 border-b border-white/10">
          <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-semibold mb-2">Unelte</div>
          <div className="grid grid-cols-2 gap-1.5" data-testid="dt-tools">
            {TOOLS.map((t) => {
              const Icon = t.icon;
              const isActive = tool === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => { setTool(t.id); if (t.id !== "measure") setMeasurePts([]); }}
                  className={`px-2 py-2 rounded-lg flex flex-col items-center gap-0.5 transition-colors ${
                    isActive
                      ? "bg-emerald-500/15 ring-1 ring-emerald-400/30 text-emerald-200"
                      : "bg-white/[0.02] hover:bg-white/5 text-stone-300"
                  }`}
                  title={t.desc}
                  data-testid={`dt-tool-${t.id}`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-[10px] font-medium">{t.label}</span>
                </button>
              );
            })}
          </div>

          {tool === "measure" && (
            <div className="mt-3 px-2.5 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200 leading-relaxed" data-testid="dt-measure-hint">
              {measurePts.length === 0 && "Click pe primul punct"}
              {measurePts.length === 1 && "Click pe al doilea punct"}
              {measurePts.length === 2 && (
                <>
                  <strong className="text-amber-100">{measurePts[0].distanceTo(measurePts[1]).toFixed(2)} m</strong>
                  <button onClick={() => setMeasurePts([])} className="ml-2 underline">Reset</button>
                </>
              )}
            </div>
          )}

          {tool === "section" && (
            <div className="mt-3 space-y-2" data-testid="dt-section-controls">
              <div className="flex gap-1">
                {SECTION_AXES.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setSectionAxis(sectionAxis === a.id ? null : a.id)}
                    className={`flex-1 px-2 py-1.5 rounded-lg text-[10px] font-medium ${
                      sectionAxis === a.id
                        ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/30"
                        : "bg-white/[0.03] text-stone-400 hover:bg-white/5"
                    }`}
                    data-testid={`dt-section-axis-${a.id}`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
              {sectionAxis && (
                <>
                  <input
                    type="range"
                    min={-10}
                    max={10}
                    step={0.1}
                    value={sectionPos}
                    onChange={(e) => setSectionPos(parseFloat(e.target.value))}
                    className="w-full accent-emerald-400"
                    data-testid="dt-section-slider"
                  />
                  <div className="text-[10px] text-stone-500 text-center">Poziție: <strong className="text-emerald-300">{sectionPos.toFixed(2)} m</strong></div>
                </>
              )}
            </div>
          )}

          {tool === "pin" && (
            <div className="mt-3 px-2.5 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-200">
              Click pe model → spawn pin colaborativ
            </div>
          )}
        </div>

        <div className="px-4 py-4 border-b border-white/10">
          <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-semibold mb-2">Face Styles</div>
          <div className="space-y-1" data-testid="dt-face-styles">
            {FACE_STYLES.map((fs) => (
              <button
                key={fs.id}
                onClick={() => setFaceStyle(fs.id)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-start gap-2 ${
                  faceStyle === fs.id
                    ? "bg-emerald-500/15 ring-1 ring-emerald-400/30 text-emerald-200"
                    : "hover:bg-white/5 text-stone-300"
                }`}
                data-testid={`dt-face-${fs.id}`}
              >
                <BoxIcon className="w-3.5 h-3.5 mt-0.5 shrink-0 opacity-60" />
                <div className="min-w-0">
                  <div className="text-xs font-medium">{fs.label}</div>
                  <div className="text-[10px] text-stone-500 truncate">{fs.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Phase 56 — Multi-layer Building Systems panel.
            Shows one row per uploaded .glb model (electric / plumbing / structure / ...)
            with visibility toggle + opacity slider. This is the "glass walls X-Ray"
            feature for layered BIM-style models. */}
        {renderLayers && renderLayers.length > 0 && (
          <div className="px-4 py-4 border-b border-white/10" data-testid="dt-systems-panel">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <div className="text-[10px] uppercase tracking-[0.16em] text-stone-400 font-semibold">
                Sisteme ({renderLayers.length})
              </div>
            </div>
            <p className="text-[10px] text-stone-500 mb-2 leading-relaxed">
              Activează simultan structură + electric + apă pentru vedere X-Ray.
            </p>
            <div className="space-y-1.5">
              {renderLayers.map((l) => (
                <div key={l.id} className="rounded-lg bg-white/[0.03] border border-white/5 p-2" data-testid={`dt-system-${l.layer_type || l.id}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <button
                      onClick={() => toggleProjectLayer(l.id)}
                      className={`w-6 h-6 rounded flex items-center justify-center transition ${
                        l.visible ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-stone-500"
                      }`}
                      data-testid={`dt-system-toggle-${l.id}`}
                      title={l.visible ? "Ascunde stratul" : "Afișează stratul"}
                    >
                      {l.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    </button>
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ background: l.color }}
                      title={l.color}
                    />
                    <span className="text-xs text-stone-200 truncate flex-1" title={l.label}>{l.label}</span>
                  </div>
                  {l.visible && (
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-[9px] text-stone-500 uppercase tracking-wider w-12 shrink-0">Opac.</span>
                      <input
                        type="range"
                        min={0.05}
                        max={1.0}
                        step={0.05}
                        value={l.opacity}
                        onChange={(e) => setProjectLayerOpacity(l.id, parseFloat(e.target.value))}
                        className="flex-1 accent-emerald-400 h-1"
                        data-testid={`dt-system-opacity-${l.id}`}
                      />
                      <span className="text-[10px] text-emerald-300 font-mono w-8 text-right">{Math.round(l.opacity * 100)}%</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="px-4 py-4 border-b border-white/10 flex-1 overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-3.5 h-3.5 text-stone-500" />
            <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-semibold">
              Tags / Layers ({layers.length})
            </div>
          </div>
          {layers.length === 0 ? (
            <div className="text-xs text-stone-500 italic px-3 py-2">Nu am detectat layers în model.</div>
          ) : (
            <div className="space-y-1" data-testid="dt-layers">
              {layers.map((layer) => {
                const hidden = hiddenLayers.has(layer);
                return (
                  <button
                    key={layer}
                    onClick={() => toggleLayer(layer)}
                    className={`w-full text-left px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2 text-xs ${
                      hidden ? "text-stone-600" : "text-stone-200 hover:bg-white/5"
                    }`}
                    data-testid={`dt-layer-${layer}`}
                  >
                    {hidden ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5 text-emerald-400" />}
                    <span className="truncate font-mono">{layer}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {projectId && (
          <div className="px-4 py-3 border-t border-white/10 space-y-2" data-testid="dt-ai-actions">
            <button
              onClick={() => setQaOpen(true)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-200 flex items-center justify-center gap-1.5"
              data-testid="dt-open-qa"
            >
              <Sparkles className="w-3.5 h-3.5" /> Întreabă AI (pe dovezi)
            </button>
            <button
              onClick={() => setDesignOpen(true)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-violet-500/15 hover:bg-violet-500/25 text-violet-200 flex items-center justify-center gap-1.5"
              data-testid="dt-open-design"
            >
              <Palette className="w-3.5 h-3.5" /> Concept AI Design
            </button>
            <button
              onClick={() => setCompareOpen(true)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-stone-200 flex items-center justify-center gap-1.5"
              data-testid="dt-open-compare"
            >
              <GitCompare className="w-3.5 h-3.5" /> Compară concepte
            </button>
            <button
              onClick={() => setValidationOpen(true)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-stone-200 flex items-center justify-center gap-1.5"
              data-testid="dt-open-validation"
            >
              <ShieldCheck className="w-3.5 h-3.5" /> Validare modele
            </button>
            <button
              onClick={handleAiGenerate}
              disabled={aiBusy}
              className="w-full px-3 py-2 text-xs rounded-lg border border-violet-500/30 bg-violet-500/10 hover:bg-violet-500/20 text-violet-200 disabled:opacity-50 flex items-center justify-center gap-1.5"
              data-testid="dt-viewer-ai-generate"
              title="Generează un model 3D orientativ (AI, inferred). Nu suprascrie modelele documentate."
            >
              {aiBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
              {aiBusy ? "Se generează…" : "Generează AI 3D (orientativ)"}
            </button>
            {aiMsg && (
              <div className={`text-[11px] rounded-lg p-2 ${aiMsg.kind === "ok" ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20" : "bg-red-500/10 text-red-300 border border-red-500/20"}`} data-testid="dt-ai-msg">
                {aiMsg.text}
              </div>
            )}
          </div>
        )}

        <div className="px-4 py-3 border-t border-white/10 flex gap-2 flex-wrap">
          <button
            onClick={() => setResetTick((t) => t + 1)}
            className="flex-1 px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 flex items-center justify-center gap-1.5"
            data-testid="dt-reset-camera"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset cameră
          </button>
          {onOpenPlans && (
            <button
              onClick={onOpenPlans}
              className="px-3 py-2 text-xs rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-200 flex items-center justify-center gap-1.5"
              data-testid="dt-open-plans"
              title="Planuri 2D (PDF)"
            >
              <Layers className="w-3.5 h-3.5" /> Plane 2D
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="px-3 py-2 text-xs rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-300"
              data-testid="dt-close-viewer"
            >
              Închide
            </button>
          )}
        </div>
      </aside>

      {/* Canvas */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/40 text-red-200 text-sm">
            Eroare la încărcarea modelului: {error}
          </div>
        )}

        {/* View mode toggle: Three.js (intern) vs Trimble Connect (SketchUp nativ) */}
        {trimbleEmbedUrl && (
          <div className="absolute top-3 right-3 z-20 flex items-center gap-1 bg-stone-900/90 backdrop-blur border border-white/10 rounded-full p-1" data-testid="viewer-mode-toggle">
            <button
              onClick={() => setViewMode("three")}
              className={`px-3 py-1 rounded-full text-[11px] font-medium transition-colors ${viewMode === "three" ? "bg-emerald-500 text-white" : "text-stone-400 hover:text-white"}`}
              data-testid="viewer-mode-three"
            >
              ✦ PropManage 3D
            </button>
            <button
              onClick={() => setViewMode("trimble")}
              className={`px-3 py-1 rounded-full text-[11px] font-medium transition-colors ${viewMode === "trimble" ? "bg-emerald-500 text-white" : "text-stone-400 hover:text-white"}`}
              data-testid="viewer-mode-trimble"
            >
              🛠️ SketchUp Native
            </button>
          </div>
        )}

        {viewMode === "trimble" && trimbleEmbedUrl ? (
          <div className="absolute inset-0 bg-black" data-testid="trimble-iframe-wrap">
            <iframe
              src={trimbleEmbedUrl}
              title="Trimble Connect 3D Viewer"
              className="w-full h-full border-0"
              allow="fullscreen; xr-spatial-tracking"
              allowFullScreen
              data-testid="trimble-iframe"
            />
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-stone-900/85 backdrop-blur border border-white/10 text-[11px] text-stone-300">
              🛠️ Viewer SketchUp nativ via <a href={trimbleEmbedUrl} target="_blank" rel="noreferrer" className="text-emerald-400 underline">Trimble Connect</a> — X-Ray, layers, secțiuni native
            </div>
          </div>
        ) : (
        <ViewerErrorBoundary
          resetKey={viewerResetKey}
          onRetry={() => { reloadLayers(); setViewerResetKey((k) => k + 1); }}
        >
        <Canvas
          camera={{ position: [12, 9, 14], fov: 50, near: 0.1, far: 2000 }}
          gl={{ antialias: true, localClippingEnabled: true, preserveDrawingBuffer: true }}
          onCreated={({ gl }) => { gl.localClippingEnabled = true; }}
        >
          <color attach="background" args={["#0a0a0a"]} />
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 15, 8]} intensity={0.9} />
          <hemisphereLight args={[0xddeeff, 0x202020, 0.3]} />
          <Suspense fallback={null}>
            {renderLayers && renderLayers.length > 0 ? (
              <MultiLayerScene
                layers={renderLayers}
                clippingPlanes={clippingPlanes}
                onMeshClick={onMeshClick}
              />
            ) : url ? (
              <ModelWithEvents
                url={url}
                faceStyle={faceStyle}
                hiddenLayers={hiddenLayers}
                onLayersDetected={setLayers}
                clippingPlanes={clippingPlanes}
                onMeshClick={onMeshClick}
              />
            ) : (
              <DemoHouse
                faceStyle={faceStyle}
                hiddenLayers={hiddenLayers}
                onLayersDetected={setLayers}
                clippingPlanes={clippingPlanes}
                onMeshClick={onMeshClick}
              />
            )}
            <MeasureMarkers points={measurePts} />
            {pins.map((p) => (
              <PinMarker
                key={p.id}
                pin={p}
                onOpen={(pin) => { setPinOpen(pin); onPinSelect?.(pin.id); }}
                isHighlighted={highlightPinId === p.id}
              />
            ))}
          </Suspense>
          <gridHelper args={[40, 40, 0x333333, 0x1a1a1a]} position={[0, -0.1, 0]} />
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.08}
            target={[0, 2, 0]}
            enabled={tool === "orbit" || tool === "section"}
          />
          <ResetCamera resetTrigger={resetTick} />
          <CanvasCapture captureFnRef={captureFnRef} />
        </Canvas>
        </ViewerErrorBoundary>
        )}
        {viewMode === "three" && (
          <ViewerOverlay
            faceStyle={faceStyle}
            layersHidden={hiddenLayers.size}
            layersTotal={layers.length}
            tool={tool}
            pinCount={pins.length}
          />
        )}

        {/* Floating "Ask AI" launcher (mobile-friendly) */}
        {projectId && !qaOpen && (
          <button
            onClick={() => setQaOpen(true)}
            className="absolute top-3 left-3 z-20 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/90 hover:bg-emerald-500 text-white text-[11px] font-medium shadow-lg backdrop-blur"
            data-testid="dt-qa-launch"
          >
            <Sparkles className="w-3.5 h-3.5" /> Întreabă AI
          </button>
        )}

        {qaOpen && projectId && (
          <DigitalTwinQAPanel
            projectId={projectId}
            projectName={projectName}
            onClose={() => setQaOpen(false)}
          />
        )}

        {designOpen && projectId && (
          <DesignConceptStudio
            projectId={projectId}
            projectName={projectName}
            onClose={() => setDesignOpen(false)}
            onModelChanged={reloadLayers}
            onOpenCompare={() => { setDesignOpen(false); setCompareOpen(true); }}
          />
        )}

        {compareOpen && projectId && (
          <ConceptComparison
            projectId={projectId}
            projectName={projectName}
            onClose={() => setCompareOpen(false)}
            onChanged={reloadLayers}
          />
        )}

        {validationOpen && projectId && (
          <ModelValidationPanel
            projectId={projectId}
            projectName={projectName}
            isProfessional={isPro}
            onClose={() => setValidationOpen(false)}
            onChanged={reloadLayers}
          />
        )}
      </div>

      {pinDraft && (
        <PinDraftModal
          draft={pinDraft}
          setDraft={setPinDraft}
          onCancel={() => setPinDraft(null)}
          onSubmit={submitPin}
        />
      )}

      {pinOpen && (
        <PinThreadModal
          pin={pinOpen}
          onClose={() => setPinOpen(null)}
          onDelete={() => deletePin(pinOpen.id)}
          onStatusChange={(s) => updatePinStatus(pinOpen.id, s)}
          onRequestScreenshot={() => Promise.resolve(captureFnRef.current ? captureFnRef.current() : null)}
        />
      )}
    </div>
  );
};

export default DigitalTwinViewer;
