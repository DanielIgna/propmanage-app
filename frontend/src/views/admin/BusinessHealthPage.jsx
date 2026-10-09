// BusinessHealthPage — 8 scoruri pe departamente, VERDE/GALBEN/ROȘU, din date reale.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Activity, RefreshCw } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { DSButton, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const COLOR = {
  green:  { ring: "#10b981", text: "text-emerald-600 dark:text-emerald-300", bg: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30", label: "SĂNĂTOS" },
  yellow: { ring: "#f59e0b", text: "text-amber-600 dark:text-amber-300",     bg: "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30",       label: "ATENȚIE" },
  red:    { ring: "#f43f5e", text: "text-rose-600 dark:text-rose-300",       bg: "bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30",           label: "CRITIC" },
};

const ScoreRing = ({ score, color }) => {
  const r = 30, c = 2 * Math.PI * r;
  return (
    <svg width="76" height="76" viewBox="0 0 76 76">
      <circle cx="38" cy="38" r={r} fill="none" stroke="currentColor" strokeWidth="6" className="text-slate-100 dark:text-slate-700" />
      <circle cx="38" cy="38" r={r} fill="none" stroke={COLOR[color].ring} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} transform="rotate(-90 38 38)" style={{ transition: "stroke-dashoffset 600ms" }} />
      <text x="38" y="43" textAnchor="middle" className="fill-slate-900 dark:fill-white" fontSize="18" fontWeight="900">{score}</text>
    </svg>
  );
};

