// Twin Orchestrator — natural-language Q&A chat for super-admins.
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Bot, Send, Loader2, Sparkles, RefreshCw, User, Zap, CheckCircle2, Clock, X } from "lucide-react";
import { API } from "../DashShared";

const SUGGESTED_QUESTIONS = [
  "Care e tier-ul curent și de ce?",
  "Câți admini au făcut acțiuni denied astăzi?",
  "Ce ar trebui să fac ca scorul DEV să crească?",
  "Twin, rulează Auto-Tune în fiecare luni la 06:00",
  "Twin, trimite digest în fiecare 1 a lunii la 09:00",
  "Twin, ia un snapshot mâine la 09:00",
];

const Bubble = ({ role, content, ts, actionProposal, onConfirm, executing, executedResult }) => {
  const isUser = role === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}
      data-testid={`twin-bubble-${role}`}
    >
      <div className={`flex gap-2 max-w-[80%] ${isUser ? "flex-row-reverse" : ""}`}>
        <div
          className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
            isUser
              ? "bg-violet-500/15 text-violet-600 dark:text-violet-300"
              : "bg-gradient-to-br from-fuchsia-500 to-cyan-500 text-white"
          }`}
        >
          {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
        </div>
        <div className="min-w-0">
          <div
            className={`rounded-2xl px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
              isUser
                ? "bg-violet-500 text-white rounded-tr-sm"
                : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-tl-sm border border-slate-200 dark:border-slate-700"
            }`}
          >
            {content}
          </div>

          {/* ACTION PROPOSAL — confirm button under the bubble */}
          {actionProposal && !executedResult && (
            <div
              className="mt-2 p-3 rounded-xl border border-fuchsia-500/40 bg-gradient-to-br from-fuchsia-500/10 to-violet-500/5"
              data-testid="twin-action-proposal"
            >
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-bold text-fuchsia-700 dark:text-fuchsia-300 mb-1">
                <Zap className="w-3 h-3" />
                {actionProposal.schedule_info ? "Programare propusă" : "Acțiune propusă"}
              </div>
              <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {actionProposal.label}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {actionProposal.description} · ~{actionProposal.estimated_seconds}s
              </div>
              {actionProposal.schedule_info && (
                <div className="mt-2 text-xs px-2 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-700 dark:text-cyan-300 inline-flex items-center gap-1.5">
                  ⏰ <strong>{actionProposal.schedule_info.label}</strong>
                  <span className="text-[10px] opacity-75">({actionProposal.schedule_info.kind === "cron" ? "recurent" : "o singură dată"})</span>
                </div>
              )}
              <div className="flex gap-2 mt-2.5">
                <button
                  onClick={onConfirm}
                  disabled={executing}
                  className="text-xs px-3 py-1.5 rounded-lg bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white font-semibold shadow disabled:opacity-50 inline-flex items-center gap-1.5"
                  data-testid="twin-action-confirm"
                >
                  {executing ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                  {executing
                    ? (actionProposal.schedule_info ? "Programează..." : "Execută...")
                    : (actionProposal.schedule_info ? "Confirmă & programează" : "Confirmă & execută")}
                </button>
                <span className="text-[10px] text-slate-400 self-center">
                  Token TTL 5min · single-use
                </span>
              </div>
            </div>
          )}

          {/* EXECUTION RESULT */}
          {executedResult && (
            <div
              className="mt-2 p-3 rounded-xl border border-emerald-500/40 bg-emerald-500/5 text-xs text-emerald-700 dark:text-emerald-300"
              data-testid="twin-action-result"
            >
              <div className="flex items-center gap-2 font-semibold mb-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Executat: {executedResult.label}
              </div>
              <pre className="text-[10px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
{JSON.stringify(executedResult.result, null, 2).slice(0, 400)}
              </pre>
            </div>
          )}

          {ts && (
            <div className={`text-[10px] mt-1 text-slate-400 ${isUser ? "text-right" : ""}`}>
              {new Date(ts).toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const TwinPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const scrollerRef = useRef(null);

  useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const send = async (question) => {
    const q = (question || input).trim();
    if (!q || loading) return;
    setInput("");
    setError(null);
    const userMsg = { role: "user", content: q, ts: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/admin/twin/ask`, {
        question: q,
        session_id: sessionId,
      });
      if (!sessionId && data.session_id) setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          ts: new Date().toISOString(),
          actionProposal: data.action_proposal || null,
        },
      ]);
    } catch (e) {
      const status = e?.response?.status;
      const msg = status === 403
        ? "Doar super-admin poate folosi Twin Orchestrator."
        : status === 404
        ? "Endpoint indisponibil — necesită REDEPLOY la producție."
        : status === 500
        ? `Eroare server: ${e?.response?.data?.detail || "necunoscută"}`
        : `Eroare: ${e?.message || "verifică conexiunea"}`;
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠ ${msg}`, ts: new Date().toISOString() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const [executingIdx, setExecutingIdx] = useState(null);

  const confirmAction = async (msgIdx) => {
    const msg = messages[msgIdx];
    if (!msg?.actionProposal || executingIdx !== null) return;
    setExecutingIdx(msgIdx);
    try {
      const { data } = await axios.post(`${API}/admin/twin/execute-action`, {
        action_key: msg.actionProposal.action_key,
        confirmation_token: msg.actionProposal.confirmation_token,
        session_id: sessionId,
      });
      setMessages((prev) =>
        prev.map((m, i) =>
          i === msgIdx ? { ...m, executedResult: data, actionProposal: null } : m
        )
      );
    } catch (e) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || e?.message;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠ Execuție eșuată (HTTP ${status || "?"}): ${detail}`,
          ts: new Date().toISOString(),
        },
      ]);
    } finally {
      setExecutingIdx(null);
    }
  };

  const resetSession = () => {
    setMessages([]);
    setSessionId(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6" data-testid="twin-page">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-fuchsia-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-fuchsia-500/30">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Twin Orchestrator</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Întreabă AI-ul orice despre platformă. Răspunde citind live din baza de date.
            </p>
          </div>
          {sessionId && (
            <button
              onClick={resetSession}
              className="ml-auto text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 inline-flex items-center gap-1.5"
              data-testid="twin-reset"
            >
              <RefreshCw className="w-3 h-3" /> Sesiune nouă
            </button>
          )}
        </div>
      </div>

      {/* Chat container */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 flex flex-col h-[calc(100vh-260px)] min-h-[440px]">
        <div ref={scrollerRef} className="flex-1 overflow-y-auto p-4" data-testid="twin-messages">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <Sparkles className="w-10 h-10 text-fuchsia-400 mb-3" />
              <div className="text-base font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Salut! Sunt Twin.
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400 max-w-md mb-5">
                Pot răspunde la întrebări despre tier, scoruri, acțiuni admin, alerte, autopilot runs și ROI.
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTED_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => send(q)}
                    className="text-left text-xs px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-fuchsia-400 dark:hover:border-fuchsia-500 hover:bg-fuchsia-50 dark:hover:bg-fuchsia-500/5 text-slate-600 dark:text-slate-300 transition-colors"
                    data-testid={`twin-suggested-${i}`}
                  >
                    💬 {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <Bubble
              key={i}
              {...m}
              onConfirm={() => confirmAction(i)}
              executing={executingIdx === i}
            />
          ))}
          {loading && (
            <div className="flex justify-start mb-3">
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-fuchsia-500 to-cyan-500 flex items-center justify-center">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-tl-sm px-3.5 py-2 inline-flex items-center gap-2 border border-slate-200 dark:border-slate-700">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-fuchsia-500" />
                  <span className="text-xs text-slate-500 dark:text-slate-400">Twin analizează...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="border-t border-slate-200 dark:border-slate-700 p-3 flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Întreabă orice despre platformă... (ex: de ce a scăzut scorul?)"
            disabled={loading}
            className="flex-1 px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-100 focus:outline-none focus:border-fuchsia-400 disabled:opacity-50"
            data-testid="twin-input"
            maxLength={600}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-violet-600 text-white text-sm font-semibold shadow disabled:opacity-50 inline-flex items-center gap-1.5"
            data-testid="twin-send"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span className="hidden sm:inline">Trimite</span>
          </button>
        </form>
      </div>

      {error && (
        <div className="mt-3 text-xs text-rose-600 dark:text-rose-400" data-testid="twin-error">
          {error}
        </div>
      )}

      <ScheduledActionsPanel />

      <div className="mt-3 text-[11px] text-slate-400 dark:text-slate-500">
        🔒 Doar super-admin · Citește read-only din MongoDB · Powered by Claude Sonnet 4.5
      </div>
    </div>
  );
};

