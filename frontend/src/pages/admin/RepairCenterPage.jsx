// RepairCenterPage — Health Repair Engine (PM-AI-REPAIR-001).
// Fiecare domeniu sub prag: Detector → Reparator → Validator, cu scor before/after.
// Route: /admin/repair-center
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Wrench, ChevronLeft, Loader2, Play, CheckCircle2, AlertTriangle,
  Activity, ArrowRight, HeartPulse, History, Compass, Landmark, Package,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const scoreColor = (s) => (s >= 80 ? "text-emerald-300" : s >= 60 ? "text-amber-300" : "text-rose-300");
const scoreBg = (s) => (s >= 80 ? "bg-emerald-500/10 border-emerald-500/30" : s >= 60 ? "bg-amber-500/10 border-amber-500/30" : "bg-rose-500/10 border-rose-500/30");

const DomainCard = ({ d, onRepair, busy }) => (
  <div className={`rounded-2xl border p-4 flex flex-col gap-3 ${scoreBg(d.score)}`} data-testid={`repair-domain-${d.domain}`}>
    <div className="flex items-center gap-2">
      <span className="text-sm font-semibold text-white">{d.label}</span>
      <div className="flex-1" />
      <span className={`text-2xl font-black ${scoreColor(d.score)}`} data-testid={`repair-score-${d.domain}`}>{Math.round(d.score)}</span>
    </div>
    <div className="text-[11px] text-stone-400">
      {d.last_repair ? (
        <>Ultima reparație: {d.last_repair.problems} probleme · {d.last_repair.actions} acțiuni
          {typeof d.last_repair.delta === "number" && d.last_repair.delta !== 0 && (
            <span className={d.last_repair.delta > 0 ? "text-emerald-300" : "text-rose-300"}> · Δ{d.last_repair.delta > 0 ? "+" : ""}{d.last_repair.delta}</span>
          )}
        </>
      ) : "Nicio reparație încă"}
    </div>
    <button
      onClick={() => onRepair(d.domain)}
      disabled={busy}
      className="mt-auto px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-xs font-medium flex items-center justify-center gap-1.5"
      data-testid={`repair-run-${d.domain}`}
    >
      {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wrench className="w-3 h-3" />} Detectează & Repară
    </button>
  </div>
);

const RunResult = ({ r }) => (
  <div className="border border-stone-800 rounded-2xl p-4 bg-stone-900/30" data-testid={`repair-result-${r.domain}`}>
    <div className="flex items-center gap-2 flex-wrap mb-2">
      <span className="text-sm font-semibold text-white capitalize">{r.domain.replace("_", " ")}</span>
      <span className="text-[11px] px-2 py-0.5 rounded-lg bg-stone-800 text-stone-300">
        scor {Math.round(r.score_before)} <ArrowRight className="w-3 h-3 inline -mt-0.5" /> {Math.round(r.score_after ?? r.score_before)}
      </span>
      {typeof r.delta === "number" && r.delta !== 0 && (
        <span className={`text-[11px] font-bold ${r.delta > 0 ? "text-emerald-300" : "text-rose-300"}`}>Δ{r.delta > 0 ? "+" : ""}{r.delta}</span>
      )}
    </div>
    {r.problems.map((p, i) => (
      <div key={i} className="flex items-start gap-2 text-xs mt-1.5">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
        <div>
          <span className="text-stone-300">{p.detail}</span>
          <span className="text-stone-500"> — {p.root_cause} · </span>
          <code className="text-[10px] text-cyan-300/70">{p.source}</code>
        </div>
      </div>
    ))}
    {r.actions.map((a, i) => (
      <div key={i} className="flex items-start gap-2 text-xs mt-1.5">
        {a.ok ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
          : <AlertTriangle className="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0" />}
        <div><span className="text-stone-200 font-medium">{a.action}</span><span className="text-stone-500"> — {a.detail}</span></div>
      </div>
    ))}
  </div>
);

const SEV_STYLE = {
  critical: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  high: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  medium: "bg-sky-500/15 text-sky-300 border-sky-500/30",
};

