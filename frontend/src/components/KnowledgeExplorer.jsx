// KnowledgeExplorer — AIB-005 · Knowledge Intelligence Engine (tab în /admin/ai-brain).
// Explorare interactivă a grafului: căutare → nod → ego-graf SVG clicabil + dependențe + impact.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Network, Loader2, Search, GitBranch, Zap, MessageCircleQuestion } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const KIND_COLORS = {
  module: "#d4ff3a", route: "#38bdf8", component: "#c084fc", api: "#94a3b8",
  service: "#fb923c", role: "#f472b6", entity: "#34d399", process: "#fbbf24", signal: "#f87171",
};

const EgoGraph = ({ center, edges, onSelect }) => {
  const neighbors = edges.slice(0, 16);
  const cx = 210, cy = 150, R = 110;
  return (
    <svg viewBox="0 0 420 300" className="w-full h-64" data-testid="ego-graph">
      {neighbors.map((e, i) => {
        const ang = (2 * Math.PI * i) / neighbors.length - Math.PI / 2;
        const x = cx + R * Math.cos(ang), y = cy + R * Math.sin(ang);
        const other = e.source === center.id ? e.target : e.source;
        const kind = other.split(":")[0];
        return (
          <g key={i} onClick={() => onSelect(other)} className="cursor-pointer">
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="#3f3f46" strokeWidth={Math.min(1 + e.weight / 3, 3)} />
            <text x={(cx + x) / 2} y={(cy + y) / 2 - 3} fill="#71717a" fontSize="6" textAnchor="middle">{e.rel}</text>
            <circle cx={x} cy={y} r="14" fill="#1c1917" stroke={KIND_COLORS[kind] || "#666"} strokeWidth="1.5" />
            <text x={x} y={y + 24} fill="#a8a29e" fontSize="7" textAnchor="middle">
              {other.split(":").slice(1).join(":").slice(0, 20)}
            </text>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r="20" fill="#1c1917" stroke={KIND_COLORS[center.kind] || "#d4ff3a"} strokeWidth="2.5" />
      <text x={cx} y={cy + 34} fill="#fff" fontSize="8" fontWeight="bold" textAnchor="middle">{center.label.slice(0, 26)}</text>
    </svg>
  );
};

export const KnowledgeExplorer = () => {
  const [ov, setOv] = useState(null);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("module");
  const [items, setItems] = useState([]);
  const [node, setNode] = useState(null);
  const [imp, setImp] = useState(null);
  const [busy, setBusy] = useState(false);
  const [relQ, setRelQ] = useState("De ce există House Health?");
  const [relAns, setRelAns] = useState(null);
  const [relBusy, setRelBusy] = useState(false);

  useEffect(() => { ax.get("/api/admin/ai-brain/graph/overview").then(r => setOv(r.data)).catch(() => {}); }, []);

  const search = useCallback(async () => {
    const { data } = await ax.get("/api/admin/ai-brain/graph/search", { params: { q, kind } });
    setItems(data.items);
  }, [q, kind]);
  useEffect(() => { search().catch(() => {}); }, [search]);

  const open = async (id) => {
    setBusy(true);
    try {
      const [n, i] = await Promise.all([
        ax.get("/api/admin/ai-brain/graph/node", { params: { id } }),
        ax.get("/api/admin/ai-brain/graph/impact", { params: { id } }),
      ]);
      setNode(n.data); setImp(i.data);
    } catch { setNode(null); } finally { setBusy(false); }
  };

  const askRel = async (e) => {
    e.preventDefault(); setRelBusy(true); setRelAns(null);
    try {
      const { data } = await ax.post("/api/ai-brain/explain/relationship", { question: relQ });
      setRelAns(data);
    } catch (ex) { setRelAns({ explanation: String(ex?.response?.data?.detail || ex.message) }); }
    finally { setRelBusy(false); }
  };

  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="knowledge-explorer">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Network className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Knowledge Explorer — graful ecosistemului</div>
        {ov && <span className="text-[10px] text-stone-500" data-testid="graph-stats">{ov.nodes} noduri · {ov.edges} relații · construit {ov.built_at ? new Date(ov.built_at).toLocaleString("ro-RO") : "—"}</span>}
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <select value={kind} onChange={e => setKind(e.target.value)}
          className="bg-stone-800 border border-stone-700 rounded-xl px-2 py-1.5 text-xs text-white" data-testid="graph-kind-select">
          {["module", "route", "component", "api", "service", "entity", "role", "process"].map(k =>
            <option key={k} value={k}>{k} {ov?.by_kind?.[k] ? `(${ov.by_kind[k]})` : ""}</option>)}
        </select>
        <div className="flex-1 min-w-[200px] flex items-center gap-2 bg-stone-800 border border-stone-700 rounded-xl px-3">
          <Search className="w-3.5 h-3.5 text-stone-500" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută nod…"
            className="flex-1 bg-transparent py-1.5 text-xs text-white outline-none" data-testid="graph-search-input" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="max-h-72 overflow-auto space-y-1" data-testid="graph-node-list">
          {items.map(n => (
            <button key={n.id} onClick={() => open(n.id)}
              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] border transition-colors ${node?.node?.id === n.id ? "border-[#d4ff3a]/50 text-white" : "border-transparent text-stone-400 hover:text-white hover:border-stone-700"}`}
              data-testid={`graph-node-${n.id}`}>
              <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: KIND_COLORS[n.kind] }} />
              {n.label}
            </button>
          ))}
        </div>
        <div className="lg:col-span-2">
          {busy && <Loader2 className="w-4 h-4 animate-spin text-stone-500" />}
          {node?.node && !busy && (
            <div data-testid="graph-node-detail">
              <EgoGraph center={node.node} edges={[...node.used_by, ...node.depends_on]} onSelect={open} />
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <div className="text-[10px] font-bold uppercase text-stone-500 flex items-center gap-1 mb-1"><GitBranch className="w-3 h-3" /> Folosit de ({node.degree.in})</div>
                  <div className="max-h-24 overflow-auto space-y-0.5">
                    {node.used_by.slice(0, 10).map((e, i) => (
                      <button key={i} onClick={() => open(e.source)} className="block text-[10px] text-stone-400 hover:text-white truncate w-full text-left">{e.rel} ← {e.source}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase text-stone-500 flex items-center gap-1 mb-1"><Zap className="w-3 h-3" /> Impact dacă îl modifici ({imp?.total_affected ?? 0})</div>
                  <div className="text-[10px] text-stone-400" data-testid="graph-impact">
                    {imp && Object.entries(imp.by_kind).map(([k, v]) => <div key={k}>{k}: {v.length}{imp.by_kind[k].length >= 20 ? "+" : ""}</div>)}
                  </div>
                </div>
              </div>
            </div>
          )}
          {!node && !busy && <div className="text-xs text-stone-500 p-6 text-center">Alege un nod din listă ca să-i vezi ego-graful, dependențele și impactul.</div>}
        </div>
      </div>

      <form onSubmit={askRel} className="mt-4 flex gap-2">
        <div className="flex-1 flex items-center gap-2 bg-stone-800 border border-stone-700 rounded-xl px-3">
          <MessageCircleQuestion className="w-3.5 h-3.5 text-stone-500" />
          <input value={relQ} onChange={e => setRelQ(e.target.value)} placeholder="Întreabă despre relații (ex: De ce există House Health?)"
            className="flex-1 bg-transparent py-2 text-xs text-white outline-none" data-testid="rel-question-input" />
        </div>
        <button disabled={relBusy} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold" data-testid="rel-ask-btn">
          {relBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Explică relația"}
        </button>
      </form>
      {relAns && (
        <div className="mt-3 text-[12px] leading-relaxed text-stone-200 whitespace-pre-wrap bg-stone-900/60 border border-stone-800 rounded-xl p-3 max-h-64 overflow-auto" data-testid="rel-answer">
          {String(relAns.explanation).replace(/##\s?/g, "▸ ").replace(/\*\*/g, "")}
        </div>
      )}
    </div>
  );
};
