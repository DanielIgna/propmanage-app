import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  FlaskConical, RefreshCcw, Loader2, Users, UserPlus, Eye, QrCode, Share2,
  MessageSquareHeart, CheckCircle2, XCircle, IdCard, Timer, LifeBuoy, ThumbsUp, ThumbsDown,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const Kpi = ({ icon: Icon, label, value, sub, testid }) => (
  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid={testid}>
    <div className="flex items-center gap-2 text-stone-400 text-xs"><Icon className="w-4 h-4 text-[#d4ff3a]" /> {label}</div>
    <div className="mt-1.5 text-2xl lg:text-3xl font-semibold text-stone-100">{value}</div>
    {sub && <div className="text-[11px] text-stone-500 mt-0.5">{sub}</div>}
  </div>
);

const FunnelBar = ({ step }) => (
  <div className="flex items-center gap-3" data-testid={`beta-funnel-${step.id}`}>
    <div className="w-44 text-xs text-stone-300 shrink-0">{step.label}</div>
    <div className="flex-1 h-5 rounded-full bg-white/5 overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${Math.max(step.pct, step.count > 0 ? 4 : 0)}%`, background: "#d4ff3a" }} />
    </div>
    <div className="w-20 text-right text-xs text-stone-400 shrink-0"><b className="text-stone-200">{step.count}</b> · {step.pct}%</div>
  </div>
);

