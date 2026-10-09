// Admin Demo Leads panel — manage leads captured from "Book a Demo" form.
import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Inbox, RefreshCw, Mail, Phone, MessageCircle, Trash2, ChevronDown, ExternalLink,
  CheckCircle2, Clock, XCircle, Calendar
} from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const STATUS_META = {
  new: { label: "Nou", color: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300", icon: Inbox },
  contacted: { label: "Contactat", color: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300", icon: Clock },
  scheduled: { label: "Programat", color: "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300", icon: Calendar },
  closed_won: { label: "Câștigat", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300", icon: CheckCircle2 },
  closed_lost: { label: "Pierdut", color: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300", icon: XCircle },
};

const STATUSES = ["new", "contacted", "scheduled", "closed_won", "closed_lost"];

const Stat = ({ label, value, color }) => (
  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-2.5">
    <div className={`text-2xl font-semibold ${color || "text-slate-900 dark:text-slate-100"}`}>{value}</div>
    <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">{label}</div>
  </div>
);

export const AdminDemoLeads = () => {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [notesDraft, setNotesDraft] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/demo-leads`, { params: { status: filter || undefined } });
      setItems(r.data?.items || []);
      setCounts(r.data?.counts || null);
    } catch {/* ignore */} finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

  const setStatus = async (id, status) => {
    try {
      await axios.patch(`${API}/admin/demo-leads/${id}`, { status });
      await load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const saveNotes = async (id) => {
    const notes = notesDraft[id];
    try {
      await axios.patch(`${API}/admin/demo-leads/${id}`, { notes });
      setNotesDraft(prev => ({ ...prev, [id]: undefined }));
      await load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Șterg definitiv acest lead?")) return;
    try {
      await axios.delete(`${API}/admin/demo-leads/${id}`);
      await load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    }
  };

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><Inbox className="w-4 h-4 text-blue-500" /> Demo Leads</div>}
      action={<AdminBtn variant="secondary" onClick={load}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></AdminBtn>}
    >
      {counts && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
          <Stat label="Total" value={counts.total || 0} />
          <Stat label="Noi" value={counts.new || 0} color="text-blue-600 dark:text-blue-400" />
          <Stat label="Contactați" value={counts.contacted || 0} color="text-amber-600 dark:text-amber-400" />
          <Stat label="Programați" value={counts.scheduled || 0} color="text-purple-600 dark:text-purple-400" />
          <Stat label="Câștigați" value={counts.closed_won || 0} color="text-emerald-600 dark:text-emerald-400" />
          <Stat label="Pierduți" value={counts.closed_lost || 0} color="text-red-600 dark:text-red-400" />
        </div>
      )}

      <div className="flex items-center gap-2 mb-3 flex-wrap text-xs">
        {[{ id: "", label: "Toate" }, ...STATUSES.map(s => ({ id: s, label: STATUS_META[s].label }))].map(f => (
          <button
            key={f.id || "all"}
            onClick={() => setFilter(f.id)}
            className={`px-2.5 py-1 rounded-full font-medium border ${
              filter === f.id
                ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
            }`}
            data-testid={`leads-filter-${f.id || "all"}`}
          >{f.label}</button>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm italic">Niciun lead în această categorie.</div>
      ) : (
        <div className="space-y-2" data-testid="demo-leads-list">
          {items.map(lead => {
            const status = lead.status || "new";
            const meta = STATUS_META[status] || STATUS_META.new;
            const Icon = meta.icon;
            const expanded = expandedId === lead._id;
            const draftNote = notesDraft[lead._id] ?? lead.notes ?? "";
            return (
              <div key={lead._id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/40" data-testid={`lead-${lead._id}`}>
                <div className="p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{lead.name}</span>
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold ${meta.color}`}>
                          <Icon className="w-2.5 h-2.5" /> {meta.label}
                        </span>
                        {lead.company && <span className="text-xs text-slate-500">@ {lead.company}</span>}
                        {lead.role && <span className="text-xs text-slate-400">· {lead.role}</span>}
                        <span className="ml-auto text-[10px] text-slate-400">{lead.created_at ? new Date(lead.created_at).toLocaleString("ro-RO") : ""}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <a href={`mailto:${lead.email}`} className="inline-flex items-center gap-1 text-slate-600 dark:text-slate-300 hover:text-blue-600" data-testid={`lead-email-${lead._id}`}>
                          <Mail className="w-3 h-3" /> {lead.email}
                        </a>
                        {lead.whatsapp_link && (
                          <a href={lead.whatsapp_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[#25d366] hover:underline" data-testid={`lead-wa-${lead._id}`}>
                            <MessageCircle className="w-3 h-3" /> WhatsApp <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                        {!lead.whatsapp_link && lead.whatsapp && (
                          <span className="inline-flex items-center gap-1 text-slate-500"><Phone className="w-3 h-3" /> {lead.whatsapp}</span>
                        )}
                      </div>
                      {lead.message && !expanded && (
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 italic line-clamp-1">"{lead.message}"</div>
                      )}
                    </div>
                    <button
                      onClick={() => setExpandedId(expanded ? null : lead._id)}
                      className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 shrink-0"
                      data-testid={`lead-expand-${lead._id}`}
                    >
                      <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>

                  {expanded && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3">
                      {lead.message && (
                        <div>
                          <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">Mesaj original</div>
                          <div className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap bg-slate-50 dark:bg-slate-800/50 rounded p-2.5">{lead.message}</div>
                        </div>
                      )}
                      <div>
                        <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">Schimbă status</div>
                        <div className="flex flex-wrap gap-1.5">
                          {STATUSES.map(s => {
                            const m = STATUS_META[s];
                            const SI = m.icon;
                            const active = status === s;
                            return (
                              <button
                                key={s}
                                onClick={() => setStatus(lead._id, s)}
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium ${active ? m.color + " ring-2 ring-offset-1 ring-blue-400 dark:ring-offset-slate-900" : "bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100"}`}
                                data-testid={`lead-status-${lead._id}-${s}`}
                              >
                                <SI className="w-3 h-3" /> {m.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">Notițe interne</div>
                        <textarea
                          rows={2}
                          value={draftNote}
                          onChange={(e) => setNotesDraft(prev => ({ ...prev, [lead._id]: e.target.value }))}
                          placeholder="ex: am sunat, e interesat de tier-ul Pro, follow-up vineri..."
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                          data-testid={`lead-notes-${lead._id}`}
                        />
                        <div className="flex justify-end gap-1.5 mt-1.5">
                          <button onClick={() => remove(lead._id)} className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10" data-testid={`lead-delete-${lead._id}`}>
                            <Trash2 className="w-3 h-3" /> Șterge
                          </button>
                          <button onClick={() => saveNotes(lead._id)} disabled={draftNote === (lead.notes || "")} className="text-[11px] px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-30" data-testid={`lead-save-${lead._id}`}>
                            Salvează notițe
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AdminCard>
  );
};

export default AdminDemoLeads;
