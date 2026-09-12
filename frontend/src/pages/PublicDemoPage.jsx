// Dedicated public /demo page — full interactive Three.js viewer.
// Canvas isolated in DemoCanvas (lazy-loaded) to avoid React 19 StrictMode
// double-mount triggering R3F applyProps reconciler bugs.
import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Box, Eye, Sparkles, Layers as LayersIcon, RotateCcw, ArrowLeft, Home, X, Loader2 } from "lucide-react";
import { MountOnce } from "../components/MountOnce";
import DemoCanvas from "../components/DemoCanvas";

const FACE_OPTIONS = [
  { id: "shaded", label: "Realist", icon: Box },
  { id: "xray", label: "X-Ray", icon: Eye },
  { id: "wireframe", label: "Wireframe", icon: LayersIcon },
];

const LAYERS = [
  { layer: "AR_PERETI", color: "#c8b89a", name: "Pereți (Structură)" },
  { layer: "AR_PLANSEE", color: "#9a8a72", name: "Planșee" },
  { layer: "AR_STALPI", color: "#666666", name: "Stâlpi structurali" },
  { layer: "AR_USI", color: "#5a3a20", name: "Uși" },
  { layer: "AR_FERESTRE", color: "#6ab0d4", name: "Ferestre" },
  { layer: "AR_ACOPERIS", color: "#3a2a20", name: "Acoperiș" },
];

