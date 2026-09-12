// CollaborationExplorer — AIB-009 · Collaborative Intelligence Engine (tab în /admin/ai-brain).
// SLA, responsabilități, transferuri între actori, notificări inteligente, escaladări propuse.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Handshake, Loader2, RefreshCw, ArrowRight, AlertTriangle, BellRing, Timer, UserCheck,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const LEVEL_STYLE = {
  at_risk: "text-amber-300", breached: "text-rose-300", abandoned: "text-rose-400", ok: "text-emerald-300",
};

const Stat = ({ label, value, tone = "" }) => (
  <div className="bg-stone-900/50 border border-stone-800 rounded-xl p-3 text-center">
    <div className={`text-xl font-black ${tone || "text-white"}`}>{value ?? "—"}</div>
    <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-0.5">{label}</div>
  </div>
);

const HandoffChain = ({ handoffs }) => (
  <div className="space-y-1.5" data-testid="ce-handoffs">
    {handoffs.map((h, i) => (
      <div key={i} className="text-[11px] text-stone-300 bg-stone-900/50 border border-stone-800 rounded-lg px-2.5 py-1.5">
        <span className="font-bold text-sky-300">{h.from_actor.join("/")}</span>
        <ArrowRight className="w-3 h-3 inline mx-1 text-stone-600" />
        <span className="font-bold text-[#d4ff3a]">{h.to_actor.join("/")}</span>
        <span className="text-stone-500"> la etapa «{h.at_state}»</span>
        <div className="text-stone-500 mt-0.5">{h.why}</div>
      </div>
    ))}
    {!handoffs.length && <div className="text-xs text-stone-500">Un singur actor pe tot fluxul — fără transferuri.</div>}
  </div>
);

