import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ShieldCheck, ShieldAlert, ShieldX, Activity, AlertTriangle, Loader2,
  RefreshCcw, Brain, Eye, Sparkles, ListChecks, X
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const LEVEL_META = {
  low:      { label: "SCĂZUT",  color: "emerald", icon: ShieldCheck },
  medium:   { label: "MEDIU",   color: "amber",   icon: ShieldAlert },
  high:     { label: "RIDICAT", color: "orange",  icon: ShieldAlert },
  critical: { label: "CRITIC",  color: "red",     icon: ShieldX },
};

const Pill = ({ children, className = "" }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium border ${className}`}>{children}</span>
);

export default function AISecurityCenterPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiRecs, setAiRecs] = useState(null);
  const [hours, setHours] = useState(24);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await ax.get("/api/admin/ai-security/overview", { params: { hours } });
      setOverview(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [hours]);

  const runAI = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const { data } = await ax.post("/api/admin/ai-security/analyze", null, { params: { hours } });
      setAiRecs(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la analiza AI");
    } finally { setAnalyzing(false); }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" />Se încarcă...</div>;
  if (!overview) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-red-400">{error || "Eroare"}</div>;

  const lvl = LEVEL_META[overview.threat_level] || LEVEL_META.low;
  const LevelIcon = lvl.icon;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">← Admin</Link>
        <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="sec-center-title">
              AI Security <span className="italic gradient-text">Center</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">Monitorizare proactivă a evenimentelor de securitate · scoring · recomandări AI. <strong className="text-[#d4ff3a]">READ-ONLY</strong> — nu blochează IP-uri automat.</p>
          </div>
          <div className="flex gap-2">
            <select value={hours} onChange={e => setHours(parseInt(e.target.value))} className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs" data-testid="sec-hours-select">
              <option value="1">Ultima oră</option>
              <option value="6">6h</option>
              <option value="24">24h</option>
              <option value="72">3 zile</option>
              <option value="168">7 zile</option>
            </select>
            <button onClick={load} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="sec-refresh"><RefreshCcw className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-2xl p-3 flex items-start gap-2 text-sm text-red-300">
            <AlertTriangle className="w-4 h-4 mt-0.5" />{error}<button onClick={() => setError(null)} className="ml-auto"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        {/* Score + Threat Level hero */}
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          <div className={`bg-${lvl.color}-500/10 border border-${lvl.color}-500/30 rounded-3xl p-6 md:col-span-2 flex items-center gap-5`} data-testid="sec-hero">
            <div className={`w-20 h-20 rounded-2xl bg-${lvl.color}-500/15 border border-${lvl.color}-500/40 flex items-center justify-center`}>
              <LevelIcon className={`w-8 h-8 text-${lvl.color}-400`} />
            </div>
            <div className="flex-1">
              <div className="text-xs text-stone-400 uppercase tracking-wider">Threat Level</div>
              <div className={`font-serif text-4xl text-${lvl.color}-400`} data-testid="sec-threat-level">{lvl.label}</div>
              <div className="text-xs text-stone-500 mt-1">Bazat pe {overview.snapshot_window_hours}h de date</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-stone-400 uppercase tracking-wider">Security Score</div>
              <div className="font-serif text-5xl text-[#d4ff3a]" data-testid="sec-score">{overview.score}</div>
              <div className="text-[10px] text-stone-500">/ 100</div>
            </div>
          </div>
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
            <div className="text-xs text-stone-400 uppercase tracking-wider mb-3">Statistici rapide</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-stone-400">Events</span><span className="font-mono">{overview.stats.events_24h}</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Login-uri eșuate</span><span className="font-mono">{overview.stats.failed_logins_24h}</span></div>
              <div className="flex justify-between"><span className="text-stone-400">IP-uri unice (failed)</span><span className="font-mono">{overview.stats.unique_ip_failed}</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Incidente active</span><span className="font-mono text-amber-300">{overview.stats.active_incidents}</span></div>
              <div className="flex justify-between"><span className="text-stone-400">IP-uri în burst</span><span className="font-mono text-red-300">{overview.stats.burst_ips?.length || 0}</span></div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-4 mt-4">
          {/* Suspicious IPs */}
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Eye className="w-4 h-4 text-[#d4ff3a]" />
              <h2 className="font-serif text-lg">IP-uri suspecte</h2>
              <Pill className="ml-auto bg-white/5 border-white/10 text-stone-300">{overview.suspicious_ips.length}</Pill>
            </div>
            {overview.suspicious_ips.length === 0 && <div className="text-xs text-stone-500 italic py-4">Niciun IP suspect detectat în această fereastră.</div>}
            <div className="space-y-1">
              {overview.suspicious_ips.map(ip => (
                <div key={ip.ip} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5 text-xs" data-testid={`sec-ip-${ip.ip}`}>
                  <code className="font-mono">{ip.ip}</code>
                  {ip.failed_logins > 0 && <Pill className="bg-red-500/15 text-red-300 border-red-500/30">failed: {ip.failed_logins}</Pill>}
                  {ip.events > 0 && <Pill className="bg-amber-500/15 text-amber-300 border-amber-500/30">events: {ip.events}</Pill>}
                </div>
              ))}
            </div>
          </div>

          {/* Top event types */}
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-[#d4ff3a]" />
              <h2 className="font-serif text-lg">Top tipuri evenimente</h2>
            </div>
            {overview.top_event_types.length === 0 && <div className="text-xs text-stone-500 italic py-4">Niciun event înregistrat.</div>}
            <div className="space-y-2">
              {overview.top_event_types.map(t => (
                <div key={t.type} className="flex items-center gap-3">
                  <span className="font-mono text-xs text-stone-300 flex-1 truncate">{t.type}</span>
                  <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
                    <div className="bg-[#d4ff3a] h-full" style={{ width: `${Math.min(100, (t.count / overview.top_event_types[0].count) * 100)}%` }} />
                  </div>
                  <span className="font-mono text-xs text-stone-400 w-10 text-right">{t.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Active incidents */}
        {overview.active_incidents.length > 0 && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5 mt-4">
            <h2 className="font-serif text-lg mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Incidente active</h2>
            <div className="space-y-2">
              {overview.active_incidents.map(inc => (
                <div key={inc.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5 text-xs">
                  <Pill className="bg-amber-500/15 text-amber-300 border-amber-500/30">{inc.severity || "?"}</Pill>
                  <span className="flex-1">{inc.title}</span>
                  <span className="text-stone-500">{inc.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Analysis */}
        <div className="bg-gradient-to-br from-[#d4ff3a]/10 to-violet-500/10 border border-[#d4ff3a]/30 rounded-3xl p-6 mt-5">
          <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
            <div>
              <h2 className="font-serif text-xl flex items-center gap-2"><Brain className="w-5 h-5 text-[#d4ff3a]" /> AI Security Analysis</h2>
              <p className="text-xs text-stone-400 mt-1">Claude analizează evenimentele recente și propune acțiuni defensive.</p>
            </div>
            <button onClick={runAI} disabled={analyzing} className="pm-btn pm-btn-primary" data-testid="sec-analyze-btn">
              {analyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> Analizez...</> : <><Sparkles className="w-4 h-4" /> Rulează analiza AI</>}
            </button>
          </div>

          {aiRecs && !aiRecs.error && (
            <div className="space-y-4 mt-4" data-testid="sec-ai-recs">
              <p className="text-sm text-stone-200">{aiRecs.summary}</p>

              {aiRecs.threat_patterns?.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-amber-400 mb-2">Pattern-uri identificate</div>
                  <div className="space-y-2">
                    {aiRecs.threat_patterns.map((p, i) => (
                      <div key={i} className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Pill className={p.severity === "critical" ? "bg-red-500/20 text-red-300 border-red-500/40" : p.severity === "high" ? "bg-orange-500/20 text-orange-300 border-orange-500/40" : "bg-amber-500/15 text-amber-300 border-amber-500/30"}>{p.severity}</Pill>
                          <span className="text-sm font-medium">{p.name}</span>
                          {p.evidence_count > 0 && <span className="text-[10px] text-stone-500">({p.evidence_count} evenimente)</span>}
                        </div>
                        <div className="text-xs text-stone-400">{p.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {aiRecs.recommendations?.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-[#d4ff3a] mb-2 flex items-center gap-1"><ListChecks className="w-3 h-3" /> Acțiuni recomandate</div>
                  <div className="space-y-2">
                    {aiRecs.recommendations.map((r, i) => (
                      <div key={i} className="bg-[#0a0a0b] border border-[#d4ff3a]/20 rounded-xl p-3 flex items-start gap-3">
                        <Pill className={r.priority === "P0" ? "bg-red-500/20 text-red-300 border-red-500/40" : r.priority === "P1" ? "bg-orange-500/20 text-orange-300 border-orange-500/40" : "bg-amber-500/15 text-amber-300 border-amber-500/30"}>{r.priority}</Pill>
                        <div className="flex-1 text-sm">{r.action}</div>
                        <Pill className="bg-stone-500/15 text-stone-400 border-stone-500/30">{r.category}</Pill>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-[10px] text-stone-500 italic pt-2 border-t border-white/5">{aiRecs.score_delta_reason} · {aiRecs.provider} {aiRecs.model}</div>
            </div>
          )}
          {aiRecs?.error && <div className="text-sm text-red-300 mt-3">{aiRecs.error}</div>}
        </div>
      </div>
    </div>
  );
}
