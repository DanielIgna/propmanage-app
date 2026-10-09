// Executive Control Tower v1 (Blueprint Phase 2) — „Ce decizii cer om azi?"
// Ordine DS: Pulse KPI → Attention Layer → Autonomy Report (AI) → KG-0
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Inbox, Briefcase, ShieldCheck, Scale, RefreshCw, ArrowRight, AlertTriangle,
  Bot, Network, Database, Play,
} from "lucide-react";
import { toast } from "sonner";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, AIInsightCard, DSButton, DSBadge, DataTable, DSSkeleton, EmptyState, CARD } from "../../design-system";

const SEV_BADGE = { critical: "ERROR", warning: "WARNING", info: "NEW" };

const AttentionCard = ({ item, onGo, onApi, busy }) => (
  <div className={`${CARD} p-4 ${item.severity === "critical" ? "border-rose-200 dark:border-rose-500/30" : "border-amber-200 dark:border-amber-500/30"}`}
    data-testid={`ct-attention-${item.id}`}>
    <div className="flex items-start gap-3">
      <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${item.severity === "critical" ? "bg-rose-50 dark:bg-rose-500/15" : "bg-amber-50 dark:bg-amber-500/15"}`}>
        <AlertTriangle className={`w-4 h-4 ${item.severity === "critical" ? "text-rose-500" : "text-amber-500"}`} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-bold text-sm text-slate-900 dark:text-white">{item.situatie}</h3>
          <DSBadge type={SEV_BADGE[item.severity] || "NEW"} />
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{item.propunere}</p>
        <p className="mt-1 text-xs text-slate-400">Impact: {item.impact_estimat} · Sursă: {item.sursa_semnalului}</p>
      </div>
      {item.actiune_1tap.api ? (
        <DSButton variant="success" disabled={busy} onClick={() => onApi(item.actiune_1tap)} data-testid={`ct-action-${item.id}`}>
          {busy ? "Se repară..." : item.actiune_1tap.label} <ArrowRight className="w-3.5 h-3.5" />
        </DSButton>
      ) : (
        <DSButton variant="primary" onClick={() => onGo(item.actiune_1tap.route)} data-testid={`ct-action-${item.id}`}>
          {item.actiune_1tap.label} <ArrowRight className="w-3.5 h-3.5" />
        </DSButton>
      )}
    </div>
  </div>
);

export default function ControlTowerPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [kg, setKg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);
  const [apiBusy, setApiBusy] = useState(false);

  const runApiAction = async (action) => {
    setApiBusy(true);
    try {
      const { data: res } = await axios.post(`${API}${action.api.replace(/^\/admin/, "/admin")}`);
      toast.success(res.message || "Acțiune executată");
      await load();
    } catch { toast.error("Acțiunea a eșuat"); }
    setApiBusy(false);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [ct, kgs] = await Promise.all([
        axios.get(`${API}/admin/control-tower`),
        axios.get(`${API}/admin/kg/stats`),
      ]);
      setData(ct.data); setKg(kgs.data);
    } catch { toast.error("Eroare la încărcarea Control Tower"); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const runBackfill = async () => {
    setBackfilling(true);
    try {
      const { data: res } = await axios.post(`${API}/admin/kg/backfill`);
      toast.success(`KG-0: ${res.total_new} muchii noi (total ${res.total_links})`);
      setKg(await axios.get(`${API}/admin/kg/stats`).then(r => r.data));
    } catch { toast.error("Backfill eșuat"); }
    setBackfilling(false);
  };

  const p = data?.pulse || {};
  const ar = data?.autonomy_report;

  return (
    <AdminLayoutMetronic active="control_tower" title="Executive Control Tower" subtitle="Ce decizii cer om azi? Restul e rezolvat și raportat de platformă.">
      <div className="space-y-6" data-testid="control-tower-page">
        {loading && !data ? <DSSkeleton kpis={5} blocks={2} /> : (
          <>
            {/* 1. Pulse */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <KpiCard icon={Inbox} label="Cereri deschise" value={p.open_requests ?? 0} accent="info" testid="ct-pulse-open" />
              <KpiCard icon={Briefcase} label="Lucrări active" value={p.active_jobs ?? 0} accent="success" testid="ct-pulse-active" />
              <KpiCard icon={ShieldCheck} label="KYC în așteptare" value={p.kyc_pending ?? 0} accent="warning" onClick={() => navigate("/admin?tab=kyc")} testid="ct-pulse-kyc" />
              <KpiCard icon={Scale} label="Dispute deschise" value={p.disputes_open ?? 0} accent="critical" onClick={() => navigate("/admin?tab=disputes")} testid="ct-pulse-disputes" />
              <KpiCard icon={RefreshCw} label="Retry eșuate" value={p.retry_failed ?? 0} accent="neutral" onClick={() => navigate("/admin/orchestrator")} testid="ct-pulse-retry" />
            </div>

            {/* 2. Attention Layer — top 5 decizii care cer om AZI */}
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3">
                Attention Layer — decizii care cer om azi ({data?.attention?.length || 0})
              </h2>
              <div className="space-y-4" data-testid="ct-attention-list">
                {(data?.attention || []).map(item => <AttentionCard key={item.id} item={item} onGo={navigate} onApi={runApiAction} busy={apiBusy} />)}
                {!data?.attention?.length && (
                  <EmptyState icon={ShieldCheck} title="Nicio decizie critică azi." hint="Platforma gestionează totul autonom. Verifică Autonomy Report mai jos." testid="ct-attention-empty" />
                )}
              </div>
            </div>

            {/* 3. Autonomy Report */}
            <AIInsightCard
              testid="ct-autonomy-report" llmModule="control_tower"
              bullets={ar ? [
                `Platforma a rezolvat singură ${ar.auto_resolved_7d} situații în ultimele 7 zile (~${ar.hours_saved_7d}h economisite).`,
                ...(ar.escalated_7d ? [`${ar.escalated_7d} situații au fost escaladate către om.`] : []),
                ...(ar.top_playbooks?.[0] ? [`Cel mai activ playbook: «${ar.top_playbooks[0].name}» (${ar.top_playbooks[0].count} rulări).`] : []),
              ] : []}
              recommendations={ar?.escalated_7d ? ["Revizuiește escaladările din Orchestrator pentru a le transforma în reguli automate."] : []}
              onAction={() => navigate("/admin/orchestrator")} actionLabel="Deschide Autonomy Orchestrator"
            />

            {/* 4. KG-0 — Property Knowledge Graph */}
            <div className={`${CARD} p-4`} data-testid="ct-kg-card">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-violet-50 dark:bg-violet-500/15">
                    <Network className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  </span>
                  <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">Knowledge Graph — KG-0</h3>
                  <DSBadge type="NEW">Blueprint §12</DSBadge>
                  <span className="text-xs text-slate-400 flex items-center gap-1"><Database className="w-3 h-3" /> {kg?.total_links ?? 0} legături · {kg?.node_types?.length ?? 0} tipuri de noduri</span>
                </div>
                <DSButton variant="secondary" icon={Play} onClick={runBackfill} disabled={backfilling} data-testid="ct-kg-backfill">
                  {backfilling ? "Rulează..." : "Rulează backfill"}
                </DSButton>
              </div>
              {kg?.by_rel?.length ? (
                <DataTable
                  columns={[
                    { key: "rel", label: "Relație", render: r => <code className="text-xs">{r.rel}</code> },
                    { key: "count", label: "Legături", render: r => <b>{r.count}</b> },
                  ]}
                  rows={kg.by_rel} exportName="kg-relations" testid="ct-kg-table" maxHeight="16rem"
                />
              ) : (
                <EmptyState icon={Network} title="Graful e gol." hint="Rulează backfill pentru a popula legăturile din datele existente (proprietăți, cereri, dispute, tranzacții)." testid="ct-kg-empty" />
              )}
            </div>
          </>
        )}
      </div>
    </AdminLayoutMetronic>
  );
}
