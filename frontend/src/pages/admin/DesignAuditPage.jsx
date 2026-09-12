// DesignAuditPage — Admin module. Evaluates UX/UI unity + mobile vs desktop impact
// per page using Claude (Emergent LLM key). Follows the Business Design System strictly.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Palette, Smartphone, Monitor, Sparkles, RefreshCw,
  CheckCircle2, AlertTriangle, ArrowRight, Layers, Compass,
  Users, MousePointer2, Eye, Accessibility, Brain,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSBadge, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const ScoreDial = ({ value, label, icon: Icon, testid }) => {
  const v = value ?? 0;
  const tone = v >= 85 ? "text-emerald-600 dark:text-emerald-300" : v >= 70 ? "text-lime-600 dark:text-lime-300" : v >= 50 ? "text-amber-600 dark:text-amber-300" : "text-rose-600 dark:text-rose-300";
  const bg = v >= 85 ? "bg-emerald-500" : v >= 70 ? "bg-lime-400" : v >= 50 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex flex-col items-center justify-center p-3 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid={testid}>
      <Icon className={`w-4 h-4 mb-1 ${tone}`} />
      <div className={`text-2xl font-black leading-none ${tone}`}>{value ?? "—"}</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mt-1">{label}</div>
      <div className="mt-2 h-1.5 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${bg} transition-all`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
};

