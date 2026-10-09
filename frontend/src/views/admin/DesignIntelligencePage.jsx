// DesignIntelligencePage — PropManage Design Intelligence Engine.
// P1a Layout Optimizer · P1b Component Optimizer · P1c Evolution Engine (Observe → Propose → Test → Apply).
// Every proposal carries an Impact Score (0-100) with breakdown.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Brain, LayoutDashboard, Boxes, GitBranch, Sparkles, RefreshCw,
  FlaskConical, CheckCircle2, XCircle, Rocket, Undo2, Trash2,
  Gauge, Users, Wrench, ShieldAlert, Scale, AlertTriangle,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSBadge, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_META = {
  proposed: { label: "Propusă",   cls: "bg-cyan-50 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300" },
  testing:  { label: "În testare", cls: "bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300" },
  approved: { label: "Aprobată",  cls: "bg-lime-50 dark:bg-lime-500/15 text-lime-700 dark:text-lime-300" },
  applied:  { label: "Aplicată",  cls: "bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" },
  rejected: { label: "Respinsă",  cls: "bg-rose-50 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300" },
};

const ImpactBadge = ({ impact, testid }) => {
  const s = impact?.score ?? 0;
  const cls = s >= 70
    ? "bg-emerald-500 text-white"
    : s >= 40
      ? "bg-amber-500 text-white"
      : "bg-rose-500 text-white";
  return (
    <div className={`flex flex-col items-center justify-center w-14 h-14 rounded-2xl shrink-0 ${cls}`} data-testid={testid}>
      <span className="text-xl font-black leading-none">{s}</span>
      <span className="text-[8px] font-bold uppercase tracking-wider opacity-80">Impact</span>
    </div>
  );
};

const MiniBar = ({ icon: Icon, label, value, max = 100, invert = false }) => {
  const pct = Math.round((value / max) * 100);
  const good = invert ? pct <= 40 : pct >= 60;
  return (
    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-slate-400">
      <Icon className="w-3 h-3 shrink-0" />
      <span className="w-14 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${good ? "bg-lime-400" : "bg-amber-400"}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-7 text-right font-bold text-slate-700 dark:text-slate-200">{value}{max === 5 ? "/5" : ""}</span>
    </div>
  );
};

