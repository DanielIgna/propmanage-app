import React, { useState } from "react";
import axios from "axios";
import { Sparkles, Send, Loader2, X, MessageSquare } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

/**
 * Compact floating widget that lets the user ask natural-language questions
 * about a Digital Twin project. Drop it into any twin-related page:
 *   <TwinAIQA projectId={twin.id} />
 */
export default function TwinAIQA({ projectId, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const ask = async () => {
    if (!question.trim() || !projectId) return;
    setAsking(true);
    setError(null);
    const q = question.trim();
    setQuestion("");
    try {
      const { data } = await ax.post("/api/digital-twin/qa/ask", {
        project_id: projectId,
        question: q,
        session_id: sessionId,
      });
      setSessionId(data.session_id);
      setHistory(h => [...h, { q, a: data.answer, ts: Date.now() }]);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la întrebare");
    } finally { setAsking(false); }
  };

  const suggestions = [
    "Care este suprafața livingului?",
    "Unde este tabloul electric?",
    "Ce finisaje sunt în baie?",
    "Câte camere are apartamentul?",
  ];

  if (!projectId) return null;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed right-6 z-40 pm-btn pm-btn-primary pm-btn-lg shadow-2xl shadow-[#d4ff3a]/20"
        style={{ bottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))" }}
        data-testid="twin-ai-open"
      >
        <Sparkles className="w-4 h-4" /> Întreabă Digital Twin
      </button>
    );
  }

  return (
    <div className="fixed right-6 z-40 w-[400px] max-w-[calc(100vw-3rem)] bg-[#0e0e10] border border-white/10 rounded-3xl shadow-2xl overflow-hidden flex flex-col" style={{maxHeight: "70vh", bottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))"}} data-testid="twin-ai-panel">
      <div className="flex items-center gap-2 p-4 border-b border-white/10">
        <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
        <h3 className="font-serif text-lg">Digital Twin AI</h3>
        <button onClick={() => setOpen(false)} className="ml-auto text-stone-400 hover:text-white"><X className="w-4 h-4" /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {history.length === 0 && !asking && (
          <>
            <p className="text-xs text-stone-400">Întreabă orice despre modelul 3D, planurile 2D, camerele și echipamentele acestui proiect.</p>
            <div className="grid grid-cols-1 gap-1.5">
              {suggestions.map((s, i) => (
                <button key={i} onClick={() => setQuestion(s)} className="text-left text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-3 py-2 transition-colors" data-testid={`twin-ai-suggest-${i}`}>
                  {s}
                </button>
              ))}
            </div>
          </>
        )}
        {history.map((h, i) => (
          <div key={i} className="space-y-2" data-testid={`twin-ai-turn-${i}`}>
            <div className="bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 rounded-xl px-3 py-2 ml-6">
              <div className="text-[10px] uppercase tracking-wider text-[#d4ff3a]">Tu</div>
              <div className="text-sm">{h.q}</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 mr-6">
              <div className="text-[10px] uppercase tracking-wider text-stone-400 flex items-center gap-1"><MessageSquare className="w-3 h-3" /> AI</div>
              <div className="text-sm whitespace-pre-wrap leading-relaxed">{h.a}</div>
            </div>
          </div>
        ))}
        {asking && <div className="text-xs text-stone-400 flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> AI analizează Digital Twin-ul...</div>}
        {error && <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-xl px-3 py-2">{error}</div>}
      </div>

      <div className="p-3 border-t border-white/10 flex gap-2">
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !asking && ask()}
          placeholder="Întreabă..."
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
          data-testid="twin-ai-input"
        />
        <button onClick={ask} disabled={asking || !question.trim()} className="pm-btn pm-btn-primary pm-btn-sm" data-testid="twin-ai-send">
          {asking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}
