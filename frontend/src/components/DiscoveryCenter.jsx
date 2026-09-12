// DiscoveryCenter — CORE-001 · Product Intelligence Engine (tab în /admin/ai-brain).
// Live Product Map + Canonical Product Graph + snapshot-uri istorice + MASTER DISCOVERY REPORT.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Compass, Loader2, RefreshCw, Camera, FileDown, ChevronDown, ChevronUp,
  AlertTriangle, Copy, GitCompare, Layers, TrendingUp, Unplug, FileText, Gauge,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_STYLE = {
  activ: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  experimental: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  duplicat: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  neconectat: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  depreciat: "bg-stone-800 text-stone-400 border-stone-600",
  candidat_reutilizare: "bg-violet-500/10 text-violet-300 border-violet-500/30",
  planificat: "bg-stone-800 text-stone-300 border-stone-600",
};
const STATUS_RO = {
  activ: "Activ", experimental: "Experimental", duplicat: "Duplicat", neconectat: "Neconectat",
  depreciat: "Depreciat", candidat_reutilizare: "Candidat reutilizare", planificat: "Planificat",
};

const scoreColor = (v) => (v >= 80 ? "bg-emerald-400" : v >= 50 ? "bg-[#d4ff3a]" : v >= 25 ? "bg-amber-400" : "bg-rose-400");

const ModuleCard = ({ m }) => {
  const [open, setOpen] = useState(false);
  const sig = m.signals || {};
  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4" data-testid={`dc-module-${m.key}`}>
      <button onClick={() => setOpen(!open)} className="w-full text-left" data-testid={`dc-module-toggle-${m.key}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="text-sm font-bold text-white flex-1">{m.name}</div>
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${STATUS_STYLE[m.status] || STATUS_STYLE.activ}`}>
            {STATUS_RO[m.status] || m.status}
          </span>
          {open ? <ChevronUp className="w-3.5 h-3.5 text-stone-500" /> : <ChevronDown className="w-3.5 h-3.5 text-stone-500" />}
        </div>
        <div className="mt-3 space-y-2">
          <div>
            <div className="flex justify-between text-[10px] text-stone-500 mb-1">
              <span>Completeness</span><span className="font-bold text-stone-300" data-testid={`dc-completeness-${m.key}`}>{m.completeness}%</span>
            </div>
            <div className="h-1.5 bg-stone-800 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${scoreColor(m.completeness)}`} style={{ width: `${m.completeness}%` }} />
            </div>
          </div>
          <div className="flex gap-3 text-[10px] text-stone-500">
            <span>Business Value: <b className="text-stone-300">{m.business_value}</b></span>
            <span>Priority Index: <b className="text-[#d4ff3a]">{m.priority_index}</b></span>
          </div>
        </div>
      </button>
      {open && (
        <div className="mt-3 border-t border-stone-800 pt-3 space-y-2" data-testid={`dc-module-detail-${m.key}`}>
          <p className="text-[11px] text-stone-400">{m.desc}</p>
          <div className="flex flex-wrap gap-2 text-[10px] text-stone-500">
            {sig.backend && <span>Backend: {sig.backend.found}/{sig.backend.declared} fișiere · {sig.backend.endpoints} endpoint-uri</span>}
            {sig.frontend && <span>Frontend: {sig.frontend.found}/{sig.frontend.declared} · {sig.frontend.mounted} montate</span>}
            {sig.data && <span>Date: {sig.data.with_data}/{sig.data.declared} colecții</span>}
            {sig.tests && <span>Teste: {sig.tests.found}</span>}
          </div>
          {sig.frontend?.unmounted?.length > 0 && (
            <div className="text-[10px] text-rose-300">Nemontate: {sig.frontend.unmounted.join(", ")}</div>
          )}
          <div className="space-y-0.5">
            {(m.features || []).map((f, i) => (
              <div key={i} className={`text-[11px] ${f.ok ? "text-emerald-300" : "text-rose-300"}`}>
                {f.ok ? "✓" : "✗"} {f.label}
              </div>
            ))}
          </div>
          {m.reuse?.length > 0 && (
            <div className="bg-violet-500/5 border border-violet-500/20 rounded-xl p-2.5">
              <div className="text-[10px] font-black uppercase text-violet-300 mb-1">Reutilizare (regula 60%)</div>
              {m.reuse.map((r, i) => <div key={i} className="text-[10px] text-stone-400">• {r}</div>)}
            </div>
          )}
          <div className="flex gap-3 text-[10px] text-stone-500">
            <span>BVS: venit {m.bvs_breakdown.revenue}/10 · conversie {m.bvs_breakdown.conversion}/10 · retenție {m.bvs_breakdown.retention}/10 · cost {m.bvs_breakdown.cost}/10</span>
          </div>
        </div>
      )}
    </div>
  );
};

