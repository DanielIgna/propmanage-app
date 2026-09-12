// CommandCenterPage — 🧠 AI Command Center: feed zilnic unificat + Top 5 recomandări AI.
// Adminul nu mai caută informația — primește prioritățile.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Brain, Inbox, Users, CheckCircle2, TrendingUp, AlertTriangle,
  Sparkles, RefreshCw, Zap, ExternalLink, Gem,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const SEV = {
  high:   { label: "URGENT",   cls: "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/40 text-rose-700 dark:text-rose-300", badge: "bg-rose-500 text-white" },
  medium: { label: "ATENȚIE",  cls: "bg-amber-50 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/40 text-amber-700 dark:text-amber-300", badge: "bg-amber-400 text-slate-900" },
  low:    { label: "INFO",     cls: "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300", badge: "bg-slate-400 text-white" },
};

const ICONS = { inbox: Inbox, users: Users, check: CheckCircle2, trend: TrendingUp, gem: Gem };

export default function CommandCenterPage() {
  const [feed, setFeed] = useState(null);
  const [recos, setRecos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, r] = await Promise.all([
        ax.get("/admin/command-center/feed"),
        ax.get("/admin/command-center/recommendations/latest"),
      ]);
      setFeed(f.data);
      setRecos(r.data.recommendations ? r.data : null);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await ax.post("/admin/command-center/recommendations");
      setRecos(r.data);
    } catch (e) { /* silent */ }
    setGenerating(false);
  };

  const accents = ["info", "ai", "success", "warning"];

  return (
    <AdminLayoutMetronic
      title="AI Command Center"
      subtitle="Feed zilnic unificat · alerte operaționale · Top 5 recomandări AI — prioritățile vin la tine"
    >
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : (
        <div className="space-y-6" data-testid="command-center-root">
          {/* Astăzi */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {(feed?.stats || []).map((s, i) => (
              <KpiCard key={s.key} icon={ICONS[s.icon] || Inbox} label={s.label} value={s.value} accent={accents[i % 4]} testid={`cc-stat-${s.key}`} />
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            {/* Alerte */}
            <AdminCard
              title={<span className="flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-500" /> Alerte operaționale ({feed?.warnings?.length || 0})</span>}
              action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="cc-refresh">Refresh</DSButton>}
              testid="cc-warnings"
            >
              <div className="space-y-2">
                {(feed?.warnings || []).map((w) => {
                  const sv = SEV[w.severity] || SEV.low;
                  const isHealth = w.key.startsWith("health_");
                  return (
                    <div key={w.key} className={`flex items-start gap-2 p-3 rounded-xl border ${sv.cls}`} data-testid={`cc-warning-${w.key}`}>
                      <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded shrink-0 ${sv.badge}`}>{isHealth ? "HEALTH" : sv.label}</span>
                      <span className="text-sm font-medium flex-1">{w.label}</span>
                      {w.link && <a href={w.link} className="shrink-0 text-[10px] font-black underline opacity-70 hover:opacity-100" data-testid={`cc-warning-link-${w.key}`}>Vezi →</a>}
                    </div>
                  );
                })}
                {!feed?.warnings?.length && (
                  <EmptyState icon={CheckCircle2} title="Zero alerte" hint="Totul e sub control operațional azi." />
                )}
              </div>
            </AdminCard>

            {/* Recomandările AI */}
            <AdminCard
              title={<span className="flex items-center gap-2"><Brain className="w-4 h-4 text-lime-500" /> Recomandările AI — Top 5 azi</span>}
              action={<DSButton variant="primary" icon={generating ? RefreshCw : Sparkles} disabled={generating} onClick={generate} data-testid="cc-generate-btn">{generating ? "Claude analizează…" : "Generează"}</DSButton>}
              testid="cc-recos"
            >
              {generating && <DSSkeleton kpis={0} blocks={1} />}
              {!generating && !recos && (
                <EmptyState icon={Brain} title="Nicio recomandare încă" hint="AI-ul citește snapshot-ul operațional (cereri, escrow, specialiști, dispute) și îți dă 5 acțiuni concrete pentru azi." />
              )}
              {!generating && recos && (
                <div className="space-y-2" data-testid="cc-recos-body">
                  {(recos.recommendations || []).map((r, i) => {
                    const sv = SEV[r.severity] || SEV.medium;
                    return (
                      <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 ${r.done ? "opacity-50" : ""}`} data-testid={`cc-reco-${i}`}>
                        <button
                          onClick={async () => { try { await ax.post("/admin/command-center/recommendations/toggle", { idx: r.idx ?? i }); load(); const rr = await ax.get("/admin/command-center/recommendations/latest"); setRecos(rr.data); } catch (e) { /* silent */ } }}
                          className={`w-6 h-6 rounded-full text-xs font-black flex items-center justify-center shrink-0 border-2 transition-colors ${r.done ? "bg-emerald-500 border-emerald-500 text-white" : "bg-lime-400 border-lime-400 text-slate-900 hover:bg-emerald-400"}`}
                          title={r.done ? "Marchează nerezolvat" : "Marchează rezolvat"}
                          data-testid={`cc-reco-toggle-${i}`}
                        >
                          {r.done ? "✓" : i + 1}
                        </button>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${sv.badge}`}>{sv.label}</span>
                            {r.category && <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300" data-testid={`cc-reco-category-${i}`}>{r.category}</span>}
                            {r.module && <span className="text-[10px] font-bold text-slate-400">{r.module}</span>}
                          </div>
                          <div className={`text-sm font-bold text-slate-900 dark:text-white mt-0.5 ${r.done ? "line-through" : ""}`}>{r.action}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">{r.why}</div>
                        </div>
                        {r.link && (
                          <a href={r.link} className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[10px] font-black bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-80" data-testid={`cc-reco-open-${i}`}>
                            Deschide <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    );
                  })}
                  <div className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    {recos.ai_generated ? "Generat de Claude pe datele reale" : "Fallback rule-based"} · {recos.generated_at && new Date(recos.generated_at).toLocaleString("ro-RO")}
                  </div>
                </div>
              )}
            </AdminCard>
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
