import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Sparkles, Plus, Send, Trash2, Loader2, Copy, CheckCircle2, AlertCircle,
  ChevronRight, FileText, Brain, History, Camera, X, RefreshCcw,
  Bug, Wrench, Database, Layers, Shield, Zap, Eye, BookOpen
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const ROLES = [
  { id: "client", label: "Client" },
  { id: "specialist", label: "Specialist" },
  { id: "operator", label: "Operator" },
  { id: "admin", label: "Admin" },
];

const CATEGORY_META = {
  UI_UX: { icon: Eye, color: "cyan", label: "UI / UX" },
  DATA: { icon: Database, color: "amber", label: "Date" },
  LOGIC_BUG: { icon: Bug, color: "red", label: "Bug Logică" },
  MISSING_FEATURE: { icon: Wrench, color: "violet", label: "Feature Lipsă" },
  INTEGRATION: { icon: Layers, color: "blue", label: "Integrare" },
  PERFORMANCE: { icon: Zap, color: "orange", label: "Performanță" },
  SECURITY: { icon: Shield, color: "rose", label: "Securitate" },
};

const SEVERITY_COLORS = {
  P0: "bg-red-500/20 text-red-300 border-red-500/40",
  P1: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  P2: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  P3: "bg-stone-500/15 text-stone-300 border-stone-500/30",
};

const Pill = ({ children, className = "", ...props }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium border ${className}`} {...props}>
    {children}
  </span>
);

// =================== Session List Sidebar ===================
const SessionList = ({ sessions, activeId, onSelect, onNew, loading }) => (
  <div className="bg-[#0e0e10] border border-white/10 rounded-2xl overflow-hidden">
    <div className="p-4 border-b border-white/10 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-[#d4ff3a]" />
        <span className="text-sm font-medium">Istoric Sesiuni</span>
      </div>
      <button onClick={onNew} className="pm-btn pm-btn-primary pm-btn-sm" data-testid="qa-new-session-btn">
        <Plus className="w-3.5 h-3.5" /> Nouă
      </button>
    </div>
    <div className="max-h-[70vh] overflow-y-auto">
      {loading && <div className="p-6 text-center text-xs text-stone-400"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă...</div>}
      {!loading && sessions.length === 0 && (
        <div className="p-6 text-center text-xs text-stone-500">Niciun istoric — creează prima sesiune.</div>
      )}
      {sessions.map(s => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/[0.03] transition-colors ${activeId === s.id ? "bg-[#d4ff3a]/8 border-l-2 border-l-[#d4ff3a]" : ""}`}
          data-testid={`qa-session-item-${s.id}`}
        >
          <div className="text-sm font-medium truncate">{s.title}</div>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-stone-400">
            <Pill className="bg-white/5 border-white/10 text-stone-300">{s.role_being_tested}</Pill>
            <span>{s.finding_count || 0} constatări</span>
            {s.status === "closed" && <Pill className="bg-stone-500/20 border-stone-500/30 text-stone-300">închisă</Pill>}
          </div>
        </button>
      ))}
    </div>
  </div>
);

