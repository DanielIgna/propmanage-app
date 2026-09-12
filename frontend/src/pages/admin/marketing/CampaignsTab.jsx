// Marketing Campaigns tab — generator manual + listă + approve/reject + auto-trigger
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Megaphone, Plus, Loader2, Sparkles, CheckCircle2, XCircle, X,
  Image as ImageIcon, Copy, Zap, AlertTriangle, RefreshCw, Eye,
  Target, DollarSign, ChevronRight, Wand2, Bot, Activity, GitBranch,
} from "lucide-react";
import { LogPerformanceModal } from "./PerformanceTab";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const OBJECTIVES = [
  { id: "awareness", label: "Awareness (vizibilitate)" },
  { id: "leads", label: "Leads (cerere oferte)" },
  { id: "conversions", label: "Conversii (achiziții)" },
  { id: "retention", label: "Retenție (clienți existenți)" },
  { id: "engagement", label: "Engagement (interacțiune)" },
];

const QUICK_CATEGORIES = [
  "HVAC", "Instalații electrice", "Instalații termice", "Termografie",
  "Sanitare", "Smart home", "Sisteme fotovoltaice", "Pompe căldură",
  "Vopsele și lavabile", "Acoperișuri", "Tâmplărie", "Securitate",
];

const QUICK_COUNTIES = [
  "București", "Cluj", "Timiș", "Iași", "Brașov", "Constanța",
  "Sibiu", "Dolj", "Mureș", "Prahova",
];

