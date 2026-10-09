import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Building2, Users, ClipboardList, Megaphone, ArrowLeft, Copy, Check,
  CalendarClock, AlertTriangle, Send, ChevronRight, Activity,
} from "lucide-react";
import { API } from "./DashShared";
import { useAuth, formatApiError } from "../auth";
import { BuildingBenefitsCard } from "../components/pb/PbEverywhere";

const GREEN = "#166534";
const DOT = { green: "#22c55e", yellow: "#f59e0b", red: "#ef4444" };
const STATUS_LABEL = { green: "Totul OK", yellow: "Necesită atenție", red: "Urgent" };

const HealthBar = ({ health }) => (
  <div className="space-y-2" data-testid="aw-health-breakdown">
    {health.components.map(c => (
      <div key={c.key}>
        <div className="flex items-center justify-between text-[11px]">
          <span className="font-bold text-slate-600">{c.label} <span className="text-slate-300">· {c.weight}%</span></span>
          <span className="font-black text-slate-900">{c.value}</span>
        </div>
        <div className="mt-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${c.value}%`, background: c.value >= 70 ? DOT.green : c.value >= 45 ? DOT.yellow : DOT.red }} />
        </div>
        <div className="mt-0.5 text-[10px] text-slate-400">{c.detail}</div>
      </div>
    ))}
  </div>
);

