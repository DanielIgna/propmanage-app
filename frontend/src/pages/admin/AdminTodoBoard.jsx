// AdminTodoBoard — Centralized view of all "TODO" items from the documentation.
// Aggregates `status.todo` from every TOPICS entry in AdminDocumentation,
// plus persisted custom todos from /api/admin/todos.
import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ListChecks, Loader2, Plus, Trash2, CheckCircle2, Square,
  Filter, BookOpen, X, Sparkles, AlertCircle, Wand2, Copy, Send,
} from "lucide-react";
import { TOPICS } from "./AdminDocumentation";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const PRIORITY_OPTIONS = [
  { value: "high",   label: "Ridicat", color: "border-red-500/40 bg-red-500/10 text-red-300" },
  { value: "medium", label: "Mediu",   color: "border-amber-500/40 bg-amber-500/10 text-amber-300" },
  { value: "low",    label: "Scăzut",  color: "border-stone-500/40 bg-stone-500/10 text-stone-300" },
];

const TodoRow = ({ todo, onToggle, onDelete, onChangePriority, onGeneratePrompt }) => {
  const prio = PRIORITY_OPTIONS.find(p => p.value === todo.priority) || PRIORITY_OPTIONS[1];
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-xl border ${todo.done ? "border-emerald-500/20 bg-emerald-500/5 opacity-60" : "border-white/10 bg-white/[0.02]"} transition-all`}
      data-testid={`todo-row-${todo.id}`}
    >
      <button
        onClick={() => onToggle(todo)}
        className="mt-0.5 shrink-0"
        data-testid={`todo-toggle-${todo.id}`}
        aria-label="toggle done"
      >
        {todo.done
          ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          : <Square className="w-5 h-5 text-stone-500 hover:text-[#d4ff3a]" />}
      </button>
      <div className="flex-1 min-w-0">
        <div className={`text-sm ${todo.done ? "line-through text-stone-400" : "text-stone-100"}`}>
          {todo.text}
        </div>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {todo.topic_title && (
            <span className="text-[10px] uppercase tracking-wider text-stone-400 inline-flex items-center gap-1">
              <BookOpen className="w-3 h-3" /> {todo.topic_title}
            </span>
          )}
          {todo.kind === "manual" && (
            <span className="text-[10px] uppercase tracking-wider text-cyan-300 px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30">
              CUSTOM
            </span>
          )}
          {onChangePriority ? (
            <select
              value={todo.priority || "medium"}
              onChange={e => onChangePriority(todo, e.target.value)}
              className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${prio.color} bg-transparent focus:outline-none`}
              data-testid={`todo-priority-${todo.id}`}
            >
              {PRIORITY_OPTIONS.map(p => <option key={p.value} value={p.value} className="bg-black">{p.label}</option>)}
            </select>
          ) : (
            <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${prio.color}`}>
              {prio.label}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {!todo.done && (
          <button
            onClick={() => onGeneratePrompt(todo)}
            className="text-stone-400 hover:text-[#d4ff3a] transition-colors p-1.5 rounded-lg hover:bg-white/5"
            data-testid={`todo-prompt-${todo.id}`}
            title="Generează prompt Emergent"
            aria-label="generează prompt"
          >
            <Wand2 className="w-4 h-4" />
          </button>
        )}
        {onDelete && todo.kind === "manual" && (
          <button
            onClick={() => onDelete(todo)}
            className="text-stone-500 hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-white/5"
            data-testid={`todo-delete-${todo.id}`}
            aria-label="șterge"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

const PromptModal = ({ todo, prompt, loading, error, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [sentToChat, setSentToChat] = useState(false);
  if (!todo) return null;

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
    } catch (_) { /* clipboard API missing or blocked — silently ignore */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const sendToEmergentChat = async () => {
    // 1) Copy to clipboard (always — fallback for any case)
    try {
      await navigator.clipboard.writeText(prompt);
    } catch (_) { /* swallow */ }
    // 2) Best-effort: postMessage to parent (works when the app is embedded
    //    in the Emergent IDE iframe — the parent listens to 'emergent.chat.inject').
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage(
          {
            type: "emergent.chat.inject",
            source: "propmanage-todo-board",
            payload: { text: prompt, topic: todo.topic_title || "", priority: todo.priority || "medium" },
          },
          "*"
        );
      }
    } catch (_) { /* swallow */ }
    setSentToChat(true);
    setTimeout(() => setSentToChat(false), 4000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose} data-testid="todo-prompt-modal">
      <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-start gap-3 mb-4">
          <div className="w-11 h-11 rounded-2xl bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 flex items-center justify-center shrink-0">
            <Wand2 className="w-5 h-5 text-[#d4ff3a]" />
          </div>
          <div className="flex-1">
            <h3 className="font-serif text-xl">Prompt Emergent generat</h3>
            <p className="text-xs text-stone-400 mt-1 truncate">
              Pentru: <span className="text-stone-200">{todo.text}</span>
            </p>
            {todo.topic_title && (
              <p className="text-[10px] uppercase tracking-wider text-stone-500 mt-0.5">
                {todo.topic_title}
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-white" data-testid="todo-prompt-modal-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-10 text-stone-400 gap-2">
            <Loader2 className="w-5 h-5 animate-spin" /> Claude scrie prompt-ul...
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {prompt && !loading && (
          <>
            <div className="bg-black/40 border border-white/10 rounded-xl p-4 font-mono text-xs text-stone-200 whitespace-pre-wrap leading-relaxed" data-testid="todo-prompt-output">
              {prompt}
            </div>
            {sentToChat && (
              <div className="mt-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-3 py-2.5 text-xs text-emerald-300 flex items-start gap-2" data-testid="todo-prompt-sent-banner">
                <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                <div>
                  <strong>Trimis spre chat Emergent.</strong> Prompt-ul este copiat în clipboard. Dă click în chat-ul Emergent și apasă <kbd className="px-1.5 py-0.5 bg-black/50 rounded border border-white/10 font-mono">Ctrl+V</kbd> ca să-l lipești. (Dacă rulezi în modul standalone, IDE-ul îl va prelua automat când îl detectează.)
                </div>
              </div>
            )}
            <div className="flex items-center justify-between gap-2 mt-4 flex-wrap">
              <div className="text-[11px] text-stone-500">
                💡 Folosește 'Trimite în chat' pentru workflow rapid sau 'Copiază' clasic.
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyPrompt}
                  className={`pm-btn pm-btn-sm ${copied ? "pm-btn-secondary" : "pm-btn-secondary"}`}
                  data-testid="todo-prompt-copy"
                >
                  {copied
                    ? <><CheckCircle2 className="w-3.5 h-3.5" /> Copiat!</>
                    : <><Copy className="w-3.5 h-3.5" /> Copiază</>}
                </button>
                <button
                  onClick={sendToEmergentChat}
                  className="pm-btn pm-btn-primary pm-btn-sm"
                  data-testid="todo-prompt-send-chat"
                >
                  <Send className="w-3.5 h-3.5" />
                  {sentToChat ? "Trimis!" : "Trimite în chat"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export const AdminTodoBoard = () => {
  // Manual todos from backend
  const [customTodos, setCustomTodos] = useState([]);
  // Local state for documented (read-only) todos completion
  const [docDoneIds, setDocDoneIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newText, setNewText] = useState("");
  const [newPrio, setNewPrio] = useState("medium");
  const [filterDone, setFilterDone] = useState("open"); // open | done | all
  const [filterTopic, setFilterTopic] = useState(null);
  const [error, setError] = useState(null);
  // Prompt generation modal
  const [promptTodo, setPromptTodo] = useState(null);
  const [promptText, setPromptText] = useState("");
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptError, setPromptError] = useState(null);
  const focusId = useMemo(() => new URLSearchParams(window.location.search).get("focus"), []);
  const [focusMissing, setFocusMissing] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await ax.get("/api/admin/todos");
      setCustomTodos(data.items || []);
      setDocDoneIds(data.doc_done_ids || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // Deep-link: /admin/todo?focus=<id> → arată + evidențiază task-ul exact (fără fallback la homepage)
  useEffect(() => {
    if (!focusId || loading) return;
    const exists = customTodos.some(t => t.id === focusId);
    setFocusMissing(!exists);
    if (exists) {
      setFilterDone("all");
      const timer = setTimeout(() => {
        const el = document.getElementById(`todo-${focusId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [focusId, loading, customTodos]);

  // Build documented todos from TOPICS (read-only items extracted from manual)
  const documentedTodos = useMemo(() => {
    const out = [];
    for (const t of TOPICS) {
      const todos = t.status?.todo || [];
      todos.forEach((text, i) => {
        const id = `doc:${t.id}:${i}`;
        out.push({
          id,
          text,
          topic_id: t.id,
          topic_title: t.title,
          kind: "documented",
          priority: "medium",
          done: docDoneIds.includes(id),
        });
      });
    }
    return out;
  }, [docDoneIds]);

  const allTodos = useMemo(() => {
    return [
      ...customTodos.map(t => ({ ...t, kind: "manual" })),
      ...documentedTodos,
    ];
  }, [customTodos, documentedTodos]);

  const filteredTodos = useMemo(() => {
    return allTodos.filter(t => {
      if (filterDone === "open" && t.done) return false;
      if (filterDone === "done" && !t.done) return false;
      if (filterTopic && t.topic_id !== filterTopic) return false;
      return true;
    });
  }, [allTodos, filterDone, filterTopic]);

  const stats = useMemo(() => {
    return {
      total: allTodos.length,
      open: allTodos.filter(t => !t.done).length,
      done: allTodos.filter(t => t.done).length,
      custom: customTodos.length,
      documented: documentedTodos.length,
    };
  }, [allTodos, customTodos, documentedTodos]);

  // Group by topic for quick filter
  const topicCounts = useMemo(() => {
    const map = {};
    for (const t of allTodos) {
      if (!t.topic_id) continue;
      map[t.topic_id] = map[t.topic_id] || { title: t.topic_title, open: 0, done: 0 };
      if (t.done) map[t.topic_id].done++;
      else map[t.topic_id].open++;
    }
    return map;
  }, [allTodos]);

  const addTodo = async () => {
    const text = newText.trim();
    if (text.length < 2) return;
    try {
      const { data } = await ax.post("/api/admin/todos", { text, priority: newPrio });
      setCustomTodos(prev => [data, ...prev]);
      setNewText("");
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la salvare");
    }
  };

  const toggleTodo = async (todo) => {
    try {
      if (todo.kind === "manual") {
        const { data } = await ax.put(`/api/admin/todos/${todo.id}`, { done: !todo.done });
        setCustomTodos(prev => prev.map(t => (t.id === todo.id ? data : t)));
      } else {
        // documented — toggle in backend (doc_done_ids list)
        const action = todo.done ? "unmark" : "mark";
        await ax.post("/api/admin/todos/doc-done", { id: todo.id, action });
        setDocDoneIds(prev => (
          todo.done ? prev.filter(x => x !== todo.id) : [...prev, todo.id]
        ));
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la actualizare");
    }
  };

  const changePriority = async (todo, priority) => {
    if (todo.kind !== "manual") return;
    try {
      const { data } = await ax.put(`/api/admin/todos/${todo.id}`, { priority });
      setCustomTodos(prev => prev.map(t => (t.id === todo.id ? data : t)));
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la actualizare");
    }
  };

  const deleteTodo = async (todo) => {
    if (todo.kind !== "manual") return;
    if (!window.confirm("Ștergi acest task?")) return;
    try {
      await ax.delete(`/api/admin/todos/${todo.id}`);
      setCustomTodos(prev => prev.filter(t => t.id !== todo.id));
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la ștergere");
    }
  };

  const generatePromptForTodo = async (todo) => {
    setPromptTodo(todo);
    setPromptText("");
    setPromptError(null);
    setPromptLoading(true);
    try {
      const { data } = await ax.post("/api/admin/todos/generate-prompt", {
        text: todo.text,
        topic_title: todo.topic_title || "",
        priority: todo.priority || "medium",
      });
      setPromptText(data.prompt || "");
    } catch (e) {
      setPromptError(e?.response?.data?.detail || "Nu am putut genera prompt. Încearcă din nou.");
    } finally { setPromptLoading(false); }
  };

  const closePromptModal = () => {
    setPromptTodo(null);
    setPromptText("");
    setPromptError(null);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-5xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="todo-back">← Înapoi la Admin Dashboard</Link>
        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="todo-title">
              ToDo <span className="italic gradient-text">Board</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">
              Lista centralizată cu tot ce mai are de implementat platforma. Cuprinde TODO-urile din documentația tehnică (read-only) + task-urile tale custom (editabile).
            </p>
          </div>
          <Link to="/admin/documentation" className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="todo-open-docs">
            <BookOpen className="w-3.5 h-3.5" /> Vezi în Documentație
          </Link>
        </div>

        {/* STATS */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5" data-testid="todo-stats">
          {[
            { label: "Total", v: stats.total, c: "text-stone-100" },
            { label: "Deschise", v: stats.open, c: "text-amber-400" },
            { label: "Finalizate", v: stats.done, c: "text-emerald-400" },
            { label: "Din manual", v: stats.documented, c: "text-stone-300" },
            { label: "Custom", v: stats.custom, c: "text-cyan-400" },
          ].map(s => (
            <div key={s.label} className="bg-[#0e0e10] border border-white/10 rounded-xl p-3">
              <div className="text-[10px] uppercase tracking-wider text-stone-400">{s.label}</div>
              <div className={`font-serif text-2xl ${s.c}`}>{s.v}</div>
            </div>
          ))}
        </div>

        {/* ADD NEW */}
        <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mt-6">
          <div className="flex items-center gap-2 mb-3">
            <Plus className="w-4 h-4 text-[#d4ff3a]" />
            <h2 className="text-sm font-semibold">Adaugă task nou</h2>
          </div>
          <div className="flex gap-2 flex-wrap">
            <input
              value={newText}
              onChange={e => setNewText(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addTodo()}
              placeholder="ex: Refă imaginile galeria principala"
              className="flex-1 min-w-[200px] bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
              data-testid="todo-new-text"
            />
            <select
              value={newPrio}
              onChange={e => setNewPrio(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none"
              data-testid="todo-new-priority"
            >
              {PRIORITY_OPTIONS.map(p => <option key={p.value} value={p.value} className="bg-black">{p.label}</option>)}
            </select>
            <button onClick={addTodo} disabled={newText.trim().length < 2} className="pm-btn pm-btn-primary pm-btn-sm" data-testid="todo-add">
              <Plus className="w-3.5 h-3.5" /> Adaugă
            </button>
          </div>
        </div>

        {/* FILTERS */}
        <div className="flex items-center gap-2 flex-wrap mt-6 mb-3" data-testid="todo-filters">
          <Filter className="w-3.5 h-3.5 text-stone-400" />
          {[
            { v: "open",  l: "Deschise"   },
            { v: "done",  l: "Finalizate" },
            { v: "all",   l: "Toate"      },
          ].map(f => (
            <button
              key={f.v}
              onClick={() => setFilterDone(f.v)}
              className={`text-[11px] px-2.5 py-1 rounded-full border transition-colors ${
                filterDone === f.v
                  ? "bg-[#d4ff3a] text-black border-[#d4ff3a]"
                  : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"
              }`}
              data-testid={`todo-filter-${f.v}`}
            >
              {f.l}
            </button>
          ))}
          {filterTopic && (
            <button
              onClick={() => setFilterTopic(null)}
              className="text-[11px] px-2.5 py-1 rounded-full border bg-white/5 border-white/10 hover:bg-white/10 inline-flex items-center gap-1"
              data-testid="todo-filter-clear-topic"
            >
              {topicCounts[filterTopic]?.title || "topic"} <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* LIST */}
        {loading && (
          <div className="text-center py-10 text-stone-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
          </div>
        )}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300 mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}
        {!loading && filteredTodos.length === 0 && (
          <div className="text-center py-10 text-stone-400 text-sm italic" data-testid="todo-empty">
            {filterDone === "open"
              ? "Niciun task deschis. Felicitări! 🎉"
              : "Niciun rezultat pentru filtrele curente."}
          </div>
        )}

        {focusMissing && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-sm text-amber-300 mb-4 flex items-center gap-2" data-testid="todo-focus-missing">
            <AlertCircle className="w-4 h-4" /> Task indisponibil (a fost șters sau nu mai există).
          </div>
        )}

        <div className="space-y-2 mt-2" data-testid="todo-list">
          {filteredTodos.map(t => (
            <div key={t.id} id={`todo-${t.id}`} className={focusId === t.id ? "ring-2 ring-[#d4ff3a] rounded-2xl transition-all" : ""}>
              <TodoRow
                todo={t}
                onToggle={toggleTodo}
                onDelete={t.kind === "manual" ? deleteTodo : null}
                onChangePriority={t.kind === "manual" ? changePriority : null}
                onGeneratePrompt={generatePromptForTodo}
              />
            </div>
          ))}
        </div>

        {/* PER-TOPIC NAV */}
        {Object.keys(topicCounts).length > 0 && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mt-8" data-testid="todo-per-topic">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
              <h2 className="text-sm font-semibold">Per modul (click pentru filtru)</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(topicCounts).map(([id, c]) => (
                <button
                  key={id}
                  onClick={() => setFilterTopic(id === filterTopic ? null : id)}
                  className={`text-xs px-3 py-1.5 rounded-xl border transition-colors ${
                    filterTopic === id
                      ? "bg-[#d4ff3a] text-black border-[#d4ff3a]"
                      : "bg-white/5 text-stone-200 border-white/10 hover:bg-white/10"
                  }`}
                >
                  {c.title} · <span className="text-amber-400">{c.open}</span>/<span className="text-emerald-400">{c.done}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <PromptModal
        todo={promptTodo}
        prompt={promptText}
        loading={promptLoading}
        error={promptError}
        onClose={closePromptModal}
      />
    </div>
  );
};

export default AdminTodoBoard;