// =================== New Session Modal ===================
const NewSessionModal = ({ open, onClose, onCreate }) => {
  const [form, setForm] = useState({ title: "", goal: "", role_being_tested: "client", area: "" });
  const [busy, setBusy] = useState(false);
  if (!open) return null;
  const submit = async () => {
    if (!form.title.trim()) return;
    setBusy(true);
    try {
      await onCreate(form);
      setForm({ title: "", goal: "", role_being_tested: "client", area: "" });
      onClose();
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif text-2xl">Sesiune nouă</h3>
          <button onClick={onClose}><X className="w-4 h-4 text-stone-400" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-stone-400 uppercase tracking-wider">Titlu *</label>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="ex: Test rol specialist - Mihai Ionescu" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-[#d4ff3a]/50 focus:outline-none" data-testid="qa-new-title" />
          </div>
          <div>
            <label className="text-xs text-stone-400 uppercase tracking-wider">Rolul testat</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {ROLES.map(r => (
                <button key={r.id} onClick={() => setForm({ ...form, role_being_tested: r.id })} className={`px-3 py-1.5 rounded-full text-xs border ${form.role_being_tested === r.id ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`} data-testid={`qa-new-role-${r.id}`}>
                  {r.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-stone-400 uppercase tracking-wider">Zonă / Modul</label>
            <input value={form.area} onChange={e => setForm({ ...form, area: e.target.value })} placeholder="ex: Marketplace / Match Specialist" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm" data-testid="qa-new-area" />
          </div>
          <div>
            <label className="text-xs text-stone-400 uppercase tracking-wider">Obiectiv (opțional)</label>
            <textarea value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} placeholder="ex: Verific tot fluxul de la primire lead → ofertă → execuție lucrare." rows="3" className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm resize-none" data-testid="qa-new-goal" />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="pm-btn pm-btn-secondary flex-1">Anulează</button>
          <button onClick={submit} disabled={busy || !form.title.trim()} className="pm-btn pm-btn-primary flex-1" data-testid="qa-new-submit">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Creează
          </button>
        </div>
      </div>
    </div>
  );
};

// =================== Finding Card ===================
const FindingCard = ({ finding, idx, onDelete }) => {
  const a = finding.ai_analysis || {};
  const meta = CATEGORY_META[a.category] || CATEGORY_META.UI_UX;
  const Icon = meta.icon;
  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 relative" data-testid={`qa-finding-${idx}`}>
      <button onClick={() => onDelete(finding.id)} className="absolute top-3 right-3 text-stone-500 hover:text-red-400" title="Șterge constatarea">
        <Trash2 className="w-3.5 h-3.5" />
      </button>
      <div className="flex items-start gap-3 mb-3">
        <div className={`w-9 h-9 rounded-xl bg-${meta.color}-500/15 border border-${meta.color}-500/30 flex items-center justify-center shrink-0`}>
          <Icon className={`w-4 h-4 text-${meta.color}-400`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-[10px] text-stone-500 font-mono">#{String(idx + 1).padStart(2, "0")}</span>
            <Pill className={SEVERITY_COLORS[a.severity] || SEVERITY_COLORS.P2}>{a.severity || "P2"}</Pill>
            <Pill className={`bg-${meta.color}-500/15 text-${meta.color}-300 border-${meta.color}-500/30`}>{meta.label}</Pill>
            {a.error && <Pill className="bg-yellow-500/15 text-yellow-300 border-yellow-500/30">AI offline</Pill>}
          </div>
          <p className="text-sm text-stone-100 leading-relaxed">{finding.text}</p>
          {a.summary && a.summary !== finding.text && (
            <p className="text-xs text-stone-400 italic mt-2">Sumar AI: {a.summary}</p>
          )}
        </div>
      </div>
      {finding.screenshot_url && (
        <img src={finding.screenshot_url} alt="Screenshot" className="mt-2 rounded-xl border border-white/10 max-h-60 object-contain" />
      )}
      {(a.suspected_files?.length > 0 || a.suggested_next_tests?.length > 0) && (
        <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
          {a.suspected_files?.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[#d4ff3a] mb-1.5 flex items-center gap-1"><FileText className="w-3 h-3" /> Fișiere suspecte {a.code_aware && <span className="text-stone-500 normal-case">· verificate vs cod real</span>}</div>
              <div className="flex flex-wrap gap-1.5">
                {a.suspected_files.map((f, i) => (
                  <code key={i} className="text-[11px] bg-white/5 border border-white/10 rounded px-2 py-0.5 text-stone-300 font-mono">{f}</code>
                ))}
              </div>
            </div>
          )}
          {a.invalid_paths_filtered?.length > 0 && (
            <div className="text-[11px] text-amber-400/80">
              ⚠ AI a propus {a.invalid_paths_filtered.length} path-uri inexistente, filtrate automat: <span className="font-mono text-stone-500">{a.invalid_paths_filtered.join(", ")}</span>
            </div>
          )}
          {a.suggested_next_tests?.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-cyan-400 mb-1.5 flex items-center gap-1"><Brain className="w-3 h-3" /> Următoarele teste sugerate</div>
              <ul className="space-y-1">
                {a.suggested_next_tests.map((t, i) => (
                  <li key={i} className="text-xs text-stone-300 flex items-start gap-2"><ChevronRight className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />{t}</li>
                ))}
              </ul>
            </div>
          )}
          {a.related_finding_ids?.length > 0 && (
            <div className="text-[11px] text-stone-400">
              <span className="text-violet-400 font-medium">{a.related_finding_ids.length}</span> constatări similare anterioare (verifică sesiunile vechi)
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// =================== Main Page ===================
export const QACopilotPage = () => {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [active, setActive] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingActive, setLoadingActive] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [findingText, setFindingText] = useState("");
  const [screenshot, setScreenshot] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const loadList = async () => {
    setLoadingList(true);
    try {
      const { data } = await ax.get("/api/admin/qa-copilot/sessions");
      setSessions(data.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare istoric");
    } finally { setLoadingList(false); }
  };

  const loadActive = async (sid) => {
    if (!sid) { setActive(null); return; }
    setLoadingActive(true);
    try {
      const { data } = await ax.get(`/api/admin/qa-copilot/sessions/${sid}`);
      setActive(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare sesiune");
    } finally { setLoadingActive(false); }
  };

  useEffect(() => { loadList(); }, []);
  useEffect(() => { loadActive(activeId); }, [activeId]);

  const createSession = async (form) => {
    const { data } = await ax.post("/api/admin/qa-copilot/sessions", form);
    await loadList();
    setActiveId(data.id);
  };

  const addFinding = async () => {
    if (!findingText.trim() || !activeId) return;
    setAnalyzing(true);
    setError(null);
    try {
      await ax.post(`/api/admin/qa-copilot/sessions/${activeId}/findings`, {
        text: findingText.trim(),
        screenshot_url: screenshot || null,
      });
      setFindingText("");
      setScreenshot("");
      await loadActive(activeId);
      await loadList();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la analiza AI");
    } finally { setAnalyzing(false); }
  };

  const deleteFinding = async (fid) => {
    if (!window.confirm("Ștergi această constatare?")) return;
    await ax.delete(`/api/admin/qa-copilot/sessions/${activeId}/findings/${fid}`);
    await loadActive(activeId);
    await loadList();
  };

  const generatePrompt = async () => {
    setGenerating(true);
    setError(null);
    try {
      await ax.post(`/api/admin/qa-copilot/sessions/${activeId}/generate-prompt`);
      await loadActive(activeId);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la generare prompt");
    } finally { setGenerating(false); }
  };

  const closeSession = async () => {
    if (!window.confirm("Marchezi sesiunea ca închisă? Vei putea o consulta în istoric.")) return;
    await ax.patch(`/api/admin/qa-copilot/sessions/${activeId}`, { status: "closed" });
    await loadActive(activeId);
    await loadList();
  };

  const deleteSession = async () => {
    if (!window.confirm("Ștergi sesiunea complet? Această acțiune e ireversibilă.")) return;
    await ax.delete(`/api/admin/qa-copilot/sessions/${activeId}`);
    setActiveId(null);
    await loadList();
  };

  const copyPrompt = async () => {
    if (!active?.generated_prompt) return;
    try {
      await navigator.clipboard.writeText(active.generated_prompt);
    } catch (_) {
      // Fallback for insecure contexts / denied permissions
      const ta = document.createElement("textarea");
      ta.value = active.generated_prompt;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (__) { /* swallow */ }
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 1024 * 1024) { setError("Imagine prea mare (max 1MB)"); return; }
    const reader = new FileReader();
    reader.onload = () => setScreenshot(reader.result);
    reader.readAsDataURL(f);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">← Înapoi la Admin Dashboard</Link>
        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="qa-copilot-title">
              QA <span className="italic gradient-text">Copilot</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">Testare manuală asistată de AI · Claude Sonnet 4.5. Descrie ce vezi, AI clasifică, sugerează teste noi și generează un prompt gata de trimis în Emergent.</p>
          </div>
          <Link to="/admin/documentation" className="pm-btn pm-btn-secondary pm-btn-sm">
            <BookOpen className="w-3.5 h-3.5" /> Documentație
          </Link>
        </div>

        {error && (
          <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-2xl p-3 flex items-start gap-2 text-sm text-red-300" data-testid="qa-error">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />{error}
            <button onClick={() => setError(null)} className="ml-auto"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        <div className="grid lg:grid-cols-[320px_1fr] gap-6 mt-6">
          <SessionList sessions={sessions} activeId={activeId} onSelect={setActiveId} onNew={() => setShowNew(true)} loading={loadingList} />

          <div className="space-y-5 min-w-0">
            {!activeId && (
              <div className="bg-[#0e0e10] border border-dashed border-white/15 rounded-3xl p-12 text-center" data-testid="qa-empty-state">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center">
                  <Sparkles className="w-7 h-7 text-[#d4ff3a]" />
                </div>
                <h3 className="font-serif text-2xl mb-2">Începe o sesiune de testare</h3>
                <p className="text-sm text-stone-400 max-w-md mx-auto mb-6">Creează o sesiune nouă, alege rolul testat, descrie ce vezi în limbaj natural. AI face restul.</p>
                <button onClick={() => setShowNew(true)} className="pm-btn pm-btn-primary pm-btn-lg" data-testid="qa-cta-new-session">
                  <Plus className="w-4 h-4" /> Sesiune nouă
                </button>
              </div>
            )}

            {activeId && loadingActive && (
              <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-12 text-center text-stone-400">
                <Loader2 className="w-6 h-6 animate-spin mx-auto" />
              </div>
            )}

            {activeId && active && (
              <>
                {/* Session Header */}
                <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div>
                      <h2 className="font-serif text-2xl mb-2" data-testid="qa-active-title">{active.title}</h2>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <Pill className="bg-[#d4ff3a]/15 text-[#d4ff3a] border-[#d4ff3a]/30">Rol: {active.role_being_tested}</Pill>
                        {active.area && <Pill className="bg-white/5 border-white/10 text-stone-300">{active.area}</Pill>}
                        <Pill className={active.status === "closed" ? "bg-stone-500/20 border-stone-500/30 text-stone-300" : "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"}>{active.status === "closed" ? "ÎNCHISĂ" : "ACTIVĂ"}</Pill>
                      </div>
                      {active.goal && <p className="text-sm text-stone-400 mt-3">{active.goal}</p>}
                    </div>
                    <div className="flex gap-2">
                      {active.status === "active" && (
                        <button onClick={closeSession} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="qa-close-session">Închide</button>
                      )}
                      <button onClick={deleteSession} className="pm-btn pm-btn-danger pm-btn-sm" data-testid="qa-delete-session"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                </div>

                {/* Findings */}
                <div className="space-y-3">
                  {(active.findings || []).map((f, i) => (
                    <FindingCard key={f.id} finding={f} idx={i} onDelete={deleteFinding} />
                  ))}
                  {(active.findings || []).length === 0 && (
                    <div className="text-xs text-stone-500 italic px-2">Nicio constatare încă. Scrie mai jos ce ai observat în timpul testării.</div>
                  )}
                </div>

                {/* Add finding */}
                {active.status === "active" && (
                  <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Brain className="w-4 h-4 text-[#d4ff3a]" />
                      <h3 className="font-serif text-lg">Adaugă constatare</h3>
                    </div>
                    <textarea
                      value={findingText}
                      onChange={e => setFindingText(e.target.value)}
                      placeholder="Descrie ce ai văzut în timpul testării — ex: 'La pasul X am apăsat butonul Y și nu se întâmplă nimic. Mă așteptam să se deschidă modalul Z.' AI va clasifica și sugera următoarele teste."
                      rows="4"
                      className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-sm focus:border-[#d4ff3a]/50 focus:outline-none resize-none"
                      data-testid="qa-finding-input"
                    />
                    {screenshot && (
                      <div className="mt-2 relative inline-block">
                        <img src={screenshot} alt="preview" className="max-h-28 rounded-lg border border-white/10" />
                        <button onClick={() => setScreenshot("")} className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1"><X className="w-3 h-3" /></button>
                      </div>
                    )}
                    <div className="flex items-center justify-between gap-2 mt-3">
                      <div className="flex gap-2">
                        <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" />
                        <button onClick={() => fileRef.current?.click()} className="pm-btn pm-btn-ghost pm-btn-sm" data-testid="qa-attach-screenshot">
                          <Camera className="w-3.5 h-3.5" /> Atașează screenshot
                        </button>
                      </div>
                      <button onClick={addFinding} disabled={analyzing || !findingText.trim()} className="pm-btn pm-btn-primary" data-testid="qa-add-finding-btn">
                        {analyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> AI analizează...</> : <><Send className="w-3.5 h-3.5" /> Trimite & analizează</>}
                      </button>
                    </div>
                  </div>
                )}

                {/* Generate prompt */}
                {(active.findings || []).length > 0 && (
                  <div className="bg-gradient-to-br from-[#d4ff3a]/10 to-emerald-500/5 border border-[#d4ff3a]/30 rounded-3xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                      <div>
                        <h3 className="font-serif text-xl flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#d4ff3a]" /> Prompt pentru Emergent</h3>
                        <p className="text-xs text-stone-400 mt-1">Compilează toate cele {(active.findings || []).length} constatări într-un prompt structurat gata de copiat în chat-ul cu agentul.</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={generatePrompt} disabled={generating} className="pm-btn pm-btn-primary" data-testid="qa-generate-prompt">
                          {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> Generez...</> : <><RefreshCcw className="w-3.5 h-3.5" /> {active.generated_prompt ? "Regenerează" : "Generează prompt"}</>}
                        </button>
                        {active.generated_prompt && (
                          <button onClick={copyPrompt} className="pm-btn pm-btn-secondary" data-testid="qa-copy-prompt">
                            {copied ? <><CheckCircle2 className="w-3.5 h-3.5" /> Copiat ✓</> : <><Copy className="w-3.5 h-3.5" /> Copiază</>}
                          </button>
                        )}
                      </div>
                    </div>
                    {active.generated_prompt && (
                      <pre className="bg-[#0a0a0b] border border-white/10 rounded-2xl p-4 text-xs text-stone-200 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[60vh] overflow-y-auto" data-testid="qa-prompt-output">
{active.generated_prompt}
                      </pre>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <NewSessionModal open={showNew} onClose={() => setShowNew(false)} onCreate={createSession} />
      </div>
    </div>
  );
};

export default QACopilotPage;