const Gate = ({ g }) => (
  <div className={`rounded-2xl border p-3 ${g.passed ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/10 bg-white/[0.02]"}`} data-testid={`beta-gate-${g.id}`}>
    <div className="flex items-start gap-2">
      {g.passed ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" /> : <XCircle className="w-4 h-4 text-stone-600 shrink-0 mt-0.5" />}
      <span className="text-xs text-stone-300 flex-1">{g.label}</span>
    </div>
    <div className="mt-1.5 pl-6 text-[11px] text-stone-500">țintă ≥{g.target_pct}% · actual <b className={g.passed ? "text-emerald-300" : "text-stone-300"}>{g.actual_pct}%</b></div>
  </div>
);

export default function BetaCockpitPage() {
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, f] = await Promise.all([
        axios.get(`${API}/api/admin/beta/overview?days=${days}`, { withCredentials: true }),
        axios.get(`${API}/api/admin/beta/feedback`, { withCredentials: true }),
      ]);
      setData(o.data); setFeedback(f.data.items || []);
    } catch (err) { console.error("Beta cockpit load failed", err); }
    finally { setLoading(false); }
  }, [days]);
  useEffect(() => { load(); }, [load]);

  if (loading && !data) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-stone-500" /></div>;
  if (!data) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 text-sm p-8">Nu am putut încărca datele beta.</div>;

  const p = data.passports;
  return (
    <div className="pm-shell min-h-screen bg-[#0a0a0b] text-stone-100 p-4 lg:p-8">
    <div className="max-w-7xl mx-auto space-y-6" data-testid="beta-cockpit-page">
    <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-block" data-testid="cockpit-back-admin">← Înapoi la Admin</Link>
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl lg:text-4xl font-bold tracking-tight text-stone-100 flex items-center gap-3"><FlaskConical className="w-5 h-5 lg:w-8 lg:h-8 text-[#d4ff3a]" /> Beta Cockpit · EO-026</h1>
          <p className="text-xs text-stone-500 mt-1">Learn before scale — doar utilizatori REALI (fără demo/test/interni) · fereastră {data.window_days} zile</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)} data-testid={`beta-days-${d}`}
              className={`px-3 py-1.5 rounded-full text-xs font-medium ${days === d ? "bg-[#d4ff3a] text-black" : "bg-white/5 text-stone-400"}`}>{d}z</button>
          ))}
          <button onClick={load} className="p-2 rounded-full bg-white/5 text-stone-400" data-testid="beta-refresh"><RefreshCcw className="w-4 h-4" /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi icon={Users} label="Vizitatori" value={data.visitors} testid="beta-kpi-visitors" />
        <Kpi icon={UserPlus} label="Înregistrări reale" value={data.registrations.total}
          sub={`${data.registrations.owners} proprietari · ${data.registrations.specialists} specialiști · conversie ${data.registrations.visitor_conversion_pct}%`} testid="beta-kpi-registrations" />
        <Kpi icon={Timer} label="Time To First Value" value={data.ttfv_minutes_median != null ? `${data.ttfv_minutes_median} min` : "—"} sub="register → primul document (mediană)" testid="beta-kpi-ttfv" />
        <Kpi icon={LifeBuoy} label="Cereri suport" value={data.support_requests} testid="beta-kpi-support" />
      </div>

      <section className="rounded-3xl border border-white/10 bg-white/[0.02] p-5" data-testid="beta-owner-funnel">
        <h2 className="text-sm font-medium text-stone-200">Funnel proprietari (misiunea beta)</h2>
        <div className="mt-4 space-y-2.5">{data.owner_funnel.map(s => <FunnelBar key={s.id} step={s} />)}</div>
      </section>

      <section data-testid="beta-gates">
        <h2 className="text-sm font-medium text-stone-200">Criteriile de succes EO-026</h2>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">{data.gates.map(g => <Gate key={g.id} g={g} />)}</div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="rounded-3xl border border-white/10 bg-white/[0.02] p-5" data-testid="beta-passport-rollup">
          <h2 className="text-sm font-medium text-stone-200 flex items-center gap-2"><IdCard className="w-4 h-4 text-[#d4ff3a]" /> Passport Analytics (toate pașapoartele)</h2>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            {[[Eye, "Vizualizări", p.views], [Users, "Vizitatori unici", p.unique_visitors], [QrCode, "Scanări QR", p.qr_scans], [Share2, "Share-uri", p.shares],
              [Share2, "Preview-uri social", p.og_fetches], [UserPlus, "Click CTA", p.cta_clicks], [UserPlus, "Conturi create", p.registers], [IdCard, "Pașapoarte active", p.active_passports],
            ].map(([Icon, l, v]) => (
              <div key={l} className="rounded-2xl bg-white/[0.03] p-3">
                <Icon className="w-4 h-4 mx-auto text-stone-500" />
                <div className="mt-1 text-lg font-semibold text-stone-100">{v}</div>
                <div className="text-[10px] text-stone-500">{l}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-white/[0.02] p-5" data-testid="beta-specialist-funnel">
          <h2 className="text-sm font-medium text-stone-200">Funnel specialiști</h2>
          <div className="mt-3 space-y-2">
            {data.specialist_funnel.map(s => (
              <div key={s.id} className="flex items-center justify-between text-xs" data-testid={`beta-spec-${s.id}`}>
                <span className="text-stone-400">{s.label}</span>
                <b className="text-stone-200">{s.count}</b>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-3xl border border-white/10 bg-white/[0.02] p-5" data-testid="beta-voc">
        <h2 className="text-sm font-medium text-stone-200 flex items-center gap-2">
          <MessageSquareHeart className="w-4 h-4 text-[#d4ff3a]" /> Voice of Customer
          <span className="text-[11px] text-stone-500 font-normal">· {data.voc.count} răspunsuri · <ThumbsUp className="w-3 h-3 inline text-emerald-400" /> {data.voc.recommend_yes} · <ThumbsDown className="w-3 h-3 inline text-red-400" /> {data.voc.recommend_no}</span>
        </h2>
        {feedback.length === 0 ? (
          <p className="mt-3 text-xs text-stone-500">Niciun feedback încă — utilizatorii beta văd widgetul „Feedback beta" în dashboard.</p>
        ) : (
          <div className="mt-3 space-y-3 max-h-96 overflow-y-auto pr-2">
            {feedback.map((f, i) => (
              <div key={i} className="rounded-2xl bg-white/[0.03] p-3 text-xs" data-testid={`beta-fb-item-${i}`}>
                <div className="flex items-center gap-2">
                  <b className="text-stone-200">{f.name || f.user_email}</b>
                  <span className="text-stone-500">{f.role}</span>
                  {f.recommend === true && <span className="text-emerald-400 font-medium">recomandă</span>}
                  {f.recommend === false && <span className="text-red-400 font-medium">nu recomandă</span>}
                  <span className="ml-auto text-stone-600">{(f.created_at || "").slice(0, 10)}</span>
                </div>
                <div className="mt-1.5 space-y-1 text-stone-400">
                  {[["Confuz", f.confusing], ["Ușor", f.easy], ["Încredere", f.trust], ["Aproape a renunțat", f.almost_quit], ["Impresionat de", f.impressed], ["De ce", f.why]]
                    .filter(([, v]) => v).map(([l, v]) => <div key={l}><span className="text-stone-500">{l}:</span> {v}</div>)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
    </div>
  );
}
