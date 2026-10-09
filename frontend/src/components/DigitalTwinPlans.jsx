// Digital Twin — Phase F: 2D Plans Viewer (PDF schedules, sections, elevations).
// Uses pdfjs-dist to render PDFs on a <canvas>. Supports upload, list filter by type,
// page navigation, zoom controls, delete.
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Upload, X, FileText, Trash2, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Layers, Loader2, Download, Box, Columns } from "lucide-react";
import { API } from "../views/DashShared";
import * as pdfjsLib from "pdfjs-dist";
import DigitalTwinViewer from "./DigitalTwinViewer";

// Tell pdf.js where to find the worker.
// We copied build/pdf.worker.min.mjs into /app/frontend/public/, so it's served at /pdf.worker.min.mjs
pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const PLAN_TYPES = [
  { id: "floorplan", label: "Plan etaj" },
  { id: "section", label: "Secțiune" },
  { id: "elevation", label: "Elevație" },
  { id: "detail", label: "Detaliu" },
  { id: "site", label: "Plan teren" },
  { id: "other", label: "Altul" },
];

const TYPE_LABELS = Object.fromEntries(PLAN_TYPES.map((t) => [t.id, t.label]));

// ============== PDF VIEWER (canvas with marker overlay for Phase H) ==============
const PdfCanvas = ({ url, page, scale, onLoaded, markers = [], anchorMode = false, onAnchorClick, onMarkerClick, highlightPinId }) => {
  const canvasRef = useRef(null);
  const [err, setErr] = useState(null);
  const [rendering, setRendering] = useState(false);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [pdfDoc, setPdfDoc] = useState(null);
  const renderTaskRef = useRef(null);

  // Load PDF document (re-loads when url changes)
  useEffect(() => {
    let cancelled = false;
    setErr(null);
    setPdfDoc(null);
    const load = async () => {
      try {
        const loadingTask = pdfjsLib.getDocument({ url, withCredentials: true });
        const pdf = await loadingTask.promise;
        if (cancelled) return;
        setPdfDoc(pdf);
        onLoaded?.(pdf.numPages);
      } catch (e) {
        if (!cancelled) setErr(e.message || "Eroare la încărcarea PDF");
      }
    };
    load();
    return () => { cancelled = true; };
  }, [url, onLoaded]);

  // Render page (re-renders when pdf doc, page or scale changes)
  useEffect(() => {
    let cancelled = false;
    const render = async () => {
      if (!pdfDoc || !canvasRef.current) return;
      try {
        setRendering(true);
        if (renderTaskRef.current) {
          try { renderTaskRef.current.cancel(); } catch { /* ignore */ }
        }
        const pageObj = await pdfDoc.getPage(page);
        if (cancelled) return;
        const viewport = pageObj.getViewport({ scale });
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        setSize({ w: viewport.width, h: viewport.height });
        const task = pageObj.render({ canvasContext: ctx, viewport });
        renderTaskRef.current = task;
        await task.promise;
        if (cancelled) return;
        setRendering(false);
      } catch (e) {
        if (e?.name !== "RenderingCancelledException" && !cancelled) {
          setErr(e.message || "Eroare la randare");
          setRendering(false);
        }
      }
    };
    render();
    return () => {
      cancelled = true;
      if (renderTaskRef.current) {
        try { renderTaskRef.current.cancel(); } catch { /* ignore */ }
      }
    };
  }, [pdfDoc, page, scale]);

  // Click handler for anchor placement
  const handleCanvasClick = (e) => {
    if (!anchorMode || !onAnchorClick || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return;
    onAnchorClick({ x_pct: x, y_pct: y });
  };

  if (err) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-red-300 bg-red-500/5 border border-red-500/20 rounded-xl p-6" data-testid="pdf-error">
        {err}
      </div>
    );
  }

  // Category → marker color
  const categoryColor = (cat) => ({
    structural: "#ef4444", plumbing: "#06b6d4", electrical: "#facc15",
    hvac: "#a78bfa", finish: "#f97316", defect: "#dc2626", general: "#10b981",
  }[cat] || "#10b981");

  return (
    <div className="relative w-full h-full overflow-auto bg-stone-900/50 rounded-xl border border-white/5 p-4 flex items-start justify-center">
      {rendering && (
        <div className="absolute top-3 right-3 z-20 flex items-center gap-2 px-3 py-1.5 rounded-full bg-stone-900/90 border border-white/10 text-xs text-stone-300" data-testid="pdf-loading">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Se randează…
        </div>
      )}
      {anchorMode && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-xs text-amber-200" data-testid="pdf-anchor-hint">
          Click pe plan pentru a ancora pin-ul selectat
        </div>
      )}
      <div className="relative" style={{ width: size.w || "auto", height: size.h || "auto" }}>
        <canvas
          ref={canvasRef}
          className={`shadow-2xl bg-white ${anchorMode ? "cursor-crosshair" : ""}`}
          data-testid="pdf-canvas"
          onClick={handleCanvasClick}
        />
        {/* Marker overlay */}
        {!rendering && size.w > 0 && markers.map((m) => {
          const isHighlighted = highlightPinId && m.pin_id === highlightPinId;
          const color = categoryColor(m.category);
          return (
            <button
              key={m.anchor_id}
              onClick={(e) => { e.stopPropagation(); onMarkerClick?.(m); }}
              className="absolute -translate-x-1/2 -translate-y-full hover:scale-110 transition-transform z-10"
              style={{ left: m.x_pct * size.w, top: m.y_pct * size.h }}
              data-testid={`pdf-marker-${m.pin_id}`}
              title={m.title}
            >
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full shadow-lg text-[10px] font-medium text-white ${isHighlighted ? "ring-2 ring-white ring-offset-1 ring-offset-stone-900 scale-110" : ""}`}
                style={{ background: color }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-white" />
                <span className="max-w-[120px] truncate">{m.title}</span>
              </div>
              {/* Pointer triangle */}
              <div className="w-0 h-0 mx-auto" style={{ borderLeft: "5px solid transparent", borderRight: "5px solid transparent", borderTop: `6px solid ${color}` }} />
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ============== UPLOAD MODAL ==============
const UploadPlanModal = ({ projectId, onClose, onUploaded }) => {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [planType, setPlanType] = useState("floorplan");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [err, setErr] = useState(null);

  const pickFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErr("Doar fișiere .pdf sunt acceptate.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setErr(`Fișier prea mare (${(f.size / (1024 * 1024)).toFixed(1)} MB). Maxim 50 MB.`);
      return;
    }
    setErr(null);
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.pdf$/i, ""));
  };

  const submit = async () => {
    if (!file || !title.trim()) {
      setErr("Selectează un fișier și completează titlul.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const params = new URLSearchParams({
        title: title.trim(),
        description: description.trim(),
        plan_type: planType,
      });
      const xhr = new XMLHttpRequest();
      const result = await new Promise((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try { reject(new Error(JSON.parse(xhr.responseText).detail || xhr.statusText)); }
            catch { reject(new Error(xhr.statusText || "Upload error")); }
          }
        };
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.withCredentials = true;
        xhr.open("POST", `${API}/digital-twin/projects/${projectId}/plans?${params.toString()}`);
        xhr.send(fd);
      });
      onUploaded(result);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-6 w-full max-w-lg space-y-3" data-testid="plan-upload-modal">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-serif text-xl text-white">Încarcă plan 2D</h3>
            <p className="text-xs text-stone-400 mt-0.5">PDF — secțiuni, elevații, planuri etaj, scheme tehnice</p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white" data-testid="plan-upload-close"><X className="w-5 h-5" /></button>
        </div>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); pickFile(e.dataTransfer?.files?.[0]); }}
          className={`border-2 border-dashed rounded-xl p-5 text-center transition-colors ${file ? "border-emerald-500/40 bg-emerald-500/5" : "border-white/15 hover:border-white/30"}`}
          data-testid="plan-upload-dropzone"
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="w-6 h-6 text-emerald-400" />
              <div className="text-left">
                <div className="text-sm text-white truncate max-w-[280px]">{file.name}</div>
                <div className="text-[11px] text-stone-500">{(file.size / (1024 * 1024)).toFixed(1)} MB</div>
              </div>
              <button onClick={() => setFile(null)} className="text-stone-500 hover:text-red-400"><X className="w-4 h-4" /></button>
            </div>
          ) : (
            <>
              <Upload className="w-7 h-7 text-stone-500 mx-auto mb-2" />
              <div className="text-sm text-stone-300 mb-1">Trage PDF-ul aici sau</div>
              <label className="inline-block px-4 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs text-white cursor-pointer">
                alege un fișier
                <input type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => pickFile(e.target.files?.[0])} data-testid="plan-upload-input" />
              </label>
              <p className="text-[10px] text-stone-500 mt-3">Format: .pdf · max 50 MB</p>
            </>
          )}
        </div>

        <div>
          <label className="text-xs text-stone-400 block mb-1">Titlu plan *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex: Plan parter — varianta finală"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="plan-upload-title"
          />
        </div>

        <div>
          <label className="text-xs text-stone-400 block mb-1">Tip plan</label>
          <select
            value={planType}
            onChange={(e) => setPlanType(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="plan-upload-type"
          >
            {PLAN_TYPES.map((t) => <option key={t.id} value={t.id} className="bg-stone-900">{t.label}</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs text-stone-400 block mb-1">Descriere (opțional)</label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="plan-upload-desc"
          />
        </div>

        {busy && (
          <div data-testid="plan-upload-progress">
            <div className="flex justify-between text-xs text-stone-400 mb-1">
              <span>Se încarcă…</span><span>{progress}%</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        <div className="flex gap-2 pt-1">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300">Anulează</button>
          <button onClick={submit} disabled={busy || !file || !title.trim()} className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium" data-testid="plan-upload-submit">
            {busy ? "Se încarcă…" : "Încarcă plan"}
          </button>
        </div>
      </div>
    </div>
  );
};

// ============== ANCHOR PIN PICKER MODAL ==============
const AnchorPinPicker = ({ pins, onPick, onClose }) => {
  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md" data-testid="anchor-pin-picker">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-serif text-lg text-white">Alege pin-ul de ancorat</h3>
            <p className="text-xs text-stone-400 mt-0.5">Selectează un pin 3D existent pentru a-l marca pe acest plan.</p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-1.5 max-h-[60vh] overflow-y-auto" data-testid="anchor-pin-list">
          {pins.length === 0 ? (
            <p className="text-xs text-stone-500 text-center py-6">Niciun pin 3D creat în acest proiect.</p>
          ) : pins.map((p) => (
            <button
              key={p.id}
              onClick={() => onPick(p)}
              className="w-full text-left p-2.5 rounded-lg border border-white/5 hover:bg-white/[0.04] transition-colors"
              data-testid={`anchor-pick-${p.id}`}
            >
              <div className="text-xs font-medium text-white truncate">{p.title}</div>
              <div className="text-[10px] text-stone-500 mt-0.5 flex items-center gap-1.5">
                <span className="px-1.5 py-0.5 rounded bg-white/5">{p.category}</span>
                <span>· {p.priority}</span>
                <span>· {p.status}</span>
                {(p.plan_anchors || []).length > 0 && <span className="text-emerald-400">· {p.plan_anchors.length} ancore</span>}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};


// ============== MAIN PANEL ==============
export default function DigitalTwinPlans({ projectId, projectName, projectModelUrl, onClose, embedded = false }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.2);
  const [showUpload, setShowUpload] = useState(false);
  const [viewMode, setViewMode] = useState("2d");
  // Phase H: pins + anchors
  const [pins, setPins] = useState([]);
  const [anchorMode, setAnchorMode] = useState(false);
  const [pendingAnchor, setPendingAnchor] = useState(null); // { x_pct, y_pct }
  const [highlightPinId, setHighlightPinId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/digital-twin/projects/${projectId}/plans`);
      const items = data.items || [];
      setPlans(items);
      if (!selected && items.length) setSelected(items[0]);
    } catch (e) {
      console.error("plans load error", e);
    } finally {
      setLoading(false);
    }
  };

  const loadPins = async () => {
    try {
      const { data } = await axios.get(`${API}/digital-twin/projects/${projectId}/pins`);
      setPins(data.items || []);
    } catch (e) {
      console.error("pins load error", e);
    }
  };

  useEffect(() => { load(); loadPins(); /* eslint-disable-next-line */ }, [projectId]);

  // Phase H: compute markers for the currently displayed plan + page
  const markers = !selected ? [] : pins.flatMap((pin) =>
    (pin.plan_anchors || [])
      .filter((a) => a.plan_id === selected.id && (a.page || 1) === page)
      .map((a) => ({
        anchor_id: a.id,
        pin_id: pin.id,
        title: pin.title,
        category: pin.category,
        x_pct: a.x_pct,
        y_pct: a.y_pct,
        anchor: a,
        pin,
      }))
  );

  const handleAnchorClick = async ({ x_pct, y_pct }) => {
    // Open pin picker; remember the coordinates
    setPendingAnchor({ x_pct, y_pct });
  };

  const handlePinPick = async (pin) => {
    if (!pendingAnchor || !selected) return;
    try {
      const { data } = await axios.post(`${API}/digital-twin/pins/${pin.id}/anchors`, {
        plan_id: selected.id,
        page,
        x_pct: pendingAnchor.x_pct,
        y_pct: pendingAnchor.y_pct,
      });
      // Update local pin state with new anchors
      setPins((arr) => arr.map((p) => p.id === pin.id ? { ...p, plan_anchors: data.plan_anchors } : p));
      setHighlightPinId(pin.id);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setPendingAnchor(null);
      setAnchorMode(false);
    }
  };

  const handleMarkerClick = (m) => {
    setHighlightPinId(m.pin_id);
    // Auto-switch to split mode to show both 2D and 3D
    if (viewMode === "2d") setViewMode("split");
  };

  const handleRemoveAnchor = async (m) => {
    if (!window.confirm(`Șterge ancora "${m.title}" de pe acest plan?`)) return;
    try {
      const { data } = await axios.delete(`${API}/digital-twin/pins/${m.pin_id}/anchors/${m.anchor_id}`);
      setPins((arr) => arr.map((p) => p.id === m.pin_id ? { ...p, plan_anchors: data.plan_anchors } : p));
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  const filtered = filter === "all" ? plans : plans.filter((p) => p.plan_type === filter);

  const handleSelect = (p) => {
    setSelected(p);
    setPage(1);
    setTotalPages(0);
  };

  const handleDelete = async (p) => {
    if (!window.confirm(`Șterge planul "${p.title}"?`)) return;
    try {
      await axios.delete(`${API}/digital-twin/plans/${p.id}`);
      setPlans((arr) => arr.filter((x) => x.id !== p.id));
      if (selected?.id === p.id) setSelected(null);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  const handleUploaded = (plan) => {
    setPlans((arr) => [plan, ...arr]);
    setShowUpload(false);
    handleSelect(plan);
  };

  const pdfUrl = selected ? `${API}${selected.url.replace(/^\/api/, "")}` : null;

  return (
    <div className={embedded ? "h-full flex flex-col bg-stone-950 text-white" : "fixed inset-0 z-50 bg-stone-950 text-white flex flex-col"} data-testid="dt-plans-panel">
      {/* HEADER */}
      <div className="flex items-center gap-3 px-4 sm:px-6 py-3 border-b border-white/10 bg-stone-950/80 backdrop-blur shrink-0">
        <Layers className="w-5 h-5 text-emerald-400" />
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold">Planuri 2D + 3D · Phase F</div>
          <div className="text-sm text-white truncate">{projectName || "Proiect"}</div>
        </div>
        {/* View mode toggle */}
        <div className="hidden sm:flex items-center gap-0.5 bg-white/5 rounded-full p-0.5" data-testid="dt-view-mode-toggle">
          <button
            onClick={() => setViewMode("2d")}
            className={`px-3 py-1.5 text-[11px] rounded-full transition-colors flex items-center gap-1.5 ${viewMode === "2d" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400 hover:text-white"}`}
            data-testid="dt-mode-2d"
            title="Doar planuri 2D"
          >
            <FileText className="w-3.5 h-3.5" /> 2D
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={`px-3 py-1.5 text-[11px] rounded-full transition-colors flex items-center gap-1.5 ${viewMode === "split" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400 hover:text-white"}`}
            data-testid="dt-mode-split"
            title="Split — 2D + 3D side-by-side"
          >
            <Columns className="w-3.5 h-3.5" /> Split
          </button>
          <button
            onClick={() => setViewMode("3d")}
            className={`px-3 py-1.5 text-[11px] rounded-full transition-colors flex items-center gap-1.5 ${viewMode === "3d" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400 hover:text-white"}`}
            data-testid="dt-mode-3d"
            title="Doar 3D"
          >
            <Box className="w-3.5 h-3.5" /> 3D
          </button>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#d4ff3a] text-black text-xs font-medium hover:bg-[#c5f02e]"
          data-testid="plans-upload-btn"
        >
          <Upload className="w-3.5 h-3.5" /> Încarcă PDF
        </button>
        {onClose && (
          <button onClick={onClose} className="px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-stone-300 text-xs" data-testid="plans-close">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* CONTENT */}
      <div className="flex-1 flex min-h-0">
        {/* SIDEBAR — only visible in 2d & split modes */}
        {viewMode !== "3d" && (
          <aside className="w-60 sm:w-64 border-r border-white/10 bg-stone-950 flex flex-col shrink-0">
            {/* Filter pills */}
            <div className="p-3 border-b border-white/5 flex flex-wrap gap-1.5" data-testid="plans-filter">
              <button
                onClick={() => setFilter("all")}
                className={`px-2.5 py-1 text-[10px] rounded-full border ${filter === "all" ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300" : "border-white/10 text-stone-400 hover:text-white"}`}
                data-testid="plans-filter-all"
              >
                Toate ({plans.length})
              </button>
              {PLAN_TYPES.map((t) => {
                const count = plans.filter((p) => p.plan_type === t.id).length;
                if (!count) return null;
                return (
                  <button
                    key={t.id}
                    onClick={() => setFilter(t.id)}
                    className={`px-2.5 py-1 text-[10px] rounded-full border ${filter === t.id ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300" : "border-white/10 text-stone-400 hover:text-white"}`}
                    data-testid={`plans-filter-${t.id}`}
                  >
                    {t.label} ({count})
                  </button>
                );
              })}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1" data-testid="plans-list">
              {loading ? (
                <div className="text-xs text-stone-500 p-4">Se încarcă…</div>
              ) : filtered.length === 0 ? (
                <div className="text-center p-6">
                  <FileText className="w-8 h-8 text-stone-700 mx-auto mb-2" />
                  <p className="text-xs text-stone-500">Niciun plan încărcat încă.</p>
                  <button
                    onClick={() => setShowUpload(true)}
                    className="mt-3 text-[11px] text-emerald-400 hover:underline"
                    data-testid="plans-empty-upload"
                  >
                    Încarcă primul plan
                  </button>
                </div>
              ) : (
                filtered.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handleSelect(p)}
                    className={`w-full text-left p-2.5 rounded-lg border transition-colors group ${selected?.id === p.id ? "bg-emerald-500/10 border-emerald-500/30" : "border-white/5 hover:bg-white/[0.03]"}`}
                    data-testid={`plan-item-${p.id}`}
                  >
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-white truncate">{p.title}</div>
                        <div className="text-[10px] text-stone-500 mt-0.5 flex items-center gap-1.5">
                          <span className="px-1.5 py-0.5 rounded bg-white/5 text-stone-400">{TYPE_LABELS[p.plan_type] || p.plan_type}</span>
                          <span>{(p.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                        </div>
                        <div className="text-[10px] text-stone-600 truncate mt-0.5">{p.uploaded_by_name}</div>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>
        )}

        {/* PDF VIEWER — only in 2d & split modes */}
        {viewMode !== "3d" && (
          <main className={`${viewMode === "split" ? "w-1/2" : "flex-1"} flex flex-col min-w-0 border-r border-white/10`} data-testid="plans-pdf-pane">
            {selected ? (
              <>
                {/* Viewer toolbar */}
                <div className="flex items-center gap-2 px-3 py-2 border-b border-white/5 bg-stone-950/60 shrink-0 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-white truncate">{selected.title}</div>
                    {selected.description && <div className="text-[10px] text-stone-500 truncate">{selected.description}</div>}
                  </div>
                  <div className="flex items-center gap-0.5 bg-white/5 rounded-full px-1 py-1">
                    <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="px-2 py-1 text-xs text-stone-300 hover:text-white disabled:opacity-30" data-testid="plan-page-prev">
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[11px] text-stone-400 px-1" data-testid="plan-page-info">
                      {page} / {totalPages || "—"}
                    </span>
                    <button onClick={() => setPage((p) => Math.min(totalPages || p, p + 1))} disabled={totalPages > 0 && page >= totalPages} className="px-2 py-1 text-xs text-stone-300 hover:text-white disabled:opacity-30" data-testid="plan-page-next">
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex items-center gap-0.5 bg-white/5 rounded-full px-1 py-1">
                    <button onClick={() => setScale((s) => Math.max(0.4, s - 0.2))} className="px-2 py-1 text-xs text-stone-300 hover:text-white" data-testid="plan-zoom-out">
                      <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[11px] text-stone-400 px-1 w-9 text-center" data-testid="plan-zoom-info">{Math.round(scale * 100)}%</span>
                    <button onClick={() => setScale((s) => Math.min(3, s + 0.2))} className="px-2 py-1 text-xs text-stone-300 hover:text-white" data-testid="plan-zoom-in">
                      <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <button
                    onClick={() => { setAnchorMode((v) => !v); setHighlightPinId(null); }}
                    className={`px-2 py-1 text-[11px] rounded-full flex items-center gap-1 ${anchorMode ? "bg-amber-500/30 text-amber-200 ring-1 ring-amber-400/40" : "text-stone-400 hover:text-white bg-white/5"}`}
                    title={anchorMode ? "Anulează ancorare" : "Ancorează pin 3D pe acest plan"}
                    data-testid="plan-anchor-toggle"
                  >
                    <Layers className="w-3.5 h-3.5" /> {anchorMode ? "Anulează" : "Ancorează pin"}
                  </button>
                  <a href={pdfUrl} target="_blank" rel="noreferrer" className="px-2 py-1 text-[11px] text-stone-400 hover:text-white" title="Descarcă" data-testid="plan-download">
                    <Download className="w-3.5 h-3.5" />
                  </a>
                  <button onClick={() => handleDelete(selected)} className="px-2 py-1 text-[11px] text-red-400 hover:text-red-300" title="Șterge" data-testid={`plan-delete-${selected.id}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                {/* PDF canvas */}
                <div className="flex-1 p-3 min-h-0" data-testid="plan-viewer-area">
                  <PdfCanvas
                    url={pdfUrl}
                    page={page}
                    scale={scale}
                    onLoaded={(n) => setTotalPages(n)}
                    markers={markers}
                    anchorMode={anchorMode}
                    onAnchorClick={handleAnchorClick}
                    onMarkerClick={anchorMode ? handleRemoveAnchor : handleMarkerClick}
                    highlightPinId={highlightPinId}
                  />
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-sm" data-testid="plans-no-selection">
                  <FileText className="w-12 h-12 text-stone-700 mx-auto mb-3" />
                  <h3 className="text-lg text-white mb-1">Niciun plan selectat</h3>
                  <p className="text-sm text-stone-500">Selectează un plan din stânga sau încarcă unul nou.</p>
                </div>
              </div>
            )}
          </main>
        )}

        {/* 3D VIEWER — only in 3d & split modes */}
        {(viewMode === "split" || viewMode === "3d") && (
          <main className={viewMode === "split" ? "w-1/2 flex flex-col min-w-0" : "flex-1 flex flex-col min-w-0"} data-testid="plans-3d-pane">
            <DigitalTwinViewer
              projectId={projectId}
              modelUrl={projectModelUrl}
              projectName={projectName}
              embedded
              compactSidebar={viewMode === "split"}
              highlightPinId={highlightPinId}
              onPinSelect={(pinId) => setHighlightPinId(pinId)}
            />
          </main>
        )}
      </div>

      {pendingAnchor && (
        <AnchorPinPicker
          pins={pins}
          onPick={handlePinPick}
          onClose={() => { setPendingAnchor(null); setAnchorMode(false); }}
        />
      )}

      {showUpload && (
        <UploadPlanModal
          projectId={projectId}
          onClose={() => setShowUpload(false)}
          onUploaded={handleUploaded}
        />
      )}
    </div>
  );
}
