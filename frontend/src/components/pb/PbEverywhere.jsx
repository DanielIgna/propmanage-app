// PB-002 · PropBenefits Everywhere — componentele contextuale per suprafață.
// Platforma ADUCE beneficiile în context; utilizatorul nu le caută.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { Gift, Sparkles, ChevronRight, Handshake, Lock, BadgeCheck, TrendingUp } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// ---------------------------------------------------------------------------
// CLIENT · Benefits Pulse — primele 30 de secunde (montat în HomeV2)
// ---------------------------------------------------------------------------
export const BenefitsPulse = ({ go }) => {
  const [p, setP] = useState(null);
  const navigate = useNavigate();
  useEffect(() => {
    axios.get(`${API}/api/benefits/pulse`).then(r => setP(r.data)).catch(() => {});
  }, []);
  if (!p) return null;
  const na = p.next_action;
  const plan = p.plan || {};
  const paid = plan.cheapest_paid;
  const period = paid?.billing_period === "yearly" ? "an" : "lună";
  return (
    <div className="mx-5 mt-6 lg:mx-0 lg:mt-0 cv2-fade" data-testid="pb-pulse">
      <div className="flex items-center gap-2 px-1">
        <h3 className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400 flex-1">Valoarea abonamentului tău azi</h3>
        {plan.subscription_active
          ? <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-[#166534]/10 text-[#166534] border border-[#166534]/20" data-testid="pb-plan-status">House Health · Activ</span>
          : <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200" data-testid="pb-plan-status">Plan gratuit</span>}
      </div>
      <div className="mt-2 rounded-3xl border border-slate-100 bg-white shadow-sm overflow-hidden">
        <div className="grid grid-cols-3 divide-x divide-slate-100">
          <button onClick={() => go("benefits")} className="p-3.5 text-left" data-testid="pb-pulse-available">
            <div className="text-lg font-black text-slate-900">{p.available.count}</div>
            <div className="text-[10px] font-bold text-slate-400 leading-tight">beneficii disponibile acum</div>
          </button>
          <div className="p-3.5" data-testid="pb-pulse-saved">
            <div className="text-lg font-black text-[#166534]">{p.saved_value} RON</div>
            <div className="text-[10px] font-bold text-slate-400 leading-tight">valoare câștigată prin ecosistem</div>
          </div>
          <button onClick={() => go("benefits")} className="p-3.5 text-left" data-testid="pb-pulse-deals">
            <div className="text-lg font-black text-slate-900">{p.community_deals.negotiating}</div>
            <div className="text-[10px] font-bold text-slate-400 leading-tight">negocieri ale comunității în lucru</div>
          </button>
        </div>
        {/* Value discovery: plan/membership existent + CTA către flow-ul EXISTENT (fără billing nou) */}
        {!plan.subscription_active && paid && (
          <button onClick={() => navigate("/house-health/upgrade")} className="w-full flex items-center gap-3 border-t border-slate-100 bg-[#F0FBF4] px-4 py-3 text-left active:scale-[0.99] transition-transform" data-testid="pb-plan-cta">
            <span className="w-8 h-8 rounded-xl bg-[#166534]/10 flex items-center justify-center shrink-0"><Sparkles className="w-4 h-4 text-[#166534]" style={{ width: 16, height: 16 }} /></span>
            <span className="min-w-0 flex-1">
              <span className="block text-xs font-black text-slate-900 leading-snug">{paid.name} — {Number(paid.price_eur)}€/{period}</span>
              <span className="block text-[11px] text-slate-500 leading-snug">scor de sănătate, +5 GB stocare și beneficii exclusive</span>
            </span>
            <ChevronRight className="w-4 h-4 shrink-0 text-[#166534]" />
          </button>
        )}
        {plan.subscription_active && (
          <button onClick={() => go("benefits")} className="w-full flex items-center gap-3 border-t border-slate-100 px-4 py-2.5 text-left" data-testid="pb-plan-cta">
            <BadgeCheck className="w-4 h-4 shrink-0 text-[#166534]" style={{ width: 16, height: 16 }} />
            <span className="text-[11px] text-slate-500 truncate flex-1">Abonamentul tău e activ{plan.membership_level ? ` · nivel ${plan.membership_level}` : ""} — vezi ce ai deblocat</span>
            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-300" />
          </button>
        )}
        {na && (
          <a href={na.cta_path} className="flex items-center gap-3 border-t border-slate-100 bg-[#F0FBF4] px-4 py-3" data-testid="pb-pulse-action">
            <Sparkles className="w-4 h-4 shrink-0 text-[#166534]" style={{ width: 16, height: 16 }} />
            <span className="min-w-0 flex-1">
              <span className="block text-xs font-black text-slate-900 leading-snug">{na.title}</span>
              <span className="block text-[11px] text-slate-500 leading-snug">{na.value}</span>
            </span>
            <ChevronRight className="w-4 h-4 shrink-0 text-[#166534]" />
          </a>
        )}
        {p.community_deals.preview.length > 0 && (
          <button onClick={() => go("benefits")} className="w-full flex items-center gap-2 border-t border-slate-100 px-4 py-2.5 text-left" data-testid="pb-pulse-deals-preview">
            <Handshake className="w-3.5 h-3.5 shrink-0 text-slate-400" style={{ width: 14, height: 14 }} />
            <span className="text-[11px] text-slate-500 truncate flex-1">
              PropManage negociază pentru tine: {p.community_deals.preview.map(d => `${d.emoji} ${d.title}`).join(" · ")}
            </span>
            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-300" />
          </button>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// SPECIALIST · beneficii care aduc cereri (montat în rail SpecialistDashboard)
// ---------------------------------------------------------------------------
export const SpecialistBenefitsCard = () => {
  const [s, setS] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/benefits/specialist-summary`).then(r => setS(r.data)).catch(() => {});
  }, []);
  if (!s?.messages?.length) return null;
  return (
    <div className="pm-card !p-4 mb-4" data-testid="pb-specialist-card">
      <div className="flex items-center gap-2 mb-2.5">
        <Gift className="w-4 h-4 text-[var(--pm-primary,#d4ff3a)]" />
        <span className="text-[11px] font-black uppercase tracking-wider opacity-60">PropBenefits pentru tine</span>
      </div>
      <div className="space-y-2.5">
        {s.messages.map(m => (
          <div key={m.id} className="text-left" data-testid={`pb-sp-${m.id}`}>
            <div className="text-xs font-bold leading-snug">{m.title}</div>
            <div className="text-[11px] opacity-60 leading-snug mt-0.5">{m.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// ADMINISTRATOR · beneficiile clădirii (montat în AdministratorWorkspace)
// ---------------------------------------------------------------------------
export const BuildingBenefitsCard = ({ buildingId }) => {
  const [b, setB] = useState(null);
  useEffect(() => {
    if (buildingId) axios.get(`${API}/api/benefits/building-summary/${buildingId}`).then(r => setB(r.data)).catch(() => {});
  }, [buildingId]);
  if (!b) return null;
  return (
    <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm mt-4" data-testid="pb-building-card">
      <div className="flex items-center gap-2 mb-2">
        <Gift className="w-4 h-4 text-[#166534]" />
        <span className="text-[11px] font-black uppercase tracking-wider text-slate-400">Beneficii pentru întreaga clădire</span>
      </div>
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[["Apartamente participante", b.participation.participating_owners],
          ["Abonamente active", b.participation.active_subscriptions],
          ["Negocieri comunitate", b.deals_negotiating]].map(([l, v]) => (
          <div key={l} className="rounded-2xl bg-slate-50 p-2.5 text-center">
            <div className="text-base font-black text-slate-900">{v}</div>
            <div className="text-[9px] font-bold text-slate-400 leading-tight">{l}</div>
          </div>
        ))}
      </div>
      {b.building_campaigns.length > 0 && (
        <div className="mb-3" data-testid="pb-building-campaigns">
          <div className="text-[10px] font-black uppercase text-slate-400 mb-1.5">Campanii dedicate asociației</div>
          {b.building_campaigns.map(c => (
            <div key={c.id} className="text-xs text-slate-700 font-semibold py-0.5">• {c.title}</div>
          ))}
        </div>
      )}
      <div data-testid="pb-building-unlock">
        <div className="text-[10px] font-black uppercase text-slate-400 mb-1.5">Ce puteți debloca împreună</div>
        {b.unlock_together.map((u, i) => (
          <div key={i} className="text-[11px] text-slate-500 leading-snug py-0.5 flex gap-1.5">
            <TrendingUp className="w-3 h-3 shrink-0 mt-0.5 text-[#166534]" style={{ width: 12, height: 12 }} />{u}
          </div>
        ))}
      </div>
      <p className="text-[10px] text-slate-400 italic mt-2.5">{b.disclaimer}</p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// HOUSE HEALTH & DIGITAL TWIN · banner contextual (dark) — AI vorbește despre casă
// ---------------------------------------------------------------------------
export const PbContextBanner = ({ surface }) => {
  const [d, setD] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/benefits/context-banner/${surface}`).then(r => setD(r.data)).catch(() => {});
  }, [surface]);
  if (!d) return null;
  return (
    <div className="rounded-2xl border border-[#d4ff3a]/25 bg-[#d4ff3a]/5 p-4 mb-5" data-testid={`pb-banner-${surface}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <Gift className="w-4 h-4 text-[#d4ff3a]" />
        <span className="text-sm font-bold text-white leading-snug">{d.headline}</span>
      </div>
      <div className="space-y-0.5 mb-1.5">
        {d.effects.map((e, i) => (
          <div key={i} className="text-[12px] text-stone-300 flex gap-1.5 items-start">
            <span className="text-[#d4ff3a]">✔</span>{e}
          </div>
        ))}
      </div>
      {d.campaign && (
        <a href="/client?tab=benefits" className="inline-flex items-center gap-1 text-[11px] font-bold text-[#d4ff3a]" data-testid={`pb-banner-cta-${surface}`}>
          {d.campaign.eligible ? `Activează „${d.campaign.benefit_title}”` : `Vezi campania „${d.campaign.title}”`}
          <ChevronRight className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// MARKETPLACE · flags 🟢 activ · 🟡 prin abonament · 🔒 blocat
// ---------------------------------------------------------------------------
const FLAG_STYLE = {
  active: { dot: "🟢", cls: "border-emerald-400/30 bg-emerald-400/5 text-emerald-200" },
  subscription: { dot: "🟡", cls: "border-amber-400/30 bg-amber-400/5 text-amber-200" },
  locked: { dot: "🔒", cls: "border-white/10 bg-white/5 text-stone-400" },
  used: { dot: "✓", cls: "border-white/10 bg-white/5 text-stone-500" },
};

export const MarketplaceBenefitStrip = () => {
  const [d, setD] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/benefits/marketplace-flags`).then(r => setD(r.data)).catch(() => {});
  }, []);
  if (!d?.flags?.length) return null;
  return (
    <div className="pm-card-glass !p-4 mb-8" data-testid="pb-mkt-strip">
      <div className="flex items-center gap-2 mb-2.5">
        <Gift className="w-4 h-4 text-[var(--pm-primary,#d4ff3a)]" />
        <span className="text-[11px] font-black uppercase tracking-wider opacity-70">Beneficiile tale în marketplace</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {d.flags.map(f => {
          const st = FLAG_STYLE[f.flag] || FLAG_STYLE.locked;
          return (
            <span key={f.campaign_id} className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border text-[11px] font-semibold ${st.cls}`}
              data-testid={`pb-mkt-flag-${f.campaign_id}`}>
              <span>{st.dot}</span>{f.benefit_title || f.title} — {f.label}
            </span>
          );
        })}
      </div>
      <p className="text-[10px] opacity-50 mt-2">{d.slogan}</p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// CLIENT · Community Deals — negocierea comunității (secțiune în PropBenefitsHub)
// ---------------------------------------------------------------------------
const DEAL_STATUS = {
  in_lucru: { label: "În lucru", cls: "bg-slate-100 text-slate-500" },
  negociere: { label: "În negociere", cls: "bg-amber-100 text-amber-700" },
  pilot: { label: "Pilot", cls: "bg-sky-100 text-sky-700" },
  lansat: { label: "Lansat", cls: "bg-emerald-100 text-emerald-700" },
};

export const CommunityDealsSection = () => {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(null);
  const [signaled, setSignaled] = useState({});
  const load = () => axios.get(`${API}/api/benefits/community-deals`).then(r => setD(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!d) return null;
  const signal = async (id, sig) => {
    setBusy(id + sig);
    try {
      await axios.post(`${API}/api/benefits/community-deals/${id}/signal`, { signal: sig });
      setSignaled(p => ({ ...p, [id + sig]: true }));
      load();
    } finally { setBusy(null); }
  };
  const SIGNALS = [["sustin", "Susțin"], ["interesat", "Interesat"], ["vreau_oferta", "Vreau ofertă"], ["notifica_ma", "Notifică-mă"]];
  return (
    <div data-testid="pb-community-deals">
      <div className="text-xs font-black uppercase tracking-wider text-slate-400 mb-1">Community Deals — negocierea comunității</div>
      <p className="text-[11px] text-slate-400 mb-2">Nu este doar negocierea ta — este negocierea întregii comunități PropManage. Semnalele tale decid prioritatea negocierilor.</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
        {d.items.map(deal => {
          const st = DEAL_STATUS[deal.status] || DEAL_STATUS.in_lucru;
          return (
            <div key={deal.id} className="rounded-2xl border border-slate-100 bg-white p-3 shadow-sm" data-testid={`pb-deal-${deal.id}`}>
              <div className="flex items-center gap-3">
                <span className="text-xl shrink-0">{deal.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-bold text-slate-900 truncate">{deal.title}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${st.cls}`}>{st.label}</span>
                    <span className="text-[10px] text-slate-400">{deal.supporters} susținători</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {SIGNALS.map(([sig, label]) => {
                  const done = signaled[deal.id + sig] || (sig === "sustin" && deal.supported_by_me);
                  return (
                    <button key={sig} onClick={() => signal(deal.id, sig)} disabled={done || busy === deal.id + sig}
                      className={`px-2.5 py-1 rounded-full text-[10px] font-black border ${done ? "bg-[#F0FBF4] text-[#166534] border-[#D2F2DC]" : "bg-white text-slate-500 border-slate-200"}`}
                      data-testid={`pb-deal-${sig}-${deal.id}`}>
                      {done ? `${label} ✓` : label}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-slate-400 italic mt-2">{d.disclaimer}</p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// CLIENT · Ambassador — progresul spre statutul de ambasador (PB-003)
// ---------------------------------------------------------------------------
export const AmbassadorCard = () => {
  const [a, setA] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/benefits/ambassador`).then(r => setA(r.data)).catch(() => {});
  }, []);
  if (!a) return null;
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm" data-testid="pb-ambassador-card">
      <div className="flex items-center gap-2 mb-1.5">
        <BadgeCheck className="w-4 h-4" style={{ color: a.is_ambassador ? "#166534" : "#94a3b8", width: 16, height: 16 }} />
        <span className="text-[13px] font-black text-slate-900">
          {a.is_founding ? `Ești ${a.founding_badge} 🏆` : a.is_ambassador ? `Ești ${a.badge} 🏅` : "Community Ambassador"}
        </span>
        {a.is_founding && a.founding_rank && (
          <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 border border-amber-100" data-testid="pb-founding-badge">
            #{a.founding_rank} din primii 10
          </span>
        )}
      </div>
      {a.is_ambassador ? (
        <div className="text-[11px] text-slate-500">Recomandările tale confirmate construiesc comunitatea. {a.perks.join(" · ")}</div>
      ) : (
        <>
          <div className="text-[11px] text-slate-500 mb-2">
            {a.remaining === 1 ? "Mai ai un pas: încă o recomandare validată și devii ambasador."
              : `Recomandă specialiști după lucrări — la ${a.threshold} recomandări validate devii ambasador cu beneficii exclusive.`}
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-[#166534]" style={{ width: `${Math.min(100, (a.validated / a.threshold) * 100)}%` }} />
          </div>
          <div className="text-[10px] text-slate-400 mt-1" data-testid="pb-ambassador-progress">{a.validated}/{a.threshold} recomandări validate{a.pending ? ` · ${a.pending} în așteptarea efectului` : ""}</div>
        </>
      )}
    </div>
  );
};
