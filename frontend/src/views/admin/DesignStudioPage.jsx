// DesignStudioPage — Admin control panel over the entire UI.
// Tabs: Tokens (colors/typography/radii/shadows/components) · Presets · Component Library ·
// UX Validator (link to Design Audit) · Design Lock · Roadmap (future builders).
//
// Any change is persisted via /api/admin/design-studio/* and instantly applied
// to the running app via DesignTokensProvider (CSS variables).
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Palette, Type, Layers, Square, Sparkles, Save, RotateCcw, Trash2,
  Lock, Unlock, CheckCircle2, AlertTriangle, ChevronRight, Sun, Moon,
  Layout, Menu, MousePointer2, FormInput, Table2, Puzzle, Code2, PlayCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSBadge, EmptyState } from "../../design-system";
import { dispatchTokensUpdated, useDesignTokens } from "../../contexts/DesignTokensProvider";

const ax = axios.create({ baseURL: API, withCredentials: true });

const TABS = [
  { id: "tokens",    label: "Design Tokens", icon: Palette },
  { id: "cascade",   label: "Palette Cascade", icon: Sparkles },
  { id: "presets",   label: "Presets",       icon: Sparkles },
  { id: "components",label: "Componente",    icon: Puzzle },
  { id: "validator", label: "UX Validator",  icon: CheckCircle2 },
  { id: "lock",      label: "Design Lock",   icon: Lock },
  { id: "roadmap",   label: "Roadmap Builder", icon: Layout },
];

