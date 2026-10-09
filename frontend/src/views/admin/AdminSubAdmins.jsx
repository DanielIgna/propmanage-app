// Sub-Admins management page (super-admin only).
// Lists all admins, lets super create new ones, edit scope/seniority,
// reset password, and deactivate.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Users, Plus, KeyRound, UserX, Pencil, Copy, Shield } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import { AdminScopeMatrix } from "./AdminScopeMatrix";
import { AdminProductivity } from "./AdminProductivity";
import { ALL_SCOPES, getPreviewScope } from "../../lib/useAdminScope";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;
const SCOPES = ["general", "testing", "frontend", "backend", "security", "ai", "ops"];
const SENIORITY = ["junior", "senior"];

const ScopeBadge = ({ scope }) => {
  const tones = {
    general: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
    testing: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300",
    frontend: "bg-pink-100 text-pink-700 dark:bg-pink-500/15 dark:text-pink-300",
    backend: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    security: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
    ai: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
    ops: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${tones[scope] || tones.general}`}>
      {scope}
    </span>
  );
};

const CreateForm = ({ onCreated, onClose }) => {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [scope, setScope] = useState("frontend");
  const [seniority, setSeniority] = useState("junior");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const body = { email, name, admin_scope: scope, admin_seniority: seniority };
      if (password) body.password = password;
      const r = await axios.post(`${API}/admin/sub-admins`, body);
      setResult(r.data);
      onCreated?.();
    } catch (err) {
      alert(err.response?.data?.detail || "Eroare la creare");
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    return (
      <div className="space-y-3" data-testid="sub-admin-created">
        <div className="rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 p-4">
          <div className="font-bold text-emerald-700 dark:text-emerald-300 mb-2">✅ Sub-admin creat cu succes</div>
          <div className="space-y-1 text-sm">
            <div><span className="text-slate-500">Email:</span> <code className="font-mono">{result.email}</code></div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Parolă inițială:</span>
              <code className="font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">{result.initial_password}</code>
              <button
                onClick={() => navigator.clipboard?.writeText(result.initial_password)}
                className="text-xs px-2 py-1 rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300"
                data-testid="copy-pwd"
              >
                <Copy className="w-3 h-3" />
              </button>
            </div>
            <div><ScopeBadge scope={result.admin_scope} /> · {result.admin_seniority}</div>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 italic">
            ⚠️ Parola se afișează O SINGURĂ DATĂ. Comunic-o direct utilizatorului.
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-full py-2.5 rounded-lg bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 text-sm font-medium"
          data-testid="close-create-modal"
        >
          Închide
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3" data-testid="sub-admin-create-form">
      <div>
        <label className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
          placeholder="ex: design.admin@propmanage.io"
          data-testid="sub-admin-email"
        />
      </div>
      <div>
        <label className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Nume</label>
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
          placeholder="ex: Maria Designer"
          data-testid="sub-admin-name"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Scope</label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
            data-testid="sub-admin-scope"
          >
            {SCOPES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Seniority</label>
          <select
            value={seniority}
            onChange={(e) => setSeniority(e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
            data-testid="sub-admin-seniority"
          >
            {SENIORITY.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Parolă (opțional · lăsa gol pentru auto-generare)</label>
        <input
          type="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm font-mono"
          placeholder="(auto-generated)"
          data-testid="sub-admin-password"
        />
      </div>
      <div className="flex gap-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 py-2.5 rounded-lg bg-slate-200 dark:bg-slate-700 text-sm font-medium"
          data-testid="cancel-create"
        >
          Anulează
        </button>
        <button
          type="submit"
          disabled={busy}
          className="flex-1 py-2.5 rounded-lg bg-violet-500 text-white text-sm font-medium hover:bg-violet-600 disabled:opacity-50"
          data-testid="submit-create"
        >
          {busy ? "Creez…" : "Creează sub-admin"}
        </button>
      </div>
    </form>
  );
};

export const AdminSubAdmins = () => {
  const [items, setItems] = useState([]);
  const [auditItems, setAuditItems] = useState([]);
  const [auditCounts, setAuditCounts] = useState({});
  const [auditScopeFilter, setAuditScopeFilter] = useState(() => getPreviewScope() || "");
  const [auditOutcomeFilter, setAuditOutcomeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/sub-admins`);
      setItems(r.data?.items || []);
    } catch {
      // silent — 403 or network error
    } finally {
      setLoading(false);
    }
  };
  const loadAudit = async (scope = auditScopeFilter, outcome = auditOutcomeFilter) => {
    try {
      const params = new URLSearchParams({ limit: "120" });
      if (scope) params.set("scope", scope);
      if (outcome) params.set("outcome", outcome);
      const r = await axios.get(`${API}/admin/sub-admins/audit?${params.toString()}`);
      setAuditItems(r.data?.items || []);
      setAuditCounts(r.data?.scope_counts || {});
    } catch {
      // silent
    }
  };

  useEffect(() => { load(); }, []);

  const handleReset = async (id, email) => {
    if (!confirm(`Resetez parola pentru ${email}?`)) return;
    try {
      const r = await axios.post(`${API}/admin/sub-admins/${id}/reset-password`);
      alert(`Parolă nouă: ${r.data.new_password}\n\nComunic-o direct utilizatorului — nu se mai poate afișa.`);
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    }
  };
  const handleDeactivate = async (id, email) => {
    if (!confirm(`Dezactivez contul ${email}? (poate fi reactivat ulterior prin PATCH)`)) return;
    try {
      await axios.delete(`${API}/admin/sub-admins/${id}`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    }
  };
  const handleEditScope = async (item) => {
    const newScope = prompt(`Scope nou pentru ${item.email} (general/testing/frontend/backend/security/ai/ops):`, item.admin_scope);
    if (!newScope || newScope === item.admin_scope) return;
    try {
      await axios.patch(`${API}/admin/sub-admins/${item.id}`, { admin_scope: newScope });
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare");
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-sub-admins-page">
      <AdminProductivity />
      <AdminCard
        testid="sub-admins-list"
        title={
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-violet-500" />
            <span>Sub-Admini & Acces Scoped</span>
            <span className="text-[10px] text-slate-500 font-normal">({items.length})</span>
          </div>
        }
        action={
          <div className="flex gap-2">
            <AdminScopeMatrix />
            <button
              onClick={() => { setAuditOpen(true); loadAudit(auditScopeFilter, auditOutcomeFilter); }}
              className="text-[11px] px-3 py-1.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 flex items-center gap-1"
              data-testid="audit-toggle"
            >
              <Shield className="w-3 h-3" />
              Audit Log
              {getPreviewScope() && (
                <span className="text-[9px] font-bold uppercase ml-1 px-1.5 py-0.5 rounded bg-amber-200 dark:bg-amber-500/30 text-amber-800 dark:text-amber-200">
                  {getPreviewScope()}
                </span>
              )}
            </button>
            <button
              onClick={() => setCreating(true)}
              className="text-[11px] px-3 py-1.5 rounded-md bg-violet-500 text-white hover:bg-violet-600 flex items-center gap-1"
              data-testid="open-create-form"
            >
              <Plus className="w-3 h-3" />
              Sub-admin nou
            </button>
          </div>
        }
      >
        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500">Se încarcă…</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">
            Nu ești super-admin sau nu există conturi.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-500 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                  <th className="py-2 pr-3">Email</th>
                  <th className="py-2 pr-3">Nume</th>
                  <th className="py-2 pr-3">Scope</th>
                  <th className="py-2 pr-3">Seniority</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Demo?</th>
                  <th className="py-2 text-right">Acțiuni</th>
                </tr>
              </thead>
              <tbody>
                {items.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100 dark:border-slate-800" data-testid={`sub-admin-row-${u.id}`}>
                    <td className="py-3 pr-3 font-mono text-xs">{u.email}</td>
                    <td className="py-3 pr-3">{u.name}</td>
                    <td className="py-3 pr-3"><ScopeBadge scope={u.admin_scope} /></td>
                    <td className="py-3 pr-3 text-xs">{u.admin_seniority}</td>
                    <td className="py-3 pr-3">
                      {u.is_active ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">ACTIV</span>
                      ) : (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300">INACTIV</span>
                      )}
                    </td>
                    <td className="py-3 pr-3 text-xs">{u.is_demo_sub_admin ? "Demo" : "—"}</td>
                    <td className="py-3 text-right space-x-1">
                      <button onClick={() => handleEditScope(u)} className="text-[11px] px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200" data-testid={`edit-${u.id}`} title="Editează scope">
                        <Pencil className="w-3 h-3 inline" />
                      </button>
                      <button onClick={() => handleReset(u.id, u.email)} className="text-[11px] px-2 py-1 rounded bg-amber-100 dark:bg-amber-500/15 hover:bg-amber-200 text-amber-700 dark:text-amber-300" data-testid={`reset-${u.id}`} title="Reset parolă">
                        <KeyRound className="w-3 h-3 inline" />
                      </button>
                      {u.is_active && (
                        <button onClick={() => handleDeactivate(u.id, u.email)} className="text-[11px] px-2 py-1 rounded bg-red-100 dark:bg-red-500/15 hover:bg-red-200 text-red-700 dark:text-red-300" data-testid={`deactivate-${u.id}`} title="Dezactivează">
                          <UserX className="w-3 h-3 inline" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminCard>

      {creating && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setCreating(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()} data-testid="create-modal">
            <h3 className="font-serif text-lg mb-4">Sub-admin nou</h3>
            <CreateForm onCreated={load} onClose={() => setCreating(false)} />
          </div>
        </div>
      )}

      {auditOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setAuditOpen(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-4xl w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="audit-modal">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-lg flex items-center gap-2">
                <Shield className="w-4 h-4" /> Audit Log
                <span className="text-[11px] text-slate-500 font-normal">
                  · {auditItems.length} acțiuni
                  {auditScopeFilter && ` · filter: ${auditScopeFilter}`}
                  {getPreviewScope() && auditScopeFilter === getPreviewScope() && (
                    <span className="ml-1 text-amber-600 dark:text-amber-400">(auto din preview)</span>
                  )}
                </span>
              </h3>
              <button onClick={() => setAuditOpen(false)} className="text-slate-500 hover:text-slate-700" data-testid="close-audit-x">✕</button>
            </div>

            {/* Scope filter chips */}
            <div className="flex flex-wrap gap-1.5 mb-2">
              <button
                onClick={() => { setAuditScopeFilter(""); loadAudit("", auditOutcomeFilter); }}
                className={`text-[10px] px-2 py-1 rounded ${auditScopeFilter === "" ? "bg-slate-700 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"}`}
                data-testid="audit-scope-all"
              >
                Toate ({Object.values(auditCounts).reduce((a, b) => a + b, 0)})
              </button>
              {ALL_SCOPES.map((s) => (
                <button
                  key={s}
                  onClick={() => { setAuditScopeFilter(s); loadAudit(s, auditOutcomeFilter); }}
                  className={`text-[10px] px-2 py-1 rounded uppercase font-bold ${auditScopeFilter === s ? "bg-indigo-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"}`}
                  data-testid={`audit-scope-${s}`}
                >
                  {s} ({auditCounts[s] || 0})
                </button>
              ))}
            </div>

            {/* Outcome filter chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {["", "allowed", "denied"].map((o) => (
                <button
                  key={o || "all"}
                  onClick={() => { setAuditOutcomeFilter(o); loadAudit(auditScopeFilter, o); }}
                  className={`text-[10px] px-2 py-1 rounded ${auditOutcomeFilter === o ? "bg-violet-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"}`}
                  data-testid={`audit-outcome-${o || "all"}`}
                >
                  {o || "all outcomes"}
                </button>
              ))}
            </div>

            <table className="w-full text-xs">
              <thead className="text-[10px] text-slate-500 uppercase tracking-wider sticky top-0 bg-white dark:bg-slate-900">
                <tr><th className="text-left pb-2">Timp</th><th className="text-left pb-2">User</th><th className="text-left pb-2">Scope</th><th className="text-left pb-2">Method</th><th className="text-left pb-2">Path</th><th className="text-left pb-2">Outcome</th></tr>
              </thead>
              <tbody>
                {auditItems.length === 0 && (
                  <tr><td colSpan={6} className="py-8 text-center text-slate-500" data-testid="audit-empty">Nicio acțiune pentru filtrele alese.</td></tr>
                )}
                {auditItems.map((a, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800" data-testid={`audit-row-${i}`}>
                    <td className="py-1.5 pr-2 text-[10px] text-slate-500 whitespace-nowrap">{new Date(a.ts).toLocaleString("ro-RO", { dateStyle: "short", timeStyle: "medium" })}</td>
                    <td className="py-1.5 pr-2 font-mono">{a.user_email || "—"}</td>
                    <td className="py-1.5 pr-2"><ScopeBadge scope={a.scope} /></td>
                    <td className="py-1.5 pr-2 font-mono">{a.method}</td>
                    <td className="py-1.5 pr-2 font-mono text-[10px] truncate max-w-xs" title={a.path}>{a.path}</td>
                    <td className="py-1.5">
                      {a.outcome === "allowed" ? (
                        <span className="text-emerald-600 dark:text-emerald-400">✓ allowed</span>
                      ) : (
                        <span className="text-red-600 dark:text-red-400">✗ denied</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={() => setAuditOpen(false)} className="mt-4 w-full py-2 rounded-lg bg-slate-200 dark:bg-slate-700 text-sm" data-testid="close-audit">Închide</button>
          </div>
        </div>
      )}
    </div>
  );
};
