import React, { useEffect, useState } from "react";
import axios from "axios";
import { Flame, ExternalLink, MousePointerClick, Loader2 } from "lucide-react";
import { API } from "../../DashShared";

export const HeatmapTab = ({ period, clarityId }) => {
  const [data, setData] = useState({ pages: [], points: [], total_clicks: 0 });
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/admin/analytics/heatmap?period=${period}&path=${encodeURIComponent(path)}`)
      .then(r => {
        setData(r.data);
        if (!path && r.data.pages.length) setPath(r.data.pages[0].path);
      }).catch(() => {})
      .finally(() => setLoading(false));
  }, [period, path]);

  return (
    <div className="space-y-4" data-testid="ag-heatmap-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">
          <MousePointerClick className="w-3.5 h-3.5 inline mr-1" />
          {data.total_clicks} click-uri colectate în perioadă (coordonate % din pagină)
        </p>
        {clarityId && (
          <a href={`https://clarity.microsoft.com/projects/view/${clarityId}/heatmaps`} target="_blank" rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-violet-600 text-white" data-testid="ag-clarity-link">
            <ExternalLink className="w-3.5 h-3.5" /> Heatmaps complete în MS Clarity
          </a>
        )}
      </div>
      <div className="grid lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 space-y-1 h-fit" data-testid="ag-heatmap-pages">
          <h4 className="text-xs font-bold uppercase text-slate-400 px-2 py-1">Pagini cu click-uri</h4>
          {data.pages.length === 0 && <p className="text-xs text-slate-400 px-2 py-4">Fără click-uri încă — trackerul colectează de la vizitatori.</p>}
          {data.pages.map(p => (
            <button key={p.path} onClick={() => setPath(p.path)} data-testid={`ag-heatmap-page-${p.path.replace(/\//g, "_")}`}
              className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs font-mono text-left ${path === p.path ? "bg-orange-50 dark:bg-orange-500/15 text-orange-600 dark:text-orange-300 font-bold" : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/40"}`}>
              <span className="truncate">{p.path}</span>
              <span className="ml-2 shrink-0 font-sans font-bold">{p.clicks}</span>
            </button>
          ))}
        </div>
        <div className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Flame className="w-4 h-4 text-orange-500" />
            <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">Click-map: <span className="font-mono text-orange-600">{path || "—"}</span></h3>
            <span className="ml-auto text-xs text-slate-400">{data.points.length} click-uri afișate</span>
          </div>
          {loading ? (
            <div className="flex items-center justify-center h-96"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>
          ) : (
            <div className="relative rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/40 overflow-hidden" style={{ height: 620 }} data-testid="ag-heatmap-canvas">
              <div className="absolute top-0 left-0 right-0 h-10 border-b border-slate-200 dark:border-slate-700 bg-white/60 dark:bg-slate-800/60 flex items-center px-3 text-[10px] uppercase font-bold text-slate-300">sus pagină</div>
              <div className="absolute bottom-0 left-0 right-0 h-8 border-t border-slate-200 dark:border-slate-700 bg-white/60 dark:bg-slate-800/60 flex items-center px-3 text-[10px] uppercase font-bold text-slate-300">jos pagină (scroll 100%)</div>
              {data.points.map((p, i) => (
                <div key={i} className="absolute rounded-full pointer-events-none" style={{
                  left: `${p.x}%`, top: `${p.y}%`, width: 38, height: 38, transform: "translate(-50%,-50%)",
                  background: "radial-gradient(circle, rgba(239,68,68,0.5) 0%, rgba(249,115,22,0.28) 45%, transparent 72%)",
                }} />
              ))}
              {data.points.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">Fără click-uri pe această pagină în perioada selectată</div>
              )}
            </div>
          )}
          <p className="text-[11px] text-slate-400 mt-2">Punctele roșii = zone cu click-uri (X = lățime %, Y = poziție scroll %). Pentru heatmap-uri vizuale peste screenshot-ul real al paginii folosește butonul MS Clarity.</p>
        </div>
      </div>
    </div>
  );
};
