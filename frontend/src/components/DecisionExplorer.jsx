// DecisionExplorer — AIB-007 · Decision Intelligence Engine (tab în /admin/ai-brain).
// Decizii generate cu scoruri, factori, reguli aplicate, explicații AI și simulări de impact.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Scale, Loader2, ScanEye, AlertTriangle, FlaskConical, MessageCircleQuestion, ListOrdered,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const FACTOR_LABELS = {
  urgency: "Urgență", impact: "Impact", unblocking: "Deblocare",
  readiness: "Pregătire", progress: "Progres", risk_of_inaction: "Risc inacțiune",
};

const FactorBars = ({ factors }) => (
  <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2" data-testid="de-factors">
    {Object.entries(factors || {}).map(([k, v]) => (
      <div key={k} className="flex items-center gap-2">
        <span className="text-[10px] text-stone-500 w-24 shrink-0">{FACTOR_LABELS[k] || k}</span>
        <div className="flex-1 h-1.5 bg-stone-800 rounded-full overflow-hidden">
          <div className="h-full bg-[#d4ff3a]" style={{ width: `${Math.round(v * 100)}%` }} />
        </div>
        <span className="text-[10px] text-stone-400 w-8 text-right">{Math.round(v * 100)}</span>
      </div>
    ))}
  </div>
);

const ScoreBadge = ({ score }) => (
  <span className={`text-[13px] font-black px-2 py-0.5 rounded-lg border ${
    score >= 60 ? "bg-[#d4ff3a]/15 text-[#d4ff3a] border-[#d4ff3a]/40"
    : score >= 35 ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
    : "bg-stone-800 text-stone-400 border-stone-700"}`}>
    {score}
  </span>
);

