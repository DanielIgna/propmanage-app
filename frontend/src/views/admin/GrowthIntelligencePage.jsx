// GrowthIntelligencePage — Board 004/005/006: agentul permanent care analizează
// comportamentul REAL și răspunde direct: când postezi, ce sursă convertește, ce repari.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  TrendingUp, RefreshCw, MessageCircle, Megaphone, Wrench, Crown,
  AlertTriangle, LogOut, Route, Clock, Target, Radar,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton, EmptyState } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const VALIDATION = {
  confirmed_real:      { label: "Confirmată de date reale", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  partially_confirmed: { label: "Confirmată parțial",       cls: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  ai_hypothesis:       { label: "Ipoteză AI",               cls: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  rejected:            { label: "Respinsă de date",         cls: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};
const CATEGORY = {
  ux:          { label: "UX",         icon: Wrench,        cls: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300" },
  marketing:   { label: "Marketing",  icon: Megaphone,     cls: "bg-lime-100 text-lime-800 dark:bg-lime-500/15 dark:text-lime-300" },
  comercial:   { label: "Comercial",  icon: Target,        cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  ceo:         { label: "CEO",        icon: Crown,         cls: "bg-slate-900 text-lime-300 dark:bg-slate-700" },
  operational: { label: "Operațional", icon: Wrench,       cls: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300" },
};

export const ValidationBadge = ({ level, testid }) => {
  const v = VALIDATION[level] || VALIDATION.ai_hypothesis;
  return <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${v.cls}`} data-testid={testid}>{v.label}</span>;
};

const BehaviorRow = ({ icon: Icon, label, value, evidence, validation, testid }) => (
  <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={testid}>
    <Icon className="w-4 h-4 text-lime-600 mt-0.5 shrink-0" />
    <div className="min-w-0 flex-1">
      <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">{label}</div>
      <div className="text-sm font-bold text-slate-900 dark:text-white">{value || "—"}</div>
      {evidence && <div className="text-[11px] text-slate-500 mt-0.5">{evidence}</div>}
    </div>
    <ValidationBadge level={validation} />
  </div>
);

export default function GrowthIntelligencePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const r = await ax.get("/admin/growth-intel/latest");
      setData(r.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
    }
    setLoading(false);
  };
  const runScan = async () => {
    setRunning(true);
    try {
      const r = await ax.post("/admin/growth-intel/run");
      setData(r.data);
    } catch (e) { /* silent */ }
    setRunning(false);
  };

  useEffect(() => { load(); }, []);

  const k = data?.kpi_snapshot || {};
  const beh = data?.behavior || {};
  const confirmedCount = (data?.recommendations || []).filter((r) => r.validation === "confirmed_real").length;

  return (
    <AdminLayoutMetronic
      title="Growth Intelligence"
      subtitle="Agent permanent pe date reale — Observă → Învață → Recomandă → Testează → Măsoară (Board 006)"
    >
      {loading ? <DSSkeleton kpis={4} blocks={3} /> : err ? (
        <div className="p-4 rounded-xl bg-rose-50 text-rose-700 text-sm" data-testid="gi-error"><AlertTriangle className="w-4 h-4 inline mr-1.5" />{err}</div>
      ) : (
        <div className="space-y-6" data-testid="gi-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Radar} label={`Sesiuni analizate (${data?.period_days || 30}z)`} value={k.sessions ?? 0} accent="ai" testid="gi-kpi-sessions" />
            <KpiCard icon={LogOut} label="Bounce rate" value={`${k.bounce_rate_pct ?? 0}%`} accent="warning" testid="gi-kpi-bounce" />
            <KpiCard icon={Target} label="Oportunități active" value={k.active_opportunities ?? 0} accent="success" testid="gi-kpi-opps" />
            <KpiCard icon={TrendingUp} label="Confirmate de date reale" value={`${confirmedCount}/${(data?.recommendations || []).length}`} accent="info" testid="gi-kpi-confirmed" />
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Clock className="w-4 h-4 text-lime-500" /> Behavioral Intelligence — răspunsuri directe</span>}
            action={<DSButton variant="primary" icon={RefreshCw} disabled={running} onClick={runScan} data-testid="gi-run-btn">{running ? "Analizează…" : "Rulează scanarea"}</DSButton>}
            testid="gi-behavior-card"
          >
            <div className="grid lg:grid-cols-2 gap-2">
              <BehaviorRow icon={MessageCircle} label="Moment optim mesaje WhatsApp" value={beh.best_whatsapp_time?.text}
                evidence={beh.best_whatsapp_time?.evidence} validation={beh.best_whatsapp_time?.validation} testid="gi-whatsapp-time" />
              <BehaviorRow icon={Megaphone} label="Moment optim postări / campanii" value={beh.best_post_time?.text}
                evidence={beh.best_post_time?.evidence} validation={beh.best_post_time?.validation} testid="gi-post-time" />
              <BehaviorRow icon={TrendingUp} label="Comparație surse de trafic" value={beh.source_comparison?.text}
                evidence={(beh.source_comparison?.sources || []).map((s) => `${s.source}: ${s.visitors} vizitatori · ${s.conv_pct}%`).join(" · ")}
                validation={beh.source_comparison?.validation} testid="gi-source-comparison" />
              <BehaviorRow icon={Target} label="Serviciul cu cea mai mare tracțiune" value={beh.top_service?.text}
                validation={beh.top_service?.validation} testid="gi-top-service" />
            </div>
          </AdminCard>

          <div className="grid lg:grid-cols-2 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-500" /> Top probleme UX (date reale)</span>} testid="gi-ux-problems">
              {!(data?.ux_problems || []).length ? (
                <EmptyState icon={Wrench} title="Nicio problemă detectată" hint="Fie UX-ul e curat, fie traficul e prea mic pentru semnal — distribuie campanii pentru date." />
              ) : (
                <div className="space-y-2">
                  {data.ux_problems.map((p, i) => (
                    <div key={i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`gi-ux-problem-${i}`}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-black text-slate-400 uppercase">{p.type}</span>
                        <ValidationBadge level={p.validation} />
                      </div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{p.label}</div>
                      <div className="text-[11px] text-slate-500">{p.evidence}</div>
                    </div>
                  ))}
                </div>
              )}
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2"><LogOut className="w-4 h-4 text-rose-500" /> Pagini de abandon</span>} testid="gi-abandon-pages">
              {!(data?.abandon_pages || []).length ? (
                <EmptyState icon={LogOut} title="Fără date de ieșire" hint="Apare automat când există sesiuni cu navigare." />
              ) : (
                <div className="space-y-1.5">
                  {data.abandon_pages.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={`gi-abandon-${i}`}>
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate">{p.path}</span>
                      <span className="text-xs font-black text-slate-500 shrink-0 ml-2">{p.exits} ieșiri · {p.exit_share_pct}%</span>
                    </div>
                  ))}
                </div>
              )}
            </AdminCard>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><Route className="w-4 h-4 text-lime-500" /> Traseele reale ale utilizatorilor</span>} testid="gi-journeys">
              {!(data?.journeys || []).length ? (
                <EmptyState icon={Route} title="Fără trasee încă" hint="Se populează din navigarea reală a vizitatorilor." />
              ) : (
                <div className="space-y-1.5">
                  {data.journeys.map((j, i) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid={`gi-journey-${i}`}>
                      <span className="text-xs font-mono text-slate-700 dark:text-slate-200 truncate">{j.journey}</span>
                      <span className="text-xs font-black text-slate-500 shrink-0 ml-2">×{j.sessions}</span>
                    </div>
                  ))}
                </div>
              )}
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2"><Radar className="w-4 h-4 text-lime-500" /> Recomandările agentului</span>} testid="gi-recos">
              {!(data?.recommendations || []).length ? (
                <EmptyState icon={Radar} title="Nicio recomandare" hint="Rulează scanarea pentru a genera recomandări." />
              ) : (
                <div className="space-y-2">
                  {data.recommendations.map((r, i) => {
                    const cat = CATEGORY[r.category] || CATEGORY.operational;
                    return (
                      <div key={r.id || i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`gi-reco-${i}`}>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${cat.cls}`}>{cat.label}</span>
                          <ValidationBadge level={r.validation} testid={`gi-reco-validation-${i}`} />
                          {r.kpi && <span className="text-[10px] font-bold text-slate-400">KPI: {r.kpi}</span>}
                        </div>
                        <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{r.title}</div>
                        <div className="text-xs text-slate-500">{r.why}</div>
                        {r.evidence && <div className="text-[11px] text-slate-400 mt-0.5">Dovadă: {r.evidence}</div>}
                      </div>
                    );
                  })}
                </div>
              )}
            </AdminCard>
          </div>

          <div className="text-[10px] text-slate-400" data-testid="gi-meta">
            Ultima scanare: {data?.generated_at && new Date(data.generated_at).toLocaleString("ro-RO")} · trigger: {data?.trigger} ·
            rulare automată zilnică 06:40 · nicio recomandare nu se implementează fără confruntarea cu datele reale (Board 006)
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
