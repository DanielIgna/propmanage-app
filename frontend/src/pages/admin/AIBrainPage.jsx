// AIBrainPage — dashboard-ul subsistemului AI Brain (AIB-001, Sprint 1: Discovery).
// Route: /admin/ai-brain · API: /api/admin/ai-brain/{status,discover,registry/{kind}}
import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { KnowledgeExplorer } from "../../components/KnowledgeExplorer";
import { ProcessExplorer } from "../../components/ProcessExplorer";
import { DecisionExplorer } from "../../components/DecisionExplorer";
import { AdaptiveExplorer } from "../../components/AdaptiveExplorer";
import { CollaborationExplorer } from "../../components/CollaborationExplorer";
import { ProductionReadiness } from "../../components/ProductionReadiness";
import { DiscoveryCenter } from "../../components/DiscoveryCenter";
import {
  Brain, Loader2, Play, ChevronLeft, Layers, Route as RouteIcon, FileCode,
  Puzzle, Server, Network, Users, Menu as MenuIcon, ScanEye,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const KIND_META = [
  { kind: "modules", label: "Module", icon: Layers },
  { kind: "routes", label: "Rute frontend", icon: RouteIcon },
  { kind: "pages", label: "Pagini", icon: FileCode },
  { kind: "components", label: "Componente", icon: Puzzle },
  { kind: "apis", label: "API-uri", icon: Network },
  { kind: "services", label: "Servicii backend", icon: Server },
  { kind: "roles", label: "Roluri", icon: Users },
  { kind: "menus", label: "Meniuri", icon: MenuIcon },
];

const CtxCard = ({ label, children }) => (
  <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3.5">
    <div className="text-[10px] font-bold uppercase tracking-wider text-stone-500 mb-1.5">{label}</div>
    {children}
  </div>
);

const ContextInspector = () => {
  const [email, setEmail] = useState("client@propmanage.io");
  const [path, setPath] = useState("/client");
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const inspect = async (e) => {
    e?.preventDefault();
    setBusy(true); setErr(null);
    try {
      const { data: d } = await ax.get(`/api/admin/ai-brain/context/inspect`, { params: { email, path } });
      setData(d);
    } catch (ex) {
      setErr(ex?.response?.data?.detail || ex.message); setData(null);
    } finally { setBusy(false); }
  };

  const c = data?.context;
  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4" data-testid="context-inspector">
      <div className="flex items-center gap-2 mb-3">
        <ScanEye className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Context Inspector — AIB-002 · Context Awareness Engine</div>
      </div>
      <form onSubmit={inspect} className="flex flex-wrap gap-2 mb-4">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email utilizator"
          className="flex-1 min-w-[220px] bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="ctx-email-input" />
        <input value={path} onChange={e => setPath(e.target.value)} placeholder="Rută (ex: /client)"
          className="flex-1 min-w-[160px] bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="ctx-path-input" />
        <button disabled={busy} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="ctx-inspect-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ScanEye className="w-3.5 h-3.5" />} Inspectează
        </button>
      </form>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="ctx-error">{err}</div>}
      {c && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3" data-testid="ctx-result">
          <CtxCard label="Utilizator analizat">
            <div className="text-sm font-bold text-white" data-testid="ctx-user-name">{c.user.name}</div>
            <div className="text-xs text-stone-400">{c.user.email}</div>
            <div className="flex gap-1.5 mt-1.5 flex-wrap">
              <span className="text-[10px] font-black uppercase px-1.5 py-0.5 rounded bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/30" data-testid="ctx-user-role">{c.user.role}</span>
              {c.user.tier && <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-stone-800 text-stone-400">{c.user.tier}</span>}
            </div>
          </CtxCard>
          <CtxCard label="Locație · modul activ">
            <div className="text-sm font-bold text-white" data-testid="ctx-module">{c.location.module}</div>
            <div className="text-xs text-stone-400">{c.location.path || "—"}</div>
            <div className="text-[11px] text-stone-500 mt-1">
              {c.location.known_route ? `Componentă: ${c.location.route?.component}` : "Rută necunoscută în App.js"}
            </div>
          </CtxCard>
          <CtxCard label="Entitate selectată">
            {c.entity ? (
              <>
                <div className="text-sm font-bold text-white" data-testid="ctx-entity">{c.entity.label}</div>
                <div className="text-[11px] text-stone-500">{c.entity.type} · {c.entity.id}</div>
              </>
            ) : c.active_property ? (
              <>
                <div className="text-sm font-bold text-white">{c.active_property.label}</div>
                <div className="text-[11px] text-stone-500">proprietate activă (implicită)</div>
              </>
            ) : <div className="text-xs text-stone-500">—</div>}
          </CtxCard>
          <CtxCard label="Permisiuni efective">
            <div className="text-sm font-bold text-white" data-testid="ctx-permissions">{c.permissions.accessible_endpoints} / {c.permissions.total_endpoints} endpoint-uri</div>
            <div className="text-[11px] text-stone-500 mt-1">{c.permissions.effective_guards.join(" · ")}</div>
          </CtxCard>
          <CtxCard label={`Acțiuni disponibile în modul (${c.available_actions.length})`}>
            <div className="max-h-28 overflow-auto space-y-0.5" data-testid="ctx-actions">
              {c.available_actions.slice(0, 10).map((a, i) => (
                <div key={i} className="text-[11px] text-stone-400"><span className="text-[#d4ff3a] font-mono">{a.method}</span> {a.path}</div>
              ))}
            </div>
          </CtxCard>
          <CtxCard label="Istoric navigare">
            <div className="max-h-28 overflow-auto space-y-0.5" data-testid="ctx-navigation">
              {(data.navigation.events || []).length === 0 && <div className="text-xs text-stone-500">Nicio navigare înregistrată încă.</div>}
              {(data.navigation.events || []).slice(0, 8).map((e, i) => (
                <div key={i} className="text-[11px] text-stone-400 flex gap-2">
                  <span className="text-stone-600">{new Date(e.ts).toLocaleTimeString("ro-RO")}</span>
                  <span className="flex-1 truncate">{e.path}</span>
                  {e.duration_ms ? <span className="text-stone-600">{Math.round(e.duration_ms / 1000)}s</span> : null}
                </div>
              ))}
            </div>
          </CtxCard>
          <CtxCard label={`Conversații AI (${(data.conversations || []).length})`}>
            <div className="max-h-28 overflow-auto space-y-1" data-testid="ctx-conversations">
              {(data.conversations || []).length === 0 && <div className="text-xs text-stone-500">Nicio conversație încă.</div>}
              {(data.conversations || []).map((s, i) => (
                <div key={i} className="text-[11px] text-stone-400">
                  <span className="text-stone-500">{s.session_id?.slice(0, 8)}…</span> {s.context?.topic || "—"}
                </div>
              ))}
            </div>
          </CtxCard>
          <CtxCard label="Workflow">
            <div className="text-[11px] text-stone-400" data-testid="ctx-workflow">
              {(c.workflow.trail || []).length ? c.workflow.trail.join(" → ") : "—"}
            </div>
          </CtxCard>
        </div>
      )}
    </div>
  );
};

