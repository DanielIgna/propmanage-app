// PropBenefitsAdminPage — PB-001 · control complet al motorului de beneficii FĂRĂ cod.
// Route: /admin/prop-benefits · API: /api/admin/prop-benefits/*
import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Gift, ChevronLeft, Loader2, Plus, RefreshCw, HeartPulse, Globe2, Brain,
  Megaphone, SlidersHorizontal, Play, Pencil, X, Handshake, Target, TrendingUp,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_STYLE = {
  active: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  preparing: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  scheduled: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  draft: "bg-stone-800 text-stone-400 border-stone-600",
  ended: "bg-stone-800 text-stone-500 border-stone-700",
};

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500">{label}</span>
    {children}
  </label>
);
const inputCls = "w-full mt-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white";

const EMPTY_FORM = {
  title: "", description: "", kind: "active_benefit", status: "draft", priority: 3,
  budget_total: 0, max_claims: 0, max_per_user: 1, city: "", starts_at: "", ends_at: "",
  benefit: { title: "", value_estimate: 0, expires_days: 60, instructions: "" },
  eligibility: {}, estimated_impact: { activation: 5, retention: 5, conversion: 5 },
};

const CampaignForm = ({ initial, kinds, statuses, onSaved, onClose }) => {
  const [f, setF] = useState(initial || EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const set = (k, v) => setF(p => ({ ...p, [k]: v }));
  const setB = (k, v) => setF(p => ({ ...p, benefit: { ...p.benefit, [k]: v } }));
  const setE = (k, v) => setF(p => {
    const el = { ...p.eligibility };
    if (v === false || v === "" || v == null) delete el[k]; else el[k] = v;
    return { ...p, eligibility: el };
  });

  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const payload = { ...f, priority: Number(f.priority), budget_total: Number(f.budget_total),
        max_claims: Number(f.max_claims), max_per_user: Number(f.max_per_user),
        starts_at: f.starts_at || null, ends_at: f.ends_at || null, city: f.city || null };
      if (initial?.id) await ax.patch(`/api/admin/prop-benefits/campaigns/${initial.id}`, payload);
      else await ax.post("/api/admin/prop-benefits/campaigns", payload);
      onSaved();
    } catch (e) { setErr(e?.response?.data?.detail || e.message); } finally { setBusy(false); }
  };

  return (
    <div className="border border-[#d4ff3a]/30 rounded-2xl bg-stone-900/60 p-4 space-y-3" data-testid="pbadmin-campaign-form">
      <div className="flex items-center gap-2">
        <div className="text-xs font-black uppercase tracking-wider text-[#d4ff3a] flex-1">
          {initial?.id ? "Editează campania" : "Campanie nouă"}
        </div>
        <button onClick={onClose} data-testid="pbadmin-form-close"><X className="w-4 h-4 text-stone-500" /></button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Field label="Titlu"><input className={inputCls} value={f.title} onChange={e => set("title", e.target.value)} data-testid="pbadmin-f-title" /></Field>
        <Field label="Tip"><select className={inputCls} value={f.kind} onChange={e => set("kind", e.target.value)} data-testid="pbadmin-f-kind">
          {kinds.map(k => <option key={k} value={k}>{k}</option>)}</select></Field>
        <Field label="Status"><select className={inputCls} value={f.status} onChange={e => set("status", e.target.value)} data-testid="pbadmin-f-status">
          {statuses.map(s => <option key={s} value={s}>{s}</option>)}</select></Field>
      </div>
      <Field label="Descriere (limbaj de beneficii, nu reduceri)"><textarea className={inputCls} rows={2} value={f.description} onChange={e => set("description", e.target.value)} data-testid="pbadmin-f-desc" /></Field>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <Field label="Prioritate 1-5"><input type="number" min="1" max="5" className={inputCls} value={f.priority} onChange={e => set("priority", e.target.value)} /></Field>
        <Field label="Buget total"><input type="number" className={inputCls} value={f.budget_total} onChange={e => set("budget_total", e.target.value)} data-testid="pbadmin-f-budget" /></Field>
        <Field label="Max. revendicări"><input type="number" className={inputCls} value={f.max_claims} onChange={e => set("max_claims", e.target.value)} /></Field>
        <Field label="Max / utilizator"><input type="number" className={inputCls} value={f.max_per_user} onChange={e => set("max_per_user", e.target.value)} /></Field>
        <Field label="Începe la"><input type="date" className={inputCls} value={(f.starts_at || "").slice(0, 10)} onChange={e => set("starts_at", e.target.value ? new Date(e.target.value).toISOString() : "")} /></Field>
        <Field label="Expiră la"><input type="date" className={inputCls} value={(f.ends_at || "").slice(0, 10)} onChange={e => set("ends_at", e.target.value ? new Date(e.target.value).toISOString() : "")} /></Field>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Field label="Beneficiu — titlu"><input className={inputCls} value={f.benefit.title} onChange={e => setB("title", e.target.value)} data-testid="pbadmin-f-benefit-title" /></Field>
        <Field label="Valoare estimată"><input type="number" className={inputCls} value={f.benefit.value_estimate} onChange={e => setB("value_estimate", Number(e.target.value))} /></Field>
        <Field label="Valabilitate (zile)"><input type="number" className={inputCls} value={f.benefit.expires_days} onChange={e => setB("expires_days", Number(e.target.value))} /></Field>
        <Field label="Oraș (opțional)"><input className={inputCls} value={f.city || ""} onChange={e => set("city", e.target.value)} /></Field>
      </div>
      <Field label="Instrucțiuni beneficiu"><input className={inputCls} value={f.benefit.instructions} onChange={e => setB("instructions", e.target.value)} /></Field>
      <div>
        <div className="text-[10px] font-bold uppercase tracking-wider text-stone-500 mb-1.5">Eligibilitate (AI Recommendation afișează doar celor relevanți)</div>
        <div className="flex flex-wrap gap-2" data-testid="pbadmin-f-eligibility">
          {[["subscription_active", "Abonament activ"], ["has_digital_twin", "Digital Twin"], ["has_house_health", "House Health"], ["email_verified", "Email verificat"]].map(([k, lbl]) => (
            <button key={k} onClick={() => setE(k, !f.eligibility[k])}
              className={`px-2.5 py-1.5 rounded-lg text-[11px] font-bold border ${f.eligibility[k] ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-700"}`}>
              {lbl}
            </button>
          ))}
          <input type="number" placeholder="Min. documente" className="bg-stone-800 border border-stone-700 rounded-lg px-2 py-1.5 text-[11px] text-white w-32"
            value={f.eligibility.min_documents ?? ""} onChange={e => setE("min_documents", e.target.value === "" ? "" : Number(e.target.value))} />
          <input type="number" placeholder="Min. lucrări" className="bg-stone-800 border border-stone-700 rounded-lg px-2 py-1.5 text-[11px] text-white w-28"
            value={f.eligibility.min_completed_jobs ?? ""} onChange={e => setE("min_completed_jobs", e.target.value === "" ? "" : Number(e.target.value))} />
          <select className="bg-stone-800 border border-stone-700 rounded-lg px-2 py-1.5 text-[11px] text-white"
            value={f.eligibility.min_membership || ""} onChange={e => setE("min_membership", e.target.value)}>
            <option value="">Nivel minim: oricare</option>
            {["bronze", "silver", "gold", "verified", "elite"].map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {["activation", "retention", "conversion"].map(k => (
          <Field key={k} label={`Impact estimat · ${k} (0-10)`}>
            <input type="number" min="0" max="10" className={inputCls} value={f.estimated_impact[k]}
              onChange={e => setF(p => ({ ...p, estimated_impact: { ...p.estimated_impact, [k]: Number(e.target.value) } }))} />
          </Field>
        ))}
      </div>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2" data-testid="pbadmin-form-error">{String(err)}</div>}
      <button onClick={save} disabled={busy} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="pbadmin-form-save">
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Salvează campania
      </button>
    </div>
  );
};

