// Strategic Partners Dashboard — unified view of City + Marketplace ecosystems
// + AI Cross-Reference Engine that suggests connections between programs.
// Route: /admin/strategic-partners
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Network, Building2, ShoppingBag, TrendingUp, Users, ChevronLeft, Loader2,
  Sparkles, ArrowRight, Mail, Copy, Zap, AlertTriangle, MapPin, CheckCircle2,
  AlertCircle, X,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const StatCard = ({ icon: Icon, label, value, color, bg }) => (
  <div className={`rounded-xl p-4 border ${bg || "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800"}`}>
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <Icon className={`w-4 h-4 ${color}`} />
    </div>
    <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
  </div>
);

const CrossRefModal = ({ lead, onClose, onDone }) => {
  const [busy, setBusy] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    ax.post(`/api/admin/strategic-partners/cross-ref/${lead.id}`)
      .then(r => { setData(r.data); onDone?.(); })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false));
  }, [lead.id]);

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="cross-ref-modal">
      <div className="w-full max-w-3xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[85vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white sticky top-0">
          <h3 className="font-bold flex items-center gap-2"><Network className="w-4 h-4" /> Cross-Reference · {lead.lead_name}</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          {busy && <div className="text-center py-10"><Loader2 className="w-7 h-7 animate-spin mx-auto text-violet-500" /><p className="text-sm text-slate-500 mt-3">Claude conectează ecosistemul…</p></div>}
          {err && <div className="text-rose-500 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{err}</div>}
          {data && (
            <>
              <div className="text-xs text-slate-500 mb-4">
                <strong>{data.lead_name}</strong> via <strong>{data.city_partner_company}</strong> ({data.city})
              </div>
              <h4 className="font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-violet-500" /> Marketplace partners recomandați</h4>
              {data.matches.length === 0 && <div className="text-sm text-slate-500">Niciun match relevant găsit.</div>}
              {data.matches.map((m, i) => (
                <div key={i} className="mb-3 p-4 rounded-xl border border-violet-200 dark:border-violet-500/30 bg-violet-50/50 dark:bg-violet-500/5" data-testid={`match-${i}`}>
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                    <h5 className="font-bold text-slate-900 dark:text-white">{i + 1}. {m.company}</h5>
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${m.relevance_score >= 80 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : m.relevance_score >= 60 ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" : "bg-slate-100 text-slate-700"}`}>
                      Score {m.relevance_score}/100
                    </span>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-200">{m.reason}</p>
                </div>
              ))}
              {data.introduction_email_subject && (
                <div className="mt-6 p-4 rounded-xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-bold text-cyan-700 dark:text-cyan-300 flex items-center gap-1.5"><Mail className="w-4 h-4" /> Email de introducere (draft AI)</h4>
                    <button onClick={() => navigator.clipboard.writeText(`Subiect: ${data.introduction_email_subject}\n\n${data.introduction_email_body}`)} className="p-1.5 rounded hover:bg-cyan-100 dark:hover:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300" title="Copiază tot" data-testid="copy-email">
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1">Subiect: {data.introduction_email_subject}</div>
                  <p className="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-wrap">{data.introduction_email_body}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const StrategicPartnersDashboard = () => {
  const [data, setData] = useState(null);
  const [unmatched, setUnmatched] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeLead, setActiveLead] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [a, b, c] = await Promise.all([
        ax.get("/api/admin/strategic-partners/dashboard"),
        ax.get("/api/admin/strategic-partners/unmatched-leads"),
        ax.get("/api/admin/strategic-partners/opportunities?limit=5"),
      ]);
      setData(a.data);
      setUnmatched(b.data?.items || []);
      setRecent(c.data?.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-7 h-7 animate-spin text-slate-400" /></div>;
  if (error) return <div className="p-8 text-rose-500"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>;
  if (!data) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="strategic-dashboard-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <Network className="w-5 h-5 text-violet-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Strategic Partners Dashboard</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/15 text-violet-700 dark:text-violet-400">Cross-Program AI</span>
      </div>

      {/* Global totals */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard icon={Users} label="Total parteneri" value={data.totals.partners} color="text-blue-500" />
        <StatCard icon={TrendingUp} label="Total lead-uri" value={data.totals.leads} color="text-amber-500" />
        <StatCard icon={CheckCircle2} label="Conversii" value={data.totals.converted} color="text-emerald-500" />
        <StatCard icon={Sparkles} label="Revenue total" value={`${data.totals.revenue} RON`} color="text-violet-500" />
      </div>

      {/* Side-by-side City vs Marketplace */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* City ecosystem */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-cyan-200 dark:border-cyan-500/30" data-testid="ecosystem-city">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold flex items-center gap-2 text-slate-900 dark:text-white"><Building2 className="w-5 h-5 text-cyan-500" /> City Partners</h3>
            <Link to="/admin/city-partners" className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1">Detalii <ArrowRight className="w-3 h-3" /></Link>
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div><div className="text-xs text-slate-400">Total</div><div className="text-xl font-bold text-slate-900 dark:text-white">{data.city.total}</div></div>
            <div><div className="text-xs text-slate-400">Activi</div><div className="text-xl font-bold text-emerald-600">{data.city.active}</div></div>
            <div><div className="text-xs text-slate-400">Onboarding</div><div className="text-xl font-bold text-amber-600">{data.city.onboarding}</div></div>
          </div>
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-3 gap-3 text-center">
            <div><div className="text-xs text-slate-400">Lead-uri</div><div className="font-bold text-slate-900 dark:text-white">{data.city.leads}</div></div>
            <div><div className="text-xs text-slate-400">Conversii</div><div className="font-bold text-emerald-600">{data.city.converted}</div></div>
            <div><div className="text-xs text-slate-400">Conv. rate</div><div className="font-bold text-violet-600">{data.city.conversion_rate}%</div></div>
          </div>
        </div>

        {/* Marketplace ecosystem */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-violet-200 dark:border-violet-500/30" data-testid="ecosystem-marketplace">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold flex items-center gap-2 text-slate-900 dark:text-white"><ShoppingBag className="w-5 h-5 text-violet-500" /> Marketplace Partners</h3>
            <Link to="/admin/marketplace-partners" className="text-xs text-violet-600 dark:text-violet-400 hover:underline flex items-center gap-1">Detalii <ArrowRight className="w-3 h-3" /></Link>
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div><div className="text-xs text-slate-400">Total</div><div className="text-xl font-bold text-slate-900 dark:text-white">{data.marketplace.total}</div></div>
            <div><div className="text-xs text-slate-400">Activi</div><div className="text-xl font-bold text-emerald-600">{data.marketplace.active}</div></div>
            <div><div className="text-xs text-slate-400">Onboarding</div><div className="text-xl font-bold text-amber-600">{data.marketplace.onboarding}</div></div>
          </div>
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-3 gap-3 text-center">
            <div><div className="text-xs text-slate-400">Lead-uri</div><div className="font-bold text-slate-900 dark:text-white">{data.marketplace.leads}</div></div>
            <div><div className="text-xs text-slate-400">Conversii</div><div className="font-bold text-emerald-600">{data.marketplace.converted}</div></div>
            <div><div className="text-xs text-slate-400">Conv. rate</div><div className="font-bold text-violet-600">{data.marketplace.conversion_rate}%</div></div>
          </div>
        </div>
      </div>

      {/* Coverage by city */}
      {data.coverage.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 mb-6">
          <h3 className="font-bold flex items-center gap-2 text-slate-900 dark:text-white mb-3"><MapPin className="w-4 h-4 text-blue-500" /> Acoperire geografică</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr><th className="text-left py-2">Oraș</th><th className="text-center py-2">City Partners</th><th className="text-center py-2">Marketplace Partners</th><th className="text-center py-2">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.coverage.map(c => (
                  <tr key={c.city} data-testid={`coverage-${c.city}`}>
                    <td className="py-2 font-medium text-slate-900 dark:text-white">{c.city}</td>
                    <td className="text-center py-2 text-cyan-600 font-bold">{c.city_partners}</td>
                    <td className="text-center py-2 text-violet-600 font-bold">{c.marketplace_partners}</td>
                    <td className="text-center py-2">
                      {c.covered
                        ? <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">FULL</span>
                        : <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">PARȚIAL</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Unmatched leads → Cross-Reference Engine */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-violet-200 dark:border-violet-500/30">
          <h3 className="font-bold flex items-center gap-2 text-slate-900 dark:text-white mb-1"><Zap className="w-4 h-4 text-violet-500" /> Cross-Reference Engine</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            Lead-uri City Partner neconectate cu Marketplace Partner. Click „Conectează" pentru sugestii AI.
          </p>
          {unmatched.length === 0
            ? <div className="text-center py-6 text-sm text-slate-500"><CheckCircle2 className="w-6 h-6 mx-auto text-emerald-500 mb-1" />Toate lead-urile sunt procesate.</div>
            : <div className="space-y-2">
              {unmatched.slice(0, 5).map(l => (
                <div key={l.id} className="p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center gap-3" data-testid={`unmatched-${l.id}`}>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{l.lead_name}</div>
                    <div className="text-[11px] text-slate-500 truncate">{l.city_partner_company} · {l.city} · {l.stage}</div>
                  </div>
                  <button onClick={() => setActiveLead(l)} className="px-3 py-1 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white text-xs font-medium flex items-center gap-1" data-testid={`xref-${l.id}`}>
                    <Sparkles className="w-3 h-3" /> Conectează
                  </button>
                </div>
              ))}
            </div>
          }
        </div>

        {/* Recent cross-refs */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
          <h3 className="font-bold flex items-center gap-2 text-slate-900 dark:text-white mb-3"><Network className="w-4 h-4 text-emerald-500" /> Oportunități recente</h3>
          {recent.length === 0
            ? <div className="text-sm text-slate-500 text-center py-6">Nicio analiză rulată încă.</div>
            : <div className="space-y-2">
              {recent.map(o => (
                <div key={o.id} className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 text-xs" data-testid={`recent-${o.id}`}>
                  <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
                    <span className="font-semibold text-slate-900 dark:text-white">{o.lead_name}</span>
                    <span className="text-[10px] text-slate-400">{o.generated_at ? new Date(o.generated_at).toLocaleDateString("ro-RO") : ""}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 mb-1.5">via {o.city_partner_company} · {o.city}</div>
                  {(o.matches || []).map((m, i) => (
                    <div key={i} className="flex items-center gap-2 text-[11px] py-0.5">
                      <span className="text-violet-600 font-bold">→</span>
                      <span className="text-slate-700 dark:text-slate-200">{m.company}</span>
                      <span className="text-emerald-600 font-bold">{m.relevance_score}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          }
        </div>
      </div>

      {activeLead && <CrossRefModal lead={activeLead} onClose={() => setActiveLead(null)} onDone={load} />}
    </div>
  );
};

export default StrategicPartnersDashboard;
export { StrategicPartnersDashboard };
