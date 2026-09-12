// Admin Accounts Manager — super-admin can block/unblock, change roles, change passwords
// for ALL admin-level accounts (incl. carlospacu@gmail.com, danieligna1, etc.). Protected: admin@propmanage.io.
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Shield, ChevronLeft, Loader2, AlertTriangle, CheckCircle2, X,
  Lock, Search, Ban, Play, KeyRound, UserCog, ShieldAlert, Filter,
  Users, Crown, Server, Briefcase,
} from "lucide-react";
import { ADMIN_ZONE_ROLES } from "../../config/adminZones";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const ROLE_STYLES = {
  super_admin: "bg-fuchsia-100 dark:bg-fuchsia-500/20 text-fuchsia-700 dark:text-fuchsia-300",
  admin: "bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300",
  marketing_manager: "bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300",
  operator: "bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300",
};

// Code-gated modal — same UX as DemoAccountsPage but more flexible
const ActionModal = ({ title, fields, onClose, onConfirm, busy, error, accent = "violet" }) => {
  const [state, setState] = useState(() => Object.fromEntries(fields.map(f => [f.key, f.initial || ""])));
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="admin-action-modal">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className={`px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-${accent}-500 to-${accent}-600 text-white`}>
          <h3 className="font-bold flex items-center gap-2 text-sm"><Lock className="w-4 h-4" /> {title}</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          {fields.map(f => (
            <div key={f.key}>
              <label className="text-xs uppercase text-slate-500 font-medium mb-1 block">{f.label}</label>
              {f.type === "select" ? (
                <select value={state[f.key]} onChange={e => setState(s => ({ ...s, [f.key]: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
                  data-testid={`field-${f.key}`}>
                  <option value="">— alege —</option>
                  {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input type={f.type === "code" ? "password" : "text"}
                  value={state[f.key]} onChange={e => setState(s => ({ ...s, [f.key]: e.target.value }))}
                  inputMode={f.type === "code" ? "numeric" : "text"}
                  maxLength={f.maxLength}
                  placeholder={f.placeholder || ""}
                  autoFocus={f === fields[0]}
                  className={`w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 ${
                    f.type === "code" ? "text-center text-xl font-mono tracking-[0.5em]" : "text-sm"
                  }`}
                  data-testid={`field-${f.key}`} />
              )}
              {f.hint && <div className="text-[10px] text-slate-500 mt-1">{f.hint}</div>}
            </div>
          ))}
          {error && <div className="text-rose-500 text-xs"><AlertTriangle className="w-3.5 h-3.5 inline mr-1" />{error}</div>}
          <button onClick={() => onConfirm(state)} disabled={busy || fields.some(f => f.required && !state[f.key])}
            className={`w-full py-2.5 rounded-lg bg-gradient-to-r from-${accent}-500 to-${accent}-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2`}
            data-testid="modal-confirm-btn">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Confirmă
          </button>
        </div>
      </div>
    </div>
  );
};

const AdminAccountsPage = () => {
  const [data, setData] = useState({ items: [], allowed_roles: [], allowed_scopes: [], protected_email: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [modal, setModal] = useState(null); // { kind, email, busy, error }

  const load = async () => {
    setLoading(true); setError("");
    try {
      const r = await ax.get("/api/admin/admin-accounts");
      setData(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return data.items.filter(i =>
      (roleFilter === "all" || i.role === roleFilter) &&
      (!q || i.email.toLowerCase().includes(q) || (i.name || "").toLowerCase().includes(q))
    );
  }, [data.items, search, roleFilter]);

  const confirm = async (state) => {
    setModal(m => ({ ...m, busy: true, error: "" }));
    try {
      const body = { email: modal.email, master_code: state.master_code };
      let url;
      if (modal.kind === "block") {
        url = "/api/admin/admin-accounts/block-toggle";
      } else if (modal.kind === "role") {
        url = "/api/admin/admin-accounts/change-role";
        body.new_role = state.new_role;
        body.new_scope = state.new_scope || "";
      } else if (modal.kind === "password") {
        url = "/api/admin/admin-accounts/change-password";
        body.new_password = state.new_password;
      } else if (modal.kind === "zone") {
        url = "/api/admin/admin-zones/assign";
        body.zone_role = state.zone_role;
      }
      const r = await ax.post(url, body);
      setFlash({ kind: "success", message: r.data.message || `Acțiune efectuată pentru ${modal.email}.` });
      setTimeout(() => setFlash(null), 6000);
      setModal(null);
      await load();
    } catch (e) {
      setModal(m => ({ ...m, busy: false, error: e.response?.data?.detail || e.message }));
    }
  };

  const openModal = (kind, email) => setModal({ kind, email, busy: false, error: "" });

  const modalConfig = useMemo(() => {
    if (!modal) return null;
    const base = [{ key: "master_code", label: "Cod master (4 cifre)", type: "code", maxLength: 4, required: true }];
    if (modal.kind === "block") {
      const target = data.items.find(i => i.email === modal.email);
      return { title: `${target?.is_active ? "Blochează" : "Activează"} ${modal.email}`, fields: base, accent: "rose" };
    }
    if (modal.kind === "role") {
      return {
        title: `Schimbă rol pentru ${modal.email}`,
        fields: [
          { key: "new_role", label: "Rol nou", type: "select", options: data.allowed_roles, required: true },
          { key: "new_scope", label: "Scope (opțional)", type: "select", options: data.allowed_scopes },
          ...base,
        ],
        accent: "violet",
      };
    }
    if (modal.kind === "password") {
      return {
        title: `Schimbă parola pentru ${modal.email}`,
        fields: [
          { key: "new_password", label: "Parolă nouă (min 8 chars, litere+cifre)", type: "text", placeholder: "ex: NewPass2026!", required: true,
            hint: "Trimite-o colaboratorului prin canal sigur. Codul master se loghează în audit." },
          ...base,
        ],
        accent: "fuchsia",
      };
    }
    if (modal.kind === "zone") {
      const target = data.items.find(i => i.email === modal.email);
      return {
        title: `Rol de zonă pentru ${modal.email}`,
        fields: [
          { key: "zone_role", label: `Rol de zonă (actual: ${target?.zone_role || "acces complet"})`, type: "select", required: true,
            options: ["none", ...ADMIN_ZONE_ROLES.map(r => r.id)],
            hint: "«none» = elimină rolul → acces complet la ambele zone. Rolurile business_* văd doar zona Business; developer/devops/system_administrator doar Infrastructure." },
          ...base,
        ],
        accent: "cyan",
      };
    }
    return null;
  }, [modal, data]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="admin-accounts-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <ShieldAlert className="w-5 h-5 text-rose-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Admin Accounts Manager</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-400">Super-admin only · cod 0108</span>
      </div>

      <div className="max-w-6xl">
        <div className="mb-5 p-4 rounded-xl bg-gradient-to-r from-rose-50 to-pink-50 dark:from-rose-500/10 dark:to-pink-500/10 border border-rose-200 dark:border-rose-500/30">
          <h2 className="font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2"><Shield className="w-4 h-4 text-rose-500" /> Control total asupra adminilor</h2>
          <p className="text-xs text-slate-600 dark:text-slate-300">
            Vezi toți utilizatorii cu rol admin (inclusiv operatori, marketing manager, conturi demo). Poți <strong>bloca/activa</strong> orice cont, <strong>schimba rolul/scope-ul</strong> sau <strong>seta o parolă nouă</strong> dacă apare ceva suspect.
            Contul <code className="font-mono bg-rose-100 dark:bg-rose-500/20 px-1.5 py-0.5 rounded">{data.protected_email}</code> este protejat (nu poate fi blocat sau demotat, doar parolă schimbată).
          </p>
        </div>

        {flash && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-sm flex items-start gap-2" data-testid="flash">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{flash.message}</span>
            <button onClick={() => setFlash(null)} className="ml-auto"><X className="w-4 h-4" /></button>
          </div>
        )}

        {/* Filters */}
        <div className="mb-4 flex items-center gap-2 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Caută după email sau nume…"
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sm"
              data-testid="search-input" />
          </div>
          <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sm"
            data-testid="role-filter">
            <option value="all">Toate rolurile ({data.items.length})</option>
            {(data.allowed_roles || []).map(r => (
              <option key={r} value={r}>{r} ({data.items.filter(i => i.role === r).length})</option>
            ))}
          </select>
          <span className="text-xs text-slate-500"><Users className="w-3.5 h-3.5 inline mr-1" />Afișate: <strong>{filtered.length}</strong></span>
        </div>

        {loading ? (
          <div className="text-center py-12"><Loader2 className="w-7 h-7 animate-spin mx-auto text-slate-400" /></div>
        ) : error ? (
          <div className="p-3 rounded-lg bg-rose-50 text-rose-700 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>
        ) : (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/50">
                <tr className="text-xs uppercase text-slate-500">
                  <th className="text-left px-4 py-2.5">Cont</th>
                  <th className="text-left px-2 py-2.5">Rol</th>
                  <th className="text-left px-2 py-2.5">Scope</th>
                  <th className="text-left px-2 py-2.5">Status</th>
                  <th className="text-right px-4 py-2.5">Acțiuni</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(i => (
                  <tr key={i.email} className="border-t border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30" data-testid={`admin-row-${i.email.replace(/[@.]/g, '_')}`}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <code className="text-xs font-mono text-slate-900 dark:text-white">{i.email}</code>
                        {i.is_protected && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 flex items-center gap-0.5"><Crown className="w-2.5 h-2.5" /> PROTECT</span>}
                        {i.is_demo_sub_admin && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300">DEMO</span>}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {i.name}
                        {i.last_login_at && <> · login {new Date(i.last_login_at).toLocaleDateString("ro-RO")}</>}
                      </div>
                    </td>
                    <td className="px-2 py-3">
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${ROLE_STYLES[i.role] || "bg-slate-100 text-slate-700"}`}>{i.role}</span>
                      {i.zone_role && (
                        <span className={`block mt-1 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded w-fit ${
                          (i.admin_zones || []).includes("infrastructure") && !(i.admin_zones || []).includes("business")
                            ? "bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300"
                            : "bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300"
                        }`} data-testid={`zone-role-${i.email.replace(/[@.]/g, '_')}`}>
                          {(i.admin_zones || []).includes("business") && !(i.admin_zones || []).includes("infrastructure") ? "🏢 " : "🛠 "}
                          {i.zone_role.replace(/_/g, " ")}
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-3 text-xs text-slate-600 dark:text-slate-300">{i.scope}</td>
                    <td className="px-2 py-3">
                      {i.is_active ? (
                        <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300">ACTIV</span>
                      ) : (
                        <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300">BLOCAT</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        <button onClick={() => openModal("block", i.email)} disabled={i.is_protected}
                          title={i.is_protected ? "Cont protejat — nu poate fi blocat" : (i.is_active ? "Blochează" : "Activează")}
                          className={`p-1.5 rounded-lg text-xs font-medium disabled:opacity-30 disabled:cursor-not-allowed ${
                            i.is_active ? "bg-rose-100 hover:bg-rose-200 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300"
                            : "bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                          }`} data-testid={`block-${i.email.replace(/[@.]/g, '_')}`}>
                          {i.is_active ? <Ban className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                        </button>
                        <button onClick={() => openModal("role", i.email)} disabled={i.is_protected}
                          title={i.is_protected ? "Cont protejat — nu poate fi demotat" : "Schimbă rol"}
                          className="p-1.5 rounded-lg bg-violet-100 hover:bg-violet-200 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 text-xs disabled:opacity-30 disabled:cursor-not-allowed"
                          data-testid={`role-${i.email.replace(/[@.]/g, '_')}`}>
                          <UserCog className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => openModal("zone", i.email)} disabled={i.is_protected}
                          title={i.is_protected ? "Cont protejat" : "Rol de zonă (Business / Infrastructure)"}
                          className="p-1.5 rounded-lg bg-cyan-100 hover:bg-cyan-200 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 text-xs disabled:opacity-30 disabled:cursor-not-allowed"
                          data-testid={`zone-${i.email.replace(/[@.]/g, '_')}`}>
                          <Server className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => openModal("password", i.email)}
                          title="Schimbă parola"
                          className="p-1.5 rounded-lg bg-fuchsia-100 hover:bg-fuchsia-200 dark:bg-fuchsia-500/20 text-fuchsia-700 dark:text-fuchsia-300 text-xs"
                          data-testid={`pw-${i.email.replace(/[@.]/g, '_')}`}>
                          <KeyRound className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan="5" className="text-center py-8 text-sm text-slate-500">Niciun cont nu corespunde filtrului.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-6 p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
          <strong className="text-slate-900 dark:text-white">Acțiuni disponibile:</strong>
          <ul className="mt-2 space-y-1 list-disc pl-5">
            <li><Ban className="w-3 h-3 inline" /> <strong>Blochează / Activează</strong> — flag is_active. Userii blocați nu se pot loga.</li>
            <li><UserCog className="w-3 h-3 inline" /> <strong>Schimbă rol</strong> — selectezi rolul nou ({(data.allowed_roles || []).join(", ")}) și scope-ul opțional.</li>
            <li><Server className="w-3 h-3 inline" /> <strong>Rol de zonă</strong> — restricționează accesul la 🏢 Business sau 🛠 Infrastructure & Development. Fără rol = acces complet. Super-adminii văd mereu ambele zone.</li>
            <li><KeyRound className="w-3 h-3 inline" /> <strong>Schimbă parola</strong> — parolă custom min 8 caractere cu litere + cifre.</li>
            <li>Toate acțiunile cer codul master <strong>0108</strong> și sunt auditate în logs.</li>
            <li>Contul <code>{data.protected_email}</code> nu poate fi blocat sau demotat (doar parolă schimbabilă).</li>
          </ul>
          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800">
            <strong className="text-slate-900 dark:text-white">Pentru conturile demo</strong> (cu badge DEMO), folosește <Link to="/admin/demo-accounts" className="text-violet-500 hover:underline">Demo Accounts Manager</Link> care permite și „Reset la parola implicită".
          </div>
        </div>
      </div>

      {modal && modalConfig && (
        <ActionModal
          title={modalConfig.title}
          fields={modalConfig.fields}
          accent={modalConfig.accent}
          busy={modal.busy}
          error={modal.error}
          onConfirm={confirm}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
};

export default AdminAccountsPage;
