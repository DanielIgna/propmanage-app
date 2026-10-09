import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { toast } from "sonner";
import {
  Map, Filter, X, ExternalLink, CheckCircle2, AlertTriangle, HelpCircle, Ban,
  Zap, ShieldCheck, Users, ChevronRight, Grid3x3, List, ArrowLeftRight,
} from "lucide-react";
import { KpiCard, TabBar, DSButton, DSBadge, EmptyState, DSSkeleton } from "../../design-system";

// Culori canonice per status (aliniat cu FUNCTION_MAP.md convenții)
const HEALTH_COLOR = {
  GREEN: "bg-emerald-500 text-white",
  YELLOW: "bg-amber-400 text-slate-900",
  ORANGE: "bg-orange-500 text-white",
  RED: "bg-rose-500 text-white",
  GREY: "bg-slate-400 text-white",
  UNKNOWN: "bg-slate-300 text-slate-700",
};
const VERIFICATION_COLOR = {
  VERIFIED: "bg-emerald-100 text-emerald-800 border-emerald-300",
  PARTIAL: "bg-amber-100 text-amber-800 border-amber-300",
  UNVERIFIED: "bg-orange-100 text-orange-800 border-orange-300",
  FAILED: "bg-rose-100 text-rose-800 border-rose-300",
  UNKNOWN: "bg-slate-100 text-slate-700 border-slate-300",
};
const CATEGORY_COLOR = {
  BUSINESS: "bg-blue-100 text-blue-800",
  INFRA: "bg-violet-100 text-violet-800",
  SHARED: "bg-teal-100 text-teal-800",
  UNKNOWN: "bg-slate-100 text-slate-700",
};
const RISK_COLOR = {
  LOW: "text-emerald-600",
  MEDIUM: "text-amber-600",
  HIGH: "text-orange-600",
  CRITICAL: "text-rose-600",
  UNKNOWN: "text-slate-400",
};

// Extrage canonic (înainte de paranteze) pentru badge display
const canon = (v) => (v || "UNKNOWN").split("(")[0].trim().toUpperCase();

const MatrixCell = ({ value }) => {
  const map = {
    "✓": { bg: "bg-emerald-500", text: "text-white", label: "Connected" },
    "~": { bg: "bg-amber-400", text: "text-slate-900", label: "Partial" },
    "?": { bg: "bg-slate-300", text: "text-slate-700", label: "Unknown" },
    "✗": { bg: "bg-rose-500", text: "text-white", label: "Broken" },
  };
  const cfg = map[value] || map["?"];
  return (
    <span title={cfg.label} data-testid={`matrix-cell-${cfg.label.toLowerCase()}`}
      className={`inline-flex items-center justify-center w-7 h-7 rounded-md font-bold text-xs ${cfg.bg} ${cfg.text}`}>
      {value || "?"}
    </span>
  );
};

