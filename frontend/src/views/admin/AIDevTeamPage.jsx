import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Code2, Search, Loader2, FileCode, Brain, AlertTriangle, ShieldCheck,
  Bug, Lightbulb, ListChecks, Copy, CheckCircle2, RefreshCcw, X
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const SEV_COLOR = {
  P0: "bg-red-500/20 text-red-300 border-red-500/40",
  P1: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  P2: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  P3: "bg-stone-500/15 text-stone-300 border-stone-500/30",
};

const Pill = ({ children, className = "" }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium border ${className}`}>{children}</span>
);

export default function AIDevTeamPage() {
  const [files, setFiles] = useState([]);
  const [filteredFiles, setFilteredFiles] = useState([]);
  const [agents, setAgents] = useState({});
  const [search, setSearch] = useState("");
  const [filterKind, setFilterKind] = useState("");
  const [selectedFile, setSelectedFile] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("auto");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState("");

  const load = async () => {
    try {
      const [filesRes, agentsRes] = await Promise.all([
        ax.get("/api/admin/ai-dev-team/files", { params: filterKind ? { kind: filterKind } : {} }),
        ax.get("/api/admin/ai-dev-team/agents"),
      ]);
      setFiles(filesRes.data.files || []);
      setAgents(agentsRes.data.agents || {});
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    }
  };
  useEffect(() => { load(); }, [filterKind]);

  useEffect(() => {
    const q = search.trim().toLowerCase();
    setFilteredFiles(q ? files.filter(f => f.toLowerCase().includes(q)).slice(0, 60) : files.slice(0, 60));
  }, [files, search]);

  const analyze = async () => {
    if (!selectedFile) return;
    setAnalyzing(true);
    setError(null);
    setAnalysis(null);
    try {
      const { data } = await ax.post("/api/admin/ai-dev-team/analyze", {
        file: selectedFile, agent: selectedAgent,
      });
      setAnalysis(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la analiză");
    } finally { setAnalyzing(false); }
  };

  const copyAction = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (__) { /* swallow */ }
      document.body.removeChild(ta);
    }
    setCopied(key);
    setTimeout(() => setCopied(""), 2500);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">← Admin</Link>
        <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="dev-team-title">
          AI Development <span className="italic gradient-text">Team</span>
        </h1>
        <p className="text-sm text-stone-400 mt-2 max-w-2xl">4 agenți AI specializați analizează fișiere din cod și propun îmbunătățiri. <strong className="text-[#d4ff3a]">READ-ONLY</strong> — niciodată nu modifică cod direct, ci generează prompturi gata de copy-paste în chat-ul cu Emergent.</p>

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-2xl p-3 flex items-start gap-2 text-sm text-red-300">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />{error}
            <button onClick={() => setError(null)} className="ml-auto"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        <div className="grid lg:grid-cols-[1fr_2fr] gap-5 mt-6">
          {/* File picker */}
          <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileCode className="w-4 h-4 text-[#d4ff3a]" />
              <h2 className="font-serif text-lg">Alege fișierul</h2>
            </div>
            <div className="flex gap-2 mb-2">
              <button onClick={() => setFilterKind("")} className={`text-xs px-3 py-1.5 rounded-full border ${!filterKind ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`}>Toate</button>
              <button onClick={() => setFilterKind("frontend")} className={`text-xs px-3 py-1.5 rounded-full border ${filterKind === "frontend" ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`}>Frontend</button>
              <button onClick={() => setFilterKind("backend")} className={`text-xs px-3 py-1.5 rounded-full border ${filterKind === "backend" ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`}>Backend</button>
            </div>
            <div className="relative mb-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Caută fișier..." className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-sm focus:outline-none" data-testid="dev-file-search" />
            </div>
            <div className="text-[10px] text-stone-500 mb-2">{files.length} fișiere · afișez {filteredFiles.length}</div>
            <div className="max-h-[400px] overflow-y-auto space-y-1">
              {filteredFiles.map(f => (
                <button key={f} onClick={() => setSelectedFile(f)} className={`w-full text-left text-xs font-mono px-3 py-1.5 rounded-lg ${selectedFile === f ? "bg-[#d4ff3a]/15 text-[#d4ff3a] border border-[#d4ff3a]/40" : "hover:bg-white/5 text-stone-300"}`} data-testid={`dev-file-${f.replace(/[^a-z0-9]/gi, '-')}`}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Analysis pane */}
          <div className="space-y-4">
            <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-[#d4ff3a]" />
                <h2 className="font-serif text-lg">Configurare analiză</h2>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-stone-400 uppercase tracking-wider">Fișier selectat</label>
                  <div className="mt-1 px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-mono text-stone-300 truncate" data-testid="dev-selected-file">{selectedFile || "— niciun fișier selectat —"}</div>
                </div>
                <div>
                  <label className="text-xs text-stone-400 uppercase tracking-wider">Agent</label>
                  <select value={selectedAgent} onChange={e => setSelectedAgent(e.target.value)} className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="dev-agent-select">
                    <option value="auto">Auto (după extensie)</option>
                    {Object.entries(agents).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
                <button onClick={analyze} disabled={analyzing || !selectedFile} className="pm-btn pm-btn-primary" data-testid="dev-analyze-btn">
                  {analyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> Agentul analizează...</> : <><Brain className="w-4 h-4" /> Analizează</>}
                </button>
              </div>
            </div>

            {analysis && (
              <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-5 space-y-4" data-testid="dev-analysis-output">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <Pill className="bg-violet-500/15 text-violet-300 border-violet-500/30 mb-2">{analysis.agent_label}</Pill>
                    <div className="font-mono text-xs text-stone-400">{analysis.file}</div>
                  </div>
                  <div className="text-[10px] text-stone-500">{analysis.provider} · {analysis.model}</div>
                </div>
                <p className="text-sm text-stone-200">{analysis.summary}</p>

                {analysis.issues?.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-red-400 mb-2 flex items-center gap-1"><Bug className="w-3 h-3" /> Probleme ({analysis.issues.length})</div>
                    <div className="space-y-2">
                      {analysis.issues.map((iss, i) => (
                        <div key={i} className="bg-white/[0.02] border border-white/5 rounded-xl p-3" data-testid={`dev-issue-${i}`}>
                          <div className="flex items-center gap-2 mb-1">
                            <Pill className={SEV_COLOR[iss.severity] || SEV_COLOR.P2}>{iss.severity}</Pill>
                            <span className="text-sm font-medium">{iss.title}</span>
                          </div>
                          <div className="text-xs text-stone-400">{iss.description}</div>
                          {iss.line_hint && <div className="text-[10px] text-stone-500 mt-1 font-mono">{iss.line_hint}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.improvements?.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-cyan-400 mb-2 flex items-center gap-1"><Lightbulb className="w-3 h-3" /> Îmbunătățiri</div>
                    <ul className="space-y-1 text-sm text-stone-300">
                      {analysis.improvements.map((s, i) => <li key={i} className="flex gap-2"><span className="text-cyan-400">→</span> {s}</li>)}
                    </ul>
                  </div>
                )}

                {analysis.security_concerns?.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-rose-400 mb-2 flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Risc de securitate</div>
                    <ul className="space-y-1 text-sm text-rose-200">
                      {analysis.security_concerns.map((s, i) => <li key={i} className="flex gap-2"><span>⚠</span> {s}</li>)}
                    </ul>
                  </div>
                )}

                {analysis.next_actions?.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[#d4ff3a] mb-2 flex items-center gap-1"><ListChecks className="w-3 h-3" /> Prompturi gata pentru Emergent</div>
                    <div className="space-y-2">
                      {analysis.next_actions.map((s, i) => (
                        <div key={i} className="bg-[#0a0a0b] border border-[#d4ff3a]/20 rounded-xl p-3 text-xs text-stone-200 relative">
                          <button onClick={() => copyAction(s, `act-${i}`)} className="absolute top-2 right-2 text-stone-500 hover:text-[#d4ff3a]" data-testid={`dev-copy-action-${i}`}>
                            {copied === `act-${i}` ? <CheckCircle2 className="w-3.5 h-3.5 text-[#d4ff3a]" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                          <div className="pr-8 whitespace-pre-wrap leading-relaxed">{s}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.issues?.length === 0 && analysis.improvements?.length === 0 && analysis.security_concerns?.length === 0 && (
                  <div className="text-sm text-emerald-300 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Niciun issue detectat. Codul arată bine!</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 bg-violet-500/10 border border-violet-500/30 rounded-3xl p-5 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
          <div className="text-xs text-violet-100">
            <strong>Read-only by design:</strong> Acești agenți NU modifică niciodată cod direct. Toate sugestiile sunt prompturi pe care le copiezi și le lipești în chat cu Emergent pentru aplicare manuală cu validare.
          </div>
        </div>
      </div>
    </div>
  );
}
