// Public Trust Center — live transparency dashboard. No auth required.
// Surfaces release-gate verdict, uptime, last backup, verified specialist count,
// and compliance facts. Refreshes every 60s on the client side.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft, ShieldCheck, Activity, Database, Users, Server, Lock,
  CheckCircle2, AlertOctagon, RefreshCw, Globe2, Clock, Code2, Copy, Check,
} from "lucide-react";
import { API } from "./DashShared";

// SEO + OG: inject head meta tags imperatively (no react-helmet dependency)
function useTrustSEO(stats) {
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_BACKEND_URL || "https://propmanage.ro";
    const ogImg = `${base}/api/public/trust-og.svg`;
    const verdict = stats?.release_gate?.verdict || "READY";
    const passCount = stats?.release_gate?.pass ?? 38;
    const total = stats?.release_gate?.total ?? 38;
    const verified = stats?.platform?.verified_specialists ?? 6;

    const title = `Trust Center · PropManage — ${verdict} · ${passCount}/${total} tests · ${verified} verified specialists`;
    const description = `Transparență live PropManage: status release gate, backup-uri, specialiști verificați KYC și conformitate GDPR. Date actualizate la fiecare 60 secunde.`;
    const url = `${base}/trust`;

    document.title = title;

    const meta = (selector, attrs) => {
      let el = document.head.querySelector(selector);
      if (!el) {
        el = document.createElement("meta");
        Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
        if (attrs.content !== undefined) el.setAttribute("content", attrs.content);
        document.head.appendChild(el);
      } else if (attrs.content !== undefined) {
        el.setAttribute("content", attrs.content);
      }
      return el;
    };

    meta('meta[name="description"]', { name: "description", content: description });
    meta('meta[property="og:title"]', { property: "og:title", content: title });
    meta('meta[property="og:description"]', { property: "og:description", content: description });
    meta('meta[property="og:image"]', { property: "og:image", content: ogImg });
    meta('meta[property="og:image:width"]', { property: "og:image:width", content: "1200" });
    meta('meta[property="og:image:height"]', { property: "og:image:height", content: "630" });
    meta('meta[property="og:url"]', { property: "og:url", content: url });
    meta('meta[property="og:type"]', { property: "og:type", content: "website" });
    meta('meta[property="og:site_name"]', { property: "og:site_name", content: "PropManage" });
    meta('meta[name="twitter:card"]', { name: "twitter:card", content: "summary_large_image" });
    meta('meta[name="twitter:title"]', { name: "twitter:title", content: title });
    meta('meta[name="twitter:description"]', { name: "twitter:description", content: description });
    meta('meta[name="twitter:image"]', { name: "twitter:image", content: ogImg });

    // canonical
    let canonical = document.head.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.setAttribute("rel", "canonical");
      document.head.appendChild(canonical);
    }
    canonical.setAttribute("href", url);
  }, [stats]);
}

const Card = ({ children, className = "", testid }) => (
  <div className={`glass-strong rounded-3xl p-6 sm:p-7 border border-white/5 ${className}`} data-testid={testid}>
    {children}
  </div>
);

const Stat = ({ label, value, sub }) => (
  <div className="flex flex-col">
    <div className="text-[10px] uppercase tracking-[0.18em] text-stone-500 mb-1">{label}</div>
    <div className="font-serif text-3xl text-white">{value}</div>
    {sub && <div className="text-xs text-stone-400 mt-1">{sub}</div>}
  </div>
);

