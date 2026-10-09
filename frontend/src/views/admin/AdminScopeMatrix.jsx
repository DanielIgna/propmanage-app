// Access matrix table: shows what each scope can see (rows = scopes, cols = nav items)
// + "Preview as" buttons that swap the super-admin's view to that scope.
import React, { useState } from "react";
import { Eye, X, Check, Grid3x3 } from "lucide-react";
import { ALL_SCOPES, SCOPE_VISIBILITY, setPreviewScope } from "../../lib/useAdminScope";

// Sync this list with NAV_SECTIONS items in AdminLayoutMetronic. Order = display order.
const NAV_ITEMS = [
  { id: "overview", label: "Dashboard" },
  { id: "ai", label: "AI Investigator" },
  { id: "concierge", label: "Concierge & Security" },
  { id: "demo", label: "Demo Tools" },
  { id: "leads", label: "Demo Leads" },
  { id: "activity", label: "Activitate Live" },
  { id: "users", label: "Toți userii" },
  { id: "verification", label: "Verificare specialiști" },
  { id: "beta_testers", label: "Beta Testers" },
  { id: "projects", label: "Proiecte" },
  { id: "disputes", label: "Dispute & NC" },
  { id: "finance", label: "Finanțe & Escrow" },
  { id: "cms", label: "Texte (CMS)" },
  { id: "emails", label: "Template-uri Email" },
  { id: "zones", label: "Zone Acoperire" },
  { id: "abtests", label: "A/B Tests" },
  { id: "trust", label: "Trust Score Weights" },
  { id: "audit", label: "Audit Log" },
  { id: "settings", label: "Setări Platformă" },
  { id: "settings_control", label: "Control Administrare" },
  { id: "docs_train", label: "Documentație & Training" },
  { id: "qa_copilot", label: "QA Copilot" },
  { id: "ai_control", label: "AI Control Center" },
  { id: "ai_docs", label: "Document Intelligence" },
  { id: "ai_dev_team", label: "AI Dev Team" },
  { id: "ai_security", label: "AI Security Center" },
  { id: "autonomy", label: "Autonomy Engine" },
  { id: "todo_board", label: "ToDo Board" },
  { id: "gdpr", label: "GDPR Pack" },
  { id: "impersonation", label: "Impersonări" },
  { id: "sub_admins", label: "Sub-Admini" },
  { id: "approvals", label: "Aprobări Admin" },
  { id: "architecture_board", label: "Architecture Review" },
  { id: "ai_governance", label: "AI Governance" },
  { id: "ai_pm", label: "AI Product Manager" },
  { id: "feature_configurator", label: "Feature Configurator" },
  { id: "exec_briefing", label: "Exec Briefing" },
  { id: "bug_memory", label: "Bug Memory" },
  { id: "docs", label: "Docs & Training" },
  { id: "qa_playbook", label: "QA Playbook" },
];

const SCOPE_TONE = {
  general:  "bg-violet-100  text-violet-700  dark:bg-violet-500/15  dark:text-violet-300",
  testing:  "bg-cyan-100    text-cyan-700    dark:bg-cyan-500/15    dark:text-cyan-300",
  frontend: "bg-pink-100    text-pink-700    dark:bg-pink-500/15    dark:text-pink-300",
  backend:  "bg-blue-100    text-blue-700    dark:bg-blue-500/15    dark:text-blue-300",
  security: "bg-red-100     text-red-700     dark:bg-red-500/15     dark:text-red-300",
  ai:       "bg-amber-100   text-amber-700   dark:bg-amber-500/15   dark:text-amber-300",
  ops:      "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
};

const canSee = (scope, itemId) => {
  if (scope === "general") return true;
  const allowed = SCOPE_VISIBILITY[scope];
  if (!allowed || allowed === "ALL") return true;
  return allowed.has(itemId);
};

