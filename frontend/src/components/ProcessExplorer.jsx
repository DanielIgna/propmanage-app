// ProcessExplorer — AIB-006 · Process Intelligence Engine (tab în /admin/ai-brain).
// Procese descoperite automat din cod: etape, actori, tranziții, relații, blocaje, abandon.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Workflow, Loader2, RefreshCw, Users, GitBranch, AlertTriangle, ScanEye, ArrowRight } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const KIND_STYLE = {
  business: "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/30",
  internal: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  automated: "bg-amber-500/10 text-amber-300 border-amber-500/30",
};

const StepFlow = ({ proc, stateSteps }) => {
  const phases = {};
  (stateSteps || []).forEach(s => { phases[s.state] = s.phase; });
  if (!proc?.steps?.length) return <div className="text-xs text-stone-500">Proces automat — fără etape per entitate.</div>;
  return (
    <div className="flex flex-wrap items-center gap-1.5" data-testid="pe-steps">
      {proc.steps.map((s, i) => (
        <React.Fragment key={s}>
          {i > 0 && <ArrowRight className="w-3 h-3 text-stone-600" />}
          <span className={`text-[10px] font-bold px-2 py-1 rounded-lg border ${
            phases[s] === "done" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
            : phases[s] === "current" ? "bg-[#d4ff3a]/15 text-[#d4ff3a] border-[#d4ff3a]/50"
            : proc.terminal_states?.includes(s) ? "bg-stone-800 text-stone-300 border-stone-600"
            : "bg-stone-900 text-stone-400 border-stone-700"}`}>
            {s}
          </span>
        </React.Fragment>
      ))}
    </div>
  );
};

