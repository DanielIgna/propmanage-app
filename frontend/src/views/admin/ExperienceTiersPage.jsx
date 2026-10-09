// ExperienceTiersPage — Admin management for Progressive Disclosure system.
//
// Lets the founder: see tier distribution, browse users with progress to next
// tier, override manually, lock/unlock, configure thresholds, run promotion job.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  GraduationCap, ChevronLeft, Loader2, Search, X,
  Lock, Unlock, Settings2, ArrowUpRight, Users as UsersIcon,
  CheckCircle2, XCircle, Activity, History,
} from "lucide-react";
import { TIER_ORDER, TIER_LABEL, TIER_COLOR } from "../../lib/experienceTier";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const ExperienceTiersPage = () => {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [history, setHistory] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterRole, setFilterRole] = useState("");
  const [filterTier, setFilterTier] = useState("");
  const [overrideModal, setOverrideModal] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const [s, u, h, c] = await Promise.all([
      ax.get("/api/admin/experience-tiers/stats"),
      ax.get("/api/admin/experience-tiers/users", { params: { limit: 100, role: filterRole || undefined, tier: filterTier || undefined } }),
      ax.get("/api/admin/experience-tiers/history?limit=30"),
      ax.get("/api/admin/experience-tiers/config"),
    ]);
    setStats(s.data);
    setUsers(u.data.items || []);
    setHistory(h.data.items || []);
    setConfig(c.data);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { await refresh(); } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterRole, filterTier]);

  const runPromotionJob = async (dryRun = true) => {
    if (!dryRun && !window.confirm("Rulez promovarea automată acum? Userii eligibili vor fi promovați.")) return;
    setBusy(true);
    try {
      const { data } = await ax.post("/api/admin/experience-tiers/run-promotion-job", { dry_run: dryRun });
      alert(`${dryRun ? "[DRY RUN] " : ""}Scan: ${data.scanned} useri. Promovați: ${data.promoted_count}. Locked: ${data.skipped_locked}.`);
      if (!dryRun) await refresh();
    } finally {
      setBusy(false);
    }
  };

  const saveOverride = async (form) => {
    setBusy(true);
    try {
      await ax.post(`/api/admin/experience-tiers/users/${overrideModal.user_id}/override`, form);
      setOverrideModal(null);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare override.");
    } finally {
      setBusy(false);
    }
  };

  const unlockUser = async (userId) => {
    if (!window.confirm("Deblochez auto-promotion pentru acest user? Va putea fi promovat automat de cron.")) return;
    await ax.post(`/api/admin/experience-tiers/users/${userId}/unlock`);
    await refresh();
  };

  const toggleEnabled = async () => {
    if (!config) return;
    const { data } = await ax.put("/api/admin/experience-tiers/config", { enabled: !config.enabled });
    setConfig(data);
  };

  const TABS = [
    { id: "overview", label: "Overview" },
    { id: "users",    label: "Useri" },
    { id: "history",  label: "Istoric promovări" },
    { id: "config",   label: "Configurare" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="et-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0">
            <GraduationCap className="w-5 h-5 text-emerald-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="et-title">
              Experience <span className="italic gradient-text">Tiers</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Progressive Disclosure system — userii încep cu UI simplu (<strong>Junior</strong>) și deblochează funcții pe măsură ce sunt activi (<strong>Regular → Verified → Pro</strong>). Promovare automată zilnică 03:30.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => runPromotionJob(true)}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded-lg bg-blue-500/15 border border-blue-500/40 text-blue-200 hover:bg-blue-500/25 disabled:opacity-50"
              data-testid="et-dry-run"
            >
              {busy ? "..." : "Dry-run"}
            </button>
            <button
              onClick={() => runPromotionJob(false)}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50 inline-flex items-center gap-1"
              data-testid="et-run-now"
            >
              <Activity className="w-3 h-3" /> Rulează acum
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-10 text-stone-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
          </div>
        ) : (
          <>
            <div className="flex gap-1 mb-6 border-b border-white/10" data-testid="et-tabs">
              {TABS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-2 text-xs uppercase tracking-wider transition-colors border-b-2 ${
                    tab === t.id ? "border-emerald-400 text-white" : "border-transparent text-stone-500 hover:text-white"
                  }`}
                  data-testid={`et-tab-${t.id}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6">
              {tab === "overview" && <OverviewTab stats={stats} config={config} />}
              {tab === "users"    && <UsersTab users={users} filterRole={filterRole} setFilterRole={setFilterRole} filterTier={filterTier} setFilterTier={setFilterTier} onOverride={setOverrideModal} onUnlock={unlockUser} />}
              {tab === "history"  && <HistoryTab history={history} />}
              {tab === "config"   && <ConfigTab config={config} onToggle={toggleEnabled} />}
            </div>
          </>
        )}

        {overrideModal && (
          <OverrideModal
            user={overrideModal}
            onClose={() => setOverrideModal(null)}
            onSubmit={saveOverride}
            busy={busy}
          />
        )}
      </div>
    </div>
  );
};