export default function FunctionMap() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("overview");
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ category: "", lifecycle: "", verification: "", health: "", risk: "" });

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/founder/knowledge/function-map`);
      setData(data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Eroare la încărcare Function Map"); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!data?.functions) return [];
    return data.functions.filter(fn => {
      for (const [k, v] of Object.entries(filters)) {
        if (!v) continue;
        if (canon(fn[k]) !== v.toUpperCase()) return false;
      }
      return true;
    });
  }, [data, filters]);

  const s = data?.summary || {};

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "function_map.json"; a.click();
    URL.revokeObjectURL(url);
  };

  const exportCsv = () => {
    if (!data?.functions?.length) return;
    const cols = ["id", "name", "category", "lifecycle", "verification", "health", "risk", "autonomy", "human_decision", "production_verified", "next_action"];
    const rows = [cols.join(",")].concat(data.functions.map(fn => cols.map(c => {
      const v = (fn[c] || "").replace(/"/g, '""').replace(/[\r\n]+/g, " ");
      return `"${v}"`;
    }).join(",")));
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "function_map.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return (
    <AdminLayoutMetronic>
      <div className="p-6 space-y-4"><DSSkeleton blocks={6} /></div>
    </AdminLayoutMetronic>
  );

  return (
    <AdminLayoutMetronic>
      <div className="p-6 space-y-6" data-testid="function-map-page">
        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-black text-slate-900 dark:text-white flex items-center gap-2">
              <Map className="w-6 h-6 text-violet-500" /> Master Function Map
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Sursa unică pentru toate funcționalitățile PropManage · alimentat din{" "}
              <code className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">memory/registries/FUNCTION_MAP.md</code>
            </p>
          </div>
          <div className="flex gap-2">
            <DSButton variant="secondary" onClick={exportCsv} data-testid="fm-export-csv">Export CSV</DSButton>
            <DSButton variant="secondary" onClick={exportJson} data-testid="fm-export-json">Export JSON</DSButton>
            <DSButton variant="ghost" onClick={load} data-testid="fm-refresh">Refresh</DSButton>
          </div>
        </div>

        {/* KPI Overview */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard icon={Map} label="Total funcții" value={s.total || 0} accent="info" />
          <KpiCard icon={CheckCircle2} label="Verified" value={s.verification?.VERIFIED || 0} accent="success" />
          <KpiCard icon={AlertTriangle} label="Partial" value={s.verification?.PARTIAL || 0} accent="warning" />
          <KpiCard icon={HelpCircle} label="Unknown" value={s.verification?.UNKNOWN || 0} accent="ai" />
          <KpiCard icon={Zap} label="LIVE" value={s.lifecycle?.LIVE || 0} accent="success" />
          <KpiCard icon={ShieldCheck} label="Health Green" value={s.health?.GREEN || 0} accent="success" />
        </div>

        {/* Distribution bands */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[
            ["Categorie", s.category, CATEGORY_COLOR],
            ["Lifecycle", s.lifecycle, {}],
            ["Health", s.health, HEALTH_COLOR],
            ["Risk", s.risk, {}],
          ].map(([title, obj, colors]) => (
            <div key={title} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
              <div className="text-[10px] uppercase font-black text-slate-500">{title}</div>
              <div className="mt-2 space-y-1">
                {Object.entries(obj || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-xs">
                    <span className={`px-1.5 py-0.5 rounded font-bold ${colors[k] || "bg-slate-100 text-slate-700"}`}>{k}</span>
                    <span className="font-mono font-black text-slate-900 dark:text-white">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <TabBar
          tabs={[
            ["overview", "Listă", List],
            ["matrix", "Matrix", Grid3x3],
            ["flow", "Business ↔ Infra ↔ Autonomy", ArrowLeftRight],
          ]}
          active={tab} onChange={setTab} testidPrefix="fm-tab"
        />

        {/* FILTERS */}
        {tab === "overview" && (
          <div className="flex flex-wrap gap-2 items-center text-xs">
            <Filter className="w-4 h-4 text-slate-400" />
            {[
              ["category", ["BUSINESS", "INFRA", "SHARED"]],
              ["lifecycle", ["LIVE", "IMPLEMENTED", "PLANNED", "DRAFT", "BLOCKED"]],
              ["verification", ["VERIFIED", "PARTIAL", "UNVERIFIED", "UNKNOWN"]],
              ["health", ["GREEN", "YELLOW", "ORANGE", "RED", "GREY"]],
              ["risk", ["LOW", "MEDIUM", "HIGH", "CRITICAL"]],
            ].map(([key, opts]) => (
              <select key={key} value={filters[key]}
                onChange={e => setFilters({ ...filters, [key]: e.target.value })}
                data-testid={`fm-filter-${key}`}
                className="px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200">
                <option value="">{key} (toate)</option>
                {opts.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            ))}
            {Object.values(filters).some(Boolean) && (
              <button onClick={() => setFilters({ category: "", lifecycle: "", verification: "", health: "", risk: "" })}
                className="flex items-center gap-1 text-slate-500 hover:text-rose-500" data-testid="fm-filter-clear">
                <X className="w-3 h-3" /> reset
              </button>
            )}
            <span className="ml-auto text-slate-500 font-mono">{filtered.length}/{data?.functions?.length || 0}</span>
          </div>
        )}

        {/* CONTENT PER TAB */}
        {tab === "overview" && (
          filtered.length === 0 ? (
            <EmptyState title="Niciun rezultat" description="Ajustează filtrele pentru a vedea funcții." icon={Map} />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="fm-list">
              {filtered.map(fn => (
                <button key={fn.id} onClick={() => setSelected(fn.id)}
                  data-testid={`fm-card-${fn.id}`}
                  className="text-left rounded-2xl border-2 border-slate-200 dark:border-slate-700 hover:border-violet-400 bg-white dark:bg-slate-800 p-4 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-3 h-3 rounded-full ${HEALTH_COLOR[canon(fn.health)]}`} title={`Health: ${fn.health}`}></span>
                        <span className="text-[10px] font-mono font-bold text-slate-400">{fn.id}</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${CATEGORY_COLOR[canon(fn.category)]}`}>
                          {canon(fn.category)}
                        </span>
                      </div>
                      <h3 className="font-black text-slate-900 dark:text-white text-sm">{fn.name}</h3>
                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{fn.description}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 shrink-0 mt-1" />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-bold">{canon(fn.lifecycle)}</span>
                    <span className={`px-1.5 py-0.5 rounded border font-bold ${VERIFICATION_COLOR[canon(fn.verification)]}`}>
                      {canon(fn.verification)}
                    </span>
                    <span className={`ml-auto font-bold ${RISK_COLOR[canon(fn.risk)]}`}>
                      Risk: {canon(fn.risk)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )
        )}

        {tab === "matrix" && data && (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="fm-matrix">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-700/50 sticky top-0">
                <tr>
                  {(data.matrix_headers || []).map(h => (
                    <th key={h} className="px-3 py-2 text-left font-black uppercase text-[10px] text-slate-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.matrix.map((row, idx) => (
                  <tr key={idx} onClick={() => row.function_id && setSelected(row.function_id)}
                    className="border-t border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 cursor-pointer"
                    data-testid={`fm-matrix-row-${row.function_id || idx}`}>
                    {(data.matrix_headers || []).map((h, i) => (
                      <td key={h} className="px-3 py-2">
                        {i === 0 ? (
                          <span className="font-bold text-slate-800 dark:text-slate-200">{row[h]}</span>
                        ) : (
                          <MatrixCell value={row[h]} />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="p-3 flex gap-3 text-[10px] text-slate-500 border-t border-slate-100 dark:border-slate-700/50">
              <span><MatrixCell value="✓" /> Connected</span>
              <span><MatrixCell value="~" /> Partial</span>
              <span><MatrixCell value="?" /> Unknown</span>
              <span><MatrixCell value="✗" /> Broken</span>
            </div>
          </div>
        )}

        {tab === "flow" && (
          <div className="rounded-2xl border-2 border-violet-200 dark:border-violet-500/30 bg-gradient-to-br from-violet-50/50 to-blue-50/30 dark:from-violet-500/5 dark:to-blue-500/5 p-6" data-testid="fm-flow">
            <h3 className="font-black text-slate-900 dark:text-white text-sm mb-4">Business ↔ Infra ↔ Autonomy ↔ Human Decision</h3>
            <p className="text-xs text-slate-500 mb-6">Legăturile reale între layere. Zero fabricație — doar ce este demonstrabil din codul existent.</p>

            <div className="space-y-6">
              {[
                { title: "BUSINESS", desc: "Growth · Revenue · Product · Marketplace · UX · Customer Trust", color: "bg-blue-100 text-blue-800 border-blue-300",
                  fns: (data?.functions || []).filter(f => canon(f.category) === "BUSINESS") },
                { title: "INFRA & DEV", desc: "API · Database · Storage · AI Brain · Automation · Security", color: "bg-violet-100 text-violet-800 border-violet-300",
                  fns: (data?.functions || []).filter(f => canon(f.category) === "INFRA") },
                { title: "SHARED (Operations · Knowledge · Autonomy · Governance)", desc: "Human Decision layer explicit", color: "bg-teal-100 text-teal-800 border-teal-300",
                  fns: (data?.functions || []).filter(f => canon(f.category) === "SHARED") },
              ].map(band => (
                <div key={band.title} className={`rounded-xl border-2 p-4 ${band.color}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <div className="font-black text-sm">{band.title}</div>
                      <div className="text-[11px] opacity-70">{band.desc}</div>
                    </div>
                    <span className="text-2xl font-black">{band.fns.length}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {band.fns.map(f => (
                      <button key={f.id} onClick={() => setSelected(f.id)}
                        className="px-2 py-1 rounded bg-white/70 dark:bg-slate-800/70 hover:bg-white text-[10px] font-bold flex items-center gap-1">
                        <span className={`w-1.5 h-1.5 rounded-full ${HEALTH_COLOR[canon(f.health)]}`}></span>
                        {f.id}
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              <div className="rounded-xl border-2 border-orange-300 bg-orange-50 dark:bg-orange-500/10 p-4">
                <div className="font-black text-sm text-orange-800 dark:text-orange-300 flex items-center gap-2">
                  <Users className="w-4 h-4" /> HUMAN DECISION LAYER
                </div>
                <div className="text-[11px] text-orange-700 dark:text-orange-400 mb-3">
                  Funcțiile care necesită aprobare umană explicită înainte de execuție:
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(data?.functions || []).filter(f => (f.human_decision || "").toUpperCase().startsWith("YES")).map(f => (
                    <button key={f.id} onClick={() => setSelected(f.id)}
                      className="px-2 py-1 rounded bg-white text-[10px] font-bold flex items-center gap-1 text-orange-800 border border-orange-200 hover:bg-orange-100">
                      {f.id} · {f.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DETAIL SIDE PANEL */}
        {selected && (
          <FunctionDetailPanel id={selected} onClose={() => setSelected(null)} data={data} />
        )}
      </div>
    </AdminLayoutMetronic>
  );
}

function FunctionDetailPanel({ id, onClose, data }) {
  const fn = data?.functions?.find(f => f.id === id);
  const matrixRow = data?.matrix?.find(m => m.function_id === id);
  if (!fn) return null;

  const rows = [
    ["Identity", "ID", fn.id],
    ["Identity", "Name", fn.name],
    ["Identity", "Category", fn.category],
    ["Identity", "Subcategory", fn.subcategory],
    ["Identity", "Lifecycle", fn.lifecycle],
    ["Identity", "Description", fn.description],
    ["Technical", "Frontend", fn.frontend],
    ["Technical", "Backend", fn.backend],
    ["Technical", "API", fn.api],
    ["Technical", "Database", fn.db],
    ["Intelligence", "Engine", fn.engine],
    ["Intelligence", "Automation", fn.automation],
    ["Intelligence", "AI Involvement", fn["ai_involvement"]],
    ["Intelligence", "Autonomy", fn.autonomy],
    ["Intelligence", "Human Decision", fn["human_decision"]],
    ["Measurement", "Metric", fn.metric],
    ["Measurement", "Enterprise Health domain", fn["enterprise_health_domain"]],
    ["Measurement", "KPI", fn.kpi],
    ["Verification", "Test", fn.test],
    ["Verification", "Verification", fn.verification],
    ["Verification", "Production Verified", fn["production_verified"]],
    ["Operational", "Health", fn.health],
    ["Operational", "Risk", fn.risk],
    ["Operational", "Owner", fn.owner],
    ["Governance", "Knowledge Center", fn["knowledge_center"]],
    ["Next", "Next Action", fn["next_action"]],
  ].filter(r => r[2]);

  const groups = rows.reduce((acc, [g, k, v]) => { (acc[g] = acc[g] || []).push([k, v]); return acc; }, {});

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="fm-detail-panel" onClick={onClose}>
      <div className="flex-1 bg-slate-900/40 backdrop-blur-sm" />
      <aside onClick={e => e.stopPropagation()} className="w-full md:w-[560px] bg-white dark:bg-slate-900 h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 z-10 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 p-4 flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-3 h-3 rounded-full ${HEALTH_COLOR[canon(fn.health)]}`}></span>
              <span className="text-[10px] font-mono font-bold text-slate-400">{fn.id}</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${CATEGORY_COLOR[canon(fn.category)]}`}>{canon(fn.category)}</span>
            </div>
            <h2 className="font-black text-slate-900 dark:text-white text-lg">{fn.name}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-rose-500" data-testid="fm-detail-close"><X className="w-5 h-5" /></button>
        </div>

        {matrixRow && (
          <div className="p-4 border-b border-slate-100 dark:border-slate-800 grid grid-cols-4 gap-2 text-[10px]">
            {Object.entries(matrixRow).filter(([k]) => k !== "Function" && k !== "function_id").map(([k, v]) => (
              <div key={k} className="flex flex-col items-center gap-1">
                <MatrixCell value={v} />
                <span className="text-slate-500 text-center">{k}</span>
              </div>
            ))}
          </div>
        )}

        <div className="p-4 space-y-4">
          {Object.entries(groups).map(([group, rows]) => (
            <div key={group}>
              <div className="text-[10px] uppercase font-black text-violet-500 mb-1.5">{group}</div>
              <div className="space-y-1.5">
                {rows.map(([k, v]) => (
                  <div key={k} className="flex flex-col gap-0.5">
                    <span className="text-[10px] font-bold text-slate-400">{k}</span>
                    <span className="text-xs text-slate-700 dark:text-slate-200 break-words">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {fn["next_action"] && fn["next_action"].toLowerCase() !== "none" && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-amber-50 dark:bg-amber-500/10">
            <div className="text-[10px] font-black text-amber-700 dark:text-amber-300 uppercase mb-1">Next Action</div>
            <div className="text-xs text-slate-800 dark:text-slate-200 font-semibold">{fn["next_action"]}</div>
          </div>
        )}
      </aside>
    </div>
  );
}
