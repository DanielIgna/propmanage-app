// RegistryGraph v2 — Dependency Map redesign (EO-002 R1+R6).
// Culori pe tip de relație, fade la selecție, edges clickabile cu evidență, zoom/fullscreen,
// vederi: Ierarhie + Matrice. Doar relații din Enterprise Relationship Registry (Truth Engine).
import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Loader2, X, ChevronRight, ZoomIn, ZoomOut, Crosshair, Maximize2, Grid3X3, GitBranch } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export const STATUS_STYLE = {
  VERIFIED: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
  "PARTIALLY VERIFIED": "bg-amber-500/10 border-amber-500/30 text-amber-300",
  UNKNOWN: "bg-red-500/10 border-red-500/30 text-red-300",
  DEPRECATED: "bg-stone-500/10 border-stone-500/30 text-stone-400",
};
export const TYPE_META = {
  prompt: { label: "Prompturi", color: "#d4ff3a" },
  document: { label: "Documente", color: "#a78bfa" },
  engine: { label: "Engines", color: "#34d399" },
  metric: { label: "Metrici", color: "#fbbf24" },
  automation: { label: "Automations", color: "#f472b6" },
  api: { label: "API", color: "#38bdf8" },
  database: { label: "Database", color: "#fb923c" },
  dashboard: { label: "Dashboards", color: "#e7e5e4" },
};
export const TYPE_ORDER = ["prompt", "document", "engine", "metric", "automation", "api", "database", "dashboard"];

export const edgeColor = (e) => {
  const s = e.verification_status;
  if (s === "UNKNOWN") return "#9ca3af";
  if (s === "DEPRECATED") return "#ef4444";
  const t = e.type || "";
  if (/governs|authorizes|inheritance/.test(t)) return "#a78bfa";
  if (/feeds/.test(t)) return "#38bdf8";
  if (/writes|computes|exposes/.test(t)) return "#fb923c";
  if (/gates|triggers/.test(t)) return "#facc15";
  return "#34d399";
};
const EDGE_LEGEND = [
  ["#a78bfa", "Guvernează / Moștenire"], ["#38bdf8", "Alimentează"], ["#fb923c", "Produce / Expune"],
  ["#facc15", "Gate / Trigger"], ["#34d399", "Folosește"], ["#9ca3af", "Unknown"], ["#ef4444", "Broken"],
];

const EdgeDetail = ({ edge, names, onClose }) => (
  <div data-testid="rg-edge-detail">
    <div className="flex items-start justify-between gap-2">
      <div>
        <div className="text-[10px] uppercase tracking-wide text-stone-500">Relație · {edge.type}</div>
        <div className="font-serif text-base text-white leading-snug mt-0.5" data-testid="rg-edge-title">
          {names[edge.source]?.name || edge.source} <span className="text-[#d4ff3a]">→</span> {names[edge.target]?.name || edge.target}
        </div>
      </div>
      <button onClick={onClose} className="p-1.5 rounded-lg bg-white/5" data-testid="rg-edge-close"><X className="w-3.5 h-3.5" /></button>
    </div>
    <div className="text-xs text-stone-400 mt-2">{edge.description}</div>
    <div className="mt-3 space-y-1.5 text-[11px]">
      <div><span className="text-stone-500">Status:</span> <span className={`px-1.5 py-0.5 rounded-full border text-[9px] ${STATUS_STYLE[edge.verification_status] || STATUS_STYLE.UNKNOWN}`}>{edge.verification_status}</span></div>
      <div><span className="text-stone-500">Evidență:</span> <span className="text-stone-300 font-mono text-[10px]">{edge.evidence}</span></div>
      <div><span className="text-stone-500">Tip evidență:</span> <span className="text-stone-300">{edge.evidence_type}</span></div>
      <div><span className="text-stone-500">Confidence:</span> <span className="text-stone-300">{edge.confidence}</span></div>
      <div><span className="text-stone-500">Verificat:</span> <span className="text-stone-300">{edge.last_verified} · {edge.verified_by}</span></div>
    </div>
  </div>
);

