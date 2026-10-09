// LearningEnginePage — GI-4a (read-only): fiecare decizie AI cu verdictul ei real.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BookOpenCheck, RefreshCw, AlertTriangle, Wallet, Target, CheckCircle2, Percent,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton, EmptyState } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const OUTCOME = {
  revenue:    { label: "VENIT",      cls: "bg-emerald-500 text-white" },
  request:    { label: "CERERE",     cls: "bg-lime-400 text-slate-900" },
  conversion: { label: "CONVERSIE",  cls: "bg-sky-500 text-white" },
  engagement: { label: "REVENIRE",   cls: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  no_effect:  { label: "FĂRĂ EFECT", cls: "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300" },
  untracked:  { label: "NEURMĂRIT",  cls: "bg-slate-100 text-slate-400 dark:bg-slate-800" },
};
const TYPE_LABEL = {
  contact_playbook: "Playbook contact", opportunity: "Oportunitate", command_center_reco: "Reco Command Center",
};
const lei = (v) => `${(v ?? 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} lei`;

export default function LearningEnginePage() {
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const [s, l] = await Promise.all([ax.get("/admin/learning/stats"), ax.get("/admin/learning/ledger?limit=50")]);
      setStats(s.data);
      setItems(l.data.items || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
    }
    setLoading(false);
  };
  const runScan = async () => {
    setRunning(true);
    try { await ax.post("/admin/learning/run"); await load(); } catch (e) { /* silent */ }
    setRunning(false);
  };
  useEffect(() => { load(); }, []);

  return (
    <AdminLayoutMetronic
      title="Learning Engine"
      subtitle="GI-4a: fiecare decizie AI primește verdictul real — revenire → conversie → cerere → venit (atribuire last-touch)"
    >
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : err ? (
        <div className="p-4 rounded-xl bg-rose-50 text-rose-700 text-sm" data-testid="le-error"><AlertTriangle className="w-4 h-4 inline mr-1.5" />{err}</div>
      ) : (
        <div className="space-y-6" data-testid="le-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={BookOpenCheck} label="Decizii AI memorate" value={stats?.total_decisions ?? 0} accent="ai" testid="le-kpi-decisions" />
            <KpiCard icon={CheckCircle2} label="Cu efect pozitiv" value={Object.entries(stats?.outcomes_by_kind || {}).filter(([k]) => ["engagement", "conversion", "request", "revenue"].includes(k)).reduce((a, [, v]) => a + v, 0)} accent="success" testid="le-kpi-positive" />
            <KpiCard icon={Percent} label="Rată de efect" value={`${stats?.outcome_rate_pct ?? 0}%`} accent="info" testid="le-kpi-rate" />
            <KpiCard icon={Wallet} label="Venit atribuit AI" value={lei(stats?.revenue_attributed_ron)} accent="warning" testid="le-kpi-revenue" />
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Target className="w-4 h-4 text-lime-500" /> Performanță pe tip de decizie</span>}
            action={<DSButton variant="primary" icon={RefreshCw} disabled={running} onClick={runScan} data-testid="le-run-btn">{running ? "Scanează…" : "Scanează outcome-uri"}</DSButton>}
            testid="le-by-type"
          >
            <div className="grid lg:grid-cols-3 gap-2">
              {(stats?.by_type || []).map((t, i) => (
                <div key={t.type || i} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={`le-type-${i}`}>
                  <div className="text-[10px] font-black uppercase text-slate-400">{TYPE_LABEL[t.type] || t.type}</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{t.decisions} decizii · {t.with_outcome} cu efect · {lei(t.revenue_ron)}</div>
                </div>
              ))}
              {!(stats?.by_type || []).length && <div className="text-xs text-slate-400">Ledger-ul se populează din deciziile tale (playbooks, oportunități, Command Center).</div>}
            </div>
          </AdminCard>

          <AdminCard title={<span className="flex items-center gap-2"><BookOpenCheck className="w-4 h-4 text-lime-500" /> AI Decision Ledger (append-only)</span>} testid="le-ledger">
            {!items.length ? (
              <EmptyState icon={BookOpenCheck} title="Nicio decizie încă" hint="Deciziile din Playbook, Oportunități și Command Center apar aici automat." />
            ) : (
              <div className="space-y-2">
                {items.map((e, i) => {
                  const o = OUTCOME[e.outcome?.kind] || null;
                  return (
                    <div key={e.ledger_id || i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`le-entry-${i}`}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300">{TYPE_LABEL[e.type] || e.type}</span>
                        {e.action && <span className="text-[10px] font-bold text-slate-400 uppercase">{e.action}</span>}
                        {o ? <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${o.cls}`} data-testid={`le-outcome-${i}`}>{o.label}{e.outcome?.revenue_ron ? ` · ${lei(e.outcome.revenue_ron)}` : ""}</span>
                           : <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">ÎN FEREASTRĂ</span>}
                        <span className="text-[10px] text-slate-400 ml-auto">{e.approved_by || "—"} · {e.created_at && new Date(e.created_at).toLocaleDateString("ro-RO")}</span>
                      </div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{e.recommendation}</div>
                      {e.reason && <div className="text-[11px] text-slate-500 truncate">{e.reason}</div>}
                    </div>
                  );
                })}
              </div>
            )}
          </AdminCard>

          <div className="text-[10px] text-slate-400" data-testid="le-meta">
            Ferestre de atribuire: 7 zile (revenire/conversie) · 30 zile (cerere/venit) · model: last-touch (arhitectura GI-4, frozen) ·
            scan automat zilnic 07:20 · ledger append-only = sursa de adevăr pentru deciziile AI
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
