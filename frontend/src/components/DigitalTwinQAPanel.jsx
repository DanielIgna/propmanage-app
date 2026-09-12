// Property Q&A on evidence — chat panel wired to /api/digital-twin/qa/ask.
// Grounded answers only (Property DNA + documents + works + models). No hallucinations.
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Sparkles, Send, X, Loader2, ShieldCheck, MessageSquare } from "lucide-react";
import { API } from "../pages/DashShared";

const SUGGESTIONS = [
  "Ce suprafață are proprietatea?",
  "Ce documente există?",
  "Ce lucrări au fost finalizate?",
  "Câte camere sunt și ce tip?",
];

export const DigitalTwinQAPanel = ({ projectId, projectName, onClose }) => {
  const [turns, setTurns] = useState([]); // { question, answer, error }
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [suggestions, setSuggestions] = useState([]); // { text, based_on }
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!projectId) return;
    setLoadingHistory(true);
    axios
      .get(`${API}/digital-twin/qa/history`, { params: { project_id: projectId, limit: 20 } })
      .then((r) => {
        const items = (r.data.items || []).slice().reverse(); // oldest → newest
        setTurns(items.map((t) => ({ question: t.question, answer: t.answer })));
        if (items.length) setSessionId(items[items.length - 1].session_id);
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
    // Evidence-based suggested questions (derived from the property's real data)
    axios
      .get(`${API}/digital-twin/qa/suggestions`, { params: { project_id: projectId } })
      .then((r) => setSuggestions(r.data.suggestions || []))
      .catch(() => setSuggestions([]));
  }, [projectId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const ask = async (question) => {
    const text = (question ?? q).trim();
    if (!text || busy) return;
    setBusy(true);
    setTurns((arr) => [...arr, { question: text, answer: null }]);
    setQ("");
    try {
      const { data } = await axios.post(`${API}/digital-twin/qa/ask`, {
        project_id: projectId,
        question: text,
        session_id: sessionId,
      });
      setSessionId(data.session_id);
      setTurns((arr) => {
        const copy = [...arr];
        copy[copy.length - 1] = { question: text, answer: data.answer };
        return copy;
      });
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message;
      setTurns((arr) => {
        const copy = [...arr];
        copy[copy.length - 1] = { question: text, answer: null, error: typeof msg === "string" ? msg : "Eroare AI" };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="absolute inset-y-0 right-0 z-30 w-full sm:w-96 max-w-full bg-stone-900/98 backdrop-blur-xl border-l border-white/10 flex flex-col shadow-2xl"
      data-testid="dt-qa-panel"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3 h-3" /> Întreabă AI · pe dovezi
          </div>
          <h3 className="font-serif text-base text-white truncate">{projectName || "Digital Twin"}</h3>
        </div>
        <button onClick={onClose} className="text-stone-500 hover:text-white shrink-0" data-testid="dt-qa-close">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Trust note */}
      <div className="px-4 py-2 bg-emerald-500/5 border-b border-emerald-500/10 flex items-start gap-2">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
        <p className="text-[10px] text-stone-400 leading-relaxed">
          Răspunsuri STRICT pe dovezi (DNA proprietate, documente, lucrări, modele). Fără presupuneri.
        </p>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4" data-testid="dt-qa-messages">
        {loadingHistory ? (
          <div className="text-center text-xs text-stone-500 py-6">
            <Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă istoricul…
          </div>
        ) : turns.length === 0 ? (
          <div className="text-center py-6">
            <MessageSquare className="w-8 h-8 text-stone-700 mx-auto mb-2" />
            <p className="text-xs text-stone-500">Pune o întrebare despre această proprietate.</p>
          </div>
        ) : (
          turns.map((t, i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-end">
                <div className="max-w-[85%] px-3 py-2 rounded-2xl rounded-br-sm bg-[#d4ff3a] text-black text-xs" data-testid={`dt-qa-q-${i}`}>
                  {t.question}
                </div>
              </div>
              <div className="flex justify-start">
                {t.answer === null && !t.error ? (
                  <div className="px-3 py-2 rounded-2xl rounded-bl-sm bg-white/5 text-stone-400 text-xs flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analizez dovezile…
                  </div>
                ) : t.error ? (
                  <div className="max-w-[85%] px-3 py-2 rounded-2xl rounded-bl-sm bg-red-500/10 border border-red-500/20 text-red-300 text-xs" data-testid={`dt-qa-a-${i}`}>
                    {t.error}
                  </div>
                ) : (
                  <div className="max-w-[85%] px-3 py-2 rounded-2xl rounded-bl-sm bg-white/5 text-stone-200 text-xs whitespace-pre-wrap leading-relaxed" data-testid={`dt-qa-a-${i}`}>
                    {t.answer}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {!loadingHistory && turns.length === 0 && (
          <div className="pt-2 space-y-2">
            {(suggestions.length ? suggestions : SUGGESTIONS.map((t) => ({ text: t, based_on: null }))).length > 0 && (
              <p className="text-[10px] uppercase tracking-[0.14em] text-stone-500 text-center">
                {suggestions.length ? "Sugestii din dovezile proprietății" : "Întrebări utile"}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 justify-center">
              {(suggestions.length ? suggestions : SUGGESTIONS.map((t) => ({ text: t, based_on: null }))).map((s, i) => (
                <button
                  key={i}
                  onClick={() => ask(s.text)}
                  title={s.based_on ? `pe baza: ${s.based_on}` : undefined}
                  className="px-2.5 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-[11px] text-stone-300 border border-white/5"
                  data-testid={`dt-qa-suggestion-${i}`}
                >
                  {s.text}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); ask(); }}
        className="px-3 py-3 border-t border-white/10 flex items-end gap-2"
      >
        <textarea
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } }}
          rows={1}
          placeholder="Întreabă despre proprietate…"
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white resize-none max-h-24"
          data-testid="dt-qa-input"
        />
        <button
          type="submit"
          disabled={busy || !q.trim()}
          className="w-9 h-9 shrink-0 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white flex items-center justify-center"
          data-testid="dt-qa-send"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
};

export default DigitalTwinQAPanel;
