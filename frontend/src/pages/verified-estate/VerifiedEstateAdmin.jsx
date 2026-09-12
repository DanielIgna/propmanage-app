import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Box, FileText, AlertTriangle, CheckCircle2, Archive,
  Eye, Sparkles, Building2, Loader2, ExternalLink, Mail, RefreshCcw, Banknote, Trophy
} from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const STAGES = [
  { key: "draft", label: "Draft", color: "stone", desc: "În pregătire" },
  { key: "pending_review", label: "Pending Review", color: "amber", desc: "Așteaptă aprobare" },
  { key: "published", label: "Published", color: "lime", desc: "LIVE pentru public" },
  { key: "sold", label: "Sold", color: "cyan", desc: "Vândut · comision încasat" },
  { key: "archived", label: "Archived", color: "red", desc: "Retras / inactiv" },
];

const GateChip = ({ ok, label }) => (
  <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${ok ? "bg-emerald-500/15 text-emerald-300" : "bg-red-500/15 text-red-300"}`}>
    {ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
    {label}
  </span>
);

const ListingCard = ({ item, onPublish, onArchive, onMarkSold, busy }) => {
  const gates = item.gates_status || {};
  const canPublish = Object.values(gates).every(g => g?.ok);
  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-4 mb-3" data-testid={`kanban-card-${item.id}`}>
      <div className="flex items-start gap-3 mb-3">
        {item.cover_image_url ? (
          <img src={item.cover_image_url} alt={item.title} className="w-14 h-14 rounded-lg object-cover shrink-0" />
        ) : (
          <div className="w-14 h-14 rounded-lg bg-stone-800 flex items-center justify-center shrink-0"><Building2 className="w-5 h-5 text-stone-600" /></div>
        )}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm leading-tight line-clamp-2 mb-1">{item.title}</div>
          <div className="text-[11px] text-stone-400">{item.city}</div>
          <div className="text-[11px] font-medium text-[#d4ff3a] mt-0.5">
            {Number(item.price_ron).toLocaleString("ro-RO")} RON · {item.transaction_type === "rent" ? "Închiriere" : "Vânzare"}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-1 mb-3">
        <GateChip ok={gates.gate_1_audit?.ok} label="Audit" />
        <GateChip ok={gates.gate_2_twin?.ok} label="Twin" />
        <GateChip ok={gates.gate_3_recommendations?.ok} label={`Reco ${item.recommendations_pct || 0}%`} />
      </div>
      {item.status === "sold" && item.sale_price_ron != null && (
        <div className="text-[11px] text-cyan-300 mb-2" data-testid={`kanban-sale-info-${item.id}`}>
          🏆 Vândut: {Number(item.sale_price_ron).toLocaleString("ro-RO")} RON · Comision net: {Number(item.commission_net_ron || 0).toLocaleString("ro-RO")} RON
        </div>
      )}
      <div className="flex gap-1.5">
        <Link to={`/imobile-verificate/${item.id}`} target="_blank" className="pm-btn pm-btn-ghost pm-btn-sm" data-testid={`kanban-view-${item.id}`}>
          <Eye className="w-3.5 h-3.5" /> Vezi
        </Link>
        {["draft", "pending_review"].includes(item.status) && (
          <button onClick={() => onPublish(item.id)} disabled={!canPublish || busy === item.id} className="pm-btn pm-btn-success pm-btn-sm" data-testid={`kanban-publish-${item.id}`} title={canPublish ? "" : "Toate Gate-urile trebuie validate"}>
            {busy === item.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            Publish
          </button>
        )}
        {item.status === "published" && (
          <button onClick={() => onMarkSold(item)} disabled={busy === item.id} className="pm-btn pm-btn-success pm-btn-sm" data-testid={`kanban-sold-${item.id}`}>
            {busy === item.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Banknote className="w-3.5 h-3.5" />}
            Vândut
          </button>
        )}
        {!["archived", "sold"].includes(item.status) && (
          <button onClick={() => onArchive(item.id)} disabled={busy === item.id} className="pm-btn pm-btn-danger pm-btn-sm" data-testid={`kanban-archive-${item.id}`}>
            <Archive className="w-3.5 h-3.5" /> Archive
          </button>
        )}
      </div>
    </div>
  );
};

const StatCard = ({ icon: Icon, color, value, label }) => (
  <div className="pm-stat-card">
    <div className={`pm-stat-icon-badge bg-${color}-500/15 text-${color}-400 border border-${color}-500/30`}>
      <Icon className="w-5 h-5" />
    </div>
    <div className="font-serif text-3xl mb-1">{value}</div>
    <div className="text-xs text-stone-400">{label}</div>
  </div>
);

export const VerifiedEstateAdmin = () => {
  const [tab, setTab] = useState("kanban");
  const [stats, setStats] = useState(null);
  const [listings, setListings] = useState([]);
  const [inquiries, setInquiries] = useState([]);
  const [external, setExternal] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, l, i, e, o] = await Promise.all([
        axios.get(`${API}/api/verified-estate/admin/stats`, { withCredentials: true }),
        axios.get(`${API}/api/verified-estate/admin/listings?limit=200`, { withCredentials: true }),
        axios.get(`${API}/api/verified-estate/admin/inquiries?limit=50`, { withCredentials: true }),
        axios.get(`${API}/api/verified-estate/admin/external-requests?limit=50`, { withCredentials: true }),
        axios.get(`${API}/api/verified-estate/admin/orders?limit=50`, { withCredentials: true }),
      ]);
      setStats(s.data);
      setListings(l.data?.items || []);
      setInquiries(i.data?.items || []);
      setExternal(e.data?.items || []);
      setOrders(o.data?.items || []);
    } catch (err) {
      console.error("Failed to load admin data", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const publish = async (id) => {
    setBusy(id);
    try {
      await axios.post(`${API}/api/verified-estate/admin/listings/${id}/publish`, {}, { withCredentials: true });
      await load();
    } catch (err) {
      const data = err?.response?.data?.detail;
      alert(typeof data === "string" ? data : JSON.stringify(data, null, 2));
    } finally {
      setBusy(null);
    }
  };

  const archive = async (id) => {
    if (!window.confirm("Arhivezi acest listing? Nu va mai fi vizibil cumpărătorilor.")) return;
    setBusy(id);
    try {
      await axios.post(`${API}/api/verified-estate/admin/listings/${id}/archive`, {}, { withCredentials: true });
      await load();
    } finally {
      setBusy(null);
    }
  };

  const markSold = async (item) => {
    const price = window.prompt(`Preț final de vânzare (RON) pentru:\n${item.title}`, item.price_ron);
    if (price == null) return;
    const v = parseFloat(price);
    if (!v || v <= 0) { alert("Preț invalid."); return; }
    if (!window.confirm(`Confirmi vânzarea la ${v.toLocaleString("ro-RO")} RON? Se calculează comisionul și listingul devine SOLD.`)) return;
    setBusy(item.id);
    try {
      await axios.post(`${API}/api/verified-estate/admin/listings/${item.id}/mark-sold`, { sale_price_ron: v }, { withCredentials: true });
      await load();
    } catch (err) {
      const data = err?.response?.data?.detail;
      alert(typeof data === "string" ? data : JSON.stringify(data, null, 2));
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă...</div>;
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-12">
        <div className="flex items-start justify-between mb-8 flex-wrap gap-3">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">
              ← Înapoi la Admin
            </Link>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="admin-ve-title">
              Imobile Verificate · <span className="italic gradient-text">Admin</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2">Moderează listings, urmărește cereri și plăți audit/Twin.</p>
          </div>
          <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="admin-ve-refresh">
            <RefreshCcw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-8">
            <StatCard icon={Building2} color="violet" value={stats.listings_total} label="Total listings" />
            <StatCard icon={CheckCircle2} color="emerald" value={stats.listings_published} label="Publicate" />
            <StatCard icon={FileText} color="amber" value={stats.listings_draft} label="Draft" />
            <StatCard icon={Trophy} color="cyan" value={stats.listings_sold || 0} label="Vândute" />
            <StatCard icon={Banknote} color="lime" value={`${Number(stats.commission_net_total_ron || 0).toLocaleString("ro-RO")}`} label="Comision net (RON)" />
            <StatCard icon={Mail} color="cyan" value={stats.inquiries_new} label="Cereri noi" />
            <StatCard icon={ExternalLink} color="pink" value={stats.external_requests_new} label="Audit extern" />
            <StatCard icon={Sparkles} color="lime" value={orders.filter(o => o.status === "paid").length} label="Plăți" />
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-white/5">
          {[
            { k: "kanban", l: "Kanban Moderation" },
            { k: "inquiries", l: `Cereri (${inquiries.length})` },
            { k: "external", l: `Audit Extern (${external.length})` },
            { k: "orders", l: `Plăți (${orders.length})` },
          ].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)} className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${tab === t.k ? "text-[#d4ff3a] border-[#d4ff3a]" : "text-stone-400 border-transparent hover:text-white"}`} data-testid={`admin-tab-${t.k}`}>
              {t.l}
            </button>
          ))}
        </div>

        {/* Kanban Board */}
        {tab === "kanban" && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
            {STAGES.map(stage => {
              const stageItems = listings.filter(l => l.status === stage.key);
              return (
                <div key={stage.key} className="bg-white/[0.02] border border-white/5 rounded-2xl p-4" data-testid={`kanban-col-${stage.key}`}>
                  <div className="flex items-center justify-between mb-3 pb-3 border-b border-white/5">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full bg-${stage.color}-400`} />
                      <h3 className="font-medium text-sm">{stage.label}</h3>
                    </div>
                    <span className="text-xs text-stone-400">{stageItems.length}</span>
                  </div>
                  <div className="text-[11px] text-stone-500 mb-3">{stage.desc}</div>
                  {stageItems.length === 0 ? (
                    <div className="text-center text-xs text-stone-600 py-8">Niciun listing</div>
                  ) : (
                    stageItems.map(it => <ListingCard key={it.id} item={it} onPublish={publish} onArchive={archive} onMarkSold={markSold} busy={busy} />)
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Inquiries */}
        {tab === "inquiries" && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-xs text-stone-400 uppercase tracking-wider">
                <tr><th className="text-left p-3">Nume</th><th className="text-left p-3">Email</th><th className="text-left p-3">Intent</th><th className="text-left p-3">Imobil</th><th className="text-left p-3">Data</th></tr>
              </thead>
              <tbody>
                {inquiries.map(i => (
                  <tr key={i.id} className="border-t border-white/5" data-testid={`inquiry-row-${i.id}`}>
                    <td className="p-3">{i.name}</td>
                    <td className="p-3 text-stone-400">{i.email}</td>
                    <td className="p-3"><span className="text-xs bg-white/5 px-2 py-0.5 rounded">{i.intent}</span></td>
                    <td className="p-3 text-xs text-stone-400">{i.listing_title}</td>
                    <td className="p-3 text-xs text-stone-500">{new Date(i.created_at).toLocaleString("ro-RO")}</td>
                  </tr>
                ))}
                {inquiries.length === 0 && <tr><td colSpan={5} className="text-center p-8 text-stone-500">Nicio cerere încă.</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {/* External requests */}
        {tab === "external" && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-xs text-stone-400 uppercase tracking-wider">
                <tr><th className="text-left p-3">Nume</th><th className="text-left p-3">Email</th><th className="text-left p-3">Adresă</th><th className="text-left p-3">URL Extern</th><th className="text-left p-3">Data</th></tr>
              </thead>
              <tbody>
                {external.map(e => (
                  <tr key={e.id} className="border-t border-white/5" data-testid={`ext-row-${e.id}`}>
                    <td className="p-3">{e.contact_name}</td>
                    <td className="p-3 text-stone-400">{e.contact_email}</td>
                    <td className="p-3 text-xs">{e.property_address}</td>
                    <td className="p-3 text-xs"><a href={e.external_listing_url} target="_blank" rel="noopener noreferrer" className="text-[#d4ff3a] hover:underline">Link <ExternalLink className="w-3 h-3 inline" /></a></td>
                    <td className="p-3 text-xs text-stone-500">{new Date(e.created_at).toLocaleString("ro-RO")}</td>
                  </tr>
                ))}
                {external.length === 0 && <tr><td colSpan={5} className="text-center p-8 text-stone-500">Nicio cerere externă încă.</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {/* Orders */}
        {tab === "orders" && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-xs text-stone-400 uppercase tracking-wider">
                <tr><th className="text-left p-3">Pachet</th><th className="text-left p-3">Sumă</th><th className="text-left p-3">Status</th><th className="text-left p-3">Email</th><th className="text-left p-3">Adresă</th><th className="text-left p-3">Data</th></tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id} className="border-t border-white/5" data-testid={`order-row-${o.id}`}>
                    <td className="p-3"><span className="text-xs bg-white/5 px-2 py-0.5 rounded">{o.package}</span></td>
                    <td className="p-3 font-medium">{Number(o.amount_ron).toLocaleString("ro-RO")} RON</td>
                    <td className="p-3"><span className={`text-xs px-2 py-0.5 rounded ${o.status === "paid" ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>{o.status}</span>{o.demo_mode && <span className="text-[10px] text-amber-300 ml-1">DEMO</span>}</td>
                    <td className="p-3 text-stone-400">{o.contact_email}</td>
                    <td className="p-3 text-xs">{o.property_address}</td>
                    <td className="p-3 text-xs text-stone-500">{new Date(o.created_at).toLocaleString("ro-RO")}</td>
                  </tr>
                ))}
                {orders.length === 0 && <tr><td colSpan={6} className="text-center p-8 text-stone-500">Nicio comandă încă.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default VerifiedEstateAdmin;
