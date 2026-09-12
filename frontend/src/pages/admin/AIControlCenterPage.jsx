import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Brain, Cpu, Database, Network, Bug, Sparkles, Power, Save, Loader2,
  AlertCircle, CheckCircle2, RefreshCcw, Trash2, Search, Activity,
  Settings, Zap, ChevronRight, X, ShieldCheck
} from "lucide-react";
import { AIInsightCard } from "../../design-system";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const Pill = ({ children, className = "", ...p }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium border ${className}`} {...p}>
    {children}
  </span>
);

const Card = ({ icon: Icon, title, value, sub, color = "lime", testid }) => (
  <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid={testid}>
    <div className="flex items-start gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center bg-${color}-500/15 border border-${color}-500/30`}>
        <Icon className={`w-4 h-4 text-${color}-400`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-stone-400">{title}</div>
        <div className="font-serif text-2xl mt-0.5">{value}</div>
        {sub && <div className="text-[10px] text-stone-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  </div>
);

// ========================= CONFIG SECTION =========================
const ConfigSection = ({ data, providers, onUpdate }) => {
  const [form, setForm] = useState(data);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => { setForm(data); }, [data]);

  const submit = async () => {
    setSaving(true);
    try {
      await onUpdate(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally { setSaving(false); }
  };

  const providerEntries = Object.entries(providers || {});
  const activeProvider = providers?.[form.provider];
  const models = activeProvider?.models || [];

  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-[#d4ff3a]" />
          <h2 className="font-serif text-xl">Configurare AI</h2>
        </div>
        <div className="flex items-center gap-2">
          <Pill className={form.enabled ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" : "bg-stone-500/15 text-stone-400 border-stone-500/30"}>
            {form.enabled ? "ECOSISTEM ACTIV" : "ECOSISTEM DEZACTIVAT"}
          </Pill>
          <button
            onClick={() => setForm({ ...form, enabled: !form.enabled })}
            className={`pm-btn pm-btn-sm ${form.enabled ? "pm-btn-danger" : "pm-btn-success"}`}
            data-testid="ai-toggle-enabled"
          >
            <Power className="w-3 h-3" /> {form.enabled ? "Dezactivează" : "Activează"}
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-stone-400 uppercase tracking-wider">Provider</label>
          <select
            value={form.provider}
            onChange={e => setForm({ ...form, provider: e.target.value, model: providers[e.target.value]?.models?.[0] || form.model })}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm focus:outline-none"
            data-testid="ai-config-provider"
          >
            {providerEntries.map(([k, p]) => (
              <option key={k} value={k} disabled={!p.active}>
                {p.label}{!p.active ? " (Faza 5)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-stone-400 uppercase tracking-wider">Model</label>
          <select
            value={form.model}
            onChange={e => setForm({ ...form, model: e.target.value })}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm focus:outline-none"
            data-testid="ai-config-model"
          >
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-stone-400 uppercase tracking-wider">Temperature ({form.temperature})</label>
          <input
            type="range" min="0" max="2" step="0.1"
            value={form.temperature}
            onChange={e => setForm({ ...form, temperature: parseFloat(e.target.value) })}
            className="w-full mt-2 accent-[#d4ff3a]"
            data-testid="ai-config-temperature"
          />
          <div className="text-[10px] text-stone-500 mt-1">Mai mic = deterministic. Mai mare = creativ.</div>
        </div>
        <div>
          <label className="text-xs text-stone-400 uppercase tracking-wider">Max Tokens</label>
          <input
            type="number" min="128" max="8192" step="128"
            value={form.max_tokens}
            onChange={e => setForm({ ...form, max_tokens: parseInt(e.target.value) || 2048 })}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm focus:outline-none"
            data-testid="ai-config-max-tokens"
          />
        </div>
      </div>

      <div className="mt-5 flex justify-end">
        <button onClick={submit} disabled={saving} className="pm-btn pm-btn-primary" data-testid="ai-config-save">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saving ? "Se salvează..." : saved ? "Salvat ✓" : "Salvează configurarea"}
        </button>
      </div>
    </div>
  );
};

// ========================= AGENTS LIST =========================
const AgentsList = ({ agents }) => (
  <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
    <div className="flex items-center gap-2 mb-4">
      <Brain className="w-4 h-4 text-[#d4ff3a]" />
      <h2 className="font-serif text-xl">Agenți AI</h2>
      <Pill className="bg-white/5 text-stone-300 border-white/10 ml-auto">{agents.length}</Pill>
    </div>
    <div className="space-y-2">
      {agents.map(a => (
        <Link key={a.id} to={a.path} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] transition-colors" data-testid={`ai-agent-${a.id}`}>
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${a.status === "active" ? "bg-emerald-400 animate-pulse" : "bg-stone-600"}`} />
            <div>
              <div className="text-sm font-medium">{a.label}</div>
              <div className="text-[10px] text-stone-500 uppercase tracking-wider">{a.kind} · {a.status}</div>
            </div>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-stone-500" />
        </Link>
      ))}
    </div>
  </div>
);

// ========================= MEMORY BROWSER =========================
const MemoryBrowser = () => {
  const [items, setItems] = useState([]);
  const [filterUser, setFilterUser] = useState("");
  const [filterScope, setFilterScope] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterUser) params.user_id = filterUser;
      if (filterScope) params.scope = filterScope;
      const { data } = await ax.get("/api/admin/ai-control/memories", { params });
      setItems(data.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filterScope]);

  const del = async (id) => {
    if (!window.confirm("Ștergi această amintire?")) return;
    await ax.delete(`/api/admin/ai-control/memories/${id}`);
    await load();
  };

  const resetUser = async () => {
    const target = window.prompt("Email sau ID user pentru reset memorii (sau '*' pentru TOATE):");
    if (!target) return;
    if (target === "*" && !window.confirm("Sigur ștergi TOATE amintirile pentru toți utilizatorii?")) return;
    const { data } = await ax.post("/api/admin/ai-control/memories/reset", { user_id: target });
    alert(`Șterse: ${data.deleted_count}`);
    await load();
  };

  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Database className="w-4 h-4 text-[#d4ff3a]" />
        <h2 className="font-serif text-xl">Memorie Persistentă</h2>
        <div className="ml-auto flex gap-2">
          <input
            value={filterUser}
            onChange={e => setFilterUser(e.target.value)}
            onKeyDown={e => e.key === "Enter" && load()}
            placeholder="Filter user_id / email"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs"
            data-testid="ai-mem-filter-user"
          />
          <select
            value={filterScope}
            onChange={e => setFilterScope(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs"
            data-testid="ai-mem-filter-scope"
          >
            <option value="">Toate scope-urile</option>
            <option value="concierge">concierge</option>
            <option value="qa_copilot">qa_copilot</option>
            <option value="client_agent">client_agent</option>
            <option value="admin_agent">admin_agent</option>
            <option value="tech_agent">tech_agent</option>
          </select>
          <button onClick={load} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="ai-mem-refresh"><RefreshCcw className="w-3 h-3" /></button>
          <button onClick={resetUser} className="pm-btn pm-btn-danger pm-btn-sm" data-testid="ai-mem-reset"><Trash2 className="w-3 h-3" />Reset</button>
        </div>
      </div>
      {loading && <div className="text-xs text-stone-400 py-6 text-center"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă...</div>}
      {!loading && items.length === 0 && <div className="text-xs text-stone-500 italic py-6 text-center">Nicio amintire (ai_memories e gol). Va începe să se populeze pe măsură ce folosești QA Copilot și viitorii agenți.</div>}
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {items.map(m => (
          <div key={m.id} className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-start gap-3" data-testid={`ai-mem-item-${m.id}`}>
            <Pill className="bg-violet-500/15 text-violet-300 border-violet-500/30 shrink-0">{m.scope}</Pill>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-stone-100">{m.summary}</div>
              <div className="text-[10px] text-stone-500 mt-0.5">user: {m.user_id} · source: {m.source} · {new Date(m.created_at).toLocaleString("ro-RO")}</div>
            </div>
            <button onClick={() => del(m.id)} className="text-stone-500 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
          </div>
        ))}
      </div>
    </div>
  );
};

// ========================= BUG SEARCH =========================
const BugSearch = () => {
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!q.trim() || q.trim().length < 2) return;
    setLoading(true);
    try {
      const { data } = await ax.get("/api/admin/ai-control/bugs/search", { params: { q: q.trim(), limit: 15 } });
      setItems(data.items || []);
    } finally { setLoading(false); }
  };

  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Bug className="w-4 h-4 text-[#d4ff3a]" />
        <h2 className="font-serif text-xl">Bug Memory · Caută în istoric</h2>
      </div>
      <div className="flex gap-2 mb-3">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === "Enter" && search()}
          placeholder="Ex: chat nu apare, specialist cluj, plata escrow..."
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none"
          data-testid="ai-bug-search-input"
        />
        <button onClick={search} disabled={loading || q.trim().length < 2} className="pm-btn pm-btn-primary" data-testid="ai-bug-search-btn">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Caută
        </button>
      </div>
      {items.length === 0 && !loading && <div className="text-xs text-stone-500 italic py-4 text-center">Scrie un keyword și apasă Enter ca să cauți în toate sesiunile QA și findings-urile AI Investigator.</div>}
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {items.map(b => (
          <div key={`${b.source}-${b.id}`} className="p-3 rounded-xl bg-white/[0.02] border border-white/5" data-testid={`ai-bug-result-${b.id}`}>
            <div className="flex items-start gap-2 mb-1 flex-wrap">
              <Pill className="bg-stone-500/15 text-stone-300 border-stone-500/30">{b.source}</Pill>
              {b.category && <Pill className="bg-amber-500/15 text-amber-300 border-amber-500/30">{b.category}</Pill>}
              {b.severity && <Pill className="bg-red-500/15 text-red-300 border-red-500/30">{b.severity}</Pill>}
              <span className="ml-auto text-[10px] text-stone-500">scor: {b.score}</span>
            </div>
            <div className="text-sm text-stone-100">{b.summary || b.text}</div>
            {b.session_title && <div className="text-[10px] text-cyan-400 mt-1">← Sesiune: {b.session_title}</div>}
          </div>
        ))}
      </div>
    </div>
  );
};

// ========================= KNOWLEDGE GRAPH =========================
const KGSection = ({ stats }) => {
  const [userId, setUserId] = useState("");
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!userId.trim()) return;
    setLoading(true);
    try {
      const { data } = await ax.get("/api/admin/ai-control/graph", { params: { user_id: userId.trim() } });
      setGraph(data);
    } catch (e) {
      setGraph({ nodes: [], edges: [], error: e?.response?.data?.detail || "Nu s-a putut încărca graful" });
    } finally { setLoading(false); }
  };

  const nodeIcon = (type) => {
    const map = { user: "👤", property: "🏠", request: "🔧", specialist: "🛠", listing: "🏢" };
    return map[type] || "•";
  };

  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Network className="w-4 h-4 text-[#d4ff3a]" />
        <h2 className="font-serif text-xl">Knowledge Graph</h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-4">
        {stats && Object.entries(stats.nodes || {}).map(([k, v]) => (
          <div key={k} className="text-center p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="font-serif text-2xl text-[#d4ff3a]">{v}</div>
            <div className="text-[10px] text-stone-500 uppercase tracking-wider">{k}</div>
          </div>
        ))}
      </div>
      <div className="flex gap-2 mb-3">
        <input
          value={userId}
          onChange={e => setUserId(e.target.value)}
          onKeyDown={e => e.key === "Enter" && load()}
          placeholder="Email sau ID user (ex: client@propmanage.io)"
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none"
          data-testid="ai-graph-user-input"
        />
        <button onClick={load} disabled={loading || !userId.trim()} className="pm-btn pm-btn-primary" data-testid="ai-graph-load">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Vizualizează
        </button>
      </div>
      {graph?.error && <div className="text-xs text-red-400">{graph.error}</div>}
      {graph && !graph.error && (
        <div className="bg-[#0a0a0b] border border-white/10 rounded-2xl p-4 max-h-[400px] overflow-y-auto" data-testid="ai-graph-output">
          <div className="text-xs text-stone-400 mb-2">{graph.nodes?.length || 0} noduri · {graph.edges?.length || 0} relații</div>
          <div className="space-y-1 font-mono text-xs">
            {(graph.nodes || []).map(n => (
              <div key={n.id} className="flex items-start gap-2 py-1">
                <span className="shrink-0">{nodeIcon(n.type)}</span>
                <span className="text-stone-300">{n.type}:</span>
                <span className="text-stone-100">{n.label}</span>
                {n.meta?.role && <Pill className="bg-violet-500/15 text-violet-300 border-violet-500/30">{n.meta.role}</Pill>}
                {n.meta?.status && <Pill className="bg-cyan-500/15 text-cyan-300 border-cyan-500/30">{n.meta.status}</Pill>}
                {n.meta?.specialty && <Pill className="bg-amber-500/15 text-amber-300 border-amber-500/30">{n.meta.specialty}</Pill>}
              </div>
            ))}
            {(graph.edges || []).length > 0 && (
              <div className="mt-3 pt-3 border-t border-white/5">
                <div className="text-[10px] text-stone-500 mb-1 uppercase tracking-wider">Relații</div>
                {graph.edges.map((e, i) => (
                  <div key={i} className="py-0.5 text-stone-400">
                    {e.from} <span className="text-[#d4ff3a]">→ {e.label} →</span> {e.to}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ========================= MAIN PAGE =========================
export const AIControlCenterPage = () => {
  const [overview, setOverview] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await ax.get("/api/admin/ai-control/overview");
      setOverview(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    ax.get("/api/admin/insights/rule?module=ai_control").then(r => setInsights(r.data)).catch(() => {});
  }, []);

  const updateConfig = async (form) => {
    const { data } = await ax.put("/api/admin/ai-control/config", form);
    setOverview(o => o ? { ...o, config: data } : o);
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă...</div>;
  if (!overview) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-red-400">{error || "Eroare"}</div>;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3">← Înapoi la Admin Dashboard</Link>
        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div>
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="ai-control-title">
              AI <span className="italic gradient-text">Control Center</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-2xl">Centru unificat pentru toți agenții AI din ecosistem. Memorie persistentă · Bug search · Knowledge graph · Provider switch.</p>
          </div>
          <button onClick={load} className="pm-btn pm-btn-secondary pm-btn-sm"><RefreshCcw className="w-3.5 h-3.5" /> Refresh</button>
        </div>

        {/* Top stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          <Card icon={Cpu} title="Model activ" value={overview.config.model.split("-")[0]} sub={overview.config.provider} color="lime" testid="ai-stat-model" />
          <Card icon={Database} title="Amintiri salvate" value={overview.memory.total} sub={`${Object.values(overview.memory.by_scope).filter(v => v > 0).length} scope-uri active`} color="violet" testid="ai-stat-memories" />
          <Card icon={Bug} title="Bug-uri în istoric" value={overview.bugs.total} sub={`QA: ${overview.bugs.qa_findings} · AI: ${overview.bugs.ai_investigator_findings}`} color="red" testid="ai-stat-bugs" />
          <Card icon={Activity} title="Agenți activi" value={overview.agents.filter(a => a.status === "active").length} sub={`din ${overview.agents.length} total`} color="cyan" testid="ai-stat-agents" />
        </div>

        {/* AI Insights v2 — rule-based + LLM (Claude) */}
        <div className="mt-5">
          <AIInsightCard
            bullets={insights?.bullets || []} alerts={insights?.alerts || []}
            recommendations={insights?.recommendations || []}
            loading={!insights} llmModule="ai_control" testid="ai-control-insights"
          />
        </div>

        <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-5 mt-6">
          <ConfigSection data={overview.config} providers={overview.providers} onUpdate={updateConfig} />
          <AgentsList agents={overview.agents} />
        </div>

        <div className="mt-5"><MemoryBrowser /></div>
        <div className="mt-5"><BugSearch /></div>
        <div className="mt-5"><KGSection stats={overview.graph} /></div>

        <div className="mt-8 bg-amber-500/10 border border-amber-500/30 rounded-3xl p-5 flex items-start gap-3" data-testid="ai-safety-note">
          <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-100">
            <strong>Siguranță &amp; reversibilitate:</strong> Dezactivează ecosistemul oricând din toggle-ul de mai sus. Toate datele rămân în Mongo (`ai_memories`) și pot fi resetate per user sau global. Module legacy (Concierge, AI Investigator, QA Copilot) funcționează independent — nu sunt afectate.
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIControlCenterPage;
