// PropBenefitsHub — PB-001 · fața de client a motorului de beneficii (tab „Beneficii" în ClientDashboardV2).
// NU afișează reduceri — afișează oportunități, portofelul de beneficii și nivelul de membru.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Gift, Sparkles, Lock, Loader2, ChevronRight, BadgeCheck, Clock, CheckCircle2 } from "lucide-react";
import { API } from "../pages/DashShared";
import { CommunityDealsSection, AmbassadorCard } from "./pb/PbEverywhere";

const LEVEL_COLORS = {
  explorer: "bg-slate-100 text-slate-600", bronze: "bg-amber-100 text-amber-700",
  silver: "bg-slate-200 text-slate-700", gold: "bg-yellow-100 text-yellow-700",
  verified: "bg-emerald-100 text-emerald-700", elite: "bg-slate-900 text-white",
};

const OppCard = ({ o, onClaim, claiming }) => (
  <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm" data-testid={`pb-opp-${o.campaign_id}`}>
    <div className="flex items-center gap-2 mb-1.5">
      <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-[#ecfdf3] text-[#166534]">{o.kind_label}</span>
      {o.ends_at && <span className="text-[10px] text-slate-400 flex items-center gap-1"><Clock className="w-3 h-3" />până la {new Date(o.ends_at).toLocaleDateString("ro-RO")}</span>}
    </div>
    <div className="text-sm font-black text-slate-900">{o.title}</div>
    <div className="text-xs text-slate-500 mt-1">{o.description}</div>
    {(o.why || []).slice(0, 2).map((w, i) => (
      <div key={i} className="text-[11px] text-[#166534] mt-1 flex items-start gap-1"><Sparkles className="w-3 h-3 mt-0.5 shrink-0" />{w}</div>
    ))}
    {o.auto_granted ? (
      <div className="mt-3 text-[11px] font-bold text-slate-400">Se acordă automat la activarea vecinului invitat.</div>
    ) : (
      <button onClick={() => onClaim(o.campaign_id)} disabled={claiming === o.campaign_id}
        className="mt-3 w-full py-2.5 rounded-full text-sm font-black text-black active:scale-[0.98] transition-transform"
        style={{ background: "#ccff00" }} data-testid={`pb-claim-${o.campaign_id}`}>
        {claiming === o.campaign_id ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Activează beneficiul"}
      </button>
    )}
  </div>
);

const BenefitRow = ({ b, onUse, using }) => (
  <div className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm" data-testid={`pb-benefit-${b.id}`}>
    <span className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${b.status === "used" ? "bg-slate-50" : "bg-[#ecfdf3]"}`}>
      {b.status === "used" ? <CheckCircle2 className="w-4.5 h-4.5 text-slate-400" style={{ width: 18, height: 18 }} /> : <Gift className="w-4.5 h-4.5 text-[#166534]" style={{ width: 18, height: 18 }} />}
    </span>
    <div className="flex-1 min-w-0">
      <div className="text-[13px] font-bold text-slate-900 truncate">{b.title}</div>
      <div className="text-[11px] text-slate-400">
        {b.status === "available" && b.expires_at ? `Valabil până la ${new Date(b.expires_at).toLocaleDateString("ro-RO")}`
          : b.status === "used" ? `Folosit la ${new Date(b.used_at).toLocaleDateString("ro-RO")}`
          : b.status === "expired" ? "Expirat" : "În așteptarea activării"}
        {b.instructions && b.status === "available" ? ` · ${b.instructions}` : ""}
      </div>
    </div>
    {b.status === "available" && (
      <button onClick={() => onUse(b.id)} disabled={using === b.id}
        className="px-3.5 py-2 rounded-full text-xs font-black bg-slate-900 text-white shrink-0" data-testid={`pb-use-${b.id}`}>
        {using === b.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Folosește"}
      </button>
    )}
  </div>
);

export const PropBenefitsHub = () => {
  const [data, setData] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [sm, setSm] = useState(null);
  const [claiming, setClaiming] = useState(null);
  const [using, setUsing] = useState(null);
  const [msg, setMsg] = useState(null);
  const [walletTab, setWalletTab] = useState("available");

  const load = useCallback(() => {
    axios.get(`${API}/benefits/opportunities`).then(r => setData(r.data)).catch(() => {});
    axios.get(`${API}/benefits/wallet`).then(r => setWallet(r.data)).catch(() => {});
    axios.get(`${API}/benefits/success-manager`).then(r => setSm(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const claim = async (cid) => {
    setClaiming(cid); setMsg(null);
    try {
      await axios.post(`${API}/benefits/claim/${cid}`);
      setMsg({ ok: true, text: "Beneficiul e acum în portofelul tău. 🎉" });
      load();
    } catch (e) {
      setMsg({ ok: false, text: e?.response?.data?.detail?.error || e?.response?.data?.detail || "Nu s-a putut activa beneficiul." });
    } finally { setClaiming(null); }
  };
  const useIt = async (bid) => {
    setUsing(bid); setMsg(null);
    try {
      await axios.post(`${API}/benefits/use/${bid}`);
      setMsg({ ok: true, text: "Beneficiu marcat ca folosit — echipa te va contacta pentru programare." });
      load();
    } catch (e) {
      setMsg({ ok: false, text: e?.response?.data?.detail || "Nu s-a putut folosi beneficiul." });
    } finally { setUsing(null); }
  };

  if (!data) return <div className="px-5 py-10 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>;
  const mem = data.membership;
  const na = sm?.next_action;

  return (
    <div className="px-5 pb-8 space-y-4 lg:max-w-3xl" data-testid="pb-hub">
      {/* Nivel membru */}
      <div className="rounded-3xl bg-slate-900 p-5 text-white" data-testid="pb-membership">
        <div className="flex items-center gap-3">
          <span className={`text-[11px] font-black uppercase px-2.5 py-1 rounded-full ${LEVEL_COLORS[mem.level.key] || LEVEL_COLORS.explorer}`} data-testid="pb-level-badge">
            <BadgeCheck className="w-3 h-3 inline mr-1" style={{ width: 12, height: 12 }} />{mem.level.name}
          </span>
          <div className="flex-1" />
          <span className="text-xs text-slate-400">{mem.points} puncte</span>
        </div>
        {mem.next_level && (
          <>
            <div className="mt-3 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${Math.min(100, (mem.points / mem.next_level.min_points) * 100)}%`, background: "#ccff00" }} />
            </div>
            <div className="text-[11px] text-slate-400 mt-1.5" data-testid="pb-next-level">
              Încă {mem.next_level.points_needed} puncte până la <b className="text-white">{mem.next_level.name}</b>
            </div>
          </>
        )}
        {(mem.level.perks || []).slice(0, 2).map((p, i) => (
          <div key={i} className="text-[11px] text-slate-300 mt-1 flex items-center gap-1.5"><Sparkles className="w-3 h-3" style={{ width: 12, height: 12 }} />{p}</div>
        ))}
      </div>

      {/* AI Success Manager — următoarea acțiune cu cel mai mare impact */}
      {na && (
        <a href={na.cta_path} className="block rounded-3xl border-2 border-[#D2F2DC] bg-[#F0FBF4] p-4" data-testid="pb-next-action">
          <div className="text-[10px] font-black uppercase tracking-wider text-[#166534] mb-1">Pasul cu cel mai mare impact</div>
          <div className="text-sm font-black text-slate-900">{na.title}</div>
          <div className="text-xs text-slate-500 mt-0.5">{na.value}</div>
          <div className="text-xs font-bold text-[#166534] mt-1.5 flex items-center gap-1">Continuă <ChevronRight className="w-3.5 h-3.5" /></div>
        </a>
      )}

      {sm?.community_action && (
        <a href={sm.community_action.cta_path} className="block rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid="pb-community-action">
          <div className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">Pentru comunitatea ta</div>
          <div className="text-sm font-black text-slate-900">{sm.community_action.title}</div>
          <div className="text-xs text-slate-500 mt-0.5">{sm.community_action.value}</div>
        </a>
      )}

      {msg && (
        <div className={`text-xs font-bold rounded-2xl px-4 py-3 ${msg.ok ? "bg-[#F0FBF4] text-[#166534]" : "bg-rose-50 text-rose-600"}`} data-testid="pb-message">
          {msg.text}
        </div>
      )}

      {/* Oportunități */}
      <div>
        <div className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Oportunitățile tale ({data.opportunities.length})</div>
        {data.opportunities.length === 0 && (
          <div className="rounded-2xl border border-slate-100 bg-white p-5 text-center text-xs text-slate-400" data-testid="pb-opp-empty">
            Nicio oportunitate activă pentru profilul tău acum — completează Cartea casei sau activează Digital Twin pentru a debloca beneficii.
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="pb-opportunities">
          {data.opportunities.map(o => <OppCard key={o.campaign_id} o={o} onClaim={claim} claiming={claiming} />)}
        </div>
      </div>

      {/* Blocate — ce mai e nevoie */}
      {data.locked?.length > 0 && (
        <div data-testid="pb-locked">
          <div className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Aproape deblocate</div>
          <div className="space-y-2">
            {data.locked.map(o => (
              <div key={o.campaign_id} className="flex items-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-3.5">
                <Lock className="w-4 h-4 text-slate-300 shrink-0" />
                <div className="min-w-0">
                  <div className="text-[13px] font-bold text-slate-500 truncate">{o.title}</div>
                  <div className="text-[11px] text-slate-400">Necesită: {(o.unlock || []).join(" · ")}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Portofelul de beneficii */}
      {wallet && (
        <div data-testid="pb-wallet">
          <div className="flex items-center gap-2 mb-2">
            <div className="text-xs font-black uppercase tracking-wider text-slate-400 flex-1">Portofelul de beneficii</div>
            {["available", "used", "expired"].map(t => (
              <button key={t} onClick={() => setWalletTab(t)}
                className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${walletTab === t ? "bg-slate-900 text-white" : "bg-slate-50 text-slate-400"}`}
                data-testid={`pb-wallet-tab-${t}`}>
                {t === "available" ? `Active (${wallet.counts.available || 0})` : t === "used" ? `Folosite (${wallet.counts.used || 0})` : `Expirate (${wallet.counts.expired || 0})`}
              </button>
            ))}
          </div>
          <div className="space-y-2" data-testid="pb-wallet-list">
            {(wallet[walletTab] || []).length === 0 && (
              <div className="rounded-2xl border border-slate-100 bg-white p-4 text-center text-xs text-slate-400">
                {walletTab === "available" ? "Niciun beneficiu activ încă — activează o oportunitate de mai sus." : "Nimic aici încă."}
              </div>
            )}
            {(wallet[walletTab] || []).map(b => <BenefitRow key={b.id} b={b} onUse={useIt} using={using} />)}
          </div>
        </div>
      )}

      {/* Ambassador — statutul tău în comunitate */}
      <AmbassadorCard />

      {/* Community Deals — negocierea comunității */}
      <CommunityDealsSection />
    </div>
  );
};
