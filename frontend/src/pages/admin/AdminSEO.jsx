// Admin → SEO Control Center — READ-ONLY observability over the existing SEO SSOT.
// Reuses the backend /api/admin/seo/* endpoints (which themselves reuse the gate,
// sitemap builders and db.pages). No SEO logic is duplicated here.
import React, { useState, useCallback, useEffect } from "react";
import axios from "axios";
import {
  Search, Globe, FileText, ListChecks, Layers, AlertTriangle, BarChart3,
  RefreshCw, CheckCircle2, XCircle, ExternalLink, Loader2, Eye, ShieldCheck,
  MapPin, Building2, Gauge, Download, Link2, Plug,
} from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { useTheme as useGlobalTheme } from "../../contexts/ThemeContext";

const SUB_TABS = [
  { id: "overview", label: "Overview", icon: Gauge },
  { id: "indexability", label: "Indexability", icon: ShieldCheck },
  { id: "inspector", label: "URL Inspector", icon: Eye },
  { id: "sitemap", label: "Sitemap", icon: ListChecks },
  { id: "pages", label: "Pages", icon: FileText },
  { id: "clusters", label: "Clusters", icon: Layers },
  { id: "hartablocuri-clusters", label: "HartaBlocuri", icon: Building2 },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "gsc", label: "GSC", icon: BarChart3 },
];

const Badge = ({ ok, yes = "INDEX", no = "NOINDEX" }) => (
  <span
    data-testid={`seo-badge-${ok ? "index" : "noindex"}`}
    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
      ok ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
         : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
    }`}
  >
    {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
    {ok ? yes : no}
  </span>
);

const Stat = ({ label, value, tone = "default", testid }) => {
  const { isDark } = useGlobalTheme();
  const tones = {
    default: isDark ? "text-slate-100" : "text-slate-900",
    good: "text-emerald-500",
    warn: "text-amber-500",
    bad: "text-red-500",
    muted: isDark ? "text-slate-400" : "text-slate-500",
  };
  return (
    <div className={`rounded-xl border p-4 ${isDark ? "bg-slate-900 border-slate-800" : "bg-white border-slate-200"}`} data-testid={testid}>
      <div className={`text-2xl font-bold ${tones[tone]}`}>{value}</div>
      <div className={`text-xs mt-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>{label}</div>
    </div>
  );
};