const SnapshotsPanel = ({ onRefresh }) => {
  const [snaps, setSnaps] = useState([]);
  const [sel, setSel] = useState([]);
  const [cmp, setCmp] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    ax.get("/api/admin/ai-brain/product-map/snapshots").then(r => setSnaps(r.data.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const take = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/ai-brain/product-map/snapshot", { label: `Snapshot ${new Date().toLocaleString("ro-RO")}` }); load(); onRefresh?.(); }
    finally { setBusy(false); }
  };
  const toggle = (id) => setSel(s => s.includes(id) ? s.filter(x => x !== id) : [...s.slice(-1), id]);
  const compare = async () => {
    if (sel.length !== 2) return;
    const { data } = await ax.get("/api/admin/ai-brain/product-map/snapshots/compare", { params: { a: sel[0], b: sel[1] } });
    setCmp(data);
  };

  return (
    <div className="space-y-3" data-testid="dc-snapshots">
      <div className="flex items-center gap-2">
        <button onClick={take} disabled={busy}
          className="px-3 py-1.5 text-[11px] rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="dc-snapshot-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Camera className="w-3 h-3" />} Salvează snapshot
        </button>
        {sel.length === 2 && (
          <button onClick={compare} className="px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 text-white font-bold flex items-center gap-1.5 border border-stone-700" data-testid="dc-compare-btn">
            <GitCompare className="w-3 h-3" /> Compară selecția
          </button>
        )}
      </div>
      {snaps.length === 0 && <div className="text-xs text-stone-500">Niciun snapshot încă — salvează prima fotografie a platformei.</div>}
      <div className="space-y-1.5">
        {snaps.map(s => (
          <button key={s.id} onClick={() => toggle(s.id)}
            className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-xl border ${sel.includes(s.id) ? "border-[#d4ff3a]/50 bg-[#d4ff3a]/5" : "border-stone-800 bg-stone-900/40"}`}
            data-testid={`dc-snapshot-${s.id}`}>
            <Camera className="w-3.5 h-3.5 text-stone-500" />
            <div className="flex-1">
              <div className="text-xs font-bold text-white">{s.label}</div>
              <div className="text-[10px] text-stone-500">{new Date(s.created_at).toLocaleString("ro-RO")} · {s.created_by}</div>
            </div>
            {s.totals && <span className="text-[10px] text-stone-400">medie {s.totals.avg_completeness}% · {s.totals.orphans} orfane</span>}
          </button>
        ))}
      </div>
      {cmp && !cmp.error && (
        <div className="border border-stone-800 rounded-xl p-3" data-testid="dc-compare-result">
          <div className="text-[10px] font-black uppercase text-stone-500 mb-2">
            {cmp.a.label} → {cmp.b.label}
          </div>
          {cmp.modules.filter(d => d.delta !== 0).map(d => (
            <div key={d.key} className="text-[11px] text-stone-300 flex justify-between">
              <span>{d.name}</span>
              <span className={d.delta > 0 ? "text-emerald-300" : d.delta < 0 ? "text-rose-300" : "text-stone-500"}>
                {d.a}% → {d.b}% ({d.delta > 0 ? "+" : ""}{d.delta})
              </span>
            </div>
          ))}
          {cmp.modules.every(d => !d.delta) && <div className="text-[11px] text-stone-500">Nicio schimbare de completitudine între snapshot-uri.</div>}
        </div>
      )}
    </div>
  );
};

const ImpactPanel = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    ax.get("/api/admin/prop-benefits/impact-scores").then(r => setData(r.data)).catch(() => {});
  }, []);
  if (!data) return <Loader2 className="w-4 h-4 animate-spin text-stone-500" />;
  return (
    <div className="space-y-2" data-testid="dc-impact">
      <p className="text-[11px] text-stone-500">{data.note}</p>
      {data.items.map(it => (
        <div key={it.key} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3" data-testid={`dc-impact-${it.key}`}>
          <div className="flex justify-between items-center text-xs mb-1.5">
            <span className="font-bold text-white">{it.name}</span>
            <span className="text-stone-400">realizat <b className="text-[#d4ff3a]">{it.realized}</b> / potențial {it.potential} · gap <b className="text-amber-300">{it.gap}</b></span>
          </div>
          <div className="h-1.5 bg-stone-800 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-[#d4ff3a]" style={{ width: `${it.potential ? (it.realized / it.potential) * 100 : 0}%` }} />
          </div>
          <div className="flex gap-3 mt-1.5 text-[10px] text-stone-500">
            <span>activare {it.impact.activation}/10</span><span>retenție {it.impact.retention}/10</span>
            <span>conversie {it.impact.conversion}/10</span><span>recomandări {it.impact.referrals}/10</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export const DiscoveryCenter = () => {
  const [map, setMap] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("module");
  const [report, setReport] = useState(null);
  const [reportBusy, setReportBusy] = useState(false);

  const load = useCallback(async (refresh = false) => {
    setBusy(true);
    try {
      const { data } = await ax.get("/api/admin/ai-brain/product-map", { params: refresh ? { refresh: true } : {} });
      setMap(data);
    } catch { /* noop */ } finally { setBusy(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const downloadReport = async () => {
    setReportBusy(true);
    try {
      const { data } = await ax.get("/api/admin/ai-brain/product-map/report");
      setReport(data);
      const blob = new Blob([data.markdown], { type: "text/markdown" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "CORE001_MASTER_DISCOVERY_REPORT.md";
      a.click();
      URL.revokeObjectURL(a.href);
    } finally { setReportBusy(false); }
  };

  const t = map?.totals;
  const TABS = [
    { id: "module", label: `Module (${map?.modules?.length ?? "—"})`, icon: Layers },
    { id: "duplicate", label: `Duplicate (${map?.duplicates?.length ?? "—"})`, icon: Copy },
    { id: "orfane", label: `Neconectate (${t?.orphans ?? "—"})`, icon: Unplug },
    { id: "roadmap", label: "Roadmap consolidare", icon: TrendingUp },
    { id: "impact", label: "Impact abonamente", icon: Gauge },
    { id: "snapshots", label: "Snapshot-uri", icon: Camera },
  ];

  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="discovery-center">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <Compass className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400 flex-1">
          Discovery Center — CORE-001 · Product Intelligence Engine
        </div>
        <button onClick={() => load(true)} disabled={busy}
          className="px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 text-white font-bold flex items-center gap-1.5 border border-stone-700" data-testid="dc-refresh-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Rescanează
        </button>
        <button onClick={downloadReport} disabled={reportBusy}
          className="px-3 py-1.5 text-[11px] rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="dc-report-btn">
          {reportBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileDown className="w-3 h-3" />} Master Discovery Report
        </button>
      </div>
      <p className="text-[11px] text-stone-500 mb-4">
        Live Product Map — se recalculează din codul real. {map?.rules?.reuse_60}
      </p>

      {t && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4" data-testid="dc-totals">
          <div className="bg-stone-900/60 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500">Completitudine medie</div>
            <div className="text-xl font-bold text-white" data-testid="dc-avg-completeness">{t.avg_completeness}%</div>
          </div>
          <div className="bg-stone-900/60 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500">Module canonice</div>
            <div className="text-xl font-bold text-white">{t.modules}</div>
          </div>
          <div className="bg-stone-900/60 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500">Fișiere neconectate</div>
            <div className="text-xl font-bold text-amber-300">{t.orphans}</div>
          </div>
          <div className="bg-stone-900/60 border border-stone-800 rounded-xl p-3">
            <div className="text-[10px] uppercase text-stone-500">Zone de duplicare</div>
            <div className="text-xl font-bold text-rose-300">{t.duplicates}</div>
          </div>
        </div>
      )}

      <div className="flex gap-1.5 flex-wrap mb-4">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-3 py-1.5 text-[11px] font-bold rounded-xl border flex items-center gap-1.5 ${tab === id ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-800"}`}
            data-testid={`dc-tab-${id}`}>
            <Icon className="w-3 h-3" /> {label}
          </button>
        ))}
      </div>

      {!map && busy && <Loader2 className="w-5 h-5 animate-spin text-stone-500" />}

      {tab === "module" && map && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="dc-modules-grid">
          {map.modules.map(m => <ModuleCard key={m.key} m={m} />)}
        </div>
      )}

      {tab === "duplicate" && map && (
        <div className="space-y-3" data-testid="dc-duplicates">
          {map.duplicates.map(d => (
            <div key={d.id} className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-amber-200 mb-1.5">
                <AlertTriangle className="w-4 h-4" /> {d.title}
              </div>
              <div className="text-[11px] text-stone-400 mb-1">Elemente: {d.elements.join(" · ")}</div>
              <div className="text-[11px] text-stone-400 mb-1">Impact: {d.impact}</div>
              <div className="text-[11px] text-emerald-300">→ {d.recommendation}</div>
            </div>
          ))}
        </div>
      )}

      {tab === "orfane" && map && (
        <div data-testid="dc-orphans">
          <p className="text-[11px] text-stone-500 mb-2">Fișiere din src/ neimportate din App.js/index.js (componentele ui/ shadcn sunt excluse).</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1 max-h-80 overflow-auto">
            {map.orphans.map(o => (
              <div key={o} className="text-[11px] text-stone-400 font-mono bg-stone-900/60 border border-stone-800 rounded-lg px-2 py-1">{o}</div>
            ))}
          </div>
        </div>
      )}

      {tab === "roadmap" && map && (
        <div className="space-y-2" data-testid="dc-roadmap">
          {map.consolidation_roadmap.map((r, i) => (
            <div key={r.id} className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3.5 flex gap-3">
              <div className="text-lg font-black text-[#d4ff3a] w-6 shrink-0">{i + 1}</div>
              <div className="flex-1">
                <div className="text-sm font-bold text-white">{r.title}</div>
                <div className="text-[11px] text-stone-400 mt-0.5">{r.why}</div>
                <div className="flex gap-2 mt-1.5 text-[10px]">
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/25">Impact {r.impact}/5</span>
                  <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/25">Risc {r.risk}/5</span>
                  <span className="px-1.5 py-0.5 rounded bg-stone-800 text-stone-400 border border-stone-700">Efort {r.effort}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "impact" && <ImpactPanel />}

      {tab === "snapshots" && <SnapshotsPanel onRefresh={() => load(true)} />}

      {report && (
        <div className="mt-4 border border-stone-800 rounded-xl p-3 flex items-center gap-2 text-[11px] text-stone-400" data-testid="dc-report-saved">
          <FileText className="w-3.5 h-3.5 text-[#d4ff3a]" />
          Raport generat la {new Date(report.generated_at).toLocaleString("ro-RO")} — descărcat + salvat în docs/CORE001_MASTER_DISCOVERY_REPORT.md
        </div>
      )}
    </div>
  );
};
