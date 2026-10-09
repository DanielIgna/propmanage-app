// ArchitectureBoardPage — P3: prevent module redundancy before building.
//
// Workflow: paste a new feature idea → AI checks overlap with existing modules
// → returns verdict (build_new / extend_existing / merge_proposal / reject_duplicate)
// and concrete suggested actions.
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Compass, ChevronLeft, Loader2, Sparkles, AlertTriangle,
  CheckCircle2, Database, Trash2, ArrowRight,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const VERDICT_META = {
  build_new:           { label: "Construiește nou",   color: "bg-emerald-500/15 border-emerald-500/50 text-emerald-200" },
  extend_existing:     { label: "Extinde existent",   color: "bg-blue-500/15 border-blue-500/50 text-blue-200" },
  merge_proposal:      { label: "Merge propunere",    color: "bg-amber-500/15 border-amber-500/50 text-amber-200" },
  reject_duplicate:    { label: "Respinge duplicat",  color: "bg-red-500/15 border-red-500/50 text-red-200" },
};
const RISK_META = {
  low:    { label: "Risc scăzut",   color: "text-emerald-300" },
  medium: { label: "Risc mediu",    color: "text-amber-300" },
  high:   { label: "Risc ridicat",  color: "text-red-300" },
};

const ArchitectureBoardPage = () => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [scope, setScope] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [catalogCount, setCatalogCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [r, c] = await Promise.all([
          ax.get("/api/admin/architecture-board/reviews"),
          ax.get("/api/admin/architecture-board/catalog"),
        ]);
        if (cancelled) return;
        setReviews(r.data.items || []);
        setCatalogCount(c.data.count || 0);
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const submit = async (e) => {
    e?.preventDefault();
    if (title.trim().length < 3 || description.trim().length < 10) return;
    setSubmitting(true);
    try {
      const { data } = await ax.post("/api/admin/architecture-board/review", {
        title: title.trim(),
        description: description.trim(),
        proposed_scope: scope.trim(),
      });
      setCurrentResult(data);
      // refresh history
      const r = await ax.get("/api/admin/architecture-board/reviews");
      setReviews(r.data.items || []);
    } catch (err) {
      alert("Eroare: " + (err?.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const deleteReview = async (id) => {
    if (!window.confirm("Șterg acest review?")) return;
    await ax.delete(`/api/admin/architecture-board/reviews/${id}`);
    const r = await ax.get("/api/admin/architecture-board/reviews");
    setReviews(r.data.items || []);
    if (currentResult?.id === id) setCurrentResult(null);
  };

  const loadReview = async (id) => {
    const { data } = await ax.get(`/api/admin/architecture-board/reviews/${id}`);
    setCurrentResult(data);
    window.scrollTo({ top: 200, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="arch-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center shrink-0">
            <Compass className="w-5 h-5 text-blue-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="arch-title">
              Architecture <span className="italic gradient-text">Review Board</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Înainte de a construi orice modul nou, lipește-l aici. AI verifică suprapunerile cu cele {catalogCount} module existente și recomandă: <code>build_new</code>, <code>extend_existing</code>, <code>merge_proposal</code> sau <code>reject_duplicate</code>.
            </p>
          </div>
        </div>

        {/* SUBMIT FORM */}
        <form onSubmit={submit} className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mb-6 space-y-3" data-testid="arch-form">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Titlu propunere *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ex: AI Health Monitor Dashboard"
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="arch-input-title"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Descriere completă *</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Descrie ce face propunerea, pentru cine, ce probleme rezolvă, fluxuri principale..."
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="arch-input-description"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-stone-500">Scope propus (opțional)</label>
            <input
              type="text"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              placeholder="ex: 1 backend route + 1 admin page + 1 cron job"
              className="w-full mt-1 bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-white/30"
              data-testid="arch-input-scope"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || title.trim().length < 3 || description.trim().length < 10}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-500/40 text-blue-200 hover:bg-blue-500/30 disabled:opacity-50 text-sm"
              data-testid="arch-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              {submitting ? "Analizez..." : "Verifică suprapuneri"}
            </button>
          </div>
        </form>

        {/* CURRENT RESULT */}
        {currentResult && <ReviewResult review={currentResult} onDelete={deleteReview} />}

        {/* HISTORY */}
        <div className="mt-6">
          <h3 className="text-xs uppercase tracking-wider text-stone-400 mb-2">Istoric reviews ({reviews.length})</h3>
          {loading ? (
            <div className="text-center py-6 text-stone-500 text-sm flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
            </div>
          ) : reviews.length === 0 ? (
            <div className="text-center py-8 text-stone-500 text-sm bg-white/[0.02] border border-white/10 rounded-xl">
              Niciun review încă. Trimite prima propunere mai sus.
            </div>
          ) : (
            <div className="space-y-2">
              {reviews.map(r => {
                const v = VERDICT_META[r.result?.verdict] || VERDICT_META.build_new;
                return (
                  <button
                    key={r.id}
                    onClick={() => loadReview(r.id)}
                    className="w-full text-left bg-white/[0.02] border border-white/10 rounded-xl p-3 hover:bg-white/[0.05] transition-colors"
                    data-testid={`arch-history-${r.id}`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`text-[10px] uppercase px-2 py-0.5 rounded border shrink-0 ${v.color}`}>{v.label}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white font-medium truncate">{r.title}</div>
                        <div className="text-[10px] text-stone-500 mt-0.5">
                          Overlap: <strong className="text-amber-300">{r.result?.overlap_score ?? "?"}%</strong>
                          {" · "}
                          {new Date(r.submitted_at).toLocaleString("ro-RO")}
                          {" · "}
                          {r.submitted_by || "?"}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-stone-500 shrink-0 mt-1" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ReviewResult = ({ review, onDelete }) => {
  const r = review.result || {};
  const v = VERDICT_META[r.verdict] || VERDICT_META.build_new;
  const risk = RISK_META[r.risk_of_redundancy] || RISK_META.medium;
  return (
    <div className="bg-[#0e0e10] border border-blue-500/30 rounded-2xl p-5" data-testid="arch-result">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] text-stone-500 uppercase tracking-wider mb-1">Verdict AI</div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-block text-xs uppercase font-semibold px-2.5 py-1 rounded-lg border ${v.color}`}>
              {v.label}
            </span>
            <span className="text-2xl font-mono text-amber-300">{r.overlap_score ?? 0}%</span>
            <span className="text-[10px] text-stone-500 uppercase">overlap</span>
            <span className={`text-[11px] uppercase ${risk.color}`}>· {risk.label}</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {review.llm_error && (
            <span className="text-[10px] px-2 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300" title={review.llm_error}>
              <AlertTriangle className="w-3 h-3 inline" /> Fallback
            </span>
          )}
          <button onClick={() => onDelete(review.id)} className="text-stone-500 hover:text-red-400" data-testid="arch-result-delete">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3 mb-3">
        <div className="text-sm text-white font-semibold">{review.title}</div>
        <div className="text-xs text-stone-400 mt-1 whitespace-pre-line">{review.description}</div>
        {review.proposed_scope && (
          <div className="text-[11px] text-stone-500 mt-2">Scope: <em>{review.proposed_scope}</em></div>
        )}
      </div>

      <div className="text-xs text-stone-300 mb-4 whitespace-pre-line italic" data-testid="arch-rationale">
        {r.rationale || "(fără rationale)"}
      </div>

      {/* Overlapping modules */}
      {(r.overlapping_modules || []).length > 0 && (
        <div className="mb-4">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
            <Database className="w-3 h-3" /> Module suprapuse ({r.overlapping_modules.length})
          </div>
          <div className="space-y-1.5">
            {r.overlapping_modules.map((m, i) => (
              <div key={i} className="bg-amber-500/5 border border-amber-500/30 rounded-lg p-2.5" data-testid={`arch-overlap-${i}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-amber-200">{m.name}</span>
                  <span className="font-mono text-[10px] text-stone-500">{m.slug}</span>
                  <span className="ml-auto text-xs font-mono text-amber-300">{m.weight}%</span>
                </div>
                <div className="text-xs text-stone-300 mt-1">{m.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested actions */}
      {(r.suggested_actions || []).length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Acțiuni recomandate
          </div>
          <ol className="space-y-1.5">
            {r.suggested_actions.map((a, i) => (
              <li key={i} className="text-xs text-stone-200 flex items-start gap-2" data-testid={`arch-action-${i}`}>
                <span className="text-stone-500 font-mono">{i + 1}.</span>
                <span className="flex-1">{a}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

export default ArchitectureBoardPage;