const InspectState = ({ pid }) => {
  const [email, setEmail] = useState("client@propmanage.io");
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  const inspect = async (e) => {
    e?.preventDefault(); setBusy(true);
    try {
      const { data } = await ax.get(`/api/admin/ai-brain/processes/${pid}/state`, { params: { email } });
      setSt(data);
    } catch (ex) { setSt({ error: ex?.response?.data?.detail || ex.message }); } finally { setBusy(false); }
  };
  return (
    <div className="mt-4 border-t border-stone-800 pt-3">
      <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2">Process State Engine — starea reală a unui utilizator</div>
      <form onSubmit={inspect} className="flex gap-2">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email utilizator"
          className="flex-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-1.5 text-xs text-white" data-testid="pe-inspect-email" />
        <button disabled={busy} className="px-3 py-1.5 text-[11px] rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1" data-testid="pe-inspect-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <ScanEye className="w-3 h-3" />} Inspectează
        </button>
      </form>
      {st && (
        <div className="mt-3 space-y-2" data-testid="pe-inspect-result">
          {st.error && <div className="text-xs text-rose-300">{st.error}</div>}
          {!st.error && (
            <>
              <div className="text-xs text-stone-300">
                Stare: <b className="text-white">{st.status}</b>
                {st.current_state && <> · etapa <b className="text-[#d4ff3a]">{st.current_state}</b> ({st.step_index + 1}/{st.total_steps})</>}
                {st.entity?.label && <span className="text-stone-500"> · {st.entity.label}</span>}
              </div>
              {st.who_acts?.length > 0 && <div className="text-[11px] text-stone-400">Acționează: {st.who_acts.join(", ")}</div>}
              <StepFlow proc={{ steps: (st.steps || []).map(s => s.state), terminal_states: [] }} stateSteps={st.steps} />
              {(st.blockers || []).map((b, i) => (
                <div key={i} className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/25 rounded-lg px-2 py-1.5 flex items-start gap-1.5" data-testid="pe-blocker">
                  <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" /> {b.text}
                </div>
              ))}
              {(st.timeline || []).length > 0 && (
                <div className="max-h-28 overflow-auto space-y-0.5" data-testid="pe-timeline">
                  {st.timeline.map((t, i) => (
                    <div key={i} className="text-[11px] text-stone-400 flex gap-2">
                      <span className="text-stone-600 shrink-0">{new Date(t.ts).toLocaleString("ro-RO")}</span>
                      <span className="flex-1 truncate">{t.event}</span>
                      {t.actor && <span className="text-stone-600">{t.actor}</span>}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export const ProcessExplorer = () => {
  const [items, setItems] = useState([]);
  const [kind, setKind] = useState("business");
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { data } = await ax.get("/api/admin/ai-brain/processes");
    setItems(data.items || []);
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const rebuild = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/ai-brain/processes/build"); await load(); } finally { setBusy(false); }
  };

  const counts = items.reduce((a, p) => { a[p.kind] = (a[p.kind] || 0) + 1; return a; }, {});
  const shown = items.filter(p => p.kind === kind);

  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="process-explorer">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Workflow className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Process Explorer — AIB-006 · Process Intelligence Engine</div>
        <div className="flex-1" />
        <span className="text-[11px] text-stone-500" data-testid="pe-counts">
          {items.length} procese · {counts.business || 0} business · {counts.internal || 0} interne · {counts.automated || 0} automate
        </span>
        <button onClick={rebuild} disabled={busy}
          className="px-3 py-1.5 text-[11px] rounded-lg bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="pe-rebuild-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Redescoperă procesele
        </button>
      </div>
      <div className="flex gap-1.5 mb-3">
        {["business", "internal", "automated"].map(k => (
          <button key={k} onClick={() => setKind(k)}
            className={`text-[10px] font-bold uppercase px-2.5 py-1 rounded-lg border ${kind === k ? KIND_STYLE[k] : "bg-stone-900 text-stone-500 border-stone-800"}`}
            data-testid={`pe-tab-${k}`}>
            {k === "business" ? "Business" : k === "internal" ? "Interne" : "Automate"} ({counts[k] || 0})
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-2 max-h-[480px] overflow-auto space-y-1.5" data-testid="pe-list">
          {shown.length === 0 && <div className="text-xs text-stone-500 p-3">Apasă «Redescoperă procesele» pentru prima analiză.</div>}
          {shown.map(p => (
            <button key={p.id} onClick={() => setSel(p)}
              className={`w-full text-left rounded-xl border p-2.5 transition-colors ${sel?.id === p.id ? "border-[#d4ff3a]/50 bg-stone-900/70" : "border-stone-800 bg-stone-900/40 hover:border-stone-700"}`}
              data-testid={`pe-item-${p.id}`}>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-bold text-white flex-1 truncate">{p.name}</span>
                {p.stats && <span className="text-[10px] text-stone-500">{p.stats.total} instanțe</span>}
                {p.stats?.stale_count > 0 && (
                  <span className="text-[10px] font-bold text-rose-300 flex items-center gap-0.5"><AlertTriangle className="w-3 h-3" />{p.stats.stale_count}</span>
                )}
              </div>
              <div className="text-[11px] text-stone-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
                {p.entity && <span className="font-mono">{p.entity}</span>}
                {p.trigger_signal && <span className="font-mono">semnal: {p.trigger_signal}</span>}
                {p.actors?.length > 0 && <span className="flex items-center gap-0.5"><Users className="w-3 h-3" />{p.actors.join(", ")}</span>}
              </div>
            </button>
          ))}
        </div>
        <div className="lg:col-span-3 rounded-xl border border-stone-800 bg-stone-900/40 p-3.5 min-h-[200px]" data-testid="pe-detail">
          {!sel ? (
            <div className="text-xs text-stone-500">Selectează un proces din listă pentru etape, tranziții, relații și blocaje.</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-white">{sel.name}</span>
                <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded border ${KIND_STYLE[sel.kind]}`}>{sel.kind}</span>
                {sel.entity && <span className="text-[11px] font-mono text-stone-500">db.{sel.entity}</span>}
              </div>
              {sel.purpose && <p className="text-[11px] text-stone-400">{sel.purpose}</p>}
              <StepFlow proc={sel} />
              {sel.transitions?.length > 0 && (
                <div data-testid="pe-transitions">
                  <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5">Tranziții ({sel.transitions.length})</div>
                  <div className="max-h-36 overflow-auto space-y-0.5">
                    {sel.transitions.map((t, i) => (
                      <div key={i} className="text-[11px] text-stone-400 flex items-center gap-1.5">
                        <span className="text-stone-500">{t.from || "∅"}</span>
                        <ArrowRight className="w-3 h-3 text-stone-600" />
                        <span className="text-white font-bold">{t.to}</span>
                        <span className="text-[10px] px-1.5 rounded bg-stone-800 text-stone-400">{t.actor}</span>
                        <span className="flex-1 truncate text-stone-600 font-mono text-[10px]">{t.endpoint.method} {t.endpoint.path}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {sel.relations?.length > 0 && (
                <div data-testid="pe-relations">
                  <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5">Relații cu alte procese</div>
                  <div className="flex flex-wrap gap-1.5">
                    {sel.relations.map((r, i) => (
                      <span key={i} className="text-[10px] font-bold px-2 py-1 rounded-lg bg-stone-800 text-stone-300 border border-stone-700 flex items-center gap-1">
                        <GitBranch className="w-3 h-3 text-[#d4ff3a]" /> {r.rel} → {r.to.replace("proc_", "")}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {sel.stats && (
                <div data-testid="pe-stats">
                  <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5">Statistici de execuție</div>
                  <div className="flex flex-wrap gap-1.5 text-[11px]">
                    <span className="px-2 py-1 rounded-lg bg-stone-800 text-stone-300">{sel.stats.total} total</span>
                    <span className="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/25">{sel.stats.active} active</span>
                    {sel.stats.stale_count > 0 && (
                      <span className="px-2 py-1 rounded-lg bg-rose-500/10 text-rose-300 border border-rose-500/25">{sel.stats.stale_count} blocate &gt;14 zile</span>
                    )}
                    {Object.entries(sel.stats.by_status || {}).map(([s, n]) => (
                      <span key={s} className="px-2 py-1 rounded-lg bg-stone-900 text-stone-400 border border-stone-800">{s}: {n}</span>
                    ))}
                  </div>
                  {(sel.stats.abandon_points || []).length > 0 && (
                    <div className="mt-2 text-[11px] text-amber-300/90" data-testid="pe-abandon">
                      Puncte de abandon: {sel.stats.abandon_points.map(a => `${a.state} (${a.stuck})`).join(" · ")}
                    </div>
                  )}
                </div>
              )}
              {sel.entity && <InspectState pid={sel.id} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