const GuardianSection = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    ax.get("/api/admin/repair-center/journey-guardian/status").then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  const run = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/repair-center/journey-guardian/run"); load(); } finally { setBusy(false); }
  };
  return (
    <div className="mt-10" data-testid="journey-guardian-section">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Compass className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Customer Journey Guardian — ochii clientului</div>
        <div className="flex-1" />
        {data?.last_run && (
          <span className="text-[11px] text-stone-500">
            Ultima rulare: {new Date(data.last_run.ts).toLocaleString("ro-RO")} · {data.last_run.issues_found} probleme · {data.resolved_total} rezolvate istoric
          </span>
        )}
        <button onClick={run} disabled={busy}
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5"
          data-testid="guardian-run-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Auditează călătoria
        </button>
      </div>
      {data && (data.open_tasks || []).length === 0 && (
        <div className="p-6 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="guardian-no-tasks">
          Zero fundături, zero link-uri moarte, conținut canonic complet — călătoria clientului e intactă.
        </div>
      )}
      <div className="space-y-2" data-testid="guardian-tasks-list">
        {(data?.open_tasks || []).map(t => (
          <div key={t.key} className="border border-stone-800 rounded-2xl p-4 bg-stone-900/30" data-testid={`guardian-task-${t.key}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded border ${SEV_STYLE[t.severity] || SEV_STYLE.medium}`}>{t.severity}</span>
              <span className="text-sm font-semibold text-white">{t.title}</span>
              <div className="flex-1" />
              <span className="text-[10px] text-stone-500">→ {t.assigned_to}</span>
            </div>
            <p className="text-xs text-stone-400 mt-1.5">{t.detail}</p>
            <p className="text-xs text-stone-500 mt-1"><span className="text-stone-400 font-semibold">Impact:</span> {t.business_impact}</p>
            <p className="text-xs text-emerald-300/70 mt-0.5"><span className="font-semibold">Așteptat:</span> {t.expected}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

const ArchGuardianSection = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    ax.get("/api/admin/repair-center/architecture-guardian/status").then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  const run = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/repair-center/architecture-guardian/run"); load(); } finally { setBusy(false); }
  };
  const score = data?.architecture_score;
  return (
    <div className="mt-10" data-testid="architecture-guardian-section">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Landmark className="w-4 h-4 text-violet-300" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Architecture Guardian — o singură implementare canonică</div>
        {typeof score === "number" && (
          <span className={`text-[11px] font-black px-2 py-0.5 rounded-full border ${score >= 80 ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : score >= 60 ? "bg-amber-500/10 text-amber-300 border-amber-500/30" : "bg-rose-500/10 text-rose-300 border-rose-500/30"}`}
            data-testid="arch-score-badge">Scor {score}/100</span>
        )}
        <div className="flex-1" />
        {data?.last_run && (
          <span className="text-[11px] text-stone-500">
            Ultima rulare: {new Date(data.last_run.ts).toLocaleString("ro-RO")} · {data.last_run.files_scanned} fișiere · {data.last_run.issues_found} probleme · {data.resolved_total} rezolvate istoric
          </span>
        )}
        <button onClick={run} disabled={busy}
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5"
          data-testid="arch-guardian-run-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Scanează arhitectura
        </button>
      </div>
      {data && (data.open_tasks || []).length === 0 && (
        <div className="p-6 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="arch-guardian-no-tasks">
          Zero duplicate, zero cod mort, zero switch-uri temporare — arhitectura e canonică.
        </div>
      )}
      <div className="space-y-2" data-testid="arch-guardian-tasks-list">
        {(data?.open_tasks || []).map(t => (
          <div key={t.key} className="border border-stone-800 rounded-2xl p-4 bg-stone-900/30" data-testid={`arch-task-${t.key}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded border ${SEV_STYLE[t.severity] || SEV_STYLE.medium}`}>{t.severity}</span>
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-stone-800 text-stone-400">risc {t.risk}</span>
              {t.recurrence > 0 && <span className="text-[10px] font-black uppercase px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">regresie ×{t.recurrence}</span>}
              <span className="text-sm font-semibold text-white">{t.title}</span>
              <div className="flex-1" />
              <span className="text-[10px] text-stone-500">→ {t.assigned_to}</span>
            </div>
            <p className="text-xs text-stone-400 mt-1.5">{t.detail}</p>
            <p className="text-xs text-stone-500 mt-1"><span className="text-stone-400 font-semibold">Impact:</span> {t.business_impact}</p>
            {t.migration_plan && <p className="text-xs text-violet-300/70 mt-0.5"><span className="font-semibold">Plan:</span> {t.migration_plan}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};

const ProductGuardianSection = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    ax.get("/api/admin/repair-center/product-guardian/status").then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  const run = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/repair-center/product-guardian/run"); load(); } finally { setBusy(false); }
  };
  const fv = data?.last_run?.first_value;
  const conv = data?.last_run?.conversion;
  return (
    <div className="mt-10" data-testid="product-guardian-section">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Package className="w-4 h-4 text-emerald-300" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Product Guardian — experiența utilizatorului</div>
        {typeof data?.product_score === "number" && (
          <span className={`text-[11px] font-black px-2 py-0.5 rounded-full border ${data.product_score >= 80 ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : data.product_score >= 60 ? "bg-amber-500/10 text-amber-300 border-amber-500/30" : "bg-rose-500/10 text-rose-300 border-rose-500/30"}`}
            data-testid="product-score-badge">Produs {data.product_score}/100</span>
        )}
        {typeof data?.platform_score === "number" && (
          <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-stone-800 text-stone-300 border border-stone-700" data-testid="platform-score-badge">
            Platformă {data.platform_score}/100
          </span>
        )}
        <div className="flex-1" />
        <button onClick={run} disabled={busy}
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5"
          data-testid="product-guardian-run-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Auditează produsul
        </button>
      </div>
      {data?.ceo_summary && (
        <div className="mb-3 px-4 py-2.5 rounded-xl bg-stone-900/60 border border-stone-800 text-xs text-stone-300" data-testid="product-ceo-summary">
          <span className="font-bold text-stone-400 uppercase text-[10px] mr-2">CEO Summary</span>{data.ceo_summary}
        </div>
      )}
      {(fv || conv) && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4" data-testid="product-funnel-stats">
          {fv && <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 text-center"><div className="text-lg font-black text-white">{fv.pct_property}%</div><div className="text-[10px] text-stone-500 uppercase">clienți cu proprietate</div></div>}
          {fv && <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 text-center"><div className="text-lg font-black text-white">{fv.pct_request}%</div><div className="text-[10px] text-stone-500 uppercase">clienți cu cerere</div></div>}
          {fv && <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 text-center"><div className="text-lg font-black text-white">{fv.pct_paid}%</div><div className="text-[10px] text-stone-500 uppercase">clienți care au plătit</div></div>}
          {conv && <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 text-center"><div className="text-lg font-black text-white">{conv.landing_to_auth_pct}%</div><div className="text-[10px] text-stone-500 uppercase">landing → auth (30z)</div></div>}
        </div>
      )}
      {data && (data.open_tasks || []).length === 0 && (
        <div className="p-6 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="product-guardian-no-tasks">
          Zero CTA moarte, roluri consistente, gate-uri valide — experiența de produs e intactă.
        </div>
      )}
      <div className="space-y-2" data-testid="product-guardian-tasks-list">
        {(data?.open_tasks || []).map(t => (
          <div key={t.key} className="border border-stone-800 rounded-2xl p-4 bg-stone-900/30" data-testid={`product-task-${t.key}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded border ${SEV_STYLE[t.severity] || SEV_STYLE.medium}`}>{t.severity}</span>
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-stone-800 text-stone-400">risc {t.risk}</span>
              {t.recurrence > 0 && <span className="text-[10px] font-black uppercase px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">regresie ×{t.recurrence}</span>}
              <span className="text-sm font-semibold text-white">{t.title}</span>
              <div className="flex-1" />
              <span className="text-[10px] text-stone-500">→ {t.assigned_to}</span>
            </div>
            <p className="text-xs text-stone-400 mt-1.5">{t.detail}</p>
            <p className="text-xs text-stone-500 mt-1"><span className="text-stone-400 font-semibold">Impact:</span> {t.business_impact}</p>
            {t.migration_plan && <p className="text-xs text-emerald-300/70 mt-0.5"><span className="font-semibold">Plan:</span> {t.migration_plan}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};

export default function RepairCenterPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [lastRun, setLastRun] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await ax.get("/api/admin/repair-center/status");
      setStatus(r.data);
      setLastRun(r.data.last_run);
    } catch (e) {
      setMsg(`❌ ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (domain) => {
    setBusy(true);
    setMsg(null);
    const prevTs = lastRun?.ts;
    try {
      await ax.post("/api/admin/repair-center/run", domain ? { domains: [domain] } : {});
      setMsg("⏳ Ciclul rulează în fundal (detect → repair → validate)...");
      for (let i = 0; i < 60; i++) {
        await new Promise(res => setTimeout(res, 3000));
        const rr = await ax.get("/api/admin/repair-center/runs", { params: { limit: 1 } }).catch(() => null);
        const nr = rr?.data?.items?.[0];
        if (nr && nr.ts !== prevTs) {
          setLastRun(nr);
          setMsg(`✅ Ciclu finalizat: ${nr.domains_repaired} domenii · ${nr.total_problems} probleme detectate · ${nr.total_actions} acțiuni executate.`);
          const s = await ax.get("/api/admin/repair-center/status").catch(() => null);
          if (s) setStatus(s.data);
          break;
        }
      }
    } catch (e) {
      setMsg(`❌ ${e?.response?.data?.detail || e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8" data-testid="repair-center-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-6">
          <Link to="/admin" className="text-stone-500 hover:text-white flex items-center gap-1 text-sm" data-testid="repair-back-link">
            <ChevronLeft className="w-4 h-4" /> Admin
          </Link>
          <span className="text-stone-700">·</span>
          <HeartPulse className="w-5 h-5 text-violet-400" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">Health Repair Engine</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">Detect → Repair → Validate</span>
          {status?.autonomy && (
            <span className="text-[11px] font-black px-2.5 py-1 rounded-full bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/30"
              title={Object.values(status.autonomy.components).map(c => c.detail).join(" · ")}
              data-testid="autonomy-score-badge">
              Autonomie {status.autonomy.score}/100
            </span>
          )}
          <div className="flex-1" />
          <Link to="/admin/enterprise-health" className="px-3 py-1.5 text-xs rounded-lg border border-stone-700 text-stone-300 hover:text-white flex items-center gap-1.5" data-testid="repair-to-health">
            <Activity className="w-3.5 h-3.5" /> Enterprise Health
          </Link>
          <button onClick={() => run(null)} disabled={busy}
            className="px-4 py-1.5 text-xs rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-semibold flex items-center gap-1.5"
            data-testid="repair-run-all">
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Rulează ciclul complet
          </button>
        </div>

        {msg && <div className="mb-4 px-4 py-2.5 rounded-xl bg-stone-900/60 border border-stone-700 text-sm text-stone-200" data-testid="repair-message">{msg}</div>}

        {loading && !status ? (
          <div className="p-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-stone-500" /></div>
        ) : status && (
          <>
            <div className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
              Domenii · fiecare scor are Detector + Reparator + Validator ({status.runs_total} cicluri rulate)
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8" data-testid="repair-domains-grid">
              {status.domains.map(d => <DomainCard key={d.domain} d={d} onRepair={run} busy={busy} />)}
            </div>

            {lastRun && (lastRun.results || []).length > 0 && (
              <>
                <div className="flex items-center gap-2 mb-3">
                  <History className="w-3.5 h-3.5 text-stone-500" />
                  <div className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Ultima rulare · {new Date(lastRun.ts).toLocaleString("ro-RO")} · trigger: {lastRun.trigger}
                  </div>
                </div>
                <div className="space-y-3" data-testid="repair-last-run">
                  {lastRun.results.map(r => <RunResult key={r.domain} r={r} />)}
                </div>
              </>
            )}
            {lastRun && (lastRun.results || []).length === 0 && (
              <div className="p-10 text-center text-sm text-stone-500 border border-dashed border-stone-800 rounded-2xl" data-testid="repair-no-results">
                Toate domeniile sunt peste prag — nimic de reparat în ultima rulare.
              </div>
            )}
            <GuardianSection />
            <ArchGuardianSection />
            <ProductGuardianSection />
          </>
        )}
      </div>
    </div>
  );
}