const ZoneTag = ({ zone }) => {
  const map = {
    public:     "bg-cyan-50 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300",
    client:     "bg-lime-50 dark:bg-lime-500/15 text-lime-700 dark:text-lime-300",
    specialist: "bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300",
    operator:   "bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    admin:      "bg-slate-100 dark:bg-slate-700/50 text-slate-700 dark:text-slate-200",
  };
  return <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${map[zone] || map.admin}`}>{zone}</span>;
};

export default function DesignAuditPage() {
  const [pages, setPages] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([
        ax.get("/admin/design-audit/pages"),
        ax.get("/admin/design-audit/summary"),
      ]);
      setPages(p.data.pages || []);
      setSummary(s.data);
    } catch (e) {
      /* silent */
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const runAudit = async (key, force = false) => {
    setActive(key);
    setResult(null);
    setRunning(true);
    try {
      const r = await ax.get(`/admin/design-audit/analyze?key=${key}${force ? "&force=true" : ""}`);
      setResult(r.data);
      // refresh list scores
      load();
    } catch (e) {
      setResult({ error: e?.response?.data?.detail || "Eroare la analiză." });
    }
    setRunning(false);
  };

  return (
    <AdminLayoutMetronic
      title="Design Audit"
      subtitle="Evaluare UX/UI · Impact mobile vs desktop · Legea lui Hick · Unitate vizuală"
    >
      {loading ? <DSSkeleton kpis={4} blocks={1} /> : (
        <div className="space-y-6" data-testid="design-audit-root">
          {/* KPI global */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Smartphone} label="Scor Mobile mediu" value={summary?.avg_mobile ?? "—"} accent="warning" testid="da-kpi-mobile" />
            <KpiCard icon={Monitor}    label="Scor Desktop mediu" value={summary?.avg_desktop ?? "—"} accent="success" testid="da-kpi-desktop" />
            <KpiCard icon={Layers}     label="Unitate vizuală"     value={summary?.avg_unity ?? "—"}   accent="ai"      testid="da-kpi-unity" />
            <KpiCard icon={Compass}    label="Hick's Law"          value={summary?.avg_hicks ?? "—"}   accent="info"    testid="da-kpi-hicks" />
          </div>

          {/* Coverage + worst 3 */}
          <div className="grid lg:grid-cols-3 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><Palette className="w-4 h-4 text-lime-500" /> Acoperire audit</span>} testid="da-coverage">
              <div className="text-3xl font-black text-slate-900 dark:text-white">{summary?.audited || 0}<span className="text-slate-400 text-lg font-medium">/{summary?.total_pages || 0}</span></div>
              <div className="mt-2 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-lime-400" style={{ width: `${summary?.coverage || 0}%` }} />
              </div>
              <div className="mt-2 text-[11px] text-slate-500">{summary?.coverage || 0}% din paginile catalogate au audit recent (≤12h).</div>
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2 text-rose-600 dark:text-rose-300"><Smartphone className="w-4 h-4" /> Cele mai slabe pe mobil</span>} testid="da-worst-mobile">
              <ul className="space-y-1.5 text-sm">
                {(summary?.worst_mobile || []).map(w => (
                  <li key={`m-${w.key}`} className="flex items-center justify-between">
                    <button onClick={() => runAudit(w.key)} className="text-slate-700 dark:text-slate-200 hover:text-lime-600 dark:hover:text-lime-300 text-left" data-testid={`da-worst-mobile-${w.key}`}>
                      {w.label}
                    </button>
                    <span className="font-black text-rose-500">{w.mobile_score}</span>
                  </li>
                ))}
                {(!summary?.worst_mobile?.length) && <li className="text-slate-400 text-xs">Rulează câteva analize pentru date.</li>}
              </ul>
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2 text-amber-600 dark:text-amber-300"><Monitor className="w-4 h-4" /> Cele mai slabe pe desktop</span>} testid="da-worst-desktop">
              <ul className="space-y-1.5 text-sm">
                {(summary?.worst_desktop || []).map(w => (
                  <li key={`d-${w.key}`} className="flex items-center justify-between">
                    <button onClick={() => runAudit(w.key)} className="text-slate-700 dark:text-slate-200 hover:text-lime-600 dark:hover:text-lime-300 text-left" data-testid={`da-worst-desktop-${w.key}`}>
                      {w.label}
                    </button>
                    <span className="font-black text-amber-500">{w.desktop_score}</span>
                  </li>
                ))}
                {(!summary?.worst_desktop?.length) && <li className="text-slate-400 text-xs">Rulează câteva analize pentru date.</li>}
              </ul>
            </AdminCard>
          </div>

          {/* Pages table + detail panel */}
          <div className="grid lg:grid-cols-5 gap-4">
            <AdminCard className="lg:col-span-2" title="Pagini catalogate" testid="da-pages">
              <div className="max-h-[500px] overflow-y-auto -mx-2">
                {pages.map(p => (
                  <button
                    key={p.key}
                    onClick={() => runAudit(p.key)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl mx-2 my-1 border transition-colors ${active === p.key ? "bg-lime-50 dark:bg-lime-500/10 border-lime-300 dark:border-lime-500/40" : "border-transparent hover:bg-slate-50 dark:hover:bg-slate-800"}`}
                    data-testid={`da-page-${p.key}`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <ZoneTag zone={p.zone} />
                      <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{p.label}</span>
                      {p.fresh && <DSBadge type="LIVE">Recent</DSBadge>}
                    </div>
                    <div className="text-[11px] text-slate-500 truncate">{p.path}</div>
                    {(p.mobile_score || p.desktop_score) && (
                      <div className="flex items-center gap-3 mt-1.5 text-[11px]">
                        <span className="inline-flex items-center gap-1 text-slate-500"><Smartphone className="w-3 h-3" />{p.mobile_score ?? "—"}</span>
                        <span className="inline-flex items-center gap-1 text-slate-500"><Monitor className="w-3 h-3" />{p.desktop_score ?? "—"}</span>
                        <span className="inline-flex items-center gap-1 text-slate-500"><Layers className="w-3 h-3" />{p.unity_score ?? "—"}</span>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </AdminCard>

            <AdminCard className="lg:col-span-3"
              title={
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-lime-500" />
                  Detaliu audit
                  {active && <span className="text-slate-400 text-xs font-normal">· {pages.find(p => p.key === active)?.label}</span>}
                </span>
              }
              action={active && (
                <DSButton variant="ghost" icon={RefreshCw} onClick={() => runAudit(active, true)} data-testid="da-force-rerun">
                  Reanalizează
                </DSButton>
              )}
              testid="da-detail"
            >
              {!active && (
                <EmptyState
                  icon={Palette}
                  title="Selectează o pagină pentru audit"
                  hint="Fiecare pagină primește scoruri pentru mobile, desktop, unitate vizuală și legea lui Hick, plus 3-5 recomandări concrete de la Claude."
                />
              )}
              {active && running && <DSSkeleton kpis={4} blocks={1} />}
              {active && !running && result?.error && (
                <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-sm">
                  <AlertTriangle className="w-4 h-4 inline mr-1.5" />{result.error}
                </div>
              )}
              {active && !running && result && !result.error && (
                <div className="space-y-4" data-testid="da-detail-body">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <ScoreDial value={result.mobile_score}   label="Mobile"   icon={Smartphone} testid="da-score-mobile" />
                    <ScoreDial value={result.desktop_score}  label="Desktop"  icon={Monitor}    testid="da-score-desktop" />
                    <ScoreDial value={result.unity_score}    label="Unitate"  icon={Layers}     testid="da-score-unity" />
                    <ScoreDial value={result.hicks_law_score} label="Hick's Law" icon={Compass} testid="da-score-hicks" />
                  </div>

                  {/* Extended UX Inspector — 7 principii */}
                  <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                    <ScoreDial value={result.millers_law_score} label="Miller" icon={Layers}    testid="da-score-miller" />
                    <ScoreDial value={result.fitts_law_score}   label="Fitts"  icon={MousePointer2} testid="da-score-fitts" />
                    <ScoreDial value={result.jakobs_law_score}  label="Jakob"  icon={Users}     testid="da-score-jakob" />
                    <ScoreDial value={result.nielsen_score}     label="Nielsen" icon={Eye}      testid="da-score-nielsen" />
                    <ScoreDial value={result.wcag_score}        label="WCAG AA" icon={Accessibility} testid="da-score-wcag" />
                    <ScoreDial value={100 - (result.cognitive_load || 0)} label="Cognitiv" icon={Brain} testid="da-score-cognitive" />
                  </div>
                  {typeof result.cognitive_load === "number" && (
                    <div className="p-3 rounded-xl bg-lime-50 dark:bg-lime-500/10 border border-lime-200 dark:border-lime-500/30">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-lime-800 dark:text-lime-200 mb-1">
                        <Brain className="w-3.5 h-3.5" /> Cognitive Load Score
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-3xl font-black text-lime-700 dark:text-lime-300">{result.cognitive_load}</div>
                        <div className="text-xs text-slate-600 dark:text-slate-300 flex-1">
                          {result.cognitive_load < 30 && "Ușor — pagina e clară, decizii puține."}
                          {result.cognitive_load >= 30 && result.cognitive_load < 60 && "Moderat — echilibru între conținut și acțiuni."}
                          {result.cognitive_load >= 60 && result.cognitive_load < 80 && "Ridicat — considera simplificare / progressive disclosure."}
                          {result.cognitive_load >= 80 && "Copleșitor — recomand refactor major."}
                        </div>
                        <div className="w-24 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div className={`h-full ${result.cognitive_load < 30 ? "bg-emerald-500" : result.cognitive_load < 60 ? "bg-lime-400" : result.cognitive_load < 80 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${result.cognitive_load}%` }} />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-amber-700 dark:text-amber-300 mb-1"><Smartphone className="w-3.5 h-3.5" /> Impact pe MOBILE</div>
                      <div className="text-sm text-slate-700 dark:text-slate-200">{result.mobile_impact || "—"}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 dark:text-emerald-300 mb-1"><Monitor className="w-3.5 h-3.5" /> Impact pe DESKTOP</div>
                      <div className="text-sm text-slate-700 dark:text-slate-200">{result.desktop_impact || "—"}</div>
                    </div>
                  </div>

                  {result.findings?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Constatări</h4>
                      <ul className="space-y-1.5">
                        {result.findings.map((f, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200">
                            <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 text-slate-400 shrink-0" /> {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.recommendations?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-lime-700 dark:text-lime-300 mb-2">Recomandări acționabile</h4>
                      <ul className="space-y-1.5">
                        {result.recommendations.map((r, i) => {
                          const isObj = r && typeof r === "object";
                          const priority = isObj ? (r.priority || "") : "";
                          const text = isObj ? (r.action || r.text || JSON.stringify(r)) : String(r);
                          return (
                            <li key={i} className="flex items-start gap-2 text-sm font-medium text-slate-800 dark:text-slate-100">
                              <ArrowRight className="w-3.5 h-3.5 mt-0.5 text-lime-500 shrink-0" />
                              <span>
                                {priority && <span className="inline-block mr-2 px-1.5 py-0.5 rounded text-[10px] font-black bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300">{priority}</span>}
                                {text}
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400">
                    {result.cached ? "Rezultat din cache (12h). Apasă Reanalizează pentru refresh." : "Analiză generată acum."} · {new Date(result.generated_at).toLocaleString("ro-RO")}
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
