// LeadIntelligencePage — Board GI-2: Intent & Lead Intelligence.
// Scor de intenție 0-100 din comportament real → vizitator/prospect/calificat/fierbinte/client.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Flame, Users, Target, RefreshCw, AlertTriangle, Radar, TrendingUp, Sparkles,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton, EmptyState } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const TIERS = {
  client:    { label: "Client",         cls: "bg-slate-900 text-lime-300" },
  hot:       { label: "Lead fierbinte", cls: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  qualified: { label: "Lead calificat", cls: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  prospect:  { label: "Prospect",       cls: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  visitor:   { label: "Vizitator",      cls: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-300" },
};

export default function LeadIntelligencePage() {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [tier, setTier] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  const load = async (t = tier) => {
    try {
      const [s, l] = await Promise.all([
        ax.get("/admin/lead-intel/stats"),
        ax.get(`/admin/lead-intel/leads${t ? `?tier=${t}` : ""}`),
      ]);
      setStats(s.data);
      setLeads(l.data.items || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
    }
    setLoading(false);
  };
  const runScan = async () => {
    setRunning(true);
    try { await ax.post("/admin/lead-intel/run"); await load(); } catch (e) { /* silent */ }
    setRunning(false);
  };
  useEffect(() => { load(); }, []);

  const t = stats?.tiers || {};

  return (
    <AdminLayoutMetronic
      title="Lead & Intent Intelligence"
      subtitle="Intent Score din comportament real — reveniri, Digital Twin, audit, cereri, WhatsApp (Board GI-2)"
    >
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : err ? (
        <div className="p-4 rounded-xl bg-rose-50 text-rose-700 text-sm" data-testid="li-error"><AlertTriangle className="w-4 h-4 inline mr-1.5" />{err}</div>
      ) : (
        <div className="space-y-6" data-testid="li-root">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <KpiCard icon={Flame} label="Lead-uri fierbinți" value={t.hot ?? 0} accent="danger" testid="li-kpi-hot" />
            <KpiCard icon={Target} label="Lead-uri calificate" value={t.qualified ?? 0} accent="warning" testid="li-kpi-qualified" />
            <KpiCard icon={TrendingUp} label="Prospects" value={t.prospect ?? 0} accent="info" testid="li-kpi-prospects" />
            <KpiCard icon={Users} label="Clienți" value={t.client ?? 0} accent="success" testid="li-kpi-clients" />
            <KpiCard icon={Radar} label="Scor mediu" value={stats?.avg_score ?? 0} accent="ai" testid="li-kpi-avg" />
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-lime-500" /> Top semnale de intenție în ecosistem</span>}
            action={<DSButton variant="primary" icon={RefreshCw} disabled={running} onClick={runScan} data-testid="li-run-btn">{running ? "Scorează…" : "Rulează scoring"}</DSButton>}
            testid="li-signals-card"
          >
            <div className="flex flex-wrap gap-2">
              {(stats?.top_signals || []).map((s, i) => (
                <span key={i} className="px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200" data-testid={`li-signal-${i}`}>
                  {s.label} <span className="text-slate-400">×{s.count}</span>
                </span>
              ))}
              {!(stats?.top_signals || []).length && <span className="text-xs text-slate-400">Fără semnale încă — rulează scoring-ul.</span>}
            </div>
            <div className="mt-3 text-[10px] text-slate-400">
              Model v1 rule-based · nivel validare: <b>Ipoteză AI</b> (Board 006) — se calibrează cu conversii reale în Learning Engine (GI-4) ·
              Revenue Hunter prioritizează automat proprietățile lead-urilor fierbinți/calificate
            </div>
          </AdminCard>

          <AdminCard
            title={<span className="flex items-center gap-2"><Flame className="w-4 h-4 text-rose-500" /> Lead-uri (sortate după Intent Score)</span>}
            action={
              <div className="flex gap-1.5">
                {["", "hot", "qualified", "prospect", "client"].map((tk) => (
                  <button key={tk} onClick={() => { setTier(tk); load(tk); }}
                    className={`px-2.5 py-1 rounded-full text-[10px] font-black transition-colors ${tier === tk ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-slate-100 dark:bg-slate-800 text-slate-500"}`}
                    data-testid={`li-filter-${tk || "all"}`}>
                    {tk ? TIERS[tk].label : "Toate"}
                  </button>
                ))}
              </div>
            }
            testid="li-leads-card"
          >
            {!leads.length ? (
              <EmptyState icon={Radar} title="Niciun lead în acest filtru" hint="Scorurile se recalculează zilnic la 06:50 din comportamentul real." />
            ) : (
              <div className="space-y-2">
                {leads.map((l, i) => {
                  const tr = TIERS[l.tier] || TIERS.visitor;
                  return (
                    <div key={l.visitor_id || i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`li-lead-${i}`}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="xos-num text-lg font-black text-slate-900 dark:text-white">{l.score}</span>
                        <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${tr.cls}`}>{tr.label}</span>
                        {l.conv_probability_pct != null && <span className="text-[10px] font-bold text-slate-400">~{l.conv_probability_pct}% probabilitate conversie</span>}
                        <span className="text-[10px] text-slate-400 ml-auto">{l.user_email || `vizitator ${String(l.visitor_id).slice(0, 8)}…`} · {(l.sources || []).join(", ")} · {l.sessions} sesiuni</span>
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {(l.signals || []).slice(0, 6).map((s, j) => (
                          <span key={j} className={`text-[10px] px-2 py-0.5 rounded-full ${s.points < 0 ? "bg-rose-50 text-rose-600 dark:bg-rose-500/10" : "bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300"}`}>
                            {s.label} {s.points > 0 ? `+${s.points}` : s.points}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </AdminCard>

          <div className="text-[10px] text-slate-400" data-testid="li-meta">
            Ultima scanare: {stats?.last_scan?.generated_at && new Date(stats.last_scan.generated_at).toLocaleString("ro-RO")} ·
            {stats?.last_scan?.scanned ?? 0} vizitatori scorați · rulare automată zilnică 06:50 (înaintea Revenue Hunter)
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