// =========================== SCHEDULED ACTIONS PANEL ===========================
const ScheduledActionsPanel = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/twin/scheduled`);
      setItems(data?.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const cancel = async (id) => {
    if (!window.confirm("Anulezi această programare?")) return;
    setCancelling(id);
    try {
      await axios.delete(`${API}/admin/twin/scheduled/${id}`);
      await load();
    } finally {
      setCancelling(null);
    }
  };

  const active = items.filter((i) => i.status === "active");

  return (
    <div className="mt-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-4" data-testid="twin-scheduled-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-500" />
          <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            Programări active <span className="text-xs text-slate-400 font-normal">({active.length})</span>
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-[11px] px-2 py-1 rounded text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 inline-flex items-center gap-1"
          data-testid="twin-scheduled-refresh"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>
      {active.length === 0 ? (
        <div className="text-xs text-slate-400 dark:text-slate-500 italic" data-testid="twin-scheduled-empty">
          Nicio programare activă. Spune-i lui Twin: &bdquo;rulează Auto-Tune în fiecare luni la 06:00&rdquo;.
        </div>
      ) : (
        <ul className="space-y-1.5" data-testid="twin-scheduled-list">
          {active.map((s, i) => (
            <li
              key={s.id}
              className="flex flex-wrap items-center gap-2 text-[12px] px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-700/40"
              data-testid={`twin-scheduled-${i}`}
            >
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${s.kind === "cron" ? "bg-cyan-500/15 text-cyan-600 dark:text-cyan-300" : "bg-amber-500/15 text-amber-600 dark:text-amber-300"}`}>
                {s.kind === "cron" ? "recurent" : "o dată"}
              </span>
              <span className="font-medium text-slate-700 dark:text-slate-200">{s.action_key}</span>
              <span className="text-slate-500 dark:text-slate-400">→ {s.label}</span>
              {s.run_count > 0 && (
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400">✓ rulat de {s.run_count}× </span>
              )}
              <button
                onClick={() => cancel(s.id)}
                disabled={cancelling === s.id}
                className="ml-auto text-[10px] text-rose-500 hover:text-rose-700 inline-flex items-center gap-1 disabled:opacity-50"
                data-testid={`twin-scheduled-cancel-${i}`}
                title="Anulează programarea"
              >
                {cancelling === s.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <X className="w-3 h-3" />}
                Anulează
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TwinPage;
