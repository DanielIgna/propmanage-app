// AIGovernancePage — Phase 1 observability-only dashboard.
//
// Single pane of glass for all AI agents: registry, costs, audit trail.
// READ-ONLY. No agent modifications possible from this UI.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Shield, ChevronLeft, Loader2, Brain, Activity, Coins,
  History, AlertTriangle, Users, Eye, Sparkles,
  ArchiveRestore, CheckCircle2, ArchiveX, CalendarClock,
  RotateCcw, X, HeartPulse, KeyRound, Mail, Bell,
} from "lucide-react";
import { AIInsightCard } from "../../design-system";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const LIFECYCLE_COLOR = {
  active:       "bg-emerald-500/10 border-emerald-500/40 text-emerald-300",
  legacy:       "bg-amber-500/10 border-amber-500/40 text-amber-300",
  experimental: "bg-blue-500/10 border-blue-500/40 text-blue-300",
  deprecated:   "bg-red-500/10 border-red-500/40 text-red-300",
};

const PERMISSION_COLOR = {
  read:                       "bg-stone-500/10 border-stone-500/40 text-stone-300",
  suggest:                    "bg-blue-500/10 border-blue-500/40 text-blue-300",
  "execute-with-approval":    "bg-amber-500/10 border-amber-500/40 text-amber-300",
  execute:                    "bg-emerald-500/10 border-emerald-500/40 text-emerald-300",
  autonomous:                 "bg-violet-500/10 border-violet-500/40 text-violet-300",
};

const CATEGORY_LABEL = {
  control_plane:  "Control Plane",
  development:    "Development",
  quality:        "Quality",
  security:       "Security",
  knowledge:      "Knowledge",
  memory:         "Memory",
  reporting:      "Reporting",
  marketplace:    "Marketplace",
  concierge:      "Concierge",
  investigation:  "Investigation",
};

const TABS = [
  { id: "agents",      label: "Agenți",            icon: Users },
  { id: "health",      label: "Health",            icon: HeartPulse },
  { id: "permissions", label: "Permissions",       icon: KeyRound },
  { id: "costs",       label: "Costuri",           icon: Coins },
  { id: "audit",       label: "Audit Trail",       icon: History },
  { id: "deprecation", label: "Deprecation Plan",  icon: ArchiveX },
  { id: "pulse",       label: "Deprecation Pulse", icon: Bell },
];

