// Phase I+: Sent Reports dashboard — "Răspunsuri așteptate".
// Lists all reports the current user has sent, with status pills, age timer, overdue filter, and reminder.
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  ArrowLeft, BellRing, CheckCircle2, FileEdit, Clock, ExternalLink,
  AlertTriangle, X, Loader2, Mail, Send, Filter, Settings, Pause, Play, BellOff,
} from "lucide-react";
import { API } from "../views/DashShared";

const STATUS_META = {
  pending: { label: "În așteptare", color: "#f59e0b", bg: "bg-amber-500/15", text: "text-amber-300", border: "border-amber-500/30" },
  confirmed: { label: "Confirmat", color: "#10b981", bg: "bg-emerald-500/15", text: "text-emerald-300", border: "border-emerald-500/30" },
  needs_changes: { label: "Necesită modificări", color: "#3b82f6", bg: "bg-blue-500/15", text: "text-blue-300", border: "border-blue-500/30" },
};

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso.slice(0, 16);
  }
};

const ReminderModal = ({ item, onClose, onSent }) => {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const send = async () => {
    setBusy(true);
    setErr(null);
    try {
      const { data } = await axios.post(`${API}/digital-twin/reports/${item.report_id}/remind`, {
        note: note.trim() || null,
      });
      onSent?.(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md space-y-3" data-testid="reminder-modal">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-amber-400/90 font-semibold">Reminder</div>
            <h3 className="font-serif text-lg text-white">Trimite reminder</h3>
            <p className="text-xs text-stone-400 mt-0.5">Re-trimite același link de aprobare către <strong>{item.recipient_name || item.recipient_email}</strong>.</p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="bg-white/[0.02] rounded-lg p-2.5 text-[11px] text-stone-400 space-y-0.5 border border-white/5">
          <div>Pin: <strong className="text-stone-200">{item.pin_title}</strong></div>
          <div>Proiect: <strong className="text-stone-200">{item.project_name}</strong></div>
          <div>În așteptare de <strong className="text-amber-300">{item.age_days} zile</strong></div>
          {item.reminder_count > 0 && <div className="text-amber-300">⚠️ {item.reminder_count} reminder{item.reminder_count > 1 ? "e" : ""} deja trimise</div>}
        </div>

        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Notă personală (opțional)</label>
          <textarea
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Ex: Te rog răspunde până vineri — am nevoie să planific echipa de săptămâna viitoare."
            maxLength={1000}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="reminder-note"
          />
          <div className="text-[10px] text-stone-600 mt-0.5 text-right">{note.length}/1000</div>
        </div>

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        <div className="flex gap-2 pt-1">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300">Anulează</button>
          <button
            onClick={send}
            disabled={busy}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-medium flex items-center justify-center gap-1.5"
            data-testid="reminder-send"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <BellRing className="w-4 h-4" />}
            Trimite reminder
          </button>
        </div>
      </div>
    </div>
  );
};

const StatusPill = ({ status }) => {
  const meta = STATUS_META[status] || STATUS_META.pending;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold ${meta.bg} ${meta.text} border ${meta.border}`} data-testid={`status-${status}`}>
      {meta.label}
    </span>
  );
};

const AutoReminderSettingsModal = ({ item, onClose, onSaved }) => {
  const [enabled, setEnabled] = useState(item.auto_reminders_enabled !== false);
  const [stopped, setStopped] = useState(!!item.auto_reminders_stopped);
  const [thresholds, setThresholds] = useState((item.reminder_thresholds_days || [7, 14, 21]).join(", "));
  const [pausedUntil, setPausedUntil] = useState(item.paused_until || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      const thrArr = thresholds.split(",").map(s => parseInt(s.trim(), 10)).filter(n => Number.isFinite(n) && n >= 1 && n <= 365);
      if (thrArr.length === 0) {
        setErr("Cel puțin un prag valid între 1-365 zile.");
        setBusy(false);
        return;
      }
      const { data } = await axios.patch(`${API}/digital-twin/reports/${item.report_id}/reminder-settings`, {
        auto_reminders_enabled: enabled,
        stopped,
        thresholds_days: thrArr,
        paused_until: pausedUntil || "",
      });
      onSaved?.(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const nextDue = (() => {
    if (!enabled || stopped) return null;
    if (pausedUntil) {
      try {
        const d = new Date(pausedUntil);
        if (d > new Date()) return `Reluare după ${d.toLocaleDateString("ro-RO")}`;
      } catch {/* ignore */}
    }
    const fired = item.auto_reminders_fired_thresholds || [];
    const remaining = (item.reminder_thresholds_days || [7, 14, 21]).filter(t => !fired.includes(t));
    if (remaining.length === 0) return "Toate pragurile au fost trimise";
    const next = Math.min(...remaining);
    const remainingDays = next - item.age_days;
    if (remainingDays <= 0) return "Va fi trimis la următoarea rulare (mâine 08:15)";
    return `Următorul: peste ${remainingDays} ${remainingDays === 1 ? "zi" : "zile"} (prag: ${next}d)`;
  })();

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md space-y-3" data-testid="auto-reminder-settings-modal">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/90 font-semibold">Auto-reminder</div>
            <h3 className="font-serif text-lg text-white">Setări reminder automat</h3>
            <p className="text-xs text-stone-400 mt-0.5 max-w-[300px]">Configurează când sistemul trimite automat reminder către <strong>{item.recipient_name || item.recipient_email}</strong>.</p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {/* Master toggle */}
        <label className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5 cursor-pointer">
          <div>
            <div className="text-sm text-white font-medium">Auto-reminder activ</div>
            <div className="text-[11px] text-stone-500">Sistemul trimite automat email-uri la pragurile setate.</div>
          </div>
          <input
            type="checkbox"
            checked={enabled && !stopped}
            onChange={(e) => { setEnabled(e.target.checked); if (e.target.checked) setStopped(false); }}
            className="w-5 h-5 accent-emerald-500"
            data-testid="auto-reminder-enabled"
          />
        </label>

        {/* Thresholds */}
        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Praguri (zile)</label>
          <input
            value={thresholds}
            onChange={(e) => setThresholds(e.target.value)}
            disabled={!enabled || stopped}
            placeholder="7, 14, 21"
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white disabled:opacity-40"
            data-testid="auto-reminder-thresholds"
          />
          <div className="text-[10px] text-stone-600 mt-0.5">Separă cu virgulă. Un prag = un email automat la X zile pending.</div>
        </div>

        {/* Pause */}
        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Pauză până la</label>
          <div className="flex gap-2 mt-1">
            <input
              type="date"
              value={pausedUntil}
              onChange={(e) => setPausedUntil(e.target.value)}
              disabled={!enabled || stopped}
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white disabled:opacity-40"
              data-testid="auto-reminder-pause-until"
            />
            {pausedUntil && (
              <button
                onClick={() => setPausedUntil("")}
                className="px-2.5 py-1 text-[11px] rounded-lg bg-white/5 hover:bg-white/10 text-stone-400"
                data-testid="auto-reminder-pause-clear"
              >
                Anulează
              </button>
            )}
          </div>
        </div>

        {/* Stop forever */}
        <label className="flex items-center justify-between p-3 rounded-lg bg-red-500/[0.05] border border-red-500/15 cursor-pointer">
          <div>
            <div className="text-sm text-red-300 font-medium flex items-center gap-1.5"><BellOff className="w-3.5 h-3.5" /> Oprește definitiv</div>
            <div className="text-[11px] text-stone-500">Nu vor mai fi trimise reminder-uri automate, indiferent de praguri.</div>
          </div>
          <input
            type="checkbox"
            checked={stopped}
            onChange={(e) => setStopped(e.target.checked)}
            className="w-5 h-5 accent-red-500"
            data-testid="auto-reminder-stopped"
          />
        </label>

        {/* Next due info */}
        {nextDue && (
          <div className="text-[11px] text-stone-400 px-3 py-2 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/15">
            <Clock className="w-3 h-3 inline-block mr-1.5 -mt-0.5 text-emerald-400" />
            {nextDue}
          </div>
        )}

        {/* Fired history */}
        {(item.auto_reminders_fired_thresholds || []).length > 0 && (
          <div className="text-[11px] text-stone-500 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5">
            Praguri trimise deja: <strong className="text-stone-300">{item.auto_reminders_fired_thresholds.map(t => `${t}d`).join(", ")}</strong>
          </div>
        )}

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        <div className="flex gap-2 pt-1">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300">Anulează</button>
          <button
            onClick={save}
            disabled={busy}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium flex items-center justify-center gap-1.5"
            data-testid="auto-reminder-save"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Settings className="w-4 h-4" />}
            Salvează
          </button>
        </div>
      </div>
    </div>
  );
};


export default function SentReportsDashboard({ onClose, onOpenProject }) {
  const [filter, setFilter] = useState("pending");
  const [items, setItems] = useState([]);
  const [counters, setCounters] = useState({ total: 0, pending: 0, confirmed: 0, needs_changes: 0, overdue: 0 });
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [reminderFor, setReminderFor] = useState(null);
  const [settingsFor, setSettingsFor] = useState(null);
  const [toast, setToast] = useState(null);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const params = {};
      if (filter !== "all") params.status = filter;
      if (overdueOnly) params.overdue_only = true;
      const { data } = await axios.get(`${API}/digital-twin/reports/sent`, { params });
      setItems(data.items || []);
      setCounters(data.counters || {});
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter, overdueOnly]);

  const handleReminderSent = (data) => {
    setReminderFor(null);
    setToast(`✓ Reminder trimis către ${data.recipient_email}`);
    setTimeout(() => setToast(null), 4000);
    load();
  };

  const filterPills = useMemo(() => [
    { id: "all", label: "Toate", count: counters.total },
    { id: "pending", label: "În așteptare", count: counters.pending },
    { id: "confirmed", label: "Confirmate", count: counters.confirmed },
    { id: "needs_changes", label: "Cu modificări", count: counters.needs_changes },
  ], [counters]);

  return (
    <div className="fixed inset-0 z-50 bg-stone-950 text-white flex flex-col" data-testid="sent-reports-dashboard">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center gap-3 shrink-0">
        <button onClick={onClose} className="text-stone-400 hover:text-white" data-testid="sent-reports-back">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold">Digital Twin · Workflow</div>
          <h1 className="font-serif text-2xl text-white">Răspunsuri așteptate</h1>
        </div>
        <button
          onClick={() => load()}
          className="px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-xs text-stone-300"
          data-testid="sent-reports-refresh"
        >
          Reîmprospătează
        </button>
      </div>

      {/* Filter bar */}
      <div className="px-6 py-3 border-b border-white/5 flex items-center gap-2 flex-wrap shrink-0" data-testid="sent-reports-filters">
        {filterPills.map((p) => (
          <button
            key={p.id}
            onClick={() => { setFilter(p.id); setOverdueOnly(false); }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
              filter === p.id && !overdueOnly ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40" : "bg-white/5 text-stone-400 hover:text-white"
            }`}
            data-testid={`filter-${p.id}`}
          >
            {p.label}
            <span className="px-1.5 py-0.5 rounded-full bg-stone-950 text-[10px]">{p.count || 0}</span>
          </button>
        ))}
        <div className="h-5 w-px bg-white/10 mx-2" />
        <button
          onClick={() => setOverdueOnly((v) => !v)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
            overdueOnly ? "bg-red-500/15 text-red-300 ring-1 ring-red-500/30" : "bg-white/5 text-stone-400 hover:text-white"
          }`}
          data-testid="filter-overdue"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          Overdue &gt;7z
          <span className="px-1.5 py-0.5 rounded-full bg-stone-950 text-[10px]">{counters.overdue || 0}</span>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-sm text-stone-500">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> Se încarcă…
          </div>
        ) : err ? (
          <div className="max-w-md mx-auto mt-12 text-center" data-testid="sent-reports-error">
            <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <p className="text-sm text-stone-300">{err}</p>
          </div>
        ) : items.length === 0 ? (
          <div className="max-w-md mx-auto mt-12 text-center" data-testid="sent-reports-empty">
            <Mail className="w-10 h-10 text-stone-600 mx-auto mb-3" />
            <h3 className="font-serif text-xl text-white mb-1">Niciun raport în această categorie</h3>
            <p className="text-sm text-stone-500">
              {filter === "pending" && "Toate rapoartele tale au primit deja un răspuns. 🎉"}
              {filter === "confirmed" && "Niciun raport confirmat încă."}
              {filter === "needs_changes" && "Niciun raport cu modificări cerute."}
              {filter === "all" && "Nu ai trimis încă niciun raport. Mergi la un pin → click 'Trimite raport'."}
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-w-4xl mx-auto" data-testid="sent-reports-list">
            {items.map((it) => (
              <article
                key={it.report_id}
                className={`rounded-xl border p-4 transition-all ${
                  it.is_overdue ? "bg-red-500/[0.04] border-red-500/30" : "bg-stone-900 border-white/10 hover:border-white/20"
                }`}
                data-testid={`report-row-${it.report_id}`}
              >
                <div className="flex items-start gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    {/* Title + status */}
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h3 className="text-base font-semibold text-white truncate">{it.pin_title}</h3>
                      <StatusPill status={it.approval_status} />
                      {it.is_overdue && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 text-[10px] uppercase tracking-wider font-bold">
                          <AlertTriangle className="w-3 h-3" /> Overdue
                        </span>
                      )}
                    </div>
                    {/* Project + recipient + age */}
                    <div className="text-xs text-stone-400 flex items-center flex-wrap gap-3 mb-2">
                      <span>📁 {it.project_name}</span>
                      <span>→ <strong className="text-stone-300">{it.recipient_name || it.recipient_email}</strong></span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {it.approval_status === "pending"
                          ? `în așteptare de ${it.age_days} ${it.age_days === 1 ? "zi" : "zile"}`
                          : `răspuns: ${fmtDate(it.decided_at)}`}
                      </span>
                      {it.reminder_count > 0 && (
                        <span className="text-amber-400">⏰ {it.reminder_count} reminder{it.reminder_count > 1 ? "e" : ""}</span>
                      )}
                      {it.approval_status === "pending" && it.auto_reminders_stopped && (
                        <span className="text-red-400 inline-flex items-center gap-1"><BellOff className="w-3 h-3" /> auto-reminder oprit</span>
                      )}
                      {it.approval_status === "pending" && !it.auto_reminders_stopped && it.paused_until && (
                        <span className="text-blue-300 inline-flex items-center gap-1"><Pause className="w-3 h-3" /> pauză până {new Date(it.paused_until).toLocaleDateString("ro-RO")}</span>
                      )}
                      {it.approval_status === "pending" && (it.auto_reminders_fired_thresholds || []).length > 0 && !it.auto_reminders_stopped && (
                        <span className="text-emerald-400">🤖 {it.auto_reminders_fired_thresholds.length} auto</span>
                      )}
                    </div>
                    {/* Decision comment */}
                    {it.decision_comment && (
                      <div className="bg-stone-950 border-l-2 border-stone-700 rounded px-3 py-2 text-xs text-stone-400 italic mt-2">
                        "{it.decision_comment}"
                      </div>
                    )}
                  </div>
                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    {it.approval_url && (
                      <a
                        href={it.approval_url}
                        target="_blank"
                        rel="noreferrer"
                        title="Deschide link aprobare"
                        className="px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-stone-400 hover:text-white"
                        data-testid={`open-link-${it.report_id}`}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                    {onOpenProject && (
                      <button
                        onClick={() => onOpenProject(it.project_id)}
                        title="Deschide proiect"
                        className="px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-stone-400 hover:text-white"
                        data-testid={`open-project-${it.report_id}`}
                      >
                        📁
                      </button>
                    )}
                    {it.approval_status === "pending" && it.approval_url && (
                      <button
                        onClick={() => setSettingsFor(it)}
                        title="Auto-reminder settings"
                        className="px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-stone-400 hover:text-emerald-300"
                        data-testid={`settings-${it.report_id}`}
                      >
                        {it.auto_reminders_stopped ? <BellOff className="w-3.5 h-3.5" /> :
                          (it.paused_until ? <Pause className="w-3.5 h-3.5" /> : <Settings className="w-3.5 h-3.5" />)}
                      </button>
                    )}
                    {it.approval_status === "pending" && it.approval_url && (
                      <button
                        onClick={() => setReminderFor(it)}
                        className="px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-xs font-medium flex items-center gap-1.5"
                        data-testid={`send-reminder-${it.report_id}`}
                      >
                        <BellRing className="w-3.5 h-3.5" /> Reminder
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70] px-4 py-2 rounded-full bg-emerald-500 text-white text-sm shadow-2xl" data-testid="reminder-toast">
          {toast}
        </div>
      )}

      {/* Reminder modal */}
      {reminderFor && (
        <ReminderModal
          item={reminderFor}
          onClose={() => setReminderFor(null)}
          onSent={handleReminderSent}
        />
      )}

      {/* Auto-reminder settings modal */}
      {settingsFor && (
        <AutoReminderSettingsModal
          item={settingsFor}
          onClose={() => setSettingsFor(null)}
          onSaved={(_data) => {
            setSettingsFor(null);
            setToast("✓ Setări auto-reminder salvate");
            setTimeout(() => setToast(null), 3500);
            load();
          }}
        />
      )}
    </div>
  );
}
