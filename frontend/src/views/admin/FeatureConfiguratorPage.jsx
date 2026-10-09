// FeatureConfiguratorPage — Admin gamification control center.
//
// 4 tabs:
//  - Matrix: grid features × (junior/regular/verified/pro) toggleable per role
//  - Pairs: client↔specialist pairs with validation warnings
//  - Quests: CRUD active quests with stats + run-now button
//  - Vouchers: list of issued vouchers (read-only audit)
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Settings2, ChevronLeft, Loader2, RefreshCw, ArrowUpRight,
  Check, X, Plus, Trash2, AlertTriangle, Award, Gift, Activity,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const TIER_ORDER = ["junior", "regular", "verified", "pro"];
const TIER_LABEL = { junior: "Junior", regular: "Regular", verified: "Verified", pro: "Pro" };
const TIER_COL = {
  junior:   "border-stone-500/30",
  regular:  "border-blue-500/30",
  verified: "border-emerald-500/30",
  pro:      "border-violet-500/30",
};

const FeatureConfiguratorPage = () => {
  const [tab, setTab] = useState("matrix");
  const [features, setFeatures] = useState([]);
  const [pairs, setPairs] = useState([]);
  const [pairWarnings, setPairWarnings] = useState([]);
  const [quests, setQuests] = useState([]);
  const [vouchers, setVouchers] = useState([]);
  const [voucherStats, setVoucherStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [filterRole, setFilterRole] = useState("");

  const refresh = async () => {
    const [c, p, w, q, v, vs] = await Promise.all([
      ax.get("/api/admin/feature-configurator/config"),
      ax.get("/api/admin/feature-configurator/pairs"),
      ax.get("/api/admin/feature-configurator/pairs/validate"),
      ax.get("/api/admin/feature-configurator/quests"),
      ax.get("/api/admin/feature-configurator/vouchers"),
      ax.get("/api/admin/feature-configurator/vouchers/stats"),
    ]);
    setFeatures(c.data.features || []);
    setPairs(p.data.items || []);
    setPairWarnings(w.data.warnings || []);
    setQuests(q.data.items || []);
    setVouchers(v.data.items || []);
    setVoucherStats(vs.data || {});
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { await refresh(); } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const updateFeature = async (key, changes) => {
    setBusy(true);
    try {
      await ax.put("/api/admin/feature-configurator/config/feature", { key, ...changes });
      await refresh();
    } finally { setBusy(false); }
  };

  const runQuests = async (dryRun = true) => {
    if (!dryRun && !window.confirm("Rulez evaluare quest-uri? Userii eligibili vor primi vouchere.")) return;
    setBusy(true);
    try {
      const { data } = await ax.post("/api/admin/feature-configurator/quests/run-now", { dry_run: dryRun });
      alert(`${dryRun ? "[DRY RUN] " : ""}Scanați ${data.scanned_users} useri. Vouchere ${dryRun ? "candidate" : "emise"}: ${data.vouchers_issued}.`);
      if (!dryRun) await refresh();
    } finally { setBusy(false); }
  };

  const TABS = [
    { id: "matrix",   label: "Matrice features", icon: Settings2 },
    { id: "pairs",    label: `Perechi (${pairWarnings.length > 0 ? `⚠️ ${pairWarnings.length}` : "OK"})`, icon: ArrowUpRight },
    { id: "quests",   label: "Quest-uri", icon: Award },
    { id: "vouchers", label: "Vouchere", icon: Gift },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="fc-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-pink-500/10 border border-pink-500/30 flex items-center justify-center shrink-0">
            <Settings2 className="w-5 h-5 text-pink-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="fc-title">
              Feature <span className="italic gradient-text">Configurator</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Control 100% asupra ce vede fiecare tier (Junior/Regular/Verified/Pro), perechi Client↔Specialist cu warnings, quest-uri cu recompense în vouchere și audit complet.
            </p>
          </div>
          <button onClick={refresh} className="px-3 py-1.5 text-xs rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-stone-300 inline-flex items-center gap-1.5" data-testid="fc-refresh">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center py-10 text-stone-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
          </div>
        ) : (
          <>
            <div className="flex gap-1 mb-6 border-b border-white/10 overflow-x-auto" data-testid="fc-tabs">
              {TABS.map(t => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`px-3 py-2 text-xs uppercase tracking-wider transition-colors border-b-2 inline-flex items-center gap-1.5 whitespace-nowrap ${
                      tab === t.id ? "border-pink-400 text-white" : "border-transparent text-stone-500 hover:text-white"
                    }`}
                    data-testid={`fc-tab-${t.id}`}
                  >
                    <Icon className="w-3.5 h-3.5" /> {t.label}
                  </button>
                );
              })}
            </div>

            <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6">
              {tab === "matrix"   && <MatrixTab features={features} filterRole={filterRole} setFilterRole={setFilterRole} onUpdate={updateFeature} busy={busy} />}
              {tab === "pairs"    && <PairsTab pairs={pairs} warnings={pairWarnings} features={features} onRefresh={refresh} />}
              {tab === "quests"   && <QuestsTab quests={quests} onRefresh={refresh} onRun={runQuests} busy={busy} />}
              {tab === "vouchers" && <VouchersTab vouchers={vouchers} stats={voucherStats} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ============== MATRIX TAB ==============
const MatrixTab = ({ features, filterRole, setFilterRole, onUpdate, busy }) => {
  const filtered = filterRole ? features.filter(f => f.role === filterRole) : features;
  // Group by category
  const byCat = filtered.reduce((acc, f) => {
    (acc[f.category] = acc[f.category] || []).push(f);
    return acc;
  }, {});

  return (
    <div className="space-y-4" data-testid="fc-matrix">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase tracking-wider text-stone-500">Filtru rol:</span>
        {["", "client", "specialist"].map(r => (
          <button
            key={r || "all"}
            onClick={() => setFilterRole(r)}
            className={`px-2.5 py-1 text-[11px] rounded-lg border ${filterRole === r ? "bg-pink-500/15 border-pink-500/40 text-pink-200" : "bg-white/5 border-white/10 text-stone-300"}`}
            data-testid={`fc-matrix-filter-${r || "all"}`}
          >
            {r === "" ? "Toate" : r === "client" ? "Client" : "Specialist"}
          </button>
        ))}
        <span className="ml-auto text-[10px] text-stone-500">{filtered.length} features</span>
      </div>

      {Object.entries(byCat).map(([cat, list]) => (
        <div key={cat}>
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">{cat}</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs border border-white/10 rounded-lg">
              <thead className="bg-white/[0.04]">
                <tr>
                  <th className="px-3 py-2 text-left text-stone-300">Feature</th>
                  <th className="px-3 py-2 text-center text-stone-300">Rol</th>
                  {TIER_ORDER.map(t => (
                    <th key={t} className={`px-2 py-2 text-center text-stone-300 border-l ${TIER_COL[t]}`}>{TIER_LABEL[t]}</th>
                  ))}
                  <th className="px-3 py-2 text-center text-stone-300">On/Off</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {list.map(f => (
                  <tr key={f.key} className="hover:bg-white/[0.02]" data-testid={`fc-row-${f.key}`}>
                    <td className="px-3 py-2 text-stone-100">
                      <div className="font-medium">{f.label_ro}</div>
                      <div className="text-[10px] font-mono text-stone-500">{f.key}</div>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded-full border ${f.role === "client" ? "bg-blue-500/10 border-blue-500/30 text-blue-300" : "bg-violet-500/10 border-violet-500/30 text-violet-300"}`}>{f.role}</span>
                    </td>
                    {TIER_ORDER.map(t => (
                      <td key={t} className={`px-2 py-2 text-center border-l ${TIER_COL[t]}`}>
                        <input
                          type="radio"
                          name={`tier-${f.key}`}
                          checked={f.tier === t}
                          onChange={() => onUpdate(f.key, { tier: t })}
                          disabled={busy}
                          data-testid={`fc-tier-${f.key}-${t}`}
                        />
                      </td>
                    ))}
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => onUpdate(f.key, { enabled: !(f.enabled !== false) })}
                        disabled={busy}
                        className={`text-[10px] uppercase px-2 py-1 rounded-lg border ${f.enabled !== false ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200" : "bg-stone-500/10 border-stone-500/30 text-stone-400"}`}
                        data-testid={`fc-enabled-${f.key}`}
                      >
                        {f.enabled !== false ? "ON" : "OFF"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
};

// ============== PAIRS TAB ==============
const PairsTab = ({ pairs, warnings, features, onRefresh }) => {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ client_feature: "", specialist_feature: "", note: "" });

  const clientFeatures = features.filter(f => f.role === "client");
  const specFeatures = features.filter(f => f.role === "specialist");

  const submit = async (e) => {
    e.preventDefault();
    if (!form.client_feature || !form.specialist_feature) return;
    await ax.post("/api/admin/feature-configurator/pairs", form);
    setForm({ client_feature: "", specialist_feature: "", note: "" });
    setAdding(false);
    onRefresh();
  };

  const remove = async (id) => {
    if (!window.confirm("Șterg această pereche?")) return;
    await ax.delete(`/api/admin/feature-configurator/pairs/${id}`);
    onRefresh();
  };

  return (
    <div className="space-y-4" data-testid="fc-pairs">
      {warnings.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/30 rounded-xl p-3" data-testid="fc-pairs-warnings">
          <div className="flex items-center gap-1 mb-2">
            <AlertTriangle className="w-4 h-4 text-amber-300" />
            <strong className="text-amber-200 text-sm">{warnings.length} avertizări (non-bloc)</strong>
          </div>
          <ul className="space-y-1 text-xs text-amber-100">
            {warnings.map((w, i) => (
              <li key={i} className="ml-3 list-disc" data-testid={`fc-warn-${i}`}>{w.message}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-stone-400">{pairs.length} perechi definite</span>
        <button onClick={() => setAdding(v => !v)} className="text-xs px-2.5 py-1 rounded-lg bg-pink-500/15 border border-pink-500/40 text-pink-200 hover:bg-pink-500/25 inline-flex items-center gap-1" data-testid="fc-pair-add">
          <Plus className="w-3 h-3" /> {adding ? "Anulează" : "Adaugă pereche"}
        </button>
      </div>

      {adding && (
        <form onSubmit={submit} className="bg-white/[0.02] border border-white/10 rounded-xl p-3 space-y-2" data-testid="fc-pair-form">
          <select value={form.client_feature} onChange={e => setForm({...form, client_feature: e.target.value})} className="w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white" required>
            <option value="">— Feature CLIENT —</option>
            {clientFeatures.map(f => <option key={f.key} value={f.key}>{f.label_ro} ({f.tier})</option>)}
          </select>
          <select value={form.specialist_feature} onChange={e => setForm({...form, specialist_feature: e.target.value})} className="w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white" required>
            <option value="">— Feature SPECIALIST —</option>
            {specFeatures.map(f => <option key={f.key} value={f.key}>{f.label_ro} ({f.tier})</option>)}
          </select>
          <input type="text" value={form.note} onChange={e => setForm({...form, note: e.target.value})} placeholder="Notă (opțional)" className="w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white" />
          <button type="submit" className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-200" data-testid="fc-pair-submit">Salvează</button>
        </form>
      )}

      <div className="divide-y divide-white/5 border border-white/10 rounded-xl">
        {pairs.map(p => {
          const w = warnings.find(x => x.pair_id === p.id);
          return (
            <div key={p.id} className="px-3 py-2 flex items-center gap-2 flex-wrap hover:bg-white/[0.02]" data-testid={`fc-pair-${p.id}`}>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-200 font-mono">{p.client_feature}</span>
              <ArrowUpRight className="w-3 h-3 text-stone-500" />
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-200 font-mono">{p.specialist_feature}</span>
              {p.note && <span className="text-[11px] text-stone-400 italic ml-2">{p.note}</span>}
              {w && <span className="text-[10px] text-amber-300 ml-2">⚠️ {w.severity}</span>}
              <button onClick={() => remove(p.id)} className="ml-auto text-stone-500 hover:text-red-400" data-testid={`fc-pair-del-${p.id}`}><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============== QUESTS TAB ==============
const QuestsTab = ({ quests, onRefresh, onRun, busy }) => {
  const toggleActive = async (q) => {
    await ax.put(`/api/admin/feature-configurator/quests/${q.id}`, { active: !q.active });
    onRefresh();
  };
  return (
    <div className="space-y-3" data-testid="fc-quests">
      <div className="flex items-center justify-between">
        <span className="text-xs text-stone-400">{quests.length} quest-uri definite ({quests.filter(q => q.active).length} active)</span>
        <div className="flex gap-2">
          <button onClick={() => onRun(true)} disabled={busy} className="text-xs px-2.5 py-1 rounded-lg bg-blue-500/15 border border-blue-500/40 text-blue-200 disabled:opacity-50" data-testid="fc-quest-dryrun">Dry-run</button>
          <button onClick={() => onRun(false)} disabled={busy} className="text-xs px-2.5 py-1 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-200 disabled:opacity-50 inline-flex items-center gap-1" data-testid="fc-quest-run"><Activity className="w-3 h-3" /> Rulează acum</button>
        </div>
      </div>

      {quests.map(q => (
        <div key={q.id} className="bg-white/[0.02] border border-white/10 rounded-xl p-3" data-testid={`fc-quest-${q.id}`}>
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="font-mono text-[10px] text-stone-500">{q.code}</span>
                <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded border ${q.applies_to_role === "specialist" ? "bg-violet-500/10 border-violet-500/30 text-violet-300" : "bg-blue-500/10 border-blue-500/30 text-blue-300"}`}>{q.applies_to_role}</span>
                <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300">{q.reward_voucher_pct}% off</span>
                <span className="text-sm font-semibold text-white">{q.title_ro}</span>
              </div>
              <div className="text-xs text-stone-300">{q.description_ro}</div>
              <div className="text-[10px] text-stone-500 mt-1">
                Target: {q.target_count}× {q.target_event} în {q.days_window}z
                {q.min_rating && <span> · rating ≥ {q.min_rating}</span>}
                {" · "}Completați: <strong className="text-emerald-300">{q.stats?.completed || 0}</strong>
                {" · "}În progres: <strong className="text-amber-300">{q.stats?.in_progress || 0}</strong>
              </div>
            </div>
            <button onClick={() => toggleActive(q)} className={`text-[10px] px-2 py-1 rounded-lg border ${q.active ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200" : "bg-stone-500/10 border-stone-500/30 text-stone-400"}`} data-testid={`fc-quest-toggle-${q.id}`}>
              {q.active ? "ACTIV" : "OPRIT"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

// ============== VOUCHERS TAB ==============
const VouchersTab = ({ vouchers, stats }) => (
  <div className="space-y-3" data-testid="fc-vouchers">
    <div className="grid grid-cols-3 gap-3">
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
        <div className="text-[10px] uppercase tracking-wider text-emerald-200">Active</div>
        <div className="text-2xl font-mono text-white mt-1">{stats.active || 0}</div>
      </div>
      <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-3 text-center">
        <div className="text-[10px] uppercase tracking-wider text-blue-200">Folosite</div>
        <div className="text-2xl font-mono text-white mt-1">{stats.used || 0}</div>
      </div>
      <div className="rounded-xl border border-stone-500/30 bg-stone-500/5 p-3 text-center">
        <div className="text-[10px] uppercase tracking-wider text-stone-300">Expirate</div>
        <div className="text-2xl font-mono text-white mt-1">{stats.expired || 0}</div>
      </div>
    </div>
    {vouchers.length === 0 ? (
      <div className="text-center py-8 text-stone-500 text-sm">Niciun voucher emis încă. Rulează evaluarea quest-urilor.</div>
    ) : (
      <div className="divide-y divide-white/5 border border-white/10 rounded-xl">
        {vouchers.map(v => (
          <div key={v.id} className="px-3 py-2 flex items-center gap-2 flex-wrap text-xs hover:bg-white/[0.02]" data-testid={`fc-voucher-${v.id}`}>
            <code className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-200">{v.code}</code>
            <span className="text-emerald-300 font-mono">{v.percent}%</span>
            <span className="text-stone-300">{v.user_email}</span>
            <span className="text-[10px] text-stone-500 italic">{v.reason}</span>
            <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded ml-auto ${v.status === "active" ? "bg-emerald-500/10 text-emerald-200" : v.status === "used" ? "bg-blue-500/10 text-blue-200" : "bg-stone-500/10 text-stone-300"}`}>{v.status}</span>
            <span className="text-[10px] text-stone-500">{new Date(v.issued_at).toLocaleDateString("ro-RO")}</span>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default FeatureConfiguratorPage;
