// AI Concierge Bubble — floating chat widget for client/specialist/operator.
// Mounted globally; auto-hides for admins (admin has dedicated AdminAIConsole).
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Bot, Send, X, MessageCircle, AlertTriangle, ShieldAlert, LifeBuoy } from "lucide-react";
import { useAuth } from "../auth";
import { API } from "../pages/DashShared";

const SUGGESTIONS_BY_ROLE = {
  client: [
    "Cum activez Digital Twin pentru proprietatea mea?",
    "Cum funcționează plata în escrow pe milestone-uri?",
    "Cum aleg cel mai bun specialist?",
  ],
  specialist: [
    "Cum accept un lead și cât costă?",
    "Cum îmi cresc Trust Score-ul?",
    "Cum setez zonele de acoperire?",
  ],
  operator: [
    "Cum validez un twin?",
    "Cum raportez o non-conformitate?",
    "Unde văd twin-urile în pending?",
  ],
};

const ROLE_TITLES = {
  client: "Asistent Client",
  specialist: "Asistent Specialist",
  operator: "Asistent Operator",
};

export const AIConciergeBubble = () => {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const h = () => setOpen(true);
    window.addEventListener("pm-open-ai", h);
    return () => window.removeEventListener("pm-open-ai", h);
  }, []);
  // Anunță AssistantDock când panoul e deschis (dock-ul se ascunde → zero suprapuneri)
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("pm-ai-state", { detail: { open } }));
  }, [open]);
  const [enabled, setEnabled] = useState(false);
  const [supportEmail, setSupportEmail] = useState("contact@propmanage.ro");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem("pm_concierge_session") || null);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  // Effective role (handles dual-role specialists viewing as client)
  const role = user?.active_view || user?.role;
  const hidden = !user || user === false || user.role === "admin";

  // Bootstrap settings
  useEffect(() => {
    if (hidden) return;
    axios.get(`${API}/concierge/settings/public`)
      .then(r => {
        setEnabled(!!r.data?.enabled && !r.data?.is_blocked);
        if (r.data?.support_email) setSupportEmail(r.data.support_email);
      })
      .catch(() => setEnabled(false));
  }, [hidden, user?.id]);

  // Load history on open
  useEffect(() => {
    if (!open || !sessionId) return;
    axios.get(`${API}/concierge/history?session_id=${sessionId}`)
      .then(r => setMessages(r.data?.messages || []))
      .catch(() => setMessages([]));
  }, [open, sessionId]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || sending) return;
    setInput("");
    setError(null);
    setSending(true);
    const optimistic = { role: "user", content: msg, created_at: new Date().toISOString() };
    setMessages(m => [...m, optimistic]);
    try {
      const r = await axios.post(`${API}/concierge/chat`, { message: msg, session_id: sessionId });
      const newSid = r.data?.session_id || sessionId;
      if (newSid !== sessionId) {
        setSessionId(newSid);
        sessionStorage.setItem("pm_concierge_session", newSid);
      }
      setMessages(m => [...m, {
        role: "assistant",
        content: r.data?.message || "—",
        blocked: !!r.data?.blocked,
        escalated: !!r.data?.escalated,
        escalation_topic: r.data?.escalation_topic,
        created_at: new Date().toISOString(),
      }]);
    } catch (e) {
      const msg429 = e?.response?.status === 429;
      setError(msg429 ? "Ai depășit limita de mesaje. Revino în câteva minute." : (e?.response?.data?.detail || "Eroare necunoscută."));
    } finally {
      setSending(false);
    }
  };

  const openSupportMail = (topic) => {
    const subj = encodeURIComponent(`[PropManage Support] ${topic || "Cerere asistență"}`);
    const recent = messages.slice(-6).map(m => `${m.role === "user" ? "Eu" : "Asistent"}: ${m.content}`).join("\n\n");
    const body = encodeURIComponent(`Bună,\n\nAm nevoie de ajutor cu:\n\n[descrie problema aici]\n\n— Context conversație recentă —\n${recent}\n\nMulțumesc!`);
    window.location.href = `mailto:${supportEmail}?subject=${subj}&body=${body}`;
  };

  const resetSession = () => {
    sessionStorage.removeItem("pm_concierge_session");
    setSessionId(null);
    setMessages([]);
  };

  if (hidden || !enabled) return null;

  const suggestions = SUGGESTIONS_BY_ROLE[role] || SUGGESTIONS_BY_ROLE.client;
  const title = ROLE_TITLES[role] || "Asistent PropManage";

  return (
    <>
      {/* Lansarea se face prin AssistantDock (FAB unificat) via evenimentul "pm-open-ai" */}
      {/* Chat panel */}
      {open && (
        <div
          className="fixed inset-x-2 bottom-2 lg:inset-x-auto lg:right-6 lg:bottom-6 lg:w-[400px] z-[55] flex flex-col rounded-2xl shadow-2xl border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 max-h-[80vh]"
          data-testid="concierge-bubble-panel"
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-[#d4ff3a]/15 to-emerald-500/10 rounded-t-2xl">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-black" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-slate-900 dark:text-slate-100">{title}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Online · Claude Sonnet 4.5
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
              data-testid="concierge-close"
              aria-label="Închide"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-[320px]" data-testid="concierge-messages">
            {messages.length === 0 && (
              <div className="text-center pt-6 pb-2">
                <Bot className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                <div className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                  Salut! Sunt aici să te ajut cu PropManage. Întreabă-mă orice sau alege o sugestie:
                </div>
                <div className="space-y-2">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => send(s)}
                      disabled={sending}
                      className="block w-full text-left text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                      data-testid={`concierge-suggestion-${i}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-[#d4ff3a] text-black rounded-br-sm"
                    : m.blocked
                      ? "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-500/30 rounded-bl-sm"
                      : m.escalated
                        ? "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 rounded-bl-sm"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-sm"
                }`}>
                  {m.role === "assistant" && m.blocked && (
                    <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold mb-1 opacity-70">
                      <ShieldAlert className="w-3 h-3" /> Blocat
                    </div>
                  )}
                  {m.content}
                  {m.role === "assistant" && m.escalated && (
                    <button
                      onClick={() => openSupportMail(m.escalation_topic)}
                      className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold"
                      data-testid="concierge-contact-support"
                    >
                      <LifeBuoy className="w-3.5 h-3.5" />
                      Contactează suport
                    </button>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-slate-100 dark:bg-slate-800 px-3 py-2 rounded-2xl text-sm text-slate-500 italic">
                  Asistentul gândește...
                </div>
              </div>
            )}
            {error && (
              <div className="flex items-start gap-1.5 text-xs text-red-600 bg-red-50 dark:bg-red-500/10 dark:text-red-300 border border-red-200 dark:border-red-500/30 rounded-lg px-3 py-2">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Footer */}
          <div className="border-t border-slate-200 dark:border-slate-700 p-2 flex items-center gap-2">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Scrie un mesaj..."
              rows={1}
              className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm resize-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400"
              disabled={sending}
              data-testid="concierge-input"
            />
            <button
              onClick={() => send()}
              disabled={sending || !input.trim()}
              className="p-2 rounded-lg bg-[#d4ff3a] hover:bg-[#bce82e] text-black disabled:opacity-40 disabled:cursor-not-allowed"
              data-testid="concierge-send"
              aria-label="Trimite"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="px-3 pb-2 flex items-center justify-between text-[10px] text-slate-400">
            <span>Conversațiile pot fi revizuite de echipa de moderare.</span>
            {messages.length > 0 && (
              <button onClick={resetSession} className="hover:text-slate-700 dark:hover:text-slate-200 underline" data-testid="concierge-reset">
                Resetează
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default AIConciergeBubble;
