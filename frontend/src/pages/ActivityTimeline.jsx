// PropManage - Request Activity Timeline
// Shows the full lifecycle of a request to authorized roles (client, specialist, admin, operator)
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import {
  X, Clock, FileText, Wrench, CheckCircle2, CreditCard, Award,
  AlertTriangle, Scale, Sparkles, Flag, Home as HomeIcon, Calendar,
} from "lucide-react";
import { API } from "./DashShared";

// Icon + color per event_type
const EVENT_CONFIG = {
  "request.created":           { icon: FileText,    color: "text-cyan-300",    bg: "bg-cyan-500/15 border-cyan-500/30",       label: "Cerere creată" },
  "request.accepted":          { icon: Wrench,      color: "text-amber-300",   bg: "bg-amber-500/15 border-amber-500/30",     label: "Specialist acceptat" },
  "escrow.paid":               { icon: CreditCard,  color: "text-emerald-300", bg: "bg-emerald-500/15 border-emerald-500/30", label: "Plată în escrow" },
  "work.started":              { icon: Wrench,      color: "text-blue-300",    bg: "bg-blue-500/15 border-blue-500/30",       label: "Lucrare pornită" },
  "work.completed":            { icon: CheckCircle2,color: "text-purple-300",  bg: "bg-purple-500/15 border-purple-500/30",   label: "Lucrare finalizată" },
  "work.confirmed":            { icon: Award,       color: "text-[#d4ff3a]",   bg: "bg-[#d4ff3a]/15 border-[#d4ff3a]/30",     label: "Confirmat + plată eliberată" },
  "twin.requested":            { icon: Sparkles,    color: "text-fuchsia-300", bg: "bg-fuchsia-500/15 border-fuchsia-500/30", label: "Twin solicitat" },
  "twin.validated":            { icon: HomeIcon,    color: "text-emerald-300", bg: "bg-emerald-500/15 border-emerald-500/30", label: "Twin validat" },
  "dispute.opened":            { icon: AlertTriangle,color:"text-red-300",     bg: "bg-red-500/15 border-red-500/30",         label: "Dispută deschisă" },
  "dispute.resolved":          { icon: Scale,       color: "text-emerald-300", bg: "bg-emerald-500/15 border-emerald-500/30", label: "Dispută rezolvată" },
  "operator.flagged_nonconformity": { icon: Flag,   color: "text-orange-300",  bg: "bg-orange-500/15 border-orange-500/30",   label: "Sesizare operator" },
  "admin.resolved_nonconformity":   { icon: Scale,  color: "text-emerald-300", bg: "bg-emerald-500/15 border-emerald-500/30", label: "Sesizare rezolvată" },
};

const fallbackCfg = { icon: Clock, color: "text-stone-300", bg: "bg-white/5 border-white/10", label: "Eveniment" };

export const RequestTimelineModal = ({ requestId, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!requestId) return;
    setLoading(true);
    axios.get(`${API}/requests/${requestId}/timeline`)
      .then(r => { setData(r.data); setError(null); })
      .catch(e => setError(e.response?.data?.detail || "Nu se poate încărca timeline-ul."))
      .finally(() => setLoading(false));
  }, [requestId]);

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-strong rounded-3xl p-6 max-w-2xl w-full max-h-[90vh] overflow-auto no-scrollbar"
        data-testid="request-timeline-modal"
      >
        <div className="flex items-start justify-between mb-5 gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-stone-500 mb-1">
              <Clock className="w-3 h-3" />Activity Timeline
            </div>
            <h2 className="font-serif text-2xl truncate" data-testid="timeline-title">
              {data?.request?.title || "Cerere"}
            </h2>
            {data?.request && (
              <div className="text-xs text-stone-500 mt-1">
                {data.request.client_name} → {data.request.specialist_name || "fără specialist"} · {data.request.status}
              </div>
            )}
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg shrink-0" data-testid="timeline-close">
            <X className="w-4 h-4 text-stone-400" />
          </button>
        </div>

        {loading && <div className="text-center py-12 text-stone-500 text-sm">Se încarcă...</div>}
        {error && <div className="text-center py-12 text-red-400 text-sm">{error}</div>}

        {!loading && !error && data && (
          data.events.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="w-10 h-10 text-stone-700 mx-auto mb-3" />
              <div className="text-sm text-stone-400">Niciun eveniment înregistrat încă</div>
            </div>
          ) : (
            <ol className="relative border-l border-white/10 ml-4 space-y-5" data-testid="timeline-list">
              {data.events.map((e, idx) => <TimelineItem key={e.id || idx} event={e} />)}
            </ol>
          )
        )}
      </motion.div>
    </div>
  );
};