export const AdminSEO = () => {
  const { isDark } = useGlobalTheme();
  const [tab, setTab] = useState(() => {
    try {
      const p = new URLSearchParams(window.location.search);
      if (p.get("gsc")) return "gsc";  // arriving back from the GSC OAuth callback
      const t = p.get("subtab");
      if (t && SUB_TABS.some((s) => s.id === t)) return t;
    } catch { /* noop */ }
    return "overview";
  });
  const [cache, setCache] = useState({});
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const txt = isDark ? "text-slate-200" : "text-slate-700";
  const muted = isDark ? "text-slate-400" : "text-slate-500";
  const border = isDark ? "border-slate-800" : "border-slate-200";
  const rowBorder = isDark ? "border-slate-800" : "border-slate-100";

  const load = useCallback(async (id, force = false) => {
    if (cache[id] && !force) return cache[id];
    setLoading(true); setErr(null);
    try {
      const r = await axios.get(`${API}/admin/seo/${id === "inspector" ? "overview" : id}`);
      setCache((c) => ({ ...c, [id]: r.data }));
      return r.data;
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Eroare la încărcare");
      return null;
    } finally {
      setLoading(false);
    }
  }, [cache]);

  React.useEffect(() => {
    if (tab === "inspector" || tab === "gsc") return; // on-demand tabs
    if (!cache[tab]) load(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const data = cache[tab];

  return (
    <div className="space-y-5" data-testid="admin-seo">
      {/* Sub-tab nav */}
      <div className={`flex flex-wrap gap-1.5 border-b pb-3 ${border}`}>
        {SUB_TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              data-testid={`seo-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                active ? "bg-blue-600 text-white"
                       : isDark ? "text-slate-300 hover:bg-slate-800" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
        <div className="ml-auto">
          <AdminBtn variant="ghost" onClick={() => load(tab === "inspector" ? "overview" : tab, true)} data-testid="seo-refresh">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </AdminBtn>
        </div>
      </div>

      {err && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm px-4 py-3" data-testid="seo-error">{err}</div>
      )}
      {loading && !data && (
        <div className={`flex items-center gap-2 text-sm ${muted}`} data-testid="seo-loading">
          <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă din SSOT…
        </div>
      )}

      {/* ---------------- OVERVIEW ---------------- */}
      {tab === "overview" && data && (
        <div className="space-y-5" data-testid="seo-overview">
          <div className="flex flex-wrap gap-2" data-testid="seo-export-bar">
            <a href={`${API}/admin/seo/export/indexability.csv`} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500" data-testid="seo-export-indexability-csv"><Download className="w-3.5 h-3.5" /> Matrice indexabilitate (CSV)</a>
            <a href={`${API}/admin/seo/export/alerts.csv`} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500" data-testid="seo-export-alerts-csv"><Download className="w-3.5 h-3.5" /> Alerte (CSV)</a>
            <a href={`${API}/admin/seo/export/report.pdf`} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-600 text-white hover:bg-slate-500" data-testid="seo-export-pdf"><Download className="w-3.5 h-3.5" /> Raport SEO (PDF)</a>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat testid="seo-stat-total" label="URL-uri publice cunoscute" value={data.indexability.total_public_urls} tone="muted" />
            <Stat testid="seo-stat-indexable" label="URL-uri INDEXABILE (în sitemap)" value={data.indexability.indexable_urls} tone="good" />
            <Stat testid="seo-stat-noindex" label="URL-uri NOINDEX (thin, excluse)" value={data.indexability.noindex_urls} tone="warn" />
            <Stat testid="seo-stat-canonical" label="Canonicalizate → părinte" value={data.indexability.canonicalized_urls} tone="muted" />
          </div>

          <AdminCard title="Sitemap" testid="seo-overview-sitemap">
            <div className="flex flex-wrap items-center gap-3 mb-4 text-sm">
              <span className={txt}>Root:</span>
              <a href={data.sitemap.root} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">
                {data.sitemap.root} <ExternalLink className="w-3 h-3" />
              </a>
              <Badge ok={data.sitemap.valid} yes="VALID" no="INVALID" />
              <span className={`text-xs ${muted}`}>sitemap-index · {data.sitemap.child_count} copii · {data.sitemap.total_urls} URL-uri</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {data.sitemap.children.map((c) => (
                <div key={c.name} className={`rounded-lg border p-3 ${border}`} data-testid={`seo-child-${c.name}`}>
                  <div className={`text-xs ${muted}`}>{c.name}</div>
                  <div className={`text-lg font-bold ${txt}`}>{c.url_count}</div>
                </div>
              ))}
            </div>
            {data.sitemap.last_generated && (
              <div className={`text-xs mt-3 ${muted}`}>Generat ultima dată: {new Date(data.sitemap.last_generated).toLocaleString("ro-RO")}</div>
            )}
          </AdminCard>

          <AdminCard title="SEO Health" testid="seo-overview-health">
            <div className="flex flex-wrap gap-2">
              {[
                ["robots.txt", data.health.robots_ok],
                ["Sitemap", data.health.sitemap_ok],
                ["Canonical", data.health.canonical_ok],
                ["Indexability Gate", data.health.gate_ok],
                ["Structured Data", data.health.structured_data_ok],
              ].map(([label, ok]) => (
                <span key={label} className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm ${ok ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"}`}>
                  {ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />} {label}
                </span>
              ))}
            </div>
            <div className="flex gap-4 mt-4 text-sm">
              <span className="text-red-500 font-semibold" data-testid="seo-critical-count">{data.health.critical_count} critice</span>
              <span className="text-amber-500 font-semibold" data-testid="seo-warning-count">{data.health.warning_count} avertismente</span>
            </div>
          </AdminCard>
        </div>
      )}

      {/* ---------------- INDEXABILITY ---------------- */}
      {tab === "indexability" && data && <IndexabilityView data={data} isDark={isDark} rowBorder={rowBorder} txt={txt} muted={muted} border={border} />}

      {/* ---------------- URL INSPECTOR ---------------- */}
      {tab === "inspector" && <InspectorView isDark={isDark} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />}

      {/* ---------------- SITEMAP ---------------- */}
      {tab === "sitemap" && data && <SitemapView data={data} isDark={isDark} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />}

      {/* ---------------- PAGES ---------------- */}
      {tab === "pages" && data && <PagesView data={data} isDark={isDark} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />}

      {/* ---------------- CLUSTERS ---------------- */}
      {tab === "clusters" && data && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="seo-clusters">
          {data.clusters.map((c) => (
            <AdminCard key={c.id} testid={`seo-cluster-${c.id}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className={`font-semibold ${txt}`}>{c.label}</h3>
                {c.internally_linked
                  ? <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500">LINKED</span>
                  : <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-500/15 text-slate-400">ORPHAN?</span>}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className={muted}>Pagini: <span className={`font-bold ${txt}`}>{c.pages}</span></div>
                <div className={muted}>În sitemap: <span className="font-bold text-emerald-500">{c.in_sitemap}</span></div>
                <div className={muted}>Indexabile: <span className="font-bold text-emerald-500">{c.indexable}</span></div>
                <div className={muted}>Noindex: <span className="font-bold text-amber-500">{c.noindex}</span></div>
              </div>
              {c.note && <div className={`text-xs mt-3 italic ${muted}`}>{c.note}</div>}
            </AdminCard>
          ))}
        </div>
      )}

      {/* ---------------- HARTABLOCURI SEO CLUSTER PILOT ---------------- */}
      {tab === "hartablocuri-clusters" && data && (
        <HartaBlocuriClustersView data={data} isDark={isDark} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />
      )}

      {/* ---------------- ALERTS ---------------- */}
      {tab === "alerts" && data && (
        <div className="space-y-4" data-testid="seo-alerts">
          <div className="flex gap-3">
            <Stat testid="seo-alerts-critical" label="Critice" value={data.critical_count} tone={data.critical_count ? "bad" : "good"} />
            <Stat testid="seo-alerts-warning" label="Avertismente" value={data.warning_count} tone={data.warning_count ? "warn" : "good"} />
          </div>
          {data.critical.length === 0 && data.warning.length === 0 && (
            <div className="rounded-lg bg-emerald-500/10 text-emerald-500 px-4 py-3 text-sm inline-flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" /> Niciun issue SEO. Fundația este sănătoasă.
            </div>
          )}
          {data.critical.map((a, i) => (
            <div key={`c${i}`} className="rounded-lg border border-red-500/30 bg-red-500/5 p-4" data-testid={`seo-alert-critical-${i}`}>
              <div className="flex items-center gap-2 text-red-500 font-semibold text-sm"><XCircle className="w-4 h-4" /> {a.title} <span className="text-[10px] font-mono opacity-60">{a.code}</span></div>
              <div className={`text-sm mt-1 ${txt}`}>{a.detail}</div>
            </div>
          ))}
          {data.warning.map((a, i) => (
            <div key={`w${i}`} className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4" data-testid={`seo-alert-warning-${i}`}>
              <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm"><AlertTriangle className="w-4 h-4" /> {a.title} <span className="text-[10px] font-mono opacity-60">{a.code}</span></div>
              <div className={`text-sm mt-1 ${txt}`}>{a.detail}</div>
            </div>
          ))}
        </div>
      )}

      {/* ---------------- GSC ---------------- */}
      {tab === "gsc" && <GSCView isDark={isDark} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />}
    </div>
  );
};

// ── HartaBlocuri SEO Cluster Pilot (read-only, NEpublicat) ──────────────────
const CONF_PILL = {
  high: "bg-emerald-500/15 text-emerald-500", medium: "bg-sky-500/15 text-sky-500",
  low: "bg-amber-500/15 text-amber-500", unknown: "bg-slate-500/15 text-slate-400",
  not_available: "bg-slate-500/10 text-slate-400",
};
const HartaBlocuriClustersView = ({ data, isDark, txt, muted, border, rowBorder }) => {
  const [open, setOpen] = useState(null);
  const [stateFilter, setStateFilter] = useState("");
  const STATE_CLS = {
    INDEX: "bg-emerald-500/15 text-emerald-500", PREPARED: "bg-sky-500/15 text-sky-500",
    CANDIDATE: "bg-slate-500/15 text-slate-400", NOINDEX: "bg-amber-500/15 text-amber-500",
    BLOCKED: "bg-red-500/15 text-red-500",
  };
  const clusters = (data.clusters || []).filter(c => !stateFilter || c.state === stateFilter);
  const STATES = ["INDEX", "PREPARED", "CANDIDATE", "NOINDEX", "BLOCKED"];
  return (
    <div className="space-y-4" data-testid="seo-hb-clusters">
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2" data-testid="seo-hb-summary">
        <Stat testid="seo-hb-total" label="Total" value={data.total} />
        <Stat testid="seo-hb-index" label="INDEX" value={data.index} tone="good" />
        <Stat testid="seo-hb-prepared" label="PREPARED" value={data.prepared} tone="muted" />
        <Stat testid="seo-hb-candidate" label="CANDIDATE" value={data.candidate} tone="muted" />
        <Stat testid="seo-hb-blocked" label="BLOCKED" value={data.blocked} tone={data.blocked ? "warn" : "muted"} />
        <Stat testid="seo-hb-sitemap" label="În sitemap" value={data.in_sitemap} tone="good" />
        <Stat testid="seo-hb-counties" label="Județe" value={(data.counties || []).length} />
      </div>
      <div className="flex flex-wrap gap-2" data-testid="seo-hb-state-filter">
        <button onClick={() => setStateFilter("")} className={`px-3 py-1 rounded-full text-xs ${!stateFilter ? "bg-[#d4ff3a]/20 text-[#8a9a1f] dark:text-[#d4ff3a]" : "bg-slate-500/10 " + muted}`}>Toate</button>
        {STATES.map(s => (
          <button key={s} onClick={() => setStateFilter(s)} className={`px-3 py-1 rounded-full text-xs ${stateFilter === s ? STATE_CLS[s] : "bg-slate-500/10 " + muted}`} data-testid={`seo-hb-filter-${s}`}>{s}</button>
        ))}
      </div>
      <div className="space-y-2">
        {clusters.map((c) => {
          const a = c.aggregates || {};
          const isOpen = open === c.slug;
          return (
            <div key={c.slug} className={`rounded-xl border ${border} ${isDark ? "bg-slate-900" : "bg-white"}`} data-testid={`seo-hb-cluster-${c.id}`}>
              <button onClick={() => setOpen(isOpen ? null : c.slug)} className="w-full text-left p-4" data-testid={`seo-hb-cluster-toggle-${c.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className={`font-semibold ${txt}`}>{c.value_label}</div>
                    <div className={`text-xs font-mono ${muted} truncate`}>{c.slug}</div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${STATE_CLS[c.state]}`}>{c.state}</span>
                    <Badge ok={c.index} />
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${c.in_sitemap ? "bg-emerald-500/15 text-emerald-500" : "bg-slate-500/15 text-slate-400"}`}>{c.in_sitemap ? "SITEMAP" : "—"}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 text-xs">
                  <div className={muted}>Clădiri: <span className={`font-bold ${txt}`}>{c.building_count}</span></div>
                  <div className={muted}>Județ: <span className={`font-bold ${txt}`}>{c.county}</span></div>
                  <div className={muted}>Dimensiune: <span className={`font-bold ${txt}`}>{c.dimension}</span></div>
                  <div className={muted}>Nivel: <span className={`font-bold ${txt}`}>{c.level}</span></div>
                  <div className={muted}>Scor: <span className={`font-bold ${txt}`}>{c.quality_score}</span></div>
                </div>
                <div className={`text-[11px] mt-2 ${muted}`}>Motiv: {c.index_reason}</div>
              </button>
              {isOpen && (
                <div className={`border-t ${rowBorder} p-4 space-y-2 text-xs`} data-testid={`seo-hb-cluster-detail-${c.id}`}>
                  <div><span className={muted}>Canonical:</span> <span className={`font-mono ${txt}`}>{c.canonical}</span></div>
                  {c.content && <>
                    <div><span className={muted}>Meta title:</span> <span className={txt}>{c.content.meta_title}</span></div>
                    <div><span className={muted}>Meta description:</span> <span className={txt}>{c.content.meta_description}</span></div>
                    <div><span className={muted}>H1:</span> <span className={txt}>{c.content.h1}</span></div>
                  </>}
                  {(a.era_distribution || []).length > 0 && <div><span className={muted}>Eră:</span> <span className={txt}>{a.era_distribution.map(e => `${e.value} (${e.count})`).join(" · ")}</span></div>}
                  {(a.neighborhood_distribution || []).length > 0 && <div><span className={muted}>Cartiere:</span> <span className={txt}>{a.neighborhood_distribution.map(e => `${e.value} (${e.count})`).join(" · ")}</span></div>}
                  <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-2 space-y-1">
                    {(c.data_limits || []).map((l, i) => <div key={i} className="text-amber-500/90">• {l}</div>)}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};


// ── Indexability matrix ─────────────────────────────────────────────────────
const IndexabilityView = ({ data, isDark, rowBorder, txt, muted, border }) => {
  const [filter, setFilter] = useState("all"); // all | index | noindex
  const [q, setQ] = useState("");
  const rows = [...data.national, ...data.combos];
  const filtered = rows.filter((r) => {
    if (filter === "index" && !r.index) return false;
    if (filter === "noindex" && r.index) return false;
    if (q) {
      const s = `${r.service_slug} ${r.city_slug || ""} ${r.service_label}`.toLowerCase();
      if (!s.includes(q.toLowerCase())) return false;
    }
    return true;
  });
  return (
    <div className="space-y-4" data-testid="seo-indexability">
      <div className="flex flex-wrap gap-3 items-center">
        <Stat label="National INDEX" value={data.summary.national_index} tone="good" />
        <Stat label="Service×City INDEX" value={data.summary.combos_index} tone="good" />
        <Stat label="Service×City NOINDEX" value={data.summary.combos_noindex} tone="warn" />
        <div className={`text-xs ${muted}`}>Prag: ≥{data.threshold} specialiști verificați</div>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {["all", "index", "noindex"].map((f) => (
          <button key={f} data-testid={`seo-idx-filter-${f}`} onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-lg text-xs font-medium ${filter === f ? "bg-blue-600 text-white" : isDark ? "bg-slate-800 text-slate-300" : "bg-slate-100 text-slate-600"}`}>
            {f === "all" ? "Toate" : f.toUpperCase()}
          </button>
        ))}
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border ${border} ml-auto`}>
          <Search className={`w-3.5 h-3.5 ${muted}`} />
          <input data-testid="seo-idx-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="serviciu / oraș…"
            className={`bg-transparent text-sm outline-none ${txt}`} />
        </div>
      </div>
      <div className={`overflow-x-auto rounded-xl border ${border}`}>
        <table className="w-full text-sm" data-testid="seo-idx-table">
          <thead>
            <tr className={`text-left ${muted} border-b ${rowBorder}`}>
              <th className="px-3 py-2 font-medium">Serviciu</th>
              <th className="px-3 py-2 font-medium">Oraș</th>
              <th className="px-3 py-2 font-medium">Verificați</th>
              <th className="px-3 py-2 font-medium">Prag</th>
              <th className="px-3 py-2 font-medium">Indexabilitate</th>
              <th className="px-3 py-2 font-medium">Canonical</th>
              <th className="px-3 py-2 font-medium">Motiv</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 400).map((r, i) => (
              <tr key={i} className={`border-b ${rowBorder}`} data-testid={`seo-idx-row-${r.service_slug}-${r.city_slug || "national"}`}>
                <td className={`px-3 py-2 ${txt}`}>{r.service_label}</td>
                <td className={`px-3 py-2 ${muted}`}>{r.city_label || <span className="italic">— național —</span>}</td>
                <td className={`px-3 py-2 font-semibold ${r.verified >= r.threshold ? "text-emerald-500" : "text-amber-500"}`}>{r.verified}</td>
                <td className={`px-3 py-2 ${muted}`}>{r.threshold}</td>
                <td className="px-3 py-2"><Badge ok={r.index} /></td>
                <td className={`px-3 py-2 text-xs ${muted}`}>{r.index ? "self" : (r.canonical || "").replace(data.site_url || "", "") || "→ părinte"}</td>
                <td className={`px-3 py-2 text-xs ${muted}`}>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={`text-xs ${muted}`}>{filtered.length} rânduri (max 400 afișate). Sursă: același gate ca sitemap-ul + paginile publice.</div>
    </div>
  );
};

// ── URL Inspector ───────────────────────────────────────────────────────────
const InspectorView = ({ isDark, txt, muted, border, rowBorder }) => {
  const [url, setUrl] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const samples = ["/", "/design-interior", "/marketplace/hvac-bucuresti", "/marketplace/electrician-bucuresti", "/probleme-casa/mucegai-igrasie", "/specialists/abc123", "/specialist"];

  const run = async (u) => {
    const target = (u ?? url).trim();
    if (!target) return;
    setUrl(target); setBusy(true); setError(null); setRes(null);
    try {
      const r = await axios.get(`${API}/admin/seo/inspect`, { params: { path: target } });
      setRes(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  const Row = ({ k, children }) => (
    <div className={`flex flex-col sm:flex-row sm:items-center gap-1 py-2 border-b ${rowBorder}`}>
      <div className={`w-48 shrink-0 text-xs font-medium ${muted}`}>{k}</div>
      <div className={`text-sm ${txt} break-all`}>{children}</div>
    </div>
  );

  return (
    <div className="space-y-4" data-testid="seo-inspector">
      <AdminCard>
        <div className="flex flex-wrap gap-2">
          <div className={`flex-1 min-w-[240px] flex items-center gap-2 px-3 py-2 rounded-lg border ${border}`}>
            <Globe className={`w-4 h-4 ${muted}`} />
            <input data-testid="seo-inspect-input" value={url} onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="/marketplace/hvac-bucuresti sau URL complet"
              className={`flex-1 bg-transparent outline-none text-sm ${txt}`} />
          </div>
          <AdminBtn onClick={() => run()} data-testid="seo-inspect-btn" disabled={busy}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Search className="w-4 h-4 mr-1 inline" />Inspectează</>}
          </AdminBtn>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {samples.map((s) => (
            <button key={s} onClick={() => run(s)} data-testid={`seo-inspect-sample-${s}`}
              className={`text-[11px] px-2 py-1 rounded-md ${isDark ? "bg-slate-800 text-slate-300 hover:bg-slate-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>{s}</button>
          ))}
        </div>
      </AdminCard>

      {error && <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm px-4 py-3">{error}</div>}

      {res && (
        <AdminCard testid="seo-inspect-result">
          <div className="flex flex-wrap items-center gap-3 mb-3">
            <code className={`text-sm font-mono ${txt}`}>{res.path}</code>
            <Badge ok={res.index} />
            <span className={`text-xs px-2 py-0.5 rounded-full ${res.http_status === 200 ? "bg-emerald-500/15 text-emerald-500" : "bg-red-500/15 text-red-500"}`}>HTTP {res.http_status}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-500`}>{res.page_type}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-500`}>{res.cluster_label}</span>
          </div>
          <Row k="Robots (meta)">{res.robots}</Row>
          <Row k="Blocat de robots.txt">{res.robots_txt_blocked ? <span className="text-red-500">DA — regula {res.robots_txt_rule}</span> : <span className="text-emerald-500">Nu</span>}</Row>
          <Row k="Canonical">{res.canonical} <span className={`text-xs italic ${muted}`}>({res.canonical_reason})</span></Row>
          <Row k="În sitemap">{res.in_sitemap ? <span className="text-emerald-500">Da</span> : <span className={muted}>Nu</span>}</Row>
          <Row k="Title">{res.title || <span className={`italic ${muted}`}>randat client-side</span>}</Row>
          <Row k="H1">{res.h1 || <span className={`italic ${muted}`}>randat client-side</span>}</Row>
          <Row k="Meta description">{res.description || <span className={`italic ${muted}`}>randat client-side</span>}</Row>
          <Row k="Structured data">{res.structured_data.length ? res.structured_data.join(", ") : <span className={muted}>—</span>}</Row>
          <Row k="BreadcrumbList">{res.breadcrumbs ? <span className="text-emerald-500">Da</span> : <span className={muted}>Nu</span>}</Row>
          {res.errors.length > 0 && (
            <div className="mt-3 space-y-1">
              {res.errors.map((e, i) => <div key={i} className="text-sm text-red-500 flex gap-1.5"><XCircle className="w-4 h-4 shrink-0" />{e}</div>)}
            </div>
          )}
          {res.warnings.length > 0 && (
            <div className="mt-3 space-y-1">
              {res.warnings.map((w, i) => <div key={i} className="text-sm text-amber-500 flex gap-1.5"><AlertTriangle className="w-4 h-4 shrink-0" />{w}</div>)}
            </div>
          )}
        </AdminCard>
      )}
    </div>
  );
};

// ── Sitemap ─────────────────────────────────────────────────────────────────
const SitemapView = ({ data, isDark, txt, muted, border, rowBorder }) => {
  const [valid, setValid] = useState(null);
  const [busy, setBusy] = useState(false);
  const runValidate = async () => {
    setBusy(true);
    try {
      const r = await axios.post(`${API}/admin/seo/sitemap/validate`);
      setValid(r.data);
    } catch (e) { setValid({ valid: false, checks: [{ ok: false, name: "Eroare", detail: e.message }] }); }
    finally { setBusy(false); }
  };
  return (
    <div className="space-y-4" data-testid="seo-sitemap">
      <AdminCard title="Structură sitemap-index" action={
        <AdminBtn onClick={runValidate} data-testid="seo-validate-btn" disabled={busy}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ShieldCheck className="w-4 h-4 mr-1 inline" />Validate Sitemap</>}
        </AdminBtn>
      }>
        <div className="flex items-center gap-2 mb-4 text-sm flex-wrap">
          <a href={data.root.url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">{data.root.url} <ExternalLink className="w-3 h-3" /></a>
          <span className={`text-xs ${muted}`}>index · {data.root.child_count} copii · {data.total_urls} URL-uri · {data.excluded_count} excluse</span>
        </div>
        <div className={`flex flex-wrap gap-4 mb-4 text-xs ${muted}`} data-testid="seo-sitemap-regen">
          {data.last_generated && <span>Generat: <span className={txt}>{new Date(data.last_generated).toLocaleString("ro-RO")}</span></span>}
          {data.last_regeneration && (
            <span>Ultima regenerare auto: {data.last_regeneration.ok
              ? <span className="text-emerald-500">OK ({data.last_regeneration.url_count} URL) · {data.last_regeneration.reason}</span>
              : <span className="text-red-500">EȘUAT · {data.last_regeneration.error}</span>}</span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {data.children.map((c) => (
            <a key={c.name} href={c.url} target="_blank" rel="noreferrer" className={`rounded-lg border p-3 hover:border-blue-500 transition-colors ${border}`} data-testid={`seo-sitemap-child-${c.name}`}>
              <div className={`text-xs ${muted} truncate`}>{c.name}</div>
              <div className={`text-lg font-bold ${txt}`}>{c.url_count}</div>
            </a>
          ))}
        </div>
      </AdminCard>

      {valid && (
        <AdminCard title="Rezultat validare" testid="seo-validate-result">
          <div className="flex items-center gap-2 mb-3">
            <Badge ok={valid.valid} yes="VALID" no="INVALID" />
            <span className={`text-xs ${muted}`}>{valid.total_urls} URL-uri verificate</span>
          </div>
          <div className="space-y-1.5">
            {valid.checks.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-sm" data-testid={`seo-check-${i}`}>
                {c.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> : <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                <span className={txt}>{c.name}</span>
                <span className={`text-xs ${muted}`}>— {c.detail}</span>
              </div>
            ))}
          </div>
        </AdminCard>
      )}

      <AdminCard title={`URL-uri excluse (${data.excluded_count}) — motivul gate-ului`} testid="seo-excluded">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={`text-left ${muted} border-b ${rowBorder} sticky top-0 ${isDark ? "bg-slate-900" : "bg-white"}`}>
                <th className="px-3 py-2 font-medium">URL</th>
                <th className="px-3 py-2 font-medium">Tip</th>
                <th className="px-3 py-2 font-medium">Motiv</th>
              </tr>
            </thead>
            <tbody>
              {data.excluded_sample.map((r, i) => (
                <tr key={i} className={`border-b ${rowBorder}`}>
                  <td className={`px-3 py-2 text-xs font-mono ${txt}`}>{r.url.replace("https://propmanage.ro", "")}</td>
                  <td className={`px-3 py-2 text-xs ${muted}`}>{r.type}</td>
                  <td className={`px-3 py-2 text-xs ${muted}`}>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AdminCard>
    </div>
  );
};

// ── Pages inventory ───────────────────────────────────────────────────────────
const PagesView = ({ data, isDark, txt, muted, border, rowBorder }) => {
  const [q, setQ] = useState("");
  const [cl, setCl] = useState("all");
  const clusters = ["all", ...Array.from(new Set(data.pages.map((p) => p.cluster)))];
  const rows = data.pages.filter((p) => {
    if (cl !== "all" && p.cluster !== cl) return false;
    if (q && !`${p.url} ${p.title || ""}`.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });
  return (
    <div className="space-y-4" data-testid="seo-pages">
      <div className="flex flex-wrap gap-3 items-center">
        <Stat label="Total pagini SEO" value={data.total} tone="muted" />
        <Stat label="Indexabile" value={data.indexable} tone="good" />
        <Stat label="Noindex" value={data.noindex} tone="warn" />
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border ${border} ml-auto`}>
          <Search className={`w-3.5 h-3.5 ${muted}`} />
          <input data-testid="seo-pages-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="URL / title…" className={`bg-transparent text-sm outline-none ${txt}`} />
        </div>
        <select data-testid="seo-pages-cluster" value={cl} onChange={(e) => setCl(e.target.value)}
          className={`text-sm rounded-lg border px-2 py-1.5 ${border} ${isDark ? "bg-slate-900 text-slate-200" : "bg-white text-slate-700"}`}>
          {clusters.map((c) => <option key={c} value={c}>{c === "all" ? "Toate clusterele" : c}</option>)}
        </select>
      </div>
      <div className={`overflow-x-auto rounded-xl border ${border}`}>
        <table className="w-full text-sm" data-testid="seo-pages-table">
          <thead>
            <tr className={`text-left ${muted} border-b ${rowBorder}`}>
              <th className="px-3 py-2 font-medium">URL</th>
              <th className="px-3 py-2 font-medium">Tip</th>
              <th className="px-3 py-2 font-medium">Cluster</th>
              <th className="px-3 py-2 font-medium">Index</th>
              <th className="px-3 py-2 font-medium">Sitemap</th>
              <th className="px-3 py-2 font-medium">Warnings</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <tr key={i} className={`border-b ${rowBorder}`} data-testid={`seo-page-row-${i}`}>
                <td className={`px-3 py-2 font-mono text-xs ${txt}`}>{p.url}</td>
                <td className={`px-3 py-2 text-xs ${muted}`}>{p.page_type}</td>
                <td className={`px-3 py-2 text-xs ${muted}`}>{p.cluster_label}</td>
                <td className="px-3 py-2"><Badge ok={p.index} /></td>
                <td className={`px-3 py-2 text-xs`}>{p.in_sitemap ? <span className="text-emerald-500">✓</span> : <span className={muted}>—</span>}</td>
                <td className={`px-3 py-2 text-xs ${p.warnings.length ? "text-amber-500" : muted}`}>{p.warnings.length ? p.warnings.join(", ") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={`text-xs ${muted}`}>{rows.length} pagini afișate.</div>
    </div>
  );
};

// ── GSC (Google Search Console) — connect + real report ──────────────────────
const GSCView = ({ isDark, txt, muted, border, rowBorder }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prop, setProp] = useState("sc-domain:propmanage.ro");
  const [json, setJson] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [oauthBusy, setOauthBusy] = useState(false);
  const [connectMsg, setConnectMsg] = useState(null);
  const [flash] = useState(() => {
    // Read the OAuth callback result synchronously (the admin console strips the
    // query string in a mount effect, so we must capture it during first render).
    try {
      const p = new URLSearchParams(window.location.search);
      const g = p.get("gsc");
      if (g) {
        if (g === "connected") return { ok: true, text: "Conectat cu Google Search Console ✓" };
        const reason = p.get("reason") || g;
        const detail = p.get("detail");
        return { ok: false, text: `Conectare GSC eșuată: ${reason}${detail ? ` (${detail})` : ""}` };
      }
    } catch { /* noop */ }
    return null;
  });
  const [range, setRange] = useState("28d");
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);

  const loadStatus = async () => {
    setLoading(true);
    try { const r = await axios.get(`${API}/admin/seo/gsc`); setStatus(r.data); }
    catch (e) { setStatus({ connected: false, message: e.message }); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadStatus(); }, []);

  const oauthConnect = async () => {
    setOauthBusy(true); setConnectMsg(null);
    try {
      const r = await axios.get(`${API}/admin/seo/gsc/oauth/start`, { params: { property: prop } });
      if (r.data.ok && r.data.authorization_url) window.location.assign(r.data.authorization_url);
      else setConnectMsg({ ok: false, text: r.data.error || "Nu s-a putut porni OAuth." });
    } catch (e) { setConnectMsg({ ok: false, text: e?.response?.data?.detail || e.message }); }
    finally { setOauthBusy(false); }
  };

  const connect = async () => {
    setConnecting(true); setConnectMsg(null);
    try {
      const r = await axios.post(`${API}/admin/seo/gsc/connect`, { property: prop, service_account_json: json });
      if (r.data.ok) { setConnectMsg({ ok: true, text: `Salvat. Adaugă ${r.data.service_account_email} ca user în property-ul GSC.` }); setJson(""); await loadStatus(); }
      else setConnectMsg({ ok: false, text: r.data.error });
    } catch (e) { setConnectMsg({ ok: false, text: e?.response?.data?.detail || e.message }); }
    finally { setConnecting(false); }
  };

  const disconnect = async () => { await axios.post(`${API}/admin/seo/gsc/disconnect`); setReport(null); await loadStatus(); };

  const loadReport = async () => {
    setReportLoading(true);
    try { const r = await axios.get(`${API}/admin/seo/gsc/report`, { params: { range } }); setReport(r.data); }
    catch (e) { setReport({ status: "error", error: e.message }); }
    finally { setReportLoading(false); }
  };
  useEffect(() => { if (status?.connected) loadReport(); /* eslint-disable-next-line */ }, [status?.connected, range]);

  if (loading) return <div className={`flex items-center gap-2 text-sm ${muted}`}><Loader2 className="w-4 h-4 animate-spin" /> Se verifică GSC…</div>;

  const FlashBanner = () => flash ? (
    <div className={`rounded-lg text-sm px-4 py-2.5 mb-3 ${flash.ok ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-500" : "bg-red-500/10 border border-red-500/30 text-red-500"}`} data-testid="seo-gsc-flash">{flash.text}</div>
  ) : null;

  if (!status?.connected) {
    return (
      <AdminCard title="Google Search Console" testid="seo-gsc">
        <FlashBanner />
        <div className="flex items-center gap-2 mb-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-500/15 text-slate-400 text-sm font-medium" data-testid="seo-gsc-status">
            <XCircle className="w-4 h-4" /> Not connected
          </span>
        </div>
        <p className={`text-sm ${txt} max-w-2xl mb-4`}>{status?.message}</p>
        {status?.last_error && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-500 text-xs px-3 py-2 max-w-2xl" data-testid="seo-gsc-last-error">
            Ultima încercare de conectare a eșuat: <code>{status.last_error}</code>{status.last_error_at ? ` · ${new Date(status.last_error_at).toLocaleString("ro-RO")}` : ""}
          </div>
        )}

        {status?.oauth_available && (
          <div className="mb-6 rounded-xl border border-blue-500/30 bg-blue-500/5 p-4 max-w-2xl" data-testid="seo-gsc-oauth">
            <div className={`text-sm font-semibold mb-2 ${txt}`}>Recomandat — conectează prin contul Google (OAuth)</div>
            <ol className={`text-xs ${muted} space-y-1 mb-3 list-decimal ml-4`}>
              {(status.how_to_oauth || []).map((s, i) => <li key={i}>{s.replace(/^\d+\.\s*/, "")}</li>)}
            </ol>
            <div className="flex flex-wrap items-center gap-2">
              <input value={prop} onChange={(e) => setProp(e.target.value)} data-testid="seo-gsc-oauth-property"
                className={`flex-1 min-w-[220px] rounded-lg border px-3 py-2 text-sm ${border} ${isDark ? "bg-slate-900 text-slate-200" : "bg-white text-slate-700"}`}
                placeholder="sc-domain:propmanage.ro" />
              <AdminBtn onClick={oauthConnect} disabled={oauthBusy} data-testid="seo-gsc-oauth-btn">
                {oauthBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plug className="w-4 h-4 mr-1 inline" /> Conectează cu Google</>}
              </AdminBtn>
            </div>
            <div className={`text-[11px] mt-2 ${muted}`}>Redirect URI de înregistrat în Google Cloud OAuth Client: <code className="text-blue-400 break-all">{status.redirect_uri}</code></div>
          </div>
        )}

        <details className="max-w-2xl" data-testid="seo-gsc-sa-details">
          <summary className={`text-sm cursor-pointer ${muted} mb-3`}>Alternativă: Service Account (cheie JSON)</summary>
          {status?.how_to && (
            <ol className={`text-xs ${muted} space-y-1 mb-4 list-decimal ml-4`}>
              {status.how_to.map((s, i) => <li key={i}>{s.replace(/^\d+\.\s*/, "")}</li>)}
            </ol>
          )}
          <div className="space-y-3" data-testid="seo-gsc-connect">
            <div>
              <label className={`text-xs ${muted}`}>Property GSC</label>
              <input value={prop} onChange={(e) => setProp(e.target.value)} data-testid="seo-gsc-property"
                className={`w-full mt-1 rounded-lg border px-3 py-2 text-sm ${border} ${isDark ? "bg-slate-900 text-slate-200" : "bg-white text-slate-700"}`}
                placeholder="sc-domain:propmanage.ro" />
            </div>
            <div>
              <label className={`text-xs ${muted}`}>Service Account JSON (nu este expus niciodată)</label>
              <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={6} data-testid="seo-gsc-json"
                className={`w-full mt-1 rounded-lg border px-3 py-2 text-xs font-mono ${border} ${isDark ? "bg-slate-900 text-slate-200" : "bg-white text-slate-700"}`}
                placeholder='{"type":"service_account", ...}' />
            </div>
            <AdminBtn onClick={connect} disabled={connecting} data-testid="seo-gsc-connect-btn">
              {connecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plug className="w-4 h-4 mr-1 inline" /> Conectează cu Service Account</>}
            </AdminBtn>
          </div>
        </details>
        {connectMsg && <div className={`text-sm mt-3 ${connectMsg.ok ? "text-emerald-500" : "text-red-500"}`} data-testid="seo-gsc-connect-msg">{connectMsg.text}</div>}
        <div className={`text-xs mt-4 ${muted}`}>Meta de verificare site: {status?.site_verification_meta_present ? <span className="text-emerald-500">prezentă ✓</span> : <span className="text-red-500">lipsă</span>} · fără metrici fabricate.</div>
      </AdminCard>
    );
  }

  return (
    <div className="space-y-4" data-testid="seo-gsc">
      <FlashBanner />
      <AdminCard>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-500 text-sm font-medium" data-testid="seo-gsc-status"><CheckCircle2 className="w-4 h-4" /> Connected</span>
          <span className={`text-sm ${txt}`} data-testid="seo-gsc-property-label">{status.property}</span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 text-[11px] font-medium" data-testid="seo-gsc-authtype">{status.auth_type === "oauth" ? "OAuth (cont Google)" : "Service Account"}</span>
          {status.service_account_email && <span className={`text-xs ${muted}`}>{status.service_account_email}</span>}
          <div className="ml-auto flex items-center gap-2">
            {["7d", "28d", "3m"].map((r) => (
              <button key={r} onClick={() => setRange(r)} data-testid={`seo-gsc-range-${r}`}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium ${range === r ? "bg-blue-600 text-white" : isDark ? "bg-slate-800 text-slate-300" : "bg-slate-100 text-slate-600"}`}>{r}</button>
            ))}
            <AdminBtn variant="ghost" onClick={disconnect} data-testid="seo-gsc-disconnect">Deconectează</AdminBtn>
          </div>
        </div>
      </AdminCard>

      {reportLoading && <div className={`flex items-center gap-2 text-sm ${muted}`}><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă din Search Console…</div>}
      {report?.status === "error" && <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm px-4 py-3" data-testid="seo-gsc-error">{report.error}</div>}
      {report?.status === "connected" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="seo-gsc-overview">
            <Stat label="Clicks" value={report.overview.clicks} tone="good" />
            <Stat label="Impressions" value={report.overview.impressions} tone="default" />
            <Stat label="CTR" value={`${(report.overview.ctr * 100).toFixed(2)}%`} tone="default" />
            <Stat label="Poziție medie" value={report.overview.position.toFixed(1)} tone="default" />
          </div>
          <div className={`text-xs ${muted}`} data-testid="seo-gsc-range-info">
            Interval: {report.overview.start} → {report.overview.end} · date până la {report.overview.data_through} · actualizat {report.overview.fetched_at ? new Date(report.overview.fetched_at).toLocaleString("ro-RO") : "—"}
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <GscTable title="Top queries" rows={report.queries} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />
            <GscTable title="Top landing pages" rows={report.pages} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />
          </div>
          <GscTable title="Devices" rows={report.devices} txt={txt} muted={muted} border={border} rowBorder={rowBorder} />
        </>
      )}
    </div>
  );
};

const GscTable = ({ title, rows, txt, muted, border, rowBorder }) => (
  <AdminCard title={title}>
    {(!rows || rows.length === 0) ? <div className={`text-sm ${muted}`}>Fără date în perioada selectată.</div> : (
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-sm">
          <thead><tr className={`text-left ${muted} border-b ${rowBorder}`}>
            <th className="px-2 py-1.5 font-medium">Valoare</th><th className="px-2 py-1.5 font-medium">Clicks</th>
            <th className="px-2 py-1.5 font-medium">Impr.</th><th className="px-2 py-1.5 font-medium">CTR</th><th className="px-2 py-1.5 font-medium">Poz.</th>
          </tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={i} className={`border-b ${rowBorder}`}>
              <td className={`px-2 py-1.5 max-w-xs truncate ${txt}`}>{r.key}</td>
              <td className={`px-2 py-1.5 ${txt}`}>{r.clicks}</td>
              <td className={`px-2 py-1.5 ${muted}`}>{r.impressions}</td>
              <td className={`px-2 py-1.5 ${muted}`}>{(r.ctr * 100).toFixed(1)}%</td>
              <td className={`px-2 py-1.5 ${muted}`}>{r.position.toFixed(1)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    )}
  </AdminCard>
);

export default AdminSEO;