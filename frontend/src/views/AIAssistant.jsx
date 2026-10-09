// AI Assistant - Floating chatbot widget (Claude Haiku 4.5)
import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, X, Send, Sparkles, MessageCircle } from "lucide-react";
import { useAuth } from "../auth";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const SUGGESTIONS_BY_ROLE = {
  client: ["AC nu mai răcește în living", "Cum funcționează escrow?", "Ce sunt tokens?"],
  specialist: ["Cum devin VERIFIED?", "Cum funcționează lead-urile?", "Sfaturi de rating"],
  admin: ["Cum verific specialiști?", "Cum funcționează disputele?"],
  operator: ["Cum validez log-uri?", "Cum actualizez 3D models?"],
};

export const AIAssistant = () => {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const scrollRef = useRef(null);

  // Load history when opened
  useEffect(() => {
    if (open && user && user !== false && messages.length === 0) {
      // Greeting
      setMessages([{
        role: "assistant",
        text: `Salut, ${user.name?.split(" ")[0] || "utilizator"}! Sunt PropManage Assistant. Cu ce te pot ajuta?`
      }]);
    }
  }, [open, user]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async (text) => {
    const message = (text || input).trim();
    if (!message || loading) return;
    setInput("");
    setMessages(m => [...m, { role: "user", text: message }]);
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/ai/chat`, { message, session_id: sessionId });
      setMessages(m => [...m, { role: "assistant", text: data.reply }]);
    } catch (e) {
      setMessages(m => [...m, { role: "assistant", text: "Hmm, am o problemă tehnică. Reîncearcă!", error: true }]);
    } finally {
      setLoading(false);
    }
  };

  if (!user || user === false) return null;
  const suggestions = SUGGESTIONS_BY_ROLE[user.role] || SUGGESTIONS_BY_ROLE.client;

  return (
    <>
      {/* Floating trigger */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-20 sm:bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] shadow-2xl shadow-[#d4ff3a]/30 flex items-center justify-center hover:scale-110 transition-transform"
        data-testid="ai-trigger"
      >
        {open ? <X className="w-5 h-5 text-black" /> : <Bot className="w-6 h-6 text-black" />}
        {!open && <span className="absolute top-0 right-0 w-3 h-3 rounded-full bg-emerald-500 border-2 border-[#0a0a0b] pulse-dot" />}
      </button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.95 }}
            className="fixed bottom-32 sm:bottom-24 right-6 z-40 w-[380px] max-w-[calc(100vw-3rem)] h-[560px] max-h-[calc(100vh-10rem)] glass-strong rounded-3xl flex flex-col overflow-hidden border border-white/10"
            data-testid="ai-panel"
          >
            <div className="p-5 border-b border-white/5 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-black" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium flex items-center gap-2">PropManage Assistant 
                  <span className="text-[9px] bg-[#d4ff3a]/15 text-[#d4ff3a] px-1.5 py-0.5 rounded uppercase tracking-wider">AI</span>
                </div>
                <div className="text-[10px] text-stone-500">Powered by Claude Haiku 4.5</div>
              </div>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-auto p-5 space-y-3 no-scrollbar">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === "user" ? "bg-[#d4ff3a] text-black" : m.error ? "bg-red-500/10 text-red-300" : "bg-white/5 text-stone-100"
                  }`}>
                    <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white/5 rounded-2xl px-4 py-3 flex gap-1.5">
                    <span className="w-1.5 h-1.5 bg-[#d4ff3a] rounded-full animate-bounce" style={{animationDelay: "0ms"}} />
                    <span className="w-1.5 h-1.5 bg-[#d4ff3a] rounded-full animate-bounce" style={{animationDelay: "150ms"}} />
                    <span className="w-1.5 h-1.5 bg-[#d4ff3a] rounded-full animate-bounce" style={{animationDelay: "300ms"}} />
                  </div>
                </div>
              )}
              {messages.length <= 1 && !loading && (
                <div className="space-y-2 pt-2">
                  <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-2">Sugestii rapide</div>
                  {suggestions.map((s, i) => (
                    <button key={i} onClick={() => send(s)}
                      className="w-full text-left text-xs bg-white/5 hover:bg-white/10 rounded-xl px-3 py-2 transition"
                      data-testid={`ai-suggest-${i}`}>
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="p-3 border-t border-white/5 flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && send()}
                placeholder="Întreabă orice..."
                disabled={loading}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-[#d4ff3a]/50 disabled:opacity-50"
                data-testid="ai-input"
              />
              <button onClick={() => send()} disabled={loading || !input.trim()} className="btn-accent px-3 rounded-xl disabled:opacity-50" data-testid="ai-send">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