// ── Palette Cascade sub-panel ────────────────────────────────────────────
const PaletteCascade = ({ onApplied, ax, flash }) => {
  const [primary, setPrimary]         = useState("#d4ff3a");
  const [accent, setAccent]           = useState("#a3e635");
  const [neutral, setNeutral]         = useState("#1c1917");
  const [surfaceLight, setSurfaceLight] = useState("#fafaf9");
  const [surfaceDark, setSurfaceDark]   = useState("#0a0d0c");
  const [preview, setPreview]         = useState(null);
  const [busy, setBusy]               = useState(false);

  const dry = async () => {
    setBusy(true);
    try {
      const r = await ax.post("/admin/design-studio/palette-cascade", {
        primary, accent, neutral, surface_light: surfaceLight, surface_dark: surfaceDark, apply: false,
      });
      setPreview(r.data.colors);
    } catch (e) { flash("Cascade dry-run eșuat.", "err"); }
    setBusy(false);
  };

  const apply = async () => {
    setBusy(true);
    try {
      const r = await ax.post("/admin/design-studio/palette-cascade", {
        primary, accent, neutral, surface_light: surfaceLight, surface_dark: surfaceDark, apply: true,
      });
      setPreview(r.data.colors);
      onApplied?.(r.data.tokens);
      flash("Paleta aplicată live pe întreaga platformă.");
    } catch (e) { flash("Cascade apply eșuat.", "err"); }
    setBusy(false);
  };

  return (
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 space-y-3" data-testid="ds-cascade-inputs">
        <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <div className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-1">Introdu 5 hex-uri și platforma se pictează singură</div>
          <p className="text-xs text-slate-500 mb-3">Sistemul derivă automat cele 20 de culori (bg, surface, text, muted, borders, on-primary contrast) pentru light & dark. Fără să atingi butoanele/cardurile.</p>
          <div className="grid sm:grid-cols-2 gap-2">
            <ColorField label="Primary (brand)"     value={primary}     onChange={setPrimary}     testid="pc-primary" />
            <ColorField label="Accent (secundar)"   value={accent}      onChange={setAccent}      testid="pc-accent" />
            <ColorField label="Neutral (ink text)"  value={neutral}     onChange={setNeutral}     testid="pc-neutral" />
            <ColorField label="Surface Light"       value={surfaceLight} onChange={setSurfaceLight} testid="pc-surface-light" />
            <ColorField label="Surface Dark"        value={surfaceDark}  onChange={setSurfaceDark}  testid="pc-surface-dark" />
          </div>
          <div className="flex gap-2 mt-4">
            <DSButton variant="ghost" onClick={dry} disabled={busy} data-testid="pc-preview-btn">Doar Preview</DSButton>
            <DSButton variant="primary" icon={Sparkles} onClick={apply} disabled={busy} data-testid="pc-apply-btn">
              {busy ? "Derivare..." : "Cascadează pe toate ecranele"}
            </DSButton>
          </div>
        </div>

        <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Cum funcționează derivarea</div>
          <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
            <li>• <b>primary_dim</b> = primary mixat 15% cu negru</li>
            <li>• <b>on_primary</b> = alb sau negru automat prin luminance WCAG (contrast maxim)</li>
            <li>• <b>accent_ink</b> = accent amestecat 35% cu neutral (text lizibil)</li>
            <li>• <b>surface_high / border / text_muted</b> = derivate din neutral & surface prin mixaje calibrate</li>
            <li>• <b>text_dark & muted_dark</b> = auto-generate din surface_dark pentru dark mode</li>
            <li>• <b>success/warning/danger/info</b> = semantice universale (verde/portocaliu/roșu/cyan)</li>
          </ul>
        </div>
      </div>

      <div className="lg:col-span-1">
        <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="ds-cascade-preview">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Preview derivare</div>
          {!preview ? (
            <div className="text-xs text-slate-400">Apasă „Doar Preview" ca să vezi cele 20 culori derivate deterministc.</div>
          ) : (
            <div className="space-y-1.5">
              {Object.entries(preview).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 text-[11px]">
                  <span className="w-6 h-6 rounded border border-slate-200 dark:border-slate-700 shrink-0" style={{ background: v }} />
                  <span className="font-mono text-slate-500 dark:text-slate-400 min-w-[110px] truncate">{k}</span>
                  <span className="font-mono text-slate-700 dark:text-slate-200">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Small color swatch input with hex text ─────────────────────────────────
const ColorField = ({ label, value, onChange, testid }) => (
  <label className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
    <input type="color" value={value || "#000000"} onChange={e => onChange(e.target.value)} data-testid={`${testid}-picker`}
      className="w-9 h-9 rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer shrink-0" />
    <div className="flex-1 min-w-0">
      <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{label}</div>
      <input type="text" value={value || ""} onChange={e => onChange(e.target.value)} data-testid={`${testid}-text`}
        className="mt-0.5 w-full bg-transparent text-[11px] font-mono text-slate-500 dark:text-slate-400 focus:outline-none" />
    </div>
  </label>
);

const TextField = ({ label, value, onChange, testid, mono = false }) => (
  <label className="block p-2.5">
    <div className="text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1">{label}</div>
    <input type="text" value={value || ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className={`w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-100 ${mono ? "font-mono" : ""}`} />
  </label>
);

const SelectField = ({ label, value, options, onChange, testid }) => (
  <label className="block p-2.5">
    <div className="text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1">{label}</div>
    <select value={value || ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className="w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-100">
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  </label>
);

// ── Live preview panel: renders one of each key component using current tokens
const LivePreview = ({ tokens }) => (
  <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="ds-preview">
    <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Preview live</div>
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <button className="px-4 py-2 rounded-full font-semibold text-sm transition-all"
          style={{ background: "var(--pm-primary)", color: "var(--pm-on-primary)", borderRadius: "var(--pm-radius-pill)", boxShadow: "var(--pm-glow-primary)" }}>
          Primary Button
        </button>
        <button className="px-4 py-2 rounded-full font-semibold text-sm border transition-all"
          style={{ borderRadius: "var(--pm-radius-pill)", borderColor: "var(--pm-outline, currentColor)", color: "var(--pm-text)" }}>
          Secondary
        </button>
        <span className="px-3 py-1 rounded-full text-xs font-bold uppercase" style={{ background: "var(--pm-primary)", color: "var(--pm-on-primary)", borderRadius: "var(--pm-radius-pill)" }}>Badge</span>
      </div>
      <div className="p-4 border rounded-2xl" style={{ background: "var(--pm-surface)", borderColor: "var(--pm-outline, rgba(0,0,0,.1))", borderRadius: "var(--pm-radius-lg)", boxShadow: "var(--pm-shadow-md)" }}>
        <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--pm-text-variant)" }}>KPI CARD</div>
        <div className="text-3xl font-black mt-1" style={{ color: "var(--pm-text)" }}>1,432</div>
        <div className="text-xs mt-1" style={{ color: "var(--pm-accent-ink)" }}>+12% vs perioada trecută</div>
      </div>
      <div style={{ fontFamily: "var(--pm-font-serif)", color: "var(--pm-text)" }} className="text-2xl">Titlu Serif · Fraunces</div>
      <div style={{ fontFamily: "var(--pm-font-sans)", color: "var(--pm-text-variant)" }} className="text-sm">Corp text sans · {tokens?.typography?.sans?.split(",")[0]?.replace(/'/g, "") || "Geist"}</div>
    </div>
  </div>
);

export default function DesignStudioPage() {
  const [tab, setTab] = useState("tokens");
  const [tokens, setTokens] = useState(null);
  const [initial, setInitial] = useState(null);
  const [presets, setPresets] = useState([]);
  const [components, setComponents] = useState([]);
  const [lock, setLock] = useState(null);
  const [builder, setBuilder] = useState({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const { reload: reloadGlobal } = useDesignTokens();

  const flash = (m, tone = "ok") => { setMsg({ text: m, tone }); setTimeout(() => setMsg(null), 2500); };

  const load = useCallback(async () => {
    try {
      const [t, p, c, l, b] = await Promise.all([
        ax.get("/admin/design-studio/tokens"),
        ax.get("/admin/design-studio/presets"),
        ax.get("/admin/design-studio/components"),
        ax.get("/admin/design-studio/lock"),
        ax.get("/admin/design-studio/builder-status"),
      ]);
      setTokens(t.data.tokens);
      setInitial(JSON.parse(JSON.stringify(t.data.tokens)));
      setPresets(p.data.presets || []);
      setComponents(c.data.components || []);
      setLock(l.data);
      setBuilder(b.data.modules || {});
    } catch (e) {
      flash("Nu s-a putut încărca configurația.", "err");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const dirty = tokens && initial && JSON.stringify(tokens) !== JSON.stringify(initial);

  const patchGroup = (group, key, val) => {
    setTokens(prev => ({ ...prev, [group]: { ...(prev?.[group] || {}), [key]: val } }));
  };

  const saveTokens = async () => {
    setSaving(true);
    try {
      const r = await ax.put("/admin/design-studio/tokens", tokens);
      setTokens(r.data.tokens);
      setInitial(JSON.parse(JSON.stringify(r.data.tokens)));
      dispatchTokensUpdated();
      reloadGlobal();
      flash("Tokens salvate — se aplică live pe întreaga platformă.");
    } catch (e) {
      flash("Salvarea a eșuat.", "err");
    }
    setSaving(false);
  };

  const resetToDefault = async () => {
    if (!confirm("Resetezi la PropManage Default? Modificările locale se pierd.")) return;
    try {
      const r = await ax.post("/admin/design-studio/reset");
      setTokens(r.data.tokens);
      setInitial(JSON.parse(JSON.stringify(r.data.tokens)));
      dispatchTokensUpdated();
      reloadGlobal();
      flash("Reset la Default.");
    } catch (e) { flash("Reset eșuat.", "err"); }
  };

  const applyPreset = async (id) => {
    try {
      const r = await ax.post("/admin/design-studio/presets/apply", { preset_id: id });
      setTokens(r.data.tokens);
      setInitial(JSON.parse(JSON.stringify(r.data.tokens)));
      dispatchTokensUpdated();
      reloadGlobal();
      flash(`Preset aplicat: ${id}`);
    } catch (e) { flash("Aplicare preset eșuată.", "err"); }
  };

  const saveAsPreset = async () => {
    const name = prompt("Nume preset nou:");
    if (!name) return;
    const description = prompt("Descriere scurtă:") || "";
    try {
      await ax.post("/admin/design-studio/presets", { name, description });
      load();
      flash("Preset salvat.");
    } catch (e) { flash("Salvare preset eșuată.", "err"); }
  };

  const deletePreset = async (id) => {
    if (!confirm("Ștergi acest preset?")) return;
    try {
      await ax.delete(`/admin/design-studio/presets/${id}`);
      load();
      flash("Preset șters.");
    } catch (e) { flash("Ștergere eșuată.", "err"); }
  };

  const toggleLock = async () => {
    try {
      const r = await ax.put("/admin/design-studio/lock", { enabled: !(lock?.enabled) });
      setLock(r.data);
      flash(`Design Lock ${r.data.enabled ? "activat" : "dezactivat"}.`);
    } catch (e) { flash("Toggle lock eșuat.", "err"); }
  };

  return (
    <AdminLayoutMetronic
      active="design_studio"
      title="Design Studio"
      subtitle="Control central UI · Tokens · Presets · Component Library · UX Validator · Design Lock"
    >
      {/* Sticky action bar */}
      <div className="sticky top-0 z-20 -mx-6 -mt-6 mb-4 px-6 py-3 backdrop-blur bg-white/90 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1 flex-wrap">
            {TABS.map(t => {
              const Ico = t.icon;
              const active = tab === t.id;
              return (
                <button key={t.id} onClick={() => setTab(t.id)} data-testid={`ds-tab-${t.id}`}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${active ? "bg-lime-400 text-slate-900" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}`}>
                  <Ico className="w-3.5 h-3.5" />{t.label}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2">
            {dirty && <DSBadge type="WARNING">Nesalvat</DSBadge>}
            <DSButton variant="ghost" icon={RotateCcw} onClick={resetToDefault} data-testid="ds-reset">Reset</DSButton>
            <DSButton variant="primary" icon={Save} onClick={saveTokens} disabled={!dirty || saving} data-testid="ds-save">
              {saving ? "Salvez..." : "Salvează + Aplică"}
            </DSButton>
          </div>
        </div>
        {msg && (
          <div className={`mt-2 text-xs font-semibold ${msg.tone === "err" ? "text-rose-500" : "text-emerald-600 dark:text-emerald-300"}`} data-testid="ds-msg">{msg.text}</div>
        )}
      </div>

      {!tokens ? <EmptyState icon={Palette} title="Se încarcă tokens..." /> : (
        <>
          {tab === "tokens" && (
            <div className="grid lg:grid-cols-3 gap-4" data-testid="ds-tokens-tab">
              <div className="lg:col-span-2 space-y-4">
                <AdminCard title={<span className="flex items-center gap-2"><Palette className="w-4 h-4 text-lime-500" /> Culori</span>} testid="ds-colors">
                  <div className="grid sm:grid-cols-2 gap-1">
                    {Object.entries(tokens.colors || {}).map(([k, v]) => (
                      <ColorField key={k} label={k.replace(/_/g, " ")} value={v} onChange={val => patchGroup("colors", k, val)} testid={`ds-color-${k}`} />
                    ))}
                  </div>
                </AdminCard>

                <AdminCard title={<span className="flex items-center gap-2"><Type className="w-4 h-4 text-lime-500" /> Tipografie</span>} testid="ds-typography">
                  <div className="grid sm:grid-cols-2 gap-1">
                    {Object.entries(tokens.typography || {}).map(([k, v]) => (
                      <TextField key={k} label={k.replace(/_/g, " ")} value={v} onChange={val => patchGroup("typography", k, val)} testid={`ds-type-${k}`} mono />
                    ))}
                  </div>
                </AdminCard>

                <AdminCard title={<span className="flex items-center gap-2"><Square className="w-4 h-4 text-lime-500" /> Radii & Shadows</span>} testid="ds-radii">
                  <div className="grid sm:grid-cols-2 gap-1">
                    {Object.entries(tokens.radii || {}).map(([k, v]) => (
                      <TextField key={`r-${k}`} label={`radius.${k}`} value={v} onChange={val => patchGroup("radii", k, val)} testid={`ds-radius-${k}`} mono />
                    ))}
                    {Object.entries(tokens.shadows || {}).map(([k, v]) => (
                      <TextField key={`s-${k}`} label={`shadow.${k}`} value={v} onChange={val => patchGroup("shadows", k, val)} testid={`ds-shadow-${k}`} mono />
                    ))}
                  </div>
                </AdminCard>

                <AdminCard title={<span className="flex items-center gap-2"><Layers className="w-4 h-4 text-lime-500" /> Stiluri componente</span>} testid="ds-components">
                  <div className="grid sm:grid-cols-2 gap-1">
                    <SelectField label="button_style" value={tokens.components?.button_style} options={["pill", "rounded", "sharp"]} onChange={v => patchGroup("components", "button_style", v)} testid="ds-comp-button" />
                    <SelectField label="input_style" value={tokens.components?.input_style} options={["rounded", "sharp", "underline"]} onChange={v => patchGroup("components", "input_style", v)} testid="ds-comp-input" />
                    <SelectField label="card_style" value={tokens.components?.card_style} options={["elevated", "flat", "glass"]} onChange={v => patchGroup("components", "card_style", v)} testid="ds-comp-card" />
                    <SelectField label="table_density" value={tokens.components?.table_density} options={["comfortable", "compact", "dense"]} onChange={v => patchGroup("components", "table_density", v)} testid="ds-comp-table" />
                    <SelectField label="sidebar_style" value={tokens.components?.sidebar_style} options={["solid", "translucent"]} onChange={v => patchGroup("components", "sidebar_style", v)} testid="ds-comp-sidebar" />
                    <SelectField label="header_style" value={tokens.components?.header_style} options={["sticky", "static", "floating"]} onChange={v => patchGroup("components", "header_style", v)} testid="ds-comp-header" />
                    <SelectField label="badge_style" value={tokens.components?.badge_style} options={["pill", "square"]} onChange={v => patchGroup("components", "badge_style", v)} testid="ds-comp-badge" />
                    <SelectField label="chart_theme" value={tokens.components?.chart_theme} options={["brand", "mono", "vivid"]} onChange={v => patchGroup("components", "chart_theme", v)} testid="ds-comp-chart" />
                    <SelectField label="kpi_variant" value={tokens.components?.kpi_variant} options={["bordered", "filled", "ghost"]} onChange={v => patchGroup("components", "kpi_variant", v)} testid="ds-comp-kpi" />
                  </div>
                </AdminCard>
              </div>

              <div className="lg:col-span-1 space-y-4">
                <LivePreview tokens={tokens} />
                <div className="p-3 rounded-2xl border border-lime-200 dark:border-lime-500/30 bg-lime-50 dark:bg-lime-500/10 text-xs text-lime-900 dark:text-lime-200">
                  <div className="font-bold mb-1 flex items-center gap-1"><Sparkles className="w-3.5 h-3.5" /> Cum funcționează</div>
                  Toate paginile citesc CSS variables (<code>--pm-primary</code>, <code>--pm-surface</code>, …). Când salvezi, se propagă instant. Nu e nevoie de redeploy.
                </div>
              </div>
            </div>
          )}

          {tab === "cascade" && (
            <PaletteCascade
              ax={ax}
              flash={flash}
              onApplied={(t) => { setTokens(t); setInitial(JSON.parse(JSON.stringify(t))); dispatchTokensUpdated(); reloadGlobal(); }}
            />
          )}

          {tab === "presets" && (
            <div className="space-y-4" data-testid="ds-presets-tab">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">{presets.length} preseturi disponibile</h3>
                <DSButton variant="primary" icon={Save} onClick={saveAsPreset} data-testid="ds-save-preset">Salvează tokens curente ca preset</DSButton>
              </div>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                {presets.map(p => (
                  <AdminCard key={p.id} testid={`ds-preset-${p.id}`}>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <div className="text-sm font-bold text-slate-800 dark:text-slate-100">{p.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{p.description}</div>
                      </div>
                      {p.builtin ? <DSBadge type="LIVE">BUILT-IN</DSBadge> : <DSBadge type="NEW">CUSTOM</DSBadge>}
                    </div>
                    <div className="flex gap-1 mb-3 h-6">
                      {["primary", "primary_dim", "bg", "surface", "accent_ink"].map(k => (
                        <div key={k} className="flex-1 rounded" style={{ background: p.tokens?.colors?.[k] || "#000", boxShadow: "0 0 0 1px rgba(0,0,0,.05)" }} title={`${k}: ${p.tokens?.colors?.[k]}`} />
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <DSButton variant="primary" onClick={() => applyPreset(p.id)} data-testid={`ds-preset-apply-${p.id}`}>Aplică</DSButton>
                      {!p.builtin && <DSButton variant="danger" icon={Trash2} onClick={() => deletePreset(p.id)} data-testid={`ds-preset-del-${p.id}`}>Șterge</DSButton>}
                    </div>
                  </AdminCard>
                ))}
              </div>
            </div>
          )}

          {tab === "components" && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="ds-components-tab">
              {components.map(c => (
                <div key={c.key} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid={`ds-comp-item-${c.key}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-sm font-bold text-slate-800 dark:text-slate-100">{c.label}</div>
                    <DSBadge type="ACTIVE">{c.category}</DSBadge>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">{c.key}</div>
                  <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Tokens folosite</div>
                    <div className="flex flex-wrap gap-1">
                      {c.tokens.map(t => <span key={t} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-lime-50 dark:bg-lime-500/15 text-lime-800 dark:text-lime-300 border border-lime-200 dark:border-lime-500/30">{t}</span>)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "validator" && (
            <AdminCard title={<span className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-lime-500" /> UX Validator (AI · Claude)</span>} testid="ds-validator">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Scanează fiecare pagină din platformă, îi dă scoruri (mobile, desktop, unitate, legea lui Hick) și livrează 3-5 recomandări acționabile.
                Rulează separat în modulul dedicat, iar rezultatele apar aici ca „worst mobile / desktop” în viitoarele iterații.
              </p>
              <div className="mt-4">
                <Link to="/admin/design-audit" data-testid="ds-validator-link">
                  <DSButton variant="primary" icon={PlayCircle}>Deschide Design Audit</DSButton>
                </Link>
              </div>
              <ul className="mt-5 space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                <li className="flex items-start gap-2"><ChevronRight className="w-3 h-3 mt-0.5 text-lime-500" /> 13 pagini catalogate (public, client, specialist, operator, admin).</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-3 h-3 mt-0.5 text-lime-500" /> Fiecare audit se cache 12h — costul LLM rămâne controlat.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-3 h-3 mt-0.5 text-lime-500" /> Legea lui Hick: scor separat + recomandări de reducere a alegerilor.</li>
              </ul>
            </AdminCard>
          )}

          {tab === "lock" && lock && (
            <AdminCard
              title={<span className="flex items-center gap-2">{lock.enabled ? <Lock className="w-4 h-4 text-emerald-500" /> : <Unlock className="w-4 h-4 text-amber-500" />} Design Lock — politica de coerență</span>}
              action={
                <DSButton variant={lock.enabled ? "danger" : "success"} onClick={toggleLock} data-testid="ds-lock-toggle">
                  {lock.enabled ? "Dezactivează Lock" : "Activează Lock"}
                </DSButton>
              }
              testid="ds-lock"
            >
              <div className={`p-3 rounded-xl mb-3 text-sm ${lock.enabled ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-500/30" : "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-500/30"}`}>
                {lock.enabled
                  ? "🔒 Design Lock e ACTIV. Toate paginile noi trebuie să respecte tokens + componente Design System."
                  : "⚠️ Design Lock e DEZACTIVAT. Dev-ii pot introduce stiluri ad-hoc. Nerecomandat în producție."}
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Reguli aplicate</div>
              <ul className="space-y-1.5">
                {(lock.rules || []).map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200">
                    <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 text-lime-500 shrink-0" />{r}
                  </li>
                ))}
              </ul>
            </AdminCard>
          )}

          {tab === "roadmap" && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="ds-roadmap-tab">
              {Object.entries(builder).map(([key, meta]) => {
                const iconMap = {
                  page_builder: Layout, menu_manager: Menu, button_manager: MousePointer2,
                  form_builder: FormInput, table_builder: Table2, dashboard_builder: Layers,
                  developer_mode: Code2,
                };
                const Ico = iconMap[key] || Puzzle;
                const statusMap = {
                  planned:        { badge: "BETA",    tone: "text-slate-500 dark:text-slate-400" },
                  in_development: { badge: "BETA",    tone: "text-amber-600 dark:text-amber-300" },
                  beta:           { badge: "LIVE",    tone: "text-lime-600 dark:text-lime-300" },
                };
                const s = statusMap[meta.status] || statusMap.planned;
                return (
                  <div key={key} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid={`ds-roadmap-${key}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="w-8 h-8 rounded-lg bg-lime-500/15 border border-lime-500/40 flex items-center justify-center">
                          <Ico className="w-4 h-4 text-lime-700 dark:text-lime-300" />
                        </span>
                        <div>
                          <div className="text-sm font-bold text-slate-800 dark:text-slate-100">{key.replace(/_/g, " ")}</div>
                          <div className="text-[10px] uppercase tracking-wider text-slate-500">ETA: {meta.eta}</div>
                        </div>
                      </div>
                      <DSBadge type={s.badge}>{meta.status}</DSBadge>
                    </div>
                    <p className={`text-xs ${s.tone}`}>{meta.note}</p>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </AdminLayoutMetronic>
  );
}