const AIGovernancePage = () => {
  const [tab, setTab] = useState("agents");
  const [summary, setSummary] = useState(null);
  const [agents, setAgents] = useState([]);
  const [costs, setCosts] = useState(null);
  const [audit, setAudit] = useState([]);
  const [depPlan, setDepPlan] = useState(null);
  const [health, setHealth] = useState(null);
  const [perms, setPerms] = useState(null);
  const [pulseCfg, setPulseCfg] = useState(null);
  const [pulsePreview, setPulsePreview] = useState(null);
  const [pulseHistory, setPulseHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [depModal, setDepModal] = useState(null);  // agent obj being deprecated
  const [busy, setBusy] = useState(false);
  const [insights, setInsights] = useState(null);

  const refresh = async () => {
    const [s, a, c, au, dp, h, pm, pc, pp, ph] = await Promise.all([
      ax.get("/api/admin/ai-governance/summary"),
      ax.get("/api/admin/ai-governance/agents"),
      ax.get("/api/admin/ai-governance/costs"),
      ax.get("/api/admin/ai-governance/audit-trail"),
      ax.get("/api/admin/ai-governance/deprecation-plan"),
      ax.get("/api/admin/ai-governance/health"),
      ax.get("/api/admin/ai-governance/permissions-matrix"),
      ax.get("/api/admin/deprecation-pulse/config"),
      ax.get("/api/admin/deprecation-pulse/preview"),
      ax.get("/api/admin/deprecation-pulse/history?limit=10"),
    ]);
    setSummary(s.data);
    setAgents(a.data.agents || []);
    setCosts(c.data);
    setAudit(au.data.events || []);
    setDepPlan(dp.data);
    setHealth(h.data);
    setPerms(pm.data);
    setPulseCfg(pc.data);
    setPulsePreview(pp.data);
    setPulseHistory(ph.data.items || []);
  };

  useEffect(() => {
    (async () => {
      try { await refresh(); }
      finally { setLoading(false); }
    })();
    ax.get("/api/admin/insights/rule?module=governance").then(r => setInsights(r.data)).catch(() => {});
  }, []);

  const handleDeprecate = async (form) => {
    setBusy(true);
    try {
      await ax.post(`/api/admin/ai-governance/agents/${depModal.slug}/deprecate`, form);
      setDepModal(null);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare la marcarea ca depreciat.");
    } finally {
      setBusy(false);
    }
  };

  const handleRestore = async (slug) => {
    if (!window.confirm(`Restaurezi agentul "${slug}" din planul de deprecation?`)) return;
    setBusy(true);
    try {
      await ax.post(`/api/admin/ai-governance/agents/${slug}/undeprecate`, {});
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const savePulseConfig = async (patch) => {
    setBusy(true);
    try {
      const { data } = await ax.put("/api/admin/deprecation-pulse/config", patch);
      setPulseCfg(data);
    } finally {
      setBusy(false);
    }
  };

  const sendPulseNow = async () => {
    if (!window.confirm("Trimit acum Deprecation Pulse către destinatarii configurați?")) return;
    setBusy(true);
    try {
      const { data } = await ax.post("/api/admin/deprecation-pulse/send-now", {});
      if (data.skipped) {
        alert(`Trimitere săritată: ${data.skipped}`);
      } else if (!data.ok) {
        alert(`Eroare email: ${data.error || "unknown"}`);
      } else {
        alert(`Pulse trimis. ${data.subject}`);
      }
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="gov-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5 text-violet-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="gov-title">
              AI <span className="italic gradient-text">Governance</span> Center
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Observability layer over the entire AI ecosystem. <strong>Read-only Phase 1</strong> — agenții nu pot fi modificați de aici.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="text-center text-stone-400 flex items-center justify-center gap-2 py-10">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă ecosistemul...
          </div>
        ) : (
          <>
            {/* SUMMARY KPIs */}
            {summary && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6" data-testid="gov-summary">
                <KPI label="Agenți activi" value={summary.by_lifecycle?.active || 0} icon={Brain} color="emerald" />
                <KPI label="Legacy" value={summary.by_lifecycle?.legacy || 0} icon={ArchiveRestore} color="amber" />
                <KPI label="Activitate 24h" value={summary.global_activity_24h} icon={Activity} color="violet" />
                <KPI label="Activitate 7d" value={summary.global_activity_7d} icon={Activity} color="blue" />
                <KPI label="Cost lunar est." value={`~${costs?.estimated_total_monthly_eur ?? 0}€`} icon={Coins} color="amber" />
              </div>
            )}

            {/* PHASE BANNER */}
            <div className="rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4 mb-6 flex items-start gap-3" data-testid="gov-phase-banner">
              <Eye className="w-5 h-5 text-violet-300 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs text-stone-300">
                <strong className="text-violet-200">{summary?.phase}</strong> — {summary?.note}
              </div>
            </div>

            {/* AI Insights v2 — rule-based + LLM (Claude) */}
            <div className="mb-6">
              <AIInsightCard
                bullets={insights?.bullets || []} alerts={insights?.alerts || []}
                recommendations={insights?.recommendations || []}
                loading={!insights} llmModule="governance" testid="governance-insights"
              />
            </div>

            {/* TABS */}
            <div className="flex flex-wrap gap-2 mb-4">
              {TABS.map(t => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm border transition-colors ${
                      tab === t.id ? "bg-white/10 border-white/30 text-white" : "bg-[#0e0e10] border-white/10 text-stone-400 hover:text-white"
                    }`}
                    data-testid={`gov-tab-${t.id}`}
                  >
                    <Icon className="w-4 h-4" /> {t.label}
                  </button>
                );
              })}
            </div>

            <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6">
              {tab === "agents"      && <AgentsTab agents={agents} onDeprecate={setDepModal} onRestore={handleRestore} />}
              {tab === "health"      && <HealthTab health={health} />}
              {tab === "permissions" && <PermissionsTab perms={perms} />}
              {tab === "costs"       && <CostsTab costs={costs} />}
              {tab === "audit"       && <AuditTab events={audit} />}
              {tab === "deprecation" && <DeprecationTab plan={depPlan} onRestore={handleRestore} onDeprecate={(slug) => {
                const agent = agents.find(a => a.slug === slug);
                if (agent) setDepModal(agent);
              }} />}
              {tab === "pulse"       && <PulseTab cfg={pulseCfg} preview={pulsePreview} history={pulseHistory} onSave={savePulseConfig} onSendNow={sendPulseNow} busy={busy} />}
            </div>
          </>
        )}

        {depModal && (
          <DeprecateModal
            agent={depModal}
            onClose={() => setDepModal(null)}
            onSubmit={handleDeprecate}
            busy={busy}
          />
        )}
      </div>
    </div>
  );
};

const KPI = ({ label, value, icon: Icon, color }) => {
  const cls = {
    emerald: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    amber:   "border-amber-500/30 bg-amber-500/5 text-amber-300",
    violet:  "border-violet-500/30 bg-violet-500/5 text-violet-300",
    blue:    "border-blue-500/30 bg-blue-500/5 text-blue-300",
  }[color];
  return (
    <div className={`rounded-xl border p-4 ${cls}`}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider">{label}</div>
        <Icon className="w-4 h-4 opacity-60" />
      </div>
      <div className="text-2xl font-mono mt-2 text-white">{value}</div>
    </div>
  );
};

const AgentsTab = ({ agents, onDeprecate, onRestore }) => {
  // Group by category
  const grouped = agents.reduce((acc, a) => {
    (acc[a.category] = acc[a.category] || []).push(a);
    return acc;
  }, {});
  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([cat, list]) => (
        <div key={cat} data-testid={`gov-cat-${cat}`}>
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">{CATEGORY_LABEL[cat] || cat} ({list.length})</h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {list.map(a => (
              <div key={a.slug} className="bg-white/[0.02] border border-white/10 rounded-xl p-4" data-testid={`gov-agent-${a.slug}`}>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-mono text-[10px] text-stone-500">{a.slug}</span>
                  <span className={`inline-block text-[10px] uppercase px-1.5 py-0.5 rounded border ${LIFECYCLE_COLOR[a.lifecycle]}`}>{a.lifecycle}</span>
                  <span className={`inline-block text-[10px] uppercase px-1.5 py-0.5 rounded border ${PERMISSION_COLOR[a.permission_level]}`}>{a.permission_level}</span>
                </div>
                <div className="text-sm font-semibold text-white">{a.name}</div>
                <div className="text-xs text-stone-400 mt-1">{a.purpose}</div>
                {a.deprecation && (
                  <div className="mt-2 rounded-lg bg-red-500/5 border border-red-500/30 px-2.5 py-2 text-[11px] text-red-200">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <ArchiveX className="w-3 h-3" /> <strong>Depreciat</strong>
                      {a.deprecation.target_retirement_date && (
                        <span className="ml-auto font-mono text-[10px] text-red-300">
                          retragere: {a.deprecation.target_retirement_date}
                        </span>
                      )}
                    </div>
                    <div className="text-stone-300">{a.deprecation.reason}</div>
                    {a.deprecation.replacement && (
                      <div className="text-[10px] text-stone-400 mt-0.5">Înlocuit cu: <strong className="text-stone-200">{a.deprecation.replacement}</strong></div>
                    )}
                  </div>
                )}
                <div className="mt-3 flex items-center gap-3 text-[10px] text-stone-500 flex-wrap">
                  <span><Activity className="w-3 h-3 inline mr-0.5" /> 24h: <strong className="text-stone-300">{a.live?.items_24h ?? 0}</strong></span>
                  <span>7d: <strong className="text-stone-300">{a.live?.items_7d ?? 0}</strong></span>
                  <span>Total: <strong className="text-stone-300">{a.live?.total_items ?? 0}</strong></span>
                  {a.live?.latest_activity_at && (
                    <span className="ml-auto">Ultim: {new Date(a.live.latest_activity_at).toLocaleString("ro-RO")}</span>
                  )}
                </div>
                <div className="mt-2 flex justify-end">
                  {a.deprecation ? (
                    <button
                      onClick={() => onRestore(a.slug)}
                      className="text-[10px] inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-stone-500/10 border border-stone-500/30 text-stone-300 hover:bg-stone-500/20"
                      data-testid={`gov-restore-${a.slug}`}
                    >
                      <RotateCcw className="w-3 h-3" /> Restaurează
                    </button>
                  ) : (
                    <button
                      onClick={() => onDeprecate(a)}
                      className="text-[10px] inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 hover:bg-red-500/20"
                      data-testid={`gov-deprecate-${a.slug}`}
                    >
                      <ArchiveX className="w-3 h-3" /> Marchează ca depreciat
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const DeprecateModal = ({ agent, onClose, onSubmit, busy }) => {
  const [reason, setReason] = useState("");
  const [replacement, setReplacement] = useState("");
  const [targetDate, setTargetDate] = useState(() =>
    new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10)
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    if (reason.trim().length < 4) return;
    onSubmit({
      reason: reason.trim(),
      replacement: replacement.trim() || null,
      target_retirement_date: targetDate,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="gov-deprecate-modal">
      <div className="bg-[#0e0e10] border border-white/10 rounded-2xl max-w-lg w-full p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Marchează ca depreciat</h3>
            <p className="text-xs text-stone-400 mt-1">
              Agent: <strong className="text-amber-300">{agent.name}</strong>
              <span className="font-mono text-[10px] ml-2 text-stone-500">{agent.slug}</span>
            </p>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-white" data-testid="gov-deprecate-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Motiv depreciere *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="ex: Subutilizat (0 sesiuni în 30 zile), funcționalitate dublată de Document Intelligence."
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="gov-deprecate-reason"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Înlocuitor (opțional)</label>
            <input
              type="text"
              value={replacement}
              onChange={(e) => setReplacement(e.target.value)}
              placeholder="ex: document_intelligence sau ai_security_center"
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="gov-deprecate-replacement"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Dată țintă retragere</label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/30"
              data-testid="gov-deprecate-date"
            />
          </div>

          <div className="bg-amber-500/5 border border-amber-500/30 rounded-lg px-3 py-2 text-[11px] text-amber-200">
            Această acțiune NU oprește agentul. Modifică doar lifecycle = <code>deprecated</code> și creează o intrare în planul de retragere.
            Codul rămâne intact până la migrare manuală.
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 text-xs rounded-lg bg-white/5 border border-white/10 text-stone-300 hover:bg-white/10">
              Anulează
            </button>
            <button
              type="submit"
              disabled={busy || reason.trim().length < 4}
              className="px-4 py-2 text-xs rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 hover:bg-red-500/30 disabled:opacity-50 inline-flex items-center gap-1.5"
              data-testid="gov-deprecate-submit"
            >
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArchiveX className="w-3.5 h-3.5" />}
              Confirmă depreciere
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const DeprecationTab = ({ plan, onRestore, onDeprecate }) => {
  if (!plan) return null;
  return (
    <div className="space-y-6" data-testid="gov-deprecation-tab">
      <div className="grid grid-cols-3 gap-3">
        <KPI label="Active deprecations" value={plan.counts.active_deprecations} icon={ArchiveX} color="amber" />
        <KPI label="Restaurate" value={plan.counts.restored} icon={RotateCcw} color="emerald" />
        <KPI label="Candidați legacy" value={plan.counts.legacy_candidates} icon={ArchiveRestore} color="blue" />
      </div>

      {/* ACTIVE TIMELINE */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">Timeline retragere ({plan.plan.length})</h3>
        {plan.plan.length === 0 ? (
          <div className="text-center py-8 text-stone-500 text-sm bg-white/[0.02] border border-white/10 rounded-xl">
            Niciun agent depreciat momentan. Folosește tabul &quot;Agenți&quot; pentru a marca unul.
          </div>
        ) : (
          <ol className="relative border-l border-white/10 ml-3 space-y-4">
            {plan.plan.map(item => (
              <li key={item.slug} className="ml-5" data-testid={`gov-dep-item-${item.slug}`}>
                <span className="absolute -left-2 w-4 h-4 bg-red-500/30 border border-red-500/60 rounded-full flex items-center justify-center">
                  <CalendarClock className="w-2.5 h-2.5 text-red-200" />
                </span>
                <div className="bg-white/[0.02] border border-red-500/20 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="text-sm font-semibold text-white">{item.name}</div>
                      <div className="font-mono text-[10px] text-stone-500">{item.slug} · {item.category}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-[10px] text-stone-500 uppercase">Țintă retragere</div>
                      <div className="font-mono text-sm text-red-300">{item.target_retirement_date}</div>
                    </div>
                  </div>
                  <div className="text-xs text-stone-300 mb-2">{item.reason}</div>
                  {item.replacement && (
                    <div className="text-[11px] text-stone-400 mb-2">
                      Înlocuit cu: <strong className="text-emerald-300">{item.replacement}</strong>
                    </div>
                  )}
                  <div className="grid grid-cols-3 gap-2 mt-3 text-[10px] text-stone-500">
                    <div className="bg-black/30 rounded-lg p-2">
                      <div className="uppercase">Items la decizie</div>
                      <div className="font-mono text-white text-sm mt-0.5">{item.impact?.items_total_at_decision ?? 0}</div>
                    </div>
                    <div className="bg-black/30 rounded-lg p-2">
                      <div className="uppercase">7d activity</div>
                      <div className="font-mono text-white text-sm mt-0.5">{item.impact?.items_7d_at_decision ?? 0}</div>
                    </div>
                    <div className="bg-black/30 rounded-lg p-2">
                      <div className="uppercase">Provider</div>
                      <div className="font-mono text-violet-300 text-sm mt-0.5">{item.impact?.provider || "—"}</div>
                    </div>
                  </div>
                  {item.impact?.data_sources?.length > 0 && (
                    <div className="text-[10px] text-stone-500 mt-2 flex flex-wrap gap-1">
                      <span>Colecții impactate:</span>
                      {item.impact.data_sources.map(ds => (
                        <code key={ds} className="bg-white/5 px-1.5 py-0.5 rounded text-stone-300">{ds}</code>
                      ))}
                    </div>
                  )}
                  <div className="flex justify-between items-center mt-3 pt-3 border-t border-white/5">
                    <div className="text-[10px] text-stone-500">
                      Marcat de {item.by_email || "—"} · {item.at ? new Date(item.at).toLocaleString("ro-RO") : ""}
                    </div>
                    <button
                      onClick={() => onRestore(item.slug)}
                      className="text-[10px] inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-stone-500/10 border border-stone-500/30 text-stone-300 hover:bg-stone-500/20"
                      data-testid={`gov-dep-restore-${item.slug}`}
                    >
                      <RotateCcw className="w-3 h-3" /> Restaurează
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* SUGGESTED CANDIDATES */}
      {plan.suggested_candidates.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">
            Candidați propuși (legacy ne-tratați) — {plan.suggested_candidates.length}
          </h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {plan.suggested_candidates.map(c => (
              <div key={c.slug} className="bg-white/[0.02] border border-amber-500/20 rounded-xl p-3" data-testid={`gov-dep-suggest-${c.slug}`}>
                <div className="text-sm font-semibold text-white">{c.name}</div>
                <div className="font-mono text-[10px] text-stone-500">{c.slug}</div>
                <div className="text-xs text-stone-400 mt-1 line-clamp-2">{c.purpose}</div>
                <button
                  onClick={() => onDeprecate(c.slug)}
                  className="mt-2 text-[10px] inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 hover:bg-red-500/20"
                  data-testid={`gov-dep-suggest-btn-${c.slug}`}
                >
                  <ArchiveX className="w-3 h-3" /> Marchează ca depreciat
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* HISTORY (restored) */}
      {plan.history.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">Istoric restaurări ({plan.history.length})</h3>
          <div className="space-y-1">
            {plan.history.map(item => (
              <div key={item.slug} className="bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center gap-2" data-testid={`gov-dep-history-${item.slug}`}>
                <RotateCcw className="w-3 h-3 text-emerald-300 shrink-0" />
                <span className="text-stone-300">{item.name}</span>
                <span className="font-mono text-[10px] text-stone-500">{item.slug}</span>
                <span className="text-stone-500 ml-auto text-[10px]">
                  restaurat la {item.restored_at ? new Date(item.restored_at).toLocaleDateString("ro-RO") : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const CostsTab = ({ costs }) => {
  if (!costs) return null;
  return (
    <div className="space-y-4">
      <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 text-xs text-amber-100 flex items-start gap-2" data-testid="gov-costs-disclaimer">
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-300" />
        <div>{costs.disclaimer}</div>
      </div>
      <div className="text-sm">
        Cost lunar total estimat: <strong className="text-2xl font-mono text-amber-300 ml-2">~{costs.estimated_total_monthly_eur}€</strong>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead className="text-[10px] uppercase tracking-wider text-stone-500 border-b border-white/10">
            <tr>
              <th className="text-left px-2 py-2">Agent</th>
              <th className="text-left px-2 py-2">Provider</th>
              <th className="text-right px-2 py-2">Apeluri 7d</th>
              <th className="text-right px-2 py-2">Estimat lunar (apeluri)</th>
              <th className="text-right px-2 py-2">€/apel</th>
              <th className="text-right px-2 py-2">Cost lunar</th>
            </tr>
          </thead>
          <tbody>
            {costs.breakdown.map(b => (
              <tr key={b.slug} className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`gov-cost-${b.slug}`}>
                <td className="px-2 py-2 text-white">{b.name}</td>
                <td className="px-2 py-2 text-violet-300 font-mono">{b.provider}</td>
                <td className="px-2 py-2 text-right text-stone-300 font-mono">{b.calls_last_7d}</td>
                <td className="px-2 py-2 text-right text-stone-300 font-mono">{b.estimated_monthly_calls}</td>
                <td className="px-2 py-2 text-right text-stone-500 font-mono">{b.avg_eur_per_call}</td>
                <td className="px-2 py-2 text-right text-amber-300 font-mono font-semibold">~{b.estimated_monthly_eur}€</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const KIND_COLOR = {
  qa:         "bg-blue-500/10 border-blue-500/40 text-blue-300",
  ai_finding: "bg-violet-500/10 border-violet-500/40 text-violet-300",
  ai_scan:    "bg-violet-500/10 border-violet-500/40 text-violet-300",
  security:   "bg-red-500/10 border-red-500/40 text-red-300",
  autonomy:   "bg-emerald-500/10 border-emerald-500/40 text-emerald-300",
  match:      "bg-amber-500/10 border-amber-500/40 text-amber-300",
  briefing:   "bg-stone-500/10 border-stone-500/40 text-stone-300",
  digest:     "bg-stone-500/10 border-stone-500/40 text-stone-300",
  smoke_test: "bg-blue-500/10 border-blue-500/40 text-blue-300",
};

const AuditTab = ({ events }) => {
  if (!events || events.length === 0) {
    return <div className="text-center py-10 text-stone-500 text-sm">Niciun eveniment în audit trail.</div>;
  }
  return (
    <div className="space-y-2" data-testid="gov-audit-list">
      {events.map((e, i) => (
        <div key={i} className="bg-white/[0.02] border border-white/10 rounded-xl px-4 py-3 flex items-start gap-3" data-testid={`gov-audit-${i}`}>
          <span className={`inline-block text-[10px] uppercase px-1.5 py-0.5 rounded border shrink-0 ${KIND_COLOR[e.kind] || "bg-stone-500/10 border-stone-500/40 text-stone-300"}`}>{e.kind}</span>
          <div className="flex-1 min-w-0">
            <div className="text-sm text-white truncate">{e.title}</div>
            <div className="text-[10px] text-stone-500 mt-0.5 font-mono">{e.source}</div>
          </div>
          {e.at && <div className="text-[10px] text-stone-500 shrink-0">{new Date(e.at).toLocaleString("ro-RO")}</div>}
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// HEALTH TAB
// ============================================================================
const HEALTH_COLOR = {
  healthy:    "bg-emerald-500/15 border-emerald-500/50 text-emerald-300",
  degraded:   "bg-amber-500/15 border-amber-500/50 text-amber-300",
  silent:     "bg-stone-500/15 border-stone-500/50 text-stone-400",
  error:      "bg-red-500/15 border-red-500/50 text-red-300",
  deprecated: "bg-red-500/10 border-red-500/40 text-red-200",
};
const HealthTab = ({ health }) => {
  if (!health) return null;
  const c = health.counts;
  return (
    <div className="space-y-5" data-testid="gov-health-tab">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KPI label="Overall" value={health.overall.toUpperCase()} icon={HeartPulse} color={health.overall === "healthy" ? "emerald" : (health.overall === "degraded" ? "amber" : "blue")} />
        <KPI label="Healthy" value={c.healthy || 0} icon={CheckCircle2} color="emerald" />
        <KPI label="Degraded" value={c.degraded || 0} icon={AlertTriangle} color="amber" />
        <KPI label="Silent" value={c.silent || 0} icon={Eye} color="blue" />
        <KPI label="Deprecated" value={c.deprecated || 0} icon={ArchiveX} color="amber" />
      </div>
      <div className="rounded-xl border border-white/10 divide-y divide-white/5">
        {health.rows.map((r) => (
          <div key={r.slug} className="px-4 py-3 flex items-start gap-3 hover:bg-white/[0.02]" data-testid={`gov-health-${r.slug}`}>
            <span className={`shrink-0 text-[10px] uppercase px-2 py-0.5 rounded-full border ${HEALTH_COLOR[r.health.status] || HEALTH_COLOR.silent}`}>
              {r.health.status}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white truncate">{r.name}</div>
              <div className="text-[10px] font-mono text-stone-500">{r.slug} · {r.category} · {r.provider}</div>
              <div className="text-[11px] text-stone-400 mt-1">{r.health.reason}</div>
            </div>
            <div className="shrink-0 text-right text-[10px] text-stone-500">
              <div>24h: <strong className="text-stone-300 font-mono">{r.items_24h}</strong></div>
              <div>7d: <strong className="text-stone-300 font-mono">{r.items_7d}</strong></div>
              {r.latest_activity_at && <div className="mt-0.5">Ultim: {new Date(r.latest_activity_at).toLocaleString("ro-RO")}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// PERMISSIONS TAB
// ============================================================================
const RISK_BADGE = ["emerald", "blue", "amber", "amber", "red"];
const PERM_BORDER = {
  read: "border-stone-500/30",
  suggest: "border-blue-500/30",
  "execute-with-approval": "border-amber-500/30",
  execute: "border-amber-500/40",
  autonomous: "border-red-500/40",
};
const PermissionsTab = ({ perms }) => {
  if (!perms) return null;
  return (
    <div className="space-y-5" data-testid="gov-perms-tab">
      <div className="bg-violet-500/5 border border-violet-500/30 rounded-xl p-4 text-xs text-violet-100">
        <strong className="block mb-2 text-violet-200">Principii:</strong>
        <ul className="space-y-1 ml-4 list-disc">
          {perms.principles.map((p, i) => (<li key={i}>{p}</li>))}
        </ul>
      </div>

      {perms.risk_hotspots.length > 0 && (
        <div className="bg-red-500/5 border border-red-500/30 rounded-xl p-4" data-testid="gov-perms-hotspots">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-300" />
            <strong className="text-red-200 text-sm">Risc hotspots ({perms.risk_hotspots.length})</strong>
          </div>
          <div className="space-y-1.5">
            {perms.risk_hotspots.map(h => (
              <div key={h.slug} className="text-xs text-stone-300 flex items-center gap-2">
                <span className="font-mono text-[10px] text-stone-500">{h.slug}</span>
                <span className="text-stone-100">{h.name}</span>
                <span className="text-[10px] uppercase px-1.5 py-0.5 rounded border bg-red-500/10 border-red-500/40 text-red-300">{h.permission_level}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-3">
        {perms.groups.map(g => {
          const colorIdx = Math.min(g.risk_level, RISK_BADGE.length - 1);
          const colorKey = RISK_BADGE[colorIdx];
          const headerCls = {
            emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-200",
            blue: "bg-blue-500/10 border-blue-500/30 text-blue-200",
            amber: "bg-amber-500/10 border-amber-500/30 text-amber-200",
            red: "bg-red-500/10 border-red-500/30 text-red-200",
          }[colorKey];
          return (
            <div key={g.permission_level} className={`bg-white/[0.02] border ${PERM_BORDER[g.permission_level] || "border-white/10"} rounded-xl p-4`} data-testid={`gov-perm-${g.permission_level}`}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className={`inline-block text-[10px] uppercase px-2 py-0.5 rounded-full border ${headerCls}`}>
                    Risc {g.risk_level} · {g.label}
                  </div>
                </div>
                <span className="text-2xl font-mono text-white">{g.count}</span>
              </div>
              {g.agents.length === 0 ? (
                <div className="text-xs text-stone-500 italic">Niciun agent.</div>
              ) : (
                <div className="space-y-1.5">
                  {g.agents.map(a => (
                    <div key={a.slug} className="text-xs text-stone-300 flex items-center gap-1.5">
                      <span className="text-stone-100">{a.name}</span>
                      <span className="font-mono text-[10px] text-stone-500">{a.slug}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// PULSE TAB (Deprecation Pulse settings + manual trigger + history)
// ============================================================================
const PulseTab = ({ cfg, preview, history, onSave, onSendNow, busy }) => {
  return cfg ? <PulseTabInner cfgKey={cfg.last_sent_at || "init"} cfg={cfg} preview={preview} history={history} onSave={onSave} onSendNow={onSendNow} busy={busy} /> : null;
};

const PulseTabInner = ({ cfg, preview, history, onSave, onSendNow, busy }) => {
  const [enabled, setEnabled] = useState(cfg.enabled || false);
  const [recipientsText, setRecipientsText] = useState((cfg.recipients || []).join(", "));
  const [pulseWindow, setPulseWindow] = useState(cfg.alert_window_days || 30);

  const save = () => {
    const recipients = recipientsText.split(",").map(e => e.trim()).filter(Boolean);
    onSave({ enabled, recipients, alert_window_days: Number(pulseWindow) });
  };

  const c = preview?.data?.counts || {};

  return (
    <div className="space-y-5" data-testid="gov-pulse-tab">
      <div className="bg-violet-500/5 border border-violet-500/30 rounded-xl p-4 text-xs text-violet-100">
        <strong className="block mb-1 text-violet-200">Deprecation Pulse</strong>
        Email digest săptămânal (joi 09:30 Europe/Bucharest) cu agenți depreciati &lt; 30 zile până la retragere,
        overlap colecții cu agenți activi, și provider risk alerts. NU se trimite SMS, NU folosește Twilio.
      </div>

      {/* PREVIEW KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI label="Retrageri viitoare" value={c.upcoming ?? 0} icon={CalendarClock} color="amber" />
        <KPI label="Overlap" value={c.overlap ?? 0} icon={AlertTriangle} color="amber" />
        <KPI label="Provider risk" value={c.provider_risk ?? 0} icon={Shield} color="violet" />
        <KPI label="Total semnale" value={c.total_signals ?? 0} icon={Bell} color="blue" />
      </div>

      {/* CONFIG */}
      <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-white">Stare schedule</div>
            <div className="text-[11px] text-stone-500">
              {cfg.last_sent_at ? `Ultim trimis: ${new Date(cfg.last_sent_at).toLocaleString("ro-RO")}` : "Nu a fost trimis niciodată"}
            </div>
          </div>
          <button
            onClick={() => setEnabled(v => !v)}
            className={`px-3 py-1.5 text-xs rounded-lg border ${enabled ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200" : "bg-stone-500/10 border-stone-500/30 text-stone-300"}`}
            data-testid="gov-pulse-toggle"
          >
            {enabled ? "Activ" : "Dezactivat"}
          </button>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wider text-stone-500">Destinatari (email, separați cu virgulă)</label>
          <input
            type="text"
            value={recipientsText}
            onChange={(e) => setRecipientsText(e.target.value)}
            placeholder="founder@propmanage.ro, ops@propmanage.ro"
            className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
            data-testid="gov-pulse-recipients"
          />
        </div>

        <div className="flex items-center gap-3">
          <label className="text-[10px] uppercase tracking-wider text-stone-500">Fereastră alertă (zile)</label>
          <input
            type="number"
            value={pulseWindow}
            onChange={(e) => setPulseWindow(e.target.value)}
            min={7}
            max={180}
            className="w-24 bg-[#0a0a0b] border border-white/10 rounded-lg px-2 py-1 text-sm text-white focus:outline-none focus:border-white/30"
            data-testid="gov-pulse-window"
          />
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={save}
            disabled={busy}
            className="px-3 py-1.5 text-xs rounded-lg bg-violet-500/20 border border-violet-500/40 text-violet-200 hover:bg-violet-500/30 disabled:opacity-50 inline-flex items-center gap-1.5"
            data-testid="gov-pulse-save"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            Salvează config
          </button>
          <button
            onClick={onSendNow}
            disabled={busy}
            className="px-3 py-1.5 text-xs rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-200 hover:bg-amber-500/30 disabled:opacity-50 inline-flex items-center gap-1.5"
            data-testid="gov-pulse-send-now"
          >
            <Mail className="w-3.5 h-3.5" /> Trimite acum
          </button>
        </div>
      </div>

      {/* HISTORY */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">Istoric ({history.length})</h3>
        {history.length === 0 ? (
          <div className="text-center py-6 text-stone-500 text-xs bg-white/[0.02] border border-white/10 rounded-xl">
            Nu există încă trimiteri. Pornește scheduler-ul sau trimite acum.
          </div>
        ) : (
          <div className="space-y-1">
            {history.map((h, i) => (
              <div key={i} className="bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center gap-2" data-testid={`gov-pulse-hist-${i}`}>
                <span className={`w-2 h-2 rounded-full ${h.ok ? "bg-emerald-400" : "bg-red-400"}`}></span>
                <span className="text-stone-300 truncate">{h.subject}</span>
                <span className="text-stone-500 ml-auto text-[10px] shrink-0">{new Date(h.sent_at).toLocaleString("ro-RO")}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AIGovernancePage;
