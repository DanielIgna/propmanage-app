// Page Registry — Configuration Layer (Task 7).
// Canonical editor for per-page: menu label / H1 / subtitle / SEO / OG /
// visibility / feature flag / status. Supports DRAFT -> PUBLISH -> LIVE
// with version history and restore. Route/URL is read-only.
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  FileText, Save, Undo2, RotateCcw, History, Rocket, Eye,
  Globe, Search, Sparkles, ShieldAlert, ListChecks, X,
} from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";

const API = process.env.REACT_APP_BACKEND_URL;

const ROLE_OPTIONS = ["client", "specialist", "operator", "admin", "partner"];
const TIER_OPTIONS = ["junior", "regular", "verified", "premium", "pro"];

const StatusBadge = ({ status }) => {
  const map = {
    active: "bg-lime-500/15 text-lime-400 border-lime-500/30",
    hidden: "bg-slate-500/15 text-slate-400 border-slate-500/30",
    draft: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  };
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${map[status] || map.hidden}`}>
      {status}
    </span>
  );
};

const DiffLine = ({ label, live, draft }) => {
  const changed = String(live || "") !== String(draft || "");
  return (
    <div className={`grid grid-cols-[110px_1fr_1fr] gap-2 items-start py-1.5 ${changed ? "" : "opacity-60"}`}>
      <div className="text-[11px] uppercase tracking-wider font-bold text-stone-500 pt-0.5">{label}</div>
      <div className={`text-xs px-2 py-1 rounded ${changed ? "bg-red-500/10 text-red-300" : "bg-white/5 text-stone-300"}`} title="LIVE">
        {String(live || "") || <span className="italic text-stone-500">—</span>}
      </div>
      <div className={`text-xs px-2 py-1 rounded ${changed ? "bg-lime-500/10 text-lime-300" : "bg-white/5 text-stone-300"}`} title="DRAFT">
        {String(draft || "") || <span className="italic text-stone-500">—</span>}
      </div>
    </div>
  );
};

const TextField = ({ label, hint, value, onChange, multiline = false, testid, disabled = false }) => (
  <label className="block space-y-1">
    <div className="text-[11px] uppercase tracking-wider font-bold text-stone-500">{label}</div>
    {multiline ? (
      <textarea
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={3}
        className="w-full px-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid={testid}
      />
    ) : (
      <input
        type="text"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full px-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid={testid}
      />
    )}
    {hint && <div className="text-[11px] text-stone-500">{hint}</div>}
  </label>
);

const ChipToggle = ({ label, options, values, onChange, testid }) => {
  const set = new Set(values || []);
  return (
    <div className="space-y-1">
      <div className="text-[11px] uppercase tracking-wider font-bold text-stone-500">{label}</div>
      <div className="flex flex-wrap gap-2" data-testid={testid}>
        {options.map((o) => {
          const on = set.has(o);
          return (
            <button
              key={o}
              onClick={() => {
                const next = new Set(set);
                if (on) next.delete(o); else next.add(o);
                onChange(Array.from(next));
              }}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                on ? "bg-lime-400 text-black border-lime-500" : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"
              }`}
              data-testid={`${testid}-${o}`}
            >
              {o}
            </button>
          );
        })}
      </div>
    </div>
  );
};

