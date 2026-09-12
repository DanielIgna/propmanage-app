// Card domeniu Enterprise Health — scor + trend + explain formula (D151) + editor ponderi
import React, { useState } from "react";
import { ChevronDown, ChevronUp, Loader2, SlidersHorizontal, Save } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const FormulaEditor = ({ explain, onSaved }) => {
  const [weights, setWeights] = useState(Object.fromEntries(explain.calculation_steps.map(s => [s.metric, s.weight])));
  const [warn, setWarn] = useState(explain.warning_threshold);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!reason.trim()) { alert("Motivul modificării este obligatoriu (audit D151)."); return; }
    setBusy(true);
    try {
      await axios.patch(`${API}/api/admin/enterprise-health/formulas/${explain.key}`,
        { weights, warning_threshold: Number(warn), reason }, { withCredentials: true });
      onSaved();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); } finally { setBusy(false); }
  };

  return (
    <div className="mt-3 pt-3 border-t border-white/5 space-y-2" data-testid={`eh-editor-${explain.key}`}>
      <div className="text-[11px] text-stone-500 uppercase tracking-wide flex items-center gap-1.5"><SlidersHorizontal className="w-3 h-3" /> Ajustează formula (v{explain.version})</div>
      {explain.calculation_steps.map(s => (
        <div key={s.metric} className="flex items-center gap-2 text-xs">
          <span className="flex-1 text-stone-400 truncate">{s.label}</span>
          <input type="number" step="0.1" min="0" value={weights[s.metric]}
            onChange={(e) => setWeights(w => ({ ...w, [s.metric]: e.target.value }))}
            className="w-16 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs" data-testid={`eh-weight-${explain.key}-${s.metric}`} />
        </div>
      ))}
      <div className="flex items-center gap-2 text-xs">
        <span className="flex-1 text-stone-400">Prag warning</span>
        <input type="number" min="0" max="100" value={warn} onChange={(e) => setWarn(e.target.value)}
          className="w-16 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs" data-testid={`eh-warn-${explain.key}`} />
      </div>
      <div className="flex gap-2">
        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Motivul modificării (obligatoriu) *"
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-[#d4ff3a]" data-testid={`eh-reason-${explain.key}`} />
        <button onClick={save} disabled={busy} className="pm-btn pm-btn-success pm-btn-sm" data-testid={`eh-save-formula-${explain.key}`}>
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Salvează
        </button>
      </div>
    </div>
  );
};

export const EhDomainCard = ({ domain, onChanged }) => {
  const [open, setOpen] = useState(false);
  const [explain, setExplain] = useState(null);

  const toggle = async () => {
    setOpen(!open);
    if (explain || open) return;
    try {
      const r = await axios.get(`${API}/api/admin/enterprise-health/formulas/${domain.key}/explain`, { withCredentials: true });
      setExplain(r.data);
    } catch (e) { console.error(e); }
  };

  return (
    <div className="bg-[#0e0e10] rounded-2xl border border-white/10 p-4" data-testid={`eh-domain-${domain.key}`}>
      <button onClick={toggle} className="w-full text-left" data-testid={`eh-domain-toggle-${domain.key}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <span className="font-serif text-2xl w-12 text-right shrink-0" style={{ color: domain.band.color }}>{Math.round(domain.score)}</span>
            <div className="min-w-0">
              <div className="text-sm text-stone-100 truncate">{domain.label}</div>
              <div className="text-[10px] text-stone-500">{domain.band.label} · încredere {domain.confidence === "high" ? "mare" : domain.confidence === "medium" ? "medie" : "mică"}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {domain.trend_30d != null && <span className={`text-[11px] ${domain.trend_30d > 0 ? "text-emerald-400" : domain.trend_30d < 0 ? "text-red-400" : "text-stone-500"}`}>{domain.trend_30d > 0 ? "+" : ""}{domain.trend_30d}</span>}
            {open ? <ChevronUp className="w-4 h-4 text-stone-500" /> : <ChevronDown className="w-4 h-4 text-stone-500" />}
          </div>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full mt-3 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${domain.score}%`, backgroundColor: domain.band.color }} />
        </div>
      </button>

      {open && (
        <div className="mt-3" data-testid={`eh-explain-${domain.key}`}>
          {!explain ? <Loader2 className="w-4 h-4 animate-spin text-stone-500" /> : (
            <>
              <p className="text-[11px] text-stone-500 mb-2">{explain.description} · <span className="text-stone-400">{explain.formula}</span></p>
              <div className="space-y-1">
                {explain.calculation_steps.map(s => (
                  <div key={s.metric} className="flex items-center justify-between text-xs bg-white/[0.02] rounded-lg px-3 py-1.5">
                    <span className="text-stone-300 truncate flex-1">{s.detail}</span>
                    <span className="text-stone-500 shrink-0 ml-2">×{s.weight} → <span className={s.subscore >= 80 ? "text-emerald-400" : "text-amber-300"}>{s.contribution_pts}p</span></span>
                  </div>
                ))}
              </div>
              <FormulaEditor explain={explain} onSaved={() => { setExplain(null); setOpen(false); onChanged(); }} />
            </>
          )}
        </div>
      )}
    </div>
  );
};