const Sparkline = ({ points, color }) => {
  if (!points || points.length < 2) return <span className="text-[9px] text-slate-400">trend din a 2-a zi</span>;
  const w = 72, h = 20;
  const min = Math.min(...points), max = Math.max(...points);
  const range = max - min || 1;
  const path = points.map((p, i) => `${(i / (points.length - 1)) * w},${h - ((p - min) / range) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={path} fill="none" stroke={COLOR[color].ring} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
};

export default function BusinessHealthPage() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [menuStats, setMenuStats] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [r, h, m] = await Promise.all([
        ax.get("/admin/business-health"),
        ax.get("/admin/business-health/history?days=30"),
        ax.get("/admin/site-menu/analytics?days=30").catch(() => ({ data: null })),
      ]);
      setData(r.data);
      setHistory(h.data.history || []);
      setMenuStats(m.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const oc = data ? COLOR[data.overall_color] : COLOR.yellow;

  return (
    <AdminLayoutMetronic
      title="Business Health"
      subtitle="8 scoruri pe departamente calculate din datele reale — VERDE sănătos · GALBEN atenție · ROȘU critic"
    >
      {loading ? <DSSkeleton kpis={4} blocks={1} /> : (
        <div className="space-y-6" data-testid="business-health-root">
          <AdminCard testid="bh-overall"
            title={<span className="flex items-center gap-2"><Activity className="w-4 h-4 text-lime-500" /> Scor general de sănătate</span>}
            action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="bh-refresh">Recalculează</DSButton>}
          >
            <div className="flex items-center gap-4">
              <ScoreRing score={Math.round(data?.overall ?? 0)} color={data?.overall_color || "yellow"} />
              <div>
                <div className={`text-[10px] font-black uppercase px-2 py-0.5 rounded inline-block border ${oc.bg} ${oc.text}`}>{oc.label}</div>
                <div className="text-sm text-slate-600 dark:text-slate-300 mt-1.5">
                  Media celor 8 departamente. Fiecare scor e o formulă deterministă pe datele din DB — nu estimări.
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <Sparkline points={history.map((h) => h.overall)} color={data?.overall_color || "yellow"} />
                  <span className="text-[10px] text-slate-400" data-testid="bh-history-info">{history.length} snapshot{history.length === 1 ? "" : "-uri"} zilnice (30z)</span>
                </div>
              </div>
            </div>
          </AdminCard>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {(data?.departments || []).map((d) => {
              const c = COLOR[d.color];
              return (
                <div key={d.key} className={`rounded-2xl border p-4 flex flex-col items-center text-center gap-2 ${c.bg}`} data-testid={`bh-dept-${d.key}`}>
                  <ScoreRing score={d.score} color={d.color} />
                  <div className="text-sm font-black text-slate-900 dark:text-white">{d.label}</div>
                  <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${c.text}`}>{c.label}</span>
                  <Sparkline points={history.map((h) => h.scores?.[d.key]).filter((v) => v != null)} color={d.color} />
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">{d.detail}</div>
                </div>
              );
            })}
          </div>

          <AdminCard testid="bh-attribution" title={<span className="flex items-center gap-2">🎯 Atribuire Google Ads → conversii (30 zile)</span>}>
            {!data?.attribution || (data.attribution.conversions_total === 0 && data.attribution.ad_visitors === 0) ? (
              <div className="text-xs text-slate-400 py-3" data-testid="bh-attribution-empty">
                Încă nu există trafic Google Ads înregistrat. Datele apar pe măsură ce vizitatorii ajung din campanii (link cu <code>gclid</code>) și convertesc (cont creat / cerere / plată). Cont Google Ads: <strong>AW-18423416296</strong>.
              </div>
            ) : (
              <div className="space-y-3" data-testid="bh-attribution-data">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                    <div className="text-lg font-black text-slate-900 dark:text-white">{data.attribution.ad_visitors}</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Vizitatori din Google Ads</div>
                  </div>
                  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                    <div className="text-lg font-black text-lime-600 dark:text-lime-300">{data.attribution.conversions_ad_attributed}</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Conversii atribuite Ads</div>
                  </div>
                  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                    <div className="text-lg font-black text-slate-900 dark:text-white">{data.attribution.ad_signup_rate_pct ?? "—"}%</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Rată signup (trafic Ads)</div>
                  </div>
                  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                    <div className="text-lg font-black text-emerald-600 dark:text-emerald-300">{(data.attribution.ad_attributed_value_ron ?? 0).toLocaleString()} lei</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Valoare plăți atribuite</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  {["sign_up", "first_request", "offer_accepted", "purchase"].map((a) => {
                    const v = data.attribution.conversions_by_action?.[a] || { total: 0, ad_attributed: 0 };
                    const lbl = { sign_up: "Cont creat", first_request: "Prima cerere", offer_accepted: "Ofertă acceptată", purchase: "Plată" }[a];
                    return (
                      <span key={a} className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200" data-testid={`bh-attr-${a}`}>
                        {lbl}: <strong>{v.total}</strong> <span className="text-slate-400">({v.ad_attributed} din Ads)</span>
                      </span>
                    );
                  })}
                </div>
                {(data.attribution.top_campaigns || []).length > 0 && (
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    Top campanii: {data.attribution.top_campaigns.map((c) => `${c.campaign} (${c.conversions})`).join(" · ")}
                  </div>
                )}
                <div className="text-[10px] text-slate-400">Google Ads <strong>AW-18423416296</strong> · doar cu consimțământ „Marketing" (Consent Mode v2).</div>
              </div>
            )}
          </AdminCard>


          <AdminCard testid="bh-menu-clicks" title="📊 Top servicii căutate din meniu (30 zile)">
            {!menuStats || menuStats.total_clicks === 0 ? (
              <div className="text-xs text-slate-400 py-3">Încă nu există click-uri înregistrate în meniu. Datele apar pe măsură ce vizitatorii navighează.</div>
            ) : (
              <div className="space-y-2">
                <div className="text-[11px] text-slate-400">{menuStats.total_clicks} click-uri totale în meniu</div>
                {menuStats.top.slice(0, 10).map((row, i) => {
                  const max = menuStats.top[0]?.clicks || 1;
                  return (
                    <div key={row.item_id} className="flex items-center gap-3" data-testid={`bh-menu-row-${row.item_id}`}>
                      <span className="text-[10px] font-black text-slate-400 w-5">{i + 1}.</span>
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-200 w-40 truncate">{row.label || row.item_id}</span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div className="h-full rounded-full bg-lime-400" style={{ width: `${Math.max(6, (row.clicks / max) * 100)}%` }} />
                      </div>
                      <span className="text-xs font-black text-slate-900 dark:text-white w-10 text-right">{row.clicks}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </AdminCard>

          <div className="text-[10px] text-slate-400">
            Formule: Marketing = creștere useri 30z · Marketplace = fill rate cereri · Escrow = eliberate vs înghețate · Specialiști = verificare + profil complet · Suport = dispute rezolvate · Conversii = plăți finalizate · SEO = media audit pagini publice · Financiar = creștere revenue 30z.
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
