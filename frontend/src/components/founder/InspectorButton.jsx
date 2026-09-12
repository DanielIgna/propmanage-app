// Dashboard Inspector (EXECUTION ORDER 002 · Module 4) — butonul ⓘ + drawer, Founder-only.
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Info, X, Loader2, FileText, Database, Cpu, Clock, Layers } from "lucide-react";
import { useFounderAccess } from "./useFounderAccess";

const API = process.env.REACT_APP_BACKEND_URL;

const Section = ({ title, children }) => (
  <div className="mb-4">
    <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-1.5">{title}</div>
    {children}
  </div>
);

const NodeChip = ({ n, onDoc }) => {
  if (!n) return <span className="text-xs text-stone-600">—</span>;
  const clickable = n.ref && (n.ref.startsWith("memory/") || n.ref.startsWith("docs/"));
  return (
    <button onClick={() => clickable && onDoc(n.ref)} disabled={!clickable}
      className={`text-xs px-2.5 py-1 rounded-lg border border-white/10 bg-white/[0.03] mr-1.5 mb-1.5 ${clickable ? "hover:border-[#d4ff3a]/40 text-stone-200" : "text-stone-400 cursor-default"}`}>
      {n.name}
    </button>
  );
};

const InspectorDrawer = ({ widgetId, onClose }) => {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const navigate = useNavigate();
  useEffect(() => {
    axios.get(`${API}/api/founder/knowledge/inspector/${widgetId}`, { withCredentials: true })
      .then(r => setD(r.data)).catch(e => setErr(e?.response?.data?.detail || "Eroare Inspector"));
  }, [widgetId]);
  const openDoc = (ref) => { onClose(); navigate(`/admin/knowledge-center?doc=${encodeURIComponent(ref)}`); };
  const tc = d?.truth_classification || {};
  return (
    <div className="fixed inset-0 z-[80] bg-black/70 flex justify-end" onClick={onClose} data-testid="inspector-drawer">
      <div className="w-full max-w-md h-full bg-[#0e0e10] border-l border-white/10 overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-[#d4ff3a] flex items-center gap-1.5"><Info className="w-3 h-3" /> Dashboard Inspector</div>
            <div className="font-serif text-xl text-white mt-1" data-testid="inspector-widget-name">{d?.name || widgetId}</div>
            {d && <div className="text-[11px] text-stone-500">{d.dashboard} · Owner: {d.owner}</div>}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg bg-white/5 hover:bg-white/10" data-testid="inspector-close"><X className="w-4 h-4" /></button>
        </div>
        {err && <div className="text-red-300 text-sm">{err}</div>}
        {!d && !err && <div className="flex items-center gap-2 text-stone-400 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...</div>}
        {d && (
          <>
            <Section title="Scop"><p className="text-sm text-stone-300">{d.purpose}</p></Section>
            <Section title="Valoare de business"><p className="text-sm text-stone-300">{d.business_value}</p></Section>
            <Section title="Inputs → Outputs">
              <ul className="text-xs text-stone-400 list-disc ml-4 space-y-0.5">{(d.inputs || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
              <div className="text-stone-600 text-xs my-1">↓</div>
              <ul className="text-xs text-emerald-300/80 list-disc ml-4 space-y-0.5">{(d.outputs || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
            </Section>
            <Section title="Powered by">
              <div className="flex flex-wrap items-center">
                <Cpu className="w-3.5 h-3.5 text-emerald-400 mr-1.5" /><NodeChip n={d.engine} onDoc={openDoc} />
                {d.api && <NodeChip n={d.api} onDoc={openDoc} />}
                {d.prompt && <NodeChip n={d.prompt} onDoc={openDoc} />}
              </div>
            </Section>
            <Section title="Database">
              <div className="flex flex-wrap items-center"><Database className="w-3.5 h-3.5 text-orange-400 mr-1.5" />{d.database.map(n => <NodeChip key={n.id} n={n} onDoc={openDoc} />)}</div>
            </Section>
            <Section title="Actualizare (cron)">
              <div className="text-xs text-stone-300 flex items-start gap-1.5"><Clock className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />{d.cron}</div>
            </Section>
            <Section title="Guvernat de (documente)">
              <div className="flex flex-wrap items-center"><FileText className="w-3.5 h-3.5 text-[#d4ff3a] mr-1.5" />{d.documents.map(n => <NodeChip key={n.id} n={n} onDoc={openDoc} />)}</div>
            </Section>
            <Section title="Dashboards conexe">
              <div className="flex flex-wrap items-center"><Layers className="w-3.5 h-3.5 text-stone-400 mr-1.5" />{d.related_dashboards.map(n => <NodeChip key={n.id} n={n} onDoc={openDoc} />)}</div>
            </Section>
            <Section title="Truth Engine (D161)">
              <div className="text-[11px] space-y-1">
                <div><span className="text-emerald-300">Measured:</span> <span className="text-stone-400">{(tc.measured || []).join(", ") || "—"}</span></div>
                <div><span className="text-amber-300">Estimated:</span> <span className="text-stone-400">{(tc.estimated || []).join(", ") || "—"}</span></div>
                <div><span className="text-red-300">Generated:</span> <span className="text-stone-400">{(tc.generated || []).join(", ") || "—"}</span></div>
                <div className="text-stone-500">Confidence: {d.confidence}</div>
              </div>
            </Section>
            <Section title={`Dependențe dovedite (${d.dependencies.length})`}>
              <div className="space-y-1.5" data-testid="inspector-dependencies">
                {d.dependencies.map(e => (
                  <div key={e.id} className="text-[11px] bg-white/[0.02] border border-white/10 rounded-lg px-2.5 py-1.5">
                    <div className="text-stone-300">{e.source_name} → {e.target_name}</div>
                    <div className="text-[9px] text-stone-600 mt-0.5">🟢 {e.verification_status} · {e.evidence}</div>
                  </div>
                ))}
              </div>
            </Section>
          </>
        )}
      </div>
    </div>
  );
};

export const InspectorButton = ({ widgetId, className = "" }) => {
  const isFounder = useFounderAccess();
  const [open, setOpen] = useState(false);
  if (!isFounder) return null;
  return (
    <>
      <button onClick={(e) => { e.stopPropagation(); setOpen(true); }} title="Dashboard Inspector (Founder)"
        className={`shrink-0 w-6 h-6 rounded-full border border-white/15 bg-white/5 hover:border-[#d4ff3a]/50 hover:text-[#d4ff3a] text-stone-400 flex items-center justify-center ${className}`}
        data-testid={`inspector-btn-${widgetId.replace(/\./g, "-")}`}>
        <Info className="w-3.5 h-3.5" />
      </button>
      {open && <InspectorDrawer widgetId={widgetId} onClose={() => setOpen(false)} />}
    </>
  );
};
