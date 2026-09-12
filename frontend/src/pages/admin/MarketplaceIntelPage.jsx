// MarketplaceIntelPage — cerere vs ofertă per categorie cu bare de deficit + recomandări AI.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Radar, Sparkles, RefreshCw, TrendingUp, UserPlus, Megaphone, Eye } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS = {
  deficit:  { label: "DEFICIT",    cls: "bg-rose-500 text-white" },
  surplus:  { label: "SUPRAOFERTĂ", cls: "bg-cyan-500 text-white" },
  balanced: { label: "ECHILIBRAT", cls: "bg-emerald-500 text-white" },
};
const RECO_TYPE = { recruit: UserPlus, promote: Megaphone, monitor: Eye };

const Bar = ({ label, value, max, cls }) => (
  <div className="flex items-center gap-2 text-xs">
    <span className="w-20 shrink-0 text-slate-500">{label}</span>
    <div className="flex-1 h-3.5 bg-slate-100 dark:bg-slate-700 rounded overflow-hidden">
      <div className={`h-full ${cls}`} style={{ width: `${max ? Math.min(100, (value / max) * 100) : 0}%` }} />
    </div>
    <span className="w-10 text-right font-black text-slate-800 dark:text-slate-100">{value}</span>
  </div>
);

export default function MarketplaceIntelPage() {
  const [data, setData] = useState(null);
  const [counties, setCounties] = useState([]);
  const [radar, setRadar] = useState([]);
  const [recos, setRecos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, r, c, rd] = await Promise.all([
        ax.get("/admin/marketplace-intel/supply-demand"),
        ax.get("/admin/marketplace-intel/recommend/latest"),
        ax.get("/admin/marketplace-intel/by-county"),
        ax.get("/admin/marketplace-intel/radar"),
      ]);
      setData(d.data);
      setRecos(r.data.recommendations ? r.data : null);
      setCounties(c.data.counties || []);
      setRadar(rd.data.trends || []);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await ax.post("/admin/marketplace-intel/recommend");
      setRecos(r.data);
    } catch (e) { /* silent */ }
    setGenerating(false);
  };

  const maxVal = Math.max(1, ...(data?.categories || []).flatMap((c) => [c.demand, c.capacity]));

  return (
    <AdminLayoutMetronic
      title="Marketplace Intelligence"
      subtitle={`Cerere vs Ofertă per categorie (fereastră: ${data?.window || "30 zile"}) — AI recomandă unde să investești`}
    >
      {loading ? <DSSkeleton kpis={0} blocks={2} /> : (
        <div className="space-y-6" data-testid="marketplace-intel-root">
          <div className="grid lg:grid-cols-5 gap-4">
            <AdminCard className="lg:col-span-3"
              title={<span className="flex items-center gap-2"><Radar className="w-4 h-4 text-lime-500" /> Balanța cerere vs capacitate</span>}
              action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="mi-refresh">Refresh</DSButton>}
              testid="mi-balance"
            >
              <div className="space-y-4">
                {(data?.categories || []).map((c) => {
                  const st = STATUS[c.status];
                  return (
                    <div key={c.key} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`mi-cat-${c.key}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-bold text-slate-900 dark:text-white">{c.label}</span>
                        <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${st.cls}`} data-testid={`mi-status-${c.key}`}>
                          {st.label}{c.pct ? ` ${c.pct}%` : ""}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        <Bar label="Cerere" value={c.demand} max={maxVal} cls="bg-lime-400" />
                        <Bar label="Capacitate" value={c.capacity} max={maxVal} cls="bg-slate-400 dark:bg-slate-500" />
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1.5">{c.supply} specialiști × {data?.jobs_per_specialist} lucrări/lună = capacitate {c.capacity}</div>
                    </div>
                  );
                })}
                {!data?.categories?.length && <EmptyState icon={Radar} title="Fără date" hint="Nu există cereri sau specialiști în fereastra analizată." />}
              </div>
            </AdminCard>

            <AdminCard className="lg:col-span-2"
              title={<span className="flex items-center gap-2"><TrendingUp className="w-4 h-4 text-lime-500" /> AI — unde investești</span>}
              action={<DSButton variant="primary" icon={generating ? RefreshCw : Sparkles} disabled={generating} onClick={generate} data-testid="mi-recommend-btn">{generating ? "Analizează…" : "Recomandă"}</DSButton>}
              testid="mi-recos"
            >
              {generating && <DSSkeleton kpis={0} blocks={1} />}
              {!generating && !recos && <EmptyState icon={TrendingUp} title="Nicio analiză încă" hint="AI-ul citește balanța cerere/ofertă și îți spune unde să recrutezi și unde să promovezi." />}
              {!generating && recos && (
                <div className="space-y-3" data-testid="mi-recos-body">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{recos.summary}</p>
                  {(recos.recommendations || []).map((r, i) => {
                    const Icon = RECO_TYPE[r.type] || Eye;
                    return (
                      <div key={i} className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid={`mi-reco-${i}`}>
                        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${r.priority === "high" ? "text-rose-500" : r.priority === "medium" ? "text-amber-500" : "text-slate-400"}`} />
                        <div>
                          <div className="text-[10px] font-bold uppercase text-slate-400">{r.category}</div>
                          <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">{r.action}</div>
                        </div>
                      </div>
                    );
                  })}
                  <div className="text-[10px] text-slate-400">{recos.ai_generated ? "Claude · date reale" : "Fallback rule-based"} · {recos.generated_at && new Date(recos.generated_at).toLocaleString("ro-RO")}</div>
                </div>
              )}
            </AdminCard>
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><Radar className="w-4 h-4 text-lime-500" /> Marketplace Radar — trenduri 30 zile ({radar.filter((t) => t.hot).length} 🔥 hot)</span>}
            testid="mi-radar"
          >
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {radar.map((t) => (
                <div key={t.key} className={`p-3 rounded-xl border ${t.hot ? "border-lime-300 dark:border-lime-500/40 bg-lime-50 dark:bg-lime-500/10" : "border-slate-200 dark:border-slate-700"}`} data-testid={`mi-radar-${t.key}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-slate-900 dark:text-white">{t.hot ? "🔥 " : ""}{t.label}</span>
                    <span className={`text-sm font-black ${t.direction === "up" ? "text-emerald-600 dark:text-emerald-300" : t.direction === "down" ? "text-rose-600 dark:text-rose-300" : "text-slate-400"}`}>
                      {t.trend_pct > 0 ? "+" : ""}{t.trend_pct}%
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500">{t.current_30d} cereri (30z) vs {t.previous_30d} anterior</div>
                </div>
              ))}
              {!radar.length && <div className="text-xs text-slate-400 col-span-full">Fără date de trend încă.</div>}
            </div>
          </AdminCard>

          <AdminCard
            title={<span className="flex items-center gap-2"><Radar className="w-4 h-4 text-lime-500" /> City Analytics — cerere vs capacitate pe județe (90 zile)</span>}
            testid="mi-counties"
          >
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {counties.map((c) => {
                const st = STATUS[c.status];
                return (
                  <div key={c.county} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`mi-county-${c.county}`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-bold text-slate-900 dark:text-white">{c.county}</span>
                      <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${st.cls}`}>{st.label}{c.pct ? ` ${c.pct}%` : ""}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 space-y-0.5">
                      <div>{c.demand} cereri · {c.supply} specialiști</div>
                      <div className="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div className={`h-full ${c.status === "deficit" ? "bg-rose-500" : "bg-lime-400"}`} style={{ width: `${Math.min(100, c.capacity ? (c.demand / c.capacity) * 100 : 100)}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
              {!counties.length && <div className="text-xs text-slate-400 col-span-full">Fără date pe județe încă.</div>}
            </div>
          </AdminCard>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
