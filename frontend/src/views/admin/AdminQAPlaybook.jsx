// Admin → QA Playbook
// Interactive checklist + AI test suggester (Claude Sonnet 4.5).
// Run management: create / resume / mark pass-fail-skip / export markdown / close.
import React, { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  ShieldCheck, Plus, Play, CheckCircle2, XCircle, MinusCircle, Circle,
  Sparkles, Loader2, Download, AlertTriangle, ChevronDown, ChevronRight,
  Search, RotateCw, ListChecks, Bot, Rocket, Mail, Clock, FileWarning, Wand2, Trash2,
} from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { ReleaseGateCard } from "./qa/ReleaseGateCard";
import { ContentAuditCard } from "./qa/ContentAuditCard";
import { TerminologyAuditCard } from "./qa/TerminologyAuditCard";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const STATUS_META = {
  pending: { icon: Circle,        color: "text-slate-400",   bg: "bg-slate-100 dark:bg-slate-800",      label: "Pending" },
  pass:    { icon: CheckCircle2,  color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-900/30", label: "Pass" },
  fail:    { icon: XCircle,       color: "text-red-600",     bg: "bg-red-50 dark:bg-red-900/30",         label: "Fail" },
  skip:    { icon: MinusCircle,   color: "text-amber-600",   bg: "bg-amber-50 dark:bg-amber-900/30",     label: "Skip" },
};

const PRIO_BADGE = {
  P0: "bg-red-500/15 text-red-600 dark:text-red-300 border-red-500/30",
  P1: "bg-amber-500/15 text-amber-600 dark:text-amber-300 border-amber-500/30",
  P2: "bg-sky-500/15 text-sky-600 dark:text-sky-300 border-sky-500/30",
};


// ----------------------------------------------------------------------------
// Sub-components
// ----------------------------------------------------------------------------

const ProgressRing = ({ pct }) => {
  const c = 2 * Math.PI * 28;
  const off = c * (1 - Math.min(Math.max(pct, 0), 100) / 100);
  return (
    <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90" data-testid="qa-progress-ring">
      <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" className="text-slate-200 dark:text-slate-700" strokeWidth="6" />
      <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" className="text-emerald-500" strokeWidth="6"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} style={{transition:"stroke-dashoffset 250ms ease"}} />
    </svg>
  );
};


const RunHeader = ({ run, summary, onClose, onExport, onChangeRun }) => {
  const isClosed = !!run?.closed_at;
  return (
    <div className="flex flex-col md:flex-row gap-4 md:items-center md:justify-between rounded-2xl border bg-white dark:bg-slate-900 dark:border-slate-800 p-4">
      <div className="flex items-center gap-4">
        <div className="relative">
          <ProgressRing pct={summary.progress_pct} />
          <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-slate-700 dark:text-slate-200">
            {summary.progress_pct}%
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">QA Run</div>
          <div className="font-semibold text-lg text-slate-900 dark:text-slate-100" data-testid="qa-run-name">{run?.name || "—"}</div>
          <div className="text-xs text-slate-500">Versiune: <code className="text-slate-700 dark:text-slate-300">{run?.version || "—"}</code></div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">Pass: {summary.by_status?.pass || 0}</span>
        <span className="text-xs px-2 py-1 rounded-full bg-red-500/15 text-red-700 dark:text-red-300">Fail: {summary.by_status?.fail || 0}</span>
        <span className="text-xs px-2 py-1 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300">Skip: {summary.by_status?.skip || 0}</span>
        <span className="text-xs px-2 py-1 rounded-full bg-slate-500/15 text-slate-700 dark:text-slate-300">Pending: {summary.by_status?.pending || 0}</span>
        {summary.release_blocked && (
          <span className="text-xs px-2 py-1 rounded-full bg-red-600 text-white flex items-center gap-1" data-testid="qa-release-blocked">
            <AlertTriangle className="w-3 h-3" /> RELEASE BLOCKED · {summary.p0_fail} P0 fail
          </span>
        )}
        <AdminBtn variant="ghost" onClick={onChangeRun} data-testid="qa-switch-run">Schimbă run</AdminBtn>
        <AdminBtn variant="secondary" onClick={onExport} data-testid="qa-export-md">
          <Download className="w-3.5 h-3.5 inline mr-1" /> Export MD
        </AdminBtn>
        {!isClosed && (
          <AdminBtn variant="success" onClick={onClose} data-testid="qa-close-run">Închide run</AdminBtn>
        )}
      </div>
    </div>
  );
};


const CheckRow = ({ check, onUpdate }) => {
  const [editingNote, setEditingNote] = useState(false);
  const [note, setNote] = useState(check.note || "");
  const meta = STATUS_META[check.status] || STATUS_META.pending;
  const Icon = meta.icon;

  const setStatus = (status) => onUpdate(check.id, status, note);
  const saveNote = () => { onUpdate(check.id, check.status, note); setEditingNote(false); };

  return (
    <div className={`rounded-xl border ${meta.bg} border-slate-200 dark:border-slate-700 p-3 transition-colors`} data-testid={`qa-check-${check.code}`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${meta.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <code className="text-xs font-mono font-semibold text-slate-900 dark:text-slate-100">{check.code}</code>
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${PRIO_BADGE[check.priority] || ""}`}>{check.priority}</span>
            {check.subcategory && (
              <span className="text-[10px] uppercase tracking-wider text-slate-500">{check.subcategory}</span>
            )}
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1">{check.description}</p>

          {/* Status toggle pills */}
          <div className="mt-2 flex items-center gap-1">
            {["pass","fail","skip","pending"].map((s) => {
              const M = STATUS_META[s];
              const SI = M.icon;
              const active = check.status === s;
              return (
                <button
                  key={s}
                  onClick={() => setStatus(s)}
                  className={`text-[11px] inline-flex items-center gap-1 px-2 py-0.5 rounded-full border transition ${
                    active ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white" : "border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                  }`}
                  data-testid={`qa-${check.code}-set-${s}`}
                >
                  <SI className="w-3 h-3" /> {M.label}
                </button>
              );
            })}
            <button
              onClick={() => setEditingNote((v) => !v)}
              className="text-[11px] ml-2 text-slate-500 hover:text-slate-900 dark:hover:text-white underline"
              data-testid={`qa-${check.code}-note-toggle`}
            >
              {editingNote ? "Anulează notă" : (check.note ? "Editează notă" : "Adaugă notă")}
            </button>
          </div>

          {/* Note editor */}
          {editingNote && (
            <div className="mt-2">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                placeholder="Ce ai observat? Steps to reproduce, screenshot URL, etc."
                className="w-full text-xs px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                data-testid={`qa-${check.code}-note-input`}
              />
              <div className="flex gap-2 mt-1">
                <AdminBtn variant="primary" onClick={saveNote} data-testid={`qa-${check.code}-note-save`}>Salvează</AdminBtn>
              </div>
            </div>
          )}
          {!editingNote && check.note && (
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-300 italic">📝 {check.note}</p>
          )}
        </div>
      </div>
    </div>
  );
};


const CategoryGroup = ({ category, checks, onUpdate }) => {
  const [open, setOpen] = useState(true);
  const passed = checks.filter((c) => c.status === "pass").length;
  const failed = checks.filter((c) => c.status === "fail").length;
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <div className="rounded-2xl border bg-white dark:bg-slate-900 dark:border-slate-800 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition"
        data-testid={`qa-cat-toggle-${category}`}
      >
        <div className="flex items-center gap-2">
          <Chevron className="w-4 h-4 text-slate-500" />
          <span className="font-semibold text-slate-900 dark:text-slate-100">{category}</span>
          <span className="text-xs text-slate-500">{checks.length} teste</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {failed > 0 && <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-700 dark:text-red-300">{failed} fail</span>}
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">{passed}/{checks.length}</span>
        </div>
      </button>
      {open && (
        <div className="p-3 pt-0 space-y-2">
          {checks.map((c) => <CheckRow key={c.id} check={c} onUpdate={onUpdate} />)}
        </div>
      )}
    </div>
  );
};


const AISuggester = ({ runId, onCheckAdded }) => {
  const [feature, setFeature] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [addedCodes, setAddedCodes] = useState(new Set());
  const [err, setErr] = useState("");

  const run = async () => {
    if (!feature.trim()) {
      toast.error("Scrie un nume de feature mai întâi");
      return;
    }
    setLoading(true);
    setErr("");
    setItems([]);
    setAddedCodes(new Set());
    try {
      const { data } = await axios.post(`${API}/admin/qa/ai-suggest`, { feature, context });
      if (data.error) setErr(data.error);
      setItems(data.items || []);
      if ((data.items || []).length === 0 && !data.error) {
        toast.error("AI nu a întors niciun test. Reformulează feature-ul.");
      } else {
        toast.success(`AI a generat ${data.items.length} teste`);
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const copyMarkdown = () => {
    if (items.length === 0) return;
    const lines = items.map((it) => `- **${it.code}** [${it.priority}] [${it.category}] — ${it.description}`);
    navigator.clipboard.writeText(lines.join("\n"));
    toast.success("Markdown copiat în clipboard");
  };

  const addToRun = async (it) => {
    if (!runId) return;
    try {
      const { data } = await axios.post(`${API}/admin/qa/runs/${runId}/add-check`, {
        code: it.code, priority: it.priority, category: it.category, description: it.description,
      });
      setAddedCodes((s) => new Set([...s, it.code]));
      onCheckAdded && onCheckAdded(data);
      toast.success(`${it.code} adăugat în run`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la adăugare");
    }
  };

  const addAllToRun = async () => {
    if (!runId || items.length === 0) return;
    let added = 0;
    for (const it of items) {
      if (addedCodes.has(it.code)) continue;
      try {
        const { data } = await axios.post(`${API}/admin/qa/runs/${runId}/add-check`, {
          code: it.code, priority: it.priority, category: it.category, description: it.description,
        });
        onCheckAdded && onCheckAdded(data);
        added++;
      } catch {}
    }
    setAddedCodes(new Set(items.map((i) => i.code)));
    toast.success(`${added} teste adăugate în run`);
  };

  return (
    <AdminCard title={<span className="inline-flex items-center gap-2"><Bot className="w-4 h-4" /> AI Test Suggester · Claude Sonnet 4.5</span>} testid="qa-ai-suggester">
      <p className="text-xs text-slate-500 mb-3">Descrie un feature sau un flow. AI va genera 8-12 cazuri de test prioritizate (P0/P1/P2). {runId ? "Apasă ➕ pentru a le adăuga direct în runul curent." : "Pentru a le adăuga într-un run, deschide un run mai întâi."}</p>
      <div className="space-y-2">
        <input
          value={feature}
          onChange={(e) => setFeature(e.target.value)}
          placeholder="Ex: Onboarding email drip pentru specialiști noi"
          className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          data-testid="qa-ai-feature-input"
        />
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          rows={2}
          placeholder="Context opțional: integrări folosite, dependențe, alte flow-uri adiacente..."
          className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          data-testid="qa-ai-context-input"
        />
        <div className="flex gap-2 flex-wrap">
          <AdminBtn variant="primary" onClick={run} disabled={loading} data-testid="qa-ai-suggest-btn">
            {loading ? (<><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Generează...</>) : (<><Sparkles className="w-3.5 h-3.5 inline mr-1" /> Sugerează teste</>)}
          </AdminBtn>
          {items.length > 0 && (
            <AdminBtn variant="secondary" onClick={copyMarkdown} data-testid="qa-ai-copy-md">Copiază MD</AdminBtn>
          )}
          {runId && items.length > 0 && (
            <AdminBtn variant="success" onClick={addAllToRun} data-testid="qa-ai-add-all">
              <Plus className="w-3.5 h-3.5 inline mr-1" /> Adaugă tot în run
            </AdminBtn>
          )}
        </div>
      </div>
      {err && <div className="mt-3 text-xs p-2 rounded bg-red-500/10 text-red-700 dark:text-red-300">{err}</div>}
      {items.length > 0 && (
        <div className="mt-4 space-y-1.5 max-h-[420px] overflow-y-auto pr-1">
          {items.map((it, idx) => {
            const added = addedCodes.has(it.code);
            return (
              <div key={idx} className="text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40" data-testid={`qa-ai-item-${it.code}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <code className="font-mono font-semibold text-slate-900 dark:text-slate-100">{it.code}</code>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${PRIO_BADGE[it.priority] || ""}`}>{it.priority}</span>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">{it.category}</span>
                  {runId && (
                    <button
                      onClick={() => addToRun(it)}
                      disabled={added}
                      className={`ml-auto text-[10px] inline-flex items-center gap-1 px-2 py-0.5 rounded-full border ${added ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" : "border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}`}
                      data-testid={`qa-ai-add-${it.code}`}
                    >
                      {added ? <><CheckCircle2 className="w-3 h-3" /> adăugat</> : <><Plus className="w-3 h-3" /> Adaugă în run</>}
                    </button>
                  )}
                </div>
                <p className="mt-0.5 text-slate-700 dark:text-slate-200">{it.description}</p>
              </div>
            );
          })}
        </div>
      )}
    </AdminCard>
  );
};


// ----------------------------------------------------------------------------
// Automation Panel — execute predefined automated tests; results write into the run.
// ----------------------------------------------------------------------------

const AutomationPanel = ({ runId, onAfterRun }) => {
  const [catalog, setCatalog] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  useEffect(() => {
    axios.get(`${API}/admin/qa/automation/tests`).then(({ data }) => setCatalog(data.tests || [])).catch(() => {});
  }, []);

  const toggle = (code) => {
    setSelected((s) => {
      const next = new Set(s);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  };
  const selectAll = () => setSelected(new Set(catalog.map((t) => t.code)));
  const clearAll = () => setSelected(new Set());

  const execute = async () => {
    const codes = [...selected];
    if (codes.length === 0) {
      toast.error("Selectează cel puțin un test");
      return;
    }
    setLoading(true);
    setResults(null);
    try {
      const { data } = await axios.post(`${API}/admin/qa/automation/execute`, { test_codes: codes, run_id: runId || null });
      setResults(data);
      toast.success(`${data.summary.pass}/${data.summary.total} PASS · ${data.summary.fail} FAIL` + (data.summary.written_to_run ? ` · ${data.summary.written_to_run} scrise în run` : ""));
      onAfterRun && onAfterRun();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la execuție");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminCard title={<span className="inline-flex items-center gap-2"><Play className="w-4 h-4" /> Automation Engine · {catalog.length} teste pre-definite</span>} testid="qa-automation-panel">
      <p className="text-xs text-slate-500 mb-3">
        Teste care rulează singure (HTTP API + Playwright browser). Selectezi câteva, apeși <strong>Execută</strong> și rezultatele se scriu direct în run-ul curent (dacă există) ca scenarii automate marcate cu badge ⚙️.
      </p>
      <div className="flex gap-2 mb-3 flex-wrap">
        <AdminBtn variant="secondary" onClick={selectAll} data-testid="qa-auto-select-all">Selectează tot ({catalog.length})</AdminBtn>
        <AdminBtn variant="ghost" onClick={clearAll} data-testid="qa-auto-clear">Golește selecția</AdminBtn>
        <AdminBtn variant="primary" onClick={execute} disabled={loading || selected.size === 0} data-testid="qa-auto-execute">
          {loading ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Rulează {selected.size}...</> : <><Play className="w-3.5 h-3.5 inline mr-1" /> Execută ({selected.size})</>}
        </AdminBtn>
      </div>
      <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
        {catalog.map((t) => {
          const checked = selected.has(t.code);
          const resForCode = results?.results?.find((r) => r.code === t.code);
          const resIcon = resForCode ? (resForCode.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-red-600" />) : null;
          return (
            <label key={t.code} className={`block text-xs p-2 rounded-lg border cursor-pointer transition ${checked ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20" : "border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/40"}`} data-testid={`qa-auto-row-${t.code}`}>
              <div className="flex items-start gap-2">
                <input type="checkbox" checked={checked} onChange={() => toggle(t.code)} className="mt-0.5" data-testid={`qa-auto-cb-${t.code}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <code className="font-mono font-semibold text-slate-900 dark:text-slate-100">{t.code}</code>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${PRIO_BADGE[t.priority] || ""}`}>{t.priority}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">{t.kind === "browser" ? "🌐 browser" : "⚡ http"}</span>
                    <span className="text-[10px] text-slate-500">{t.category}</span>
                    {resIcon && <span className="ml-auto inline-flex items-center gap-1 text-[10px]">{resIcon} {resForCode.duration_ms}ms</span>}
                  </div>
                  <div className="text-slate-700 dark:text-slate-200 mt-0.5">{t.title}</div>
                  {resForCode && <div className={`text-[10px] mt-1 italic ${resForCode.status === "pass" ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>📋 {resForCode.note}</div>}
                </div>
              </div>
            </label>
          );
        })}
      </div>
      {results && (
        <div className="mt-3 text-xs p-3 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200" data-testid="qa-auto-summary">
          <strong>Sumar:</strong> {results.summary.pass} pass / {results.summary.fail} fail / {results.summary.total} total
          {results.summary.written_to_run > 0 && <> · <strong>{results.summary.written_to_run}</strong> scrise în run</>}
        </div>
      )}
    </AdminCard>
  );
};



const RunsList = ({ onPick, onCreate }) => {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/qa/runs`);
      setRuns(data.runs || []);
    } catch (e) {
      toast.error("Nu am putut încărca run-urile");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = async () => {
    setCreating(true);
    try {
      const { data } = await axios.post(`${API}/admin/qa/runs`, { name, version });
      toast.success("Run creat");
      onCreate(data.run.run_id);
    } catch (e) {
      toast.error("Eroare la creare run");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <AdminCard title="Run nou" testid="qa-run-create">
        <p className="text-xs text-slate-500 mb-2">Creează un test run cu toate cele 105 scenarii din QA Playbook. Le poți marca progresiv pe parcursul mai multor sesiuni.</p>
        <div className="space-y-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nume run (ex: Release v2026.03)"
            className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
            data-testid="qa-new-run-name" />
          <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="Versiune testată (opțional)"
            className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
            data-testid="qa-new-run-version" />
          <AdminBtn variant="primary" onClick={create} disabled={creating} data-testid="qa-create-run-btn">
            {creating ? <Loader2 className="w-3.5 h-3.5 inline animate-spin" /> : <Play className="w-3.5 h-3.5 inline mr-1" />}
            Pornește run nou
          </AdminBtn>
        </div>
      </AdminCard>

      <AdminCard title={`Run-uri recente (${runs.length})`} testid="qa-runs-list" action={
        <button onClick={reload} className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white inline-flex items-center gap-1" data-testid="qa-runs-reload">
          <RotateCw className="w-3.5 h-3.5" /> Refresh
        </button>
      }>
        {loading ? (
          <div className="text-xs text-slate-500 py-6 text-center"><Loader2 className="w-4 h-4 inline animate-spin mr-1" /> Se încarcă...</div>
        ) : runs.length === 0 ? (
          <div className="text-xs text-slate-500 py-6 text-center">Niciun run încă. Creează unul nou →</div>
        ) : (
          <ul className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
            {runs.map((r) => (
              <li key={r.run_id}>
                <button onClick={() => onPick(r.run_id)} className="w-full text-left p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition" data-testid={`qa-pick-run-${r.run_id.slice(0,8)}`}>
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{r.name}</div>
                    {r.closed_at ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-500/15 text-slate-600 dark:text-slate-300">închis</span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">activ</span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    <span>v: {r.version || "—"}</span> · <span>creat: {new Date(r.created_at).toLocaleDateString("ro-RO")}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </AdminCard>
    </div>
  );
};



// ----------------------------------------------------------------------------
// Release Gate — runs all 14 automated tests, emails summary to admins.
// ----------------------------------------------------------------------------


export const AdminQAPlaybook = () => {
  const [runId, setRunId] = useState(null);
  const [run, setRun] = useState(null);
  const [summary, setSummary] = useState({ progress_pct: 0, by_status: {} });
  const [search, setSearch] = useState("");
  const [filterPrio, setFilterPrio] = useState("ALL");
  const [filterStatus, setFilterStatus] = useState("ALL");

  const loadRun = useCallback(async (id) => {
    try {
      const { data } = await axios.get(`${API}/admin/qa/runs/${id}`);
      setRun(data.run);
      setSummary(data.summary);
      setRunId(id);
    } catch (e) {
      toast.error("Nu am putut încărca run-ul");
    }
  }, []);

  const updateCheck = useCallback(async (checkId, status, note) => {
    try {
      const { data } = await axios.patch(`${API}/admin/qa/runs/${runId}/check/${checkId}`, { status, note });
      setRun(data.run);
      setSummary(data.summary);
    } catch (e) {
      toast.error("Eroare la salvare");
    }
  }, [runId]);

  const closeRun = async () => {
    if (!confirm("Sigur închizi acest run? Nu va mai putea fi modificat.")) return;
    try {
      const { data } = await axios.post(`${API}/admin/qa/runs/${runId}/close`);
      setRun(data.run);
      setSummary(data.summary);
      toast.success("Run închis");
    } catch (e) {
      toast.error("Eroare la închidere");
    }
  };

  const exportMd = () => {
    window.open(`${API}/admin/qa/runs/${runId}/markdown`, "_blank");
  };

  // Filtered + grouped
  const filteredByCategory = useMemo(() => {
    if (!run) return {};
    const q = search.trim().toLowerCase();
    const out = {};
    for (const c of run.checks || []) {
      if (filterPrio !== "ALL" && c.priority !== filterPrio) continue;
      if (filterStatus !== "ALL" && c.status !== filterStatus) continue;
      if (q && !(c.code.toLowerCase().includes(q) || c.description.toLowerCase().includes(q) || (c.subcategory||"").toLowerCase().includes(q))) continue;
      (out[c.category] = out[c.category] || []).push(c);
    }
    return out;
  }, [run, search, filterPrio, filterStatus]);

  // Selection screen
  if (!runId || !run) {
    return (
      <div className="space-y-4">
        <AdminCard testid="qa-intro">
          <div className="flex items-start gap-3">
            <ShieldCheck className="w-8 h-8 text-emerald-600 shrink-0" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">QA Playbook · 105 scenarii de test</h2>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                Execută manual testele cu un click. Marchează fiecare scenariu ca <strong>pass</strong>, <strong>fail</strong> sau <strong>skip</strong> și adaugă note. Progresul se salvează automat — poți reveni oricând să continui.
                Folosește <strong>AI Test Suggester</strong> pentru a genera teste noi pentru feature-urile recent adăugate.
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                <span className="px-2 py-1 rounded-full bg-red-500/15 text-red-700 dark:text-red-300">P0 = release blocker</span>
                <span className="px-2 py-1 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300">P1 = should-pass</span>
                <span className="px-2 py-1 rounded-full bg-sky-500/15 text-sky-700 dark:text-sky-300">P2 = lunar / nice-to-have</span>
              </div>
            </div>
          </div>
        </AdminCard>
        <ReleaseGateCard />
        <ContentAuditCard />
        <TerminologyAuditCard />
        <RunsList onPick={loadRun} onCreate={loadRun} />
        <AISuggester runId={null} />
        <AutomationPanel runId={null} />
      </div>
    );
  }

  // Run view
  return (
    <div className="space-y-4">
      <RunHeader run={run} summary={summary} onClose={closeRun} onExport={exportMd} onChangeRun={() => { setRunId(null); setRun(null); }} />

      <div className="grid lg:grid-cols-[1fr_360px] gap-4">
        <div className="space-y-4">
          {/* Filter bar */}
          <AdminCard testid="qa-filters">
            <div className="flex flex-wrap gap-2 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Caută în coduri, descrieri..."
                  className="w-full text-sm pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                  data-testid="qa-search"
                />
              </div>
              <select value={filterPrio} onChange={(e) => setFilterPrio(e.target.value)}
                className="text-sm px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                data-testid="qa-filter-prio">
                <option value="ALL">Toate prioritățile</option>
                <option value="P0">P0 — release blocker</option>
                <option value="P1">P1 — should-pass</option>
                <option value="P2">P2 — opțional</option>
              </select>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                className="text-sm px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                data-testid="qa-filter-status">
                <option value="ALL">Toate statusurile</option>
                <option value="pending">Pending</option>
                <option value="pass">Pass</option>
                <option value="fail">Fail</option>
                <option value="skip">Skip</option>
              </select>
              <span className="text-xs text-slate-500 ml-auto inline-flex items-center gap-1">
                <ListChecks className="w-3.5 h-3.5" /> {Object.values(filteredByCategory).reduce((s,a)=>s+a.length,0)} afișate
              </span>
            </div>
          </AdminCard>

          {/* Categories */}
          {Object.keys(filteredByCategory).length === 0 ? (
            <AdminCard><div className="text-center py-8 text-sm text-slate-500">Niciun test nu corespunde filtrului.</div></AdminCard>
          ) : (
            Object.entries(filteredByCategory).map(([cat, checks]) => (
              <CategoryGroup key={cat} category={cat} checks={checks} onUpdate={updateCheck} />
            ))
          )}
        </div>

        <div className="space-y-4">
          <AISuggester
            runId={runId}
            onCheckAdded={(payload) => {
              if (payload?.run) setRun(payload.run);
              if (payload?.summary) setSummary(payload.summary);
            }}
          />
          <AutomationPanel runId={runId} onAfterRun={() => loadRun(runId)} />
        </div>
      </div>
    </div>
  );
};

export default AdminQAPlaybook;