export const RegistryGraph = ({ typeFilter = null, search = "", onOpenDoc = null }) => {
  const [reg, setReg] = useState(null);
  const [regErr, setRegErr] = useState(null);
  const [sel, setSel] = useState(null);
  const [selEdge, setSelEdge] = useState(null);
  const [hoverEdge, setHoverEdge] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [view, setView] = useState("map");
  const wrapRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/api/founder/knowledge/registry`, { withCredentials: true })
      .then(r => setReg(r.data))
      .catch(e => setRegErr(e?.response?.status === 403 ? "Registrul este disponibil exclusiv Fondatorului." : "Registrul nu a putut fi încărcat."));
  }, []);

  const viewData = useMemo(() => {
    if (!reg) return null;
    const q = search.trim().toLowerCase();
    let nodes = reg.nodes;
    if (typeFilter && typeFilter.size) nodes = nodes.filter(n => typeFilter.has(n.type));
    if (q) {
      const direct = new Set(reg.nodes.filter(n => n.name.toLowerCase().includes(q) || (n.ref || "").toLowerCase().includes(q)).map(n => n.id));
      const linked = new Set(direct);
      reg.edges.forEach(e => { if (direct.has(e.source)) linked.add(e.target); if (direct.has(e.target)) linked.add(e.source); });
      nodes = nodes.filter(n => linked.has(n.id));
    }
    const visible = new Set(nodes.map(n => n.id));
    const edges = reg.edges.filter(e => visible.has(e.source) && visible.has(e.target));
    const cols = TYPE_ORDER.filter(t => nodes.some(n => n.type === t));
    const pos = {};
    cols.forEach((t, ci) => {
      nodes.filter(n => n.type === t).forEach((n, ri) => { pos[n.id] = { x: ci * 235 + 10, y: ri * 54 + 46 }; });
    });
    const ys = Object.values(pos).map(p => p.y);
    return { nodes, edges, cols, pos, w: cols.length * 235 + 20, h: (ys.length ? Math.max(...ys) : 0) + 90 };
  }, [reg, typeFilter, search]);

  // R1: highlight selected + părinți/copii direcți + nivelul 2
  const related = useMemo(() => {
    if (!reg || !sel) return null;
    const lvl1 = new Set([sel.id]);
    reg.edges.forEach(e => { if (e.source === sel.id) lvl1.add(e.target); if (e.target === sel.id) lvl1.add(e.source); });
    const lvl2 = new Set(lvl1);
    reg.edges.forEach(e => { if (lvl1.has(e.source)) lvl2.add(e.target); if (lvl1.has(e.target)) lvl2.add(e.source); });
    return { lvl1, lvl2 };
  }, [reg, sel]);

  if (regErr) return <div className="text-sm text-red-300 border border-red-500/20 bg-red-500/5 rounded-xl p-4" data-testid="rg-error">{regErr}</div>;
  if (!reg || !viewData) return <div className="flex items-center gap-2 text-stone-400 text-sm p-6"><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă registrul...</div>;
  const names = Object.fromEntries(reg.nodes.map(n => [n.id, n]));
  const selEdges = sel ? reg.edges.filter(e => e.source === sel.id || e.target === sel.id) : [];
  const edgeRelated = (e) => sel && (e.source === sel.id || e.target === sel.id);
  const center = () => { setSel(null); setSelEdge(null); setZoom(1); if (scrollRef.current) { scrollRef.current.scrollLeft = 0; scrollRef.current.scrollTop = 0; } };
  const fullscreen = () => {
    const el = wrapRef.current;
    if (!document.fullscreenElement) el?.requestFullscreen?.(); else document.exitFullscreen?.();
  };

  const matrixNodes = [...viewData.nodes].sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type));
  const edgeMap = {};
  viewData.edges.forEach(e => { edgeMap[`${e.source}|${e.target}`] = e; });

  return (
    <div ref={wrapRef} className="grid lg:grid-cols-[1fr_320px] gap-4 bg-[#0a0a0b]" data-testid="registry-graph">
      <div className="bg-[#0a0a0b] border border-white/10 rounded-2xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-between flex-wrap gap-2 px-4 pt-3 pb-2 border-b border-white/5">
          <div className="text-[10px] text-stone-500 flex flex-wrap gap-x-3 gap-y-1" data-testid="rg-stats">
            <span>{viewData.nodes.length}/{reg.stats.nodes} noduri · {viewData.edges.length}/{reg.stats.edges} relații</span>
            {EDGE_LEGEND.map(([c, l]) => <span key={l} className="flex items-center gap-1"><span className="w-3 h-[3px] rounded" style={{ background: c }} />{l}</span>)}
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={() => setView("map")} className={`p-1.5 rounded-lg border text-[10px] flex items-center gap-1 ${view === "map" ? "border-[#d4ff3a]/50 text-[#d4ff3a]" : "border-white/10 text-stone-400"}`} title="Ierarhie" data-testid="rg-view-map"><GitBranch className="w-3.5 h-3.5" /> Hartă</button>
            <button onClick={() => setView("matrix")} className={`p-1.5 rounded-lg border text-[10px] flex items-center gap-1 ${view === "matrix" ? "border-[#d4ff3a]/50 text-[#d4ff3a]" : "border-white/10 text-stone-400"}`} title="Dependency Matrix" data-testid="rg-view-matrix"><Grid3X3 className="w-3.5 h-3.5" /> Matrice</button>
            <span className="w-px h-4 bg-white/10 mx-1" />
            <button onClick={() => setZoom(z => Math.min(2, +(z + 0.15).toFixed(2)))} className="p-1.5 rounded-lg border border-white/10 text-stone-400 hover:text-white" data-testid="rg-zoom-in"><ZoomIn className="w-3.5 h-3.5" /></button>
            <button onClick={() => setZoom(z => Math.max(0.4, +(z - 0.15).toFixed(2)))} className="p-1.5 rounded-lg border border-white/10 text-stone-400 hover:text-white" data-testid="rg-zoom-out"><ZoomOut className="w-3.5 h-3.5" /></button>
            <button onClick={center} className="p-1.5 rounded-lg border border-white/10 text-stone-400 hover:text-white" title="Centrează / Reset" data-testid="rg-center"><Crosshair className="w-3.5 h-3.5" /></button>
            <button onClick={fullscreen} className="p-1.5 rounded-lg border border-white/10 text-stone-400 hover:text-white" title="Fullscreen" data-testid="rg-fullscreen"><Maximize2 className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {view === "matrix" && (
          <div className="overflow-auto max-h-[70vh]" data-testid="rg-matrix">
            <table className="border-collapse">
              <thead>
                <tr>
                  <th className="sticky left-0 top-0 bg-[#0a0a0b] z-20 p-1" />
                  {matrixNodes.map(n => (
                    <th key={n.id} className="sticky top-0 bg-[#0a0a0b] z-10 p-0.5">
                      <div className="text-[8px] font-normal whitespace-nowrap" style={{ color: TYPE_META[n.type]?.color, writingMode: "vertical-rl", maxHeight: 110, overflow: "hidden" }}>{n.name}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixNodes.map(row => (
                  <tr key={row.id}>
                    <td className="sticky left-0 bg-[#0a0a0b] z-10 pr-2 text-[9px] whitespace-nowrap max-w-[180px] overflow-hidden text-ellipsis" style={{ color: TYPE_META[row.type]?.color }}>{row.name}</td>
                    {matrixNodes.map(col => {
                      const e = edgeMap[`${row.id}|${col.id}`];
                      return (
                        <td key={col.id} className="p-0">
                          <button onClick={() => e && setSelEdge(e)} disabled={!e}
                            className="w-4 h-4 border border-white/5 block"
                            style={{ background: e ? edgeColor(e) : "transparent", opacity: e ? 0.9 : 1 }}
                            title={e ? `${row.name} → ${col.name} · ${e.type}` : ""} />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {view === "map" && (
          <div ref={scrollRef} className="overflow-auto max-h-[70vh]">
            <div style={{ width: viewData.w * zoom, height: viewData.h * zoom }}>
              <div className="relative origin-top-left" style={{ width: viewData.w, height: viewData.h, transform: `scale(${zoom})` }}>
                <svg className="absolute inset-0" width={viewData.w} height={viewData.h}>
                  <defs>
                    <filter id="rg-glow" x="-50%" y="-50%" width="200%" height="200%">
                      <feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                    </filter>
                  </defs>
                  {viewData.edges.map(e => {
                    const s = viewData.pos[e.source], t = viewData.pos[e.target];
                    if (!s || !t) return null;
                    const isSel = edgeRelated(e) || selEdge?.id === e.id;
                    const isHover = hoverEdge === e.id;
                    const faded = (sel || selEdge) && !isSel;
                    const x1 = s.x + 210, y1 = s.y + 18, x2 = t.x, y2 = t.y + 18;
                    const d = `M ${x1} ${y1} C ${x1 + 60} ${y1}, ${x2 - 60} ${y2}, ${x2} ${y2}`;
                    return (
                      <g key={e.id}>
                        <path d={d} fill="none" stroke={edgeColor(e)}
                          strokeWidth={isSel ? 6 : isHover ? 4 : 2.5}
                          opacity={faded ? 0.08 : isSel ? 1 : 0.55}
                          filter={isSel ? "url(#rg-glow)" : undefined}
                          style={{ transition: "stroke-width 150ms, opacity 200ms" }} />
                        <path d={d} fill="none" stroke="transparent" strokeWidth="12" className="cursor-pointer"
                          onMouseEnter={() => setHoverEdge(e.id)} onMouseLeave={() => setHoverEdge(null)}
                          onClick={() => { setSelEdge(e); setSel(null); }} data-testid={`rg-edge-${e.id}`} />
                      </g>
                    );
                  })}
                </svg>
                {viewData.cols.map((t, ci) => (
                  <div key={t} className="absolute text-[10px] uppercase tracking-widest font-semibold" style={{ left: ci * 235 + 10, top: 14, color: TYPE_META[t].color }}>{TYPE_META[t].label}</div>
                ))}
                {viewData.nodes.map(n => {
                  const p = viewData.pos[n.id];
                  const active = sel?.id === n.id;
                  const inLvl1 = related?.lvl1.has(n.id);
                  const inLvl2 = related?.lvl2.has(n.id);
                  const faded = sel && !inLvl2;
                  return (
                    <button key={n.id} onClick={() => { setSel(active ? null : n); setSelEdge(null); }}
                      className={`absolute w-[210px] text-left px-3 py-2 rounded-xl border text-[11px] leading-tight hover:scale-105 ${active ? "border-[#d4ff3a] bg-[#d4ff3a]/10 text-white" : inLvl1 ? "border-white/40 bg-white/[0.06] text-white" : "border-white/10 bg-white/[0.03] text-stone-300 hover:border-white/30"}`}
                      style={{ left: p.x, top: p.y, opacity: faded ? 0.15 : 1, transform: active ? "scale(1.2)" : undefined, transformOrigin: "left center", transition: "opacity 200ms, transform 150ms", zIndex: active ? 5 : 1 }}
                      data-testid={`rg-node-${n.id.replace(/[:]/g, "-")}`}>
                      <span className="block truncate">{n.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-4 h-fit lg:sticky lg:top-24" data-testid="rg-node-panel">
        {selEdge && <EdgeDetail edge={selEdge} names={names} onClose={() => setSelEdge(null)} />}
        {!selEdge && !sel && <div className="text-xs text-stone-500">Selectează un nod sau o relație (linie/celulă): vezi evidența, confidence-ul și statusul Truth Engine.</div>}
        {!selEdge && sel && (
          <>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[10px] uppercase tracking-wide" style={{ color: TYPE_META[sel.type]?.color }}>{TYPE_META[sel.type]?.label}</div>
                <div className="font-serif text-lg text-white leading-snug" data-testid="rg-node-name">{sel.name}</div>
              </div>
              <button onClick={() => setSel(null)} className="p-1.5 rounded-lg bg-white/5"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="text-xs text-stone-400 mt-1.5">{sel.description}</div>
            <div className="text-[10px] font-mono text-stone-500 mt-1 break-all">{sel.ref}</div>
            {onOpenDoc && (sel.ref?.startsWith("memory/") || sel.ref?.startsWith("docs/")) && (
              <button onClick={() => onOpenDoc(sel.ref)} className="mt-2 text-[11px] text-[#d4ff3a] flex items-center gap-1" data-testid="rg-node-open-doc">Deschide documentul <ChevronRight className="w-3 h-3" /></button>
            )}
            <div className="mt-3 space-y-1.5 max-h-[50vh] overflow-y-auto">
              {selEdges.map(e => {
                const otherId = e.source === sel.id ? e.target : e.source;
                const dir = e.source === sel.id ? "→" : "←";
                return (
                  <button key={e.id} onClick={() => setSelEdge(e)} className="w-full text-left text-[11px] bg-white/[0.02] border border-white/10 rounded-lg px-2.5 py-2 hover:border-[#d4ff3a]/30">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="w-2.5 h-[3px] rounded" style={{ background: edgeColor(e) }} />
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${STATUS_STYLE[e.verification_status] || STATUS_STYLE.UNKNOWN}`}>{e.verification_status}</span>
                      <span className="text-stone-300">{dir} {names[otherId]?.name || otherId}</span>
                    </div>
                    <div className="text-[10px] text-stone-500 mt-0.5">{e.description}</div>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
