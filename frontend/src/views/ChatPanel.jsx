// Real-time chat panel for a request (client <-> specialist)
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Send, MessageSquare, X } from "lucide-react";
import { useAuth } from "../auth";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

export const ChatPanel = ({ requestId, onClose }) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const scrollRef = useRef(null);

  // Load history
  useEffect(() => {
    axios.get(`${API}/chat/${requestId}/messages`).then(r => setMessages(r.data)).catch(() => {});
  }, [requestId]);

  // WS connection
  useEffect(() => {
    if (!user || user === false) return;
    
    // Read JWT from cookies to send via query param (WebSocket can't send cookies cross-origin reliably)
    // We'll fetch a short-lived ws token via /api/auth/me
    let isMounted = true;
    
    const connect = async () => {
      try {
        // Get cookies-based token by calling auth/me - we need to extract JWT
        // Simpler: use the access_token from document.cookie if accessible (httpOnly cookies aren't readable)
        // Alternative: backend already accepts token query param
        const cookies = document.cookie.split(";").map(c => c.trim());
        const tokenCookie = cookies.find(c => c.startsWith("access_token="));
        let token = tokenCookie ? tokenCookie.split("=")[1] : null;
        
        // Since access_token is httpOnly, we need a backend endpoint to issue WS token
        // Fallback: use a query token from a dedicated endpoint
        if (!token) {
          const { data } = await axios.get(`${API}/auth/ws-token`, { withCredentials: true });
          token = data.token;
        }
        
        const wsUrl = process.env.NEXT_PUBLIC_BACKEND_URL.replace(/^http/, "ws") + `/api/ws/chat/${requestId}?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => { if (isMounted) setConnected(true); };
        ws.onclose = () => { if (isMounted) setConnected(false); };
        ws.onerror = (e) => console.error("WS error", e);
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (isMounted) setMessages(prev => [...prev, msg]);
          } catch {}
        };
        wsRef.current = ws;
      } catch (e) {
        console.error("WS connect failed", e);
      }
    };
    connect();
    
    return () => {
      isMounted = false;
      if (wsRef.current) wsRef.current.close();
    };
  }, [requestId, user]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ text }));
    setInput("");
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-6" onClick={onClose}>
      <div className="glass-strong rounded-3xl w-full max-w-lg h-[600px] flex flex-col" onClick={e => e.stopPropagation()} data-testid="chat-panel">
        <div className="flex items-center justify-between p-5 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#d4ff3a]/15 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-[#d4ff3a]" />
            </div>
            <div>
              <div className="font-medium">Chat lucrare</div>
              <div className="text-[10px] text-stone-500 flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-stone-600"}`} />
                {connected ? "Conectat" : "Se conectează..."}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="chat-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div ref={scrollRef} className="flex-1 overflow-auto p-5 space-y-3 no-scrollbar">
          {messages.length === 0 && (
            <div className="text-center text-xs text-stone-500 py-8">Începe conversația...</div>
          )}
          {messages.map((m, i) => {
            if (m.type === "system") {
              return <div key={i} className="text-center text-[10px] text-stone-500 uppercase tracking-wider">{m.text}</div>;
            }
            const mine = m.user_id === user?.id;
            return (
              <div key={i} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[75%] ${mine ? "bg-[#d4ff3a] text-black" : "bg-white/5"} rounded-2xl px-4 py-2.5`}>
                  {!mine && <div className="text-[10px] opacity-70 mb-1">{m.user_name}</div>}
                  <div className="text-sm">{m.text}</div>
                  <div className={`text-[9px] mt-1 ${mine ? "opacity-50" : "opacity-40"}`}>
                    {new Date(m.timestamp).toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        <div className="p-4 border-t border-white/5 flex gap-2">
          <input
            type="text" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Scrie un mesaj..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
            data-testid="chat-input"
            disabled={!connected}
          />
          <button onClick={send} disabled={!connected || !input.trim()} className="btn-accent px-4 rounded-xl disabled:opacity-50" data-testid="chat-send">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