export const CollaborationExplorer = () => {
  const [ov, setOv] = useState(null);
  const [sel, setSel] = useState(null);
  const [handoffs, setHandoffs] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => ax.get("/api/admin/ai-brain/collaboration/overview").then(r => setOv(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const sweep = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/ai-brain/collaboration/sweep"); await load(); } finally { setBusy(false); }
  };

  const select = async (p) => {
    setSel(p); setHandoffs(null);
    try {
      const { data } = await ax.get(`/api/admin/ai-brain/collaboration/handoffs/${p.process_id}`);
      setHandoffs(data.handoffs);
    } catch { setHandoffs([]); }
  };

  const t = ov?.totals;
  return (
    <div className="border border-stone-800 rounded-2xl bg-stone-900/30 p-4 mt-8" data-testid="collaboration-explorer">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Handshake className="w-4 h-4 text-[#d4ff3a]" />
        <div className="text-xs font-bold uppercase tracking-wider text-stone-400">Collaboration Explorer — AIB-009 · Collaborative Intelligence Engine</div>
        <div className="flex-1" />
        <button onClick={sweep} disabled={busy}
          className="px-3 py-1.5 text-[11px] rounded-lg bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5" data-testid="ce-sweep-btn">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Rulează SLA sweep
        </button>
      </div>

      <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 mb-4" data-testid="ce-stats">
        <Stat label="Procese monitorizate" value={t?.monitored} />
        <Stat label="Instanțe active" value={t?.instances} />
        <Stat label="La risc" value={t?.at_risk} tone="text-amber-300" />
        <Stat label="SLA depășit" value={t?.breached} tone="text-rose-300" />
        <Stat label="Abandon probabil" value={t?.abandoned} tone="text-rose-400" />
        <Stat label="Notificări active" value={t?.notifications_active} tone="text-sky-300" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-2 space-y-1.5 max-h-[420px] overflow-auto" data-testid="ce-process-list">
          {(ov?.processes || []).map(p => (
            <button key={p.process_id} onClick={() => select(p)}
              className={`w-full text-left rounded-xl border p-2.5 transition-colors ${sel?.process_id === p.process_id ? "border-[#d4ff3a]/50 bg-stone-900/70" : "border-stone-800 bg-stone-900/40 hover:border-stone-700"}`}
              data-testid={`ce-item-${p.process_id}`}>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-bold text-white flex-1 truncate">{p.process_name}</span>
                <span className="text-[10px] text-stone-500">{p.active} active</span>
              </div>
              <div className="text-[10px] mt-0.5 flex gap-2">
                <span className={LEVEL_STYLE.ok}>{p.counts.ok} ok</span>
                <span className={LEVEL_STYLE.at_risk}>{p.counts.at_risk} risc</span>
                <span className={LEVEL_STYLE.breached}>{p.counts.breached} depășite</span>
                <span className={LEVEL_STYLE.abandoned}>{p.counts.abandoned} abandon</span>
              </div>
            </button>
          ))}
          {!(ov?.processes || []).length && <div className="text-xs text-stone-500 p-2">Rulează SLA sweep pentru prima analiză.</div>}
        </div>

        <div className="lg:col-span-3 rounded-xl border border-stone-800 bg-stone-900/40 p-3.5 max-h-[420px] overflow-auto" data-testid="ce-detail">
          {!sel ? (
            <div className="text-xs text-stone-500">Selectează un proces pentru transferuri, instanțe blocate și escaladări.</div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm font-bold text-white flex items-center gap-2">
                {sel.process_name}
                <span className="text-[10px] text-stone-500 font-normal">actori: {(sel.actors || []).join(", ")}</span>
              </div>
              <div>
                <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
                  <UserCheck className="w-3 h-3 text-[#d4ff3a]" /> Intelligent Handoff — transferuri de responsabilitate
                </div>
                {handoffs === null ? <Loader2 className="w-4 h-4 animate-spin text-stone-500" /> : <HandoffChain handoffs={handoffs} />}
              </div>
              {(sel.breaches || []).length > 0 && (
                <div data-testid="ce-breaches">
                  <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
                    <Timer className="w-3 h-3 text-rose-400" /> Instanțe peste SLA + escaladări propuse
                  </div>
                  <div className="space-y-2">
                    {sel.breaches.map((b, i) => (
                      <div key={i} className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-2.5 text-[11px]">
                        <div className="text-stone-200">
                          <b>{b.entity.label}</b> — etapa «{b.state}» de <b>{Math.round(b.sla.hours_in_stage / 24)}z</b>
                          <span className="text-stone-500"> (SLA {Math.round(b.sla.sla_hours)}h · {b.sla.ratio}× · {b.sla.basis})</span>
                        </div>
                        <div className="text-stone-400 mt-0.5">
                          Responsabil: <b className="text-rose-300">{(b.responsible_now || []).join(", ") || "—"}</b>
                          {b.waiting_actors?.length > 0 && <> · așteaptă: {b.waiting_actors.join(", ")}</>}
                        </div>
                        {(b.escalations || []).map((e, j) => (
                          <div key={j} className="mt-1 text-amber-200/90 flex items-start gap-1.5" data-testid="ce-escalation">
                            <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                            <span><b className="uppercase text-[10px]">{e.action}</b> → {(e.to || []).join(", ")} — {e.why}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {(ov?.notifications || []).length > 0 && (
        <div className="mt-4" data-testid="ce-notifications">
          <div className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-1.5 flex items-center gap-1">
            <BellRing className="w-3 h-3 text-sky-300" /> Notification Intelligence — notificări generate (deduplicate, prioritizate)
          </div>
          <div className="space-y-1 max-h-48 overflow-auto">
            {ov.notifications.map(n => (
              <div key={n.key} className="flex items-start gap-2 text-[11px] text-stone-300 bg-stone-900/50 border border-stone-800 rounded-lg px-2.5 py-1.5">
                <span className="text-[10px] font-black text-sky-300 shrink-0 w-8 text-center bg-sky-500/10 rounded border border-sky-500/25">{n.priority}</span>
                <span className="font-bold text-white shrink-0">{n.target}</span>
                <span className="flex-1">{n.why}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
