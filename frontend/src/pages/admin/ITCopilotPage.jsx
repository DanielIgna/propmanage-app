// AI Performance Copilot — analyzes the IT team's metrics with Claude Sonnet 4.5.
// Route: /admin/it-collaborators/copilot
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Bot, Loader2, ChevronLeft, Sparkles, AlertTriangle, TrendingUp,
  TrendingDown, CheckCircle2, AlertCircle, RotateCcw, Send, Clock, History,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const RISK_META = {
  low: { color: "text-emerald-700 bg-emerald-100 dark:text-emerald-300 dark:bg-emerald-500/15", icon: CheckCircle2 },
  medium: { color: "text-amber-700 bg-amber-100 dark:text-amber-300 dark:bg-amber-500/15", icon: AlertCircle },
  high: { color: "text-rose-700 bg-rose-100 dark:text-rose-300 dark:bg-rose-500/15", icon: AlertTriangle },
};

const ITCopilotPage = () => {
  const [team, setTeam] = useState([]);
  const [loadingTeam, setLoadingTeam] = useState(true);
  const [question, setQuestion] = useState("");
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [digest, setDigest] = useState(null);
  const [digestBusy, setDigestBusy] = useState(false);
  const [digestMsg, setDigestMsg] = useState("");

  useEffect(() => {
    ax.get("/api/admin/it-collaborators?status=active")
      .then(r => setTeam(r.data?.items || []))
      .catch(() => {})
      .finally(() => setLoadingTeam(false));
    ax.get("/api/admin/it-collaborators/copilot/history?limit=5")
      .then(r => setHistory(r.data?.items || []))
      .catch(() => {});
    ax.get("/api/admin/it-collaborators/digest/settings")
      .then(r => setDigest(r.data))
      .catch(() => {});
  }, []);

  const saveDigest = async (patch) => {
    try {
      const { data } = await ax.post("/api/admin/it-collaborators/digest/settings", patch);
      setDigest(data);
      setDigestMsg("Setări salvate.");
      setTimeout(() => setDigestMsg(""), 2500);
    } catch (err) {
      setDigestMsg(err.response?.data?.detail || err.message);
    }
  };

  const sendDigestNow = async () => {
    setDigestBusy(true); setDigestMsg("");
    try {
      const { data } = await ax.post("/api/admin/it-collaborators/digest/run");
      setDigestMsg(`Trimis către ${data.sent_to} prin ${data.provider}. Risk: ${data.report?.risk_level}.`);
      ax.get("/api/admin/it-collaborators/digest/settings").then(r => setDigest(r.data));
    } catch (err) {
      setDigestMsg(err.response?.data?.detail || err.message);
    } finally { setDigestBusy(false); }
  };

  const analyze = async () => {
    setBusy(true); setError(""); setReport(null);
    try {
      const { data } = await ax.post("/api/admin/it-collaborators/copilot/analyze", {
        question: question.trim() || null,
      });
      setReport(data);
      // refresh history
      ax.get("/api/admin/it-collaborators/copilot/history?limit=5")
        .then(r => setHistory(r.data?.items || []))
        .catch(() => {});
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally { setBusy(false); }
  };

  const riskInfo = report ? (RISK_META[report.risk_level] || RISK_META.medium) : null;
  const RiskIcon = riskInfo?.icon || AlertCircle;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="it-copilot-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin/it-collaborators" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm">
          <ChevronLeft className="w-4 h-4" /> IT Collaborators
        </Link>
        <span className="text-slate-300">·</span>
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-500" />
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">AI Performance Copilot</h1>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-400">Claude Sonnet 4.5</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input column */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Analiză performanță
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Copilot-ul analizează metricile celor <strong>{team.length}</strong> colaboratori activi (bug-uri, task-uri, review score) și sugerează acțiuni concrete.
            </p>
            <div className="mt-4">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Întrebare opțională</label>
              <textarea
                value={question}
                onChange={e => setQuestion(e.target.value)}
                rows={3}
                placeholder="Ex: Cine ar trebui să primească o promovare în Q1? Există un risc de burnout?"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm"
                data-testid="copilot-question"
              />
            </div>
            <button
              onClick={analyze}
              disabled={busy || team.length === 0}
              className="mt-3 w-full px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-60"
              data-testid="run-copilot"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {busy ? "Se analizează…" : "Rulează analiza"}
            </button>
            {error && <div className="mt-3 text-xs text-rose-500 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> {error}</div>}
          </div>

          {history.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" /> Rapoarte recente
              </div>
              <div className="space-y-2">
                {history.map(h => (
                  <button
                    key={h.id}
                    onClick={() => setReport(h)}
                    className="w-full text-left p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-100 dark:border-slate-800"
                    data-testid={`history-${h.id}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${(RISK_META[h.risk_level] || RISK_META.medium).color}`}>{h.risk_level}</span>
                      <span className="text-[10px] text-slate-400">{h.generated_at ? new Date(h.generated_at).toLocaleString("ro-RO") : ""}</span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2">{h.summary}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sprint Health Digest configuration */}
          {digest && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800" data-testid="digest-card">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Sprint Health Digest · Email săptămânal
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 mb-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!digest.enabled}
                  onChange={(e) => saveDigest({ enabled: e.target.checked })}
                  data-testid="digest-enabled"
                  className="w-4 h-4"
                />
                Activează trimitere automată
              </label>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div>
                  <label className="block text-[11px] text-slate-500 dark:text-slate-400 mb-1">Zi</label>
                  <select value={digest.day_of_week} onChange={e => saveDigest({ day_of_week: e.target.value })} className="w-full px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs" data-testid="digest-day">
                    <option value="mon">Luni</option>
                    <option value="tue">Marți</option>
                    <option value="wed">Miercuri</option>
                    <option value="thu">Joi</option>
                    <option value="fri">Vineri</option>
                    <option value="sat">Sâmbătă</option>
                    <option value="sun">Duminică</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-500 dark:text-slate-400 mb-1">Ora (24h)</label>
                  <input type="number" min="0" max="23" value={digest.hour} onChange={e => saveDigest({ hour: parseInt(e.target.value || 0) })} className="w-full px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs" data-testid="digest-hour" />
                </div>
              </div>
              <label className="block text-[11px] text-slate-500 dark:text-slate-400 mb-1">Email destinatar</label>
              <input
                type="email"
                value={digest.recipient_email}
                onBlur={(e) => e.target.value !== digest.recipient_email && saveDigest({ recipient_email: e.target.value })}
                onChange={(e) => setDigest({ ...digest, recipient_email: e.target.value })}
                className="w-full px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs mb-3"
                data-testid="digest-email"
              />
              <button
                onClick={sendDigestNow}
                disabled={digestBusy}
                className="w-full px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium flex items-center justify-center gap-1.5 disabled:opacity-60"
                data-testid="digest-send-now"
              >
                {digestBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                {digestBusy ? "Se trimite…" : "Trimite test acum"}
              </button>
              {digestMsg && <div className="mt-2 text-[11px] text-emerald-600 dark:text-emerald-400">{digestMsg}</div>}
              {digest.last_sent_at && (
                <div className="mt-2 text-[10px] text-slate-400">
                  Ultim trimis: {new Date(digest.last_sent_at).toLocaleString("ro-RO")} · status: {digest.last_status}
                  {digest.last_error && <div className="text-rose-500 mt-0.5">{digest.last_error}</div>}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Report column */}
        <div className="lg:col-span-2">
          {!report && !busy && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-10 border-2 border-dashed border-slate-200 dark:border-slate-700 text-center">
              <Bot className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Niciun raport încă</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Apasă „Rulează analiza” pentru a primi un raport AI despre echipa IT.
              </p>
            </div>
          )}

          {busy && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-10 border border-slate-200 dark:border-slate-800 text-center">
              <Loader2 className="w-8 h-8 mx-auto animate-spin text-cyan-500 mb-3" />
              <p className="text-sm text-slate-500">Se analizează echipa cu Claude Sonnet 4.5…</p>
            </div>
          )}

          {report && (
            <div className="space-y-4" data-testid="copilot-report">
              {/* Risk + summary */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold uppercase ${riskInfo.color}`}>
                      <RiskIcon className="w-3.5 h-3.5" /> Risk: {report.risk_level}
                    </span>
                    <span className="text-xs text-slate-500">Sprint risk score: <strong className="text-slate-900 dark:text-white">{report.sprint_risk_score}/100</strong></span>
                  </div>
                  <span className="text-[10px] text-slate-400">{report.analyzed_count} colaboratori · {report.generated_at ? new Date(report.generated_at).toLocaleString("ro-RO") : ""}</span>
                </div>
                <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed" data-testid="report-summary">
                  {report.summary}
                </div>
              </div>

              {/* Two-column: performers vs at risk */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5" /> Top performers
                  </div>
                  {(report.top_performers || []).length === 0
                    ? <div className="text-xs text-slate-400">—</div>
                    : (report.top_performers || []).map((t, i) => (
                      <div key={i} className="py-2 border-b border-slate-100 dark:border-slate-800 last:border-0" data-testid={`top-performer-${i}`}>
                        <div className="text-sm font-semibold text-slate-900 dark:text-white">{t.name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{t.reason}</div>
                      </div>
                    ))
                  }
                </div>

                <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-2 flex items-center gap-1.5">
                    <TrendingDown className="w-3.5 h-3.5" /> În atenție
                  </div>
                  {(report.at_risk || []).length === 0
                    ? <div className="text-xs text-slate-400">—</div>
                    : (report.at_risk || []).map((t, i) => (
                      <div key={i} className="py-2 border-b border-slate-100 dark:border-slate-800 last:border-0" data-testid={`at-risk-${i}`}>
                        <div className="text-sm font-semibold text-slate-900 dark:text-white">{t.name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{t.reason}</div>
                        {t.recommended_action && (
                          <div className="mt-1 text-xs px-2 py-1 rounded bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300">
                            ➜ {t.recommended_action}
                          </div>
                        )}
                      </div>
                    ))
                  }
                </div>
              </div>

              {/* Team-wide recommendations */}
              {(report.team_recommendations || []).length > 0 && (
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Recomandări pentru echipă
                  </div>
                  <ul className="space-y-1.5">
                    {report.team_recommendations.map((r, i) => (
                      <li key={i} className="text-sm text-slate-700 dark:text-slate-200 flex items-start gap-2" data-testid={`recommendation-${i}`}>
                        <span className="text-cyan-500 mt-0.5">•</span> {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ITCopilotPage;
export { ITCopilotPage };
