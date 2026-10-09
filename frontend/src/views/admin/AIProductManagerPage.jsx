// AIProductManagerPage — P5: Idea -> Epic > Features > Stories breakdown.
//
// Paste a raw idea, AI returns structured tree with acceptance criteria,
// effort estimates and risks. Inject features as TODOs with one click.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Layers, ChevronLeft, Loader2, Sparkles, AlertTriangle,
  Trash2, ArrowRight, ListChecks, Target, ShieldAlert, Wand2,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const PRIORITY_COLOR = {
  P0: "bg-red-500/15 border-red-500/50 text-red-200",
  P1: "bg-amber-500/15 border-amber-500/50 text-amber-200",
  P2: "bg-blue-500/15 border-blue-500/50 text-blue-200",
  P3: "bg-stone-500/15 border-stone-500/50 text-stone-300",
};
const SEVERITY_COLOR = {
  critical: "text-red-300",
  high:     "text-amber-300",
  medium:   "text-blue-300",
  low:      "text-stone-400",
};

const AIProductManagerPage = () => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [context, setContext] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [injecting, setInjecting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await ax.get("/api/admin/ai-pm/breakdowns");
        if (!cancelled) setHistory(data.items || []);
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const submit = async (e) => {
    e?.preventDefault();
    if (title.trim().length < 3 || description.trim().length < 10) return;
    setSubmitting(true);
    try {
      const { data } = await ax.post("/api/admin/ai-pm/breakdown", {
        title: title.trim(),
        description: description.trim(),
        context: context.trim(),
      });
      setCurrent(data);
      const h = await ax.get("/api/admin/ai-pm/breakdowns");
      setHistory(h.data.items || []);
    } catch (err) {
      alert("Eroare: " + (err?.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const loadOne = async (id) => {
    const { data } = await ax.get(`/api/admin/ai-pm/breakdowns/${id}`);
    setCurrent(data);
    window.scrollTo({ top: 200, behavior: "smooth" });
  };

  const removeOne = async (id) => {
    if (!window.confirm("Șterg acest breakdown?")) return;
    await ax.delete(`/api/admin/ai-pm/breakdowns/${id}`);
    const h = await ax.get("/api/admin/ai-pm/breakdowns");
    setHistory(h.data.items || []);
    if (current?.id === id) setCurrent(null);
  };

  const injectTodos = async () => {
    if (!current) return;
    if (!window.confirm(`Injectez toate feature-urile (${(current.result?.features || []).length}) ca TODO-uri în Board?`)) return;
    setInjecting(true);
    try {
      const { data } = await ax.post(`/api/admin/ai-pm/breakdowns/${current.id}/inject-todos`);
      alert(`${data.injected} TODO-uri create din ${data.total_features || 0} feature-uri.`);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="aipm-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center shrink-0">
            <Layers className="w-5 h-5 text-violet-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="aipm-title">
              AI <span className="italic gradient-text">Product Manager</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Transformă o idee într-o ierarhie <strong>Epic → Features → User Stories</strong> cu acceptance criteria, effort estimates și risc analysis. Injectează features-urile ca TODO-uri cu un click.
            </p>
          </div>
        </div>

        {/* SUBMIT FORM */}
        <form onSubmit={submit} className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mb-6 space-y-3" data-testid="aipm-form">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Titlu idee *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ex: Onboarding self-serve pentru specialiști"
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="aipm-input-title"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Descriere *</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Descrie problema, soluția propusă, user-ii afectați, beneficii așteptate..."
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="aipm-input-description"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Context business (opțional)</label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={2}
              placeholder="ex: Targetăm specialiști HVAC din București. Conversion baseline 12%. Buget dev: ~80 credite."
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="aipm-input-context"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || title.trim().length < 3 || description.trim().length < 10}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-violet-500/20 border border-violet-500/40 text-violet-200 hover:bg-violet-500/30 disabled:opacity-50 text-sm"
              data-testid="aipm-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              {submitting ? "Descompun..." : "Descompune ideea"}
            </button>
          </div>
        </form>

        {/* CURRENT RESULT */}
        {current && <BreakdownResult breakdown={current} onInject={injectTodos} onDelete={removeOne} injecting={injecting} />}

        {/* HISTORY */}
        <div className="mt-6">
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">Istoric breakdowns ({history.length})</h3>
          {loading ? (
            <div className="text-center py-6 text-stone-500 text-sm flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-stone-500 text-sm bg-white/[0.02] border border-white/10 rounded-xl">
              Niciun breakdown încă. Trimite prima idee mai sus.
            </div>
          ) : (
            <div className="space-y-2">
              {history.map(h => (
                <button
                  key={h.id}
                  onClick={() => loadOne(h.id)}
                  className="w-full text-left bg-white/[0.02] border border-white/10 rounded-xl p-3 hover:bg-white/[0.05]"
                  data-testid={`aipm-history-${h.id}`}
                >
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-violet-300 shrink-0 mt-1" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white font-medium truncate">{h.title}</div>
                      <div className="text-[10px] text-stone-500 mt-0.5">
                        {(h.result?.features || []).length} features
                        {" · "}
                        {new Date(h.submitted_at).toLocaleString("ro-RO")}
                        {" · "}
                        {h.submitted_by || "?"}
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-stone-500 shrink-0 mt-1" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const BreakdownResult = ({ breakdown, onInject, onDelete, injecting }) => {
  const r = breakdown.result || {};
  const epic = r.epic || {};
  const features = r.features || [];
  const risks = r.risks || [];
  const oos = r.out_of_scope || [];

  return (
    <div className="bg-[#0e0e10] border border-violet-500/30 rounded-2xl p-5" data-testid="aipm-result">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] text-stone-500 uppercase tracking-wider mb-1">Epic</div>
          <h3 className="text-lg font-serif text-white">{epic.title || breakdown.title}</h3>
          {epic.goal && (
            <div className="text-xs text-stone-400 mt-1 flex items-start gap-1.5">
              <Target className="w-3 h-3 mt-0.5 shrink-0 text-violet-300" />
              <span>{epic.goal}</span>
            </div>
          )}
          {epic.success_metric && (
            <div className="text-[11px] text-emerald-300 mt-2">📊 Success metric: <em>{epic.success_metric}</em></div>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {breakdown.llm_error && (
            <span className="text-[10px] px-2 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300" title={breakdown.llm_error}>
              <AlertTriangle className="w-3 h-3 inline" /> Fallback
            </span>
          )}
          {features.length > 0 && (
            <button
              onClick={onInject}
              disabled={injecting}
              className="text-[11px] inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50"
              data-testid="aipm-inject-todos"
            >
              {injecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <ListChecks className="w-3 h-3" />}
              Injectează în TODO
            </button>
          )}
          <button onClick={() => onDelete(breakdown.id)} className="text-stone-500 hover:text-red-400" data-testid="aipm-result-delete">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* FEATURES */}
      <div className="space-y-2 mb-4">
        {features.map((f, i) => (
          <div key={f.id || i} className="bg-white/[0.02] border border-white/10 rounded-xl p-3" data-testid={`aipm-feature-${i}`}>
            <div className="flex items-center gap-2 flex-wrap mb-1.5">
              <span className="font-mono text-[10px] text-stone-500">{f.id || `F${i+1}`}</span>
              <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded border ${PRIORITY_COLOR[f.priority] || PRIORITY_COLOR.P2}`}>
                {f.priority || "P2"}
              </span>
              <span className="text-[10px] text-stone-500">~{f.effort_estimate_days ?? "?"}z</span>
              <span className="text-sm font-semibold text-white">{f.title}</span>
            </div>
            <div className="text-xs text-stone-400 mb-2">{f.description}</div>
            {(f.stories || []).length > 0 && (
              <details className="text-[11px] text-stone-300">
                <summary className="cursor-pointer text-violet-300 hover:text-violet-200">
                  {(f.stories || []).length} stories
                </summary>
                <div className="mt-2 space-y-2 pl-2 border-l border-white/10">
                  {(f.stories || []).map((s, j) => (
                    <div key={s.id || j} data-testid={`aipm-story-${i}-${j}`}>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] text-stone-500">{s.id || `${f.id}-S${j+1}`}</span>
                        <span className="text-stone-300">Ca <strong className="text-violet-200">{s.as_a}</strong>, vreau <strong>{s.i_want}</strong>, ca să <em>{s.so_that}</em>.</span>
                      </div>
                      {(s.acceptance_criteria || []).length > 0 && (
                        <ul className="mt-1 ml-4 list-disc text-[11px] text-stone-400 space-y-0.5">
                          {(s.acceptance_criteria || []).map((ac, k) => (<li key={k}>{ac}</li>))}
                        </ul>
                      )}
                      {s.technical_notes && (
                        <div className="text-[10px] text-stone-500 italic mt-0.5 ml-4">⚙️ {s.technical_notes}</div>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
      </div>

      {/* RISKS */}
      {risks.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" /> Riscuri ({risks.length})
          </div>
          <div className="space-y-1">
            {risks.map((rk, i) => (
              <div key={i} className="text-xs flex items-start gap-2" data-testid={`aipm-risk-${i}`}>
                <span className={`uppercase font-mono text-[10px] shrink-0 ${SEVERITY_COLOR[rk.severity] || SEVERITY_COLOR.medium}`}>{rk.severity || "medium"}</span>
                <span className="text-stone-200"><strong>{rk.title}.</strong> <span className="text-stone-400">{rk.mitigation}</span></span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OUT OF SCOPE */}
      {oos.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1">Out of scope (versiunea curentă)</div>
          <ul className="text-[11px] text-stone-400 list-disc ml-4 space-y-0.5">
            {oos.map((o, i) => (<li key={i}>{o}</li>))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default AIProductManagerPage;