// =================== Tabs ===================

const TIER_BG = {
  junior:   "bg-stone-500/15 border-stone-500/40 text-stone-200",
  regular:  "bg-blue-500/15 border-blue-500/40 text-blue-200",
  verified: "bg-emerald-500/15 border-emerald-500/40 text-emerald-200",
  pro:      "bg-violet-500/15 border-violet-500/40 text-violet-200",
};

const OverviewTab = ({ stats, config }) => {
  if (!stats) return null;
  const dist = stats.distribution || {};
  return (
    <div className="space-y-6" data-testid="et-overview">
      <div className={`rounded-xl px-4 py-3 text-xs border ${config?.enabled ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200" : "bg-amber-500/10 border-amber-500/30 text-amber-200"}`}>
        {config?.enabled ? "✅ Sistem ACTIV — cron-ul zilnic 03:30 promovează automat userii eligibili." : "⚠️ Sistem DEZACTIVAT — promovarea automată e oprită. Override manual e încă posibil."}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {TIER_ORDER.map(t => {
          const clients = (dist.client || {})[t] || 0;
          const specs = (dist.specialist || {})[t] || 0;
          const total = clients + specs;
          return (
            <div key={t} className={`rounded-xl border p-4 ${TIER_BG[t]}`} data-testid={`et-card-${t}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider">{TIER_LABEL[t]}</span>
                <span className="text-2xl font-mono text-white">{total}</span>
              </div>
              <div className="text-[10px] mt-2 space-y-0.5">
                <div>Clienți: <strong>{clients}</strong></div>
                <div>Specialiști: <strong>{specs}</strong></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-2">Totaluri</div>
          <div className="text-sm">Clienți: <strong className="text-blue-300">{stats.totals_per_role?.client ?? 0}</strong></div>
          <div className="text-sm">Specialiști: <strong className="text-violet-300">{stats.totals_per_role?.specialist ?? 0}</strong></div>
          <div className="text-sm">Blocați (locked): <strong className="text-amber-300">{stats.locked_count ?? 0}</strong></div>
        </div>
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-2">Features per tier</div>
          {TIER_ORDER.map(t => (
            <details key={t} className="text-xs mt-1">
              <summary className={`cursor-pointer ${TIER_COLOR[t]} inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] uppercase`}>
                {TIER_LABEL[t]}
              </summary>
              <ul className="ml-3 mt-1 list-disc text-stone-400 text-[11px]">
                {(stats.features_per_tier?.[t] || []).map(f => <li key={f}>{f}</li>)}
              </ul>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
};

const UsersTab = ({ users, filterRole, setFilterRole, filterTier, setFilterTier, onOverride, onUnlock }) => {
  const [q, setQ] = useState("");
  const filtered = q ? users.filter(u => (u.email || "").toLowerCase().includes(q.toLowerCase())) : users;
  return (
    <div data-testid="et-users-tab">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Caută după email..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-[#0a0a0b] border border-white/10 text-white placeholder:text-stone-500 focus:outline-none focus:border-white/30"
            data-testid="et-users-search"
          />
        </div>
        <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)} className="text-xs px-2 py-2 rounded-lg bg-[#0a0a0b] border border-white/10 text-white" data-testid="et-users-role">
          <option value="">Toate rolurile</option>
          <option value="client">Clienți</option>
          <option value="specialist">Specialiști</option>
        </select>
        <select value={filterTier} onChange={(e) => setFilterTier(e.target.value)} className="text-xs px-2 py-2 rounded-lg bg-[#0a0a0b] border border-white/10 text-white" data-testid="et-users-tier">
          <option value="">Toate tier-urile</option>
          {TIER_ORDER.map(t => <option key={t} value={t}>{TIER_LABEL[t]}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-8 text-stone-500 text-sm">Niciun user în lista filtrată.</div>
      ) : (
        <div className="divide-y divide-white/5 border border-white/10 rounded-xl overflow-hidden">
          {filtered.map(u => (
            <div key={u.user_id} className="px-3 py-2.5 hover:bg-white/[0.02]" data-testid={`et-user-${u.user_id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded-full border ${TIER_BG[u.current_tier]}`}>{TIER_LABEL[u.current_tier]}</span>
                {u.locked && (
                  <span className="text-[10px] uppercase px-1.5 py-0.5 rounded-full border bg-amber-500/10 border-amber-500/30 text-amber-300 inline-flex items-center gap-1">
                    <Lock className="w-2.5 h-2.5" /> Locked
                  </span>
                )}
                <span className="text-sm text-white">{u.email}</span>
                <span className="text-[10px] text-stone-500">· {u.role}</span>
                {u.eligible_for && (
                  <span className="text-[10px] text-emerald-300 inline-flex items-center gap-0.5">
                    <ArrowUpRight className="w-3 h-3" /> Eligibil pentru {TIER_LABEL[u.eligible_for]}
                  </span>
                )}
                <span className="ml-auto text-[10px] text-stone-500">{u.days_active}z · {u.completed_actions} acțiuni · ⭐ {u.rating?.toFixed?.(1) || 0}</span>
                <button
                  onClick={() => onOverride(u)}
                  className="text-[10px] px-2 py-1 rounded-lg bg-violet-500/10 border border-violet-500/30 text-violet-200 hover:bg-violet-500/20"
                  data-testid={`et-override-${u.user_id}`}
                >
                  Override
                </button>
                {u.locked && (
                  <button
                    onClick={() => onUnlock(u.user_id)}
                    className="text-[10px] px-2 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 hover:bg-amber-500/20 inline-flex items-center gap-1"
                    data-testid={`et-unlock-${u.user_id}`}
                  >
                    <Unlock className="w-2.5 h-2.5" /> Unlock
                  </button>
                )}
              </div>
              {u.requirements && u.requirements.length > 0 && (
                <div className="ml-1 mt-1 flex flex-wrap gap-1 text-[10px]">
                  {u.requirements.map((r, i) => (
                    <span key={i} className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded ${r.satisfied ? "text-emerald-300 bg-emerald-500/5" : "text-stone-500 bg-white/5"}`}>
                      {r.satisfied ? <CheckCircle2 className="w-2.5 h-2.5" /> : <XCircle className="w-2.5 h-2.5" />}
                      {r.name}: {String(r.current)}/{String(r.needed)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const HistoryTab = ({ history }) => (
  <div className="space-y-1" data-testid="et-history-tab">
    {history.length === 0 ? (
      <div className="text-center py-8 text-stone-500 text-sm">Niciun istoric promovări încă.</div>
    ) : (
      history.map((h, i) => (
        <div key={i} className="bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center gap-2 flex-wrap" data-testid={`et-history-${i}`}>
          <History className="w-3 h-3 text-stone-500 shrink-0" />
          <span className="text-stone-300">{h.user_email}</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${TIER_BG[h.from] || TIER_BG.junior}`}>{TIER_LABEL[h.from]}</span>
          <ArrowUpRight className="w-3 h-3 text-stone-500" />
          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${TIER_BG[h.to] || TIER_BG.junior}`}>{TIER_LABEL[h.to]}</span>
          <span className="text-[10px] text-stone-500 italic">{h.reason}</span>
          <span className="ml-auto text-[10px] text-stone-500">{h.by_email} · {new Date(h.at).toLocaleString("ro-RO")}</span>
        </div>
      ))
    )}
  </div>
);

const ConfigTab = ({ config, onToggle }) => {
  if (!config) return null;
  const c = config.criteria || {};
  return (
    <div className="space-y-4" data-testid="et-config-tab">
      <div className="bg-violet-500/5 border border-violet-500/30 rounded-xl p-4 text-xs text-violet-100">
        <strong className="block mb-1 text-violet-200">Criteriile actuale</strong>
        Pentru a modifica criteriile, foloseste PUT /api/admin/experience-tiers/config (sau cere agentului). Praguri prea relaxate = useri promovați prea repede (UI complex pt începători). Praguri prea stricte = niciun user nu avansează.
      </div>

      <div className="flex items-center justify-between bg-white/[0.02] border border-white/10 rounded-xl p-4">
        <div>
          <div className="text-sm font-semibold text-white">Cron promovare automată</div>
          <div className="text-[11px] text-stone-500">Rulează zilnic 03:30 (Europe/Bucharest). Userii locked sunt sărit.</div>
        </div>
        <button
          onClick={onToggle}
          className={`px-3 py-1.5 text-xs rounded-lg border ${config.enabled ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200" : "bg-stone-500/10 border-stone-500/30 text-stone-300"}`}
          data-testid="et-toggle-enabled"
        >
          {config.enabled ? "Activ" : "Dezactivat"}
        </button>
      </div>

      {Object.entries(c).map(([transition, crit]) => (
        <div key={transition} className="bg-white/[0.02] border border-white/10 rounded-xl p-4" data-testid={`et-crit-${transition}`}>
          <div className="text-xs font-semibold text-emerald-200 uppercase mb-2 flex items-center gap-1">
            <Settings2 className="w-3 h-3" /> {transition.replace(/_/g, " ")}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
            {Object.entries(crit).map(([k, v]) => (
              <div key={k} className="bg-black/30 rounded px-2 py-1.5">
                <div className="text-stone-500">{k}</div>
                <div className="text-white font-mono">{String(v)}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const OverrideModal = ({ user, onClose, onSubmit, busy }) => {
  const [tier, setTier] = useState(user.current_tier);
  const [reason, setReason] = useState("");
  const [lock, setLock] = useState(true);

  const submit = (e) => {
    e.preventDefault();
    if (!tier) return;
    onSubmit({ tier, reason: reason.trim() || "admin_manual_override", lock });
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="et-override-modal">
      <div className="bg-[#0e0e10] border border-white/10 rounded-2xl max-w-md w-full p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Override tier</h3>
            <p className="text-xs text-stone-400 mt-1">{user.email} · curent: <strong>{TIER_LABEL[user.current_tier]}</strong></p>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-white" data-testid="et-override-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Nou tier *</label>
            <select value={tier} onChange={(e) => setTier(e.target.value)} className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white" data-testid="et-override-tier">
              {TIER_ORDER.map(t => <option key={t} value={t}>{TIER_LABEL[t]}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Motiv (audit log)</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="ex: VIP partner, beta tester, escalation request"
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600"
              data-testid="et-override-reason"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 text-xs text-stone-300">
              <input type="checkbox" checked={lock} onChange={(e) => setLock(e.target.checked)} data-testid="et-override-lock" />
              Blochează auto-promovări viitoare (recomandat pentru override-uri manuale)
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 text-xs rounded-lg bg-white/5 border border-white/10 text-stone-300 hover:bg-white/10">Anulează</button>
            <button type="submit" disabled={busy} className="px-4 py-2 text-xs rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50 inline-flex items-center gap-1.5" data-testid="et-override-submit">
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowUpRight className="w-3.5 h-3.5" />}
              Aplică override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ExperienceTiersPage;
