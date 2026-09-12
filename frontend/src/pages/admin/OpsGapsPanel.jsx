// Specialist Gap Engine — cereri fără specialist → Gap Records (filtrare / alocare / export)
import React, { useEffect, useState, useCallback } from "react";
import { AlertTriangle, Download, Loader2, UserCheck, Star, RefreshCcw } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
const STATUS_LABELS = { open: "Deschis", assigned: "Alocat", resolved: "Rezolvat", all: "Toate" };

const GapRow = ({ gap, onAssigned }) => {
  const [open, setOpen] = useState(false);
  const [candidates, setCandidates] = useState(null);
  const [fallback, setFallback] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadCandidates = async () => {
    setOpen(!open);
    if (candidates || open) return;
    try {
      const r = await axios.get(`${API}/api/admin/operations/gaps/${gap.id}/candidates`, { withCredentials: true });
      setCandidates(r.data.candidates || []);
      setFallback(r.data.fallback);
    } catch (e) { setCandidates([]); }
  };

  const assign = async (spec) => {
    if (!window.confirm(`Aloci specialistul ${spec.name} pentru "${gap.title}"?`)) return;
    setBusy(true);
    try {
      await axios.post(`${API}/api/admin/operations/gaps/${gap.id}/assign`, { specialist_id: spec.id }, { withCredentials: true });
      onAssigned();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la alocare"); } finally { setBusy(false); }
  };

  return (
    <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3.5" data-testid={`gap-row-${gap.id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-sm text-white truncate">{gap.title || "Cerere fără titlu"}</div>
          <div className="text-xs text-stone-400 mt-0.5">
            <span className="capitalize text-amber-300">{gap.category}</span>
            {gap.city && <span> · {gap.city}</span>}
            {gap.client_name && <span> · {gap.client_name}</span>}
            <span> · {String(gap.request_created_at).slice(0, 10)}</span>
          </div>
          {gap.status !== "open" && (
            <div className="text-[11px] text-emerald-400 mt-1">{STATUS_LABELS[gap.status]}{gap.assigned_specialist_name ? ` → ${gap.assigned_specialist_name}` : ""}</div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-amber-300">{Number(gap.est_lost_revenue_ron).toLocaleString("ro-RO")} RON</span>
          {gap.status === "open" && (
            <button onClick={loadCandidates} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid={`gap-candidates-btn-${gap.id}`}>
              <UserCheck className="w-3.5 h-3.5" /> Alocă
            </button>
          )}
        </div>
      </div>
      {open && (
        <div className="mt-3 pt-3 border-t border-white/5 space-y-1.5" data-testid={`gap-candidates-${gap.id}`}>
          {candidates === null ? <Loader2 className="w-4 h-4 animate-spin text-stone-500" />
            : candidates.length === 0 ? <p className="text-xs text-stone-500">Niciun specialist disponibil — exact acesta este gap-ul de recrutare.</p>
            : (<>
              {fallback && <p className="text-[11px] text-amber-400">Fără match exact pe categorie — specialiști verificați top-rated:</p>}
              {candidates.map(c => (
                <div key={c.id} className="flex items-center justify-between text-xs bg-white/[0.03] rounded-lg px-3 py-2">
                  <div className="text-stone-200">{c.name} <span className="text-stone-500">· {c.specialty || "—"}</span>
                    {c.rating != null && <span className="text-stone-400 ml-1.5 inline-flex items-center gap-0.5"><Star className="w-3 h-3 text-amber-400" />{c.rating}</span>}
                    {c.in_zone && <span className="text-emerald-400 ml-1.5">în zonă</span>}
                  </div>
                  <button onClick={() => assign(c)} disabled={busy} className="pm-btn pm-btn-success pm-btn-sm" data-testid={`gap-assign-${gap.id}-${c.id}`}>
                    {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : "Alocă"}
                  </button>
                </div>
              ))}
            </>)}
        </div>
      )}
    </div>
  );
};

export const OpsGapsPanel = ({ onChanged }) => {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("open");
  const [category, setCategory] = useState("");
  const [city, setCity] = useState("");

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ status });
      if (category) params.append("category", category);
      if (city) params.append("city", city);
      const r = await axios.get(`${API}/api/admin/operations/gaps?${params}`, { withCredentials: true });
      setData(r.data);
    } catch (e) { console.error(e); }
  }, [status, category, city]);
  useEffect(() => { load(); }, [load]);

  const s = data?.summary || {};
  const records = data?.records || [];

  return (
    <div className="bg-[#0e0e10] rounded-3xl border border-white/10 p-6 mt-6" data-testid="ops-gap-engine">
      <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2 className="font-serif text-xl flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /> Specialist Gap Engine</h2>
          <p className="text-[11px] text-stone-500 mt-0.5">Fiecare cerere fără specialist = Gap Record. Cerere · oraș · client · venit pierdut estimat.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5" data-testid="gap-filter-status">
            {["open", "assigned", "resolved", "all"].map(v => <option key={v} value={v}>{STATUS_LABELS[v]}</option>)}
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5" data-testid="gap-filter-category">
            <option value="">Toate categoriile</option>
            {Object.keys(s.by_category || {}).map(c => <option key={c} value={c}>{c} ({s.by_category[c]})</option>)}
          </select>
          <select value={city} onChange={(e) => setCity(e.target.value)} className="bg-[#141416] border border-white/15 rounded-lg text-xs px-2 py-1.5" data-testid="gap-filter-city">
            <option value="">Toate orașele</option>
            {Object.keys(s.by_city || {}).filter(c => c !== "necunoscut").map(c => <option key={c} value={c}>{c} ({s.by_city[c]})</option>)}
          </select>
          <button onClick={load} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="gap-refresh"><RefreshCcw className="w-3.5 h-3.5" /></button>
          <a href={`${API}/api/admin/operations/gaps/export?status=${status}`} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="gap-export-btn">
            <Download className="w-3.5 h-3.5" /> Export CSV
          </a>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4" data-testid="gap-summary">
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3 text-center"><div className="font-serif text-xl text-amber-300">{s.total_open ?? 0}</div><div className="text-[11px] text-stone-500">Gaps deschise</div></div>
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3 text-center"><div className="font-serif text-xl">{s.waiting_customers ?? 0}</div><div className="text-[11px] text-stone-500">Clienți în așteptare</div></div>
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-3 text-center"><div className="font-serif text-xl text-red-400">{Number(s.est_lost_revenue_ron || 0).toLocaleString("ro-RO")}</div><div className="text-[11px] text-stone-500">RON venit pierdut est.</div></div>
      </div>

      <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
        {records.length === 0
          ? <p className="text-sm text-stone-500" data-testid="gap-empty">Niciun gap {status === "open" ? "deschis" : ""} — toate cererile au specialist. 🎉</p>
          : records.map(g => <GapRow key={g.id} gap={g} onAssigned={() => { load(); onChanged && onChanged(); }} />)}
      </div>
    </div>
  );
};