const countVisible = (scope) => {
  if (scope === "general") return NAV_ITEMS.length;
  return NAV_ITEMS.filter((i) => canSee(scope, i.id)).length;
};

export const AdminScopeMatrix = () => {
  const [open, setOpen] = useState(false);

  const startPreview = (scope) => {
    setPreviewScope(scope);
    // Visual feedback before page nav happens automatically
    setTimeout(() => {
      window.location.href = "/admin";
    }, 200);
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-[11px] px-3 py-1.5 rounded-md bg-indigo-500 text-white hover:bg-indigo-600 flex items-center gap-1"
        data-testid="open-scope-matrix"
      >
        <Grid3x3 className="w-3 h-3" />
        Matrice Acces
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-7xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            data-testid="scope-matrix-modal"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-xl flex items-center gap-2">
                  <Grid3x3 className="w-5 h-5 text-indigo-500" />
                  Matrice Acces per Scope
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Vezi ce tab-uri din sidebar are dreptul fiecare scope. Click pe <strong>Preview</strong> ca să intri în pielea acelui admin.
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                data-testid="close-matrix"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Summary chips */}
            <div className="flex gap-2 flex-wrap mb-4">
              {ALL_SCOPES.map((s) => (
                <div
                  key={s}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 ${SCOPE_TONE[s]}`}
                >
                  <span className="font-bold uppercase">{s}</span>
                  <span className="opacity-70">{countVisible(s)} / {NAV_ITEMS.length} tab-uri</span>
                  {s !== "general" && (
                    <button
                      onClick={() => startPreview(s)}
                      className="ml-1 text-[10px] px-2 py-0.5 rounded bg-white/40 hover:bg-white/70 dark:bg-black/30 dark:hover:bg-black/50"
                      data-testid={`preview-${s}`}
                    >
                      <Eye className="w-3 h-3 inline mr-1" />
                      Preview
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Matrix table */}
            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800">
                  <tr>
                    <th className="text-left py-2 px-3 border-b border-slate-200 dark:border-slate-700 font-medium text-slate-600 dark:text-slate-300">
                      Tab / Nav Item
                    </th>
                    {ALL_SCOPES.map((s) => (
                      <th
                        key={s}
                        className={`py-2 px-2 border-b border-slate-200 dark:border-slate-700 text-center uppercase text-[10px] font-bold ${SCOPE_TONE[s]}`}
                      >
                        {s}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {NAV_ITEMS.map((item, idx) => (
                    <tr
                      key={item.id}
                      className={idx % 2 === 0 ? "bg-white dark:bg-slate-900" : "bg-slate-50 dark:bg-slate-800/50"}
                      data-testid={`matrix-row-${item.id}`}
                    >
                      <td className="py-1.5 px-3 border-b border-slate-100 dark:border-slate-800 font-medium">
                        <span className="text-slate-700 dark:text-slate-200">{item.label}</span>
                        <code className="ml-2 text-[10px] text-slate-400 font-mono">{item.id}</code>
                      </td>
                      {ALL_SCOPES.map((s) => {
                        const ok = canSee(s, item.id);
                        return (
                          <td
                            key={s}
                            className="py-1.5 px-2 border-b border-slate-100 dark:border-slate-800 text-center"
                            data-testid={`cell-${s}-${item.id}`}
                          >
                            {ok ? (
                              <Check className="w-3.5 h-3.5 text-emerald-500 inline" />
                            ) : (
                              <X className="w-3.5 h-3.5 text-red-400 inline opacity-50" />
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 text-[11px] text-slate-500 dark:text-slate-400">
              ℹ️ <strong>Cum funcționează Preview</strong>: dacă ești super-admin, click pe <em>Preview</em> îți filtrează
              sidebar-ul ca și cum ai fi acel sub-admin. Acțiunile reale rămân cu drepturile tale (nu te
              limitează backend-ul). Apasă "Ieși din Preview" în topbar ca să revii la super.
            </div>
          </div>
        </div>
      )}
    </>
  );
};
