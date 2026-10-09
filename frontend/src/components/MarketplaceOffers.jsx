// Sprint C — Specialist offer apply form + Client offers browse list with hybrid ranking.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Star, Loader2, X, Crown, Trophy, Award, ChevronRight,
  DollarSign, TrendingUp, Clock, Filter, AlertTriangle, CheckCircle2,
} from "lucide-react";
import { RatingBadge } from "./RatingBadge";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;

// ============= SPONSORED BADGE =============
export const SponsoredBadge = ({ size = "sm" }) => {
  const sz = size === "lg" ? "text-sm px-2.5 py-1" : "text-[10px] px-2 py-0.5";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 font-medium uppercase tracking-wider ${sz}`} data-testid="sponsored-badge" title="Specialist sponsorizat — a plătit fee priority pentru poziție vizibilă">
      <Crown className="w-3 h-3" /> Sponsorizat
    </span>
  );
};


// ============= TIER BADGE =============
const TierBadge = ({ tier }) => {
  const cfg = {
    PREMIUM: { c: "text-fuchsia-300 bg-fuchsia-500/15 border-fuchsia-500/30", icon: Crown, label: "Premium" },
    VERIFIED: { c: "text-[#d4ff3a] bg-[#d4ff3a]/15 border-[#d4ff3a]/30", icon: Award, label: "Verified" },
    ENTRY: { c: "text-stone-400 bg-stone-500/10 border-stone-500/20", icon: Trophy, label: "Entry" },
  }[tier || "ENTRY"];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${cfg.c}`}>
      <Icon className="w-3 h-3" /> {cfg.label}
    </span>
  );
};


