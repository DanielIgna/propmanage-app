import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  ArrowUp, ArrowDown, Trash2, Plus, Save, RotateCcw, Eye, EyeOff, GripVertical, Menu as MenuIco,
  Settings2, Globe, Store, FileCog,
} from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";

const API = process.env.REACT_APP_BACKEND_URL;

const VIS_OPTIONS = [
  { value: "all", label: "Toți" },
  { value: "guests", label: "Doar vizitatori" },
  { value: "auth", label: "Doar autentificați" },
];

const DEST_OPTIONS = [
  { value: "internal", label: "Pagină internă" },
  { value: "marketplace", label: "Marketplace" },
  { value: "external", label: "URL extern (parteneri)" },
  { value: "none", label: "Fără destinație" },
];

const newProvider = () => ({ name: "", logo: "", description: "", url: "", priority: 0, active: true });

const ProviderRow = ({ p, onChange, onDelete, idx, itemId }) => (
  <div className="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-black/20 border border-white/10" data-testid={`mm-provider-${itemId}-${idx}`}>
    <input value={p.name} onChange={(e) => onChange({ ...p, name: e.target.value })} placeholder="Nume partener"
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs w-36" data-testid={`mm-prov-name-${itemId}-${idx}`} />
    <input value={p.url} onChange={(e) => onChange({ ...p, url: e.target.value })} placeholder="https://..."
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs flex-1 min-w-[120px]" data-testid={`mm-prov-url-${itemId}-${idx}`} />
    <input value={p.logo} onChange={(e) => onChange({ ...p, logo: e.target.value })} placeholder="Logo URL"
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs w-28" />
    <input value={p.description} onChange={(e) => onChange({ ...p, description: e.target.value })} placeholder="Descriere scurtă"
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs flex-1 min-w-[120px]" />
    <input type="number" value={p.priority} onChange={(e) => onChange({ ...p, priority: Number(e.target.value) || 0 })} title="Prioritate (mai mare = primul)"
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-xs w-16" />
    <button onClick={() => onChange({ ...p, active: !p.active })}
      className={`p-1 rounded-lg border ${p.active ? "text-[#d4ff3a] border-[#d4ff3a]/30" : "text-stone-500 border-white/10"}`}
      title={p.active ? "Activ" : "Inactiv"} data-testid={`mm-prov-toggle-${itemId}-${idx}`}>
      {p.active ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
    </button>
    <button onClick={onDelete} className="p-1 rounded-lg hover:bg-red-500/20 text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
  </div>
);

const ServiceDetailsPanel = ({ item, onChange }) => (
  <div className="mt-1 p-3 rounded-xl bg-black/20 border border-white/10 space-y-2" data-testid={`mm-details-${item.id}`}>
    <div className="flex flex-wrap gap-2">
      <input value={item.description || ""} onChange={(e) => onChange({ ...item, description: e.target.value })}
        placeholder="Descriere serviciu" className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-xs flex-1 min-w-[200px]"
        data-testid={`mm-desc-${item.id}`} />
      <input value={item.category || ""} onChange={(e) => onChange({ ...item, category: e.target.value })}
        placeholder="Categorie" className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-xs w-32" />
      <input value={item.image || ""} onChange={(e) => onChange({ ...item, image: e.target.value })}
        placeholder="Imagine URL (opțional)" className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-xs w-44" />
      <select value={item.dest_type || "internal"} onChange={(e) => onChange({ ...item, dest_type: e.target.value })}
        className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-xs" data-testid={`mm-dest-${item.id}`}>
        {DEST_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
    <div className="flex flex-wrap gap-2 text-xs">
      <button onClick={() => onChange({ ...item, visible_site: item.visible_site === false })}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-semibold ${item.visible_site !== false ? "text-[#d4ff3a] border-[#d4ff3a]/40 bg-[#d4ff3a]/10" : "text-stone-500 border-white/10"}`}
        data-testid={`mm-vissite-${item.id}`}>
        <Globe className="w-3.5 h-3.5" /> Vizibil în website: {item.visible_site !== false ? "DA" : "NU"}
      </button>
      <button onClick={() => onChange({ ...item, visible_marketplace: !item.visible_marketplace })}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-semibold ${item.visible_marketplace ? "text-[#d4ff3a] border-[#d4ff3a]/40 bg-[#d4ff3a]/10" : "text-stone-500 border-white/10"}`}
        data-testid={`mm-vismkt-${item.id}`}>
        <Store className="w-3.5 h-3.5" /> Vizibil în Marketplace: {item.visible_marketplace ? "DA" : "NU"}
      </button>
    </div>
    {item.dest_type === "external" && (
      <div className="space-y-2 pt-1">
        <div className="text-[10px] font-black uppercase tracking-wider text-stone-500">
          Parteneri externi (pagina publică /servicii/{item.id})
        </div>
        {(item.providers || []).map((p, pi) => (
          <ProviderRow key={pi} p={p} idx={pi} itemId={item.id}
            onChange={(v) => onChange({ ...item, providers: item.providers.map((x, xi) => (xi === pi ? v : x)) })}
            onDelete={() => onChange({ ...item, providers: item.providers.filter((_, xi) => xi !== pi) })} />
        ))}
        <button onClick={() => onChange({ ...item, providers: [...(item.providers || []), newProvider()] })}
          className="inline-flex items-center gap-1.5 text-xs text-stone-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/5"
          data-testid={`mm-add-provider-${item.id}`}>
          <Plus className="w-3.5 h-3.5" /> Adaugă partener
        </button>
      </div>
    )}
  </div>
);

const ICON_SUGGESTIONS = "Home, Layers, BadgeCheck, Box, Palette, Trees, Compass, Hammer, Paintbrush, Armchair, Wrench, Brush, Users, MessageCircle, KeyRound, PlayCircle, Sparkles, CircleDollarSign, HelpCircle, Building2, Info, BookOpen, Mail, UserCircle, LogIn, LogOut, UserPlus, LayoutDashboard, FolderKanban, MessageSquare, Bell, Settings";

const newItem = () => ({
  id: `item_${Date.now().toString(36)}`,
  label: "Element nou",
  href: "/",
  icon: "Sparkles",
  active: true,
  visibility: "all",
  children: [],
});

const ItemRow = ({ item, onChange, onMove, onDelete, isChild, pageKeys = [] }) => {
  const [showDetails, setShowDetails] = useState(false);
  return (
  <div className={`py-2 px-3 rounded-xl ${isChild ? "bg-white/[0.03]" : "bg-white/[0.06]"} border border-white/10`}>
  <div className="flex flex-wrap items-center gap-2">
    <GripVertical className="w-4 h-4 text-stone-600 shrink-0" />
    <input
      value={item.label}
      onChange={(e) => onChange({ ...item, label: e.target.value })}
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm w-44"
      placeholder="Etichetă"
      data-testid={`mm-label-${item.id}`}
    />
    <input
      value={item.href}
      onChange={(e) => onChange({ ...item, href: e.target.value })}
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm flex-1 min-w-[140px]"
      placeholder="Link (/pagina)"
      data-testid={`mm-href-${item.id}`}
    />
    <input
      value={item.icon}
      onChange={(e) => onChange({ ...item, icon: e.target.value })}
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm w-32"
      placeholder="Icon"
      title={`Iconuri disponibile: ${ICON_SUGGESTIONS}`}
      data-testid={`mm-icon-${item.id}`}
    />
    <select
      value={item.visibility}
      onChange={(e) => onChange({ ...item, visibility: e.target.value })}
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm"
      data-testid={`mm-vis-${item.id}`}
    >
      {VIS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
    <select
      value={item.page_key || ""}
      onChange={(e) => onChange({ ...item, page_key: e.target.value })}
      className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-stone-400"
      title="Leagă acest item la o pagină din Page Registry (opțional)"
      data-testid={`mm-pagekey-${item.id}`}
    >
      <option value="">— fără page config —</option>
      {pageKeys.map((pk) => <option key={pk} value={pk}>{pk}</option>)}
    </select>
    {item.page_key && (
      <a
        href={`/admin/page-registry?edit=${item.page_key}`}
        target="_blank"
        rel="noreferrer"
        className="p-1.5 rounded-lg border text-lime-400 border-lime-400/30 bg-lime-400/10 hover:bg-lime-400/20"
        title="Edit Page Config (deschide Page Registry)"
        data-testid={`mm-editpage-${item.id}`}
      >
        <FileCog className="w-4 h-4" />
      </a>
    )}
    <button
      onClick={() => onChange({ ...item, active: !item.active })}
      className={`p-1.5 rounded-lg border ${item.active ? "text-[#d4ff3a] border-[#d4ff3a]/30 bg-[#d4ff3a]/10" : "text-stone-500 border-white/10"}`}
      title={item.active ? "Activ — click pentru dezactivare" : "Inactiv — click pentru activare"}
      data-testid={`mm-toggle-${item.id}`}
    >
      {item.active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
    </button>
    <div className="flex items-center gap-1">
      <button onClick={() => onMove(-1)} className="p-1.5 rounded-lg hover:bg-white/10 text-stone-400" data-testid={`mm-up-${item.id}`}><ArrowUp className="w-4 h-4" /></button>
      <button onClick={() => onMove(1)} className="p-1.5 rounded-lg hover:bg-white/10 text-stone-400" data-testid={`mm-down-${item.id}`}><ArrowDown className="w-4 h-4" /></button>
      <button onClick={onDelete} className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400" data-testid={`mm-del-${item.id}`}><Trash2 className="w-4 h-4" /></button>
      {isChild && (
        <button onClick={() => setShowDetails(!showDetails)}
          className={`p-1.5 rounded-lg border ${showDetails ? "text-[#d4ff3a] border-[#d4ff3a]/30 bg-[#d4ff3a]/10" : "text-stone-400 border-white/10 hover:bg-white/10"}`}
          title="Detalii serviciu (descriere, destinație, parteneri, vizibilitate)"
          data-testid={`mm-details-btn-${item.id}`}>
          <Settings2 className="w-4 h-4" />
        </button>
      )}
    </div>
  </div>
  {isChild && showDetails && <ServiceDetailsPanel item={item} onChange={onChange} />}
  </div>
  );
};

export default function MenuManagerPage() {
  const [items, setItems] = useState(null);
  const [saving, setSaving] = useState(false);
  const [autoReorder, setAutoReorder] = useState(true);
  const [running, setRunning] = useState(false);
  const [pageKeys, setPageKeys] = useState([]);

  const load = () =>
    axios.get(`${API}/api/admin/site-menu`, { withCredentials: true })
      .then((r) => { setItems(r.data.items || []); setAutoReorder(r.data.auto_reorder !== false); })
      .catch(() => toast.error("Nu am putut încărca meniul."));

  const loadPageKeys = () =>
    axios.get(`${API}/api/admin/pages`, { withCredentials: true })
      .then((r) => setPageKeys((r.data.items || []).map(p => p.key)))
      .catch(() => setPageKeys([]));

  const toggleAutoReorder = async () => {
    const next = !autoReorder;
    setAutoReorder(next);
    try {
      await axios.post(`${API}/api/admin/site-menu/auto-reorder`, { enabled: next }, { withCredentials: true });
      toast.success(next ? "Autonomy activ: serviciile populare urcă automat primele (zilnic 04:30)." : "Auto-ordonare dezactivată.");
    } catch { setAutoReorder(!next); toast.error("Eroare la salvare."); }
  };

  const runReorderNow = async () => {
    setRunning(true);
    try {
      const r = await axios.post(`${API}/api/admin/site-menu/auto-reorder/run`, {}, { withCredentials: true });
      toast.success(r.data.status === "applied" ? "Meniu reordonat după popularitate!" : "Ordinea e deja optimă — nicio schimbare.");
      load();
    } catch { toast.error("Eroare la rulare."); } finally { setRunning(false); }
  };

  useEffect(() => { load(); loadPageKeys(); }, []);

  const move = (arr, idx, dir) => {
    const j = idx + dir;
    if (j < 0 || j >= arr.length) return arr;
    const copy = [...arr];
    [copy[idx], copy[j]] = [copy[j], copy[idx]];
    return copy;
  };

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/api/admin/site-menu`, { items }, { withCredentials: true });
      toast.success("Meniu salvat — vizibil instant pe Desktop și Mobile.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la salvare.");
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    if (!window.confirm("Resetezi meniul la structura implicită?")) return;
    const r = await axios.post(`${API}/api/admin/site-menu/reset`, {}, { withCredentials: true });
    setItems(r.data.items);
    toast.success("Meniu resetat la implicit.");
  };

  if (!items) return <AdminLayoutMetronic title="Menu Manager" subtitle="Navigare unificată Desktop + Mobile"><div className="p-8 text-stone-400">Se încarcă meniul...</div></AdminLayoutMetronic>;

  return (
    <AdminLayoutMetronic title="Menu Manager" subtitle="Navigare unificată Desktop + Mobile — administrată din CMS">
    <div className="p-4 sm:p-8 max-w-6xl mx-auto space-y-6" data-testid="menu-manager-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2"><MenuIco className="w-6 h-6 text-[#d4ff3a]" /> Menu Manager</h1>
          <p className="text-sm text-stone-400 mt-1">
            Un singur sistem de navigare, administrat centralizat — se adaptează automat Desktop (bară orizontală) și Mobile (drawer hamburger).
            Un serviciu nou adăugat aici apare instant pe ambele, fără cod.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={reset} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10" data-testid="menu-manager-reset">
            <RotateCcw className="w-4 h-4" /> Reset implicit
          </button>
          <button onClick={save} disabled={saving} className="btn-accent inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-semibold disabled:opacity-50" data-testid="menu-manager-save">
            <Save className="w-4 h-4" /> {saving ? "Se salvează..." : "Salvează meniul"}
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-lime-300/40 bg-lime-50 dark:bg-lime-900/10 dark:border-lime-700/40 p-4 flex flex-wrap items-center gap-3" data-testid="auto-reorder-panel">
        <div className="flex-1 min-w-[240px]">
          <div className="text-sm font-bold text-slate-900 dark:text-white">🤖 Auto-ordonare după popularitate (Autonomy)</div>
          <p className="text-xs text-slate-500 mt-0.5">Serviciile cele mai căutate din meniu (click-uri 30 zile) urcă automat primele în „Servicii" — rulare zilnică la 04:30.</p>
        </div>
        <button onClick={toggleAutoReorder}
          className={`px-4 py-2 rounded-full text-xs font-black border ${autoReorder ? "bg-lime-400 text-black border-lime-500" : "bg-white dark:bg-slate-800 text-slate-500 border-slate-200 dark:border-slate-600"}`}
          data-testid="auto-reorder-toggle">
          {autoReorder ? "ACTIV" : "INACTIV"}
        </button>
        <button onClick={runReorderNow} disabled={running}
          className="px-4 py-2 rounded-full text-xs font-semibold border border-slate-200 dark:border-slate-600 hover:bg-white dark:hover:bg-slate-800 disabled:opacity-50"
          data-testid="auto-reorder-run">
          {running ? "Rulează..." : "Rulează acum"}
        </button>
      </div>

      <div className="space-y-4">
        {items.map((it, i) => (
          <div key={it.id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-3 space-y-2" data-testid={`mm-group-${it.id}`}>
            <ItemRow
              item={it}
              isChild={false}
              pageKeys={pageKeys}
              onChange={(v) => setItems(items.map((x, xi) => (xi === i ? v : x)))}
              onMove={(dir) => setItems(move(items, i, dir))}
              onDelete={() => setItems(items.filter((_, xi) => xi !== i))}
            />
            {(it.children || []).length > 0 && (
              <div className="ml-6 space-y-2 border-l border-white/10 pl-3">
                {it.children.map((c, ci) => (
                  <ItemRow
                    key={c.id}
                    item={c}
                    isChild
                    pageKeys={pageKeys}
                    onChange={(v) => setItems(items.map((x, xi) => xi === i ? { ...x, children: x.children.map((y, yi) => (yi === ci ? v : y)) } : x))}
                    onMove={(dir) => setItems(items.map((x, xi) => (xi === i ? { ...x, children: move(x.children, ci, dir) } : x)))}
                    onDelete={() => setItems(items.map((x, xi) => (xi === i ? { ...x, children: x.children.filter((_, yi) => yi !== ci) } : x)))}
                  />
                ))}
              </div>
            )}
            <button
              onClick={() => setItems(items.map((x, xi) => (xi === i ? { ...x, children: [...(x.children || []), newItem()] } : x)))}
              className="ml-6 inline-flex items-center gap-1.5 text-xs text-stone-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/5"
              data-testid={`mm-add-child-${it.id}`}
            >
              <Plus className="w-3.5 h-3.5" /> Adaugă subcategorie
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={() => setItems([...items, newItem()])}
        className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-dashed border-white/20"
        data-testid="menu-manager-add-item"
      >
        <Plus className="w-4 h-4" /> Adaugă element principal
      </button>

      <div className="text-xs text-stone-500 space-y-1 pt-2 border-t border-white/10">
        <p>• <b>Regula platformei</b>: un serviciu apare public DOAR când e marcat <b>Activ</b> (ochi) și <b>Vizibil în website = DA</b>. Serviciile incomplete rămân ascunse până le activezi de aici.</p>
        <p>• <b>Detalii serviciu</b> (⚙ pe subcategorii): descriere, categorie, imagine, tip destinație (pagină internă / Marketplace / URL extern / fără) și partenerii externi cu prioritate.</p>
        <p>• <b>URL extern</b>: serviciile cu parteneri primesc automat pagina publică <code>/servicii/&#123;id&#125;</code> (ex. Mobilier la comandă).</p>
        <p>• <b>Vizibilitate</b>: „Toți" = oricine; „Doar vizitatori" = ascuns după login; „Doar autentificați" = vizibil doar cu cont.</p>
        <p>• <b>Link-uri speciale</b>: <code>/dashboard</code> duce automat la dashboard-ul rolului; <code>#logout</code> deconectează.</p>
        <p>• <b>Iconuri disponibile</b>: {ICON_SUGGESTIONS}.</p>
      </div>
    </div>
    </AdminLayoutMetronic>
  );
}