const TimelineItem = ({ event }) => {
  const cfg = EVENT_CONFIG[event.event_type] || fallbackCfg;
  const Icon = cfg.icon;
  const when = new Date(event.created_at);
  const dateStr = when.toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

  return (
    <li className="ml-6 relative" data-testid={`timeline-event-${event.event_type}`}>
      <span className={`absolute -left-[34px] w-7 h-7 rounded-full flex items-center justify-center border ${cfg.bg}`}>
        <Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
      </span>
      <div className="bg-white/5 rounded-2xl p-3 hover:bg-white/[0.08] transition-colors">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-1">
          <div className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</div>
          <div className="text-[10px] text-stone-500">{dateStr}</div>
        </div>
        <div className="text-[11px] text-stone-400">
          <span className="text-stone-300 font-medium">{event.actor_name}</span>
          <span className="ml-1.5 text-[9px] uppercase tracking-wider text-stone-500">{event.actor_role}</span>
        </div>
        {event.payload && Object.keys(event.payload).length > 0 && (
          <EventPayload payload={event.payload} />
        )}
      </div>
    </li>
  );
};

const EventPayload = ({ payload }) => {
  // Special render for schedule proposal
  if (payload.schedule && payload.schedule.start_date) {
    const s = payload.schedule;
    return (
      <div className="mt-2 bg-black/30 rounded-lg p-2 text-[10px] space-y-1">
        <div className="flex items-center gap-1.5 text-amber-300">
          <Calendar className="w-3 h-3" />
          <span>Programare: {s.start_date?.slice(0,10)} {s.end_date ? `→ ${s.end_date.slice(0,10)}` : ""}</span>
        </div>
        {s.estimated_hours != null && <div className="text-stone-400">Ore estimate: {s.estimated_hours}h</div>}
        {s.note && <div className="text-stone-400 italic">"{s.note}"</div>}
      </div>
    );
  }
  // Generic render
  const entries = Object.entries(payload).filter(([_, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <div className="mt-2 bg-black/30 rounded-lg p-2 text-[10px] text-stone-400 space-y-0.5">
      {entries.slice(0, 4).map(([k, v]) => (
        <div key={k}>
          <span className="text-stone-500">{k}:</span> <span className="text-stone-300">{typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v).slice(0, 100)}</span>
        </div>
      ))}
    </div>
  );
};

// ============= SCHEDULE PROPOSAL MODAL (Specialist) =============
export const ScheduleProposalModal = ({ requestId, requestTitle, feeWaived = false, onClose, onAccepted }) => {
  const today = new Date().toISOString().split("T")[0];
  const [form, setForm] = useState({
    proposed_start_date: today,
    proposed_end_date: today,
    estimated_hours: 4,
    note: "",
  });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/requests/${requestId}/accept`, form);
      onAccepted?.();
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || "Eroare la acceptare.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-strong rounded-3xl p-6 max-w-md w-full"
        data-testid="schedule-proposal-modal"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-2xl">Propune termenii</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="schedule-close">
            <X className="w-4 h-4 text-stone-400" />
          </button>
        </div>
        <p className="text-xs text-stone-400 mb-4 leading-relaxed">
          {requestTitle ? <>Pentru: <span className="text-stone-200">"{requestTitle}"</span>. </> : null}
          Setează datele propuse — clientul le va vedea în timeline și te poate contacta pentru ajustări. {feeWaived ? "Cerere directă de re-angajare — taxa de lead este 0 RON." : "Taxa de lead 45 RON se reține la acceptare."}
        </p>
        <form onSubmit={submit} className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Data start">
              <input type="date" required min={today}
                value={form.proposed_start_date}
                onChange={e => setForm({ ...form, proposed_start_date: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm"
                data-testid="schedule-start" />
            </Field>
            <Field label="Data finalizare">
              <input type="date" required min={form.proposed_start_date}
                value={form.proposed_end_date}
                onChange={e => setForm({ ...form, proposed_end_date: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm"
                data-testid="schedule-end" />
            </Field>
          </div>
          <Field label="Ore estimate">
            <input type="number" min="0.5" max="200" step="0.5"
              value={form.estimated_hours}
              onChange={e => setForm({ ...form, estimated_hours: parseFloat(e.target.value) })}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm"
              data-testid="schedule-hours" />
          </Field>
          <Field label="Mesaj pentru client (opțional)">
            <textarea rows={3}
              value={form.note}
              onChange={e => setForm({ ...form, note: e.target.value })}
              placeholder="ex: Vin marți dimineață cu echipa. Vă rog să aveți acces la centrală."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm resize-none"
              data-testid="schedule-note" />
          </Field>
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Anulează</button>
            <button type="submit" disabled={loading} className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium" data-testid="schedule-submit">
              {loading ? "..." : feeWaived ? "Acceptă (gratuit)" : "Acceptă (45 RON)"}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

// ============= OPERATOR NONCONFORMITY FLAG MODAL =============
export const NonConformityFlagModal = ({ targetType = "request", targetId, targetLabel, onClose, onFlagged }) => {
  const [form, setForm] = useState({ reason: "", severity: "medium" });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/operator/flag-nonconformity`, {
        target_type: targetType,
        target_id: targetId,
        reason: form.reason,
        severity: form.severity,
      });
      alert("Sesizare trimisă admin-ului. Va fi analizată în maxim 48h.");
      onFlagged?.();
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || "Eroare la trimitere.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-strong rounded-3xl p-6 max-w-md w-full"
        data-testid="nonconformity-modal"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-2xl flex items-center gap-2">
            <Flag className="w-5 h-5 text-orange-400" />Sesizare admin
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <X className="w-4 h-4 text-stone-400" />
          </button>
        </div>
        <p className="text-xs text-stone-400 mb-4">
          Țintă: <span className="text-stone-200">{targetLabel || targetType}</span>. Admin-ul va primi notificare imediat.
        </p>
        <form onSubmit={submit} className="space-y-3">
          <Field label="Severitate">
            <div className="grid grid-cols-3 gap-2">
              {["low","medium","high"].map(s => (
                <button key={s} type="button" onClick={() => setForm({ ...form, severity: s })}
                  className={`py-2.5 rounded-xl text-xs uppercase tracking-wider font-medium ${
                    form.severity === s
                      ? (s === "high" ? "bg-red-500/30 text-red-200 border border-red-500/50"
                         : s === "medium" ? "bg-amber-500/30 text-amber-200 border border-amber-500/50"
                         : "bg-stone-500/30 text-stone-200 border border-stone-500/50")
                      : "bg-white/5 text-stone-500"
                  }`}
                  data-testid={`severity-${s}`}>
                  {s === "low" ? "Scăzută" : s === "medium" ? "Medie" : "Ridicată"}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Motiv">
            <textarea required rows={5} minLength={5}
              value={form.reason}
              onChange={e => setForm({ ...form, reason: e.target.value })}
              placeholder="Descrie neconformitatea observată: documente lipsă, lucrare nefinalizată conform standardelor, suspiciune de fraudă etc."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm resize-none"
              data-testid="nc-reason" />
          </Field>
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Anulează</button>
            <button type="submit" disabled={loading} className="flex-1 bg-orange-500 hover:bg-orange-600 text-white py-3 rounded-xl text-sm font-medium" data-testid="nc-submit">
              {loading ? "..." : "Trimite sesizare"}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5 block">{label}</label>
    {children}
  </div>
);

// ============= LAST ACTION BANNER (shown on request cards) =============
const ACTION_LABELS = {
  "request.created":                 "a creat solicitarea",
  "request.accepted":                "a acceptat",
  "escrow.paid":                     "a plătit escrow",
  "work.started":                    "a pornit lucrarea",
  "work.completed":                  "a marcat finalizată",
  "work.confirmed":                  "a confirmat & eliberat plata",
  "twin.requested":                  "a cerut activare twin",
  "twin.validated":                  "a validat twin-ul",
  "dispute.opened":                  "a deschis o dispută",
  "dispute.resolved":                "a rezolvat disputa",
  "operator.flagged_nonconformity":  "a raportat neconformitate",
  "admin.resolved_nonconformity":    "a rezolvat sesizarea",
};

const ROLE_DOT_COLOR = {
  client:     "bg-cyan-400",
  specialist: "bg-amber-400",
  admin:      "bg-purple-400",
  operator:   "bg-fuchsia-400",
  system:     "bg-stone-400",
};

function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "acum câteva secunde";
  if (m < 60) return `acum ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `acum ${h}h`;
  const d = Math.floor(h / 24);
  if (d < 7) return `acum ${d}z`;
  return new Date(iso).toLocaleDateString("ro-RO", { day: "2-digit", month: "short" });
}

export const LastActionBanner = ({ event, onClick }) => {
  if (!event) return null;
  const label = ACTION_LABELS[event.event_type] || event.event_type.replace(/[._]/g, " ");
  const dot = ROLE_DOT_COLOR[event.actor_role] || ROLE_DOT_COLOR.system;

  // Surface schedule info when relevant
  let extra = null;
  const sched = event.payload?.schedule;
  if (sched && sched.start_date) {
    const s = sched.start_date.slice(0, 10);
    const e = sched.end_date ? `→ ${sched.end_date.slice(0, 10)}` : "";
    const hrs = sched.estimated_hours != null ? ` · ${sched.estimated_hours}h` : "";
    extra = ` (${s}${e ? " " + e : ""}${hrs})`;
  } else if (event.payload?.amount != null && event.event_type.startsWith("escrow")) {
    extra = ` · ${event.payload.amount} RON`;
  }

  return (
    <button
      onClick={onClick}
      className="w-full mt-3 mb-1 bg-white/[0.04] hover:bg-white/[0.07] border border-white/5 rounded-lg px-3 py-2 text-left transition-colors group"
      data-testid="last-action-banner"
    >
      <div className="flex items-center gap-2 text-[11px] flex-wrap">
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
        <span className="text-stone-300 font-medium truncate">{event.actor_name}</span>
        <span className="text-stone-400">{label}</span>
        {extra && <span className="text-stone-500 italic">{extra}</span>}
        <span className="text-stone-600 ml-auto shrink-0">{timeAgo(event.created_at)}</span>
      </div>
    </button>
  );
};

