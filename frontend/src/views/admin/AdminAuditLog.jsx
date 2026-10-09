// Audit Log — view all admin actions (CMS edits, user bans, setting changes, presets, etc.)
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Search, Download, RefreshCw, ChevronRight, Pin, PinOff } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const ACTION_META = {
  "cms.update": { color: "blue", icon: "📝", label: "CMS Editat" },
  "cms.reset": { color: "amber", icon: "↺", label: "CMS Resetat" },
  "cms.rollback": { color: "violet", icon: "⏪", label: "CMS Rollback" },
  "settings.update": { color: "violet", icon: "⚙️", label: "Setări actualizate" },
  "settings.rollback": { color: "violet", icon: "⏪", label: "Setări Rollback" },
  "user.update": { color: "blue", icon: "👤", label: "User editat" },
  "user.ban": { color: "red", icon: "🚫", label: "User banat" },
  "user.unban": { color: "emerald", icon: "✓", label: "User reactivat" },
  "trust_weights.update": { color: "amber", icon: "⭐", label: "Trust weights" },
  "trust_weights.rollback": { color: "violet", icon: "⏪", label: "Trust Rollback" },
  "preset.create": { color: "emerald", icon: "💾", label: "Preset creat" },
  "preset.delete": { color: "red", icon: "🗑️", label: "Preset șters" },
};

const COLOR_CLS = {
  blue: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
  violet: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
  red: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
  emerald: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
  slate: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "short", year: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
  catch { return iso; }
};

const formatDiff = (val) => {
  if (val === null || val === undefined) return "—";
  if (typeof val === "object") {
    try { return JSON.stringify(val, null, 2); } catch { return String(val); }
  }
  return String(val);
};

