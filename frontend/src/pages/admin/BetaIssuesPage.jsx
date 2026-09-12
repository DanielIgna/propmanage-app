import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { ClipboardList, Loader2, Plus, Bug, Lightbulb, MessageSquare, RefreshCcw } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const SEV_STYLE = {
  P0: "bg-red-500/15 text-red-300 border-red-500/40",
  P1: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  P2: "bg-sky-500/15 text-sky-300 border-sky-500/40",
  P3: "bg-white/5 text-stone-400 border-white/10",
};
const STATUS_LABEL = {
  new: "Nou", triaged: "Triat", in_progress: "În lucru",
  fixed: "Rezolvat", shipped: "Livrat", wont_fix: "Nu se face",
};
const TYPE_META = {
  bug: [Bug, "text-red-300"],
  feature: [Lightbulb, "text-[#d4ff3a]"],
  feedback: [MessageSquare, "text-sky-300"],
};

export default function BetaIssuesPage() {
  const [data, setData] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("bug");
  const [severity, setSeverity] = useState("P1");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/api/admin/beta/issues${statusFilter ? `?status=${statusFilter}` : ""}`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error("beta issues load failed", e); }
  }, [statusFilter]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!title.trim()) return;
    setBusy(true);
    try {
      await axios.post(`${API}/api/admin/beta/issues`, { title, type, severity, source: "war_room" }, { withCredentials: true });
      setTitle(""); await load();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la creare"); }
    setBusy(false);
  };

  const patch = async (id, updates) => {
    try {
      await axios.patch(`${API}/api/admin/beta/issues/${id}`, updates, { withCredentials: true });
      await load();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la actualizare"); }
  };

  if (!data) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-stone-500" /></div>;
  const c = data.counts;

  return (
    <div className="pm-shell min-h-screen bg-[#0a0a0b] text-stone-100 p-4 lg:p-8">
    <div className="max-w-6xl mx-auto space-y-5" data-testid="beta-issues-page">
      <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-block" data-testid="issues-back-admin">← Înapoi la Admin</Link>
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl lg:text-4xl font-bold tracking-tight text-stone-100 flex items-center gap-3"><ClipboardList className="w-5 h-5 lg:w-8 lg:h-8 text-[#d4ff3a]" /> Beta Issues · Prioritization Board</h1>
          <p className="text-xs text-stone-500 mt-1">P0 = blocant beta (fix &lt;24h) · P1 = major (fix &lt;72h) · P2/P3 = batch săptămânal. Workflow: nou → triat → în lucru → rezolvat → livrat.</p>
        </div>
        <button onClick={load} className="p-2 rounded-full bg-white/5 text-stone-400" data-testid="issues-refresh"><RefreshCcw className="w-4 h-4" /></button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[["Deschise", c.open, "issues-kpi-open"], ["P0 deschise", c.open_p0, "issues-kpi-p0"], ["P1 deschise", c.open_p1, "issues-kpi-p1"], ["Rezolvate", c.fixed, "issues-kpi-fixed"]].map(([l, v, tid]) => (
          <div key={l} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid={tid}>
            <div className="text-xs text-stone-400">{l}</div>
            <div className="mt-1 text-2xl lg:text-3xl font-semibold text-stone-100">{v}</div>
          </div>
        ))}
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-4 flex flex-wrap items-center gap-2" data-testid="issues-add-form">
        <input value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => e.key === "Enter" && add()}
          placeholder="Descrie problema sau cererea (din feedback, suport, observație)..."
          className="flex-1 min-w-[240px] bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm text-stone-200 outline-none focus:border-[#d4ff3a]/50" data-testid="issue-title-input" />
        <select value={type} onChange={e => setType(e.target.value)} className="bg-white/5 border border-white/10 rounded-full px-3 py-2.5 text-xs text-stone-300" data-testid="issue-type-select">
          <option value="bug">Bug</option><option value="feature">Feature</option><option value="feedback">Feedback</option>
        </select>
        <select value={severity} onChange={e => setSeverity(e.target.value)} className="bg-white/5 border border-white/10 rounded-full px-3 py-2.5 text-xs text-stone-300" data-testid="issue-severity-select">
          {["P0", "P1", "P2", "P3"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button onClick={add} disabled={busy || !title.trim()}
          className="flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-[#d4ff3a] text-black text-xs font-bold disabled:opacity-50" data-testid="issue-add-btn">
          <Plus className="w-3.5 h-3.5" /> Adaugă
        </button>
      </div>

      <div className="flex items-center gap-2 flex-wrap" data-testid="issues-filters">
        {[["", "Toate"], ["new", "Noi"], ["triaged", "Triate"], ["in_progress", "În lucru"], ["fixed", "Rezolvate"], ["shipped", "Livrate"], ["wont_fix", "Nu se fac"]].map(([v, l]) => (
          <button key={v} onClick={() => setStatusFilter(v)} data-testid={`issues-filter-${v || "all"}`}
            className={`px-3 py-1.5 rounded-full text-xs font-medium ${statusFilter === v ? "bg-[#d4ff3a] text-black" : "bg-white/5 text-stone-400"}`}>{l}</button>
        ))}
      </div>

      <div className="space-y-2" data-testid="issues-list">
        {data.items.length === 0 && (
          <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-10 text-center text-sm text-stone-500" data-testid="issues-empty">
            Niciun issue {statusFilter ? "cu acest status" : "încă"} — adaugă primul din formularul de sus sau din feedback-ul beta.
          </div>
        )}
        {data.items.map(it => {
          const [TIcon, tColor] = TYPE_META[it.type] || TYPE_META.bug;
          return (
            <div key={it.id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-3.5 flex items-center gap-3 flex-wrap" data-testid={`issue-${it.id}`}>
              <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold shrink-0 ${SEV_STYLE[it.severity]}`}>{it.severity}</span>
              <TIcon className={`w-4 h-4 shrink-0 ${tColor}`} />
              <div className="flex-1 min-w-[200px]">
                <div className="text-sm text-stone-200 font-medium">{it.title}</div>
                <div className="text-[10px] text-stone-500 mt-0.5">
                  {it.source}{it.reporter_email ? ` · ${it.reporter_email}` : ""} · {(it.created_at || "").slice(0, 10)}
                  {it.notes ? ` · ${it.notes}` : ""}
                </div>
              </div>
              <select value={it.severity} onChange={e => patch(it.id, { severity: e.target.value })}
                className="bg-white/5 border border-white/10 rounded-full px-2 py-1.5 text-[11px] text-stone-300 shrink-0" data-testid={`issue-sev-${it.id}`}>
                {["P0", "P1", "P2", "P3"].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={it.status} onChange={e => patch(it.id, { status: e.target.value })}
                className="bg-white/5 border border-white/10 rounded-full px-2 py-1.5 text-[11px] text-stone-300 shrink-0" data-testid={`issue-status-${it.id}`}>
                {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          );
        })}
      </div>
    </div>
    </div>
  );
}
