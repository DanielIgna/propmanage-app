// Floating Audit Log button — visible only to super-admins when in preview mode.
// Opens a modal showing audit entries auto-filtered by the preview scope.
import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Shield, X } from "lucide-react";
import { getPreviewScope, ALL_SCOPES } from "../../lib/useAdminScope";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const ScopeChip = ({ scope }) => {
  const tones = {
    general:  "bg-violet-100  text-violet-700  dark:bg-violet-500/15  dark:text-violet-300",
    testing:  "bg-cyan-100    text-cyan-700    dark:bg-cyan-500/15    dark:text-cyan-300",
    frontend: "bg-pink-100    text-pink-700    dark:bg-pink-500/15    dark:text-pink-300",
    backend:  "bg-blue-100    text-blue-700    dark:bg-blue-500/15    dark:text-blue-300",
    security: "bg-red-100     text-red-700     dark:bg-red-500/15     dark:text-red-300",
    ai:       "bg-amber-100   text-amber-700   dark:bg-amber-500/15   dark:text-amber-300",
    ops:      "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${tones[scope] || tones.general}`}>
      {scope}
    </span>
  );
};

export const PreviewAuditButton = ({ scope }) => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [scopeFilter, setScopeFilter] = useState(scope || "");
  const [outcomeFilter, setOutcomeFilter] = useState("");

  const load = useCallback(async (sc, oc) => {
    try {
      const params = new URLSearchParams({ limit: "120" });
      if (sc) params.set("scope", sc);
      if (oc) params.set("outcome", oc);
      const r = await axios.get(`${API}/admin/sub-admins/audit?${params.toString()}`);
      setItems(r.data?.items || []);
      setCounts(r.data?.scope_counts || {});
    } catch {
      // silent (only super can fetch)
    }
  }, []);

  useEffect(() => {
    if (open) load(scopeFilter, outcomeFilter);
  }, [open, scopeFilter, outcomeFilter, load]);

  // Don't render if not in preview
  if (!scope) return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-24 right-6 z-40 px-4 py-3 rounded-full bg-amber-500 hover:bg-amber-600 text-white shadow-2xl flex items-center gap-2 font-medium text-sm animate-bounce"
        title={`Audit Log filtrat pe scope: ${scope}`}
        data-testid="preview-audit-fab"
      >
        <Shield className="w-4 h-4" />
        <span>Audit · {scope}</span>
      </button>

      {open && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <div
            className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-4xl w-full max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            data-testid="preview-audit-modal"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-lg flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-500" /> Audit Log
                <span className="text-[11px] text-slate-500 font-normal">
                  · {items.length} acțiuni · scope: {scopeFilter || "all"}
                  <span className="ml-1 text-amber-600 dark:text-amber-400">(preview)</span>
                </span>
              </h3>
              <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-slate-700" data-testid="close-preview-audit">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5 mb-2">
              <button
                onClick={() => setScopeFilter("")}
                className={`text-[10px] px-2 py-1 rounded ${scopeFilter === "" ? "bg-slate-700 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600"}`}
                data-testid="preview-audit-scope-all"
              >
                Toate ({Object.values(counts).reduce((a, b) => a + b, 0)})
              </button>
              {ALL_SCOPES.map((s) => (
                <button
                  key={s}
                  onClick={() => setScopeFilter(s)}
                  className={`text-[10px] px-2 py-1 rounded uppercase font-bold ${scopeFilter === s ? "bg-indigo-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600"}`}
                  data-testid={`preview-audit-scope-${s}`}
                >
                  {s} ({counts[s] || 0})
                </button>
              ))}
            </div>

            <div className="flex flex-wrap gap-1.5 mb-3">
              {["", "allowed", "denied"].map((o) => (
                <button
                  key={o || "all"}
                  onClick={() => setOutcomeFilter(o)}
                  className={`text-[10px] px-2 py-1 rounded ${outcomeFilter === o ? "bg-violet-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600"}`}
                  data-testid={`preview-audit-outcome-${o || "all"}`}
                >
                  {o || "all outcomes"}
                </button>
              ))}
            </div>

            <table className="w-full text-xs">
              <thead className="text-[10px] text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="text-left pb-2">Timp</th>
                  <th className="text-left pb-2">User</th>
                  <th className="text-left pb-2">Scope</th>
                  <th className="text-left pb-2">Method</th>
                  <th className="text-left pb-2">Path</th>
                  <th className="text-left pb-2">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr><td colSpan={6} className="py-8 text-center text-slate-500" data-testid="preview-audit-empty">
                    Nicio acțiune pe scope <strong>{scopeFilter || "any"}</strong>.
                  </td></tr>
                )}
                {items.map((a, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-1.5 pr-2 text-[10px] text-slate-500 whitespace-nowrap">
                      {new Date(a.ts).toLocaleString("ro-RO", { dateStyle: "short", timeStyle: "medium" })}
                    </td>
                    <td className="py-1.5 pr-2 font-mono">{a.user_email || "—"}</td>
                    <td className="py-1.5 pr-2"><ScopeChip scope={a.scope} /></td>
                    <td className="py-1.5 pr-2 font-mono">{a.method}</td>
                    <td className="py-1.5 pr-2 font-mono text-[10px] truncate max-w-xs" title={a.path}>{a.path}</td>
                    <td className="py-1.5">
                      {a.outcome === "allowed" ? (
                        <span className="text-emerald-600 dark:text-emerald-400">✓</span>
                      ) : (
                        <span className="text-red-600 dark:text-red-400">✗</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
};
