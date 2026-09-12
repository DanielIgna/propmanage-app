// Digital Twin — Next Stage:
//  A) Side-by-side comparison of 2 AI design concepts.
//  B) "Cere ofertă" from a PROFESSIONALLY VERIFIED concept.
//  D) Real materials with indicative prices (City Partners catalog + market fallback).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  X, Loader2, Palette, Coins, ShieldCheck, AlertTriangle, GitCompare,
  ShoppingBag, FileText, CheckCircle2, Image as ImageIcon, Star,
} from "lucide-react";
import { API } from "../pages/DashShared";

const IMG = (u) => `${process.env.REACT_APP_BACKEND_URL}${u}`;

const StatusBadge = ({ status }) => {
  const map = {
    inferred: { t: "Orientativ AI · neverificat", c: "bg-amber-500/15 text-amber-300 border-amber-500/25", Icon: AlertTriangle },
    in_review: { t: "În validare", c: "bg-blue-500/15 text-blue-300 border-blue-500/25", Icon: ShieldCheck },
    verified: { t: "Verificat profesional", c: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25", Icon: ShieldCheck },
    rejected: { t: "Respins (rămâne orientativ)", c: "bg-red-500/15 text-red-300 border-red-500/25", Icon: AlertTriangle },
  };
  const s = map[status] || map.inferred;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${s.c}`} data-testid="concept-status-badge">
      <s.Icon className="w-3 h-3" /> {s.t}
    </span>
  );
};

// ── D) Real materials + indicative price (partner product OR market fallback) ──
export const ConceptMaterials = ({ conceptId }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!conceptId) return;
    axios.get(`${API}/digital-twin/design-concepts/${conceptId}/materials`)
      .then((r) => setData(r.data)).catch(() => setData({ items: [] }));
  }, [conceptId]);

  if (!data) return <div className="text-[11px] text-stone-500 py-2"><Loader2 className="w-3 h-3 animate-spin inline mr-1" />Se încarcă materialele…</div>;
  if (!data.items?.length) return null;

  return (
    <div data-testid={`concept-materials-${conceptId}`}>
      <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1.5 flex items-center gap-1.5">
        <ShoppingBag className="w-3 h-3" /> Materiale · preț orientativ
      </div>
      <div className="space-y-1.5">
        {data.items.map((it, i) => (
          <div key={i} className="rounded-lg bg-white/[0.03] border border-white/10 p-2" data-testid={`material-row-${i}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs text-white truncate">{it.material}</div>
                {it.surface && <div className="text-[10px] text-stone-500">{it.surface}</div>}
              </div>
              {it.pricing ? (
                <div className="text-right shrink-0">
                  <div className="text-[11px] font-mono text-emerald-300" data-testid={`material-price-${i}`}>
                    {(it.pricing.price_low ?? 0).toLocaleString()}–{(it.pricing.price_high ?? 0).toLocaleString()}
                    <span className="text-stone-500"> {data.currency}/{it.pricing.unit}</span>
                  </div>
                  <div className="text-[9px] text-stone-500">
                    {it.pricing_source === "city_partner"
                      ? `Produs partener${it.pricing.partner ? " · " + it.pricing.partner : ""}`
                      : "Preț orientativ piață"}
                  </div>
                </div>
              ) : (
                <div className="text-[10px] text-stone-500 shrink-0" data-testid={`material-noprice-${i}`}>preț orientativ indisponibil</div>
              )}
            </div>
            {it.pricing?.url && (
              <a href={it.pricing.url} target="_blank" rel="noreferrer" className="text-[10px] text-violet-300 underline mt-1 inline-block">Vezi produs partener →</a>
            )}
          </div>
        ))}
      </div>
      {data.disclaimer && <p className="text-[9px] text-amber-400/80 mt-1.5 leading-relaxed">{data.disclaimer}</p>}
    </div>
  );
};