const VersionHistory = ({ pageKey, onRestore }) => {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/api/admin/pages/${pageKey}/versions`);
      setItems(data.items || []);
    } catch (_) { setItems([]); }
  };

  useEffect(() => { load(); }, [pageKey]);

  const restore = async (v) => {
    setBusy(v);
    try {
      await axios.post(`${API}/api/admin/pages/${pageKey}/restore/${v}`);
      onRestore && (await onRestore());
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(null);
    }
  };

  if (!items.length) return <div className="text-xs text-stone-500 italic p-3">Nu există versiuni salvate încă.</div>;

  return (
    <div className="space-y-2" data-testid="page-version-history">
      {items.map((v) => (
        <div key={`${v.page_key}-${v.version}-${v.published_at}`} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
          <div className="w-10 h-10 rounded-lg bg-lime-500/15 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-lime-400">v{v.version}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm text-stone-200 truncate">
              {v.snapshot?.seo_title || v.snapshot?.h1 || <span className="italic text-stone-500">fără titlu</span>}
            </div>
            <div className="text-[11px] text-stone-500 truncate">
              publicat de {v.published_by || "—"} · {v.published_at ? new Date(v.published_at).toLocaleString("ro-RO") : ""}
              {v.note && <span className="ml-1 text-amber-400">· {v.note}</span>}
            </div>
          </div>
          <button
            onClick={() => restore(v.version)}
            disabled={busy === v.version}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-50"
            data-testid={`page-restore-v${v.version}`}
          >
            {busy === v.version ? "Se restaurează..." : "Restaurează în draft"}
          </button>
        </div>
      ))}
    </div>
  );
};

const PreviewOverlay = ({ data, onClose }) => {
  if (!data) return null;
  const d = data.data || {};
  return (
    <div
      className="fixed inset-0 z-[70] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="preview-overlay"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-amber-500/30 bg-[#0d0d0f]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-2 px-5 py-3 bg-[#1a1408] border-b border-amber-500/30">
          <div className="flex items-center gap-2 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <Eye className="w-4 h-4" /> Mod Preview · simulare post-publish · LIVE neatins
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-stone-300" data-testid="preview-overlay-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-6 space-y-5">
          <div className="flex flex-wrap items-center gap-2 text-xs text-stone-400">
            <span className="px-2 py-0.5 rounded-full border border-white/10 bg-white/5 font-mono">{d.route}</span>
            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase ${data.source === "draft" ? "border-amber-500/30 bg-amber-500/10 text-amber-300" : "border-lime-500/30 bg-lime-500/10 text-lime-300"}`}>
              sursă: {data.source}
            </span>
            <span className="text-stone-500">v{d.version}</span>
          </div>
          {data.feature_flag_would_block && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs px-3 py-2" data-testid="preview-flag-blocked">
              Atenție: feature flag-ul curent ar bloca pagina publică (404) — preview-ul îl ignoră intenționat.
            </div>
          )}
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <div className="text-[10px] uppercase tracking-wider font-bold text-stone-500 mb-3">Conținut pagină (după publish)</div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight" data-testid="preview-h1">{d.h1 || "—"}</h1>
            <p className="text-sm text-stone-400 mt-2" data-testid="preview-subtitle">{d.subtitle || "—"}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white p-4">
            <div className="text-[10px] uppercase tracking-wider font-bold text-stone-400 mb-2">Google · SEO snippet</div>
            <div className="text-[#1a0dab] text-base leading-snug" data-testid="preview-seo-title">{d.seo_title || d.h1 || "—"}</div>
            <div className="text-[#006621] text-xs mt-0.5">propmanage.ro{d.route}</div>
            <div className="text-[#545454] text-xs mt-1 leading-snug" data-testid="preview-seo-desc">{d.seo_description || "—"}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[10px] uppercase tracking-wider font-bold text-stone-500 mb-2">Social share (Open Graph)</div>
            <div className="rounded-lg border border-white/10 overflow-hidden">
              <div className="h-20 bg-gradient-to-r from-lime-400/20 to-stone-800 flex items-center px-4">
                <span className="text-lg font-bold text-white" data-testid="preview-og-title">{d.og_title || d.seo_title || "—"}</span>
              </div>
              <div className="px-4 py-2 bg-black/40">
                <div className="text-xs text-stone-400">{d.og_description || d.seo_description || "—"}</div>
                <div className="text-[10px] text-stone-600 mt-1 uppercase">propmanage.ro</div>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-stone-400">
            <span>Menu label: <b className="text-stone-200">{d.menu_label || "—"}</b></span>
            <span>Desktop: <b className="text-stone-200">{d.desktop_visible ? "da" : "nu"}</b></span>
            <span>Mobil: <b className="text-stone-200">{d.mobile_visible ? "da" : "nu"}</b></span>
          </div>
        </div>
      </div>
    </div>
  );
};

