// Configuration Import / Export (Task 8 · P2).
// Reuses admin_audit_log via config_io backend routes. No new UI framework,
// no new theme — just a safe pane for backup/migration workflows.
import React, { useState } from "react";
import axios from "axios";
import { Download, Upload, Eye, Rocket, ShieldAlert } from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";

const API = process.env.REACT_APP_BACKEND_URL;

const errText = (e) => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d) return JSON.stringify(d);
  return e.message;
};

export default function ConfigIOPage() {
  const [downloading, setDownloading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [bundleText, setBundleText] = useState("");
  const [plan, setPlan] = useState(null);
  const [applied, setApplied] = useState(null);
  const [error, setError] = useState("");

  const downloadExport = async () => {
    setDownloading(true);
    setError("");
    try {
      const { data } = await axios.get(`${API}/api/admin/config/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `propmanage-config-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(errText(e));
    } finally { setDownloading(false); }
  };

  const dryRun = async () => {
    setError("");
    setPlan(null);
    setApplied(null);
    let bundle;
    try {
      bundle = JSON.parse(bundleText);
    } catch {
      setError("JSON invalid — verifică sintaxa.");
      return;
    }
    setImporting(true);
    try {
      const { data } = await axios.post(`${API}/api/admin/config/import`,
                                        { bundle, apply: false });
      setPlan(data.plan);
    } catch (e) {
      setError(errText(e));
    } finally { setImporting(false); }
  };

  const applyImport = async () => {
    if (!window.confirm("Aplici DEFINITIV configurația importată? Acțiunea este auditată.")) return;
    let bundle;
    try { bundle = JSON.parse(bundleText); } catch { setError("JSON invalid"); return; }
    setImporting(true);
    setError("");
    try {
      const { data } = await axios.post(`${API}/api/admin/config/import`,
                                        { bundle, apply: true });
      setApplied(data.applied);
    } catch (e) {
      setError(errText(e));
    } finally { setImporting(false); }
  };

  return (
    <AdminLayoutMetronic title="Config Import/Export" subtitle="Backup + migrare configurație PropManage">
      <div className="p-4 sm:p-8 max-w-4xl mx-auto space-y-6" data-testid="config-io-page">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2 text-white">
            <ShieldAlert className="w-6 h-6 text-[#d4ff3a]" /> Configuration I/O
          </h1>
          <p className="text-sm text-stone-400 mt-1 max-w-2xl">
            Export/import JSON pentru pages, menu, CMS, app settings, feature config
            și design tokens. <b>Nu include</b> useri, parole, subscriptions, secrete
            sau plăți. Import-ul e <b>dry-run implicit</b> — modificările reale se aplică
            doar când confirmi.
          </p>
        </div>

        {/* EXPORT */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-3">
          <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5" /> Export
          </div>
          <p className="text-sm text-stone-300">
            Descarcă un backup JSON al configurației complete. Fișierul se poate
            folosi pentru migrare între medii sau restore după accidente.
          </p>
          <button
            onClick={downloadExport}
            disabled={downloading}
            className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-lime-400 text-black hover:bg-lime-300 disabled:opacity-50"
            data-testid="config-export-btn"
          >
            <Download className="w-4 h-4" /> {downloading ? "Se pregătește..." : "Export configurație"}
          </button>
        </section>

        {/* IMPORT */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-3">
          <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 flex items-center gap-1.5">
            <Upload className="w-3.5 h-3.5" /> Import (dry-run → apply)
          </div>
          <p className="text-sm text-stone-300">
            Lipește un bundle JSON. Rulează întâi <b>Dry-run</b> ca să vezi ce s-ar
            schimba. Apoi <b>Apply</b> execută modificările real (audit trail scris).
          </p>
          <textarea
            value={bundleText}
            onChange={(e) => setBundleText(e.target.value)}
            rows={10}
            placeholder='{"app":"propmanage","schema_version":"1.0","sections":{...}}'
            className="w-full font-mono text-xs px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-stone-200 focus:outline-none focus:border-lime-400/50"
            data-testid="config-import-textarea"
          />
          <div className="flex gap-2">
            <button
              onClick={dryRun}
              disabled={importing || !bundleText.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-50"
              data-testid="config-import-dryrun"
            >
              <Eye className="w-4 h-4" /> Dry-run
            </button>
            <button
              onClick={applyImport}
              disabled={importing || !bundleText.trim() || !plan}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-amber-400 text-black hover:bg-amber-300 disabled:opacity-50"
              data-testid="config-import-apply"
            >
              <Rocket className="w-4 h-4" /> Apply
            </button>
          </div>

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm px-4 py-3" data-testid="config-io-error">
              {error}
            </div>
          )}

          {plan && (
            <div className="rounded-xl border border-lime-500/30 bg-lime-500/10 p-3" data-testid="config-io-plan">
              <div className="text-[11px] uppercase tracking-wider font-bold text-lime-400 mb-2">Plan (dry-run)</div>
              <pre className="text-xs text-stone-200 overflow-x-auto">{JSON.stringify(plan, null, 2)}</pre>
            </div>
          )}
          {applied && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3" data-testid="config-io-applied">
              <div className="text-[11px] uppercase tracking-wider font-bold text-emerald-400 mb-2">Applied</div>
              <pre className="text-xs text-stone-200 overflow-x-auto">{JSON.stringify(applied, null, 2)}</pre>
            </div>
          )}
        </section>

        <div className="text-xs text-stone-500 space-y-1 pt-2 border-t border-white/10">
          <p>• Sensitive fields (password, secret, token, api_key) sunt <b>excluse defensiv</b> din export.</p>
          <p>• Secțiunile permise: pages, pages_versions, site_menu, cms_content, app_settings, feature_config, design_tokens.</p>
          <p>• <code>design_tokens</code> = starea RUNTIME-ACTIVĂ (Design Studio, doc <code>_id:"active"</code>) — restore-ul chiar schimbă tema vizibilă.</p>
          <p>• Rol: strat de portabilitate JSON brut. Snapshot-urile canonice in-DB: Admin Console → Snapshots.</p>
          <p>• <code>pages_versions</code> este read-only istoric — la import va fi <b>skipped</b>.</p>
        </div>
      </div>
    </AdminLayoutMetronic>
  );
}
