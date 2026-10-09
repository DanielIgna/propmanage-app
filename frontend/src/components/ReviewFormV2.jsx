// Sprint B — Multi-dimensional Review Form (Client → Specialist OR Specialist → Client)
// 8 dims for C→S, 5 dims for S→C. Each dim is 1-5 stars + optional global comment.
// Implements double-blind window awareness.
import React, { useState } from "react";
import axios from "axios";
import { Star, Loader2, X, CheckCircle2, Eye, EyeOff } from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;

const DIMENSIONS_C2S = [
  { key: "timeliness", label: "Respectarea termenelor", desc: "A respectat data agreată?" },
  { key: "quality", label: "Calitatea execuției", desc: "Lucrarea finalizată e ok?" },
  { key: "offer_adherence", label: "Respectarea ofertei", desc: "S-a încadrat în prețul stabilit?" },
  { key: "communication", label: "Comunicare", desc: "Răspunde la mesaje? Clar?" },
  { key: "professionalism", label: "Profesionalism", desc: "Atitudine ok pe parcursul lucrării?" },
  { key: "cleanliness", label: "Curățenie și organizare", desc: "A lăsat în ordine?" },
  { key: "documentation", label: "Respectarea documentației", desc: "A întocmit acte/fotografii dacă era nevoie?" },
  { key: "recommendation", label: "Recomandare generală", desc: "Ai recomanda specialistul altor clienți?" },
];

const DIMENSIONS_S2C = [
  { key: "seriousness", label: "Seriozitate", desc: "Și-a respectat angajamentele?" },
  { key: "responsiveness", label: "Răspuns la solicitări", desc: "Răspunde rapid la mesaje?" },
  { key: "commitment", label: "Respectarea înțelegerilor", desc: "Înțelegerile au fost respectate?" },
  { key: "punctuality", label: "Punctualitate", desc: "Pe vizite, programări?" },
  { key: "collaboration", label: "Colaborare", desc: "Disponibilitate, atitudine?" },
];

const StarRow = ({ value, onChange, testid }) => (
  <div className="flex items-center gap-1" data-testid={testid}>
    {[1, 2, 3, 4, 5].map(n => (
      <button key={n} type="button" onClick={() => onChange(value === n ? null : n)}
        className="p-0.5 hover:scale-110 transition" data-testid={`${testid}-star-${n}`}>
        <Star className={`w-5 h-5 ${value && n <= value ? "fill-amber-400 text-amber-400" : "text-stone-600 hover:text-stone-400"}`} />
      </button>
    ))}
    {value !== null && value !== undefined && (
      <button type="button" onClick={() => onChange(null)} className="text-[10px] text-stone-500 hover:text-stone-300 ml-1" title="Curăță">×</button>
    )}
  </div>
);


export const ReviewFormV2 = ({ requestId, direction = "client_to_specialist", onClose, onSubmit }) => {
  const dimensions = direction === "client_to_specialist" ? DIMENSIONS_C2S : DIMENSIONS_S2C;
  const endpoint = direction === "client_to_specialist" ? "review-v2" : "review-client-v2";
  const minDims = direction === "client_to_specialist" ? 3 : 2;
  const [scores, setScores] = useState({});
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const scored = Object.values(scores).filter(v => v != null).length;
  const canSubmit = scored >= minDims && !submitting;

  const submit = async () => {
    setSubmitting(true); setError("");
    try {
      const cleanScores = Object.fromEntries(Object.entries(scores).filter(([_, v]) => v != null));
      const { data } = await axios.post(`${API}/api/requests/${requestId}/${endpoint}`, { scores: cleanScores, comment });
      setResult(data);
      onSubmit && onSubmit(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la trimiterea recenziei");
    } finally { setSubmitting(false); }
  };

  if (result) {
    return (
      <div className="glass-strong rounded-3xl max-w-lg w-full p-8 text-center" data-testid="review-v2-success">
        <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-3" />
        <h3 className="font-serif text-2xl mb-2">Mulțumim pentru recenzie!</h3>
        <p className="text-sm text-stone-400 mb-4">Scor mediu: <strong className="text-[#d4ff3a]">{result.dimension_avg}/5</strong></p>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-200 mb-5">
          {result.mutual_reveal ? (
            <div className="flex items-center gap-2 justify-center"><Eye className="w-4 h-4" /> Ambele recenzii au fost publicate (cealaltă parte a trimis și ea).</div>
          ) : (
            <div className="flex items-center gap-2 justify-center"><EyeOff className="w-4 h-4" /> Recenzia ta este ascunsă <strong>7 zile</strong> (sau până trimite și cealaltă parte). Anti-revenge protection.</div>
          )}
        </div>
        <button onClick={onClose} className="btn-accent px-6 py-2.5 rounded-xl text-sm font-medium" data-testid="review-v2-done">Închide</button>
      </div>
    );
  }

  return (
    <div className="glass-strong rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" data-testid="review-form-v2">
      <div className="p-6 border-b border-white/10 flex items-center justify-between sticky top-0 bg-[#0a0a0b]/95 backdrop-blur-xl">
        <div>
          <h3 className="font-serif text-2xl">{direction === "client_to_specialist" ? "Evaluează specialistul" : "Evaluează clientul"}</h3>
          <p className="text-xs text-stone-400 mt-1">Punctează cel puțin <strong>{minDims}</strong> dimensiuni. Recenzia rămâne ascunsă 7 zile (double-blind).</p>
        </div>
        <button onClick={onClose} className="text-stone-400 hover:text-stone-200" data-testid="review-v2-close"><X className="w-5 h-5" /></button>
      </div>

      <div className="p-6 space-y-3">
        {dimensions.map(d => (
          <div key={d.key} className="flex items-start justify-between gap-3 py-2.5 border-b border-white/5 last:border-0" data-testid={`review-dim-${d.key}`}>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-stone-200">{d.label}</div>
              <div className="text-[11px] text-stone-500">{d.desc}</div>
            </div>
            <StarRow value={scores[d.key]} onChange={v => setScores(s => ({ ...s, [d.key]: v }))} testid={`review-${d.key}`} />
          </div>
        ))}

        <div className="pt-2">
          <label className="text-xs uppercase tracking-wider text-stone-500 mb-1.5 block">Comentariu (opțional, max 2000 caractere)</label>
          <textarea value={comment} onChange={e => setComment(e.target.value)} rows={3} maxLength={2000}
            placeholder={direction === "client_to_specialist" ? "Cum a fost colaborarea cu specialistul?" : "Cum a fost colaborarea cu clientul?"}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-[#d4ff3a]/50"
            data-testid="review-comment" />
          <div className="text-[10px] text-stone-500 mt-1 text-right">{comment.length}/2000</div>
        </div>

        {error && <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2" data-testid="review-v2-error">{error}</div>}

        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-stone-500">
            Dimensiuni evaluate: <strong className={scored >= minDims ? "text-emerald-300" : "text-amber-300"}>{scored}</strong> / {dimensions.length}
          </div>
          <button onClick={submit} disabled={!canSubmit} className="btn-accent px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2" data-testid="review-v2-submit">
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Star className="w-4 h-4" />} Trimite recenzia
          </button>
        </div>
      </div>
    </div>
  );
};


export const ReviewFormV2Modal = ({ requestId, direction, onClose, onSubmit }) => (
  <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
    <div onClick={e => e.stopPropagation()}>
      <ReviewFormV2 requestId={requestId} direction={direction} onClose={onClose} onSubmit={onSubmit} />
    </div>
  </div>
);

export default ReviewFormV2Modal;
