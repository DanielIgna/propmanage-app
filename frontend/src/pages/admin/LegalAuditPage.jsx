// LegalAuditPage — admin view: all IT collaborators × contract status (compliance matrix).
// Route: /admin/legal-audit
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  ShieldCheck, ChevronLeft, Loader2, CheckCircle2, AlertTriangle, AlertCircle,
  FileText, Search, RefreshCw, Eye,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_META = {
  ok: { color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300", icon: CheckCircle2, label: "Semnat" },
  missing: { color: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300", icon: AlertTriangle, label: "Lipsește" },
  outdated: { color: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300", icon: AlertCircle, label: "Versiune veche" },
};

const TYPE_LABELS = {
  nda: "NDA",
  collaboration: "Colaborare",
  ip_cession: "Cesiune IP",
  security_policy: "Securitate IT",
  infra_access: "Acces infra",
  regulation: "Regulament",
};

const ContractsModal = ({ email, onClose }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    ax.get(`/api/admin/legal/contracts/${encodeURIComponent(email)}`)
      .then(r => setItems(r.data?.items || [])).catch(() => {})
      .finally(() => setLoading(false));
  }, [email]);
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Istoric semnături · {email}</h3>
          <button onClick={onClose} className="text-slate-400">✕</button>
        </div>
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {loading && <Loader2 className="w-5 h-5 animate-spin text-slate-400 mx-auto" />}
          {!loading && items.length === 0 && <div className="text-sm text-slate-500 text-center py-6">Nicio semnătură înregistrată.</div>}
          {!loading && items.map(c => (
            <div key={c.id} className="py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="text-sm font-semibold text-slate-900 dark:text-white">{c.document_title || c.document_type}</div>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${c.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>{c.status}</span>
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                v{c.document_version} · {c.accepted_at ? new Date(c.accepted_at).toLocaleString("ro-RO") : "—"} · IP: {c.ip_address || "—"}
              </div>
              {c.signature_name && <div className="text-[11px] text-slate-600 dark:text-slate-300 italic mt-0.5">Semnat: „{c.signature_name}”</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const LegalAuditPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [onlyNon, setOnlyNon] = useState(false);
  const [q, setQ] = useState("");
  const [requiredTypes, setRequiredTypes] = useState([]);
  const [showContracts, setShowContracts] = useState(null);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const { data } = await ax.get("/api/admin/legal/audit", { params: { only_non_compliant: onlyNon } });
      setItems(data.items || []);
      setRequiredTypes(data.required_types || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [onlyNon]);

  const filtered = useMemo(() => {
    if (!q.trim()) return items;
    const needle = q.toLowerCase();
    return items.filter(c => (c.name || "").toLowerCase().includes(needle) || (c.email || "").toLowerCase().includes(needle));
  }, [items, q]);

  const totalCompliant = items.filter(i => i.compliant).length;
  const totalNon = items.length - totalCompliant;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="legal-audit-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm">
          <ChevronLeft className="w-4 h-4" /> Admin
        </Link>
        <span className="text-slate-300">·</span>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-500" />
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Audit Juridic · Colaboratori IT</h1>
        </div>
        <div className="flex-1" />
        <button onClick={load} className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-1.5 text-slate-700 dark:text-slate-200" data-testid="reload-audit">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
          <div className="text-xs text-slate-500 dark:text-slate-400">Total colaboratori</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white">{items.length}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-emerald-200 dark:border-emerald-500/30">
          <div className="text-xs text-emerald-600 dark:text-emerald-400">Conform</div>
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{totalCompliant}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-rose-200 dark:border-rose-500/30">
          <div className="text-xs text-rose-600 dark:text-rose-400">Cu probleme</div>
          <div className="text-2xl font-bold text-rose-700 dark:text-rose-300">{totalNon}</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută nume / email…" className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="audit-search" />
        </div>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer text-slate-700 dark:text-slate-300">
          <input type="checkbox" checked={onlyNon} onChange={e => setOnlyNon(e.target.checked)} data-testid="filter-non-compliant" />
          Doar non-conformi
        </label>
      </div>

      {/* Matrix table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {loading && <div className="p-10 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-slate-400" /></div>}
        {error && <div className="p-6 text-rose-500 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {error}</div>}
        {!loading && filtered.length === 0 && !error && (
          <div className="p-10 text-center text-sm text-slate-500 dark:text-slate-400">Niciun colaborator de afișat.</div>
        )}
        {!loading && filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="text-left py-2.5 px-4">Colaborator</th>
                  <th className="text-left py-2.5 px-4">Stare</th>
                  {requiredTypes.map(t => (
                    <th key={t} className="text-center py-2.5 px-2">{TYPE_LABELS[t] || t}</th>
                  ))}
                  <th className="py-2.5 px-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filtered.map(c => (
                  <tr key={c.collaborator_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`audit-row-${c.collaborator_id}`}>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 dark:text-white">{c.name}</div>
                      <div className="text-[11px] text-slate-500">{c.email} · {c.role}/{c.seniority}</div>
                    </td>
                    <td className="py-3 px-4">
                      {c.compliant
                        ? <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300 inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Conform</span>
                        : <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Acțiune</span>
                      }
                    </td>
                    {requiredTypes.map(t => {
                      const doc = c.documents.find(d => d.type === t);
                      const meta = doc ? (STATUS_META[doc.status] || STATUS_META.missing) : STATUS_META.missing;
                      const Icon = meta.icon;
                      return (
                        <td key={t} className="text-center py-3 px-2">
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${meta.color}`} title={meta.label}>
                            <Icon className="w-3 h-3" />
                          </span>
                        </td>
                      );
                    })}
                    <td className="py-3 px-2">
                      <button onClick={() => setShowContracts(c.email)} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" title="Vezi istoric semnături" data-testid={`view-history-${c.collaborator_id}`}>
                        <Eye className="w-4 h-4 text-slate-500" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="mt-4 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
        <FileText className="w-3 h-3" />
        Documentele obligatorii sunt afișate pe coloane. Click pe iconul ochi pentru a vedea istoricul complet al semnăturilor pentru un colaborator.
      </div>

      {showContracts && <ContractsModal email={showContracts} onClose={() => setShowContracts(null)} />}
    </div>
  );
};

export default LegalAuditPage;
export { LegalAuditPage };