// ============= SPECIALIST: APPLY TO REQUEST =============
export const OfferApplyForm = ({ requestId, onClose, onSubmit }) => {
  const [fee, setFee] = useState(5);
  const [priority, setPriority] = useState(0);
  const [message, setMessage] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [hours, setHours] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(null);

  const total = (parseFloat(fee) || 0) + (parseFloat(priority) || 0);

  const submit = async () => {
    setSubmitting(true); setError("");
    try {
      const { data } = await axios.post(`${API}/api/requests/${requestId}/offers`, {
        fee_ron: parseFloat(fee), priority_fee_ron: parseFloat(priority || 0),
        message, proposed_start_date: startDate || null, proposed_end_date: endDate || null,
        estimated_hours: hours ? parseFloat(hours) : null,
      });
      setSuccess(data);
      onSubmit && onSubmit(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la trimitere");
    } finally { setSubmitting(false); }
  };

  if (success) {
    return (
      <div className="glass-strong rounded-3xl max-w-lg w-full p-8 text-center" data-testid="offer-apply-success">
        <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-3" />
        <h3 className="font-serif text-2xl mb-2">Ofertă trimisă!</h3>
        <p className="text-sm text-stone-400 mb-4">Fee total plătit: <strong className="text-[#d4ff3a]">{success.fee_paid} RON</strong></p>
        <p className="text-xs text-stone-500 mb-5">Clientul va vedea oferta ta. Vei fi notificat dacă e acceptată sau respinsă.</p>
        <button onClick={onClose} className="btn-accent px-6 py-2.5 rounded-xl text-sm font-medium" data-testid="offer-done">Închide</button>
      </div>
    );
  }

  return (
    <div className="glass-strong rounded-3xl max-w-xl w-full max-h-[90vh] overflow-y-auto" data-testid="offer-apply-form">
      <div className="p-6 border-b border-white/10 flex items-center justify-between sticky top-0 bg-[#0a0a0b]/95 backdrop-blur-xl">
        <div>
          <h3 className="font-serif text-2xl">Aplică la cerere</h3>
          <p className="text-xs text-stone-400 mt-1">Fee minim 5 RON, maxim 50 RON. Priority fee = boost vizibil "🏆 Sponsorizat".</p>
        </div>
        <button onClick={onClose} className="text-stone-400 hover:text-stone-200" data-testid="offer-apply-close"><X className="w-5 h-5" /></button>
      </div>
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase text-stone-500 mb-1 block">Fee base (RON) <span className="text-red-400">*</span></label>
            <input type="number" min="5" max="50" step="1" value={fee} onChange={e => setFee(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="offer-fee" />
          </div>
          <div>
            <label className="text-xs uppercase text-stone-500 mb-1 block">Priority fee (opțional)</label>
            <input type="number" min="0" max="50" step="1" value={priority} onChange={e => setPriority(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="offer-priority-fee" />
            <div className="text-[10px] text-stone-500 mt-1">{priority > 0 ? "Veți primi badge 🏆 Sponsorizat" : "Fără badge sponsor"}</div>
          </div>
        </div>
        <div className="bg-[#d4ff3a]/5 border border-[#d4ff3a]/20 rounded-xl p-3 text-xs flex items-center justify-between">
          <span className="text-stone-300">Total de plată acum:</span>
          <span className="text-[#d4ff3a] font-bold text-lg tabular-nums" data-testid="offer-total">{total} RON</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase text-stone-500 mb-1 block">Start propus</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="offer-start" />
          </div>
          <div>
            <label className="text-xs uppercase text-stone-500 mb-1 block">Sfârșit propus</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="offer-end" />
          </div>
        </div>
        <div>
          <label className="text-xs uppercase text-stone-500 mb-1 block">Ore estimate (opțional)</label>
          <input type="number" min="0" step="0.5" value={hours} onChange={e => setHours(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="offer-hours" />
        </div>
        <div>
          <label className="text-xs uppercase text-stone-500 mb-1 block">Mesaj pentru client (opțional, max 1000)</label>
          <textarea value={message} onChange={e => setMessage(e.target.value)} maxLength={1000} rows={3} placeholder="Prezintă experiența ta sau oferta..." className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm resize-none" data-testid="offer-message" />
        </div>
        {error && <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2" data-testid="offer-error">{error}</div>}
        <button onClick={submit} disabled={submitting || total < 5} className="btn-accent w-full py-3 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2" data-testid="offer-submit">
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
          Trimite oferta ({total} RON din wallet)
        </button>
      </div>
    </div>
  );
};


// ============= CLIENT: BROWSE OFFERS =============
export const OffersList = ({ requestId }) => {
  const [data, setData] = useState(null);
  const [sort, setSort] = useState("hybrid");
  const [accepting, setAccepting] = useState(null);
  const navigate = useNavigate();

  const load = () => axios.get(`${API}/api/requests/${requestId}/offers?sort=${sort}`).then(r => setData(r.data)).catch(() => setData({ items: [], error: true }));
  useEffect(() => { load(); }, [requestId, sort]);

  const accept = async (offerId) => {
    if (!window.confirm("Confirmi alegerea acestui specialist? Celelalte oferte vor fi marcate ca pierdute.")) return;
    setAccepting(offerId);
    try {
      const { data: r } = await axios.post(`${API}/api/requests/${requestId}/offers/${offerId}/accept`);
      alert(`Specialist ales: ${r.specialist_name}. Te redirecționăm la cerere.`);
      navigate(`/client/requests/${requestId}`);
    } catch (e) {
      alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally { setAccepting(null); }
  };

  if (!data) return <Loader2 className="w-6 h-6 animate-spin text-[#d4ff3a]" />;
  if (data.error) return <div className="text-red-300 text-sm">Eroare la încărcarea ofertelor</div>;

  return (
    <div className="space-y-4" data-testid="offers-list">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-serif text-2xl">Oferte primite ({data.total})</h3>
        <div className="flex items-center gap-1.5 text-xs">
          <Filter className="w-3.5 h-3.5 text-stone-400" />
          <span className="text-stone-400">Sortează după:</span>
          {[
            { id: "hybrid", label: "Recomandat" },
            { id: "rating", label: "Rating" },
            { id: "fee", label: "Fee" },
            { id: "newest", label: "Nou" },
          ].map(s => (
            <button key={s.id} onClick={() => setSort(s.id)} className={`px-2.5 py-1 rounded-full text-xs ${sort === s.id ? "bg-[#d4ff3a] text-black font-semibold" : "bg-white/5 text-stone-300 hover:bg-white/10"}`} data-testid={`offers-sort-${s.id}`}>{s.label}</button>
          ))}
        </div>
      </div>

      {sort === "hybrid" && data.ranking_policy && (
        <div className="text-[10px] text-stone-500 bg-white/3 px-3 py-1.5 rounded-lg flex items-center gap-1.5" data-testid="ranking-policy-note">
          <TrendingUp className="w-3 h-3" /> {data.ranking_policy}
        </div>
      )}

      {data.items.length === 0 && (
        <div className="glass rounded-2xl p-8 text-center text-stone-500 text-sm">
          Nicio ofertă încă. Specialiștii vor aplica în următoarele ore.
        </div>
      )}

      {data.items.map((o, idx) => (
        <div key={o.id} className={`glass rounded-2xl p-5 ${o.badge === "sponsored" ? "border-amber-500/40 bg-amber-500/3" : ""}`} data-testid={`offer-card-${o.id}`}>
          <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-stone-500 text-xs">#{idx + 1}</span>
              <div className="font-semibold text-base">{o.specialist?.name}</div>
              <TierBadge tier={o.specialist?.tier} />
              {o.badge === "sponsored" && <SponsoredBadge />}
              {o.specialist?.low_rating_warning && (
                <span className="inline-flex items-center gap-1 text-[10px] bg-red-500/10 border border-red-500/30 text-red-300 px-2 py-0.5 rounded-full" data-testid="low-rating-warning">
                  <AlertTriangle className="w-2.5 h-2.5" /> Rating sub medie — verifică recenziile
                </span>
              )}
            </div>
            <RatingBadge rating={o.specialist?.rating} reviewsCount={o.specialist?.reviews_count || 0} showWarning={false} />
          </div>

          {o.message && <p className="text-sm text-stone-300 mb-3">{o.message}</p>}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs mb-4">
            <div className="bg-white/5 rounded-lg p-2">
              <div className="text-[10px] text-stone-500 uppercase">Fee plătit</div>
              <div className="text-stone-100 font-semibold tabular-nums">{o.total_fee_ron} RON</div>
            </div>
            {o.proposed_start_date && (
              <div className="bg-white/5 rounded-lg p-2">
                <div className="text-[10px] text-stone-500 uppercase">Start</div>
                <div className="text-stone-100">{new Date(o.proposed_start_date).toLocaleDateString("ro-RO")}</div>
              </div>
            )}
            {o.proposed_end_date && (
              <div className="bg-white/5 rounded-lg p-2">
                <div className="text-[10px] text-stone-500 uppercase">Final</div>
                <div className="text-stone-100">{new Date(o.proposed_end_date).toLocaleDateString("ro-RO")}</div>
              </div>
            )}
            {o.estimated_hours && (
              <div className="bg-white/5 rounded-lg p-2">
                <div className="text-[10px] text-stone-500 uppercase">Ore</div>
                <div className="text-stone-100 tabular-nums">{o.estimated_hours}h</div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-2 flex-wrap">
            <button onClick={() => navigate(`/specialist/${o.specialist_id}`)} className="text-xs text-stone-400 hover:text-stone-200 flex items-center gap-1" data-testid={`offer-view-profile-${o.id}`}>
              Profil specialist <ChevronRight className="w-3 h-3" />
            </button>
            <button onClick={() => accept(o.id)} disabled={accepting === o.id} className="btn-accent px-5 py-2 rounded-lg text-xs font-medium flex items-center gap-2 disabled:opacity-50" data-testid={`offer-accept-${o.id}`}>
              {accepting === o.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              Alege această ofertă
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default OffersList;
