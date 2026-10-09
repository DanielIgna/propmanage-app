// Unified user management — Design System standard (KPI → AI Insights → Filtre → Tabel)
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Search, Download, Edit2, Ban, CheckCircle2, X, UserCheck, Trash2, AlertTriangle, Mail, Phone, Megaphone, MailX, PhoneOff, Users as UsersIcon, UserPlus, Wrench } from "lucide-react";
import { AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { ImpersonateModal } from "./ImpersonateModal";
import { useAuth } from "../../auth";
import { KpiCard, AIInsightCard, DataTable, DSButton, CARD } from "../../design-system";

const EditUserModal = ({ user, onClose, onSaved }) => {
  const [form, setForm] = useState({
    name: user.name || "",
    email: user.email || "",
    role: user.role || "client",
    verified: !!user.verified,
    tier: user.tier || "",
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await axios.patch(`${API}/admin/users/${user.id}`, form);
      onSaved();
      onClose();
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare la salvare");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6" onClick={e => e.stopPropagation()} data-testid="edit-user-modal">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Editare user</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Nume</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="edit-user-name" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Email</label>
            <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="edit-user-email" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Rol</label>
            <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="edit-user-role">
              <option value="client">Client</option>
              <option value="specialist">Specialist</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Tier</label>
            <select value={form.tier} onChange={e => setForm({ ...form, tier: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="edit-user-tier">
              <option value="">— niciun tier —</option>
              <option value="ENTRY">ENTRY</option>
              <option value="VERIFIED">VERIFIED</option>
              <option value="PREMIUM">PREMIUM</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.verified} onChange={e => setForm({ ...form, verified: e.target.checked })} data-testid="edit-user-verified" />
            <span className="text-sm">Verificat ✓</span>
          </label>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <AdminBtn variant="secondary" onClick={onClose}>Anulează</AdminBtn>
          <AdminBtn onClick={save} disabled={saving} data-testid="edit-user-save">{saving ? "Se salvează..." : "Salvează"}</AdminBtn>
        </div>
      </div>
    </div>
  );
};

export const AdminUsers = () => {
  const { user: me } = useAuth();
  const [data, setData] = useState({ items: [], total: 0 });
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState(null);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [emailVerifiedFilter, setEmailVerifiedFilter] = useState("");
  const [phoneVerifiedFilter, setPhoneVerifiedFilter] = useState("");
  const [marketingFilter, setMarketingFilter] = useState("");
  const [skip, setSkip] = useState(0);
  const [editing, setEditing] = useState(null);
  const [impersonating, setImpersonating] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCleanup, setShowCleanup] = useState(false);

  const load = () => {
    setLoading(true);
    const params = { skip, limit: 25 };
    if (q) params.q = q;
    if (role) params.role = role;
    if (emailVerifiedFilter !== "") params.email_verified = emailVerifiedFilter === "yes";
    if (phoneVerifiedFilter !== "") params.phone_verified = phoneVerifiedFilter === "yes";
    if (marketingFilter !== "") params.marketing_consent = marketingFilter === "yes";
    axios.get(`${API}/admin/users`, { params })
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [skip, role, emailVerifiedFilter, phoneVerifiedFilter, marketingFilter]);
  useEffect(() => {
    axios.get(`${API}/admin/bi/overview`).then(r => setStats(r.data)).catch(() => {});
    axios.get(`${API}/admin/insights/rule?module=users`).then(r => setInsights(r.data)).catch(() => {});
  }, []);

  const onSearch = (e) => { e.preventDefault(); setSkip(0); load(); };

  const ban = async (uid, banned) => {
    if (!window.confirm(banned ? "Reactivează acest user?" : "Banează acest user?")) return;
    await axios.post(`${API}/admin/users/${uid}/${banned ? "unban" : "ban"}`);
    load();
  };

  const exportCsv = () => {
    window.open(`${API}/admin/export/users.csv`, "_blank");
  };

  const roleBadge = (r) => <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700">{r}</span>;
  const tierBadge = (t) => t ? (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${t === "VERIFIED" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400" : t === "PREMIUM" ? "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400" : "bg-slate-100 dark:bg-slate-700"}`}>{t}</span>
  ) : null;

  const columns = [
    { key: "name", label: "Nume", render: u => <span className="font-medium">{u.name || "—"}</span> },
    { key: "email", label: "Email", render: u => (
      <div>
        <div className="text-slate-600 dark:text-slate-400">{u.email}</div>
        {u.phone && <div className="text-[10px] text-slate-500 font-mono" data-testid={`user-phone-${u.id}`}>📞 {u.phone}</div>}
      </div>
    ) },
    { key: "role", label: "Rol", render: u => roleBadge(u.role) },
    { key: "tier", label: "Tier", render: u => tierBadge(u.tier) },
    { key: "wallet_balance", label: "Wallet", render: u => <span className="tabular-nums">{Number(u.wallet_balance || 0).toFixed(2)}</span> },
    { key: "_verif", label: "Verificări", sortable: false, render: u => (
      <span className="inline-flex items-center gap-2">
        {u.email_verified ? <Mail className="w-3.5 h-3.5 text-emerald-500" title="Email verificat" /> : <MailX className="w-3.5 h-3.5 text-amber-500" title="Email NEverificat" />}
        {u.phone_verified ? <Phone className="w-3.5 h-3.5 text-emerald-500" title="Telefon verificat" /> : <PhoneOff className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" title="Telefon NEverificat" />}
        {u.marketing_consent ? <Megaphone className="w-3.5 h-3.5 text-emerald-500" title="Acord marketing" /> : <span className="text-slate-300 dark:text-slate-600 text-xs w-3.5 text-center">—</span>}
      </span>
    ) },
    { key: "banned", label: "Status", render: u => (
      u.banned ? <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400">Banned</span>
        : u.verified ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
        : <span className="text-slate-300">—</span>
    ) },
    { key: "_actions", label: "Acțiuni", sortable: false, render: u => (
      <span className="inline-flex items-center gap-2">
        <button onClick={() => setEditing(u)} className="text-blue-600 hover:text-blue-700 dark:text-blue-400" title="Editare" data-testid={`edit-user-${u.id}`}>
          <Edit2 className="w-4 h-4" />
        </button>
        {u.role !== "admin" && u.id !== me?.id && !u.banned && (
          <button onClick={() => setImpersonating(u)} className="text-red-600 hover:text-red-700 dark:text-red-400" title="Intră în contul lui (jurnalizat GDPR)" data-testid={`impersonate-user-${u.id}`}>
            <UserCheck className="w-4 h-4" />
          </button>
        )}
        <button onClick={() => ban(u.id, u.banned)} className={u.banned ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"} title={u.banned ? "Unban" : "Ban"} data-testid={`ban-user-${u.id}`}>
          <Ban className="w-4 h-4" />
        </button>
      </span>
    ) },
  ];

  return (
    <div className="space-y-6" data-testid="admin-users-page">
      {/* 1. KPI Cards standard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={UsersIcon} label="Total useri" value={stats?.total_users ?? "—"} accent="info" testid="users-kpi-total" />
        <KpiCard icon={UserCheck} label="Clienți activi" value={stats?.active_clients ?? "—"} accent="success" testid="users-kpi-clients" />
        <KpiCard icon={Wrench} label="Specialiști activi" value={stats?.active_specialists ?? "—"} accent="ai" testid="users-kpi-specialists" />
        <KpiCard icon={UserPlus} label="Useri noi (30z)" value={stats?.new_users_30d ?? "—"} accent="warning" testid="users-kpi-new" />
      </div>

      {/* 2. AI Insights — obligatoriu după KPI */}
      <AIInsightCard
        bullets={insights?.bullets || []} alerts={insights?.alerts || []}
        recommendations={insights?.recommendations || []}
        loading={!insights} llmModule="users" testid="users-ai-insights"
      />

      {/* 3. Filtre + acțiuni */}
      <div className={`${CARD} p-4`}>
        <div className="flex flex-wrap gap-3 items-center">
          <form onSubmit={onSearch} className="flex-1 min-w-[200px] relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Caută după nume sau email..."
              className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="users-search-input"
            />
          </form>
          <select value={role} onChange={e => { setRole(e.target.value); setSkip(0); }} className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="users-role-filter">
            <option value="">Toate rolurile</option>
            <option value="client">Client</option>
            <option value="specialist">Specialist</option>
            <option value="operator">Operator</option>
            <option value="admin">Admin</option>
          </select>
          <select value={emailVerifiedFilter} onChange={e => { setEmailVerifiedFilter(e.target.value); setSkip(0); }} className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="filter-email-verified" title="Email verificat">
            <option value="">Email: toți</option>
            <option value="yes">✉ Verificat</option>
            <option value="no">✉ Neverificat</option>
          </select>
          <select value={phoneVerifiedFilter} onChange={e => { setPhoneVerifiedFilter(e.target.value); setSkip(0); }} className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="filter-phone-verified" title="Telefon verificat">
            <option value="">Telefon: toți</option>
            <option value="yes">📱 Verificat</option>
            <option value="no">📱 Neverificat</option>
          </select>
          <select value={marketingFilter} onChange={e => { setMarketingFilter(e.target.value); setSkip(0); }} className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="filter-marketing-consent" title="Acord marketing">
            <option value="">Marketing: toți</option>
            <option value="yes">📣 Acceptat</option>
            <option value="no">📣 Refuzat</option>
          </select>
          <DSButton variant="secondary" icon={Download} onClick={exportCsv} data-testid="users-export-csv">CSV</DSButton>
          <DSButton
            variant="danger"
            icon={Trash2}
            onClick={() => setShowCleanup(true)}
            data-testid="users-cleanup-test-btn"
            title="Șterge userii de test (test_*@test.io, beta_*@example.com, etc.)"
          >
            Curăță userii de test
          </DSButton>
        </div>
      </div>

      {/* 4. Tabel standard (DataTable) + paginare server-side */}
      <DataTable
        title="Utilizatori"
        columns={columns}
        rows={data.items}
        emptyTitle="Niciun user găsit"
        emptyHint="Ajustează filtrele sau căutarea."
        testid="users-table"
        headerExtra={<span className="text-xs text-slate-400" data-testid="users-total">Total: {data.total}</span>}
      />
      <div className="flex justify-end gap-2">
        <DSButton variant="secondary" onClick={() => setSkip(Math.max(0, skip - 25))} disabled={skip === 0}>← Anterior</DSButton>
        <DSButton variant="secondary" onClick={() => setSkip(skip + 25)} disabled={skip + 25 >= data.total}>Următor →</DSButton>
      </div>

      {editing && <EditUserModal user={editing} onClose={() => setEditing(null)} onSaved={load} />}
      {impersonating && <ImpersonateModal user={impersonating} onClose={() => setImpersonating(null)} />}
      {showCleanup && <CleanupTestUsersModal onClose={() => setShowCleanup(false)} onCleaned={load} />}
    </div>
  );
};


// ============= CLEANUP TEST USERS MODAL =============
const CleanupTestUsersModal = ({ onClose, onCleaned }) => {
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    axios.get(`${API}/admin/test-users/preview`)
      .then(r => setPreview(r.data))
      .catch(e => setResult({ error: e?.response?.data?.detail || e.message }));
  }, []);

  const doCleanup = async () => {
    if (confirmText !== "STERGE") return;
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/admin/test-users/cleanup?confirm=STERGE`);
      setResult(data);
      setTimeout(() => { onCleaned?.(); }, 800);
    } catch (e) {
      setResult({ error: e?.response?.data?.detail || e.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="cleanup-test-users-modal">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-500/15 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Curăță userii de test</h3>
              <div className="text-xs text-slate-500">Șterge ireversibil conturile create în timpul testelor backend.</div>
            </div>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>

        {result?.deleted_users != null ? (
          <div className="text-sm bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-lg p-4" data-testid="cleanup-success">
            <div className="font-semibold text-emerald-700 dark:text-emerald-400 mb-2">✓ {result.deleted_users} useri șterși</div>
            <div className="text-xs text-slate-600 dark:text-slate-400">Resurse cascade-deleted:</div>
            <ul className="text-xs text-slate-600 dark:text-slate-400 mt-1 space-y-0.5">
              {Object.entries(result.counts || {}).filter(([_, v]) => v > 0).map(([k, v]) => (
                <li key={k}>• <strong>{k}</strong>: {v}</li>
              ))}
            </ul>
            <button onClick={onClose} className="mt-3 w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium">Închide</button>
          </div>
        ) : result?.error ? (
          <div className="text-sm bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg p-3 text-red-700 dark:text-red-400">{result.error}</div>
        ) : preview === null ? (
          <div className="text-center py-6 text-sm text-slate-500">Se încarcă...</div>
        ) : preview.count === 0 ? (
          <div className="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-lg p-4 text-center">
            <div className="text-emerald-700 dark:text-emerald-400 font-semibold mb-1">✓ Niciun user de test găsit</div>
            <div className="text-xs text-slate-500">Baza ta de date e deja curată.</div>
          </div>
        ) : (
          <>
            <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-lg p-3 mb-3">
              <div className="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-1">
                Vor fi șterși <span data-testid="cleanup-count">{preview.count}</span> useri
              </div>
              <div className="text-[11px] text-slate-600 dark:text-slate-400 mb-2">
                Match-uri după pattern-uri test (test_*@test.io, beta_*@example.com, etc.). Conturile demo + admins protejate sunt EXCLUSE automat.
              </div>
              <div className="max-h-40 overflow-y-auto bg-white dark:bg-slate-950/50 rounded p-2 text-[11px] font-mono space-y-0.5">
                {preview.items.slice(0, 30).map(u => (
                  <div key={u.id} className="flex justify-between gap-2 text-slate-700 dark:text-slate-300" data-testid={`cleanup-target-${u.id}`}>
                    <span className="truncate">{u.email}</span>
                    <span className="text-slate-500 shrink-0">{u.role}</span>
                  </div>
                ))}
                {preview.items.length > 30 && <div className="text-slate-500 italic text-center pt-1">... și încă {preview.items.length - 30}</div>}
              </div>
            </div>

            <div className="text-xs text-slate-600 dark:text-slate-400 mb-2">
              Scrie <code className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded font-mono text-red-600 dark:text-red-400">STERGE</code> pentru a confirma:
            </div>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="STERGE"
              autoComplete="off"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-mono"
              data-testid="cleanup-confirm-input"
            />

            <div className="flex gap-2 mt-3">
              <button onClick={onClose} className="flex-1 px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sm">Anulează</button>
              <button
                onClick={doCleanup}
                disabled={busy || confirmText !== "STERGE"}
                className="flex-1 px-3 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-1.5"
                data-testid="cleanup-confirm-btn"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {busy ? "Se șterg..." : `Șterge ${preview.count} useri`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