const STATUS_STYLES = {
  draft: { color: "text-slate-600 dark:text-slate-300", bg: "bg-slate-100 dark:bg-slate-700", label: "Draft" },
  auto_draft: { color: "text-violet-700 dark:text-violet-300", bg: "bg-violet-100 dark:bg-violet-500/20", label: "Auto-Trigger" },
  approved: { color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-100 dark:bg-emerald-500/20", label: "Aprobată" },
  rejected: { color: "text-rose-700 dark:text-rose-300", bg: "bg-rose-100 dark:bg-rose-500/20", label: "Respinsă" },
  completed: { color: "text-blue-700 dark:text-blue-300", bg: "bg-blue-100 dark:bg-blue-500/20", label: "Finalizată" },
};

// ----- Generate modal -----
const GenerateModal = ({ onClose, onCreated }) => {
  const [objective, setObjective] = useState("leads");
  const [service, setService] = useState("");
  const [county, setCounty] = useState("");
  const [budget, setBudget] = useState(500);
  const [skipImages, setSkipImages] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!service.trim() || !county.trim()) {
      setErr("Completează serviciul și județul.");
      return;
    }
    setBusy(true); setErr("");
    try {
      const r = await ax.post("/api/admin/marketing/campaigns/generate", {
        objective, service_category: service.trim(), county: county.trim(),
        budget_ron: Number(budget), skip_images: skipImages,
      });
      onCreated(r.data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="generate-campaign-modal">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white sticky top-0">
          <h3 className="font-bold flex items-center gap-2"><Wand2 className="w-4 h-4" /> Generator Campanie AI</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1.5 block">Obiectiv</label>
            <select value={objective} onChange={e => setObjective(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm" data-testid="gen-objective">
              {OBJECTIVES.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1.5 block">Serviciu / Categorie</label>
            <input value={service} onChange={e => setService(e.target.value)} placeholder="ex: Sisteme fotovoltaice"
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm" data-testid="gen-service" />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {QUICK_CATEGORIES.map(c => (
                <button key={c} onClick={() => setService(c)} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-violet-100 dark:hover:bg-violet-500/20">{c}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1.5 block">Județ / Oraș</label>
            <input value={county} onChange={e => setCounty(e.target.value)} placeholder="ex: Cluj"
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm" data-testid="gen-county" />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {QUICK_COUNTIES.map(c => (
                <button key={c} onClick={() => setCounty(c)} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-violet-100 dark:hover:bg-violet-500/20">{c}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1.5 block">Buget total (RON)</label>
            <input type="number" min={50} max={100000} value={budget} onChange={e => setBudget(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm" data-testid="gen-budget" />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input type="checkbox" checked={skipImages} onChange={e => setSkipImages(e.target.checked)} data-testid="gen-skip-images" />
            <span>Sari peste generare imagini (mai rapid, doar text)</span>
          </label>
          {err && <div className="text-rose-500 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{err}</div>}
          <button onClick={submit} disabled={busy}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="gen-submit">
            {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Claude + Nano Banana lucrează… ({skipImages ? "10s" : "30s"})</>
              : <><Sparkles className="w-4 h-4" /> Generează campanie</>}
          </button>
        </div>
      </div>
    </div>
  );
};

// ----- Detail modal -----
const DetailModal = ({ campaignId, onClose, onUpdate }) => {
  const [c, setC] = useState(null);
  const [busy, setBusy] = useState(true);
  const [acting, setActing] = useState(false);
  const [err, setErr] = useState("");
  const [showLog, setShowLog] = useState(false);
  const [perfLogs, setPerfLogs] = useState([]);

  const load = async () => {
    setBusy(true);
    try {
      const r = await ax.get(`/api/admin/marketing/campaigns/${campaignId}`);
      setC(r.data);
      // Fetch perf logs if approved/completed
      if (["approved", "completed"].includes(r.data.status)) {
        const pR = await ax.get(`/api/admin/marketing/campaigns/${campaignId}/performance`);
        setPerfLogs(pR.data.items || []);
      } else {
        setPerfLogs([]);
      }
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };
  useEffect(() => { load(); }, [campaignId]);

  const act = async (action) => {
    setActing(true);
    try {
      await ax.post(`/api/admin/marketing/campaigns/${campaignId}/${action}`);
      await load();
      onUpdate?.();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setActing(false); }
  };

  const regenImg = async (idx) => {
    setActing(true);
    try {
      await ax.post(`/api/admin/marketing/campaigns/${campaignId}/regenerate-image`, { image_index: idx });
      await load();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setActing(false); }
  };

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="campaign-detail-modal">
      <div className="w-full max-w-4xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[92vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white sticky top-0 z-10">
          <h3 className="font-bold flex items-center gap-2"><Megaphone className="w-4 h-4" /> Detalii Campanie</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          {busy && <div className="text-center py-10"><Loader2 className="w-7 h-7 animate-spin mx-auto text-violet-500" /></div>}
          {err && <div className="text-rose-500 text-sm mb-3"><AlertTriangle className="w-4 h-4 inline mr-1" />{err}</div>}
          {c && (
            <div className="space-y-5">
              {/* Header info */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${STATUS_STYLES[c.status]?.bg} ${STATUS_STYLES[c.status]?.color}`}>{STATUS_STYLES[c.status]?.label}</span>
                {c.source === "auto_trigger" && (
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-fuchsia-100 dark:bg-fuchsia-500/20 text-fuchsia-700 dark:text-fuchsia-300 flex items-center gap-1"><Zap className="w-3 h-3" /> Auto-Trigger</span>
                )}
                <span className="text-sm text-slate-600 dark:text-slate-300"><strong>{c.service_category}</strong> · {c.county}</span>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1"><DollarSign className="w-3 h-3" /> {c.budget_ron} RON</span>
              </div>

              {c.trigger_reason && (
                <div className="p-3 rounded-lg bg-fuchsia-50 dark:bg-fuchsia-500/10 border border-fuchsia-200 dark:border-fuchsia-500/30 text-sm">
                  <strong className="text-fuchsia-700 dark:text-fuchsia-300">Motiv trigger:</strong> {c.trigger_reason}
                </div>
              )}

              {/* Images */}
              {c.images && c.images.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-2 flex items-center gap-1"><ImageIcon className="w-3 h-3" /> Imagini AI (Nano Banana)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {c.images.map((img) => (
                      <div key={img.idx} className="relative group rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700" data-testid={`campaign-image-${img.idx}`}>
                        <img src={img.data_uri} alt={`creative ${img.idx + 1}`} className="w-full h-56 object-cover" />
                        <button onClick={() => regenImg(img.idx)} disabled={acting}
                          className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/70 text-white hover:bg-black opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                          title="Regenerează" data-testid={`regen-img-${img.idx}`}>
                          {acting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Avatar */}
              {c.avatar && (
                <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-500/30 bg-blue-50/40 dark:bg-blue-500/5">
                  <h4 className="text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400 font-bold mb-2">Avatar client</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-slate-500">Vârstă:</span> <strong>{c.avatar.age_range}</strong></div>
                    <div><span className="text-slate-500">Ocupație:</span> <strong>{c.avatar.occupation}</strong></div>
                  </div>
                  {c.avatar.pain_points?.length > 0 && (
                    <div className="mt-2 text-sm"><span className="text-slate-500">Pain points:</span> <strong>{c.avatar.pain_points.join(" · ")}</strong></div>
                  )}
                  {c.avatar.motivations?.length > 0 && (
                    <div className="mt-1 text-sm"><span className="text-slate-500">Motivații:</span> <strong>{c.avatar.motivations.join(" · ")}</strong></div>
                  )}
                </div>
              )}

              {/* Audience */}
              {c.audience && (
                <div className="p-4 rounded-xl border border-violet-200 dark:border-violet-500/30 bg-violet-50/40 dark:bg-violet-500/5">
                  <h4 className="text-xs uppercase tracking-wider text-violet-600 dark:text-violet-400 font-bold mb-2">Audiență țintă</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-200 mb-2">{c.audience.targeting}</p>
                  {c.audience.interests?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-1">
                      {c.audience.interests.map((i, k) => (
                        <span key={k} className="text-[11px] px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300">{i}</span>
                      ))}
                    </div>
                  )}
                  {c.audience.exclusions?.length > 0 && (
                    <div className="text-xs text-slate-500 mt-1">Exclusiuni: {c.audience.exclusions.join(", ")}</div>
                  )}
                </div>
              )}

              {/* Ad texts */}
              {c.ad_texts?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-2">Variante text reclamă (3)</h4>
                  <div className="space-y-2">
                    {c.ad_texts.map((t, i) => (
                      <div key={i} className="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50" data-testid={`ad-text-${i}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] uppercase font-bold text-slate-400">Varianta {i + 1}</span>
                          <button onClick={() => navigator.clipboard.writeText(`${t.headline}\n${t.primary_text}\n${t.description}`)}
                            className="text-xs text-slate-400 hover:text-violet-500"><Copy className="w-3 h-3" /></button>
                        </div>
                        <div className="text-sm font-bold text-slate-900 dark:text-white">{t.headline}</div>
                        <div className="text-sm text-slate-700 dark:text-slate-200 mt-1">{t.primary_text}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t.description}</div>
                      </div>
                    ))}
                  </div>
                  {c.cta && <div className="mt-2 text-sm"><span className="text-slate-500">CTA:</span> <strong className="text-violet-600 dark:text-violet-400">{c.cta}</strong></div>}
                </div>
              )}

              {/* KPIs */}
              {c.kpis && Object.keys(c.kpis).length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-2">KPI estimați</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                    {Object.entries(c.kpis).map(([k, v]) => (
                      <div key={k} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800">
                        <div className="text-[10px] uppercase text-slate-400">{k.replace(/_/g, " ")}</div>
                        <div className="font-bold text-slate-900 dark:text-white">{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {c.rationale && (
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200">
                  <strong className="text-slate-900 dark:text-white">Rațional AI:</strong> {c.rationale}
                </div>
              )}

              {/* Performance loop section — for approved/completed */}
              {["approved", "completed"].includes(c.status) && (
                <div className="p-4 rounded-xl border border-violet-200 dark:border-violet-500/30 bg-gradient-to-br from-violet-50 to-fuchsia-50 dark:from-violet-500/10 dark:to-fuchsia-500/10">
                  <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                    <h4 className="text-xs uppercase tracking-wider text-violet-700 dark:text-violet-300 font-bold flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5" /> Performance Loop · {perfLogs.length} log{perfLogs.length !== 1 ? "uri" : ""}
                    </h4>
                    <button onClick={() => setShowLog(true)}
                      className="text-xs px-2.5 py-1 rounded-lg bg-violet-500 hover:bg-violet-600 text-white font-medium flex items-center gap-1"
                      data-testid="log-perf-btn">
                      <Plus className="w-3 h-3" /> Loghează rezultate
                    </button>
                  </div>
                  {perfLogs.length === 0 ? (
                    <p className="text-xs text-slate-600 dark:text-slate-300">Nicio metrică reală logată. Adaugă rezultatele din Meta/Google Ads pentru a permite AI-ului să învețe.</p>
                  ) : (
                    <div className="space-y-2">
                      {perfLogs.slice(0, 3).map(log => (
                        <div key={log.id} className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-violet-200 dark:border-violet-500/30 text-xs" data-testid={`perf-log-${log.id}`}>
                          <div className="grid grid-cols-3 gap-2 mb-1">
                            <div><span className="text-slate-400">Impresii:</span> <strong className="text-slate-900 dark:text-white">{log.impressions?.toLocaleString("ro-RO")}</strong>
                              {log.deltas?.impressions_delta_pct != null && <span className={`ml-1 ${log.deltas.impressions_delta_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>({log.deltas.impressions_delta_pct >= 0 ? "+" : ""}{log.deltas.impressions_delta_pct}%)</span>}
                            </div>
                            <div><span className="text-slate-400">Clicks:</span> <strong className="text-slate-900 dark:text-white">{log.clicks}</strong>
                              {log.deltas?.clicks_delta_pct != null && <span className={`ml-1 ${log.deltas.clicks_delta_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>({log.deltas.clicks_delta_pct >= 0 ? "+" : ""}{log.deltas.clicks_delta_pct}%)</span>}
                            </div>
                            <div><span className="text-slate-400">Leads:</span> <strong className="text-slate-900 dark:text-white">{log.leads}</strong>
                              {log.deltas?.leads_delta_pct != null && <span className={`ml-1 ${log.deltas.leads_delta_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>({log.deltas.leads_delta_pct >= 0 ? "+" : ""}{log.deltas.leads_delta_pct}%)</span>}
                            </div>
                          </div>
                          <div className="flex items-center justify-between text-slate-500">
                            <span>Cheltuit: <strong className="text-slate-900 dark:text-white">{log.spent_ron} RON</strong> · CPL: <strong>{log.deltas?.cpl_actual_ron || "—"} RON</strong></span>
                            <span className="text-[10px]">{new Date(log.logged_at).toLocaleDateString("ro-RO")}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              {["draft", "auto_draft"].includes(c.status) && (
                <div className="flex gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <button onClick={() => act("approve")} disabled={acting}
                    className="flex-1 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-1.5" data-testid="approve-btn">
                    <CheckCircle2 className="w-4 h-4" /> Aprobă
                  </button>
                  <button onClick={() => act("reject")} disabled={acting}
                    className="flex-1 py-2.5 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-1.5" data-testid="reject-btn">
                    <XCircle className="w-4 h-4" /> Respinge
                  </button>
                </div>
              )}
              {c.status === "approved" && (
                <div className="text-xs text-emerald-600 dark:text-emerald-400 text-center">✓ Aprobată de {c.approved_by} la {new Date(c.approved_at).toLocaleString("ro-RO")}</div>
              )}
              {c.status === "rejected" && (
                <div className="text-xs text-rose-600 dark:text-rose-400 text-center">✗ Respinsă la {new Date(c.rejected_at).toLocaleString("ro-RO")}</div>
              )}
              {c.calibration_applied && (
                <div className="text-xs text-violet-600 dark:text-violet-400 text-center flex items-center justify-center gap-1">
                  <GitBranch className="w-3 h-3" /> KPI-urile au fost calibrate pe baza învățămintelor istorice
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {showLog && c && (
        <LogPerformanceModal campaignId={campaignId} predictedKpis={c.kpis}
          onClose={() => setShowLog(false)}
          onLogged={() => { setShowLog(false); load(); onUpdate?.(); }} />
      )}
    </div>
  );
};

// ----- Main CampaignsTab -----
const CampaignsTab = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGen, setShowGen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    try {
      const r = await ax.get("/api/admin/marketing/campaigns", { params: { limit: 50 } });
      setItems(r.data.items || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const runAutoTrigger = async () => {
    setScanning(true); setScanResult(null);
    try {
      const r = await ax.post("/api/admin/marketing/auto-triggers/scan");
      setScanResult(r.data);
      await load();
    } catch (e) {
      setScanResult({ error: e.response?.data?.detail || e.message });
    } finally { setScanning(false); }
  };

  const filtered = filter === "all" ? items : items.filter(i => i.status === filter);

  return (
    <div className="space-y-5" data-testid="mkt-tab-campaigns">
      {/* Action bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          {["all", "draft", "auto_draft", "approved", "rejected"].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all ${
                filter === f ? "bg-violet-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
              }`} data-testid={`filter-${f}`}>
              {f === "all" ? "Toate" : (STATUS_STYLES[f]?.label || f)} ({f === "all" ? items.length : items.filter(i => i.status === f).length})
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={runAutoTrigger} disabled={scanning}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-fuchsia-500/15 to-violet-500/15 border border-fuchsia-200 dark:border-fuchsia-500/30 text-fuchsia-700 dark:text-fuchsia-300 text-sm font-medium hover:bg-fuchsia-500/25 disabled:opacity-50 flex items-center gap-1.5"
            data-testid="auto-trigger-btn">
            {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            {scanning ? "Scanare…" : "Auto-Trigger Scan"}
          </button>
          <button onClick={() => setShowGen(true)}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white text-sm font-medium flex items-center gap-1.5"
            data-testid="new-campaign-btn">
            <Plus className="w-4 h-4" /> Campanie nouă
          </button>
        </div>
      </div>

      {/* Scan result banner */}
      {scanResult && (
        <div className={`p-3 rounded-lg text-sm flex items-center justify-between ${
          scanResult.error ? "bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300"
          : "bg-fuchsia-50 dark:bg-fuchsia-500/10 border border-fuchsia-200 dark:border-fuchsia-500/30 text-fuchsia-700 dark:text-fuchsia-300"
        }`} data-testid="scan-result">
          {scanResult.error ? (
            <span><AlertTriangle className="w-4 h-4 inline mr-1" />{scanResult.error}</span>
          ) : (
            <span>
              <Zap className="w-4 h-4 inline mr-1" />
              Detectate <strong>{scanResult.triggers_detected}</strong> oportunități · <strong>{scanResult.drafts_created}</strong> draft-uri create · <strong>{scanResult.skipped_recent_duplicate}</strong> sărite (deja existente).
            </span>
          )}
          <button onClick={() => setScanResult(null)}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="text-center py-10"><Loader2 className="w-6 h-6 animate-spin mx-auto text-slate-400" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <Megaphone className="w-12 h-12 mx-auto opacity-20 mb-3" />
          <p className="text-sm">Nicio campanie {filter !== "all" ? `cu status "${STATUS_STYLES[filter]?.label}"` : "încă"}.</p>
          <p className="text-xs mt-1">Apasă „Auto-Trigger Scan" pentru detectare automată sau creează manual.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(c => {
            const s = STATUS_STYLES[c.status] || STATUS_STYLES.draft;
            return (
              <div key={c.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-violet-400 dark:hover:border-violet-500/50 transition-colors cursor-pointer"
                onClick={() => setSelected(c.id)} data-testid={`campaign-${c.id}`}>
                <div className="flex items-center justify-between mb-2 flex-wrap gap-1">
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${s.bg} ${s.color}`}>{s.label}</span>
                  {c.source === "auto_trigger" && <Zap className="w-3.5 h-3.5 text-fuchsia-500" />}
                </div>
                <div className="font-bold text-slate-900 dark:text-white text-sm">{c.service_category}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{c.county} · {c.objective}</div>
                <div className="flex items-center justify-between mt-3 text-xs">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1"><DollarSign className="w-3 h-3" /> {c.budget_ron} RON</span>
                  <span className="text-slate-400 flex items-center gap-2">
                    {c.image_count > 0 && <span className="flex items-center gap-0.5"><ImageIcon className="w-3 h-3" /> {c.image_count}</span>}
                    <span className="flex items-center gap-0.5">{c.ad_texts?.length || 0} texte</span>
                    <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
                {c.trigger_reason && (
                  <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-fuchsia-600 dark:text-fuchsia-400 line-clamp-2">
                    {c.trigger_reason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showGen && <GenerateModal onClose={() => setShowGen(false)} onCreated={(c) => { setShowGen(false); load(); setSelected(c.id); }} />}
      {selected && <DetailModal campaignId={selected} onClose={() => setSelected(null)} onUpdate={load} />}
    </div>
  );
};

export default CampaignsTab;
export { CampaignsTab };
