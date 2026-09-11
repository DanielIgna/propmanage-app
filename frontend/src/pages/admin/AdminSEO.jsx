// Admin → SEO Control Center — READ-ONLY observability over the existing SEO SSOT.
// Reuses the backend /api/admin/seo/* endpoints (which themselves reuse the gate,
// sitemap builders and db.pages). No SEO logic is duplicated here.
import React, { useState, useCallback } from "react";
import axios from "axios";
import {
  Search, Globe, FileText, ListChecks, Layers, AlertTriangle, BarChart3,
  RefreshCw, CheckCircle2, XCircle, ExternalLink, Loader2, Eye, ShieldCheck,
  MapPin, Building2, Gauge,
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
  const [tab, setTab] = useState("overview");
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
    if (tab === "inspector") return; // inspector is on-demand
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
      {tab === "gsc" && data && (
        <AdminCard title="Google Search Console" testid="seo-gsc">
          <div className="flex items-center gap-2 mb-4">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-500/15 text-slate-400 text-sm font-medium" data-testid="seo-gsc-status">
              <XCircle className="w-4 h-4" /> Not connected
            </span>
          </div>
          <p className={`text-sm ${txt} max-w-2xl`}>{data.message}</p>
          <div className={`mt-4 grid grid-cols-2 md:grid-cols-3 gap-3 opacity-50 pointer-events-none`}>
            {["Impressions", "Clicks", "CTR", "Poziție medie", "Queries", "Landing pages"].map((m) => (
              <div key={m} className={`rounded-lg border border-dashed p-3 ${border}`}>
                <div className={`text-xs ${muted}`}>{m}</div>
                <div className={`text-lg font-bold ${muted}`}>—</div>
              </div>
            ))}
          </div>
          <div className={`text-xs mt-4 ${muted}`}>
            Meta de verificare site: {data.site_verification_meta_present ? <span className="text-emerald-500">prezentă ✓</span> : <span className="text-red-500">lipsă</span>}
            {data.site_verification_token && <span className="font-mono opacity-60"> ({data.site_verification_token.slice(0, 12)}…)</span>}
            <br />Modelul de date este pregătit pentru conectare ulterioară — fără metrici fabricate.
          </div>
        </AdminCard>
      )}
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

export default AdminSEO;