export const PublicDemoPage = () => {
  const [faceStyle, setFaceStyle] = useState("shaded");
  const [hiddenLayers, setHiddenLayers] = useState(new Set());
  const [resetKey, setResetKey] = useState(0);
  const [engageToast, setEngageToast] = useState({ show: false, dismissed: false });

  // Engagement signals
  const xrayActivatedAt = useRef(null);
  const layersHiddenAt = useRef(null);

  const toggleLayer = (l) => {
    setHiddenLayers(prev => {
      const next = new Set(prev);
      if (next.has(l)) next.delete(l); else next.add(l);
      if (next.size >= 1 && !layersHiddenAt.current) {
        layersHiddenAt.current = Date.now();
      }
      return next;
    });
  };

  // Track X-Ray activation
  useEffect(() => {
    if (faceStyle === "xray" && !xrayActivatedAt.current) {
      xrayActivatedAt.current = Date.now();
    }
  }, [faceStyle]);

  // Show conversion toast: 30s after page load AND user has explored X-Ray + hidden a layer.
  // This converts curiosity into a lead without being pushy on bored visitors.
  useEffect(() => {
    if (engageToast.show || engageToast.dismissed) return undefined;
    const timer = setInterval(() => {
      const xrayMs = xrayActivatedAt.current ? Date.now() - xrayActivatedAt.current : 0;
      const layersMs = layersHiddenAt.current ? Date.now() - layersHiddenAt.current : 0;
      // Trigger if user explored X-Ray for >5s OR hid layers for >5s (signal of intent)
      if (xrayMs > 5000 || layersMs > 5000) {
        setEngageToast({ show: true, dismissed: false });
        clearInterval(timer);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [engageToast]);

  return (
    <div className="min-h-screen bg-stone-950 text-white flex flex-col overflow-x-hidden" data-testid="public-demo-page">
      {/* Top nav */}
      <header className="border-b border-white/5 bg-stone-950/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-2 text-xs sm:text-sm text-stone-300 hover:text-white shrink-0" data-testid="demo-back-home">
            <ArrowLeft className="w-4 h-4" /> <span className="hidden xs:inline sm:inline">Înapoi la</span> PropManage
          </Link>
          <div className="hidden md:flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[#d4ff3a]">
            <Sparkles className="w-3 h-3" /> Demo Interactiv
          </div>
          <Link
            to="/register"
            className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-1.5 rounded-full bg-[#d4ff3a] text-black text-xs font-semibold hover:bg-[#c5f000] shrink-0 whitespace-nowrap"
            data-testid="demo-cta-register"
          >
            Vreau Digital Twin <span aria-hidden>→</span>
          </Link>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        {/* 3D Canvas — full height on desktop, fixed viewport slice on mobile */}
        <div className="relative bg-black w-full h-[58vh] min-h-[360px] lg:h-auto lg:flex-1 lg:min-h-[calc(100vh-64px)]">
          <MountOnce fallback={
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-stone-500">
              <Loader2 className="w-8 h-8 animate-spin text-[#d4ff3a]" />
              <span className="text-sm">Se încarcă viewer-ul 3D…</span>
            </div>
          }>
            <DemoCanvas faceStyle={faceStyle} hiddenLayers={hiddenLayers} resetKey={resetKey} />
          </MountOnce>

          {/* Floating mode pills */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 bg-stone-900/90 backdrop-blur border border-white/10 rounded-full p-1 max-w-[calc(100vw-1.5rem)]" data-testid="demo-mode-pills">
            {FACE_OPTIONS.map(opt => {
              const Icon = opt.icon;
              const active = faceStyle === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => setFaceStyle(opt.id)}
                  className={`inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-full text-[10px] sm:text-[11px] font-medium transition-colors ${active ? "bg-[#d4ff3a] text-black" : "text-stone-400 hover:text-white"}`}
                  data-testid={`demo-mode-${opt.id}`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  {opt.label}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setResetKey(k => k + 1)}
            className="absolute top-2 right-2 z-10 inline-flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-full bg-stone-900/90 backdrop-blur border border-white/10 text-[10px] sm:text-[11px] text-stone-300 hover:text-white"
            data-testid="demo-reset"
            title="Resetează cameră"
          >
            <RotateCcw className="w-3 h-3" /> <span className="hidden sm:inline">Resetează cameră</span>
          </button>

          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-stone-900/85 backdrop-blur border border-white/10 text-[10px] sm:text-[11px] text-stone-300 text-center max-w-[calc(100vw-1.5rem)]">
            <span className="hidden sm:inline">🖱 Drag pentru rotire · Scroll pentru zoom · Shift+drag pentru pan</span>
            <span className="sm:hidden">👆 Trage pentru rotire · Ciupește pentru zoom</span>
          </div>
        </div>

        {/* Side panel — layers */}
        <aside className="lg:w-80 shrink-0 border-t lg:border-t-0 lg:border-l border-white/5 bg-stone-950 p-4 sm:p-5 space-y-4 lg:overflow-y-auto">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-bold mb-2">Layers · click pentru ascundere</div>
            <ul className="space-y-1.5">
              {LAYERS.map(l => {
                const hidden = hiddenLayers.has(l.layer);
                return (
                  <li key={l.layer}>
                    <button
                      onClick={() => toggleLayer(l.layer)}
                      className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs transition-colors ${hidden ? "bg-white/[0.02] text-stone-500" : "bg-white/5 hover:bg-white/10 text-white"}`}
                      data-testid={`demo-layer-${l.layer}`}
                    >
                      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${hidden ? "ring-1 ring-stone-600" : ""}`} style={{ background: hidden ? "transparent" : l.color }} />
                      <span className={`flex-1 text-left ${hidden ? "line-through" : ""}`}>{l.name}</span>
                      <Eye className={`w-3 h-3 ${hidden ? "opacity-40" : ""}`} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-[#d4ff3a]/15 via-[#d4ff3a]/5 to-transparent border border-[#d4ff3a]/30 p-4">
            <div className="text-[10px] uppercase tracking-[0.16em] text-[#d4ff3a] font-bold mb-1.5">Asta-i doar demo</div>
            <p className="text-xs text-stone-300 leading-relaxed mb-3">
              Vrei un model 3D al locuinței <strong>tale</strong>? Echipa PropManage face scanare LiDAR + modelare arhitecturală în 48h.
            </p>
            <Link
              to="/register"
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full bg-[#d4ff3a] hover:bg-[#c5f000] text-black font-bold text-xs"
              data-testid="demo-side-cta"
            >
              <Home className="w-3.5 h-3.5" />
              Programează vizita LiDAR
            </Link>
          </div>

          <div className="text-[10px] text-stone-600 leading-relaxed">
            🎯 <strong className="text-stone-400">Tips:</strong> Click pe layers ca să le ascunzi · Toggle X-Ray ca să vezi instalațiile prin pereți · Wireframe pentru a vedea doar scheletul.
          </div>
        </aside>
      </div>

      {/* Engagement toast — slides in from bottom-left after user explores
          X-Ray or hides a layer for >5s. Single chance to convert. */}
      {engageToast.show && !engageToast.dismissed && (
        <div
          className="fixed bottom-4 left-4 right-4 sm:left-6 sm:right-auto z-50 max-w-sm bg-stone-900/95 backdrop-blur-xl border border-[#d4ff3a]/40 rounded-2xl shadow-2xl shadow-[#d4ff3a]/10 p-4 animate-in slide-in-from-left-5 fade-in duration-500"
          data-testid="demo-engage-toast"
        >
          <button
            onClick={() => setEngageToast({ show: false, dismissed: true })}
            className="absolute top-2 right-2 w-6 h-6 inline-flex items-center justify-center rounded-full text-stone-500 hover:text-white hover:bg-white/10"
            data-testid="demo-engage-dismiss"
            aria-label="Închide"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          <div className="flex items-start gap-3 pr-4">
            <div className="w-10 h-10 rounded-xl bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5 text-[#d4ff3a]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white leading-snug mb-1">
                Vrei să vezi <span className="text-[#d4ff3a]">casa TA</span> așa?
              </p>
              <p className="text-[11px] text-stone-400 leading-relaxed mb-3">
                48h scanare LiDAR + livrare directă în PropManage. Răspuns în 24h.
              </p>
              <Link
                to="/register"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#d4ff3a] hover:bg-[#c5f000] text-black font-bold text-xs"
                data-testid="demo-engage-cta"
                onClick={() => setEngageToast({ show: false, dismissed: true })}
              >
                <Home className="w-3 h-3" />
                Programează vizita
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PublicDemoPage;