export const AdminAuditLog = () => {
  const [data, setData] = useState({ items: [], total: 0 });
  const [actions, setActions] = useState([]);
  const [filterAction, setFilterAction] = useState("");
  const [q, setQ] = useState("");
  const [expanded, setExpanded] = useState(null);
  const [loading, setLoading] = useState(false);
  const [skip, setSkip] = useState(0);
  const [rolling, setRolling] = useState(null);
  const [toast, setToast] = useState("");
  const [selected, setSelected] = useState([]); // up to 2 ids for diff compare
  const [showCompare, setShowCompare] = useState(false);
  const [pendingCompare, setPendingCompare] = useState(null); // [id1, id2] from URL ?compare=
  const [missingCompare, setMissingCompare] = useState(false); // shareable link entries not found
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [dateFilter, setDateFilter] = useState(null); // YYYY-MM-DD from heatmap navigation
  const [pinning, setPinning] = useState(null); // entry id being pinned/unpinned
  const [emailModal, setEmailModal] = useState(null); // { entry } when open
  const [emailRecipients, setEmailRecipients] = useState("");
  const [emailNote, setEmailNote] = useState("");
  const [emailSending, setEmailSending] = useState(false);
  const [presets, setPresets] = useState([]);
  const [activePresetId, setActivePresetId] = useState(null);
  const [showPresetForm, setShowPresetForm] = useState(false);
  const [newPresetName, setNewPresetName] = useState("");
  const [newPresetEmails, setNewPresetEmails] = useState("");
  const [presetSaving, setPresetSaving] = useState(false);
  const [statsModal, setStatsModal] = useState(null); // { preset } when open
  const [statsData, setStatsData] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const openStats = async (preset, ev) => {
    ev.stopPropagation();
    setStatsModal({ preset });
    setStatsData(null);
    setStatsLoading(true);
    try {
      const r = await axios.get(`${API}/admin/recipient-presets/${preset.id}/stats`);
      setStatsData(r.data);
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la încărcarea statisticilor"}`);
      setStatsModal(null);
    } finally {
      setStatsLoading(false);
    }
  };

  const loadPresets = () => {
    axios.get(`${API}/admin/recipient-presets`).then(r => setPresets(r.data.items || [])).catch(() => {});
  };

  const applyPreset = (p) => {
    // Merge with existing recipients (dedupe)
    const current = emailRecipients.split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
    const merged = [...current];
    for (const e of p.emails) {
      if (!merged.includes(e.toLowerCase())) merged.push(e);
    }
    setEmailRecipients(merged.join(", "));
    setActivePresetId(p.id);
  };

  const createPreset = async () => {
    if (!newPresetName.trim()) return;
    const emails = newPresetEmails.split(",").map(s => s.trim()).filter(Boolean);
    if (emails.length === 0) {
      flash("❌ Adaugă cel puțin un email");
      return;
    }
    setPresetSaving(true);
    try {
      const r = await axios.post(`${API}/admin/recipient-presets`, { name: newPresetName, emails });
      flash(`✓ Preset "${r.data.preset.name}" creat${r.data.invalid_emails?.length ? ` (${r.data.invalid_emails.length} email invalid ignorat)` : ""}`);
      setNewPresetName("");
      setNewPresetEmails("");
      setShowPresetForm(false);
      loadPresets();
      applyPreset(r.data.preset);
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la creare preset"}`);
    } finally {
      setPresetSaving(false);
    }
  };

  const deletePreset = async (preset, ev) => {
    ev.stopPropagation();
    if (!window.confirm(`Ștergi presetul "${preset.name}"?\nVa pierde și istoricul de ${preset.sent_count} trimiteri.`)) return;
    try {
      await axios.delete(`${API}/admin/recipient-presets/${preset.id}`);
      flash(`✓ Preset șters: ${preset.name}`);
      loadPresets();
      if (activePresetId === preset.id) setActivePresetId(null);
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la ștergere"}`);
    }
  };

  const sendEmailReport = async () => {
    if (!emailModal) return;
    const recipients = emailRecipients.split(",").map(s => s.trim()).filter(Boolean);
    if (recipients.length === 0) {
      flash("❌ Adaugă cel puțin un destinatar");
      return;
    }
    setEmailSending(true);
    try {
      const r = await axios.post(`${API}/admin/audit-log/${emailModal.entry.id}/email-report`, {
        recipients,
        note: emailNote,
        base_url: window.location.origin,
        preset_id: activePresetId,
      });
      const provider = r.data.provider;
      const invalid = r.data.invalid_recipients || [];
      let msg = r.data.demo
        ? `✓ Email simulat (provider: console — configurează RESEND_API_KEY pentru trimitere reală). Destinatari: ${r.data.recipients.length}`
        : `✓ Email trimis via ${provider} către ${r.data.recipients.length} destinatar(i)`;
      if (invalid.length) msg += ` · ${invalid.length} adresă(e) invalidă(e) ignorată(e)`;
      flash(msg);
      setEmailModal(null);
      setEmailRecipients("");
      setEmailNote("");
      setActivePresetId(null);
      loadPresets(); // refresh sent_count
      load();
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la trimiterea emailului"}`);
    } finally {
      setEmailSending(false);
    }
  };

  const togglePin = async (entry) => {
    let note = entry.pinned_note;
    if (!entry.pinned) {
      // Show prompt for optional context note when pinning (not when unpinning)
      const input = window.prompt(
        `📌 Marchezi această intrare ca anomalie/eveniment important.\n\nAdaugă o notă scurtă (opțional, max 240 caractere):\n\nEx: "Modificarea care a stricat producția pe 15 feb"`,
        ""
      );
      // null = cancelled
      if (input === null) return;
      note = (input || "").trim().slice(0, 240);
    } else if (!window.confirm("Demarchezi această intrare? Nota anexată va fi ștearsă.")) {
      return;
    }
    setPinning(entry.id);
    try {
      await axios.post(`${API}/admin/audit-log/${entry.id}/pin`, {
        pinned: !entry.pinned,
        note,
      });
      flash(entry.pinned ? "✓ Pin eliminat" : `📌 Intrare marcată${note ? ` cu nota: "${note.slice(0, 40)}${note.length > 40 ? "..." : ""}"` : ""}`);
      load();
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la pin"}`);
    } finally {
      setPinning(null);
    }
  };

  const toggleSelect = (id) => {
    setSelected(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 2) return [prev[1], id]; // FIFO drop oldest
      return [...prev, id];
    });
  };

  const flash = (m) => { setToast(m); setTimeout(() => setToast(""), 3500); };

  const doRollback = async (entry) => {
    if (!window.confirm(`Restaurezi starea anterioară pentru "${entry.target_label || entry.action}"?\n\nAceasta va crea o intrare nouă în audit log de tip "${entry.action}.rollback".`)) return;
    setRolling(entry.id);
    try {
      await axios.post(`${API}/admin/audit-log/${entry.id}/rollback`);
      flash(`✓ Restaurat cu succes: ${entry.target_label || entry.action}`);
      setExpanded(null);
      load();
    } catch (e) {
      flash(`❌ ${e?.response?.data?.detail || "Eroare la rollback"}`);
    } finally {
      setRolling(null);
    }
  };

  const load = () => {
    setLoading(true);
    const params = { limit: 100, skip };
    if (filterAction) params.action = filterAction;
    if (q) params.q = q;
    if (pinnedOnly) params.pinned = true;
    if (dateFilter) {
      params.date_from = `${dateFilter}T00:00:00`;
      params.date_to = `${dateFilter}T23:59:59.999Z`;
    }
    axios.get(`${API}/admin/audit-log`, { params })
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    axios.get(`${API}/admin/audit-log/actions`).then(r => setActions(r.data)).catch(() => {});
    // Parse ?compare=ID1,ID2 from URL for shareable diff links
    try {
      const sp = new URLSearchParams(window.location.search);
      const cmp = sp.get("compare");
      if (cmp) {
        const ids = cmp.split(",").map(s => s.trim()).filter(Boolean).slice(0, 2);
        if (ids.length === 2) setPendingCompare(ids);
      }
      const dt = sp.get("audit_date");
      if (dt && /^\d{4}-\d{2}-\d{2}$/.test(dt)) setDateFilter(dt);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { load(); }, [filterAction, skip, pinnedOnly, dateFilter]);

  // Auto-resolve shareable compare link once data is loaded
  useEffect(() => {
    if (!pendingCompare || data.items.length === 0) return;
    const [a, b] = pendingCompare;
    const foundA = data.items.find(i => i.id === a);
    const foundB = data.items.find(i => i.id === b);
    if (foundA && foundB) {
      setSelected([a, b]);
      setShowCompare(true);
      setPendingCompare(null);
      setMissingCompare(false);
    } else {
      // Try fetch directly (entries may be older than current page)
      Promise.all([
        axios.get(`${API}/admin/audit-log/${a}`).then(r => r.data).catch(() => null),
        axios.get(`${API}/admin/audit-log/${b}`).then(r => r.data).catch(() => null),
      ]).then(([eA, eB]) => {
        if (eA && eB) {
          // Inject into data.items so modal can find them
          setData(prev => ({ ...prev, items: [eA, eB, ...prev.items.filter(i => i.id !== a && i.id !== b)] }));
          setSelected([a, b]);
          setShowCompare(true);
          setMissingCompare(false);
        } else {
          setMissingCompare(true);
          flash("❌ Una sau ambele intrări din link-ul de compare nu au fost găsite (poate au fost șterse).");
        }
        setPendingCompare(null);
      });
    }
  }, [pendingCompare, data.items]);

  const onSearch = (e) => { e.preventDefault(); setSkip(0); load(); };

  return (
    <div className="space-y-4">
      <AdminCard>
        <form onSubmit={onSearch} className="flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Caută după actor, target, notă..."
              className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="audit-search"
            />
          </div>
          <select
            value={filterAction}
            onChange={e => { setFilterAction(e.target.value); setSkip(0); }}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="audit-action-filter"
          >
            <option value="">Toate acțiunile</option>
            {actions.map(a => (
              <option key={a.action} value={a.action}>
                {ACTION_META[a.action]?.label || a.action} ({a.count})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => { setPinnedOnly(!pinnedOnly); setSkip(0); }}
            className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors flex items-center gap-1.5 ${
              pinnedOnly
                ? "border-amber-400 bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:border-amber-500/50 dark:text-amber-300"
                : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            }`}
            data-testid="audit-pinned-only-toggle"
            title="Afișează doar intrările marcate (anomalii / momente importante)"
          >
            <Pin className="w-3.5 h-3.5" /> {pinnedOnly ? "Doar Pinned ✓" : "Doar Pinned"}
            {data.pinned_total > 0 && !pinnedOnly && (
              <span className="ml-1 text-[10px] bg-amber-500 text-white rounded-full px-1.5 py-0.5">{data.pinned_total}</span>
            )}
          </button>
          {dateFilter && (
            <button
              type="button"
              onClick={() => {
                setDateFilter(null);
                setSkip(0);
                try {
                  const url = new URL(window.location.href);
                  url.searchParams.delete("audit_date");
                  window.history.replaceState({}, "", url.toString());
                } catch { /* ignore */ }
              }}
              className="px-3 py-2 rounded-lg border border-orange-400 bg-orange-50 text-orange-700 dark:bg-orange-500/15 dark:border-orange-500/50 dark:text-orange-300 text-sm font-medium flex items-center gap-1.5"
              data-testid="audit-date-filter-clear"
              title="Click pentru a elimina filtrul de dată"
            >
              📅 {dateFilter} <span className="text-base leading-none ml-0.5">×</span>
            </button>
          )}
          <AdminBtn variant="ghost" type="button" onClick={load} data-testid="audit-refresh">
            <RefreshCw className="w-3.5 h-3.5 inline mr-1" /> Refresh
          </AdminBtn>
          <AdminBtn variant="secondary" type="button" onClick={() => window.open(`${API}/admin/audit-log/export.csv`, "_blank")} data-testid="audit-export-csv">
            <Download className="w-3.5 h-3.5 inline mr-1" /> CSV
          </AdminBtn>
          {selected.length === 2 && (
            <AdminBtn variant="primary" type="button" onClick={() => setShowCompare(true)} data-testid="audit-compare-btn">
              🔬 Compară selectate (2)
            </AdminBtn>
          )}
          {selected.length === 1 && (
            <span className="text-xs text-slate-500" data-testid="compare-hint">Selectează încă unul pentru compare</span>
          )}
        </form>
      </AdminCard>

      <AdminCard testid="audit-list-card">
        {toast && <div className="mb-3 text-sm font-medium text-emerald-600 dark:text-emerald-400" data-testid="audit-toast">{toast}</div>}
        {loading && <div className="text-center py-8 text-slate-500">Se încarcă...</div>}
        {!loading && data.items.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            Niciun eveniment în audit log{filterAction || q ? " pentru acest filtru" : ""}.
          </div>
        )}

        <div className="space-y-1.5">
          {data.items.map(e => {
            const meta = ACTION_META[e.action] || { color: "slate", icon: "•", label: e.action };
            const isOpen = expanded === e.id;
            const hasDetail = e.before || e.after || e.note;
            const isSelected = selected.includes(e.id);
            return (
              <div
                key={e.id}
                className={`rounded-lg border ${
                  isSelected
                    ? "border-amber-400 dark:border-amber-500/60 bg-amber-50 dark:bg-amber-500/10 ring-2 ring-amber-200 dark:ring-amber-500/30"
                    : e.pinned
                      ? "border-l-4 border-l-amber-500 border-amber-200 dark:border-amber-500/40 bg-amber-50/40 dark:bg-amber-500/5"
                      : isOpen ? "border-blue-200 dark:border-blue-500/30 bg-blue-50/30 dark:bg-blue-500/5" : "border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30"
                } transition-colors`}
                data-testid={`audit-row-${e.id}`}
              >
                <div className="flex items-stretch">
                  <label className="flex items-center justify-center pl-3 cursor-pointer shrink-0" title="Selectează pentru compare">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(e.id)}
                      className="w-4 h-4 accent-amber-500"
                      data-testid={`audit-select-${e.id}`}
                    />
                  </label>
                  <button
                    onClick={() => hasDetail && setExpanded(isOpen ? null : e.id)}
                    className="flex-1 flex items-center gap-3 p-3 text-left"
                    disabled={!hasDetail}
                  >
                    <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded-full shrink-0 ${COLOR_CLS[meta.color] || COLOR_CLS.slate}`}>
                      {meta.icon} {meta.label}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm flex items-center gap-1.5 flex-wrap">
                        <span className="font-medium">{e.actor_name || "Sistem"}</span>
                        <span className="text-slate-500">a modificat</span>
                        <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{e.target_label || e.target_type || "—"}</span>
                        {e.pinned && (
                          <span className="inline-flex items-center gap-0.5 text-[10px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded-full bg-amber-500 text-white" title={e.pinned_note || "Marcat ca anomalie"}>
                            <Pin className="w-2.5 h-2.5" /> PIN
                          </span>
                        )}
                      </div>
                      {e.pinned && e.pinned_note && (
                        <div className="text-xs text-amber-700 dark:text-amber-300 mt-0.5 italic flex items-start gap-1" data-testid={`audit-pin-note-${e.id}`}>
                          <span>📌</span><span className="truncate">{e.pinned_note}</span>
                        </div>
                      )}
                      <div className="text-[11px] text-slate-500 mt-0.5">{fmtTime(e.created_at)} · {e.actor_email}</div>
                    </div>
                    {hasDetail && (
                      <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform shrink-0 ${isOpen ? "rotate-90" : ""}`} />
                    )}
                  </button>
                  <button
                    onClick={(ev) => { ev.stopPropagation(); togglePin(e); }}
                    disabled={pinning === e.id}
                    className={`shrink-0 px-3 flex items-center justify-center border-l ${
                      e.pinned
                        ? "text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/30 hover:bg-amber-100/50 dark:hover:bg-amber-500/10"
                        : "text-slate-400 hover:text-amber-600 border-slate-100 dark:border-slate-800 hover:bg-amber-50 dark:hover:bg-amber-500/5"
                    } disabled:opacity-50 transition-colors`}
                    title={e.pinned ? "Demarchează" : "Marchează ca anomalie / moment important"}
                    data-testid={`audit-pin-${e.id}`}
                  >
                    {pinning === e.id ? (
                      <span className="text-xs">...</span>
                    ) : e.pinned ? (
                      <PinOff className="w-4 h-4" />
                    ) : (
                      <Pin className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {isOpen && hasDetail && (
                  <div className="px-3 pb-3 pt-1 border-t border-slate-100 dark:border-slate-800" data-testid={`audit-detail-${e.id}`}>
                    {e.pinned && (
                      <div className="mb-3 p-2 rounded-lg bg-amber-100/60 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 text-xs flex items-start gap-2" data-testid={`audit-pin-detail-${e.id}`}>
                        <Pin className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-amber-800 dark:text-amber-300">Marcat ca anomalie / moment important</div>
                          {e.pinned_note && <div className="italic text-amber-700 dark:text-amber-200 mt-0.5">"{e.pinned_note}"</div>}
                          <div className="text-[10px] text-amber-600/80 dark:text-amber-400/80 mt-0.5">de {e.pinned_by_name || "—"} · {fmtTime(e.pinned_at)}</div>
                        </div>
                        <button
                          onClick={(ev) => {
                            ev.stopPropagation();
                            const url = `${API}/admin/audit-log/${e.id}/incident-report.pdf?base_url=${encodeURIComponent(window.location.origin)}`;
                            window.open(url, "_blank");
                          }}
                          className="shrink-0 text-[11px] font-semibold px-2.5 py-1.5 rounded-md bg-amber-500 hover:bg-amber-600 text-white transition-colors flex items-center gap-1"
                          data-testid={`audit-pdf-${e.id}`}
                          title="Generează raport PDF cu diff, notă incident și QR code. Ideal pentru audituri ISO/SOC2, board meetings, post-mortems."
                        >
                          📄 Raport PDF
                        </button>
                        <button
                          onClick={(ev) => {
                            ev.stopPropagation();
                            setEmailModal({ entry: e });
                            setEmailRecipients("");
                            setEmailNote("");
                            setActivePresetId(null);
                            setShowPresetForm(false);
                            loadPresets();
                          }}
                          className="shrink-0 text-[11px] font-semibold px-2.5 py-1.5 rounded-md bg-slate-800 dark:bg-slate-700 hover:bg-slate-900 dark:hover:bg-slate-600 text-white transition-colors flex items-center gap-1"
                          data-testid={`audit-email-${e.id}`}
                          title="Trimite raportul PDF prin email către legal, compliance sau echipa de incident response. One-click compliance forwarding."
                        >
                          📧 Email raport
                        </button>
                      </div>
                    )}
                    <div className="grid md:grid-cols-2 gap-3">
                      {e.before && (
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-red-600 dark:text-red-400 font-bold mb-1">Înainte</div>
                          <pre className="bg-red-50 dark:bg-red-500/5 border border-red-100 dark:border-red-500/20 rounded-lg p-2 text-[11px] font-mono overflow-x-auto max-h-48">{formatDiff(e.before)}</pre>
                        </div>
                      )}
                      {e.after && (
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-bold mb-1">După</div>
                          <pre className="bg-emerald-50 dark:bg-emerald-500/5 border border-emerald-100 dark:border-emerald-500/20 rounded-lg p-2 text-[11px] font-mono overflow-x-auto max-h-48">{formatDiff(e.after)}</pre>
                        </div>
                      )}
                      {e.note && <div className="md:col-span-2 text-xs italic text-slate-600 dark:text-slate-300">📝 {e.note}</div>}
                    </div>
                    {e.rollbackable && e.before && (
                      <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 flex-wrap">
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          💡 Poți reveni la starea anterioară cu un singur click.
                        </div>
                        <AdminBtn
                          variant="primary"
                          onClick={() => doRollback(e)}
                          disabled={rolling === e.id}
                          data-testid={`audit-rollback-${e.id}`}
                        >
                          {rolling === e.id ? "Se restaurează..." : "↺ Restaurează valoarea anterioară"}
                        </AdminBtn>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {data.total > 0 && (
          <div className="flex justify-between items-center pt-4 mt-2 text-sm">
            <div className="text-slate-500">Total: <b>{data.total}</b> evenimente</div>
            <div className="flex gap-2">
              <AdminBtn variant="secondary" onClick={() => setSkip(Math.max(0, skip - 100))} disabled={skip === 0}>← Anterior</AdminBtn>
              <AdminBtn variant="secondary" onClick={() => setSkip(skip + 100)} disabled={skip + 100 >= data.total}>Următor →</AdminBtn>
            </div>
          </div>
        )}
      </AdminCard>

      {showCompare && selected.length === 2 && (
        <CompareDiffModal
          entryA={data.items.find(i => i.id === selected[0])}
          entryB={data.items.find(i => i.id === selected[1])}
          onClose={() => {
            setShowCompare(false);
            // Strip ?compare= from URL so refresh doesn't auto-reopen
            try {
              const url = new URL(window.location.href);
              if (url.searchParams.has("compare")) {
                url.searchParams.delete("compare");
                window.history.replaceState({}, "", url.toString());
              }
            } catch { /* ignore */ }
          }}
          onClear={() => {
            setSelected([]);
            setShowCompare(false);
            try {
              const url = new URL(window.location.href);
              url.searchParams.delete("compare");
              window.history.replaceState({}, "", url.toString());
            } catch { /* ignore */ }
          }}
          onCopiedLink={() => flash("✓ Link copiat în clipboard — îl poți trimite oricui are acces admin.")}
        />
      )}
      {statsModal && (
        <StatsPresetModal
          preset={statsModal.preset}
          data={statsData}
          loading={statsLoading}
          onClose={() => setStatsModal(null)}
          fmtTime={fmtTime}
        />
      )}
      {emailModal && (
        <div className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => !emailSending && setEmailModal(null)}>
          <div
            className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-lg w-full p-6"
            onClick={ev => ev.stopPropagation()}
            data-testid="email-report-modal"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">📧 Email raport incident</h3>
                <p className="text-xs text-slate-500 mt-1">Trimite PDF-ul cu raportul către legal, compliance sau orice destinatar relevant.</p>
              </div>
              <button onClick={() => !emailSending && setEmailModal(null)} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">×</button>
            </div>

            <div className="mb-3 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-xs">
              <div className="font-semibold text-slate-700 dark:text-slate-300 mb-0.5">Intrare:</div>
              <div className="text-slate-600 dark:text-slate-400">
                <span className="font-mono">{emailModal.entry.action}</span> · {emailModal.entry.target_label || emailModal.entry.target_type}
              </div>
              {emailModal.entry.pinned_note && (
                <div className="text-amber-700 dark:text-amber-300 italic mt-1">📌 "{emailModal.entry.pinned_note}"</div>
              )}
            </div>

            <label className="block mb-1">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Destinatari <span className="text-slate-500 font-normal">(separate prin virgulă, max 10)</span>
              </span>
            </label>

            {/* Preset chips */}
            {(presets.length > 0 || true) && (
              <div className="mb-3" data-testid="preset-chips">
                <div className="flex flex-wrap gap-1.5 items-center">
                  {presets.map(p => {
                    const active = activePresetId === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => applyPreset(p)}
                        className={`group text-[11px] font-medium px-2.5 py-1 rounded-full border transition-colors flex items-center gap-1 ${
                          active
                            ? "bg-amber-100 dark:bg-amber-500/20 border-amber-400 dark:border-amber-500/60 text-amber-800 dark:text-amber-200"
                            : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-amber-300 dark:hover:border-amber-500/40 hover:bg-amber-50/50 dark:hover:bg-amber-500/5"
                        }`}
                        title={`${p.emails.join(", ")} · trimis ${p.sent_count}x`}
                        data-testid={`preset-chip-${p.id}`}
                      >
                        <span>{p.name}</span>
                        <span className="text-[9px] opacity-60">({p.emails.length})</span>
                        {p.sent_count > 0 && (
                          <span className="text-[9px] bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full px-1.5 py-0.5 -mr-1">{p.sent_count}↑</span>
                        )}
                        <span
                          onClick={(ev) => openStats(p, ev)}
                          className="opacity-0 group-hover:opacity-60 hover:!opacity-100 hover:text-blue-500 text-[11px] leading-none ml-0.5"
                          title="Vezi statistici trimiteri"
                          data-testid={`preset-stats-${p.id}`}
                        >📊</span>
                        <span
                          onClick={(ev) => deletePreset(p, ev)}
                          className="opacity-0 group-hover:opacity-60 hover:!opacity-100 hover:text-red-500 text-[11px] leading-none ml-0.5"
                          title="Șterge preset"
                          data-testid={`preset-delete-${p.id}`}
                        >×</span>
                      </button>
                    );
                  })}
                  <button
                    type="button"
                    onClick={() => setShowPresetForm(!showPresetForm)}
                    className="text-[11px] font-medium px-2.5 py-1 rounded-full border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 hover:border-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                    data-testid="preset-new-toggle"
                  >
                    {showPresetForm ? "× anulează" : "+ Preset nou"}
                  </button>
                </div>

                {showPresetForm && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5" data-testid="preset-new-form">
                    <input
                      type="text"
                      value={newPresetName}
                      onChange={ev => setNewPresetName(ev.target.value)}
                      placeholder="Nume preset (ex: Compliance Team, Board)"
                      className="w-full px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs"
                      data-testid="preset-new-name"
                      maxLength={80}
                    />
                    <input
                      type="text"
                      value={newPresetEmails}
                      onChange={ev => setNewPresetEmails(ev.target.value)}
                      placeholder="emails separate prin virgulă (ex: legal@..., dpo@...)"
                      className="w-full px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
                      data-testid="preset-new-emails"
                    />
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={createPreset}
                        disabled={presetSaving || !newPresetName.trim() || !newPresetEmails.trim()}
                        className="text-[11px] font-semibold px-2.5 py-1 rounded-md bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50 transition-colors"
                        data-testid="preset-new-save"
                      >
                        {presetSaving ? "Se salvează..." : "Salvează & aplică"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <label className="block mb-3">
              <input
                type="text"
                value={emailRecipients}
                onChange={ev => { setEmailRecipients(ev.target.value); setActivePresetId(null); }}
                placeholder="legal@firma.ro, compliance@firma.ro"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-mono"
                data-testid="email-recipients-input"
                disabled={emailSending}
              />
            </label>

            <label className="block mb-4">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Notă admin <span className="text-slate-500 font-normal">(opțional — va apărea în corpul emailului)</span>
              </span>
              <textarea
                value={emailNote}
                onChange={ev => setEmailNote(ev.target.value)}
                placeholder="Ex: Pentru review urgent — modificarea a fost discutată în meetingul de azi."
                rows={3}
                maxLength={500}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm resize-none"
                data-testid="email-note-input"
                disabled={emailSending}
              />
            </label>

            <div className="text-[11px] text-slate-500 dark:text-slate-400 mb-4 p-2 rounded-md bg-blue-50/50 dark:bg-blue-500/5 border border-blue-100 dark:border-blue-500/20">
              ℹ️ Email-ul va include PDF-ul complet ca atașament, plus diff before/after, nota incident și QR code spre intrare live.
              <br/>Dacă <code className="font-mono">RESEND_API_KEY</code> nu e configurat, emailul va fi simulat (logat în consolă).
            </div>

            <div className="flex justify-end gap-2">
              <AdminBtn variant="secondary" onClick={() => setEmailModal(null)} disabled={emailSending} data-testid="email-cancel">Anulează</AdminBtn>
              <AdminBtn variant="primary" onClick={sendEmailReport} disabled={emailSending || !emailRecipients.trim()} data-testid="email-send">
                {emailSending ? "Se trimite..." : "📨 Trimite email"}
              </AdminBtn>
            </div>
          </div>
        </div>
      )}
      {missingCompare && (
        <div className="fixed bottom-4 right-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-300 text-sm px-4 py-2 rounded-lg shadow-lg" data-testid="compare-missing-banner">
          ⚠️ Link de compare invalid — intrările nu mai există.
        </div>
      )}
    </div>
  );
};

// ============= LINE-BY-LINE DIFF (LCS) =============
// GitHub-style side-by-side diff. Returns array of rows: { type, leftNo, left, rightNo, right }
const computeLineDiff = (a, b) => {
  const linesA = String(a ?? "").split("\n");
  const linesB = String(b ?? "").split("\n");
  const m = linesA.length, n = linesB.length;
  // Build LCS DP table
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = linesA[i] === linesB[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const rows = [];
  let i = 0, j = 0, li = 1, lj = 1;
  while (i < m && j < n) {
    if (linesA[i] === linesB[j]) {
      rows.push({ type: "eq", leftNo: li++, left: linesA[i], rightNo: lj++, right: linesB[j] });
      i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      rows.push({ type: "del", leftNo: li++, left: linesA[i], rightNo: null, right: null });
      i++;
    } else {
      rows.push({ type: "add", leftNo: null, left: null, rightNo: lj++, right: linesB[j] });
      j++;
    }
  }
  while (i < m) rows.push({ type: "del", leftNo: li++, left: linesA[i++], rightNo: null, right: null });
  while (j < n) rows.push({ type: "add", leftNo: null, left: null, rightNo: lj++, right: linesB[j++] });
  return rows;
};

const LineDiffView = ({ left, right }) => {
  // Normalize: if object → JSON pretty
  const normalize = (v) => {
    if (v === null || v === undefined) return "";
    if (typeof v === "object") { try { return JSON.stringify(v, null, 2); } catch { return String(v); } }
    return String(v);
  };
  const rows = computeLineDiff(normalize(left), normalize(right));
  const stats = rows.reduce((acc, r) => {
    if (r.type === "add") acc.add++;
    else if (r.type === "del") acc.del++;
    return acc;
  }, { add: 0, del: 0 });

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden" data-testid="line-diff-view">
      <div className="px-3 py-2 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 text-[11px] flex items-center gap-3">
        <span className="text-emerald-600 dark:text-emerald-400 font-bold">+{stats.add}</span>
        <span className="text-red-600 dark:text-red-400 font-bold">−{stats.del}</span>
        <span className="text-slate-500">linii modificate</span>
      </div>
      <div className="overflow-auto max-h-[55vh]">
        <table className="w-full text-xs font-mono">
          <tbody>
            {rows.map((r, idx) => {
              const bg = r.type === "add" ? "bg-emerald-50 dark:bg-emerald-500/10"
                : r.type === "del" ? "bg-red-50 dark:bg-red-500/10"
                : "";
              const leftBg = r.type === "del" ? "bg-red-100/60 dark:bg-red-500/15" : r.type === "add" ? "" : "";
              const rightBg = r.type === "add" ? "bg-emerald-100/60 dark:bg-emerald-500/15" : r.type === "del" ? "" : "";
              return (
                <tr key={idx} className={bg}>
                  <td className="w-10 px-2 py-0.5 text-right text-slate-400 select-none border-r border-slate-100 dark:border-slate-800 align-top">{r.leftNo ?? ""}</td>
                  <td className={`px-2 py-0.5 whitespace-pre-wrap break-all border-r border-slate-100 dark:border-slate-800 align-top ${leftBg}`}>
                    {r.type === "del" && <span className="text-red-600 dark:text-red-400 mr-1">−</span>}
                    {r.left ?? <span className="text-slate-300"> </span>}
                  </td>
                  <td className="w-10 px-2 py-0.5 text-right text-slate-400 select-none border-r border-slate-100 dark:border-slate-800 align-top">{r.rightNo ?? ""}</td>
                  <td className={`px-2 py-0.5 whitespace-pre-wrap break-all align-top ${rightBg}`}>
                    {r.type === "add" && <span className="text-emerald-600 dark:text-emerald-400 mr-1">+</span>}
                    {r.right ?? <span className="text-slate-300"> </span>}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr><td colSpan={4} className="text-center py-6 text-slate-400 italic">Conținut identic — nicio diferență detectată.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============= COMPARE DIFF MODAL =============
const CompareDiffModal = ({ entryA, entryB, onClose, onClear, onCopiedLink }) => {
  const [view, setView] = useState("auto"); // auto | lines | keys
  const [linkCopied, setLinkCopied] = useState(false);
  if (!entryA || !entryB) return null;
  // Order chronologically: older = A, newer = B
  const [older, newer] = (new Date(entryA.created_at) <= new Date(entryB.created_at))
    ? [entryA, entryB] : [entryB, entryA];

  // Smart compare: prefer "after" of each (final state after that action)
  // If action was a reset/delete → use "before" (what existed before reset)
  const stateOf = (e) => {
    if (e.action === "cms.reset") return e.before;
    return e.after || e.before;
  };

  const olderState = stateOf(older);
  const newerState = stateOf(newer);

  // Compute key-level diff if both are objects
  const isObjA = olderState && typeof olderState === "object";
  const isObjB = newerState && typeof newerState === "object";
  const bothObjects = isObjA && isObjB;
  const keys = bothObjects
    ? Array.from(new Set([...Object.keys(olderState), ...Object.keys(newerState)]))
    : null;

  // Decide which view to render
  const effectiveView = view === "auto" ? (bothObjects ? "keys" : "lines") : view;

  const sameTarget = entryA.target_id === entryB.target_id && entryA.target_type === entryB.target_type;

  return (
    <div className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-5xl w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={e => e.stopPropagation()}
        data-testid="compare-modal"
      >
        <div className="flex items-start justify-between mb-4 gap-4">
          <div>
            <h3 className="text-lg font-semibold">🔬 Diff Compare</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {sameTarget
                ? <>Aceeași țintă: <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{entryA.target_label}</span></>
                : <>⚠️ Țintele sunt diferite — compararea poate fi mai puțin relevantă.</>
              }
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">×</button>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <ColumnHeader entry={older} role="Mai vechi" tone="red" />
          <ColumnHeader entry={newer} role="Mai nou" tone="emerald" />
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 mb-3 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg w-fit" data-testid="compare-view-toggle">
          {bothObjects && (
            <button
              onClick={() => setView("keys")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${effectiveView === "keys" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm" : "text-slate-600 dark:text-slate-400"}`}
              data-testid="view-keys"
            >📋 Tabel câmpuri</button>
          )}
          <button
            onClick={() => setView("lines")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${effectiveView === "lines" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm" : "text-slate-600 dark:text-slate-400"}`}
            data-testid="view-lines"
          >📄 Diff linie cu linie</button>
        </div>

        {effectiveView === "keys" && keys ? (
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden" data-testid="compare-table">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/50">
                <tr>
                  <th className="text-left py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-bold">Câmp</th>
                  <th className="text-left py-2 px-3 text-[10px] uppercase tracking-wider text-red-600 dark:text-red-400 font-bold">Mai vechi</th>
                  <th className="text-left py-2 px-3 text-[10px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-bold">Mai nou</th>
                </tr>
              </thead>
              <tbody>
                {keys.map(k => {
                  const v1 = (olderState || {})[k];
                  const v2 = (newerState || {})[k];
                  const changed = JSON.stringify(v1) !== JSON.stringify(v2);
                  return (
                    <tr key={k} className={`border-t border-slate-100 dark:border-slate-800/50 ${changed ? "bg-amber-50/40 dark:bg-amber-500/5" : ""}`}>
                      <td className="py-2 px-3 font-mono text-xs">{k}{changed && <span className="ml-1 text-[9px] text-amber-600 dark:text-amber-400">●</span>}</td>
                      <td className="py-2 px-3 font-mono text-xs text-slate-700 dark:text-slate-300 break-all">{v1 === undefined ? <em className="text-slate-400">— absent —</em> : typeof v1 === "object" ? JSON.stringify(v1) : String(v1)}</td>
                      <td className="py-2 px-3 font-mono text-xs text-slate-700 dark:text-slate-300 break-all">{v2 === undefined ? <em className="text-slate-400">— absent —</em> : typeof v2 === "object" ? JSON.stringify(v2) : String(v2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="px-3 py-2 bg-slate-50 dark:bg-slate-800/50 text-[11px] text-slate-500 border-t border-slate-200 dark:border-slate-700">
              Rândurile cu <span className="text-amber-600 dark:text-amber-400">●</span> au valoare diferită între cele 2 momente.
            </div>
          </div>
        ) : (
          <LineDiffView left={olderState} right={newerState} />
        )}

        <div className="flex justify-between items-center gap-2 mt-5 flex-wrap">
          <button
            onClick={async () => {
              const url = `${window.location.origin}${window.location.pathname}?compare=${entryA.id},${entryB.id}`;
              try {
                await navigator.clipboard.writeText(url);
              } catch {
                // Fallback for browsers without clipboard API
                const ta = document.createElement("textarea");
                ta.value = url;
                document.body.appendChild(ta);
                ta.select();
                try { document.execCommand("copy"); } catch { /* ignore */ }
                document.body.removeChild(ta);
              }
              setLinkCopied(true);
              setTimeout(() => setLinkCopied(false), 2500);
              if (onCopiedLink) onCopiedLink();
            }}
            className="text-xs font-medium px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5"
            data-testid="compare-copy-link"
            title="Generează un URL permanent care deschide automat acest compare. Util pentru investitori, auditori, sau colegi de echipă."
          >
            {linkCopied ? <>✓ Copiat!</> : <>🔗 Copiază link Diff</>}
          </button>
          <div className="flex gap-2">
            <AdminBtn variant="secondary" onClick={onClear} data-testid="compare-clear">Deselectează & închide</AdminBtn>
            <AdminBtn variant="primary" onClick={onClose} data-testid="compare-close">Închide</AdminBtn>
          </div>
        </div>
      </div>
    </div>
  );
};

const ColumnHeader = ({ entry, role, tone }) => {
  const meta = ACTION_META[entry.action] || { icon: "•", label: entry.action, color: "slate" };
  const tones = {
    red: "border-red-200 dark:border-red-500/30 bg-red-50/50 dark:bg-red-500/5",
    emerald: "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-500/5",
  };
  return (
    <div className={`p-3 rounded-xl border ${tones[tone]}`}>
      <div className="text-[10px] uppercase tracking-wider font-bold opacity-70 mb-1">{role}</div>
      <div className="text-sm font-medium">{meta.icon} {meta.label}</div>
      <div className="text-[11px] text-slate-500 mt-0.5">{entry.actor_name} · {fmtTime(entry.created_at)}</div>
    </div>
  );
};


// ============= STATS PER PRESET MODAL =============
const MONTH_LABELS_RO = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Noi", "Dec"];

const StatsPresetModal = ({ preset, data, loading, onClose, fmtTime }) => {
  const maxCount = data?.months?.length ? Math.max(...data.months.map(m => m.count)) : 0;

  return (
    <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={e => e.stopPropagation()}
        data-testid="stats-preset-modal"
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">📊 Statistici · {preset.name}</h3>
            <p className="text-xs text-slate-500 mt-1">Cadența de incident response pe ultimele luni · {preset.emails.length} destinatari în preset</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl leading-none" data-testid="stats-close">×</button>
        </div>

        {loading && <div className="text-center py-12 text-slate-500" data-testid="stats-loading">Se încarcă...</div>}

        {!loading && data && (
          <>
            {/* Top KPIs */}
            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800" data-testid="stats-kpi-total">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Total trimiteri</div>
                <div className="text-2xl font-semibold text-slate-900 dark:text-white">{data.total_sends}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Prima trimitere</div>
                <div className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-1">{data.first_send ? fmtTime(data.first_send) : <span className="text-slate-400">—</span>}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Ultima trimitere</div>
                <div className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-1">{data.last_send ? fmtTime(data.last_send) : <span className="text-slate-400">—</span>}</div>
              </div>
            </div>

            {/* Monthly bar chart (CSS-only) */}
            <div className="mb-5 p-4 rounded-xl border border-slate-200 dark:border-slate-800" data-testid="stats-monthly-chart">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold">Trimiteri pe lună</h4>
                <span className="text-[10px] text-slate-500">Ultimele {data.window_days} zile</span>
              </div>
              {data.months.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm italic">Nicio trimitere încă</div>
              ) : (
                <div className="flex items-end gap-2 h-32">
                  {data.months.map(m => {
                    const heightPct = maxCount > 0 ? (m.count / maxCount) * 100 : 0;
                    const [year, mon] = m.month.split("-");
                    return (
                      <div key={m.month} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                        <div className="text-[10px] text-slate-500 font-mono">{m.count > 0 ? m.count : ""}</div>
                        <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-md relative flex-1 flex items-end overflow-hidden">
                          <div
                            className={`w-full rounded-md transition-all ${m.count > 0 ? "bg-gradient-to-t from-amber-500 to-amber-300 dark:from-amber-600 dark:to-amber-400" : ""}`}
                            style={{ height: `${heightPct}%`, minHeight: m.count > 0 ? "4px" : "0" }}
                            title={`${m.count} trimitere(i), ${m.recipients} destinatari în total`}
                          />
                        </div>
                        <div className="text-[10px] text-slate-500 font-medium">{MONTH_LABELS_RO[parseInt(mon, 10) - 1]}</div>
                        <div className="text-[9px] text-slate-400">{year.slice(2)}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Recent sends list */}
            <div className="mb-2">
              <h4 className="text-sm font-semibold mb-2">Istoric recent (ultimele {data.recent_sends.length})</h4>
              {data.recent_sends.length === 0 ? (
                <div className="text-center py-6 text-slate-400 text-sm italic border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  Nicio trimitere nu a fost înregistrată pentru acest preset.
                  <br/><span className="text-[11px]">(trimiterile anterioare implementării acestui feature nu apar)</span>
                </div>
              ) : (
                <div className="space-y-1.5" data-testid="stats-recent-list">
                  {data.recent_sends.map((r, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-2 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                      <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400 shrink-0">
                        {r.action}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{r.target_label || "—"}</div>
                        <div className="text-[11px] text-slate-500">
                          {fmtTime(r.sent_at)} · {r.sent_by_name || "—"} · <span className="font-semibold">{r.recipient_count}</span> destinatar(i) via {r.provider}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
