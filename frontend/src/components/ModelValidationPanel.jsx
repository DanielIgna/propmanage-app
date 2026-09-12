// Professional Validation — inferred → in_review → verified. Explicit professional action.
// Preserves validation history (who/when/what/result). Never auto-verifies.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  X, Loader2, ShieldCheck, ShieldQuestion, Clock, Check, Ban, History, AlertTriangle, FileBox,
} from "lucide-react";
import { API } from "../pages/DashShared";

const trust = (m) => {
  const rev = m.review_state || "none";
  if (m.confidence === "verified" || rev === "verified")
    return { label: "Verificat profesional", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25", Icon: ShieldCheck };
  if (rev === "in_review")
    return { label: "În validare", cls: "bg-blue-500/15 text-blue-300 border-blue-500/25", Icon: Clock };
  if (rev === "rejected")
    return { label: "Respins (rămâne orientativ)", cls: "bg-red-500/15 text-red-300 border-red-500/25", Icon: Ban };
  if (m.confidence === "documented")
    return { label: "Documentat", cls: "bg-stone-500/15 text-stone-300 border-stone-500/25", Icon: FileBox };
  return { label: "Orientativ AI · neverificat", cls: "bg-amber-500/15 text-amber-300 border-amber-500/25", Icon: AlertTriangle };
};

const HistoryList = ({ modelId }) => {
  const [items, setItems] = useState(null);
  useEffect(() => {
    axios.get(`${API}/digital-twin/models/${modelId}/validation-history`)
      .then((r) => setItems(r.data.items || [])).catch(() => setItems([]));
  }, [modelId]);
  if (items === null) return <div className="text-[11px] text-stone-500 py-2"><Loader2 className="w-3 h-3 animate-spin inline mr-1" />Se încarcă istoricul…</div>;
  if (!items.length) return <div className="text-[11px] text-stone-500 py-2">Fără istoric de validare.</div>;
  return (
    <div className="space-y-1 pt-2" data-testid={`validation-history-${modelId}`}>
      {items.map((v, i) => (
        <div key={v.id} className="text-[11px] text-stone-400 flex items-start gap-1.5" data-testid={`validation-history-entry-${i}`}>
          <span className="text-stone-600 mt-0.5">•</span>
          <span>
            <strong className="text-stone-300">{v.action === "confirm" ? "Validat" : v.action === "reject" ? "Respins" : "Trimis la validare"}</strong>
            {" "}de {v.actor_name} ({v.actor_role}) · {new Date(v.ts).toLocaleString("ro-RO")}
            {v.note ? <span className="italic text-stone-500"> — „{v.note}"</span> : null}
          </span>
        </div>
      ))}
    </div>
  );
};

const ModelRow = ({ m, isProfessional, onChanged }) => {
  const [busy, setBusy] = useState(null); // 'review' | 'confirm' | 'reject'
  const [showHist, setShowHist] = useState(false);
  const [err, setErr] = useState(null);
  const t = trust(m);
  const rev = m.review_state || "none";
  const isInferred = m.confidence === "inferred";
  const canRequest = isInferred && rev !== "in_review" && rev !== "verified";
  const canValidate = isProfessional && (rev === "in_review" || isInferred) && m.confidence !== "verified";

  const act = async (kind) => {
    setBusy(kind); setErr(null);
    try {
      if (kind === "review") await axios.post(`${API}/digital-twin/models/${m.id}/request-review`, {});
      else await axios.post(`${API}/digital-twin/models/${m.id}/validate`, { action: kind });
      onChanged?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 space-y-2" data-testid={`validation-model-${m.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs text-white truncate">{m.filename || m.stored_as}</div>
          <div className="text-[10px] text-stone-500">{m.source} · {new Date(m.uploaded_at).toLocaleDateString("ro-RO")}</div>
        </div>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${t.cls}`} data-testid={`validation-badge-${m.id}`}>
          <t.Icon className="w-3 h-3" /> {t.label}
        </span>
      </div>

      {(canRequest || canValidate) && (
        <div className="flex flex-wrap gap-1.5">
          {canRequest && (
            <button onClick={() => act("review")} disabled={!!busy}
              className="px-2.5 py-1.5 rounded-full text-[11px] bg-blue-500/15 text-blue-200 hover:bg-blue-500/25 disabled:opacity-50 flex items-center gap-1"
              data-testid={`validation-request-${m.id}`}>
              {busy === "review" ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldQuestion className="w-3 h-3" />} Trimite la validare
            </button>
          )}
          {canValidate && (
            <>
              <button onClick={() => act("confirm")} disabled={!!busy}
                className="px-2.5 py-1.5 rounded-full text-[11px] bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-50 flex items-center gap-1"
                data-testid={`validation-confirm-${m.id}`}>
                {busy === "confirm" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />} Validează
              </button>
              <button onClick={() => act("reject")} disabled={!!busy}
                className="px-2.5 py-1.5 rounded-full text-[11px] bg-red-500/15 text-red-200 hover:bg-red-500/25 disabled:opacity-50 flex items-center gap-1"
                data-testid={`validation-reject-${m.id}`}>
                {busy === "reject" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Ban className="w-3 h-3" />} Respinge
              </button>
            </>
          )}
        </div>
      )}
      {err && <div className="text-[11px] text-red-400">{err}</div>}

      <button onClick={() => setShowHist((s) => !s)} className="text-[10px] text-stone-500 hover:text-stone-300 flex items-center gap-1" data-testid={`validation-history-toggle-${m.id}`}>
        <History className="w-3 h-3" /> {showHist ? "Ascunde istoricul" : "Istoric validare"}
      </button>
      {showHist && <HistoryList modelId={m.id} />}
    </div>
  );
};

export const ModelValidationPanel = ({ projectId, projectName, isProfessional, onClose, onChanged }) => {
  const [models, setModels] = useState(null);

  const load = () => {
    axios.get(`${API}/digital-twin/projects/${projectId}/models`)
      .then((r) => setModels((r.data.items || []).filter((m) => m.kind === "model")))
      .catch(() => setModels([]));
  };
  useEffect(() => { load(); }, [projectId]);

  const handleChanged = () => { load(); onChanged?.(); };

  return (
    <div className="absolute inset-y-0 right-0 z-40 w-full sm:w-[420px] max-w-full bg-stone-900/98 backdrop-blur-xl border-l border-white/10 flex flex-col shadow-2xl" data-testid="validation-panel">
      <div className="px-4 py-3 border-b border-white/10 flex items-start justify-between gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-300/90 font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3" /> Validare profesională
          </div>
          <h3 className="font-serif text-base text-white truncate">{projectName || "Digital Twin"}</h3>
        </div>
        <button onClick={onClose} className="text-stone-500 hover:text-white" data-testid="validation-close"><X className="w-5 h-5" /></button>
      </div>
      <div className="px-4 py-2 bg-emerald-500/5 border-b border-emerald-500/10">
        <p className="text-[10px] text-stone-400 leading-relaxed">
          Flux: <strong className="text-amber-300">Orientativ AI</strong> → <strong className="text-blue-300">În validare</strong> → <strong className="text-emerald-300">Verificat profesional</strong>. Verificarea cere acțiune explicită a unui profesionist. Nimic nu devine „verificat" automat.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {models === null ? (
          <div className="text-center py-8 text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă modelele…</div>
        ) : models.length === 0 ? (
          <div className="text-center py-8 text-sm text-stone-500">Niciun model 3D în acest proiect.</div>
        ) : (
          models.map((m) => <ModelRow key={m.id} m={m} isProfessional={isProfessional} onChanged={handleChanged} />)
        )}
      </div>
    </div>
  );
};

export default ModelValidationPanel;