// ── Winner pick — mark a concept as preferred (Alegere câștigătoare) ──
export const PreferButton = ({ concept, projectId, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const preferred = !!concept?.preferred;
  const toggle = async () => {
    if (!projectId) return;
    setBusy(true);
    try {
      await axios.post(`${API}/digital-twin/projects/${projectId}/design-concepts/${concept.id}/prefer`, { preferred: !preferred });
      toast.success(!preferred ? "Concept marcat ca preferat." : "Preferință eliminată.");
      onChanged?.();
    } catch (e) {
      toast.error("Nu am putut marca preferatul.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      onClick={toggle}
      disabled={busy}
      data-testid="prefer-btn"
      className={`w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-full border transition-colors ${preferred ? "bg-amber-500/20 border-amber-500/40 text-amber-200" : "bg-white/5 border-white/10 text-stone-300 hover:bg-white/10"}`}
    >
      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Star className={`w-3.5 h-3.5 ${preferred ? "fill-amber-300 text-amber-300" : ""}`} />}
      {preferred ? "Preferat" : "Alege ca preferat"}
    </button>
  );
};

// ── B) Request an offer from a verified concept (explicit client confirmation) ──
export const RequestOfferButton = ({ concept, projectId, onDone }) => {
  const [step, setStep] = useState("idle"); // idle | confirm | busy | done
  const [msg, setMsg] = useState(null);
  const verified = concept?.status === "verified" || concept?.confidence === "verified";
  const already = !!concept?.offer_request_id;
  const combined = !!projectId; // "Alege și cere ofertă" (prefer + offer)

  if (!verified) {
    return (
      <div className="text-[10px] text-stone-500 bg-white/[0.03] border border-white/10 rounded-lg p-2" data-testid="offer-locked">
        Oferta se poate cere doar dintr-un concept <strong className="text-stone-300">validat profesional</strong>.
      </div>
    );
  }

  const send = async () => {
    setStep("busy"); setMsg(null);
    try {
      if (combined) {
        try { await axios.post(`${API}/digital-twin/projects/${projectId}/design-concepts/${concept.id}/prefer`, { preferred: true }); } catch (_) { /* prefer best-effort */ }
      }
      const { data } = await axios.post(`${API}/digital-twin/design-concepts/${concept.id}/request-offer`, { confirm: true });
      setStep("done");
      setMsg(data.message);
      toast.success(data.already_exists ? "Există deja o cerere de ofertă activă." : "Cerere de ofertă trimisă către specialiștii verificați.");
      onDone?.(data);
    } catch (e) {
      setStep("idle");
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Nu am putut trimite cererea de ofertă.");
    }
  };

  if (step === "done" || already) {
    return (
      <div className="text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2 flex items-center gap-1.5" data-testid="offer-requested">
        <CheckCircle2 className="w-3.5 h-3.5" /> {msg || "Ofertă cerută. Specialiștii verificați au fost notificați."}
      </div>
    );
  }

  if (step === "confirm") {
    return (
      <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-2.5 space-y-2" data-testid="offer-confirm">
        <p className="text-[11px] text-stone-300 leading-relaxed">
          {combined
            ? "Marchez acest concept ca preferat și trimit o cerere de ofertă către specialiștii verificați (proprietate + buget + materiale). Confirmi?"
            : "Trimit o cerere de ofertă către specialiștii verificați, cu proprietatea, bugetul și materialele acestui concept validat. Confirmi?"}
        </p>
        <div className="flex gap-2">
          <button onClick={send} className="flex-1 px-3 py-1.5 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white text-[11px] font-medium" data-testid="offer-confirm-yes">Da, trimite cererea</button>
          <button onClick={() => setStep("idle")} className="px-3 py-1.5 rounded-full bg-white/5 text-stone-300 text-[11px]" data-testid="offer-confirm-no">Anulează</button>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={() => setStep("confirm")}
      disabled={step === "busy"}
      className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-full bg-emerald-500 hover:bg-emerald-600 text-white font-medium disabled:opacity-50"
      data-testid="request-offer-btn"
    >
      {step === "busy" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (combined ? <Star className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />)}
      {combined ? "Alege și cere ofertă" : "Cere ofertă de la specialiști verificați"}
    </button>
  );
};

// ── A) One comparison column ──
const ConceptColumn = ({ c, projectId, onChanged }) => {
  if (!c) return <div className="text-xs text-stone-500 text-center py-8">Selectează un concept.</div>;
  const concept = c.concept || {};
  const budget = concept.budget || {};
  const status = c.status || "inferred";
  return (
    <div className="space-y-3" data-testid={`compare-col-${c.id}`}>
      {c.render_url ? (
        <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30">
          <img src={IMG(c.render_url)} alt="Render concept" className="w-full h-36 object-cover" />
        </div>
      ) : (
        <div className="rounded-xl h-36 border border-white/10 bg-violet-500/10 flex items-center justify-center">
          <ImageIcon className="w-6 h-6 text-violet-300/60" />
        </div>
      )}

      <div>
        <h4 className="font-serif text-base text-white leading-tight">{concept.title || c.inputs?.style || "Concept"}</h4>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <StatusBadge status={status} />
          {c.preferred && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/30" data-testid={`preferred-badge-${c.id}`}>
              <Star className="w-3 h-3 fill-amber-300" /> Preferat
            </span>
          )}
          {c.inputs?.style && <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-stone-400 border border-white/10">{c.inputs.style}</span>}
        </div>
      </div>

      {concept.summary && <p className="text-[11px] text-stone-400 leading-relaxed">{concept.summary}</p>}

      {(concept.palette || []).length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1.5 flex items-center gap-1.5"><Palette className="w-3 h-3" /> Paletă</div>
          <div className="flex flex-wrap gap-1.5">
            {concept.palette.map((p, i) => (
              <span key={i} className="w-6 h-6 rounded-md border border-white/20" style={{ backgroundColor: p.hex }} title={p.name} />
            ))}
          </div>
        </div>
      )}

      {(budget.total_low || budget.total_high) && (
        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-2.5">
          <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold mb-1 flex items-center gap-1.5"><Coins className="w-3 h-3" /> Buget estimativ</div>
          <div className="text-sm font-mono text-white" data-testid={`compare-budget-${c.id}`}>
            {(budget.total_low ?? 0).toLocaleString()}–{(budget.total_high ?? 0).toLocaleString()} {budget.currency || "RON"}
          </div>
          <p className="text-[9px] text-amber-400/80 mt-0.5">Estimare orientativă, NU preț garantat.</p>
        </div>
      )}

      <ConceptMaterials conceptId={c.id} />

      <div className="space-y-2">
        <PreferButton concept={c} projectId={projectId} onChanged={onChanged} />
        <RequestOfferButton concept={c} projectId={projectId} onDone={onChanged} />
      </div>
    </div>
  );
};

// ── A) Comparison overlay ──
export const ConceptComparison = ({ projectId, projectName, onClose, onChanged }) => {
  const [concepts, setConcepts] = useState(null);
  const [aId, setAId] = useState("");
  const [bId, setBId] = useState("");

  const load = () => {
    axios.get(`${API}/digital-twin/projects/${projectId}/design-concepts`)
      .then((r) => {
        const items = r.data.items || [];
        setConcepts(items);
        if (items[0]) setAId((v) => v || items[0].id);
        if (items[1]) setBId((v) => v || items[1].id);
      })
      .catch(() => setConcepts([]));
  };
  useEffect(() => { load(); }, [projectId]); // eslint-disable-line

  const A = (concepts || []).find((c) => c.id === aId);
  const B = (concepts || []).find((c) => c.id === bId);

  const handleChanged = () => { load(); onChanged?.(); };

  const Selector = ({ value, onChange, testid, exclude }) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full bg-stone-800 border border-white/10 rounded-lg px-2.5 py-2 text-xs text-white"
      data-testid={testid}
    >
      <option value="">— alege concept —</option>
      {(concepts || []).map((c) => (
        <option key={c.id} value={c.id} disabled={c.id === exclude}>
          {(c.concept?.title || c.inputs?.style || "Concept")} · {c.status}
        </option>
      ))}
    </select>
  );

  return (
    <div className="absolute inset-0 z-50 bg-stone-950/97 backdrop-blur-xl flex flex-col" data-testid="concept-comparison">
      <div className="px-4 py-3 border-b border-white/10 flex items-start justify-between gap-2 shrink-0">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-violet-300/90 font-semibold flex items-center gap-1.5">
            <GitCompare className="w-3 h-3" /> Comparație concepte AI
          </div>
          <h3 className="font-serif text-base text-white truncate">{projectName || "Digital Twin"}</h3>
        </div>
        <button onClick={onClose} className="text-stone-500 hover:text-white shrink-0" data-testid="compare-close"><X className="w-5 h-5" /></button>
      </div>

      {concepts === null ? (
        <div className="flex-1 flex items-center justify-center text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin mr-2" />Se încarcă…</div>
      ) : concepts.length < 2 ? (
        <div className="flex-1 flex items-center justify-center px-6 text-center" data-testid="compare-need-more">
          <p className="text-sm text-stone-400 max-w-xs">Ai nevoie de cel puțin <strong className="text-white">2 concepte</strong> pentru comparație. Generează mai multe din „Concept AI Design".</p>
        </div>
      ) : (
        <>
          <div className="px-4 py-3 border-b border-white/10 grid grid-cols-2 gap-3 shrink-0">
            <Selector value={aId} onChange={setAId} testid="compare-select-a" exclude={bId} />
            <Selector value={bId} onChange={setBId} testid="compare-select-b" exclude={aId} />
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto">
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4"><ConceptColumn c={A} projectId={projectId} onChanged={handleChanged} /></div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4"><ConceptColumn c={B} projectId={projectId} onChanged={handleChanged} /></div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ConceptComparison;