const ConfigPanel = () => {
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  useEffect(() => { ax.get("/api/admin/prop-benefits/config").then(r => setCfg(r.data)).catch(() => {}); }, []);
  if (!cfg) return <Loader2 className="w-4 h-4 animate-spin text-stone-500" />;

  const save = async (patch) => {
    setBusy(true); setSaved(false);
    try { const { data } = await ax.patch("/api/admin/prop-benefits/config", patch); setCfg(data); setSaved(true); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4" data-testid="pbadmin-config">
      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-3">Niveluri de membru (praguri de puncte)</div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {cfg.levels.map((lv, i) => (
            <Field key={lv.key} label={lv.name}>
              <input type="number" className={inputCls} value={lv.min_points} data-testid={`pbadmin-level-${lv.key}`}
                onChange={e => setCfg(p => { const levels = [...p.levels]; levels[i] = { ...lv, min_points: Number(e.target.value) }; return { ...p, levels }; })} />
            </Field>
          ))}
        </div>
        <button onClick={() => save({ levels: cfg.levels })} disabled={busy}
          className="mt-3 px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold" data-testid="pbadmin-save-levels">Salvează nivelurile</button>
      </div>
      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-3">Puncte per criteriu (Membership)</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(cfg.level_points).map(([k, v]) => (
            <Field key={k} label={k.replace(/_/g, " ")}>
              <input type="number" className={inputCls} value={v}
                onChange={e => setCfg(p => ({ ...p, level_points: { ...p.level_points, [k]: Number(e.target.value) } }))} />
            </Field>
          ))}
        </div>
        <button onClick={() => save({ level_points: cfg.level_points })} disabled={busy}
          className="mt-3 px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold">Salvează punctele</button>
      </div>
      <div className="border border-stone-800 rounded-2xl p-4" data-testid="pbadmin-referral-config">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-1">Beneficiu Referral (PB-001.4)</div>
        <p className="text-[11px] text-stone-500 mb-3">Se acordă DOAR după activarea abonamentului sau primul serviciu plătit — nu la crearea contului.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Beneficiu pentru cel care invită"><input className={inputCls} value={cfg.referral_benefit.inviter.title}
            onChange={e => setCfg(p => ({ ...p, referral_benefit: { ...p.referral_benefit, inviter: { ...p.referral_benefit.inviter, title: e.target.value } } }))} /></Field>
          <Field label="Beneficiu pentru cel invitat"><input className={inputCls} value={cfg.referral_benefit.invitee.title}
            onChange={e => setCfg(p => ({ ...p, referral_benefit: { ...p.referral_benefit, invitee: { ...p.referral_benefit.invitee, title: e.target.value } } }))} /></Field>
        </div>
        <button onClick={() => save({ referral_benefit: cfg.referral_benefit })} disabled={busy}
          className="mt-3 px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold">Salvează referral</button>
      </div>
      {cfg.journey && (
        <div className="border border-stone-800 rounded-2xl p-4" data-testid="pbadmin-journey-config">
          <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-1">Journey & Readiness (SH-001)</div>
          <p className="text-[11px] text-stone-500 mb-3">Pragurile Drumului Casei — zero hardcodare. Categoriile obligatorii pentru „Documentație verificată" se scriu separate prin virgulă.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Field label="Completitudine minimă L5 (%)">
              <input type="number" min="1" max="100" className={inputCls} value={cfg.journey.doc_verified_min_completeness} data-testid="pbadmin-journey-mincomp"
                onChange={e => setCfg(p => ({ ...p, journey: { ...p.journey, doc_verified_min_completeness: Number(e.target.value) } }))} />
            </Field>
            <Field label="Min. documente L2">
              <input type="number" min="1" className={inputCls} value={cfg.journey.book_started_min_docs}
                onChange={e => setCfg(p => ({ ...p, journey: { ...p.journey, book_started_min_docs: Number(e.target.value) } }))} />
            </Field>
            <div className="col-span-2">
              <Field label="Categorii obligatorii L5 (virgulă)">
                <input className={inputCls} value={(cfg.journey.doc_verified_required_categories || []).join(", ")} data-testid="pbadmin-journey-cats"
                  onChange={e => setCfg(p => ({ ...p, journey: { ...p.journey, doc_verified_required_categories: e.target.value.split(",").map(s => s.trim()).filter(Boolean) } }))} />
              </Field>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-3">
            {Object.entries(cfg.journey.readiness_weights || {}).map(([k, v]) => (
              <Field key={k} label={`Pondere ${k}`}>
                <input type="number" min="0" className={inputCls} value={v}
                  onChange={e => setCfg(p => ({ ...p, journey: { ...p.journey, readiness_weights: { ...p.journey.readiness_weights, [k]: Number(e.target.value) } } }))} />
              </Field>
            ))}
          </div>
          <button onClick={() => save({ journey: cfg.journey })} disabled={busy}
            className="mt-3 px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold" data-testid="pbadmin-save-journey">Salvează Journey</button>
        </div>
      )}
      {cfg.engagement && (
        <div className="border border-stone-800 rounded-2xl p-4" data-testid="pbadmin-engagement-config">
          <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-1">Engagement & Achievements (UX-001)</div>
          <p className="text-[11px] text-stone-500 mb-3">Mesaje, praguri, insigne și deblocări — zero hardcodare.</p>
          <div className="flex gap-2 mb-3">
            {[["enabled", "Sistem activ"], ["animations_enabled", "Animații"]].map(([k, lbl]) => (
              <button key={k} onClick={() => setCfg(p => ({ ...p, engagement: { ...p.engagement, [k]: !p.engagement[k] } }))}
                data-testid={`pbadmin-eng-${k}`}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border ${cfg.engagement[k] ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-700"}`}>
                {lbl}: {cfg.engagement[k] ? "ON" : "OFF"}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Field label="Prag celebrare Readiness (+%)">
              <input type="number" min="1" className={inputCls} value={cfg.engagement.readiness_celebration_min_delta}
                onChange={e => setCfg(p => ({ ...p, engagement: { ...p.engagement, readiness_celebration_min_delta: Number(e.target.value) } }))} />
            </Field>
            <div className="col-span-2">
              <Field label="Milestone-uri (%) — virgulă">
                <input className={inputCls} value={(cfg.engagement.milestones || []).join(", ")} data-testid="pbadmin-eng-milestones"
                  onChange={e => setCfg(p => ({ ...p, engagement: { ...p.engagement, milestones: e.target.value.split(",").map(s => Number(s.trim())).filter(n => n > 0) } }))} />
              </Field>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(cfg.engagement.level_messages || {}).map(([n, msg]) => (
              <Field key={n} label={`Mesaj Nivel ${n} · deblocare: ${(cfg.engagement.level_unlocks || {})[n] || "—"}`}>
                <input className={inputCls} value={msg} data-testid={`pbadmin-eng-lvlmsg-${n}`}
                  onChange={e => setCfg(p => ({ ...p, engagement: { ...p.engagement, level_messages: { ...p.engagement.level_messages, [n]: e.target.value } } }))} />
              </Field>
            ))}
          </div>
          <div className="mt-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-stone-500 mb-2">Insigne ({(cfg.engagement.badges || []).length})</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {(cfg.engagement.badges || []).map((b, i) => (
                <div key={b.id} className="flex items-center gap-2 bg-stone-900/40 border border-stone-800 rounded-xl p-2" data-testid={`pbadmin-badge-${b.id}`}>
                  <span className="text-base shrink-0">{b.icon}</span>
                  <input className="flex-1 bg-transparent text-xs text-white font-bold outline-none" value={b.label}
                    onChange={e => setCfg(p => { const badges = [...p.engagement.badges]; badges[i] = { ...badges[i], label: e.target.value }; return { ...p, engagement: { ...p.engagement, badges } }; })} />
                  <button onClick={() => setCfg(p => { const badges = [...p.engagement.badges]; badges[i] = { ...badges[i], enabled: !badges[i].enabled }; return { ...p, engagement: { ...p.engagement, badges } }; })}
                    className={`text-[9px] font-black px-2 py-0.5 rounded-full ${b.enabled !== false ? "bg-emerald-500/10 text-emerald-300" : "bg-stone-800 text-stone-500"}`}>
                    {b.enabled !== false ? "ON" : "OFF"}
                  </button>
                </div>
              ))}
            </div>
          </div>
          <button onClick={() => save({ engagement: cfg.engagement })} disabled={busy}
            className="mt-3 px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold" data-testid="pbadmin-save-engagement">Salvează Engagement</button>
        </div>
      )}
      {saved && <div className="text-xs text-emerald-300" data-testid="pbadmin-config-saved">Configurare salvată.</div>}
    </div>
  );
};

const GrowthPanel = () => {
  const [g, setG] = useState(null);
  useEffect(() => { ax.get("/api/admin/prop-benefits/community-growth").then(r => setG(r.data)).catch(() => {}); }, []);
  if (!g) return <Loader2 className="w-4 h-4 animate-spin text-stone-500" />;
  const Q = [
    ["most_valuable_deal", "Care este cel mai valoros Deal?"],
    ["negotiation_to_start", "Ce negociere trebuie pornită?"],
    ["top_demand_category", "Ce categorie are cea mai mare cerere?"],
    ["partner_to_contact", "Ce partener merită contactat?"],
    ["active_ambassadors", "Care sunt ambasadorii activi?"],
    ["retention_impact", "Care este impactul asupra retenției?"],
  ];
  return (
    <div className="space-y-3" data-testid="pbadmin-growth">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Q.map(([k, q]) => (
          <div key={k} className="border border-stone-800 rounded-2xl p-3.5 bg-stone-900/40" data-testid={`pbadmin-growth-${k}`}>
            <div className="text-[10px] font-black uppercase tracking-wider text-[#d4ff3a] mb-1">{q}</div>
            <div className="text-xs text-stone-200 leading-snug">{g.answers[k]?.answer}</div>
            {k === "active_ambassadors" && (g.answers[k]?.items || []).map(a => (
              <div key={a.id} className="text-[11px] text-stone-400 mt-1">🏅 {a.name || a.email} · {a.validated} recomandări validate</div>
            ))}
          </div>
        ))}
      </div>
      <div className="border border-stone-800 rounded-2xl p-3.5">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2">Cererea pe Community Deals (prioritate negociere)</div>
        {g.deals_demand.map(d => (
          <div key={d.id} className="flex items-center gap-3 py-1.5 border-b border-stone-800/60 last:border-0 text-xs" data-testid={`pbadmin-demand-${d.id}`}>
            <span className="text-stone-500 w-5">#{d.negotiation_priority}</span>
            <span>{d.emoji}</span>
            <span className="text-white font-bold flex-1 truncate">{d.title}</span>
            <span className="text-stone-400">scor {d.demand_score}</span>
            <span className="text-[10px] text-stone-500">S:{d.counts.sustin} · I:{d.counts.interesat} · O:{d.counts.vreau_oferta} · N:{d.counts.notifica_ma}</span>
            <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded ${d.interest_level === "ridicat" ? "bg-emerald-500/10 text-emerald-300" : d.interest_level === "moderat" ? "bg-amber-500/10 text-amber-300" : "bg-stone-800 text-stone-400"}`}>{d.interest_level}</span>
          </div>
        ))}
      </div>
      <div className="text-[11px] text-stone-500">Recomandări: {g.recommendations.validated} validate · {g.recommendations.pending} în așteptarea efectului (contact → ofertă → lucrare → lucrare confirmată).</div>
    </div>
  );
};

const DealsPanel = () => {
  const [d, setD] = useState(null);
  const [nt, setNt] = useState("");
  const load = () => ax.get("/api/admin/prop-benefits/community-deals").then(r => setD(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!d) return <Loader2 className="w-4 h-4 animate-spin text-stone-500" />;
  const setStatus = async (id, status) => { await ax.patch(`/api/admin/prop-benefits/community-deals/${id}`, { status }); load(); };
  const add = async () => {
    if (!nt.trim()) return;
    await ax.post("/api/admin/prop-benefits/community-deals", { title: nt, status: "in_lucru" });
    setNt(""); load();
  };
  return (
    <div className="space-y-2" data-testid="pbadmin-deals">
      <p className="text-[11px] text-stone-500">Negocierea comunității. REGULĂ: nu promitem procente — beneficiile depind de acordurile comerciale și de puterea comunității la momentul lansării.</p>
      <div className="flex gap-2">
        <input value={nt} onChange={e => setNt(e.target.value)} placeholder="Deal nou (ex: 🚪 Uși interior Polonia)"
          className="flex-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="pbadmin-deal-new-title" />
        <button onClick={add} className="px-3 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold" data-testid="pbadmin-deal-add">Adaugă</button>
      </div>
      {d.items.map(deal => (
        <div key={deal.id} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3 flex items-center gap-3 flex-wrap" data-testid={`pbadmin-deal-${deal.id}`}>
          <span className="text-lg">{deal.emoji}</span>
          <div className="flex-1 min-w-[180px]">
            <div className="text-xs font-bold text-white">{deal.title}</div>
            <div className="text-[10px] text-stone-500">{deal.category || "—"} · {deal.supporters} susținători</div>
          </div>
          <select value={deal.status} onChange={e => setStatus(deal.id, e.target.value)}
            className="bg-stone-800 border border-stone-700 rounded-lg px-2 py-1.5 text-[11px] text-white" data-testid={`pbadmin-deal-status-${deal.id}`}>
            {d.statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      ))}
    </div>
  );
};

export default function PropBenefitsAdminPage() {
  const navigate = useNavigate();
  const [ov, setOv] = useState(null);
  const [tab, setTab] = useState("campaigns");
  const [camps, setCamps] = useState([]);
  const [health, setHealth] = useState([]);
  const [advisor, setAdvisor] = useState(null);
  const [advisorBusy, setAdvisorBusy] = useState(false);
  const [form, setForm] = useState(null);
  const [tickBusy, setTickBusy] = useState(false);
  const [ns, setNs] = useState(null);

  const load = useCallback(() => {
    ax.get("/api/admin/prop-benefits/overview").then(r => setOv(r.data)).catch(() => {});
    ax.get("/api/admin/prop-benefits/campaigns").then(r => setCamps(r.data.items || [])).catch(() => {});
    ax.get("/api/admin/prop-benefits/north-star").then(r => setNs(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (tab === "health") ax.get("/api/admin/prop-benefits/subscription-health").then(r => setHealth(r.data.items || [])).catch(() => {});
    if (tab === "advisor" && !advisor) { setAdvisorBusy(true); ax.get("/api/admin/prop-benefits/growth-advisor").then(r => setAdvisor(r.data)).catch(() => {}).finally(() => setAdvisorBusy(false)); }
  }, [tab]); // eslint-disable-line

  const runTick = async () => {
    setTickBusy(true);
    try { await ax.post("/api/admin/prop-benefits/run-tick"); load(); if (tab === "health") setTab("health"); } finally { setTickBusy(false); }
  };
  const refreshAdvisor = async () => {
    setAdvisorBusy(true);
    try { const { data } = await ax.get("/api/admin/prop-benefits/growth-advisor?refresh=true"); setAdvisor(data); } finally { setAdvisorBusy(false); }
  };

  const eco = ov?.ecosystem;
  const TABS = [
    { id: "campaigns", label: `Campanii (${camps.length})`, icon: Megaphone },
    { id: "growth", label: "Community Growth", icon: TrendingUp },
    { id: "deals", label: "Community Deals", icon: Handshake },
    { id: "config", label: "Niveluri & Config", icon: SlidersHorizontal },
    { id: "health", label: "Subscription Health", icon: HeartPulse },
    { id: "advisor", label: "AI Growth Advisor", icon: Brain },
    { id: "ecosystem", label: "Ecosystem Health", icon: Globe2 },
  ];

  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8 admin-shell" data-testid="pbadmin-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-2">
          <button onClick={() => navigate("/admin")} className="text-stone-400 hover:text-white" data-testid="pbadmin-back"><ChevronLeft className="w-5 h-5" /></button>
          <Gift className="w-6 h-6 text-[#d4ff3a]" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">PropBenefits</h1>
          <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full border bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/30">PB-001 · Motor de retenție</span>
          <div className="flex-1" />
          <button onClick={runTick} disabled={tickBusy} className="px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold flex items-center gap-1.5" data-testid="pbadmin-run-tick">
            {tickBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} Rulează tick-ul zilnic
          </button>
        </div>
        <p className="text-xs text-stone-500 mb-5">PropManage nu vinde reduceri. Construiește valoare pentru proprietari prin puterea comunității.</p>

        {ns && (
          <div className="border border-[#d4ff3a]/25 bg-[#d4ff3a]/5 rounded-2xl p-4 mb-4" data-testid="pbadmin-north-star">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <Target className="w-4 h-4 text-[#d4ff3a]" />
              <span className="text-xs font-black uppercase tracking-wider text-[#d4ff3a]">North Star — obiectivul comun al agenților AI</span>
              <span className="text-[10px] text-stone-500">AI Growth Advisor + AI Success Manager</span>
            </div>
            <div className="flex items-end gap-3 flex-wrap">
              <div className="text-3xl font-black text-white" data-testid="pbadmin-ns-value">{ns.healthy}</div>
              <div className="text-xs text-stone-400 pb-1">/ {ns.target} abonamente active și sănătoase</div>
              <div className="flex-1" />
              {ns.dimensions.map(dd => (
                <div key={dd.key} className="text-center px-2">
                  <div className="text-sm font-bold text-white">{dd.value}</div>
                  <div className="text-[9px] text-stone-500 leading-tight max-w-[90px]">{dd.label}</div>
                </div>
              ))}
            </div>
            <div className="h-1.5 bg-stone-800 rounded-full overflow-hidden mt-2.5">
              <div className="h-full rounded-full bg-[#d4ff3a]" style={{ width: `${Math.max(0.5, ns.progress_pct)}%` }} />
            </div>
            <p className="text-[10px] text-stone-500 mt-1.5">{ns.definition}</p>
          </div>
        )}

        {ov && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6" data-testid="pbadmin-kpis">
            {[["Ecosystem Health", `${eco?.score}/100`], ["Campanii active", ov.campaigns.active],
              ["Beneficii active", ov.benefits.available], ["Referral în așteptare", ov.referrals.pending],
              ["Abonați at-risk", ov.health.at_risk]].map(([l, v]) => (
              <div key={l} className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4">
                <div className="text-[10px] uppercase tracking-wider text-stone-500">{l}</div>
                <div className="text-2xl font-bold text-white mt-1">{v}</div>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-1.5 flex-wrap mb-5">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`px-3 py-1.5 text-[11px] font-bold rounded-xl border flex items-center gap-1.5 ${tab === id ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-800"}`}
              data-testid={`pbadmin-tab-${id}`}>
              <Icon className="w-3 h-3" /> {label}
            </button>
          ))}
        </div>

        {tab === "campaigns" && (
          <div className="space-y-3" data-testid="pbadmin-campaigns">
            {!form && (
              <button onClick={() => setForm({ ...EMPTY_FORM })} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="pbadmin-new-campaign">
                <Plus className="w-3.5 h-3.5" /> Campanie nouă
              </button>
            )}
            {form && <CampaignForm initial={form.id ? form : null} kinds={ov?.meta?.kinds || []} statuses={ov?.meta?.statuses || []}
              onSaved={() => { setForm(null); load(); }} onClose={() => setForm(null)} />}
            {camps.map(c => (
              <div key={c.id} className="bg-stone-900/40 border border-stone-800 rounded-2xl p-4 flex flex-wrap items-center gap-3" data-testid={`pbadmin-camp-${c.id}`}>
                <div className="flex-1 min-w-[220px]">
                  <div className="text-sm font-bold text-white">{c.title}</div>
                  <div className="text-[11px] text-stone-500">{c.kind} · prioritate {c.priority} · {c.claims_count}/{c.max_claims || "∞"} revendicări · buget {c.budget_used}/{c.budget_total || "∞"}</div>
                </div>
                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${STATUS_STYLE[c.status] || STATUS_STYLE.draft}`}>{c.status}</span>
                <button onClick={() => setForm(c)} className="p-1.5 rounded-lg bg-stone-800 border border-stone-700" data-testid={`pbadmin-edit-${c.id}`}><Pencil className="w-3.5 h-3.5 text-stone-300" /></button>
              </div>
            ))}
          </div>
        )}

        {tab === "growth" && <GrowthPanel />}

        {tab === "deals" && <DealsPanel />}

        {tab === "config" && <ConfigPanel />}

        {tab === "health" && (
          <div className="space-y-2" data-testid="pbadmin-health">
            <p className="text-[11px] text-stone-500">Snapshot zilnic (08:45) al abonaților activi. Dacă scorul scade, AI Success Manager intervine contextual la user.</p>
            {health.length === 0 && <div className="text-xs text-stone-500 border border-stone-800 rounded-xl p-4">Niciun snapshot încă — rulează tick-ul zilnic din header.</div>}
            {health.map(h => (
              <div key={h.user_id} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3 flex items-center gap-3">
                <span className={`text-lg font-black w-12 ${h.score >= 70 ? "text-emerald-300" : h.score >= 40 ? "text-amber-300" : "text-rose-300"}`}>{h.score}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-white truncate">{h.name || h.email}</div>
                  <div className="text-[10px] text-stone-500">{h.email}</div>
                </div>
                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${h.status === "at_risk" ? "bg-rose-500/10 text-rose-300" : h.status === "watch" ? "bg-amber-500/10 text-amber-300" : "bg-emerald-500/10 text-emerald-300"}`}>{h.status}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "advisor" && (
          <div className="space-y-3" data-testid="pbadmin-advisor">
            <button onClick={refreshAdvisor} disabled={advisorBusy} className="px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold flex items-center gap-1.5" data-testid="pbadmin-advisor-refresh">
              {advisorBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Regenerează analiza
            </button>
            {advisorBusy && !advisor && <Loader2 className="w-5 h-5 animate-spin text-stone-500" />}
            {advisor && (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {[["Abonamente active", advisor.metrics.subscriptions_active], ["Retenție 30z", `${advisor.metrics.retention_pct}%`],
                    ["Expiră în 30z", advisor.metrics.expiring_30d], ["Referral activate", advisor.metrics.referral_activated]].map(([l, v]) => (
                    <div key={l} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3">
                      <div className="text-[10px] uppercase text-stone-500">{l}</div>
                      <div className="text-xl font-bold text-white">{v}</div>
                    </div>
                  ))}
                </div>
                <div className="border border-stone-800 rounded-2xl p-4">
                  <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2">Constatări</div>
                  {advisor.findings.map((f, i) => <div key={i} className="text-xs text-stone-300 mb-1.5">• {f}</div>)}
                </div>
                {advisor.ai_recommendations && (
                  <div className="border border-[#d4ff3a]/25 bg-[#d4ff3a]/5 rounded-2xl p-4" data-testid="pbadmin-advisor-ai">
                    <div className="text-xs font-black uppercase tracking-wider text-[#d4ff3a] mb-2">Acțiunile săptămânii — AI Growth Advisor</div>
                    <div className="text-xs text-stone-200 whitespace-pre-wrap">{advisor.ai_recommendations}</div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {tab === "ecosystem" && eco && (
          <div className="space-y-2" data-testid="pbadmin-ecosystem">
            <div className="flex items-end gap-3 mb-2">
              <div className="text-5xl font-black text-white">{eco.score}</div>
              <div className="text-xs text-stone-500 pb-1.5">/100 · {eco.status} · Nord: {eco.north_star.value}/{eco.north_star.target} abonamente</div>
            </div>
            {eco.components.map(c => (
              <div key={c.key} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3">
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-bold text-white">{c.label}</span>
                  <span className="text-stone-400">{c.value} / {c.target} · {c.points}p din {c.weight}</span>
                </div>
                <div className="h-1.5 bg-stone-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-[#d4ff3a]" style={{ width: `${c.ratio * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
