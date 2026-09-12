// AI Design Concepts — style + budget + materials → orientative (inferred) concept.
// Reuses property context. Clearly marks AI/inferred + estimated budget. Shows render + 3D layer.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Sparkles, Wand2, X, Loader2, Palette, Coins, ShieldCheck, Image as ImageIcon,
  ChevronRight, AlertTriangle, GitCompare,
} from "lucide-react";
import { API } from "../pages/DashShared";
import { ConceptMaterials, RequestOfferButton, PreferButton } from "./ConceptComparison";

const TrustBadge = () => (
  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 text-[10px] font-semibold border border-amber-500/25" data-testid="design-inferred-badge">
    <AlertTriangle className="w-3 h-3" /> Orientativ AI · neverificat
  </span>
);

const ConceptResult = ({ c, onRequestReview, reviewBusy, projectId, onChanged }) => {
  const concept = c.concept || {};
  const budget = concept.budget || {};
  const status = c.status || "inferred";
  return (
    <div className="space-y-4" data-testid="design-concept-result">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="font-serif text-lg text-white">{concept.title || "Concept de design"}</h4>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            <TrustBadge />
            {status === "in_review" && <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25">În validare</span>}
            {status === "verified" && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">Verificat profesional</span>}
            {status === "rejected" && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-300 border border-red-500/25">Respins</span>}
          </div>
        </div>
      </div>

      {c.render_url && (
        <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30">
          <img
            src={`${process.env.REACT_APP_BACKEND_URL}${c.render_url}`}
            alt="Render concept AI"
            className="w-full h-auto object-cover"
            data-testid="design-render-img"
          />
          <div className="px-3 py-1.5 text-[10px] text-stone-500 flex items-center gap-1.5">
            <ImageIcon className="w-3 h-3" /> Render generat de AI (Gemini) — ilustrativ, nu fotografie reală
          </div>
        </div>
      )}
      {c.render_error && !c.render_url && (
        <div className="text-[11px] text-stone-500 bg-white/[0.03] border border-white/10 rounded-lg p-2">
          Render vizual indisponibil pentru acest concept.
        </div>
      )}

      {concept.summary && <p className="text-xs text-stone-300 leading-relaxed">{concept.summary}</p>}

      {(concept.palette || []).length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1.5 flex items-center gap-1.5"><Palette className="w-3 h-3" /> Paletă</div>
          <div className="flex flex-wrap gap-2">
            {concept.palette.map((p, i) => (
              <div key={i} className="flex items-center gap-1.5" data-testid={`design-swatch-${i}`}>
                <span className="w-6 h-6 rounded-md border border-white/20" style={{ backgroundColor: p.hex }} />
                <span className="text-[10px] text-stone-400">{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(concept.materials_plan || []).length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1.5">Plan materiale</div>
          <div className="space-y-1">
            {concept.materials_plan.map((m, i) => (
              <div key={i} className="text-xs text-stone-300 flex gap-2">
                <span className="text-stone-500 shrink-0">{m.surface}:</span>
                <span className="text-white">{m.material}</span>
                {m.note && <span className="text-stone-500">· {m.note}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {(budget.items?.length || budget.total_low || budget.total_high) && (
        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1.5 flex items-center gap-1.5"><Coins className="w-3 h-3" /> Buget ESTIMATIV</div>
          {(budget.items || []).map((it, i) => (
            <div key={i} className="flex justify-between text-xs text-stone-300 py-0.5">
              <span className="text-stone-400">{it.label}</span>
              <span className="font-mono">{it.low?.toLocaleString?.() ?? it.low}–{it.high?.toLocaleString?.() ?? it.high}</span>
            </div>
          ))}
          <div className="flex justify-between text-sm text-white font-semibold border-t border-white/10 mt-1.5 pt-1.5">
            <span>Total estimat</span>
            <span className="font-mono" data-testid="design-budget-total">{(budget.total_low ?? 0).toLocaleString()}–{(budget.total_high ?? 0).toLocaleString()} {budget.currency || "RON"}</span>
          </div>
          <p className="text-[10px] text-amber-400/90 mt-1.5">
            {budget.disclaimer || "Estimare orientativă, NU preț garantat de execuție."}
          </p>
        </div>
      )}

      {c.id && <ConceptMaterials conceptId={c.id} />}

      {c.id && projectId && <PreferButton concept={c} projectId={projectId} onChanged={onChanged} />}
      {c.id && <RequestOfferButton concept={c} projectId={projectId} onDone={onChanged} />}

      {c.model_id && status === "inferred" && (
        <button
          onClick={() => onRequestReview(c.model_id)}
          disabled={reviewBusy}
          className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-full border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-200 disabled:opacity-50"
          data-testid="design-request-review"
        >
          {reviewBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
          Trimite la validare profesională
        </button>
      )}
    </div>
  );
};

export const DesignConceptStudio = ({ projectId, projectName, onClose, onModelChanged, onOpenCompare }) => {
  const [options, setOptions] = useState({ styles: [], materials: [], default_currency: "RON" });
  const [concepts, setConcepts] = useState([]);
  const [view, setView] = useState("wizard"); // wizard | result
  const [active, setActive] = useState(null); // active concept
  const [busy, setBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [err, setErr] = useState(null);

  // form
  const [style, setStyle] = useState("");
  const [roomName, setRoomName] = useState("");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [materials, setMaterials] = useState([]);
  const [notes, setNotes] = useState("");
  const [genRender, setGenRender] = useState(true);

  const reloadConcepts = () => {
    axios.get(`${API}/digital-twin/projects/${projectId}/design-concepts`)
      .then((r) => {
        const items = r.data.items || [];
        setConcepts(items);
        setActive((a) => (a ? (items.find((x) => x.id === a.id) || a) : a));
      })
      .catch(() => {});
  };

  useEffect(() => {
    axios.get(`${API}/digital-twin/design-options`).then((r) => setOptions(r.data)).catch(() => {});
    axios.get(`${API}/digital-twin/projects/${projectId}/design-concepts`)
      .then((r) => setConcepts(r.data.items || [])).catch(() => {});
  }, [projectId]);

  const toggleMaterial = (m) =>
    setMaterials((arr) => (arr.includes(m) ? arr.filter((x) => x !== m) : [...arr, m]));

  const submit = async () => {
    if (!style) { setErr("Alege un stil."); return; }
    setBusy(true); setErr(null);
    try {
      const body = {
        style,
        room_name: roomName || null,
        budget_min: budgetMin ? Number(budgetMin) : null,
        budget_max: budgetMax ? Number(budgetMax) : null,
        currency: options.default_currency || "RON",
        materials,
        notes: notes || null,
        generate_render: genRender,
      };
      const { data } = await axios.post(`${API}/digital-twin/projects/${projectId}/design-concepts`, body);
      setConcepts((arr) => [data, ...arr]);
      setActive(data);
      setView("result");
      onModelChanged?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Generarea a eșuat.");
    } finally {
      setBusy(false);
    }
  };

  const requestReview = async (modelId) => {
    setReviewBusy(true);
    try {
      await axios.post(`${API}/digital-twin/models/${modelId}/request-review`, { note: "Concept AI Design" });
      setActive((c) => (c ? { ...c, status: "in_review" } : c));
      setConcepts((arr) => arr.map((x) => (x.model_id === modelId ? { ...x, status: "in_review" } : x)));
      onModelChanged?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setReviewBusy(false);
    }
  };

  return (
    <div
      className="absolute inset-y-0 right-0 z-40 w-full sm:w-[440px] max-w-full bg-stone-900/98 backdrop-blur-xl border-l border-white/10 flex flex-col shadow-2xl"
      data-testid="design-studio"
    >
      <div className="px-4 py-3 border-b border-white/10 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-violet-300/90 font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3 h-3" /> Concept AI Design
          </div>
          <h3 className="font-serif text-base text-white truncate">{projectName || "Digital Twin"}</h3>
        </div>
        <button onClick={onClose} className="text-stone-500 hover:text-white shrink-0" data-testid="design-close"><X className="w-5 h-5" /></button>
      </div>

      {/* tabs */}
      <div className="px-4 py-2 border-b border-white/10 flex items-center gap-2">
        <button
          onClick={() => setView("wizard")}
          className={`px-3 py-1.5 rounded-full text-[11px] ${view === "wizard" ? "bg-violet-500 text-white" : "bg-white/5 text-stone-400"}`}
          data-testid="design-tab-wizard"
        >Concept nou</button>
        <button
          onClick={() => setView("history")}
          className={`px-3 py-1.5 rounded-full text-[11px] ${view === "history" ? "bg-violet-500 text-white" : "bg-white/5 text-stone-400"}`}
          data-testid="design-tab-history"
        >Concepte ({concepts.length})</button>
        {onOpenCompare && concepts.length >= 2 && (
          <button
            onClick={onOpenCompare}
            className="ml-auto px-3 py-1.5 rounded-full text-[11px] bg-white/5 text-stone-300 hover:bg-white/10 inline-flex items-center gap-1"
            data-testid="design-open-compare"
          ><GitCompare className="w-3 h-3" /> Compară</button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {busy && (
          <div className="text-center py-10" data-testid="design-generating">
            <Loader2 className="w-6 h-6 animate-spin text-violet-400 mx-auto mb-3" />
            <p className="text-sm text-stone-300">Se creează conceptul{genRender ? " + render AI" : ""}…</p>
            <p className="text-[11px] text-stone-500 mt-1">Poate dura până la ~40s pentru render.</p>
          </div>
        )}

        {!busy && view === "wizard" && (
          <div className="space-y-4" data-testid="design-wizard">
            <div>
              <label className="text-[11px] text-stone-400 mb-1.5 block">Stil de design</label>
              <div className="flex flex-wrap gap-1.5">
                {options.styles.map((s) => (
                  <button
                    key={s}
                    onClick={() => setStyle(s)}
                    className={`px-2.5 py-1.5 rounded-full text-[11px] border transition-colors ${style === s ? "bg-violet-500 text-white border-violet-500" : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"}`}
                    data-testid={`design-style-${s.replace(/\s+/g, "-").toLowerCase()}`}
                  >{s}</button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[11px] text-stone-400 mb-1.5 block">Cameră (opțional)</label>
              <input value={roomName} onChange={(e) => setRoomName(e.target.value)} placeholder="ex: Living, Bucătărie"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white" data-testid="design-room" />
            </div>

            <div>
              <label className="text-[11px] text-stone-400 mb-1.5 block">Buget estimativ ({options.default_currency || "RON"})</label>
              <div className="flex items-center gap-2">
                <input type="number" value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} placeholder="min"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white" data-testid="design-budget-min" />
                <span className="text-stone-500">–</span>
                <input type="number" value={budgetMax} onChange={(e) => setBudgetMax(e.target.value)} placeholder="max"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white" data-testid="design-budget-max" />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-stone-400 mb-1.5 block">Materiale preferate</label>
              <div className="flex flex-wrap gap-1.5">
                {options.materials.map((m) => (
                  <button
                    key={m}
                    onClick={() => toggleMaterial(m)}
                    className={`px-2.5 py-1.5 rounded-full text-[11px] border transition-colors ${materials.includes(m) ? "bg-emerald-500 text-white border-emerald-500" : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"}`}
                    data-testid={`design-material-${m.replace(/\s+/g, "-").toLowerCase()}`}
                  >{m}</button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[11px] text-stone-400 mb-1.5 block">Note / priorități (opțional)</label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="ex: cât mai multă lumină naturală, spațiu de depozitare"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white resize-none" data-testid="design-notes" />
            </div>

            <label className="flex items-center gap-2 text-xs text-stone-300 cursor-pointer" data-testid="design-render-toggle" data-state={genRender ? "checked" : "unchecked"} aria-checked={genRender}>
              <input type="checkbox" checked={genRender} onChange={(e) => setGenRender(e.target.checked)} className="accent-violet-500" />
              Generează și un render vizual AI (Gemini)
            </label>

            {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

            <button
              onClick={submit}
              disabled={!style}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-full bg-violet-500 hover:bg-violet-600 disabled:opacity-40 text-white text-sm font-medium"
              data-testid="design-generate"
            >
              <Wand2 className="w-4 h-4" /> Generează conceptul
            </button>
            <p className="text-[10px] text-stone-500 text-center">
              Concept ORIENTATIV, bazat pe datele proprietății. Bugetul e estimativ. Necesită validare profesională.
            </p>
          </div>
        )}

        {!busy && view === "result" && active && (
          <ConceptResult c={active} onRequestReview={requestReview} reviewBusy={reviewBusy} projectId={projectId} onChanged={reloadConcepts} />
        )}

        {!busy && view === "history" && (
          <div className="space-y-2" data-testid="design-history">
            {concepts.length === 0 ? (
              <p className="text-xs text-stone-500 text-center py-6">Niciun concept încă. Creează primul din „Concept nou".</p>
            ) : concepts.map((c) => (
              <button
                key={c.id}
                onClick={() => { setActive(c); setView("result"); }}
                className="w-full text-left rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] p-3 flex items-center gap-3"
                data-testid={`design-history-${c.id}`}
              >
                {c.render_url ? (
                  <img src={`${process.env.REACT_APP_BACKEND_URL}${c.render_url}`} alt="" className="w-12 h-12 rounded-lg object-cover shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0"><Palette className="w-5 h-5 text-violet-300" /></div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-white truncate">{c.concept?.title || c.inputs?.style || "Concept"}</div>
                  <div className="text-[10px] text-stone-500">{c.inputs?.style} · {new Date(c.created_at).toLocaleDateString("ro-RO")} · {c.status}</div>
                </div>
                <ChevronRight className="w-4 h-4 text-stone-600" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DesignConceptStudio;