export default function AIBrainPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(() => {
    ax.get("/api/admin/ai-brain/status").then(r => setStatus(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const discover = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/ai-brain/discover"); load(); if (selected) openKind(selected); } finally { setBusy(false); }
  };

  const openKind = async (kind) => {
    setSelected(kind); setDetailLoading(true);
    try {
      const { data } = await ax.get(`/api/admin/ai-brain/registry/${kind}?limit=100`);
      setDetail(data);
    } catch { setDetail(null); } finally { setDetailLoading(false); }
  };

  const g = status?.guardians || {};
  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8" data-testid="ai-brain-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-2">
          <button onClick={() => navigate("/admin")} className="text-stone-400 hover:text-white" data-testid="ai-brain-back-btn">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <Brain className="w-6 h-6 text-[#d4ff3a]" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">AI Brain</h1>
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${status?.status === "active" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : "bg-stone-800 text-stone-400 border-stone-700"}`}
            data-testid="ai-brain-status-badge">
            {status?.status === "active" ? "Activ" : "Nu a rulat încă"} · {status?.version}
          </span>
          <div className="flex-1" />
          {status?.last_run && (
            <span className="text-[11px] text-stone-500" data-testid="ai-brain-last-run">
              Ultima analiză: {new Date(status.last_run.ts).toLocaleString("ro-RO")} · {status.last_run.duration_ms}ms · {status.last_run.trigger}
            </span>
          )}
          <button onClick={discover} disabled={busy}
            className="px-4 py-1.5 text-xs rounded-lg bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5"
            data-testid="ai-brain-discover-btn">
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Analizează aplicația
          </button>
        </div>
        <p className="text-xs text-stone-500 mb-6">Sprint 1 · Discovery Engine + Knowledge Registry — AI Brain cartografiază automat structura reală a platformei.</p>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8" data-testid="ai-brain-counts">
          {KIND_META.map(({ kind, label, icon: Icon }) => (
            <button key={kind} onClick={() => openKind(kind)}
              className={`text-left bg-stone-900/40 border rounded-2xl p-4 transition-colors ${selected === kind ? "border-[#d4ff3a]/50" : "border-stone-800 hover:border-stone-700"}`}
              data-testid={`ai-brain-card-${kind}`}>
              <div className="flex items-center gap-2 text-xs text-stone-400 uppercase tracking-wider">
                <Icon className="w-3.5 h-3.5 text-[#d4ff3a]" /> {label}
              </div>
              <div className="text-2xl font-bold text-white mt-1.5">{status?.registry?.[kind] ?? "—"}</div>
            </button>
          ))}
        </div>

        {(g.platform_score != null) && (
          <div className="flex items-center gap-2 flex-wrap mb-8" data-testid="ai-brain-guardians">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Guardian Kernel:</span>
            <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/30">Arhitectură {g.architecture_score}/100</span>
            <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">Produs {g.product_score}/100</span>
            <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-stone-800 text-stone-300 border border-stone-700">Platformă {g.platform_score}/100</span>
          </div>
        )}

        {selected && (
          <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mb-8" data-testid="ai-brain-detail">
            <div className="text-xs font-bold uppercase tracking-wider text-stone-400 mb-3">
              Registry · {KIND_META.find(k => k.kind === selected)?.label} {detail && `(${detail.count} total, primele ${Array.isArray(detail.data) ? detail.data.length : "—"})`}
            </div>
            {detailLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-stone-500" />
            ) : (
              <pre className="text-[11px] text-stone-300 overflow-auto max-h-96 whitespace-pre-wrap" data-testid="ai-brain-detail-json">
                {JSON.stringify(detail?.data, null, 1)}
              </pre>
            )}
          </div>
        )}

        <DiscoveryCenter />
        <ContextInspector />
        <KnowledgeExplorer />
        <ProcessExplorer />
        <DecisionExplorer />
        <AdaptiveExplorer />
        <CollaborationExplorer />
        <ProductionReadiness />
      </div>
    </div>
  );
}