export const DecisionExplorer = () => {
  const [email, setEmail] = useState("client@propmanage.io");
  const [items, setItems] = useState(null);
  const [role, setRole] = useState("");
  const [sel, setSel] = useState(null);
  const [sim, setSim] = useState(null);
  const [expl, setExpl] = useState(null);
  const [rules, setRules] = useState(null);
  const [prios, setPrios] = useState([]);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [showRules, setShowRules] = useState(false);

  useEffect(() => {
    ax.get("/api/admin/ai-brain/decisions/priorities").then(r => setPrios(r.data.items)).catch(() => {});
    ax.get("/api/admin/ai-brain/decisions/rules").then(r => setRules(r.data)).catch(() => {});
  }, []);

  const inspect = async (e) => {
    e?.preventDefault(); setBusy(true); setSel(null); setSim(null); setExpl(null);
    try {
      const { data } = await ax.get("/api/admin/ai-brain/decisions/inspect", { params: { email } });
      setItems(data.items); setRole(data.role);
    } catch (ex) { setItems([]); setRole(String(ex?.response?.data?.detail || ex.message)); }
    finally { setBusy(false); }
  };

  const simulate = async (d) => {
    setBusyAction("sim"); setSim(null);
    try {
      // simularea rulează pe snapshot-ul utilizatorului inspectat — refolosim inspecția + POST ca admin nu are snapshot-ul lui
      const { data } = await ax.post("/api/ai-brain/decisions/simulate", { decision_id: d.id, email });
      setSim(data);
    } catch { setSim({ found: false }); } finally { setBusyAction(""); }
  };

  const explain = async (d) => {
    setBusyAction("expl"); setExpl(null);
    try {
      const { data } = await ax.post("/api/ai-brain/decisions/explain", { decision_id: d.id, email });
      setExpl(data);
    } catch { setExpl(null); } finally { setBusyAction(""); }
  };

  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="decision-explorer">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Scale className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Decision Explorer — AIB-007 · Decision Intelligence Engine</div>
        <div className="flex-1" />
        <button onClick={() => setShowRules(!showRules)}
          className="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-stone-800 text-stone-300 border border-stone-700 flex items-center gap-1"
          data-testid="de-rules-btn">
          <ListOrdered className="w-3 h-3" /> Reguli & ponderi
        </button>
      </div>

      {showRules && rules && (
        <div className="mb-4 rounded-xl border border-stone-800 bg-stone-900/50 p-3" data-testid="de-rules">
          <div className="flex flex-wrap gap-1.5 mb-2">
            {Object.entries(rules.weights).map(([k, w]) => (
              <span key={k} className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/25">
                {FACTOR_LABELS[k] || k}: {Math.round(w * 100)}%
              </span>
            ))}
          </div>
          {rules.generators.map(g => (
            <div key={g.kind} className="text-[11px] text-stone-400 mb-0.5"><b className="text-stone-300">{g.kind}</b> — {g.rule}</div>
          ))}
        </div>
      )}

      {prios.length > 0 && (
        <div className="mb-4" data-testid="de-priorities">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5">Priority Engine — prioritățile platformei acum</div>
          <div className="space-y-1">
            {prios.slice(0, 5).map((p, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-stone-300 bg-stone-900/50 border border-stone-800 rounded-lg px-2.5 py-1.5">
                <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
                <span className="flex-1">{p.title} <span className="text-stone-500">— {p.detail}</span></span>
                <span className="text-[10px] font-black text-rose-300">{p.severity}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={inspect} className="flex gap-2 mb-3">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email utilizator"
          className="flex-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white" data-testid="de-email-input" />
        <button disabled={busy} className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="de-inspect-btn">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ScanEye className="w-3.5 h-3.5" />} Generează deciziile
        </button>
      </form>

      {items && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <div className="lg:col-span-2 space-y-1.5 max-h-[460px] overflow-auto" data-testid="de-list">
            {items.length === 0 && <div className="text-xs text-stone-500 p-2">Nicio decizie generată ({role}).</div>}
            {items.map(d => (
              <button key={d.id} onClick={() => { setSel(d); setSim(null); setExpl(null); }}
                className={`w-full text-left rounded-xl border p-2.5 transition-colors ${sel?.id === d.id ? "border-[#d4ff3a]/50 bg-stone-900/70" : "border-stone-800 bg-stone-900/40 hover:border-stone-700"}`}
                data-testid={`de-item-${d.id}`}>
                <div className="flex items-start gap-2">
                  <ScoreBadge score={d.score} />
                  <span className="text-[12px] font-bold text-white flex-1">{d.title}</span>
                </div>
                <div className="text-[10px] text-stone-500 mt-1">{d.kind}{d.process_name ? ` · ${d.process_name}` : ""}</div>
              </button>
            ))}
          </div>
          <div className="lg:col-span-3 rounded-xl border border-stone-800 bg-stone-900/40 p-3.5" data-testid="de-detail">
            {!sel ? (
              <div className="text-xs text-stone-500">Selectează o decizie pentru factori, explicație și simulare.</div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ScoreBadge score={sel.score} />
                  <span className="text-sm font-bold text-white flex-1">{sel.title}</span>
                  {sel.confidence != null && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-violet-500/10 text-violet-300 border border-violet-500/30"
                      data-testid="de-confidence">Încredere {sel.confidence}%</span>
                  )}
                </div>
                {sel.adaptive?.reasons?.length > 0 && (
                  <div className="text-[11px] text-violet-200/90 bg-violet-500/10 border border-violet-500/25 rounded-lg px-2.5 py-1.5 space-y-0.5" data-testid="de-adaptive">
                    <div className="text-[9px] font-black uppercase text-violet-300">
                      Recalibrare adaptivă: {sel.adaptive.adjustment > 0 ? "+" : ""}{sel.adaptive.adjustment}p (bază {sel.base_score})
                    </div>
                    {sel.adaptive.reasons.map((r, i) => <div key={i}>· {r}</div>)}
                  </div>
                )}
                {sel.confidence_factors?.length > 0 && (
                  <div className="text-[10px] text-stone-500 space-y-0.5" data-testid="de-confidence-factors">
                    {sel.confidence_factors.map((f, i) => <div key={i}>◦ {f}</div>)}
                  </div>
                )}
                <FactorBars factors={sel.factors} />
                <div className="text-[11px] text-stone-300 space-y-1" data-testid="de-reasons">
                  {(sel.reasons || []).map((r, i) => <div key={i}>· {r}</div>)}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                  <div className="bg-stone-900/60 border border-stone-800 rounded-lg p-2"><b className="text-stone-400 block text-[10px] uppercase">Rezolvă</b><span className="text-stone-300">{sel.resolves}</span></div>
                  <div className="bg-stone-900/60 border border-stone-800 rounded-lg p-2"><b className="text-stone-400 block text-[10px] uppercase">Risc evitat</b><span className="text-stone-300">{sel.avoids_risk}</span></div>
                  <div className="bg-stone-900/60 border border-stone-800 rounded-lg p-2"><b className="text-stone-400 block text-[10px] uppercase">Impact</b><span className="text-stone-300">{sel.produces_impact}</span></div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => simulate(sel)} disabled={busyAction === "sim"}
                    className="px-3 py-1.5 text-[11px] rounded-lg bg-sky-500/15 text-sky-300 border border-sky-500/30 font-bold flex items-center gap-1.5" data-testid="de-simulate-btn">
                    {busyAction === "sim" ? <Loader2 className="w-3 h-3 animate-spin" /> : <FlaskConical className="w-3 h-3" />} Simulează impactul
                  </button>
                  <button onClick={() => explain(sel)} disabled={busyAction === "expl"}
                    className="px-3 py-1.5 text-[11px] rounded-lg bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/30 font-bold flex items-center gap-1.5" data-testid="de-explain-btn">
                    {busyAction === "expl" ? <Loader2 className="w-3 h-3 animate-spin" /> : <MessageCircleQuestion className="w-3 h-3" />} De ce această decizie?
                  </button>
                </div>
                {sim && sim.found && (
                  <div className="rounded-lg border border-sky-500/25 bg-sky-500/5 p-2.5 text-[11px] text-stone-300 space-y-1" data-testid="de-sim-result">
                    <div className="text-[10px] font-black uppercase text-sky-300">Simulare (nimic nu a fost executat)</div>
                    <div>Module afectate: <b>{sim.affected_modules.join(", ") || "—"}</b></div>
                    <div>Procese afectate: <b>{sim.affected_processes.join(", ") || "—"}</b></div>
                    <div>Actori afectați: <b>{sim.affected_users.join(", ")}</b></div>
                    {(sim.estimated_state_changes || []).map((c, i) => (
                      <div key={i} className="text-stone-400">
                        {c.entity}: {c.from || "∅"} → <b className="text-white">{c.to}</b>
                        {c.terminal ? " (final)" : ""}{c.estimated ? ` (apoi, ${c.actor})` : ""}
                      </div>
                    ))}
                  </div>
                )}
                {expl?.explanation && (
                  <div className="rounded-lg border border-[#d4ff3a]/25 bg-[#d4ff3a]/5 p-2.5 max-h-64 overflow-auto" data-testid="de-explanation">
                    <div className="text-[12px] text-stone-200 whitespace-pre-wrap leading-relaxed">
                      {String(expl.explanation).replace(/##\s?/g, "▸ ").replace(/\*\*/g, "")}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