const ProposalCard = ({ p, onAction, busy }) => {
  const st = STATUS_META[p.status] || STATUS_META.proposed;
  const imp = p.impact || {};
  return (
    <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 space-y-3" data-testid={`di-proposal-${p.id}`}>
      <div className="flex items-start gap-3">
        <ImpactBadge impact={imp} testid={`di-impact-${p.id}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${st.cls}`}>{st.label}</span>
            {p.ux_law && <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{p.ux_law}</span>}
            <span className="text-[10px] text-slate-400">{p.source === "layout_optimizer" ? "Layout" : p.source === "component_optimizer" ? "Component" : "Manual"} · {p.target_label}</span>
            {p.token_patch && <DSBadge type="AI">TOKENS LIVE</DSBadge>}
          </div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white">{p.title}</h4>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">{p.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <MiniBar icon={Gauge}      label="UX"      value={imp.ux_benefit ?? 0} />
        <MiniBar icon={Users}      label="Reach"   value={imp.users_reach ?? 0} />
        <MiniBar icon={Wrench}     label="Efort"   value={imp.effort ?? 0} max={5} invert />
        <MiniBar icon={ShieldAlert} label="Risc"   value={imp.risk ?? 0} max={5} invert />
      </div>

      {p.token_patch && (
        <pre className="text-[10px] p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 overflow-x-auto" data-testid={`di-patch-${p.id}`}>
          {JSON.stringify(p.token_patch, null, 1)}
        </pre>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {p.status === "proposed" && (
          <>
            <DSButton variant="ghost" icon={FlaskConical} disabled={busy} onClick={() => onAction(p, "start_test")} data-testid={`di-test-${p.id}`}>Testează</DSButton>
            <DSButton variant="ghost" icon={CheckCircle2} disabled={busy} onClick={() => onAction(p, "approve")} data-testid={`di-approve-${p.id}`}>Aprobă direct</DSButton>
          </>
        )}
        {p.status === "testing" && (
          <DSButton variant="primary" icon={CheckCircle2} disabled={busy} onClick={() => onAction(p, "approve")} data-testid={`di-approve-${p.id}`}>Aprobă</DSButton>
        )}
        {p.status === "approved" && (
          <DSButton variant="primary" icon={Rocket} disabled={busy} onClick={() => onAction(p, "apply")} data-testid={`di-apply-${p.id}`}>
            {p.token_patch ? "Aplică LIVE (tokens)" : "Marchează aplicată"}
          </DSButton>
        )}
        {p.status === "applied" && (
          <DSButton variant="ghost" icon={Undo2} disabled={busy} onClick={() => onAction(p, "rollback")} data-testid={`di-rollback-${p.id}`}>Rollback</DSButton>
        )}
        {["proposed", "testing", "approved"].includes(p.status) && (
          <DSButton variant="ghost" icon={XCircle} disabled={busy} onClick={() => onAction(p, "reject")} data-testid={`di-reject-${p.id}`}>Respinge</DSButton>
        )}
        {["proposed", "rejected"].includes(p.status) && (
          <DSButton variant="ghost" icon={Trash2} disabled={busy} onClick={() => onAction(p, "delete")} data-testid={`di-delete-${p.id}`}>Șterge</DSButton>
        )}
      </div>
    </div>
  );
};

const TargetList = ({ items, activeKey, onAnalyze, running, kindLabel, testPrefix }) => (
  <div className="max-h-[480px] overflow-y-auto space-y-1 -mx-1 px-1">
    {items.map((t) => (
      <button
        key={t.key}
        onClick={() => onAnalyze(t.key)}
        disabled={!!running}
        className={`w-full text-left px-3 py-2.5 rounded-xl border transition-colors ${activeKey === t.key ? "bg-lime-50 dark:bg-lime-500/10 border-lime-300 dark:border-lime-500/40" : "border-transparent hover:bg-slate-50 dark:hover:bg-slate-800"}`}
        data-testid={`${testPrefix}-${t.key}`}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{t.label}</span>
          {running === t.key
            ? <RefreshCw className="w-3.5 h-3.5 text-lime-500 animate-spin shrink-0" />
            : <Sparkles className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600 shrink-0" />}
        </div>
        <div className="text-[11px] text-slate-500">{t.zone || t.category} {t.path ? `· ${t.path}` : ""}</div>
      </button>
    ))}
    {!items.length && <div className="text-xs text-slate-400 p-3">Niciun {kindLabel} disponibil.</div>}
  </div>
);

const TABS = [
  { id: "layout",     label: "Layout Optimizer",    icon: LayoutDashboard },
  { id: "components", label: "Component Optimizer", icon: Boxes },
  { id: "evolution",  label: "Evolution Engine",    icon: GitBranch },
];

export default function DesignIntelligencePage() {
  const [tab, setTab] = useState("layout");
  const [targets, setTargets] = useState({ pages: [], components: [] });
  const [summary, setSummary] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null);
  const [activeKey, setActiveKey] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState(null);

  const load = useCallback(async () => {
    try {
      const [t, s, pr] = await Promise.all([
        ax.get("/admin/design-intelligence/targets"),
        ax.get("/admin/design-intelligence/summary"),
        ax.get("/admin/design-intelligence/proposals"),
      ]);
      setTargets(t.data);
      setSummary(s.data);
      setProposals(pr.data.proposals || []);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const analyze = async (kind, key) => {
    setRunning(key);
    setActiveKey(key);
    setFlash(null);
    try {
      const url = kind === "layout" ? "/admin/design-intelligence/layout/analyze" : "/admin/design-intelligence/components/analyze";
      const body = kind === "layout" ? { page_key: key } : { component_key: key };
      const r = await ax.post(url, body);
      const n = r.data.proposals?.length || 0;
      setFlash({ ok: true, text: `${n} propuneri generate${r.data.ai_generated ? " de AI" : " (fallback rule-based)"} — fiecare cu Impact Score.` });
      load();
    } catch (e) {
      setFlash({ ok: false, text: e?.response?.data?.detail || "Eroare la analiză." });
    }
    setRunning(null);
  };

  const onAction = async (p, action) => {
    setBusy(true);
    setFlash(null);
    try {
      if (action === "delete") {
        await ax.delete(`/admin/design-intelligence/proposals/${p.id}`);
        setFlash({ ok: true, text: "Propunere ștearsă." });
      } else if (action === "rollback") {
        const r = await ax.post(`/admin/design-intelligence/proposals/${p.id}/rollback`);
        setFlash({ ok: true, text: r.data.tokens_restored ? "Tokens restaurate — UI-ul a revenit la starea anterioară." : "Rollback efectuat." });
      } else {
        const r = await ax.post(`/admin/design-intelligence/proposals/${p.id}/advance`, { action });
        if (action === "apply") {
          setFlash({ ok: true, text: r.data.applied?.tokens_applied ? "Modificarea de tokens a fost aplicată LIVE pe toată platforma." : (r.data.applied?.note || "Aplicată.") });
          if (r.data.applied?.tokens_applied) setTimeout(() => window.location.reload(), 1200);
        } else {
          setFlash({ ok: true, text: `Status actualizat: ${STATUS_META[r.data.proposal?.status]?.label || action}.` });
        }
      }
      load();
    } catch (e) {
      setFlash({ ok: false, text: e?.response?.data?.detail || "Eroare la acțiune." });
    }
    setBusy(false);
  };

  const bySource = (src) => proposals.filter((p) => p.source === src && (activeKey ? p.target === activeKey : true));
  const evolutionList = statusFilter === "all" ? proposals : proposals.filter((p) => p.status === statusFilter);
  const counts = summary?.counts || {};

  return (
    <AdminLayoutMetronic
      title="Design Intelligence Engine"
      subtitle="Layout Optimizer · Component Optimizer · Evolution Engine — Impact Score per modificare · Observe → Propose → Test → Apply"
    >
      {loading ? <DSSkeleton kpis={4} blocks={1} /> : (
        <div className="space-y-6" data-testid="design-intelligence-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Brain}        label="Total propuneri"   value={summary?.total ?? 0}                                    accent="ai"      testid="di-kpi-total" />
            <KpiCard icon={Scale}        label="Impact Score mediu" value={summary?.avg_impact ?? "—"}                            accent="info"    testid="di-kpi-avg" />
            <KpiCard icon={FlaskConical} label="În pipeline"       value={(counts.proposed || 0) + (counts.testing || 0) + (counts.approved || 0)} accent="warning" testid="di-kpi-pending" />
            <KpiCard icon={Rocket}       label="Aplicate"          value={counts.applied ?? 0}                                    accent="success" testid="di-kpi-applied" />
          </div>

          {flash && (
            <div className={`p-3 rounded-xl text-sm border ${flash.ok ? "bg-lime-50 dark:bg-lime-500/10 border-lime-300 dark:border-lime-500/30 text-lime-800 dark:text-lime-200" : "bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300"}`} data-testid="di-flash">
              {flash.ok ? <CheckCircle2 className="w-4 h-4 inline mr-1.5" /> : <AlertTriangle className="w-4 h-4 inline mr-1.5" />}
              {flash.text}
            </div>
          )}

          <div className="flex gap-2 flex-wrap">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); setActiveKey(null); }}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold transition-colors ${tab === t.id ? "bg-lime-400 text-slate-900" : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"}`}
                data-testid={`di-tab-${t.id}`}
              >
                <t.icon className="w-4 h-4" /> {t.label}
              </button>
            ))}
          </div>

          {(tab === "layout" || tab === "components") && (
            <div className="grid lg:grid-cols-5 gap-4">
              <AdminCard className="lg:col-span-2"
                title={tab === "layout" ? "Pagini — rulează Layout Optimizer AI" : "Componente — rulează Component Optimizer AI"}
                testid={`di-targets-${tab}`}
              >
                <p className="text-[11px] text-slate-500 mb-2">
                  {tab === "layout"
                    ? "AI-ul observă structura paginii + scorurile de audit și propune modificări de layout cu Impact Score."
                    : "AI-ul analizează componenta + tokens-urile active și propune optimizări (contrast, touch targets, consistență)."}
                </p>
                <TargetList
                  items={tab === "layout" ? targets.pages : targets.components}
                  activeKey={activeKey}
                  onAnalyze={(k) => analyze(tab, k)}
                  running={running}
                  kindLabel={tab === "layout" ? "pagină" : "componentă"}
                  testPrefix={tab === "layout" ? "di-page" : "di-comp"}
                />
              </AdminCard>

              <AdminCard className="lg:col-span-3"
                title={<span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-lime-500" /> Propuneri {activeKey ? `· ${activeKey}` : "(toate)"}</span>}
                action={activeKey && <DSButton variant="ghost" onClick={() => setActiveKey(null)} data-testid="di-clear-filter">Toate</DSButton>}
                testid={`di-results-${tab}`}
              >
                {running && <DSSkeleton kpis={0} blocks={2} />}
                {!running && (
                  <div className="space-y-3">
                    {bySource(tab === "layout" ? "layout_optimizer" : "component_optimizer").map((p) => (
                      <ProposalCard key={p.id} p={p} onAction={onAction} busy={busy} />
                    ))}
                    {!bySource(tab === "layout" ? "layout_optimizer" : "component_optimizer").length && (
                      <EmptyState icon={Brain} title="Nicio propunere încă" hint={`Selectează ${tab === "layout" ? "o pagină" : "o componentă"} din stânga și AI-ul va genera propuneri cu Impact Score.`} />
                    )}
                  </div>
                )}
              </AdminCard>
            </div>
          )}

          {tab === "evolution" && (
            <AdminCard
              title={<span className="flex items-center gap-2"><GitBranch className="w-4 h-4 text-lime-500" /> Pipeline evolutiv — Observe → Propose → Test → Apply</span>}
              testid="di-evolution"
            >
              <div className="flex gap-2 flex-wrap mb-4">
                {["all", ...Object.keys(STATUS_META)].map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${statusFilter === s ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900" : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"}`}
                    data-testid={`di-filter-${s}`}
                  >
                    {s === "all" ? `Toate (${summary?.total ?? 0})` : `${STATUS_META[s].label} (${counts[s] || 0})`}
                  </button>
                ))}
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {evolutionList.map((p) => <ProposalCard key={p.id} p={p} onAction={onAction} busy={busy} />)}
              </div>
              {!evolutionList.length && (
                <EmptyState icon={GitBranch} title="Pipeline gol" hint="Rulează Layout sau Component Optimizer pentru a genera propuneri. Nimic nu se aplică fără aprobarea ta." />
              )}
              <div className="mt-4 text-[10px] text-slate-400">
                Propunerile cu badge TOKENS LIVE se aplică instant pe toată platforma prin Design Studio (cu snapshot pentru rollback). Restul sunt marcate pentru implementare manuală.
              </div>
            </AdminCard>
          )}
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
