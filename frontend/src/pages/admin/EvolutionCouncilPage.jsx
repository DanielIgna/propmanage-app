// AI 27 — Enterprise Evolution Council: ședința automată nightly, UN raport, 5 întrebări
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Users, Loader2, Play, TrendingUp, TrendingDown, Ban, Bot, Target } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const Section = ({ icon: Icon, title, items, color, testid }) => (
  <div className="bg-[#0e0e10] rounded-2xl border border-white/10 p-5" data-testid={testid}>
    <div className={`text-xs uppercase tracking-widest mb-3 flex items-center gap-1.5 ${color}`}><Icon className="w-3.5 h-3.5" /> {title}</div>
    <ul className="space-y-1.5 text-xs text-stone-300 list-disc list-inside">
      {(items || []).map((it, i) => <li key={i}>{it}</li>)}
    </ul>
  </div>
);

export default function EvolutionCouncilPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/evolution-council`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const runNow = async () => {
    setRunning(true);
    try {
      await axios.post(`${API}/api/admin/evolution-council/run`, {}, { withCredentials: true });
      await load();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); } finally { setRunning(false); }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă...</div>;
  const r = data?.latest;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-5xl mx-auto px-6 pt-28 pb-16">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3" data-testid="council-title">
              <Users className="w-8 h-8 text-[#d4ff3a]" /> Evolution Council
            </h1>
            <p className="text-sm text-stone-400 mt-1">Ședința automată a departamentelor AI — în fiecare noapte, un singur raport. (AI 27, Rezoluția 003)</p>
          </div>
          <button onClick={runNow} disabled={running} className="pm-btn pm-btn-success" data-testid="council-run-btn">
            {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Rulează ședința acum
          </button>
        </div>

        {!r ? (
          <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-10 text-center text-stone-400" data-testid="council-empty">
            Nicio ședință încă. Apasă „Rulează ședința acum" — sau așteaptă rularea automată de la 23:45.
          </div>
        ) : (
          <>
            <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-5 mb-6 flex items-center justify-between flex-wrap gap-3" data-testid="council-header">
              <div className="text-sm text-stone-300">Raport: <span className="text-white font-medium">{r.day}</span> · convocat de <span className="text-stone-400">{r.actor}</span></div>
              <div className="text-xs text-stone-400">Enterprise Health: <span className="text-[#d4ff3a] font-serif text-lg">{r.health.overall}</span>
                {r.health.delta != null && <span className={r.health.delta >= 0 ? "text-emerald-400 ml-1" : "text-red-400 ml-1"}>({r.health.delta >= 0 ? "+" : ""}{r.health.delta})</span>}
              </div>
            </div>

            {/* Tomorrow's top action */}
            <div className="bg-[#d4ff3a]/5 rounded-3xl border-2 border-[#d4ff3a]/30 p-6 mb-6" data-testid="council-tomorrow">
              <div className="flex items-center gap-2 text-[#d4ff3a] text-xs uppercase tracking-widest mb-2"><Target className="w-4 h-4" /> Acțiunea cu cel mai mare ROI mâine</div>
              <div className="font-serif text-xl leading-snug mb-2">{r.tomorrow_top_action?.action}</div>
              <div className="flex flex-wrap gap-2 text-xs">
                {[["ROI", r.tomorrow_top_action?.expected_roi], ["ROT", r.tomorrow_top_action?.expected_rot], ["Încredere", `${r.tomorrow_top_action?.confidence_pct}%`]].map(([k, v]) => (
                  <span key={k} className="bg-white/5 border border-white/10 rounded-full px-3 py-1"><span className="text-stone-500">{k}:</span> <span className="text-[#d4ff3a]">{v}</span></span>
                ))}
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mb-8">
              <Section icon={TrendingUp} title="1 · Ce s-a îmbunătățit azi?" items={r.improved} color="text-emerald-400" testid="council-improved" />
              <Section icon={TrendingDown} title="2 · Ce s-a înrăutățit?" items={r.worsened} color="text-red-400" testid="council-worsened" />
              <Section icon={Ban} title="3 · Ce ar trebui oprit?" items={r.stop} color="text-amber-300" testid="council-stop" />
              <Section icon={Bot} title="4 · Ce automatizăm următorul?" items={r.automate_next} color="text-cyan-300" testid="council-automate" />
            </div>

            {/* History */}
            {data.history.length > 1 && (
              <div data-testid="council-history">
                <h2 className="font-serif text-xl mb-3">Ședințe anterioare</h2>
                <div className="space-y-2">
                  {data.history.filter(h => h.day !== r.day).map(h => (
                    <div key={h.day} className="flex items-center justify-between text-xs bg-[#0e0e10] border border-white/10 rounded-xl px-4 py-2.5">
                      <span className="text-stone-300">{h.day}</span>
                      <span className="text-stone-500 truncate mx-3 flex-1">{h.tomorrow_top_action?.action}</span>
                      <span className="text-[#d4ff3a] shrink-0">EH {h.health?.overall}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
