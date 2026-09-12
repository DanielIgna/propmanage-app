import React, { useEffect, useState } from "react";
import axios from "axios";
import { Building2, Users, Search, Plus, Sparkles, Check, Megaphone } from "lucide-react";
import { API } from "../pages/DashShared";
import { formatApiError } from "../auth";
import { GREEN, CTA, Sheet } from "../pages/clientv2/ui";
import { trackIntent } from "../lib/analytics";

const ConnectSheet = ({ properties, onClose, onDone }) => {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", address: "", city: "", property_id: properties[0]?.id || "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return; }
    const t = setTimeout(() => {
      axios.get(`${API}/buildings/search`, { params: { q } }).then(r => setResults(r.data?.buildings || [])).catch(() => {});
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const join = async (bid) => {
    setLoading(true);
    try {
      await axios.post(`${API}/buildings/${bid}/join`, { property_id: form.property_id });
      trackIntent("building_joined");
      onDone();
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };

  const create = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/buildings`, form);
      trackIntent("building_created");
      onDone();
    } catch (e2) { alert(formatApiError(e2)); }
    finally { setLoading(false); }
  };

  return (
    <Sheet title="Conectează-ți blocul" onClose={onClose} testid="bh-connect-sheet">
      <div className="space-y-3">
        {properties.length > 1 && (
          <select value={form.property_id} onChange={e => setForm(f => ({ ...f, property_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="bh-connect-property">
            {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
        {!creating ? (
          <>
            <div className="relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-slate-300" />
              <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută blocul după nume sau adresă..."
                className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 py-2.5 text-sm" data-testid="bh-search" />
            </div>
            {results.map(b => (
              <button key={b.id} disabled={loading} onClick={() => join(b.id)} data-testid={`bh-join-${b.id}`}
                className="w-full flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 text-left">
                <span className="w-9 h-9 rounded-xl bg-slate-50 flex items-center justify-center shrink-0"><Building2 className="w-4 h-4 text-slate-400" /></span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-bold text-slate-900 truncate">{b.name}</span>
                  <span className="block text-[11px] text-slate-400 truncate">{b.address} · {b.members_count} {b.members_count === 1 ? "vecin" : "vecini"}</span>
                </span>
                <Plus className="w-4 h-4 text-slate-300 shrink-0" />
              </button>
            ))}
            {q.trim().length >= 2 && results.length === 0 && <p className="text-xs text-slate-400 text-center py-2">Niciun bloc găsit.</p>}
            <button onClick={() => setCreating(true)} data-testid="bh-create-toggle" className="w-full py-3 rounded-full bg-slate-50 text-xs font-bold text-slate-600">
              + Blocul meu nu există — îl creez
            </button>
          </>
        ) : (
          <form onSubmit={create} className="space-y-3">
            <input required minLength={3} placeholder="Numele blocului (ex: Bloc A4, Aviației 22)" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="bh-create-name" />
            <input required minLength={3} placeholder="Adresa" value={form.address}
              onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="bh-create-address" />
            <input placeholder="Orașul (opțional)" value={form.city}
              onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="bh-create-city" />
            <CTA testid="bh-create-submit" disabled={loading}>{loading ? "..." : "Creează blocul și conectează proprietatea"}</CTA>
            <button type="button" onClick={() => setCreating(false)} className="w-full py-2 text-xs font-bold text-slate-400">← Înapoi la căutare</button>
          </form>
        )}
      </div>
    </Sheet>
  );
};

const CampaignCard = ({ c, myPropIds, onJoin, onAccept, userId }) => {
  const bestOffer = (c.offers || []).slice().sort((a, b) => a.price_per_unit - b.price_per_unit)[0];
  const isCreator = c.created_by === userId;
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-3.5" data-testid={`bh-campaign-${c.id}`}>
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-black text-slate-900">{c.title}</div>
          <div className="text-[11px] text-slate-400">
            {c.participants_count} {c.participants_count === 1 ? "apartament înscris" : "apartamente înscrise"}
            {c.source === "auto" ? " · detectată de AI" : c.created_by_name ? ` · pornită de ${c.created_by_name.split(" ")[0]}` : ""}
          </div>
        </div>
        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${c.status === "scheduled" ? "bg-[#34C759]/10 text-[#166534]" : "bg-amber-50 text-amber-600"}`}>
          {c.status === "scheduled" ? "Programată" : "Deschisă"}
        </span>
      </div>
      {bestOffer && c.status === "open" && (
        <div className="mt-2 flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2" data-testid={`bh-offer-${c.id}`}>
          <Megaphone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="text-[11px] text-slate-600 flex-1">
            <b>{bestOffer.specialist_name}</b>: {bestOffer.price_per_unit} RON/apartament{c.offers.length > 1 ? ` (+${c.offers.length - 1} oferte)` : ""}
          </span>
        </div>
      )}
      {c.status === "scheduled" && c.accepted_offer && (
        <div className="mt-2 text-[11px] font-bold text-[#166534] bg-[#34C759]/10 rounded-xl px-3 py-2">
          ✓ {c.accepted_offer.specialist_name} — {c.accepted_offer.price_per_unit} RON/apartament
        </div>
      )}
      {c.status === "open" && (
        <div className="mt-3 flex gap-2">
          {!c.joined_by_me && (
            <button onClick={() => onJoin(c)} data-testid={`bh-join-campaign-${c.id}`}
              className="flex-1 py-2.5 rounded-full text-xs font-black text-white" style={{ background: GREEN }}>
              Particip și eu
            </button>
          )}
          {c.joined_by_me && <span className="flex-1 py-2.5 rounded-full bg-slate-50 text-xs font-bold text-slate-500 text-center flex items-center justify-center gap-1"><Check className="w-3.5 h-3.5" style={{ color: GREEN }} />Ești înscris</span>}
          {isCreator && bestOffer && (
            <button onClick={() => onAccept(c, bestOffer)} data-testid={`bh-accept-offer-${c.id}`}
              className="flex-1 py-2.5 rounded-full bg-slate-900 text-xs font-black text-white">
              Acceptă {bestOffer.price_per_unit} RON/ap.
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const BuildingHub = ({ properties = [], onRequestsChanged }) => {
  const [data, setData] = useState(null);
  const [showConnect, setShowConnect] = useState(false);
  const [invitePreview, setInvitePreview] = useState(null);
  const [joinPropId, setJoinPropId] = useState("");
  const [copiedInvite, setCopiedInvite] = useState(null);

  const load = () => axios.get(`${API}/buildings/mine`).then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  useEffect(() => {
    const bid = localStorage.getItem("pm_building_invite");
    if (!bid || !data) return;
    if ((data.buildings || []).some(b => b.id === bid)) { localStorage.removeItem("pm_building_invite"); return; }
    axios.get(`${API}/buildings/${bid}/preview`).then(r => {
      setInvitePreview(r.data);
      setJoinPropId(properties[0]?.id || "");
    }).catch(() => localStorage.removeItem("pm_building_invite"));
  }, [data, properties]);

  if (!data || properties.length === 0) return null;
  const buildings = data.buildings || [];

  const acceptInvite = async () => {
    try {
      await axios.post(`${API}/buildings/${invitePreview.id}/join`, { property_id: joinPropId });
      trackIntent("building_invite_claimed");
      localStorage.removeItem("pm_building_invite");
      setInvitePreview(null);
      load();
    } catch (e) { alert(formatApiError(e)); }
  };
  const copyInviteLink = async (b) => {
    const link = `${window.location.origin}/register?binvite=${b.id}`;
    try { await navigator.clipboard.writeText(`Blocul nostru e pe PropManage — conectează-ți apartamentul: ${link}`); setCopiedInvite(b.id); setTimeout(() => setCopiedInvite(null), 2000); } catch {}
    trackIntent("building_invite_shared");
  };

  const joinCampaign = async (c, building) => {
    const pid = building.my_property_ids[0];
    try {
      await axios.post(`${API}/campaigns/${c.id}/join`, { property_id: pid });
      trackIntent("campaign_joined");
      load();
    } catch (e) { alert(formatApiError(e)); }
  };
  const acceptOffer = async (c, offer) => {
    if (!window.confirm(`Accepți oferta lui ${offer.specialist_name} (${offer.price_per_unit} RON/apartament)? Se creează automat lucrările pentru toți participanții.`)) return;
    try {
      const { data: r } = await axios.post(`${API}/campaigns/${c.id}/accept-offer`, { specialist_id: offer.specialist_id });
      trackIntent("campaign_offer_accepted");
      alert(`Campanie programată — ${r.requests_created} lucrări create.`);
      load(); onRequestsChanged?.();
    } catch (e) { alert(formatApiError(e)); }
  };
  const startCampaign = async (building, opp) => {
    try {
      await axios.post(`${API}/campaigns`, {
        building_id: building.id, category: opp.category, property_id: building.my_property_ids[0],
      });
      trackIntent("campaign_created");
      load();
    } catch (e) { alert(formatApiError(e)); }
  };

  return (
    <div className="px-5 pt-6 pb-4 lg:max-w-3xl" data-testid="bh-section">
      <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 px-1 flex items-center gap-1.5">
        <Building2 className="w-3.5 h-3.5" style={{ color: GREEN }} /> Blocul meu
      </h3>
      {invitePreview && (
        <div className="mt-3 rounded-3xl border-2 border-[#34C759]/40 bg-[#34C759]/5 p-4" data-testid="bh-invite-banner">
          <div className="text-sm font-black text-slate-900">Ai fost invitat în „{invitePreview.name}"</div>
          <p className="mt-1 text-xs text-slate-500">{invitePreview.address} · {invitePreview.members_count} {invitePreview.members_count === 1 ? "vecin conectat" : "vecini conectați"}. Conectează-ți apartamentul pentru anunțuri, calendar comun și campanii de grup.</p>
          <div className="mt-3 flex gap-2 items-center flex-wrap">
            {properties.length > 1 && (
              <select value={joinPropId} onChange={e => setJoinPropId(e.target.value)} data-testid="bh-invite-property"
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold">
                {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
            <button onClick={acceptInvite} data-testid="bh-invite-accept"
              className="px-5 py-2.5 rounded-full text-xs font-black text-white" style={{ background: GREEN }}>Mă alătur blocului</button>
            <button onClick={() => { localStorage.removeItem("pm_building_invite"); setInvitePreview(null); }} data-testid="bh-invite-dismiss"
              className="px-4 py-2.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-500">Nu acum</button>
          </div>
        </div>
      )}
      {buildings.length === 0 ? (
        <button onClick={() => setShowConnect(true)} data-testid="bh-empty-cta"
          className="mt-3 w-full rounded-3xl border-2 border-dashed border-slate-200 bg-white p-5 text-left">
          <div className="text-sm font-black text-slate-900">Mentenanță împreună cu vecinii = prețuri mai bune</div>
          <p className="mt-1 text-xs text-slate-400">Conectează-ți blocul: când mai multe apartamente au aceeași revizie, porniți o campanie comună și specialiștii oferă preț de grup.</p>
          <span className="mt-3 inline-block text-xs font-bold" style={{ color: GREEN }}>Conectează blocul →</span>
        </button>
      ) : buildings.map(b => (
        <div key={b.id} className="mt-3 rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid={`bh-building-${b.id}`}>
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-2xl bg-slate-50 flex items-center justify-center shrink-0"><Building2 className="w-5 h-5" style={{ color: GREEN }} /></span>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-black text-slate-900 truncate">{b.name}</div>
              <div className="text-[11px] text-slate-400 flex items-center gap-1"><Users className="w-3 h-3" /> {b.members_count} {b.members_count === 1 ? "vecin conectat" : "vecini conectați"} · {b.properties_count} apartamente</div>
            </div>
            <button onClick={() => copyInviteLink(b)} data-testid={`bh-share-${b.id}`}
              className="shrink-0 px-3 py-2 rounded-full bg-slate-50 border border-slate-100 text-[10px] font-bold text-slate-500 flex items-center gap-1">
              {copiedInvite === b.id ? <Check className="w-3 h-3" style={{ color: GREEN }} /> : <Plus className="w-3 h-3" />}
              {copiedInvite === b.id ? "Copiat" : "Invită vecini"}
            </button>
          </div>
          {b.is_admin && (
            <a href="/administrator" data-testid={`bh-admin-link-${b.id}`}
              className="mt-3 flex items-center justify-between rounded-2xl bg-slate-900 px-4 py-3 text-white">
              <span className="text-xs font-black">🏢 Administrare bloc — dashboard, locatari, anunțuri</span>
              <span className="text-xs font-black">→</span>
            </a>
          )}
          {(b.announcements || []).length > 0 && (
            <div className="mt-3 space-y-1.5" data-testid={`bh-announcements-${b.id}`}>
              {b.announcements.map(a => (
                <div key={a.id} className="rounded-xl bg-slate-50 px-3 py-2">
                  <div className="text-[11px] font-black text-slate-800">📢 {a.title}</div>
                  <div className="text-[10px] text-slate-500 line-clamp-2">{a.body}</div>
                </div>
              ))}
            </div>
          )}
          {(b.opportunities || []).length > 0 && (
            <div className="mt-3 space-y-2">
              {b.opportunities.map(opp => (
                <div key={opp.category} className="flex items-center gap-2.5 rounded-2xl border border-amber-100 bg-amber-50/60 p-3" data-testid={`bh-opp-${opp.category}`}>
                  <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
                  <span className="text-[11px] text-slate-600 flex-1 leading-snug">
                    <b>{opp.properties} apartamente</b> au „{opp.category_label}" scadentă în ≤60 zile — porniți o campanie de grup.
                  </span>
                  <button onClick={() => startCampaign(b, opp)} data-testid={`bh-start-campaign-${opp.category}`}
                    className="shrink-0 px-3 py-2 rounded-full bg-slate-900 text-white text-[10px] font-black">Pornește</button>
                </div>
              ))}
            </div>
          )}
          {(b.campaigns || []).length > 0 && (
            <div className="mt-3 space-y-2">
              {b.campaigns.map(c => (
                <CampaignCard key={c.id} c={c} myPropIds={b.my_property_ids} userId={data.me}
                  onJoin={(cc) => joinCampaign(cc, b)} onAccept={acceptOffer} />
              ))}
            </div>
          )}
          {(b.campaigns || []).length === 0 && (b.opportunities || []).length === 0 && (
            <p className="mt-3 text-[11px] text-slate-400">Nicio campanie activă. Adaugă revizii în calendarul de mentenanță — detectăm automat scadențele comune cu vecinii.</p>
          )}
        </div>
      ))}
      {buildings.length > 0 && properties.some(p => !(data.my_properties || []).find(mp => mp.id === p.id)?.building_id) && (
        <button onClick={() => setShowConnect(true)} data-testid="bh-connect-more" className="mt-2 w-full py-2.5 rounded-full bg-slate-50 text-xs font-bold text-slate-500">
          + Conectează altă proprietate la un bloc
        </button>
      )}
      {showConnect && <ConnectSheet properties={properties} onClose={() => setShowConnect(false)}
        onDone={() => { setShowConnect(false); load(); }} />}
    </div>
  );
};