const AnnouncementComposer = ({ buildingId, onPosted }) => {
  const [form, setForm] = useState({ title: "", body: "" });
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/buildings/${buildingId}/announcements`, form);
      setForm({ title: "", body: "" });
      onPosted();
    } catch (err) { alert(formatApiError(err)); }
    finally { setLoading(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-2" data-testid="aw-announce-form">
      <input required minLength={3} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        placeholder="Titlul anunțului (ex: Oprire apă caldă marți)"
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm" data-testid="aw-announce-title" />
      <textarea required minLength={3} rows={2} value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
        placeholder="Detalii pentru locatari..."
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm resize-none" data-testid="aw-announce-body" />
      <button disabled={loading} data-testid="aw-announce-submit"
        className="px-4 py-2.5 rounded-full text-xs font-black text-white disabled:opacity-50" style={{ background: GREEN }}>
        <Send className="w-3.5 h-3.5 inline mr-1 -mt-0.5" />{loading ? "..." : "Publică și notifică locatarii"}
      </button>
    </form>
  );
};

const BuildingDetail = ({ buildingId, onBack }) => {
  const [d, setD] = useState(null);
  const [copied, setCopied] = useState(false);
  const load = () => axios.get(`${API}/buildings/${buildingId}/dashboard`).then(r => setD(r.data)).catch(e => alert(formatApiError(e)));
  useEffect(() => { load(); }, [buildingId]);
  if (!d) return <div className="py-16 text-center text-sm text-slate-400">Se încarcă...</div>;

  const copyInvite = async () => {
    try { await navigator.clipboard.writeText(d.invite_link); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
  };

  return (
    <div data-testid="aw-building-detail">
      <button onClick={onBack} data-testid="aw-back" className="flex items-center gap-1.5 text-xs font-bold text-slate-500 mb-4">
        <ArrowLeft className="w-4 h-4" /> Portofoliu
      </button>
      <div className="flex items-start gap-3 flex-wrap">
        <div className="flex-1 min-w-[240px]">
          <h1 className="text-2xl lg:text-[32px] font-bold tracking-tight text-slate-900">{d.name}</h1>
          <p className="text-xs text-slate-400 mt-1">{d.address}{d.city ? `, ${d.city}` : ""} · {d.properties_count} apartamente conectate · {d.members_count} {d.members_count === 1 ? "locatar" : "locatari"}</p>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white px-4 py-3 text-center shadow-sm" data-testid="aw-health-score">
          <div className="text-3xl font-black" style={{ color: DOT[d.health.status] }}>{d.health.score}</div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Building Health</div>
        </div>
      </div>

      <div className="mt-5 grid lg:grid-cols-2 gap-4">
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
              <Activity className="w-3.5 h-3.5" style={{ color: GREEN }} /> Sănătatea blocului — {STATUS_LABEL[d.health.status]}
            </h3>
            <HealthBar health={d.health} />
          </div>

          <BuildingBenefitsCard buildingId={buildingId} />

          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
              <Users className="w-3.5 h-3.5" style={{ color: GREEN }} /> Apartamente ({d.apartments.length})
            </h3>
            <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1" data-testid="aw-apartments">
              {d.apartments.map(a => (
                <div key={a.property_id} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2" data-testid={`aw-apt-${a.property_id}`}>
                  <span className="text-xs font-bold text-slate-700 flex-1 truncate">{a.name} <span className="text-slate-400 font-semibold">· {a.owner_first_name}</span></span>
                  {a.overdue_tasks > 0 && <span className="text-[10px] font-bold text-rose-500 flex items-center gap-0.5"><AlertTriangle className="w-3 h-3" />{a.overdue_tasks} depășite</span>}
                  {a.open_requests > 0 && <span className="text-[10px] font-bold text-amber-600">{a.open_requests} cereri</span>}
                  {a.active_tasks > 0 && <span className="text-[10px] font-bold text-slate-400">{a.active_tasks} revizii</span>}
                </div>
              ))}
              {d.apartments.length === 0 && <p className="text-xs text-slate-400">Niciun apartament conectat încă — trimite linkul de invitație.</p>}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm" data-testid="aw-invite-card">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 mb-2">Invită locatarii</h3>
            <p className="text-[11px] text-slate-400 mb-2">Trimite linkul pe grupul blocului sau afișează-l la avizier — fiecare locatar conectat crește puterea campaniilor comune.</p>
            <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5">
              <code className="flex-1 text-[10px] text-slate-600 break-all" data-testid="aw-invite-link">{d.invite_link}</code>
              <button onClick={copyInvite} data-testid="aw-invite-copy" className="shrink-0 p-1.5 rounded-lg bg-white border border-slate-200">
                {copied ? <Check className="w-3.5 h-3.5" style={{ color: GREEN }} /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
              </button>
              <a href={`https://wa.me/?text=${encodeURIComponent(`Blocul nostru e acum pe PropManage — conectează-ți apartamentul: ${d.invite_link}`)}`}
                target="_blank" rel="noreferrer" data-testid="aw-invite-wa"
                className="shrink-0 px-3 py-1.5 rounded-lg bg-[#25D366] text-white text-[10px] font-black">WhatsApp</a>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
              <Megaphone className="w-3.5 h-3.5" style={{ color: GREEN }} /> Anunțuri
            </h3>
            {d.is_admin && <div className="mb-3"><AnnouncementComposer buildingId={d.id} onPosted={load} /></div>}
            <div className="space-y-2" data-testid="aw-announcements">
              {d.announcements.map(a => (
                <div key={a.id} className="rounded-xl bg-slate-50 px-3 py-2.5" data-testid={`aw-ann-${a.id}`}>
                  <div className="text-xs font-black text-slate-900">{a.title}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{a.body}</div>
                  <div className="text-[9px] text-slate-400 mt-1">{a.author_name} · {new Date(a.created_at).toLocaleDateString("ro-RO")}</div>
                </div>
              ))}
              {d.announcements.length === 0 && <p className="text-xs text-slate-400">Niciun anunț încă.</p>}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
              <CalendarClock className="w-3.5 h-3.5" style={{ color: GREEN }} /> Mentenanță în următoarele 90 zile
            </h3>
            <div className="space-y-1.5" data-testid="aw-upcoming">
              {d.upcoming_maintenance.map(u => (
                <div key={u.title} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
                  <span className="text-xs font-bold text-slate-700 flex-1 truncate">{u.title}</span>
                  <span className="text-[10px] font-bold text-slate-400">{u.count} ap. · din {new Date(`${u.earliest}T00:00:00`).toLocaleDateString("ro-RO")}</span>
                </div>
              ))}
              {d.upcoming_maintenance.length === 0 && <p className="text-xs text-slate-400">Nicio revizie planificată — încurajează locatarii să-și adauge calendarul de mentenanță.</p>}
            </div>
            {(d.opportunities || []).length > 0 && (
              <div className="mt-3 space-y-1.5">
                {d.opportunities.map(o => (
                  <div key={o.category} className="text-[11px] font-bold text-amber-600 bg-amber-50 rounded-xl px-3 py-2">
                    ✨ {o.properties} apartamente au „{o.category_label}" scadentă — pornește o campanie din contul tău de proprietar.
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-100 bg-white p-4 shadow-sm">
            <h3 className="text-[11px] font-black uppercase tracking-wider text-slate-400 mb-3">Campanii comune</h3>
            <div className="space-y-1.5" data-testid="aw-campaigns">
              {d.campaigns.map(c => (
                <div key={c.id} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
                  <span className="text-xs font-bold text-slate-700 flex-1 truncate">{c.title}</span>
                  <span className="text-[10px] font-bold text-slate-400">{c.participants_count} ap.</span>
                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${c.status === "scheduled" ? "bg-[#34C759]/10 text-[#166534]" : c.status === "open" ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-400"}`}>
                    {c.status === "scheduled" ? "Programată" : c.status === "open" ? "Deschisă" : c.status}
                  </span>
                </div>
              ))}
              {d.campaigns.length === 0 && <p className="text-xs text-slate-400">Nicio campanie încă.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function AdministratorWorkspace() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (!user) return;
    axios.get(`${API}/admin-workspace/portfolio`).then(r => setData(r.data)).catch(() => setData({ buildings: [], totals: {} }));
  }, [user, selected]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#FAFBFA] cv2-scope" data-testid="admin-workspace">
      <div className="max-w-6xl mx-auto px-5 py-6">
        {!selected && (
          <>
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex-1 min-w-[220px]">
                <h1 className="text-2xl lg:text-[36px] font-bold tracking-tight text-slate-900">Administrare blocuri</h1>
                <p className="text-xs text-slate-400 mt-1">Portofoliul tău — fără Excel, totul într-un singur loc.</p>
              </div>
              <Link to="/client" data-testid="aw-back-client" className="px-4 py-2.5 rounded-full bg-slate-50 border border-slate-100 text-xs font-bold text-slate-600 flex items-center gap-1.5">
                <ArrowLeft className="w-3.5 h-3.5" /> Contul de proprietar
              </Link>
            </div>

            {data && data.buildings.length > 0 && (
              <div className="mt-5 flex items-center gap-3 flex-wrap" data-testid="aw-totals">
                {[["Blocuri", data.totals.buildings], ["Apartamente", data.totals.apartments], ["Locatari", data.totals.residents],
                  ["Cereri deschise", data.totals.open_requests], ["Campanii active", data.totals.active_campaigns]].map(([l, v]) => (
                  <div key={l} className="rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-sm">
                    <div className="text-xl font-black text-slate-900">{v}</div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{l}</div>
                  </div>
                ))}
                <div className="rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-sm flex items-center gap-3">
                  {["green", "yellow", "red"].map(s => (
                    <span key={s} className="flex items-center gap-1 text-xs font-bold text-slate-600">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: DOT[s] }} /> {data.totals[s] || 0}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="aw-portfolio">
              {data === null && <p className="text-sm text-slate-400">Se încarcă...</p>}
              {data && data.buildings.length === 0 && (
                <div className="col-span-full rounded-3xl border-2 border-dashed border-slate-200 bg-white p-8 text-center">
                  <Building2 className="w-10 h-10 mx-auto text-slate-300" />
                  <h2 className="mt-3 text-lg font-black text-slate-900">Niciun bloc administrat</h2>
                  <p className="mt-1 text-sm text-slate-400">Creează blocul din contul de proprietar (tab Proprietăți → Blocul meu) — devii automat administratorul lui.</p>
                  <Link to="/client?tab=property" className="mt-4 inline-block px-6 py-3 rounded-full text-sm font-black text-white" style={{ background: GREEN }}>Mergi la Blocul meu</Link>
                </div>
              )}
              {data && data.buildings.map(b => (
                <button key={b.id} onClick={() => setSelected(b.id)} data-testid={`aw-building-${b.id}`}
                  className="rounded-3xl border border-slate-100 bg-white p-4 text-left shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: DOT[b.health.status] }} data-testid={`aw-dot-${b.id}`} />
                    <span className="text-sm font-black text-slate-900 truncate flex-1">{b.name}</span>
                    <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400 truncate">{b.address}</div>
                  <div className="mt-3 flex items-center gap-3 text-[11px] font-bold text-slate-500 flex-wrap">
                    <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{b.properties_count} ap.</span>
                    <span className="flex items-center gap-1"><ClipboardList className="w-3.5 h-3.5" />{b.open_requests} cereri</span>
                    {b.overdue_tasks > 0 && <span className="text-rose-500">{b.overdue_tasks} revizii depășite</span>}
                    <span className="ml-auto text-slate-900 font-black">{b.health.score}<span className="text-slate-300 font-bold">/100</span></span>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
        {selected && <BuildingDetail buildingId={selected} onBack={() => setSelected(null)} />}
      </div>
    </div>
  );
}
