import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  FileText, Upload, MessageSquare, Loader2, Trash2, Send,
  X, BookOpen, Sparkles, AlertCircle, CheckCircle2, ChevronRight, Brain
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

export default function DocsAIPage() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState("");
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const { data } = await ax.get("/api/ai-docs/list");
      setDocs(data.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally { setLoading(false); }
  };

  useEffect(() => { loadDocs(); }, []);

  const onUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("title", f.name);
      await ax.post("/api/ai-docs/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      await loadDocs();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la upload");
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const del = async (id) => {
    if (!window.confirm("Ștergi acest document și toate fragmentele indexate?")) return;
    await ax.delete(`/api/ai-docs/${id}`);
    await loadDocs();
    if (selectedDoc === id) setSelectedDoc("");
  };

  const ask = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setError(null);
    try {
      const { data } = await ax.post("/api/ai-docs/ask", {
        question: question.trim(),
        doc_id: selectedDoc || null,
        top_k: 4,
      });
      setAnswer(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la întrebare");
    } finally { setAsking(false); }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-5xl mx-auto px-6 pt-28 pb-16">
        <Link to="/client" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">← Înapoi la Dashboard</Link>
        <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="docs-ai-title">
          Document <span className="italic gradient-text">Intelligence</span>
        </h1>
        <p className="text-sm text-stone-400 mt-2 max-w-2xl">Încarcă contracte, regulamente, facturi, procese-verbale. AI-ul indexează și răspunde la întrebări citând sursele exacte.</p>

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-2xl p-3 flex items-start gap-2 text-sm text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />{error}
            <button onClick={() => setError(null)} className="ml-auto"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        {/* Upload */}
        <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 mt-6">
          <div className="flex items-center gap-2 mb-3">
            <Upload className="w-4 h-4 text-[#d4ff3a]" />
            <h2 className="font-serif text-xl">Documentele tale</h2>
            <span className="ml-auto text-xs text-stone-500">{docs.length} documente</span>
          </div>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" onChange={onUpload} className="hidden" />
          <button onClick={() => fileRef.current?.click()} disabled={uploading} className="pm-btn pm-btn-primary" data-testid="docs-upload-btn">
            {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Se procesează...</> : <><Upload className="w-4 h-4" /> Încarcă PDF / DOCX / TXT (max 10MB)</>}
          </button>

          {loading && <div className="mt-4 text-xs text-stone-400"><Loader2 className="w-4 h-4 animate-spin inline mr-1" /> Se încarcă...</div>}
          {!loading && docs.length === 0 && <div className="mt-4 text-xs text-stone-500 italic">Niciun document încărcat încă.</div>}
          <div className="mt-4 space-y-2">
            {docs.map(d => (
              <div key={d.id} className={`p-3 rounded-xl border flex items-center gap-3 cursor-pointer ${selectedDoc === d.id ? "bg-[#d4ff3a]/10 border-[#d4ff3a]/40" : "bg-white/[0.02] border-white/5 hover:bg-white/[0.05]"}`} onClick={() => setSelectedDoc(d.id === selectedDoc ? "" : d.id)} data-testid={`docs-item-${d.id}`}>
                <FileText className="w-4 h-4 text-[#d4ff3a] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">{d.title}</div>
                  <div className="text-[10px] text-stone-500">{d.kind?.toUpperCase()} · {d.chunk_count} fragmente · {Math.round((d.size_bytes || 0) / 1024)} KB</div>
                </div>
                {selectedDoc === d.id && <CheckCircle2 className="w-4 h-4 text-[#d4ff3a]" />}
                <button onClick={(e) => { e.stopPropagation(); del(d.id); }} className="text-stone-500 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            ))}
          </div>
        </div>

        {/* Ask */}
        <div className="bg-gradient-to-br from-[#d4ff3a]/10 to-emerald-500/5 border border-[#d4ff3a]/30 rounded-3xl p-6 mt-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-[#d4ff3a]" />
            <h2 className="font-serif text-xl">Întreabă AI-ul</h2>
            {selectedDoc && <span className="text-xs text-[#d4ff3a]">· cu sursa filtrată la documentul selectat</span>}
          </div>
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ex: Care este durata garanției din contract? Care sunt cotele de participare ale asociației? Ce sumă este facturată pentru lift în luna iunie?"
            rows="3"
            className="w-full bg-[#0a0a0b] border border-white/10 rounded-xl p-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50 resize-none"
            data-testid="docs-question-input"
          />
          <div className="flex justify-end mt-3">
            <button onClick={ask} disabled={asking || !question.trim() || docs.length === 0} className="pm-btn pm-btn-primary" data-testid="docs-ask-btn">
              {asking ? <><Loader2 className="w-4 h-4 animate-spin" /> AI gândește...</> : <><Send className="w-4 h-4" /> Trimite întrebarea</>}
            </button>
          </div>

          {answer && (
            <div className="mt-5 bg-[#0a0a0b] border border-white/10 rounded-2xl p-4" data-testid="docs-answer">
              <div className="text-xs text-stone-500 uppercase tracking-wider mb-2">Răspuns AI</div>
              <div className="text-sm text-stone-100 whitespace-pre-wrap leading-relaxed">{answer.answer}</div>
              {answer.sources?.length > 0 && (
                <div className="mt-4 pt-3 border-t border-white/5">
                  <div className="text-[10px] uppercase tracking-wider text-[#d4ff3a] mb-2 flex items-center gap-1"><BookOpen className="w-3 h-3" /> Surse ({answer.sources.length})</div>
                  <div className="space-y-1">
                    {answer.sources.map((s, i) => (
                      <div key={i} className="text-[11px] text-stone-400 flex items-center gap-2">
                        <ChevronRight className="w-3 h-3 text-[#d4ff3a]" />
                        <span className="text-stone-200">{s.doc_title}</span>
                        <span>· fragment #{s.chunk_idx}</span>
                        <span className="ml-auto text-stone-500">scor: {s.score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
