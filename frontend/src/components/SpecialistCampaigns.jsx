import React, { useEffect, useState } from "react";
import axios from "axios";
import { Building2, Send, Check } from "lucide-react";
import { API } from "../pages/DashShared";
import { formatApiError } from "../auth";
import { PMCard, PMSectionHeader, PMChip, PMPillButton } from "./pm";

const OfferForm = ({ campaign, onSent }) => {
  const [price, setPrice] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/campaigns/${campaign.id}/offer`, {
        price_per_unit: parseFloat(price), message: message || undefined,
      });
      onSent();
    } catch (err) { alert(formatApiError(err)); }
    finally { setLoading(false); }
  };

  return (
    <form onSubmit={submit} className="mt-3 flex gap-2 items-center flex-wrap">
      <input type="number" required min="1" step="0.01" value={price} onChange={e => setPrice(e.target.value)}
        placeholder="RON / apartament" data-testid={`camp-offer-price-${campaign.id}`}
        className="w-40 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm" />
      <input value={message} onChange={e => setMessage(e.target.value)} placeholder="Mesaj (opțional)"
        data-testid={`camp-offer-msg-${campaign.id}`}
        className="flex-1 min-w-[160px] bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm" />
      <PMPillButton variant="primary" size="sm" type="submit" disabled={loading} testid={`camp-offer-submit-${campaign.id}`}>
        <Send className="w-3.5 h-3.5 mr-1 inline" />{loading ? "..." : "Trimite oferta"}
      </PMPillButton>
    </form>
  );
};

export const SpecialistCampaigns = () => {
  const [campaigns, setCampaigns] = useState([]);

  const load = () => axios.get(`${API}/campaigns/mine`).then(r => setCampaigns(r.data?.campaigns || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  if (campaigns.length === 0) return null;

  return (
    <div className="space-y-3 mt-6 max-w-3xl" data-testid="spec-campaigns-section">
      <PMSectionHeader title={`${campaigns.length} campanii de grup`} />
      {campaigns.map(c => (
        <PMCard key={c.id} testid={`spec-campaign-${c.id}`}>
          <div className="flex items-start gap-2 flex-wrap">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <PMChip variant="info" icon={Building2}>CAMPANIE DE GRUP</PMChip>
                <span className="text-[11px] text-stone-500">{c.building_name}</span>
              </div>
              <div className="font-semibold text-sm md:text-base">{c.title}</div>
              <p className="text-xs text-stone-400 mt-1">
                {c.participants_count} {c.participants_count === 1 ? "apartament înscris" : "apartamente înscrise"} · taxă lead 0 · o singură deplasare, mai multe lucrări
              </p>
            </div>
          </div>
          {c.my_offer ? (
            <div className="mt-3 flex items-center gap-2 text-xs text-stone-300 bg-white/5 rounded-xl px-3 py-2.5" data-testid={`camp-my-offer-${c.id}`}>
              <Check className="w-4 h-4 text-emerald-400" />
              Oferta ta: <b>{c.my_offer.price_per_unit} RON/apartament</b> — poți retrimite pentru a o actualiza.
            </div>
          ) : null}
          <OfferForm campaign={c} onSent={load} />
        </PMCard>
      ))}
    </div>
  );
};
