import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { Reorder, useDragControls } from "framer-motion";
import {
  GripVertical, Eye, EyeOff, Save, RotateCcw, LayoutDashboard, Smartphone,
  History, Boxes, Users, Shield, ExternalLink, Undo2,
} from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import XOSRegistryPanel from "./XOSRegistryPanel";
import ExperienceProfilesPanel from "./ExperienceProfilesPanel";

const API = process.env.REACT_APP_BACKEND_URL;

const CLASS_COLORS = {
  CORE: "bg-slate-200 text-slate-700", AI: "bg-violet-100 text-violet-700",
  AUTONOMY: "bg-cyan-100 text-cyan-700", BUSINESS: "bg-amber-100 text-amber-700",
  PREMIUM: "bg-yellow-100 text-yellow-800", GROWTH: "bg-lime-100 text-lime-700",
  INFRASTRUCTURE: "bg-stone-200 text-stone-600", EXPERIMENTAL: "bg-pink-100 text-pink-700",
  LEGACY: "bg-red-100 text-red-600",
};

const WidgetRow = ({ item, widget, onToggle }) => {
  const controls = useDragControls();
  return (
    <Reorder.Item value={item} dragListener={false} dragControls={controls}
      className={`flex items-center gap-3 rounded-2xl border p-4 bg-white dark:bg-slate-900 ${item.enabled ? "border-slate-200 dark:border-slate-700" : "border-dashed border-slate-300 dark:border-slate-600 opacity-60"}`}
      data-testid={`xos-widget-${item.id}`}>
      <button onPointerDown={(e) => controls.start(e)} className="cursor-grab active:cursor-grabbing p-1 text-slate-400 touch-none" data-testid={`xos-drag-${item.id}`}>
        <GripVertical className="w-5 h-5" />
      </button>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-black text-slate-900 dark:text-white">{widget?.label || item.id}</div>
        <div className="text-xs text-slate-500 truncate">{widget?.desc}</div>
      </div>
      <button onClick={onToggle}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border ${item.enabled ? "text-lime-700 bg-lime-50 border-lime-300 dark:text-lime-300 dark:bg-lime-900/20 dark:border-lime-700" : "text-slate-500 bg-slate-50 border-slate-200 dark:bg-slate-800 dark:border-slate-600"}`}
        data-testid={`xos-toggle-${item.id}`}>
        {item.enabled ? <><Eye className="w-3.5 h-3.5" /> Vizibil</> : <><EyeOff className="w-3.5 h-3.5" /> Ascuns</>}
      </button>
    </Reorder.Item>
  );
};

// Preview live: telefonul clientului, randat din starea curentă (nesalvată) a editorului
const LivePreview = ({ items, widgetMap, surfaceLabel }) => {
  const visible = items.filter((i) => i.enabled);
  return (
    <div className="mx-auto w-64 rounded-[2rem] border-4 border-slate-800 bg-slate-950 p-2 shadow-2xl sticky top-6" data-testid="xc-preview">
      <div className="rounded-[1.6rem] bg-slate-100 dark:bg-slate-900 overflow-hidden">
        <div className="bg-slate-900 text-white px-4 py-3">
          <div className="text-[9px] uppercase tracking-widest text-slate-400">Preview live</div>
          <div className="text-xs font-black truncate">{surfaceLabel}</div>
        </div>
        <div className="p-2.5 space-y-2 min-h-[320px] max-h-[420px] overflow-y-auto">
          {visible.length === 0 && <div className="text-[10px] text-slate-400 text-center pt-10">Niciun widget vizibil</div>}
          {visible.map((i, idx) => {
            const w = widgetMap[i.id];
            return (
              <div key={i.id} className="rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-2.5" data-testid={`xc-preview-widget-${i.id}`}>
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[10px] font-black text-slate-800 dark:text-slate-100 truncate">{idx + 1}. {w?.label || i.id}</span>
                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${CLASS_COLORS[w?.class] || CLASS_COLORS.CORE}`}>{w?.class || "?"}</span>
                </div>
                <div className="mt-1.5 space-y-1">
                  <div className="h-1.5 rounded bg-slate-200 dark:bg-slate-700 w-full" />
                  <div className="h-1.5 rounded bg-slate-200 dark:bg-slate-700 w-2/3" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const HistoryPanel = ({ surface, refreshKey, onRestored }) => {
  const [versions, setVersions] = useState(null);
  const load = () => axios.get(`${API}/api/admin/xos/layout/${surface}/history`, { withCredentials: true })
    .then((r) => setVersions(r.data.versions)).catch(() => setVersions([]));
  useEffect(() => { load(); }, [surface, refreshKey]);

  const rollback = async (vid) => {
    try {
      const r = await axios.post(`${API}/api/admin/xos/layout/${surface}/rollback/${vid}`, {}, { withCredentials: true });
      toast.success("Layout restaurat din istoric.");
      onRestored(r.data.items);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la restaurare.");
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4" data-testid="xc-history">
      <div className="flex items-center gap-2 text-sm font-black text-slate-800 dark:text-white mb-3"><History className="w-4 h-4 text-lime-600" /> Istoric versiuni (ultimele 20)</div>
      {!versions ? <div className="text-xs text-slate-400">Se încarcă...</div> :
        versions.length === 0 ? <div className="text-xs text-slate-400" data-testid="xc-history-empty">Nicio versiune salvată încă — istoricul apare după prima salvare.</div> : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {versions.map((v) => (
              <div key={v.version_id} className="flex items-center gap-3 text-xs rounded-xl border border-slate-100 dark:border-slate-800 p-2.5" data-testid={`xc-history-${v.version_id}`}>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-slate-700 dark:text-slate-200">{new Date(v.saved_at).toLocaleString("ro-RO")}</div>
                  <div className="text-slate-400 truncate">{v.items?.length || 0} widget-uri · {v.saved_by} · {v.reason}</div>
                </div>
                <button onClick={() => rollback(v.version_id)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 font-bold hover:bg-slate-50 dark:hover:bg-slate-800" data-testid={`xc-rollback-${v.version_id}`}>
                  <Undo2 className="w-3.5 h-3.5" /> Restaurează
                </button>
              </div>
            ))}
          </div>
        )}
    </div>
  );
};

const UIRulesSummary = () => {
  const [rules, setRules] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/admin/ui-rules`, { withCredentials: true }).then((r) => setRules(r.data.rules)).catch(() => setRules([]));
  }, []);
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5" data-testid="xc-uirules-summary">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 text-sm font-black text-slate-800 dark:text-white"><Shield className="w-4 h-4 text-lime-600" /> Reguli UI active</div>
        <Link to="/admin/ui-rules" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-lime-500 text-black hover:bg-lime-400" data-testid="xc-uirules-open">
          Editează în UI Rules Manager <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>
      {!rules ? <div className="text-xs text-slate-400">Se încarcă...</div> :
        rules.length === 0 ? <div className="text-xs text-slate-400">Nicio regulă definită. Regulile ascund/arată elemente pe baza condițiilor (rol, verificat, vechime cont).</div> : (
          <div className="space-y-2">
            {rules.map((r) => (
              <div key={r.id} className="flex items-center gap-3 text-xs rounded-xl border border-slate-100 dark:border-slate-800 p-2.5" data-testid={`xc-rule-${r.id}`}>
                <span className={`w-2 h-2 rounded-full shrink-0 ${r.active ? "bg-lime-500" : "bg-slate-300"}`} />
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-slate-700 dark:text-slate-200 truncate">{r.name}</div>
                  <div className="text-slate-400 truncate">{r.action} · {r.target_type}:{r.target_id} · {r.conditions?.length || 0} condiții</div>
                </div>
              </div>
            ))}
          </div>
        )}
    </div>
  );
};

const TABS = [
  { id: "layout", label: "Layout & Preview", icon: LayoutDashboard },
  { id: "registry", label: "Registru widget-uri", icon: Boxes },
  { id: "profiles", label: "Profiluri roluri", icon: Users },
  { id: "rules", label: "Reguli UI", icon: Shield },
];

export default function XOSBuilderPage() {
  const [tab, setTab] = useState("layout");
  const [surfaces, setSurfaces] = useState(null);
  const [surface, setSurface] = useState("client_home");
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  useEffect(() => {
    axios.get(`${API}/api/admin/xos/surfaces`, { withCredentials: true })
      .then((r) => {
        setSurfaces(r.data.surfaces);
        const s = r.data.surfaces.find((x) => x.surface === surface);
        if (s) setItems(s.items);
      })
      .catch(() => toast.error("Nu am putut încărca layout-urile."));
  }, []);

  const switchSurface = (key) => {
    setSurface(key);
    const s = surfaces?.find((x) => x.surface === key);
    if (s) setItems(s.items);
  };

  const meta = surfaces?.find((x) => x.surface === surface);
  const widgetMap = Object.fromEntries((meta?.widgets || []).map((w) => [w.id, w]));

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/api/admin/xos/layout/${surface}`, { items }, { withCredentials: true });
      toast.success("Layout publicat — utilizatorii văd instant noua ordine.");
      setHistoryKey((k) => k + 1);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la salvare.");
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    try {
      const r = await axios.post(`${API}/api/admin/xos/layout/${surface}/reset`, {}, { withCredentials: true });
      setItems(r.data.items);
      toast.success("Layout resetat la implicit.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la resetare.");
    }
  };

  return (
    <AdminLayoutMetronic title="Experience Configuration Center" subtitle="Centrul vizual XOS — layouts, registru, profiluri și reguli UI, fără cod">
      <div className="max-w-5xl mx-auto space-y-6 p-4 sm:p-6" data-testid="xos-builder-page">
        {/* Tab bar */}
        <div className="flex flex-wrap gap-2" data-testid="xc-tabs">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${tab === t.id ? "bg-lime-500 text-black border-lime-500" : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-lime-400"}`}
              data-testid={`xc-tab-${t.id}`}>
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        {tab === "layout" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                <Smartphone className="w-4 h-4 text-lime-600" />
                <select value={surface} onChange={(e) => switchSurface(e.target.value)}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-1.5 text-sm font-bold"
                  data-testid="xos-surface-select">
                  {(surfaces || []).map((s) => <option key={s.surface} value={s.surface}>{s.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={reset} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800" data-testid="xos-reset">
                  <RotateCcw className="w-4 h-4" /> Reset
                </button>
                <button onClick={save} disabled={saving} className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-lime-500 text-black hover:bg-lime-400 disabled:opacity-50" data-testid="xos-save">
                  <Save className="w-4 h-4" /> {saving ? "Se salvează..." : "Publică layout"}
                </button>
              </div>
            </div>

            <div className="grid lg:grid-cols-[1fr_18rem] gap-6 items-start">
              {!surfaces ? (
                <div className="text-slate-400 p-8">Se încarcă...</div>
              ) : (
                <Reorder.Group axis="y" values={items} onReorder={setItems} className="space-y-3">
                  {items.map((item) => (
                    <WidgetRow key={item.id} item={item} widget={widgetMap[item.id]}
                      onToggle={() => setItems(items.map((x) => (x.id === item.id ? { ...x, enabled: !x.enabled } : x)))} />
                  ))}
                </Reorder.Group>
              )}
              <LivePreview items={items} widgetMap={widgetMap} surfaceLabel={meta?.label || surface} />
            </div>

            <div className="text-xs text-slate-400 flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <LayoutDashboard className="w-4 h-4" />
              Trage de mâner pentru reordonare · comută Vizibil/Ascuns · preview-ul din dreapta se actualizează live, publici doar când ești mulțumit.
            </div>

            <HistoryPanel surface={surface} refreshKey={historyKey} onRestored={setItems} />
          </div>
        )}

        {tab === "registry" && <XOSRegistryPanel onChanged={() => window.location.reload()} />}
        {tab === "profiles" && <ExperienceProfilesPanel />}
        {tab === "rules" && <UIRulesSummary />}
      </div>
    </AdminLayoutMetronic>
  );
}