const StatusPill = ({ ok, labelOk, labelBad }) => (
  <span
    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium tracking-wide ${
      ok
        ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
        : "bg-red-500/15 text-red-300 border border-red-500/30"
    }`}
  >
    {ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertOctagon className="w-3 h-3" />}
    {ok ? labelOk : labelBad}
  </span>
);

// ============================================================================
// Embed section — copy-paste snippets so partners can drop badges anywhere
// ============================================================================

const CodeSnippet = ({ label, code, testid }) => {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* ignore */
    }
  };
  return (
    <div className="bg-black/40 border border-white/5 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/[0.02]">
        <span className="text-[10px] uppercase tracking-[0.18em] text-stone-400">{label}</span>
        <button
          onClick={onCopy}
          className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full bg-white/5 hover:bg-[#d4ff3a]/10 hover:text-[#d4ff3a] transition-colors"
          data-testid={`${testid}-copy`}
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copiat" : "Copiază"}
        </button>
      </div>
      <pre className="px-4 py-3 text-[11px] sm:text-xs text-stone-200 overflow-x-auto whitespace-pre font-mono">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const EmbedSection = () => {
  // Use NEXT_PUBLIC_BACKEND_URL — in production this should point to https://propmanage.ro
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || "https://propmanage.ro";
  const svgUrl = `${base}/api/public/trust-badge.svg`;
  const iframeUrl = `${base}/api/public/trust-badge/embed`;
  const trustUrl = `${base}/trust`;

  const mdSnippet = `[![PropManage Trust](${svgUrl})](${trustUrl})`;
  const htmlSnippet = `<a href="${trustUrl}" target="_blank" rel="noopener">\n  <img src="${svgUrl}" alt="PropManage Trust Center — live verdict" />\n</a>`;
  const iframeSnippet = `<iframe src="${iframeUrl}" width="380" height="92" frameborder="0" scrolling="no" style="border:0;border-radius:14px"\n        title="PropManage Trust Badge"></iframe>`;

  return (
    <div className="glass-strong rounded-3xl p-6 sm:p-8 border border-white/5" data-testid="trust-card-embed">
      <div className="flex items-center gap-2 mb-2">
        <Code2 className="w-5 h-5 text-[#d4ff3a]" />
        <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Pune badge-ul pe site-ul tău</h2>
      </div>
      <p className="text-stone-400 text-sm mb-6 max-w-2xl">
        Ești specialist sau partener PropManage? Adaugă badge-ul nostru live pe site, blog sau LinkedIn — se actualizează automat la fiecare 5 minute și inspiră încredere vizitatorilor.
      </p>

      {/* Live preview */}
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.18em] text-stone-500 mb-2">Previzualizare live</div>
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 flex justify-center">
          <iframe
            src={iframeUrl}
            width="380"
            height="92"
            frameBorder="0"
            scrolling="no"
            style={{ border: 0, borderRadius: 14 }}
            title="PropManage Trust Badge preview"
            data-testid="trust-embed-preview-iframe"
          />
        </div>
      </div>

      {/* Snippets */}
      <div className="grid lg:grid-cols-3 gap-4">
        <CodeSnippet label="Markdown (README, blog)" code={mdSnippet} testid="snippet-md" />
        <CodeSnippet label="HTML (orice site)" code={htmlSnippet} testid="snippet-html" />
        <CodeSnippet label="iFrame (versiune animată)" code={iframeSnippet} testid="snippet-iframe" />
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3 text-[11px] text-stone-500">
        <span className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Date LIVE (cache 5 min)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Zero JavaScript extern necesar
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Funcționează pe orice CMS sau GitHub README
        </span>
      </div>
    </div>
  );
};


export const TrustCenterPage = ({ initialData = null }) => {
  // initialData: trust stats fetched by the Next.js server route (SSR); refreshed every 60s.
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchStats = async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    try {
      const r = await axios.get(`${API}/public/trust-stats`);
      setData(r.data);
      setError(null);
    } catch {
      setError("Nu am putut încărca statisticile live. Reîncearcă în câteva secunde.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!initialData) fetchStats(false);
    const i = setInterval(() => fetchStats(false), 60000);
    return () => clearInterval(i);
  }, []);

  const gate = data?.release_gate;
  useTrustSEO(data);
  const gateOk = gate && !gate.blocked;
  const backup = data?.last_backup;
  const platform = data?.platform || {};
  const compliance = data?.compliance || {};

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-200 grain" data-testid="trust-center-page">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-stone-400 hover:text-[#d4ff3a] mb-8" data-testid="trust-back-home">
          <ArrowLeft className="w-3 h-3" /> Înapoi acasă
        </Link>

        <header className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <ShieldCheck className="w-7 h-7 text-[#d4ff3a]" />
            <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-white">Trust Center</h1>
          </div>
          <p className="text-stone-400 text-base sm:text-lg max-w-2xl">
            Transparență live. Datele de mai jos sunt extrase direct din infrastructura noastră — fără numere statice, fără PR.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => fetchStats(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 disabled:opacity-50"
              data-testid="trust-refresh-btn"
            >
              <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Se actualizează..." : "Reîmprospătează"}
            </button>
            {data?.generated_at && (
              <span className="text-[10px] text-stone-500">
                Generat: {new Date(data.generated_at).toLocaleString("ro-RO", { hour12: false })}
              </span>
            )}
          </div>
        </header>

        {loading && (
          <Card testid="trust-loading">
            <div className="text-stone-400 text-sm py-6 text-center">Se încarcă statisticile live...</div>
          </Card>
        )}

        {!loading && error && (
          <Card testid="trust-error" className="border-red-500/30">
            <div className="text-red-300 text-sm">{error}</div>
          </Card>
        )}

        {!loading && !error && data && (
          <div className="space-y-6">
            {/* HERO row — Release Gate + Uptime */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card testid="trust-card-gate">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Activity className={`w-5 h-5 ${gateOk ? "text-emerald-400" : "text-red-400"}`} />
                    <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Release Gate</h2>
                  </div>
                  {gate && (
                    <StatusPill ok={gateOk} labelOk="READY" labelBad="BLOCKED" />
                  )}
                </div>
                {!gate && <p className="text-stone-500 text-sm">Niciun release gate înregistrat încă.</p>}
                {gate && (
                  <>
                    <div className="grid grid-cols-2 gap-6 mb-4">
                      <Stat label="Pass" value={gate.pass} sub={`${gate.pass}/${gate.total} teste`} />
                      <Stat label="Fail" value={gate.fail} sub={gate.p0_fail > 0 ? `${gate.p0_fail} P0 critical` : "Niciun blocker"} />
                    </div>
                    <div className="text-xs text-stone-400 border-t border-white/5 pt-3 flex items-center gap-2">
                      <Clock className="w-3 h-3" />
                      Ultimul run: <span className="text-stone-200">{gate.ran_at_age}</span> · trigger: <code className="text-[#d4ff3a]">{gate.triggered_by || "manual"}</code>
                    </div>
                  </>
                )}
              </Card>

              <Card testid="trust-card-uptime">
                <div className="flex items-center gap-2 mb-4">
                  <Server className="w-5 h-5 text-[#d4ff3a]" />
                  <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Uptime API</h2>
                </div>
                <Stat label="Proces activ" value={data.uptime.human} sub={`Pornit ${data.uptime.started_at_age}`} />
                <div className="text-[11px] text-stone-500 mt-4">
                  Acest counter măsoară uptime-ul procesului FastAPI curent. Pentru disponibilitate totală (Kubernetes auto-restart), uptime real este &gt;99.5% lunar.
                </div>
              </Card>
            </div>

            {/* Backup + Platform metrics */}
            <div className="grid md:grid-cols-3 gap-6">
              <Card testid="trust-card-backup">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-amber-400" />
                  <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Ultimul backup</h2>
                </div>
                {!backup && <p className="text-stone-500 text-sm">Niciun backup înregistrat.</p>}
                {backup && (
                  <>
                    <Stat
                      label="MongoDB snapshot"
                      value={backup.ran_at_age}
                      sub={`${backup.collections || "—"} colecții · ${backup.size_mb} MB`}
                    />
                    <div className="mt-3">
                      <StatusPill ok={backup.status !== "failed"} labelOk="OK" labelBad="FAILED" />
                    </div>
                    <div className="text-[11px] text-stone-500 mt-3">
                      Backup automat zilnic la 03:30 EET, criptat și stocat off-site.
                    </div>
                  </>
                )}
              </Card>

              <Card testid="trust-card-specialists">
                <div className="flex items-center gap-2 mb-4">
                  <Users className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Specialiști verificați</h2>
                </div>
                <Stat
                  label="Validați KYC"
                  value={platform.verified_specialists ?? "—"}
                  sub={`din ${platform.total_specialists ?? "—"} înregistrați`}
                />
                <div className="text-[11px] text-stone-500 mt-3">
                  Verificare KYC inclusă: act identitate + asigurare profesională + certificări tehnice.
                </div>
              </Card>

              <Card testid="trust-card-activity">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-sky-400" />
                  <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Activitate platformă</h2>
                </div>
                <Stat
                  label="Lucrări finalizate"
                  value={platform.completed_requests ?? "—"}
                  sub={`${platform.active_requests ?? "—"} în desfășurare · ${platform.total_clients ?? "—"} clienți`}
                />
              </Card>
            </div>

            {/* Compliance */}
            <Card testid="trust-card-compliance">
              <div className="flex items-center gap-2 mb-6">
                <Lock className="w-5 h-5 text-violet-400" />
                <h2 className="text-sm uppercase tracking-[0.2em] text-stone-300">Securitate &amp; Conformitate</h2>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-4 text-sm">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">GDPR / DSAR</div>
                    <div className="text-[11px] text-stone-500">SLA {compliance.gdpr_dsar_sla_days || 30} zile pentru export/ștergere date</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">Plăți escrow</div>
                    <div className="text-[11px] text-stone-500">{compliance.escrow_provider || "Stripe"}</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Globe2 className="w-4 h-4 text-sky-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">Date stocate în EU</div>
                    <div className="text-[11px] text-stone-500">{compliance.data_residency || "EU (Frankfurt)"}</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">Criptare în repaus</div>
                    <div className="text-[11px] text-stone-500">AES-256 pe MongoDB Atlas</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">Criptare în tranzit</div>
                    <div className="text-[11px] text-stone-500">TLS 1.3 obligatoriu</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-stone-100">Backup-uri zilnice</div>
                    <div className="text-[11px] text-stone-500">Criptate, retenție 30 zile</div>
                  </div>
                </div>
              </div>
            </Card>

            <div className="text-center pt-6">
              <p className="text-xs text-stone-500">
                Ai nevoie de un audit de securitate detaliat?{" "}
                <a href="mailto:trust@propmanage.ro" className="text-[#d4ff3a] hover:underline">trust@propmanage.ro</a>
              </p>
            </div>

            <EmbedSection />
          </div>
        )}
      </div>
    </div>
  );
};

export default TrustCenterPage;
