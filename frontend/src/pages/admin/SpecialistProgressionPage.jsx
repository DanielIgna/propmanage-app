// Sprint A — Specialist Progression Admin Panel
// Manages: dynamic fees, tier promotion thresholds, policy docs, manual promotion run
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  DollarSign, Trophy, Scale, Play, Plus, Trash2, Loader2,
  AlertTriangle, Save, FileText, RefreshCcw, CheckCircle2, X,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const POLICY_SLUGS = [
  { slug: "terms", title: "Termeni și Condiții" },
  { slug: "privacy", title: "Politica de Confidențialitate" },
  { slug: "reviews_policy", title: "Politica Recenzii" },
  { slug: "suspensions_policy", title: "Politica Suspendări" },
  { slug: "ranking_policy", title: "Politica Ranking Specialiști" },
];

export const SpecialistProgressionPage = () => {
  const [tab, setTab] = useState("fees");

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="specialist-progression-page">
      <h1 className="font-serif text-3xl mb-1">Progresie Specialiști — Sprint A</h1>
      <p className="text-sm text-stone-400 mb-6">Configurare fee-uri dinamice, praguri tier, politici platformă. Toate modificările sunt versionate.</p>

      <div className="flex gap-2 mb-6 border-b border-white/10">
        {[
          { id: "fees", label: "Fee-uri dinamice", icon: DollarSign },
          { id: "tiers", label: "Praguri Tier", icon: Trophy },
          { id: "policies", label: "Politici", icon: FileText },
          { id: "runs", label: "Istoric promovări", icon: RefreshCcw },
        ].map(t => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2.5 text-sm font-medium flex items-center gap-2 border-b-2 transition ${tab === t.id ? "border-[#d4ff3a] text-[#d4ff3a]" : "border-transparent text-stone-400 hover:text-stone-200"}`} data-testid={`sp-tab-${t.id}`}>
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === "fees" && <FeesTab />}
      {tab === "tiers" && <TierRulesTab />}
      {tab === "policies" && <PoliciesTab />}
      {tab === "runs" && <PromotionRunsTab />}
    </div>
  );
};


const FeesTab = () => {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => axios.get(`${API}/api/admin/fee-config`).then(r => setCfg(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true); setMsg("");
    try {
      await axios.put(`${API}/api/admin/fee-config`, cfg);
      setMsg("Salvat. Modificările sunt active imediat.");
    } catch (e) {
      setMsg(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  if (!cfg) return <Loader2 className="w-6 h-6 animate-spin text-[#d4ff3a]" />;

  const updateRule = (idx, key, val) => {
    const newRules = [...cfg.rules];
    newRules[idx] = { ...newRules[idx], [key]: val };
    setCfg({ ...cfg, rules: newRules });
  };
  const addRule = () => setCfg({ ...cfg, rules: [...(cfg.rules || []), { base_fee_ron: 5, priority_fee_ron: 0, active: true }] });
  const removeRule = (idx) => setCfg({ ...cfg, rules: cfg.rules.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass rounded-2xl p-4">
          <label className="text-xs uppercase text-stone-500 mb-1 block">Fee minim (RON)</label>
          <input type="number" min="1" value={cfg.min_fee_ron} onChange={e => setCfg({ ...cfg, min_fee_ron: parseFloat(e.target.value) || 5 })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid="fee-min" />
        </div>
        <div className="glass rounded-2xl p-4">
          <label className="text-xs uppercase text-stone-500 mb-1 block">Fee maxim (RON)</label>
          <input type="number" min="5" value={cfg.max_fee_ron} onChange={e => setCfg({ ...cfg, max_fee_ron: parseFloat(e.target.value) || 50 })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid="fee-max" />
        </div>
        <div className="glass rounded-2xl p-4">
          <label className="text-xs uppercase text-stone-500 mb-1 block">Top vizibil (count)</label>
          <input type="number" min="1" max="10" value={cfg.top_visible_count} onChange={e => setCfg({ ...cfg, top_visible_count: parseInt(e.target.value) || 3 })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid="fee-top-visible" />
        </div>
      </div>

      <label className="flex items-center gap-2 cursor-pointer" data-testid="fee-multi-offer-wrap">
        <input type="checkbox" checked={cfg.multi_offer_enabled} onChange={e => setCfg({ ...cfg, multi_offer_enabled: e.target.checked })} className="w-4 h-4 accent-[#d4ff3a]" data-testid="fee-multi-offer" />
        <span className="text-sm text-stone-300">Activează mod "multi-oferte" (legacy "accept" rămâne pentru cereri vechi)</span>
      </label>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-serif text-xl">Reguli fee per categorie/zonă</h3>
          <button onClick={addRule} className="px-3 py-1.5 rounded-lg text-xs bg-white/5 hover:bg-white/10 flex items-center gap-1.5" data-testid="fee-add-rule">
            <Plus className="w-3.5 h-3.5" /> Adaugă regulă
          </button>
        </div>
        <div className="space-y-2">
          {(cfg.rules || []).length === 0 && <div className="text-xs text-stone-500 italic">Nicio regulă. Se folosește fee_min global.</div>}
          {(cfg.rules || []).map((r, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-white/3 rounded-xl p-2.5" data-testid={`fee-rule-${idx}`}>
              <input placeholder="Categorie (ex: hvac)" value={r.category || ""} onChange={e => updateRule(idx, "category", e.target.value || null)} className="col-span-3 bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" />
              <input placeholder="Zonă (ex: Cluj)" value={r.zone || ""} onChange={e => updateRule(idx, "zone", e.target.value || null)} className="col-span-3 bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" />
              <input type="number" placeholder="5" min="5" max="50" value={r.base_fee_ron} onChange={e => updateRule(idx, "base_fee_ron", parseFloat(e.target.value))} className="col-span-2 bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" title="Fee base RON (5-50)" />
              <input type="number" placeholder="0" min="0" max="50" value={r.priority_fee_ron || 0} onChange={e => updateRule(idx, "priority_fee_ron", parseFloat(e.target.value))} className="col-span-2 bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" title="Fee priority extra RON" />
              <label className="col-span-1 flex items-center gap-1 cursor-pointer text-xs">
                <input type="checkbox" checked={r.active !== false} onChange={e => updateRule(idx, "active", e.target.checked)} className="w-3.5 h-3.5 accent-[#d4ff3a]" /> activ
              </label>
              <button onClick={() => removeRule(idx)} className="col-span-1 text-red-400 hover:bg-red-500/10 rounded-md p-1.5"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
        </div>
      </div>

      <button onClick={save} disabled={saving} className="btn-accent px-6 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2" data-testid="fee-save">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează configurare
      </button>
      {msg && <div className="text-xs text-emerald-300">{msg}</div>}
    </div>
  );
};


const TierRulesTab = () => {
  const [rules, setRules] = useState(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    axios.get(`${API}/api/admin/tier-rules`).then(r => setRules(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true); setMsg("");
    try {
      await axios.put(`${API}/api/admin/tier-rules`, rules);
      setMsg("Salvat.");
    } catch (e) {
      setMsg(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  const runNow = async () => {
    if (!window.confirm("Rulează manual algoritmul de promovare?\n(Nu retrograda pe nimeni, doar promovează în sus + flag warning pe rating mic.)")) return;
    setRunning(true);
    try {
      const r = await axios.post(`${API}/api/admin/run-auto-promotion`);
      setLastRun(r.data);
    } catch (e) {
      setLastRun({ error: e?.response?.data?.detail || e.message });
    } finally { setRunning(false); }
  };

  if (!rules) return <Loader2 className="w-6 h-6 animate-spin text-[#d4ff3a]" />;

  const RuleField = ({ k, label, suffix, ...props }) => (
    <div>
      <label className="text-xs uppercase text-stone-500 mb-1 block">{label}</label>
      <div className="flex items-center gap-2">
        <input type="number" value={rules[k]} onChange={e => setRules({ ...rules, [k]: props.step === "0.1" ? parseFloat(e.target.value) : parseInt(e.target.value) })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm" data-testid={`tier-${k}`} {...props} />
        {suffix && <span className="text-xs text-stone-500">{suffix}</span>}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-5 space-y-4">
        <h3 className="font-serif text-xl text-[#d4ff3a]">🥇 Nivel 2 (VERIFIED) — promovare automată</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <RuleField k="nivel_2_min_completed_jobs" label="Min joburi finalizate" suffix="joburi" min="1" />
          <RuleField k="nivel_2_min_rating" label="Min rating mediu" suffix="/ 5" step="0.1" min="1" max="5" />
          <RuleField k="nivel_2_min_reviews" label="Min recenzii" suffix="reviews" min="1" />
        </div>
      </div>

      <div className="glass rounded-2xl p-5 space-y-4">
        <h3 className="font-serif text-xl text-[#d4ff3a]">🏆 Nivel 3 (PREMIUM) — promovare automată</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <RuleField k="nivel_3_min_completed_jobs" label="Min joburi" suffix="joburi" min="1" />
          <RuleField k="nivel_3_min_rating" label="Min rating" suffix="/ 5" step="0.1" min="1" max="5" />
          <RuleField k="nivel_3_min_reviews" label="Min recenzii" suffix="reviews" min="1" />
        </div>
      </div>

      <div className="glass rounded-2xl p-5 space-y-2 border border-amber-500/30">
        <h3 className="font-serif text-xl text-amber-400">⚠️ Warning Soft Rating (NU retrograda, NU suspendă)</h3>
        <p className="text-xs text-stone-400">Specialiștii sub acest rating primesc DOAR un flag vizual (badge roșu pe profil + warning în marketplace pentru clienți). Conform politicii "Marketplace Neutru", platforma NU suspendă pe nimeni.</p>
        <div className="max-w-xs"><RuleField k="soft_demote_below_rating" label="Sub rating" suffix="/ 5" step="0.1" min="1" max="5" /></div>
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={rules.cron_enabled} onChange={e => setRules({ ...rules, cron_enabled: e.target.checked })} className="w-4 h-4 accent-[#d4ff3a]" data-testid="tier-cron-enabled" />
        <span className="text-sm text-stone-300">Cron job activ (rulează zilnic la 03:30 Europe/Bucharest)</span>
      </label>

      <div className="flex items-center gap-3">
        <button onClick={save} disabled={saving} className="btn-accent px-6 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2" data-testid="tier-save">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează praguri
        </button>
        <button onClick={runNow} disabled={running} className="px-5 py-2.5 rounded-xl text-sm font-medium bg-violet-500/20 hover:bg-violet-500/30 text-violet-200 border border-violet-500/30 flex items-center gap-2" data-testid="tier-run-now">
          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Rulează acum
        </button>
        {msg && <span className="text-xs text-emerald-300">{msg}</span>}
      </div>

      {lastRun && (
        <div className="glass rounded-2xl p-4 text-sm" data-testid="tier-last-run-result">
          {lastRun.error ? (
            <div className="text-red-300 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {lastRun.error}</div>
          ) : (
            <div className="space-y-1 text-stone-300">
              <div className="flex items-center gap-2 text-emerald-300 font-semibold"><CheckCircle2 className="w-4 h-4" /> Promovare completă</div>
              <div>• Specialiști scanați: <strong>{lastRun.scanned}</strong></div>
              <div>• Promovați (Nivel ↑): <strong className="text-[#d4ff3a]">{lastRun.promoted}</strong></div>
              <div>• Flag warning low rating activat: <strong className="text-amber-300">{lastRun.flagged_low}</strong></div>
              <div>• Flag warning curățat: <strong className="text-stone-400">{lastRun.cleared_low}</strong></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


const PoliciesTab = () => {
  const [docs, setDocs] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = () => axios.get(`${API}/api/admin/policy-docs`).then(r => setDocs(r.data.items || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (data) => {
    try {
      await axios.post(`${API}/api/admin/policy-docs`, data);
      setEditing(null);
      load();
    } catch (e) {
      alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const latestPerSlug = {};
  docs.forEach(d => { if (!latestPerSlug[d.slug] || latestPerSlug[d.slug].created_at < d.created_at) latestPerSlug[d.slug] = d; });

  return (
    <div className="space-y-4">
      <p className="text-xs text-stone-400">Politicile sunt versionate. La fiecare modificare creezi o versiune nouă. Userii văd întotdeauna ultima versiune publicată. Dacă bifezi "necesită re-acceptare", toți userii vor fi solicitați să accepte la următorul login.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {POLICY_SLUGS.map(p => {
          const latest = latestPerSlug[p.slug];
          return (
            <div key={p.slug} className="glass rounded-2xl p-4" data-testid={`policy-${p.slug}`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-semibold text-sm">{p.title}</div>
                  <div className="text-xs text-stone-500 font-mono">slug: {p.slug}</div>
                </div>
                {latest && <span className="text-[10px] uppercase px-2 py-0.5 rounded-full bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/20">v{latest.version}</span>}
              </div>
              {latest ? (
                <div className="text-xs text-stone-400 mb-3">Publicat: {new Date(latest.created_at).toLocaleString("ro-RO")}</div>
              ) : (
                <div className="text-xs text-amber-300 mb-3 italic">Fără versiune publicată</div>
              )}
              <button onClick={() => setEditing({ slug: p.slug, title: p.title, content_html: latest?.content_html || "", version: latest ? incrementVersion(latest.version) : "1.0.0", requires_reacceptance: false })} className="px-3 py-1.5 rounded-lg text-xs bg-white/5 hover:bg-white/10" data-testid={`policy-edit-${p.slug}`}>
                {latest ? "Versiune nouă" : "Creează"}
              </button>
            </div>
          );
        })}
      </div>

      {editing && <PolicyEditor doc={editing} onClose={() => setEditing(null)} onSave={save} />}
    </div>
  );
};

const incrementVersion = (v) => {
  const parts = (v || "1.0.0").split(".").map(Number);
  parts[2] = (parts[2] || 0) + 1;
  return parts.join(".");
};


const PolicyEditor = ({ doc, onClose, onSave }) => {
  const [d, setD] = useState(doc);
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-strong rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="policy-editor">
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <h3 className="font-serif text-2xl">{d.title}</h3>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-200" data-testid="policy-editor-close"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase text-stone-500 mb-1 block">Versiune (semver)</label>
              <input value={d.version} onChange={e => setD({ ...d, version: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono" data-testid="policy-version" />
            </div>
            <label className="flex items-center gap-2 cursor-pointer mt-6">
              <input type="checkbox" checked={d.requires_reacceptance} onChange={e => setD({ ...d, requires_reacceptance: e.target.checked })} className="w-4 h-4 accent-[#d4ff3a]" data-testid="policy-requires-reaccept" />
              <span className="text-xs text-stone-300">Necesită re-acceptare userilor la login</span>
            </label>
          </div>
          <div>
            <label className="text-xs uppercase text-stone-500 mb-1 block">Conținut HTML</label>
            <textarea value={d.content_html} onChange={e => setD({ ...d, content_html: e.target.value })} rows={14} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono" placeholder="<h2>Titlu</h2><p>Conținut...</p>" data-testid="policy-content" />
            <div className="text-[10px] text-stone-500 mt-1">HTML acceptat: h2, p, ul, li, a, strong, em</div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-stone-400 hover:bg-white/5">Anulează</button>
            <button onClick={() => onSave(d)} disabled={!d.version || !d.content_html} className="btn-accent px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50" data-testid="policy-save">
              <Save className="w-4 h-4 inline mr-1" /> Publică versiunea
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


const PromotionRunsTab = () => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    axios.get(`${API}/api/admin/tier-promotion-runs`).then(r => setItems(r.data.items || [])).catch(() => {});
  }, []);
  if (items.length === 0) return <div className="text-stone-500 italic text-sm">Niciun istoric. Apasă "Rulează acum" în tab-ul "Praguri Tier".</div>;
  return (
    <div className="space-y-2" data-testid="promotion-runs-list">
      {items.map((r, i) => (
        <div key={i} className="glass rounded-xl p-3 text-sm grid grid-cols-6 gap-3 items-center">
          <div className="col-span-2 font-mono text-xs">{new Date(r.at).toLocaleString("ro-RO")}</div>
          <div className="text-xs">Scanați: <strong>{r.scanned}</strong></div>
          <div className="text-xs">Promovați: <strong className="text-[#d4ff3a]">{r.promoted}</strong></div>
          <div className="text-xs">Flag: <strong className="text-amber-300">{r.flagged_low}</strong></div>
          <div className="text-[10px] text-stone-500">{r.triggered_by}</div>
        </div>
      ))}
    </div>
  );
};

export default SpecialistProgressionPage;
