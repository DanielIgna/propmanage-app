// Extracted from AdminQAPlaybook.jsx for maintainability.
import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { CheckCircle2, ListChecks, Loader2, Plus, RotateCw, Search, Sparkles, Trash2, Wand2 } from "lucide-react";
import { AdminCard, AdminBtn } from "../AdminLayoutMetronic";
import { API } from "./shared";

export const TerminologyAuditCard = () => {
  const [clusters, setClusters] = useState([]);
  const [incs, setIncs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [fixingId, setFixingId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("open");
  const [showClusters, setShowClusters] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [proposed, setProposed] = useState([]);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState({ done: 0, total: 0, current: "" });

  const loadClusters = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/admin/qa/term-audit/clusters`);
      setClusters(data.clusters || []);
    } catch {}
  }, []);

  const loadIncs = useCallback(async () => {
    setLoading(true);
    try {
      const url = statusFilter === "ALL" ? `${API}/admin/qa/term-audit/inconsistencies` : `${API}/admin/qa/term-audit/inconsistencies?status=${statusFilter}`;
      const { data } = await axios.get(url);
      setIncs(data.inconsistencies || []);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { loadClusters(); loadIncs(); }, [loadClusters, loadIncs]);

  const scan = async () => {
    setScanning(true);
    try {
      const { data } = await axios.post(`${API}/admin/qa/term-audit/scan`);
      toast.success(`Scanare completă: ${data.report.total_inconsistencies} inconsistențe (${data.persisted.added} noi)`);
      loadIncs();
    } finally {
      setScanning(false);
    }
  };

  const discover = async () => {
    setDiscovering(true);
    setProposed([]);
    try {
      const { data } = await axios.post(`${API}/admin/qa/term-audit/discover`);
      if (data.error) toast.error(data.error);
      else {
        setProposed(data.proposed || []);
        toast.success(`AI propune ${(data.proposed || []).length} cluster-uri noi`);
      }
    } finally {
      setDiscovering(false);
    }
  };

  const addCluster = async (c) => {
    try {
      await axios.post(`${API}/admin/qa/term-audit/clusters`, c);
      toast.success(`Cluster «${c.key}» adăugat`);
      setProposed((p) => p.filter((x) => x.key !== c.key));
      loadClusters();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la adăugare");
    }
  };

  const aiFix = async (id, occIndex = 0) => {
    setFixingId(id);
    try {
      const { data } = await axios.post(`${API}/admin/qa/term-audit/inconsistencies/${id}/ai-fix`, { occurrence_index: occIndex });
      if (data.error) toast.error(`AI fix eșuat: ${data.error}`);
      else { toast.success("AI a generat o rescriere"); loadIncs(); }
    } finally {
      setFixingId(null);
    }
  };

  const apply = async (id) => {
    if (!confirm("Aplici fix-ul AI? Blocul afectat va folosi termenul canonic în PDF + UI (override DB).")) return;
    try {
      await axios.post(`${API}/admin/qa/term-audit/inconsistencies/${id}/apply`, {});
      toast.success("Termen standardizat aplicat");
      loadIncs();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare");
    }
  };

  const dismiss = async (id) => {
    try {
      await axios.patch(`${API}/admin/qa/term-audit/inconsistencies/${id}/status`, { status: "dismissed" });
      toast.success("Marcat ca dismissed");
      loadIncs();
    } catch {}
  };

  const applyAll = async () => {
    // Get fresh list of opens
    const { data } = await axios.get(`${API}/admin/qa/term-audit/inconsistencies?status=open`);
    const opens = data.inconsistencies || [];
    if (opens.length === 0) {
      toast.info("Niciun conflict deschis de rezolvat");
      return;
    }
    if (!confirm(`Rulează AI fix + apply override pentru toate cele ${opens.length} inconsistențe? Durează ~${opens.length * 10} secunde.`)) return;
    setBulkRunning(true);
    setBulkProgress({ done: 0, total: opens.length, current: "" });
    let totalFixed = 0;
    let totalPartial = 0;
    let totalOcc = 0;
    for (let i = 0; i < opens.length; i++) {
      const inc = opens[i];
      setBulkProgress({ done: i, total: opens.length, current: `${inc.doc_slug} · ${inc.cluster_key}` });
      try {
        const { data: res } = await axios.post(`${API}/admin/qa/term-audit/apply-all`, { inc_id: inc.id });
        const det = res?.details?.[0];
        if (det) {
          totalOcc += det.occurrences_patched || 0;
          if (det.status === "fixed") totalFixed++;
          else if (det.status === "partial") totalPartial++;
        }
      } catch (e) {
        // continue
      }
    }
    setBulkProgress({ done: opens.length, total: opens.length, current: "" });
    setBulkRunning(false);
    toast.success(`Bulk apply complet: ${totalFixed} fixate · ${totalPartial} parțiale · ${totalOcc} blocuri patch-uite`);
    loadIncs();
  };

  const statBadge = (s) => ({
    open: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    approved: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
    dismissed: "bg-slate-500/15 text-slate-600 dark:text-slate-400",
    fixed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  }[s] || "bg-slate-500/15");

  return (
    <AdminCard
      title={<span className="inline-flex items-center gap-2"><ListChecks className="w-4 h-4" /> Terminology Audit · consistență vocabular în documentație</span>}
      testid="qa-term-audit-card"
      action={
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="text-xs px-2 py-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900" data-testid="qa-term-filter">
            <option value="ALL">Toate</option>
            <option value="open">Open</option>
            <option value="dismissed">Dismissed</option>
            <option value="fixed">Fixed</option>
          </select>
          <button onClick={loadIncs} className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white" data-testid="qa-term-refresh"><RotateCw className="w-3.5 h-3.5" /></button>
        </div>
      }
    >
      <p className="text-xs text-slate-500 mb-3">
        Detectează când un manual folosește simultan 2+ termeni pentru același concept (ex: „escrow" + „cont blocat" + „depozit garanție"). Sistemul vine cu <strong>{clusters.length} cluster-uri seed</strong> + poți cere AI-ului să descopere altele noi.
      </p>

      <div className="flex gap-2 mb-3 flex-wrap">
        <AdminBtn variant="primary" onClick={scan} disabled={scanning} data-testid="qa-term-scan-btn">
          {scanning ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Scanare...</> : <><Search className="w-3.5 h-3.5 inline mr-1" /> Scanează manualele</>}
        </AdminBtn>
        <AdminBtn variant="success" onClick={applyAll} disabled={bulkRunning} data-testid="qa-term-apply-all-btn">
          {bulkRunning ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Apply ALL ({bulkProgress.done}/{bulkProgress.total})...</> : <><Wand2 className="w-3.5 h-3.5 inline mr-1" /> Apply ALL AI fixes</>}
        </AdminBtn>
        <AdminBtn variant="secondary" onClick={() => setShowClusters((v) => !v)} data-testid="qa-term-toggle-clusters">
          {showClusters ? "Ascunde" : "Vezi"} cluster-uri ({clusters.length})
        </AdminBtn>
        <AdminBtn variant="ghost" onClick={discover} disabled={discovering} data-testid="qa-term-discover-btn">
          {discovering ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> AI caută...</> : <><Sparkles className="w-3.5 h-3.5 inline mr-1" /> AI discover cluster-uri noi</>}
        </AdminBtn>
      </div>

      {bulkRunning && bulkProgress.total > 0 && (
        <div className="mb-3 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800" data-testid="qa-term-bulk-progress">
          <div className="flex items-center justify-between text-xs text-emerald-700 dark:text-emerald-300 mb-1">
            <span><strong>Bulk Apply în curs:</strong> {bulkProgress.current || "..."}</span>
            <span>{bulkProgress.done} / {bulkProgress.total}</span>
          </div>
          <div className="w-full h-2 bg-emerald-100 dark:bg-emerald-800/40 rounded-full overflow-hidden">
            <div className="h-2 bg-emerald-500 rounded-full transition-all" style={{width: `${(bulkProgress.done / bulkProgress.total) * 100}%`}} />
          </div>
        </div>
      )}

      {showClusters && clusters.length > 0 && (
        <div className="mb-3 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 max-h-[200px] overflow-y-auto">
          {clusters.map((c) => (
            <div key={c.key} className="text-xs py-1.5 border-b border-slate-200 dark:border-slate-700 last:border-0">
              <code className="font-semibold text-slate-900 dark:text-slate-100">{c.canonical}</code>
              <span className="text-slate-500 mx-1">≡</span>
              <span className="text-slate-600 dark:text-slate-300">{c.variants.join(" · ")}</span>
              {c.is_seed && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-slate-500/15 text-slate-500">seed</span>}
            </div>
          ))}
        </div>
      )}

      {proposed.length > 0 && (
        <div className="mb-3 p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800" data-testid="qa-term-proposed">
          <div className="text-xs uppercase tracking-wider text-blue-700 dark:text-blue-300 mb-2">✨ Cluster-uri propuse de AI</div>
          {proposed.map((c) => (
            <div key={c.key} className="text-xs py-2 border-b border-blue-200 dark:border-blue-800 last:border-0 flex items-start gap-2">
              <div className="flex-1">
                <code className="font-semibold">{c.canonical}</code>
                <span className="text-slate-500 mx-1">≡</span>
                <span className="text-slate-600 dark:text-slate-300">{c.variants.join(" · ")}</span>
                {c.description && <div className="text-[10px] text-slate-500 mt-0.5">{c.description}</div>}
              </div>
              <AdminBtn variant="primary" onClick={() => addCluster(c)} data-testid={`qa-term-add-${c.key}`}><Plus className="w-3 h-3 inline" /> Add</AdminBtn>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="text-xs text-slate-500 py-6 text-center"><Loader2 className="w-4 h-4 inline animate-spin mr-1" /> Se încarcă...</div>
      ) : incs.length === 0 ? (
        <div className="text-center py-6 text-sm text-slate-500">
          {statusFilter === "open" ? "🎉 Niciun conflict de terminologie deschis!" : "Niciun rezultat pentru filtrul selectat."}
        </div>
      ) : (
        <ul className="space-y-2 max-h-[420px] overflow-y-auto pr-1" data-testid="qa-term-inc-list">
          {incs.map((inc) => {
            const isFixed = inc.status === "fixed";
            return (
              <li key={inc.id} className="text-xs p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40" data-testid={`qa-term-inc-${inc.id}`}>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <code className="font-mono font-semibold">{inc.doc_slug}</code>
                  <span className="text-slate-500">› cluster «{inc.cluster_key}»</span>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">canonic: <strong>{inc.canonical}</strong></span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-700 dark:text-red-300">
                    {inc.variants_used.length} variante
                  </span>
                  <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full ${statBadge(inc.status)}`}>{inc.status}</span>
                </div>
                <div className="text-slate-600 dark:text-slate-300">
                  Folosite simultan: {inc.variants_used.map((v) => (
                    <span key={v} className={`mx-0.5 px-1.5 py-0.5 rounded text-[10px] ${v.toLowerCase() === inc.canonical.toLowerCase() ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" : "bg-amber-500/15 text-amber-700 dark:text-amber-300"}`}>{v}</span>
                  ))}
                  · {inc.occurrences.length} apariții
                </div>
                {inc.ai_suggested_fix && (
                  <div className="mt-2 p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                    <div className="text-[10px] uppercase tracking-wider text-blue-700 dark:text-blue-300 mb-1">✨ Rescriere AI (occurrence #{inc.ai_suggested_fix.occurrence_index})</div>
                    {inc.ai_suggested_fix.title && <div className="font-semibold text-slate-900 dark:text-slate-100">{inc.ai_suggested_fix.title}</div>}
                    <div className="text-slate-700 dark:text-slate-200">{inc.ai_suggested_fix.body}</div>
                  </div>
                )}
                <div className="flex gap-1 mt-2 flex-wrap">
                  {!isFixed && !inc.ai_suggested_fix && (
                    <AdminBtn variant="secondary" onClick={() => aiFix(inc.id, 0)} disabled={fixingId === inc.id} data-testid={`qa-term-${inc.id}-aifix`}>
                      {fixingId === inc.id ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> AI...</> : <><Wand2 className="w-3.5 h-3.5 inline mr-1" /> AI rescrie 1ª apariție</>}
                    </AdminBtn>
                  )}
                  {!isFixed && inc.ai_suggested_fix && (
                    <AdminBtn variant="success" onClick={() => apply(inc.id)} data-testid={`qa-term-${inc.id}-apply`}>
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" /> Aplică
                    </AdminBtn>
                  )}
                  {!isFixed && (
                    <AdminBtn variant="ghost" onClick={() => dismiss(inc.id)} data-testid={`qa-term-${inc.id}-dismiss`}>
                      <Trash2 className="w-3.5 h-3.5 inline mr-1" /> Dismiss
                    </AdminBtn>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </AdminCard>
  );
};
