// /admin/auth-health — real-time Google OAuth health metrics.
// Admin only. Auto-refresh every 30s.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, ArrowLeft, CheckCircle2, Clock, Download, Mail, RefreshCw, Users, Zap } from "lucide-react";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const OUTCOME_LABEL = {
  success: { label: "Reușite", color: "emerald" },
  user_error: { label: "Eroare user", color: "amber" },
  upstream_5xx: { label: "5xx upstream", color: "orange" },
  network: { label: "Rețea", color: "red" },
  exhausted: { label: "Retry epuizat", color: "red" },
  unknown: { label: "Necunoscut", color: "stone" },
};

const ColorChip = ({ color, children, "data-testid": testId }) => {
  const cls = {
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    orange: "bg-orange-500/15 text-orange-300 border-orange-500/30",
    red: "bg-red-500/15 text-red-300 border-red-500/30",
    stone: "bg-stone-500/15 text-stone-300 border-stone-500/30",
  }[color] || "bg-stone-500/15 text-stone-300 border-stone-500/30";
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border ${cls}`} data-testid={testId}>{children}</span>;
};

// Inline SVG sparkline — no chart libs needed. Shows hourly success rate over 24h.
// Color per bar: green (≥95%), amber (80-95%), red (<80%), stone (no data).
const Sparkline24h = ({ buckets }) => {
  const W = 900;
  const H = 110;
  const PAD_X = 8;
  const PAD_Y = 20;
  const BAR_GAP = 3;
  const n = buckets.length || 24;
  const barW = (W - PAD_X * 2 - BAR_GAP * (n - 1)) / n;
  const chartH = H - PAD_Y - 18; // top padding + bottom label space
  const colorFor = (r) => {
    if (r === null || r === undefined) return "#3f3f46";
    if (r >= 95) return "#34d399";
    if (r >= 80) return "#fbbf24";
    return "#ef4444";
  };
  const points = buckets.map((b, i) => {
    const x = PAD_X + i * (barW + BAR_GAP) + barW / 2;
    const r = b.success_rate_pct;
    const y = r === null ? PAD_Y + chartH : PAD_Y + chartH - (r / 100) * chartH;
    return { x, y, r, label: b.hour_label, total: b.total };
  });
  // Line path connecting samples that have data
  const dataPoints = points.filter(p => p.r !== null);
  const pathD = dataPoints.length > 1
    ? dataPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")
    : "";
  return (
    <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="auth-health-sparkline">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-stone-300 flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#d4ff3a]" /> Success rate · ultimele 24h
        </h2>
        <div className="flex items-center gap-3 text-[10px] text-stone-500">
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400" />≥95%</span>
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />80-95%</span>
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />&lt;80%</span>
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-stone-600" />fără date</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="none">
        {/* 80% threshold guide line */}
        <line x1={PAD_X} y1={PAD_Y + chartH - 0.8 * chartH} x2={W - PAD_X} y2={PAD_Y + chartH - 0.8 * chartH}
              stroke="#fbbf24" strokeWidth="1" strokeDasharray="3 4" opacity="0.4" />
        <text x={PAD_X + 4} y={PAD_Y + chartH - 0.8 * chartH - 3} fill="#fbbf24" fontSize="9" opacity="0.7">80% threshold</text>
        {/* Trend line over data points */}
        {pathD && <path d={pathD} fill="none" stroke="#d4ff3a" strokeWidth="1.5" opacity="0.45" />}
        {/* Bars (success rate height) */}
        {points.map((p, i) => {
          const r = p.r;
          const x0 = PAD_X + i * (barW + BAR_GAP);
          const fullH = chartH;
          const valH = r === null ? 0 : (r / 100) * chartH;
          return (
            <g key={i}>
              <rect x={x0} y={PAD_Y} width={barW} height={fullH} fill="#27272a" opacity="0.5" rx="1.5" />
              {r !== null && (
                <rect
                  x={x0}
                  y={PAD_Y + chartH - valH}
                  width={barW}
                  height={valH}
                  fill={colorFor(r)}
                  rx="1.5"
                >
                  <title>{`${p.label} · ${p.total} req · ${r}% success`}</title>
                </rect>
              )}
              {/* Hour label every 4 hours */}
              {i % 4 === 0 && (
                <text x={x0 + barW / 2} y={H - 4} fill="#71717a" fontSize="9" textAnchor="middle">{p.label}</text>
              )}
              {/* Dot for active hours */}
              {r !== null && (
                <circle cx={p.x} cy={p.y} r="2" fill={colorFor(r)} stroke="#0a0a0a" strokeWidth="1" />
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex items-center justify-between text-[10px] text-stone-500">
        <span>Cel mai vechi · {buckets[0]?.hour_label || "—"}</span>
        <span data-testid="sparkline-active-hours">
          Ore cu activitate: {points.filter(p => p.r !== null).length} / {n}
        </span>
        <span>Acum · {buckets[buckets.length - 1]?.hour_label || "—"}</span>
      </div>
    </div>
  );
};

export const AdminAuthHealthPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/admin/auth-health`);
      setData(r.data);
      setErr(null);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const exportCsv = () => {
    // Browser handles auth cookies; opens download dialog
    window.open(`${API}/admin/auth-health/export.csv`, "_blank");
  };

  const sendTestAlert = async () => {
    if (!window.confirm("Trimite un email de test către toți adminii?")) return;
    try {
      const r = await axios.post(`${API}/admin/auth-health/test-alert`);
      alert(
        r.data?.sent
          ? `✓ Email trimis către ${r.data.recipients} admin(i).`
          : `Skipped: ${r.data?.reason || "necunoscut"}`
      );
    } catch (e) {
      alert("Eroare: " + (e?.response?.data?.detail || e.message));
    }
  };
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  if (loading) return <div className="min-h-screen bg-stone-950 text-stone-400 flex items-center justify-center" data-testid="auth-health-loading">Se încarcă…</div>;
  if (err) return <div className="min-h-screen bg-stone-950 text-red-300 p-8" data-testid="auth-health-error">Eroare: {err}</div>;

  const succRate = data.success_rate_pct;
  const succColor = succRate === null ? "stone" : succRate >= 95 ? "emerald" : succRate >= 80 ? "amber" : "red";
  const lat = data.latency_ms || {};
  const buckets = data.hourly_buckets || [];

  return (
    <div className="min-h-screen bg-stone-950 text-white p-6 lg:p-10" data-testid="admin-auth-health-page">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Link to="/admin" className="inline-flex items-center gap-2 text-xs text-stone-500 hover:text-white mb-2">
              <ArrowLeft className="w-3 h-3" /> Admin Dashboard
            </Link>
            <h1 className="font-serif text-3xl flex items-center gap-3" data-testid="auth-health-title">
              <Activity className="w-7 h-7 text-[#d4ff3a]" />
              Google OAuth · Sănătate Auth
            </h1>
            <p className="text-stone-500 text-sm mt-1">Statistici real-time pentru endpoint-ul <code className="text-stone-400">/api/auth/google/session</code> · refresh la 30s</p>
          </div>
          <button onClick={load} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-xs" data-testid="auth-health-refresh">
            <RefreshCw className="w-3 h-3" /> Refresh acum
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 -mt-2">
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-xs text-emerald-300"
            data-testid="auth-health-export-csv"
          >
            <Download className="w-3 h-3" /> Export CSV (24h)
          </button>
          <button
            onClick={sendTestAlert}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-xs text-amber-300"
            data-testid="auth-health-test-alert"
            title="Forțează un email de alertă către toți adminii (skip threshold + cooldown)"
          >
            <Mail className="w-3 h-3" /> Trimite test email alert
          </button>
          <div className="text-[10px] text-stone-500 self-center ml-2">
            ⚙️ Alertă automată: email când success rate &lt; 80% în ultima oră (cooldown 60min)
          </div>
        </div>

        {/* Sparkline graph — 24h hourly success rate trend */}
        <Sparkline24h buckets={buckets} />

        {/* KPI cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="kpi-total">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500"><Users className="w-3 h-3" /> Total 24h</div>
            <div className="text-3xl font-serif mt-2">{data.total_attempts}</div>
          </div>
          <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="kpi-success">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500"><CheckCircle2 className="w-3 h-3" /> Rata succes</div>
            <div className={`text-3xl font-serif mt-2 ${succColor === "emerald" ? "text-emerald-300" : succColor === "amber" ? "text-amber-300" : succColor === "red" ? "text-red-300" : "text-stone-300"}`}>
              {succRate === null ? "—" : `${succRate}%`}
            </div>
            <div className="text-[10px] text-stone-500 mt-1">{data.outcomes?.success || 0} din {data.total_attempts}</div>
          </div>
          <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="kpi-p95">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500"><Clock className="w-3 h-3" /> P95 latență</div>
            <div className="text-3xl font-serif mt-2">{lat.p95 != null ? `${lat.p95}ms` : "—"}</div>
            <div className="text-[10px] text-stone-500 mt-1">P50: {lat.p50 ?? "—"}ms · P99: {lat.p99 ?? "—"}ms</div>
          </div>
          <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="kpi-5xx" title="Erori 5xx primite de la upstream Emergent OAuth — pot indica probleme la providerul de autentificare">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500"><AlertTriangle className="w-3 h-3" /> Upstream 5xx</div>
            <div className={`text-3xl font-serif mt-2 ${data.upstream_5xx_count > 0 ? "text-orange-300" : "text-stone-300"}`}>{data.upstream_5xx_count}</div>
            <div className="text-[10px] text-stone-500 mt-1">
              <span className={data.upstream_5xx_count_1h > 0 ? "text-orange-400" : ""}>{data.upstream_5xx_count_1h || 0} în ultima oră</span> · Emergent OAuth
            </div>
          </div>
          <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="kpi-gateway" title="Gateway errors (502/504/520-524) observate de browser-ul utilizatorilor — indică probleme la Kubernetes ingress / Cloudflare pe propmanage.ro, NU la upstream Emergent">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500"><AlertTriangle className="w-3 h-3" /> Gateway errs</div>
            <div className={`text-3xl font-serif mt-2 ${data.gateway_errors_count > 0 ? "text-red-300" : "text-stone-300"}`}>{data.gateway_errors_count || 0}</div>
            <div className="text-[10px] text-stone-500 mt-1">
              <span className={data.gateway_errors_count_1h > 0 ? "text-red-400" : ""}>{data.gateway_errors_count_1h || 0} în ultima oră</span> · K8s/Cloudflare
            </div>
          </div>
        </div>

        {/* Diagnostic banner when gateway errors present */}
        {data.gateway_errors_count_1h > 0 && (
          <div className="rounded-2xl bg-red-500/5 border border-red-500/30 p-4 flex items-start gap-3" data-testid="gateway-alert-banner">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              <div className="text-red-300 font-medium mb-1">
                ⚠️ {data.gateway_errors_count_1h} gateway error{data.gateway_errors_count_1h !== 1 ? "s" : ""} în ultima oră
              </div>
              <p className="text-stone-400 text-xs leading-relaxed">
                Utilizatorii primesc 502/504/520-524 înainte ca request-ul să ajungă la backend.
                <strong className="text-red-300"> Problema NU e la Emergent OAuth — e la ingress-ul tău Kubernetes sau la Cloudflare pe propmanage.ro.</strong>
                {" "}Acțiuni: verifică <code className="text-stone-300 bg-white/5 px-1 rounded">kubectl get pods</code>, restartează backend pod dacă e crash-loop, sau verifică status.cloudflare.com.
              </p>
            </div>
          </div>
        )}

        {/* Outcomes breakdown */}
        <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5">
          <h2 className="text-sm font-medium text-stone-300 mb-3 flex items-center gap-2"><Zap className="w-4 h-4 text-[#d4ff3a]" /> Distribuție rezultate</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.outcomes || {}).length === 0 && <span className="text-xs text-stone-500">Niciun event în ultimele 24h.</span>}
            {Object.entries(data.outcomes || {}).map(([key, count]) => {
              const meta = OUTCOME_LABEL[key] || OUTCOME_LABEL.unknown;
              return (
                <ColorChip key={key} color={meta.color} data-testid={`outcome-${key}`}>
                  <span>{meta.label}</span>
                  <span className="font-mono ml-1">{count}</span>
                </ColorChip>
              );
            })}
          </div>
        </div>

        {/* Recent 5xx incidents */}
        {data.recent_upstream_5xx?.length > 0 && (
          <div className="rounded-2xl bg-orange-500/5 border border-orange-500/20 p-5" data-testid="upstream-5xx-list">
            <h2 className="text-sm font-medium text-orange-300 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Erori Emergent OAuth 5xx (ultimele 10)
            </h2>
            <table className="w-full text-xs">
              <thead className="text-stone-500 uppercase text-[10px]">
                <tr className="border-b border-white/5">
                  <th className="text-left py-1.5">Timp</th>
                  <th className="text-left py-1.5">Status</th>
                  <th className="text-left py-1.5">Încercări</th>
                  <th className="text-left py-1.5">Rezultat final</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_upstream_5xx.map((e, i) => (
                  <tr key={i} className="border-b border-white/5 last:border-b-0">
                    <td className="py-1.5 text-stone-400">{new Date(e.started_at).toLocaleString("ro-RO")}</td>
                    <td className="py-1.5 text-orange-300 font-mono">HTTP {e.upstream_status}</td>
                    <td className="py-1.5 text-stone-400">{e.attempts}/3</td>
                    <td className="py-1.5"><ColorChip color={OUTCOME_LABEL[e.outcome]?.color || "stone"}>{OUTCOME_LABEL[e.outcome]?.label || e.outcome}</ColorChip></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Recent events */}
        <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid="recent-events-list">
          <h2 className="text-sm font-medium text-stone-300 mb-3">Ultimele 20 events</h2>
          {data.recent_events?.length === 0 ? (
            <div className="text-xs text-stone-500">Niciun event în ultimele 24h.</div>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-stone-500 uppercase text-[10px]">
                <tr className="border-b border-white/5">
                  <th className="text-left py-1.5">Timp</th>
                  <th className="text-left py-1.5">Rezultat</th>
                  <th className="text-left py-1.5">Status</th>
                  <th className="text-left py-1.5">Durată</th>
                  <th className="text-left py-1.5">Email</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_events.map((e, i) => (
                  <tr key={e._id || i} className="border-b border-white/5 last:border-b-0">
                    <td className="py-1.5 text-stone-400 whitespace-nowrap">{new Date(e.started_at).toLocaleString("ro-RO")}</td>
                    <td className="py-1.5"><ColorChip color={OUTCOME_LABEL[e.outcome]?.color || "stone"}>{OUTCOME_LABEL[e.outcome]?.label || e.outcome}</ColorChip></td>
                    <td className="py-1.5 text-stone-400 font-mono">{e.final_status || "—"}</td>
                    <td className="py-1.5 text-stone-400">{e.duration_ms != null ? `${e.duration_ms}ms` : "—"}</td>
                    <td className="py-1.5 text-stone-500 truncate max-w-[200px]">{e.email || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminAuthHealthPage;
