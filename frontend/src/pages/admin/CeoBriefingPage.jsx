// CEO Briefing (D152) — o singură pagină de decizie pe zi. Nu dashboards. Priorități.
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Crown, Loader2, RefreshCcw, Target, AlertTriangle, Sparkles, EyeOff, Users2, Fingerprint } from "lucide-react";
import axios from "axios";
import { InspectorButton } from "../../components/founder/InspectorButton";

const API = process.env.REACT_APP_BACKEND_URL;

export default function CeoBriefingPage() {
  const [b, setB] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/ceo-briefing`, { withCredentials: true });
      setB(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se generează briefing-ul...</div>;
  if (!b) return <div className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center text-stone-400 gap-4" data-testid="ceo-brief-error"><span>Briefing indisponibil.</span><button onClick={load} className="pm-btn pm-btn-secondary"><RefreshCcw className="w-3.5 h-3.5" /> Reîncearcă</button></div>;

  const st = b.enterprise_status;
  const ot = b.one_thing;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-5xl mx-auto px-6 pt-28 pb-16">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3" data-testid="ceo-brief-title">
              <Crown className="w-8 h-8 text-[#d4ff3a]" /> CEO Briefing · {b.day}
            </h1>
            <p className="text-sm text-stone-400 mt-1">O pagină. Priorități, nu informații. (Directiva 152)</p>
          </div>
          <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="ceo-brief-refresh"><RefreshCcw className="w-3.5 h-3.5" /> Regenerează</button>
        </div>

        {/* Status */}
        <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6 mb-6 flex items-center gap-6 flex-wrap" data-testid="ceo-brief-status">
          <div className="font-serif text-6xl" style={{ color: st.band.color }}>{Math.round(st.overall)}</div>
          <div className="min-w-0 flex-1">
            <div className="text-lg font-medium" style={{ color: st.band.color }}>Company Status: {st.status}{st.escalated && <span className="text-[10px] bg-red-500/15 text-red-300 px-2 py-0.5 rounded-full ml-2 uppercase tracking-wide">Escaladat (EP-007)</span>}</div>
            <p className="text-xs text-stone-400 mt-1">{st.reason}</p>
          </div>
          <div className="text-right shrink-0">
            {st.enterprise_score != null && (
              <div className="text-xs text-stone-500 mb-1" data-testid="ceo-brief-es">Enterprise Score: <span className="font-serif text-xl" style={{ color: st.enterprise_score_band?.color }}>{Math.round(st.enterprise_score)}</span></div>
            )}
            <Link to="/admin/enterprise-health" className="text-xs text-[#d4ff3a] hover:underline">Enterprise Health →</Link>
          </div>
          <InspectorButton widgetId="ceo.enterprise_status" />
        </div>

        {/* ONE THING */}
        <div className="bg-[#d4ff3a]/5 rounded-3xl border-2 border-[#d4ff3a]/30 p-7 mb-8" data-testid="ceo-brief-one-thing">
          <div className="flex items-center gap-2 text-[#d4ff3a] text-xs uppercase tracking-widest mb-3"><Target className="w-4 h-4" /> Dacă faci UN SINGUR lucru azi <InspectorButton widgetId="ceo.one_thing" className="ml-auto" /></div>
          <div className="font-serif text-2xl leading-snug mb-3" data-testid="ceo-brief-action">{ot.action}</div>
          <p className="text-sm text-stone-300 mb-4">{ot.why}</p>
          <div className="flex flex-wrap gap-2 text-xs">
            {[["ROI", ot.expected_roi], ["ROT", ot.expected_rot], ["Health", ot.expected_health_impact], ["Încredere", `${ot.confidence_pct}%`]].map(([k, v]) => (
              <span key={k} className="bg-white/5 border border-white/10 rounded-full px-3 py-1.5"><span className="text-stone-500">{k}:</span> <span className="text-[#d4ff3a]">{v}</span></span>
            ))}
          </div>
        </div>

        {/* Snapshot */}
        <div className="grid sm:grid-cols-2 gap-2.5 mb-8" data-testid="ceo-brief-snapshot">
          {b.snapshot.map(s => (
            <div key={s.key} className="flex items-center gap-3 bg-[#0e0e10] border border-white/10 rounded-xl px-4 py-3">
              <span className="font-serif text-lg w-10 text-right shrink-0" style={{ color: s.color }}>{s.score != null ? Math.round(s.score) : "—"}</span>
              <div className="min-w-0"><div className="text-xs text-stone-200">{s.label}</div><div className="text-[11px] text-stone-500 truncate">{s.line}</div></div>
            </div>
          ))}
        </div>

        {/* Autonomous Execution Report 24h */}
        {b.autonomous_execution && (
          <div className="bg-[#0e0e10] rounded-3xl border border-emerald-500/20 p-6 mb-8" data-testid="ceo-brief-autonomous">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <h2 className="font-serif text-xl">Execuție autonomă · ultimele 24h <span className="text-[10px] align-middle ml-2 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">L2</span></h2>
              {!b.autonomous_execution.email_live && <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300" data-testid="ceo-brief-auto-blocked">EMAIL BLOCAT (DNS Resend)</span>}
              <InspectorButton widgetId="ceo.autonomous_execution" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 text-center">
              {[
                { l: "Procesate", v: b.autonomous_execution.leads_processed },
                { l: "Trimise", v: b.autonomous_execution.emails_sent },
                { l: "În coadă", v: b.autonomous_execution.emails_queued },
                { l: "Reactivate", v: b.autonomous_execution.leads_reactivated },
                { l: "Consultanțe", v: b.autonomous_execution.consultations_scheduled },
                { l: "Contracte", v: b.autonomous_execution.contracts_signed },
                { l: "Venit (RON)", v: b.autonomous_execution.revenue_generated_ron },
                { l: "Ore salvate (est. 60%)", v: b.autonomous_execution.hours_saved },
              ].map((s, i) => (
                <div key={i} className="bg-white/[0.02] border border-white/10 rounded-xl px-2 py-2.5">
                  <div className="font-serif text-lg text-emerald-300">{s.v}</div>
                  <div className="text-[10px] text-stone-500">{s.l}</div>
                </div>
              ))}
            </div>
            <div className="text-[11px] text-stone-500 mt-3" data-testid="ceo-brief-auto-reco">→ <span className="text-emerald-300/90">{b.autonomous_execution.recommendation}</span> · {b.autonomous_execution.truth_note}</div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Risks */}
          <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ceo-brief-risks">
            <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Top riscuri</h2>
            <div className="space-y-2">
              {b.top_risks.map((r, i) => (
                <div key={i} className="text-xs bg-white/[0.02] border border-white/10 rounded-xl px-3.5 py-2.5">
                  <span className={r.severity === "critical" ? "text-red-400" : r.severity === "blocker" ? "text-cyan-300" : "text-amber-300"}>{r.title}</span>
                  <div className="text-stone-500 mt-0.5">{r.why}</div>
                </div>
              ))}
            </div>
          </div>
          {/* Opportunities */}
          <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6" data-testid="ceo-brief-opportunities">
            <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><Sparkles className="w-4 h-4 text-[#d4ff3a]" /> Top oportunități</h2>
            <div className="space-y-2">
              {b.top_opportunities.map((o, i) => (
                <div key={i} className="text-xs bg-white/[0.02] border border-white/10 rounded-xl px-3.5 py-2.5">
                  <span className="text-stone-200">{o.title}</span>
                  <div className="text-[#d4ff3a]/80 mt-0.5">→ {o.action}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Founder Focus */}
        <div className="grid md:grid-cols-3 gap-4" data-testid="ceo-brief-focus">
          {[
            { t: "Ignoră azi", icon: EyeOff, items: b.founder_focus.ignore_today, c: "text-stone-400" },
            { t: "Deleagă", icon: Users2, items: b.founder_focus.delegate, c: "text-cyan-300" },
            { t: "Doar tu", icon: Fingerprint, items: b.founder_focus.founder_only, c: "text-[#d4ff3a]" },
          ].map(col => (
            <div key={col.t} className="bg-[#0e0e10] rounded-2xl border border-white/10 p-5">
              <div className={`text-xs uppercase tracking-widest mb-3 flex items-center gap-1.5 ${col.c}`}><col.icon className="w-3.5 h-3.5" /> {col.t}</div>
              <ul className="space-y-1.5 text-[11px] text-stone-400 list-disc list-inside">
                {col.items.map((it, i) => <li key={i}>{it}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