const PageEditor = ({ page, onClose, onSaved }) => {
  const live = page.live || {};
  const [draft, setDraft] = useState(page.draft || live);
  const [status, setStatus] = useState(page.status);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const openPreview = async () => {
    setPreviewLoading(true);
    try {
      const { data } = await axios.get(`${API}/api/admin/pages/${page.key}/preview`);
      setPreview(data);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const hasDraft = !!page.draft;
  const patch = (k, v) => setDraft((d) => ({ ...d, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const body = { ...draft, status };
      const { data } = await axios.put(`${API}/api/admin/pages/${page.key}`, body);
      await onSaved(data.page);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally { setSaving(false); }
  };

  const publish = async () => {
    if (!hasDraft && !window.confirm("Nu există modificări noi. Publici oricum LIVE-ul curent?")) return;
    setPublishing(true);
    try {
      // Ensure any pending in-memory edit gets flushed first.
      await axios.put(`${API}/api/admin/pages/${page.key}`, { ...draft, status });
      await axios.post(`${API}/api/admin/pages/${page.key}/publish`);
      await onSaved();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally { setPublishing(false); }
  };

  const discard = async () => {
    if (!hasDraft) return;
    if (!window.confirm("Renunți la toate modificările din draft?")) return;
    await axios.post(`${API}/api/admin/pages/${page.key}/discard-draft`);
    await onSaved();
  };

  const reset = async () => {
    if (!window.confirm("Revert la textele implicite? Se creează un snapshot al versiunii curente.")) return;
    await axios.post(`${API}/api/admin/pages/${page.key}/reset`);
    await onSaved();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-4" data-testid="page-editor-modal">
      <div className="w-full max-w-4xl my-6 rounded-2xl bg-[#0a0a0b] border border-white/10 shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#0a0a0b] rounded-t-2xl">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white truncate">{page.key}</h2>
              <StatusBadge status={status} />
              {hasDraft && <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40">draft nepublicat</span>}
            </div>
            <div className="text-xs text-stone-500 mt-0.5 flex items-center gap-1.5">
              <Globe className="w-3 h-3" /> <code className="text-stone-400">{page.route}</code>
              <span className="text-stone-600">(read-only)</span>
              <span className="ml-2">v{live.version || 0}</span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10" data-testid="page-editor-close"><X className="w-5 h-5 text-stone-400" /></button>
        </div>

        <div className="p-6 space-y-6">
          {/* Section 1 · Status + Menu identity */}
          <section className="space-y-3">
            <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
              <ListChecks className="w-3.5 h-3.5" /> 1. Identitate meniu &amp; status
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <TextField
                label="Menu label (afișat în navigare)"
                hint="Poate fi diferit de H1 sau de route."
                value={draft.menu_label}
                onChange={(v) => patch("menu_label", v)}
                testid="page-input-menu-label"
              />
              <label className="block space-y-1">
                <div className="text-[11px] uppercase tracking-wider font-bold text-stone-500">Status</div>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50"
                  data-testid="page-input-status"
                >
                  <option value="active">Active — pagina publică</option>
                  <option value="hidden">Hidden — retrasă temporar</option>
                  <option value="draft">Draft — încă în lucru</option>
                </select>
              </label>
            </div>
          </section>

          {/* Section 2 · Content (H1 + Subtitle) */}
          <section className="space-y-3">
            <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> 2. Conținut pagină (H1 &amp; Subtitle)
            </div>
            <TextField
              label="H1 — titlu principal vizibil"
              hint="Textul mare afișat pe pagina publică."
              value={draft.h1}
              onChange={(v) => patch("h1", v)}
              testid="page-input-h1"
            />
            <TextField
              label="Subtitle"
              hint="Fraza scurtă sub H1."
              multiline
              value={draft.subtitle}
              onChange={(v) => patch("subtitle", v)}
              testid="page-input-subtitle"
            />
          </section>

          {/* Section 3 · SEO + OG */}
          <section className="space-y-3">
            <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5" /> 3. SEO &amp; Open Graph
            </div>
            <TextField
              label="SEO title (browser + Google)"
              hint="Recomandat max 60 caractere."
              value={draft.seo_title}
              onChange={(v) => patch("seo_title", v)}
              testid="page-input-seo-title"
            />
            <TextField
              label="SEO description (Google snippet)"
              hint="Recomandat 150–160 caractere."
              multiline
              value={draft.seo_description}
              onChange={(v) => patch("seo_description", v)}
              testid="page-input-seo-description"
            />
            <div className="grid md:grid-cols-2 gap-4">
              <TextField
                label="OG title (share Facebook/LinkedIn)"
                hint="Dacă e gol, cade la SEO title."
                value={draft.og_title}
                onChange={(v) => patch("og_title", v)}
                testid="page-input-og-title"
              />
              <TextField
                label="OG description"
                hint="Dacă e gol, cade la SEO description."
                multiline
                value={draft.og_description}
                onChange={(v) => patch("og_description", v)}
                testid="page-input-og-description"
              />
            </div>
          </section>

          {/* Section 4 · Visibility */}
          <section className="space-y-3">
            <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" /> 4. Vizibilitate &amp; feature flag
            </div>
            <ChipToggle
              label="Roluri permise (gol = public)"
              options={ROLE_OPTIONS}
              values={draft.allowed_roles}
              onChange={(vs) => patch("allowed_roles", vs)}
              testid="page-chip-roles"
            />
            <ChipToggle
              label="Tier-uri permise (gol = orice tier)"
              options={TIER_OPTIONS}
              values={draft.allowed_tiers}
              onChange={(vs) => patch("allowed_tiers", vs)}
              testid="page-chip-tiers"
            />
            <div className="grid md:grid-cols-3 gap-3">
              <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
                <input type="checkbox" checked={!!draft.desktop_visible} onChange={(e) => patch("desktop_visible", e.target.checked)} data-testid="page-chk-desktop" />
                <span className="text-sm text-stone-300">Vizibil pe desktop</span>
              </label>
              <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
                <input type="checkbox" checked={!!draft.mobile_visible} onChange={(e) => patch("mobile_visible", e.target.checked)} data-testid="page-chk-mobile" />
                <span className="text-sm text-stone-300">Vizibil pe mobil</span>
              </label>
              <TextField
                label="Feature flag key (opțional)"
                hint="Se leagă la feature_config.enabled."
                value={draft.feature_flag}
                onChange={(v) => patch("feature_flag", v)}
                testid="page-input-feature-flag"
              />
            </div>
          </section>

          {/* Section 5 · LIVE vs DRAFT diff */}
          {hasDraft && (
            <section className="space-y-2 border-t border-white/10 pt-5">
              <div className="text-[11px] uppercase tracking-wider font-bold text-amber-400 flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5" /> 5. Preview LIVE vs DRAFT
              </div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                <div className="grid grid-cols-[110px_1fr_1fr] gap-2 text-[10px] font-bold uppercase tracking-wider text-stone-500 pb-2 border-b border-white/10">
                  <div>Câmp</div>
                  <div>LIVE (public)</div>
                  <div>DRAFT (după publish)</div>
                </div>
                <DiffLine label="Menu label" live={live.menu_label} draft={draft.menu_label} />
                <DiffLine label="H1" live={live.h1} draft={draft.h1} />
                <DiffLine label="Subtitle" live={live.subtitle} draft={draft.subtitle} />
                <DiffLine label="SEO title" live={live.seo_title} draft={draft.seo_title} />
                <DiffLine label="SEO desc" live={live.seo_description} draft={draft.seo_description} />
                <DiffLine label="OG title" live={live.og_title} draft={draft.og_title} />
                <DiffLine label="OG desc" live={live.og_description} draft={draft.og_description} />
                <DiffLine label="Feature flag" live={live.feature_flag} draft={draft.feature_flag} />
                <DiffLine label="Roles" live={(live.allowed_roles || []).join(", ")} draft={(draft.allowed_roles || []).join(", ")} />
                <DiffLine label="Tiers" live={(live.allowed_tiers || []).join(", ")} draft={(draft.allowed_tiers || []).join(", ")} />
              </div>
            </section>
          )}

          {/* Section 6 · Version history */}
          {showHistory && (
            <section className="space-y-2 border-t border-white/10 pt-5">
              <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" /> 6. Istoric versiuni
              </div>
              <VersionHistory
                pageKey={page.key}
                onRestore={async () => { await onSaved(); }}
              />
            </section>
          )}
        </div>

        <div className="sticky bottom-0 z-10 px-6 py-4 border-t border-white/10 bg-[#0a0a0b] rounded-b-2xl flex flex-wrap items-center gap-2 justify-end">
          <button
            onClick={() => setShowHistory((s) => !s)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10 mr-auto"
            data-testid="page-editor-toggle-history"
          >
            <History className="w-4 h-4" /> {showHistory ? "Ascunde istoric" : "Vezi istoric"}
          </button>
          <button
            onClick={reset}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10 text-red-300"
            data-testid="page-editor-reset"
          >
            <RotateCcw className="w-4 h-4" /> Reset defaults
          </button>
          {hasDraft && (
            <button
              onClick={openPreview}
              disabled={previewLoading}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 disabled:opacity-50"
              data-testid="page-editor-preview-draft"
            >
              <Eye className="w-4 h-4" /> {previewLoading ? "Se încarcă..." : "Preview draft"}
            </button>
          )}
          {preview && <PreviewOverlay data={preview} onClose={() => setPreview(null)} />}
          {hasDraft && (
            <button
              onClick={discard}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10"
              data-testid="page-editor-discard-draft"
            >
              <Undo2 className="w-4 h-4" /> Renunță la draft
            </button>
          )}
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-50"
            data-testid="page-editor-save-draft"
          >
            <Save className="w-4 h-4" /> {saving ? "Se salvează..." : "Salvează draft"}
          </button>
          <button
            onClick={publish}
            disabled={publishing}
            className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-lime-400 text-black hover:bg-lime-300 disabled:opacity-50"
            data-testid="page-editor-publish"
          >
            <Rocket className="w-4 h-4" /> {publishing ? "Se publică..." : "Publish LIVE"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function PageRegistryPage() {
  const [pages, setPages] = useState(null);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/api/admin/pages`);
      setPages(data.items || []);
    } catch (_) { setPages([]); }
  };
  useEffect(() => { load(); }, []);

  // Deep-link support: /admin/page-registry?edit=<key> opens the editor directly.
  useEffect(() => {
    if (!pages || pages.length === 0) return;
    const params = new URLSearchParams(window.location.search);
    const editKey = params.get("edit");
    if (editKey) {
      const p = pages.find((x) => x.key === editKey);
      if (p) setEditing(p);
    }
  }, [pages?.length]);

  const filtered = useMemo(() => {
    if (!pages) return [];
    const qq = q.trim().toLowerCase();
    return pages.filter((p) => {
      if (statusFilter && p.status !== statusFilter) return false;
      if (!qq) return true;
      return (
        p.key.toLowerCase().includes(qq) ||
        (p.route || "").toLowerCase().includes(qq) ||
        (p.live?.h1 || "").toLowerCase().includes(qq) ||
        (p.live?.menu_label || "").toLowerCase().includes(qq)
      );
    });
  }, [pages, q, statusFilter]);

  const reloadOne = async () => {
    await load();
    if (editing) {
      const fresh = (await axios.get(`${API}/api/admin/pages/${editing.key}`)).data;
      setEditing(fresh);
    }
  };

  if (!pages) {
    return (
      <AdminLayoutMetronic title="Page Registry" subtitle="Configuration Layer · Task 7">
        <div className="p-8 text-stone-400">Se încarcă paginile...</div>
      </AdminLayoutMetronic>
    );
  }

  return (
    <AdminLayoutMetronic title="Page Registry" subtitle="Sursa canonică pentru H1, subtitle, SEO, OG și vizibilitate per pagină">
      <div className="p-4 sm:p-8 max-w-6xl mx-auto space-y-6" data-testid="page-registry-page">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2 text-white">
              <FileText className="w-6 h-6 text-[#d4ff3a]" /> Page Registry
            </h1>
            <p className="text-sm text-stone-400 mt-1 max-w-2xl">
              Configurare centralizată per pagină: menu label, H1, subtitle, SEO, OG,
              vizibilitate și feature flag. <b>Route-ul rămâne protejat</b> (read-only).
              Fluxul <span className="text-amber-400">DRAFT</span> →
              <span className="text-lime-400"> PUBLISH </span>→
              <span className="text-white"> LIVE</span> creează versiuni salvate automat.
            </p>
          </div>
          <a
            href="/admin/menu-manager"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10 text-stone-300"
          >
            <Sparkles className="w-4 h-4" /> Deschide Menu Manager
          </a>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
            <input
              type="text"
              placeholder="Caută pagină (key, route, H1, label)..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50"
              data-testid="page-registry-search"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50"
            data-testid="page-registry-status-filter"
          >
            <option value="">Toate statusurile</option>
            <option value="active">Doar active</option>
            <option value="hidden">Doar hidden</option>
            <option value="draft">Doar draft</option>
          </select>
        </div>

        <div className="rounded-2xl border border-white/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/5">
              <tr className="text-left text-[11px] uppercase tracking-wider text-stone-500">
                <th className="px-4 py-3 font-bold">Key</th>
                <th className="px-4 py-3 font-bold">Route</th>
                <th className="px-4 py-3 font-bold">Menu label</th>
                <th className="px-4 py-3 font-bold">H1 (LIVE)</th>
                <th className="px-4 py-3 font-bold">Status</th>
                <th className="px-4 py-3 font-bold">V</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filtered.map((p) => (
                <tr key={p.key} className="hover:bg-white/[0.03]" data-testid={`page-row-${p.key}`}>
                  <td className="px-4 py-3 font-mono text-xs text-stone-300">{p.key}</td>
                  <td className="px-4 py-3 font-mono text-xs text-stone-400">{p.route}</td>
                  <td className="px-4 py-3 text-stone-200">{p.live?.menu_label || <span className="italic text-stone-600">—</span>}</td>
                  <td className="px-4 py-3 text-stone-200 truncate max-w-[280px]">{p.live?.h1 || <span className="italic text-stone-600">—</span>}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <StatusBadge status={p.status} />
                      {p.draft && <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">draft</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-stone-500">{p.live?.version ?? 0}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setEditing(p)}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-lime-500/10 text-lime-400 hover:bg-lime-500/20 border border-lime-500/30"
                      data-testid={`page-edit-${p.key}`}
                    >
                      Edit config
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-stone-500 italic">Nicio pagină găsită.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="text-xs text-stone-500 space-y-1 pt-2 border-t border-white/10">
          <p>• <b>Menu label</b> ≠ <b>H1</b> ≠ <b>Route</b>. Poți schimba independent orice text fără să afectezi URL-ul.</p>
          <p>• <b>Backward fallback</b>: dacă H1/SEO sunt goale în Page Registry, se folosesc valorile vechi din CMS (`hero.*`) și app_settings.seo.</p>
          <p>• <b>DRAFT nu afectează LIVE</b> — până la Publish, publicul vede versiunea LIVE. Publish creează un snapshot nou în istoric.</p>
          <p>• <b>Feature flag</b> se leagă la `feature_config.enabled` — dacă flag-ul e OFF, publicul primește 404 pe pagină.</p>
        </div>

        {editing && (
          <PageEditor
            page={editing}
            onClose={() => setEditing(null)}
            onSaved={async (updated) => {
              if (updated) setEditing(updated);
              await reloadOne();
            }}
          />
        )}
      </div>
    </AdminLayoutMetronic>
  );
}
