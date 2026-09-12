// Architecture Navigator (/admin/architecture) — fluxul complet al platformei (Founder-only).
// EXECUTION ORDER 002: fiecare bloc = fișiere reale; Truth Engine validează fiecare conexiune.
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Map, ShieldAlert, X, Loader2, ArrowDown, FileText, Network } from "lucide-react";
import { RegistryGraph } from "../../components/founder/RegistryGraph";
import { useFounderAccess } from "../../components/founder/useFounderAccess";

const API = process.env.REACT_APP_BACKEND_URL;
const LAYER_COLORS = {
  "Guvernanță": "#d4ff3a", "Inteligență": "#34d399", "Execuție": "#38bdf8",
  "Produs": "#fbbf24", "Client": "#f472b6",
};

const BlockDrawer = ({ block, onClose }) => {
  const navigate = useNavigate();
  return (
    <div className="fixed inset-0 z-[80] bg-black/70 flex justify-end" onClick={onClose} data-testid="arch-block-drawer">
      <div className="w-full max-w-md h-full bg-[#0e0e10] border-l border-white/10 overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="text-[10px] uppercase tracking-widest" style={{ color: LAYER_COLORS[block.layer] }}>{block.layer}</div>
            <div className="font-serif text-xl text-white mt-0.5" data-testid="arch-block-name">{block.name}</div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg bg-white/5 hover:bg-white/10" data-testid="arch-block-close"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-stone-300 mb-1">{block.description}</p>
        <p className="text-xs text-stone-500 mb-4">{block.purpose}</p>
        {[["Fișiere (repo)", block.files], ["Rute", block.routes], ["API", block.api], ["Database", block.database]].map(([label, items]) => (
          <div key={label} className="mb-3">
            <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1">{label}</div>
            {items?.length
              ? items.map((f, i) => <div key={i} className="text-[11px] font-mono text-stone-300 bg-white/[0.03] border border-white/10 rounded-lg px-2.5 py-1.5 mb-1 break-all">{f}</div>)
              : <div className="text-xs text-stone-600">—</div>}
          </div>
        ))}
        <div className="flex flex-wrap gap-2 mt-4">
          {block.kc_doc && (
            <button onClick={() => navigate(`/admin/knowledge-center?doc=${encodeURIComponent(block.kc_doc)}`)}
              className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="arch-open-doc"><FileText className="w-3.5 h-3.5" /> Documentul de guvernanță</button>
          )}
          {block.registry_node && (
            <button onClick={() => navigate(`/admin/explorer`)} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="arch-open-explorer"><Network className="w-3.5 h-3.5" /> Vezi în Explorer</button>
          )}
        </div>
      </div>
    </div>
  );
};

export default function ArchitectureNavigator() {
  const isFounder = useFounderAccess();
  const [data, setData] = useState(null);
  const [sel, setSel] = useState(null);
  const [mode, setMode] = useState("flow");
  useEffect(() => {
    axios.get(`${API}/api/founder/knowledge/architecture`, { withCredentials: true })
      .then(r => setData(r.data)).catch(() => {});
  }, []);

  if (isFounder === false) return (
    <div className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center text-stone-400 gap-3" data-testid="arch-denied">
      <ShieldAlert className="w-8 h-8 text-amber-400" />
      <div className="text-sm">Architecture Navigator este disponibil exclusiv Fondatorului.</div>
      <Link to="/admin" className="text-[#d4ff3a] text-xs underline">← Înapoi la Admin</Link>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
        <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3 mb-1" data-testid="arch-title">
          <Map className="w-8 h-8 text-[#d4ff3a]" /> Architecture Navigator
          <span className="text-[10px] px-2 py-1 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 text-[#d4ff3a] font-sans tracking-normal">FOUNDER ONLY</span>
        </h1>
        <p className="text-sm text-stone-400 mb-6">De la SYSTEM ZERO până la Client — fiecare bloc este clickabil și arată fișierele reale din spatele lui.</p>

        <div className="flex gap-2 mb-6">
          <button onClick={() => setMode("flow")} className={`pm-btn pm-btn-sm ${mode === "flow" ? "pm-btn-success" : "pm-btn-secondary"}`} data-testid="arch-mode-flow">Flux</button>
          <button onClick={() => setMode("deps")} className={`pm-btn pm-btn-sm ${mode === "deps" ? "pm-btn-success" : "pm-btn-secondary"}`} data-testid="arch-mode-deps">Dependențe (registry)</button>
        </div>

        {mode === "deps" && <RegistryGraph onOpenDoc={(ref) => window.location.assign(`/admin/knowledge-center?doc=${encodeURIComponent(ref)}`)} />}

        {mode === "flow" && !data && <div className="flex items-center gap-2 text-stone-400 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă arhitectura...</div>}
        {mode === "flow" && data && (
          <div className="max-w-xl mx-auto" data-testid="arch-flow">
            {data.blocks.map((b, i) => (
              <React.Fragment key={b.id}>
                <button onClick={() => setSel(b)}
                  className="w-full text-left bg-[#0e0e10] border border-white/10 rounded-2xl px-5 py-4 hover:border-[#d4ff3a]/40 transition-colors flex items-center justify-between gap-3"
                  data-testid={`arch-block-${b.id}`}>
                  <div className="min-w-0">
                    <div className="text-[9px] uppercase tracking-widest" style={{ color: LAYER_COLORS[b.layer] }}>{b.layer}</div>
                    <div className="font-serif text-lg text-white truncate">{b.name}</div>
                    <div className="text-[11px] text-stone-500 truncate">{b.description}</div>
                  </div>
                  <div className="text-[10px] text-stone-600 shrink-0">{b.files.length} fișiere</div>
                </button>
                {i < data.blocks.length - 1 && <div className="flex justify-center py-1.5"><ArrowDown className="w-4 h-4 text-stone-600" /></div>}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
      {sel && <BlockDrawer block={sel} onClose={() => setSel(null)} />}
    </div>
  );
}
